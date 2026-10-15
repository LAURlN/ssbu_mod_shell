#!/usr/bin/env python3
"""Build game assets for MV-tilt_up__miifighter: Mii Brawler up tilt on Mii Gunner.

Outputs into workspace gamedata/mii_customizer/moves/tilt_up__miifighter/:
- package/fighter/miigunner/motion/body/c00/c01mcmiifighterattackhi3.nuanmb
- reference/motion_list_vanilla_plus_owned.bin (vanilla Gunner list + 1 appended owned entry)
- manifest.json (file sizes, hashes, motion metadata)
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

OUT_BASE = WORKSPACE / 'gamedata/mii_customizer/moves/tilt_up__miifighter'
PACKAGE_DIR = OUT_BASE / 'package'
DEST_BODY_DIR = PACKAGE_DIR / 'fighter/miigunner/motion/body/c00'
REFERENCE_MLIST = OUT_BASE / 'reference/motion_list_vanilla_plus_owned.bin'
MANIFEST_PATH = OUT_BASE / 'manifest.json'

DONOR_CLIP_EXTRACTED = OUT_BASE / 'extracted/fighter/miifighter/motion/body/c00/c02attackhi3.nuanmb'
DATA_ARC = WORKSPACE / 'gamedata/ssbu-13.0.4/data.arc'
ARC_EXTRACT = WORKSPACE / 'tools/arc-extract/target/release/arc-extract.exe'

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

def create_entry(donor_entry, owned_name: str, clip_name: str):
    raw = bytearray(donor_entry['raw'])
    struct.pack_into('<QQ', raw, 0, hash40(owned_name), hash40('game_' + owned_name.replace('_', '')))
    struct.pack_into('<Q', raw, 24, hash40(clip_name))
    tail = donor_entry['tail_offset']
    struct.pack_into('<QQQ', raw, tail,
                     hash40('expression_' + owned_name.replace('_', '')),
                     hash40('sound_' + owned_name.replace('_', '')),
                     hash40('effect_' + owned_name.replace('_', '')))
    return bytes(raw)

def ensure_donor_clip() -> Path:
    if DONOR_CLIP_EXTRACTED.is_file():
        return DONOR_CLIP_EXTRACTED
    assert ARC_EXTRACT.is_file(), f"arc-extract executable missing: {ARC_EXTRACT}"
    assert DATA_ARC.is_file(), f"data.arc missing: {DATA_ARC}"
    out_dir = OUT_BASE / 'extracted'
    cmd = [
        str(ARC_EXTRACT),
        '--arc', str(DATA_ARC),
        '--out', str(out_dir),
        'fighter/miifighter/motion/body/c00/c02attackhi3.nuanmb'
    ]
    subprocess.run(cmd, check=True)
    assert DONOR_CLIP_EXTRACTED.is_file(), f"Extraction failed to create {DONOR_CLIP_EXTRACTED}"
    return DONOR_CLIP_EXTRACTED

def main():
    print(f"Building MV-tilt_up__miifighter assets into {OUT_BASE}")
    assert GUNNER_MLIST_SRC.is_file(), f"Missing {GUNNER_MLIST_SRC}"
    assert BRAWLER_MLIST_SRC.is_file(), f"Missing {BRAWLER_MLIST_SRC}"

    DEST_BODY_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_MLIST.parent.mkdir(parents=True, exist_ok=True)

    # 1. Parse lists
    data_g = GUNNER_MLIST_SRC.read_bytes()
    magic_g, path_g, entries_g = parse_mlist(data_g)

    data_b = BRAWLER_MLIST_SRC.read_bytes()
    magic_b, path_b, entries_b = parse_mlist(data_b)
    donor_entry = [e for e in entries_b if e['kind'] == hash40('attack_hi3')][0]

    owned_name = 'mc_miifighter_attack_hi3'
    owned_clip_name = 'c01mcmiifighterattackhi3.nuanmb'

    # Copy clip
    donor_clip = ensure_donor_clip()
    dest_clip = DEST_BODY_DIR / owned_clip_name
    shutil.copy2(donor_clip, dest_clip)
    print(f"Copied owned clip to {dest_clip}")

    # Build reference motion_list_vanilla_plus_owned.bin
    added_entry = create_entry(donor_entry, owned_name, owned_clip_name)
    all_raw = [e['raw'] for e in entries_g] + [added_entry]
    new_count = len(all_raw)
    header = struct.pack('<QQQ', magic_g, path_g, new_count)
    rebuilt_mlist_data = header + b''.join(all_raw)
    REFERENCE_MLIST.write_bytes(rebuilt_mlist_data)
    print(f"Wrote reference list {REFERENCE_MLIST} ({len(rebuilt_mlist_data)} bytes, {new_count} entries)")

    # 2. Build manifest
    manifest_pkg_files = {}
    for p in sorted(PACKAGE_DIR.rglob('*')):
        if p.is_file():
            rel = p.relative_to(PACKAGE_DIR).as_posix()
            manifest_pkg_files[rel] = {
                'size': p.stat().st_size,
                'sha256': sha256_file(p),
            }

    tail = donor_entry['tail_offset']
    cancel_frame = struct.unpack_from('<H', added_entry, tail + 26)[0]

    manifest = {
        'unit': 'tilt_up__miifighter',
        'entry': 'tilt_up',
        'donor': 'miifighter',
        'package_files': manifest_pkg_files,
        'reference_list': {
            'path': 'reference/motion_list_vanilla_plus_owned.bin',
            'size': REFERENCE_MLIST.stat().st_size,
            'sha256': sha256_file(REFERENCE_MLIST),
            'entry_count': new_count,
        },
        'added_motions': {
            owned_name: {
                'kind_hash': f"0x{hash40(owned_name):010x}",
                'game_script': 'game_mcmiifighterattackhi3',
                'game_script_hash': f"0x{hash40('game_mcmiifighterattackhi3'):010x}",
                'expression_script': 'expression_mcmiifighterattackhi3',
                'expression_script_hash': f"0x{hash40('expression_mcmiifighterattackhi3'):010x}",
                'sound_script': 'sound_mcmiifighterattackhi3',
                'sound_script_hash': f"0x{hash40('sound_mcmiifighterattackhi3'):010x}",
                'effect_script': 'effect_mcmiifighterattackhi3',
                'effect_script_hash': f"0x{hash40('effect_mcmiifighterattackhi3'):010x}",
                'clip': owned_clip_name,
                'clip_hash': f"0x{hash40(owned_clip_name):010x}",
                'flags': f"0x{donor_entry['flags']:04x}",
                'cancel_frame': cancel_frame,
            }
        }
    }

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f"Generated manifest: {MANIFEST_PATH}")
    print(f"Build complete.")

if __name__ == '__main__':
    main()
