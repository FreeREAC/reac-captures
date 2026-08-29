#!/usr/bin/env python3
"""Why an S-4000S cold-connects to a real M-5000 and not to reac-pw.

Censuses one or more captures by (source, frame geometry, control op) and
normalises every count by the capture's own duration, because the corpus mixes
phases: a desk sitting in its control phase emits ~77 frames/s while a streaming
segment emits 8000, so a PERCENTAGE of frames compares nothing. Rates compare.

Geometry is the role test and it needs no heuristic. reac.ksy fixes a REAC frame
at 52 + n_channels*36, so 1492 is the 40-channel master downstream and 1204 is a
32-channel box upstream. A box emitting 1204 is a BOX, whatever any FSM says
about it -- this is what refuted the reading that our S-4000 was driving the
segment as a rival master.

Read through reac_pcap.iter_packets, which drops a mirrored capture's duplicate
copies; several corpus files are mirrored and ours is not, so any count taken
without it compares a doubled stream against a single one.
"""
import sys, collections
sys.path.insert(0, __file__.rsplit('/', 1)[0])
from reac_pcap import iter_packets, mac, is_reac, control

CAPTURES = '/home/pau/Devel/audio/reac-captures/captures/'


def census(path):
    ops = collections.Counter()
    frames = collections.Counter()
    geom = collections.Counter()
    unicast = collections.Counter()
    t0 = t1 = None
    for ts, wirelen, fr in iter_packets(path):
        if not is_reac(fr):
            continue
        if t0 is None:
            t0 = ts
        t1 = ts
        src, dst = mac(fr[6:12]), mac(fr[0:6])
        frames[src] += 1
        geom[(src, wirelen)] += 1
        c = control(fr)
        if c:
            ops[(src, c[0], c[1].hex(), c[2])] += 1
            if dst != 'ff:ff:ff:ff:ff:ff':
                unicast[src] += 1
    return frames, geom, ops, unicast, max((t1 or 0) - (t0 or 0), 1e-9)


def channels(wirelen):
    return f'{(wirelen - 52) // 36}ch' if wirelen >= 52 and (wirelen - 52) % 36 == 0 else 'non-geom'


def report(path, label):
    frames, geom, ops, unicast, dur = census(path)
    print(f'\n===== {label}\n      {path.rsplit("/", 1)[-1]}  ({dur:.1f}s) =====')
    for src, n in frames.most_common():
        sizes = ', '.join(f'{wl}B {channels(wl)} x{c}'
                          for (s, wl), c in geom.most_common() if s == src)
        print(f'  {src}  {n} frames ({n / dur:.0f}/s)  unicast-ctrl={unicast[src]}')
        print(f'      geometry: {sizes}')
        for (s, tag, op, oplen), c in sorted(ops.items(), key=lambda kv: -kv[1]):
            if s == src:
                print(f'      {tag} {op} oplen={oplen:<4d} {c:6d}  {c / dur:7.2f}/s')


if __name__ == '__main__':
    args = sys.argv[1:] or [
        ('m5000-s4000s-96k-mirror__matrix-m5000-s4000-unit1-coldconnect-2026-07-11.pcap',
         'REAL M-5000 + S-4000S unit1 -- box JOINS'),
        ('m5000-none-96k-mirror__matrix-m5000-s4000-unit2-coldconnect-2026-07-11.pcap',
         'REAL M-5000 + S-4000S unit2 (c4:08:bc, OUR box) -- box JOINS'),
        ('reacpw-m5000-s4000s-96k-direct__s4000s-c408bc-filler-only-no-coldconnect-2026-08-30.pcap',
         'reac-pw master + the SAME box c4:08:bc -- never joins'),
    ]
    for item in args:
        path, label = item if isinstance(item, tuple) else (item, item)
        report(path if path.startswith('/') else CAPTURES + path, label)
