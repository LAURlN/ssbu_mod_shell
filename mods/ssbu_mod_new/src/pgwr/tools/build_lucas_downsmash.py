"""Retarget Lucas's down smash for Mythra (`elight`) c06/c07. v1.0.0.

Donor: Lucas c00, pinned in `refs/lucas_attack_lw4/arc/`
(provenance `refs/lucas_attack_lw4/SOURCE.json`).
Recipient: Mythra `elight` c06/c07. Its body skeleton is **vanilla**: the
0.20.19 package ships no `fighter/elight/model/body/*/model.nusktb`, and
`build_mythra_skin` in `src/pgwr/build.py` copies only `*.nutexb` textures.
Measured, not assumed - `audit_lucas_lw4_donor.py` pins both slot models and
asserts they are byte-identical.

What is written
---------------
* Lucas's `c04attacklw4.nuanmb` and `c04attacklw4charge.nuanmb`, retargeted onto
  the recipient skeleton and written **over the clips elight already has for
  those two kinds**. Both file names already exist on the recipient, so this
  adds no motion file and no `config.json` declaration - the same shape as the
  Snake up tilt and the Little Mac forward smash, and the reason this change is
  asset-overrides-only on the motion side.
* Nothing else. No material, no extra bank, no alias. The animation-name field
  of the donor's motion entry is left exactly as Lucas wrote it and asserted to
  hash to the file this build writes, so no alias slot is consumed.

# Two motion-list findings that are not obvious

**The charge hold is `attack_lw4_hold`, not `attack_lw4_charge`.** A first pass
looking for `attack_lw4_charge` found no entry at all and read as a missing
donor file. `hash40('attack_lw4_hold')` is `0xfee188235` and that is the kind
Lucas's own charge entry carries. The kind name and the script name are also not
a mechanical pair: the hold entry's kind is `attack_lw4_hold` but its
`game_script` is `game_attacklw4charge`. `audit_lucas_lw4_donor.py` proves both
by re-reading G&W's list - a *different* fighter - and comparing every field
against `dumps/scripts/gamewatch_motion_list.yml`, an independent dump by
different tooling.

**The two entries are not equally different.** `attack_lw4` needs Lucas's
(cancel **316** against Mythra's 56, and the two entries are not byte-equal),
but `attack_lw4_hold` is **byte-identical** between Lucas and Mythra: same
cancel 0, same flags 0x80, same `game_attacklw4charge`, same clip name. So the
motion-list delta for this port is exactly one changed u16 in one entry, and
that is asserted here rather than left to the installer.

# Retargeting: name filter plus the recipient's own visibility

The donor clip's 68 transform nodes are filtered by exact name against the
recipient skeleton. Measured on the built recipient: **66 of 68 survive, 2 are
dropped (`Bat`, `BatL` - Lucas's bat), 0 case-only matches, and 0 parent
mismatches.** The parent comparison is not decoration: a name that survives
under a *different* parent bends the wrong way, and a plain name filter cannot
see that, so parent chains are compared by name between the two skeletons.

The donor's Visibility group names 28 of his own face/eye/psi meshes, none of
which exist on the recipient, and the donor has **no** Material group at all.
So the group is replaced with the recipient's own idle Visibility states, taken
from the built `a00wait1.nuanmb` beside the output rather than from the ARC, for
the same reason the jab, down tilt, up tilt and forward smash do it that way:
guessing a visibility state is how a retarget ends up with an invisible fighter.

# The legs are measured, not assumed

The R.O.B. down tilt was rejected by the user for leaving limbs in rest pose,
so `deploy_for_slot` refuses to ship unless every limb bone actually moves
against the recipient idle. Measured here on the built c06 skeleton: all 17 limb
bones are present and all 17 move - `LegL/R` 127/129 degrees, `KneeL/R` 103,
`FootL/R` 61/63, `ClavicleL/R` 125/97, `ShoulderL/R` 122/139, `ArmL/R` 106/86,
`HandL/R` 100/108, `Hip` 66.

Unverified: how the move looks or hits in game. Offline node coverage is tier B;
the visual and gameplay result is tier D and needs the user's console.

    python src/pgwr/tools/build_lucas_downsmash.py --check
    python src/pgwr/tools/build_lucas_downsmash.py --deploy <out>/c06 <out>/c07
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import zlib
from pathlib import Path

import ssbh_data_py as s

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
REFS = ROOT / 'refs/lucas_attack_lw4'
DONOR = REFS / 'arc/fighter/lucas/motion/body/c00'
RECIP = REFS / 'recipient'

CLIPS = {
    'attack_lw4': 'c04attacklw4.nuanmb',
    'attack_lw4_hold': 'c04attacklw4charge.nuanmb',
}
# Pinned donor clips. The motion list itself is pinned by
# `tools/audit_lucas_lw4_donor.py`, which is the single reader of it.
CLIP_PINS = {
    'c04attacklw4.nuanmb':
        ('968d9035e69eecacc427d58bd2403e803511351f65d11064d7c946164f0d5887', 42656),
    'c04attacklw4charge.nuanmb':
        ('202e5d020db31b9cf4bcdb310effe845ab8467eb3e4c76bdde5745019528012b', 24385),
}
# Read off the pinned donor list by `audit_lucas_lw4_donor.py` and recorded in
# `refs/lucas_attack_lw4/inventory.json`. Both asserted here so a donor
# revision bump fails this tool instead of quietly producing a different move.
EXPECTED = {
    'attack_lw4': {'cancel': 316, 'flags': 0x80, 'blend': 0,
                   'game_script': 'game_attacklw4'},
    'attack_lw4_hold': {'cancel': 0, 'flags': 0x80, 'blend': 0,
                        'game_script': 'game_attacklw4charge'},
}
# Mythra's own values, from the same inventory. Only `attack_lw4` differs.
RECIPIENT_CANCEL = {'attack_lw4': 56, 'attack_lw4_hold': 0}

# Real bones only. See the note in `audit_lucas_lw4_donor.py`: an earlier list
# named `ElbowL/R` and `WaistL/R`, which are not bones on either fighter, so they
# would have reported as static limbs forever.
LIMB_BONES = (
    'Hip', 'Waist', 'LegL', 'LegR', 'KneeL', 'KneeR', 'FootL', 'FootR',
    'ClavicleC', 'ClavicleL', 'ClavicleR', 'ShoulderL', 'ShoulderR',
    'ArmL', 'ArmR', 'HandL', 'HandR',
)


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pinned_clip(name: str) -> Path:
    path = DONOR / name
    digest, size = CLIP_PINS[name]
    if not path.is_file() or path.stat().st_size != size or sha(path) != digest:
        raise RuntimeError(f'{path} missing or not the pinned revision')
    return path


def read_entries(motion_list: Path) -> list:
    """Motion-list entries. Same container parse as the audit tool; see its
    `read_entries` docstring and `cross_validate_parser` for the proof that it
    matches an independent dump."""
    data = Path(motion_list).read_bytes()
    magic, _, count = struct.unpack_from('<QQQ', data, 0)
    if magic != hash40('motion'):
        raise RuntimeError('not a motion list')
    offset = 24
    out = []
    for _ in range(count):
        start = offset
        kind, script, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = (offset + n_anims * 9 + 3) & ~3
        end = offset + size
        cancel = struct.unpack_from('<H', data, end - 2)[0] if size % 8 == 4 else None
        out.append({'raw': data[start:end], 'kind': kind, 'game_script': script,
                    'flags': flags, 'blend': blend, 'anims': anims,
                    'cancel': cancel, 'size': size})
        offset = end
    if offset != len(data):
        raise RuntimeError(f'motion list has {len(data) - offset} unparsed trailing bytes')
    return out


def donor_entry(kind: str) -> dict:
    """Lucas's own entry for `kind`, whole, with the pinned reading asserted."""
    clip = CLIPS[kind]
    found = [e for e in read_entries(DONOR / 'motion_list.bin') if e['kind'] == hash40(kind)]
    if len(found) != 1:
        raise RuntimeError(f'lucas motion list: {len(found)} entries of kind {kind}')
    entry = found[0]
    want = EXPECTED[kind]
    if entry['anims'] != (hash40(clip),):
        raise RuntimeError(f'lucas {kind} no longer names {clip}')
    if entry['cancel'] != want['cancel'] or entry['flags'] != want['flags'] \
            or entry['blend'] != want['blend'] or entry['game_script'] != hash40(want['game_script']):
        raise RuntimeError(f'lucas {kind} reading differs from the pinned inventory: {entry}')
    return entry


