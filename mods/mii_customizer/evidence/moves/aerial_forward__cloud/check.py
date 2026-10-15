#!/usr/bin/env python3
"""Offline check of the Cloud units. Run from the workspace root; exit 1 on any mismatch.

    python -I mods/mii_customizer/evidence/moves/aerial_forward__cloud/check.py            (both units)
    python -I mods/mii_customizer/evidence/moves/aerial_forward__cloud/check.py --unit aerial_forward__cloud
    python -I mods/mii_customizer/evidence/moves/aerial_forward__cloud/check.py --negative  (self test)

Checks (tier B; nothing here shows behaviour in game):
  1. every generated file matches its manifest entry (size, sha256);
  2. each owned motion entry in the reference list: kind / clip / four script hashes equal the names the
     code uses, flags / blend / cancel field equal Cloud's entry, the clip resolves to a package file;
  3. every ACMD script named by a motion entry is registered in the unit's code;
  4. every ATTACK in the unit's code equals the call decoded from lua2cpp_cloud.nro (all 36 arguments);
  5. every effect, trail texture and sound the code names is in the merged Gunner bank, the trail folder
     or the common bank, and the merge records show the base bank kept intact;
  6. the parameters in the code equal Cloud's vl.prc / fighter_param.prc values;
  7. the sword article: two meshes on one bone, its motion list names the kinds mccloud.rs uses, and every
     clip's visibility nodes are meshes of the model.
"""
from __future__ import annotations

import argparse
import json
import re
import struct
import sys
from pathlib import Path

WS = Path(__file__).resolve().parents[5]
MOD = WS / 'mods/mii_customizer'
sys.path.insert(0, str(MOD / 'moves/aerial_forward__cloud'))
import mccloud_common as c  # noqa: E402

UNITS = {
    'aerial_forward__cloud': {
        'code': MOD / 'moves/aerial_forward__cloud/unit.rs',
        'out': c.G / 'moves/aerial_forward__cloud',
        'decoded': {'game_mccloudattackairf': 'cloud/game_attackairf'},
        'decoded_table': c.G / 'moves/aerial_forward__cloud/tables/acmd_calls.json',
    },
    'special_up__cloud': {
        'code': MOD / 'moves/special_up__cloud/unit.rs',
        'out': c.G / 'moves/special_up__cloud',
        'decoded': {'game_mccloudspecialhi': 'cloud/game_specialhi',
                    'game_mccloudspecialhi2': 'cloud/game_specialhi2',
                    'game_mccloudspecialhi2landing': 'cloud/game_specialhi2landing'},
        'decoded_table': c.G / 'moves/special_up__cloud/tables/acmd_calls.json',
    },
}
SHARED = c.G / 'moves/aerial_forward__cloud'
MCCLOUD_RS = MOD / 'moves/aerial_forward__cloud/mccloud.rs'
GUNNER_SE = c.RECIPIENT / 'sound/bank/fighter/se_miigunner'

FAIL = []


def check(cond, msg):
    if not cond:
        FAIL.append(msg)
    return cond


def lua_const():
    cands = list((Path.home() / '.cargo/git/checkouts').glob('skyline-smash-*/**/src/lua_const.rs'))
    p = max(cands, key=lambda x: x.stat().st_mtime)
    return {m.group(1): int(m.group(2), 0) for m in re.finditer(
        r'^\s+([A-Za-z_0-9]+):\s*(-?0x[0-9a-fA-F]+|-?\d+),', p.read_text(encoding='utf-8', errors='replace'), re.M)}


def functions(src: str) -> dict:
    """name -> body text of every `fn` in a Rust file (brace matched)."""
    out = {}
    for m in re.finditer(r'fn (\w+)\s*\(', src):
        i = src.find('{', m.end())
        depth, j = 0, i
        while j < len(src):
            if src[j] == '{':
                depth += 1
            elif src[j] == '}':
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out[m.group(1)] = src[i:j + 1]
    return out


def split_args(text: str) -> list:
    args, depth, cur = [], 0, ''
    for ch in text:
        if ch in '(':
            depth += 1
        elif ch == ')':
            depth -= 1
        if ch == ',' and depth == 0:
            args.append(cur.strip())
            cur = ''
        else:
            cur += ch
    if cur.strip():
        args.append(cur.strip())
    return args


