"""P1-CATALOG-AUDIT part 2: validate the shared reader's field interpretation
against the WHOLE GameWatch reference, and inventory Gunner's tilt/smash kinds.

Controls:
  - GameWatch `dumps/scripts/gamewatch_motion_list.yml` is a decoded field listing
    (game_script / blend_frames / cancel_frame / xlu_start / xlu_end / no_stop_intp)
    for a fighter whose binary is on disk. Comparing the shared reader's output to
    it for every shared kind is a semantic check the round-trip cannot give.
  - The 12-byte animation block (u64 hash + u32 unk per anim) is separated from the
    `size`-byte tail so tail offsets are reported against the real tail.

Read-only; the shared reader is imported, not modified.
"""
import hashlib
import importlib.util
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location(
    "mlist", ROOT / "mods/ssbu_mod_new/src/pgwr/tools/mlist.py")
mlist = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mlist)

GUN = ROOT / "gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin"
GWC = ROOT / "gamedata/ssbu-13.0.4/files/fighter/gamewatch/motion/body/c00/motion_list.bin"
YML = ROOT / "mods/ssbu_mod_new/dumps/scripts/gamewatch_motion_list.yml"
LABELS = ROOT / "mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv"


def real_tail(e):
    """The `size`-byte tail, excluding the 12-bytes-per-anim animation block."""
    anim_block = ((24 + e["n"] * 12 + 3) & ~3) - 24
    return e["raw"][anim_block:], anim_block


def load_yml(path):
    """kind -> dict of the decoded fields."""
    out, cur = {}, None
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if line.startswith("  ") and not line.startswith("   ") and s.endswith(":"):
            cur = s[:-1]
            out[cur] = {}
        elif cur and ":" in s:
            k, _, v = s.partition(":")
            if k in ("game_script", "blend_frames", "cancel_frame",
                     "xlu_start", "xlu_end", "no_stop_intp"):
                out[cur][k] = int(v.strip()) if v.strip().isdigit() else v.strip()
    return out


