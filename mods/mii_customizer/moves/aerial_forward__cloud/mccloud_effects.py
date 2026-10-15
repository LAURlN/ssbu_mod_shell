#!/usr/bin/env python3
"""Add Cloud's emitter sets for forward air and Climhazzard to ANY Mii Gunner effect bank.

The Gunner's loader only reads `effect/fighter/miigunner/ef_miigunner.eff` (workspace
`kb/findings/effect-ownership-of-donor-banks-and-per-slot-trails.md`), so Cloud's sets have to live in that
bank. This script does not own that file: it takes a base bank (vanilla, or one another unit already merged
into) and writes base + the eight sets below. Run it once per base.

    python -I mods/mii_customizer/moves/aerial_forward__cloud/mccloud_effects.py \
        --base <ef_miigunner.eff> --output <dir under gamedata/mii_customizer/moves/aerial_forward__cloud>/ef_miigunner.eff

Method: the reference repo's merge (mods/ssbu_mod_new/tools/merge_hero_neutral_b_effects.py 1.2.0, copied
and reduced): dump both banks with the pinned EffectConverter, copy the donor emitter-set folders, relocate
texture / model ids that collide with a different payload, append the handle entries, repack, dump the
result again and compare every decoded emitter field and payload hash with the inputs.

Added to the bank (handle name -> donor handle, donor emitter set):
    MC_CLOUD_SWORD_FLARE       CLOUD_SWORD_FLARE       forward air, sword glow
    MC_CLOUD_AIRF_SLASH        CLOUD_AIRF_SLASH        forward air, slash arc
    MC_CLOUD_SPEEDLINE         CLOUD_SPEEDLINE         Climhazzard start
    MC_CLOUD_CLIMHAZZARD_SWORD CLOUD_CLIMHAZZARD_SWORD Climhazzard, sword glow
    MC_CLOUD_CLIMHAZZARD_STING / _SLASH / _SLASH2 / _SLASH3
The handle is renamed (the brief's mc_cloud_ prefix; a real Cloud in the same match keeps his own names);
the emitter data is not changed.

Tier B only: no offline check shows an effect on screen.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mccloud_common import WORKSPACE, DONOR, MOD, G, rel, sha256  # noqa: E402

CONVERTER = WORKSPACE / 'mods/ssbu_mod_new/builds/.cache/hero_effect_converter/bin/EffectConverter.exe'  # read-only tool
DONOR_BANK = DONOR / 'effect/fighter/cloud/ef_cloud.eff'
DONOR_SHA256 = None  # filled from the manifest by callers that pin it; the merge record stores the hash it used
PREFIX = 'MC_'
EFFECTS = ('CLOUD_SWORD_FLARE', 'CLOUD_AIRF_SLASH', 'CLOUD_SPEEDLINE', 'CLOUD_CLIMHAZZARD_SWORD',
           'CLOUD_CLIMHAZZARD_STING', 'CLOUD_CLIMHAZZARD_SLASH', 'CLOUD_CLIMHAZZARD_SLASH2',
           'CLOUD_CLIMHAZZARD_SLASH3')
MODEL_REFERENCE_FIELDS = ('PrimitiveID', 'PrimitiveExID', 'PrimitiveIndex')
SCRATCH = MOD / 'builds/.cache/MV-aerial_forward__cloud-target/effect_work'


def dotnet() -> Path:
    found = shutil.which('dotnet')
    if not found:
        raise RuntimeError('no dotnet launcher on PATH (needed only when an id has to be relocated)')
    return Path(found)


def convert(path: Path, cwd: Path):
    cwd.mkdir(parents=True, exist_ok=True)
    r = subprocess.run([str(CONVERTER), str(path.resolve())], cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr + r.stdout[-3000:])


def dump(path: Path, cwd: Path) -> Path:
    convert(path, cwd)
    folder = cwd / path.stem
    if not (folder / 'NamcoFile.json').exists():
        raise RuntimeError(f'converter wrote no NamcoFile.json for {path}')
    return folder


def jread(path: Path):
    return json.loads(path.read_text())


def semantic(folder: Path) -> dict:
    relocated = {'ShaderIndex', 'UserShaderIndex1', 'UserShaderIndex2', 'ComputeShaderIndex'}

    def norm(v):
        if isinstance(v, dict):
            return {k: norm(x) for k, x in v.items() if k not in relocated}
        if isinstance(v, list):
            return [norm(x) for x in v]
        return v

    out = {}
    for p in folder.rglob('*.json'):
        if p.name != 'NamcoFile.json':
            out[p.relative_to(folder).as_posix()] = norm(jread(p))
    for p in folder.rglob('*.bin'):
        if p.name != 'EmitterData.bin':
            out[p.relative_to(folder).as_posix()] = sha256(p)
    for ext in ('.bfres', '.bntx', '.bnsh'):
        for p in folder.rglob('*' + ext):
            out[p.relative_to(folder).as_posix()] = sha256(p)
    return out


def merge(base: Path, output: Path, effects=EFFECTS) -> dict:
    base, output = Path(base).resolve(), Path(output).resolve()
    if not output.is_relative_to(G) and not output.is_relative_to(MOD / 'builds/.cache'):
        raise RuntimeError('output must be under gamedata/mii_customizer or builds/.cache')
    if not CONVERTER.is_file():
        raise RuntimeError(f'EffectConverter missing at {rel(CONVERTER)}')
    SCRATCH.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='merge_', dir=SCRATCH))
    donor = dump(DONOR_BANK, work / 'donor')
    target = dump(base, work / 'recipient')
    baseline = semantic(target)
    donor_entries = jread(donor / 'NamcoFile.json')
    target_entries = jread(target / 'NamcoFile.json')
    names = set(effects)
    selected = [e for e in donor_entries if e['Name'] in names]
    if {e['Name'] for e in selected} != names:
        raise RuntimeError(f'donor bank lacks {sorted(names - {e["Name"] for e in selected})}')
    if any(e['ExternalModelFlag'] or e['Variants'] for e in selected):
        raise RuntimeError('a selected set needs an external model or variants; not handled')
    have = {e['Name'] for e in target_entries}
    if have & {PREFIX + n for n in names}:
        raise RuntimeError('the base bank already has MC_CLOUD_* handles: merge onto a bank without them')
    donor_order = jread(donor / 'EmitterSetInfo.txt')['Order']
    target_order = jread(target / 'EmitterSetInfo.txt')['Order']
    expected = dict(baseline)

    resources = {}
    for p in target.rglob('*'):
        if p.suffix in ('.bntx', '.bfres'):
            resources.setdefault((p.suffix, p.stem), set()).add(sha256(p))
    used = {int(p.stem) for root in (target, donor) for p in root.rglob('*') if p.suffix in ('.bntx', '.bfres')}
    tex_reloc, model_reloc = {}, {}
    selected_sets = sorted({donor_order[e['EmitterSet_ID'] - 1] for e in selected})
    for suffix, table, salt in (('.bntx', tex_reloc, 'mccloud_texture'), ('.bfres', model_reloc, 'mccloud_model')):
        for name in selected_sets:
            for p in (donor / name).rglob('*' + suffix):
                key = (suffix, p.stem)
                if key in resources and resources[key] != {sha256(p)}:
                    old = int(p.stem)
                    if old not in table:
                        new = int(hashlib.sha256(f'{salt}_{old}'.encode()).hexdigest()[:8], 16)
                        while new in used:
                            new = (new + 1) & 0xffffffff
                        used.add(new)
                        table[old] = new

    def relocate(v):
        if isinstance(v, dict):
            out = {}
            for k, x in v.items():
                if k == 'TextureID':
                    out[k] = tex_reloc.get(x, x)
                elif k in MODEL_REFERENCE_FIELDS and isinstance(x, int) and x in model_reloc:
                    out[k] = model_reloc[x]
                else:
                    out[k] = relocate(x)
            return out
        if isinstance(v, list):
            return [relocate(x) for x in v]
        return v

    controls = []
    mapping = {}
    for entry in selected:
        old_id = entry['EmitterSet_ID']
        if old_id not in mapping:
            name = donor_order[old_id - 1]
            if name in target_order:
                raise RuntimeError(f'emitter set name {name} already in the base bank')
            dest = target / name
            shutil.copytree(donor / name, dest)
            for suffix, table, helper in (('.bfres', model_reloc, 'HeroModelRename.dll'),
                                          ('.bntx', tex_reloc, 'HeroTextureRename.dll')):
                for p in list(dest.rglob('*' + suffix)):
                    old = int(p.stem)
                    if old in table:
                        new = table[old]
                        renamed = p.with_name(f'{new}{suffix}')
                        r = subprocess.run([str(dotnet()), str(CONVERTER.with_name(helper)), str(p), str(renamed),
                                            f'mccloud_{new}'], capture_output=True, text=True)
                        if r.returncode != 0:
                            raise RuntimeError(r.stdout + r.stderr)
                        controls.append({'kind': suffix, 'old_id': old, 'new_id': new,
                                         'original_sha256': sha256(p), 'renamed_sha256': sha256(renamed)})
                        p.unlink()
            for p in dest.rglob('*.json'):
                data = jread(p)
                moved = relocate(data)
                if moved != data:
                    p.write_text(json.dumps(moved, indent=2))
            for p in dest.rglob('*'):
                if p.suffix in ('.bntx', '.bfres'):
                    key = (p.suffix, p.stem)
                    if key in resources and resources[key] != {sha256(p)}:
                        raise RuntimeError(f'resource id collision left after relocation: {key}')
                    resources.setdefault(key, set()).add(sha256(p))
            target_order.append(name)
            mapping[old_id] = len(target_order)
            for k, v in semantic(dest).items():
                expected[name + '/' + k] = v
        new_entry = copy.deepcopy(entry)
        new_entry['Name'] = PREFIX + entry['Name']
        new_entry['EmitterSet_ID'] = mapping[old_id]
        target_entries.append(new_entry)
    (target / 'EmitterSetInfo.txt').write_text(json.dumps({'Order': target_order}, indent=2))
    (target / 'NamcoFile.json').write_text(json.dumps(target_entries, indent=2))
    convert(target, work / 'recipient')
    packed = work / 'recipient' / (target.name + '_NEW.eff')
    if not packed.exists():
        raise RuntimeError('converter wrote no repacked bank')
    reread = dump(packed, work / 'verification')
    if semantic(reread) != expected:
        raise RuntimeError('repacked bank: decoded emitter fields or payload hashes changed')
    if jread(reread / 'NamcoFile.json') != target_entries:
        raise RuntimeError('repacked bank: handle table changed')
    if jread(reread / 'EmitterSetInfo.txt')['Order'] != target_order:
        raise RuntimeError('repacked bank: emitter set order changed')
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(packed, output)
    record = {
        'tool': 'mccloud_effects.py', 'evidence_tier': 'B', 'hardware_validated': False,
        'base': rel(base), 'base_sha256': sha256(base), 'base_handles': len(have),
        'donor': rel(DONOR_BANK), 'donor_sha256': sha256(DONOR_BANK),
        'output': rel(output), 'output_sha256': sha256(output), 'output_handles': len(target_entries),
        'added_handles': {PREFIX + e['Name']: {'donor_handle': e['Name'], 'kind': e['Kind'],
                                               'emitter_set': donor_order[e['EmitterSet_ID'] - 1]}
                          for e in selected},
        'id_relocations': controls,
        'base_emitter_fields_and_payloads_preserved': True,
        'donor_emitter_fields_and_payloads_preserved': True,
        'converter_sha256': sha256(CONVERTER),
    }
    output.with_suffix('.merge.json').write_text(json.dumps(record, indent=2) + '\n')
    shutil.rmtree(work, ignore_errors=True)
    return record


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--base', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    rec = merge(a.base, a.output)
    print(f"merged {len(rec['added_handles'])} handles into {rec['output']} "
          f"({rec['base_handles']} -> {rec['output_handles']}), {len(rec['id_relocations'])} ids relocated, "
          f"sha256 {rec['output_sha256']}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
