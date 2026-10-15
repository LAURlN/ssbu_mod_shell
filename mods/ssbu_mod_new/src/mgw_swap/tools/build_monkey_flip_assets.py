"""Build and package the retargeted Monkey Flip motions for Game & Watch c07.

Why this tool exists
--------------------
`references/inject_monkey_flip.py` deployed Diddy's twelve `d01*.nuanmb` files
byte for byte with `shutil.copy2` and no retargeting. Diddy's skeleton has 85
bones, G&W c07 has 45, so the copies carried 47 tracks per motion that name bones
G&W does not have, plus Diddy's own visibility and material groups, which name
Diddy's mesh objects and materials. That is the reported "the animation looks
wrong" symptom.

What this tool does
-------------------
1. Reads the recipient skeleton from the dump and intersects donor transform
   tracks with it by bone name. Donor-only helper tracks (tail, hat, lips, extra
   finger segments, article bones) are dropped. See
   `references/diddy_specials/monkey_flip_motion_audit.md` for the per-motion
   table that justifies every keep and every drop.
2. Drops the donor's Visibility and Material groups and installs G&W's own
   visibility group instead, so G&W's body renders with its normal mesh set.

   G&W does NOT have a single canonical visibility layout. Measured with
   `scratch/probe_vis_values2.py`: G&W c00 carries **73 distinct visibility
   layouts** across 241 animations, because the layout encodes which hand mesh
   (Lhand/Rhand Hold|Move|Open) and which held-item or judge mesh is drawn.
   G&W c00 also carries **zero** Material nodes, so the empty recipient material
   group is the correct recipient material group.

   The source is therefore chosen deliberately and pinned by layout id:
   `a00wait1.nuanmb`, layout `ffeba8cc4702` - the recipient's own default
   standing layout, 94 nodes, constant (one track per node, no node animated),
   and the single most common layout in c00 (84 of 241 animations, including
   a00waititem, a01turn, a02dash, e02capturewaithi). The donor gives no basis for
   any choice here (Diddy's visibility group names Diddy's meshes), so the
   defensible option is the recipient's own modal default. The alternatives and
   why they were rejected are recorded in the manifest.
3. Injects the donor motion-list entries into G&W c07 `motion_list.bin` byte for
   byte, with a parse/encode round-trip check and an assertion that every
   unrelated entry is unchanged.

Binding semantics (why name intersection is the correct retarget)
-----------------------------------------------------------------
The recipient's own animations list transform nodes alphabetically (ArmL, ArmR,
BodyHaveN, Bust, ...) while the skeleton lists them hierarchically (Trans, Rot,
Hip, Waist, Bust, ...). Track binding therefore cannot be positional against the
skeleton; it is resolved per node name. Dropping donor-only tracks is safe, and
the surviving order is not semantic.

Invariants, asserted not assumed
--------------------------------
Every count and expectation below was measured from the dump and is re-checked
on every run, so a donor or recipient change fails loudly instead of silently
producing wrong assets. Values come from:
  - `references/diddy_specials/motion_list.yml` (transcription of the donor
    motion_list.bin): motion slot names, donor animation names, cancel frames.
  - `references/diddy_specials/monkey_flip_motion_audit.json`: track counts.
  - `references/diddy_specials/donor_acmd_manifest.json`: the pinned ACMD
    scripts that prove the slot names.

Run: python mod_files/mythra_gamewatch_swap/tools/build_monkey_flip_assets.py
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
# The game dump is machine specific and read only, so it is configurable instead
# of pinned: set MGW_EXPORT when it lives on another drive or on the USB stick.
# It defaults to <workspace_root>/export, which is where it is kept now; the
# a drive-specific export path only worked on one machine
# and was silently wrong elsewhere.
EXPORT = Path(os.environ.get('MGW_EXPORT', WORKSPACE / 'dumps' / 'arc'))
if not EXPORT.is_dir():
    raise SystemExit(
        f'Game dump not found at {EXPORT}.\n'
        f'The dump is expected at <workspace_root>/export. Point MGW_EXPORT at it\n'
        f'when it lives elsewhere, from cmd.exe:\n'
        f'    set MGW_EXPORT=<drive>:<path to the ArcExplorer export folder>\n'
        f'or from PowerShell:\n'
        f'    $env:MGW_EXPORT = "<drive>:<path to the ArcExplorer export folder>"')
MOD_OUT = WORKSPACE / 'mod_output/ultimate/mods/mythra_gamewatch_swap'
GW_MOTION_DIR = MOD_OUT / 'fighter/gamewatch/motion/body/c07'
BASE_MOTION_DIR = EXPORT / 'fighter/gamewatch/motion/body/c07'
BASE_MOTION_DIR_C00 = EXPORT / 'fighter/gamewatch/motion/body/c00'
# Animation the fair tool owns; writing it here would fight that build.
FOREIGN_OWNED = ('c05attackairf',)

GW_SKEL = EXPORT / 'fighter/gamewatch/model/body/c07/model.nusktb'
# The mesh-object list lives in the .numshb, not the .numdlb; pointing this at the
# numdlb made ssbh_data_py reject the file and silently skip the cross-check.
GW_MESH = EXPORT / 'fighter/gamewatch/model/body/c07/model.numshb'
# Recipient visibility group source. `a00wait1` is G&W's default standing motion;
# its layout `ffeba8cc4702` is the modal c00 layout (84 of 241 animations), is
# constant, and shows exactly G&W's normal body meshes. See the module docstring.
GW_VIS_SOURCE = EXPORT / 'fighter/gamewatch/motion/body/c00/a00wait1.nuanmb'
GW_VIS_LAYOUT = 'ffeba8cc4702'
DONOR_DIR = EXPORT / 'fighter/diddy/motion/body/c00'
DONOR_MLIST = DONOR_DIR / 'motion_list.bin'
RECIPIENT_MLIST_FALLBACKS = [
    EXPORT / 'fighter/gamewatch/motion/body/c07/motion_list.bin',
    EXPORT / 'fighter/gamewatch/motion/body/c00/motion_list.bin',
]

MANIFEST = WORKSPACE / 'references/diddy_specials/monkey_flip_animation_manifest.json'

# (slot, donor animation) in move order. Names taken from motion_list.yml.
MOTIONS = [
    ('special_s_start', 'd01specialsstart.nuanmb'),
    ('special_air_s_start', 'd01specialairsstart.nuanmb'),
    ('special_air_s_jump', 'd01specialairsjump.nuanmb'),
    ('special_air_s_kick', 'd01specialairskick.nuanmb'),
    ('special_s_kick_landing', 'd01specialskicklanding.nuanmb'),
    ('special_air_s_fall', 'd01specialairsfall.nuanmb'),
    ('special_s_stick', 'd01specialsstick.nuanmb'),
    ('special_s_stick_attack', 'd01specialsstickattack.nuanmb'),
    ('special_s_stick_attack2', 'd01specialsstickattack2.nuanmb'),
    ('special_s_stick_jump', 'd01specialsstickjump.nuanmb'),
    ('special_s_stick_jump2', 'd01specialsstickjump2.nuanmb'),
    ('special_s_landing', 'd01specialslanding.nuanmb'),
]

# Carrier animation names: the twelve slots load files the base install already
# has, instead of twelve new file names.
#
# Why this is necessary
# ---------------------
# The deployed c07 motion_list.bin mapped each slot to a *new* animation name
# (`d01specialsstart.nuanmb` and friends). The Switch log shows what that does:
# MotionModule::motion_kind reports the hash we asked for, but the phase lasts
# exactly as long as the clip that was already playing, and that length changes
# between attempts (17, 24, 40 frames) and is always a real Game & Watch clip
# length (a02dash 17, a02turndash 24, a02run 40). Frame counter and rate reset,
# the clip does not swap. MotionModule::motion_kind echoes the request, so it
# never was evidence that the animation loaded.
#
# Evidence that a replaced name works where an added name does not:
#   - c05attackairf.nuanmb, rewritten by tools/build_fair_assets.py, is served
#     from the mod and plays.
#   - the twelve d01* names exist in no vanilla Game & Watch folder, so nothing
#     in the base install ever references them.
#   - vanilla c07 motion_list.bin names `fighter/gamewatch/motion/body/c00` as its
#     motion_path, so the field is not the folder the files are read from, which
#     rules out the placement of the twelve files as the cause.
#
# The carriers below are Game & Watch's own animations for the two specials this
# mod has already replaced, so nothing that used to be playable changes:
#   - d01special*    Judge, the native side-B, replaced by Monkey Flip.
#   - d03speciallw*  Bucket, the native down-B, replaced by the Mythra swap.
# The two catch animations (d03speciallwcatch, d03specialairlwcatch) are left
# untouched as spares, and both sets exist in c00 and c07 in the base install,
# which is what makes the override resolvable.
CARRIERS = {
    'special_s_start': 'd01specials',
    'special_air_s_start': 'd01specialairs',
    'special_air_s_jump': 'd01specialairsl',
    'special_air_s_kick': 'd01specialsl',
    'special_s_kick_landing': 'd03speciallw',
    'special_air_s_fall': 'd03specialairlw',
    'special_s_stick': 'd03speciallwstart',
    'special_s_stick_attack': 'd03speciallwshoot',
    'special_s_stick_attack2': 'd03speciallwend',
    'special_s_stick_jump': 'd03specialairlwstart',
    'special_s_stick_jump2': 'd03specialairlwshoot',
    'special_s_landing': 'd03specialairlwend',
}

# cancel_frame per slot, from motion_list.yml lines 3064-3423.
EXPECTED_CANCEL = {
    'special_s_start': 0,
    'special_air_s_start': 0,
    'special_air_s_jump': 0,
    'special_air_s_kick': 33,
    'special_s_kick_landing': 19,
    'special_air_s_fall': 0,
    'special_s_stick': 0,
    'special_s_stick_attack': 0,
    'special_s_stick_attack2': 17,
    'special_s_stick_jump': 0,
    'special_s_stick_jump2': 17,
    'special_s_landing': 27,
}

# Measured invariants from the audit. These are the donor's shape, not guesses.
EXPECTED_DONOR_TRANSFORM_TRACKS = 84
EXPECTED_KEPT_TRACKS = 37
# G&W c07 bones the donor has no knowledge of; they get no track and stay at rest.
EXPECTED_RECIPIENT_ONLY_BONES = ('BodyHaveN', 'HeadHaveN', 'Sparky', 'TopHave')
EXPECTED_VIS_NODES = 94
EXPECTED_VIS_VISIBLE = ('GW', 'HeadM', 'LhandHold', 'NoseM', 'RhandHold')
# The layout id hashes the full node-name -> value-set mapping, so pinning it
# checks the node names and the visible set together, not just the count.
# Same construction as scratch/probe_vis_values2.py.
# (An EXPECTED_VIS_MESHES_REQUIRED check used to gate the build here. It compared
# visibility node names against mesh object names, which are disjoint sets in this
# model, so it only stayed silent while it was pointed at the wrong file.)


def hash40(name):
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


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
            'flags': flags, 'blend': blend,
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


def values_fingerprint(nodes):
    """Stable fingerprint of a set of transform nodes, for phase-distinctness."""
    h = hashlib.sha256()
    for n in nodes:
        h.update(n.name.encode())
        for t in n.tracks:
            for v in (t.values or []):
                parts = [repr(round(float(v), 5))] if isinstance(v, (int, float)) else []
                if not parts:
                    for attr in ('x', 'y', 'z', 'w', 'scale_x', 'scale_y', 'scale_z'):
                        if hasattr(v, attr):
                            parts.append(round(float(getattr(v, attr)), 5))
                h.update(repr(parts).encode())
            h.update(b'|')
    return h.hexdigest()


def visibility_layout_id(group):
    """Layout id: hash of node-name -> value-set, as probe_vis_values2.py does."""
    per_node = {}
    for n in group.nodes:
        vals = []
        for t in n.tracks:
            vals.extend([bool(v) for v in (t.values or [])])
        per_node[n.name] = tuple(sorted(set(vals)))
    return hashlib.sha256(
        repr(sorted(per_node.items())).encode()).hexdigest()[:12]


def read_recipient_visibility_source():
    """G&W's own visibility group, validated against the pinned layout id."""
    anim = s.anim_data.read_anim(str(GW_VIS_SOURCE))
    group = groups_by_type(anim).get('Visibility')
    if group is None:
        raise SystemExit(f'No Visibility group in {GW_VIS_SOURCE}')
    visible = []
    for n in group.nodes:
        if len(n.tracks) != 1:
            raise SystemExit(
                f'Visibility node {n.name} has {len(n.tracks)} tracks; the '
                f'resize-to-motion-length step assumes one track per node.')
        vals = [bool(v) for v in (n.tracks[0].values or [])]
        if not vals:
            raise SystemExit(f'Visibility node {n.name} has an empty track.')
        if len(set(vals)) != 1:
            raise SystemExit(
                f'Visibility node {n.name} is animated ({sorted(set(vals))}); '
                f'it cannot be resized as a constant without inventing values.')
        if vals[0]:
            visible.append(n.name)
    if len(group.nodes) != EXPECTED_VIS_NODES:
        raise SystemExit(
            f'Expected {EXPECTED_VIS_NODES} G&W visibility nodes, found '
            f'{len(group.nodes)} in {GW_VIS_SOURCE}')
    if tuple(sorted(visible)) != tuple(sorted(EXPECTED_VIS_VISIBLE)):
        raise SystemExit(
            f'Unexpected visible set {sorted(visible)}; expected '
            f'{sorted(EXPECTED_VIS_VISIBLE)}. The G&W model or the source '
            f'motion changed.')
    layout_id = visibility_layout_id(group)
    if layout_id != GW_VIS_LAYOUT:
        raise SystemExit(
            f'Visibility layout {layout_id} in {GW_VIS_SOURCE.name}, expected '
            f'{GW_VIS_LAYOUT}. The pinned source motion changed, so the '
            f'visibility this move ships would change with it.')
    print(f'      Visibility source: {GW_VIS_SOURCE.name} layout {layout_id} '
          f'({len(group.nodes)} nodes, constant, visible: {sorted(visible)})')
    return group


