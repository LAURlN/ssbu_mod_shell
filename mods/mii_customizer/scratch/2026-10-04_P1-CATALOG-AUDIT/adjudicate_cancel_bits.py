"""P1-CATALOG-AUDIT part 3: adjudicate the reader's `cancel` u16.

Established so far (part 2, tier B):
  - the shared reader's `game_script` and `blend` agree with the decoded GameWatch
    YAML for 746/746 kinds;
  - `cancel_frame` agrees for 728/746 and every one of the 18 disagreements is
    exactly reader_value == yml_value + 256.

This script tests whether bit 0x100 of that trailing u16 is a separate boolean that
the reader folds into the number, using the decoded YAML's own boolean field
`no_stop_intp` as the labelled control. It also locates the field's exact bytes in
each entry and re-reads the Gunner outliers under the corrected reading.

Read-only. The shared reader is imported, never modified.
"""
import hashlib
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


def tail_and_offsets(e):
    """Return the real `size`-byte tail and the file offset of its final u16.

    Layout: 24-byte header, then the animation block
    (`n` x (u64 hash + u32 unk), padded to 4), then `size` bytes of tail.
    """
    anim_block = ((e["n"] * 12) + 3) & ~3
    tail_start = 24 + anim_block
    tail = e["raw"][tail_start:tail_start + e["size"]]
    return tail, tail_start, e["size"]


def load_yml(path):
    out, cur = {}, None
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        s = line.strip()
        if line.startswith("  ") and not line.startswith("   ") and s.endswith(":"):
            cur = s[:-1]
            out[cur] = {}
        elif cur and ":" in s:
            k, _, v = s.partition(":")
            v = v.strip()
            out[cur][k] = int(v) if v.isdigit() else v
    return out


def u16(tail, off):
    return struct.unpack_from("<H", tail, off)[0]


def main():
    gw, gun = mlist.parse(GWC), mlist.parse(GUN)
    yml = load_yml(YML)

    print("### H1: the disagreements are exactly bit 0x100 set in the trailing u16")
    rows = []
    for name, rec in yml.items():
        e = mlist.find(gw, name)
        if e["cancel"] is None or "cancel_frame" not in rec:
            continue
        reader, truth = e["cancel"], rec["cancel_frame"]
        rows.append((name, reader, truth, reader == truth,
                     reader & ~0x100, rec.get("no_stop_intp")))
    exact = sum(1 for r in rows if r[3])
    masked = sum(1 for r in rows if r[4] == r[2])
    print(f"  entries compared                : {len(rows)}")
    print(f"  raw reader == yml               : {exact}")
    print(f"  reader & ~0x100 == yml          : {masked}")

    print("\n### H2: bit 0x100 tracks the decoded `no_stop_intp` boolean")
    tab = {}
    for name, reader, truth, eq, masked_val, nsi in rows:
        tab[(reader & 0x100 != 0, nsi)] = tab.get((reader & 0x100 != 0, nsi), 0) + 1
    for k in sorted(tab, key=lambda t: str(t)):
        print(f"  bit0x100_set={str(k[0]):<5} no_stop_intp={str(k[1]):<5} -> {tab[k]}")
    agree = sum(v for k, v in tab.items() if k[0] == (k[1] == "true"))
    print(f"  bit0x100_set == (no_stop_intp is true): {agree}/{len(rows)}")

    print("\n### H3: the four trailing bytes carry xlu_start / xlu_end / cancel / no_stop_intp")
    e = mlist.find(gw, "attack_s3_s")
    tail, ts, size = tail_and_offsets(e)
    print(f"  attack_s3_s tail ({size} bytes): {tail.hex(' ')}")
    print(f"  first 24 bytes as 3x u64      : "
          f"{[format(struct.unpack_from('<Q', tail, i)[0], '#011x') for i in (0, 8, 16)]}")
    print(f"  last 4 bytes                   : {tail[24:].hex(' ')} "
          f"-> xlu_start={u16(tail, 24)} xlu_end={u16(tail, 26)}? "
          f"cancel={u16(tail, size - 2)}")
    print(f"  yml extra for attack_s3_s      : {yml['attack_s3_s']}")
    print("\n  cross-check: are the 3 leading u64 the expression/sound/effect hashes?")
    got = [struct.unpack_from("<Q", tail, i)[0] for i in (0, 8, 16)]
    for cand in ("expression_attacks3", "sound_attacks3", "effect_attacks3",
                 "expression_attack_s3", "sound_attack_s3", "effect_attack_s3"):
        print(f"    {cand:<24} {mlist.hash40(cand):#011x} "
              f"{'MATCH' if mlist.hash40(cand) in got else ''}")

    print("\n### Gunner outliers re-read with bit 0x100 masked")
    labels = {}
    for line in (ROOT / "mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv") \
            .read_text(encoding="utf-8", errors="replace").splitlines():
        if "," in line:
            hx, _, nm = line.partition(",")
            try:
                labels.setdefault(int(hx, 16), []).append(nm.strip())
            except ValueError:
                pass
    by_kind = {e["kind"]: e for e in gun["entries"]}
    print(f"  {'kind hash':<13} {'names':<26} {'raw':>5} {'&~0x100':>8} {'0x100':>6}")
    for k, e in sorted(by_kind.items(), key=lambda kv: -kv[1]["cancel"]):
        if e["cancel"] is None or e["cancel"] < 200:
            continue
        names = ",".join(labels.get(k, ["?"]))[:25]
        print(f"  {k:#011x}   {names:<26} {e['cancel']:>5} "
              f"{e['cancel'] & ~0x100:>8} {'set' if e['cancel'] & 0x100 else '-':>6}")

    print("\n### full Gunner cancel distribution, raw vs masked")
    raw = sorted({e["cancel"] for e in gun["entries"] if e["cancel"] is not None})
    msk = sorted({e["cancel"] & ~0x100 for e in gun["entries"] if e["cancel"] is not None})
    print(f"  raw     ({len(raw)}): {raw}")
    print(f"  masked  ({len(msk)}): {msk}")

    print("\n### whole-file re-check under the masked reading")
    ok = bad = 0
    for name, rec in yml.items():
        e = mlist.find(gw, name)
        if e["cancel"] is None or "cancel_frame" not in rec:
            continue
        if (e["cancel"] & ~0x100) == rec["cancel_frame"]:
            ok += 1
        else:
            bad += 1
            print(f"  STILL WRONG {name}: reader={e['cancel']} yml={rec['cancel_frame']}")
    print(f"  masked reading agrees on {ok}/{ok + bad} GameWatch kinds")

    print("\n### sha256 of inputs")
    for p in (GUN, GWC):
        print(f"  {p.relative_to(ROOT)}  {hashlib.sha256(p.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()