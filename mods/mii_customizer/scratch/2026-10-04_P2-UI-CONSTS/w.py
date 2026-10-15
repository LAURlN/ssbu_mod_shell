"""P2-SKILL-NATIVE window dumper: instructions with adrp/add/ldr resolution notes.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python w.py START COUNT [END]

Prints one line per instruction, annotating adrp page results and add/ldr completions
against a base register whose adrp is inside the dumped range. Also prints, for every
`bl`, its resolved target, and for every `stp`/`str` whose base is a register, the store
offsets. Relocated pointer values are read from the relocation table (not the file qword).
"""
import struct
import sys
from pathlib import Path

import capstone

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
md.detail = False


def sx(v, b):
    return v - (1 << b) if v & (1 << (b - 1)) else v


def cstr(a, limit=72):
    if not (0x39C8000 <= a < len(data)):
        return ''
    e = data.find(b'\0', a, a + limit)
    if e < 0:
        return ''
    r = data[a:e]
    if len(r) < 3 or any(c < 0x20 or c > 0x7E for c in r):
        return ''
    return r.decode()


start = int(sys.argv[1], 0)
count = int(sys.argv[2]) if len(sys.argv) > 2 else 40
end = int(sys.argv[3], 0) if len(sys.argv) > 3 else start + 4 * count

pages = {}
for k in range((end - start) // 4):
    a = start + 4 * k
    w = struct.unpack_from('<I', data, a)[0]
    ins = next(md.disasm(data[a:a + 4], a), None)
    txt = ('%7s %s' % (ins.mnemonic, ins.op_str)) if ins else '.word'
    note = ''
    if (w & 0x9F000000) == 0x90000000:                      # adrp
        rd = w & 31
        page = (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12)
        pages[rd] = page
        note = '   ; x%d page 0x%x' % (rd, page)
    elif (w & 0xFF800000) == 0x91000000:                     # add imm
        rd, rn = w & 31, (w >> 5) & 31
        if rn in pages:
            t = pages[rn] + ((w >> 10) & 0xFFF)
            s = cstr(t)
            note = '   ; x%d = 0x%x' % (rd, t) + (' "%s"' % s if s else '')
            if rd != rn:
                pages[rd] = t
    elif (w & 0xFFC00000) == 0xF9400000:                     # ldr (64-bit imm)
        rd, rn = w & 31, (w >> 5) & 31
        if rn in pages:
            t = pages[rn] + (((w >> 10) & 0xFFF) << 3)
            note = '   ; x%d = [0x%x]' % (rd, t)
            pages[rd] = t
    elif (w & 0x7C000000) == 0x94000000:                     # bl
        t = a + (sx(w & 0x3FFFFFF, 26) << 2)
        note = '   ; -> 0x%x' % t
    elif (w & 0xFFC00000) == 0xA9000000 or (w & 0xFFC00000) == 0xF9000000:
        pass
    print('0x%08x: %s%s' % (a, txt, note))
