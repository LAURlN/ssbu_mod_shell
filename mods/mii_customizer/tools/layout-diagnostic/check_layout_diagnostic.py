#!/usr/bin/env python3
"""Smoke check for tools/layout-diagnostic.

Runs the builder through its real CLI and then checks the produced files again
with code that is not the builder's own: the two pre-existing tools
(`bflyt-inspect`, `sarc-layout`) plus a small independent reader here.

It covers:

* the builder's happy path, including that the control archive is byte-identical
  to the pinned input and the patched archive differs only inside the two scale
  fields;
* determinism: two `--dry-run` invocations predict the same hashes, and the
  predicted hash equals the file actually written;
* cross-tool agreement: `bflyt-inspect` reads the emitted patched layout and
  reports the scaled row, and `sarc-layout verify` accepts both archives;
* refusals, each of which must exit nonzero, print a reason and write nothing:
  ambiguous part name, unknown part name, wrong archive hash, wrong member hash,
  a member that is not a BFLYT, and factors of 0, -1, inf and 1e39 (zero,
  negative, non-finite and f32-overflowing scale);
* that writing into a supplied input tree is refused, and that the read-only
  input trees are unchanged at the end of the run.

Exit status is 0 only when every check passes.
"""

from __future__ import annotations

import hashlib
import json
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
BUILDER = os.path.join(HERE, "build_diagnostic.py")
SARC_TOOL = os.path.join(os.path.dirname(HERE), "sarc-layout", "sarc_layout.py")
BFLYT_TOOL = os.path.join(os.path.dirname(HERE), "bflyt-inspect", "bflyt_inspect.py")
EVIDENCE = "mods/mii_customizer/evidence/P2-LAYOUT-PATCH"
REPORT = os.path.join(EVIDENCE, "diagnostic.json")

ARCHIVE = "gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc"
EDIT_ARCHIVE = "gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc"
EXTRACTED = "gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_special/blyt/make_mii_special.bflyt"
OUT_DIR = "gamedata/mii_customizer/P2-LAYOUT-PATCH"
CONTROL = os.path.join(OUT_DIR, "control", "layout_original.arc")
PATCHED = os.path.join(OUT_DIR, "patched", "layout_row00_scale075.arc")
PAYLOAD = os.path.join(OUT_DIR, "member", "make_mii_special.scale075.bflyt")

ARCHIVE_SHA256 = "5ba29f4448686d89d478b17b1d5028dda2374c3e1b66cc3ac7c0f7a6abaad945"
MEMBER_SHA256 = "a63cbacc09a9264ff07ac83c1b765dd0caeeaa1afd92bdb58297f774a3c0b3e8"
BFLAN_MEMBER = "anim/make_mii_special_in.bflan"
BFLAN_SHA256 = "d97db701eef02a560bffe3a1adf0291831654b4938116d00a509575e7f8cb563"
SCALE_MEMBER_OFFSETS = (0x10E0, 0x10E4)
SCALE_ARCHIVE_OFFSETS = (0x14E42, 0x14E46)
SARC_DATA_OFFSET = 0x2000
MEMBER_DATA_START = 0x11D60

INPUT_TREES = (
    "gamedata/mii_customizer/P1-UI",
    "gamedata/mii_customizer/P1-LAYOUT",
)

CHECKS: list[tuple[bool, str]] = []


def check(ok: bool, msg: str) -> bool:
    CHECKS.append((bool(ok), msg))
    return bool(ok)


