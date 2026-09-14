# M-200 at 44.1 kHz — two enrolments, read out

Two captures, both the same M-200 at 44.1 kHz, both a cable bounce into a re-enrolment:

| dir | box | records | window |
|---|---|---|---|
| `m200-enrol-441k-2026-09-13` | S-1608 `00:40:ab:c4:80:3b`, 16 in | 295 950 | 1789327533 – 580 |
| `m200-enrol-s4000-441k-2026-09-13` | S-4000S `00:40:ab:c4:06:80`, 32 in | 291 525 | 1789330629 – 674 |

The S-4000S session carries the ENROLL group map the S-1608 session does not, and closes §1.
Both read 3675 pps. Everything below is the S-1608 session unless the S-4000S one is named.

Capture: `enrol-bounce-slice.pcap`, 295 950 records, 295 949 REAC frames, every one 802.1Q
tagged (VLAN 12), snaplen 512. Master `00:40:ab:c9:cc:03` (M-200), box `00:40:ab:c4:80:3b`
(S-1608). Frames from `34:5a:60:9f:9e:be` are ours and are absent from this slice.

Instrument: `libreac` @3abd0ba built in a scratch tree — `group_map_scan`, `wire_census`, and two
readers written for this pass (a control-block timeline and a scene-body reassembler). The pcap
reader strips the 802.1Q tag before the REAC check (`src/pcap_source.c`), so `vlan_tagged=295950`
and `reac=295949` in the same line are the tag-awareness control.

Rate control: the longest gap-free run is 60 241 frames / 16.3903 s = **3675.35 pps** on both
talkers — 44100 / 12. The same reader reads 3999.7 pps on a 48 kHz file.

## Timeline

| t | who | event |
|---|---|---|
| 1789327533.000062 | both | slice opens, box established, console announcing `box_in_width=0x10 pace=0x02 box_count=1` |
| 1789327535.553524 | box | last frame before the bounce |
| 1789327535.553 – 548.619 | — | **13.066 s of box silence** |
| 1789327542.128116 | console | `cfea` drops to `box_in_width=0x08`, `box_count` still 1 |
| 1789327542.135952 – 542.820338 | console | scene transfer #1 (343 frames, 0.684 s) |
| 1789327543.130245 | console | `cfea` `box_count` 1 → 0 |
| 1789327544.831563 – 545.514848 | console | scene transfer #2 |
| 1789327547.525979 – 548.209600 | console | scene transfer #3 |
| 1789327548.619531 | box | first frame back |
| 1789327550.105055 | box | commit report `cdea 01 03 0010 82` |
| 1789327550.105345/.105626/.105900 | box | link-4 records: join `06 00 01 00`, head-mark `03 00 00 00`, box-ready `00 01 00` |
| 1789327550.313223 | console | `cfea` back to `box_in_width=0x10`, `box_count` 0 |
| 1789327550.317346 | console | chanmap sweep resumes at the `fe` marker |
| 1789327550.354248 | box | join climbs to `06 00 09 00` |
| 1789327551.820802 | console | **grant** `06 00 01 00` |
| 1789327551.827559 – 551.978283 | console | the rest of the burst, 55 records |
| 1789327552.317620 | console | `cfea` `box_count` 0 → 1 |

Scene transfers run at a metronomic 2.6957 s **while the box is missing** and stop once it is
back: three in the slice, none in the 28 s of steady state after the grant. The console's
declared `box_in_width` tracks the box (16 → 8 while absent → 16 on the commit report) and its
pace code never moves off `0x02`.

## 1. The 44.1 kHz pace code, and where it is carried

`cfea` block[17] (`cfea[19]` counting from the type word) reads **`0x02`** on all 47 announces
here. The scene body's `revision` at +0x14 reads **`0x0002`** in all three transfers. The
chanmap section marker's second byte reads **`0x02`** on all 6 `fe` records.

### The chanmap section marker is the pace code

Corpus-wide, per talker, over 108 files / 5 295 229 REAC frames:

