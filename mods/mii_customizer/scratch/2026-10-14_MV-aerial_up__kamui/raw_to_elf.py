"""Wrap a raw AArch64 code blob in a minimal ELF64 relocatable so llvm-objdump can disassemble it.

Scratch helper (2026-10-08, MV-aerial_up__kamui). Usage: python -I raw_to_elf.py <in.bin> <base_addr_hex> <out.o>
The .text section starts at virtual address 0 in the object; `base` only sets the sh_addr shown by objdump.
"""
import struct
import sys

src, base, out = sys.argv[1], int(sys.argv[2], 16), sys.argv[3]
code = open(src, 'rb').read()

shstr = b'\0.text\0.shstrtab\0'
name_text = shstr.index(b'.text')
name_shstr = shstr.index(b'.shstrtab')

ehdr_size = 64
text_off = ehdr_size
shstr_off = text_off + len(code)
shoff = (shstr_off + len(shstr) + 7) & ~7
pad = shoff - (shstr_off + len(shstr))

ehdr = struct.pack('<4sBBBBB7sHHIQQQIHHHHHH',
                   b'\x7fELF', 2, 1, 1, 0, 0, b'\0' * 7,
                   1, 183, 1, 0, 0, shoff, 0, ehdr_size, 0, 0, 64, 3, 2)

def shdr(name, typ, flags, addr, off, size, link, info, align, entsize):
    return struct.pack('<IIQQQQIIQQ', name, typ, flags, addr, off, size, link, info, align, entsize)

sh_null = b'\0' * 64
sh_text = shdr(name_text, 1, 0x6, base, text_off, len(code), 0, 0, 4, 0)
sh_str = shdr(name_shstr, 3, 0, 0, shstr_off, len(shstr), 0, 0, 1, 0)

blob = ehdr + code + shstr + b'\0' * pad + sh_null + sh_text + sh_str
open(out, 'wb').write(blob)
print('wrote', out, len(blob), 'bytes; code', len(code), 'bytes at base', hex(base))