def sha256_file(rel: str) -> str:
    with open(os.path.join(REPO_ROOT, rel), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def run(script: str, args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, os.path.join(REPO_ROOT, script)] + args,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def tree_state(root: str) -> dict:
    state = {}
    base = os.path.join(REPO_ROOT, root)
    for dirpath, _dirs, files in os.walk(base):
        for name in files:
            full = os.path.join(dirpath, name)
            state[os.path.relpath(full, REPO_ROOT)] = os.path.getsize(full)
    return state


def out_tree() -> dict:
    return tree_state(OUT_DIR)


def expect_refusal(label: str, args: list[str], needle: str) -> None:
    before = out_tree()
    proc = run("mods/mii_customizer/tools/layout-diagnostic/build_diagnostic.py", args)
    ok = proc.returncode != 0
    check(ok, "%s exits nonzero (got %d)" % (label, proc.returncode))
    check("refused:" in proc.stderr, "%s prints a refusal reason: %s"
          % (label, proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "<empty>"))
    check(needle in proc.stderr, "%s names the reason %r" % (label, needle))
    check(before == out_tree(), "%s writes no output file" % label)


def main() -> int:
    inputs_before = {tree: tree_state(tree) for tree in INPUT_TREES}

    # 1. happy path -------------------------------------------------------
    proc = run("mods/mii_customizer/tools/layout-diagnostic/build_diagnostic.py", [])
    check(proc.returncode == 0, "builder exits 0 on its documented arguments")
    check("refused:" not in proc.stderr, "builder refuses nothing on the happy path")
    if proc.returncode != 0:
        print(proc.stdout, proc.stderr)

    report_path = os.path.join(REPO_ROOT, REPORT)
    check(os.path.isfile(report_path), "builder writes its JSON report to %s" % REPORT)
    report = {}
    if os.path.isfile(report_path):
        with open(report_path, encoding="utf-8") as fh:
            report = json.load(fh)
    check(report.get("all_checks_pass") is True, "builder reports all of its own checks passing")
    check(len(report.get("verification", [])) >= 15,
          "builder ran %d internal checks" % len(report.get("verification", [])))

    # 2. the files themselves, hashed here and not by the builder ----------
    check(sha256_file(CONTROL) == ARCHIVE_SHA256,
          "control archive is byte-identical to the pinned input (%s)" % sha256_file(CONTROL))
    patched_sha = sha256_file(PATCHED)
    check(patched_sha == report.get("outputs", {}).get("patched_sha256"),
          "patched archive on disk matches the hash in the report (%s)" % patched_sha)
    check(sha256_file(PAYLOAD) != MEMBER_SHA256 and os.path.getsize(os.path.join(REPO_ROOT, PAYLOAD)) == 10408,
          "patched member payload is a same-length 10408-byte file that differs from the original")

    # 3. independent byte comparison of the two archives -------------------
    with open(os.path.join(REPO_ROOT, ARCHIVE), "rb") as fh:
        original = fh.read()
    with open(os.path.join(REPO_ROOT, PATCHED), "rb") as fh:
        patched = fh.read()
    with open(os.path.join(REPO_ROOT, CONTROL), "rb") as fh:
        control = fh.read()
    check(len(original) == len(patched) == len(control), "all three archives are the same length")
    diffs = [i for i in range(len(original)) if original[i] != patched[i]]
    check(diffs == list(SCALE_ARCHIVE_OFFSETS),
          "patched archive differs at exactly %s (got %s)" % (list(SCALE_ARCHIVE_OFFSETS),
                                                              [hex(d) for d in diffs]))
    for off in SCALE_ARCHIVE_OFFSETS:
        member_off = off - SARC_DATA_OFFSET - MEMBER_DATA_START
        inside = any(start <= member_off < start + 4 for start in SCALE_MEMBER_OFFSETS)
        check(inside,
              "archive offset 0x%x maps into a scale field (member offset 0x%x)" % (off, member_off))

    # 4. cross-tool agreement ---------------------------------------------
    for label, archive in (("input", ARCHIVE), ("control", CONTROL), ("patched", PATCHED)):
        proc = run("mods/mii_customizer/tools/sarc-layout/sarc_layout.py",
                   ["verify", archive, "--quiet"])
        check(proc.returncode == 0, "sarc-layout verify accepts the %s archive" % label)
    proc = run("mods/mii_customizer/tools/bflyt-inspect/bflyt_inspect.py",
               ["rows", PAYLOAD, "set_special_item"])
    check(proc.returncode == 0 and "set_special_item_00 @0x00109c" in proc.stdout,
          "bflyt-inspect finds the row at the same offset in the emitted payload")
    inv_path = "mods/mii_customizer/scratch/2026-10-04_P2-LAYOUT-PATCH/inspector_payload.json"
    proc = run("mods/mii_customizer/tools/bflyt-inspect/bflyt_inspect.py",
               ["inventory", PAYLOAD, "--out", inv_path])
    inv = {}
    if os.path.isfile(os.path.join(REPO_ROOT, inv_path)):
        with open(os.path.join(REPO_ROOT, inv_path), encoding="utf-8") as fh:
            inv = json.load(fh)
    scaled = [p for p in inv.get("parts", []) if p["name"] == "set_special_item_00"]
    check(len(scaled) == 1 and scaled[0]["scale"] == [0.75, 0.75],
          "bflyt-inspect reads scale [0.75, 0.75] on the patched payload (got %s)"
          % (scaled[0]["scale"] if scaled else "no such part"))
    original_inv = "mods/mii_customizer/scratch/2026-10-04_P2-LAYOUT-PATCH/inspector_original.json"
    run("mods/mii_customizer/tools/bflyt-inspect/bflyt_inspect.py",
        ["inventory", EXTRACTED, "--out", original_inv])
    base_inv = {}
    if os.path.isfile(os.path.join(REPO_ROOT, original_inv)):
        with open(os.path.join(REPO_ROOT, original_inv), encoding="utf-8") as fh:
            base_inv = json.load(fh)
    base_parts = [p for p in base_inv.get("parts", []) if p["name"] == "set_special_item_00"]
    check(bool(base_parts) and base_parts[0]["scale"] == [1.0, 1.0],
          "the same inspector reports scale [1.0, 1.0] on the original layout")
    for field in ("position", "extent", "child_count", "name", "size"):
        check(bool(base_parts) and scaled and base_parts[0][field] == scaled[0][field],
              "bflyt-inspect shows %s unchanged by the patch" % field)
    proc = run("mods/mii_customizer/tools/bflyt-inspect/bflyt_inspect.py",
               ["verify", EXTRACTED, PAYLOAD])
    check(proc.returncode == 0, "bflyt-inspect verifies the original and patched layouts")

    # 5. determinism ------------------------------------------------------
    dry1 = run("mods/mii_customizer/tools/layout-diagnostic/build_diagnostic.py", ["--dry-run"])
    dry2 = run("mods/mii_customizer/tools/layout-diagnostic/build_diagnostic.py", ["--dry-run"])
    check(dry1.returncode == 0 and dry2.returncode == 0, "two --dry-run invocations both exit 0")
    check(dry1.stdout == dry2.stdout, "two --dry-run invocations produce identical reports")
    check(ARCHIVE_SHA256 in dry1.stdout and patched_sha in dry1.stdout,
          "the dry run predicts the same hashes that were written")

    # 6. refusals ---------------------------------------------------------
    expect_refusal("ambiguous part name", ["--part", "set_special_item"],
                   "finds 4 prt1 parts matching")
    expect_refusal("unknown part name", ["--part", "set_special_item_04"],
                   "finds 0 prt1 parts matching")
    expect_refusal("wrong archive hash", ["--expect-archive-sha256", "0" * 64], "unexpected archive hash")
    expect_refusal("wrong archive", ["--archive", EDIT_ARCHIVE], "unexpected archive hash")
    expect_refusal("wrong member hash", ["--expect-member-sha256", "0" * 64], "unexpected member hash")
    expect_refusal("member that is not a BFLYT",
                   ["--member", BFLAN_MEMBER, "--expect-member-sha256", BFLAN_SHA256],
                   "not FLYT")
    expect_refusal("zero scale", ["--factor", "0"], "not positive")
    expect_refusal("negative scale", ["--factor", "-1"], "not positive")
    expect_refusal("non-finite scale", ["--factor", "inf"], "not finite")
    expect_refusal("scale that overflows f32", ["--factor", "1e39"], "does not fit in an f32")
    expect_refusal("output inside a read-only input tree",
                   ["--out-dir", "gamedata/mii_customizer/P1-LAYOUT/unpacked/p2"], "read-only")
    expect_refusal("output equal to the input archive",
                   ["--out-dir", "gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special"],
                   "read-only")

    # 7. inputs untouched -------------------------------------------------
    for tree in INPUT_TREES:
        check(inputs_before[tree] == tree_state(tree),
              "%s is unchanged (file set and sizes)" % tree)
    check(sha256_file(ARCHIVE) == ARCHIVE_SHA256, "input archive still hashes to its pinned value")
    check(sha256_file(EXTRACTED) == MEMBER_SHA256, "input extracted layout still hashes to its pinned value")
    check(os.path.isfile(os.path.join(REPO_ROOT, "gamedata/mii_customizer/P2-LAYOUT-PATCH",
                                      "patched", "layout_row00_scale075.arc")),
          "the patched diagnostic archive is still in place after the refusals")

    failed = [msg for ok, msg in CHECKS if not ok]
    for ok, msg in CHECKS:
        print("  %-4s %s" % ("ok" if ok else "FAIL", msg))
    print("\n%d/%d checks passed" % (len(CHECKS) - len(failed), len(CHECKS)))

    result = {
        "task": "P2-LAYOUT-PATCH",
        "checks": [{"pass": ok, "check": msg} for ok, msg in CHECKS],
        "total": len(CHECKS),
        "failed": len(failed),
        "all_pass": not failed,
        "patched_archive_sha256": patched_sha,
        "control_archive_sha256": sha256_file(CONTROL),
        "differing_archive_byte_offsets": ["0x%x" % d for d in diffs],
    }
    out = os.path.join(REPO_ROOT, EVIDENCE, "checks.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
        fh.write("\n")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())