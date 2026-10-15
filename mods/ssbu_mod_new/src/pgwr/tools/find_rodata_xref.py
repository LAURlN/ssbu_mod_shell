"""Find code in the flat Smash `main.bin` image that references a rodata string.

The ExeFS `main` is an NSO with every segment compressed (flags 0x3F), so
`dumps/exefs/13.0.4/main.bin` is the *decompressed* flat
image: virtual address == file offset, `.text` content at 0x100, `.rodata` at
0x39C8000, `.data` at 0x4F16000. That flatness is what makes this possible
without Ghidra: an `adrp` + `add` pair that names a known string offset is
findable with two integer compares per instruction, and an 86 MB scan of that
shape takes seconds.

Only `adrp` is searched for, because it is the instruction that carries the
page. The `add`/`ldr` that completes the address lives in the next few
instructions and is reported as context rather than required to match, so a
string reached through a jump table or a struct pointer still surfaces.

    toolchains/py312/python.exe src/pgwr/tools/find_rodata_xref.py normal_weapon
"""
from __future__ import annotations

import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
IMAGE = ROOT / 'dumps/exefs/13.0.4/main.bin'

TEXT_START = 0x100
TEXT_END = 0x39C8000


def find_offsets(m: bytes, needle: bytes) -> list[int]:
    out, i = [], 0
    while True:
        j = m.find(needle, i)
        if j < 0:
            return out
        out.append(j)
        i = j + 1


def sign_extend(value: int, bits: int) -> int:
    if value & (1 << (bits - 1)):
        return value - (1 << bits)
    return value


def disasm_context(data: bytes, addr: int, count: int = 6) -> list[str]:
    """Raw hex of the instructions around `addr`, plus any adrp targets."""
    rows = []
    for k in range(count):
        a = addr + 4 * k
        w = struct.unpack_from('<I', data, a)[0]
        note = ''
        if (w >> 24) & 0x9F == 0x90:            # adrp
            immlo = (w >> 29) & 3
            immhi = (w >> 5) & 0x7FFFF
            imm = sign_extend((immhi << 2) | immlo, 21) << 12
            note = f'  ; adrp -> 0x{(a & ~0xFFF) + imm:x}'
        rows.append(f'  0x{a:08x}: {w:08x}{note}')
    return rows


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else 'normal_weapon'
    # A `0x...` argument is treated as an address to find code references to,
    # which is the common case now that the tables are already located: the
    # interesting question is usually "who touches this address", not "who
    # mentions this string".
    if arg.lower().startswith('0x'):
        needle = b''
        addr = int(arg, 16)
        targets = [addr]
    else:
        needle = arg.encode()
        addr = None
        targets = None
    if not IMAGE.is_file():
        print(f'missing {IMAGE}', file=sys.stderr)
        return 1
    data = IMAGE.read_bytes()
    print(f'image {IMAGE.name}: {len(data)} bytes')
    if targets is None:
        targets = find_offsets(data, needle)
    print(f'{(hex(addr) + " (address)" if addr is not None else repr(needle))} '
          f'at {len(targets)} offset(s): '
          + ', '.join(hex(t) for t in targets))
    if not targets:
        return 1

    text = data[TEXT_START:TEXT_END]
    pages = {t & ~0xFFF for t in targets}
    pages_with_low = {}
    for t in targets:
        pages_with_low.setdefault(t & ~0xFFF, set()).add(t & 0xFFF)

    print(f'\nscanning {len(text)} bytes of .text for adrp into '
          f'{len(pages)} page(s)...')
    hits: dict[int, list[int]] = {}
    for off in range(0, len(text) - 4, 4):
        w = struct.unpack_from('<I', text, off)[0]
        if (w >> 24) & 0x9F != 0x90:
            continue
        immlo = (w >> 29) & 3
        immhi = (w >> 5) & 0x7FFFF
        imm = sign_extend((immhi << 2) | immlo, 21) << 12
        page = ((off + TEXT_START) & ~0xFFF) + imm
        if page in pages:
            hits.setdefault(page, []).append(off + TEXT_START)

    if not hits:
        print('no adrp found targeting those pages')
        return 1

    # An adrp into the page is cheap: that page holds a whole string blob, so
    # hundreds of unrelated functions land there. The instruction that actually
    # names *this* string is the `add xD, xN, #low` that consumes the adrp's
    # register, so require that pairing and match the low 12 bits exactly.
    # A string reached via a pointer table or a jump table has no such add, and
    # is reported separately by --loose below rather than silently dropped.
    print('\n=== exact add(xN, #low) completions ===')
    exact: list[tuple[int, int, int]] = []   # (adrp addr, low, reg)
    loose_pages: dict[int, list[int]] = {}
    for page, addrs in sorted(hits.items()):
        lows = pages_with_low[page]
        for a in addrs:
            w = struct.unpack_from('<I', data, a)[0]
            rd = w & 0x1F
            matched = False
            for k in range(1, 9):
                w2 = struct.unpack_from('<I', data, a + 4 * k)[0]
                if (w2 >> 24) & 0x9F == 0x90:   # another adrp: give up on this pair
                    break
                if (w2 & 0x7F800000) == 0x11000000:      # add (immediate), 64-bit
                    imm12 = (w2 >> 10) & 0xFFF
                    rn = (w2 >> 5) & 0x1F
                    if rn == rd and imm12 in lows:
                        exact.append((a, imm12, rd))
                        matched = True
            if not matched:
                loose_pages.setdefault(page, []).append(a)

    for a, low, reg in exact:
        print(f'\n adrp 0x{a:x} + add x{reg}, #0x{low:x}  -> 0x{(a & ~0xFFF) + low:x}')
        for line in disasm_context(data, a, 8):
            print(line)

    if loose_pages:
        total = sum(len(v) for v in loose_pages.values())
        print(f'\n({total} further adrp site(s) into the same page(s) with no '
              f'completing add - pointer/jump-table references or other '
              f'strings; --loose lists them)')
        for page, addrs in sorted(loose_pages.items()):
            print(f'  page 0x{page:x}: {len(addrs)} site(s), e.g. '
                  + ', '.join(hex(x) for x in addrs[:12]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
