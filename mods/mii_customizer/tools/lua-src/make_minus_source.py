#!/usr/bin/env python3
"""Generate the 0.6.0 edit script (variant `minus`) from the byte-identical source.

Run from the workspace root:

    python mods/mii_customizer/tools/lua-src/make_minus_source.py
    python mods/mii_customizer/tools/lua-src/make_minus_source.py --strip

Output: make_mii_edit_actor_minus.lua = make_mii_edit_actor.lua plus two marked blocks:

* the P13-KEYHELP block in `initialize`, taken unchanged from make_keyhelp_source.py (the
  Favourite tip becomes "<Minus glyph> Advanced Options");
* a MINUS block at the top of `edit_state.update`: when the global `MC_MINUS` is 1 the
  script clears it and, unless FROM_AMIIBO, leaves with exit value 7 exactly as the
  P10-EDIT-ENTRY block did (same four statements). Plugin 0.6.0 raises `MC_MINUS` for one
  Minus press (plugin/src/editor.rs `minus_frame`). Without the plugin the global is nil,
  `nil == 1` is false and the script behaves as the original.

The Favourite-on-Headgear entry block of the `entry` variants is NOT included: Favourite
does only what the game does. `--strip` removes both blocks and must reproduce the base.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_keyhelp_source as kh  # noqa: E402

BASE = os.path.join(HERE, "make_mii_edit_actor.lua")
OUT = os.path.join(HERE, "make_mii_edit_actor_minus.lua")

BEGIN = "    -- >>> MINUS BLOCK START (0.6.0) >>>"
END = "    -- <<< MINUS BLOCK END (0.6.0) <<<"
ANCHOR = (
    "edit_state.update = function(self)\n"
    "    if self.virtual_input:is_cancel() == true then\n"
)
BLOCK = (
    BEGIN + "\n"
    "    if MC_MINUS == 1 then\n"
    "        MC_MINUS = 0\n"
    "        if not FROM_AMIIBO then\n"
    "            self.exit_value = 7\n"
    "            self.selector1_selected_id = -1\n"
    "            UiSoundManager.play_se(UI_SE_ID_DECIDE)\n"
    "            return true\n"
    "        end\n"
    "    end\n"
    + END + "\n"
)


def strip(text):
    for begin, end in ((BEGIN, END), (kh.BEGIN, kh.END)):
        if text.count(begin) != 1 or text.count(end) != 1:
            return None
        start = text.index(begin)
        finish = text.index(end) + len(end)
        if finish < len(text) and text[finish] == "\n":
            finish += 1
        text = text[:start] + text[finish:]
    return text


def main(argv):
    base = open(BASE, encoding="utf-8", newline="").read()
    if argv == ["--strip"]:
        restored = strip(open(OUT, encoding="utf-8", newline="").read())
        if restored != base:
            print("FAIL: stripping both blocks does not reproduce the base source")
            return 1
        print("PASS: --strip reproduces make_mii_edit_actor.lua exactly (%d bytes)" % len(base.encode("utf-8")))
        return 0
    if argv:
        print(__doc__)
        return 2
    if base.count(ANCHOR) != 1 or base.count(kh.ANCHOR) != 1:
        print("anchor count mismatch")
        return 1
    first_line, rest = ANCHOR.split("\n", 1)
    text = base.replace(ANCHOR, first_line + "\n" + BLOCK + rest)
    text = text.replace(kh.ANCHOR, kh.BLOCK + kh.ANCHOR)
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    print("wrote %s (%d lines)" % (os.path.relpath(OUT, os.getcwd()), text.count("\n")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