def norm_code_arg(a: str, consts: dict):
    a = a.strip()
    m = re.fullmatch(r'Some\((.*)\)', a)
    if m:
        a = m.group(1)
    m = re.fullmatch(r'Hash40::new\("([^"]+)"\)', a)
    if m:
        return ('hash', c.hash40(m.group(1)))
    if a.startswith('*'):
        return ('int', consts[a[1:]])
    if a in ('true', 'false'):
        return ('int', int(a == 'true'))
    return ('num', float(a))


def norm_decoded_arg(a: dict, consts: dict):
    t = a.get('t')
    if t == 'hash':
        return ('hash', int(a['v'], 16) if isinstance(a['v'], str) else a['v'])
    if t == 'const':
        return ('int', consts[a['name']])
    if t == 'bool':
        return ('int', int(bool(a['v'])))
    return ('num', float(a['v']))


def same(x, y) -> bool:
    if x[0] == 'num' or y[0] == 'num':
        return abs(float(x[1]) - float(y[1])) < 1e-3
    return x == y


def attacks_in(body: str, consts: dict) -> list:
    out = []
    for m in re.finditer(r'macros::ATTACK\(agent,(.*?)\);', body, re.S):
        out.append([norm_code_arg(a, consts) for a in split_args(m.group(1))])
    return out


def check_manifest(out: Path, unit: str):
    man = json.loads((out / 'manifest.json').read_text())
    for group in ('files', 'reference'):
        for relpath, meta in man[group].items():
            p = out / relpath
            if check(p.is_file(), f'{unit}: manifest file missing {relpath}'):
                check(p.stat().st_size == meta['size'] and c.sha256(p) == meta['sha256'],
                      f'{unit}: {relpath} differs from its manifest entry')
    return man


def check_motion_entries(unit: str, out: Path, code: str, names_used: set):
    report = json.loads((out / 'tables/build_report.json').read_text())
    _, _, ref = c.parse_mlist((out / 'reference/motion_list_vanilla_plus_owned.bin').read_bytes())
    _, _, van = c.parse_mlist((c.RECIPIENT / 'fighter/miigunner/motion/body/c00/motion_list.bin').read_bytes())
    _, _, donor = c.parse_mlist((c.DONOR / 'fighter/cloud/motion/body/c00/motion_list.bin').read_bytes())
    check([e['raw'] for e in ref[:len(van)]] == [e['raw'] for e in van], f'{unit}: vanilla entries changed')
    by_kind = {e['kind']: e for e in ref}
    dby = {e['kind']: e for e in donor}
    for kind, rep in report['body']['clips'].items():
        me = rep['motion_entry']
        e = by_kind.get(c.hash40(kind))
        if not check(e is not None, f'{unit}: {kind} not in the reference list'):
            continue
        check(f'"{kind}"' in code or kind in names_used, f'{unit}: code never names motion {kind}')
        check(e['anims'] == (c.hash40(me['owned_clip']),), f'{unit}: {kind} clip hash')
        check((out / 'package/fighter/miigunner/motion/body/c00' / me['owned_clip']).is_file(),
              f'{unit}: {kind} clip file missing')
        d = dby[c.hash40(me['donor_kind'])]
        check((e['flags'], e['blend'], c.entry_cancel(e), e['size']) == (d['flags'], d['blend'], c.entry_cancel(d), d['size']),
              f'{unit}: {kind} flags/blend/cancel/size differ from Cloud')
        t = e['tail_offset']
        scripts = struct.unpack_from('<QQQ', e['raw'], t)
        suffix = me['scripts']['game'][5:]
        check(e['game'] == c.hash40(f'game_{suffix}'), f'{unit}: {kind} game script hash')
        check(scripts == (c.hash40(f'expression_{suffix}'), c.hash40(f'sound_{suffix}'), c.hash40(f'effect_{suffix}')),
              f'{unit}: {kind} expression/sound/effect hashes')
        for cat in ('game', 'effect', 'sound', 'expression'):
            check(re.search(rf'{cat}_acmd\("{cat}_{suffix}"', code) is not None,
                  f'{unit}: script {cat}_{suffix} is not registered')


