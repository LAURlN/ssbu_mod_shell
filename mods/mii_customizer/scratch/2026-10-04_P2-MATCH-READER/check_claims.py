"""Re-derives the instructions and offsets cited in research/P2-MATCH-READER.md. Exit 0 = all match."""
import struct, sys, hashlib
from pathlib import Path
import capstone
IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
def dis(a):
    i = next(md.disasm(data[a:a + 4], a))
    return f'{i.mnemonic} {i.op_str}'
def adrp_add(a):
    w, w2 = struct.unpack_from('<II', data, a)
    sx = lambda v, b: v - (1 << b) if v & (1 << (b - 1)) else v
    return (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12) + ((w2 >> 10) & 0xFFF)
def bl_callers(t):
    n = []
    for a in range(0x100, 0x39C8000, 4):
        w = struct.unpack_from('<I', data, a)[0]
        if (w & 0xFC000000) == 0x94000000 and a + (((w & 0x3FFFFFF) ^ 0x2000000) - 0x2000000) * 4 == t: n.append(a)
    return n
C = [
 # A: record (sp+0x240) -> local L (sp+0x3f0) -> entry
 (0x1791774, 'add x2, sp, #0x240'), (0x1791778, 'bl #0x17c8210'),
 (0x17918b4, 'ldr x8, [sp, #0x380]'), (0x17918b8, 'str x8, [sp, #0x480]'),
 (0x1791904, 'add x2, sp, #0x3f0'), (0x179190c, 'bl #0x179e440'),
 (0x179e454, 'mov w8, #0x1c8'), (0x179e60c, 'add x1, x2, #0x28'), (0x179e610, 'add x0, x8, #0x38'), (0x179e618, 'bl #0x16b6bb0'),
 (0x16b6d18, 'ldp x9, x10, [x20, #0x68]'), (0x16b6d24, 'stp x9, x10, [x19, #0x68]'),
 # ID into the second table in 0x17914d0
 (0x1791a30, 'ldr w8, [x20, #0x14]'), (0x1791a34, 'str w8, [sp, #8]'), (0x1791a3c, 'mov w8, #0x240'),
 (0x1791a40, 'madd x8, x23, x8, x19'), (0x1791a44, 'ldp x10, x11, [sp]'), (0x1791a58, 'str x11, [x8, #0xe58]'),
 # 0x25cc840: second writer of both tables
 (0x25cce7c, 'madd x8, x8, x9, x24'), (0x25cce80, 'ldr w9, [x8, #0x14]'),
 (0x25cd064, 'add x24, x23, #0xe50'), (0x25cd080, 'ldr w28, [sp, #0x278]'), (0x25cd0e4, 'bl #0x17c8210'),
 (0x25cd314, 'ldr x9, [sp, #0x278]'), (0x25cd328, 'stp x9, x10, [x24, #8]'), (0x25cd3d0, 'bl #0x179e440'),
 # 0x230d4c0: ID read back from the second table, then record load
 (0x230ec98, 'smaddl x20, w24, w8, x21'), (0x230eca0, 'ldr x8, [x20, #0xe58]'), (0x230ecb8, 'stp x8, x10, [sp, #0x78]'),
 (0x230f238, 'ldr w20, [sp, #0x78]'), (0x230f2a0, 'mov x1, x20'), (0x230f2a4, 'bl #0x17c8210'),
 # copy-out sites of entry+0x38
 (0x18384f4, 'add x1, x8, x9'), (0x18384fc, 'bl #0x15547e0'),
 (0x1897a78, 'add x1, x8, x9'), (0x1897a7c, 'bl #0x16b6bb0'),
 (0x19617e8, 'add x1, x20, #0x38'), (0x19617f4, 'bl #0x15547e0'),
 (0x230ed38, 'add x1, x8, #0x38'), (0x230ed44, 'bl #0x15547e0'),
 (0x2316290, 'add x1, x8, x9'), (0x23162a0, 'bl #0x15547e0'),
 (0x2341bf4, 'add x1, x8, #0x38'), (0x2341bf8, 'bl #0x16b6bb0'), (0x2341c0c, 'ldr x13, [x8, #0xe58]'), (0x2341c3c, 'str x13, [x26, x10]'),
 (0x25cb350, 'add x1, x8, #0x38'), (0x25cb35c, 'bl #0x15547e0'),
 (0x25ccc18, 'add x1, x8, #0x38'), (0x25ccc20, 'bl #0x15547e0'),
 (0x3311574, 'add x2, x8, x9'), (0x331157c, 'b #0x3311190'),
 # C: loader ID arguments
 (0x14ebb08, 'ldr w21, [x9, #0x26c]'), (0x1810068, 'ldr w1, [x19, #0x100]'), (0x18102c8, 'ldr w1, [x19, #0x100]'),
 (0x1ccb6fc, 'ldr w1, [x19, #0x5d4]'), (0x23710f0, 'ldr w1, [x20, #8]'), (0x2371088, 'ldr w8, [x21, #0x14]'),
 (0x2372a2c, 'ldr w1, [sp, #0x7b4]'), (0x23a0e7c, 'ldr w23, [x8, #0x14]'), (0x23a0f9c, 'str w23, [sp, #0x228]'),
 (0x23a1004, 'ldr w24, [sp, #0x228]'), (0x23a3fa4, 'ldr w24, [sp, #0x228]'), (0x23a5998, 'ldr w28, [sp, #0x248]'),
 (0x23b2ec4, 'ldr w24, [sp, #0x228]'), (0x23bab00, 'ldr w1, [x19, #0xaa8]'), (0x23bac44, 'ldr w26, [x19, #0x8f8]'),
 (0x23bae10, 'ldr w19, [x19, #0xaa8]'), (0x23bb434, 'ldr w1, [x19, #0x8f8]'),
 (0x24932b8, 'ldr w8, [x8, #0x26c]'), (0x24932bc, 'str w8, [sp, #0xc]'), (0x2493384, 'ldr w8, [sp, #0xc]'),
 (0x24cab5c, 'ldr w1, [x8, x9]'), (0x25cce44, 'ldr w9, [x9, #0x26c]'), (0x25ccde0, 'ldr w8, [x8, x9]'),
]
bad = 0; total = 0
def ck(name, got, want):
    global bad, total
    ok = got == want; bad += not ok; total += 1
    print(('ok   ' if ok else 'FAIL ') + f'{name}: {got}' + ('' if ok else f'   expected {want}'))
