# analysis/ — corpus-wide extractors

Streaming analyzers that read the whole capture corpus without ever loading a
pcap into memory. Everything here is derived data: delete it and re-run.

| file | what it is |
|---|---|
| `reac_pcap.py` | streaming classic-pcap reader (4 MB chunks, all four magics) + the REAC control decoder — frame coordinates, `cdea`/`cfea` dispatch, the Roland-DT1 container rule (wrapper `00 02 00 fe` + SysEx `f0 41 0a 00 00`, never the `04 03` opcode alone) |
| `placement_scan.py` | one JSON row per capture: desk + box identity, declared width, ENROLL group map (`0103 000d`), chanmap (`0103 0019`), cfea fields, box config-announce (`0103 0010`), cold-connect identity records, upstream audio width, and the grant sweep's group-A base/span |
| `make_table.py` | condenses the rows into `placement_table.csv` + the human table |
| `placement_rows.jsonl` | 82 rows, generated 2026-07-28 |
| `placement_table.csv` | the condensed evidence table |

```
./placement_scan.py            # whole corpus -> placement_rows.jsonl
./make_table.py                # -> placement_table.csv
```

The placement study built on this is `reac-pw/docs/PLACEMENT-EVIDENCE.md`
(FreeREAC/reac-pw#63): 42 of the 82 captures carry a grant sweep, and they show the
box's fabric base is a deterministic function of what the box DECLARES at
cold-connect — not of the desk, the MAC, the enrolment order, the ENROLL map or the
chanmap.

Field offsets worth keeping (all relative to the `cdea`/`cfea` byte at frame offset 16):

- **cfea announce** — `[17]` audio fabric total (`0x28` = 40), `[18]` box input width,
  `[19]` console generation (0 V-Mixer / 1 OHRCA), `[20:22]` enrolled-box count BE.
- **box config-announce `0103 0010`** — `[6]` selector (`0x82` S-1608, `0x84`
  S-0808/S-4000S), `[9]` a one-byte field (`0x02` S-1608, `0x00` the others),
  `[10:22]` twelve 4-channel cells: `0x02` analog input, `0x01` output, `0x03` absent.
- **ENROLL group map `0103 000d`** — `[8]` console generation, `[9:14]` input region
  (`width/8` bytes of `0x41`, front-packed), `[14:19]` output region (the rest as
  `0xc3`, back-packed).
- **chanmap `0103 0019`** — `[6]` payload type, then 8 x 3-byte slot records at `[7]`.
