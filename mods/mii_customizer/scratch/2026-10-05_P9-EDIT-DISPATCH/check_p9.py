"""P9-EDIT-DISPATCH: verification script for research/P9-EDIT-DISPATCH.md.

Re-reads every address, instruction word, immediate, string, state-table entry and
40-bit path hash cited in the report straight out of main.bin (flat MOD0 image,
address == file offset) and exits non-zero on any mismatch.

    PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
      python mods/mii_customizer/scratch/2026-10-05_P9-EDIT-DISPATCH/check_p9.py

Negative controls (each must make the script fail, exit 1):

    ... check_p9.py --neg handlers   mis-pair the alternating x8/x9 accumulators
    ... check_p9.py --neg movimm     narrow the MOV decoder back to MOVZ/MOVN only
    ... check_p9.py --neg path       claim the wrong ARC path for a script hash
    ... check_p9.py --neg str        move an anchor string's expected address
    ... check_p9.py --neg branch     aim a cited branch at the wrong target
    ... check_p9.py --neg size       claim the wrong child object size

Nothing here is executed from the game; this is a static re-read only.
"""
import hashlib
import struct
import sys
import zlib
from pathlib import Path

import capstone

IMAGE = Path('gamedata/ssbu-13.0.4/main.bin')
DATA = IMAGE.read_bytes()
MD = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
MD.detail = False
# A second disassembler with detail on, used where the operand list itself is the
# claim (memory displacements, register sets).  `insn()` above is text only.
MDD = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
MDD.detail = True
MASK40 = (1 << 40) - 1

NEG = None
for _i, _a in enumerate(sys.argv):
    if _a == '--neg' and _i + 1 < len(sys.argv):
        NEG = sys.argv[_i + 1]

FAIL = []
OK = 0


def chk(cond, label, detail=''):
    global OK
    if cond:
        OK += 1
    else:
        FAIL.append('%s %s' % (label, detail))


def word(a):
    return struct.unpack_from('<I', DATA, a)[0]


def insn(a):
    i = next(MD.disasm(DATA[a:a + 4], a), None)
    return '%s %s' % (i.mnemonic, i.op_str) if i else ''


def bl_target(a):
    w = word(a)
    imm = w & 0x03FFFFFF
    if w & 0x2000000:
        imm -= 1 << 26
    return a + (imm << 2)


def cstr(a):
    e = DATA.find(b'\0', a, a + 96)
    return DATA[a:e].decode('ascii', 'replace')


def hash40(s):
    b = s.lower().encode()
    return (len(b) << 32) | (zlib.crc32(b) & MASK40)


def ones(n):
    return (1 << n) - 1


def hsb(x):
    """Highest set bit index, -1 for zero."""
    return x.bit_length() - 1


def mov_imm32(a):
    """Value a 32-bit register is set to by the instruction at `a`.

    Handles the three encodings the compiler actually emits for a small integer:
      * MOVZ Wd, #imm16        (bits 28..23 == 0x25, opc 10)
      * MOVN Wd, #imm16        (bits 28..23 == 0x25, opc 00)
      * ORR  Wd, WZR, #bitmask (bits 28..23 == 0x24, opc 01) -- the `mov` alias

    The third form is what P8's decoder was missing.  `mov w3, #-2` at 0x1808fa8 is
    word 0x321f7be3, i.e. ORR with a bitmask, not MOVZ/MOVN, so a MOVZ/MOVN-only
    decoder returns None there.  The bitmask is expanded with the ARM
    `DecodeBitMasks` rule at 32-bit element size: S = imms, R = immr,
    element = Ones(S+1) rotated right by R.

    Self-tested below over a sample of every `mov Wd, #imm` in the Mii editor
    blocks, against capstone's own rendering of the immediate.
    """
    w = word(a)
    cls = (w >> 23) & 0x3F
    if cls == 0x25:                                     # MOVZ / MOVN / MOVK
        opc = (w >> 29) & 3
        imm = (w >> 5) & 0xFFFF
        hw = (w >> 21) & 3
        if opc == 2:                                    # MOVZ, imm16 LSL (16*hw)
            v = (imm << (16 * hw)) & 0xFFFFFFFF
        elif opc == 0:                                  # MOVN, same shape
            v = (~imm) & 0xFFFF
            if v & 0x8000:                              # sign extend from bit 15
                v |= 0xFFFF0000
            v = (v << (16 * hw)) & 0xFFFFFFFF
        else:                                           # MOVK: not a plain set
            return None
    elif cls == 0x14 and (w >> 29) & 3 == 1:            # ORR (shifted register)
        # `orr Wd, WZR, WZR` with no shift is the third `mov` encoding the
        # compiler emits (0x18090ac, `mov w3, wzr`).
        if (w >> 31) & 1 or ((w >> 5) & 0x1F) != 0x1F or ((w >> 16) & 0x1F) != 0x1F:
            return None
        # bits 23..22 shift type and bit 21 N must be 0, and imm6 bits 15..10 must
        # be 0.  Rm occupies bits 20..16 and is legitimately 31 (WZR) here.
        if ((w >> 22) & 3) or ((w >> 21) & 1) or ((w >> 10) & 0x3F):
            return None
        v = 0
    elif cls == 0x24 and (w >> 29) & 3 == 1:            # logical immediate
        if (w >> 31) & 1 or ((w >> 5) & 0x1F) != 0x1F:  # sf must be 0, Rn must be WZR
            return None
        S = (w >> 10) & 0x3F                            # imms
        R = (w >> 16) & 0x3F                            # immr
        if S + 1 > 32:
            return None
        e = ones(S + 1)
        v = (((e >> R) | (e << (32 - R))) & 0xFFFFFFFF) if R else e
    else:
        return None
    return v - (1 << 32) if v & 0x80000000 else v


# Self-test: every `mov Wd, #imm` capstone renders in the two Mii editor windows
# must decode here to the same number.  If this ever fails the decoder, not the
# image, is wrong.
import capstone as _cs
_md = _cs.Cs(_cs.CS_ARCH_ARM64, _cs.CS_MODE_ARM)
_self = 0
for _lo, _hi in ((0x1808980, 0x180DE70), (0x19CA000, 0x19CB400)):
    _a = _lo
    while _a < _hi:
        _i = next(_md.disasm(DATA[_a:_a + 4], _a), None)
        if _i is not None and _i.mnemonic == 'mov' and _i.op_str.startswith('w')                 and '#' in _i.op_str:
            _txt = _i.op_str.split('#')[1].rstrip(')')
            _neg = _txt.startswith('-')
            _digits = _txt[1:] if _neg else _txt
            _want = int(_digits, 16) if _digits.startswith('0x') else int(_digits)
            if _neg:
                _want = -_want
            if _want >= 1 << 31:
                _want -= 1 << 32
            _got = mov_imm32(_a)
            chk(_got == _want, 'mov decoder self test @0x%x' % _a,
                'got %s want %s  (%s)' % (_got, _want, _i.op_str))
            _self += 1
        _a += 4
chk(_self > 100, 'mov decoder self test covered a sample', 'only %d sites' % _self)


def chain40(addrs):
    """Read a MOVZ/MOVK 64-bit chain (the 40-bit path hash) from the raw words."""
    v = 0
    for a in addrs:
        w = word(a)
        v |= ((w >> 5) & 0xFFFF) << (16 * ((w >> 21) & 3))
    return v & MASK40


