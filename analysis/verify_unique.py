#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Pau Aliagas <linuxnow@gmail.com>
"""Prove a capture holds each frame ONCE — and that we parsed it right.

Every REAC frame carries a free-running u16 LITTLE-endian counter at offset 14
(`spec/reac.ksy`), incremented by its sender. So within one source MAC the counter
is a serial number, and two frames sharing one is either the mirror's second copy or
a parse that lost its place. That makes uniqueness a TEST rather than a hope:

  - step 0 (the counter does not advance) -> a duplicate: the mirror's second copy
  - step 1                                -> the stream is intact and in order
  - any other step                        -> a GAP; frames the capture genuinely
    missed (a mirror port drops under load). Reported, never treated as an error.

THE COUNTER IS u16 AND WRAPS EVERY 65536 FRAMES, so "have I seen this counter
before" is NOT a duplicate test — a 475k-frame capture reuses every counter about
seven times over, legitimately. Asking that question flags a third of a clean file
as broken (measured, 2026-08-22, on the first draft of this script). The STEP between
consecutive frames of one source is the honest signal, because it is local and wrap
is just another step value.

The step histogram is the real verdict. A clean capture is overwhelmingly step=1
with a handful of wraps; anything with a fat step=0 bar has not been deduped, and
anything with steps scattered across many values is not being parsed as REAC at all.

Reads the RAW stream (keep_mirror_copies=True) — it must see both copies to judge
them. The reader drops them for every OTHER consumer.

Run it on the OUTPUT of dedup_mirror.py. Reporting "0 duplicates" on a file the
reader could not parse would be the same false null this corpus has produced before,
so a file that yields no frames is a FAILURE here, never a pass.
"""
import collections
import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from reac_pcap import iter_packets  # noqa: E402
from dedup_mirror import strip    # noqa: E402  (compare frames without FCS residue)


def verify(path: str) -> bool:
    steps = collections.Counter()
    last_ctr, last_body = {}, {}
    repeats = collections.Counter()      # step 0 AND identical bytes: a real duplicate
    stutter = collections.Counter()      # step 0 but DIFFERENT bytes: a mis-parse
    total = 0
    for ts, wirelen, frame in iter_packets(path, keep_mirror_copies=True):
        if len(frame) < 50 or frame[12:14] != b'\x88\x19':
            continue
        total += 1
        src = frame[6:12].hex(':')
        ctr = frame[14] | (frame[15] << 8)
        body = strip(bytes(frame)) or bytes(frame)   # FCS residue is not a difference
        if src in last_ctr:
            step = (ctr - last_ctr[src]) & 0xffff
            steps[step] += 1
            if step == 0:
                (repeats if body == last_body[src] else stutter)[src] += 1
        last_ctr[src], last_body[src] = ctr, body
    name = path.rsplit('/', 1)[-1]
    if total == 0:
        print(f'  {name}: NO REAC FRAMES READ - not a pass, the file was not parsed')
        return False
    dup, mis = sum(repeats.values()), sum(stutter.values())
    ok = dup == 0 and mis == 0
    ordered = steps.get(1, 0)
    gaps = total - 1 - ordered - steps.get(0, 0)
    print(f'  {"OK " if ok else "BAD"} {name[:52]:<54} frames={total:<8} '
          f'in-order={ordered:<8} dupes={dup:<6} mis-parse={mis:<5} gaps={gaps}')
    if mis:
        print('       ^ counter did not advance but the bytes differ: MIS-PARSE, not duplication')
    return ok


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: verify_unique.py <pcap>...', file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(0 if all([verify(p) for p in sys.argv[1:]]) else 1)
