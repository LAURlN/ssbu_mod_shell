"""P1-CATALOG-AUDIT part 5: confirm the trailing-byte layout and check directional
variants, then dump every field the slot table needs.

Tail hypothesis to confirm: tail[24:28] is four single bytes
    xlu_start, xlu_end, cancel_frame, no_stop_intp
Tested against the decoded GameWatch YAML over all 746 kinds, including the 28
kinds where xlu_start/xlu_end are non-zero (the cases that can distinguish a byte
from a u16).

Also: does Gunner carry the same directional tilt/smash variants GameWatch does?

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
YML = ROOT / "mods/ssbu_mod_new/dumps/scripts/gamewatch_motion_list.yml"
LAB = ROOT / "mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv"


def load_yml(path):
    out, cur = {}, None
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if line.startswith("  ") and not line.startswith("   ") and s.endswith(":"):
            cur = s[:-1]
            out[cur] = {}
        elif cur and ":" in s and not s.startswith("- name"):
            k, _, v = s.partition(":")
            v = v.strip()
            out[cur][k] = int(v) if v.isdigit() else v
    return out


def tail_of(e):
    ab = ((e["n"] * 12) + 3) & ~3
    ts = 24 + ab
    return e["raw"][ts:ts + e["size"]], ts


def labels_by_kind():
    m = {}
    for line in LAB.read_text(encoding="utf-8", errors="replace").splitlines():
        if "," in line:
            hx, _, nm = line.partition(",")
            try:
                m.setdefault(int(hx, 16), []).append(nm.strip())
            except ValueError:
                pass
    return m


def main():
    gw, gun = mlist.parse(GWC), mlist.parse(GUN)
    yml = load_yml(YML)
    labs = labels_by_kind()

    print("### confirm: tail[24:28] = xlu_start, xlu_end, cancel_frame, no_stop_intp (bytes)")
    checks = {0: "xlu_start", 1: "xlu_end", 2: "cancel_frame", 3: "no_stop_intp"}
    tally = {i: 0 for i in range(4)}
    n = 0
    wrong = []
    for name, rec in yml.items():
        e = mlist.find(gw, name)
        t, _ = tail_of(e)
        last4 = t[-4:]
        n += 1
        for i, f in checks.items():
            want = rec.get(f)
            if want is None:
                continue
            wantv = int(want) if str(want).isdigit() else (1 if want == "true" else 0)
            if last4[i] == wantv:
                tally[i] += 1
            else:
                wrong.append((name, f, wantv, last4[i]))
    for i in range(4):
        print(f"  tail[24+{i}] == {checks[i]:<14} {tally[i]}/{n}")
    print(f"  mismatches: {len(wrong)} {wrong[:8]}")

    print("\n### the 28 non-zero xlu_start/xlu_end kinds, read byte-wise")
    print(f"  {'kind':<22} {'xlu_s':>5} {'xlu_e':>5} {'cancel':>6} {'nsi':>4}   last4")
    shown = 0
    for name, rec in yml.items():
        if rec.get("xlu_start") in (0, "0") and rec.get("xlu_end") in (0, "0"):
            continue
        e = mlist.find(gw, name)
        t, _ = tail_of(e)
        print(f"  {name:<22} {rec.get('xlu_start'):>5} {rec.get('xlu_end'):>5} "
              f"{rec.get('cancel_frame'):>6} {str(rec.get('no_stop_intp')):>6}   {t[-4:].hex(' ')}")
        shown += 1
        if shown >= 12:
            break

    print("\n### directional variants: GameWatch vs Gunner")
    probe = ["attack_s3_s", "attack_s3_l", "attack_s3_r", "attack_s3_f", "attack_s3_b",
             "attack_hi3", "attack_hi3_l", "attack_hi3_r", "attack_hi3_f", "attack_hi3_b",
             "attack_lw3", "attack_s4_s", "attack_s4_hold", "attack_hi4", "attack_hi4_r",
             "attack_hi4_l", "attack_hi4_f", "attack_hi4_b", "attack_hi4_hold",
             "attack_lw4", "attack_lw4_hold"]
    print(f"  {'kind':<18} {'GameWatch':<12} {'Gunner':<12}")
    for p in probe:
        def st(ml):
            try:
                e = mlist.find(ml, p)
                return f"f{e['flags']:#06x} c{e['cancel']}"
            except KeyError:
                return "-"
        print(f"  {p:<18} {st(gw):<12} {st(gun):<12}")

    print("\n### Gunner: full player-facing attack/grab/throw inventory (named kinds only)")
    rows = []
    for e in gun["entries"]:
        names = labs.get(e["kind"])
        if not names:
            continue
        for nm in names:
            if nm.startswith(("attack_", "catch", "throw_", "landing_",
                              "special_n", "special_s", "special_hi", "special_lw",
                              "down_attack", "down_forward", "down_back")):
                rows.append((nm, e))
    seen = set()
    for nm, e in sorted(rows, key=lambda r: r[0]):
        if nm in seen:
            continue
        seen.add(nm)
        t, ts = tail_of(e)
        last4 = t[-4:]
        gs = f"{e['gs']:#011x}"
        print(f"  {nm:<24} gs={gs} flags={e['flags']:#06x} blend={e['blend']:<3} "
              f"idx={gun['entries'].index(e):<4} "
              f"xlu_s={last4[0]} xlu_e={last4[1]} cancel={last4[2]} nsi={last4[3]}")


if __name__ == "__main__":
    main()