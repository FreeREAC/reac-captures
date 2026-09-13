# The master announce's unknown bytes, the head-amp base, and where SP mode is not

Two fields in `reac-protocol/wire-format.md` are labelled unknown — `unknown1[9]` at `data[0..8]`
of the `cf ea` MASTER_ANNOUNCE and `unknown2[4]` at `data[17..20]` — and one rule, the head-amp
channel base, is stated there as off-wire session state. This pass reads every announce and every
head-amp sweep in the corpus and settles all three. It also answers, with a presence control, the
question the operator asked on top: whether any of it is the SP (split) path, and whether the
corpus holds a single frame from a split device.

## What was read, and the control that says the read happened

111 pcap files under `~/Devel/audio/reac-captures`, every `.pcap`, `.pcapng` and the eleven
`m200-headamp-re/*.pcapNN` split parts. 6 910 724 pcap records, **6 450 414 REAC frames** after
dropping each mirror's second copy (a frame byte-identical to its immediate predecessor; the
free-running u16 counter at `frame[14:16]` makes two distinct frames never identical).

Instruments, all written for this pass against `libreac` @3abd0ba built in a scratch copy —
`announce_census`, `enrol_facts`, `pps_scan`, `width_scan`, `split_hunt`. They read through
`pcap_source_next`, which strips the 802.1Q tag before the REAC check, so the VLAN-tagged
2026-09 captures and the untagged older ones are read the same way. Three independent runs
report the same 6 450 414 REAC frames, which is the cross-check that the scans agree on what
they scanned.

Frame types, whole corpus, at the type word `frame[16:18]`:

| type | name | frames | files |
|---|---|---:|---:|
| `0x0000` | FILLER | 5 962 839 | 89 |
| `0xcdea` | CONTROL | 470 535 | 108 |
| `0xcfea` | MASTER_ANNOUNCE | **17 040** | 105 |
| `0xceea` | SPLIT_ANNOUNCE | **0** | 0 |
| `0xc2ea` | ENDING | **0** | 0 |

Those five rows come out of one scan, so the two zeros are readable: the same pass that found
no split frame found 17 040 announces and 470 535 control frames. There are no other type words.

The 17 040 announces come from **11 emitter MACs** and collapse to **35 distinct 32-byte blocks**
(36 distinct MAC+block pairs). Every one of the 35 sums to **0 mod 256** — the block checksum
verifies, so `data[31]` is the checksum and the bytes in front of it are not garbage.

## 1. `unknown1[9]` — `data[0..8]`

**Constant. 17 025 of 17 025 announces carrying a non-zero block read**

```
ff ff 01 00 01 03 0d 01 04
```

It does not vary with emitter class (4 console models, 2 boxes in master mode, our own two
stacks), with rate (44.1 / 48 / 96 kHz), with box width (8 / 16 / 32), or with position in the
session: of the 105 files that carry an announce, **105 open with this prefix** on the file's
first announce, and no later announce in any file departs from it.

The only 15 announces in the corpus that do not carry it are all-zero blocks — one M-5000
(`00:40:ab:ca:15:4c`) in
`captures/m5000-s1608-96k-mirror__matrix-m5000-s1608-2026-07-11.pcap`, at announce ordinal 49,
so mid-session and not a first announce. A zeroed block is what a device broadcasts before it
links; it is an absence of content, not a variant.

**The nine bytes are three fields, not one.** `spec/reac.ksy`'s `cfea_payload` already splits
them and the corpus agrees:

| data | reading |
|---|---|
| `0..1` | `ff ff` — the record's op, `control_op::announce` (`0xffff`), exactly where `cd ea` carries `01 03` |
| `2..3` | `01 00` — the record length/count field, as `cd ea` carries `00 10` |
| `4..8` | `01 03 0d 01 04` — a five-byte record header whose **third byte, `data[6]`, is the announce kind** |

