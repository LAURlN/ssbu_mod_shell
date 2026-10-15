#!/usr/bin/env python3
"""Build the game assets of move unit MV-aerial_up__kamui (Corrin's up air on Mii Gunner).

Retarget by bone-name intersection, the same construction as the reference repo's air-clip ports
(src/pgwr/tools/build_pikachu_airb.py, handbook/04 section "Retargeting a donor air clip"):

* The Transform node set is the Mii Gunner's own idle node set. Pose nodes that exist on both
  rigs take the donor's rotation; translation is rebuilt as recipient idle + (donor frame - donor
  idle). Every other node is held at the recipient's idle value.
* Donor-only nodes (wing, mantle, shirttail, spear, face, mouth, tongue, lip and leg/clavicle nodes the Gunner does not
  have) are dropped. The list is written to tables/retarget_report.json, not filtered silently.
* The Visibility group comes from the Gunner's own idle clip. The donor's Visibility group (Corrin
  face, hair, wing and Omega Yato `Kamui_Weapon` meshes) is not carried. The Material group is dropped.
* A vertical ground-contact correction is applied to Rot, as in the precedent.
* Gates (refuse to write on failure): parent chains by name, limbs must move, Transform node set.

The motion entry is Corrin's own `attack_air_hi` entry copied whole, with the kind, game/expression/
sound/effect script hashes and the animation hash replaced by owned names. Flags and the cancel
field are copied unchanged.

Run from the workspace root:
    python -I mods/mii_customizer/moves/aerial_up__kamui/build_assets.py

Writes (workspace-relative) under gamedata/mii_customizer/moves/aerial_up__kamui/:
    package/fighter/miigunner/motion/body/c00/c01mckamuiattackairhi.nuanmb
    reference/motion_list_vanilla_plus_owned.bin   (vanilla Gunner list + the one added entry)
    tables/retarget_report.json
    manifest.json
No motion_list.bin, motion_list.motdiff or config.json is written into package/ (the coordinator
merges all units; see evidence/2026-10-07_session4/RESULT_boot2.md).
"""
from __future__ import annotations

import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

import numpy as np

WORKSPACE = Path(__file__).resolve().parents[4]
UNIT_DIR = Path(__file__).resolve().parent
UNIT = 'aerial_up__kamui'
GUNNER_TOOLS = WORKSPACE / 'mods/ssbu_mod_new/src/pgwr/tools'  # read-only: pose helper
sys.path.insert(0, str(GUNNER_TOOLS))
import ssbh_data_py as s  # noqa: E402
import pose_fk as fk  # noqa: E402

G = WORKSPACE / 'gamedata/mii_customizer'
OUT = G / 'moves' / UNIT
DONOR = OUT / 'donor'
RECIPIENT = OUT / 'recipient'

DONOR_CLIP = DONOR / 'fighter/kamui/motion/body/c00/c05attackairhi.nuanmb'
DONOR_IDLE = DONOR / 'fighter/kamui/motion/body/c00/a00wait1.nuanmb'
DONOR_SKEL = DONOR / 'fighter/kamui/model/body/c00/model.nusktb'
DONOR_MLIST = DONOR / 'fighter/kamui/motion/body/c00/motion_list.bin'
RECIPIENT_IDLE = RECIPIENT / 'fighter/miigunner/motion/body/c00/a00wait1.nuanmb'
RECIPIENT_SKEL = G / 'P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb'
VANILLA_MLIST = G / 'P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin'

DONOR_KIND = 'attack_air_hi'
OWNED_KIND = 'mc_kamui_attack_air_hi'
OWNED_CLIP = 'c01mckamuiattackairhi.nuanmb'
SUFFIX = 'mckamuiattackairhi'
OWNED_SCRIPTS = {
    'game': f'game_{SUFFIX}',
    'expression': f'expression_{SUFFIX}',
    'sound': f'sound_{SUFFIX}',
    'effect': f'effect_{SUFFIX}',
}

PACKAGE_BODY = OUT / 'package/fighter/miigunner/motion/body/c00'
REFERENCE = OUT / 'reference/motion_list_vanilla_plus_owned.bin'
DONOR_LAND_CLIP = DONOR / 'fighter/kamui/motion/body/c00/c05landingairhi.nuanmb'
LAND_KIND = 'mc_kamui_landing_air_hi'
LAND_CLIP = 'c01mckamuilandingairhi.nuanmb'
LAND_SUFFIX = 'mckamuilandingairhi'
# Corrin's landing_attack_air_frame_hi (fighter_param.prc, fighter_kind_kamui); the Gunner's is 13.
LANDING_FRAME_HI = 9.0
TABLES = OUT / 'tables'
MANIFEST = OUT / 'manifest.json'

