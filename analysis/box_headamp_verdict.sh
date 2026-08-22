#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Pau Aliagas <linuxnow@gmail.com>
#
# HEALTHY or GATED? One command, one verdict, per box.
#
# The S-1608's head-amp path is gated at boot from two I/O-expander bits that no wire
# sequence reaches (FUN_0c00f6b4 -> FUN_0c007e06/FUN_0c00cb14; decoded once in
# FUN_0c01091a and deliberately never re-sampled). EACH POWER CYCLE IS AN INDEPENDENT
# SAMPLE, which is why the box worked one morning and not that evening with nothing
# physically touched. So the question "did this boot come up healthy?" gets asked a lot,
# and asking it by ear or by LED is slow and easy to get wrong.
#
# The test: arm every declared input at a high SENS and ask whether ANY slot leaves the
# converter floor. A live preamp lifts its own noise floor ~35 dB going from minimum to
# maximum gain -- about -106 dBFS (a running converter with a dead-quiet analogue stage
# in front of it) to about -70. No microphone, no signal generator and no operator needed;
# the preamp's own thermal noise is the signal.
#
# IT IS A RATIO TEST, deliberately. It compares each slot against ITSELF at two gains
# rather than against an absolute threshold, because an absolute reading depends on how
# quiet the room is: the same healthy channel read -69 dBFS at midnight and -84 dBFS at
# 3 am. A ratio survives that; a threshold does not.
#
# ALWAYS RUN IT AGAINST A KNOWN-GOOD BOX FIRST if one is on the rig. A verdict of GATED
# from a probe that cannot detect a healthy box is worthless, and that exact false null
# has been reported confidently three times here.
#
# Usage: box_headamp_verdict.sh <nic> <box-mac> <headamp-base>
#   e.g. box_headamp_verdict.sh enp131s0 00:40:ab:c4:dc:9c 0     # S-0808 (control)
#        box_headamp_verdict.sh eth0     00:40:ab:c4:80:41 32    # S-1608
#
# The base is the box's PUBLISHED reac.headamp.base -- `headamp_set.py --list` prints it.
# Never select a box by node name: after a cable swap the node called "reac-playback" was
# the S-1608 and "reac-playback.s1608" was the S-0808. Every name wrong, every declaration
# right.

set -o pipefail

NIC=${1:?nic}
MAC=${2:?box mac}
BASE=${3:?headamp base}

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export UP_SLOTS=${UP_SLOTS:-$HERE/up_slots}

LOW=${LOW_SENS:-0}
HIGH=${HIGH_SENS:-44}
# 12 dB is well above the ~1 dB of run-to-run ambient wobble seen on an idle slot, and far
# below the ~35 dB a real preamp delivers, so neither noise nor a partial lift can straddle it.
THRESH=${THRESH_DB:-12}

read_slots() {   # -> "slot rms" lines
	"$HERE/slot_rms.sh" "$NIC" "$MAC" verdict 3000 8 2>/dev/null \
		| sed -nE 's/^slot +([0-9]+): +(-?[0-9.]+) dBFS$/\1 \2/p'
}

# SENS ONLY, deliberately. Sweeping phantom would drop 48 V on whatever condensers are
# plugged in and can pop hard through a live PA, and sweeping pad changes a setting the
# operator chose; neither adds anything to the verdict, because SENS alone moves an idle
# preamp's own noise floor by ~35 dB. A diagnostic that reconfigures the desk to run is a
# diagnostic nobody dares run during a show.
arm() {
	python3 "$HERE/headamp_set.py" --base "$BASE" --all --set "sens=$1" \
		>/dev/null || { echo "could not write head-amp (is a master running?)" >&2; exit 2; }
}

echo "# box $MAC on $NIC, head-amp base $BASE"
echo "# sweeping every declared input SENS (phantom and pad untouched) $LOW -> $HIGH"

arm "$LOW";  sleep 3; LOWOUT=$(read_slots)
arm "$HIGH"; sleep 3; HIGHOUT=$(read_slots)
arm "$LOW"                                     # leave the preamps where we found them

if [ -z "$LOWOUT" ] || [ -z "$HIGHOUT" ]; then
	echo "VERDICT: UNAVAILABLE — no frames from the box." >&2
	echo "  An unclaimed REAC box transmits NOTHING, so this does not mean 'powered off'." >&2
	echo "  Check: carrier=$(cat "/sys/class/net/$NIC/carrier" 2>/dev/null), and that a" >&2
	echo "  master owns this segment (pgrep -ax reac-pw)." >&2
	exit 3
fi

paste <(echo "$LOWOUT") <(echo "$HIGHOUT") | awk -v t="$THRESH" '
	{ slot=$1; lo=$2; hi=$4; d=hi-lo;
	  printf "  slot %2d: %8.1f -> %8.1f dBFS   delta %+6.1f%s\n",
	         slot, lo, hi, d, (d>=t ? "  LIVE" : "");
	  if (d>=t) live++; n++ }
	END {
	  printf "\n%d of %d inputs responded to SENS\n", live, n;
	  if (live==0)      print "VERDICT: GATED — the box applies no head-amp on any input.";
	  else if (live==n) print "VERDICT: HEALTHY — every declared input responded.";
	  else              print "VERDICT: PARTIAL — some inputs respond and some do not.";
	}'
