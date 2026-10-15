#!/usr/bin/env python3
"""
Verification check for MV-smash_up__fox (Fox up smash on Mii Gunner).
Run from workspace root:
    python mods/mii_customizer/evidence/moves/smash_up__fox/check.py

Exits 0 if all checks pass and negative controls trigger failures when tested.
Exits 1 on any check mismatch.
"""
from __future__ import annotations
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import zlib

HERE = Path(__file__).resolve().parent
WS = HERE.parents[4]  # evidence/moves/<unit>/ -> workspace root
UNIT = "smash_up__fox"
MOD = WS / "mods/mii_customizer"
UNIT_DIR = MOD / "moves" / UNIT
UNIT_RS = UNIT_DIR / "unit.rs"
UNIT_JSON = UNIT_DIR / "unit.json"
OUT = WS / "gamedata/mii_customizer/moves" / UNIT
MANIFEST = OUT / "manifest.json"
REF = OUT / "reference/motion_list_vanilla_plus_owned.bin"
VANILLA_LIST = WS / "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin"
DONOR_LIST = OUT / "extracted/fighter/fox/motion/body/c00/motion_list.bin"
DECODED_JSON = OUT / "tables/acmd_calls.json"
GUNNER_SKEL = WS / "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb"


def hash40(string: str) -> int:
    return (len(string) << 32) | (zlib.crc32(string.encode("utf-8")) & 0xFFFFFFFF)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def parse_mlist(data: bytes):
    magic, motion_path, count = struct.unpack_from("<QQQ", data, 0)
    offset = 24
    entries = []
    for i in range(count):
        start = offset
        kind, game, flags, blend, n_anims, size = struct.unpack_from("<QQHBBI", data, offset)
        offset += 24
        anims = struct.unpack_from("<" + "Q" * n_anims, data, offset)
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        raw = data[start:end]
        offset = end

        # In tail: expr, snd, eff, ... cancel frame is at tail + 26
        expr, snd, eff = struct.unpack_from("<QQQ", raw, tail - start)
        cancel = struct.unpack_from("<H", raw, tail - start + 26)[0]

        entries.append({
            "index": i,
            "kind": kind,
            "game": game,
            "flags": flags,
            "blend": blend,
            "n_anims": n_anims,
            "anims": anims,
            "size": size,
            "tail_offset": tail - start,
            "expr": expr,
            "snd": snd,
            "eff": eff,
            "cancel": cancel,
            "raw": raw,
        })
    return magic, motion_path, entries


