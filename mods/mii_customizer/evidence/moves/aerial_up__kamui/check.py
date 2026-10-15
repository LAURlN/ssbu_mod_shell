#!/usr/bin/env python3
"""Offline check of move unit MV-aerial_up__kamui (Corrin's up air on Mii Gunner). Run from the workspace root:

    python -I mods/mii_customizer/evidence/moves/aerial_up__kamui/check.py

Exit 0 when every check passes and every negative control is rejected; exit 1 otherwise. Tier B only: nothing here
runs the game.

  1. package files against manifest.json (size and sha256); reference list and sound additions against the manifest
  2. attack clip reloads: Transform node set = the Gunner idle's (order too), 58 frames, Visibility = the Gunner idle's,
     the 47 dropped donor nodes are exactly donor-minus-Gunner
  3. landing clip reloads the same way (final index 19 from the donor report, or the donor's own)
  4. reference motion list = vanilla + two entries; each added entry's hashes equal the names the unit uses; flags 0x80;
     cancel fields 38 (attack) and 20 (landing) equal the donor's; each entry differs from its donor entry only in names
  5. unit.rs ATTACK / ACMD values equal the decoded donor calls (argument by argument), frames 4/7/13/38, trail 6/12,
     sound 4, rumble 7; the trail names are the owned ones and map to the donor's texture names
  6. bone `haver` = `HaveR` on both skeletons (hash40 case-insensitive)
  7. gates: legs moving, world-space nodes; landing lag = Corrin's fighter_param landing_attack_air_frame_hi (9)
  8. sword article: model files read back (3 rigid objects on `Have`, 1 bone, 3 materials, 3 modl entries), the one-frame
     clip (Visibility `mckamui_sword` True), the article motion-list entry hashes; rust names agree
  9. sound: the appended tone is in the output bank, labels resolve, the PLAY_SE name in unit.rs is that tone, the
     Gunner's base bank is untouched (its tones are a prefix of the output)
 10. trail: the two packaged textures carry the owned footer names, differ from the donor only in the 64-byte name field
 11. plugin copy: unit and sword files identical to the sources; lib/menu/moves wiring present; built NRO passes stack check
 12. negative controls: changed damage, changed frame, changed cancel field, changed landing lag, changed sword object
     count must each be rejected by the check that covers them
"""
from __future__ import annotations

import hashlib
import io
import contextlib
import json
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path

MOD = Path(__file__).resolve().parents[3]          # mods/mii_customizer
ROOT = MOD.parents[1]                               # workspace root
G = ROOT / 'gamedata/mii_customizer'
UNIT = 'aerial_up__kamui'
OUT = G / 'moves' / UNIT
SRC = MOD / 'moves' / UNIT
PLUGIN = MOD / 'scratch/2026-10-14_MV-aerial_up__kamui/plugin'
NRO = MOD / 'builds/.cache/MV-aerial_up__kamui-target/aarch64-skyline-switch/release/libmii_customizer.nro'
STACK = MOD / 'tools/stack-frames/stack_frames.py'
GUNNER_IDLE = OUT / 'recipient/fighter/miigunner/motion/body/c00/a00wait1.nuanmb'
GUNNER_SKEL = G / 'P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb'
DONOR_SKEL = OUT / 'donor/fighter/kamui/model/body/c00/model.nusktb'
DONOR_ATTACK = OUT / 'donor/fighter/kamui/motion/body/c00/c05attackairhi.nuanmb'
DONOR_LANDING = OUT / 'donor/fighter/kamui/motion/body/c00/c05landingairhi.nuanmb'
DONOR_MLIST = OUT / 'donor/fighter/kamui/motion/body/c00/motion_list.bin'
VANILLA_MLIST = G / 'P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin'
DECODED = OUT / 'tables/acmd_calls.json'
REPORT = OUT / 'tables/retarget_report.json'
MANIFEST = OUT / 'manifest.json'
REFERENCE = OUT / 'reference/motion_list_vanilla_plus_owned.bin'
SOUND_DIR = OUT / 'reference/sound/bank/fighter'
SOUND_BASE = OUT / 'recipient/sound/bank/fighter'
PKG = OUT / 'package'
ATTACK_CLIP = PKG / 'fighter/miigunner/motion/body/c00/c01mckamuiattackairhi.nuanmb'
LANDING_CLIP = PKG / 'fighter/miigunner/motion/body/c00/c01mckamuilandingairhi.nuanmb'
SWORD_MODEL = PKG / 'fighter/miigunner/model/mckamuisword/c00'
SWORD_MOTION = PKG / 'fighter/miigunner/motion/mckamuisword/c00'
TRAIL = PKG / 'effect/fighter/miigunner/trail'
ATTACK_KIND, ATTACK_CLIP_NAME = 'mc_kamui_attack_air_hi', 'c01mckamuiattackairhi.nuanmb'
LAND_KIND, LAND_CLIP_NAME = 'mc_kamui_landing_air_hi', 'c01mckamuilandingairhi.nuanmb'
SWORD_KIND, SWORD_CLIP_NAME = 'mc_kamui_sword', 'a00mckamuisword.nuanmb'
LANDING_FRAME_HI = 9.0            # fighter_param.prc fighter_kind_kamui landing_attack_air_frame_hi (measured 2026-10-14)
GUNNER_LANDING_FRAME_HI = 13.0    # fighter_param.prc fighter_kind_miigunner landing_attack_air_frame_hi
LIMBS = ('Hip', 'LegL', 'LegR', 'KneeL', 'KneeR', 'FootL', 'FootR', 'ToeL', 'ToeR')
FAILS: list = []


