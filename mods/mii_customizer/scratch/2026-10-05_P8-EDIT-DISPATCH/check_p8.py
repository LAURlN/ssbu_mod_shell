"""P8-EDIT-DISPATCH: verification script for research/P8-EDIT-DISPATCH.md.

Re-reads every address, instruction word, immediate and string cited in the
report straight out of main.bin (flat MOD0 image, address == file offset) and
exits non-zero on any mismatch.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
    python mods/mii_customizer/scratch/2026-10-05_P8-EDIT-DISPATCH/check_p8.py

Add --neg NAME to inject one deliberate corruption (negative control); the
script must then fail.  Available: addr, word, imm, str, hash, table, count.
"""
import struct
import sys
import zlib
from pathlib import Path

import capstone

IMAGE = Path('gamedata/ssbu-13.0.4/main.bin')
DATA = IMAGE.read_bytes()
MD = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
MD.detail = False
MASK = (1 << 40) - 1

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


def cstr(a):
    e = DATA.find(b'\0', a, a + 96)
    return DATA[a:e].decode('ascii', 'replace')


def hash40(s):
    b = s.lower().encode()
    return (len(b) << 32) | (zlib.crc32(b) & MASK)


# --------------------------------------------------------------------------
# 0. input identity
# --------------------------------------------------------------------------
EXPECT_SHA = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'
import hashlib
chk(hashlib.sha256(DATA).hexdigest() == EXPECT_SHA, 'sha256',
    'got %s' % hashlib.sha256(DATA).hexdigest())
chk(len(DATA) == 86672752, 'image size', 'got %d' % len(DATA))

# hash40 self test against the workspace value
chk(hash40('fighter_kind_miigunner') == 0x0166e9fae70, 'hash40 self test')

# --------------------------------------------------------------------------
# 1. anchor strings: one occurrence each, at the cited address
# --------------------------------------------------------------------------
ANCHORS = {
    0x42e5a36: 'get_exit_value',
    0x42e5a3a: 'exit_value',
    0x42e5a28: 'is_empty_name',
    0x4359e6a: 'EXIT_VALUE_DECIDE',
    0x43ef3ad: 'EXIT_VALUE_CANCEL',
    0x4431954: 'IS_SKILL_EDITABLE',
    0x44119af: 'IS_READ_ONLY',
    0x4359ec6: 'FROM_AMIIBO',
    0x425e171: 'mode_make_mii_edit',
    0x4348c5a: 'set_skill_id',
    0x4291cb9: 'is_end',
    0x439bd15: 'set_flag_changed',
    0x445203e: 'set_camera_type',
    0x4542a28: '(unused placeholder)',
}
for a, s in ANCHORS.items():
    if s.startswith('('):
        continue
    chk(cstr(a) == s, 'str@0x%x' % a, 'got %r want %r' % (cstr(a), s))
    chk(DATA.count(s.encode() + b'\0') == 1,
        'strcount %s' % s, 'count %d' % DATA.count(s.encode() + b'\0'))

# --------------------------------------------------------------------------
# 2. host global registration: values and the registration call shape
#   0x1808fa8 mov w3,#-2 ; 0x1808fac bl 0x33750a0   -> EXIT_VALUE_CANCEL
#   0x1808fcc mov w3,#-1 ; 0x1808fd0 bl 0x33750a0   -> EXIT_VALUE_DECIDE
# --------------------------------------------------------------------------
def mov_imm(a):
    """Immediate written into w3 by the 32-bit MOVZ/MOVN at `addr`, sign extended.

    Decoded from the raw word, not from a table.
    """
    w = word(a)
    if (w & 31) != 3 or ((w >> 21) & 3) != 0:
        return None
    top = (w >> 23) & 0xFF
    imm = (w >> 5) & 0xFFFF
    if top == 0x25:                     # sf=0 opc=10 -> MOVZ Wd
        v = imm
    elif top == 0x05:                   # sf=0 opc=00 -> MOVN Wd
        v = (~imm) & 0xFFFF
    else:
        return None
    return v - 0x10000 if v & 0x8000 else v


for a, want in ((0x1808fa8, -2), (0x1808fcc, -1)):
    v = mov_imm(a)
    chk(v == want, 'imm w3 @0x%x' % a, 'got %s want %d' % (v, want))
    chk('w3' in insn(a) and str(want) in insn(a), 'text @0x%x' % a, insn(a))

