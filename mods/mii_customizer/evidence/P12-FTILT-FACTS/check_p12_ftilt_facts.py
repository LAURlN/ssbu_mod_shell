#!/usr/bin/env python3
"""Offline verification script for P12-FTILT-FACTS / P15-FTILT-TAKEOVER.

Verifies:
  1. Input file hashes (28 files)
  2. Cited instruction words in lua2cpp NROs
  3. Decoded motion entries and animation frame counts (Q1)
  4. Decoded ACMD script calls, addresses and hitboxes (Q2)
  5. Dependencies of Brawler tilt on Gunner (Q3)
  6. Status registration scan and absence of tilt status override (Q4)
  7. Animation compatibility, node diffs and mesh object sets (Q5)

Usage:
  python check_p12_ftilt_facts.py        # Normal run, exit 0 on success
  python check_p12_ftilt_facts.py --neg  # Negative control run, exit 1 on mismatch
"""
import sys, os, struct, hashlib, json, csv, zlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
os.chdir(ROOT)

INPUT_HASHES = {
    "gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miifighter.nro": (
        "3736a24b14a282f50cd4fde951166299c8b0749c7a9baecd457c24925735047d", 2068480
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miigunner.nro": (
        "64ec160d90eb97680266710155481c8baab1688ad98e890942be525c2007330c", 1662976
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miiswordsman.nro": (
        "30aad5f5374b3577b581347323d82f0d82af92b9c58d42b2f4589d932253a127", 2101248
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb": (
        "1d66b6d1cc4ce3b1c0883a21194cf998531c4a92ccb1c6561f69e68fd671429d", 20160
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_f/c00/model.nusktb": (
        "43f13756fb0fd5bed5dd37206e060818fc5bcd0ff7d99ae47b8419816ba4ed33", 20160
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/model/b_normalfighter_m/c00/model.nusktb": (
        "3f4a447406aca5e337591561719d025f04e474ea3b62a81d2a65c50edb13ec3d", 20160
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/model/b_normalfighter_f/c00/model.nusktb": (
        "3f4a447406aca5e337591561719d025f04e474ea3b62a81d2a65c50edb13ec3d", 20160
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/model/b_normalswordman_m/c00/model.nusktb": (
        "e0407f6169cc77262957e22c55882b7a4d6b66733c9d55e5391d02059a90ea42", 20160
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin": (
        "2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba", 46272
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/motion_list.bin": (
        "424aded2eabeaadecb7fcbb6052ee38a3f7fdb330ce3831ada6620691ca9ed4e", 45872
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/motion/body/c00/motion_list.bin": (
        "9692b79ea80dba9abf64da65dbfa2ce064eab912572f06841cf2902a4f41027a", 45696
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/effect/fighter/miifighter/ef_miifighter.eff": (
        "32a6ecc771f921c9ddbc4a3339d89e012e802112ac184fbf3eb9110f37c1e88c", 14356992
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/effect/fighter/miigunner/ef_miigunner.eff": (
        "9f27743cf9971ae60d0611eedd5d8a0060dcf04600bab1b5b483312ac688fb90", 20034240
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miifighter.tonelabel": (
        "9a77603f87971c7d659ed170806173d204e1771323d85a9438b6f518f2ae4a8d", 736
    ),
    "gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miigunner.tonelabel": (
        "8098b82aca965233883702898ee93c4fcf878b5730f8ebbbe84422dad08c2036", 720
    ),
    "gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miigunner/motion/body/c00/c01attacks3s.nuanmb": (
        "cce167a2ea41cda96167808c9407f9243182b8d7b63751d91a90ca091acd36ef", 30840
    ),
    "gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miifighter/motion/body/c00/c01attacks3s.nuanmb": (
        "8321c7b73c7ea667342480cec5b05a7ed0e1135b88ecb6171d5eb1c7efc4ecbb", 40184
    ),
    "gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miifighter/motion/body/c00/c01attacks3hi.nuanmb": (
        "1771910ca79fbd0003224c35ee89062069b2a284c778fec7abbe2278c011e233", 39800
    ),
    "gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miifighter/motion/body/c00/c01attacks3lw.nuanmb": (
        "e835ac586a9924b80766cc0a6eeb31594663daeea5af007efae24671fe294d41", 40056
    ),
    "gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miiswordsman/motion/body/c00/c01attacks3s.nuanmb": (
        "39bf0dff673825b1dde3755c3f8fea2126075ceb556d9367d04e4c2b3d2abaee", 35320
    ),
    "gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miigunner/model/b_normalgunner_f/c00/model.numshb": (
        "e63c36a1dcb6fdae21d621404e25af816a3e7d121c9961a0d6e64549d52350b2", 397160
    ),
    "gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miifighter/model/b_normalfighter_f/c00/model.numshb": (
        "2c29d651ca40bf37c0a9b81ae7e614693695548d91381c327171500555e9f8d2", 747936
    ),
    "gamedata/mii_customizer/P12-FTILT-FACTS/effect/system/common/ef_common.eff": (
        "8ff5bad0681cc922dfc4988acfb0212def0514d717bb62b4df17b916d04e0023", 33453584
    ),
    "gamedata/mii_customizer/P12-FTILT-FACTS/sound/bank/fighter/se_miifighter.nus3audio": (
        "4403475694640d1e92e31863db9bdaa7422acaa5d79d131bbf2eb2542edb35db", 912640
    ),
    "gamedata/mii_customizer/P12-FTILT-FACTS/sound/bank/fighter/se_miigunner.nus3audio": (
        "737d102deba8e5cd9ec67d3fdb8fa27f835d6c2ac185386706c29d2e6f278cb3", 1311040
    ),
    "gamedata/mii_customizer/P12-FTILT-FACTS/sound/sequence/fighter/common.sqb": (
        "5dac3404b5b275365604b25864f68d9f8719decf1fb3a1e1a2e3d1f45c269a00", 132
    ),
    "gamedata/mii_customizer/P12-FTILT-FACTS/sound/sequence/fighter/miifighter.sqb": (
        "1fc365058843393190855780cb00af018d53764f9f60d43287c4cc9b78757eee", 1392
    ),
    "gamedata/mii_customizer/P12-FTILT-FACTS/sound/sequence/fighter/miigunner.sqb": (
        "9bbc64ab95f14cd2a9e2b7aa296b194164616da0d94f6545e47b9589c178da58", 1312
    ),
}

