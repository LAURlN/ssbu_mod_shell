"""Decode ACMD implementations of the forward-tilt scripts to structured calls (v2).

Fixes over v1:
  * general symbolic loc arithmetic through sp/x29 chains
  * const loads resolve to name (constmap xxh64 table) AND value
    (const_value_table__ symbol inside the same NRO)
  * globals resolved via relocated pointer -> label (L2CValue::NIL)
  * stack pointer arrays may hold any value kind (loc or global)
  * fresh-flag registration scan (no stale x1/x2 across caller windows)

Outputs:
  gamedata/mii_customizer/moves/tilt_down__miifighter/tables/registrations.tsv  (rewritten)
  gamedata/mii_customizer/moves/tilt_down__miifighter/tables/acmd_calls.json
"""
import sys, os, struct, json, zlib, csv, re, hashlib
sys.path.insert(0, "mods/ssbu_mod_new/builds/.cache/dk_cargo/python")
sys.path.insert(0, "mods/ssbu_mod_new/tools/nro_decomp")
sys.path.insert(0, "mods/mii_customizer/scratch/2026-10-07_MV-tilt_down__miifighter")
import capstone
import nro_flatten as nf
import nro_util as u
import constmap_local as cl

def hash40(name):
    d = name.encode("utf-8")
    return (len(d) << 32) | zlib.crc32(d)

SCRIPTS = [f"{c}_{s}" for c in ("game", "effect", "sound", "expression")
           for s in ("attacklw3",)]
NAMES = {hash40(s): s for s in SCRIPTS}

LABELS = {}
with open("mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv", encoding="utf-8") as f:
    for line in f:
        p = line.strip().split(",")
        if len(p) >= 2:
            try: LABELS[int(p[0], 16)] = p[1]
            except ValueError: pass

# Enum values for const names come from the pinned skyline-smash lua_const.rs
# (a local tool install; the game-side const_value_table__E is constructed at
# runtime by construct_bind_const_value_table and is not present as bytes in
# the local lua2cpp_common.nro copy - both measured, recorded in the report).
LUA_CONST = {}
from pathlib import Path as _P
def _load_lua_const():
    cands = list((_P.home() / ".cargo/git/checkouts").glob("skyline-smash-*/**/src/lua_const.rs"))
    p = max(cands, key=lambda x: x.stat().st_mtime)
    for m in re.finditer(r"^\s+([A-Za-z_0-9]+):\s*(0x[0-9a-fA-F]+|\d+),", p.read_text(encoding="utf-8", errors="replace"), re.M):
        LUA_CONST[m.group(1)] = int(m.group(2), 0)
    return p
LUA_CONST_PATH = _load_lua_const()

NROS = {
    "miifighter": "gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miifighter.nro",
    "miigunner": "gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miigunner.nro",
}

CTOR = {
    "_ZN3lib8L2CValueC1Ei": "int",
    "_ZN3lib8L2CValueC1Eb": "bool",
    "_ZN3lib8L2CValueC1Ef": "float",
    "_ZN3lib8L2CValueC1EN3phx6Hash40E": "hash",
    "_ZN3lib8L2CValueC1Ev": "nil",
}

def disasm(img, start, size):
    md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)
    return list(md.disasm(img[start:start + size], start))

def pretty(name):
    """Partial demangler: _ZN3app10sv_animcmd5frameE... -> app::sv_animcmd::frame."""
    if not name.startswith("_Z"):
        return name
    i = 3 if name[2] == "N" else 2
    ids = []
    while i < len(name):
        m = re.match(r"(\d+)", name[i:])
        if not m:
            break
        n = int(m.group(1))
        start = i + len(m.group(1))
        ident = name[start:start + n]
        if len(ident) != n:
            break
        ids.append(ident)
        i = start + n
    return "::".join(ids) if ids else name

def last_id(name):
    return pretty(name).split("::")[-1]

_helper_cache = {}
def resolve_helper(img, plt, addr):
    """Underlying plt target of a generated variadic push thunk.

    The thunk pushes every argument then tail-calls (`b`, not `bl`) the
    sv_animcmd import; scanning must stop at the first control transfer out
    or it walks into the next generated function.
    """
    if addr in _helper_cache:
        return _helper_cache[addr]
    target = None
    for ins in disasm(img, addr, 0x600):
        if ins.mnemonic in ("bl", "b"):
            t = int(ins.op_str[1:], 0)
            if t in plt:
                name = plt[t]
                if "sv_animcmd" in name or "sv_module_access" in name:
                    target = (t, name)
                    break
            if ins.mnemonic == "b":
                break  # tail call to something not of interest / out of scope
        if ins.mnemonic in ("ret", "udf"):
            break
    _helper_cache[addr] = target
    return target