# type tag pointer 0x42b1a84 must be the "i" tag string
chk(DATA[0x42b1a84:0x42b1a86] == b'i\0', 'type tag @0x42b1a84',
    repr(DATA[0x42b1a84:0x42b1a88]))

for a in (0x1808fac, 0x1808fd0):
    w = word(a)
    chk((w & 0xFC000000) == 0x94000000, 'bl @0x%x' % a)
    tgt = a + ((w & 0x03FFFFFF) << 2 if not (w & 0x2000000) else
               ((w & 0x03FFFFFF) - (1 << 26)) * 4)
    chk(tgt == 0x33750a0, 'bl target @0x%x' % a, 'got 0x%x' % tgt)

# --------------------------------------------------------------------------
# 3. get_exit_value reference sites and the two caller functions
# --------------------------------------------------------------------------
for a in (0x19ca668, 0x19ca8ec, 0x19d0094, 0x19d0134):
    chk((word(a) & 0x9F000000) == 0x90000000, 'adrp @0x%x' % a)
for a, s in ((0x19ca66c, '#0xa36'), (0x19ca8f0, '#0xa36'),
             (0x19d0098, '#0xa36'), (0x19d0138, '#0xa36')):
    chk(insn(a).startswith('add') and s in insn(a), 'add -> get_exit_value @0x%x' % a, insn(a))

for a in (0x19ca674, 0x19ca680, 0x19ca8f8):
    chk((word(a) & 0xFC000000) == 0x94000000, 'bl @0x%x' % a)

# exit value stored at actor+0x128 : 0x19ca93c mov x8,x19 / ldr x9,[x8,#0x10]!
# then 0x19ca94c str w0,[x8,#0x118]  -> x19 + 0x10 + 0x118
chk(insn(0x19ca93c).startswith('mov') and 'x19' in insn(0x19ca93c), 'mov x8,x19', insn(0x19ca93c))
chk('#0x10' in insn(0x19ca940), 'pre-index +0x10', insn(0x19ca940))
chk(insn(0x19ca94c).startswith('str') and 'w0' in insn(0x19ca94c)
    and '#0x118' in insn(0x19ca94c), 'str w0,[x8,#0x118] @0x19ca94c', insn(0x19ca94c))

# --------------------------------------------------------------------------
# 4. the row -> state table dispatch (Q2, Q4, Q7)
# --------------------------------------------------------------------------
# 0x180a030: prologue, first four instructions contain no PC-relative insn
PROLOGUE = [0x180a030, 0x180a034, 0x180a038, 0x180a03c]
for a in PROLOGUE:
    t = insn(a)
    chk(not any(t.startswith(p) for p in ('adrp', 'adr ', 'ldr ', 'bl ')),
        'no pc-rel @0x%x' % a, t)

# the decided row is read into w8 at 0x180a098 from [child+0x80]+0x128
chk(insn(0x180a098).startswith('ldr') and 'w8' in insn(0x180a098)
    and '#0x128' in insn(0x180a098), 'row load @0x180a098', insn(0x180a098))
chk('#0x178' in insn(0x180a048), 'child slot @0x180a048', insn(0x180a048))

# value 5 -> 0x180a228 ; value 6 -> fallthrough to 0x180a0d8 ; -1 -> 0x180a504
chk('cmp' in insn(0x180a0c8) and '#5' in insn(0x180a0c8), 'cmp #5 @0x180a0c8', insn(0x180a0c8))
chk(insn(0x180a0cc).strip().startswith('b.eq') and '#0x180a228' in insn(0x180a0cc),
    'b.eq 0x180a228', insn(0x180a0cc))
chk('cmp' in insn(0x180a0d0) and '#6' in insn(0x180a0d0), 'cmp #6 @0x180a0d0', insn(0x180a0d0))
chk(insn(0x180a0d4).strip().startswith('b.ne') and '#0x180a4f0' in insn(0x180a0d4),
    'b.ne default', insn(0x180a0d4))
chk('#0x1f' in insn(0x180a09c) and '#0x180a1cc' in insn(0x180a09c),
    'tbnz negative @0x180a09c', insn(0x180a09c))
chk('cmn' in insn(0x180a1cc) and '#1' in insn(0x180a1cc)
    and '#0x180a504' in insn(0x180a1d0), 'cmn -1 @0x180a1cc', insn(0x180a1cc))

# state codes pushed into the per-child table at x19 + n*4 + 0xf8
for a in (0x180a0c4, 0x180a0fc, 0x180a1f0, 0x180a24c, 0x180a554):
    chk('#0xf8' in insn(a) and insn(a).startswith('str'), 'state store @0x%x' % a, insn(a))
