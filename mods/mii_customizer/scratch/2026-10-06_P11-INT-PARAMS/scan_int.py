"""P11-INT-PARAMS Q2/Q4 survey.

Reuses the copied P4/P10 method (scan_wide.classify_site + stat_reads
scanners, both byte-identical copies in this scratch folder; originals not
edited) over every field hash of the fighter_param table, then emits:

  * Q2 table: the i32 fields - site counts, +0x250 site count, x2 at each
    +0x250 site, Mii Gunner's value, min / max / distinct values over the
    94 fighters.
  * Q4 table: the bool and hash fields - site counts and displacement
    histogram (which getter slot they use).

Commands (workspace root):

    PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \\
      python mods/mii_customizer/scratch/2026-10-06_P11-INT-PARAMS/scan_int.py validate
    PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \\
      python mods/mii_customizer/scratch/2026-10-06_P11-INT-PARAMS/scan_int.py scan

validate:
  1. the copied scanner's own planted-sequence self-test (stat_reads),
  2. P10's validate_p4 (the ten float controls, unchanged),
  3. P4's jump_count_max control: 5 sites, 1 via +0x250 (0x622960),
     1 direct_bl, 3 none, 0 via +0x270.

Outputs (game-derived, workspace gamedata/mii_customizer/P11-INT-PARAMS/):
    sites_int.json   - full per-site survey for all 369 fields
    int_table.json   - Q2 table (i32 fields)
    others_table.json- Q4 table (bool/hash fields)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.abspath(os.path.join(HERE, "..", ".."))
ROOT = os.path.abspath(os.path.join(MOD, "..", ".."))
sys.path.insert(0, HERE)

from stat_reads import (  # noqa: E402
    load, TEXT, scan_sequences, scan_sequences_strict,
)
from scan_wide import (  # noqa: E402
    classify_site, load_table, sha256_of, P4_CONTROL, validate_p4,
    PINNED_IMAGE_SHA256, PINNED_FULL_SHA256, FULL_REL,
)

OUT_REL = "gamedata/mii_customizer/P11-INT-PARAMS"

# P4-STAT-SITES section 6 / section 3: jump_count_max (i32, 0x0e35ca3d82)
# total 5 sites: direct_bl 1, indirect 1 (displacement 0x250 at 0x622960),
# none 3; via +0x270 = 0.
P4_JUMP_CONTROL = {
    "hash": "0x0e35ca3d82",
    "name": "jump_count_max",
    "sites": 5,
    "via250": 1,
    "via270": 0,
    "direct_bl": 1,
    "none": 3,
    "site_250": 0x622960,
}

MIIGUNNER = "fighter_kind_miigunner"


def run_validate():
    import stat_reads
    ok = True
    n = stat_reads.run_validate()          # scanner self-test, prints its own line
    ok = ok and (n == 0)
    image_path = os.path.join(ROOT, "gamedata/ssbu-13.0.4/main.bin")
    if sha256_of(image_path) != PINNED_IMAGE_SHA256:
        print("FAIL image sha256 mismatch")
        return 1
    data = load()
    doc, ordered = load_table()
    rc = validate_p4(data, doc, ordered)   # the ten float controls
    ok = ok and (rc == 0)

    # jump_count_max control
    want = P4_JUMP_CONTROL
    value = int(want["hash"], 16)
    hits = scan_sequences(data, [value], TEXT[0], TEXT[1], max_gap=4)
    sites = [classify_site(data, h) for h in hits]
    via250 = [s for s in sites if s.get("displacement") == 0x250]
    via270 = [s for s in sites if s.get("displacement") == 0x270]
    direct = [s for s in sites if s["class"] == "direct_bl"]
    none = [s for s in sites if s["class"] == "none"]
    checks = [
        ("sites", len(sites), want["sites"]),
        ("via250", len(via250), want["via250"]),
        ("via270", len(via270), want["via270"]),
        ("direct_bl", len(direct), want["direct_bl"]),
        ("none", len(none), want["none"]),
        ("site_250 addr", via250[0]["site"] if via250 else None,
         want["site_250"]),
    ]
    for label, got, exp in checks:
        good = got == exp
        ok = ok and good
        print("%-4s jump_count_max %-14s got=%s expected=%s"
              % ("ok" if good else "FAIL", label, hex(got) if isinstance(got, int)
                 else got, hex(exp) if isinstance(exp, int) else exp))
    print("VALIDATE_INT", "OK" if ok else "FAILED")
    return 0 if ok else 1


def value_stats(doc):
    """Per hash: values per fighter for non-float fields + row order."""
    out = {}
    for row in doc["rows"]:
        name = row["fighter_kind_name"] or ("row%d" % row["row_index"])
        for field in row["fields"]:
            e = out.setdefault(field["hash"], {})
            e[name] = field["value"]
    return out


def run_scan():
    t0 = time.time()
    image_path = os.path.join(ROOT, "gamedata/ssbu-13.0.4/main.bin")
    image_sha = sha256_of(image_path)
    if image_sha != PINNED_IMAGE_SHA256:
        raise SystemExit("main.bin sha256 %s, expected %s"
                         % (image_sha, PINNED_IMAGE_SHA256))
    full_sha = sha256_of(os.path.join(ROOT, FULL_REL))
    if full_sha != PINNED_FULL_SHA256:
        raise SystemExit("fighter_param_full.json sha256 mismatch")
    data = load()
    doc, ordered = load_table()
    targets = sorted({int(f["hash"], 16) for f in ordered})

    t0 = time.time()
    hits = scan_sequences(data, targets, TEXT[0], TEXT[1], max_gap=4)
    t_scan = time.time() - t0
    strict = scan_sequences_strict(data, targets, TEXT[0], TEXT[1], max_gap=4)

    by_hash = {}
    for h in hits:
        by_hash.setdefault(h["value"], []).append(h)
    strict_by_hash = {}
    for h in strict:
        strict_by_hash.setdefault(h["value"], []).append(h)

    vals = value_stats(doc)
    fighters = [r["fighter_kind_name"] or ("row%d" % r["row_index"])
                for r in doc["rows"]]

    per_field = {}
    int_rows = []
    other_rows = []
    for field in ordered:
        value = int(field["hash"], 16)
        sites = [classify_site(data, h) for h in by_hash.get(value, [])]
        disp = {}
        classes = {}
        for s in sites:
            d = s.get("displacement")
            key = "none" if d is None else hex(d)
            disp[key] = disp.get(key, 0) + 1
            classes[s["class"]] = classes.get(s["class"], 0) + 1
        agree = sorted(h["addr"] for h in by_hash.get(value, [])) == \
            sorted(h["addr"] for h in strict_by_hash.get(value, []))
        rec = {
            "hash": field["hash"],
            "name": field["name"],
            "name_hash_verified": field["name_hash_verified"],
            "type": field["type"],
            "code_sites": len(sites),
            "code_sites_strict": len(strict_by_hash.get(value, [])),
            "scanners_agree": agree,
            "classes": classes,
            "displacements": disp,
            "via_0x250": disp.get("0x250", 0),
            "via_0x270": disp.get("0x270", 0),
            "sites": sites,
        }
        per_field[field["hash"]] = rec

        fv = vals.get(field["hash"], {})
        if field["type"] == "i32":
            ivals = [fv[f] for f in fighters if f in fv]
            s250 = [s for s in sites if s.get("displacement") == 0x250]
            rec["values"] = {
                "miigunner": fv.get(MIIGUNNER),
                "min": min(ivals),
                "max": max(ivals),
                "distinct": len(set(ivals)),
            }
            rec["values_by_fighter"] = {f: fv[f] for f in fighters if f in fv}
            rec["sites_250"] = [
                {"site": s["site"], "call": s.get("call"),
                 "x2_immediate": (s.get("x2_immediate") or {}).get("value")
                 if s.get("x2_immediate") else s.get("x2_immediate"),
                 "x2_text": (s.get("x2_immediate") or {}).get("text")
                 if s.get("x2_immediate") else None,
                 "producer": s.get("producer")}
                for s in s250]
            differs = len(set(ivals)) > 1
            has250zero = any((s.get("x2_immediate") or {}).get("value") == 0
                             for s in s250)
            rec["qualifies"] = bool(s250 and has250zero and differs)
            int_rows.append(rec)
        elif field["type"] in ("bool", "hash"):
            other_rows.append(rec)

    report = {
        "task": "P11-INT-PARAMS",
        "purpose": "OFFLINE_SITE_SURVEY_NOT_RUNTIME_EVIDENCE",
        "image": {"relative_path": "gamedata/ssbu-13.0.4/main.bin",
                  "sha256": image_sha,
                  "code_range": [hex(TEXT[0]), hex(TEXT[1])]},
        "table_source": {"relative_path": FULL_REL, "sha256": full_sha,
                         "rows": doc["row_count"],
                         "fields_per_row": doc["field_count_per_row"]},
        "method": {
            "scanner": "stat_reads.scan_sequences (byte-identical P2/P4 copy, "
                       "sha256 28126c1bb703ecc7f79b7cc71b32d24db6b711c00bbb5f781b4dc01d44fd9a6d)",
            "classifier": "scan_wide.classify_site (byte-identical P10 copy, "
                          "sha256 773c90b410601760e0a82c11474b02a7d942301843b8494e32b7132681f44069)",
            "max_gap": 4,
            "first_call_span_bytes": 0x400,
            "producer_lookback_instructions": 20,
            "x2_lookback_instructions": 8,
        },
        "timing_seconds": {"scan_primary": round(t_scan, 1)},
        "fields": len(ordered),
        "total_sites": len(hits),
        "int_field_count": len(int_rows),
        "other_field_count": len(other_rows),
        "scanners_disagree": [f["hash"] for f in ordered
                              if not per_field[f["hash"]]["scanners_agree"]],
        "fields_scanned": per_field,
    }
    out_dir = os.path.join(ROOT, OUT_REL)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "sites_int.json"), "w",
              encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=1, default=str)
        handle.write("\n")
    with open(os.path.join(out_dir, "int_table.json"), "w",
              encoding="utf-8", newline="\n") as handle:
        json.dump({"task": "P11-INT-PARAMS", "rows": int_rows},
                  handle, indent=1, default=str)
        handle.write("\n")
    with open(os.path.join(out_dir, "others_table.json"), "w",
              encoding="utf-8", newline="\n") as handle:
        json.dump({"task": "P11-INT-PARAMS", "rows": other_rows},
                  handle, indent=1, default=str)
        handle.write("\n")

    print("primary scan %.1fs; sites %d over %d fields"
          % (t_scan, len(hits), len(ordered)))
    print("scanners disagree on %d fields" % len(report["scanners_disagree"]))
    print("i32 fields %d, bool+hash %d" % (len(int_rows), len(other_rows)))
    q = [r["name"] or r["hash"] for r in int_rows if r["qualifies"]]
    print("qualifying i32 fields: %d -> %s" % (len(q), ", ".join(q)))
    print("wrote %s/{sites_int,int_table,others_table}.json" % OUT_REL)
    return 0


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"
    if cmd == "validate":
        return run_validate()
    if cmd == "scan":
        return run_scan()
    print("unknown subcommand", cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main())
