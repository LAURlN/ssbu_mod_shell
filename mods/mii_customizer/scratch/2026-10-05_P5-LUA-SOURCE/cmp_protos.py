#!/usr/bin/env python3
"""Per-prototype comparison: original game chunk vs my compiled chunk.

Usage (from the workspace root):
    python mods/mii_customizer/scratch/2026-10-05_P5-LUA-SOURCE/cmp_protos.py \
        gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc \
        gamedata/mii_customizer/P5-LUA-SOURCE/make_mii_special_actor.lc

Prints one row per prototype: instruction count, constant count, first
differing pc, upvalue descriptor equality. With --verbose it also prints both
decodings of the first differing instruction and the constant tables.
Exit 0 only when every prototype is identical.
"""

from __future__ import annotations

import sys

sys.path.insert(0, "mods/mii_customizer/tools/lua53-inspect")

import lua53_inspect as li  # noqa: E402


def consts(p: li.Proto) -> "list[str]":
    return [const_repr(k) for k in p.constants]


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


def dis(p: li.Proto, ins: li.Instruction) -> str:
    args = ins.args_text()
    txt = "%d\t%s\t%s" % (ins.pc, ins.name(), args)
    # resolve RK operands for readability
    try:
        return "%-46s %s" % (txt, ins.rk(p, "B") or "")
    except Exception:
        return txt


def main(argv: "list[str]") -> int:
    verbose = "--verbose" in argv
    files = [a for a in argv[1:] if not a.startswith("--")]
    if len(files) != 2:
        print(__doc__)
        return 2
    a_data = open(files[0], "rb").read()
    b_data = open(files[1], "rb").read()
    a_hdr, a_main = li.load_chunk(a_data)
    b_hdr, b_main = li.load_chunk(b_data)

    print("bytes  orig %d  mine %d  %s"
          % (len(a_data), len(b_data), "OK" if a_data == b_data else "DIFFER"))
    print()
    rows = []
    a_protos = {p.path: p for p in li.walk(a_main)}
    b_protos = {p.path: p for p in li.walk(b_main)}
    names = sorted(set(a_protos) | set(b_protos),
                   key=lambda s: (s.count("."), s))
    bad = 0
    for path in names:
        a = a_protos.get(path)
        b = b_protos.get(path)
        if a is None or b is None:
            rows.append((path, "missing on one side", "", "", "", ""))
            bad += 1
            continue
        nc, nc2 = len(a.code), len(b.code)
        kc, kc2 = len(a.constants), len(b.constants)
        firstdiff = "-"
        if nc != nc2:
            firstdiff = "count"
        else:
            for i, (x, y) in enumerate(zip(a.code, b.code)):
                if x.word != y.word:
                    firstdiff = str(i)
                    break
        upv = "OK" if a.upvalues == b.upvalues else "DIFF"
        hdr = "OK" if (a.linedefined == b.linedefined
                       and a.lastlinedefined == b.lastlinedefined) else "DIFF"
        flags = (a.numparams, a.is_vararg, a.maxstacksize,
                 b.numparams, b.is_vararg, b.maxstacksize)
        meta = "OK" if a.maxstacksize == b.maxstacksize else \
            "maxstack %s/%s" % (a.maxstacksize, b.maxstacksize)
        ok = (firstdiff == "-" and upv == "OK" and hdr == "OK"
              and kc == kc2 and consts(a) == consts(b))
        if not ok:
            bad += 1
        rows.append((path, "%d/%d" % (nc, nc2), "%d/%d" % (kc, kc2),
                     firstdiff, upv, "%s lines %s/%s,%s/%s  %s"
                     % (hdr, a.linedefined, b.linedefined,
                        a.lastlinedefined, b.lastlinedefined, meta)))
    w = max(len(r[0]) for r in rows) + 1
    print("%-*s %-12s %-12s %-8s %-6s %s" % (w, "proto", "instr o/m",
                                             "const o/m", "1st diff", "upv",
                                             "lines/misc"))
    for r in rows:
        print("%-*s %-12s %-12s %-8s %-6s %s" % (w, r[0], r[1], r[2], r[3],
                                                r[4], r[5]))
    print()
    print("prototypes differing: %d of %d" % (bad, len(rows)))

    if verbose:
        for path in names:
            a = a_protos.get(path)
            b = b_protos.get(path)
            if a is None or b is None:
                continue
            if (a.code == b.code and consts(a) == consts(b)
                    and a.upvalues == b.upvalues
                    and a.linedefined == b.linedefined
                    and a.lastlinedefined == b.lastlinedefined):
                continue
            print("=== %s ===" % path)
            n = max(len(a.code), len(b.code))
            for i in range(n):
                x = a.code[i] if i < len(a.code) else None
                y = b.code[i] if i < len(b.code) else None
                if x is not None and y is not None and x.word == y.word:
                    continue
                print("  orig %3d %08x  %s" % (i, x.word, x.args_text())
                      if x else "  orig %3d <missing>" % i)
                print("  mine %3d %08x  %s" % (i, y.word, y.args_text())
                      if y else "  mine %3d <missing>" % i)
            for i in range(max(len(a.constants), len(b.constants))):
                x = const_repr(a.constants[i]) if i < len(a.constants) else "-"
                y = const_repr(b.constants[i]) if i < len(b.constants) else "-"
                if x != y:
                    print("  const %3d orig %-40s mine %s" % (i, x, y))
            if a.upvalues != b.upvalues:
                print("  upv orig %s mine %s" % (a.upvalues, b.upvalues))
    return 1 if (bad or a_data != b_data) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))