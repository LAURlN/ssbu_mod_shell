"""P4-BRIDGE-FACTS claim checker.

Re-derives every instruction word cited in research/P4-BRIDGE-FACTS.md and the
structural claims, directly from gamedata/ssbu-13.0.4/main.bin. Exit 0 iff all
checks pass; nonzero on the first mismatch or a failed assertion.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python check_p4.py
"""
import hashlib
import struct
import sys

import lib
from lib import data, word, qword, TEXT, IMAGE, sx

EXPECT_SHA = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'

fails = []
checks = 0


def ck(cond, msg):
    global checks
    checks += 1
    if not cond:
        fails.append(msg)


def ckword(addr, expect, note=''):
    global checks
    checks += 1
    got = word(addr)
    if got != expect:
        fails.append('word 0x%08x: got 0x%08x expected 0x%08x %s' % (addr, got, expect, note))


def pcrel(w):
    return ((w & 0x7C000000) == 0x14000000 or (w & 0xFF000010) == 0x54000000
            or (w & 0x7E000000) == 0x34000000 or (w & 0x7E000000) == 0x36000000
            or (w & 0x9F000000) == 0x10000000 or (w & 0xFF000000) == 0x58000000
            or (w & 0xFF000000) == 0x18000000)


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


def adrp_page(a, w):
    return (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12)


def def_of(reg, a, lo):
    for b in range(a - 4, lo - 4, -4):
        ins = lib.one(b)
        if ins is not None and reg in lib.written(ins):
            return b
    return None


def origin(reg, a, lo, depth=0):
    if depth > 6:
        return None
    d = def_of(reg, a, lo)
    if d is None:
        return None
    w = word(d)
    ins = lib.one(d)
    if (w & 0x9F000000) == 0x90000000:
        return ('adrp', d, adrp_page(d, w), 0)
    if (w & 0xFF800000) == 0x91000000:
        rn = (w >> 5) & 31
        o = origin(rn, d, lo, depth + 1)
        if o and o[0] == 'adrp':
            return ('adrp', o[1], o[2], o[3] + ((w >> 10) & 0xFFF))
        return None
    if (w & 0xFFE0FFE0) == 0xAA0003E0:
        rm = (w >> 16) & 31
        if rm in (19, 23):
            return ('copy', rm, None, None)
        return origin(rm, d, lo, depth + 1)
    return None


