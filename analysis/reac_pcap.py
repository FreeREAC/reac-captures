#!/usr/bin/env python3
"""Streaming pcap/pcapng reader + REAC control-frame decoder.

Never loads a whole capture: reads fixed-size chunks and yields one packet at a
time. The 19 GB corpus is processed in bounded memory.

Frame coordinates used throughout (offset from the first byte of the Ethernet
frame), verified against reac-pw's own emitters (src/reac_master.c gen_cfea,
src/reac_grant.c GRANT_HEAD_ACK):

    [0:6]   dst MAC
    [6:12]  src MAC
    [12:14] ethertype 0x8819
    [14:16] (2 bytes, pre-control)
    [16:18] cd ea (master/box control) | cf ea (master announce)
    [18:20] op            e.g. 04 03 (grant/head-amp), 01 03 (chanmap/enroll)
    [20:22] oplen  BE
    [16:50] the 32-byte control block whose bytes sum to 0 (mod 256)
"""
import struct, sys

PCAP_MAGICS = {                            # keyed by the RAW first 4 bytes
    b'\xa1\xb2\xc3\xd4': ('>', 1_000_000),
    b'\xd4\xc3\xb2\xa1': ('<', 1_000_000),
    b'\xa1\xb2\x3c\x4d': ('>', 1_000_000_000),
    b'\x4d\x3c\xb2\xa1': ('<', 1_000_000_000),
}
CHUNK = 4 << 20


def iter_packets(path):
    """Yield (ts_float, wirelen, frame_bytes). Streaming, bounded memory."""
    with open(path, 'rb') as f:
        gh = f.read(24)
        if len(gh) < 24:
            return
        if gh[:4] not in PCAP_MAGICS:
            raise ValueError(f'{path}: not a classic pcap (magic {gh[:4].hex()})')
        endian, tsdiv = PCAP_MAGICS[gh[:4]]
        rh = struct.Struct(endian + 'IIII')
        buf = b''
        while True:
            blk = f.read(CHUNK)
            if not blk:
                break
            buf += blk
            i = 0
            n = len(buf)
            while True:
                if n - i < 16:
                    break
                ts_s, ts_f, caplen, wirelen = rh.unpack_from(buf, i)
                if caplen > 262144:
                    raise ValueError(f'{path}: caplen {caplen} at {i} — desync')
                if n - i - 16 < caplen:
                    break
                yield (ts_s + ts_f / tsdiv, wirelen, buf[i + 16:i + 16 + caplen])
                i += 16 + caplen
            buf = buf[i:]


def mac(b):
    return ':'.join(f'{x:02x}' for x in b)


WRAP = bytes([0x00, 0x02, 0x00, 0xfe])
SYS = bytes([0xf0, 0x41, 0x0a, 0x00, 0x00])


def is_reac(fr):
    return len(fr) >= 18 and fr[12:14] == b'\x88\x19'


def control(fr):
    """(tag, op, oplen) for a REAC control frame, else None.
    tag is 'cdea' or 'cfea'."""
    if len(fr) < 50:
        return None
    t = fr[16:18]
    if t == b'\xcd\xea':
        return ('cdea', fr[18:20], int.from_bytes(fr[20:22], 'big'))
    if t == b'\xcf\xea':
        return ('cfea', fr[18:20], int.from_bytes(fr[20:22], 'big'))
    return None


def dt1_record(fr):
    """Decode a cdea 04 03 Roland-DT1 control container.

    Returns dict(marker, tag, data, ok) or None if this is not a genuine
    container (the box-upstream audio braid also carries cd ea 04 03; the
    wrapper + SysEx envelope is the discriminator — corpus_protocol_conformance.py).
    """
    if len(fr) < 50 or fr[16:20] != b'\xcd\xea\x04\x03':
        return None
    if fr[22:26] != WRAP or fr[27:32] != SYS:
        return None
    oplen = int.from_bytes(fr[20:22], 'big')
    rec_len = oplen - 0x0d
    if rec_len < 2 or 34 + rec_len + 1 > len(fr):
        return None
    rec = fr[34:34 + rec_len]
    return {
        'marker': fr[32:34].hex(),
        'tag': rec[0:2].hex(),
        'data': rec[2:-1],
        'oplen': oplen,
        'inner_ok': (sum(rec) & 0xff) == 0x80,
        'f7': fr[34 + rec_len] == 0xf7,
    }
