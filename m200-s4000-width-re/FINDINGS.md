# S-4000S upstream-width RE — dynamic box width

**Date:** 2026-07-24. **Goal:** make reac-pw open the S-4000S digital snake's FULL
32-channel audio return, by generalising box width to a fully DYNAMIC value (read what
the snake declares in the handshake) — deleting every per-width special case
(`OBSERVED_PLACEMENT` etc.). Symmetric payoff: the same field the master READS is the one
the slave DECLARES → arbitrary-width virtual stageboxes.

## The problem, measured

Under reac-pw `--mixer m200`, the S-4000S (box MAC `00:40:ab:c4:08:bc`, 32 analog in)
streams only **8 channels** upstream (340-byte frames — `frame_len = 52 + nch*36`, so
340 = 8ch). A real M-200 opens the same snake to **32ch (1204-byte frames)**. reac-pw
already drives the S-0808 (8) and S-1608 (16) at full width — so the dynamic mechanism
works ≤16 and breaks above 16.

## Confirmed on the wire (goldens in ../captures/)

| golden | master | snake upstream | note |
|---|---|---|---|
| matrix-m200-s4000-2026-07-24.pcap | real M-200 (`…c9:cc:03`) | **1204B = 32ch** | 8→32 at cold-connect, ts ~1784851874.9445 (last 340B @ .943309, first 1204B @ .945651) |
| matrix-m5000-s4000-unit1/2-coldconnect | M-5000 (OHRCA) | 1204B = 32ch | same snake, cross-check |
| matrix-m200-s1608 | M-200 | 628B = 16ch | WORKS under reac-pw — baseline |
| matrix-m200-s0808 | M-200 | 340B = 8ch | WORKS — baseline |

The 8→32 is console-generation-independent (both M-200 V-Mixer and M-5000 OHRCA do it),
so it is NOT about OHRCA/rate. (Aside: `reac_master.c:159` hardcodes `console_field!=0 →
96000`; the real M-5000 does 48/96/192 — that hardcode is a reac-pw simplification, not a
constraint, but it is NOT this bug.)

## Ruled out (do not re-derive)

- **Decoder** — `reac_upstream.c` already handles up to 32 (`reac_upstream_channels`).
- **cfea announce width** — reac-pw's cfea (src `…cc:04`) declares box width `0x20`=32 at
  payload offset 20 (fabric `0x28`=40 at offset 19), byte-identical to the M-5000's cfea
  except the console-gen byte at offset 21 (reac-pw `0x00` V-Mixer vs M-5000 `0x01` OHRCA)
  + MAC/counter/checksum.
- **Head-amp / grant span** — control reaches box input 16 (operator saw 48V toggle), and
  `reac_master_set_box(in_ch=32)` is called (`reac_pacer.c:263`); the grant sweep builds
  32-wide (`REAC_GRANT_MAX_WIDTH`=32, `alloc_fits(0,32)` OK).

So the snake accepts head-amp control across 32 but caps its AUDIO RETURN at 8: the
differentiating field had to be one the snake reads to decide how many slots to FILL.

## SOLVED (2026-07-24): the ENROLL group map is the audio-width gate

The trimmed golden `../captures/matrix-m200-s4000-coldconnect-2026-07-24.pcap` (6 s,
probing → cold-connect → widen → JOIN → grant burst) shows the widen SEQUENCE — an
ORDER of states, not a timing recipe:

```
874.724  console  cdea 0102 000e         negotiation op begins (box connecting)
874.733  box      cdea 0103 0010         CONFIG-announce (3rd frame; box streams 8ch/340B)
874.941  console  cfea ffff 0100         one-shot cfea (console MAC, fabric 0x28, width 0x20)
874.942  console  cdea 0103 000d         ENROLL — the group map, 32-wide      ← THE GATE
874.9456 box      340B → 1204B           BOX WIDENS 8→32ch, 3 ms after the ENROLL
874.946  console  cdea 0103 0019         CHANMAP resumes
876.5    box      cdea 0403 JOIN         head-amp phase (separate, later)
878      console  cdea 0403 grant burst  head-amp arming sweep
```

**The ENROLL group map is a pure function of width — NO per-box special case.** In the
block (from the `cdea` marker), the input region `[9:14]` carries `width/8` bytes of
`0x41` packed from the front; the output region `[14:19]` carries the remaining groups
as `0xc3` packed from the back:

| box | width | input region | output region |
|---|---|---|---|
| S-0808 | 8 | `41 00 00 00 00` | `00 c3 c3 c3 c3` |
| S-1608 | 16 | `41 41 00 00 00` | `00 00 c3 c3 c3` |
| S-4000S | 32 | `41 41 41 41 00` | `00 00 00 00 c3` |

Cross-console verified byte-for-byte on the goldens: **M-200, M-300 and M-5000 emit the
identical map for the same box** — only the console-model byte at block `[8]` differs
(`0x00` V-Mixer / `0x01` OHRCA). Also checked: the CHANMAP sweep advertises the full
40-slot fabric regardless of box (width-independent), and the M-200's first grant frames
to an S-0808 vs an S-1608 are byte-identical — no per-box constant anywhere in the
width path.

**reac-pw's bug (branch `feat/dynamic-enroll-width`, commit `d037319`):** it emitted a
STATIC 8-ch ENROLL (`1×0x41`) once at GRANTING-start — recognition
(`reac_master_set_box`) later learned width 32 and rebuilt the grant sweep + cfea width
byte but never touched `enroll_blk`. Circular trap: enrol 8 → box streams 8 →
"recognize" 8. Fix: `set_enroll_width()` derives the group map from width;
`set_box` applies the declared width + flags a one-shot re-emit that the GRANTING dwell
delivers (matching the golden's post-CONFIG enrol); the default seed is the wide-safe
32 (`4×0x41`+`1×0xc3`, the widest real-box config) so an unrecognized box still opens
fully.

**Live result (2026-07-24):** S-4000S upstream went 340 B → **1204 B / 32 ch** on the
wire; music + 48 V phantom on box inputs 16 AND 32 confirmed by the operator by ear.
S-0808/S-1608 regression pending a box swap.

**Still open on the width topic:** the head-amp CH base for the S-1608 (`0x20` in
`reac_grant.c` / prior live 48V evidence) appears in NO capture here — the goldens are
steady-state and never show a real M-200 editing an S-1608 head-amp. Needs a dedicated
capture (M-200 + S-1608 + a 48V toggle) before touching that rule.

**Constraint:** reac-pw merges to main auto-deploy → the fix lives on branch
`feat/dynamic-enroll-width`, manual-launch tested, not merged until the operator
confirms.