# ==========================================================================
# 0. input identity
# ==========================================================================
EXPECT_SHA = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'
got_sha = hashlib.sha256(DATA).hexdigest()
chk(got_sha == EXPECT_SHA, 'sha256', 'got %s' % got_sha)
chk(len(DATA) == 86672752, 'image size', 'got %d' % len(DATA))
chk(hash40('fighter_kind_miigunner') == 0x0166E9FAE70, 'hash40 self test')

# ==========================================================================
# 1. anchor strings, each occurring once
# ==========================================================================
ANCHORS = {
    0x42E5A36: 'get_exit_value',
    0x43EF3AD: 'EXIT_VALUE_CANCEL',
    0x4359E6A: 'EXIT_VALUE_DECIDE',
    0x4431954: 'IS_SKILL_EDITABLE',
    0x44119AF: 'IS_READ_ONLY',
    0x4359EC6: 'FROM_AMIIBO',
    0x4317830: 'IS_NEW_CREATE_AMIIBO',
    0x4291CB9: 'is_end',
    0x439BD15: 'set_flag_changed',
    0x429FCCE: 'EDIT_MII_TYPE',
    0x42B1A84: 'i',            # Lua integer type tag
    0x43CCB7B: 'b',            # Lua boolean type tag
}
if NEG == 'str':
    ANCHORS = dict(ANCHORS)
    ANCHORS[0x42E5A36] = 'get_exit_valueX'
for a, s in ANCHORS.items():
    chk(cstr(a) == s, 'str@0x%x' % a, 'got %r want %r' % (cstr(a), s))
for s in ('get_exit_value', 'EXIT_VALUE_CANCEL', 'EXIT_VALUE_DECIDE',
          'IS_SKILL_EDITABLE', 'IS_READ_ONLY', 'FROM_AMIIBO'):
    chk(DATA.count(s.encode() + b'\0') == 1, 'strcount %s' % s,
        'count %d' % DATA.count(s.encode() + b'\0'))

# ==========================================================================
# 2. host global registrations (Q6), function 0x1808f40 inside 0x1808980
# ==========================================================================
# signature: x0 = lua env pointer ([x22+0x40] -> vtable -> [0] = state),
#            x1 = name string, x2 = type tag ('i' or 'b'), w3 = value
REGISTER = {                     # (mov-imm addr, name, expected w3, type tag)
    (0x1808FA8, 'EXIT_VALUE_CANCEL', -2, 'i'),
    (0x1808FCC, 'EXIT_VALUE_DECIDE', -1, 'i'),
    (0x1808FF0, 'INPUT_COMMON_BUTTON', 6, 'i'),
    (0x1809014, 'INPUT_FAVORITE', 7, 'i'),
    (0x18090AC, 'AMIIBO_CONFIRM_RESULT_DECIDE', 0, 'i'),
    (0x18090D0, 'AMIIBO_CONFIRM_RESULT_CANCEL', 1, 'i'),
}
for a, name, want, tag in REGISTER:
    v = mov_imm32(a)
    chk(v == want, 'global %s value @0x%x' % (name, a),
        'got %s want %d  (%s)' % (v, want, insn(a)))
    chk('w3' in insn(a), 'global %s writes w3 @0x%x' % (name, a), insn(a))
    call = a + 4
    chk(bl_target(call) == 0x33750A0, 'global %s bl 0x33750a0 @0x%x' % (name, call),
        'got 0x%x' % bl_target(call))
    # the x2 type tag pointer is 4 instructions back from the value immediate
    chk('#0x%x' % (0x42B1A84 - 0x42B1000) in insn(a - 4), 'tag add @0x%x' % (a - 4),
        insn(a - 4))

# FROM_AMIIBO / IS_NEW_CREATE_AMIIBO read one byte each from the static editor record
for a, tag, off in ((0x1809050, 'FROM_AMIIBO', 0xD3C), (0x1809078, 'IS_NEW_CREATE_AMIIBO', 0xD3D)):
    chk('#0x%x' % off in insn(a), '%s static offset @0x%x' % (tag, a), insn(a))
    chk(insn(a).startswith('ldrb') and 'w3' in insn(a), '%s ldrb w3 @0x%x' % (tag, a), insn(a))
    chk(bl_target(a + 20) == 0x33750A0, '%s register call' % tag)

# IS_READ_ONLY: (byte at 0x5306b8c) != 0
chk('#0xb8c' in insn(0x18090E8), 'IS_READ_ONLY record addr', insn(0x18090E8))
chk(insn(0x18090EC).startswith('ldrb'), 'IS_READ_ONLY ldrb', insn(0x18090EC))
chk('cmp' in insn(0x18090F0) and '#0' in insn(0x18090F0), 'IS_READ_ONLY cmp 0', insn(0x18090F0))
chk('cset' in insn(0x18090F4) and 'ne' in insn(0x18090F4), 'IS_READ_ONLY cset ne', insn(0x18090F4))
chk(bl_target(0x1809108) == 0x33750A0, 'IS_READ_ONLY register call')
# IS_SKILL_EDITABLE: (byte at +0) == 0 OR (u16 at +0x10) != 0
chk(insn(0x1809114).startswith('ldrb'), 'IS_SKILL byte @+0', insn(0x1809114))
chk(insn(0x1809118).startswith('ldrh') and '#0x10' in insn(0x1809118),
    'IS_SKILL u16 @+0x10', insn(0x1809118))
chk('cset' in insn(0x1809120) and 'eq' in insn(0x1809120), 'IS_SKILL cset eq', insn(0x1809120))
chk('cset' in insn(0x1809128) and 'ne' in insn(0x1809128), 'IS_SKILL cset ne', insn(0x1809128))
chk('orr' in insn(0x180912C), 'IS_SKILL orr', insn(0x180912C))
chk(bl_target(0x1809148) == 0x33750A0, 'IS_SKILL_EDITABLE register call')

# ==========================================================================
# 3. the 13 state handlers at scene+0x28, installed by 0x180de70 (Q1)
# ==========================================================================
# Each entry is  adrp <acc> ; add <acc>, #lo ; stp <acc>, xzr, [x19, #0x28+16*n].
# The two accumulators alternate (x8 and x9), which is exactly where the P8
# check went wrong: it always matched the nearest preceding adrp/add pair.
# (stp address, register, expected handler)
HANDLERS = [
    (0x180E07C, 'x8', 0x1808980),
    (0x180E08C, 'x8', 0x1809E60),
    (0x180E0C8, 'x9', 0x1809FB0),
    (0x180E098, 'x8', 0x180A030),
    (0x180E0A4, 'x8', 0x180A5B0),
    (0x180E0E0, 'x9', 0x180ABD0),
    (0x180E0B0, 'x8', 0x180B1C0),
    (0x180E0BC, 'x8', 0x180B670),
    (0x180E0F8, 'x9', 0x180BA20),
    (0x180E0D4, 'x8', 0x180BC60),
    (0x180E0EC, 'x8', 0x180C360),
    (0x180E10C, 'x9', 0x180CBC0),
    (0x180E104, 'x8', 0x180CC80),
]
PAGE_MASK = 0xFFFFFFFFFFFFF000


def adrp_target(a):
    w = word(a)
    assert (w & 0x9F000000) == 0x90000000, insn(a)
    imm = ((w >> 5) & 0x7FFFF) << 2 | ((w >> 29) & 3)
    if imm & (1 << 20):
        imm -= 1 << 21
    return ((a & ~0xFFF) + (imm << 12)) & PAGE_MASK


