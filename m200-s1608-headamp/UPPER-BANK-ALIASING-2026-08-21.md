# The S-1608 upper bank is ALIASED onto the lower one (2026-08-21, second session)

The defect that has resisted a night and a day is not "inputs 9–16 are dead". They never
receive a head-amp record at all: **CH 0x28–0x2f alias onto physical ports 1–8.**

## The proof — wire only, no soft indicator

A healthy S-1608 (`00:40:ab:c4:80:41`, power-cycled, on a non-mirrored USB NIC, established
at 48 kHz, base 0x20 published). Desk ch7 patched to box input 16, so the engine addresses
**CH 0x2f**. Sweeping that one cell's SENS and reading the box's own upstream:

| SENS written to CH 0x2f | slot 8 | slot 16 | slot 1 (control) |
|---|---|---|---|
| 55 | **−69.7** | −106.2 | −88.9 |
| 0 | **−106.1** | −106.0 | −88.9 |
| 40 | **−84.4** | −106.2 | −88.8 |

Slot 8 tracks the gain monotonically across all three; slot 1 never moves and slot 16 never
moves. A microphone was physically in port 16 throughout, so its silence is not an empty
socket.

**Physically confirmed and independent:** with the establishment scene carrying `phantom=1`
on CH 0x2f and `phantom=0` on every other channel, the operator saw **port 8's 48 V lit**.
We addressed input 16; input 8 powered.

The first hint was already in the enrolment pattern and went unread: after that establish,
slots 1–7 sat at −88.7…−89.0 (the sweep's default SENS 32) while **slot 8 sat at −92.9** —
the one channel carrying SENS 30, the value addressed to CH 0x2f.

## What this rules in

It matches the firmware exactly. The 48 V write (`FUN_0c00ac1e`) range-checks its channel to
**0..7 — an index WITHIN a bank** — and inputs 9–16 need **bank 1**, whose binding comes from
the port→group map rebuilt by the chanmap republish. Bank 1 is never bound, so an address in
group 5 falls into bank 0 and lands on port 8.

## What this rules OUT (tested, refuted)

**Declaring the high bank an INPUT group does not bind bank 1 — it breaks what worked.**
The chanmap's flag nibble feeds the peer port table (`FUN_0c002d42`:4175): `0x38>>4 = 3` is
EMPTY, `0x28>>4 = 2` is INPUT. Marking slots 0x28–0x2f as `0x28` reached the wire (verified,
all eight slots) and the box then converted **nothing at all** — the lower bank stopped too.
Reverting restored the previous behaviour after a re-establish.

Also already refuted, earlier: addressing (records are byte-correct at CH 0x2f), delivery,
the ENROLL width gate, the SUB-pair commit, and the source MAC.

## Where to look next

The question is now sharp: **what does a real M-200 send that binds bank 1?** The corpus has
a golden where one converts slot 16 at −35.3 dBFS on this box model, so it is reachable.

- The bank↔group binding routine is at `0x0c00838a`–`0x0c00881c`, in a Ghidra gap, and reads
  the box MODE (`FUN_0c00f6a8`). Lifting it is the highest-value RE left.
- Diff the golden's establish against ours at the level of the CHANMAP's full 49-record
  sweep — not just the flag nibble, which is byte-identical.
- A live edit DOES latch on a healthy box (the sweep above proves it), which corrects the
  earlier "only the establishment scene applies" reading: that was a symptom of the box's
  refusing state, not a rule.

## The refusing state, for whoever hits it next

This box intermittently enters a state where it applies NOTHING on either bank, and only a
POWER CYCLE clears it — not a master restart, not a NIC bounce, not a re-establish. Every
measurement taken in that state is meaningless; check the lower bank converts (≈ −88 dBFS
idle, not −106) before believing any upper-bank result.
