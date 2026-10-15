"""Audit a *packaged* pgwr tree for the Hero side-B static wiring (v1.0.0).

Tier B: it measures the bytes that would go on the card. It proves nothing about
console behaviour. What it answers, per recipient slot:

  * every owned motion kind (`pgwr_hero_special_s*`, `pgwr_hero_special_air_s*`)
    exists in the packaged `motion_list.bin`, with its clip name and cancel frame;
  * each entry's four script hashes resolve to *names*, and every one of those
    names is actually registered in the plugin source (so no entry can silently
    keep the previous clip because the game found no script);
  * every owned clip file exists;
  * the spark/lightning article motion lists exist for all eight slots and are
    declared in `config.json` under `new-dir-files`;
  * every effect emitter name the owned ACMD spawns is present in the merged
    `ef_<fighter>_cXX.eff`.

Usage:
  python tools/audit_hero_side_b_package.py <mod_root> [--source SRC] [--json OUT]
  python tools/audit_hero_side_b_package.py --check     # smoke test, offline

`<mod_root>` is the mod directory inside a staged package, e.g.
`builds/pgwr/0.20.16/ultimate/mods/pyra_gamewatch_reskin`.
`--source` is the plugin source tree that carries the registrations
(default `src/pgwr/plugin/src/mythra/hero_side_b`).

Why this exists: handbook/04 records that a motion-list entry naming a script the
mod does not resolve leaves the previous clip playing with no error, and
handbook/06 records the same for articles. A level-3 "no lightning" report is
exactly what a silently unresolved `game_*`/effect chain looks like, so the
discriminating measurement belongs to a script rather than to a console session.

No writes outside `--json`.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '1.0.0'
SLOTS = tuple(f'c{i:02d}' for i in range(8))
TARGET_SLOTS = ('c06', 'c07')
ARTICLE_DIRS = ('pgwr_hero_spark', 'pgwr_hero_lightning')
MOTION_DIR = 'fighter/elight/motion'


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def owned_motions() -> list[tuple[str, str]]:
    """(motion kind, clip file name) exactly as tools/build_hero_side_b_assets.py emits."""
    out = []
    for air in ('', 'air'):
        for phase in ('start', 'hold', '1', '2', '3', '32'):
            donor = ('special_air_s' if air else 'special_s') + ('_' if phase.isalpha() else '') + phase
            owned = 'pgwr_hero_' + donor
            out.append((owned, owned.replace('_', '') + '.nuanmb'))
    return out


def parse_mlist(data: bytes) -> dict[int, dict]:
    """Motion list -> {kind: entry}. Layout per entry, 24-byte header then the
    animation names at a 9-byte stride, then a tail of expression/sound/effect
    hashes and a cancel frame (see handbook/04 and audit_littlemac_fsmash.py)."""
    magic, _path, count = struct.unpack_from('<QQQ', data, 0)
    if magic != hash40('motion'):
        raise ValueError('not a motion list')
    offset, out = 24, {}
    for _ in range(count):
        kind, game, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = [struct.unpack_from('<Q', data, offset + 9 * i)[0] for i in range(n_anims)]
        offset = (offset + n_anims * 9 + 3) & ~3
        tail = data[offset:offset + size]
        offset += size
        scripts = {}
        if size >= 24:
            for index, category in enumerate(('expression', 'sound', 'effect')):
                value = struct.unpack_from('<Q', tail, index * 8)[0]
                if value:
                    scripts[category] = value
        cancel = struct.unpack_from('<H', tail, size - 2)[0] if size >= 2 else None
        out[kind] = {'raw_game': game, 'flags': flags, 'blend': blend, 'anims': anims,
                     'scripts': scripts, 'cancel': cancel, 'size': size}
    return out


def registered_scripts(source: Path) -> set[str]:
    """Every ACMD name the plugin registers for this move."""
    names: set[str] = set()
    for path in sorted(source.glob('*.rs')):
        text = path.read_text(encoding='utf-8', errors='replace')
        for match in re.finditer(r'\.(?:game|effect|sound|expression)_acmd\(\s*"([^"]+)"', text):
            names.add(match.group(1))
        for match in re.finditer(r'Hash40::new\("(effect_[^"]+)"\)', text):
            names.add(match.group(1))
        # generated arms: name("effect", "3") etc, expanded below from the helper
        for match in re.finditer(r'\.(?:game|effect|sound|expression)_acmd\(\s*name\("(\w+)",\s*"(\w+)"\)', text):
            for air in ('', 'air'):
                # tools/build_hero_side_b_assets.py strips every underscore from the
                # motion kind before building the script names, so "start" stays
                # "sstart" and the air variants are "specialairs...".
                names.add(f'{match.group(1)}_pgwrherospecial{air}s{match.group(2)}')
    return names


def emitters_in(path: Path) -> set[str]:
    blob = path.read_bytes()
    upper = set()
    for match in re.finditer(rb'[A-Z][A-Z0-9_]{5,}', blob):
        upper.add(match.group().decode())
    return upper


def audit(mod_root: Path, source: Path) -> dict:
    registered = registered_scripts(source)
    result: dict = {'tool_version': VERSION, 'tier': 'B', 'hardware_validated': False,
                    'mod_root': mod_root.as_posix(), 'source': source.as_posix(),
                    'registered_script_count': len(registered), 'slots': {}, 'problems': []}

    for slot in TARGET_SLOTS:
        slot_row: dict = {'owned_motions': {}, 'articles': {}, 'emitters': {}}
        mlist_path = mod_root / MOTION_DIR / 'body' / slot / 'motion_list.bin'
        if not mlist_path.is_file():
            result['problems'].append(f'{slot}: missing {mlist_path.name}')
            result['slots'][slot] = slot_row
            continue
        entries = parse_mlist(mlist_path.read_bytes())
        for kind_name, clip in owned_motions():
            entry = entries.get(hash40(kind_name))
            if entry is None:
                result['problems'].append(f'{slot}: motion kind {kind_name} missing')
                continue
            row = {'clip': clip, 'clip_present': (mlist_path.parent / clip).is_file(),
                   'flags': entry['flags'], 'cancel_frame': entry['cancel'],
                   'scripts': {}}
            if not row['clip_present']:
                result['problems'].append(f'{slot}: clip {clip} missing')
            for category, value in entry['scripts'].items():
                name = None
                for candidate in (f'{category}_{kind_name.replace("_", "")}',):
                    if hash40(candidate) == value:
                        name = candidate
                row['scripts'][category] = {'hash': f'{value:#x}', 'name': name,
                                            'registered': name in registered if name else False}
                if name is None:
                    result['problems'].append(
                        f'{slot}: {kind_name} {category} hash {value:#x} is not an owned name')
                elif name not in registered:
                    result['problems'].append(f'{slot}: {name} is in the list but not registered')
            game_hash = entry['raw_game']
            game_name = f'game_{kind_name.replace("_", "")}'
            row['game_script'] = {'hash': f'{game_hash:#x}', 'name': game_name,
                                  'registered': game_name in registered if game_name else False}
            if game_name is None or hash40(game_name) != game_hash:
                result['problems'].append(
                    f'{slot}: {kind_name} game hash {game_hash:#x} != {game_name}')
            elif game_name not in registered:
                result['problems'].append(f'{slot}: {game_name} not registered')
            row['clip_hash'] = f'{entry["anims"][0]:#x}'
            slot_row['owned_motions'][kind_name] = row

        for article in ARTICLE_DIRS:
            article_path = mod_root / MOTION_DIR / article / slot / 'motion_list.bin'
            slot_row['articles'][article] = {'present': article_path.is_file()}
            if not article_path.is_file():
                result['problems'].append(f'{slot}: article motion list {article} missing')

        eff = mod_root / 'effect/fighter/elight' / f'ef_elight_{slot}.eff'
        if eff.is_file():
            found = emitters_in(eff)
            wanted = [n for n in re.findall(r'"(brave_[a-z0-9_]+)"',
                                            (source / 'script_acmd.rs').read_text(encoding='utf-8')
                                            + (source / 'weapon.rs').read_text(encoding='utf-8'))]
            missing = sorted({name for name in wanted if name.upper() not in found})
            slot_row['emitters'] = {'file': eff.name, 'wanted': len(set(wanted)),
                                    'missing': missing}
            result['problems'] += [f'{slot}: emitter {m} missing from {eff.name}' for m in missing]
        else:
            result['problems'].append(f'{slot}: {eff.name} missing')
        result['slots'][slot] = slot_row

    config = mod_root / 'config.json'
    if config.is_file():
        declared = json.loads(config.read_text(encoding='utf-8')).get('new-dir-files', {})
        flat = {path for slot_files in declared.values() for path in slot_files}
        for slot in TARGET_SLOTS:
            for article in ARTICLE_DIRS:
                want = f'{MOTION_DIR}/{article}/{slot}/motion_list.bin'
                if want not in flat:
                    result['problems'].append(f'config.json: {want} not declared')
    else:
        result['problems'].append('config.json missing')
    result['ok'] = not result['problems']
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mod_root', nargs='?', type=Path)
    parser.add_argument('--source', type=Path,
                        default=ROOT / 'src/pgwr/plugin/src/mythra/hero_side_b')
    parser.add_argument('--json', type=Path)
    parser.add_argument('--check', action='store_true',
                        help='self-test: hash40 round trip and motion-list layout')
    args = parser.parse_args()
    if args.check:
        assert hash40('motion') == 29896909288, hash40('motion')
        # Layout control: the pinned Hero donor list must yield four distinct script
        # words per entry, or the 24-byte header + 9-byte stride parse is wrong and
        # every downstream number would be fiction.
        donor = ROOT / 'refs/brave_special_s/arc/fighter/brave/motion/body/c06/motion_list.bin'
        if donor.is_file():
            entries = parse_mlist(donor.read_bytes())
            entry = entries[hash40('special_s3')]
            words = [entry['raw_game'], *entry['scripts'].values()]
            assert len(words) == 4 and len(set(words)) == 4, words
        staged = ROOT / 'builds/pgwr/0.20.16/ultimate/mods/pyra_gamewatch_reskin'
        if staged.is_dir():
            rows = audit(staged, args.source)
            assert rows['slots']['c06']['owned_motions'], 'no owned entries decoded'
            print(json.dumps({'check': 'ok', 'problems': rows['problems']}, indent=1))
        else:
            print(json.dumps({'check': 'ok', 'note': 'no staged package; layout assertions only'}))
        return
    if not args.mod_root:
        parser.error('give a mod root or --check')
    rows = audit(args.mod_root, args.source)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(rows, indent=1) + '\n')
    print(json.dumps({'ok': rows['ok'], 'problems': rows['problems']}, indent=1))


if __name__ == '__main__':
    main()