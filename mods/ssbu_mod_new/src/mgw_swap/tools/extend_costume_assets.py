"""Extend the current c07 payload to c06 while retaining c06's original body.

Run after the c07 builders. Motion lists receive only the delta from stock c07;
the G&W body receives only the sword additions from the packaged c07 model.
Never writes the dump or c07. Missing dumps and incompatible rigs are errors.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parent / 'vendor'))
import ssbh_data_py as s
from build_fair_assets import parse_mlist, encode_mlist

ROOT = Path(__file__).resolve().parents[3]
EXPORT = Path(os.environ.get('MGW_EXPORT', ROOT / 'dumps' / 'arc'))
OUTPUT = ROOT / 'mod_output/ultimate/mods/mythra_gamewatch_swap'
RECORD = ROOT / 'mod_files/mythra_gamewatch_swap/c06-assets-validation.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def copy_motions(fighter):
    rel = Path('fighter') / fighter
    stock6 = EXPORT / rel / 'motion/body/c06/motion_list.bin'
    stock7 = EXPORT / rel / 'motion/body/c07/motion_list.bin'
    source = OUTPUT / rel / 'motion/body/c07'
    dest = OUTPUT / rel / 'motion/body/c06'
    # Existing clips were authored for the c07 body; prove the c06 rig is equal.
    require((EXPORT / rel / 'model/body/c06/model.nusktb').read_bytes() ==
            (EXPORT / rel / 'model/body/c07/model.nusktb').read_bytes(),
            f'{fighter}: c06 and c07 rigs differ; explicit retargeting required')
    parsed = [parse_mlist(p) for p in [stock6, stock7, source / 'motion_list.bin']]
    for p, (magic, header, entries) in zip([stock6, stock7, source / 'motion_list.bin'], parsed):
        require(encode_mlist(magic, header, entries) == p.read_bytes(), f'Round-trip failed: {p}')
    magic, header, entries6 = parsed[0]
    entries7, modified7 = parsed[1][2], parsed[2][2]
    require(entries7.keys() <= modified7.keys(), f'{fighter}: unexpected removed motion')
    changes = {k: v for k, v in modified7.items() if k not in entries7 or v['raw'] != entries7[k]['raw']}
    original6 = {k: v['raw'] for k, v in entries6.items()}
    entries6.update(changes)
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / 'motion_list.bin'
    path.write_bytes(encode_mlist(magic, header, entries6))
    readback = parse_mlist(path)
    require(readback[1] == header, f'{fighter}: c06 motion path changed')
    require(encode_mlist(*readback) == path.read_bytes(), f'{fighter}: output round-trip failed')
    require(all(readback[2][k]['raw'] == raw for k, raw in original6.items() if k not in changes),
            f'{fighter}: unrelated c06 motion changed')
    clips = list(source.glob('*.nuanmb'))
    for clip in clips:
        shutil.copy2(clip, dest / clip.name)
        require(sha(clip) == sha(dest / clip.name), f'Clip copy failed: {clip}')
    require({p.name for p in dest.iterdir()} == {p.name for p in source.iterdir()},
            f'{fighter}: stale/unexpected c06 motion files')
    return {'changed_or_added_motions': [f'{k:#x}' for k in changes],
            'unrelated_entries_preserved': len(original6.keys() - changes.keys()),
            'clips': len(clips), 'compatible_rigs': True, 'motion_path_preserved': True,
            'motion_list_sha256': sha(path)}


def inject_sword():
    stock = EXPORT / 'fighter/gamewatch/model/body/c06'
    source = OUTPUT / 'fighter/gamewatch/model/body/c07'
    dest = OUTPUT / 'fighter/gamewatch/model/body/c06'
    dest.mkdir(parents=True, exist_ok=True)
    formats = [
        ('nusktb', s.skel_data.read_skel, 'bones', lambda e: e.name == 'SwordR'),
        ('numshb', s.mesh_data.read_mesh, 'objects', lambda e: e.name.startswith('SwordM')),
        ('numdlb', s.modl_data.read_modl, 'entries', lambda e: e.mesh_object_name.startswith('SwordM')),
        ('numatb', s.matl_data.read_matl, 'entries', None),
        ('numshexb', s.meshex_data.read_meshex, 'mesh_object_groups', lambda e: e.mesh_object_name == 'SwordM'),
    ]
    counts = {}
    # Compare canonical serializations after readback and removal of additions.
    # This covers original body geometry, material colors, and skeleton transforms.
    with tempfile.TemporaryDirectory(prefix='mgw-c06-') as temp:
        temp = Path(temp)
        for ext, reader, attr, predicate in formats:
            name = 'model.' + ext
            original = reader(str(stock / name))
            modified7 = reader(str(source / name))
            if ext == 'numatb':
                labels = {e.material_label for e in original.entries}
                added = [e for e in modified7.entries if e.material_label not in labels]
            else:
                require(not any(predicate(e) for e in getattr(original, attr)), f'Sword already in stock {ext}')
                added = [e for e in getattr(modified7, attr) if predicate(e)]
            require(bool(added), f'No sword additions found in {ext}')
            if ext == 'nusktb':
                require(len(added) == 1, 'Expected one SwordR bone')
                require(original.bones[added[0].parent_index].name == 'HaveR', 'SwordR parent mismatch')
            original.save(str(temp / ('base.' + ext)))
            original_count = len(getattr(original, attr))
            getattr(original, attr).extend(added)
            original.save(str(dest / name))
            readback = reader(str(dest / name))
            require(len(getattr(readback, attr)) == original_count + len(added), f'Addition count mismatch: {ext}')
            setattr(readback, attr, getattr(readback, attr)[:original_count])
            readback.save(str(temp / ('restored.' + ext)))
            require((temp / ('base.' + ext)).read_bytes() == (temp / ('restored.' + ext)).read_bytes(),
                    f'Original c06 body changed in {ext}')
            counts[ext] = len(added)
    # Only injected sword textures override stock c06 files. Fail on collisions.
    for texture in source.glob('*.nutexb'):
        if (stock / texture.name).exists():
            require(sha(stock / texture.name) == sha(texture), f'Would override c06 body texture: {texture.name}')
        shutil.copy2(texture, dest / texture.name)
    mesh = s.mesh_data.read_mesh(str(dest / 'model.numshb'))
    modl = s.modl_data.read_modl(str(dest / 'model.numdlb'))
    matl = s.matl_data.read_matl(str(dest / 'model.numatb'))
    skeleton = s.skel_data.read_skel(str(dest / 'model.nusktb'))
    mesh_keys = {(o.name, o.subindex) for o in mesh.objects}
    labels = {e.material_label for e in matl.entries}
    bones = {b.name for b in skeleton.bones}
    sword_entries = [e for e in modl.entries if e.mesh_object_name.startswith('SwordM')]
    require(len(sword_entries) == counts['numshb'] == 4, 'Expected four sword submeshes')
    for e in sword_entries:
        require((e.mesh_object_name, e.mesh_object_subindex) in mesh_keys, 'Missing sword mesh')
        require(e.material_label in labels, 'Missing sword material')
    for o in mesh.objects:
        if o.name.startswith('SwordM'):
            require(o.parent_bone_name in bones, 'Missing sword attachment bone')
    for e in matl.entries:
        if e.material_label in {v.material_label for v in sword_entries}:
            for texture in e.textures:
                name = texture.data + '.nutexb'
                # This exact engine-provided cubemap token is already present
                # in the shipped c07 materials; it is not a disk texture.
                require((dest / name).exists() or (stock / name).exists() or texture.data == '#replace_cubemap',
                        f'Missing sword texture {name}')
    return {'additions': counts, 'original_c06_body_preserved': True,
            'sword_mesh_material_bone_references_verified': True}


def main():
    before7 = {str(p.relative_to(OUTPUT)): sha(p) for p in OUTPUT.rglob('*') if p.is_file() and 'c07' in p.parts}
    record = {'motions': {fighter: copy_motions(fighter) for fighter in ['elight', 'gamewatch']},
              'gamewatch_model': inject_sword()}
    require(all(sha(OUTPUT / p) == h for p, h in before7.items()), 'c07 assets changed')
    record['c07_unchanged'] = True
    record['c06_files'] = {str(p.relative_to(OUTPUT)).replace('\\', '/'): sha(p)
                           for p in OUTPUT.rglob('*') if p.is_file() and 'c06' in p.parts}
    RECORD.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in record.items() if k != 'c06_files'}, indent=2))
    print(f'Validated {len(record["c06_files"])} c06 files; record: {RECORD}')


if __name__ == '__main__':
    main()