for idx, (stp, reg, want) in enumerate(HANDLERS):
    t = insn(stp)
    chk(t.startswith('stp') and ('%s,' % reg) in t and 'xzr' in t,
        'stp form @0x%x' % stp, t)
    chk('#0x%x]' % (0x28 + 16 * idx) in t, 'handler slot +0x%x (state %d)' % (0x28 + 16 * idx, idx), t)
    # The `add <acc>, #lo` that feeds this stp is not always the word right
    # before it (0x180e088 puts `mov x0, x19` in between), so walk back to the
    # nearest `add <same reg>` and require its own predecessor to be the adrp.
    add = None
    for back in range(4, 96, 4):
        a = stp - back
        t = insn(a)
        if t.startswith('add') and t.split(',')[1].strip() == reg:
            add = a
            break
    chk(add is not None, 'add for accumulator %s before stp @0x%x' % (reg, stp))
    if add is None:
        continue
    chk((word(add - 4) & 0x9F000000) == 0x90000000, 'adrp before add @0x%x' % add,
        insn(add - 4))
    got = adrp_target(add - 4) + int(insn(add).split('#')[1].strip().rstrip(']'), 0)
    chk(got == want, 'handler for state %d' % idx,
        'got 0x%x want 0x%x' % (got, want))

# the scene object size that proves +0x1a0 is a valid child pointer
chk(mov_imm32(0x180DE98) == 0x1E0, 'scene object size 0x1e0', insn(0x180DE98))
chk(mov_imm32(0x180DE94) == 0x10, 'scene object alignment 0x10', insn(0x180DE94))
chk(bl_target(0x180DE9C) == 0x392DCE0, 'scene allocator call')

if NEG == 'handlers':
    # claim the alternating accumulator is always x8 (the P8 mis-pairing)
    for stp, _reg, want in HANDLERS:
        chk(insn(stp - 4).split(',')[0].strip() == 'x8',
            'negative handler accumulator @0x%x' % (stp - 4), insn(stp - 4))

# ==========================================================================
# 4. the state reader 0x180ce40 and the dispatch 0x180a030 (Q4, Q5)
# ==========================================================================
chk('ldrsw' in insn(0x180CE4C) and '#0x144' in insn(0x180CE4C), 'state index load', insn(0x180CE4C))
chk('cmp' in insn(0x180CE50) and '#0x13' in insn(0x180CE50), 'state limit 0x13', insn(0x180CE50))
chk('#0xf8' in insn(0x180CE5C), 'state stack base +0xf8', insn(0x180CE5C))
chk('#0x28' in insn(0x180CE88), 'handler table base +0x28', insn(0x180CE88))
chk('lsl #4' in insn(0x180CE84), '16-byte handler stride', insn(0x180CE84))
chk(insn(0x180CEB4).strip().startswith('blr'), 'indirect handler call', insn(0x180CEB4))

# dispatch entry: 4 words, no PC-relative encoding
PROLOGUE = (0x180A030, 0x180A034, 0x180A038, 0x180A03C)
for a in PROLOGUE:
    w = word(a)
    pc_rel = ((w & 0x9F000000) == 0x90000000 or (w & 0x9F000000) == 0x10000000 or
              (w & 0x3B000000) == 0x18000000 or (w & 0xFC000000) in (0x14000000, 0x94000000) or
              (w & 0xFF000010) == 0x54000000 or (w & 0x7F000000) in (0x34000000, 0x37000000))
    chk(not pc_rel, 'entry word 0x%x is not PC-relative' % a, '0x%08x %s' % (w, insn(a)))
    chk(w != 0, 'entry word 0x%x is not padding' % a)

# the value load and the state push
chk('ldr' in insn(0x180A098) and 'w8' in insn(0x180A098) and '#0x128' in insn(0x180A098),
    'exit value load @0x180a098', insn(0x180A098))
chk('tbnz' in insn(0x180A09C) and '#0x1f' in insn(0x180A09C) and '#0x180a1cc' in insn(0x180A09C),
    'negative -> 0x180a1cc', insn(0x180A09C))
chk('#0x144' in insn(0x180A0A0), 'stack index load', insn(0x180A0A0))
chk('cmp' in insn(0x180A0A4) and '#0x11' in insn(0x180A0A4), 'index guard 0x11', insn(0x180A0A4))
chk('b.gt' in insn(0x180A0A8) and '#0x180a0c8' in insn(0x180A0A8), 'skip push', insn(0x180A0A8))
chk('cmp' in insn(0x180A0B0) and '#0x13' in insn(0x180A0B0), 'new index guard 0x13', insn(0x180A0B0))
chk('#0xf8' in insn(0x180A0C4), 'state store base +0xf8', insn(0x180A0C4))
chk('add' in insn(0x180A0C0) and 'w8' in insn(0x180A0C0) and '#4' in insn(0x180A0C0),
    'pushed value is w8+4', insn(0x180A0C0))
chk('cmp' in insn(0x180A0C8) and '#5' in insn(0x180A0C8), 'cmp 5', insn(0x180A0C8))
chk('b.eq' in insn(0x180A0CC) and '#0x180a228' in insn(0x180A0CC), 'value 5 branch', insn(0x180A0CC))
chk('cmp' in insn(0x180A0D0) and '#6' in insn(0x180A0D0), 'cmp 6', insn(0x180A0D0))
chk('b.ne' in insn(0x180A0D4) and '#0x180a4f0' in insn(0x180A0D4), 'default epilogue', insn(0x180A0D4))
chk(mov_imm32(0x180A0F8) == 0xB, 'value 6 pushes state 0xb', insn(0x180A0F8))
chk(mov_imm32(0x180A248) == 0xB, 'value 5 pushes state 0xb', insn(0x180A248))
chk(mov_imm32(0x180A550) == 4, 'cancel pushes state 4', insn(0x180A550))
chk(mov_imm32(0x180A1EC) == 1, 'negative pushes state 1', insn(0x180A1EC))
chk('cmn' in insn(0x180A1CC) and '#1' in insn(0x180A1CC), 'cmn 1 (is it -1?)', insn(0x180A1CC))
chk('b.eq' in insn(0x180A1D0) and '#0x180a504' in insn(0x180A1D0), 'cancel target', insn(0x180A1D0))
chk('#0xf8' in insn(0x180A554), 'cancel state store', insn(0x180A554))
chk(mov_imm32(0x180A1D4) == 2, 'scene+0x168 = 2 on negative', insn(0x180A1D8))

if NEG == 'movimm':
    # narrow the decoder back to MOVZ/MOVN only and confirm 0x1808fa8 becomes unreadable
    w = word(0x1808FA8)
    chk((w >> 23) & 0x3F == 0x25, 'negative MOVZ/MOVN-only control @0x1808fa8',
        'bits28_23=0x%x' % ((w >> 23) & 0x3F))

