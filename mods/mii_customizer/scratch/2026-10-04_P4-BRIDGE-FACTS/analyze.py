"""P4-BRIDGE-FACTS static analyzer (read-only).

Reads only gamedata/ssbu-13.0.4/main.bin (flat MOD0 image, address == file offset).
Prints facts; writes no files.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python analyze.py
"""
import struct

import lib
from lib import data, word, qword, dis, text, TEXT, sx


def pcrel(w):
    """True if the encoding is PC-relative (B/BL/B.cond/CBZ/CBNZ/TBZ/TBNZ/ADR/ADRP/LDR-literal)."""
    return ((w & 0x7C000000) == 0x14000000        # B / BL
            or (w & 0xFF000010) == 0x54000000     # B.cond
            or (w & 0x7E000000) == 0x34000000     # CBZ / CBNZ
            or (w & 0x7E000000) == 0x36000000     # TBZ / TBNZ
            or (w & 0x9F000000) == 0x10000000     # ADR / ADRP
            or (w & 0xFF000000) == 0x58000000     # LDR literal 64
            or (w & 0xFF000000) == 0x18000000)    # LDR literal 32


def btarget(a, w):
    if (w & 0x7C000000) == 0x14000000:
        return a + (sx(w & 0x3FFFFFF, 26) << 2)
    if (w & 0xFF000010) == 0x54000000:
        return a + (sx((w >> 5) & 0x7FFFF, 19) << 2)
    if (w & 0x7E000000) == 0x34000000:
        return a + (sx((w >> 5) & 0x7FFFF, 19) << 2)
    if (w & 0x7E000000) == 0x36000000:
        return a + (sx((w >> 5) & 0x3FFF, 14) << 2)
    return None


def branchscan(start, end):
    """All direct branches/calls in TEXT whose target is in [start, end)."""
    out = []
    for a in range(TEXT[0], TEXT[1], 4):
        w = word(a)
        t = btarget(a, w)
        if t is not None and start <= t < end:
            out.append((a, w, t))
    return out


def reloc_addends(target):
    """Records (r_offset, file_off) whose R_AARCH64_RELATIVE addend == target."""
    pat = struct.pack('<Q', target)
    hits, i = [], 0
    while True:
        i = data.find(pat, i)
        if i < 0:
            return hits
        if i >= 0x10:
            off = i - 0x10
            info = struct.unpack_from('<I', data, off + 8)[0]
            pad = struct.unpack_from('<I', data, off + 0xC)[0]
            if info == 0x403 and pad == 0:
                hits.append((qword(off), off))
        i += 1


def rawptr(target):
    """8-byte-aligned occurrences of the raw value in the file (unrelocated)."""
    pat = struct.pack('<Q', target)
    hits, i = [], 0
    while True:
        i = data.find(pat, i)
        if i < 0:
            return hits
        if i % 8 == 0:
            hits.append(i)
        i += 1


def adrp_target(a, w):
    return (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12)


def show_func(name, start, end):
    print('==== %s 0x%x .. 0x%x ====' % (name, start, end))
    n = (end - start) // 4
    print('first-4 pcrel:', [(i, pcrel(word(start + 4 * i))) for i in range(4)])
    for k in range(n):
        a = start + 4 * k
        w = word(a)
        print('0x%08x: %08x  %s' % (a, w, text(a)))
    print('inbound branches/calls into [0x%x,0x%x):' % (start, end))
    for a, w, t in branchscan(start, end):
        print('   0x%08x  %s -> 0x%x  (target inside)' % (a, text(a), t))


def q3():
    show_func('set_skill_id', 0x19dcf20, 0x19dcf40)
    print()
    show_func('get_skill_id', 0x19dcf40, 0x19dcf54)
    print()
    for tgt in (0x19dcf20, 0x19dcf40):
        print('reloc addend==0x%x:' % tgt, reloc_addends(tgt))
        print('raw qword==0x%x:' % tgt, rawptr(tgt))
    print('--- 0x39c20a0 first 20 insns ---')
    for k in range(20):
        a = 0x39c20a0 + 4 * k
        print('0x%08x: %08x  %s' % (a, word(a), text(a)))


def q4():
    show_func('replace_skill', 0x19dd1a0, 0x19dd24c)
    print()
    show_func('replace_skill_subwindow', 0x19dd250, 0x19dd474)
    print()
    for tgt in (0x19dd1a0, 0x19dd250):
        print('reloc addend==0x%x:' % tgt, reloc_addends(tgt))
        print('raw qword==0x%x:' % tgt, rawptr(tgt))


