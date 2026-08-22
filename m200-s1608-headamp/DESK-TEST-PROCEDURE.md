# The deciding test: a real Roland desk on THIS S-1608

Two questions are waiting on one cabling session. Both need a real desk (M-200 / M-300 /
M-5000) and neither can be answered from our side — everything reachable without a desk has
been measured.

Box under test: **S-1608 `00:40:ab:c4:80:41`** (the rig's own unit — not `c4:80:3b`, which
is the corpus's other S-1608).

---

## Question 1 — is the head-amp gate the UNIT, or us?

**State of the evidence, 2026-08-22.** Same console, same code path, same night:

| box | requested | measured on the wire |
|---|---|---|
| S-0808 `c4:dc:9c` | +20 dB | **+20.2 dB** |
| S-1608 `c4:80:41` | +44 dB | **0.2 dB** |

`box_headamp_verdict.sh` says HEALTHY 8/8 for the S-0808 and **GATED 0/16** for the S-1608,
every delta inside ±0.8 dB of noise. Every REST PATCH returned `ok:true`. The wire records
are byte-identical to what an M-200, M-300 and M-5000 each write. So our side is exonerated
as far as anything here can exonerate it.

The leading explanation is a **boot-sampled hardware gate**: `FUN_0c00f6b4()` ∈ {0,1} guards
both the head-amp hardware path (`FUN_0c007e06`:8654) and the only sender of the apply
command (`FUN_0c00cb14`:11985); it is decoded ONCE at boot by `FUN_0c01091a`:15843 from two
I/O-expander bits (`b = bit1<<1|bit0`; `b==1`→0, `b==2`→1, else **2/3 = DISABLED**) and
deliberately never re-sampled. That is an inference from a decompile, and it is the last
thing standing between "send the unit for service" and "we are missing something".

**The test.** Cable the desk to the S-1608 directly. From the desk's own surface, set 48 V
and a gain change on any input.

- **The desk CAN set 48 V** → the box is fine and OUR MASTER is missing something. Capture it
  (below) — that capture is the answer.
- **The desk CANNOT set 48 V** → the unit is faulty. It goes for service, and every hour
  spent on the protocol from here is wasted.

Note a real M-200 already failed to bring this unit's upper slots up
(`m200-anchor-openwindow-20260721-221150`), which points the same way — but that capture was
about the upper bank, not about 48 V on a gated box, so it does not settle this.

---

## Question 2 — where does the REAC PACE ride? (settles the 96 kHz default)

**Why it cannot be answered without a desk.** A real stagebox follows the master's pace
symmetrically (4000 pps at 48 k, 8000 at 96 k — measured, `PACE-IS-NOT-FOLLOWED-2026-08-22.md`).
Ours does not: our downstream is byte- and cadence-identical to a real 96 kHz desk
(1492-byte frames, 125.1 µs mean) and both boxes answer 4000 pps. The pace is announced
somewhere we are not setting, and **the corpus cannot say where, because family and rate are
perfectly confounded in it**: all 30 M-200 captures are 48 k, all 10 M-5000 captures are 96 k.
Nothing separates "OHRCA chatter" from "the rate field".

**The test.** One desk, one box, one cable, **capturing continuously across a rate change in
the desk's REAC menu**. Everything else held constant is what makes it decisive — the diff
across the switch can only be the pace.

```
sudo tcpdump -Z root -i <nic> -w reac-captures/captures/<desk>-s1608-RATESWITCH-48k-to-96k-2026-08-XX.pcap \
     ether proto 0x8819
```

Start the capture, leave the segment established at 48 k for ~30 s, switch the desk's REAC
menu to 96 k, leave it ~30 s, stop. Then:

```
analysis/pps_by_mac.py <pcap> 20            # confirms both ends actually changed pace
analysis/rate_field_hunt.py <pcap> <desk> <pcap> <desk>   # the control-plane diff
```

If the desk is a V-Mixer (M-200/M-300) its menu may offer only 48 k. Then the same capture
from an **M-5000 switched 48 k ↔ 96 k** answers it, and additionally breaks the
family/rate confound in the corpus for good.

---

## Bring-up checklist (so the session is not wasted)

1. `pgrep -ax reac-pw` and **kill every master** first. Two masters on one segment source the
   same real MAC, discard each other as own-echo, and the box goes mute — ~40 min lost to this
   once. One master, or none.
2. Capture with `-Z root`; tcpdump otherwise drops privileges and cannot write the file, and
   an empty capture reads exactly like a silent segment.
3. Filter to control frames when hunting the control plane — `ether[16:2] != 0` — so the
   frame budget is not spent on audio.
4. `-c N` is not a time window. At 8000 fps, `-c 4000` is half a second.
5. An unclaimed REAC box transmits NOTHING. Use `/sys/class/net/<nic>/carrier` as the
   master-independent power detector, never the absence of frames.
6. Note whether the tap is mirrored. A mirrored capture doubles the DESK's frames but not the
   box's, and halving both reads a 96 kHz box as 48 kHz.
7. A desk MAC is not proof of a real desk — reac-pw impersonated `c9:cc:03` in July 2026.
   Name the capture from what is IN it.
