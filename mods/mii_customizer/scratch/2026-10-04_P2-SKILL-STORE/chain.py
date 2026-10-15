"""Provenance-bound scan: holder slot load ([r,#SLOT]) -> ldr [r,#0x80] -> access at 0xf8..0x107.
Tracks register copies linearly within a window; no bare-displacement matching.
usage: chain.py <slot_hex> [window]"""
import struct, sys
from pathlib import Path
import capstone
from capstone.arm64 import *
IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM); md.detail = True
slot = int(sys.argv[1], 0); W = int(sys.argv[2]) if len(sys.argv) > 2 else 400
TEXT = (0x100, 0x39C8000)
def is_ldr_x(w, disp):  # ldr xT,[xN,#disp] unsigned offset
    return (w & 0xFFC00000) == 0xF9400000 and ((w >> 10) & 0xFFF) * 8 == disp
hits = 0
for a in range(TEXT[0], TEXT[1], 4):
    w = struct.unpack_from('<I', data, a)[0]
    if not is_ldr_x(w, slot): continue
    outer = {w & 31}; obj = set()
    for ins in md.disasm(data[a + 4:a + 4 + 4 * W], a + 4):
        if ins.mnemonic == 'ret': break
        ops = ins.operands
        mem = [o for o in ops if o.type == ARM64_OP_MEM]
        name = lambda r: ins.reg_name(r)
        def rn(r):
            n = ins.reg_name(r)
            return int(n[1:]) if n and n[0] in 'xw' and n[1:].isdigit() else {'fp':29,'x29':29,'lr':30,'x30':30}.get(n, -1)
        dst = rn(ops[0].reg) if ops and ops[0].type == ARM64_OP_REG else -1
        if mem:
            b = rn(mem[0].mem.base); d = mem[0].mem.disp
            if b in obj and 0xf8 <= d <= 0x107:
                print(f'HIT slot 0x{slot:x} load@0x{a:x}: 0x{ins.address:x} {ins.mnemonic} {ins.op_str}'); hits += 1
            if ins.mnemonic == 'ldr' and b in outer and d == 0x80 and dst >= 0:
                outer.discard(dst); obj.add(dst); continue
        if ins.mnemonic == 'mov' and len(ops) == 2 and ops[1].type == ARM64_OP_REG:
            s = rn(ops[1].reg)
            if s in outer: outer.add(dst); obj.discard(dst); continue
            if s in obj: obj.add(dst); outer.discard(dst); continue
        if ins.mnemonic == 'add' and len(ops) == 3 and ops[1].type == ARM64_OP_REG and ops[2].type == ARM64_OP_IMM and rn(ops[1].reg) in obj and 0xf8 <= ops[2].imm <= 0x103:
            print(f'HIT(add) slot 0x{slot:x} load@0x{a:x}: 0x{ins.address:x} {ins.mnemonic} {ins.op_str}'); hits += 1
        if ins.mnemonic in ('bl', 'blr'):
            for r in list(outer | obj):
                if r < 19: outer.discard(r); obj.discard(r)
        elif dst >= 0 and not ins.mnemonic.startswith(('str', 'stp', 'cmp', 'cb', 'tb', 'stur')):
            outer.discard(dst); obj.discard(dst)
        if not outer and not obj: break
print('hits', hits)
