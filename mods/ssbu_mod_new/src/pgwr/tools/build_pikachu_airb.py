"""Retarget Pikachu's back air (`AttackAirB`) and landing onto eflame c06/c07 (v1.0.0).

Donor: Pikachu (`refs/pikachu_attack_air_b/`, extracted from the local 13.0.4
`data.arc` on 2026-10-03 with the workspace tool `tools/arc-extract`; ACMD text
pinned from WuBoytH/SSBU-Dumped-Scripts at commit 5900468523).
Recipient: Pyra c06/c07 (`eflame`, reskinned to G&W).
Hitboxes/effects/sound/rumble: `plugin/src/acmd/pikachu_attack_air_b.rs`.
Measurements: `tools/audit_pikachu_airb_donor.py` -> `refs/pikachu_attack_air_b/inventory.json`.

What is written
---------------
Two clips per slot, each retargeted by name intersection onto the **built**
recipient skeleton, and two motion-list entries taken whole from Pikachu's own
list.

* `c05attackairb.nuanmb` and `c05landingairb.nuanmb`.
* The `attack_air_b` and `landing_air_b` motion entries.

# The clip name does not have to change, and here it does not

The donor's `attack_air_b` entry already names `c05attackairb.nuanmb` - the exact
file name the recipient's own entry names, hash `0x147bff280f` on both sides.
So unlike Snake's up tilt there is **no spare-name alias and no `config.json`
change**: the animation-name field is left as Pikachu wrote it and the retargeted
clip is written over the file that name resolves to.

That is also why `assert_entry_names_clip` exists. The `chrom_jab_sword` finding
in CURRENT_INSTALL.md is that an animation-name hash covers the file name *with*
its extension, so a hash taken from a bare stem names a file that does not exist
and fails silently, leaving the previous clip playing. Both hashes are asserted
here rather than assumed.

# The motion-list delta is exactly two bytes per slot

Measured (`refs/pikachu_attack_air_b/inventory.json`, `delta.c0*`), the recipient's
`attack_air_b` entry differs from Pikachu's at entry-relative offsets **16** (the
flags field, `0x0080` vs Pikachu's `0x0084`) and **62** (the cancel frame, 296 vs
Pikachu's **300**), and nowhere else. `landing_air_b` is already **byte-identical**
to Pikachu's - cancel 20, flags `0x0080` - so it needs no patch at all, only the
retargeted clip.

Flags `0x0084` vs `0x0080` is not decoded here. Snake's up tilt carries the same
`0x84`, the R.O.B. down tilt carries `0x80`, and neither port claims to know what
bit 2 means; copying the donor's own word is the faithful choice and guessing a
meaning for the bit would not be. Recorded as an open item, not as a fact.

# The Visibility group comes from the recipient, never from the donor

Pikachu's clips carry a 38-node Visibility group naming 26 of his face/eye meshes
and a 1-node Material group. **Zero** of those 38 nodes exist on the built
recipient (measured). Shipping them would either be inert or, worse, disable a
recipient mesh, so the group is rebuilt from the recipient's own idle - the same
rule `build_snake_uptilt.py` applies and the reason its own donor visibility was
dropped.

# Two gates refuse to ship

`assert_parent_chains_match` and `assert_limbs_move`, both measured rather than
assumed, both with negative controls in `tools/audit_pikachu_airb_donor.py
--negative-controls`:

* **parent chains** - a name filter keeps a node whose name still exists even if
  the recipient hangs that bone off a different parent, so the limb bends the
  wrong way with no error anywhere. Measured 0 mismatches here.
* **limbs move** - node coverage cannot see a clip whose limbs sit in rest pose,
  which is what the user rejected on the R.O.B. down tilt (`handbook/04`). All 17
  tracked limb bones move here; `Hip` 176.6 deg, `ShoulderL` 169.1, `FootL` 112.7,
  `HandL` 92.2.

Unverified: how the move looks or hits on hardware. Offline node coverage is
tier B; the visual result is tier D and needs the user's console.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import ssbh_data_py as s

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
sys.path.insert(0, str(ROOT / 'tools'))
import mlist  # noqa: E402
import audit_pikachu_airb_donor as audit  # noqa: E402
import pose_fk as fk  # noqa: E402

REF = ROOT / 'refs/pikachu_attack_air_b'
DONOR = REF / 'arc/fighter/pikachu/motion/body/c00'
DONOR_SKEL = REF / 'arc/fighter/pikachu/model/body/c00/model.nusktb'
DONOR_IDLE = DONOR / 'a00wait1.nuanmb'

# The bones whose *pose* is transferred. Together with the recipient's 16 other
# native nodes (fingers, hand-hold, throw, mouth and four prop-attach helpers,
# held at the recipient idle) they are the 41 nodes G&W's own clips animate.
POSE_BONES = ('Trans', 'Rot', 'Hip', 'Waist', 'Bust', 'Neck', 'Head',
              'ClavicleC', 'ClavicleL', 'ClavicleR', 'ShoulderL', 'ShoulderR',
              'ArmL', 'ArmR', 'HandL', 'HandR', 'LegC', 'LegL', 'LegR',
              'KneeL', 'KneeR', 'FootL', 'FootR', 'ToeL', 'ToeR')
ACMD = ROOT / 'src/pgwr/plugin/src/acmd/pikachu_attack_air_b.rs'

CLIPS = {audit.KIND: audit.CLIP, audit.LANDING_KIND: audit.LANDING_CLIP}
DEFAULT_RECIPIENT = ROOT / ('builds/pgwr/0.20.23/ultimate/mods/pyra_gamewatch_reskin'
                            '/fighter/eflame')

# Taken from refs/pikachu_attack_air_b/inventory.json (motion.donor_*), and
# re-read from the pinned donor motion list on every run below.
EXPECTED = {
    audit.KIND: {'cancel': 300, 'flags': 0x0084},
    audit.LANDING_KIND: {'cancel': 20, 'flags': 0x0080},
}


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def donor_entry(kind: str) -> dict:
    """Pikachu's own raw motion-list entry for `kind`, whole, re-read every run."""
    ml = mlist.parse(DONOR / 'motion_list.bin')
    if mlist.encode(ml) != ml['data']:
        raise RuntimeError('donor motion_list.bin does not round-trip')
    entry = mlist.find(ml, kind)
    clip = CLIPS[kind]
    if list(entry['anims']) != [hash40(clip)]:
        raise RuntimeError(f'donor {kind} does not name {clip}')
    want = EXPECTED[kind]
    if entry['cancel'] != want['cancel'] or entry['flags'] != want['flags']:
        raise RuntimeError(
            f'donor {kind}: cancel {entry["cancel"]} flags {entry["flags"]:#x} differ '
            f'from the pinned reading {want}')
    if entry['gs'] != hash40('game_attackairb' if kind == audit.KIND else 'game_landingairb'):
        raise RuntimeError(f'donor {kind}: unexpected game_script {entry["gs"]:#x}')
    return entry


