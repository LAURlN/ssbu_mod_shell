"""P1-ID-REVIEW scratch disassembler. Reads gamedata/ssbu-13.0.4/main.bin only
(flat decompressed NSO, VA == file offset). Resolves adrp+add/ldr targets and bl targets.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python d.py win 0x19d41f0 80
  ... d.py fstart 0x19d41f0        # backward scan for prologue
  ... d.py xref 0x42e5a45          # adrp+add / adrp+ldr completions to an address
  ... d.py calls 0x17c8210         # bl/b callers of an address
  ... d.py ptr 0x19d41f0           # 8-byte pointers to an address in data
"""
import struct, sys, mmap
from pathlib import Path
import capstone
IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
TEXT = (0x100, 0x39C8000)
data = IMAGE.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
md.detail = False

def sx(v, b):
    return v - (1 << b) if v & (1 << (b - 1)) else v

def cstr(a, limit=96):
    if not (0x39C8000 <= a < len(data)):
        return ''
    e = data.find(b'\0', a, a + limit)
    if e < 0: return ''
    r = data[a:e]
    if len(r) < 3 or any(c < 0x20 or c > 0x7e for c in r): return ''
    return r.decode()

def win(addr, n):
    pages = {}
    for k in range(n):
        a = addr + 4 * k
        w = struct.unpack_from('<I', data, a)[0]
        ins = next(md.disasm(data[a:a + 4], a), None)
        txt = f'{ins.mnemonic:7s} {ins.op_str}' if ins else '.word'
        note = ''
        if (w & 0x9F000000) == 0x90000000:
            rd = w & 31
            pages[rd] = (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12)
        elif (w & 0xFF800000) == 0x91000000:
            rd, rn = w & 31, (w >> 5) & 31
            if rn in pages:
                t = pages[rn] + ((w >> 10) & 0xFFF)
                s = cstr(t)
                note = f'  ; = 0x{t:x}' + (f' "{s}"' if s else '')
                pages[rd] = t if rd != rn else pages.pop(rn) and t
                if rd == rn: pages.pop(rd, None)
        elif (w & 0xFFC00000) == 0xF9400000:
            rd, rn = w & 31, (w >> 5) & 31
            if rn in pages:
                t = pages[rn] + (((w >> 10) & 0xFFF) << 3)
                v = struct.unpack_from('<Q', data, t)[0] if t + 8 <= len(data) else 0
                note = f'  ; [0x{t:x}] (file qword 0x{v:x})'
            pages.pop(rd, None)
        else:
            rd = w & 31
            if rd in pages and ins and ins.mnemonic not in ('cmp', 'str', 'strb', 'strh', 'stp', 'cbz', 'cbnz', 'tbz', 'tbnz', 'b', 'bl', 'ldrb', 'ldrh'):
                pass
        print(f'0x{a:08x}: {txt}{note}')

def fstart(addr):
    a = addr & ~3
    for _ in range(4000):
        w = struct.unpack_from('<I', data, a)[0]
        # sub sp, sp, #imm   or stp x29,x30,[sp,#-imm]! or stp xN,xM,[sp,#-imm]!
        if (w & 0xFF8003FF) == 0xD10003FF or (w & 0xFFC003E0) == 0xA98003E0:
            pw = struct.unpack_from('<I', data, a - 4)[0]
            if pw in (0xD65F03C0,) or (pw & 0xFC000000) == 0x14000000 or pw == 0 or (pw & 0xFFFFFC1F) == 0xD61F0000 or pw==0xD4200020 or (pw&0xFC000000)==0x94000000:
                print(f'candidate start 0x{a:x} (prev word 0x{pw:08x})'); return
        a -= 4
    print('none')

def xref(target):
    page = target & ~0xFFF; lo = target & 0xFFF
    for a in range(TEXT[0], TEXT[1], 4):
        w = struct.unpack_from('<I', data, a)[0]
        if (w & 0x9F000000) != 0x90000000: continue
        p = (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12)
        if p != page: continue
        rd = w & 31
        for j in range(1, 8):
            w2 = struct.unpack_from('<I', data, a + 4 * j)[0]
            if (w2 & 0xFF800000) == 0x91000000 and ((w2 >> 5) & 31) == rd and ((w2 >> 10) & 0xFFF) == lo:
                print(f'add  completion 0x{a + 4 * j:x} (adrp 0x{a:x})')
            if (w2 & 0xFFC00000) == 0xF9400000 and ((w2 >> 5) & 31) == rd and (((w2 >> 10) & 0xFFF) << 3) == lo:
                print(f'ldr  completion 0x{a + 4 * j:x} (adrp 0x{a:x})')
            if (w2 & 0xFFC00000) == 0xF9000000 and ((w2 >> 5) & 31) == rd and (((w2 >> 10) & 0xFFF) << 3) == lo:
                print(f'str  completion 0x{a + 4 * j:x} (adrp 0x{a:x})')

def calls(target):
    for a in range(TEXT[0], TEXT[1], 4):
        w = struct.unpack_from('<I', data, a)[0]
        if (w & 0x7C000000) == 0x14000000:
            t = a + (sx(w & 0x3FFFFFF, 26) << 2)
            if t == target:
                print(f'{"bl" if w >> 31 else "b "} at 0x{a:x}')

def ptr(target):
    pat = struct.pack('<Q', target); i = 0
    while True:
        i = data.find(pat, i)
        if i < 0: break
        if i % 8 == 0: print(f'qword at 0x{i:x}')
        i += 1

c = sys.argv[1]
if c == 'win': win(int(sys.argv[2], 0), int(sys.argv[3]) if len(sys.argv) > 3 else 64)
elif c == 'fstart': fstart(int(sys.argv[2], 0))
elif c == 'xref': xref(int(sys.argv[2], 0))
elif c == 'calls': calls(int(sys.argv[2], 0))
elif c == 'ptr': ptr(int(sys.argv[2], 0))
