"""Derive the minimal power-of-two alignment each member start requires, and
correlate it with member size, in both archives.
"""
import struct
import sys


def load(path):
    d = open(path, 'rb').read()
    c = struct.unpack_from('<H', d, 0x1A)[0]
    nb = 0x20 + c * 16 + 8
    ents = []
    for i in range(c):
        f0, f1, st, en = struct.unpack_from('<4I', d, 0x20 + i * 16)
        no = (f1 & 0xFFFFFF) * 4
        e = d.find(b'\x00', nb + no)
        ents.append((d[nb + no:e].decode(), st, en))
    return ents


def main(path):
    ents = load(path)
    print(f"== {path.split('/')[-3]}")
    print("   prev_end -> start   min_pow2_align  size        name")
    prev_end = 0
    rows = []
    for name, st, en in ents:
        size = en - st
        align = None
        for a in (1, 2, 4, 8, 0x10, 0x20, 0x40, 0x80, 0x100, 0x200, 0x400,
                  0x800, 0x1000, 0x2000, 0x4000, 0x8000, 0x10000):
            if (prev_end + a - 1) & ~(a - 1) == st:
                align = a
        rows.append((prev_end, st, align, size, name))
        prev_end = en
    for r in rows:
        if r[2] and r[2] > 0x10:
            print(f"   {r[0]:#08x} -> {r[1]:#08x}   {r[2]:#8x}  {r[3]:#9x}  {r[4]}")
    small = [r for r in rows if r[2] and r[2] <= 0x10]
    print(f"   members needing <= 0x10: {len(small)}; max size among them "
          f"{max(r[3] for r in small):#x}")


if __name__ == '__main__':
    for p in sys.argv[1:]:
        main(p)