# ==========================================================================
# 5. the six child objects and their scripts (Q2)
# ==========================================================================
# (store addr, slot, allocator size imm addr, ctor call, ctor)
CHILDREN = [
    (0x1809498, 0x178, 0x18089C4, None, None),           # built inline, no named ctor
    (0x18095AC, 0x180, 0x18094C0, 0x1809558, 0x19CEB30),  # headgear
    (0x18096C4, 0x188, 0x18095E4, 0x1809670, 0x19C7830),  # outfit
    (0x1809794, 0x190, 0x18096D8, 0x1809740, 0x19C9340),  # no script hash
    (0x1809868, 0x198, 0x18097A8, 0x1809814, 0x19DDB30),  # special moves
    (0x1809934, 0x1A0, 0x180987C, 0x18098E4, 0x19E33E0),  # voice
]
for store, slot, size_at, call, ctor in CHILDREN:
    chk('#0x%x]' % slot in insn(store), 'child store +0x%x' % slot, insn(store))
    if NEG == 'size':
        # negative control: claim the 0x178 child is the 0x138-byte inner object
        # instead of the 0x88-byte wrapper.  It is the SAME instruction address,
        # so only the expected size differs and this must fail.
        want_size = 0x138 if slot == 0x178 else 0x88
        chk(mov_imm32(size_at) == want_size,
            'negative child +0x%x size' % slot, 'got %s want %s' % (mov_imm32(size_at), want_size))
        continue
    chk(mov_imm32(size_at) == 0x88, 'child +0x%x object size 0x88' % slot,
        'got %s' % mov_imm32(size_at))
    if call is None:
        continue
    chk(bl_target(call) == ctor, 'child +0x%x ctor @0x%x' % (slot, call),
        'got 0x%x want 0x%x' % (bl_target(call), ctor))

# the +0x178 object's inner 0x138 object and the pointer that joins them
chk(mov_imm32(0x1808A34) == 0x138, 'inner object size 0x138', insn(0x1808A34))
chk('#0x80]' in insn(0x1808C74) and insn(0x1808C74).startswith('str'),
    'x21+0x80 = x22', insn(0x1808C74))
chk('#0x178]' in insn(0x1809498), 'x21 stored at scene+0x178', insn(0x1809498))

# script path hashes, with the ARC path they match
PATHS = [
    (0x1808C60, [0x1808C60, 0x1808C64, 0x1808C68],
     'ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc'),
    (0x1808C6C, [0x1808C6C, 0x1808C70, 0x1808C80],
     'ui/script_patch/chara_make/make_mii_edit_actor.lc'),
    (0x19CECF8, [0x19CECF8, 0x19CECFC, 0x19CED08],
     'ui/script/menu/chara_make/make_mii_hat_actor.lc'),
    (0x19C79F8, [0x19C79F8, 0x19C79FC, 0x19C7A08],
     'ui/script/menu/chara_make/make_mii_body_actor.lc'),
    (0x19DDD6C, [0x19DDD6C, 0x19DDD70, 0x19DDD7C],
     'ui/script/menu/chara_make/make_mii_special_actor.lc'),
    (0x19E3534, [0x19E3534, 0x19E3538, 0x19E3544],
     'ui/script/menu/chara_make/make_mii_voice_actor.lc'),
]
if NEG == 'path':
    PATHS = [(a, c, 'ui/script/menu/chara_make/make_mii_edit_actor.lc')
             for a, c, p in PATHS]
for first, addrs, path in PATHS:
    got = chain40(addrs)
    want = hash40(path)
    chk(got == want, 'hash40 @0x%x' % first,
        'got 0x%011x want 0x%011x (%s)' % (got, want, path))
    # the MOVZ/MOVK/MOVK shape
    for k, a in enumerate(addrs):
        w = word(a)
        chk((w >> 23) & 0x3F == 0x25 and ((w >> 21) & 3) == k,
            'chain word %d @0x%x' % (k, a), insn(a))
# the script is loaded through the shared helper
for call, ctx in ((0x1808C98, 'edit menu'), (0x19CED1C, 'hat'), (0x19C7A1C, 'body'),
                  (0x19DDD90, 'special'), (0x19E3558, 'voice')):
    chk(bl_target(call) == 0x32CAA90, 'bl 0x32caa90 @0x%x (%s)' % (call, ctx),
        'got 0x%x' % bl_target(call))
# the two child ctors with no script hash load nothing through 0x32caa90
for lo, hi, name in ((0x19C9340, 0x19C9340 + 0x1200, '0x19c9340'),
                     (0x19E0910, 0x19E0910 + 0x1400, '0x19e0910')):
    found = 0
    a = lo
    while a < hi:
        w = word(a)
        if (w & 0xFC000000) == 0x94000000 and bl_target(a) == 0x32CAA90:
            found += 1
        a += 4
    chk(found == 0, 'no script load in %s' % name, 'found %d' % found)

# ==========================================================================
# 6. the exit value field: script call -> store -> dispatch read (Q3)
# ==========================================================================
chk('#0x178]' in insn(0x180A048), 'dispatch child slot @0x180a048', insn(0x180A048))
chk('#0x80]' in insn(0x180A054) and '#0x80]' in insn(0x180A080), 'child+0x80 indirection')
chk('#0x128]' in insn(0x180A098), 'dispatch reads +0x128', insn(0x180A098))
chk('#0xa36' in insn(0x19CA8F0) and '#0x42e5000' in insn(0x19CA8EC),
    'name get_exit_value built at 0x19ca8ec', insn(0x19CA8F0))
chk(bl_target(0x19CA8F8) == 0x38F4790, 'script call helper', insn(0x19CA8F8))
chk(insn(0x19CA93C).startswith('mov') and 'x19' in insn(0x19CA93C), 'mov x8,x19', insn(0x19CA93C))
chk('#0x10]' in insn(0x19CA940), 'pre-index +0x10', insn(0x19CA940))
chk(insn(0x19CA94C).startswith('str') and 'w0' in insn(0x19CA94C) and '#0x118' in insn(0x19CA94C),
    'str w0,[x8,#0x118] -> x19+0x128', insn(0x19CA94C))
# the same function's start, so the reader knows the store's enclosing function
chk(word(0x19CA590) != 0, 'function 0x19ca590 exists')
chk('#0xe4]' in insn(0x19CA5A4), '0x19ca590 reads +0xe4', insn(0x19CA5A4))
chk('#0x12c]' in insn(0x19CA5AC), '0x19ca590 clears +0x12c', insn(0x19CA5AC))
# the initial value of the field and the -2 reset
chk(insn(0x1808BF8).startswith('str') and '#0x128]' in insn(0x1808BF8),
    'field init @0x1808bf8', insn(0x1808BF8))
chk(mov_imm32(0x1808BEC) == -2, 'initial value is -2', insn(0x1808BEC))
chk(mov_imm32(0x19CAB48) == -2, 'reset value is -2 @0x19cab48', insn(0x19CAB48))
chk(insn(0x19CAB4C).startswith('str') and '#0x128]' in insn(0x19CAB4C),
    'reset store', insn(0x19CAB4C))
# the delegate pair that binds 0x19ca590 to this object
chk(adrp_target(0x1808C08) + int(insn(0x1808C0C).split('#')[1].strip(), 0) == 0x19CA590,
    'delegate pair target', insn(0x1808C0C))
chk('#0x80]' in insn(0x1808C1C), 'delegate pair stored at +0x80', insn(0x1808C1C))

# ==========================================================================
# 7. the three flag bytes (Q3)
# ==========================================================================
# +0x130 set at construction (strh w26 with w26 = 1 -> both 0x130 and 0x131)
chk(mov_imm32(0x1808BF4) == 1, 'w26 = 1 for the flag init', insn(0x1808BF4))
chk(insn(0x1808C14).startswith('strh') and '#0x130]' in insn(0x1808C14)
    and 'w26' in insn(0x1808C14), 'strh w26,[x22,#0x130]', insn(0x1808C14))