def val_to_json(v):
    """Register/slot value tuple -> JSON dict."""
    if v is None:
        return {"t": "unresolved"}
    if not isinstance(v, tuple):
        return {"t": "raw", "v": str(v)}
    k = v[0]
    if k == "int":
        return {"t": "int", "v": v[1] if v[1] < (1 << 63) else v[1] - (1 << 64)}
    if k == "float":
        return {"t": "float", "v": v[1]}
    if k == "const":
        return {"t": "const", "name": v[1], "value": v[2]}
    if k == "global":
        return {"t": "global", "symbol": v[1]}
    if k == "ptr":
        return {"t": "ptr", "addr": hex(v[1])}
    if k == "loc":
        return {"t": "slot", "slot": f"{v[1]}{v[2]:+#x}"}
    if k == "sym":
        return {"t": "sym", "v": v[1]}
    return {"t": "raw", "v": str(v)}

_VC = re.compile(r"^[vs](\d+)$")
def canon(r):
    """s0/v0 register bank: canonicalise to v<n>."""
    m = _VC.match(r)
    return "v" + m.group(1) if m else r

def decode_script(ftr, script, impl, plt, meta, img):
    rows = []
    regs = {}
    slots = {}
    sp_slots = {}
    pending = []
    frame = None
    const_base = None
    for addr_s, lbl in meta["labels"].items():
        if lbl.endswith("const_value_table__E"):
            const_base = int(addr_s, 16)
            break

    insns = disasm(img, impl, 0x8000)
    body = []
    for ins in insns:
        body.append(ins)
        if ins.mnemonic == "ret":
            break

    def setreg(r, v):
        r = canon(r)
        regs[r] = v
        if r.startswith("w"):
            regs["x" + r[1:]] = v
        elif r.startswith("x"):
            regs["w" + r[1:]] = v
        # vector regs (v/s): no 32/64 aliasing

    def getreg(r):
        r = canon(r)
        if r in regs:
            return regs[r]
        if r.startswith(("w", "x")):
            alt = ("x" + r[1:]) if r.startswith("w") else ("w" + r[1:])
            return regs.get(alt)
        return None

    def load_word(addr):
        if 0 <= addr + 4 <= len(img):
            return struct.unpack_from("<I", img, addr)[0]
        return None

    for ins in body:
        m, ops = ins.mnemonic, ins.op_str
        a = ops.split(", ")
        if m == "mov" and len(a) == 2:
            t = a[1].strip()
            t0 = t.split(".")[0]  # vector arrangement suffix: v8.16b
            if _VC.match(t0) and getreg(t0) is not None and not t.startswith("#"):
                # register-to-register move (incl. mov v0.16b, v8.16b)
                setreg(a[0].split(".")[0], getreg(t0))
            elif t.startswith("#"):
                setreg(a[0], ("int", int(t[1:], 0) & ((1 << 64) - 1)))
            elif t == "wzr" or t == "xzr":
                setreg(a[0], ("int", 0))
            elif t == "sp":
                setreg(a[0], getreg("sp") or ("loc", "sp", 0))
            elif getreg(t) is not None:
                setreg(a[0], getreg(t))
            else:
                setreg(a[0], ("sym", t))
        elif m == "fmov" and len(a) == 2:
            t = a[1]
            if t == "wzr":
                setreg(a[0], ("float", 0.0))
            elif t.startswith("#"):
                setreg(a[0], ("float", float(t[1:])))
            elif t in regs:
                v = regs[t]
                if a[0].startswith("s") and isinstance(v, tuple) and v[0] == "int":
                    setreg(a[0], ("float", struct.unpack("<f", struct.pack("<I", v[1] & 0xffffffff))[0]))
                else:
                    setreg(a[0], v)
        elif m == "movk" and len(a) >= 2:
            imm = int(a[1].lstrip("#"), 0)
            shift = int(a[2].split("#")[1]) if len(a) == 3 else 0
            cur = getreg(a[0])
            base = cur[1] if isinstance(cur, tuple) and cur[0] == "int" else 0
            base = (base & ~(0xffff << shift)) | (imm << shift)
            setreg(a[0], ("int", base))
        elif m in ("adrp", "adr") and len(a) == 2 and a[1].startswith("#"):
            setreg(a[0], ("int", int(a[1][1:], 0)))
        elif m in ("add", "sub") and len(a) == 3 and a[2].startswith("#"):
            imm = int(a[2][1:], 0) * (1 if m == "add" else -1)
            base = getreg(a[1])
            if a[1] == "sp":
                base = getreg("sp") or ("loc", "sp", 0)
            if isinstance(base, tuple) and base[0] == "loc":
                setreg(a[0], ("loc", base[1], base[2] + imm))
            elif isinstance(base, tuple) and base[0] == "int":
                setreg(a[0], ("int", (base[1] + imm) & ((1 << 64) - 1)))
            else:
                setreg(a[0], ("sym", ops))
        elif m == "sub" and len(a) == 3 and a[2].startswith("#"):
            imm = int(a[2][1:], 0)
            base = getreg(a[1])
            if isinstance(base, tuple) and base[0] == "loc":
                setreg(a[0], ("loc", base[1], base[2] - imm))
            elif isinstance(base, tuple) and base[0] == "int":
                setreg(a[0], ("int", (base[1] - imm) & ((1 << 64) - 1)))
            else:
                setreg(a[0], ("sym", ops))
        elif m == "ldr":
            mm = re.match(r"(\w+), \[(\w+)(?:, (#?[\w]+))?\]$", ops)
            if not mm:
                if a[0].startswith(("w", "x")):
                    setreg(a[0], ("sym", ops))
                continue
            dst, base_r, idx = mm.groups()
            off = None
            if idx is None:
                off = 0
            elif idx.startswith("#"):
                off = int(idx[1:], 0)
            elif idx in regs and isinstance(regs[idx], tuple) and regs[idx][0] == "int":
                off = regs[idx][1]
            # const table? only when the base register was loaded from the
            # imported const_value_table__ symbol (guards against struct loads)
            bval0 = getreg(base_r)
            if (off is not None and off % 4 == 0 and dst.startswith("w")
                    and isinstance(bval0, tuple) and bval0[0] == "const_table"):
                cn = cl.const_name(off)
                if cn is not None:
                    setreg(dst, ("const", cn, LUA_CONST.get(cn)))
                    continue
            bval = getreg(base_r)
            if off is not None and isinstance(bval, tuple) and bval[0] == "int":
                addr = (bval[1] + off) & ((1 << 64) - 1)
                if dst.startswith("s"):
                    if 0 <= addr + 4 <= len(img):
                        setreg(dst, ("float", struct.unpack_from("<f", img, addr)[0]))
                    else:
                        setreg(dst, ("sym", ops))
                elif dst.startswith("w"):
                    v = load_word(addr)
                    setreg(dst, ("int", v) if v is not None else ("mem", addr))
                else:
                    if 0 <= addr + 8 <= len(img):
                        p = struct.unpack_from("<Q", img, addr)[0]
                        lbl = meta["labels"].get(hex(p))
                        if lbl and lbl.endswith("const_value_table__E"):
                            setreg(dst, ("const_table",))
                        elif lbl:
                            setreg(dst, ("global", lbl))
                        else:
                            setreg(dst, ("ptr", p))
                    else:
                        setreg(dst, ("mem", addr))
            else:
                setreg(dst, ("sym", ops))
        elif m == "stp":
            mm = re.match(r"(\w+), (\w+), \[sp(?:, #(-?0x[0-9a-f]+|\d+))?\]$", ops)
            if mm:
                r1, r2 = mm.group(1), mm.group(2)
                off = int(mm.group(3), 0) if mm.group(3) else 0
                for k, r in ((off, r1), (off + 8, r2)):
                    v = getreg(r)
                    if isinstance(v, tuple) and v[0] in ("loc", "global", "ptr", "int"):
                        sp_slots[k] = v
        elif m == "str":
            mm = re.match(r"(\w+), \[sp(?:, #(-?0x[0-9a-f]+|\d+))?\]$", ops)
            if mm:
                r = mm.group(1)
                off = int(mm.group(2), 0) if mm.group(2) else 0
                v = getreg(r)
                if isinstance(v, tuple) and v[0] in ("loc", "global", "ptr", "int"):
                    sp_slots[off] = v
        # ---- calls ------------------------------------------------------
        if m == "bl":
            t = int(a[0].lstrip("#"), 0)
            if t in plt:
                name = plt[t]
                if name in CTOR:
                    slot = getreg("x0")
                    kind = CTOR[name]
                    if kind == "int":
                        w1 = getreg("w1")
                        if isinstance(w1, tuple) and w1[0] == "const":
                            val = {"t": "const", "name": w1[1],
                                   "value": LUA_CONST.get(w1[1])}
                        elif isinstance(w1, tuple) and w1[0] == "int":
                            v = w1[1]
                            val = {"t": "int", "v": v if v < (1 << 63) else v - (1 << 64)}
                        else:
                            val = {"t": "unresolved", "note": "int ctor"}
                    elif kind == "bool":
                        w1 = getreg("w1")
                        v = w1[1] if isinstance(w1, tuple) and w1[0] == "int" else None
                        val = {"t": "bool", "v": bool(v) if v is not None else None}
                    elif kind == "float":
                        s0 = getreg("s0")
                        v = s0[1] if isinstance(s0, tuple) and s0[0] == "float" else None
                        val = {"t": "float", "v": v}
                    elif kind == "hash":
                        x1 = getreg("x1")
                        v = x1[1] if isinstance(x1, tuple) and x1[0] == "int" else None
                        val = {"t": "hash", "v": hex(v) if v is not None else None,
                               "len": (v >> 32) if v is not None else None,
                               "crc": (v & 0xffffffff) if v is not None else None,
                               "name": LABELS.get(v) if v is not None else None}
                    else:
                        val = {"t": "nil"}
                    if isinstance(slot, tuple) and slot[0] == "loc":
                        slots[slot] = val
                elif "sv_animcmd5frame" in name or "sv_animcmd4wait" in name:
                    pushed = [slots.get(p, {"t": "unresolved"}) for p in pending]
                    kind = "frame" if "5frame" in name else "wait"
                    fv = None
                    if pushed:
                        pv = pushed[0]
                        if pv["t"] == "int":
                            fv = pv["v"]
                        elif pv["t"] == "float":
                            fv = pv["v"]
                    rows.append({"kind": kind, "addr": hex(ins.address), "frame": frame,
                                 "args": pushed, "target": pretty(name)})
                    if fv is not None:
                        frame = fv if kind == "frame" else (frame or 0) + fv
                    pending = []
                elif "is_excute" in name:
                    rows.append({"kind": "is_excute", "addr": hex(ins.address),
                                 "frame": frame, "args": [], "target": pretty(name)})
                    pending = []
                elif "sv_animcmd" in name or "sv_module_access" in name:
                    pushed = [slots.get(p, {"t": "unresolved"}) for p in pending]
                    rows.append({"kind": last_id(name),
                                 "addr": hex(ins.address), "frame": frame,
                                 "args": pushed, "target": pretty(name)})
                    pending = []
                elif "lua_bind" in name:
                    rows.append({"kind": "lua_bind", "addr": hex(ins.address),
                                 "frame": frame, "args": [], "target": pretty(name),
                                 "import": name})
                elif "push_lua_stack" in name:
                    x1 = getreg("x1")
                    if isinstance(x1, tuple) and x1[0] == "loc":
                        pending.append(x1)
                elif "clear_lua_stack" in name:
                    pending = []
            else:
                h = resolve_helper(img, plt, t)
                if h:
                    ht, hname = h
                    args = []
                    for r in ("x1", "x2", "x3", "x4", "x5", "x6", "x7"):
                        v = getreg(r)
                        if isinstance(v, tuple) and v[0] == "loc":
                            args.append(slots.get(v, {"t": "unresolved", "slot": str(v)}))
                        else:
                            args.append(val_to_json(v))
                    for off in sorted(o for o in sp_slots if 0 <= o < 0x1000):
                        v = sp_slots[off]
                        if isinstance(v, tuple) and v[0] == "loc":
                            args.append(slots.get(v, {"t": "unresolved", "slot": str(v)}))
                        else:
                            args.append(val_to_json(v))
                    rows.append({"kind": last_id(hname),
                                 "addr": hex(ins.address), "frame": frame,
                                 "args": args, "target": pretty(hname),
                                 "via_helper": hex(t)})
                else:
                    rows.append({"kind": "local_call", "addr": hex(ins.address),
                                 "frame": frame, "args": [], "target": hex(t)})
    end = body[-1].address + 4
    return {"fighter": ftr, "script": script, "impl": hex(impl),
            "impl_end": hex(end), "instructions": len(body),
            "impl_sha256": hashlib.sha256(bytes(img[impl:end])).hexdigest(),
            "calls": rows}