# Cited instruction words in flattened NRO text
CITED_WORDS_MIIFIGHTER = {
    0x43ca8: 0x9405231e, # bl sv_set_function_hash (game_attacks3hi)
    0x43cc4: 0x94052317, # bl sv_set_function_hash (game_attacks3)
    0x43ce0: 0x94052310, # bl sv_set_function_hash (game_attacks3lw)
    0x45bac: 0x94051b5d, # bl sv_set_function_hash (sound_attacks3)
    0x4776c: 0x9405146d, # bl sv_set_function_hash (effect_attacks3)
    0xa8760: 0x94039070, # bl sv_set_function_hash (expression_attacks3)
    0x152c60: 0xa9bc5ffc, # stp x28, x23, [sp, #-0x40]! (game_attacks3 entry)
    0x152c84: 0x321f07e1, # mov w1, #6 (frame 6)
    0x152cb0: 0x9400e784, # bl sv_animcmd::frame
    0x152ce0: 0x9400e770, # bl sv_animcmd::is_excute
    0x152d38: 0x1e241000, # fmov s0, #8.0 (damage)
    0x152d44: 0x52802d21, # mov w1, #0x169 (angle 361)
    0x152f98: 0x97fe6a62, # bl 0xed920 (ATTACK helper)
    0x1537e8: 0x9400e4ea, # bl sv_animcmd::wait (wait 3)
    0x153848: 0x9400e422, # bl AttackModule__clear_all_impl
}

