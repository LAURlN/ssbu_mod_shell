"""Retarget Ness's back throw onto Mythra c06/c07 and write the motion-list byte.

Donor: Ness (`ness`), `fighter/ness/motion/body/c00/e01throwb.nuanmb` plus his
own `throw_b` motion-list entry. Both extracted read-only from the local 13.0.4
`data.arc` with the workspace tool `tools/arc-extract`; hashes pinned below and
re-checked on every run.
Recipient: Mythra c06/c07 (`elight`), the costume-gated body this crate targets.

Why this is smaller than every other move port in this project
--------------------------------------------------------------
Measured by `tools/audit_ness_throw_b.py` and re-asserted here on every run:

* the donor's and recipient's `throw_b` **entries are byte-identical except
  offset 62**, the cancel frame - Ness `53`, Mythra `36`;
* they name the **same clip file**, `e01throwb.nuanmb`, so no alias is consumed,
  no spare name is taken and no `new-dir-files` entry is needed. That is the
  opposite of Snake's up tilt (T-0043), where the donor clip name did not exist
  on the recipient;
* the donor clip's Transform group has 68 nodes and **66 of them exist exactly**
  on Mythra's c06 skeleton. The two that do not are `Bat` and `BatL` - Ness's
  baseball bat, which has no counterpart on Mythra and is dropped rather than
  remapped;
* no case-only matches, so nothing is silently renamed.

So the whole asset delta is: one `.nuanmb` per slot, and one byte per slot in
`motion_list.bin`.

What is deliberately not here
----------------------------
No bone remapping inside the ACMD module, and no edit to the other three throws.
`throw_f`, `throw_hi`, `throw_lw` and `thrown_b` are asserted byte-identical
before and after, because "preserve other throws" is a check, not an intention.
The Luigi down throw already shipped on these costumes and must not move.

Unverified: how the throw looks, hits or launches on hardware. Everything this
tool establishes is tier B (offline, byte-checkable); runtime is tier D.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import sys

import ssbh_data_py as s

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]

KIND = 'throw_b'
DONOR_CLIP = 'e01throwb.nuanmb'
# Read from the pinned motion_list.bin on 2026-10-02 (refs/ness_throw_b/).
EXPECTED_CANCEL = 53
RECIPIENT_CANCEL = 36
EXPECTED_FLAGS = 0x0081
# The only cancel-frame byte offset inside a 28-byte entry whose header+anim is
# 24 + 8 + 8 padding = 40... measured, and re-derived in assert_single_byte_delta.
EXPECTED_DIFF_OFFSET = 62
# Bones whose absence from the survivor set means the retarget left a limb in
# rest pose - the failure the user rejected on the R.O.B. down tilt (handbook/04).
REQUIRED_MOVING = ('ArmL', 'ArmR', 'Bust', 'HandL', 'HandR', 'Hip', 'LegL', 'LegR',
                   'ShoulderL', 'ShoulderR', 'Throw', 'Waist')
# Ness's bat. Mythra has no `Bat`/`BatL`, so these are dropped, not remapped.
EXPECTED_DROPPED = ('Bat', 'BatL')

PINS = {
    'donor_clip': ('376d65d66708585911a91cc8132c8354fd5ce754e2b079752972ecfae1c52d52',
                   50488, 'fighter/ness/motion/body/c00/e01throwb.nuanmb'),
    'donor_motion_list': ('7a6b50663683e12b6192b77133bc4c7a2169986a2f8b015f238321f3a887a514',
                          43008, 'fighter/ness/motion/body/c00/motion_list.bin'),
    'recipient_motion_list': ('0b091450a00bdb2b382c59e965997f96d2a387dd2581d7d492183dd69d56c2f7',
                              43712, 'fighter/elight/motion/body/c06/motion_list.bin'),
}

sys.path.insert(0, str(TOOLS))
import mlist  # noqa: E402
from mlist import parse, encode, hash40  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _pinned(key, arc_root=None):
    """Read a pinned ARC input, from the extracted tree when it is present.

    `paths.toml` points `dumps.arc` at an external export that is nearly empty in
    this checkout, so the authoritative copy is the one `tools/arc-extract` pulled
    from the local 13.0.4 `data.arc` into the workspace `gamedata/` tree. Both
    locations are accepted; the hash is what decides.
    """
    digest, size, arc_path = PINS[key]
    candidates = []
    if arc_root:
        candidates.append(Path(arc_root) / arc_path)
    candidates.append(Path(ROOT).parents[1] / 'gamedata/ssbu-13.0.4/files' / arc_path)
    for path in candidates:
        if path.is_file() and path.stat().st_size == size and sha(path) == digest:
            return path
    raise RuntimeError(
        f'{key}: no copy of {arc_path} at the pinned sha256 {digest} ({size} B).\n'
        f'  looked in: ' + '\n           '.join(str(c) for c in candidates) + '\n'
        f'  re-pull with: tools/arc-extract/target/release/arc-extract.exe '
        f'--arc gamedata/ssbu-13.0.4/data.arc --out gamedata/ssbu-13.0.4/files {arc_path}')


def _angle_between(q, r):
    """Degrees between two SSBH xyzw rotations, sign-insensitive."""
    a = [float(x) for x in q.rotation]
    b = [float(x) for x in r.rotation]
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    dot = abs(sum(x / na * y / nb for x, y in zip(a, b)))
    return math.degrees(2.0 * math.acos(min(1.0, dot)))


def donor_entry(arc_root=None):
    """Ness's own raw `throw_b` entry, whole, with the pinned reading asserted."""
    path = _pinned('donor_motion_list', arc_root)
    ml = parse(path)
    entry = next(e for e in ml['entries'] if e['kind'] == hash40(KIND))
    assert entry['cancel'] == EXPECTED_CANCEL, entry['cancel']
    assert entry['flags'] == EXPECTED_FLAGS, hex(entry['flags'])
    assert entry['anims'] == (hash40(DONOR_CLIP),), [hex(a) for a in entry['anims']]
    assert entry['gs'] == hash40('game_throwb'), hex(entry['gs'])
    return entry


