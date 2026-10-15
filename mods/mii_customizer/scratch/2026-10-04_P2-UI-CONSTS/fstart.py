"""P2-SKILL-NATIVE: backward scan for a function prologue candidate.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python fstart.py ADDR

Accepts a stack-pointer prologue preceded by a return/branch/nop, like P1-ID-REVIEW d.py,
but also reports stp-preindex prologues of any register pair so we can see candidates.
"""
import struct
import sys
from pathlib import Path

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()

a = int(sys.argv[1], 0) & ~3
for _ in range(6000):
    w = struct.unpack_from('<I', data, a)[0]
    if (w & 0xFF8003FF) == 0xD10003FF:            # sub sp, sp, #imm
        print('0x%x: sub sp prologue  imm=%#x' % (a, (w >> 10) & 0xFFF))
    elif (w & 0xFFC003E0) == 0xA98003E0:           # stp xN,xM,[sp,#-imm]!
        pw = struct.unpack_from('<I', data, a - 4)[0]
        mark = '  <== candidate start' if (pw in (0xD65F03C0, 0) or (pw & 0xFC000000) == 0x94000000
                                           or (pw & 0xFFFFFC1F) == 0xD61F0000) else ''
        print('0x%x: stp preindex prologue  prev=0x%08x%s' % (a, pw, mark))
    a -= 4
    if a < 0x100:
        break
