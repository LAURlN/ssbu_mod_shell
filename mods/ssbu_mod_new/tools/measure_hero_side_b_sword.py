#!/usr/bin/env python
"""Measure the `sword1` joint frame of Hero's side-B on the donor and on the recipient.

Purpose: an effect attached with `EFFECT_FOLLOW(..., "sword1", pos, rot, ...)` inherits the
joint's world rotation, so a donor effect only points the donor's way on the recipient if
`R_recipient(t) * R_offset == R_donor(t)`. This tool measures both joint frames by forward
kinematics, frame by frame, and prints the residual rotation that is left after the offset
the plugin currently applies - as an axis, an angle, and the pitch (elevation) of each joint
axis in the fighter's sagittal plane - so an orientation correction is chosen from numbers
instead of from a guess.

It reads only: a donor skeleton + clip, a recipient skeleton + clip. It writes nothing but
the optional `--json` report. Tier B: it measures files. It proves nothing about what the
console draws; in particular the effect's own emission axis is not in these files.

Conventions (the same ones `measure_recipient_pose.py` verified against the visible mesh):
SSBH local bind matrices are row-vector and are transposed for column-vector FK; animated
`xyzw` quaternions become column-vector rotation matrices directly. A bone a clip does not
animate keeps its bind-local transform. Model space: +Y up, +Z the facing direction.

Usage:
  python tools/measure_hero_side_b_sword.py \
      --donor-skel refs/brave_special_s/arc/fighter/brave/model/body/c06/model.nusktb \
      --donor-clip refs/brave_special_s/arc/fighter/brave/motion/body/c06/d01specials2.nuanmb \
      --recipient-skel ../../gamedata/ssbu-13.0.4/files/fighter/elight/model/body/c06/model.nusktb \
      --recipient-clip builds/pgwr/<package>/ultimate/mods/pyra_gamewatch_reskin/fighter/elight/motion/body/c06/pgwrherospecials2.nuanmb \
      --offset-z -90 --first 10 --last 29 [--json out.json]
  python tools/measure_hero_side_b_sword.py --smoke

`--solve` additionally derives the offset the measurement asks for. The emission axis of a
donor effect attached with a zero rotation is the donor joint's +X, so the wanted direction in
the recipient joint's own frame is `R_recipient(t)^T * x_donor(t)`, averaged over the window.
The engine's Euler composition order for the `rot` triple is not established offline, so the
solver returns a triple `(rx, ry, rz)` whose **direction is the same under both common orders**
(`Rz*Ry*Rx` and `Rx*Ry*Rz`): `rz`, `ry` place the axis under the first, and `rx` - a pure roll
about the emission axis under the first - is what places it under the second. Only the roll
about the bolt's own axis differs between the two, and that is reported, not hidden.
`--rot RX RY RZ` evaluates a given triple the same way.

`--check-nro NRO --rot RX RY RZ [--nro-baseline NRO]` checks that a built plugin carries the
triple as f32 constants and that the baseline build does not (it reads no game file).

`--python-path` (or env PGWR_PYLIBS) names a directory holding `ssbh_data_py`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from pathlib import Path

VERSION = "1.2.0"


def _libs(extra: str | None) -> None:
    for cand in (extra, os.environ.get("PGWR_PYLIBS")):
        if cand:
            sys.path.insert(0, str(Path(cand)))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quat_to_mat(np, q):
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def rot_axis(np, axis: str, degrees: float):
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    if axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def axis_angle(np, r):
    """Rotation matrix -> (unit axis, angle in degrees)."""
    cos = max(-1.0, min(1.0, (np.trace(r) - 1.0) / 2.0))
    angle = math.degrees(math.acos(cos))
    v = np.array([r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1]])
    n = np.linalg.norm(v)
    return (v / n if n > 1e-9 else np.array([0.0, 0.0, 1.0])), angle


def pitch(v) -> float:
    """Elevation of a model-space direction above the horizontal, in degrees.

    Measured in the sagittal plane the user looks at: +Y is up, Z is the facing axis, and
    the sideways X component is what the camera does not show."""
    return math.degrees(math.atan2(v[1], abs(v[2]) if abs(v[2]) > 1e-9 else 1e-9))


def euler(np, order: str, rx: float, ry: float, rz: float):
    """`zyx`: R = Rz*Ry*Rx (X applied first). `xyz`: R = Rx*Ry*Rz (Z applied first)."""
    x, y, z = rot_axis(np, "x", rx), rot_axis(np, "y", ry), rot_axis(np, "z", rz)
    return z @ y @ x if order == "zyx" else x @ y @ z


ORDERS = ("zyx", "xyz")


def solve_direction(v):
    """(rx, ry, rz) in degrees sending +X onto unit `v` under both orders in `ORDERS`."""
    ry = math.degrees(math.asin(max(-1.0, min(1.0, -v[2]))))
    rz = math.degrees(math.atan2(v[1], v[0]))
    a, b = math.radians(rz), math.radians(ry)
    before = math.atan2(-math.cos(a) * math.sin(b), math.sin(a))
    rx = math.degrees(math.atan2(v[2], v[1]) - before)
    rx = (rx + 180.0) % 360.0 - 180.0
    return rx, ry, rz


def angle_between(np, a, b) -> float:
    return math.degrees(math.acos(max(-1.0, min(1.0, float(a @ b)))))


class Rig:
    def __init__(self, np, ssbh, skel: Path, clip: Path | None):
        self.np = np
        self.skel_path, self.clip_path = skel, clip
        s = ssbh.skel_data.read_skel(str(skel))
        self.names = [b.name for b in s.bones]
        self.parent = [b.parent_index for b in s.bones]
        self.bind = [np.array(b.transform, dtype=float).T for b in s.bones]
        self.tracks = {}
        self.final_frame = 0.0
        if clip is not None:
            a = ssbh.anim_data.read_anim(str(clip))
            self.final_frame = a.final_frame_index
            for group in a.groups:
                if getattr(group.group_type, "name", str(group.group_type)) != "Transform":
                    continue
                for node in group.nodes:
                    for track in node.tracks:
                        self.tracks[node.name] = track.values

    def local(self, i: int, frame: int):
        np = self.np
        vals = self.tracks.get(self.names[i])
        if not vals:
            return self.bind[i]
        t = vals[min(frame, len(vals) - 1)]
        m = np.eye(4)
        m[:3, :3] = quat_to_mat(np, t.rotation) @ np.diag(t.scale)
        m[:3, 3] = t.translation
        return m

    def world(self, name: str, frame: int):
        i = self.names.index(name)
        m = self.local(i, frame)
        p = self.parent[i]
        while p is not None and p >= 0:
            m = self.local(p, frame) @ m
            p = self.parent[p]
        return m

    def chain(self, name: str) -> list[str]:
        i = self.names.index(name)
        out = [name]
        p = self.parent[i]
        while p is not None and p >= 0:
            out.append(self.names[p])
            p = self.parent[p]
        return out


def unit_rot(np, m):
    r = m[:3, :3].copy()
    for c in range(3):
        r[:, c] /= np.linalg.norm(r[:, c]) or 1.0
    return r


def measure(np, ssbh, args) -> dict:
    donor = Rig(np, ssbh, Path(args.donor_skel), Path(args.donor_clip))
    recip = Rig(np, ssbh, Path(args.recipient_skel), Path(args.recipient_clip))
    joint = args.joint
    offset = rot_axis(np, "z", args.offset_z)
    frames = []
    for f in range(args.first, args.last + 1):
        rd = unit_rot(np, donor.world(joint, f))
        rr = unit_rot(np, recip.world(joint, f))
        eff = rr @ offset                       # what the recipient's effect inherits now
        residual = eff.T @ rd                   # still needed, in the effect's own frame
        axis, angle = axis_angle(np, residual)
        world_res = rd @ eff.T                  # same residual, expressed in model space
        waxis, _ = axis_angle(np, world_res)
        frames.append({
            "frame": f,
            "donor_axes_pitch_deg": [round(pitch(rd[:, c]), 3) for c in range(3)],
            "recipient_axes_pitch_deg": [round(pitch(eff[:, c]), 3) for c in range(3)],
            "pitch_excess_deg": [round(pitch(eff[:, c]) - pitch(rd[:, c]), 3) for c in range(3)],
            "residual_angle_deg": round(angle, 3),
            "residual_axis_effect_frame": [round(float(x), 4) for x in axis],
            "residual_axis_model_space": [round(float(x), 4) for x in waxis],
            "donor_axes": [[round(float(x), 4) for x in rd[:, c]] for c in range(3)],
            "recipient_axes": [[round(float(x), 4) for x in eff[:, c]] for c in range(3)],
        })
    solved = None
    triple = None
    if args.rot:
        triple = tuple(args.rot)
    elif args.solve:
        acc = np.zeros(3)
        for f in range(args.first, args.last + 1):
            rd = unit_rot(np, donor.world(joint, f))
            rr = unit_rot(np, recip.world(joint, f))
            acc += rr.T @ rd[:, 0]
        mean = acc / np.linalg.norm(acc)
        triple = solve_direction(mean)
        if args.round is not None:
            triple = tuple(round(x, args.round) for x in triple)
        solved = [round(float(x), 5) for x in mean]
    evaluation = None
    if triple is not None:
        evaluation = {"rot_deg": [float(x) for x in triple], "wanted_axis_in_joint_frame": solved,
                      "orders": {}}
        for order in ORDERS:
            off = euler(np, order, *triple)
            worst_dir, worst_pitch, rolls = 0.0, 0.0, []
            for f in range(args.first, args.last + 1):
                rd = unit_rot(np, donor.world(joint, f))
                eff = unit_rot(np, recip.world(joint, f)) @ off
                worst_dir = max(worst_dir, angle_between(np, eff[:, 0], rd[:, 0]))
                worst_pitch = max(worst_pitch, abs(pitch(eff[:, 0]) - pitch(rd[:, 0])))
                # roll: angle of the effect's Y about the donor's X, against the donor's Y
                y = eff[:, 1] - (eff[:, 1] @ rd[:, 0]) * rd[:, 0]
                y /= np.linalg.norm(y) or 1.0
                rolls.append(math.degrees(math.atan2(float(np.cross(rd[:, 1], y) @ rd[:, 0]),
                                                     float(rd[:, 1] @ y))))
            evaluation["orders"][order] = {
                "max_direction_error_deg": round(worst_dir, 4),
                "max_pitch_error_deg": round(worst_pitch, 4),
                "roll_about_bolt_axis_deg": [round(min(rolls), 3), round(max(rolls), 3)],
            }
    return {
        "evaluation": evaluation,
        "tool": "tools/measure_hero_side_b_sword.py v" + VERSION,
        "tier": "B",
        "joint": joint,
        "offset_z_deg": args.offset_z,
        "donor": {"skel": str(donor.skel_path), "skel_sha256": sha256(donor.skel_path),
                  "clip": str(donor.clip_path), "clip_sha256": sha256(donor.clip_path),
                  "final_frame": donor.final_frame, "chain": donor.chain(joint),
                  "animated": [n for n in donor.chain(joint) if n in donor.tracks]},
        "recipient": {"skel": str(recip.skel_path), "skel_sha256": sha256(recip.skel_path),
                      "clip": str(recip.clip_path), "clip_sha256": sha256(recip.clip_path),
                      "final_frame": recip.final_frame, "chain": recip.chain(joint),
                      "animated": [n for n in recip.chain(joint) if n in recip.tracks]},
        "frames": frames,
    }


def f32_sites(blob: bytes, value: float) -> dict:
    """Where a compiled AArch64 binary can hold an f32 constant: a 4-byte literal, or a
    single `movz w, #imm16, lsl #16` when the low half of its bit pattern is zero."""
    import struct
    bits = struct.unpack("<I", struct.pack("<f", value))[0]
    out = {"bits": "%#010x" % bits, "literal": blob.count(struct.pack("<I", bits)), "movz": 0}
    if bits & 0xFFFF == 0:
        word = 0x52A00000 | ((bits >> 16) << 5)
        out["movz"] = sum(blob.count(struct.pack("<I", word | reg)) for reg in range(31))
    return out


def check_nro(nro: Path, baseline: Path | None, triple) -> tuple[dict, int]:
    """The built plugin must carry the triple; the baseline must not carry all of it."""
    blob = nro.read_bytes()
    report = {"nro": str(nro), "sha256": hashlib.sha256(blob).hexdigest(), "values": {}}
    failures = 0
    for value in triple:
        sites = f32_sites(blob, value)
        report["values"][str(value)] = sites
        if sites["literal"] + sites["movz"] == 0:
            failures += 1
    if baseline is not None:
        base = baseline.read_bytes()
        report["baseline"] = {"nro": str(baseline), "sha256": hashlib.sha256(base).hexdigest(),
                              "values": {str(v): f32_sites(base, v) for v in triple}}
        # Negative control: a value pair that exists nowhere in the baseline is what makes
        # "present" mean "this change", not "some float that was always there".
        new = [v for v in triple
               if f32_sites(base, v)["literal"] + f32_sites(base, v)["movz"] == 0]
        report["absent_from_baseline"] = [str(v) for v in new]
        if not new:
            failures += 1
    return report, failures


def smoke() -> int:
    """Self-test of the arithmetic, with no game file: a known rotation must come back."""
    import numpy as np
    failures = []
    r = rot_axis(np, "x", 7.5)
    axis, angle = axis_angle(np, r)
    if abs(angle - 7.5) > 1e-9 or abs(axis[0] - 1.0) > 1e-9:
        failures.append("axis_angle did not return 7.5 deg about +x: %r %r" % (axis, angle))
    # A direction raised by 12 degrees must report a pitch of 12, on either facing.
    for z in (1.0, -1.0):
        v = np.array([0.3, math.tan(math.radians(12.0)), z])
        if abs(pitch(v) - 12.0) > 1e-9:
            failures.append("pitch(%r) = %r, expected 12" % (v, pitch(v)))
    # Negative control: the identity is not a 7.5 degree rotation.
    if abs(axis_angle(np, np.eye(3))[1]) > 1e-9:
        failures.append("identity reported a non-zero angle")
    q = quat_to_mat(np, (0.0, 0.0, math.sin(math.radians(-45)), math.cos(math.radians(-45))))
    if np.abs(q - rot_axis(np, "z", -90)).max() > 1e-9:
        failures.append("quaternion and matrix disagree on Rz(-90)")
    # The solver must put +X on the wanted axis under BOTH composition orders.
    want = np.array([0.10718, -0.94401, -0.31202])
    want /= np.linalg.norm(want)
    triple = solve_direction(want)
    for order in ORDERS:
        got = euler(np, order, *triple)[:, 0]
        if angle_between(np, got, want) > 1e-6:
            failures.append("solver misses the axis under %s by %r deg"
                            % (order, angle_between(np, got, want)))
    # Negative control: without rx the second order must NOT reach it, or rx is decorative.
    if angle_between(np, euler(np, "xyz", 0.0, triple[1], triple[2])[:, 0], want) < 5.0:
        failures.append("rx is not what places the axis under xyz; the solver proves nothing")
    # Negative control: the offset this tool was written to correct is measurably off.
    if angle_between(np, euler(np, "zyx", 0.0, 0.0, -90.0)[:, 0], want) < 10.0:
        failures.append("Rz(-90) already reaches the wanted axis; the residual is not real")
    for line in failures:
        print("FAIL\t%s" % line, file=sys.stderr)
    if not failures:
        print("PASS\taxis-angle, pitch, quaternion and two-order solver agree (8 checks)")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--donor-skel")
    ap.add_argument("--donor-clip")
    ap.add_argument("--recipient-skel")
    ap.add_argument("--recipient-clip")
    ap.add_argument("--joint", default="Sword1")
    ap.add_argument("--offset-z", type=float, default=-90.0,
                    help="rot_z the plugin passes for the effect on the recipient")
    ap.add_argument("--first", type=int, default=10)
    ap.add_argument("--last", type=int, default=29)
    ap.add_argument("--solve", action="store_true",
                    help="derive the offset that puts the emission axis on the donor's")
    ap.add_argument("--round", type=int, help="round the solved triple to N decimals")
    ap.add_argument("--rot", type=float, nargs=3, metavar=("RX", "RY", "RZ"),
                    help="evaluate this offset triple instead of solving")
    ap.add_argument("--check-nro", help="built plugin that must carry --rot as f32 constants")
    ap.add_argument("--nro-baseline", help="plugin built without the change (negative control)")
    ap.add_argument("--python-path")
    ap.add_argument("--json")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    _libs(args.python_path)
    if args.smoke:
        return smoke()
    if args.check_nro:
        if not args.rot:
            ap.error("--check-nro needs --rot RX RY RZ")
        report, failures = check_nro(Path(args.check_nro),
                                     Path(args.nro_baseline) if args.nro_baseline else None,
                                     args.rot)
        print(json.dumps(report, indent=2))
        if args.json:
            Path(args.json).parent.mkdir(parents=True, exist_ok=True)
            Path(args.json).write_text(json.dumps(report, indent=2) + chr(10), encoding="utf-8")
        print("# %d NRO check(s) not matching" % failures)
        return 1 if failures else 0
    for need in ("donor_skel", "donor_clip", "recipient_skel", "recipient_clip"):
        if not getattr(args, need):
            ap.error("--%s is required unless --smoke is given" % need.replace("_", "-"))
    import numpy as np
    import ssbh_data_py as ssbh
    report = measure(np, ssbh, args)
    print("# joint %s, offset rot_z %s" % (report["joint"], report["offset_z_deg"]))
    for side in ("donor", "recipient"):
        print("# %-9s chain %s" % (side, " <- ".join(report[side]["chain"])))
        print("# %-9s animated %s" % (side, ", ".join(report[side]["animated"])))
    print("frame  residual  axis(effect frame)          axis(model space)           pitch excess x/y/z")
    for row in report["frames"]:
        print("%5d  %7.3f   %-26s  %-26s  %s" % (
            row["frame"], row["residual_angle_deg"],
            row["residual_axis_effect_frame"], row["residual_axis_model_space"],
            row["pitch_excess_deg"]))
    ev = report["evaluation"]
    if ev:
        print("# offset rot (rx, ry, rz) = %s" % (ev["rot_deg"],))
        if ev["wanted_axis_in_joint_frame"]:
            print("# wanted +X in the recipient joint frame = %s" % ev["wanted_axis_in_joint_frame"])
        for order, row in ev["orders"].items():
            print("#   order %s: max direction error %.4f deg, max pitch error %.4f deg, "
                  "roll about the bolt axis %s deg"
                  % (order, row["max_direction_error_deg"], row["max_pitch_error_deg"],
                     row["roll_about_bolt_axis_deg"]))
    if args.json:
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print("# wrote %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
