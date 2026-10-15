"""P8-LUA-LIST derivation scratch (NOT a deliverable).

Reads the two target chunks plus common/ui_common and derives, from the bytes:
  * every global (_ENV) read / write per chunk
  * every SELF (method) call site, with nargs / nres
  * every UiScriptPlayer.invoke bridge site, with nargs / nres / args
  * back-traced argument provenance for every call site

Writes derived.json + callflow.txt next to this file.
"""
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "mods", "mii_customizer", "tools",
                                "lua53-inspect"))
import lua53_inspect as L  # noqa: E402

GD = os.path.join(ROOT, "gamedata", "mii_customizer", "P8-LUA-LIST",
                  "ui", "script")
CHUNKS = {
    "collection_tips_list":
        os.path.join(GD, "menu", "collection", "collection_tips_list.lc"),
    "option_button_top":
        os.path.join(GD, "menu", "option", "option_button_top.lc"),
    "ui_common":
        os.path.join(GD, "common", "ui_common.lc"),
}
BRIDGE_TABLE = "UiScriptPlayer"
BRIDGE_METHOD = "invoke"


# --------------------------------------------------------------------------
# _ENV resolution
# --------------------------------------------------------------------------
def build_env_index(main):
    """proto.path -> upvalue index holding _ENV, or None.

    An upvalue descriptor (instack, idx) with instack == 0 means "parent
    closure's register idx". main's register 0 is what the loader installed as
    the environment, so we walk parents looking for register 0.
    """
    index = {main.path: 0}
    for p in main.iter_protos():
        index.setdefault(p.path, None)
    parent_of = {}
    for p in main.iter_protos():
        for ch in p.protos:
            parent_of[id(ch)] = p
    for p in main.iter_protos():
        if p is main:
            continue
        par = parent_of[id(p)]
        for i, (instack, ridx) in enumerate(p.upvalues):
            if instack:
                continue
            if ridx == 0 and par is main:
                index[p.path] = i
                break
            if ridx < len(par.upvalues):
                pinc, pidx = par.upvalues[ridx]
                if not pinc:
                    continue
                # the parent took register ridx from the grandparent chain;
                # only register 0 of main is the environment
                if par is main:
                    index[p.path] = i
                    break
    return index


# --------------------------------------------------------------------------
# back-tracer: who wrote register r before pc p?
# --------------------------------------------------------------------------
WRITERS = {
    "MOVE", "LOADK", "LOADBOOL", "LOADNIL", "LOADKX", "GETTABUP", "GETTABLE",
    "SELF", "CALL", "TAILCALL", "CLOSURE", "NEWTABLE", "ADD", "SUB", "MUL",
    "DIV", "MOD", "POW", "UNM", "NOT", "LEN", "CONCAT", "LOADTRUE",
    "LOADFALSE", "TFORCALL", "VARARG", "EXTRAARG",
}


def describe(p, ins, env_idx):
    """Human text for one instruction."""
    k = ins.rk(p, "C")
    if ins.name in ("GETTABUP", "SETTABUP"):
        raw = ins.b
        up = ("up[%d]=_ENV" % raw if raw == env_idx and ins.name == "GETTABUP"
              else "up[%d]" % raw)
        return "%s %s[%s]" % (ins.name, up, k)
    if ins.name == "GETTABLE":
        return "R[%d][%s]" % (ins.b, k)
    if ins.name == "LOADK":
        return "K[%d]=%s" % (ins.bx, p.constants[ins.bx].text(48))
    if ins.name == "LOADBOOL":
        return "%s" % ("True" if ins.b else "False")
    if ins.name == "SELF":
        return "R[%d].%s" % (ins.b, k)
    if ins.name in ("CALL", "TAILCALL"):
        return "call r[%d..%d] %d arg" % (ins.a, ins.a + ins.b - 1,
                                          ins.b - 1)
    if ins.name in ("ADD", "SUB", "MUL", "DIV", "MOD", "POW"):
        return "%s(R[%d],%s)" % (ins.name, ins.b, k)
    return ins.name


