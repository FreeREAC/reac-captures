# What a real desk sends an S-1608 that reac-pw does not

**CORRECTED 2026-08-22 by the operator, and this correction is the whole point of the
document.** An earlier draft framed the S-1608's head-amp silence as a possible UNIT FAULT
and proposed sending it for service. That is refuted by direct operator experience:

> "S-1608 is working perfectly. We have setup 48V in the first 8 ports and in the last.
> I use it with real mixers."

So the boot-sampled-strap hypothesis (`FUN_0c00f6b4` ∈ {0,1} gating both the head-amp
hardware path and the apply command, decoded once at boot from two I/O-expander bits) does
NOT explain what we see. Whatever it does in the firmware, it is not what stops OUR master.
**The divergence is ours.** Everything below is aimed at finding it.

Box: **S-1608 `00:40:ab:c4:80:41`** (the rig's own unit — not `c4:80:3b`, the corpus's other
S-1608).

---

## The shape of the problem

| | head-amp under reac-pw | head-amp under a real mixer |
|---|---|---|
| S-0808 `c4:dc:9c` | **works** — 8/8 inputs, +20.0…+37.1 dB | works |
| S-1608 `c4:80:41` | **0 of 16**, every delta within ±0.8 dB | **works, both banks** |

Measured 2026-08-22, both boxes, same console, same code path, same night
(`box_headamp_verdict.sh`), with the S-0808 as an in-run positive control. Through the
console's own door as well: `PATCH /api/channel/input/3/headAmp` moved the S-0808's wire slot
by +20.2 dB and restored exactly, while the same row on the S-1608 returned `ok:true` for
every value and moved the wire 0.2 dB.

Read the table by column and it says "the unit is fine". Read it by row and it says "reac-pw
is fine". Both are true, so **the missing thing is something the S-1608 needs and the S-0808
does not, which real mixers send and reac-pw does not.**

That is a well-posed question with the evidence already in this corpus.

## Question 1 — the op-set diff (no new capture needed to START)

`analysis/opdiff.py` exists for exactly this: "what a real desk sends an S-1608 that reac-pw
never sends", reading the committed `analysis/placement_rows.jsonl` without rescanning pcaps.
Its discriminator is the FILENAME PREFIX, not the source MAC, because reac-pw impersonated
the real M-200 MAC `00:40:ab:c9:cc:03` in the July runs — a desk MAC is not proof of a desk.

Goldens where a real desk drove an S-1608 and head-amp landed:
`m200-s1608-headamp/*.pcap`, `m200i-s1608-48k-*`, and for the upper bank
`m200-headamp-1357_16-toggle3` (names its own scene and lights slots 1, 3, 7, 16).

**RESULT, run 2026-08-22.** `opdiff.py` over 8 "golden" and 13 "ours" captures:

```
ONLY the real desk sends (present in >=1 golden, 0 of ours):
    (nothing)
ONLY reac-pw sends:
    cdea 0103 000d   (in 6/13 of ours)
```

**There is no op TYPE a real desk sends that reac-pw never sends.** We send a superset, and
the one extra is the ENROLL group map `0103 000d` — already known inert on this box (all
three `01 03` parsers in `S-1608_alldecomp.c` reject it on their opcode gate; it arrives
`0x10` and they want `1`, `0x80/0x82`, `0`). So the difference is NOT a missing op. It is in
CONTENT, ORDER or repetition — and content is largely exonerated, which leaves ORDER, the
thing the operator says is the law of this protocol.

**CAVEAT ON THE GOLDEN SET, and it is not small.** `opdiff.py` discriminates by FILENAME
PREFIX. Six of its eight "goldens" are the `2026-07-21` `m200-*` captures — and reac-pw was
impersonating the real M-200 MAC `00:40:ab:c9:cc:03` from that date. Some of those may be US,
in which case one of them reads as a golden while being reac-pw refusing. Before building on
this diff, re-partition the corpus by a desk MAC reac-pw never impersonated (M-300
`c9:d8:5b`, M-5000 `ca:15:4c`) — noting those drove the OTHER S-1608, `c4:80:3b`.

