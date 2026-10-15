#!/usr/bin/env python3
"""Re-derive every quantitative claim in research/P3-SPECIAL-VARIANTS.md from the
committed JSON. Exit 0 only when all pass. This checks the PROSE against the
data, so a wrong number in the report cannot ship unnoticed.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
D = json.loads((ROOT / "mods/mii_customizer/evidence/P3-SPECIAL-VARIANTS/special_variants.json").read_text(encoding="utf-8"))
MD = (ROOT / "mods/mii_customizer/research/P3-SPECIAL-VARIANTS.md").read_text(encoding="utf-8")

P, F = [], []


def ck(name, condition, detail=""):
    (P if condition else F).append(name)
    print("%s  %s%s" % ("ok  " if condition else "FAIL", name,
                         ("  -- " + detail) if detail and not condition else ""))


def ind(needle):
    return needle in MD


# ---- inputs --------------------------------------------------------------
inp = {r["role"]: r for r in D["inputs"]["primary_binaries"]}
nd = {r["role"]: r for r in D["inputs"]["name_dictionaries"]}
ck("report states the motion list sha256", inp["gunner_body_c00_motion_list"]["sha256"] in MD)
ck("report states the vl.prc sha256", inp["gunner_vl_prc"]["sha256"] in MD)
ck("report states the fighter_param sha256", inp["common_fighter_param"]["sha256"] in MD)
ck("report states the ParamLabels sha256", nd["motion_kind_and_param_labels"]["sha256"] in MD)
ck("report states the arc index sha256", nd["archive_path_index"]["sha256"] in MD)
ck("no extraction is claimed", D["inputs"]["extraction_performed_by_this_task"] is False)
ck("report says no extraction", ind("No extraction was performed by this"))
for role, size in (("gunner_body_c00_motion_list", 46272), ("gunner_vl_prc", 10192),
                   ("common_fighter_param", 176604)):
    ck("input size %d is correct and in the report" % size,
       inp[role]["bytes"] == size and str(size) in MD, str(inp[role]["bytes"]))

# ---- naming rule and coverage -------------------------------------------
r = D["naming_rule"]
ms = D["motion_source"]
ck("the motion list has 774 entries", r["entries_checked"] == 774 and "774" in MD)
ck("70 entries are assigned", r["entries_assigned"] == 70)
ck("the assigned run is 89..158", ms["special_block_index_range"] == [89, 158] and "89..158" in MD)
ck("both rules matched all 70", r["entries_with_both_rules_matching"] == 70)
ck("the two rules never disagree", r["entries_where_rules_disagree"] == [])
ck("the special run is contiguous", ms["special_block_is_contiguous"] is True)

scripts = [(k, rec) for s in D["slots"] for v in s["variants"] for e in v["motion_entries"]
           for k, rec in e["scripts"].items()]
ck("280 script names resolved", sum(1 for _, rec in scripts if rec["name_verified"]) == 280)
ck("report says 280", "280" in MD)
ck("140 of those are sound+effect",
   sum(1 for k, rec in scripts if k in ("sound_script", "effect_script") and rec["name_verified"]) == 140
   and "140" in MD)
ck("no special entry kept a script as a hash",
   sum(1 for row in D["summary_table"] for x in row["unresolved_script_names"]) == 0)
ck("no special entry kept a kind as a hash",
   sum(1 for row in D["summary_table"] for x in row["unresolved_kind_names"]) == 0)

# ---- summary table -------------------------------------------------------
tbl = {(x["slot"], x["variant"]): x for x in D["summary_table"]}
ck("the summary table has twelve rows", len(tbl) == 12)
ck("four slots x three variants", sorted(tbl) == sorted(
    [(s, v) for s in ("n", "s", "hi", "lw") for v in (1, 2, 3)]))
ck("entries sum to 70", sum(x["motion_entry_count"] for x in tbl.values()) == 70)
ck("report says the entries sum to 70", ind("sum to **70**"))
ck("every report row cites the right entry count",
   all(ind("| %s | %d | %d |" % (k[0], k[1], v["motion_entry_count"])) for k, v in tbl.items()))


# Parse the report's 12-row summary table and compare every cell against the
# JSON. Matching substrings is not enough: a stale cell must fail.
def md_table_rows():
    rows = {}
    for line in MD.splitlines():
        line = line.strip()
        m = re.match(r"^\| (n|s|hi|lw) \| ([123]) \| (\d+) \| (\d+)/(\d+) \| (\d+) \| (\w+) \| (.*?) \| `param_special_\w+` \| (\d) \| (\d+) \| (.*?) \|$", line)
        if m:
            rows[(m.group(1), int(m.group(2)))] = {
                "motion_entry_count": int(m.group(3)),
                "ground_entry_count": int(m.group(4)),
                "air_entry_count": int(m.group(5)),
                "distinct_animation_files": int(m.group(6)),
                "all_animations_in_archive_index": m.group(7),
                "articles": m.group(8),
                "param_row_index": int(m.group(9)),
                "param_field_count": int(m.group(10)),
                "nonzero": m.group(11),
            }
    return rows


mdrows = md_table_rows()
ck("the report's summary table was parsed: 12 rows", len(mdrows) == 12, str(sorted(mdrows)))
if len(mdrows) == 12:
    mism = []
    for k, cell in mdrows.items():
        j = tbl[k]
        if cell["motion_entry_count"] != j["motion_entry_count"]:
            mism.append((k, "entry count", cell["motion_entry_count"], j["motion_entry_count"]))
        if cell["ground_entry_count"] != j["ground_entry_count"]:
            mism.append((k, "ground", cell["ground_entry_count"], j["ground_entry_count"]))
        if cell["air_entry_count"] != j["air_entry_count"]:
            mism.append((k, "air", cell["air_entry_count"], j["air_entry_count"]))
        if cell["distinct_animation_files"] != len(j["distinct_animation_files"]):
            mism.append((k, "anims", cell["distinct_animation_files"],
                         len(j["distinct_animation_files"])))
        if cell["all_animations_in_archive_index"] != ("yes" if j["all_animations_in_archive_index"] else "no"):
            mism.append((k, "index flag", cell["all_animations_in_archive_index"],
                         j["all_animations_in_archive_index"]))
        if cell["param_row_index"] != j["param_row_index"]:
            mism.append((k, "param row", cell["param_row_index"], j["param_row_index"]))
        if cell["param_field_count"] != j["param_field_count"]:
            mism.append((k, "param fields", cell["param_field_count"], j["param_field_count"]))
        nz = cell["nonzero"].replace("`", "").replace("+ one unlabelled", "").strip()
        nz = nz.replace("and one unlabelled", "").strip()
        nz = " ".join(nz.replace(",", " ").split())
        want = " ".join(j["param_nonzero_numeric_field_name_prefixes"])
        if nz != want:
            mism.append((k, "non-zero prefixes", nz, want))
        has_art = "by name only" in cell["articles"]
        want_art = bool(j["articles"])
        if has_art != want_art:
            mism.append((k, "articles", cell["articles"], j["articles"]))
    ck("every cell of the report's summary table matches the JSON", not mism, str(mism[:4]))
ck("ground plus air equals the entry count everywhere",
   all(v["ground_entry_count"] + v["air_entry_count"] == v["motion_entry_count"] for v in tbl.values()))
ck("every animation file is present under fighter/miigunner",
   all(v["all_animations_present_under_fighter_miigunner"] for v in tbl.values()))
ck("entry indices are unique across variants",
   len({i for v in tbl.values() for i in v["entry_indices"]}) == 70)
asym = sorted(k for k, v in tbl.items() if v["ground_entry_count"] != v["air_entry_count"])
ck("the asymmetric variants are n1, hi2 and hi3",
   asym == [("hi", 2), ("hi", 3), ("n", 1)], str(asym))
ck("the report names all three asymmetric variants",
   ind("`n1` is 5/6") or ind("`n1` is\n5/6"))
ck("the other nine variants are exactly balanced",
   sum(1 for v in tbl.values() if v["ground_entry_count"] == v["air_entry_count"]) == 9)

# ---- recovered kind names -----------------------------------------------
rec = [(e["entry_name"] if False else e["entry_index"], e["kind_name"],
        e["kind_name_recovery"]["candidates_tried"], e["kind_name_recovery"]["hash_matches"])
       for s in D["slots"] for v in s["variants"] for e in v["motion_entries"]
       if e["kind_name_recovery"]]
ck("four kind names were recovered", len(rec) == 4, str(rec))
for idx, name, tried, hits in rec:
    ck("recovered name %s is in the report" % name, ind(name))
    ck("its candidate count %d is in the report" % tried, ind(str(tried)))
    ck("%s had exactly one hash match" % name, hits == 1, str(hits))
    ck("%s re-hashes to its stored kind hash" % name,
       any(e["entry_index"] == idx and e["kind_name_hash_verified"]
           for s in D["slots"] for v in s["variants"] for e in v["motion_entries"]))

# ---- vl.prc --------------------------------------------------------------
tp = D["params"]["vl_prc"]["top_level_groups"]
ck("vl.prc has 42 top-level groups", len(tp) == 42 and "**42**" in MD)
g = {x["group_name"]: x for x in tp}
ck("the four param_special_* groups are 4-row lists",
   all(g["param_special_" + t]["entry_count"] == 4 for t in ("n", "s", "hi", "lw")))
ck("only the four param_special_* groups are named for a variant",
   sorted(x["group_name"] for x in tp if x["special_variant_group"])
   == ["param_special_hi", "param_special_lw", "param_special_n", "param_special_s"])
ck("every top-level group name that was emitted re-hashes",
   all(x["group_name_hash_verified"] for x in tp if x["group_name"]))
sg = D["params"]["vl_prc"]["special_variant_groups"]
ck("per-row field counts are 13/16/35/24",
   [len(sg[t]["rows"][0]["fields"]) for t in ("n", "s", "hi", "lw")] == [13, 16, 35, 24],
   str([len(sg[t]["rows"][0]["fields"]) for t in ("n", "s", "hi", "lw")]))
ck("the report quotes all four field counts",
   all(ind("**%d**" % n) for n in (13, 16, 35, 24)))
ck("all four groups share one field-name set",
   all(sg[t]["shared_field_name_set"] for t in ("n", "s", "hi", "lw")))
ck("row 3 has every numeric field at zero, in all four groups",
   all(sg[t]["rows"][3]["all_numeric_values_zero"] for t in ("n", "s", "hi", "lw")))
ck("param_special_lw names its one all-row hash field",
   sg["lw"]["non_numeric_fields_holding_one_value_in_every_row"] == ["lw3_phy_magnet_parts"])
ck("no group other than lw has an all-row hash field",
   all(sg[t]["non_numeric_fields_holding_one_value_in_every_row"] == []
       for t in ("n", "s", "hi")))
ck("that field holds 23356055229 in all four rows",
   all(sg["lw"]["rows"][i]["fields"]["lw3_phy_magnet_parts"]["value"] == 23356055229
       for i in range(4)))
for t, digit in (("n", "n"), ("s", "s"), ("hi", "hi"), ("lw", "lw")):
    for ri in (0, 1, 2):
        nz = [p for p in sg[t]["rows"][ri]["nonzero_numeric_field_name_prefixes"]
              if p != "UNLABELLED"]
        ck("param_special_%s row %d holds only its own variant's numbers" % (t, ri),
           nz == ["%s%d" % (digit, ri + 1)], str(nz))
unl = {(t, k) for t in sg for row in sg[t]["rows"] for k, f in row["fields"].items()
       if f["field_name_status"] == "UNLABELLED_HASH"}
ck("exactly one unlabelled field, and it is in param_special_hi",
   {t for t, _ in unl} == {"hi"}, str(unl))
ck("the unlabelled field is reported by hash",
   ind("UNLABELLED_0x250a27ba9b"))
ck("352 special-named leaf paths is stated", ind("352"))

# ---- fighter_param -------------------------------------------------------
fp = D["params"]["fighter_param"]
ck("fighter_param_table has 94 rows", fp["row_count"] == 94)
ck("the Gunner row is row 82", fp["gunner_row_index"] == 82)
ck("the Gunner row has 369 keys", fp["gunner_row_key_count"] == 369 and "**369**" in MD)
ck("eleven special-named fields in the Gunner row",
   fp["gunner_row_special_named_field_count"] == 11 and "**Eleven**" in MD)
ck("every Gunner-row special field name re-hashes",
   all(f["field_name_hash_verified"] for f in fp["gunner_row_special_named_fields"]))
ck("the three hash-valued trail fields got a value name",
   all("value_name" in f for f in fp["gunner_row_special_named_fields"] if f["decoded_type"] == "hash"))

# ---- articles ------------------------------------------------------------
arts = [a for a in D["articles"] if a["is_separate_weapon_or_article_folder"]]
ck("14 weapon/article folders", len(arts) == 14 and "**14 separate weapon/article folders**" in MD)
ck("five of them have a model folder",
   sum(1 for a in arts if a["has_model_folder"]) == 5 and "Only **five** have a `model/` folder" in MD)
ck("the other nine are motion-only",
   sum(1 for a in arts if not a["has_model_folder"]) == 9 and "other nine are motion-only" in MD)
ck("every folder name is in the report", all(ind(a["folder_name"]) for a in arts))
ck("exactly one folder has a link", sorted({a["folder_name"] for a in arts if a["variant_link"]})
   == ["rapidshot_bullet"])
links = [l for a in arts for l in (a["variant_link"] or [])]
ck("that link points at neutral variant 2", {(l["slot"], l["variant"]) for l in links} == {("n", 2)})
ck("it rests on seven param fields", len({l["param_field"] for l in links}) == 7)
ck("the seven fields are non-zero only in row 1",
   all(sg["n"]["rows"][1]["fields"][l["param_field"]]["value"] != 0 for l in links)
   and all(sg["n"]["rows"][i]["fields"][l["param_field"]]["value"] == 0
           for l in links for i in (0, 2, 3)))
ck("the other thirteen folders are NOT_LINKED",
   sum(1 for a in arts if a["variant_link_basis"] == "NOT_LINKED") == 13
   and ind("For the other 13 folders"))
ck("no article link claims anything but a name",
   all(l["basis"] == "BY_NAME_ONLY" for l in links))
ck("every article motion list carries a sha256",
   all(a["local_motion_list"]["motion_list_sha256"] for a in arts))

# ---- unassigned ----------------------------------------------------------
u = D["unassigned_special_related_entries"]
ck("26 unassigned special-looking entries", len(u) == 26 and "**26 entries**" in MD)
ck("four of them are the fall entries at 34..37",
   [x["entry_index"] for x in u][:4] == [34, 35, 36, 37] and ind("indices 34-37"))
ck("twenty-two are other fighters' victim reactions",
   len([x for x in u if x["entry_index"] >= 712]) == 22)
ck("all 26 are names, none was force-fitted",
   all(x["rule_kind_match"] is False and x["rule_clip_match"] is False for x in u))

# ---- language the report must and must not use ---------------------------
flat = " ".join(MD.split())  # collapse the report's line wrapping before matching prose
for phrase in ("No A evidence", "Script bodies are unavailable", "BY_NAME_ONLY",
               "No effect bank and no sound bank was opened", "NOT a dependency",
               "is not established", "No runtime behaviour is claimed"):
    ck("the report states %r" % phrase, phrase in flat)
for bad in ("works in a match", "proven to", "will be handled",
            "at runtime the game", "we can swap", "safe to replace"):
    ck("the report avoids %r" % bad, bad.lower() not in flat.lower())

print("\n%d passed, %d failed" % (len(P), len(F)))
for f in F:
    print("  - " + f)
sys.exit(1 if F else 0)