#!/usr/bin/env python3
"""Derive a capture's name from what is IN it, not from what someone called it.

"Capture filenames are not evidence" (operator, 2026-08-21) — so make them
evidence. Every field below is measured from the frames:

  mixer  the desk identity ON THE WIRE, by source MAC of the cfea announcer.
         This is what the segment was TOLD, which is the fact that matters; when
         reac-pw impersonated a desk MAC the wire really did carry that identity.
         Our own NIC MAC prints as `reacpw`.
  box    by source MAC, cross-checked against the declared port table in the
         box's own config-announce (libreac reac_ports: 0x02 = 4-in group,
         0x01 = 4-out, 0x03 = empty) wherever one appears in the window.
  rate   the desk's frame rate DEDUPED by the counter at frame[14:16], times 12.
         Counting raw frames through a mirrored tap doubles it — that artifact
         has now caused two wrong conclusions in this repo.
  tap    `mirror` when a large fraction of frames are same-counter copies,
         `clean` otherwise. It is a property of the capture rig, and a reader
         needs it before trusting any rate or per-frame count.

Usage:
  name_from_facts.py            # dry run: print the proposed mapping
  name_from_facts.py --apply    # git mv into the derived names
"""
import collections, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reac_pcap as R

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS = ('captures', 'm200-headamp-re', 'm200-s1608-headamp',
        'm200-s4000-width-re', 'm200-scene-recall-re')
LIMIT = 60000            # frames per capture: plenty for rate, tap and identity

DESK = {'00:40:ab:c9:cc:03': 'm200i', '00:40:ab:c9:d8:5b': 'm300',
        '00:40:ab:ca:15:4c': 'm5000', '00:40:ab:c9:cc:04': 'reacpw',
        '00:40:ab:00:00:01': 'reacpw'}
BOX = {'00:40:ab:c4:80:3b': 's1608', '00:40:ab:c4:80:41': 's1608',
       '00:40:ab:c4:dc:9c': 's0808', '00:40:ab:c4:06:80': 's4000s',
       '00:40:ab:c4:08:bc': 's4000s'}
PORT_IN, PORT_OUT, PORT_EMPTY, CH_PER = 0x02, 0x01, 0x03, 4
GEOM = {(16, 8): 's1608', (8, 8): 's0808', (32, 8): 's4000s'}


def scan(path):
    f = {'desks': collections.Counter(), 'boxes': collections.Counter(),
         'ctr': collections.Counter(), 'declared': collections.Counter(),
         'dframes': 0, 't0': None, 't1': None, 'ours': 0, 'slopes': collections.defaultdict(list),
         'ctr_by': collections.defaultdict(collections.Counter)}
    prev = {}
    n = 0
    for ts, wl, fr in R.iter_packets(path):
        n += 1
        if n > LIMIT:
            break
        if not R.is_reac(fr):
            continue
        src = R.mac(fr[6:12])
        if f['t0'] is None:
            f['t0'] = ts
        f['t1'] = ts
        if src.startswith('34:5a:60'):
            f['ours'] += 1
        c = R.control(fr)
        if c and c[0] == 'cfea':
            f['desks'][src] += 1
        if c and c[1] == b'\x01\x03' and c[2] == 0x0010 and len(fr) > 38:
            t = fr[26:38]
            if len(t) == 12 and all(x in (PORT_IN, PORT_OUT, PORT_EMPTY) for x in t):
                f['declared'][(src, sum(x == PORT_IN for x in t) * CH_PER,
                               sum(x == PORT_OUT for x in t) * CH_PER)] += 1
        if src in BOX:
            f['boxes'][src] += 1
        if src in DESK or (f['desks'] and src in f['desks']):
            f['dframes'] += 1
            ctr = int.from_bytes(fr[14:16], 'little')
            f['ctr'][ctr] += 1
            f['ctr_by'][src][ctr] += 1
            pc, pt = prev.get(src, (None, None))
            if pc is not None:
                dt = ts - pt
                dc = (ctr - pc) & 0xFFFF
                if 0 < dt < 0.5 and dc:
                    f['slopes'][src].append(dc / dt)
            prev[src] = (ctr, ts)
    return f


