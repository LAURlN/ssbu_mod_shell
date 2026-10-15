"""P1-CATALOG-AUDIT part 4: pin the exact byte layout of the 28-byte tail.

Parts 1-3 established, against the decoded GameWatch YAML (746/746):
  tail[0:24]  three u64  = expression / sound / effect script-name hashes
  tail[24:28] four bytes = the remaining timing fields

This script identifies which of those four bytes is which by locating every
non-zero value in the file and correlating it with the YAML's `xlu_start`,
`xlu_end`, `cancel_frame` and `no_stop_intp`. Nothing is assumed from position.

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

GWC = ROOT / "gamedata/ssbu-13.0.4/files/fighter/gamewatch/motion/body/c00/motion_list.bin"
YML = ROOT / "mods/ssbu_mod_new/dumps/scripts/gamewatch_motion_list.yml"


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
    anim_block = ((e["n"] * 12) + 3) & ~3
    ts = 24 + anim_block
    return e["raw"][ts:ts + e["size"]], ts


def main():
    gw = mlist.parse(GWC)
    yml = load_yml(YML)

    sizes = sorted({e["size"] for e in gw["entries"]})
    print(f"### distinct tail sizes in GameWatch c00: {sizes}")
    for sz in sizes:
        n = sum(1 for e in gw["entries"] if e["size"] == sz)
        print(f"  size={sz}: {n} entries")

    print("\n### every distinct value of each tail byte offset (24-byte tail only)")
    by_size = {sz: [] for sz in sizes}
    for e in gw["entries"]:
        if e["cancel"] is None:
            continue
        t, _ = tail_of(e)
        by_size[e["size"]].append((e, t))

    for sz in sizes:
        rows = by_size[sz]
        if not rows:
            continue
        print(f"\n  -- size {sz} ({len(rows)} entries): "
              f"{'last 8 bytes of tail':<40}")
        tails = sorted({t[-8:].hex(' ') for _, t in rows})
        print(f"     distinct last-8: {len(tails)}")
        for x in tails[:20]:
            print(f"       {x}")

    print("\n### correlate: which YAML field is each of the last four bytes?")
    # For each of the last four byte positions, check whether it equals
    # xlu_start / xlu_end / cancel_frame / no_stop_intp across all 746 kinds.
    fields = ["xlu_start", "xlu_end", "cancel_frame", "no_stop_intp"]
    hits = {f: [0, 0, 0, 0] for f in fields}  # 4 candidate byte positions
    n = 0
    for name, rec in yml.items():
        e = mlist.find(gw, name)
        t, _ = tail_of(e)
        n += 1
        last4 = t[-4:]
        pos_vals = {i: last4[i] for i in range(4)}
        pos_vals_u16 = {
            0: struct.unpack_from("<H", last4, 0)[0],
            2: struct.unpack_from("<H", last4, 2)[0],
        }
        for f in fields:
            want = rec.get(f)
            if want is None:
                continue
            wantb = int(want) if str(want).isdigit() else (1 if want == "true" else 0)
            # byte match at each of the four positions
            for i in range(4):
                if pos_vals[i] == wantb:
                    hits[f][i] += 1
            # u16 match for the two u16 slots (xlu_start/xlu_end style)
            if f in ("xlu_start", "xlu_end") and wantb in (0,):
                pass
    print(f"  entries: {n}")
    print(f"  byte position -> field matches (of {n}):")
    for f in fields:
        print(f"    {f:<15} {[hits[f][i] for i in range(4)]}")

    print("\n### xlu_start / xlu_end: are they ever non-zero anywhere in the file?")
    nz_xs = [(k, v.get("xlu_start")) for k, v in yml.items() if v.get("xlu_start") not in (0, "0")]
    nz_xe = [(k, v.get("xlu_end")) for k, v in yml.items() if v.get("xlu_end") not in (0, "0")]
    print(f"  non-zero xlu_start: {len(nz_xs)} {nz_xs[:10]}")
    print(f"  non-zero xlu_end  : {len(nz_xe)} {nz_xe[:10]}")

    print("\n### so: last four bytes, interpreted (byte0 byte1) u16 + (byte2 byte3) u16")
    interesting = ["attack_s3_s", "attack_s4_s", "attack_air_hi", "attack_11",
                   "wait", "landing_air_b", "special_s_5"]
    for name in interesting:
        if name not in yml:
            continue
        e = mlist.find(gw, name)
        t, ts = tail_of(e)
        last4 = t[-4:]
        lo = struct.unpack_from("<H", last4, 0)[0]
        hi = struct.unpack_from("<H", last4, 2)[0]
        print(f"  {name:<16} file_off={ts + len(t) - 4} last4={last4.hex(' ')} "
              f"u16_lo={lo} u16_hi={hi}  "
              f"(hi & 0xff)={hi & 0xFF} (hi>>8)={hi >> 8}  "
              f"yml cancel={yml[name].get('cancel_frame')} nsi={yml[name].get('no_stop_intp')}")


if __name__ == "__main__":
    main()