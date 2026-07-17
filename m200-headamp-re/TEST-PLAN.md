# REAC head-amp + stagebox — test plan (2026-07-17)

What landed overnight and what still needs **live-rig verification**. Everything below is committed
and merged; the tests confirm it behaves on hardware, not just in offline byte-compare.

## What merged (no test needed — already verified offline / on the wire)

- `FreeREAC/reac-protocol` **#1** — wire-format: head-amp source control + state-assertion model + per-model CH base + width-driven base.
- `FreeREAC/reac-pw` **#36** — `reac_ctrl_build_headamp` + TAG dispatch (#33 fix). 16/16 tests pass; byte-exact vs 294 real M-200 records; adversary could not refute.
- `FreeREAC/reac-pw` **#32** — passive REAC discovery node props.
- `FreeMixer/openmixer` **#291** — head-amp design spec (#155). **#267** — audio KB index. **#290** — discovery from reac-pw node props.
- docs-mcp memory `reference_reac_headamp_source_control` — indexed + pushed.

## MUST TEST on the rig

### A. reac-pw stagebox — establishment on the merged binary
1. **Box re-establishes cleanly** on `main` binary (`reac-pw --role slave --tx enp131s0`): FLOOD_ANNOUNCE → COLDCONNECT → TX_MUTE → ESTABLISHED. *Left in COLDCONNECT at hand-off — may need a PHY bounce (box only cold-connects on link-up) or the M-200's 600-frame link-check to expire from the prior session. Confirm it reaches ESTABLISHED, and time how long.*
2. **Settled frame rate** — an established box emits ~a handful of control frames/s, NOT thousands (the stale 10-July binary flooded 31,922). Confirm `tcpdump` shows single digits.
3. **M-200 shows the device** on its own screen when established.

### B. Head-amp RECEIVE (already proven once — reconfirm on merged binary)
4. **Box receives phantom/pad/SENS** from the M-200 at CH `0x20`, and the merged binary now **classifies them as HEADAMP, not GRANT** (the #33 fix). Verify the FSM does NOT mistake a knob-turn for a grant during/after join.
5. **Full SENS sweep** `0x00..0x37` decodes to −65…−10 dBu (pad-off) / +10 (pad-on). Confirm the pad-relative offset live.
6. **Does the slave LOG received head-amp values?** (Reviewer noted the RX path feeds the FSM but may not surface values.) If not, decide whether to add a decode log line.

### C. Head-amp SEND (reac-pw as MASTER — NOT yet built; spec only)
7. `reac_ctrl_build_headamp` exists and is byte-exact, but reac-pw does **not yet drive it as a master** to a real box. Test only after #155 wiring: send phantom/pad/SENS to a real S-0808/S-1608 and **measure 48 V at the XLR pins** (a green button is not evidence).
8. **Pad shifts SENS by the box, not us** — set SENS, engage pad, confirm the level moves 20 dB with NO SENS frame on the wire.

### D. Known gaps that will bite (open issues)
9. **reac-pw #34** — we send no TAG `05 00` model identity. Width alone got us base `0x20`; confirm whether identity is ever needed (e.g. for the master to assign head-amp-controllable inputs, or for correct enrolment on other consoles).
10. **reac-pw #35** — our stand-in MAC `c4:80:41` collides with a real S-1608. Switch to our own NIC MAC; until then captures with both boxes present are ambiguous.
11. **DMX-style periodic re-assert** as a master (openmixer #155) — a fire-and-forget master leaves 48 V on the pins after a lost frame. Not built; test the re-assert loop once it is.

### E. Regression / hygiene
12. **Establishment not regressed** by the TAG dispatch change — a real cold-connect (TAG `01 00`) must still classify GRANT and grant our slave. (Offline courtship test passes; confirm live.)
13. **Auto-deploy** — reac-pw merges to main auto-deploy (build+test+setcap+restart unit). Confirm the merge of #36/#32 deployed cleanly and did not disturb the manually-run slave.
14. **openmixer #290 discovery** — the web-ui shows discovered REAC devices sourced from reac-pw node props (no socket/subprocess).

## Rig state at hand-off
- reac-pw `main` = `dd7e329` (head-amp merged), local binary rebuilt + setcap'd, box **re-establishing** on `enp131s0`.
- USB tap capture (`ctl2.pcap`) still running — 4.7 GB, stop it if not needed (`pkill -f 'tcpdump.*ctl2'`).
- reac-captures clean/pushed. All FreeREAC + openmixer non-draft PRs merged; 6 openmixer **drafts** left open by design.