def recipient_entry(kind: str) -> dict:
    found = [e for e in read_entries(RECIP / 'fighter/elight/motion/body/c06/motion_list.bin')
             if e['kind'] == hash40(kind)]
    if len(found) != 1:
        raise RuntimeError(f'elight motion list: {len(found)} entries of kind {kind}')
    entry = found[0]
    if entry['cancel'] != RECIPIENT_CANCEL[kind]:
        raise RuntimeError(f'elight {kind} cancel {entry["cancel"]} != pinned '
                           f'{RECIPIENT_CANCEL[kind]}')
    return entry


def motion_list_delta() -> dict:
    """Exactly what the motion list must change, and the proof it is that small.

    Returns per kind: whether the two entries differ at all, and if they do, the
    byte offset and the two u16 values. `attack_lw4_hold` is byte-identical
    between Lucas and Mythra, so nothing has to be written for it.
    """
    out = {}
    for kind in CLIPS:
        donor = donor_entry(kind)
        recip = recipient_entry(kind)
        identical = donor['raw'] == recip['raw']
        differing = [i for i, (a, b) in enumerate(zip(donor['raw'], recip['raw'])) if a != b]
        out[kind] = {
            'identical': identical,
            'donor_cancel': donor['cancel'], 'recipient_cancel': recip['cancel'],
            'donor_flags': donor['flags'], 'recipient_flags': recip['flags'],
            'game_script': EXPECTED[kind]['game_script'],
            'differing_byte_offsets': differing,
            'raw': donor['raw'].hex(),
        }
        if identical:
            assert recip['cancel'] == donor['cancel']
        else:
            # Only the cancel frame may differ. If the donor also changed flags or
            # the script, that is a real motion-list edit, not a two-byte one, and
            # it has to be said out loud rather than folded into a "small delta".
            assert donor['flags'] == recip['flags'], f'{kind}: flags differ too'
            assert donor['game_script'] == recip['game_script'], f'{kind}: script differs too'
    return out


