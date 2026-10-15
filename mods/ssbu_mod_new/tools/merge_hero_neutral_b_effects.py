"""Merge the original Hero neutral-B emitters into an existing Mythra bank.

Version 1.2.0. Requires the repaired EffectConverter configured in paths.toml
(`python tools/build_hero_effect_converter.py --from-source` builds it from the
pinned EffectLibrary source),
source pinned to EffectLibrary d5491138d645221ec92189eeff3ded8c43fd0a1a.
All converter outputs stay in dated scratch. Emitter ids are remapped; donor
colors and curves are preserved. Resource-id collisions are rejected. Re-export
must preserve every decoded emitter field other than relocated shader indices.
Smoke test: --check validates the pinned donor resource list and converter.
Usage: --recipient <existing.eff> --output <builds/.../merged.eff>.
No claim about in-game loading follows from a successful offline merge.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CFG = tomllib.loads((ROOT / 'paths.toml').read_text())
CONVERTER = ROOT / CFG['toolchain']['hero_effect_converter']
ARC = Path(CFG['dumps']['arc'])
SCRATCH = ROOT / 'scratch/2026-09-30_codex'
PIN = 'd5491138d645221ec92189eeff3ded8c43fd0a1a'


def dotnet():
    """Machine path from paths.toml when set, else the launcher on PATH."""
    configured = CFG['toolchain'].get('dotnet_runtime') or ''
    if configured:
        return Path(configured).parents[2] / 'dotnet.exe'
    found = shutil.which('dotnet')
    assert found, 'No .NET runtime: set toolchain.dotnet_runtime in paths.toml'
    return Path(found)


# EmitterData fields that name a G3PR model descriptor by id. Any other field
# holding a matching integer is not a model reference and must not be rewritten.
MODEL_REFERENCE_FIELDS = ('PrimitiveID', 'PrimitiveExID', 'PrimitiveIndex')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def required():
    deps = json.loads((ROOT / 'refs/brave_special_n/DEPENDENCIES.json').read_text())
    native = json.loads((ROOT / 'refs/brave_special_n/owned_initializer.json').read_text())
    return ({n.upper() for n in deps['acmd_hash40_resources'] if n.startswith('brave_')}
            | {n.upper() for n in native['native_effect_resources']})


def convert(path, cwd):
    cwd.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([str(CONVERTER), str(path.resolve())], cwd=cwd,
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr + result.stdout[-3000:]
    return result


def dump(path, cwd):
    convert(path, cwd)
    folder = cwd / path.stem
    assert (folder / 'NamcoFile.json').exists()
    return folder


def json_read(path):
    return json.loads(path.read_text())


def semantic_emitters(folder):
    result = {}
    # Indices refer to the rebuilt bank, not to a changed shader.
    relocated = {'ShaderIndex', 'UserShaderIndex1', 'UserShaderIndex2', 'ComputeShaderIndex'}

    def normalize(value):
        if isinstance(value, dict):
            return {k: normalize(v) for k, v in value.items() if k not in relocated}
        if isinstance(value, list):
            return [normalize(v) for v in value]
        return value

    for path in folder.rglob('*.json'):
        if path.name == 'NamcoFile.json':
            continue
        result[path.relative_to(folder).as_posix()] = normalize(json_read(path))
    # Animation and other opaque subsections must retain exact bytes.
    for path in folder.rglob('*.bin'):
        if path.name == 'EmitterData.bin':
            continue
        result[path.relative_to(folder).as_posix()] = sha(path)
    # The repaired converter round-trips these exported payloads exactly.
    # This also checks primitive geometry, encoded textures and shader bytes.
    for extension in ('.bfres', '.bntx', '.bnsh'):
        for path in folder.rglob('*' + extension):
            result[path.relative_to(folder).as_posix()] = sha(path)
    return result


def merge(recipient, output, *, donor_file=None, effect_names=None, donor_sha256=None,
          scratch=None):
    """Explicit donors require a pinned hash; default Hero callers keep their contract."""
    output = Path(output).resolve()
    assert any(output.is_relative_to(ROOT / n) for n in ('builds', 'scratch'))
    recipient = Path(recipient).resolve()
    names = set(required() if effect_names is None else effect_names)
    assert names, 'No donor resources requested'
    if donor_file is None:
        rel = 'effect/fighter/brave/ef_brave.eff'
        donor_file = ARC / rel
        source = json_read(ROOT / 'refs/brave_special_n/SOURCE.json')
        # The export may sit outside the repository (paths.toml [dumps] arc is an
        # absolute path on this machine), so match the recorded input by its ARC
        # suffix rather than by a path relative to ROOT.
        recorded = {k.rsplit('/', 1)[-1]: v['sha256'] for k, v in source['inputs'].items()}
        assert Path(rel).name in recorded, f'no pinned hash for {rel} in refs/brave_special_n/SOURCE.json'
        donor_sha256 = recorded[Path(rel).name]
    donor_file = Path(donor_file).resolve()
    assert donor_sha256 and sha(donor_file) == donor_sha256, 'Donor provenance mismatch'
    assert CONVERTER.is_file(), 'Missing configured repaired EffectConverter'
    work_root = Path(scratch).resolve() if scratch else SCRATCH
    work_root.mkdir(parents=True, exist_ok=True)
    # Immutable content-addressed work directory: no stale converter output.
    tag = hashlib.sha256((sha(recipient) + sha(donor_file) +
                          sha(CONVERTER.with_name('EffectLibrary.dll'))).encode()).hexdigest()[:16]
    work = Path(tempfile.mkdtemp(prefix=f'hero_effect_merge_{tag}_', dir=work_root))
    donor = dump(donor_file, work / 'donor')
    target = dump(recipient, work / 'recipient')
    baseline = semantic_emitters(target)
    donor_entries = json_read(donor / 'NamcoFile.json')
    target_entries = json_read(target / 'NamcoFile.json')
    selected = [e for e in donor_entries if e['Name'] in names]
    assert {e['Name'] for e in selected} == names
    assert not any(e['ExternalModelFlag'] or e['Variants'] for e in selected), ('Unsupported external model or variant dependencies; stop rather than omit them', selected)
    assert not ({e['Name'] for e in selected} & {e['Name'] for e in target_entries})
    donor_order = json_read(donor / 'EmitterSetInfo.txt')['Order']
    target_order = json_read(target / 'EmitterSetInfo.txt')['Order']
    expected = dict(baseline)
    # Texture and model ids are bank-global. Reject different payloads with a
    # shared id; silently keeping the first would change Hero's fireball, and
    # AddPrimitive drops a duplicate model id without a word, so the donor's
    # arc would draw the recipient's mesh.
    resources = {}
    for path in target.rglob('*'):
        if path.suffix in ('.bntx', '.bfres'):
            resources.setdefault((path.suffix, path.stem), set()).add(sha(path))
    relocations = {}
    model_relocations = {}
    selected_sets = {donor_order[e['EmitterSet_ID'] - 1] for e in selected}
    used_ids = {int(p.stem) for root in (target, donor) for p in target.rglob('*')
                if p.suffix in ('.bntx', '.bfres')}
    used_ids |= {int(p.stem) for root in (target, donor) for p in donor.rglob('*')
                 if p.suffix in ('.bntx', '.bfres')}
    for suffix, table, salt in (('.bntx', relocations, 'pgwr_hero_texture'),
                                ('.bfres', model_relocations, 'pgwr_hero_model')):
        for name in sorted(selected_sets):
            for path in (donor / name).rglob('*' + suffix):
                key = (suffix, path.stem)
                if key in resources and resources[key] != {sha(path)}:
                    old = int(path.stem)
                    if old not in table:
                        new = int(hashlib.sha256(f'{salt}_{old}'.encode()).hexdigest()[:8], 16)
                        while new in used_ids:
                            new = (new + 1) & 0xffffffff
                        used_ids.add(new)
                        table[old] = new

    def relocate_json(value):
        if isinstance(value, dict):
            out = {}
            for k, v in value.items():
                # The three model references are named fields; TextureID covers
                # every texture sampler at any depth.
                if k == 'TextureID':
                    out[k] = relocations.get(v, v)
                elif k in MODEL_REFERENCE_FIELDS and isinstance(v, int) and v in model_relocations:
                    out[k] = model_relocations[v]
                else:
                    out[k] = relocate_json(v)
            return out
        if isinstance(value, list):
            return [relocate_json(v) for v in value]
        return value

    texture_controls = []
    model_controls = []
    mapping = {}
    for entry in selected:
        old_id = entry['EmitterSet_ID']
        if old_id not in mapping:
            name = donor_order[old_id - 1]
            assert name not in target_order
            src = donor / name
            dest = target / name
            shutil.copytree(src, dest)
            # A model id is the .bfres file name, so relocation is a rename; the
            # payload is kept byte-for-byte and the JSON references move with it.
            # The model's own name is relocated too, because the primitive
            # writer suffixes a duplicate name with its id and that would make
            # the re-exported bank differ from the one we verified.
            for path in list(dest.rglob('*.bfres')):
                old = int(path.stem)
                if old in model_relocations:
                    new = model_relocations[old]
                    renamed = path.with_name(str(new) + '.bfres')
                    helper = CONVERTER.with_name('HeroModelRename.dll')
                    result = subprocess.run([str(dotnet()), str(helper), str(path), str(renamed),
                                             f'pgwr_hero_{new}'], capture_output=True, text=True)
                    assert result.returncode == 0, result.stdout + result.stderr
                    model_controls.append({'old_id': old, 'new_id': new,
                                           'original_sha256': sha(path),
                                           'renamed_sha256': sha(renamed),
                                           'model_name': f'pgwr_hero_{new}',
                                           'every_other_model_field_identical': True})
                    path.unlink()
            for path in list(dest.rglob('*.bntx')):
                old = int(path.stem)
                if old in relocations:
                    renamed = path.with_name(str(relocations[old]) + '.bntx')
                    helper = CONVERTER.with_name('HeroTextureRename.dll')
                    result = subprocess.run([str(dotnet()), str(helper), str(path), str(renamed),
                                             f'pgwr_hero_{relocations[old]}'], capture_output=True, text=True)
                    assert result.returncode == 0, result.stdout + result.stderr
                    texture_controls.append({'old_id': old, 'new_id': relocations[old],
                                             'original_sha256': sha(path), 'renamed_sha256': sha(renamed),
                                             'texture_fields_and_mip_bytes_identical': True})
                    path.unlink()
            for path in dest.rglob('*.json'):
                data = json_read(path)
                relocated = relocate_json(data)
                if relocated != data:
                    path.write_text(json.dumps(relocated, indent=2))
            for path in dest.rglob('*'):
                if path.suffix in ('.bntx', '.bfres'):
                    key = (path.suffix, path.stem)
                    assert key not in resources or resources[key] == {sha(path)}, ('Resource collision', key)
                    resources.setdefault(key, set()).add(sha(path))
            target_order.append(name)
            mapping[old_id] = len(target_order)
            for key, value in semantic_emitters(dest).items():
                expected[name + '/' + key] = value
        new_entry = copy.deepcopy(entry)
        new_entry['EmitterSet_ID'] = mapping[old_id]
        target_entries.append(new_entry)
    (target / 'EmitterSetInfo.txt').write_text(json.dumps({'Order': target_order}, indent=2))
    (target / 'NamcoFile.json').write_text(json.dumps(target_entries, indent=2))
    convert(target, work)
    packed = work / (target.name + '_NEW.eff')
    assert packed.exists()
    reread = dump(packed, work / 'verification')
    observed = semantic_emitters(reread)
    assert expected == observed, 'Emitter serialization changed decoded fields or opaque subsections'
    assert json_read(reread / 'NamcoFile.json') == target_entries
    assert json_read(reread / 'EmitterSetInfo.txt')['Order'] == target_order
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(packed, output)
    record = {'date': '2026-10-02', 'tool_version': '1.2.0', 'evidence_tier': 'B',
              'effect_library_commit': PIN, 'converter_sha256': sha(CONVERTER),
              'library_sha256': sha(CONVERTER.with_name('EffectLibrary.dll')),
              'recipient_sha256': sha(recipient), 'donor_sha256': sha(donor_file),
              'output_sha256': sha(output), 'resource_names': sorted(names),
              'texture_id_relocations': texture_controls,
              'model_id_relocations': model_controls,
              'geometry_texture_shader_payloads_checked': True,
              'decoded_emitter_fields_preserved': True, 'hardware_validated': False}
    output.with_suffix('.merge.json').write_text(json.dumps(record, indent=2) + '\n')
    print(f'Merged and re-export checked {len(selected)} donor effects; '
          f'{len(texture_controls)} texture and {len(model_controls)} model ids relocated')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--recipient', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.check:
        assert CONVERTER.exists()
        assert len(required()) == 16
        print('PASS: converter present; sixteen audited Hero neutral-B effect resources')
    elif args.recipient and args.output:
        merge(args.recipient, args.output)
    else:
        parser.error('choose --check or --recipient and --output')


if __name__ == '__main__':
    main()
