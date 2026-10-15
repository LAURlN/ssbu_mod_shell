"""Retarget Snake's up tilt (AttackHi3) for Mr. Game & Watch on Pyra c06/c07.

Donor: Snake (`refs/snake_attack_hi3/arc/fighter/snake`, live-extracted
2026-10-01, provenance `refs/snake_attack_hi3/SOURCE.json`).
Recipient: Pyra c06/c07 (eflame, reskinned to G&W).
Hitboxes/effects/sound/rumble: `plugin/src/acmd/snake_attack_hi3.rs`.
Cancel frame: `attack_hi3` = **38**, flags 0x84, taken whole from Snake's own
motion-list entry (against G&W's own entry, which is a different number).

What is written
---------------
* Snake's `c02attackhi3.nuanmb`, retargeted onto the **built** recipient
  skeleton (Pyra's grafted onto G&W's), written over the `c02attackhi3.nuanmb`
  eflame already has for that kind. The animation-name field of the donor's
  entry is left exactly as Snake wrote it and asserted to hash to the same file
  this build writes, so no alias is consumed.
* Snake's own `attack_hi3` motion-list entry, whole: kind, `game_script`
  (`game_attackhi3`), flags, blend, cancel frame and clip name.
* The recipient's own idle Visibility group, and **no** Material group. Snake's
  own Visibility group names 26 of his face/eye/bandana meshes, none of which
  exist on the recipient, and his 2 Material groups have no counterpart either.

# The filter is not the thing that went wrong last time

The user rejected the earlier R.O.B. down-tilt clips because a filtered retarget
left the left limbs in the rest pose (T-0036/T-0048, `handbook/04`), so this
generator *measures* rather than assumes: `leg_motion` in the report is the
largest rotation and translation each leg chain bone reaches against the
recipient idle, and `deploy_for_slot` refuses to ship if any of
`LegL/R`, `KneeL/R`, `FootL/R`, `ToeL/R` is static. Measured on the built c06
skeleton: 77 of 87 transform nodes survive, the 10 dropped ones are `FaceN` and
the nine `S_Bandanna*` nodes, and the whole leg chain moves - `LegL/R` 78-93
degrees, `KneeL/R` 80-98, `FootL/R` 54-103, and `ToeL/R` translate 0.59 units
with no rotation of their own.

# What is deliberately not here

No bone remapping inside the ACMD module: the donor writes its hitboxes on
`top`/`kneel`/`legl` and so does the G&W handler this replaces. See that
module's docstring and `projects/pgwr/TODO.md`.

Unverified: how the move looks or hits on hardware. Offline node coverage is
tier B; the visual result is tier D and needs the user's console judgment.
"""
from pathlib import Path
import hashlib
import math
import struct
import zlib

import ssbh_data_py as s

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
DONOR = ROOT / 'refs/snake_attack_hi3/arc/fighter/snake/motion/body/c00'
ACMD = ROOT / 'src/pgwr/plugin/src/acmd/snake_attack_hi3.rs'

KIND = 'attack_hi3'
CLIP = 'c02attackhi3.nuanmb'
PINS = {
    CLIP: ('f5151e106cbf78764159adf326e36e761d1800dfa189c06cfd77bfd76d9f5f71', 45760),
    'motion_list.bin': ('b70e42ca1e6ea143301349e268af5a7e98d391d0321a39c79a4187ef6fd39c34', 45740),
}
# Read from the pinned motion_list.bin on 2026-10-01
# (`refs/snake_attack_hi3/inventory.json`). G&W's own entry is deliberately not
# compared here: build.py replaces every G&W kind wholesale and the recipient's
# pre-existing number is not what this move should run on.
EXPECTED_CANCEL = 38
EXPECTED_FLAGS = 0x84
# Bones whose motion has to be present for this to be Snake's kick on G&W's body.
LEG_BONES = ('LegL', 'LegR', 'KneeL', 'KneeR', 'FootL', 'FootR', 'ToeL', 'ToeR')


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
    """Snake's own raw `attack_hi3` entry, whole, from the pinned motion list."""
    data = _pinned('motion_list.bin').read_bytes()
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    if magic != hash40('motion'):
        raise RuntimeError('snake motion_list.bin is not a motion list')
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
                raise RuntimeError(f'Snake {KIND} no longer names {CLIP}: {[hex(a) for a in anims]}')
            if cancel != EXPECTED_CANCEL or flags != EXPECTED_FLAGS:
                raise RuntimeError(f'Snake {KIND}: cancel {cancel} flags {flags:#x} '
                                   f'differ from the pinned reading')
            if game_script != hash40('game_' + KIND.replace('_', '')):
                raise RuntimeError(f'Snake {KIND} game_script {game_script:#x} is not '
                                   f'game_{KIND.replace("_", "")}')
            return {'raw': data[start:end], 'kind': kind, 'game_script': game_script,
                    'flags': flags, 'blend': blend, 'n_anims': n_anims, 'anims': anims,
                    'size': size, 'cancel': cancel}
        offset = end
    raise RuntimeError(f'Snake motion list has no kind {target_kind:#x}')


