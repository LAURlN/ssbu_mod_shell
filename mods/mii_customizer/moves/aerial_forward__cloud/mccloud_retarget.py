"""Retarget one Cloud body clip onto the Mii Gunner skeleton (shared by both Cloud units).

Same construction as the first pass of MV-aerial_forward__cloud (name intersection on the Gunner's idle
node set, donor-only nodes dropped and listed, world-space transfer for the four limbs whose parent differs,
ground-contact correction on Rot, visibility from the Gunner's idle), now a function of the clip.

Added 2026-10-08: `trans_scale` multiplies the Trans translation (root motion). Cloud's model scale is 0.98
and the Gunner's is 1.15 (fighter_param `scale`); the up special moves the fighter by Trans, so the factor
0.98 / 1.15 keeps Cloud's travel in world units. That the engine multiplies root motion by the model scale is
unverified (tier D).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from mccloud_common import WORKSPACE, G, DONOR, RECIPIENT, rel, sha256

sys.path.insert(0, str(WORKSPACE / 'mods/ssbu_mod_new/src/pgwr/tools'))  # read-only: pose helper
import ssbh_data_py as s  # noqa: E402
import pose_fk as fk  # noqa: E402

DONOR_IDLE = DONOR / 'fighter/cloud/motion/body/c00/a00wait1.nuanmb'
DONOR_SKEL = DONOR / 'fighter/cloud/model/body/c00/model.nusktb'
RECIPIENT_IDLE = RECIPIENT / 'fighter/miigunner/motion/body/c00/a00wait1.nuanmb'
RECIPIENT_SKEL = G / 'P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb'

LIMB_BONES = ('Hip', 'LegL', 'LegR', 'KneeL', 'KneeR', 'FootL', 'FootR', 'ToeL', 'ToeR')
ROT_EPS_DEG = 0.5
TRANS_EPS = 1e-3


def rot_angle_deg(a, b) -> float:
    qa = np.array(a, dtype=float)
    qb = np.array(b, dtype=float)
    d = abs(float(np.dot(qa, qb)))
    d = min(1.0, d)
    return float(np.degrees(2.0 * np.arccos(d)))


def retarget(donor_clip_path, clip_out, trans_scale=1.0, require_limb_motion=True) -> dict:
    clip_out = Path(clip_out)
    d_anim, d_clip = fk.read_transform_tracks(donor_clip_path)
    _, d_idle = fk.read_transform_tracks(DONOR_IDLE)
    r_anim, r_idle = fk.read_transform_tracks(RECIPIENT_IDLE)
    r_idle_anim = s.anim_data.read_anim(str(RECIPIENT_IDLE))
    r_vis = next(g for g in r_idle_anim.groups if g.group_type.name == 'Visibility')

    skel_d = fk.Skeleton(DONOR_SKEL)
    skel_r = fk.Skeleton(RECIPIENT_SKEL)

    n = fk.frame_count(d_clip)
    if n == 1:  # every track constant (Cloud's 2-frame dive loop): keep the donor's length
        n = int(d_anim.final_frame_index) + 1
    if n != int(d_anim.final_frame_index) + 1:
        raise RuntimeError(f'donor clip: {n} frames vs final index {d_anim.final_frame_index}')

    # Case-insensitive name matching (Smash hash40 is case-insensitive); the Gunner's own
    # spelling is written, and every case-only difference is reported.
    r_native = [name for name in r_idle]  # Gunner idle Transform node set, in file order
    r_lower = {name.lower(): name for name in r_native}
    kept, dropped, case_only = [], [], {}
    for name in d_clip:
        low = name.lower()
        if low in r_lower and low in {n_.lower() for n_ in skel_r.names}:
            target = r_lower[low]
            kept.append(target)
            if target != name:
                case_only[name] = target
        else:
            dropped.append(name)
    pose = [name for name in r_native if name.lower() in {k.lower() for k in kept}]
    kept_set = set(pose)

    # Node-set guard: every pose bone must exist on both skeletons and in both idles.
    for name in pose:
        if name not in skel_r.index:
            raise RuntimeError(f'pose bone {name} missing from the Gunner skeleton')
        donor_name = next(k for k in d_clip if k.lower() == name.lower())
        if donor_name not in skel_d.index or donor_name not in d_idle:
            raise RuntimeError(f'pose bone {name} missing from the donor skeleton or idle')

    # The donor idle must be unit scale: the donor/idle scale ratio is only meaningful then. The
    # recipient idle may carry small scales (Bust, Waist ~1.003-1.013); the composition multiplies them.
    for name in pose:
        donor_name = next(k for k in d_clip if k.lower() == name.lower())
        if max(abs(float(x) - 1.0) for x in d_idle[donor_name][0].scale) > 1e-4:
            raise RuntimeError(f'{donor_name} is scaled in the donor idle')
    recipient_scaled_idle = sorted(n_ for n_ in r_native
                                   if max(abs(float(x) - 1.0) for x in r_idle[n_][0].scale) > 1e-4)
    scaled_in_clip = sorted(next(k for k in d_clip if k.lower() == name.lower())
                            for name in pose
                            if any(abs(float(x) - 1.0) > 1e-4
                                   for v in d_clip[next(k for k in d_clip if k.lower() == name.lower())]
                                   for x in v.scale))

    # Vertical ground-contact correction needs Trans to be unrotated (as in the precedent).
    trans_d = d_clip.get('Trans', [])
    for v in trans_d:
        if abs(abs(float(v.rotation[3])) - 1.0) > 1e-4:
            raise RuntimeError('Trans rotates in the donor clip: the Rot correction would not be a world shift')

    parent_mismatch = []
    for name in pose:
        donor_name = next(k for k in d_clip if k.lower() == name.lower())
        dp = skel_d.parent[skel_d.index[donor_name]]
        rp = skel_r.parent[skel_r.index[name]]
        dpn = skel_d.names[dp].lower() if dp is not None else None
        rpn = skel_r.names[rp].lower() if rp is not None else None
        if dpn != rpn:
            parent_mismatch.append({'node': name, 'donor_parent': dpn, 'gunner_parent': rpn})
    mismatched = [m['node'] for m in parent_mismatch]

    out = {}
    for name in r_native:
        base_r = r_idle[name][0]
        if name not in kept_set:
            out[name] = [base_r] * n
            continue
        donor_name = next(k for k in d_clip if k.lower() == name.lower())
        base_d = d_idle[donor_name][0]
        frames = []
        for f in range(n):
            dv = fk.value_at(d_clip[donor_name], f)
            translation = [float(base_r.translation[i]) + float(dv.translation[i])
                           - float(base_d.translation[i]) for i in range(3)]
            frames.append(s.anim_data.Transform(
                [float(base_r.scale[i]) * float(dv.scale[i]) / float(base_d.scale[i]) for i in range(3)],
                [float(x) for x in dv.rotation], translation))
        out[name] = frames

    # Parent-chain differences (ClavicleL/R under ClavicleC vs Bust, LegL/R under LegC vs Hip). A
    # parent-local rotation copied across would bend the limb the wrong way, so the rotation is
    # carried in world space instead: the donor's world rotation change from its idle is applied to
    # the Gunner's idle world rotation, then converted to the Gunner's local frame each frame.
    world_space = []
    for name in mismatched:
        donor_name = next(k for k in d_clip if k.lower() == name.lower())
        i_d = skel_d.index[donor_name]
        i_r = skel_r.index[name]
        wd_idle = rot_of(skel_d.worlds(fk.locals_at(skel_d, d_idle, 0))[i_d])
        wr_idle = rot_of(skel_r.worlds(fk.locals_at(skel_r, r_idle, 0))[i_r])
        p_idx = skel_r.parent[i_r]
        for f in range(n):
            wd_f = rot_of(skel_d.worlds(fk.locals_at(skel_d, d_clip, f))[i_d])
            target = (wd_f @ wd_idle.T) @ wr_idle
            parent_world = rot_of(skel_r.worlds(fk.locals_at(skel_r, out, f))[p_idx])
            local = parent_world.T @ target
            v = out[name][f]
            out[name][f] = s.anim_data.Transform(list(v.scale), matrix_to_quat(local), list(v.translation))
        world_space.append(name)

    # Ground contact: keep the lower toe at the same clearance above its neutral stance as the donor's.
    if 'Rot' not in kept_set:
        raise RuntimeError('Rot is not a pose bone; the ground correction has no node to shift')
    contact_d_idle = fk.lowest_toe(skel_d, skel_d.worlds(fk.locals_at(skel_d, d_idle, 0)))
    contact_r_idle = fk.lowest_toe(skel_r, skel_r.worlds(fk.locals_at(skel_r, r_idle, 0)))
    corrections = []
    for f in range(n):
        target = contact_r_idle + (fk.lowest_toe(skel_d, skel_d.worlds(fk.locals_at(skel_d, d_clip, f)))
                                   - contact_d_idle)
        have = fk.lowest_toe(skel_r, skel_r.worlds(fk.locals_at(skel_r, out, f)))
        corrections.append(target - have)
    out['Rot'] = [s.anim_data.Transform(list(v.scale), list(v.rotation),
                                        [float(v.translation[0]), float(v.translation[1]) + corrections[f],
                                         float(v.translation[2])])
                  for f, v in enumerate(out['Rot'])]

    # Root motion: keep the donor's travel in world units on the larger Gunner model (see module docstring).
    if trans_scale != 1.0 and 'Trans' in kept_set:
        out['Trans'] = [s.anim_data.Transform(list(v.scale), list(v.rotation),
                                              [float(x) * trans_scale for x in v.translation])
                        for v in out['Trans']]
    trans_travel = [round(max(abs(float(v.translation[i])) for v in out['Trans']), 5) for i in range(3)]         if 'Trans' in out else None

    # ---- gates ----
    # The limb gate reads the OUTPUT clip: a limb the donor moves but the retarget freezes must fail.
    limb = {}
    for name in LIMB_BONES:
        if name not in r_native:
            raise RuntimeError(f'limb {name} is not a Gunner node')
        if name not in kept_set:
            limb[name] = {'kept': False}
            continue
        vals = out[name]
        rot = max(rot_angle_deg(v.rotation, vals[0].rotation) for v in vals)
        trn = max(max(abs(float(v.translation[i]) - float(vals[0].translation[i])) for i in range(3)) for v in vals)
        limb[name] = {'kept': True, 'max_rot_deg': round(rot, 3), 'max_trans': round(trn, 5)}
    static = [k for k, v in limb.items() if v.get('kept') and v['max_rot_deg'] < ROT_EPS_DEG and v['max_trans'] < TRANS_EPS]
    missing_limbs = [k for k, v in limb.items() if not v.get('kept')]
    if missing_limbs or (static and require_limb_motion):
        raise RuntimeError(f'limbs static or missing after retarget: static={static} missing={missing_limbs}')

    # ---- write the clip ----
    transform_nodes = [s.anim_data.NodeData(name, [s.anim_data.TrackData(
        'Transform', values=collapsed(out[name]))]) for name in r_native]
    vis_nodes = [s.anim_data.NodeData(node.name, [s.anim_data.TrackData(
        'Visibility', values=[node.tracks[0].values[0]])]) for node in r_vis.nodes]
    d_anim.groups = [s.anim_data.GroupData(s.anim_data.GroupType.Transform, transform_nodes),
                     s.anim_data.GroupData(s.anim_data.GroupType.Visibility, vis_nodes)]
    clip_out.parent.mkdir(parents=True, exist_ok=True)
    d_anim.save(str(clip_out))

    check = s.anim_data.read_anim(str(clip_out))
    got_groups = [(g.group_type.name, len(g.nodes)) for g in check.groups]
    got_nodes = [n_.name for n_ in next(g for g in check.groups if g.group_type.name == 'Transform').nodes]
    if got_nodes != r_native:
        raise RuntimeError('Transform node set changed after saving')
    if got_groups != [('Transform', len(r_native)), ('Visibility', len(vis_nodes))]:
        raise RuntimeError(f'unexpected groups after save: {got_groups}')

    return {
        'frames': n,
        'final_frame_index': float(d_anim.final_frame_index),
        'donor_transform_nodes': len(d_clip),
        
        'recipient_native_transform_nodes': len(r_native),
        'pose_nodes': pose,
        'kept_donor_nodes': len(kept),
        'dropped_donor_nodes': sorted(dropped),
        'case_only_name_differences': case_only,
        'held_at_recipient_idle': [n_ for n_ in r_native if n_ not in kept_set],
        'donor_scaled_pose_nodes': scaled_in_clip,
        'recipient_idle_scaled_nodes': recipient_scaled_idle,
        'parent_mismatches': parent_mismatch,
        'world_space_transfer_nodes': world_space,
        'limb_motion': limb,
        'static_limbs': static,
        'trans_scale': trans_scale,
        'trans_max_abs_translation': trans_travel,
        'ground_correction_range': [round(min(corrections), 5), round(max(corrections), 5)],
        'visibility_nodes_from_recipient_idle': [n_.name for n_ in vis_nodes],
        'material_group': 'dropped (donor carries EyeL/EyeR; precedent drops Material outright)',
        'clip_out': str(clip_out.relative_to(WORKSPACE)).replace('\\', '/'),
        'clip_sha256': sha256(clip_out),
    }


def rot_of(m) -> np.ndarray:
    """Nearest proper rotation to the 3x3 part of a 4x4 (scale removed by SVD, not column norms:
    the Gunner's Bust and Waist carry small non-uniform scales)."""
    r = np.array(m, dtype=float)[:3, :3]
    u, _, vt = np.linalg.svd(r)
    rot = u @ vt
    if np.linalg.det(rot) < 0:
        u[:, -1] *= -1
        rot = u @ vt
    return rot


def matrix_to_quat(r) -> list:
    """xyzw quaternion of a 3x3 rotation; the inverse of pose_fk.quat_to_matrix (checked in main)."""
    r = np.array(r, dtype=float)
    tr = r[0, 0] + r[1, 1] + r[2, 2]
    if tr > 0:
        s_ = np.sqrt(tr + 1.0) * 2
        w = 0.25 * s_
        x = (r[2, 1] - r[1, 2]) / s_
        y = (r[0, 2] - r[2, 0]) / s_
        z = (r[1, 0] - r[0, 1]) / s_
    elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
        s_ = np.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2]) * 2
        w = (r[2, 1] - r[1, 2]) / s_
        x = 0.25 * s_
        y = (r[0, 1] + r[1, 0]) / s_
        z = (r[0, 2] + r[2, 0]) / s_
    elif r[1, 1] > r[2, 2]:
        s_ = np.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2]) * 2
        w = (r[0, 2] - r[2, 0]) / s_
        x = (r[0, 1] + r[1, 0]) / s_
        y = 0.25 * s_
        z = (r[1, 2] + r[2, 1]) / s_
    else:
        s_ = np.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1]) * 2
        w = (r[1, 0] - r[0, 1]) / s_
        x = (r[0, 2] + r[2, 0]) / s_
        y = (r[1, 2] + r[2, 1]) / s_
        z = 0.25 * s_
    q = [float(x), float(y), float(z), float(w)]
    n_ = np.linalg.norm(q)
    q = [v / n_ for v in q]
    back = fk.quat_to_matrix(q)
    if np.max(np.abs(back - r)) > 1e-6:
        raise RuntimeError('matrix_to_quat does not invert quat_to_matrix')
    return q


def collapsed(values):
    def key(v):
        return (tuple(v.scale), tuple(v.rotation), tuple(v.translation))
    return values[:1] if len({key(v) for v in values}) == 1 else values


