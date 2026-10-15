#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate Mii Customizer character stat presets from the user's own game file.

Task P6-PRESET-DATA. Evidence tier **B**: everything below is measured offline
from the user's own extracted files. Nothing here shows a preset working in
game, and applying a preset only copies the listed numbers.

Outputs (all workspace-relative, nothing game-derived lands in the mod tree):

    gamedata/mii_customizer/P6-PRESET-DATA/fighter_param_full.json
    gamedata/mii_customizer/P6-PRESET-DATA/presets.txt
    gamedata/mii_customizer/P6-PRESET-DATA/fighters.json

With --write-list (and only then) it also writes, into the same output folder:

    list.txt          format `mc_list 1` (contract F of prompts/P10-UI-SLICE.md)
    fields_wide.json  the Part 1 field table plus the decision per field,
                      from --field-table and --decisions

Defaults are unchanged: without --write-list the three files above are
byte-identical to what P6-PRESET-DATA produced.

Inputs (read-only):

    gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc
    mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv          (name dictionary only)
    gamedata/mii_customizer/P6-PRESET-DATA/files/ui/message/msg_name.msbt

Reads `mods/ssbu_mod_new/src/pgwr/tools/prc.py` by path, read-only, and never
modifies it. `stat_fields.txt` (same directory as this script) is the
coordinator-owned list of preset fields.

Usage, from the workspace root:

    python -B mods/mii_customizer/tools/stat-presets/build_presets.py

Optional arguments (defaults are the workspace layout, relative paths only):

    --fighter-param   path to fighter_param.prc
    --labels          path to ParamLabels.csv
    --msg-name        path to msg_name.msbt
    --fields          path to stat_fields.txt
    --out-dir         output folder
    --expect-hash     sha256 the fighter_param.prc must have (repeatable)

Task P10-PRESET-WIDE added, all with defaults that leave the P6 run unchanged:

    --write-list          also write list.txt and fields_wide.json
    --decisions           path to stat_fields_wide_decisions.json
    --field-table         path to the P10-PRESET-WIDE Part 1 field_table.json
    --label-prefix        message label family for list.txt (nam_chr1_00_)
    --list-name           list file name (list.txt)
    --fields-json-name    fields_wide.json file name (fields_wide.json)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))

DEFAULT_PRC = "gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc"
DEFAULT_LABELS = "mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv"
DEFAULT_MSG_NAME = "gamedata/mii_customizer/P6-PRESET-DATA/files/ui/message/msg_name.msbt"
DEFAULT_FIELDS = "mods/mii_customizer/tools/stat-presets/stat_fields.txt"
DEFAULT_OUT = "gamedata/mii_customizer/P6-PRESET-DATA"
DEFAULT_DECISIONS = "mods/mii_customizer/tools/stat-presets/stat_fields_wide_decisions.json"
DEFAULT_FIELD_TABLE = "gamedata/mii_customizer/P10-PRESET-WIDE/field_table.json"

# Output file names. Defaults reproduce the P6 outputs byte for byte; the wide
# run overrides the first three and turns the optional files on.
PRESETS_NAME = "presets.txt"
FIGHTERS_NAME = "fighters.json"
FULL_NAME = "fighter_param_full.json"
LIST_NAME = "list.txt"
FIELDS_WIDE_NAME = "fields_wide.json"

# Contract F of prompts/P10-UI-SLICE.md.
LIST_FORMAT = "mc_list 1"
LIST_LABEL_PREFIX = "nam_chr1_00_"
LIST_MAX_LINES = 128
LIST_MAX_BYTES = 16 * 1024
LIST_MAX_LABEL = 63
LIST_NAME_SKIP_PREFIXES = ("miienemy",)
DEFAULT_LIST_EXCLUDE = os.path.join(HERE, "list_exclude.txt")

# Contract A of prompts/P7-PRESET-ENGINE.md.
PRESET_MAX_BYTES = 512 * 1024
PRESET_MAX_PRESETS = 128
PRESET_MAX_FIELDS = 48
PRESET_MAX_DISTINCT_HASHES = 48
PRESET_MAX_NAME = 31

# The one fighter_param.prc this tool was built against. The check script
# re-asserts it; the generator only warns so it can run on another game build.
PINNED_PRC_SHA256 = "87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2"

PRESET_FORMAT = "mc_presets 1"
FLOAT_REPR_DIGITS = 9  # enough to round-trip IEEE-754 binary32

