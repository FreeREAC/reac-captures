#!/usr/bin/env python3
"""Condense placement_rows.jsonl into the placement evidence table (CSV + markdown)."""
import csv, json, os, sys

D = os.path.dirname(os.path.abspath(__file__))
rows = [json.loads(l) for l in open(os.path.join(D, 'placement_rows.jsonl'))]

FIELDS = ['file', 'desk', 'box_mac', 'box', 'cfg_selector', 'cfg_byte7',
          'cfg_in', 'cfg_out', 'cfea_width', 'up_nch', 'enroll_in_out',
          'chanmap', 'grant_base', 'grant_span', 'contiguous', 'live_edit_ch']

out = []
for r in rows:
    if not r.get('reac_frames'):
        continue
    cfg = r.get('box_cfg') or []
    blk = bytes.fromhex(cfg[0]['block']) if cfg else None
    eps = r.get('episodes') or []
    grants = [e for e in eps if e['n_ch'] >= 4]          # a sweep, not a live edit
    lives = [e for e in eps if e['n_ch'] < 4]
    cm = r.get('chanmap')
    out.append({
        'file': r['file'],
        'desk': ','.join(r.get('desk_models', [])),
        'box_mac': ','.join(r.get('box_macs', [])),
        'box': ','.join(r.get('box_models', [])),
        'cfg_selector': f'{blk[0]:#04x}' if blk else '',
        'cfg_byte7': f'{blk[3]:#04x}' if blk else '',
        'cfg_in': blk[4:16].count(2) * 4 if blk else '',
        'cfg_out': blk[4:16].count(1) * 4 if blk else '',
        'cfea_width': ','.join(sorted({str(c['width']) for c in r.get('cfea', [])})),
        'up_nch': ','.join(sorted({str(a['nch']) for a in r.get('audio', [])})),
        'enroll_in_out': ','.join(sorted({f"{e['in_groups']}i/{e['out_groups']}o"
                                          for e in r.get('enroll', [])})),
        'chanmap': f"{cm['span']}/{cm['n_slots']}" if cm else '',
        'grant_base': ','.join(sorted({f"{g['base']:#04x}" for g in grants})),
        'grant_span': ','.join(sorted({str(g['n_ch']) for g in grants})),
        'contiguous': ','.join(sorted({str(g['contiguous']) for g in grants})),
        'live_edit_ch': ','.join(sorted({f"{e['base']:#04x}" for e in lives})),
    })

with open(os.path.join(D, 'placement_table.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, FIELDS)
    w.writeheader()
    w.writerows(out)
print(f'{len(out)} rows -> placement_table.csv')

usable = [r for r in out if r['grant_base']]
print(f'\nrows with a GRANT SWEEP (usable placement tuple): {len(usable)}')
hdr = ['file', 'desk', 'box', 'cfg_selector', 'cfg_byte7', 'cfg_in',
       'enroll_in_out', 'grant_base', 'grant_span']
print(' | '.join(hdr))
for r in sorted(usable, key=lambda x: (x['box'], x['file'])):
    print(' | '.join(str(r[h]) for h in hdr))