# Limbs that must move in the retargeted clip (the leg/foot chain the precedent gates on).
LIMB_BONES = ('Hip', 'LegL', 'LegR', 'KneeL', 'KneeR', 'FootL', 'FootR', 'ToeL', 'ToeR')
ROT_EPS_DEG = 0.5
TRANS_EPS = 1e-3


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Motion list (same layout as tools/move-package/build_p16_assets.py)
# ---------------------------------------------------------------------------

def parse_mlist(data: bytes):
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    offset = 24
    entries = []
    for i in range(count):
        start = offset
        kind, game, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        raw = data[start:end]
        offset = end
        entries.append({'index': i, 'kind': kind, 'game': game, 'flags': flags, 'blend': blend,
                        'n_anims': n_anims, 'anims': anims, 'size': size, 'raw': raw,
                        'tail_offset': tail - start})
    if offset != len(data):
        raise RuntimeError(f'motion list: {len(data) - offset} trailing bytes after {count} entries')
    return magic, motion_path, entries


def donor_entry(entries) -> dict:
    hit = [e for e in entries if e['kind'] == hash40(DONOR_KIND)]
    if len(hit) != 1:
        raise RuntimeError(f'donor list has {len(hit)} {DONOR_KIND} entries')
    e = hit[0]
    if e['anims'] != (hash40('c05attackairhi.nuanmb'),):
        raise RuntimeError('donor attack_air_hi does not name c05attackairhi.nuanmb')
    if e['game'] != hash40('game_attackairhi'):
        raise RuntimeError('donor attack_air_hi game script is not game_attackairhi')
    return e


def owned_entry(donor: dict) -> bytes:
    raw = bytearray(donor['raw'])
    struct.pack_into('<QQ', raw, 0, hash40(OWNED_KIND), hash40(OWNED_SCRIPTS['game']))
    struct.pack_into('<Q', raw, 24, hash40(OWNED_CLIP))
    t = donor['tail_offset']
    struct.pack_into('<QQQ', raw, t, hash40(OWNED_SCRIPTS['expression']),
                     hash40(OWNED_SCRIPTS['sound']), hash40(OWNED_SCRIPTS['effect']))
    return bytes(raw)


# ---------------------------------------------------------------------------
# Retarget
# ---------------------------------------------------------------------------

def rot_angle_deg(a, b) -> float:
    qa = np.array(a, dtype=float)
    qb = np.array(b, dtype=float)
    d = abs(float(np.dot(qa, qb)))
    d = min(1.0, d)
    return float(np.degrees(2.0 * np.arccos(d)))


def retarget(donor_clip: Path = None, owned_clip: str = None) -> dict:
    donor_clip = donor_clip or DONOR_CLIP
    owned_clip = owned_clip or OWNED_CLIP
    d_anim, d_clip = fk.read_transform_tracks(donor_clip)
    _, d_idle = fk.read_transform_tracks(DONOR_IDLE)
    r_anim, r_idle = fk.read_transform_tracks(RECIPIENT_IDLE)
    r_idle_anim = s.anim_data.read_anim(str(RECIPIENT_IDLE))
    r_vis = next(g for g in r_idle_anim.groups if g.group_type.name == 'Visibility')

    skel_d = fk.Skeleton(DONOR_SKEL)
    skel_r = fk.Skeleton(RECIPIENT_SKEL)

    n = fk.frame_count(d_clip)
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
    if static or missing_limbs:
        raise RuntimeError(f'limbs static or missing after retarget: static={static} missing={missing_limbs}')

    # ---- write the clip ----
    transform_nodes = [s.anim_data.NodeData(name, [s.anim_data.TrackData(
        'Transform', values=collapsed(out[name]))]) for name in r_native]
    vis_nodes = [s.anim_data.NodeData(node.name, [s.anim_data.TrackData(
        'Visibility', values=[node.tracks[0].values[0]])]) for node in r_vis.nodes]
    d_anim.groups = [s.anim_data.GroupData(s.anim_data.GroupType.Transform, transform_nodes),
                     s.anim_data.GroupData(s.anim_data.GroupType.Visibility, vis_nodes)]
    PACKAGE_BODY.mkdir(parents=True, exist_ok=True)
    clip_out = PACKAGE_BODY / owned_clip
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
        'donor_visibility_nodes': sum(1 for g in d_anim.groups if g.group_type.name == 'Visibility'),
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

