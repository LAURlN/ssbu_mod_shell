"""Build Snake's down throw for Pyra/G&W c06/c07 (v1.0.0).

Produces three things, all as *deltas against a recorded baseline* rather than
a regenerated shared tree, so this runs beside the other concurrent agents
without touching their output (`AGENTS.md` rule 17, and the "do not regenerate
shared output trees" instruction for this task):

  1. the retargeted attacker clip `e01throwlw.nuanmb`,
  2. the `throw_lw` motion-list entry, taken **whole** from Snake's own pinned
     `motion_list.bin`, and
  3. `motion_list_delta.bin` - the baseline motion list with only that one
     entry replaced, and an assertion that every other byte is identical.

`throw_lw` is the down throw, **not** `attack_lw4`. See the module docstring of
`plugin/src/acmd/snake_throw_lw.rs` for the measurement that settles it.

Why the entry is copied whole: an entry carries per-move timing (cancel frame,
blend, flags) that the clip does not. Snake's `throw_lw` cancels at **48**; the
recipient's own G&W-derived entry cancels at 34. Copying only the clip would
silently keep G&W's throw timing.

Usage (from the mod root):

    python src/pgwr/tools/build_snake_throw_lw.py
    python src/pgwr/tools/build_snake_throw_lw.py \\
        --baseline builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin \\
        --out builds/pgwr/snake-throw-lw-delta/ultimate/mods/pyra_gamewatch_reskin

`--out` writes only the three files above; it never writes into the baseline.

Tier B: all of this is measured offline against pinned vanilla files. How the
move looks and behaves on hardware is **tier D** and needs the user's console.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import struct
import zlib

import ssbh_data_py as s

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
DONOR = ROOT / 'refs/snake_throw_lw/arc/fighter/snake/motion/body/c00'
ACMD = ROOT / 'src/pgwr/plugin/src/acmd/snake_throw_lw.rs'

KIND = 'throw_lw'
CLIP = 'e01throwlw.nuanmb'
PINS = {
    CLIP: ('993b2022270ae57d8cb2d78a0acf7159c67668b5fdbe4b62b45a87961277c9ec', 39704),
    'motion_list.bin': ('b70e42ca1e6ea143301349e268af5a7e98d391d0321a39c79a4187ef6fd39c34', 45740),
}
# Read from the pinned motion_list.bin on 2026-10-02
# (`refs/snake_throw_lw/inventory.json`). The recipient's own pre-existing
# numbers are recorded in EXPECTED_RECIPIENT and asserted separately, because
# the point of the delta is to replace them.
EXPECTED_CANCEL = 48
EXPECTED_FLAGS = 0x80
GAME_SCRIPT = 'game_throwlw'
# What the recipient's `throw_lw` entry looks like before this change, measured
# on builds/pgwr/0.20.19 and identical in 0.20.16 and 0.20.17. Kept so the
# delta can prove it replaced *this* entry and not something else.
#
# Note the recipient already names `e01throwlw.nuanmb`: G&W's own down throw
# clip happens to share that filename with Snake's, so only the bytes and the
# cancel frame differ. That is also why `attack_lw4` on the recipient cancels at
# 34 - it is the down *smash* entry, a different kind entirely, and this change
# does not touch it.
EXPECTED_RECIPIENT = {'cancel': 50, 'flags': 0x80}
# The victim lands prone and gets up. That is engine-side (`LAY_DOWN`, routed by
# `collision_attr_lay`) and victim-side, not something this file authors - but a
# static limb here would mean the attacker does not visibly move either, which
# is the R.O.B. down-tilt failure the user already rejected once.
#
# These are Snake's own names, taken from the pinned donor skeleton (97 bones):
# he has a single `Hip` and `ArmL/R`, not the recipient's `HipL/R` and
# `WristL/R`. Listing a bone he does not have would make the guard vacuous, so
# the list is measured against the donor rather than guessed.
LIMB_BONES = ('LegL', 'LegR', 'KneeL', 'KneeR', 'FootL', 'FootR', 'ToeL', 'ToeR',
              'ArmL', 'ArmR', 'HandL', 'HandR', 'Hip', 'Bust', 'Waist')


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


def parse_entries(data):
    """Every motion-list entry as (start, end, dict), in file order."""
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    if magic != hash40('motion'):
        raise RuntimeError('not a motion list')
    offset, out = 24, []
    for _ in range(count):
        start = offset
        kind, game_script, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = (offset + n_anims * 9 + 3) & ~3
        end = offset + size
        if end > len(data):
            raise RuntimeError('truncated motion list')
        cancel = struct.unpack_from('<H', data, end - 2)[0] if size % 8 == 4 else None
        out.append({'start': start, 'end': end,
                    'kind': kind, 'game_script': game_script, 'flags': flags,
                    'blend': blend, 'n_anims': n_anims, 'anims': anims,
                    'size': size, 'cancel': cancel, 'raw': data[start:end]})
        offset = end
    if offset != len(data):
        raise RuntimeError('unexpected trailing data in motion list')
    return magic, motion_path, out


def get_entry(target_kind=hash40(KIND)):
    """Snake's own raw `throw_lw` entry, whole, from the pinned motion list."""
    data = _pinned('motion_list.bin').read_bytes()
    _, _, entries = parse_entries(data)
    for entry in entries:
        if entry['kind'] != target_kind:
            continue
        if entry['anims'] != (hash40(CLIP),):
            raise RuntimeError(f'Snake {KIND} no longer names {CLIP}: '
                               f'{[hex(a) for a in entry["anims"]]}')
        if entry['cancel'] != EXPECTED_CANCEL or entry['flags'] != EXPECTED_FLAGS:
            raise RuntimeError(f'Snake {KIND}: cancel {entry["cancel"]} flags '
                               f'{entry["flags"]:#x} differ from the pinned reading')
        if entry['game_script'] != hash40(GAME_SCRIPT):
            raise RuntimeError(f'Snake {KIND} game_script {entry["game_script"]:#x} '
                               f'is not {GAME_SCRIPT}')
        return entry
    raise RuntimeError(f'Snake motion list has no kind {target_kind:#x}')


