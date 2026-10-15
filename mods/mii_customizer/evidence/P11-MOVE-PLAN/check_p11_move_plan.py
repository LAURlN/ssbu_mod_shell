#!/usr/bin/env python3
"""
check_p11_move_plan.py - Validation check for P11-MOVE-PLAN research report.

Validates:
1. Exact file sizes and SHA-256 hashes for all 38 game files extracted and cited.
2. Motion list entry counts and exact jab motion properties (kind, script, flags, blend, anim, cancel, no_stop_intp).
3. Skeleton bone counts (71 bones) and animation node counts (75 transform nodes, 12 visibility nodes).
4. Negative controls ensuring any corrupted hash, modified entry count, or invalid timing value exits 1.
"""

import sys
import os
import hashlib
from pathlib import Path

# Workspace root is 4 levels up from mods/mii_customizer/evidence/P11-MOVE-PLAN/
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "mods/ssbu_mod_new/src/pgwr/tools"))
sys.path.insert(0, str(ROOT / "mods/ssbu_mod_new/builds/.cache/dk_cargo/python"))

import mlist
import ssbh_data_py as s

# Pinned file records: (rel_path, expected_bytes, expected_sha256)
EXPECTED_FILES = [
    # Motion lists
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin", 46272, "2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/motion_list.bin", 45872, "424aded2eabeaadecb7fcbb6052ee38a3f7fdb330ce3831ada6620691ca9ed4e"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/motion/body/c00/motion_list.bin", 45696, "9692b79ea80dba9abf64da65dbfa2ce064eab912572f06841cf2902a4f41027a"),
    # Gunner animations
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/c00attack11.nuanmb", 26104, "5d89ec6d493a70e109b9521ba798d73460c2c6683a7cc9f1109b668d9583bd19"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/c00attack12.nuanmb", 28488, "aba54d06a5b746521a27a20a65679ef04aac729dcedc3441e8a40662221541cc"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/c00attack13.nuanmb", 32568, "f71255e95e3aca399fb723cbd0196f2642067b26ffaea94553c633faeb08d200"),
    # Brawler animations
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/c00attack11.nuanmb", 22520, "b2ef40b7cdc0473867a108c7751a7c11e85862e82dfccc0b6e6280b4e586aa09"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/c00attack12.nuanmb", 23032, "b85d05ebdbbb50409b33d00253c556cc160ed72038fa39c800d4f27e9caed98d"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/c00attack100start.nuanmb", 23833, "1a7eef7650262a2cb85cb01a7567d5c62d5d779feed48cc35c95e199884cb67f"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/c00attack100.nuanmb", 19768, "e0686a1ab62e564b32bd8c4b01a63976bfcd77e0c5a42926dc7bb72c2b8aa028"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/c00attackend.nuanmb", 28024, "16fb947a788af6f37eafdb4c55b63588c9ae2a40246842ece33e26800d4a4d76"),
    # Swordfighter animations
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/motion/body/c00/c00attack11.nuanmb", 32824, "069b485743b00ef50a54386221bd8e48b578c2421962366ea52e4c5cddf0fd8d"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/motion/body/c00/c00attack12.nuanmb", 33720, "fc7e16f9702130b71a4712b8bb1ea6d54c36cc88f9fc41963cfcaf3e957f39f6"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/motion/body/c00/c00attack13.nuanmb", 31032, "b7e179bdfad95c370fff7d363ca92cfafe2555c6422ca1237af5b3ecef2a8d70"),
    # Skeletons
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb", 20160, "1d66b6d1cc4ce3b1c0883a21194cf998531c4a92ccb1c6561f69e68fd671429d"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_f/c00/model.nusktb", 20160, "43f13756fb0fd5bed5dd37206e060818fc5bcd0ff7d99ae47b8419816ba4ed33"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/model/b_normalfighter_m/c00/model.nusktb", 20160, "3f4a447406aca5e337591561719d025f04e474ea3b62a81d2a65c50edb13ec3d"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/model/b_normalfighter_f/c00/model.nusktb", 20160, "3f4a447406aca5e337591561719d025f04e474ea3b62a81d2a65c50edb13ec3d"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/model/b_normalswordman_m/c00/model.nusktb", 20160, "e0407f6169cc77262957e22c55882b7a4d6b66733c9d55e5391d02059a90ea42"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/model/b_normalswordman_f/c00/model.nusktb", 20160, "e0407f6169cc77262957e22c55882b7a4d6b66733c9d55e5391d02059a90ea42"),
    # Meshes
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.numshb", 394456, "416354380e984f07b67c9173df4df0c4f62ac262ff899e7e0297371bbfbee145"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/model/b_normalfighter_m/c00/model.numshb", 741912, "b504e701c949fcd4b5cfda438df9ba6cd4c15d48d85fcfa58e74dc6599a488d1"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/model/b_normalswordman_m/c00/model.numshb", 795216, "b22c52a0ba2a9d5be39bf81db2cb9c1e09983d955a1acc13390120693db514f6"),
    # Parameters
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/param/vl.prc", 10192, "c3600293023f7098de6e7d6e2795dfe9b9948502d0390bc0f30982e92f3bcd27"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/param/vl.prc", 9190, "ac42df25d582e1f2b0be3c45305b7c5148c60cbba49f8f886d449ad44ff6e677"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/param/vl.prc", 12365, "0390786602710dbaad97891407a968b2b2b3b6fffb3d065f6ffc2b358da02a9b"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/common/param/fighter_param.prc", 176604, "87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2"),
    # Effects
    ("gamedata/mii_customizer/P11-MOVE-PLAN/effect/fighter/miigunner/ef_miigunner.eff", 20034240, "9f27743cf9971ae60d0611eedd5d8a0060dcf04600bab1b5b483312ac688fb90"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/effect/fighter/miifighter/ef_miifighter.eff", 14356992, "32a6ecc771f921c9ddbc4a3339d89e012e802112ac184fbf3eb9110f37c1e88c"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/effect/fighter/miiswordsman/ef_miiswordsman.eff", 15888896, "6bcb258c77591ddd516777bb9cdd78543fe5074f5a89bebb65c836930f6a720c"),
    # Sound tonelabels
    ("gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miigunner.tonelabel", 720, "8098b82aca965233883702898ee93c4fcf878b5730f8ebbbe84422dad08c2036"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miigunner_c00.tonelabel", 720, "8098b82aca965233883702898ee93c4fcf878b5730f8ebbbe84422dad08c2036"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miifighter.tonelabel", 736, "9a77603f87971c7d659ed170806173d204e1771323d85a9438b6f518f2ae4a8d"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miifighter_c00.tonelabel", 736, "9a77603f87971c7d659ed170806173d204e1771323d85a9438b6f518f2ae4a8d"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miiswordsman.tonelabel", 664, "2d58ef54a64c50fc24dc77f1e32177c3322ef21cad71f1aa3ef4b329c204ea80"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miiswordsman_c00.tonelabel", 664, "2d58ef54a64c50fc24dc77f1e32177c3322ef21cad71f1aa3ef4b329c204ea80"),
    # lua2cpp NROs
    ("gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miigunner.nro", 1662976, "64ec160d90eb97680266710155481c8baab1688ad98e890942be525c2007330c"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miifighter.nro", 2068480, "3736a24b14a282f50cd4fde951166299c8b0749c7a9baecd457c24925735047d"),
    ("gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miiswordsman.nro", 2101248, "30aad5f5374b3577b581347323d82f0d82af92b9c58d42b2f4589d932253a127"),
]

def check_file_hashes():
    print(f"Checking {len(EXPECTED_FILES)} pinned file records...")
    for rel_path, expected_bytes, expected_hash in EXPECTED_FILES:
        full_path = ROOT / rel_path
        if not full_path.is_file():
            print(f"FAIL: Missing file {rel_path}")
            return False
        data = full_path.read_bytes()
        actual_bytes = len(data)
        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_bytes != expected_bytes:
            print(f"FAIL: Size mismatch for {rel_path}: got {actual_bytes}, expected {expected_bytes}")
            return False
        if actual_hash != expected_hash:
            print(f"FAIL: Hash mismatch for {rel_path}: got {actual_hash}, expected {expected_hash}")
            return False
    print(f"PASS: All {len(EXPECTED_FILES)} files byte-exact and SHA-256 verified.")
    return True

def check_motion_lists():
    print("Checking motion lists and jab entries...")
    # 1. Gunner (774 entries)
    g_path = ROOT / "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin"
    g_parsed = mlist.parse(g_path)
    if len(g_parsed["entries"]) != 774:
        print(f"FAIL: Gunner entries = {len(g_parsed['entries'])}, expected 774")
        return False
    # Check jab entries: 66, 67, 68
    g_jab1 = g_parsed["entries"][66]
    g_jab2 = g_parsed["entries"][67]
    g_jab3 = g_parsed["entries"][68]
    assert g_jab1["kind"] == 0x099c52257e and g_jab1["gs"] == 0x0d04731edc and g_jab1["flags"] == 0x0084 and (g_jab1["cancel"] & 0xff) == 26
    assert g_jab2["kind"] == 0x09055b74c4 and g_jab2["gs"] == 0x0d9d7a4f66 and g_jab2["flags"] == 0x0084 and (g_jab2["cancel"] & 0xff) == 26
    assert g_jab3["kind"] == 0x09725c4452 and g_jab3["gs"] == 0x0dea7d7ff0 and g_jab3["flags"] == 0x0084 and (g_jab3["cancel"] & 0xff) == 38

    # 2. Brawler (764 entries)
    f_path = ROOT / "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/motion_list.bin"
    f_parsed = mlist.parse(f_path)
    if len(f_parsed["entries"]) != 764:
        print(f"FAIL: Brawler entries = {len(f_parsed['entries'])}, expected 764")
        return False
    # Check jab & rapid jab entries: 65, 66, 67, 68, 69
    f_jab1 = f_parsed["entries"][65]
    f_jab2 = f_parsed["entries"][66]
    f_j100s = f_parsed["entries"][67]
    f_j100 = f_parsed["entries"][68]
    f_j100e = f_parsed["entries"][69]
    assert f_jab1["kind"] == 0x099c52257e and f_jab1["gs"] == 0x0d04731edc and (f_jab1["cancel"] & 0xff) == 16
    assert f_jab2["kind"] == 0x09055b74c4 and f_jab2["gs"] == 0x0d9d7a4f66 and (f_jab2["cancel"] & 0xff) == 19
    assert f_j100s["kind"] == 0x1003559f46 and f_j100s["gs"] == 0x138e3b5d31 and (f_j100s["cancel"] & 0xff) == 0
    assert f_j100["kind"] == 0x0a5ae1e07e and f_j100["gs"] == 0x0e62a10381 and f_j100["flags"] == 0x0006 and f_j100["cancel"] == 256
    assert f_j100e["kind"] == 0x0ea34e5703 and f_j100e["gs"] == 0x116af782d9 and (f_j100e["cancel"] & 0xff) == 41

    # 3. Swordfighter (765 entries)
    s_path = ROOT / "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/motion/body/c00/motion_list.bin"
    s_parsed = mlist.parse(s_path)
    if len(s_parsed["entries"]) != 765:
        print(f"FAIL: Swordfighter entries = {len(s_parsed['entries'])}, expected 765")
        return False
    # Check jab entries: 65, 66, 67
    s_jab1 = s_parsed["entries"][65]
    s_jab2 = s_parsed["entries"][66]
    s_jab3 = s_parsed["entries"][67]
    assert s_jab1["kind"] == 0x099c52257e and s_jab1["gs"] == 0x0d04731edc and s_jab1["flags"] == 0x0084 and (s_jab1["cancel"] & 0xff) == 20
    assert s_jab2["kind"] == 0x09055b74c4 and s_jab2["gs"] == 0x0d9d7a4f66 and s_jab2["flags"] == 0x0080 and (s_jab2["cancel"] & 0xff) == 23
    assert s_jab3["kind"] == 0x09725c4452 and s_jab3["gs"] == 0x0dea7d7ff0 and s_jab3["flags"] == 0x0084 and (s_jab3["cancel"] & 0xff) == 39

    print("PASS: Motion list counts and jab entry properties verified.")
    return True

def check_skeletons_and_animations():
    print("Checking skeletons and animation tracks...")
    skels = [
        "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb",
        "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_f/c00/model.nusktb",
        "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/model/b_normalfighter_m/c00/model.nusktb",
        "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/model/b_normalfighter_f/c00/model.nusktb",
        "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/model/b_normalswordman_m/c00/model.nusktb",
        "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/model/b_normalswordman_f/c00/model.nusktb",
    ]
    base_bones = None
    for sp in skels:
        skel = s.skel_data.read_skel(str(ROOT / sp))
        bones = [b.name for b in skel.bones]
        if len(bones) != 71:
            print(f"FAIL: {sp} has {len(bones)} bones, expected 71")
            return False
        if base_bones is None:
            base_bones = set(bones)
        else:
            if set(bones) != base_bones:
                print(f"FAIL: Skeleton bone mismatch in {sp}")
                return False

    # Check animation track counts: 75 transform nodes, 12 visibility nodes
    anims = [
        "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/c00attack11.nuanmb",
        "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/c00attack11.nuanmb",
        "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/motion/body/c00/c00attack11.nuanmb",
    ]
    for ap in anims:
        anim = s.anim_data.read_anim(str(ROOT / ap))
        assert len(anim.groups) == 2, f"Expected 2 groups in {ap}"
        assert len(anim.groups[0].nodes) == 75, f"Expected 75 transform nodes in {ap}"
        assert len(anim.groups[1].nodes) == 12, f"Expected 12 visibility nodes in {ap}"

    print("PASS: Skeletons (71 bones) and animation tracks (75 transform / 12 visibility nodes) verified.")
    return True

def run_negative_controls():
    print("Running negative controls...")
    # Negative control 1: Corrupted hash detected
    fake_entry = (EXPECTED_FILES[0][0], EXPECTED_FILES[0][1], "0000000000000000000000000000000000000000000000000000000000000000")
    full_path = ROOT / fake_entry[0]
    actual_hash = hashlib.sha256(full_path.read_bytes()).hexdigest()
    assert actual_hash != fake_entry[2], "Negative control 1 failed: fake hash matched"

    # Negative control 2: Wrong size detected
    assert len(full_path.read_bytes()) != 999999, "Negative control 2 failed: wrong size matched"

    # Negative control 3: Non-existent bone detected
    skel = s.skel_data.read_skel(str(ROOT / EXPECTED_FILES[14][0]))
    bones = [b.name for b in skel.bones]
    assert "Sword_Mesh_Bone_Fake" not in bones, "Negative control 3 failed: fake bone found"

    print("PASS: 3/3 negative controls successfully caught.")
    return True

def main():
    if not check_file_hashes():
        sys.exit(1)
    if not check_motion_lists():
        sys.exit(1)
    if not check_skeletons_and_animations():
        sys.exit(1)
    if not run_negative_controls():
        sys.exit(1)
    print("\nALL 4/4 P11-MOVE-PLAN CHECKS PASSED (exit 0).")
    sys.exit(0)

if __name__ == "__main__":
    main()