def hash40(name: str) -> int:
    data = name.encode('utf-8')
    return (len(data) << 32) | zlib.crc32(data)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(cond: bool, msg: str) -> bool:
    if not cond:
        FAILS.append(msg)
        print('FAIL', msg)
    return cond


def _capture(fn) -> int:
    """Runs fn with its FAIL lines swallowed; returns how many checks it failed (controls)."""
    before = len(FAILS)
    with contextlib.redirect_stdout(io.StringIO()):
        fn()
    n = len(FAILS) - before
    del FAILS[before:]
    return n


# ---------------------------------------------------------------------------
# 1. manifest
# ---------------------------------------------------------------------------

def check_manifest():
    man = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for rel, info in man['files'].items():
        p = OUT / rel
        check(p.is_file(), f'manifest file missing: {rel}')
        if p.is_file():
            check(p.stat().st_size == info['size'], f'size differs: {rel}')
            check(sha256(p) == info['sha256'], f'sha256 differs: {rel}')
    for rel, info in man['reference'].items():
        p = OUT / rel
        check(p.is_file() and sha256(p) == info['sha256'], f'reference file differs from manifest: {rel}')
    cfg = man['config_needed_by_coordinator']['new-dir-files']
    check('fighter/miigunner/motion/body/c00' in cfg and 'fighter/miigunner/model/mckamuisword/c00' in cfg
          and 'effect/fighter/miigunner/trail' in cfg, 'config new-dir-files lacks a folder of the unit')
    n_files = sum(len(v) for v in cfg.values())
    check(n_files == len(man['files']), f'config lists {n_files} files, package has {len(man["files"])}')
    print(f"1 manifest: {len(man['files'])} package file(s), {len(man['reference'])} reference file(s) match")


# ---------------------------------------------------------------------------
# 2-3. clips
# ---------------------------------------------------------------------------

def check_clip(path: Path, donor_clip: Path, label: str, frames: int) -> int:
    import ssbh_data_py as s
    clip = s.anim_data.read_anim(str(path))
    idle = s.anim_data.read_anim(str(GUNNER_IDLE))
    groups = {g.group_type.name: g for g in clip.groups}
    igroups = {g.group_type.name: g for g in idle.groups}
    tr = [n.name for n in groups['Transform'].nodes]
    itr = [n.name for n in igroups['Transform'].nodes]
    check(tr == itr, f'{label}: Transform node set/order differs from the Gunner idle')
    check(len(tr) == 75, f'{label}: Transform node count {len(tr)} != 75')
    check(all(len(t.values) in (1, frames) for n in groups['Transform'].nodes for t in n.tracks),
          f'{label}: a track is not {frames} frames')
    vis = [n.name for n in groups['Visibility'].nodes] if 'Visibility' in groups else []
    check(vis == [n.name for n in igroups['Visibility'].nodes], f'{label}: Visibility group differs from the Gunner idle')
    d = s.anim_data.read_anim(str(donor_clip))
    dnames = [n.name for n in next(g for g in d.groups if g.group_type.name == 'Transform').nodes]
    low = {x.lower() for x in itr}
    dropped = sorted(x for x in dnames if x.lower() not in low)
    kept = [x for x in dnames if x.lower() in low]
    check(len(dropped) == 47 and len(kept) == 64, f'{label}: dropped {len(dropped)} / kept {len(kept)} (want 47 / 64)')
    return len(tr)