def assert_single_byte_delta(donor_raw, recipient_raw):
    """The claim this whole port rests on, re-measured instead of trusted.

    If the donor and recipient entries ever diverge in more than the cancel frame,
    the motion-list delta stops being a one-byte patch and the port would need
    donor fields this tool does not copy. Fail loudly rather than ship a partial.
    """
    assert len(donor_raw) == len(recipient_raw), (len(donor_raw), len(recipient_raw))
    diff = [i for i in range(len(donor_raw)) if donor_raw[i] != recipient_raw[i]]
    assert diff == [EXPECTED_DIFF_OFFSET], f'unexpected entry differences at {diff}'
    return {'offset': diff[0], 'donor': donor_raw[diff[0]], 'recipient': recipient_raw[diff[0]]}


def bone_motion(tracks, idle_values, names):
    """Largest rotation/translation each named bone reaches against the idle.

    "Moved" means rotation **or** translation (handbook/04, Snake up tilt:
    `ToeL`/`ToeR` translate with no rotation of their own). A survivor count
    alone cannot see a limb left in rest pose, which is what the user rejected.
    """
    result = {}
    for name in names:
        values = tracks.get(name)
        base = idle_values.get(name)
        if values is None or base is None:
            result[name] = {'present': values is not None, 'idle_base': base is not None,
                            'max_rotation_deg': None, 'max_translation': None, 'moved': False}
            continue
        rotation = max(_angle_between(v, base) for v in values)
        translation = max(max(abs(float(x) - float(y))
                              for x, y in zip(v.translation, base.translation))
                          for v in values)
        result[name] = {'present': True, 'idle_base': True,
                        'max_rotation_deg': round(rotation, 2),
                        'max_translation': round(translation, 4),
                        'moved': bool(rotation > 1.0 or translation > 0.05)}
    return result