def _angle_between(q, r):
    """Degrees between two SSBH xyzw rotations, sign-insensitive."""
    a = [float(x) for x in q.rotation]
    b = [float(x) for x in r.rotation]
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    dot = abs(sum(x / na * y / nb for x, y in zip(a, b)))
    return math.degrees(2.0 * math.acos(min(1.0, dot)))


def leg_motion(tracks, idle_values):
    """Largest rotation/translation each leg-chain bone reaches against the idle.

    The point is to catch the failure the user rejected on the R.O.B. down tilt:
    a retarget that keeps the clip's node names but leaves the limbs in rest
    pose because their names did not survive the filter.
    """
    result = {}
    for name in LEG_BONES:
        values = tracks.get(name)
        base = idle_values.get(name)
        if values is None or base is None:
            result[name] = {'present': bool(values is not None), 'idle_base': bool(base is not None),
                            'max_rotation_deg': None, 'max_translation': None}
            continue
        rotation = max(_angle_between(v, base) for v in values)
        translation = max(max(abs(float(x) - float(y))
                              for x, y in zip(v.translation, base.translation)) for v in values)
        result[name] = {'present': True, 'idle_base': True,
                        'max_rotation_deg': round(rotation, 2),
                        'max_translation': round(translation, 4),
                        # A foot bone can carry the kick as pure translation (measured:
                        # `ToeL`/`ToeR` rotate 0 deg and translate 0.59 units), so
                        # "moved" is either channel, not rotation alone.
                        'moved': bool(rotation > 1.0 or translation > 0.05)}
    return result


def retarget(model_dir, out_path, gw_slot='c06', idle_path=None):
    """Retarget Snake's up-tilt clip onto the built recipient skeleton.

    `model_dir` must be the **built** model (Pyra's skeleton grafted onto
    G&W's), not the raw G&W model, for the same reason the jab, down tilt and
    forward smash use it: filtering against the built skeleton is what keeps the
    bones Pyra's graft contributed. `idle_path` defaults to the recipient idle
    this build has already written beside the destination, which is how
    `build.py` calls it; nothing is read from the ARC export, so this works in a
    tree where `dumps/arc` is empty.
    """
    src = _pinned(CLIP)
    model_path = Path(model_dir) / 'model.nusktb'
    skel = s.skel_data.read_skel(str(model_path))
    exact = {b.name for b in skel.bones}
    folded = {b.name.lower(): b.name for b in skel.bones}

    idle_path = Path(idle_path) if idle_path else Path(out_path).parent / 'a00wait1.nuanmb'
    if not idle_path.is_file():
        raise RuntimeError(f'Need the built recipient idle (no guessed visibility): {idle_path}')
    idle = s.anim_data.read_anim(str(idle_path))
    idle_vis = next(g for g in idle.groups if g.group_type.name == 'Visibility')
    idle_values = {n.name: n.tracks[0].values[0] for g in idle.groups
                   if g.group_type.name == 'Transform' for n in g.nodes}

    donor = s.anim_data.read_anim(str(src))
    transform = next(g for g in donor.groups if g.group_type.name == 'Transform')
    kept, dropped, case_only = [], [], []
    for node in transform.nodes:
        if node.name in exact:
            kept.append(node)
        elif node.name.lower() in folded:
            case_only.append((node.name, folded[node.name.lower()]))
        else:
            dropped.append(node.name)
    if not kept:
        raise RuntimeError(f'{CLIP}: no transform node survived the filter')
    transform.nodes = kept

    # The recipient's own idle mesh-visibility states, replicated. Snake's own
    # Visibility group names 26 of his face/eye meshes, and his 2 Material
    # groups have no counterpart on this recipient.
    vis_nodes = [s.anim_data.NodeData(node.name, [s.anim_data.TrackData(
        'Visibility', values=[node.tracks[0].values[0]])]) for node in idle_vis.nodes]
    donor.groups = [transform, s.anim_data.GroupData(s.anim_data.GroupType.Visibility, vis_nodes)]

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    donor.save(str(out_path))

    check = s.anim_data.read_anim(str(out_path))
    groups = [(g.group_type.name, len(g.nodes)) for g in check.groups]
    got = {n.name for n in next(g for g in check.groups if g.group_type.name == 'Transform').nodes}
    if got != {n.name for n in kept}:
        raise RuntimeError(f'Transform node set changed after saving {out_path}')
    if groups != [('Transform', len(kept)), ('Visibility', len(vis_nodes))]:
        raise RuntimeError(f'{out_path}: unexpected groups after save: {groups}')

    tracks = {n.name: n.tracks[0].values for n in transform.nodes}
    frames = sorted({len(v) for v in tracks.values()})
    legs = leg_motion(tracks, idle_values)
    entry = get_entry()
    return {'donor_sha256': sha(src), 'motion_list_sha256': sha(DONOR / 'motion_list.bin'),
            'recipient_skeleton_sha256': sha(model_path), 'recipient_idle_sha256': sha(idle_path),
            'acmd_sha256': sha(ACMD), 'final_frame_index': donor.final_frame_index,
            'transform_nodes': len(transform.nodes), 'bones_kept': len(kept),
            'bones_dropped': dropped, 'case_only': case_only, 'vis_nodes': len(vis_nodes),
            'material_groups_dropped': 2, 'frames': frames, 'sha256': sha(out_path),
            'motion_entry': {'kind': hex(entry['kind']), 'game_script': hex(entry['game_script']),
                             'flags': entry['flags'], 'blend': entry['blend'],
                             'cancel': entry['cancel'],
                             'anims': [hex(a) for a in entry['anims']]},
            'leg_motion': legs,
            'legs_all_moving': all(v.get('moved') for v in legs.values()),
            'game_behavior': 'unverified; needs console review'}