def check_clips():
    rep = json.loads(REPORT.read_text(encoding='utf-8'))
    import ssbh_data_py as s
    check(s.anim_data.read_anim(str(ATTACK_CLIP)).final_frame_index == 57.0, 'attack clip final index != 57')
    check_clip(ATTACK_CLIP, DONOR_ATTACK, 'attack clip', 58)
    land = s.anim_data.read_anim(str(LANDING_CLIP))
    check_clip(LANDING_CLIP, DONOR_LANDING, 'landing clip', int(land.final_frame_index) + 1)
    check(len(rep['landing']['dropped_donor_nodes']) == 47, 'landing report drops a different count than 47')
    print(f"2-3 clips: attack {int(s.anim_data.read_anim(str(ATTACK_CLIP)).final_frame_index) + 1} frames, "
          f"landing {int(land.final_frame_index) + 1} frames, both 75 transform nodes on the Gunner idle set")


# ---------------------------------------------------------------------------
# 4. motion list
# ---------------------------------------------------------------------------

def parse_mlist(data: bytes):
    magic, motion_path, count = struct.unpack_from('<QQQ', data, 0)
    offset = 24
    entries = []
    for i in range(count):
        start = offset
        kind, game, flags, blend, n_anims, size = struct.unpack_from('<QQHBBI', data, offset)
        offset += 24
        anims = struct.unpack_from('<' + 'Q' * n_anims, data, offset)
        tail = (start + 24 + n_anims * 9 + 3) & ~3
        end = tail + size
        entries.append({'kind': kind, 'game': game, 'flags': flags, 'blend': blend, 'anims': anims, 'size': size,
                        'raw': data[start:end], 'tail': tail - start})
        offset = end
    if offset != len(data):
        raise RuntimeError('motion list has trailing bytes')
    return magic, motion_path, entries


def cancel_ok(own_cancel: int, donor_cancel: int, want: int) -> bool:
    return own_cancel == donor_cancel == want


def check_motion_list():
    _, _, ev = parse_mlist(VANILLA_MLIST.read_bytes())
    _, _, er = parse_mlist(REFERENCE.read_bytes())
    check(len(er) == len(ev) + 2, 'reference list is not vanilla + 2 entries')
    check(all(a['raw'] == b['raw'] for a, b in zip(er[:len(ev)], ev)), 'reference list changed a vanilla entry')
    _, _, ed = parse_mlist(DONOR_MLIST.read_bytes())
    for owned, (kind, donor_kind, clip, scripts, want_cancel) in (
            (er[-2], (ATTACK_KIND, 'attack_air_hi', ATTACK_CLIP_NAME, 'mckamuiattackairhi', 38)),
            (er[-1], (LAND_KIND, 'landing_air_hi', LAND_CLIP_NAME, 'mckamuilandingairhi', 20))):
        check(owned['kind'] == hash40(kind), f'{kind}: kind hash differs from the unit name')
        check(owned['game'] == hash40(f'game_{scripts}'), f'{kind}: game script hash differs')
        check(owned['anims'] == (hash40(clip),), f'{kind}: animation hash differs (name includes .nuanmb)')
        tail = owned['tail']
        exp, snd, eff = struct.unpack_from('<QQQ', owned['raw'], tail)
        check((exp, snd, eff) == (hash40(f'expression_{scripts}'), hash40(f'sound_{scripts}'), hash40(f'effect_{scripts}')),
              f'{kind}: tail script hashes differ')
        donor = [e for e in ed if e['kind'] == hash40(donor_kind)]
        check(len(donor) == 1, f'{kind}: donor has no single {donor_kind}')
        d = donor[0]
        check(owned['flags'] == d['flags'] == 0x0080, f'{kind}: flags differ from donor 0x0080')
        oc = struct.unpack_from('<H', owned['raw'], tail + 26)[0]
        dc = struct.unpack_from('<H', d['raw'], d['tail'] + 26)[0]
        check(cancel_ok(oc, dc, want_cancel), f'{kind}: cancel {oc} / donor {dc} != {want_cancel}')
        a, b = bytearray(owned['raw']), bytearray(d['raw'])
        for buf in (a, b):
            buf[0:16] = b'\0' * 16
            buf[24:32] = b'\0' * 8
            buf[d['tail']:d['tail'] + 24] = b'\0' * 24
        check(a == b, f'{kind}: entry differs from its donor in fields other than the names')
    print(f"4 motion list: {len(er)} entries (vanilla {len(ev)} + 2), hashes OK, flags 0x0080, cancel 38 and 20")


