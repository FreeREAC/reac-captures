# The ENROLL is the S-1608 bank gate — no real desk sends one to this box (2026-08-21)

Answers the question left open by `UPPER-BANK-2026-08-21.md`: *what does a real console send
that we do not, between CONFIG and the box opening its upper bank?*

Nothing. The difference runs the other way — **reac-pw sends one frame to an S-1608 that no
real desk ever sends it: the ENROLL group map, `cdea 01 03 000d`.**

Derived entirely from the committed corpus (`analysis/placement_rows.jsonl`); no pcap was
re-scanned and no new capture was needed.

## The discriminator trap, disarmed first

Source MAC cannot tell a golden from one of our own runs: through July reac-pw impersonated
the real M-200's address `00:40:ab:c9:cc:03`, so both sides of the corpus answer to the same
desk MAC. The only reliable discriminator here is the **filename prefix** — `m200-*` is the
real desk, `reacpw-*` is us. A diff keyed on MAC compares us against ourselves.

Second correction, in `analysis/placement_scan.py`: `00:40:ab:c4:80:41` was labelled
`reac-pw(slave stand-in)`. It is **the rig's own S-1608** (`HEADAMP-S1608-STATE-DIAGRAM-2026-07-19`,
`UPPER-BANK-2026-08-21`), now `S-1608#2`. The stale label made every table over this rig
unreadable, and it hid the two most recent goldens inside a row that looked synthetic.

## The measurement

An ENROLL is only ever sent at cold-connect, so a capture can testify only if it *contains*
an establishment — i.e. the box sourced a CONFIG announce (`0103 0010`) or a cold JOIN
(`0403 0016/001a`). Captures with two boxes on the segment are dropped: an ENROLL cannot be
attributed to either. That leaves 33 captures.

| box family | sender | captures with an ENROLL |
|---|---|---|
| S-0808 | real desk | **9 / 10** |
| S-4000S | real desk | **5 / 5** |
| **S-1608** | **real desk** | **0 / 11** |
| S-1608 | reac-pw | 6 / 7 |

The 0/11 spans **three desk models** (M-200i, M-300, M-5000) and **both S-1608 units**
(`c4:80:3b`, `c4:80:41`), across sessions from 2026-07-10 to 2026-07-24.

**The probe is proven able to detect presence** — the same extractor, on the same real M-200
`c9:cc:03`, finds the ENROLL in the S-0808 and S-4000S captures. The S-1608 absence is real,
not a broken search. (The one S-0808 miss is `m200-…pcap09`, a mid-stream split-file segment
whose establishment marker is a heartbeat, not a cold-connect. The one reac-pw miss is
`reacpw-slave-m5000-postfix`, where reac-pw was the **slave** — a master frame is correctly
absent there.)

## What the group map says when it is sent

| box | inputs | region bytes | in-groups |
|---|---|---|---|
| S-0808 | 8 | `41 00 00 00 00 c3 c3 c3 c3` | 1 |
| S-4000S | 32 | `41 41 41 41 00 00 00 00 c3` | 4 |

Both fit exactly 8 channels per `0x41` group, which is what `reac_master.c:set_enroll_width`
computes (`n_in = in_ch / 8`). **The formula is not wrong for the base-0 boxes.** The S-1608
case is not "two groups" — it is *none*.

The correlation worth naming: the S-1608 is the only captured box that declares a **non-zero
base** (`0x20`; the S-0808 and S-4000S declare `0x00`, verified 3/3 in the config-announce
`payload[3]<<4`). A box that declares where it sits in the fabric ring is not placed by the
desk. Suggestive, not proven — three box models is not a law.

## The audio A/B, same box, same night

`up_slots` over the two 2026-07-21 establish captures against `c4:80:41`, fourteen minutes
apart. Per-slot RMS of the box's own upstream fillers:

| sample | reac-pw 23:43 (sends ENROLL) | real M-200 23:57 (sends none) |
|---|---|---|
| skip 20 000 | slot 1 only; 2–16 at −106 | slot 1 only (still transient) |
| skip 60 000 | slot 1 only; 2–16 at −106 | mid-transition |
| skip 100 000 | *capture ends* | all banks converting |
| skip 140 000 | — | slot 7 **−14.1**, slot 16 **−36.1**, 9/11/13/15 live |

−106 dBFS is mathematical zero on this rig; −89 is an idle preamp converting.

Scene confound, and why it does not apply: a channel stays at digital zero until a group-A
head-amp record lands on it, so dead slots could in principle just mean "we never wrote that
channel". That escape is closed by the live test in `UPPER-BANK-2026-08-21.md` — a
byte-correct record **was** written to CH `0x2f` and input 16 stayed at −106.1 across two SENS
values with phantom on. Record delivered, channel still dead.

## This was found once already, and parked

`reac-pw` branch `wip/headamp-noenroll-campaign` (`bd7b52b`, unmerged) carries
`REACPW_NO_ENROLL` and names the mechanism outright: *"the ENROLL is what shifts the box's
slot→XLR config +8 (S-1608 top bank over the gate). The M-200 sends none."* Campaign state:
**NO_ENROLL lit all 16 phantom** — but the session did not hold without an enroll (48 V
flickered on an ~8 s cycle), so it never merged.

That blocker now reads differently. A real M-200 holds an S-1608 for the length of a 70-second
capture having sent **zero** enrolls, and its post-establish cadence is the same cfea+chanmap
pair reac-pw already implements. So the hold dependency is **ours**, not the protocol's — most
likely our own FSM requiring `enroll_pending` to clear before it will stay established, which
is what `REACPW_LINKCHECK_SECONDS` was added to discriminate and never did.

## Ruled out, do not re-open

- **The chanmap 0x38 flag** (the standing lead): byte-faithful, and M-200i/M-300/M-5000 all
  send the identical pattern to a real S-1608. `UPPER-BANK-2026-08-21.md`.
- **The SUB01→SUB02 post-establish commit** (`REACPW_EST_COMMIT`): debunked by the 2026-07-22
  protocol audit and deliberately deleted in reac-pw `7ac3567` — a real M-200 emits zero
  sub01/sub02 once established.
- **Addressing, delivery, and the ENROLL width gate** as a frame-size limit: all three refuted
  on the wire, `UPPER-BANK-2026-08-21.md`.

## The next measurement

Rig, direct cable, single master (`pgrep -ax reac-pw` first — a second master is invisible to
discovery when both source the real NIC MAC, and costs the segment half its frames):

1. Establish the S-1608 with the ENROLL suppressed.
2. `up_slots` on the box's upstream: do slots 9–16 leave −106 without any head-amp write?
3. Then write a head-amp record to CH `0x2f` and watch input 16 specifically.
4. Hold it for several minutes and record whether the session survives — that is the
   open half, and the number that decides whether this is a one-line model condition or an
   FSM fix.

If it holds, the change is small and principled: **a box that declares its own base is not
enrolled** — matching what every real desk in the corpus does, with the S-0808 and S-4000S
byte-goldens unchanged.

## Reproducing this

```
cd analysis && python3 enroll_control.py        # the tally above, from placement_rows.jsonl
cd analysis && python3 opdiff.py                # the full desk-side op-set diff
```

`placement_rows.jsonl`'s `box_models` is a derived field; it was re-mapped in place from
`box_macs` after the label fix rather than re-scanning 20 GB of pcaps.
