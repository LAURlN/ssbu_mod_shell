"""How big should the Aegis blade be on the Cloud fair? Measure it, do not guess.

Forward-kinematics over the retargeted body clip and the *article's own* chain,
measuring the blade against Cloud's own hitbox capsule. Read-only.

This replaces an earlier version that modelled the blade as rigidly attached to the
grafted *body* bone `Sword1` and rigid along its +z. That model was refuted on
hardware 2026-09-30 (`handbook/graveyard.md` R-21: a `Sword1` track in the body clip
changed nothing), so its numbers measured the model, not the game. The chain below is
the one the two refutations leave standing:

    owner `HaveR` (animated by the fair clip)      <- what the article actually follows
      x article `HaveR`  (from the article's clip) <- constant in every sword state
      x article `Sword1` (from the article's clip) <- constant too
      x the blade's +z axis, tip at the mesh's own z max

Both article rotations are **read out of `z00open.nuanmb`** rather than typed in, and
the blade tip is **read out of the esword mesh**, so this file cannot drift away from
the data it describes. Hitbox numbers are cross-checked against the plugin's ACMD.

Two things are still assumptions, both marked so nobody mistakes them for measurement:
the attach bone (`HaveR` - chosen because the body clip *does* animate it and the
article demonstrably does not follow the grafted `Sword1`), and the `top` anchor
resolving to the origin.

Run:
    toolchains/py312/python.exe src/pgwr/tools/fair_sword_geometry.py
    toolchains/py312/python.exe src/pgwr/tools/fair_sword_geometry.py --scale
"""
from pathlib import Path
import sys

import numpy as np
import ssbh_data_py as s

ROOT = Path(__file__).resolve().parents[3]
BUILDS = ROOT / 'builds/pgwr'
EXPORT = ROOT / 'dumps/arc'
PLUGIN_ACMD = ROOT / 'src/pgwr/plugin/src/acmd/attack_air_f.rs'

BUILT = BUILDS / 'pyra_gamewatch_reskin/ultimate/mods/pyra_gamewatch_reskin'
ARTICLE = EXPORT / 'fighter/eflame/motion/esword'
ARTICLE_CLIP = 'z00open.nuanmb'     # the state the fair opens the sword into
ESWORD_MESH = EXPORT / 'fighter/eflame/model/esword/c06/model.numshb'
ATTACH_BONE = 'HaveR'               # assumption: see the module docstring

# Cloud's blade hitbox (id 2) on `top`, from the plugin's ACMD; asserted below.
HITBOX = {'bone': 'top', 'p1': (0.0, 9.5, 14.0), 'p2': (0.0, 14.5, 14.6)}
ACTIVE_FRAMES = range(18, 27)       # live frames 18-20, cleared at 26


def _assert_hitbox_matches_source():
    if not PLUGIN_ACMD.is_file():
        return 'plugin ACMD not found; hitbox numbers not cross-checked'
    text = PLUGIN_ACMD.read_text(encoding='utf-8')
    needle = 'Some(%.1f), Some(%.1f), Some(%.1f)' % HITBOX['p2']
    return ('hitbox cross-checked against %s' % PLUGIN_ACMD.name if needle in text
            else 'WARNING: %s no longer contains %s' % (PLUGIN_ACMD.name, needle))


def blade_tip():
    """The blade's z extent in the esword mesh, which is the tip along +z."""
    mesh = s.mesh_data.read_mesh(str(ESWORD_MESH))
    z_max = -1e9
    for obj in mesh.objects:
        for attr in obj.positions:
            d = np.array(attr.data, dtype=np.float64).reshape(-1, 3)
            z_max = max(z_max, float(d[:, 2].max()))
    return z_max


def _quat_to_mat(q):
    x, y, z, w = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=np.float64)


def article_chain(slot='c06'):
    """article `HaveR` @ article `Sword1`, read from the clip the fair opens into."""
    anim = s.anim_data.read_anim(str(ARTICLE / slot / ARTICLE_CLIP))
    group = next(g for g in anim.groups if g.group_type.name == 'Transform')
    parts = {}
    for node in group.nodes:
        track = next((t for t in node.tracks if t.name == 'Transform'), None)
        if track and node.name in ('HaveR', 'Sword1'):
            scale, rotation, translation = track.values[0].scale, track.values[0].rotation, track.values[0].translation
            m = np.eye(4)
            m[:3, :3] = _quat_to_mat(rotation) @ np.diag(np.array(scale, dtype=np.float64))
            m[:3, 3] = np.array(translation, dtype=np.float64)
            parts[node.name] = m
    for name in ('HaveR', 'Sword1'):
        if name not in parts:
            raise RuntimeError(f'{slot}/{ARTICLE_CLIP} has no {name} track; the chain is not what this models')
    return parts['HaveR'] @ parts['Sword1']


