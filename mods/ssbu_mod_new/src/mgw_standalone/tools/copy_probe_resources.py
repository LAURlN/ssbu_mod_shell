"""Materialize donor resources and retarget motion-list directory hashes.

Only reads the user's export tree. Unavailable inputs remain explicitly listed;
the caller must not report a completely independent asset pack until resolved.
"""
from pathlib import Path
import hashlib
import struct
import zlib

PAIRS = (('elight', 'mgw_mythra'), ('eflame', 'mgw_pyra'))


def hash40(text):
    data = text.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def validate_motion_references(pack, manifest):
    """Check that every retargeted animation reference reaches a copied clip.

    Entry layout follows the pinned engine's motion_list.rs reader. Animation
    hashes include the .nuanmb extension. This also verifies parsing consumes
    the complete file, without rewriting any motion entry.
    """
    audit = []
    for item in manifest['copied']:
        if not item['changes']:
            continue
        data = (pack / item['destination']).read_bytes()
        count = struct.unpack_from('<Q', data, 16)[0]
        at, animations = 24, set()
        for _ in range(count):
            num_animations = data[at+19]
            scripts_bytes = struct.unpack_from('<I', data, at+20)[0]
            assert num_animations <= 3, item['destination']
            at += 24
            animations.update(struct.unpack_from('<Q', data, at+i*8)[0] for i in range(num_animations))
            at = (at + num_animations*9 + 3) & ~3
            at += scripts_bytes
        assert at == len(data), item['destination']
        folder = pack / item['changes'][0]['destination_directory']
        existing = {hash40(path.name) for path in folder.glob('*.nuanmb')}
        missing = animations - existing - {0}
        assert not missing, (item['destination'], [hex(value) for value in missing])
        audit.append(dict(path=item['destination'], unique_animations=len(animations), missing=[]))
    return audit


def copy_resources(export, pack, config):
    planned = [(src, dst) for src, targets in config['share-to-vanilla'].items()
               for dst in targets if any(clone in dst for _, clone in PAIRS)]
    # These live behind the donor's cmn directory link in a model-only pack.
    for base, clone in PAIRS:
        for branch in ('param', 'ai'):
            for source in sorted((export / f'fighter/{base}/{branch}').rglob('*')):
                if source.is_file():
                    src = source.relative_to(export).as_posix()
                    planned.append((src, src.replace(f'fighter/{base}/', f'fighter/{clone}/', 1)))
    # Both Mythra sword lists reference Pyra's esword folder in the native
    # dump. Several open/close clips differ from Mythra's local counterparts.
    # Keep the exact referenced clips in a separate owned directory.
    sword_source = 'fighter/eflame/motion/esword/c00'
    sword_target = 'fighter/mgw_mythra/motion/eflame_esword/c00'
    sword_names = ('d01specials1', 'd01specials2', 'd01specialsmovel', 'd01specialsmover',
                   'z00close', 'z00open', 'z00toclose', 'z00toopen')
    planned += [(f'{sword_source}/{name}.nuanmb', f'{sword_target}/{name}.nuanmb') for name in sword_names]
    # A model.numdlb makes the vendor generator regard the entire model folder
    # as owned. Defer a partial source model as a unit, otherwise a mid-extraction
    # build could suppress aliases for its still-missing mesh or textures.
    incomplete_models = {str(Path(src).parent) for src, _ in planned
                         if '/model/' in src and not (export / src).is_file()}
    copied, missing = [], []
    for src, dst in sorted(set(planned)):
        source = export / src
        if not source.is_file() or str(Path(src).parent) in incomplete_models:
            missing.append(dict(source=src, destination=dst,
                                reason='incomplete model directory' if source.is_file() else 'not dumped'))
            continue
        data = source.read_bytes()
        output = data
        changes = []
        if source.name == 'motion_list.bin':
            assert len(data) >= 24 and struct.unpack_from('<Q', data)[0] == hash40('motion'), src
            old_hash = struct.unpack_from('<Q', data, 8)[0]
            # A zero path is a native special case. All nonzero path values
            # must identify the actual donor directory before retargeting.
            if old_hash:
                old_directory = str(Path(src).parent).replace('\\', '/')
                new_directory = str(Path(dst).parent).replace('\\', '/')
                if src in ('fighter/elight/motion/esword/c00/motion_list.bin',
                           'fighter/elight/motion/winsword/c00/motion_list.bin'):
                    old_directory, new_directory = sword_source, sword_target
                elif src == 'fighter/eflame/motion/winsword/c00/motion_list.bin':
                    old_directory = 'fighter/eflame/motion/esword/c00'
                    new_directory = 'fighter/mgw_pyra/motion/esword/c00'
                assert old_hash == hash40(old_directory), (src, hex(old_hash), old_directory)
                output = data[:8] + struct.pack('<Q', hash40(new_directory)) + data[16:]
                changes.append(dict(offset=8, source_directory=old_directory, destination_directory=new_directory))
                assert output[:8] == data[:8] and output[16:] == data[16:]
        destination = pack / dst
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_bytes() != output:
            raise ValueError(f'Refusing to overwrite a different pack resource: {dst}')
        destination.write_bytes(output)
        copied.append(dict(source=src, destination=dst, bytes=len(output),
                           source_sha256=hashlib.sha256(data).hexdigest(),
                           sha256=hashlib.sha256(output).hexdigest(), changes=changes))
    return dict(copied=copied, missing=missing, complete=not missing)