def trace_arg(p, pc, reg, env_idx):
    """Walk back from pc to find what last wrote register reg."""
    for j in range(pc - 1, max(-1, pc - 14), -1):
        ins = p.code[j]
        if ins.name in WRITERS and ins.sets_a and reg >= ins.a:
            # crude range check: for multi-register writes require containment
            span = 1
            if ins.name in ("LOADNIL", "MOVE", "GETTABLE", "LOADK",
                            "LOADBOOL", "CLOSURE", "SELF", "NEWTABLE",
                            "GETTABUP", "SETTABUP", "CALL", "TFORCALL"):
                span = ins.b + 1 if ins.name == "LOADNIL" else 1
            if reg - ins.a < span:
                return "pc%d: %s" % (j, describe(p, ins, env_idx))
    return "?"


# --------------------------------------------------------------------------
# call-site discovery
# --------------------------------------------------------------------------
def consuming_call(p, i, areg):
    """First CALL/TAILCALL at pc > i whose A == areg, stopping at a join."""
    for j in range(i + 1, min(len(p.code), i + 12)):
        nxt = p.code[j]
        if nxt.name in ("CALL", "TAILCALL") and nxt.a == areg:
            return j
        if nxt.branch_target() is not None and j > i:
            break
    return None


def method_sites(main, env_idx):
    out = []
    for p in main.iter_protos():
        e = env_idx.get(p.path)
        for i, ins in enumerate(p.code):
            if ins.name != "SELF":
                continue
            ci = ins.c if (ins.c & L.BITRK) else -1
            ci = ins.c & ~L.BITRK
            if not (ins.c & L.BITRK) or ci >= len(p.constants):
                continue
            if not p.constants[ci].is_string:
                continue
            cp = consuming_call(p, i, ins.a)
            if cp is None:
                continue
            c = p.code[cp]
            # CALL B == 0 means "up to L->top" (lopcodes.h:250-253): the tool
            # must not invent a count there.
            nargs = "0*" if c.b == 0 else c.b - 2
            nres = "0*" if c.c == 0 else c.c - 1
            out.append({
                "proto": p.path, "self_pc": i, "call_pc": cp,
                "method": p.constants[ci].value,
                "receiver": "R[%d]" % ins.b if not (ins.b & L.BITRK) else
                            p.constants[ins.b & ~L.BITRK].text(40),
                "nargs": nargs, "nres": nres,
                "call_b": c.b, "call_c": c.c,
                "args": ([] if c.b == 0 else
                         [trace_arg(p, cp, ins.a + 2 + k, e)
                          for k in range(c.b - 2)]),
                "env_index": e,
            })
    return out


def bridge_sites(main, env_idx):
    out = []
    for p in main.iter_protos():
        e = env_idx.get(p.path)
        for i, ins in enumerate(p.code):
            if ins.name != "GETTABUP" or ins.b != e or \
                    not (ins.c & L.BITRK):
                continue
            ti = ins.c & ~L.BITRK
            if ti >= len(p.constants) or \
                    p.constants[ti].value != BRIDGE_TABLE:
                continue
            for j in range(i + 1, min(len(p.code), i + 6)):
                g = p.code[j]
                if g.name != "GETTABLE" or g.b != ins.a or \
                        not (g.c & L.BITRK):
                    continue
                mi = g.c & ~L.BITRK
                if mi >= len(p.constants) or \
                        p.constants[mi].value != BRIDGE_METHOD:
                    continue
                cp = consuming_call(p, j, g.a)
                if cp is None:
                    continue
                c = p.code[cp]
                out.append({
                    "proto": p.path, "table_pc": i, "method_pc": j,
                    "call_pc": cp, "name_arg": c.a + 1,
                    "call_b": c.b, "call_c": c.c,
                    "nargs": "0*" if c.b == 0 else c.b - 1,
                    "nres": "0*" if c.c == 0 else c.c - 1,
                    "name": trace_arg(p, cp, c.a + 1, e),
                    "args": ([] if c.b == 0 else
                             [trace_arg(p, cp, c.a + 1 + k, e)
                              for k in range(1, c.b - 1)]),
                })
                break
    return out


