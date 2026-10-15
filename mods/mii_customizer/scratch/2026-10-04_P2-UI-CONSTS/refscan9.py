"""P2-UI-CONSTS step 3: adrp(+add/ldr/str) reference sites for the nine name strings.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python refscan9.py

One pass over TEXT; for each of the nine string addresses records every adrp page match
and any add/ldr/str completion within 7 instructions forming a full reference.

Adapted from P2-SKILL-NATIVE refscan.py. FIX vs that script: the original kept one
target per page in a dict, which loses every target on a shared page (SPECIAL_SKILL_NUM
0x0424de53 and SKILL_COMMAND_SIDE 0x0424de65 share page 0x0424d000). Here the page maps
to a LIST of targets and every completion is tested against every target on that page.
"""
import struct
from pathlib import Path

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
TEXT = (0x100, 0x39C8000)

TARGETS = {
    0x0424DE53: 'SPECIAL_SKILL_NUM',
    0x04338B2F: 'SKILL_COMMAND_NUM',
    0x04348C67: 'SKILL_COMMAND_NORMAL',
    0x0424DE65: 'SKILL_COMMAND_SIDE',
    0x043BD0B4: 'SKILL_COMMAND_UPPER',
    0x0432898F: 'SKILL_COMMAND_LOWER',
    0x04306E9B: 'INPUT_OK',
    0x04431954: 'IS_SKILL_EDITABLE',
    0x044119AF: 'IS_READ_ONLY',
}

pages = {}
for t in TARGETS:
    pages.setdefault(t & ~0xFFF, []).append(t)


def sx(v, b):
    return v - (1 << b) if v & (1 << (b - 1)) else v


hits = {t: [] for t in TARGETS}
adrp_only = {t: [] for t in TARGETS}
for a in range(TEXT[0], TEXT[1], 4):
    w = struct.unpack_from('<I', data, a)[0]
    if (w & 0x9F000000) != 0x90000000:
        continue
    p = (a & ~0xFFF) + (sx((((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3), 21) << 12)
    if p not in pages:
        continue
    rd = w & 31
    found = set()
    for j in range(1, 8):
        if a + 4 * j >= len(data):
            break
        w2 = struct.unpack_from('<I', data, a + 4 * j)[0]
        if ((w2 >> 5) & 31) != rd:
            continue
        for target in pages[p]:
            lo = target & 0xFFF
            if (w2 & 0xFF800000) == 0x91000000 and ((w2 >> 10) & 0xFFF) == lo:
                hits[target].append(('add', a, a + 4 * j))
                found.add(target)
            if (w2 & 0xFFC00000) == 0xF9400000 and (((w2 >> 10) & 0xFFF) << 3) == lo:
                hits[target].append(('ldr', a, a + 4 * j))
                found.add(target)
            if (w2 & 0xFFC00000) == 0xF9000000 and (((w2 >> 10) & 0xFFF) << 3) == lo:
                hits[target].append(('str', a, a + 4 * j))
                found.add(target)
    for target in pages[p]:
        if target not in found:
            adrp_only[target].append(a)

print('page collisions among the nine targets:')
bypage = {}
for t in TARGETS:
    bypage.setdefault(t & ~0xFFF, []).append((t, TARGETS[t]))
for pg, lst in sorted(bypage.items()):
    if len(lst) > 1:
        print('  page 0x%08x -> %s' % (pg, ', '.join('0x%x %s' % x for x in lst)))
print()

for t in sorted(TARGETS, key=lambda x: TARGETS[x]):
    name = TARGETS[t]
    print('=== %s  string 0x%08x ===' % (name, t))
    print('  adrp+add/ldr/str completions: %d' % len(hits[t]))
    for kind, ap, ac in sorted(hits[t], key=lambda h: h[2]):
        w2 = struct.unpack_from('<I', data, ac)[0]
        print('   %s completion 0x%08x (adrp 0x%08x, dest x%d)' % (kind, ac, ap, w2 & 31))
    if not hits[t]:
        print('   (no adrp+add/ldr/str reference found in TEXT)')
    print('  bare adrp to same page (no completion in +7): %d' % len(adrp_only[t]))
    print()
