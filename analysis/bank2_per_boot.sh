#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Pau Aliagas <linuxnow@gmail.com>
#
# Ride S-1608 power cycles and record, PER BOOT, two things together:
#   1. the value the box reports in its join  (1212 tag 0100, data byte 2)
#   2. whether each BANK's preamp actually moves audio
#
# WHY BOTH, ON THE SAME BOOT. 2026-08-22 established that our traffic is identical to
# a real M-200's in every dimension: chanmap coverage, the channels addressed, the
# params, the values, the record bytes and the establish ORDER (ACK 20x3 MARK Bx6
# 21x3 .. 2fx3, 56 records). So nothing WE send explains why ports 9-16 never enrol.
# The only box-side variable found is that join byte, which changes between boots:
# across the whole corpus this unit has reported 0x01 x245, 0x05 x5, 0x09 x2. Whether
# it predicts bank health is UNKNOWN — no capture carries a bank measurement beside
# it. This script is what makes the correlation, one boot at a time.
#
# THIS SCRIPT NEVER STARTS reac-pw. Its predecessor did, and relaunched a master on
# every cycle: three copies left running spawned three masters on one segment, which
# is what broke establishment AND froze the head-amp for a whole night. A second
# master leaves the box enrolled but refusing head-amp updates — phantom still lands,
# SENS and pad do not — which reads exactly like a protocol fault and is not one. So
# this script REFUSES TO RUN if the segment does not have exactly one master, and
# never creates one.
#
# THE VERDICT IS AUDIO, never a status field. Each bank is measured against ITSELF at
# two gains on a source-free channel — the preamp's own noise floor is the signal, and
# a ratio survives a quiet room where an absolute threshold does not. An untouched
# slot is read in the same capture as a reference: if IT moves, the measurement is
# noise and the row says so.
set -o pipefail