def string_consts(main, needle):
    """Every string constant containing needle, per proto."""
    hits = []
    for p in main.iter_protos():
        for k in p.constants:
            if k.is_string and needle in (k.value or ""):
                hits.append([p.path, k.index, k.value])
    return hits


def global_reads(main, env):
    """GETTABUP _ENV[K] reads: (proto, pc, name)."""
    out = []
    for p in main.iter_protos():
        e = env.get(p.path)
        if e is None:
            continue
        for ins in p.code:
            if ins.name == "GETTABUP" and ins.b == e and (ins.c & L.BITRK):
                ci = ins.c & ~L.BITRK
                if ci < len(p.constants) and p.constants[ci].is_string:
                    out.append([p.path, ins.pc, p.constants[ci].value])
    return out


def global_writes(main, env):
    """SETTABUP _ENV[K] := ... writes: (proto, pc, name).

    Operand order differs from GETTABUP: SETTABUP is ``up[A][K[B]] := RK[C]``
    (lopcodes.h), so the *upvalue* is A and the *constant* is B.
    """
    out = []
    for p in main.iter_protos():
        e = env.get(p.path)
        if e is None:
            continue
        for ins in p.code:
            if ins.name == "SETTABUP" and ins.a == e and (ins.b & L.BITRK):
                ci = ins.b & ~L.BITRK
                if ci < len(p.constants) and p.constants[ci].is_string:
                    if ins.c & L.BITRK:
                        vi = ins.c & ~L.BITRK
                        val = (p.constants[vi].text(48)
                               if vi < len(p.constants) else "K[?]")
                    else:
                        val = "R[%d]" % ins.c
                    out.append([p.path, ins.pc, p.constants[ci].value, val])
    return out


def main_run():
    result = {}
    lines = []
    for name, path in CHUNKS.items():
        with open(path, "rb") as fh:
            data = fh.read()
        hdr, main = L.load_chunk(data)
        env = build_env_index(main)
        reads = global_reads(main, env)
        writes = global_writes(main, env)
        msites = method_sites(main, env)
        bridges = bridge_sites(main, env)
        protos = [p.path for p in main.iter_protos()]
        result[name] = {
            "sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
            "protos": protos, "reads": reads, "writes": writes,
            "methods": msites, "invokes": bridges,
            "env_index": env,
        }
        lines.append("=== %s  %d bytes  %d protos  %d instrs" %
                     (name, len(data), len(protos),
                      sum(len(p.code) for p in main.iter_protos())))
        lines.append("-- _ENV upvalue index per proto: %s" %
                     ", ".join("%s=%s" % (k, env.get(k))
                               for k in protos))
        lines.append("-- global WRITES (%d)" % len(writes))
        for w in writes:
            lines.append("   %s pc%d  %s := %s" %
                         (w[0], w[1], w[2], w[3]))
        lines.append("-- distinct global READS (%d)" %
                     len(sorted({r[2] for r in reads})))
        lines.append("   " + ", ".join(sorted({r[2] for r in reads})))
        lines.append("-- SELF sites (%d)" % len(msites))
        for m in msites:
            lines.append("   %-10s pc%-4d %s:%s  %s.%s  nargs=%s nres=%s  "
                         "args=[%s]" %
                         (m["proto"], m["self_pc"],
                          "pc%d" % m["self_pc"], "pc%d" % m["call_pc"],
                          m["receiver"], m["method"], m["nargs"], m["nres"],
                          "; ".join(m["args"])))
        lines.append("-- UiScriptPlayer.invoke sites (%d)" % len(bridges))
        for b in bridges:
            lines.append("   %-10s pc%d/pc%d/pc%d  invoke nargs=%s nres=%s  "
                         "name=%s  args=[%s]" %
                         (b["proto"], b["table_pc"], b["method_pc"],
                          b["call_pc"], b["nargs"], b["nres"], b["name"],
                          "; ".join(b["args"])))
        lines.append("")
    with open(os.path.join(HERE, "derived.json"), "w",
              encoding="utf-8") as fh:
        json.dump(result, fh, indent=1, sort_keys=True)
    with open(os.path.join(HERE, "callflow.txt"), "w",
              encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("\n".join(lines))


main_run()