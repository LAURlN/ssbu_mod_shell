"""Q5 cross-check: backward register provenance instead of forward tracking.

For every store in 0x19ddb30..0x19de6b0, find the most recent definition of its base
register; if that chain roots in an `adrp`, report the store. Also reports whether the
stored data register is x19, x23, a copy, or something else.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python q5_backward.py
"""
import lib
from lib import word, text, one, written, sx

START, END = 0x19ddb30, 0x19de6b0


def adrp_page(a):
    w = word(a)
    return (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12)


def def_of(reg, a, depth=0):
    """Most recent instruction at or before a that writes reg, walking backward."""
    if depth > 4:
        return None
    for b in range(a - 4, START - 4, -4):
        ins = one(b)
        if ins is None:
            continue
        if reg in written(ins):
            return b
    return None


def origin(reg, a, seen=None, depth=0):
    """Return ('adrp', addr, base, off) if reg traces to an adrp; ('copy', src) if mov from 19/23."""
    if depth > 6:
        return None
    d = def_of(reg, a)
    if d is None:
        return None
    w = word(d)
    m = one(d).mnemonic if one(d) else ''
    if (w & 0x9F000000) == 0x90000000:            # adrp
        return ('adrp', d, adrp_page(d), 0)
    if (w & 0xFF800000) == 0x91000000:            # add rd, rn, #imm
        rd, rn = w & 31, (w >> 5) & 31
        o = origin(rn, d, seen, depth + 1)
        if o and o[0] == 'adrp':
            return ('adrp', o[1], o[2], o[3] + ((w >> 10) & 0xFFF))
        return None
    if (w & 0xFFE0FFE0) == 0xAA0003E0:            # mov rd, rm
        rm = (w >> 16) & 31
        if rm in (19, 23):
            return ('copy', rm, None, None)
        return origin(rm, d, seen, depth + 1)
    return None


def main():
    total = 0
    carry = 0
    print('stores in 0x%x..0x%x whose base traces to an adrp:' % (START, END))
    for a in range(START, END, 4):
        ins = one(a)
        if ins is None:
            continue
        m = ins.mnemonic
        if m in ('str', 'strb', 'strh', 'stur', 'sturb', 'sturh'):
            rts, rn = [word(a) & 31], (word(a) >> 5) & 31
        elif m in ('stp', 'stnp'):
            rts, rn = [word(a) & 31, (word(a) >> 10) & 31], (word(a) >> 5) & 31
        else:
            continue
        o = origin(rn, a)
        if not o or o[0] != 'adrp':
            continue
        total += 1
        dat = []
        for rt in rts:
            od = origin(rt, a)
            tag = ''
            if rt == 19:
                tag = 'x19'
            elif rt == 23:
                tag = 'x23'
            elif od and od[0] == 'copy':
                tag = 'copy-of-x%d' % od[1]
            if tag in ('x19', 'x23') or (od and od[0] == 'copy' and od[1] in (19, 23)):
                carry += 1
            dat.append('x%d%s' % (rt, '(%s)' % tag if tag else ''))
        print('0x%08x: %-5s data %-22s base=x%d -> adrp 0x%08x + 0x%x = 0x%x  [%s]'
              % (a, m, ','.join(dat), rn, o[1], o[3], o[2] + o[3], text(a)))
    print('total adrp-derived stores:', total)
    print('of those carrying x19/x23 (direct or copy):', carry)


if __name__ == '__main__':
    main()
