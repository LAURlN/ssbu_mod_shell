#!/usr/bin/env python3
"""Hero's Spin (up-B) air-descent audit for the modded Mythra c06/c07.

Purpose
-------
`hero_spin_params.rs` adapts two air-kinetic numbers for the duration of the
aerial phase of Hero's Spin (`AIR_ACCEL_Y_SCALE`, `AIR_SPEED_Y_SCALE`, applied
on top of Mii Swordfighter's common `air_accel_y` / `air_speed_y_stable`).
This tool measures what those numbers actually do to the attacker's descent and
prints the result against the frame windows of the donor's air-spin ACMD, so a
tuning change is a number on a page instead of a guess.

It reads the constants out of the Rust source, so it cannot drift from what is
compiled. It parses the donor's `ATTACK` calls to recover each air-spin window's
frame, box size and vertical offsets, which is what makes the descent argument a
measurement rather than a feeling.

It does **not** model the victim, the engine, or the hitbox/victim overlap test.
Everything it prints is arithmetic on two pinned inputs: the scales in
`hero_spin_params.rs` and the frame/offset literals in `hero_spin_acmd.rs`.

ATTACK argument order, from the locked `smash_script` `fdc6144` `macros.rs`:
`(id, part, bone, damage, angle, kbg, fkb, bkb, size, x, y, z, x2, y2, z2, ...)`,
so `size` is the shared box radius and `y`/`y2` the two box centres above the
bone. The vertical span of one window is therefore
`[min(y, y2) - size, max(y, y2) + size]`.

What it measures
----------------
* descent (positive = downward) at every air-spin hit window and at the end of
  the air motion;
* the vertical band each window's boxes cover relative to the attacker's own
  bone, and the union of those bands across the whole string;
* descent *between* consecutive windows against the band they have to share, the
  `gap` and `gap/band` columns: this is the descent-vs-retention relationship in
  one number per window;
* `rel = attacker_descent - reference_descent` against Mythra's own common air
  values, as a free-fall bound.

Read `gap/band` and `rel` honestly. `gap/band` is the fraction of its own box a
window travels before the next window opens: at or above 1 the boxes cannot
still be covering the same height, which is the offline form of "opponents fall
out". It says nothing about how fast the *victim* is moving, because a real
victim here is in hitstun and no pinned file records hitstun gravity. `rel` is
only the free-fall bound. Both are why `hero_spin_params.rs` records the
decision against the observed Switch traces and not against this table alone.

Usage
-----
    python tools/audit_hero_spin_airtime.py                 # table on stdout
    python tools/audit_hero_spin_airtime.py --json out.json # machine-readable
    python tools/audit_hero_spin_airtime.py --check          # offline self-test

Offline only (tier B over the source file). `--check` runs positive and negative
controls and needs no network, console, emulator or dump.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARAMS = ROOT / "src/pgwr/plugin/src/mythra/hero_spin_params.rs"
ACMD = ROOT / "src/pgwr/plugin/src/mythra/hero_spin_acmd.rs"

VERSION = "1.0.0"

# Donor air-spin hit windows, read out of `hi3_air_spin` in hero_spin_acmd.rs.
# Kept as an explicit list with a --check assertion against the file, because a
# silent mismatch here would make the table look authoritative and be wrong.
HIT_WINDOWS = [8, 11, 16, 19, 22, 26, 31, 38, 47, 48]

# ATTACK(...) argument positions after `agent`, from smash_script fdc6144:
#   0 id, 1 part, 2 bone, 3 damage, 4 angle, 5 kbg, 6 fkb, 7 bkb,
#   8 size, 9 x, 10 y, 11 z, 12 x2, 13 y2, 14 z2
SIZE_IDX, Y_IDX, Y2_IDX = 8, 10, 13
ATTACK_RE = re.compile(r"macros::ATTACK\(agent,\s*(?P<args>[^;]*?)\)\s*;")
LAST_ACTIVE_FRAME = 49  # the wait(1.0) after the 47/48 finisher boxes
AIR_MOTION_FRAMES = 85  # donor d02specialairhi3 length, per refs/mii_hero_spin_hi3/ASSESSMENT.md

CONST_RE = re.compile(
    r"pub const (?P<name>[A-Z0-9_]+): f32 = (?P<value>[-0-9.eE]+);"
)


def read_consts(path: Path = PARAMS) -> dict[str, float]:
    """Pull the f32 constants out of the Rust params file."""
    out: dict[str, float] = {}
    for match in CONST_RE.finditer(path.read_text(encoding="utf-8")):
        out[match.group("name")] = float(match.group("value"))
    return out


def parse_acmd_windows(path: Path = ACMD) -> list[dict]:
    """Per-hit-window geometry of `hi3_air_spin`.

    Each hit is a `frame(N)` followed by `if is_excute { ATTACK(..) }`, so the
    windows are exactly the `frame()` markers whose own block contains ATTACK.
    Each window's `size`/`y`/`y2` are read out of the donor's own literals; the
    band is the vertical span the window's boxes cover above the attacker's bone.

    Returns a list of `{frame, boxes, lo, hi}` in ACMD order.
    """
    text = path.read_text(encoding="utf-8")
    body = text.split('unsafe extern "C" fn hi3_air_spin', 1)[1]
    parts = re.split(r"frame\(agent\.lua_state_agent, (\d+)\.0\);", body)
    windows: list[dict] = []
    for idx in range(1, len(parts) - 1, 2):
        frame_no, block = int(parts[idx]), parts[idx + 1]
        boxes = []
        for match in ATTACK_RE.finditer(block):
            args = [a.strip() for a in match.group("args").split(",")]
            if len(args) <= Y2_IDX:
                continue
            size = float(args[SIZE_IDX])
            ys = [float(args[Y_IDX])]
            opt = args[Y2_IDX]
            if opt.startswith("Some("):
                ys.append(float(opt[5:-1]))
            boxes.append({"size": size, "y": ys, "lo": min(ys) - size,
                          "hi": max(ys) + size})
        if boxes:
            windows.append({
                "frame": frame_no,
                "boxes": boxes,
                "lo": min(b["lo"] for b in boxes),
                "hi": max(b["hi"] for b in boxes),
            })
    return windows


def descent(accel: float, stable: float, frames: int) -> list[float]:
    """Per-frame semi-implicit descent, starting at zero velocity and zero height.

    Matches how the game integrates the GRAVITY kinetic energy: accelerate by the
    accel each frame, clamp the magnitude at the stable speed, then move.
    """
    out = [0.0] * (frames + 1)
    v = 0.0
    y = 0.0
    for f in range(1, frames + 1):
        v += accel
        if v > stable:
            v = stable
        y -= v
        out[f] = y
    return out


def report(consts: dict[str, float], windows: list[dict]) -> dict:
    mii_a = consts["MII_HI3_AIR_ACCEL_Y"]
    mii_v = consts["MII_HI3_AIR_SPEED_Y_STABLE"]
    sa = consts["AIR_ACCEL_Y_SCALE"]
    sv = consts["AIR_SPEED_Y_SCALE"]
    # Mythra's own common air values, pinned in refs/mii_hero_spin_hi3/kinetic_manifest.json
    mythra_a, mythra_v = 0.13699999451637268, 1.8700000047683716

    n = AIR_MOTION_FRAMES
    ship = descent(mii_a * sa, mii_v * sv, n)
    raw = descent(mii_a, mii_v, n)
    ref = descent(mythra_a, mythra_v, n)
    frames = [w["frame"] for w in windows]

    def row(curve):
        return {f"f{f}": round(-curve[f], 2) for f in frames}

    # Descent since the previous window, against the band that window's boxes
    # cover. gap/band >= 1 means the boxes have moved at least their own height
    # before the next window opens, so they cannot still span one height.
    gaps: dict[str, dict] = {}
    for i, w in enumerate(windows):
        f = w["frame"]
        band = round(w["hi"] - w["lo"], 2)
        if i == 0:
            gaps[f"f{f}"] = {"frames_since_prev": None, "gap": None,
                             "band": band, "gap_over_band": None,
                             "lo": round(w["lo"], 2), "hi": round(w["hi"], 2)}
            continue
        pf = windows[i - 1]["frame"]
        gap = -ship[f] + ship[pf]
        gaps[f"f{f}"] = {
            "frames_since_prev": f - pf,
            "gap": round(gap, 2),
            "band": band,
            "gap_over_band": round(gap / band, 3),
            "lo": round(w["lo"], 2),
            "hi": round(w["hi"], 2),
        }

    return {
        "tool": f"audit_hero_spin_airtime.py {VERSION}",
        "source": str(PARAMS.relative_to(ROOT)),
        "acmd_source": str(ACMD.relative_to(ROOT)),
        "hit_windows": frames,
        "window_geometry": [
            {"frame": w["frame"], "lo": round(w["lo"], 2),
             "hi": round(w["hi"], 2),
             "boxes": [{"size": b["size"], "y": b["y"]} for b in w["boxes"]]}
            for w in windows
        ],
        "last_active_frame": LAST_ACTIVE_FRAME,
        "air_motion_frames": n,
        "mii_common": {"air_accel_y": mii_a, "air_speed_y_stable": mii_v},
        "shipped_scales": {"AIR_ACCEL_Y_SCALE": sa, "AIR_SPEED_Y_SCALE": sv},
        "effective": {
            "accel_y": round(mii_a * sa, 6),
            "stable_y": round(mii_v * sv, 6),
        },
        "mythra_freefall_reference": {
            "accel_y": mythra_a,
            "stable_y": mythra_v,
        },
        "descent_shipped": row(ship),
        "descent_mii_raw": row(raw),
        "descent_mythra_freefall": row(ref),
        "gap_vs_band": gaps,
        "rel_attacker_minus_freefall": {
            f"f{f}": round(-ship[f] + ref[f], 2) for f in frames
        },
        "totals": {
            "shipped_at_last_active": round(-ship[LAST_ACTIVE_FRAME], 2),
            "mii_raw_at_last_active": round(-raw[LAST_ACTIVE_FRAME], 2),
            "mythra_freefall_at_last_active": round(-ref[LAST_ACTIVE_FRAME], 2),
            "shipped_at_motion_end": round(-ship[n], 2),
            "mii_raw_at_motion_end": round(-raw[n], 2),
        },
        "monotone_down": all(ship[f] < ship[f - 1] for f in range(1, n + 1)),
    }


def print_table(data: dict) -> None:
    eff = data["effective"]
    sc = data["shipped_scales"]
    print("Hero's Spin aerial phase - attacker descent (positive = downward)")
    print(
        f"  applied accel  {eff['accel_y']:.4f} u/f^2   (Mii common {data['mii_common']['air_accel_y']:.4f} "
        f"x scale {sc['AIR_ACCEL_Y_SCALE']:.3f})"
    )
    print(
        f"  terminal speed {eff['stable_y']:.4f} u/f    (Mii common {data['mii_common']['air_speed_y_stable']:.4f} "
        f"x scale {sc['AIR_SPEED_Y_SCALE']:.3f})"
    )
    print()
    header = (f"{'frame':>6} {'descent':>9} {'band':>10} {'since':>6} "
              f"{'gap':>7} {'gap/band':>9} {'freefall':>9} {'rel':>8}")
    print(header)
    print("-" * len(header))
    for f in data["hit_windows"]:
        key = f"f{f}"
        g = data["gap_vs_band"][key]
        since = "-" if g["frames_since_prev"] is None else g["frames_since_prev"]
        gap = "-" if g["gap"] is None else f"{g['gap']:.1f}"
        ratio = "-" if g["gap_over_band"] is None else f"{g['gap_over_band']:.2f}"
        print(
            f"{f:>6} {data['descent_shipped'][key]:>9.1f} "
            f"{g['lo']:>5.1f}..{g['hi']:<4.1f} {since:>6} {gap:>7} {ratio:>9} "
            f"{data['descent_mythra_freefall'][key]:>9.1f} "
            f"{data['rel_attacker_minus_freefall'][key]:>8.1f}"
        )
    t = data["totals"]
    print()
    print(f"  descent at frame {data['last_active_frame']} (last finisher box): "
          f"shipped {t['shipped_at_last_active']:.1f}  "
          f"mii raw {t['mii_raw_at_last_active']:.1f}  "
          f"mythra free fall {t['mythra_freefall_at_last_active']:.1f}")
    print(f"  descent at frame {data['air_motion_frames']} (motion end):        "
          f"shipped {t['shipped_at_motion_end']:.1f}  "
          f"mii raw {t['mii_raw_at_motion_end']:.1f}")
    print()
    print(f"  monotone downward for all {data['air_motion_frames']} frames: "
          f"{data['monotone_down']}  (false would mean a hover)")
    print("  band    = vertical span the window's donor boxes cover above the bone")
    print("  gap     = descent since the previous window opened")
    print("  gap/band = how far the boxes travel, in units of their own height;")
    print("             >= 1.00 means consecutive windows cannot span one height")
    print("  freefall = a Mythra opponent NOT in hitstun. A hitstun victim falls at a")
    print("             rate no pinned file here records, so this is a bound only.")


def _check() -> int:
    failures: list[str] = []

    def require(cond: bool, msg: str) -> None:
        if not cond:
            failures.append(msg)

    consts = read_consts()
    for name in (
        "MII_HI3_AIR_ACCEL_Y",
        "MII_HI3_AIR_SPEED_Y_STABLE",
        "AIR_ACCEL_Y_SCALE",
        "AIR_SPEED_Y_SCALE",
    ):
        require(name in consts, f"constant {name} not found in {PARAMS.name}")

    windows = parse_acmd_windows()
    frames = [w["frame"] for w in windows]
    require(
        frames == HIT_WINDOWS,
        f"hit windows parsed from hero_spin_acmd.rs {frames} != documented {HIT_WINDOWS}",
    )
    for w in windows:
        require(w["hi"] > w["lo"], f"frame {w['frame']}: inverted band")
        require(
            len(w["boxes"]) >= 1,
            f"frame {w['frame']}: no ATTACK box parsed",
        )

    data = report(consts, windows)

    # positive: descent must be strictly increasing downward and land strictly
    # between the Mii raw values and zero, i.e. slower than the donor but moving.
    require(data["monotone_down"], "descent is not strictly downward (hover risk)")
    t = data["totals"]
    require(
        0.0 < t["shipped_at_last_active"] < t["mii_raw_at_last_active"],
        "shipped descent is not between 0 and the Mii raw descent",
    )
    require(
        data["effective"]["stable_y"] > 0.0,
        "terminal speed is not positive; the phase would stop falling",
    )
    require(
        0.0 < data["effective"]["accel_y"] < data["mii_common"]["air_accel_y"],
        "applied accel is not a positive reduction of the Mii value",
    )
    require(
        0.0 < data["shipped_scales"]["AIR_ACCEL_Y_SCALE"] <= 1.0
        and 0.0 < data["shipped_scales"]["AIR_SPEED_Y_SCALE"] <= 1.0,
        "a scale is outside (0, 1]: that is either no reduction or a hover",
    )
    # every window after the first must carry a measured gap/band
    for f in data["hit_windows"][1:]:
        require(
            data["gap_vs_band"][f"f{f}"]["gap_over_band"] is not None,
            f"frame {f}: no gap/band measured",
        )

    # negative control 1: a zero scale must read as a hover, so the monotone
    # assertion above is not vacuous.
    zeroed = dict(consts)
    zeroed["AIR_ACCEL_Y_SCALE"] = 0.0
    zeroed["AIR_SPEED_Y_SCALE"] = 0.0
    zero_data = report(zeroed, windows)
    require(
        zero_data["totals"]["shipped_at_last_active"] == 0.0,
        "negative control failed: zero scales did not produce zero descent",
    )
    require(
        all(
            zero_data["gap_vs_band"][f"f{f}"]["gap"] == 0.0
            for f in data["hit_windows"][1:]
        ),
        "negative control failed: zero scales did not produce zero gaps",
    )

    # negative control 2: raising a scale back to the Mii raw 1.0 must remove
    # every custom reduction, so the table is really driven by the scales.
    raw_consts = dict(consts)
    raw_consts["AIR_ACCEL_Y_SCALE"] = 1.0
    raw_consts["AIR_SPEED_Y_SCALE"] = 1.0
    raw_data = report(raw_consts, windows)
    require(
        abs(raw_data["totals"]["shipped_at_last_active"]
            - raw_data["totals"]["mii_raw_at_last_active"]) < 0.01,
        "negative control failed: scales of 1.0 do not reproduce the Mii raw descent",
    )
    require(
        raw_data["totals"]["shipped_at_last_active"]
        > data["totals"]["shipped_at_last_active"],
        "negative control failed: the Mii raw descent is not faster than the shipped one",
    )

    if failures:
        for f in failures:
            print(f"FAIL {f}", file=sys.stderr)
        return 1
    worst = max(
        (g["gap_over_band"], f)
        for f, g in data["gap_vs_band"].items()
        if g["gap_over_band"] is not None
    )
    print(f"PASS audit_hero_spin_airtime.py {VERSION} --check "
          f"(windows {frames}, shipped descent "
          f"{t['shipped_at_last_active']:.1f} u at frame {data['last_active_frame']}, "
          f"worst gap/band {worst[0]:.2f} at frame {worst[1][1:]}, "
          f"two negative controls fired)")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", type=Path, help="write the measurement as JSON here")
    ap.add_argument("--check", action="store_true", help="offline self-test")
    args = ap.parse_args(argv)

    if args.check:
        return _check()

    data = report(read_consts(), parse_acmd_windows())
    print_table(data)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))