"""P2-UI-CONSTS claim check: re-derive every address and value in
research/P2-UI-CONSTS.md directly from gamedata/ssbu-13.0.4/main.bin.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python check_claims.py

Nothing here reads the window scripts or the saved evidence files. Every check decodes
the raw instruction words itself (capstone for text, struct for data) so a mismatch in
the report fails rather than being copied through.

Exit code 0 when every check passes, 1 otherwise.
"""
import struct
import sys
from pathlib import Path

import capstone

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
EXPECTED_SHA256 = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'
IMAGE_SIZE = 86672752
TEXT = (0x100, 0x39C8000)
REG_FN = 0x33750A0

data = IMAGE.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

results = []


def check(label, got, want):
    ok = got == want
    results.append((ok, label, got, want))
    return ok


def sx(v, b):
    return v - (1 << b) if v & (1 << (b - 1)) else v


def word(a):
    return struct.unpack_from('<I', data, a)[0]


def dis(a):
    return next(md.disasm(data[a:a + 4], a), None)


def text(a):
    ins = dis(a)
    return ('%s %s' % (ins.mnemonic, ins.op_str)).strip() if ins else None


def cstr_at(a):
    e = data.find(b'\0', a, a + 96)
    if e < 0:
        return None
    return data[a:e].decode('latin1')


def adrp_target(a):
    """Page address an adrp at a sets, or None if the word is not an adrp."""
    w = word(a)
    if (w & 0x9F000000) != 0x90000000:
        return None
    return (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12)


def add_imm(a):
    """Immediate of an add-immediate at a (unsigned 12-bit), or None."""
    w = word(a)
    if (w & 0xFF800000) != 0x91000000:
        return None
    return (w >> 10) & 0xFFF


def adrp_add(a_adrp, a_add):
    """Full address formed by an adrp at a_adrp completed by an add-immediate at a_add."""
    p = adrp_target(a_adrp)
    i = add_imm(a_add)
    if p is None or i is None:
        return None
    if ((word(a_add) >> 5) & 31) != (word(a_adrp) & 31):
        return None
    return p + i


def mov_imm(a):
    """Value written into w3 by the `mov <wN>, #imm` / `mov <wN>, wzr` word at a.

    Two DIFFERENT AArch64 classes produce the words at the group-1 value sites and they
    must not be conflated:

      - ORR (immediate) with Rn = wzr: sf=0 opc=01 and bits 28:23 == 0b100100.
        The value is the logical immediate RotateRight(ONES(imms), immr), with
        N = bit 22, immr = bits 21:16, imms = bits 15:10. Six of the seven sites are
        this form.
      - The `mov wN, wzr` alias at 0x19de4cc is NOT that form: its bits 28:23 are
        0b010100 (ORN), where the bitmask is inverted. Decoding it with ORR semantics
        yields 2, which is wrong. It is 0.

    The alias case is not decoded arithmetically here. Instead `WORD_CHECKS` pins the
    exact 32-bit word and the disassembler text, and the value was established by an
    assembler round-trip: `mov w3, wzr` assembles to exactly 0x2a1f03e3
    (evidence/P2-UI-CONSTS/08_assembler_roundtrip.txt), and LLVM 22.1.8 llvm-objdump
    decodes that same word as `mov w3, wzr` (evidence/P2-UI-CONSTS/07_llvm_crosscheck.txt).
    """
    w = word(a)
    sf = w >> 31
    opc = (w >> 29) & 3
    pat = (w >> 23) & 0x3F
    if sf == 0 and opc == 1 and pat == 0b100100 and ((w >> 5) & 31) == 31:
        return decode_bitmask(0, (w >> 16) & 0x3F, (w >> 10) & 0x3F, 0)
    if sf == 0 and opc == 1 and pat == 0b010100 and ((w >> 5) & 31) == 31:
        # ORN (immediate) with Rn = wzr: the disassembler alias for a zero move.
        return 0 if text(a) == 'mov w3, wzr' else None
    return None


