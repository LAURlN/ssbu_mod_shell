#!/usr/bin/env python3
"""Negative controls for tools/lua-src/build_check.py.

A check that only ever prints "BYTE-IDENTICAL" proves nothing.  Each control
below deliberately breaks the build in one specific way and asserts that
``build_check.py`` notices.  The suite passes only if every control is caught.

Run from the workspace root:

    python mods/mii_customizer/tools/lua-src/negative_controls.py

Each control runs in its own throw-away copy of the workspace layout under a
temporary directory, so the real reconstructed source, the real
``build_check.py`` and the original game chunk are never modified.  The copy
holds real copies of the two inputs the check needs (``luac53-game`` and
``lua53-inspect``) plus the original chunk, and freshly copied copies of
``tools/lua-src`` and the build output directory, which the control is then
free to break.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
LUA_SRC = HERE                                          # .../tools/lua-src
TOOLS = os.path.dirname(LUA_SRC)                        # .../tools
MOD = os.path.dirname(TOOLS)                            # mods/mii_customizer
WORKSPACE = os.path.dirname(MOD)                        # workspace root

TOOL_DIRS = ("luac53-game", "lua53-inspect")
LUA_SRC_NAMES = ("build_check.py", "compare_chunks.py",
                 "make_mii_edit_actor.lua", "make_mii_special_actor.lua",
                 "README.md")
REL_ORIG = os.path.join("gamedata", "mii_customizer", "P1-UI", "ui",
                        "script_patch", "chara_make", "make_mii_edit_actor.lc")
REL_OUT = os.path.join("gamedata", "mii_customizer", "P9-EDIT-SOURCE",
                       "make_mii_edit_actor.lc")
REL_SRC = os.path.join("mods", "mii_customizer", "tools", "lua-src",
                       "make_mii_edit_actor.lua")
# absolute paths of the real files, which the controls must not disturb
ABS_SRC = os.path.join(LUA_SRC, "make_mii_edit_actor.lua")
ABS_ORIG = os.path.join(os.path.dirname(WORKSPACE), REL_ORIG)


def sha256(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


# --- the controls ----------------------------------------------------------
# Each mutates the staged workspace in place.  ``expect`` is a string that must
# appear in the check's output for the control to count as caught.

def c1_missing_source(ws: str) -> str:
    """Delete the source file: the check must report a missing input."""
    os.remove(os.path.join(ws, REL_SRC))
    return "missing input"


def c2_wrong_constant(ws: str) -> str:
    """Change a string constant: the constant table must be reported."""
    p = os.path.join(ws, REL_SRC)
    text = open(p, encoding="utf-8").read()
    assert '"category_00"' in text
    open(p, "w", encoding="utf-8").write(
        text.replace('"category_00"', '"category_01"'))
    return "const"


def c3_extra_statement(ws: str) -> str:
    """Add a statement: the instruction count must be reported as changed."""
    p = os.path.join(ws, REL_SRC)
    text = open(p, encoding="utf-8").read()
    needle = "function set_flag_changed(flag)\n"
    assert needle in text
    open(p, "w", encoding="utf-8").write(
        text.replace(needle, needle + "    local unused = 0\n"))
    return "count"


def c4_wrong_comparison(ws: str) -> str:
    """Change < to <= in p4: the differing prototype must be named."""
    p = os.path.join(ws, REL_SRC)
    text = open(p, encoding="utf-8").read()
    assert "0 <= self.exit_value" in text
    open(p, "w", encoding="utf-8").write(
        text.replace("0 <= self.exit_value", "0 < self.exit_value"))
    return "main.p4"


def c5_post_pass_disabled(ws: str) -> str:
    """Disable the is_vararg post-pass: the file must stop being identical."""
    p = os.path.join(ws, "mods", "mii_customizer", "tools", "lua-src",
                     "build_check.py")
    text = open(p, encoding="utf-8").read()
    assert "    data[off] = original[off]\n" in text
    open(p, "w", encoding="utf-8").write(
        text.replace("    data[off] = original[off]\n", "    pass\n"))
    return "NOT byte-identical"


def c6_post_pass_wrong_offset(ws: str) -> str:
    """Write one byte too low: the guard must reject the derived offset."""
    p = os.path.join(ws, "mods", "mii_customizer", "tools", "lua-src",
                     "build_check.py")
    text = open(p, encoding="utf-8").read()
    assert "    off = main.offset + IS_VARARG_IN_PROTO\n" in text
    open(p, "w", encoding="utf-8").write(
        text.replace("    off = main.offset + IS_VARARG_IN_PROTO\n",
                     "    off = main.offset + IS_VARARG_IN_PROTO + 1\n"))
    return "is_vararg offset"


def c7_wrong_line_placement(ws: str) -> str:
    """Insert a line above a function: its linedefined must be reported."""
    p = os.path.join(ws, REL_SRC)
    text = open(p, encoding="utf-8").read()
    needle = "function get_exit_value()\n"
    assert needle in text
    open(p, "w", encoding="utf-8").write(
        text.replace(needle, "-- an extra comment line\n" + needle))
    return "lines DIFF"


CONTROLS = [
    ("source file deleted", c1_missing_source, "missing input"),
    ("string constant changed", c2_wrong_constant, "const"),
    ("statement added", c3_extra_statement, "count"),
    ("comparison operator changed", c4_wrong_comparison, "main.p4"),
    ("is_vararg post-pass disabled", c5_post_pass_disabled,
     "NOT byte-identical"),
    ("post-pass offset shifted by one", c6_post_pass_wrong_offset,
     "is_vararg offset"),
    ("function moved down one line", c7_wrong_line_placement, "lines DIFF"),
]


def stage(pristine: str, ws: str) -> None:
    """Build a throw-away workspace copy with the mutable parts fresh."""
    for d in TOOL_DIRS:
        shutil.copytree(os.path.join(TOOLS, d),
                        os.path.join(ws, "mods", "mii_customizer", "tools", d))
    lua_src = os.path.join(ws, "mods", "mii_customizer", "tools", "lua-src")
    os.makedirs(lua_src)
    for name in LUA_SRC_NAMES:
        src = os.path.join(LUA_SRC, name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(lua_src, name))
    dest = os.path.join(ws, REL_ORIG)
    os.makedirs(os.path.dirname(dest))
    shutil.copy2(ABS_ORIG, dest)
    os.makedirs(os.path.join(ws, os.path.dirname(REL_OUT)))


def run_check(ws: str) -> "tuple[int, str]":
    proc = subprocess.run(
        [sys.executable,
         os.path.join(ws, "mods", "mii_customizer", "tools", "lua-src",
                      "build_check.py"),
         "edit"],
        capture_output=True, text=True, cwd=ws)
    return proc.returncode, proc.stdout + proc.stderr


def first_verdict(out: str) -> str:
    for line in out.splitlines():
        s = line.strip()
        if s.startswith(("NOT byte-identical", "missing input",
                         "prototypes differing", "FAIL")):
            return s
    return "(no verdict line found)"


def main() -> int:
    luac = os.path.join(TOOLS, "luac53-game", "bin", "luac-game.exe")
    if not os.path.exists(luac):
        print("missing input: %s" % luac)
        return 2

    src_sha_before = sha256(ABS_SRC)
    orig_sha_before = sha256(ABS_ORIG)

    print("baseline: an unmodified copy of the workspace must pass")
    with tempfile.TemporaryDirectory(prefix="negctl-base") as tmp:
        ws = os.path.join(tmp, "ws")
        stage(tmp, ws)
        rc, out = run_check(ws)
        if rc != 0:
            print("BASELINE FAILED (exit %d); the controls would prove nothing"
                  % rc)
            sys.stdout.write(out)
            return 1
        print("  build_check.py edit -> exit 0, output sha256 %s"
              % sha256(os.path.join(ws, REL_OUT)))

    print()
    print("%-38s %-7s %s" % ("control", "caught", "what the check said"))
    results = []
    for name, mutate, expect in CONTROLS:
        with tempfile.TemporaryDirectory(prefix="negctl") as tmp:
            ws = os.path.join(tmp, "ws")
            stage(tmp, ws)
            mutate(ws)
            rc, out = run_check(ws)
        caught = rc != 0 and expect in out
        results.append((name, caught))
        note = "" if caught else "   UNDETECTED: exit %d, wanted %r" % (rc,
                                                                       expect)
        print("%-38s %-7s exit %d  %s%s"
              % (name, "yes" if caught else "NO", rc, first_verdict(out), note))

    print()
    print("reconstructed source unchanged by the controls: %s  sha256 %s"
          % (sha256(ABS_SRC) == src_sha_before, src_sha_before))
    print("original game chunk unchanged by the controls: %s  sha256 %s"
          % (sha256(ABS_ORIG) == orig_sha_before, orig_sha_before))

    bad = [n for n, ok in results if not ok]
    print()
    print("controls caught %d of %d" % (len(results) - len(bad), len(results)))
    if bad:
        print("UNDETECTED: %s" % ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
