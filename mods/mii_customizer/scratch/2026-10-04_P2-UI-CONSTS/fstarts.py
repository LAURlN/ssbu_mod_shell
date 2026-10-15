"""P2-UI-CONSTS: list function-start candidates in a range (prologue + padding check).

  PYTHONPATH=... python fstarts.py START END

A candidate is a `sub sp,sp,#imm` or `stp ..., [sp,#-imm]!` word whose previous word is
udf #0, a ret, a branch, or zero. Adapted from P2-SKILL-NATIVE fstart.py, which only
searched backwards from one address and could not see a prologue that fell outside its
4000-word window.
"""
import struct
import sys
from pathlib import Path

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()

start = int(sys.argv[1], 0)
end = int(sys.argv[2], 0)

a = start
while a < end:
    w = struct.unpack_from('<I', data, a)[0]
    is_sub = (w & 0xFF8003FF) == 0xD10003FF
    is_push = (w & 0xFFC003E0) == 0xA98003E0
    if is_sub or is_push:
        pw = struct.unpack_from('<I', data, a - 4)[0]
        if (pw in (0xD65F03C0, 0x00000000)
                or (pw & 0xFC000000) == 0x14000000
                or (pw & 0xFFFFFC1F) == 0xD61F0000
                or pw == 0xD4200020
                or (pw & 0xFC000000) == 0x94000000):
            print('candidate start 0x%08x (prev word 0x%08x)' % (a, pw))
    a += 4
