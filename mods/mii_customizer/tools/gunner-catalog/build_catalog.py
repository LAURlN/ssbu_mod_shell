#!/usr/bin/env python3
"""Build the machine-readable Gunner move/stat catalogue (P1-DATASET).

Editor INPUT DATA. Not a save schema, not a loadout format, not a move port.

Stdlib only. The two binary inputs are re-read and re-decoded on every run, so
the output is recomputed from those bytes rather than copied out of a prose
report. The shared readers `mods/ssbu_mod_new/src/pgwr/tools/mlist.py` and
`.../prc.py` are imported read-only and are never modified.

Usage (from anywhere; paths default to the workspace layout):

    python -B mods/mii_customizer/tools/gunner-catalog/build_catalog.py \
        --out mods/mii_customizer/evidence/P1-DATASET/gunner_catalog.json

Design rules enforced here:

* Nothing is written unless it was found in a binary. A kind that cannot be
  resolved becomes an explicit unknown-name record, not a dropped entry.
* Display labels are plain English author labels authored in this file and are
  marked `label_origin: author_display_label`. They are never presented as
  game strings.
* Timing bytes are stored as authored bytes with their byte offsets. They are
  not runtime frame promises.
* No dependency closure is invented for the specials. Helper motion lists are
  listed as unlinked candidates only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
ROOT = TOOL_DIR.parents[3]

DEFAULT_MOTION_LIST = "gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin"
DEFAULT_FIGHTER_PARAM = "gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc"
DEFAULT_LABELS = "mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv"
DEFAULT_ARC_INDEX = "mods/ssbu_mod_new/dumps/decoded/arc_files.tsv"
DEFAULT_HELPER_ROOT = "gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion"
DEFAULT_OUT = "mods/mii_customizer/evidence/P1-DATASET/gunner_catalog.json"

MOTION_ARC_PATH = "fighter/miigunner/motion/body/c00/motion_list.bin"
FIGHTER_PARAM_ARC_PATH = "fighter/common/param/fighter_param.prc"
FIGHTER_KIND_NAME = "fighter_kind_miigunner"
PARAM_ROOT_LIST = "fighter_param_table"

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


def hexh(value: int) -> str:
    return "0x%010x" % value


def f32_bits(value: float) -> str:
    return "0x%08x" % struct.unpack("<I", struct.pack("<f", value))[0]


# --------------------------------------------------------------------------
# name resolution helpers
# --------------------------------------------------------------------------

def load_labels(path: Path) -> dict:
    """hash -> label, from the reference label table (a name dictionary only)."""
    labels = {}
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        for row in csv.reader(handle):
            if len(row) >= 2 and row[1] not in ("", "-1", "-2"):
                labels.setdefault(int(row[0], 16), row[1])
    return labels


def load_animation_index(path: Path) -> dict:
    """Animation hash -> ARC paths, joined on hash40(basename-with-extension).

    Basename hashing collides across motion folders; the full paths are kept so
    a collision stays visible instead of silently resolving to one file.
    """
    index = {}
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            arc_path = line.strip()
            if not arc_path.startswith("fighter/miigunner/") or not arc_path.endswith(".nuanmb"):
                continue
            index.setdefault(hash40(arc_path.rsplit("/", 1)[1]), []).append(arc_path)
    return index


# Game-script names are not in the label table. The naming rule recovered by
# P1-CATALOG-AUDIT is "game_" + the kind name with a trailing "_s" and the
# underscore before a digit dropped. Every derived name is accepted only when
# hash40(name) equals the entry's own game_script field, so a wrong rule fails
# loudly instead of inventing a name.
GAME_SCRIPT_OVERRIDES = {
    "attack_s4_hold": "game_attacks4charge",
    "attack_hi4_hold": "game_attackhi4charge",
    "attack_lw4_hold": "game_attacklw4charge",
}


def _strip_underscore_before_digit(stem: str) -> str:
    out = []
    for i, ch in enumerate(stem):
        if ch == "_" and i + 1 < len(stem) and stem[i + 1].isdigit():
            continue
        out.append(ch)
    return "".join(out)


def game_script_candidates(kind_name: str):
    """Plausible game-script names for a motion kind, in a fixed order.

    P1-CATALOG-AUDIT recovered the rule: the script name is "game_" plus the
    kind name with its separators dropped (attack_hi3 -> game_attackhi3,
    catch_attack -> game_catchattack, attack_s3_s -> game_attacks3,
    attack_s4_s -> game_attacks4). Charge holds swap the suffix
    (attack_s4_hold -> game_attacks4charge). Rather than commit to one form,
    every candidate is generated and accepted ONLY when hash40(candidate)
    equals the entry's own game_script field, so a wrong guess cannot leak in.
    """
    bases = [kind_name]
    if kind_name.endswith("_s"):
        bases.append(kind_name[:-2])
    if kind_name.endswith("_l"):
        # The down-special-1 "_l" states share their base state's script hash
        # (measured in P1-CATALOG-AUDIT), so the base name is tried too.
        bases.append(kind_name[:-2])
    bases.append(kind_name.replace("_hold", "charge"))
    out = []
    for base in bases:
        for stem in (base.replace("_", ""), _strip_underscore_before_digit(base).replace("_", "")):
            name = "game_" + stem
            if name not in out:
                out.append(name)
    return out


def derive_game_script_name(kind_name: str):
    """First candidate form (kept for provenance wording; acceptance is by hash)."""
    return game_script_candidates(kind_name)[0]


# --------------------------------------------------------------------------
# motion entry decoding
# --------------------------------------------------------------------------

class MotionView:
    def __init__(self, ml, labels, anim_index):
        self.ml = ml
        self.labels = labels
        self.anim_index = anim_index
        self.by_kind = {}
        self.by_index = {}
        for index, entry in enumerate(ml["entries"]):
            self.by_kind[entry["kind"]] = (index, entry)
            self.by_index[index] = entry

    def entry_for_name(self, kind_name):
        hit = self.by_kind.get(hash40(kind_name))
        return None if hit is None else hit[0]

    def name_of(self, kind_hash):
        return self.labels.get(kind_hash)

    def tail_of(self, entry):
        block = (entry["n"] * 9 + 3) & ~3
        return entry["raw"][24 + block:]

    def timing(self, entry):
        """The four separate authored bytes at the end of the entry tail.

        Byte layout pinned by P1-CATALOG-AUDIT against a decoded reference
        fighter: tail[24]=xlu_start, tail[25]=xlu_end, tail[26]=cancel_frame,
        tail[27]=no_stop_intp. Stored here as bytes with their offsets, plus
        the little-endian u16 read of the last two bytes so the packed raw
        value stays visible.
        """
        tail = self.tail_of(entry)
        if len(tail) < 28:
            return {
                "tail_length": len(tail),
                "status": "TIMING_BYTES_UNAVAILABLE",
                "cancel_frame_byte": None,
                "no_stop_intp_byte": None,
                "cancel_u16_raw": entry["cancel"],
            }
        raw_u16 = struct.unpack_from("<H", tail, 26)[0]
        return {
            "tail_length": len(tail),
            "byte_offsets": {"xlu_start": 24, "xlu_end": 25, "cancel_frame": 26, "no_stop_intp": 27},
            "xlu_start": tail[24],
            "xlu_end": tail[25],
            "cancel_frame": tail[26],
            "no_stop_intp": tail[27],
            "cancel_u16_raw": raw_u16,
            "no_stop_intp_bit": NO_STOP_INTP_BIT,
            "field_semantics_evidence": "B: P1-CATALOG-AUDIT vs decoded gamewatch_motion_list.yml (746/746 per offset)",
            "interpretation_note": (
                "Authored bytes in motion_list.bin. cancel_frame is the low byte and "
                "bit 0x100 of the same u16 is no_stop_intp; this is a parameter to copy, "
                "not a measured runtime cancel window and not a frame guarantee."
            ),
            "consistency_check": {
                "cancel_frame_matches_low_byte": (raw_u16 & CANCEL_FRAME_MASK) == tail[26],
                "no_stop_intp_matches_bit_0x100": bool(raw_u16 & NO_STOP_INTP_BIT) == bool(tail[27]),
            },
        }

    def animations(self, entry):
        out = []
        for anim_hash in entry["anims"]:
            paths = self.anim_index.get(anim_hash, [])
            out.append({
                "hash": hexh(anim_hash),
                "arc_paths": paths,
                "resolved": bool(paths),
                "name_source": "hash40(basename) join over the archive path index",
                "basename": paths[0].rsplit("/", 1)[1] if paths else None,
            })
        return out

    def state(self, kind_name, role, view_kind_hash=None, name_status=None):
        """One catalogued motion state, resolved from the binary by name."""
        wanted = hash40(kind_name) if view_kind_hash is None else view_kind_hash
        hit = self.by_kind.get(wanted)
        if hit is None:
            return {
                "role": role,
                "status": "KIND_NOT_FOUND_IN_INPUT",
                "requested_kind_name": kind_name,
                "kind_name": None,
                "kind_hash": hexh(wanted),
                "note": "named here but absent from the motion list; recorded instead of dropped",
            }
        index, entry = hit
        resolved_name = self.name_of(entry["kind"])
        gs_name = GAME_SCRIPT_OVERRIDES.get(resolved_name or "")
        gs_form = None
        if gs_name is None and resolved_name is not None:
            for candidate in game_script_candidates(resolved_name):
                if hash40(candidate) == entry["gs"]:
                    gs_name, gs_form = candidate, "form"
                    break
        if gs_name is not None and hash40(gs_name) != entry["gs"]:
            gs_name, gs_form = None, None  # never keep an unverified name
        if view_kind_hash is not None:
            status = name_status or "UNKNOWN_KIND_NAME_BY_HASH"
        elif resolved_name is None:
            status = "UNKNOWN_KIND_NAME"
        else:
            status = "RESOLVED_BY_LABEL_HASH_JOIN"
        record = {
            "role": role,
            "status": status,
            "entry_index": index,
            "kind_name": resolved_name,
            "requested_kind_name": kind_name,
            "kind_hash": hexh(entry["kind"]),
            "kind_hash_matches_name": (hash40(resolved_name) == entry["kind"]) if resolved_name else None,
            "game_script": {
                "hash": hexh(entry["gs"]),
                "name": gs_name,
                "name_source": (
                    "hash40(form) verified against the entry field (prior audited override)"
                    if gs_name and gs_form is None
                    else ("hash40(form) verified against the entry field"
                          if gs_name else "unresolved: no form matched this entry field")
                ),
                "name_verified": bool(gs_name) and hash40(gs_name) == entry["gs"],
            },
            "flags_raw_u16": entry["flags"],
            "flags_raw_hex": "0x%04x" % entry["flags"],
            "blend_raw_u8": entry["blend"],
            "animation_count": entry["n"],
            "animations": self.animations(entry),
            "timing_raw": self.timing(entry),
        }
        return record


def states(view, pairs):
    return [view.state(name, role) for role, name in pairs]


# --------------------------------------------------------------------------
# the provisional editor grouping
#
# Slot identifiers describe a user action. A normal has exactly one available
# choice because Gunner ships one move for it; the four special directions each
# have the three alternatives that already exist in the motion list. This
# grouping is an editor proposal, not proof of how the game routes input.
# --------------------------------------------------------------------------

def slot(slot_id, group, label, input_action, choice_specs, notes=None):
    return {
        "slot_id": slot_id,
        "group": group,
        "display_label": {
            "text": label,
            "label_origin": "author_display_label",
            "is_game_string": False,
            "note": "plain English label written by this tool; not a name from the game's own strings",
        },
        "input_action": input_action,
        "grouping_status": "PROVISIONAL_EDITOR_GROUPING",
        "grouping_note": (
            "Slot identity is an editor proposal built from motion kinds and hashes. "
            "It is not evidence that the engine routes this input to these kinds."
        ),
        "notes": notes or [],
        "choices": choice_specs,
    }


def simple_choice(choice_id, label, view, pairs, extra=None):
    return {
        "choice_id": choice_id,
        "display_label": {"text": label, "label_origin": "author_display_label", "is_game_string": False},
        "available": True,
        "states": states(view, pairs),
        **(extra or {}),
    }


def build_slots(view):
    slots = []

    slots.append(slot(
        "normal_jab", "normal", "Jab sequence", "press attack up to three times",
        [{
            "choice_id": "gunner_jab_chain",
            "display_label": {"text": "Gunner jab chain (1-2-3)", "label_origin": "author_display_label",
                              "is_game_string": False},
            "available": True,
            "sequence_constraint": "ordered",
            "sequence_note": (
                "The three stages belong to one chain. A stage is not offered as an independent "
                "attack and the stages are not freely mixable; stage order is the authored order "
                "in this file, which is not proof of the engine's chain order."
            ),
            "states": states(view, [
                ("stage_1", "attack_11"),
                ("stage_2", "attack_12"),
                ("stage_3", "attack_13"),
            ]),
        }],
        notes=["one choice: Gunner ships a single jab chain"],
    ))

    slots.append(slot(
        "normal_dash", "normal", "Dash attack", "attack while dashing",
        [simple_choice("gunner_dash_attack", "Gunner dash attack", view, [("move", "attack_dash")])],
    ))

    for slot_id, label, kind in (
        ("tilt_up", "Up tilt", "attack_hi3"),
        ("tilt_side", "Side / forward tilt", "attack_s3_s"),
        ("tilt_down", "Down tilt", "attack_lw3"),
    ):
        slots.append(slot(
            slot_id, "normal", label, "tilt stick",
            [simple_choice("gunner_" + slot_id, "Gunner " + label.lower(), view, [("move", kind)])],
            notes=["no directional variant of this kind exists in this motion list"],
        ))

    for slot_id, label, release, hold in (
        ("smash_forward", "Forward smash", "attack_s4_s", "attack_s4_hold"),
        ("smash_up", "Up smash", "attack_hi4", "attack_hi4_hold"),
        ("smash_down", "Down smash", "attack_lw4", "attack_lw4_hold"),
    ):
        slots.append(slot(
            slot_id, "normal", label, "smash stick",
            [{
                "choice_id": "gunner_" + slot_id,
                "display_label": {"text": "Gunner " + label.lower(), "label_origin": "author_display_label",
                                  "is_game_string": False},
                "available": True,
                "state_pair_note": (
                    "A smash is a release/hold state pair in this file. Both states belong to the "
                    "slot; shipping one without the other is an incomplete slot."
                ),
                "states": states(view, [("release", release), ("charge_hold", hold)]),
            }],
        ))

    for slot_id, label, kind, landing in (
        ("aerial_neutral", "Neutral aerial", "attack_air_n", "landing_air_n"),
        ("aerial_forward", "Forward aerial", "attack_air_f", "landing_air_f"),
        ("aerial_back", "Back aerial", "attack_air_b", "landing_air_b"),
        ("aerial_up", "Up aerial", "attack_air_hi", "landing_air_hi"),
        ("aerial_down", "Down aerial", "attack_air_lw", "landing_air_lw"),
    ):
        states_out = states(view, [("move", kind)])
        states_out += states(view, [("paired_landing", landing)])
        slots.append(slot(
            slot_id, "aerial", label, "aerial stick in the air",
            [{
                "choice_id": "gunner_" + slot_id,
                "display_label": {"text": "Gunner " + label.lower(), "label_origin": "author_display_label",
                                  "is_game_string": False},
                "available": True,
                "states": states_out,
            }],
            notes=["each direction owns a distinct aerial kind and a distinct paired landing kind"],
        ))

    slots.append(slot(
        "grab", "grab", "Grab family", "grab button",
        [{
            "choice_id": "gunner_grab_chain",
            "display_label": {"text": "Gunner grab chain", "label_origin": "author_display_label",
                              "is_game_string": False},
            "available": True,
            "state_pair_note": "One grab action owns these states; they are not separate offers.",
            "states": states(view, [
                ("grab_start", "catch"),
                ("dash_grab", "catch_dash"),
                ("turn_grab", "catch_turn"),
                ("pull", "catch_pull"),
                ("hold", "catch_wait"),
                ("escape_cut", "catch_cut"),
            ]),
            "dependency_note": (
                "The victim-side capture states are separate entries in the same file and are "
                "recorded under dependencies. No link from script bodies was read."
            ),
        }],
    ))

    slots.append(slot(
        "pummel", "grab", "Pummel", "grab button while holding the opponent",
        [simple_choice("gunner_pummel", "Gunner pummel", view, [("move", "catch_attack")])],
    ))

    for slot_id, label, kind in (
        ("throw_forward", "Forward throw", "throw_f"),
        ("throw_back", "Back throw", "throw_b"),
        ("throw_up", "Up throw", "throw_hi"),
        ("throw_down", "Down throw", "throw_lw"),
    ):
        slots.append(slot(
            slot_id, "throw", label, "throw direction while holding the opponent",
            [simple_choice("gunner_" + slot_id, "Gunner " + label.lower(), view, [("move", kind)])],
            notes=["a throw also has a victim-side reaction entry; see dependencies"],
        ))

    # --- specials: three existing alternatives per direction ----------------
    special_defs = {
        "special_neutral": ("Neutral special", "down", [
            ("alt_1", "Neutral special option 1", [
                ("start", "special_n1_start"), ("hold", "special_n1_hold"), ("cancel", "special_n1_cancel"),
                ("fire", "special_n1_fire"), ("fire_max", "special_n1_fire_max"),
                ("air_start", "special_air_n1_start"), ("air_hold", "special_air_n1_hold"),
                ("air_cancel", "special_air_n1_cancel"), ("air_jump_cancel", "special_air_n1_jump_cancel"),
                ("air_fire", "special_air_n1_fire"), ("air_fire_max", "special_air_n1_fire_max"),
            ]),
            ("alt_2", "Neutral special option 2", [
                ("start", "special_n2_start"), ("loop", "special_n2_loop"), ("end", "special_n2_end"),
                ("air_start", "special_air_n2_start"), ("air_loop", "special_air_n2_loop"),
                ("air_end", "special_air_n2_end_by_clip"),
            ]),
            ("alt_3", "Neutral special option 3", [
                ("start", "special_n3_start"), ("end", "special_n3_end"),
                ("air_start", "special_air_n3_start"), ("air_end", "special_air_n3_end"),
            ]),
        ]),
        "special_side": ("Side special", "side", [
            ("alt_1", "Side special option 1", [
                ("move", "special_s1"), ("air_move", "special_air_s1")]),
            ("alt_2", "Side special option 2", [
                ("start", "special_s2_start"), ("loop", "special_s2_loop"), ("end", "special_s2_end"),
                ("air_start", "special_air_s2_start"), ("air_loop", "special_air_s2_loop"),
                ("air_end", "special_air_s2_end"),
            ]),
            ("alt_3", "Side special option 3", [
                ("step_1", "special_s3_1"), ("step_2", "special_s3_2"),
                ("air_step_1", "special_air_s3_1"), ("air_step_2", "special_air_s3_2"),
            ]),
        ]),
        "special_up": ("Up special", "up", [
            ("alt_1", "Up special option 1", [
                ("move", "special_hi1"), ("air_move", "special_air_hi1")]),
            ("alt_2", "Up special option 2", [
                ("move", "special_hi2"), ("squat", "special_hi2_squat"),
                ("air_squat", "special_air_hi2_squat"),
            ]),
            ("alt_3", "Up special option 3", [
                ("start", "special_hi3_start"), ("move", "special_hi3"),
                ("directional_forward", "special_hi3_f_by_clip"),
                ("directional_back", "special_hi3_b_by_clip"),
                ("air_start", "special_air_hi3_start_by_clip"), ("air_end", "special_air_hi3_end"),
            ]),
        ]),
        "special_down": ("Down special", "down", [
            ("alt_1", "Down special option 1", [
                ("start", "special_lw1_start"), ("loop", "special_lw1_loop"),
                ("hit", "special_lw1_hit"), ("end", "special_lw1_end"),
                ("left_start", "special_lw1_start_l"), ("left_loop", "special_lw1_loop_l"),
                ("left_hit", "special_lw1_hit_l"), ("left_end", "special_lw1_end_l"),
                ("air_start", "special_air_lw1_start"), ("air_loop", "special_air_lw1_loop"),
                ("air_hit", "special_air_lw1_hit"), ("air_end", "special_air_lw1_end"),
                ("air_left_start", "special_air_lw1_start_l"), ("air_left_loop", "special_air_lw1_loop_l"),
                ("air_left_hit", "special_air_lw1_hit_l"), ("air_left_end", "special_air_lw1_end_l"),
            ]),
            ("alt_2", "Down special option 2", [
                ("move", "special_lw2"), ("air_move", "special_air_lw2")]),
            ("alt_3", "Down special option 3", [
                ("start", "special_lw3_start"), ("hold", "special_lw3_hold"),
                ("hit", "special_lw3_hit"), ("end", "special_lw3_end"),
                ("air_start", "special_air_lw3_start"), ("air_hold", "special_air_lw3_hold"),
                ("air_hit", "special_air_lw3_hit"), ("air_end", "special_air_lw3_end"),
            ]),
        ]),
    }

    # Four motion kinds in this file have no name in the label table. They are
    # identified by their kind hash plus the animation the entry points at, and
    # are stored as explicit unknown-name records.
    UNNAMED_BY_CLIP = {
        "special_air_n2_end_by_clip": {
            "kind_hash": 0x12772B6B5F, "clip": "d00specialairn2end.nuanmb",
            "observed_as": "neutral special option 2 air end state, by index position and clip name",
        },
        "special_hi3_f_by_clip": {
            "kind_hash": 0x0D3AAF0366, "clip": "d02specialhi3f.nuanmb",
            "observed_as": "up special option 3 forward directional variant",
        },
        "special_hi3_b_by_clip": {
            "kind_hash": 0x0D3DC2C77F, "clip": "d02specialhi3b.nuanmb",
            "observed_as": "up special option 3 back directional variant",
        },
        "special_air_hi3_start_by_clip": {
            "kind_hash": 0x15EBA8646E, "clip": "d02specialairhi3start.nuanmb",
            "observed_as": "up special option 3 air start state",
        },
    }

    for slot_id, (label, direction, alts) in special_defs.items():
        choices = []
        for alt_id, alt_label, pairs in alts:
            resolved_pairs = []
            for role, key in pairs:
                if key in UNNAMED_BY_CLIP:
                    info = UNNAMED_BY_CLIP[key]
                    resolved_pairs.append((role, key, info["kind_hash"]))
                else:
                    resolved_pairs.append((role, key, None))
            states_out = []
            for role, key, forced_hash in resolved_pairs:
                if forced_hash is not None:
                    state = view.state(key, role, view_kind_hash=forced_hash)
                    state["identified_by"] = UNNAMED_BY_CLIP[key]["clip"]
                    state["observed_as"] = UNNAMED_BY_CLIP[key]["observed_as"]
                    states_out.append(state)
                else:
                    states_out.append(view.state(key, role))
            choices.append({
                "choice_id": "gunner_%s_%s" % (slot_id, alt_id),
                "display_label": {"text": alt_label, "label_origin": "author_display_label",
                                  "is_game_string": False},
                "available": True,
                "states": states_out,
                "dependency_note": (
                    "Motion states only. Which helper motion list, script or projectile this "
                    "alternative uses is NOT established from these inputs and is not asserted here."
                ),
            })
        slots.append(slot(
            slot_id, "special", label, "special button + %s direction" % direction,
            choices,
            notes=[
                "three alternatives already present in this fighter's motion list",
                "no helper dependency closure is claimed for any alternative",
            ],
        ))

    return slots


# --------------------------------------------------------------------------
# parameters
# --------------------------------------------------------------------------

# The twelve candidates named in P1-CATALOG section 7, with the type each one
# decodes to. Safe ranges and runtime override behaviour are deliberately left
# UNKNOWN: nothing measured them, so nothing is asserted.
STAT_SPECS = [
    ("weight", "float", "Body mass"),
    ("scale", "float", "Model scale"),
    ("walk_speed_max", "float", "Walk top speed"),
    ("run_speed_max", "float", "Run top speed"),
    ("dash_speed", "float", "Dash top speed"),
    ("air_speed_x_stable", "float", "Horizontal air speed cap"),
    ("air_speed_y_stable", "float", "Vertical air speed cap (terminal-style cap, not floatiness)"),
    ("air_accel_y", "float", "Vertical air acceleration"),
    ("air_accel_x_mul", "float", "Horizontal air acceleration multiplier"),
    ("jump_y", "float", "Jump height term"),
    ("jump_speed_x", "float", "Horizontal jump speed"),
    ("jump_count_max", "i32", "Jump count"),
]

# Related keys that live in the same row and were measured, but are not part of
# the twelve. Recorded so the editor knows they exist without claiming a range.
RELATED_KEYS = [
    "jump_initial_y", "jump_squat_frame", "ground_brake", "run_accel_mul", "walk_accel_mul",
    "air_brake_x", "air_brake_y", "air_accel_x_add", "shield_radius",
]


def build_stats(prc_path):
    tree = prc.read(prc_path)
    root_dict = prc.as_dict(tree)
    list_key = hash40(PARAM_ROOT_LIST)
    if list_key not in root_dict or root_dict[list_key][0] != "list":
        raise SystemExit("%s: no %s list" % (prc_path, PARAM_ROOT_LIST))
    rows = root_dict[list_key][1]

    # The row's key is `fighter_kind`; its value is the fighter-kind hash.
    kind_key = hash40("fighter_kind")
    kind_hash = hash40(FIGHTER_KIND_NAME)
    matches = [i for i, row in enumerate(rows)
               if prc.as_dict(row).get(kind_key, (None, None))[1] == kind_hash]
    if len(matches) != 1:
        raise SystemExit("expected exactly one %s row, found %r" % (FIGHTER_KIND_NAME, matches))
    row_index = matches[0]
    row = prc.as_dict(rows[row_index])

    stats = []
    for name, expected_type, description in STAT_SPECS:
        key = hash40(name)
        node = row.get(key)
        if node is None:
            stats.append({
                "stat_id": "stat_" + name,
                "parameter_name": name,
                "hash": hexh(key),
                "status": "KEY_NOT_FOUND_IN_ROW",
                "description": description,
            })
            continue
        tag, value = node
        record = {
            "stat_id": "stat_" + name,
            "parameter_name": name,
            "hash": hexh(key),
            "hash_verified": key == hash40(name),
            "decoded_type": tag,
            "expected_type": expected_type,
            "type_matches": tag == expected_type,
            "default_value": value,
            "description": description,
            "description_origin": "author_display_label",
            "safe_range": {
                "status": "UNKNOWN",
                "min": None,
                "max": None,
                "note": "No safe range was measured. No range is inferred here.",
            },
            "runtime_override": {
                "schema_supported": True,
                "declared_candidate": True,
                "observed": False,
                "mechanism": "UNKNOWN",
                "per_instance_scope": "UNKNOWN",
                "note": (
                    "The catalogue carries an override field so a runtime override can be "
                    "recorded later. Nothing here shows the engine reads this row unchanged "
                    "or that one saved Mii can be scoped to one battle object."
                ),
            },
            "cross_stat_relationships": {
                "status": "UNKNOWN",
                "independent_of_other_stats": None,
                "note": (
                    "No cross-stat independence is claimed. Where a row holds more than one "
                    "related key (for example jump_y and jump_initial_y) the relationship was "
                    "not measured and must not be assumed."
                ),
            },
            "provenance": {
                "table": PARAM_ROOT_LIST,
                "row_index": row_index,
                "row_identity": "fighter_kind == %s (%s)" % (FIGHTER_KIND_NAME, hexh(kind_hash)),
                "row_key": "fighter_kind (%s)" % hexh(kind_key),
                "arc_path": FIGHTER_PARAM_ARC_PATH,
            },
        }
        if tag == "float":
            record["value_f32_bits"] = f32_bits(value)
        stats.append(record)

    related = []
    for name in RELATED_KEYS:
        node = row.get(hash40(name))
        if node is None:
            related.append({"parameter_name": name, "status": "KEY_NOT_FOUND_IN_ROW"})
            continue
        related.append({
            "parameter_name": name,
            "hash": hexh(hash40(name)),
            "decoded_type": node[0],
            "value": node[1],
            "in_candidate_set": False,
            "note": "measured neighbour in the same row; not proposed as an editor stat here",
        })

    identity = {
        "fighter_kind_name": FIGHTER_KIND_NAME,
        "fighter_kind_hash": hexh(kind_hash),
        "table": PARAM_ROOT_LIST,
        "row_index": row_index,
        "row_key_count": len(row),
        "row_count": len(rows),
        "identity_method": "row key fighter_kind (%s) value matched against hash40(%s)"
                           % (hexh(kind_key), FIGHTER_KIND_NAME),
        "identity_unique": len(matches) == 1,
        "arc_path": FIGHTER_PARAM_ARC_PATH,
        "arc_directory": "miigunner",
    }
    return stats, related, identity


# --------------------------------------------------------------------------
# helpers, gaps, provenance
# --------------------------------------------------------------------------

def build_helpers(helper_root: Path):
    """Helper / weapon motion lists, listed as UNLINKED dependency candidates.

    The body motion list never names these. Which helper belongs to which
    special alternative lives in script or article code that is not in the
    local inputs, so nothing here is attached to a slot.
    """
    if not helper_root.is_dir():
        return [], "helper root not present: %s" % helper_root.relative_to(ROOT).as_posix()
    out = []
    for path in sorted(helper_root.glob("*/c00/motion_list.bin")):
        name = path.parent.parent.name
        if name == "body":
            continue  # the body list is a primary input, not a helper
        out.append({
            "helper_id": "helper_" + name,
            "name_from_path": name,
            "arc_path": "fighter/miigunner/motion/%s/c00/motion_list.bin" % name,
            "sha256": sha256_of(path),
            "bytes": path.stat().st_size,
            "role": "dependency_candidate",
            "link_status": "UNLINKED",
            "linked_slots": [],
            "note": "present in this fighter's data; no measured link to any slot or special alternative",
        })
    return out, None


def build_gaps(view, helpers, referenced_kind_hashes):
    gaps = []

    # Only the unnamed kinds the catalogue actually references get their own
    # record; the rest of the file's unnamed kinds are counted, not dropped.
    for index, entry in enumerate(view.ml["entries"]):
        if view.name_of(entry["kind"]) is not None:
            continue
        if entry["kind"] not in referenced_kind_hashes:
            continue
        anims = [a["basename"] for a in view.animations(entry) if a["basename"]]
        gaps.append({
            "gap_id": "gap_unnamed_kind_" + hexh(entry["kind"]),
            "type": "UNRESOLVED_NAME",
            "kind_hash": hexh(entry["kind"]),
            "entry_index": index,
            "clips": anims,
            "referenced_by": sorted(referenced_kind_hashes[entry["kind"]]),
            "detail": ("motion kind has no name in the label table; recorded by hash and clip, "
                       "never guessed into a label"),
        })

    unnamed_total = sum(1 for e in view.ml["entries"] if not view.name_of(e["kind"]))
    gaps.append({
        "gap_id": "gap_unnamed_kinds_file_wide",
        "type": "COVERAGE",
        "unnamed_entry_count": unnamed_total,
        "entry_count": len(view.ml["entries"]),
        "detail": ("Entries in this motion list whose kind hash has no name in the label table. "
                   "Most are item, ledge, step or state entries outside editor scope. Those "
                   "referenced by a catalogued slot or choice are listed individually above."),
    })

    gaps.append({
        "gap_id": "gap_special_helper_links",
        "type": "UNLINKED_DEPENDENCY",
        "detail": ("No helper motion list is linked to any special alternative. Script bodies are "
                   "absent from this workspace, so the link was not measured."),
        "helper_ids": [h["helper_id"] for h in helpers],
    })
    gaps.append({
        "gap_id": "gap_final_smash",
        "type": "PENDING_SCOPE",
        "detail": "Final Smash kinds exist (final_start/final/final_end/final_air_*/final_u/final_d/"
                  "final_air_u/final_air_d) but editor scope is a coordinator decision. Note that "
                  "motion/fullthrottle/c00 owns clips with the same d04final* names; reading a clip "
                  "name alone would invert the dependency.",
        "offers_slots": False,
    })
    gaps.append({
        "gap_id": "gap_get_up",
        "type": "PENDING_SCOPE",
        "detail": ("Get-up attacks are present and named but scope is undecided. Recovery and "
                   "movement states (down_stand, down_bounce, walk, fall, jump) are NOT enumerated "
                   "as get-up attacks here."),
        "offers_slots": False,
    })
    gaps.append({
        "gap_id": "gap_ledge",
        "type": "PENDING_SCOPE",
        "detail": "Ledge/cliff motions present (cliff_catch, cliff_wait, cliff_attack_quick, "
                  "slip_attack, slip_escape_f/b) with four unnamed kinds; scope undecided.",
        "offers_slots": False,
    })
    gaps.append({
        "gap_id": "gap_taunts",
        "type": "PENDING_SCOPE",
        "detail": "Taunt/appeal kinds present (six appeal_* kinds) plus win_*, lose, menu_pose*, "
                  "entry_* and share_*; scope undecided.",
        "offers_slots": False,
    })
    gaps.append({
        "gap_id": "gap_script_bodies",
        "type": "MISSING_INPUT",
        "detail": "ACMD / game script bodies are absent from this workspace. Script bodies were not "
                  "read, so no behaviour, hit box, damage or input routing claim is made.",
    })
    gaps.append({
        "gap_id": "gap_stat_ranges",
        "type": "UNKNOWN_SEMANTICS",
        "detail": "No safe range, runtime override mechanism or per-instance scope was measured for "
                  "any of the twelve stat candidates.",
    })
    gaps.append({
        "gap_id": "gap_other_costumes",
        "type": "COVERAGE",
        "detail": "Only body/c00 was read. c06 and c07 motion lists exist and were not decoded, so "
                  "one script per slot per costume set is not established.",
    })
    gaps.append({
        "gap_id": "gap_move_data",
        "type": "COVERAGE",
        "detail": "fighter/miigunner/param/vl.prc per-move hit_data and map_collision values were "
                  "not mined into this catalogue.",
    })
    gaps.append({
        "gap_id": "gap_no_runtime_evidence",
        "type": "EVIDENCE_TIER",
        "detail": "No console, no emulator, no build. Every value here is file-level (tier B) or a "
                  "hypothesis (tier D). Nothing here is runtime behaviour.",
    })
    gaps.append({
        "gap_id": "gap_back_tilt_routing",
        "type": "UNKNOWN_SEMANTICS",
        "detail": "Whether the engine routes back tilt to attack_s3_s, or drives it from a kind with "
                  "no separate clip, is not settled by a motion list.",
    })
    gaps.append({
        "gap_id": "gap_no_stop_intp_runtime",
        "type": "UNKNOWN_SEMANTICS",
        "detail": "no_stop_intp is identified by correlation with a decoded boolean label; what it "
                  "does to interpolation at runtime is not established.",
    })
    gaps.append({
        "gap_id": "gap_identity_and_persistence",
        "type": "OUT_OF_SCOPE",
        "detail": "Saved-Mii identity, save format, loadout persistence and native UI binding are "
                  "owned by other tasks and are untouched here.",
    })
    return gaps


def build(ml_path: Path, prc_path: Path, labels_path: Path, arc_index: Path, helper_root: Path):
    ml = mlist.parse(ml_path)
    round_trip_equal = mlist.encode(ml) == ml["data"]
    labels = load_labels(labels_path)
    anim_index = load_animation_index(arc_index)
    view = MotionView(ml, labels, anim_index)

    stats, related, identity = build_stats(prc_path)
    helpers, helper_note = build_helpers(helper_root)
    slots = build_slots(view)

    # kind hash -> the slot/choice/role references that need it, so the
    # coverage gaps can point at the exact consumer of an unresolved name.
    referenced = {}
    for s in slots:
        for choice in s["choices"]:
            for st in choice["states"]:
                if st.get("kind_hash"):
                    referenced.setdefault(int(st["kind_hash"], 16), set()).add(
                        "%s/%s/%s" % (s["slot_id"], choice["choice_id"], st["role"]))

    catalog = {
        "format_version": "1.0.0",
        "catalogue_id": "mii_customizer.gunner.editor_catalogue",
        "task": "P1-DATASET",
        "purpose": "EDITOR_INPUT_DATA",
        "generator": {
            "tool": "tools/gunner-catalog/build_catalog.py",
            "stdlib_only": True,
            "shared_readers_imported_read_only": [
                "mods/ssbu_mod_new/src/pgwr/tools/mlist.py",
                "mods/ssbu_mod_new/src/pgwr/tools/prc.py",
            ],
            "determinism": "no timestamps, no absolute paths and no hash-order output; identical "
                           "inputs must produce identical bytes",
        },
        "disclaimer": [
            "This is provisional editor INPUT DATA, not a final loadout or save schema.",
            "It is not a runtime implementation and not a move port. No move is shown to work.",
            "Slot grouping is an editor proposal. Native input routing is not established.",
            "Timing bytes are authored data copied from a file, not measured frame data.",
            "Nothing here touches saved-Mii identity, persistence or the native editor.",
        ],
        "evidence_tier": "B (measured offline from pinned local binaries); no tier A exists",
        "inputs": {
            "primary_binaries": [
                {
                    "role": "gunner_body_c00_motion_list",
                    "relative_path": ml_path.relative_to(ROOT).as_posix(),
                    "arc_path": MOTION_ARC_PATH,
                    "sha256": sha256_of(ml_path),
                    "bytes": ml_path.stat().st_size,
                    "entry_count": len(ml["entries"]),
                    "round_trip_encode_equal": round_trip_equal,
                    "source": "gamedata/ssbu-13.0.4/data.arc via tools/arc-extract (see "
                              "evidence/P1-CATALOG/EXTRACTION.md)",
                },
                {
                    "role": "common_fighter_param",
                    "relative_path": prc_path.relative_to(ROOT).as_posix(),
                    "arc_path": FIGHTER_PARAM_ARC_PATH,
                    "sha256": sha256_of(prc_path),
                    "bytes": prc_path.stat().st_size,
                    "source": "gamedata/ssbu-13.0.4/data.arc via tools/arc-extract (see "
                              "evidence/P1-CATALOG/EXTRACTION.md)",
                },
            ],
            "name_dictionaries": [
                {
                    "role": "motion_kind_labels",
                    "relative_path": labels_path.relative_to(ROOT).as_posix(),
                    "sha256": sha256_of(labels_path),
                    "use": "hash -> name dictionary only; it is not an input for any measured value",
                },
                {
                    "role": "archive_path_index",
                    "relative_path": arc_index.relative_to(ROOT).as_posix(),
                    "sha256": sha256_of(arc_index),
                    "use": "animation hash (hash40 of the file basename) -> ARC path join",
                },
            ],
            "auxiliary_read_only": [
                {
                    "role": "helper_motion_lists",
                    "relative_path": helper_root.relative_to(ROOT).as_posix(),
                    "count": len(helpers),
                    "note": helper_note or "listed as unlinked dependency candidates only",
                }
            ],
            "extraction_performed_by_this_task": False,
        },
        "fighter_identity": identity,
        "motion_source": {
            "entry_count": len(ml["entries"]),
            "motion_path_field_hash": hexh(ml["motion_path"]),
            "named_entry_count": sum(1 for e in ml["entries"] if view.name_of(e["kind"])),
            "unnamed_entry_count": sum(1 for e in ml["entries"] if not view.name_of(e["kind"])),
        },
        "editor_slots": slots,
        "stat_candidates": stats,
        "stat_row_neighbours": related,
        "dependency_candidates": helpers,
        "coverage_gaps": build_gaps(view, helpers, referenced),
        "explicit_unknowns": [
            "Native input routing for every slot.",
            "Which helper, script or projectile each special alternative uses.",
            "Whether the engine reads fighter_param row 82 unchanged at runtime.",
            "Any safe range, override mechanism or per-instance scope for the stat candidates.",
            "Meaning of no_stop_intp at runtime.",
            "Names of the unnamed motion kinds listed in coverage_gaps.",
            "Final Smash, get-up, ledge and taunt scope.",
        ],
    }
    return catalog


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--motion-list", default=DEFAULT_MOTION_LIST)
    parser.add_argument("--fighter-param", default=DEFAULT_FIGHTER_PARAM)
    parser.add_argument("--labels", default=DEFAULT_LABELS)
    parser.add_argument("--arc-index", default=DEFAULT_ARC_INDEX)
    parser.add_argument("--helper-root", default=DEFAULT_HELPER_ROOT)
    parser.add_argument("--out", default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    # Relative arguments are resolved against the workspace root, so the tool
    # writes no absolute machine path into the catalogue.
    def resolve(value):
        path = Path(value)
        return path if path.is_absolute() else ROOT / path

    ml_path = resolve(args.motion_list)
    prc_path = resolve(args.fighter_param)
    args.labels = str(resolve(args.labels))
    args.arc_index = str(resolve(args.arc_index))
    args.helper_root = str(resolve(args.helper_root))
    for path in (ml_path, prc_path, Path(args.labels), Path(args.arc_index)):
        if not path.is_file():
            raise SystemExit("missing input: %s" % path)

    catalog = build(ml_path, prc_path, Path(args.labels), Path(args.arc_index), Path(args.helper_root))
    out = resolve(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(catalog, indent=2, ensure_ascii=True, sort_keys=False) + "\n",
                   encoding="utf-8", newline="\n")

    slots = catalog["editor_slots"]
    aerials = [s for s in slots if s["group"] == "aerial"]
    states_n = sum(len(c["states"]) for s in slots for c in s["choices"])
    print("wrote %s" % out.as_posix())
    print("  slots %d (aerials %d)  choices %d  motion states %d"
          % (len(slots), len(aerials), sum(len(s["choices"]) for s in slots), states_n))
    print("  stat candidates %d  gaps %d"
          % (len(catalog["stat_candidates"]), len(catalog["coverage_gaps"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
