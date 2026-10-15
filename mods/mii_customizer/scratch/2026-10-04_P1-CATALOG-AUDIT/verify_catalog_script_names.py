"""P1-CATALOG-AUDIT part 7: verify every game-script NAME written into the
corrected P1-CATALOG.md tables, by recomputing hash40(name) and comparing it to the
game_script hash actually stored in the Gunner entry.

P1-CATALOG-AUDIT filled in script names that were previously `-`. Those names are only
worth anything if each one hashes to the entry's own game_script field, so each is
checked here rather than trusted. The `_l` forms are the intended negative control:
`expression_attack_s3` style names must NOT match.

Read-only; the shared reader is imported, never modified.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location(
    "mlist", ROOT / "mods/ssbu_mod_new/src/pgwr/tools/mlist.py")
mlist = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mlist)

GUN = ROOT / "gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin"

# (kind, script name now written in P1-CATALOG.md / P1-CATALOG-AUDIT.md)
CLAIMS = [
    ("attack_11", "game_attack11"),
    ("attack_12", "game_attack12"),
    ("attack_13", "game_attack13"),
    ("attack_dash", "game_attackdash"),
    ("attack_hi3", "game_attackhi3"),
    ("attack_lw3", "game_attacklw3"),
    ("attack_s3_s", "game_attacks3"),
    ("attack_lw4", "game_attacklw4"),
    ("attack_lw4_hold", "game_attacklw4charge"),
    ("attack_hi4", "game_attackhi4"),
    ("attack_hi4_hold", "game_attackhi4charge"),
    ("attack_s4_s", "game_attacks4"),
    ("attack_s4_hold", "game_attacks4charge"),
    ("attack_air_n", "game_attackairn"),
    ("attack_air_f", "game_attackairf"),
    ("attack_air_b", "game_attackairb"),
    ("attack_air_hi", "game_attackairhi"),
    ("attack_air_lw", "game_attackairlw"),
]

# grab / pummel / throw names carried over from P1-CATALOG, re-verified here.
GRAB = [
    ("catch", "game_catch"), ("catch_dash", "game_catchdash"),
    ("catch_turn", "game_catchturn"), ("catch_pull", "game_catchpull"),
    ("catch_wait", "game_catchwait"), ("catch_attack", "game_catchattack"),
    ("catch_cut", "game_catchcut"),
    ("throw_f", "game_throwf"), ("throw_b", "game_throwb"),
    ("throw_hi", "game_throwhi"), ("throw_lw", "game_throwlw"),
]

# Negative control: these must NOT be the script name of attack_s3_s.
NEGATIVE = ["game_attack_s3_s", "game_attacks3_s", "game_attack_s3",
            "game_attacks4_s", "game_attack_s4_s"]


def main():
    gun = mlist.parse(GUN)
    bad = []

    print("### positive: script name written in the report -> hash40 -> entry gs")
    for kind, name in CLAIMS + GRAB:
        e = mlist.find(gun, kind)
        want = mlist.hash40(name)
        ok = want == e["gs"]
        print(f"  [{'PASS' if ok else 'FAIL'}] {kind:<16} {name:<22} "
              f"{want:#011x} vs entry {e['gs']:#011x}")
        if not ok:
            bad.append((kind, name, f"{want:#011x}", f"{e['gs']:#011x}"))

    print("\n### negative control: plausible-but-wrong names must not match")
    e_s3 = mlist.find(gun, "attack_s3_s")
    e_s4 = mlist.find(gun, "attack_s4_s")
    for name in NEGATIVE:
        h = mlist.hash40(name)
        hit = (h == e_s3["gs"]) or (h == e_s4["gs"])
        ok = not hit
        print(f"  [{'PASS' if ok else 'FAIL'}] {name:<22} {h:#011x} does not match "
              f"attack_s3_s/attack_s4_s")
        if not ok:
            bad.append(("NEG", name, "matched", ""))

    print("\n### the kind-name -> script-name rule, stated once")
    print("  rule: strip a trailing '_s' from an s<n>_<s> kind, drop '_' before digits,")
    print("        then prefix 'game_'.  attack_s3_s -> attacks3 -> game_attacks3")

    print("\n" + "=" * 60)
    print(f"RESULT: {len(bad)} failing script-name claim(s)")
    for b in bad:
        print(f"  FAILED: {b}")


if __name__ == "__main__":
    main()