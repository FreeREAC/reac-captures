# M-200 → S-1608 head-amp: independent confirmation (2026-07-17)

Live capture of a **real M-200** (`00:40:ab:c9:cc:03`) driving 48V / pad / SENS on a
**real S-1608** (`00:40:ab:c4:80:41`), operator toggling at the desk, LED as ground truth.
This is an INDEPENDENT re-confirmation of the 2026-07-16 decode — captured with a
different session, different console power-cycle, decoded with a fresh parser.

- Capture: `captures/m200-s1608-headamp-48v-pad-sens-2026-07-17.pcap` (control distillate)
- Decoder: `find_ha.py` (binary pcap parse; scans for the `cdea` marker, no fixed offset)

## Result: 82 head-amp records, every one at CH 0x20

| param | code | values captured | operator action |
| --- | --- | --- | --- |
| phantom | `0` | `0x01`, `0x00` | 48V on/off |
| pad | `1` | `0x01`, `0x00` | pad on/off |
| sens | `2` | `0x11`–`0x19`, `0x36` | SENS sweep, 1 dB/step |

## Byte-exact records

```
phantom on : cdea 0403 0013 000200fe 0ef0410a 0000 1212 0101 20 00 01 5d f7 ...02
pad on     : cdea 0403 0013 000200fe 0ef0410a 0000 1212 0101 20 01 01 5c f7 ...02
sens 0x36  : cdea 0403 0013 000200fe 0ef0410a 0000 1212 0101 20 02 36 26 f7 ...02
                                                  TAG  CH P  V  cks
```

## What this confirms (nothing needed revising)

- **TAG `01 01` = head-amp**, carried in the op `04 03` tagged-record container.
- **params `0/1/2` = phantom / pad / sens** — exactly the three the box owns.
- **CH = `0x20` for this S-1608** — the M-200's allocation, stable across sessions.
- **Inner record checksum sums to `0x80`**, verifiable by hand:
  `01+01+20+00+01+5d = 0x80` ✓  ·  `01+01+20+01+01+5c = 0x80` ✓  ·  `01+01+20+02+36+26 = 0x80` ✓
- reac-pw's own `reac_headamp` test still passes byte-exact against the M-200 reference,
  so **our builder produces the same bytes**.

## Method note (why this capture exists)

An afternoon of live head-amp tests produced repeated dark-LED results that were all
**instrument error, not protocol error** — probes trusted without validating them against
a known-good case. This capture is the antidote: a record set the LED proves is real, so
any decoder that finds nothing here is broken, and any of our frames can be diffed
against it byte-for-byte.

The rule this cost us a day to relearn: **validate the probe on known-good traffic before
trusting what it says about the unknown.**
