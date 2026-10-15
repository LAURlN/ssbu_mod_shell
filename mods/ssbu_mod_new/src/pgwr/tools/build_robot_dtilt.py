"""Author G&W down tilt on the built recipient skeleton (v3.0.0).

Donor: R.O.B. (`refs/robot_attack_lw3/arc/fighter/robot`, live-extracted 2026-09-30,
provenance `refs/robot_attack_lw3/SOURCE.json`).
Recipient: Pyra c06/c07 (eflame, reskinned to G&W).
Hitboxes/effects/sound/rumble: `plugin/src/acmd/robot_attack_lw3.rs`.
Cancel frame: `attack_lw3` = 15, taken whole from R.O.B.'s own motion list entry.

What changed in 3.0.0 (T-0048; design record
`evidence/2026-10-02_pgwr_T-0045/T-0047_design_record.md`)
---------------------------------------------------------------------------
2.0.0 drove both arms through the same two-link `solve_limb` as the legs and asked for
wrist goals ~5x further away than a G&W arm is long. `solve_limb` clamps the request to
the links' reach, so the unreachable part of each goal was silently dropped and the pose
peaked well short of the capsule. 3.0.0 does not push those goals through the old IK:

* Each arm is deformed as a **rigid block rooted at `Shoulder{L,R}`**. The shoulder bone is
  rotated so the shoulder->hand direction points along a recipe-supplied aim direction, then
  translated in model axes so the hand lands `arm_reach` body heights ahead of its own idle
  position. `Arm{L,R}`, `Hand{L,R}` and the helper bones are children and ride along
  untouched, which is what makes the block rigid.
* This is the only lever that is both shear-free and size-preserving. Measured
  alternatives, from the T-0047 record: translating `Hand{L,R}` moves no visible geometry
  (weight 0 on the fist mesh), translating `Arm{L,R}` alone shears the fist (z-extent
  5.751 -> 4.185), and scaling grows the fist's cross-section (x 1.21 / y 1.80 at 2.2x).
* Transform serialization is **scale-aware and orthonormal-safe**: `decompose()` splits any
  3x3 into an orthonormal rotation and a positive axis-aligned scale, `quaternion()`
  orthonormalizes before extracting, and the emitted `Transform` carries the bone's actual
  scale instead of a hardcoded `[1,1,1]`. This recipe writes unit scale - no bone is scaled -
  and the generator *measures and reports* that, so "hands, head and body keep their
  proportions" is a checked invariant rather than a side effect of the emit path.

Preserved (unchanged from 2.0.0)
--------------------------------
* The donor's raw `attack_lw3` motion-list entry, whole (flags 0x80, cancel 15, R.O.B.'s
  own script hashes), and c06/c07 routing.
* Recipient bind transforms and built idle as the base pose; explicit tracks for all 165
  bones including grafted helpers; planted feet via leg IK; visibility copied from the
  recipient idle (no Material tracks, no skeleton edit).
* Gameplay: ACMD, hitbox, effects, sounds, rumble, slope, duration 28, active frame 3,
  clear frame 4, cancel 15.

Unverified
----------
Mesh deformation on screen, palm/hitbox alignment, facing mirroring, slopes and recovery
feel are tier D and need the user's console judgment. `preview()` is a joint authoring
diagram, not a render. The CLI stages an animation-only variant of an existing complete
release, preserving its core version and both packaged NROs. It never runs tests, compiles
Rust or installs to the card.
"""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import math
import os
import re
import struct
import zlib

import ssbh_data_py as s
import numpy as np

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
EXPORT = ROOT / 'dumps/arc'
DONOR = ROOT / 'refs/robot_attack_lw3/arc/fighter/robot/motion/body/c00'
ACMD = ROOT / 'src/pgwr/plugin/src/acmd/robot_attack_lw3.rs'

KIND = 'attack_lw3'
CLIP = 'c02attacklw3.nuanmb'
PINS = {
    CLIP: ('dd265d1cbad5d36ae5b4401c335893d2e3f578fc8319960381109758f13d6879', 33808),
    'motion_list.bin': ('456434191c6de18a1a12d49e0f821347fe2abb48b813d80ee45054c57caebdad', 43256),
}
EXPECTED_CANCEL = 15
EXPECTED_FLAGS = 0x80
RECIPE = ROOT / 'src/pgwr/assets/robot_dtilt/recipe.json'
# Lab-wide shared-build reservation (see the T-0036 record for its original use).
LOCK = ROOT.parents[1] / 'state/pgwr-shared-build.lock'