# ---- instruction words cited in the report -------------------------------------
# Q1: two-argument invoke thunk 0x19dd950 (to its tail branch) and its cold blocks.
THUNK950 = {
    0x19dd950: 0xd10103ff, 0x19dd954: 0xa90157f6, 0x19dd958: 0xa9024ff4, 0x19dd95c: 0xa9037bfd,
    0x19dd960: 0x9100c3fd, 0x19dd964: 0xf9400828, 0x19dd968: 0xd1008115, 0x19dd96c: 0xb85e8108,
    0x19dd970: 0xaa0103f4, 0x19dd974: 0xaa0003f3, 0x19dd978: 0x71004d1f, 0x19dd97c: 0x54000061,
    0x19dd980: 0xf94002b5, 0x19dd984: 0x14000019, 0x19dd988: 0xb9400aa8, 0x19dd98c: 0x71004d1f,
    0x19dd990: 0x54ffff80, 0x19dd994: 0x71000d1f, 0x19dd998: 0x54000980, 0x19dd99c: 0x12000d08,
    0x19dd9a0: 0x7100111f, 0x19dd9a4: 0x54000201, 0x19dd9a8: 0xf94002a8, 0x19dd9ac: 0x91006100,
    0x19dd9b0: 0x910003e1, 0x19dd9b4: 0x947ca7e7, 0x19dd9b8: 0xf94002a8, 0x19dd9bc: 0x39402109,
    0x19dd9c0: 0x7100113f, 0x19dd9c4: 0x54000061, 0x19dd9c8: 0x39402d08, 0x19dd9cc: 0x14000002,
    0x19dd9d0: 0xf9400908, 0x19dd9d4: 0x91000508, 0x19dd9d8: 0x910003f5, 0x19dd9dc: 0xeb08001f,
    0x19dd9e0: 0x54fffd40, 0x19dd9e4: 0xaa1f03f5, 0x19dd9e8: 0xf9400a88, 0x19dd9ec: 0xd1004116,
    0x19dd9f0: 0xb85f8108, 0x19dd9f4: 0x71004d1f, 0x19dd9f8: 0x54000061, 0x19dd9fc: 0xf94002c2,
    0x19dda00: 0x14000019, 0x19dda04: 0xb9400ac8, 0x19dda08: 0x71004d1f, 0x19dda0c: 0x54ffff80,
    0x19dda10: 0x71000d1f, 0x19dda14: 0x54000720, 0x19dda18: 0x12000d08, 0x19dda1c: 0x7100111f,
    0x19dda20: 0x54000201, 0x19dda24: 0xf94002c8, 0x19dda28: 0x91006100, 0x19dda2c: 0x910003e1,
    0x19dda30: 0x947ca7c8, 0x19dda34: 0xf94002c8, 0x19dda38: 0x39402109, 0x19dda3c: 0x7100113f,
    0x19dda40: 0x54000061, 0x19dda44: 0x39402d08, 0x19dda48: 0x14000002, 0x19dda4c: 0xf9400908,
    0x19dda50: 0x91000508, 0x19dda54: 0x910003f6, 0x19dda58: 0xeb08001f, 0x19dda5c: 0x54fffd40,
    0x19dda60: 0xaa1f03e2, 0x19dda64: 0xf9401288, 0x19dda68: 0xf9400108, 0x19dda6c: 0xf9400a89,
    0x19dda70: 0x91004108, 0x19dda74: 0xeb08013f, 0x19dda78: 0x540000e2, 0x19dda7c: 0x9100412a,
    0x19dda80: 0xf9000a8a, 0x19dda84: 0xb900093f, 0x19dda88: 0xf9400a89, 0x19dda8c: 0xeb08013f,
    0x19dda90: 0x54ffff63, 0x19dda94: 0xf9000a88, 0x19dda98: 0xa9410e68, 0x19dda9c: 0xf9401269,
    0x19ddaa0: 0x8b890500, 0x19ddaa4: 0x36000069, 0x19ddaa8: 0xf9400008, 0x19ddaac: 0xf8636903,
    0x19ddab0: 0x2a1503e1, 0x19ddab4: 0xa9437bfd, 0x19ddab8: 0xa9424ff4, 0x19ddabc: 0xa94157f6,
    0x19ddac0: 0x910103ff, 0x19ddac4: 0xd61f0060, 0x19ddac8: 0xbd4002a0, 0x19ddacc: 0x900154a8,
    0x19ddad0: 0xbd48f501, 0x19ddad4: 0x1e254000, 0x19ddad8: 0x1e212000, 0x19ddadc: 0x54fff84b,
    0x19ddae0: 0x900154a8, 0x19ddae4: 0xbd4e6901, 0x19ddae8: 0x1e212000, 0x19ddaec: 0x54fff7c5,
    0x19ddaf0: 0x9e380015, 0x19ddaf4: 0x17ffffbd, 0x19ddaf8: 0xbd4002c0, 0x19ddafc: 0x900154a8,
    0x19ddb00: 0xbd48f501, 0x19ddb04: 0x1e254000, 0x19ddb08: 0x1e212000, 0x19ddb0c: 0x54fffaab,
    0x19ddb10: 0x900154a8, 0x19ddb14: 0xbd4e6901, 0x19ddb18: 0x1e212000, 0x19ddb1c: 0x54fffa25,
    0x19ddb20: 0x9e380002, 0x19ddb24: 0x17ffffd0,
}

