"""Audit Hero neutral-B inputs without building, installing, or copying assets.

Usage: toolchains/py312/python.exe tools/audit_hero_neutral_b.py [--check]
Writes reproducible source hashes, dependency inventory, donor PRC values, and
native status registrations to refs/brave_special_n. --check compares existing
reports instead of changing them. Smoke test: run normally, then with --check.
All game inputs resolve through paths.toml. Version 1.0.0.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
sys.path.insert(0, str(ROOT / 'tools/nro_decomp'))
import prc
import nro_flatten
import status_table

VERSION = '1.0.0'
DEST = ROOT / 'refs/brave_special_n'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def selected_status(name):
    return name == 'FIGHTER_STATUS_KIND_SPECIAL_N' or name.startswith(
        ('FIGHTER_BRAVE_STATUS_KIND_SPECIAL_N_', 'WEAPON_BRAVE_FIREBALL_STATUS_KIND_'))


def generate():
    cfg = tomllib.loads((ROOT / 'paths.toml').read_text(encoding='utf-8'))
    arc = ROOT / cfg['dumps']['arc']
    scripts = ROOT / cfg['dumps']['scripts'] / 'smashline/lua2cpp_brave'
    files = set()
    missing = []
    required = ['fighter/brave/param/vl.prc', 'fighter/brave/model/body/c00/model.nusktb',
                'fighter/brave/motion/body/c00/motion_list.bin',
                'fighter/elight/motion/body/c00/motion_list.bin',
                'fighter/elight/model/body/c06/model.nusktb',
                'prebuilt/nro/release/lua2cpp_brave.nro',
                'prebuilt/nro/release/lua2cpp_common.nro',
                'effect/fighter/brave/ef_brave.eff']
    for air in ('', 'air'):
        for phase in ('start', 'hold', 'cancel', '1', '2', '3'):
            required.append(f'fighter/brave/motion/body/c00/d00special{air}n{phase}.nuanmb')
    for name in required:
        path = arc / name
        if path.is_file():
            files.add(path)
        elif name == 'fighter/brave/motion/body/c00/motion_list.bin' and (DEST / 'motion_list.bin').is_file():
            files.add(DEST / 'motion_list.bin')
        else:
            missing.append(name)
    for folder in ('fighter/brave/model/fireball', 'fighter/brave/motion/fireball'):
        files.update(p for p in (arc / folder).rglob('*') if p.is_file())
    for folder in ('sound/bank/fighter', 'sound/bank/fighter_voice'):
        files.update(p for p in (arc / folder).glob('*brave*') if p.is_file())
    script_files = sorted(p for p in (scripts / 'brave').glob('*.txt')
                          if p.name.startswith(('SpecialN', 'SpecialAirN')))
    script_files += sorted((scripts / 'brave_fireball').glob('*.txt'))
    assert script_files, 'donor ACMD absent'
    files.update(script_files)
    files.add(arc / 'fighter/common/param/fighter_param.prc')
    sequence = DEST / 'sound/arc/sound/sequence/fighter/brave.sqb'
    if sequence.is_file():
        files.add(sequence)
    text = '\n'.join(p.read_text(encoding='utf-8') for p in script_files)
    functions = sorted(set(re.findall(r'fn\s+((?:game|effect|sound|expression)_\w+)', text)))
    constants = sorted(set(re.findall(r'\b(?:FIGHTER_BRAVE|WEAPON_BRAVE)_[A-Z0-9_]+', text)))
    resources = sorted(set(re.findall(r'Hash40::new\("([^"\n]+)"\)', text)))
    labels = {}
    label_file = ROOT / cfg['dumps']['scripts'].split('/SSBU-')[0] / 'ParamLabels.csv'
    files.add(label_file)
    for line in label_file.read_text(encoding='utf-8', errors='replace').splitlines():
        pieces = line.split(',')
        if len(pieces) > 1:
            try:
                labels[int(pieces[0], 16)] = pieces[1]
            except ValueError:
                pass

    def labelled(node):
        tag, value = node
        if tag == 'struct':
            value = {labels.get(key, f'0x{key:010x}'): labelled(val) for key, val in value}
        elif tag == 'list':
            value = [labelled(val) for val in value]
        return {'type': tag, 'value': value}

    params = {}
    for key, node in prc.read(arc / 'fighter/brave/param/vl.prc')[1]:
        name = labels.get(key, f'0x{key:010x}')
        if 'special_n' in name or 'fireball' in name:
            params[name] = labelled(node)
    assert params, 'neutral-B PRC table selection failed'
    native = arc / 'prebuilt/nro/release/lua2cpp_brave.nro'
    image, meta = nro_flatten.flatten(native.read_bytes())
    rows = [row for row in status_table.table(image, meta) if selected_status(row[0])]
    assert any('FIREBALL' in row[0] for row in rows)
    assert any('SPECIAL_N_HOLD' in row[0] for row in rows)
    assert not selected_status('FIGHTER_BRAVE_STATUS_KIND_SPECIAL_S_HOLD')
    outputs = {'status_table.txt': ''.join(f'{a} {b} {c:#x}\n' for a, b, c in rows)}
    source = {
        'date': '2026-09-30', 'tool': 'tools/audit_hero_neutral_b.py', 'tool_version': VERSION,
        'tool_sha256': digest(Path(__file__)), 'game_version': cfg['switch']['game_version'],
        'donor': 'brave', 'recipient': 'elight c06/c07',
        'scope': 'Hero neutral-B mechanics, animations, fireball and effects; omit mana',
        'classification': [2, 3, 5, 6], 'evidence_tier': 'B (offline inventory only)',
        'acmd_upstream': {'url': 'https://github.com/WuBoytH/SSBU-Dumped-Scripts',
                          'commit': None,
                          'note': 'Local export has no git metadata. Hashes pin these exact local files; upstream commit remains unverified.'},
        'inputs': {p.relative_to(ROOT).as_posix(): {'sha256': digest(p), 'bytes': p.stat().st_size}
                   for p in sorted(files)}, 'missing_arc_paths': missing,
    }
    pin = DEST / 'acmd_pin.json'
    if pin.is_file():
        record = json.loads(pin.read_text(encoding='utf-8'))
        if record['all_match']:
            source['acmd_upstream'] = {'url': record['repo'], 'commit': record['commit'],
                                       'verification': 'refs/brave_special_n/acmd_pin.json',
                                       'sha256': digest(pin)}
    source['derived_evidence'] = {name: digest(DEST / name) for name in
                                ('neutral_b_status.c', 'shoot_control.c', 'fireball_native.json', 'fireball_init.asm')
                                if (DEST / name).is_file()}
    source['native_recovery'] = {
        'method': 'tools/nro_decomp/run_ghidra.sh; Ghidra 11.1.2; BinaryLoader base 0; annotate_c.py',
        'selection': 'status_table.txt callbacks, then referenced FUN_/LAB_ and void-pointer callbacks from the first pass',
        'output': 'refs/brave_special_n/neutral_b_status.c',
        'limitations': 'Decompiler loses Lua-stack arguments and some hash40 length bytes; cross-check disassembly before porting. Further helper tracing may still be needed.',
    }
    dependencies = {
        'evidence_tier': 'B', 'not_runtime_validation': True,
        'functions': functions, 'acmd_work_and_article_constants': constants,
        'acmd_hash40_resources': resources, 'donor_parameter_tables': params,
        'native_status_rows': [{'status': a, 'condition': b, 'nro_offset': hex(c)} for a, b, c in rows],
        'implementation_requirements': [
            'Own elight statuses allocated after Hero Spin block 0x1F1..0x1F4, starting at 0x1F5.',
            'Own motion kinds; copy donor motion-list entries whole; retarget donor tracks by skeleton names.',
            'Charge, stored charge, ground/air transitions, shield/roll/jump cancels and three release levels from native donor code.',
            'Remove mana cost/failure branches, not charging or release timing; never call Brave fighter methods on Mythra.',
            'Clone fireball article and supply all eight costume file groups; audit constructor and owner parameter accesses first.',
            'Own fireball flight/burst status logic with donor values and no Hero owner work-id assumptions.',
            'Merge copied fireball/charge effects into existing Mythra one-slot banks, preserving native Mythra effects and current colours.',
            'Copy required donor sounds; no substitute sounds or unresolved Brave names.',
            'Gate fighter entry/status/ACMD using set_costume([6,7]); log state transitions and projectile consequences to file.',
            'No build, packaging, asset generation or installation until user authorizes.',
        ],
    }
    outputs['SOURCE.json'] = json.dumps(source, indent=2) + '\n'
    outputs['DEPENDENCIES.json'] = json.dumps(dependencies, indent=2) + '\n'
    return outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    outputs = generate()
    if not args.check:
        DEST.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        path = DEST / name
        if args.check:
            assert path.read_text(encoding='utf-8') == content, f'stale: {path.relative_to(ROOT)}'
        else:
            path.write_text(content, encoding='utf-8')
    missing = json.loads(outputs['SOURCE.json'])['missing_arc_paths']
    print(f'Hero neutral-B audit {VERSION}: {len(outputs)} reports; missing ARC paths: {missing}')


if __name__ == '__main__':
    main()
