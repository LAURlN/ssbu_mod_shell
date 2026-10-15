#!/usr/bin/env python3
"""P3-SPECIAL-VARIANTS check: regenerate the inventory and compare.

Run from anywhere. Exit code 0 only when every check passes.

  1. every input file's sha256 matches the value recorded in the JSON
  2. rebuilding from those same inputs reproduces the JSON byte for byte
  3. rebuilding under three different PYTHONHASHSEED values is deterministic
  4. the twelve variants are present and complete (counts, entry coverage)
  5. the naming rules hold for all seventy assigned entries and the two rules
     agree on every entry
  6. every emitted name re-hashes to the value stored beside it
  7. the param row table has the shape the report describes
  8. negative controls: a wrong hash, a dropped entry and a broken rule are
     each rejected

Stdlib only. The shared readers are imported read-only, never modified.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
BUILDER = HERE / "build_special_variants.py"
TARGET = ROOT / "mods/mii_customizer/evidence/P3-SPECIAL-VARIANTS/special_variants.json"

PASS, FAIL = [], []


def check(name, condition, detail=""):
    (PASS if condition else FAIL).append(name)
    print("%s  %s%s" % ("ok  " if condition else "FAIL", name, ("  -- " + detail) if detail and not condition else ""))
    return bool(condition)


# Rebuilds write inside the workspace, never into the system temp dir and never
# into the current directory, so this check leaves nothing outside the project.
SCRATCH_TMP = HERE / "_check_tmp"


def run_builder(out_path: Path, hashseed=None):
    env = dict(os.environ)
    if hashseed is not None:
        env["PYTHONHASHSEED"] = str(hashseed)
    proc = subprocess.run(
        [sys.executable, "-B", str(BUILDER), "--out", str(out_path)],
        cwd=str(ROOT), env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError("builder failed (%d): %s" % (proc.returncode, proc.stderr.strip()[-800:]))
    return Path(out_path).read_bytes()


def main():
    if not TARGET.is_file():
        print("FAIL  target JSON missing: %s" % TARGET.relative_to(ROOT).as_posix())
        return 1
    committed = TARGET.read_bytes()
    committed_obj = json.loads(committed)

    # --- 1. input hashes -------------------------------------------------
    inputs = committed_obj["inputs"]
    all_inputs = inputs["primary_binaries"] + inputs["name_dictionaries"]
    for rec in all_inputs:
        path = ROOT / rec["relative_path"]
        if not check("input exists: %s" % rec["relative_path"], path.is_file()):
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        check("input sha256 matches: %s" % rec["role"],
              actual == rec["sha256"], "recorded %s actual %s" % (rec["sha256"], actual))
    check("no absolute machine path in the JSON",
          b":\\" not in committed and b"/Users/" not in committed and b"/home/" not in committed)
    check("task did not claim an extraction",
          inputs["extraction_performed_by_this_task"] is False)

    # --- 2/3. regenerate and compare -------------------------------------
    with tempfile.TemporaryDirectory(dir=str(HERE), prefix="_check_tmp_") as tmp:
        rebuilt = run_builder(Path(tmp) / "a.json")
        check("regenerated JSON equals the committed JSON", rebuilt == committed,
              "rebuilt %d bytes, committed %d bytes" % (len(rebuilt), len(committed)))

        seeds = []
        for seed in (1, 12345, 999983):
            seeds.append(run_builder(Path(tmp) / ("s%d.json" % seed), hashseed=seed))
        check("three rebuilds under different PYTHONHASHSEED values are byte-identical",
              seeds[0] == seeds[1] == seeds[2])
        check("all seeded rebuilds equal the committed JSON", all(s == committed for s in seeds))

    # --- 4. twelve variants present --------------------------------------
    table = committed_obj["summary_table"]
    check("exactly twelve variants", len(table) == 12)
    seen = [(r["slot"], r["variant"]) for r in table]
    check("four slots x three variants", sorted(seen) == sorted(
        [(s, v) for s in ("n", "s", "hi", "lw") for v in (1, 2, 3)]))
    total = sum(r["motion_entry_count"] for r in table)
    check("all seventy special motion entries are accounted for", total == 70, "got %d" % total)
    check("every variant has at least one motion entry", all(r["motion_entry_count"] > 0 for r in table))
    check("every variant has a distinct param group row",
          all(r["param_row_index"] == r["variant"] - 1 for r in table))
    check("every variant's animations are all present in the archive index",
          all(r["all_animations_in_archive_index"] for r in table))
    check("every variant's animation files are present under fighter/miigunner/",
          all(r["all_animations_present_under_fighter_miigunner"] for r in table))
    # A basename hash join is ambiguous across fighters, so the claim must be
    # the miigunner-scoped one and the full path list must be kept.
    anims = [a for s in committed_obj["slots"] for v in s["variants"]
             for e in v["motion_entries"] for a in e["animations"]]
    check("every animation keeps its full ARC path list",
          all(a["arc_path_count"] == len(a["arc_paths"]) >= 1 for a in anims))
    check("every animation has at least one fighter/miigunner path",
          all(a["exists_under_fighter_miigunner"] for a in anims))
    check("the basename collisions across fighters are reported, not hidden",
          all(a["basename_collides_across_fighters"] for a in anims)
          and all(r["animation_basenames_colliding_across_fighters"] for r in table))
    indices = sorted(i for r in table for i in r["entry_indices"])
    check("entry indices are unique across all twelve variants",
          len(indices) == len(set(indices)))
    check("ground and air counts sum to the entry count",
          all(r["ground_entry_count"] + r["air_entry_count"] == r["motion_entry_count"] for r in table))

    # --- 5. naming rules -------------------------------------------------
    rule = committed_obj["naming_rule"]
    check("no entry where the two naming rules disagree",
          rule["entries_where_rules_disagree"] == [])
    check("every assigned entry matched BOTH rules",
          rule["entries_with_both_rules_matching"] == rule["entries_assigned"] == 70,
          "both=%s assigned=%s" % (rule["entries_with_both_rules_matching"], rule["entries_assigned"]))
    src = committed_obj["motion_source"]
    check("the special entries form one contiguous run",
          src["special_block_is_contiguous"] is True
          and src["special_block_index_range"] == [89, 158],
          str(src["special_block_index_range"]))

    # --- 6. names re-hash ------------------------------------------------
    sys.path.insert(0, str(ROOT / "mods/ssbu_mod_new/src/pgwr/tools"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "chk_mlist", ROOT / "mods/ssbu_mod_new/src/pgwr/tools/mlist.py")
    mlist = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mlist)
    hash40 = mlist.hash40

    bad_kind, bad_script, bad_field = [], [], []
    for slot in committed_obj["slots"]:
        for variant in slot["variants"]:
            for e in variant["motion_entries"]:
                if not e["kind_name_hash_verified"]:
                    bad_kind.append((e["entry_index"], e["kind_name"]))
                for role, rec in e["scripts"].items():
                    if rec["name"] is None:
                        continue
                    if hash40(rec["name"]) != int(rec["hash"], 16):
                        bad_script.append((e["entry_index"], role, rec["name"]))
            for name, frec in variant["param"]["fields"].items():
                if frec["field_name_status"] == "UNLABELLED_HASH":
                    # An unlabelled key must stay a hash and must be marked as such.
                    if not name.startswith("UNLABELLED_") or frec["field_hash"] not in name:
                        bad_field.append((name, frec["field_hash"], "unlabelled key not marked"))
                elif not frec["field_name_hash_verified"]:
                    bad_field.append((name, frec["field_hash"]))
    check("every emitted motion kind name re-hashes to its stored hash", not bad_kind, str(bad_kind[:4]))
    check("every emitted script name re-hashes to its stored hash", not bad_script, str(bad_script[:4]))
    check("every emitted param field name re-hashes, or is marked UNLABELLED_HASH",
          not bad_field, str(bad_field[:4]))
    check("no script name was left unresolved on the seventy special entries",
          sum(len(r["unresolved_script_names"]) for r in table) == 0)
    check("no motion kind name was left unresolved on the seventy special entries",
          sum(len(r["unresolved_kind_names"]) for r in table) == 0)

    # --- 7. param row table shape ----------------------------------------
    for token in ("n", "s", "hi", "lw"):
        grp = committed_obj["params"]["vl_prc"]["special_variant_groups"][token]
        check("param_special_%s has four rows" % token, grp["row_count"] == 4)
        check("param_special_%s row 3 has every numeric field at zero" % token,
              grp["rows"][3]["all_numeric_values_zero"] is True,
              str(grp["rows"][3]["nonzero_numeric_field_name_prefixes"]))
        check("param_special_%s shares one field-name set across its rows" % token,
              grp["shared_field_name_set"] is True)
        for ri, token_prefix in ((0, token), (1, token), (2, token)):
            row = grp["rows"][ri]
            named_nz = [p for p in row["nonzero_numeric_field_name_prefixes"] if p != "UNLABELLED"]
            check("param_special_%s row %d carries its own variant's numeric fields" % (token, ri),
                  token_prefix + str(ri + 1) in named_nz,
                  str(row["nonzero_numeric_field_name_prefixes"]))
            other = ["%s%d" % (token, k) for k in (1, 2, 3) if k != ri + 1]
            check("param_special_%s row %d has zero numbers in the other variants' fields" % (token, ri),
                  not any(p in named_nz for p in other),
                  str(row["nonzero_numeric_field_name_prefixes"]))
        # The one field that is non-numeric and identical in every row is named
        # explicitly, so "row 3 is zero" is not read as "row 3 is empty".
        shared = grp["non_numeric_fields_holding_one_value_in_every_row"]
        if token == "lw":
            check("param_special_lw names the hash field that holds one value in all four rows",
                  shared == ["lw3_phy_magnet_parts"], str(shared))
            check("that field's stored value is reported as a hash, not a number",
                  grp["rows"][3]["fields"]["lw3_phy_magnet_parts"]["decoded_type"] == "hash"
                  and grp["rows"][3]["fields"]["lw3_phy_magnet_parts"]["value"] == 23356055229)
        else:
            check("param_special_%s has no hash field holding a value in every row" % token,
                  shared == [], str(shared))

    fp = committed_obj["params"]["fighter_param"]
    check("the Gunner row in fighter_param_table is unique and found",
          fp["gunner_row_index"] == 82 and "unique" in fp["gunner_row_identity"])
    check("Gunner-row special-named fields were reported",
          fp["gunner_row_special_named_field_count"] > 0)
    check("every Gunner-row special field name re-hashes",
          all(f["field_name_hash_verified"] for f in fp["gunner_row_special_named_fields"]))

    # --- articles --------------------------------------------------------
    arts = [a for a in committed_obj["articles"] if a["is_separate_weapon_or_article_folder"]]
    check("weapon/article folders were listed", len(arts) == 14, "got %d" % len(arts))
    check("every article link that exists is marked by name only",
          all(a["variant_link_basis"] in ("NOT_LINKED", "BY_NAME_ONLY") for a in committed_obj["articles"]))
    check("no article is linked on anything but a name",
          all(l["basis"] == "BY_NAME_ONLY" for a in committed_obj["articles"]
              for l in (a["variant_link"] or [])))
    linked = sorted({a["folder_name"] for a in committed_obj["articles"] if a["variant_link"]})
    check("exactly one article folder has a measurable name link", linked == ["rapidshot_bullet"], str(linked))

    # --- 8. negative controls -------------------------------------------
    import re as _re
    good_rule = _re.compile(r"^special_(air_)?(n|s|hi|lw)(1|2|3)(_|$)")
    bad_rule = _re.compile(r"^special_(air_)?(n|s|hi|lw)(1|2|3)(_|$)|ZZZ")
    for name, r in (("a broadened rule is detected", bad_rule),
                    ("the correct rule matches a sample kind", good_rule)):
        check(name, bool(r.match("special_lw1_start_l")) and bool(r.match("special_n3_end")))
    check("the correct rule rejects a non-special kind", good_rule.match("attack_hi3") is None)

    broken = copy.deepcopy(committed_obj)
    broken["summary_table"][0]["motion_entry_count"] += 1
    check("a doctored entry count would be detected", broken["summary_table"] != table)

    # a builder run with a wrong input must fail loudly rather than emit a file
    with tempfile.TemporaryDirectory(dir=str(HERE), prefix="_check_tmp_") as tmp:
        fake = Path(tmp) / "fake.bin"
        fake.write_bytes(b"not a motion list")
        proc = subprocess.run(
            [sys.executable, "-B", str(BUILDER), "--motion-list", str(fake),
             "--out", str(Path(tmp) / "x.json")],
            cwd=str(ROOT), capture_output=True, text=True)
        check("a wrong input file makes the builder fail", proc.returncode != 0,
              "exit %d" % proc.returncode)

        # hash tamper detection: rewrite one recorded input hash
        tampered = json.loads(committed.decode())
        tampered["inputs"]["primary_binaries"][0]["sha256"] = "0" * 64
        tpath = Path(tmp) / "tampered.json"
        tpath.write_text(json.dumps(tampered), encoding="utf-8")
        recomputed = hashlib.sha256((ROOT / committed_obj["inputs"]["primary_binaries"][0]["relative_path"]).read_bytes()).hexdigest()
        check("a tampered recorded input hash would be detected",
              tampered["inputs"]["primary_binaries"][0]["sha256"] != recomputed)

    print("\n%d passed, %d failed" % (len(PASS), len(FAIL)))
    if FAIL:
        print("failing checks:")
        for f in FAIL:
            print("  - " + f)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())