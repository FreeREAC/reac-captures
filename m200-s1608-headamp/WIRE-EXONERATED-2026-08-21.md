# The S-1608 upper bank: the wire is exonerated, and the swap fix would have been wrong

2026-08-21, evening. Follows `UPPER-BANK-ALIASING-2026-08-21.md`, which proved that on our
unit `CH 0x28..0x2f` land on physical ports 1..8.

The firmware lift (see below) suggested an attractive fix: if the box's two head-amp banks
are simply **swapped** relative to the CH numbering, reac-pw could emit box inputs 1..8 as
`CH 0x28+n` and 9..16 as `CH 0x20+n` and the defect would vanish with a one-line change.

**The corpus refutes that fix.** Do not ship it.

## What a real desk sends — measured, not assumed

Every desk-side artifact we emit is byte-identical to a real desk's.

**The addressed cells.** A real M-200i, M-300 and M-5000 each write exactly `CH 0x20..0x2f`
to an S-1608 — the same sixteen cells reac-pw writes (`analysis/headamp_cells.py`). There is
no cell a real desk uses that we do not.

**The container.** Masking the CH/PARAM/VALUE window and both checksums leaves ONE distinct
`op-0403` shape across all three desks and reac-pw:

```
04 03 00 13 00 02 00 fe 0e f0 41 0a 00 00 12 12
01 01 __ __ __ __ f7 00 00 00 00 00 00 00 00 00
```

So there is no bank selector hiding in the record. The desk distinguishes the two banks by
the CH byte and nothing else.

**The chanmap.** A real M-200 declares slots `0x00..0x27` populated (`28`) and `0x28..0x2f`
empty (`38`) — identically for an S-0808, an S-1608 and an S-4000S. The boundary does not
move with the box, so it is not about banks at all: `0x28` is 40, the tail of the M-200i's
40-channel stream. reac-pw declares the same.

That last point retro-justifies the refuted `REACPW_UPPER_IS_INPUT` experiment: declaring
`0x28..0x2f` as INPUT contradicts every real desk in the corpus, which is why the box then
converted nothing at all.

## The measurement that kills the swap

`captures/m200i-s1608-48k-mirror__m200-s1608-establish-switch-2026-07-11.pcap` — a real
M-200i driving a real S-1608 (`c4:80:3b`), 96 head-amp records and 92 889 audio fillers, from
before reac-pw ever impersonated a desk MAC.

SENS drives a preamp's idle noise floor by ~36 dB, so the desk's per-channel SENS values pair
against the box's own per-slot RMS. The desk set sixteen different values; the box reports
sixteen converting slots (`upstream_channels: 16`).

Pairing CH `0x20+n` -> slot `n+1` (identity):

| sens | slot RMS (dBFS) |
|---|---|
| 0 (x7) | −105.7 −105.9 −106.0 −106.0 −106.1 −106.2 −106.0 |
| 6 | −101.0 |
| 7, 7 | −100.4 −100.2 |
| 13, 13 | −100.8 −97.1 |
| 18 | −96.6 |
| 19, 19 | −95.4 −95.4 |
| 21 | −93.6 |

Monotone across all sixteen. The swapped pairing (`0x20+n` -> slot `9+n`) fails on its first
rows: it puts `sens=0` cells on slots reading −100, and lands two equal-SENS cells 9 dB apart.

**On a working S-1608 the mapping is identity, for all sixteen inputs.** There is no
numbering convention to compensate for. Our unit binding `CH 0x2f` to port 8 is a
mis-binding, not a dialect.

## Where that leaves the defect

The firmware lift (agent, same day) found the hardware apply to be

```
FUN_0c00ac1e(bank, slot & 7, value)      ; the mask, at 0c0084be
bank = (port == 1)                       ; a loop counter, never derived from the slot
slots = FUN_0c012162(port) * 8 .. +7     ; a PERMUTED port->group table on this model
```

Our measurement pins `FUN_0c012162(0) == 5` on our unit — bank 0 (ports 1..8) reads group 5
(`0x28..0x2f`). A working unit must have `FUN_0c012162(0) == 4` and `(1) == 5`. So the
permutation itself is built wrong on this box, and `FUN_0c012162` selects its table from
`FUN_0c00f6b4()` — a strap sampled once at boot from two I/O-expander bits and never re-read.

`m200-s1608-headamp/m200i-s1608-48k-mirror__m200-anchor-openwindow-20260721-221150.pcap` is a
real M-200 on OUR unit (`c4:80:41`) and its upper slots do not carry signal either, which
points the same way: the difference is the unit, not the master.

## Method notes worth keeping

- **A desk MAC is not proof of a real desk.** reac-pw impersonated `00:40:ab:c9:cc:03` from
  2026-07-21 onward, so several captures named `m200-...` on that date are US. Check the date
  against the impersonation window before calling a capture a golden. One capture here
  (`m200-s1608-establish-today-20260721-235750`) reads as a real M-200 by MAC and is reac-pw
  in the refusing state.
- **A chanmap slot count is a capture-window property.** The golden holds 14 chanmap frames
  and reac-pw's 26, so a naive union reports a difference in the declared table that is
  purely the shorter sweep. Count the frames before diffing the map.
- `analysis/headamp_cells.py` and `analysis/chanmap_diff.py` are new here and are what the
  above was measured with. `headamp_cells.py` was proven able to detect presence (27 captures
  carry records) before its silence on any capture was believed.