TRAIL_SRC = DONOR / 'effect/fighter/kamui/trail'
TRAIL_DST = OUT / 'package/effect/fighter/miigunner/trail'
# donor texture -> owned name (the footer name is rewritten to the owned name, as the Cloud units do)
TRAILS = {'tex_kamui_sword1': 'tex_mc_kamui_sword1', 'tex_kamui_sword2': 'tex_mc_kamui_sword2'}


def copy_trail_textures() -> dict:
    """Corrin's two sword-trail textures under the Gunner's trail folder; only the 64-byte footer name differs.

    The engine requests a trail by the hash of its NUTEXB footer name (reference repo handbook/10). The Cloud units
    rewrite the footer the same way (mccloud_build.py::build_trails). Placement in the Gunner's loader is unverified.
    """
    TRAIL_DST.mkdir(parents=True, exist_ok=True)
    report = {}
    for donor, owned in TRAILS.items():
        d = bytearray((TRAIL_SRC / f'{donor}.nutexb').read_bytes())
        if d[-0x70:-0x6c] != b' XNT' or d[-8:-4] != b' XET':
            raise RuntimeError(f'{donor}: unexpected NUTEXB footer')
        name = bytes(d[-0x6c:-0x2c]).rstrip(b'\0').decode()
        if name != donor.upper():
            raise RuntimeError(f'{donor}: footer name is {name}')
        new = owned.upper().encode()
        d[-0x6c:-0x2c] = new + b'\0' * (0x40 - len(new))
        (TRAIL_DST / f'{owned}.nutexb').write_bytes(bytes(d))
        report[owned] = {'donor': donor, 'footer_name': owned.upper(), 'request_hash': f'0x{hash40(owned):010x}',
                         'bytes_changed': 'footer name field only', 'sha256': sha256(TRAIL_DST / f'{owned}.nutexb')}
    return report


def owned_entry_for(donor: dict, kind: str, clip: str, suffix: str) -> bytes:
    raw = bytearray(donor['raw'])
    struct.pack_into('<QQ', raw, 0, hash40(kind), hash40(f'game_{suffix}'))
    struct.pack_into('<Q', raw, 24, hash40(clip))
    struct.pack_into('<QQQ', raw, donor['tail_offset'], hash40(f'expression_{suffix}'),
                     hash40(f'sound_{suffix}'), hash40(f'effect_{suffix}'))
    return bytes(raw)


def find_donor(entries, kind_name: str, clip_name: str) -> dict:
    hit = [e for e in entries if e['kind'] == hash40(kind_name)]
    if len(hit) != 1:
        raise RuntimeError(f'donor list has {len(hit)} {kind_name} entries')
    e = hit[0]
    if e['anims'] != (hash40(clip_name),):
        raise RuntimeError(f'donor {kind_name} does not name {clip_name}')
    return e


def package_config() -> dict:
    """ARCropolis new-dir-files lines: every package file, grouped by its folder (declared by the coordinator)."""
    dirs: dict = {}
    for p in sorted((OUT / 'package').rglob('*')):
        if p.is_file():
            rel_ = p.relative_to(OUT / 'package').as_posix()
            folder, name = rel_.rsplit('/', 1)
            dirs.setdefault(folder, []).append(rel_)
    return dirs


