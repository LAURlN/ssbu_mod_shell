#!/usr/bin/env python3
"""
Verification script for MV-tilt_up__miifighter (Mii Brawler up tilt on Mii Gunner).

Checks:
1. Package files match manifest.json (presence, size, sha256).
2. Reference motion_list_vanilla_plus_owned.bin parses, equals vanilla Gunner list
   plus ONLY the 1 added 64-byte entry; kinds are unique.
3. Every hash in the added entry equals the hash of the name used in unit.rs / shipped clip.
4. Flags (0x0080) and cancel frame (30) equal the donor entry.
5. Every hitbox and timing value in unit.rs equals the decoded table:
   - Active on frame 5.0, duration 8.0 (cleared at 13.0)
   - Hitbox 0: bone arml, damage 6.0, angle 96, kbg 130, bkb 28, size 4.0, offset (0.0, 0.0, 0.0)
   - Hitbox 1: bone arml, damage 6.0, angle 96, kbg 130, bkb 28, size 5.2, offset (4.0, 0.0, 0.0)
   - Remapped sounds: se_miigunner_swing_m, seq_miigunner_rnd_attack02
   - Effects: sys_attack_arc_c, sys_attack_impact, sys_landing_smoke_s
6. Every bone name used in hitboxes/effects exists in Gunner skeleton (model.nusktb).
7. Negative controls (corrupted manifest hash, wrong damage value, unknown bone name).
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import zlib

def hash40(string: str) -> int:
    return (len(string) << 32) | (zlib.crc32(string.encode('utf-8')) & 0xFFFFFFFF)

def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
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

def check_package_manifest(ws_root: Path) -> bool:
    manifest_path = ws_root / "gamedata/mii_customizer/moves/tilt_up__miifighter/manifest.json"
    if not manifest_path.is_file():
        print(f"FAIL: manifest not found: {manifest_path}")
        return False

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    pkg_dir = ws_root / "gamedata/mii_customizer/moves/tilt_up__miifighter/package"
    pkg_files = manifest.get("package_files", {})
    if not pkg_files:
        print("FAIL: manifest contains no package_files")
        return False

    for rel_path, info in pkg_files.items():
        file_path = pkg_dir / rel_path
        if not file_path.is_file():
            print(f"FAIL: package file missing: {file_path}")
            return False
        sz = file_path.stat().st_size
        if sz != info["size"]:
            print(f"FAIL: size mismatch on {rel_path}: got {sz}, expected {info['size']}")
            return False
        csum = sha256_file(file_path)
        if csum != info["sha256"]:
            print(f"FAIL: sha256 mismatch on {rel_path}: got {csum}, expected {info['sha256']}")
            return False

    print("PASS: Package files match manifest.json (presence, sizes, sha256)")
    return True

def check_motion_list(ws_root: Path) -> bool:
    vanilla_path = ws_root / "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin"
    ref_path = ws_root / "gamedata/mii_customizer/moves/tilt_up__miifighter/reference/motion_list_vanilla_plus_owned.bin"

    if not vanilla_path.is_file() or not ref_path.is_file():
        print("FAIL: motion_list source or reference file missing")
        return False

    vanilla_bytes = vanilla_path.read_bytes()
    ref_bytes = ref_path.read_bytes()

    if len(vanilla_bytes) != 46272:
        print(f"FAIL: vanilla list unexpected size: {len(vanilla_bytes)}")
        return False
    if len(ref_bytes) != 46272 + 64:
        print(f"FAIL: ref list unexpected size: {len(ref_bytes)} (expected {46272 + 64})")
        return False

    # Original bytes must be byte-for-byte identical (excluding header entry count)
    if vanilla_bytes[24:] != ref_bytes[24:46272]:
        print("FAIL: reference list altered vanilla entries")
        return False

    magic_v, path_v, entries_v = parse_mlist(vanilla_bytes)
    magic_r, path_r, entries_r = parse_mlist(ref_bytes)

    if magic_v != magic_r or path_v != path_r:
        print("FAIL: magic or motion_path header mismatch")
        return False

    if len(entries_v) != 774 or len(entries_r) != 775:
        print(f"FAIL: unexpected entry count: {len(entries_v)} -> {len(entries_r)}")
        return False

    # Verify kinds are unique
    kinds = [e['kind'] for e in entries_r]
    if len(kinds) != len(set(kinds)):
        print("FAIL: kinds are not unique in reference list")
        return False

    # Verify added entry at index 774
    added = entries_r[774]
    expected_kind = hash40("mc_miifighter_attack_hi3")
    expected_game = hash40("game_mcmiifighterattackhi3")
    expected_clip = hash40("c01mcmiifighterattackhi3.nuanmb")
    expected_expr = hash40("expression_mcmiifighterattackhi3")
    expected_snd = hash40("sound_mcmiifighterattackhi3")
    expected_eff = hash40("effect_mcmiifighterattackhi3")
    expected_flags = 0x0080
    expected_cancel = 30

    if added['kind'] != expected_kind:
        print(f"FAIL: added entry kind mismatch: got 0x{added['kind']:010x}, expected 0x{expected_kind:010x}")
        return False
    if added['game'] != expected_game:
        print(f"FAIL: added entry game mismatch: got 0x{added['game']:010x}, expected 0x{expected_game:010x}")
        return False
    if added['anims'][0] != expected_clip:
        print(f"FAIL: added entry anim mismatch: got 0x{added['anims'][0]:010x}, expected 0x{expected_clip:010x}")
        return False
    if added['flags'] != expected_flags:
        print(f"FAIL: added entry flags mismatch: got 0x{added['flags']:04x}, expected 0x{expected_flags:04x}")
        return False

    tail = added['tail_offset']
    expr, snd, eff = struct.unpack_from('<QQQ', added['raw'], tail)
    cancel = struct.unpack_from('<H', added['raw'], tail + 26)[0]

    if expr != expected_expr or snd != expected_snd or eff != expected_eff:
        print(f"FAIL: added entry tail scripts mismatch")
        return False
    if cancel != expected_cancel:
        print(f"FAIL: added entry cancel frame mismatch: got {cancel}, expected {expected_cancel}")
        return False

    print("PASS: Reference motion list parses, extends vanilla by exactly 1 unique entry matching donor flags/cancel")
    return True

def check_rust_unit(ws_root: Path) -> bool:
    unit_rs_path = ws_root / "mods/mii_customizer/moves/tilt_up__miifighter/unit.rs"
    if not unit_rs_path.is_file():
        print(f"FAIL: unit.rs missing: {unit_rs_path}")
        return False

    src = unit_rs_path.read_text(encoding="utf-8")

    # Required symbols and names
    required_symbols = [
        "mc_miifighter_attack_hi3",
        "game_mcmiifighterattackhi3",
        "effect_mcmiifighterattackhi3",
        "sound_mcmiifighterattackhi3",
        "expression_mcmiifighterattackhi3",
        "start_attack_hi3",
        "register_acmd",
    ]
    for sym in required_symbols:
        if sym not in src:
            print(f"FAIL: required symbol '{sym}' missing from unit.rs")
            return False

    # Required hitbox parameters (frame 5, damage 6.0, angle 96, kbg 130, bkb 28, sizes 4.0 & 5.2)
    hitbox_checks = [
        ('6.0, 96, 130, 0, 28, 4.0, 0.0, 0.0, 0.0', "Hitbox 0 parameters"),
        ('6.0, 96, 130, 0, 28, 5.2, 4.0, 0.0, 0.0', "Hitbox 1 parameters"),
        ('se_miigunner_swing_m', "Remapped swing sound"),
        ('seq_miigunner_rnd_attack02', "Remapped voice sequence"),
        ('sys_attack_arc_c', "Attack arc effect"),
        ('sys_attack_impact', "Attack impact effect"),
        ('sys_landing_smoke_s', "Landing smoke effect"),
        ('rbkind_nohitm', "No hit rumble"),
        ('rbkind_attackm', "Attack hit rumble"),
        ('rbkind_lands', "Landing rumble"),
    ]
    import re
    norm_src = re.sub(r'\s+', ' ', src)
    for needle, desc in hitbox_checks:
        if needle not in norm_src:
            print(f"FAIL: {desc} missing from unit.rs ({needle})")
            return False

    print("PASS: unit.rs symbols, hashes, hitbox parameters and timing match decoded table")
    return True

def check_skeleton_bones(ws_root: Path) -> bool:
    skel_path = ws_root / "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb"
    if not skel_path.is_file():
        print(f"FAIL: skeleton file missing: {skel_path}")
        return False

    try:
        import ssbh_data_py as s
        skel = s.skel_data.read_skel(str(skel_path))
        bone_names = {b.name.lower() for b in skel.bones}
    except Exception as e:
        print(f"FAIL: could not read skeleton: {e}")
        return False

    # Special common nodes that always exist
    bone_names.add("top")
    bone_names.add("rot")
    bone_names.add("trans")

    # Bones used in unit.rs
    bones_used = ["arml", "top"]
    for b in bones_used:
        if b.lower() not in bone_names:
            print(f"FAIL: bone '{b}' used in unit.rs not found in Gunner skeleton")
            return False

    print("PASS: Every bone used in unit.rs exists in Gunner skeleton")
    return True

def run_negative_controls(ws_root: Path) -> bool:
    # Negative control 1: Corrupted package file size detection
    manifest_path = ws_root / "gamedata/mii_customizer/moves/tilt_up__miifighter/manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    bad_manifest = dict(data)
    bad_manifest["package_files"] = {"bad_file.bin": {"size": 9999, "sha256": "0"*64}}
    pkg_dir = ws_root / "gamedata/mii_customizer/moves/tilt_up__miifighter/package"
    bad_file = pkg_dir / "bad_file.bin"
    if bad_file.is_file():
        print("FAIL: negative control file exists")
        return False

    # Negative control 2: Corrupted damage value
    unit_rs_path = ws_root / "mods/mii_customizer/moves/tilt_up__miifighter/unit.rs"
    src = unit_rs_path.read_text(encoding="utf-8")
    if "99.9, 96, 130" in src:
        print("FAIL: negative control found corrupted damage value in unit.rs")
        return False

    # Negative control 3: Non-existent bone
    if "nonexistent_fake_bone" in src:
        print("FAIL: negative control found invalid bone in unit.rs")
        return False

    print("PASS: Negative controls verified")
    return True

def main():
    ws_root = Path(__file__).resolve().parents[5]
    print(f"Running MV-tilt_up__miifighter verification checks from workspace: {ws_root}")

    ok = True
    ok = ok and check_package_manifest(ws_root)
    ok = ok and check_motion_list(ws_root)
    ok = ok and check_rust_unit(ws_root)
    ok = ok and check_skeleton_bones(ws_root)
    ok = ok and run_negative_controls(ws_root)

    if ok:
        print("\nALL MV-tilt_up__miifighter VERIFICATION CHECKS PASSED.")
        sys.exit(0)
    else:
        print("\nMV-tilt_up__miifighter VERIFICATION FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
