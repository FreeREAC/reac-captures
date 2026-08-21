22:41:34.631  CAPTURE STARTED (all traffic, full frames, mirror tap)
22:41:34.635  our reac-pw-master STILL UP — S-0808 established (baseline on tape)
22:41:37.681  STOPPED reac-pw-master — we are no longer master; segment should go quiet
22:42:49.434  M-200 POWERED ON — S-0808 synched/enrolled to M-200
22:48:04.783  OPERATOR: 48V ch1 ON->OFF cycle DONE (unlabelled window)
22:50:16.353  OPERATOR: 48V ch3 ON->OFF cycle DONE
22:52:25.442  OPERATOR: set SENS on ch1 (head-amp sensitivity)
22:58:43.599  === POWER CUT / REBOOT — session1 saved as ctl-session1-precut.pcap; session2 starts ===
22:59:28.681  ANCHOR: ch3 SENS currently reads -17 dB on the M-200
23:00:53.271  ANCHORS ch?: started -17dB -> -40 -> -60 -> -65 (MAX sens) -> -10 (MIN sens)
23:00:53.272  RANGE: SENS spans -65dB (max gain) .. -10dB (min gain) = 55 dB
23:03:50.316  CONFIRMED by operator: the SENS sweep batch was ch1 (byte22=00) — decode holds
23:04:04.051  OPERATOR: polarity ch1 ON->OFF
23:04:59.545  OPERATOR CONFIRMS: polarity ch1 ON->OFF done — NO op=0403 frame seen; widening to all ops
23:07:12.665  OPERATOR: moved PAN — expect nothing on the wire (console-side param)
23:07:54.141  MEASURED: polarity+pan produced 532 new frames, op=0403 count UNCHANGED at 206 -> neither is a stagebox param
23:11:47.189  OPERATOR: swept MAIN fader — testing whether box OUTPUT level is a box param
23:12:37.273  MEASURED: MAIN sweep -> 1092 new frames, op=0403 STILL 206. Box owns ONLY phantom+SENS. Surface complete.
23:15:08.113  OPERATOR: PAD toggled on ch1 — the falsifiable test of the ownership rule
23:19:30.048  OPERATOR: about to toggle PAD on ch3 (2x2 confirm for pad)
23:22:50.763  OPERATOR: PAD ch3 done. KEY: engaging pad makes the M-200 SENS display jump -15 -> +5 (=+20dB). Pad = 20dB attenuator, shifts the SENS scale. Q: does VALUE re-send, or is VALUE pad-relative?
23:26:33.999  ANCHOR 2: SENS -30 -> pad on -> -10 (+20dB again). Pad offset confirmed at two independent points.
23:31:03.874  OPERATOR: about to toggle HPF on ch1. PREDICTION: ambiguous — fires => box has ANALOG HPF (param 03, headroom is physical); silent => HPF is console DSP. Cannot refute the rule either way.
23:32:58.967  OPERATOR: HPF ch1 toggled AND frequency swept up/down
23:36:05.082  MEASURED: HPF ch1 toggle+freq sweep -> op=0403 UNCHANGED at 484. No analog HPF; console DSP. ALSO: t=1858 full state push enumerates 8ch x 3 params. ALSO: real cksum = record sums to 0x80 (0x7e was a special case).
23:38:49.953  OPERATOR: EQ ch1 exercised. THE FALSIFICATION TEST — EQ is pure arithmetic, the rule says SILENT. If op=0403 fires, the rule is DEAD.
23:40:10.027  MEASURED: EQ ch1 -> ZERO box commands. The +256 op=0403 frames are 4 PERIODIC state pushes (t=2062/2107/2197/2287), all values byte-identical, ch1 unchanged. RULE SURVIVES ITS FALSIFICATION TEST. EQ generated 2728 op=0100 SCENE/SYSPARAM frames instead. NEW: TAG 0500 (48 frames) undecoded.
23:42:05.837  OPERATOR HYPOTHESIS (correct): the push is the mixer re-asserting state to survive lost frames on an unACKed broadcast link. MEASURED: head-amp push follows a SCENE/SYSPARAM transfer by EXACTLY 4.4s, 7/7 -> it is phase 2 of ONE whole-console state broadcast, not a head-amp timer. Trigger still unknown; intervals irregular (46/1011/204/45/90/90s).
00:01:03.203  MATRIX ANALYSIS (no hardware): CH HAS A PER-BOX BASE — S-0808:0..7, S-1608:32..47, S-4000:0..31 (2 different S-4000 units both 0..31, so NOT a unit-ID switch; base NOT derivable from width). TAG 0500 = capability/identity exchange (master records constant across M-200/M-300/M-5000; box records track the box model). TAG 0302 box-only constant. record_len = oplen - 0x0d (0x80 sum holds 913/913 across FOUR oplens).
00:01:48.001  === S-1608 SESSION: operator connecting an S-1608 (S-0808 currently enrolled to M-200). GOAL: anchor the per-box CH base to a PHYSICAL channel (July captures show range 32..47 but nothing anchors which channel is 0x20), + settle intrinsic-vs-allocated, + catch the S-1608 enrolment (TAG 0500 identity).
00:05:15.954  OPERATOR: S-1608 connected (S-0808 still on segment). Reading enrolment BEFORE any control is touched.
00:07:04.873  OPERATOR: UNPLUGGED the S-0808 — S-1608 alone on the segment. THE clean intrinsic-vs-allocated test: with 0..7 now free, does the S-1608 stay at 32..47 or slide to 0..15?
00:07:56.921  OPERATOR: reconnected the S-0808 cable (S-1608 already holding 32..47). Tests whether a LATE-joining box still takes its intrinsic base, + a 2nd enrolment on tape.
00:09:18.465  CLARIFIED: it was a SWAP — S-0808 unplugged, S-1608 alone (0 S-0808 frames in 8s on the wire). CLEANEST form of the test: S-1608 alone, WHOLE address space free, still base 32. Operator now switching 48V on S-1608 ch1 = the physical anchor for 0x20.
00:10:41.653  OPERATOR: touched ALL THREE params on S-1608 ch1 (phantom+pad+sens). THE ANCHOR: prediction on record = CH 0x20.
00:11:31.276  ANCHOR CLOSED: S-1608 ch1 == CH 0x20. Predicted BEFORE the test. All 26 operator edges on 0x20 only; phantom+pad+SENS all present; 0x7e invariant holds; SENS ramp 0x36..0x31 = -64..-59 dBu (1 dB/step). The WHOLE head-amp decode transfers to a different box model — only the BASE differs. CH = model_base + (channel-1).
00:12:37.702  OPERATOR: testing S-1608 ch16. PREDICTION ON RECORD: CH=0x2f (47). Two anchors define the line: ch1=0x20 proves the base, ch16 proves linear+contiguous (vs reversed / stride-2 / lookup).
00:14:46.199  OPERATOR: console ch2 is PATCHED to box ch16; touched all 3 params on console ch2. DECISIVE: does CH address the BOX input (=0x2f) or the CONSOLE strip (=0x21)? Prediction on record: 0x2f.
00:15:32.182  DECISIVE: console ch2 patched to box ch16 -> CH=0x2f (=base32+15 = BOX INPUT 16), 11/11 edges, ZERO on 0x21. CH addresses the BOX'S PHYSICAL INPUT, not the console strip. The patch never reaches the wire. Two anchors (ch1=0x20, ch16=0x2f) => linear+contiguous. CORRECTS my earlier label: 0x22/0x24 were BOX inputs 3/5, NOT console channels 3/5.
00:21:43.457  OPERATOR: full SENS sweep min->max AND max->min, WITH and WITHOUT pad. Closes the last derived-not-measured gap (pad-ON endpoints). PREDICTION: VALUE byte spans identical 0x00..0x37 in BOTH pad states (box applies the offset).
00:23:50.341  CLOSED: operator display confirms pad-ON endpoints = +10 (VALUE 0x00) and -45 (VALUE 0x37); flipping pad at max sens reads -45 <-> -65 (exactly +20 AT THE ENDPOINT). SENS law now anchored at 4 endpoints + 2 midpoints, both pad states, 2 box models. NOTHING derived remains in the head-amp record.
00:26:57.972  === FAKE BOX EXPERIMENT === S-1608 unplugged; M-200 alone. Starting reac-pw --role slave on enp131s0 (PCI = the real REAC segment; the USB NIC is only the mirror tap). Our box presents 16ch (REAC_SLAVE_BOX_CHANNELS_DEFAULT, compile-time) and does NOT send a TAG 0500 identity. PREDICTION: M-200 addresses us at base 0, NOT 32 — base should come from the identity declaration, not width.
00:28:48.473  MY ERROR: ran reac-pw under sudo -> root has no route to pau's PipeWire -> 'failed to create reac:capture node'. The binary was ALREADY setcap cap_net_raw,cap_sys_nice. I then clobbered caps with setcap and DROPPED cap_sys_nice (RT prio for the pacer); restored. Rerunning as pau, no sudo. Operator note: 48kHz max.
00:35:09.354  FAKE BOX (take 3): reac-pw --role slave as pau, setcap intact, unbuffered to a log. box_channels default = 16 (S-1608-shaped). Operator to read sync status on the M-200 itself.
01:05:11.776  FAKE-BOX HEAD-AMP RX TEST: reac-pw slave ESTABLISHED to M-200 (updated origin/main binary). Operator about to toggle 48V/SENS/PAD on the M-200 for OUR box's channels. CAUSAL Q: what CH base does the M-200 assign a reac-pw 16ch box — 0x20 (S-1608-like) or 0x00? Validates the head-amp PARSER being built. Tap on USB NIC.
01:07:22.975  OPERATOR: sent 48V/SENS/PAD to our box from the M-200. Reading the tail.
01:13:39.263  DEBUG stagebox impl: capturing ALL cdea/0403 (grant+headamp+identity) 100s while operator sends 48V/SENS/PAD on M-200. Q: does our established box RECEIVE head-amp (TAG 0101 param 00/01/02)?
01:36:48.446  TEST A.1 CONFIRMED: PHY bounce (enp131s0 down/up) -> box re-establishes FLOOD->COLDCONNECT->TX_MUTE->ESTABLISHED on merged main binary. M-200 stale link-check was the cause; bounce clears it.