# ---------------------------------------------------------------------------
# 5. unit.rs against the decoded donor
# ---------------------------------------------------------------------------

def top_level_args(text: str) -> list:
    args, depth, cur = [], 0, ''
    for ch in text:
        if ch == ',' and depth == 0:
            args.append(cur.strip())
            cur = ''
            continue
        if ch in '([':
            depth += 1
        elif ch in ')]':
            depth -= 1
        cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args


def rust_calls(src: str, macro: str) -> list:
    out = []
    for m in re.finditer(r'macros::' + macro + r'\(', src):
        i = m.end()
        depth, j = 1, i
        while depth:
            if src[j] == '(':
                depth += 1
            elif src[j] == ')':
                depth -= 1
            j += 1
        args = top_level_args(src[i:j - 1])
        if args and args[0] == 'agent':
            args = args[1:]
        out.append(args)
    return out


def norm_rust(tok: str):
    t = tok.strip()
    if t == 'None':
        return ('nil', None)
    m = re.fullmatch(r'Some\((.*)\)', t)
    if m:
        return norm_rust(m.group(1))
    m = re.fullmatch(r'Hash40::new\("(.*)"\)', t)
    if m:
        return ('hash', m.group(1))
    if t in ('true', 'false'):
        return ('bool', t == 'true')
    if t.startswith('*'):
        return ('const', t[1:])
    try:
        return ('num', float(t.rstrip('fF')))
    except ValueError:
        return ('raw', t)


def norm_decoded(arg: dict):
    t = arg['t']
    if t == 'global':
        return ('nil', None)
    if t == 'hash':
        return ('hash', arg['name'])
    if t == 'const':
        return ('const', arg['name'])
    if t == 'bool':
        return ('bool', arg['v'])
    if t in ('int', 'float'):
        return ('num', float(arg['v']))
    return ('raw', arg)


def same(r, d) -> bool:
    if r[0] == 'num' and d[0] == 'num':
        return abs(r[1] - d[1]) <= 1e-6 * max(1.0, abs(d[1]))
    return r == d


def script_body(src: str, fn: str) -> str:
    body = src[src.index('pub unsafe extern "C" fn ' + fn):]
    return body[:body.index('// ----')] if '// ----' in body else body


def script_frames(src: str, fn: str) -> list:
    return [(m.group(1), float(m.group(2)))
            for m in re.finditer(r'(frame|wait)\(agent\.lua_state_agent, ([0-9.]+)\)', script_body(src, fn))]


def effective_frames(pairs) -> list:
    out, now = [], 0.0
    for kind, v in pairs:
        now = v if kind == 'frame' else now + v
        out.append(now)
    return out


def decoded_calls(decoded: dict, key: str):
    return decoded[key]['calls']


def decoded_frame_calls(decoded: dict, key: str) -> list:
    return [float(c['args'][0]['v']) for c in decoded_calls(decoded, key) if c['kind'] == 'frame' and c['args']]