def hash40(name):
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pinned(name):
    path = DONOR / name
    digest, size = PINS[name]
    if not path.is_file() or path.stat().st_size != size or sha(path) != digest:
        raise RuntimeError(f'{path} missing or not the pinned revision')
    return path


def get_entry(target_kind=hash40(KIND)):
    """R.O.B.'s own raw `attack_lw3` entry, whole, from the extracted motion list."""
    data = _pinned('motion_list.bin').read_bytes()
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    if magic != hash40('motion'):
        raise RuntimeError('robot motion_list.bin is not a motion list')
    offset = 24
    for _ in range(count):
        start = offset
        kind, game_script, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = (offset + n_anims * 9 + 3) & ~3
        end = offset + size
        if kind == target_kind:
            cancel = struct.unpack_from('<H', data, end - 2)[0] if size % 8 == 4 else None
            if anims != (hash40(CLIP),):
                raise RuntimeError(f'R.O.B. {KIND} no longer names {CLIP}: {[hex(a) for a in anims]}')
            if cancel != EXPECTED_CANCEL or flags != EXPECTED_FLAGS:
                raise RuntimeError(f'R.O.B. {KIND}: cancel {cancel} flags {flags:#x} differ from the pinned reading')
            return {'raw': data[start:end], 'kind': kind, 'game_script': game_script,
                    'flags': flags, 'blend': blend, 'n_anims': n_anims, 'anims': anims,
                    'size': size, 'cancel': cancel}
        offset = end
    raise RuntimeError(f'R.O.B. motion list has no kind {target_kind:#x}')


def active_hitbox(path=ACMD):
    """The frame-3 capsule, parsed out of the donor's own `game_attacklw3`.

    Read from the source rather than copied, so the preview overlay and the generation report
    cannot drift away from the capsule the engine is asked to evaluate.
    """
    text = Path(path).read_text(encoding='utf-8')
    body = text.split('fn game_attacklw3', 1)[1].split('\nfn ', 1)[0]
    call = re.sub(r'//.*', '', body.split('macros::ATTACK(', 1)[1])
    token = r'(?:Some\(\s*(-?[0-9.]+)\s*\)|(-?[0-9.]+))'
    number = lambda pair: float(pair[0] or pair[1])  # noqa: E731 - one capture form is empty
    head = re.search(r'Hash40::new\("top"\)\s*,\s*(' + r'\s*,\s*'.join([token] * 9) + r')', call)
    if not head:
        raise RuntimeError('game_attacklw3: could not read the down-tilt capsule arguments')
    values = [number(pair) for pair in re.findall(token, head.group(1))]
    damage, angle, knockback, base, kind, radius, x, y, z = values[:9]
    if kind != 2:
        raise RuntimeError(f'game_attacklw3 down tilt is not a capsule (kind {kind})')
    hit = {'damage': damage, 'angle': angle, 'knockback': knockback, 'base': base,
           'kind': kind, 'radius': radius, 'start': [x, y, z]}
    end = [number(pair) for pair in re.findall(token, call[head.end():])[:3]]
    if len(end) == 3:
        hit['end'] = end
    hit['source_sha256'] = sha(path)
    return hit


def rotation(q):
    """SSBH xyzw quaternion to a column-vector rotation matrix."""
    x, y, z, w = np.asarray(q) / np.linalg.norm(q)
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                     [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                     [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])


def decompose(m):
    """Split a 3x3 into an orthonormal rotation and a positive axis-aligned scale.

    `M = R @ diag(s)` needs the *columns* of `M` to be the scaled columns of `R`, in order, so
    the rotation is Gram-Schmidt over `M`'s own columns and the scale is each column's
    length. That is the only construction that holds for a rotation, whose `M M^T` is the
    identity and therefore has no usable eigenbasis to read the axes from. Extracting a
    quaternion straight from a non-orthonormal `M` (the previous behaviour) folds any scale
    silently into the rotation, so every rotation read goes through here.

    Gram-Schmidt is only unstable when two columns are near-parallel, which for a bone
    matrix means a degenerate transform; that case is rejected rather than approximated, and
    `det > 0` guarantees a proper rotation with positive scales.
    """
    m = np.asarray(m, dtype=float)[:3, :3]
    if float(np.linalg.det(m)) <= 0:
        raise ValueError('bone transform is not a proper rotation with positive scale')
    rot = np.zeros((3, 3))
    for i in range(3):
        v = m[:, i].copy()
        for j in range(i):
            v -= (rot[:, j] @ v) * rot[:, j]
        length = float(np.linalg.norm(v))
        if length < 1e-9:
            raise ValueError('bone transform columns are degenerate; cannot separate scale from rotation')
        rot[:, i] = v / length
    return rot, np.linalg.norm(m, axis=0)