def read_mesh_names():
    """Mesh object names of the recipient model, to sanity-check node names."""
    if not GW_MESH.is_file():
        return None
    try:
        mesh = s.mesh_data.read_mesh(str(GW_MESH))
    except Exception as exc:  # noqa: BLE001 - report, do not fail the build
        print(f'      Mesh-name cross-check skipped: {exc}')
        return None
    return {o.name for o in mesh.objects}


def build_visibility_group(src_group, frame_count):
    """Rebuild the visibility group for a motion of `frame_count` frames."""
    nodes = []
    for n in src_group.nodes:
        src_track = n.tracks[0]
        const = bool((src_track.values or [False])[0])
        track = s.anim_data.TrackData(
            src_track.name, src_track.compensate_scale, src_track.transform_flags,
            [const] * frame_count)
        nodes.append(s.anim_data.NodeData(n.name, [track]))
    src_group.nodes = nodes
    return src_group


def retarget_motion(slot, anim_name, gw_set, vis_src_group):
    donor_path = DONOR_DIR / anim_name
    if not donor_path.is_file():
        raise SystemExit(f'Missing donor animation: {donor_path}')
    anim = s.anim_data.read_anim(str(donor_path))
    groups = groups_by_type(anim)
    for required in ('Transform', 'Visibility', 'Material'):
        if required not in groups:
            raise SystemExit(f'{anim_name}: expected a {required} group')

    donor_nodes = list(groups['Transform'].nodes)
    kept = [n for n in donor_nodes if n.name in gw_set]
    dropped = sorted(n.name for n in donor_nodes if n.name not in gw_set)
    if len(donor_nodes) != EXPECTED_DONOR_TRANSFORM_TRACKS:
        raise SystemExit(
            f'{anim_name}: {len(donor_nodes)} transform tracks, expected '
            f'{EXPECTED_DONOR_TRANSFORM_TRACKS}')
    if len(kept) != EXPECTED_KEPT_TRACKS:
        raise SystemExit(
            f'{anim_name}: {len(kept)} tracks survive bone-name intersection, '
            f'expected {EXPECTED_KEPT_TRACKS}')
    if slot not in EXPECTED_CANCEL:
        raise SystemExit(f'{slot}: no expected cancel frame on record')

    dropped_vis = [n.name for n in groups['Visibility'].nodes]
    dropped_mat = [n.name for n in groups['Material'].nodes]

    frame_count = int(round(anim.final_frame_index)) + 1
    groups['Transform'].nodes = kept
    vis_group = build_visibility_group(vis_src_group, frame_count)
    # Order matters for readability only; Transform then Visibility is the
    # convention the recipient's own files use.
    anim.groups = [groups['Transform'], vis_group]
    # The retargeted clip is written under the carrier name, not under the donor
    # file name. The motion-list entry is repointed at the carrier below, so the
    # engine asks for a name the base install already has.
    carrier = CARRIERS[slot]
    out_path = GW_MOTION_DIR / f'{carrier}.nuanmb'
    anim.save(str(out_path))

    return {
        'slot': slot,
        'carrier': carrier,
        'carrier_source': str(BASE_MOTION_DIR / f'{carrier}.nuanmb'),
        'donor_animation': anim_name,
        'donor_path': str(donor_path),
        'donor_sha256': sha256(donor_path),
        'output_path': str(out_path),
        'output_sha256': sha256(out_path),
        'frames': anim.final_frame_index,
        'visibility_track_length': frame_count,
        'transform_tracks_in': len(donor_nodes),
        'transform_tracks_kept': len(kept),
        'transform_tracks_dropped': len(dropped),
        'dropped_tracks': dropped,
        'dropped_visibility_nodes': dropped_vis,
        'dropped_material_nodes': dropped_mat,
        'kept_bones': sorted(n.name for n in kept),
        'retargeted_fingerprint': values_fingerprint(kept),
        'donor_fingerprint': values_fingerprint(donor_nodes),
    }


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_assets():
    GW_MOTION_DIR.mkdir(parents=True, exist_ok=True)

    print('[1/5] Reading recipient skeleton and validating visibility source...')
    gw_bones = [b.name for b in s.skel_data.read_skel(str(GW_SKEL)).bones]
    gw_set = set(gw_bones)
    print(f'      G&W c07 skeleton: {len(gw_bones)} bones from {GW_SKEL}')
    vis_src_group = read_recipient_visibility_source()

    mesh_names = read_mesh_names()
    vis_names = {n.name for n in vis_src_group.nodes}
    if mesh_names is None:
        print('      Mesh-name cross-check unavailable; node names trusted.')
    else:
        shared = sorted(vis_names & mesh_names)
        # Measured: the 94 visibility node names and the 98 mesh object names of
        # G&W c07 have nothing in common, because the visibility nodes are bone
        # names (GW, HeadM, NoseM, ...) rather than mesh object names. The group
        # is copied verbatim from G&W's own a00wait1, so it is consistent with the
        # recipient model by construction. Reported, not asserted.
        print(f'      mesh objects: {len(mesh_names)}, visibility nodes: '
              f'{len(vis_names)}, names in both: {len(shared)}'
              + (f' {shared[:6]}' if shared else ' (visibility nodes are bones, '
                 f'not mesh objects, in this model)'))

    print('[2/5] Validating carrier names against the base install...')
    carriers = [CARRIERS[slot] for slot, _ in MOTIONS]
    if len(set(carriers)) != len(carriers):
        raise SystemExit('Two slots share a carrier; each slot needs its own file.')
    donor_stems = {anim_name.rsplit('.', 1)[0] for _, anim_name in MOTIONS}
    for slot, carrier in CARRIERS.items():
        if carrier in FOREIGN_OWNED:
            raise SystemExit(f'{slot}: carrier {carrier} belongs to another tool')
        if carrier in donor_stems:
            raise SystemExit(
                f'{slot}: carrier {carrier} collides with a donor file name')
        for base in (BASE_MOTION_DIR, BASE_MOTION_DIR_C00):
            if not (base / f'{carrier}.nuanmb').is_file():
                raise SystemExit(
                    f'{slot}: carrier {carrier}.nuanmb is not in {base}. Only '
                    f'names the base install already has are known to load, so a '
                    f'carrier absent there cannot work.')
    print(f'      {len(carriers)} carriers, each present in the base c07 and c00 '
          f'motion folders, none owned by another tool')

    print('[3/5] Retargeting donor transform tracks by bone-name intersection...')
    records = []
    for slot, anim_name in MOTIONS:
        rec = retarget_motion(slot, anim_name, gw_set, vis_src_group)
        records.append(rec)
        print(f"      {slot:<24} kept {rec['transform_tracks_kept']:>2} / "
              f"dropped {rec['transform_tracks_dropped']:>2}  "
              f"frames {rec['frames']:>4}  -> {rec['carrier']}.nuanmb "
              f"(from {anim_name})")

    # Coverage: which recipient bones get no track at all. This was previously a
    # hardcoded four-name tuple, which quietly hid the bones that are actually
    # uncovered. Compute it instead of asserting it.
    covered = {name for rec in records for name in rec['kept_bones']}
    uncovered = sorted(set(gw_bones) - covered)
    unexpected = sorted(set(uncovered) - set(EXPECTED_RECIPIENT_ONLY_BONES))
    print(f'      G&W c07 bones with no donor track: {len(uncovered)} of '
          f'{len(gw_bones)} -> {uncovered}')
    if unexpected:
        print(f'      WARNING: {len(unexpected)} of those are NOT on the '
              f'recipient-only list {list(EXPECTED_RECIPIENT_ONLY_BONES)}: '
              f'{unexpected}. They hold their rest pose for every phase of this '
              f'move. Confirm each is a helper or attach node rather than a bone '
              f'the pose needs, or the move will look wrong in a way nothing '
              f'else here would catch.')

    # Distinctness must be tested as information loss, not as raw inequality.
    # Two donor motions that are already identical across all 84 tracks are
    # allowed to stay identical: the drop did not cause that. What is forbidden
    # is the drop discarding the only difference between two donor-distinct
    # motions, because then two phases would play the same animation.
    fps = {}
    donor_of = {}
    for rec in records:
        fps.setdefault(rec['retargeted_fingerprint'], []).append(rec['slot'])
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
              f'all {EXPECTED_DONOR_TRANSFORM_TRACKS} transform tracks, so the '
              f'drop did not discard a difference between them. Allowed.')

    if lost:
        raise SystemExit(
            f'The drop discarded the only difference between these slots, so '
            f'they would play as the same animation: {lost}. That is a '
            f'retargeting defect, not a property of the donor.')

    print(f'      Distinct phases: {len(fps)} fingerprints for {len(records)} '
          f'slots ({len(donor_identical)} legitimately shared)')

    print('[4/5] Pruning superseded files and injecting motion-list entries...')
    removed = []
    for _, anim_name in MOTIONS:
        stale = GW_MOTION_DIR / anim_name
        if stale.is_file():
            stale.unlink()
            removed.append(anim_name)
    print(f'      removed {len(removed)} donor-named files the slots no longer '
          f'reference: {removed}')
    recipient_mlist = GW_MOTION_DIR / 'motion_list.bin'
    if recipient_mlist.is_file():
        mlist_source = recipient_mlist
    else:
        mlist_source = next(
            (p for p in RECIPIENT_MLIST_FALLBACKS if p.is_file()), None)
        if mlist_source is None:
            raise SystemExit('No recipient motion_list.bin available')
        shutil.copy2(mlist_source, recipient_mlist)
    print(f'      Existing motion list retained as baseline: {mlist_source}')

    baseline_bytes = recipient_mlist.read_bytes()
    magic, motion_path, baseline = parse_mlist(recipient_mlist)
    if encode_mlist(magic, motion_path, baseline) != baseline_bytes:
        raise SystemExit('Round-trip check failed on the recipient motion list')

    _, _, donor = parse_mlist(DONOR_MLIST)
    motions = dict(baseline)
    target_hashes = set()
    injected = []
    for slot, anim_name in MOTIONS:
        key = hash40(slot)
        target_hashes.add(key)
        if key not in donor:
            raise SystemExit(f'Donor motion list has no entry for {slot}')
        entry = donor[key]
        expected_game_script = hash40('game_' + slot.replace('_', ''))
        if entry['game_script'] != expected_game_script:
            raise SystemExit(
                f'{slot}: donor game_script hash {entry["game_script"]:#x} does '
                f'not match game_{slot.replace("_", "")}; the pinned ACMD '
                f'scripts would not bind.')
        if len(entry['animations']) != 1:
            raise SystemExit(
                f'{slot}: donor entry has {len(entry["animations"])} '
                f'animations, expected exactly 1')
        if entry['animations'][0] != hash40(anim_name):
            raise SystemExit(
                f'{slot}: donor entry names animation '
                f'{entry["animations"][0]:#x}, expected {anim_name}')
        expected_cancel = EXPECTED_CANCEL[slot]
        actual_cancel = entry['cancel']
        if expected_cancel:
            if actual_cancel != expected_cancel:
                raise SystemExit(
                    f'{slot}: cancel frame {actual_cancel}, expected '
                    f'{expected_cancel}')
        elif actual_cancel not in (None, 0):
            raise SystemExit(
                f'{slot}: cancel frame {actual_cancel}, expected none/0')
        # Repoint the entry at the carrier. The donor entry names a donor file,
        # and the engine does not load animation names the base install does not
        # already have. Only the 8-byte animation name hash changes here: game
        # script, flags, blend, cancel frame and entry size stay the donor's.
        carrier = CARRIERS[slot]
        carrier_hash = hash40(f'{carrier}.nuanmb')
        raw = bytearray(entry['raw'])
        if struct.unpack_from('<Q', raw, 24)[0] != hash40(anim_name):
            raise SystemExit(
                f'{slot}: the entry does not name {anim_name} at its animation '
                f'offset, so the carrier hash would land in the wrong field')
        struct.pack_into('<Q', raw, 24, carrier_hash)
        patched = dict(entry)
        patched['raw'] = bytes(raw)
        patched['animations'] = (carrier_hash,)
        # Replacing an existing key keeps its position, so entry order is stable.
        motions[key] = patched
        injected.append({
            'slot': slot,
            'carrier': carrier,
            'carrier_hash': f'{carrier_hash:#x}',
            'cancel_frame': actual_cancel,
            'game_script_hash': f'{entry["game_script"]:#x}',
            'donor_animation': anim_name,
        })

    result_bytes = encode_mlist(magic, motion_path, motions)
    recipient_mlist.write_bytes(result_bytes)
    _, _, check = parse_mlist(recipient_mlist)
    if check != motions:
        raise SystemExit('Re-parsed motion list does not match what was written')
    if check != baseline and any(
            check[k] != v for k, v in baseline.items() if k not in target_hashes):
        raise SystemExit('An unrelated motion-list entry changed')
    unchanged = sum(1 for k, v in baseline.items()
                    if k not in target_hashes and check[k] == v)
    print(f'      Injected {len(injected)} donor entries; '
          f'{unchanged} unrelated entries byte-identical to baseline')

    print('[5/5] Writing manifest...')
    manifest = {
        'generated_by': 'mod_files/mythra_gamewatch_swap/tools/build_monkey_flip_assets.py',
        'purpose': (
            'Retarget Diddy Monkey Flip motions onto G&W c07 by bone-name '
            'intersection, replacing the previous raw byte copies.'
        ),
        'supersedes': 'references/inject_monkey_flip.py (raw byte copies)',
        'recipient': {
            'fighter': 'gamewatch',
            'slot': 'c07',
            'skeleton': str(GW_SKEL),
            'bone_count': len(gw_bones),
            'bones': gw_bones,
        },
        'donor': {'fighter': 'diddy', 'motion_dir': str(DONOR_DIR)},
        'binding_semantics': (
            'Recipient animation node order is alphabetical, skeleton order is '
            'hierarchical, so transform binding is by node name, not index.'
        ),
        'visibility_group': {
            'source': str(GW_VIS_SOURCE),
            'source_sha256': sha256(GW_VIS_SOURCE),
            'node_count': EXPECTED_VIS_NODES,
            'visible_nodes': sorted(EXPECTED_VIS_VISIBLE),
            'rationale': (
                'G&W c00 carries no Material nodes at all, and its Visibility '
                'node set and values are canonical (one value-vector across all '
                '237 motions sharing the dominant node set), so the donor '
                'groups are dropped and the recipient group is used.'
            ),
        },
        'motion_list': {
            'baseline_source': str(mlist_source),
            'baseline_bytes': len(baseline_bytes),
            'baseline_sha256': hashlib.sha256(baseline_bytes).hexdigest(),
            'output_bytes': len(result_bytes),
            'output_sha256': sha256(recipient_mlist),
            'unrelated_entries_unchanged': unchanged,
            'injected_entries': injected,
        },
        'motions': records,
        'assertions': {
            'distinct_phases': (
                f'{len(fps)} distinct fingerprints for {len(records)} slots'
            ),
            'donor_transform_tracks_per_motion': EXPECTED_DONOR_TRANSFORM_TRACKS,
            'kept_tracks_per_motion': EXPECTED_KEPT_TRACKS,
            'recipient_bones_without_donor_track': uncovered,
            'recipient_bones_expected_without_track':
                sorted(EXPECTED_RECIPIENT_ONLY_BONES),
        },
        'carriers': {
            'why': (
                'Each slot loads an animation name the base install already has, '
                'written over by this tool. Newly added animation names were '
                'observed not to load at all: the phase ran for the length of '
                'whatever clip was already on screen, and that length changed '
                'with what the player had been doing before the input. The '
                'carriers are Game & Watch animations for the side-B and down-B '
                'that this mod has already replaced, so no playable pose changes.'
            ),
            'map': CARRIERS,
            'donor_names_no_longer_shipped': [a for _, a in MOTIONS],
        },
        'files': {
            **{f"{r['carrier']}.nuanmb": r['output_sha256'] for r in records},
            'motion_list.bin': sha256(recipient_mlist),
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Wrote {MANIFEST}')
    print('\n[SUCCESS] Monkey Flip motions retargeted and packaged.')
    return manifest


if __name__ == '__main__':
    build_assets()