`data[6]` reads **`0x0d` on 17 025 of 17 025**. `0x0a` — documented as the split-announce
response — appears **zero** times. `0x0e` appears zero times and is not a documented value in
any source: the firmware trees hold no branch on this byte at all (the box CPU never sees the
type word; `reac-firmware-re/FIRMWARE-INDEX.md:26` records that ethertype, end marker and frame
length are applied by the FPGA and are in no firmware image), and the docs corpus names only
`0x0d` and `0x0a`.

The split-confirm form the inherited driver documents, `ff ff 01 00 01 03 0a 02 02`
(`wire-format.md:197`), differs from the primary form in exactly `data[6..8]` — so those three
bytes are the kind tuple and `data[0..5]` is the fixed announce header. The `0xceea`
SPLIT_ANNOUNCE forms in the same source (`01 00 <id> 00 01 03 08 43 05`, `… 08 42 05`,
`… 02 41 05`) have the same shape: `01 03` at `data[4..5]`, a three-byte kind at `data[6..8]`.
That is a structural reading, not a measurement — no `0xceea` frame exists to check it against.

**So: `unknown1[9]` is not unknown and is not one field.** It is `op(2) + len(2) + header(5)`,
and only `data[6]` is a discriminator. Nothing in it varies in this corpus.

## 2. `unknown2[4]` — `data[17..20]`

The table row `01 <split?> 01 00` is wrong in three of its four bytes. Measured:

| data | wire-format.md says | corpus says | frames |
|---|---|---|---|
| 17 | `0x01`, constant | **the PACE CODE**: `0x00` 48 kHz, `0x01` 96 kHz, `0x02` 44.1 kHz | `0x00`×15 315, `0x01`×1 487, `0x02`×238 |
| 18 | `0x01` after a split-announce-response, else `0x00` | **high byte of the enrolled-box count**, `u2` BE at `data[18:20]` | `0x00` ×17 040 — never anything else |
| 19 | `0x01`, constant | **low byte of that count** | `0x00`×3 232, `0x01`×13 808 |
| 20 | `0x00` | the first of eleven pad bytes | `data[20..30]` is zero on **17 040 of 17 040** |

`data[17]` is a rate class, and the rate is **measured, not read off a filename**. `pps_scan`
takes the longest gap-free run per talker and REAC sends 12 samples per frame, so pps × 12 is
the rate; the measured values cluster at 3675, 4000 and 8000 pps with nothing in between.

| emitter | measured pps | rate | `data[17]` | announce frames | files |
|---|---:|---|---|---:|---:|
| M-200 `00:40:ab:c9:cc:03` | 3675 | 44.1 kHz | **`0x02`** | 238 | 4 |
| M-200 `00:40:ab:c9:cc:03` | 4000 | 48 kHz | **`0x00`** | 35 | 7 |
| S-1608 `00:40:ab:c4:80:3b` in master mode | 8005 | 96 kHz | **`0x01`** | 150 | 4 |
| S-4000S `00:40:ab:c4:08:bc` in master mode | 8000 | 96 kHz | **`0x01`** | 8 | 1 |

Two controls make that a rate reading and not a device reading. **Within one device:** the same
M-200 MAC writes `0x00` at a measured 4000 pps and `0x02` at a measured 3675 pps
(`m200-enrol-441k-2026-09-13/enrol-bounce-slice.pcap`,
`m200-enrol-s4000-441k-2026-09-13/enrol-bounce-slice.pcap`,
`m200-master-441k-2026-09-11/box-boot-with-our-slave-present-12h03-12h06.pcap`,
`courtship-trial-2026-09-12/two-reboots-06h49-07h02-sampled.pcap`). **Within one rate, across
device classes:** at a measured 8005 pps an S-1608 and an S-4000S, neither of them a console,
both write `0x01` (`box-to-box-2026-09-13/enrol-{main,backup}-port-slice.pcap`;
`captures/reacpw-m5000-s4000s-96k-direct__s4000s-c408bc-filler-only-no-coldconnect-2026-08-30.pcap`).
Every M-5000 announce in the corpus reads `0x01` and every M-200i, M-300 and `deskc9919c/d`
announce reads `0x00`, which is why the byte once read as a console generation.

