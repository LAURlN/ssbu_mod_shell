#!/usr/bin/env python3
"""Generate the P9 Part 2 probe source from the byte-identical source.

Run from the workspace root:

    python mods/mii_customizer/tools/lua-src/make_probe_source.py
    python mods/mii_customizer/tools/lua-src/make_probe_source.py --strip

The first form writes ``tools/lua-src/make_mii_edit_actor_probe.lua``: a copy
of ``make_mii_edit_actor.lua`` with one clearly marked block added.  The base
source is never edited, so ``build_check.py`` keeps proving the pristine
reconstruction while the probe is generated from exactly that text.

``--strip`` takes the two marked regions back out again and asserts that the
result is byte-for-byte the base source.  That is the check that the probe is
purely additive: whatever the probe does, the rest of the file is the shipped
logic unchanged.

What the probe does
-------------------
``MC_PROBE_EXIT_VALUE`` at the top of the file is the single switch.  Set it to
a row id (1 = the first row, Headgear) and, while ``selector0`` has focus and
its selected button is that row, one extra press of ``INPUT_FAVORITE`` makes
the selector decide that row.  Everything after the probe block is untouched
original code, so the decided state is consumed by the same
``get_decided_button_id()`` branch, the same ``exit_value`` assignment and the
same ``return true`` that a real decide takes.

Setting it to ``0`` turns the probe off, because the block's first test,
``MC_PROBE_EXIT_VALUE ~= 0``, is then false on every frame and the rest of the
block is never reached.  Note that this is a *runtime* disable, not a
compile-time one: ``MC_PROBE_EXIT_VALUE`` is a local, so the compiler cannot
fold the test and the block's instructions stay in the chunk either way
(measured: 10739 bytes and 111 instructions in ``main.p4`` with the probe set
to 1 *and* with it set to 0).  For a chunk with no probe code in it at all,
delete the marked block; ``build_check.py`` then reproduces the original
byte-for-byte again.

Why INPUT_FAVORITE
------------------
The probe may only use an input constant and an input object/method that the
chunk already reads.  This chunk reads exactly six input constants, all through
``self.virtual_input``, and calls ``is_pressed``, ``is_pressing``,
``is_released`` and ``is_cancel`` on it.  Of the six, only ``INPUT_FAVORITE``
is not already bound to another job on the edit screen:

* ``INPUT_COMMON_BUTTON`` is consumed at the top of ``update`` by
  ``ComFrameActor.press_decide()``; using it as the probe button would just be
  the normal decide, not an extra one.
* ``INPUT_BUTTON_LEFT`` / ``RIGHT`` / ``UP`` / ``DOWN`` are the cursor keys and
  are read in three different handlers, each with its own ``is_moved``
  bookkeeping.  Stealing one of those would fight that state machine.

``INPUT_FAVORITE`` is read exactly once, in ``update``, and only under
``not FROM_AMIIBO``; on the stock edit screen it drives the
``switch_favorite`` invoke.  The probe checks the probe conditions first, so on
a row-1 press it wins over that branch for that frame.
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(HERE, "make_mii_edit_actor.lua")
OUT = os.path.join(HERE, "make_mii_edit_actor_probe.lua")

PROBE_VALUE = "1"

# Markers used both to insert the probe and, in --strip mode, to take it back
# out again.  --strip must reproduce the base source exactly, which is how this
# script shows the probe is purely additive.
HEADER_BEGIN = "-- >>> PROBE HEADER START (P9 part 2) >>>"
HEADER_END = "-- <<< PROBE HEADER END (P9 part 2) <<<"
BLOCK_BEGIN = "    -- >>> PROBE BLOCK START (P9 part 2) >>>"
BLOCK_END = "    -- <<< PROBE BLOCK END (P9 part 2) <<<"

HEADER_MARK = "local edit_state = {}\n"
HEADER_NEW = """-- >>> PROBE HEADER START (P9 part 2) >>>\n-- ===================================================================
-- PROBE (P9-EDIT-SOURCE part 2).  Delete this whole marked region, or set
-- MC_PROBE_EXIT_VALUE to 0, to get the shipped behaviour back.
--
-- MC_PROBE_EXIT_VALUE is the selector0 row the probe decides for, and it is
-- also the exit_value that row produces.  1 is the first row (Headgear).
--
-- Setting it to 0 turns the probe off at run time: the block's first test,
-- MC_PROBE_EXIT_VALUE ~= 0, is then false on every frame, so nothing after
-- it runs.  The block's instructions stay in the chunk either way, because
-- the value is a local and the compiler cannot fold the test.  For a chunk
-- with no probe code in it at all, delete the region; build_check.py then
-- reproduces the original byte for byte again.
-- ===================================================================
local MC_PROBE_EXIT_VALUE = %s
-- <<< PROBE HEADER END (P9 part 2) <<<