| talker | model | `cfea` pace | chanmap `fe` marker |
|---|---|---|---|
| `00:40:ab:c9:cc:03` | M-200 | `0x00` ×24339, `0x02` ×192 | `0x00` ×3178, `0x02` ×24 |
| `00:40:ab:c9:cc:04` | M-200i | `0x00` ×1216 | `0x00` ×202 |
| `00:40:ab:c9:d8:5b` | M-300 | `0x00` ×1396 | `0x00` ×215 |
| `00:40:ab:c9:91:9c` / `:9d` | desk | `0x00` | `0x00` |
| `00:40:ab:ca:15:4c` | M-5000 | `0x01` ×1895, `0x00` ×30 | `0x01` ×190, `0x00` ×4 |
| `00:40:ab:ca:15:4d` | M-5000 | `0x01` ×26 | `0x01` ×4 |
| `00:40:ab:c4:80:3b` | S-1608 on M | `0x01` ×40 | `0x01` ×7 |
| `00:40:ab:c4:08:bc` | S-4000S on M | `0x01` ×8 | `0x01` ×4 |

Every real talker is collinear, including one MAC carrying two values. The decisive controls are
within-device (the same M-200 writes `0x00` at 48 kHz and `0x02` at 44.1 kHz) and
within-rate-across-class (an S-1608 and an S-4000S in master mode both write `0x01` at 96 kHz,
and neither is an OHRCA console). The byte is a **rate class**, not a console generation.

Our own two MACs are the only rows that break it: `00:40:ab:00:00:01` and
`34:5a:60:9f:9e:be` emit `pace=0x01` while writing marker `0x00` in 11 sweeps. That is a
libreac/reac-pw defect, not a counterexample.

### ENROLL[8] is the fourth carrier — `0x02` at 44.1 kHz

`m200-enrol-s4000-441k-2026-09-13`, t = **1789330642.379775**, src `00:40:ab:c9:cc:03`, one
group map, whole 34-byte template:

```
cd ea 01 03 00 0d 10 | 04 02 41 41 41 41 00 00 00 00 00 c3 | 00 … 12
```

`group_map_scan` reads it back as `console=0x02 n=1 inputs=4x8=32 out_groups=1`. It lands
209.5 ms after the box's commit report at 1789330642.170256 — the same offset as the 48 kHz
S-0808 map (209 ms), which is the presence control in the same pass.

**Same console, same map width, one byte apart:**

| rate | console | box | `cfea` pace | ENROLL[8] | map bytes |
|---|---|---|---|---|---|
| 44.1 k | M-200 `c9:cc:03` | S-4000S, 32 in | `0x02` | **`0x02`** | `04 02 41 41 41 41 00 00 00 00 00 c3` |
| 48 k | M-200 `c9:cc:03` | S-4000S, 32 in | `0x00` | `0x00` | `04 00 41 41 41 41 00 00 00 00 00 c3` |
| 48 k | M-200 `c9:cc:03` | S-0808, 8 in | `0x00` | `0x00` | `04 00 41 00 00 00 00 00 c3 c3 c3 c3` |
| 96 k | M-5000 `ca:15:4c` | S-4000S, 32 in | `0x01` | `0x01` | `04 01 41 41 41 41 00 00 00 00 00 c3` |
| 96 k | M-5000 `ca:15:4c` | S-0808, 8 in | `0x01` | `0x01` | `04 01 41 00 00 00 00 00 c3 c3 c3 c3` |

The two 32-wide rows are the same console MAC and the same box class and differ in exactly one
byte, ENROLL[8]. The byte is the **pace code** — a fourth carrier of it, not a console
generation. `0x01` only ever read as "OHRCA" because the M-5000 is the desk that runs 96 kHz.

**The map shape.** `04` is constant. ENROLL[8] is the pace code. Then five input-group slots and
five output-group slots — 5 × 8 = 40, the console's own fabric width: `0x41` front-packed, one
per group of eight enrolled inputs, `0xc3` back-packed in every slot that is not an input. An
8-input box draws `1 × 41` then `4 × c3`; a 32-input box draws `4 × 41` then `1 × c3`. Width
moves the split between the two runs and changes nothing else.

### No console sends a group map to a 16-input box

The S-1608 session carries **zero** group maps across its whole 47 s, 30 s of it after the box's
commit report. That is not a rate effect and not a capture gap: across 109 files the corpus holds
108 group maps and every one is addressed to an 8-input or a 32-input declarer. Twenty-two files
carry an S-1608 as the only box — five of them full enrolments
(`real-m200-s1608-coldboot`, `m200-s1608-BIDIR-coldboot`, `m200-s1608-COLDCONNECT-clean`,
`m200-s1608-establish-today`, and the S-1608 session here) — and not one carries a map. The
16-wide row `2 × 41` is a prediction of the width rule with no wire behind it, and may describe
a frame that is never sent.

