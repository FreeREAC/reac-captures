# A box that boots while reac-pw is a slave on its segment does not enrol — why

Captures: `box-boot-with-our-slave-present-12h03-12h06.pcap` (the failure, VLAN 12, 802.1Q kept,
snaplen 512, 1 099 400 REAC frames) and `/home2/pau/reac-captures-run2/m200-441k-headamp-ch16.pcap`
(the control: the same desk, the same box, a cable bounce with our slave absent, 1 098 822 frames).
Peers: M-200 `00:40:ab:c9:cc:03` (desk, master, 44.1 k), S-1608 `00:40:ab:c4:80:3b`,
reac-pw slave `34:5a:60:9f:9e:be` — the NIC's own MAC, **not** the Roland-OUI stand-in
`00:40:ab:9f:9e:be` the daemon is supposed to announce from; worth a separate look.

Frames are classified exactly as `spec/reac.ksy`'s `ctrl_kind` does it (type word at payload[2:4];
link payload[4], segment payload[5], subtype payload[8]; DT1 model/command/tag at payload[18],[19],
[20:22]). The appendix carries the scanner.

## 1. The decisive window, per source

| time | desk (00:40:ab:c9:cc:03) | S-1608 (…c4:80:3b) | our slave (34:5a:60:…) |
|---|---|---|---|
| 12:03:30–12:03:43 | filler bcast 3673/s, `cfea` 1/s, `master_hb` ~0.5/s | unicast upstream 3674/s + `box_hb` 1/s (enrolled) | unicast upstream to the desk 3672/s + `box_hb` + config-announce + JOIN, ~every 1.74 s |
| **12:03:43.481** | unchanged | **last frame — reboot** | unchanged |
| 12:03:43 → 12:05:04 (80.7 s) | **unchanged**: 84 `cfea`, 48 `master_hb`, **0 scene transfers**, 0 frames addressed to anyone but broadcast | **nothing at all** — not one frame of any ethertype on VLAN 12 | ~300 000 frames, 47 more config-announce/JOIN/BOX_READY rounds, **never granted** |
| 12:05:04.142 | desk rebooted (operator) — silent to 12:05:09.874 | silent | still streaming; goes broadcast at 12:05:07, **last frame 12:05:12.262** (link down) |
| 12:05:09.876 | **scene transfer starts**, `cfea` now `28 08 02 0000` | — | gone |
| 12:05:13.653 | scene transfer continues | **presence flood (broadcast)** | — |
| 12:05:15.138 | — | config-announce `82`, JOIN `0100`, BOX_READY `0302`, heartbeat, unicast | — |
| 12:05:16.85 | echoes `0100`, `0000` head-mark, 6 × `0500`, then the 48-record head-amp sweep | granted, upstream carries audio | — |

Answers to the brief's question 1: **the box never sends a JOIN** in the whole 90 s it is away
(12:03:43.481 → 12:05:13.653); it sends nothing at all. **The desk never grants it** because it is
never asked. **The desk never grants us either** — 54 JOIN (`0100`) records from our slave, zero
echoes; the desk's only record frame before its own reboot is a single `0000` head-mark at
12:05:01.964 (payload `…0000 0300 0101`, a shape neither the box's `…0001` nor the desk's grant
`…0000` — unexplained, one frame, 3 s before the operator rebooted the desk).

## 2. The control: the same desk, the same box, no slave

| | failure (slave present) | control (slave absent) |
|---|---|---|
| box's last frame | 12:03:43.481 | 12:08:01.635 |
| desk's `cfea` announce | `…28 **10** 02 **0001**` unchanged for the whole 80.7 s (84 frames) | flips at **12:08:08.783 (+7.148 s)** to `…28 **08** 02 0001`, then `…0000` at +8.15 s |
| desk scene transfer | **0 frames in 80.7 s** | **4 116 frames**, first at 12:08:08.791, repeating ~2.7 s for 31 s |
| box returns | 12:05:13.653, only after the desk rebooted AND we left | 12:08:39.527, 10 s after replug |
| granted | 12:05:16.85 | 12:08:42.0 |

That `cfea` field is the enrolment slot itself: slot total `0x28`, enrolled width `0x10` (16, the
S-1608) → `0x08`, enrolled-box count `0x0001` → `0x0000` (reac.ksy `cfea_payload`). So in the
control the desk **declares the session over 7.1 s after its box goes quiet and immediately starts
courting**; in the failure it never declares anything and never courts.

The absence of scene transfers is a real absence, not a broken detector: the same scanner, in the
same file, counts 680 scene-transfer frames after 12:05:09.876 and 4 116 in the control.

## 3. The mechanism

**The M-200 keeps exactly ONE box session per segment, and its liveness test is fed by any upstream
stream of the enrolled geometry, regardless of source MAC. reac-pw's slave, ungranted, streams
exactly that — so the desk never notices its box has gone, never runs the enrolment ritual, and the
booting S-1608 has nothing to join.**

