"""Q7 hook facts, measured from main.bin.

(a) The first four instruction words at 0x180a030 and whether any is PC-relative.
(b) Register liveness over 0x180a098..0x180a0c8 (the value read, the state push
    and its guard), reported from capstone's per-instruction read/write sets using
    the ARM64 register enum rather than raw ids, so the names are the real ones.
"""
from pathlib import Path
import capstone
import capstone.arm64 as arm64
IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
md.detail = True

PCREL_CLASSES = [
    ('adrp', lambda w: (w & 0x9F000000) == 0x90000000),
    ('adr', lambda w: (w & 0x9F000000) == 0x10000000),
    ('ldr literal', lambda w: (w & 0x3B000000) == 0x18000000),
    ('bl', lambda w: (w & 0xFC000000) == 0x94000000),
    ('b', lambda w: (w & 0xFC000000) == 0x14000000),
    ('b.cond', lambda w: (w & 0xFF000010) == 0x54000000),
    ('cbz/cbnz', lambda w: (w & 0x7F000000) == 0x34000000),
    ('tbz/tbnz', lambda w: (w & 0x7F000000) == 0x37000000),
]


def decode(a):
    return next(md.disasm(data[a:a + 4], a), None), int.from_bytes(data[a:a + 4], 'little')


def regnums(ins):
    """Return (read, written) as sets of canonical register ids, via reg_name."""
    rd, wr = set(), set()
    try:
        r, w = ins.regs_access()
    except capstone.CsError:
        return rd, wr
    for src, dst in ((r, rd), (w, wr)):
        for rid in src:
            n = ins.reg_name(rid)
            if n and n[0] in 'xw' and n[1:].isdigit():
                dst.add(int(n[1:]))
    return rd, wr


print('--- (a) first four instruction words at 0x180a030 ---')
for k in range(4):
    a = 0x180a030 + 4 * k
    i, w = decode(a)
    hits = [nm for nm, f in PCREL_CLASSES if f(w)]
    print('  0x%08x  0x%08x  %-7s %-28s  PC-relative: %s'
          % (a, w, i.mnemonic, i.op_str, ', '.join(hits) if hits else 'NO'))

print()
print('--- (b) registers read/written over 0x180a098..0x180a0c8 ---')
LO, HI = 0x180a098, 0x180a0c8
touch = {}
a = LO
while a <= HI:
    i, w = decode(a)
    a += 4
    if i is None:
        continue
    rd, wr = regnums(i)
    for r in rd | wr:
        touch.setdefault(r, set()).update('rw' if r in rd and r in wr else ('r' if r in rd else 'w'))
    print('  0x%08x %-26s r=%s w=%s' % (a - 4, '%s %s' % (i.mnemonic, i.op_str),
          ','.join('x%d' % r for r in sorted(rd)), ','.join('x%d' % r for r in sorted(wr))))

print()
print('  x19 is the scene object (`mov x19, x0` at 0x180a04c) and stays live through the range.')
print('  registers touched in the whole range:',
      ', '.join('x%d' % r for r in sorted(touch)))
print()
print('  AAPCS64: x19..x28, x29(fp), x30(lr) are callee-saved -> NOT free.')
print('  free scratch (caller-saved, untouched in the range):',
      ', '.join('x%d/w%d' % (r, r) for r in range(0, 19) if r not in touch))
