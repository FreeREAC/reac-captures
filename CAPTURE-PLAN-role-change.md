# Role change on a live segment — the captures §8a is blocked on

Written 2026-08-31. The arbitration spec's §8 (role as a settable field) is blocked on knowledge,
not on code: **no capture in this corpus shows a master ceding the wire, or a box reacting to its
master's role changing under it.** A rate change is measured and golden-pinned; a role change is
inference. This work has twice been caught building on inference — the founding incident (a box
whose REAC Mode switch was on M, misread as a protocol fault) and the ~27 s dwell (imitating one
desk's wall clock instead of following the box's own confirmations).

Every arm below uses **hardware already on the bench**. No desk is required.

## The one lever that makes this possible

**A box's REAC Mode switch has an `M` position, and a box on `M` MASTERS THE WIRE.** That is the
whole experiment: it manufactures the rival-master case §2b classifies, on demand, with a switch
the operator can flip back. It is also the exact case the founding incident hit by accident and
nobody has ever recorded on purpose.

## Arm 1 — a rival master ARRIVES while we are established (the §2b case)

**Why:** §2b rules that a rival is classified by GEOMETRY before it is joined, and §8c wants the
disagreement published. Both are written against frames nobody has captured arriving mid-session.

    1. reac-pw master, box enrolled, audio flowing. Confirm: `recognized box = …`, ESTABLISHED.
    2. START THE CAPTURE (both directions, full frames — see `analysis/` conventions).
    3. Flip the OTHER box's REAC Mode switch to M and power-cycle it.
    4. Let it run 60 s. The console should report `rival-master-box`.
    5. Stop the capture. Flip the switch back to S and power-cycle.

**What it answers:** what a box emits when it believes it is master; whether our FSM notices
without a link event (it has no link-state watch — issue #95); whether the enrolled box on that
segment keeps streaming or drops.

## Arm 2 — we CEDE: what a master must send when it steps down

**Why:** §8d's one-gesture yield writes a role change to a running daemon. Nothing records what
frames a master should emit on the way out — whether it announces, or simply stops.

    1. As arm 1, established and flowing.
    2. START THE CAPTURE.
    3. Stop reac-pw (`systemctl --user stop reac-pw`) — a HARD cede, the crudest form.
    4. Watch the box for 60 s: does it keep streaming, re-hunt, or go quiet?
    5. Start reac-pw again and record the re-enrol.

**What it answers:** the box's behaviour when its master vanishes, which bounds what a graceful
cede must improve on. A stop is not a graceful cede — it is the FLOOR, and any real yield must do
at least as well.

## Arm 3 — the box's own view of a master that changes identity

**Why:** a role change re-opens the segment. Whether the box treats the returning master as the
same one or a new one decides whether §8a needs a full cold enrol or can re-establish in place.

    1. Established. START THE CAPTURE.
    2. Restart reac-pw with a DIFFERENT `REAC_NAME` (a different segment identity, same NIC).
    3. Record the box's reaction.

**What it answers:** whether identity or merely presence drives the box's enrolment state.

## Discipline — the two traps this rig has already paid for

**A restart is NOT a cold connect, and the journal cannot tell you which you got.** A daemon
restart does not bounce the BOX's PHY, and a box that never dropped is re-adopted, not
re-enrolled — the log prints the same `PROBING -> GRANTING -> ESTABLISHED` either way. The
difference is visible only AT THE BOX: relays and the REAC LED. **Every arm above needs eyes on
the box, and the observation written into the capture's notes.**

**Do not capture on the USB AX88179.** It logged a complete enrolment for a box that physically
sat still (2026-08-31). Use the PCIe NIC for anything whose timing matters.

## What NOT to conclude

These arms use BOXES as the rival master. A box on `M` is not a desk: §2b exists precisely
because the two want opposite answers. What a real M-200 or M-5000 sends when it cedes remains
uncaptured, and arm 2's hard stop is our own floor, not a desk's behaviour. Say so in the
manifest entry rather than letting a future reader infer the desk case from these.