def retarget(kind: str, model_dir: Path, out_path: Path, idle_path: Path) -> dict:
    """Retarget one donor clip onto the built recipient skeleton for one slot (v2).

    `model_dir` must be the **built** model (Pyra's skeleton grafted onto G&W's),
    not a raw base-game model, for the same reason every other port in this repo
    filters against it: that is what keeps the bones Pyra's graft contributed.

    The output carries exactly the recipient's own native Transform node set (the
    nodes G&W's own idle and aerial clips animate), filled from two sources:

    * `POSE_BONES`: the donor's absolute rotations, with each translation rebuilt
      as `recipient idle + (donor frame - donor idle)`, so a bone the donor
      holds at a constant offset keeps *the recipient's* offset;
    * every other native node: the recipient's own idle value, held constant.

    Face, finger, hand-hold, throw and mouth tracks, Pikachu's ears/hat/tail and
    the donor's 38-node mesh-visibility group are not carried.

    Then `Rot` is shifted vertically per frame so the lower toe keeps the same
    clearance above its own neutral stance that Pikachu's keeps above his.
    """
    clip_name = CLIPS[kind]
    src = DONOR / clip_name
    skel_path = model_dir / 'model.nusktb'
    skel = fk.Skeleton(skel_path)
    donor_skel = fk.Skeleton(DONOR_SKEL)

    if not idle_path.is_file():
        raise RuntimeError(f'need the built recipient idle (no guessed visibility): {idle_path}')
    idle_anim = s.anim_data.read_anim(str(idle_path))
    idle_vis = next(g for g in idle_anim.groups if g.group_type.name == 'Visibility')
    _, idle_r = fk.read_transform_tracks(idle_path)
    _, idle_d = fk.read_transform_tracks(DONOR_IDLE)
    donor, clip_d = fk.read_transform_tracks(src)

    n = fk.frame_count(clip_d)
    if n != int(donor.final_frame_index) + 1:
        raise RuntimeError(f'{clip_name}: {n} frames but final frame index {donor.final_frame_index}')
    for bone in POSE_BONES:
        for where, tracks in (('donor clip', clip_d), ('donor idle', idle_d),
                              ('recipient idle', idle_r)):
            if bone not in tracks:
                raise RuntimeError(f'{clip_name}: pose bone {bone} has no track in the {where}')
        if bone not in skel.index or bone not in donor_skel.index:
            raise RuntimeError(f'{clip_name}: pose bone {bone} is not on both skeletons')
    transform_group = next(g for g in donor.groups if g.group_type.name == 'Transform')
    for node in transform_group.nodes:
        for track in node.tracks:
            f = track.transform_flags
            if (f.override_translation or f.override_rotation or f.override_scale
                    or f.override_compensate_scale or track.compensate_scale):
                raise RuntimeError(f'{clip_name}: {node.name} carries transform flags this '
                                   f'retarget does not model')
    # What the construction below assumes and a different donor could break.
    # Scale is composed multiplicatively (recipient idle * donor / donor idle), so
    # both idles must sit at unit scale for the result to mean "the donor's squash
    # and stretch", and the bones the donor actually scales are recorded in the
    # report instead of being carried silently. Measured on the pinned donor: the
    # attack scales only `Tail2` (not carried); the landing is Pikachu's squash,
    # `Rot` y down to 0.8 and `Hip` within +-4%.
    for bone in POSE_BONES:
        for where, tracks in (('donor idle', idle_d), ('recipient idle', idle_r)):
            if max(abs(float(x) - 1.0) for x in tracks[bone][0].scale) > 1e-4:
                raise RuntimeError(f'{clip_name}: {bone} is scaled in the {where}')
    scaled = sorted(name for name, values in clip_d.items()
                    if any(abs(float(x) - 1.0) > 1e-4 for v in values for x in v.scale))
    expected_scaled = {'attack_air_b': {'Tail2'}, 'landing_air_b': {'Rot', 'Hip'}}[kind]
    if set(scaled) != expected_scaled:
        raise RuntimeError(f'{clip_name}: donor scales {scaled}, pinned reading is '
                           f'{sorted(expected_scaled)}')
    for v in clip_d['Trans']:
        if abs(abs(float(v.rotation[3])) - 1.0) > 1e-4:
            raise RuntimeError(f'{clip_name}: Trans rotates, so the vertical correction '
                               f'on Rot would not be a world-space shift')

    native = [node.name for node in next(
        g for g in idle_anim.groups if g.group_type.name == 'Transform').nodes]
    out = {}
    for name in native:
        base_r = idle_r[name][0]
        if name not in POSE_BONES:
            out[name] = [base_r] * n
            continue
        base_d = idle_d[name][0]
        frames = []
        for f in range(n):
            d = fk.value_at(clip_d[name], f)
            translation = [float(base_r.translation[i]) + float(d.translation[i])
                           - float(base_d.translation[i]) for i in range(3)]
            frames.append(s.anim_data.Transform(
                [float(base_r.scale[i]) * float(d.scale[i]) / float(base_d.scale[i])
                 for i in range(3)],
                [float(x) for x in d.rotation], translation))
        out[name] = frames

    # Vertical ground-contact correction on Rot (a child of Trans, whose rotation
    # is the identity - asserted above - so a shift of Rot's y is a world shift).
    contact_d_idle = fk.lowest_toe(donor_skel, donor_skel.worlds(fk.locals_at(donor_skel, idle_d, 0)))
    contact_r_idle = fk.lowest_toe(skel, skel.worlds(fk.locals_at(skel, idle_r, 0)))
    corrections = []
    for f in range(n):
        target = contact_r_idle + (fk.lowest_toe(donor_skel, donor_skel.worlds(
            fk.locals_at(donor_skel, clip_d, f))) - contact_d_idle)
        have = fk.lowest_toe(skel, skel.worlds(fk.locals_at(skel, out, f)))
        corrections.append(target - have)
    out['Rot'] = [s.anim_data.Transform(list(v.scale), list(v.rotation),
                                        [float(v.translation[0]),
                                         float(v.translation[1]) + corrections[f],
                                         float(v.translation[2])])
                  for f, v in enumerate(out['Rot'])]

    def collapsed(values):
        def key(v):
            return (tuple(v.scale), tuple(v.rotation), tuple(v.translation))
        return values[:1] if len({key(v) for v in values}) == 1 else values

    transform_nodes = [s.anim_data.NodeData(name, [s.anim_data.TrackData(
        'Transform', values=collapsed(out[name]))]) for name in native]

    # The recipient's own idle mesh-visibility states, replicated. Zero of
    # Pikachu's 38 visibility nodes exist on this recipient.
    vis_nodes = [s.anim_data.NodeData(node.name, [s.anim_data.TrackData(
        'Visibility', values=[node.tracks[0].values[0]])]) for node in idle_vis.nodes]
    measurement = audit.retarget_measurement(src, skel_path, idle_path)
    donor.groups = [s.anim_data.GroupData(s.anim_data.GroupType.Transform, transform_nodes),
                    s.anim_data.GroupData(s.anim_data.GroupType.Visibility, vis_nodes)]

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    donor.save(str(out_path))

    check = s.anim_data.read_anim(str(out_path))
    groups = [(g.group_type.name, len(g.nodes)) for g in check.groups]
    got = [n_.name for n_ in next(g for g in check.groups
                                  if g.group_type.name == 'Transform').nodes]
    if got != native:
        raise RuntimeError(f'{out_path}: Transform node set changed after saving')
    if groups != [('Transform', len(native)), ('Visibility', len(vis_nodes))]:
        raise RuntimeError(f'{out_path}: unexpected groups after save: {groups}')

    audit.assert_parent_chains_match(measurement, clip_name)
    audit.assert_limbs_move(src, skel_path, idle_path)
    not_carried = {}
    for name in clip_d:
        if name in POSE_BONES:
            continue
        if name not in skel.index:
            not_carried[name] = 'not a bone on the recipient (costume appendage)'
        elif name in idle_r:
            not_carried[name] = 'recipient-native node: held at the recipient idle'
        else:
            not_carried[name] = 'face-only bone the recipient animates nowhere'
    return {
        'clip': clip_name,
        'frames': n,
        'donor_sha256': sha(src),
        'output_sha256': sha(out_path),
        'output_bytes': out_path.stat().st_size,
        'donor_final_frame_index': donor.final_frame_index,
        'transform_nodes': measurement['transform_nodes'],
        'native_nodes_written': len(native),
        'pose_bones_transferred': list(POSE_BONES),
        'donor_bones_scaled': scaled,
        'bones_kept': len(POSE_BONES),
        'donor_nodes_not_carried': not_carried,
        'bones_dropped': sorted(k for k, v in not_carried.items() if v.startswith('not a bone')),
        'case_only': [],
        'parent_chain_mismatches': measurement['parent_chain_mismatches'],
        'vis_nodes': len(vis_nodes),
        'donor_visibility_nodes_discarded': measurement['visibility_group_nodes'],
        'material_group_nodes_discarded': measurement['material_group_nodes'],
        'limb_motion': measurement['limb_motion'],
        'static_limbs': audit.static_limbs(measurement),
        'ground_contact_correction': {
            'bone': 'Rot (y)',
            'reference': 'lower of ToeL/ToeR world height',
            'recipient_idle_contact': round(contact_r_idle, 4),
            'donor_idle_contact': round(contact_d_idle, 4),
            'min': round(min(corrections), 4),
            'max': round(max(corrections), 4),
            'max_step': round(max(abs(b - a) for a, b in zip(corrections, corrections[1:])), 4)
            if len(corrections) > 1 else 0.0,
        },
        'recipient_skeleton_sha256': sha(skel_path),
        'recipient_idle_sha256': sha(idle_path),
        'donor_idle_sha256': sha(DONOR_IDLE),
        'donor_skeleton_sha256': sha(DONOR_SKEL),
        'acmd_sha256': sha(ACMD),
    }


