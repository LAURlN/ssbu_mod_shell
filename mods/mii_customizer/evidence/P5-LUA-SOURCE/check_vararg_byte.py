#!/usr/bin/env python3
"""Evidence for P5-LUA-SOURCE: the one byte no Lua 5.3.6 source can reproduce.

The reconstructed source compiles to a chunk that is byte-identical to
``make_mii_special_actor.lc`` in every prototype, but differs in exactly one
byte: the ``is_vararg`` byte of the **main** prototype, at file offset 0x28.

Stock Lua 5.3.6 hard-codes that byte. ``lparser.c`` ``mainfunc()`` sets
``fs->f->is_vararg = 1`` unconditionally for the main function, so every chunk
produced by this compiler has main ``is_vararg == 1``. The three SSBU editor
chunks all have main ``is_vararg == 2``. No choice of Lua source changes it:
``is_vararg`` is a property of the *function*, and the main chunk is always
vararg regardless of whether the source mentions ``...``.

This is byte evidence about the chunk only (tier B). It says the game's
compiler differs from stock 5.3.6 in this one field. It says nothing about
whether the game would load either chunk, and it does not identify which
toolchain produced the original.

Run from the workspace root. Exit 0 only if every claim below holds.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys

sys.path.insert(0, "mods/mii_customizer/tools/lua53-inspect")
import lua53_inspect as li  # noqa: E402

ORIGINAL = ("gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/"
            "make_mii_special_actor.lc")
SIBLINGS = [
    "gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_edit_actor.lc",
    "gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc",
]
MINE = "gamedata/mii_customizer/P5-LUA-SOURCE/make_mii_special_actor.lc"
LUAC = os.path.join("mods", "mii_customizer", "tools", "luac53-game", "bin",
                    "luac-game.exe")
MAIN_VA_OFFSET = 0x28
PROBE_DIR = ("mods/mii_customizer/scratch/2026-10-05_P5-LUA-SOURCE/vararg")

failures = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print("%-5s %s%s" % ("ok" if ok else "FAIL", label,
                         (" -- " + detail) if detail else ""))
    if not ok:
        failures.append(label)


def sha256(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def compile_probe(source: str, name: str):
    """Compile a one-line source and report the main proto's is_vararg."""
    os.makedirs(PROBE_DIR, exist_ok=True)
    src = os.path.join(PROBE_DIR, name + ".lua")
    out = os.path.join(PROBE_DIR, name + ".lc")
    open(src, "w", encoding="utf-8").write(source)
    r = subprocess.run([os.path.join(".", LUAC), "-s", "-o", out, src],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    _, main = li.load_chunk(open(out, "rb").read())
    return main.is_vararg


def main() -> int:
    a = open(ORIGINAL, "rb").read()
    b = open(MINE, "rb").read()

    # 1. inputs are the expected ones
    check(len(a) == 7799, "original is 7799 bytes", "%d" % len(a))
    check(sha256(ORIGINAL) ==
          "ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d",
          "original sha256 matches the task input")

    # 2. exactly one byte differs, and it is main's is_vararg
    diff = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    check(len(a) == len(b), "same length", "%d vs %d" % (len(a), len(b)))
    check(diff == [MAIN_VA_OFFSET], "exactly one differing byte",
          "offsets=%s" % [hex(x) for x in diff])
    check(a[MAIN_VA_OFFSET] == 2 and b[MAIN_VA_OFFSET] == 1,
          "that byte is main is_vararg: original 2, mine 1",
          "orig=%d mine=%d" % (a[MAIN_VA_OFFSET], b[MAIN_VA_OFFSET]))

    # 3. the byte really is at that offset, read back through the parser
    _, am = li.load_chunk(a)
    _, bm = li.load_chunk(b)
    check(am.offset == MAIN_VA_OFFSET - 10,
          "main prototype starts at 0x1e, so +10 is is_vararg",
          "main.offset=0x%x" % am.offset)
    check(am.is_vararg == 2 and bm.is_vararg == 1,
          "parser agrees: original main is_vararg 2, mine 1")

    # 4. every prototype is otherwise identical
    ap = {p.path: p for p in li.walk(am)}
    bp = {p.path: p for p in li.walk(bm)}
    check(set(ap) == set(bp), "same set of prototypes",
          "%d vs %d" % (len(ap), len(bp)))
    code_ok = all([i.word for i in ap[k].code] == [i.word for i in bp[k].code]
                  for k in ap)
    check(code_ok, "every prototype's instruction words are identical")
    const_ok = all(len(ap[k].constants) == len(bp[k].constants)
                   and [(c.tag, c.value) for c in ap[k].constants]
                   == [(c.tag, c.value) for c in bp[k].constants]
                   for k in ap)
    check(const_ok, "every prototype's constant table is identical")
    # main's is_vararg is the one byte that is known to differ, so it is
    # compared separately and excluded here
    meta_ok = all(
        (ap[k].numparams, ap[k].maxstacksize, ap[k].upvalues,
         ap[k].linedefined, ap[k].lastlinedefined,
         ap[k].is_stripped)
        == (bp[k].numparams, bp[k].maxstacksize, bp[k].upvalues,
            bp[k].linedefined, bp[k].lastlinedefined,
            bp[k].is_stripped)
        for k in ap)
    check(meta_ok,
          "numparams, maxstacksize, upvalues, linedefined/lastlinedefined "
          "and stripped-ness all match per prototype")
    child_va_ok = all(ap[k].is_vararg == bp[k].is_vararg
                      for k in ap if k != "main")
    check(child_va_ok, "every non-main prototype's is_vararg matches")

    # 5. the differing byte is not source-controlled: stock 5.3.6 always
    #    writes 1 for main, whatever the source says.
    probes = {
        "empty":            "",
        "one local":        "local x = 1\n",
        "uses ...":         "local x = ...\n",
        "vararg function":  "local function v(...) return ... end\nreturn v(1)\n",
        "prints ...":       "print(...)\n",
        "table from ...":   "local t = {...}\n",
    }
    got = {}
    for name, src in probes.items():
        got[name] = compile_probe(src, name.replace(" ", "_"))
        check(got[name] == 1,
              "stock 5.3.6 main is_vararg == 1 for source %r" % name,
              "got %r" % (got[name],))
    check(all(v == 1 for v in got.values()),
          "no probed source produces main is_vararg 2")

    # 6. all three game chunks agree on 2, so this is a property of the
    #    game's compiler rather than of this one script.
    for p in [ORIGINAL] + SIBLINGS:
        _, m = li.load_chunk(open(p, "rb").read())
        check(m.is_vararg == 2,
              "main is_vararg == 2 in %s" % os.path.basename(p),
              "got %d" % m.is_vararg)

    print()
    if failures:
        print("%d FAILED: %s" % (len(failures), "; ".join(failures)))
        return 1
    print("all checks passed")
    print()
    print("CONCLUSION (tier B, bytes only): the reconstructed source reproduces")
    print("the original chunk in all 17 prototypes and differs in exactly one")
    print("byte, main is_vararg at 0x28. Stock Lua 5.3.6 writes 1 there for")
    print("every source; the SSBU chunks all carry 2. Byte identity with the")
    print("game's own compiler is therefore unreachable from Lua source alone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())