`data[18:20]` is the enrolled-box count and its behaviour is visible as a transition, not just a
value: **43 files carry both `0x0000` and `0x0001`** from the same talker, and the timeline in
`m200-enrol-441k-2026-09-13/analysis.md` shows it going 1 → 0 when the box drops and 0 → 1 after
the grant. The high byte has never been anything but zero, so `<split?>` at `data[18]` is refuted
by 17 040 frames: it is a count's high byte, and the count has never reached 256.

### Two neighbouring bytes the same scan corrects

Not asked for, but the same rows make the naming beside `unknown2` wrong, and a reader of the
table will hit them first.

`data[15]` is **not** "master in-channel count". It is `0x28` (40 — the whole downstream fabric,
and the 1492-byte frame is 40 channels) on **every console and on both of our stacks**, 16 867
frames. It reads `0x10` on the S-1608 in master mode (150) and `0x20` on the S-4000S in master
mode (8) — each box's own declared input width.

`data[16]` is **not** "master out-channel count". It is the **upstream width in force on the
segment**: `0x08` / `0x10` / `0x20` tracking the enrolled box, and falling back to `0x08` while
`data[18:20]` is zero. `width_scan` proves the "in force" wording rather than "the box's declared
width": in `box-to-box-2026-09-13` the S-4000S `00:40:ab:c4:06:80` **declares 32 inputs** and
sends **340-byte (8-channel)** upstream frames, and the S-1608 master announces `data[16]=0x08`;
under a real console the same box class sends 1204-byte (32-channel) frames and the console
announces `data[16]=0x20`
(`captures/m200i-s4000s-48k-mirror__matrix-m200-s4000-2026-07-24.pcap`).

`data[9..14]` is the announced master MAC and equals the source MAC on every real device. The
only 147 exceptions are ours: `00:40:ab:00:00:01` announcing the M-5000's MAC `00:40:ab:ca:15:4d`
in `captures/reacpw-none-96k-clean__s1608-master-{bounce,first-link}-2026-07-06.pcap`. A desk MAC
in this field is not proof of a desk.

### Two defects in our own emitters, from the same rows

- `34:5a:60:9f:9e:be` writes `data[17]=0x01` in every announce it has ever sent, including in
  48 kHz captures (`s1608-bank-2026-08-22/reacpw-s1608-48k-clean__nightR-wire*.pcap`). It should
  write the pace code of the rate it is pacing.
- The same MAC writes `data[16]=0x20` in the six
  `headamp-boxmaster-2026-09-11/segments/seg0*.pcap` files while the only box present declares
  16 inputs. It should track the enrolled box.

## 3. The head-amp sweep base

**The base is the chassis strap the box announces: `base = config-announce block[7] × 0x10`.**
That is `libreac`'s rule (`include/reac/reac_ports.h:61-100`) and the corpus does not contradict
it anywhere. `wire-format.md:658` still says "No byte on the wire carries this… it is negotiated
session state"; that is the statement this section replaces.

35 files carry exactly one box's config announce **and** a head-amp sweep, so the join is
unambiguous. In all 35 the sweep's lowest channel equals `block[7] × 0x10`:

| box | declared in | `block[4]` selector | `block[7]` strap | sweep span | distinct CH | files |
|---|---:|---|---|---|---:|---:|
| S-0808 | 8 | `0x84` | `0x00` | `0x00`–`0x07` | 8 | 9 |
| S-1608 | 16 | `0x82` | `0x02` | `0x20`–`0x2f` | 16 | 20 |
| S-4000S | 32 | `0x84` | `0x00` | `0x00`–`0x1f` | 32 | 6 |

(Six of the 20 S-1608 rows are partial sweeps — 2 or 6 channels, a live edit rather than an
enrolment — and they start at `0x20` like the rest.)

### What does NOT key it

- **Not the input width.** An 8-input box and a 32-input box are both addressed at `0x00`. A
  width table happens to agree on the three chassis we own only because width and strap are
  collinear across them.