def patch_motion_list(kind: str, motion_list_path: Path) -> dict:
    """Replace one entry with the donor's own bytes, proving the delta is tiny.

    The whole donor entry is copied rather than field by field, because only the
    donor's bytes reproduce an entry exactly. The result is then compared against
    the previous bytes so the size, and the set of differing offsets, are
    measurements rather than claims.
    """
    donor = donor_entry(kind)
    path = Path(motion_list_path)
    before = path.read_bytes()
    # The patched bytes are written back here, not merely returned. Measured
    # 2026-10-03: an earlier revision of this function returned `after` in the
    # report and never persisted it, so the JSON said "cancel 296->300, 2 bytes
    # differ" while the staged file stayed byte-identical to the baseline. A
    # report that outruns the artefact is worse than no report, so the write is
    # here and the caller's assertions below read the file back from disk.
    assert path.is_file(), f'{path}: patch_motion_list needs a real file to patch'
    ml = mlist.parse(path)
    if mlist.encode(ml) != before:
        raise RuntimeError(f'{path}: motion list does not round-trip')
    target = mlist.find(ml, kind)
    old = bytes(target['raw'])
    if len(old) != len(donor['raw']):
        raise RuntimeError(
            f'{path}: {kind} entry is {len(old)} bytes, donor is {len(donor["raw"])}; '
            f'the list cannot be patched in place')
    entry = mlist.find(ml, kind)
    entry['raw'] = donor['raw']
    after = mlist.encode(ml)
    reread = mlist.parse_bytes(after)
    if mlist.encode(reread) != after:
        raise RuntimeError(f'{path}: patched list does not round-trip')
    new_entry = mlist.find(reread, kind)
    if bytes(new_entry['raw']) != bytes(donor['raw']):
        raise RuntimeError(f'{path}: patched entry does not read back as the donor entry')
    path.write_bytes(after)
    if hashlib.sha256(path.read_bytes()).hexdigest() != \
            hashlib.sha256(after).hexdigest():
        raise RuntimeError(f'{path}: the patched bytes did not survive the write')
    diffs = mlist.diff_offsets(old, bytes(donor['raw']))
    baseline_entry = mlist.find(mlist.parse_bytes(before), kind)
    return {
        'kind': kind,
        'path': str(path),
        'file_bytes_before': len(before),
        'file_bytes_after': len(after),
        'entry_bytes': len(old),
        'entry_bytes_preserved': len(old) == len(donor['raw']),
        'differing_offsets': diffs,
        'differing_bytes': len(diffs),
        'cancel_before': baseline_entry['cancel'],
        'cancel_after': new_entry['cancel'],
        'flags_before': f'0x{baseline_entry["flags"]:04x}',
        'flags_after': f'0x{new_entry["flags"]:04x}',
        'blend_after': new_entry['blend'],
        'anims_after': [f'0x{a:x}' for a in new_entry['anims']],
        'output_sha256': hashlib.sha256(after).hexdigest(),
        '_bytes': after,
    }