So the cleanest evidence would be a fresh capture of a real desk setting 48 V on
`c4:80:41`, which is Question 1's session anyway.

Known already, and to be re-checked rather than re-derived:
- the `op-0403 tag-0101` head-amp records we emit are BYTE-IDENTICAL to what an M-200i,
  M-300 and M-5000 each write, masked across CH/PARAM/VALUE and both checksums
  (`WIRE-EXONERATED-2026-08-21.md`);
- the chanmap is byte-faithful, and its `0x28..0x2f` boundary is a 40-channel desk's tail,
  not a box property;
- the ENROLL group map `01 03 00 0d` is inert on this box (all three firmware parsers reject
  it on their opcode gate).

So the record CONTENT is not the difference. Look at what surrounds it: op SET, ORDER
("this protocol sets things one after the other, never on a clock" — timing is
circumstantial, order is the law), and anything present in a desk's establish that reac-pw
never emits at all.

## Question 2 — where the PACE rides (needs one new capture)

**Operator's facts, 2026-08-22, not conjecture:**
- A REAC rig has exactly ONE clock master dictating the pace; it may be a box or a mixer.
- Everybody else follows that clock and adapts.
- **The pace is set exclusively by the console.**
- Boxes are dumb: their only clock configuration is the M / S / SP switch.
- All REAC mixers can set 44.1, 48 and 96 kHz.

Measured against that: a real M-5000 at 96 kHz has desk AND box both at 8000 pps; a real
M-200 at 48 kHz has both at 4000 (mirror tap corrected per direction — the desk copy is
duplicated in this corpus, the box copy is not). Under reac-pw at `--rate 96000` our
downstream is byte- and cadence-identical to a real 96 kHz desk (1492-byte frames, 125.1 µs
mean, p50 124.9) and **both** boxes answer 4000 pps, the S-0808 included.

Since the pace is the console's to set and boxes merely adapt, our master is failing to
convey it. Ruled out by measurement: the cfea announce (across rates the only differing
constants are the desk MAC and `[19]`, the console generation), the generation byte itself
(`--mixer m5000` at 96 kHz left the box at 4000 pps), the chanmap, and the cadence alone.

**The corpus cannot isolate it**: family and rate are perfectly confounded — all 30 M-200
captures are 48 kHz, all 10 M-5000 captures are 96 kHz. So the three ops only a 96 kHz desk
sends (`cdea 0100 len 26`, `0101 len 24`, `0102 len 14`) are equally explicable as OHRCA
chatter.

**The deciding capture** is one desk, one box, one cable, capturing continuously ACROSS a
rate change in the desk's REAC menu. Everything else held constant is what makes it
decisive.

```
sudo tcpdump -Z root -i <nic> -w reac-captures/captures/<desk>-s1608-RATESWITCH-48k-to-96k-2026-08-XX.pcap \
     ether proto 0x8819
```

Start the capture, hold at 48 k ~30 s, switch the desk's menu to 96 k, hold ~30 s, stop.

```
analysis/pps_by_mac.py <pcap> 20                          # did both ends change pace?
analysis/rate_field_hunt.py <pcap> <desk> <pcap> <desk>   # the control-plane diff
```

While the desk is cabled it is worth capturing a **head-amp write on the S-1608** in the same
session — that is Question 1's answer on a plate, from the unit that refuses us.

---

## Bring-up checklist (so the session is not wasted)

1. `pgrep -ax reac-pw` and **kill every master first**. Two masters on one segment source the
   same real MAC, discard each other as own-echo, and the box goes mute — ~40 min lost once.
2. Capture with `-Z root`; tcpdump otherwise drops privileges, writes nothing, and the empty
   file reads exactly like a silent segment.
3. `-c N` is not a time window. At 8000 fps, `-c 4000` is half a second.
4. An unclaimed REAC box transmits NOTHING. Use `/sys/class/net/<nic>/carrier` as the
   master-independent power detector, never the absence of frames.
5. Note whether the tap is mirrored: it doubles the DESK's frames but not the box's, and
   halving both reads a 96 kHz box as 48 kHz.
6. Name the capture from what is IN it. A desk MAC is not proof of a real desk.
