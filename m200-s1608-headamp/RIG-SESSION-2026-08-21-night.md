# Rig session, 2026-08-21 night — the ENROLL A/B, and a box that stopped answering

Companion to `ENROLL-IS-THE-GATE-2026-08-21.md` (the corpus finding) and to reac-pw branch
`fix/enrol-answers-the-declaration` (the code). Written mid-session; the A/B is NOT finished.

Rig: direct cable `enp131s0`, our NIC `34:5a:60:9f:9e:be`, S-1608 `00:40:ab:c4:80:41`
(declares 16 in / 8 out, head-amp base 0x20), wire at 96 k, free-running pacer, no
clock-follow. Condenser mics on box inputs **8** and **16**, music in the room.

## The baseline, which is the only healthy state seen tonight

Master had been up 51 minutes (started 01:59:39 by the previous session, no `--headamp`),
engine driving head-amps. `up_slots` on the box's own upstream fillers:

| slots 1–7 | slot 8 (condenser) | slots 9–16 (incl. condenser on 16) |
|---|---|---|
| −88.5…−89.0 (enrolled, idle preamp) | **−58.6 (live)** | **−105.9…−106.2 (zero)** |

This is a textbook positive control: the probe demonstrably detects presence (slot 8 sits
30 dB above the idle floor) **in the same command** that reports slots 9–16 as zero. So the
upper bank's silence was real, with a live microphone plugged into input 16.

## What was run, and what it showed

Every run below reached `PROBING -> GRANTING (rx CONFIG) -> ESTABLISHED` with the box
recognized as `S-1608 (16 in / 8 out)`, `gaps=0`.

| run | build | head-amp source | slots 1–8 | slots 9–16 |
|---|---|---|---|---|
| baseline | main | engine | 8 live at −58.6 | −106 |
| A | no-enrol branch | `--headamp` ×2 | −106 | −106 |
| B | main | `--headamp` ×2 | −106 | −106 |
| C | main | `--headamp` ×16 (phantom+sens) | −106 | −106 |
| D–H | main | engine, `--headamp` ×16, both | −106 | −106 |

**The change is not implicated: main reproduces the dead state.** After the first master
restart the box never converted again, on either build, through a NIC bounce, a full
kill→bounce→start cold connect, an engine restart, and head-amp records proven byte-correct
on the wire.

Physical read, which is the honest instrument here and not a soft meter — the operator
watching the box's own 48 V LEDs:

- all 16 channels asserted from reac-pw, records verified on the wire (CH 0x20–0x2f, 122
  records captured through the establish window): **no LED lit**.
- phantom driven OFF then ON through the ENGINE on CH 0x27 and CH 0x2f, both records
  verified on the wire in the same capture: **no LED lit** — including port 8, which the
  operator had been setting and unsetting successfully earlier.

So the box stopped accepting head-amp commands altogether. Operator is power-cycling it.
**Everything measured after the baseline describes a wedged box, not the ENROLL question.**

## Two things worth keeping regardless

**`--headamp` has never committed on this unit.** Tonight all 16 cells reached the wire
byte-correct and lit nothing. That is the same anchor anomaly recorded in
`reac-firmware-re/HEADAMP-S1608-STATE-DIAGRAM-2026-07-19.md` §5 for this exact MAC. The
proven actuation path on `c4:80:41` is the ENGINE, not the CLI arming — do not use
`--headamp` as the lever in a head-amp experiment on this box.

**The boot placeholder node pair is not benign.** Every reac-pw run leaves two pairs on the
graph:

```
capture 341 / playback 227   box-model none   link-state probing      headamp.base none
capture 215 / playback 353   box-model s1608  link-state established  headamp.base 32
```

Both are published by the same process (they die with it). The resolver prefers
`link-state=established`, which is why this was filed as benign — but openmixer PR #653
taught the actuator to REFUSE HONESTLY when `reac.headamp.base` is absent, and the
placeholder twin publishes exactly `base = none`. A resolver that lands on the wrong twin
now produces a silent, correct-by-construction no-op. That is a real defect with a real
failure mode, not cosmetic residue: destroy the placeholder pair on recognition.

## Where to resume

1. Box power-cycled → restore the baseline and CONFIRM it: engine drives phantom on ch3
   (CH 0x27, box input 8), operator sees LED 8 light, `up_slots` shows slot 8 above the
   idle floor. No experiment means anything until that control is back.
2. With the control healthy, the A/B is one flip: same conditions, `main` vs
   `fix/enrol-answers-the-declaration`, and the question is whether LED 16 lights and
   whether slot 16 leaves −106.
3. The corpus finding stands on its own either way: no desk we can positively identify as
   real ever enrols a 16-in box (0/6), while an 8-in box is enrolled 2/2 and a 32-in box
   2/2. What the rig has to say is whether removing OUR enrol is sufficient to open the
   bank, or merely necessary.