def check_attacks(unit: str, cfg: dict, code: str, consts: dict):
    fns = functions(code)
    table = json.loads(cfg['decoded_table'].read_text())
    for fn, key in cfg['decoded'].items():
        mine = attacks_in(fns[fn], consts)
        decoded = [[norm_decoded_arg(a, consts) for a in call['args']] for call in table[key]['calls']
                   if call['kind'] == 'ATTACK']
        if not check(len(mine) == len(decoded), f'{unit}: {fn} has {len(mine)} ATTACKs, donor {len(decoded)}'):
            continue
        for i, (a, b) in enumerate(zip(mine, decoded)):
            check(len(a) == len(b) == 36, f'{unit}: {fn} ATTACK {i} argument count')
            for k, (x, y) in enumerate(zip(a, b)):
                check(same(x, y), f'{unit}: {fn} ATTACK {i} argument {k}: code {x} donor {y}')


def check_resources(unit: str, code: str):
    eff = json.loads((SHARED / 'reference/effect/fighter/miigunner/ef_miigunner.merge.json').read_text())
    check(eff['base_emitter_fields_and_payloads_preserved'], 'effect merge did not keep the base bank')
    handles = {h.lower() for h in eff['added_handles']}
    for name in set(re.findall(r'Hash40::new\("(mc_cloud_[a-z0-9_]+)"\)', code)):
        if name.startswith('mc_cloud_') and not name.startswith(('mc_cloud_attack', 'mc_cloud_landing',
                                                                  'mc_cloud_special', 'mc_cloud_sword_')):
            check(name in handles, f'{unit}: effect {name} not in the merged bank')
    for name in set(re.findall(r'Hash40::new\("(tex_[a-z0-9_]+)"\)', code)):
        check((SHARED / f'package/effect/fighter/miigunner/trail/{name}.nutexb').is_file(), f'{unit}: trail {name} missing')
        data = (SHARED / f'package/effect/fighter/miigunner/trail/{name}.nutexb').read_bytes()
        check(data[-0x6c:-0x2c].rstrip(b'\0').decode().lower() == name, f'{unit}: trail {name} footer name')
    snd = json.loads((SHARED / 'reference/sound/bank/fighter/se_miigunner.merge.json').read_text())
    appended = {t['name'].lower() for t in snd['appended']}
    gunner = {n.lower() for n in re.findall(rb'se_miigunner_[A-Za-z0-9_]+', GUNNER_SE.with_suffix('.nus3audio').read_bytes())}
    for name in set(re.findall(r'PLAY_(?:SE|LANDING_SE)\(agent, Hash40::new\("([a-z0-9_]+)"\)', code)):
        check(name in appended or name.encode() in gunner, f'{unit}: sound {name} not in the merged bank')
    for name in set(re.findall(r'PLAY_SEQUENCE\(agent, Hash40::new\("([a-z0-9_]+)"\)', code)):
        crc = c.hash40(name).to_bytes(8, 'little')[:5]
        sqb = (c.RECIPIENT / 'sound/sequence/fighter/miigunner.sqb').read_bytes()
        check(c.hash40(name).to_bytes(5, 'little') in sqb, f'{unit}: sequence {name} not in miigunner.sqb')


def check_params(unit: str, code: str):
    params = c.load_prc(c.DONOR / 'fighter/cloud/param/vl.prc')['param_special_hi'][0]
    fp = c.load_prc(WS / 'gamedata/ssbu-13.0.4/files/fighter/common/param/fighter_param.prc')['fighter_param_table']
    cloud = next(r for r in fp if r.get('fighter_kind') == ('hash', 'fighter_kind_cloud'))
    consts = dict(re.findall(r'pub const ([A-Z0-9_]+): (?:f32|i32) = (-?[0-9.]+);', code))
    if unit == 'aerial_forward__cloud':
        check(abs(float(consts['LANDING_FRAME_F']) - cloud['landing_attack_air_frame_f']) < 1e-4,
              'landing lag differs from fighter_param landing_attack_air_frame_f')
        return
    for name, val in params.items():
        key = name.upper()
        if key in consts:
            check(abs(float(consts[key]) - float(val)) < 1e-4, f'{unit}: {key} = {consts[key]}, vl.prc {val}')
    used = [k for k in consts if k.startswith(('SPECIAL', 'HI2'))]
    check(len(used) == 14 and all(k.lower() in params for k in used), f'{unit}: parameter set {used}')


