#!/usr/bin/env python3
"""TASK #210 — fabric-slot PLACEMENT evidence extractor.

For every capture in the corpus, pull the full placement tuple:

  desk model | box model | DECLARED width (cfea + upstream frame size + box CONFIG)
  | ENROLL group map (cdea 0103 000d) | CHANMAP coverage (cdea 0103 0019)
  | the grant sweep's group-A head-amp CH span (the ACTUAL base the master
    addresses this box at) | live head-amp CH edits | box identity records

Streaming: reac_pcap.iter_packets never holds more than one 4 MB chunk.

Emits JSONL (one row per capture) + a human table. Run:
    placement_scan.py [--out DIR] [capture ...]
"""
import collections, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reac_pcap as R

# Desks are identified by their L2 source MAC (MIXER-VS-BOX-MATRIX.md: the cfea
# announce block [9:15] repeats the L2 source, and the model is stable per unit).
DESK_MAC = {
    '00:40:ab:c9:cc:03': 'M-200i',
    '00:40:ab:c9:d8:5b': 'M-300',
    '00:40:ab:ca:15:4c': 'M-5000',
}
BOX_MAC = {
    '00:40:ab:c4:80:3b': 'S-1608',
    '00:40:ab:c4:dc:9c': 'S-0808',
    '00:40:ab:c4:06:80': 'S-4000S#1',
    '00:40:ab:c4:08:bc': 'S-4000S#2',
    # The rig's own S-1608 (base 0x20), NOT a stand-in: HEADAMP-S1608-STATE-DIAGRAM
    # -2026-07-19 and UPPER-BANK-2026-08-21 both identify c4:80:41 as the real box.
    # The old 'reac-pw(slave stand-in)' label made every table over this rig unreadable.
    '00:40:ab:c4:80:41': 'S-1608#2',
    '00:40:ab:c9:cc:04': 'reac-pw(master stand-in)',
}

# Upstream audio frame length -> channel count: len = 52 + nch*36 (m200-s4000-width-re
# FINDINGS.md). The mirror tap adds +2 (Ethernet FCS), so accept len and len-2.
def nch_from_len(n):
    for cand in (n, n - 2):
        if cand >= 52 and (cand - 52) % 36 == 0:
            c = (cand - 52) // 36
            if 1 <= c <= 40:
                return c
    return None


