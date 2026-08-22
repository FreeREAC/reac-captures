#!/usr/bin/env python3
"""EXHAUSTIVE wire-feature differential, not a search for a named suspect.

opdiff.py answers this question at ONE granularity -- (kind, op, oplen) -- and at
that granularity the S-1608 answer is already known and nearly empty. This goes
finer, because the thing we are missing is by definition something nobody has
thought to name: it enumerates every DT1 inner record tag, every slot/channel id,
every control sub-index and payload prefix present in one side's traffic and
absent from the other's, in both directions.

Three comparisons, the third being the one that isolates:

  A  real desk -> S-1608   vs  reac-pw -> S-1608     (what we fail to send)
  B  real desk -> S-0808   vs  real desk -> S-1608   (how the two boxes differ)
  C  the intersection: present for S-0808 under a real desk, present for S-1608
     under a real desk, absent from ours -- i.e. what real desks do for BOTH
     boxes that we do for neither.

COUNTS ARE NOT COMPARABLE ACROSS CAPTURE MODES, only PRESENCE is. Mirrored
captures in this corpus are decimated ~8:1 (see establish_pace.py: audio
arithmetic fixes the true rate at 4000 frames/s and mirrored files show 500),
while "clean" captures are complete. A feature's rate therefore says more about
the capture than the sender. Every verdict here is presence/absence over
captures, and the per-capture-count column is advisory only.

Usage: wire_vocab.py
"""
import sys, os, glob, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reac_pcap as R

STOP_AFTER = 400_000


def features(fr, is_desk):
    """Every token this frame contributes, at several granularities."""
    out = []
    ct = R.control(fr)
    if ct is None:
        return out
    kind, op, oplen = ct
    side = 'DESK' if is_desk else 'BOX '
    ophex = op.hex()
    out.append(f'{side} L1 op {kind} {ophex} {oplen:04x}')

    body = fr[22:50]
    if kind == 'cdea' and ophex == '0103':
        # sub-index / first payload byte distinguishes chanmap pages, config kinds
        out.append(f'{side} L4 0103.{oplen:04x} b0={fr[22]:02x}')
        if oplen == 0x0019:
            # oplen 25 = 1 page byte + 8 TRIPLETS (slot, val, 00). Stride is 3,
            # not 2: a stride-2 read produces plausible-looking but fictitious
            # slot ids (it lands on val and pad bytes).
            out.append(f'{side} L5 chanmap page={fr[22]:02x}')
            for k in range(8):
                i = 23 + 3 * k
                if i + 2 < 50:
                    out.append(f'{side} L6 chanmap slot={fr[i]:02x} val={fr[i+1]:02x}')
        if oplen == 0x0010:                      # box self-declaration
            out.append(f'{side} L5 boxconfig payload={body[:14].hex()}')

    if kind == 'cdea' and ophex in ('0100', '0101', '0102'):
        out.append(f'{side} L4 {ophex}.{oplen:04x} b0b1={fr[22]:02x}{fr[23]:02x}')

    if kind == 'cfea':
        # cfea ffff 0100: ... [27:33] master MAC, then a sizing pair at [33],[34]
        # (0x28 = the 40ch downstream braid; the second byte tracks box width),
        # then flags.
        out.append(f'{side} L4 announce sizing={fr[33]:02x},{fr[34]:02x}')
        out.append(f'{side} L8 announce flags={fr[35:39].hex()}')

    rec = R.dt1_record(fr)
    if rec:
        ok = 'ok' if rec['inner_ok'] else 'BAD'
        out.append(f'{side} L2 dt1 marker={rec["marker"]} tag={rec["tag"]} '
                   f'len={len(rec["data"])} {ok}')
        if rec['data']:
            out.append(f'{side} L3 dt1 tag={rec["tag"]} slot={rec["data"][0]:02x}')
        if len(rec['data']) >= 2:
            out.append(f'{side} L7 dt1 tag={rec["tag"]} nbytes={len(rec["data"])}')
    return out


def scan(path):
    counts = collections.Counter()
    seq = {}
    lens = {}
    frames = []
    for i, (ts, wl, fr) in enumerate(R.iter_packets(path)):
        if i > STOP_AFTER:
            break
        if not R.is_reac(fr):
            continue
        src = fr[6:12]
        seq[src] = seq.get(src, 0) + 1
        lens.setdefault(src, set()).add(len(fr))
        frames.append((src, fr))
    if not seq:
        return counts
    master = max(seq, key=lambda s: (max(lens[s]) >= 1492, seq[s]))
    for src, fr in frames:
        for t in features(fr, src == master):
            counts[t] += 1
    return counts


def group_of(base):
    ours = 'reacpw' in base
    pre = base.split('__')[0].split('-')
    box = pre[1] if len(pre) > 1 else '?'
    if box == 's1608':
        return ('ours_s1608' if ours else 'real_s1608')
    if box == 's0808':
        return ('ours_s0808' if ours else 'real_s0808')
    if box == 's4000s':
        return ('ours_s4000' if ours else 'real_s4000')
    return None


def main():
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'captures')
    groups = collections.defaultdict(list)      # group -> [(base, counts)]
    for p in sorted(glob.glob(os.path.join(root, '*.pcap'))):
        base = os.path.basename(p)
        g = group_of(base)
        if g is None:
            continue
        try:
            groups[g].append((base, scan(p)))
        except Exception as e:
            print(f'  !! {base}: {e}', file=sys.stderr)

    def present(g):
        """token -> number of captures in the group containing it."""
        d = collections.Counter()
        for base, c in groups.get(g, []):
            for t in c:
                d[t] += 1
        return d

    for g in sorted(groups):
        print(f'{g:12} {len(groups[g])} captures')

    def diff(title, a, b, na, nb):
        pa, pb = present(a), present(b)
        print(f'\n\n########  {title}  ########')
        print(f'  {na}: {len(groups.get(a, []))} captures    {nb}: {len(groups.get(b, []))} captures')
        only_a = sorted(t for t in pa if t not in pb)
        only_b = sorted(t for t in pb if t not in pa)
        print(f'\n--- PRESENT in {na}, ABSENT from {nb}  ({len(only_a)}) ---')
        for t in only_a:
            print(f'   [{pa[t]}/{len(groups.get(a, []))}] {t}')
        print(f'\n--- PRESENT in {nb}, ABSENT from {na}  ({len(only_b)}) ---')
        for t in only_b:
            print(f'   [{pb[t]}/{len(groups.get(b, []))}] {t}')

    diff('A. real desk -> S-1608   vs   reac-pw -> S-1608',
         'real_s1608', 'ours_s1608', 'REAL->1608', 'OURS->1608')
    diff('B. real desk -> S-0808   vs   real desk -> S-1608',
         'real_s0808', 'real_s1608', 'REAL->0808', 'REAL->1608')

    # C: what real desks send to BOTH boxes that we never send to the S-1608
    pr8, pr16, po16 = present('real_s0808'), present('real_s1608'), present('ours_s1608')
    both = sorted(t for t in pr16 if t in pr8 and t not in po16)
    print('\n\n########  C. real desks send to BOTH boxes, we send to NEITHER  ########')
    print(f'  ({len(both)} tokens)')
    for t in both:
        print(f'   [0808 {pr8[t]}, 1608 {pr16[t]}, ours 0] {t}')


main()
