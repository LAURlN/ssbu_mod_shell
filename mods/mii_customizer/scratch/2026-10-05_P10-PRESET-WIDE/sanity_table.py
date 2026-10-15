#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P10-PRESET-WIDE Part 4 - sanity table for the coordinator.

Reads (game-derived, workspace gamedata/):
    gamedata/mii_customizer/P10-PRESET-WIDE/presets_wide.txt
    gamedata/mii_customizer/P10-PRESET-WIDE/field_table.json
Reads (mod tree):
    mods/mii_customizer/tools/stat-presets/stat_fields_wide.txt   (field order)

Writes (game-derived, workspace gamedata/):
    gamedata/mii_customizer/P10-PRESET-WIDE/sanity_table.md

Every chosen field, side by side for Mii Gunner and mario, fox, purin,
ganon, kirby, straight from the generated preset file (the numbers the
plugin would hand the engine). Fields are marked `*` when at least one
of the five characters deviates from the Gunner by >= 25% of the
Gunner's value - those are the ones the user should feel first.
Nothing here runs in the game; it only shows what the file says.
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.abspath(os.path.join(HERE, "..", ".."))
ROOT = os.path.abspath(os.path.join(MOD, "..", ".."))

PRESETS = os.path.join(ROOT, "gamedata/mii_customizer/P10-PRESET-WIDE/presets_wide.txt")
FIELD_TABLE = os.path.join(ROOT, "gamedata/mii_customizer/P10-PRESET-WIDE/field_table.json")
FIELDS = os.path.join(MOD, "tools/stat-presets/stat_fields_wide.txt")
OUT = os.path.join(ROOT, "gamedata/mii_customizer/P10-PRESET-WIDE/sanity_table.md")

FIGHTERS = ["miigunner", "mario", "fox", "purin", "ganon", "kirby"]
DISPLAY = {"miigunner": "Mii Gunner", "mario": "mario", "fox": "fox",
           "purin": "purin (Jigglypuff)", "ganon": "ganon", "kirby": "kirby"}
MARK_THRESHOLD = 0.25  # relative deviation from the Gunner that gets a field marked


def load_field_names():
    names = []
    with open(FIELDS, encoding="utf-8") as handle:
        for line in handle:
            line = line.split("#")[0].strip()
            if line:
                names.append(line)
    return names


def load_hash_names():
    """field hash -> verified field name, from the Part 1 survey."""
    with open(FIELD_TABLE, encoding="utf-8") as handle:
        table = json.load(handle)
    mapping = {}
    for row in table["rows"]:
        if row["name"]:
            mapping[row["hash"]] = row["name"]
    return mapping


def load_presets():
    """preset name -> {field_name: value}, values as written in the file."""
    hash_names = load_hash_names()
    field_names = load_field_names()
    chosen = set(field_names)
    presets = {}
    current = None
    unknown = set()
    with open(PRESETS, encoding="ascii") as handle:
        for raw in handle:
            parts = raw.split("#")[0].split()
            if not parts:
                continue
            if parts[0] in ("mc_presets",):
                continue
            if parts[0] == "fighter":
                current = {}
                presets[parts[1]] = current
                continue
            name = hash_names.get(parts[0])
            if name is None:
                unknown.add(parts[0])
                continue
            if name in chosen:
                current[name] = float(parts[1])
    if unknown:
        raise SystemExit("field hashes not in the Part 1 table: %s"
                         % ", ".join(sorted(unknown)))
    missing = [f for f in field_names
               if any(presets[p].get(f) is None for p in presets)]
    if missing:
        raise SystemExit("chosen fields absent from some preset: %s"
                         % ", ".join(missing))
    return presets, field_names


def fmt(value):
    if value is None:
        return "-"
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return "%.6g" % value


def main():
    presets, field_names = load_presets()
    missing = [f for f in FIGHTERS if f not in presets]
    if missing:
        raise SystemExit("presets missing: %s" % ", ".join(missing))

    rows = []
    for field in field_names:
        values = [presets[f].get(field) for f in FIGHTERS]
        gunner = values[0]
        devs = []
        for v in values[1:]:
            if v is None or gunner is None:
                devs.append(None)
            elif gunner == 0:
                devs.append(0.0 if v == 0 else float("inf"))
            else:
                devs.append(abs(v - gunner) / abs(gunner))
        known = [d for d in devs if d is not None]
        worst = max(known) if known else None
        rows.append({"field": field, "values": values, "worst": worst,
                     "marked": worst is not None and worst >= MARK_THRESHOLD})

    lines = []
    lines.append("# P10-PRESET-WIDE Part 4 - sanity table")
    lines.append("")
    lines.append("Every chosen field (41) side by side, straight from")
    lines.append("`presets_wide.txt` - the numbers the plugin would hand the")
    lines.append("engine for a saved Mii Gunner. Evidence tier **B**: offline")
    lines.append("reading of a generated file; nothing is run in the game.")
    lines.append("")
    lines.append("Backticked field names are the marked ones: at least one")
    lines.append("of the five characters deviates from Mii Gunner by >= %d%%"
                 % int(MARK_THRESHOLD * 100))
    lines.append("of the Gunner value; those are what the user should feel")
    lines.append("first in the next test.")
    lines.append("")
    header = ["field"] + [DISPLAY[f] for f in FIGHTERS] + ["max dev"]
    lines.append("| " + " | ".join(header) + " |")
    lines.append("|" + "---|" * len(header))
    for row in rows:
        cells = ["`%s`" % row["field"] if row["marked"] else row["field"]]
        cells += [fmt(v) for v in row["values"]]
        cells.append("-" if row["worst"] is None else
                     ("%d%%" % round(row["worst"] * 100)))
        lines.append("| " + " | ".join(cells) + " |")
    marked = sum(1 for r in rows if r["marked"])
    lines.append("")
    lines.append("%d of %d fields marked; largest deviation %s%%."
                 % (marked, len(rows),
                    fmt(max((r["worst"] for r in rows if r["worst"] is not None),
                            default=0) * 100)))
    text = "\n".join(lines) + "\n"

    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print(text)
    print("wrote %s" % os.path.relpath(OUT, ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
