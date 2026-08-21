# S-1608 inputs 9–16: open on the fabric, converting nothing (rig, 2026-08-21 02:05–02:20)

Live rig, direct cable `enp131s0`, one reac-pw master (free-running pacer, `--rate 96000`),
S-1608 `00:40:ab:c4:80:41` ESTABLISHED, base 0x20, declared 16x8.

## What was measured

Per-channel RMS of the box's upstream FILLERs, decoded through libreac
(`reac_upstream_decode`, tool in `analysis/up_slots.c`):

| box input | wire RMS | reading |
|---|---|---|
| 1–7 | −88.8 dBFS | enrolled, idle preamp noise floor |
| 8 | −45..−69 dBFS | the live mic (varies with the room) |
| 9–16 | −106 dBFS | mathematical zero |

The probe proved it can detect presence in the same command that reported the absence:
input 8 sits 26 dB above the idle floor while 9–16 sit 17 dB below it. Three states are
distinguishable — signal, enrolled-idle, zero — so −106 is a real absence.

## What that absence is NOT

**Not a probe pointed sideways.** `reac_upstream_channels(len)` returns **16** for these
frames and the decoder was re-run printing all 40 fabric slots: slots 17–40 carry no data
at all. The zeros are in the box's own 16 declared slots.

**Not the ENROLL width gate** (the S-4000S defect solved in `m200-s4000-width-re`, commit
`b3548c9`). That gate sets the upstream FRAME SIZE — the S-4000S went 340 B → 1204 B/32ch
when the map widened. This box is already emitting a 16-channel frame, so the group map
that reached it opened all 16. reac-pw main carries the width-derived map
(`reac_master.c:set_enroll_width`, 16ch → 2×0x41) and the GRANTING-dwell re-emit; the
establish log shows recognition (`S-1608 (16 in / 8 out)`) landing one tick before the
`PROBING -> GRANTING (rx CONFIG)` edge, which is the path that arms `enroll_pending`.

**Not an un-enrolling scene.** The hypothesis carried into this session — that a scene with
SENS 0 un-enrols a channel — is refuted on the wire (below).

## The group-A record reaches CH 0x2f and changes nothing

Desk ch7 is patched to `reac-capture:capture_16` (head-amp CH 0x2f). A PATCH through
openmixer's `/channel/input/7/headAmp` was captured on our own TX
(`ether[16]=0xcd and ether[18]=4 and ether[19]=3`) and decoded:

```
01 01 2f 00 01    CH 0x2f  param 00 (phantom)  value 1
01 01 2f 02 14    CH 0x2f  param 02 (SENS)     value 0x14 = 20 dB
```

Byte-correct, on the wire, addressed to the right channel. Box input 16 stayed at
−106.1 dBFS across SENS 10 and SENS 20 with phantom on.

## The zero-scene hypothesis is refuted

On CH 0x27 (box input 8), an ALREADY-ENROLLED channel:

| scene written | box input 8 |
|---|---|
| phantom off, SENS 1 | −48.0 dBFS (alive) |
| phantom off, pad off, SENS 0 — the full all-zero scene | −55.2 dBFS (alive) |

An enrolled channel does not un-enrol when an all-zero scene lands on it. So
`reac_grant.c`'s enrolling default is not defending against un-enrolment of a live channel;
whatever the enrolling default buys, it is bought at establishment, not per write.

Still open from that same note: the MINIMAL enrolling value, and whether SENS alone enrols a
channel that has never enrolled. Neither is answered here — both writes above landed on a
channel that was already live.

## The goldens: a real M-200 DID convert on input 16

`analysis/up_slots.c` over the corpus, 400 frames sampled at `skip 50000` (established, not
the cold-connect transient):

| capture | slot 1 | slot 3 | slot 7 | slot 16 |
|---|---|---|---|---|
| `m200-ch16-anchor-toggle-20260721-220347` | −63.8 | −94.0 | −53.3 | **−35.3** |
| `m200-s1608-COLDCONNECT-clean-2026-07-24` | −58.1 | −88.1 | −29.4 | **−67.4** |
| `m200-headamp-1357_16-toggle3-20260721-214420` | −65.0 | −93.8 | −52.0 | **−32.5** |

The third capture's name states its own scene — channels 1, 3, 5, 7 and 16 — and the slots
that carry signal are 1, 3, 7 and 16. So the upper bank is not a hardware limit of the
S-1608, and it is not something only an OHRCA desk can reach: a V-Mixer M-200 had input 16
converting at −32 dBFS.

That makes this a divergence between what a real desk sends and what reac-pw sends, and
the chanmap is NOT that divergence (see below).

## The 1 Hz chanmap is byte-faithful — ruled out

The steady-state control plane is one frame each way per second: we send CHANMAP
(`cdea 0103 0019`), a rolling 8-entry window over the 49-position ring, and the box answers
`cdea 0103 0001` `81 00`, byte-identical every second (it carries nothing about banks).

Our chanmap flags 0x28–0x2f with `0x38` and everything else with `0x28`
(`reac_master.c:gen_chanmap`, hardcoded). `analysis/placement_rows.jsonl` shows every real
desk doing exactly the same to a real S-1608 — M-200i, M-300 and M-5000 alike, in
`m200-s1608-BIDIR-coldboot`, `matrix-m300-s1608`, `matrix-m5000-s1608`,
`real-m200-s1608-coldboot`. The flag correlates perfectly with the dead bank on our rig,
and is still not the cause.

## One measurement nuance worth keeping

Our dead slots read ~−106 dBFS, which is roughly 1 LSB of dither — a converter that is
running. Absolute absence reads −200 (the probe's log floor, i.e. all-zero samples), which
is what `m200-s1608-BIDIR-reboot` shows in slots 1–8 while its slots 9–16 carry −94..−106.
So "−106" and "no data at all" are different states, and the corpus contains both.

## Where the next evidence is

A golden where a real M-200 had all 16 S-1608 inputs converting, diffed against what reac-pw
sends. Candidates in this directory: `m200-ch16-anchor-toggle-*`, `m200-ch16-anchor-v2-*`
(both name ch16 explicitly), `m200-s1608-COLDCONNECT-clean-2026-07-24.pcap`. The question to
put to them: what does the console send that we do not, between CONFIG and the box opening
its upper bank — and does the golden's box ever stream non-zero in slots 9–16 at all.

The chanmap flag difference already noted for 0x28–0x2f (0x38) in `m200-headamp-re/DECODE.md`
is the standing lead.