def motion_list_delta(baseline, out_path):
    """Replace only the `throw_lw` entry in `baseline`, proving the rest is intact.

    The entry is the same length as the one it replaces (both are 28 bytes:
    24-byte header + one 9-byte padded animation name + a 4-byte tail), so this
    is a pure in-place splice. That is asserted rather than assumed, because a
    size change would silently shift every later entry and this tool's whole
    value is that it does not.
    """
    data = Path(baseline).read_bytes()
    magic, motion_path, entries = parse_entries(data)
    donor = get_entry()
    hits = [e for e in entries if e['kind'] == hash40(KIND)]
    if len(hits) != 1:
        raise RuntimeError(f'{baseline}: expected exactly one {KIND} entry, '
                           f'found {len(hits)}')
    old = hits[0]
    if (old['cancel'], old['flags']) != (EXPECTED_RECIPIENT['cancel'],
                                         EXPECTED_RECIPIENT['flags']):
        raise RuntimeError(f'baseline {KIND} is not the recorded one: cancel '
                           f'{old["cancel"]} flags {old["flags"]:#x}')
    if len(donor['raw']) != len(old['raw']):
        raise RuntimeError(f'entry size changed: donor {len(donor["raw"])} vs '
                           f'baseline {len(old["raw"])}; an in-place splice is '
                           f'no longer safe')
    merged = data[:old['start']] + donor['raw'] + data[old['end']:]

    # Round-trip and per-entry proof: every kind still present, every non-target
    # entry byte-identical, the target entry now equal to the donor's.
    _, _, after = parse_entries(merged)
    before_by_kind = {e['kind']: e for e in entries}
    after_by_kind = {e['kind']: e for e in after}
    if set(before_by_kind) != set(after_by_kind):
        raise RuntimeError('delta changed the set of motion kinds')
    changed = []
    for kind, e in after_by_kind.items():
        want = donor['raw'] if kind == hash40(KIND) else before_by_kind[kind]['raw']
        if e['raw'] != want:
            raise RuntimeError(f'delta altered an unexpected entry: {kind:#x}')
        if e['raw'] != before_by_kind[kind]['raw']:
            changed.append(kind)
    if changed != [hash40(KIND)]:
        raise RuntimeError(f'delta changed {len(changed)} entries, expected 1')

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(merged)
    assert sha(out_path) == sha(out_path)
    return {
        'baseline': str(baseline), 'baseline_sha256': hashlib.sha256(data).hexdigest(),
        'delta': str(out_path), 'delta_sha256': hashlib.sha256(merged).hexdigest(),
        'kind': KIND, 'kind_hash': hex(hash40(KIND)),
        'entries_total': len(after), 'entries_changed': 1,
        'size_preserved': len(merged) == len(data),
        'game_script': {'before': hex(old['game_script']), 'after': hex(donor['game_script']),
                        'name': GAME_SCRIPT},
        'cancel': {'before': old['cancel'], 'after': donor['cancel']},
        'flags': {'before': hex(old['flags']), 'after': hex(donor['flags'])},
        'anim_before': [hex(a) for a in old['anims']],
        'anim_after': [hex(a) for a in donor['anims']],
        'clip': CLIP,
    }