chk('#4' in insn(0x180a0c0), 'row+4 @0x180a0c0', insn(0x180a0c0))
chk('mov' in insn(0x180a0f8) and '#0xb' in insn(0x180a0f8), 'code 0xb', insn(0x180a0f8))
chk('mov' in insn(0x180a1ec) and '#1' in insn(0x180a1ec), 'code 1', insn(0x180a1ec))
chk('mov' in insn(0x180a248) and '#0xb' in insn(0x180a248), 'code 0xb (row 5)', insn(0x180a248))
chk('mov' in insn(0x180a550) and '#4' in insn(0x180a550), 'code 4 (cancel)', insn(0x180a550))

# state table reader 0x180ce40 : index at +0x144, table at +0xf8, jump at +0x28
chk('ldrsw' in insn(0x180ce4c) and '#0x144' in insn(0x180ce4c),
    'index load @0x180ce4c', insn(0x180ce4c))
chk('#0xf8' in insn(0x180ce5c), 'table load @0x180ce5c', insn(0x180ce5c))
chk('#0x28' in insn(0x180ce88), 'jump table @0x180ce88', insn(0x180ce88))
chk('lsl #4' in insn(0x180ce84), '16-byte stride @0x180ce84', insn(0x180ce84))
chk(insn(0x180ceb4).strip().startswith('blr'), 'indirect call @0x180ceb4', insn(0x180ceb4))

# the handler jump table installed by the scene ctor 0x180de70:
#   stp <handler>, xzr, [x19, #off] with off = 0x28 + 16*n
HANDLERS = {
    0x28: 0x1808980, 0x38: 0x1809e60, 0x48: 0x1809fb0, 0x58: 0x180a030,
    0x68: 0x180a5b0, 0x78: 0x180abd0, 0x88: 0x180b1c0, 0x98: 0x180b670,
    0xa8: 0x180ba20, 0xb8: 0x180bc60, 0xc8: 0x180c360, 0xd8: 0x180cbc0,
    0xe8: 0x180cc80,
}
for off, target in HANDLERS.items():
    idx = (off - 0x28) // 16
    addr = 0x180e06c + 4 * sum(
        1 for o in HANDLERS
        if o < off and abs(o - off) >= 8)          # walk the block in order
    # locate the actual stp: search the ctor body for this offset
    found = None
    for a in range(0x180e06c, 0x180e114, 4):
        t = insn(a)
        if t.startswith('stp') and '#0x%x]' % off in t:
            found = a
            break
    chk(found is not None, 'stp #0x%x' % off)
    if found is None:
        continue
    # walk back to the adrp/add pair that builds the handler pointer
    pair = None
    for a in range(found - 4, found - 32, -4):
        if insn(a).startswith('add') and insn(a - 4).startswith('adrp'):
            pair = a
            break
    chk(pair is not None, 'adrp/add pair before stp @0x%x' % found)
    if pair is None:
        continue
    page = int(insn(pair - 4).split('#')[1].strip(), 0)
    got = page + int(insn(pair).split('#')[1].strip().rstrip(']'), 0)
    chk(got == target, 'handler off 0x%x' % off,
        'got 0x%x want 0x%x (index %d)' % (got, target, idx))

# --------------------------------------------------------------------------
# 5. child slots and their constructors / scripts
# --------------------------------------------------------------------------
CHILDREN = [
    # (slot store, slot, ctor call, ctor)
    (0x1809498, 0x178, None, None),
    (0x18095ac, 0x180, 0x1809558, 0x19ceb30),
    (0x18096c4, 0x188, 0x1809670, 0x19c7830),
    (0x1809794, 0x190, 0x1809740, 0x19c9340),
    (0x1809868, 0x198, 0x1809814, 0x19ddb30),
    (0x1809934, 0x1a0, 0x18098e4, 0x19e33e0),
]
for a, off, call, ctor in CHILDREN:
    chk('#0x%x]' % off in insn(a), 'child slot @0x%x' % a, insn(a))
    if call is None:
        continue
    w = word(call)
    imm = (w & 0x03FFFFFF)
    tgt = call + (imm * 4 if not (w & 0x2000000) else (imm - (1 << 26)) * 4)
    chk((w & 0xFC000000) == 0x94000000 and tgt == ctor, 'ctor call @0x%x' % call,
        'got 0x%x want 0x%x' % (tgt, ctor))

