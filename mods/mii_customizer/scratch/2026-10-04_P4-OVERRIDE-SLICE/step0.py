"""P4-OVERRIDE-SLICE step 0: offline facts about the 13.0.4 image that plugin 0.2.0 relies on.
usage: python step0.py        exit 0 = all checks pass
Reads workspace gamedata/ssbu-13.0.4/main.bin (flat image, VA == file offset). Runs nothing."""
import hashlib, struct, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
WS = HERE.parents[3]
sys.path.insert(0, str(WS / 'mods/ssbu_mod_new/builds/.cache/dk_cargo/python'))
import capstone
IMAGE = WS / 'gamedata/ssbu-13.0.4/main.bin'
d = IMAGE.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
TEXT = (0x100, 0x39C8000)
ok = bad = 0


def check(name, cond, detail=''):
    global ok, bad
    ok += bool(cond)
    bad += not cond
    print(('PASS ' if cond else 'FAIL ') + name + (' | ' + str(detail) if detail != '' else ''))


def u32(a): return struct.unpack_from('<I', d, a)[0]
def sx(v, b): return v - (1 << b) if v & (1 << (b - 1)) else v


def dis(a, n):
    out = []
    for k in range(n):
        i = next(md.disasm(d[a + 4 * k:a + 4 * k + 4], a + 4 * k), None)
        out.append(f'{i.mnemonic} {i.op_str}'.strip() if i else '.word')
    return out


def has_seq(ins, *parts):
    """parts appear in this order (not necessarily adjacent)."""
    k = 0
    for line in ins:
        if k < len(parts) and line == parts[k]:
            k += 1
    return k == len(parts)