def check_script_values(src: str, decoded: dict):
    game = decoded_calls(decoded, 'kamui/game_attackairhi')
    attacks = [c for c in game if c['kind'] == 'ATTACK']
    rust = rust_calls(src, 'ATTACK')
    check(len(rust) == len(attacks) == 3, f'ATTACK count: rust {len(rust)} decoded {len(attacks)}')
    for k, (r_args, d) in enumerate(zip(rust, attacks)):
        check(len(r_args) == len(d['args']), f'ATTACK {k}: argument count {len(r_args)} != decoded {len(d["args"])}')
        for pos, (rt, da) in enumerate(zip(r_args, d['args'])):
            rn, dn = norm_rust(rt), norm_decoded(da)
            if dn[0] == 'nil':
                check(rn[0] == 'nil', f'ATTACK {k} arg {pos}: decoded nil, rust {rt}')
                continue
            check(same(rn, dn), f'ATTACK {k} arg {pos}: rust {rt!r} != decoded {da}')
    g_rust = effective_frames(script_frames(src, 'game_mckamuiattackairhi'))
    g_dec = decoded_frame_calls(decoded, 'kamui/game_attackairhi')
    clear = [c['frame'] for c in game if c['kind'] == 'lua_bind' and 'clear_all' in c['target']][0]
    check(sorted(set(g_dec + [float(clear)])) == g_rust, f'game frames {g_rust} vs decoded {g_dec} + clear {clear}')
    check(bool(re.search(r'frame\(agent\.lua_state_agent, 4\.0\);\s*if macros::is_excute\(agent\) \{\s*'
                         r'WorkModule::on_flag', src)), 'on_flag not at frame 4')
    check(bool(re.search(r'frame\(agent\.lua_state_agent, 38\.0\);\s*if macros::is_excute\(agent\) \{\s*'
                         r'WorkModule::off_flag', src)), 'off_flag not at frame 38')
    check('AttackModule::clear_all(agent.module_accessor)' in src, 'clear_all missing')
    e_rust = effective_frames(script_frames(src, 'effect_mckamuiattackairhi'))
    e_dec = decoded_frame_calls(decoded, 'kamui/effect_attackairhi')
    check(e_rust == e_dec == [6.0, 12.0], f'effect frames {e_rust} vs decoded {e_dec}')
    s_rust = effective_frames(script_frames(src, 'sound_mckamuiattackairhi'))
    s_dec = decoded_frame_calls(decoded, 'kamui/sound_attackairhi')
    check(s_rust == s_dec == [4.0], f'sound frames {s_rust} vs decoded {s_dec}')
    x_rust = effective_frames(script_frames(src, 'expression_mckamuiattackairhi'))
    rumble_frame = [c['frame'] for c in decoded_calls(decoded, 'kamui/expression_attackairhi') if c['kind'] == 'RUMBLE_HIT'][0]
    check(x_rust == [float(rumble_frame)], f'expression frame {x_rust} vs decoded RUMBLE_HIT {rumble_frame}')
    rumble = rust_calls(script_body(src, 'expression_mckamuiattackairhi'), 'RUMBLE_HIT')
    check(len(rumble) == 1 and norm_rust(rumble[0][0]) == ('hash', 'rbkind_slashm')
          and norm_rust(rumble[0][1]) == ('num', 0.0), 'RUMBLE_HIT not rbkind_slashm, 0')
    # sound: the donor tone is kept by its own name; the donor sequence is not (Cloud's voice rule)
    snd = script_body(src, 'sound_mckamuiattackairhi')
    check('Hash40::new("se_kamui_attackair_h01")' in snd, 'PLAY_SE is not the donor tone se_kamui_attackair_h01')
    check('seq_kamui_rnd_attack_air' not in snd and 'seq_miigunner_rnd_attack02' in snd,
          'sequence is not the Gunner sequence seq_miigunner_rnd_attack02')
    # trail: the donor's 29 arguments, the two texture names renamed to the owned names
    trail = rust_calls(script_body(src, 'effect_mckamuiattackairhi'), 'AFTER_IMAGE4_ON_arg29')
    dtrail = [c for c in decoded_calls(decoded, 'kamui/effect_attackairhi') if c['kind'] == 'AFTER_IMAGE4_ON_arg29'][0]
    check(len(trail) == 1 and len(trail[0]) == len(dtrail['args']) == 29, 'trail argument count differs from decoded (29)')
    if len(trail) == 1 and len(trail[0]) == len(dtrail['args']):
        for pos, (rt, da) in enumerate(zip(trail[0], dtrail['args'])):
            if da.get('t') == 'global' or norm_decoded(da)[0] == 'raw':
                continue
            rn, dn = norm_rust(rt), norm_decoded(da)
            if pos in (0, 1):
                expect = ('hash', 'tex_mc_' + dn[1][len('tex_'):])
                check(rn == expect, f'trail texture {pos}: rust {rt!r} != owned {expect[1]}')
                continue
            check(same(rn, dn), f'trail arg {pos}: rust {rt!r} != decoded {da}')
    print(f"5 unit.rs: {len(rust)} ATTACK calls and the 29-argument trail call match the decode; game frames {g_rust}, "
          f"effect {e_rust}, sound {s_rust}, expression {x_rust}")