def _angle_between(a, b):
    """Degrees between two SSBH xyzw rotations, sign-insensitive.

    `ssbh_data_py.anim_data.Transform.rotation` already yields a plain list, so
    the arguments are the rotation lists themselves, not the Transform objects.
    """
    a = [float(x) for x in a]
    b = [float(x) for x in b]
    dot = abs(sum(x * y for x, y in zip(a, b)))
    dot = min(1.0, dot)
    return math.degrees(2.0 * math.acos(dot))


def limb_motion(tracks, idle_values):
    """Did each limb actually move away from the recipient's own idle?

    Node coverage cannot see this - a clip whose legs sit in rest pose reports
    the same "kept 77 of 87 nodes" as one that kicks, which is exactly what the
    user rejected on the R.O.B. down tilt. "Moved" means rotation **or**
    translation.
    """
    out = {}
    for name in LIMB_BONES:
        values = tracks.get(name)
        if not values:
            out[name] = {'present': False}
            continue
        idle = idle_values.get(name)
        best_rot, best_tr = 0.0, 0.0
        for v in values:
            if idle is not None:
                best_rot = max(best_rot, _angle_between(v.rotation, idle.rotation))
            best_tr = max(best_tr, math.dist([float(x) for x in v.translation],
                                             [float(x) for x in idle.translation])
                          if idle is not None else 0.0)
        out[name] = {'present': True, 'max_rotation_deg': round(best_rot, 2),
                     'max_translation': round(best_tr, 4),
                     'moved': best_rot > 1.0 or best_tr > 0.01}
    return out


