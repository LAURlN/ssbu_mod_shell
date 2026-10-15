"""Report what a ported G&W script depends on, so the eflame port can be planned
from evidence instead of discovered one crash at a time.

Why
---
G&W's ACMD dumps cannot be pasted into eflame. Three classes of identifier in
them are not portable:

* `*FIGHTER_GAMEWATCH_*` constants. In `lua_const.rs` these are raw values, and
  the work-id ones are absolute WorkModule indices (`..._INT_NORMAL_WEAPON_KIND:
  0x100000BD`). eflame's own ranges are float 0x4B-0x4C and int
  0x100000BF-0x100000C3, so a G&W index written into a Pyra agent lands on her
  storage.
* `gamewatch::ST_*` status kinds. Status ids are per fighter, and the project's
  rules forbid equating them across fighters.
* `ArticleModule` calls. G&W's articles run 0-8; eflame's stop at
  `ARTICLE_TERM 0x5`.

Bones are *not* in that list: build.py installs G&W's skeleton and grafts Pyra's
bones on, so every G&W bone name resolves.

Run:
    toolchains/py312/python.exe src/pgwr/tools/analyse_port.py
    toolchains/py312/python.exe src/pgwr/tools/analyse_port.py --moves Attack11 AttackAirF
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GW = ROOT / 'dumps' / 'scripts' / 'SSBU-Dumped-Scripts-main' / 'smashline' / 'lua2cpp_gamewatch' / 'gamewatch'
FL = ROOT / 'dumps' / 'scripts' / 'SSBU-Dumped-Scripts-main' / 'smashline' / 'lua2cpp_eflame' / 'eflame'
OUT = Path(__file__).resolve().parents[1] / 'port-dependencies.json'

# eflame's WorkModule layout, from skyline-smash 315e4e8 src/lua_const.rs.
EFLAME_FLOAT = range(0x4B, 0x4D)
EFLAME_INT = range(0x100000BF, 0x100000C4)
EFLAME_ARTICLES = range(0x0, 0x5)

# Pyra's non-special move statuses, i.e. everything phase 2 must cover.
# Specials, the down-B swap and the Final are deliberately excluded.
PHASE2_MOVES = [
    'Attack11', 'Attack12', 'Attack13',
    'AttackDash', 'AttackHi3', 'AttackHi4', 'AttackHi4Charge',
    'AttackLw3', 'AttackLw4', 'AttackLw4Charge',
    'AttackS3', 'AttackS3Hi', 'AttackS3Lw', 'AttackS4', 'AttackS4Charge',
    'AttackAirN', 'AttackAirB', 'AttackAirF', 'AttackAirHi', 'AttackAirLw',
    'Catch', 'CatchAttack', 'CatchDash', 'CatchTurn', 'CatchWait',
    'CaptureDamageLw',
    'ThrowF', 'ThrowB', 'ThrowHi', 'ThrowLw',
    'DownAttackU', 'DownAttackD',
]

RE_CONST = re.compile(r'\*(FIGHTER_GAMEWATCH_[A-Z0-9_]+)')
RE_STATUS = re.compile(r'gamewatch::([A-Z0-9_]+)')
RE_EFFECT = re.compile(r'\b(?:macros::)?(?:FOOT_EFFECT|EFFECT|EFFECT_FOLLOW|EFFECT_FOLLOW_WORK|'
                       r'SPAWN_EFFECT|EFFECT_FLIP|ADD_DUST)\s*\([^;]*?Hash40::new\("([^"]+)"\)', re.S)
RE_SOUND = re.compile(r'PLAY_SE\w*\([^;]*?Hash40::new\("([^"]+)"\)', re.S)
RE_ARTICLE = re.compile(r'GENERATE_ARTICLE_([A-Z0-9_]+)')
RE_BONE = re.compile(r'ATTACK\w*\(\s*agent\s*,\s*\d+\s*,\s*\d+\s*,\s*Hash40::new\("([^"]+)"\)')
RE_MOTION = re.compile(r'change_motion\([^;]*?Hash40::new\("([^"]+)"\)', re.S)
RE_SLOPE = re.compile(r'\bslope!\(')


def analyse(path: Path) -> dict:
    text = path.read_text(encoding='utf-8', errors='replace')
    work = sorted(set(RE_CONST.findall(text)))
    # Split the constants into raw work indices (port-unsafe) and named
    # flags/attack values, which are fighter-independent enums.
    work_idx = [c for c in work if '_WORK_ID_' in c]
    other_const = [c for c in work if '_WORK_ID_' not in c]
    return {
        'gamewatch_constants': other_const,
        'gamewatch_work_ids': work_idx,
        'gamewatch_statuses': sorted(set(RE_STATUS.findall(text))),
        'articles': sorted(set(RE_ARTICLE.findall(text))),
        'effects': sorted(set(RE_EFFECT.findall(text))),
        'sounds': sorted(set(RE_SOUND.findall(text))),
        'attack_bones': sorted(set(RE_BONE.findall(text))),
        'article_motions': sorted(set(RE_MOTION.findall(text))),
        'uses_slope': bool(RE_SLOPE.search(text)),
        'functions': sorted(set(re.findall(r'fn\s+(game|effect|sound|expression)_(\w+)', text))),
    }


def main() -> int:
    if not GW.is_dir():
        print(f'error: G&W dump not found at {GW}', file=sys.stderr)
        return 2
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    moves = args or PHASE2_MOVES

    report, missing = {}, []
    for move in moves:
        src = GW / f'{move}.txt'
        if not src.is_file():
            missing.append(move)
            continue
        report[move] = analyse(src)
        report[move]['eflame_has_this_status'] = (FL / f'{move}.txt').is_file()

    OUT.write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')

    # Roll up what actually needs translating.
    work_ids = sorted({c for m in report.values() for c in m['gamewatch_work_ids']})
    statuses = sorted({c for m in report.values() for c in m['gamewatch_statuses']})
    articles = sorted({c for m in report.values() for c in m['articles']})
    effects = sorted({c for m in report.values() for c in m['effects']})
    sounds = sorted({c for m in report.values() for c in m['sounds']})
    bones = sorted({c for m in report.values() for c in m['attack_bones']})
    motions = sorted({c for m in report.values() for c in m['article_motions']})

    print(f'analysed {len(report)} G&W scripts -> {OUT.relative_to(ROOT)}')
    if missing:
        print(f'  MISSING in G&W dump: {missing}')
    both = [m for m in report if report[m]['eflame_has_this_status']]
    only_gw = [m for m in report if not report[m]['eflame_has_this_status']]
    print(f'\nstatuses Pyra also has: {len(both)}')
    print(f'statuses only G&W has:  {only_gw}')
    print(f'\nG&W work ids used ({len(work_ids)}) - each needs an eflame translation:')
    for c in work_ids:
        print(f'  {c}')
    print(f'\nG&W status kinds used ({len(statuses)}):')
    for s in statuses:
        print(f'  {s}')
    print(f'\nG&W articles used ({len(articles)}):')
    for a in articles:
        print(f'  {a}')
    print(f'\narticle motions used: {motions}')
    print(f'\nATTACK bones used ({len(bones)}): {bones}')
    print(f'\neffect names ({len(effects)}): {effects}')
    print(f'\nsound names ({len(sounds)}): {sounds}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