What the bytes support:

- **We are a byte-for-byte impersonation of the S-1608.** Our upstream frames are 634/632 B — the
  16-channel box geometry (`52 + 16*36`), identical to the box's. Our config-announce control block
  is *character-for-character* the box's:
  `010300108200000202020202010103030303030300000000000000000000004c` (port table `02 02 02 02 01 01`
  = a 16-input box, reac.ksy). Our `box_hb` block is identical too
  (`010300018100…7a`), and our BOX_READY `0302` is identical. Only the JOIN differs, in one payload
  byte (ours `…0100 0600 01`, the box's `…0100 0600 05` / `0d`) and its DT1 checksum.
- **We stream ungranted, forever.** ~300 000 unicast frames to the desk across the 90 s gap, at the
  box's own rate, with no grant at any point. `reac_fsm.h` says so in its own words: FSM_COLDCONNECT
  retries "until the master's grant lands (**no hard give-up while PHY stays up**)", emitting
  "unicast audio between".
- **The desk's own announce says the slot stayed taken**: width `0x10`, enrolled `0x0001`, for 84
  consecutive announces over 80.7 s of a box that was not there.

What the bytes refute:

- *"Our cold-connect flood collides with the box's."* No. Every frame we sent after the initial
  flood was **unicast to the desk's MAC**; on a switched segment the box never saw one of them. The
  box's silence must follow from what the **desk broadcast**, and the only two things that differ
  there are the missing scene transfer and the held `cfea` slot.
- *"The desk grants by first-come and the box gives up."* No. The desk granted nobody: it ignored
  all 54 of our JOINs, and the box never joined to be refused.
- *"Switch-port timing (STP) kept the box's JOIN off the wire."* Already ruled out by the operator's
  12:08 bounce on the same port (timeline §12:09:15); and the box was silent for 90 s, not for a
  listening interval.

Not settled by these captures:

- **Whether the desk's liveness test keys on the geometry or merely on frames arriving.** Both
  readings predict every byte we have. It matters only for the second-order fix (announcing a
  distinct width); it does not change the first-order one.
- **Why the box stays mute.** Two candidates fit: it waits for the master's scene transfer /
  prepare-to-grant invitation, or it reads the `cfea` slot as taken and does not try. Both are
  consequences of the desk not declaring the session over, so the fix is the same either way. The
  timeline's 11:41–11:45 trial (box rebooted with our slave present, silent for ~100 s, then synched
  *instantly* on a direct desk↔box cable) says the box was booted and functional while mute, but it
  is a second link-up, so it is evidence, not proof.
- **The box's link state during the 90 s.** The capture is VLAN 12 only; an untagged or non-REAC
  frame from the box would not be in it (one IPv6 frame from our host and one corrupt `93ac` frame at
  12:05:13 did make it in, so the filter was not ethertype-limited).

## 4. The change: bound the ungranted courtship, then get off the wire

