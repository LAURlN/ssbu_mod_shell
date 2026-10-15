#!/usr/bin/env python3
"""Generate the P13-KEYHELP edit script from its byte-identical source.

Run from the workspace root:

    python mods/mii_customizer/tools/lua-src/make_keyhelp_source.py
    python mods/mii_customizer/tools/lua-src/make_keyhelp_source.py --strip

The generated variant adds one marked initialize block. For ordinary Mii
edits, it replaces the existing keyhelp icon message with the game's existing
Minus glyph label and replaces the help word with the literal
"Advanced Options". Amiibo edits keep the original hidden keyhelp untouched.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "make_mii_edit_actor.lua")
OUT = os.path.join(HERE, "make_mii_edit_actor_keyhelp.lua")

BEGIN = "    -- >>> KEYHELP BLOCK START (P13-KEYHELP) >>>"
END = "    -- <<< KEYHELP BLOCK END (P13-KEYHELP) <<<"

ANCHOR = (
    '    if FROM_AMIIBO then\n'
    '        edit_state.layout_view:get_parts("btn_other_try"):set_visible(false)\n'
)

BLOCK = (
    BEGIN + "\n"
    "    if not FROM_AMIIBO then\n"
    '        local keyhelp = edit_state.layout_view:get_parts("set_btn_keyhelp_00")\n'
    '        keyhelp:get_pane("set_txt_icon"):set_text_message("cmn_button_nx_minus")\n'
    '        keyhelp:get_pane("set_txt_help"):set_text_string("Advanced Options")\n'
    "    end\n"
    + END + "\n"
)


def strip(text: str) -> str | None:
    if text.count(BEGIN) != 1 or text.count(END) != 1:
        print("generated source must contain exactly one start and end marker")
        return None
    start = text.index(BEGIN)
    finish = text.index(END) + len(END)
    if finish < start:
        print("end marker precedes start marker")
        return None
    if finish < len(text) and text[finish] == "\n":
        finish += 1
    return text[:start] + text[finish:]


def main(argv: list[str]) -> int:
    if not os.path.isfile(BASE):
        print("missing byte-identical base source: %s" % BASE)
        return 2
    base = open(BASE, encoding="utf-8", newline="").read()

    if argv == ["--strip"]:
        if not os.path.isfile(OUT):
            print("missing generated source: %s (run without --strip first)" % OUT)
            return 2
        generated = open(OUT, encoding="utf-8", newline="").read()
        restored = strip(generated)
        if restored is None:
            return 1
        if restored != base:
            print("FAIL: stripping the keyhelp block does not reproduce the base source")
            return 1
        print("PASS: --strip reproduces %s exactly (%d bytes)" %
              (os.path.basename(BASE), len(base.encode("utf-8"))))
        return 0

    if argv:
        print(__doc__)
        return 2
    if BEGIN in base or END in base:
        print("base source already contains a P13-KEYHELP marker; refusing to generate")
        return 1
    if base.count(ANCHOR) != 1:
        print("initialize anchor found %d times, expected 1" % base.count(ANCHOR))
        return 1

    generated = base.replace(ANCHOR, BLOCK + ANCHOR)
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(generated)
    print("wrote %s (%d lines)" %
          (os.path.relpath(OUT, os.getcwd()), generated.count("\n")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