# Q2: one-argument invoke thunk 0x19dd7d0.
THUNK7D0 = {
    0x19dd7d0: 0xd10103ff, 0x19dd7d4: 0xf9000bf5, 0x19dd7d8: 0xa9024ff4, 0x19dd7dc: 0xa9037bfd,
    0x19dd7e0: 0x9100c3fd, 0x19dd7e4: 0xf9400828, 0x19dd7e8: 0xd1004115, 0x19dd7ec: 0xb85f8108,
    0x19dd7f0: 0xaa0103f3, 0x19dd7f4: 0xaa0003f4, 0x19dd7f8: 0x71004d1f, 0x19dd7fc: 0x54000061,
    0x19dd800: 0xf94002a1, 0x19dd804: 0x14000019, 0x19dd808: 0xb9400aa8, 0x19dd80c: 0x71004d1f,
    0x19dd810: 0x54ffff80, 0x19dd814: 0x71000d1f, 0x19dd818: 0x54000780, 0x19dd81c: 0x12000d08,
    0x19dd820: 0x7100111f, 0x19dd824: 0x54000201, 0x19dd828: 0xf94002a8, 0x19dd82c: 0x91006100,
    0x19dd830: 0x910003e1, 0x19dd834: 0x947ca847, 0x19dd838: 0xf94002a8, 0x19dd83c: 0x39402109,
    0x19dd840: 0x7100113f, 0x19dd844: 0x54000061, 0x19dd848: 0x39402d08, 0x19dd84c: 0x14000002,
    0x19dd850: 0xf9400908, 0x19dd854: 0x91000508, 0x19dd858: 0x910003f5, 0x19dd85c: 0xeb08001f,
    0x19dd860: 0x54fffd40, 0x19dd864: 0xaa1f03e1, 0x19dd868: 0xf9401268, 0x19dd86c: 0xf9400108,
    0x19dd870: 0xf9400a69, 0x19dd874: 0x91004108, 0x19dd878: 0xeb08013f, 0x19dd87c: 0x540000e2,
    0x19dd880: 0x9100412a, 0x19dd884: 0xf9000a6a, 0x19dd888: 0xb900093f, 0x19dd88c: 0xf9400a69,
    0x19dd890: 0xeb08013f, 0x19dd894: 0x54ffff63, 0x19dd898: 0xf9000a68, 0x19dd89c: 0xa942ae88,
    0x19dd8a0: 0xf9400a8a, 0x19dd8a4: 0x92400169, 0x19dd8a8: 0xaa08012c, 0x19dd8ac: 0xb400026c,
    0x19dd8b0: 0x8b8b0540, 0x19dd8b4: 0xb4000069, 0x19dd8b8: 0xf9400009, 0x19dd8bc: 0xf8686928,
    0x19dd8c0: 0xd63f0100, 0x19dd8c4: 0xf9400a69, 0x19dd8c8: 0x93407c08, 0x19dd8cc: 0xf9000128,
    0x19dd8d0: 0x52800268, 0x19dd8d4: 0xb9000928, 0x19dd8d8: 0xf9400a68, 0x19dd8dc: 0x91004108,
    0x19dd8e0: 0xf9000a68, 0x19dd8e4: 0xf9400bf5, 0x19dd8e8: 0xa9437bfd, 0x19dd8ec: 0xa9424ff4,
    0x19dd8f0: 0x910103ff, 0x19dd8f4: 0xd65f03c0, 0x19dd8f8: 0xa941a688, 0x19dd8fc: 0x8b890540,
    0x19dd900: 0x3707fdc9, 0x19dd904: 0x17ffffef, 0x19dd908: 0xbd4002a0, 0x19dd90c: 0x900154a8,
    0x19dd910: 0xbd48f501, 0x19dd914: 0x1e254000, 0x19dd918: 0x1e212000, 0x19dd91c: 0x54fffa4b,
    0x19dd920: 0x900154a8, 0x19dd924: 0xbd4e6901, 0x19dd928: 0x1e212000, 0x19dd92c: 0x54fff9c5,
    0x19dd930: 0x9e380001, 0x19dd934: 0x17ffffcd,
}

# Q3/Q4 handler words (whole function incl. cold block, and the two replace functions' first 8).
HANDLERS = {
    0x19dcf20: 0x7100103f, 0x19dcf24: 0x54000082, 0x19dcf28: 0x8b21c008, 0x19dcf2c: 0x39040102,
    0x19dcf30: 0xd65f03c0, 0x19dcf34: 0xa9bf7bfd, 0x19dcf38: 0x910003fd, 0x19dcf3c: 0x947f9459,
    0x19dcf40: 0x7100103f, 0x19dcf44: 0x54000082, 0x19dcf48: 0x8b21c008, 0x19dcf4c: 0x39440100,
    0x19dcf50: 0xd65f03c0, 0x19dcf54: 0xa9bf7bfd, 0x19dcf58: 0x910003fd, 0x19dcf5c: 0x947f9451,
    0x19dd1a0: 0xd10103ff, 0x19dd1a4: 0xf9000bf5, 0x19dd1a8: 0xa9024ff4, 0x19dd1ac: 0xa9037bfd,
    0x19dd1b0: 0x9100c3fd, 0x19dd1b4: 0xaa0003f5, 0x19dd1b8: 0xf8410c08, 0x19dd1bc: 0xf9400409,
    0x19dd244: 0x947f8ecf,
    0x19dd250: 0xd101c3ff, 0x19dd254: 0xf90013f9, 0x19dd258: 0xa9035ff8, 0x19dd25c: 0xa90457f6,
    0x19dd260: 0xa9054ff4, 0x19dd264: 0xa9067bfd, 0x19dd268: 0x910183fd, 0x19dd26c: 0xaa0003f4,
    0x19dd46c: 0x947f8e45, 0x19dd470: 0xb4000040, 0x19dd474: 0x147d4447, 0x19dd478: 0xd65f03c0,
}