def quaternion(value):
    # Largest eigenvector avoids trace singularities at 180-degree bind rotations.
    rot, _ = decompose(value)
    k = np.array([[rot[0,0]-rot[1,1]-rot[2,2], rot[0,1]+rot[1,0], rot[0,2]+rot[2,0], rot[2,1]-rot[1,2]],
                  [rot[0,1]+rot[1,0], rot[1,1]-rot[0,0]-rot[2,2], rot[1,2]+rot[2,1], rot[0,2]-rot[2,0]],
                  [rot[0,2]+rot[2,0], rot[1,2]+rot[2,1], rot[2,2]-rot[0,0]-rot[1,1], rot[1,0]-rot[0,1]],
                  [rot[2,1]-rot[1,2], rot[0,2]-rot[2,0], rot[1,0]-rot[0,1], np.trace(rot)]]) / 3
    _, vectors = np.linalg.eigh(k)
    return vectors[:, -1]


def matrix(value):
    m = np.eye(4)
    m[:3, :3] = decompose(rotation(value.rotation) @ np.diag(value.scale))[0] @ np.diag(value.scale)
    m[:3, 3] = value.translation
    return m


def world_pose(local, bones):
    result = []
    for b, m in zip(bones, local):
        result.append(m if b.parent_index is None else result[b.parent_index] @ m)
    return result


def turn(a, b):
    a, b = a / np.linalg.norm(a), b / np.linalg.norm(b)
    axis = np.cross(a, b)
    dot = float(np.clip(np.dot(a, b), -1, 1))
    if dot < -0.999999:
        axis = np.cross(a, [1, 0, 0] if abs(a[0]) < .9 else [0, 1, 0])
        axis /= np.linalg.norm(axis)
        return 2 * np.outer(axis, axis) - np.eye(3)
    skew = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + skew + skew @ skew / max(1 + dot, 1e-9)


def solve_limb(local, bones, ids, names, target, pole, end_rotation):
    """Two-link IK using recipient segment lengths, preserving translations/scales.

    Feet only, deliberately. The request is clamped to the links' reach, so a goal beyond
    limb length would be truncated silently; the arms therefore do not go through here, and
    `deform_arm` reports the deficit instead of hiding it.
    """
    upper, lower, end = [ids[n] for n in names]
    world = world_pose(local, bones)
    start = world[upper][:3, 3]
    first = np.linalg.norm(local[lower][:3, 3])
    second = np.linalg.norm(local[end][:3, 3])
    delta = target - start
    requested = np.linalg.norm(delta)
    direction = delta / max(requested, 1e-9)
    distance = float(np.clip(requested, abs(first-second)+.001, first+second-.001))
    side = np.asarray(pole) - direction * np.dot(pole, direction)
    side /= np.linalg.norm(side)
    along = (first*first-second*second+distance*distance)/(2*distance)
    elbow = start + direction*along + side*math.sqrt(max(0, first*first-along*along))
    reached = start + direction*distance
    for joint, child, goal in ((upper, lower, elbow), (lower, end, reached)):
        world = world_pose(local, bones)
        orient = turn(world[child][:3, 3]-world[joint][:3, 3], goal-world[joint][:3, 3]) @ world[joint][:3,:3]
        parent = bones[joint].parent_index
        local[joint][:3,:3] = world[parent][:3,:3].T @ orient
    world = world_pose(local, bones)
    local[end][:3,:3] = world[bones[end].parent_index][:3,:3].T @ end_rotation
    return float(max(0, requested-distance))


