"""P2-UI-CONSTS: wrap raw AArch64 bytes in a minimal ELF64 so llvm-objdump can decode them.

  PYTHONPATH=... python elfwrap.py START COUNT OUT.elf [VADDR]

Independent of capstone: used to cross-check the disputed value instructions in
0x19ddb30 before any value was recorded in the report.
"""
import struct
import sys
from pathlib import Path

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'

start = int(sys.argv[1], 0)
count = int(sys.argv[2], 0)
out = Path(sys.argv[3])
vaddr = int(sys.argv[4], 0) if len(sys.argv) > 4 else start

code = IMAGE.read_bytes()[start:start + count]
EHDR = 64
PHDR = 56

eh = bytearray(EHDR)
eh[0:4] = b'\x7fELF'
eh[4] = 2          # ELFCLASS64
eh[5] = 1          # ELFDATA2LSB
eh[6] = 1          # EV_CURRENT
eh[7] = 0          # ELFOSABI_NONE
struct.pack_into('<HHI', eh, 16, 2, 183, 1)        # ET_EXEC, EM_AARCH64, EV_CURRENT
struct.pack_into('<QQQ', eh, 24, vaddr + count, EHDR, 0)  # e_entry, e_phoff, e_shoff
struct.pack_into('<IHHHHHH', eh, 48, 0, EHDR, PHDR, 1, 64, 0, 0)

ph = bytearray(PHDR)
struct.pack_into('<II', ph, 0, 1, 5)              # PT_LOAD, PF_R|PF_X
# p_offset must be the real file offset of the code (after both headers). With p_offset=0
# the loader maps the ELF header to vaddr, so every decoded address is shifted by
# EHDR+PHDR and the listing silently disagrees with the image.
struct.pack_into('<QQQQQQ', ph, 8, EHDR + PHDR, vaddr, vaddr,
                 len(code), len(code), 0x1000)

out.write_bytes(bytes(eh) + bytes(ph) + code)
print('wrote %s: 0x%x bytes of code, vaddr 0x%x' % (out, len(code), vaddr))