def deploy_for_slot(slot, out_dir, gw_slot='c06', model_dir=None, idle_path=None):
    """Write the retargeted up tilt over eflame's own `c02attackhi3.nuanmb`."""
    if model_dir is None:
        model_dir = ROOT / 'builds/pgwr/pyra_gamewatch_reskin/ultimate/mods/pyra_gamewatch_reskin' \
                           f'/fighter/eflame/model/body/{slot}'
    dst = Path(out_dir) / CLIP
    report = retarget(model_dir, dst, gw_slot, idle_path)
    if report['case_only']:
        raise RuntimeError(f'nodes matched only case-insensitively: {report["case_only"]}')
    if not report['legs_all_moving']:
        static = {k: v for k, v in report['leg_motion'].items() if not v.get('moved')}
        raise RuntimeError(f'{slot}: leg chain bones are static after retarget: {static}')
    return {CLIP: report, 'motion_entry': {KIND: get_entry()['cancel']},
            'dropped': report['bones_dropped']}


if __name__ == '__main__':
    import argparse
    import tempfile
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-body', type=Path,
                        help='built recipient model/body/<slot> directory to filter against')
    parser.add_argument('--out', type=Path, help='directory to write c02attackhi3.nuanmb into')
    parser.add_argument('--idle', type=Path,
                        help='recipient a00wait1.nuanmb (defaults to a00wait1.nuanmb beside --out)')
    args = parser.parse_args()
    entry = get_entry()
    print(f"Snake {KIND}: cancel frame {entry['cancel']}, flags {entry['flags']:#x}, "
          f"game_script {entry['game_script']:#x}, anims {[hex(a) for a in entry['anims']]}")
    assert entry['cancel'] == EXPECTED_CANCEL and entry['flags'] == EXPECTED_FLAGS
    if not args.model_body or not args.out:
        print('(pass --model-body and --out to retarget against a built recipient)')
    else:
        with tempfile.TemporaryDirectory() as tmp:
            rep = deploy_for_slot('c06', tmp, 'c06', args.model_body, args.idle)
        clip = rep[CLIP]
        print(f"retarget: {clip['bones_kept']} bones kept, {clip['vis_nodes']} visibility nodes, "
              f"frames {clip['frames']}, sha256 {clip['sha256']}")
        print(f"dropped (not on the recipient): {clip['bones_dropped']}")
        print('leg motion:')
        for name, value in clip['leg_motion'].items():
            print(f"  {name:6s} {value}")
        assert clip['legs_all_moving']
        print('build_snake_uptilt OK')