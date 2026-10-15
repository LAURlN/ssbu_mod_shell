"""P2-SKILL-NATIVE step 1: locate every NUL-terminated occurrence of the six bridge names.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python strfind.py

Prints every offset at which name+NUL appears, plus the surrounding context so a
prefix match (replace_skill inside replace_skill_subwindow) is distinguishable.
Bare occurrences without the terminator are printed separately.
"""
import struct
from pathlib import Path

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
TEXT = (0x100, 0x39C8000)

NAMES = ['get_skill_id', 'set_skill_id', 'replace_skill',
         'replace_skill_subwindow', 'get_skill_name_label', 'get_skill_help_label']


def region(a):
    if TEXT[0] <= a < TEXT[1]:
        return 'TEXT(0x%x-0x%x)' % TEXT
    if a < TEXT[0]:
        return 'before-TEXT'
    return 'after-TEXT(rodata-or-data)'


def ctx(a, n=40):
    e = data.find(b'\0', a)
    s = data[a:e].decode('latin1')
    before = data[max(0, a - 8):a].decode('latin1')
    return repr(before + '[' + s + ']')


for n in NAMES:
    b = n.encode()
    term = b + b'\0'
    hits = []
    i = 0
    while True:
        i = data.find(term, i)
        if i < 0:
            break
        hits.append(i)
        i += 1
    print('=== %s ===' % n)
    print('  NUL-terminated count: %d' % len(hits))
    for h in hits:
        print('   0x%08x  %s  %s' % (h, region(h), ctx(h)))
    bare = []
    i = 0
    while True:
        i = data.find(b, i)
        if i < 0:
            break
        if data[i + len(b):i + len(b) + 1] != b'\0':
            bare.append(i)
        i += 1
    print('  bare (no terminator right after) count: %d %s' % (len(bare), ['0x%x' % x for x in bare]))
    print()

# substring summary: which occurrences of the shorter names are also inside the longer
for short, long_ in (('replace_skill', 'replace_skill_subwindow'),):
    lb = long_.encode()
    print('=== containment %s inside %s ===' % (short, long_))
    i = 0
    while True:
        i = data.find(lb, i)
        if i < 0:
            break
        print('   %s at 0x%08x %s' % (long_, i, region(i)))
        i += 1
