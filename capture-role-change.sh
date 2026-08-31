#!/bin/bash
# Capture a role-change experiment on a live REAC segment.
#
#   ./capture-role-change.sh <arm> <nic> [seconds]
#
# Arms are the three in CAPTURE-PLAN-role-change.md. This script only CAPTURES and records
# context; the physical act (flipping a REAC Mode switch, power-cycling a box) is the operator's,
# and the script tells you when to do it.
#
# WHY A SCRIPT: a capture whose context was not recorded at the time is a file nobody can name
# later — this corpus renames from measured facts, and the facts have to exist. It writes a
# sidecar with the daemon's state before and after, so the pcap is interpretable a year on.
set -u

ARM="${1:?arm: rival-arrives | we-cede | identity-change | sp-mode}"
NIC="${2:?nic, e.g. enp131s0 — NOT the USB AX88179, it lies about enrolment}"
SECS="${3:-90}"
STAMP=$(date +%Y%m%d-%H%M%S)
OUT="$HOME/Devel/audio/reac-captures/captures/role-${ARM}-${STAMP}"
mkdir -p "$(dirname "$OUT")"

note() { echo "$*" | tee -a "$OUT.notes.txt"; }

note "=== role-change capture: $ARM on $NIC, ${SECS}s, $STAMP"
note "--- link:  $(ethtool "$NIC" 2>/dev/null | grep -i 'speed\|link detected' | tr '\n' ' ')"
note "--- daemon before:"
journalctl --user -u reac-pw --no-pager -o short-precise -n 12 2>/dev/null \
  | grep -E "recognized|ESTABLISHED|PROBING|GRANTING" | tail -4 | tee -a "$OUT.notes.txt"

case "$ARM" in
  rival-arrives)   ACT="Flip the OTHER box's REAC Mode switch to M and power-cycle it." ;;
  we-cede)         ACT="Run: systemctl --user stop reac-pw   (then start it again at the halfway mark)" ;;
  identity-change) ACT="Restart reac-pw with a different REAC_NAME on this NIC." ;;
  sp-mode)         ACT="POWER-CYCLE the box (its REAC Mode switch is already on SP). The switch is latched at BOOT — measured 2026-08-31: moving it live changed nothing." ;;
  *) echo "unknown arm: $ARM"; exit 2 ;;
esac

note ""
note ">>> CAPTURE STARTS NOW. After ~10 s, do this:"
note ">>>   $ACT"
note ">>> WATCH THE BOX: relays audible? REAC LED blinking? Write it below — the journal"
note ">>> cannot tell a cold connect from a re-adoption, and only your eyes can."
note ""

sudo timeout "$SECS" tcpdump -i "$NIC" -s 0 -w "$OUT.pcap" ether proto 0x8819 2>>"$OUT.notes.txt"
RC=$?

note "--- tcpdump exit $RC   size: $(du -h "$OUT.pcap" 2>/dev/null | cut -f1)"
note "--- daemon after:"
journalctl --user -u reac-pw --no-pager -o short-precise --since "-${SECS}s" 2>/dev/null \
  | grep -E "recognized|ESTABLISHED|PROBING|GRANTING|peer-gone|rival" | tail -8 | tee -a "$OUT.notes.txt"

# A capture that caught nothing looks exactly like a segment that said nothing. Prove it saw
# frames before anyone trusts its silence.
FRAMES=$(tcpdump -r "$OUT.pcap" 2>/dev/null | wc -l)
note "--- FRAMES CAPTURED: $FRAMES"
if [ "$FRAMES" -lt 100 ]; then
  note "!!! FEWER THAN 100 FRAMES — the capture is suspect. A REAC segment at 48k emits 8000/s."
  note "!!! Check the NIC name and that the segment was live. Do NOT analyse this file."
fi
note ""
note "WRITE HERE what the box physically did (relays / LED / audio), then add an entry to"
note "MANIFEST.md naming this capture from its measured facts:"
note "  box did: "