def main():
    out = {}
    reg_rows = []
    for ftr, path in NROS.items():
        d = open(path, "rb").read()
        img, meta = nf.flatten(d)
        plt = u.plt_map(img, meta["labels"], meta["text_end"])
        syms, rel, text_end = nf.parse(d)
        funcs = sorted([(s[3], s[4], s[0]) for s in syms if (s[1] & 0xf) == 2 and s[4] > 0])
        def owner(addr):
            for st, sz, nm in funcs:
                if st <= addr < st + sz:
                    return (nm, st, sz)
            return (None, None, None)
        stub = [a for a, n in plt.items() if "sv_set_function_hash" in n][0]
        callers = u.bl_callers(img, meta["text_end"], stub)
        seen = set()
        for c in callers:
            regs = {}
            x1_fresh = False
            x2_fresh = False
            for ins in u.disasm(img, c - 0x60, 0x64):
                args = ins.op_str.split(", ")
                op = ins.mnemonic
                if op in ("adrp", "adr") and args[0] == "x1":
                    x1_fresh = True
                    regs["x1"] = int(args[1][1:], 0)
                    continue
                if op == "add" and len(args) == 3 and args[0] == "x1" and args[2].startswith("#") and isinstance(regs.get("x1"), int):
                    regs["x1"] += int(args[2][1:], 0)
                    continue
                if op == "mov" and len(args) == 2 and args[0] == "x2" and args[1].startswith("#"):
                    x2_fresh = True
                    regs["x2"] = int(args[1][1:], 0)
                    continue
                if op == "movk" and args[0] == "x2":
                    shift = int(args[2].split("#")[1]) if len(args) == 3 else 0
                    base = regs.get("x2", 0)
                    regs["x2"] = (base & ~(0xffff << shift)) | (int(args[1][1:], 0) << shift)
                    continue
                if op == "bl" and int(args[0][1:], 0) == stub:
                    h = regs.get("x2")
                    if x2_fresh and x1_fresh and isinstance(h, int) and h in NAMES:
                        key = (NAMES[h], ins.address)
                        if key not in seen:
                            seen.add(key)
                            reg_rows.append(dict(fighter=ftr, script=NAMES[h],
                                                 script_hash=hex(h),
                                                 registration=hex(ins.address),
                                                 wrapper=hex(regs["x1"])))
        for row in [r for r in reg_rows if r["fighter"] == ftr]:
            wrapper = int(row["wrapper"], 16)
            targets = []
            wsize = None
            for ins in u.disasm(img, wrapper, 0x120):
                if ins.mnemonic == "bl":
                    t = int(ins.op_str[1:], 0)
                    if t not in plt:
                        targets.append(t)
                if ins.mnemonic == "ret" and targets:
                    wsize = ins.address + 4 - wrapper
                    break
            uniq = sorted(set(targets))
            assert len(uniq) == 1, (row, [hex(x) for x in uniq])
            row["wrapper_size"] = wsize
            row["impl"] = hex(uniq[0])
            onm, ost, osz = owner(int(row["registration"], 16))
            row["register_fn"] = onm
            row["register_fn_start"] = hex(ost) if ost else None
            row["register_fn_size"] = osz
        for row in [r for r in reg_rows if r["fighter"] == ftr]:
            res = decode_script(ftr, row["script"], int(row["impl"], 16), plt, meta, img)
            row["impl_end"] = res["impl_end"]
            row["impl_instructions"] = res["instructions"]
            row["impl_sha256"] = res["impl_sha256"]
            out[f"{ftr}/{row['script']}"] = res

    os.makedirs("gamedata/mii_customizer/moves/tilt_down__miifighter/tables", exist_ok=True)
    with open("gamedata/mii_customizer/moves/tilt_down__miifighter/tables/acmd_calls.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    keys = ["fighter", "script", "script_hash", "registration", "wrapper", "wrapper_size",
            "impl", "impl_end", "impl_instructions", "impl_sha256",
            "register_fn", "register_fn_start", "register_fn_size"]
    with open("gamedata/mii_customizer/moves/tilt_down__miifighter/tables/registrations.tsv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        w.writerows(reg_rows)
    for k in sorted(out):
        s = out[k]
        print(f"{k}: impl={s['impl']}..{s['impl_end']} n={s['instructions']} calls={len(s['calls'])}")
    print("registrations:", len(reg_rows))

if __name__ == "__main__":
    main()
