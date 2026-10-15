"""P2-STAT-API scratch probe.

Re-decodes the two parameters this task assesses (weight, walk_speed_max) out of
the pinned fighter_param.prc, independently of the P1-DATASET catalogue, and
cross-checks the Hash40 values against the pinned third-party field tables that
live in the old mod repo (read-only).

Read-only. Writes nothing. Prints its own evidence.
"""
import importlib.util
import struct
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[4]
PRC_REL = "gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


prc = load("pgwr_prc", WS / "mods/ssbu_mod_new/src/pgwr/tools/prc.py")

TARGETS = {"weight": 0x0607CD5541, "walk_speed_max": 0x0EE2EC2860}
ROW_KEY = 0x0C541EF0B2  # fighter_kind
GUNNER = 0x166E9FAE70  # hash40("fighter_kind_miigunner")


def main() -> int:
    path = WS / PRC_REL
    tree = prc.read(path)

    # the top-level node is a struct holding one list of fighter rows
    tag, top = tree
    if tag != "struct":
        print(f"FAIL: top-level node is {tag}, not a struct")
        return 1
    rows = None
    for key, node in top:
        if node[0] == "list":
            rows = node[1]
            break
    if rows is None:
        print("FAIL: no row list found")
        return 1

    hits = []
    for index, row in enumerate(rows):
        if row[0] != "struct":
            continue
        for key, node in row[1]:
            if key == ROW_KEY and node[0] == "hash" and node[1] == GUNNER:
                hits.append((index, row))
    print(f"rows in list: {len(rows)}; rows whose fighter_kind == fighter_kind_miigunner: {len(hits)}")
    if len(hits) != 1:
        print("FAIL: Gunner row is not unique")
        return 1
    index, row = hits[0]
    print(f"Gunner row index: {index}")

    ok = True
    for name, want in TARGETS.items():
        assert prc.hash40(name) == want, (name, hex(prc.hash40(name)))
        found = [(k, n) for k, n in row[1] if k == want]
        if len(found) != 1:
            print(f"FAIL {name}: {len(found)} entries with hash {want:#x}")
            ok = False
            continue
        node = found[0][1]
        value = node[1]
        bits = struct.unpack("<I", struct.pack("<f", value))[0]
        print(f"{name}: hash {want:#011x} recomputed hash40 match, type {node[0]}, "
              f"value {value!r}, f32 bits {bits:#010x}")

    # Cross-check: the pinned third-party field tables in the old mod repo carry the
    # same Hash40 for the same two names in the fighter_param row.
    row_tbl = (WS / "mods/ssbu_mod_new/src/mgw_standalone/vendor/ssbu_clone_engine/"
               "clone_engine_core/src/fighter_param_row_table.rs").read_text()
    for name, want in TARGETS.items():
        line = [l for l in row_tbl.splitlines() if f'"{name}"' in l]
        if len(line) != 1:
            print(f"FAIL {name}: {len(line)} lines in the pinned fighter_param row table")
            ok = False
            continue
        text = line[0]
        got = int(text.split("hash: ")[1].split(",")[0], 16)
        off = int(text.split("offset: ")[1].split(",")[0], 16)
        agree = got == want
        print(f"{name}: pinned row table hash {got:#011x} "
              f"{'AGREES' if agree else 'DISAGREES'} with hash40, row offset {off:#x}")
        ok = ok and agree

    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