def deform_arm(local, bones, ids, suffix, aim, projection):
    """Aim and reach one arm as a rigid block rooted at `Shoulder{L,R}`.

    `aim` is a direction; `projection` is where the hand must land *along that direction,
    measured from the fighter's origin* (which is the ground contact point on this recipient,
    so it doubles as "how far forward of the body"). Rotation happens about the shoulder's
    own origin so the shoulder joint keeps its place, and the translation is a pure shift
    along `aim` applied in model axes rather than the (leaned) parent frame, so the achieved
    reach is exactly the requested one and does not compound with the torso lean.

    Anchoring the target to the origin rather than to each arm's own idle hand is what makes
    one shared recipe value put both hands in the same place: the left arm hangs further back
    at idle, so an idle-relative target would send it short by the difference.
    """
    si, hi = ids['Shoulder' + suffix], ids['Hand' + suffix]
    aim = np.asarray(aim, dtype=float)
    aim = aim / np.linalg.norm(aim)
    world = world_pose(local, bones)
    shoulder = world[si][:3, 3].copy()
    span = float(np.linalg.norm(world[hi][:3, 3] - shoulder))
    parent = bones[si].parent_index
    local[si][:3, :3] = world[parent][:3, :3].T @ (turn(world[hi][:3, 3] - shoulder, aim) @ world[si][:3, :3])
    world = world_pose(local, bones)
    slide = (projection - float(world[hi][:3, 3] @ aim)) * aim
    local[si][:3, 3] = local[si][:3, 3] + world[parent][:3, :3].T @ slide
    world = world_pose(local, bones)
    return {'arm_span': span,
            'slide': slide.tolist(),
            'slide_magnitude': float(np.linalg.norm(slide)),
            'hand': world[hi][:3, 3].tolist(),
            'shoulder': world[si][:3, 3].tolist(),
            # A rigid arm of this span could only ever reach this far from its own shoulder;
            # everything beyond it is what posing cannot deliver and the slide supplies.
            'ik_only_max_reach': span,
            'slide_beyond_ik_reach': float(max(0.0, np.linalg.norm(slide) - span))}


def capsule_distance(point, hit):
    """Distance from a model-space point to the down-tilt capsule surface (negative = inside)."""
    a = np.asarray(hit['start'], dtype=float)
    b = np.asarray(hit.get('end', hit['start']), dtype=float)
    axis = b - a
    t = 0.0 if not np.any(axis) else float(np.clip(np.dot(point - a, axis) / (axis @ axis), 0, 1))
    return float(np.linalg.norm(point - (a + t * axis)) - hit['radius'])


