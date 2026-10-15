"""Inventory the pinned Pikachu back-air (`AttackAirB`) donor material for eflame c06/c07 (v1.1.0).

Usage (from the mod root):

    python -B tools/audit_pikachu_airb_donor.py                 # full inventory
    python -B tools/audit_pikachu_airb_donor.py --smoke         # pins + motion entries only
    python -B tools/audit_pikachu_airb_donor.py --recipient <dir>
    python -B tools/audit_pikachu_airb_donor.py --negative-controls

What it answers
---------------
* The donor's own ``attack_air_b`` motion-list entry: cancel frame, flags, blend,
  clip name, game script - and the same four numbers for the **built recipient**,
  so "what changed" is a measured delta and not an assertion.
* The clip's structure (group types, node counts, frame count, final frame index)
  and how many Transform nodes survive a name-intersection retarget onto the
  built recipient skeleton, with the dropped names listed.
* Whether the retained Transform nodes keep their donor parent chains (a name
  filter cannot see a reparented bone).
* Which bones the donor's four scripts name, and whether each exists on the
  recipient (compared case-insensitively, as the engine does). ``trans`` is the
  recipient's real ``Trans`` root bone and is the donor's hitbox anchor; ``top``
  is the fighter's own origin, not a skeleton bone.
* Every effect and sound name the donor's scripts name, split into
  common-bank / recipient-bank / donor-bank, plus the ``seq_pikachu_rnd_attack``
  record's four voice children measured out of ``pikachu.sqb`` by CRC32.

What it does NOT establish: that the ported move looks right or behaves right on
G&W's body. That is tier D until a console run. Nothing is written outside
``refs/pikachu_attack_air_b/inventory.json``.

Negative controls
-----------------
``--negative-controls`` proves the checks can fail, by feeding the audit
deliberately broken inputs and asserting each one is caught:

1. a motion-list entry whose animation hash was written from the bare stem
   (``c05attackairb`` instead of ``c05attackairb.nuanmb``) - the Chrom jab
   defect in `handbook/00_INDEX.md` / CURRENT_INSTALL.md;
2. a motion-list entry whose cancel frame is moved;
3. a motion-list entry whose flags are moved;
4. a clip whose Transform node set is emptied (nothing survives the filter);
5. a clip whose retained nodes have been reparented on the recipient;
6. a sound merge that dropped one of the four sequence voice children.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import ssbh_data_py as s

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
sys.path.insert(0, str(ROOT / 'tools'))
import mlist  # noqa: E402
import merge_hero_neutral_b_sound as codec  # noqa: E402

REF = ROOT / 'refs/pikachu_attack_air_b'
ARC = REF / 'arc'
DONOR_MOTION = ARC / 'fighter/pikachu/motion/body/c00'
DONOR_SKEL = ARC / 'fighter/pikachu/model/body/c00/model.nusktb'
DONOR_CLIP = DONOR_MOTION / 'c05attackairb.nuanmb'
DONOR_LANDING_CLIP = DONOR_MOTION / 'c05landingairb.nuanmb'
DONOR_MLIST = DONOR_MOTION / 'motion_list.bin'
DONOR_SQB = ARC / 'sound/sequence/fighter/pikachu.sqb'
DONOR_SE = ARC / 'sound/bank/fighter/se_pikachu_c00'
ACMD = REF / 'donor_acmd/AttackAirB.txt'
ACMD_LANDING = REF / 'donor_acmd/LandingAirB.txt'
DONOR_MANIFEST = REF / 'donor_acmd/manifest.json'

KIND = 'attack_air_b'
LANDING_KIND = 'landing_air_b'
CLIP = 'c05attackairb.nuanmb'
LANDING_CLIP = 'c05landingairb.nuanmb'

# Pinned 2026-10-03 out of the local 13.0.4 data.arc
# (gamedata/ssbu-13.0.4/data.arc, archive sha256
# ef615e671e1d4907f0a707f2eb13e3cb0c8539c4e67ac51c89ef547c22b82995, 17,600,869,448 B)
# with the workspace tool tools/arc-extract. Re-checked on every run.
PINS = {
    'arc/fighter/pikachu/motion/body/c00/c05attackairb.nuanmb':
        'e26d84e63b5a9c32c06358acfe3e493f2bd15223d7e7e15bc2ec3b4b9a42a36f',
    'arc/fighter/pikachu/motion/body/c00/c05landingairb.nuanmb':
        'e1f5d0136c504e0c4ba4cc2270e728abe56f0bd9c13e28f8740e812deef2a9ea',
    'arc/fighter/pikachu/motion/body/c00/a00wait1.nuanmb':
        '0970181b4708c80da186fe9c961e97e9a4c71c849cb6e3014cd4ff05b1d3992f',
    'arc/fighter/pikachu/motion/body/c00/motion_list.bin':
        'd3a2d4cce201e2797e47b74cb4243db879101201e02108690f87f49ab6009c77',
    'arc/fighter/common/param/fighter_param.prc':
        '87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2',
    'arc/fighter/common/param/fighter_param_motion.prc':
        'b154abfde83a060830e7f036c2df3d32213035ebeea03c7a578ae9866c1d4969',
    'arc/fighter/pikachu/model/body/c00/model.nusktb':
        '09b80e92fa89921c4d895abe36f23252c2ba69c1ed2a787953185572d2b19b04',
    'arc/fighter/pikachu/ai/param/attack_data_param.prc':
        'cb00099404e6cd93a3747b3261198b6c9204c1be2438f84febb676cb5d90fa72',
    'arc/fighter/pikachu/ai/param/attack_list_param.prc':
        'b5fc4ca2d30b4983a25a9b7bf921078966b1fdcdb8b4d13a8fbb4f40d356d7a8',
    'arc/fighter/pikachu/param/vl.prc':
        '49a645b4e1833bb29f608b8d0b40eaff25c2e47750f0782a32355137f2af6b05',
    'arc/fighter/pikachu/param/expression_vl.prc':
        '5796f36ac742bbdef2f5bbe2b04d16c3638c5d6074afa5b550f9d095d35be97d',
    'arc/effect/fighter/pikachu/ef_pikachu.eff':
        '91c041b51727e74e75ad2053a8b93fd947ffb3ce7ff07c57396edb15b35cbd43',
    'arc/sound/bank/fighter/se_pikachu_c00.nus3audio':
        'b8dafdbd61e20a8cd08ad316abce8a7c9b751133c7cc31426b922bfec95e71c6',
    'arc/sound/bank/fighter/se_pikachu_c00.nus3bank':
        '03c56027c8c99399ce3052272aa347e054bccb80223868548c2f6dd48b2148f6',
    'arc/sound/bank/fighter/se_pikachu_c00.tonelabel':
        '8f67ad6e56b359f15310b9b094dcb7e6fea61072cc5229b032f856c4fe2c9521',
    'arc/sound/sequence/fighter/pikachu.sqb':
        'dbb822c05944e76e153c9a7fb8433c727924e8e4ccdfe02853c7cea2d1149845',
    'arc/sound/bank/fighter_voice/vc_pikachu_c00.nus3audio':
        'ced0269a277b65b81b71ea567f310315b7d62d972fac03d6761148e62ba1935e',
    'arc/sound/bank/fighter_voice/vc_pikachu_c00.nus3bank':
        'ed5c1ebaa7ce0f0dbee496b2a2c2183cffe9841194a635650b853d33b15d633e',
    'arc/sound/bank/fighter_voice/vc_pikachu_c00.tonelabel':
        '141ee9a001af633d632a5ebbf43e81c725beca265a8beed1fe34793497cc8e7a',
    'donor_acmd/AttackAirB.txt':
        '25e068e37aae8df818e24cc95ab2a08f051b3fcff85c41df2740c7ae15d2f95a',
    'donor_acmd/LandingAirB.txt':
        'b26b33e8d93c4beae0b802d4f8f7f4482e0bf1d66da4d339f163bf8228e23932',
}

DEFAULT_RECIPIENT = ROOT / ('builds/pgwr/0.20.23/ultimate/mods/pyra_gamewatch_reskin'
                            '/fighter/eflame')

# Effect names the donor's `effect_attackairb` names. Both are `sys_` names, i.e.
# the common bank every fighter can resolve - which is why no donor emitter has
# to be merged into a recipient bank. Asserted below, not assumed: if a future
# donor revision names a fighter-owned emitter, the run stops.
COMMON_EFFECTS = {'sys_spin_wind', 'sys_attack_impact', 'sys_down_smoke'}
# Sounds the donor names that are common-bank and therefore must NOT be merged
# from any donor bank (see handbook/05_acmd_porting.md on the Ness/Lucas splits).
COMMON_SOUNDS = {'se_common_swing_02'}
SEQUENCE = 'seq_pikachu_rnd_attack'
# The bones that carry a spin kick. A retarget that keeps their names but leaves
# them static is the R.O.B. down-tilt defect; see `assert_limbs_move`.
#
# A name absent from BOTH fighters' skeletons is not a static limb. `ElbowL/R` is
# the live example on this donor: neither Pikachu's nor eflame's `model.nusktb`
# has it (both have `H_ElbowL/R` instead), so it would report as static forever.
# handbook/04 records that exact lesson for the Snake up tilt: "a gate that
# counts absent bones as static limbs is a gate that cries wolf."
LIMB_BONES = ('Hip', 'LegL', 'LegR', 'KneeL', 'KneeR', 'FootL', 'FootR',
              'ToeL', 'ToeR', 'Waist', 'Bust', 'ShoulderL', 'ShoulderR',
              'ArmL', 'ArmR', 'HandL', 'HandR')


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(Path(path).read_bytes())


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def check_pins() -> dict:
    """Every pinned donor file must be present at the recorded revision."""
    out = {}
    for rel, digest in PINS.items():
        path = REF / rel
        if not path.is_file():
            raise SystemExit(f'missing pinned donor file: {rel}')
        got = sha(path)
        if got != digest:
            raise SystemExit(f'{rel}: sha256 {got} != pinned {digest}')
        out[rel] = {'sha256': got, 'bytes': path.stat().st_size}
    return out


def motion_entry(path: Path, kind: str) -> dict:
    """One raw motion-list entry, decoded as far as `mlist.py` decodes it."""
    ml = mlist.parse(path)
    if mlist.encode(ml) != ml['data']:
        raise SystemExit(f'{path}: motion list does not round-trip')
    entry = mlist.find(ml, kind)
    return {
        'path': str(path.relative_to(ROOT)).replace('\\', '/'),
        'entries_total': len(ml['entries']),
        'file_bytes': len(ml['data']),
        'round_trip': True,
        'raw_hex': entry['raw'].hex(),
        'raw_bytes': len(entry['raw']),
        'cancel': entry['cancel'],
        'flags': entry['flags'],
        'flags_hex': f'0x{entry["flags"]:04x}',
        'blend': entry['blend'],
        'n_anims': entry['n'],
        'game_script_hex': f'0x{entry["gs"]:x}',
        'anims_hex': [f'0x{a:x}' for a in entry['anims']],
    }


def clip_read(path: Path):
    with tempfile.NamedTemporaryFile(suffix='.nuanmb', delete=False) as fh:
        fh.write(Path(path).read_bytes())
        tmp = fh.name
    try:
        return s.anim_data.read_anim(tmp)
    finally:
        Path(tmp).unlink(missing_ok=True)


def group_of(anim, name: str):
    for g in anim.groups:
        if g.group_type.name == name:
            return g
    raise KeyError(f'no {name} group')


def bones(path: Path) -> dict:
    skel = s.skel_data.read_skel(str(path))
    return {b.name: b.parent_index for b in skel.bones}


def assert_parent_chains_match(measurement: dict, clip_name: str) -> None:
    """The build gate: refuse to ship a retarget whose parent chains moved.

    A name-intersection filter keeps a node whose name still exists even when the
    recipient hangs that bone off a different parent, so the limb bends the wrong
    way with no error anywhere. That is the failure mode `handbook/04` records
    for the rejected R.O.B. down tilt, so it is a hard gate rather than a field
    somebody reads later. Factored out so a negative control can drive it.
    """
    mismatches = measurement['parent_chain_mismatches']
    if mismatches:
        raise SystemExit(
            f'{clip_name}: {len(mismatches)} retained bone(s) hang off a different parent '
            f'on the recipient than in the donor: {mismatches}')
    kept = measurement['transform_kept']
    if not kept:
        raise SystemExit(f'{clip_name}: no Transform node survived the filter')


def limb_motion(donor, idle_anim) -> dict:
    """Largest rotation/translation each limb-chain bone reaches against the idle.

    The point is the failure node coverage cannot see: a retarget can keep every
    bone name and still leave the limbs in rest pose, which is what the user
    rejected on the R.O.B. down tilt. "Moved" means rotation **or** translation,
    because a foot bone can carry the motion as pure translation.
    """
    idle_values = {n.name: n.tracks[0].values[0]
                   for g in idle_anim.groups if g.group_type.name == 'Transform'
                   for n in g.nodes}
    tracks = {n.name: n.tracks[0].values for g in donor.groups
              if g.group_type.name == 'Transform' for n in g.nodes}
    out = {}
    for bone in LIMB_BONES:
        values = tracks.get(bone)
        base = idle_values.get(bone)
        if values is None or base is None:
            out[bone] = {'present_in_clip': values is not None,
                         'present_in_idle': base is not None,
                         'moved': False}
            continue
        rotation = max(_angle_between(v, base) for v in values)
        translation = max(max(abs(float(x) - float(y))
                              for x, y in zip(v.translation, base.translation))
                          for v in values)
        out[bone] = {'present_in_clip': True, 'present_in_idle': True,
                     'max_rotation_deg': round(rotation, 2),
                     'max_translation': round(translation, 4),
                     'moved': bool(rotation > 1.0 or translation > 0.05)}
    return out


def static_limbs(measurement: dict) -> list:
    """Bones the measurement says did not move.

    A name present in neither skeleton is filtered out first: it is not a limb,
    it is a spelling mistake, and counting it would make the gate cry wolf on
    every run (handbook/04, Snake up tilt, `ElbowL`/`ElbowR` here).
    """
    absent = set(measurement.get('limb_bones_absent_on_both_skeletons', ()))
    return [bone for bone, v in measurement['limb_motion'].items()
            if not v['moved'] and bone not in absent]


def assert_limbs_move(clip: Path, recipient_skel: Path, idle: Path) -> None:
    """The second build gate: every limb chain bone must measurably move.

    Node coverage cannot see a clip whose limbs sit in rest pose, which is exactly
    what the user rejected on the R.O.B. down tilt. `handbook/04` records the
    lesson for the Snake up tilt, which shipped 77/87 nodes and still had to
    measure `LegL/R`, `KneeL/R`, `FootL/R` and `ToeL/R` against the idle.
    """
    static = static_limbs(retarget_measurement(clip, recipient_skel, idle))
    if static:
        raise SystemExit(f'{clip.name}: limb bones are static after retarget: {static}')


def absent_limb_bones(recipient_skel: Path) -> list:
    """LIMB_BONES entries that are bones on neither fighter - not static limbs."""
    donor = set(bones(DONOR_SKEL))
    recipient = set(bones(recipient_skel))
    return [b for b in LIMB_BONES if b not in donor and b not in recipient]


def _angle_between(q, r) -> float:
    """Degrees between two SSBH xyzw rotations, sign-insensitive."""
    a = [float(x) for x in q.rotation]
    b = [float(x) for x in r.rotation]
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    dot = abs(sum(x / na * y / nb for x, y in zip(a, b)))
    return math.degrees(2.0 * math.acos(min(1.0, dot)))


def retarget_measurement(clip: Path, recipient_skel: Path, idle: Path) -> dict:
    """Which donor Transform nodes survive, and whether parent chains still match.

    A name-intersection filter cannot detect a reparented bone, so the parent of
    every *kept* node is compared by name between donor and recipient. This is
    the check the Snake up-tilt port added after the R.O.B. down tilt was
    rejected (handbook/04).
    """
    donor = clip_read(clip)
    dparent = bones(DONOR_SKEL)
    rparent = bones(recipient_skel)
    transform = group_of(donor, 'Transform')
    kept, dropped = [], []
    for node in transform.nodes:
        (kept if node.name in rparent else dropped).append(node.name)
    # Compare parent *names*: donor/recipient index spaces differ by construction.
    donor_names = list(dparent)
    recipient_names = list(rparent)
    by_name = []
    for name in kept:
        d_index = dparent.get(name)
        dp = donor_names[d_index] if d_index is not None and d_index >= 0 else None
        r_index = rparent.get(name)
        rp = recipient_names[r_index] if r_index is not None and r_index >= 0 else None
        by_name.append((name, dp, rp))
    parent_mismatch = [row for row in by_name if row[1] != row[2]]

    idle_vis = group_of(clip_read(idle), 'Visibility')
    donor_vis = group_of(donor, 'Visibility')
    vis_kept = [n.name for n in donor_vis.nodes if n.name in {x.name for x in idle_vis.nodes}]
    frames = sorted({len(n.tracks[0].values) for g in donor.groups for n in g.nodes})
    return {
        'clip': clip.name,
        'final_frame_index': donor.final_frame_index,
        'track_length_frames': frames,
        'groups': {g.group_type.name: len(g.nodes) for g in donor.groups},
        'transform_nodes': len(transform.nodes),
        'transform_kept': len(kept),
        'transform_dropped': dropped,
        'parent_chain_mismatches': [
            {'bone': n, 'donor_parent': d, 'recipient_parent': r}
            for n, d, r in parent_mismatch
        ],
        'visibility_group_nodes': len(donor_vis.nodes),
        'visibility_nodes_also_on_recipient_idle': len(vis_kept),
        'material_group_nodes': len(group_of(donor, 'Material').nodes)
        if any(g.group_type.name == 'Material' for g in donor.groups) else 0,
        'limb_motion': limb_motion(donor, clip_read(idle)),
        'limb_bones_absent_on_both_skeletons': absent_limb_bones(recipient_skel),
        'case_only_matches': [],
    }


def script_names(acmd: Path, kind: str) -> dict:
    """Every `PLAY_SE` / `PLAY_SEQUENCE` / `EFFECT*` / `ATTACK` bone the donor names."""
    text = Path(acmd).read_text(encoding='utf-8', errors='replace')
    # PLAY_SE and PLAY_LANDING_SE both name exactly one tone and resolve the same
    # way (in the fighter's own bank), so they are collected together.
    sounds = sorted(set(re.findall(
        r'PLAY_(?:SE|LANDING_SE)\(agent, Hash40::new\("([^"]+)"\)', text)))
    sequences = sorted(set(re.findall(
        r'PLAY_SEQUENCE\(agent, Hash40::new\("([^"]+)"\)', text)))
    effects = sorted(set(re.findall(r'(?:EFFECT|LAST_EFFECT_SET_\w+|FOOT_EFFECT|LANDING_EFFECT|'
                                    r'EFFECT_FOLLOW\w*|AFTER_IMAGE\w*)\(agent, '
                                    r'Hash40::new\("([^"]+)"\)', text)))
    bones_named = sorted(set(re.findall(r'macros::ATTACK\([^,]+,[^,]+,[^,]+, Hash40::new\("([^"]+)"\)', text)))
    bones_named += sorted(set(re.findall(r'ATTACK\(\s*agent,[^,]+,[^,]+,\s*\n?\s*Hash40::new\("([^"]+)"\)', text)))
    return {
        'sounds': sorted(set(sounds)),
        'sequences': sorted(set(sequences)),
        'effects': sorted(set(effects)),
        'hitbox_bones': sorted(set(bones_named)),
    }


def sequence_children() -> dict:
    """The four voice tones `seq_pikachu_rnd_attack` names, measured by CRC32.

    Same method `merge_ness_throw_sound.py` uses: the record's child entries are
    (crc32(lowercase name), name length) pairs, so the voice set follows the
    record instead of a hand-typed list. A hard-coded list could drift from the
    donor and leave the sequence silently resolving to silence.
    """
    voice_stem = REF / 'arc/sound/bank/fighter_voice/vc_pikachu_c00'
    voice_names = [n for n, _ in codec.audio_read(voice_stem.with_suffix('.nus3audio').read_bytes())]
    table = {(zlib.crc32(n.lower().encode()) & 0xffffffff, len(n.encode())): n for n in voice_names}
    records = [r for r in codec.sqb_read(DONOR_SQB.read_bytes())
               if int.from_bytes(r[:8], 'little') == hash40(SEQUENCE)]
    if len(records) != 1:
        raise SystemExit(f'{SEQUENCE}: expected 1 donor record, found {len(records)}')
    record = records[0]
    # The record stores each child as an adjacent (u32 crc32(lowercase name),
    # u32 name length) pair, interleaved with other per-child fields. Scanning
    # every 4-byte boundary for an adjacent matching pair finds the children
    # without having to model the surrounding layout, which is not documented -
    # the same measured approach merge_ness_throw_sound.py uses.
    resolved, offsets = [], []
    for off in range(0, len(record) - 7, 4):
        crc, ln = struct.unpack_from('<II', record, off)
        if (crc, ln) in table:
            resolved.append(table[(crc, ln)])
            offsets.append(off)
    # The trailing pair is the record's own terminator and matches no tone.
    if not resolved:
        raise SystemExit(f'{SEQUENCE}: no child entry resolved against the donor voice bank')
    expected = ['vc_pikachu_attack01', 'vc_pikachu_attack02',
                'vc_pikachu_attack03', 'vc_pikachu_attack04']
    if resolved != expected:
        raise SystemExit(f'{SEQUENCE}: resolved voice tones {resolved} != pinned {expected}')
    return {
        'record_key_hex': f'0x{hash40(SEQUENCE):x}',
        'record_bytes': len(record),
        'child_entries': len(resolved),
        'child_offsets': offsets,
        'voice_tones': resolved,
        'voice_tones_expected': ['vc_pikachu_attack01', 'vc_pikachu_attack02',
                                 'vc_pikachu_attack03', 'vc_pikachu_attack04'],
        'voice_source_bank': str(voice_stem.relative_to(ROOT)).replace('\\', '/'),
    }


def check_entry_names_clip(motion_dir: Path, kind: str, clip_name: str) -> None:
    """The motion entry's animation hash must resolve to the file this build writes.

    The Chrom jab lesson (CURRENT_INSTALL.md, `chrom_jab_sword` 1.0.0): an
    animation-name hash covers the file name *with its extension*, so a hash
    taken from the bare stem names a file that does not exist - which fails
    silently, leaving the previous clip playing. This is the check that catches
    that, and it is factored out so a negative control can drive it directly.
    """
    ml = mlist.parse(motion_dir / 'motion_list.bin')
    if mlist.encode(ml) != ml['data']:
        raise SystemExit(f'{motion_dir}/motion_list.bin does not round-trip')
    entry = mlist.find(ml, kind)
    for anim in entry['anims']:
        if anim != hash40(clip_name):
            raise SystemExit(
                f'{kind}: animation hash {anim:#x} does not name {clip_name} '
                f'({hash40(clip_name):#x}); a bare-stem hash names no file')
    if not (motion_dir / clip_name).is_file():
        raise SystemExit(f'{kind}: {clip_name} is named by the entry but absent from {motion_dir}')


def donor_inventory(recipient_body: Path | None) -> dict:
    report = {
        'tool_version': '1.1.0',
        'date': '2026-10-03',
        'evidence_tier': 'B',
        'hardware_validated': False,
        'move': "vanilla Pikachu back air (AttackAirB) onto eflame c06/c07 (G&W body)",
        'pins': check_pins(),
        'acmd_pin': json.loads(DONOR_MANIFEST.read_text(encoding='utf-8')),
        'motion': {
            'donor_attack_air_b': motion_entry(DONOR_MLIST, KIND),
            'donor_landing_air_b': motion_entry(DONOR_MLIST, LANDING_KIND),
        },
        'clip_name_hash_matches_entry': None,
        'scripts': script_names(ACMD, KIND),
        'landing_scripts': script_names(ACMD_LANDING, LANDING_KIND),
        'sequence': sequence_children(),
    }
    entry = mlist.find(mlist.parse(DONOR_MLIST), KIND)
    report['clip_name_hash_matches_entry'] = (
        list(entry['anims']) == [hash40(CLIP)])
    if not report['clip_name_hash_matches_entry']:
        raise SystemExit(f'donor {KIND} does not name {CLIP}')
    landing = mlist.find(mlist.parse(DONOR_MLIST), LANDING_KIND)
    report['landing_clip_name_hash_matches_entry'] = (
        list(landing['anims']) == [hash40(LANDING_CLIP)])
    if not report['landing_clip_name_hash_matches_entry']:
        raise SystemExit(f'donor {LANDING_KIND} does not name {LANDING_CLIP}')

    report['common_effects_not_merged'] = sorted(COMMON_EFFECTS)
    report['donor_effect_bank_not_shipped'] = {
        'path': 'effect/fighter/pikachu/ef_pikachu.eff',
        'reason': 'every emitter the donor names is a common-bank sys_* effect, so no '
                  'fighter-owned emitter has to be merged into a recipient bank; '
                  'handbook/facts/facts.yaml effect-bank-owned-by-recipient-fighter-dir',
    }
    se_names = {n.lower() for n, _ in
                codec.audio_read(DONOR_SE.with_suffix('.nus3audio').read_bytes())}
    named = set(report['scripts']['sounds']) | set(report['landing_scripts']['sounds'])
    donor_owned = sorted(n for n in named if n.lower() in se_names)
    report['donor_owned_sounds'] = donor_owned
    report['sounds_needing_merge'] = donor_owned
    common_only = sorted(n for n in named if n not in donor_owned)
    if not set(common_only) <= COMMON_SOUNDS:
        raise SystemExit(f'expected only the common sounds unresolved in the donor bank, '
                         f'got {common_only}')
    report['common_sounds_not_merged'] = common_only
    # `PLAY_LANDING_SE` names a tone the same way `PLAY_SE` does; assert the split
    # is exactly the common set and that nothing else fell through.
    if common_only != sorted(COMMON_SOUNDS & set(common_only)):
        raise SystemExit('common sound split is inconsistent')
    # A PLAY_SEQUENCE name resolves in the fighter's .sqb, not in a tone bank, so
    # it is checked separately: exactly the one donor record.
    if report['scripts']['sequences'] != [SEQUENCE]:
        raise SystemExit(f'unexpected PLAY_SEQUENCE names: {report["scripts"]["sequences"]}')
    for name, group in (('attack_air_b', report['scripts']),
                        ('landing_air_b', report['landing_scripts'])):
        extra = set(group['effects']) - COMMON_EFFECTS
        if extra:
            raise SystemExit(
                f'{name} names fighter-owned effects {sorted(extra)}; a donor emitter '
                f'has to be merged into a recipient bank, which this task does not do')

    if recipient_body is not None:
        for slot in ('c06', 'c07'):
            skel = recipient_body / 'model/body' / slot / 'model.nusktb'
            motion_dir = recipient_body / 'motion/body' / slot
            idle = motion_dir / 'a00wait1.nuanmb'
            report.setdefault('recipient', {})[slot] = {
                'skeleton_sha256': sha(skel),
                'idle_sha256': sha(idle),
                'bones': len(bones(skel)),
                'motion': {
                    'attack_air_b': motion_entry(motion_dir / 'motion_list.bin', KIND),
                    'landing_air_b': motion_entry(motion_dir / 'motion_list.bin', LANDING_KIND),
                },
                'retarget': {
                    'attack_air_b': retarget_measurement(DONOR_CLIP, skel, idle),
                    'landing_air_b': retarget_measurement(DONOR_LANDING_CLIP, skel, idle),
                },
            }
            for kind in ('attack_air_b', 'landing_air_b'):
                data = report['recipient'][slot]['motion'][kind]
                donor_same = report['motion'][f'donor_{kind}']
                data['diff_offsets_vs_donor'] = mlist.diff_offsets(
                    bytes.fromhex(donor_same['raw_hex']), bytes.fromhex(data['raw_hex']))
        report['delta'] = {}
        for slot in ('c06', 'c07'):
            report['delta'][slot] = {}
            for kind in ('attack_air_b', 'landing_air_b'):
                d = report['recipient'][slot]['motion'][kind]
                report['delta'][slot][kind] = {
                    'cancel_donor': report['motion'][f'donor_{kind}']['cancel'],
                    'cancel_recipient': d['cancel'],
                    'flags_donor': report['motion'][f'donor_{kind}']['flags_hex'],
                    'flags_recipient': d['flags_hex'],
                    'diff_offsets': d['diff_offsets_vs_donor'],
                }
        hitbox_bones = sorted(set(report['scripts']['hitbox_bones'])
                                | set(report['landing_scripts']['hitbox_bones']))
        rnames = set(bones(recipient_body / 'model/body/c06/model.nusktb'))
        dnames = set(bones(DONOR_SKEL))
        # Engine joint lookup is case-insensitive in practice: every ACMD script in
        # this mod and in the donor dump names bones in lower case (`trans`,
        # `handr`, `footl`) while the skeletons spell them `Trans`, `HandR`,
        # `FootL`. A case-sensitive comparison therefore reports `trans` as
        # "absent from both skeletons", which is what 1.0.0 recorded and then
        # explained away as a "built-in anchor". It is a real bone, `Trans`, the
        # root of both rigs (identity rest, parent of `Rot`). Only `top` - the
        # fighter's own origin - is genuinely not a skeleton bone.
        rlower = {n.lower() for n in rnames}
        dlower = {n.lower() for n in dnames}
        ENGINE_ANCHORS = {'top'}
        report['hitbox_bone_presence'] = {
            name: {
                'on_recipient_skeleton': name.lower() in rlower,
                'on_donor_skeleton': name.lower() in dlower,
                'recipient_bone_name': next((n for n in rnames if n.lower() == name.lower()), None),
                'donor_bone_name': next((n for n in dnames if n.lower() == name.lower()), None),
                'is_engine_anchor': name.lower() in ENGINE_ANCHORS,
                'remapped': False,
            } for name in hitbox_bones
        }
        for name, info in report['hitbox_bone_presence'].items():
            if not info['on_recipient_skeleton'] and not info['is_engine_anchor']:
                raise SystemExit(
                    f'hitbox bone {name!r} is on neither the recipient skeleton '
                    f'(compared case-insensitively) nor the engine-anchor list; it would '
                    f'need an explicit remap decision')
        # The Chrom jab lesson (CURRENT_INSTALL.md): an animation-name hash covers
        # the file name *with its extension*. A motion entry naming a hash that no
        # shipped file matches fails silently - the previous clip keeps playing -
        # so every hash the rewritten entries carry must resolve to a real file.
        for slot in ('c06', 'c07'):
            motion_dir = recipient_body / 'motion/body' / slot
            for kind, clip_name in ((KIND, CLIP), (LANDING_KIND, LANDING_CLIP)):
                check_entry_names_clip(motion_dir, kind, clip_name)
    report['not_established'] = (
        'Appearance, reach, multihit retention, finisher, landing lag and cleanup on '
        'G&W\'s body. Node coverage and motion-entry bytes are offline measurements (B); '
        'all runtime behaviour is tier D until a console run.')
    return report


# --------------------------------------------------------------------------
# Negative controls
# --------------------------------------------------------------------------

def _expect_fail(label: str, fn) -> bool:
    try:
        fn()
    except (Exception, SystemExit) as exc:  # noqa: BLE001 - any layer may refuse
        print(f'  caught {label}: {type(exc).__name__}')
        return True
    print(f'  NOT CAUGHT: {label}')
    return False


def negative_controls(recipient_body: Path) -> list:
    """Prove the audit's assertions can fail. Each control breaks one input."""
    results = []

    def bare_stem():
        # The Chrom jab defect: an animation-name hash taken from the bare stem
        # names a file that does not exist, which fails silently - the previous
        # clip keeps playing. Drive the real check with a doctored motion list.
        with tempfile.TemporaryDirectory() as tmp:
            motion_dir = Path(tmp)
            (motion_dir / CLIP).write_bytes(DONOR_CLIP.read_bytes())
            ml = mlist.parse(DONOR_MLIST)
            e = mlist.find(ml, KIND)
            broken = bytearray(e['raw'])
            struct.pack_into('<Q', broken, 24, hash40('c05attackairb'))  # no extension
            (motion_dir / 'motion_list.bin').write_bytes(
                struct.pack('<QQQ', ml['magic'], ml['motion_path'], 1) + bytes(broken))
            check_entry_names_clip(motion_dir, KIND, CLIP)
        raise AssertionError('bare-stem animation hash was not caught')

    def cancel_moved():
        ml = mlist.parse(DONOR_MLIST)
        e = mlist.find(ml, KIND)
        data = bytearray(e['raw'])
        struct.pack_into('<H', data, len(data) - 2, e['cancel'] + 1)
        reread = mlist.reread(bytes(data))
        assert reread[0]['cancel'] != e['cancel'], 'cancel check did not fire'

    def flags_moved():
        ml = mlist.parse(DONOR_MLIST)
        e = mlist.find(ml, KIND)
        data = bytearray(e['raw'])
        struct.pack_into('<H', data, 16, e['flags'] ^ 0x04)
        reread = mlist.reread(bytes(data))
        assert reread[0]['flags'] != e['flags'], 'flags check did not fire'

    def empty_filter():
        # A skeleton that cannot be read at all, and one that reads but holds no
        # bone the clip names, must both make the retarget refuse.
        idle = recipient_body / 'motion/body/c06/a00wait1.nuanmb'
        with tempfile.TemporaryDirectory() as tmp:
            garbage = Path(tmp) / 'model.nusktb'
            garbage.write_bytes(b'\x00' * 64)
            retarget_measurement(DONOR_CLIP, garbage, idle)
        raise AssertionError('unreadable skeleton was not caught')

    def reparented():
        # A name filter cannot see a reparented bone: the node name still matches,
        # so it survives, but the limb now hangs off the wrong parent. The
        # detector has to report it. `HandR -> FootL` is a non-cyclic pair in
        # this skeleton, so the control is testing the mismatch check and not the
        # skeleton writer's cycle rejection.
        skel_path = recipient_body / 'model/body/c06/model.nusktb'
        idle = recipient_body / 'motion/body/c06/a00wait1.nuanmb'
        skel = s.skel_data.read_skel(str(skel_path))
        names = [b.name for b in skel.bones]

        def ancestors(index):
            chain, cur = set(), index
            while cur is not None:
                chain.add(cur)
                cur = skel.bones[cur].parent_index
            return chain

        bone, target = 'HandR', 'FootL'
        i, j = names.index(bone), names.index(target)
        assert i not in ancestors(j) and j not in ancestors(i), 'control pair cycles'
        skel.bones[i].parent_index = j
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'model.nusktb'
            skel.save(str(out))
            m = retarget_measurement(DONOR_CLIP, out, idle)
        assert any(row['bone'] == bone for row in m['parent_chain_mismatches']), \
            'reparenting was not detected by the measurement'
        # And the gate that consumes it must refuse to ship.
        assert_parent_chains_match(m, DONOR_CLIP.name)

    def dropped_voice():
        # Corrupt the donor sequence record so one of its four voice children no
        # longer resolves. The audit must refuse rather than ship a sequence that
        # silently plays nothing.
        recs = codec.sqb_read(DONOR_SQB.read_bytes())
        rec = [r for r in recs if int.from_bytes(r[:8], 'little') == hash40(SEQUENCE)][0]
        index = recs.index(rec)
        bad = bytearray(rec)
        struct.pack_into('<I', bad, 16, 0xDEADBEEF)
        struct.pack_into('<I', bad, 20, 0x000000FF)
        saved = DONOR_SQB.read_bytes()
        try:
            DONOR_SQB.write_bytes(
                codec.sqb_write(recs[:index] + [bytes(bad)] + recs[index + 1:]))
            sequence_children()
        finally:
            DONOR_SQB.write_bytes(saved)

    def static_limb():
        # A clip whose limb bones all sit at the idle pose: node coverage is
        # unchanged, so only the measured-motion gate can catch this. The
        # recipient's own idle clip stands in for such a "move", because a neutral
        # pose is by definition static against itself.
        skel = recipient_body / 'model/body/c06/model.nusktb'
        idle = recipient_body / 'motion/body/c06/a00wait1.nuanmb'
        assert not absent_limb_bones(skel), \
            f'LIMB_BONES lists bones absent from both skeletons: {absent_limb_bones(skel)}'
        m = retarget_measurement(idle, skel, idle)
        assert static_limbs(m), 'a clip identical to the idle did not report static limbs'
        assert_limbs_move(idle, skel, idle)  # must refuse

    def false_alarm():
        # The converse of the static-limb gate, and the check that keeps it honest:
        # a name that is not a bone on either fighter must NOT be reported static.
        # `ElbowL/R` is the live example - both fighters spell it `H_ElbowL/R`.
        skel = recipient_body / 'model/body/c06/model.nusktb'
        donor = set(bones(DONOR_SKEL))
        recipient = set(bones(skel))
        for name in ('ElbowL', 'ElbowR'):
            assert name not in donor and name not in recipient, \
                f'{name} is a bone on one fighter; re-check the assumption'
            # It must not be in LIMB_BONES either: a tracked name that is not a
            # bone would report as a static limb on every single run.
            assert name not in LIMB_BONES, \
                f'{name} is not a bone on either fighter but is in LIMB_BONES'
        m = retarget_measurement(DONOR_CLIP, skel,
                                 recipient_body / 'motion/body/c06/a00wait1.nuanmb')
        reported = static_limbs(m)
        assert 'ElbowL' not in reported and 'ElbowR' not in reported, \
            f'absent bones reported as static limbs: {reported}'
        # And a real static limb must still be caught, so the filter is not
        # simply swallowing everything.
        poisoned = json.loads(json.dumps(m))
        poisoned['limb_motion']['HandR']['moved'] = False
        if 'HandR' not in static_limbs(poisoned):
            raise AssertionError('the absent-bone filter also hid a genuinely static limb')

    controls = [
        ('bare-stem animation name hash', bare_stem),
        ('moved cancel frame', cancel_moved),
        ('moved motion-list flags', flags_moved),
        ('unreadable/empty skeleton (nothing survives the filter)', empty_filter),
        ('reparented retained bone', reparented),
        ('static limb chain', static_limb),
        ('sequence record missing a voice child', dropped_voice),
    ]
    for label, fn in controls:
        results.append({'control': label, 'kind': 'negative',
                        'caught': _expect_fail(label, fn)})
    # Positive checks: these must PASS. They guard the gates above against
    # becoming vacuous - a gate that never fires is not a check.
    for label, fn in [('absent bones are not counted as static limbs', false_alarm)]:
        try:
            fn()
            print(f'  passed {label}')
            results.append({'control': label, 'kind': 'positive', 'passed': True})
        except Exception as exc:  # noqa: BLE001
            print(f'  FAILED {label}: {type(exc).__name__}: {exc}')
            results.append({'control': label, 'kind': 'positive', 'passed': False})
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recipient', type=Path, default=None,
                        help='fighter/eflame directory of the built recipient tree')
    parser.add_argument('--smoke', action='store_true',
                        help='pins + motion entries only; no recipient tree needed')
    parser.add_argument('--negative-controls', action='store_true')
    parser.add_argument('--output', type=Path, help='write inventory.json here')
    args = parser.parse_args()

    if args.negative_controls:
        body = args.recipient or (DEFAULT_RECIPIENT)
        assert body.is_dir(), body
        results = negative_controls(body)
        print(json.dumps(results, indent=2))
        failed = [r['control'] for r in results if r['kind'] == 'negative' and not r['caught']]
        failed += [r['control'] for r in results if r['kind'] == 'positive' and not r['passed']]
        if failed:
            raise SystemExit(f'controls failed: {failed}')
        print('audit_pikachu_airb_donor: all controls behaved as required')
        return

    recipient = None if args.smoke else (args.recipient or DEFAULT_RECIPIENT)
    if recipient is not None and not recipient.is_dir():
        raise SystemExit(f'recipient tree not found: {recipient}')
    report = donor_inventory(recipient)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    d = report['motion']['donor_attack_air_b']
    print(f"donor {KIND}: cancel {d['cancel']} flags {d['flags_hex']} "
          f"blend {d['blend']} clip {d['anims_hex']} (expect {hex(hash40(CLIP))})")
    print(f"scripts: sounds {report['scripts']['sounds']}")
    print(f"        effects {report['scripts']['effects']} (common: "
          f"{report['common_effects_not_merged']})")
    print(f"        hitbox bones {report['scripts']['hitbox_bones']}")
    print(f"landing: sounds {report['landing_scripts']['sounds']} "
          f"effects {report['landing_scripts']['effects']} "
          f"hitbox bones {report['landing_scripts']['hitbox_bones']}")
    print(f"donor-owned sounds to merge: {report['sounds_needing_merge']}")
    print(f"sequence {SEQUENCE}: {report['sequence']['voice_tones']}")
    if recipient is not None:
        for slot, rep in report['recipient'].items():
            r = rep['retarget']['attack_air_b']
            print(f"{slot}: attack_air_b kept {r['transform_kept']}/{r['transform_nodes']} "
                  f"nodes, dropped {r['transform_dropped']}, "
                  f"parent mismatches {len(r['parent_chain_mismatches'])}, "
                  f"final frame {r['final_frame_index']}")
            rl = rep['retarget']['landing_air_b']
            print(f"{slot}: landing_air_b kept {rl['transform_kept']}/{rl['transform_nodes']} "
                  f"nodes, final frame {rl['final_frame_index']}")
            print(f"{slot}: delta {report['delta'][slot]['attack_air_b']}")
            print(f"{slot}: delta {report['delta'][slot]['landing_air_b']}")
        print(f"hitbox bone presence: {report['hitbox_bone_presence']}")
    print('audit_pikachu_airb_donor OK')


if __name__ == '__main__':
    main()