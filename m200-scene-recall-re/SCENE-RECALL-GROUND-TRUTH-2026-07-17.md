# M-200 scene recall = the COMPLETE head-amp status push (2026-07-17)

Ground-truth capture of a real Roland M-200 driving the S-1608 (`00:40:ab:c4:80:41`),
taken on the switch **mirror port** (both directions), while the operator ran a scripted
sequence: connect + load the desk's default scene, then toggle 48V on reac1 / reac16 / reac3
a few times, ending all three OFF.

- `m200-scene-recall-2026-07-17.pcap` — the capture, truncated to 160 B/frame (control
  region; the bulk audio is dropped to keep it indexable). Desk MAC `00:40:ab:c9:cc:03`.
- `decode_scene.py` — reusable decoder (scene snapshot + final state + transition log).
- `SCENE-DECODE-2026-07-17.txt` — its output on this capture.

## The key mechanism: a scene sets EVERY port's full head-amp at once

On scene recall the M-200 pushes head-amp records (`cdea 04 03 … 12 12 01 01 CH PARAM VAL`)
for **all 16 channels × all 3 params** in a single tight burst — the complete scene is on
the wire within **0.15 s**. The box applies it as one state. This is what "the scene sets
all the ports" means, and it is a single, atomic, complete push — NOT a trickle of edits.

### The complete scene the M-200 pushed (ground truth)

| input | ch | phantom | pad | sens | dBu |
|---|---|---|---|---|---|
| reac1 | 0x20 | 1 | 0 | 0x11 | −27 |
| reac2 | 0x21 | 0 | 0 | 0x07 | −17 |
| reac3 | 0x22 | 1 | **1** | 0x14 | −10 |
| reac4 | 0x23 | 0 | 0 | 0x0d | −23 |
| reac5 | 0x24 | 1 | 0 | 0x00 | −10 |
| reac6 | 0x25 | 0 | 0 | 0x00 | −10 |
| reac7 | 0x26 | 0 | 0 | 0x13 | −29 |
| reac8 | 0x27 | 0 | 0 | 0x13 | −29 |
| reac9 | 0x28 | 0 | **1** | 0x0d | −3 |
| reac10 | 0x29 | 0 | 0 | 0x00 | −10 |
| reac11 | 0x2a | 0 | 0 | 0x00 | −10 |
| reac12 | 0x2b | 0 | 0 | 0x00 | −10 |
| reac13 | 0x2c | 0 | 0 | 0x00 | −10 |
| reac14 | 0x2d | 0 | 0 | 0x00 | −10 |
| reac15 | 0x2e | 0 | 0 | 0x12 | −28 |
| reac16 | 0x2f | 1 | 0 | 0x22 | −44 |

All three parameters are present and varying in this ONE capture, so pad and sens are
already decoded — no separate pad/sens captures are needed:

- **PARAM 0x00 = phantom** (48V), value 0/1.
- **PARAM 0x01 = pad** (−20 dB), value 0/1 — present here on reac3 and reac9.
- **PARAM 0x02 = sens** (0x00..0x37, 1 dB/step). Law: `dBu = −10 − value + (pad ? 20 : 0)`.
  Pad's −20 dB is applied via this +20 offset when pad=1, exactly as the operator noted
  ("pad already sets it −20").

## Timeline (relative to desk connect)

```
+0.00s  op 0100 (SYSPARAM)   \
+0.68s  op 0102               |  scene setup: SYSPARAM + chanmap + sub-state blocks
+1.48s  op 0103 (SCENE map)   |
+2.69s  op 0101              /
+6.86s  op 0403  <-- COMPLETE head-amp scene push, all 16ch x 3 params in ~0.15s
+23s    reac1 phantom on/off x3, ending OFF   (operator edits = incremental op-0403)
+29s    reac16 phantom on/off x3, ending OFF
+35s    reac3  phantom on/off x4, ending OFF
```

Note the scene MAP ops (0100/0102/0103/0101) come first, then ~4 s later the full head-amp
push. Operator edits after that are single incremental op-0403 records for the one changed
(channel, param).

## Implication for reac-pw (the operator's hypothesis)

When reac-pw takes over, the box resets every channel to off **because our scene is empty /
incorrect** — the box faithfully applies whatever complete state we push, and ours carries
no real per-channel values. To make the box hold head-amp, reac-pw's group-A push must be a
COMPLETE, CORRECT scene: all 16 channels, all 3 params, with the intended values — the exact
shape captured above — not zeros-plus-overrides.

Open question to test next: make reac-pw's group-A sweep emit this exact 16×3 scene (byte
values above) and re-run the objective test / LED check. Earlier tests pushed a structurally
complete but value-empty sweep; this capture is the first clean template of a *correct* full
scene to replicate and verify against.
