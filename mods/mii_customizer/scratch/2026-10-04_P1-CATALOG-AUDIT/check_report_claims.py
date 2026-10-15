"""P1-CATALOG-AUDIT part 6: verify the claims the report makes, before the report
is trusted. Every number in research/P1-CATALOG-AUDIT.md that is marked B is
re-derived here from the two binaries, so a wrong claim fails loudly.

Read-only; the shared reader is imported, never modified.
"""
import importlib.util
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location(
    "mlist", ROOT / "mods/ssbu_mod_new/src/pgwr/tools/mlist.py")
mlist = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mlist)

GUN = ROOT / "gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin"
GWC = ROOT / "gamedata/ssbu-13.0.4/files/fighter/gamewatch/motion/body/c00/motion_list.bin"

fails = []


def check(label, got, want):
    ok = got == want
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}: got {got!r} want {want!r}")
    if not ok:
        fails.append(label)


def tail_of(e):
    ab = ((e["n"] * 12) + 3) & ~3
    ts = 24 + ab
    return e["raw"][ts:ts + e["size"]]


def fields(e):
    t = tail_of(e)[-4:]
    return dict(xlu_s=t[0], xlu_e=t[1], cancel=t[2], nsi=t[3])


def main():
    gun, gw = mlist.parse(GUN), mlist.parse(GWC)

    print("### report claim: representative Gunner entries, resolved fields")
    want = {
        "attack_11":     dict(xlu_s=0, xlu_e=0, cancel=26, nsi=0, flags=0x0084, blend=0),
        "attack_12":     dict(xlu_s=0, xlu_e=0, cancel=26, nsi=0, flags=0x0084, blend=0),
        "attack_13":     dict(xlu_s=0, xlu_e=0, cancel=38, nsi=0, flags=0x0084, blend=0),
        "attack_dash":   dict(xlu_s=0, xlu_e=0, cancel=46, nsi=0, flags=0x0084, blend=0),
        "attack_hi3":    dict(xlu_s=0, xlu_e=0, cancel=38, nsi=0, flags=0x0080, blend=0),
        "attack_s3_s":   dict(xlu_s=0, xlu_e=0, cancel=37, nsi=0, flags=0x0080, blend=0),
        "attack_lw3":    dict(xlu_s=0, xlu_e=0, cancel=41, nsi=0, flags=0x0080, blend=0),
        "attack_s4_s":   dict(xlu_s=0, xlu_e=0, cancel=78, nsi=1, flags=0x0084, blend=0),
        "attack_s4_hold": dict(xlu_s=0, xlu_e=0, cancel=0, nsi=0, flags=0x0084, blend=0),
        "attack_hi4":    dict(xlu_s=0, xlu_e=0, cancel=56, nsi=0, flags=0x0080, blend=0),
        "attack_hi4_hold": dict(xlu_s=0, xlu_e=0, cancel=0, nsi=0, flags=0x0080, blend=0),
        "attack_lw4":    dict(xlu_s=0, xlu_e=0, cancel=53, nsi=0, flags=0x0084, blend=0),
        "attack_lw4_hold": dict(xlu_s=0, xlu_e=0, cancel=0, nsi=0, flags=0x0080, blend=0),
        "attack_air_n":  dict(xlu_s=0, xlu_e=0, cancel=42, nsi=0, flags=0x0080, blend=0),
        "attack_air_f":  dict(xlu_s=0, xlu_e=0, cancel=42, nsi=0, flags=0x0080, blend=0),
        "attack_air_b":  dict(xlu_s=0, xlu_e=0, cancel=48, nsi=0, flags=0x0080, blend=0),
        "attack_air_hi": dict(xlu_s=0, xlu_e=0, cancel=62, nsi=1, flags=0x0080, blend=0),
        "attack_air_lw": dict(xlu_s=0, xlu_e=0, cancel=55, nsi=0, flags=0x0080, blend=0),
    }
    for k, w in want.items():
        e = mlist.find(gun, k)
        f = fields(e)
        got = dict(f, flags=e["flags"], blend=e["blend"])
        check(k, got, w)

    print("\n### report claim: five landing kinds, all cancel 20")
    for k in ("landing_air_n", "landing_air_f", "landing_air_b",
              "landing_air_hi", "landing_air_lw"):
        check(f"{k}.cancel", fields(mlist.find(gun, k))["cancel"], 20)

    print("\n### report claim: grab/pummel/throw block")
    gwant = {
        "catch": (35, 0x0080), "catch_dash": (43, 0x0084), "catch_turn": (38, 0x0081),
        "catch_pull": (2, 0x0080), "catch_wait": (0, 0x0002),
        "catch_attack": (7, 0x0080), "catch_cut": (30, 0x0080),
        "throw_f": (34, 0x0080), "throw_b": (50, 0x0081),
        "throw_hi": (52, 0x0080), "throw_lw": (41, 0x0080),
    }
    for k, (c, fl) in gwant.items():
        e = mlist.find(gun, k)
        check(f"{k} (cancel, flags)", (fields(e)["cancel"], e["flags"]), (c, fl))
    check("catch_wait.blend", mlist.find(gun, "catch_wait")["blend"], 6)
    print("  note: only catch_wait should have a non-zero blend among these:")
    nz = [k for k in gwant if mlist.find(gun, k)["blend"] != 0]
    check("non-zero blend count in grab/throw block", nz, ["catch_wait"])

    print("\n### report claim: side specials s3_1=41, s3_2=50, s1=64")
    for k, c in (("special_s3_1", 41), ("special_s3_2", 50), ("special_s1", 64)):
        check(f"{k}.cancel", fields(mlist.find(gun, k))["cancel"], c)

    print("\n### report claim: special_lw1 _l kinds share base game_script hash")
    for base, side in (("special_lw1_start", "special_lw1_start_l"),
                       ("special_lw1_loop", "special_lw1_loop_l"),
                       ("special_lw1_hit", "special_lw1_hit_l"),
                       ("special_lw1_end", "special_lw1_end_l")):
        b, s = mlist.find(gun, base), mlist.find(gun, side)
        check(f"{base} == {side} gs", (b["gs"], s["gs"]), (b["gs"], b["gs"]))
        check(f"{base} vs {side} anims differ", b["anims"] != s["anims"], True)

    print("\n### report claim: down-attack xlu values (1 / 23-24) and cancel 46")
    for k, xe in (("down_attack_u", 23), ("down_attack_d", 24)):
        f = fields(mlist.find(gun, k))
        check(f"{k} (xlu_s, xlu_e, cancel)", (f["xlu_s"], f["xlu_e"], f["cancel"]),
              (1, xe, 46))

    print("\n### report claim: up-special hi2_squat xlu 7/13; special_hi1 cancel 0")
    f = fields(mlist.find(gun, "special_hi2_squat"))
    check("special_hi2_squat (xlu_s, xlu_e)", (f["xlu_s"], f["xlu_e"]), (7, 13))
    check("special_hi1.cancel", fields(mlist.find(gun, "special_hi1"))["cancel"], 0)

    print("\n### report claim: masked Gunner cancel max is 81, no value above 81")
    vals = [e["cancel"] & ~0x100 for e in gun["entries"] if e["cancel"] is not None]
    check("max masked cancel", max(vals), 81)
    check("entries above 81 after masking", sum(1 for v in vals if v > 81), 0)

    print("\n### report claim: 19 Gunner entries had bit 0x100 set")
    check("count bit0x100 set",
          sum(1 for e in gun["entries"] if e["cancel"] and e["cancel"] & 0x100), 19)

    print("\n### report claim: directional variants present in GW, absent in Gunner")
    for k in ("attack_hi3_l", "attack_hi4_r"):
        check(f"{k} in GameWatch", bool(_has(gw, k)), True)
        check(f"{k} absent in Gunner", bool(_has(gun, k)), False)
    for k in ("attack_s3_l", "attack_s3_r", "attack_s3_f", "attack_s3_b",
              "attack_hi3_f", "attack_hi3_b", "attack_hi3_r", "attack_hi4_f",
              "attack_hi4_b", "attack_hi4_l"):
        check(f"{k} absent in both", bool(_has(gw, k) or _has(gun, k)), False)

    print("\n### report claim: AI attack list contains no Gunner attack kind hashes")
    import csv
    tsv = (ROOT / "mods/mii_customizer/evidence/P1-CATALOG/"
           "fighter_miigunner_ai_param_attack_list_param_labelled.tsv").read_text(
        encoding="utf-8", errors="replace")
    for k in ("attack_s3_s", "attack_s4_s", "attack_hi3", "attack_11",
              "attack_air_hi", "attack_lw3"):
        h = f"{mlist.hash40(k):#011x}".lstrip("#0")
        check(f"AI tsv lacks hash of {k}", h in tsv, False)

    print("\n### report claim: Final Smash / ledge / appeal / get-up presence")
    for k in ("final_start", "final_end", "final_air_start", "final_u",
              "cliff_catch", "cliff_wait", "cliff_attack_quick", "slip_attack",
              "slip_escape_f", "slip_escape_b", "appeal_hi_r", "appeal_hi_l",
              "down_attack_u", "down_attack_d", "down_forward_u", "down_back_u"):
        check(f"{k} present in Gunner", bool(_has(gun, k)), True)

    print("\n### report claim: five get-up attack kinds (the next-question premise)")
    check("down_attack_* count", sum(1 for k in
          ("down_attack_u", "down_attack_d", "down_forward_u", "down_forward_d",
           "down_back_u", "down_back_d") if _has(gun, k)), 6)

    print("\n### report claim: gunner entry count 774, gamewatch 746")
    check("gunner entries", len(gun["entries"]), 774)
    check("gamewatch entries", len(gw["entries"]), 746)

    print("\n### report claim: round trip equal for both")
    check("gunner round trip", mlist.encode(gun) == gun["data"], True)
    check("gamewatch round trip", mlist.encode(gw) == gw["data"], True)

    print("\n### report claim: gunner sha256")
    import hashlib
    check("gunner sha256", hashlib.sha256(Path(GUN).read_bytes()).hexdigest(),
          "2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba")
    check("gamewatch sha256", hashlib.sha256(Path(GWC).read_bytes()).hexdigest(),
          "306be009edb40b692f58aa67eb2bb18c12e47068d8350d4e0a7e96ceb88ed0a2")

    print("\n" + "=" * 60)
    print(f"RESULT: {len(fails)} failing claim(s)")
    for f in fails:
        print(f"  FAILED: {f}")


def _has(ml, name):
    try:
        mlist.find(ml, name)
        return True
    except KeyError:
        return False


if __name__ == "__main__":
    main()