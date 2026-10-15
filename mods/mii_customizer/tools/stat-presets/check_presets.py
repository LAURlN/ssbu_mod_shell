#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Check the outputs of tools/stat-presets/build_presets.py.

Task P6-PRESET-DATA. Evidence tier **B**: offline checks only. Nothing here
runs the game, and nothing here shows a preset working in game.

What it does, in order:

1. asserts the pinned input hashes;
2. regenerates all three outputs into a scratch folder and compares them
   byte-for-byte with the committed ones, including a determinism rebuild under
   three PYTHONHASHSEED values;
3. re-parses `presets.txt` with an INDEPENDENT reader -- its own tokenizer,
   which shares no code with the generator -- and compares every value
   bit-for-bit with the table in the `.prc`;
4. checks the structure the contract asks for: version line, ASCII, `\n` line
   endings, field order, no duplicate presets, names matching `[a-z0-9_]`;
5. runs the negative controls, each of which MUST fail:
   - a field removed from the field list,
   - a non-float field added to the field list,
   - a corrupted input hash.

Exit code 0 only when every check passes.

Usage, from the workspace root:

    python -B mods/mii_customizer/tools/stat-presets/check_presets.py

Temporary files go under workspace `gamedata/mii_customizer/P6-PRESET-DATA/check-tmp/`
(game-derived, so not in the mod tree) and are removed at exit.
"""
from __future__ import annotations

import json
import os
import re
import struct
import subprocess
import sys
import shutil
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
SCRATCH_REL = "gamedata/mii_customizer/P6-PRESET-DATA/check-tmp"

OUT_REL = "gamedata/mii_customizer/P6-PRESET-DATA"
PINNED_PRC_SHA256 = "87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2"
PINNED_LABELS_SHA256 = "6ae7f792609612370e6b9244e1d6986ebd8ced9bbb77fad49de8c568919344f4"
PINNED_MSG_NAME_SHA256 = "9efc357db8ea46e671222dbbd90bbdc0ea5455383090fae3fe2ba6017e9da3ad"

RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), detail))
    print("%-4s %s%s" % ("ok" if ok else "FAIL", name, ("  -- " + detail) if detail else ""))
    return bool(ok)


def abspath(rel):
    return os.path.join(ROOT, rel)


def sha256_of(path):
    import hashlib
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_generator(out_dir_rel, extra=None):
    """Run the generator; return (returncode, stdout+stderr)."""
    cmd = [sys.executable, "-B", os.path.join(HERE, "build_presets.py"),
           "--out-dir", out_dir_rel]
    if extra:
        cmd.extend(extra)
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# --------------------------------------------------------------------------
# independent preset reader: its own tokenizer, no import from the generator
# --------------------------------------------------------------------------

HASH_RE = re.compile(r"^0x([0-9a-f]{10})$")
NAME_RE = re.compile(r"^[a-z0-9_]+$")
NUM_RE = re.compile(r"^-?(?:[0-9]+)(?:\.[0-9]+)?$")


def read_presets_independently(path):
    """Parse presets.txt from scratch. Returns (version, [preset], comments).

    Deliberately strict: it refuses anything the contract does not allow, so a
    file the generator could emit but the plugin could not read is rejected
    here rather than at runtime on the console.
    """
    with open(path, "rb") as handle:
        blob = handle.read()
    if b"\r\n" in blob:
        raise ValueError("CRLF line ending present")
    if b"\r" in blob:
        raise ValueError("bare CR present")
    try:
        text = blob.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("not pure ASCII: %s" % exc)

    comments = 0
    presets = []
    current = None
    version = None
    lines = text.split("\n")
    # The contract is explicit that line 1 is the version line, and the
    # loadout parser the plugin ships refuses a file whose first line is not
    # exactly it. Comments may follow, never precede. Enforced here, not
    # assumed.
    if not lines or lines[0] != "mc_presets 1":
        raise ValueError("line 1 is %r, expected 'mc_presets 1'"
                         % (lines[0] if lines else None))
    for lineno, line in enumerate(lines, 1):
        if lineno == len(lines) and line == "":
            break
        stripped = line.strip()
        if stripped == "":
            continue
        if stripped.startswith("#"):
            comments += 1
            continue
        if version is None:
            version = stripped
            continue
        if version != "mc_presets 1":
            raise ValueError("bad version line %r" % version)
        parts = stripped.split(" ")
        if parts[0] == "fighter":
            if len(parts) != 3:
                raise ValueError("line %d: fighter line needs 3 fields" % lineno)
            if not NAME_RE.match(parts[1]):
                raise ValueError("line %d: bad preset name %r" % (lineno, parts[1]))
            if not HASH_RE.match(parts[2]):
                raise ValueError("line %d: bad kind hash %r" % (lineno, parts[2]))
            current = {"name": parts[1], "kind_hash": parts[2], "fields": []}
            presets.append(current)
            continue
        if parts[0].startswith("0x"):
            if current is None:
                raise ValueError("line %d: field line before any fighter line" % lineno)
            if len(parts) != 2:
                raise ValueError("line %d: field line needs 2 fields" % lineno)
            if not HASH_RE.match(parts[0]):
                raise ValueError("line %d: bad field hash %r" % (lineno, parts[0]))
            if not NUM_RE.match(parts[1]):
                raise ValueError("line %d: value %r is not a plain decimal"
                                 % (lineno, parts[1]))
            current["fields"].append((parts[0], parts[1]))
            continue
        raise ValueError("line %d: unrecognised line %r" % (lineno, stripped))
    if version is None:
        raise ValueError("no version line")
    return version, presets, comments


def f32_bits(text):
    return struct.unpack("<I", struct.pack("<f", float(text)))[0]


def main():
    os.makedirs(abspath(SCRATCH_REL), exist_ok=True)
    scratch = tempfile.mkdtemp(prefix="check-", dir=abspath(SCRATCH_REL))

    full_rel = os.path.join(OUT_REL, "fighter_param_full.json")
    presets_rel = os.path.join(OUT_REL, "presets.txt")
    fighters_rel = os.path.join(OUT_REL, "fighters.json")

    # ---- 1. pinned input hashes ------------------------------------------
    exclude_path = os.path.join(HERE, "list_exclude.txt")
    exclusion_names = []
    with open(exclude_path, encoding="ascii") as handle:
        for raw in handle:
            name = raw.split("#", 1)[0].strip()
            if name:
                exclusion_names.append(name)
    check("list exclusion file contains only the reviewed names",
          exclusion_names == ["koopag", "miigunner"], ", ".join(exclusion_names))
    check("input fighter_param.prc sha256 pinned",
          sha256_of(abspath("gamedata/mii_customizer/P1-CATALOG/files/"
                            "fighter/common/param/fighter_param.prc")) == PINNED_PRC_SHA256,
          PINNED_PRC_SHA256)
    check("input ParamLabels.csv sha256 pinned",
          sha256_of(abspath("mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv"))
          == PINNED_LABELS_SHA256, PINNED_LABELS_SHA256)
    check("input msg_name.msbt sha256 pinned",
          sha256_of(abspath(os.path.join(OUT_REL, "files/ui/message/msg_name.msbt")))
          == PINNED_MSG_NAME_SHA256, PINNED_MSG_NAME_SHA256)

    # ---- 2. regenerate and compare ---------------------------------------
    regen_rel = os.path.relpath(os.path.join(scratch, "regen"), ROOT).replace("\\", "/")
    code, log = run_generator(regen_rel)
    if not check("generator reruns cleanly", code == 0, log.strip().splitlines()[-1] if log.strip() else ""):
        return 1
    for rel in (full_rel, presets_rel, fighters_rel):
        a, b = abspath(rel), abspath(os.path.join(regen_rel, os.path.basename(rel)))
        check("regenerated %s is byte-identical" % os.path.basename(rel),
              os.path.isfile(b) and open(a, "rb").read() == open(b, "rb").read())

    # determinism under different hash seeds
    for seed in ("0", "1", "12345"):
        env_dir = os.path.relpath(os.path.join(scratch, "seed" + seed), ROOT).replace("\\", "/")
        env = dict(os.environ, PYTHONHASHSEED=seed)
        cmd = [sys.executable, "-B", os.path.join(HERE, "build_presets.py"),
               "--out-dir", env_dir]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
        same = proc.returncode == 0 and all(
            open(abspath(rel), "rb").read()
            == open(abspath(os.path.join(env_dir, os.path.basename(rel))), "rb").read()
            for rel in (full_rel, presets_rel, fighters_rel))
        check("deterministic under PYTHONHASHSEED=%s" % seed, same)

    # ---- 3. independent re-parse, bit-for-bit against the .prc ------------
    sys.path.insert(0, os.path.join(ROOT, "mods", "ssbu_mod_new", "src", "pgwr", "tools"))
    import prc

    try:
        version, presets, comments = read_presets_independently(abspath(presets_rel))
        check("presets.txt parses with the independent reader", True,
              "%d presets, %d comment lines" % (len(presets), comments))
    except ValueError as exc:
        check("presets.txt parses with the independent reader", False, str(exc))
        return 1
    check("presets.txt version line is 'mc_presets 1'", version == "mc_presets 1", version)

    root = prc.as_dict(prc.read(abspath(
        "gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/"
        "fighter_param.prc")))
    table = root[prc.hash40("fighter_param_table")][1]
    kind_key = prc.hash40("fighter_kind")

    by_hash = {}
    for row in table:
        d = prc.as_dict(row)
        by_hash[d[kind_key][1]] = d

    field_order = []
    with open(abspath("mods/mii_customizer/tools/stat-presets/stat_fields.txt"),
              encoding="utf-8") as handle:
        for raw in handle:
            line = raw.split("#", 1)[0].strip()
            if line:
                field_order.append(prc.hash40(line))
    field_order_hex = ["0x%010x" % h for h in field_order]

    mismatches = []
    seen_names = set()
    order_ok = True
    for preset in presets:
        if preset["name"] in seen_names:
            mismatches.append("duplicate preset name %s" % preset["name"])
        seen_names.add(preset["name"])
        row = by_hash.get(int(preset["kind_hash"], 16))
        if row is None:
            mismatches.append("kind %s not in the table" % preset["kind_hash"])
            continue
        got = [h for h, _ in preset["fields"]]
        if got != field_order_hex:
            order_ok = False
            mismatches.append("%s: field order/count differs" % preset["name"])
            continue
        for (fh, text), want_hash in zip(preset["fields"], field_order):
            node = row.get(want_hash)
            if node is None:
                mismatches.append("%s: %s absent from row" % (preset["name"], fh))
                continue
            if node[0] != "float":
                mismatches.append("%s: %s is %s not float" % (preset["name"], fh, node[0]))
                continue
            if f32_bits(text) != struct.unpack("<I", struct.pack("<f", node[1]))[0]:
                mismatches.append("%s: %s value %s != table %r"
                                  % (preset["name"], fh, text, node[1]))
    check("every preset field hash appears in stat_fields.txt order", order_ok)
    check("every preset value re-parses bit-for-bit to the table",
          not mismatches,
          "; ".join(mismatches[:3]) if mismatches else "%d values compared" % (
              sum(len(p["fields"]) for p in presets)))

    # preset name must come from a hash-verified kind label
    import csv
    labels = {}
    with open(abspath("mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv"),
              newline="", encoding="utf-8", errors="replace") as handle:
        for row in csv.reader(handle):
            if len(row) >= 2 and row[1] not in ("", "-1", "-2"):
                labels.setdefault(int(row[0], 16), row[1])
    name_bad = []
    for preset in presets:
        kind = int(preset["kind_hash"], 16)
        label = labels.get(kind)
        if label is None or prc.hash40(label) != kind:
            name_bad.append(preset["name"])
        elif label != "fighter_kind_" + preset["name"]:
            name_bad.append(preset["name"])
    check("every preset name comes from a hash-verified kind label",
          not name_bad, ", ".join(name_bad[:5]))

    # ---- 4. fighters.json agrees with presets.txt ------------------------
    fighters = json.load(open(abspath(fighters_rel), encoding="utf-8"))
    listing = fighters["fighters"]
    check("fighters.json is in presets.txt order",
          [e["name"] for e in listing] == [p["name"] for p in presets])
    check("fighters.json kind hashes match presets.txt",
          [e["kind_hash"] for e in listing] == [p["kind_hash"] for p in presets])
    rule = fighters["display_name_label_rule"]
    check("display label rule coverage is recorded",
          rule["holds_for"] == sum(1 for e in listing if e["display_name_label"]),
          "%d / %d" % (rule["holds_for"], rule["total_fighters"]))

    full = json.load(open(abspath(full_rel), encoding="utf-8"))
    check("full table row count matches presets.txt",
          full["row_count"] == len(presets), "%d rows" % full["row_count"])
    check("full table field count equal for all rows",
          full["field_count_equal_for_all_rows"] is True,
          str(full["field_count_per_row"]))
    check("full table has no absolute paths",
          ROOT.lower() not in json.dumps(full).lower()
          and "d:\\" not in json.dumps(full).lower())

    # ---- 5. negative controls: each MUST fail ---------------------------
    fields_src = abspath("mods/mii_customizer/tools/stat-presets/stat_fields.txt")
    original = open(fields_src, encoding="utf-8").read()

    # (a) a field removed from the list
    bad_fields = os.path.join(scratch, "fields_missing_one.txt")
    kept = [ln for ln in original.splitlines() if ln.strip() and not ln.strip().startswith("weight")]
    open(bad_fields, "w", encoding="utf-8", newline="\n").write("\n".join(kept) + "\n")
    neg_out = os.path.relpath(os.path.join(scratch, "neg_missing"), ROOT).replace("\\", "/")
    code, log = run_generator(neg_out, ["--fields", os.path.relpath(bad_fields, ROOT).replace("\\", "/")])
    differing = code == 0 and os.path.isfile(
        abspath(os.path.join(neg_out, "presets.txt"))) and \
        open(abspath(presets_rel), "rb").read() != open(
            abspath(os.path.join(neg_out, "presets.txt")), "rb").read()
    check("negative control: a field removed from the list changes the output",
          differing or code != 0,
          "generator refused it" if code != 0 else "output differs as expected")

    # (b) a non-float field added
    bad_fields2 = os.path.join(scratch, "fields_nonfloat.txt")
    open(bad_fields2, "w", encoding="utf-8", newline="\n").write(
        original.rstrip("\n") + "\njump_count_max\n")
    code2, log2 = run_generator(os.path.relpath(os.path.join(scratch, "neg_nonfloat"), ROOT).replace("\\", "/"),
                                ["--fields", os.path.relpath(bad_fields2, ROOT).replace("\\", "/")])
    check("negative control: a non-float field is refused loudly",
          code2 != 0 and "expected float" in log2,
          log2.strip().splitlines()[-1] if log2.strip() else "no message")
    neg_nonfloat_presets = abspath(os.path.join(scratch, "neg_nonfloat", "presets.txt"))
    check("negative control: refused run wrote no preset file",
          not os.path.isfile(neg_nonfloat_presets))

    # (c) a corrupted input hash
    code3, log3 = run_generator(
        os.path.relpath(os.path.join(scratch, "neg_hash"), ROOT).replace("\\", "/"),
        ["--expect-hash", "0" * 64])
    check("negative control: a corrupted expected hash is refused loudly",
          code3 != 0 and "sha256" in log3,
          log3.strip().splitlines()[-1] if log3.strip() else "no message")
    neg_hash_presets = abspath(os.path.join(scratch, "neg_hash", "presets.txt"))
    check("negative control: hash-refused run wrote no preset file",
          not os.path.isfile(neg_hash_presets))

    # (d) the comparison must not be vacuous. Control (a) only proves the
    # generator reacts to the field list; this proves the bit comparison
    # actually rejects a wrong value. A tampered copy of presets.txt is fed to
    # the same comparison used above and must produce a mismatch.
    tampered_path = os.path.join(scratch, "presets_tampered.txt")
    blob = open(abspath(presets_rel), "rb").read().decode("ascii")
    with open(tampered_path, "w", encoding="ascii", newline="") as handle:
        handle.write(blob.replace("0x0607cd5541 98", "0x0607cd5541 99", 1))
    try:
        _v, tampered_presets, _c = read_presets_independently(tampered_path)
        bad = []
        for preset in tampered_presets:
            row = by_hash.get(int(preset["kind_hash"], 16))
            for fh, text in preset["fields"]:
                key = int(fh, 16)
                if key in row and f32_bits(text) != struct.unpack(
                        "<I", struct.pack("<f", row[key][1]))[0]:
                    bad.append("%s %s" % (preset["name"], fh))
        caught = bool(bad)
    except ValueError as exc:
        caught, bad = True, [str(exc)]
    check("negative control: a tampered preset value is caught by the comparison",
          caught, "; ".join(bad[:3]) if bad else "no mismatch found")

    # (e) the version line must be line 1. A file whose header comments come
    # first would be refused whole by the plugin's existing parser, so the
    # independent reader must reject exactly the layout this tool used to emit.
    bad_order = os.path.join(scratch, "presets_versionline_second.txt")
    reordered = "# a comment first\n" + blob
    with open(bad_order, "w", encoding="ascii", newline="") as handle:
        handle.write(reordered)
    try:
        read_presets_independently(bad_order)
        rejected, why = False, "reader accepted a comment before the version line"
    except ValueError as exc:
        rejected, why = True, str(exc)
    check("negative control: a comment before the version line is rejected",
          rejected, why)
    check("negative control: comments AFTER the version line are accepted",
          read_presets_independently(abspath(presets_rel))[0] == "mc_presets 1")

    # field list restored? the tool never writes it, so confirm nothing moved
    check("stat_fields.txt untouched by the check",
          open(fields_src, encoding="utf-8").read() == original)

    failed = [name for name, ok, _ in RESULTS if not ok]
    print("\n%d checks, %d failed" % (len(RESULTS), len(failed)))
    for name in failed:
        print("  FAILED: %s" % name)
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        code = main()
    finally:
        shutil.rmtree(abspath(SCRATCH_REL), ignore_errors=True)
    raise SystemExit(code)