def main():
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import mckamui_sword
    import mckamui_sounds

    report = retarget()
    report['landing'] = retarget(DONOR_LAND_CLIP, LAND_CLIP)
    report['trail_textures'] = copy_trail_textures()
    report['sword'] = mckamui_sword.build_sword(OUT / 'package')
    report['sound_merge'] = mckamui_sounds.merge(OUT / 'recipient/sound/bank/fighter', OUT / 'reference/sound/bank/fighter')

    vanilla = VANILLA_MLIST.read_bytes()
    magic_v, path_v, entries_v = parse_mlist(vanilla)
    if any(e['kind'] in (hash40(OWNED_KIND), hash40(LAND_KIND)) for e in entries_v):
        raise RuntimeError('vanilla Gunner list already has an owned kind')
    _, _, entries_d = parse_mlist(DONOR_MLIST.read_bytes())
    attack_d = find_donor(entries_d, 'attack_air_hi', 'c05attackairhi.nuanmb')
    landing_d = find_donor(entries_d, 'landing_air_hi', 'c05landingairhi.nuanmb')
    raws = [owned_entry_for(attack_d, OWNED_KIND, OWNED_CLIP, SUFFIX),
            owned_entry_for(landing_d, LAND_KIND, LAND_CLIP, LAND_SUFFIX)]
    rebuilt = struct.pack('<QQQ', magic_v, path_v, len(entries_v) + len(raws)) + b''.join(
        e['raw'] for e in entries_v) + b''.join(raws)
    REFERENCE.parent.mkdir(parents=True, exist_ok=True)
    REFERENCE.write_bytes(rebuilt)

    magic_r, _, entries_r = parse_mlist(rebuilt)
    if len(entries_r) != len(entries_v) + 2:
        raise RuntimeError('reference list entry count is wrong')
    motion = {}
    for kind_name, donor_e, owned_e, clip, owned_kind in (
            ('attack_air_hi', attack_d, entries_r[-2], OWNED_CLIP, OWNED_KIND),
            ('landing_air_hi', landing_d, entries_r[-1], LAND_CLIP, LAND_KIND)):
        if owned_e['flags'] != donor_e['flags'] or owned_e['blend'] != donor_e['blend']:
            raise RuntimeError(f'{owned_kind}: flags/blend differ from the donor entry')
        own_cancel = struct.unpack_from('<H', owned_e['raw'], owned_e['tail_offset'] + 26)[0]
        donor_cancel = struct.unpack_from('<H', donor_e['raw'], donor_e['tail_offset'] + 26)[0]
        if own_cancel != donor_cancel:
            raise RuntimeError(f'{owned_kind}: cancel field {own_cancel} differs from donor {donor_cancel}')
        motion[owned_kind] = {
            'donor_kind': kind_name, 'owned_kind_hash': f'0x{hash40(owned_kind):010x}',
            'owned_clip': clip, 'owned_clip_hash': f'0x{hash40(clip):010x}',
            'flags': f'0x{owned_e["flags"]:04x}', 'blend': owned_e['blend'],
            'cancel_field': own_cancel, 'donor_cancel_field': donor_cancel,
        }
    report['motion_entries'] = motion
    report['landing_frame_hi'] = {'corrin': LANDING_FRAME_HI, 'gunner': 13.0,
                                  'source': 'fighter_param.prc landing_attack_air_frame_hi'}
    report['reference_list'] = {'path': str(REFERENCE.relative_to(WORKSPACE)).replace('\\', '/'),
                                'sha256': sha256(REFERENCE), 'entries': len(entries_r),
                                'vanilla_entries': len(entries_v)}

    TABLES.mkdir(parents=True, exist_ok=True)
    (TABLES / 'retarget_report.json').write_text(json.dumps(report, indent=2, default=str) + '\n', encoding='utf-8')

    files = {}
    for p in sorted(OUT.joinpath('package').rglob('*')):
        if p.is_file():
            files[p.relative_to(OUT).as_posix()] = {'size': p.stat().st_size, 'sha256': sha256(p)}
    sound_out = OUT / 'reference/sound/bank/fighter'
    ref_files = {REFERENCE.relative_to(OUT).as_posix(): {'size': REFERENCE.stat().st_size, 'sha256': sha256(REFERENCE)}}
    for p in sorted(sound_out.iterdir()):
        ref_files[p.relative_to(OUT).as_posix()] = {'size': p.stat().st_size, 'sha256': sha256(p)}
    manifest = {
        'unit': UNIT,
        'package_name': 'mii_customizer_move_aerial_up__kamui',
        'files': files,
        'reference': ref_files,
        'config_needed_by_coordinator': {'new-dir-files': package_config()},
        'added_motion': [
            {'kind': OWNED_KIND, 'clip': OWNED_CLIP, 'scripts': OWNED_SCRIPTS},
            {'kind': LAND_KIND, 'clip': LAND_CLIP, 'scripts': {c: f'{c}_{LAND_SUFFIX}' for c in OWNED_SCRIPTS}},
        ],
        'merge_rules': {
            'motion_list': 'reference/motion_list_vanilla_plus_owned.bin is vanilla + 2 entries; merge, never ship whole',
            'se_miigunner': 'reference/sound/bank/fighter/se_miigunner.* is vanilla + 1 tone (mckamui_sounds.py); merge',
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')

    print(f"clip: {report['clip_out']} frames={report['frames']} transform_nodes={report['recipient_native_transform_nodes']} "
          f"pose={len(report['pose_nodes'])} dropped_donor_nodes={len(report['dropped_donor_nodes'])}")
    print(f"landing clip: {report['landing']['clip_out']} pose={len(report['landing']['pose_nodes'])}")
    print(f"reference: {len(entries_r)} entries (vanilla {len(entries_v)} + 2)")
    print(f"sword: {report['sword']['article']} objects={len(report['sword']['objects'])} "
          f"materials={report['sword']['materials']}")
    print(f"sound: {report['sound_merge']['retained_tones']} -> {report['sound_merge']['total_tones']} tones")
    print(f"manifest: {MANIFEST.relative_to(WORKSPACE)}")


if __name__ == '__main__':
    main()