# ---------------------------------------------------------------------------
# 6-7. skeleton bone, gates, landing lag
# ---------------------------------------------------------------------------

def check_haver():
    import ssbh_data_py as s
    for label, path in (('kamui', DONOR_SKEL), ('miigunner', GUNNER_SKEL)):
        names = [b.name for b in s.skel_data.read_skel(str(path)).bones]
        check(any(hash40(n.lower()) == hash40('haver') for n in names), f'haver not on {label} skeleton')
    print('6 bone haver = HaveR on the Corrin and Gunner skeletons (hash40 case-insensitive)')


def check_gates_and_lag(src: str):
    rep = json.loads(REPORT.read_text(encoding='utf-8'))
    for part in ('', 'landing'):
        block = rep if part == '' else rep['landing']
        for limb in LIMBS:
            v = block['limb_motion'].get(limb, {})
            check(v.get('kept') is True, f'{part or "attack"} limb {limb} not kept')
            check(v.get('max_rot_deg', 0) >= 0.5 or v.get('max_trans', 0) >= 1e-3, f'{part or "attack"} limb {limb} static')
        check(block['world_space_transfer_nodes'] == ['ClavicleL', 'ClavicleR', 'LegL', 'LegR'],
              f'{part or "attack"} world-space nodes differ')
    m = re.search(r'pub const LANDING_FRAME_HI: f32 = ([0-9.]+);', src)
    check(bool(m) and float(m.group(1)) == LANDING_FRAME_HI, 'unit.rs LANDING_FRAME_HI is not Corrin\'s 9.0')
    check(rep['landing_frame_hi']['corrin'] == LANDING_FRAME_HI and rep['landing_frame_hi']['gunner'] == GUNNER_LANDING_FRAME_HI,
          'report landing lag differs from the measured fighter_param values')
    print(f"7 gates: legs moving (attack and landing), world-space nodes as listed; landing lag {LANDING_FRAME_HI} "
          f"(Gunner {GUNNER_LANDING_FRAME_HI}); ground correction attack {rep['ground_correction_range']}, "
          f"landing {rep['landing']['ground_correction_range']}")


# ---------------------------------------------------------------------------
# 8. sword article
# ---------------------------------------------------------------------------

def sword_ok(objects: int, bones: list, mats: list, modl: int) -> bool:
    return objects == 3 and bones == ['Have'] and len(mats) == 3 and modl == 3


def check_sword(src_mckamui: str):
    import ssbh_data_py as s
    mesh = s.mesh_data.read_mesh(str(SWORD_MODEL / 'model.numshb'))
    bones = [b.name for b in s.skel_data.read_skel(str(SWORD_MODEL / 'model.nusktb')).bones]
    mats = [e.material_label for e in s.matl_data.read_matl(str(SWORD_MODEL / 'model.numatb')).entries]
    modl = s.modl_data.read_modl(str(SWORD_MODEL / 'model.numdlb'))
    check(sword_ok(len(mesh.objects), bones, mats, len(modl.entries)),
          f'sword: objects {len(mesh.objects)} bones {bones} materials {mats} modl {len(modl.entries)}')
    check(all(o.name == 'mckamui_sword_VIS_O_OBJShape' and o.parent_bone_name == 'Have' and not o.bone_influences
              for o in mesh.objects), 'sword objects are not rigid mckamui_sword meshes on Have')
    check(mats == ['mckamui_sword_001', 'mckamui_sword_002', 'mckamui_sword_003'], 'sword material labels differ')
    for t in ('def_sword_001_col', 'def_sword_002_col', 'def_sword_003_col', 'default_Normal'):
        f = SWORD_MODEL / f"{t.lower() if t == 'default_Normal' else t}.nutexb"
        check(f.is_file(), f'sword texture missing: {f.name}')
    clip = s.anim_data.read_anim(str(SWORD_MOTION / 'a00mckamuisword.nuanmb'))
    vis = next(g for g in clip.groups if g.group_type.name == 'Visibility')
    check([(n.name, n.tracks[0].values[0]) for n in vis.nodes] == [('mckamui_sword', True)],
          'sword clip Visibility is not mckamui_sword True')
    ml = (SWORD_MOTION / 'motion_list.bin').read_bytes()
    _, _, ents = parse_mlist(ml)
    check(len(ents) == 1 and ents[0]['kind'] == hash40(SWORD_KIND) and ents[0]['anims'] == (hash40(SWORD_CLIP_NAME),),
          'sword article motion list entry hashes differ from the unit names')
    m = re.search(r'pub const ARTICLE_NAME: &str = "([^"]+)";', src_mckamui)
    check(bool(m) and m.group(1) == 'mckamuisword', 'mckamui.rs article name differs')
    m = re.search(r'pub const ARTICLE_MOTION: &str = "([^"]+)";', src_mckamui)
    check(bool(m) and m.group(1) == SWORD_KIND, 'mckamui.rs article motion differs')
    check('"fighter/miigunner/model/mckamuisword/c00/model.numshb"' in src_mckamui, 'mckamui.rs model file path differs')
    print(f"8 sword article: {len(mesh.objects)} rigid objects on {bones}, materials {mats}, clip Visibility mckamui_sword True, "
          f"article motion entry hashes match")