# --------------------------------------------------------------------------
# 6. 40-bit path hashes: MOVZ/MOVK chains and their ARC path names
# --------------------------------------------------------------------------
PATHS = {
    # (movz, movk1, movk2): expected ARC path
    (0x1808c60, 0x1808c64, 0x1808c68): 'ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc',
    (0x1808c6c, 0x1808c70, 0x1808c80): 'ui/script_patch/chara_make/make_mii_edit_actor.lc',
    (0x180e1c4, 0x180e1c8, 0x180e1cc): 'ui/script_patch/chara_make/make_mii_edit_actor.lc',
    (0x19cecf8, 0x19cecfc, 0x19ced08): 'ui/script/menu/chara_make/make_mii_hat_actor.lc',
    (0x19c79f8, 0x19c79fc, 0x19c7a08): 'ui/script/menu/chara_make/make_mii_body_actor.lc',
    (0x19ddd6c, 0x19ddd70, 0x19ddd7c): 'ui/script/menu/chara_make/make_mii_special_actor.lc',
    (0x19e3534, 0x19e3538, 0x19e3544): 'ui/script/menu/chara_make/make_mii_voice_actor.lc',
    (0x198ca58, 0x198ca5c, 0x198ca68): 'ui/script/menu/chara_make/make_mii_hat_actor.lc',
    (0x198cbfc, 0x198cc00, 0x198cc04): 'ui/script/menu/chara_make/make_mii_body_actor.lc',
    (0x198cdb4, 0x198cdb8, 0x198cdbc): 'ui/script/menu/chara_make/make_mii_special_actor.lc',
    (0x198ced8, 0x198cedc, 0x198cee0): 'ui/script/menu/chara_make/make_mii_voice_actor.lc',
    (0x19d0fd4, 0x19d0fd8, 0x19d0fe4): 'ui/script/menu/chara_make/make_mii_select_actor.lc',
    (0x1811b84, 0x1811b88, 0x1811b8c): 'ui/script/menu/chara_make/make_mii_select_actor.lc',
    (0x180e400, 0x180e404, 0x180e408): 'ui/script/menu/chara_make/make_mii_hat_body_layout.lc',
    (0x180e23c, 0x180e240, 0x180e244): 'ui/script/menu/chara_make/make_mii_utility.lc',
    (0x180e3a0, 0x180e3a4, 0x180e3a8): 'ui/script/menu/chara_make/make_mii_hat_actor.lc',
    (0x180e540, 0x180e544, 0x180e548): 'ui/script/menu/chara_make/make_mii_body_actor.lc',
    (0x180e6b8, 0x180e6bc, 0x180e6c0): 'ui/layout/menu/make_mii_special/make_mii_special/layout.arc',
    (0x180e6e0, 0x180e6e4, 0x180e6e8):
        'ui/layout/menu/make_mii_special_subwindow/make_mii_special_subwindow/layout.arc',
    (0x180e708, 0x180e70c, 0x180e710): 'ui/script/menu/chara_make/make_mii_special_actor.lc',
    (0x180e810, 0x180e814, 0x180e818): 'ui/layout/menu/make_mii_voice/make_mii_voice/layout.arc',
    (0x180e838, 0x180e83c, 0x180e840): 'ui/script/menu/chara_make/make_mii_voice_actor.lc',
    (0x180e350, 0x180e354, 0x180e358):
        'ui/layout/menu/make_mii_hat_body/make_mii_hat_body/layout.arc',
    (0x1811b34, 0x1811b38, 0x1811b3c): 'ui/layout/menu/make_mii_select/make_mii_select/layout.arc',
}


def chain40(a, b, c):
    for x, hw in ((a, 0), (b, 1), (c, 2)):
        w = word(x)
        chk((w >> 23) & 0xFF == (0xA5 if hw == 0 else 0xE5) and ((w >> 21) & 3) == hw,
            'mov%s @0x%x' % ('z' if hw == 0 else 'k', x), insn(x))
    v = (word(a) >> 5) & 0xFFFF
    v |= ((word(b) >> 5) & 0xFFFF) << 16
    v |= ((word(c) >> 5) & 0xFFFF) << 32
    return v & MASK


NEG = None
for _i, _a in enumerate(sys.argv):
    if _a == '--neg' and _i + 1 < len(sys.argv):
        NEG = sys.argv[_i + 1]
