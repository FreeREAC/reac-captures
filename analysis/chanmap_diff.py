#!/usr/bin/env python3
"""Dump the DISTINCT desk->box control blocks per opcode, so two establishes diff.

The head-amp record says WHICH cell; the chanmap and the subscription say what
the box is told to BE. A real desk and reac-pw write the same 16 head-amp cells
(measured 2026-08-21) yet only the real one reaches the upper bank, so the
difference is in these blocks, not in the addressing.

Prints, per (opcode, block-bytes), the count — a stable block appears once with
a large count, a rolling one (the chanmap sweep) appears many times.

Usage: chanmap_diff.py <op-hex e.g. 01030019|any> <pcap>...
"""
import collections, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reac_pcap as R

want = sys.argv[1].lower()

for path in sys.argv[2:]:
    blocks = collections.Counter()
    order = []
    n = 0
    for _ts, _wl, fr in R.iter_packets(path):
        n += 1
        if n > 400000:
            break
        if not R.is_reac(fr) or len(fr) < 50:
            continue
        if fr[16:18] != b'\xcd\xea':
            continue
        op = fr[18:22].hex()
        if want != 'any' and op != want:
            continue
        src = R.mac(fr[6:12])
        if src.startswith('00:40:ab:c4'):     # a box, not a desk
            continue
        key = (src, op, fr[18:50].hex())
        if key not in blocks:
            order.append(key)
        blocks[key] += 1
    print(f'\n=== {os.path.basename(path)}   ({len(order)} distinct)')
    for key in order[:40]:
        src, op, blk = key
        print(f'  {src} op {op} x{blocks[key]:-6d}')
        b = bytes.fromhex(blk)
        print(f'     {" ".join(f"{x:02x}" for x in b[:16])}')
        print(f'     {" ".join(f"{x:02x}" for x in b[16:])}')