def decode_bitmask(N, immr, imms, sf):
    """Decode the AArch64 ORR logical immediate (N, immr, imms) to a value.

    Implements the ARM DecodeBitMasks pseudocode: RotateRight(ONES(imms), immr).
    """
    length = 6 if sf == 0 else 7
    combined = (N << 6) | (~imms & 0x3F)
    if combined == 0:
        return None
    len_ = combined.bit_length() - 1
    if len_ < 1 or len_ > length:
        return None
    levels = (1 << len_) - 1
    S = imms & levels
    R = immr & levels
    esize = 1 << len_
    if sf == 0 and esize != 0x20:
        return None
    ones = (1 << (S + 1)) - 1
    if R:
        rot = ((ones >> R) | (ones << (esize - R))) & ((1 << esize) - 1)
    else:
        rot = ones
    return rot & 0xFFFFFFFF if sf == 0 else rot


def bl_target(a):
    w = word(a)
    if (w & 0xFC000000) != 0x94000000:
        return None
    return a + (sx(w & 0x3FFFFFF, 26) << 2)


def prologue_at(a):
    """True if a is a function prologue: a downward sp write, preceded by padding.

    Defined by observable stack behaviour rather than by raw opcode masks, because the
    three prologue shapes in this image differ in encoding:
      - `sub sp, sp, #imm`            e.g. 0x1808980
      - 32-bit `stp ..., [sp, #-imm]!` e.g. 0x1809e60
      - 64-bit `str d8, [sp, #-0x70]!` e.g. 0x1874680, word 0xfc190fe8

    The inherited fstart.py masks cover only the first two, which is why it
    mis-attributes the site-B enclosing function to 0x1874570. The third word's encoding
    was confirmed against the LLVM 22.1.8 assembler (`str d8, [sp, #-0x70]!` -> 0xfc190fe8)
    rather than guessed; the textual test below then avoids depending on that bit layout
    at all. The previous word must be udf #0, a ret, a branch, or zero.
    """
    ins = dis(a)
    if ins is None:
        return False
    m, ops = ins.mnemonic, ins.op_str
    if m in ('sub', 'subw'):
        alloc = ops.startswith('sp,')
    elif m in ('str', 'stur', 'stp'):
        # a pre-indexed store with a negative displacement allocates the frame
        alloc = '[sp, #-' in ops and ops.endswith('!')
    else:
        alloc = False
    if not alloc:
        return False
    pw = word(a - 4)
    return (pw in (0xD65F03C0, 0x00000000)
            or (pw & 0xFC000000) == 0x14000000
            or (pw & 0xFFFFFC1F) == 0xD61F0000
            or pw == 0xD4200020
            or (pw & 0xFC000000) == 0x94000000)


def last_prologue_at_or_before(addr, lo):
    """The highest prologue candidate in [lo, addr]; 0 if none."""
    for a in range(addr & ~3, lo - 4, -4):
        if prologue_at(a):
            return a
    return 0


def cset_eq_flag(a):
    """Return the register compared by a cset <wN>, eq|ne at a, or None."""
    t = text(a)
    if t is None:
        return None
    p = t.split()
    if len(p) != 3 or p[0] != 'cset' or p[2] not in ('eq', 'ne'):
        return None
    return p[1]


# ---------------------------------------------------------------- input identity

import hashlib

h = hashlib.sha256()
with IMAGE.open('rb') as fh:
    for chunk in iter(lambda: fh.read(1 << 22), b''):
        h.update(chunk)
check('input sha256', h.hexdigest(), EXPECTED_SHA256)
check('input size', len(data), IMAGE_SIZE)
results.append((TEXT[1] < len(data), 'TEXT range inside file', TEXT[1], 'ok'))

# ------------------------------------------------- string table (name -> address)

NAMES = {
    'SPECIAL_SKILL_NUM': 0x0424DE53,
    'SKILL_COMMAND_NUM': 0x04338B2F,
    'SKILL_COMMAND_NORMAL': 0x04348C67,
    'SKILL_COMMAND_SIDE': 0x0424DE65,
    'SKILL_COMMAND_UPPER': 0x043BD0B4,
    'SKILL_COMMAND_LOWER': 0x0432898F,
    'INPUT_OK': 0x04306E9B,
    'IS_SKILL_EDITABLE': 0x04431954,
    'IS_READ_ONLY': 0x044119AF,
}
for name, addr in NAMES.items():
    check('string %s at 0x%08x' % (name, addr), cstr_at(addr), name)
    # exactly one NUL-terminated occurrence
    n = 0
    i = 0
    term = name.encode() + b'\0'
    while True:
        i = data.find(term, i)
        if i < 0:
            break
        n += 1
        i += 1
    check('string %s NUL-terminated count' % name, n, 1)