def retarget(model_dir, out_path, gw_slot='c06', idle_path=None, hit=None):
    """Author recipient motion; historical function name retained for build.py callers."""
    src = _pinned(CLIP)
    hit = hit or active_hitbox()
    model_path = Path(model_dir) / 'model.nusktb'
    skel = s.skel_data.read_skel(str(model_path))
    # In the full builder this idle has already been written beside the destination.
    idle_path = Path(idle_path) if idle_path else Path(out_path).parent / 'a00wait1.nuanmb'
    if not idle_path.is_file():
        raise RuntimeError(f'Need built recipient idle (no guessed pose/visibility): {idle_path}')
    idle = s.anim_data.read_anim(str(idle_path))
    idle_values = {n.name: n.tracks[0].values[0] for g in idle.groups
                   if g.group_type.name == 'Transform' for n in g.nodes}
    ids = {b.name: i for i, b in enumerate(skel.bones)}
    base = [matrix(idle_values[b.name]) if b.name in idle_values else np.asarray(b.transform, dtype=float).T.copy()
            for b in skel.bones]
    base_rotation = [decompose(m[:3, :3])[0] for m in base]
    base_scale = [decompose(m[:3, :3])[1] for m in base]
    base_scale_deviation = max(float(np.abs(s - 1).max()) for s in base_scale)
    idle_world = world_pose(base, skel.bones)
    recipe = json.loads(RECIPE.read_text())
    height = float(recipe['body_height_model_units'])
    donor = s.anim_data.read_anim(str(src))
    end = donor.final_frame_index
    if end != recipe['keys'][-1]['frame'] or recipe['cancel_frame'] != get_entry()['cancel']:
        raise RuntimeError('Recipe timing disagrees with pinned donor')
    values = {b.name: [] for b in skel.bones}
    samples, clamping, arms, scales_written = [], [], [], []
    peak = int(recipe['active_frame'])
    for frame in range(int(end)+1):
        lo, hi = next((a,b) for a,b in zip(recipe['keys'],recipe['keys'][1:]) if a['frame'] <= frame <= b['frame'])
        t = (frame-lo['frame'])/(hi['frame']-lo['frame'])
        t = t*t*(3-2*t)
        key = {n: np.asarray(lo[n])*(1-t)+np.asarray(hi[n])*t for n in lo if n != 'frame'}
        local = [m.copy() for m in base]
        local[ids['Hip']][:3,3] += idle_world[ids['Rot']][:3,:3].T @ key['hip']
        for name, degrees in [('Waist', key['lean_deg']*.7), ('Bust', key['lean_deg']*.3), ('Neck', key['neck_deg'])]:
            angle = math.radians(float(degrees))
            tilt = np.array([[1,0,0],[0,math.cos(angle),-math.sin(angle)],[0,math.sin(angle),math.cos(angle)]])
            world = world_pose(local, skel.bones)
            i = ids[name]
            parent = world[skel.bones[i].parent_index][:3,:3]
            local[i][:3,:3] = parent.T @ tilt @ parent @ local[i][:3,:3]
        reach = {}
        for suffix in ('L', 'R'):
            foot = idle_world[ids['Foot'+suffix]]
            reach['Foot'+suffix] = solve_limb(local, skel.bones, ids, ['Leg'+suffix,'Knee'+suffix,'Foot'+suffix],
                                             foot[:3,3], [0,0,1], foot[:3,:3])
        aim = np.asarray(key['arm_aim'], dtype=float)
        aim = aim / np.linalg.norm(aim)
        # Where along `aim`, measured from the fighter's origin, the hands should end up.
        arm_projection = float(key['arm_reach']) * height
        arm_measure = {}
        if float(key['arm_reach']) != 0.0 or abs(float(aim[2]) - 1.0) > 1e-9:
            for suffix in ('L', 'R'):
                arm_measure[suffix] = deform_arm(local, skel.bones, ids, suffix, aim, arm_projection)
        # Return exactly to the recipient idle at cancel; no snap from the IK's alternate solution.
        weight = float(key['weight'])
        scale_worst = 0.0
        for i, bone in enumerate(skel.bones):
            rotation_value, scale_value = decompose(local[i][:3,:3])
            q, initial = quaternion(rotation_value), quaternion(base_rotation[i])
            if np.dot(q, initial) < 0: q = -q
            q = initial*(1-weight)+q*weight
            q /= np.linalg.norm(q)
            pos = base[i][:3,3]*(1-weight)+local[i][:3,3]*weight
            scale = base_scale[i]*(1-weight)+scale_value*weight
            if not (np.all(np.isfinite(q)) and np.all(np.isfinite(pos)) and np.all(np.isfinite(scale))):
                raise RuntimeError(f'{bone.name} frame {frame}: non-finite transform')
            scale_worst = max(scale_worst, float(np.abs(scale - base_scale[i]).max()))
            value = s.anim_data.Transform(scale.tolist(), q.tolist(), pos.tolist())
            values[bone.name].append(value)
            local[i] = matrix(value)
        scales_written.append(scale_worst)
        world = world_pose(local, skel.bones)
        gap = {suffix: round(capsule_distance(world[ids['Hand'+suffix]][:3, 3], hit), 6) for suffix in ('L', 'R')}
        arms.append({'frame': frame,
                     'hand_extension_body_heights': {
                         suffix: round((world[ids['Hand'+suffix]][2, 3] - idle_world[ids['Hand'+suffix]][2, 3]) / height, 6)
                         for suffix in ('L', 'R')},
                     'hand_forward_of_origin_body_heights': {
                         suffix: round(float(world[ids['Hand'+suffix]][:3, 3][2]) / height, 6)
                         for suffix in ('L', 'R')},
                     'hand': {suffix: world[ids['Hand'+suffix]][:3, 3].tolist() for suffix in ('L', 'R')},
                     'shoulder': {suffix: world[ids['Shoulder'+suffix]][:3, 3].tolist() for suffix in ('L', 'R')},
                     'arm_span': {suffix: m['arm_span'] for suffix, m in arm_measure.items()},
                     'slide': {suffix: m['slide'] for suffix, m in arm_measure.items()},
                     'slide_beyond_ik_reach': {suffix: m['slide_beyond_ik_reach']
                                               for suffix, m in arm_measure.items()},
                     'hand_to_capsule_surface': gap,
                     'hand_inside_hitbox': {suffix: bool(gap[suffix] <= 0) for suffix in ('L', 'R')}})
        samples.append({'frame': frame, 'joints': {n: world[ids[n]][:3,3].tolist() for n in
                        ['Hip','Head','HandL','HandR','FootL','FootR','ShoulderL','ShoulderR']},
                        'arm': arm_measure})
        clamping.append({'frame': frame, 'unreachable_distance': reach})
    cancel = int(recipe['cancel_frame'])
    recovery = {}
    for check in (cancel, int(end)):
        world = world_pose([matrix(values[b.name][check]) for b in skel.bones], skel.bones)
        recovery[str(check)] = max(float(np.linalg.norm(world[i][:3, 3] - idle_world[i][:3, 3]))
                                   for i in range(len(skel.bones)))
    peak_row = arms[peak]
    transform = s.anim_data.GroupData(s.anim_data.GroupType.Transform, [s.anim_data.NodeData(
        b.name, [s.anim_data.TrackData('Transform', values=values[b.name])]) for b in skel.bones])
    gw_vis = next(g for g in idle.groups if g.group_type.name == 'Visibility')
    vis_nodes = [s.anim_data.NodeData(n.name, [s.anim_data.TrackData('Visibility', values=[n.tracks[0].values[0]])])
                 for n in gw_vis.nodes]
    anim = s.anim_data.AnimData()
    anim.final_frame_index = end
    anim.groups = [transform, s.anim_data.GroupData(s.anim_data.GroupType.Visibility, vis_nodes)]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    anim.save(str(out_path))
    return {'recipe_version':recipe['version'], 'recipe_sha256':sha(RECIPE), 'recipient_skeleton_sha256':sha(model_path),
            'recipient_idle_sha256':sha(idle_path), 'donor_sha256':sha(src), 'final_frame_index':end,
            'bones_kept':len(skel.bones), 'bones_dropped':[], 'case_only':[], 'vis_nodes':len(vis_nodes),
            'frames':int(end)+1, 'sha256':sha(out_path), 'pose_samples':samples, 'ik_reach':clamping,
            'body_height_model_units':height, 'base_bone_scale_deviation':base_scale_deviation,
            'scale_written_max_deviation':max(scales_written),
            'bone_scale_policy':'unit: arms are deformed rigidly, no bone is scaled',
            'arm_extension':arms,
            'frame3':{'frame':peak, 'hand':peak_row['hand'], 'shoulder':peak_row['shoulder'],
                      'hand_extension_body_heights':peak_row['hand_extension_body_heights'],
                      'hand_forward_of_origin_body_heights':peak_row['hand_forward_of_origin_body_heights'],
                      'hitbox':hit,
                      'hand_to_capsule_surface':peak_row['hand_to_capsule_surface'],
                      'hand_inside_hitbox':peak_row['hand_inside_hitbox'],
                      'arm_span':peak_row['arm_span'], 'slide':peak_row['slide'],
                      'slide_beyond_ik_reach':peak_row['slide_beyond_ik_reach']},
            'recovery_max_bone_displacement':recovery,
            'all_transforms_finite':True}