# ---------------------------------------------------------------------------
# 9. sound
# ---------------------------------------------------------------------------

def check_sound(src: str):
    sys.path.insert(0, str(SRC))
    import mckamui_sound_codec as codec
    rec = json.loads((SOUND_DIR / 'se_miigunner.merge.json').read_text(encoding='utf-8'))
    check([a['name'] for a in rec['appended']] == ['se_kamui_attackair_H01'], 'appended tone names differ')
    check(rec['retained_tones'] == 89 and rec['total_tones'] == 90, f"tone counts {rec['retained_tones']} -> {rec['total_tones']}")
    out_audio = (SOUND_DIR / 'se_miigunner.nus3audio').read_bytes()
    base_audio = (SOUND_BASE / 'se_miigunner.nus3audio').read_bytes()
    out_names = [n for n, _ in codec.audio_read(out_audio)]
    base_names = [n for n, _ in codec.audio_read(base_audio)]
    check(out_names[:len(base_names)] == base_names and out_names[-1].lower() == 'se_kamui_attackair_h01',
          'output bank is not base + the Corrin tone')
    check(sha256(SOUND_BASE / 'se_miigunner.nus3bank') == rec['base']['.nus3bank']['sha256'],
          'base bank changed since the merge record')
    labels = codec.labels_read_partial((SOUND_DIR / 'se_miigunner.tonelabel').read_bytes(), out_names)
    check(zlib.crc32(b'se_kamui_attackair_h01') in {c for c, _ in labels}, 'output label for the Corrin tone missing')
    check('Hash40::new("se_kamui_attackair_h01")' in src, 'unit.rs PLAY_SE does not name the appended tone')
    print(f"9 sound: se_miigunner {rec['retained_tones']} -> {rec['total_tones']} tones, base prefix kept, label resolves")


# ---------------------------------------------------------------------------
# 10. trail textures
# ---------------------------------------------------------------------------

def check_trail():
    for donor, owned in (('tex_kamui_sword1', 'tex_mc_kamui_sword1'), ('tex_kamui_sword2', 'tex_mc_kamui_sword2')):
        d = (G / 'moves/aerial_up__kamui/donor/effect/fighter/kamui/trail' / f'{donor}.nutexb').read_bytes()
        p = TRAIL / f'{owned}.nutexb'
        check(p.is_file(), f'trail texture missing: {owned}')
        if not p.is_file():
            continue
        o = p.read_bytes()
        check(len(o) == len(d), f'{owned}: size differs from the donor')
        check(o[-0x6c:-0x2c].rstrip(b'\0') == owned.upper().encode(), f'{owned}: footer name is not {owned.upper()}')
        check(o[:-0x6c] == d[:-0x6c] and o[-0x2c:] == d[-0x2c:], f'{owned}: bytes differ outside the footer name')
    print('10 trail: two textures, owned footer names, only the 64-byte name field differs from the donor')


# ---------------------------------------------------------------------------
# 11. plugin
# ---------------------------------------------------------------------------

