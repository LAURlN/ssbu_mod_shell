"""Prepare independently editable inputs. This does NOT build a playable mod.

Only read the user's dump. No links, donor fallback aliases, or runtime patches.
Every materialized file is checked against a recorded source hash. Existing
edited output is preserved and reported as a conflict, never overwritten.
"""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import tempfile
import time
import zlib

ROOT = Path(__file__).resolve().parents[1]
NAMES = json.loads((ROOT / 'project.json').read_text())['namespaces']
TOKEN = re.compile(r'(?<![a-zA-Z0-9])(?:' + '|'.join(sorted(NAMES, key=len, reverse=True)) + ')')


def h40(text):
    raw = text.encode('utf8')
    return len(raw) << 32 | zlib.crc32(raw)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def owned_path(path):
    # Keep local mesh/material/texture/animation names together. Their parent
    # namespace is private; changing their leaf names breaks internal references.
    if path.startswith('fighter/') and ('/model/' in path or '/motion/' in path):
        parent, leaf = path.rsplit('/', 1)
        mapped = TOKEN.sub(lambda m: NAMES[m.group()], parent)
        if mapped != parent:
            return mapped + '/' + leaf
    return TOKEN.sub(lambda m: NAMES[m.group()], path)


def relevant(path):
    return (TOKEN.search(path) is not None and path.startswith((
        'fighter/', 'camera/fighter/', 'effect/fighter/', 'sound/',
        'ui/replace/chara/', 'ui/replace_patch/chara/', 'finalsmash/',
        'prebuilt/nro/')))


def safe_relative(path):
    p = Path(path)
    if p.is_absolute() or '..' in p.parts or ':' in path or '\\' in path:
        raise ValueError('Unsafe archive path: ' + path)
    return p


def materialize(source, destination, output):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if destination.is_symlink() or destination.stat().st_nlink > 1:
            raise ValueError('Output must be an independent regular file: ' + str(destination))
        if destination.read_bytes() != output:
            return 'conflict_preserved'
    else:
        with destination.open('xb') as f:
            f.write(output)
    if source.samefile(destination):
        raise ValueError('Output aliases source: ' + str(source))
    if destination.read_bytes() != output:
        raise ValueError('Readback mismatch: ' + str(destination))
    return 'verified'


def motion_info(data):
    if len(data) < 24 or struct.unpack_from('<Q', data)[0] != h40('motion'):
        raise ValueError('Invalid motion-list header')
    directory, count = struct.unpack_from('<QQ', data, 8)
    at, animations = 24, set()
    for _ in range(count):
        n = data[at + 19]
        if n > 3:
            raise ValueError('Unsupported motion entry')
        scripts_size = struct.unpack_from('<I', data, at + 20)[0]
        at += 24
        animations.update(struct.unpack_from('<Q', data, at + i * 8)[0] for i in range(n))
        at = (at + n * 9 + 3) & ~3
        at += scripts_size
    if at != len(data):
        raise ValueError('Motion parser did not consume file')
    return directory, animations - {0}


def write_json(name, value):
    (ROOT / 'reports').mkdir(exist_ok=True)
    destination = ROOT / 'reports' / name
    # Keep the last complete report if the disk fills during a new write.
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf8', dir=destination.parent,
                                     prefix=name + '.', suffix='.tmp', delete=False) as f:
        f.write(json.dumps(value, indent=2) + '\n')
        temporary = f.name
    # Windows readers/indexers may briefly hold a handle without delete sharing.
    for attempt in range(20):
        try:
            os.replace(temporary, destination)
            break
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.1)