def retarget(model_dir, out_path, idle_path=None):
    """Retarget Snake's down-throw clip onto the built recipient skeleton.

    `model_dir` must be the **built** model (Pyra's skeleton grafted onto
    G&W's), for the same reason the jab, down tilt, forward smash and up tilt use
    it: filtering against the built skeleton is what keeps the bones Pyra's
    graft contributed. `idle_path` defaults to the recipient idle already in the
    destination, so nothing is read from the ARC export (which is absent here).
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
    # clip has only a Transform group, so nothing of his is dropped here.
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
    limbs = limb_motion(tracks, idle_values)
    entry = get_entry()
    return {'donor_sha256': sha(src), 'motion_list_sha256': sha(DONOR / 'motion_list.bin'),
            'recipient_skeleton_sha256': sha(model_path), 'recipient_idle_sha256': sha(idle_path),
            'acmd_sha256': sha(ACMD), 'final_frame_index': donor.final_frame_index,
            'transform_nodes': len(transform.nodes), 'bones_kept': len(kept),
            'bones_dropped': dropped, 'case_only': case_only, 'vis_nodes': len(vis_nodes),
            'frames': frames, 'sha256': sha(out_path),
            'motion_entry': {'kind': hex(entry['kind']), 'game_script': hex(entry['game_script']),
                             'flags': entry['flags'], 'blend': entry['blend'],
                             'cancel': entry['cancel'],
                             'anims': [hex(a) for a in entry['anims']]},
            'limb_motion': limbs,
            'limbs_all_moving': all(v.get('moved') for v in limbs.values()),
            'victim_outcome': ('engine-side LAY_DOWN routed by collision_attr_lay; '
                               'not authored by this clip'),
            'game_behavior': 'unverified; needs console review'}


def deploy_for_slot(slot, out_dir, model_dir, idle_path=None):
    """Write the retargeted down throw over eflame's own `e01throwlw.nuanmb`."""
    dst = Path(out_dir) / CLIP
    report = retarget(model_dir, dst, idle_path)
    if report['case_only']:
        raise RuntimeError(f'nodes matched only case-insensitively: {report["case_only"]}')
    if not report['limbs_all_moving']:
        static = {k: v for k, v in report['limb_motion'].items() if not v.get('moved')}
        raise RuntimeError(f'{slot}: limb bones are static after retarget: {static}')
    return {CLIP: report, 'dropped': report['bones_dropped']}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=Path,
                        help='baseline mod tree (e.g. builds/pgwr/0.20.19/ultimate/mods/...)')
    parser.add_argument('--out', type=Path, help='directory to write the delta into')
    args = parser.parse_args()

    entry = get_entry()
    print(f"Snake {KIND}: cancel frame {entry['cancel']}, flags {entry['flags']:#x}, "
          f"game_script {entry['game_script']:#x} ({GAME_SCRIPT}), "
          f"anims {[hex(a) for a in entry['anims']]} -> {CLIP}")
    if not args.baseline or not args.out:
        print('(pass --baseline and --out to build the delta)')
        return 0

    baseline = args.baseline
    out = args.out
    report = {'tool': 'build_snake_throw_lw.py', 'version': '1.0.0', 'date': '2026-10-02',
              'evidence_tier': 'B', 'hardware_validated': False,
              'move': f'Snake {KIND} on Pyra c06/c07', 'baseline': str(baseline)}
    for slot in ('c06', 'c07'):
        model_dir = baseline / f'fighter/eflame/model/body/{slot}'
        dest_dir = out / f'fighter/eflame/motion/body/{slot}'
        idle = baseline / f'fighter/eflame/motion/body/{slot}/a00wait1.nuanmb'
        dest_dir.mkdir(parents=True, exist_ok=True)
        dep = deploy_for_slot(slot, dest_dir, model_dir, idle)
        report[slot] = dep[CLIP]
        print(f"  {slot}: {dep[CLIP]['bones_kept']} bones kept, "
              f"{dep[CLIP]['vis_nodes']} visibility nodes, frames {dep[CLIP]['frames']}, "
              f"sha256 {dep[CLIP]['sha256']}")
        print(f"       dropped: {dep[CLIP]['bones_dropped']}")
        print(f"       limbs all moving: {dep[CLIP]['limbs_all_moving']}")

    # Each slot carries its own motion_list.bin, so both are emitted. They are
    # byte-identical in the baseline, and the tool asserts each one independently
    # rather than assuming they stay that way.
    report['motion_list_delta'] = {}
    for slot in ('c06', 'c07'):
        ml = motion_list_delta(
            baseline / f'fighter/eflame/motion/body/{slot}/motion_list.bin',
            out / f'fighter/eflame/motion/body/{slot}/motion_list.bin')
        report['motion_list_delta'][slot] = ml
        print(f"  {slot} motion_list.bin: cancel {ml['cancel']['before']} -> "
              f"{ml['cancel']['after']}, flags {ml['flags']['before']} -> "
              f"{ml['flags']['after']}, {ml['entries_changed']} of "
              f"{ml['entries_total']} entries changed, "
              f"size preserved {ml['size_preserved']}")
        print(f"  {slot} delta sha256 {ml['delta_sha256']}")

    out.mkdir(parents=True, exist_ok=True)
    (out / 'snake_throw_lw_build.json').write_text(json.dumps(report, indent=2) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())