ck('sha256', hashlib.sha256(data).hexdigest(), 'f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613')
for a, want in C: ck(f'0x{a:x}', dis(a), want)
G = adrp_add(0x17913d4); T = G + 0x3670
ck('G', hex(G), '0x53040f0'); ck('T', hex(T), '0x5307760')
ck('T == 0x52c4180+0x435e0', hex(0x52c4180 + 0x435e0), hex(T))
ck('adrp/add 0x25cb338', hex(adrp_add(0x25cb338)), hex(T))
ck('adrp/add 0x2341bd0', hex(adrp_add(0x2341bd0)), hex(T))
ck('adrp/add 0x230ec88', hex(adrp_add(0x230ec88)), hex(T))
ck('adrp/add 0x236f3fc (sel 2)', hex(adrp_add(0x236f3fc)), hex(G + 0x18a8))
R, L = 0x240, 0x3f0                       # stack offsets in 0x17914d0
s_off = (0x480 - L) - 0x28                # offset inside S of record +0x140
ck('S offset of record+0x140', hex(s_off), '0x68')
ck('record offset copied at 0x17918b4', hex(0x380 - R), '0x140')
ck('entry offset of record+0x142', hex(0x38 + s_off + 2), '0xa2')
ck('specials p0 absolute', hex(T + 0xa2), '0x5307802')
ck('ID p0 absolute', hex(T + 0xe58), '0x53085b8')
ck('0x3618 form == entry+0x38', hex(0x52c4180 + 0x43618), hex(T + 0x38))
c = bl_callers(0x17c8210)
ck('loader bl callers', len(c), 139)
ck('loader callers outside editor', len([a for a in c if not 0x19d0950 <= a <= 0x19dc304]), 22)
ck('0x25cc840 bl callers', [hex(a) for a in bl_callers(0x25cc840)], ['0x23a0394', '0x23a33e8', '0x23a6474', '0x23a9e78', '0x23ac8ec', '0x23b23b8'])
ck('0x25cb100 bl callers', [hex(a) for a in bl_callers(0x25cb100)], ['0x188c084', '0x24a2f9c'])
ck('0x3311530 bl callers', [hex(a) for a in bl_callers(0x3311530)], ['0x1806dc4', '0x1806ddc'])
ck('0x17914d0 bl callers', [hex(a) for a in bl_callers(0x17914d0)], ['0x179140c', '0x1791420'])
print(f'{total} checks, {bad} failures')
sys.exit(1 if bad else 0)
