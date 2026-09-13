# M-200 at 44.1 kHz — an S-1608 enrolment, read out

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

### ENROLL[8] — not resolvable from this capture

**Zero** ENROLL group maps (`cdea`, link 1, opcode `0x10`) in the slice. Presence control in the
same pass: `group_map_scan enrol-bounce-slice.pcap matrix-m200-s0808.pcap` reports
`group_maps=2`, both from this same console MAC, `console=0x00`, at t=1783783848.749 — **209 ms
after** that box's commit report. Here the 30 s after the commit report are fully captured, so
the window is covered and the absence is real.

**Why there is none: the box, not the rate.** Across 108 files the corpus holds 107 group maps,
and every one is addressed to an 8-input or a 32-input declarer:

- `04 00 41 00 00 00 00 00 c3 c3 c3 c3` — 8-wide, console byte `0x00`
- `04 00 41 41 41 41 00 00 00 00 00 c3` — 32-wide, console byte `0x00`
- the same two with console byte `0x01` from the M-5000

Twenty-two files carry an S-1608 as the only box — five of them full enrolments
(`real-m200-s1608-coldboot`, `m200-s1608-BIDIR-coldboot`, `m200-s1608-COLDCONNECT-clean`,
`m200-s1608-establish-today`, and this one) — and **not one carries a group map**. No console
in the corpus has ever sent an ENROLL group map to a 16-input box. The 16-wide row remains a
prediction of the width rule with no wire behind it, and may describe a frame that is never sent.

Settling capture: **an M-200 at 44.1 kHz enrolling an S-0808 or an S-4000S.** A 44.1 kHz session
with an S-1608 will not produce one however long it runs.

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

**There is no `XVSCEN`, no `SYSPARAM` and no `SCENE` anywhere in the body.** The tags are four
bytes each, and each is followed by `version` `u2le` = 1 and `key` `u2le` = 0; `SYSP`'s `flag` at
+8 is 0. This is the search `wire-format.md:203` asks for and the answer is negative, with three
positives found by the same pass.

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

**Not exercised here, and not anywhere in the corpus.** The S-1608 declares with opcode `0x82`,
once, at 1789327550.105055. Across 108 files / 5 295 229 REAC frames there are **zero** link-1
`0x80` declarations; the same scan finds `0x82` in 36 files and `0x84` in 17.

The arm is the box firmware's second branch in `FUN_0c003c8a`, and the only declaration of it on
record is `libreac`'s `reac_ctrl_build_config_announce_box_master`, whose two golden blocks came
from `box-to-box-enroll.pcap` (2026-09-09) — a file that no longer exists on this machine.

The topology that exercises it: **a box enrolling to another box in M mode, no console on the
segment** — an S-0808 in M with an S-1608 in S, or the reverse, on one VLAN. It is the declaration
a box sends *to a box master*, not to a desk, and it differs from the desk form in two fields:
selector `0x82` → `0x80`, and the port table gains a leading `0x00` (`02 02 02 02 02 01 01 …`
becomes `00 02 02 02 02 01 01 …`). A console anywhere on the segment takes the first arm and the
capture is wasted. The box-to-box session attempted on 2026-09-13
(`box-to-box-2026-09-13/timeline.txt`) was dropped before any box was put in M mode.

## What this changes in the published description

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
6. `spec/reac.ksy` `enroll_page.console_field` — still unmeasured at 44.1 kHz, and the reason is
   now known: no console sends a group map to a 16-input box.

`spec/protocol-facts.yaml` `CONSOLE_FIELD_GATES_RATE` still says "44.1 kHz has NO distinct value
on either field … 44.1 is a graph/RME rate, not a REAC-wire rate". Three carriers now read
`0x02` at 44.1 kHz. That entry carries an operator ruling and drives generated headers, so it is
left for a ruling rather than edited here.
