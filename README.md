# reac-captures (PRIVATE)

Raw REAC packet captures from our rig, kept for **testing and protocol
verification** — the ground truth our decoders, the wire-format docs, and the
firmware RE (`reac-firmware-re`) are checked against.

**Private, not for publication.** These hold the real rig device MACs (the
sanitization tokens), so they cannot go in a public repo as-is. Small,
MAC-sanitized slices are extracted from here into the public test fixtures
(e.g. `reac-aes67/tests/fixtures/real_reac_stream.pcap`); the full raw captures
stay here. We own the appliances — legitimate capture of our own traffic.

All streams are REAC (EtherType `0x8819`), source OUI `00:40:ab` (Roland). The
downstream master broadcast is a fixed 40-channel / 1492-byte frame; a stagebox's
upstream return is a smaller, box-dependent frame (16-ch → 628 B, 8-ch → 340 B).

## Catalogue

| File | Size | Streams | Rate | Notes |
|------|------|---------|------|-------|
| `real_reac_stream.pcap` | 6 KB | 40-ch downstream | 48k | 4 frames; the sanitized public CI fixture lives downstream of this |
| `zoneA-48k.pcap` | 68 MB | 40-ch downstream **+ 16-ch upstream** (628 B) | 48k | both directions, 4000 pps each; the canonical mixed-stream test |
| `zoneB-48k.pcap` | 44 MB | 40-ch downstream **+ 8-ch upstream** (340 B) | 48k | a smaller (8-ch) stagebox return |
| `reac-jitter-sample.pcap` | 2.4 MB | 64-B control frames | — | no audio payload; for re-pacer jitter/timing tests |
| `wired-reac-a-bothdirs-2026-06-09.pcap` | 166 MB | 40-ch downstream + 16-ch upstream | see note | wired tap, both directions; recipe-(f) reference |
| `wired-reac-loud-bothdirs-2026-06-09.pcap` | 166 MB | 40-ch downstream + 16-ch upstream | see note | as above, loud signal level |

> **Note on the `*-bothdirs-*` captures.** The downstream frames clock at
> ~16000 pps and the upstream at ~8000 pps — i.e. 2× the single-stream rates.
> That is consistent with either a 96 k capture or a dual-point merge that sees
> each frame twice. Confirm the per-stream rate (de-duplicate / split by capture
> point) before using these for exact timing work.

## Use

```
# split a capture by stream (frame size) before analysing one direction:
tshark -r captures/zoneA-48k.pcap -Y 'frame.len==1492' -w /tmp/downstream.pcap   # 40-ch master
tshark -r captures/zoneA-48k.pcap -Y 'frame.len==628'  -w /tmp/upstream16.pcap   # 16-ch box return
```

To refresh a public fixture: take a few frames, rewrite the rig MACs to the
stand-in `00:40:ab:c4:80:f6` (keep OUI `00:40:ab`), and drop into the consuming
repo's `tests/fixtures/`.

## Adding captures

Name `<scope>-<rate|kind>-<date>.pcap`, note the streams + rate + how it was
tapped here, and keep the raw original (LFS-tracked by extension).
