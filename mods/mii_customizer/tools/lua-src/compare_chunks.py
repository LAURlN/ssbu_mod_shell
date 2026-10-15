#!/usr/bin/env python3
"""Per-prototype comparison of two Lua 5.3 chunks.

Run from the workspace root:

    python mods/mii_customizer/tools/lua-src/compare_chunks.py A.lc B.lc \
        [--verbose] [--proto NAME ...]

Prints one row per prototype: instruction count, constant count, first
differing pc, upvalue descriptor equality, line numbers and maxstack.  With
``--verbose`` it prints both decodings of every differing instruction, plus
constant, upvalue, numparams and is_vararg differences.

A prototype counts as identical only when instructions, constants, upvalue
descriptors, numparams, is_vararg, maxstacksize, linedefined and
lastlinedefined all match.  Exit 0 only when the two files are byte-identical
*and* every prototype is identical; the byte comparison covers the chunk
header, which the per-prototype table does not.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join("mods", "mii_customizer", "tools",
                                "lua53-inspect"))
import lua53_inspect as li  # noqa: E402


def const_repr(k: li.Constant) -> str:
    if k.is_string:
        return "S:%r" % (k.value,)
    if k.tag == li.T_NUMFLT:
        return "F:%r" % (k.value,)
    if k.tag == li.T_NUMINT:
        return "I:%d" % (k.value,)
    if k.tag == li.T_NIL:
        return "nil"
    if k.tag == li.T_BOOLEAN:
        return "B:%s" % (k.value,)
    return "tag%d:%r" % (k.tag, k.value)


def consts(p: li.Proto) -> "list[str]":
    return [const_repr(k) for k in p.constants]


def proto_equal(a: li.Proto, b: li.Proto) -> bool:
    return (len(a.code) == len(b.code)
            and all(x.word == y.word for x, y in zip(a.code, b.code))
            and consts(a) == consts(b)
            and a.upvalues == b.upvalues
            and a.numparams == b.numparams
            and a.is_vararg == b.is_vararg
            and a.maxstacksize == b.maxstacksize
            and a.linedefined == b.linedefined
            and a.lastlinedefined == b.lastlinedefined)


def main(argv: "list[str]") -> int:
    args = argv[1:]
    verbose = "--verbose" in args
    only: "list[str]" = []
    files: "list[str]" = []
    i = 0
    while i < len(args):
        if args[i] == "--proto":
            only.append(args[i + 1])
            i += 2
            continue
        if args[i].startswith("--"):
            i += 1
            continue
        files.append(args[i])
        i += 1
    if len(files) != 2:
        print(__doc__)
        return 2

    a_data = open(files[0], "rb").read()
    b_data = open(files[1], "rb").read()
    _, a_main = li.load_chunk(a_data)
    _, b_main = li.load_chunk(b_data)

    print("bytes orig %d  mine %d  %s"
          % (len(a_data), len(b_data),
             "IDENTICAL" if a_data == b_data else "DIFFER"))
    a_protos = {p.path: p for p in li.walk(a_main)}
    b_protos = {p.path: p for p in li.walk(b_main)}
    names = sorted(set(a_protos) | set(b_protos),
                   key=lambda s: (s.count("."), s))

    rows = []
    bad = 0
    for path in names:
        if only and path not in only:
            continue
        a = a_protos.get(path)
        b = b_protos.get(path)
        if a is None or b is None:
            rows.append((path, "missing on one side", "", "", "", ""))
            bad += 1
            continue
        first = "-"
        if len(a.code) != len(b.code):
            first = "count %d/%d" % (len(a.code), len(b.code))
        else:
            for k, (x, y) in enumerate(zip(a.code, b.code)):
                if x.word != y.word:
                    first = str(k)
                    break
        upv = "OK" if a.upvalues == b.upvalues else "DIFF"
        lines_ok = (a.linedefined == b.linedefined
                    and a.lastlinedefined == b.lastlinedefined)
        meta = "" if a.maxstacksize == b.maxstacksize else \
            "maxstack %d/%d" % (a.maxstacksize, b.maxstacksize)
        if not proto_equal(a, b):
            bad += 1
        rows.append((path, "%d/%d" % (len(a.code), len(b.code)),
                     "%d/%d" % (len(a.constants), len(b.constants)),
                     first, upv,
                     "lines %s %d/%d,%d/%d %s"
                     % ("OK" if lines_ok else "DIFF", a.linedefined,
                        b.linedefined, a.lastlinedefined, b.lastlinedefined,
                        meta)))

    w = max(len(r[0]) for r in rows) + 1 if rows else 5
    print("%-*s %-12s %-10s %-10s %-6s %s"
          % (w, "proto", "instr o/m", "const o/m", "1st diff", "upv",
             "lines/misc"))
    for r in rows:
        print("%-*s %-12s %-10s %-10s %-6s %s"
              % (w, r[0], r[1], r[2], r[3], r[4], r[5]))
    print()
    print("prototypes differing: %d of %d" % (bad, len(rows)))

    if verbose:
        for path in names:
            if only and path not in only:
                continue
            a = a_protos.get(path)
            b = b_protos.get(path)
            if a is None or b is None or proto_equal(a, b):
                continue
            print("=== %s ===" % path)
            for k in range(max(len(a.code), len(b.code))):
                x = a.code[k] if k < len(a.code) else None
                y = b.code[k] if k < len(b.code) else None
                if x is not None and y is not None and x.word == y.word:
                    continue
                print("  orig %3d  %s" % (k, x.args_text()) if x
                      else "  orig %3d  <missing>" % k)
                print("  mine %3d  %s" % (k, y.args_text()) if y
                      else "  mine %3d  <missing>" % k)
            for k in range(max(len(a.constants), len(b.constants))):
                x = const_repr(a.constants[k]) if k < len(a.constants) else "-"
                y = const_repr(b.constants[k]) if k < len(b.constants) else "-"
                if x != y:
                    print("  const %3d orig %-46s mine %s" % (k, x, y))
            if a.upvalues != b.upvalues:
                print("  upv orig %s" % (a.upvalues,))
                print("      mine %s" % (b.upvalues,))
            if a.numparams != b.numparams:
                print("  numparams orig %d mine %d" % (a.numparams,
                                                       b.numparams))
            if a.is_vararg != b.is_vararg:
                print("  is_vararg orig %d mine %d" % (a.is_vararg,
                                                      b.is_vararg))
            if a.maxstacksize != b.maxstacksize:
                print("  maxstacksize orig %d mine %d" % (a.maxstacksize,
                                                          b.maxstacksize))
            if (a.linedefined, a.lastlinedefined) != \
               (b.linedefined, b.lastlinedefined):
                print("  lines orig %d-%d mine %d-%d"
                      % (a.linedefined, a.lastlinedefined,
                         b.linedefined, b.lastlinedefined))

    return 1 if (bad or a_data != b_data) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