- **Not the console.** Four consoles address the same box at the same base:

  | box | M-200 | M-200i | M-300 | M-5000 | reac-pw |
  |---|---|---|---|---|---|
  | S-0808 | `0x00` (6) | — | `0x00` (1) | `0x00` (1) | `0x00` (1) |
  | S-1608 | `0x20` (13) | `0x20` (1) | `0x20` (1) | `0x20` (5) | — |
  | S-4000S | `0x00` (4) | — | — | `0x00` (2) | — |

- **Not the rate.** The S-4000S is addressed at `0x00` in captures whose pace code reads `0x00`,
  `0x01` and `0x02`; the S-1608 is addressed at `0x20` at 48 kHz and at 44.1 kHz
  (`m200-enrol-441k-2026-09-13/enrol-bounce-slice.pcap`).
- **Not the group map's slot.** All **63 ENROLL group-map frames** in the corpus collapse to five
  templates, and every one is front-packed from the first input-group slot:
  `04 PP 41 00 00 00 00 00 c3 c3 c3 c3` (8-input, 57 frames) or
  `04 PP 41 41 41 41 00 00 00 00 00 c3` (32-input, 6 frames). The `0x41` run is 1 long or 4
  long, never 2, and always starts at slot 0, so the map cannot distinguish the two boxes that both base at `0x00` — and,
  decisively, **the one box whose base is not zero never receives a group map at all**. 21 files
  carry both a group map and a head-amp sweep and every one of them is an 8- or 32-input box at
  base `0x00`; across the whole corpus no group map is ever addressed to a 16-input declarer.
  A map that is never sent cannot be what assigns that box its base.
- **Not `unit_offset` or a box index.** `(box_index << 5)` is refuted the same way it always was:
  the 32-channel S-4000S bases at 0 like the 8-channel S-0808.

### The one carrier still collinear with the strap, and the new evidence against it

Every `0x82` declarer in the corpus straps `0x02` and every `0x84`/`0x80` declarer straps `0x00`,
so a head-amp measurement alone cannot separate the **selector** from the **strap**. Two things
break the tie without a new sweep.

First, the firmware: `reac-firmware-re/devices/S-1608/decompile/S-1608_alldecomp.c:5866-5867`
has `FUN_0c003c8a` writing `puVar1[7] = (*(code *)PTR_FUN_0c0040e8)()` — block[7] is filled from
a function-pointer call that `HEADAMP-FABRIC-BASE-2026-08-23.md:105` traces to the GPIO strap at
`*0x0c080918`, read before the RTOS starts. Byte 7 is a hardware property of the chassis.

Second, and new in this corpus: **the selector moves with the peer and the strap does not.** The
same physical S-4000S, `00:40:ab:c4:06:80`, emits two config-announce blocks that differ in
exactly one byte plus its checksum —

```
0103 0010 84 000000 020202020202020201010303 0003000000010000000000 4c   under a console
0103 0010 80 000000 020202020202020201010303 0003000000010000000000 50   under a box master
```

`0x84` in the three console captures, `0x80` in `box-to-box-2026-09-13/enrol-{main,backup}-port-slice.pcap`,
strap `0x00` and all twelve inventory cells unchanged in both. A base derived from the selector
would move when the box is patched into a box master; a GPIO strap cannot. (This also closes
`wire-format.md:679` — "settling it needs a box-to-box enrolment, a pairing the corpus lacks
entirely". The corpus now has one, and it is where the `0x80` selector arm finally appears: 2
files, the only `0x80` declarations anywhere.)

**No box in master mode ever sweeps head-amp.** Neither `00:40:ab:c4:80:3b` nor
`00:40:ab:c4:08:bc` emits a single head-amp record in any capture, consistent with the measured
finding that a box in M mode ignores head-amp.

## 4. Split (SP) mode

### (a) Do any of the still-unnamed announce bytes belong to the split path?

