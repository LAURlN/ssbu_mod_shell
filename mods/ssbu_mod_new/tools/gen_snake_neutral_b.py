"""Generate Pyra c06/c07's owned Snake neutral-B scripts and parameters (v1.2.0).

Outputs (never hand-edit them; re-run this):
  src/pgwr/plugin/src/status/snake_grenade/acmd.rs    ACMD for the 14 `pgwr_snake_*` motions
  src/pgwr/plugin/src/status/snake_grenade/params.rs  Snake's param_special_n / param_snakegrenade
  refs/snake_grenade/acmd_translation.json            inputs with sha256

Donor text: WuBoytH `smashline-hdr/lua2cpp_snake/snake/SpecialN*.txt` (tier C; dump text is evidence,
not code). Every rule below is explicit and asserted, and anything the rules do not cover fails:

  S1 `generate_article(GRENADE)` -> `super::pull(agent)`: Pyra creates the real
     ITEM_KIND_SNAKEGRENADE in her own hand (no Snake article; `projects/pgwr/TODO.md`).
  S2 The dump's conversion error around the throw, i.e.
     `battle_object(); methodlib...; is_constraint_article(); if(false){ ... shoot(GRENADE, LAST) ... }`,
     is `if FighterSpecializer_Snake::is_constraint_article(GRENADE, LAST) { shoot }` in the NRO
     (`lua2cpp_snake.nro` 13.0.4). It becomes `if super::holding(boma) { ... super::release(agent) }`.
  S3 `GRENADE_PIN` creation/visibility -> owned pin helper calls; donor timing is retained.
  S4 Sounds `se_snake_special_n01..03` stay as they are. They are Snake's bank entries; until the
     bank is merged into eflame's (`refs/snake_grenade/arc/sound/`), playback is unverified. No stand-in.

Params come from `dumps/arc/fighter/snake/param/vl.prc` (sha256 in the output header).
`--check` regenerates in memory and requires the files on disk to match.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
CFG = tomllib.loads((ROOT / 'paths.toml').read_text())
DONOR = ROOT / CFG['dumps']['scripts'] / 'smashline-hdr/lua2cpp_snake/snake'
VL = ROOT / CFG['dumps']['arc'] / 'fighter/snake/param/vl.prc'
OUT_DIR = ROOT / 'src/pgwr/plugin/src/status/snake_grenade'
RECORD = ROOT / 'refs/snake_grenade/acmd_translation.json'
sys.path.insert(0, str(ROOT / 'src/pgwr/tools'))
from gen_acmd import split_functions  # noqa: E402
import prc  # noqa: E402

VERSION = '1.2.0'
# (donor file stem, donor motion kind). The owned kind is `pgwr_snake_<kind>`.
SOURCES = [
    ('SpecialNStart', 'special_n_start'), ('SpecialNHold', 'special_n_hold'),
    ('SpecialNThrowLw', 'special_n_throw_lw'), ('SpecialNThrowM', 'special_n_throw_m'),
    ('SpecialNThrowHi', 'special_n_throw_hi'), ('SpecialNClose', 'special_n_close'),
    ('SpecialNThrowFail', 'special_n_throw_fail'), ('SpecialAirNStart', 'special_air_n_start'),
    ('SpecialAirNJumpAerial', 'special_air_n_jump_aerial'),
    ('SpecialAirNThrowLw', 'special_air_n_throw_lw'), ('SpecialAirNThrowM', 'special_air_n_throw_m'),
    ('SpecialAirNThrowHi', 'special_air_n_throw_hi'),
    ('SpecialAirNThrowFail', 'special_air_n_throw_fail'),
]
LOWER_SOURCES = [('ItemLegsWalk' + d, 'item_shoot_legs_walk_' + d.lower()) for d in ('F', 'B')]
LOWER_SOURCES += [('ShootLegs' + title, 'item_shoot_legs_' + kind) for title, kind in (
    ('Wait', 'wait'), ('DashF', 'dash_f'), ('DashB', 'dash_b'),
    ('BrakeF', 'brake_f'), ('BrakeB', 'brake_b'), ('JumpSquat', 'jump_squat'),
    ('Landing', 'landing'), ('SlowF', 'slow_f'), ('SlowB', 'slow_b'),
    ('MiddleF', 'middle_f'), ('MiddleB', 'middle_b'), ('FastF', 'fast_f'), ('FastB', 'fast_b'))]

def translate_lower(name, text):
    """Repair measured native loop boundaries/gates, not the dump's unwind artifacts.

    Native registration/body signatures and recovered C: lower_acmd_native.json/C.
    The cyclic functions begin with their first frame and yield at the loop end.
    Slow effects have an initial pair followed by a distinct cycling pair.
    """
    text = text.replace('let boma = agent.boma();', 'let boma = agent.module_accessor;')
    declarations, content = text.split('    let boma = agent.module_accessor;', 1)
    content = content.rsplit('}', 1)[0]
    cycling = 'wait_loop_sync_mot();' in content
    initial = ''
    if name in ('effect_shootlegsslowf', 'effect_shootlegsslowb'):
        initial, content = content.split('    wait_loop_sync_mot();', 1)
        content = content.replace('    methodlib::L2CAgent::pop();\n', '')
        content = content.replace('    wait_loop_sync_mot();\n', '')
        foot = re.search(r'        (FOOT_EFFECT\([^\n]+;)', content).group(1)
        other = foot.replace('"footl"', '"footr"') if name.endswith('f') else foot.replace('"footr"', '"footl"')
        assert content.count('loc.imp._Unwind_Resume();') == 1
        content = content.replace('    loc.imp._Unwind_Resume();', '    ' + other)
        initial += '\n    agent.clear_lua_stack();\n    smash::app::sv_animcmd::wait_loop_sync_mot(lua_state);\n    agent.pop_lua_stack(1);\n'
    else:
        content = content.replace('    wait_loop_sync_mot();\n', '')
    # Native bodies gate the second event too; the text loses that predicate.
    lines = []
    for line in content.splitlines():
        if re.match(r'^    (FOOT_EFFECT|PLAY_STEP_FLIPPABLE|ControlModule::set_rumble)\(', line):
            lines += ['    if is_excute(agent) {', '    ' + line, '    }']
        else:
            lines.append(line)
    content = '\n'.join(lines)
    assert all(x not in content for x in ('methodlib', 'loc.imp', 'wait_loop_sync_mot();'))
    if cycling:
        content = '    loop {\n' + content + '\n    agent.clear_lua_stack();\n    smash::app::sv_animcmd::wait_loop_sync_mot(lua_state);\n    agent.pop_lua_stack(1);\n    }\n'
    return declarations + '    let boma = agent.module_accessor;\n' + initial + content + '\n}\n'
# special_air_n_hold has no donor scripts (no file in the dump); its entry keeps none.

CONSTRAINT = re.compile(
    r'battle_object\(\);\s*methodlib::L2CValue::L2CValue\(void\*\)\(\);\s*'
    r'methodlib::L2CValue::L2CValue\(lib::L2CValueconst&\)\(\);\s*'
    r'methodlib::L2CValue::as_pointer\(\)const\(\*FIGHTER_SNAKE_GENERATE_ARTICLE_GRENADE, '
    r'\*ARTICLE_OPE_TARGET_LAST\);\s*is_constraint_article\(\);\s*if\(false\)\{')
SHOOT = 'ArticleModule::shoot(boma, *FIGHTER_SNAKE_GENERATE_ARTICLE_GRENADE, *ARTICLE_OPE_TARGET_LAST, false);'
PIN_LINES = [
    'ArticleModule::generate_article(boma, *FIGHTER_SNAKE_GENERATE_ARTICLE_GRENADE_PIN, false, -1);',
    'ArticleModule::set_visibility_whole(boma, *FIGHTER_SNAKE_GENERATE_ARTICLE_GRENADE_PIN, false, '
    'ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL));',
    'ArticleModule::set_visibility_whole(boma, *FIGHTER_SNAKE_GENERATE_ARTICLE_GRENADE_PIN, true, '
    'ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL));',
]
GENERATE = 'ArticleModule::generate_article(boma, *FIGHTER_SNAKE_GENERATE_ARTICLE_GRENADE, false, -1);'


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def translate(name: str, text: str, counts: dict) -> str:
    text, n = CONSTRAINT.subn('if super::holding(boma) {', text)
    counts['S2'] += n
    if n:
        assert text.count(SHOOT) == n, name
        text = text.replace(SHOOT, 'super::release(agent);')
    for line, replacement in zip(PIN_LINES, ('super::pin::generate(agent);',
                                           'super::pin::visibility(boma, false);',
                                           'super::pin::visibility(boma, true);')):
        k = text.count(line)
        counts['S3'] += k
        text = text.replace(line, replacement)
    k = text.count(GENERATE)
    counts['S1'] += k
    text = text.replace(GENERATE, 'super::pull(agent);')
    text = text.replace('let boma = agent.boma();', 'let boma = agent.module_accessor;')
    assert 'FIGHTER_SNAKE_' not in text, (name, [l for l in text.splitlines() if 'FIGHTER_SNAKE_' in l])
    assert 'methodlib' not in text and 'if(false)' not in text, name
    assert text.count('{') == text.count('}'), name
    return text


def acmd():
    parts = [f'// Generated by tools/gen_snake_neutral_b.py v{VERSION}; do not edit.',
             '// Snake neutral-B scripts for the owned `pgwr_snake_*` motions on Pyra c06/c07.',
             'use smash::{app::{lua_bind::*, sv_animcmd::{frame, wait}}, lib::lua_const::*, lua2cpp::*, phx::*};',
             'use smash_script::{*, macros::*};', 'use smashline::*;']
    regs, inputs = [], []
    counts = {'S1': 0, 'S2': 0, 'S3': 0}
    for stem, kind in SOURCES + LOWER_SOURCES:
        path = DONOR / f'{stem}.txt'
        inputs.append({'path': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)})
        donor_stem = stem.lower()
        for name, body in split_functions(path.read_text()).items():
            cat, suffix = name.split('_', 1)
            assert suffix == donor_stem, (path.name, name)
            body = translate_lower(name, body) if (stem, kind) in LOWER_SOURCES else translate(name, body, counts)
            owned_fn = f'{cat}_pgwrsnake{kind.replace("_", "")}'
            body = body.replace(f'fn {name}(', f'pub(super) unsafe extern "C" fn {owned_fn}(', 1)
            body = body.replace('unsafe extern "C" pub(super) unsafe extern "C"', 'pub(super) unsafe extern "C"')
            assert f'fn {owned_fn}(' in body, name
            parts.append(body)
            regs.append((cat, owned_fn))
    # Every donor throw had its shoot translated; both starts create the grenade.
    assert counts['S1'] == 2 and counts['S2'] == 6 and counts['S3'] == 6, counts
    parts.append('pub(super) fn install() {')
    parts.append('    Agent::new("eflame")')
    parts.append('        .set_costume(crate::TARGET_COSTUMES.to_vec())')
    for cat, fn in regs:
        parts.append(f'        .{cat}_acmd("{fn}", {fn}, Priority::Low)')
    parts.append('        .install();')
    parts.append('}')
    return '\n'.join(parts) + '\n', inputs, counts


def params():
    tree = prc.as_dict(prc.read(VL))

    def first_struct(key):
        tag, items = tree[prc.hash40(key)]
        assert tag == 'list', key
        return prc.as_dict(items[0])
    lines = [f'// Generated by tools/gen_snake_neutral_b.py v{VERSION}; do not edit.',
             f'// Source: {VL.relative_to(ROOT).as_posix()}', f'// SHA256: {sha(VL)}',
             '// Snake\'s own values, read here so Pyra never asks the engine for Snake\'s params.']
    special = first_struct('param_special_n')
    for key in ('throw_m_speed_x', 'throw_m_speed_y', 'throw_hi_speed_x', 'throw_hi_speed_y',
                'throw_lw_speed_x', 'throw_lw_speed_y', 'throw_hi_threshold', 'throw_lw_threshold'):
        tag, value = special[prc.hash40(key)]
        assert tag == 'float', key
        lines.append(f'pub const {key.upper()}: f32 = {value!r}f32;')
    tag, life = first_struct('param_snakegrenade')[prc.hash40('life')]
    assert tag in ('i32', 'u32') and life == 150, (tag, life)
    lines.append('/// `param_snakegrenade[0].life`: what `app::snakegrenade::life()` returns with Snake loaded.')
    lines.append(f'pub const GRENADE_LIFE: i32 = {life};')
    return '\n'.join(lines) + '\n'


def outputs():
    source, inputs, counts = acmd()
    record = {'version': VERSION, 'evidence_tier': 'B', 'hardware_validated': False,
              'inputs': inputs + [{'path': VL.relative_to(ROOT).as_posix(), 'sha256': sha(VL)}],
              'rules_applied': counts,
              'not_ported': [],
              'lower_native_evidence': 'refs/snake_grenade/lower_translation_audit.json',
              'no_donor_scripts': ['special_air_n_hold']}
    return {OUT_DIR / 'acmd.rs': source, OUT_DIR / 'params.rs': params(),
            RECORD: json.dumps(record, indent=2) + '\n'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check', action='store_true')
    args = ap.parse_args()
    for path, content in outputs().items():
        if args.check:
            assert path.read_text() == content, f'{path} differs from the generator output'
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
    print(f'PASS: {len(SOURCES) + len(LOWER_SOURCES)} donor script files translated, params pinned')


if __name__ == '__main__':
    main()