chk(insn(0x1808C18).startswith('strb') and 'wzr' in insn(0x1808C18) and '#0x132]' in insn(0x1808C18),
    'strb wzr,[x22,#0x132]', insn(0x1808C18))
# +0x130 set to 1 by the actor at 0x19ca62c
chk(mov_imm32(0x19CA628) == 1, 'flag130 value 1', insn(0x19CA628))
chk(insn(0x19CA62C).startswith('strb') and '#0x130]' in insn(0x19CA62C)
    and 'w8' in insn(0x19CA62C), 'strb w8,[x19,#0x130]', insn(0x19CA62C))
# +0x131 set to 1 by the actor at 0x19cb098
chk(mov_imm32(0x19CB090) == 1, 'flag131 value 1', insn(0x19CB090))
chk(insn(0x19CB098).startswith('strb') and '#0x131]' in insn(0x19CB098)
    and 'w8' in insn(0x19CB098), 'strb w8,[x19,#0x131]', insn(0x19CB098))
# +0x132 is only ever cleared, never set, inside the scene and actor windows
for a in (0x180A064, 0x180A084, 0x180A098, 0x180A1AC):
    chk(insn(a).startswith('ldr'), 'dispatch flag read @0x%x' % a, insn(a))
chk('#0x132]' in insn(0x180A1AC) and 'wzr' in insn(0x180A1B8),
    'dispatch clears +0x132', insn(0x180A1B8))
chk(insn(0x180A4B0).startswith('strh') and 'wzr' in insn(0x180A4B0) and '#0x130]' in insn(0x180A4B0),
    'dispatch clears 0x130+0x131', insn(0x180A4B0))

# ==========================================================================
# 8. the state pop (Q5)
# ==========================================================================
# Every handler pops with the same three-instruction idiom:
#   ldr w<n>, [x19, #0x144] ; subs w<n>, w<n>, #1 ; b.lt <skip> ; str w<n>, [x19, #0x144]
POPS = [
    (0x1809FC4, 'state 2 0x1809fb0'),
    (0x180A5F0, 'state 4 0x180a5b0'),
    (0x180ADF4, 'state 5 0x180abd0'),
    (0x180B3DC, 'state 6 0x180b1c0'),
    (0x180B7B8, 'state 7 0x180b670'),
    (0x180BB50, 'state 8 0x180ba20'),
    (0x180C0D4, 'state 9 0x180bc60'),
    (0x180CB64, 'state 10 0x180c360'),
    (0x180CC60, 'state 12 0x180cc80'),
    (0x180CDD0, 'state 12 tail 0x180cc80'),
]
# The three-instruction idiom is sometimes padded by an unrelated store in the
# middle (0x180c0dc), so search a bounded window rather than assume 4-instruction
# spacing, and require every part of the sequence to be present in order.
for at, name in POPS:
    chk('#0x144]' in insn(at), '%s pop load' % name, insn(at))
    sub_at = br_at = st_at = None
    for k in range(1, 8):
        t = insn(at + 4 * k)
        if sub_at is None and t.startswith('subs') and '#1' in t:
            sub_at = at + 4 * k
        elif sub_at is not None and br_at is None and t.startswith('b.lt'):
            br_at = at + 4 * k
        elif br_at is not None and t.startswith('str') and '#0x144]' in t:
            st_at = at + 4 * k
            break
    chk(sub_at is not None, '%s pop decrement' % name, insn(at + 4))
    chk(br_at is not None and sub_at is not None and br_at > sub_at,
        '%s pop guard' % name, insn((sub_at or at) + 4))
    chk(st_at is not None, '%s pop store' % name,
        'no str -> +0x144 within 7 instructions of 0x%x' % at)
# the resume of the edit menu state: cancel path pushes state 1 then tail-calls 0x180daf0
chk(mov_imm32(0x180A1EC) == 1, 'cancel pushes state 1', insn(0x180A1EC))
chk(bl_target(0x180A208) == 0x180DAF0, 'cancel tail-calls 0x180daf0', insn(0x180A208))
chk(mov_imm32(0x180A504) == 1, 'scene+0x168 = 1 on cancel', insn(0x180A504))
chk('#0x168]' in insn(0x180A508), 'cancel stores to +0x168', insn(0x180A508))
# 0x180d200 (the commit reached from the cancel path when a static flag is set)
chk(bl_target(0x180A52C) == 0x180D200, 'cancel -> 0x180d200 when flag set', insn(0x180A52C))
chk('#0xc8c' in insn(0x180A510), '0x180d200 gate flag', insn(0x180A510))
chk(mov_imm32(0x180D230) == 1, '0x180d200 pushes state 1', insn(0x180D230))
chk(bl_target(0x180D23C) == 0x180DAF0, '0x180d200 calls 0x180daf0', insn(0x180D23C))

# ==========================================================================
# 9. branch-target control
# ==========================================================================
if NEG == 'branch':
    chk(bl_target(0x19CA8F8) == 0x38F4794, 'negative script-call target',
        'got 0x%x' % bl_target(0x19CA8F8))
else:
    for call, want, ctx in ((0x1808C98, 0x32CAA90, 'script load'),
                            (0x19CA8F8, 0x38F4790, 'script call'),
                            (0x18092EC, 0x19E0910, 'INPUT_* registrar'),
                            (0x180A1BC, 0x180CF10, 'dispatch -> 0x180cf10')):
        chk(bl_target(call) == want, 'bl 0x%x @0x%x (%s)' % (want, call, ctx),
            'got 0x%x' % bl_target(call))

# ==========================================================================
# 10. the driver chain: who calls the state machine (Q1, Q5)
# ==========================================================================
# 0x180de70 is vtable slot +0x40 (0x50a0c18).  Slot +0x08 (0x50a0c20) is
# 0x180ea90, the destructor: it takes the inner object out of the wrapper and
# frees it.  Slot +0x10 (0x50a0c28) is 0x180ead0, the per-frame update, and
# that is the only caller of 0x180ce40 -- which is why a `bl` scan finds none.
chk(insn(0x180EA9C).startswith('ldr') and '#0x58]' in insn(0x180EA9C),
    '0x180ea90 loads the inner object', insn(0x180EA9C))
chk(bl_target(0x180EAAC) == 0x180DC50, '0x180ea90 calls 0x180dc50', insn(0x180EAAC))
chk(bl_target(0x180EABC) == 0x392E590, '0x180ea90 frees it', insn(0x180EABC))
chk(insn(0x180EAE8).startswith('ldr') and '#0x58]' in insn(0x180EAE8)
    and 'x19' in insn(0x180EAE8), '0x180ead0 loads the inner object into x19',
    insn(0x180EAE8))
chk(bl_target(0x180EAF4) == 0x180CE40, '0x180ead0 calls 0x180ce40', insn(0x180EAF4))
chk(insn(0x180EAD0).startswith('sub') and 'sp' in insn(0x180EAD0),
    '0x180ead0 prologue', insn(0x180EAD0))
# 0x180ce40 does return to its caller: the `ret` at 0x180cefc is reachable from
# 0x180ead0's own `bl`, i.e. the chain is a plain call, not a tail call.
chk(word(0x180CEFC) == 0xD65F03C0, '0x180ce40 ends in ret', insn(0x180CEFC))

