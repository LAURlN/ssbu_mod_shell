#!/usr/bin/env python3
"""Generate the P10-EDIT-ENTRY entry sources from the byte-identical source.

Run from the workspace root:

    python mods/mii_customizer/tools/lua-src/make_entry_source.py
    python mods/mii_customizer/tools/lua-src/make_entry_source.py --strip

The first form writes two generated files next to the byte-identical
reconstruction:

* ``make_mii_edit_actor_entry.lua`` - the reconstruction plus one marked entry
  block in ``update`` (variant ``entry``);
* ``make_mii_edit_actor_entry_marker.lua`` - the same plus a second marked
  boot-marker block in ``initialize`` (variant ``entry-marker``).

The base source is never edited, so ``build_check.py`` keeps proving the
pristine reconstruction while both variants are generated from exactly that
text.  ``--strip`` removes the marked regions from both generated files and
asserts that each result is byte-for-byte the base source: that is the check
that both variants are purely additive.

What the entry block does
-------------------------
On a frame where ``INPUT_FAVORITE`` is pressed (that test already sits under
``elseif not FROM_AMIIBO``), if selector0 has focus and its selected button is
row 1 (Headgear), the script sets ``self.exit_value = 7``,
``self.selector1_selected_id = -1``, plays ``UI_SE_ID_DECIDE`` and returns
true, so ``main()`` leaves exactly as it does for a decided row.  Any other
row - or selector0 not focused - falls through to the original
``switch_favorite`` invocation unchanged.  Nothing else in the file moves;
only line-number metadata of prototypes defined after ``update`` shifts,
because lines were inserted above them (recorded in MANIFEST.json).

Only names the shipped chunk already uses appear in the block:
``INPUT_FAVORITE``, ``virtual_input:is_pressed``, ``selector0:has_focus``,
``selector0:get_selected_button_id``, the ``exit_value`` and
``selector1_selected_id`` fields, ``UiSoundManager.play_se`` and
``UI_SE_ID_DECIDE``.  The numbers 1 (the row id, the chunk's own row
numbering) and 7 (the exit value this task publishes) are the only numeric
constants added.  No new ``INPUT_*`` name is introduced.

What the boot-marker block does
-------------------------------
Unconditionally hides the ``btn_other_try`` parts when the script initialises
- the same statement the shipped ``FROM_AMIIBO`` branch runs - so a console
boot can tell the marker chunk from the stock one without pressing anything:
with the marker chunk loaded, the Try button is missing on the edit screen
from the moment it appears.  Diagnostic only; the entry behaviour is the same
as the ``entry`` variant.

Both files are generated.  Do not edit them; edit this script and regenerate.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "make_mii_edit_actor.lua")
OUT_ENTRY = os.path.join(HERE, "make_mii_edit_actor_entry.lua")
OUT_MARKER = os.path.join(HERE, "make_mii_edit_actor_entry_marker.lua")

# Markers used both to insert the blocks and, in --strip mode, to take them
# back out again.  --strip must reproduce the base source exactly, which is
# how this script shows both variants are purely additive.
ENTRY_BEGIN = "            -- >>> ENTRY BLOCK START (P10-EDIT-ENTRY) >>>"
ENTRY_END = "            -- <<< ENTRY BLOCK END (P10-EDIT-ENTRY) <<<"
MARKER_BEGIN = "    -- >>> ENTRY-MARKER BLOCK START (P10-EDIT-ENTRY) >>>"
MARKER_END = "    -- <<< ENTRY-MARKER BLOCK END (P10-EDIT-ENTRY) <<<"

# The whole favourite branch as it ships (make_mii_edit_actor.lua lines
# 366-369): the entry block is inserted between the `then` and the invoke, so
# every other line of the branch is reused verbatim.
FAVORITE_ANCHOR = (
    '        if self.virtual_input:is_pressed(INPUT_FAVORITE) == true then\n'
    '            UiScriptPlayer.invoke("switch_favorite")\n'
    '            self.is_changed = true\n'
    '        end\n')

ENTRY_BLOCK = (
    '        if self.virtual_input:is_pressed(INPUT_FAVORITE) == true then\n'
    + ENTRY_BEGIN + "\n"
    "            if self.selector0:has_focus() == true\n"
    "                and self.selector0:get_selected_button_id() == 1 then\n"
    "                self.exit_value = 7\n"
    "                self.selector1_selected_id = -1\n"
    "                UiSoundManager.play_se(UI_SE_ID_DECIDE)\n"
    "                return true\n"
    "            end\n"
    + ENTRY_END + "\n"
    '            UiScriptPlayer.invoke("switch_favorite")\n'
    '            self.is_changed = true\n'
    '        end\n')

# The tail of the FROM_AMIIBO block in initialize (lines 542-543); the marker
# statement is the same parts lookup + set_visible(false) that branch runs,
# placed after its `end` so it is unconditional.  The parts exist at that
# point because the shipped branch does the same lookup there.
MARKER_ANCHOR = (
    '        edit_state.layout_view:get_parts("set_btn_keyhelp_00")'
    ':set_visible(false)\n'
    '    end\n')

MARKER_BLOCK = (
    MARKER_BEGIN + "\n"
    + '    edit_state.layout_view:get_parts("btn_other_try")'
    ':set_visible(false)\n'
    + MARKER_END + "\n")


def strip(text: str, regions: "list[tuple[str, str, str]]") -> "str | None":
    """Remove each marked region, or return None if the markers are wrong."""
    for begin, end, what in regions:
        n_begin, n_end = text.count(begin), text.count(end)
        if n_begin > 1 or n_end > 1:
            print("cannot strip the %s region: %d start markers, %d end "
                  "markers" % (what, n_begin, n_end))
            return None
        if n_begin != n_end:
            print("cannot strip the %s region: %d start markers, %d end "
                  "markers" % (what, n_begin, n_end))
            return None
        if n_begin == 0:
            continue
        i = text.index(begin)
        j = text.index(end) + len(end)
        if j < i:
            print("cannot strip the %s region: end marker precedes the "
                  "start marker" % what)
            return None
        # also drop the newline that ended the region's last line
        if j < len(text) and text[j] == "\n":
            j += 1
        text = text[:i] + text[j:]
    return text


def make_entry(text: str) -> "str | None":
    if text.count(FAVORITE_ANCHOR) != 1:
        print("entry anchor found %d times, expected 1"
              % text.count(FAVORITE_ANCHOR))
        return None
    return text.replace(FAVORITE_ANCHOR, ENTRY_BLOCK)


def make_marker(text: str) -> "str | None":
    if text.count(MARKER_ANCHOR) != 1:
        print("marker anchor found %d times, expected 1"
              % text.count(MARKER_ANCHOR))
        return None
    return text.replace(MARKER_ANCHOR, MARKER_ANCHOR + MARKER_BLOCK)


def main(argv: "list[str]") -> int:
    if not os.path.isfile(BASE):
        print("missing base source: %s" % BASE)
        return 2
    base = open(BASE, encoding="utf-8", newline="").read()

    if "--strip" in argv:
        rc = 0
        for out, regions, what in (
                (OUT_ENTRY,
                 [(ENTRY_BEGIN, ENTRY_END, "entry")],
                 "entry"),
                (OUT_MARKER,
                 [(ENTRY_BEGIN, ENTRY_END, "entry"),
                  (MARKER_BEGIN, MARKER_END, "marker")],
                 "entry-marker")):
            if not os.path.isfile(out):
                print("missing generated source: %s (run without --strip "
                      "first)" % out)
                return 2
            text = open(out, encoding="utf-8", newline="").read()
            stripped = strip(text, regions)
            if stripped is None:
                rc = 1
                continue
            if stripped != base:
                print("FAIL: stripping the %s regions from %s does not "
                      "reproduce the base source, so the variant is not "
                      "purely additive" % (what, os.path.basename(out)))
                rc = 1
                continue
            print("PASS: stripping the %s regions from %s reproduces %s "
                  "exactly (%d bytes)"
                  % (what, os.path.basename(out), os.path.basename(BASE),
                     len(base)))
        return rc

    if argv:
        print(__doc__)
        return 2
    for marker in (ENTRY_BEGIN, ENTRY_END, MARKER_BEGIN, MARKER_END):
        if marker in base:
            print("the base source already contains marker %r; refusing to "
                  "generate on top of it" % marker)
            return 1

    entry = make_entry(base)
    if entry is None:
        return 1
    marker = make_marker(entry)
    if marker is None:
        return 1

    with open(OUT_ENTRY, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(entry)
    print("wrote %s (%d lines, from %s)"
          % (os.path.relpath(OUT_ENTRY, os.getcwd()), entry.count("\n"),
             os.path.basename(BASE)))
    with open(OUT_MARKER, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(marker)
    print("wrote %s (%d lines, from %s + marker block)"
          % (os.path.relpath(OUT_MARKER, os.getcwd()), marker.count("\n"),
             os.path.basename(OUT_ENTRY)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
