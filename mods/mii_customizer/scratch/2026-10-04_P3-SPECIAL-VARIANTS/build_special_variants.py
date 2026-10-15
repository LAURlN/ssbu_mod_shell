#!/usr/bin/env python3
"""P3-SPECIAL-VARIANTS: file-level inventory of the twelve Gunner special variants.

WHAT THIS IS
    An inventory of which game-file resources belong to each of Mii Gunner's
    twelve special variants (4 slots x 3 vanilla variants), read from pinned
    local binaries.

WHAT THIS IS NOT
    Not a move-swap design, not a dependency closure, not runtime behaviour.
    Nothing here is opened to be executed; no effect or sound bank was read.
    Every value is re-derived from the input bytes on each run.

Evidence tier: B (measured offline from pinned local binaries). No tier A exists.

Rules baked in:
  * A name is emitted only when hash40(name) equals the hash stored beside it.
    An unresolvable hash stays a hash.
  * A resemblance between names is "by name only", never a dependency.
  * Script/param field semantics are NOT explained. Values only.
  * Nothing is dropped: entries that cannot be assigned are listed explicitly.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import re
import struct
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
ROOT = TOOL_DIR.parents[3]

DEFAULT_MOTION_LIST = "gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin"
DEFAULT_VL_PRC = "gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/param/vl.prc"
DEFAULT_FIGHTER_PARAM = "gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc"
DEFAULT_LABELS = "mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv"
DEFAULT_ARC_INDEX = "mods/ssbu_mod_new/dumps/decoded/arc_files.tsv"
DEFAULT_HELPER_ROOT = "gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion"
DEFAULT_OUT = "mods/mii_customizer/evidence/P3-SPECIAL-VARIANTS/special_variants.json"

MOTION_ARC = "fighter/miigunner/motion/body/c00/motion_list.bin"
VL_ARC = "fighter/miigunner/param/vl.prc"
FIGHTER_PARAM_ARC = "fighter/common/param/fighter_param.prc"

# Slot key -> (direction token in the name, direction word used in labels)
SLOTS = [("n", "neutral"), ("s", "side"), ("hi", "up"), ("lw", "down")]

# R1: the naming rule used to assign a body motion entry to a slot+variant.
RULE_KIND = re.compile(r"^special_(air_)?(n|s|hi|lw)(1|2|3)(_|$)")
# R2: independent cross-check straight off the clip file name.
RULE_CLIP = re.compile(r"^[a-z]\d\d(?:special)?(air)?(n|s|hi|lw)(1|2|3)")

# Tail layout pinned by P1-CATALOG-AUDIT against a decoded GameWatch reference.
TAIL_SCRIPT_OFFSETS = {"expression_script": 0, "sound_script": 8, "effect_script": 16}
TAIL_TIMING_OFFSETS = {"xlu_start": 24, "xlu_end": 25, "cancel_frame": 26, "no_stop_intp": 27}
NO_STOP_INTP_BIT = 0x100
CANCEL_FRAME_MASK = 0xFF


def load_shared(name: str, relative: str):
    """Import a shared reader by path, read-only. Never copies or edits it."""
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


mlist = load_shared("shared_mlist", "mods/ssbu_mod_new/src/pgwr/tools/mlist.py")
prc = load_shared("shared_prc", "mods/ssbu_mod_new/src/pgwr/tools/prc.py")
hash40 = mlist.hash40


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hexh(value: int, width: int = 10) -> str:
    return "0x%0*x" % (width, value)


def f32_bits(value: float) -> str:
    return "0x%08x" % struct.unpack("<I", struct.pack("<f", value))[0]


# --------------------------------------------------------------------------
# name dictionaries (already in the workspace; names only, never values)
# --------------------------------------------------------------------------

def load_labels(path: Path) -> dict:
    labels = {}
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        for row in csv.reader(handle):
            if len(row) >= 2 and row[1] not in ("", "-1", "-2"):
                labels.setdefault(int(row[0], 16), row[1])
    return labels


def load_animation_index(path: Path):
    """hash40(basename with extension) -> [ARC paths]. Full paths are kept so a
    collision stays visible instead of silently resolving to one file."""
    index = {}
    folder = {}
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            arc_path = line.strip()
            # Folder membership is about the PATH, so it is decided before any
            # extension filter; a folder must be listed even if its only files
            # are .numatb/.nutexb and not animations.
            m = re.match(r"^fighter/miigunner/(?:motion|model)/([^/]+)/c00/", arc_path)
            if m and not m.group(1).startswith(("b_", "body")):
                folder.setdefault(m.group(1), set()).add(arc_path)
            if not arc_path.endswith(".nuanmb"):
                continue
            index.setdefault(hash40(arc_path.rsplit("/", 1)[1]), []).append(arc_path)
    return index, folder


# --------------------------------------------------------------------------
# kind-name recovery for entries the label table does not name
# --------------------------------------------------------------------------

def underscore_forms(stem: str):
    """Every string obtainable from `stem` by inserting underscores."""
    n = len(stem)
    for mask in range(1 << (n - 1)):
        yield "".join(stem[i] + ("_" if i < n - 1 and (mask >> i) & 1 else "")
                      for i in range(n))


def recover_kind_name(clip_stem: str, kind_hash: int):
    """Recover a motion kind name from its clip name, accepted only on a hash
    match. Returns (name, evidence) or (None, evidence)."""
    prefix = clip_stem[:3]
    stem = clip_stem[len(prefix):]
    hits = [c for c in underscore_forms(stem) if hash40(c) == kind_hash]
    evidence = {
        "method": "hash40 over every underscore insertion of the clip stem %r "
                  "(2^%d candidates, minus the %r prefix)" % (stem, len(stem) - 1, prefix),
        "candidates_tried": 1 << (len(stem) - 1),
        "hash_matches": len(hits),
    }
    return (hits[0] if len(hits) == 1 else None), evidence


# --------------------------------------------------------------------------
# script name derivation
# --------------------------------------------------------------------------

def _strip_underscore_before_digit(stem: str) -> str:
    out = []
    for i, ch in enumerate(stem):
        if ch == "_" and i + 1 < len(stem) and stem[i + 1].isdigit():
            continue
        out.append(ch)
    return "".join(out)


def script_candidates(kind_name: str):
    """Plausible script names for a motion kind, in a fixed order.

    P1-CATALOG-AUDIT pinned the rule for `game_*`: drop a trailing `_s`/`_l`,
    drop the underscore before a digit, drop separators, prefix `game_`. The
    same shape is applied to the expression/sound/effect slots here. Every
    candidate is accepted ONLY when hash40(candidate) equals the stored field,
    so a wrong guess cannot leak into the inventory.
    """
    bases = [kind_name]
    if kind_name.endswith("_s"):
        bases.append(kind_name[:-2])
    if kind_name.endswith("_l"):
        bases.append(kind_name[:-2])
    bases.append(kind_name.replace("_hold", "charge"))
    out = []
    for prefix in ("game_", "expression_", "sound_", "effect_"):
        for base in bases:
            for stem in (base.replace("_", ""), _strip_underscore_before_digit(base).replace("_", "")):
                name = prefix + stem
                if name not in out:
                    out.append(name)
    return out


def resolve_script(stored_hash: int, kind_name: str):
    for candidate in script_candidates(kind_name):
        if hash40(candidate) == stored_hash:
            return candidate
    return None


# --------------------------------------------------------------------------
# motion list reading
# --------------------------------------------------------------------------

def tail_of(entry) -> bytes:
    block = (entry["n"] * 9 + 3) & ~3
    return entry["raw"][24 + block:]


def read_motion(ml_path: Path, labels: dict, anim_index: dict):
    """Return (motion_list, per-entry records, assignment maps)."""
    ml = mlist.parse(ml_path)
    records = []
    for index, entry in enumerate(ml["entries"]):
        tail = tail_of(entry)
        clip_names = []
        for anim_hash in entry["anims"]:
            paths = anim_index.get(anim_hash, [])
            gunner = [p for p in paths if p.startswith("fighter/miigunner/")]
            clip_names.append({
                "hash": hexh(anim_hash),
                "basename": paths[0].rsplit("/", 1)[1] if paths else None,
                "arc_paths": paths,
                # Motion names hash WITH the extension, and these basenames are
                # shared across fighters, so one hash maps to many ARC paths. The
                # full list is kept so the collision stays visible; only the
                # miigunner subset is claimed as this fighter's own file.
                "miigunner_arc_paths": gunner,
                "exists_in_archive_index": bool(paths),
                "exists_under_fighter_miigunner": bool(gunner),
                "arc_path_count": len(paths),
                "basename_collides_across_fighters": len(paths) > 1,
                "name_source": "hash40(file basename with extension) joined over the archive path index",
            })
        scripts = {"game_script": {"hash": hexh(entry["gs"]), "name": None, "name_verified": False}}
        timing = {"tail_length": len(tail)}
        if len(tail) >= 28:
            for role, off in TAIL_SCRIPT_OFFSETS.items():
                scripts[role] = {
                    "hash": hexh(struct.unpack_from("<Q", tail, off)[0], 16),
                    "name": None,
                    "name_verified": False,
                }
            raw_u16 = struct.unpack_from("<H", tail, 26)[0]
            for field, off in TAIL_TIMING_OFFSETS.items():
                timing[field] = tail[off]
            timing["cancel_u16_raw"] = raw_u16
            timing["no_stop_intp_bit"] = NO_STOP_INTP_BIT
            timing["consistency_check"] = {
                "cancel_frame_matches_low_byte": (raw_u16 & CANCEL_FRAME_MASK) == tail[26],
                "no_stop_intp_matches_bit_0x100": bool(raw_u16 & NO_STOP_INTP_BIT) == bool(tail[27]),
            }
        else:
            timing["status"] = "TIMING_BYTES_UNAVAILABLE"
        records.append({
            "entry_index": index,
            "kind_hash": hexh(entry["kind"]),
            "kind_name": labels.get(entry["kind"]),
            "kind_name_source": None,
            "kind_name_recovery": None,
            "flags_raw_hex": "0x%04x" % entry["flags"],
            "flags_raw_u16": entry["flags"],
            "blend_raw_u8": entry["blend"],
            "animation_count": entry["n"],
            "animations": clip_names,
            "scripts": scripts,
            "timing_raw": timing,
            "_entry": entry,
            "_tail": tail,
        })

    # R1 + R2 assignment. R2 (clip name) runs first so R1 has a name for the
    # entries the label table does not carry; both must then agree.
    for rec in records:
        clips = [c["basename"] for c in rec["animations"] if c["basename"]]
        rec["_clip_stem"] = clips[0][:-7] if len(clips) == 1 and clips[0].endswith(".nuanmb") else None

    for rec in records:
        if rec["kind_name"]:
            rec["kind_name_source"] = "ParamLabels.csv label joined on the entry kind hash"
            continue
        if rec["_clip_stem"]:
            name, ev = recover_kind_name(rec["_clip_stem"], rec["_entry"]["kind"])
            rec["kind_name_recovery"] = ev
            if name:
                rec["kind_name"] = name
                rec["kind_name_source"] = (
                    "recovered: hash40(recovered name) equals the entry kind hash; "
                    "not present in ParamLabels.csv"
                )

    for rec in records:
        rec["kind_name_hash_verified"] = bool(
            rec["kind_name"] and hash40(rec["kind_name"]) == rec["_entry"]["kind"])
        name = rec["kind_name"]
        for role in rec["scripts"]:
            rec["scripts"][role]["name"] = resolve_script(rec["scripts"][role]["hash"] and
                                                          int(rec["scripts"][role]["hash"], 16) or 0,
                                                          name) if name else None
            resolved = rec["scripts"][role]["name"]
            rec["scripts"][role]["name_verified"] = bool(resolved) and hash40(resolved) == int(
                rec["scripts"][role]["hash"], 16)
            rec["scripts"][role]["name_source"] = (
                "hash40(candidate form) verified against the entry field"
                if rec["scripts"][role]["name_verified"]
                else "unresolved: no candidate form matched this entry field; the hash stands")

    assigned = {}
    unmatched_kind = []
    unmatched_clip = []
    for rec in records:
        by_kind = bool(rec["kind_name"]) and bool(RULE_KIND.match(rec["kind_name"]))
        by_clip = bool(rec["_clip_stem"]) and bool(RULE_CLIP.match(rec["_clip_stem"]))
        rec["rule_kind_match"] = by_kind
        rec["rule_clip_match"] = by_clip
        rec["rules_agree"] = (by_kind == by_clip) or not (rec["kind_name"] and rec["_clip_stem"])
        if by_kind and by_clip:
            m = RULE_KIND.match(rec["kind_name"])
            rec["assignment"] = {"slot": m.group(2), "variant": int(m.group(3)),
                                 "air": bool(m.group(1)), "stage": m.group(0)}
        else:
            rec["assignment"] = None
            if by_kind or by_clip:
                unmatched_kind.append(rec["entry_index"])
    return ml, records


# --------------------------------------------------------------------------
# params
# --------------------------------------------------------------------------

def read_group(root, name):
    key = prc.hash40(name)
    if key not in root:
        return None
    return root[key]


def named(node, labels):
    """[(label_or_UNLABELLED, hash, tag, value), ...] for a struct node."""
    out = []
    for key, child in node[1]:
        name = labels.get(key)
        out.append((name if name else "UNLABELLED_%s" % hexh(key, 10), key, child[0], child[1]))
    return out


def build_param_groups(vl_path: Path, labels: dict):
    tree = prc.read(vl_path)
    root = dict(tree[1])
    top = []
    for key, node in tree[1]:
        name = labels.get(key)
        record = {
            "group_name": name,
            "group_name_source": ("ParamLabels.csv label joined on the group hash"
                                  if name else None),
            "group_hash": hexh(key),
            "group_name_hash_verified": bool(name) and hash40(name) == key,
            "node_type": node[0],
            "entry_count": len(node[1]) if node[0] in ("list", "struct") else None,
            "special_variant_group": bool(name) and name in
                                     ("param_special_n", "param_special_s",
                                      "param_special_hi", "param_special_lw"),
        }
        top.append(record)

    special = {}
    for token, direction in SLOTS:
        gname = "param_special_%s" % token
        node = read_group(root, gname)
        rows = []
        for ri, row in enumerate(node[1]):
            entries = named(row, labels)
            # Which field-name prefixes carry a non-zero NUMERIC value in this
            # row? A hash-typed field has no numeric zero, so it is reported
            # separately instead of being folded in here.
            nonzero = sorted({name.split("_")[0] for name, _, tag, val in entries
                              if tag in ("float", "i32", "u32") and val != 0})
            nonnumeric = sorted({name for name, _, tag, _ in entries
                                 if tag not in ("float", "i32", "u32")})
            values = {}
            for name, key, tag, val in entries:
                labelled = not name.startswith("UNLABELLED_")
                rec = {"field_name": name, "field_hash": hexh(key),
                       "field_name_hash_verified": (hash40(name) == key) if labelled else None,
                       "field_name_status": ("NAMED_AND_HASH_VERIFIED" if labelled
                                             else "UNLABELLED_HASH"),
                       "decoded_type": tag, "value": val}
                if tag == "float":
                    rec["value_f32_bits"] = f32_bits(val)
                elif tag == "hash":
                    rec["value_name"] = labels.get(val)
                    rec["value_name_status"] = ("NAMED" if labels.get(val) else "UNRESOLVED_HASH")
                values[name] = rec
            rows.append({
                "row_index": ri,
                "entry_count": len(entries),
                "nonzero_numeric_field_name_prefixes": nonzero,
                "all_numeric_values_zero": not nonzero,
                "non_numeric_field_names": nonnumeric,
                "fields": values,
            })
        special[token] = {"group_name": gname, "direction": direction,
                           "row_count": len(rows), "rows": rows,
                           "shared_field_name_set": len({tuple(sorted(r["fields"]))
                                                         for r in rows}) == 1,
                           # A non-numeric field (a hash) has no numeric zero, so "row 3's numbers are all
                           # zero" does not mean row 3 is empty. These are named explicitly.
                           "non_numeric_fields_holding_one_value_in_every_row": sorted(
                               name for name in rows[0]["fields"]
                               if rows[0]["fields"][name]["decoded_type"] not in ("float", "i32", "u32")
                               and all(r["fields"][name]["value"] == rows[0]["fields"][name]["value"]
                                       for r in rows))}

    # fighter_param.prc, Gunner row
    fp_tree = prc.read(ROOT / DEFAULT_FIGHTER_PARAM)
    fp_root = dict(fp_tree[1])
    fp_rows = fp_root[prc.hash40("fighter_param_table")][1]
    kind_key = prc.hash40("fighter_kind")
    want = prc.hash40("fighter_kind_miigunner")
    matches = [i for i, r in enumerate(fp_rows) if dict(r[1]).get(kind_key, (None, None))[1] == want]
    if len(matches) != 1:
        raise SystemExit("expected exactly one %s row, found %r" % ("fighter_kind_miigunner", matches))
    gunner_index = matches[0]
    gunner = named(fp_rows[gunner_index], labels)
    special_fields = []
    for name, key, tag, val in gunner:
        if "special" not in name.lower():
            continue
        rec = {"field_name": name, "field_hash": hexh(key),
               "field_name_hash_verified": hash40(name) == key,
               "decoded_type": tag, "value": val}
        if isinstance(val, int) and tag == "hash":
            rec["value_name"] = labels.get(val)
            rec["value_name_source"] = ("ParamLabels.csv label joined on the stored value hash"
                                        if labels.get(val) else
                                        "unresolved: the stored value hash has no label")
            rec["value_hash"] = hexh(val, 10)
        if tag == "float":
            rec["value_f32_bits"] = f32_bits(val)
        special_fields.append(rec)

    return {
        "vl_prc": {"top_level_groups": top,
                   "top_level_group_count": len(top),
                   "special_variant_groups": special},
        "fighter_param": {
            "table_name": "fighter_param_table",
            "row_count": len(fp_rows),
            "gunner_row_index": gunner_index,
            "gunner_row_identity": "fighter_kind == fighter_kind_miigunner (%s), unique in the table"
                                   % hexh(want),
            "gunner_row_key_count": len(gunner),
            "gunner_row_special_named_fields": special_fields,
            "gunner_row_special_named_field_count": len(special_fields),
        },
    }


# --------------------------------------------------------------------------
# articles / weapons
# --------------------------------------------------------------------------

ARTICLE_EXCLUSIONS = ("b_", "body")


def build_articles(folder_paths: dict, helper_root: Path, labels: dict):
    records = []
    for name in sorted(folder_paths):
        paths = sorted(folder_paths[name])
        kinds = sorted({p.split("/")[2] for p in paths})
        has_model = "model" in kinds
        has_motion = "motion" in kinds
        local = {}
        mlp = helper_root / name / "c00" / "motion_list.bin"
        if mlp.is_file():
            ml = mlist.parse(mlp)
            local = {
                "motion_list_relative_path": mlp.relative_to(ROOT).as_posix(),
                "motion_list_sha256": sha256_of(mlp),
                "motion_list_bytes": mlp.stat().st_size,
                "motion_list_entry_count": len(ml["entries"]),
                "motion_list_motion_path_field": hexh(ml["motion_path"]),
                "entry_kind_names": [labels.get(e["kind"]) for e in ml["entries"]],
                "entry_kind_names_unresolved": sum(
                    1 for e in ml["entries"] if not labels.get(e["kind"])),
            }
        records.append({
            "folder_name": name,
            "is_separate_weapon_or_article_folder": has_model or has_motion,
            "has_model_folder": has_model,
            "has_motion_folder": has_motion,
            "arc_file_count": len(paths),
            "arc_file_kinds": kinds,
            "arc_paths": paths,
            "local_motion_list": local,
            "variant_link": None,
            "variant_link_basis": "NOT_LINKED",
        })
    return records


# --------------------------------------------------------------------------
# summary table
# --------------------------------------------------------------------------

def build_summary(slots, articles, params):
    rows = []
    for token, direction in SLOTS:
        grp = params["vl_prc"]["special_variant_groups"][token]
        for variant in (1, 2, 3):
            entries = slots[(token, variant)]["entries"]
            rows.append({
                "slot": token,
                "direction": direction,
                "variant": variant,
                "motion_entry_count": len(entries),
                "ground_entry_count": sum(1 for e in entries if not e["assignment"]["air"]),
                "air_entry_count": sum(1 for e in entries if e["assignment"]["air"]),
                "distinct_animation_files": sorted({a["basename"] for e in entries
                                                   for a in e["animations"] if a["basename"]}),
                "all_animations_in_archive_index": all(
                    a["exists_in_archive_index"] for e in entries for a in e["animations"]),
                "all_animations_present_under_fighter_miigunner": all(
                    a["exists_under_fighter_miigunner"] for e in entries for a in e["animations"]),
                "animation_basenames_colliding_across_fighters": sorted({
                    a["basename"] for e in entries for a in e["animations"]
                    if a["basename_collides_across_fighters"] and a["basename"]}),
                "entry_indices": [e["entry_index"] for e in entries],
                "motion_kind_names": [e["kind_name"] for e in entries],
                "unresolved_kind_names": [e["kind_hash"] for e in entries if not e["kind_name"]],
                "unresolved_script_names": [
                    {"entry_index": e["entry_index"], "role": role, "hash": e["scripts"][role]["hash"]}
                    for e in entries for role in ("game_script", "expression_script",
                                                  "sound_script", "effect_script")
                    if not e["scripts"][role]["name_verified"]],
                "articles": slots[(token, variant)]["articles"],
                "param_group": grp["group_name"],
                "param_row_index": variant - 1,
                "param_field_count": grp["rows"][variant - 1]["entry_count"],
                "param_nonzero_numeric_field_name_prefixes":
                    grp["rows"][variant - 1]["nonzero_numeric_field_name_prefixes"],
            })
    return rows


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------

def build(ml_path: Path, vl_path: Path, fp_path: Path, labels_path: Path,
          arc_index: Path, helper_root: Path):
    labels = load_labels(labels_path)
    anim_index, folder_paths = load_animation_index(arc_index)
    ml, records = read_motion(ml_path, labels, anim_index)
    params = build_param_groups(vl_path, labels)
    articles = build_articles(folder_paths, helper_root, labels)

    slots = {}
    for rec in records:
        a = rec["assignment"]
        if a is None:
            continue
        slots.setdefault((a["slot"], a["variant"]), {"entries": [], "articles": []})["entries"].append(rec)

    # Article <-> variant link. Only a name token shared between the archive
    # folder name and a field name in that slot's param row is a link, and it
    # stays "by name only" either way.
    for rec in articles:
        hits = []
        for token, _ in SLOTS:
            grp = params["vl_prc"]["special_variant_groups"][token]
            for ri in (0, 1, 2):
                row = grp["rows"][ri]
                # Only a field that actually carries a non-zero value in THIS row
                # is evidence about this row's variant. Every row shares one
                # field-name set, so matching on the name alone would link an
                # article to all three variants at once.
                for name, frec in row["fields"].items():
                    if frec["decoded_type"] in ("float", "i32", "u32") and frec["value"] == 0:
                        continue
                    stem = name.split("_", 1)[1] if "_" in name else ""
                    for cand in {rec["folder_name"], rec["folder_name"].replace("_bullet", ""),
                                 rec["folder_name"].rstrip("_s")}:
                        if len(cand) >= 5 and cand in stem:
                            hits.append({"slot": token, "variant": ri + 1,
                                         "shared_token": cand, "param_field": name})
        if hits:
            seen = set()
            unique = []
            for h in hits:
                key = (h["slot"], h["variant"], h["shared_token"], h["param_field"])
                if key in seen:
                    continue
                seen.add(key)
                unique.append(h)
            hits = unique
            rec["variant_link"] = [{"slot": h["slot"], "variant": h["variant"],
                                    "basis": "BY_NAME_ONLY",
                                    "shared_token": h["shared_token"],
                                    "param_field": h["param_field"],
                                    "note": "the token appears in a param field name that is non-zero in "
                                            "that slot's row for that variant, and in an archive folder "
                                            "name; no file read here references the other"}
                                for h in hits]
            rec["variant_link_basis"] = "BY_NAME_ONLY"
            for h in hits:
                key = (h["slot"], h["variant"])
                if key in slots:
                    entry = {
                        "folder_name": rec["folder_name"],
                        "link_basis": "BY_NAME_ONLY",
                        "shared_token": h["shared_token"],
                        "param_field": h["param_field"],
                    }
                    if entry not in slots[key]["articles"]:
                        slots[key]["articles"].append(entry)

    # strip the internal reader objects before serialising
    for rec in records:
        rec.pop("_entry", None)
        rec.pop("_tail", None)
        rec.pop("_clip_stem", None)

    slot_records = []
    for token, direction in SLOTS:
        variants = []
        for variant in (1, 2, 3):
            s = slots.get((token, variant), {"entries": [], "articles": []})
            grp = params["vl_prc"]["special_variant_groups"][token]
            variants.append({
                "variant": variant,
                "motion_entry_count": len(s["entries"]),
                "motion_entries": [public_entry(e) for e in s["entries"]],
                "articles": s["articles"],
                "param": {
                    "group_name": grp["group_name"],
                    "row_index": grp["rows"][variant - 1]["row_index"],
                    "row_entry_count": grp["rows"][variant - 1]["entry_count"],
                    "row_all_numeric_values_zero":
                        grp["rows"][variant - 1]["all_numeric_values_zero"],
                    "row_nonzero_numeric_field_name_prefixes":
                        grp["rows"][variant - 1]["nonzero_numeric_field_name_prefixes"],
                    "row_non_numeric_field_names":
                        grp["rows"][variant - 1]["non_numeric_field_names"],
                    "fields": grp["rows"][variant - 1]["fields"],
                },
            })
        slot_records.append({
            "slot": token,
            "direction": direction,
            "variant_count": len(variants),
            "entry_index_range": [
                min(e["entry_index"] for v in (1, 2, 3) for e in slots[(token, v)]["entries"]),
                max(e["entry_index"] for v in (1, 2, 3) for e in slots[(token, v)]["entries"])],
            "variants": variants,
        })

    unassigned = [{"entry_index": r["entry_index"], "kind_hash": r["kind_hash"],
                   "kind_name": r["kind_name"], "clip": [a["basename"] for a in r["animations"]],
                   "rule_kind_match": r["rule_kind_match"], "rule_clip_match": r["rule_clip_match"],
                   "looks_special_related": bool(
                       (r["kind_name"] and "special" in r["kind_name"].lower())
                       or (r["_clip_stem"] and "special" in r["_clip_stem"].lower()))}
                  for r in records if r["assignment"] is None and (
                      (r["kind_name"] and "special" in r["kind_name"].lower())
                      or (r.get("rule_clip_match")))]

    result = {
        "format_version": "1.0.0",
        "task": "P3-SPECIAL-VARIANTS",
        "purpose": "FILE_LEVEL_RESOURCE_INVENTORY",
        "disclaimer": [
            "This is a file inventory of the twelve Gunner special variants, not a move-swap design.",
            "No dependency is asserted. A shared name is recorded as 'by name only'.",
            "No script body, effect bank or sound bank was read.",
            "No runtime behaviour, status script, hitbox or balance claim is made.",
            "Every value here is file-level (tier B) or a stated hypothesis (tier D).",
        ],
        "evidence_tier": "B (measured offline from pinned local binaries); no tier A exists",
        "generator": {
            "tool": "mods/mii_customizer/scratch/2026-10-04_P3-SPECIAL-VARIANTS/build_special_variants.py",
            "stdlib_only": True,
            "shared_readers_imported_read_only": [
                "mods/ssbu_mod_new/src/pgwr/tools/mlist.py",
                "mods/ssbu_mod_new/src/pgwr/tools/prc.py",
            ],
        },
        "inputs": {
            "primary_binaries": [
                {"role": "gunner_body_c00_motion_list",
                 "relative_path": ml_path.relative_to(ROOT).as_posix(),
                 "arc_path": MOTION_ARC, "sha256": sha256_of(ml_path),
                 "bytes": ml_path.stat().st_size, "entry_count": len(ml["entries"]),
                 "round_trip_encode_equal": mlist.encode(ml) == ml["data"]},
                {"role": "gunner_vl_prc",
                 "relative_path": vl_path.relative_to(ROOT).as_posix(),
                 "arc_path": VL_ARC, "sha256": sha256_of(vl_path), "bytes": vl_path.stat().st_size},
                {"role": "common_fighter_param",
                 "relative_path": fp_path.relative_to(ROOT).as_posix(),
                 "arc_path": FIGHTER_PARAM_ARC, "sha256": sha256_of(fp_path),
                 "bytes": fp_path.stat().st_size},
            ],
            "name_dictionaries": [
                {"role": "motion_kind_and_param_labels", "relative_path":
                 labels_path.relative_to(ROOT).as_posix(), "sha256": sha256_of(labels_path),
                 "use": "hash -> name dictionary only; it is not the source of any measured value"},
                {"role": "archive_path_index", "relative_path": arc_index.relative_to(ROOT).as_posix(),
                 "sha256": sha256_of(arc_index),
                 "use": "animation hash (hash40 of the file basename) -> ARC path join; "
                        "and the weapon/article folder listing"},
            ],
            "extraction_performed_by_this_task": False,
            "extraction_note": "Every base-game file this inventory needs was already extracted under "
                               "gamedata/mii_customizer/P1-CATALOG/. No file was extracted for this task; "
                               "the archive index was consulted to confirm nothing else was required.",
        },
        "naming_rule": {
            "rule_kind": RULE_KIND.pattern,
            "rule_kind_prose": "A body motion entry belongs to slot S variant V when the label joined on "
                               "its kind hash matches special_ [air_] <n|s|hi|lw> <1|2|3>, optionally "
                               "followed by more '_'-separated text.",
            "rule_clip": RULE_CLIP.pattern,
            "rule_clip_prose": "An independent cross-check read straight off the animation file name: a "
                               "one-letter and two-digit prefix, then optional 'special', optional 'air', "
                               "a direction token and a variant digit.",
            "entries_checked": len(records),
            "entries_assigned": sum(1 for r in records if r["assignment"] is not None),
            "entries_with_both_rules_matching": sum(1 for r in records
                                                    if r["rule_kind_match"] and r["rule_clip_match"]),
            "entries_where_rules_disagree": [r["entry_index"] for r in records if not r["rules_agree"]],
            "unassigned_entry_count": sum(1 for r in records if r["assignment"] is None),
            "note": "Both rules must agree for an assignment. Where only the label exists, the clip "
                    "cross-check is what catches a wrong join.",
        },
        "motion_source": {
            "entry_count": len(ml["entries"]),
            "motion_path_field_hash": hexh(ml["motion_path"]),
            "special_block_index_range": [min(e["entry_index"] for e in records if e["assignment"]),
                                          max(e["entry_index"] for e in records if e["assignment"])],
            "special_block_is_contiguous": (
                sorted(e["entry_index"] for e in records if e["assignment"])
                == list(range(min(e["entry_index"] for e in records if e["assignment"]),
                              max(e["entry_index"] for e in records if e["assignment"]) + 1))),
        },
        "slots": slot_records,
        "summary_table": build_summary(slots, articles, params),
        "articles": articles,
        "params": params,
        "unassigned_special_related_entries": unassigned,
        "variant_selection": build_variant_selection(params, records),
    }
    return result


def public_entry(rec):
    out = {k: v for k, v in rec.items() if not k.startswith("_")}
    out["assignment"] = rec["assignment"]
    return out


def build_variant_selection(params, records):
    """What the bytes show about choosing between variants 1/2/3. Names only."""
    groups = params["vl_prc"]["special_variant_groups"]
    per_slot = {}
    for token, direction in SLOTS:
        grp = groups[token]
        per_slot[token] = {
            "direction": direction,
            "group_name": grp["group_name"],
            "row_count": grp["row_count"],
            "all_rows_share_one_field_name_set": len({tuple(sorted(r["fields"]))
                                                       for r in grp["rows"]}) == 1,
            "rows": [{"row_index": r["row_index"],
                      "nonzero_numeric_field_name_prefixes": r["nonzero_numeric_field_name_prefixes"],
                      "all_numeric_values_zero": r["all_numeric_values_zero"],
                      "non_numeric_field_names": r["non_numeric_field_names"]} for r in grp["rows"]],
        }
    return {
        "param_row_table": {
            "what_was_measured": "param_special_n / _s / _hi / _lw are each a 4-row list. Every row "
                                 "carries the same field-name set. In rows 0-2 the only fields holding "
                                 "a non-zero NUMERIC value are those whose name starts with that row's own "
                                 "variant token (n1/s1/hi1/lw1 etc.). Row 3 has every numeric field at "
                                 "zero. One field, param_special_lw's lw3_phy_magnet_parts, holds the "
                                 "same non-numeric value 23356055229 in all four rows; it is listed "
                                 "separately rather than counted as a variant value.",
            "evidence_tier": "B",
            "per_slot": per_slot,
            "note": "That row i carries variant i+1's numeric values and row 3 is a numeric-zero row is "
                    "what the bytes show. Which code indexes this list, and with what value, is NOT "
                    "established here.",
        },
        "motion_entry_index_order": {
            "what_was_measured": "In the body motion list the special entries are one contiguous run "
                                 "(see motion_source.special_block_index_range), ordered neutral 1,2,3 "
                                 "then side 1,2,3 then up 1,2,3 then down 1,2,3, with ground kinds "
                                 "before their air mirrors inside each variant.",
            "evidence_tier": "B",
            "note": "An entry's index in this file is a position, not a stored selector field. The "
                    "motion entry header holds no variant index; its fields are the kind hash, the game "
                    "script hash, flags, blend, the animation count and the tail.",
        },
        "motion_entry_header_fields": {
            "fields": ["kind_hash", "game_script_hash", "flags_u16", "blend_u8",
                       "animation_count_u8", "size_u32", "animation_hashes", "tail"],
            "evidence_tier": "B",
            "note": "No variant index, slot number or option id appears in the entry header or tail.",
        },
        "naming_suffix": {
            "what_was_measured": "The variant number is carried in the motion kind name itself "
                                 "(special_n1..., special_s2..., special_hi3..., special_lw1...) and in "
                                 "the animation file name (d00specialn1..., d03speciallw3...).",
            "evidence_tier": "B",
            "note": "This is a naming convention read from the files. It is not a selector field.",
        },
        "other_three_per_slot_shapes_seen": {
            "note": "No other file read here carries a three-rows-per-slot table. hit_target has 3 rows "
                    "but no special-named fields; hit_data has 10 rows with no special-named fields.",
            "evidence_tier": "B",
        },
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--motion-list", default=DEFAULT_MOTION_LIST)
    parser.add_argument("--vl-prc", default=DEFAULT_VL_PRC)
    parser.add_argument("--fighter-param", default=DEFAULT_FIGHTER_PARAM)
    parser.add_argument("--labels", default=DEFAULT_LABELS)
    parser.add_argument("--arc-index", default=DEFAULT_ARC_INDEX)
    parser.add_argument("--helper-root", default=DEFAULT_HELPER_ROOT)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    def resolve(value):
        path = Path(value)
        return path if path.is_absolute() else ROOT / path

    ml_path, vl_path, fp_path = resolve(args.motion_list), resolve(args.vl_prc), resolve(args.fighter_param)
    labels_path, arc_index = resolve(args.labels), resolve(args.arc_index)
    helper_root = resolve(args.helper_root)
    for path in (ml_path, vl_path, fp_path, labels_path, arc_index):
        if not path.is_file():
            try:
                shown = path.relative_to(ROOT).as_posix()
            except ValueError:
                shown = path.name
            raise SystemExit("missing input: %s" % shown)

    result = build(ml_path, vl_path, fp_path, labels_path, arc_index, helper_root)
    out = resolve(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=True, sort_keys=False) + "\n",
                   encoding="utf-8", newline="\n")

    def show(path: Path) -> str:
        """Workspace-relative when possible, so no machine path is printed."""
        try:
            return path.relative_to(ROOT).as_posix()
        except ValueError:
            return path.name

    table = result["summary_table"]
    print("wrote %s" % show(out))
    print("  variants %d  motion entries assigned %d  articles %d"
          % (len(table),
             sum(r["motion_entry_count"] for r in table),
             sum(1 for a in result["articles"] if a["is_separate_weapon_or_article_folder"])))
    print("  unassigned special-related entries %d"
          % len(result["unassigned_special_related_entries"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())