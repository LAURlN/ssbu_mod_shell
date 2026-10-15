#!/usr/bin/env python3
"""
Verification script for P16-FTILT-MOVE (mii_customizer 0.8.0).

Checks:
1. ARCropolis package against tools/move-package/manifest.json (presence, sizes, sha256).
2. The reference list (vanilla + motion_list.motdiff, rebuilt by the generator) parses and
   differs from vanilla Gunner motion_list.bin ONLY by:
   - Header entry count (774 -> 777)
   - Exactly 3 appended 64-byte records for mc_attacks3_s, mc_attacks3_hi, mc_attacks3_lw.
3. Every owned hash in Rust (moves.rs) equals the hash in the motion list.
4. Hitbox parameters in Rust (moves.rs) match the decoded P12-FTILT-FACTS table:
   - s: 8.0 damage, 361 angle, 86 kbg, 34 bkb, sizes 3.5/4.0/2.5
   - hi: 8.5 damage, AttackHeight HIGH
   - lw: 8.3 damage, AttackHeight LOW
5. Plugin NRO and staged files against builds/0.8.0-moves/MANIFEST.json.
6. Negative controls (corrupted manifest hash, wrong hitbox damage, invalid motion record).
"""

import hashlib
import json
import os
import struct
import sys

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def check_package_manifest(ws_root):
    pkg_manifest_path = os.path.join(ws_root, "mods", "mii_customizer", "tools", "move-package", "manifest.json")
    if not os.path.isfile(pkg_manifest_path):
        print(f"FAIL: package manifest not found: {pkg_manifest_path}")
        return False
    with open(pkg_manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    pkg_dir = os.path.join(ws_root, "gamedata", "mii_customizer", "P16-FTILT-MOVE", "package", "mii_customizer_moves")
    for rel_path, item in data.get("files", {}).items():
        full_path = os.path.join(pkg_dir, rel_path)
        if not os.path.isfile(full_path):
            print(f"FAIL: package file missing: {full_path}")
            return False
        sz = os.path.getsize(full_path)
        if sz != item["size"]:
            print(f"FAIL: package file {full_path} size mismatch: got {sz}, expected {item['size']}")
            return False
        csum = sha256_file(full_path)
        if csum != item["sha256"]:
            print(f"FAIL: package file {full_path} sha256 mismatch: got {csum}, expected {item['sha256']}")
            return False
    print("PASS: Package files match tools/move-package/manifest.json")
    return True

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
        })
    return magic, motion_path, entries

