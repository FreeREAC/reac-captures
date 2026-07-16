# REAC head-amp source control — DECODED (M-200 capture, 2026-07-17)

Ground-truthed on real hardware: a **Roland M-200** (master, `00:40:ab:c9:cc:03`) commanding a
**Roland S-0808** stagebox (`00:40:ab:c4:dc:9c`), captured passively on a switch mirror port.
openmixer/reac-pw were **not** master during the capture — every frame here is the M-200's.

This closes **gap #1** (head-amp / 48V), the blocker on openmixer #155.

## The command frame

EtherType `0x8819`, control type `cdea`, **op `0403`** (the channel-list heartbeat is op `0103`):

```
[counter:2] cdea 0403 0013 000200fe0ef0410a0000 1212 0101 [CH] [PARAM] [VALUE] [CKSUM] f7 …
```

Byte offsets **within the full frame payload, counter included** (tcpdump `-x` starts after the
14-byte Ethernet header, and bytes 0..1 are the free-running counter):

| offset | field | notes |
|---|---|---|
| `[0:2]`   | counter    | free-running, LE — varies every frame, exclude when diffing |
| `[2:4]`   | type       | `cdea` = control |
| `[4:6]`   | **op**     | **`0403` = source/head-amp control** |
| `[6:8]`   | op-len     | `0013` |
| `[22]`    | **CH**     | **channel, ZERO-BASED** (ch1 = `00`, ch3 = `02`) |
| `[23]`    | **PARAM**  | **`00` = phantom +48V · `01` = PAD (-20 dB) · `02` = SENS** |
| `[24]`    | **VALUE**  | phantom/pad: `00`/`01` · SENS: `0x00..0x37` |
| `[25]`    | **CKSUM**  | `0x7e - (CH + PARAM + VALUE)` |

## PAD (`PARAM 01`) — and why it changes the SENS formula

The pad is a **-20 dB analog attenuator ahead of the head-amp**. It is a box parameter for the same
reason 48V is: it must happen *before* the converter. A digital pad is useless — once the samples
exist, the clipping it was meant to prevent has already happened.

**The pad shifts the whole SENS scale by +20 dB**, and the box — not the console — applies the
offset. This is measured, not inferred: across **20 pad toggles on two channels, the M-200 never
sent a single `param=02` frame**, yet its SENS display moved 20 dB. Only the pad bit is on the wire,
so the same VALUE byte means two different dB depending on pad state.

| pad | SENS range |
|---|---|
| off | **-65 … -10 dBu** |
| on  | **-45 … +10 dBu** (same 55 dB span, shifted +20) |

Together: **+10 down to -65 dBu = 75 dB of head-amp range**, with a 35 dB overlap.

> **Trap for implementors:** `dB = -10 - value` is only the pad-OFF half. Ship it alone and every
> gain readout goes silently 20 dB wrong the moment an engineer engages the pad.

## SENS ↔ dB

Roland SENS is **input sensitivity in dBu**, so **more negative = MORE gain**.

```
dB    = -10 - value + (pad ? 20 : 0)
value = -(dB + 10) + (pad ? 20 : 0)

pad OFF:  0x00 = -10 dB (MIN sens)  ..  0x37 = -65 dB (MAX sens)
pad ON :  0x00 = +10 dB (MIN sens)  ..  0x37 = -45 dB (MAX sens)
```

Operator cross-check that pinned the pad offset: SENS reading **-15 dBu** (= value `0x05`) jumped to
**+5 dBu** the instant pad engaged. `10 - 5 = +5` ✓ — an independent confirmation from the console's
own display, using a number not available when the pad-off formula was derived.

**56 values (0x00..0x37) over 55 dB (-10..-65) = exactly 1 dB per step.** Linear, one step per
detent — no lookup table, no dB×2.

Operator-anchored against the M-200's own display (every anchor lands):

| M-200 display | value | `-10 - value` |
|---|---|---|
| -17 dB | `0x07` | -17 ✓ |
| -40 dB | `0x1e` | -40 ✓ |
| -60 dB | `0x32` | -60 ✓ |
| -65 dB (max) | `0x37` | -65 ✓ |
| -10 dB (min) | `0x00` | -10 ✓ |

## The checksum invariant

`CH + PARAM + VALUE + CKSUM == 0x7e` — held across **all 376 op-0403 frames**, two channels, all
three parameters, and the full 56-step sweep. Worked examples:

```
ch1 phantom off : 00 + 00 + 00 + 7e = 0x7e
ch1 phantom on  : 00 + 00 + 01 + 7d = 0x7e
ch3 phantom on  : 02 + 00 + 01 + 7b = 0x7e
ch3 SENS  0x05  : 02 + 02 + 05 + 75 = 0x7e
ch1 SENS  0x37  : 00 + 02 + 37 + 45 = 0x7e
ch1 PAD  on    : 00 + 01 + 01 + 7c = 0x7e
ch3 PAD  on    : 02 + 01 + 01 + 7a = 0x7e
```

This is what proves CH/PARAM/VALUE are the **only** semantic fields — anything else moving would
break the sum.

## Method (why this worked)

- **Passive mirror-port capture**; we stopped being master first, so the segment carried only the
  M-200 ↔ S-0808 conversation.
- **One variable at a time**, labelled: phantom ch1, phantom ch3, SENS ch3, SENS ch1 — the 2×2 is
  what proves channel and parameter are independent rather than one coupled field.
- **Sweep, don't sample**: two gain values only prove a byte moved; the full `0x00..0x37` ramp is
  what revealed the encoding is linear at 1 dB/step.
- **Control is 1 frame in ~2000** — filtering `ether[16:2] != 0x0000` (non-FILLER) drops the
  8000 fps audio and makes a permanent capture ~4 KB/s instead of 8 MB/s.