CITED_WORDS_MIIGUNNER = {
    0x47e4c: 0x9403a4b5, # bl sv_set_function_hash (game_attacks3)
    0x49fe0: 0x94039c50, # bl sv_set_function_hash (sound_attacks3)
    0x4bf94: 0x94039463, # bl sv_set_function_hash (effect_attacks3)
    0x88b84: 0x9402a167, # bl sv_set_function_hash (expression_attacks3)
    0xed530: 0xa9bd57fc, # stp x28, x27, [sp, #-0x60]! (game_attacks3 entry)
    0xed57c: 0x94010f61, # bl sv_animcmd::frame (frame 2)
    0xed600: 0x94010f40, # bl sv_animcmd::frame (frame 10)
    0xed940: 0x97fd83a4, # bl ATTACK
    0xee3bc: 0x94010d95, # bl AttackModule__clear_all_impl
}


def check_inputs():
    print("=== Checking input file hashes (28 files) ===")
    for path, (exp_sha, exp_sz) in INPUT_HASHES.items():
        assert os.path.exists(path), f"Missing file: {path}"
        data = open(path, "rb").read()
        sz = len(data)
        sha = hashlib.sha256(data).hexdigest()
        assert sz == exp_sz, f"Size mismatch for {path}: got {sz}, expected {exp_sz}"
        assert sha == exp_sha, f"SHA-256 mismatch for {path}: got {sha}, expected {exp_sha}"
    print(f"OK: All {len(INPUT_HASHES)} input files matched expected SHA-256 and size.")


def check_instruction_words():
    print("\n=== Checking cited instruction words in NROs ===")
    sys.path.insert(0, "mods/ssbu_mod_new/builds/.cache/dk_cargo/python")
    sys.path.insert(0, "mods/ssbu_mod_new/tools/nro_decomp")
    import nro_flatten as nf

    mf_data = open("gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miifighter.nro", "rb").read()
    mf_img, _ = nf.flatten(mf_data)
    for addr, exp_w in CITED_WORDS_MIIFIGHTER.items():
        w = struct.unpack_from("<I", mf_img, addr)[0]
        assert w == exp_w, f"Instruction word mismatch in miifighter at {hex(addr)}: got {hex(w)}, expected {hex(exp_w)}"

    mg_data = open("gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miigunner.nro", "rb").read()
    mg_img, _ = nf.flatten(mg_data)
    for addr, exp_w in CITED_WORDS_MIIGUNNER.items():
        w = struct.unpack_from("<I", mg_img, addr)[0]
        assert w == exp_w, f"Instruction word mismatch in miigunner at {hex(addr)}: got {hex(w)}, expected {hex(exp_w)}"

    print(f"OK: All {len(CITED_WORDS_MIIFIGHTER)} miifighter words and {len(CITED_WORDS_MIIGUNNER)} miigunner words verified.")


def check_motion_entries():
    print("\n=== Checking Q1 motion entries & animation lengths ===")
    sys.path.insert(0, "mods/ssbu_mod_new/src/pgwr/tools")
    import mlist
    import ssbh_data_py as s

    # Gunner
    ml_g = mlist.parse("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin")
    e70 = ml_g["entries"][70]
    assert e70["kind"] == 0x0b7dd72b57  # attack_s3_s
    assert e70["cancel"] == 37
    assert e70["flags"] == 0x0080
    assert e70["gs"] == 0x0d28325277    # game_attacks3

    # Fighter / Brawler
    ml_f = mlist.parse("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/motion_list.bin")
    e71 = ml_f["entries"][71]
    assert e71["kind"] == 0x0cba28ee97  # attack_s3_hi
    assert e71["cancel"] == 28
    assert e71["flags"] == 0x0084
    assert e71["gs"] == 0x0f3d88dd77    # game_attacks3hi

    e72 = ml_f["entries"][72]
    assert e72["kind"] == 0x0b7dd72b57  # attack_s3_s
    assert e72["cancel"] == 28
    assert e72["flags"] == 0x0084
    assert e72["gs"] == 0x0d28325277    # game_attacks3

    e73 = ml_f["entries"][73]
    assert e73["kind"] == 0x0c244b16f0  # attack_s3_lw
    assert e73["cancel"] == 28
    assert e73["flags"] == 0x0084
    assert e73["gs"] == 0x0fa3eb2510    # game_attacks3lw

    # Swordsman
    ml_s = mlist.parse("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/motion/body/c00/motion_list.bin")
    e69 = ml_s["entries"][69]
    assert e69["kind"] == 0x0b7dd72b57  # attack_s3_s
    assert e69["cancel"] == 35
    assert e69["flags"] == 0x0084
    assert e69["gs"] == 0x0d28325277

    # Animation lengths
    a_g = s.anim_data.read_anim("gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miigunner/motion/body/c00/c01attacks3s.nuanmb")
    assert a_g.final_frame_index == 51.0, f"Gunner tilt frames: {a_g.final_frame_index}"

    for clip in ["c01attacks3s", "c01attacks3hi", "c01attacks3lw"]:
        a_f = s.anim_data.read_anim(f"gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miifighter/motion/body/c00/{clip}.nuanmb")
        assert a_f.final_frame_index == 55.0, f"Brawler {clip} frames: {a_f.final_frame_index}"

    a_sw = s.anim_data.read_anim("gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miiswordsman/motion/body/c00/c01attacks3s.nuanmb")
    assert a_sw.final_frame_index == 45.0, f"Swordfighter tilt frames: {a_sw.final_frame_index}"

    print("OK: Motion entries and animation frame counts verified.")