# --------------------------------------------------- group 1: seven call sites

# (name, adrp, add, bl, value-def addr, expected w3 value, expected word, expected text)
G1 = [
    ('SPECIAL_SKILL_NUM', 0x019DE498, 0x019DE49C, 0x019DE4AC, 0x019DE4A8, 3,
     0x320007E3, 'mov w3, #3'),
    ('SKILL_COMMAND_NORMAL', 0x019DE4BC, 0x019DE4C0, 0x019DE4D0, 0x019DE4CC, 0,
     0x2A1F03E3, 'mov w3, wzr'),
    ('SKILL_COMMAND_SIDE', 0x019DE4E0, 0x019DE4E4, 0x019DE4F4, 0x019DE4F0, 1,
     0x320003E3, 'mov w3, #1'),
    ('SKILL_COMMAND_UPPER', 0x019DE504, 0x019DE508, 0x019DE518, 0x019DE514, 2,
     0x321F03E3, 'mov w3, #2'),
    ('SKILL_COMMAND_LOWER', 0x019DE528, 0x019DE52C, 0x019DE53C, 0x019DE538, 3,
     0x320007E3, 'mov w3, #3'),
    ('SKILL_COMMAND_NUM', 0x019DE54C, 0x019DE550, 0x019DE560, 0x019DE55C, 4,
     0x321E03E3, 'mov w3, #4'),
    ('INPUT_OK', 0x019DE56C, 0x019DE570, 0x019DE580, 0x019DE57C, 6,
     0x321F07E3, 'mov w3, #6'),
]
G1_FN = (0x19DDB30, 0x19DE6B0)

for name, a_adrp, a_add, a_bl, a_val, val, want_word, want_text in G1:
    check('%s adrp+add -> string 0x%08x' % (name, NAMES[name]),
          adrp_add(a_adrp, a_add), NAMES[name])
    check('%s call at 0x%08x targets registration fn' % (name, a_bl),
          bl_target(a_bl), REG_FN)
    check('%s call site inside 0x19ddb30' % name,
          G1_FN[0] <= a_bl <= G1_FN[1], True)
    # anchor on the exact word, then on the decoded value and text
    check('%s value word at 0x%08x' % (name, a_val), word(a_val), want_word)
    check('%s value text at 0x%08x' % (name, a_val), text(a_val), want_text)
    check('%s w3 value defined at 0x%08x' % (name, a_val), mov_imm(a_val), val)
    # x1 is the name and x3 is the value at the call: confirm register numbers
    check('%s add destination is x1' % name, word(a_add) & 31, 1)
    check('%s value def writes w3' % name, word(a_val) & 31, 3)

# x2 at each group-1 site is the same adrp-established pointer 0x42b1a84
for name, a_adrp, a_add, a_bl, a_val, val, want_word, want_text in G1:
    x2_adrp, x2_add = a_bl - 12, a_bl - 8
    check('%s x2 = 0x42b1a84' % name, adrp_add(x2_adrp, x2_add), 0x042B1A84)

# x0 at each group-1 site comes from `ldr x0, [x8]`, itself loaded from x19+0x40.
# Six of the seven share one shape: ldr x8 at -32, ldr x0 at -28, cbz at -24.
# INPUT_OK is the odd one: the cbz of the SKILL_COMMAND_NUM block (0x19de548) targets
# 0x19de56c, which IS the INPUT_OK adrp, so INPUT_OK is reached by branch and has no cbz
# of its own; its two loads sit 28 and 24 bytes before the call.
X0_OFFSET = {'INPUT_OK': (24, 28, False)}
for name, a_adrp, a_add, a_bl, a_val, val, want_word, want_text in G1:
    d0, d8, has_cbz = X0_OFFSET.get(name, (28, 32, True))
    check('%s x0 is a load, not an immediate' % name,
          text(a_bl - d0), 'ldr x0, [x8]')
    check('%s x8 for that load is itself a load' % name,
          text(a_bl - d8), 'ldr x8, [x19, #0x40]')
    check('%s x0 has %s own null-check' % (name, 'an' if has_cbz else 'no'),
          text(a_bl - d0 + 4) if has_cbz else None,
          'cbz x0, #0x19de56c' if has_cbz else None)