print('== image')
check('main.bin sha256 f70c97d2...7613', hashlib.sha256(d).hexdigest() == 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613')

# relocations (R_AARCH64_RELATIVE) and dynsym
REL = {}
for o in range(0x39c8070, 0x40c9fc8, 24):
    off, info, add = struct.unpack_from('<QQq', d, o)
    if info & 0xffffffff == 0x403:
        REL[off] = add
m = u32(4)
dyn = m + struct.unpack_from('<i', d, m + 4)[0]
tags = {}
while True:
    t, v = struct.unpack_from('<QQ', d, dyn)
    dyn += 16
    if t == 0:
        break
    tags[t] = v
symtab, strtab = tags[6], tags[5]
SYM = {}
for i in range((strtab - symtab) // 24):
    name, info, other, shndx, value, size = struct.unpack_from('<IBBHQQ', d, symtab + 24 * i)
    e = d.find(b'\0', strtab + name)
    s = d[strtab + name:e].decode('latin1')
    if s and shndx:
        SYM[s] = (value, size)

print('== hook sites')
PARAM, CUSTOM = 0x4e53e0, 0x4e53f0
check('0x4e53e0 words f9401c00 f9400008 f9401903 d61f0060', [u32(PARAM + 4 * k) for k in range(4)] == [0xf9401c00, 0xf9400008, 0xf9401903, 0xd61f0060])
cw = [u32(CUSTOM + 4 * k) for k in range(4)]
check('0x4e53f0 words f9401c00 f9400008 f9401d03 d61f0060', cw == [0xf9401c00, 0xf9400008, 0xf9401d03, 0xd61f0060], ' '.join(f'{w:08x}' for w in cw))
check('0x4e53f0 = ldr x0,[x0,#0x38]; ldr x8,[x0]; ldr x3,[x8,#0x38]; br x3',
      dis(CUSTOM, 4) == ['ldr x0, [x0, #0x38]', 'ldr x8, [x0]', 'ldr x3, [x8, #0x38]', 'br x3'], dis(CUSTOM, 4))
check('0x4e53f0 is 8-aligned (far hook form overwrites exactly its 4 words)', CUSTOM % 8 == 0)
check('next function starts at 0x4e5400 (cmp w0,#7)', dis(0x4e5400, 1) == ['cmp w0, #7'], dis(0x4e5400, 2))
slots = sorted(k for k, v in REL.items() if v == CUSTOM)
check('exactly two relocated pointers to 0x4e53f0: slot +0x278 of vtables 0x4f73738 and 0x4f89490',
      slots == [0x4f73738 + 0x278, 0x4f89490 + 0x278], [hex(s) for s in slots])
inner = [k for k, v in REL.items() if CUSTOM < v < CUSTOM + 0x10]
check('no relocated pointer into 0x4e53f4..0x4e53fc', not inner, inner)
branches = []
for a in range(TEXT[0], TEXT[1], 4):
    w = u32(a)
    if (w & 0x7C000000) == 0x14000000:
        t = a + (sx(w & 0x3FFFFFF, 26) << 2)
    elif (w & 0xFF000010) == 0x54000000 or (w & 0x7E000000) == 0x34000000:
        t = a + (sx((w >> 5) & 0x7FFFF, 19) << 2)
    elif (w & 0x7E000000) == 0x36000000:
        t = a + (sx((w >> 5) & 0x3FFF, 14) << 2)
    else:
        continue
    if PARAM <= t < CUSTOM + 0x10:
        branches.append((a, t))
check('no direct branch (b/bl/b.cond/cbz/tbz) targets 0x4e53e0..0x4e53fc', not branches, [(hex(a), hex(t)) for a, t in branches][:4])

print('== vtable 0x4f89490 and its parent link')
check('slot +0x270 of 0x4f89490 -> 0x4e53e0, +0x268 -> 0x4e53d0', REL.get(0x4f89490 + 0x270) == PARAM and REL.get(0x4f89490 + 0x268) == 0x4e53d0)
check('slot +0x98 (get_int) of 0x4f89490 and 0x4f73738 -> 0x4e4600', REL.get(0x4f89490 + 0x98) == 0x4e4600 and REL.get(0x4f73738 + 0x98) == 0x4e4600)
g = dis(0x4e4600, 7)
check('0x4e4600 = [x0+0x18][(id>>24)&0xf] -> slot +0x10 with id&0xffffff; does not touch [x0+0x38] (no path into the param thunk)',
      g == ['ldr x9, [x0, #0x18]', 'ubfx w8, w1, #0x18, #4', 'and w1, w1, #0xffffff', 'ldr x0, [x9, w8, uxtw #3]', 'ldr x8, [x0]', 'ldr x2, [x8, #0x10]', 'br x2'], g)
c = dis(0x688508, 32)
check('constructor 0x688508: 0x98-byte object, stp vtable,parent -> [obj], str obj -> [parent+0x50]',
      has_seq(c, 'mov w1, #0x98', 'stp x8, x19, [x20]', 'str x20, [x19, #0x50]'), [x for x in c if 'x20' in x][:6])
adds = []
for a in range(TEXT[0], TEXT[1], 4):
    w = u32(a)
    if (w & 0x9F000000) == 0x90000000:
        page = (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12)
        if page == 0x4f89000:
            rd = w & 31
            for j in range(1, 8):
                w2 = u32(a + 4 * j)
                if (w2 & 0xFF800000) == 0x91000000 and ((w2 >> 5) & 31) == rd and ((w2 >> 10) & 0xFFF) == 0x490:
                    adds.append(a + 4 * j)
check('vtable 0x4f89490 is materialised at three code sites: the constructor 0x688524 and its two own slot-0/1 functions',
      adds == [0x688524, 0x6f1870, 0x6f18d0] and REL.get(0x4f89490) == 0x6f1860 and REL.get(0x4f89498) == 0x6f18c0, [hex(a) for a in adds])

print('== exported functions the plugin imports (dynsym of main)')
EXPORTS = {
    'get_kind': '_ZN3app7utility8get_kindEPKNS_26BattleObjectModuleAccessorE',
    'get_int': '_ZN3app8lua_bind24WorkModule__get_int_implEPNS_26BattleObjectModuleAccessorEi',
    'module_accessor': '_ZN3app16sv_battle_object15module_accessorEj',
    'category': '_ZN3app16sv_battle_object8categoryEj',
    'kind': '_ZN3app16sv_battle_object4kindEj',
    'entry_id': '_ZN3app16sv_battle_object8entry_idEj',
}
A = {}
for short, name in EXPORTS.items():
    A[short] = SYM.get(name, (0, 0))
    check(f'exported: {name}', A[short][0] != 0, f'0x{A[short][0]:x} size 0x{A[short][1]:x}')
LOOKUP = 'bl #0x3ac560'
gk = dis(A['get_kind'][0], A['get_kind'][1] // 4)
check('get_kind(accessor): null-checks x0, reads the object id at [accessor+8], looks the object up, returns [object+0xc] or -1',
      has_seq(gk, 'cbz x0, #0x15ce04c', 'ldr w0, [x0, #8]', LOOKUP, 'mov w0, #-1', 'ldr w0, [x19, #0xc]'), gk[:6])
gi = dis(A['get_int'][0], 4)
check('WorkModule::get_int wrapper = ldr x0,[x0,#0x50]; ldr x8,[x0]; ldr x2,[x8,#0x98]; br x2',
      gi == ['ldr x0, [x0, #0x50]', 'ldr x8, [x0]', 'ldr x2, [x8, #0x98]', 'br x2'], gi)
for short, tail in (('module_accessor', ['ldr x0, [x0, #0x20]']), ('category', ['ldr w8, [x0, #8]', 'lsr w0, w8, #0x1c']),
                    ('kind', ['ldr w0, [x0, #0xc]']), ('entry_id', ['ldr w0, [x0, #0x10]'])):
    ins = dis(A[short][0], A[short][1] // 4)
    check(f'sv_battle_object::{short}(id): object lookup, state byte [obj+0x3a] > 3 or the static dummy, then {"; ".join(tail)}',
          has_seq(ins, LOOKUP, 'ldrb w8, [x0, #0x3a]', 'cmp w8, #3', *tail) and ins.count(LOOKUP) == 1, ins[3:9])
    calls = [x for x in ins if x.startswith('bl ') or x.startswith('blr')]
    check(f'  {short}: only calls are the lookup and the one-time static-dummy initialisation (guard acquire/release, constructor)',
          sorted(set(calls)) == sorted({LOOKUP, 'bl #0x39c0100', 'bl #0x3a9ab0', 'bl #0x39c0110'}), sorted(set(calls)))
lk = dis(0x3ac560, 3)
check('object lookup 0x3ac560 rejects ids whose category (id>>28) is above 4', lk == ['lsr w8, w0, #0x1c', 'cmp w8, #4', 'b.hi #0x3ac654'] and dis(0x3ac654, 3) == ['mov x8, xzr', 'mov x0, x8', 'ret'], lk)
check('object lookup compares the stored id with the requested one (stale ids give null)', dis(0x3ac644, 4) == ['umaddl x8, w8, w10, x9', 'ldr w9, [x8, #8]', 'cmp w9, w0', 'b.eq #0x3ac658'])
gcat = SYM.get('_ZN3app7utility12get_categoryEj', (0, 0))
check('the game\'s own utility::get_category(id) is `lsr w0,w0,#0x1c; ret` (same rule as the binding\'s inline get_category)',
      gcat[0] != 0 and dis(gcat[0], 2) == ['lsr w0, w0, #0x1c', 'ret'], hex(gcat[0]))
ve = SYM.get('_ZN3app11FighterUtil17is_valid_entry_idERNS_26BattleObjectModuleAccessorE', (0, 0))
vi = dis(ve[0], ve[1] // 4) if ve[0] else []
check('FighterUtil::is_valid_entry_id(accessor) reads work int 0x10000000 through [accessor+0x50] slot +0x98 and compares with -1',
      has_seq(vi, 'ldr x0, [x0, #0x50]', 'ldr x8, [x8, #0x98]', 'mov w1, #0x10000000', 'blr x8', 'cmn w0, #1'), vi)

print('== per-player tables stay inside .bss')
check('T+0xe58+7*0x240+4 and T+0xa2+7*0x1c8+4 below the image end of bss 0x7446100; above bss start 0x52a9000',
      0x52a9000 <= 0x5307760 + 0xa2 and 0x5307760 + 0xe58 + 7 * 0x240 + 4 <= 0x7446100)

print(f'\n{ok} passed, {bad} failed')
sys.exit(1 if bad else 0)
