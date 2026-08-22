#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Pau Aliagas <linuxnow@gmail.com>
"""Per-source packet rate in a REAC capture -- who is pacing, and at what rate.

REAC's cadence IS its sample rate: libreac's byte law is pps = rate / 12, so 44.1k =
3675 pps, 48k = 4000 and 96k = 8000, with 12 samples per packet in every mode (the 96k
mode doubles pps rather than halving channels). That makes a packet rate a direct,
decode-free reading of the pace each end is running.

MIRRORED CAPTURES DOUBLE EVERY FRAME. Part of this corpus was taken on a TX/RX-mirrored
switch port, where the same frame appears twice -- one clean copy and one carrying +2
bytes of FCS residue (documented in libreac reac.h:35-47). A mirrored capture therefore
reads 8000 pps for a 48 kHz segment, which is exactly a 96 kHz segment's number. This
tool reports the RAW rate and, when it can see the duplication, the de-mirrored one, so
the two can never be confused. The `-mirror` / `-clean` token in a corpus filename says
which tap was used; trust the measurement over the name, since names in this corpus have
been wrong before.

Usage: pps_by_mac.py <pcap> [seconds-to-analyse]
"""

import struct
import sys
from collections import defaultdict

RATE_FOR_PPS = {3675: "44.1k", 4000: "48k", 8000: "96k"}


def frames(path):
    d = open(path, "rb").read()
    if len(d) < 24:
        return
    magic = struct.unpack("<I", d[:4])[0]
    endian = "<"
    if magic in (0xA1B2C3D4, 0xA1B23C4D):
        endian = "<"
    elif magic in (0xD4C3B2A1, 0x4D3CB2A1):
        endian = ">"
    nano = magic in (0xA1B23C4D, 0x4D3CB2A1)
    off = 24
    while off + 16 <= len(d):
        s, frac, incl, orig = struct.unpack(endian + "IIII", d[off:off + 16])
        off += 16
        pkt = d[off:off + incl]
        off += incl
        if len(pkt) < 14:
            continue
        ts = s + (frac / 1e9 if nano else frac / 1e6)
        yield ts, pkt


def classify(pps):
    best = min(RATE_FOR_PPS, key=lambda r: abs(r - pps))
    return RATE_FOR_PPS[best] if abs(best - pps) < best * 0.06 else "?"


def main():
    path = sys.argv[1]
    limit = float(sys.argv[2]) if len(sys.argv) > 2 else None

    per = defaultdict(list)
    seen = defaultdict(int)   # (src, payload-prefix) -> count, to detect mirroring
    t0 = None
    for ts, pkt in frames(path):
        if pkt[12:14] != b"\x88\x19":
            continue
        if t0 is None:
            t0 = ts
        if limit is not None and ts - t0 > limit:
            break
        src = ":".join(f"{b:02x}" for b in pkt[6:12])
        per[src].append(ts)
        seen[(src, pkt[14:34])] += 1

    if not per:
        print(f"{path}: no REAC (0x8819) frames -- an unclaimed box transmits nothing, "
              f"so this is not proof the box was off")
        return 1

    print(f"# {path}")
    for src, ts in sorted(per.items(), key=lambda kv: -len(kv[1])):
        if len(ts) < 2:
            continue
        span = ts[-1] - ts[0]
        if span <= 0:
            continue
        raw = len(ts) / span
        # A mirrored tap repeats each frame, so identical control payloads appear an
        # even number of times far more often than a live segment would produce.
        dupes = sum(c for (s, _), c in seen.items() if s == src and c >= 2)
        mirrored = dupes > len(ts) * 0.5
        eff = raw / 2 if mirrored else raw
        tag = " [mirrored, halved]" if mirrored else ""
        print(f"  {src}  frames={len(ts):>7} span={span:6.2f}s  "
              f"raw={raw:7.0f} pps  eff={eff:7.0f} pps -> {classify(eff):>5}{tag}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
