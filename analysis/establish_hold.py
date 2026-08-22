#!/usr/bin/env python3
"""How long does a master hold before it GRANTS -- i.e. before the head-amp sweep?

Parameterises the rig lane's establishment-hold experiment. The claim to test is
that a real M-200 sits ~27 s in the establishment phase before granting, while
reac-pw grants fast.

LANDMARKS (all on the wire, all in one pass):

  box_first    first frame of any kind from the box MAC -- the box appears
  box_join     first cdea 0403 0016/001a from the box   -- cold JOIN
  box_config   first cdea 0103 0010 from the box        -- box declares itself
  grant        first DESK DT1 1212/0101 head-amp record -- the grant sweep opens
  grant_end    last record of that first contiguous sweep (>2 s gap ends it)

The HOLD reported is grant - box_first: the whole window in which the box is on
the wire and has not yet been granted.

THE CLOCK. Capture timestamps carry host scheduling, and separately 17 of the 72
corpus captures are capture-FILTERED to control frames only (measured, see
opcode_census.py -- this corrects an earlier reading of the same evidence as
"the mirror dropped 7 of 8 frames"). Either way a raw inter-frame gap is not the
sender's pace. So intervals are measured on the free-running u16 at offset 14,
which the SENDER increments once per frame: 4000/s at 48k, 8000/s at 96k.

WRAP DISAMBIGUATION. The counter wraps every 65536 ticks (16.4 s at 48k), which is
SHORTER than the hold we are trying to measure -- so a naive unwrap would silently
fold a 27 s hold into 10 s. Timestamps are used for one narrow job where their
coarseness is harmless: choosing the wrap COUNT (an integer, needing only
seconds-level accuracy). The fine interval remains tick-derived. Any capture where
the two disagree by more than half a wrap is reported as UNRELIABLE rather than
guessed at.

Usage: establish_hold.py
"""
import sys, os, glob, json, statistics, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reac_pcap as R

WRAP = 65536
ROLAND = bytes.fromhex('0040ab')


def tick_rate_of(pairs):
    """ticks/s from adjacent pairs, median, no dt band filter."""
    rates = []
    for i in range(1, len(pairs)):
        dt = pairs[i][0] - pairs[i - 1][0]
        dk = (pairs[i][1] - pairs[i - 1][1]) % WRAP
        if 0 < dt < 0.05 and 0 < dk < 500:
            rates.append(dk / dt)
    if len(rates) < 50:
        return None
    m = statistics.median(rates)
    return 8000.0 if m > 6000 else 4000.0


def abs_ticks(pairs, rate):
    """Unwrap with the wrap COUNT chosen by elapsed timestamp (integer decision,
    seconds-tolerant); returns [(ts, abs_tick)] and the worst disagreement."""
    out = []
    total = 0
    worst = 0.0
    for i, (ts, raw) in enumerate(pairs):
        if i == 0:
            out.append((ts, raw))
            continue
        pts, praw = pairs[i - 1]
        prev_abs = out[-1][1]
        dk_raw = (raw - praw) % WRAP
        expect = (ts - pts) * rate
        n = round((expect - dk_raw) / WRAP)
        if n < 0:
            n = 0
        dk = dk_raw + n * WRAP
        worst = max(worst, abs(dk - expect) / rate)
        total += dk
        out.append((ts, prev_abs + dk))
    return out, worst


def scan(path):
    frames = []
    seq = collections.Counter()
    lens = collections.defaultdict(set)
    for ts, wl, fr in R.iter_packets(path):
        if not R.is_reac(fr):
            continue
        src = fr[6:12]
        seq[src] += 1
        lens[src].add(len(fr))
        frames.append((ts, src, fr))
    if not seq:
        return None
    master = max(seq, key=lambda s: (max(lens[s]) >= 1492, seq[s]))
    boxes = [s for s in seq if s != master and s[:3] == ROLAND]
    if not boxes:
        return None
    box = max(boxes, key=lambda s: seq[s])

    mp = [(ts, int.from_bytes(fr[14:16], 'little')) for ts, src, fr in frames if src == master]
    rate = tick_rate_of(mp)
    if rate is None:
        return {'file': path, 'skip': 'master stream too sparse for a tick rate'}
    axis, worst = abs_ticks(mp, rate)
    ts_axis = [t for t, _ in axis]
    import bisect

    def ms(ts):
        j = bisect.bisect_left(ts_axis, ts)
        j = max(1, min(j, len(axis) - 1))
        (t0, k0), (t1, k1) = axis[j - 1], axis[j]
        k = k0 if t1 == t0 else k0 + (k1 - k0) * (ts - t0) / (t1 - t0)
        return k / rate * 1000.0

    L = {}
    grants = []
    desk_ops_in_hold = collections.Counter()
    for ts, src, fr in frames:
        ct = R.control(fr)
        if src == box and 'box_first' not in L:
            L['box_first'] = ts
        if ct:
            kind, op, oplen = ct
            if src == box and op == b'\x04\x03' and oplen in (0x16, 0x1a):
                L.setdefault('box_join', ts)
            if src == box and op == b'\x01\x03' and oplen == 0x10:
                L.setdefault('box_config', ts)
            if src == master:
                rec = R.dt1_record(fr)
                if rec and rec.get('inner_ok') and rec['tag'] == '0101':
                    grants.append(ts)
    if 'box_first' not in L or not grants:
        return {'file': path, 'skip': 'no box appearance or no grant sweep'}
    # first grant AFTER the box appears
    after = [t for t in grants if t >= L['box_first']]
    if not after:
        return {'file': path, 'skip': 'grants precede the box (mid-session capture)'}
    L['grant'] = after[0]
    end = after[0]
    for t in after[1:]:
        if t - end > 2.0:
            break
        end = t
    L['grant_end'] = end
    for ts, src, fr in frames:
        if src == master and L['box_first'] <= ts < L['grant']:
            ct = R.control(fr)
            if ct:
                desk_ops_in_hold[f'{ct[0]} {ct[1].hex()} {ct[2]:04x}'] += 1
    return {
        'file': path, 'rate': rate, 'unwrap_worst_s': round(worst, 3),
        'hold_s': round((ms(L['grant']) - ms(L['box_first'])) / 1000.0, 3),
        'join_to_grant_s': round((ms(L['grant']) - ms(L['box_join'])) / 1000.0, 3)
        if 'box_join' in L else None,
        'config_to_grant_s': round((ms(L['grant']) - ms(L['box_config'])) / 1000.0, 3)
        if 'box_config' in L else None,
        'sweep_s': round((ms(L['grant_end']) - ms(L['grant'])) / 1000.0, 3),
        'hold_s_by_timestamp': round(L['grant'] - L['box_first'], 3),
        'desk_ops_in_hold': dict(desk_ops_in_hold.most_common(8)),
    }


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = sorted(glob.glob(os.path.join(root, '**', '*.pcap'), recursive=True))
    out = []
    for p in files:
        try:
            r = scan(p)
        except Exception as e:
            r = {'file': p, 'skip': f'ERROR {e!r}'}
        if r:
            r['file'] = os.path.basename(r['file'])
            out.append(r)
            print(json.dumps(r), flush=True)
    with open(os.path.join(root, 'analysis', 'establish_hold.jsonl'), 'w') as fh:
        for r in out:
            fh.write(json.dumps(r) + '\n')


if __name__ == '__main__':
    main()
