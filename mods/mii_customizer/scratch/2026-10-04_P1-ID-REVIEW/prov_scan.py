"""Provenance-bound scan: list accesses to <singleton>+OFF where the base register is
demonstrably loaded as  adrp/ldr [GLOBAL] ; ldr xB,[x,#8]  in the same straight-line window.
usage: prov_scan.py GLOBAL OFF[,OFF...]   (hex)"""
import struct, sys
from pathlib import Path
import capstone
data = (Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin').read_bytes()
G = int(sys.argv[1], 16); OFFS = [int(x, 16) for x in sys.argv[2].split(',')]
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
def sx(v, b): return v - (1 << b) if v & (1 << (b - 1)) else v
page, lo = G & ~0xFFF, G & 0xFFF
n = 0
for a in range(0x100, 0x39C8000, 4):
    w = struct.unpack_from('<I', data, a)[0]
    if (w & 0x9F000000) != 0x90000000: continue
    if (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12) != page: continue
    rd = w & 31
    # find ldr xP,[xrd,#lo] within 6 insns
    for j in range(1, 7):
        w2 = struct.unpack_from('<I', data, a + 4 * j)[0]
        if (w2 & 0xFFC00000) == 0xF9400000 and ((w2 >> 5) & 31) == rd and (((w2 >> 10) & 0xFFF) << 3) == lo:
            n += 1
            hits = []
            for ins in md.disasm(data[a + 4 * j:a + 4 * j + 4 * 400], a + 4 * j):
                if ins.mnemonic == 'ret': break
                for o in OFFS:
                    if f'#0x{o:x}]' in ins.op_str:
                        hits.append(f'    0x{ins.address:x}: {ins.mnemonic} {ins.op_str}')
            if hits:
                print(f'global load at 0x{a + 4 * j:x}'); print('\n'.join(hits))
            break
print('total loads of global:', n)
