#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Pau Aliagas <linuxnow@gmail.com>
"""Is the REAC capture stream LABELLED with the rate it is actually carrying?

The problem this answers: reac-pw declares its PipeWire node at the CONFIGURED pace
(--rate), but a box that has not followed to that pace keeps delivering at its own. A node
declaring 96 kHz over 48 kHz audio produces no xrun and no error -- PipeWire simply
believes the label -- so every soft indicator reads healthy while everything from that box
plays an octave low. `applied:true` proves the row ran, not that the audio is right.

THE ORACLE IS MAINS HUM. A live condenser in a European room picks up 50 Hz and its
harmonics. Mains frequency is a physical constant we do not control, so it is a free
reference tone that is always present: if the stream is mislabelled by 2x, the hum peak
lands at 25 Hz instead of 50. No signal generator and no physical access required.

This is a RATIO test, which is what makes it survive a quiet desk: it asks where a peak
sits, not how loud it is. An absolute level would prove nothing on a muted channel.

Reads WAVE_FORMAT_EXTENSIBLE float32, which Python's `wave` module refuses.

Usage: hum_rate_check.py <wav> [channel-1-based] [expected-mains-hz]
"""

import struct
import sys

import numpy as np


def read_wav_f32(path):
    d = open(path, "rb").read()
    if d[:4] != b"RIFF" or d[8:12] != b"WAVE":
        raise SystemExit(f"{path}: not a RIFF/WAVE file")
    off = 12
    fmt = None
    while off + 8 <= len(d):
        cid = d[off:off + 4]
        size = struct.unpack("<I", d[off + 4:off + 8])[0]
        body = d[off + 8:off + 8 + size]
        if cid == b"fmt ":
            tag, nch, sr, _br, _ba, bits = struct.unpack("<HHIIHH", body[:16])
            fmt = (tag, nch, sr, bits)
        elif cid == b"data":
            if fmt is None:
                raise SystemExit("data chunk before fmt chunk")
            _tag, nch, sr, bits = fmt
            if bits != 32:
                raise SystemExit(f"expected 32-bit float samples, got {bits}-bit")
            a = np.frombuffer(body[:len(body) - (len(body) % (4 * nch))], dtype="<f4")
            return a.reshape(-1, nch), sr
        off += 8 + size + (size & 1)
    raise SystemExit("no data chunk")


def main():
    path = sys.argv[1]
    ch = int(sys.argv[2]) if len(sys.argv) > 2 else None
    mains = float(sys.argv[3]) if len(sys.argv) > 3 else 50.0

    data, sr = read_wav_f32(path)
    n, nch = data.shape
    print(f"# {path.rsplit('/', 1)[-1]}: {nch} ch, {sr} Hz, {n / sr:.2f} s")

    rms = 20 * np.log10(np.sqrt((data ** 2).mean(axis=0)) + 1e-12)
    for c in range(nch):
        print(f"   ch{c + 1}: {rms[c]:7.1f} dBFS")

    # Pick the loudest channel when none is named -- the hum reference has to be a channel
    # that actually carries a preamp's output, not a dead slot.
    idx = (ch - 1) if ch else int(np.argmax(rms))
    print(f"\n# hum analysis on ch{idx + 1} ({rms[idx]:.1f} dBFS)")
    if rms[idx] < -80:
        print("   channel is at the noise floor -- no hum to find, verdict UNAVAILABLE")
        return 1

    x = data[:, idx].astype(np.float64)
    x = x[len(x) // 4: len(x) // 4 + (1 << 18)] if n > (1 << 19) else x
    x = x - x.mean()
    w = np.hanning(len(x))
    spec = np.abs(np.fft.rfft(x * w))
    freqs = np.fft.rfftfreq(len(x), 1.0 / sr)

    def peak_near(f0, tol=0.25):
        lo, hi = f0 * (1 - tol), f0 * (1 + tol)
        m = (freqs >= lo) & (freqs <= hi)
        if not m.any():
            return None, 0.0
        sub = spec[m]
        return float(freqs[m][int(np.argmax(sub))]), float(sub.max())

    # Compare the two candidate homes for the mains line: where it belongs, and where it
    # would land if the stream were labelled at twice the rate it carries.
    f_true, a_true = peak_near(mains)
    f_half, a_half = peak_near(mains / 2)
    floor = float(np.median(spec))
    print(f"   peak near {mains:.0f} Hz : {f_true:6.2f} Hz  {20 * np.log10(a_true / floor):6.1f} dB over median")
    print(f"   peak near {mains / 2:.0f} Hz : {f_half:6.2f} Hz  {20 * np.log10(a_half / floor):6.1f} dB over median")
    if a_true >= a_half:
        print(f"   VERDICT: hum sits at ~{mains:.0f} Hz -> stream rate label is CONSISTENT")
    else:
        print(f"   VERDICT: hum sits at ~{mains / 2:.0f} Hz -> stream is labelled 2x its "
              f"true rate (an octave low)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