def deploy_for_slot(slot, out_dir, gw_slot, model_dir):
    """Write the custom recipient clip under the existing down-tilt carrier name."""
    report = retarget(model_dir, Path(out_dir) / CLIP, gw_slot)
    if report['case_only']:
        raise RuntimeError(f'nodes matched only case-insensitively: {report["case_only"]}')
    return {CLIP: report, 'motion_entry': {KIND: get_entry()['cancel']},
            'dropped': report['bones_dropped']}


def preview(package, out_path, hit=None, frames=(0, 1, 2, 3, 4, 6, 15)):
    """Render the whole deformed arm chain plus the donor hitbox, in one shared frame.

    Every panel uses the same z/y->pixel mapping and one shared auto-fit bound covering every
    bone and the whole capsule, so a stretched arm is never clipped away and the hitbox
    overlay is directly comparable with the skeleton. Authoring diagram only: it draws joints,
    not meshes, and says nothing about what the console renders.
    """
    from PIL import Image, ImageDraw
    hit = hit or active_hitbox()
    mod = package / 'ultimate/mods/pyra_gamewatch_reskin'
    skel = s.skel_data.read_skel(str(mod / 'fighter/eflame/model/body/c06/model.nusktb'))
    anim = s.anim_data.read_anim(str(mod / 'fighter/eflame/motion/body/c06' / CLIP))
    tracks = {n.name: n.tracks[0].values for g in anim.groups if g.group_type.name == 'Transform' for n in g.nodes}
    poses = {f: world_pose([matrix(tracks[b.name][f]) for b in skel.bones], skel.bones) for f in frames}
    capsule = np.asarray(hit.get('end', hit['start']), dtype=float)
    sphere_a, sphere_b = np.asarray(hit['start'], dtype=float), capsule
    bounds = [p[i][:3, 3] for p in poses.values() for i in range(len(skel.bones))]
    bounds += [sphere_a, sphere_b, sphere_a - hit['radius'], sphere_b + hit['radius']]
    zs = [p[2] for p in bounds] + [-hit['radius'], 0.0]
    ys = [p[1] for p in bounds] + [-hit['radius'], 0.0]
    z0, z1 = min(zs) - 2.0, max(zs) + 2.0
    y0, y1 = min(ys) - 2.0, max(ys) + 2.0
    panel_w, panel_h, top, margin = 420, 640, 66, 16
    scale = min((panel_w - 2 * margin) / (z1 - z0), (panel_h - 2 * margin) / (y1 - y0))
    img = Image.new('RGB', (panel_w * len(frames) + 20, panel_h + top + 40), '#f8f8fa')
    draw = ImageDraw.Draw(img)
    draw.text((14, 8), 'T-0048 robot down tilt: recipient joints and the donor hitbox capsule, one shared scale', fill='black')
    draw.text((14, 24), f'+Z forward (right), +Y up. Capsule parsed from robot_attacklw3.rs (sha {hit["source_sha256"][:12]}): '
                        f'r={hit["radius"]} {hit["start"]} -> {hit.get("end")}', fill='#444444')
    draw.text((14, 42), 'Joint authoring diagram only: no mesh, no engine, no console claim.', fill='#444444')
    arm_names = ('Shoulder', 'Arm', 'Hand', 'H_')
    for panel, f in enumerate(frames):
        x_off = panel * panel_w + 10

        def screen(v, x_off=x_off):
            return (x_off + margin + (v[2] - z0) * scale, top + panel_h - margin - (v[1] - y0) * scale)

        draw.rectangle((x_off, top, x_off + panel_w, top + panel_h), outline='#dddddd')
        pa, pb = screen(sphere_a), screen(sphere_b)
        if np.any(sphere_a - sphere_b):
            draw.polygon([(pa[0], pa[1]), (pb[0], pb[1]),
                          (pb[0], pb[1] + 2 * hit['radius'] * scale),
                          (pa[0], pa[1] + 2 * hit['radius'] * scale)], fill='#7fb3ff88', outline='#2b6cb0')
        for p in (pa, pb):
            r = hit['radius'] * scale
            draw.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill='#7fb3ff88', outline='#2b6cb0')
        gy = screen((0.0, 0.0, 0.0))[1]
        draw.line([(x_off + 4, gy), (x_off + panel_w - 4, gy)], fill='#999999')
        world = poses[f]
        drawn = set()
        for i, bone in enumerate(skel.bones):
            if bone.parent_index is None or bone.parent_index in drawn:
                continue
            start, end = screen(world[bone.parent_index][:3, 3]), screen(world[i][:3, 3])
            arm = bone.name.endswith(('R', 'L')) and any(k in bone.name for k in arm_names)
            color = '#2463aa' if bone.name.endswith('R') else '#d25936' if bone.name.endswith('L') else '#9a9a9a'
            draw.line([start, end], fill=color, width=6 if arm else 2)
            if arm:
                draw.ellipse((end[0]-4, end[1]-4, end[0]+4, end[1]+4), fill=color)
            drawn.add(i)
        draw.text((x_off + 10, top + 8), f'frame {f}' + ('   <- hitbox active' if f == 3 else ''), fill='black')
        draw.text((x_off + 10, top + panel_h - 16), 'ground y = 0', fill='#777777')
        draw.text((x_off + 10, top + panel_h + 4), 'blue right arm / orange left arm / grey rest', fill='#555555')
        draw.text((x_off + 10, top + panel_h + 20), f'shared bounds z {z0:.0f}..{z1:.0f}  y {y0:.0f}..{y1:.0f}', fill='#777777')
    img.save(str(out_path))


