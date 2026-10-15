#!/usr/bin/env python3
"""MV-tilt_up__snake: decode the donor's four ACMD scripts for attack_hi3 from lua2cpp_snake.nro.

Reuses the P12 decoder (decode_acmd.py) by import, as the neutral-B unit does; only the script
names, the NRO and the output folder differ. Run from the workspace root (the P12 decoder finds capstone by relative path):
    python -I mods/mii_customizer/scratch/2026-10-08_MV-tilt_up__snake/decode_unit.py
Writes gamedata/mii_customizer/moves/tilt_up__snake/tables/acmd_calls.json and registrations.tsv.
"""
import csv
import json
import os
import sys

P12_DIR = "mods/mii_customizer/scratch/2026-10-07_P12-FTILT-FACTS"
sys.path.insert(0, P12_DIR)
import decode_acmd as d  # noqa: E402
import nro_flatten as nf  # noqa: E402
import nro_util as u  # noqa: E402

UNIT_DIR = "gamedata/mii_customizer/moves/tilt_up__snake"
SNAKE_NRO = "gamedata/mii_customizer/moves/special_neutral__snake/prebuilt;/nro/release/lua2cpp_snake.nro"
OUT = os.path.join(UNIT_DIR, "tables")
NAMES_WANTED = ["game_attackhi3", "effect_attackhi3", "sound_attackhi3", "expression_attackhi3"]


def main():
    d.NAMES = {d.hash40(n): n for n in NAMES_WANTED}
    d.NROS = {"snake": SNAKE_NRO}
    out, reg_rows = {}, []
    data = open(SNAKE_NRO, "rb").read()
    img, meta = nf.flatten(data)
    plt = u.plt_map(img, meta["labels"], meta["text_end"])
    syms, rel, text_end = nf.parse(data)
    funcs = sorted([(s[3], s[4], s[0]) for s in syms if (s[1] & 0xf) == 2 and s[4] > 0])

    def owner(addr):
        for st, sz, nm in funcs:
            if st <= addr < st + sz:
                return (nm, st, sz)
        return (None, None, None)

    stub = [a for a, n in plt.items() if "sv_set_function_hash" in n][0]
    seen = set()
    for c in u.bl_callers(img, meta["text_end"], stub):
        regs, x1_fresh, x2_fresh = {}, False, False
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
                if x2_fresh and x1_fresh and isinstance(h, int) and h in d.NAMES:
                    key = (d.NAMES[h], ins.address)
                    if key not in seen:
                        seen.add(key)
                        reg_rows.append(dict(fighter="snake", script=d.NAMES[h], script_hash=hex(h),
                                             registration=hex(ins.address), wrapper=hex(regs["x1"])))
    for row in reg_rows:
        wrapper = int(row["wrapper"], 16)
        targets, wsize = [], None
        for ins in u.disasm(img, wrapper, 0x120):
            if ins.mnemonic == "bl":
                t = int(ins.op_str[1:], 0)
                if t not in plt:
                    targets.append(t)
            if ins.mnemonic == "ret" and targets:
                wsize = ins.address + 4 - wrapper
                break
        uniq = sorted(set(targets))
        row["wrapper_size"] = wsize
        row["wrapper_targets"] = [hex(x) for x in uniq]
        if len(uniq) != 1:
            row["impl"] = None
            print(f"AMBIGUOUS wrapper for {row['script']} at {row['wrapper']}: {row['wrapper_targets']}")
            continue
        row["impl"] = hex(uniq[0])
        onm, ost, osz = owner(int(row["registration"], 16))
        row["register_fn"] = onm
        row["register_fn_start"] = hex(ost) if ost else None
        row["register_fn_size"] = osz
    for row in [r for r in reg_rows if r.get("impl")]:
        res = d.decode_script("snake", row["script"], int(row["impl"], 16), plt, meta, img)
        row["impl_end"] = res["impl_end"]
        row["impl_instructions"] = res["instructions"]
        row["impl_sha256"] = res["impl_sha256"]
        out[row["script"]] = res
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "acmd_calls.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    keys = ["fighter", "script", "script_hash", "registration", "wrapper", "wrapper_size", "impl",
            "impl_end", "impl_instructions", "impl_sha256", "register_fn", "register_fn_start", "register_fn_size"]
    with open(os.path.join(OUT, "registrations.tsv"), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        w.writerows(reg_rows)
    for r in reg_rows:
        print(r["script"], r["script_hash"], "reg", r["registration"], "impl", r.get("impl"), "end", r.get("impl_end"))
    print("registrations:", len(reg_rows), "decoded:", len(out))


if __name__ == "__main__":
    main()