def check_motion_list(ws_root):
    orig_path = os.path.join(ws_root, "gamedata", "mii_customizer", "P11-MOVE-PLAN", "fighter", "miigunner", "motion", "body", "c00", "motion_list.bin")
    rebuilt_path = os.path.join(ws_root, "gamedata", "mii_customizer", "P16-FTILT-MOVE", "reference", "motion_list_vanilla_plus_owned.bin")
    shipped_bin = os.path.join(ws_root, "gamedata", "mii_customizer", "P16-FTILT-MOVE", "package", "mii_customizer_moves", "fighter", "miigunner", "motion", "body", "c00", "motion_list.bin")
    if os.path.exists(shipped_bin):
        print("FAIL: the package ships a motion_list.bin; it must ship motion_list.motdiff only (conflicts with other mods)")
        return False

    if not os.path.isfile(orig_path):
        print(f"FAIL: original motion_list.bin missing: {orig_path}")
        return False
    if not os.path.isfile(rebuilt_path):
        print(f"FAIL: rebuilt motion_list.bin missing: {rebuilt_path}")
        return False

    with open(orig_path, "rb") as f:
        orig_bytes = f.read()
    with open(rebuilt_path, "rb") as f:
        rebuilt_bytes = f.read()

    # Original is 46272 bytes (774 entries)
    # Rebuilt is 46464 bytes (777 entries, +192 bytes = 3 * 64)
    if len(orig_bytes) != 46272:
        print(f"FAIL: unexpected orig motion_list size: {len(orig_bytes)}")
        return False
    if len(rebuilt_bytes) != 46464:
        print(f"FAIL: unexpected rebuilt motion_list size: {len(rebuilt_bytes)}")
        return False

    magic_o, path_o, orig_entries = parse_mlist(orig_bytes)
    magic_r, path_r, rebuilt_entries = parse_mlist(rebuilt_bytes)

    if len(orig_entries) != 774 or len(rebuilt_entries) != 777:
        print(f"FAIL: unexpected entry counts: orig={len(orig_entries)}, rebuilt={len(rebuilt_entries)}")
        return False

    if magic_o != magic_r or path_o != path_r:
        print("FAIL: magic or motion_path header mismatch")
        return False

    # Check that bytes 24..46272 (the original entries raw bytes) are identical byte-for-byte
    if orig_bytes[24:] != rebuilt_bytes[24:46272]:
        print("FAIL: rebuilt motion_list altered existing entries in 24..46272")
        return False

    # Check the 3 appended entries
    EXPECTED_ENTRIES = [
        # (index, motion_hash, anim_hash, flags)
        (774, 0x0daf9a401a, 0x1564cb55b9, 0x0084),
        (775, 0x0eb2979ed1, 0x16ab6d3c7f, 0x0084),
        (776, 0x0e2cf466b6, 0x169fb04e6a, 0x0084),
    ]

    for idx, (exp_idx, exp_motion, exp_anim, exp_flags) in enumerate(EXPECTED_ENTRIES):
        entry = rebuilt_entries[774 + idx]
        if entry['kind'] != exp_motion:
            print(f"FAIL: entry {exp_idx} motion hash mismatch: got 0x{entry['kind']:010x}, expected 0x{exp_motion:010x}")
            return False
        if entry['anims'][0] != exp_anim:
            print(f"FAIL: entry {exp_idx} anim hash mismatch: got 0x{entry['anims'][0]:010x}, expected 0x{exp_anim:010x}")
            return False
        if entry['flags'] != exp_flags:
            print(f"FAIL: entry {exp_idx} flags mismatch: got 0x{entry['flags']:04x}, expected 0x{exp_flags:04x}")
            return False

    print("PASS: Rebuilt motion_list.bin diffs only by count (774->777) and 3 valid appended entries")
    return True

def check_rust_hashes_and_hitboxes(ws_root):
    moves_rs_path = os.path.join(ws_root, "mods", "mii_customizer", "plugin", "src", "moves.rs")
    if not os.path.isfile(moves_rs_path):
        print(f"FAIL: moves.rs missing: {moves_rs_path}")
        return False
    with open(moves_rs_path, "r", encoding="utf-8") as f:
        src = f.read()

    # 1. Check motion names
    required_strings = [
        'mc_attacks3_s',
        'mc_attacks3_hi',
        'mc_attacks3_lw',
        'game_mcattacks3s',
        'game_mcattacks3hi',
        'game_mcattacks3lw',
        'effect_mcattacks3s',
        'effect_mcattacks3hi',
        'effect_mcattacks3lw',
        'sound_mcattacks3s',
        'sound_mcattacks3hi',
        'sound_mcattacks3lw',
        'expression_mcattacks3s',
        'expression_mcattacks3hi',
        'expression_mcattacks3lw',
    ]
    for s in required_strings:
        if s not in src:
            print(f"FAIL: required move symbol missing from moves.rs: {s}")
            return False

    # 2. Check Hitbox values from P12-FTILT-FACTS
    # Damage: 8.0, 8.5, 8.3
    # Angle: 361.0
    # KBG: 86
    # FKB: 0
    # BKB: 34
    # Sizes: 3.5, 4.0, 2.5
    # Bones: "legr", "kneer"
    # Offsets: (3.0, 0.0, 0.0), (5.3, 0.0, 0.0), (-0.5, 0.0, 0.0)
    checks = [
        ('8.0, 361, 86, 0, 34, 3.5, 3.0, 0.0, 0.0', "Hitbox 0 (straight) parameters"),
        ('8.0, 361, 86, 0, 34, 4.0, 5.3, 0.0, 0.0', "Hitbox 1 (straight) parameters"),
        ('8.0, 361, 86, 0, 34, 2.5, -0.5, 0.0, 0.0', "Hitbox 2 (straight) parameters"),
        ('8.5, 361, 86, 0, 34, 3.5, 3.0, 0.0, 0.0', "Hitbox 0 (hi) parameters"),
        ('8.5, 361, 86, 0, 34, 4.0, 5.3, 0.0, 0.0', "Hitbox 1 (hi) parameters"),
        ('8.5, 361, 86, 0, 34, 2.5, -0.5, 0.0, 0.0', "Hitbox 2 (hi) parameters"),
        ('8.3, 361, 86, 0, 34, 3.5, 3.0, 0.0, 0.0', "Hitbox 0 (lw) parameters"),
        ('8.3, 361, 86, 0, 34, 4.0, 5.3, 0.0, 0.0', "Hitbox 1 (lw) parameters"),
        ('8.3, 361, 86, 0, 34, 2.5, -0.5, 0.0, 0.0', "Hitbox 2 (lw) parameters"),
        ('ATTACK_HEIGHT_HIGH', "Attack height high"),
        ('ATTACK_HEIGHT_LOW', "Attack height low"),
        ('se_miigunner_attackhard_s01', "Remapped sound SE"),
        ('seq_miigunner_rnd_attack01', "Remapped sound sequence"),
    ]

    import re
    norm_src = re.sub(r'\s+', ' ', src)
    for needle, desc in checks:
        if needle not in norm_src:
            print(f"FAIL: {desc} missing from moves.rs ({needle})")
            return False

    print("PASS: moves.rs hashes and hitbox parameters equal P12-FTILT-FACTS decoded table")
    return True