def prepare(export, index):
    indexed = {line.split('\t')[0].replace('prebuilt:/', 'prebuilt/')
               for line in index.read_text(encoding='utf8').splitlines() if line}
    planned = {p for p in indexed if relevant(p)}
    # Include dumped files absent from the third-party index too.
    for top in ('fighter', 'camera', 'effect', 'sound', 'ui', 'finalsmash', 'prebuilt'):
        for file in (export / top).rglob('*'):
            if file.is_file():
                relative = file.relative_to(export).as_posix()
                if relevant(relative):
                    planned.add(relative)
    directories = {h40(str(Path(p).parent).replace('\\', '/')):
                   str(Path(p).parent).replace('\\', '/') for p in planned}
    missing, files, motion_rows, unresolved, conflicts = [], [], [], [], []
    required_bytes = sum((export / p).stat().st_size for p in planned if (export / p).is_file()
                         and not (ROOT / 'editable' / owned_path(p)).exists())
    if required_bytes + 128 * 1024**2 > shutil.disk_usage(ROOT).free:
        raise RuntimeError('Insufficient free space for independent copies')
    for relative in sorted(planned):
        source = export / safe_relative(relative)
        if not source.is_file():
            missing.append(relative)
            continue
        data = source.read_bytes()
        output, changes = data, []
        destination = owned_path(relative)
        if source.name == 'motion_list.bin':
            directory, animations = motion_info(data)
            old = directories.get(directory)
            if directory and old is None:
                unresolved.append({'file': relative, 'directory_hash': hex(directory)})
            elif old:
                new = owned_path(old)
                output = data[:8] + struct.pack('<Q', h40(new)) + data[16:]
                changes.append({'offset': 8, 'source_directory': old, 'clone_directory': new})
                motion_rows.append({'file': destination, 'directory': new,
                                    'animations': sorted(animations)})
        status = materialize(source, ROOT / 'editable' / destination, output)
        if status != 'verified':
            conflicts.append(destination)
        files.append({'source': relative, 'destination': destination, 'bytes': len(data),
                      'source_sha256': digest(data), 'output_sha256': digest(output),
                      'changes': changes, 'status': status})
    motion_missing = []
    for row in motion_rows:
        available = {h40(p.name) for p in (ROOT / 'editable' / row['directory']).glob('*.nuanmb')}
        absent = set(row['animations']) - available
        if absent:
            motion_missing.append({'file': row['file'], 'directory': row['directory'],
                                   'missing_animation_hashes': [hex(h) for h in sorted(absent)]})
    summary = {'playable': False, 'runtime_implemented': False,
               'report_scope': 'Asset preparation only; runtime_implemented means a playable runtime',
               'runtime_evidence': 'reports/loader-build.json',
               'index_sha256': digest(index.read_bytes()),
               'index_scope': 'Named character resources; not proof of full dependency closure',
               'planned_files': len(planned), 'materialized_files': len(files),
               'bytes': sum(f['bytes'] for f in files), 'missing_files': len(missing),
               'missing_groups': dict(Counter('/'.join(p.split('/')[:3]) for p in missing)),
               'motion_lists_retargeted': len(motion_rows),
               'unresolved_motion_directories': unresolved, 'missing_motion_animations': motion_missing,
               'preserved_edit_conflicts': conflicts,
               'remaining': ['Runtime registration of one transforming pair',
                             'Private character-native relocation and import binding (NRO loading already tested)',
                             'Character-specific routines in main executable',
                             'Effect, sound, parameter, UI and script internal identifier routing',
                             'Shared parameter/database row extraction and dependency closure',
                             'On-console coexistence and behavior validation']}
    write_json('assets.json', {'summary': summary, 'files': files})
    write_json('missing.json', missing)
    (ROOT / 'reports' / 'missing-paths.txt').write_text('\n'.join(missing) + '\n', encoding='utf8')
    write_json('summary.json', summary)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--export', type=Path, default=ROOT.parent / 'export')
    parser.add_argument('--index', type=Path, default=ROOT.parent / 'mod_files/mgw_standalone/vendor/clone_pack_workbench/arc_index/arc_files.tsv')
    args = parser.parse_args()
    prepare(args.export.resolve(), args.index.resolve())