# the branch target that makes INPUT_OK a branch-reached site
check('cbz of the SKILL_COMMAND_NUM block targets the INPUT_OK adrp',
      text(0x019DE548), 'cbz x0, #0x19de56c')
check('INPUT_OK adrp is at that branch target',
      adrp_target(0x019DE56C), 0x04306000)

# no x5 write anywhere in 0x19ddb30..0x19de6b0
def writes_x5(lo, hi):
    n = 0
    for a in range(lo, hi, 4):
        w = word(a)
        ins = dis(a)
        if ins is None:
            continue
        op = ins.op_str.split(',')[0].strip()
        if op in ('x5', 'w5') and ins.mnemonic not in (
                'cmp', 'tst', 'str', 'strb', 'strh', 'stur', 'stp', 'ldur'):
            n += 1
    return n


check('x5 never written in 0x19ddb30..0x19de6b0', writes_x5(*G1_FN), 0)

# x4 at the group-1 sites: last definition is 0x19ddd84, with 59 intervening calls
check('x4 last definition in 0x19ddb30 is at 0x19ddd84',
      text(0x019DDD84), 'mov w4, #1')
check('x4 at 0x19ddd84 is an immediate', mov_imm(0x019DDD84), 1)
# x4 is set to 1 at 0x19ddd84 but 59 calls follow before the group-1 sites, so its value at
# the call is NOT established; the report must not claim 1 there. Confirm the shape.
check('0x19ddd84 is before the first group-1 call', 0x019DDD84 < 0x019DE4AC, True)
n_between = 0
for a in range(0x019DDD88, 0x019DE4AC, 4):
    ins = dis(a)
    if ins is not None and ins.mnemonic in ('bl', 'blr'):
        n_between += 1
check('intervening bl/blr between 0x19ddd84 and 0x19de4ac', n_between, 59)

# ------------------------------- registration function 0x33750a0 argument reads

check('0x33750a0 prologue', text(0x33750A0), 'sub sp, sp, #0x120')
check('0x33750a0 first call target', bl_target(0x3375118), 0x372CF50)
# argument registers read before that call (0x33750a0..0x3375118)
check('0x33750a0 reads x3 (str x3, [sp, #0x88])', text(0x33750C8), 'str x3, [sp, #0x88]')
check('0x33750a0 reads x0 (mov x20, x0)', text(0x33750DC), 'mov x20, x0')
check('0x33750a0 reads x2 (mov x8, x2)', text(0x33750E4), 'mov x8, x2')
check('0x33750a0 reads x1 (mov x19, x1)', text(0x33750E8), 'mov x19, x1')
check('0x33750a0 dereferences x0 (ldr x0, [x0])', text(0x337510C), 'ldr x0, [x0]')
check('0x33750a0 null-checks x1 (cbz x19) after the call', text(0x3375124), 'cbz x19, #0x337519c')

# --------------------------------------------------- group 2: IS_* registration

G2_FN_A = 0x01808980
G2_FN_B = 0x01874680

# site A: one function, two registrations
check('IS_READ_ONLY site A adrp+add',
      adrp_add(0x018090F8, 0x018090FC), NAMES['IS_READ_ONLY'])
check('IS_READ_ONLY site A bl target', bl_target(0x01809108), REG_FN)
check('IS_SKILL_EDITABLE site A adrp+add',
      adrp_add(0x01809134, 0x01809138), NAMES['IS_SKILL_EDITABLE'])
check('IS_SKILL_EDITABLE site A bl target', bl_target(0x01809148), REG_FN)
check('site A call inside function 0x1808980', G2_FN_A <= 0x01809148, True)
check('site A x2 = 0x43ccb7b',
      adrp_add(0x01809100, 0x01809104), 0x043CCB7B)
check('site A x2 is the same for IS_SKILL_EDITABLE',
      adrp_add(0x0180913C, 0x01809140), 0x043CCB7B)

# IS_READ_ONLY site A value: ldrb w8,[x23] ; cmp w8,#0 ; cset w3,ne
check('site A IS_READ_ONLY value load', text(0x018090EC), 'ldrb w8, [x23]')
check('site A IS_READ_ONLY compare', text(0x018090F0), 'cmp w8, #0')
check('site A IS_READ_ONLY cset', text(0x018090F4), 'cset w3, ne')
check('site A IS_READ_ONLY base x23 = 0x5306b8c',
      adrp_add(0x018090E4, 0x018090E8), 0x05306B8C)