def deploy_for_slot(slot: str, out_dir: Path, recipient_body: Path) -> dict:
    """Write both clips and both motion entries for one slot."""
    model_dir = recipient_body / 'model/body' / slot
    motion_dir = recipient_body / 'motion/body' / slot
    idle = motion_dir / 'a00wait1.nuanmb'
    stage = Path(out_dir) / slot
    stage.mkdir(parents=True, exist_ok=True)

    report = {'slot': slot, 'clips': {}, 'motion': {}}
    for kind, clip_name in CLIPS.items():
        report['clips'][clip_name] = retarget(
            kind, model_dir, stage / clip_name, idle)
    # The motion lists are patched in a copy of the recipient's own file, never
    # in the shared tree: another agent is editing live sources.
    for kind in (audit.KIND, audit.LANDING_KIND):
        src = motion_dir / 'motion_list.bin'
        staged = stage / 'motion_list.bin'
        if kind == audit.KIND:
            staged.write_bytes(src.read_bytes())
        rec = patch_motion_list(kind, staged)
        rec.pop('_bytes')
        rec['baseline_sha256'] = sha(src)
        report['motion'][kind] = rec
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipient', type=Path, default=DEFAULT_RECIPIENT,
                        help='fighter/eflame directory of the built recipient tree')
    parser.add_argument('--out', type=Path, help='directory to stage the slot outputs into')
    parser.add_argument('--report', type=Path, help='write the JSON report here')
    args = parser.parse_args()

    if not args.recipient.is_dir():
        raise SystemExit(f'recipient tree not found: {args.recipient}')
    audit.check_pins()

    for kind in (audit.KIND, audit.LANDING_KIND):
        e = donor_entry(kind)
        print(f'donor {kind}: cancel {e["cancel"]} flags {e["flags"]:#06x} '
              f'game_script {e["gs"]:#x} anims {[hex(a) for a in e["anims"]]}')

    if not args.out:
        print('(pass --out to retarget against a built recipient)')
        return
    out = args.out.resolve()
    if not any(out.is_relative_to(ROOT / name) for name in ('scratch', 'builds')):
        raise SystemExit('--out must be under builds/ or scratch/')

    report = {'tool_version': '1.0.0', 'date': '2026-10-03', 'evidence_tier': 'B',
              'hardware_validated': False, 'recipient': str(args.recipient), 'slots': {}}
    for slot in ('c06', 'c07'):
        report['slots'][slot] = deploy_for_slot(slot, out, args.recipient)
        for clip, rec in report['slots'][slot]['clips'].items():
            print(f'{slot} {clip}: kept {rec["bones_kept"]}/{rec["transform_nodes"]} bones, '
                  f'dropped {len(rec["bones_dropped"])}, vis {rec["vis_nodes"]}, '
                  f'sha256 {rec["output_sha256"][:16]}')
        for kind, rec in report['slots'][slot]['motion'].items():
            print(f'{slot} {kind}: cancel {rec["cancel_before"]}->{rec["cancel_after"]} '
                  f'flags {rec["flags_before"]}->{rec["flags_after"]}, '
                  f'{rec["differing_bytes"]} differing byte(s) '
                  f'at offsets {rec["differing_offsets"]}')
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('build_pikachu_airb OK')


if __name__ == '__main__':
    main()