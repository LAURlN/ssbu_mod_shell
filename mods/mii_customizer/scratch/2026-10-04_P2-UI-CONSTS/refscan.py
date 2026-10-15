"""P2-SKILL-NATIVE step 2: adrp(+add/ldr/str) reference sites for each name string.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python refscan.py [extra_target ...]

One pass over TEXT; records for each target address every adrp page match and the
completions (add / ldr / str) within 7 instructions that form the full reference.
"""
import struct
from pathlib import Path

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
TEXT = (0x100, 0x39C8000)

TARGETS = {
    0x042905bf: 'get_skill_id',
    0x04348c5a: 'set_skill_id',
    0x0439bd6c: 'replace_skill',
    0x0437af9d: 'replace_skill_subwindow',
    0x0427f3d5: 'get_skill_name_label',
    0x0441127e: 'get_skill_help_label',
}
for a in sys.argv[1:] if (sys := __import__('sys')) else []:
    TARGETS[int(a, 0)] = 'extra_0x%x' % int(a, 0)

pages = {}
for t in TARGETS:
    pages[t & ~0xFFF] = t


def sx(v, b):
    return v - (1 << b) if v & (1 << (b - 1)) else v


def is_adrp(w):
    return (w & 0x9F000000) == 0x90000000


def is_add(w):
    return (w & 0xFF800000) == 0x91000000


def is_ldr(w):
    return (w & 0xFFC00000) == 0xF9400000


def is_str(w):
    return (w & 0xFFC00000) == 0xF9000000


hits = {t: [] for t in TARGETS}
for a in range(TEXT[0], TEXT[1], 4):
    w = struct.unpack_from('<I', data, a)[0]
    if not is_adrp(w):
        continue
    p = (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12)
    if p not in pages:
        continue
    rd = w & 31
    target = pages[p]
    lo = target & 0xFFF
    for j in range(1, 8):
        if a + 4 * j >= len(data):
            break
        w2 = struct.unpack_from('<I', data, a + 4 * j)[0]
        rn = (w2 >> 5) & 31
        if rn != rd:
            continue
        if is_add(w2) and ((w2 >> 10) & 0xFFF) == lo:
            hits[target].append(('add', a, a + 4 * j))
        if is_ldr(w2) and (((w2 >> 10) & 0xFFF) << 3) == lo:
            hits[target].append(('ldr', a, a + 4 * j))
        if is_str(w2) and (((w2 >> 10) & 0xFFF) << 3) == lo:
            hits[target].append(('str', a, a + 4 * j))

for t in sorted(TARGETS, key=lambda x: TARGETS[x]):
    name = TARGETS[t]
    hs = hits[t]
    print('=== %s  string 0x%08x ===' % (name, t))
    print('  adrp+add/ldr/str completions: %d' % len(hs))
    for kind, ap, ac in hs:
        w2 = struct.unpack_from('<I', data, ac)[0]
        rd2 = w2 & 31
        print('   %s completion 0x%08x (adrp 0x%08x, dest x%d)' % (kind, ac, ap, rd2))
    if not hs:
        print('   (no adrp+add/ldr/str reference found in TEXT)')
    print()
