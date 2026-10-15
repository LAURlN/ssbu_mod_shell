#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""check_p14_sword_facts.py - evidence check for research/P14-SWORD-FACTS.md (task P14).

Everything the report marks (B) is re-read from the hashed game files here.

Modes:
  (none)     run all groups; exit 0 when every check matched, 1 otherwise
             (at most 3 failures printed per group)
  --neg      negative controls: deliberately wrong expectations, each of which must
             be DETECTED as a mismatch; prints one line per control; exits 1
  --selftest helper functions against known vectors, in-process; exit 0/1
"""
import argparse
import csv
import hashlib
import os
import re
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
GD = os.path.join(WS, "gamedata", "mii_customizer", "P14-SWORD-FACTS")
T = os.path.join(GD, "tables")
REPORT = os.path.join(WS, "mods", "mii_customizer", "research", "P14-SWORD-FACTS.md")
ARC = os.path.join(WS, "mods", "ssbu_mod_new", "dumps", "decoded", "arc_files.tsv")
PARAM = os.path.join(WS, "mods", "ssbu_mod_new", "dumps", "scripts", "ParamLabels.csv")
MLIST_DIR = os.path.join(WS, "mods", "ssbu_mod_new", "src", "pgwr", "tools")
NRO_DIR = os.path.join(GD, "prebuilt;", "nro", "release")
NRO_M = os.path.join(NRO_DIR, "lua2cpp_miiswordsman.nro")
NRO_G = os.path.join(NRO_DIR, "lua2cpp_miigunner.nro")
NRO_C = os.path.join(NRO_DIR, "lua2cpp_common.nro")
EFF_M = os.path.join(GD, "effect", "fighter", "miiswordsman", "ef_miiswordsman.eff")
EFF_G = os.path.join(GD, "effect", "fighter", "miigunner", "ef_miigunner.eff")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for blk in iter(lambda: f.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()


def hash40(name):
    b = name.encode("utf-8")
    return (len(b) << 32) | zlib.crc32(b)


def word(buf, off):
    return int.from_bytes(buf[off:off + 4], "little")


def bl_target(buf, off):
    w = word(buf, off)
    if (w >> 26) != 0x25:
        raise ValueError("not a bl at 0x%x" % off)
    imm = w & 0x03FFFFFF
    if imm & 0x2000000:
        imm -= 0x4000000
    return (off + imm * 4) & 0xFFFFFFFF


def mov_triple(buf, off):
    """movz + movk + movk building a 64-bit constant; None if the words do not match."""
    v = None
    for i in range(3):
        w = word(buf, off + 4 * i)
        imm16 = (w >> 5) & 0xFFFF
        hw = (w >> 21) & 3
        if i == 0:
            if (w & 0xFF800000) != 0xD2800000:
                return None
            v = imm16 << (hw * 16)
        else:
            if (w & 0xFF800000) != 0xF2800000:
                return None
            v |= imm16 << (hw * 16)
    return v


def encode_mov_triple(value):
    """Inverse of mov_triple (selftest): (movz, movk16, movk32) words for x1."""
    w0 = 0xD2800000 | ((value & 0xFFFF) << 5) | 1
    w1 = 0xF2800000 | (((value >> 16) & 0xFFFF) << 5) | (1 << 21) | 1
    w2 = 0xF2800000 | (((value >> 32) & 0xFFFF) << 5) | (2 << 21) | 1
    return [w0, w1, w2]


def scan_mov_hashes(buf, target):
    """Whole-file scan for movz+movk+movk triples building `target` (q2 method)."""
    hits = []
    n = len(buf)
    for off in range(0, n - 12, 4):
        w = int.from_bytes(buf[off:off + 4], "little")
        if (w & 0xFF800000) != 0xD2800000:
            continue
        v = ((w >> 5) & 0xFFFF) << (((w >> 21) & 3) * 16)
        ok = True
        for k in (1, 2):
            w2 = int.from_bytes(buf[off + 4 * k:off + 4 * k + 4], "little")
            if (w2 & 0xFF800000) != 0xF2800000:
                ok = False
                break
            v |= ((w2 >> 5) & 0xFFFF) << (((w2 >> 21) & 3) * 16)
        if ok and v == target:
            hits.append(off)
    return hits


# ---------------------------------------------------------------- checking
RESULTS = {}  # group -> list of (name, ok, expected, actual)


def _fmt(x):
    r = repr(x)
    return r if len(r) <= 160 else r[:157] + "..."


def check(group, name, actual, expected):
    ok = actual == expected
    RESULTS.setdefault(group, []).append((name, ok, expected, actual))
    return ok


def check_close(group, name, actual, expected, tol):
    try:
        ok = len(actual) == len(expected) and all(
            abs(float(a) - float(e)) <= tol for a, e in zip(actual, expected))
    except Exception:
        ok = False
    RESULTS.setdefault(group, []).append((name, ok, list(expected), list(actual)))
    return ok


def guard(group, fn):
    try:
        fn()
    except Exception as exc:  # a crash inside a group is a failure, not a pass
        RESULTS.setdefault(group, []).append(
            ("group execution", False, "no exception", "%s: %s" % (type(exc).__name__, exc)))


# ---------------------------------------------------------------- pins
# sha256 (and size where known) of every file the report cites. Constants are pinned
# from this task's runs; they are NOT read back from the tables.
_H = "b22c52a0ba2a9d5be39bf81db2cb9c1e09983d955a1acc13390120693db514f6"
_SN = "e0407f6169cc77262957e22c55882b7a4d6b66733c9d55e5391d02059a90ea42"
PIN_FILES = {
    "fighter/miiswordsman/model/b_normalswordman_m/c00/model.numshb": (795216, _H),
    "fighter/miiswordsman/model/b_normalswordman_m/c00/model.nusktb": (20160, _SN),
    "fighter/miiswordsman/model/b_normalswordman_m/c00/model.numshexb": (
        688, "d76a97c1207abafc4ba6c4bc9df3b843a880791828c1ae92057251f8d7595e5c"),
    "fighter/miiswordsman/model/b_normalswordman_m/c00/model.numatb": (
        2188, "0c662518ca4f726779c1908fb2b68e267849ec1d7a964f4c6aad5eab62839c77"),
    "fighter/miiswordsman/model/b_normalswordman_f/c00/model.numshb": (
        755312, "dc332f9c1365a5297a61b4ed233eda3c19efd0e951d11da3f48499338b956f5b"),
    "fighter/miiswordsman/model/b_normalswordman_f/c00/model.nusktb": (20160, _SN),
    "fighter/miiswordsman/model/b_normalswordman_f/c00/model.numshexb": (
        576, "b4b774470d4bc34bfab50a10de7eed2fbbfce4a77b5f190bce0f82d28312dd22"),
    "fighter/miigunner/model/b_normalgunner_m/c00/model.numshb": (
        394456, "416354380e984f07b67c9173df4df0c4f62ac262ff899e7e0297371bbfbee145"),
    "fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb": (
        20160, "1d66b6d1cc4ce3b1c0883a21194cf998531c4a92ccb1c6561f69e68fd671429d"),
    "fighter/miigunner/model/b_normalgunner_m/c00/model.numshexb": (
        336, "2f26ef4fe71c2e4a2e7c2d4cd8395ece81a2e20ac8ee9282fcb67d348f48bec4"),
    "fighter/miigunner/model/b_normalgunner_m/c00/model.numatb": (
        2548, "2ccf5a14338788715ac97e309f5b07fc1cbc2253ee2e4c1ad440f266a1a1448d"),
    "fighter/miigunner/model/b_normalgunner_f/c00/model.numshb": (
        397160, "e63c36a1dcb6fdae21d621404e25af816a3e7d121c9961a0d6e64549d52350b2"),
    "fighter/miigunner/model/b_normalgunner_f/c00/model.nusktb": (
        20160, "43f13756fb0fd5bed5dd37206e060818fc5bcd0ff7d99ae47b8419816ba4ed33"),
    "fighter/miigunner/model/b_normalgunner_f/c00/model.numshexb": (
        336, "df01add204abfdf89b034e6230b385b26e375433a8223daee2cec927d4995401"),
    "effect/fighter/miiswordsman/ef_miiswordsman.eff": (
        15888896, "6bcb258c77591ddd516777bb9cdd78543fe5074f5a89bebb65c836930f6a720c"),
    "effect/fighter/miigunner/ef_miigunner.eff": (
        20034240, "9f27743cf9971ae60d0611eedd5d8a0060dcf04600bab1b5b483312ac688fb90"),
    "effect/fighter/miiswordsman/trail/tex_miiswordsman_sword01.nutexb": (
        176816, "8001eb5466288f6f603225d12450ed7fb440b78c4b5cdd40894bc7b6cb208972"),
    "effect/fighter/miiswordsman/trail/tex_miiswordsman_sword03.nutexb": (
        89264, "2014944d4dd0b009c0fcb2ff2ac060f155060b6cd320177b150f78f9388ec515"),
    "effect/fighter/miiswordsman/trail/tex_miiswordsman_sword70.nutexb": (
        89264, "a48feb9175b3d877a9fa3edd0e82ba6f464df7d7894e3a6ab0bd9db7558c74a4"),
    "prebuilt;/nro/release/lua2cpp_miiswordsman.nro": (
        2101248, "30aad5f5374b3577b581347323d82f0d82af92b9c58d42b2f4589d932253a127"),
    "prebuilt;/nro/release/lua2cpp_miigunner.nro": (
        1662976, "64ec160d90eb97680266710155481c8baab1688ad98e890942be525c2007330c"),
    "prebuilt;/nro/release/lua2cpp_common.nro": (
        8466432, "43876f961a80e413370629d32c23af9de6e4cc26b448bab88d5433714a566097"),
    "fighter/miiswordsman/motion/body/c00/motion_list.bin": (
        45696, "9692b79ea80dba9abf64da65dbfa2ce064eab912572f06841cf2902a4f41027a"),
    "fighter/miiswordsman/motion/body/c00/c00attack11.nuanmb": (
        32824, "069b485743b00ef50a54386221bd8e48b578c2421962366ea52e4c5cddf0fd8d"),
    "fighter/miiswordsman/motion/body/c00/c01attacks3s.nuanmb": (
        35320, "39bf0dff673825b1dde3755c3f8fea2126075ceb556d9367d04e4c2b3d2abaee"),
    "fighter/miiswordsman/model/b_normalswordman_m/c00/def_normalswordman_m_001_col.nutexb": (
        1400496, "5b6865ece02041d55f46ea995a45e8d43b106056e21d06b408b26b1dff16580a"),
    "fighter/miiswordsman/model/b_normalswordman_m/c00/def_normalswordman_m_001_nor.nutexb": (
        1400496, "74830c2f84272c97861d822cc4406b70df7c2eb6ec58e06f95ac7e008cca403c"),
    "fighter/miiswordsman/model/b_normalswordman_m/c00/def_normalswordman_m_001_prm.nutexb": (
        351920, "e8a6c32db39a14c8d634137dc2161eba5c7f04f453f35749b886ac52934e3be1"),
    "fighter/miiswordsman/model/b_normalswordman_m/c00/metal_normalswordman_m_001_col.nutexb": (
        1400496, "ea3bb0b3c03c7607ddf4ef67b92e172f3836f2cb01be14490bbb2dd3d3872227"),
    "fighter/miiswordsman/model/b_normalswordman_m/c00/metal_normalswordman_m_001_nor.nutexb": (
        1400496, "408724b00fd43b35c3b917d3a527dcfcd4dce8f2effa65c987b68ca0a9b2861a"),
    "fighter/miiswordsman/model/b_normalswordman_m/c00/metal_normalswordman_m_001_prm.nutexb": (
        351920, "b6eba6b3a9b6a078c07289b3b07fc62072711265f5ac46f1287189f0cacb267c"),
    "fighter/miigunner/model/b_normalgunner_m/c00/def_normalgunner_m_001_emi.nutexb": (
        177328, "0f7819a1a79162c55673fe1d184b4f82aa27e032162e9a905c78f2377fee1d06"),
    "fighter/miigunner/model/b_normalgunner_m/c00/metal_normalgunner_m_001_emi.nutexb": (
        177328, "0be2cc4542cd11b2ccd49b35bf6fff316598c1c43c82d6a1c8fc3d8faddc34d9"),
}
# the 12 byte-identical default-costume slots (size known, one shared sha)
for _slot in range(12):
    PIN_FILES["fighter/miiswordsman/model/b_normalswordman_m/c%02d/model.numshb"
              % _slot] = (795216, _H)
# 8 sampled alternate-costume models (sha from the run; sizes covered by the inventory)
for _rel, _sha in [
    ("b_chrom_m", "279c990567f3e82657eea0e6bdbbb1f3a0d953c254b8eefe546504232e48f21a"),
    ("b_dunban_m", "22f3962766f84edf58d5b8843db2ce92cd647ab42dc4d9fc0b87f0029e9ae0d5"),
    ("b_link_m", "ce02ab9f345613d6f5e75cb667e7852f2c6f7427542d9e3322e3cf36b0d3d6e4"),
    ("b_lip_f", "f46f06b0f6897a97d0319691ebfff5e3b58260bd32548d18dbf44c3798d16185"),
    ("b_pirate_m", "4862032318ca0b7fb8f6fb4e531d71850c6d448774fd74fc8a6c36e31fd5f5fd"),
    ("b_robin_m", "bc2fd2cf0b445c5ac46d6e99fe11c46c058e7c7099d6d5d65b732a96d5871c4c"),
    ("b_takamaru_m", "899d7ee45fcbb2a0b60f6aff55bc6562087d215b56898d46ed77b8b7ca105596"),
    ("b_zero_m", "f08f1735f2bbf661dbd0738ca1c156850e6acb152452627d2b123e8c16701685"),
]:
    PIN_FILES["fighter/miiswordsman/model/%s/c00/model.numshb" % _rel] = (None, _sha)

# cited instruction words and bl targets in lua2cpp_miiswordsman.nro (file offsets;
# the flattened .text image coincides with the file offsets in this NRO - the offsets
# below were verified against both)
PIN_MOV = [(0xD9F94, 0x59AE5C70F),    # hash40("sword") built in expression_lose
           (0xD9FA8, 0xAB4F18A85),    # hash40("sword_hide")
           (0x15B498, 0x31ED91FCA),   # hash40("top") bone arg in game_attack11
           (0x15B634, 0x14860B063A)]  # hash40("collision_attr_cutup")
PIN_WORDS = [(0xD9F94, 0xD298E1E1), (0xD9F98, 0xF2B35CA1), (0xD9F9C, 0xF2C000A1),
             (0xD9FA8, 0xD29150A1), (0xD9FAC, 0xF2B69E21), (0xD9FB0, 0xF2C00141),
             (0x15B498, 0xD283F941), (0x15B49C, 0xF2A3DB21), (0x15B4A0, 0xF2C00061),
             (0x15B634, 0xD280C741), (0x15B638, 0xF2B0C161), (0x15B63C, 0xF2C00281)]
PIN_BL = [(0xD9FDC, 0x192540),   # set_int64 plt slot
          (0xD9FA4, 0x191540),   # L2CValue(Hash40) ctor for "sword"
          (0xD9FB8, 0x191540),   # ... for "sword_hide"
          (0xBE0E8, 0x191F90),   # registration bl of expression_lose
          (0x15B4A8, 0x191540),  # ctor for "top" in game_attack11
          (0x15B748, 0x10FE20)]  # sv_animcmd::ATTACK thunk in game_attack11
PIN_SCAN = {"sword": [0xD9F94], "sword_hide": [0xD9FA8]}  # in miiswordsman; 0 hits in
                                                            # miigunner and common

# mesh pins: (name, parent, vertex_positions, vertex_indices_len, n_bone_influences)
PIN_MESH = {
    "swordman_m": [("GamemodelShape", "", 1296, 5700, 44),
                   ("miiswordsman_sheath_highShape", "Bust", 1128, 5376, 0),
                   ("miiswordsman_sheath_lowShape", "Bust", 826, 3768, 0),
                   ("MiiS_Sword_VIS_O_OBJShape", "HaveR", 686, 2868, 0),
                   ("body_highShape", "", 5539, 26946, 27),
                   ("body_highShape", "", 1477, 6768, 8),
                   ("body_lowShape", "", 3974, 18036, 27),
                   ("body_lowShape", "", 852, 3684, 8)],
    "swordman_f": [("GamemodelShape", "", 1296, 5700, 44),
                   ("miiswordsman_sheathShape", "Bust", 1128, 5376, 0),
                   ("MiiS_Sword_VIS_O_OBJShape", "HaveR", 686, 2868, 0),
                   ("body_highShape", "", 5544, 26946, 27),
                   ("body_highShape", "", 1476, 6768, 8),
                   ("body_lowShape", "", 3936, 17898, 27),
                   ("body_lowShape", "", 853, 3678, 8)],
    "gunner_m": [("GamemodelShape", "", 6081, 28602, 44),
                 ("buckleShape", "", 153, 648, 2),
                 ("gunShape", "ArmR", 1597, 6264, 0)],
    "gunner_f": [("GamemodelShape", "", 6100, 28764, 46),
                 ("buckleShape", "", 153, 648, 2),
                 ("gunShape", "ArmR", 1597, 6264, 0)],
}
PIN_MESHEX = {
    "swordman_m": ["Gamemodel", "miiswordsman_sheath_high", "miiswordsman_sheath_low",
                   "MiiS_Sword", "body_high", "body_low"],
    "gunner_m": ["Gamemodel", "buckle", "gun"],
}
PIN_SPHERE = {  # (center, radius) of two groups, model-numshexb values
    ("swordman_m", "MiiS_Sword"): (0.0002, 3.9585, 0.0015, 5.7277),
    ("gunner_m", "gun"): (2.9166, -0.0010, 0.3313, 2.7835),
}

# Q6 family table: family -> (n_kinds, n_scripts, bone, eff, vis)
PIN_FAMILIES = {
    "aerial": (5, 11, 11, 5, 1),
    "jab": (3, 6, 6, 3, 0),
    "other-normal": (1, 2, 2, 1, 0),
    "other/state": (46, 49, 20, 46, 3),
    "smash": (4, 5, 3, 3, 2),
    "special": (50, 83, 49, 41, 29),
    "tilt": (3, 5, 5, 3, 0),
}

FACIAL = ("MiiFighterM_eye_ANGER", "MiiFighterM_eye_BLINK", "MiiFighterM_eye_FRUSTRATED",
          "MiiFighterM_eye_NORMAL", "MiiFighterM_eye_SMILE", "MiiFighterM_eye_SORROW",
          "MiiFighterM_eye_SURPRISE", "MiiFighterM_eye_WINK_LEFT",
          "MiiFighterM_eye_WINK_RIGHT", "MiiFighterM_mouth_CLOSE",
          "MiiFighterM_mouth_LIKE", "MiiFighterM_mouth_OPEN")

REPORT_ANCHORS = [
    "Status: DONE", "b22c52a0ba2a", "dc332f9c1365", "416354380e98", "e0407f6169cc",
    "9f27743cf997", "6bcb258c7759", "30aad5f5374b", "9692b79ea80d", "0xd9fdc",
    "0x31ed91fca", "expression_lose", "set_int64", "AFTER_IMAGE4_ON_WORK",
    "tex_miiswordsman_sword01..70", "(0.995895, 0.01364, 0)", "(1.35, 0.15, 0)",
    "590,711", "-8.106", "acmd_calls 80890", "file_inventory 265",
    "216 classified scripts", "402…3,666", "ef_miiswordsman.eff",
    "71 bones", "No recommendation is made",
]

# ---------------------------------------------------------------- groups
MODELS = {
    "swordman_m": "fighter/miiswordsman/model/b_normalswordman_m/c00",
    "swordman_f": "fighter/miiswordsman/model/b_normalswordman_f/c00",
    "gunner_m": "fighter/miigunner/model/b_normalgunner_m/c00",
    "gunner_f": "fighter/miigunner/model/b_normalgunner_f/c00",
}
COSTUMES = ["b_chrom_m", "b_dunban_m", "b_link_m", "b_lip_f",
            "b_pirate_m", "b_robin_m", "b_takamaru_m", "b_zero_m"]


def _tsv(name):
    with open(os.path.join(T, name), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def g_inventory():
    rows = _tsv("file_inventory.tsv")
    check("inventory", "row count", len(rows), 265)
    for r in rows:
        p = os.path.join(GD, r["path"])
        if not os.path.isfile(p):
            check("inventory", r["path"], "MISSING", "present+hashed")
            continue
        check("inventory", r["path"], (os.path.getsize(p), sha256(p)),
              (int(r["bytes"]), r["sha256"]))


def g_pins():
    inv = {r["path"]: r for r in _tsv("file_inventory.tsv")}
    check("pinned", "pin count >= 50", len(PIN_FILES) >= 50, True)
    for rel, (size, want) in sorted(PIN_FILES.items()):
        p = os.path.join(GD, rel)
        if not os.path.isfile(p):
            check("pinned", rel, "MISSING", want)
            continue
        got = sha256(p)
        check("pinned", rel, got, want)
        if size is not None:
            check("pinned", rel + " size", os.path.getsize(p), size)
        if rel in inv:
            check("pinned", rel + " agrees with inventory",
                  (got, os.path.getsize(p)),
                  (inv[rel]["sha256"], int(inv[rel]["bytes"])))


def g_instructions():
    d = open(NRO_M, "rb").read()
    for off, want in PIN_MOV:
        check("instructions", "mov triple @0x%x" % off, mov_triple(d, off), want)
    for off, want in PIN_WORDS:
        check("instructions", "word @0x%x" % off, word(d, off), want)
    for off, want in PIN_BL:
        check("instructions", "bl @0x%x -> 0x%x" % (off, want), bl_target(d, off), want)
    for path, want in ((NRO_M, PIN_SCAN),
                       (NRO_G, {"sword": [], "sword_hide": []}),
                       (NRO_C, {"sword": [], "sword_hide": []})):
        buf = open(path, "rb").read()
        for nm, offs in sorted(want.items()):
            check("instructions", "%s whole-file scan %s"
                  % (os.path.basename(path), nm),
                  scan_mov_hashes(buf, hash40(nm)), offs)
    # hash40 vectors cited in the report
    for nm, val in (("sword", 0x59AE5C70F), ("sword_hide", 0xAB4F18A85),
                    ("top", 0x31ED91FCA), ("collision_attr_cutup", 0x14860B063A),
                    ("expression_lose", 0xFC95C070A), ("haver", 0x51A07C0E7)):
        check("instructions", "hash40(%s)" % nm, hash40(nm), val)


def g_mesh():
    import ssbh_data_py as S

    def objs(path):
        out = []
        for o in S.mesh_data.read_mesh(path).objects:
            pos = o.positions
            arr = pos[0].data if isinstance(pos, list) else pos.data
            bi = o.bone_influences
            n_inf = bi if isinstance(bi, int) else len(bi)
            out.append((o.name, o.parent_bone_name or "", len(arr),
                        len(o.vertex_indices), n_inf))
        return out

    for tag, rel in MODELS.items():
        check("mesh", tag + " objects", objs(os.path.join(GD, rel, "model.numshb")),
              PIN_MESH[tag])
    for tag in ("swordman_m", "gunner_m"):
        rel = MODELS[tag]
        mx = S.meshex_data.read_meshex(os.path.join(GD, rel, "model.numshexb"))
        check("mesh", tag + " meshex groups",
              [g.mesh_object_name for g in mx.mesh_object_groups], PIN_MESHEX[tag])
        for g in mx.mesh_object_groups:
            key = (tag, g.mesh_object_name)
            if key in PIN_SPHERE:
                c = g.bounding_sphere.center
                got = (round(float(c[0]), 4), round(float(c[1]), 4),
                       round(float(c[2]), 4), round(float(g.bounding_sphere.radius), 4))
                check("mesh", "%s sphere %s" % (tag, g.mesh_object_name), got, PIN_SPHERE[key])
    # alternate costumes: the sword object exists on HaveR in every sampled model
    for cdir in COSTUMES:
        path = os.path.join(GD, "fighter", "miiswordsman", "model", cdir, "c00",
                            "model.numshb")
        swords = [t for t in objs(path) if t[0] == "MiiS_Sword_VIS_O_OBJShape"]
        check("mesh", cdir + " sword object on HaveR",
              [(t[0], t[1]) for t in swords],
              [("MiiS_Sword_VIS_O_OBJShape", "HaveR")] * len(swords) if swords else "absent")
    rob = objs(os.path.join(GD, "fighter/miiswordsman/model/b_robin_m/c00/model.numshb"))
    check("mesh", "robin sword (positions, vertex_indices)",
          [(t[2], t[3]) for t in rob if t[0] == "MiiS_Sword_VIS_O_OBJShape"], [(151, 402)])
    check("mesh", "robin sheath",
          [(t[0], t[1], t[2], t[3]) for t in rob if t[0] == "swordsheathShape"],
          [("swordsheathShape", "Bust", 56, 228)])
    zer = objs(os.path.join(GD, "fighter/miiswordsman/model/b_zero_m/c00/model.numshb"))
    check("mesh", "zero has two sword objects",
          sorted((t[2], t[3]) for t in zer if t[0] == "MiiS_Sword_VIS_O_OBJShape"),
          [(189, 882), (340, 924)])


def g_bones():
    import ssbh_data_py as S

    skels = {t: S.skel_data.read_skel(os.path.join(GD, r, "model.nusktb"))
             for t, r in MODELS.items()}
    names = {t: [b.name for b in sk.bones] for t, sk in skels.items()}
    for t in MODELS:
        check("bones", t + " bone count", len(names[t]), 71)
    for t in ("swordman_f", "gunner_m", "gunner_f"):
        check("bones", t + " bone names == swordman_m", names[t], names["swordman_m"])
        check("bones", t + " parent indices == swordman_m",
              [b.parent_index for b in skels[t].bones],
              [b.parent_index for b in skels["swordman_m"].bones])

    def key(b):
        tr = b.transform
        return tuple(round(float(tr[r][c]), 5) for r in range(4) for c in range(4))

    base = names["swordman_m"]
    diffs = [base[i] for i in range(71)
             if len({key(skels[t].bones[i]) for t in MODELS}) > 1]
    check("bones", "local rest diffs across four skeletons", len(diffs), 32)
    check("bones", "HaveR differs", "HaveR" in diffs, True)

    def local_t(tag, bone):
        b = skels[tag].bones[names[tag].index(bone)]
        return tuple(round(float(b.transform[3][c]), 6) for c in range(3))

    check_close("bones", "swordman_m HaveR local T",
                local_t("swordman_m", "HaveR"), (0.995895, 0.01364, 0.0), 1e-5)
    check_close("bones", "swordman_f HaveR local T",
                local_t("swordman_f", "HaveR"), (0.995895, 0.01364, 0.0), 1e-5)
    check_close("bones", "gunner_m HaveR local T",
                local_t("gunner_m", "HaveR"), (1.35, 0.15, 0.0), 1e-5)
    check_close("bones", "gunner_f HaveR local T",
                local_t("gunner_f", "HaveR"), (1.35, 0.15, 0.0), 1e-5)
    for bone in ("ShoulderR", "ArmR", "HandR"):
        check("bones", bone + " local equal (swordman_m vs gunner_m)",
              key(skels["gunner_m"].bones[names["gunner_m"].index(bone)]),
              key(skels["swordman_m"].bones[base.index(bone)]))

    def rest_world(sk):
        out = []
        for b in sk.bones:
            if b.parent_index is None:
                out.append([list(r) for r in b.transform])
            else:
                p = out[b.parent_index]
                t = b.transform
                out.append([[sum(t[i][k] * p[k][j] for k in range(4)) for j in range(4)]
                            for i in range(4)])
        return out

    worlds = {t: rest_world(sk) for t, sk in skels.items()}

    def world_t(tag, bone):
        m = worlds[tag][names[tag].index(bone)]
        return tuple(round(float(m[3][c]), 3) for c in range(3))

    check_close("bones", "swordman_m HaveR world T",
                world_t("swordman_m", "HaveR"), (-6.200, 9.611, 0.0), 0.002)
    check_close("bones", "gunner_m HaveR world T",
                world_t("gunner_m", "HaveR"), (-6.554, 9.475, 0.0), 0.002)
    check_close("bones", "swordman_m HandR world T",
                world_t("swordman_m", "HandR"), (-5.204, 9.625, 0.0), 0.002)
    check_close("bones", "gunner_m HandR world T",
                world_t("gunner_m", "HandR"), (-5.204, 9.625, 0.0), 0.002)

    # rest-pose AABBs (q4_geometry.py method: every 7th vertex, v @ world)
    import numpy as np

    def find_obj(path, name):
        for o in S.mesh_data.read_mesh(path).objects:
            if o.name == name:
                return o
        raise KeyError(name)

    def aabb(obj, world_mat, step=7):
        pos = obj.positions
        arr = pos[0].data if isinstance(pos, list) else pos.data
        sub = arr[::step]
        hom = np.hstack([sub, np.ones((len(sub), 1))])
        w = hom @ np.array(world_mat, dtype=float)
        return (tuple(round(float(v), 3) for v in w[:, :3].min(axis=0)),
                tuple(round(float(v), 3) for v in w[:, :3].max(axis=0)))

    cases = [
        ("sword_on_swordman_m", "swordman_m", "swordman_m",
         (-7.752, 9.333, -1.651), (-4.633, 9.930, 9.686)),
        ("sword_on_gunner_m", "swordman_m", "gunner_m",
         (-8.106, 9.196, -1.651), (-4.987, 9.794, 9.686)),
        ("sword_f_on_gunner_f", "swordman_f", "gunner_f",
         (-8.106, 9.196, -1.651), (-4.987, 9.794, 9.686)),
    ]
    sword_box = {}
    for case, src, host, lo_w, hi_w in cases:
        o = find_obj(os.path.join(GD, MODELS[src], "model.numshb"),
                     "MiiS_Sword_VIS_O_OBJShape")
        m = worlds[host][names[host].index("HaveR")]
        lo, hi = aabb(o, m)
        sword_box[case] = (lo, hi)
        check_close("bones", case + " sword AABB lo", lo, lo_w, 0.005)
        check_close("bones", case + " sword AABB hi", hi, hi_w, 0.005)
    for host in ("gunner_m", "gunner_f"):
        o = find_obj(os.path.join(GD, MODELS[host], "model.numshb"), "gunShape")
        m = worlds[host][names[host].index("ArmR")]
        lo, hi = aabb(o, m)
        check_close("bones", host + " gun AABB lo", lo, (-8.951, 8.182, -1.574), 0.005)
        check_close("bones", host + " gun AABB hi", hi, (-3.968, 11.794, 1.628), 0.005)
        case = "sword_on_gunner_m" if host == "gunner_m" else "sword_f_on_gunner_f"
        sl, sh = sword_box[case]
        gaps = [round(min(sh[k], hi[k]) - max(sl[k], lo[k]), 3) for k in range(3)]
        check("bones", host + " sword/gun AABB overlap", all(g > 0 for g in gaps), True)
        check_close("bones", host + " per-axis intersection", gaps,
                    (3.120, 0.597, 3.202), 0.01)


def g_effects():
    donor = open(EFF_M, "rb").read().upper()
    gunner = open(EFF_G, "rb").read().upper()
    check("effects", "donor MIISWORDSMAN_SWORD matches", donor.count(b"MIISWORDSMAN_SWORD"), 109)
    check("effects", "gunner MIISWORDSMAN_SWORD matches", gunner.count(b"MIISWORDSMAN_SWORD"), 0)
    flags = {
        b"EF_MIISWORDSMAN_SWORD00": (True, False),
        b"MIISWORDSMAN_COUNTER_FLASH": (True, False),
        b"MIISWORDSMAN_RAPID_SLASH_ARC": (True, False),
        b"TEX_MIISWORDSMAN_SWORD03": (False, False),
        b"SYS_SMASH_FLASH": (False, False),
        b"BG_MIISWORDSMAN_FINAL": (False, False),
    }
    for nm, (want_d, want_g) in flags.items():
        label = nm.decode()
        check("effects", label + " in ef_miiswordsman", nm in donor, want_d)
        check("effects", label + " in ef_miigunner", nm in gunner, want_g)
    er = _tsv("effect_requests.tsv")
    check("effects", "effect_requests rows", len(er), 45)
    ms = [r for r in er if "miiswordsman" in r["effect_name"].lower()]
    check("effects", "requested names containing miiswordsman", len(ms), 14)
    check("effects", "of those flagged present in donor bank",
          sum(1 for r in ms if r["in_miiswordsman_eff"] == "True"), 9)
    tt = [r for r in er if r["kind"] == "trail-tex"]
    check("effects", "trail-tex requests", len(tt), 4)
    check("effects", "trail-tex absent from both banks",
          all(r["in_miiswordsman_eff"] == "False" and r["in_miigunner_eff"] == "False"
              for r in tt), True)
    check("effects", "total donor-bank flags", sum(1 for r in er if r["in_miiswordsman_eff"] == "True"), 11)
    check("effects", "total gunner-bank flags", sum(1 for r in er if r["in_miigunner_eff"] == "True"), 2)


def g_arc():
    with open(ARC, encoding="utf-8") as f:
        lines = [l.rstrip("\r\n") for l in f]
    check("arc", "line count", len(lines), 590711)
    trail = [p for p in lines
             if p.startswith("effect/fighter/miiswordsman/trail/tex_miiswordsman_sword")]
    check("arc", "tex_miiswordsman_sword* trail files", len(trail), 70)
    check("arc", "all trail files in the one miiswordsman trail dir",
          all(p.startswith("effect/fighter/miiswordsman/trail/") for p in trail), True)
    sub_m = {p.split("/")[3] for p in lines if p.startswith("fighter/miiswordsman/model/")}
    sub_g = {p.split("/")[3] for p in lines if p.startswith("fighter/miigunner/model/")}
    nonb_m = sorted(x for x in sub_m if not x.startswith("b_"))
    nonb_g = sorted(x for x in sub_g if not x.startswith("b_"))
    check("arc", "swordman model subdirs", len(sub_m), 54)
    check("arc", "swordman b_* costume dirs", sum(1 for x in sub_m if x.startswith("b_")), 53)
    check("arc", "swordman non-costume subdir", nonb_m, ["chakram"])
    check("arc", "gunner model subdirs", len(sub_g), 50)
    check("arc", "gunner b_* costume dirs", sum(1 for x in sub_g if x.startswith("b_")), 45)
    check("arc", "gunner article subdirs", nonb_g,
          ["fullthrottle", "grenadelauncher", "groundbomb", "miimissile", "supermissile"])
    for pat, want in (("fighter/miiswordsman/model/b_normalswordman_m/", 12),
                      ("fighter/miiswordsman/model/b_chrom_m/", 12),
                      ("fighter/miigunner/model/b_normalgunner_m/", 12)):
        slots = {p.split("/")[4] for p in lines if p.startswith(pat)}
        check("arc", pat + " colour slots", len(slots), want)
    check("arc", "effect/common paths", sum(1 for p in lines if p.startswith("effect/common/")), 0)
    check("arc", "ef_miiswordsman.eff in index",
          "effect/fighter/miiswordsman/ef_miiswordsman.eff" in lines, True)
    check("arc", "ef_miigunner.eff in index",
          "effect/fighter/miigunner/ef_miigunner.eff" in lines, True)
    check("arc", "gunner_m per-slot numshb paths",
          sum(1 for p in lines
              if re.fullmatch(r"fighter/miigunner/model/b_normalgunner_m/c\d+/model.numshb", p)),
          12)


def g_tables():
    import json
    from collections import Counter

    counts = {"file_inventory": 265, "acmd_scripts": 1061, "acmd_calls": 80890,
              "sword_scripts": 216, "visibility_sites": 51, "effect_requests": 45,
              "family_counts": 7, "motion_scripts": 765, "mesh_objects": 21,
              "skeleton_bones": 284, "rest_transform_diff": 71, "rest_aabb": 6,
              "meshex_groups": 17, "costume_sword_objects": 46, "materials": 8}
    for k, v in sorted(counts.items()):
        check("tables", k + " rows", len(_tsv(k + ".tsv")), v)
    tsvs = sorted(f for f in os.listdir(T) if f.endswith(".tsv"))
    check("tables", "tsv file count in tables/", len(tsvs), 16)
    check("tables", "superseded v1 sword_effects.tsv rows", len(_tsv("sword_effects.tsv")), 139)

    acmd = _tsv("acmd_scripts.tsv")
    check("tables", "acmd named registrations",
          sum(1 for r in acmd if not r["script"].startswith("0x")), 603)

    vs = _tsv("visibility_sites.tsv")
    c = Counter(r["target_short"].split("__")[1].split("_impl")[0]
                if "__" in r["target_short"] else r["target_short"] for r in vs)
    check("tables", "VisibilityModule::set_whole sites", c["set_whole"], 4)
    check("tables", "VisibilityModule::set_int64 sites", c["set_int64"], 1)
    check("tables", "ItemModule::set_have_item_visibility sites",
          c["set_have_item_visibility"], 46)
    check("tables", "... in scripts",
          len({r["script"] for r in vs if "set_have_item" in r["target_short"]}), 43)

    ss = _tsv("sword_scripts.tsv")
    check("tables", "sword_scripts named",
          sum(1 for r in ss if not r["script"].startswith("0x")), 161)
    check("tables", "sword_scripts with visibility",
          sum(1 for r in ss if r["visibility"]), 46)

    got = {r["family"]: (int(r["n_kinds"]), int(r["n_scripts"]),
                          int(r["scripts_with_sword_bone"]),
                          int(r["scripts_with_effect_request"]),
                          int(r["scripts_with_visibility"]))
           for r in _tsv("family_counts.tsv")}
    check("tables", "family counts (Q6)", got, PIN_FAMILIES)

    calls = _tsv("acmd_calls.tsv")
    vals = set()
    for r in calls:
        if r["script"] == "game_attack11" and "Hash40" in r["target"]:
            v = json.loads(r["args"]).get("x1")
            if isinstance(v, str) and not v.startswith("0x"):
                vals.add(v)
    check("tables", "game_attack11 hash40 constants", sorted(vals),
          ["collision_attr_cutup", "top"])
    int64 = [(int(r["addr"]), "sword_hide" in r["args"])
             for r in calls if r["script"] == "0x0fc95c070a" and "set_int64" in r["target"]]
    check("tables", "expression_lose set_int64 call site", int64, [(892892, True)])
    ae = sorted((r["script"], int(r["addr"])) for r in calls
                if "AFTER_IMAGE4_ON_WORK" in r["target"]
                and r["script"] in ("effect_attack11", "effect_attacks3"))
    check("tables", "afterimage sites of the two example moves", ae,
          [("effect_attack11", 744128), ("effect_attacks3", 731476)])

    # reparsed motion list (hash-pinned above; entry count is the reported claim)
    try:
        sys.path.insert(0, MLIST_DIR)
        import mlist
        ml = mlist.parse(os.path.join(GD, "fighter/miiswordsman/motion/body/c00/motion_list.bin"))
        entries = ml["entries"] if isinstance(ml, dict) else ml.entries
        check("tables", "motion_list entries (reparse)", len(entries), 765)
    except Exception as exc:
        check("tables", "motion_list entries (reparse)", "exception: %s" % exc, 765)


def g_animations():
    import ssbh_data_py as S

    def gtype(g):
        return int(getattr(g.group_type, "value", g.group_type))

    clips = [r["path"] for r in _tsv("file_inventory.tsv") if r["path"].endswith(".nuanmb")]
    check("animations", "clip count", len(clips), 96)
    nonfacial, empty, full = [], [], 0
    for p in clips:
        a = S.anim_data.read_anim(os.path.join(GD, p))
        vis = set()
        for g in a.groups:
            if gtype(g) == 2:
                vis |= {n.name for n in g.nodes}
        if not vis:
            empty.append(p)
        elif vis == set(FACIAL):
            full += 1
        else:
            nonfacial.append(p)
    check("animations", "clips with non-facial visibility nodes", nonfacial, [])
    check("animations", "clip with no visibility group", empty,
          ["fighter/miiswordsman/motion/body/c00/f04downattackd.nuanmb"])
    check("animations", "clips with exactly the 12 facial visibility nodes", full, 95)
    a = S.anim_data.read_anim(os.path.join(
        GD, "fighter/miiswordsman/motion/body/c00/c00attack11.nuanmb"))
    tr = {n.name for g in a.groups if gtype(g) == 1 for n in g.nodes}
    check("animations", "jab clip transform node count", len(tr), 75)
    check("animations", "jab clip transforms include HaveR", "HaveR" in tr, True)
    check("animations", "jab clip transforms have no 'top' node", "top" in tr, False)


def g_labels():
    want = ["0x051a07c0e7,haver", "0x059ae5c70f,sword",
            "0x0ab4f18a85,sword_hide", "0x031ed91fca,top"]
    have = set()
    with open(PARAM, encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if s in want:
                have.add(s)
    for s in want:
        check("labels", "ParamLabels row " + s, s in have, True)


def g_report():
    with open(REPORT, encoding="utf-8") as f:
        txt = f.read()
    for a in REPORT_ANCHORS:
        check("report", "anchor %r" % a, a in txt, True)


GROUPS = [("inventory", g_inventory), ("pinned", g_pins),
          ("instructions", g_instructions), ("mesh", g_mesh),
          ("bones", g_bones), ("effects", g_effects), ("arc", g_arc),
          ("tables", g_tables), ("animations", g_animations),
          ("labels", g_labels), ("report", g_report)]


def selftest():
    """Exercise the helper functions on known vectors, in-process."""
    n = 0
    failures = []

    def ok(cond, name):
        nonlocal n
        n += 1
        if not cond:
            failures.append(name)

    for nm, val in (("sword", 0x59AE5C70F), ("sword_hide", 0xAB4F18A85),
                    ("top", 0x31ED91FCA), ("collision_attr_cutup", 0x14860B063A),
                    ("expression_lose", 0xFC95C070A), ("haver", 0x51A07C0E7),
                    ("HaveR", 0x5E0A8CF2B)):
        ok(hash40(nm) == val, "hash40(%s)" % nm)
        ok(((val >> 32) & 0xFFFFFFFF) == len(nm), "hash40 length high bits (%s)" % nm)

    # movz/movk triple roundtrip on synthetic buffers
    for val in (0x59AE5C70F, 0xAB4F18A85, 0x0000000000000001, 0x00456789ABCDEF):
        buf = bytearray(64)
        for i, w in enumerate(encode_mov_triple(val)):
            buf[16 + 4 * i:20 + 4 * i] = int(w).to_bytes(4, "little")
        ok(mov_triple(bytes(buf), 16) == val, "mov triple roundtrip 0x%x" % val)

    # bl encode/decode roundtrip (sign-extended imm26)
    buf = bytearray(0x2008)
    for src, dst in ((0x1000, 0x5000), (0x1000, 0x0000)):
        imm = (dst - src) // 4
        w = 0x94000000 | (imm & 0x03FFFFFF)
        buf[src:src + 4] = int(w).to_bytes(4, "little")
        ok(bl_target(bytes(buf), src) == dst & 0xFFFFFFFF,
           "bl roundtrip 0x%x -> 0x%x" % (src, dst))

    # sha256 helper vs a single-shot read of the same file
    p = REPORT
    ok(os.path.isfile(p), "report exists for hashing")
    if os.path.isfile(p):
        single = hashlib.sha256(open(p, "rb").read()).hexdigest()
        ok(sha256(p) == single, "chunked sha256 == single-shot sha256")
    ok(sha256.__call__ is not None, "sha256 callable")

    # scan on a synthetic buffer containing one mov triple at a known offset
    buf = bytearray(128)
    for i, w in enumerate(encode_mov_triple(0x0AB4F18A85)):
        buf[64 + 4 * i:68 + 4 * i] = int(w).to_bytes(4, "little")
    ok(scan_mov_hashes(bytes(buf), 0x0AB4F18A85) == [64], "scan finds synthetic triple")
    ok(scan_mov_hashes(bytes(buf), 0x59AE5C70F) == [], "scan rejects absent value")

    if failures:
        print("selftest: %d checks, %d FAILED" % (n, len(failures)))
        for f in failures:
            print("  FAIL %s" % f)
        return 1
    print("selftest: %d checks OK" % n)
    return 0


def negative_controls():
    """Deliberately wrong expectations; each must be DETECTED as a mismatch."""
    results = []

    def control(i, desc, actual, wrong):
        detected = actual != wrong
        results.append(detected)
        print("neg%02d %-52s actual=%s -> %s"
              % (i, desc, _fmt(actual),
                 "detected" if detected else "NOT DETECTED - CHECK BROKEN"))

    try:
        import ssbh_data_py as S

        p = os.path.join(GD, "fighter/miiswordsman/model/b_normalswordman_m/c00",
                         "model.numshb")
        control(1, "file-hash pin (wrong sha256)", sha256(p), "0" * 64)

        d = open(NRO_M, "rb").read()
        control(2, "instruction-word pin (wrong hash40)",
                mov_triple(d, 0xD9F94), 0xAB4F18A85)

        mesh = S.mesh_data.read_mesh(p)
        sword = [o for o in mesh.objects if o.name == "MiiS_Sword_VIS_O_OBJShape"][0]
        control(3, "mesh-parent pin (wrong parent)", sword.parent_bone_name, "HandR")

        sk = S.skel_data.read_skel(os.path.join(GD, MODELS["gunner_m"], "model.nusktb"))
        control(4, "bone-count pin (wrong count)", len(sk.bones), 72)

        gunner_bank = open(EFF_G, "rb").read().upper()
        control(5, "effect-bank pin (claim present, actually absent)",
                b"MIISWORDSMAN_COUNTER_FLASH" in gunner_bank, True)

        with open(ARC, encoding="utf-8") as f:
            n_trail = sum(1 for l in f
                          if l.startswith("effect/fighter/miiswordsman/trail/"
                                          "tex_miiswordsman_sword"))
        control(6, "archive trail-count pin (wrong count)", n_trail, 69)

        jab = [r for r in _tsv("family_counts.tsv") if r["family"] == "jab"][0]
        control(7, "table-pin (wrong jab script count)", int(jab["n_scripts"]), 5)

        with open(REPORT, encoding="utf-8") as f:
            txt = f.read()
        control(8, "report-anchor pin (anchor absent)", "Status: DONE" in txt, False)
    except Exception as exc:
        print("neg: aborted with %s: %s" % (type(exc).__name__, exc))
        return 1

    n = len(results)
    detected = sum(results)
    print("negative controls: %d/%d detected (a bare --neg run exits 1)"
          % (detected, n))
    return 1


def main():
    ap = argparse.ArgumentParser(description="P14-SWORD-FACTS evidence check")
    ap.add_argument("--neg", action="store_true",
                    help="run negative controls; exits 1")
    ap.add_argument("--selftest", action="store_true",
                    help="run helper self-tests in-process")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.neg:
        return negative_controls()

    print("P14-SWORD-FACTS check_p14_sword_facts.py")
    for name, fn in GROUPS:
        guard(name, fn)
    total = fails = 0
    for name, _fn in GROUPS:
        rows = RESULTS.get(name, [])
        nf = sum(1 for _c, ok, _e, _a in rows if not ok)
        total += len(rows)
        fails += nf
        print("group %-12s %5d checks  %s"
              % (name, len(rows), ("FAIL %d" % nf) if nf else "ok"))
        if nf:
            shown = 0
            for cname, ok, exp, act in rows:
                if ok:
                    continue
                shown += 1
                if shown > 3:
                    print("    ... %d more failures in group %s" % (nf - 3, name))
                    break
                print("    FAIL %s: expected %s, got %s"
                      % (cname, _fmt(exp), _fmt(act)))
    print("TOTAL: %d checks, %d failures -> exit %d"
          % (total, fails, 1 if fails else 0))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