def retarget(model_dir, out_path, idle_path=None, arc_root=None):
    """Write the donor's throw clip onto the recipient's own `e01throwb.nuanmb`.

    `model_dir` must be the **built** recipient model, because the model this
    crate ships is Mythra's with pgwr's grafts; filtering against the raw ARC
    skeleton would drop bones the shipped body has. Same rule as the jab, the
    down tilt, the forward smash and Snake's up tilt.
    """
    src = _pinned('donor_clip', arc_root)
    model_path = Path(model_dir) / 'model.nusktb'
    skel = s.skel_data.read_skel(str(model_path))
    exact = {b.name for b in skel.bones}
    folded = {b.name.lower(): b.name for b in skel.bones}

    idle_path = Path(idle_path) if idle_path else Path(out_path).parent / 'a00wait1.nuanmb'
    if not idle_path.is_file():
        raise RuntimeError(f'Need the recipient idle (no guessed visibility): {idle_path}')
    idle = s.anim_data.read_anim(str(idle_path))
    idle_vis = next(g for g in idle.groups if g.group_type.name == 'Visibility')
    idle_values = {n.name: n.tracks[0].values[0] for g in idle.groups
                   if g.group_type.name == 'Transform' for n in g.nodes}

    donor = s.anim_data.read_anim(str(src))
    transform = next(g for g in donor.groups if g.group_type.name == 'Transform')
    donor_nodes = len(transform.nodes)
    kept, dropped, case_only = [], [], []
    for node in transform.nodes:
        if node.name in exact:
            kept.append(node)
        elif node.name.lower() in folded:
            case_only.append((node.name, folded[node.name.lower()]))
        else:
            dropped.append(node.name)
    if not kept:
        raise RuntimeError(f'{DONOR_CLIP}: no transform node survived the filter')
    transform.nodes = kept

    # The donor's own Visibility and Material groups name Ness's face/hat/psi
    # meshes. The recipient's own idle visibility is replicated instead, so the
    # swap keeps her costume's mesh states; donor Material groups have no
    # counterpart here and are dropped rather than guessed at.
    vis_nodes = [s.anim_data.NodeData(node.name, [s.anim_data.TrackData(
        'Visibility', values=[node.tracks[0].values[0]])]) for node in idle_vis.nodes]
    donor_material = [g for g in donor.groups if g.group_type.name == 'Material']
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
    static = sorted(set(dropped) | set(case_only and [c[0] for c in case_only]))
    motion = bone_motion(tracks, idle_values, REQUIRED_MOVING)
    return {
        'donor_clip_sha256': sha(src),
        'recipient_skeleton_sha256': sha(model_path),
        'recipient_skeleton_bones': len(skel.bones),
        'recipient_idle_sha256': sha(idle_path),
        'final_frame_index': donor.final_frame_index,
        'donor_transform_nodes': donor_nodes,
        'transform_nodes': len(transform.nodes),
        'bones_kept': len(kept),
        'bones_dropped': sorted(dropped),
        'case_only': case_only,
        'vis_nodes': len(vis_nodes),
        'material_groups_dropped': len(donor_material),
        'frames': frames,
        'sha256': sha(out_path),
        'required_bone_motion': motion,
        'required_bones_all_moving': all(v['moved'] for v in motion.values()),
        'unmapped_bones': static,
        'game_behavior': 'unverified; needs console review',
    }


def patch_motion_list(list_path, donor_raw, delta):
    """Write the donor's cancel frame into the recipient's `throw_b` entry.

    Only the one byte moves. Every other entry is re-encoded and compared against
    the input byte for byte, and the result is re-parsed, so "the other throws are
    untouched" is checked on this file rather than asserted about it.
    """
    path = Path(list_path)
    original = path.read_bytes()
    ml = parse(path)
    assert encode(ml) == original, f'{path}: parser is not byte-faithful'
    before = {}
    for entry in ml['entries']:
        before[entry['kind']] = entry['raw']

    target = next(e for e in ml['entries'] if e['kind'] == hash40(KIND))
    if target['raw'] == donor_raw:
        return path, False, None
    assert_single_byte_delta(donor_raw, target['raw'])
    raw = bytearray(target['raw'])
    raw[delta['offset']] = donor_raw[delta['offset']]
    target['raw'] = bytes(raw)
    data = encode(ml)

    # Control: every non-target entry must be unchanged, byte for byte.
    reread = parse_data(data)
    for entry in reread:
        if entry['kind'] == hash40(KIND):
            assert entry['raw'] == bytes(raw)
        else:
            assert entry['raw'] == before[entry['kind']], \
                f'an unrelated motion entry changed: {entry["kind"]:#x}'
    path.write_bytes(data)
    return path, True, delta


def parse_data(data):
    """Re-parse an in-memory list through the same byte-faithful reader."""
    return mlist.reread(data)