Yes — the announce is the split path's *other half*, and that is precisely why those bytes
looked unknown. In the handshake as documented (`wire-format.md:891-908`) the split device is a
passive listener that sends `0xceea` SPLIT_ANNOUNCE, and **the master answers inside a
MASTER_ANNOUNCE**: `data[6] = 0x0a`, `data[9..14]` = the split's MAC, `data[15] = 0x00`,
`data[16] = 0x60` (the assigned split identifier). So four of the bytes this pass measured are
the split response's carriers.

None of them has ever carried a split value on our wire:

| byte | split value | corpus |
|---|---|---|
| `data[6]` | `0x0a` | `0x0d` × 17 025, `0x0a` × **0** |
| `data[15]` | `0x00` | `0x28`/`0x10`/`0x20`; `0x00` only in the 15 all-zero blocks |
| `data[16]` | `0x60` | `0x07`/`0x08`/`0x10`/`0x20`; `0x60` × **0** |
| `data[18]` | `0x01` "after a split-announce-response" | `0x00` × 17 040 |

The `<split?>` reading of `data[18]` is therefore refuted twice over — no split exchange has ever
occurred in this corpus, *and* the byte has an established non-split job as the high half of the
enrolled-box count.

`unknown1[9]` itself is **not** split-specific: its nine bytes are the announce's op, length and
record header, and only `data[6]` would change for a split response.

### (b) Does the corpus hold any frame from a split device?

**No.** Zero `0xceea` and zero `0xc2ea` at the type word across 6 450 414 REAC frames in 111
files, against 17 040 `0xcfea` and 470 535 `0xcdea` found by the same scan.

A byte-pattern sweep of `frame[0:52]` — not just the type word — finds `ce ea` 95 times and
`c2 ea` 97 times, and every one of them is accounted for: 95 + 96 sit at **offset 14**, the
free-running frame counter, and one `c2 ea` sits at offset 50, the first audio byte. Not one is
at a type-word position.

This is consistent with every source. `libreac/src/reac_disco.c:89` calls SPLIT_ANNOUNCE
"real gear, none captured"; `reac-protocol/firmware-findings.md:267` lists
"`ce ea` / `c2 ea` … not verified (need a real split device / topology)" as an open item;
`reac-firmware-re/REAC-FSM-EVIDENCE.md:265-267` says the split path appears in zero corpus
captures. The names `SPLIT_ANNOUNCE`, `0xceea` and `0xc2ea` and the whole five-step handshake
come from **`per-gron/reacdriver`** — a GPL-3.0 reverse-engineered macOS driver — by way of
reac-aes67's `REAC-PROTOCOL.md §6`. No Roland manual and no capture. The `0xc2ea` byte pair has
a second, unrelated life as obs-h8819's frame-end marker near byte 1490, which is a good reason
to keep the two claims apart.

The firmware side is an empty box with a label on it. The S-4000S image carries the RTTI names
`CSplitSciMsgParser` and `CSplitTDataKikiMsgParser`, and the M-400 image carries a
`CSplitReacManager` vtable at `0x8c45adfc` — but none of them is decompiled, and a literal
search for `0xce` in `devices/S-4000S/decompile/S-4000_alldecomp.c` returns zero against a
positive control of 6 632 `FUN_0c` hits in the same file. There is no recovered split behaviour
to read, only a class name.

What *is* rig-measured about SP is the mode switch itself (`wire-format.md:306-330`): the
three-position REAC Mode switch is read at boot and never re-read, **SP splits the box's I/O
across two REAC ports so two consoles share one stagebox**, and **M is the splitter's clock role**
— clock-slave on the uplink, master on the split outputs. M and SP are two halves of one feature.
That is why the box-to-box captures matter: they are the M half, already taken.

### (c) The rig that would capture it

Everything needed is already in the building. The split-capable chassis is the S-4000 series, and
there are two units in the corpus — `00:40:ab:c4:06:80` and `00:40:ab:c4:08:bc`. The topology:

