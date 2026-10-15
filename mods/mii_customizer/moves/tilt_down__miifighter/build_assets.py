#!/usr/bin/env python3
"""Build game assets for unit tilt_down__miifighter (MV-tilt_down__miifighter).

Mii Brawler's down tilt (donor attack_lw3) as an owned motion for Mii Gunner.

Outputs, all under workspace gamedata/mii_customizer/moves/tilt_down__miifighter/:
- package/fighter/miigunner/motion/body/c00/c01mcmiifighterattacklw3.nuanmb
    the donor clip c02attacklw3.nuanmb, copied under the owned name (bytes unchanged)
- reference/motion_list_vanilla_plus_owned.bin
    the vanilla Gunner motion_list.bin with ONE entry appended (kind mc_miifighter_attack_lw3),
    copied from the donor entry with kind / script / clip / sound / effect / expression hashes replaced.
    This is the list the coordinator's merged patch must reproduce, not a shipped file.
- manifest.json (sizes, sha256 of every input and output, the added entry's hashes)

Not written, on purpose: package/.../motion_list.bin, motion_list.motdiff and config.json.
The coordinator merges all units into one motion-list patch and one config.json.

Run from anywhere: paths are relative to this file. Uses only the Python standard library.
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import struct
import zlib

UNIT = 'tilt_down__miifighter'
OWNED_KIND = 'mc_miifighter_attack_lw3'
DONOR_KIND = 'attack_lw3'
DONOR_CLIP = 'c02attacklw3.nuanmb'
OWNED_CLIP = 'c01mcmiifighterattacklw3.nuanmb'

HERE = Path(__file__).resolve().parent
MOD_ROOT = HERE.parents[1]  # mods/mii_customizer
WORKSPACE = MOD_ROOT.parents[1]  # the folder that contains AGENTS.md, mods/, gamedata/

GUNNER_MLIST_SRC = WORKSPACE / 'gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin'
DONOR_MLIST_SRC = WORKSPACE / 'gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/motion_list.bin'
DONOR_CLIP_SRC = WORKSPACE / 'gamedata/mii_customizer/moves' / UNIT / 'extract/fighter/miifighter/motion/body/c00' / DONOR_CLIP

OUT_DIR = WORKSPACE / 'gamedata/mii_customizer/moves' / UNIT
PACKAGE_BODY_DIR = OUT_DIR / 'package/fighter/miigunner/motion/body/c00'
REFERENCE_MLIST = OUT_DIR / 'reference/motion_list_vanilla_plus_owned.bin'
MANIFEST_PATH = OUT_DIR / 'manifest.json'


def hash40(name: str) -> int:
    b = name.encode('utf-8')
    return (len(b) << 32) | (zlib.crc32(b) & 0xFFFFFFFF)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_mlist(data: bytes):
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    offset = 24
    entries = []
    for i in range(count):
        start = offset
        kind, game, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        raw = data[start:end]
        offset = end
        entries.append({
            'index': i, 'kind': kind, 'game': game, 'flags': flags, 'blend': blend,
            'n_anims': n_anims, 'anims': anims, 'size': size, 'raw': raw,
            'tail_offset': tail - start,
        })
    if offset != len(data):
        raise ValueError(f'motion list has {len(data) - offset} trailing bytes')
    return magic, motion_path, entries


def create_entry(donor_entry: dict, owned_kind: str, clip_name: str) -> bytes:
    stem = owned_kind.replace('_', '')
    raw = bytearray(donor_entry['raw'])
    struct.pack_into('<QQ', raw, 0, hash40(owned_kind), hash40('game_' + stem))
    struct.pack_into('<Q', raw, 24, hash40(clip_name))
    tail = donor_entry['tail_offset']
    struct.pack_into('<QQQ', raw, tail,
                     hash40('expression_' + stem),
                     hash40('sound_' + stem),
                     hash40('effect_' + stem))
    return bytes(raw)


def main():
    for p in (GUNNER_MLIST_SRC, DONOR_MLIST_SRC, DONOR_CLIP_SRC):
        if not p.is_file():
            raise SystemExit(f'missing input: {p.relative_to(WORKSPACE).as_posix()}')

    gunner_bytes = GUNNER_MLIST_SRC.read_bytes()
    donor_bytes = DONOR_MLIST_SRC.read_bytes()
    magic_g, path_g, entries_g = parse_mlist(gunner_bytes)
    _, _, entries_d = parse_mlist(donor_bytes)

    donor_hits = [e for e in entries_d if e['kind'] == hash40(DONOR_KIND)]
    if len(donor_hits) != 1:
        raise SystemExit(f'expected exactly one donor entry for {DONOR_KIND}, found {len(donor_hits)}')
    donor_entry = donor_hits[0]
    if donor_entry['n_anims'] != 1 or donor_entry['anims'][0] != hash40(DONOR_CLIP):
        raise SystemExit('donor entry does not reference the expected clip')

    if any(e['kind'] == hash40(OWNED_KIND) for e in entries_g):
        raise SystemExit(f'vanilla Gunner list already has {OWNED_KIND}')

    added = create_entry(donor_entry, OWNED_KIND, OWNED_CLIP)
    reference = struct.pack('<QQQ', magic_g, path_g, len(entries_g) + 1) + b''.join(e['raw'] for e in entries_g) + added
    REFERENCE_MLIST.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE_MLIST.write_bytes(reference)

    PACKAGE_BODY_DIR.mkdir(parents=True, exist_ok=True)
    dest_clip = PACKAGE_BODY_DIR / OWNED_CLIP
    shutil.copyfile(DONOR_CLIP_SRC, dest_clip)

    # Parse-back of what was written
    magic_r, _, entries_r = parse_mlist(REFERENCE_MLIST.read_bytes())
    assert len(entries_r) == len(entries_g) + 1
    assert entries_r[-1]['kind'] == hash40(OWNED_KIND)

    stem = OWNED_KIND.replace('_', '')
    files = {}
    for p in sorted(OUT_DIR.rglob('*')):
        if p.is_file() and p.name != 'manifest.json':
            rel = p.relative_to(OUT_DIR).as_posix()
            files[rel] = {'size': p.stat().st_size, 'sha256': sha256_file(p)}

    manifest = {
        'unit': UNIT,
        'task_id': 'MV-' + UNIT,
        'package_root': 'package',
        'files': {k: v for k, v in files.items() if k.startswith('package/')},
        'reference': {k: v for k, v in files.items() if k.startswith('reference/')},
        'inputs': {
            'gunner_motion_list': {'path': GUNNER_MLIST_SRC.relative_to(WORKSPACE).as_posix(),
                                   'size': len(gunner_bytes), 'sha256': sha256_file(GUNNER_MLIST_SRC),
                                   'entries': len(entries_g)},
            'donor_motion_list': {'path': DONOR_MLIST_SRC.relative_to(WORKSPACE).as_posix(),
                                  'size': len(donor_bytes), 'sha256': sha256_file(DONOR_MLIST_SRC),
                                  'entries': len(entries_d), 'donor_index': donor_entry['index']},
            'donor_clip': {'path': DONOR_CLIP_SRC.relative_to(WORKSPACE).as_posix(),
                           'size': DONOR_CLIP_SRC.stat().st_size, 'sha256': sha256_file(DONOR_CLIP_SRC)},
        },
        'added_motion': {
            'kind': OWNED_KIND,
            'kind_hash': f"0x{hash40(OWNED_KIND):010x}",
            'game_script': 'game_' + stem,
            'game_hash': f"0x{hash40('game_' + stem):010x}",
            'expression_script': 'expression_' + stem,
            'expression_hash': f"0x{hash40('expression_' + stem):010x}",
            'sound_script': 'sound_' + stem,
            'sound_hash': f"0x{hash40('sound_' + stem):010x}",
            'effect_script': 'effect_' + stem,
            'effect_hash': f"0x{hash40('effect_' + stem):010x}",
            'clip': OWNED_CLIP,
            'clip_hash': f"0x{hash40(OWNED_CLIP):010x}",
            'flags': f"0x{donor_entry['flags']:04x}",
            'blend': donor_entry['blend'],
            'cancel_frame': struct.unpack_from('<H', donor_entry['raw'], donor_entry['tail_offset'] + 24 + 2)[0],
            'size': donor_entry['size'],
        },
        'reference_entry_count': len(entries_r),
        'reference_magic': f"0x{magic_r:016x}",
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f'Built {UNIT}: package files={len(manifest["files"])}, reference entries={len(entries_r)}')
    print(f'Manifest: {MANIFEST_PATH.relative_to(WORKSPACE).as_posix()}')


if __name__ == '__main__':
    main()
