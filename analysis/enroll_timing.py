#!/usr/bin/env python3
"""WHEN does a desk send its ENROLL — before or after the box declares itself?

reac-pw emits a wide-safe ENROLL at GRANTING tick 0, before it knows what the box
is, and a second one once the declaration lands. reac_master.c claims the golden
"sends its enrol ~200ms into the session, after reading the box config". This
checks that claim against the captures, per capture, in wall-clock order.

Usage: enroll_timing.py <pcap> [<pcap> ...]
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import reac_pcap as R

STOP_AFTER = 400_000     # frames; every establishment in the corpus fits well inside


def scan(path):
    t0 = None
    events = []          # (dt, label)
    seen_cfg = 0
    for i, (ts, wl, fr) in enumerate(R.iter_packets(path)):
        if i > STOP_AFTER:
            break
        if not R.is_reac(fr):
            continue
        if t0 is None:
            t0 = ts
        ct = R.control(fr)
        if ct is None:
            continue
        kind, op, oplen = ct
        if op == b'\x01\x03' and oplen == 0x000d:
            events.append((ts - t0, 'DESK ENROLL      cdea 0103 000d'))
        elif op == b'\x01\x03' and oplen == 0x0010:
            seen_cfg += 1
            events.append((ts - t0, f'BOX  CONFIG      cdea 0103 0010  #{seen_cfg}'))
        elif op == b'\x04\x03' and oplen in (0x0016, 0x001a):
            events.append((ts - t0, f'BOX  JOIN        cdea 0403 {oplen:04x}'))
        if len(events) >= 14:
            break
    return events


for p in sys.argv[1:]:
    print(f'\n=== {os.path.basename(p)} ===')
    ev = scan(p)
    if not ev:
        print('  (no establishment events in the scanned window)')
    for dt, label in ev:
        print(f'  t+{dt:8.3f}s  {label}')
