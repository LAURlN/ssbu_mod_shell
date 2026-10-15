"""List the exported symbols in a `lua2cpp_<fighter>.nro`, with file offsets.

## Why this is not a full `Elf64_Sym` reader

The obvious implementation - find `MOD0`, read `dynstr_offset` / `dynsym_offset` /
`dynsym_size` and walk 0x18-byte `Elf64_Sym` records - does not work on these
files, and the reasons are worth recording so nobody re-derives them:

* **`Elf64_Sym` is 0x18 bytes, not 0x10.** `st_name`/`st_info`/`st_other`/
  `st_shndx` then `st_value`/`st_size`. Reading it as `<IIQQ` at a 0x10 stride is
  the single most likely way to get a plausible-looking but wrong symbol table.
* **The NRO magic is at 0x10**, not 0.
* **`MOD0` does not hold `dynstr`/`dynsym` directly.** Its first field is the
  offset of `.dynamic`, relative to `MOD0` itself (G&W: `0x105070 + 0x52e80 =
  0x157ef0`); `.dynamic` then gives `DT_SYMTAB`/`DT_STRTAB`/`DT_RELA`/`DT_JMPREL`.
  That full reader now exists: `tools/nro_decomp/nro_flatten.py` (2026-09-29;
  the earlier claim here that no MOD0 reading resolves names is in
  `handbook/graveyard.md` R-17). Note that only 11 symbols are *exported*;
  status functions are anonymous and are found through `sv_set_status_func`
  (`tools/nro_decomp/status_table.py`), not through this scan.

## What is reliable

`.dynstr` is a contiguous run of NUL-terminated ASCII, and the symbol names are
unmistakable: `_ZN...` (Itanium C++) or `__...` (C runtime). Scanning for that
pattern gives the **exported symbol list with file offsets**, which is enough to
answer the questions this project actually asks - *does this NRO export a status
script creator, and where is it?*

Note the real exported name is
`_ZN7lua2cpp44create_agent_fighter_**status**_script_gamewatch...`, not
`create_agent_status_script_gamewatch`; searching for the short form finds
nothing, which is misleading.

    toolchains/py312/python.exe src/pgwr/tools/nro_syms.py \
        export/prebuilt/nro/release/lua2cpp_gamewatch.nro status
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# Itanium-mangled C++ and C runtime symbols. `_Z` covers the mangled namespace;
# `__` covers the C/SDK exports that a Smash module also needs.
SYMBOL = re.compile(rb'(?:_Z[A-Za-z0-9_$.]{6,4096}|__[A-Za-z0-9_]{4,200})')


def scan(path: Path) -> list[tuple[int, str]]:
    d = path.read_bytes()
    out: list[tuple[int, str]] = []
    for m in SYMBOL.finditer(d):
        start = m.start()
        # The match must begin right after a NUL, otherwise we are inside a
        # longer string and have latched onto a suffix of it.
        if start and d[start - 1] != 0:
            continue
        end = d.find(b'\x00', start)
        if end < 0:
            continue
        name = d[start:end]
        if all(33 <= c < 127 for c in name):
            out.append((start, name.decode('ascii')))
    return out


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    path = Path(sys.argv[1])
    if not path.is_absolute() and not path.is_file():
        path = ROOT / path
    syms = scan(path)
    needle = sys.argv[2].lower() if len(sys.argv) > 2 else None
    sel = syms if not needle else [s for s in syms if needle in s[1].lower()]
    print(f'{path.name}: {len(syms)} exported symbol names'
          f'{" matching " + repr(needle) if needle else ""}'
          f' -> {len(sel)}\n')
    for off, name in sel:
        print(f'  0x{off:08x}  {name}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
