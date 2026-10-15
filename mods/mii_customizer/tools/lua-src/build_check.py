#!/usr/bin/env python3
"""Compile the reconstructed sources and require byte-identical chunks.

Run from the workspace root:

    python mods/mii_customizer/tools/lua-src/build_check.py [TARGET ...]

With no argument both targets are checked.  A target is a source file plus the
original game chunk it must reproduce:

| target | source | original |
|---|---|---|
| `special` | `make_mii_special_actor.lua` | `ui/script/menu/chara_make/…` (P5) |
| `edit`    | `make_mii_edit_actor.lua`    | `ui/script_patch/chara_make/…` (P9) |

For each target this script

1. compiles the source with `tools/luac53-game/bin/luac-game.exe -s` into
   `gamedata/mii_customizer/<project>/`,
2. compares it against the original, printing the per-prototype table from
   `compare_chunks.py` on any mismatch,
3. applies the `is_vararg` post-pass described below,
4. re-reads the patched file and re-runs both the per-prototype comparison and
   a plain byte comparison, so the reported verdict is about the bytes that
   are actually on disk.

## The is_vararg post-pass

Both the main chunk and every other prototype must match exactly, and they do,
except for one byte.  In `lundump`/`ldump` the main prototype's header is

    source (size_t) | linedefined (int) | lastlinedefined (int)
    | numparams (u8) | is_vararg (u8) | maxstacksize (u8) | ...

and `ldump.c` writes `is_vararg` straight through with no normalisation, so the
game's chunks carry **2** in the main prototype while this compiler emits
**1** (`lparser.c` `mainfunc()` sets `fs->f->is_vararg = 1` unconditionally for
the main chunk; no Lua source can change it).  The post-pass therefore writes
the original's value into that single byte.

The offset is *derived* from the parsed chunk, not hardcoded.  A prototype body
is laid out as

    source | linedefined (int) | lastlinedefined (int)
    | numparams (u8) | is_vararg (u8) | maxstacksize (u8) | sizecode (int) | ...

and a stripped prototype dumps its `source` as a single zero size byte, so
`is_vararg` sits 10 bytes into the main prototype.  `is_vararg_offset()` starts
from the main prototype's own offset as reported by `lua53_inspect` and then
*checks* the derivation against the parse: the bytes immediately before and
after the candidate must equal the parsed `numparams` and `maxstacksize`.  If
they do not, the check aborts rather than writing to a guessed offset.

The pass also refuses to run unless the target byte is already 1 and the
original holds 2, so it cannot silently mask a real difference elsewhere.

Exit 0 only when every requested target ends byte-identical on disk.

Nothing here is evidence that the game would load, accept or behave correctly
with any of these chunks.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))       # .../tools/lua-src
MOD = os.path.dirname(HERE)                            # mods/mii_customizer
WORKSPACE = os.path.dirname(os.path.dirname(
    os.path.dirname(MOD)))                             # workspace root
LUAC = os.path.join(WORKSPACE, "mods", "mii_customizer", "tools",
                    "luac53-game", "bin", "luac-game.exe")
CMP = os.path.join(WORKSPACE, "mods", "mii_customizer", "tools", "lua-src",
                   "compare_chunks.py")
sys.path.insert(0, os.path.join(WORKSPACE, "mods", "mii_customizer", "tools",
                                "lua53-inspect"))
import lua53_inspect as li  # noqa: E402

# source (1 zero size byte in a stripped proto) + 2 int line numbers
# + 1 numparams byte, so is_vararg is 10 bytes into the prototype.
IS_VARARG_IN_PROTO = 1 + 4 + 4 + 1

TARGETS = {
    "special": {
        "src": os.path.join("mods", "mii_customizer", "tools", "lua-src",
                            "make_mii_special_actor.lua"),
        "out": os.path.join("gamedata", "mii_customizer", "P5-LUA-SOURCE",
                            "make_mii_special_actor.lc"),
        "orig": os.path.join("gamedata", "mii_customizer", "P1-UI", "ui",
                             "script", "menu", "chara_make",
                             "make_mii_special_actor.lc"),
        "sha256": "ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d",
        "length": 7799,
        "project": "P5-LUA-SOURCE",
    },
    "edit": {
        "src": os.path.join("mods", "mii_customizer", "tools", "lua-src",
                            "make_mii_edit_actor.lua"),
        "out": os.path.join("gamedata", "mii_customizer", "P9-EDIT-SOURCE",
                            "make_mii_edit_actor.lc"),
        "orig": os.path.join("gamedata", "mii_customizer", "P1-UI", "ui",
                             "script_patch", "chara_make",
                             "make_mii_edit_actor.lc"),
        "sha256": ("c777ecc492cea48f6ffd40112b22f96e66219d00969b570a7cc3cf"
                   "8d7f4a9417"),
        "length": 10576,
        "project": "P9-EDIT-SOURCE",
    },
}


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compare(original: str, candidate: str) -> int:
    """Run the per-prototype comparator; return its exit code."""
    rc = subprocess.run([sys.executable, CMP, original, candidate,
                         "--verbose"], capture_output=True, text=True)
    sys.stdout.write(rc.stdout)
    sys.stderr.write(rc.stderr)
    return rc.returncode


def is_vararg_offset(data: bytes) -> int:
    """File offset of the main prototype's is_vararg byte.

    Derived from the parsed chunk and then validated: the two neighbouring
    bytes must be the numparams and maxstacksize values the parser read.
    """
    _, main = li.load_chunk(data)
    if not main.source_is_null:
        raise ValueError("main prototype is not stripped; its source field is "
                         "not a single zero byte, so the offset derivation "
                         "does not apply")
    off = main.offset + IS_VARARG_IN_PROTO
    if data[off - 1] != main.numparams or data[off + 1] != main.maxstacksize:
        raise ValueError("is_vararg offset %d (0x%02x) does not line up with "
                         "the parsed header: bytes are numparams=%d "
                         "is_vararg=%d maxstacksize=%d"
                         % (off, off, data[off - 1], data[off],
                            data[off + 1]))
    return off


def build(t: dict) -> bool:
    for p in (t["src"], LUAC, t["orig"]):
        if not os.path.exists(p):
            print("missing input: %s" % p)
            return False
    os.makedirs(os.path.dirname(t["out"]), exist_ok=True)
    cmd = [LUAC, "-s", "-o", t["out"], t["src"]]
    print("$ " + " ".join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.stdout:
        sys.stdout.write(proc.stdout)
    if proc.stderr:
        sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        print("luac-game failed with exit code %d" % proc.returncode)
        return False
    return True


def check(name: str, t: dict) -> bool:
    print("=" * 72)
    print("target %s   project %s" % (name, t["project"]))
    print("=" * 72)
    if not build(t):
        return False

    original = open(t["orig"], "rb").read()
    ref_sha, ref_len = sha256(t["orig"]), os.path.getsize(t["orig"])
    print("original %s  %d bytes  sha256 %s" % (t["orig"], ref_len, ref_sha))
    if ref_len != t["length"] or not ref_sha.startswith(t["sha256"][:16]):
        print("WARNING: the original chunk is not the expected input for %s"
              % name)

    print("\n-- per-prototype comparison before the is_vararg post-pass --")
    pre_rc = compare(t["orig"], t["out"])
    print("comparator exit %d%s"
          % (pre_rc, "" if pre_rc else "  (all prototypes identical)"))

    data = bytearray(open(t["out"], "rb").read())
    print("\n-- is_vararg post-pass --")
    try:
        off = is_vararg_offset(bytes(data))
    except ValueError as exc:
        print("FAIL: %s" % exc)
        return False
    print("patched byte offset %d (0x%02x), derived from the parsed main "
          "prototype at 0x%02x and validated against numparams/maxstacksize"
          % (off, off, li.load_chunk(bytes(data))[1].offset))
    if len(data) <= off:
        print("FAIL: chunk is shorter than the patch offset")
        return False
    print("original[%d] = %d   compiled[%d] = %d"
          % (off, original[off], off, data[off]))
    if original[off] != 2 or data[off] != 1:
        print("FAIL: expected the original to hold 2 and the build to hold 1; "
              "refusing to patch, because a different difference is present")
        return False
    data[off] = original[off]
    with open(t["out"], "wb") as fh:
        fh.write(bytes(data))
    print("wrote %s with is_vararg = %d" % (t["out"], original[off]))

    # Verify against what is now on disk, not against the in-memory copy.
    print("\n-- per-prototype comparison after the post-pass --")
    post_rc = compare(t["orig"], t["out"])

    on_disk = open(t["out"], "rb").read()
    same = on_disk == original
    got_sha, got_len = sha256(t["out"]), os.path.getsize(t["out"])
    print("\nfinal %s  %d bytes  sha256 %s" % (t["out"], got_len, got_sha))
    if not same:
        diffs = [i for i in range(min(len(on_disk), len(original)))
                 if on_disk[i] != original[i]]
        print("NOT byte-identical: %d differing bytes, first at %s"
              % (len(diffs),
                 ", ".join("0x%04x" % i for i in diffs[:16])))
        return False
    if post_rc != 0:
        print("byte-identical but the per-prototype comparator disagrees")
        return False
    n_protos = len(list(li.walk(li.load_chunk(on_disk)[1])))
    print("BYTE-IDENTICAL  (%d prototypes, all fields, sha256 %s)"
          % (n_protos, got_sha))
    return True


def main() -> int:
    names = sys.argv[1:] or sorted(TARGETS)
    for n in names:
        if n not in TARGETS:
            print("unknown target %r; known: %s"
                  % (n, ", ".join(sorted(TARGETS))))
            return 2
    results = [(n, check(n, TARGETS[n])) for n in names]
    print()
    print("=" * 72)
    for n, ok in results:
        print("%-8s %s" % (n, "BYTE-IDENTICAL" if ok else "FAILED"))
    return 0 if all(ok for _, ok in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
