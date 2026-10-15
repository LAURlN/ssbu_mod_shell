"""Audit every hitbox the Pikachu back air opens, field by field (v1.0.0).

    python -B tools/audit_pikachu_airb_hitboxes.py            # check + print the table
    python -B tools/audit_pikachu_airb_hitboxes.py --json out.json
    python -B tools/audit_pikachu_airb_hitboxes.py --negative-controls

Why this exists
---------------
The 1.0.0 candidate documented the jab boxes as "bkb 100, kbg 40, kbscale 0,
x 3.5, y +/-4.0" and the finisher as "bkb 160, kbg 0, kbscale 40". Those labels
were read off the donor line by position and are **wrong**: the argument order of
`macros::ATTACK` is

    id, part, bone, damage, angle, KBG, FKB, BKB, size, x, y, z, x2, y2, z2, ...

so `1.0, 367, 100, 40, 0, 4.2, 0.0, 3.5, 4.0` is damage 1.0, angle 367, **KBG
100, FKB 40, BKB 0**, size 4.2 at (x 0, **y 3.5, z +/-4.0**) - a fixed-knockback
multihit - and the finisher `3.6, 45, 160, 0, 40, 5.0, 0, 7, 6 -> 0, 7, -4` is
**KBG 160, FKB 0, BKB 40**, size 5.0 on a capsule along z. The code was a verbatim
port and so was unaffected; only the documentation and the notes handed to the
meter work were. This tool replaces "read off by eye" with a derivation:

1. the field names come from the **pinned `smash-script` source**
   (`macros::ATTACK` parameter list, checked below when the checkout is present)
   - tier C;
2. every `ATTACK` and `AttackModule::clear_all` in the donor script text and in
   the Rust module is expanded with the script's own `frame`/`wait`/`for`
   structure into (frame, call, fields) events;
3. the two event lists must be identical field for field - so "the port is
   verbatim" is a measured statement - and the table printed is labelled with
   the names from (1);
4. the first/last active frame is compared with the game's own AI data
   (`fighter/pikachu/ai/param/attack_data_param.prc`, extracted from the
   local `data.arc`): `attack_air_b` start 4 / end 26, `landing_air_b` start 1 /
   end 3 - a source independent of the text dump - tier B.

What it does not establish: that a box connects with anything on the G&W body,
or that the dump has no conversion error in a *value* it prints. The latter would
need the native Pikachu script, which this workspace cannot decompile offline
(no Ghidra); the AI-data timing is the independent cross-check available.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
import prc  # noqa: E402

REF = ROOT / 'refs/pikachu_attack_air_b'
DONOR_TEXT = {'attack_air_b': REF / 'donor_acmd/AttackAirB.txt',
              'landing_air_b': REF / 'donor_acmd/LandingAirB.txt'}
AI_DATA = REF / 'arc/fighter/pikachu/ai/param/attack_data_param.prc'
RUST = ROOT / 'src/pgwr/plugin/src/acmd/pikachu_attack_air_b.rs'
SMASH_SCRIPT_GLOB = 'smash-script-*/*/src/macros.rs'

# macros::ATTACK parameter names, in call order (skipping the agent). Verified
# against the pinned source whenever a checkout of it can be found.
FIELDS = ('id', 'part', 'bone', 'damage', 'angle', 'kbg', 'fkb', 'bkb', 'size',
          'x', 'y', 'z', 'x2', 'y2', 'z2', 'hitlag', 'sdi', 'setoff', 'facing',
          'set_weight', 'shield_damage', 'trip', 'rehit', 'reflectable',
          'absorbable', 'flinchless', 'disable_hitlag', 'direct', 'ground_air',
          'hitbits', 'collision_part', 'friendly_fire', 'effect', 'sfx_level',
          'collision_sound', 'region')
# The names smash-script itself uses for the same parameters.
SIGNATURE_NAMES = ('id', 'part', 'bone', 'damage', 'angle', 'kbg', 'fkb', 'bkb',
                   'size', 'x', 'y', 'z', 'x2', 'y2', 'z2', 'hitlag', 'sdi',
                   'clang', 'facing', 'set_weight', 'shield_damage', 'trip',
                   'rehit', 'reflectable', 'absorbable', 'flinchless',
                   'disable_hitlag', 'direct', 'ground_air', 'hitbits',
                   'collision_part', 'friendly_fire', 'effect', 'sfx_level',
                   'collision_sound', '_type')


def find_signature() -> list | None:
    home = Path.home() / '.cargo/git/checkouts'
    for macros in sorted(home.glob(SMASH_SCRIPT_GLOB)):
        text = macros.read_text(encoding='utf-8', errors='replace')
        m = re.search(r'pub unsafe fn ATTACK<[^>]*>\(agent: &mut L2CAgentBase,(.*?)\)\s*\{',
                      text, re.S)
        if m:
            names = []
            for part in _split_args(m.group(1)):
                name = part.split(':')[0].strip()
                if name:
                    names.append(name)
            return names
    return None


def _split_args(text: str) -> list:
    out, depth, start = [], 0, 0
    for i, ch in enumerate(text):
        if ch in '(<[{':
            depth += 1
        elif ch in ')>]}':
            depth -= 1
        elif ch == ',' and depth == 0:
            out.append(text[start:i].strip())
            start = i + 1
    tail = text[start:].strip()
    if tail:
        out.append(tail)
    return out


def _norm(token: str):
    token = token.strip()
    m = re.fullmatch(r'Hash40::new\("([^"]+)"\)', token)
    if m:
        return m.group(1)
    m = re.fullmatch(r'Some\((.*)\)', token)
    if m:
        return _norm(m.group(1))
    if token == 'None':
        return None
    if token in ('true', 'false'):
        return token == 'true'
    if token.startswith('*'):
        return token[1:]
    try:
        v = float(token)
        return int(v) if re.fullmatch(r'-?\d+', token) else v
    except ValueError:
        return token


def _block_end(text: str, open_at: int) -> int:
    depth = 0
    for i in range(open_at, len(text)):
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
            if depth == 0:
                return i
    raise ValueError('unbalanced braces')


def _function_body(text: str, name: str) -> str:
    m = re.search(r'fn\s+' + re.escape(name) + r'\s*\([^)]*\)\s*\{', text)
    if not m:
        raise ValueError(f'no function {name}')
    return text[m.end():_block_end(text, m.end() - 1)]


TOKEN = re.compile(
    r'(?P<for>for\s+_\s+in\s+0\.\.(?P<count>\d+)\s*\{)'
    r'|(?P<frame>\bframe\(agent\.lua_state_agent,\s*(?P<fv>[-0-9.]+)\))'
    r'|(?P<wait>\bwait\(agent\.lua_state_agent,\s*(?P<wv>[-0-9.]+)\))'
    r'|(?P<attack>macros::ATTACK\()'
    r'|(?P<clear>AttackModule::clear_all\()'
    r'|(?P<call>\b(?P<callee>jab_window)\(agent\))')


def expand(body: str, helpers: dict, frame: float = 0.0) -> tuple:
    """Walk a script body into (frame, call, fields) events; returns (events, frame)."""
    events, pos = [], 0
    while True:
        m = TOKEN.search(body, pos)
        if not m:
            return events, frame
        if m.group('for'):
            end = _block_end(body, m.end() - 1)
            inner = body[m.end():end]
            for _ in range(int(m.group('count'))):
                sub, frame = expand(inner, helpers, frame)
                events += sub
            pos = end + 1
        elif m.group('frame'):
            frame = float(m.group('fv'))
            pos = m.end()
        elif m.group('wait'):
            frame += float(m.group('wv'))
            pos = m.end()
        elif m.group('call'):
            sub, _ = expand(helpers[m.group('callee')], helpers, frame)
            events += sub
            pos = m.end()
        elif m.group('clear'):
            events.append((frame, 'clear_all', None))
            pos = m.end()
        else:
            start = m.end()
            depth, i = 1, start
            while depth:
                depth += (body[i] == '(') - (body[i] == ')')
                i += 1
            args = _split_args(body[start:i - 1])
            if len(args) != len(FIELDS) + 1:
                raise ValueError(f'ATTACK with {len(args)} args at frame {frame}')
            events.append((frame, 'ATTACK',
                           {k: _norm(v) for k, v in zip(FIELDS, args[1:])}))
            pos = i


def donor_events(kind: str) -> list:
    text = DONOR_TEXT[kind].read_text(encoding='utf-8')
    name = 'game_attackairb' if kind == 'attack_air_b' else 'game_landingairb'
    return expand(_function_body(text, name), {})[0]


def rust_events(kind: str, path: Path = RUST) -> list:
    text = path.read_text(encoding='utf-8')
    helpers = {'jab_window': _function_body(text, 'jab_window')}
    name = 'game_attackairb' if kind == 'attack_air_b' else 'game_landingairb'
    return expand(_function_body(text, name), helpers)[0]


def ai_window(kind: str) -> dict:
    tree = prc.read(AI_DATA)
    items = prc.as_dict(tree)[prc.hash40('attack_data')][1]
    want = prc.hash40(kind)
    for item in items:
        d = prc.as_dict(item)
        if d[prc.hash40('motion_kind')][1] == want:
            return {k: d[prc.hash40(k)][1] for k in
                    ('start_frame', 'end_frame', 'cancel_frame')}
    raise ValueError(f'{kind} not in attack_data_param.prc')


def table(events: list) -> list:
    """One row per ATTACK, with the frame it opens and the frame that closes it."""
    rows = []
    for i, (frame, call, fields) in enumerate(events):
        if call != 'ATTACK':
            continue
        close = next((f for f, c, _ in events[i + 1:] if c == 'clear_all'), None)
        rows.append({'open': frame, 'close': close, **fields})
    return rows


def measure() -> dict:
    out = {'signature_verified_against_smash_script': None, 'moves': {}}
    sig = find_signature()
    if sig is not None:
        out['signature_verified_against_smash_script'] = (tuple(sig) == SIGNATURE_NAMES)
    for kind in ('attack_air_b', 'landing_air_b'):
        d, r = donor_events(kind), rust_events(kind)
        rows = table(d)
        ai = ai_window(kind)
        opens = [row['open'] for row in rows]
        closes = [f for f, c, _ in d if c == 'clear_all']
        out['moves'][kind] = {
            'donor_events': len(d), 'rust_events': len(r),
            'rust_equals_donor_field_for_field': d == r,
            'boxes': rows,
            'first_open': min(opens), 'last_clear': max(closes),
            'every_box_closed': all(row['close'] is not None for row in rows),
            'ai_data': ai,
            'ai_start_matches': int(min(opens)) == ai['start_frame'],
            'ai_end_matches': int(max(closes)) == ai['end_frame'],
        }
    return out


def verdict(m: dict) -> list:
    bad = []
    if m['signature_verified_against_smash_script'] is False:
        bad.append('FIELDS no longer match macros::ATTACK in the pinned smash-script')
    for kind, v in m['moves'].items():
        if not v['rust_equals_donor_field_for_field']:
            bad.append(f'{kind}: Rust ATTACK/clear_all events differ from the donor script')
        if not v['every_box_closed']:
            bad.append(f'{kind}: an ATTACK has no later clear_all')
        if not v['ai_start_matches']:
            bad.append(f'{kind}: first active frame {v["first_open"]} != AI start_frame '
                       f'{v["ai_data"]["start_frame"]}')
        if not v['ai_end_matches']:
            bad.append(f'{kind}: last clear {v["last_clear"]} != AI end_frame '
                       f'{v["ai_data"]["end_frame"]}')
    return bad


def render(m: dict) -> str:
    lines = []
    for kind, v in m['moves'].items():
        lines.append(f'{kind}: {len(v["boxes"])} ATTACK calls, first open {v["first_open"]:g}, '
                     f'last clear {v["last_clear"]:g}; AI data start/end/cancel '
                     f'{v["ai_data"]["start_frame"]}/{v["ai_data"]["end_frame"]}/'
                     f'{v["ai_data"]["cancel_frame"]}')
        for r in v['boxes']:
            end = '' if r['y2'] is None else f' -> ({r["x2"]}, {r["y2"]}, {r["z2"]})'
            lines.append(
                f'  f{r["open"]:g}-{r["close"]:g} id{r["id"]} {r["bone"]}: dmg {r["damage"]} '
                f'angle {r["angle"]} KBG {r["kbg"]} FKB {r["fkb"]} BKB {r["bkb"]} '
                f'size {r["size"]} at ({r["x"]}, {r["y"]}, {r["z"]}){end} '
                f'hitlag x{r["hitlag"]} sdi x{r["sdi"]} {r["facing"]} {r["effect"]} '
                f'{r["sfx_level"]}/{r["collision_sound"]} {r["region"]}')
    return '\n'.join(lines)


def negative_controls() -> int:
    """Each damaged input must make `verdict` complain."""
    import copy
    base = measure()
    assert not verdict(base), verdict(base)
    caught = 0
    cases = []

    m = copy.deepcopy(base)
    m['moves']['attack_air_b']['rust_equals_donor_field_for_field'] = False
    cases.append(('rust-differs', m))
    m = copy.deepcopy(base)
    m['moves']['attack_air_b']['every_box_closed'] = False
    cases.append(('box-never-closed', m))
    m = copy.deepcopy(base)
    m['moves']['landing_air_b']['ai_start_matches'] = False
    cases.append(('landing-start-wrong', m))
    m = copy.deepcopy(base)
    m['signature_verified_against_smash_script'] = False
    cases.append(('signature-drift', m))
    for label, case in cases:
        got = verdict(case)
        print(f'{"PASS" if got else "FAIL"}: {label}: {got[:1]}')
        caught += bool(got)

    # Real damage: edit a throw-away copy of the Rust module so the parsed events
    # genuinely change, rather than flipping a flag the verdict reads.
    import tempfile
    text = RUST.read_text(encoding='utf-8')
    for label, old, new in (
            ('kbg-fkb-swapped', '1.0, 367, 100, 40, 0, 4.2', '1.0, 367, 40, 100, 0, 4.2'),
            ('finisher-frame-moved', 'wait(agent.lua_state_agent, 2.0);\n    if macros::is_excute(agent) {\n        AttackModule::clear_all(agent.module_accessor);\n    }\n    frame(agent.lua_state_agent, 38.0);',
             'wait(agent.lua_state_agent, 3.0);\n    if macros::is_excute(agent) {\n        AttackModule::clear_all(agent.module_accessor);\n    }\n    frame(agent.lua_state_agent, 38.0);')):
        if old not in text:
            print(f'FAIL: {label}: pattern not found, control is not live')
            continue
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'damaged.rs'
            p.write_text(text.replace(old, new, 1), encoding='utf-8')
            m = copy.deepcopy(base)
            for kind in m['moves']:
                m['moves'][kind]['rust_equals_donor_field_for_field'] = (
                    donor_events(kind) == rust_events(kind, p))
            got = verdict(m)
            print(f'{"PASS" if got else "FAIL"}: {label}: {got[:1]}')
            caught += bool(got)
    total = len(cases) + 2
    print(f'{caught}/{total} damaged inputs rejected')
    return 0 if caught == total else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--json', type=Path)
    ap.add_argument('--negative-controls', action='store_true')
    args = ap.parse_args()
    if args.negative_controls:
        return negative_controls()
    m = measure()
    print(render(m))
    print('signature verified against pinned smash-script:',
          m['signature_verified_against_smash_script'])
    bad = verdict(m)
    for b in bad:
        print('FAIL:', b)
    if args.json:
        args.json.write_text(json.dumps(m, indent=1), encoding='utf-8')
    print('audit_pikachu_airb_hitboxes', 'FAILED' if bad else 'OK')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