def deploy(slot, out_dir, model_body=None, arc_root=None, idle_path=None, report_dir=None):
    """Write one slot's clip and one slot's motion-list byte."""
    out_dir = Path(out_dir)
    model_body = Path(model_body) if model_body else out_dir.parent / 'model/body' / slot
    donor = donor_entry(arc_root)
    clip_report = retarget(model_body, out_dir / DONOR_CLIP, idle_path=idle_path, arc_root=arc_root)
    if clip_report['case_only']:
        raise RuntimeError(f'{slot}: nodes matched only case-insensitively: '
                           f'{clip_report["case_only"]}')
    if sorted(clip_report['bones_dropped']) != sorted(EXPECTED_DROPPED):
        raise RuntimeError(f'{slot}: dropped set is {clip_report["bones_dropped"]}, '
                           f'expected exactly {list(EXPECTED_DROPPED)}')
    if not clip_report['required_bones_all_moving']:
        dead = {k: v for k, v in clip_report['required_bone_motion'].items() if not v['moved']}
        raise RuntimeError(f'{slot}: required bones are static after retarget: {dead}')
    return {DONOR_CLIP: clip_report,
            'motion_entry': {'kind': hash40(KIND), 'donor_cancel': EXPECTED_CANCEL,
                             'recipient_cancel': RECIPIENT_CANCEL, 'flags': EXPECTED_FLAGS}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arc-root', type=Path,
                        help='tree holding the pinned ARC inputs (default: workspace gamedata)')
    parser.add_argument('--model-body', type=Path,
                        help='built recipient model/body/<slot> directory')
    parser.add_argument('--out', type=Path, help='recipient motion/body/<slot> directory')
    parser.add_argument('--idle', type=Path,
                        help='recipient a00wait1.nuanmb. Mythra c06/c07 does not ship a '
                             'body idle in the package, so this points at the ARC copy.')
    parser.add_argument('--motion-list', type=Path, help='recipient motion_list.bin to patch in place')
    parser.add_argument('--report', type=Path, help='write the JSON report here')
    parser.add_argument('--check', action='store_true',
                        help='verify the pins and the one-byte delta; write nothing')
    args = parser.parse_args()

    donor = donor_entry(args.arc_root)
    print(f'Ness {KIND}: cancel {donor["cancel"]}, flags {donor["flags"]:#x}, '
          f'game_script {donor["gs"]:#x}, anims {[hex(a) for a in donor["anims"]]}')

    if args.check:
        recipient = _pinned('recipient_motion_list', args.arc_root)
        entry = next(e for e in parse(recipient)['entries'] if e['kind'] == hash40(KIND))
        delta = assert_single_byte_delta(donor['raw'], entry['raw'])
        print(f'PASS: pins verified; entry differs only at offset {delta["offset"]} '
              f'(cancel {delta["recipient"]} -> {delta["donor"]})')
        return

    if not (args.model_body and args.out):
        parser.error('pass --check, or --model-body and --out')
    report = deploy(args.out.name, args.out, args.model_body, args.arc_root, args.idle)
    if args.motion_list:
        patched, changed, delta = patch_motion_list(args.motion_list, donor['raw'],
                                                     {'offset': EXPECTED_DIFF_OFFSET})
        report['motion_list'] = {'path': str(patched), 'changed': changed,
                                 'sha256': sha(patched), 'delta': delta}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    clip = report[DONOR_CLIP]
    print(f'retarget: {clip["bones_kept"]}/{clip["donor_transform_nodes"]} donor nodes kept, '
          f'{clip["vis_nodes"]} visibility nodes, frames {clip["frames"]}, '
          f'sha256 {clip["sha256"]}')
    print(f'dropped (not on the recipient): {clip["bones_dropped"]}')
    print(f'required bones all moving: {clip["required_bones_all_moving"]}')
    for name, value in clip['required_bone_motion'].items():
        print(f'  {name:10s} rot={value["max_rotation_deg"]:8} deg  '
              f'trans={value["max_translation"]}')
    if 'motion_list' in report:
        print(f'motion list: {report["motion_list"]["path"]} '
              f'sha256 {report["motion_list"]["sha256"]}')


if __name__ == '__main__':
    main()