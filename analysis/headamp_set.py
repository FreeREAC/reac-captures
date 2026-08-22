#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Pau Aliagas <linuxnow@gmail.com>
"""Write head-amp settings straight to a reac-pw playback node's SPA_PROP_params.

This is the BOX-facing probe: it bypasses the engine, the patch and the port map, so a
null answer accuses the box rather than eight layers above it. That also means it is not
a test of the console -- a value set here is invisible to omx, which is the documented
way to end up with a channel showing no 48 V while its preamp has it.

THE NODE IS SELECTED BY ITS PUBLISHED reac.headamp.base + reac.headamp.channels, NEVER BY
NAME. Two masters run on this rig and the names lie: after a physical cable swap the node
called "reac-playback" was the S-1608 and "reac-playback.s1608" was the S-0808. Every
declaration stayed right while every name went wrong. A name match once took the 8-channel
box for a CH 39 write, which fell outside its range and was silently dropped -- a false
null that reads exactly like a box refusing.

Channels are addressed as ABSOLUTE WIRE CHANNELS: base + (input - 1). The S-1608 grants
base 32 (0x20), so its input 8 is CH 39 (0x27) and its input 16 is CH 47 (0x2f).

Usage:
  headamp_set.py --base 32 --input 8 --set sens=20
  headamp_set.py --base 32 --all  --set phantom=1,pad=0,sens=44
  headamp_set.py --base 0  --input 1 --set sens=0
  headamp_set.py --list
"""

import argparse
import json
import subprocess
import sys

PARAMS = ("phantom", "pad", "sens")
RANGE = {"phantom": (0, 1), "pad": (0, 1), "sens": (0, 55)}


def pw_dump():
    out = subprocess.run(["pw-dump"], capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def reac_playback_nodes(objs):
    """Every reac-pw playback node that PUBLISHES a head-amp declaration.

    Requiring base+channels is what makes selection honest: a node without them cannot be
    addressed, so it is better excluded loudly than matched by a name that means nothing.
    An 'established' link-state wins over a probing twin under the same name -- a reac-pw
    restart can leave a placeholder pair behind, and writing to the zombie is another
    silent null.
    """
    found = []
    for o in objs:
        if o.get("type") != "PipeWire:Interface:Node":
            continue
        p = (o.get("info") or {}).get("props") or {}
        if "reac.headamp.base" not in p or "reac.headamp.channels" not in p:
            continue
        try:
            base = int(p["reac.headamp.base"])
            chans = int(p["reac.headamp.channels"])
        except (TypeError, ValueError):
            continue
        if chans <= 0:
            continue
        # A sink carries playback ports; the capture node publishes the same declaration.
        if p.get("media.class") != "Audio/Sink":
            continue
        found.append({
            "id": o["id"],
            "name": p.get("node.name"),
            "base": base,
            "channels": chans,
            "model": p.get("reac.box-model"),
            "caps": p.get("reac.headamp.caps"),
            "state": p.get("reac.link-state"),
            "scope": p.get("reac.discovery.scope"),
        })
    found.sort(key=lambda n: (n["state"] != "established", n["id"]))
    return found


def pick(nodes, base, channels=None):
    hits = [n for n in nodes
            if n["base"] == base and (channels is None or n["channels"] == channels)]
    if not hits:
        raise SystemExit(
            f"no established reac playback node publishes base={base}"
            + (f" channels={channels}" if channels else "")
            + f"; visible: {[(n['base'], n['channels'], n['name']) for n in nodes]}")
    if len(hits) > 1:
        raise SystemExit(f"base={base} is ambiguous across {[n['name'] for n in hits]}; "
                         "pass --channels to disambiguate")
    return hits[0]


def parse_set(text):
    out = {}
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        k, _, v = item.partition("=")
        k = k.strip()
        if k not in PARAMS:
            raise SystemExit(f"unknown head-amp param {k!r}; expected {PARAMS}")
        try:
            n = int(v)
        except ValueError:
            raise SystemExit(f"{k}={v!r} is not an integer")
        lo, hi = RANGE[k]
        if not lo <= n <= hi:
            # reac-pw drops out-of-range values in its own parser, which would make this
            # probe report a write it never performed.
            raise SystemExit(f"{k}={n} out of range {lo}..{hi}")
        out[k] = n
    if not out:
        raise SystemExit("--set was empty")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", type=int, help="published reac.headamp.base of the target box")
    ap.add_argument("--channels", type=int, help="disambiguate two boxes sharing a base")
    ap.add_argument("--input", type=int, help="1-based box input")
    ap.add_argument("--all", action="store_true", help="every input the box declares")
    ap.add_argument("--set", help="phantom=1,pad=0,sens=44")
    ap.add_argument("--list", action="store_true", help="show declarations and exit")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    nodes = reac_playback_nodes(pw_dump())
    if a.list or a.base is None:
        for n in nodes:
            print(f"id={n['id']:>5} base={n['base']:>3} channels={n['channels']:>3} "
                  f"model={n['model']} state={n['state']} scope={n['scope']} "
                  f"caps={n['caps']} name={n['name']}")
        return 0 if a.list else 2

    node = pick(nodes, a.base, a.channels)
    values = parse_set(a.set or "")

    if a.all:
        inputs = list(range(1, node["channels"] + 1))
    elif a.input:
        if not 1 <= a.input <= node["channels"]:
            raise SystemExit(f"input {a.input} outside the box's declared "
                             f"1..{node['channels']}")
        inputs = [a.input]
    else:
        raise SystemExit("pass --input N or --all")

    entries = []
    for i in inputs:
        ch = node["base"] + (i - 1)
        for k, v in values.items():
            entries.append(f'"reac.headamp.{ch}.{k}" {v}')

    pod = "{ params = [ " + " ".join(entries) + " ] }"
    print(f"# node id={node['id']} name={node['name']} base={node['base']} "
          f"channels={node['channels']} model={node['model']}")
    print(f"# inputs {inputs[0]}..{inputs[-1]} -> wire CH "
          f"{node['base'] + inputs[0] - 1}..{node['base'] + inputs[-1] - 1} "
          f"(0x{node['base'] + inputs[0] - 1:02x}..0x{node['base'] + inputs[-1] - 1:02x})")
    print(f"# set {values}")
    if a.dry_run:
        print(pod)
        return 0

    r = subprocess.run(["pw-cli", "set-param", str(node["id"]), "Props", pod],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stdout + r.stderr, file=sys.stderr)
        raise SystemExit(f"pw-cli set-param failed ({r.returncode})")
    print("# written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
