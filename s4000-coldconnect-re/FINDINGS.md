# The S-4000S was in MASTER mode — that was the whole "it will not join reac-pw" thread

RESOLVED 2026-08-30 01:54 on the live rig. The box `00:40:ab:c4:08:bc` was physically switched
to **master**. Moved to **slave** and power-cycled, it cold-connected to reac-pw in 1.8 s:

```
box presence GAINED (UNICAST from 00:40:ab:c4:08:bc)
recognized box = S-4000S (32 in / 8 out)
box JOIN seen (cdea 04 03, unicast from 00:40:ab:c4:08:bc) -> GRANTING
PROBING -> GRANTING -> ESTABLISHED
```

Confirmed through the console (`/stagebox` -> `box-2f085c4f S-4000S in=32 out=8 ready`;
`/reac/segment` -> `seg2: established 96000Hz model=s4000s`), the graph (32 capture + 8 playback
ports on `reac-capture.seg2` / `reac-playback.seg2`) and the wire (8003 pkt/s at 96 k).

**A master does not cold-connect to another master.** That is the entire explanation, and it
accounts for every symptom the thread has carried since 2026-08-20: the box broadcast instead of
unicasting, `reac-disco` classified it `master`, and no rate, desk profile or link-up edge could
change any of it.

## REFUTED — do not cite the earlier conclusion

An earlier revision of this file argued that reac-pw never emitting `cdea 04 03` was why the box
would not join, since a real M-5000 broadcasts ~104 of them per session and we broadcast none.
**That is wrong.** reac-pw still sends no `cdea 0403` during PROBING, and the box joined anyway
the moment its mode was right — sending `cdea 0403` itself, unicast, as its JOIN. The gap was a
consequence of probing a peer that was never going to answer, not its cause. It was filed
provisional at the time and is now closed.

Also withdrawn: the claim that `rx_box_ctrl=0` is a lying counter. The box was not a box on that
wire, so counting zero BOX control frames while it broadcast `cdea 0100` as a master is defensible
behaviour, not a defect. It is not evidence of anything and should not be re-filed as a bug.

## What survives, and is still worth fixing

**The slave-role stream detector misreads box geometry.** Run with `--role slave` against that
segment, reac-pw reported `rx stream = master downstream (40 ch)` while the only stream present
was **1204 B**, which is `52 + 32*36` — a 32-channel BOX upstream. A master downstream is 1492 B
/ 40 channels. reac.ksy fixes the geometry, so the frame length settles the direction with no
heuristic; the detector should read it rather than assume. This is independent of the mode
question: 1204 is not 1492 whoever sent it.

## The method that got there, kept because it nearly went wrong

Four hypotheses were tested on the wire and all four refuted — rate (the box free-runs at 96 k,
so a 48 k drive only produced `WIRE PACE MISMATCH`), desk profile (m200 and m5000 identical),
link-up timing (four genuine edges including a cable replug at the box end, master live
throughout), and "it is a rival master" (refuted by geometry: it emitted 1204 B box frames).

Every one of those was a software hypothesis about a hardware switch. The question that resolved
it — *what is this unit actually set to?* — is one no capture could answer and the operator
answered in a sentence. **Ask what the hardware is configured as before diffing protocol bytes.**

## Reproduce

`python3 analysis/s4000_join_diff.py` censuses the two July M-5000 goldens and the
2026-08-30 capture, normalising by capture duration (the corpus mixes a 77 fps control phase
against an 8000 fps streaming one, so frame percentages compare nothing).
