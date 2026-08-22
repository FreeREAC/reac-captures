#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Pau Aliagas <linuxnow@gmail.com>
"""Every distinct cfea MASTER-ANNOUNCE a desk emits in a capture, as raw bytes.

Written to answer one question: WHERE DOES THE REAC PACE RIDE? reac-pw builds the cfea
announce from a captured M-200 at 48 kHz and hard-zeroes bytes [22:33]; it paces its own
TX at whatever --rate says but never tells the box, and measurement shows two different
boxes ignoring a 96 kHz master and answering at 48 kHz (4000 pps). If a real desk running
96 kHz sets a byte our 48 kHz-derived announce leaves at zero, that byte is the pace.

The announce is 34 bytes from the `cfea` at frame offset 16. Known fields (analysis/README):
  [17] audio fabric total (0x28 = 40 slots)   [18] box input width
  [19] console generation (0 V-Mixer, 1 OHRCA) [20:22] enrolled-box count, big-endian
  [22:33] UNMAPPED -- reac-pw always sends zeros here.

Output is grouped by source MAC so a desk and a stand-in master are never merged, and the
MAC is printed because the corpus contains captures where reac-pw impersonated a real desk
MAC: a desk MAC is NOT proof of a real desk.

Usage: announce_bytes.py <pcap> [<pcap> ...]
"""

import sys
from collections import Counter, defaultdict

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from reac_pcap import iter_packets, is_reac, mac  # noqa: E402

ANNOUNCE_LEN = 34


def announces(path):
    """(src_mac -> Counter of 34-byte announce payloads) for one capture."""
    out = defaultdict(Counter)
    # iter_packets yields (ts, wirelen, frame) -- unpacking it as a bare frame makes
    # is_reac() false for every packet, which reads exactly like "this capture has no
    # announce". Counting REAC frames alongside is what catches that.
    seen = 0
    for _ts, _wirelen, fr in iter_packets(path):
        if not is_reac(fr):
            continue
        seen += 1
        body = fr[16:16 + ANNOUNCE_LEN]
        if len(body) < ANNOUNCE_LEN or body[0:2] != b"\xcf\xea":
            continue
        out[mac(fr[6:12])][bytes(body)] += 1
    out["__reac_frames__"] = seen
    return out


def show(path):
    got = announces(path)
    nreac = got.pop("__reac_frames__", 0)
    print(f"# {path.rsplit('/', 1)[-1]}  ({nreac} REAC frames)")
    if not got:
        print("    no cfea announce in this capture")
        return
    for src, variants in sorted(got.items()):
        print(f"  src {src}  ({len(variants)} distinct announce(s))")
        for body, n in variants.most_common():
            hexed = " ".join(f"{b:02x}" for b in body)
            print(f"    x{n:<6} {hexed}")
            print(f"           total=0x{body[17]:02x} width=0x{body[18]:02x} "
                  f"gen=0x{body[19]:02x} boxes={body[20] << 8 | body[21]} "
                  f"tail[22:33]={' '.join(f'{b:02x}' for b in body[22:33])}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        show(p)
        print()