IFACE=${IFACE:-enp131s0}   # the S-1608's segment since the eth0 adapter was retired
BOX=${BOX:-00:40:ab:c4:80:41}
API=${API:-http://127.0.0.1:8800}
HERE=$(cd "$(dirname "$0")" && pwd)
LOG=${LOG:-$HERE/bank2-per-boot.log}

# console channel -> box port. The patch puts the S-1608's ports 1-12 on ch9-20, so the
# console channel is the port plus 8. Re-read it before trusting these two if the patch moves:
#   curl -s localhost:8800/api/patch/input/input/<ch>   ->  capture_AUX<n> is port n+1
BANK1_CH=13; BANK1_SLOT=5      # port 5  -> wire 0x24, inside the bank that works
BANK2_CH=17; BANK2_SLOT=9      # port 9  -> wire 0x28, the first slot of the dead bank
REF_SLOT=2                     # untouched, read in every capture as the reference

say () { echo "$(date -Is) $*" | tee -a "$LOG"; }

masters () {
	local n=0
	for p in /proc/[0-9]*; do
		[ -r "$p/status" ] || continue
		[ "$(awk '/^Name:/{print $2}' "$p/status" 2>/dev/null)" = reac-pw ] || continue
		[ "$(awk '/^Tgid:/{print $2}' "$p/status")" = "${p#/proc/}" ] || continue
		tr '\0' ' ' < "/proc/${p#/proc/}/cmdline" | grep -q -- "--live $IFACE" && n=$((n+1))
	done
	echo "$n"
}

rms () {  # rms <slot>  -> dBFS for that slot, from the wire
	sudo -n "$HERE/slot_rms.sh" "$IFACE" "$BOX" b2 8000 3 2>/dev/null \
		| grep -oP "^slot +$1: +\K-?[0-9.]+"
}

# ONLY the gain. The operator lights phantom across the box to watch the LEDs while testing,
# and pad may be set deliberately too — a probe that clears either is destroying the operator's
# own instrument. Twice on 2026-08-22 a sweep wrote pad:false and phantom:false and put out the
# lights someone was reading.
set_gain () { curl -s --max-time 5 -X PATCH "$API/api/channel/input/$1/headAmp" \
	-H 'content-type: application/json' -d "{\"gainDb\":$2}" >/dev/null; }

# sweep <console-ch> <slot> -> "lo hi delta ref_lo ref_hi"
#
# The low end is 10 dB rather than 0 only so the ratio is read against a real gain
# setting. An earlier note here claimed 0 un-enrols a channel; that was inferred from
# a run that also involved daemon restarts and duplicate masters, and the operator has
# since observed channels sitting at 0 while holding 48V and passing sound. Unproven,
# so not claimed.
SWEEP_LO=${SWEEP_LO:-10}
sweep () {
	set_gain "$1" $SWEEP_LO;  sleep 4; local lo ref_lo;  lo=$(rms "$2");  ref_lo=$(rms "$REF_SLOT")
	set_gain "$1" 55; sleep 4; local hi ref_hi;  hi=$(rms "$2");  ref_hi=$(rms "$REF_SLOT")
	set_gain "$1" 32
	python3 -c "
lo,hi,a,b='$lo','$hi','$ref_lo','$ref_hi'
try: print(f'{float(lo):.1f} {float(hi):.1f} {float(hi)-float(lo):+.1f} {float(a):.1f} {float(b):.1f}')
except Exception: print('- - - - -')"
}

# The join is sent ONCE, AT ESTABLISH — not continuously. Measured 2026-08-22: a
# window opened after the box has settled captures 31615 box frames and ZERO joins.
# So the capture must be RUNNING BEFORE the box comes back, and span the whole
# settle. Start it at link-up, decode it after.
join_start () {
	JOINPCAP=$(mktemp -u /tmp/join.XXXX.pcap)
	sudo -n timeout 50 tcpdump -Z root -i "$IFACE" -w "$JOINPCAP" \
		ether src "$BOX" and ether proto 0x8819 2>/dev/null &
	JOINPID=$!
}

join_finish () {
	wait $JOINPID 2>/dev/null
	python3 - "$JOINPCAP" <<-'PY'
	import sys, collections
	sys.path.insert(0, '/home/pau/Devel/audio/reac-captures/analysis')
	from reac_pcap import iter_packets, dt1_record
	c = collections.Counter()
	for ts, wl, fr in iter_packets(sys.argv[1]):
	    r = dt1_record(fr)
	    if r and r['marker'] == '1212' and r['tag'] == '0100' and len(r['data']) >= 3:
	        c[r['data'][2]] += 1
	print(' '.join(f'0x{v:02x}x{n}' for v, n in c.most_common()) or 'NO-JOIN-CAPTURED')
	PY
	rm -f "$JOINPCAP"
}

n=$(masters)
if [ "$n" != 1 ]; then
	say "REFUSING: $n masters on $IFACE (need exactly 1). Kill the extras — and any"
	say "          cycle-until-healthy.sh still running, which respawns them every cycle."
	exit 1
fi
say "one master on $IFACE — good. Power-cycle the box when you like; Ctrl-C to stop."

boot=0
prev_up=1
while true; do
	up=$(cat "/sys/class/net/$IFACE/carrier" 2>/dev/null || echo 0)
	if [ "$prev_up" = 1 ] && [ "$up" = 0 ]; then say "link DOWN — box power-cycling"; fi
	if [ "$prev_up" = 0 ] && [ "$up" = 1 ]; then
		boot=$((boot+1))
		say "link UP — boot #$boot, capturing the establish and settling 45 s"
		join_start
		sleep 45
		[ "$(masters)" = 1 ] || { say "boot #$boot ABORT: master count changed to $(masters)"; prev_up=$up; continue; }
		jb=$(join_finish)
		b1=$(sweep "$BANK1_CH" "$BANK1_SLOT")
		b2=$(sweep "$BANK2_CH" "$BANK2_SLOT")
		say "boot #$boot  join=$jb"
		say "    bank1 port5 (lo hi delta ref_lo ref_hi): $b1"
		say "    bank2 port9 (lo hi delta ref_lo ref_hi): $b2"
		say "    read: delta >= +25 dB is a live preamp; ref must not move."
	fi
	prev_up=$up
	sleep 2
done
