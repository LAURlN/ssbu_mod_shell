#!/usr/bin/env python3
"""Build game assets for P16-FTILT-MOVE: Mii Brawler forward tilt on Mii Gunner.

Outputs:
- motion_list.motdiff: an ARCropolis motion-list patch adding 3 owned motions
    (mc_attacks3_s, mc_attacks3_hi, mc_attacks3_lw). A patch, not a motion_list.bin: the
    user's other mod ships its own Gunner motion_list.bin and ARCropolis keeps only one
    file per path, but applies patches on top of whichever list is loaded (session 4).
    The rebuilt full list is kept beside the package as the reference the patch must give.
- 3 owned animation clips copied from Brawler donor clips:
    c01mcattacks3s.nuanmb, c01mcattacks3hi.nuanmb, c01mcattacks3lw.nuanmb
- config.json declaring new clips under fighter/miigunner/c00
- manifest.json in tools/move-package/ with hashes and sizes
Package destination:
    <workspace>/gamedata/mii_customizer/P16-FTILT-MOVE/package/mii_customizer_moves/
"""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

MOD_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = MOD_ROOT.parent.parent

GUNNER_MLIST_SRC = WORKSPACE / 'gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin'
BRAWLER_MLIST_SRC = WORKSPACE / 'gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/motion_list.bin'
DONOR_CLIPS_DIR = WORKSPACE / 'gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miifighter/motion/body/c00'

PACKAGE_DIR = WORKSPACE / 'gamedata/mii_customizer/P16-FTILT-MOVE/package/mii_customizer_moves'
DEST_BODY_DIR = PACKAGE_DIR / 'fighter/miigunner/motion/body/c00'
MANIFEST_PATH = MOD_ROOT / 'tools/move-package/manifest.json'
# Not shipped: the full list the patch must reproduce from the vanilla list.
REFERENCE_MLIST = WORKSPACE / 'gamedata/mii_customizer/P16-FTILT-MOVE/reference/motion_list_vanilla_plus_owned.bin'
# tools/move-package/motdiff, built with: cargo build --release --target-dir builds/.cache/motdiff-target
MOTDIFF_EXE = MOD_ROOT / 'builds/.cache/motdiff-target/release/motdiff.exe'

def hash40(string: str) -> int:
    return (len(string) << 32) | (zlib.crc32(string.encode('utf-8')) & 0xFFFFFFFF)

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()

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
            'index': i,
            'kind': kind,
            'game': game,
            'flags': flags,
            'blend': blend,
            'n_anims': n_anims,
            'anims': anims,
            'size': size,
            'raw': raw,
            'tail_offset': tail - start,
        })
    return magic, motion_path, entries

def create_entry(donor_entry, owned_name, clip_name):
    raw = bytearray(donor_entry['raw'])
    struct.pack_into('<QQ', raw, 0, hash40(owned_name), hash40('game_' + owned_name.replace('_', '')))
    struct.pack_into('<Q', raw, 24, hash40(clip_name))
    tail = donor_entry['tail_offset']
    struct.pack_into('<QQQ', raw, tail,
                     hash40('expression_' + owned_name.replace('_', '')),
                     hash40('sound_' + owned_name.replace('_', '')),
                     hash40('effect_' + owned_name.replace('_', '')))
    return bytes(raw)

