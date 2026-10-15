#!/usr/bin/env python3
"""Build merged motion_list.motdiff for 0.10.0-moves: all owned motions.

Owns motions from:
- P16-FTILT-MOVE: mc_attacks3_s, mc_attacks3_hi, mc_attacks3_lw (Brawler forward tilt)
- tilt_up__miifighter: mc_miifighter_attack_hi3 (Brawler up tilt)
- tilt_down__miifighter: mc_miifighter_attack_lw3 (Brawler down tilt)
- smash_up__fox: mc_fox_attack_hi4, mc_fox_attack_hi4_hold (Fox up smash)

Outputs into builds/0.10.0-menu/mii_customizer_moves/:
- motion_list.motdiff (patch from vanilla to vanilla+all owned)
- config.json with all new clips
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
FOX_MLIST_SRC = WORKSPACE / 'gamedata/mii_customizer/moves/smash_up__fox/extracted/fighter/fox/motion/body/c00/motion_list.bin'

PACKAGE_DIR = MOD_ROOT / 'builds/0.10.0-menu/mii_customizer_moves'
DEST_BODY_DIR = PACKAGE_DIR / 'fighter/miigunner/motion/body/c00'
MANIFEST_PATH = MOD_ROOT / 'builds/0.10.0-menu/MANIFEST.json'
REFERENCE_MLIST = MOD_ROOT / 'builds/0.10.0-menu/reference_motion_list.bin'
MOTDIFF_EXE = MOD_ROOT / 'builds/.cache/motdiff-target/release/motdiff.exe'

# Donor clips for P16 and session 5 units
P16_CLIPS_DIR = WORKSPACE / 'gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miifighter/motion/body/c00'
TILT_CLIPS_DIR = WORKSPACE / 'gamedata/mii_customizer/moves'

# Fox clips from smash_up__fox extraction
FOX_CLIPS_DIR = WORKSPACE / 'gamedata/mii_customizer/moves/smash_up__fox/extracted/fighter/fox/motion/body/c00'

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

def create_entry(donor_entry, owned_name, clip_name, expr_name, snd_name, eff_name):
    raw = bytearray(donor_entry['raw'])
    struct.pack_into('<QQ', raw, 0, hash40(owned_name), hash40('game_' + owned_name.replace('_', '')))
    struct.pack_into('<Q', raw, 24, hash40(clip_name))
    tail = donor_entry['tail_offset']
    struct.pack_into('<QQQ', raw, tail,
                     hash40(expr_name),
                     hash40(snd_name),
                     hash40(eff_name))
    return bytes(raw)

def main():
    print(f"Building merged 0.10.0 assets into {PACKAGE_DIR}")
    assert GUNNER_MLIST_SRC.is_file(), f"Missing {GUNNER_MLIST_SRC}"
    assert BRAWLER_MLIST_SRC.is_file(), f"Missing {BRAWLER_MLIST_SRC}"
    assert FOX_MLIST_SRC.is_file(), f"Missing {FOX_MLIST_SRC}"

    DEST_BODY_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_MLIST.parent.mkdir(parents=True, exist_ok=True)

    # Parse all lists
    data_g = GUNNER_MLIST_SRC.read_bytes()
    magic_g, path_g, entries_g = parse_mlist(data_g)

    data_b = BRAWLER_MLIST_SRC.read_bytes()
    magic_b, path_b, entries_b = parse_mlist(data_b)
    brawler_by_kind = {e['kind']: e for e in entries_b}

    data_f = FOX_MLIST_SRC.read_bytes()
    magic_f, path_f, entries_f = parse_mlist(data_f)
    fox_by_kind = {e['kind']: e for e in entries_f}

    added_entries = []
    clips_to_copy = []  # (src_path, dest_name)

    # P16: Brawler forward tilt (3 motions)
    p16_moves = [
        ('attack_s3_s', 'mc_attacks3_s', 'c01mcattacks3s.nuanmb', 'c01attacks3s.nuanmb',
         'game_mcattacks3s', 'expression_mcattacks3s', 'sound_mcattacks3s', 'effect_mcattacks3s'),
        ('attack_s3_hi', 'mc_attacks3_hi', 'c01mcattacks3hi.nuanmb', 'c01attacks3hi.nuanmb',
         'game_mcattacks3hi', 'expression_mcattacks3hi', 'sound_mcattacks3hi', 'effect_mcattacks3hi'),
        ('attack_s3_lw', 'mc_attacks3_lw', 'c01mcattacks3lw.nuanmb', 'c01attacks3lw.nuanmb',
         'game_mcattacks3lw', 'expression_mcattacks3lw', 'sound_mcattacks3lw', 'effect_mcattacks3lw'),
    ]
    for donor_kind, owned_name, clip_name, donor_clip_name, game_s, expr_s, snd_s, eff_s in p16_moves:
        donor_entry = brawler_by_kind[hash40(donor_kind)]
        e_raw = create_entry(donor_entry, owned_name, clip_name, expr_s, snd_s, eff_s)
        added_entries.append(e_raw)
        src = P16_CLIPS_DIR / donor_clip_name
        assert src.is_file(), f"Missing P16 clip {src}"
        shutil.copy2(src, DEST_BODY_DIR / clip_name)
        clips_to_copy.append((src, clip_name))
        print(f"  P16: {owned_name}")

    # tilt_up: Brawler up tilt
    tilt_up_donor = brawler_by_kind[hash40('attack_hi3')]
    tilt_up_owned = 'mc_miifighter_attack_hi3'
    tilt_up_clip = 'c01mcmiifighterattackhi3.nuanmb'
    tilt_up_donor_clip = 'c02attackhi3.nuanmb'
    e_raw = create_entry(tilt_up_donor, tilt_up_owned, tilt_up_clip,
                         'expression_mcmiifighterattackhi3', 'sound_mcmiifighterattackhi3',
                         'effect_mcmiifighterattackhi3')
    added_entries.append(e_raw)
    src = TILT_CLIPS_DIR / 'tilt_up__miifighter/package/fighter/miigunner/motion/body/c00' / tilt_up_clip
    if not src.is_file():
        src = WORKSPACE / 'gamedata/mii_customizer/moves/tilt_up__miifighter/package/fighter/miigunner/motion/body/c00' / tilt_up_clip
    assert src.is_file(), f"Missing tilt_up clip {src}"
    shutil.copy2(src, DEST_BODY_DIR / tilt_up_clip)
    clips_to_copy.append((src, tilt_up_clip))
    print(f"  tilt_up: {tilt_up_owned}")

    # tilt_down: Brawler down tilt
    tilt_down_donor = brawler_by_kind[hash40('attack_lw3')]
    tilt_down_owned = 'mc_miifighter_attack_lw3'
    tilt_down_clip = 'c01mcmiifighterattacklw3.nuanmb'
    tilt_down_donor_clip = 'c02attacklw3.nuanmb'
    e_raw = create_entry(tilt_down_donor, tilt_down_owned, tilt_down_clip,
                         'expression_mcmiifighterattacklw3', 'sound_mcmiifighterattacklw3',
                         'effect_mcmiifighterattacklw3')
    added_entries.append(e_raw)
    src = TILT_CLIPS_DIR / 'tilt_down__miifighter/package/fighter/miigunner/motion/body/c00' / tilt_down_clip
    if not src.is_file():
        src = WORKSPACE / 'gamedata/mii_customizer/moves/tilt_down__miifighter/package/fighter/miigunner/motion/body/c00' / tilt_down_clip
    assert src.is_file(), f"Missing tilt_down clip {src}"
    shutil.copy2(src, DEST_BODY_DIR / tilt_down_clip)
    clips_to_copy.append((src, tilt_down_clip))
    print(f"  tilt_down: {tilt_down_owned}")

    # smash_up: Fox up smash (2 motions)
    fox_moves = [
        ('attack_hi4', 'mc_fox_attack_hi4', 'c01mcfoxattackhi4.nuanmb', 'c04attackhi4.nuanmb',
         'game_mcfoxattackhi4', 'expression_mcfoxattackhi4', 'sound_mcfoxattackhi4', 'effect_mcfoxattackhi4'),
        ('attack_hi4_hold', 'mc_fox_attack_hi4_hold', 'c01mcfoxattackhi4charge.nuanmb', 'c04attackhi4charge.nuanmb',
         'game_mcfoxattackhi4charge', 'expression_mcfoxattackhi4charge', 'sound_mcfoxattackhi4charge', 'effect_mcfoxattackhi4charge'),
    ]
    for donor_kind, owned_name, clip_name, donor_clip_name, game_s, expr_s, snd_s, eff_s in fox_moves:
        donor_entry = fox_by_kind[hash40(donor_kind)]
        e_raw = create_entry(donor_entry, owned_name, clip_name, expr_s, snd_s, eff_s)
        added_entries.append(e_raw)
        src = FOX_CLIPS_DIR / donor_clip_name
        assert src.is_file(), f"Missing Fox clip {src}"
        shutil.copy2(src, DEST_BODY_DIR / clip_name)
        clips_to_copy.append((src, clip_name))
        print(f"  smash_up: {owned_name}")

    # Build reference motion list
    all_raw = [e['raw'] for e in entries_g] + added_entries
    new_count = len(all_raw)
    header = struct.pack('<QQQ', magic_g, path_g, new_count)
    rebuilt_mlist_data = header + b''.join(all_raw)
    REFERENCE_MLIST.write_bytes(rebuilt_mlist_data)
    print(f"Reference list: {len(rebuilt_mlist_data)} bytes, {new_count} entries (vanilla {len(entries_g)} + {len(added_entries)} owned)")

    # Build motdiff patch
    stale_bin = DEST_BODY_DIR / 'motion_list.bin'
    if stale_bin.exists():
        stale_bin.unlink()
    assert MOTDIFF_EXE.is_file(), f"Missing motdiff: {MOTDIFF_EXE}"
    patch_path = DEST_BODY_DIR / 'motion_list.motdiff'
    subprocess.run([str(MOTDIFF_EXE), 'diff', str(GUNNER_MLIST_SRC), str(REFERENCE_MLIST), str(patch_path)], check=True)
    
    # Verify roundtrip
    roundtrip = REFERENCE_MLIST.with_name('roundtrip.bin')
    subprocess.run([str(MOTDIFF_EXE), 'patch', str(GUNNER_MLIST_SRC), str(patch_path), str(roundtrip)], check=True)
    assert roundtrip.read_bytes() == rebuilt_mlist_data, 'motdiff roundtrip mismatch'
    roundtrip.unlink()
    print(f"motdiff verified: patch reproduces reference list")

    # Verify parse
    magic_chk, path_chk, entries_chk = parse_mlist(rebuilt_mlist_data)
    assert magic_chk == magic_g
    assert path_chk == path_g
    assert len(entries_chk) == len(entries_g) + len(added_entries)
    print(f"Verified: {len(entries_chk)} entries, magic/path match")

    # Write config.json
    clip_paths = [f"fighter/miigunner/motion/body/c00/{name}" for _, name in clips_to_copy]
    config = {
        "new-dir-infos": [],
        "new-dir-infos-base": {},
        "new-dir-files": {
            "fighter/miigunner/c00": sorted(clip_paths)
        },
        "share-to-vanilla": {},
        "share-to-added": {}
    }
    config_path = PACKAGE_DIR / 'config.json'
    config_path.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    print(f"config.json: {len(clip_paths)} clips")

    # Build manifest
    manifest_files = {}
    for p in sorted(PACKAGE_DIR.rglob('*')):
        if p.is_file():
            rel = p.relative_to(PACKAGE_DIR).as_posix()
            manifest_files[rel] = {
                'size': p.stat().st_size,
                'sha256': sha256_file(p),
            }

    # Get NRO hash
    nro_path = MOD_ROOT / 'builds/0.10.0-menu/libmii_customizer.nro'
    nro_hash = sha256_file(nro_path) if nro_path.is_file() else ""

    # Motion names in order of addition (matches added_entries/clips_to_copy)
    motion_names = [
        'mc_attacks3_s', 'mc_attacks3_hi', 'mc_attacks3_lw',  # P16
        'mc_miifighter_attack_hi3',                              # tilt_up
        'mc_miifighter_attack_lw3',                              # tilt_down
        'mc_fox_attack_hi4', 'mc_fox_attack_hi4_hold',          # smash_up
    ]
    added_motions = {}
    for owned_name, (_, clip_name) in zip(motion_names, clips_to_copy):
        added_motions[owned_name] = {
            'kind_hash': f"0x{hash40(owned_name):010x}",
            'clip': clip_name,
            'clip_hash': f"0x{hash40(clip_name):010x}",
        }

    manifest = {
        'package_name': 'mii_customizer_moves',
        'version': '0.10.0',
        'plugin_nro': {
            'path': 'libmii_customizer.nro',
            'size': nro_path.stat().st_size,
            'sha256': nro_hash,
        },
        'files': manifest_files,
        'added_motions': added_motions,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"Package built: {len(manifest_files)} files, {len(added_motions)} owned motions")

if __name__ == '__main__':
    main()
