# S-4000S vs reac-pw: what the wire shows, and the one op a real desk sends that we never do

> **READ THIS FIRST — the box was in MASTER mode for every measurement below.**
> The operator established at 2026-08-30 01:52, after the capture was taken, that the S-4000S
> was physically switched to **master**, and moved it to **slave** at that point. A REAC master
> does not cold-connect to another master, so the headline question "why does it not join" may
> be answered entirely by the mode, and the `cdea 0403` gap below may be a consequence of our
> daemon probing a peer that was never going to answer rather than its cause. Everything in the
> MEASURED section is still true of the wire; the CONCLUSION is provisional until the box is
> re-measured in slave mode after a power cycle. Do not cite the conclusion as settled.
>
> One measurement resists the simple reading and is worth keeping: even in master mode the box
> emitted **1204 B / 32ch** frames, which is a box upstream geometry, not the 1492 B / 40ch
> downstream a REAC master sends. Whatever "master" means on this unit's switch, it was not
> emitting a master's frame shape.


Measured 2026-08-30 on the live rig, direct cable, `enp131s0`. Reproduce with
`python3 analysis/s4000_join_diff.py`.

## MEASURED — true of the wire regardless of the mode question

## What was believed, and is wrong

Since 2026-08-20 the thread has carried "the S-4000 unit at 96 k ignores a driven clock and
never cold-connects even at power-cycle". Three parts of that are refuted:

- **It is not the rate.** Driving the segment at 48 k produced
  `WIRE PACE MISMATCH — configured 48000 but the segment is carrying 96000`. The box
  free-runs at 96 k by itself. 96 k was always the right setting.
- **It is not the desk profile.** `--mixer m200` (the July-proven one) and `--mixer m5000`
  behave identically: filler, no join.
- **It is not link-up timing.** Four genuine link-up edges with our master live and
  transmitting throughout — `ethtool -r`, a physical cable unplug/replug at the BOX end,
  `ip link down/up`, and daemon restarts — all end the same way. The daemon's own advice
  line ("bounce the box PHY: it only cold-connects on link-up") does not hold for this box.
- **The box is not a rival master.** `--role slave` reports `rx stream = master downstream
  (40 ch)`, but the geometry says otherwise: every frame it sends is **1204 B = 32ch**, a box
  upstream return (`52 + n*36`). A master downstream is 1492 B. The slave-side stream detector
  is misreading a 32-channel box return as a 40-channel master downstream — a separate defect,
  filed here because it cost an hour.
- **The wire is not silent, and our counter says it is.** reac-pw shut down reporting
  `rx_box_frames=2632631 rx_box_ctrl=0`, yet the capture holds **7759 `cdea 0100`** plus
  `0101/0102/0103` and 8 `cfea` announces from the box. `rx_box_ctrl` is not counting frames
  the box demonstrably sends.

## CONCLUSION (PROVISIONAL — see the box at the top)

## The actual difference

Our box `00:40:ab:c4:08:bc` **does** cold-connect — it did so to a real M-5000 on 2026-07-11
(`m5000-none-96k-mirror__matrix-m5000-s4000-unit2-coldconnect-2026-07-11.pcap`), answering
**unicast** to the desk with `cdea 0103 oplen=1` (19x) and `cdea 0403` (6x). So the box is
healthy and the divergence is ours.

Normalised by capture duration, our control cadence matches the desk's everywhere but one row:

| op (master -> broadcast) | M-5000 unit1 | M-5000 unit2 | reac-pw 2026-08-30 |
|---|---|---|---|
| `cdea 0100` | 74.6/s | 147/s | 118.6/s |
| `cfea ffff` | 1.05/s | 1.04/s | 1.01/s |
| `cdea 0103` | 0.63/s | 0.42/s | 0.38/s |
| `cdea 0101` | 0.22/s | 0.35/s | 0.38/s |
| `cdea 0102` | 0.22/s | 0.34/s | 0.38/s |
| **`cdea 0403`** | **0.44/s (104)** | **0.35/s (104)** | **0.00/s (0)** |

The desk broadcasts `cdea 04 03` — the Roland DT1 container — around 104 times in both
sessions. reac-pw broadcasts none, in either role, at any rate, on either profile.

## Why that is the one that matters

The firmware RE already decided it (`openmixer docs/design/notes/2026-08-26-enrol-frame-firmware.md`):
the ENROLL builder is gated on a literal match of the box's announced kind — **0x83/0x84 send
(S-0808/S-4000S), 0x80/0x82 send nothing (S-1608)** — and **the S-4000S box FSM requires
subtype 0x10 to leave state 3**, where it applies a 10-byte group map. The S-1608 needs none of
it: its dispatcher recognises only subtype 0x01 and self-places from scene transfer, head-amp
sweep and GPIO straps.

That accounts for the whole asymmetry. An S-1608 joins reac-pw in about a second; an S-4000S
sits in filler forever, because the frame it is waiting for is one we never emit.

## The open question this capture cannot answer

reac-pw gates ENROLL on the box's announced kind, but **this box never announces to us** — every
frame it sends is broadcast, `unicast-ctrl=0`, whereas against the M-5000 all 26 of its control
frames were unicast to the desk. So either the S-4000S will not announce until it has seen DT1
traffic (in which case the gate is a deadlock and the desk's unconditional broadcast is the
mechanism), or its broadcast `cdea 0103` IS the announcement and reac-pw's `is_box_join` does not
recognise it (it accepts `0013/0014/0016/001a`, not `0103`).

Deciding it needs one run of reac-pw emitting `cdea 0403` unconditionally during PROBING, the way
the desk does, and watching whether the box switches to unicast.