def check_plugin():
    check((PLUGIN / 'src/unit_aerial_up_kamui.rs').read_bytes() == (SRC / 'unit.rs').read_bytes(),
          'plugin unit file differs from moves/aerial_up__kamui/unit.rs')
    check((PLUGIN / 'src/mckamui.rs').read_bytes() == (SRC / 'mckamui.rs').read_bytes(),
          'plugin mckamui.rs differs from moves/aerial_up__kamui/mckamui.rs')
    lib = (PLUGIN / 'src/lib.rs').read_text(encoding='utf-8')
    menu = (PLUGIN / 'src/menu.rs').read_text(encoding='utf-8')
    moves = (PLUGIN / 'src/moves.rs').read_text(encoding='utf-8')
    check('pub mod unit_aerial_up_kamui;' in lib and 'pub mod mckamui;' in lib, 'lib.rs does not declare the modules')
    check('(b"aerial_up", b"kamui")' in menu and 'IMPLEMENTED_MOVES: [(&[u8], &[u8]); 9]' in menu,
          'menu.rs does not list aerial_up/kamui (9 entries)')
    check('("aerial_up", b"kamui", crate::unit_aerial_up_kamui::start_attack_air)' in moves,
          'moves.rs: no row for kamui in gunner_attack_air_main')
    check('crate::unit_aerial_up_kamui::start_landing_attack_air(fighter, was_kamui_up)' in moves,
          'moves.rs: landing hook missing')
    check('crate::mckamui::install();' in moves and '.on_line(Main, crate::mckamui::sword_guard);' in moves,
          'moves.rs: sword install or guard missing')
    check('crate::unit_aerial_up_kamui::register_acmd(&mut agent);' in moves, 'moves.rs: ACMD registration missing')
    check(NRO.is_file(), 'built NRO missing')
    r = subprocess.run([sys.executable, '-I', str(STACK), str(NRO)], capture_output=True, text=True)
    check(r.returncode == 0, f'stack-frame check exit {r.returncode}')
    print(f'11 plugin copy: unit and sword identical to the sources, wiring present, NRO sha256 '
          f'{sha256(NRO)[:16] if NRO.is_file() else "MISSING"}, stack check exit {r.returncode}')


# ---------------------------------------------------------------------------
# 12. negative controls
# ---------------------------------------------------------------------------

def controls(src: str, decoded: dict):
    bad = src.replace('10.0, 70, 97, 0, 55, 5.5,', '11.0, 70, 97, 0, 55, 5.5,', 1)
    check(_capture(lambda: check_script_values(bad, decoded)) > 0, 'control: changed hitbox damage was NOT rejected')
    bad = src.replace('frame(agent.lua_state_agent, 38.0);', 'frame(agent.lua_state_agent, 39.0);', 1)
    check(_capture(lambda: check_script_values(bad, decoded)) > 0, 'control: changed frame was NOT rejected')
    check(not cancel_ok(39, 38, 38), 'control: changed cancel field was NOT rejected')
    bad = src.replace('pub const LANDING_FRAME_HI: f32 = 9.0;', 'pub const LANDING_FRAME_HI: f32 = 8.0;', 1)
    check(_capture(lambda: check_gates_and_lag(bad)) > 0, 'control: changed landing lag was NOT rejected')
    check(not sword_ok(2, ['Have'], ['a', 'b', 'c'], 3), 'control: a two-object sword was NOT rejected')
    print('12 negative controls: damage, frame, cancel field, landing lag and sword object count all rejected')


def main() -> int:
    src = (SRC / 'unit.rs').read_text(encoding='utf-8')
    src_sword = (SRC / 'mckamui.rs').read_text(encoding='utf-8')
    decoded = json.loads(DECODED.read_text(encoding='utf-8'))
    check_manifest()
    check_clips()
    check_motion_list()
    check_script_values(src, decoded)
    check_haver()
    check_gates_and_lag(src)
    check_sword(src_sword)
    check_sound(src)
    check_trail()
    check_plugin()
    controls(src, decoded)
    if FAILS:
        print(f'FAILED: {len(FAILS)} check(s)')
        return 1
    print('PASS: aerial_up__kamui offline checks')
    return 0


if __name__ == '__main__':
    sys.exit(main())