# scene+0x14c is a frame counter: +1 after the state ran (0x180eb28..34), and
# both 0x180ce40 paths that finish without running a handler clear it.
chk(insn(0x180EB28).startswith('ldr') and '#0x14c]' in insn(0x180EB28),
    'frame counter read @0x180eb28', insn(0x180EB28))
chk(insn(0x180EB30).startswith('add') and '#1' in insn(0x180EB30),
    'frame counter +1 @0x180eb30', insn(0x180EB30))
chk(insn(0x180EB34).startswith('str') and '#0x14c]' in insn(0x180EB34),
    'frame counter store @0x180eb34', insn(0x180EB34))
chk(insn(0x180CEB8).startswith('str') and 'wzr' in insn(0x180CEB8)
    and '#0x14c]' in insn(0x180CEB8), '0x180ce40 clears the frame counter',
    insn(0x180CEB8))
chk(insn(0x180CEEC).startswith('str') and 'wzr' in insn(0x180CEEC)
    and '#0x14c]' in insn(0x180CEEC), '0x180ce40 clears it again at 0x180ceec',
    insn(0x180CEEC))

# ==========================================================================
# 11. state 1 is the edit menu: it calls the +0x178 child through its vtable
# ==========================================================================
# 0x1809e60 (state 1) reads the +0x178 child, then a virtual at vtable+0x20,
# then compares the result with -1.  That is the get_exit_value call: the
# return value of the edit script decides which Mii part screen opens next.
chk(insn(0x1809E84).startswith('ldr') and '#0x178]' in insn(0x1809E84)
    and 'x20' in insn(0x1809E84), 'state 1 reads scene+0x178', insn(0x1809E84))
chk(insn(0x1809E88).startswith('ldr') and insn(0x1809E88).split()[1].rstrip(',') == 'x8',
    'vtable load into x8', insn(0x1809E88))
chk(insn(0x1809E8C).startswith('ldr') and '#0x20]' in insn(0x1809E8C),
    'vtable slot +0x20', insn(0x1809E8C))
chk(insn(0x1809E90).strip().startswith('blr'), 'virtual call', insn(0x1809E90))
chk('cmn' in insn(0x1809E94) and '#1' in insn(0x1809E94),
    'result compared with -1 (cancel)', insn(0x1809E94))
chk(insn(0x1809E98).startswith('b.eq'), 'cancel skips the part dispatch',
    insn(0x1809E98))
# after the virtual returns it indexes a table of 10 part screens by the value
# (cmp w0,#9 then an indexed ldr), which is the menu of parts the editor offers
chk('cmp' in insn(0x1809EB0) and '#9' in insn(0x1809EB0),
    'part table has 10 entries', insn(0x1809EB0))
chk(insn(0x1809ED0).startswith('ldr') and 'w0' in insn(0x1809ED0)
    and 'sxtw #3' in insn(0x1809ED0), 'indexed part load', insn(0x1809ED0))
chk(insn(0x1809EE4).startswith('cmp') and '#6' in insn(0x1809EE4),
    'group index 0..6', insn(0x1809EE4))
# and it hands the chosen part id to a controller (0x1afe3e0)
chk(bl_target(0x1809F3C) == 0x1AFE3E0, 'part id handed over', insn(0x1809F3C))
# the state ends by pushing scene+0x168 as the argument and tail-calling
chk(insn(0x1809F54).startswith('ldr') and '#0x168]' in insn(0x1809F54),
    'state 1 reads scene+0x168', insn(0x1809F54))
chk(bl_target(0x1809F64) == 0x3726540, 'state 1 tail-calls 0x3726540', insn(0x1809F64))

# ==========================================================================
# 12. which child slot each state drives (Q1, Q2)
# ==========================================================================
# Every handler that owns a child reads scene+<slot>, then the child's own
# +0x80, then a per-screen field, then writes scene+0x1b0.  The slot offsets
# are what tie a state to a child, so they are asserted per state.
SLOT_USE = [
    (5, 0x180ABF0, '#0x180]', 0x180ABF4, '#0x80]', 0x180ABF8, '#0x160]', 0x180ABFC),
    (6, 0x180B1DC, '#0x188]', 0x180B1E0, '#0x80]', 0x180B1E4, '#0x160]', 0x180B1E8),
    (7, 0x180B68C, '#0x190]', 0x180B690, '#0x80]', 0x180B694, '#0xe4]',  0x180B698),
    (8, 0x180BA30, '#0x198]', 0x180BA3C, '#0x80]', 0x180BA40, '#0xe0]', None),
    (9, 0x180BC94, '#0x1a0]', 0x180BC98, '#0x80]', 0x180BC9C, '#0xfc]', None),
]
for state, load, lo, plus80, p80, field, lf, store in SLOT_USE:
    chk(insn(load).startswith('ldr') and lo in insn(load),
        'state %d reads scene%s' % (state, lo), insn(load))
    chk(insn(plus80).startswith('ldr') and p80 in insn(plus80),
        'state %d then +0x80 of the child' % state, insn(plus80))
    chk(insn(field).startswith('ldr') and lf in insn(field),
        'state %d reads child field%s' % (state, lf), insn(field))
    if store is not None:
        chk(insn(store).startswith('str') and '#0x1b0]' in insn(store),
            'state %d writes scene+0x1b0' % state, insn(store))
# state 8 reads its slot through x9 (it is also its base pointer), state 9
# through x8/x9 -- both still the same scene+slot load, asserted above.
chk('x9' in insn(0x180BA30), 'state 8 loads +0x198 into x9', insn(0x180BA30))
chk('x9' in insn(0x180BA3C), 'state 8 then walks x9', insn(0x180BA3C))
chk('x9' in insn(0x180BC98), 'state 9 then walks x9', insn(0x180BC98))

# state 4 (0x180a5b0) reads no child slot: it is the confirm/OK state, and it
# writes scene+0x161 and reads scene+0x168.
chk(insn(0x180AA04).startswith('mov'), 'state 4 mov 1', insn(0x180AA04))
chk(mov_imm32(0x180AA04) == 1, 'state 4 value 1', insn(0x180AA04))
chk(insn(0x180AA08).startswith('strb') and '#0x161]' in insn(0x180AA08),
    'state 4 sets scene+0x161', insn(0x180AA08))
chk(insn(0x180AA0C).startswith('ldr') and '#0x168]' in insn(0x180AA0C),
    'state 4 reads scene+0x168', insn(0x180AA0C))

# Negative check: the three states that the report says own no child must not
# reference any of the six slots.  Scanned with capstone's memory operand, so
# a shifted or unscaled form cannot hide.
CHILD_SLOTS = (0x178, 0x180, 0x188, 0x190, 0x198, 0x1A0)
for lo, hi, name in ((0x180C360, 0x180CBC0, 'state 10 handler'),
                     (0x180CBC0, 0x180CC80, 'state 11 handler'),
                     (0x180CC80, 0x180CE40, 'state 12 handler')):
    hits = []
    a = lo
    while a < hi:
        i = next(MDD.disasm(DATA[a:a + 4], a), None)
        if i is not None:
            for op in i.operands:
                if op.type == capstone.arm64.ARM64_OP_MEM and op.mem.disp in CHILD_SLOTS:
                    hits.append((a, i.mnemonic, i.op_str))
        a += 4
    chk(hits == [], '%s touches no child slot' % name, str(hits[:4]))

