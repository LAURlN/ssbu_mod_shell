#!/usr/bin/env python3
"""Scratch disassembly helper (capstone from the other mod's build cache, read-only).

  mcdis.py <file> dis <hex addr> <count>
  mcdis.py <file> blxref <hex target>          every bl/b to target
  mcdis.py <file> const <hex value>            movz/movk sequences building the 40-bit constant
  mcdis.py <file> plt <substring>              (NRO) PLT stubs whose import name contains substring
  mcdis.py <file> func <hex addr>              start of the function containing addr (sub sp / stp x29 scan)
"""
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
WS = HERE.parents[4]
sys.path.insert(0, str(WS / 'mods/ssbu_mod_new/builds/.cache/dk_cargo/python'))
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM  # noqa: E402

path = sys.argv[1]
data = Path(path).read_bytes()
md = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
is_nro = data[0x10:0x14] == b'NRO0'
got_names = {}
exports = {}
if is_nro:
    mod0 = struct.unpack_from('<I', data, 4)[0]
    dyn = mod0 + struct.unpack_from('<I', data, mod0 + 4)[0]
    tags = {}
    i = dyn
    while True:
        t, v = struct.unpack_from('<qQ', data, i)
        i += 16
        if t == 0:
            break
        tags.setdefault(t, v)
    symtab, strtab = tags[6], tags[5]

    def cstr(o):
        return data[o:data.index(b'\0', o)].decode('latin1')

    def sym(idx):
        name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', data, symtab + idx * 24)
        return cstr(strtab + name), value, shndx
    for rel_tag, sz_tag in ((23, 2), (7, 8)):
        if rel_tag not in tags:
            continue
        off, size = tags[rel_tag], tags[sz_tag]
        for k in range(0, size, 24):
            r_off, r_info, addend = struct.unpack_from('<QQq', data, off + k)
            s = r_info >> 32
            if s:
                n, v, sh = sym(s)
                got_names[r_off] = n
    k = 1
    while symtab + k * 24 < strtab:
        n, v, sh = sym(k)
        if sh and v:
            exports[v] = n
        k += 1


def plt_target(addr):
    if not is_nro or addr + 16 > len(data):
        return None
    w0, w1 = struct.unpack_from('<II', data, addr)
    if (w0 & 0x9f00001f) != 0x90000010 or (w1 & 0xffc003ff) != 0xf9400211:
        return None
    immlo = (w0 >> 29) & 3
    immhi = (w0 >> 5) & 0x7ffff
    page = ((addr >> 12) << 12) + (((immhi << 2) | immlo) << 12)
    slot = page + ((w1 >> 10) & 0xfff) * 8
    return got_names.get(slot)


def dis(addr, count):
    for ins in md.disasm(data[addr:addr + count * 4], addr):
        extra = ''
        if ins.mnemonic in ('bl', 'b'):
            t = int(ins.op_str.lstrip('#'), 16)
            nm = plt_target(t) or exports.get(t)
            if nm:
                extra = '  ; ' + nm[:110]
        print(f'{ins.address:08x}: {ins.mnemonic:8s} {ins.op_str}{extra}')


cmd = sys.argv[2]
if cmd == 'dis':
    dis(int(sys.argv[3], 16), int(sys.argv[4]))
elif cmd == 'blxref':
    t = int(sys.argv[3], 16)
    n = len(data) // 4
    words = struct.unpack_from('<%dI' % n, data)
    for idx, w in enumerate(words):
        if (w & 0x7c000000) == 0x14000000:
            off = w & 0x3ffffff
            if off & 0x2000000:
                off -= 0x4000000
            if idx * 4 + off * 4 == t:
                print(hex(idx * 4), 'bl' if w & 0x80000000 else 'b')
elif cmd == 'const':
    h = int(sys.argv[3], 16)
    n = len(data) // 4
    words = struct.unpack_from('<%dI' % n, data)
    lo, mid, hi = h & 0xffff, (h >> 16) & 0xffff, (h >> 32) & 0xffff
    for idx, w in enumerate(words):
        # movz xN, #lo
        if (w & 0xffe00000) == 0xd2800000 and ((w >> 5) & 0xffff) == lo:
            reg = w & 31
            near = words[idx + 1: idx + 4]
            if any((x & 0xffe0001f) == (0xf2a00000 | reg) and ((x >> 5) & 0xffff) == mid for x in near) and \
               any((x & 0xffe0001f) == (0xf2c00000 | reg) and ((x >> 5) & 0xffff) == hi for x in near):
                print(hex(idx * 4))
elif cmd == 'plt':
    want = sys.argv[3]
    for a in range(0, len(data) - 16, 4):
        nm = plt_target(a)
        if nm and want in nm:
            print(hex(a), nm)
elif cmd == 'func':
    a = int(sys.argv[3], 16)
    while a > 0:
        w = struct.unpack_from('<I', data, a)[0]
        p = struct.unpack_from('<I', data, a - 4)[0]
        if p in (0xd65f03c0, 0, 0xd503201f) or (p & 0xfc000000) == 0x14000000:
            if (w & 0xff0003ff) == 0xd10003ff or (w & 0xffc003e0) == 0xa98003e0 or (w & 0xffc07fff) == 0xa9807bfd or (w & 0xff00001f) in (0xf800001f,) or (w & 0xffe00c00) == 0xf8000c00:
                print(hex(a))
                break
        a -= 4
