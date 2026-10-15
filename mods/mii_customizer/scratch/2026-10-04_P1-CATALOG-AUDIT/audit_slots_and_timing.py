"""P1-CATALOG-AUDIT: pin raw bytes for representative Gunner motion entries and
test the reader's `cancel` interpretation against a fighter whose decoded field
names are known (GameWatch, dumps/scripts/gamewatch_motion_list.yml).

Read-only. Imports the shared reader mods/ssbu_mod_new/src/pgwr/tools/mlist.py
without modifying it, per the prompt's "do not rewrite shared motion-list tools".

Usage: python -B mods/mii_customizer/scratch/2026-10-04_P1-CATALOG-AUDIT/audit_slots_and_timing.py
"""
import hashlib
import importlib.util
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "mods/ssbu_mod_new/src"))

spec = importlib.util.spec_from_file_location(
    "mlist", ROOT / "mods/ssbu_mod_new/src/pgwr/tools/mlist.py")
mlist = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mlist)


def h40(name):
    return mlist.hash40(name)


def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse_yaml_extra(path):
    """Pull kind -> (game_script, cancel_frame) out of the decoded GameWatch yml.

    Deliberately minimal: only the two fields this audit compares against.
    """
    text = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    out, cur, script, cancel = {}, None, None, None
    for line in text:
        if line.startswith("  ") and not line.startswith("   ") and line.rstrip().endswith(":"):
            cur, script, cancel = line.strip()[:-1], None, None
        elif cur and line.strip().startswith("game_script:"):
            script = line.split(":", 1)[1].strip()
        elif cur and line.strip().startswith("cancel_frame:"):
            cancel = int(line.split(":", 1)[1].strip())
            out[cur] = (script, cancel)
    return out


def show(ml, label, names, evidence):
    print(f"\n===== {label} =====")
    print("file:", ml["path"])
    for n in names:
        try:
            e = mlist.find(ml, n)
        except KeyError as exc:
            print(f"  {n}: ABSENT ({exc})")
            continue
        raw = e["raw"]
        print(f"\n  -- {n}")
        print(f"     index          : {ml['entries'].index(e)}")
        print(f"     entry offsets  : start={e['start']} end={e['end']} len={len(raw)}")
        print(f"     kind hash      : {e['kind']:#011x}")
        print(f"     game_script    : {e['gs']:#011x}")
        print(f"     flags u16 @16  : {e['flags']:#06x}")
        print(f"     blend  u8  @18 : {e['blend']}")
        print(f"     n_anims u8 @19 : {e['n']}")
        print(f"     size   u32 @20 : {e['size']}")
        print(f"     anims          : {[format(a, '#011x') for a in e['anims']]}")
        print(f"     reader cancel  : {e['cancel']}")
        tail = raw[24:]
        print(f"     tail bytes ({len(tail)}): {tail.hex(' ')}")
        # Every u16 and u32 read inside the tail, so no field is guessed by position.
        u16s = {i: struct.unpack_from("<H", tail, i)[0] for i in range(0, len(tail) - 1, 2)}
        print(f"     tail u16 reads : {dict(sorted(u16s.items()))}")
        u32s = {i: struct.unpack_from("<I", tail, i)[0] for i in range(0, len(tail) - 3, 4)}
        print(f"     tail u32 reads : {dict(sorted(u32s.items()))}")
        print(f"     size % 8        : {e['size'] % 8}")
        if n in evidence:
            gs_name, gs_cancel = evidence[n]
            gs_want = h40(gs_name) if gs_name else None
            print(f"     yml game_script: {gs_name} -> {gs_want:#011x}"
                  if gs_want else "     yml game_script: -")
            print(f"     yml cancel     : {gs_cancel}")
            if gs_want is not None:
                print(f"     gs hash match  : {gs_want == e['gs']}")
            if gs_cancel is not None:
                print(f"     cancel match   : {gs_cancel == e['cancel']}")


GUN = ROOT / "gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin"
GWC = ROOT / "gamedata/ssbu-13.0.4/files/fighter/gamewatch/motion/body/c00/motion_list.bin"
YML = ROOT / "mods/ssbu_mod_new/dumps/scripts/gamewatch_motion_list.yml"

REPRESENTATIVE = [
    "attack_11",      # jab
    "attack_hi3",     # up tilt
    "attack_s3_s",    # side/forward tilt candidate
    "attack_s4_s",    # forward smash (the reported 334)
    "attack_air_hi",  # the reported 318
    "attack_lw4",     # a non-suspicious smash for contrast
]

if __name__ == "__main__":
    print("### inputs")
    for p in (GUN, GWC):
        print(f"  {p.relative_to(ROOT)}  sha256={sha256(p)}")

    gun = mlist.parse(GUN)
    gw = mlist.parse(GWC)
    print(f"\n  Gunner entries: {len(gun['entries'])}   GameWatch entries: {len(gw['entries'])}")
    print(f"  Gunner round-trip equal: {mlist.encode(gun) == gun['data']}")
    print(f"  GameWatch round-trip equal: {mlist.encode(gw) == gw['data']}")

    ev = parse_yaml_extra(YML)
    show(gun, "Gunner body c00", REPRESENTATIVE, {})
    show(gw, "GameWatch body c00 (decoded reference)", REPRESENTATIVE, ev)

    # Distribution of the reader's cancel value, to see whether 334/318 are unique
    # or just the tail of a wider spread.
    cancels = sorted({e["cancel"] for e in gun["entries"] if e["cancel"] is not None})
    print("\n===== Gunner cancel distribution =====")
    print("  distinct values:", cancels)
    print("  count:", len(cancels))
    outliers = [e for e in gun["entries"] if e["cancel"] is not None and e["cancel"] > 100]
    print("  entries with cancel > 100:", len(outliers))
    for e in outliers:
        print(f"    kind {e['kind']:#011x} cancel={e['cancel']} size={e['size']} "
              f"size%8={e['size'] % 8} tail={e['raw'][24:].hex(' ')}")