- **The box.** One S-4000S, REAC Mode switch to **SP**, then power-cycled — the switch is read at
  boot and never re-read, so flipping it on a running box changes nothing and would read exactly
  like "SP is not implemented". Confirm the mode took before trusting any negative: an SP box
  must present on *both* REAC ports, so a port that stays silent is the control that says the
  reboot did not take.
- **Port A → VLAN A → the M-200** (`00:40:ab:c9:cc:03`). This is the known-good side and the
  clock side: the console is the sample-clock master and the box recovers word clock from its
  arrival cadence. Run it at 48 kHz, not 96 — the loss budget is ~600 frames, so 48 kHz gives
  ~150 ms of tolerance against ~75 ms, and a split handshake is a once-per-session event that
  must not be lost to a hiccup.
- **Port B → VLAN B → reac-pw** as the second master, on its own tagged segment. reac-pw must
  announce with `data[17] = 0x00` for this to be a 48 kHz segment — it currently hard-writes
  `0x01`, so fix that defect first or the second console announces the wrong rate class. reac-pw
  is the right second master rather than a second desk precisely because it can be instrumented:
  it can be made to answer a `0xceea` with a `data[6]=0x0a` MASTER_ANNOUNCE, which is the one
  step of the handshake no capture can supply on its own.
- **One mirror port carrying both VLANs**, single capture file, snaplen ≥ 512 so the whole
  control block and the scene header survive. `pcap_source` strips the 802.1Q tag, so one tagged
  capture reads as two segments without any post-processing.

What to expect, and where:

| where | expect |
|---|---|
| VLAN A | the ordinary establishment: FILLER flood, cold-connect, grant, config announce `01 03 00 10`, `cfea` at ~1/s with `data[6]=0x0d` and `data[18:20]` going `0x0000` → `0x0001` |
| VLAN B | **`0xceea` from the box**, unicast, periodic — the first one ever captured. Its `data[0..8]` should read `01 00 7f 00 01 03 08 43 05` followed by the box's MAC if the inherited driver is right |
| VLAN B | reac-pw's reply: a `0xcfea` with `data[6] = 0x0a`, `data[9..14]` = the box's MAC, `data[15] = 0x00`, `data[16]` = an assigned split id |
| VLAN B | the box's second `0xceea`, `… 08 42 05`, echoing the id at `data[2]`; then keep-alives `… 02 41 05` |
| either | `0xc2ea` on teardown — unplug port B while port A stays up |
| both | a head-amp sweep on VLAN A only, base `0x00` (the S-4000S straps `0x00`). **Whether the SP box sweeps head-amp on the split port is the second question this rig answers**, and it bears on which console owns the preamps in a shared-box installation |

Two measurements make the capture worth the patch time even if the split handshake never appears.
The box's config announce on port B tells us whether `block[4]` takes a third selector value in SP
mode — it already takes `0x80` under a box master and `0x84` under a console — and whether
`block[7]`, the strap, stays `0x00` on both ports. If the strap is the same on both ports and the
selector differs, the head-amp base question closes completely.

## What stays unknown

- **`data[6] = 0x0e`.** Named in the brief, not present in this corpus, and not documented in any
  source read here — not `wire-format.md`, not `reac.ksy`, not `protocol-facts.yaml`, not either
  firmware tree. The same greps return dense hits for `0x0d` and `0x0a` in this role, so the
  absence is real and not a broken search. If `0x0e` came from somewhere, that source needs
  naming before the value goes in a table.
- **`data[20..30]`, eleven bytes.** Zero on 17 040 of 17 040 announces. They may be padding or
  they may be a field no device in this building populates. A corpus of one value cannot tell
  those apart, and the split response is the most likely place a value would appear.
- **The whole `0xceea` / `0xc2ea` grammar.** Source-derived from `per-gron/reacdriver`, never
  captured, never seen in a decompile. It should stay marked as inherited until the rig in §4(c)
  produces a frame.
- **Selector versus strap for the head-amp base.** They remain collinear across the three chassis
  we own. The strap is the better-founded reading — firmware sets it from a GPIO read, and the
  selector is now measured to change with the peer while the strap does not — but the separating
  measurement is a box whose selector and strap disagree, and we do not have one.

