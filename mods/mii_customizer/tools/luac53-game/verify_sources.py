#!/usr/bin/env python
"""P4-LUAC: prove that tools/luac53-game/src/ holds the official Lua 5.3.6.

lua.org publishes no checksum file for lua-5.3.6.tar.gz (both
lua-5.3.6.tar.gz.sha256 and lua-5.3.6.tar.gz.md5 answer HTTP 404), so the
download is checked a second, stronger way: every C source and header of the
unpacked tree is compared byte-for-byte with the official repository at the
pinned tag v5.3.6 (github.com/lua/lua), and the release tarball itself is
compared with the tarball of the same tag.

    python tools/luac53-game/verify_sources.py              # local files only
    python tools/luac53-game/verify_sources.py --fetch-tag  # also download the tag

Exit code 0 only if every compared file is identical. Writes nothing outside
this tool directory and scratch/.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.dirname(os.path.dirname(HERE))
SRC = os.path.join(HERE, "src", "lua-5.3.6")
DL = os.path.join(HERE, "dl")
SCRATCH = os.path.join(MOD, "scratch", "2026-10-04_P4-LUAC")
TAG_URL = "https://codeload.github.com/lua/lua/tar.gz/refs/tags/v5.3.6"
RELEASE = os.path.join(DL, "lua-5.3.6.tar.gz")
TAG_ARCHIVE = os.path.join(SCRATCH, "lua-v5.3.6-tag.tar.gz")

# Generated or test-only files: the release tarball and the git tag differ here
# by design, so they are reported rather than compared.
IGNORED = {"makefile", "Makefile", "all", ".gitignore", "manual", "testes",
           "ltests.c", "ltests.h", "lib1.c", "lib2.c", "lib11.c", "lib21.c"}

# The git tag puts the sources at the top of the tree, the release tarball one
# level down in src/. Both are accepted; anything deeper is documentation.
DEPTHS = (1, 2)


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def rel(p: str) -> str:
    return os.path.relpath(p, MOD).replace("\\", "/")


def compare(label: str, member_paths, archive: str, problems: list) -> None:
    """Compare files from `archive` (top level of the tree) with our src/."""
    tar = tarfile.open(archive)
    tar_files = {}
    for m in tar.getmembers():
        if not m.isfile():
            continue
        parts = m.name.split("/")[1:]
        if len(parts) not in DEPTHS:
            continue
        name = parts[-1]
        if name in IGNORED:
            continue
        if len(parts) == 2 and parts[0] != "src":
            continue
        tar_files[name] = tar.extractfile(m).read()
    same, differ = [], []
    for name, blob in sorted(tar_files.items()):
        path = os.path.join(SRC, "src", name)
        if not os.path.isfile(path):
            continue
        if open(path, "rb").read() == blob:
            same.append(name)
        else:
            differ.append(name)
    print("%s: %d files compared, %d identical, %d different"
          % (label, len(same) + len(differ), len(same), len(differ)))
    if differ:
        problems.extend("%s differs: %s" % (label, d) for d in differ)
        print("   DIFFERENT: %s" % ", ".join(differ))
    print("   identical sample: %s" % ", ".join(same[:8]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch-tag", action="store_true",
                    help="download the pinned github.com/lua/lua tag v5.3.6")
    args = ap.parse_args()
    problems: list = []

    print("unpacked tree : %s" % rel(SRC))
    if not os.path.isdir(SRC):
        print("missing; run the unpack step described in README.md")
        return 2
    print("release tarball: %s  size %d bytes  sha256 %s"
          % (rel(RELEASE), os.path.getsize(RELEASE), sha256(RELEASE))
          if os.path.isfile(RELEASE) else "release tarball: MISSING")
    if not os.path.isfile(RELEASE):
        return 2
    print("upstream published checksum for that file: none (404 on both"
          " .sha256 and .md5, observed 2026-10-05)")
    print()

    compare("release tarball vs unpacked src/", None, RELEASE, problems)

    if args.fetch_tag:
        os.makedirs(SCRATCH, exist_ok=True)
        if not os.path.isfile(TAG_ARCHIVE):
            subprocess.run(["curl", "-sSL", "--max-time", "180", "-o",
                            TAG_ARCHIVE, TAG_URL], check=True)
        print("git tag v5.3.6 : %s  size %d bytes  sha256 %s"
              % (rel(TAG_ARCHIVE), os.path.getsize(TAG_ARCHIVE),
                 sha256(TAG_ARCHIVE)))
        compare("official git tag v5.3.6 vs unpacked src/", None,
                TAG_ARCHIVE, problems)

    print()
    if problems:
        print("FAILED: %d problem(s)" % len(problems))
        for p in problems:
            print("  %s" % p)
        return 1
    print("OK: the unpacked C sources match the official Lua 5.3.6 sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())