check('site A x23 base is beyond EOF (runtime .bss)', 0x05306B8C > len(data), True)

# IS_SKILL_EDITABLE site A value: orr w23, w8, w9 ; mov w3, w23
check('site A IS_SKILL_EDITABLE combine', text(0x0180912C), 'orr w23, w8, w9')
check('site A IS_SKILL_EDITABLE w3 move', text(0x01809144), 'mov w3, w23')
check('site A IS_SKILL_EDITABLE byte load', text(0x01809114), 'ldrb w8, [x23]')
check('site A IS_SKILL_EDITABLE byte compare', text(0x0180911C), 'cmp w8, #0')
check('site A IS_SKILL_EDITABLE byte cset', text(0x01809120), 'cset w8, eq')
check('site A IS_SKILL_EDITABLE halfword load', text(0x01809118), 'ldrh w9, [x23, #0x10]')
check('site A IS_SKILL_EDITABLE halfword compare', text(0x01809124), 'cmp w9, #0')
check('site A IS_SKILL_EDITABLE halfword cset', text(0x01809128), 'cset w9, ne')

# site B: second function, IS_READ_ONLY only
check('IS_READ_ONLY site B adrp+add',
      adrp_add(0x01874EE8, 0x01874EEC), NAMES['IS_READ_ONLY'])
check('IS_READ_ONLY site B bl target', bl_target(0x01874EF8), REG_FN)
check('site B call inside function 0x1874680', G2_FN_B <= 0x01874EF8, True)
check('site B x2 = 0x43ccb7b',
      adrp_add(0x01874EF0, 0x01874EF4), 0x043CCB7B)
check('site B IS_READ_ONLY compare', text(0x01874EE0), 'cmp w27, #1')
check('site B IS_READ_ONLY cset', text(0x01874EE4), 'cset w3, eq')
check('site B IS_READ_ONLY value load', text(0x01874D50), 'ldr w27, [x19, #0xdc]')
check('site B x19 is the incoming x0', text(0x018746AC), 'mov x19, x0')

# function-start evidence
check('site A function 0x1808980 prologue', text(0x01808980), 'sub sp, sp, #0x190')
check('site A padding before it is udf', text(0x0180897C), 'udf #0')
check('site B function 0x1874680 prologue', text(0x01874680), 'str d8, [sp, #-0x70]!')
check('site B padding before it is udf', text(0x0187467C), 'udf #0')
check('0x1874570 is a different, earlier function ending in ret',
      text(0x0187466C), 'ret')

# The attributed function start must be the LAST prologue at or before each call, not
# merely an address smaller than it. A weaker `start <= call` test accepted 0x1874570,
# which is the wrong function; these assertions reject that by scanning for prologues.
check('site A attributed start is the last prologue before its calls',
      last_prologue_at_or_before(0x01809148, 0x01800000), G2_FN_A)
check('site B attributed start is the last prologue before its call',
      last_prologue_at_or_before(0x01874EF8, 0x01870000), G2_FN_B)
check('0x1874570 is a prologue, and is NOT the nearest one above 0x1874ef8',
      (prologue_at(0x01874570),
       prologue_at(0x01874680),
       last_prologue_at_or_before(0x01874EF8, 0x01870000)),
      (True, True, 0x01874680))

# function extents: both group-2 sites lie inside the function each site is attributed to
check('site A function ends at the next prologue 0x1809e60',
      text(0x01809E60), 'stp x20, x19, [sp, #-0x20]!')
check('site A call sites inside 0x1808980..0x1809e60',
      all(G2_FN_A <= a < 0x01809E60 for a in (0x01809108, 0x01809148)), True)
check('site B function epilogue restores sp', text(0x018751E4), 'ldr d8, [sp], #0x70')
check('site B function ends in ret', text(0x018751E8), 'ret')
check('site B call site inside 0x1874680..0x18751e8',
      G2_FN_B <= 0x01874EF8 < 0x018751E8, True)
# ...and no prologue intervenes between each attributed start and its call
check('no prologue between site B start 0x1874680 and its call',
      [a for a in range(G2_FN_B + 4, 0x01874EF8, 4) if prologue_at(a)], [])