def check_sword():
    import ssbh_data_py as s
    model = SHARED / 'package/fighter/miigunner/model/mccloudsword/c00'
    motion = SHARED / 'package/fighter/miigunner/motion/mccloudsword/c00'
    mesh = s.mesh_data.read_mesh(str(model / 'model.numshb'))
    names = {o.name.split('_VIS_')[0] for o in mesh.objects}
    check(names == {'mccloud_sword_r', 'mccloud_sword_l'}, f'sword meshes {names}')
    check(all(o.parent_bone_name == 'Have' and not o.bone_influences for o in mesh.objects), 'sword mesh binding')
    check([b.name for b in s.skel_data.read_skel(str(model / 'model.nusktb')).bones] == ['Have'], 'sword skeleton')
    rs = MCCLOUD_RS.read_text(encoding='utf-8')
    _, path, entries = c.parse_mlist((motion / 'motion_list.bin').read_bytes())
    check(path == c.hash40('fighter/miigunner/motion/mccloudsword/c00'), 'sword motion list path hash')
    kinds = {e['kind'] for e in entries}
    for k in ('mc_cloud_sword_r', 'mc_cloud_sword_l'):
        check(c.hash40(k) in kinds and f'"{k}"' in rs, f'sword motion {k}')
    for e in entries:
        clip = [p for p in motion.glob('*.nuanmb') if c.hash40(p.name) == e['anims'][0]]
        if check(len(clip) == 1, 'sword clip hash resolves to no file'):
            a = s.anim_data.read_anim(str(clip[0]))
            vis = {n.name for g in a.groups if g.group_type.name == 'Visibility' for n in g.nodes}
            check(vis == names, f'sword clip {clip[0].name} visibility nodes {vis}')
    check('"mccloudsword"' in rs and 'fighter/miigunner/model/mccloudsword/c00/model.numshb' in rs, 'article name in code')
    for t in ('def_cloud_004_col', 'def_cloud_004_nor', 'def_cloud_004_prm'):
        check(c.sha256(model / f'{t}.nutexb') == c.sha256(c.DONOR / f'fighter/cloud/model/body/c00/{t}.nutexb'),
              f'sword texture {t} is not Cloud\'s')


def run(units) -> int:
    FAIL.clear()
    consts = lua_const()
    for unit in units:
        cfg = UNITS[unit]
        code = cfg['code'].read_text(encoding='utf-8')
        check_manifest(cfg['out'], unit)
        check_motion_entries(unit, cfg['out'], code, set())
        check_attacks(unit, cfg, code, consts)
        check_resources(unit, code)
        check_params(unit, code)
    check_sword()
    return len(FAIL)


def negative() -> int:
    """Each mutation must make the check fail."""
    caught = 0
    orig = {u: UNITS[u]['code'].read_text(encoding='utf-8') for u in UNITS}
    mutations = [
        ('aerial_forward__cloud', 'Hash40::new("top"), 14.0, 270', 'Hash40::new("top"), 14.0, 271'),
        ('special_up__cloud', 'pub const HI2_HIT_FALL_FRAME: i32 = 50;', 'pub const HI2_HIT_FALL_FRAME: i32 = 51;'),
        ('special_up__cloud', '"mc_cloud_climhazzard_slash3"', '"mc_cloud_climhazzard_slash4"'),
    ]
    real_read = Path.read_text
    for unit, a, b in mutations:
        assert a in orig[unit], a
        mutated = orig[unit].replace(a, b, 1)
        target = UNITS[unit]['code']

        def fake(self, *args, _t=target, _m=mutated, **kw):
            return _m if self == _t else real_read(self, *args, **kw)
        Path.read_text = fake
        try:
            n = run(list(UNITS))
        finally:
            Path.read_text = real_read
        print(f'negative control {unit}: {a!r} -> {b!r}: {"caught" if n else "NOT caught"} ({n} failures)')
        caught += bool(n)
    return 0 if caught == len(mutations) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--unit', choices=list(UNITS))
    ap.add_argument('--negative', action='store_true')
    a = ap.parse_args()
    if a.negative:
        return negative()
    n = run([a.unit] if a.unit else list(UNITS))
    for f in FAIL:
        print('FAIL', f)
    print('ALL CHECKS PASSED' if not n else f'{n} FAILURES')
    return 1 if n else 0


if __name__ == '__main__':
    raise SystemExit(main())
