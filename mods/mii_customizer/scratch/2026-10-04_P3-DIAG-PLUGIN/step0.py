"""P3-DIAG-PLUGIN step 0: offline prerequisites for the three hook sites.
Read-only on gamedata/ssbu-13.0.4/main.bin and the lab's Skyline runtime copy.
usage (from anywhere): python step0.py      exit 0 = all checks pass"""
import hashlib, struct, sys, array
from pathlib import Path
HERE = Path(__file__).resolve().parent
WS = HERE.parents[3]
sys.path.insert(0, str(WS / 'mods/ssbu_mod_new/builds/.cache/dk_cargo/python'))
sys.path.insert(0, str(HERE))
import capstone, nso
IMG = WS / 'gamedata/ssbu-13.0.4/main.bin'
SHA = 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613'
SKY = WS / 'testenv/ryujinx/data/sdcard/atmosphere/contents/01006A800016E000/exefs/subsdk9'
TEXT_END = 0x39C8000
d = IMG.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
ok = bad = 0


def check(name, cond, detail=''):
    global ok, bad
    if cond:
        ok += 1
    else:
        bad += 1
    print(('PASS ' if cond else 'FAIL ') + name + (' | ' + detail if detail else ''))


def u32(a): return struct.unpack_from('<I', d, a)[0]
def u64(a): return struct.unpack_from('<Q', d, a)[0]
def sx(v, b): return v - (1 << b) if v & (1 << (b - 1)) else v


def dis(w, a):
    i = next(md.disasm(struct.pack('<I', w), a), None)
    return f'{i.mnemonic} {i.op_str}' if i else '.word'


# R_AARCH64_RELATIVE table (bounds as in rel.py): pointer slots are zero in the file and filled by rtld.
RELA = {}
for o in range(0x39c8070, 0x40c9fc8, 24):
    off, info, add = struct.unpack_from('<QQq', d, o)
    if info & 0xffffffff == 0x403:
        RELA[off] = add


def slot(a): return RELA.get(a, -1)


def in_sites(t):
    return 0x4e53d0 <= t < 0x4e5400 or 0x179e440 <= t < 0x179e460 or 0x17c8210 <= t < 0x17c8230


def pcrel(w):
    return ((w & 0x1F000000) == 0x10000000 or (w & 0x7C000000) == 0x14000000 or (w & 0xFF000010) == 0x54000000
            or (w & 0x7E000000) in (0x34000000, 0x36000000) or (w & 0x3B000000) == 0x18000000)


print('== input')
check('image sha256', hashlib.sha256(d).hexdigest() == SHA, f'size 0x{len(d):x}')

print('== 0a offset convention: old-mod vtable patch (handbook/12_native_offsets_13_0_4_only.md line 9, tier A)')
# mods/ssbu_mod_new/src/pgwr/plugin/src/status/special_hi.rs:534-541,578-585: at load time that plugin
# requires [base+0x4faf9c8+0x210] == base+0x68d9c0, [..+0x220] == base+0x68d9e0 and these code bytes,
# with base = getRegionAddress(Region::Text); only then it patches, and the patched +0x220 handler fired on console.
check('relocated slot [0x4faf9c8+0x210] == 0x68d9c0', slot(0x4faf9c8 + 0x210) == 0x68d9c0, hex(slot(0x4faf9c8 + 0x210)))
check('relocated slot [0x4faf9c8+0x220] == 0x68d9e0', slot(0x4faf9c8 + 0x220) == 0x68d9e0, hex(slot(0x4faf9c8 + 0x220)))
check('bytes at 0x68d9c0 == DEFAULT_RESET_CODE', d[0x68d9c0:0x68d9c8] == bytes([0xe0, 3, 0, 0x32, 0xc0, 3, 0x5f, 0xd6]),
      dis(u32(0x68d9c0), 0x68d9c0) + ' ; ' + dis(u32(0x68d9c4), 0x68d9c4))
check('bytes at 0x68d9e0 == DEFAULT_DAMAGED_CODE', d[0x68d9e0:0x68d9e4] == bytes([0xc0, 3, 0x5f, 0xd6]),
      dis(u32(0x68d9e0), 0x68d9e0))

print('== 0b hook sites')
SITES = {0x4e53e0: [0xf9401c00, 0xf9400008, 0xf9401903, 0xd61f0060], 0x179e440: None, 0x17c8210: None}
words = array.array('I')
words.frombytes(d[:TEXT_END])
targets = {}
for idx, w in enumerate(words):
    a = idx * 4
    if (w & 0x7C000000) == 0x14000000:
        t = a + (sx(w & 0x3FFFFFF, 26) << 2)
    elif (w & 0xFF000010) == 0x54000000 or (w & 0x7E000000) == 0x34000000:
        t = a + (sx((w >> 5) & 0x7FFFF, 19) << 2)
    elif (w & 0x7E000000) == 0x36000000:
        t = a + (sx((w >> 5) & 0x3FFF, 14) << 2)
    else:
        continue
    if in_sites(t):
        targets.setdefault(t, []).append((a, w))
ptrs = {}
for k, v in RELA.items():
    if in_sites(v):
        ptrs.setdefault(v, []).append(k)