def _angle_between(q, r) -> float:
    a = [float(x) for x in q.rotation]
    b = [float(x) for x in r.rotation]
    na = sum(x * x for x in a) ** 0.5 or 1.0
    nb = sum(x * x for x in b) ** 0.5 or 1.0
    dot = abs(sum(x / na * y / nb for x, y in zip(a, b)))
    return math.degrees(2.0 * math.acos(min(1.0, dot)))


def limb_motion(tracks, idle_values) -> dict:
    result = {}
    for name in LIMB_BONES:
        values = tracks.get(name)
        base = idle_values.get(name)
        if values is None or base is None:
            result[name] = {'present': values is not None, 'idle_base': base is not None,
                            'moved': False, 'reason': 'node or idle reference absent'}
            continue
        rotation = max(_angle_between(v, base) for v in values)
        translation = max(max(abs(float(x) - float(y))
                              for x, y in zip(v.translation, base.translation)) for v in values)
        result[name] = {'present': True, 'idle_base': True,
                        'max_rotation_deg': round(rotation, 2),
                        'max_translation': round(translation, 4),
                        # Either channel counts: a hand or foot can carry a whole
                        # pose change as pure translation.
                        'moved': bool(rotation > 1.0 or translation > 0.05)}
    return result


def _skeleton_parents(path: Path) -> dict:
    skel = s.skel_data.read_skel(str(path))
    names = [b.name for b in skel.bones]
    return {b.name: (None if b.parent_index is None or b.parent_index >= len(names)
                     else names[b.parent_index]) for b in skel.bones}


