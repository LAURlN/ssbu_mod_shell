"""Provenance-bound scan for code that forms addresses inside the static block
[LO,HI) (default: per-player table T = G+0x3670 .. second table end).
Register values are tracked linearly from adrp/add/mov/movk/madd inside each function
(state reset at ret, caller-saved cleared at bl). A hit needs a base register whose
constant part was built from an adrp in the same window. No bare-displacement matching.
usage: scan.py [lo hi]   -> lines: site fn? kind value(+idx*stride) insn"""
import struct, sys
from pathlib import Path
import capstone
from capstone.arm64 import *
IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM); md.detail = True
TEXT = (0x100, 0x39C8000)
LO = int(sys.argv[1], 0) if len(sys.argv) > 2 else 0x5307760
HI = int(sys.argv[2], 0) if len(sys.argv) > 2 else 0x5307760 + 0xe40 + 8 * 0x240
def rn(ins, r):
    n = ins.reg_name(r)
    if not n: return -1
    if n in ('x29', 'fp'): return 29
    if n in ('x30', 'lr'): return 30
    if n[0] in 'xw' and n[1:].isdigit(): return int(n[1:])
    return -1
# value forms: ('c', v) plain constant (addr flag = came from adrp), ('b', v, stride) = v + idx*stride
st = {}
def hit(ins, kind, v, stride=0):
    s = f'+i*0x{stride:x}' if stride else ''
    print(f'0x{ins.address:08x} {kind:5s} 0x{v:x}{s}  | {ins.mnemonic} {ins.op_str}')
def inr(v, stride):
    if stride: return LO - stride * 8 < v < HI and v >= LO - 0x10 or (LO <= v < HI)
    return LO <= v < HI
CH = 1 << 20
for base in range(TEXT[0], TEXT[1], CH):
    for ins in md.disasm(data[base:min(base + CH, TEXT[1])], base):
        m = ins.mnemonic; ops = ins.operands
        if m == 'ret': st = {}; continue
        if m in ('bl', 'blr'):
            for r in list(st):
                if r < 19: del st[r]
            continue
        if not ops: continue
        d = rn(ins, ops[0].reg) if ops[0].type == ARM64_OP_REG else -1
        mem = [o for o in ops if o.type == ARM64_OP_MEM]
        if mem:
            b = rn(ins, mem[0].mem.base); v = st.get(b)
            if v:
                disp = mem[0].mem.disp; idx = mem[0].mem.index
                tot = None
                if idx:
                    iv = st.get(rn(ins, idx))
                    if iv and iv[0] == 'c' and v[0] in 'cb': tot = v[1] + iv[1]
                    elif iv and iv[0] == 'b' and v[0] == 'c': tot = v[1] + iv[1]; v = ('b', tot, iv[2])
                else: tot = v[1] + disp
                if tot is not None and v[0] in 'cb' and (v[0] == 'b' or v[1] > 0x4000000):
                    if inr(tot, v[2] if v[0] == 'b' else 0): hit(ins, 'mem', tot, v[2] if v[0] == 'b' else 0)
            if m.startswith('ld') and d >= 0:
                st.pop(d, None)
                if len(ops) > 2 and ops[1].type == ARM64_OP_REG: st.pop(rn(ins, ops[1].reg), None)
            if ins.writeback: st.pop(b, None)
            continue
        if d < 0: continue
        if m == 'adrp': st[d] = ('c', ops[1].imm); continue
        if m in ('mov', 'movz') and ops[1].type == ARM64_OP_IMM: st[d] = ('c', ops[1].imm & 0xffffffffffffffff); continue
        if m == 'mov' and ops[1].type == ARM64_OP_REG:
            s = st.get(rn(ins, ops[1].reg))
            if s: st[d] = s
            else: st.pop(d, None)
            continue
        if m == 'movk' and d in st and st[d][0] == 'c':
            sh = ops[1].shift.value if ops[1].shift.type else 0
            st[d] = ('c', (st[d][1] & ~(0xffff << sh)) | (ops[1].imm << sh)); continue
        if m == 'add' and len(ops) == 3 and ops[1].type == ARM64_OP_REG:
            a = st.get(rn(ins, ops[1].reg)); nv = None
            if ops[2].type == ARM64_OP_IMM and a:
                imm = ops[2].imm << (ops[2].shift.value if ops[2].shift.type else 0)
                nv = (a[0], a[1] + imm) + a[2:]
            elif ops[2].type == ARM64_OP_REG and not ops[2].shift.type and not ops[2].ext:
                c = st.get(rn(ins, ops[2].reg))
                if a and c:
                    if a[0] == 'c' and c[0] == 'c': nv = ('c', a[1] + c[1])
                    elif a[0] == 'b' and c[0] == 'c': nv = ('b', a[1] + c[1], a[2])
                    elif a[0] == 'c' and c[0] == 'b': nv = ('b', a[1] + c[1], c[2])
            if nv:
                st[d] = nv
                if nv[1] > 0x4000000 and inr(nv[1], nv[2] if nv[0] == 'b' else 0): hit(ins, 'addr', nv[1], nv[2] if nv[0] == 'b' else 0)
            else: st.pop(d, None)
            continue
        if m in ('madd', 'smaddl', 'umaddl') and len(ops) == 4:
            s1 = st.get(rn(ins, ops[1].reg)); s2 = st.get(rn(ins, ops[2].reg)); a = st.get(rn(ins, ops[3].reg))
            stride = s2[1] if s2 and s2[0] == 'c' else (s1[1] if s1 and s1[0] == 'c' else None)
            if stride and a and a[0] == 'c' and a[1] > 0x4000000 and stride < 0x100000:
                st[d] = ('b', a[1], stride)
                if inr(a[1], stride): hit(ins, 'addr', a[1], stride)
            else: st.pop(d, None)
            continue
        if m in ('cmp', 'cmn', 'tst', 'str', 'strb', 'strh', 'stp', 'stur', 'cbz', 'cbnz', 'tbz', 'tbnz', 'b', 'ccmp') or m.startswith('b.'): continue
        st.pop(d, None)