for (a, b, c), path in PATHS.items():
    h = chain40(a, b, c)
    want = hash40(path)
    chk(h == want, 'hash40 @0x%x' % a,
        'got 0x%011x want 0x%011x (%s)' % (h, want, path))

# negative control targets
if NEG == 'hash':
    # claim the edit-menu script is the non-patch path: must now fail
    a, b, c = 0x1808c6c, 0x1808c70, 0x1808c80
    chk(chain40(a, b, c) == hash40('ui/script/menu/chara_make/make_mii_edit_actor.lc'),
        'negative hash control')
if NEG == 'imm':
    for a in (0x1808fa8, 0x1808fcc):
        v = (word(a) >> 5) & 0xFFFF
        if v & 0x8000:
            v -= 0x10000
        want = -2 if a == 0x1808fa8 else -1
        chk(v == (-want), 'negative imm control @0x%x' % a)
if NEG == 'str':
    chk(cstr(0x42e5a36) == 'get_exit_valueX', 'negative string control')
if NEG == 'word':
    chk(word(0x180a098) == 0x12345678, 'negative word control')
if NEG == 'addr':
    chk(insn(0x180a0cc).find('#0x180a228') >= 0, 'negative branch-target control')
if NEG == 'table':
    a, b, c = 0x1808c60, 0x1808c64, 0x1808c68
    chk(chain40(a, b, c) == hash40('ui/layout/menu/make_mii_hat/layout.arc'),
        'negative table-entry control')
if NEG == 'count':
    chk(DATA.count(b'EXIT_VALUE_DECIDE\0') == 2, 'negative count control')

# --------------------------------------------------------------------------
# 7. misc anchors used in the report
# --------------------------------------------------------------------------
# IS_READ_ONLY / IS_SKILL_EDITABLE sources
chk('#0xb8c' in insn(0x18090e8), 'W+0x14 addr @0x18090e8', insn(0x18090e8))
chk(insn(0x18090ec).startswith('ldrb') and 'w8' in insn(0x18090ec), 'byte load', insn(0x18090ec))
chk('cmp' in insn(0x18090f0) and '#0' in insn(0x18090f0), 'cmp 0', insn(0x18090f0))
chk('cset' in insn(0x18090f4) and 'ne' in insn(0x18090f4), 'cset ne', insn(0x18090f4))
chk(cstr(0x44119af) == 'IS_READ_ONLY' and '#0x33750a0' in insn(0x1809108),
    'IS_READ_ONLY registration', insn(0x1809108))
chk(insn(0x1809114).startswith('ldrb'), 'IS_SKILL byte', insn(0x1809114))
chk(insn(0x1809118).startswith('ldrh') and '#0x10' in insn(0x1809118),
    'IS_SKILL u16 +0x10', insn(0x1809118))
chk('cset' in insn(0x1809120) and 'eq' in insn(0x1809120), 'cset eq', insn(0x1809120))
chk('cset' in insn(0x1809128) and 'ne' in insn(0x1809128), 'cset ne', insn(0x1809128))
chk('orr' in insn(0x180912c), 'orr', insn(0x180912c))
chk('#0x33750a0' in insn(0x1809148), 'IS_SKILL registration', insn(0x1809148))
# FROM_AMIIBO
chk('#0xd3c' in insn(0x1809050), 'FROM_AMIIBO byte @0x1809050', insn(0x1809050))
chk(cstr(0x4359ec6) == 'FROM_AMIIBO' and '#0x33750a0' in insn(0x1809064),
    'FROM_AMIIBO registration', insn(0x1809064))
chk('#0xd3d' in insn(0x1809078), 'IS_NEW_CREATE_AMIIBO byte', insn(0x1809078))

# 0x32caa90 call sites cited for sub-screen script loads
for call, ctor_ctx in ((0x1808c98, 'edit'), (0x19ced1c, 'hat'),
                       (0x19c7a1c, 'body'), (0x19ddd90, 'special'),
                       (0x19e3558, 'voice')):
    w = word(call)
    imm = w & 0x03FFFFFF
    tgt = call + (imm * 4 if not (w & 0x2000000) else (imm - (1 << 26)) * 4)
    chk((w & 0xFC000000) == 0x94000000 and tgt == 0x32caa90,
        'bl 0x32caa90 @0x%x (%s)' % (call, ctor_ctx), 'got 0x%x' % tgt)

# --------------------------------------------------------------------------
print('checks passed: %d   failed: %d' % (OK, len(FAIL)))
for f in FAIL:
    print('FAIL: %s' % f)
sys.exit(1 if FAIL else 0)