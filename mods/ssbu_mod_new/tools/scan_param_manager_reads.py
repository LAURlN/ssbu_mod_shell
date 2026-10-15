"""List native reads of a fighter's decoded vl.prc slot in the parameter manager (v1.0.0).

Donor weapon code reads *(*(main+0x52bb3b0)+slot), the donor fighter's decoded
vl.prc object. With a foreign owner that slot was null on hardware twice (G&W breath
+0x690, Hero fireball +0x1298; handbook/07_articles.md). This finds every
`ldr xN, [xM, #slot]` whose base came from `adrp 0x52bb000` within 40 instructions,
and names the function and vtable slot(s) that reference it through RELATIVE relocs.

usage: scan_param_manager_reads.py <slot hex>        e.g. 0x1298
       scan_param_manager_reads.py --smoke           checks the two known cases
Static reading of dumps/exefs/13.0.4/main.bin only; it proves nothing about runtime.
"""
import struct
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANAGER_PAGE = 0x52bb000
FUNCTION_WINDOW = 0x1000


def load():
    cfg = tomllib.loads((ROOT / 'paths.toml').read_text())
    data = (ROOT / cfg['dumps']['exefs'] / 'main.bin').read_bytes()
    return data, struct.unpack('<%dI' % (len(data) // 4), data[:len(data) // 4 * 4])


def relative_relocs(data):
    """{target: [reloc offsets]} for R_AARCH64_RELATIVE entries (type 0x403) in the RELA table."""
    targets = {}
    needle = struct.pack('<Q', 0x403)
    i = data.find(needle)
    while i != -1:
        if i >= 8 and (i - 8) % 8 == 0:
            off, add = struct.unpack_from('<QQ', data, i - 8)[0], struct.unpack_from('<Q', data, i + 8)[0]
            if add < len(data):
                targets.setdefault(add, []).append(off)
        i = data.find(needle, i + 8)
    return targets


def adrp_page(pc, word):
    if word & 0x9F000000 != 0x90000000:
        return None
    imm = ((word >> 5) & 0x7FFFF) << 2 | (word >> 29) & 3
    if imm & (1 << 20):
        imm -= 1 << 21
    return (pc & ~0xFFF) + (imm << 12)


def scan(slot, data=None, words=None, relocs=None):
    if data is None:
        data, words = load()
    relocs = relative_relocs(data) if relocs is None else relocs
    ldr = 0xF9400000 | (slot // 8) << 10
    starts = sorted(relocs)
    import bisect
    hits = []
    for index, word in enumerate(words):
        if word & 0xFFFFFC00 != ldr:
            continue
        pc = index * 4
        if not any(adrp_page(pc - 4 * j, words[index - j]) == MANAGER_PAGE for j in range(1, 40)):
            continue
        k = bisect.bisect_right(starts, pc) - 1
        function = starts[k] if k >= 0 and pc - starts[k] < FUNCTION_WINDOW else None
        hits.append((pc, function, relocs.get(function, []) if function is not None else []))
    return hits


def main():
    if sys.argv[1:] == ['--smoke']:
        data, words = load()
        relocs = relative_relocs(data)
        fireball = {h[0]: h for h in scan(0x1298, data, words, relocs)}
        assert fireball[0x33c8ec0][1] == 0x33c8ea0 and 0x51b1078 in fireball[0x33c8ec0][2], fireball[0x33c8ec0]
        breath = {h[0] for h in scan(0x690, data, words, relocs)}
        assert 0x33fc13c in breath, sorted(map(hex, breath))
        print('PASS: fireball constructor 0x33c8ea0 (vtable slot 0x51b1078) and breath 0x33fc13c found')
        return
    for pc, function, slots in scan(int(sys.argv[1], 16)):
        where = f'fn {function:#x} vtable/ptr slots {[hex(s) for s in slots[:4]]}' if function is not None else 'fn ?'
        print(f'{pc:#x}  {where}')


if __name__ == '__main__':
    main()