if __name__ == '__main__':
    import shutil
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--stage-only', action='store_true', required=True)
    parser.add_argument('--preview', action='store_true', help='render authoring PNG, not a game test')
    parser.add_argument('--task-id', default=os.environ.get('PGWR_BUILD_TASK', 'T-0048'),
                        help='identity used for the shared-build reservation, report and manifest')
    args = parser.parse_args()
    task = args.task_id
    baseline, package = args.baseline.resolve(), args.package.resolve()
    if not baseline.is_relative_to(ROOT / 'builds/pgwr') or not package.is_relative_to(ROOT / 'builds/pgwr'):
        parser.error('baseline and package must stay under builds/pgwr')
    if package.exists():
        parser.error('package already exists; choose a fresh versioned variant')
    # Shared-build coordination: take the reservation only when it is free. An active
    # reservation owned by another task is never taken over.
    owner = None
    if LOCK.is_file():
        try:
            owner = json.loads(LOCK.read_text()).get('owner')
        except (ValueError, OSError):
            owner = 'unreadable'
        if owner != task:
            parser.error(f'shared build is reserved by {owner}; refusing to steal an active reservation')
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    LOCK.write_text(json.dumps({'owner': task, 'pid': os.getpid(), 'tool': 'build_robot_dtilt.py',
                                'acquired': datetime.datetime.now(datetime.timezone.utc).isoformat(
                                    timespec='seconds')}) + '\n')
    try:
        mod_rel = Path('ultimate/mods/pyra_gamewatch_reskin')
        manifest = json.loads((baseline / 'MANIFEST.json').read_text())
        nro_rel = Path('atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpyra_gamewatch_reskin.nro')
        if not (baseline / nro_rel).is_file():
            parser.error('baseline NRO missing; cannot stage a complete animation-only variant')
        hit = active_hitbox()

        # Measure the actual local baseline rather than assuming old manifests are current.
        def inventory(path):
            return {p.relative_to(path).as_posix(): sha(p) for p in sorted(path.rglob('*')) if p.is_file()}
        before = inventory(baseline / mod_rel)
        for slot in ('c06', 'c07'):
            for rel in (f'fighter/eflame/model/body/{slot}/model.nusktb',
                        f'fighter/eflame/motion/body/{slot}/a00wait1.nuanmb'):
                if not (baseline / mod_rel / rel).is_file():
                    parser.error(f'missing actual recipient input: {rel}')
            mlist = baseline / mod_rel / f'fighter/eflame/motion/body/{slot}/motion_list.bin'
            if get_entry()['raw'] not in mlist.read_bytes():
                parser.error(f'{slot}: pinned complete donor down-tilt entry absent; preserve routing before staging')
        shutil.copytree(baseline, package)
        reports = {}
        for slot in ('c06', 'c07'):
            model = package / mod_rel / f'fighter/eflame/model/body/{slot}'
            motion = package / mod_rel / f'fighter/eflame/motion/body/{slot}'
            reports[slot] = retarget(model, motion / CLIP, slot, hit=hit)
        after = inventory(package / mod_rel)
        changed = [n for n in after if before.get(n) != after[n]]
        expected = [f'fighter/eflame/motion/body/{slot}/{CLIP}' for slot in ('c06', 'c07')]
        if sorted(changed) != sorted(expected) or before.keys() != after.keys():
            raise RuntimeError('Unexpected baseline delta; staged package must not be used')
        nros = {p.name: sha(p) for p in sorted((package / nro_rel).parent.glob('*.nro'))}
        for name, digest in nros.items():
            if sha(baseline / nro_rel.parent / name) != digest:
                raise RuntimeError(f'{name} differs from the baseline; an animation-only variant must reuse both NROs')
        evidence = {'task': task, 'package_id': package.name,
                    'baseline': baseline.relative_to(ROOT).as_posix(),
                    'core_version': manifest['version'],
                    'animation_version': reports['c06']['recipe_version'],
                    'stage_only': True,
                    'nro_reused_unchanged': nros,
                    'changed_mod_files': changed,
                    'mod_file_count': len(after), 'reports': reports,
                    'game_behavior': 'unverified; needs console review',
                    'rust_compilation': 'not needed: animation-only; baseline plugin unchanged',
                    'hitbox_source': {'path': ACMD.relative_to(ROOT).as_posix(), 'sha256': sha(ACMD),
                                      'capsule': hit},
                    'body_height_model_units': reports['c06']['body_height_model_units'],
                    'reserved_cargo_target': f'builds/.cache/pgwr-{task}-target'}
        (package / 'robot_dtilt_custom.json').write_text(json.dumps(evidence, indent=2) + '\n')
        # Retain donor/sound/baseline records, replace only the active release inventory.
        tree_hash = hashlib.sha256(''.join(f'{v}  ./{n}\n' for n, v in after.items()).encode()).hexdigest()
        manifest.update({'package_id': package.name, 'task': task, 'mod_file_hashes': after,
                         'animation_variant': 'robot_dtilt_custom.json', 'hardware_validated': False,
                         'scope': f'{task} stretched-arm animation variant; inherited core '
                                  f"{manifest['version']} and all unrelated assets",
                         'inherited_reports_note': 'Copied reports describe baseline generation; robot_dtilt_custom.json supersedes their down-tilt clip fields',
                         'source_git_commit_note': f'{task} branch commit records animation changes; git field identifies reused baseline core'})
        manifest['artifacts']['mod_tree'].update({'path': (package/mod_rel).relative_to(ROOT).as_posix(),
                                                  'files': len(after), 'tree_sha256': tree_hash})
        manifest['artifacts']['reskin_nro']['path'] = (package/nro_rel).relative_to(ROOT).as_posix()
        manifest['source_hashes']['src/pgwr/tools/build_robot_dtilt.py'] = sha(Path(__file__))
        manifest['source_hashes']['src/pgwr/build.py'] = sha(ROOT / 'src/pgwr/build.py')
        manifest['source_hashes'][RECIPE.relative_to(ROOT).as_posix()] = sha(RECIPE)
        (package / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
        if args.preview:
            preview(package, package / 'robot_dtilt_pose_preview.png', hit=hit)
        print(json.dumps({k: v for k, v in evidence.items() if k != 'reports'}, indent=2))
    finally:
        if LOCK.is_file() and json.loads(LOCK.read_text()).get('owner') == task:
            LOCK.unlink()