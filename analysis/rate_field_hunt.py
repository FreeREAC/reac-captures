#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Pau Aliagas <linuxnow@gmail.com>
"""Where does the REAC PACE ride? Diff a desk's whole control plane at 48k vs 96k.

Measured 2026-08-22: a real stagebox FOLLOWS the master's pace symmetrically -- 4000 pps
at 48 kHz, 8000 pps at 96 kHz, matching the desk in both directions (mirror-tap doubling
accounted for: the desk copy is duplicated in this corpus, the box copy is not). reac-pw's
downstream is byte-identical and cadence-identical to a real 96 kHz desk -- 1492-byte
frames at 125.1 us, p50 124.9 -- and BOTH boxes on this rig still answer at 4000 pps.

So the pace is not carried by the cadence alone, and it is not in the cfea announce (the
only 48k-vs-96k difference there is byte [19], the console generation, and forcing that to
OHRCA does not move the box). This tool widens the search to every control op the desk
emits, so the field cannot hide in an op nobody thought to look at.

Frames are grouped by (tag, op, oplen). For each group the payloads are collapsed with a
per-offset "does this byte ever vary" mask, so a counter or checksum column reads as
VARIABLE and a genuine constant stands out. Comparing the two rates' constants is then a
byte-for-byte question rather than an eyeball job.

Usage: rate_field_hunt.py <48k-pcap> <desk-mac> <96k-pcap> <desk-mac> [frame-budget]
"""

import sys
from collections import defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from reac_pcap import iter_packets, is_reac, mac  # noqa: E402

PAYLOAD = 48   # bytes from the tag onward -- covers every known control block


def scan(path, desk, budget):
    """(tag,op,oplen) -> [constant-or-None per byte offset], for desk-sourced control."""
    seen = defaultdict(list)
    n = 0
    for _ts, _wl, fr in iter_packets(path):
        if not is_reac(fr) or mac(fr[6:12]) != desk:
            continue
        n += 1
        if n > budget:
            break
        tag = fr[16:18]
        if tag not in (b"\xcd\xea", b"\xcf\xea"):
            continue
        key = (tag.hex(), fr[18:20].hex(), int.from_bytes(fr[20:22], "big"))
        seen[key].append(bytes(fr[16:16 + PAYLOAD]))
    out = {}
    for key, bodies in seen.items():
        first = bodies[0]
        const = list(first)
        for b in bodies[1:]:
            for i in range(min(len(const), len(b))):
                if const[i] is not None and const[i] != b[i]:
                    const[i] = None
        out[key] = (const, len(bodies))
    return out


def fmt(const):
    return " ".join("--" if c is None else f"{c:02x}" for c in const)


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        return 2
    p48, d48, p96, d96 = sys.argv[1:5]
    budget = int(sys.argv[5]) if len(sys.argv) > 5 else 120000

    a = scan(p48, d48, budget)
    b = scan(p96, d96, budget)

    print("# '--' = byte varies within that capture (counter/checksum/payload)")
    print(f"# 48k desk {d48}   vs   96k desk {d96}\n")

    for key in sorted(set(a) | set(b)):
        tag, op, oplen = key
        ca, na = a.get(key, (None, 0))
        cb, nb = b.get(key, (None, 0))
        print(f"== {tag} op {op} len {oplen}   48k:x{na}  96k:x{nb}")
        if ca is None:
            print("   ONLY AT 96k")
            print(f"   96k {fmt(cb)}")
            continue
        if cb is None:
            print("   ONLY AT 48k")
            print(f"   48k {fmt(ca)}")
            continue
        diffs = [i for i in range(min(len(ca), len(cb)))
                 if ca[i] != cb[i] and ca[i] is not None and cb[i] is not None]
        print(f"   48k {fmt(ca)}")
        print(f"   96k {fmt(cb)}")
        # The MAC bytes always differ (different desks) -- call that out so it is never
        # mistaken for a rate field.
        note = " (offsets 6..11 are the desk MAC, expected to differ)" if any(
            6 <= i <= 11 for i in diffs) else ""
        print(f"   differing CONSTANT offsets: {diffs}{note}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
