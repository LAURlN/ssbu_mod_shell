"""P12-INT-PARAMS step 4 (Q3): qualifying-field detail + extra-jump motions.

  python scratch/2026-10-07_P12-INT-PARAMS/q3_qualify.py

A. For each of the six qualifying i32 fields (int_table.json): Mii Gunner's
   value, min/max/distinct, and the full value -> fighters distribution.
B. Fighters with jump_count_max > 2, with their display label from
   gamedata/mii_customizer/P10-PRESET-WIDE/fighters.json.
C. Extra-jump motion evidence: decode the c00 body motion_list.bin of each
   fighter in group B plus two controls (mario, miigunner) from
   gamedata/ssbu-13.0.4/dk_cargo/fighter/<kind>/motion/body/c00/ and of
   Mii Gunner also from P1-DATASET's file (P1-CATALOG extraction), reporting:
     - sha256 of each motion_list.bin,
     - presence of jump motion KIND hashes (jump_squat, jump_f/b,
       jump_aerial_f/b, jump_aerial_f2/f3/b2/b3),
     - presence of jump ANIM hashes (a03jumpsquat, a03jumpf/b,
       a03jumpaerialf/b, a03jumpaerialf2/f3/b2/b3 .nuanmb).
   hash40(name) = (len<<32) | crc32(name) - the P1-CATALOG rule.
Read-only over game data; writes nothing.
"""
from __future__ import annotations

import hashlib
import json
import os
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "gamedata", "mii_customizer", "P11-INT-PARAMS")
FULL = os.path.join(ROOT, "gamedata", "mii_customizer", "P10-PRESET-WIDE",
                    "fighter_param_full.json")
FIGHTERS_JSON = os.path.join(ROOT, "gamedata", "mii_customizer",
                             "P10-PRESET-WIDE", "fighters.json")
DK = os.path.join(ROOT, "gamedata", "ssbu-13.0.4", "dk_cargo", "fighter")
GUNNER_P1 = os.path.join(ROOT, "gamedata", "mii_customizer", "P1-CATALOG",
                         "files", "fighter", "miigunner", "motion", "body",
                         "c00", "motion_list.bin")
GUNNER_P1_SHA = ("2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba")

KINDS = ["jump_squat", "jump_f", "jump_b", "jump_aerial_f", "jump_aerial_b",
         "jump_aerial_f2", "jump_aerial_f3", "jump_aerial_b2",
         "jump_aerial_b3"]
ANIMS = ["a03jumpsquat.nuanmb", "a03jumpf.nuanmb", "a03jumpb.nuanmb",
         "a03jumpaerialf.nuanmb", "a03jumpaerialb.nuanmb",
         "a03jumpaerialf2.nuanmb", "a03jumpaerialf3.nuanmb",
         "a03jumpaerialb2.nuanmb", "a03jumpaerialb3.nuanmb"]


def hash40(name: str) -> int:
    b = name.encode("utf-8")
    return (len(b) << 32) | zlib.crc32(b)


def decode_mlist(path):
    """Return (sha256, kind_hashes set, anim_hashes set) for a motion_list.bin."""
    data = open(path, "rb").read()
    sha = hashlib.sha256(data).hexdigest()
    magic, _motion_path, count = struct.unpack_from("<QQQ", data, 0)
    if magic != hash40("motion"):
        raise SystemExit("bad magic in %s" % path)
    off = 24
    kinds, anims = set(), set()
    for _ in range(count):
        kind, _gs, _flags, _blend, n, size = struct.unpack_from(
            "<QQHBBI", data, off)
        off += 24
        kinds.add(kind)
        for i in range(n):
            anims.add(struct.unpack_from("<Q", data, off + 8 * i)[0])
        off = (off + n * 9 + 3) & ~3
        off += size
    return sha, kinds, anims


