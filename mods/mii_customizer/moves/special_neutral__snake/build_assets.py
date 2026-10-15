#!/usr/bin/env python3
"""Build the game assets of move unit MV-special_neutral__snake (Snake's hand grenade on Mii Gunner).

Run from anywhere:
    python -I mods/mii_customizer/moves/special_neutral__snake/build_assets.py            build everything
    python -I .../build_assets.py apply-motion <base motion_list.bin> <out.bin>           add the 29 entries to any list
    python -I .../build_assets.py apply-sound <base bank stem> <out bank stem>            add the 9 tones to any bank triple
(a bank stem is a path without extension: <stem>.nus3audio, <stem>.nus3bank, <stem>.tonelabel)

Inputs: gamedata/ssbu-13.0.4/data.arc through tools/arc-extract (only when a file is missing), read into
gamedata/mii_customizer/moves/special_neutral__snake/ (the unit's game-data folder, ARC paths mirrored).

Outputs under that folder:
  package/fighter/miigunner/motion/body/c00/c01mcsnake*.nuanmb   29 clips: Snake's 14 special_(air_)n_* motions and
                                                                 his 15 item_shoot_legs_* motions on the Gunner skeleton
  package/fighter/miigunner/model/mc_snake_pin/cNN/*             Snake's pin prop model, NN = 00..11 (every Mii colour)
  package/fighter/miigunner/motion/mc_snake_pin/cNN/*            its 3 clips and its motion list (kinds renamed)
  reference/motion_list_vanilla_plus_owned.bin                   vanilla Gunner list + the 29 owned entries (reference)
  reference/sound/bank/fighter/se_miigunner{,_c00}.*             vanilla Gunner SE banks + 9 Snake tones (reference)
  tables/retarget_report.json, manifest.json

Shared Gunner files (motion list, sound banks, config.json) are NOT shipped as whole copies: the `apply-*` commands
add this unit's entries/tones to whichever base file the installer assembles.

Retarget (same construction as moves/aerial_forward__cloud/build_assets.py, i.e. the other mod's
"Retargeting a donor air clip" recipe): pose nodes present on both rigs take the donor rotation; translation is
recipient idle + (donor frame - donor idle); nodes whose parent differs (ClavicleL/R, LegL/R) are transferred in
world space; Rot gets a vertical ground-contact correction; donor-only nodes are dropped; Visibility comes from the
Gunner's idle; Material is dropped. `special_n_hold` is the donor's upper-body layer (no Trans/Rot/Hip/legs): only
the nodes the donor clip animates are written, so it stays a partial clip.

Sound: the same method as moves/tilt_up__snake/build_assets.py (append_tones): donor sample bytes and tone records
unchanged, appended after the recipient's own tones, labels rebased.

Offline only (tier B): nothing here shows the move in game.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

MOD_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = MOD_ROOT.parent.parent
UNIT = 'special_neutral__snake'
OUT = WORKSPACE / 'gamedata/mii_customizer/moves' / UNIT
EXTRACTED = OUT            # ARC paths are mirrored directly in the unit's game-data folder
PACKAGE = OUT / 'package'
REFERENCE = OUT / 'reference'
TABLES = OUT / 'tables'
MANIFEST = OUT / 'manifest.json'
DATA_ARC = WORKSPACE / 'gamedata/ssbu-13.0.4/data.arc'
ARC_EXTRACT = WORKSPACE / 'tools/arc-extract/target/release/arc-extract.exe'
POSE_TOOLS = WORKSPACE / 'mods/ssbu_mod_new/src/pgwr/tools'   # read-only: pose_fk.py

SNAKE_BODY = 'fighter/snake/motion/body/c00'
GUNNER_BODY = 'fighter/miigunner/motion/body/c00'
SNAKE_MLIST = SNAKE_BODY + '/motion_list.bin'
GUNNER_MLIST = GUNNER_BODY + '/motion_list.bin'
SNAKE_IDLE = SNAKE_BODY + '/a00wait1.nuanmb'
GUNNER_IDLE = GUNNER_BODY + '/a00wait1.nuanmb'
SNAKE_SKEL = 'fighter/snake/model/body/c00/model.nusktb'
GUNNER_SKEL = 'fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb'
PIN_MODEL = 'fighter/snake/model/grenade/c00'
PIN_MOTION = 'fighter/snake/motion/grenade/c00'
PIN_MODEL_FILES = ['dark_model.numatb', 'def_grenade_001_col.nutexb', 'def_grenade_001_nor.nutexb',
                   'def_grenade_001_prm.nutexb', 'light_model.numatb', 'metamon_model.numatb', 'model.nuanmb',
                   'model.nuhlpb', 'model.numatb', 'model.numdlb', 'model.numshb', 'model.numshexb',
                   'model.nusktb', 'model.nusrcmdlb', 'model.xmb']
PIN_CLIPS = ['d00specialnstart.nuanmb', 'd00specialairnstart.nuanmb', 'd00specialnstartkirby.nuanmb']
PIN_ARTICLE = 'mc_snake_pin'
PIN_KINDS = {'special_n_start': 'mc_snake_pin_start', 'special_air_n_start': 'mc_snake_pin_air_start',
             'special_n_start_kirby': 'mc_snake_pin_start_kirby'}
MII_SLOTS = [f'c{i:02}' for i in range(12)]

# Donor motion kinds, in the donor list's order of use. Owned kind = mc_snake_<kind>.
SPECIAL_KINDS = ['special_n_start', 'special_n_hold', 'special_n_throw_lw', 'special_n_throw_m',
                 'special_n_throw_hi', 'special_n_close', 'special_n_throw_fail',
                 'special_air_n_start', 'special_air_n_hold', 'special_air_n_jump_aerial',
                 'special_air_n_throw_lw', 'special_air_n_throw_m', 'special_air_n_throw_hi',
                 'special_air_n_throw_fail']
LOWER_PARTS = ['wait', 'walk_f', 'walk_b', 'dash_f', 'dash_b', 'brake_f', 'brake_b', 'jump_squat', 'landing',
               'slow_f', 'middle_f', 'fast_f', 'slow_b', 'middle_b', 'fast_b']
KINDS = SPECIAL_KINDS + ['item_shoot_legs_' + p for p in LOWER_PARTS]
# The donor's upper-body layer: written as a partial clip.
PARTIAL_KINDS = {'special_n_hold'}
# Donor clip per kind (resolved from the donor list by hash in `donor_entries`, asserted against this table).
DONOR_CLIPS = {
    'special_n_start': 'd00specialnstart', 'special_n_hold': 'd00specialnhold',
    'special_n_throw_lw': 'd00specialnthrowlw', 'special_n_throw_m': 'd00specialnthrowm',
    'special_n_throw_hi': 'd00specialnthrowhi', 'special_n_close': 'd00specialnclose',
    'special_n_throw_fail': 'd00specialnthrowm', 'special_air_n_start': 'd00specialairnstart',
    'special_air_n_hold': 'd00specialairnhold', 'special_air_n_jump_aerial': 'd00specialairnhold',
    'special_air_n_throw_lw': 'd00specialairnthrowlw', 'special_air_n_throw_m': 'd00specialairnthrowm',
    'special_air_n_throw_hi': 'd00specialairnthrowhi', 'special_air_n_throw_fail': 'd00specialairnthrowm',
}
DONOR_CLIPS.update({'item_shoot_legs_' + p: 'h10itemlegs' + p.replace('_', '') for p in LOWER_PARTS})

SE_DONOR_STEM = 'sound/bank/fighter/se_snake_c00'
SE_RECIPIENT_STEMS = ['sound/bank/fighter/se_miigunner', 'sound/bank/fighter/se_miigunner_c00']
SE_TONES = ['se_snake_special_n01', 'se_snake_special_n02', 'se_snake_special_n03', 'se_snake_special_n04',
            'se_snake_step_left_m', 'se_snake_step_right_m', 'se_snake_dash_stop', 'se_snake_jump01',
            'se_snake_landing02']
SQB_DONOR = 'sound/sequence/fighter/snake.sqb'

PINS = {
    SNAKE_MLIST: 'b70e42ca1e6ea143301349e268af5a7e98d391d0321a39c79a4187ef6fd39c34',
    GUNNER_MLIST: '2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba',
    SNAKE_IDLE: '542313c8aa3b3736bcf21229ae15b7cbfaaad0d0fff694b9af14cfca6da10c91',
    GUNNER_IDLE: '6b14939e4bef4a0f00bfa9b559a3f338372a5a01bb6dec65ec83e649d21a47fe',
    SNAKE_SKEL: 'df2c83b2426fb3a2e7ebc0bd1029e67608b53368eafb5d97a04b2f1d0aae72e4',
    GUNNER_SKEL: '1d66b6d1cc4ce3b1c0883a21194cf998531c4a92ccb1c6561f69e68fd671429d',
    PIN_MOTION + '/motion_list.bin': '392773db12013ccf1744b05ea595d03da24f49122c506e202112076c945c6bdc',
    SE_DONOR_STEM + '.nus3audio': '88057e12e9aa1dcadad8c604e1bf148a9b49e93b898a7ce8b7f67ec19479a495',
    SE_DONOR_STEM + '.nus3bank': '4e09776aad72a942e317be17b809e4dc8b8fa55c6f5538ba1510a1bfd4f28fa0',
    SE_DONOR_STEM + '.tonelabel': '8692a0a7eec86fb7159fbb96884f9424c44e57458388e37cb278f518d47a67c1',
    SQB_DONOR: '90370dcfeaed1e27498c1eaf4dc6e2a64d03d79e6a2df8ac1daa7f45df44ce0b',
    'fighter/snake/param/vl.prc': '62ee0282c6221e2938abaad4e7d32c046d55a53ba2fe787693e82dc2a43f33de',
}

u32 = lambda data, offset: struct.unpack_from('<I', data, offset)[0]  # noqa: E731
pack = lambda n: struct.pack('<I', n)  # noqa: E731


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    return sha(Path(path).read_bytes())


def rel(path: Path) -> str:
    return Path(path).relative_to(WORKSPACE).as_posix()


def owned_kind(kind: str) -> str:
    return 'mc_snake_' + kind


def owned_stem(kind: str) -> str:
    return 'mcsnake' + kind.replace('_', '')


def owned_clip(kind: str) -> str:
    return 'c01' + owned_stem(kind) + '.nuanmb'


def owned_scripts(kind: str) -> dict:
    return {c: f'{c}_{owned_stem(kind)}' for c in ('game', 'expression', 'sound', 'effect')}


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def wanted_inputs() -> list:
    paths = [SNAKE_MLIST, GUNNER_MLIST, SNAKE_IDLE, GUNNER_IDLE, SNAKE_SKEL, GUNNER_SKEL, SQB_DONOR,
             'fighter/snake/param/vl.prc', PIN_MOTION + '/motion_list.bin']
    paths += sorted({f'{SNAKE_BODY}/{c}.nuanmb' for c in DONOR_CLIPS.values()})
    paths += [f'{PIN_MODEL}/{n}' for n in PIN_MODEL_FILES] + [f'{PIN_MOTION}/{n}' for n in PIN_CLIPS]
    for stem in [SE_DONOR_STEM] + SE_RECIPIENT_STEMS:
        paths += [f'{stem}.{ext}' for ext in ('nus3audio', 'nus3bank', 'tonelabel')]
    return paths


def ensure_extracted() -> None:
    missing = [p for p in wanted_inputs() if not (EXTRACTED / p).is_file()]
    if missing:
        assert ARC_EXTRACT.is_file(), f'arc-extract missing: {ARC_EXTRACT}'
        assert DATA_ARC.is_file(), f'data.arc missing: {DATA_ARC}'
        subprocess.run([str(ARC_EXTRACT), '--arc', str(DATA_ARC), '--out', str(EXTRACTED)] + missing, check=True)
    for p in wanted_inputs():
        assert (EXTRACTED / p).is_file(), f'missing input {p}'
    for p, digest in PINS.items():
        assert sha_file(EXTRACTED / p) == digest, f'{p} is not the pinned revision'


# ---------------------------------------------------------------------------
# Motion list
# ---------------------------------------------------------------------------

def parse_mlist(data: bytes):
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    offset = 24
    entries = []
    for i in range(count):
        start = offset
        kind, game, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset + 24)
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        entries.append({'index': i, 'kind': kind, 'game': game, 'flags': flags, 'blend': blend,
                        'n_anims': n_anims, 'anims': anims, 'size': size, 'raw': data[start:end],
                        'tail_offset': tail - start})
        offset = end
    if offset != len(data):
        raise RuntimeError(f'motion list: {len(data) - offset} trailing bytes after {count} entries')
    return magic, motion_path, entries


def donor_entries() -> dict:
    _, _, entries = parse_mlist((EXTRACTED / SNAKE_MLIST).read_bytes())
    by_kind = {e['kind']: e for e in entries}
    out = {}
    for kind in KINDS:
        e = by_kind.get(hash40(kind))
        assert e is not None, f'donor list has no {kind}'
        assert e['anims'] == (hash40(DONOR_CLIPS[kind] + '.nuanmb'),), f'{kind}: donor clip is not {DONOR_CLIPS[kind]}'
        assert e['size'] == 28, kind
        out[kind] = e
    return out


def owned_entry(kind: str, donor: dict) -> bytes:
    """The donor entry whole; only the kind, the clip and the four script names are repointed."""
    raw = bytearray(donor['raw'])
    names = owned_scripts(kind)
    struct.pack_into('<QQ', raw, 0, hash40(owned_kind(kind)), hash40(names['game']))
    struct.pack_into('<Q', raw, 24, hash40(owned_clip(kind)))
    t = donor['tail_offset']
    struct.pack_into('<QQQ', raw, t, hash40(names['expression']), hash40(names['sound']), hash40(names['effect']))
    out = bytes(raw)
    changed = {i for i in range(len(out)) if out[i] != donor['raw'][i]}
    assert changed <= set(range(0, 16)) | set(range(24, 32)) | set(range(t, t + 24)), kind
    return out


def apply_motion(base: bytes) -> bytes:
    """Append the 29 owned entries to any Gunner motion list (refuses a list that already has one)."""
    magic, path, entries = parse_mlist(base)
    have = {e['kind'] for e in entries}
    donors = donor_entries()
    for kind in KINDS:
        assert hash40(owned_kind(kind)) not in have, f'base list already has {owned_kind(kind)}'
    added = b''.join(owned_entry(kind, donors[kind]) for kind in KINDS)
    out = struct.pack('<QQQ', magic, path, len(entries) + len(KINDS)) + b''.join(e['raw'] for e in entries) + added
    _, _, back = parse_mlist(out)
    assert [e['raw'] for e in back[:len(entries)]] == [e['raw'] for e in entries]
    return out


def build_motion_list() -> dict:
    vanilla = (EXTRACTED / GUNNER_MLIST).read_bytes()
    rebuilt = apply_motion(vanilla)
    dest = REFERENCE / 'motion_list_vanilla_plus_owned.bin'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(rebuilt)
    _, _, before = parse_mlist(vanilla)
    _, _, after = parse_mlist(rebuilt)
    donors = donor_entries()
    motions = {}
    for kind, e in zip(KINDS, after[len(before):]):
        d = donors[kind]
        t = e['tail_offset']
        exp, snd, eff = struct.unpack_from('<QQQ', e['raw'], t)
        cancel = struct.unpack_from('<H', e['raw'], t + 26)[0]
        assert cancel == struct.unpack_from('<H', d['raw'], d['tail_offset'] + 26)[0]
        assert (e['flags'], e['blend'], e['n_anims'], e['size']) == (d['flags'], d['blend'], d['n_anims'], d['size'])
        names = owned_scripts(kind)
        motions[owned_kind(kind)] = {
            'kind_hash': f'0x{e["kind"]:010x}', 'donor_kind': kind, 'donor_index': d['index'],
            'donor_clip': DONOR_CLIPS[kind] + '.nuanmb', 'clip': owned_clip(kind),
            'clip_hash': f'0x{e["anims"][0]:010x}',
            'game_script': names['game'], 'game_script_hash': f'0x{e["game"]:010x}',
            'expression_script': names['expression'], 'expression_script_hash': f'0x{exp:010x}',
            'sound_script': names['sound'], 'sound_script_hash': f'0x{snd:010x}',
            'effect_script': names['effect'], 'effect_script_hash': f'0x{eff:010x}',
            'flags': f'0x{e["flags"]:04x}', 'blend': e['blend'], 'cancel_frame': cancel,
            'index_in_reference_list': e['index'],
        }
    return {'reference': rel(dest), 'sha256': sha_file(dest), 'vanilla_entries': len(before),
            'entries': len(after), 'motions': motions}


# ---------------------------------------------------------------------------
# Retarget
# ---------------------------------------------------------------------------

def load_pose_tools():
    sys.path.insert(0, str(POSE_TOOLS))
    import numpy as np  # noqa: E402
    import ssbh_data_py as s  # noqa: E402
    import pose_fk as fk  # noqa: E402
    return np, s, fk


def retarget_all() -> dict:
    np, s, fk = load_pose_tools()

    def rot_of(m):
        r = np.array(m, dtype=float)[:3, :3]
        u, _, vt = np.linalg.svd(r)
        rot = u @ vt
        if np.linalg.det(rot) < 0:
            u[:, -1] *= -1
            rot = u @ vt
        return rot

    def matrix_to_quat(r):
        r = np.array(r, dtype=float)
        tr = r[0, 0] + r[1, 1] + r[2, 2]
        if tr > 0:
            k = np.sqrt(tr + 1.0) * 2
            w, x, y, z = 0.25 * k, (r[2, 1] - r[1, 2]) / k, (r[0, 2] - r[2, 0]) / k, (r[1, 0] - r[0, 1]) / k
        elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
            k = np.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2]) * 2
            w, x, y, z = (r[2, 1] - r[1, 2]) / k, 0.25 * k, (r[0, 1] + r[1, 0]) / k, (r[0, 2] + r[2, 0]) / k
        elif r[1, 1] > r[2, 2]:
            k = np.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2]) * 2
            w, x, y, z = (r[0, 2] - r[2, 0]) / k, (r[0, 1] + r[1, 0]) / k, 0.25 * k, (r[1, 2] + r[2, 1]) / k
        else:
            k = np.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1]) * 2
            w, x, y, z = (r[1, 0] - r[0, 1]) / k, (r[0, 2] + r[2, 0]) / k, (r[1, 2] + r[2, 1]) / k, 0.25 * k
        q = np.array([x, y, z, w], dtype=float)
        q = [float(v) for v in q / np.linalg.norm(q)]
        if np.max(np.abs(fk.quat_to_matrix(q) - r)) > 1e-6:
            raise RuntimeError('matrix_to_quat does not invert quat_to_matrix')
        return q

    def collapsed(values):
        def key(v):
            return (tuple(v.scale), tuple(v.rotation), tuple(v.translation))
        return values[:1] if len({key(v) for v in values}) == 1 else values

    skel_d = fk.Skeleton(EXTRACTED / SNAKE_SKEL)
    skel_r = fk.Skeleton(EXTRACTED / GUNNER_SKEL)
    _, d_idle = fk.read_transform_tracks(EXTRACTED / SNAKE_IDLE)
    _, r_idle = fk.read_transform_tracks(EXTRACTED / GUNNER_IDLE)
    r_idle_anim = s.anim_data.read_anim(str(EXTRACTED / GUNNER_IDLE))
    r_vis = next(g for g in r_idle_anim.groups if g.group_type.name == 'Visibility')
    d_idle0 = {k: v[:1] for k, v in d_idle.items()}
    r_idle0 = {k: v[:1] for k, v in r_idle.items()}
    r_native = list(r_idle)
    r_lower = {n.lower(): n for n in r_native}
    skel_r_lower = {n.lower() for n in skel_r.names}
    contact_d_idle = fk.lowest_toe(skel_d, skel_d.worlds(fk.locals_at(skel_d, d_idle, 0)))
    contact_r_idle = fk.lowest_toe(skel_r, skel_r.worlds(fk.locals_at(skel_r, r_idle, 0)))

    dest_dir = PACKAGE / GUNNER_BODY
    if dest_dir.is_dir():
        for old in dest_dir.glob('c01mcsnake*.nuanmb'):
            old.unlink()
    dest_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for kind in KINDS:
        src = EXTRACTED / SNAKE_BODY / (DONOR_CLIPS[kind] + '.nuanmb')
        d_anim, d_clip = fk.read_transform_tracks(src)
        partial = kind in PARTIAL_KINDS
        n = int(round(d_anim.final_frame_index)) + 1
        assert fk.frame_count(d_clip) in (1, n), (kind, fk.frame_count(d_clip), n)
        donor_of = {}
        dropped = []
        for name in d_clip:
            low = name.lower()
            if low in r_lower and low in skel_r_lower:
                donor_of[r_lower[low]] = name
            else:
                dropped.append(name)
        pose = [name for name in r_native if name in donor_of]
        assert ('Trans' in donor_of) != partial, (kind, 'partial flag does not match the donor node set')
        for name in pose:
            dn = donor_of[name]
            assert name in skel_r.index and dn in skel_d.index and dn in d_idle, (kind, name)
            assert max(abs(float(x) - 1.0) for x in d_idle[dn][0].scale) <= 1e-4, (kind, dn, 'scaled in donor idle')
        # FK inputs: a node the clip does not animate sits at the idle (not the skeleton rest), on both rigs.
        d_fk = {**d_idle0, **d_clip}

        out = {}
        written = pose if partial else r_native
        for name in written:
            base_r = r_idle[name][0]
            if name not in donor_of:
                out[name] = [base_r] * n
                continue
            dn = donor_of[name]
            base_d = d_idle[dn][0]
            frames = []
            for f in range(n):
                dv = fk.value_at(d_clip[dn], f)
                frames.append(s.anim_data.Transform(
                    [float(base_r.scale[i]) * float(dv.scale[i]) / float(base_d.scale[i]) for i in range(3)],
                    [float(x) for x in dv.rotation],
                    [float(base_r.translation[i]) + float(dv.translation[i]) - float(base_d.translation[i])
                     for i in range(3)]))
            out[name] = frames

        mismatches = []
        for name in pose:
            dp = skel_d.parent[skel_d.index[donor_of[name]]]
            rp = skel_r.parent[skel_r.index[name]]
            dpn = skel_d.names[dp].lower() if dp is not None else None
            rpn = skel_r.names[rp].lower() if rp is not None else None
            if dpn != rpn:
                mismatches.append({'node': name, 'donor_parent': dpn, 'gunner_parent': rpn})
        for m in mismatches:
            name = m['node']
            i_d = skel_d.index[donor_of[name]]
            i_r = skel_r.index[name]
            wd_idle = rot_of(skel_d.worlds(fk.locals_at(skel_d, d_idle, 0))[i_d])
            wr_idle = rot_of(skel_r.worlds(fk.locals_at(skel_r, r_idle, 0))[i_r])
            p_idx = skel_r.parent[i_r]
            for f in range(n):
                wd_f = rot_of(skel_d.worlds(fk.locals_at(skel_d, d_fk, f))[i_d])
                target = (wd_f @ wd_idle.T) @ wr_idle
                parent_world = rot_of(skel_r.worlds(fk.locals_at(skel_r, {**r_idle0, **out}, f))[p_idx])
                v = out[name][f]
                out[name][f] = s.anim_data.Transform(list(v.scale), matrix_to_quat(parent_world.T @ target),
                                                     list(v.translation))

        corrections = []
        trans_rotates = any(abs(abs(float(v.rotation[3])) - 1.0) > 1e-4 for v in d_clip.get('Trans', []))
        if not partial and not trans_rotates:
            for f in range(n):
                target = contact_r_idle + (fk.lowest_toe(skel_d, skel_d.worlds(fk.locals_at(skel_d, d_fk, f)))
                                           - contact_d_idle)
                have = fk.lowest_toe(skel_r, skel_r.worlds(fk.locals_at(skel_r, out, f)))
                corrections.append(target - have)
            out['Rot'] = [s.anim_data.Transform(list(v.scale), list(v.rotation),
                                                [float(v.translation[0]), float(v.translation[1]) + corrections[f],
                                                 float(v.translation[2])]) for f, v in enumerate(out['Rot'])]

        transform_nodes = [s.anim_data.NodeData(name, [s.anim_data.TrackData('Transform', values=collapsed(out[name]))])
                           for name in written]
        vis_nodes = [s.anim_data.NodeData(node.name, [s.anim_data.TrackData(
            'Visibility', values=[node.tracks[0].values[0]])]) for node in r_vis.nodes]
        d_anim.groups = [s.anim_data.GroupData(s.anim_data.GroupType.Transform, transform_nodes),
                         s.anim_data.GroupData(s.anim_data.GroupType.Visibility, vis_nodes)]
        clip_out = dest_dir / owned_clip(kind)
        d_anim.save(str(clip_out))

        check = s.anim_data.read_anim(str(clip_out))
        got = [n_.name for n_ in next(g for g in check.groups if g.group_type.name == 'Transform').nodes]
        assert got == written, (kind, 'Transform node set changed after saving')
        assert [g.group_type.name for g in check.groups] == ['Transform', 'Visibility'], kind
        assert check.final_frame_index == d_anim.final_frame_index == n - 1, kind
        # Hand travel (world space) of donor and result, as the offline evidence that the pose was carried.
        travel = {}
        for hand in ('HandL', 'HandR'):
            pd = np.array([fk.world_position(skel_d, skel_d.worlds(fk.locals_at(skel_d, d_fk, f)), hand)
                           for f in range(n)])
            pr = np.array([fk.world_position(skel_r, skel_r.worlds(fk.locals_at(skel_r, {**r_idle0, **out}, f)), hand)
                           for f in range(n)])
            travel[hand] = {'donor': [round(float(x), 3) for x in pd.max(0) - pd.min(0)],
                            'gunner': [round(float(x), 3) for x in pr.max(0) - pr.min(0)]}
        report[owned_kind(kind)] = {
            'clip': owned_clip(kind), 'clip_sha256': sha_file(clip_out), 'bytes': clip_out.stat().st_size,
            'donor_clip': rel(src), 'donor_clip_sha256': sha_file(src),
            'frames': n, 'final_frame_index': float(check.final_frame_index), 'partial': partial,
            'donor_transform_nodes': len(d_clip), 'pose_nodes': len(pose), 'written_transform_nodes': len(written),
            'dropped_donor_nodes': sorted(dropped),
            'held_at_gunner_idle': [x for x in written if x not in donor_of],
            'world_space_transfer_nodes': [m['node'] for m in mismatches], 'parent_mismatches': mismatches,
            'ground_correction_range': ([round(min(corrections), 5), round(max(corrections), 5)]
                                        if corrections else None),
            'trans_rotates': trans_rotates, 'hand_travel': travel,
            'visibility_nodes_from_gunner_idle': len(vis_nodes),
        }
    return report


# ---------------------------------------------------------------------------
# Pin prop (Snake's article 12, weapon kind WEAPON_KIND_SNAKE_GRENADE): files only this unit uses
# ---------------------------------------------------------------------------

def build_pin() -> dict:
    src_list = (EXTRACTED / PIN_MOTION / 'motion_list.bin').read_bytes()
    magic, path, entries = parse_mlist(src_list)
    assert {e['kind'] for e in entries} == {hash40(k) for k in PIN_KINDS}
    clip_hashes = {hash40(n) for n in PIN_CLIPS}
    raws = []
    for e in entries:
        donor_kind = next(k for k in PIN_KINDS if hash40(k) == e['kind'])
        assert len(e['anims']) == 1 and e['anims'][0] in clip_hashes, donor_kind
        raw = bytearray(e['raw'])
        struct.pack_into('<Q', raw, 0, hash40(PIN_KINDS[donor_kind]))
        raws.append(bytes(raw))
    list_bytes = struct.pack('<QQQ', magic, path, len(raws)) + b''.join(raws)
    assert len(list_bytes) == len(src_list)
    files = []
    for old in (PACKAGE / 'fighter/miigunner/model' / PIN_ARTICLE, PACKAGE / 'fighter/miigunner/motion' / PIN_ARTICLE):
        if old.is_dir():
            shutil.rmtree(old)
    for slot in MII_SLOTS:
        for category, folder, names in (('model', PIN_MODEL, PIN_MODEL_FILES), ('motion', PIN_MOTION, PIN_CLIPS)):
            for name in names:
                dest = PACKAGE / f'fighter/miigunner/{category}/{PIN_ARTICLE}/{slot}/{name}'
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(EXTRACTED / folder / name, dest)
                files.append(dest)
        dest = PACKAGE / f'fighter/miigunner/motion/{PIN_ARTICLE}/{slot}/motion_list.bin'
        dest.write_bytes(list_bytes)
        files.append(dest)
    return {'article': PIN_ARTICLE, 'slots': MII_SLOTS, 'files_per_slot': len(PIN_MODEL_FILES) + len(PIN_CLIPS) + 1,
            'motion_kinds': PIN_KINDS, 'motion_list_sha256': sha(list_bytes),
            'donor_model_sha256': {n: sha_file(EXTRACTED / PIN_MODEL / n) for n in PIN_MODEL_FILES},
            'donor_clip_sha256': {n: sha_file(EXTRACTED / PIN_MOTION / n) for n in PIN_CLIPS},
            'file_count': len(files)}


# ---------------------------------------------------------------------------
# Sound (method of moves/tilt_up__snake/build_assets.py, itself the other mod's merge tools)
# ---------------------------------------------------------------------------

def chunk(tag, payload):
    return tag + pack(len(payload)) + payload


def audio_read(data):
    assert data[:4] == b'NUS3' and data[8:12] == b'AUDI'
    assert u32(data, 4) + 8 == len(data)
    offset, chunks = 12, {}
    while offset < len(data):
        tag = data[offset:offset + 4]
        size = u32(data, offset + 4)
        assert tag not in chunks and offset + 8 + size <= len(data)
        chunks[tag] = data[offset + 8:offset + 8 + size]
        offset += 8 + size
    assert set(chunks) == {b'INDX', b'TNID', b'NMOF', b'ADOF', b'TNNM', b'JUNK', b'PACK'}
    count = u32(chunks[b'INDX'], 0)
    ids = list(struct.unpack('<' + 'I' * count, chunks[b'TNID']))
    assert ids == list(range(count)), 'Nonsequential tone ids need a separate mapping'
    result = []
    for i in range(count):
        name_offset = u32(chunks[b'NMOF'], i * 4)
        name = data[name_offset:data.index(b'\0', name_offset)].decode()
        start, size = struct.unpack_from('<II', chunks[b'ADOF'], i * 8)
        assert start + size <= len(data)
        result.append((name, data[start:start + size]))
    assert len({n for n, _ in result}) == count
    return result


def audio_write(entries):
    count = len(entries)
    prefix = chunk(b'INDX', pack(count)) + chunk(b'TNID', b''.join(pack(i) for i in range(count)))
    name_start = 12 + len(prefix) + 8 + count * 4 + 8 + count * 8 + 8
    names, name_offsets = bytearray(), []
    for name, _ in entries:
        name_offsets.append(name_start + len(names))
        names += name.encode() + b'\0'
    prefix += chunk(b'NMOF', b''.join(pack(n) for n in name_offsets))
    name_chunk = chunk(b'TNNM', bytes(names))
    before_junk = 12 + len(prefix) + 8 + count * 8 + len(name_chunk)
    padding = (-before_junk - 16) % 16
    audio_start = before_junk + 8 + padding + 8
    payload, offsets = bytearray(), []
    for _, encoded in entries:
        offsets.append((audio_start + len(payload), len(encoded)))
        payload += encoded
        payload += b'\0' * (-len(payload) % 16)
    body = prefix + chunk(b'ADOF', b''.join(struct.pack('<II', *o) for o in offsets))
    body += name_chunk + chunk(b'JUNK', b'\0' * padding) + chunk(b'PACK', bytes(payload))
    result = b'NUS3' + pack(4 + len(body)) + b'AUDI' + body
    assert audio_read(result) == entries
    return result


def bank_read(data):
    assert data[:4] == b'NUS3' and data[8:16] == b'BANKTOC '
    assert u32(data, 4) + 8 == len(data)
    count = u32(data, 20)
    assert u32(data, 16) == 4 + count * 8
    offset, result = 20 + u32(data, 16), []
    for i in range(count):
        tag = data[offset:offset + 4]
        size = u32(data, offset + 4)
        assert data[24 + i * 8:32 + i * 8] == tag + pack(size)
        result.append((tag, data[offset + 8:offset + 8 + size]))
        offset += 8 + size
    assert offset == len(data)
    return result


def bank_write(chunks):
    body = b'BANKTOC ' + pack(4 + len(chunks) * 8) + pack(len(chunks))
    body += b''.join(tag + pack(len(data)) for tag, data in chunks)
    body += b''.join(chunk(tag, data) for tag, data in chunks)
    result = b'NUS3' + pack(len(body)) + body
    assert bank_read(result) == chunks
    return result


def tones_read(payload):
    count = u32(payload, 0)
    entries = []
    for i in range(count):
        off, size = struct.unpack_from('<II', payload, 4 + i * 8)
        assert off >= 4 + count * 8 and off + size <= len(payload)
        entries.append(payload[off:off + size])
    assert 4 + count * 8 + sum(map(len, entries)) == len(payload)
    return entries


def tones_write(entries):
    offset, table = 4 + len(entries) * 8, bytearray()
    for data in entries:
        table += struct.pack('<II', offset, len(data))
        offset += len(data)
    result = pack(len(entries)) + table + b''.join(entries)
    assert tones_read(result) == entries
    return result


def tone_kind(tone, names):
    name_at = 12 if u32(tone, 4) & 0x80000000 else 8
    size = tone[name_at]
    name = tone[name_at + 1:name_at + size].decode()
    assert name.lower() in {n.lower() for n in names}
    start = (name_at + 1 + size + 3) & ~3
    return u32(tone, start), u32(tone, start + 4)


def labels_read(data, names, partial=False):
    assert u32(data, 0) == 1
    entries = list(struct.iter_unpack('<II', data[8:]))
    assert u32(data, 4) == len(entries)
    if not partial:
        assert {value >> 8 for _, value in entries} == set(range(len(names)))
    for crc, value in entries:
        assert 0 <= (value >> 8) < len(names)
        assert crc == zlib.crc32(names[value >> 8].lower().encode())
        assert value & 0xff == len(names[value >> 8].encode())
    return entries


def sqb_read(data):
    assert data[:4] == b'SQB\0'
    version, count = struct.unpack_from('<HH', data, 4)
    assert version == 1 and u32(data, 8) == count * 4
    base = 12 + count * 4
    offsets = list(struct.unpack_from('<' + 'I' * count, data, 12)) + [len(data) - base]
    assert offsets[0] == 0 and offsets == sorted(offsets)
    return [data[base + offsets[i]:base + offsets[i + 1]] for i in range(count)]


def read_bank(stem: Path, partial_labels: bool = False):
    stem = Path(stem)
    entries = audio_read(Path(str(stem) + '.nus3audio').read_bytes())
    chunks = bank_read(Path(str(stem) + '.nus3bank').read_bytes())
    labels = labels_read(Path(str(stem) + '.tonelabel').read_bytes(), [n for n, _ in entries], partial_labels)
    return entries, chunks, labels


def append_tones(donor_stem: Path, recipient_stem: Path, dest_stem: Path, wanted: list) -> dict:
    """Append the named donor tones (sample bytes and tone records unchanged) to the recipient bank."""
    donor, chunks_d, labels_d = read_bank(donor_stem, partial_labels=True)
    names = [n for n, _ in donor]
    dc = dict(chunks_d)
    tones_d = tones_read(dc[b'TONE'])
    wanted_l = [w.lower() for w in wanted]
    selected = [names.index(next(n for n in names if n.lower() == w)) for w in wanted_l]
    for i in selected:
        assert tone_kind(tones_d[i], names) == (0, 8), f'{names[i]} is not a single-sample tone'

    original, chunks_r, labels_r = read_bank(recipient_stem)
    rc = dict(chunks_r)
    for tag in (b'GRP ', b'DTON', b'PACK'):
        assert rc[tag] == dc[tag], f'{Path(recipient_stem).name}: {tag!r} differs from the donor bank'
    tones_r = tones_read(rc[b'TONE'])
    present = {a.lower() for a, _ in original}
    assert not (present & set(wanted_l)), f'{Path(recipient_stem).name}: a requested tone already exists'
    entries = original + [donor[i] for i in selected]
    assert len({n.lower() for n, _ in entries}) == len(entries), 'tone name collision'
    mapping = {i: len(original) + j for j, i in enumerate(selected)}
    labels = list(labels_r) + [(crc, mapping[value >> 8] << 8 | (value & 255))
                               for crc, value in labels_d if value >> 8 in mapping]
    labels.sort()
    label_bytes = pack(1) + pack(len(labels)) + b''.join(struct.pack('<II', *p) for p in labels)
    labels_read(label_bytes, [n for n, _ in entries])
    audio_bytes = audio_write(entries)
    bank_bytes = bank_write([(tag, tones_write(tones_r + [tones_d[i] for i in selected]) if tag == b'TONE' else data)
                             for tag, data in chunks_r])
    dest_stem = Path(dest_stem)
    dest_stem.parent.mkdir(parents=True, exist_ok=True)
    Path(str(dest_stem) + '.nus3audio').write_bytes(audio_bytes)
    Path(str(dest_stem) + '.tonelabel').write_bytes(label_bytes)
    Path(str(dest_stem) + '.nus3bank').write_bytes(bank_bytes)

    back, chunks_back, labels_back = read_bank(dest_stem)
    cb = dict(chunks_back)
    assert back[:len(original)] == original, 'a pre-existing sample changed'
    assert back[len(original):] == [donor[i] for i in selected], 'an appended sample differs from the donor'
    assert cb[b'BINF'] == rc[b'BINF'] and cb[b'PROP'] == rc[b'PROP'], 'recipient identity changed'
    assert tones_read(cb[b'TONE'])[:len(tones_r)] == tones_r, 'a pre-existing tone record changed'
    assert tones_read(cb[b'TONE'])[len(tones_r):] == [tones_d[i] for i in selected]
    kept = {(crc, value) for crc, value in labels_back if value >> 8 < len(original)}
    assert kept == set(labels_r), 'a pre-existing tone label was lost or rebased'
    assert {zlib.crc32(w.encode()) for w in wanted_l} <= {crc for crc, _ in labels_back}, 'appended tones do not resolve'
    return {'recipient': Path(recipient_stem).name, 'retained_tones': len(original),
            'appended': [names[i] for i in selected],
            'appended_sample_sha256': {names[i]: sha(donor[i][1]) for i in selected},
            'output_sha256': {'nus3audio': sha(audio_bytes), 'nus3bank': sha(bank_bytes), 'tonelabel': sha(label_bytes)}}


def build_sound() -> dict:
    report = {'banks': []}
    for stem in SE_RECIPIENT_STEMS:
        report['banks'].append(append_tones(EXTRACTED / SE_DONOR_STEM, EXTRACTED / stem,
                                            REFERENCE / 'sound' / Path(stem).relative_to('sound'), SE_TONES)
                               | {'stem': stem})
    # None of the nine names is a sequence key in the donor table (they are plain PLAY_SE / PLAY_STATUS /
    # PLAY_STEP / PLAY_LANDING_SE tones), so the Gunner's sequence file needs no record. Measured, not assumed.
    keys = {int.from_bytes(r[:8], 'little') for r in sqb_read((EXTRACTED / SQB_DONOR).read_bytes())}
    assert not (keys & {hash40(n) for n in SE_TONES}), 'a grenade tone has a donor sequence record'
    report['donor_sequence_records'] = len(keys)
    report['sequence_records_needed'] = 0
    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def config_additions() -> dict:
    files = {'fighter/miigunner/c00': [f'{GUNNER_BODY}/{owned_clip(k)}' for k in KINDS]}
    for slot in MII_SLOTS:
        files.setdefault(f'fighter/miigunner/{slot}', [])
        files[f'fighter/miigunner/{slot}'] += (
            [f'fighter/miigunner/model/{PIN_ARTICLE}/{slot}/{n}' for n in PIN_MODEL_FILES]
            + [f'fighter/miigunner/motion/{PIN_ARTICLE}/{slot}/{n}' for n in PIN_CLIPS + ['motion_list.bin']])
    return {'new-dir-files': files}


def build() -> None:
    print(f'Building MV-{UNIT} assets into {rel(OUT)}')
    ensure_extracted()
    retarget = retarget_all()
    print(f'retarget: {len(retarget)} clips')
    mlist = build_motion_list()
    print(f"motion list: {mlist['vanilla_entries']} + {mlist['entries'] - mlist['vanilla_entries']} entries")
    pin = build_pin()
    print(f"pin: {pin['file_count']} files in {len(pin['slots'])} slots")
    sound = build_sound()
    print(f"sound: {len(sound['banks'])} banks, {len(SE_TONES)} tones each")
    TABLES.mkdir(parents=True, exist_ok=True)
    (TABLES / 'retarget_report.json').write_text(json.dumps(retarget, indent=1) + '\n', encoding='utf-8')
    files = {}
    for root in (PACKAGE, REFERENCE):
        for p in sorted(root.rglob('*')):
            if p.is_file():
                files[p.relative_to(OUT).as_posix()] = {'bytes': p.stat().st_size, 'sha256': sha_file(p)}
    manifest = {
        'unit': UNIT, 'task_id': 'MV-' + UNIT, 'entry': 'special_neutral', 'donor': 'snake',
        'inputs_pinned': PINS,
        'motion_list': mlist,
        'clips': {k: {'clip': v['clip'], 'sha256': v['clip_sha256'], 'frames': v['frames'], 'partial': v['partial']}
                  for k, v in retarget.items()},
        'pin': pin,
        'sound': sound,
        'config_needed_by_coordinator': config_additions(),
        'files': files,
    }
    MANIFEST.write_text(json.dumps(manifest, indent=1) + '\n', encoding='utf-8')
    print(f'manifest: {rel(MANIFEST)} ({len(files)} files)')


def main(argv) -> int:
    if len(argv) >= 2 and argv[1] == 'apply-motion':
        ensure_extracted()
        Path(argv[3]).write_bytes(apply_motion(Path(argv[2]).read_bytes()))
        print(f'wrote {argv[3]} (+{len(KINDS)} entries)')
        return 0
    if len(argv) >= 2 and argv[1] == 'apply-sound':
        ensure_extracted()
        print(json.dumps(append_tones(EXTRACTED / SE_DONOR_STEM, Path(argv[2]), Path(argv[3]), SE_TONES), indent=1))
        return 0
    build()
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
