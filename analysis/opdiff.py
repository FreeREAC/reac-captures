#!/usr/bin/env python3
"""Op-set diff: what a real desk sends an S-1608 that reac-pw never sends.

Reads the committed analysis/placement_rows.jsonl (no pcap rescan).
Discriminator is the FILENAME prefix, not the source MAC: reac-pw impersonated
the real M-200 MAC 00:40:ab:c9:cc:03 in the July runs.
"""
import json, sys, collections

ROWS = '/home/pau/Devel/audio/reac-captures/analysis/placement_rows.jsonl'

rows = [json.loads(l) for l in open(ROWS)]
by_file = {r['file']: r for r in rows}

GOLDEN = [f for f in by_file if f.startswith(('m200-ch16-anchor', 'm200-headamp-1357',
                                              'm200-s1608-COLDCONNECT', 'm200-s1608-establish-today',
                                              'm200-anchor-openwindow', 'm200-pad-'))]
OURS = [f for f in by_file if f.startswith('reacpw-')]

def deskops(r):
    """op keys sourced by the DESK side (cfea sourcer), as a set."""
    desks = set(r.get('desk_macs') or [])
    out = collections.Counter()
    for k, n in (r.get('ops') or {}).items():
        src, kind, op, ln = k.split('|')
        if src in desks:
            out[f'{kind} {op} {ln}'] += n
    return out

def boxops(r):
    desks = set(r.get('desk_macs') or [])
    out = collections.Counter()
    for k, n in (r.get('ops') or {}).items():
        src, kind, op, ln = k.split('|')
        if src not in desks:
            out[f'{kind} {op} {ln}'] += n
    return out

def show(title, files):
    print(f'\n=== {title} ===')
    for f in sorted(files):
        r = by_file[f]
        d, b = deskops(r), boxops(r)
        print(f'\n{f}')
        print(f'  desk={r["desk_macs"]} box={r["box_macs"]} models={r["desk_models"]}->{r["box_models"]}')
        print(f'  frames={r["reac_frames"]}')
        print(f'  DESK ops: ' + ', '.join(f'{k}x{v}' for k, v in d.most_common()))
        print(f'  BOX  ops: ' + ', '.join(f'{k}x{v}' for k, v in b.most_common()))

show('GOLDEN (real M-200 -> real S-1608)', GOLDEN)
show('OURS (reac-pw -> real S-1608)', OURS)

# The set diff, unioned across each side
gd = collections.Counter()
for f in GOLDEN:
    gd.update(deskops(by_file[f]).keys())
od = collections.Counter()
for f in OURS:
    od.update(deskops(by_file[f]).keys())

print('\n\n=== DESK-SIDE OP SET DIFF ===')
print(f'golden captures: {len(GOLDEN)}   ours: {len(OURS)}')
print('\nONLY the real desk sends (present in >=1 golden, 0 of ours):')
for k in sorted(set(gd) - set(od)):
    print(f'  {k}   (in {gd[k]}/{len(GOLDEN)} goldens)')
print('\nONLY reac-pw sends:')
for k in sorted(set(od) - set(gd)):
    print(f'  {k}   (in {od[k]}/{len(OURS)} of ours)')
print('\nBOTH send:')
for k in sorted(set(od) & set(gd)):
    print(f'  {k}   golden {gd[k]}/{len(GOLDEN)}   ours {od[k]}/{len(OURS)}')