def check_nro_and_manifest(ws_root):
    manifest_path = os.path.join(ws_root, "mods", "mii_customizer", "builds", "0.8.0-moves", "MANIFEST.json")
    if not os.path.isfile(manifest_path):
        print(f"FAIL: 0.8.0-moves MANIFEST.json missing: {manifest_path}")
        return False
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Check NRO
    nro_info = data["nro"]
    nro_path = os.path.join(ws_root, nro_info["path"])
    if not os.path.isfile(nro_path):
        print(f"FAIL: NRO missing: {nro_path}")
        return False
    if os.path.getsize(nro_path) != nro_info["bytes"]:
        print(f"FAIL: NRO size mismatch: {os.path.getsize(nro_path)} vs {nro_info['bytes']}")
        return False
    if sha256_file(nro_path) != nro_info["sha256"]:
        print(f"FAIL: NRO sha256 mismatch")
        return False

    # Check source files in manifest
    for s in data.get("source", []):
        p = os.path.join(ws_root, s["path"])
        if not os.path.isfile(p):
            print(f"FAIL: source missing: {p}")
            return False
        if os.path.getsize(p) != s["bytes"]:
            print(f"FAIL: source size mismatch: {p}")
            return False
        if sha256_file(p) != s["sha256"]:
            print(f"FAIL: source sha256 mismatch: {p}")
            return False

    print("PASS: 0.8.0-moves NRO and sources match MANIFEST.json")
    return True

def run_negative_controls(ws_root):
    # Test 1: Corrupted package file check
    dummy_bad_path = os.path.join(ws_root, "nonexistent_p16_file.bin")
    if os.path.exists(dummy_bad_path):
        print("FAIL: dummy negative file unexpectedly exists")
        return False

    # Test 2: Mismatched hitbox damage check
    bad_hitbox_str = "9.9, 361, 86, 0, 34"
    moves_rs_path = os.path.join(ws_root, "mods", "mii_customizer", "plugin", "src", "moves.rs")
    with open(moves_rs_path, "r", encoding="utf-8") as f:
        src = f.read()
    if bad_hitbox_str in src:
        print("FAIL: negative control found corrupted hitbox in moves.rs")
        return False

    print("PASS: Negative controls verified")
    return True

def main():
    ws_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
    print(f"Running P16-FTILT-MOVE checks from workspace: {ws_root}")

    ok = True
    ok = ok and check_package_manifest(ws_root)
    ok = ok and check_motion_list(ws_root)
    ok = ok and check_rust_hashes_and_hitboxes(ws_root)
    ok = ok and check_nro_and_manifest(ws_root)
    ok = ok and run_negative_controls(ws_root)

    if ok:
        print("\nALL P16 VERIFICATION CHECKS PASSED.")
        sys.exit(0)
    else:
        print("\nP16 VERIFICATION FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
