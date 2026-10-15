#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P10-PRESET-WIDE: check the wide preset file and the list file.

Evidence tier B - offline checks only, nothing runs in the game.

What this script does, in order:

 1. Regenerates the wide outputs (presets_wide.txt, list.txt,
    fields_wide.json, fighters.json, fighter_param_full.json) into a
    temporary folder under workspace gamedata/ and compares them
    byte-for-byte with the delivered files.
 2. Regenerates the default outputs (presets.txt) into the same temporary
    folder and asserts the P6 byte-identity sha256.
 3. Validates presets_wide.txt against its own model of contract A
    (prompts/P7-PRESET-ENGINE.md): version line, 512 KiB, 128 presets,
    names [a-z0-9_]{1,31} and unique, 48 fields per preset, 48 distinct
    hashes, finite values.
 4. Validates list.txt against its own model of contract F
    (prompts/P10-UI-SLICE.md): version line, 16 KiB, 128 lines, label
    [a-z0-9_]{1,63}, no miienemy, and the cross-references both ways
    between list.txt and presets_wide.txt, with every label resolved in
    ui/message/msg_name.msbt.
 5. Checks fields_wide.json: every field of the table carries a decision,
    the chosen list matches stat_fields_wide.txt, the first ten are
    stat_fields.txt unchanged and in order.
 6. Runs four negative controls, each of which MUST be rejected:
    a a 49th field in the field list (the generator itself must refuse),
    b a duplicate preset name in a preset copy,
    c a list line naming a preset that does not exist,
    d a list line whose label does not exist in msg_name.msbt.
 7. Runs the P7 host-side checker (the plugin's own parser, built by
    scratch/2026-10-05_P7-PRESET-ENGINE/, used read-only) over
    presets_wide.txt when its executable is available and reports its
    output; otherwise that step is reported as skipped and the checks
    above stand on their own model.

Every temporary file is created under
gamedata/mii_customizer/P10-PRESET-WIDE/_check_tmp/ and removed at the
end, also on failure. Exit 0 = all checks pass, exit 1 = any mismatch.

usage: python mods/mii_customizer/evidence/P10-PRESET-WIDE/check_preset_wide.py
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.abspath(os.path.join(HERE, "..", ".."))          # mods/mii_customizer
ROOT = os.path.abspath(os.path.join(MOD, "..", ".."))          # workspace root

BUILD = os.path.join(MOD, "tools/stat-presets/build_presets.py")
STAT_FIELDS = os.path.join(MOD, "tools/stat-presets/stat_fields.txt")
STAT_FIELDS_WIDE = os.path.join(MOD, "tools/stat-presets/stat_fields_wide.txt")
MSBT_PATH = os.path.join(ROOT, "gamedata/mii_customizer/P6-PRESET-DATA/files/ui/message/msg_name.msbt")
OUT_DIR = os.path.join(ROOT, "gamedata/mii_customizer/P10-PRESET-WIDE")
TMP_DIR = os.path.join(OUT_DIR, "_check_tmp")
P7_EXE = os.path.join(MOD, "builds/.cache/host-test/preset_report_p7.exe")

# The P6 byte-identity required by task P10-PRESET-WIDE Part 3.
DEFAULT_PRESETS_SHA256 = "f6acbba17d510aae0f0a2cc49cc5417287d4f0d0a8428dbf52d3ca4505865c0d"

# Contract A (prompts/P7-PRESET-ENGINE.md).
A_MAX_BYTES = 512 * 1024
A_MAX_PRESETS = 128
A_MAX_FIELDS = 48
A_MAX_HASHES = 48
A_NAME_RE = re.compile(r"[a-z0-9_]{1,31}")
A_HASH_RE = re.compile(r"0x[0-9a-f]{10}")
A_VERSION = "mc_presets 1"

# Contract F (prompts/P10-UI-SLICE.md).
F_MAX_LINES = 128
F_MAX_BYTES = 16 * 1024
F_LABEL_RE = re.compile(r"[a-z0-9_]{1,63}")
F_VERSION = "mc_list 1"
F_LABEL_PREFIX = "nam_chr1_00_"
F_SKIP_PREFIX = "miienemy"

