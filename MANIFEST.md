# MANIFEST — the REAC capture corpus

Generated 2026-08-23 by lane CAP; distilled 2026-08-23 by lane DIST. One row per capture: device
pair, event, date, truncation, size raw and distilled, and what it is evidence FOR. A capture
nobody can identify is nearly worthless; this file is what stops that.

**The captures in this repository are DISTILLED.** Same 85 names, same relative paths, 271.3 MB
instead of 47.9 GB. Every control frame that is not a `grant` is still here — all 852,274 of
them; the audio is sampled, and so are the grants. The rule and its proof are at the foot of this file. The raw 47.9 GB set lives outside
git at `~/Devel/audio/reac-captures-raw/` with its own README and a full `SHA256SUMS.txt`.

## How to read a row

- **Pair** — `<console> x <box>` as MEASURED from the MACs in the file, not as labelled by hand.
  `none` = no box on the segment; `reacpw` = our own stack was the master; `unk` = the desk could
  not be identified from the capture (too short to carry an announce).
- **Tap** — `mirror` means the capture was taken through a port mirroring both directions, so
  EVERY frame appears twice. 61 of the corpus is mirrored. A rate read as packets-per-second off
  a mirrored capture is 2x wrong; measure it from the counter advance at `frame[14:16]`.
- **Trunc** — `TRUNCATED snaplen=N` describes the RAW capture: every record kept only the first N
  bytes as it came off the wire. It still carries headers, control block and timing, but NOT whole
  frames. Never do structural or frame-length work on one: a truncated 1492-byte frame can pass
  `canonical_len()` as a legal 18-channel frame.

  After distillation this column no longer tells you what a record in THIS repo looks like. Most
  control frames here are cut to 50 bytes whatever their raw row says, and the sampled audio runs
  are whole whatever it says. Every record still carries its true wire length in `origlen`, so ask
  the file, not this column. The column is kept because it is a fact about the capture session —
  a snaplen-128 session never recorded audio and no distillation can put it back.
- **Size raw → distilled** — bytes in `~/Devel/audio/reac-captures-raw/`, then bytes in this repo.
- **State** — `committed(LFS)` was already in git via git-lfs before the distillation;
  `ON DISK, uncommitted` was not. Both are committed now, distilled. The label is kept because it
  says which objects the unpushable raw history still carries — see The 2 GB question.

## Corpus totals

| | files | raw | distilled |
|---|---:|---:|---:|
| `captures/` | 47 | 20.4 GB | 124.9 MB |
| `m200-headamp-re/` | 19 | 6.9 GB | 88.6 MB |
| `m200-s1608-headamp/` | 16 | 20.3 GB | 57.2 MB |
| `m200-scene-recall-re/` | 1 | 190.1 MB | 369.6 KB |
| `s1608-bank-2026-08-22/` | 2 | 125.0 MB | 278.0 KB |
| **total** | **85** | **47,907,786,044 (47.9 GB)** | **271,331,352 (271.3 MB)** |

**176.6x smaller.** Not one control frame was dropped except `grant`, which is sampled the same
way audio is. What each number does across the distillation:

| | raw | distilled | |
|---|---:|---:|---|
| control frames | 6,910,123 | 922,420 | every one kept except `grant` |
| scene_transfer | 778,751 | **778,751** | identical |
| config_announce | 305 | **305** | identical |
| group_map | 107 | **107** | identical |
| record_fragment | 40 | **40** | identical |
| grant | 6,057,849 | 70,146 | sampled — this is the 395 MB |
| head-amp records | 10,101 | **10,101** | identical |
| filler frames | 38,417,760 | 174,743 | sampled — this is the 47 GB |
| pcap records | 45,327,906 | 1,097,186 | |
| audio frames decoded | 36,732,190 | 185,590 | sampled, contiguous |

Truncated in every record: **14 of 85**. Independently confirmed two ways — a direct
caplen<origlen scan, and the `trunc=` column of libreac's `tests/corpus-baseline.txt`, which
agree on the same 12 files of the 83 that predate this manifest.

## `captures/` — 47 captures, 20.4 GB raw → 124.9 MB distilled

