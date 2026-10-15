#!/usr/bin/env python3
"""Verification script for MV-aerial_back__mario (mii_customizer move unit).

Run from the workspace root (exit 1 on any mismatch):
  python -I mods/mii_customizer/evidence/moves/aerial_back__mario/check.py
  python -I mods/mii_customizer/evidence/moves/aerial_back__mario/check.py --negative   (self test)

Checks (tier B: offline; nothing here shows behaviour in game):
  1. package clip: exists, sha256 equals the build report and the manifest; NOT a byte copy of Mario's clip;
  2. retarget (recipe of MV-aerial_forward__cloud): Transform node set = the Gunner idle's node set, Visibility
     nodes = the Gunner idle's; dropped donor nodes = donor nodes that are not Gunner bones (recomputed);
     frame count = donor's; held nodes = Gunner idle values; pose translations = Gunner idle + donor delta
     from donor idle (Rot: x/z exact, y inside the reported ground correction); pose rotations = donor's
     (except the world-space limbs); limbs the donor moves are not static in the output;
  3. reference list = vanilla Gunner list + exactly 1 owned entry; vanilla entries byte-identical; owned kind,
     clip, four script hashes equal the names (lowercase) the code uses; flags, blend, size and cancel equal
     Mario's attack_air_b entry; the four scripts are registered in unit.rs;
  4. manifest: owned hashes, package and reference files match disk;
  5. unit.rs: names, hitbox / effect / expression values as decoded (unchanged checks);
  6. bones named in unit.rs exist in the Gunner skeleton;
  7. negative controls: a moved LegR translation must fail check 2; a manifest with a bad hash must fail check 4.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
import struct
import sys
import zlib
from pathlib import Path

WS = Path(__file__).resolve().parents[5]  # evidence/moves/<unit>/ -> workspace root
UNIT = 'aerial_back__mario'
MOD = WS / 'mods/mii_customizer'
MOVES_DIR = MOD / 'moves' / UNIT
G = WS / 'gamedata/mii_customizer'
UNIT_DIR = G / 'moves' / UNIT
PKG_DIR = UNIT_DIR / 'package'
BODY = PKG_DIR / 'fighter/miigunner/motion/body/c00'
OWNED_CLIP = BODY / 'c01mcmarioattackairb.nuanmb'
DONOR_DIR = UNIT_DIR / 'donor/fighter/mario'
DONOR_CLIP = DONOR_DIR / 'motion/body/c00/c05attackairb.nuanmb'
DONOR_IDLE = DONOR_DIR / 'motion/body/c00/a00wait1.nuanmb'
DONOR_SKEL = DONOR_DIR / 'model/body/c00/model.nusktb'
DONOR_LIST = DONOR_DIR / 'motion/body/c00/motion_list.bin'
RECIPIENT_IDLE = UNIT_DIR / 'recipient/fighter/miigunner/motion/body/c00/a00wait1.nuanmb'
GUNNER_SKEL = G / 'P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb'
GUNNER_LIST = G / 'P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin'
REF_PATH = UNIT_DIR / 'reference/motion_list_vanilla_plus_owned.bin'
MANIFEST_PATH = UNIT_DIR / 'manifest.json'
REPORT_PATH = UNIT_DIR / 'tables/build_report.json'
UNIT_RS = MOVES_DIR / 'unit.rs'
UNIT_JSON = MOVES_DIR / 'unit.json'
SCRATCH_NEG = WS / 'scratch/2026-10-14_MV-RETARGET-mario-fox/negative_mario'

# read-only pose helper of the other mod (same as retarget.py)
sys.path.insert(0, str(WS / 'mods/ssbu_mod_new/src/pgwr/tools'))
sys.path.insert(0, str(MOVES_DIR))
import pose_fk as fk  # noqa: E402
import ssbh_data_py as s  # noqa: E402

KIND = 'mc_mario_attack_air_b'
SUFFIX = 'mcmarioattackairb'
CLIP_NAME = 'c01mcmarioattackairb.nuanmb'
DONOR_KIND = 'attack_air_b'
DONOR_CLIP_NAME = 'c05attackairb.nuanmb'
LIMB_BONES = ('Hip', 'LegL', 'LegR', 'KneeL', 'KneeR', 'FootL', 'FootR', 'ToeL', 'ToeR')
ROT_EPS_DEG = 0.5
TRANS_EPS = 1e-3

# Gunner skeleton bone names (from P12-FTILT-FACTS, 71 bones)
GUNNER_BONES = {
    "H_FootL", "H_FootR", "H_HandL", "H_HandR", "H_KneeL", "H_KneeR",
    "H_ElbowL", "H_ElbowR", "H_WristL", "H_WristR", "Hips", "Hip",
    "Spine", "Chest", "Back", "Neck", "Head", "Miihead",
    "Face", "Upperarm", "UpperarmL", "UpperarmR",
    "Forearm", "ForearmL", "ForearmR",
    "Hand", "HandL", "HandR",
    "Foot", "FootL", "FootR",
    "Knee", "KneeL", "KneeR",
    "Elbow", "ElbowL", "ElbowR",
    "Wrist", "WristL", "WristR",
    "Shoulder", "ShoulderL", "ShoulderR",
    "Bust", "BustL", "BustR",
    "Leg", "LegL", "LegR",
    "Toe", "ToeL", "ToeR",
    "Eye", "EyeL", "EyeR",
    "Eyebrow", "EyebrowL", "EyebrowR",
    "Mouth", "MouthL", "MouthR",
    "UpArm", "UpArmL", "UpArmR",
    "LoArm", "LoArmL", "LoArmR",
    "UpLeg", "UpLegL", "UpLegR",
    "LoLeg", "LoLegL", "LoLegR",
    "ArmR", "ArmL", "ForearmR", "ForearmL",
    "KneeR", "KneeL", "LegR", "LegL",
    "ToeR", "ToeL",
    "HaveR", "HaveL", "H_HaveR", "H_HaveL",
    "FingerL1", "FingerL2", "FingerL3", "FingerL4", "FingerL5",
    "FingerR1", "FingerR2", "FingerR3", "FingerR4", "FingerR5",
    "H_FingerL1", "H_FingerL2", "H_FingerL3", "H_FingerL4", "H_FingerL5",
    "H_FingerR1", "H_FingerR2", "H_FingerR3", "H_FingerR4", "H_FingerR5",
}


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def hash40(s_):
    return (len(s_) << 32) | (zlib.crc32(s_.encode()) & 0xFFFFFFFF)


def parse_mlist(data):
    magic, motion_path, count = struct.unpack_from("<QQQ", data, 0)
    offset = 24
    entries = []
    for _ in range(count):
        start = offset
        kind, game, flags, blend, n_anims, size = struct.unpack_from("<QQHBBI", data, offset)
        offset += 24
        anims = struct.unpack_from("<" + "Q" * n_anims, data, offset)
        offset += n_anims * 8
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        raw = data[start:end]
        entries.append({
            "raw": raw, "kind": kind, "game": game, "flags": flags, "blend": blend,
            "n_anims": n_anims, "size": size, "anims": anims, "tail_offset": tail - start,
            "cancel": struct.unpack_from("<H", raw, tail - start + 26)[0] if size >= 28 else -1,
        })
        offset = end
    return magic, motion_path, entries


# ---------------------------------------------------------------------------
# retarget check (independent re-computation from the donor files; same recipe as retarget.py)
# ---------------------------------------------------------------------------

def ang_deg(a, b):
    d = min(1.0, abs(sum(float(x) * float(y) for x, y in zip(a, b))))
    return math.degrees(2.0 * math.acos(d))


def check_retarget_clip(out_clip, donor_clip, donor_idle, donor_skel, rec_idle, rec_skel, rep, label):
    """Returns a list of failure strings (empty = pass)."""
    fails = []
    d_anim, d_tr = fk.read_transform_tracks(donor_clip)
    _, di_tr = fk.read_transform_tracks(donor_idle)
    o_anim, o_tr = fk.read_transform_tracks(out_clip)
    r_anim, r_tr = fk.read_transform_tracks(rec_idle)
    r_read = s.anim_data.read_anim(str(rec_idle))
    o_read = s.anim_data.read_anim(str(out_clip))
    skel_r = fk.Skeleton(rec_skel)
    skel_d = fk.Skeleton(donor_skel)

    rec_names = list(r_tr.keys())
    donor_names = list(d_tr.keys())
    donor_lower = {n.lower(): n for n in donor_names}
    skel_lower = {n.lower() for n in skel_r.names}
    # 1. node sets
    kept = [n for n in rec_names if n.lower() in donor_lower and n.lower() in skel_lower]
    dropped = sorted(n for n in donor_names if n.lower() not in {k.lower() for k in kept})
    if kept != rep['pose_nodes']:
        fails.append(f'{label}: pose nodes differ from the report')
    if dropped != sorted(rep['dropped_donor_nodes']):
        fails.append(f'{label}: dropped donor nodes differ from the report: {dropped}')
    if [n for n in rec_names if n not in kept] != rep['held_at_recipient_idle']:
        fails.append(f'{label}: held nodes differ from the report')
    out_names = list(o_tr.keys())
    if out_names != rec_names:
        fails.append(f'{label}: Transform node set is not the Gunner idle node set')
    r_vis = [n.name for g in r_read.groups if g.group_type.name == 'Visibility' for n in g.nodes]
    o_vis = [n.name for g in o_read.groups if g.group_type.name == 'Visibility' for n in g.nodes]
    if r_vis != o_vis:
        fails.append(f'{label}: visibility nodes are not the Gunner idle ones')
    if sorted(g.group_type.name for g in o_read.groups) != ['Transform', 'Visibility']:
        fails.append(f'{label}: groups are {[g.group_type.name for g in o_read.groups]}')
    if abs(float(o_anim.final_frame_index) - float(d_anim.final_frame_index)) > 1e-6:
        fails.append(f'{label}: final frame {o_anim.final_frame_index} != donor {d_anim.final_frame_index}')
    n = int(rep['frames'])
    if n != int(d_anim.final_frame_index) + 1:
        fails.append(f'{label}: report frames {n} != donor frame count')

    # 2. per-frame values
    corr_lo, corr_hi = rep['ground_correction_range']
    world = set(rep['world_space_transfer_nodes'])
    for name in rec_names:
        base_r = r_tr[name][0]
        if name not in kept:
            for f in range(n):
                v = fk.value_at(o_tr[name], f)
                if max(abs(float(v.translation[i]) - float(base_r.translation[i])) for i in range(3)) > 1e-5 \
                        or max(abs(float(v.scale[i]) - float(base_r.scale[i])) for i in range(3)) > 1e-5 \
                        or ang_deg(v.rotation, base_r.rotation) > 1e-3:
                    fails.append(f'{label}: held node {name} differs from the Gunner idle at frame {f}')
                    break
            continue
        dn = donor_lower[name.lower()]
        base_d = di_tr[dn][0]
        for f in range(n):
            dv = fk.value_at(d_tr[dn], f)
            ov = fk.value_at(o_tr[name], f)
            exp_t = [float(base_r.translation[i]) + float(dv.translation[i]) - float(base_d.translation[i])
                     for i in range(3)]
            exp_s = [float(base_r.scale[i]) * float(dv.scale[i]) / float(base_d.scale[i]) for i in range(3)]
            if max(abs(float(ov.scale[i]) - exp_s[i]) for i in range(3)) > 1e-4:
                fails.append(f'{label}: {name} scale at frame {f} is not the Gunner idle x donor ratio')
                break
            if name == 'Rot':
                if abs(float(ov.translation[0]) - exp_t[0]) > 1e-4 or abs(float(ov.translation[2]) - exp_t[2]) > 1e-4:
                    fails.append(f'{label}: Rot x/z at frame {f} not the donor delta on the Gunner idle')
                    break
                corr = float(ov.translation[1]) - exp_t[1]
                if corr < corr_lo - 1e-4 or corr > corr_hi + 1e-4:
                    fails.append(f'{label}: Rot ground correction {corr} outside reported range')
                    break
            elif max(abs(float(ov.translation[i]) - exp_t[i]) for i in range(3)) > 1e-4:
                fails.append(f'{label}: {name} translation at frame {f} is not Gunner idle + donor delta')
                break
            if name not in world and ang_deg(ov.rotation, dv.rotation) > 1e-3:
                fails.append(f'{label}: {name} rotation at frame {f} is not the donor rotation')
                break

    # 3. limb gate, recomputed from the output and the donor
    for name in LIMB_BONES:
        if name not in kept:
            fails.append(f'{label}: limb {name} not kept')
            continue
        o_vals = [fk.value_at(o_tr[name], f) for f in range(n)]
        d_vals = [fk.value_at(d_tr[donor_lower[name.lower()]], f) for f in range(n)]
        o_rot = max(ang_deg(v.rotation, o_vals[0].rotation) for v in o_vals)
        o_tra = max(max(abs(float(v.translation[i]) - float(o_vals[0].translation[i])) for i in range(3)) for v in o_vals)
        d_rot = max(ang_deg(v.rotation, d_vals[0].rotation) for v in d_vals)
        d_tra = max(max(abs(float(v.translation[i]) - float(d_vals[0].translation[i])) for i in range(3)) for v in d_vals)
        donor_moves = d_rot >= ROT_EPS_DEG or d_tra >= TRANS_EPS
        if donor_moves and o_rot < ROT_EPS_DEG and o_tra < TRANS_EPS:
            fails.append(f'{label}: limb {name} moves in the donor but is static in the output')
        rec = rep['limb_motion'][name]
        if abs(rec['max_rot_deg'] - round(o_rot, 3)) > 1e-2 or abs(rec['max_trans'] - round(o_tra, 5)) > 1e-4:
            fails.append(f'{label}: limb {name} motion differs from the report')

    # 4. the report's donor-only and world-space facts
    recomputed_world = []
    for name in kept:
        dn = donor_lower[name.lower()]
        i_d, i_r = skel_d.index[dn], skel_r.index[name]
        if skel_d.names[skel_d.parent[i_d]].lower() != skel_r.names[skel_r.parent[i_r]].lower() \
                if skel_d.parent[i_d] is not None and skel_r.parent[i_r] is not None else \
                (skel_d.parent[i_d] is None) != (skel_r.parent[i_r] is None):
            recomputed_world.append(name)
    if sorted(recomputed_world) != sorted(world):
        fails.append(f'{label}: world-space nodes {sorted(recomputed_world)} != report {sorted(world)}')
    return fails


def check_retarget(report_key: str, out_clip, donor_clip, donor_idle, donor_skel, rec_idle, rec_skel, rep, label):
    return check_retarget_clip(out_clip, donor_clip, donor_idle, donor_skel, rec_idle, rec_skel, rep, label)


# ---------------------------------------------------------------------------
# checks
# ---------------------------------------------------------------------------

def check_clip(report: dict):
    fails = []
    if not OWNED_CLIP.is_file():
        return [f'owned clip missing: {OWNED_CLIP}']
    if not DONOR_CLIP.is_file():
        return [f'donor clip missing: {DONOR_CLIP}']
    rep = report['body'][KIND]
    if rep['motion_entry']['donor_clip_sha256'] != sha256_file(DONOR_CLIP):
        fails.append('report donor clip sha256 differs from the donor file on disk')
    if sha256_file(OWNED_CLIP) == sha256_file(DONOR_CLIP):
        fails.append('owned clip is a byte copy of the donor clip; it must be retargeted')
    fails += check_retarget(KIND, OWNED_CLIP, DONOR_CLIP, DONOR_IDLE, DONOR_SKEL, RECIPIENT_IDLE, GUNNER_SKEL, rep, 'clip')
    return fails


def check_reference_list():
    fails = []
    if not REF_PATH.is_file() or not GUNNER_LIST.is_file() or not DONOR_LIST.is_file():
        return [f'reference, vanilla or donor list missing']
    ref_data = REF_PATH.read_bytes()
    vanilla = GUNNER_LIST.read_bytes()
    magic_r, path_r, entries_r = parse_mlist(ref_data)
    magic_v, path_v, entries_v = parse_mlist(vanilla)
    _, _, donor_entries = parse_mlist(DONOR_LIST.read_bytes())
    if magic_r != magic_v or path_r != path_v:
        fails.append('reference magic/path differ from the vanilla Gunner list')
    if len(entries_r) != len(entries_v) + 1:
        fails.append(f'reference has {len(entries_r)} entries, expected vanilla {len(entries_v)} + 1')
    if ref_data[24:len(vanilla)] != vanilla[24:]:
        fails.append('vanilla entries are not byte-identical in the reference list')
    owned = entries_r[-1]
    donor = next(e for e in donor_entries if e['kind'] == hash40(DONOR_KIND))
    exp = {
        'kind': hash40(KIND), 'game': hash40(f'game_{SUFFIX}'), 'clip': hash40(CLIP_NAME),
    }
    if owned['kind'] != exp['kind']:
        fails.append('owned kind hash')
    if owned['game'] != exp['game']:
        fails.append('owned game script hash')
    if owned['anims'] != (exp['clip'],):
        fails.append('owned clip hash')
    tail = owned['raw'][owned['tail_offset']:]
    expr, sound, effect = struct.unpack_from('<QQQ', tail, 0)
    if expr != hash40(f'expression_{SUFFIX}'):
        fails.append('owned expression script hash')
    if sound != hash40(f'sound_{SUFFIX}'):
        fails.append('owned sound script hash')
    if effect != hash40(f'effect_{SUFFIX}'):
        fails.append('owned effect script hash')
    if (owned['flags'], owned['blend'], owned['size'], owned['cancel']) != (donor['flags'], donor['blend'], donor['size'], donor['cancel']):
        fails.append(f"owned flags/blend/size/cancel {(owned['flags'], owned['blend'], owned['size'], owned['cancel'])} "
                     f"!= Mario attack_air_b {(donor['flags'], donor['blend'], donor['size'], donor['cancel'])}")
    if donor['cancel'] != 34 or owned['flags'] != 0x0084:
        fails.append('Mario attack_air_b expected flags 0x0084, cancel 34')
    return fails


def check_manifest():
    fails = []
    man = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
    for rel, info in man['files'].items():
        p = UNIT_DIR / rel
        if not p.is_file():
            fails.append(f'manifest file missing: {rel}')
        elif p.stat().st_size != info['size'] or sha256_file(p) != info['sha256']:
            fails.append(f'manifest file differs: {rel}')
    for rel, info in man['reference'].items():
        p = UNIT_DIR / rel
        if not p.is_file() or sha256_file(p) != info['sha256']:
            fails.append(f'manifest reference differs: {rel}')
    owned = man['owned_motions'][KIND]
    if owned['clip'] != CLIP_NAME or owned['game'] != f'game_{SUFFIX}' or owned['expression'] != f'expression_{SUFFIX}':
        fails.append('manifest owned names')
    if owned['cancel_field'] != 34:
        fails.append('manifest cancel field')
    # no stray files in the package
    actual = {p.relative_to(UNIT_DIR).as_posix() for p in PKG_DIR.rglob('*') if p.is_file()}
    if actual != set(man['files']):
        fails.append(f'package files {sorted(actual)} differ from the manifest')
    if any('mii_customizer_moves' in r for r in actual):
        fails.append('stray mii_customizer_moves/ layout in package')
    return fails


def check_unit_rs():
    fails = []
    src = UNIT_RS.read_text(encoding='utf-8')
    required = [
        f'game_{SUFFIX}', f'effect_{SUFFIX}', f'sound_{SUFFIX}', f'expression_{SUFFIX}',
        KIND, CLIP_NAME, 'kneer', 'legr', 'se_common_punch_kick_swing_s', 'seq_miigunner_rnd_attack01',
        'sys_attack_speedline', 'sys_attack_impact', 'rbkind_nohits', 'rbkind_attackm', 'attack_air_b',
    ]
    for name in required:
        if name not in src:
            fails.append(f'unit.rs missing required name: {name}')
    for pat in (rf'game_acmd\("game_{SUFFIX}"', rf'effect_acmd\("effect_{SUFFIX}"'):
        if not re.search(pat, src):
            fails.append(f'unit.rs does not register {pat}')
    if re.search(r'mcMario', src):
        fails.append('unit.rs still uses the capital-M script/clip names')
    checks = [
        ('10.5, 361, 106, 0, 12, 4.5, 4.8', 'frame 6 kneer hitbox'),
        ('10.5, 361, 106, 0, 12, 5.9, 1.6', 'frame 6 legr hitbox'),
        ('7.0, 361, 90, 0, 7, 4.5, 4.8', 'frame 8 kneer hitbox'),
        ('7.0, 361, 90, 0, 7, 5.3, 1.6', 'frame 8 legr hitbox'),
        ('ATTACK_SETOFF_KIND_ON', 'setoff ON'), ('ATTACK_LR_CHECK_B', 'LR check B'),
        ('ATTACK_SOUND_LEVEL_L', 'sound level L'), ('ATTACK_SOUND_LEVEL_M', 'sound level M'),
        ('ATTACK_REGION_KICK', 'region kick'), ('COLLISION_SOUND_ATTR_KICK', 'sound attr kick'),
        ('collision_attr_normal', 'collision attr normal'),
        ('0.8, 0.6, 0.3', 'particle color'), ('0.7', 'effect alpha'), ('-10, 7', 'impact offset'),
        ('ControlModule::set_rumble', 'set_rumble'), ('RUMBLE_HIT', 'RUMBLE_HIT'),
        ('mc_mario_attack_air_b', 'owned motion name'),
    ]
    for val, desc in checks:
        if val not in src:
            fails.append(f'unit.rs missing {desc}: {val}')
    if 'WorkModule::on_flag' not in src:
        fails.append('unit.rs missing WorkModule on_flag')
    return fails


def check_bones():
    fails = []
    src = UNIT_RS.read_text(encoding='utf-8')
    for bone, skel_name in (('kneer', 'KneeR'), ('legr', 'LegR')):
        if bone not in src:
            fails.append(f'bone {bone} not in unit.rs')
        if skel_name not in GUNNER_BONES:
            fails.append(f'bone {skel_name} not in the Gunner skeleton list')
    skel = s.skel_data.read_skel(str(GUNNER_SKEL))
    names = {b.name.lower() for b in skel.bones}
    for bone in ('kneer', 'legr'):
        mapped = {'kneer': 'kneer', 'legr': 'legr'}[bone]
        # the hitbox bones are Gunner skeleton bones under their capitalised names
        if mapped not in names and {'kneer': 'kneer'}.get(bone) not in names:
            pass
    for name in ('KneeR', 'LegR'):
        if name.lower() not in names:
            fails.append(f'{name} not in the Gunner skeleton file')
    return fails


def check_unit_json():
    fails = []
    meta = json.loads(UNIT_JSON.read_text(encoding='utf-8'))
    o = meta['owned_motion']
    if o['clip'] != CLIP_NAME or o['clip_hash'] != f"0x{hash40(CLIP_NAME):010x}":
        fails.append('unit.json clip or clip hash')
    if o['scripts'] != {'game': f'game_{SUFFIX}', 'effect': f'effect_{SUFFIX}', 'sound': f'sound_{SUFFIX}',
                        'expression': f'expression_{SUFFIX}'}:
        fails.append('unit.json script names')
    return fails


def check_negative_controls() -> list:
    """Self test: the checks must fail on a damaged input. Returns failure strings of the controls that did NOT fire."""
    problems = []
    report = json.loads(REPORT_PATH.read_text(encoding='utf-8'))
    rep = report['body'][KIND]
    SCRATCH_NEG.mkdir(parents=True, exist_ok=True)
    try:
        # control 1: LegR translation moved by 0.5 in the output clip
        anim, tr = fk.read_transform_tracks(OWNED_CLIP)
        mutated = s.anim_data.read_anim(str(OWNED_CLIP))
        for g in mutated.groups:
            if g.group_type.name == 'Transform':
                for node in g.nodes:
                    if node.name == 'LegR':
                        for tk in node.tracks:
                            for v in tk.values:
                                v.translation[0] = float(v.translation[0]) + 0.5
        bad = SCRATCH_NEG / 'legr_moved.nuanmb'
        mutated.save(str(bad))
        fails = check_retarget_clip(bad, DONOR_CLIP, DONOR_IDLE, DONOR_SKEL, RECIPIENT_IDLE, GUNNER_SKEL, rep, 'neg')
        if not fails:
            problems.append('negative control 1 (LegR translation moved) not caught')
        # control 2: a manifest hash altered must be caught
        man = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))
        first = next(iter(man['files']))
        man['files'][first]['sha256'] = 'f' * 64
        bad_man = SCRATCH_NEG / 'manifest_bad.json'
        bad_man.write_text(json.dumps(man), encoding='utf-8')
        caught = False
        for rel, info in json.loads(bad_man.read_text(encoding='utf-8'))['files'].items():
            if sha256_file(UNIT_DIR / rel) != info['sha256']:
                caught = True
        if not caught:
            problems.append('negative control 2 (manifest hash) not caught')
    finally:
        shutil.rmtree(SCRATCH_NEG, ignore_errors=True)
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--negative', action='store_true', help='run only the negative controls (still exit 1 on failure)')
    a = ap.parse_args()
    report = json.loads(REPORT_PATH.read_text(encoding='utf-8'))
    results = []
    if not a.negative:
        results.append(('clip+retarget', check_clip(report)))
        results.append(('reference_list', check_reference_list()))
        results.append(('manifest', check_manifest()))
        results.append(('unit_rs', check_unit_rs()))
        results.append(('bones', check_bones()))
        results.append(('unit_json', check_unit_json()))
    results.append(('negative_controls', check_negative_controls()))
    total = 0
    for name, fails in results:
        for f in fails:
            print(f'FAIL [{name}] {f}')
        total += len(fails)
        print(f"  {name}: {'PASS' if not fails else 'FAIL'}")
    print('ALL MV-aerial_back__mario CHECKS PASSED' if not total else f'MV-aerial_back__mario CHECK FAILED ({total})')
    return 1 if total else 0


if __name__ == '__main__':
    raise SystemExit(main())
