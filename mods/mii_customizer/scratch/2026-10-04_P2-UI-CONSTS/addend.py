"""P2-UI-CONSTS: find every R_AARCH64_RELATIVE record whose addend equals a target.

  PYTHONPATH=... python addend.py ADDR [ADDR ...]

The flat image has no relocation header, so this walks the validated bare 24-byte record
array (see relocs.py) and reports r_offset for any record whose addend matches. This
catches a string reached through a .data pointer table instead of an adrp+add in TEXT.
"""
import struct
import sys
from pathlib import Path

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
REC = 24
LO = 0x39C8070
HI = 0x40C9FC8

targets = {int(a, 0) for a in sys.argv[1:]}
n = 0
off = LO
while off + REC <= HI:
    r_offset, info, pad, addend = struct.unpack_from('<QIIQ', data, off)
    if info == 0x403 and pad == 0 and addend != 0:
        n += 1
        if addend in targets:
            print('addend 0x%08x  at slot 0x%08x  (record file 0x%x)' % (addend, r_offset, off))
    off += REC
print('scanned %d R_AARCH64_RELATIVE records in 0x%x..0x%x' % (n, LO, HI))
