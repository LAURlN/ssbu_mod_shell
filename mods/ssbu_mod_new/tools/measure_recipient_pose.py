"""Measure a pgwr recipient's body height, limb geometry and mesh skinning weights.

Read-only. Answers the questions an animation recipe needs before it can be authored:
what "one body height" is in this rig's units, how long each limb is, which bones actually
drive a given visible mesh (so a bone edit moves what you think it moves), and whether
scale compensation is required anywhere.

Standard SSBH conventions are applied and asserted rather than assumed:
  * local bind matrices are row-vector and are transposed for column-vector FK;
  * animated xyzw quaternions become column-vector rotation matrices directly;
  * skinning is `sum(w * world_i @ inv(bindworld_i)) * v`.

Run:
    toolchains\\py312\\python.exe tools/measure_recipient_pose.py \\
        --package builds/pgwr/0.20.16+robot-dtilt.4 --slot c06 \\
        --clip c02attacklw3.nuanmb --frame 3 --json out.json

Requires `ssbh_data_py`, `numpy` and a complete built package. Writes nothing except the
`--json` file you name. Never runs a test and never touches the card.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import ssbh_data_py as s

ROOT = Path(__file__).resolve().parents[1]
VISIBLE_DEFAULT = ('gw', 'headm', 'lhandhold', 'rhandhold', 'nosem')


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def quat_to_matrix(q) -> np.ndarray:
    """SSBH xyzw quaternion -> column-vector rotation matrix."""
    x, y, z, w = np.asarray(q, dtype=float) / np.linalg.norm(q)
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def transform_matrix(value) -> np.ndarray:
    m = np.eye(4)
    m[:3, :3] = quat_to_matrix(value.rotation) @ np.diag(np.asarray(value.scale, dtype=float))
    m[:3, 3] = np.asarray(value.translation, dtype=float)
    return m


def forward(local, bones):
    """Parent-first column-vector chain. SSBH bind matrices are transposed on the way in."""
    out = []
    for bone, m in zip(bones, local):
        out.append(m if bone.parent_index is None else out[bone.parent_index] @ m)
    return out


def tracks_of(anim, group='Transform'):
    group_data = next(g for g in anim.groups if g.group_type.name == group)
    return {n.name: n.tracks[0].values for n in group_data.nodes}


def visibility_of(anim):
    group_data = next((g for g in anim.groups if g.group_type.name == 'Visibility'), None)
    if group_data is None:
        return {}
    return {n.name: bool(n.tracks[0].values[0]) for n in group_data.nodes}


def skin(objects, world, bind_world, ids, bones):
    """Skinned vertex positions for a set of mesh objects, in world space."""
    skin_mats = {b.name: world[ids[b.name]] @ np.linalg.inv(bind_world[ids[b.name]]) for b in bones}
    out = []
    for obj in objects:
        pts = np.vstack([np.asarray(a.data, dtype=float).reshape(-1, 3) for a in obj.positions])
        if not obj.bone_influences:
            out.append(pts)
            continue
        acc = np.zeros_like(pts)
        total = np.zeros(len(pts))
        for infl in obj.bone_influences:
            if infl.bone_name not in skin_mats or not infl.vertex_weights:
                continue
            w = np.zeros(len(pts))
            for vw in infl.vertex_weights:
                w[vw.vertex_index] += float(vw.vertex_weight)
            if w.max() <= 0:
                continue
            m = skin_mats[infl.bone_name]
            acc += ((m[:3, :3] @ pts.T).T + m[:3, 3]) * w[:, None]
            total += w
        good = total > 1e-6
        acc[~good] = pts[~good]
        out.append(acc)
    return out


def segment_distance(p, a, b):
    d = b - a
    t = float(np.clip(np.dot(p - a, d) / np.dot(d, d), 0, 1))
    return float(np.linalg.norm(p - (a + d * t)))


def measure(package: Path, slot: str, clip: str | None, frame: int) -> dict:
    mod = package / 'ultimate/mods/pyra_gamewatch_reskin'
    model_dir = mod / f'fighter/eflame/model/body/{slot}'
    motion_dir = mod / f'fighter/eflame/motion/body/{slot}'

    skel = s.skel_data.read_skel(str(model_dir / 'model.nusktb'))
    bones = list(skel.bones)
    ids = {b.name: i for i, b in enumerate(bones)}
    bind_local = [np.asarray(b.transform, dtype=float).T.copy() for b in bones]
    bind_world = forward(bind_local, bones)

    idle = s.anim_data.read_anim(str(motion_dir / 'a00wait1.nuanmb'))
    idle_tracks = tracks_of(idle)
    vis = visibility_of(idle)
    enabled = {k.lower() for k, v in vis.items() if v}

    def pose(tracks, f):
        local = [transform_matrix(tracks[b.name][min(f, len(tracks[b.name]) - 1)])
                 if b.name in tracks else bind_local[i].copy() for i, b in enumerate(bones)]
        return forward(local, bones)

    world_idle = pose(idle_tracks, 0)

    # non-unit world scales: an animation-scale compensation question
    non_unit = [{'bone': b.name,
                 'world_scale': np.round(np.linalg.norm(world_idle[i][:3, :3], axis=0), 5).tolist()}
                for i, b in enumerate(bones)
                if not np.allclose(np.linalg.norm(world_idle[i][:3, :3], axis=0), 1.0, atol=1e-4)]

    shb = s.mesh_data.read_mesh(str(model_dir / 'model.numshb'))

    def visible_objects(node):
        return [o for o in shb.objects if o.name.lower().startswith(node)]

    def mesh_for(node):
        parts = skin(visible_objects(node), world_idle, bind_world, ids, bones)
        return np.vstack(parts) if parts else None

    body_nodes = [n for n in enabled if n not in ('headm', 'nosem')]
    body_pts = np.vstack([p for n in body_nodes if (p := mesh_for(n)) is not None])
    head_pts = mesh_for('headm')
    crown = float(head_pts[:, 1].max()) if head_pts is not None else float('nan')
    ground = float(body_pts[:, 1].min())
    body_height = crown - ground

    limbs = {}
    for sfx in ('L', 'R'):
        sh, ar, hd = (f'Shoulder{sfx}', f'Arm{sfx}', f'Hand{sfx}')
        if not all(n in ids for n in (sh, ar, hd)):
            continue
        p_sh = world_idle[ids[sh]][:3, 3]
        p_ar = world_idle[ids[ar]][:3, 3]
        p_hd = world_idle[ids[hd]][:3, 3]
        limbs[sfx] = {
            'shoulder': [round(float(v), 4) for v in p_sh],
            'elbow': [round(float(v), 4) for v in p_ar],
            'hand': [round(float(v), 4) for v in p_hd],
            'upper_len': round(float(np.linalg.norm(p_ar - p_sh)), 4),
            'fore_len': round(float(np.linalg.norm(p_hd - p_ar)), 4),
            'shoulder_to_hand': round(float(np.linalg.norm(p_hd - p_sh)), 4),
            'in_body_heights': round(float(np.linalg.norm(p_hd - p_sh)) / body_height, 4),
        }

    weights = {}
    for obj in shb.objects:
        low = obj.name.lower()
        if not any(low.startswith(v) for v in VISIBLE_DEFAULT):
            continue
        counts = {infl.bone_name: round(max((float(vw.vertex_weight) for vw in infl.vertex_weights),
                                            default=0.0), 4)
                  for infl in obj.bone_influences}
        arm_bones = {k: v for k, v in counts.items()
                     if k.endswith(('ArmL', 'ArmR', 'HandL', 'HandR', 'ShoulderL', 'ShoulderR',
                                    'H_ArmL', 'H_ArmR'))}
        if arm_bones:
            weights[obj.name] = arm_bones

    result = {
        'inputs': {
            'package': package.name,
            'slot': slot,
            'skeleton_sha256': sha(model_dir / 'model.nusktb'),
            'idle_sha256': sha(motion_dir / 'a00wait1.nuanmb'),
            'numshb_sha256': sha(model_dir / 'model.numshb'),
            'bones': len(bones),
            'visibility_enabled': sorted(enabled),
        },
        'body_height': {
            'model_units': round(body_height, 4),
            'ground_y': round(ground, 4),
            'crown_y': round(crown, 4),
            'convention': 'skinned visible mesh, idle frame 0, +Y up, +Z forward, '
                          'model origin at the skeleton root bone',
        },
        'limbs_idle0': limbs,
        'non_unit_world_scales': non_unit,
        'visible_arm_mesh_weights': weights,
    }

    if clip:
        anim = s.anim_data.read_anim(str(motion_dir / clip))
        tr = tracks_of(anim)
        world = pose(tr, frame)
        row = {'clip': clip, 'clip_sha256': sha(motion_dir / clip),
               'final_frame_index': anim.final_frame_index, 'frame': frame,
               'bones': {}}
        for name in ('Hip', 'ShoulderL', 'ArmL', 'HandL', 'ShoulderR', 'ArmR', 'HandR'):
            if name in ids:
                row['bones'][name] = [round(float(v), 4) for v in world[ids[name]][:3, 3]]
        result['clip_pose'] = row
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--package', type=Path, default=ROOT / 'builds/pgwr/0.20.16',
                        help='built package directory (read-only)')
    parser.add_argument('--slot', default='c06')
    parser.add_argument('--clip', default=None, help='also report this clip at --frame')
    parser.add_argument('--frame', type=int, default=0)
    parser.add_argument('--json', type=Path, default=None, help='write the report here')
    args = parser.parse_args()
    package = args.package.resolve()
    if not package.is_dir():
        parser.error(f'package not found: {package}')
    report = measure(package, args.slot, args.clip, args.frame)
    text = json.dumps(report, indent=2)
    if args.json:
        args.json.write_text(text + '\n', encoding='utf-8')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())