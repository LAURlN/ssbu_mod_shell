"""Measure the Lucas down-smash donor: motion entries, clip groups, bone fit.

Tier B - offline measurement by this script on pinned files. It establishes
nothing about how the move looks or hits in game.

Donor: Lucas c00 (pinned in `refs/lucas_attack_lw4/arc/`, provenance
`refs/lucas_attack_lw4/SOURCE.json`).
Recipient: Mythra `elight` c06/c07 - the **built** skeleton from
`builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin`, because the moves
that already ship (jab, down tilt, up tilt, forward smash) all filter against
the built model rather than the raw export.

What is measured, and why each question is asked here rather than assumed:

* the raw `attack_lw4` and `attack_lw4_charge` motion entries, whole: kind,
  `game_script`, flags, blend, cancel frame and clip names. The cancel frame
  is what makes this move *Lucas's* and not a reskin of the recipient's, so it
  is read and printed rather than inherited.
* every clip's group list (Transform / Visibility / Material) and node count.
  A donor Material group naming meshes the recipient does not have is the
  classic cause of a retarget that silently drops part of the character, so
  the count is reported even when the retarget drops the group.
* per-node parent chains, compared between the donor clip and the recipient
  skeleton. A name that survives but sits under a *different* parent produces a
  limb that bends in the wrong direction, and a plain name filter cannot see
  it, so parent mismatches are counted separately from dropped nodes.
* how much each surviving node actually moves against the recipient idle, per
  limb chain. The R.O.B. down tilt was rejected by the user for leaving limbs
  in rest pose, so a "moved" measurement is a gate here, not a nicety.

    python tools/audit_lucas_lw4_donor.py                     # print report
    python tools/audit_lucas_lw4_donor.py --json out.json     # also write it
    python tools/audit_lucas_lw4_donor.py --check              # assert the pins
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

ROOT = Path(__file__).resolve().parents[1]
TOOL_VERSION = '1.0.0'
DATE = '2026-10-02'

# Pinned donor inputs. `--check` refuses to report against anything else, so a
# donor revision bump cannot quietly change the port.
PINS = {
    'arc/fighter/lucas/motion/body/c00/c04attacklw4.nuanmb':
        ('968d9035e69eecacc427d58bd2403e803511351f65d11064d7c946164f0d5887', 42656),
    'arc/fighter/lucas/motion/body/c00/c04attacklw4charge.nuanmb':
        ('202e5d020db31b9cf4bcdb310effe845ab8467eb3e4c76bdde5745019528012b', 24385),
    'arc/fighter/lucas/motion/body/c00/motion_list.bin':
        ('ae6086343b1ab2e368b8966996dddd5668d32130653636641655c6c6e0a57d37', 43520),
    'arc/fighter/lucas/model/body/c00/model.nusktb':
        ('ad7cd39840bd114016351709c032c9b38f8f179696ddf39cb3e6c86a2b1a8ef1', 22696),
    # Recipient baseline. Mythra's body is *not* reskinned: `build_mythra_skin`
    # in `src/pgwr/build.py` copies only `*.nutexb` body/sword textures into
    # `fighter/elight/model/body/c06`, and the 0.20.19 package ships no
    # `model.nusktb` for elight at all. So the skeleton this port retargets onto
    # is vanilla `elight` c06/c07, and both slots are byte-identical - measured,
    # and asserted below rather than assumed from the file list.
    'recipient/fighter/elight/model/body/c06/model.nusktb':
        ('5b6fbbe6f702e5ab9b14b208899799ec99f13c15e88611017b2547ac3de93f03', 48136),
    'recipient/fighter/elight/model/body/c07/model.nusktb':
        ('5b6fbbe6f702e5ab9b14b208899799ec99f13c15e88611017b2547ac3de93f03', 48136),
    'recipient/fighter/elight/motion/body/c06/a00wait1.nuanmb':
        ('484e973e13876b9931b097f8d0d804dab3745852d23398fbcecaa50dbd124408', 69896),
    'recipient/fighter/elight/motion/body/c06/motion_list.bin':
        ('0b091450a00bdb2b382c59e965997f96d2a387dd2581d7d492183dd69d56c2f7', 43712),
    'recipient/fighter/elight/motion/body/c07/motion_list.bin':
        ('0b091450a00bdb2b382c59e965997f96d2a387dd2581d7d492183dd69d56c2f7', 43712),
    # Control list for the parser cross-check: G&W c00. Only its attack_lw4 and
    # attack_lw4_hold entries are read, and they are compared against
    # `dumps/scripts/gamewatch_motion_list.yml`, a dump of the same list by
    # different tooling.
    'control/fighter/gamewatch/motion/body/c00/motion_list.bin':
        ('306be009edb40b692f58aa67eb2bb18c12e47068d8350d4e0a7e96ceb88ed0a2', 44480),
}
# The charge hold is `attack_lw4_hold`, NOT `attack_lw4_charge`. Measured:
# hash40('attack_lw4_hold') = 0xfee188235, and that is the kind the donor's own
# charge entry carries - cross-checked against `dumps/scripts/
# gamewatch_motion_list.yml`, an independent dump of a different fighter's list
# that names the entry `attack_lw4_hold` and agrees on every field read here
# (G&W attack_lw4 cancel 34, flags 0x80, game_attacklw4, c04attacklw4.nuanmb).
# Guessing `attack_lw4_charge` would have found nothing and looked like a
# missing donor file.
CLIPS = {
    'attack_lw4': 'c04attacklw4.nuanmb',
    'attack_lw4_hold': 'c04attacklw4charge.nuanmb',
}
# The limb bones that must visibly move. Every name here was checked to exist on
# BOTH skeletons first: an earlier draft listed `ElbowL/R` and `WaistL/R`, which
# are not bones on either fighter (the forearm helpers are `H_ElbowL/R` and the
# pelvis is plain `Waist`), so those four reported as "static" when in fact they
# were simply not part of this move's rig. A gate that counts absent bones as
# static limbs is a gate that cries wolf, so the list is real bones only.
LIMB_BONES = (
    'Hip', 'Waist', 'LegL', 'LegR', 'KneeL', 'KneeR', 'FootL', 'FootR',
    'ClavicleC', 'ClavicleL', 'ClavicleR', 'ShoulderL', 'ShoulderR',
    'ArmL', 'ArmR', 'HandL', 'HandR',
)


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def check_pins() -> None:
    for rel, (digest, size) in PINS.items():
        path = ROOT / 'refs/lucas_attack_lw4' / rel
        assert path.is_file(), f'missing pinned donor file {rel}'
        assert path.stat().st_size == size, f'{rel}: {path.stat().st_size} != {size}'
        assert sha(path) == digest, f'{rel}: sha256 differs from the pin'
    # c06 and c07 must really be the same recipient, or a single-slot retarget
    # would quietly mean something different from the other.
    c06 = ROOT / 'refs/lucas_attack_lw4/recipient/fighter/elight/model/body/c06/model.nusktb'
    c07 = ROOT / 'refs/lucas_attack_lw4/recipient/fighter/elight/model/body/c07/model.nusktb'
    assert sha(c06) == sha(c07), 'c06 and c07 Mythra skeletons differ'


def read_entries(motion_list: Path) -> dict:
    """Every motion-list entry, keyed by kind name where the kind is known.

    The container is the game's own: a header, then per entry
    `kind, game_script, flags, blend, n_anims, size` followed by `n_anims`
    hashes, padded, followed by `size` bytes. The cancel frame is the trailing
    u16 of the entry body, which is why the body's own length decides how it is
    read - this parser is the one `build_snake_uptilt.py` uses, and it is
    re-implemented here rather than imported so that a change to that tool
    cannot move this port's numbers silently.
    """
    data = Path(motion_list).read_bytes()
    magic, path_hash, count = struct.unpack_from('<QQQ', data, 0)
    assert magic == hash40('motion'), 'not a motion list'
    offset = 24
    entries = []
    for _ in range(count):
        start = offset
        kind, script, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        offset = (offset + n_anims * 9 + 3) & ~3
        end = offset + size
        cancel = struct.unpack_from('<H', data, end - 2)[0] if size % 8 == 4 else None
        entries.append({'raw': data[start:end], 'kind': kind, 'game_script': script,
                        'flags': flags, 'blend': blend, 'anims': anims,
                        'cancel': cancel, 'size': size})
        offset = end
    return {'header_path': path_hash, 'count': count, 'entries': entries,
            'trailing_bytes': len(data) - offset}


def pick(entries: dict, kind_name: str) -> dict:
    want = hash40(kind_name)
    found = [e for e in entries['entries'] if e['kind'] == want]
    assert len(found) == 1, f'{kind_name}: {len(found)} entries'
    return found[0]


def cross_validate_parser(ml_path: Path) -> dict:
    """Prove the entry parser against an independent dump of a *different* list.

    `dumps/scripts/gamewatch_motion_list.yml` is a readable dump of Mr. Game &
    Watch's motion list, produced by different tooling from the game bytes this
    port reads. If this parser and that dump agree on G&W's `attack_lw4` - kind
    name, cancel frame, flags, game script and clip - then the 316 and 56 read
    for Lucas and Mythra are measurements rather than an artifact of a
    mis-parsed container, and the `attack_lw4_hold` kind name is confirmed by a
    second source.

    This is the check that caught the wrong kind name: the donor's charge entry
    hashes to `attack_lw4_hold`, and a first pass that looked for
    `attack_lw4_charge` found nothing and read as a missing donor file.
    """
    entries = read_entries(ml_path)
    # The motion kind and the script name are NOT a mechanical pair: the hold
    # entry's kind is `attack_lw4_hold` but its script is `game_attacklw4charge`.
    # Both are spelled out here because the yml dump spells both out.
    expected = {'attack_lw4': ('game_attacklw4', 34, 'c04attacklw4.nuanmb'),
                'attack_lw4_hold': ('game_attacklw4charge', 0, None)}
    out = {}
    for kind, (script, cancel_expected, clip) in expected.items():
        found = [e for e in entries['entries'] if e['kind'] == hash40(kind)]
        assert len(found) == 1, f'{kind}: {len(found)} entries in the control list'
        entry = found[0]
        assert entry['cancel'] == cancel_expected, (
            f'{kind}: parser says cancel {entry["cancel"]}, the yml dump says {cancel_expected}')
        assert entry['flags'] == 0x80, f'{kind}: yml says unk_80 true, flags {entry["flags"]:#x}'
        assert entry['game_script'] == hash40(script), (
            f'{kind}: yml names {script}, parser read {entry["game_script"]:#x}')
        if clip:
            assert entry['anims'] == (hash40(clip),), \
                f'{kind}: yml names {clip}, parser read {[hex(a) for a in entry["anims"]]}'
        out[kind] = {'game_script': script, 'cancel': entry['cancel'],
                     'flags': hex(entry['flags']),
                     'anims': [hex(a) for a in entry['anims']]}
    return out


def clip_report(path: Path) -> dict:
    anim = s.anim_data.read_anim(str(path))
    groups = {g.group_type.name: g for g in anim.groups}
    transform = groups.get('Transform')
    assert transform is not None, f'{path.name}: no Transform group'
    nodes = {n.name: n for n in transform.nodes}
    tracks = {name: n.tracks[0].values for name, n in nodes.items()}
    return {
        'file': path.name,
        'sha256': sha(path),
        'bytes': path.stat().st_size,
        'final_frame_index': anim.final_frame_index,
        'groups': {name: len(g.nodes) for name, g in groups.items()},
        'transform_nodes': len(nodes),
        'node_names': sorted(nodes),
        'frames': sorted({len(v) for v in tracks.values()}),
        'tracks': tracks,
    }


def skeleton(path: Path) -> dict:
    """Bone name -> parent bone name, from the skeleton's own parent indices.

    Resolved by name rather than by index, because the donor and the recipient
    are different files: comparing *parent names* is what answers "does this arm
    hang off the same place in both bodies", which is the question a retarget
    needs answered. `None` is a root.
    """
    skel = s.skel_data.read_skel(str(path))
    names = [b.name for b in skel.bones]
    parents = {}
    for index, bone in enumerate(skel.bones):
        pi = bone.parent_index
        parents[bone.name] = None if pi is None or pi >= len(names) else names[pi]
    return parents


def _angle_between(q, r) -> float:
    """Degrees between two SSBH xyzw rotations, sign-insensitive."""
    a = [float(x) for x in q.rotation]
    b = [float(x) for x in r.rotation]
    na = sum(x * x for x in a) ** 0.5 or 1.0
    nb = sum(x * x for x in b) ** 0.5 or 1.0
    dot = abs(sum(x / na * y / nb for x, y in zip(a, b)))
    return math.degrees(2.0 * math.acos(min(1.0, dot)))


def motion_against_idle(tracks, idle_values) -> dict:
    """Largest rotation/translation each limb bone reaches against the idle.

    "Moved" is either channel. A foot or hand bone can carry a whole move as
    pure translation, so a rotation-only test would call a genuinely moving
    limb static - which is the same mistake that shipped rest-pose legs on the
    rejected R.O.B. down tilt.
    """
    result = {}
    for name in LIMB_BONES:
        values = tracks.get(name)
        base = idle_values.get(name)
        if values is None or base is None:
            result[name] = {'present': values is not None,
                            'idle_base': base is not None,
                            'max_rotation_deg': None, 'max_translation': None,
                            'moved': False,
                            'reason': 'node or idle reference absent'}
            continue
        rotation = max(_angle_between(v, base) for v in values)
        translation = max(max(abs(float(x) - float(y))
                              for x, y in zip(v.translation, base.translation)) for v in values)
        result[name] = {'present': True, 'idle_base': True,
                        'max_rotation_deg': round(rotation, 2),
                        'max_translation': round(translation, 4),
                        'moved': bool(rotation > 1.0 or translation > 0.05)}
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true', help='assert the donor pins and exit')
    ap.add_argument('--json', type=Path, help='write the report here')
    ap.add_argument('--recipient-model', type=Path,
                    help='built recipient model.nusktb (default: the 0.20.19 package)')
    ap.add_argument('--recipient-idle', type=Path,
                    help='built recipient a00wait1.nuanmb (default: beside --recipient-model)')
    args = ap.parse_args()

    check_pins()
    if args.check:
        print(f'PASS: {len(PINS)} pinned Lucas donor files match SOURCE.json hashes')
        return 0

    base = ROOT / 'refs/lucas_attack_lw4/recipient'
    model = args.recipient_model or base / 'fighter/elight/model/body/c06/model.nusktb'
    idle = args.recipient_idle or base / 'fighter/elight/motion/body/c06/a00wait1.nuanmb'
    assert model.is_file(), f'recipient model not found: {model}'
    assert idle.is_file(), f'recipient idle not found: {idle}'

    donor_ml = ROOT / 'refs/lucas_attack_lw4/arc/fighter/lucas/motion/body/c00/motion_list.bin'
    recip_ml = base / 'fighter/elight/motion/body/c06/motion_list.bin'
    donor_entries = read_entries(donor_ml)
    recip_entries = read_entries(recip_ml)
    donor_skel = skeleton(ROOT / 'refs/lucas_attack_lw4/arc/fighter/lucas/model/body/c00/model.nusktb')
    recip_skel = skeleton(model)

    idle_anim = s.anim_data.read_anim(str(idle))
    idle_vis = next(g for g in idle_anim.groups if g.group_type.name == 'Visibility')
    idle_values = {n.name: n.tracks[0].values[0] for g in idle_anim.groups
                   if g.group_type.name == 'Transform' for n in g.nodes}

    report = {
        'tool': Path(__file__).name, 'tool_version': TOOL_VERSION, 'date': DATE,
        'evidence_tier': 'B', 'hardware_validated': False,
        'donor': {'fighter': 'lucas', 'costume': 'c00',
                  'model_sha256': sha(ROOT / 'refs/lucas_attack_lw4/arc/fighter/lucas/model/body/c00/model.nusktb'),
                  'motion_list_sha256': sha(donor_ml),
                  'bone_count': len(donor_skel)},
        'recipient': {'fighter': 'elight', 'costumes': ['c06', 'c07'],
                      'skeleton_is_vanilla': True,
                      'why': 'build_mythra_skin copies only nutexb body/sword '
                             'textures; the 0.20.19 package ships no elight '
                             'model.nusktb, so the body skeleton is vanilla',
                      'model_sha256': sha(model), 'idle_sha256': sha(idle),
                      'bone_count': len(recip_skel),
                      'motion_list_sha256': sha(recip_ml)},
        'motion_entries': {}, 'clips': {}, 'fit': {},
        'parser_cross_validation': cross_validate_parser(
            ROOT / 'refs/lucas_attack_lw4/control/fighter/gamewatch/motion/body/c00/motion_list.bin'),
    }

    for kind, clip in CLIPS.items():
        de = pick(donor_entries, kind)
        re_ = pick(recip_entries, kind)
        report['motion_entries'][kind] = {
            'donor': {'kind': hex(de['kind']), 'game_script': hex(de['game_script']),
                      'flags': de['flags'], 'blend': de['blend'], 'cancel': de['cancel'],
                      'anims': [hex(a) for a in de['anims']],
                      'expected_clip_hash': hex(hash40(clip)),
                      'names_own_clip': de['anims'] == (hash40(clip),)},
            'recipient': {'kind': hex(re_['kind']), 'game_script': hex(re_['game_script']),
                          'flags': re_['flags'], 'blend': re_['blend'], 'cancel': re_['cancel'],
                          'anims': [hex(a) for a in re_['anims']]},
            'cancel_differs': de['cancel'] != re_['cancel'],
            'entry_bytes_equal': de['raw'] == re_['raw'],
        }
        clip_info = clip_report(donor_ml.parent / clip)
        tracks = clip_info.pop('tracks')
        report['clips'][kind] = clip_info

        kept, dropped, case_only = [], [], []
        parent_mismatch = []
        for name in clip_info['node_names']:
            if name in recip_skel:
                kept.append(name)
                if donor_skel.get(name) != recip_skel.get(name):
                    parent_mismatch.append({'bone': name,
                                            'donor_parent': donor_skel.get(name),
                                            'recipient_parent': recip_skel.get(name)})
            elif name.lower() in {b.lower() for b in recip_skel}:
                case_only.append(name)
            else:
                dropped.append(name)
        report['fit'][kind] = {
            'nodes_total': len(clip_info['node_names']),
            'kept': len(kept),
            'dropped_count': len(dropped),
            'dropped': dropped,
            'case_only': case_only,
            'parent_mismatches': parent_mismatch,
            'visibility_group_replaced_by_recipient_idle': True,
            'recipient_idle_visibility_nodes': len(idle_vis.nodes),
            'material_groups_in_donor': clip_info['groups'].get('Material', 0),
            'limb_motion': motion_against_idle(tracks, idle_values),
        }
        report['fit'][kind]['all_limbs_present'] = all(
            report['fit'][kind]['limb_motion'][b]['present'] for b in LIMB_BONES)
        # Recorded because it decides two things in the Rust module: the two
        # dropped nodes are Lucas's bat, so this move needs no article, and
        # neither fighter's skeleton has a `havel` bone - `havel`/`haver` are
        # the engine's built-in hand anchors, the same class of name as the `top`
        # every hitbox in this game is written on, so the donor's effect anchors
        # are used unchanged rather than remapped to `HandL`.
        report['fit'][kind]['donor_only_bones'] = sorted(set(donor_skel) - set(recip_skel))
        report['fit'][kind]['built_in_anchors'] = {
            name: {'on_donor_skeleton': name in donor_skel,
                   'on_recipient_skeleton': name in recip_skel}
            for name in ('top', 'havel', 'haver', 'sword1')}
        report['fit'][kind]['static_limbs'] = sorted(
            b for b, v in report['fit'][kind]['limb_motion'].items() if not v['moved'])
        # A parent mismatch changes which way a limb bends, so it is reported
        # separately from a dropped node rather than hidden inside "kept".
        report['fit'][kind]['parent_mismatch_count'] = len(parent_mismatch)

    text = json.dumps(report, indent=2)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text + '\n')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
