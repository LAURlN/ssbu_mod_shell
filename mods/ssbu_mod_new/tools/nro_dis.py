"""Disassemble parts of a lua2cpp NRO with imported symbol names resolved.

usage: nro_dis.py <nro> hashsites <name>...      where each name's hash40 is built
       nro_dis.py <nro> dis <hex addr> <count>    disassemble
       nro_dis.py <nro> xref <hex addr>           find bl/b/adrp+add refs to addr
"""
import struct, sys, zlib
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

path = sys.argv[1]
data = open(path, 'rb').read()

# MOD0 -> dynamic
mod0_off = struct.unpack_from('<I', data, 4)[0]
_, dyn_rel = struct.unpack_from('<4sI', data, mod0_off)
dyn = mod0_off + dyn_rel
tags = {}
i = dyn
rels = []
while True:
    t, v = struct.unpack_from('<qQ', data, i); i += 16
    if t == 0: break
    tags.setdefault(t, v)
symtab, strtab, syment = tags[6], tags[5], tags.get(11, 24)
def cstr(o):
    e = data.index(b'\0', o); return data[o:e].decode('latin1')
def sym(idx):
    name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', data, symtab + idx * syment)
    return cstr(strtab + name), value, shndx
got_names = {}
for rel_tag, sz_tag in ((23, 2), (7, 8)):   # JMPREL/PLTRELSZ, RELA/RELASZ
    if rel_tag not in tags: continue
    off, size = tags[rel_tag], tags[sz_tag]
    for k in range(0, size, 24):
        r_off, r_info, addend = struct.unpack_from('<QQq', data, off + k)
        s = r_info >> 32
        if s:
            n, v, sh = sym(s)
            if sh == 0:
                got_names[r_off] = n
# local exported symbols
exports = {}
k = 1
while symtab + k * syment < strtab:
    try:
        n, v, sh = sym(k)
    except Exception:
        break
    if sh and v: exports[v] = n
    k += 1

md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
md.detail = False

def plt_target(addr):
    """If addr is a PLT stub (adrp x16; ldr x17,[x16,#o]; add; br x17) return name."""
    ins = list(md.disasm(data[addr:addr + 16], addr))
    if len(ins) >= 2 and ins[0].mnemonic == 'adrp' and ins[1].mnemonic == 'ldr' and 'x16' in ins[0].op_str:
        page = int(ins[0].op_str.split('#')[1], 16)
        o = ins[1].op_str.split('#')[1].rstrip(']')
        slot = page + int(o, 16)
        return got_names.get(slot)
    return None

import re
def demangle_short(n):
    m = re.search(r'lua_bind(\d+)(\w+?)_impl', n)
    if m:
        L = int(m.group(1)); return n[n.index('lua_bind') + 8 + len(m.group(1)):][:L]
    return n[:120]

def dis(addr, count):
    for ins in md.disasm(data[addr:addr + count * 4], addr):
        extra = ''
        if ins.mnemonic in ('bl', 'b'):
            t = int(ins.op_str.lstrip('#'), 16)
            nm = plt_target(t) or exports.get(t)
            if nm: extra = '  ; ' + demangle_short(nm)
        print(f'{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}{extra}')

def h40(s):
    b = s.encode(); return (len(b) << 32) | zlib.crc32(b)

cmd = sys.argv[2]
if cmd == 'hashsites':
    words = struct.unpack_from('<%dI' % (len(data) // 4), data)
    for n in sys.argv[3:]:
        h = h40(n)
        lo = h & 0xffff
        for idx, w in enumerate(words):
            if (w & 0x7f800000) in (0x52800000, 0x72800000) and ((w >> 21) & 3) == 0 and ((w >> 5) & 0xffff) == lo:
                near = words[max(0, idx - 8): idx + 8]
                if any(((x & 0x7f800000) in (0x52800000, 0x72800000)) and ((x >> 21) & 3) == 1 and ((x >> 5) & 0xffff) == ((h >> 16) & 0xffff) for x in near):
                    print(n, hex(idx * 4))
elif cmd == 'dis':
    dis(int(sys.argv[3], 16), int(sys.argv[4]))
elif cmd == 'xref':
    t = int(sys.argv[3], 16)
    for ins in md.disasm(data[0:tags.get(0, len(data))] if False else data[:0x200000], 0):
        pass

if cmd == 'calls':
    want = sys.argv[3]
    text_end = struct.unpack_from('<I', data, 0x10 + 0x10 + 4)[0] if False else None
    # find PLT stubs whose target name contains want
    stubs = set()
    for a in range(0, len(data) - 16, 4):
        w = struct.unpack_from('<I', data, a)[0]
        if (w & 0x9f00001f) == 0x90000010:  # adrp x16
            n = plt_target(a)
            if n and want in n:
                stubs.add(a)
    print('stubs', [hex(s) for s in stubs])
    for a in range(0, len(data), 4):
        w = struct.unpack_from('<I', data, a)[0]
        if (w & 0xfc000000) == 0x94000000:
            off = w & 0x3ffffff
            if off & 0x2000000: off -= 0x4000000
            t = a + off * 4
            if t in stubs:
                # show preceding mov w1
                prev = list(md.disasm(data[a-24:a], a-24))
                w1 = [p.op_str for p in prev if p.op_str.startswith('w1,')]
                print(hex(a), w1[-1] if w1 else '?')

if cmd == 'calloffs':
    want = sys.argv[3]
    stubs = set()
    for a in range(0, len(data) - 16, 4):
        w = struct.unpack_from('<I', data, a)[0]
        if (w & 0x9f00001f) == 0x90000010:
            n = plt_target(a)
            if n and want in n:
                stubs.add(a)
    from collections import Counter
    c = Counter()
    for a in range(0, len(data), 4):
        w = struct.unpack_from('<I', data, a)[0]
        if (w & 0xfc000000) == 0x94000000:
            off = w & 0x3ffffff
            if off & 0x2000000: off -= 0x4000000
            if a + off * 4 in stubs:
                prev = list(md.disasm(data[a-48:a], a-48))
                movs = [p.op_str.split('#')[-1] for p in prev if p.mnemonic == 'mov' and p.op_str.startswith(('w8, #0x', 'w9, #0x'))]
                c[movs[-1] if movs else '?'] += 1
                print(hex(a), movs[-1] if movs else '?')
    print(c)