def main():
    gun, gw = mlist.parse(GUN), mlist.parse(GWC)
    yml = load_yml(YML)

    print("### full-file cross-validation: shared reader vs decoded GameWatch YAML")
    shared, gs_ok, cancel_ok, blend_ok = 0, 0, 0, 0
    gs_bad, cancel_bad, blend_bad, missing = [], [], [], []
    for name, rec in yml.items():
        try:
            e = mlist.find(gw, name)
        except KeyError:
            missing.append(name)
            continue
        shared += 1
        if rec.get("game_script") and mlist.hash40(rec["game_script"]) == e["gs"]:
            gs_ok += 1
        else:
            gs_bad.append((name, rec.get("game_script"), f"{e['gs']:#011x}"))
        if "cancel_frame" in rec and rec["cancel_frame"] == e["cancel"]:
            cancel_ok += 1
        else:
            cancel_bad.append((name, rec.get("cancel_frame"), e["cancel"]))
        if "blend_frames" in rec and rec["blend_frames"] == e["blend"]:
            blend_ok += 1
        else:
            blend_bad.append((name, rec.get("blend_frames"), e["blend"]))

    print(f"  yml kinds parsed          : {len(yml)}")
    print(f"  yml kinds found in binary : {shared}   (yml-only: {len(missing)})")
    print(f"  game_script hash agrees   : {gs_ok}/{shared}")
    print(f"  cancel_frame agrees       : {cancel_ok}/{shared}")
    print(f"  blend_frames agrees       : {blend_ok}/{shared}")
    for label, bad in (("game_script", gs_bad), ("cancel", cancel_bad), ("blend", blend_bad)):
        if bad:
            print(f"  MISMATCHES ({label}): {len(bad)}")
            for row in bad[:12]:
                print(f"    {row}")
    print(f"  yml kinds absent from binary (sample): {missing[:12]}")

    # Does the YAML cancel claim track the *tail*, i.e. is the reader's offset right?
    print("\n### is cancel_frame read at the same offset in every entry?")
    offs = {}
    for name, rec in yml.items():
        try:
            e = mlist.find(gw, name)
        except KeyError:
            continue
        tail, _ = real_tail(e)
        if e["cancel"] is None:
            continue
        o = len(tail) - 2
        offs.setdefault((e["size"], o), []).append(
            (name, rec.get("cancel_frame") == e["cancel"]))
    for (size, o), rows in sorted(offs.items()):
        good = sum(1 for _, g in rows if g)
        print(f"  size={size} tail_off={o}: {good}/{len(rows)} match")

    print("\n### Gunner: real 28-byte tail of representative entries")
    for n in ["attack_11", "attack_hi3", "attack_s3_s", "attack_s4_s",
              "attack_air_hi", "attack_lw4"]:
        e = mlist.find(gun, n)
        tail, ab = real_tail(e)
        u64 = [f"{struct.unpack_from('<Q', tail, i)[0]:#011x}" for i in range(0, 24, 8)]
        tail_u16 = {i: struct.unpack_from("<H", tail, i)[0] for i in range(24, len(tail) - 1, 2)}
        print(f"  {n:<14} animblock={ab} tail={tail.hex(' ')}")
        print(f"  {'':<14} 3x u64={u64}  tail_u16={tail_u16}")

    # Are those three u64 slots script-name hashes?
    print("\n### are the three tail u64 slots script-name hashes?")
    for n in ["attack_11", "attack_s3_s", "attack_s4_s", "attack_air_hi"]:
        e = mlist.find(gun, n)
        tail, _ = real_tail(e)
        got = [struct.unpack_from("<Q", tail, i)[0] for i in range(0, 24, 8)]
        stem = n.replace("attack_", "attack")
        cands = {f"expression_{stem}": 0, f"sound_{stem}": 1, f"effect_{stem}": 2}
        hit = []
        for name, slot in cands.items():
            hit.append(f"{name}->{mlist.hash40(name) == got[slot]}")
        print(f"  {n:<14} {' '.join(hit)}")

    print("\n### Gunner: tilt / smash kind inventory (incl. variants)")
    labels = {}
    for line in LABELS.read_text(encoding="utf-8", errors="replace").splitlines():
        if "," in line:
            hx, _, nm = line.partition(",")
            try:
                labels.setdefault(nm.strip(), []).append(int(hx, 16))
            except ValueError:
                pass
    present = {}
    for e in gun["entries"]:
        for nm, hs in labels.items():
            if e["kind"] in hs:
                present[nm] = e
    for pat in ["attack_", "landing_", "catch", "throw", "down_attack", "final",
                "appeal", "cliff", "special_s", "special_hi3", "special_lw1"]:
        rows = sorted(n for n in present if n.startswith(pat))
        print(f"  [{pat}] {rows}")

    print("\n### Gunner: which attack_s3*/attack_s4*/variants exist, reader fields")
    for n in sorted(n for n in present if n.startswith(("attack_s3", "attack_s4",
                                                      "attack_hi3", "attack_lw4", "attack_hi4"))):
        e = present[n]
        print(f"  {n:<20} gs={e['gs']:#011x} flags={e['flags']:#06x} "
              f"anims={[f'{a:#011x}' for a in e['anims']]} cancel={e['cancel']}")

    print("\n### Gunner: does it carry the GameWatch-only directional tilt variant?")
    for n in ["attack_hi3_l", "attack_s3_l", "attack_hi3_f", "attack_hi3_b"]:
        try:
            e = mlist.find(gun, n)
            print(f"  {n:<16} PRESENT gs={e['gs']:#011x} flags={e['flags']:#06x}")
        except KeyError:
            print(f"  {n:<16} absent")

    print("\n### sha256 of the two binaries actually read")
    for p in (GUN, GWC):
        print(f"  {p.relative_to(ROOT)}  {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()