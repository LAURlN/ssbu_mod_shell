"""P2-UI-CONSTS step 1: locate every NUL-terminated occurrence of the nine target names.

  PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python strfind9.py

Adapted from P2-SKILL-NATIVE strfind.py (unmodified original kept alongside).
"""
from pathlib import Path

IMAGE = Path(__file__).resolve().parents[4] / 'gamedata/ssbu-13.0.4/main.bin'
data = IMAGE.read_bytes()
TEXT = (0x100, 0x39C8000)

NAMES = ['SPECIAL_SKILL_NUM', 'SKILL_COMMAND_NUM', 'SKILL_COMMAND_NORMAL',
         'SKILL_COMMAND_SIDE', 'SKILL_COMMAND_UPPER', 'SKILL_COMMAND_LOWER',
         'INPUT_OK', 'IS_SKILL_EDITABLE', 'IS_READ_ONLY']


def region(a):
    if TEXT[0] <= a < TEXT[1]:
        return 'TEXT(0x%x-0x%x)' % TEXT
    if a < TEXT[0]:
        return 'before-TEXT'
    return 'after-TEXT(rodata-or-data)'


def ctx(a, n=48):
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

# containment: shorter names inside longer ones
PAIRS = [('SKILL_COMMAND', 'SKILL_COMMAND_NUM'),
         ('SKILL_COMMAND', 'SKILL_COMMAND_NORMAL'),
         ('SKILL_COMMAND', 'SKILL_COMMAND_SIDE'),
         ('SKILL_COMMAND', 'SKILL_COMMAND_UPPER'),
         ('SKILL_COMMAND', 'SKILL_COMMAND_LOWER'),
         ('IS_READ_ONLY', 'IS_SKILL_EDITABLE'),
         ('SPECIAL_SKILL_NUM', 'IS_SKILL_EDITABLE')]
for short, long_ in PAIRS:
    lb = long_.encode()
    hits = []
    i = 0
    while True:
        i = data.find(lb, i)
        if i < 0:
            break
        hits.append(i)
        i += 1
    print('=== containment %s inside %s: %d occurrences %s' % (
        short, long_, len(hits), ['0x%x' % x for x in hits]))
