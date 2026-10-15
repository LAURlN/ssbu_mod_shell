"""Render the Q2 (i32) and Q4 (bool/hash) tables as markdown, and print a
compact console view for the report author.

  python make_tables.py            # writes int_table.md / others_table.md
                                   # under gamedata/mii_customizer/P11-INT-PARAMS/
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
OUT = os.path.join(ROOT, "gamedata", "mii_customizer", "P11-INT-PARAMS")

int_doc = json.load(open(os.path.join(OUT, "int_table.json"), encoding="utf-8"))
oth_doc = json.load(open(os.path.join(OUT, "others_table.json"), encoding="utf-8"))


def label(rec):
    if rec["name_hash_verified"] and rec["name"]:
        return rec["name"]
    if rec["name"]:
        return "%s (unlabelled)" % rec["name"]
    return "(unlabelled)"


def disp_cell(rec):
    d = rec["displacements"]
    if not d:
        return "-"
    return ", ".join("%s x%d" % (k, v) for k, v in sorted(d.items()))


def classes_cell(rec):
    c = rec["classes"]
    return ", ".join("%s x%d" % (k, v) for k, v in sorted(c.items())) or "-"


def x2_cell(rec):
    out = []
    for s in rec.get("sites_250", []):
        imm = s.get("x2_immediate")
        txt = s.get("x2_text") or "?"
        out.append("0x%x: %s" % (s["site"], ("imm " + str(imm)) if imm is not None
                                 else ("'" + txt + "' (not imm)")))
    return "; ".join(out) if out else "-"


# ---------------------------------------------------------------- Q2 table
lines = []
lines.append("# P11-INT-PARAMS Q2 - integer (i32) fighter_param fields")
lines.append("")
lines.append("Source: `int_table.json` (same folder); image and table hashes are")
lines.append("pinned in `sites_int.json`. All values offline (tier B).")
lines.append("")
lines.append("| # | field | hash | sites | via +0x250 | x2 at the +0x250 site(s) |")
lines.append("|---|---|---|---|---|---|")
for i, r in enumerate(int_doc["rows"], 1):
    lines.append("| %d | %s | `%s` | %d | %d | %s |" % (
        i, label(r), r["hash"], r["code_sites"], r["via_0x250"], x2_cell(r)))
lines.append("")
lines.append("Displacement / class histogram per field, and value statistics:")
lines.append("")
lines.append("| # | field | classes | displacements | Mii Gunner | min | max | distinct | qualifies |")
lines.append("|---|---|---|---|---|---|---|---|---|")
for i, r in enumerate(int_doc["rows"], 1):
    v = r["values"]
    lines.append("| %d | %s | %s | %s | %s | %s | %s | %d | %s |" % (
        i, label(r), classes_cell(r), disp_cell(r), v["miigunner"], v["min"],
        v["max"], v["distinct"], "yes" if r["qualifies"] else "no"))
lines.append("")
lines.append("Qualifying rule (same as the floats, P10): integer type, at least one")
lines.append("+0x250 site with x2 == 0, and the value differs between fighters.")
lines.append("")
with open(os.path.join(OUT, "int_table.md"), "w", encoding="utf-8",
          newline="\n") as fh:
    fh.write("\n".join(lines))

# ---------------------------------------------------------------- Q4 table
lines = []
lines.append("# P11-INT-PARAMS Q4 - bool and hash fields: which getter slot")
lines.append("")
lines.append("Source: `others_table.json` (same folder). Site counts and the")
lines.append("displacement of the feeding `ldr` at the first call after the hash")
lines.append("composition (P4 method). All values offline (tier B).")
lines.append("")
lines.append("| field | hash | type | sites | displacements (slot x count) |")
lines.append("|---|---|---|---|---|")
for r in oth_doc["rows"]:
    lines.append("| %s | `%s` | %s | %d | %s |" % (
        label(r), r["hash"], r["type"], r["code_sites"], disp_cell(r)))
lines.append("")
with open(os.path.join(OUT, "others_table.md"), "w", encoding="utf-8",
          newline="\n") as fh:
    fh.write("\n".join(lines))

# ------------------------------------------------------- +0x250 site detail
import capstone
import capstone.arm64

IMAGE = os.path.join(ROOT, "gamedata", "ssbu-13.0.4", "main.bin")
img = open(IMAGE, "rb").read()
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

READ_FIRST = {"cmp", "cmn", "tst", "str", "strb", "strh", "stp",
              "stur", "sturb", "sturh", "cbz", "cbnz", "tbz", "tbnz",
              "ccmp", "tst"}


def first_result_read(call_addr):
    """First instruction after the call that READs w0 or x0 (dest-position
    operands of writer instructions do not count)."""
    for ins in md.disasm(img[call_addr + 4:call_addr + 4 + 64], call_addr + 4):
        if ins.mnemonic in ("bl", "blr", "ret", "b"):
            return None
        toks = ins.op_str.replace(",", " ").split()
        for idx, t in enumerate(toks):
            if t in ("w0", "x0") and (idx >= 1 or ins.mnemonic in READ_FIRST):
                return ins.address, "%s %s" % (ins.mnemonic, ins.op_str)
    return None


lines = []
lines.append("# P11-INT-PARAMS - every +0x250 site of the i32 fields, in detail")
lines.append("")
lines.append("Site = movz seed of the hash40 composition; producer = the feeding")
lines.append("`ldr` that loads the call target from vtable slot +0x250; x2 = the")
lines.append("closest x2 writer within 8 instructions of the call (P4 rule);")
lines.append("return use = first instruction reading w0/x0 after the call.")
lines.append("")
lines.append("| field | site | producer | call | x2 at the call | return use |")
lines.append("|---|---|---|---|---|---|")
for r in int_doc["rows"]:
    for s in r.get("sites_250", []):
        p = s["producer"]
        ru = first_result_read(s["call"]["addr"])
        lines.append("| %s | `0x%x` | `0x%x` `%s` | `0x%x` | %s `%s` | %s |" % (
            label(r), s["site"], p["addr"], p["text"], s["call"]["addr"],
            ("imm %s" % s["x2_immediate"]) if s["x2_immediate"] is not None
            else "not imm",
            s["x2_text"],
            ("`0x%x` `%s`" % ru) if ru else "none in 16 insns"))
lines.append("")
with open(os.path.join(OUT, "sites250.md"), "w", encoding="utf-8",
          newline="\n") as fh:
    fh.write("\n".join(lines))

# ------------------------------------------------------------- console view
print("=== Q2: i32 fields ===")
print("%-30s %5s %6s %-40s %-40s mii min max dist q" % (
    "field", "sites", "+250", "classes", "displacements"))
for r in int_doc["rows"]:
    v = r["values"]
    print("%-30s %5d %6d %-40s %-40s %s %s %s %d %s" % (
        (r["name"] or r["hash"]), r["code_sites"], r["via_0x250"],
        classes_cell(r), disp_cell(r), v["miigunner"], v["min"], v["max"],
        v["distinct"], "Y" if r["qualifies"] else "n"))

print("\n=== +0x250 sites detail ===")
for r in int_doc["rows"]:
    if r["sites_250"]:
        for s in r["sites_250"]:
            print("%-30s site 0x%x  x2=%s (%s)  producer=%s" % (
                (r["name"] or r["hash"]), s["site"], s["x2_immediate"],
                s["x2_text"], (s["producer"] or {}).get("text")))

print("\n=== Q4: bool/hash fields ===")
print("%-36s %-5s %5s %s" % ("field", "type", "sites", "displacements"))
for r in oth_doc["rows"]:
    print("%-36s %-5s %5d %s" % (
        (r["name"] or r["hash"]), r["type"], r["code_sites"], disp_cell(r)))

print("\nwrote %s/int_table.md, %s/others_table.md" % (OUT, OUT))