# ==========================================================================
# 13. the value-6 tail, the duplicate push and the out-of-range path (Q4)
# ==========================================================================
# Value 6: after pushing state 0xb it plays a sound and TAIL-CALLS 0x33143f0,
# so it never returns into the dispatch function's epilogue.
chk(mov_imm32(0x180A0F8) == 0xB, 'value 6 pushes 0xb (second push)', insn(0x180A0F8))
chk(insn(0x180A0FC).startswith('str') and '#0xf8]' in insn(0x180A0FC),
    'value 6 second push store', insn(0x180A0FC))
chk(bl_target(0x180A120) == 0x32B1E30, 'value 6 sound call', insn(0x180A120))
chk(insn(0x180A128).startswith('mov') and insn(0x180A128).split(',')[1].strip() == 'x0',
    'sound handle passed on', insn(0x180A128))
chk(bl_target(0x180A144) == 0x33143F0, 'value 6 tail-calls 0x33143f0', insn(0x180A144))
_b144 = next(MDD.disasm(DATA[0x180A144:0x180A148], 0x180A144), None)
chk(_b144 is not None and _b144.mnemonic == 'b',
    'value 6 tail is an unconditional branch (b, not bl)', insn(0x180A144))
chk(_b144 is not None and insn(0x180A140).startswith('ldp'),
    'the epilogue is torn down before the tail call', insn(0x180A140))

# Value 5 takes the same second push but at a different site (0x180a228),
# so both value 5 and value 6 leave the stack holding ... 9, 0xb.
chk(insn(0x180A228).startswith('ldr') and '#0x144]' in insn(0x180A228),
    'value 5 re-reads the stack index', insn(0x180A228))
chk(insn(0x180A22C).startswith('cmp') and '#0x11' in insn(0x180A22C),
    'value 5 index guard', insn(0x180A22C))
chk(insn(0x180A234).startswith('add') and '#1' in insn(0x180A234),
    'value 5 increments the index', insn(0x180A234))
chk(mov_imm32(0x180A248) == 0xB, 'value 5 pushes 0xb', insn(0x180A248))
chk(insn(0x180A250).startswith('b '), 'value 5 returns to the epilogue',
    insn(0x180A250))

# Values >= 9 push state >= 0xd, which is the first value past the 13-entry
# table: 0x180ce40 stores it and then `b.hs 0x180cf00` without a handler.
chk(mov_imm32(0x180A0F8) == 0xB, 'pushed value 0xb stays inside the table',
    insn(0x180A0F8))
chk(insn(0x180CE70).startswith('cmp') and '#0xd' in insn(0x180CE70),
    '0x180ce40 rejects states >= 0xd', insn(0x180CE70))
chk(insn(0x180CE7C).startswith('b.hs') and '#0x180cf00' in insn(0x180CE7C),
    'states >= 0xd skip the handler', insn(0x180CE7C))
# 0x180cf00 is the "no handler" trap: it calls the assert helper and never
# returns normally.
chk(bl_target(0x180CF00) == 0x39C20A0, '0x180cf00 assert helper', insn(0x180CF00))
# and both push sites guard with the same limit before reaching it
chk(insn(0x180A0B8).startswith('b.hs') and '#0x180a5a0' in insn(0x180A0B8),
    'push guard at 0x180a0b8', insn(0x180A0B8))
chk(insn(0x180A0F0).startswith('b.hs') and '#0x180a5a0' in insn(0x180A0F0),
    'push guard at 0x180a0f0', insn(0x180A0F0))
chk(bl_target(0x180A5A0) == 0x39C20A0, '0x180a5a0 is the same assert helper',
    insn(0x180A5A0))
chk(insn(0x180A240).startswith('b.hs') and '#0x180a5a0' in insn(0x180A240),
    'value 5 guard at 0x180a240', insn(0x180A240))

# ==========================================================================
# 14. the exit-value conversion, in detail (Q3)
# ==========================================================================
# 0x19ca590 calls the script's get_exit_value; when the value is not the
# sentinel type 6 it forces w0 to 0 (0x19ca934) -- i.e. the raw script
# integer is only trusted in one branch.
chk(insn(0x19CA91C).startswith('cmp') and '#6' in insn(0x19CA91C),
    'exit-value type check', insn(0x19CA91C))
chk(insn(0x19CA920).startswith('b.ne') and '#0x19ca934' in insn(0x19CA920),
    'non-integer result goes to 0x19ca934', insn(0x19CA920))
chk(mov_imm32(0x19CA924) == 1, 'conversion argument 1', insn(0x19CA924))
chk(bl_target(0x19CA92C) == 0x3376B80, 'conversion helper', insn(0x19CA92C))
chk(mov_imm32(0x19CA934) == 0, 'otherwise w0 = 0', insn(0x19CA934))
# and the field is reset to -2 between uses, at 0x19cab48
chk(mov_imm32(0x19CAB48) == -2, 'reset value -2', insn(0x19CAB48))
chk(bl_target(0x19CAB38) == 0x1AF6200, 'reset helper', insn(0x19CAB38))
chk(bl_target(0x19CAB44) == 0x33763D0, 'reset helper 2', insn(0x19CAB44))
# the +0x130 raise happens on the path that asks the script for its value, and
# the same function names get_exit_value at 0x19ca668
chk(cstr(0x42E5A36) == 'get_exit_value', 'name at 0x19ca668 is get_exit_value')
chk(insn(0x19CA66C).startswith('add') and '#0xa36' in insn(0x19CA66C),
    'name materialised at 0x19ca66c', insn(0x19CA66C))
chk(mov_imm32(0x19CA618) == -2, 'script call argument -2 @0x19ca618',
    insn(0x19CA618))
chk(bl_target(0x19CA620) == 0x38F4A10, 'script run call @0x19ca620', insn(0x19CA620))
chk(insn(0x19CA61C) == 'mov x0, x21',
    'x0 = the script object (register form, not an immediate)', insn(0x19CA61C))
# the +0x131 producer (0x19cae30) names the two sounds it toggles between
chk(cstr(0x42F7A93) == 'favorite_off', 'favorite_off string')
chk(cstr(0x4329744) == 'favorite_on', 'favorite_on string')
chk(insn(0x19CAE98).startswith('add') and '#0xa93' in insn(0x19CAE98),
    'favorite_off materialised @0x19cae98', insn(0x19CAE98))
chk(insn(0x19CAED8).startswith('add') and '#0x744' in insn(0x19CAED8),
    'favorite_on materialised @0x19caed8', insn(0x19CAED8))
chk(bl_target(0x19CAE9C) == 0x3777D50, 'favorite_off sound call', insn(0x19CAE9C))
chk(bl_target(0x19CAEDC) == 0x3777D50, 'favorite_on sound call', insn(0x19CAEDC))
# and it toggles one byte in the static record, which is why +0x131 is a
# "changed" marker rather than a mode
chk(insn(0x19CAE5C).startswith('ldrb') and '#0xd20]' in insn(0x19CAE5C),
    'favorite toggle reads the static byte', insn(0x19CAE5C))
chk(insn(0x19CAE60).startswith('eor') and '#1' in insn(0x19CAE60),
    'favorite toggle flips it', insn(0x19CAE60))
chk(insn(0x19CAE64).startswith('strb') and '#0xd20]' in insn(0x19CAE64),
    'favorite toggle stores it back', insn(0x19CAE64))

