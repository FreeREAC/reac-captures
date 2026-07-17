#!/usr/bin/env python3
"""Decode the M-200 scene-recall + head-amp sequence from a mirror-port capture.

Ground truth for the "complete scene" mechanism: at scene recall the M-200 pushes
EVERY channel's full head-amp state (phantom + pad + sens) as op-0403 records, then
issues incremental op-0403 changes on operator edits. A REAC master that wants the
box to apply head-amp must send this COMPLETE per-channel/per-param scene, not an
empty/partial one (an empty scene is why a takeover resets every channel to off).

Head-amp record: cdea 04 03 <oplen> ... 12 12 01 01 <CH> <PARAM> <VALUE> <cksum> f7
  CH    = 0x20 + (box_input-1)   (S-1608: 0x20..0x2f = reac1..reac16)
  PARAM = 0x00 phantom(48V) | 0x01 pad(-20dB) | 0x02 sens(0..0x37, 1 dB/step)
  SENS law: dBu = -10 - value + (pad ? 20 : 0)

Usage: decode_scene.py CAPTURE.pcap [desk_mac=0040abc9cc03]
"""
import struct, sys, collections

DESK = sys.argv[2] if len(sys.argv) > 2 else '0040abc9cc03'
PARAM = {0: 'phantom', 1: 'pad', 2: 'sens'}


def frames(path):
    f = open(path, 'rb'); f.read(24); hdr = f.read(16)
    while len(hdr) == 16:
        ts, tu, cap, orig = struct.unpack('<IIII', hdr)
        fr = f.read(cap); hdr = f.read(16)
        yield ts + tu / 1e6, fr


def headamp_records(fr):
    """yield (ch, param, value) for every head-amp record in a desk downstream frame."""
    if len(fr) < 20 or fr[12:14] != b'\x88\x19' or fr[6:12].hex() != DESK:
        return
    b = fr[14:]; i = 0
    while True:
        j = b.find(b'\xcd\xea', i)
        if j < 0:
            break
        if b[j+2:j+4] == b'\x04\x03':
            k = b.find(b'\x12\x12\x01\x01', j)
            if 0 <= k < j + 40:
                ch, pm, val = b[k+4], b[k+5], b[k+6]
                if 0x20 <= ch <= 0x2f and pm in PARAM:
                    yield ch, pm, val
        i = j + 2


def main():
    t0 = None
    scene = collections.defaultdict(dict)      # ch -> {param: value} (latest)
    initial = None                             # snapshot at first full population
    scene_done = None
    events = []                                 # (t, ch, param, value) transitions
    last = {}
    for t, fr in frames(sys.argv[1]):
        recs = list(headamp_records(fr))
        if not recs:
            continue
        if t0 is None:
            t0 = t
        for ch, pm, val in recs:
            if last.get((ch, pm)) != val:
                events.append((t - t0, ch, pm, val)); last[(ch, pm)] = val
            scene[ch][pm] = val
        if scene_done is None and len(scene) == 16 and all(len(v) == 3 for v in scene.values()):
            scene_done = t - t0
            initial = {ch: dict(v) for ch, v in scene.items()}

    def table(snap, title):
        print(f"# {title}")
        print("input  ch    phantom  pad  sens    dBu")
        for n in range(16):
            ch = 0x20 + n; s = snap.get(ch, {})
            ph, pa, se = s.get(0, 0), s.get(1, 0), s.get(2, 0)
            dbu = -10 - se + (20 if pa else 0)
            print(f"reac{n+1:<3} 0x{ch:02x}    {ph:^7} {pa:^4} 0x{se:02x}   {dbu:+d} dBu")
        print()

    table(initial, f"COMPLETE SCENE pushed at recall (16ch x 3 params, fully populated in {scene_done:.2f}s)")
    table(scene, "FINAL state after the operator toggle sequence (modified channels back to phantom off)")
    print(f"\n# {len(events)} head-amp transitions total; first change edges:")
    for t, ch, pm, val in events[:60]:
        print(f"  +{t:7.2f}s  reac{ch-0x20+1:<2} {PARAM[pm]:7} -> 0x{val:02x}")


if __name__ == '__main__':
    main()
