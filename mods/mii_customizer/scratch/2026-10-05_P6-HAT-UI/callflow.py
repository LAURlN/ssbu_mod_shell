#!/usr/bin/env python3
"""Resolve every CALL in the four P6-HAT-UI chunks to a callee chain and an
argument list, using only the decoded instructions.

This is a bounded expression tracker, not a decompiler: it understands the
register/stack effects of the handful of opcodes the chunks actually use
(GETTABUP, GETTABLE, SELF, GETUPVAL, MOVE, LOADK, LOADBOOL, arithmetic) and
prints ``proto pc range -> receiver:method(args)``. Anything it cannot resolve
is printed with ``?`` rather than guessed.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.normpath(os.path.join(HERE, "..", ".."))
ROOT = os.path.normpath(os.path.join(MOD, "..", ".."))
sys.path.insert(0, os.path.join(MOD, "tools", "lua53-inspect"))

import lua53_inspect as L  # noqa: E402

CHUNKS = ["make_mii_hat_actor", "make_mii_hat_body_layout",
          "make_mii_utility", "make_mii_body_actor"]


def ktext(p, raw):
    if raw >= L.BITRK:
        k = p.constants[raw & ~L.BITRK]
        if k.kind == "string":
            return repr(k.value)
        if k.kind == "boolean":
            return "true" if k.value else "false"
        if k.kind == "integer":
            return str(k.value)
        if k.kind == "float":
            return repr(k.value)
        return "nil"
    return "R[%d]" % raw


def analyse(p):
    """One pass of symbolic register tracking; returns call descriptions."""
    reg = {}          # register -> expression string
    env = {}          # proto path -> set of upvalue indices that are _ENV
    out = []
    for inst in p.code:
        n = inst.name
        if n == "GETTABUP":
            up = inst.b
            base = "up[%d]" % up
            if up in env.get(p.path, ()):
                base = "_ENV"
            reg[inst.a] = "%s[%s]" % (base, ktext(p, inst.c))
        elif n == "GETUPVAL":
            reg[inst.a] = "up[%d]" % inst.b
        elif n == "GETTABLE":
            reg[inst.a] = "%s[%s]" % (reg.get(inst.b, "R[%d]" % inst.b),
                                      ktext(p, inst.c))
        elif n == "SELF":
            fn = "%s[%s]" % (reg.get(inst.b, "R[%d]" % inst.b), ktext(p, inst.c))
            reg[inst.a] = fn
            reg[inst.a + 1] = reg.get(inst.b, "R[%d]" % inst.b)
        elif n == "MOVE":
            reg[inst.a] = reg.get(inst.b, "R[%d]" % inst.b)
        elif n == "LOADK":
            reg[inst.a] = ktext(p, inst.bx)
        elif n == "LOADBOOL":
            reg[inst.a] = "true" if inst.b else "false"
        elif n == "LOADNIL":
            for i in range(inst.a, inst.a + inst.b + 1):
                reg[i] = "nil"
        elif n == "ADD":
            reg[inst.a] = "(%s + %s)" % (reg.get(inst.b, "R[%d]" % inst.b),
                                         ktext(p, inst.c))
        elif n == "SUB":
            reg[inst.a] = "(%s - %s)" % (ktext(p, inst.b),
                                         reg.get(inst.c, "R[%d]" % inst.c))
        elif n == "NEWTABLE":
            reg[inst.a] = "{}"
        elif n == "CLOSURE":
            reg[inst.a] = "closure(%s.p%d)" % (p.path, inst.bx)
        elif n == "SETTABLE":
            pass
        elif n == "SETTABUP":
            pass
        elif n in ("CALL", "TAILCALL"):
            fn = reg.get(inst.a, "R[%d]" % inst.a)
            nargs = inst.b - 1 if inst.b else "?"
            args = []
            for k in range(1, (nargs if isinstance(nargs, int) else 0) + 1):
                args.append(reg.get(inst.a + k, "R[%d]" % (inst.a + k)))
            out.append((inst.pc, inst.offset, n, fn, nargs,
                        inst.c - 1 if inst.c else "multret", args))
            # a call returning 0 values leaves the callee register alone;
            # 1 value replaces it; more values occupy consecutive registers
            if inst.c == 2:
                reg[inst.a] = "(%s)->" % fn
            elif isinstance(inst.c, int) and inst.c > 2:
                for k in range(inst.c - 1):
                    reg[inst.a + k] = "(%s)[%d])->" % (fn, k)
            else:
                reg.pop(inst.a, None)
            for k in range(1, (nargs if isinstance(nargs, int) else 0) + 2):
                reg.pop(inst.a + k, None)
        elif n == "RETURN":
            out.append((inst.pc, inst.offset, n, "return", inst.b - 1,
                        "multret", []))
        elif n in ("EQ", "LE", "LT", "TEST", "TESTSET", "JMP"):
            pass
        else:
            reg.pop(inst.a, None)
    return out


def main():
    gd = os.path.join(
        sys.argv[1] if len(sys.argv) > 1
        else os.path.join(ROOT, "gamedata", "mii_customizer", "P6-HAT-UI"),
        "ui", "script", "menu", "chara_make")

    def env_ups(main):
        index = {q.path: q for q in L.walk(main)}

        def origin(path, n):
            q = index[path]
            instack, idx = q.upvalues[n]
            parent = q.path.rsplit(".p", 1)[0] if ".p" in q.path else None
            return ("local", parent, idx)

        def is_env(path, n, seen=None):
            seen = seen or set()
            if (path, n) in seen:
                return False
            seen.add((path, n))
            kind, parent, idx = origin(path, n)
            if path == "main":
                return kind == "local" and idx == 0
            if kind == "local":
                return False
            return is_env(parent, idx, seen)

        return {q.path: {n for n in range(len(q.upvalues)) if is_env(q.path, n)}
                for q in L.walk(main)}

    for name in CHUNKS:
        with open(os.path.join(gd, name + ".lc"), "rb") as fh:
            hdr, main = L.load_chunk(fh.read())
        env = env_ups(main)
        print("=" * 72)
        print("==", name)
        for p in L.walk(main):
            if not any(i.name in ("CALL", "TAILCALL") for i in p.code):
                continue
            print("--- proto %s (params=%d, env_upvalues=%s)"
                  % (p.path, p.numparams, sorted(env[p.path])))
            prev = None
            for pc, off, n, fn, nargs, nres, args in analyse(p):
                print("  pc %3d @0x%04x %-9s %-58s args(%s)=%s -> %s"
                      % (pc, off, n, fn, nargs,
                         ", ".join(args) if args else "-", nres))


if __name__ == "__main__":
    main()