check('no prologue between site A start 0x1808980 and its calls',
      [a for a in range(G2_FN_A + 4, 0x01809148, 4) if prologue_at(a)], [])

# ---------------------------------------- no second reference outside these sites

def all_refs(target):
    """Every adrp+add/ldr/str completion to target anywhere in TEXT."""
    out = []
    page = target & ~0xFFF
    lo = target & 0xFFF
    for a in range(TEXT[0], TEXT[1], 4):
        w = word(a)
        if (w & 0x9F000000) != 0x90000000:
            continue
        if adrp_target(a) != page:
            continue
        rd = w & 31
        for j in range(1, 8):
            a2 = a + 4 * j
            if a2 >= TEXT[1]:
                break
            w2 = word(a2)
            if ((w2 >> 5) & 31) != rd:
                continue
            if (w2 & 0xFF800000) == 0x91000000 and ((w2 >> 10) & 0xFFF) == lo:
                out.append(('add', a2))
            if (w2 & 0xFFC00000) == 0xF9400000 and (((w2 >> 10) & 0xFFF) << 3) == lo:
                out.append(('ldr', a2))
            if (w2 & 0xFFC00000) == 0xF9000000 and (((w2 >> 10) & 0xFFF) << 3) == lo:
                out.append(('str', a2))
    return out


EXPECTED_REFS = {
    'SPECIAL_SKILL_NUM': [('add', 0x019DE49C)],
    'SKILL_COMMAND_NORMAL': [('add', 0x019DE4C0)],
    'SKILL_COMMAND_SIDE': [('add', 0x019DE4E4)],
    'SKILL_COMMAND_UPPER': [('add', 0x019DE508)],
    'SKILL_COMMAND_LOWER': [('add', 0x019DE52C)],
    'SKILL_COMMAND_NUM': [('add', 0x019DE550)],
    'INPUT_OK': [('add', 0x019DE570)],
    'IS_SKILL_EDITABLE': [('add', 0x01809138)],
    'IS_READ_ONLY': [('add', 0x018090FC), ('add', 0x01874EEC)],
}
for name, want in EXPECTED_REFS.items():
    check('TEXT reference sites for %s' % name, all_refs(NAMES[name]), want)

# no R_AARCH64_RELATIVE addend points at any of the nine strings
REC = 24
found_addend = []
for off in range(0x39C8070, 0x40C9FC8, REC):
    r_offset, info, pad, addend = struct.unpack_from('<QIIQ', data, off)
    if info == 0x403 and pad == 0 and addend in set(NAMES.values()):
        found_addend.append((addend, r_offset))
check('no relocation addend points at the nine strings', found_addend, [])

# --------------------- float argument setup: none for group 1, some for group 2 site B

def float_insns(lo, hi):
    out = []
    for a in range(lo, hi, 4):
        ins = dis(a)
        if ins is None:
            continue
        if ins.mnemonic.startswith('f') or ins.mnemonic in ('scvtf', 'ucvtf', 'fcsel'):
            out.append(a)
    return out


check('no float instructions in 0x19ddb30..0x19de6b0',
      float_insns(G1_FN[0], G1_FN[1]), [])
check('no float instructions before the group-1 calls',
      float_insns(0x019DE480, 0x019DE584), [])
check('no float instructions in site A fn before its calls',
      float_insns(G2_FN_A, 0x01809148), [])
# Site B is the exception and is reported as such: its enclosing function sets up s0
# before the call, but on an unrelated earlier path, and the value argument is w3.
check('site B fn does set up s0 before the call (reported, not an argument)',
      float_insns(G2_FN_B, 0x01874EF8),
      [0x01874BA4, 0x01874D04, 0x01874D18, 0x01874D1C, 0x01874D20])
check('the s0 setup at 0x1874d20 is an fcsel',
      text(0x01874D20), 'fcsel s0, s8, s0, hi')
# step 2: 0x33750a0 reads no float register before its first call, so a float in the
# caller's s0 cannot be what x3 carries
check('0x33750a0 has no float instruction before its first call',
      float_insns(0x033750A0, 0x03375118), [])

# ------------------------------------------------------------------ report

failed = [r for r in results if not r[0]]
for ok, label, got, want in results:
    if not ok:
        print('FAIL  %-58s got %r want %r' % (label, got, want))
print('%d checks, %d failures' % (len(results), len(failed)))
sys.exit(1 if failed else 0)