def main():
    print(f"Building P16 assets into {PACKAGE_DIR}")
    assert GUNNER_MLIST_SRC.is_file(), f"Missing {GUNNER_MLIST_SRC}"
    assert BRAWLER_MLIST_SRC.is_file(), f"Missing {BRAWLER_MLIST_SRC}"

    DEST_BODY_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Rebuild motion_list.bin
    data_g = GUNNER_MLIST_SRC.read_bytes()
    magic_g, path_g, entries_g = parse_mlist(data_g)

    data_b = BRAWLER_MLIST_SRC.read_bytes()
    magic_b, path_b, entries_b = parse_mlist(data_b)
    donor_by_kind = {e['kind']: e for e in entries_b}

    moves = [
        ('attack_s3_s', 'mc_attacks3_s', 'c01mcattacks3s.nuanmb', 'c01attacks3s.nuanmb'),
        ('attack_s3_hi', 'mc_attacks3_hi', 'c01mcattacks3hi.nuanmb', 'c01attacks3hi.nuanmb'),
        ('attack_s3_lw', 'mc_attacks3_lw', 'c01mcattacks3lw.nuanmb', 'c01attacks3lw.nuanmb'),
    ]

    added_entries = []
    for donor_kind_name, owned_name, clip_name, donor_clip_name in moves:
        donor_entry = donor_by_kind[hash40(donor_kind_name)]
        added_entries.append(create_entry(donor_entry, owned_name, clip_name))

        # Copy clip
        donor_clip_path = DONOR_CLIPS_DIR / donor_clip_name
        dest_clip_path = DEST_BODY_DIR / clip_name
        assert donor_clip_path.is_file(), f"Missing donor clip {donor_clip_path}"
        shutil.copy2(donor_clip_path, dest_clip_path)

    all_raw = [e['raw'] for e in entries_g] + added_entries
    new_count = len(all_raw)
    header = struct.pack('<QQQ', magic_g, path_g, new_count)
    rebuilt_mlist_data = header + b''.join(all_raw)

    REFERENCE_MLIST.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE_MLIST.write_bytes(rebuilt_mlist_data)
    stale = DEST_BODY_DIR / 'motion_list.bin'
    if stale.exists():
        stale.unlink()
    assert MOTDIFF_EXE.is_file(), f"Build tools/move-package/motdiff first: {MOTDIFF_EXE}"
    patch_path = DEST_BODY_DIR / 'motion_list.motdiff'
    subprocess.run([str(MOTDIFF_EXE), 'diff', str(GUNNER_MLIST_SRC), str(REFERENCE_MLIST), str(patch_path)], check=True)
    # The patch applied to the vanilla list must give the reference list back, byte for byte.
    roundtrip = REFERENCE_MLIST.with_name('roundtrip.bin')
    subprocess.run([str(MOTDIFF_EXE), 'patch', str(GUNNER_MLIST_SRC), str(patch_path), str(roundtrip)], check=True)
    assert roundtrip.read_bytes() == rebuilt_mlist_data, 'motdiff does not reproduce the rebuilt list'
    roundtrip.unlink()

    # Verify parse
    magic_chk, path_chk, entries_chk = parse_mlist(rebuilt_mlist_data)
    assert magic_chk == magic_g
    assert path_chk == path_g
    assert len(entries_chk) == len(entries_g) + 3

    # 2. Write config.json
    config = {
        "new-dir-infos": [],
        "new-dir-infos-base": {},
        "new-dir-files": {
            "fighter/miigunner/c00": [
                "fighter/miigunner/motion/body/c00/c01mcattacks3hi.nuanmb",
                "fighter/miigunner/motion/body/c00/c01mcattacks3lw.nuanmb",
                "fighter/miigunner/motion/body/c00/c01mcattacks3s.nuanmb"
            ]
        },
        "share-to-vanilla": {},
        "share-to-added": {}
    }
    config_path = PACKAGE_DIR / 'config.json'
    config_path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')

    # 3. Build manifest
    manifest_files = {}
    for p in sorted(PACKAGE_DIR.rglob('*')):
        if p.is_file():
            rel = p.relative_to(PACKAGE_DIR).as_posix()
            manifest_files[rel] = {
                'size': p.stat().st_size,
                'sha256': sha256_file(p),
            }

    manifest = {
        'package_name': 'mii_customizer_moves',
        'files': manifest_files,
        'added_motions': {
            'mc_attacks3_s': {
                'kind_hash': f"0x{hash40('mc_attacks3_s'):010x}",
                'game_script': f"0x{hash40('game_mcattacks3s'):010x}",
                'clip': 'c01mcattacks3s.nuanmb',
                'clip_hash': f"0x{hash40('c01mcattacks3s.nuanmb'):010x}",
            },
            'mc_attacks3_hi': {
                'kind_hash': f"0x{hash40('mc_attacks3_hi'):010x}",
                'game_script': f"0x{hash40('game_mcattacks3hi'):010x}",
                'clip': 'c01mcattacks3hi.nuanmb',
                'clip_hash': f"0x{hash40('c01mcattacks3hi.nuanmb'):010x}",
            },
            'mc_attacks3_lw': {
                'kind_hash': f"0x{hash40('mc_attacks3_lw'):010x}",
                'game_script': f"0x{hash40('game_mcattacks3lw'):010x}",
                'clip': 'c01mcattacks3lw.nuanmb',
                'clip_hash': f"0x{hash40('c01mcattacks3lw.nuanmb'):010x}",
            },
        }
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f"Generated manifest: {MANIFEST_PATH}")
    print(f"Package successfully built: {len(manifest_files)} files staged.")

if __name__ == '__main__':
    main()