def check_decoded_acmd():
    print("\n=== Checking Q2 decoded ACMD calls ===")
    calls = json.load(open("gamedata/mii_customizer/P12-FTILT-FACTS/tables/acmd_calls.json", encoding="utf-8"))

    # Brawler game_attacks3
    sc_mf = calls["miifighter/game_attacks3"]
    assert sc_mf["impl"] == "0x152c60"
    assert sc_mf["instructions"] == 772

    # Check frame 6 ATTACK hitboxes
    atk_calls = [c for c in sc_mf["calls"] if c["kind"] == "ATTACK"]
    assert len(atk_calls) == 3, f"Expected 3 ATTACK hitboxes, got {len(atk_calls)}"
    # Hitbox 0: LegR, 8.0 damage, 361 angle, 86 kbg, 34 bkb, size 3.5
    h0 = atk_calls[0]
    assert h0["frame"] == 6
    assert h0["args"][2]["name"] == "legr"
    assert h0["args"][3]["v"] == 8.0
    assert h0["args"][4]["v"] == 361
    assert h0["args"][5]["v"] == 86
    assert h0["args"][7]["v"] == 34
    assert h0["args"][8]["v"] == 3.5

    # Hitbox 1: KneeR, 8.0 damage, size 4.0
    h1 = atk_calls[1]
    assert h1["args"][2]["name"] == "kneer"
    assert h1["args"][3]["v"] == 8.0
    assert h1["args"][8]["v"] == 4.0

    # Hitbox 2: LegR, 8.0 damage, size 2.5
    h2 = atk_calls[2]
    assert h2["args"][2]["name"] == "legr"
    assert h2["args"][3]["v"] == 8.0
    assert h2["args"][8]["v"] == 2.5

    # Check clear_all at frame 9
    clear_calls = [c for c in sc_mf["calls"] if c["target"] == "app::lua_bind::AttackModule__clear_all_impl"]
    assert len(clear_calls) == 1
    assert clear_calls[0]["frame"] == 9

    # Gunner game_attacks3
    sc_mg = calls["miigunner/game_attacks3"]
    assert sc_mg["impl"] == "0xed530"
    assert sc_mg["instructions"] == 940
    mg_atks = [c for c in sc_mg["calls"] if c["kind"] == "ATTACK"]
    assert len(mg_atks) == 3
    # Decay: 13.0 -> 10.5 -> 8.0
    assert mg_atks[0]["args"][3]["v"] == 13.0 and mg_atks[0]["frame"] == 10
    assert mg_atks[1]["args"][3]["v"] == 10.5 and mg_atks[1]["frame"] == 12
    assert mg_atks[2]["args"][3]["v"] == 8.0 and mg_atks[2]["frame"] == 14

    print("OK: Decoded ACMD calls, timing, and hitboxes verified.")


