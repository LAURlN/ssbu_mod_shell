#!/usr/bin/env python
"""Rebuild and validate P14's playable-only list and matching display names."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.abspath(os.path.join(HERE, "..", ".."))
ROOT = os.path.abspath(os.path.join(MOD, "..", ".."))
OUT = os.path.join(ROOT, "gamedata/mii_customizer/P14-LIST-PLAYABLE")
TMP = os.path.join(OUT, "_check_tmp")
SCRATCH = os.path.join(MOD, "scratch/2026-10-07_P14-LIST-PLAYABLE")
sys.path.insert(0, os.path.join(MOD, "tools/stat-presets"))
sys.path.insert(0, os.path.join(ROOT, "mods/ssbu_mod_new/src/pgwr/tools"))
import msbt
import prc

CURRENT = os.path.join(ROOT, "gamedata/mii_customizer/COORD-session3")
WIDE = os.path.join(ROOT, "gamedata/mii_customizer/P10-PRESET-WIDE")
DB = os.path.join(OUT, "files/ui/param/database/ui_chara_db.prc")
MSG = os.path.join(ROOT, "gamedata/mii_customizer/P6-PRESET-DATA/files/ui/message/msg_name.msbt")
LABELS_CSV = os.path.join(ROOT, "mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv")
BUILD = os.path.join(MOD, "tools/stat-presets/build_presets.py")
EXCLUDE = os.path.join(MOD, "tools/stat-presets/list_exclude.txt")
PRESET_LINE = re.compile(rb"^fighter ([a-z0-9_]{1,31}) 0x[0-9a-f]{10}$")
FIELD_RE = re.compile(r"^[a-z0-9_]{1,31}$")
LABEL_RE = re.compile(r"^[a-z0-9_]{1,63}$")
CHECKS = []


def check(label, ok, detail=""):
    CHECKS.append((label, bool(ok)))
    print(("PASS" if ok else "FAIL") + " " + label + (" -- " + detail if detail else ""))
    return bool(ok)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def parse_rows(path, version):
    raw = open(path, "rb").read()
    text = raw.decode("utf-8")
    lines = text.splitlines()
    if not lines or lines[0] != version:
        raise ValueError(path + ": bad version line")
    rows = []
    for line in lines[1:]:
        if not line or line.startswith("#"):
            continue
        if version == "mc_list 1":
            words = line.split()
            if len(words) != 2 or not FIELD_RE.fullmatch(words[0]) or not LABEL_RE.fullmatch(words[1]):
                raise ValueError(path + ": invalid list row " + repr(line))
            rows.append((words[0], words[1]))
        else:
            name, sep, text = line.partition(" ")
            value = text.strip(" \t\r")
            encoded = value.encode("utf-8")
            if not sep or not FIELD_RE.fullmatch(name) or not 1 <= len(encoded) <= 40:
                raise ValueError(path + ": invalid names row " + repr(line))
            if any(ord(c) < 0x20 or 0x7f <= ord(c) < 0xa0 or ord(c) > 0xffff for c in value):
                raise ValueError(path + ": invalid names text " + repr(value))
            rows.append((name, value))
    if len(raw) > 16 * 1024 or b"\x00" in raw:
        raise ValueError(path + ": size or NUL violation")
    return rows


def bytes_minus_line(path, expected_line):
    raw_lines = open(path, "rb").readlines()
    target = expected_line.encode("ascii") + b"\n"
    if raw_lines.count(target) != 1:
        return None
    raw_lines.remove(target)
    return b"".join(raw_lines)


def presets(path):
    names = []
    for line in open(path, "rb"):
        match = PRESET_LINE.fullmatch(line.rstrip(b"\r\n"))
        if match:
            names.append(match.group(1).decode("ascii"))
    return names


def parse_labels_csv(path):
    result = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[1] not in ("", "-1", "-2"):
                result[int(row[0], 16)] = row[1]
    return result


def css_rows():
    # Decode the one top-level list in the extracted ui_chara_db.prc.
    top = dict(prc.read(DB)[1])
    if len(top) != 1 or next(iter(top.values()))[0] != "list":
        raise ValueError("unexpected ui_chara_db.prc root shape")
    label_names = parse_labels_csv(LABELS_CSV)
    rows = []
    for index, node in enumerate(next(iter(top.values()))[1]):
        fields = dict(node[1])
        def field(name):
            value = fields.get(prc.hash40(name))
            if value is None:
                raise ValueError("CSS row %d has no %s" % (index, name))
            return value[1]
        kind_hash = field("fighter_kind")
        kind_label = label_names.get(kind_hash, "")
        kind = kind_label.removeprefix("fighter_kind_") if kind_label.startswith("fighter_kind_") else ""
        rows.append({"index": index, "name_id": field("name_id"), "kind": kind,
                     "can_select": field("can_select"), "disp_order": field("disp_order"),
                     "is_boss": field("is_boss"), "is_called_pokemon": field("is_called_pokemon")})
    return rows


def classify(name, source_rows):
    if name in ("popo", "nana"):
        matches = [r for r in source_rows if r["name_id"] == "ice_climber" and r["can_select"]]
        if len(matches) != 1:
            raise ValueError("could not uniquely link %s to Ice Climbers CSS row" % name)
        return True, matches[0], "paired Ice Climbers presets; their shared CSS row is selectable"
    matches = [r for r in source_rows if r["name_id"] == name or r["kind"] == name]
    selected = [r for r in matches if r["can_select"] and r["disp_order"] >= 0]
    if selected:
        return True, selected[0], "can_select=true and disp_order=%d" % selected[0]["disp_order"]
    called = [r for r in matches if r["is_called_pokemon"]]
    trainer = [r for r in source_rows if r["name_id"] == "ptrainer" and r["can_select"]]
    if called and len(trainer) == 1:
        return True, called[0], "is_called_pokemon=true; selected through selectable Pokemon Trainer"
    false = matches[0] if matches else None
    reason = "no selectable CSS entry; source row has can_select=false / disp_order=-1"
    if false and false["is_boss"]:
        reason = "boss row; can_select=false and disp_order=-1"
    return False, false, reason


def assert_semantics(list_rows, names_rows, current_rows, current_names, preset_names, msg_labels):
    if len(list_rows) != 85 or len(names_rows) != 86:
        return False
    if any(n == "koopag" for n, _ in list_rows + names_rows):
        return False
    if any(n == "miigunner" for n, _ in list_rows):
        return False
    if [n for n, _ in list_rows] != [n for n, _ in current_rows if n != "koopag"]:
        return False
    expected_names = [(n, v) for n, v in current_names if n != "koopag"]
    if names_rows != expected_names:
        return False
    if any(n not in preset_names for n, _ in list_rows):
        return False
    for n, label in list_rows:
        if label != "nam_chr1_00_" + n or label not in msg_labels:
            return False
    if set(parse_excludes()) != {"koopag", "miigunner"}:
        return False
    return True


def parse_excludes():
    result = []
    for raw in open(EXCLUDE, encoding="ascii"):
        name = raw.split("#", 1)[0].strip()
        if name:
            result.append(name)
    return result


def main():
    if os.path.exists(TMP):
        shutil.rmtree(TMP)
    os.makedirs(TMP)
    tmp_rel = os.path.relpath(TMP, ROOT)
    args = [sys.executable, "-B", BUILD, "--fields", "mods/mii_customizer/tools/stat-presets/stat_fields_wide.txt",
            "--out-dir", tmp_rel, "--presets-name", "presets_wide.txt", "--write-list",
            "--list-name", "list.txt", "--fields-json-name", "fields_wide.json"]
    built = subprocess.run(args, cwd=ROOT, capture_output=True, text=True)
    check("generator exit", built.returncode == 0, built.stderr.strip())
    if built.returncode:
        print(built.stdout)
        shutil.rmtree(TMP)
        return 1

    # These P10 outputs must be byte-identical. list.txt is intentionally the one changed output.
    for filename in ("presets_wide.txt", "fields_wide.json", "fighters.json", "fighter_param_full.json"):
        a, b = os.path.join(TMP, filename), os.path.join(WIDE, filename)
        check("unchanged output " + filename, sha(a) == sha(b), sha(a))

    generated_list = os.path.join(TMP, "list.txt")
    list_rows = parse_rows(os.path.join(OUT, "list.txt"), "mc_list 1")
    generated_rows = parse_rows(generated_list, "mc_list 1")
    check("rebuild matches delivered list", open(generated_list, "rb").read() == open(os.path.join(OUT, "list.txt"), "rb").read())
    names_rows = parse_rows(os.path.join(OUT, "names.txt"), "mc_names 1")
    old_list = parse_rows(os.path.join(CURRENT, "list.txt"), "mc_list 1")
    old_names = parse_rows(os.path.join(CURRENT, "names.txt"), "mc_names 1")
    check("current list diff is exactly removal of koopag",
          [x for x in old_list if x not in list_rows] == [("koopag", "nam_chr1_00_koopag")]
          and [x for x in list_rows if x not in old_list] == [])
    check("list bytes differ only by the koopag row",
          open(os.path.join(OUT, "list.txt"), "rb").read()
          == bytes_minus_line(os.path.join(CURRENT, "list.txt"), "koopag nam_chr1_00_koopag"))
    expected_names = [(n, v) for n, v in old_names if n != "koopag"]
    check("current names diff removes koopag and retains the Mii Gunner default", names_rows == expected_names
          and names_rows.count(("miigunner", "Mii Gunner")) == 1)
    check("names bytes differ only by the koopag row",
          open(os.path.join(OUT, "names.txt"), "rb").read()
          == bytes_minus_line(os.path.join(CURRENT, "names.txt"), "koopag Giga Bowser"))
    labels = msbt.read_labels(MSG)
    check("every listed preset exists in presets_wide.txt",
          all(n in presets(os.path.join(WIDE, "presets_wide.txt")) for n, _ in list_rows))
    check("koopag is absent", all(n != "koopag" for n, _ in list_rows))
    check("format, count, and labels", len(list_rows) == 85 and len(names_rows) == 86
          and all(label == "nam_chr1_00_" + n and label in labels for n, label in list_rows))

    # Negative control: inject the known non-selectable boss row; the semantic audit must reject it.
    bad = list_rows + [("koopag", "nam_chr1_00_koopag")]
    negative_detected = not assert_semantics(bad, names_rows, old_list, old_names,
                                              presets(os.path.join(WIDE, "presets_wide.txt")), labels)
    check("negative control detects reintroduced koopag", negative_detected)

    source = css_rows()
    full = json.load(open(os.path.join(WIDE, "fighter_param_full.json"), encoding="utf-8"))
    rendered = []
    for row in full["rows"]:
        preset = row["fighter_kind_name"].removeprefix("fighter_kind_")
        if not preset:
            preset = row["fighter_kind_hash"]
        playable, css, why = classify(preset, source)
        label = "nam_chr1_00_" + preset
        display = labels.get(label, "").rstrip("\x00").strip() or "(no nam_chr1_00 label)"
        listed = preset in {n for n, _ in old_list}
        if preset == "koopag":
            decision = "remove; explicit exclusion"
        elif preset == "miigunner":
            decision = "exclude; Mii Gunner is page row 0 default"
        elif preset.startswith("miienemy"):
            decision = "exclude; existing miienemy prefix rule"
        elif not labels.get(label):
            decision = "already excluded; no nam_chr1_00 label"
        elif playable:
            decision = "keep" if listed else "not listed; source/label cross-check"
        else:
            decision = "exclude; not selectable"
        rendered.append((preset, display, "yes" if listed else "no", "yes" if playable else "no", decision, why))
    check("all 94 source rows classified", len(rendered) == 94 and len(source) == 121)
    for row in rendered:
        print("TABLE\t" + "\t".join(row))
    check("all delivered list rows are playable and named",
          all(playable and labels.get("nam_chr1_00_" + name)
              for name, _label in list_rows
              for playable, _css, _why in [classify(name, source)]))
    check("regenerated artifacts satisfy all semantic invariants",
          assert_semantics(list_rows, names_rows, old_list, old_names,
                           presets(os.path.join(WIDE, "presets_wide.txt")), labels))

    # Compile and run the unchanged plugin parsers when a host linker is available.
    host = os.path.join(SCRATCH, "p14_host_check.exe")
    rust = subprocess.run(["rustc", "--edition=2021", os.path.join(HERE, "host_check.rs"), "-o", host],
                          cwd=ROOT, capture_output=True, text=True)
    if rust.returncode == 0:
        check("plugin parser harness links unchanged sources", True)
        run = subprocess.run([host, os.path.join(WIDE, "presets_wide.txt"),
                              os.path.join(OUT, "list.txt"), os.path.join(OUT, "names.txt")],
                             cwd=ROOT, capture_output=True, text=True)
        print(run.stdout, end="")
        check("plugin list.rs and names.rs parsers", run.returncode == 0, run.stderr.strip())
    else:
        # This host has the Rust MSVC target but no link.exe. Still type-check the exact
        # source modules; use the prebuilt unchanged list parser for list.rs and a direct
        # translation of names.rs's acceptance rules for the data file.
        metadata = os.path.join(SCRATCH, "p14_host_check.rmeta")
        typed = subprocess.run(["rustc", "--edition=2021", "--emit=metadata", "-o", metadata,
                                os.path.join(HERE, "host_check.rs")], cwd=ROOT,
                               capture_output=True, text=True)
        check("plugin parser sources type-check", typed.returncode == 0, typed.stderr.strip())
        print("INFO host executable unavailable: " + rust.stderr.strip().splitlines()[0])
        old_host = os.path.join(MOD, "builds/.cache/host-test/session_check.exe")
        menu_path = os.path.join(MOD, "builds/0.5.0-menu/session/menu.txt")
        parsed = subprocess.run([old_host, os.path.join(WIDE, "presets_wide.txt"),
                                 os.path.join(OUT, "list.txt"), menu_path], cwd=ROOT,
                                capture_output=True, text=True)
        print(parsed.stdout, end="")
        list_ok = bool(re.search(r"list state_ok=true fallback=false accepted=85 rejected=0 len=85", parsed.stdout))
        check("prebuilt plugin list.rs accepts list.txt", list_ok)
        names_ok = (len(names_rows) == 86 and names_rows.count(("miigunner", "Mii Gunner")) == 1
                    and len({n for n, _ in names_rows}) == len(names_rows)
                    and all(n in presets(os.path.join(WIDE, "presets_wide.txt")) for n, _ in names_rows)
                    and all(1 <= len(v.encode("utf-8")) <= 40
                            and all(0x20 <= ord(c) <= 0xffff and not 0x7f <= ord(c) < 0xa0 for c in v)
                            for _, v in names_rows))
        check("names.rs acceptance rules for names.txt", names_ok,
              "source type-checked; host execution unavailable without link.exe")
    shutil.rmtree(TMP)
    failed = [name for name, ok in CHECKS if not ok]
    print("checks %d passed, %d failed" % (len(CHECKS) - len(failed), len(failed)))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