def retarget(kind: str, out_path: Path, idle_path: Path) -> dict:
    clip = CLIPS[kind]
    src = _pinned_clip(clip)
    model = RECIP / 'fighter/elight/model/body/c06/model.nusktb'
    recip_parents = _skeleton_parents(model)
    donor_parents = _skeleton_parents(REFS / 'arc/fighter/lucas/model/body/c00/model.nusktb')

    if not idle_path.is_file():
        raise RuntimeError(f'need the recipient idle next to the output: {idle_path}')
    idle = s.anim_data.read_anim(str(idle_path))
    idle_vis = next(g for g in idle.groups if g.group_type.name == 'Visibility')
    idle_values = {n.name: n.tracks[0].values[0] for g in idle.groups
                   if g.group_type.name == 'Transform' for n in g.nodes}

    donor = s.anim_data.read_anim(str(src))
    transform = next(g for g in donor.groups if g.group_type.name == 'Transform')
    kept, dropped, case_only, parent_mismatch = [], [], [], []
    for node in transform.nodes:
        if node.name in recip_parents:
            kept.append(node)
            if donor_parents.get(node.name) != recip_parents.get(node.name):
                parent_mismatch.append({'bone': node.name,
                                        'donor_parent': donor_parents.get(node.name),
                                        'recipient_parent': recip_parents.get(node.name)})
        elif node.name.lower() in {b.lower() for b in recip_parents}:
            case_only.append(node.name)
        else:
            dropped.append(node.name)
    if not kept:
        raise RuntimeError(f'{clip}: nothing survived the filter')
    transform.nodes = kept

    # The recipient's own idle mesh-visibility states, replicated. Lucas's
    # Visibility group names 28 of his own face/eye/psi meshes, none of which
    # exist here, and the donor has no Material group at all.
    vis_nodes = [s.anim_data.NodeData(n.name, [s.anim_data.TrackData(
        'Visibility', values=[n.tracks[0].values[0]])]) for n in idle_vis.nodes]
    donor.groups = [transform,
                    s.anim_data.GroupData(s.anim_data.GroupType.Visibility, vis_nodes)]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    donor.save(str(out_path))

    # Re-read after saving: a retarget that only *looks* right in memory has
    # been wrong before on this project.
    check = s.anim_data.read_anim(str(out_path))
    got = {n.name for n in next(g for g in check.groups
                                if g.group_type.name == 'Transform').nodes}
    if got != {n.name for n in kept}:
        raise RuntimeError(f'transform node set changed after saving {out_path}')
    groups = [(g.group_type.name, len(g.nodes)) for g in check.groups]
    if groups != [('Transform', len(kept)), ('Visibility', len(vis_nodes))]:
        raise RuntimeError(f'{out_path}: unexpected groups after save: {groups}')

    tracks = {n.name: n.tracks[0].values for n in transform.nodes}
    entry = donor_entry(kind)
    legs = limb_motion(tracks, idle_values)
    recip = recipient_entry(kind)
    return {
        'kind': kind, 'clip': clip,
        'donor_sha256': sha(src), 'output_sha256': sha(out_path),
        'output_bytes': out_path.stat().st_size,
        'recipient_skeleton_sha256': sha(model), 'recipient_idle_sha256': sha(idle_path),
        'donor_final_frame_index': donor.final_frame_index,
        'nodes_total': len(transform.nodes) + len(dropped) + len(case_only),
        'nodes_kept': len(kept), 'nodes_dropped': dropped, 'case_only': case_only,
        'parent_mismatches': parent_mismatch,
        'frames': sorted({len(v) for v in tracks.values()}),
        'visibility_nodes': len(vis_nodes), 'material_groups': 0,
        'limb_motion': legs,
        'all_limbs_present': all(legs[b]['present'] for b in LIMB_BONES),
        'static_limbs': sorted(b for b, v in legs.items() if not v['moved']),
        'motion_entry': {'kind': hex(entry['kind']), 'game_script': EXPECTED[kind]['game_script'],
                         'flags': entry['flags'], 'blend': entry['blend'],
                         'cancel': entry['cancel'],
                         'anims': [hex(a) for a in entry['anims']],
                         'recipient_cancel': recip['cancel'],
                         'entry_bytes_differ': entry['raw'] != recip['raw']},
        'game_behavior': 'unverified; needs console review',
    }