---

# Proposed wire-format.md edits

Three replacements. The integrator applies them; this file does not touch `reac-protocol`.

## Edit 1 — the MasterAnnouncePacket overlay line and table (currently lines 192-204)

Replace lines 192-204 — from `Overlaid on \`data[]\`:` through the end of the table and the
`A receiver recovers the master from ...` paragraph that follows it — with:

````
Overlaid on `data[]`: `{op[2]; len[2]; header[5]; address[6]; totalSlots;
upstreamWidth; paceCode; boxCount[2]; pad[11]; checksum}`. There are no unknown
fields left in this block: all 32 bytes are named, and the block checksum verifies
on all 35 distinct blocks in the corpus.

| data | field | notes |
|---|---|---|
| 0..1 | op | `ff ff` = `control_op::announce`, the same slot `cd ea` uses for `01 03`. Constant on 17 025 of 17 025 announces |
| 2..3 | len | `01 00`. Constant |
| 4..8 | header[5] | `01 03 0d 01 04`. `data[6]` is the **announce kind**: `0x0d` = primary announce (the only value ever captured — 17 025 of 17 025, across 4 console models, 2 boxes in master mode, 3 rates and 105 files); `0x0a` = the split-announce response, whose header form is `01 03 0a 02 02`. `0x0a` has **never** been captured. The three bytes `data[6..8]` move together as the kind tuple; `data[0..5]` is fixed |
| 9..14 | address[6] | the announcing master's MAC. Equals the source MAC on every real device; only our own stack has ever announced a MAC it does not own |
| 15 | totalSlots | `0x28` (40) — the whole downstream fabric, matching the 1492-byte 40-channel frame — on every console, 16 867 frames. A **box in master mode** writes its own declared input width instead: `0x10` on an S-1608, `0x20` on an S-4000S |
| 16 | upstreamWidth | the upstream width **in force on the segment**: `0x08` / `0x10` / `0x20`, tracking the enrolled box, and falling back to `0x08` while `boxCount` is zero. It is the width actually being sent, not the box's declaration: in `reac-captures box-to-box-2026-09-13` an S-4000S that declares 32 inputs sends 340-byte (8-channel) upstream frames under a box master and the master announces `0x08` |
| 17 | paceCode | the **rate class**: `0x00` = 48 kHz, `0x01` = 96 kHz, `0x02` = 44.1 kHz. The same carrier as the ENROLL group map's `block[6]` and the chanmap section marker's second byte |
| 18..19 | boxCount | `u2` big-endian, enrolled boxes. `0x0000` → `0x0001` when a box commits and back when it drops; 43 corpus files carry both values from one talker. The high byte has never been non-zero |
| 20..30 | pad[11] | zero on 17 040 of 17 040. Unread; a value here has never been observed |
| 31 | checksum | the block's 8-bit modular checksum (see the `data[32]` section) |

A receiver recovers the master from `data[6]==0x0d`, MAC = `data[9..14]`,
fabric = `data[15]`, upstream width = `data[16]`, rate class = `data[17]`, and
whether a box is enrolled from `data[18:20]`.

**The pace code is measured, not inferred from a filename.** One M-200
(`00:40:ab:c9:cc:03`) writes `0x00` at a measured 4000 pps and `0x02` at a measured
3675 pps; at a measured 8005 pps an S-1608 and an S-4000S — neither of them a
console — both write `0x01`. Corpus totals: `0x00` x15 315, `0x01` x1 487,
`0x02` x238 over 17 040 announces in 105 files
(`reac-captures analysis/2026-09-13-announce-bytes-and-headamp-base.md`).
````

## Edit 2 — appended to the "Split handshake (fully specified)" section (line 892), after its
step 5 and the master-accepts paragraph (line 908)

Append:

