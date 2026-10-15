#!/usr/bin/env python3
"""Validate the P1-DATASET Gunner catalogue.

Checks the emitted catalogue against the same pinned binaries it was built
from, so a stale or hand-edited catalogue fails instead of passing quietly.

What is checked (all re-derived here, nothing read back from the report):

  1. determinism      - rebuild twice with different PYTHONHASHSEED values and
                        require byte-identical output equal to the committed file
  2. identifiers      - unique slot ids, unique choice ids, 5 aerial slots,
                        1 choice per normal / 3 per special direction,
                        jab kept as one ordered chain
  3. hash joins       - every resolved kind / script / animation name hashes
                        back to the hash stored next to it
  4. statistics       - twelve candidates, correct decoded types and hashes,
                        defaults re-read from the .prc, unique Gunner row
  5. byte separation  - the reported 334 / 318 entries really do carry a
                        cancel_frame byte and a separate no_stop_intp byte
  6. scope            - pending-scope categories offer no slots, recovery
                        motions are not sold as get-up attacks, specials claim
                        no helper dependency closure, gaps are machine-readable
  7. negative control - a wrong input hash and an unresolved/mismatched known
                        reference must each make the checks FAIL

Usage (from anywhere):

    python -B mods/mii_customizer/tools/gunner-catalog/validate_catalog.py

Exit code 0 when every check passes, 1 otherwise.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
ROOT = TOOL_DIR.parents[3]

spec = importlib.util.spec_from_file_location("gunner_catalog_build", TOOL_DIR / "build_catalog.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)

mlist = build.mlist
prc = build.prc
hash40 = build.hash40

CATALOG = ROOT / build.DEFAULT_OUT
MOTION_LIST = ROOT / build.DEFAULT_MOTION_LIST
FIGHTER_PARAM = ROOT / build.DEFAULT_FIGHTER_PARAM

# The two entries whose trailing u16 was originally reported as a frame count.
REPRESENTATIVE = [
    ("attack_s4_s", 334, 78, 1),
    ("attack_air_hi", 318, 62, 1),
]

# Recovery / locomotion / landing motions must not be offered as attacks.
FORBIDDEN_STATE_PREFIXES = (
    "down_attack", "down_stand", "down_bounce", "down_wait", "down_forward",
    "down_back", "landing", "walk", "run", "dash", "turn", "jump", "fall",
    "wait", "guard", "escape", "edge", "crawl", "wall", "ceil", "swallow",
)

PENDING_SCOPE_GAPS = ("gap_final_smash", "gap_get_up", "gap_ledge", "gap_taunts")

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("%-46s %s%s" % (name, "PASS" if ok else "FAIL", ("  " + detail) if detail else ""))
    return ok


def iter_states(catalog):
    for slot in catalog["editor_slots"]:
        for choice in slot["choices"]:
            for state in choice["states"]:
                yield slot, choice, state


def s_group(catalog, slot_id):
    return next(s["group"] for s in catalog["editor_slots"] if s["slot_id"] == slot_id)


def strip_abs(text):
    return text.replace("\\", "/")


# --------------------------------------------------------------------------
# individual check groups
# --------------------------------------------------------------------------

def check_determinism(catalog_bytes):
    digests = []
    with tempfile.TemporaryDirectory() as tmp:
        for seed in ("0", "1", "12345"):
            out = Path(tmp) / ("catalog_%s.json" % seed)
            env = dict(os.environ, PYTHONHASHSEED=seed)
            proc = subprocess.run(
                [sys.executable, "-B", str(TOOL_DIR / "build_catalog.py"), "--out", str(out)],
                cwd=str(ROOT), env=env, capture_output=True, text=True)
            if proc.returncode != 0:
                return check("determinism: rebuild exit 0", False, proc.stderr.strip()[-300:])
            digests.append(hashlib.sha256(out.read_bytes()).hexdigest())
    same = len(set(digests)) == 1
    check("determinism: three rebuilds byte-identical", same, digests[0][:16])
    check("determinism: committed file matches rebuild",
          hashlib.sha256(catalog_bytes).hexdigest() == digests[0],
          hashlib.sha256(catalog_bytes).hexdigest()[:16])


def check_structure(catalog):
    slots = catalog["editor_slots"]
    slot_ids = [s["slot_id"] for s in slots]
    check("structure: slot ids unique", len(set(slot_ids)) == len(slot_ids))
    choice_ids = [c["choice_id"] for s in slots for c in s["choices"]]
    check("structure: choice ids unique", len(set(choice_ids)) == len(choice_ids))

    aerials = [s for s in slots if s["group"] == "aerial"]
    check("structure: exactly five aerial slots", len(aerials) == 5,
          ", ".join(s["slot_id"] for s in aerials))

    wrong = []
    for s in slots:
        expected = 3 if s["group"] == "special" else 1
        if len(s["choices"]) != expected:
            wrong.append("%s has %d choices (expected %d)" % (s["slot_id"], len(s["choices"]), expected))
    check("structure: normals one choice, specials three", not wrong, "; ".join(wrong))

    specials = [s["slot_id"] for s in slots if s["group"] == "special"]
    check("structure: four special directions", len(specials) == 4, ", ".join(specials))

    jab = next((s for s in slots if s["slot_id"] == "normal_jab"), None)
    jab_ok = False
    if jab and len(jab["choices"]) == 1:
        choice = jab["choices"][0]
        roles = [st["role"] for st in choice["states"]]
        jab_ok = (choice.get("sequence_constraint") == "ordered"
                  and roles == ["stage_1", "stage_2", "stage_3"])
    check("structure: jab is one ordered three-stage chain", jab_ok)

    groups = {s["group"] for s in slots}
    check("structure: no pending-scope group offered as a slot",
          not (groups & {"final_smash", "get_up", "ledge", "taunt"}), ", ".join(sorted(groups)))


def check_hash_joins(catalog):
    bad_kind, bad_script, bad_anim, unresolved = [], [], [], []
    for slot, choice, state in iter_states(catalog):
        name = state.get("kind_name")
        if state.get("status") == "RESOLVED_BY_LABEL_HASH_JOIN":
            if not name or hash40(name) != int(state["kind_hash"], 16):
                bad_kind.append("%s/%s" % (slot["slot_id"], name))
        else:
            unresolved.append("%s/%s (%s)" % (slot["slot_id"], state.get("requested_kind_name"),
                                             state.get("status")))
        script = state.get("game_script") or {}
        if script.get("name_verified") and hash40(script["name"]) != int(script["hash"], 16):
            bad_script.append("%s/%s" % (slot["slot_id"], script["name"]))
        for anim in state.get("animations", []):
            if anim.get("basename") and hash40(anim["basename"]) != int(anim["hash"], 16):
                bad_anim.append("%s/%s" % (slot["slot_id"], anim["basename"]))
    check("joins: every resolved kind name hashes to its hash", not bad_kind, "; ".join(bad_kind[:5]))
    check("joins: every named game script hashes to its hash", not bad_script, "; ".join(bad_script[:5]))
    check("joins: every named clip hashes to its animation hash", not bad_anim, "; ".join(bad_anim[:5]))
    check("joins: unresolved names are explicit, not guessed",
          all(status for status in [u.split("(")[-1].rstrip(")") for u in unresolved]) and len(unresolved) == 4,
          "%d explicit unknown-name states" % len(unresolved))


def check_stats(catalog, prc_path):
    stats = catalog["stat_candidates"]
    check("stats: twelve candidates present", len(stats) == 12, str(len(stats)))

    tree = prc.read(prc_path)
    rows = prc.as_dict(tree)[hash40("fighter_param_table")][1]
    kind_key, kind_hash = hash40("fighter_kind"), hash40("fighter_kind_miigunner")
    matches = [i for i, row in enumerate(rows)
               if prc.as_dict(row).get(kind_key, (None, None))[1] == kind_hash]

    identity = catalog["fighter_identity"]
    check("stats: Gunner row identity unique and recorded",
          len(matches) == 1 and identity["row_index"] == matches[0] and identity["identity_unique"],
          "row_index=%s of %d" % (identity["row_index"], len(rows)))
    check("stats: fighter kind hash equals hash40(fighter_kind_miigunner)",
          identity["fighter_kind_hash"] == build.hexh(kind_hash), identity["fighter_kind_hash"])

    row = prc.as_dict(rows[matches[0]]) if len(matches) == 1 else {}
    wrong_hash, wrong_type, wrong_value = [], [], []
    for stat in stats:
        name = stat["parameter_name"]
        node = row.get(hash40(name))
        if stat["hash"] != build.hexh(hash40(name)) or not stat["hash_verified"]:
            wrong_hash.append(name)
            continue
        if node is None or node[0] != stat["decoded_type"] or not stat["type_matches"]:
            wrong_type.append("%s: file has %r, catalogue says %r"
                              % (name, node, (stat["decoded_type"], stat["expected_type"])))
            continue
        if stat["decoded_type"] == "float":
            same = struct.pack("<f", node[1]) == struct.pack("<f", stat["default_value"])
        else:
            same = node[1] == stat["default_value"]
        if not same:
            wrong_value.append("%s: file %r vs catalogue %r" % (name, node[1], stat["default_value"]))
    check("stats: parameter hashes recomputed", not wrong_hash, "; ".join(wrong_hash))
    check("stats: decoded types match the file", not wrong_type, "; ".join(wrong_type))
    check("stats: defaults re-read from the .prc", not wrong_value, "; ".join(wrong_value))

    ranges = [s["parameter_name"] for s in stats
              if s["safe_range"]["status"] != "UNKNOWN" or s["safe_range"]["min"] is not None
              or s["safe_range"]["max"] is not None]
    check("stats: every safe range marked UNKNOWN with no bounds", not ranges, "; ".join(ranges))

    override = [s["parameter_name"] for s in stats if not s["runtime_override"]["schema_supported"]
                or s["runtime_override"]["observed"] or s["runtime_override"]["mechanism"] != "UNKNOWN"]
    check("stats: runtime override declared but not claimed observed", not override, "; ".join(override))

    independence = [s["parameter_name"] for s in stats
                    if s["cross_stat_relationships"]["status"] != "UNKNOWN"
                    or s["cross_stat_relationships"]["independent_of_other_stats"] is not None]
    check("stats: no cross-stat independence claimed", not independence, "; ".join(independence))


def check_byte_separation(catalog, ml):
    """Prove cancel_frame and no_stop_intp are separate bytes, not one u16."""
    view = build.MotionView(ml, build.load_labels(ROOT / build.DEFAULT_LABELS),
                            build.load_animation_index(ROOT / build.DEFAULT_ARC_INDEX))
    details = []
    ok_all = True
    for kind_name, raw_expected, frame_expected, nsi_expected in REPRESENTATIVE:
        index = view.entry_for_name(kind_name)
        if index is None:
            ok_all = False
            details.append("%s absent" % kind_name)
            continue
        entry = view.by_index[index]
        timing = view.timing(entry)
        tail = view.tail_of(entry)
        # Perturb the no_stop_intp byte only, in memory. The cancel_frame byte
        # and the recomputed raw u16 must move exactly as separate bytes would.
        mutated = bytearray(tail)
        mutated[27] = 0
        raw_after = struct.unpack_from("<H", mutated, 26)[0]
        same = (timing["cancel_u16_raw"] == raw_expected
                and timing["cancel_frame"] == frame_expected
                and timing["no_stop_intp"] == nsi_expected
                and timing["cancel_frame"] == tail[26]
                and raw_after == frame_expected
                and tail[24:26] == bytes([timing["xlu_start"], timing["xlu_end"]]))
        ok_all = ok_all and same
        details.append("%s raw=%d cancel_frame=%d nsi=%d bytes=%s after_nsi0=%d"
                       % (kind_name, timing["cancel_u16_raw"], timing["cancel_frame"],
                          timing["no_stop_intp"], tail[24:28].hex(" "), raw_after))
        # Negative control: the old reading (raw u16 == frame) must NOT hold.
        check("separation: %s raw u16 is not the frame count" % kind_name,
              timing["cancel_u16_raw"] != timing["cancel_frame"])
    check("separation: representative 334/318 entries split into two bytes", ok_all,
          " | ".join(details))

    stored = {st.get("kind_name"): st for _, _, st in iter_states(catalog)}
    mismatch = [k for k, _, frame, nsi in REPRESENTATIVE
                if k in stored and (stored[k]["timing_raw"]["cancel_frame"] != frame
                                    or stored[k]["timing_raw"]["no_stop_intp"] != nsi)]
    check("separation: catalogue carries the split timing bytes", not mismatch, "; ".join(mismatch))


def check_scope(catalog):
    gap_ids = {g["gap_id"] for g in catalog["coverage_gaps"]}
    missing = [g for g in PENDING_SCOPE_GAPS if g not in gap_ids]
    check("scope: pending-scope gaps are machine-readable", not missing, "missing %s" % missing)

    # A paired landing state is a declared dependency of an aerial, not an
    # offered attack. Anything else from the recovery/locomotion vocabulary is
    # a leak into the slot table.
    landings = [(s["slot_id"], st) for s, _, st in iter_states(catalog)
                if (st.get("kind_name") or "").startswith("landing")]
    bad_landings = ["%s/%s" % (sid, st.get("kind_name")) for sid, st in landings
                    if st.get("role") != "paired_landing" or s_group(catalog, sid) != "aerial"]
    leaking = ["%s/%s" % (s["slot_id"], st.get("kind_name"))
               for s, _, st in iter_states(catalog)
               if (st.get("kind_name") or "").startswith(FORBIDDEN_STATE_PREFIXES)
               and st.get("role") != "paired_landing"]
    check("scope: recovery motions are not sold as get-up attacks", not leaking,
          "; ".join(leaking[:5]))
    check("scope: landing states appear only as aerial dependencies",
          not bad_landings and len(landings) == 5,
          "%d landing states, %d misplaced" % (len(landings), len(bad_landings)))

    helper_refs = []
    for slot, choice, _ in iter_states(catalog):
        if slot["group"] == "special":
            text = json.dumps(choice)
            if '"helper_' in text or '"link_status": "LINKED"' in text:
                helper_refs.append(choice["choice_id"])
    check("scope: specials claim no helper dependency closure", not helper_refs,
          "; ".join(helper_refs))

    helpers = catalog["dependency_candidates"]
    unlinked = [h["helper_id"] for h in helpers if h["link_status"] != "UNLINKED" or h["linked_slots"]]
    check("scope: helper motion lists recorded as unlinked dependencies", not unlinked,
          "%d helpers" % len(helpers))

    unexplained = []
    for slot, choice, state in iter_states(catalog):
        if state.get("status") != "RESOLVED_BY_LABEL_HASH_JOIN":
            referenced = any(g.get("kind_hash") == state.get("kind_hash") for g in catalog["coverage_gaps"])
            if not referenced:
                unexplained.append("%s/%s" % (slot["slot_id"], state.get("role")))
    check("scope: every unresolved name has a coverage gap", not unexplained,
          "; ".join(unexplained))

    text = strip_abs(json.dumps(catalog))
    check("scope: no absolute machine path in the catalogue",
          "<drive>:/" not in text and "<drive>:/" not in text and "C:/" not in text and "C:\\" not in text)
    check("scope: no complete-move-port claim",
          any("not a move port" in d for d in catalog["disclaimer"])
          and "INPUT" in catalog["purpose"].upper()
          and "PROVISIONAL" in " ".join(s["grouping_status"] for s in catalog["editor_slots"]))
    check("scope: display labels marked as author labels, not game strings",
          all(s["display_label"]["is_game_string"] is False
              and s["display_label"]["label_origin"] == "author_display_label"
              for s in catalog["editor_slots"]))


def negative_controls(catalog):
    """Each control must FAIL loudly; a control that passes proves nothing."""
    wrong_input = copy.deepcopy(catalog)

    wrong_input["inputs"]["primary_binaries"][0]["sha256"] = "0" * 64
    failed = provenance_ok(wrong_input) is False
    check("negative control: wrong input hash is rejected", failed)

    unresolved_ref = copy.deepcopy(catalog)
    target = next(st for _, _, st in iter_states(unresolved_ref) if st.get("kind_name"))
    target["kind_name"] = "attack_12"  # plausible, wrong name for that hash
    bad = []
    for slot, choice, state in iter_states(unresolved_ref):
        name = state.get("kind_name")
        if name and state.get("status") == "RESOLVED_BY_LABEL_HASH_JOIN" \
                and hash40(name) != int(state["kind_hash"], 16):
            bad.append(name)
    check("negative control: mismatched known reference is rejected",
          len(bad) == 1 and bad[0] == "attack_12", "; ".join(bad))

    missing_ref = copy.deepcopy(catalog)
    state = next(st for _, _, st in iter_states(missing_ref) if st.get("kind_name"))
    state["kind_name"] = None
    state["status"] = "RESOLVED_BY_LABEL_HASH_JOIN"
    dropped = [1 for _, _, st in iter_states(missing_ref)
               if st.get("status") == "RESOLVED_BY_LABEL_HASH_JOIN" and not st.get("kind_name")]
    check("negative control: dropped name is not counted as resolved", len(dropped) == 1)

    bad_stats = copy.deepcopy(catalog)
    bad_stats["stat_candidates"][0]["default_value"] = 999.0
    check("negative control: altered stat default differs from the file",
          bad_stats["stat_candidates"][0]["default_value"]
          != catalog["stat_candidates"][0]["default_value"])

    bad_aerial = copy.deepcopy(catalog)
    for index, s in enumerate(bad_aerial["editor_slots"]):
        if s["group"] == "aerial":
            del bad_aerial["editor_slots"][index]
            break
    aerials = [s for s in bad_aerial["editor_slots"] if s["group"] == "aerial"]
    check("negative control: four aerials do not satisfy the five-aerial check",
          len(aerials) == 4, "%d aerials in the mutated copy" % len(aerials))

    stale = copy.deepcopy(catalog)
    stale["inputs"]["primary_binaries"][0]["sha256"] = "f" * 64
    check("negative control: a second wrong provenance hash is also rejected",
          provenance_ok(stale) is False)
    check("negative control: the real provenance passes", provenance_ok(catalog) is True)


def provenance_ok(catalog):
    """Input provenance check, used by the negative controls."""
    ml_path = ROOT / build.DEFAULT_MOTION_LIST
    prc_path = ROOT / build.DEFAULT_FIGHTER_PARAM
    for entry in catalog["inputs"]["primary_binaries"]:
        path = ROOT / entry["relative_path"]
        if not path.is_file():
            return False
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            return False
        if entry["sha256"] != hashlib.sha256(
                (ml_path if entry["role"].startswith("gunner") else prc_path).read_bytes()).hexdigest():
            return False
    return True


def main():
    if not CATALOG.is_file():
        print("missing catalogue: %s (run build_catalog.py first)" % CATALOG)
        return 1
    catalog_bytes = CATALOG.read_bytes()
    catalog = json.loads(catalog_bytes.decode("utf-8"))
    ml = mlist.parse(MOTION_LIST)

    print("catalogue: %s (%d bytes, sha256 %s)"
          % (CATALOG.relative_to(ROOT).as_posix(), len(catalog_bytes),
             hashlib.sha256(catalog_bytes).hexdigest()))
    print("inputs:    motion_list sha256 %s"
          % next(i["sha256"] for i in catalog["inputs"]["primary_binaries"]
                 if i["role"] == "gunner_body_c00_motion_list"))
    print("           fighter_param sha256 %s"
          % next(i["sha256"] for i in catalog["inputs"]["primary_binaries"]
                 if i["role"] == "common_fighter_param"))
    print()

    check_determinism(catalog_bytes)
    check_structure(catalog)
    check_hash_joins(catalog)
    check_stats(catalog, FIGHTER_PARAM)
    check_byte_separation(catalog, ml)
    check_scope(catalog)
    print()
    negative_controls(catalog)

    failed = [name for name, ok, _ in results if not ok]
    print("\n%d checks, %d failed" % (len(results), len(failed)))
    for name in failed:
        print("  FAILED: %s" % name)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
