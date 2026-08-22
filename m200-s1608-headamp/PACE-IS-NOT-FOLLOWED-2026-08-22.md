# The boxes do not follow our pace — and 96 kHz mislabels the audio

2026-08-22, night. Rig: S-0808 `00:40:ab:c4:dc:9c` on `enp131s0`, S-1608
`00:40:ab:c4:80:41` on `eth0`, one reac-pw master per segment, reac-pw main
(nodes are PipeWire adapters since `513b741`).

## What was measured

**A real Roland stagebox follows the master's pace, symmetrically.** From the corpus,
counting frames per source and correcting for the mirror tap:

| capture | desk raw | desk true | box raw | box true |
|---|---|---|---|---|
| `m200i-s1608-48k-mirror__…BIDIR-coldboot` | 8000 | **4000 = 48 k** | 4000 | **4000 = 48 k** |
| `m5000-s1608-96k-mirror__real-s1608-coldboot` | 16000 | **8000 = 96 k** | 8000 | **8000 = 96 k** |

The mirror correction is not a guess: the desk copy shows 117 728 / 387 708 adjacent-identical
frames and two frame sizes two bytes apart (the clean copy plus the FCS residue documented in
libreac `reac.h:35-47`); the box copy shows essentially none and a single size. Desk
duplicated, box not. Halving both — the obvious mistake — reads a 96 kHz box as 48 kHz and
is how this was first got wrong tonight.

Frame sizes are rate-independent (desk 1492/1494 B, box 628/630 B): 40 slots × 12 samples ×
3 bytes. **The pace IS the packet rate**, matching libreac's byte law `pps = rate / 12`
(`src/reac.c`): 44.1 k = 3675, 48 k = 4000, 96 k = 8000.

**Our boxes do not follow.** With `--rate 96000` on both segments:

- our master TX: **7996 pps, 1492-byte frames, mean interval 125.1 µs** (p10 120.9, p50 124.9,
  p90 129.0, p99 142.1) — byte-identical and cadence-identical to a real 96 kHz desk;
- S-1608 answers **4000 pps**; S-0808 answers **4000 pps**.

Both boxes, including the one whose preamps demonstrably obey us. Two independent units
behaving identically accuses the master, not the boxes.

**Consequence, and it is an audio-correctness defect.** reac-pw declares its capture node at
the CONFIGURED pace regardless of what arrives: `reac-capture.s1608` published
`F32P 16 96000` while the box delivered 4000 pps × 12 samples = **48 000 samples/s**. reac-pw
reported `gaps=0` throughout. PipeWire reported `ERR 0`. Every soft indicator read healthy
over a stream labelled at twice the rate it carried.

At `--rate 48000` everything agrees — our TX 4000 pps, both boxes 4000 pps, nodes declare
48000 Hz — so the rig has been left there.

## Where the pace does NOT ride

- **Not the cfea master-announce.** Same box, both rates, the only differing constant
  offsets are `[14:17]` (the desk MAC) and `[19]`, the console generation. `[17]` is `0x28`
  (40 slots) at both rates and `[22:33]` is zero at both. `analysis/announce_bytes.py`.
- **Not the console generation byte.** Running `--mixer m5000` (gen `0x01`, the OHRCA value a
  96 kHz M-5000 sends) at `--rate 96000` left the S-1608 at 4000 pps.
- **Not the chanmap.** `cdea 0103 len 25` has identical constants at both rates.
- **Not the TX cadence alone** — ours is correct to 0.1 µs of the target and the box ignores it.

## The corpus cannot answer this

**Family and rate are perfectly confounded in it**: every M-200 capture is 48 k, every M-5000
capture is 96 k. So the three ops a 96 kHz desk sends that we never send — `cdea 0100 len 26`,
`cdea 0101 len 24`, `cdea 0102 len 14` (`analysis/rate_field_hunt.py`) — are equally
explicable as OHRCA-family chatter. Nothing in 47 captures separates the two.

**The deciding capture** therefore needs a real desk switched between rates with everything
else held constant — same desk, same box, same cable — capturing across the switch. That is
the one experiment that isolates the pace from the family, and it needs the Roland desk.

## Method notes

- `analysis/slot_rms.sh` needs `tcpdump -Z root`: tcpdump drops to an unprivileged user and
  cannot write a file we pre-created, and the empty capture reads exactly like a silent box.
  The probe now takes a NAME from `mktemp -u` and lets tcpdump create the file.
- `iter_packets` yields `(ts, wirelen, frame)`. Unpacking it as a bare frame makes `is_reac`
  false for every packet and prints "no announce in this capture" — a clean-looking null.
  `announce_bytes.py` now prints the REAC frame count beside the verdict so the two cannot be
  confused.
- `pw-record --target=… --channels=8` downmixed: ch3–8 came back at −240 dBFS (all-zero) on a
  box whose wire slots were live. The graph side is not a per-port oracle; the wire is.
