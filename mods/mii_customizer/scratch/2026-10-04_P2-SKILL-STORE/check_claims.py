"""Re-derives every instruction cited in research/P2-SKILL-STORE.md from the image. Exit 0 = all match."""
import struct, sys, hashlib
from pathlib import Path
import capstone
IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
def dis(a):
    i = next(md.disasm(data[a:a + 4], a))
    return f'{i.mnemonic} {i.op_str}'
def adrp_add(a):  # adrp at a, add at a+4 -> target
    w, w2 = struct.unpack_from('<II', data, a)
    sx = lambda v, b: v - (1 << b) if v & (1 << (b - 1)) else v
    return (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12) + ((w2 >> 10) & 0xFFF)
C = [
 (0x180ba30, 'ldr x9, [x0, #0x198]'), (0x180ba88, 'ldr x8, [x9, #0x80]'),
 (0x180ba94, 'ldur x10, [x9, #0x5e]'), (0x180ba98, 'str x10, [x8, #0xf8]'),
 (0x180ba9c, 'ldrb w10, [x9]'), (0x180baa0, 'strb w10, [x8, #0x100]'),
 (0x180baa4, 'ldrb w10, [x9, #1]'), (0x180baa8, 'strb w10, [x8, #0x101]'),
 (0x180baac, 'ldrb w10, [x9, #2]'), (0x180bab0, 'strb w10, [x8, #0x102]'),
 (0x180bab4, 'ldrb w9, [x9, #3]'), (0x180bab8, 'strb w9, [x8, #0x103]'),
 (0x180bac8, 'b #0x19de890'),
 (0x180ba40, 'ldr w8, [x8, #0xe0]'), (0x180ba58, 'ldr x9, [x9, #0x80]'),
 (0x180ba60, 'ldrb w12, [x11, #0xcba]'), (0x180ba64, 'ldrb w10, [x9, #0x100]'),
 (0x180bacc, 'strb w10, [x11, #0xcba]'), (0x180bad8, 'ldrb w11, [x9, #0x101]'),
 (0x180baec, 'strb w11, [x12, #0xcbb]'), (0x180baf4, 'ldrb w11, [x9, #0x102]'),
 (0x180bb08, 'strb w11, [x12, #0xcbc]'), (0x180bb10, 'ldrb w9, [x9, #0x103]'),
 (0x180bb28, 'strb w9, [x11, #0xcbd]'), (0x180bb3c, 'bl #0x19cb2e0'),
 (0x180bb48, 'strb w8, [x19, #0x161]'), (0x180bb4c, 'bl #0x180cf10'),
 (0x180fc3c, 'ldr w1, [x10, x9, lsl #2]'), (0x180fcb0, 'mov x2, x21'), (0x180fcb4, 'bl #0x17c8210'),
 (0x180fc58, 'bl #0x17bd350'),
 (0x17c84d8, 'ldp x9, x10, [x8, #0x140]'), (0x17c84e4, 'stp x9, x10, [x19, #0x140]'),
 (0x17c8508, 'ldr x9, [x8, #0x1a0]'), (0x17c8514, 'str x9, [x19, #0x1a0]'),
 (0x17bd2fc, 'ldp x8, x9, [x20, #0x140]'), (0x17bd308, 'stp x8, x9, [x19, #0x140]'),
 (0x180d328, 'bl #0x17c8530'), (0x180d3d4, 'bl #0x39bfb30'),
 (0x180d6e8, 'bl #0x17bd1b0'), (0x180d704, 'bl #0x17bd1b0'), (0x180d428, 'bl #0x17bd1b0'),
 (0x180d8cc, 'ldrb w9, [x20, #0x142]'), (0x180d8d0, 'cmp w9, #2'), (0x180d8d4, 'b.hi #0x180d71c'),
 (0x180d8d8, 'ldrb w9, [x20, #0x143]'), (0x180d8e0, 'b.hi #0x180d71c'),
 (0x180d8e4, 'ldrb w9, [x20, #0x144]'), (0x180d8ec, 'b.hi #0x180d71c'),
 (0x180d8f0, 'ldrb w9, [x20, #0x145]'), (0x180d8f8, 'b.hi #0x180d71c'),
 (0x180d9c4, 'madd x22, x9, x2, x8'), (0x180d9d0, 'bl #0x39bfb30'), (0x180da08, 'bl #0x17c7bc0'),
 (0x180da10, 'strb w8, [x21, #0xfc]'), (0x180d720, 'bl #0x392e590'),
 (0x1987db4, 'ldr x10, [x19, #0x5e8]'), (0x1987dbc, 'ldrb w13, [x10, #0x100]'),
 (0x1987e7c, 'bl #0x32e0680'), (0x1987e88, 'ldr x9, [sp, #0x1a0]'), (0x1987e8c, 'str x9, [x8, #0xf8]'),
 (0x1987e90, 'ldrb w9, [sp, #0x142]'), (0x1987e94, 'strb w9, [x8, #0x100]'),
 (0x1987ea8, 'ldrb w9, [sp, #0x145]'), (0x1987eac, 'strb w9, [x8, #0x103]'),
 (0x1987ef4, 'bl #0x32deaa0'), (0x1987efc, 'strb w8, [x0, #0x13]'), (0x1987f14, 'strb w8, [x0, #0x16]'),
 (0x32e0cb4, 'ldrb w8, [x24, #0x13]'), (0x32e0cb8, 'cmp w8, #2'), (0x32e0cbc, 'csel w8, wzr, w8, hi'),
 (0x32e0cc0, 'strb w8, [x19, #0x142]'), (0x32e0cf4, 'strb w8, [x19, #0x145]'), (0x32e0c2c, 'str x22, [x19, #0x1a0]'),
 (0x19dcf20, 'cmp w1, #4'), (0x19ddd24, 'str xzr, [x19, #0x100]'), (0x19ddd0c, 'stp x0, x8, [x19, #0xf0]'),
 (0x1809814, 'bl #0x19ddb30'), (0x1982fc0, 'bl #0x19ddb30'),
 (0x1809868, 'str x21, [x19, #0x198]'), (0x1983014, 'str x23, [x19, #0x5e8]'),
]
bad = 0
print('sha256', hashlib.sha256(data).hexdigest())
for a, exp in C:
    got = dis(a); ok = got == exp; bad += not ok
    print(f'{"ok  " if ok else "FAIL"} 0x{a:x}: {got}' + ('' if ok else f'   expected: {exp}'))
A = [(0x180ba8c, 0x5306cba), (0x1809a94, 0x5306b78), (0x180fca8, 0x5306b78), (0x180d6d4, 0x5306b78)]
for a, t in A:
    g = adrp_add(a); ok = g == t; bad += not ok
    print(f'{"ok  " if ok else "FAIL"} adrp+add 0x{a:x} -> 0x{g:x}')
ar = [(0x5306cba - 0x5306b78, 0x142), (0x5306cba + 0x5e - 0x5306b78, 0x1a0), (0x5306d50 - 0x5306b78, 0x1d8)]
for g, t in ar:
    ok = g == t; bad += not ok; print(f'{"ok  " if ok else "FAIL"} offset 0x{g:x}')
print(f'{len(C) + len(A) + len(ar)} checks, {bad} failures'); sys.exit(1 if bad else 0)