| capture | pair | rate/tap | date | size raw → distilled | trunc | state | evidence for |
|---|---|---|---|---:|---|---|---|
| `deskc9919c-s1608-unk-clean__zoneA-48k.pcap` | deskc9919c x s1608 | unk/clean | 2026-06-03 | 68.2 MB → **2.2 MB** | full | committed(LFS) | libreac tests/ctrl_fixtures.inc; README calls it the canonical mixed-stream test (40-ch down + 16-ch up) |
| `deskc9919d-s0808-unk-clean__zoneB-48k.pcap` | deskc9919d x s0808 | unk/clean | 2026-06-03 | 44.2 MB → **1.9 MB** | full | committed(LFS) | the 8-ch stagebox return (340 B upstream); openmixer audio-kb-index |
| `deskca154d-s0808-unk-clean__reac-jitter-sample.pcap` | deskca154d x s0808 | unk/clean | 2026-06-04 | 2.4 MB → **132 KB** | **TRUNCATED snaplen=64** | committed(LFS) | re-pacer jitter/timing tests; OFF-C3-repacer-egress-model.py input; C1-tbf + C3/C4 designs |
| `deskca154d-s1608-unk-mirror__wired-reac-a-bothdirs-2026-06-09.pcap` | deskca154d x s1608 | unk/mirror | 2026-06-08 | 174.4 MB → **2.2 MB** | full | committed(LFS) | recipe-(f) reference, both directions |
| `deskca154d-s1608-unk-mirror__wired-reac-loud-bothdirs-2026-06-09.pcap` | deskca154d x s1608 | unk/mirror | 2026-06-08 | 174.6 MB → **2.2 MB** | full | committed(LFS) | as above at loud signal level |
| `m200i-none-48k-clean__m200-probing-nobox-2026-07-11.pcap` | m200i x none | 48k/clean | 2026-07-10 | 18.0 MB → **1.5 MB** | full | ON DISK, uncommitted | libreac tests/ctrl_fixtures.inc |
| `m200i-none-48k-clean__m200-s1608-boxB-synced-2026-07-11.pcap` | m200i x none | 48k/clean | 2026-07-10 | 30.0 MB → **1.5 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-none-48k-clean__m200-s1608-realbox-establish-2026-07-11.pcap` | m200i x none | 48k/clean | 2026-07-10 | 690.2 MB → **1.0 MB** | **TRUNCATED snaplen=700** | ON DISK, uncommitted | libreac reac_ctrlblk.c + ctrl_fixtures.inc; reac-pw src/reac_fsm.h |
| `m200i-none-48k-clean__m200-s1608-realbox-unicast-2026-07-11.pcap` | m200i x none | 48k/clean | 2026-07-10 | 687.3 MB → **98 KB** | **TRUNCATED snaplen=700** | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-none-48k-clean__s0808-synced-2026-07-11.pcap` | m200i x none | 48k/clean | 2026-07-10 | 30.0 MB → **1.5 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__m200-BIDIR-coldboot-2026-07-11.pcap` | m200i x s0808 | 48k/mirror | 2026-07-11 | 2.0 GB → **3.9 MB** | full | ON DISK, uncommitted | openmixer docs/reference/audio-kb-index.md |
| `m200i-s0808-48k-mirror__m200-s0808-establish-switch-2026-07-11.pcap` | m200i x s0808 | 48k/mirror | 2026-07-11 | 2.5 MB → **2.5 MB** | full | ON DISK, uncommitted | libreac tests/ctrl_fixtures.inc |
| `m200i-s0808-48k-mirror__m200-s1608-BIDIR-establish-2026-07-11.pcap` | m200i x s0808 | 48k/mirror | 2026-07-11 | 1.1 GB → **3.8 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__matrix-m200-s0808-2026-07-11.pcap` | m200i x s0808 | 48k/mirror | 2026-07-11 | 4.8 MB → **3.1 MB** | full | ON DISK, uncommitted | reac-pw tests/test_reac_master.c, src/reac_master.c/.h |
| `m200i-s1608-48k-clean__reacpw-s1608-cfeatiming-2026-07-18.pcap` | m200i x s1608 | 48k/clean | 2026-07-18 | 1.2 MB → **1.2 MB** | full | ON DISK, uncommitted | libreac tests/ctrl_fixtures.inc; reac-firmware-re HEADAMP-MASTER-STATE / GRANT-SWEEP |
| `m200i-s1608-48k-clean__reacpw-s1608-establish-2026-07-18.pcap` | m200i x s1608 | 48k/clean | 2026-07-18 | 1.2 MB → **1.2 MB** | full | ON DISK, uncommitted | reac-firmware-re HEADAMP-MASTER-STATE-2026-07-17 / GRANT-SWEEP / FACTS-SETTLED-2026-08-23 |
| `m200i-s1608-48k-clean__reacpw-s1608-establish-acksweep-2026-07-18.pcap` | m200i x s1608 | 48k/clean | 2026-07-18 | 1.2 MB → **1.2 MB** | full | ON DISK, uncommitted | reac-firmware-re HEADAMP-MASTER-STATE / GRANT-SWEEP / FACTS-SETTLED-2026-08-23 |
| `m200i-s1608-48k-clean__reacpw-slave-m200-CONNECTED-2026-07-11.pcap` | m200i x s1608 | 48k/clean | 2026-07-11 | 51.5 MB → **2.2 MB** | full | ON DISK, uncommitted | reac-pw docs MASTER-HARDWARE-VERIFY / REAC-BOX-STATE-DIAGRAM / SLAVE-EMULATION-SCOPE |
| `m200i-s1608-48k-mirror__m200-s1608-BIDIR-coldboot-2026-07-11.pcap` | m200i x s1608 | 48k/mirror | 2026-07-11 | 431.4 MB → **3.7 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s1608-48k-mirror__m200-s1608-BIDIR-reboot-2026-07-11.pcap` | m200i x s1608 | 48k/mirror | 2026-07-11 | 976.4 MB → **4.4 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s1608-48k-mirror__m200-s1608-establish-switch-2026-07-11.pcap` | m200i x s1608 | 48k/mirror | 2026-07-11 | 188.6 MB → **4.4 MB** | full | ON DISK, uncommitted | openmixer tools/reac-firmware-emu/{controls,headamp,pathdiff}.py script input |
| `m200i-s1608-48k-mirror__m200-s1608-handshake-ctrl-2026-07-11.pcap` | m200i x s1608 | 48k/mirror | 2026-07-11 | 1.8 MB → **1.8 MB** | full | ON DISK, uncommitted | reac-firmware-re HEADAMP-MASTER-STATE / GRANT-SWEEP / FACTS-SETTLED-2026-08-23 |
| `m200i-s1608-48k-mirror__matrix-m200-s1608-2026-07-11.pcap` | m200i x s1608 | 48k/mirror | 2026-07-11 | 4.9 MB → **3.2 MB** | full | ON DISK, uncommitted | reac-pw tests/reac_grant_golden.inc (cited by OLD name), src/reac_master.c/.h |
| `m200i-s1608-48k-mirror__real-m200-s1608-coldboot-2026-07-11.pcap` | m200i x s1608 | 48k/mirror | 2026-07-11 | 1.7 GB → **4.5 MB** | full | ON DISK, uncommitted | reac-pw data/PROVENANCE.md, src/reac_scene_body.c, tools/gen-scene-body.py |
| `m200i-s4000s-48k-mirror__matrix-m200-s4000-2026-07-24.pcap` | m200i x s4000s | 48k/mirror | 2026-07-24 | 651.2 MB → **5.9 MB** | full | ON DISK, uncommitted | libreac + reac-pw tests/upstream_fixtures.inc |
| `m200i-s4000s-48k-mirror__matrix-m200-s4000-coldconnect-2026-07-24.pcap` | m200i x s4000s | 48k/mirror | 2026-07-24 | 99.2 MB → **5.8 MB** | full | committed(LFS) | reac-pw tests/reac_s4000_golden.inc |
| `m200i-s4000s-48k-mirror__s4000s-coldboot-m5000-2026-07-12.pcap` | m200i x s4000s | 48k/mirror | 2026-07-11 | 991.0 MB → **4.8 MB** | full | ON DISK, uncommitted | reac-pw tests/test_reac_tx.c; openmixer audio-kb-index |
| `m300-none-48k-clean__m200-s1608-establish-2026-07-10.pcap` | m300 x none | 48k/clean | 2026-07-10 | 863.0 MB → **791 KB** | **TRUNCATED snaplen=700** | committed(LFS) | reac-firmware-re REAC-PROTOCOL-AND-TESTS.md + REAC-CONNECTION-FSM.md |
| `m300-none-48k-clean__m300-coldboot-mirror-2026-07-10.pcap` | m300 x none | 48k/clean | 2026-07-10 | 859.8 MB → **776 KB** | **TRUNCATED snaplen=700** | committed(LFS) | reac-firmware-re REAC-PROTOCOL-AND-TESTS.md + REAC-CONNECTION-FSM.md; openmixer audio-kb-index |
| `m300-none-48k-clean__m300-s1608-coldboot-mirror-2026-07-10.pcap` | m300 x none | 48k/clean | 2026-07-10 | 861.2 MB → **821 KB** | **TRUNCATED snaplen=700** | committed(LFS) | reac-firmware-re REAC-PROTOCOL-AND-TESTS.md + REAC-CONNECTION-FSM.md |
| `m300-none-48k-clean__m300-s1608-coldconnect-mirror-2026-07-10.pcap` | m300 x none | 48k/clean | 2026-07-10 | 861.5 MB → **843 KB** | **TRUNCATED snaplen=700** | committed(LFS) | reac-firmware-re REAC-PROTOCOL-AND-TESTS.md + REAC-CONNECTION-FSM.md |
| `m300-none-48k-clean__m300-s1608-establish-2026-07-10.pcap` | m300 x none | 48k/clean | 2026-07-10 | 82.5 MB → **295 KB** | **TRUNCATED snaplen=700** | committed(LFS) | reac-firmware-re REAC-PROTOCOL-AND-TESTS.md + REAC-CONNECTION-FSM.md |
| `m300-s0808-48k-mirror__matrix-m300-s0808-2026-07-11.pcap` | m300 x s0808 | 48k/mirror | 2026-07-11 | 5.0 MB → **3.1 MB** | full | ON DISK, uncommitted | reac-firmware-re MIXER-VS-BOX-MATRIX.md |
| `m300-s1608-48k-mirror__matrix-m300-s1608-2026-07-11.pcap` | m300 x s1608 | 48k/mirror | 2026-07-11 | 3.5 MB → **3.1 MB** | full | ON DISK, uncommitted | reac-firmware-re MIXER-VS-BOX-MATRIX.md |
| `m5000-none-96k-mirror__matrix-m5000-s4000-unit2-coldconnect-2026-07-11.pcap` | m5000 x none | 96k/mirror | 2026-07-11 | 105.1 MB → **7.5 MB** | full | ON DISK, uncommitted | reac-firmware-re MIXER-VS-BOX-MATRIX.md; openmixer audio-kb-index |
| `m5000-s0808-96k-mirror__matrix-m5000-s0808-2026-07-11.pcap` | m5000 x s0808 | 96k/mirror | 2026-07-11 | 4.8 MB → **3.1 MB** | full | ON DISK, uncommitted | reac-firmware-re MIXER-VS-BOX-MATRIX.md |
| `m5000-s1608-96k-mirror__matrix-m5000-s1608-2026-07-11.pcap` | m5000 x s1608 | 96k/mirror | 2026-07-11 | 8.4 MB → **3.3 MB** | full | ON DISK, uncommitted | reac-firmware-re MIXER-VS-BOX-MATRIX.md |
| `m5000-s1608-96k-mirror__reacpw-slave-m5000-postfix-2026-07-11.pcap` | m5000 x s1608 | 96k/mirror | 2026-07-11 | 624.9 MB → **5.2 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m5000-s1608-96k-mirror__real-m200-s1608-alltraffic-2026-07-11.pcap` | m5000 x s1608 | 96k/mirror | 2026-07-11 | 222 KB → **222 KB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m5000-s1608-96k-mirror__real-s1608-alltraffic-m5000-2026-07-11.pcap` | m5000 x s1608 | 96k/mirror | 2026-07-11 | 18.2 MB → **3.7 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m5000-s1608-96k-mirror__real-s1608-coldboot-m5000-2026-07-11.pcap` | m5000 x s1608 | 96k/mirror | 2026-07-11 | 1.3 GB → **4.7 MB** | full | ON DISK, uncommitted | reac-pw docs MASTER-HARDWARE-VERIFY / REAC-BOX-STATE-DIAGRAM / SLAVE-EMULATION-SCOPE |
| `m5000-s4000s-96k-mirror__matrix-m5000-s4000-unit1-coldconnect-2026-07-11.pcap` | m5000 x s4000s | 96k/mirror | 2026-07-11 | 52.3 MB → **5.3 MB** | full | ON DISK, uncommitted | reac-pw tests/reac_s4000_golden.inc |
| `reacpw-none-96k-clean__s1608-master-bounce-2026-07-06.pcap` | reacpw x none | 96k/clean | 2026-07-06 | 1.5 GB → **1.6 MB** | full | ON DISK, uncommitted | libreac tests/ctrl_fixtures.inc |
| `reacpw-none-96k-clean__s1608-master-first-link-2026-07-06.pcap` | reacpw x none | 96k/clean | 2026-07-06 | 2.1 GB → **1.6 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `reacpw-s0808-48k-mirror__s0808-reboot-enrollfix-2026-07-12.pcap` | reacpw x s0808 | 48k/mirror | 2026-07-12 | 958.2 MB → **5.2 MB** | full | ON DISK, uncommitted | openmixer docs/reference/audio-kb-index.md |
| `unk-none-unk-clean__real_reac_stream.pcap` | unk x none | unk/clean | ? | 6 KB → **6 KB** | full | committed(LFS) | SOURCE OF THE PUBLIC CI FIXTURE. reac-aes67 + reac-tools test suites; reac-tools/tests/fixtures/. README:21 |
| `unk-s1608-unk-clean__reacpw-slave-m5000-established-2026-07-11.pcap` | unk x s1608 | unk/clean | 2026-07-11 | 16.6 MB → **2.2 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |

## `m200-headamp-re/` — 19 captures, 6.9 GB raw → 483.7 MB distilled

| capture | pair | rate/tap | date | size raw → distilled | trunc | state | evidence for |
|---|---|---|---|---:|---|---|---|
| `m200-s1608-headamp-48v-pad-sens-2026-07-17.pcap` | ? x ? | ?/? | 2026-07-17 | 57.6 KB → **26.4 KB** | **TRUNCATED snaplen=128** | committed(LFS) | m200-headamp-re/HEADAMP-GROUND-TRUTH-2026-07-17.md |
| `m200i-s0808-48k-mirror__ctl-session1-precut.pcap` | m200i x s0808 | 48k/mirror | 2026-07-16 | 5.5 MB → **3.3 MB** | full | committed(LFS) | session 1 control-plane extract (pre power-cut); 00-timeline.md, DECODE.md |
| `m200i-s0808-48k-mirror__ctl2.pcap` | m200i x s0808 | 48k/mirror | 2026-07-16 | 4.8 GB → **46.8 MB** | full | committed(LFS) | THE HEAD-AMP RE MASTER CAPTURE. 12 citers: libreac reac_ctrlblk.c, reac-pw reac_grant.c + test_reac_headamp.c, PLACEMENT-EVIDENCE.md, 4 openmixer design docs. Session 2 of the 2026-07-16 head-amp night |
| `m200i-s0808-48k-mirror__enrol-01-control.pcap` | m200i x s0808 | 48k/mirror | 2026-07-16 | 96 KB → **96 KB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__enrol-02-control.pcap` | m200i x s0808 | 48k/mirror | 2026-07-16 | 96 KB → **96 KB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__enrol-03-control.pcap` | m200i x s0808 | 48k/mirror | 2026-07-16 | 93 KB → **93 KB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__enrol-04-control.pcap` | m200i x s0808 | 48k/mirror | 2026-07-16 | 93 KB → **93 KB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__m200-%Y%m%d-%H%M%S.pcap01` | m200i x s0808 | 48k/mirror | 2026-07-16 | 200.0 MB → **3.4 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__m200-%Y%m%d-%H%M%S.pcap02` | m200i x s0808 | 48k/mirror | 2026-07-16 | 200.0 MB → **3.7 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__m200-%Y%m%d-%H%M%S.pcap03` | m200i x s0808 | 48k/mirror | 2026-07-16 | 200.0 MB → **3.4 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__m200-%Y%m%d-%H%M%S.pcap04` | m200i x s0808 | 48k/mirror | 2026-07-16 | 200.0 MB → **3.4 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__m200-%Y%m%d-%H%M%S.pcap05` | m200i x s0808 | 48k/mirror | 2026-07-16 | 200.0 MB → **3.7 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__m200-%Y%m%d-%H%M%S.pcap06` | m200i x s0808 | 48k/mirror | 2026-07-16 | 200.0 MB → **3.7 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__m200-%Y%m%d-%H%M%S.pcap07` | m200i x s0808 | 48k/mirror | 2026-07-16 | 200.0 MB → **1.9 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__m200-%Y%m%d-%H%M%S.pcap08` | m200i x s0808 | 48k/mirror | 2026-07-16 | 200.0 MB → **3.7 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__m200-%Y%m%d-%H%M%S.pcap09` | m200i x s0808 | 48k/mirror | 2026-07-16 | 200.0 MB → **3.7 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s0808-48k-mirror__m200-%Y%m%d-%H%M%S.pcap10` | m200i x s0808 | 48k/mirror | 2026-07-16 | 111.8 MB → **1.9 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m5000-s0808-96k-mirror__enrol-00-control.pcap` | m5000 x s0808 | 96k/mirror | 2026-07-16 | 1.7 MB → **1.7 MB** | full | committed(LFS) | enrolment control transcript; DECODE.md |
| `m5000-s0808-96k-mirror__m200-%Y%m%d-%H%M%S.pcap00` | m5000 x s0808 | 96k/mirror | 2026-07-16 | 200.0 MB → **3.8 MB** | full | ON DISK, uncommitted | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |

## `m200-s1608-headamp/` — 16 captures, 20.3 GB raw → 57.2 MB distilled

| capture | pair | rate/tap | date | size raw → distilled | trunc | state | evidence for |
|---|---|---|---|---:|---|---|---|
| `m200i-s1608-48k-mirror__m200-anchor-openwindow-20260721-221150.pcap` | m200i x s1608 | 48k/mirror | 2026-07-21 | 1.1 GB → **3.7 MB** | full | committed(LFS) | m200-s1608-headamp/WIRE-EXONERATED-2026-08-21.md |
| `m200i-s1608-48k-mirror__m200-ch16-anchor-toggle-20260721-220347.pcap` | m200i x s1608 | 48k/mirror | 2026-07-21 | 351.3 MB → **3.7 MB** | full | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s1608-48k-mirror__m200-ch16-anchor-v2-20260721-220654.pcap` | m200i x s1608 | 48k/mirror | 2026-07-21 | 585.8 MB → **3.7 MB** | full | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s1608-48k-mirror__m200-ch7-ON-OFF-ON-20260721-215743.pcap` | m200i x s1608 | 48k/mirror | 2026-07-21 | 527.3 MB → **3.7 MB** | full | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s1608-48k-mirror__m200-headamp-1357_16-toggle3-20260721-214420.pcap` | m200i x s1608 | 48k/mirror | 2026-07-21 | 366.0 MB → **3.7 MB** | full | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s1608-48k-mirror__m200-pad-sweep-20260721-222651.pcap` | m200i x s1608 | 48k/mirror | 2026-07-21 | 2.6 GB → **3.7 MB** | full | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s1608-48k-mirror__m200-pad-v2-20260721-223131.pcap` | m200i x s1608 | 48k/mirror | 2026-07-21 | 3.5 GB → **3.8 MB** | full | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s1608-48k-mirror__m200-s1608-COLDCONNECT-clean-2026-07-24.pcap` | m200i x s1608 | 48k/mirror | 2026-07-24 | 305.3 MB → **3.7 MB** | full | committed(LFS) | m200-s1608-headamp/UPPER-BANK-2026-08-21.md |
| `m200i-s1608-48k-mirror__m200-s1608-establish-today-20260721-235750.pcap` | m200i x s1608 | 48k/mirror | 2026-07-21 | 847.0 MB → **4.4 MB** | full | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s1608-48k-mirror__reacpw-cc03-headamp-20260721-231501.pcap` | m200i x s1608 | 48k/mirror | 2026-07-21 | 116.5 MB → **3.7 MB** | full | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s1608-48k-mirror__reacpw-establish-20260721-234355.pcap` | m200i x s1608 | 48k/mirror | 2026-07-21 | 232.9 MB → **4.4 MB** | full | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s1608-48k-mirror__reacpw-estcommit-233158.pcap` | m200i x s1608 | 48k/mirror | 2026-07-21 | 14.4 MB → **315 KB** | **TRUNCATED snaplen=200** | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s1608-48k-mirror__reacpw-in1-phantom-20260721-224512.pcap` | m200i x s1608 | 48k/mirror | 2026-07-21 | 263.5 MB → **4.3 MB** | full | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `m200i-s1608-48k-mirror__reacpw-reconnect-20260722-000735.pcap` | m200i x s1608 | 48k/mirror | 2026-07-21 | 9.1 GB → **5.9 MB** | full | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `reacpw-s1608-48k-mirror__reacpw-headamp-fulllen-20260721-230628.pcap` | reacpw x s1608 | 48k/mirror | 2026-07-21 | 219.1 MB → **4.3 MB** | full | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |
| `reacpw-s1608-48k-mirror__reacpw-headamp-preset-20260721-225954.pcap` | reacpw x s1608 | 48k/mirror | 2026-07-21 | 74.8 MB → **272 KB** | **TRUNCATED snaplen=400** | committed(LFS) | corpus membership only — held by the per-file baselines in libreac `tests/corpus-baseline.txt` and reac-protocol `spec/corpus-baseline.json` |

## `m200-scene-recall-re/` — 1 captures, 190.1 MB raw → 370 KB distilled

| capture | pair | rate/tap | date | size raw → distilled | trunc | state | evidence for |
|---|---|---|---|---:|---|---|---|
| `m200i-s1608-48k-mirror__m200-scene-recall-2026-07-17.pcap` | m200i x s1608 | 48k/mirror | 2026-07-17 | 190.1 MB → **370 KB** | **TRUNCATED snaplen=160** | committed(LFS) | m200-scene-recall-re/SCENE-RECALL-GROUND-TRUTH-2026-07-17.md + decode_scene.py |

## `s1608-bank-2026-08-22/` — 2 captures, 125.0 MB raw → 278 KB distilled

| capture | pair | rate/tap | date | size raw → distilled | trunc | state | evidence for |
|---|---|---|---|---:|---|---|---|
| `reacpw-s1608-48k-clean__nightR-wire-2026-08-22.pcap` | reacpw x s1608 | 48k/clean | 2026-08-22 | 17.4 MB → **134 KB** | **TRUNCATED snaplen=256** | ON DISK, uncommitted | THE EMITTER EXONERATION. openmixer rig night 2026-08-22: commanding SENS on console ch24 put phantom=1/pad=0/SENS=44 on the wire for CH 0x2f, ch16 -> CH 0x27, both checksum-clean. Refutes "the console writes phantom false". Cited as wire.pcap by FINDING-headamp-base-off-by-8.md |
| `reacpw-s1608-48k-clean__nightR-wire-act-2026-08-22.pcap` | reacpw x s1608 | 48k/clean | 2026-08-22 | 107.6 MB → **144 KB** | **TRUNCATED snaplen=256** | ON DISK, uncommitted | Actuation window for the same night (the head-amp slot map 0x20..0x27 actuate / 0x28..0x2f do not). Cited as wire-act.pcap by FINDING-headamp-base-off-by-8.md |

## The distillation — what was done, and what proves it

Done 2026-08-23 by the lane that owns the corpus gates, because distilling moves their baselines
and the move has to be proved rather than asserted. Tool: `analysis/distil.c`, which links
**libreac's own classifier** so the classification preserved here is the same one the gate
measures, not a second spelling of it.

### The rule

1. **Every frame that is not FILLER and not a `grant` is kept — all 852,274 of them.** No
   sampling, no dedup, no exceptions. Each is cut to its first **50 bytes**: ethernet[0:14], counter[14:16], type[16:18],
   control block[18:50]. Fifty is `REAC_CTRL_BLOCK_END`, the offset where audio begins, so those
   bytes are the whole of what any control reader ever looks at — `reac_ctrl_parse`, the block
   checksum, the head-amp record, the declared port table and the box identity all read inside
   [0:50] and every one returns the same answer over the cut frame as over the whole one.

   The pcap record keeps its **original `origlen`**, so the frame still states its length on the
   wire. That is what makes this a snaplen and not a forgery, and both gates have always treated
   such a record as a control block with no audio: the corpus already contained captures taken at
   snaplen 64/128/200/400 and they were first-class in it.

2. **Grants are sampled, per control-opcode key.** One capture, `ctl2.pcap`, was 6.6M control
   records of which 6,054,293 were `grant` — a single record repeating through 241 join cycles —
   and at 50 bytes each those were 400 MB of the corpus on their own. They are sampled exactly as
   audio is: 128 contiguous runs of 500, spaced evenly through the file. *Contiguous* because a
   grant defect is a relationship between adjacent grants — how long a burst runs, whether the
   counter stays contiguous across it, where in the join cycle it stops — and scattered singles
   cannot show one. *Spaced* because the grants of one join cycle say nothing about the next.

   The sampling bucket is the control triple `L<op0>.<op1>.<sel>`, **the same key the corpus gate
   reports**, so a rare grant subtype is never sampled away: a bucket that fits inside the budget
   is kept entire. In `ctl2` that separates 6,053,140 `L4.3.02` grants, which are sampled to
   65,437, from 1,153 `L4.3.00` grants, which are kept in full. Bucketing on anything coarser
   would have spent the whole budget on the common record and thrown the rare one away — and the
   rare subtype is where a defect is most likely to hide.

   A grant that falls inside a sampled **audio** run is kept whole and exempt from grant sampling:
   those frames are what `dn=`/`up=` decode, and thinning them here would move the audio tallies
   from the control arm, which is exactly the confusion the two self-tests exist to keep apart.

3. **Audio is sampled**: 4 contiguous runs of 250 whole frames, per distinct wire geometry, spaced
   evenly through each file. Per *geometry* because a REAC file interleaves streams of different
   widths (40ch downstream 1492 B, 16ch upstream 628 B, 8ch 340 B, 32ch 1204 B) and a run must be
   contiguous *within* the stream it samples. *Spaced* because the head of a capture is the
   establish handshake and the audio worth decoding is the steady state after it. *Contiguous*
   because braid and lane defects are a relationship between adjacent frames; scattered singles
   cannot show one.

4. **Non-REAC records are kept whole** — there are 23 and they are cheaper to keep than to explain.

Timestamps are copied byte for byte, never regenerated: the counter-contiguity and clock-drift
findings rest on them. The pcap global header is copied verbatim, so link-type, endianness and
the file's own snaplen survive.

### The proof it is a distillation and not a loss

Both whole-corpus baselines were regenerated and then diffed against the raw ones **field by
field**, across all 85 files:

- **Dropping filler moved `records`, `reac`, `filler`, `trunc`, `dn`, `up`** — exactly the
  quantities that rule is allowed to move.
- **Sampling grants moved six fields and no others**, each by **exactly 5,987,703**, which is
  precisely the number of grants removed: `records` 7,084,889 → 1,097,186, `reac` 7,084,866 →
  1,097,163, `trunc` 6,899,276 → 911,573, `grant` 6,057,849 → 70,146, `cksum` 6,910,123 →
  922,420, and in `ctl2` the one L-key the sampled grants carry, `L4.3.02` 6,053,140 → 65,437.
  A grant is checksum-bearing, so `cksum` loses the same count from numerator and denominator
  alike; it is still 922,420/922,420, with not one bad checksum.
- **The non-grant control frames are exactly conserved: 852,274 before and 852,274 after.**
  That is the whole claim in one number — 6,910,123 − 6,057,849 = 922,420 − 70,146.
- **Zero violations.** `filler`, `scene_transfer` (778,751), `master_hb`, `master_announce`,
  `headamp` (10,101), `box_hb`, `config_announce` (305), `group_map` (107), `record_fragment`
  (40), every head-amp parameter split, the declared port tables (812,903), the `decl` geometry,
  the box match and **both audio tallies** (`dn` 111,613, `up` 73,977) are **identical** before
  and after. A grant sets neither the port table (which reads `op0==0x01`) nor the head-amp record
  nor the box identity, so none of them could move. `L4.3.00` held at 3,173 — the rare grant
  subtype survived whole.
- **Only one of the 85 baseline rows changed**, in both gates: `ctl2.pcap`. The other 84 are
  byte-identical.
- **The two implementations still agree.** libreac's C checker and the Kaitai grammar
  independently report the same 185,590 whole frames and the same 911,573 truncated control
  blocks over the distilled set — and the Kaitai gate, run against the *old* baseline, reported
  the same 5,987,703 delta from the other side before it was re-recorded.

### The gates, and that they can still fail

| gate | over the distilled corpus | sabotaged |
|---|---|---|
| `libreac tools/run-corpus.sh` | green, 85 captures | `--self-test` red (control arm) |
| | | `--self-test-audio` red (audio arm) |
| `reac-protocol spec/corpus-check.py` | green, 85 files fully clean | `--self-test` rejects all 185,590 frames and all 911,573 blocks |

Two things were fixed while proving this, and both were gates that could not fail:

- **libreac's `--self-test` never proved the audio arm.** It flips a control-block byte, and the
  audio decoders read [50:] and never look at the control block — so `dn=`/`up=` could not move,
  and the report would have looked identical over a corpus carrying no decodable audio at all.
  `--self-test-audio` was added: it flips the frame's **end marker**, which is the field
  `reac_frame_inspect` actually validates, and then requires the audio tallies to move *and* the
  control counts to hold still.
- **`spec/corpus-check.py` read only the first 4000 frames per file.** That cap existed because
  the corpus was 47.9 GB. It is now 271 MB and an uncapped run takes well under a minute, so the
  default is 0 — every frame. A cap silently turns "the corpus parses" into "the first 4000
  frames parse".

And the gate was shown to catch a real loss: removing **10** control frames from one distilled
capture moved `cksum=2170/2170` to `cksum=2160/2160` and turned `run-corpus.sh` red.

### The 2 GB question

**Four files exceeded GitHub's 2 GiB per-file LFS limit** in the raw set — `reacpw-reconnect`
(9.118 GB), `ctl2.pcap` (4.758 GB), `m200-pad-v2` (3.517 GB), `m200-pad-sweep` (2.637 GB). Two
more raw files exceed 2x10^9 bytes if the limit is read decimally (`s1608-master-first-link`
2.055 GB, `m200-BIDIR-coldboot` 2.005 GB), but **they were never committed**, so they were never
the push's problem: a scan of every LFS pointer in the history found **four** over the limit and
no more. The count of six is a fact about the raw set, not about this repository's history.

**The distilled set clears the limit with four orders of magnitude to spare: the largest file is
still `ctl2.pcap`, now 46.8 MB, and the next largest is 7.5 MB.** The
oversized objects were nonetheless still *committed*, so `.git/lfs` carried them and the history
was unpushable however small the working tree became. Distilling the working tree does not rewrite
history; that rewrite is below.

**Grants are now sampled, and that is what closed the gap.** `ctl2.pcap` was 442 MB of the
666.5 MB total, and it was not slack: every one of its 6,626,869 records is a control frame (no
filler at all), 6,054,293 of them `grant`. Under a flat "keep every control frame" it could not
get smaller. Sampling grants takes it to 46.8 MB and the corpus to **271.3 MB**.

An earlier draft of this file estimated that decision would land the corpus near 220 MB. It does
not: **the floor is 271.3 MB**, because the 572,576 control frames in `ctl2` that are *not* grants
are kept in full, and they are 37.8 MB on their own on top of the 224.5 MB the other 84 captures
already occupy. The 220 MB figure assumed a saving on frames the rule does not touch.

### The LFS history rewrite, 2026-08-23

The working tree had been small since the distillation, and the repository was still unpushable,
because `git push` offers **every LFS object the history references**, not the ones the tip needs.
Four pointers over the limit sat in 19 commits between 2026-08-21 and 2026-08-22.

`git filter-repo` rewrote them out. The rule was narrow on purpose: a blob callback read every LFS
pointer in the history, and where the pointer declared more than 2x10^9 bytes it replaced that
pointer — and nothing else — with a short note naming the object's **sha256 and byte count** and
saying where the bytes are. Nothing was deleted blindly: each of those four digests is an entry in
`~/Devel/audio/reac-captures-raw/SHA256SUMS.txt`, so the note is a working reference to the file
it replaced rather than a hole.

What was checked afterwards, rather than assumed:

- **The tip is untouched.** `HEAD^{tree}` is the same object id before and after the rewrite,
  `9b79632`, so the 85 distilled captures, the manifest and every finding are bit-for-bit what
  they were. Nothing at the tip carried an oversized pointer, so nothing at the tip could move.
- **All 56 commits survive**, and author name, author email, author date, committer name,
  committer email, committer date and subject are **identical across every one of them** — diffed
  against a bundle of the pre-rewrite history, not eyeballed.
- **No LFS pointer over the limit remains**: 107 pointers, 0 above 2x10^9. The largest object the
  history now offers is `m200-anchor-openwindow` at 1.146 GB, comfortably inside 2 GiB.
- **Four notes, four blobs.** Exactly one replacement per oversized object.

The pre-rewrite history is preserved outside the repository as a verified git bundle at
`~/Devel/audio/reac-captures-pre-lfs-rewrite.bundle` (3.3 MB — the history is tiny; the 30 GB was
all LFS storage). `.git/lfs` still holds the four large objects locally; they are simply no longer
reachable from any commit, so no push will ever offer them.

### Where the raw corpus is

`~/Devel/audio/reac-captures-raw/` — a plain directory, not a git repository, with a README and a
full `SHA256SUMS.txt`. It was copied out with `cp --reflink` on btrfs and verified independently
before anything was overwritten: 85/85 files present, byte totals equal at 47,907,786,044 on both
sides, and all 85 SHA256 digests identical.

## Nothing in this corpus was dropped

All **85** captures are named in BOTH whole-corpus regression baselines (`libreac
tests/corpus-baseline.txt`, now 85 lines with per-file record and checksum counts, and
`reac-protocol spec/corpus-baseline.json`, now 85 files). Deleting any capture turns those gates
red. There are no duplicates to reclaim and no orphans: the corpus was already curated and renamed
from measured facts on 2026-08-21 (`CAPTURE-PLAN-next.md`, `analysis/name_from_facts.py`).

Both baselines were 83 lines until 2026-08-23 and the corpus was 85 — `s1608-bank-2026-08-22/`
had landed without them. libreac's gate was RED for that reason before any distillation began;
the two files contribute exactly 215 control frames, which is the whole of the 6,909,908 →
6,910,123 difference between the old baseline and the corpus. Both are now baselined.

**Nothing was renamed.** A capture cited by name stays citable: the distillation writes to the
same 85 relative paths, so every reference in `libreac tests/`, `reac-pw`, `spec/`,
`HEADAMP-GROUND-TRUTH-2026-07-17.md` and the openmixer docs still resolves. The contents are
distilled; the names are not touched.

**`analysis/dedup_mirror.py` was deliberately NOT used.** It is the obvious tool for the 61% of
the corpus taken through a port mirror, and it is wrong for this job twice: it drops the mirror's
second copy of every frame, which would change per-class CONTROL counts and break the
"identical partition" proof above; and it rewrites `wirelen` to the captured length, which
destroys the `caplen < origlen` evidence that says a session ran at a snaplen. Keeping both mirror
copies costs 50 bytes each and keeps the arithmetic honest. The duplicate geometry (a 1492-byte
frame and its 1494-byte FCS-residue twin) is preserved as evidence in its own right.

The eleven `m200-%Y%m%d-%H%M%S.pcapNN` files look like broken tcpdump rotation output — the
strftime format never expanded — and they are the obvious thing to throw away. They are not.
They are the longest sessions in the set, and `spec/corpus-check.py` carries a comment recording
that a `*.pcap` glob "silently covered 72 of 83 files, and the eleven it dropped were the longest
sessions in the set". They are deliberately in the corpus. Leave them.
