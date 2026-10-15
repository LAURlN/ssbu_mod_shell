"""Locate and check the donor landing-lag parameter for the Pikachu back air (v1.0.0).

    python -B tools/audit_pikachu_airb_params.py
    python -B tools/audit_pikachu_airb_params.py --plugin <plugin dir>   # params.rs to check
    python -B tools/audit_pikachu_airb_params.py --negative-controls

Why this exists
---------------
1.0.0 kept `landing_attack_air_frame_b = 18.0` "because Pikachu's own value is not
reachable offline: the parameter lives in the shared `fighter/common` table, not
in `fighter/pikachu/param/vl.prc`". The first half is right and the conclusion is
wrong - a *shared* table is still in the game dump. It is
`fighter/common/param/fighter_param.prc`, one struct per fighter in a list of 94,
extracted from the local `data.arc` with `tools/arc-extract`, and
`tools/extract_gw_params.py` already reads its entries 26 (G&W) and 77 (Pyra).

Which entry is Pikachu's
------------------------
Not assumed from an index: the sibling list `fighter_param_motion.prc` has the
same 94 entries and names each by a `fighter_kind_<name>` hash (key
`0xc541ef0b2`), and the two lists agree on the entries the mod already relies on
(26 = `fighter_kind_gamewatch`, 77 = `fighter_kind_eflame`) and on four
unmistakable anchors - `purin` weight 68, `koopa` 135, `donkey` 127, `gamewatch`
75 - so the parallel order is measured, not recalled. Pikachu is entry 7.

Result (tier B, `fighter_param.prc` sha256 `87fcf45c...`)
---------------------------------------------------------
    landing_attack_air_frame_b   Pikachu 18.0   G&W 18.0   Pyra (eflame) 14.0

The two values are equal, so the 18.0 the 1.0.0 build shipped is numerically the
donor's own value; what was missing was the proof, and with it the guarantee that
the value survives a regeneration of `params.rs` from G&W's table. Nothing else
changes: the other four landing-lag entries of c06/c07 are still G&W's (n 7, hi 12,
lw 22) and Cloud's fair override (f 11).

Units and gating
----------------
The values are floats in **frames** (G&W's 7 / 17 / 18 / 12 / 22 for n / f / b /
hi / lw); the engine reads them through `WorkModule::get_param_float(module,
hash40("common"), hash40(<key>))` (the hook in `params.rs` matches parent `0` or
`common`) and the hook answers only when `is_target_fighter` holds: kind
`FIGHTER_KIND_EFLAME` **and** costume 6 or 7. Vanilla Pyra c00-c05, real G&W,
Pikachu and Mythra fall through to the engine's own table. This tool checks the
table side of that statement; the hook's gate is read from the source.

What it does not establish: that the engine's landing lag is exactly this number
of frames on a console (tier D), nor the hook's behaviour at runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
import prc  # noqa: E402

REF = ROOT / 'refs/pikachu_attack_air_b/arc/fighter/common/param'
FIGHTER_PARAM = REF / 'fighter_param.prc'
FIGHTER_PARAM_MOTION = REF / 'fighter_param_motion.prc'
PINS = {FIGHTER_PARAM: '87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2',
        FIGHTER_PARAM_MOTION: 'b154abfde83a060830e7f036c2df3d32213035ebeea03c7a578ae9866c1d4969'}
SNAPSHOT = ROOT / 'builds/.cache/silent-0.20.23/plugin'
DEFAULT_PLUGIN = ROOT / 'builds/.cache/pikachu-airb/plugin'

KIND_KEY = 0xc541ef0b2
ANCHORS = {'purin': 68.0, 'koopa': 135.0, 'donkey': 127.0, 'gamewatch': 75.0}
KEYS = {a: 'landing_attack_air_frame_' + a for a in ('n', 'f', 'b', 'hi', 'lw')}
# What params.rs must say for c06/c07: G&W's value for every aerial except the
# forward air, which is Cloud's 11 (attack_air_f.rs); the back air is the
# donor's, which is G&W's value too.
EXPECTED_RS = {'n': 7.0, 'f': 11.0, 'b': 18.0, 'hi': 12.0, 'lw': 22.0}


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _list(tree):
    return prc.as_dict(tree)[next(iter(prc.as_dict(tree)))][1]


def kinds() -> dict:
    """fighter name -> list index, from fighter_param_motion.prc."""
    names = {}
    candidates = ['mario', 'donkey', 'link', 'samus', 'yoshi', 'kirby', 'fox', 'pikachu',
                  'luigi', 'ness', 'captain', 'purin', 'peach', 'koopa', 'popo', 'nana',
                  'sheik', 'zelda', 'mariod', 'pichu', 'falco', 'marth', 'younglink',
                  'ganon', 'mewtwo', 'roy', 'gamewatch', 'metaknight', 'pit', 'eflame',
                  'elight', 'edge', 'cloud']
    wanted = {prc.hash40('fighter_kind_' + n): n for n in candidates}
    for i, entry in enumerate(_list(prc.read(FIGHTER_PARAM_MOTION))):
        h = prc.as_dict(entry)[KIND_KEY][1]
        if h in wanted:
            names[wanted[h]] = i
    return names


def table() -> dict:
    for path, digest in PINS.items():
        if sha(path) != digest:
            raise SystemExit(f'{path.name}: sha256 {sha(path)} != pinned {digest}')
    entries = _list(prc.read(FIGHTER_PARAM))
    motion = _list(prc.read(FIGHTER_PARAM_MOTION))
    if len(entries) != len(motion):
        raise SystemExit(f'fighter_param has {len(entries)} entries, fighter_param_motion {len(motion)}')
    index = kinds()
    weight = prc.hash40('weight')
    anchors = {n: prc.as_dict(entries[index[n]])[weight][1] for n in ANCHORS}
    out = {'entries': len(entries), 'index': {n: index[n] for n in
                                              ('pikachu', 'gamewatch', 'eflame', 'elight', 'cloud')
                                              if n in index},
           'anchors': anchors, 'anchors_hold': anchors == ANCHORS, 'landing': {}}
    for name in ('pikachu', 'gamewatch', 'eflame'):
        d = prc.as_dict(entries[index[name]])
        out['landing'][name] = {a: float(d[prc.hash40(k)][1]) for a, k in KEYS.items()}
    return out


def rs_values(plugin: Path) -> dict:
    text = (plugin / 'src/params.rs').read_text(encoding='utf-8')
    got = {}
    for a, key in KEYS.items():
        h = prc.hash40(key)
        m = re.search(r'0x%010x\s*=>\s*Some\(([-0-9.]+)f32\)' % (h & 0xffffffffff), text)
        got[a] = float(m.group(1)) if m else None
    gate = ('FIGHTER_KIND_EFLAME' in text and 'TARGET_COSTUMES.contains' in text
            and 'if is_target_fighter(boma)' in text)
    return {'values': got, 'gated_on_eflame_and_target_costumes': gate}


def verdict(t: dict, rs: dict, snapshot_rs: dict) -> list:
    bad = []
    if not t['anchors_hold']:
        bad.append(f'entry order is not the parallel order: anchors {t["anchors"]}')
    if t['index'].get('gamewatch') != 26 or t['index'].get('eflame') != 77:
        bad.append(f'gamewatch/eflame are not entries 26/77: {t["index"]}')
    if t['index'].get('pikachu') != 7:
        bad.append(f'pikachu is not entry 7: {t["index"]}')
    donor_b = t['landing']['pikachu']['b']
    if rs['values']['b'] != donor_b:
        bad.append(f'params.rs back-air landing {rs["values"]["b"]} != Pikachu {donor_b}')
    for a, want in EXPECTED_RS.items():
        if rs['values'][a] != want:
            bad.append(f'params.rs landing_attack_air_frame_{a} is {rs["values"][a]}, expected {want}')
    for a in KEYS:
        if rs['values'][a] != snapshot_rs['values'][a]:
            bad.append(f'landing_attack_air_frame_{a} differs from the 0.20.23 snapshot: '
                       f'{snapshot_rs["values"][a]} -> {rs["values"][a]}')
    if t['landing']['gamewatch']['b'] != 18.0:
        bad.append('G&W back-air landing is not 18.0 any more')
    if t['landing']['eflame']['b'] == donor_b:
        bad.append('Pyra (eflame) already equals the donor: the override would be meaningless')
    if not rs['gated_on_eflame_and_target_costumes']:
        bad.append('params.rs hook is not gated on eflame + TARGET_COSTUMES')
    return bad


def measure(plugin: Path) -> tuple:
    return table(), rs_values(plugin), rs_values(SNAPSHOT)


def negative_controls(plugin: Path) -> int:
    t, rs, snap = measure(plugin)
    assert not verdict(t, rs, snap), verdict(t, rs, snap)
    cases = []

    import copy
    for label, mutate in (
            ('params.rs back air set to Pyra\'s 14', lambda r: r['values'].__setitem__('b', 14.0)),
            ('params.rs forward air lost Cloud\'s 11', lambda r: r['values'].__setitem__('f', 17.0)),
            ('another aerial (up air) changed', lambda r: r['values'].__setitem__('hi', 14.0)),
            ('hook gate removed', lambda r: r.__setitem__('gated_on_eflame_and_target_costumes', False))):
        r = copy.deepcopy(rs)
        mutate(r)
        cases.append((label, verdict(t, r, snap)))
    # Real file damage: rewrite params.rs text in a throw-away copy.
    text = (plugin / 'src/params.rs').read_text(encoding='utf-8')
    with tempfile.TemporaryDirectory() as td:
        (Path(td) / 'src').mkdir()
        (Path(td) / 'src/params.rs').write_text(
            re.sub(r'(0x1a4262b54f => Some\()18\.0', r'\g<1>14.0', text), encoding='utf-8')
        cases.append(('params.rs file edited to 14.0', verdict(t, rs_values(Path(td)), snap)))
    t2 = copy.deepcopy(t)
    t2['index']['pikachu'] = 19      # Pichu's slot: a wrong index must be refused
    cases.append(('Pikachu resolved to the wrong entry', verdict(t2, rs, snap)))
    t3 = copy.deepcopy(t)
    t3['anchors_hold'] = False
    cases.append(('entry-order anchors fail', verdict(t3, rs, snap)))
    ok = 0
    for label, bad in cases:
        print(f'{"PASS" if bad else "FAIL"}: {label}: {bad[0] if bad else "NOT REJECTED"}')
        ok += bool(bad)
    print(f'{ok}/{len(cases)} damaged inputs rejected')
    return 0 if ok == len(cases) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--plugin', type=Path, default=DEFAULT_PLUGIN)
    ap.add_argument('--json', type=Path)
    ap.add_argument('--negative-controls', action='store_true')
    args = ap.parse_args()
    if args.negative_controls:
        return negative_controls(args.plugin)
    t, rs, snap = measure(args.plugin)
    print(f'fighter_param.prc: {t["entries"]} entries; indices {t["index"]}; anchors {t["anchors"]}')
    for name, vals in t['landing'].items():
        print(f'  {name:10} landing_attack_air_frame n/f/b/hi/lw = '
              f'{vals["n"]:g}/{vals["f"]:g}/{vals["b"]:g}/{vals["hi"]:g}/{vals["lw"]:g}')
    print(f'params.rs ({args.plugin}): {rs["values"]}, gated={rs["gated_on_eflame_and_target_costumes"]}')
    bad = verdict(t, rs, snap)
    for b in bad:
        print('FAIL:', b)
    if args.json:
        args.json.write_text(json.dumps({'table': t, 'params_rs': rs, 'snapshot_params_rs': snap,
                                         'failures': bad}, indent=1), encoding='utf-8')
    print('audit_pikachu_airb_params', 'FAILED' if bad else 'OK')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
