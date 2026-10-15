#!/usr/bin/env python3
"""Derive per-chunk global reads/writes, invoke sites and call argument counts
for the four P6-HAT-UI chunks.

Reads only the extracted chunks; writes nothing (prints JSON on stdout).

Upvalue resolution is done properly: each upvalue descriptor is either
``instack=1, idx=k`` (the parent's local R[k]) or ``instack=0, idx=k`` (the
parent's upvalue k), so a GETTABUP/SETTABUP with ``B=0`` is only a *global*
access when that chain ends at the main chunk's own upvalue 0, which is
``_ENV`` by construction (lundump.c's ``LoadFunction`` gives the main closure
exactly one upvalue and the loader binds it to the globals table).
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MOD = os.path.normpath(os.path.join(HERE, "..", ".."))      # mods/mii_customizer
ROOT = os.path.normpath(os.path.join(MOD, "..", ".."))      # workspace root
sys.path.insert(0, os.path.join(MOD, "tools", "lua53-inspect"))

import lua53_inspect as L  # noqa: E402

CHUNKS = [
    "make_mii_hat_actor",
    "make_mii_hat_body_layout",
    "make_mii_utility",
    "make_mii_body_actor",
]


def build_index(main):
    return {p.path: p for p in L.walk(main)}


def up_origin(index, path, n):
    """Where does ``path``'s upvalue ``n`` come from, as a label string."""
    p = index[path]
    instack, idx = p.upvalues[n]
    parent = p.path.rsplit(".p", 1)[0] if ".p" in p.path else None
    if instack:
        return ("local", parent, idx)
    return ("upvalue", parent, idx)


def resolve_env(index, path, n, seen=None):
    """True when ``path``'s upvalue ``n`` is the main chunk's ``_ENV``.

    The main chunk's single upvalue is described as ``instack=1, idx=0``:
    the enclosing scope of a loaded chunk is the loader, whose R[0] is the
    globals table, so that descriptor *is* ``_ENV``. Every other proto's
    descriptors refer to the parent's registers or the parent's upvalues and
    are followed until the chain reaches that one.
    """
    seen = seen or set()
    key = (path, n)
    if key in seen:
        return False
    seen.add(key)
    kind, parent, idx = up_origin(index, path, n)
    if path == "main":
        return kind == "local" and idx == 0
    if kind == "local":
        return False
    return resolve_env(index, parent, idx, seen)


def kdesc(p, raw):
    if raw >= L.BITRK:
        return repr(p.constants[raw & ~L.BITRK].value)
    return "R[%d]" % raw


def main() -> None:
    gd = os.path.join(
        sys.argv[1] if len(sys.argv) > 1
        else os.path.join(ROOT, "gamedata", "mii_customizer", "P6-HAT-UI"),
        "ui", "script", "menu", "chara_make")
    out = {}
    for name in CHUNKS:
        with open(os.path.join(gd, name + ".lc"), "rb") as fh:
            data = fh.read()
        hdr, main = L.load_chunk(data)
        index = build_index(main)
        info = {"globals_read": {}, "globals_written": {}, "invokes": [],
                "calls": [], "protos": [], "n_env_upvalues": {}}
        for p in L.walk(main):
            info["protos"].append({
                "path": p.path, "code": len(p.code), "consts": len(p.constants),
                "params": p.numparams, "maxstack": p.maxstacksize,
                "nups": len(p.upvalues),
                "env_upvalues": [n for n in range(len(p.upvalues))
                                 if resolve_env(index, p.path, n)],
            })
            for inst in p.code:
                # GETTABUP uses B as the upvalue index, SETTABUP uses A
                up_idx = inst.b if inst.name == "GETTABUP" else inst.a
                if inst.name in ("GETTABUP", "SETTABUP") \
                        and up_idx < len(p.upvalues) \
                        and resolve_env(index, p.path, up_idx):
                    site = "%s pc=%d @0x%04x" % (p.path, inst.pc, inst.offset)
                    if inst.name == "GETTABUP":
                        # R(A) := UpValue[B][RK(C)]  -- lopcodes.h:179
                        key = p.constants[inst.c & ~L.BITRK].value \
                            if inst.c >= L.BITRK else "R[%d]" % inst.c
                        info["globals_read"].setdefault(key, []).append(site)
                    else:
                        # UpValue[A][RK(B)] := RK(C)  -- lopcodes.h:181
                        key = p.constants[inst.b & ~L.BITRK].value \
                            if inst.b >= L.BITRK else "R[%d]" % inst.b
                        info["globals_written"].setdefault(key, []).append(
                            "%s = %s" % (site, kdesc(p, inst.c)))
                if inst.name in ("CALL", "TAILCALL"):
                    info["calls"].append({
                        "proto": p.path, "pc": inst.pc,
                        "offset": "0x%04x" % inst.offset, "op": inst.name,
                        "func": "R[%d]" % inst.a,
                        "nargs": inst.b - 1 if inst.b else "multret",
                        "nres": inst.c - 1 if inst.c else "multret",
                    })

        # invoke sites: GETTABLE <x>.invoke, then the next CALL/TAILCALL
        for p in L.walk(main):
            for i, inst in enumerate(p.code):
                if inst.name != "GETTABLE":
                    continue
                if p.constants[inst.c & ~L.BITRK].value != "invoke" \
                        if inst.c >= L.BITRK else True:
                    continue
                src = ("R[%d]" % inst.b) if inst.b < L.BITRK \
                    else repr(p.constants[inst.b & ~L.BITRK].value)
                # resolve the source register's provenance inside this proto
                call = None
                for j in range(i + 1, min(i + 10, len(p.code))):
                    if p.code[j].name in ("CALL", "TAILCALL"):
                        call = p.code[j]
                        break
                bridge = None
                if call is not None:
                    for j in range(call.pc - 1, i, -1):
                        ins = p.code[j]
                        if ins.a == call.a + 1 and ins.name == "LOADK":
                            bridge = p.constants[ins.bx].value
                            break
                # argument 2 provenance (one instruction before the bridge LOADK
                # is usually the argument itself)
                info["invokes"].append({
                    "proto": p.path, "gettable_pc": inst.pc,
                    "src": src, "call_pc": call.pc if call else None,
                    "offset": "0x%04x" % call.offset if call else None,
                    "bridge": bridge,
                    "nargs": (call.b - 1) if call else None,
                    "nres": (call.c - 1) if call else None,
                    "raw": " ".join(
                        "%d:%s %s" % (x.pc, x.name, x.args_text())
                        for x in p.code[i:call.pc + 1]) if call else "",
                })
        out[name] = info
    print(json.dumps(out, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()