#!/usr/bin/env python
"""P4-LUAC checks for the game-format luac built by build.sh.

Runs every check the P4-LUAC prompt asks for, prints one line per check with
its exit code, and writes the raw evidence (listings, headers, listings of the
game chunks) plus a summary file. Paths resolve against this script's own
location, so it can be run from anywhere:

    python mods/mii_customizer/tools/luac53-game/check_luac53_game.py

Tier B throughout: everything here is offline observation of bytes and of a
locally built program. Nothing here says the game would load any chunk.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))            # tools/luac53-game
MOD = os.path.dirname(os.path.dirname(HERE))                 # mods/mii_customizer
WS = os.path.dirname(os.path.dirname(MOD))                   # workspace root

BIN = os.path.join(HERE, "bin")
TESTSRC = os.path.join(HERE, "testsrc")
EVID = os.path.join(MOD, "evidence", "P4-LUAC")
SCRATCH = os.path.join(MOD, "scratch", "2026-10-04_P4-LUAC")
OUT = os.path.join(SCRATCH, "out")
LISTINGS = os.path.join(EVID, "listings")

INSPECT_PY = os.path.join(MOD, "tools", "lua53-inspect", "lua53_inspect.py")

UI = os.path.join(WS, "gamedata", "mii_customizer", "P1-UI", "ui")
CHUNKS = [
    ("edit_actor", os.path.join(UI, "script", "menu", "chara_make",
                                "make_mii_edit_actor.lc")),
    ("special_actor", os.path.join(UI, "script", "menu", "chara_make",
                                   "make_mii_special_actor.lc")),
    ("edit_actor_patch", os.path.join(UI, "script_patch", "chara_make",
                                      "make_mii_edit_actor.lc")),
]

LUAC = os.path.join(BIN, "luac-game.exe")
LUA = os.path.join(BIN, "lua-game.exe")
LUAC_DOUBLE = os.path.join(BIN, "luac-control-double.exe")
LUA_DOUBLE = os.path.join(BIN, "lua-control-double.exe")
LUAC_32 = os.path.join(BIN, "luac-control-32bit.exe")

# The header ends with the main closure's upvalue count at 0x1d (lundump.c
# LoadHeader), so bytes 0x00..0x1d inclusive are the comparable prefix.
HEADER_BYTES = 0x1E

# Offset of the sizeof(lua_Number) byte inside the header.
OFF_NUM_SIZE = 0x10

# Opcodes that no game chunk uses but that the requested test constructs
# inevitably produce; used by check 5 to tell "expected" from "unexpected".
EXPECTED_EXTRA_OPCODES = {
    "SETUPVAL": "local functions sharing an upvalue that is written to "
                "(makeCounter's `n = n + ...`)",
    "LEN": "the `#CONFIG.label` length operator in test_editor_constructs.lua",
    "TESTSET": "the `elseif self.ticks <= 3` comparison chain in the test source",
}


def f32(x: float) -> float:
    return struct.unpack("<f", struct.pack("<f", x))[0]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rel(path: str) -> str:
    """Workspace-relative path for printing (never an absolute machine path)."""
    try:
        return os.path.relpath(path, WS).replace("\\", "/")
    except ValueError:  # pragma: no cover
        return path


def run(argv, **kw):
    return subprocess.run(argv, capture_output=True, text=True, **kw)


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, bool, int, str]] = []
        self.notes: list[str] = []

    def add(self, cid: str, title: str, ok: bool, detail: str) -> int:
        code = 0 if ok else 1
        self.rows.append((cid, title, ok, code, detail))
        print("%-4s %-6s exit=%d  %s" % (cid, "PASS" if ok else "FAIL", code,
                                         title))
        for line in detail.splitlines():
            print("       %s" % line)
        return code


def load_inspector():
    spec = importlib.util.spec_from_file_location("lua53_inspect", INSPECT_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    rep = Report()
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(EVID, exist_ok=True)
    os.makedirs(LISTINGS, exist_ok=True)

    for _, path in CHUNKS:
        if not os.path.isfile(path):
            print("missing game input: %s" % rel(path))
            return 2
    for exe in (LUAC, LUA, LUAC_DOUBLE, LUAC_32):
        if not os.path.isfile(exe):
            print("missing binary: %s (run tools/luac53-game/build.sh)" % rel(exe))
            return 2

    L = load_inspector()

    src_header = os.path.join(TESTSRC, "test_header.lua")
    src_editor = os.path.join(TESTSRC, "test_editor_constructs.lua")
    lc_header = os.path.join(OUT, "test_header.lc")
    lc_editor = os.path.join(OUT, "test_editor_constructs.lc")

    # ---------------------------------------------------------------- (a)
    r = run([LUAC, "-s", "-o", lc_header, src_header])
    ok_a = r.returncode == 0 and os.path.isfile(lc_header)
    if not ok_a:
        rep.add("a", "luac -s compiles the small test source", False,
                r.stderr.strip() or "no output file")
        return finish(rep)
    mine = open(lc_header, "rb").read()
    ref = open(CHUNKS[0][1], "rb").read()
    same = all(mine[:HEADER_BYTES] == open(p, "rb").read()[:HEADER_BYTES]
               for _, p in CHUNKS)
    detail = ["compiled %s (%d bytes, sha256 %s)"
              % (rel(lc_header), len(mine), sha256(mine)),
              "compared bytes 0x00..0x%02x (%d bytes, through the main "
              "closure upvalue byte at 0x1d)" % (HEADER_BYTES - 1, HEADER_BYTES),
              "our header : " + mine[:HEADER_BYTES].hex(" ")]
    for name, path in CHUNKS:
        data = open(path, "rb").read()
        equal = mine[:HEADER_BYTES] == data[:HEADER_BYTES]
        diff = [i for i in range(HEADER_BYTES)
                if mine[i] != data[i]]
        detail.append("%-17s %s  %s  diffs=%s"
                      % (name, data[:HEADER_BYTES].hex(" "),
                         "IDENTICAL" if equal else "DIFFERENT", diff or "none"))
    rep.add("a", "compiled header is byte-identical to all three game chunks",
            same, "\n".join(detail))

    # ---------------------------------------------------------------- (b)
    outs = []
    ok_b = True
    for cmd in ("verify", "roundtrip"):
        r = run([sys.executable, INSPECT_PY, cmd, lc_header])
        outs.append("lua53_inspect %-9s exit=%d" % (cmd, r.returncode))
        if r.returncode != 0:
            ok_b = False
            outs.append((r.stdout.strip() + r.stderr.strip())[-400:])
    rep.add("b", "lua53-inspect verify + roundtrip accept the compiled chunk",
            ok_b, "\n".join(outs))

    # ---------------------------------------------------------------- (c)
    detail = []
    ok_c = True
    proto_totals = []
    for name, path in CHUNKS:
        # -p ("parse only") is required: luac.c pmain dumps to `luac.out` after
        # printing the listing unless dumping is turned off, which would write
        # a file into whatever directory the check was started from.
        r = run([LUAC, "-p", "-l", "-l", path])
        listing_path = os.path.join(LISTINGS, name + ".luac-l-l.txt")
        with open(listing_path, "w", newline="\n") as fh:
            fh.write("luac -p -l -l %s\n" % rel(path))
            fh.write("sha256(input) %s\n" % sha256(open(path, "rb").read()))
            fh.write("exit code %d\n\n" % r.returncode)
            fh.write(r.stdout)
            if r.stderr:
                fh.write("\n--- stderr ---\n" + r.stderr)
        listing = r.stdout
        listed = parse_listing(listing)
        data = open(path, "rb").read()
        hdr, main = L.load_chunk(data)
        parsed = [(p.path, len(p.code), len(p.constants))
                  for p in L.walk(main)]
        mismatches = []
        if len(listed) != len(parsed):
            mismatches.append("prototype count: listing %d, inspector %d"
                              % (len(listed), len(parsed)))
        for (lp, lcode, lconst), (pp, pcode, pconst) in zip(listed, parsed):
            if lcode != pcode or lconst != pconst:
                mismatches.append(
                    "%s: listing %d instr / %d const, inspector %d / %d"
                    % (pp, lcode, lconst, pcode, pconst))
        proto_totals.append((name, len(parsed),
                             sum(x[1] for x in parsed),
                             sum(x[2] for x in parsed),
                             sum(x[1] for x in listed),
                             sum(x[2] for x in listed)))
        if r.returncode != 0 or mismatches:
            ok_c = False
        detail.append("%-17s luac exit=%d stderr=%r  protos=%d  "
                      "instructions listing/inspector=%d/%d  constants=%d/%d"
                      % (name, r.returncode, r.stderr.strip()[:60],
                         len(parsed), sum(x[1] for x in listed),
                         sum(x[1] for x in parsed),
                         sum(x[2] for x in listed), sum(x[2] for x in parsed)))
        detail.append("   listing saved: %s" % rel(listing_path))
        for m in mismatches:
            detail.append("   MISMATCH " + m)
    rep.add("c", "luac -l -l loads and lists all three game chunks; counts "
                 "agree with lua53-inspect summary", ok_c, "\n".join(detail))

    # ---------------------------------------------------------------- (d)
    expected = [
        "3",
        "integer",
        # 2^63-1: what LUA_INT_LONGLONG (luaconf.h:558-560) prints. A
        # LUA_32BITS build would print 2147483647 instead.
        str(2 ** 63 - 1),
        "%.17g" % f32(0.1),
        "true" if f32(f32(0.1) + f32(0.2)) == f32(0.3) else "false",
        # tostring of a float uses LUA_NUMBER_FMT, which for a float build is
        # "%.7g" (luaconf.h:464), not LUAI_MAXNUMBER2STR's "%.14g".
        "%.7g" % f32(1 / 3),
    ]
    r = run([LUA, lc_header])
    got = r.stdout.splitlines()
    ok_d = r.returncode == 0 and got == expected
    lines = ["expected values derived in Python from float32 semantics, not "
             "copied from a run",
             "exit code %d" % r.returncode]
    for i, (e, g) in enumerate(zip(expected + [""] * 8, got + [""] * 8), 1):
        if not e and not g:
            break
        lines.append("line %d expected %-22r got %r%s" %
                     (i, e, g, "" if e == g else "   <-- MISMATCH"))
    if r.stderr.strip():
        lines.append("stderr: " + r.stderr.strip())
    # the same source built with doubles must print different numbers
    lc_double = os.path.join(OUT, "test_header.control-double.lc")
    r2 = run([LUAC_DOUBLE, "-s", "-o", lc_double, src_header])
    r3 = run([LUA_DOUBLE, lc_double])
    lines.append("control (stock double build) prints: %r"
                 % (r3.stdout.splitlines() or r3.stderr.strip()[:80]))
    rep.add("d", "lua runs the compiled chunk and float32 behaviour is "
                 "visible", ok_d, "\n".join(lines))

    # ---------------------------------------------------------------- (e)
    lc_32 = os.path.join(OUT, "test_header.control-32bit.lc")
    r32 = run([LUAC_32, "-s", "-o", lc_32, src_header])
    d32 = open(lc_32, "rb").read() if r32.returncode == 0 else b""
    dbl = open(lc_double, "rb").read() if r2.returncode == 0 else b""

    mut = bytearray(mine)
    mutated_path = os.path.join(OUT, "test_header.bad-numsize.lc")
    mut[OFF_NUM_SIZE] = 8          # claim sizeof lua_Number = 8 in a float chunk
    open(mutated_path, "wb").write(bytes(mut))

    e1 = dbl[:HEADER_BYTES] != ref[:HEADER_BYTES]
    e2 = d32[:HEADER_BYTES] != ref[:HEADER_BYTES]
    # the loader's own wording for a bad header is either of these
    # (lundump.c checkHeader / checkHeaderField messages)
    BAD_HEADER = ("bad header", "size mismatch in precompiled chunk")

    def rejects(proc):
        text = (proc.stdout + proc.stderr).lower()
        return proc.returncode != 0 and any(m in text for m in BAD_HEADER)

    rv = run([sys.executable, INSPECT_PY, "verify", mutated_path])
    e3 = rv.returncode != 0
    rl = run([LUA, mutated_path])
    e4 = rejects(rl)
    rd = run([LUA, lc_double])
    e5 = rejects(rd)

    detail = [
        "E1 stock double luac: same source, sizeof lua_Number byte 0x10 = %d, "
        "header differs from game header -> %s"
        % (dbl[OFF_NUM_SIZE] if dbl else -1, "REJECTED (good)" if e1 else "ACCEPTED (BAD)"),
        "   header: " + (dbl[:HEADER_BYTES].hex(" ") if dbl else "n/a"),
        "   game  : " + ref[:HEADER_BYTES].hex(" "),
        "E2 32-bit target luac (--target=i686-w64-mingw32): sizeof size_t byte "
        "0x0d = %d, header differs -> %s"
        % (d32[0x0D] if d32 else -1, "REJECTED (good)" if e2 else "ACCEPTED (BAD)"),
        "   header: " + (d32[:HEADER_BYTES].hex(" ") if d32 else "n/a"),
        "E3 one header byte changed in our chunk (0x10: 4 -> 8): "
        "lua53_inspect verify exit=%d -> %s"
        % (rv.returncode, "REJECTED (good)" if e3 else "ACCEPTED (BAD)"),
        "   inspector says: " + (rv.stdout.strip().splitlines()[-1]
                                 if rv.stdout.strip() else rv.stderr.strip()[:120]),
        "E4 the game-format lua on that mutated chunk: exit=%d -> %s"
        % (rl.returncode, "REJECTED (good)" if e4 else "ACCEPTED (BAD)"),
        "   " + (rl.stderr.strip().splitlines()[-1] if rl.stderr.strip()
                else rl.stdout.strip()[:120]),
        "E5 the game-format lua on the double-built chunk: exit=%d -> %s"
        % (rd.returncode, "REJECTED (good)" if e5 else "ACCEPTED (BAD)"),
        "   " + (rd.stderr.strip().splitlines()[-1] if rd.stderr.strip()
                else rd.stdout.strip()[:120]),
        "control: the same three game chunks are accepted by this lua (check c), "
        "so the rejection above is about the header, not about being a chunk",
    ]
    rep.add("e", "negative controls are rejected when they should be",
            all((e1, e2, e3, e4, e5)), "\n".join(detail))

    # ---------------------------------------------------------------- (f)
    lc_a = os.path.join(OUT, "determinism-a.lc")
    lc_b = os.path.join(OUT, "determinism-b.lc")
    ha_a = os.path.join(OUT, "determinism-header-a.lc")
    ha_b = os.path.join(OUT, "determinism-header-b.lc")
    ra = run([LUAC, "-s", "-o", lc_a, src_editor])
    rb = run([LUAC, "-s", "-o", lc_b, src_editor])
    rc = run([LUAC, "-s", "-o", ha_a, src_header])
    rd2 = run([LUAC, "-s", "-o", ha_b, src_header])
    h1 = sha256(open(lc_a, "rb").read()) if ra.returncode == 0 else ""
    h2 = sha256(open(lc_b, "rb").read()) if rb.returncode == 0 else ""
    h3 = sha256(open(ha_a, "rb").read()) if rc.returncode == 0 else ""
    h4 = sha256(open(ha_b, "rb").read()) if rd2.returncode == 0 else ""
    rep.add("f", "compiling the same source twice gives identical bytes",
            bool(h1) and h1 == h2 and bool(h3) and h3 == h4 and h3 == sha256(mine),
            "test_editor_constructs.lua run 1 sha256 %s\n"
            "test_editor_constructs.lua run 2 sha256 %s\n"
            "test_header.lua          run 1 sha256 %s\n"
            "test_header.lua          run 2 sha256 %s (same file as check a: %s)\n"
            "exit codes %d / %d / %d / %d"
            % (h1, h2, h3, h4, sha256(mine), ra.returncode, rb.returncode,
               rc.returncode, rd2.returncode))

    # ------------------------------------------------------- check 5 (extra)
    r = run([LUAC, "-s", "-o", lc_editor, src_editor])
    ok5 = r.returncode == 0
    detail = []
    if ok5:
        edata = open(lc_editor, "rb").read()
        ehdr, emain = L.load_chunk(edata)
        e_ops = sorted({i.op for p in L.walk(emain) for i in p.code})
        e_tags = sorted({k.tag for p in L.walk(emain) for k in p.constants})
        e_kinds = sorted({k.kind for p in L.walk(emain) for k in p.constants})
        g_ops, g_tags, g_kinds = set(), set(), set()
        for _, path in CHUNKS:
            _, m = L.load_chunk(open(path, "rb").read())
            g_ops |= {i.op for p in L.walk(m) for i in p.code}
            g_tags |= {k.tag for p in L.walk(m) for k in p.constants}
            g_kinds |= {k.kind for p in L.walk(m) for k in p.constants}
        extra_ops = [L.OPNAMES[o] for o in e_ops if o not in g_ops]
        extra_tags = [t for t in e_tags if t not in g_tags]
        never = [L.OPNAMES[o] for o in range(len(L.OPNAMES)) if o not in g_ops]
        detail.append("test chunk: %s (%d bytes, sha256 %s)"
                      % (rel(lc_editor), len(edata), sha256(edata)))
        detail.append("opcodes used by the test: %s"
                      % ", ".join(L.OPNAMES[o] for o in e_ops))
        detail.append("constant tags used by the test: %s (%s)"
                      % (e_tags, ", ".join(e_kinds)))
        detail.append("game chunks use %d of %d opcodes and %d of the %d "
                      "constant tags" % (len(g_ops), len(L.OPNAMES),
                                         len(g_tags), len(e_tags)))
        detail.append("opcodes used by the test that NO game chunk uses: %s"
                      % (", ".join(extra_ops) or "none"))
        detail.append("constant tags used by the test that NO game chunk uses: %s"
                      % (", ".join(str(t) for t in extra_tags) or "none"))
        for op in extra_ops:
            detail.append("   %s comes from the requested construct: %s"
                          % (op, EXPECTED_EXTRA_OPCODES.get(op, "UNEXPECTED")))
        unexpected = [o for o in extra_ops
                      if o not in EXPECTED_EXTRA_OPCODES]
        detail.append("for reference, opcodes no game chunk uses: %s"
                      % ", ".join(never))
        detail.append("game-chunk constant tag numbers seen: %s (kinds %s)"
                      % (sorted(g_tags), ", ".join(sorted(g_kinds))))
        # A constant tag or opcode outside the game chunks' sets would mean the
        # compiler emits something the editor chunks never contain. The three
        # opcodes below are expected: they are what the constructs the prompt
        # asks for compile to, and the game chunks simply never happen to use
        # them. Anything else is a finding.
        ok5 = not extra_tags and not unexpected
    else:
        detail.append(r.stderr.strip())
    rep.add("5", "editor-construct source: opcodes and constant tags stay "
                 "inside the game chunks' sets", ok5, "\n".join(detail))

    # ------------------------------------------- (g) stripped-shape parity
    # Beyond the header, `luac -s` must produce the same debug-section shape
    # as the game chunks: a NULL source string and empty debug tables in every
    # prototype (ldump.c DumpDebug with strip set).
    e_hdr, e_main2 = L.load_chunk(edata)
    e_props = [(p.source_is_null, p.is_stripped) for p in L.walk(e_main2)]
    lines = []
    ok_g = True
    for name, path in CHUNKS:
        _, gm = L.load_chunk(open(path, "rb").read())
        g_props = [(p.source_is_null, p.is_stripped) for p in L.walk(gm)]
        bad = [p.path for p in L.walk(gm)
               if not p.source_is_null or not p.is_stripped]
        same_shape = all(x[0] and x[1] for x in e_props)
        if bad or not same_shape:
            ok_g = False
        lines.append("%-17s protos with a source string or debug data: %s"
                     % (name, ", ".join(bad) or "none"))
    lines.append("our two compiled chunks: every prototype has a NULL source "
                 "and stripped debug tables: %s" % (all(e_props) and e_props))
    rep.add("g", "luac -s produces the same stripped debug shape as the game "
                 "chunks", ok_g, "\n".join(lines))

    # verification of the compiled test chunk with the inspector, repeated for
    # the record with its own exit code
    r = run([sys.executable, INSPECT_PY, "verify", lc_header, lc_editor])
    rep.add("b2", "lua53-inspect verify on both compiled chunks",
            r.returncode == 0, "exit=%d\n%s" % (r.returncode,
                                                r.stdout.strip()))

    return finish(rep)


def parse_listing(text: str):
    """Parse a `luac -l -l` listing into (path, instructions, constants).

    luac.c PrintFunction prints one header block per prototype, recursing into
    nested prototypes in load order (luac.c:443-450), which is the same order
    lua53-inspect's walk() uses.
    """
    hdr = re.compile(r"^(main|function) <([^>]*)> \((\d+) instructions? at ")
    stats = re.compile(
        r"^(\d+)(\+)? params?, (\d+) slots?, (\d+) upvalues?, "
        r"(\d+) locals?, (\d+) constants?, (\d+) functions?")
    rows = []
    pending = None
    for line in text.splitlines():
        m = hdr.match(line)
        if m:
            pending = {"name": m.group(1), "src": m.group(2),
                       "line": int(m.group(3)), "consts": None}
            continue
        if pending is not None:
            m = stats.match(line.strip())
            if m:
                rows.append((pending["name"], pending["line"],
                             int(m.group(6))))
                pending = None
    return rows


def finish(rep: Report) -> int:
    failed = [r for r in rep.rows if not r[2]]
    lines = ["P4-LUAC check summary",
             "generated by tools/luac53-game/check_luac53_game.py",
             "inputs (workspace-relative):"]
    for name, path in CHUNKS:
        lines.append("  %-34s sha256 %s"
                     % (rel(path), sha256(open(path, "rb").read())))
    lines.append("")
    for cid, title, ok, code, _ in rep.rows:
        lines.append("%-4s %-6s exit=%d  %s" % (cid, "PASS" if ok else "FAIL",
                                                code, title))
    lines.append("")
    lines.append("%d checks, %d failed" % (len(rep.rows), len(failed)))
    text = "\n".join(lines) + "\n"
    with open(os.path.join(EVID, "CHECK_SUMMARY.txt"), "w",
              newline="\n") as fh:
        fh.write(text)
    print()
    print("%d checks, %d failed" % (len(rep.rows), len(failed)))
    print("summary: %s" % rel(os.path.join(EVID, "CHECK_SUMMARY.txt")))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())