for s, exp in SITES.items():
    ws = [u32(s + 4 * k) for k in range(5)]
    print(f'-- site 0x{s:x}')
    for k, w in enumerate(ws):
        print(f'   +{4 * k:#04x} {w:08x}  {dis(w, s + 4 * k)}')
    print('   expected words for the plugin: ' + ', '.join(f'0x{w:08x}' for w in ws[:4]))
    if exp:
        check('  words equal the coordinator-quoted thunk', ws[:4] == exp)
    check('  8-aligned (far hook overwrites exactly 4 words, see skyline check)', s % 8 == 0)
    check('  none of the first 4 words is pc-relative', not any(pcrel(w) for w in ws[:4]))
    prev = u32(s - 4)
    check('  previous word ends a function or is padding',
          prev in (0xD65F03C0, 0) or (prev & 0xFFFFFC1F) == 0xD61F0000 or (prev & 0xFC000000) == 0x14000000,
          f'{prev:08x} {dis(prev, s - 4)}')
    inner = {t: v for t, v in targets.items() if s < t < s + 16}
    check('  no direct branch targets site+4..+0xc', not inner,
          str({hex(k): [hex(a) for a, _ in v] for k, v in inner.items()}))
    innerp = {t: v for t, v in ptrs.items() if s < t < s + 16}
    check('  no relocated pointer slot points at site+4..+0xc', not innerp, str(innerp))
    ent = targets.get(s, [])
    bl = [a for a, w in ent if w >> 26 == 0x25]
    other = [a for a, w in ent if w >> 26 != 0x25]
    print(f'   direct callers: {len(bl)} bl, {len(other)} other branches {[hex(a) for a in other]}; '
          f'data pointers to entry: {[hex(p) for p in ptrs.get(s, [])]}')
    if s == 0x4e53e0:
        check('  entry reached through data pointers only (vtable slots)', not ent and len(ptrs.get(s, [])) >= 2)
    else:
        check('  entry is a bl target', len(bl) > 0)
check('0x179e440 word 4 is the b.hs that consumes the relocated cmp', u32(0x179e450) & 0xFF00001F == 0x54000002,
      dis(u32(0x179e450), 0x179e450))
check('vtable 0x4f89490 +0x270 -> 0x4e53e0, +0x268 -> 0x4e53d0',
      slot(0x4f89490 + 0x270) == 0x4e53e0 and slot(0x4f89490 + 0x268) == 0x4e53d0)
check('vtable 0x4f73738 +0x270 -> 0x4e53e0, +0x268 -> 0x4e53d0',
      slot(0x4f73738 + 0x270) == 0x4e53e0 and slot(0x4f73738 + 0x268) == 0x4e53d0)
check('data pointers to 0x4e53e0 are exactly those two slots',
      sorted(ptrs.get(0x4e53e0, [])) == [0x4f73738 + 0x270, 0x4f89490 + 0x270],
      str([hex(p) for p in ptrs.get(0x4e53e0, [])]))

print('== statics')
m = u32(4)
assert d[m:m + 4] == b'MOD0'
bss0 = m + struct.unpack_from('<i', d, m + 8)[0]
bss1 = m + struct.unpack_from('<i', d, m + 12)[0]
T = 0x5307760
lo, hi = T + 0xa2, T + 0xe58 + 7 * 0x240 + 4
print(f'   MOD0 bss 0x{bss0:x}..0x{bss1:x}; file end 0x{len(d):x}; tables span 0x{lo:x}..0x{hi:x}')
check('all 16 table reads lie inside MOD0 bss', bss0 <= lo and hi <= bss1)
check('player-0 addresses', T + 0xe58 == 0x53085b8 and T + 0xa2 == 0x5307802)
check('special-byte table ends before the ID table (8 entries)', T + 0xa2 + 7 * 0x1c8 + 4 <= T + 0xe58)
check('0x179e440 range-checks w1 < 8 itself', u32(0x179e44c) == 0x7100203F, dis(u32(0x179e44c), 0x179e44c))

print('== 0c Skyline runtime copy in the lab test environment (card copy not hashed by this task)')
sk = SKY.read_bytes()
print('   sha256', hashlib.sha256(sk).hexdigest(), 'size', len(sk))
img, segs, _ = nso.load(str(SKY))


def s32(a): return struct.unpack_from('<I', img, a)[0]


check('A64HookFunction stores the trampoline to *result (0x4454) before calling A64HookFunctionV (0x448c -> 0x40f4)',
      s32(0x4454) == 0xf9000001 and s32(0x448c) == 0x97ffff1a and 0x448c + (sx(s32(0x448c) & 0x3ffffff, 26) << 2) == 0x40f4)
check('far hook: count = 4 when (symbol+8)&7 == 0, else 5',
      s32(0x4170) == 0x91002000 and s32(0x4174) == 0x92400800 and s32(0x4180) == 0x528000a0 and s32(0x418c) == 0x52800080)
check('far hook writes ldr x17,#8 ; br x17 ; .quad replace',
      s32(0x4258) == 0x52800a21 and s32(0x425c) == 0x72ab0001 and s32(0x426c) == 0x52804401 and s32(0x4270) == 0x72bac3e1)
V = [s32(a) for a in range(0x40f4, 0x43d8, 4)]
check('near hook relocates 1 instruction (mov w2,#1) and writes one b (0x14000000 | off)', 0x52800022 in V and 0x52a28000 in V and V.index(0x52800022) < V.index(0x52a28000))
print(f'\n{ok} passed, {bad} failed')
sys.exit(1 if bad else 0)
