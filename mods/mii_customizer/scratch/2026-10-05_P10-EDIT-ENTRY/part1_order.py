#!/usr/bin/env python3
"""Part 1: where a Favorite press runs in the original and in the 0.3.1 probe.

For both chunks this script
  * annotates every instruction of every prototype with the RK constants it
    references, and
  * enumerates every instruction site that reads `get_decided_button_id`,
    `is_decided` or `press_decide` (and the Favorite / switch_favorite sites),
  * then prints, for the prototype chain `update` -> `update_com_frame` ->
    `update_selector0` -> `update_selector1`, the instructions in file order
    so the order a single frame executes them can be read off directly.

Nothing is executed: this is a reading of the bytes.

Run from the workspace root:

    python mods/mii_customizer/scratch/2026-10-05_P10-EDIT-ENTRY/part1_order.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))            # mods/mii_customizer
WORKSPACE = os.path.dirname(os.path.dirname(MOD))       # workspace root
sys.path.insert(0, os.path.join(MOD, "tools", "lua53-inspect"))
import lua53_inspect as li  # noqa: E402

CHUNKS = {
    "original": os.path.join(WORKSPACE, "gamedata", "mii_customizer", "P1-UI",
                             "ui", "script_patch", "chara_make",
                             "make_mii_edit_actor.lc"),
    "probe-0.3.1": os.path.join(MOD, "builds", "0.3.1-edit-probe",
                                "mii_customizer_probe_edit", "ui",
                                "script_patch", "chara_make",
                                "make_mii_edit_actor.lc"),
}

NEEDLES = ("get_decided_button_id", "is_decided", "press_decide", "is_pressed",
           "is_cancelled", "switch_favorite", "INPUT_FAVORITE",
           "get_selected_button_id", "select_button")

# prototypes we walk in file order: the ones the question is about
WALK = ("main", "main.p4", "main.p5", "main.p6", "main.p9")


def ann(proto, ins) -> str:
    """One annotated instruction line."""
    parts = []
    for which in ("B", "C"):
        raw = ins.b if which == "B" else ins.c
        if raw & li.BITRK:
            idx = raw & ~li.BITRK
            if idx < len(proto.constants):
                parts.append("%s=K%d(%s)" % (which, idx,
                                            proto.constants[idx].text(28)))
    if ins.mode == li._IABX and ins.name == "LOADK":
        parts.append("Bx=K%d(%s)" % (ins.bx,
                                     proto.constants[ins.bx].text(28)
                                     if ins.bx < len(proto.constants)
                                     else "<out of range>"))
    tgt = ins.branch_target()
    if tgt is not None:
        parts.append("-> pc %d" % tgt)
    if ins.is_test:
        parts.append("(test: skip next when %s)" %
                     ("A true" if ins.name in ("TEST", "TESTSET") else "not"))
    return "  pc%-4d %-10s %s%s" % (ins.pc, ins.name, ins.args_text(),
                                    ("   " + " ".join(parts)) if parts else "")


def find_proto(main, path):
    for p in li.walk(main):
        if p.path == path:
            return p
    raise SystemExit("no prototype %s" % path)


def dump(label, path, verbose=True) -> None:
    data = open(path, "rb").read()
    main = li.load_chunk(data)[1]
    print("=" * 74)
    print("%s  %s  %d bytes" % (label, os.path.relpath(path, WORKSPACE),
                                len(data)))
    print("=" * 74)

    print("\n-- sites that reference the decide-related names --")
    for proto in li.walk(main):
        for i, ins in enumerate(proto.code):
            text = ann(proto, ins)
            if any(n in text for n in NEEDLES):
                print("%-9s %s" % (proto.path, text))

    if not verbose:
        return
    for path_ in WALK:
        proto = find_proto(main, path_)
        print("\n-- %s: %d instructions, %d constants --"
              % (path_, len(proto.code), len(proto.constants)))
        for ins in proto.code:
            print(ann(proto, ins))


def symbolic_trace(path) -> None:
    """The order a frame with INPUT_FAVORITE pressed reaches the sites."""
    data = open(path, "rb").read()
    main = li.load_chunk(data)[1]
    upd = find_proto(main, "main.p9")        # update
    s0 = find_proto(main, "main.p4")        # update_selector0
    print("\n-- symbolic order, frame with INPUT_FAVORITE pressed and "
          "selector0 focused on row 1 --")
    print("update (main.p9):")
    print("  1. virtual_input:is_cancel()          read")
    print("  2. elif INPUT_COMMON_BUTTON pressed  not taken")
    print("  3. elif not FROM_AMIIBO              taken (stock screen)")
    print("  4.   INPUT_FAVORITE pressed          taken")
    print("  5.   UiScriptPlayer.invoke(switch_favorite); is_changed = true"
          "   <-- favourite branch runs FIRST")
    print("  6. ComFrameActor.is_decided()        read  <-- the only "
          "is_decided read")
    print("  7.   false -> elseif is_cancelled()  read, false")
    print("  8.   update_com_frame()               returns false")
    print("  9.   update_selector0()               <-- probe block lives here")
    print(" 10.   update_selector1()")
    # where exactly is the probe block inside p4?
    for i, ins in enumerate(s0.code):
        text = ann(s0, ins)
        if "press_decide" in text:
            print("\n  probe press_decide site: %s" % text.strip())
            print("  get_decided_button_id sites in update_selector0:")
            for ins2 in s0.code:
                t2 = ann(s0, ins2)
                if "get_decided_button_id" in t2:
                    print("    %s" % t2.strip())
            break
    else:
        print("\n  no press_decide site in update_selector0 (original chunk)")
        print("  get_decided_button_id sites in update_selector0:")
        for ins2 in s0.code:
            t2 = ann(s0, ins2)
            if "get_decided_button_id" in t2:
                print("    %s" % t2.strip())
    print("  is_decided / is_cancelled reads in update:")
    for ins in upd.code:
        t = ann(upd, ins)
        if "is_decided" in t or "is_cancelled" in t:
            print("    %s" % t.strip())


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    verbose = "--quiet" not in sys.argv
    for label in (args or list(CHUNKS)):
        dump(label, CHUNKS[label], verbose=verbose)
        symbolic_trace(CHUNKS[label])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())