def q5():
    """Walk 0x19ddb30..0x19de6b0; report stores to adrp-derived bases, flag any x19/x23 value.

    Tracking is invalidated whenever a register is written by any instruction, so a
    reused scratch register is not mistaken for a live adrp base.
    """
    start, end = 0x19ddb30, 0x19de6b0
    adrp_base = {}   # reg -> materialised address (adrp alone or adrp+add)
    alias = {}       # reg -> source of a copy: 19 or 23
    adrp_store_hits = []
    for a in range(start, end, 4):
        w = word(a)
        ins = lib.one(a)
        if ins is None:
            continue
        m = ins.mnemonic
        wr = lib.written(ins)
        # --- store check uses the state before this instruction updates registers ---
        if m in ('str', 'strb', 'strh', 'stur', 'sturb', 'sturh'):
            rt, rn = w & 31, (w >> 5) & 31
            if rn in adrp_base:
                adrp_store_hits.append((a, m, rt, alias.get(rt), adrp_base[rn]))
        elif m in ('stp', 'stnp'):
            rt, rt2, rn = w & 31, (w >> 10) & 31, (w >> 5) & 31
            if rn in adrp_base:
                for r in (rt, rt2):
                    adrp_store_hits.append((a, m, r, alias.get(r), adrp_base[rn]))
        # --- update tracking ---
        if (w & 0x9F000000) == 0x90000000:            # adrp
            adrp_base[w & 31] = adrp_target(a, w)
        elif (w & 0xFF800000) == 0x91000000:          # add
            rd, rn = w & 31, (w >> 5) & 31
            if rn in adrp_base:
                adrp_base[rd] = adrp_base[rn] + ((w >> 10) & 0xFFF)
            else:
                adrp_base.pop(rd, None)
        else:
            for r in wr:
                adrp_base.pop(r, None)
        # alias tracking
        for r in wr:
            alias.pop(r, None)
        if (w & 0xFFE0FFE0) == 0xAA0003E0:            # mov xD, xN
            rd, rm = w & 31, (w >> 16) & 31
            if rm in (19, 23):
                alias[rd] = rm
            elif rm in alias:
                alias[rd] = alias[rm]
    print('all stores with an adrp-derived base in 0x%x..0x%x:' % (start, end))
    for a, mn, rt, al, base in adrp_store_hits:
        tag = ''
        if rt == 19 or al == 19:
            tag = '   <== x19'
        if rt == 23 or al == 23:
            tag += '   <== x23'
        print('0x%08x: %-5s data x%d%s  base 0x%x%s'
              % (a, mn, rt, ('(copy of x%d)' % al) if al else '', base, tag))
    print('adrp-derived stores carrying x19 or x23:',
          sum(1 for h in adrp_store_hits if h[2] in (19, 23) or h[3] in (19, 23)))


def xref_add(target):
    """adrp+add completions whose computed address == target."""
    page, lo = target & ~0xFFF, target & 0xFFF
    hits = []
    for a in range(TEXT[0], TEXT[1], 4):
        w = word(a)
        if (w & 0x9F000000) != 0x90000000:
            continue
        if adrp_target(a, w) != page:
            continue
        rd = w & 31
        for j in range(1, 8):
            w2 = word(a + 4 * j)
            if (w2 & 0xFF800000) == 0x91000000 and ((w2 >> 5) & 31) == rd and ((w2 >> 10) & 0xFFF) == lo:
                hits.append((a, a + 4 * j))
    return hits


def q6():
    for a in range(0x180fca8, 0x180fcb8, 4):
        print('0x%08x: %08x  %s' % (a, word(a), text(a)))
    print()
    for a in range(0x180d320, 0x180d32c, 4):
        print('0x%08x: %08x  %s' % (a, word(a), text(a)))
    print()
    hits = xref_add(0x5306b78)
    print('adrp+add materialisations of exactly 0x5306b78:', len(hits))
    for ad, ad2 in hits:
        print('   adrp 0x%08x  add 0x%08x' % (ad, ad2))


def show_thunk(name, start, end):
    print('==== %s 0x%x .. 0x%x ====' % (name, start, end))
    for a in range(start, end, 4):
        print('0x%08x: %08x  %s' % (a, word(a), text(a)))
    print()


if __name__ == '__main__':
    q3()
    print('\n\n######## Q4 ########')
    q4()
    print('\n\n######## Q5 ########')
    q5()
    print('\n\n######## Q6 ########')
    q6()
    print('\n\n######## registration 0x19de1a0 ########')
    for a in range(0x19de1a0, 0x19de1c4, 4):
        print('0x%08x: %08x  %s' % (a, word(a), text(a)))
    print('\n######## set_skill_id handler build 0x19de0e0 ########')
    for a in range(0x19de0e0, 0x19de110, 4):
        print('0x%08x: %08x  %s' % (a, word(a), text(a)))
