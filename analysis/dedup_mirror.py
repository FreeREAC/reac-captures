#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Pau Aliagas <linuxnow@gmail.com>
"""Strip a mirrored capture down to one copy of each frame.

A switch mirror port hands the capture the SAME frame twice: once clean and once
with two bytes of the capture's own Ethernet FCS left on the end. `spec/reac.ksy`
states the geometry that makes this decidable rather than heuristic —

    14 B ethernet | 2 B counter | 2 B type | 32 B control [18:50]
    | n_channels * 36 B audio | 2 B C2 EA end marker | [2 B FCS residue]

so a REAL frame is `52 + n*36` bytes (40ch downstream = 1492, 16ch upstream = 628,
8ch = 340, 32ch = 1204) and the same frame carrying FCS residue is that plus two.
The residue is not protocol: the grammar strips it and does not model it.

WHY THIS MATTERS BEYOND TIDINESS. Every per-op count taken from a mirrored file is
inflated, and not uniformly — a frame present in both copies counts twice while one
present in a single copy counts once. Comparing OUR traffic (captured off a plain
NIC) against a mirrored corpus capture therefore compares a deduplicated stream with
a doubled one, and the arithmetic quietly favours whichever side was mirrored. Dedup
first, then count.

The end marker is the check that keeps this honest: after stripping, bytes [-2:] of
every kept frame must be C2 EA. A file that does not satisfy that is not a REAC
capture shaped the way this tool assumes, and it says so instead of writing a
plausible-looking output.
"""
import struct
import sys

sys.path.insert(0, __file__.rsplit('/', 1)[0])
from reac_pcap import PCAP_MAGICS  # noqa: E402  (same directory, shared reader)

END_MARKER = b'\xc2\xea'


def canonical_len(n: int) -> bool:
    """A frame length the geometry allows: 52 + n_channels*36."""
    return n >= 52 and (n - 52) % 36 == 0


def strip(frame: bytes) -> bytes | None:
    """The frame without FCS residue, or None when it fits no declared width."""
    if canonical_len(len(frame)):
        return frame
    if canonical_len(len(frame) - 2):
        return frame[:-2]
    return None


def main(src: str, dst: str) -> int:
    with open(src, 'rb') as f, open(dst, 'wb') as out:
        gh = f.read(24)
        if len(gh) < 24 or gh[:4] not in PCAP_MAGICS:
            print(f'{src}: not a classic pcap', file=sys.stderr)
            return 2
        endian, tsdiv = PCAP_MAGICS[gh[:4]]
        out.write(gh)
        rh = struct.Struct(endian + 'IIII')
        kept = dropped = odd = 0
        prev = None
        while True:
            hdr = f.read(16)
            if len(hdr) < 16:
                break
            ts_s, ts_f, caplen, wirelen = rh.unpack(hdr)
            frame = f.read(caplen)
            if len(frame) < caplen:
                break
            body = strip(frame)
            if body is None:
                odd += 1
                continue
            if body == prev:                 # the mirror's second copy
                dropped += 1
                continue
            if not body.endswith(END_MARKER):
                odd += 1
                continue
            prev = body
            out.write(struct.pack(endian + 'IIII', ts_s, ts_f, len(body), len(body)))
            out.write(body)
            kept += 1
    total = kept + dropped + odd
    print(f'  {src.rsplit("/", 1)[-1]}')
    print(f'    kept {kept}, dropped {dropped} mirror copies, {odd} unrecognised '
          f'({100 * dropped // total if total else 0}% of the file was duplication)')
    if kept == 0:
        print('    NOTHING KEPT — the geometry did not match; treat this file as unread',
              file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: dedup_mirror.py <in.pcap> <out.pcap>', file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