def facts(path):
    f = scan(path)
    dur = (f['t1'] - f['t0']) if (f['t0'] is not None and f['t1'] and f['t1'] > f['t0']) else 0
    desk_mac = f['desks'].most_common(1)[0][0] if f['desks'] else None
    # An unknown desk is named by its ADDRESS, not lumped as "other": the corpus
    # holds more desks than the three we can name (ca:15:4d appears to be a second
    # REAC port on the M-5000; c9:91:9c/9d are the zoneA/zoneB pair), and a label
    # that hides which one it was is the same defect as a filename that lies.
    if desk_mac is None:
        mixer = 'unk'
    elif desk_mac.startswith('34:5a:60'):
        mixer = 'reacpw'
    else:
        mixer = DESK.get(desk_mac, 'desk' + desk_mac.replace(':', '')[-6:])
    # box: declared geometry wins, MAC is the fallback
    box = 'none'
    if f['declared']:
        (_, i, o), _ = f['declared'].most_common(1)[0]
        box = GEOM.get((i, o), f'{i}x{o}')
    elif f['boxes']:
        names = {BOX[m] for m in f['boxes']}
        box = names.pop() if len(names) == 1 else 'multi'
    # Everything below describes the ANNOUNCING desk, not a pool of whatever
    # desks happened to be on the segment — two of them share a capture more
    # often than you would think, and pooling their counters yields a rate that
    # belongs to neither.
    ctr = f['ctr_by'].get(desk_mac) or f['ctr']
    distinct = len(ctr)
    total = sum(ctr.values())
    dup = 1 - distinct / total if total else 0
    tap = 'mirror' if dup > 0.25 else 'clean'
    # RATE FROM THE COUNTER, NOT FROM THE PACKET RATE. Many captures in this
    # corpus were recorded through a BPF filter (control frames only), so frames
    # per second measures the FILTER and comes out as 20..150 fps. The free-running
    # counter at frame[14:16] advances once per frame at the true pace whether or
    # not we captured that frame, so the pace is its ADVANCE per second — taken
    # between closely spaced frames (dt < 0.5 s) so a 16-bit wrap cannot be
    # mistaken for progress, and as a MEDIAN so a reordered or duplicated pair
    # cannot drag it.
    rate = 'unk'
    slopes = sorted(f['slopes'].get(desk_mac, []))
    if slopes:
        hz = slopes[len(slopes) // 2] * 12
        for cand in (44100, 48000, 96000):
            if abs(hz - cand) <= cand * 0.12:
                rate = {44100: '44k1', 48000: '48k', 96000: '96k'}[cand]
    return {'mixer': mixer, 'box': box, 'rate': rate, 'tap': tap,
            'dup_pct': round(dup * 100), 'desk_frames': total, 'seconds': round(dur, 1)}


def derived_name(old, fx):
    base = os.path.basename(old)
    stem, ext = base, ''
    for e in ('.pcap', '.pcapng'):
        if base.endswith(e):
            stem, ext = base[:-len(e)], e
            break
    if not ext:                      # split files like foo.pcap00
        i = base.find('.pcap')
        stem, ext = base[:i], base[i:]
    # keep the human descriptor, drop nothing
    return f"{fx['mixer']}-{fx['box']}-{fx['rate']}-{fx['tap']}__{stem}{ext}"


def main():
    apply = '--apply' in sys.argv
    rows = []
    for d in DIRS:
        p = os.path.join(ROOT, d)
        if not os.path.isdir(p):
            continue
        for name in sorted(os.listdir(p)):
            if '.pcap' not in name:
                continue
            old = os.path.join(p, name)
            if not os.path.isfile(old):
                continue
            try:
                fx = facts(old)
            except Exception as e:
                print(f'  SKIP {d}/{name}: {type(e).__name__}: {e}')
                continue
            new = derived_name(old, fx)
            rows.append({'dir': d, 'old': name, 'new': new, **fx})
            print(f"  {d}/{name}\n     -> {new}   ({fx['dup_pct']}% dup, "
                  f"{fx['desk_frames']} desk frames, {fx['seconds']}s)")
    with open(os.path.join(ROOT, 'analysis', 'capture_facts.jsonl'), 'w') as fh:
        for r in rows:
            fh.write(json.dumps(r) + '\n')
    print(f'\n{len(rows)} captures; facts -> analysis/capture_facts.jsonl')
    if not apply:
        print('dry run — pass --apply to git mv into these names')
        return 0
    for r in rows:
        if r['new'] == r['old']:
            continue
        src = os.path.join(ROOT, r['dir'], r['old'])
        dst = os.path.join(ROOT, r['dir'], r['new'])
        if os.path.exists(dst):
            print(f'  EXISTS, skipped: {r["new"]}')
            continue
        rc = subprocess.run(['git', '-C', ROOT, 'mv', '--', src, dst]).returncode
        if rc != 0:      # untracked file: plain rename
            os.rename(src, dst)
    print('renamed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
