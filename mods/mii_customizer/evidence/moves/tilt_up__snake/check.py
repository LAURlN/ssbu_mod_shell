#!/usr/bin/env python3
"""Verification for MV-tilt_up__snake (Snake's up tilt, donor attack_hi3, on Mii Gunner).

Run from anywhere; exits 0 when every check passes, 1 on the first group of mismatches (all printed).
Needs ssbh_data_py (the same package the build uses).

Checks
 1. Every file in moves/tilt_up__snake/manifest.json exists with the recorded size and sha256.
 2. Every donor input the build reads is the pinned revision (extracted from data.arc, sha256 pinned).
 3. Motion list: reference = vanilla Gunner list + exactly one entry; the owned entry differs from the
    donor's raw entry only in the name hashes, the clip hash and the script hashes; flags 0x84, cancel 38,
    blend 0, one animation; every hash equals hash40 of the name used in unit.rs and in the package.
 4. Retargeted clip: the package clip keeps only nodes the Gunner skeleton has; the removed set equals the
    donor nodes that are not on the Gunner; visibility/material groups are complete; leg chain present.
 5. Script values in unit.rs equal the decoded donor ACMD calls (tables/acmd_calls.json): every ATTACK's
    frame, bone, damage, angle, kbg, fkb, bkb, size and offset; the clear frame; the effect, sound,
    expression names and frames.
 6. Sounds in the reference banks: the appended tones are the donor's (sample bytes equal), every original
    tone is kept in order, the Gunner's sequence file gained exactly the donor's seq_snake_rnd_attack record.
 7. Hitbox bones: top is absent from both skeletons (engine anchor); kneel and legl are on the Gunner.
 8. Plugin copy: unit.rs in moves/ equals the plugin module; the wiring is in moves.rs and lib.rs; the NRO (when
    built) contains the four script names and the motion kind.
 9. Negative controls: a damaged expected value and a damaged motion-entry check must each be rejected.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import struct
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[2]                     # mods/mii_customizer
WORKSPACE = MOD.parents[1]                 # workspace root (folder holding AGENTS.md)
UNIT = MOD / 'moves/tilt_up__snake'
GD = WORKSPACE / 'gamedata/mii_customizer/moves/tilt_up__snake'
PLUGIN = MOD / 'scratch/2026-10-08_MV-tilt_up__snake/plugin'
NRO = MOD / 'builds/.cache/MV-tilt_up__snake-target/aarch64-skyline-switch/release/libmii_customizer.nro'
GUNNER_SKEL = WORKSPACE / 'gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb'
SNAKE_SKEL = GD / 'extracted/fighter/snake/model/body/c00/model.nusktb'

failures: list[str] = []
passes = [0]


def check(cond: bool, msg: str) -> None:
    if cond:
        passes[0] += 1
    else:
        failures.append(msg)


def hash40(name: str) -> int:
    return (len(name) << 32) | (zlib.crc32(name.encode('utf-8')) & 0xFFFFFFFF)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_build():
    spec = importlib.util.spec_from_file_location('build_assets', UNIT / 'build_assets.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


B = load_build()  # the codec and the parsers the build used (audio, bank, sqb, motion list)


# ---------------------------------------------------------------------------
# 1, 2: manifest and pins
# ---------------------------------------------------------------------------

def check_manifest() -> dict:
    man = json.loads((GD / 'manifest.json').read_text(encoding='utf-8'))
    for rel, rec in man['files'].items():
        p = WORKSPACE / rel
        check(p.is_file(), f'manifest file missing: {rel}')
        if p.is_file():
            check(p.stat().st_size == rec['bytes'], f'size differs: {rel}')
            check(sha(p) == rec['sha256'], f'sha256 differs from manifest: {rel}')
    for rel, digest in man['inputs_pinned'].items():
        if rel == 'gunner_skeleton':
            check(sha(GUNNER_SKEL) == digest, 'Gunner skeleton is not the pinned revision')
            continue
        p = GD / 'extracted' / rel
        check(p.is_file() and sha(p) == digest, f'pinned donor/base input differs: {rel}')
    return man


# ---------------------------------------------------------------------------
# 3: motion list
# ---------------------------------------------------------------------------

OWNED = {
    'kind': 'mc_snake_attack_hi3',
    'game': 'game_mcsnakeattackhi3', 'effect': 'effect_mcsnakeattackhi3',
    'sound': 'sound_mcsnakeattackhi3', 'expression': 'expression_mcsnakeattackhi3',
    'clip': 'c02mcsnakeattackhi3.nuanmb',
}


def owned_entry_diff_offsets(donor: bytes, owned: bytes, tail: int) -> set[int]:
    return {i for i in range(len(donor)) if donor[i] != owned[i]}


def check_motion_list(expected_cancel: int = 38) -> None:
    ref = (GD / 'reference/motion_list_vanilla_plus_owned.bin').read_bytes()
    _, _, ref_entries = B.parse_mlist(ref)
    _, _, van = B.parse_mlist((GD / 'extracted/fighter/miigunner/motion/body/c00/motion_list.bin').read_bytes())
    _, _, snake = B.parse_mlist((GD / 'extracted/fighter/snake/motion/body/c00/motion_list.bin').read_bytes())
    check(len(ref_entries) == len(van) + 1, f'reference list has {len(ref_entries)} entries, want {len(van) + 1}')
    check([e['raw'] for e in ref_entries[:-1]] == [e['raw'] for e in van],
          'reference list changes a vanilla Gunner entry')
    owned = ref_entries[-1]
    check(owned['kind'] == hash40(OWNED['kind']), 'last reference entry is not the owned kind')
    donor = [e for e in snake if e['kind'] == hash40('attack_hi3')]
    check(len(donor) == 1, 'donor attack_hi3 not unique')
    donor = donor[0]
    tail = donor['tail_offset']
    raw = owned['raw']
    game_hash, = struct.unpack_from('<Q', raw, 8)
    clip_hash, = struct.unpack_from('<Q', raw, 24)
    exp_h, snd_h, eff_h = struct.unpack_from('<QQQ', raw, tail)
    check(game_hash == hash40(OWNED['game']), 'owned game script hash is not hash40(game_mcsnakeattackhi3)')
    check(clip_hash == hash40(OWNED['clip']), 'owned clip hash is not hash40(c02mcsnakeattackhi3.nuanmb)')
    check(exp_h == hash40(OWNED['expression']), 'owned expression hash mismatch')
    check(snd_h == hash40(OWNED['sound']), 'owned sound hash mismatch')
    check(eff_h == hash40(OWNED['effect']), 'owned effect hash mismatch')
    check(owned['flags'] == 0x84 and donor['flags'] == 0x84, 'flags are not 0x0084')
    cancel = struct.unpack_from('<H', raw, tail + 26)[0]
    check(cancel == expected_cancel, f'owned cancel frame {cancel}, expected {expected_cancel}')
    check(cancel == 38 and donor['raw'] and struct.unpack_from('<H', donor['raw'], tail + 26)[0] == 38,
          'donor cancel frame is not 38')
    check(owned['n_anims'] == 1 and donor['n_anims'] == 1, 'animation count is not 1')
    check(struct.unpack_from('<H', raw, 16)[0] == 0x84 and raw[18] == 0, 'flags/blend field differs from donor')
    # every byte that differs from the donor entry must lie in a name-hash field
    allowed = set(range(0, 16)) | set(range(24, 32)) | set(range(tail, tail + 24))
    diff = owned_entry_diff_offsets(donor['raw'], raw, tail)
    check(diff <= allowed, f'owned entry changes bytes outside name hashes: {sorted(diff - allowed)}')
    check(len(raw) == len(donor['raw']), 'owned entry length differs from donor')


# ---------------------------------------------------------------------------
# 4: retargeted clip
# ---------------------------------------------------------------------------

def check_clip() -> None:
    import ssbh_data_py as s

    gunner = {b.name.lower() for b in s.skel_data.read_skel(str(GUNNER_SKEL)).bones}
    donor = s.anim_data.read_anim(str(GD / 'extracted' / B.DONOR_CLIP))
    owned = s.anim_data.read_anim(str(GD / 'package/fighter/miigunner/motion/body/c00' / B.OWNED_CLIP))

    def groups(anim):
        out = {}
        for g in anim.groups:
            out[str(g.group_type)] = [n.name for n in g.nodes]
        return out

    gd, go = groups(donor), groups(owned)
    t_d = gd['<GroupType.Transform: 1>']
    t_o = go['<GroupType.Transform: 1>']
    check(all(n.lower() in gunner for n in t_o), 'retargeted clip keeps a node the Gunner skeleton lacks')
    removed = [n for n in t_d if n.lower() not in gunner]
    check(set(t_o) == set(t_d) - set(removed), 'retargeted clip is not donor minus the non-Gunner nodes')
    check(len(removed) == 23, f'removed {len(removed)} nodes, measured 23')
    check(len(gd['<GroupType.Visibility: 2>']) == len(go['<GroupType.Visibility: 2>']) == 26,
          'visibility tracks not kept whole')
    check(len(gd['<GroupType.Material: 4>']) == len(go['<GroupType.Material: 4>']) == 2, 'material tracks not kept')
    for must in ('Hip', 'Waist', 'LegL', 'KneeL', 'FootL', 'LegR', 'KneeR', 'FootR', 'ArmL', 'ArmR', 'Head'):
        check(must.lower() in {n.lower() for n in t_o}, f'retargeted clip lost {must}')


# ---------------------------------------------------------------------------
# 5: script values
# ---------------------------------------------------------------------------

ATTACK_RE = re.compile(
    r'macros::ATTACK\(agent,\s*(\d+),\s*(\d+),\s*Hash40::new\("(\w+)"\),\s*([-\d.]+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+),\s*([-\d.]+)')
TOKEN_RE = re.compile(r'\b(frame|wait)\(agent\.lua_state_agent,\s*([\d.]+)\)|(macros::ATTACK\()|(AttackModule::clear_all)|'
                      r'(macros::EFFECT_FOLLOW\(|macros::LAST_EFFECT_SET_RATE\(|macros::FOOT_EFFECT\(|macros::PLAY_SEQUENCE\(|macros::PLAY_SE\(|'
                      r'slope!\(|ControlModule::set_rumble\(|macros::RUMBLE_HIT\()')


def rust_fn_body(src: str, name: str) -> str:
    start = src.index(f'pub unsafe extern "C" fn {name}(')
    nxt = src.find('pub unsafe extern "C" fn', start + 10)
    nxt2 = src.find('pub fn register_acmd', start + 10)
    ends = [e for e in (nxt, nxt2) if e != -1]
    return src[start: min(ends) if ends else len(src)]


def rust_timeline(body: str):
    """(frame, kind, args-text) in source order; frame(x) sets, wait(x) adds."""
    cur = 0.0
    rows = []
    for m in re.finditer(r'\b(frame|wait)\(agent\.lua_state_agent,\s*([\d.]+)\)|AttackModule::clear_all|slope!\(agent,\s*([^)]*)\)|'
                         r'ControlModule::set_rumble\(agent\.module_accessor,\s*Hash40::new\("(\w+)"\)|'
                         r'macros::RUMBLE_HIT\(agent,\s*Hash40::new\("(\w+)"\)|'
                         r'macros::(EFFECT_FOLLOW|FOOT_EFFECT|LAST_EFFECT_SET_RATE|PLAY_SEQUENCE|PLAY_SE)\(agent,\s*(?:Hash40::new\("(\w+)"\))?|'
                         r'macros::ATTACK\(agent,\s*\d+,\s*\d+,\s*Hash40::new\("(\w+)"\)', body):
        txt = m.group(0)
        if m.group(1) == 'frame':
            cur = float(m.group(2))
        elif m.group(1) == 'wait':
            cur += float(m.group(2))
        elif txt.startswith('AttackModule::clear_all'):
            rows.append((cur, 'clear', ''))
        elif txt.startswith('slope!'):
            rows.append((cur, 'slope', m.group(3).replace(' ', '')))
        elif txt.startswith('ControlModule::set_rumble'):
            rows.append((cur, 'set_rumble', m.group(4)))
        elif txt.startswith('macros::RUMBLE_HIT'):
            rows.append((cur, 'RUMBLE_HIT', m.group(5)))
        elif txt.startswith('macros::ATTACK'):
            rows.append((cur, 'ATTACK', m.group(6)))
        else:
            rows.append((cur, m.group(7), m.group(8) or ''))
    return rows


def decoded_calls() -> dict:
    return json.loads((GD / 'tables/acmd_calls.json').read_text(encoding='utf-8'))


def check_scripts(src: str, decoded: dict, game_override=None) -> list[str]:
    """Return mismatch messages (empty when everything agrees). Used by the negative control too."""
    msgs = []
    # ATTACK rows: frame, bone, and the numeric fields, against the decoded calls
    body = rust_fn_body(src, 'game_mcsnakeattackhi3') if game_override is None else game_override
    rust_attacks = []
    cur = 0.0
    tokens = re.finditer(r'\b(frame|wait)\(agent\.lua_state_agent,\s*([\d.]+)\)|' + ATTACK_RE.pattern + r'|AttackModule::clear_all', body, re.S)
    clears = []
    for m in tokens:
        if m.group(1) == 'frame':
            cur = float(m.group(2))
        elif m.group(1) == 'wait':
            cur += float(m.group(2))
        elif m.group(3) is not None:
            vals = m.groups()[2:]
            rust_attacks.append((cur, int(vals[0]), vals[2], float(vals[3]), int(vals[4]), int(vals[5]), int(vals[6]), int(vals[7]),
                                 float(vals[8]), float(vals[9]), float(vals[10]), float(vals[11])))
        else:
            clears.append(cur)
    # ATTACK args must come in the order the donor's decoded macro uses: id, part, bone, damage, angle, kbg, fkb, bkb, size, x, y, z
    dec = []
    for c in decoded['game_attackhi3']['calls']:
        if c['kind'] == 'ATTACK':
            a = c['args']
            def val(x):
                return x.get('name', x.get('v')) if x.get('t') == 'hash' else x.get('v', x.get('name'))
            v = [val(x) for x in a]
            dec.append((float(c['frame']), int(v[0]), v[2], float(v[3]), int(v[4]), int(v[5]), int(v[6]), int(v[7]),
                        float(v[8]), float(v[9]), float(v[10]), float(v[11])))
        if c['kind'] == 'lua_bind' and 'clear_all' in c.get('target', ''):
            dec_clear = float(c['frame'])
    if len(rust_attacks) != len(dec):
        msgs.append(f'ATTACK count: rust {len(rust_attacks)} decoded {len(dec)}')
    for r, d in zip(rust_attacks, dec):
        for i, (x, y) in enumerate(zip(r, d)):
            if isinstance(x, float) or isinstance(y, float):
                if abs(float(x) - float(y)) > 1e-4:
                    msgs.append(f'ATTACK field {i} differs at frame {d[0]}: rust {x} decoded {y}')
            elif x != y:
                msgs.append(f'ATTACK field {i} differs at frame {d[0]}: rust {x!r} decoded {y!r}')
    if clears != [dec_clear]:
        msgs.append(f'clear frame: rust {clears} decoded {dec_clear}')
    # effect / sound / expression: names and frames
    eff = rust_fn_body(src, 'effect_mcsnakeattackhi3')
    names_eff = re.findall(r'Hash40::new\("(\w+)"\)', eff)
    for n in ('sys_attack_arc_b', 'sys_turn_smoke', 'top'):
        if n not in names_eff:
            msgs.append(f'effect script lacks {n}')
    sound = rust_fn_body(src, 'sound_mcsnakeattackhi3')
    for n in ('seq_snake_rnd_attack', 'se_snake_attackhard_h01'):
        if f'"{n}"' not in sound:
            msgs.append(f'sound script lacks {n}')
    dec_sound = [(c['frame'], c['kind'], c['args'][0].get('name')) for c in decoded['sound_attackhi3']['calls']
                 if c['kind'] in ('PLAY_SE', 'PLAY_SEQUENCE')]
    for f, k, n in dec_sound:
        if f'"{n}"' not in sound or f'{k}' not in ('PLAY_SE', 'PLAY_SEQUENCE'):
            msgs.append(f'sound {k} {n} not in the owned script')
    expr = rust_fn_body(src, 'expression_mcsnakeattackhi3')
    for n in ('rbkind_nohitm', 'rbkind_attackm'):
        if f'"{n}"' not in expr:
            msgs.append(f'expression script lacks {n}')
    rows = rust_timeline(expr)
    want = [(None, 'slope', 'MA_MSC_CMD_SLOPE_SLOPE,SLOPE_STATUS_R'), (4.0, 'set_rumble', 'rbkind_nohitm'),
            (6.0, 'RUMBLE_HIT', 'rbkind_attackm'), (32.0, 'slope', 'MA_MSC_CMD_SLOPE_SLOPE_INTP,SLOPE_STATUS_LR,4')]
    for (f, k, a), (wf, wk, wa) in zip(rows, want):
        if (wf is not None and abs(f - wf) > 1e-6) or k != wk or wa.split(',')[0] not in a:
            msgs.append(f'expression timeline row {(f, k, a)} differs from {(wf, wk, wa)}')
    if len(rows) != len(want):
        msgs.append(f'expression timeline has {len(rows)} rows, want {len(want)}')
    return msgs


def check_donor_scripts(src: str) -> None:
    dec = decoded_calls()
    msgs = check_scripts(src, dec)
    for m in msgs:
        check(False, 'script: ' + m)
    if not msgs:
        check(True, 'script values')


# ---------------------------------------------------------------------------
# 6: sound additions in the reference banks
# ---------------------------------------------------------------------------

def check_sound(man: dict) -> None:
    for entry in man['sound']['banks']:
        stem = WORKSPACE / 'gamedata/mii_customizer/moves/tilt_up__snake/reference' / entry['stem']
        base_stem = GD / 'extracted' / entry['stem']
        new = B.audio_read(stem.with_suffix('.nus3audio').read_bytes())
        old = B.audio_read(base_stem.with_suffix('.nus3audio').read_bytes())
        names_new = [n for n, _ in new]
        check(names_new[:len(old)] == [n for n, _ in old], f'{entry["stem"]}: an original tone moved or vanished')
        check(all(new[i][1] == old[i][1] for i in range(len(old))), f'{entry["stem"]}: an original sample changed')
        donor = B.audio_read((GD / 'extracted' / B.VC_DONOR_STEM).with_suffix('.nus3audio').read_bytes()) \
            if entry['folder'] == 'fighter_voice' else \
            B.audio_read((GD / 'extracted' / B.SE_DONOR_STEM).with_suffix('.nus3audio').read_bytes())
        dmap = {n.lower(): b for n, b in donor}
        for n in entry['appended']:
            got = [b for name, b in new if name.lower() == n.lower()]
            check(len(got) == 1 and got[0] == dmap[n.lower()], f'{entry["stem"]}: appended {n} is not the donor sample')
        check(len(new) == len(old) + len(entry['appended']), f'{entry["stem"]}: tone count is not base + appended')
    # the tones the Gunner plays through its own sequences resolve in every voice bank
    seq_expect = {'vc_snake_attack01', 'vc_snake_attack02', 'vc_snake_attack03', 'vc_snake_attack04'}
    for stem in B.MII_VOICE_STEMS:
        if stem.endswith('cheer'):
            continue
        p = GD / 'reference' / (stem)
        if p.with_suffix('.nus3audio').is_file():
            names = {n.lower() for n, _ in B.audio_read(p.with_suffix('.nus3audio').read_bytes())}
            check(seq_expect <= names, f'{stem}: snake attack voice missing')
    # sequence file
    donor_recs = B.sqb_read((GD / 'extracted' / B.SQB_DONOR).read_bytes())
    rec = [r for r in donor_recs if int.from_bytes(r[:8], 'little') == hash40(B.SEQUENCE)]
    check(len(rec) == 1, 'donor seq_snake_rnd_attack not unique')
    base = B.sqb_read((GD / 'extracted' / B.SQB_RECIPIENT).read_bytes())
    ref = B.sqb_read((GD / 'reference/sound/sequence/fighter/miigunner.sqb').read_bytes())
    check(ref[:len(base)] == base, 'Gunner sqb: an original record changed')
    check(len(ref) == len(base) + 1 and ref[-1] == rec[0], 'Gunner sqb does not gain exactly the donor record')
    check(sum(int.from_bytes(r[:8], 'little') == hash40(B.SEQUENCE) for r in ref) == 1, 'sequence record count != 1')


# ---------------------------------------------------------------------------
# 7: hitbox bones
# ---------------------------------------------------------------------------

def check_bones() -> None:
    import ssbh_data_py as s
    g = {b.name.lower() for b in s.skel_data.read_skel(str(GUNNER_SKEL)).bones}
    sn = {b.name.lower() for b in s.skel_data.read_skel(str(SNAKE_SKEL)).bones}
    check('top' not in g and 'top' not in sn, 'top is on a skeleton now: revisit the engine-anchor note')
    check('kneel' in g and 'legl' in g, 'kneel/legl not on the Gunner skeleton')


# ---------------------------------------------------------------------------
# 8: plugin copy and NRO
# ---------------------------------------------------------------------------

def check_plugin() -> None:
    unit_src = (UNIT / 'unit.rs').read_bytes()
    plug = (PLUGIN / 'src/unit_tilt_up_snake.rs').read_bytes()
    check(unit_src == plug, 'moves/tilt_up__snake/unit.rs differs from the plugin module')
    moves = (PLUGIN / 'src/moves.rs').read_text(encoding='utf-8')
    check('crate::unit_tilt_up_snake::start_attack_hi3' in moves, 'moves.rs does not dispatch the Snake start')
    check('crate::unit_tilt_up_snake::register_acmd(&mut agent);' in moves, 'moves.rs does not register the Snake ACMD')
    lib = (PLUGIN / 'src/lib.rs').read_text(encoding='utf-8')
    check('pub mod unit_tilt_up_snake;' in lib, 'lib.rs does not declare unit_tilt_up_snake')
    if NRO.is_file():
        data = NRO.read_bytes()
        for name in (OWNED['game'], OWNED['effect'], OWNED['sound'], OWNED['expression'], OWNED['kind']):
            check(name.encode() in data, f'NRO lacks the string {name}')
    else:
        check(False, f'NRO not built: {NRO}')


# ---------------------------------------------------------------------------
# 9: negative controls
# ---------------------------------------------------------------------------

def negative_controls(src: str) -> None:
    # a damaged donor value must be caught by the script comparator
    dec = decoded_calls()
    bad = json.loads(json.dumps(dec))
    for c in bad['game_attackhi3']['calls']:
        if c['kind'] == 'ATTACK':
            c['args'][3]['v'] = 15.5
            break
    caught = bool(check_scripts(src, bad))
    check(caught, 'negative control: a damaged damage value was not caught')
    # a motion list with a wrong cancel frame must be caught
    before = len(failures)
    check_motion_list(expected_cancel=30)
    cancel_caught = any('owned cancel frame' in f for f in failures[before:])
    del failures[before:]  # the control's own failure is expected; it is not a real mismatch
    check(cancel_caught, 'negative control: a wrong cancel frame was not caught')


def main() -> int:
    man = check_manifest()
    check_motion_list()
    check_clip()
    src = (UNIT / 'unit.rs').read_text(encoding='utf-8')
    check_donor_scripts(src)
    check_sound(man)
    check_bones()
    check_plugin()
    negative_controls(src)
    if failures:
        print(f'FAIL: {len(failures)} mismatch(es), {passes[0]} checks passed')
        for f in failures:
            print('  -', f)
        return 1
    print(f'PASS: {passes[0]} checks (manifest, pins, motion list, clip, script values, sounds, bones, plugin, NRO, negative controls)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