""" % PROBE_VALUE

# The anchor is the first line of the decided branch in update_selector0.  The
# probe goes immediately before it so that whatever the press does, the
# assignment and the return below are the original ones.
ANCHOR = "    self.exit_value = self.selector0:get_decided_button_id()\n"
PROBE = ("""    -- >>> PROBE BLOCK START (P9 part 2) >>>
    -- While selector0 has focus and its selected button is the probe row, one
    -- press of INPUT_FAVORITE selects that row again and pushes the decide
    -- through, so the lines below see exactly the state a real decide on that
    -- row would leave: the same exit_value, the same selector1_selected_id
    -- reset, the same return value, and the decide sound the selector widget
    -- plays on its own decide path.
    --
    -- MC_PROBE_EXIT_VALUE == 0 makes the first test false on every frame, so
    -- the rest of the block is never reached.  The instructions stay in the
    -- chunk because the value is a local the compiler cannot fold.
    --
    -- INPUT_FAVORITE and self.virtual_input:is_pressed() are both already used
    -- by this chunk; selector0:select_button(), selector0:get_selected_button_id()
    -- and ComFrameActor.press_decide() are called on the code paths this block
    -- sits in front of.  No new host API is introduced.
    if MC_PROBE_EXIT_VALUE ~= 0
        and self.selector0:get_selected_button_id() == MC_PROBE_EXIT_VALUE
        and self.virtual_input:is_pressed(INPUT_FAVORITE) == true then
        self.selector0:select_button(MC_PROBE_EXIT_VALUE)
        ComFrameActor.press_decide()
    end
    -- <<< PROBE BLOCK END (P9 part 2) <<<

""")


def strip(text: str) -> "str | None":
    """Remove both marked regions, or return None if the markers are wrong."""
    for begin, end, what in ((HEADER_BEGIN, HEADER_END, "header"),
                             (BLOCK_BEGIN, BLOCK_END, "block")):
        if text.count(begin) != 1 or text.count(end) != 1:
            print("cannot strip the probe %s region: %d start markers, %d end "
                  "markers" % (what, text.count(begin), text.count(end)))
            return None
        i = text.index(begin)
        j = text.index(end) + len(end)
        if j < i:
            print("cannot strip the probe %s region: end marker precedes the "
                  "start marker" % what)
            return None
        # also drop the blank line that separated the region from the code
        while j < len(text) and text[j] == "\n":
            j += 1
        text = text[:i] + text[j:]
    return text


def main(argv: "list[str]") -> int:
    if not os.path.isfile(BASE):
        print("missing base source: %s" % BASE)
        return 2
    if not os.path.isfile(OUT):
        print("missing probe source: %s (run without --strip first)" % OUT)
        return 2
    text = open(BASE, encoding="utf-8", newline="").read()

    if "--strip" in argv:
        probe = open(OUT, encoding="utf-8", newline="").read()
        stripped = strip(probe)
        if stripped is None:
            return 1
        if stripped != text:
            print("FAIL: stripping the probe does not reproduce the base "
                  "source, so the probe is not purely additive")
            return 1
        print("PASS: stripping the two marked regions from %s reproduces %s "
              "exactly (%d bytes)" % (os.path.basename(OUT),
                                      os.path.basename(BASE), len(text)))
        return 0

    if argv:
        print(__doc__)
        return 2
    if text.count(HEADER_MARK) != 1:
        print("anchor %r found %d times, expected 1"
              % (HEADER_MARK, text.count(HEADER_MARK)))
        return 1
    if text.count(ANCHOR) != 1:
        print("anchor %r found %d times, expected 1"
              % (ANCHOR, text.count(ANCHOR)))
        return 1
    if "MC_PROBE_EXIT_VALUE" in text:
        print("the base source already mentions MC_PROBE_EXIT_VALUE; refusing "
              "to add a second probe")
        return 1

    out = text.replace(HEADER_MARK, HEADER_NEW + HEADER_MARK)
    out = out.replace(ANCHOR, PROBE + ANCHOR)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(out)
    print("wrote %s (%d lines, from %s)"
          % (os.path.relpath(OUT, os.getcwd()), out.count("\n"),
             os.path.basename(BASE)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
