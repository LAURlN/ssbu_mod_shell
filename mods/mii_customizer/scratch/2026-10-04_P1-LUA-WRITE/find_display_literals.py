#!/usr/bin/env python3
"""Find string constants that look like display text rather than bridge names.

A candidate for the length-changing mutation test must be a literal that a
human reads (display text) or at worst a formatting template -- never an
identifier passed to native code, a selector/state/flag name, a layout part
name or a loop bound. This script lists the string constants that are *not*
plain identifiers so the choice can be made explicitly and recorded.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.abspath(os.path.join(HERE, "..", ".."))
ROOT = os.path.abspath(os.path.join(MOD, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "mods", "mii_customizer", "tools",
                                "lua53-inspect"))

import lua53_inspect as L  # noqa: E402

G = os.path.join(ROOT, "gamedata", "mii_customizer", "P1-UI", "ui")
PATHS = [
    os.path.join(G, "script", "menu", "chara_make", "make_mii_edit_actor.lc"),
    os.path.join(G, "script", "menu", "chara_make", "make_mii_special_actor.lc"),
    os.path.join(G, "script_patch", "chara_make", "make_mii_edit_actor.lc"),
]

IDENT = re.compile(r"\A[A-Za-z_][A-Za-z0-9_]*\Z")
REQUIRE_PATH = re.compile(r"\A[./A-Za-z0-9_]+\Z")
FORMAT = re.compile(r"\A%[-+ #0-9.]*[A-Za-z%]\Z")

for full in PATHS:
    data = open(full, "rb").read()
    main = L.load_chunk(data)[1]
    print("== %s" % os.path.basename(full))
    for p in L.walk(main):
        for k in p.constants:
            if not k.is_string:
                continue
            s = k.value or ""
            tag = "ident"
            if REQUIRE_PATH.match(s):
                tag = "path"
            elif FORMAT.match(s):
                tag = "FORMAT"
            elif IDENT.match(s):
                tag = "ident"
            else:
                tag = "OTHER"
            if tag == "OTHER" or tag == "FORMAT":
                uses = L.const_uses(p, k.index)
                how = ",".join(sorted({h for _i, h in uses})) or "UNUSED"
                print("  %-10s K[%-2d] %-6s %-7s %r" %
                      (p.path, k.index, tag, how, s))