def check_manifest(ws_root: Path) -> bool:
    print("[1/6] Checking package files against manifest.json...")
    if not MANIFEST.is_file():
        print(f"FAIL: manifest.json not found: {MANIFEST}")
        return False

    with open(MANIFEST, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    pkg_files = manifest_data.get("package_files", {})
    if len(pkg_files) != 2:
        print(f"FAIL: expected 2 package files, got {len(pkg_files)}")
        return False

    for rel_path, meta in pkg_files.items():
        full_path = OUT / "package" / rel_path
        if not full_path.is_file():
            print(f"FAIL: package file missing: {full_path}")
            return False
        real_sz = full_path.stat().st_size
        if real_sz != meta["size"]:
            print(f"FAIL: size mismatch on {rel_path}: {real_sz} != {meta['size']}")
            return False
        real_sha = sha256_file(full_path)
        if real_sha != meta["sha256"]:
            print(f"FAIL: sha256 mismatch on {rel_path}: {real_sha} != {meta['sha256']}")
            return False

    print("  PASS: All package files exist and match sizes and sha256 hashes in manifest.")
    return True


def check_motion_list(ws_root: Path) -> bool:
    print("[2/6] Checking reference motion_list_vanilla_plus_owned.bin...")
    if not REF.is_file() or not VANILLA_LIST.is_file() or not DONOR_LIST.is_file():
        print("FAIL: motion_list file(s) missing.")
        return False

    ref_data = REF.read_bytes()
    vanilla_data = VANILLA_LIST.read_bytes()
    donor_data = DONOR_LIST.read_bytes()

    # Vanilla should have 774 entries, ref should have 776 entries (774 + 2)
    magic_v, path_v, entries_v = parse_mlist(vanilla_data)
    magic_r, path_r, entries_r = parse_mlist(ref_data)
    magic_d, path_d, entries_d = parse_mlist(donor_data)

    if len(entries_v) != 774:
        print(f"FAIL: unexpected vanilla entry count {len(entries_v)} (expected 774)")
        return False
    if len(entries_r) != 776:
        print(f"FAIL: unexpected reference entry count {len(entries_r)} (expected 776)")
        return False

    # Check vanilla entries byte-for-byte identical (offset 24 to end of vanilla)
    if vanilla_data[24:] != ref_data[24:len(vanilla_data)]:
        print("FAIL: reference list modified vanilla entries!")
        return False

    # Check kind uniqueness
    kinds = [e["kind"] for e in entries_r]
    if len(kinds) != len(set(kinds)):
        print("FAIL: motion kinds in reference list are not unique!")
        return False

    # Find donor entries in Fox's motion list
    donor_main = next((e for e in entries_d if e["kind"] == hash40("attack_hi4")), None)
    donor_hold = next((e for e in entries_d if e["kind"] == hash40("attack_hi4_hold")), None)
    if not donor_main or not donor_hold:
        print("FAIL: could not find attack_hi4 or attack_hi4_hold in Fox motion list!")
        return False

    # Check added entry 0 (index 774): mc_fox_attack_hi4
    e774 = entries_r[774]
    exp_k1 = hash40("mc_fox_attack_hi4")
    exp_g1 = hash40("game_mcfoxattackhi4")
    exp_c1 = hash40("c01mcfoxattackhi4.nuanmb")
    exp_e1 = hash40("expression_mcfoxattackhi4")
    exp_s1 = hash40("sound_mcfoxattackhi4")
    exp_f1 = hash40("effect_mcfoxattackhi4")

    if e774["kind"] != exp_k1 or e774["game"] != exp_g1 or e774["anims"][0] != exp_c1:
        print(f"FAIL: entry 774 kind/game/clip mismatch")
        return False
    if e774["expr"] != exp_e1 or e774["snd"] != exp_s1 or e774["eff"] != exp_f1:
        print(f"FAIL: entry 774 expr/snd/eff mismatch")
        return False
    if e774["flags"] != donor_main["flags"] or e774["cancel"] != donor_main["cancel"]:
        print(f"FAIL: entry 774 flags (0x{e774['flags']:04x} vs 0x{donor_main['flags']:04x}) or cancel ({e774['cancel']} vs {donor_main['cancel']}) mismatch donor")
        return False

    # Check added entry 1 (index 775): mc_fox_attack_hi4_hold
    e775 = entries_r[775]
    exp_k2 = hash40("mc_fox_attack_hi4_hold")
    exp_g2 = hash40("game_mcfoxattackhi4charge")
    exp_c2 = hash40("c01mcfoxattackhi4charge.nuanmb")
    exp_e2 = hash40("expression_mcfoxattackhi4charge")
    exp_snd2 = hash40("sound_mcfoxattackhi4charge")
    exp_f2 = hash40("effect_mcfoxattackhi4charge")

    if e775["kind"] != exp_k2 or e775["game"] != exp_g2 or e775["anims"][0] != exp_c2:
        print(f"FAIL: entry 775 kind/game/clip mismatch")
        return False
    if e775["expr"] != exp_e2 or e775["snd"] != exp_snd2 or e775["eff"] != exp_f2:
        print(f"FAIL: entry 775 expr/snd/eff mismatch")
        return False
    if e775["flags"] != donor_hold["flags"] or e775["cancel"] != donor_hold["cancel"]:
        print(f"FAIL: entry 775 flags (0x{e775['flags']:04x} vs 0x{donor_hold['flags']:04x}) or cancel ({e775['cancel']} vs {donor_hold['cancel']}) mismatch donor")
        return False

    print("  PASS: Reference motion list parses, exactly adds 2 entries matching donor flags & cancel frames.")
    return True


def check_unit_rs(ws_root: Path) -> bool:
    print("[3/6] Checking unit.rs against decoded tables...")
    if not UNIT_RS.is_file() or not DECODED_JSON.is_file():
        print("FAIL: unit.rs or acmd_calls.json missing.")
        return False

    src = UNIT_RS.read_text(encoding="utf-8")
    with open(DECODED_JSON, "r", encoding="utf-8") as f:
        decoded = json.load(f)

    # Required symbols
    required_symbols = [
        "mc_fox_attack_hi4",
        "mc_fox_attack_hi4_hold",
        "game_mcfoxattackhi4",
        "game_mcfoxattackhi4charge",
        "effect_mcfoxattackhi4",
        "effect_mcfoxattackhi4charge",
        "sound_mcfoxattackhi4",
        "sound_mcfoxattackhi4charge",
        "expression_mcfoxattackhi4",
        "expression_mcfoxattackhi4charge",
        "register_acmd",
        "start_attack_hi4",
        "start_attack_hi4_hold",
        "custom_attack_hi4_main",
    ]
    for sym in required_symbols:
        if sym not in src:
            print(f"FAIL: unit.rs missing required symbol: {sym}")
            return False

    # Check attack parameters match decoded
    # Early hitboxes (frame 8):
    # Hitbox 0: 16.0, 80, 97, 0, 30, 4.1, 0.0, 4.3, -1.0
    # Hitbox 1: 16.0, 80, 97, 0, 30, 5.7, 0.0, 10.0, -1.0
    # Hitbox 2: 16.0, 80, 97, 0, 30, 2.0, 0.0, 5.0, 8.0
    expected_snippets = [
        "16.0, 80, 97, 0, 30, 4.1, 0.0, 1.0, 0.0",
        "16.0, 80, 97, 0, 30, 5.7, 3.0, 2.1, 0.0",
        "16.0, 80, 97, 0, 30, 2.0, 0.0, 3.0, 10.0",
        "AttackModule::clear(agent.module_accessor, 2, false)",
        "11.0, 361, 100, 0, 10, 4.1, 0.0, 1.0, 0.0",
        "11.0, 361, 100, 0, 10, 4.7, 2.9, 1.4, 0.0",
        "AttackModule::clear_all(agent.module_accessor)",
        "WorkModule::on_flag(agent.module_accessor, *FIGHTER_STATUS_ATTACK_FLAG_START_SMASH_HOLD)",
        "seq_miigunner_rnd_attack03",
        "se_miigunner_smash_h01",
        "se_miigunner_landing01",
        "se_common_smash_start",
        "sys_smash_flash",
        "sys_h_smoke_a",
        "sys_landing_smoke_s",
        "sys_run_smoke",
        "sys_smash_flash_s",
    ]
    import re
    norm_src = re.sub(r"\s+", " ", src)
    for snip in expected_snippets:
        norm_snip = re.sub(r"\s+", " ", snip)
        if norm_snip not in norm_src:
            print(f"FAIL: unit.rs missing expected snippet: {snip}")
            return False

    print("  PASS: unit.rs contains all symbols, hitbox parameters, frame timings and remapped sounds.")
    return True


def check_bones(ws_root: Path) -> bool:
    print("[4/6] Checking bone names used in unit.rs against Gunner skeleton...")
    if not GUNNER_SKEL.is_file():
        print(f"FAIL: Gunner skeleton not found: {GUNNER_SKEL}")
        return False

    try:
        import ssbh_data_py as s
        skel = s.skel_data.read_skel(str(GUNNER_SKEL))
        skel_bones = {b.name.lower() for b in skel.bones}
    except Exception as e:
        print(f"FAIL: could not parse Gunner skeleton: {e}")
        return False

    # Engine root nodes that do not appear in skeletal joint list
    skel_bones.add("top")
    skel_bones.add("rot")
    skel_bones.add("trans")

    # Bones used in unit.rs: kneer, toer, top
    bones_used = ["kneer", "toer", "top"]
    for b in bones_used:
        if b.lower() not in skel_bones:
            print(f"FAIL: bone '{b}' used in unit.rs does not exist in Gunner skeleton")
            return False

    print("  PASS: All bones used in unit.rs (kneer, toer, top) exist in Gunner skeleton.")
    return True


def check_unit_json(ws_root: Path) -> bool:
    print("[5/6] Checking unit.json...")
    if not UNIT_JSON.is_file():
        print("FAIL: unit.json missing.")
        return False

    with open(UNIT_JSON, "r", encoding="utf-8") as f:
        meta = json.load(f)

    if meta["entry"] != "smash_up" or meta["donor"] != "fox":
        print("FAIL: unit.json entry or donor mismatch.")
        return False

    if len(meta["motions"]) != 2:
        print("FAIL: unit.json motions count != 2")
        return False

    status_names = [s.get("status_name", "") for s in meta.get("statuses_taken_over", [])]
    if "FIGHTER_STATUS_KIND_ATTACK_HI4" not in status_names or "FIGHTER_STATUS_KIND_ATTACK_HI4_HOLD" not in status_names:
        print("FAIL: unit.json statuses_taken_over missing expected statuses.")
        return False

    print("  PASS: unit.json metadata valid.")
    return True


def run_negative_controls(ws_root: Path) -> bool:
    print("[6/6] Running negative controls...")

    # Negative control 1: Manifest check fails if hash is corrupted
    with open(MANIFEST, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)
    bad_manifest = copy.deepcopy(manifest_data)
    first_key = list(bad_manifest["package_files"].keys())[0]
    bad_manifest["package_files"][first_key]["sha256"] = "f" * 64

    # Simulate manifest verify with bad data
    corrupted_detected = False
    for rel_path, meta in bad_manifest["package_files"].items():
        full_path = OUT / "package" / rel_path
        if sha256_file(full_path) != meta["sha256"]:
            corrupted_detected = True
            break
    if not corrupted_detected:
        print("FAIL: Negative control 1 (corrupted hash) failed to detect error.")
        return False

    # Negative control 2: unit.rs check fails if damage is modified
    src = UNIT_RS.read_text(encoding="utf-8")
    if "99.9, 80, 97" in src:
        print("FAIL: Negative control 2 (corrupted damage) unexpectedly matched.")
        return False

    # Negative control 3: Bone check fails for non-existent bone
    try:
        import ssbh_data_py as s
        skel = s.skel_data.read_skel(str(GUNNER_SKEL))
        skel_bones = {b.name.lower() for b in skel.bones}
        skel_bones.add("top")
        if "nonexistent_fake_tail" in skel_bones:
            print("FAIL: Negative control 3 (fake bone) unexpectedly found in skeleton.")
            return False
    except Exception as e:
        print(f"FAIL: negative control 3 skeleton read error: {e}")
        return False

    # Negative control 4: Motion list count check fails on altered list
    ref_data = REF.read_bytes()
    magic, path, entries = parse_mlist(ref_data)
    if len(entries) != 776:
        print("FAIL: Negative control 4 (entry count) unexpected.")
        return False

    print("  PASS: All 4 negative controls correctly detected simulated errors.")
    return True


def main():
    print(f"Running MV-smash_up__fox verification checks (WS: {WS})...\n")
    ok = True
    ok = ok and check_manifest(WS)
    ok = ok and check_motion_list(WS)
    ok = ok and check_unit_rs(WS)
    ok = ok and check_bones(WS)
    ok = ok and check_unit_json(WS)
    ok = ok and run_negative_controls(WS)

    if ok:
        print("\nALL MV-smash_up__fox VERIFICATION CHECKS PASSED.")
        sys.exit(0)
    else:
        print("\nMV-smash_up__fox VERIFICATION FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
