# Building the reac-captures tools

The captures need no build. The tooling around them does, a little.

## Fetching the captures

`*.pcap`, `*.pcapng` and `*.cap` are stored with Git LFS. Without `git-lfs` a clone holds only the
pointer files.

```
git lfs install
git clone https://github.com/FreeREAC/reac-captures.git
cd reac-captures && git lfs pull
```

## Python extractors (`analysis/*.py`)

Python 3, standard library only, except `analysis/hum_rate_check.py`, which needs `numpy`.
Run them in place; nothing is installed.

## C tools (`analysis/distil.c`, `analysis/up_slots.c`)

Both link [libreac](https://github.com/FreeREAC/libreac). Build libreac first (`make` in its
checkout produces `libreac.a`), then:

```
LIBREAC=../libreac
gcc -O2 -Wall -o analysis/distil   analysis/distil.c   -I$LIBREAC/include $LIBREAC/libreac.a -lm
gcc -O2 -Wall -o analysis/up_slots analysis/up_slots.c -I$LIBREAC/include $LIBREAC/libreac.a -lm
```

`analysis/slot_rms.sh` expects `up_slots` beside it (or its path in `UP_SLOTS`).

## Checks

The repository's own check, the same one CI runs (`.github/workflows/check.yml`):

```
python3 -m unittest discover -s tools -p 'test_*.py'
python3 tools/freereac_ops.py check
```
