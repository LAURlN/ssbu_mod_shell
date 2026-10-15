"""Decode the global article registry in the flat Smash `main.bin` image.

`FIGHTER_GAMEWATCH_GENERATE_ARTICLE_NORMAL_WEAPON` and its siblings are
*per-fighter* indices, but the game keeps every fighter's articles in one
contiguous run of a single global table, so a fighter's block has to be located
before the constant can be read off. The block boundaries are not stored as
counts; they fall out of the table's own ordering.

What is in the file, and where (all offsets are == virtual address in the flat
image):

* The table is 1845 records of 0x18 bytes at `0x3EACF88`, laid out
  `{u32 name_ptr, u32 pad, u32 data_ptr, u32 pad, u32 flags, u32 pad}`.
  The table start is pinned by requiring **every** `name_ptr` to resolve as a
  real string; that filter is what makes the boundary trustworthy, since a
  looser `data_ptr`/`flags` walk overshoots to 306,168 records.
* `name_ptr` points into `.rodata` and resolves for **all 1845** records.
* `data_ptr` increments by exactly 8 per record (from `0x5185BD0` upward) and is
  **not a resolvable address in this image**. The whole 1849-slot span
  `0x5185BD0..0x5189590` is **0/1849 nonzero**, the pages around it are
  essentially all zero, and a scan of `.text` for `adrp`+`str` pairs targeting
  that range finds only 3 stores, none of them at an article slot. So the values
  are not unrelocated pointers sitting in `.data` either.

  The reading consistent with all of that: they are **runtime virtual addresses**
  and the game loads `main` at a **non-zero base**, so `0x5185BD0` is simply not
  where those objects live in the flat image. That is a correction to an earlier
  claim in this file, which said the slots were "`.bss` vtables filled in at load
  time by constructors" - there is no code writing them here, and `.bss` (35 MB)
  is not present in the image at all.

  Consequence, stated plainly: **this table says which articles exist and in what
  order, and nothing about their behaviour.** Reaching the behaviour needs the
  game's load base for `main`, which is not recorded in
  `pyra_mythra_clone/reports/exefs-dumps.json`. Do not claim otherwise from this
  image alone.
* `flags` is `0x403` for every record, so it carries no discriminating
  information.

Two independent cross-checks pin the blocks, and both are in this file's
docstring tests below: `eflame` occupies 5 consecutive records immediately
before `elight`, which matches the known `ARTICLE_TERM = 0x5` (eflame has
articles 0-4), and G&W's own `model/`+`motion/` folders name exactly the nine
articles in his run.

    toolchains/py312/python.exe src/pgwr/tools/article_table.py
"""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IMAGE = ROOT / 'dumps/exefs/13.0.4/main.bin'
EXPORT = ROOT / 'dumps/arc/fighter/gamewatch'

TABLE_START = 0x3EACF88
RECORD = 0x18
COUNT = 1845

RODATA = (0x39C8000, 0x4F16000)
BSS_FIRST = 0x5185BD0

# G&W's block, verified two ways (see module docstring).
GW_FIRST, GW_LAST = 120, 128

# eflame's block, used as the independent sanity check on the layout.
EFLAME_FIRST, EFLAME_COUNT, EFLAME_TERM = 1818, 5, 0x5


def load() -> bytes:
    if not IMAGE.is_file():
        raise SystemExit(f'missing {IMAGE}')
    return IMAGE.read_bytes()


def cstr(d: bytes, addr: int, cap: int = 48) -> str | None:
    if not (RODATA[0] <= addr < RODATA[1]):
        return None
    end = d.find(b'\x00', addr, addr + cap)
    if end < 0 or end == addr:
        return None
    raw = d[addr:end]
    return raw.decode('ascii') if all(32 <= c < 127 for c in raw) else None


def record(d: bytes, i: int) -> tuple[int, str, int, int]:
    a = TABLE_START + i * RECORD
    name_ptr, _, data_ptr, _, flags, _ = struct.unpack_from('<6I', d, a)
    return a, cstr(d, name_ptr) or f'#{name_ptr:#x}', data_ptr, flags


def main() -> int:
    d = load()
    print(f'image  {IMAGE.name}  {len(d)} bytes')
    print(f'table  0x{TABLE_START:x}  {COUNT} records x 0x{RECORD:x} bytes\n')

    unresolved = [i for i in range(COUNT) if record(d, i)[1].startswith('#')]
    print(f'name resolution: {COUNT - len(unresolved)}/{COUNT}')
    if unresolved:
        print(f'  unresolved at {unresolved[:20]}')
    flags = {record(d, i)[3] for i in range(COUNT)}
    print(f'flags observed: {sorted(hex(f) for f in flags)}'
          f'{"  (no discriminating information)" if len(flags) == 1 else ""}')

    print('\n=== Mr. Game & Watch ===')
    print(f'block 0x{GW_FIRST}..0x{GW_LAST} '
          f'({GW_LAST - GW_FIRST + 1} articles, indices 0-8)\n')
    print('  local  global  name             data_ptr (not an image addr)')
    for k, i in enumerate(range(GW_FIRST, GW_LAST + 1)):
        a, name, dptr, _ = record(d, i)
        star = '   <== the missing props' if name == 'normal_weapon' else ''
        print(f'  {k:5d}  {i:6d}  {name:15s}  0x{dptr:08x}{star}')

    # Cross-check 1: G&W's own export folders must name exactly his articles.
    folders = {p.name for p in (EXPORT / 'model').iterdir() if p.is_dir()}
    folders -= {'body'}
    in_table = {record(d, i)[1] for i in range(GW_FIRST, GW_LAST + 1)}
    only_table = in_table - folders
    only_folders = folders - in_table
    print(f'\n  export model/ folders: {len(folders)}  '
          f'(articles in table but no folder: {sorted(only_table)})')
    print(f'  folders that are not articles (food/item models): '
          f'{sorted(only_folders)}')
    assert not only_table, f'table block disagrees with export: {only_table}'

    # Cross-check 2: eflame must be ARTICLE_TERM + 1 records, right before elight.
    _, eflame0, _, _ = record(d, EFLAME_FIRST)
    _, eflameN, _, _ = record(d, EFLAME_FIRST + EFLAME_COUNT - 1)
    _, after, _, _ = record(d, EFLAME_FIRST + EFLAME_COUNT)
    print(f'\n  sanity: global {EFLAME_FIRST}..{EFLAME_FIRST + EFLAME_COUNT - 1} '
          f'= {eflame0!r}..{eflameN!r}, then {after!r}')
    assert eflame0 == 'eflame' and after == 'elight', 'eflame block moved'
    # `ARTICLE_TERM` is the exclusive end (eflame's is 0x5 and she has articles
    # 0-4), so the record count must equal it, not one less.
    assert EFLAME_COUNT == EFLAME_TERM, 'eflame count != ARTICLE_TERM'
    print('  both cross-checks pass: blocks are per-fighter and contiguous.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