## 2. The enrolment records

The whole link-4 exchange is 63 records: 7 from the box, 56 from the console. Record layout is
`block[14]` model, `[15]` command (`0x11` RQ1 / `0x12` DT1), `[16:18]` tag, `[18…]` payload.

**Box → console**, 1789327550.105345 – 550.354248:

| # | len | cmd | tag | payload |
|---|---|---|---|---|
| 1 | `0x0014` | `12` | `0100` | `06 00 01 00` |
| 2 | `0x0014` | `12` | `0000` | `03 00 00 00` |
| 3 | `0x0013` | `12` | `0302` | `00 01 00` |
| 4 | `0x0014` | `12` | `0100` | `06 00 01 00` (repeat, +48.6 ms) |
| 5 | `0x0014` | `12` | `0100` | `06 00 09 00` (+200 ms) |
| 6 | `0x0016` | `12` | `0500` | `00 00 02 02 00 00` (answering RQ1 #1) |
| 7 | `0x001a` | `12` | `0500` | `06 00 00 00 00 02 00 03 00 02` (answering RQ1 #2) |

**Console → box**, 1789327551.820802 – 551.978283, in order:

| # | t | len | cmd | tag | payload |
|---|---|---|---|---|---|
| 1 | 551.820802 | `0x0014` | `12` | `0100` | `06 00 01 00` — the grant |
| 2–4 | 551.827559 – .828122 | `0x0013` | `12` | `0101` | CH `0x20` params `00`=01, `01`=00, `02`=20 |
| 5 | 551.828958 | `0x0014` | `12` | `0000` | `03 00 00 00` — head mark |
| 6–11 | 551.829245 – .830557 | `0x0013` | **`11`** | `0500` | six identity REQUESTS: `00 00 04`, `06 00 08`, `10 00 11`, `10 11 09`, `11 00 11`, `11 11 09` |
| 12–56 | 551.837598 – .978283 | `0x0013` | `12` | `0101` | CH `0x21`…`0x2f`, params `00`/`01`/`02` each |

So the head-amp sweep is **48 records — 16 channels × 3 params**, addressed at base `0x20`,
which is the S-1608's slot base. Params are `0x00` phantom, `0x01` pad, `0x02` sens. The six
`0500` records are RQ1 (`cmd 0x11`), not DT1: the console *asks*, and the box answers two of the
six with the `0x0016` and `0x001a` records above, 0.75 ms later.

The console's `01 03 0010 82` commit report from the box reads byte for byte
`01 03 00 10 82 00 00 02 02 02 02 02 01 01 03 03 03 03 03 03 00…00 4c` — selector `0x82`,
`board_config_code` `0x02`, twelve cells `02 02 02 02 01 01 03×6` = 16 in / 8 out. Identical to
the golden in `libreac tests/test_ctrl.c`, checksum included.

### 44.1 kHz versus 48 kHz, same console

Compared against `m200-s1608-headamp/m200i-s1608-48k-mirror__m200-s1608-establish-today-20260721-235750.pcap`
(same console MAC, S-1608 `c4:80:41`, pace `0x00`):

- **56 records both times, same order, same lengths, same commands, same tags, same channel and
  param sequence.** Zero structural differences.
- Four payload bytes differ, all inside `tag 0101`: CH `0x25` and CH `0x2d` param `00`
  (phantom 1 vs 0), CH `0x2e` param `02` (`0x09` vs `0x1e`) and CH `0x2f` param `02`
  (`0x0a` vs `0x1d`). Those are desk settings two months apart, not rate.

**Nothing in the enrolment record set is twelve wide.** The only twelve-wide structure that
reaches the wire in this session is the box's own commit-report inventory. The console's
post-grant burst addresses head-amp **per channel**, 16 of them, not per group of four.

### 16-input box versus 32-input box, same console, same rate

The S-4000S session runs the same sequence. Console burst from 1789330645.373902:
grant → CH base ×3 → head-mark → six `0500` RQ1 → the rest of the sweep, ending 1789330645.687940.

| | S-1608, 16 in | S-4000S, 32 in |
|---|---|---|
| console records | 56 | **104** |
| grant `0100` | `06 00 01 00` | `06 00 01 00` — identical |
| head-mark `0000` | `03 00 00 00` | `03 00 00 00` — identical |
| `0500` RQ1 ×6 | `00 00 04`, `06 00 08`, `10 00 11`, `10 11 09`, `11 00 11`, `11 11 09` | byte-identical |
| head-amp sweep | 48 records, CH `0x20`–`0x2f` | **96 records, CH `0x00`–`0x1f`** |
| ENROLL group map | none | one, `4 × 41` |
| box records | 7 (join sent three times, `01`/`01`/`09`) | 5 (join once, `06 00 01 00`) |
| box commit report | `82`, code `0x02`, cells `02 02 02 02 01 01 03×6` | `84`, code `0x00`, cells `02×8 01 01 03 03` |
| box `0500` `0x0016` | `00 00 02 02 00 00` | `00 00 02 05 00 00` |
| box `0500` `0x001a` | `06 00 00 00 00 02 00 03 00 02` | `06 00 00 00 00 02 00 01 00 02` |
| scene body | 8904 B | **byte-identical, 0 of 8904 differ** |

So the console side splits cleanly. **Width-independent, byte for byte:** the grant, the head
mark, the six identity requests, and the whole scene body — the body carries no trace of which
box is enrolled. **Width-dependent:** the head-amp sweep, whose base is the box's slot base
(`0x20` for an S-1608, `0x00` for an S-4000S) and whose length is 3 × the input width; and the
ENROLL group map, which is sent for 8 and 32 and not at all for 16.

The S-4000S session also reproduces the rest of §1 and §3 independently: `cfea` pace `0x02` on
all 46 announces, chanmap `fe` marker `0x02` on all 6 sweeps, two complete 8904-byte scene bodies
(t = 1789330638.783331 and 641.477842) that are byte-identical to each other, to the three from
the S-1608 session, and carry the same three ASCII runs and `revision = 0x0002`.

## 3. XVSCEN and SYSPARAM

The scene bulk rides the **32-byte control block**, not the 1440-byte audio region: one
`seg=FIRST` frame (`len 0x0018`) carrying a 2-byte total and 24 body bytes, 341 `seg=MIDDLE`
frames (`len 0x001a`) carrying 26 each, one `seg=LAST` (`len 0x000e`) carrying 14 —
24 + 341×26 + 14 = **8904** = the `0x22c8` the FIRST frame declares. A 512-byte snaplen therefore
loses nothing of a scene transfer.

Three complete bodies were reassembled (t = 542.135952, 544.831563, 547.525979), 343 frames each,
declared length = recovered length = 8904, and all three **byte-identical**.

The only ASCII runs of 4 or more printable bytes in all 8904 bytes:

| offset | bytes |
|---|---|
| `0x0000` | `1234` |
| `0x0368` | `SYSP` |
| `0x037c` | `SCEN` |

**There is no `XVSCEN`, no `SYSPARAM` and no `SCENE` anywhere in a console's body.** The tags are
four bytes each, and each is followed by `version` `u2le` = 1 and `key` `u2le` = 0; `SYSP`'s
`flag` at +8 is 0. This is the search `wire-format.md:203` asks for and on a console the answer
is negative, with three positives found by the same pass. **`XVSCEN` is not a tag but it is not
imaginary either — see §5**, where a box in master mode fills two bytes the console leaves zero
and the ASCII reader runs them into `SCEN`.

Structure as recovered:

- `0x000` `1234`, `unit_map_select` `0x0001`, `map_a_arg` `0x0004`, `revision` `0x0002`
- `0x01a` 80 scene records of 10 bytes: 32 read `02 00 00 00 01 00 00 00 00 00` (analog input)
  and 48 read `03 …` (absent)
- `0x340` the master's own MAC, `00:40:ab:c9:cc:03`, then two `ff ff ff ff ff ff` slots
- `0x368` `SYSP`, 20 bytes
- `0x37c` `SCEN`, then 800 records of 10, every one `03 00 00 00 01 00 00 00 00 00`, then 4 zero
  bytes to `0x22c8`

Across rates, same console: the 44.1 kHz body and the 48 kHz body differ in **one byte of 8904**
— offset `0x14`, `revision`, `02` against `00`. Nothing else, including the master MAC field and
both tag blocks. The body carries no box identity and nothing that varies with the box.

This also lifts the `n=1` caveat on `revision` at 44.1 kHz: three headers, all `0x0002`.

## 4. The `0x80` selector arm

**Not exercised under a console, anywhere in the corpus.** The S-1608 declares with opcode
`0x82`, once, at 1789327550.105055. Across the 108 console-bearing files / 5 295 229 REAC frames
there are **zero** link-1 `0x80` declarations; the same scan finds `0x82` in 36 files and `0x84`
in 17. The arm is the box firmware's second branch in `FUN_0c003c8a`, taken only when the peer is
a box rather than a desk — and that pairing is now captured. See §5.

## 5. Box to box, no console — the `0x80` arm on the wire

`box-to-box-2026-09-13`, VLAN 12, snaplen 512, reac-pw stopped so no frame of ours exists in
either file. S-1608 `00:40:ab:c4:80:3b` set to **M** and rebooted; S-4000S `00:40:ab:c4:06:80`
in S. Two enrolments of the same pair: `enrol-main-port-slice.pcap` (692 609 records, cable
bounced on the box's REAC **main** port) and `enrol-backup-port-slice.pcap` (631 303 records,
cable moved to the box's **backup** port).

### The declaration: selector `0x80`, and `0x83` is not the S-4000's second arm

The S-4000S declares, in both enrolments, byte for byte:

```
cd ea | 01 03 00 10 80 00 00 00 02 02 02 02 02 02 02 02 01 01 03 03 00 03 00 00 00 01 00 … 50
```

The **same physical box** declaring to the M-200 two hours earlier
(`m200-enrol-s4000-441k-2026-09-13`, t = 1789330642.170256) reads:

```
cd ea | 01 03 00 10 84 00 00 00 02 02 02 02 02 02 02 02 01 01 03 03 00 03 00 00 00 01 00 … 4c
```

**One byte moves, the selector — `0x84` to `0x80` — and the checksum follows it** (`0x4c` +
`0x04` = `0x50`, the exact compensation). `board_config_code` is `0x00` in both arms and the
twelve cells are identical, so this capture cannot speak to the zeroing the image describes.

Two corrections follow. `spec/reac.ksy` predicts the S-4000's second literal is **`0x83`**
(`DAT_0c013752`); measured, it is `0x80` — the same value as the S-1608's second arm, so the
second arm is one shared constant and not a per-model pair. And `libreac`'s
`reac_ctrl_build_config_announce_box_master` describes the desk→box-master delta as "the
selector, and one entry of the port-type table (five `02` become four, with a `00` ahead of
them)": the byte that moves there is `board_config_code`, not a cell, and for a model whose code
is already `0x00` nothing but the selector moves.

### The exchange, with no console on the segment

The S-1608 master announces `cfea … 10 08 01 00 01 00 …` once a second (median 1.008 s):
`slot_total` **`0x10`** (16, its own width, against a console's `0x28`), `box_in_width` `0x08`,
pace `0x01` (96 kHz), `box_count` `0x0001`. That announce is **byte-identical in every one of the
110 announces across both files** — it never changes to the 32-input box that enrolled, and
`box_count` never falls to 0 through a 42-second absence. A console does both within seconds.

No ENROLL group map is sent at all (op `0x10` count 0 in both files; control, op `0x01` sweeps
present in the same scan).

The grant is three records and they are the box's own, echoed back 1.9 ms later:

| t (main) | who | tag | payload |
|---|---|---|---|
| 1789331549.471677 | box | `0100` | `06 00 01 00` |
| 1789331549.471805 | box | `0000` | `03 00 00 00` |
| 1789331549.471929 | box | `0302` | `00 01 00` |
| 1789331549.473576 | **master** | `0100` | `06 00 01 00` |
| 1789331549.473680 | **master** | `0000` | `03 00 00 00` |
| 1789331549.473802 | **master** | `0302` | `00 01 00` |

That is the whole link-4 exchange. **No head-amp sweep and no identity requests**: a console
sends 56 (16-in box) or 104 (32-in box) records here; a box master sends three, and all three are
echoes. The echo is not quite literal — on the backup-port enrolment the box joins with
`06 00 **03** 00` and the master still answers `06 00 **01** 00`, so the join value is normalised
to `0x01` exactly as a console normalises it, while the head mark and the box-ready record are
returned byte for byte.

The master also emits one `0100` `06 00 01 00` record 33 ms (main) / 74 ms (backup) after the
box's last frame — it notices the loss at once, and then does nothing about it for the rest of
the gap.

### The box master's scene body

Two transfers per enrolment, and the **first one is short**: 337 frames, 24 + 335 × 26 + 14 =
**8748** bytes against a declared `0x22c8` = 8904. The second, 2.290 s later, is complete at 343
frames / 8904. Identical in both enrolments, and it is not capture loss — the frame counter is
contiguous across every frame of both transfers, and the only two counter gaps in each file fall
outside them.

The complete body is **byte-identical between the main-port and the backup-port enrolment** (0 of
8904 differ). Against the M-200's body at 44.1 kHz it differs in **76 bytes**:

| where | M-200 | S-1608 on M |
|---|---|---|
| +0x008 `map_a_arg` | `04 00` | `02 00` |
| +0x00b (`unknown_0a`) | `80` | `00` |
| +0x014 `revision` | `02` (44.1 k) | `01` (96 k) |
| +0x01a slots | 32 input cells | 16 input, 8 output, 56 absent |
| +0x33c | `00 00 00 00` | **`c0 a8 01 01`** = 192.168.1.1 |
| +0x340 `master_id` | its own MAC | its own MAC |
| +0x346 | `00 00 00 00` | **`c0 a8 01 02`** = 192.168.1.2 |
| +0x34a | zeros | the same MAC again |
| +0x360, +0x364 (`map_b`) | zero | `33 08`, `47 01` |
| +0x37a (`sysp.rest` tail) | `00 00` | **`59 56`** |

`revision` `0x0001` at 96 kHz, `cfea` pace `0x01` and the chanmap `fe` marker `0x01` agree on a
box master too — the rate-class reading holds on a device that is not a console at all.

The `c0 a8` pair is the "`0xc0 0xa8` (= 192.168) address prefix repeated twice" of
`wire-format.md`, now located: **+0x33c and +0x346, each a 4-byte IPv4 immediately followed by a
6-byte MAC**, with `master_id` at +0x340 being the first pair's MAC. A console leaves both
addresses and the second MAC slot zero. And `scene_body.map_b` (+0x35a), which the ksy calls
"all zero on every capture, so the SHAPE is INFERRED", is not all zero here.

### `XVSCEN` explained

`scene_sysp` is 20 bytes: `tag(4) SYSP`, `version`, `key`, `flag`, then 11 bytes the ksy calls
`rest`. Its **last two bytes, at +0x37a, read `59 56` on a box master** and `00 00` on every
console. `SCEN` begins at +0x37c. So an ASCII scan of a box-master body returns a six-character
run:

```
0378  00 00 59 56 53 43 45 4e  01 00 00 00        ..YVSCEN....
```

`YVSCEN`, not `XVSCEN` — `0x59` where the earlier notes record `0x58`. Either way **there is no
six-byte tag**: the run is two bytes of `sysp.rest` abutting the four-byte `SCEN` tag, and the
box's commit gates on `SCEN` at +0x37c, not on the run. The name in the old notes came from
reading a real byte sequence in a body like this one. `SYSPARAM` and `SCENE` remain absent
everywhere.

### The chanmap value byte is not always zero

The ksy records "over 183 872 chanmap records in 72 captures the value byte is `0x00` every
single time, and the flags byte takes only `0x28` and `0x38` on real slots". That is a fact about
consoles. The S-1608 in master mode writes, on its own op-`0x01` sweeps in the main-port file,
flags `0x18` (72), `0x28` (144), `0x30` (151), `0x38` (72) and **value `0x20` on 151 of 448
records**; the S-4000S echoes the same values back in its op-`0x81` replies. Control in the same
pass: the M-200 driving the same S-4000S writes only `0x28`/`0x38` and value `0x00`, 288 of 288.
The capability the two box images carry is exercised — by a box master, never by a desk.

### Main port versus backup port

**Nothing in either enrolment names the port.** The declaration, the scene body, the grant
exchange, the announce and the chanmap content are identical; the only differing byte in the whole
sequence is the box's join value, `06 00 01 00` on the main port and `06 00 03 00` on the backup,
which is the climbing join alphabet and not a port field.

### 42.620 s against 12.283 s

Measured from the frames:

| | main port | backup port |
|---|---|---|
| box silent | 42.620 s | 12.283 s |
| box's last frame → master's first scene transfer | **+39.979 s** | **+9.642 s** |
| master's first scene transfer → box's first frame | +2.641 s | +2.641 s |
| box's first frame → its `0x80` declaration | +0.683 s | +0.683 s |
| declaration → the box's link-4 burst | +1.124 s | +1.123 s |
| box's burst → the master's echo | +1.9 ms | +1.9 ms |

Everything from the master's first scene transfer onward is identical to the millisecond, twice.
**The entire difference sits before it**, in a stretch where the only traffic is the master's own
`cfea`, chanmap sweeps and filler — and that traffic does not change: `box_count` stays 1,
`box_in_width` stays `0x08`, the announce stays byte-identical. The one wire-visible precursor is
the master's chanmap cadence, which runs at 1.000 s and stretches to 2.000 s before the push, then
pauses for 6.376 s — the same 6.376 s in both files — with the scene transfer inside that pause.
The stretch begins at box-last **+30.9 s** on the main port and **+0.6 s** on the backup port.

So the box waits on the master for the fixed part, and the master's own start is what differs.
**What makes the master start is not on the wire.** A PHY link-up puts no REAC frame on the
segment, and the capture cannot see the cable. The settling measurement is the same session with
switch port-state transitions logged against the capture clock, or a per-cable inline tap.

## 6. A desk arriving on a live segment — arbitration Q4

`desk-arrival-q4-2026-09-14/desk-arrival-slice.pcap`, 270 594 records, VLAN 12, full frames,
44.1 kHz (`cfea` pace `0x02`, chanmap `fe` marker `0x02`). The M-200 `c9:cc:03` was unplugged and
replugged; the S-4000S-3208 `c4:08:bc` stayed linked to the switch throughout and **its cable was
never touched**. Our `.12` was a tap — no frame of ours in the file.

### What the box does when the desk vanishes

Desk's last frame 1789372381.641620. The box then:

- sends **one** link-4 record, `tag 0100` `06 00 01 00`, at 1789372381.729980 — **+88.4 ms**;
- sends nothing else: its op-`0x81` heartbeat stopped with the desk (last one 1789372381.271741)
  and no control frame leaves it for the rest of the gap;
- **keeps streaming**, 20 690 frames of full-width 1204-byte (32-channel) upstream audio, for
  **5.629 s**;
- then stops dead at 1789372387.270965 and is silent for 6.958 s.

So the master-loss timeout is 5.629 s of carrying audio into a void, one re-assert record at the
moment of loss, and then silence. It never bounces its own link and never cold-connects.

### What the returning desk sends, and what wakes the box

| t | who | frame |
|---|---|---|
| 1789372390.849028 | desk | first frame back — **filler** |
| 1789372390.869148 | desk | **`cfea` announce**, `box_in_width 0x08`, `box_count 0x0000`, pace `0x02` (+20.1 ms) |
| 1789372390.850151 – 391.526032 | desk | 338 scene MIDDLE chunks and a LAST — **with no FIRST**: the tail of a transfer it began while unplugged |
| 1789372393.537566 – 394.220840 | desk | **one complete scene transfer**: FIRST declaring `0x22c8`, 341 chunks, LAST |
| 1789372394.229195 | box | **first frame back**, +8.355 ms after that LAST |
| 1789372394.229741 | box | its **state-4 commit report** `cdea 01 03 0010 84 …`, +0.55 ms later |
| 1789372394.439302 | desk | the **ENROLL group map** `04 02 41 41 41 41 …`, +209.6 ms after the commit report |
| 1789372395.927676 | box | its `cdea 04 03` burst: join `06 00 03 00`, head mark, box-ready (+1.489 s) |
| 1789372397.433060 | desk | the **grant** `06 00 01 00`, then 103 more records (+1.505 s) |
| 1789372397.442494 | box | its two `0500` identity answers |

**A completed scene transfer is what captures an already-linked box, and the capture carries its
own negative control.** The desk's first push after returning is missing its FIRST frame and the
box does not answer it; the next push is complete and the box is transmitting 8.4 ms after its
last chunk, with the PHY never having bounced. That is arbitration Q4 answered in the
affirmative.

**The box's first frame is a commit report, not a cold connect.** Its `cdea 04 03` records come
1.698 s later, and only after the desk's ENROLL group map. A master that waits for a `04 03`
JOIN from a warm box waits for something the box will not send first.

**The ENROLL group map is what opens the box's upstream to full width.** Back on the wire the
S-4000S sends 774 frames of 340-byte (`52 + 8 × 36`, 8-channel) upstream, from 1789372394.229195
to 1789372394.439459 — and its first 1204-byte (32-channel) frame is at 1789372394.442304,
**3.0 ms after the group map** at 1789372394.439302. The group map has a measured function, not
only a shape.

### Against reac-pw's master

`libreac src/reac_master.c` enters PROBING on the first pacer slot and its comment states the
premise this capture refutes: *"a master that waits for 'presence' deadlocks against a box whose
PHY never bounced (§13b: the box only cold-connects on a real link-down/up)"*. **A box whose PHY
never bounced rejoined here in 3.380 s**, and it did not cold-connect — it commit-reported. The
`§13b` premise is false, so the honest surface in the arbitration spec's §3b ("bounce its link")
and the daemon's `rx_box_frames=0` advice are both describing a limitation of our push, not of
the box.

The FSM is not the gap: `EDGE[REAC_M_PROBING][REAC_M_EV_CONFIG_EARLY]` already takes the warm
relink, and `control_cadence`'s HUNT branch already emits HEAD → 341 chunks → TAIL at a
`probe_stride` of `fps/500` (7 slots at 44.1 kHz, against the desk's measured 7.36). What a
libreac lane now has is a reference to prove our push against, on the wire, with a box that is
linked and silent:

1. push while no box is known — announce `box_count=0`, `box_in_width=0x08`;
2. the push must **complete** — FIRST declaring `0x22c8`, 341 chunks, LAST. An interrupted push
   is measured here to produce nothing at all;
3. expect the answer as a **config announce** within ~10 ms of the LAST, not a `04 03` JOIN;
4. answer it with the **ENROLL group map within ~210 ms** — that is what widens the box's
   upstream and what precedes its JOIN by 1.489 s;
5. grant ~1.505 s after the JOIN burst.

The pass/fail for that lane is `rx_box_frames > 0` with no cable touched, and the first box frame
inside ~10 ms of a completed push.

## What this changes in the published description

0. `spec/reac.ksy` `enroll_page.console_field` — it is the **pace code**, reading `0x02` at
   44.1 kHz, not a console generation.
0b. `spec/reac.ksy` `commit_report_page.selector` — the S-4000's second arm is `0x80`, not the
   predicted `0x83`, and the second arm is one constant shared with the S-1608.
0c. `spec/reac.ksy` `chanmap_entry` — the value byte is not always `0x00` and the flags byte is
   not only `0x28`/`0x38`: a box master writes value `0x20` and flags `0x18`/`0x30`.
0d. `spec/reac.ksy` `scene_sysp.rest` — its last two bytes read `59 56` on a box master, which is
   where `XVSCEN` comes from; there is no six-byte tag. `scene_body.map_b` is not always zero.
0e. `wire-format.md` — the `0xc0 0xa8` pair is at +0x33c and +0x346 of the scene body, each an
   IPv4 followed by a MAC; and a box master grants by echoing the joining box's three records,
   normalising only the join value, with no head-amp sweep and no identity requests.
0f. `spec/reac.ksy` `enroll_page` — the group map has a measured function: the box's upstream
   goes from 8-channel to its declared 32 within 3.0 ms of receiving it.
0g. A desk captures an already-linked box with no PHY bounce, and the trigger is a COMPLETED
   scene transfer; the box answers with its commit report, not a cold connect. This answers
   `openmixer docs/design/specs/2026-08-20-reac-master-arbitration.md` §6 Q4.
1. `wire-format.md` — `XVSCEN` is refuted, by the reassembled-body search the paragraph itself
   names as the settling measurement.
2. `wire-format.md` — the `SCENE` / `SYSPARAM` question inside the bulk data is settled: the tags
   are `SYSP` at +0x368 and `SCEN` at +0x37c, four bytes each.
3. `wire-format.md` — "all 24 head-amp records" is the 8-input figure. The sweep is 3 × the box's
   input width: 24 for an S-0808, **48** for an S-1608.
4. `spec/reac.ksy` `chanmap_entry.is_identity_record` — its flags byte takes a third value,
   `0x02`, and is collinear with the `cfea` pace code on every real talker in the corpus.
5. `spec/reac.ksy` `scene_body.revision` — the `n=1` caveat at 44.1 kHz is lifted, and the
   whole-body diff against 48 kHz is one byte.
6. `spec/reac.ksy` `enroll_page.console_field` — the group map is sent for an 8- and a 32-input
   box and never for a 16-input one, which is why it took a second capture to measure.

`spec/protocol-facts.yaml` `CONSOLE_FIELD_GATES_RATE` still says "44.1 kHz has NO distinct value
on either field … 44.1 is a graph/RME rate, not a REAC-wire rate". Three carriers now read
`0x02` at 44.1 kHz. That entry carries an operator ruling and drives generated headers, so it is
left for a ruling rather than edited here.