## Evidence

- `ctl-session1-precut.pcap` — phantom ch1/ch3 + SENS ch3 (338,290 control frames)
- `ctl2.pcap` — SENS ch1 full sweep, 206 op-0403 frames, both endpoints anchored
- `enrol-00-control.pcap` — the M-200 enrolling the S-0808 from cold (a box declares its model
  **once**, at enrolment; a prior 24001-frame steady-state capture contained no config-announce)
- `00-timeline.md` — UTC-stamped operator actions

## NOT yet decoded

(Polarity was expected here as another `PARAM` on op-0403. It is not — see the negative-results
section below: it never reaches the box at all, because it is not the box's parameter.)

- The fixed preamble `000200fe0ef0410a0000 1212 0101` — constant across every frame observed;
  purpose unknown (session/target addressing?). Do not assume it is constant for other box models
  or master generations (see reac-pw #135: per-generation decode).
- Whether the box **acknowledges** a command (upstream reply not yet analysed).

## The frame census — every op the M-200 emits

**All REAC control is BROADCAST** (`ff:ff:ff:ff:ff:ff`), including box commands. There is no
unicast addressing on this protocol, so *who a frame is for* cannot be read off the destination MAC
— only off the payload. (This killed an earlier argument of ours that assumed otherwise.)

| type | op | n | meaning |
|---|---|---|---|
| `cfea` | `ffff` | 2892 | master announce |
| `cdea` | `0103` | 2858 | channel-list heartbeat |
| `cdea` | `0403` | 376 | **source control** — params `00` phantom, `01` pad, `02` SENS |
| `cdea` | `0100` | 1364 | SCENE/SYSPARAM bulk data (see below) — **not** box traffic |
| `cdea` | `0101` | 4 | bulk-transfer START marker (carries the ASCII name) |
| `cdea` | `0102` | 4 | bulk-transfer END marker |

### `op=0100/0101/0102` — console memory, not stagebox control

A 47-second burst of 1364 frames. It is **not** a fader stream: it is 5 distinct payload shapes
cycling ~5×/sec (a sweep would produce ~56 *different* values), bracketed by `0101` start and `0102`
end markers. The markers carry ASCII: **`SCENE`**, **`SYSPARAM`**, `1234`. **Zero** of the 1372
frames contain the S-0808's MAC, and a stagebox has neither scenes nor system parameters.

**Unexplained:** the burst coincides with a MAIN-fader sweep, and we could not establish a trigger.
Recorded as an open question rather than explained away.

## Negative results — the ownership boundary (measured, not assumed)

**Polarity (Ø), PAN and MAIN LEVEL never reach the box.** All three were exercised on the M-200
while the tap was demonstrably live, and the `op=0403` count never moved. Announce and heartbeat
kept flowing throughout, so the capture was not stalled — the source-control channel was silent.

MAIN was the test that could have broken the rule: the S-0808 has eight **outputs**, so an analog
output-level stage would have been a plausible box parameter. It is not one — the box's outputs are
dumb converters at fixed level, and the console sends samples already at the right amplitude.

> **Method warning, learned the hard way.** We first "confirmed" the MAIN negative by counting
> `op=0403` alone, and nearly published it while an op we were not counting (`0100`) was carrying
> 1364 frames during the very same sweep. A negative result is only as wide as the census behind it.
> **Always re-census ALL ops before claiming silence.**

**The rule — the protocol carries ONLY what cannot be done in software.** The stagebox owns exactly
three things, and they are exactly the three that are physically impossible anywhere else:

- **+48 V** — a voltage on the XLR pins
- **PAD** — analog attenuation *before* the preamp (you cannot un-clip a sample)
- **SENS** — the analog gain stage *before* quantisation (buys real signal-to-noise)

Everything else is arithmetic on samples, and arithmetic belongs to whoever is already performing
it. Polarity is a sign flip; pan is amplitude maths on a mix bus the S-0808 does not have; main is
a gain on a mix the box never sees. None of them are the box's to own, so none are on the wire.

**The box-side surface is three controls** — all of them pre-converter, exactly as the rule
predicts. Pad was found *because* the rule predicted it: it was a falsifiable test that could have
broken the theory, and instead confirmed it.

### What this means for openmixer

| control | physical owner | openmixer today |
|---|---|---|
| Phantom +48 V | **the box** | state-only (#93) — a button that lies. Now implementable. |
| **PAD (-20 dB)** | **the box** | **absent entirely.** Now implementable — and it *shifts SENS by +20*. |
| SENS (head-amp) | **the box** | absent. Now implementable — and NOT the same thing as trim. |
| Polarity (Ø) | **the console** | **already correct** — native DSP `sgain = polarity ? -gain : gain` |
| Trim / pan / main | **the console** | already correct — digital, post-converter |

openmixer's native-DSP polarity is not a workaround for missing hardware control: **it is what
Roland does too.** The reference implementation agrees with us.

Note there are genuinely **two** gains and a real desk has both: the box's analog **SENS** (buys
signal-to-noise; must be set right before anything downstream matters) and the console's digital
**trim** (fine adjustment after the fact). openmixer currently has only the second.

**Caveat on the negatives:** absence of evidence is the weakest evidence, and this document already
contains one instance of us getting it wrong (see the method warning above). It is strong here — a
full six-op census, and the physics agrees — but if a console ever carries polarity over a path we
are not watching (a different EtherType, or Roland's separate RUI network), this capture would not
show it. Re-test against ALL traffic, not just `0x8819`, before treating it as universal.

**Still open:** the pad-ON SENS endpoints (`-45 … +10`) are derived from the measured +20 offset and
two display anchors, not from a full pad-ON sweep. Worth 60 seconds on the next box day.