Prose: a real box is granted ~1.7 s after its presence flood ends. Ours courts forever. Since the
desk's session hold is **7.148 s** (measured above), a slave that has not been granted must stop
transmitting for **longer than that** before trying again, so that a box booting beside it always
gets a window in which the desk declares its session over and starts courting. The patch adds one
state to the pure FSM: `FSM_COLDCONNECT` gets a 4 s budget (≈2× a real box's grant latency); when it
runs out with no grant ever seen, the slave enters `FSM_BACKOFF` and emits **nothing** for 10 s,
then re-floods. Nothing else changes: a granted courtship goes through the existing `grant_ack`
window and never reaches the budget.

Measured offline, driving the patched FSM with 90 s of M-200 announces at 3675 fps and no grant —
the failure window exactly (`gcc -Iinclude harness.c src/reac_fsm.c`):

```
OLD (libreac 29b27d1): frames on the wire in 90 s: 330750 (100.0% duty)  longest silence: 0.000 s
NEW (patched):         frames on the wire in 90 s: 120959 ( 36.6% duty)  longest silence: 10.000 s
```

330 750 is the same order as the ~300 000 frames the wire actually carried from us in that window.
10.000 s > 7.148 s, so the desk must time its box out on every cycle.

The red-first arm belongs in `tests/test_link.c`: drive `FSM_EV_RX` with `REAC_CTRL_MASTER_ANNOUNCE`
and no grant for 90 s of frames and assert `FSM_ACT_STOP` for at least `hold+1` consecutive steps —
it fails on HEAD (the action is never anything but `FSM_ACT_UNICAST_COLDCONNECT`) and passes with the
patch. Rejected alternative: dropping only the filler between join retries. The joins alone still
arrive every 1.74 s, which is inside the desk's 7.1 s hold, so it would not free the slot — and that
it would not is *predicted*, not measured, which is why the honest fix is silence.

Not committed anywhere; it applies clean to libreac `29b27d1` (`git apply --check -p1`).

```diff
--- a/include/reac/reac_fsm.h
+++ b/include/reac/reac_fsm.h
@@ -68,6 +68,23 @@
  * all 8 escalation phases (incl. 0016 + 001a) re-emit regardless of alignment. */
 #define REAC_FSM_GRANT_ACK_FRAMES  7200   /* 9 x JOIN_RETRY_PERIOD */
 
+/* THE UNGRANTED COURTSHIP IS BOUNDED (2026-09-11, m200-master-441k capture).
+ * FSM_COLDCONNECT used to retry forever while the PHY stayed up, streaming
+ * unicast FILLER to the master at wire rate between the join retries. Measured
+ * against a live M-200 at 44.1 k: an ungranted slave doing that for 93 s held
+ * the desk's ONE box session open - the desk's cfea kept announcing width 0x10 /
+ * enrolled 0x0001 for the whole 80.7 s the real S-1608 was away, and it emitted
+ * ZERO scene transfers, so the rebooting box never enrolled. With the slave
+ * absent the same desk declared the session over 7.148 s after the box's last
+ * frame (cfea -> 0x08 / 0x0000) and scene-transferred every ~2.7 s until the box
+ * joined. So an ungranted slave must GO SILENT for longer than that hold: court
+ * for COLDCONNECT_BUDGET_S, then emit NOTHING for BACKOFF_S, then re-flood.
+ * Seconds, not frames, because both bounds are wall-clock facts about the
+ * master; the step count is derived from the rate (heartbeat_period = fps).
+ * A real box is granted ~1.7 s after its flood stops, so 4 s is ~2x generous. */
+#define REAC_FSM_COLDCONNECT_BUDGET_S 4
+#define REAC_FSM_BACKOFF_S           10
+
 enum reac_fsm_state {
 	FSM_PHY_DOWN = 0,
 	FSM_FLOOD_ANNOUNCE,   /* hunting: BOUNDED broadcast FILLER flood, learn master */
@@ -75,6 +92,7 @@
 	FSM_TX_MUTE,          /* grant accepted, settle dwell */
 	FSM_ESTABLISHED,      /* linked: unicast audio + heartbeat */
 	FSM_DROP,             /* link lost / torn down */
+	FSM_BACKOFF,          /* courted, never granted: off the wire so a real box can join */
 };
 
 enum reac_fsm_action {
@@ -115,6 +133,8 @@
 	int      join_retry_countdown;  /* steps until the next cold-connect on the grid */
 	int      grant_ack;             /* >0: post-grant ACK window (frames left) — keep
 	                                 * cold-connecting so 0016/001a re-emit, then mute */
+	int      coldconnect_frames;    /* frames spent courting since the flood ended */
+	int      backoff;               /* >0: frames left off the wire before re-flooding */
 };
 
 struct reac_fsm_out {
--- a/src/reac_fsm.c
+++ b/src/reac_fsm.c
@@ -20,6 +20,13 @@
 	return fsm->heartbeat_period > 0 ? fsm->heartbeat_period : HEARTBEAT_PERIOD;
 }
 
+/* Frame periods in one wall-clock second: the heartbeat period IS fps (see the
+ * field's doc), so every wall-clock bound below scales with the wire rate. */
+static inline int frames_per_s(const struct reac_fsm *fsm)
+{
+	return hb_period(fsm);
+}
+
 static int is_master_frame(const struct reac_ctrl_parsed *rx)
 {
 	/* HEADAMP is master EVIDENCE (only a console emits preamp records) but it
@@ -61,6 +68,7 @@
 static void arm_coldconnect(struct reac_fsm *fsm)
 {
 	fsm->join_retry_countdown = 0;
+	fsm->coldconnect_frames = 0;   /* fresh courtship: fresh ungranted budget */
 }
 
 /* One FLOOD_ANNOUNCE tick: emit ONE broadcast FILLER frame (no cold-connect
@@ -81,6 +89,7 @@
 static struct reac_fsm_out coldconnect_tick(struct reac_fsm *fsm)
 {
 	fsm->counter++;
+	fsm->coldconnect_frames++;
 	if (--fsm->join_retry_countdown <= 0) {
 		fsm->emit_join = 1;
 		fsm->join_retry_countdown = REAC_FSM_JOIN_RETRY_PERIOD;
@@ -156,9 +165,29 @@
 			fsm->link_check = REAC_FSM_LINKCHECK_RELOAD;
 			return out(fsm, FSM_ACT_SILENCE);
 		}
+		/* NEVER GRANTED, BUDGET SPENT -> off the wire. A master keeps exactly one
+		 * box session and its liveness is fed by our upstream stream, so courting
+		 * forever locks a booting box out (see reac_fsm.h). Only when no grant has
+		 * been seen at all: a granted courtship is inside the grant_ack window. */
+		if (fsm->grant_ack == 0 &&
+		    fsm->coldconnect_frames >= REAC_FSM_COLDCONNECT_BUDGET_S * frames_per_s(fsm)) {
+			fsm->state = FSM_BACKOFF;
+			fsm->backoff = REAC_FSM_BACKOFF_S * frames_per_s(fsm);
+			return out(fsm, FSM_ACT_STOP);
+		}
 		/* tick or non-grant RX: unicast cold-connect on the grid, audio between */
 		return coldconnect_tick(fsm);
 
+	case FSM_BACKOFF:
+		/* The silent window. Nothing is emitted and the counter does not advance -
+		 * we are not on the wire - so the master's session hold expires and it
+		 * starts courting whatever real box is booting. Then try again. */
+		if (--fsm->backoff <= 0) {
+			arm_flood(fsm);
+			return flood_tick(fsm);
+		}
+		return out(fsm, FSM_ACT_STOP);
+
 	case FSM_TX_MUTE:
 		/* Frame-arrival IS the box's clock (it recovers word clock from the
 		 * master's inter-arrival interval), so a received master frame
--- a/transport/src/reac_slave.c
+++ b/transport/src/reac_slave.c
@@ -841,7 +841,8 @@
 	uint8_t rxbuf[2048];
 
 	static const char *const st_name[] = {
-		"PHY_DOWN", "FLOOD_ANNOUNCE", "COLDCONNECT", "TX_MUTE", "ESTABLISHED", "DROP"
+		"PHY_DOWN", "FLOOD_ANNOUNCE", "COLDCONNECT", "TX_MUTE", "ESTABLISHED", "DROP",
+		"BACKOFF"
 	};
 	enum reac_fsm_state prev_state = s->fsm.state;
 	fprintf(stderr, "reac_slave: %sSTATE %s\n", s->tag, st_name[prev_state]);
```

Second-order, **guessed not proven**, do not ship without a trial: announce a width/port table that
is not the S-1608's, so a desk that keys its liveness on geometry can tell us apart. Refuted as
*sufficient* on its own — the first-order defect is that we transmit at all while ungranted.

Operational rule until the patch lands (unchanged from the timeline): the box enrols first, our
slave joins after; a venue box power-cycle must not find us on its VLAN.

## Appendix — the scanner

```python
import struct, sys, collections, time
def frames(path):
    f=open(path,'rb'); hdr=f.read(24)
    magic=struct.unpack('<I',hdr[:4])[0]
    endian='<' if magic in (0xA1B2C3D4,0xA1B23C4D) else '>'
    if endian=='>': magic=struct.unpack('>I',hdr[:4])[0]
    div=1_000_000_000 if magic==0xA1B23C4D else 1_000_000
    pkt=struct.Struct(endian+'IIII')
    while True:
        ph=f.read(16)
        if len(ph)<16: break
        sec,frac,incl,orig=pkt.unpack(ph); raw=f.read(incl)
        if len(raw)<incl: break
        et=raw[12:14]
        if et==b'\x81\x00':
            if raw[16:18]!=b'\x88\x19': continue
            vlan=int.from_bytes(raw[14:16],'big')&0xfff; p=raw[18:]
        elif et==b'\x88\x19': vlan=None; p=raw[14:]
        else: continue
        yield sec+frac/div, raw[0:6], raw[6:12], vlan, p, orig
def mac(b): return ':'.join('%02x'%x for x in b)
def classify(p):                       # spec/reac.ksy ctrl_kind, verbatim
    tw=int.from_bytes(p[2:4],'big')
    if tw==0x0000: return 'filler',None
    if tw==0xcfea: return 'master_announce',None
    if tw!=0xcdea: return 'unknown_tw_%04x'%tw,None
    link,seg,op=p[4],p[5],p[8]
    if link==2: return 'link2',None
    if link==4:
        if (seg&3)!=3: return 'record_fragment',None
        tag=int.from_bytes(p[20:22],'big')
        if p[18]==0x12 and p[19]==0x12 and tag==0x0101: return 'head_amp',None
        return 'grant','tag%04x'%tag
    if link!=1: return 'unknown_link_%d'%link,None
    return ({0x00:'scene_transfer',0x01:'master_hb',0x81:'box_hb',0x10:'group_map'}.get(op)
            or ('config_announce' if op in (0x80,0x82,0x83,0x84) else 'unknown_op_%02x'%op),
            'sel%02x'%op if op in (0x80,0x82,0x83,0x84) else None)
# per-second census: collections.Counter over (int(ts), src, dst, kind); the cfea slot is
# p[4:36] on a master_announce — bytes 15,16,17,18:20 are slot total, width, pace code,
# enrolled-box count.
```
