"""P2-SKILL-NATIVE step 5: relocated pointer values at a delegate vtable.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python relocs.py ADDR [COUNT]

main.bin is a flat MOD0 image: no ELF header and no program headers, so there is no
walkable relocation table header. The R_AARCH64_RELATIVE records are present as a bare
24-byte array. The record layout, confirmed against the vtable that P1-ID-REVIEW already
decoded (0x50a6d28 -> {0x19c2210, 0x19dc640, 0x19dc650}), is

    +0x00  u64  r_offset   (the .data slot address)
    +0x08  u32  r_info     (0x403 = R_AARCH64_RELATIVE)
    +0x0c  u32  zero
    +0x10  u64  r_addend   (the runtime value of the slot)

This script scans the whole image for records whose r_offset equals a requested address
and reports the addend. A slot with no matching record is reported as such rather than
falling back to the file qword (which is 0 in .data).

  ... relocs.py --bounds            # print the extent of the record array
"""
import struct
import sys
from pathlib import Path

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
REC = 24
R_AARCH64_RELATIVE = 0x403


def scan(target):
    """Yield (file_offset, addend) for every RELA record with r_offset == target."""
    pat = struct.pack('<Q', target)
    i = 0
    while True:
        i = data.find(pat, i)
        if i < 0:
            return
        if (i + REC) <= len(data):
            info = struct.unpack_from('<I', data, i + 8)[0]
            pad = struct.unpack_from('<I', data, i + 0xC)[0]
            addend = struct.unpack_from('<Q', data, i + 0x10)[0]
            if info == R_AARCH64_RELATIVE and pad == 0 and addend != 0:
                yield i, addend
        i += 1


if '--bounds' in sys.argv:
    # walk a contiguous run of valid RELA records around the known post_fighter vtable
    seed = scan(0x50a6d28)
    lo = next(seed)[0]
    back = lo
    while back - REC >= 0:
        w = struct.unpack_from('<II', data, back - REC + 8)
        if w != (R_AARCH64_RELATIVE, 0):
            break
        back -= REC
    fwd = lo
    while fwd + REC <= len(data):
        w = struct.unpack_from('<II', data, fwd + 8)
        if w != (R_AARCH64_RELATIVE, 0):
            break
        fwd += REC
    print('contiguous R_AARCH64_RELATIVE record array: file 0x%x .. 0x%x  (%d records, %d bytes)'
          % (back, fwd + 23, (fwd + REC - back) // REC, fwd + REC - back))
    sys.exit(0)

base = int(sys.argv[1], 0)
n = int(sys.argv[2]) if len(sys.argv) > 2 else 3
print('=== vtable %s : relocated slots ===' % hex(base))
for i in range(n):
    a = base + 8 * i
    fileq = struct.unpack_from('<Q', data, a)[0]
    hits = list(scan(a))
    if hits:
        for fo, addend in hits:
            print('  +0x%02x  addr 0x%08x  RELATIVE addend 0x%08x   (reloc rec file 0x%x; file qword 0x%x)'
                  % (8 * i, a, addend, fo, fileq))
    else:
        print('  +0x%02x  addr 0x%08x  NO RELATIVE RELOCATION FOR THIS SLOT; file qword 0x%x' % (8 * i, a, fileq))