def deploy(out_dir: Path, idle_dir: Path | None = None) -> dict:
    """Retarget both clips into `out_dir`, refusing to ship a static limb."""
    out_dir = Path(out_dir)
    idle_dir = Path(idle_dir) if idle_dir else out_dir
    report = {}
    for kind, clip in CLIPS.items():
        idle = idle_dir / 'a00wait1.nuanmb'
        rep = retarget(kind, out_dir / clip, idle)
        if rep['case_only']:
            raise RuntimeError(f'{clip}: nodes matched only case-insensitively: {rep["case_only"]}')
        if rep['parent_mismatches']:
            raise RuntimeError(f'{clip}: parent mismatches would bend limbs the wrong '
                               f'way: {rep["parent_mismatches"]}')
        if not rep['all_limbs_present']:
            missing = [b for b in LIMB_BONES if not rep['limb_motion'][b]['present']]
            raise RuntimeError(f'{clip}: limb bones absent from the retarget: {missing}')
        if rep['static_limbs']:
            raise RuntimeError(f'{clip}: limb bones are static after retarget: {rep["static_limbs"]}')
        report[kind] = rep
    report['motion_list'] = motion_list_delta()
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true',
                    help='assert the pinned donor reading and print the motion-list delta')
    ap.add_argument('--deploy', type=Path, nargs=2, metavar=('OUT_C06', 'OUT_C07'),
                    help='retarget both clips into these two directories')
    ap.add_argument('--idle', type=Path, nargs=2, metavar=('IDLE_C06', 'IDLE_C07'),
                    help='recipient a00wait1.nuanmb for each slot (default: beside each --deploy dir)')
    args = ap.parse_args()

    for name, (digest, size) in CLIP_PINS.items():
        path = DONOR / name
        assert path.is_file() and path.stat().st_size == size and sha(path) == digest, \
            f'{name} is not the pinned donor revision'

    delta = motion_list_delta()
    for kind, info in delta.items():
        state = 'byte-identical, nothing to write' if info['identical'] else 'DIFFERS'
        print(f'lucas {kind}: cancel {info["donor_cancel"]} vs Mythra '
              f'{info["recipient_cancel"]}, flags {info["donor_flags"]:#x} vs '
              f'{info["recipient_flags"]:#x} -> {state}'
              + ('' if info['identical'] else
                 f' (differing byte offsets {info["differing_byte_offsets"]})'))
    assert delta['attack_lw4_hold']['identical'], \
        'the charge hold used to be byte-identical; re-measure before assuming'

    if args.check:
        print('PASS: pinned Lucas down-smash reading; motion-list delta is one cancel u16')
        return 0

    assert args.deploy, 'pass --check, or --deploy OUT_C06 OUT_C07'
    idles = args.idle or [None, None]
    reports = {}
    for slot, out, idle in zip(('c06', 'c07'), args.deploy, idles):
        rep = deploy(Path(out), idle)
        reports[slot] = rep
        for kind, clip in CLIPS.items():
            r = rep[kind]
            print(f'{slot} {clip}: {r["nodes_kept"]}/{r["nodes_total"]} nodes kept, '
                  f'dropped {r["nodes_dropped"]}, frames {r["frames"]}, '
                  f'sha256 {r["output_sha256"]}')
        print(f'{slot} all {len(LIMB_BONES)} limb bones present and moving; '
              f'0 parent mismatches')
    assert reports['c06']['attack_lw4']['output_sha256'] == \
        reports['c07']['attack_lw4']['output_sha256'], \
        'c06 and c07 clips differ; the two Mythra skeletons are byte-identical'
    for kind in CLIPS:
        assert reports['c06'][kind]['output_sha256'] == reports['c07'][kind]['output_sha256']
    (Path(args.deploy[0]) / 'lucas_downsmash_retarget.json').write_text(
        json.dumps(reports, indent=2) + '\n')
    print('build_lucas_downsmash OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
