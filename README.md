# reac-captures (PRIVATE)

Raw REAC packet captures from our rig — the ground truth that the decoders, the
[reac-protocol](https://github.com/FreeREAC/reac-protocol) wire-format docs, and the firmware
reverse-engineering are checked against.

**Private, not for publication.** These hold the real rig device MACs, so they cannot go in a
public repo as-is. Small, MAC-sanitized slices are extracted from here into public test fixtures
(e.g. `reac-aes67/tests/fixtures/real_reac_stream.pcap`); the full raw captures stay here. We own
the appliances captured — legitimate capture of our own traffic.

All streams are REAC (EtherType `0x8819`), source OUI `00:40:ab` (Roland). The downstream master
broadcast is a fixed 40-channel / 1492-byte frame; a stagebox's upstream return is a smaller,
box-dependent frame (16-ch → 628 B, 8-ch → 340 B).

## Organisation

The corpus is split across a general `captures/` directory and per-investigation directories
(`<topic>-<date>/`, e.g. `m200-s1608-headamp/`, `courtship-trial-2026-09-12/`) that hold their own
captures alongside the notes and analysis written from them. A directory's own notes are evidence
for its captures — read them together, never edit a capture.

**[MANIFEST.md](MANIFEST.md)** is the catalogue: one row per capture with its device pair, event,
date, truncation, raw and distilled size, and what it is evidence for — read it before assuming a
file's contents from its name. It also documents the distillation (below) and the proof that it
lost no control frame. A capture directory added after the manifest's last update (`git log --
MANIFEST.md`) is not yet catalogued there.

## Naming

`<console>-<box>-<rate>-<tap>__<original-name>-<date>.pcap` — device pair as MEASURED from the
MACs in the file (not as labelled by hand), sample rate, and `tap` (`clean` = single capture
point, `mirror` = a port mirror carrying both directions, so every frame appears twice — a rate
read as packets-per-second off one is 2x wrong). `analysis/name_from_facts.py` derives this from a
capture's own contents. Investigation directories that capture a specific experiment rather than a
generic session use a more descriptive name instead (see `capture-role-change.sh` and
`CAPTURE-PLAN-role-change.md` for one such convention, with `.notes.txt` sidecars).

## Distillation and LFS

`*.pcap`, `*.pcapng` and `*.cap` are LFS-tracked (`.gitattributes`). The captures committed here
are **distilled**: every control frame is kept except `grant`, which — like the audio payload —
is sampled rather than dropped, because the full corpus is 47.9 GB and does not fit GitHub's LFS
limits. MANIFEST.md's "The distillation" section states the exact rule (what is kept whole, what
is sampled, and why) and the proof that distilling changed only the fields the rule allows to
change. The undistilled raw set lives outside git at `~/Devel/audio/reac-captures-raw/`, with its
own README and a `SHA256SUMS.txt`.

## Use

```
# split a capture by stream (frame size) before analysing one direction:
tshark -r captures/<file>.pcap -Y 'frame.len==1492' -w /tmp/downstream.pcap   # 40-ch master
tshark -r captures/<file>.pcap -Y 'frame.len==628'  -w /tmp/upstream16.pcap   # 16-ch box return
```

`analysis/` holds corpus-wide extractors — a streaming pcap reader, a placement scanner, and the
naming/table generators — that read the whole corpus without loading any one file into memory; see
[analysis/README.md](analysis/README.md).

To refresh a public fixture: take a few frames, rewrite the rig MACs to the stand-in
`00:40:ab:c4:80:f6` (keep OUI `00:40:ab`), and drop the result into the consuming repo's
`tests/fixtures/`.

## Adding a capture

1. Capture on a wired tap where possible (`clean`, not `mirror`); note which you took.
2. Name it from measured facts (see Naming above), or write a `.notes.txt` sidecar recording the
   device pair, event and what was physically observed if the name alone can't carry it.
3. Add a row to `MANIFEST.md`: device pair, event, date, truncation, size, and what the capture is
   evidence for. A capture nobody can identify from the manifest is close to worthless.
4. `*.pcap`/`*.pcapng`/`*.cap` are LFS-tracked automatically; commit as normal.
