# What to capture next, and why each one exists

Written 2026-08-21 after a full audit of the corpus (82 captures, all renamed from
measured facts — see `analysis/name_from_facts.py`). Two questions are open that the
existing corpus **cannot** answer, and one capture each would close them.

## The gap, measured

| desk | rates present in the corpus |
|---|---|
| M-200i | 48 k only (53 captures) |
| M-300 | 48 k only (7) |
| M-5000 | 96 k only (10) |
| reac-pw (us) | 48 k ×3, 96 k ×2 |
| unnamed desks (`ca:15:4d`, `c9:91:9c/9d`) | unmeasurable (too short) |

**No 44.1 kHz anywhere. No desk at a rate outside its family's.** Every desk we can
name ran exactly one rate, so "the console byte is the family" and "the console byte
is the rate class" predict the whole corpus identically.

## UPDATE 2026-08-26 — rig + tool answered it FOR OUR BOX (real-desk capture still open)

Ran `analysis/rate_field_hunt.py` over reac-pw driving the S-0808 at 48k vs 96k (full-frame
captures): cfea[19] (+checksum) is the ONLY master byte that differs, and the box's own
frames are byte-IDENTICAL across rates. On the rig cfea[19]=0 -> box 48k, =1 -> box 96k,
cadence-independent, and a live flip re-paces the box. So for OUR box the byte is the rate
class, and reac-pw now derives cfea[19]=f(rate) (commit 0c0f4c9). The DECIDING capture is
still needed — this is reac-pw driving, not a real M-5000 at 48k / M-300 at 96k, so whether
a real desk emits the byte as rate-class or family is unconfirmed. 44.1 also still missing;
our box maps cfea[19]=0 to 48k (binary field), so a rig-driven 44.1 lands the box at 48k —
a real desk at 44.1 is the only way to pin the third pace.

## 1. THE DECIDING CAPTURE — a desk at an off-family rate

`cfea` block byte **19** is `0x00` for M-200i/M-300 and `0x01` for M-5000. On the rig
it is also what the box's pace follows: with `0x00` an S-0808 returns 48 k, with `0x01`
96 k, while our TX paces 8001 fps either way. Two readings fit, and they differ in
what reac-pw should emit:

- **family** — the byte names the desk, and the box infers a rate from it
- **rate class** — the byte IS the pace, and the family is irrelevant to it

Capture **either** of these and it is settled:

- an **M-300 at 96 kHz** (`c9:d8:5b` — this MAC was never impersonated by reac-pw, so
  it is unambiguous evidence), or
- an **M-5000 at 48 kHz** (`ca:15:4c`)

Read byte 19 of any `cfea` frame from the desk.

**CORRECTION 2026-08-26 (operator):** M-300 at 96k is IMPOSSIBLE — the V-Mixer family is hardware-limited to 48 kHz. The only off-family capture is M-5000 (OHRCA) at 48 kHz, and its answer is forced: an M-5000 at 48k drives its box at 48k, which requires cfea[19]=0x00 (the box follows the byte); if the byte were the family, M-5000 would always send 0x01 and could never run a box at 48k. So the byte is the rate class by logic + rig; an M-5000@48k capture only confirms.
 If it stayed at the family's usual
value while the rate changed, the byte is the family. If it moved with the rate, it is
the rate class.

reac-pw currently derives it from the rate (`reac_rate_console_field`), which is
rig-determined behaviour satisfying the operator's law that the family must not gate
the pace — not a decoded field. This capture tells us whether that is right.

## 2. 44.1 kHz, at all

Nothing in the corpus runs at 44.1 k, on any desk with any box. One capture per desk
family is enough to pin the third legal pace.

## 3. Capture CLEAN, or say it is mirrored

**61 of the 82 existing captures are mirrored** — recorded through a port mirroring
both directions, so every frame appears twice. That artifact has now produced two
wrong conclusions in this repo:

- a "frame doubling" defect that led to a pacer fix (withdrawn, reac-pw PR #93)
- an "M-200i runs 96 kHz" reading that was really 48 k counted twice (2026-08-21)

Prefer a non-mirrored tap. Where that is not possible, the name now carries `mirror`
and any rate must be measured from the **counter's advance** (frame[14:16]), never
from packets per second.

## The matrix worth filling

Three desks × three rates × three boxes is 27, which is more than anyone needs. The
useful subset:

| desk | 44.1 k | 48 k | 96 k |
|---|---|---|---|
| M-200i | needed | have | **needed (deciding)** |
| M-300 | needed | have | **needed (deciding)** |
| M-5000 | needed | **needed (deciding)** | have |

One box is enough per cell — the S-0808 is the least temperamental. Include the
establishment (cold connect) in each: it carries the config-announce, the JOIN burst
and the desk's cfea, which is where every field of interest lives.

## While capturing, also worth having

- A **head-amp sweep on each box** — pad/sens/phantom across all channels. The operator
  reports this worked on all three boxes historically; the S-1608's live edits do not
  latch under reac-pw today (its scene applies only at establishment), so a golden
  showing a real desk doing it live would localise that defect too.
- The **link-bounce / replug** sequence per desk, now that reac-pw resets per-session
  state on `(peer, session)` — a golden reconnect from a real desk would confirm the
  order we now emit.
