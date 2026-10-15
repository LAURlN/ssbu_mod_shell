"""Relocation addend lookup. rel.py <addr> <nslots>: prints R_AARCH64_RELATIVE addends for 8-byte slots.
rel.py find <target>: slots whose addend == target."""
import struct, sys
from pathlib import Path
IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
LO, HI = 0x39c8070, 0x40c9fc8
def table():
    m = {}
    for o in range(LO, HI, 24):
        off, info, add = struct.unpack_from('<QQq', data, o)
        if info & 0xffffffff == 0x403:
            m[off] = add
    return m
T = table()
if sys.argv[1] == 'find':
    t = int(sys.argv[2], 0)
    for k, v in sorted(T.items()):
        if v == t: print(f'slot 0x{k:x} -> 0x{v:x}')
else:
    a = int(sys.argv[1], 0); n = int(sys.argv[2])
    for i in range(n):
        s = a + 8 * i
        v = T.get(s)
        print(f'0x{s:x} [+0x{8*i:x}]: ' + (f'0x{v:x}' if v is not None else f'(no reloc; file 0x{struct.unpack_from("<Q", data, s)[0]:x})'))