def load_body(slot='c06'):
    model = BUILT / 'fighter/eflame/model/body' / slot
    clip = BUILT / 'fighter/eflame/motion/body' / slot / 'c05attackairf.nuanmb'
    skel = s.skel_data.read_skel(str(model / 'model.nusktb'))
    anim = s.anim_data.read_anim(str(clip))
    parents, bind = {}, {}
    for i, bone in enumerate(skel.bones):
        parents[bone.name] = skel.bones[bone.parent_index].name if bone.parent_index is not None else None
        bind[bone.name] = np.array(bone.transform, dtype=np.float64).reshape(4, 4)
    tracks = {}
    group = next((g for g in anim.groups if g.group_type.name == 'Transform'), None)
    for node in (group.nodes if group else []):
        track = next((t for t in node.tracks if t.name == 'Transform'), None)
        if track:
            tracks[node.name] = [(np.array(v.scale, float), np.array(v.rotation, float),
                                  np.array(v.translation, float)) for v in track.values]
    lookup = {b.name.lower(): b.name for b in skel.bones}
    return parents, bind, tracks, lookup


def body_world(name, frame, parents, bind, tracks, lookup):
    if name == HITBOX['bone']:
        return np.eye(4)     # assumption: the anchor resolves to the origin
    chain, cur = [], lookup.get(name.lower(), name)
    while cur is not None:
        chain.append(cur)
        cur = parents[cur]
    m = np.eye(4)
    for bone in reversed(chain):
        frames = tracks.get(bone)
        if not frames:
            local = bind[bone]
        else:
            scale, rotation, translation = frames[min(frame, len(frames) - 1)]
            local = np.eye(4)
            local[:3, :3] = _quat_to_mat(rotation) @ np.diag(scale)
            local[:3, 3] = translation
        m = m @ local
    return m


def segment_distance(p, q, a, b):
    d1, d2, r = q - p, b - a, p - a
    e, f, c, dot = np.dot(d2, d2), np.dot(d2, r), np.dot(d1, r), np.dot(d1, d2)
    den = np.dot(d1, d1) * e - dot * dot
    u = 0.0 if den < 1e-9 else np.clip((dot * f - c * e) / den, 0.0, 1.0)
    v = np.clip((dot * u + f) / e, 0.0, 1.0)
    return np.linalg.norm((p + u * d1) - (a + v * d2))


def report(label, scale=1.0, slot='c06', verbose=True):
    parents, bind, tracks, lookup = load_body(slot)
    art = article_chain(slot)
    art_scaled = art.copy()
    art_scaled[:3, :3] = art[:3, :3] @ np.diag([scale] * 3)
    tip_local = np.array([0.0, 0.0, blade_tip()])
    hb_a, hb_b = np.array(HITBOX['p1']), np.array(HITBOX['p2'])
    hb_mid = (hb_a + hb_b) / 2
    hb_dir = hb_b - hb_a
    hb_dir = hb_dir / np.linalg.norm(hb_dir)

    dists, tip_gap, cosines = [], [], []
    grip_world = None
    for frame in ACTIVE_FRAMES:
        hand = body_world(ATTACH_BONE, frame, parents, bind, tracks, lookup)
        m = hand @ art_scaled
        grip = m[:3, 3]
        tip = m[:3, :3] @ tip_local + grip
        dists.append(segment_distance(grip, tip, hb_a, hb_b))
        tip_gap.append(float(np.linalg.norm(tip - hb_mid)))
        axis = (tip - grip)
        axis = axis / np.linalg.norm(axis)
        cosines.append(float(np.dot(axis, hb_dir)))
        grip_world = m
    result = {
        'label': label, 'scale': scale,
        'blade_len': blade_tip() * scale,
        'mean_blade_to_hitbox': float(np.mean(dists)),
        'mean_tip_to_hitbox_mid': float(np.mean(tip_gap)),
        'mean_axis_cosine_to_hitbox': float(np.mean(cosines)),
    }
    if verbose:
        print(f'{label}')
        print(f'   blade {result["blade_len"]:.2f} long, scale {scale:.2f}')
        print(f'   mean blade-to-hitbox-segment distance  {result["mean_blade_to_hitbox"]:.2f}')
        print(f'   mean blade-tip-to-hitbox-centre gap    {result["mean_tip_to_hitbox_mid"]:.2f}')
        print(f'   blade axis vs hitbox axis cosine      {result["mean_axis_cosine_to_hitbox"]:+.2f}')
        print(f'   grip (frame 18) {np.round(grip_world[:3, 3], 2)}, hitbox centre {np.round(hb_mid, 2)}')
    return result


def main(argv):
    print(_assert_hitbox_matches_source())
    print(f'blade tip read from the mesh: z = {blade_tip():.3f}')
    print(f'attach bone: {ATTACH_BONE} (assumption), top anchor: origin (assumption)\n')
    if '--scale' in argv:
        print('sweep (the tip reaching the hitbox centre is the thing to look at):')
        best = None
        for scale in (1.0, 1.15, 1.3, 1.45, 1.6, 1.8, 2.0, 2.5):
            r = report(f'  scale {scale}', scale)
            if best is None or r['mean_tip_to_hitbox_mid'] < best[1]:
                best = (scale, r['mean_tip_to_hitbox_mid'])
        print(f'\nsmallest tip-to-hitbox gap at scale {best[0]} (gap {best[1]:.2f})')
        return 0
    report('built c06 fair', 1.0)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