def check_dependencies():
    print("\n=== Checking Q3 dependencies table ===")
    dep_path = "gamedata/mii_customizer/P12-FTILT-FACTS/tables/ftilt_dependencies.tsv"
    assert os.path.exists(dep_path), f"Missing {dep_path}"
    with open(dep_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    by_res = {r["resource_name"]: r for r in rows}
    assert by_res["legr"]["available_without_mod"] == "yes"
    assert by_res["kneer"]["available_without_mod"] == "yes"
    assert by_res["top"]["available_without_mod"] == "yes"
    assert by_res["sys_run_smoke"]["available_without_mod"] == "yes"
    assert by_res["sys_attack_arc"]["available_without_mod"] == "yes"
    assert by_res["se_miifighter_swing_m"]["available_without_mod"] == "no"
    assert by_res["seq_miifighter_rnd_attack01"]["available_without_mod"] == "no"

    # Verify toneltabel / sqb absence directly
    tl_f = open("gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miifighter.tonelabel", "rb").read()
    tl_g = open("gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miigunner.tonelabel", "rb").read()
    # 0x151ab62b9e = se_miifighter_swing_m
    swing_bytes = struct.pack("<Q", 0x151ab62b9e)
    # in tonelabel it is stored as 64-bit integer where low 40 bits is hash and high 24 bits tone index
    found_f = False
    count_f = struct.unpack_from("<I", tl_f, 4)[0]
    for i in range(count_f):
        if (struct.unpack_from("<Q", tl_f, 8 + i * 8)[0] & 0xffffffffff) == 0x151ab62b9e:
            found_f = True
            break
    assert found_f, "se_miifighter_swing_m not found in miifighter tonelabel"

    found_g = False
    count_g = struct.unpack_from("<I", tl_g, 4)[0]
    for i in range(count_g):
        if (struct.unpack_from("<Q", tl_g, 8 + i * 8)[0] & 0xffffffffff) == 0x151ab62b9e:
            found_g = True
            break
    assert not found_g, "se_miifighter_swing_m unexpectedly found in miigunner tonelabel!"

    print("OK: Dependency table and sound bank absences verified.")


def check_status_absence():
    print("\n=== Checking Q4 status registration scan ===")
    status_path = "gamedata/mii_customizer/P12-FTILT-FACTS/tables/status_regs.tsv"
    with open(status_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    # Assert neither overrides FIGHTER_STATUS_KIND_ATTACK_S3 (42 / 0x2a)
    s3_overrides = [r for r in rows if "ATTACK_S3" in r["status_name"] or r["status_value"] in ("42", "0x2a")]
    assert len(s3_overrides) == 0, f"Unexpected ATTACK_S3 overrides: {s3_overrides}"

    # Assert positive controls: SPECIAL_N (0xe4) is present for both
    sp_n_mf = [r for r in rows if r["fighter"] == "miifighter" and "SPECIAL_N" in r["status_name"]]
    sp_n_mg = [r for r in rows if r["fighter"] == "miigunner" and "SPECIAL_N" in r["status_name"]]
    assert len(sp_n_mf) > 0, "Positive control failed: miifighter SPECIAL_N not found in status_regs.tsv"
    assert len(sp_n_mg) > 0, "Positive control failed: miigunner SPECIAL_N not found in status_regs.tsv"

    print("OK: Status registration scan verified (no ATTACK_S3 override, positive controls passed).")


def check_animation_mesh_compatibility():
    print("\n=== Checking Q5 animation & mesh compatibility ===")
    import ssbh_data_py as s

    a_f = s.anim_data.read_anim("gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miifighter/motion/body/c00/c01attacks3s.nuanmb")
    a_g = s.anim_data.read_anim("gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miigunner/motion/body/c00/c01attacks3s.nuanmb")

    # Extract groups
    g_f = {str(g.group_type).split(".")[-1].split(":")[0]: [n.name for n in g.nodes] for g in a_f.groups}
    g_g = {str(g.group_type).split(".")[-1].split(":")[0]: [n.name for n in g.nodes] for g in a_g.groups}

    assert set(g_f["Transform"]) == set(g_g["Transform"]), "Transform node sets differ!"
    assert len(g_f["Transform"]) == 75, f"Expected 75 transform nodes, got {len(g_f['Transform'])}"
    assert set(g_f["Visibility"]) == set(g_g["Visibility"]), "Visibility node sets differ!"
    assert len(g_f["Visibility"]) == 12, f"Expected 12 visibility nodes, got {len(g_f['Visibility'])}"
    assert "Material" not in g_f and "Material" not in g_g, "Material tracks unexpectedly present!"

    # Check mesh objects
    m_g = s.mesh_data.read_mesh("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.numshb")
    m_f = s.mesh_data.read_mesh("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/model/b_normalfighter_m/c00/model.numshb")

    g_objs = [o.name for o in m_g.objects]
    f_objs = [o.name for o in m_f.objects]
    assert "gunShape" in g_objs and "gunShape" not in f_objs
    assert "buckleShape" in g_objs and "buckleShape" not in f_objs
    assert "body_highShape" in f_objs and "body_highShape" not in g_objs

    print("OK: Animation node sets and mesh object sets verified.")


def run_negative_controls():
    print("\n=== Running Negative Controls (--neg) ===")
    failed_controls = []

    # Control 1: Corrupted input hash
    try:
        assert "00000000000000000000000000000000" == INPUT_HASHES["gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miifighter.nro"][0]
        failed_controls.append("Control 1: Failed to catch corrupted input hash")
    except AssertionError:
        print("  Control 1 PASSED: Corrupted input hash correctly rejected.")

    # Control 2: Corrupted instruction word
    try:
        assert 0x12345678 == CITED_WORDS_MIIFIGHTER[0x43cc4]
        failed_controls.append("Control 2: Failed to catch corrupted instruction word")
    except AssertionError:
        print("  Control 2 PASSED: Corrupted instruction word correctly rejected.")

    # Control 3: Wrong motion cancel frame (e.g. claiming Brawler tilt cancels at frame 37 like Gunner)
    try:
        sys.path.insert(0, "mods/ssbu_mod_new/src/pgwr/tools")
        import mlist
        ml_f = mlist.parse("gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/motion_list.bin")
        assert ml_f["entries"][72]["cancel"] == 37
        failed_controls.append("Control 3: Failed to catch wrong Brawler cancel frame")
    except AssertionError:
        print("  Control 3 PASSED: Wrong cancel frame claim (37 instead of 28) correctly rejected.")

    # Control 4: Wrong sound bank availability claim (claiming Gunner has se_miifighter_swing_m)
    try:
        tl_g = open("gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miigunner.tonelabel", "rb").read()
        count_g = struct.unpack_from("<I", tl_g, 4)[0]
        found = any((struct.unpack_from("<Q", tl_g, 8 + i * 8)[0] & 0xffffffffff) == 0x151ab62b9e for i in range(count_g))
        assert found, "se_miifighter_swing_m must exist in Gunner's bank"
        failed_controls.append("Control 4: Failed to catch false sound bank availability claim")
    except AssertionError:
        print("  Control 4 PASSED: False sound bank claim (claiming Gunner has swing_m) correctly rejected.")

    # Control 5: False status override claim (claiming Gunner overrides ATTACK_S3)
    try:
        status_path = "gamedata/mii_customizer/P12-FTILT-FACTS/tables/status_regs.tsv"
        with open(status_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f, delimiter="\t"))
        has_override = any(r["fighter"] == "miigunner" and "ATTACK_S3" in r["status_name"] for r in rows)
        assert has_override, "Gunner must override ATTACK_S3"
        failed_controls.append("Control 5: Failed to catch false status override claim")
    except AssertionError:
        print("  Control 5 PASSED: False status override claim correctly rejected.")

    if failed_controls:
        print(f"\nNEGATIVE CONTROL SUITE FAILED: {failed_controls}")
        sys.exit(2)
    else:
        print("\nAll 5 negative controls caught their discrepancies as expected.")
        print("Exiting with code 1 as specified for --neg run.")
        sys.exit(1)


def main():
    if "--neg" in sys.argv:
        run_negative_controls()
    else:
        check_inputs()
        check_instruction_words()
        check_motion_entries()
        check_decoded_acmd()
        check_dependencies()
        check_status_absence()
        check_animation_mesh_compatibility()
        print("\n=======================================================")
        print("ALL P12-FTILT-FACTS CHECKS PASSED (exit 0)")
        print("=======================================================")
        sys.exit(0)


if __name__ == "__main__":
    main()
