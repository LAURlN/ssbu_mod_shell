"""Copy the selected user skins into the probes' sole c00 costume.

Inputs are treated as read-only. Model, article, effect and trail files retain
their source bytes and filenames; only the costume directory and fighter
namespace change. UI portraits are handled by build_probe_ui.py because their
embedded BNTX keys need a checked clone-name rewrite.
"""
from pathlib import Path
import hashlib
import zipfile


MYTHRA_ROOT = Path('skins_to_use/black_and_pink_mythra/mythra skin')
WATCH_ROOT = Path('skins_to_use/pink_g_w/Pink G&W')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def _copy_record(workspace, pack, source, destination, skin_name, records):
    if not source.is_file():
        raise FileNotFoundError(f'Missing {skin_name} input: {source}')
    source_data = source.read_bytes()
    target = pack / destination
    old = target.read_bytes() if target.is_file() else None
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source_data)
    if target.read_bytes() != source_data:
        raise IOError(f'Skin copy verification failed: {target}')
    records.append({
        'skin': skin_name,
        'source': source.relative_to(workspace).as_posix(),
        'destination': destination.as_posix(),
        'bytes': len(source_data),
        'source_sha256': sha(source_data),
        'output_sha256': sha(target.read_bytes()),
        'replaced_existing_file': old is not None,
        'previous_sha256': sha(old) if old is not None else None,
        'byte_identical_to_previous': old == source_data if old is not None else None,
    })


def _verify_gw_zip(workspace, skin_root):
    archive_path = workspace / 'skins_to_use/pink_g_w.zip'
    prefix = 'Pink G&W/'
    with zipfile.ZipFile(archive_path) as archive:
        zipped = {
            name[len(prefix):]: hashlib.sha256(archive.read(name)).hexdigest()
            for name in archive.namelist()
            if name.startswith(prefix) and not name.endswith('/')
        }
    extracted = {
        path.relative_to(skin_root).as_posix(): sha(path.read_bytes())
        for path in skin_root.rglob('*') if path.is_file()
    }
    if zipped != extracted:
        missing = sorted(set(zipped) - set(extracted))
        extra = sorted(set(extracted) - set(zipped))
        changed = sorted(path for path in set(zipped) & set(extracted)
                         if zipped[path] != extracted[path])
        raise ValueError(
            f'Pink G&W extracted folder differs from its ZIP: '
            f'missing={missing[:5]}, extra={extra[:5]}, changed={changed[:5]}'
        )
    return {'archive': archive_path.relative_to(workspace).as_posix(),
            'archive_sha256': sha(archive_path.read_bytes()),
            'extracted_files': len(extracted), 'extracted_hashes_match': True}


def import_model_and_effects(workspace: Path, pack: Path):
    records = []
    sources = {'black_and_pink_mythra': workspace / MYTHRA_ROOT}
    mythra = sources['black_and_pink_mythra']
    mythra_models = sorted((mythra / 'fighter/elight/model').rglob('*'))
    mythra_models = [path for path in mythra_models if path.is_file()]
    if len(mythra_models) != 23:
        raise ValueError(f'Expected 23 Mythra model textures; found {len(mythra_models)}')
    for source in mythra_models:
        relative = source.relative_to(mythra / 'fighter/elight/model')
        if 'c06' not in relative.parts:
            raise ValueError(f'Unexpected Mythra costume path: {source}')
        destination = Path('fighter/mgw_mythra/model') / Path(
            *('c00' if part == 'c06' else part for part in relative.parts)
        )
        _copy_record(workspace, pack, source, destination,
                     'black_and_pink_mythra', records)

    effects_root = mythra / 'effect/fighter/elight'
    effect_files = [effects_root / 'ef_elight.eff'] + sorted(
        (effects_root / 'trail').glob('tex_elight_sword*.nutexb')
    )
    if len(effect_files) != 6 or not all(path.is_file() for path in effect_files):
        raise ValueError('Mythra skin must contain its effect bank and all five sword trails')
    for source in effect_files:
        if source.name == 'ef_elight.eff':
            destination = Path('effect/fighter/mgw_mythra/ef_mgw_mythra.eff')
        else:
            destination = Path('effect/fighter/mgw_mythra/trail') / source.name
        _copy_record(workspace, pack, source, destination,
                     'black_and_pink_mythra', records)

    return {
        'skins': {
            'black_and_pink_mythra': {
                'source_directory': MYTHRA_ROOT.as_posix(),
                'source_costume': 'c06',
                'destination_character': 'mgw_mythra',
                'destination_costume': 'c00',
                'model_files': len(mythra_models),
                'effect_files': len(effect_files),
                'portraits': 'elight_only variants present in source, rewritten by build_probe_ui.py',
            },
        },
        'copied': records,
    }