# Registration / handler-address construction and the cold-block target stub.
MISC = {
    0x19de0ec: 0x9001b655, 0x19de0f0: 0x9139e2b5, 0x19de0f4: 0xd0ffffe8, 0x19de0f8: 0x913c8108,
    0x19de0fc: 0xf9000015, 0x19de100: 0xf900101f, 0x19de104: 0xa9012013,
    0x19de19c: 0xd0ffffe9, 0x19de1a0: 0x913d0129, 0x19de1a4: 0xf9000008, 0x19de1a8: 0x320003e8,
    0x19de1ac: 0xa9017c13, 0x19de1b0: 0xf900181f, 0x19de1b4: 0xa902241f,
    0x19de39c: 0xf0ffffe8, 0x19de3a0: 0x91068108, 0x19de3a8: 0xa9012013,
    0x19de444: 0xf0ffffe9, 0x19de448: 0x91094129, 0x19de454: 0xa9012413,
    0x39c20a0: 0xb000c6f0, 0x39c20a4: 0xf9410611, 0x39c20a8: 0x91082210, 0x39c20ac: 0xd61f0220,
    0x39c20b0: 0xb000c6f0, 0x39c20b4: 0xf9410a11, 0x39c20b8: 0x91084210, 0x39c20bc: 0xd61f0220,
    0x39c20c0: 0xb000c6f0, 0x39c20c4: 0xf9410e11, 0x39c20c8: 0x91086210, 0x39c20cc: 0xd61f0220,
    0x180fca8: 0xf001d7b5, 0x180fcac: 0x912de2b5, 0x180fcb0: 0xaa1503e2, 0x180fcb4: 0x97fee157,
    0x180d31c: 0xb001d7da, 0x180d320: 0xb94b7b41, 0x180d324: 0xaa1503e0, 0x180d328: 0x97feec82,
    0x19ddd80: 0xf90042f3, 0x19ddc04: 0xaa1303fa, 0x19ddc08: 0xf8030d1f,
    0x19ddb94: 0xaa0003f3, 0x19ddb80: 0x52802a01, 0x19ddb88: 0xa904fc1f,
    0x19ddb8c: 0x321c03e0, 0x19ddb90: 0x947d4054,
}

# adrp+add materialisations of 0x5306b78 (Q6).
XREF_5306B78 = sorted([
    (0x01809a94, 0x01809a98), (0x0180d41c, 0x0180d420), (0x0180d6d4, 0x0180d6d8),
    (0x0180d6f8, 0x0180d6fc), (0x0180d864, 0x0180d868), (0x0180d8a4, 0x0180d8bc),
    (0x0180d8b8, 0x0180d8bc), (0x0180fc4c, 0x0180fc50), (0x0180fca8, 0x0180fcac),
    (0x01812b24, 0x01812b28), (0x0181506c, 0x01815070), (0x019cadc4, 0x019cadc8),
    (0x022f7e34, 0x022f7e38), (0x022f8f64, 0x022f8f68),
])


