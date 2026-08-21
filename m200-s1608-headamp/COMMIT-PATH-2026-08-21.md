# The S-1608 applies nothing — the commit path, and three theories killed (2026-08-21 night)

Supersedes the direction of `ENROLL-IS-THE-GATE-2026-08-21.md`. That document's MEASUREMENTS
stand; its INFERENCE does not, and the firmware says why.

Rig: direct cable, S-1608 `00:40:ab:c4:80:41` (declares 16 in / 8 out, head-amp base 0x20),
condensers on box inputs 8 and 16, music in the room, single master.

## The state that matters

Since the first master restart of the night the box applies **no head-amp command on either
bank**. Not the upper bank — *both*. With a perfectly clean link (`gaps=0`, `peer-gone=0`),
byte-correct records on the wire, and the engine as the actuator:

| SENS on CH 0x27 (box input 8) | slot 8 | slot 16 |
|---|---|---|
| 0 dB | −106.2 | −105.9 |
| 55 dB | −106.1 | −106.0 |

A preamp gain that moves the channel's own noise floor **not at all** across the full 55 dB
travel is a command that never reached hardware. Earlier the same channel carried a live
condenser at −58.6 dBFS, 30 dB over the enrolled-idle floor, so this is a regression in the
box's state, not a measurement artefact. No 48 V LED lights (operator, physical).

That reframes the whole question: **the upper bank was never the defect to chase tonight. The
commit path is.**

## Theory 1, KILLED by firmware: the ENROLL group map

`op 01 03 00 0d` is **not parsed by the S-1608 at all**. All three `01 03` parsers in the
image reject it on their opcode gate (`S-1608_alldecomp.c`):

| parser | gate | verdict on `01 03 00 0d 10 …` |
|---|---|---|
| `FUN_0c002e94` (test at 4236) | `buf[0]==1 && buf[1]==3 && buf[4]==1` | rejected (`buf[4]==0x10`) |
| `FUN_0c00350a` / `FUN_0c003548` | `buf[4] ∈ {0x80,0x82}` | rejected |
| `FUN_0c003aae` (FSM state 2) | `buf[4]==0` | rejected |

and `FUN_0c002f94` (the be16 reader) has 8 call sites, none comparing a length to `0x0d`. The
frame is a property of the DESK, not the box — the M-200 sends byte-identical
`41 00 00 00 00 c3 c3 c3 c3` to an S-0808 and to an S-1608.

So the corpus observation was real (a 16-in box is enrolled 0/6 by desks we can positively
identify) and the inference drawn from it was wrong: the frame is inert on this box, which is
exactly why removing it changed nothing on the rig. `reac.ksy` had already recorded the same
absence and drawn the correct conclusion — that the map is *not a placement carrier* — which
is the reading I should have taken.

**The real group map rides the CHANMAP flag nibble**, not this frame: `FUN_0c002d42`:4175 does
`peer_port_table[slot>>2] = flag>>4`, so `0x28>>4 = 2` = INPUT group and `0x38>>4 = 3` = EMPTY,
written to the 12×u16 table at `0x0c0f62fa`. The "bank marker" in the notes is the master's
per-group port TYPE. It still is not the gate — every real desk sends the identical `0x38` and
gets 16 channels — but it is not decoration either.

## Theory 2, KILLED on the wire: the sustained SUB-pair commit

`DECODE.md`'s "Commit mechanism RESOLVED" holds that `op-0101` (SUB-A) → `op-0102` (SUB-B)
drives the scene-FSM state-4 commit `FUN_0c003c8a`, which copies staging `0x0c0cd52e` → active
`0x0c0cf85a`; and that reac-pw only ever sends the pair while PROBING, so nothing flushes. It
was implemented once (`REACPW_EST_COMMIT`), removed as "debunked", and never rig-tested.

Tested tonight, sustained at ~1/s while ESTABLISHED. It does not commit — **it makes the box
leave**:

```
box silence windows >0.5s: 1
  box silent 10.29s  (t+15.32 -> t+25.62)
     we sent just before: cfea ffff 0100, cdea 0102 000e
```

The box went quiet for 10.29 s immediately after a SUB02, blowing the ~6.5 s peer-gone budget,
and the master cycled ESTABLISHED → PROBING → GRANTING → ESTABLISHED for as long as the knob
was on (2 drops in 35 s with it, 0 in 40 s without, 0 at 96 k without). So the
"0 sub01/sub02 once established" invariant is not merely what an M-200 happens to do — the box
actively refuses. **Do not re-open this. The knob stays deleted.**

## Theory 3, NOT the cause: rate and bandwidth

At `--rate 96000` the NIC receives 4002 fps where 8000 are expected and reac-pw books the
missing half as `gaps` — the box is running at **48 kHz**, so this is a rate mismatch, not
packet loss. At `--rate 48000`: `gaps=0`, `peer-gone=0`, stable. Worth knowing (and worth a
loud refusal in reac-pw rather than a silent gap count), but it does not explain the commit
failure: the box applies nothing at either rate.

## Where the commit actually dies — firmware

48 V is written by `FUN_0c00ac1e`:10935:

```c
void FUN_0c00ac1e(bank, ch, value, latch) {
  if (FUN_0c00ab96(ch) == 1) {                    // FUN_0c00a68c(ch,0,7): ch in 0..7
    FUN_0c00a9bc(bank, ch + 0x18, value != 1, 1); // GPIO pin 0x18+ch
```

