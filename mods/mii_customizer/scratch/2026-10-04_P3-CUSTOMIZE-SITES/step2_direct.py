"""P3-CUSTOMIZE-SITES step 2: direct users of the wrapper at 0x208de60.

Three independent searches, all re-derivable from the image:
  (a) `bl`/`b` in TEXT with a branch target of exactly 0x208de60 (opcode-decoded,
      no capstone; a b/BL has bits 31:26 == 0b100101, i.e. (w & 0xFC000000) == 0x94000000);
  (b) any 8-byte little-endian occurrence of the value 0x208de60 in the whole image;
  (c) any R_AARCH64_RELATIVE record whose r_addend equals 0x208de60.

The relocation record layout and the flat MOD0 image shape are those established in
P2-SKILL-NATIVE's relocs.py (24-byte RELA records, bare array, no ELF header):
    +0x00 u64 r_offset, +0x08 u32 r_info, +0x0c u32 zero, +0x10 u64 r_addend.

Writes nothing to the current directory; prints to stdout.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python step2_direct.py
"""
import struct
from pathlib import Path

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
TEXT = (0x100, 0x39C8000)
TARGET = 0x208DE60

data = IMAGE.read_bytes()
sx = lambda v, b: v - (1 << b) if v & (1 << (b - 1)) else v


def branches():
    out = []
    for a in range(TEXT[0], TEXT[1], 4):
        w = struct.unpack_from('<I', data, a)[0]
        if (w & 0xFC000000) != 0x94000000:
            continue
        t = a + (sx(w & 0x3FFFFFF, 26) << 2)
        if t == TARGET:
            out.append((a, 'bl' if w >> 31 else 'b'))
    return out


def pointers():
    out = []
    pat = struct.pack('<Q', TARGET)
    i = 0
    while True:
        i = data.find(pat, i)
        if i < 0:
            return out
        out.append(i)
        i += 1


def reloc_addends():
    """Walk the bare RELA array reported by relocs.py --bounds (file 0x39c8070..0x40c9fc7)."""
    out = []
    start, end = 0x39C8070, 0x40C9FC7
    a = start
    while a + 24 <= end + 1:
        off, info, pad = struct.unpack_from('<QII', data, a)
        addend, = struct.unpack_from('<Q', data, a + 0x10)
        if info == 0x403 and pad == 0 and addend != 0 and addend == TARGET:
            out.append((a, off, addend))
        a += 24
    return out


br = branches()
pt = pointers()
rl = reloc_addends()

print('=== (a) bl/b in TEXT 0x%x..0x%x targeting 0x%x: %d ==='
      % (TEXT[0], TEXT[1], TARGET, len(br)))
for a, k in br:
    print('  %s at 0x%08x' % (k, a))
print('=== (b) 8-byte pointers to 0x%x anywhere in the image: %d ===' % (TARGET, len(pt)))
for o in pt:
    print('  at file 0x%08x  (8-byte aligned: %s, in TEXT: %s)'
          % (o, o % 8 == 0, TEXT[0] <= o < TEXT[1]))
print('=== (c) R_AARCH64_RELATIVE addends == 0x%x: %d ===' % (TARGET, len(rl)))
for rec, off, addend in rl:
    print('  reloc rec file 0x%08x -> r_offset 0x%08x addend 0x%08x' % (rec, off, addend))