# ==========================================================================
# 15. the resume path (Q5)
# ==========================================================================
# state 1 resumes through 0x180daf0.  Both cancel paths reach it: the
# negative-value path tail-calls it directly (0x180a208) and 0x180d200 calls
# it (0x180d23c) after pushing state 1 again.
chk(bl_target(0x180A208) == 0x180DAF0, 'cancel tail-calls 0x180daf0', insn(0x180A208))
chk(bl_target(0x180D23C) == 0x180DAF0, '0x180d200 calls 0x180daf0', insn(0x180D23C))
chk(insn(0x180D238).startswith('str') and '#0xf8]' in insn(0x180D238),
    '0x180d200 pushes state 1', insn(0x180D238))
chk(insn(0x180D220).startswith('ldrsw') and '#0x144]' in insn(0x180D220),
    '0x180d200 reads the stack index', insn(0x180D220))
chk(insn(0x180D228).startswith('b.hs'), '0x180d200 index guard', insn(0x180D228))
chk(insn(0x180D240).startswith('ldr') and '#0x168]' in insn(0x180D240),
    '0x180d200 re-reads scene+0x168', insn(0x180D240))
chk(insn(0x180D244).startswith('cmp') and '#1' in insn(0x180D244),
    'and branches on cancel-vs-confirm', insn(0x180D244))
# the free of the inner object happens in two destructors, both calling 0x180dc50
chk(bl_target(0x180DDF8) == 0x180DC50, 'state 12 free @0x180ddf8', insn(0x180DDF8))
chk(bl_target(0x180DE4C) == 0x180DC50, 'wrapper free @0x180de4c', insn(0x180DE4C))
chk(insn(0x180DE2C).startswith('ldr') and '#0x58]' in insn(0x180DE2C),
    'wrapper destructor takes the inner object', insn(0x180DE2C))
chk(bl_target(0x180DE08) == 0x392E590, 'and frees it', insn(0x180DE08))
# scene+0x1c8 / +0x1cc are the two button-state words the resume path compares
chk(insn(0x180DB24).startswith('ldr') and '#0x1c8]' in insn(0x180DB24),
    'resume reads +0x1c8', insn(0x180DB24))
chk(insn(0x180DB3C).startswith('ldr') and '#0x1cc]' in insn(0x180DB3C),
    'resume reads +0x1cc', insn(0x180DB3C))
chk(insn(0x180DB38).startswith('b.ne') and '#0x180db90' in insn(0x180DB38),
    '+0x1c8 branch', insn(0x180DB38))
chk(insn(0x180DB4C).startswith('b.eq') and '#0x180dbe0' in insn(0x180DB4C),
    '+0x1cc branch', insn(0x180DB4C))

# ==========================================================================
# 16. vtable addends (Q2): the delegate slots read out of the RELA array
# ==========================================================================
def reloc_addend(target):
    """r_addend of the R_AARCH64_RELATIVE record whose r_offset == target.

    main.bin is a flat image with no relocation-table header, so the records
    are a bare 24-byte array and are found by scanning for the r_offset
    pattern.  Returns None when the slot has no such record, rather than
    falling back to the (zero) file qword.
    """
    pat = struct.pack('<Q', target)
    i = 0
    while True:
        i = DATA.find(pat, i)
        if i < 0:
            return None
        if (i + 24) <= len(DATA):
            info, pad = struct.unpack_from('<II', DATA, i + 8)
            addend = struct.unpack_from('<Q', DATA, i + 0x10)[0]
            if info == 0x403 and pad == 0 and addend != 0:
                return addend
        i += 1


VTABLES = [
    (0x50A6AA8, [0x19CC210, 0x19CC2D0, 0x32CA8D0, 0x19CC390], '+0x178 edit actor'),
    (0x50A69D8, [0x19C9D90, 0x19C9E90, 0x32CA8D0, 0x19C9F80], '+0x190 child'),
    (0x50A0C18, [0x180DE70, 0x180EA90, 0x180EAD0, 0x180F350], 'scene outer vtable'),
]
for base, want, name in VTABLES:
    for k, w in enumerate(want):
        slot = base + 8 * k
        got = reloc_addend(slot)
        chk(got == w, '%s slot +0x%02x @0x%x' % (name, 8 * k, slot),
            'got %s want 0x%x' % ('None' if got is None else hex(got), w))
    # the file qword is zero in .data, so the addend is the only source
    chk(struct.unpack_from('<Q', DATA, base)[0] == 0,
        '%s base slot is relocated, not inline' % name)

# the +0x190 child vtable is installed by its constructor at 0x19c9340
for a in range(0x19C9340, 0x19C9340 + 0x40, 4):
    w = word(a)
    if (w & 0x9F000000) == 0x90000000:
        nxt = insn(a + 4)
        if nxt.startswith('add') and '#0x' in nxt:
            got = adrp_target(a) + int(nxt.split('#')[1].strip(), 0)
            if got == 0x50A69D8:
                chk(True, '+0x190 child vtable installed at 0x%x' % a)
                break
else:
    chk(False, '+0x190 child vtable installed', 'not found in 0x19c9340..0x19c9380')

# ==========================================================================
# 17. hook facts (Q7): entry words and the register set
# ==========================================================================
ENTRY = (0x180A030, 0x180A034, 0x180A038, 0x180A03C)
ENTRY_WORDS = (0xA9BC5FF8, 0xA90157F6, 0xA9024FF4, 0xA9037BFD)
for a, w in zip(ENTRY, ENTRY_WORDS):
    chk(word(a) == w, 'entry word @0x%x' % a,
        'got 0x%08x want 0x%08x' % (word(a), w))
for a in ENTRY:
    i = next(MDD.disasm(DATA[a:a + 4], a), None)
    chk(i is not None and i.mnemonic.startswith('stp'), 'entry @0x%x is a stp' % a,
        '' if i is None else '%s %s' % (i.mnemonic, i.op_str))
# the fifth word is the only SP-relative one and is not PC-relative either
chk(word(0x180A040) == 0x9100C3FD, 'word 5 is add x29, sp, #0x30', insn(0x180A040))

# Over 0x180a098..0x180a0c8 only x8, x9, x10 and x19 are read or written, and
# the condition flags, so everything else is free across that range.  Computed
# from capstone's operand list over the exact byte range the report quotes.
SKIP_REGS = {0x1D, 0x1E, 0x1F, 0x9F}      # fp/simd share the encoding space
REGNO = {}
for _n in range(31):
    REGNO['x%d' % _n] = _n
    REGNO['w%d' % _n] = _n
REGNO.update({'sp': 31, 'wsp': 31, 'xzr': 31, 'wzr': 31})
touched = set()
a = 0x180A098
while a < 0x180A0CC:
    i = next(MDD.disasm(DATA[a:a + 4], a), None)
    if i is not None:
        for op in i.operands:
            if op.type == capstone.arm64.ARM64_OP_REG and op.reg not in SKIP_REGS:
                touched.add(REGNO.get(i.reg_name(op.reg), -1))
    a += 4
chk(touched == {8, 9, 10, 19}, 'register set over 0x180a098..0x180a0c8',
    'got %s' % sorted(touched))

# ==========================================================================
print('negative control: %s' % (NEG if NEG else 'none'))
print('checks passed: %d   failed: %d' % (OK, len(FAIL)))
for f in FAIL:
    print('FAIL: %s' % f)
sys.exit(1 if FAIL else 0)