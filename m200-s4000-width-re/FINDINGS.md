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

So the snake accepts head-amp control across 32 but caps its AUDIO RETURN at 8. The
differentiating field is subtler — in the grant burst / chanmap / downstream fabric, or
a config/identity frame the snake reads to decide how many slots to FILL. It SCALES with
width (reac-pw computes it right for ≤16, wrong/truncated at 32).

## The generalisation (target)

The snake declares its own width/base/model in its handshake frames; reac-pw should READ
that per-connection rather than look up a table. Prime special case to delete:
`OBSERVED_PLACEMENT` in `reac_grant.c` (`{8→0x00, 16→0x20, 32→0x00}` — non-monotonic, so
NOT a width→base formula; the base is likely the box's own declaration / head-amp CH
base). reac-pw's SLAVE (`reac_slave.c`, `--box-channels`, task #134) ALREADY stamps a
width into its box→master frames — very likely the SAME field the master must read
(shortcut + confirms the encoding).

## Open (RE agent decoding)

WHERE in the box→master frames the snake declares width/base; the exact per-width special
cases to replace with dynamic derivations; validation that 8/16/32 reproduce the goldens
so 24 (S-2416) falls out. Then: read it, delete the tables, derive the rest.

**Constraint:** reac-pw merges to main auto-deploy → the fix lives on branch
`feat/dynamic-box-width`, manual-launch tested, not merged until the operator confirms.
