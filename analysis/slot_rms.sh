#!/bin/bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Pau Aliagas <linuxnow@gmail.com>
#
# Capture a box's upstream and print per-slot RMS -- the honest answer to "did that
# head-amp write reach the preamps?".
#
# The filter pins `ether src <box>` so our own TX can never be mistaken for the box's
# answer, and the capture is bounded by BOTH a frame count and a timeout: `-c N` alone is
# not a time window (at 8000 fps, -c 4000 is half a second and can close before the write
# lands), and a timeout alone never terminates on a silent segment.
#
# An unclaimed REAC box transmits NOTHING, so zero frames means "no master owns this box",
# not "the box is off". Use /sys/class/net/<nic>/carrier as the power detector instead.
#
# Usage: slot_rms.sh <nic> <box-mac> [label] [frames] [seconds]

set -o pipefail

NIC=${1:?nic}
MAC=${2:?box mac}
LABEL=${3:-slots}
FRAMES=${4:-3000}
SECS=${5:-8}

HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
UP=${UP_SLOTS:-$HERE/up_slots}
if [ ! -x "$UP" ]; then
	echo "up_slots not built at $UP" >&2
	echo "  gcc -O2 -o $UP $HERE/up_slots.c -I ~/Devel/audio/libreac/include \\" >&2
	echo "      ~/Devel/audio/libreac/libreac.a -lm" >&2
	exit 2
fi

if [ "$(cat "/sys/class/net/$NIC/carrier" 2>/dev/null)" != "1" ]; then
	echo "$LABEL: NIC $NIC has NO CARRIER -- the box is unplugged or powered off" >&2
	exit 3
fi

PCAP=$(mktemp -u -t "reac-$LABEL-XXXXXX.pcap")
trap 'sudo -n rm -f "$PCAP"' EXIT

# -Z root keeps tcpdump from dropping to the unprivileged `tcpdump` user, which cannot
# write a file we created. Without it the capture is empty and the probe reports the box
# as silent -- a broken probe and a dead box are indistinguishable from the output alone,
# so `mktemp -u` hands tcpdump a NAME and lets it create the file itself.
sudo -n timeout "$SECS" tcpdump -Z root -i "$NIC" -c "$FRAMES" -w "$PCAP" \
	"ether proto 0x8819 and ether src $MAC" >/dev/null 2>&1

# tcpdump exits non-zero when the timeout fires with fewer than N frames, which is a
# normal outcome here, so the frame count -- not the exit status -- is the check.
if [ ! -s "$PCAP" ]; then
	echo "$LABEL: NO FRAMES from $MAC on $NIC in ${SECS}s" >&2
	exit 4
fi

echo "== $LABEL =="
"$UP" "$PCAP" 200
