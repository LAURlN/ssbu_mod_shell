#!/usr/bin/env python
"""Build the P14 list and matching display-name file from the pinned local inputs."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
MOD = os.path.join(ROOT, "mods", "mii_customizer")
OUT = os.path.join(ROOT, "gamedata", "mii_customizer", "P14-LIST-PLAYABLE")
TMP = os.path.join(OUT, "_build_tmp")
sys.path.insert(0, os.path.join(MOD, "tools", "stat-presets"))
import msbt


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main():
    if os.path.exists(TMP):
        shutil.rmtree(TMP)
    rel_tmp = os.path.relpath(TMP, ROOT)
    command = [sys.executable, "-B", os.path.join(MOD, "tools/stat-presets/build_presets.py"),
               "--fields", "mods/mii_customizer/tools/stat-presets/stat_fields_wide.txt",
               "--out-dir", rel_tmp, "--presets-name", "presets_wide.txt", "--write-list",
               "--list-name", "list.txt", "--fields-json-name", "fields_wide.json"]
    run = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    print(run.stdout, end="")
    if run.returncode:
        print(run.stderr, file=sys.stderr, end="")
        return run.returncode

    old = os.path.join(ROOT, "gamedata/mii_customizer/P10-PRESET-WIDE")
    for name in ("presets_wide.txt", "fields_wide.json", "fighters.json", "fighter_param_full.json"):
        actual, expected = os.path.join(TMP, name), os.path.join(old, name)
        if sha(actual) != sha(expected):
            raise SystemExit("unchanged tool output hash mismatch: " + name)
        print("unchanged %-22s %s" % (name, sha(actual)))

    list_out = os.path.join(OUT, "list.txt")
    shutil.copyfile(os.path.join(TMP, "list.txt"), list_out)
    labels_path = os.path.join(ROOT, "gamedata/mii_customizer/P6-PRESET-DATA/files/ui/message/msg_name.msbt")
    labels = msbt.read_labels(labels_path)
    rows = []
    for raw in open(list_out, encoding="ascii"):
        line = raw.rstrip("\n")
        if line and not line.startswith("#") and line != "mc_list 1":
            rows.append(line.split())
    rows.append(["miigunner", "nam_chr1_00_miigunner"])
    output = ["mc_names 1"]
    for name, label in rows:
        if label not in labels:
            raise SystemExit("no display text for " + label)
        display = labels[label].rstrip("\x00").strip()
        raw = display.encode("utf-8")
        ok = (1 <= len(raw) <= 40 and all(0x20 <= ord(c) <= 0xffff
              and not 0x7f <= ord(c) < 0xa0 for c in display))
        if not ok:
            raise SystemExit("display text outside mc_names rules: " + repr(display))
        output.append("%s %s" % (name, display))
    names_out = os.path.join(OUT, "names.txt")
    with open(names_out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(output) + "\n")
    shutil.rmtree(TMP)
    for name in ("list.txt", "names.txt"):
        path = os.path.join(OUT, name)
        print("output %-22s lines=%d bytes=%d sha256=%s" %
              (name, len(open(path, encoding="utf-8").read().splitlines()), os.path.getsize(path), sha(path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