````
**None of this has ever been on the wire.** The handshake above is source-derived
from `per-gron/reacdriver` by way of reac-aes67's `REAC-PROTOCOL.md` §6; there is no
capture and no decompiled firmware behind it. Measured against the whole corpus —
111 files, 6 450 414 REAC frames — there are **zero** `0xceea` and **zero** `0xc2ea`
frames at the type word, against 17 040 `0xcfea` and 470 535 `0xcdea` found by the
same scan. A byte-pattern sweep of `frame[0:52]` finds `ce ea` 95 times and `c2 ea`
97 times and every one is the free-running counter at offset 14 or a single audio
byte at offset 50; none is a type word.

The four announce bytes this handshake would move are all pinned to their non-split
values across the corpus: `data[6]` is `0x0d` on 17 025 of 17 025, `data[15]` is
never `0x00` except in an all-zero block, `data[16]` is never `0x60`, and `data[18]`
is `0x00` on 17 040 of 17 040 — `data[18]` is the high byte of the enrolled-box
count, not a split flag.

Capturing it needs an S-4000 series box with its REAC Mode switch set to **SP** and
power-cycled (the switch is read at boot and never re-read), one port on a VLAN to a
console and the other on a VLAN to a second master, and one mirror port carrying both
VLANs.
````

## Edit 3 — the head-amp base section (replaces lines 648-686)

Replace the section heading `### CH carries a BASE keyed on the box's DECLARED WIDTH` (line 648)
and its body, through the block quote ending `... runs past the \`0x2f\` ceiling).` (line 686),
with:

````
### CH carries a BASE the box ANNOUNCES: config-announce `block[7]` x `0x10`

```
CH = base + (box_input - 1)
base = config-announce block[7] * 0x10

 S-0808   8 in   block[7] = 0x00  ->  base 0x00  ->  0x00..0x07
 S-1608  16 in   block[7] = 0x02  ->  base 0x20  ->  0x20..0x2f
 S-4000S 32 in   block[7] = 0x00  ->  base 0x00  ->  0x00..0x1f
```

**A byte on the wire does carry this**, and it is the box's own property, not
negotiated session state. `block[7]` of the config announce (`01 03 00 10`) is a
GPIO chassis strap the box reads before its RTOS starts — S-1608 firmware
`FUN_0c003c8a` writes `buf[7]` from the strap at `*0x0c080918` and
`FUN_0c007fbc(bank, group)` applies it — so a master cannot move where a head-amp
write lands by granting differently.

Measured on 35 corpus captures that carry exactly one box's config announce and a
head-amp sweep: the sweep's lowest channel equals `block[7] * 0x10` in all 35, over
three box models and four consoles, at 44.1, 48 and 96 kHz.

**A per-width table is wrong even though it agrees here.** The retired mapping
(8 -> 0, 16 -> 32, 32 -> 0) matches every chassis we own only because width and strap
are collinear across those three. An 8-input box and a 32-input box are **both**
addressed at `0x00`, so a width cannot be what selects a base; the first box that
breaks the collinearity would have its preamps addressed 32 slots off with every
gate still green. `(box_index << 5)` is refuted the same way.

**The ENROLL group map does not assign it either.** Every group map in the corpus is
front-packed from the first input-group slot, so a 1x`0x41` map and a 4x`0x41` map
both describe a box at base `0x00` and the map cannot separate them. Decisively, the
one box whose base is **not** zero never receives a group map at all: no console in
the corpus sends one to a 16-input declarer.

**The selector and the strap are still collinear, and the strap is the better-founded
of the two.** Every `0x82` declarer straps `0x02` and every `0x84`/`0x80` declarer
straps `0x00`, so no head-amp measurement separates them. But one S-4000S
(`00:40:ab:c4:06:80`) has now been captured emitting `block[4] = 0x84` under a console
and `block[4] = 0x80` under a box master, with `block[7] = 0x00` and all twelve
inventory cells unchanged: the selector follows the peer, the strap does not, and a
base that followed the peer would be absurd for a GPIO strap.

An implementation reads the base from the announce, once, when the announce parses.
It does not derive it from a width and it has no sentinel for "not known yet": a box
that has not announced has nothing to address.
````
