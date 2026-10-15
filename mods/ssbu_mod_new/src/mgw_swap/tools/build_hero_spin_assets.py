"""Build and package the five retargeted Hero Spin motions for elight c07.

Why this tool exists
--------------------
Mii Swordfighter's Hero Spin up-B is being transplanted onto Mythra (`elight`)
`c07`. The donor clips are the Mii's `d02specialhi1*` family and the recipient
slots are Mythra's own up-B slots, which already exist in the base install:

    donor clip                     recipient slot          file written
    d02specialhi1start.nuanmb      special_hi_start        d02specialhistart.nuanmb
    d02specialairhi1start.nuanmb   special_air_hi_start    d02specialairhistart.nuanmb
    d02specialairhi1.nuanmb        special_air_hi_jump     d02specialairhijump.nuanmb
    d02specialairhi1loop.nuanmb    special_air_hi1         d02specialairhi1.nuanmb
    d02specialhi1end.nuanmb        special_air_hi_end      d02specialairhiend.nuanmb

Because every target name already exists in the base install this move needs
**no carrier repointing and no new animation name** - unlike
`tools/build_monkey_flip_assets.py`, which had to load twelve donor-named files
over Game & Watch names the engine never resolved. No new name is introduced
here, and the tool refuses to leave a donor-named clip in the output folder.

What this tool does
-------------------
1. Reads the recipient skeleton from the dump (elight c07, 169 bones) and
   intersects donor Transform tracks with it **by bone name**, never by index:
   the recipient's animation node order is alphabetical while the skeleton's is
   hierarchical, so a positional retarget would bind the wrong bones.
   The Mii's 75 transform tracks leave 64 that name bones Mythra has; the 11
   dropped ones are the Mii's finger effect segments and `Miihead`.
2. Drops the donor's Visibility group (the Mii's mesh names) and installs the
   recipient's own Visibility and Material groups, both taken from
   `fighter/elight/motion/body/c07/a00wait1.nuanmb` - Mythra's default standing
   motion - pinned by measured value: layout `6dc7dbb4addc`, 19 visibility
   nodes, visible set {Gamemodel, eflame_Mouth_FaceN}; material: 4 nodes
   (EyeL, EyeR, def_flame_001_add, skin_flame_001), 22 constant tracks.
   That clip is the only usable source class because every node of it is
   constant, so it can be resized to a clip of any length without inventing a
   value. The recipient's own up-B clips carry the same 34-node visibility
   layout `dee56b0400c5` but animate 2 of those visibility tracks and 2 material
   tracks, and an animated recipient track cannot be retimed onto a donor clip
   of a different length without inventing data. That alternative and its
   rejection are recorded in the manifest.
3. Applies the two motion-list metadata fixes PLAN.md section 13 measured as
   mismatches, and asserts both in the written file:
     - `special_air_hi1` (the loop slot) needs `loop: true`: the donor's
       `special_air_hi1_loop` has it, the recipient's slot does not, and the
       donor's Loop status never tests `MotionModule::is_end()`, so without it
       the six-frame clip plays once and the status holds the final frame until
       landing. Bit 1 (0x02) of the entry's flag word.
     - `special_air_hi_end` (the End slot) needs `cancel_frame: 45`: the donor's
       value, where the recipient has 0. Last-2 byte of the entry, the same
       field `tools/build_monkey_flip_assets.py` and `tools/build_fair_assets.py`
       already patch.
   Neither the bit nor the byte is assumed: both are first proved against the
   donor's own motion_list.bin, whose `special_air_hi1_loop` is documented as
   `loop: true` and whose `special_hi1_end` is documented as cancel frame 45.
4. Writes a motion_list.bin into the mod output only because the metadata patch
   needs one; the baseline is the base install's elight c07 list, byte-identical
   to elight c00's. Every unrelated entry is asserted byte-identical to that
   baseline, and each patched entry is asserted to differ from it at exactly the
   intended byte offsets and nowhere else.

Invariants, asserted not assumed
--------------------------------
Every count below was measured from the dump and is re-checked on every run, so
a donor or recipient change fails loudly instead of silently shipping wrong
assets. Sources of the pinned values:
  - `references/miiswordsman_special_hi/PLAN.md` sections 2, 3, 12 and 13: the
    slot map, the 75/64/11 track expectation, the two metadata mismatches.
  - the dump: donor clip bytes and counts, the recipient skeleton, the recipient
    and donor motion lists, the recipient group source (hashes below).
  - `references/miiswordsman_special_hi/motion_list_body_c00.yml`: the donor slot
    metadata used to prove the flag bit and the cancel byte.
Every written clip is read back and re-parsed, and its group list, node names,
track counts, frame count and value fingerprint are checked against what was
intended; a successful write is not treated as evidence of a correct file.

Run: python mod_files/mythra_gamewatch_swap/tools/build_hero_spin_assets.py
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import struct
import zlib

import ssbh_data_py as s

WORKSPACE = Path(__file__).resolve().parents[3]
# Same configurable dump as build_monkey_flip_assets.py; see the note there.
EXPORT = Path(os.environ.get('MGW_EXPORT', WORKSPACE / 'dumps' / 'arc'))
if not EXPORT.is_dir():
    raise SystemExit(
        f'Game dump not found at {EXPORT}.\n'
        f'The dump is expected at <workspace_root>/export. Point MGW_EXPORT at '
        f'it when it lives elsewhere, from cmd.exe:\n'
        f'    set MGW_EXPORT=<drive>:<path to the ArcExplorer export folder>')
MOD_OUT = WORKSPACE / 'mod_output/ultimate/mods/mythra_gamewatch_swap'
OUT_MOTION_DIR = MOD_OUT / 'fighter/elight/motion/body/c07'

DONOR_DIR = EXPORT / 'fighter/miiswordsman/motion/body/c00'
DONOR_MLIST = DONOR_DIR / 'motion_list.bin'
RECIPIENT_MOTION_DIR = EXPORT / 'fighter/elight/motion/body/c07'
RECIPIENT_MOTION_DIR_ALT = EXPORT / 'fighter/elight/motion/body/c00'
RECIPIENT_SKEL = EXPORT / 'fighter/elight/model/body/c07/model.nusktb'
RECIPIENT_MESH = EXPORT / 'fighter/elight/model/body/c07/model.numshb'
# Recipient group source: Mythra's own default standing motion. Constant in both
# the Visibility and the Material group, which is what makes the resize step
# below honest. See the module docstring for why the up-B family's own layout is
# not usable, and the manifest for the recorded alternative.
VIS_SOURCE = RECIPIENT_MOTION_DIR / 'a00wait1.nuanmb'
VIS_SOURCE_ALT = RECIPIENT_MOTION_DIR_ALT / 'a00wait1.nuanmb'
VIS_LAYOUT = '6dc7dbb4addc'
RECIPIENT_MLIST_FALLBACKS = [
    RECIPIENT_MOTION_DIR / 'motion_list.bin',
    RECIPIENT_MOTION_DIR_ALT / 'motion_list.bin',
]

MANIFEST = WORKSPACE / 'references/miiswordsman_special_hi/hero_spin_animation_manifest.json'

# (recipient slot, donor animation, recipient animation file written) in move
# order. The recipient names are the slots' own animation names, read from the
# recipient motion list below and asserted against it every run.
MOTIONS = [
    ('special_hi_start', 'd02specialhi1start.nuanmb', 'd02specialhistart.nuanmb'),
    ('special_air_hi_start', 'd02specialairhi1start.nuanmb',
     'd02specialairhistart.nuanmb'),
    ('special_air_hi_jump', 'd02specialairhi1.nuanmb',
     'd02specialairhijump.nuanmb'),
    ('special_air_hi1', 'd02specialairhi1loop.nuanmb', 'd02specialairhi1.nuanmb'),
    ('special_air_hi_end', 'd02specialhi1end.nuanmb', 'd02specialairhiend.nuanmb'),
]
# Donor slot each donor clip belongs to, for the donor motion-list cross-check
# that proves the flag bit and the cancel-frame byte before they are written.
DONOR_SLOT = {
    'd02specialhi1start.nuanmb': 'special_hi1_start',
    'd02specialairhi1start.nuanmb': 'special_air_hi1_start',
    'd02specialairhi1.nuanmb': 'special_air_hi1',
    'd02specialairhi1loop.nuanmb': 'special_air_hi1_loop',
    'd02specialhi1end.nuanmb': 'special_hi1_end',
}

# The two metadata fixes (PLAN.md section 13) and the raw-entry field locations
# they live at. The flag word is a uint16 at byte 16 of a motion entry (after the
# 8-byte kind and 8-byte game script, then flags, blend, animation count, size);
# the cancel frame is the last-2 byte, which is where the donor's own 45 and the
# Monkey Flip and fair tools' patches are already read from.
LOOP_SLOT = 'special_air_hi1'
LOOP_FLAG_BIT = 0x02
LOOP_FLAGS_BEFORE = 0x0080
LOOP_FLAGS_AFTER = 0x0082
END_SLOT = 'special_air_hi_end'
END_CANCEL_FRAME = 45
END_CANCEL_BEFORE = 0
MLIST_FLAGS_OFFSET = 16

# Measured invariants. These are the donor's, the recipient's and the source
# clip's shape, not guesses.
EXPECTED_DONOR_TRANSFORM_TRACKS = 75
EXPECTED_KEPT_TRACKS = 64
EXPECTED_DROPPED_TRACKS = (
    'FingerL14_eff', 'FingerL24_eff', 'FingerL34_eff', 'FingerL44_eff',
    'FingerL54_eff', 'FingerR14_eff', 'FingerR24_eff', 'FingerR34_eff',
    'FingerR44_eff', 'FingerR54_eff', 'Miihead')
EXPECTED_DONOR_GROUPS = ('Transform', 'Visibility')
EXPECTED_RECIPIENT_BONES = 169
EXPECTED_VIS_NODES = 19
EXPECTED_VIS_VISIBLE = ('Gamemodel', 'eflame_Mouth_FaceN')
EXPECTED_MAT_NODES = 4
EXPECTED_MAT_TRACKS = 22
EXPECTED_MAT_NAMES = ('EyeL', 'EyeR', 'def_flame_001_add', 'skin_flame_001')
RECIPIENT_SKEL_SHA256 = '5b6fbbe6f702e5ab9b14b208899799ec99f13c15e88611017b2547ac3de93f03'
RECIPIENT_MLIST_SHA256 = '0b091450a00bdb2b382c59e965997f96d2a387dd2581d7d492183dd69d56c2f7'
EXPECTED_MLIST_ENTRIES = 734
# Pinned donor bytes: if the dump's Mii clips change, the retarget this tool
# ships changes with them, so that has to fail here rather than downstream.
DONOR_SHA256 = {
    'd02specialhi1start.nuanmb':
        '14fa82001c072789cdb2c983bc2467219361408376c4b99b3d715e3b6813b3f5',
    'd02specialairhi1start.nuanmb':
        'be456cd3dce697fbbe420bba5d18e56752ae164e1d9524f2c746b33ef22f799f',
    'd02specialairhi1.nuanmb':
        'e098078db7f025af0e314c2e51b7eeb71e3a80c859d55138f52e7aa33971bc05',
    'd02specialairhi1loop.nuanmb':
        'a6ef4bde8df94823d7889397bbac2ce51228ac55aa4292044fba8b8b71e0b4c0',
    'd02specialhi1end.nuanmb':
        '597767cfc12c67e38abad1c268524140a8b12c6c3bc7c7f3f0661aa5aee12c16',
}
# Files in this output folder that other tools own. Writing one of them here
# would fight another build, so a collision is fatal rather than silent.
FOREIGN_OWNED = ('c05attackairhi.nuanmb', 'e01throwlw.nuanmb')


def hash40(name):
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse_mlist(path):
    """Parse a motion_list.bin. Mirrors references/inject_monkey_flip.py."""
    data = Path(path).read_bytes()
    magic, motion_path, count = struct.unpack_from('<QQQ', data)
    if magic != hash40('motion'):
        raise ValueError(f'Invalid motion-list header: {path}')
    offset = 24
    motions = {}
    for _ in range(count):
        start = offset
        kind, game_script, flags, blend, animations, size = struct.unpack_from(
            '<QQHBBI', data, offset)
        if animations > 3 or size % 8 not in (0, 4):
            raise ValueError(f'Invalid motion entry: {path} at {offset:#x}')
        offset += 24
        names = struct.unpack_from('<' + 'Q' * animations, data, offset)
        offset = (offset + animations * 9 + 3) & ~3
        end = offset + size
        if end > len(data) or kind in motions:
            raise ValueError(f'Truncated or duplicate motion: {path}, {kind:#x}')
        motions[kind] = {
            'raw': data[start:end], 'animations': names, 'game_script': game_script,
            'flags': flags, 'blend': blend, 'size': size,
            'cancel': data[end - 2] if size % 8 == 4 else None,
        }
        offset = end
    if offset != len(data):
        raise ValueError(f'Unexpected trailing data: {path}')
    return magic, motion_path, motions


def encode_mlist(magic, motion_path, motions):
    return struct.pack('<QQQ', magic, motion_path, len(motions)) + b''.join(
        m['raw'] for m in motions.values())


def groups_by_type(anim):
    return {g.group_type.name: g for g in anim.groups}


def const_key(value):
    """Hashable, rounded identity of an animation value.

    The installed ssbh_data_py hands Visibility values back as bools, Material
    values as vectors (lists of four floats), and Transform values as a Transform
    whose scale/rotation/translation are float lists. The Monkey Flip fingerprint
    understood only scalars and xyzw objects, so for two of those three shapes it
    recorded nothing and for a transform it fell through to a printed float,
    which a one-ULP float32 round trip changes. This covers all three.
    """
    if isinstance(value, bool):
        return ('b', value)
    if isinstance(value, (int, float)):
        return round(float(value), 5)
    if isinstance(value, (list, tuple)):
        return tuple(const_key(v) for v in value)
    for attrs in (('scale', 'rotation', 'translation'), ('x', 'y', 'z', 'w')):
        if all(hasattr(value, a) for a in attrs):
            return tuple((a, const_key(getattr(value, a))) for a in attrs)
    return repr(value)


def flat_values(value):
    """One animation value as a flat tuple of floats (or a single bool)."""
    if isinstance(value, bool):
        return (value,)
    if isinstance(value, (int, float)):
        return (float(value),)
    if isinstance(value, (list, tuple)):
        return tuple(x for v in value for x in flat_values(v))
    for attrs in (('scale', 'rotation', 'translation'), ('x', 'y', 'z', 'w')):
        if all(hasattr(value, a) for a in attrs):
            return tuple(x for a in attrs for x in flat_values(getattr(value, a)))
    return (repr(value),)


def node_series(nodes):
    """Per-node, per-track lists of flat value tuples, keyed by node name.

    Node order and track order are not semantic - binding is by name and the
    writer does not promise to keep the order it was handed - so both are
    normalised by name; the values inside a track keep their order, which is what
    carries the animation.
    """
    out = {}
    for n in nodes:
        out[n.name] = [[flat_values(v) for v in (t.values or [])]
                       for t in sorted(n.tracks, key=lambda track: track.name)]
    return out


def first_difference(name, written, reread, tolerance=1e-4):
    """Description of the first value difference in a node, or None.

    The tolerance exists because the write path is not bit-exact:
      - ssbh_data_py re-quantises transform floats to float32, so a component can
        come back one ULP from the float64 value read out of the donor file
        (measured: -0.24764026701450348 written, -0.24764025211334229 re-read);
      - the quaternion it writes is normalised, so a donor quaternion whose norm
        is off by ~1e-5 comes back with every component moved by about that much
        (measured: component 0.003409238299354911 written, 0.0034266768489032984
        re-read, delta 1.74e-05).
    Neither is a retargeting defect: 1e-4 on a rotation component is about
    0.006 degrees. A real mismatch - the wrong bone, the wrong phase, a truncated
    track - is orders of magnitude larger, so this tolerance still fails it
    loudly while the measured maximum is recorded in the manifest.
    """
    if len(written) != len(reread):
        return f'{name}: {len(written)} tracks written, {len(reread)} re-read'
    for track_index, (a_track, b_track) in enumerate(zip(written, reread)):
        if len(a_track) != len(b_track):
            return (f'{name} track {track_index}: {len(a_track)} values written, '
                    f'{len(b_track)} re-read')
        for value_index, (a_value, b_value) in enumerate(zip(a_track, b_track)):
            if len(a_value) != len(b_value):
                return (f'{name} track {track_index} value {value_index}: '
                        f'{a_value} written, {b_value} re-read')
            for component, (a, b) in enumerate(zip(a_value, b_value)):
                if isinstance(a, bool) or isinstance(b, bool):
                    if a != b:
                        return (f'{name} track {track_index} value {value_index}: '
                                f'{a} written, {b} re-read')
                elif abs(a - b) > tolerance:
                    return (f'{name} track {track_index} value {value_index} '
                            f'component {component}: {a!r} written, {b!r} '
                            f're-read (delta {abs(a - b):.3e})')
    return None


def max_component_delta(written, reread):
    """Largest absolute component difference between two series.

    `float('inf')` when a value is missing or a boolean differs, so an
    incomplete comparison can never be reported as a small drift.
    """
    worst = 0.0
    for name in written:
        for a_track, b_track in zip(written[name], reread[name]):
            for a_value, b_value in zip(a_track, b_track):
                if len(a_value) != len(b_value):
                    return float('inf')
                for a, b in zip(a_value, b_value):
                    if isinstance(a, bool) or isinstance(b, bool):
                        if a != b:
                            return float('inf')
                    else:
                        worst = max(worst, abs(a - b))
    return worst


def collapse_series(series):
    """Collapse each constant track in a series to a single value.

    ssbh_data_py stores a constant track as one value instead of one per frame,
    so the length of a constant track is not preserved across a write/read round
    trip. Collapsing both sides of the comparison compares meaning, not storage.
    """
    out = {}
    for name, tracks in series.items():
        collapsed = []
        for values in tracks:
            if len(values) > 1 and len({repr(v) for v in values}) == 1:
                collapsed.append([values[0]])
            else:
                collapsed.append(list(values))
        out[name] = collapsed
    return out


def flat_difference(written, reread, tolerance=1e-5):
    """Description of a difference between two flat value tuples, or None."""
    if len(written) != len(reread):
        return f'{written} written, {reread} re-read'
    for index, (a, b) in enumerate(zip(written, reread)):
        if isinstance(a, bool) or isinstance(b, bool):
            if a != b:
                return f'{a} written, {b} re-read'
        elif abs(a - b) > tolerance:
            return (f'component {index}: {a!r} written, {b!r} re-read '
                    f'(delta {abs(a - b):.3e})')
    return None


def node_constants(nodes):
    """Per node, per track, the single distinct value as a flat tuple."""
    out = {}
    for n in nodes:
        tracks = {}
        for t in sorted(n.tracks, key=lambda track: track.name):
            keys = {repr(const_key(v)) for v in (t.values or [])}
            if len(keys) != 1:
                raise SystemExit(f'{n.name}/{t.name} is not constant')
            tracks[t.name] = flat_values((t.values or [None])[0])
        out[n.name] = tracks
    return out


def node_fingerprints(nodes):
    """Per-node fingerprint, keyed by name.

    Node order is not semantic - binding is by name, and the writer does not
    promise to keep the list order it was handed - so the fingerprint is keyed
    by node name and the tracks inside a node are sorted by name. Comparing
    these dicts across a write/read round trip therefore tests the values, not
    the ordering.
    """
    out = {}
    for n in nodes:
        h = hashlib.sha256()
        for t in sorted(n.tracks, key=lambda track: track.name):
            h.update(t.name.encode())
            h.update(repr([const_key(v) for v in (t.values or [])]).encode())
            h.update(b'|')
        out[n.name] = h.hexdigest()
    return out


def values_fingerprint(nodes):
    """Stable fingerprint of a set of nodes, for phase-distinctness and drift."""
    h = hashlib.sha256()
    for name, fingerprint in sorted(node_fingerprints(nodes).items()):
        h.update(name.encode())
        h.update(fingerprint.encode())
        h.update(b'|')
    return h.hexdigest()


def visibility_layout_id(group):
    """Layout id: hash of node-name -> value-set, as Monkey Flip does.

    The id hashes the full node-name to visible-set mapping, so pinning it checks
    the node names and the visible set together, not just the count.
    """
    per_node = {}
    for n in group.nodes:
        vals = []
        for t in n.tracks:
            vals.extend([bool(v) for v in (t.values or [])])
        per_node[n.name] = tuple(sorted(set(vals)))
    return hashlib.sha256(
        repr(sorted(per_node.items())).encode()).hexdigest()[:12]


def read_recipient_groups():
    """The recipient's own Visibility and Material groups, pinned by value.

    Read fresh on every call, so the resize below cannot contaminate the next
    motion, and validated on every call, so the invariants are re-checked per
    clip rather than once.
    """
    for path in (VIS_SOURCE, VIS_SOURCE_ALT):
        if not path.is_file():
            raise SystemExit(f'Missing recipient group source: {path}')
    if sha256(VIS_SOURCE) != sha256(VIS_SOURCE_ALT):
        raise SystemExit(
            f'{VIS_SOURCE} and {VIS_SOURCE_ALT} differ, so "the recipient\'s own '
            f'default standing motion" is ambiguous and the pinned layout below '
            f'cannot be attributed to one file.')
    anim = s.anim_data.read_anim(str(VIS_SOURCE))
    groups = groups_by_type(anim)
    vis = groups.get('Visibility')
    mat = groups.get('Material')
    if vis is None:
        raise SystemExit(f'No Visibility group in {VIS_SOURCE}')
    if mat is None:
        raise SystemExit(f'No Material group in {VIS_SOURCE}')

    visible = []
    for n in vis.nodes:
        if len(n.tracks) != 1:
            raise SystemExit(
                f'Visibility node {n.name} has {len(n.tracks)} tracks; the '
                f'resize-to-motion-length step assumes one track per node.')
        vals = [bool(v) for v in (n.tracks[0].values or [])]
        if not vals:
            raise SystemExit(f'Visibility node {n.name} has an empty track.')
        if len(set(vals)) != 1:
            raise SystemExit(
                f'Visibility node {n.name} is animated ({sorted(set(vals))}); it '
                f'cannot be resized as a constant without inventing values.')
        if vals[0]:
            visible.append(n.name)
    if len(vis.nodes) != EXPECTED_VIS_NODES:
        raise SystemExit(
            f'Expected {EXPECTED_VIS_NODES} recipient visibility nodes, found '
            f'{len(vis.nodes)} in {VIS_SOURCE}')
    if tuple(sorted(visible)) != tuple(sorted(EXPECTED_VIS_VISIBLE)):
        raise SystemExit(
            f'Unexpected visible set {sorted(visible)}; expected '
            f'{sorted(EXPECTED_VIS_VISIBLE)}. The recipient model or the source '
            f'motion changed.')
    layout_id = visibility_layout_id(vis)
    if layout_id != VIS_LAYOUT:
        raise SystemExit(
            f'Visibility layout {layout_id} in {VIS_SOURCE.name}, expected '
            f'{VIS_LAYOUT}. The pinned source motion changed, so the visibility '
            f'this move ships would change with it.')

    if len(mat.nodes) != EXPECTED_MAT_NODES:
        raise SystemExit(
            f'Expected {EXPECTED_MAT_NODES} recipient material nodes, found '
            f'{len(mat.nodes)} in {VIS_SOURCE}')
    mat_names = tuple(sorted(n.name for n in mat.nodes))
    if mat_names != tuple(sorted(EXPECTED_MAT_NAMES)):
        raise SystemExit(
            f'Unexpected material nodes {list(mat_names)}; expected '
            f'{list(EXPECTED_MAT_NAMES)}.')
    mat_tracks = 0
    for n in mat.nodes:
        for t in n.tracks:
            mat_tracks += 1
            keys = {repr(const_key(v)) for v in (t.values or [])}
            if len(keys) != 1:
                raise SystemExit(
                    f'Material node {n.name} track {t.name} is animated; a '
                    f'material track cannot be retimed onto a donor clip of a '
                    f'different length without inventing values.')
    if mat_tracks != EXPECTED_MAT_TRACKS:
        raise SystemExit(
            f'Expected {EXPECTED_MAT_TRACKS} recipient material tracks, found '
            f'{mat_tracks} in {VIS_SOURCE}')
    return vis, mat, {
        'source': str(VIS_SOURCE),
        'source_alt': str(VIS_SOURCE_ALT),
        'source_sha256': sha256(VIS_SOURCE),
        'layout_id': layout_id,
        'node_count': len(vis.nodes),
        'node_names': [n.name for n in vis.nodes],
        'visible_nodes': sorted(visible),
        'material_node_count': len(mat.nodes),
        'material_track_count': mat_tracks,
        'material_node_names': list(mat_names),
        'material_fingerprint': values_fingerprint(mat.nodes),
    }


def build_group(src_group, frame_count):
    """Rebuild a constant group for a motion of `frame_count` frames."""
    nodes = []
    for n in src_group.nodes:
        tracks = []
        for t in n.tracks:
            keys = {repr(const_key(v)) for v in (t.values or [])}
            if len(keys) != 1:
                raise SystemExit(
                    f'{n.name}/{t.name} is not constant, so it cannot be '
                    f'resized to {frame_count} frames.')
            const = (t.values or [None])[0]
            tracks.append(s.anim_data.TrackData(
                t.name, t.compensate_scale, t.transform_flags,
                [const] * frame_count))
        nodes.append(s.anim_data.NodeData(n.name, tracks))
    src_group.nodes = nodes
    return src_group


def read_mesh_names():
    """Mesh object names of the recipient model, to sanity-check node names."""
    if not RECIPIENT_MESH.is_file():
        return None
    try:
        mesh = s.mesh_data.read_mesh(str(RECIPIENT_MESH))
    except Exception as exc:  # noqa: BLE001 - report, do not fail the build
        print(f'      Mesh-name cross-check skipped: {exc}')
        return None
    return {o.name for o in mesh.objects}


def retarget_motion(slot, donor_anim, recipient_clip, bone_names, mlist_donor):
    donor_path = DONOR_DIR / donor_anim
    if not donor_path.is_file():
        raise SystemExit(
            f'Missing donor animation: {donor_path}\n'
            f'Every clip this move needs was present in the dump when the tool '
            f'was written, and no pinned upstream of the clip *bytes* exists in '
            f'references/miiswordsman_special_hi (the manifest there pins the '
            f'motion-list YAML, which contains no .nuanmb). Fetching is therefore '
            f'not available: supply the dump rather than substituting a clip.')
    donor_hash = sha256(donor_path)
    if donor_hash != DONOR_SHA256[donor_anim]:
        raise SystemExit(
            f'{donor_anim}: sha256 {donor_hash} does not match the pinned '
            f'{DONOR_SHA256[donor_anim]}. The donor changed.')

    anim = s.anim_data.read_anim(str(donor_path))
    groups = groups_by_type(anim)
    donor_group_types = tuple(g.group_type.name for g in anim.groups)
    if donor_group_types != EXPECTED_DONOR_GROUPS:
        raise SystemExit(
            f'{donor_anim}: group list {list(donor_group_types)}, expected '
            f'{list(EXPECTED_DONOR_GROUPS)}. The donor carries no Material group '
            f'here, so the recipient group is the only possible source of one.')

    donor_nodes = list(groups['Transform'].nodes)
    donor_vis_nodes = len(groups['Visibility'].nodes)
    kept = [n for n in donor_nodes if n.name in bone_names]
    dropped = sorted(n.name for n in donor_nodes if n.name not in bone_names)
    if len(donor_nodes) != EXPECTED_DONOR_TRANSFORM_TRACKS:
        raise SystemExit(
            f'{donor_anim}: {len(donor_nodes)} transform tracks, expected '
            f'{EXPECTED_DONOR_TRANSFORM_TRACKS}')
    if len(kept) != EXPECTED_KEPT_TRACKS:
        raise SystemExit(
            f'{donor_anim}: {len(kept)} tracks survive bone-name intersection, '
            f'expected {EXPECTED_KEPT_TRACKS}')
    if dropped != sorted(EXPECTED_DROPPED_TRACKS):
        raise SystemExit(
            f'{donor_anim}: dropped {dropped}, expected '
            f'{sorted(EXPECTED_DROPPED_TRACKS)}. A silently different drop set '
            f'means the donor or the recipient skeleton changed.')

    donor_slot = DONOR_SLOT[donor_anim]
    donor_entry = mlist_donor.get(hash40(donor_slot))
    if donor_entry is None:
        raise SystemExit(f'Donor motion list has no entry for {donor_slot}')
    if donor_entry['animations'] != (hash40(donor_anim),):
        raise SystemExit(
            f'{donor_slot}: donor entry names '
            f'{[f"{a:#x}" for a in donor_entry["animations"]]}, expected '
            f'{donor_anim} ({hash40(donor_anim):#x})')

    frame_count = int(round(anim.final_frame_index)) + 1
    vis_src, mat_src, src_info = read_recipient_groups()
    vis_group = build_group(vis_src, frame_count)
    mat_group = build_group(mat_src, frame_count)

    groups['Transform'].nodes = kept
    # Transform, Visibility, Material is the order the recipient's own files use.
    anim.groups = [groups['Transform'], vis_group, mat_group]

    out_path = OUT_MOTION_DIR / recipient_clip
    anim.save(str(out_path))

    return {
        'slot': slot,
        'donor_slot': donor_slot,
        'donor_animation': donor_anim,
        'donor_path': str(donor_path),
        'donor_sha256': donor_hash,
        'recipient_animation': recipient_clip,
        'output_path': str(out_path),
        'final_frame_index': anim.final_frame_index,
        'clip_frames': frame_count,
        'group_track_length': frame_count,
        'donor_transform_tracks': len(donor_nodes),
        'output_transform_tracks': len(kept),
        'dropped_track_count': len(dropped),
        'dropped_tracks': dropped,
        'kept_bones': sorted(n.name for n in kept),
        'donor_visibility_nodes': donor_vis_nodes,
        'output_group_types': ['Transform', 'Visibility', 'Material'],
        'output_visibility_nodes': src_info['node_count'],
        'output_material_nodes': src_info['material_node_count'],
        'output_material_tracks': src_info['material_track_count'],
        'donor_fingerprint': values_fingerprint(donor_nodes),
        'retargeted_transform_fingerprint': values_fingerprint(kept),
        'retargeted_node_fingerprints': node_fingerprints(kept),
        'retargeted_node_series': node_series(kept),
        'output_group_constants': {
            'Visibility': node_constants(vis_group.nodes),
            'Material': node_constants(mat_group.nodes),
        },
        'source': src_info,
    }


def verify_written_clip(rec):
    """Read the file back and check it against what was intended.

    A successful `save` is not evidence of a correct file; this is.
    """
    out_path = Path(rec['output_path'])
    if not out_path.is_file():
        raise SystemExit(f'{out_path} was not written')
    anim = s.anim_data.read_anim(str(out_path))
    group_types = [g.group_type.name for g in anim.groups]
    if group_types != rec['output_group_types']:
        raise SystemExit(
            f"{out_path.name}: group list {group_types}, expected "
            f"{rec['output_group_types']}")
    groups = groups_by_type(anim)
    got_names = [n.name for n in groups['Transform'].nodes]
    if len(got_names) != len(rec['kept_bones']):
        raise SystemExit(
            f'{out_path.name}: {len(got_names)} transform tracks re-read, '
            f"expected {len(rec['kept_bones'])}")
    if sorted(got_names) != sorted(rec['kept_bones']):
        raise SystemExit(
            f'{out_path.name}: transform node names changed on the round trip')
    actual_nodes = node_fingerprints(groups['Transform'].nodes)
    intended_nodes = rec['retargeted_node_fingerprints']
    if set(actual_nodes) != set(intended_nodes):
        raise SystemExit(
            f'{out_path.name}: transform node names differ after the round trip: '
            f'missing {sorted(set(intended_nodes) - set(actual_nodes))[:8]}, '
            f'unexpected {sorted(set(actual_nodes) - set(intended_nodes))[:8]}')
    # A track whose values are all equal is written as a single value rather than
    # one value per frame, so its length does not survive the round trip. That is
    # the format, not a defect: the recipient's own clips read back the same way.
    # Collapsing both sides therefore compares what the file means; a real change
    # in the middle of an animated track still shows up.
    written_series = collapse_series(rec['retargeted_node_series'])
    reread_series = collapse_series(node_series(groups['Transform'].nodes))
    for name in sorted(written_series):
        difference = first_difference(name, written_series[name],
                                      reread_series[name])
        if difference:
            raise SystemExit(
                f'{out_path.name}: transform values changed on the round trip: '
                f'{difference}')
    max_transform_delta = max_component_delta(written_series, reread_series)
    if int(round(anim.final_frame_index)) != int(round(rec['final_frame_index'])):
        raise SystemExit(
            f"{out_path.name}: final_frame_index {anim.final_frame_index}, "
            f"expected {rec['final_frame_index']}")
    value_counts = set()
    for name, expected_nodes, expected_tracks, expected_constants in (
            ('Visibility', rec['output_visibility_nodes'],
             rec['output_visibility_nodes'],
             rec['output_group_constants']['Visibility']),
            ('Material', rec['output_material_nodes'],
             rec['output_material_tracks'],
             rec['output_group_constants']['Material'])):
        if name not in groups:
            raise SystemExit(f'{out_path.name}: no {name} group after the write')
        nodes = groups[name].nodes
        if len(nodes) != expected_nodes:
            raise SystemExit(
                f'{out_path.name}: {len(nodes)} {name} nodes, expected '
                f'{expected_nodes}')
        if {n.name for n in nodes} != set(expected_constants):
            raise SystemExit(
                f'{out_path.name}: {name} node names differ after the round trip')
        tracks = 0
        for n in nodes:
            if len(n.tracks) != len(expected_constants[n.name]):
                raise SystemExit(
                    f'{out_path.name}: {name} node {n.name} has {len(n.tracks)} '
                    f'tracks, expected {len(expected_constants[n.name])}')
            for t in n.tracks:
                tracks += 1
                values = t.values or []
                if not values:
                    raise SystemExit(
                        f'{out_path.name}: {name} node {n.name} track {t.name} '
                        f'has an empty track after the write')
                if len(values) > rec['group_track_length']:
                    raise SystemExit(
                        f'{out_path.name}: {name} node {n.name} track {t.name} '
                        f'has {len(values)} values, expected at most '
                        f"{rec['group_track_length']}")
                if len({repr(const_key(v)) for v in values}) != 1:
                    raise SystemExit(
                        f'{out_path.name}: {name} node {n.name} track {t.name} '
                        f'is not constant after the write')
                value_counts.add(len(values))
                difference = flat_difference(expected_constants[n.name][t.name],
                                             flat_values(values[0]))
                if difference:
                    raise SystemExit(
                        f'{out_path.name}: {name} node {n.name} track {t.name} '
                        f'holds {difference}')
        if tracks != expected_tracks:
            raise SystemExit(
                f'{out_path.name}: {tracks} {name} tracks, expected '
                f'{expected_tracks}')
    return {
        'output_bytes': out_path.stat().st_size,
        'output_sha256': sha256(out_path),
        'output_fingerprint': values_fingerprint(
            list(groups['Transform'].nodes) + list(groups['Visibility'].nodes)
            + list(groups['Material'].nodes)),
        'output_transform_tracks_reread': len(got_names),
        'output_visibility_nodes_reread': len(groups['Visibility'].nodes),
        'output_material_nodes_reread': len(groups['Material'].nodes),
        'output_material_tracks_reread': sum(
            len(n.tracks) for n in groups['Material'].nodes),
        # Measured: 1 per constant track, i.e. the writer collapsed the
        # frame-length values the source group was resized to.
        'constant_track_value_counts': sorted(value_counts),
        'max_transform_value_delta': max_transform_delta,
    }


def patch_motion_list():
    """Create/patch the mod output motion list and assert every change."""
    out_mlist = OUT_MOTION_DIR / 'motion_list.bin'
    if out_mlist.is_file():
        mlist_source = out_mlist
    else:
        mlist_source = next(
            (p for p in RECIPIENT_MLIST_FALLBACKS if p.is_file()), None)
        if mlist_source is None:
            raise SystemExit('No recipient motion_list.bin available')
        shutil.copy2(mlist_source, out_mlist)
    for path in RECIPIENT_MLIST_FALLBACKS:
        if sha256(path) != RECIPIENT_MLIST_SHA256:
            raise SystemExit(
                f'{path}: sha256 {sha256(path)} does not match the pinned '
                f'{RECIPIENT_MLIST_SHA256}. The recipient motion list changed, '
                f'so the slot metadata this tool patches may have moved.')
    print(f'      Motion-list baseline: {mlist_source}')

    baseline_bytes = out_mlist.read_bytes()
    magic, motion_path, baseline = parse_mlist(out_mlist)
    if encode_mlist(magic, motion_path, baseline) != baseline_bytes:
        raise SystemExit('Round-trip check failed on the recipient motion list')
    if len(baseline) != EXPECTED_MLIST_ENTRIES:
        raise SystemExit(
            f'{len(baseline)} motion entries, expected {EXPECTED_MLIST_ENTRIES}')

    # Prove both field locations against the donor's own list, whose slot
    # metadata is documented in motion_list_body_c00.yml (loop: true on
    # special_air_hi1_loop, cancel frame 45 on special_hi1_end), before writing
    # either value into the recipient's.
    _, _, donor_doc = parse_mlist(DONOR_MLIST)
    donor_loop = donor_doc[hash40('special_air_hi1_loop')]
    if not donor_loop['flags'] & LOOP_FLAG_BIT:
        raise SystemExit(
            f"Donor special_air_hi1_loop flags {donor_loop['flags']:#06x} do not "
            f'carry bit {LOOP_FLAG_BIT:#x}, so that bit is not the loop flag and '
            f'the recipient patch would write the wrong field.')
    donor_end = donor_doc[hash40('special_hi1_end')]
    if donor_end['cancel'] != END_CANCEL_FRAME:
        raise SystemExit(
            f"Donor special_hi1_end cancel frame {donor_end['cancel']}, expected "
            f'{END_CANCEL_FRAME}; the last-2 byte is not the cancel frame.')
    donor_sibling = donor_doc[hash40('special_air_hi1')]
    print(f"      Donor list proves the fields: special_air_hi1_loop flags "
          f"{donor_loop['flags']:#06x} (loop bit set), special_hi1_end cancel "
          f"{donor_end['cancel']}; sibling special_air_hi1 flags "
          f"{donor_sibling['flags']:#06x} without it")

    motions = dict(baseline)
    target_hashes = set()
    patches = []
    for slot, _, recipient_clip in MOTIONS:
        key = hash40(slot)
        target_hashes.add(key)
        entry = baseline.get(key)
        if entry is None:
            raise SystemExit(f'Recipient motion list has no entry for {slot}')
        if entry['animations'] != (hash40(recipient_clip),):
            raise SystemExit(
                f'{slot}: entry names '
                f'{[f"{a:#x}" for a in entry["animations"]]}, expected '
                f'{recipient_clip} ({hash40(recipient_clip):#x}); the clip this '
                f'tool writes would never be loaded.')
        raw = bytearray(entry['raw'])

        if slot == LOOP_SLOT:
            before = struct.unpack_from('<H', raw, MLIST_FLAGS_OFFSET)[0]
            if before not in (LOOP_FLAGS_BEFORE, LOOP_FLAGS_AFTER):
                raise SystemExit(
                    f'{slot}: flags {before:#06x} at offset '
                    f'{MLIST_FLAGS_OFFSET}, expected {LOOP_FLAGS_BEFORE:#06x} or '
                    f'{LOOP_FLAGS_AFTER:#06x}; rejecting an unexpected value '
                    f'rather than overwriting it')
            already = before == LOOP_FLAGS_AFTER
            after = before | LOOP_FLAG_BIT
            if after != LOOP_FLAGS_AFTER:
                raise SystemExit(
                    f'{slot}: setting the loop bit gave {after:#06x}, expected '
                    f'{LOOP_FLAGS_AFTER:#06x}; the recipient entry carries flags '
                    f'this patch does not account for')
            struct.pack_into('<H', raw, MLIST_FLAGS_OFFSET, after)
            patches.append({
                'slot': slot, 'field': 'flags', 'offset': MLIST_FLAGS_OFFSET,
                'before': f'{before:#06x}', 'after': f'{after:#06x}',
                'bit_set': f'{LOOP_FLAG_BIT:#06x}', 'already_applied': already,
                'why': ('loop: true. The donor slot special_air_hi1_loop carries '
                        'it, the recipient slot does not, and the ported Loop '
                        'status never tests MotionModule::is_end(), so a six-frame '
                        'clip without it plays once and holds its final frame.'),
            })

        if slot == END_SLOT:
            before = entry['cancel']
            if before not in (END_CANCEL_BEFORE, END_CANCEL_FRAME):
                raise SystemExit(
                    f'{slot}: cancel frame {before}, expected '
                    f'{END_CANCEL_BEFORE} or {END_CANCEL_FRAME}; rejecting an '
                    f'unexpected value rather than overwriting it')
            if entry['size'] % 8 != 4:
                raise SystemExit(
                    f"{slot}: entry size {entry['size']} does not carry a cancel "
                    f'field (last-2 byte), so 45 cannot be written')
            already = before == END_CANCEL_FRAME
            raw[-2] = END_CANCEL_FRAME
            patches.append({
                'slot': slot, 'field': 'cancel_frame',
                'offset_from_end': -2,
                'before': before, 'after': END_CANCEL_FRAME,
                'already_applied': already,
                'why': ('cancel_frame: 45, the donor value. The recipient slot is '
                        '0, so the interrupt window the donor End phase has would '
                        'be lost.'),
            })

        patched = dict(entry)
        patched['raw'] = bytes(raw)
        if slot == LOOP_SLOT:
            patched['flags'] = struct.unpack_from('<H', raw, MLIST_FLAGS_OFFSET)[0]
        if slot == END_SLOT:
            patched['cancel'] = raw[-2]
        # Replacing an existing key keeps its position, so entry order is stable
        # and the unrelated entries stay where they are.
        motions[key] = patched

    result_bytes = encode_mlist(magic, motion_path, motions)
    out_mlist.write_bytes(result_bytes)
    _, _, check = parse_mlist(out_mlist)
    if check != motions:
        raise SystemExit('Re-parsed motion list does not match what was written')
    if check[hash40(LOOP_SLOT)]['flags'] != LOOP_FLAGS_AFTER:
        raise SystemExit(
            f"Written {LOOP_SLOT} flags are "
            f"{check[hash40(LOOP_SLOT)]['flags']:#06x}, expected "
            f'{LOOP_FLAGS_AFTER:#06x}')
    if check[hash40(END_SLOT)]['cancel'] != END_CANCEL_FRAME:
        raise SystemExit(
            f'Written {END_SLOT} cancel frame is '
            f"{check[hash40(END_SLOT)]['cancel']}, expected {END_CANCEL_FRAME}")

    # Everything except the two patched entries must be byte-identical to the
    # baseline. Only LOOP_SLOT and END_SLOT are patched, so the three other
    # target slots - whose animation names were asserted above - are covered by
    # this check as well.
    patched_hashes = {hash40(LOOP_SLOT), hash40(END_SLOT)}
    for kind, entry in baseline.items():
        if kind in patched_hashes:
            continue
        if check[kind]['raw'] != entry['raw']:
            raise SystemExit(
                f'Unrelated motion-list entry {kind:#x} changed byte-wise')
    unchanged = sum(1 for k, v in baseline.items()
                    if k not in patched_hashes and check[k]['raw'] == v['raw'])
    expected_unchanged = len(baseline) - len(patched_hashes)
    if unchanged != expected_unchanged:
        raise SystemExit(
            f'{unchanged} unrelated entries byte-identical, expected '
            f'{expected_unchanged}')

    # Each patched entry must differ from the baseline at exactly the intended
    # byte offsets and nowhere else.
    for patch in patches:
        entry = baseline[hash40(patch['slot'])]
        written = check[hash40(patch['slot'])]['raw']
        diffs = [i for i in range(len(entry['raw']))
                 if entry['raw'][i] != written[i]]
        if patch['field'] == 'flags':
            # Only the bytes the flag word actually moves may differ: raising
            # 0x0080 to 0x0082 changes the low byte and leaves the high byte at
            # zero. Byte 17 is in the expected set precisely when it changes.
            before_bytes = struct.pack('<H', int(patch['before'], 16))
            after_bytes = struct.pack('<H', int(patch['after'], 16))
            intended = {MLIST_FLAGS_OFFSET + i for i in range(2)
                        if before_bytes[i] != after_bytes[i]}
        elif patch['before'] != patch['after']:
            intended = {len(entry['raw']) - 2}
        else:
            intended = set()
        if patch['already_applied']:
            intended = set()
        if set(diffs) != intended:
            raise SystemExit(
                f"{patch['slot']}: patched entry differs at bytes {diffs}, "
                f'expected exactly {sorted(intended)}')
        patch['differing_byte_offsets'] = diffs

    print(f'      {len(patches)} patches applied; {unchanged} unrelated entries '
          f'byte-identical to baseline')
    return {
        'baseline_source': str(mlist_source),
        'baseline_bytes': len(baseline_bytes),
        'baseline_sha256': hashlib.sha256(baseline_bytes).hexdigest(),
        'output_path': str(out_mlist),
        'output_bytes': len(result_bytes),
        'output_sha256': sha256(out_mlist),
        'entry_count': len(motions),
        'unrelated_entries_unchanged': unchanged,
        'expected_unrelated_entries': expected_unchanged,
        'patches': patches,
    }


def build_assets():
    OUT_MOTION_DIR.mkdir(parents=True, exist_ok=True)
    own_outputs = {clip for _, _, clip in MOTIONS} | {'motion_list.bin'}

    print('[1/6] Reading the recipient skeleton and validating the group source...')
    if not RECIPIENT_SKEL.is_file():
        raise SystemExit(f'Missing recipient skeleton: {RECIPIENT_SKEL}')
    if sha256(RECIPIENT_SKEL) != RECIPIENT_SKEL_SHA256:
        raise SystemExit(
            f'{RECIPIENT_SKEL}: sha256 {sha256(RECIPIENT_SKEL)} does not match '
            f'the pinned {RECIPIENT_SKEL_SHA256}')
    bone_names = [b.name for b in s.skel_data.read_skel(str(RECIPIENT_SKEL)).bones]
    bone_set = set(bone_names)
    if len(bone_names) != EXPECTED_RECIPIENT_BONES:
        raise SystemExit(
            f'elight c07 skeleton has {len(bone_names)} bones, expected '
            f'{EXPECTED_RECIPIENT_BONES}')
    print(f'      elight c07 skeleton: {len(bone_names)} bones from '
          f'{RECIPIENT_SKEL}')
    _, _, src_info = read_recipient_groups()
    print(f"      Group source: {VIS_SOURCE.name} layout {src_info['layout_id']} "
          f"({src_info['node_count']} visibility nodes, constant, visible: "
          f"{src_info['visible_nodes']}; material "
          f"{src_info['material_node_count']} nodes / "
          f"{src_info['material_track_count']} tracks, constant)")

    mesh_names = read_mesh_names()
    vis_names = set(src_info['node_names'])
    if mesh_names is None:
        print('      Mesh-name cross-check unavailable; node names trusted.')
    else:
        shared = sorted(vis_names & mesh_names)
        # Reported, not asserted: whether the visibility node names line up with
        # mesh object names is a property of this model's naming, and the group is
        # copied from the recipient's own motion, so it is consistent with the
        # recipient model by construction.
        print(f'      mesh objects: {len(mesh_names)}, visibility node names '
              f'checked: {len(vis_names)}, names in both: {len(shared)}'
              + (f' {shared[:6]}' if shared else
                 ' (visibility nodes are not mesh object names in this model)'))

    print('[2/6] Validating the recipient slots and the output folder...')
    for slot, donor_anim, recipient_clip in MOTIONS:
        if not (RECIPIENT_MOTION_DIR / recipient_clip).is_file():
            raise SystemExit(
                f'{slot}: {recipient_clip} is not in {RECIPIENT_MOTION_DIR}, so '
                f'the slot names an animation the base install does not have')
        if donor_anim == recipient_clip:
            raise SystemExit(f'{slot}: donor and recipient clip are the same name')
    collisions = sorted(set(FOREIGN_OWNED) & {c for _, _, c in MOTIONS})
    if collisions:
        raise SystemExit(
            f'This tool would overwrite files another tool owns: {collisions}')
    # Only donor names that are not also recipient names are suspect: the donor's
    # d02specialairhi1.nuanmb and the recipient's special_air_hi1 clip share a
    # file name, because the two fighters name their up-B clips the same way.
    donor_only = sorted(p.name for p in OUT_MOTION_DIR.glob('*.nuanmb')
                        if p.name in DONOR_SHA256 and p.name not in own_outputs)
    if donor_only:
        raise SystemExit(
            f'Donor-only animation names left in the output folder: '
            f'{donor_only}. This move introduces no new animation name; no slot '
            f'references those files and they are not cleaned up automatically.')
    pre_existing = {p.name: sha256(p) for p in sorted(OUT_MOTION_DIR.iterdir())
                    if p.is_file() and p.name not in own_outputs}
    print(f'      {len(MOTIONS)} recipient slots validated; pre-existing files '
          f'this tool does not own: {sorted(pre_existing)}')

    print('[3/6] Retargeting donor transform tracks by bone-name intersection...')
    _, _, donor_doc = parse_mlist(DONOR_MLIST)
    records = []
    for slot, donor_anim, recipient_clip in MOTIONS:
        rec = retarget_motion(slot, donor_anim, recipient_clip, bone_set, donor_doc)
        records.append(rec)
        print(f"      {slot:<24} kept {rec['output_transform_tracks']:>2} / "
              f"dropped {rec['dropped_track_count']:>2}  frames "
              f"{rec['clip_frames']:>3}  -> {recipient_clip} "
              f"(from {donor_anim})")

    # Distinctness must be tested as information loss, not as raw inequality: two
    # donor motions that are already identical across all 75 tracks are allowed to
    # stay identical, but the drop must not discard the only difference between
    # two donor-distinct motions or two phases would play the same animation.
    fps = {}
    donor_of = {}
    for rec in records:
        fps.setdefault(rec['retargeted_transform_fingerprint'], []).append(
            rec['slot'])
        donor_of[rec['slot']] = rec['donor_fingerprint']
    donor_identical = []
    lost = {}
    for key, slots in ((k, v) for k, v in fps.items() if len(v) > 1):
        if len({donor_of[s] for s in slots}) == 1:
            donor_identical.append(slots)
        else:
            lost[key] = slots
    for slots in donor_identical:
        print(f'      {" and ".join(slots)} are identical in the donor across '
              f'all {EXPECTED_DONOR_TRANSFORM_TRACKS} tracks, so the drop did '
              f'not discard a difference between them. Allowed.')
    if lost:
        raise SystemExit(
            f'The drop discarded the only difference between these slots, so '
            f'they would play as the same animation: {lost}. That is a '
            f'retargeting defect, not a property of the donor.')
    print(f'      Distinct phases: {len(fps)} fingerprints for {len(records)} '
          f'slots ({len(donor_identical)} legitimately shared)')

    covered = {name for rec in records for name in rec['kept_bones']}
    uncovered = sorted(set(bone_names) - covered)
    print(f'      elight c07 bones with no donor track: {len(uncovered)} of '
          f'{len(bone_names)}; they hold their rest pose through the move '
          f'(the Mii has no track for Mythra-only finger, hair, sword or '
          f'expression bones)')

    print('[4/6] Patching the two slot metadata fixes and asserting them...')
    mlist_info = patch_motion_list()
    for patch in mlist_info['patches']:
        state = 'already applied' if patch['already_applied'] else 'applied'
        print(f"      {patch['slot']:<24} {patch['field']:<12} "
              f"{patch['before']} -> {patch['after']} ({state})")

    print('[5/6] Reading every written clip back and re-checking it...')
    for rec in records:
        rec.update(verify_written_clip(rec))
        print(f"      {rec['recipient_animation']:<28} "
              f"{rec['output_bytes']:>7} bytes  transform "
              f"{rec['output_transform_tracks_reread']:>2}  visibility "
              f"{rec['output_visibility_nodes_reread']:>2}  material "
              f"{rec['output_material_nodes_reread']} nodes / "
              f"{rec['output_material_tracks_reread']} tracks  "
              f"sha256 {rec['output_sha256'][:16]}")

    # Nothing else in the output folder may have moved.
    for name, digest in pre_existing.items():
        path = OUT_MOTION_DIR / name
        if not path.is_file():
            raise SystemExit(f'Pre-existing file {name} disappeared')
        if sha256(path) != digest:
            raise SystemExit(f'Unrelated output file {name} changed')

    # The per-node value series and the per-clip copy of the group source are
    # comparison inputs, not manifest content: between them they run to tens of
    # thousands of numbers, and the same facts are pinned by the hashes, track
    # counts and fingerprints recorded below.
    for rec in records:
        for key in ('retargeted_node_series', 'output_group_constants', 'source'):
            rec.pop(key, None)

    print('[6/6] Writing the manifest...')
    manifest = {
        'generated_by':
            'mod_files/mythra_gamewatch_swap/tools/build_hero_spin_assets.py',
        'purpose': (
            'Retarget Mii Swordfighter Hero Spin (up-B) motions onto elight c07 '
            'by bone-name intersection, replacing the recipient slots\' own '
            'vanilla clips. No animation name is introduced and no carrier is '
            'repointed: every slot written already exists in the base install.'),
        'evidence': {
            'plan': ('references/miiswordsman_special_hi/PLAN.md '
                     '(sections 2, 3, 12, 13)'),
            'donor_slot_metadata': (
                'references/miiswordsman_special_hi/motion_list_body_c00.yml '
                '(fetched from WuBoytH/SSBU-Dumped-Motion-Lists at '
                '3f14a9d46b69eb9e7cd622bddde459192848580e)'),
            'recipient_slot_metadata': (
                'references/mythra_ftilt/elight_body_motion_list.yml (elight body '
                'c00; the dump\'s elight c07 and c00 motion_list.bin are '
                'byte-identical)'),
        },
        'recipient': {
            'fighter': 'elight',
            'slot': 'c07',
            'skeleton': str(RECIPIENT_SKEL),
            'skeleton_sha256': RECIPIENT_SKEL_SHA256,
            'bone_count': len(bone_names),
            'bones': bone_names,
        },
        'donor': {
            'fighter': 'miiswordsman',
            'motion_dir': str(DONOR_DIR),
            'motion_list': str(DONOR_MLIST),
            'motion_list_sha256': sha256(DONOR_MLIST),
            'clip_sha256': DONOR_SHA256,
        },
        'binding_semantics': (
            'Recipient animation node order is alphabetical, skeleton order is '
            'hierarchical, so transform binding is by node name, not index.'),
        'visibility_group': {
            'source': src_info['source'],
            'source_alt_identical': src_info['source_alt'],
            'source_sha256': src_info['source_sha256'],
            'layout_id': src_info['layout_id'],
            'node_count': src_info['node_count'],
            'node_names': src_info['node_names'],
            'visible_nodes': src_info['visible_nodes'],
            'material_source': src_info['source'],
            'material_node_count': src_info['material_node_count'],
            'material_track_count': src_info['material_track_count'],
            'material_node_names': src_info['material_node_names'],
            'material_values_fingerprint': src_info['material_fingerprint'],
            'rationale': (
                'The donor carries Transform + Visibility only, and its '
                'visibility names the Mii\'s meshes, so both recipient groups are '
                'replaced from the recipient\'s own default standing motion. That '
                'clip is constant in both groups, which is what allows it to be '
                'resized to a clip of any length without inventing values.'),
            'rejected_alternative': (
                'The recipient\'s own up-B family (d02specialhi*, layout '
                'dee56b0400c5, 34 visibility nodes) matches the slot being '
                'written, but it animates 2 of those visibility tracks '
                '(eflame_Mouth_Heavyattack, eflame_Mouth_Talk) and 2 material '
                'tracks (CustomVector31 on EyeL and EyeR), so it cannot be '
                'retimed onto a donor clip of a different length without '
                'inventing values. Those two animated recipient tracks are '
                'therefore not reproduced; the meshes they drive hold the '
                'constant values the recipient\'s own idle also uses. Recorded '
                'as a limitation, not asserted away.'),
        },
        'motion_list': mlist_info,
        'motions': records,
        'assertions': {
            'donor_transform_tracks_per_motion': EXPECTED_DONOR_TRANSFORM_TRACKS,
            'kept_tracks_per_motion': EXPECTED_KEPT_TRACKS,
            'dropped_tracks': sorted(EXPECTED_DROPPED_TRACKS),
            'distinct_phases': f'{len(fps)} fingerprints for {len(records)} slots',
            'donor_identical_phases': donor_identical,
            'recipient_bones': len(bone_names),
            'recipient_bones_covered_by_a_donor_track': len(covered),
            'recipient_bones_without_donor_track': uncovered,
            'loop_slot': {
                'slot': LOOP_SLOT,
                'flag_bit': f'{LOOP_FLAG_BIT:#06x}',
                'before': f'{LOOP_FLAGS_BEFORE:#06x}',
                'after': f'{LOOP_FLAGS_AFTER:#06x}',
                'proved_against_donor': (
                    f"donor special_air_hi1_loop flags "
                    f"{donor_doc[hash40('special_air_hi1_loop')]['flags']:#06x}"),
            },
            'end_slot': {
                'slot': END_SLOT,
                'cancel_frame': END_CANCEL_FRAME,
                'before': END_CANCEL_BEFORE,
                'proved_against_donor': (
                    f"donor special_hi1_end cancel "
                    f"{donor_doc[hash40('special_hi1_end')]['cancel']}"),
            },
            'written_clips_reread': True,
            'unrelated_motion_entries_byte_identical':
                mlist_info['unrelated_entries_unchanged'],
            'unrelated_output_files_unchanged': sorted(pre_existing),
        },
        'not_applied_deliberately': [{
            'field': ('xlu_start / xlu_end on special_hi_start and '
                      'special_air_hi_start'),
            'reason': (
                'PLAN.md section 12 records the donor fading the model in over '
                'frames 5 to 13 and the recipient slots at 0/0. That is a design '
                'decision for the port, not one of the two measured mismatches '
                'this tool was asked to fix, so it is recorded here and left '
                'alone rather than decided silently.'),
        }],
        'open_items': [
            'The recipient\'s esword motion list has no up-B entries, so no sword '
            'clip is written; how the Aegis sword behaves during the spin is a '
            'Switch observation, not something the donor can answer.',
            'The two animated recipient visibility tracks and two animated '
            'material tracks of the vanilla up-B family are not reproduced; see '
            'visibility_group.rejected_alternative.',
        ],
        'files': {
            **{r['recipient_animation']: r['output_sha256'] for r in records},
            'motion_list.bin': mlist_info['output_sha256'],
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Wrote {MANIFEST}')
    print('\n[SUCCESS] Hero Spin motions retargeted and packaged.')
    return manifest


if __name__ == '__main__':
    build_assets()
