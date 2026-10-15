"""Inventory a built mod tree's fighter effect banks and per-slot trail folders.

Why this exists
---------------
Two ownership questions kept coming up and neither had an answer in the tree:

1. *Which fighter actually loads a `.eff` file this mod ships?* The One Slot
   Effects plugin (`src/pgwr/tools/one_slot_effects_reference.rs`,
   `check_extension_eff_inline_hook`, main+0x355f66c) only accepts, inside
   `effect/fighter/<fighter>/`, a file whose name hash is `ef_<fighter>.eff` or
   `ef_<fighter>_c<slot>.eff`. A bank filed under any other fighter's folder is
   shipped but never loaded by anybody.
2. *Which trail textures can ever be requested?* A trail is looked up by name
   (`Hash40` of the label), so a file whose internal NUTEXB resource name is not
   a known label can never be drawn - and two files in one slot folder that
   share an internal name register the same resource twice under the plugin's
   `<NAME>_C<slot>` rename.

Both are byte-level facts about the *packaged* tree, so they are measurable
without a console. Tier **B**. Nothing here says an effect draws in game.

Usage
-----
    python tools/effect_trail_inventory.py <mod_dir> [--labels dumps/scripts/ParamLabels.csv]
                                             [--json out.json] [--package builds/pgwr/0.20.16]

`<mod_dir>` is the packaged mod (the directory holding `config.json`), e.g.
`builds/pgwr/0.20.16/ultimate/mods/pyra_gamewatch_reskin`. With `--package` the
tool also resolves `<package>/ultimate/mods/*` itself.

Smoke test
----------
    python tools/effect_trail_inventory.py builds/pgwr/0.20.16 --smoke
checks the reader against the pinned Cloud donor in `refs/cloud_attack_air_f/`
and exits non-zero if the footer name is not recovered.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABELS = ROOT / 'dumps' / 'scripts' / 'ParamLabels.csv'
FOOTER_SIZE = 0x70  # nutexb footer region the one-slot plugin reads/writes


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def nutexb_name(path: Path) -> str | None:
    """The internal NUTEXB resource name, read from the trailing footer.

    Same region `get_raw_nutexb_data` (main+0x355ff00) parses and renames, so
    this is the string the One Slot Effects plugin turns into `<name>_C<slot>`
    and the string the engine registers the loaded texture under.
    """
    raw = path.read_bytes()
    if len(raw) < FOOTER_SIZE:
        return None
    footer = raw[-FOOTER_SIZE:]
    tag = footer.find(b'XNT')  # the name string starts right after the chunk tag
    if tag < 0:
        return None
    found = re.match(rb'[A-Z0-9_]{4,}', footer[tag + 3:])
    return found.group().decode('ascii') if found else None


def load_labels(path: Path) -> set[str]:
    """Lowercased label names from the dumped ParamLabels table (tier B/C).

    A trail is requested by the `Hash40` of a label the engine already knows, so
    a shipped texture whose internal name is not in this set can never be drawn.
    """
    names: set[str] = set()
    if not path.is_file():
        return names
    with path.open(newline='', encoding='utf-8', errors='replace') as handle:
        for row in csv.reader(handle):
            if len(row) < 2 or not row[0].startswith('0x'):
                continue
            names.add(row[1].strip().lower())
    return names


def eff_names(path: Path) -> list[str]:
    """Emitter names from the EFFN prefix string table (before the VFXB payload).

    Same shape as `parse_effect_names` in `src/pgwr/tools/eff_reference.rs` and
    `eff_names` in `tools/build_littlemac_fsmash_effect.py`.
    """
    raw = path.read_bytes()
    marker = raw.find(b'VFXB')
    if marker <= 0:
        return []
    prefix, names, i = raw[:marker], [], 0
    while i < len(prefix):
        if prefix[i] == 0 or not chr(prefix[i]).isascii():
            i += 1
            continue
        end = prefix[i:].find(b'\x00')
        if end is None:
            end = 0
        if end >= 4:
            text = prefix[i:i + end].decode('ascii', 'replace')
            if all(c.isalnum() or c in '_-.' for c in text):
                names.append(text)
        i += end + 1
    return names


def resolve(package: Path | None, mod_dir: Path | None) -> Path:
    if mod_dir:
        return mod_dir
    if package:
        found = sorted((package / 'ultimate' / 'mods').iterdir())
        if len(found) != 1:
            raise SystemExit(f'{package}/ultimate/mods holds {len(found)} entries; pass the mod dir')
        return found[0]
    raise SystemExit('pass a mod dir or a --package directory')


def inventory(mod_dir: Path, labels: set[str]) -> dict:
    fighters: dict[str, dict] = {}
    for bank_dir in sorted((mod_dir / 'effect' / 'fighter').glob('*')):
        if not bank_dir.is_dir():
            continue
        slots: dict[str, dict] = {}
        banks: dict[str, dict] = {}
        for path in sorted(bank_dir.iterdir()):
            if path.is_file() and path.suffix == '.eff':
                banks[path.name] = {
                    'sha256': sha256(path),
                    'bytes': path.stat().st_size,
                    'emitters': len(eff_names(path)),
                }
            elif path.is_dir() and path.name.startswith('trail_c'):
                slot = path.name[len('trail_c'):]
                files = []
                for texture in sorted(path.iterdir()):
                    if not texture.is_file() or texture.suffix != '.nutexb':
                        continue
                    internal = nutexb_name(texture)
                    files.append({
                        'file': texture.name,
                        'sha256': sha256(texture),
                        'bytes': texture.stat().st_size,
                        'internal_name': internal,
                        'internal_name_is_engine_label': (
                            internal is not None and internal.lower() in labels),
                        'file_stem_is_engine_label': texture.stem.lower() in labels,
                    })
                names: dict[str, list[str]] = {}
                for entry in files:
                    names.setdefault(entry['internal_name'], []).append(entry['file'])
                slots[slot] = {
                    'files': files,
                    'duplicate_internal_names': {k: v for k, v in names.items()
                                                if len(v) > 1},
                    'unrequestable_files': [f['file'] for f in files
                                            if not (f['internal_name_is_engine_label']
                                                    or f['file_stem_is_engine_label'])],
                }
        # A bank is only loaded by the fighter whose directory holds it, and only
        # under the name ef_<fighter>.eff or ef_<fighter>_c<slot>.eff
        # (one_slot_effects_reference.rs, check_extension_eff_inline_hook).
        accepted = {name: (name == f'ef_{bank_dir.name}.eff'
                           or (name.startswith(f'ef_{bank_dir.name}_c')
                               and name.endswith('.eff')))
                    for name in banks}
        fighters[bank_dir.name] = {
            # Only this fighter kind's own effect loader searches this folder, so
            # a bank filed here is reachable only by this fighter.
            'bank_loader_fighter': bank_dir.name,
            'slots': slots,
            'banks': banks,
            'banks_loaded_by_this_fighter': accepted,
            'banks_not_loaded_by_any_fighter': [n for n, ok in accepted.items() if not ok],
        }
    return {'mod_dir': mod_dir.as_posix(), 'label_count': len(labels),
            'fighters': fighters}


def cross_slot_bytes(report: dict) -> dict:
    """Files whose bytes are identical in c06 and c07 but whose names are shared.

    Identical bytes under a shared internal name cannot be told apart by the
    engine; after the plugin's rename they are still two registrations of one
    name per slot, which is the shape to remove first.
    """
    out = {}
    for fighter, data in report['fighters'].items():
        for slot, info in data['slots'].items():
            if not slot.isdigit():
                continue
            other = '07' if slot == '06' else '06'
            peer = data['slots'].get(other)
            if not peer:
                continue
            mine = {f['file']: f['sha256'] for f in info['files']}
            theirs = {f['file']: f['sha256'] for f in peer['files']}
            same = sorted(n for n, h in mine.items() if theirs.get(n) == h)
            if same:
                out.setdefault(fighter, {})[f'c{slot}_vs_c{other}_identical_bytes'] = same
    return out


def smoke() -> None:
    donor = ROOT / 'refs' / 'cloud_attack_air_f' / 'trail'
    assert donor.is_dir(), f'{donor} missing; run the T-0035 pin'
    for texture in sorted(donor.iterdir()):
        name = nutexb_name(texture)
        assert name, f'{texture.name}: no internal resource name recovered'
        assert name == texture.stem.upper(), f'{texture.name}: name/file disagree ({name})'
        print(f'  {texture.name}: internal={name}')
    bank = ROOT / 'refs' / 'littlemac_attack_s4' / 'arc' / 'effect' / 'fighter' / 'littlemac' / 'ef_littlemac.eff'
    assert bank.is_file(), f'{bank} missing'
    names = eff_names(bank)
    for required in ('LITTLEMAC_ATTACK_LINE', 'LITTLEMAC_ATTACK_ARC'):
        assert required in names, f'{required} not in the pinned donor bank'
    print('PASS footer names and donor emitters recovered from the pinned refs')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('mod_dir', nargs='?', type=Path)
    parser.add_argument('--package', type=Path)
    parser.add_argument('--labels', type=Path, default=DEFAULT_LABELS)
    parser.add_argument('--json', type=Path)
    parser.add_argument('--smoke', action='store_true')
    args = parser.parse_args()

    if args.smoke:
        smoke()
        return
    report = inventory(resolve(args.package, args.mod_dir), load_labels(args.labels))
    report['cross_slot'] = cross_slot_bytes(report)
    text = json.dumps(report, indent=2)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + '\n', encoding='utf-8')
        print(f'wrote {args.json}')
    for fighter, data in report['fighters'].items():
        foreign = data['banks_not_loaded_by_any_fighter']
        print(f'{fighter}: banks {list(data["banks"])}'
              + (f' NOT LOADED BY ANY FIGHTER: {foreign}' if foreign else ''))
        for slot, info in data['slots'].items():
            if not slot.isdigit():
                continue
            dupes = info['duplicate_internal_names']
            dead = info['unrequestable_files']
            print(f'  c{slot}: {len(info["files"])} nutexb'
                  + (f'; duplicate internal names {dupes}' if dupes else '')
                  + (f'; never requestable {dead}' if dead else ''))
    print(text if not args.json else '')


if __name__ == '__main__':
    sys.exit(main())