def scan(path):
    row = {
        'file': os.path.basename(path),
        'bytes': os.path.getsize(path),
        'packets': 0, 'reac': 0,
        'macs': collections.Counter(),
        'cfea': collections.Counter(),      # (fabric, width, console, boxcount) -> n
        'enroll': collections.Counter(),    # (console, region hex) -> n
        'chanmap_slots': set(),
        'audio': collections.Counter(),     # (src, framelen) -> n
        'groupa': collections.defaultdict(collections.Counter),  # (desk,phase) -> CH
        'groupb': collections.Counter(),
        'box_join': collections.Counter(),  # (src, tag, oplen, data hex)
        'box_cfg': collections.Counter(),   # cdea 0103 0010 from a box
        'ops': collections.Counter(),
        'error': None,
    }
    # The grant burst is the contiguous run of 1212/0101 records that follows a
    # 1212/0100 master ACK; a LIVE edit is an isolated one in steady state. We
    # separate them by gap: >2 s from the previous 0101 starts a new episode.
    episodes = []           # list of dict(t0, t1, src, chs Counter)
    last0101 = {}
    try:
        for ts, wl, fr in R.iter_packets(path):
            row['packets'] += 1
            if not R.is_reac(fr):
                continue
            row['reac'] += 1
            src = R.mac(fr[6:12])
            row['macs'][src] += 1
            ct = R.control(fr)
            if ct is None:
                row['audio'][(src, len(fr))] += 1
                continue
            kind, op, oplen = ct
            row['ops'][(src, kind, op.hex(), f'{oplen:04x}')] += 1
            if kind == 'cfea':
                # gen_cfea template coords: out[17] fabric, [18] width, [19] console,
                # [20:22] box count.  out[] starts at frame offset 16.
                row['cfea'][(fr[33], fr[34], fr[35],
                             int.from_bytes(fr[36:38], 'big'))] += 1
                continue
            if op == b'\x01\x03':
                if oplen == 0x000d:                     # ENROLL group map
                    row['enroll'][(fr[24], fr[25:35].hex())] += 1
                elif oplen == 0x0019:                   # CHANMAP window
                    # blk[6]=payload type, then 8 x 3-byte slot records at blk[7]
                    # (reac_master.c gen_chanmap); blk index = frame offset - 16.
                    for i in range(8):
                        t = 23 + i * 3
                        row['chanmap_slots'].add((fr[t], fr[t + 1]))
                elif oplen == 0x0010:                   # box CONFIG announce
                    row['box_cfg'][(src, fr[22:40].hex())] += 1
                continue
            d = R.dt1_record(fr)
            if d is None:
                continue
            key = (src, d['marker'], d['tag'])
            if d['marker'] == '1212' and d['tag'] == '0101':
                ch = d['data'][0]
                prev = last0101.get(src)
                if prev is None or ts - prev > 2.0:
                    episodes.append({'t0': ts, 't1': ts, 'src': src,
                                     'chs': collections.Counter()})
                last0101[src] = ts
                ep = next(e for e in reversed(episodes) if e['src'] == src)
                ep['t1'] = ts
                ep['chs'][ch] += 1
            elif d['marker'] == '1211':
                row['groupb'][(src, d['tag'], d['data'].hex())] += 1
            else:
                row['box_join'][(src, d['marker'], d['tag'], d['oplen'],
                                 d['data'].hex())] += 1
    except Exception as e:                      # truncated/rotated captures exist
        row['error'] = f'{type(e).__name__}: {e}'

    # ---- condense -------------------------------------------------------
    out = {'file': row['file'], 'bytes': row['bytes'], 'packets': row['packets'],
           'reac_frames': row['reac'], 'error': row['error']}
    desks = [m for m in row['macs'] if m in DESK_MAC or m.startswith('00:40:ab:c9')
             or m.startswith('00:40:ab:ca')]
    # A desk is whatever sourced cfea; fall back to the MAC table.
    cfea_src = {s for (s, k, o, l) in row['ops'] if k == 'cfea'}
    out['desk_macs'] = sorted(cfea_src) or sorted(desks)
    out['desk_models'] = sorted({DESK_MAC.get(m, '?' + m) for m in out['desk_macs']})
    hb_src = {s for (s, k, o, l) in row['ops'] if k == 'cdea' and o == '0103' and l == '0001'}
    join_src = {s for (s, m, t, ol, dh) in row['box_join']}
    box_macs = sorted((hb_src | join_src | set(row['box_cfg'] and
                       {s for (s, h) in row['box_cfg']} or set())) - cfea_src)
    out['box_macs'] = box_macs
    out['box_models'] = sorted({BOX_MAC.get(m, '?' + m) for m in box_macs})

    out['cfea'] = [{'fabric': f, 'width': w, 'console': c, 'boxcount': b, 'n': n}
                   for (f, w, c, b), n in sorted(row['cfea'].items())]
    out['enroll'] = [{'console': c, 'region': h,
                      'in_groups': h[:10].count('41') if False else
                      bytes.fromhex(h)[0:5].count(0x41),
                      'out_groups': bytes.fromhex(h)[5:10].count(0xc3),
                      'n': n}
                     for (c, h), n in sorted(row['enroll'].items())]
    cm = row['chanmap_slots']
    out['chanmap'] = None
    if cm:
        slots = sorted({s for s, v in cm if s != 0xfe})
        out['chanmap'] = {
            'span': f'{slots[0]:#04x}-{slots[-1]:#04x}', 'n_slots': len(slots),
            'vals': sorted({f'{s:#04x}:{v:#04x}' for s, v in cm
                            if v not in (0x28,) or s > 0x27})[:12],
        }
    up = collections.Counter()
    for (s, ln), n in row['audio'].items():
        c = nch_from_len(ln)
        if c is not None:
            up[(s, ln, c)] += n
    out['audio'] = [{'src': s, 'len': ln, 'nch': c, 'n': n}
                    for (s, ln, c), n in sorted(up.items(), key=lambda x: -x[1])][:8]
    out['episodes'] = []
    for e in episodes:
        chs = sorted(e['chs'])
        out['episodes'].append({
            'src': e['src'], 'dur_s': round(e['t1'] - e['t0'], 3),
            'n_records': sum(e['chs'].values()), 'n_ch': len(chs),
            'base': chs[0], 'top': chs[-1],
            'contiguous': chs == list(range(chs[0], chs[0] + len(chs))),
            'chs': [f'{c:#04x}' for c in chs] if len(chs) <= 40 else None,
        })
    out['groupb'] = [{'src': s, 'tag': t, 'data': d, 'n': n}
                     for (s, t, d), n in sorted(row['groupb'].items())]
    out['box_join'] = [{'src': s, 'marker': m, 'tag': t, 'oplen': ol, 'data': d, 'n': n}
                       for (s, m, t, ol, d), n in sorted(row['box_join'].items())]
    out['box_cfg'] = [{'src': s, 'block': h, 'n': n}
                      for (s, h), n in sorted(row['box_cfg'].items())]
    out['ops'] = {f'{s}|{k}|{o}|{l}': n for (s, k, o, l), n in
                  sorted(row['ops'].items(), key=lambda x: -x[1])}
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    outdir = os.path.dirname(os.path.abspath(__file__))
    if not args:
        base = '/home/pau/Devel/audio/reac-captures'
        args = []
        for d in ('captures', 'm200-headamp-re', 'm200-s1608-headamp',
                  'm200-scene-recall-re'):
            p = os.path.join(base, d)
            if os.path.isdir(p):
                args += [os.path.join(p, f) for f in sorted(os.listdir(p))
                         if f.endswith(('.pcap', '.pcapng')) or '.pcap' in f]
    rows = []
    for p in args:
        if not os.path.isfile(p):
            continue
        sys.stderr.write(f'{os.path.basename(p):60s} {os.path.getsize(p)/1e6:9.1f} MB ... ')
        sys.stderr.flush()
        try:
            r = scan(p)
        except Exception as e:
            r = {'file': os.path.basename(p), 'bytes': os.path.getsize(p),
                 'error': f'{type(e).__name__}: {e}'}
        r['path'] = p
        rows.append(r)
        eps = r.get('episodes') or []
        sys.stderr.write(f"{r.get('reac_frames', 0)} reac, "
                         f"{len(eps)} groupA episode(s)"
                         + (f", err={r['error']}" if r.get('error') else '') + '\n')
    with open(os.path.join(outdir, 'placement_rows.jsonl'), 'w') as f:
        for r in rows:
            f.write(json.dumps(r) + '\n')
    print(f'\nwrote {len(rows)} rows -> {outdir}/placement_rows.jsonl')


if __name__ == '__main__':
    sys.exit(main())