so the hardware address is **(bank ∈ {0,1}, ch ∈ 0..7)** — `ch` is an index WITHIN a bank, never
0..15 — and each bank has its own full set of 5 GPIO expanders (`FUN_0c00a982`: `base + bank*100`,
100 = 5 × 0x14). Inputs 9–16 require `bank = 1`.

The routine binding a bank to a channel group is **not in the decompile**. The visible one,
`FUN_0c007fbc`:8741 (`group<10`, `bVar2 = bank==1`, groups of 8 — CH 0x20–0x27 = group 4,
CH 0x28–0x2f = group 5, exactly the working/broken boundary), is **dead code**: no direct
caller and zero pointer-table references in a 546 KB scan of the image. The live routine sits
in a Ghidra gap at `0x0c00838a`–`0x0c00881c`, whose constant pool holds `0x0c0cf85a` (active
table), `0x0c0f5e00` (HW shadow), `0x0c00ac1e` (phantom write), `0x0c00ac96` (pad) and
`0x0c00f6a8` (the box-MODE getter) — and unlike the dead one it reads the mode.

Also mode-conditional and upper-bank-specific, `FUN_0c004f46`:6819: the firmware seeds head-amp
defaults for groups 10–11 (slots 0x28–0x2f = inputs 9–16) **only when box mode == 0**. The
S-1608 announces mode 2 at block[7]; the S-0808 announces 0. Code says this plainly; whether it
is causal is unproven.

Prior work's `0x0c033158` / `FUN_0c01e49e` is re-confirmed as RUI panel parameters, not an
enrol array — it never touches `0x0c0cf85a`, `0x0c0f5e00` or `FUN_0c00ac1e`.

## RESOLVED as far as the wire goes: the block is INSIDE the box

Everything above was chased to exhaustion on the wire and the answer is that the wire is not
the problem. The discriminating run: clean establish, **two complete 49 s chanmap sweeps**
landed before anything was pushed, then `phantom=1 sens=55` on CH 0x27 byte-verified on the
wire, then another sweep. Every slot stayed at −106 dBFS, both banks, no LED. Repeated with
`REACPW_CHANMAP_PERTURB` forcing four map CHANGES (the only network-side trigger for the
hardware push, `FUN_0c0041e8`:6085 → `FUN_0c00cb8e` → `FUN_0c00cb14` → task cmd 2 →
`FUN_0c0081f6` → `FUN_0c007fbc`): same null.

The commit itself is FINE and provably so. The box's `01 03 00 10 8x` frame is emitted ONLY by
`FUN_0c003c8a` (lines 5857–5891), so **it is a commit receipt**, and it is present in tonight's
captures (`cm.pcap` t+9.045, `bidir.pcap` t+8.608) — in both cases fired by a one-shot
SUB01→SUB02, before the first complete sweep. Staging → active works. What never happens is
the copy from the active table to the pins.

**The gate is strap-derived and unreachable from the wire.** `FUN_0c007e06`:8654 returns true
only when `FUN_0c00f6b4()` (`*0x0c08091c`) is 0 or 1, and `FUN_0c0081f6` returns immediately
otherwise, applying nothing. The same value independently gates `FUN_0c00cb14`:11985, the only
sender of the apply command. That value is decoded once at boot by `FUN_0c01091a`:15843 from
two I/O-expander input bits (device 8, bits 1 and 0):

```c
b = (FUN_0c01f020(8,1) << 1) | FUN_0c01f020(8,0);
role = (b==1)?0 : (b==2)?1 : (b==3)?2 : 3;      // head-amp path needs 0 or 1
```

sampled in `FUN_0c00f650`:14416 and deliberately NOT re-sampled by the re-init path
(`FUN_0c00f68c`). So `b==0` or `b==3` silently disables all head-amp hardware writes for the
whole power cycle, and **no frame a master can send will change it**. What those two pins are
physically wired to is not in the decompile.

Secondary suspects on the same path, both real but unproven: `*0x0c0805f8 == 1` (set by
`FUN_0c00435e` when a second config source publishes; blocks the master's chanmap from ever
republishing) and `FUN_0c00cbd4() != 0`, which diverts to a compare branch that pushes nothing.
Both are cleared by re-entry to `FUN_0c00444c`, i.e. by a clean link drop — which was done
repeatedly tonight without effect.

## The operator ask (physical, first thing)

The box worked at 03:00 and has applied nothing since, across a power cycle. Since the gate is
a boot-sampled hardware strap, check the box's PHYSICAL configuration before any more wire
work: rear mode/role switches, which REAC port the cable occupies, any split/merge or
standalone selector, and whether anything was moved during the power cycle. A strap that reads
`b==0` or `b==3` reproduces every symptom seen tonight exactly.

## What to do next, in order

1. **Recover the commit at all**, on bank 0, before touching the bank question. The box
   committed 48 V on input 8 earlier this same session and last night; find what fired the
   state-4 commit then. The corpus positive control is `s0808-reboot-enrollfix` (desk MAC
   `00:40:ab:00:00:01` = reac-pw's own old default), where a box DID commit under reac-pw.
   Diff that capture's desk-side sequence against tonight's.
2. **Lift `0x0c00838a`–`0x0c00881c` out of the Ghidra gap** (re-run with that range forced as a
   function; its constant pool is already located). That routine is the bank↔group binding and
   the only place the upper-bank answer can come from.
3. Only then the CH sweep 0x00–0x4f with phantom=1, reading the physical LEDs, with CH 0x20 as
   the in-run positive control — it is worthless while nothing commits.
