#!/usr/bin/env python3
"""Does a real desk ever ENROLL an S-1608?

The control that makes the absence meaningful: an ENROLL (cdea 0103 000d) is only
ever sent at cold-connect, so only captures that CONTAIN an establishment can
testify. A capture contains one iff the box sourced a CONFIG announce
(cdea 0103 0010) or a JOIN (0403 0016/001a/0013/0014) in it.

Restricted to that set, the question is: which desk->box pairs carry an ENROLL.
"""
import json, collections

rows = [json.loads(l) for l in open('/home/pau/Devel/audio/reac-captures/analysis/placement_rows.jsonl')]

def ops(r):
    return r.get('ops') or {}

def has_establishment(r):
    desks = set(r.get('desk_macs') or [])
    for k in ops(r):
        src, kind, op, ln = k.split('|')
        if src in desks:
            continue
        if (op, ln) == ('0103', '0010'):          # box CONFIG announce
            return True
        if op == '0403' and ln in ('0016', '001a'):  # box cold JOIN
            return True
    return False

def enroll_n(r):
    return sum(n for k, n in ops(r).items() if k.split('|')[2:4] == ['0103', '000d'])

def is_ours(f):
    return f.startswith('reacpw') or 'reacpw' in f

def family(r):
    """Box family, collapsing the two S-1608 units and the two S-4000S units."""
    m = '/'.join(r.get('box_models') or []) or '?'
    for fam in ('S-1608', 'S-0808', 'S-4000S'):
        if fam in m:
            return fam
    return m


print(f'{"capture":52} {"desk":10} {"box":12} {"src":8} {"ENROLL":>7}')
print('-' * 95)
# Single-box captures only: with two boxes on the segment an ENROLL cannot be
# attributed to either of them (m200-s0808-establish-switch carries both).
with_est = [r for r in rows if has_establishment(r) and len(r.get('box_macs') or []) == 1]
print(f'(dropped {sum(1 for r in rows if has_establishment(r)) - len(with_est)} '
      f'multi-box captures as unattributable)')
for r in sorted(with_est, key=lambda r: (family(r), r['file'])):
    side = 'reac-pw' if is_ours(r['file']) else 'REAL'
    print(f'{r["file"][:52]:52} {"/".join(r.get("desk_models") or [])[:10]:10} '
          f'{"/".join(r.get("box_models") or [])[:12]:12} {side:8} {enroll_n(r):>7}')

print('\n=== captures WITH an establishment that carry an ENROLL ===')
seen = collections.defaultdict(lambda: [0, 0])   # (family, side) -> [with, total]
for r in with_est:
    side = 'reac-pw' if is_ours(r['file']) else 'REAL'
    cell = seen[(family(r), side)]
    cell[1] += 1
    if enroll_n(r):
        cell[0] += 1
for (fam, side), (n, total) in sorted(seen.items()):
    print(f'  {fam:10} {side:8} {n}/{total}')
