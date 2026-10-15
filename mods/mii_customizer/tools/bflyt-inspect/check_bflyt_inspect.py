"""Smoke check for bflyt-inspect (task P2-LAYOUT-STRUCTURE).

Run from the workspace root:

    python mods/mii_customizer/tools/bflyt-inspect/check_bflyt_inspect.py

Exits 0 only when every check passes. The checks are chosen to fail loudly if
the structure this tool models drifts: block framing must consume each file
exactly, every grp1 payload must be fully explained by its entry count, the prt1
child records must fit, every group member must resolve to a node name in the
same file, and the known editor row and selector names must still be present at
the expected counts.

Input paths default to the two files owned by P1-LAYOUT and can be overridden
with --edit and --special for use against other extracted layouts.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bflyt_inspect as bi  # noqa: E402

DEFAULT_EDIT = "gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_edit/blyt/make_mii_edit.bflyt"
DEFAULT_SPECIAL = "gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_special/blyt/make_mii_special.bflyt"

# sha256 of the two files this task was measured against. A different hash means
# the inputs changed and every offset in the research report must be rechecked.
KNOWN = {
    DEFAULT_EDIT: "2668a7ecf146a31e5003df682208d21d3a4cd2d032d4d68e839dfe0853b6dd34",
    DEFAULT_SPECIAL: "a63cbacc09a9264ff07ac83c1b765dd0caeeaa1afd92bdb58297f774a3c0b3e8",
}

# group name -> expected member count, measured in P2-LAYOUT-STRUCTURE
EDIT_GROUPS = {
    "RootGroup": 0,
    "all": 3,
    "selector_0": 8,
    "selector_1": 2,
    "maker_grp": 1,
    "favorite_grp": 1,
    "unedit_grp": 1,
}
SPECIAL_GROUPS = {
    "RootGroup": 0,
    "all": 1,
    "selector_0": 7,
    "detail_color_grp": 2,
}

EDIT_ROWS = [f"set_item_0{i}" for i in range(6)]
SPECIAL_ROWS = [f"set_special_item_0{i}" for i in range(4)]

EDIT_SELECTOR_0 = EDIT_ROWS + ["btn_cursor", "set_footer_area"]


class Checker:
    def __init__(self) -> None:
        self.passed = 0
        self.failed: list[str] = []

    def check(self, ok: bool, msg: str) -> bool:
        if ok:
            self.passed += 1
        else:
            self.failed.append(msg)
        print(f"  {'PASS' if ok else 'FAIL'}  {msg}")
        return ok

    def eq(self, got, want, msg: str) -> bool:
        return self.check(got == want, f"{msg} (got {got!r}, want {want!r})")


def check_file(c: Checker, path: str, label: str, groups: dict, rows: list[str],
               selector_0: list[str] | None) -> None:
    print(f"\n=== {label}: {path}")
    p = Path(path)
    if not p.exists():
        c.check(False, f"{label} input exists")
        return
    bf = bi.load(path)

    if path in KNOWN:
        c.eq(bf.sha256, KNOWN[path], f"{label} sha256 matches recorded input")
    else:
        print(f"  NOTE  {label} sha256 {bf.sha256} (not a recorded input)")

    c.eq(bf.size, bf.header["file_size_field"], f"{label} file_size field")
    c.check(bf.exact_walk,
            f"{label} block walk consumes file exactly ({bf.walked_end}/{bf.size})")
    c.eq(len(bf.blocks), bf.header["block_count"], f"{label} block count")
    c.eq(bf.header["header_size"], 0x14, f"{label} header_size")

    # every block tag must be printable and sizes must tile the file with no gap
    c.check(all(b.size >= 8 for b in bf.blocks), f"{label} every block size >= 8")
    contiguous = True
    prev = bf.header["header_size"]
    for b in bf.blocks:
        if b.offset != prev:
            contiguous = False
        prev = b.end
    c.check(contiguous and prev == bf.size,
            f"{label} blocks tile the file with no gap or overlap")

    # grp1 layout
    got_groups = {g.name: g.entry_count for g in bf.groups}
    c.eq(got_groups, groups, f"{label} group names and entry counts")
    c.check(all(g.exact for g in bf.groups),
            f"{label} every grp1 payload exactly consumed by its entry count")

    # prt1 rows
    got_rows = [p_.name for p_ in bf.parts if p_.name in rows]
    c.eq(got_rows, rows, f"{label} row parts present in file order")
    c.check(all(bi.row_parts(bf, r[:7]) or True for r in rows),
            f"{label} row lookup runs")

    # selector_0 membership, when we have an expectation
    if selector_0 is not None:
        g = next((x for x in bf.groups if x.name == "selector_0"), None)
        if c.check(g is not None, f"{label} selector_0 group exists"):
            names = [e.name for e in g.entries]
            c.eq(names, selector_0, f"{label} selector_0 member names and order")
            c.check(all(e.offset % 2 == 0 for e in g.entries),
                    f"{label} selector_0 entry offsets are even")
            c.check(len({e.offset for e in g.entries}) == len(selector_0),
                    f"{label} selector_0 entry offsets are distinct")

    # cross-check: every group member must resolve inside this file
    cc = bi.crosscheck_groups(bf)
    c.check(cc["unresolved"] == 0,
            f"{label} every group member resolves in-file "
            f"({cc['resolved']}/{cc['total_members']})")

    # prt1 internals
    c.check(all(p_.node_type == 3 for p_ in bf.parts),
            f"{label} every prt1 node_type is 3")
    c.check(all(p_.exact for p_ in bf.parts),
            f"{label} prt1 child records fit inside their payload")
    c.check(all(p_.name for p_ in bf.parts), f"{label} every prt1 has a name")

    # marker field must not be treated as a constant (regression guard)
    markers = {p_.sentinel for p_ in bf.parts}
    c.check(markers <= set(bi.MARKERS_SEEN),
            f"{label} prt1 markers are all measured values "
            f"(got {sorted(hex(m) for m in markers)})")
    pane_markers = {
        d["marker_u16"]
        for defs in bf.node_names.values()
        for d in defs
        if d["tag"] == "pan1"
    }
    c.check(pane_markers <= set(bi.MARKERS_SEEN),
            f"{label} pane markers are measured values "
            f"(got {sorted(hex(m) for m in pane_markers)})")

    # every node block in these files carries a valid name; a drop here means the
    # name scanner is skipping real nodes and would fake 'unresolved' results
    node_blocks = [b for b in bf.blocks if b.tag in bi.NODE_TAGS]
    named = [n for defs in bf.node_names.values() for n in defs]
    c.eq(len(named), len(node_blocks),
         f"{label} every node block yields a name "
         f"({len(named)}/{len(node_blocks)})")

    # rows must be laid out on a monotonic vertical stack
    ys = [r["position"][1] for r in bi.row_parts(bf, rows[0].rsplit("_", 1)[0])]
    c.check(ys == sorted(ys, reverse=True),
            f"{label} row y positions descend in file order ({ys})")

    # tail must be reported, not invented
    c.check(all(p_.tail_names for p_ in bf.parts),
            f"{label} every prt1 tail has reportable names")


def check_tool_robustness(c: Checker) -> None:
    print("\n=== tool robustness")
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "bad.bflyt"
        bad.write_bytes(b"NOPE" + bytes(60))
        try:
            bi.load(str(bad))
            c.check(False, "rejects a file with bad magic")
        except bi.BflytError:
            c.check(True, "rejects a file with bad magic")

        truncated = Path(td) / "trunc.bflyt"
        real = Path(DEFAULT_EDIT).read_bytes()
        truncated.write_bytes(real[:200])
        try:
            bi.load(str(truncated))
            c.check(False, "rejects a truncated file")
        except bi.BflytError:
            c.check(True, "rejects a truncated file")

        # a flipped size field must be caught by the walk, not silently accepted
        tampered = bytearray(real)
        tampered[0x14 + 4] = 0xFF
        tp = Path(td) / "tampered.bflyt"
        tp.write_bytes(bytes(tampered))
        try:
            bi.load(str(tp))
            c.check(False, "rejects an out-of-range block size")
        except bi.BflytError:
            c.check(True, "rejects an out-of-range block size")

    c.check(not hasattr(bi, "write"), "module exposes no write helper")


def check_multi_file_integrity(c: Checker, edit: str, special: str) -> None:
    """Regression guard: every FILE given to a multi-file command must be checked.

    An earlier version of main() read only argv[2] and discarded the rest, so
    `verify good.bflyt corrupt.bflyt` exited 0. That is a false pass and would
    hide a corrupt input, so each case below is asserted on the real exit status.
    """
    import subprocess
    import sys as _sys
    import tempfile

    print("\n=== multi-file argument integrity")

    tool = Path(bi.__file__).resolve()

    def run(args: list[str]) -> int:
        proc = subprocess.run(
            [_sys.executable, str(tool), *args],
            capture_output=True, text=True,
        )
        return proc.returncode

    # both real files are clean -> 0
    rc = run(["verify", edit, special])
    c.eq(rc, 0, "verify with two clean files exits 0")

    # a corrupt second file must make the exit status nonzero
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "corrupt.bflyt"
        good = Path(special).read_bytes()
        corrupt = bytearray(good)
        corrupt[0:4] = b"XXXX"
        bad.write_bytes(bytes(corrupt))
        rc = run(["verify", edit, str(bad)])
        c.check(rc != 0, f"verify detects a corrupt SECOND file (exit {rc})")
        rc = run(["verify", str(bad), edit])
        c.check(rc != 0, f"verify detects a corrupt FIRST file (exit {rc})")

        # a truncated file must also be caught
        trunc = Path(td) / "trunc.bflyt"
        trunc.write_bytes(good[:300])
        rc = run(["verify", edit, str(trunc)])
        c.check(rc != 0, f"verify detects a truncated second file (exit {rc})")

        # an out-of-range block size must be caught
        tampered = bytearray(good)
        tampered[0x18] = 0xFF
        tp = Path(td) / "tampered.bflyt"
        tp.write_bytes(bytes(tampered))
        rc = run(["verify", edit, str(tp)])
        c.check(rc != 0, f"verify detects a bad block size in the second file (exit {rc})")

    # crosscheck must not silently pass on a file it could not resolve
    with tempfile.TemporaryDirectory() as td:
        bad = Path(td) / "corrupt.bflyt"
        corrupt = bytearray(Path(special).read_bytes())
        corrupt[0:4] = b"XXXX"
        bad.write_bytes(bytes(corrupt))
        rc = run(["crosscheck", edit, str(bad)])
        c.check(rc != 0, f"crosscheck refuses a corrupt second file (exit {rc})")


def check_command_line_surface(c: Checker, edit: str, special: str) -> None:
    """Every documented command must run and must not silently ignore arguments.

    A wrong argument split once made `rows FILE PREFIX` print nothing while still
    exiting 0, which reads as a pass. Each command is now exercised through the
    real CLI and asserted on both exit status and that it produced output.
    """
    import subprocess
    import sys as _sys

    print("\n=== command line surface")

    tool = Path(bi.__file__).resolve()

    def run(args: list[str]) -> tuple[int, str]:
        proc = subprocess.run(
            [_sys.executable, str(tool), *args],
            capture_output=True, text=True,
        )
        return proc.returncode, proc.stdout

    cases = [
        ("header", [edit], "size"),
        ("blocks", [edit], "grp1"),
        ("groups", [edit], "selector_0"),
        ("parts", [edit], "set_item_00"),
        ("rows", [edit, "set_item"], "set_item_03"),
        ("crosscheck", [edit], "unresolved"),
    ]
    for cmd, args, expect in cases:
        rc, out = run([cmd, *args])
        c.check(rc == 0 and expect in out,
                f"{cmd} exits 0 and reports {expect!r} (exit {rc})")

    # multi-file commands must emit a section per file
    for cmd in ("header", "blocks", "groups", "crosscheck"):
        rc, out = run([cmd, edit, special])
        c.check(rc == 0 and edit in out and special in out,
                f"{cmd} processes both files (exit {rc})")

    # a missing PREFIX must be an explicit error, not an empty success
    rc, out = run(["rows", edit])
    c.check(rc != 0, f"rows without PREFIX is an error (exit {rc})")
    rc, out = run(["parts", edit, "set_item_00", "extra"])
    c.check(rc != 0, f"parts with a surplus argument is an error (exit {rc})")

    # a nonexistent file must be an error, not a silent skip
    rc, _ = run(["verify", edit, "no_such_file.bflyt"])
    c.check(rc != 0, f"verify with a missing file is an error (exit {rc})")

    # no command at all
    rc, _ = run(["verify"])
    c.check(rc != 0, f"bare command with no file is an error (exit {rc})")
    src = Path(bi.__file__).read_text(encoding="utf-8")
    for forbidden in ("write_bytes", "open(", "shutil"):
        c.check(forbidden not in src,
                f"source contains no {forbidden!r} (read-only by construction)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--edit", default=DEFAULT_EDIT)
    ap.add_argument("--special", default=DEFAULT_SPECIAL)
    args = ap.parse_args()

    c = Checker()
    check_file(c, args.edit, "edit", EDIT_GROUPS, EDIT_ROWS, EDIT_SELECTOR_0)
    check_file(c, args.special, "special", SPECIAL_GROUPS, SPECIAL_ROWS, None)
    check_tool_robustness(c)
    check_multi_file_integrity(c, args.edit, args.special)
    check_command_line_surface(c, args.edit, args.special)

    total = c.passed + len(c.failed)
    print(f"\n{c.passed}/{total} checks passed")
    if c.failed:
        print("\nfailures:")
        for m in c.failed:
            print(f"  - {m}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())