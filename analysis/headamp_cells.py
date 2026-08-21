#!/usr/bin/env python3
"""Which head-amp CELLS did a desk actually write, and in which order?

The op-0403 container carries a Roland DT1 record at frame[34:40]:

    34 35   TAG 01 01   = head-amp
    36      CH          = wire channel (box base + input - 1)
    37      PARAM       = 0 phantom, 1 pad, 2 sens
    38      VALUE
    39      inner checksum (sum-to-0x80)

(reac-pw `src/reac_ctrl.c` TMPL_HEADAMP, byte-truthed against a live M-200.)

The question this answers: on a box whose upper bank CONVERTS, which CH did the
real desk use for the upper inputs? If a golden that lights slot 16 never writes
CH 0x2f, the aliasing we measured is not the box mis-decoding our record — it is
us addressing a cell the desk does not use.

Usage: headamp_cells.py <pcap>...
"""
import collections, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reac_pcap as R

PARAM = {0: 'phantom', 1: 'pad', 2: 'sens'}


def cells(path, limit=400000):
    seen, order, n = collections.defaultdict(dict), [], 0
    for _ts, _wl, fr in R.iter_packets(path):
        n += 1
        if n > limit:
            break
        if not R.is_reac(fr) or len(fr) < 40:
            continue
        if fr[16:20] != b'\xcd\xea\x04\x03' or fr[34:36] != b'\x01\x01':
            continue
        src, ch, p, v = R.mac(fr[6:12]), fr[36], fr[37], fr[38]
        if (src, ch, p) not in seen or seen[(src, ch, p)] != v:
            order.append((src, ch, p, v))
        seen[(src, ch, p)] = v
    return seen, order


for path in sys.argv[1:]:
    seen, order = cells(path)
    print(f'\n=== {os.path.basename(path)}')
    if not seen:
        print('  no head-amp records')
        continue
    by_src = collections.defaultdict(set)
    for (src, ch, p) in seen:
        by_src[src].add(ch)
    for src, chs in sorted(by_src.items()):
        print(f'  writer {src}: CH {sorted(hex(c) for c in chs)}')
        print(f'    range 0x{min(chs):02x}..0x{max(chs):02x}, {len(chs)} distinct')
    print(f'  first 24 writes (src ch param value):')
    for src, ch, p, v in order[:24]:
        print(f'    {src}  CH 0x{ch:02x}  {PARAM.get(p, p):8s} {v}')