def main():
    h = hashlib.sha256(data).hexdigest()
    ck(h == EXPECT_SHA, 'input sha256 %s != %s' % (h, EXPECT_SHA))

    for table, name in ((THUNK950, 'THUNK950'), (THUNK7D0, 'THUNK7D0'),
                        (HANDLERS, 'HANDLERS'), (MISC, 'MISC')):
        for a, w in table.items():
            ckword(a, w, name)

    # constants used by the float path
    ck(word(0x44718f4) == 0xdf000000, '0x44718f4 != 0xdf000000')
    ck(word(0x4471e68) == 0x5f000000, '0x4471e68 != 0x5f000000')

    # PC-relative classification of the first four handler words
    for start in (0x19dcf20, 0x19dcf40):
        got = [pcrel(word(start + 4 * i)) for i in range(4)]
        ck(got == [False, True, False, False], 'pcrel first-4 of 0x%x = %r' % (start, got))
    for start in (0x19dd1a0, 0x19dd250):
        got = [pcrel(word(start + 4 * i)) for i in range(8)]
        ck(got == [False] * 8, 'pcrel first-8 of 0x%x = %r' % (start, got))

    # single pass: inbound direct branches + adrp+add completions for 0x5306b78
    ranges = [(0x19dcf20, 0x19dcf40), (0x19dcf40, 0x19dcf54),
              (0x19dd1a0, 0x19dd24c), (0x19dd250, 0x19dd480)]
    inbound = {r: [] for r in ranges}
    xref = []
    page = 0x5306b78 & ~0xFFF
    lo = 0x5306b78 & 0xFFF
    for a in range(TEXT[0], TEXT[1], 4):
        w = word(a)
        t = btarget(a, w)
        if t is not None:
            for r0, r1 in ranges:
                if r0 <= t < r1:
                    inbound[(r0, r1)].append((a, t))
        if (w & 0x9F000000) == 0x90000000 and adrp_page(a, w) == page:
            rd = w & 31
            for j in range(1, 8):
                w2 = word(a + 4 * j)
                if (w2 & 0xFF800000) == 0x91000000 and ((w2 >> 5) & 31) == rd and ((w2 >> 10) & 0xFFF) == lo:
                    xref.append((a, a + 4 * j))

    ck(inbound[(0x19dcf20, 0x19dcf40)] == [(0x19dcf24, 0x19dcf34)],
       'set_skill_id inbound = %r' % inbound[(0x19dcf20, 0x19dcf40)])
    ck(inbound[(0x19dcf40, 0x19dcf54)] == [], 'get_skill_id inbound = %r' % inbound[(0x19dcf40, 0x19dcf54)])
    rp = inbound[(0x19dd1a0, 0x19dd24c)]
    ck(sorted(rp) == [(0x19dd1c4, 0x19dd244), (0x19dd224, 0x19dd230)],
       'replace_skill inbound = %r' % rp)
    sub = inbound[(0x19dd250, 0x19dd480)]
    ck(len(sub) == 11, 'replace_skill_subwindow inbound count = %d' % len(sub))
    ck(sorted(xref) == XREF_5306B78, '0x5306b78 xref list mismatch: %r' % sorted(xref))

    # relocated pointers equal to the four function starts must not exist
    for target in (0x19dcf20, 0x19dcf40, 0x19dd1a0, 0x19dd250):
        pat = struct.pack('<Q', target)
        i, found = 0, []
        while True:
            i = data.find(pat, i)
            if i < 0:
                break
            if i >= 0x10 and struct.unpack_from('<I', data, i - 0x10 + 8)[0] == 0x403 \
                    and struct.unpack_from('<I', data, i - 0x10 + 0xC)[0] == 0:
                found.append(i - 0x10)
            i += 1
        ck(found == [], 'reloc addend==0x%x found at %r' % (target, found))

    # Q5: no store with an adrp-derived base in 0x19ddb30..0x19de6b0 carries x19/x23.
    start, end = 0x19ddb30, 0x19de6b0
    total, carry = 0, 0
    for a in range(start, end, 4):
        ins = lib.one(a)
        if ins is None:
            continue
        m = ins.mnemonic
        if m in ('str', 'strb', 'strh', 'stur', 'sturb', 'sturh'):
            rts, rn = [word(a) & 31], (word(a) >> 5) & 31
        elif m in ('stp', 'stnp'):
            rts, rn = [word(a) & 31, (word(a) >> 10) & 31], (word(a) >> 5) & 31
        else:
            continue
        o = origin(rn, a, start)
        if not o or o[0] != 'adrp':
            continue
        total += 1
        for rt in rts:
            if rt in (19, 23):
                carry += 1
            od = origin(rt, a, start)
            if od and od[0] == 'copy' and od[1] in (19, 23):
                carry += 1
    ck(total == 0, 'Q5 adrp-derived stores in 0x19ddb30 = %d (expected 0)' % total)
    ck(carry == 0, 'Q5 adrp-derived stores carrying x19/x23 = %d' % carry)

    # Q6: the two named sites really resolve to 0x5306b78
    ck(adrp_page(0x180fca8, word(0x180fca8)) + ((word(0x180fcac) >> 10) & 0xFFF) == 0x5306b78,
       '0x180fca8/0x180fcac does not resolve to 0x5306b78')
    ck(adrp_page(0x180d31c, word(0x180d31c)) + 0xb78 == 0x5306b78,
       '0x180d31c + 0xb78 does not resolve to 0x5306b78')
    ck((word(0x180d320) >> 5) & 31 == 26 and ((word(0x180d320) >> 10) & 0xFFF) * 4 == 0xb78,
       '0x180d320 is not ldr [x26,#0xb78]')

    # 0x39c20a0 first 12 instructions contain no ret; terminal instruction of each stub is br x17.
    for a in (0x39c20ac, 0x39c20bc, 0x39c20cc):
        ck(word(a) == 0xd61f0220, '0x%x is not br x17' % a)
    ck(all((word(0x39c20a0 + 4 * i) & 0xFFFFFC1F) != 0xD65F0000 for i in range(12)),
       '0x39c20a0 window contains a ret')

    # --- report ---
    print('P4-BRIDGE-FACTS checks: %d run, %d failed' % (checks, len(fails)))
    for f in fails:
        print('  FAIL:', f)
    if fails:
        sys.exit(1)
    print('all passed, exit 0')


if __name__ == '__main__':
    main()
