#!/usr/bin/env python3
"""Is opcode 0x9D ever sent, by anyone? And does the chanmap 0xFE value CHANGE?

Two questions from the firmware lane, answered over the whole corpus in one pass
(45 GB, so it reads each file exactly once).

Q1  FUN_0c02781e dispatches opcode 0x9D into FUN_0c0045ec, which writes the
    generation trigger when the incoming value DIFFERS. 0x9D is in neither
    reac.ksy nor libreac/src, so we have never sent it. Does a real desk?

    THE PROBE IS ITS OWN CONTROL. Rather than asking "is 0x9D present" -- a
    question whose negative answer is indistinguishable from a broken search --
    this takes a full CENSUS of every distinct byte value at every control-block
    offset. The same table that reports 0x9D's absence at an offset also lists
    the values that ARE there, proving the offset was read. A census that came
    back empty everywhere would be visibly broken.

Q2  The chanmap sentinel handler writes record[1] into the trigger with NO
    difference guard, and the apply path fires on an EDGE. So a CONSTANT value
    can never trigger it, whatever that constant is. Per desk generation the
    value is fixed (M-200/M-300 -> 0x00, M-5000 -> 0x01); the question now is
    whether it is fixed WITHIN A SESSION, or moves during establish / phases /
    head-amp bursts. Emitted here as a full timeline, not a set.

Chanmap records are 3-byte TRIPLETS (slot, val, pad) after a 1-byte page --
stride 3, not 2.

Usage: opcode_census.py [out.jsonl]
"""
import sys, os, glob, json, collections, multiprocessing

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reac_pcap as R

CTRL_LO, CTRL_HI = 16, 52
TARGET = 0x9D


def scan(path):
    off_vals = collections.defaultdict(set)      # control-block offset -> byte values
    ops = collections.Counter()
    dt1_tags = collections.Counter()
    nine_d = collections.Counter()               # where 0x9D turned up
    fe_timeline = []                             # (frame_idx, tick, value, src_is_master)
    fe_counts = collections.Counter()
    n_ctrl = n_other = n_frames = 0
    seq = collections.Counter()
    lens = collections.defaultdict(set)
    pending = []

    for idx, (ts, wl, fr) in enumerate(R.iter_packets(path)):
        if not R.is_reac(fr):
            continue
        n_frames += 1
        src = fr[6:12]
        seq[src] += 1
        lens[src].add(len(fr))
        ct = R.control(fr)
        if ct is None:
            n_other += 1
            continue
        n_ctrl += 1
        kind, op, oplen = ct
        ops[f'{kind} {op.hex()} {oplen:04x}'] += 1
        hi = min(len(fr), CTRL_HI)
        for o in range(CTRL_LO, hi):
            off_vals[o].add(fr[o])
            if fr[o] == TARGET:
                nine_d[o] += 1
        # 0x9D anywhere later in a long control frame, too
        for o in range(CTRL_HI, min(len(fr), 200)):
            if fr[o] == TARGET:
                nine_d[f'tail{o}'] += 1
        rec = R.dt1_record(fr)
        if rec:
            dt1_tags[rec['tag']] += 1
        if kind == 'cdea' and op == b'\x01\x03' and oplen == 0x19:
            tick = int.from_bytes(fr[14:16], 'little')
            for k in range(8):
                i = 23 + 3 * k
                if i + 2 < len(fr) and fr[i] == 0xFE:
                    pending.append((idx, ts, tick, fr[i + 1], src))
                    fe_counts[fr[i + 1]] += 1

    master = max(seq, key=lambda s: (max(lens[s]) >= 1492, seq[s])) if seq else None
    for idx, ts, tick, val, src in pending:
        fe_timeline.append([idx, round(ts, 6), tick, val, src == master])

    return {
        'file': os.path.relpath(path, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'n_frames': n_frames, 'n_control': n_ctrl, 'n_noncontrol': n_other,
        'ops': dict(ops),
        'dt1_tags': dict(dt1_tags),
        'nine_d': {str(k): v for k, v in nine_d.items()},
        'off_vals': {str(o): sorted(v) for o, v in sorted(off_vals.items())},
        'fe_counts': {str(k): v for k, v in fe_counts.items()},
        'fe_timeline': fe_timeline[:4000],
        'fe_n': len(fe_timeline),
    }


def safe(path):
    try:
        return scan(path)
    except Exception as e:
        return {'file': path, 'error': repr(e)}


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = sorted(glob.glob(os.path.join(root, '**', '*.pcap'), recursive=True))
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(root, 'analysis', 'opcode_census.jsonl')
    with multiprocessing.Pool(min(10, len(files))) as pool, open(out, 'w') as fh:
        for i, res in enumerate(pool.imap_unordered(safe, files), 1):
            fh.write(json.dumps(res) + '\n')
            fh.flush()
            print(f'[{i}/{len(files)}] {os.path.basename(res["file"])} '
                  f'{"ERR " + res["error"] if "error" in res else ""}', flush=True)
    print('wrote', out)


if __name__ == '__main__':
    main()
