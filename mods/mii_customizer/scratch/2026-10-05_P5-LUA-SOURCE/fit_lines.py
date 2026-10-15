#!/usr/bin/env python3
"""Rewrite make_mii_special_actor.lua so every function's linedefined and
lastlinedefined match the original chunk exactly.

Blank lines between functions are free: the original fixes the first and last
line of every prototype, so this shifts each function down (or complains when
a body is too long for its window).

Run from the workspace root. Writes the .lua in place.
"""

from __future__ import annotations

import re
import sys

SRC = ("mods/mii_customizer/tools/lua-src/make_mii_special_actor.lua")

MARKERS = [
    ("-- main.p0 ", 41, 42),
    ("-- main.p1 ", 44, 48),
    ("-- main.p2 ", 53, 90),
    ("-- main.p3 ", 92, 99),
    ("-- main.p4 ", 101, 118),
    ("-- main.p5 ", 120, 123),
    ("-- main.p6 ", 125, 135),
    ("-- main.p7 ", 137, 141),
    ("-- main.p8 ", 143, 190),
    ("-- main.p9 ", 195, 212),
    ("-- main.p10 ", 214, 236),
    ("-- main.p11 ", 238, 248),
    ("-- main.p12 ", 250, 258),
    ("-- main.p13 ", 260, 271),
    ("-- main.p14 ", 276, 296),
    ("-- main.p15 ", 302, 355),
]

OPENERS = ("function", "if", "for", "while", "repeat")
CLOSERS = ("end", "until")


def first_code_line(lines: "list[str]", idx: "int") -> "int":
    """0-based index of the first real statement at or after idx."""
    for i in range(idx, len(lines)):
        s = lines[i].strip()
        if s and not s.startswith("--"):
            return i
    raise RuntimeError("no code after line %d" % (idx + 1))


def block_end(lines: "list[str]", start0: "int") -> "int":
    """0-based index of the line closing the block whose body starts at start0."""
    depth = 0
    for i in range(start0, len(lines)):
        code = lines[i].split("--")[0]
        for tok in re.findall(r"[A-Za-z_]+", code):
            if tok in OPENERS:
                depth += 1
            elif tok in CLOSERS:
                depth -= 1
                if depth == 0:
                    return i
    raise RuntimeError("no matching end found from line %d" % (start0 + 1))


def main() -> int:
    text = open(SRC, encoding="utf-8").read()
    lines = text.split("\n")
    for _ in range(500):
        changed = False
        for marker, want_start, want_end in MARKERS:
            idx = next((i for i, ln in enumerate(lines)
                        if ln.startswith(marker)), None)
            if idx is None:
                print("marker not found: %r" % marker)
                return 2
            body0 = first_code_line(lines, idx)
            got_start, got_end = body0 + 1, block_end(lines, body0) + 1
            if got_start == want_start and got_end == want_end:
                continue
            if got_start != want_start:
                if got_start < want_start:
                    lines[idx:idx] = [""] * (want_start - got_start)
                else:
                    drop = got_start - want_start
                    k = idx
                    while drop and k > 0 and lines[k - 1].strip() == "":
                        del lines[k - 1]
                        k -= 1
                        drop -= 1
                    if drop:
                        print("%-12s want %3d  got %3d  cannot move up"
                              % (marker.strip(), want_start, got_start))
                        return 1
                changed = True
                break
            if got_end > want_end:
                print("%-12s want %3d-%-3d  got %3d-%-3d  body too long"
                      % (marker.strip(), want_start, want_end,
                         got_start, got_end))
                return 1
            if got_end < want_end:
                # blank lines inside the body are free: pad before the final end
                end0 = block_end(lines, body0)
                lines[end0:end0] = [""] * (want_end - got_end)
                changed = True
                break
        if not changed:
            break
    open(SRC, "w", encoding="utf-8").write("\n".join(lines))
    bad = 0
    for marker, want_start, want_end in MARKERS:
        idx = next(i for i, ln in enumerate(lines) if ln.startswith(marker))
        body0 = first_code_line(lines, idx)
        got = (body0 + 1, block_end(lines, body0) + 1)
        flag = "" if got == (want_start, want_end) else "   <-- MISMATCH"
        if flag:
            bad += 1
        print("%-12s want %3d-%-3d  got %3d-%-3d%s"
              % (marker.strip(), want_start, want_end, got[0], got[1], flag))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())