results = []


def check(name, cond, detail=""):
    """Record one PASS/FAIL line."""
    results.append((bool(cond), name, detail))
    print(("PASS " if cond else "FAIL ") + name +
          (" | " + str(detail) if str(detail) != "" else ""))
    return bool(cond)


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_field_names(path):
    """One field name per line, '#' comments allowed (own reader)."""
    fields = []
    with open(path, encoding="utf-8") as handle:
        for raw in handle:
            line = raw.split("#", 1)[0].strip()
            if line:
                fields.append(line)
    return fields


def validate_presets(path, label):
    """Own model of contract A. Returns a list of problems, empty = good."""
    errors = []
    with open(path, "rb") as handle:
        raw = handle.read()
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        return ["not plain ASCII: %s" % exc]
    if b"\r" in raw or b"\x00" in raw:
        errors.append("contains CR or NUL")
    lines = text.split("\n")
    if lines[0] != A_VERSION:
        errors.append("first line is %r, expected %r" % (lines[0], A_VERSION))
    if len(raw) > A_MAX_BYTES:
        errors.append("%d bytes, contract A allows %d" % (len(raw), A_MAX_BYTES))

    names = []
    hashes = set()
    current = None
    fields_in_preset = 0

    def close_preset():
        if current is not None and fields_in_preset > A_MAX_FIELDS:
            errors.append("preset %r has %d fields, contract A allows %d"
                          % (current, fields_in_preset, A_MAX_FIELDS))

    for lineno, line in enumerate(lines[1:], start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if parts[0] == "fighter":
            close_preset()
            if len(parts) != 3 or not A_NAME_RE.fullmatch(parts[1]) \
                    or not A_HASH_RE.fullmatch(parts[2]):
                errors.append("line %d: bad fighter line %r" % (lineno, line))
                current = None
                continue
            if parts[1] in names:
                errors.append("line %d: duplicate preset name %r"
                              % (lineno, parts[1]))
            names.append(parts[1])
            current = parts[1]
            fields_in_preset = 0
            continue
        if current is None:
            errors.append("line %d: field line outside a preset: %r"
                          % (lineno, line))
            continue
        if len(parts) != 2 or not A_HASH_RE.fullmatch(parts[0]):
            errors.append("line %d: bad field line %r" % (lineno, line))
            continue
        try:
            value = float(parts[1])
        except ValueError:
            errors.append("line %d: value %r is not a number" % (lineno, parts[1]))
            continue
        if not math.isfinite(value):
            errors.append("line %d: value %r is not finite" % (lineno, parts[1]))
        hashes.add(parts[0])
        fields_in_preset += 1
    close_preset()

    if len(names) > A_MAX_PRESETS:
        errors.append("%d presets, contract A allows %d" % (len(names), A_MAX_PRESETS))
    if not names:
        errors.append("no presets found")
    if len(hashes) > A_MAX_HASHES:
        errors.append("%d distinct field hashes, contract A allows %d"
                      % (len(hashes), A_MAX_HASHES))
    return errors


def read_msg_labels():
    """label -> raw text, via the established msbt reader (read-only)."""
    sys.path.insert(0, os.path.join(MOD, "tools/stat-presets"))
    import msbt as msbt_reader
    labels, _head, _undecodable = msbt_reader.read_labels_counted(MSBT_PATH)
    return labels


def message_text_ok(text):
    """Usable single-line text, same rule as the generator, own code."""
    if text is None:
        return False
    if "\r" in text or "\n" in text:
        return False
    return bool(text.replace("\x00", "").strip())


def validate_list(path, preset_order, msg_labels):
    """Own model of contract F plus both cross-references.

    preset_order: the preset names of presets_wide.txt in file order.
    Returns a list of problems, empty = good.
    """
    errors = []
    with open(path, "rb") as handle:
        raw = handle.read()
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        return ["not plain ASCII: %s" % exc]
    if b"\r" in raw or b"\x00" in raw:
        errors.append("contains CR or NUL")
    lines = text.split("\n")
    if lines[0] != F_VERSION:
        errors.append("first line is %r, expected %r" % (lines[0], F_VERSION))
    if len(raw) > F_MAX_BYTES:
        errors.append("%d bytes, contract F allows %d" % (len(raw), F_MAX_BYTES))

    entries = []
    for lineno, line in enumerate(lines[1:], start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) != 2:
            errors.append("line %d: not `<preset> <label>`: %r" % (lineno, line))
            continue
        name, label = parts
        entries.append((lineno, name, label))
        if name.startswith(F_SKIP_PREFIX):
            errors.append("line %d: preset %r starts with %s and must be left out"
                          % (lineno, name, F_SKIP_PREFIX))
        if not A_NAME_RE.fullmatch(name):
            errors.append("line %d: preset name %r is not [a-z0-9_]{1,31}"
                          % (lineno, name))
        if name not in preset_order:
            errors.append("line %d: list names preset %r which is not in "
                          "presets_wide.txt" % (lineno, name))
        if not F_LABEL_RE.fullmatch(label):
            errors.append("line %d: label %r is not [a-z0-9_]{1,63}"
                          % (lineno, label))
            continue
        if label not in msg_labels:
            errors.append("line %d: label %s does not exist in msg_name.msbt"
                          % (lineno, label))
        elif not message_text_ok(msg_labels[label]):
            errors.append("line %d: label %s has empty or multi-line text"
                          % (lineno, label))

    if len(entries) > F_MAX_LINES:
        errors.append("%d entries, contract F allows %d"
                      % (len(entries), F_MAX_LINES))
    names = [name for _ln, name, _lb in entries]
    if len(names) != len(set(names)):
        errors.append("duplicate preset names in the list")

    # Order: the list follows fighter_param table order = preset file order.
    listed = [preset_order.index(n) for n in names if n in preset_order]
    if listed != sorted(listed):
        errors.append("list entries are not in fighter_param table order")

    # The other direction: every preset that is not in the list must have a
    # recorded reason (miienemy prefix, or the label unusable).
    listed_set = set(names)
    for name in preset_order:
        if name in listed_set:
            continue
        if name.startswith(F_SKIP_PREFIX):
            continue
        label = F_LABEL_PREFIX + name
        if label not in msg_labels or not message_text_ok(msg_labels[label]):
            continue
        errors.append("preset %r has a usable label %s but is not in the list"
                      % (name, label))
    return errors


def run_build(extra_args):
    """Run build_presets.py with the given arguments, return (code, output)."""
    proc = subprocess.run(
        [sys.executable, "-B", BUILD] + extra_args,
        cwd=ROOT, capture_output=True, text=True)
    return proc.returncode, (proc.stdout + proc.stderr)


def regenerate_and_compare():
    """Step 1 + 2: regenerate wide and default outputs, compare bytes."""
    wide_tmp = os.path.join(TMP_DIR, "wide")
    default_tmp = os.path.join(TMP_DIR, "default")

    code, out = run_build([
        "--fields", "mods/mii_customizer/tools/stat-presets/stat_fields_wide.txt",
        "--out-dir", os.path.relpath(wide_tmp, ROOT),
        "--presets-name", "presets_wide.txt",
        "--write-list",
    ])
    check("wide regeneration exits 0", code == 0, out.strip().splitlines()[-1] if out.strip() else code)
    if code != 0:
        return
    for name in ("presets_wide.txt", "list.txt", "fields_wide.json",
                 "fighters.json", "fighter_param_full.json"):
        generated = os.path.join(wide_tmp, name)
        delivered = os.path.join(OUT_DIR, name)
        if not os.path.isfile(generated):
            check("regenerated %s exists" % name, False, "not written")
            continue
        same = sha256_of(generated) == sha256_of(delivered)
        check("%s is byte-identical to the regenerated file" % name, same,
              sha256_of(delivered))

    code, out = run_build([
        "--out-dir", os.path.relpath(default_tmp, ROOT),
    ])
    check("default regeneration exits 0", code == 0)
    if code == 0:
        digest = sha256_of(os.path.join(default_tmp, "presets.txt"))
        check("default presets.txt keeps the P6 sha256", digest == DEFAULT_PRESETS_SHA256, digest)


def check_fields_wide():
    """Step 5: every field carries a decision, the choice matches the files."""
    with open(os.path.join(OUT_DIR, "fields_wide.json"), encoding="utf-8") as handle:
        doc = json.load(handle)
    rows = doc["fields"] if "fields" in doc else doc["rows"]
    check("fields_wide.json holds one row per table field", len(rows) == 369, len(rows))
    missing = [r.get("hash") for r in rows if not r.get("decision")]
    check("every field row carries a decision", not missing,
          "%d without" % len(missing))
    counts = {}
    for row in rows:
        counts[row["decision"]] = counts.get(row["decision"], 0) + 1
    chosen = load_field_names(STAT_FIELDS_WIDE)
    ten = load_field_names(STAT_FIELDS)
    check("the first ten of stat_fields_wide.txt are stat_fields.txt in order",
          chosen[:10] == ten, chosen[:10])
    included = [r["name"] for r in rows if r["decision"] == "included"]
    # fields_wide.json rows follow fighter_param table order, the field file
    # follows the ranking order of Part 2, so membership is compared, not order.
    check("the included decisions are exactly stat_fields_wide.txt (same set)",
          set(included) == set(chosen) and len(included) == len(chosen),
          "%d included, %d in the file; only here: %s; only there: %s"
          % (len(included), len(chosen), set(included) - set(chosen),
             set(chosen) - set(included)))
    check("at most 48 fields chosen", len(chosen) <= 48, len(chosen))
    print("     decision counts: %s" % counts)
    return counts


def negative_controls(preset_errors_fn):
    """Step 6: four tampered files, each of which must be rejected."""
    # (a) a 49th field: the generator itself must refuse the list.
    extra = load_field_names(STAT_FIELDS_WIDE)
    with open(os.path.join(OUT_DIR, "fields_wide.json"), encoding="utf-8") as handle:
        wide_doc = json.load(handle)
    rows = wide_doc["fields"] if "fields" in wide_doc else wide_doc["rows"]
    for row in rows:
        if len(extra) >= 49:
            break
        if row["type"] == "float" and row.get("name") and row["name"] not in extra \
                and row.get("qualifies"):
            extra.append(row["name"])
    field49 = os.path.join(TMP_DIR, "fields_49.txt")
    with open(field49, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("# negative control (a): 49 fields\n")
        for name in extra:
            handle.write(name + "\n")
    check("negative control (a): the field list really has 49 fields",
          len(extra) == 49, len(extra))
    out49 = os.path.join(TMP_DIR, "out_49")
    code, out = run_build(["--fields", os.path.relpath(field49, ROOT),
                           "--out-dir", os.path.relpath(out49, ROOT)])
    check("negative control (a): a 49th field is refused",
          code != 0 and "contract A allows at most 48" in out,
          out.strip().splitlines()[-1] if out.strip() else code)
    check("negative control (a): no preset file is written",
          not os.path.exists(os.path.join(out49, "presets.txt")))

    # (b) a duplicate preset name inside a copy of presets_wide.txt.
    dup = os.path.join(TMP_DIR, "presets_dup.txt")
    with open(os.path.join(OUT_DIR, "presets_wide.txt"), encoding="ascii") as handle:
        text = handle.read()
    tampered = text.replace("fighter donkey ", "fighter mario ", 1)
    check("negative control (b): the tamper changed something",
          tampered != text)
    with open(dup, "w", encoding="ascii", newline="\n") as handle:
        handle.write(tampered)
    errs = preset_errors_fn(dup, "control b")
    check("negative control (b): a duplicate preset name is caught",
          any("duplicate preset name" in e for e in errs), "; ".join(errs[:3]))

    # (c) a list line naming a preset that does not exist.
    missing = os.path.join(TMP_DIR, "list_missing_preset.txt")
    with open(os.path.join(OUT_DIR, "list.txt"), encoding="ascii") as handle:
        text = handle.read()
    tampered = text.replace("mario nam_chr1_00_mario",
                            "no_such_preset nam_chr1_00_mario", 1)
    check("negative control (c): the tamper changed something",
          tampered != text)
    with open(missing, "w", encoding="ascii", newline="\n") as handle:
        handle.write(tampered)
    preset_order = preset_names(os.path.join(OUT_DIR, "presets_wide.txt"))
    errs = validate_list(missing, preset_order, read_msg_labels())
    check("negative control (c): a list line naming a missing preset is caught",
          any("not in presets_wide.txt" in e for e in errs), "; ".join(errs[:3]))

    # (d) a list line whose label does not exist in msg_name.msbt.
    badlabel = os.path.join(TMP_DIR, "list_bad_label.txt")
    with open(os.path.join(OUT_DIR, "list.txt"), encoding="ascii") as handle:
        text = handle.read()
    tampered = text.replace("mario nam_chr1_00_mario",
                            "mario nam_chr1_00_no_such_label", 1)
    check("negative control (d): the tamper changed something",
          tampered != text)
    with open(badlabel, "w", encoding="ascii", newline="\n") as handle:
        handle.write(tampered)
    errs = validate_list(badlabel, preset_order, read_msg_labels())
    check("negative control (d): a label that does not exist is caught",
          any("does not exist in msg_name.msbt" in e for e in errs),
          "; ".join(errs[:3]))


def preset_names(path):
    """Preset names of a preset file, in file order."""
    names = []
    with open(path, encoding="ascii") as handle:
        for raw in handle:
            parts = raw.split("#", 1)[0].split()
            if parts and parts[0] == "fighter":
                names.append(parts[1])
    return names


def run_p7_checker():
    """Step 7: the plugin's own parser over presets_wide.txt, if available."""
    if not os.path.isfile(P7_EXE):
        print("SKIP P7 host-side checker (not built): %s"
              % os.path.relpath(P7_EXE, ROOT))
        print("     the contract A/F checks above use this script's own model")
        return
    proc = subprocess.run(
        [P7_EXE, os.path.join(OUT_DIR, "presets_wide.txt")],
        capture_output=True, text=True)
    lines = proc.stdout.splitlines()
    print("     P7 plugin parser: %s" % (lines[0] if lines else "<no output>"))
    head = {}
    if lines:
        for token in lines[0].split():
            if "=" in token:
                key, value = token.split("=", 1)
                head[key] = value
    fpp = next((l for l in lines if l.startswith("fields_per_preset")), "")
    print("     P7 plugin parser: %s" % fpp)
    check("P7 parser: exits 0", proc.returncode == 0, proc.returncode)
    check("P7 parser: state ok, nothing rejected or skipped",
          head.get("state") == "ok" and head.get("rejected") == "0"
          and head.get("skipped") == "0", lines[0] if lines else "")
    check("P7 parser: at most 48 distinct hashes",
          int(head.get("hashes", 0)) <= 48, head.get("hashes"))
    max_fields = int(fpp.split("max=")[1].split()[0]) if "max=" in fpp else 0
    check("P7 parser: at most 48 fields per preset",
          max_fields <= 48, max_fields)


def main():
    if not os.path.isdir(TMP_DIR):
        os.makedirs(TMP_DIR)
    try:
        regenerate_and_compare()

        presets_path = os.path.join(OUT_DIR, "presets_wide.txt")
        list_path = os.path.join(OUT_DIR, "list.txt")

        errs = validate_presets(presets_path, "presets_wide")
        check("presets_wide.txt satisfies contract A (own model)", not errs,
              "; ".join(errs[:5]))

        order = preset_names(presets_path)
        msg_labels = read_msg_labels()
        errs = validate_list(list_path, order, msg_labels)
        check("list.txt satisfies contract F and both cross-references (own model)",
              not errs, "; ".join(errs[:5]))

        check_fields_wide()
        negative_controls(validate_presets)
        run_p7_checker()
    finally:
        shutil.rmtree(TMP_DIR, ignore_errors=True)
        check("temporary files removed", not os.path.exists(TMP_DIR), TMP_DIR)

    failed = [r for r in results if not r[0]]
    print("\n%d passed, %d failed" % (len(results) - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