def main():
    fails = []

    def check(cond, msg):
        print(("PASS  " if cond else "FAIL  ") + msg)
        if not cond:
            fails.append(msg)

    # ------------------------------------------------------------- A
    int_doc = json.load(open(os.path.join(OUT, "int_table.json"),
                             encoding="utf-8"))
    print("=== A. qualifying i32 fields: value distributions ===")
    qualifying = [r for r in int_doc["rows"] if r.get("qualifies")]
    check(len(qualifying) == 6, "six qualifying i32 fields (got %d)"
          % len(qualifying))
    jump_rec = None
    for r in qualifying:
        label = r["name"] or r["hash"]
        v = r["values"]
        byv = {}
        for f, val in r["values_by_fighter"].items():
            byv.setdefault(val, []).append(f)
        print("\n-- %s  hash %s" % (label, r["hash"]))
        print("   MiiGunner=%s min=%s max=%s distinct=%s sites=%d via250=%d"
              % (v["miigunner"], v["min"], v["max"], v["distinct"],
                 r["code_sites"], r["via_0x250"]))
        for val in sorted(byv):
            lst = sorted(byv[val])
            print("   %3s : %2d  %s" % (val, len(lst),
                  ", ".join(x.replace("fighter_kind_", "") for x in lst)
                  if len(lst) <= 12 else "(%d fighters)" % len(lst)))
        if r["hash"] == "0x0e35ca3d82":
            jump_rec = r

    # ------------------------------------------------------------- B
    print("\n=== B. fighters with jump_count_max > 2 ===")
    fj = json.load(open(FIGHTERS_JSON, encoding="utf-8"))
    label_of = {f["name"]: f.get("display_name_label") for f in fj["fighters"]}
    over2 = sorted((f.replace("fighter_kind_", ""), v)
                   for f, v in jump_rec["values_by_fighter"].items() if v > 2)
    print("count: %d" % len(over2))
    for name, val in over2:
        print("  %-14s jump_count_max=%d  display label: %s"
              % (name, val, label_of.get(name, "?")))
    check(len(over2) == 9, "nine fighters with jump_count_max > 2")
    check(jump_rec["values_by_fighter"].get("fighter_kind_miigunner") == 2,
          "Mii Gunner jump_count_max == 2")

    # ------------------------------------------------------------- C
    print("\n=== C. extra-jump motion evidence (c00 body motion lists) ===")
    subjects = [n for n, _ in over2] + ["mario", "miigunner"]
    k_present = {k: [] for k in KINDS}
    a_present = {a: [] for a in ANIMS}
    for name in subjects:
        path = os.path.join(DK, name, "motion", "body", "c00",
                            "motion_list.bin")
        if not os.path.exists(path):
            print("  %-14s MISSING %s" % (name, path))
            fails.append("missing motion list " + name)
            continue
        sha, kinds, anims = decode_mlist(path)
        kflags = []
        for k in KINDS:
            if hash40(k) in kinds:
                k_present[k].append(name)
                kflags.append(k)
        aflags = []
        for a in ANIMS:
            if hash40(a) in anims:
                a_present[a].append(name)
                aflags.append(a)
        print("  %-14s sha256 %s" % (name, sha))
        print("      kinds : %s" % (", ".join(kflags) or "none of the list"))
        print("      anims : %s" % (", ".join(aflags) or "none of the list"))

    # Mii Gunner's own file, the P1-DATASET extraction
    sha, kinds, anims = decode_mlist(GUNNER_P1)
    print("\n  Mii Gunner P1-DATASET file: sha256 %s" % sha)
    check(sha == GUNNER_P1_SHA, "Gunner motion list sha256 matches P1-DATASET's "
          "2b7ed9b6...f4ba")
    gk = [k for k in KINDS if hash40(k) in kinds]
    ga = [a for a in ANIMS if hash40(a) in anims]
    print("      kinds : %s" % (", ".join(gk) or "none"))
    print("      anims : %s" % (", ".join(ga) or "none"))

    print("\n--- matrix over the nine >2 fighters ---")
    for k in KINDS:
        hit = k_present[k]
        print("  kind %-18s present in %d/9: %s"
              % (k, len(hit), ", ".join(hit) or "-"))
    for a in ANIMS:
        hit = a_present[a]
        print("  anim %-24s present in %d/9: %s"
              % (a, len(hit), ", ".join(hit) or "-"))

    # every >2 fighter has the extra-jump kinds? and Gunner does not?
    for k in ("jump_aerial_f2", "jump_aerial_f3", "jump_aerial_b2",
              "jump_aerial_b3"):
        n = len(k_present[k])
        print("NOTE  kind %s in %d of 9 fighters above 2; in Mii Gunner: %s"
              % (k, n, "yes" if hash40(k) in kinds else "NO"))

    print("\n%s  (%d failures)" % ("ALL PASS" if not fails else "FAILURES",
                                   len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
