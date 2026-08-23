# S-1608 bank investigation — openmixer rig night, 2026-08-22

Two captures rescued from the `openmixer` repo, where they had been committed by mistake:
captures do not belong in the console's repo. They were `rig/wire.pcap` and `rig/wire-act.pcap`
on the branch `investigate/s1608-bank0-rig`, and they are cited by name from that night's
`FINDING-headamp-base-off-by-8.md`.

| here | was | size | sha256 |
|---|---|---:|---|
| `reacpw-s1608-48k-clean__nightR-wire-2026-08-22.pcap` | `rig/wire.pcap` | 17.4 MB | `5e8846ba2771abf7…` |
| `reacpw-s1608-48k-clean__nightR-wire-act-2026-08-22.pcap` | `rig/wire-act.pcap` | 107.6 MB | `cc01d030d4f351ff…` |

Pair is **reac-pw (master) x S-1608 at 48 k**, and the tap is **clean, not mirrored** — measured,
not assumed: `analysis/verify_unique.py` reads 63 895 and 395 642 REAC frames with zero duplicates
and zero mis-parses.

## BOTH ARE TRUNCATED AT SNAPLEN 256

Every record keeps 256 bytes of a 1492-byte frame. That is fine for the head-amp records these
were taken for — they live at bytes 32–40 — and useless for anything structural. The night's own
result note says so explicitly:

> My pcaps used `-s 256`. Fine for head-amp records, which live at bytes 32–40, but F warns a
> truncated 1492-byte frame passes `canonical_len()` as a legal 18-channel frame — use a full
> snaplen for anything structural.

## What they are evidence for

`wire` is **the emitter exoneration**. Commanding SENS on console channel 24 emitted phantom=1,
pad=0, SENS=44 for CH 0x2f; the same command on channel 16 emitted the same three for CH 0x27;
both checksum-clean, same count, same order. That refutes "the console writes phantom false"
directly — we put a correct record on the wire for a channel that does not light.

`wire-act` is the actuation window behind the slot map: head-amp slots **0x20..0x27 actuate and
0x28..0x2f do not**, which is what made a pure addressing offset look like a bank split.

The inference drawn that night — that the S-1608's head-amp base is 0x18 — was **refuted** in the
same document by 21 real grant sweeps across three desk models placing the box at 0x20..0x2f. What
survives is the measurement, not the reading. Anything built on these two files should start from
`FINDING-headamp-base-off-by-8.md`, which carries both the data and its own refutation.

## Note for the corpus gates

Adding these takes the corpus from 83 captures to 85, so the per-file baselines in
`libreac tests/corpus-baseline.txt` and `reac-protocol spec/corpus-baseline.json` will report two
unknown files until they are regenerated. That is expected and deliberate, not a regression.
