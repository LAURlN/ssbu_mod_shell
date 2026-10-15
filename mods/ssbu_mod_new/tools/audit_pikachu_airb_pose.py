"""Measure the retargeted Pikachu back-air clips in world space (v1.0.0).

    python -B tools/audit_pikachu_airb_pose.py                    # shipped package
    python -B tools/audit_pikachu_airb_pose.py --package <dir>
    python -B tools/audit_pikachu_airb_pose.py --negative-controls
    python -B tools/audit_pikachu_airb_pose.py --json out.json

What 1.0.0 got wrong, and why no earlier check saw it
------------------------------------------------------
1.0.0 kept 45 of the donor's 55 Transform nodes **with their donor values**, and
every earlier gate (node count, parent-chain names, "do the limbs move") passed.
But an animation `Transform` is *absolute*: it carries the translation of every
bone as well as its rotation, and the donor's translations are **Pikachu's bone
offsets**. Measured on the pinned data, the donor clip's frame-0 translations
equal Pikachu's rest offsets, not G&W's - `ShoulderL` 2.35 vs 0.29, `HandL` 0.65
vs 2.43, `Bust` 2.27 vs 0, `Head` 0 vs 0.81 - so the "retargeted" skeleton was
Pikachu's, drawn under G&W's skinned mesh at G&W's bind pose. This tool measures
that directly (forward kinematics over both skeletons) and checks the 1.1.0
construction instead:

* the clip carries exactly the recipient's 41 native Transform nodes and its own
  98-node idle mesh-visibility group;
* the 25 pose bones keep the donor's **absolute rotations** (the limbs' bind
  rotations agree to within 6 degrees on both rigs, so the same joint angles
  give the same limb directions - measured below) and the donor's **motion** in
  translation, applied on the recipient's own bone offsets;
* every other native node is held at the recipient idle;
* root motion (`Trans`) is the donor's, unscaled, because the hitboxes hang off
  `Trans` and must travel the donor's path;
* the lowest toe keeps the same clearance above its own neutral stance that the
  donor's keeps above his, so G&W neither sinks nor hovers (and the landing ends
  on its own idle height instead of popping).

Tier B: offline geometry. It cannot say how the clip looks; skinning, the
G&W mesh and the engine's own pose handling are tier D.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import shutil
import sys
import tempfile
from pathlib import Path

import numpy as np
import ssbh_data_py as s

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
sys.path.insert(0, str(ROOT / 'tools'))
import pose_fk as fk  # noqa: E402
import audit_pikachu_airb_hitboxes as hitboxes  # noqa: E402

BASELINE = ROOT / 'builds/pgwr/0.20.23/ultimate/mods/pyra_gamewatch_reskin'
PACKAGE = ROOT / 'builds/pgwr/pikachu-airb-1.1.0'
OLD_PACKAGE = ROOT / 'builds/pgwr/pikachu-airb-1.0.0'
REF = ROOT / 'refs/pikachu_attack_air_b/arc/fighter/pikachu'
DONOR_MOTION = REF / 'motion/body/c00'
DONOR_SKEL = REF / 'model/body/c00/model.nusktb'
DONOR_IDLE = DONOR_MOTION / 'a00wait1.nuanmb'
SLOTS = ('c06', 'c07')
CLIPS = {'attack_air_b': 'c05attackairb.nuanmb', 'landing_air_b': 'c05landingairb.nuanmb'}

POSE_BONES = ('Trans', 'Rot', 'Hip', 'Waist', 'Bust', 'Neck', 'Head',
              'ClavicleC', 'ClavicleL', 'ClavicleR', 'ShoulderL', 'ShoulderR',
              'ArmL', 'ArmR', 'HandL', 'HandR', 'LegC', 'LegL', 'LegR',
              'KneeL', 'KneeR', 'FootL', 'FootR', 'ToeL', 'ToeR')
# Segments whose joint angles map one-to-one between the rigs (their bind
# rotations agree to <6 degrees and their offset directions are the same).
LIMB_SEGMENTS = (('LegC', 'LegL'), ('LegC', 'LegR'), ('LegL', 'KneeL'),
                 ('LegR', 'KneeR'), ('KneeL', 'FootL'), ('KneeR', 'FootR'),
                 ('ShoulderL', 'ArmL'), ('ShoulderR', 'ArmR'),
                 ('ArmL', 'HandL'), ('ArmR', 'HandR'))
BODY_JOINTS = ('FootL', 'FootR', 'KneeL', 'KneeR', 'ToeL', 'ToeR', 'HandL', 'HandR',
               'Head', 'Hip', 'Waist', 'Bust', 'LegL', 'LegR', 'ArmL', 'ArmR')

# Gates. Each is set against a measured value with margin and has a negative
# control; none is decorative.
TOL_OFFSET = 1e-4          # donor motion applied exactly on the recipient offsets
TOL_ROT_DEG = 1e-2         # absolute donor rotation preserved
TOL_CONTACT = 1e-3         # per-frame ground contact equals its target
TOL_SEGMENT_DEG = {'attack_air_b': 1.0, 'landing_air_b': 3.0}   # the landing squashes Rot
TOL_END_POP = 0.05         # landing ends on the recipient's own idle height


def _tracks(path):
    return fk.read_transform_tracks(path)


def _vis(path):
    anim = s.anim_data.read_anim(str(path))
    group = next(g for g in anim.groups if g.group_type.name == 'Visibility')
    return [(n.name, [bool(v) for v in n.tracks[0].values]) for n in group.nodes]


def _segment_dir(skel, worlds, a, b):
    return worlds[skel.index[b]][:3, 3] - worlds[skel.index[a]][:3, 3]


def _dist_to_box(point, a, b):
    if b is None:
        return float(np.linalg.norm(point - a))
    ab = b - a
    t = float(np.clip(np.dot(point - a, ab) / np.dot(ab, ab), 0.0, 1.0))
    return float(np.linalg.norm(point - (a + t * ab)))


def analyse(clip_path: Path, kind: str, skel_path: Path, idle_path: Path) -> dict:
    skel, dskel = fk.Skeleton(skel_path), fk.Skeleton(DONOR_SKEL)
    out_anim, out = _tracks(clip_path)
    donor_anim, donor = _tracks(DONOR_MOTION / CLIPS[kind])
    _, idle_r = _tracks(idle_path)
    _, idle_d = _tracks(DONOR_IDLE)
    n = fk.frame_count(donor)
    m = {'clip': clip_path.name, 'frames_donor': n, 'frames_out': fk.frame_count(out),
         'final_frame_index': [out_anim.final_frame_index, donor_anim.final_frame_index]}

    native = list(idle_r)
    m['node_set_equals_recipient_native'] = list(out) == native
    m['nodes_out'] = len(out)
    m['visibility_equals_recipient_idle'] = _vis(clip_path) == _vis(idle_path)

    # Rotations: absolute donor values on the pose bones.
    rot_dev = 0.0
    for bone in POSE_BONES:
        if bone not in out:
            continue
        for f in range(n):
            a = fk.rotation_of(fk.transform_matrix(fk.value_at(out[bone], f)))
            b = fk.rotation_of(fk.transform_matrix(fk.value_at(donor[bone], f)))
            rot_dev = max(rot_dev, fk.angle_between(a, b))
    m['pose_rotation_max_deviation_deg'] = round(rot_dev, 5)

    # Translations: the donor's motion, on the recipient's own offsets.
    imposed, per_bone = 0.0, {}
    for bone in POSE_BONES:
        if bone not in out:
            continue
        base_r = np.array(idle_r[bone][0].translation, dtype=float)
        base_d = np.array(idle_d[bone][0].translation, dtype=float)
        worst, drift = 0.0, 0.0
        for f in range(n):
            t_o = np.array(fk.value_at(out[bone], f).translation, dtype=float)
            t_d = np.array(fk.value_at(donor[bone], f).translation, dtype=float)
            want = base_r + (t_d - base_d)
            diff = t_o - want
            if bone == 'Rot':
                diff = np.array([diff[0], 0.0, diff[2]])   # y carries the contact correction
            worst = max(worst, float(np.linalg.norm(diff)))
            drift = max(drift, float(np.linalg.norm(t_o - base_r)))
        imposed = max(imposed, worst)
        per_bone[bone] = {'max_motion_from_recipient_offset': round(drift, 4),
                          'recipient_offset_length': round(float(np.linalg.norm(base_r)), 4),
                          'donor_offset_length': round(float(np.linalg.norm(base_d)), 4)}
    m['translation_error_vs_construction_max'] = round(imposed, 6)
    m['per_bone'] = per_bone
    m['max_donor_offset_imposed'] = round(max(
        float(np.linalg.norm(np.array(fk.value_at(out[b], 0).translation, dtype=float)
                             - np.array(idle_r[b][0].translation, dtype=float)))
        - float(np.linalg.norm(np.array(fk.value_at(donor[b], 0).translation, dtype=float)
                               - np.array(idle_d[b][0].translation, dtype=float)))
        for b in POSE_BONES if b in out and b not in ('Trans', 'Rot', 'Hip')), 4)

    # Native nodes that are not pose bones: held at the recipient idle.
    held = 0.0
    for name in native:
        if name in POSE_BONES or name not in out:
            continue
        a = fk.transform_matrix(idle_r[name][0])
        for f in range(max(1, fk.frame_count(out))):
            b = fk.transform_matrix(fk.value_at(out[name], f))
            held = max(held, float(np.abs(a - b).max()))
    m['native_hold_max_deviation'] = round(held, 6)

    # Root motion: Trans is the donor's, unscaled.
    root = 0.0
    if 'Trans' in out:
        for f in range(n):
            root = max(root, float(np.linalg.norm(
                np.array(fk.value_at(out['Trans'], f).translation, dtype=float)
                - np.array(fk.value_at(donor['Trans'], f).translation, dtype=float))))
    m['trans_root_motion_error'] = round(root, 6)
    z = [float(fk.value_at(donor['Trans'], f).translation[2]) for f in range(n)]
    m['trans_z_range'] = [round(min(z), 3), round(max(z), 3)]

    # World-space pose: donor on Pikachu's skeleton vs the clip on the recipient's.
    dworlds = [dskel.worlds(fk.locals_at(dskel, donor, f)) for f in range(n)]
    oworlds = [skel.worlds(fk.locals_at(skel, out, f)) for f in range(n)]
    seg = {}
    for a, b in LIMB_SEGMENTS:
        errs = []
        for f in range(n):
            u, v = _segment_dir(dskel, dworlds[f], a, b), _segment_dir(skel, oworlds[f], a, b)
            if np.linalg.norm(u) > 0.25 and np.linalg.norm(v) > 0.25:
                c = float(np.dot(u, v) / np.linalg.norm(u) / np.linalg.norm(v))
                errs.append(math.degrees(math.acos(max(-1.0, min(1.0, c)))))
        seg[f'{a}->{b}'] = {'mean_deg': round(float(np.mean(errs)), 3),
                            'max_deg': round(float(np.max(errs)), 3), 'frames': len(errs)}
    m['limb_segment_direction_error'] = seg
    m['limb_segment_mean_worst_deg'] = max(v['mean_deg'] for v in seg.values())

    # Ground contact.
    c_d_idle = fk.lowest_toe(dskel, dskel.worlds(fk.locals_at(dskel, idle_d, 0)))
    c_r_idle = fk.lowest_toe(skel, skel.worlds(fk.locals_at(skel, idle_r, 0)))
    err = 0.0
    contact = []
    for f in range(n):
        want = c_r_idle + (fk.lowest_toe(dskel, dworlds[f]) - c_d_idle)
        have = fk.lowest_toe(skel, oworlds[f])
        err = max(err, abs(have - want))
        contact.append(have)
    m['ground_contact_error_max'] = round(err, 5)
    m['lowest_toe_height'] = {'min': round(min(contact), 3), 'max': round(max(contact), 3),
                              'first': round(contact[0], 3), 'last': round(contact[-1], 3),
                              'recipient_idle': round(c_r_idle, 3),
                              'donor_idle': round(c_d_idle, 3)}
    m['end_height_error_vs_recipient_idle'] = round(abs(contact[-1] - c_r_idle), 4)
    rot_y = [float(fk.value_at(out['Rot'], f).translation[1])
             - (float(idle_r['Rot'][0].translation[1])
                + float(fk.value_at(donor['Rot'], f).translation[1])
                - float(idle_d['Rot'][0].translation[1])) for f in range(n)]
    m['rot_y_correction'] = {'min': round(min(rot_y), 3), 'max': round(max(rot_y), 3),
                             'max_step': round(max((abs(b - a) for a, b in zip(rot_y, rot_y[1:])),
                                                   default=0.0), 3)}

    # Hitbox-to-body alignment (attack only: its script frames are clip frames).
    if kind == 'attack_air_b':
        rows = hitboxes.table(hitboxes.donor_events(kind))
        windows = {}
        for r in rows:
            key = (r['open'], r['id'])
            f = int(r['open'])
            for label, skl, worlds in (('recipient', skel, oworlds), ('donor_on_pikachu', dskel, dworlds)):
                tw = worlds[f][skl.index['Trans']]
                a = (tw @ np.array([r['x'], r['y'], r['z'], 1.0]))[:3]
                b = None if r['y2'] is None else (tw @ np.array([r['x2'], r['y2'], r['z2'], 1.0]))[:3]
                best = min(((_dist_to_box(worlds[f][skl.index[j]][:3, 3], a, b), j)
                            for j in BODY_JOINTS))
                windows.setdefault(f'f{f} id{r["id"]}', {'radius': r['size']})[label] = {
                    'nearest_joint': best[1], 'distance': round(best[0], 2)}
        m['hitbox_alignment'] = windows
        m['hitbox_windows_overlapping_body'] = sum(
            1 for w in windows.values() if w['recipient']['distance'] <= w['radius'])
        m['hitbox_windows'] = len(windows)
    return m


def verdict(m: dict, kind: str) -> list:
    bad = []

    def need(ok, text):
        if not ok:
            bad.append(text)

    need(m['node_set_equals_recipient_native'],
         f'node set is not the recipient native set ({m["nodes_out"]} nodes)')
    need(m['visibility_equals_recipient_idle'], 'visibility group differs from the recipient idle')
    need(m['frames_out'] == m['frames_donor'] and
         m['final_frame_index'][0] == m['final_frame_index'][1],
         f'duration differs from the donor: {m["frames_out"]}/{m["final_frame_index"]}')
    need(m['pose_rotation_max_deviation_deg'] <= TOL_ROT_DEG,
         f'pose rotations deviate from the donor by {m["pose_rotation_max_deviation_deg"]} deg')
    need(m['translation_error_vs_construction_max'] <= TOL_OFFSET,
         f'translations differ from recipient offset + donor motion by '
         f'{m["translation_error_vs_construction_max"]} (donor bone offsets imposed?)')
    need(m['max_donor_offset_imposed'] <= TOL_OFFSET,
         f'a bone sits {m["max_donor_offset_imposed"]} further from the recipient offset '
         f'than the donor moved it')
    need(m['native_hold_max_deviation'] <= 1e-5,
         f'native non-pose nodes deviate from the recipient idle by {m["native_hold_max_deviation"]}')
    need(m['trans_root_motion_error'] <= 1e-6,
         f'Trans root motion differs from the donor by {m["trans_root_motion_error"]}')
    need(m['limb_segment_mean_worst_deg'] <= TOL_SEGMENT_DEG[kind],
         f'limb segment direction error {m["limb_segment_mean_worst_deg"]} deg')
    need(m['ground_contact_error_max'] <= TOL_CONTACT,
         f'ground contact off by {m["ground_contact_error_max"]}')
    if kind == 'landing_air_b':
        need(m['end_height_error_vs_recipient_idle'] <= TOL_END_POP,
             f'landing ends {m["end_height_error_vs_recipient_idle"]} off the recipient idle height')
    if kind == 'attack_air_b':
        need(m['hitbox_windows_overlapping_body'] == m['hitbox_windows'],
             f'{m["hitbox_windows"] - m["hitbox_windows_overlapping_body"]} hitbox window(s) '
             f'contain no body joint')
    return bad


def package_clip(pkg: Path, slot: str, kind: str) -> Path:
    return pkg / 'ultimate/mods/pyra_gamewatch_reskin/fighter/eflame/motion/body' / slot / CLIPS[kind]


def run(pkg: Path) -> tuple:
    results, failures = {}, []
    for slot in SLOTS:
        base = BASELINE / 'fighter/eflame'
        skel = base / 'model/body' / slot / 'model.nusktb'
        idle = base / 'motion/body' / slot / 'a00wait1.nuanmb'
        for kind in CLIPS:
            clip = package_clip(pkg, slot, kind)
            if not clip.is_file():
                failures.append(f'{slot}/{kind}: {clip} missing')
                continue
            m = analyse(clip, kind, skel, idle)
            results[f'{slot}/{kind}'] = m
            failures += [f'{slot}/{kind}: {x}' for x in verdict(m, kind)]
    return results, failures


# ---------------------------------------------------------------------------
# Negative controls
# ---------------------------------------------------------------------------

def _damaged(src: Path, tmp: Path, fn) -> Path:
    anim = s.anim_data.read_anim(str(src))
    fn(anim)
    dst = tmp / src.name
    anim.save(str(dst))
    return dst


def _node(anim, name):
    group = next(g for g in anim.groups if g.group_type.name == 'Transform')
    return next(n for n in group.nodes if n.name == name)


def negative_controls(pkg: Path) -> int:
    base = BASELINE / 'fighter/eflame'
    skel = base / 'model/body/c06/model.nusktb'
    idle = base / 'motion/body/c06/a00wait1.nuanmb'
    good = package_clip(pkg, 'c06', 'attack_air_b')
    good_l = package_clip(pkg, 'c06', 'landing_air_b')
    donor_a = _tracks(DONOR_MOTION / CLIPS['attack_air_b'])[1]
    ok = {'attack_air_b': good, 'landing_air_b': good_l}
    results, caught = [], 0

    def expect_bad(label, clip, kind):
        nonlocal caught
        bad = verdict(analyse(clip, kind, skel, idle), kind)
        results.append((label, bool(bad), bad[:1]))
        caught += bool(bad)

    # Positive control first: an undamaged package must be accepted.
    pos = [verdict(analyse(ok[k], k, skel, idle), k) for k in ok]
    positive = not any(pos)

    old = package_clip(OLD_PACKAGE, 'c06', 'attack_air_b')
    cases = 0
    if old.is_file():
        cases += 1
        expect_bad('the real 1.0.0 clip (donor bone offsets imposed)', old, 'attack_air_b')
        cases += 1
        expect_bad('the real 1.0.0 landing clip',
                   package_clip(OLD_PACKAGE, 'c06', 'landing_air_b'), 'landing_air_b')
        # The node-set gate alone would reject the old clip; the point of the
        # *offset* gate is that it independently sees the defect itself.
        cases += 1
        bad = verdict(analyse(old, 'attack_air_b', skel, idle), 'attack_air_b')
        hit = [b for b in bad if 'imposed' in b]
        results.append(('the real 1.0.0 clip trips the offset gate by itself', bool(hit), hit[:1]))
        caught += bool(hit)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        def waist_from_donor(anim):
            node = _node(anim, 'Waist')
            node.tracks[0].values = list(donor_a['Waist'])

        def arm_rotated(anim):
            node = _node(anim, 'ArmL')
            vals = list(node.tracks[0].values)
            node.tracks[0].values = [s.anim_data.Transform(
                list(v.scale), [v.rotation[0] + 0.15, v.rotation[1], v.rotation[2], v.rotation[3]],
                list(v.translation)) for v in vals]

        def no_correction(anim):
            node = _node(anim, 'Rot')
            idle_rot = _tracks(idle)[1]['Rot'][0]
            dr = donor_a['Rot']
            d_idle = _tracks(DONOR_IDLE)[1]['Rot'][0]
            node.tracks[0].values = [s.anim_data.Transform(
                list(v.scale), list(v.rotation),
                [float(idle_rot.translation[i]) + float(dr[min(f, len(dr) - 1)].translation[i])
                 - float(d_idle.translation[i]) for i in range(3)])
                for f, v in enumerate(node.tracks[0].values)]

        def node_dropped(anim):
            group = next(g for g in anim.groups if g.group_type.name == 'Transform')
            group.nodes = [n for n in group.nodes if n.name != 'Sparky']

        def trans_scaled(anim):
            node = _node(anim, 'Trans')
            node.tracks[0].values = [s.anim_data.Transform(
                list(v.scale), list(v.rotation), [x * 1.19 for x in v.translation])
                for v in node.tracks[0].values]

        def visibility_flipped(anim):
            group = next(g for g in anim.groups if g.group_type.name == 'Visibility')
            group.nodes[0].tracks[0].values = [not group.nodes[0].tracks[0].values[0]]

        def duration_cut(anim):
            anim.final_frame_index = anim.final_frame_index + 5

        for label, fn in (('Waist carries the donor offsets again', waist_from_donor),
                          ('ArmL rotation perturbed', arm_rotated),
                          ('ground-contact correction removed', no_correction),
                          ('a native node (Sparky) dropped', node_dropped),
                          ('Trans root motion scaled by 1.19', trans_scaled),
                          ('visibility group changed', visibility_flipped),
                          ('final frame index lengthened (duration differs from the donor)', duration_cut)):
            cases += 1
            expect_bad(label, _damaged(good, tmp, fn), 'attack_air_b')
        # Landing: a clip that pops at the end - remove the correction there too.
        cases += 1
        expect_bad('landing: ground-contact correction removed',
                   _damaged(good_l, tmp, lambda a: _land_no_correction(a, idle)), 'landing_air_b')

    for label, was_caught, why in results:
        print(f'{"PASS" if was_caught else "FAIL"}: {label}: {why[0] if why else "NOT REJECTED"}')
    print(f'positive control (undamaged package accepted): {"PASS" if positive else "FAIL"} {pos}')
    print(f'{caught}/{cases} damaged inputs rejected; 1/1 undamaged accepted'
          if positive else f'{caught}/{cases} damaged inputs rejected; UNDAMAGED REJECTED')
    return 0 if caught == cases and positive else 1


def _land_no_correction(anim, idle):
    donor_l = _tracks(DONOR_MOTION / CLIPS['landing_air_b'])[1]
    idle_rot = _tracks(idle)[1]['Rot'][0]
    d_idle = _tracks(DONOR_IDLE)[1]['Rot'][0]
    node = _node(anim, 'Rot')
    dr = donor_l['Rot']
    node.tracks[0].values = [s.anim_data.Transform(
        list(v.scale), list(v.rotation),
        [float(idle_rot.translation[i]) + float(dr[min(f, len(dr) - 1)].translation[i])
         - float(d_idle.translation[i]) for i in range(3)])
        for f, v in enumerate(node.tracks[0].values)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--package', type=Path, default=PACKAGE)
    ap.add_argument('--json', type=Path)
    ap.add_argument('--negative-controls', action='store_true')
    args = ap.parse_args()
    if args.negative_controls:
        return negative_controls(args.package)
    results, failures = run(args.package)
    for key, m in results.items():
        print(f'{key}: {m["frames_out"]} frames, {m["nodes_out"]} nodes; pose rot dev '
              f'{m["pose_rotation_max_deviation_deg"]} deg; offset error '
              f'{m["translation_error_vs_construction_max"]}; limb segment worst mean '
              f'{m["limb_segment_mean_worst_deg"]} deg; contact error {m["ground_contact_error_max"]}; '
              f'Rot y correction {m["rot_y_correction"]}; toe y {m["lowest_toe_height"]}')
        if 'hitbox_alignment' in m:
            print(f'   hitbox windows overlapping a body joint: '
                  f'{m["hitbox_windows_overlapping_body"]}/{m["hitbox_windows"]}')
    for f in failures:
        print('FAIL:', f)
    if args.json:
        args.json.write_text(json.dumps({'results': results, 'failures': failures}, indent=1),
                             encoding='utf-8')
    print('audit_pikachu_airb_pose', 'FAILED' if failures else 'OK')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
