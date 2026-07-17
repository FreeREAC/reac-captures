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
