"""Look for the donor Monkey Flip script inside the reference JSON blobs.

Read-only. The two blobs are 6-9 MB, and an unbounded grep on this machine has
already walked the filesystem once and produced ~96 MB of output, so every
excerpt here is bounded and capped.

Purpose: mod_files/mythra_gamewatch_swap/src/monkey_flip.rs cites
"references/diddy_specials/donor_acmd/SpecialAirSJump.txt" as the pinned donor
for its CATCH call. That directory does not exist. This asks whether the donor
script is instead present inside one of the symbol/script dumps, because if it
is, the argument layout can be read instead of guessed.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / 'references' / 'diddy_specials' / 'source_audit'

TARGETS = ['SSBU-Dumped-Status-Scripts.json', 'ssbu.json']
# Names the donor script could be indexed under, plus the command itself.
PATTERNS = ['specialairsjump', 'specialsjump', 'game_specialsjump', 'CATCH', 'sv_animcmd']


def excerpt(text, at, before=140, after=260):
    start = max(0, at - before)
    end = min(len(text), at + after)
    return text[start:end].replace('\n', '\\n').replace('\r', '')


def probe(path):
    if not path.is_file():
        print(f'MISSING {path}')
        return
    raw = path.read_text(encoding='utf-8', errors='replace')
    print(f'=== {path.name}: {len(raw)} chars ===')
    print('head: ' + raw[:220].replace('\n', '\\n').replace('\r', ''))
    for pattern in PATTERNS:
        hits = [m.start() for m in re.finditer(re.escape(pattern), raw, re.IGNORECASE)]
        print(f'--- {pattern}: {len(hits)} occurrence(s) ---')
        for at in hits[:3]:
            print('   ...' + excerpt(raw, at) + '...')
    print()


for name in TARGETS:
    probe(REF / name)
