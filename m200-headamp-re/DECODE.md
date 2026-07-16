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
| `[23]`    | **PARAM**  | **`00` = phantom +48V · `02` = SENS (head-amp sensitivity)** |
| `[24]`    | **VALUE**  | phantom: `00`/`01` · SENS: `0x00..0x37` |
| `[25]`    | **CKSUM**  | `0x7e - (CH + PARAM + VALUE)` |

## SENS ↔ dB

Roland SENS is **input sensitivity in dBu**, so **more negative = MORE gain**.

```
dB    = -10 - value
value = -(dB + 10)

value 0x00 = -10 dB  (MIN sensitivity / least gain)
value 0x37 = -65 dB  (MAX sensitivity / most gain)
```

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

`CH + PARAM + VALUE + CKSUM == 0x7e` — held across **all 206 op-0403 frames**, two channels, two
parameters, and the full 56-step sweep. Worked examples:

```
ch1 phantom off : 00 + 00 + 00 + 7e = 0x7e
ch1 phantom on  : 00 + 00 + 01 + 7d = 0x7e
ch3 phantom on  : 02 + 00 + 01 + 7b = 0x7e
ch3 SENS  0x05  : 02 + 02 + 05 + 75 = 0x7e
ch1 SENS  0x37  : 00 + 02 + 37 + 45 = 0x7e
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

- **Polarity (Ø)** — expected to be another `PARAM` on the same op-0403 frame (`01` or `03`?).
- The fixed preamble `000200fe0ef0410a0000 1212 0101` — constant across every frame observed;
  purpose unknown (session/target addressing?). Do not assume it is constant for other box models
  or master generations (see reac-pw #135: per-generation decode).
- Whether the box **acknowledges** a command (upstream reply not yet analysed).

## Negative results — the ownership boundary (measured, not assumed)

**Polarity (Ø) and PAN never reach the box.** Both were toggled/moved on the M-200 while the tap
was demonstrably live: **532 frames arrived during those experiments and the `op=0403` count stayed
frozen at 206.** Announce (`cfea/ffff`) and heartbeat (`cdea/0103`) kept flowing throughout, so the
capture was not stalled — the source-control channel was simply silent.

Across the whole session the M-200 emits only THREE frame kinds:

| type | op | meaning |
|---|---|---|
| `cfea` | `ffff` | master announce |
| `cdea` | `0103` | channel-list heartbeat |
| `cdea` | `0403` | source control — **only** param `00` (phantom) and `02` (SENS) |

**The rule:** the stagebox owns exactly what it can physically do — **+48 V** on the XLR pins and
**SENS**, the analog gain stage before the A/D. Everything after the converter is arithmetic, and
arithmetic belongs to whoever performs it. Polarity is a sign flip on a sample; pan is amplitude
maths on a mix bus the S-0808 does not have. Neither is the box's to own, so neither is on the wire.

### What this means for openmixer

| control | physical owner | openmixer today |
|---|---|---|
| Phantom +48 V | **the box** | state-only (#93) — a button that lies. Now implementable. |
| SENS (head-amp) | **the box** | absent. Now implementable — and NOT the same thing as trim. |
| Polarity (Ø) | **the console** | **already correct** — native DSP `sgain = polarity ? -gain : gain` |
| Trim / pan | **the console** | already correct — digital, post-converter |

openmixer's native-DSP polarity is not a workaround for missing hardware control: **it is what
Roland does too.** The reference implementation agrees with us.

Note there are genuinely **two** gains and a real desk has both: the box's analog **SENS** (buys
signal-to-noise; must be set right before anything downstream matters) and the console's digital
**trim** (fine adjustment after the fact). openmixer currently has only the second.

**Caveat on the negatives:** absence of evidence is the weakest evidence. It is strong here (1704+
frames, only three ops, and the physics agrees), but if a console ever carries polarity over a path
we are not watching — a different EtherType, or Roland's separate RUI network — this capture would
not show it. Re-test against ALL traffic, not just `0x8819`, before treating it as universal.