sys.path.insert(0, os.path.join(ROOT, "mods", "ssbu_mod_new", "src", "pgwr", "tools"))


def import_prc():
    try:
        import prc
    except ImportError as exc:  # pragma: no cover - environment problem
        raise SystemExit("cannot import the shared .prc reader: %s" % exc)
    return prc


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def hexh(value):
    return "0x%010x" % value


def load_labels(path):
    """hash -> name, from the reference label table. A name dictionary only.

    Rows whose second column is empty, `-1` or `-2` carry no name and are
    skipped. The first name wins for a repeated hash, so a later duplicate
    cannot silently rewrite an earlier row.
    """
    labels = {}
    skipped = 0
    duplicates = 0
    with open(path, newline="", encoding="utf-8", errors="replace") as handle:
        for row in csv.reader(handle):
            if len(row) < 2 or row[1] in ("", "-1", "-2"):
                skipped += 1
                continue
            value = int(row[0], 16)
            if value in labels:
                duplicates += 1
                continue
            labels[value] = row[1]
    return labels, {"rows_without_a_name": skipped, "duplicate_hashes_skipped": duplicates}


def load_field_list(path):
    """Read stat_fields.txt: one field name per line, '#' comments allowed."""
    fields = []
    with open(path, encoding="utf-8") as handle:
        for lineno, raw in enumerate(handle, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            if not re.fullmatch(r"[a-z0-9_]+", line):
                raise SystemExit("%s:%d: field name %r must match [a-z0-9_]+"
                                 % (path, lineno, line))
            if line in fields:
                raise SystemExit("%s:%d: field %r listed twice" % (path, lineno, line))
            fields.append(line)
    if not fields:
        raise SystemExit("%s: no fields listed" % path)
    return fields


def verified_label(labels, value, prc):
    """The label for `value` only if hashing it again reproduces `value`.

    A label is never trusted on the strength of appearing in the CSV: the name
    must hash back to the hash it is filed under. Returns (name, ok).
    """
    name = labels.get(value)
    if name is None:
        return None, False
    return name, prc.hash40(name) == value


def float_text(value):
    """Shortest decimal that round-trips the f32 exactly.

    `%.9g` is more digits than binary32 needs (9 significant decimal digits
    always round-trip a 24-bit significand), so the printed text re-parses to
    the same f32. The generator re-parses every value it writes and fails if
    the bit pattern differs, so this is verified, not assumed.
    """
    return "%.*g" % (FLOAT_REPR_DIGITS, value)


def read_table(prc, prc_path):
    """Return (rows_as_dicts, kind_key, field_count_set)."""
    tree = prc.read(prc_path)
    root = prc.as_dict(tree)
    list_key = prc.hash40("fighter_param_table")
    node = root.get(list_key)
    if node is None or node[0] != "list":
        raise SystemExit("%s: no fighter_param_table list" % prc_path)
    raw_rows = node[1]

    kind_key = prc.hash40("fighter_kind")
    rows = []
    counts = set()
    for index, row in enumerate(raw_rows):
        as_dict = prc.as_dict(row)
        if kind_key not in as_dict:
            raise SystemExit("row %d has no fighter_kind key" % index)
        counts.add(len(as_dict))
        rows.append(as_dict)
    return rows, kind_key, counts


def build_full_json(rows, kind_key, labels, prc, inputs, out_path, field_counts):
    """The whole table: kind hash, label if verified, and every field."""
    type_counts = {}
    field_names_seen = set()
    unlabelled = set()
    per_row = []

    for index, row in enumerate(rows):
        kind_hash = row[kind_key][1]
        kind_label, kind_ok = verified_label(labels, kind_hash, prc)
        fields = []
        for key, (tag, value) in row.items():
            name, name_ok = verified_label(labels, key, prc)
            field_names_seen.add(key)
            if name is None or not name_ok:
                unlabelled.add(key)
                name = None
            entry = {
                "hash": hexh(key),
                "name": name,
                "name_hash_verified": bool(name_ok) and name is not None,
                "type": tag,
            }
            if tag == "float":
                bits = struct.unpack("<I", struct.pack("<f", value))[0]
                entry["value"] = value
                entry["value_f32_bits"] = "0x%08x" % bits
                entry["value_text"] = float_text(value)
            elif tag == "hash":
                value_label, value_ok = verified_label(labels, value, prc)
                entry["value"] = value
                entry["value_text"] = hexh(value)
                entry["value_name"] = value_label
                entry["value_name_hash_verified"] = bool(value_ok) and value_label is not None
            else:
                entry["value"] = value
                entry["value_text"] = str(value)
            fields.append(entry)
            type_counts[tag] = type_counts.get(tag, 0) + 1
        fields.sort(key=lambda f: f["hash"])
        per_row.append({
            "row_index": index,
            "fighter_kind_hash": hexh(kind_hash),
            "fighter_kind_name": kind_label,
            "fighter_kind_name_hash_verified": bool(kind_ok),
            "field_count": len(row),
            "fields": fields,
        })

    doc = {
        "format_version": "1.0.0",
        "task": "P6-PRESET-DATA",
        "purpose": "OFFLINE_VIEW_OF_THE_USERS_OWN_TABLE",
        "source_table": "fighter/common/param/fighter_param.prc -> fighter_param_table",
        "evidence_tier": "B (measured offline from the user's own extracted files)",
        "disclaimer": [
            "This is a decode of a file, not a statement about game behaviour.",
            "Reading a row does not show the engine reads it unchanged.",
            "No preset here is shown to make a Mii behave like any character.",
        ],
        "generator": {
            "tool": "mods/mii_customizer/tools/stat-presets/build_presets.py",
            "shared_reader_imported_read_only": "mods/ssbu_mod_new/src/pgwr/tools/prc.py",
            "float_text_digits": FLOAT_REPR_DIGITS,
        },
        "inputs": inputs,
        "row_count": len(rows),
        "field_count_per_row": sorted(field_counts),
        "field_count_equal_for_all_rows": len(field_counts) == 1,
        "distinct_field_names": len(field_names_seen),
        "field_type_counts": {k: type_counts[k] for k in sorted(type_counts)},
        "field_types_other_than_float_int_bool_hash": sorted(
            t for t in type_counts if t not in ("float", "int", "i32", "u32", "bool", "hash")
        ),
        "unlabelled_field_hashes": sorted(hexh(k) for k in unlabelled),
        "unlabelled_field_count": len(unlabelled),
        "rows": per_row,
    }
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(doc, handle, indent=1, ensure_ascii=True, sort_keys=False)
        handle.write("\n")
    return doc


def build_presets(rows, kind_key, labels, prc, field_names, inputs, out_path,
                  out_name=PRESETS_NAME, log=print):
    """Write the preset file in the `mc_presets 1` contract format.

    Every limit of contract A is checked here, before the file is written, so a
    field list that would overflow the plugin's static storage fails loudly here
    instead of being refused on the console.
    """
    # Resolve and type-check the field list against the table BEFORE writing
    # anything, so a bad list can never leave a half-written preset file.
    resolved = []
    for name in field_names:
        key = prc.hash40(name)
        types = set(row[key][0] for row in rows if key in row)
        if not types:
            raise SystemExit("stat_fields.txt lists %r but the table has no such field" % name)
        if types != {"float"}:
            raise SystemExit("stat_fields.txt lists %r but its type is %s, expected float"
                             % (name, "/".join(sorted(types))))
        resolved.append((name, key))
    if len(resolved) != len(set(key for _n, key in resolved)):
        raise SystemExit("%s lists the same field twice" % out_name)
    if len(resolved) > PRESET_MAX_FIELDS:
        raise SystemExit("%s lists %d fields; contract A allows at most %d per preset"
                         % (out_name, len(resolved), PRESET_MAX_FIELDS))
    if len(set(key for _n, key in resolved)) > PRESET_MAX_DISTINCT_HASHES:
        raise SystemExit("%s has %d distinct field hashes; contract A allows at most %d"
                         % (out_name, len(set(k for _n, k in resolved)),
                            PRESET_MAX_DISTINCT_HASHES))
    if len(rows) > PRESET_MAX_PRESETS:
        raise SystemExit("the table has %d rows; contract A allows at most %d presets"
                         % (len(rows), PRESET_MAX_PRESETS))
    # Contract A's 31-character limit is on the PRESET name, not on a field
    # name: the generator already checks the preset name when it derives one
    # from a kind label. A field name only has to resolve to a table key.

    # The contract puts the version line FIRST. The loadout-file parser the
    # plugin already ships refuses a file whose first line is not exactly the
    # version line (`bad_version_line_bom`, research/P4-OVERRIDE-SLICE.md 2.1),
    # so comments must come after it, never before.
    out = []
    out.append("%s" % PRESET_FORMAT)
    out.append("# Mii Customizer stat presets, format %s" % PRESET_FORMAT)
    out.append("# Generated from the user's own fighter/common/param/fighter_param.prc")
    out.append("# sha256 %s" % inputs["fighter_param"]["sha256"])
    out.append("# One preset per fighter kind. Values are copied numbers from that")
    out.append("# table; nothing here states that using one changes how a Mii plays.")
    # No line naming the field list here: the default run must stay byte-identical
    # to the P6 output, and the field list is already recorded in
    # fighters.json's inputs and in the report.

    written = []
    skipped = []
    seen_names = set()
    for index, row in enumerate(rows):
        kind_hash = row[kind_key][1]
        label, ok = verified_label(labels, kind_hash, prc)
        if not ok:
            skipped.append({"row_index": index, "kind_hash": hexh(kind_hash),
                            "reason": "no hash-verified ParamLabels entry"})
            continue
        if not label.startswith("fighter_kind_"):
            skipped.append({"row_index": index, "kind_hash": hexh(kind_hash),
                            "reason": "label %r has no fighter_kind_ prefix" % label})
            continue
        name = label[len("fighter_kind_"):]
        if not re.fullmatch(r"[a-z0-9_]{1,%d}" % PRESET_MAX_NAME, name):
            skipped.append({"row_index": index, "kind_hash": hexh(kind_hash),
                            "reason": "derived name %r is not [a-z0-9_]{1,%d}"
                                      % (name, PRESET_MAX_NAME)})
            continue
        if name in seen_names:
            # Contract A rejects a duplicate preset name. The generator refuses
            # to emit one at all: it cannot be fixed per-line by a reader
            # without dropping a whole preset's fields.
            skipped.append({"row_index": index, "kind_hash": hexh(kind_hash),
                            "reason": "duplicate preset name %r" % name})
            continue
        seen_names.add(name)
        out.append("")
        out.append("# row %d" % index)
        out.append("fighter %s %s" % (name, hexh(kind_hash)))
        values = []
        for field, key in resolved:
            value = row[key][1]
            values.append((field, key, value, float_text(value)))
            out.append("%s %s" % (hexh(key), float_text(value)))
        written.append({
            "name": name,
            "kind_hash": hexh(kind_hash),
            "row_index": index,
            "values": values,
        })

    text = "\n".join(out) + "\n"
    size = len(text.encode("ascii"))
    if size > PRESET_MAX_BYTES:
        raise SystemExit("%s would be %d bytes; contract A allows at most %d"
                         % (out_name, size, PRESET_MAX_BYTES))
    # Fail loudly rather than ship a file a version-checking parser rejects.
    if text.split("\n", 1)[0] != PRESET_FORMAT:
        raise SystemExit("%s: first line is %r, expected %r"
                         % (out_path, text.split("\n", 1)[0], PRESET_FORMAT))
    if text.startswith("#") or "\r" in text or b"\x00" in text.encode("ascii"):
        raise SystemExit("%s: not plain ASCII with \\n endings" % out_path)
    with open(out_path, "w", encoding="ascii", newline="\n") as handle:
        handle.write(text)

    # Verified, not assumed: every written value must re-parse to the same f32.
    for preset in written:
        for field, _key, value, printed in preset["values"]:
            again = struct.unpack("<I", struct.pack("<f", float(printed)))[0]
            want = struct.unpack("<I", struct.pack("<f", value))[0]
            if again != want:
                raise SystemExit("%s: %s did not round-trip (printed %r)"
                                 % (out_path, field, printed))

    return written, skipped, resolved


def message_text_ok(text):
    """True when a message label carries usable single-line text.

    The raw string keeps its trailing NUL and any control code. A label is only
    usable in a one-line list entry when stripping NUL, CR, LF and spaces leaves
    something, and no line break survives.
    """
    if text is None:
        return False
    if "\n" in text or "\r" in text:
        return False
    return text.replace("\x00", "").strip() != ""


def load_list_exclusions(path):
    """Read explicit preset-name exclusions; comments and blank lines are ignored."""
    names = set()
    with open(path, encoding="ascii") as handle:
        for lineno, raw in enumerate(handle, 1):
            name = raw.split("#", 1)[0].strip()
            if not name:
                continue
            if not re.fullmatch(r"[a-z0-9_]{1,31}", name):
                raise SystemExit("%s:%d: invalid preset name %r" % (path, lineno, name))
            if name in names:
                raise SystemExit("%s:%d: duplicate preset name %r" % (path, lineno, name))
            names.add(name)
    return names


def build_list(written, msg_labels, inputs, out_path, out_name=LIST_NAME,
               prefix=LIST_LABEL_PREFIX, excluded_names=None):
    """Write list.txt, format `mc_list 1` (contract F).

    One line per preset in fighter_param table order: `<preset_name>
    <message_label>`. A fighter is left out, with a reason, when

      * its preset name starts with `miienemy` (always left out),
      * its preset name is in the explicit exclusion file,
      * `<prefix><name>` is not a label in msg_name.msbt, or its text is empty
        or more than one line, or
      * the label does not match [a-z0-9_]{1,63}.

    Only the label goes into the file. The English text stays in the game file;
    five resolved examples are printed so a reader can see the label family is
    the right one, but the text is not written into any file under mods/.
    """
    entries = []
    left_out = []
    excluded_names = set(excluded_names or ())
    for preset in written:
        name = preset["name"]
        if name.startswith(LIST_NAME_SKIP_PREFIXES):
            left_out.append({"name": name, "row_index": preset["row_index"],
                             "reason": "preset name starts with %s"
                                       % "/".join(LIST_NAME_SKIP_PREFIXES)})
            continue
        if name in excluded_names:
            left_out.append({"name": name, "row_index": preset["row_index"],
                             "reason": "preset name is in the explicit list exclusion file"})
            continue
        label = prefix + name
        if label not in msg_labels:
            left_out.append({"name": name, "row_index": preset["row_index"],
                             "reason": "no label %s in msg_name.msbt" % label})
            continue
        if not re.fullmatch(r"[a-z0-9_]{1,%d}" % LIST_MAX_LABEL, label):
            left_out.append({"name": name, "row_index": preset["row_index"],
                             "reason": "label %r does not match [a-z0-9_]{1,%d}"
                                       % (label, LIST_MAX_LABEL)})
            continue
        if not message_text_ok(msg_labels[label]):
            left_out.append({"name": name, "row_index": preset["row_index"],
                             "reason": "label %s has empty or multi-line text" % label})
            continue
        entries.append({"name": name, "label": label, "row_index": preset["row_index"]})

    if len(entries) > LIST_MAX_LINES:
        raise SystemExit("%s would hold %d entries; contract F allows at most %d"
                         % (out_name, len(entries), LIST_MAX_LINES))

    out = [LIST_FORMAT,
           "# Mii Customizer character list, format %s" % LIST_FORMAT,
           "# One line per preset: <preset_name> <message_label>, in the order of",
           "# fighter_param_table. The label is resolved in ui/message/msg_name.msbt;",
           "# the text stays in that game file and is not copied here.",
           "# sha256 %s" % inputs["msg_name"]["sha256"],
           ""]
    for entry in entries:
        out.append("%s %s" % (entry["name"], entry["label"]))
    text = "\n".join(out) + "\n"

    size = len(text.encode("ascii"))
    if size > LIST_MAX_BYTES:
        raise SystemExit("%s would be %d bytes; contract F allows at most %d"
                         % (out_name, size, LIST_MAX_BYTES))
    if text.split("\n", 1)[0] != LIST_FORMAT:
        raise SystemExit("%s: first line is %r, expected %r"
                         % (out_name, text.split("\n", 1)[0], LIST_FORMAT))
    if "\r" in text or b"\x00" in text.encode("ascii"):
        raise SystemExit("%s: not plain ASCII with \\n endings" % out_name)
    with open(out_path, "w", encoding="ascii", newline="\n") as handle:
        handle.write(text)

    samples = []
    for entry in entries[:5]:
        samples.append({"preset": entry["name"], "label": entry["label"],
                        "text": msg_labels[entry["label"]].replace("\x00", "")})
    return {"entries": entries, "left_out": left_out, "bytes": size,
            "lines": len(entries), "samples": samples}


def build_fields_wide_json(field_table_path, decisions_path, inputs, out_path,
                           out_name=FIELDS_WIDE_NAME):
    """The Part 1 field table plus the decision taken for each field.

    The two inputs are the Part 1 survey (which hash has how many +0x270 sites,
    what x2 held there, and the value spread over the 94 fighters) and the Part 2
    decision record. Merging them here keeps one machine-readable file that says
    both what was measured and what was chosen, and why.
    """
    with open(field_table_path, encoding="utf-8") as handle:
        table = json.load(handle)
    with open(decisions_path, encoding="utf-8") as handle:
        decisions = json.load(handle)

    rows = []
    for row in table["rows"]:
        key = row["name"] or ("hash:%s" % row["hash"])
        decision = decisions["decisions"].get(key)
        rows.append({
            "hash": row["hash"],
            "name": row["name"],
            "name_hash_verified": bool(row["name"]),
            "type": row["type"],
            "code_sites": row["code_sites"],
            "sites_via_0x270": row["via_0x270"],
            "sites_via_0x250": row["via_0x250"],
            "sites_other_displacement": row["other_displacement_sites"],
            "x2_zero_at_0x270": row["x2_zero_at_270"],
            "x2_nonzero_at_0x270": row["x2_nonzero_at_270"],
            "x2_unknown_at_0x270": row["x2_unknown_at_270"],
            "displacements": row["displacements"],
            "gunner_value": row["gunner_value"],
            "min": row["min"],
            "max": row["max"],
            "distinct_values": row["distinct_values"],
            "has_zero_or_negative_value": row["has_zero_or_negative"],
            "qualifies": row["qualifies"],
            "not_qualified_reason": row["not_qualified_reason"],
            "decision": decision["decision"] if decision else None,
            "group": decision["group"] if decision else None,
            "decision_reason": decision["reason"] if decision else
                               "no decision recorded",
        })

    counts = {}
    for row in rows:
        counts[row["decision"]] = counts.get(row["decision"], 0) + 1
    doc = {
        "format_version": "1.0.0",
        "task": "P10-PRESET-WIDE",
        "purpose": "FIELD_TABLE_PLUS_THE_DECISION_TAKEN_FOR_EACH_FIELD",
        "evidence_tier": "B (measured offline from the user's own extracted files)",
        "disclaimer": [
            "A +0x270 site with x2 == 0 proves the engine CAN ask for that field",
            "through the hooked getter. It does not prove the engine does ask",
            "during play, nor that the value it gets back changes movement.",
            "Only the plugin log on the console answers that, per field.",
        ],
        "inputs": inputs,
        "qualifying_rule": ("float, at least one code site calling through vtable slot "
                            "+0x270 with x2 == 0, and more than one distinct value "
                            "over the 94 fighters"),
        "field_count": len(rows),
        "decision_counts": {str(k): counts[k] for k in sorted(counts, key=lambda v: str(v))},
        "chosen_fields": decisions["chosen"],
        "max_fields": decisions["max_fields"],
        "fields": rows,
    }
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(doc, handle, indent=1, ensure_ascii=True, sort_keys=False)
        handle.write("\n")
    return doc


def build_fighters_json(written, msg_labels, inputs, out_path):
    """The fighter list, with the display-name label only where a rule holds.

    Rule, measured on this file: the display name of a fighter kind whose
    internal name is `N` is the message label `nam_chr0_00_<N>` in
    ui/message/msg_name.msbt. It resolves for 82 of the 94 kinds. The other four
    `nam_chr*_00_` families (`nam_chr1_00_`, `nam_chr2_00_`, `nam_chr3_00_`,
    `nam_chr_no_00_`) do not hold for all kinds, so they are not used as a
    fallback: picking one of them would be a guess about which family a given
    screen reads. Where `nam_chr0_00_<N>` is absent the field stays null and
    the kind is listed in `display_name_label_rule_exceptions`.
    """
    prefix = "nam_chr0_00_"
    resolved = [p for p in sorted(msg_labels) if p.startswith(prefix)]
    exceptions = []
    entries = []
    for preset in written:
        label = prefix + preset["name"]
        if label in msg_labels:
            found, why = label, None
        else:
            found, why = None, "no %s%s in msg_name.msbt" % (prefix, preset["name"])
            exceptions.append({"name": preset["name"], "kind_hash": preset["kind_hash"],
                               "reason": why})
        entries.append({
            "name": preset["name"],
            "kind_hash": preset["kind_hash"],
            "row_index": preset["row_index"],
            "display_name_label": found,
        })

    doc = {
        "format_version": "1.0.0",
        "task": "P6-PRESET-DATA",
        "purpose": "MACHINE_READABLE_FIGHTER_LIST_FOR_THE_PRESET_UI",
        "evidence_tier": "B (measured offline from the user's own extracted files)",
        "disclaimer": [
            "display_name_label is a message LABEL, not the text. The English text stays",
            "in the game file and is counted in the report only; it is not copied here.",
            "This list says which presets exist. It says nothing about how they behave.",
        ],
        "inputs": inputs,
        "order": "same order as presets.txt",
        "display_name_label_rule": {
            "file": "ui/message/msg_name.msbt",
            "rule": "display_name_label = 'nam_chr0_00_' + <fighter internal name>",
            "holds_for": sum(1 for e in entries if e["display_name_label"]),
            "total_fighters": len(entries),
            "families_not_used": ["nam_chr1_00_", "nam_chr2_00_", "nam_chr3_00_",
                                  "nam_chr_no_00_"],
            "families_not_used_reason": (
                "no family other than nam_chr0_00_ resolves for all kinds, so using one "
                "of them as a fallback would guess which screen reads it"
            ),
            "labels_matching_the_prefix_in_the_file": len(resolved),
        },
        "display_name_label_rule_exceptions": exceptions,
        "fighters": entries,
    }
    with open(out_path, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(doc, handle, indent=1, ensure_ascii=True, sort_keys=False)
        handle.write("\n")
    return doc


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fighter-param", default=DEFAULT_PRC)
    parser.add_argument("--labels", default=DEFAULT_LABELS)
    parser.add_argument("--msg-name", default=DEFAULT_MSG_NAME)
    parser.add_argument("--fields", default=DEFAULT_FIELDS)
    parser.add_argument("--out-dir", default=DEFAULT_OUT)
    parser.add_argument("--expect-hash", action="append", default=[])
    parser.add_argument("--write-list", action="store_true",
                        help="also write list.txt and fields_wide.json")
    parser.add_argument("--decisions", default=DEFAULT_DECISIONS)
    parser.add_argument("--field-table", default=DEFAULT_FIELD_TABLE)
    parser.add_argument("--label-prefix", default=LIST_LABEL_PREFIX)
    parser.add_argument("--list-exclude", default=DEFAULT_LIST_EXCLUDE,
                        help="explicit preset names to omit from list.txt (default: next to this script)")
    parser.add_argument("--list-name", default=LIST_NAME)
    parser.add_argument("--fields-json-name", default=FIELDS_WIDE_NAME)
    parser.add_argument("--presets-name", default=PRESETS_NAME)
    parser.add_argument("--fighters-name", default=FIGHTERS_NAME)
    parser.add_argument("--full-name", default=FULL_NAME)
    args = parser.parse_args(argv)

    prc = import_prc()
    prc_path = os.path.join(ROOT, args.fighter_param)
    labels_path = os.path.join(ROOT, args.labels)
    msg_path = os.path.join(ROOT, args.msg_name)
    fields_path = os.path.join(ROOT, args.fields)
    out_dir = os.path.join(ROOT, args.out_dir)
    decisions_path = os.path.join(ROOT, args.decisions)
    table_path = os.path.join(ROOT, args.field_table)

    for path in (prc_path, labels_path, msg_path, fields_path):
        if not os.path.isfile(path):
            raise SystemExit("input not found: %s" % os.path.relpath(path, ROOT))
    if args.write_list:
        for path in (decisions_path, table_path, os.path.join(ROOT, args.list_exclude)):
            if not os.path.isfile(path):
                raise SystemExit("input not found: %s" % os.path.relpath(path, ROOT))
    for name in (args.presets_name, args.fighters_name, args.full_name):
        if "/" in name or "\\" in name or name in ("", ".", ".."):
            raise SystemExit("output file name %r must be a plain name" % name)

    prc_hash = sha256_of(prc_path)
    wanted = args.expect_hash or [PINNED_PRC_SHA256]
    for want in wanted:
        if prc_hash != want:
            raise SystemExit("fighter_param.prc sha256 is %s, expected %s"
                             % (prc_hash, want))
    if not args.expect_hash and prc_hash != PINNED_PRC_SHA256:
        # unreachable given `wanted`, kept as an explicit record of the pin
        raise SystemExit("pinned hash mismatch")

    labels, label_stats = load_labels(labels_path)
    field_names = load_field_list(fields_path)

    sys.path.insert(0, HERE)
    import msbt as msbt_reader
    msg_labels, msg_head, msg_undecodable = msbt_reader.read_labels_counted(msg_path)

    os.makedirs(out_dir, exist_ok=True)
    out_full = os.path.join(out_dir, args.full_name)
    out_presets = os.path.join(out_dir, args.presets_name)
    out_fighters = os.path.join(out_dir, args.fighters_name)
    out_list = os.path.join(out_dir, args.list_name)
    out_fields_wide = os.path.join(out_dir, args.fields_json_name)

    inputs = {
        "fighter_param": {
            "relative_path": args.fighter_param,
            "sha256": prc_hash,
            "bytes": os.path.getsize(prc_path),
        },
        "labels": {
            "relative_path": args.labels,
            "sha256": sha256_of(labels_path),
            "bytes": os.path.getsize(labels_path),
            "role": "name dictionary only; a name is used only when it re-hashes to its key",
            **label_stats,
        },
        "msg_name": {
            "relative_path": args.msg_name,
            "sha256": sha256_of(msg_path),
            "bytes": os.path.getsize(msg_path),
            "label_count": len(msg_labels),
            "undecodable_labels": len(msg_undecodable),
            "container": msg_head,
        },
        "fields": {
            "relative_path": args.fields,
            "sha256": sha256_of(fields_path),
            "field_count": len(field_names),
        },
    }

    rows, kind_key, field_counts = read_table(prc, prc_path)
    doc = build_full_json(rows, kind_key, labels, prc, inputs, out_full, field_counts)
    written, skipped, resolved = build_presets(
        rows, kind_key, labels, prc, field_names, inputs, out_presets,
        out_name=args.presets_name)
    fighters = build_fighters_json(written, msg_labels, inputs, out_fighters)

    listing = wide = None
    if args.write_list:
        excluded_names = load_list_exclusions(os.path.join(ROOT, args.list_exclude))
        listing = build_list(written, msg_labels, inputs, out_list,
                             out_name=args.list_name, prefix=args.label_prefix,
                             excluded_names=excluded_names)
        wide = build_fields_wide_json(table_path, decisions_path, inputs,
                                      out_fields_wide, out_name=args.fields_json_name)

    presets_size = os.path.getsize(out_presets)
    print("rows                     %d" % len(rows))
    print("field count per row      %s (equal for all rows: %s)"
          % (", ".join(str(c) for c in doc["field_count_per_row"]),
             "yes" if doc["field_count_equal_for_all_rows"] else "no"))
    print("field type counts        %s" % doc["field_type_counts"])
    print("unlabelled field names   %d" % doc["unlabelled_field_count"])
    print("presets written          %d" % len(written))
    print("presets skipped          %d" % len(skipped))
    for item in skipped:
        print("   skip row %-3d %s  %s"
              % (item["row_index"], item["kind_hash"], item["reason"]))
    print("presets.txt bytes        %d (plugin 16 KiB limit fits: %s)"
          % (presets_size, "yes" if presets_size <= 16 * 1024 else "NO"))
    print("fields per preset        %d (contract A allows 48; distinct hashes %d)"
          % (len(resolved), len(set(k for _n, k in resolved))))
    print("presets bytes            %d (contract A limit %d)"
          % (presets_size, PRESET_MAX_BYTES))
    print("display label rule holds %d / %d"
          % (fighters["display_name_label_rule"]["holds_for"],
             fighters["display_name_label_rule"]["total_fighters"]))
    for item in fighters["display_name_label_rule_exceptions"]:
        print("   no label  %-14s %s" % (item["name"], item["reason"]))
    if listing is not None:
        print("list.txt lines           %d (contract F allows 128)"
              % listing["lines"])
        print("list.txt bytes           %d (contract F limit %d)"
              % (listing["bytes"], LIST_MAX_BYTES))
        print("list.txt left out        %d" % len(listing["left_out"]))
        for item in listing["left_out"]:
            print("   no line   %-14s row %-3d %s"
                  % (item["name"], item["row_index"], item["reason"]))
        for sample in listing["samples"]:
            print("   sample    %-12s -> %-24s %r"
                  % (sample["preset"], sample["label"], sample["text"]))
        print("fields_wide.json         %d fields, decisions %s"
              % (wide["field_count"], wide["decision_counts"]))
    print("wrote                    %s" % args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
