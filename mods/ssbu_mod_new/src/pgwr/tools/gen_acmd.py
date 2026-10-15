"""Generate the phase-2 Rust ACMD modules from the G&W script dumps.

Why generate instead of hand-writing 27 files
---------------------------------------------
The port is mechanical in every respect that matters, and the failure mode of
hand-copying ~110 functions is a silently mistyped hitbox. Generating from the
dump makes the translation reproducible, reviewable in one place, and rerunnable
when a dump is corrected. The transformations are listed in RULES below and each
one is applied by an explicit rule, so a reviewer can check the rule list rather
than diff 110 functions.

The dumps are evidence, not truth (see .agents/rules/movemakerguide.md), so the
output is reviewed by hand after generation. Every drop is recorded in the
emitted `GEN-NOTES` block and in port-dependencies.json, not silently applied.

Transformations, and why each is required
-----------------------------------------
R1  Drop `ArticleModule::*` lines that name a G&W article. G&W's articles run
    0-8; eflame's stop at `FIGHTER_EFLAME_ARTICLE_TERM: 0x5`. Generating an index
    eflame does not have writes outside her article table. Phase 4 owns articles
    and `clone_weapon`.
R13 G&W sound names are kept verbatim; nothing is substituted. `tools/merge_gw_sound.py`
    appends G&W's real tone records and audio to Pyra's own `se_eflame_c06`/`c07` banks,
    the same approach `tools/merge_hero_neutral_b_sound.py` uses for Hero, so the donor
    names resolve on the target fighter: measured 0/22 resolvable before the merge and
    22/22 after. This supersedes the old R2, which rewrote each donor name to an
    `se_eflame_*` stand-in so something audible would come out. That was a stand-in
    (AGENTS.md rule 17 forbids it) and it collapsed three distinct G&W waves onto one
    Pyra swing, so the jab, dash and aerial all sounded the same. `se_common_*` names
    were always kept; they name the always-resident common bank. R2's old numbering is
    retired rather than reused - see the note above SOUND_MAP and `SOUND_MAP = {}`.
R3  Drop `notify_event_msc_cmd!` calls carrying `Hash40::new_raw(...)`. The raw
    value could not be resolved to a name (checked against every plausible
    command name), and these are NRO-relative per the project's rules, so
    guessing is not allowed. Recorded as an open item.
R4  `hash40("x") as i64` -> `as u64`. The dump's signature does not match the
    locked skyline-smash revision (315e4e8), where `set_int64` takes u64. This
    was a real compile error before it was found.
R5  Rename functions to the *Pyra* status they are registered under, so several
    Pyra statuses can share one G&W source (Attack12/Attack13 reuse Attack11).

R6  Drop any line that writes a G&W WorkModule index. `*FIGHTER_GAMEWATCH_INSTANCE_WORK_ID_*`
    and `*WEAPON_GAMEWATCH_*` are raw per-fighter values, not symbolic names, and
    an eflame agent's work array is laid out differently. This rule exists because
    the first review pass missed it: R1 only matched `ArticleModule::`, so a
    `WorkModule::set_int(..., *FIGHTER_GAMEWATCH_INSTANCE_WORK_ID_INT_NORMAL_WEAPON_KIND)`
    in the aerials survived generation and would have written G&W's index 0x100000BD
    into Pyra's storage. Never assume dropping the article drops its work id.
R12 Drop lines that spawn an `eflame_*` or `elght_*` effect. These are Pyra's
    and Mythra's own effect banks, and while a script that calls them is a Pyra
    script that should have been replaced, a missed status would otherwise keep
    playing Pyra's magic effects on G&W's body. This rule is a backstop, not a
    substitute for porting the status. It was added when `effect_attack100` was
    found still spawning `eflame_attack100_hand` during the rapid-fire, which is
    the "leftover Pyra animations" the user reported on 0.3.0. It did not need to
    fire for the G&W donors, because their scripts do not name Pyra effects.
R13 Bare `wait_loop_sync_mot()` -> `sv_animcmd::wait_loop_sync_mot(agent.lua_state_agent)`.
    Same family as R10: the dump calls the raw `sv_animcmd` symbol with no
    arguments, but the binding takes the lua_State. Unlike AREA_WIND there is no
    `macros::` wrapper for this one, so the raw call with the state passed
    explicitly is the correct form. It appears only in G&W's rapid-fire scripts.
R7  Collapse `if macros::is_excute(agent) { }` blocks left empty by a drop. Purely
    cosmetic, but an empty block reads like a missed statement during review.

The next four are dump-vs-toolchain mismatches found by the first compile of the
generated output. Each is a place where the dump's signature does not match the
locked skyline-smash revision (315e4e8) or smash-script (fdc6144), which is the
conversion-error risk movemakerguide.md warns about.

R8  `ItemModule::set_attach_item_visibility(a, b)` -> `(a, b, 0)`. The binding
    (cpp.rs:17755) takes a third `u8` the dump omits.
R9  `VisibilityModule::set_default_int64(a, Hash40::new("x"))` ->
    `set_default_int64(a, hash40("x"))`. The binding (cpp.rs:18188) takes
    `c_ulong`, and `Hash40` is a struct (cpp.rs:21869) that does not coerce with
    `as`. `smash::hash40()` is the function that yields the raw u64. Note this is
    *not* the same thing as R4: `hash40("x") as u64` is a cast of a u64 to u64 and
    R4 must not touch it.
R10 Bare `AREA_WIND_2ND_arg10(...)` -> `macros::AREA_WIND_2ND_arg10(agent, ...)`.
    The dump calls the raw `sv_animcmd` symbol, which takes only the lua_State.
    The ten arguments belong to the smash_script wrapper (macros.rs:1216), which
    pushes them first.
R11 The two-line construct

        WorkModule::is_flag(agent.module_accessor, *FLAG);
        if(methodlib::L2CValue::operator==(lib::L2CValueconst&)const(false, true)){

    is a conversion artifact for the Lua `if WorkModule.is_flag(...) then`. It
    is rewritten to a single `if WorkModule::is_flag(agent.module_accessor, *FLAG) {`.
    Left as-is it is a discarded return value plus a hardcoded `false == true`
    branch that never runs, so the guarded body would silently stop executing.

R21 Conditions on a G&W article id become `if false`; other statements naming one are
    dropped. eflame's article table has 5 entries, so indexing G&W's id 5 reads past it.
R23 Restore the `normal_weapon` article calls that R1/R6/R21 drop, and only those.
    0.11.0: the article is registered on eflame at boot by THIS mod's plugin
    (`plugin/src/article.rs`, smashline `clone_weapon`), not by a patched global
    plugin. The id a move passes is eflame's *local* article index, which is
    `FIGHTER_EFLAME_ARTICLE_TERM` + the index clone_weapon returns (G&W's 125 is the
    global weapon kind, a different number), so every use goes through
    `crate::article::normal_weapon()`. G&W's kind work-int becomes plugin-owned
    per-entry storage holding G&W's own `WEAPON_GAMEWATCH_NORMAL_WEAPON_KIND_*`
    values rather than his raw 0x100000BD, and `IS_EXIST_ARTICLE` becomes a real
    condition instead of `if false`. The *other* G&W articles (bomb, rescue,
    parachute, panel, oil) are still dropped, because they belong to the specials and
    are not registered. One added log line, `article::note_spawn`, is an addition and
    not donor code; it exists so a missing prop and a misplaced one are
    distinguishable in the log.
R26 0.12.0: the same treatment for `breath`, G&W's up-air projectile, which
    `plugin/src/article.rs` now registers on eflame as a second clone (local
    article id `TERM + 1`). `game_attackairhi` in the donor is exactly two
    article calls - `generate_article` at frame 8 and `shoot` at frame 9 - and
    no hitbox, so without this rule the whole move is empty. Runs before R1 for
    the same reason R23 does: the id has to stop naming a G&W constant before
    R1 sees the line. `article::note_breath` is an addition, like R23's
    `note_spawn`, so the log distinguishes "never spawned" from "spawned".
    The calls use the version-checked breath parameter bridge (0.14.0).
    Native spawn and donor status parameters are supplied for the clone only.
R25 The dump's two-line `get_value_float(<article>, *SO_VAR_FLOAT_MOTION_RATE_TOTAL);` +
    `macros::SET_RATE_ARTICLE_V(agent, 256);` is one call in G&W's compiled
    `game_landingairn` (lua2cpp_gamewatch.nro 0xc032c-0xc03a4): push the article id,
    push `get_value_float(lua_state, SO_VAR_FLOAT_MOTION_RATE_TOTAL)`, call
    SET_RATE_ARTICLE_V. The `256` is decompiler noise. Rewritten to that call.
R14 (gen_common.py) A G&W script textually identical to Pyra's is not overridden.
R15 `methodlua2cpp::L2CFighterAnimcmd<X>Common::fn(args)` -> the binding, called on
    the agent cast to that class. The dump prints a garbled path for a real method
    of `smash::lua2cpp::L2CFighterAnimcmd{Game,Effect,Sound,Expression}Common`
    (e.g. `expression_JumpRumble`, `game_SwordSwing1Common`); the ACMD agent is an
    instance of that class at runtime, so the cast is valid.
R16 `frame(false, N)` / `wait(false, N)` -> `(agent.lua_state_agent, N)`. The dump
    prints the lua_State argument as `false`.
R17 Bare `wait_loop_clear()` -> `sv_animcmd::wait_loop_clear(agent.lua_state_agent)`
    (same family as R13).
R18 Bare `THROW_ITEM_arg3(a, b, c)` -> `macros::THROW_ITEM_arg3(agent, a, b, c)`.
R19 `<call>;` followed by `if(methodlib::L2CValue::operator==(...)(false, X)){` is
    Lua `if <call> == X then`. Generalises R11 to any preceding call: X=true gives
    `if <call> {`, X=false gives `if !<call> {`.
R20 `macros::NAME(` for NAME in THROW_ITEM_OFFSET, SHOOT_ITEM_BULLET,
    SHOOT_ITEM_BULLET_CHARGE, IS_HAVE_ITEM_KIND, DOWN_EFFECT, SET_RATE_ARTICLE_V ->
    `crate::acmd::compat::NAME(`; the pinned smash_script has no such macro, and
    `plugin/src/acmd/compat.rs` supplies it.
R22 (REMOVED, and do not re-add it) was a rule that rewrote
    `VisibilityModule::set_int64(hash40("rhand"), hash40("rhand_hammer"))` into a
    direct `ModelModule::set_mesh_visibility(.., true)`, on the theory that the
    hammer was shown by native code because `rhand_hammer` is not a state in any
    visibility table. **The premise was wrong and the rule is gone.**

    What is actually true, measured: the `rhand` group has exactly one state and
    it is the empty one, so there is no `rhand_hammer` and no `lhand_hammer` -
    the donor's `set_int64` calls for them are dead code and stay dead. But the
    hammer does not need them. G&W's own clips turn `RHammerM` on by themselves,
    in exactly the three moves that use it: `f03downattacku` and `f04downattackd`
    at frame 11, `g03slipattack` at frame 18. Those three clip names are not
    aliased - they overwrite Pyra's same-named files, and the built files are
    byte-identical to G&W's export - and the down-attack statuses resolve their
    motion by name, so the track plays on its own. Nothing was broken.

    The lesson, kept because it generalises: a dead `set_int64` in a donor script
    is not evidence that the prop is missing. Check whether the *clip* already
    carries the visibility track before concluding the prop needs a code fix.
    `tools/visibility_table.py` resolves the table's mesh names for this.

R27 0.19.0, up-B (Fire): G&W's four `FIGHTER_GAMEWATCH_STATUS_SPECIAL_HI_FLAG_*` writes
    become `crate::status::special_hi::on_flag(.., FLAG_*)`. Like R6 these are raw
    per-fighter work indices; unlike R6 they are the only way the donor's status
    code learns the frame (direction on 9, landing on 11, parachute on 33), so they
    are redirected to the plugin-owned storage the ported statuses read, not dropped.
R28 R3 does not apply to hashes in NOTIFY_KEEP. `0x2127e37c07` is a hash40
    constant, not an NRO-relative value: it is loaded as an immediate at three sites in
    `lua2cpp_gamewatch.nro` and appears in 451 dumped scripts across fighters. With
    `GROUND_CLIFF_CHECK_KIND_ALWAYS` it is how up-B lets G&W grab the ledge from frame
    14; dropping it would leave the status's ON_DROP cliff check in force.
R29 Groups in FILL_EMPTY register an empty function for each category the donor has
    no script for. Up-B's clip names are Pyra's too (`special_hi`, `special_air_hi`), so
    without the stub her own effect script for that name would keep running on G&W's
    body - the same leftover-Pyra-effect failure R12 backs up.
R30 WEAPON_GROUPS port an article's own scripts from `lua2cpp_gamewatch/gamewatch_<a>/`
    onto the cloned `eflame_<a>` agent (0.19.0: `rescue` and `parachute`, visibility
    only). They are cloned with `use_original_code = false`, so these copies are the
    only scripts the articles run; G&W's module is never loaded for them.

Bones need no rule: the only ATTACK bone G&W uses is `top`, which is not a bone at
all but Smash's built-in fighter-top anchor.

Run:
    toolchains/py312/python.exe src/pgwr/tools/gen_acmd.py
    toolchains/py312/python.exe src/pgwr/tools/gen_acmd.py --check
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GW_ROOT = ROOT / 'dumps' / 'scripts' / 'SSBU-Dumped-Scripts-main' / 'smashline' / 'lua2cpp_gamewatch'
GW = GW_ROOT / 'gamewatch'
OUT_DIR = Path(__file__).resolve().parents[1] / 'plugin' / 'src' / 'acmd' / 'generated'

HEADER = '''// @generated by tools/gen_acmd.py from SSBU-Dumped-Scripts-main/smashline/
// lua2cpp_gamewatch/gamewatch/*.txt. Do not edit by hand: change the generator
// and re-run, or the next run will silently discard the edit.
// {drops}
use {{
    smash::{{
        lua2cpp::*,
        phx::*,
        app::{{sv_animcmd::*, lua_bind::*, *}},
        lib::{{lua_const::*, L2CValue, L2CAgent}},
        hash40
    }},
    smash_script::*,
    smashline::{{*, Priority::*}}
}};

use crate::TARGET_COSTUMES;
'''

# R2. G&W sound names are now KEPT VERBATIM. The substitution table that used to live
# here is gone, and rule 13 in the RULES docstring explains why.
#
# What it was: every `se_gamewatch_*` name rewritten to an `se_eflame_*` one, so that
# something audible came out of a move whose own sound was unreachable.
#
# Why that was wrong: it is a stand-in, which AGENTS.md rule 17 forbids ("no stand-in
# sounds ... presented as done"), and it replaced the exact noises that identify the
# moves. `wave04_mi` is G&W's own swing for his jab and rapid pokes; swapping in
# Pyra's sword swing is the "leftover Pyra" symptom in a different costume. Substituting
# also loses the information the port is trying to keep - three distinct G&W waves
# (`wave01`, `wave02`, `wave04`) collapsed onto one `swing_s01`, so the jab, the dash and
# the aerial became audibly identical.
#
# Why it is no longer needed: the sounds were never missing, only unreachable from this
# fighter's bank list. `tools/merge_gw_sound.py` appends G&W's real tone records and
# audio to Pyra's own `se_eflame_c06` / `se_eflame_c07` banks (the same approach
# `tools/merge_hero_neutral_b_sound.py` already uses for Hero), so all 22 names the
# ported scripts reference resolve on the target fighter. Measured: 0/22 before the
# merge, 22/22 after. c00-c05 keep their own banks, so the vanilla control stays vanilla.
#
# SOUND_KEEP below is now the whole rule: `se_gamewatch_*` and `se_common_*` both pass
# through untouched. Anything else is reported as unmapped rather than silently rewritten.
SOUND_MAP = {}
# Kept verbatim, and why.
#   se_gamewatch_* : resolved by the merged bank (tools/merge_gw_sound.py), tier B.
#   se_common_*    : names the always-resident common bank, so it resolves for every
#                    fighter. This export has no common SFX bank, so that stays an
#                    inference from the name rather than a verified measurement.
SOUND_KEEP = {'se_common_throw_02', 'se_common_throw_03'}

# Pyra status -> G&W source script. Five Pyra statuses have no G&W counterpart.
PORT = {
    # ground normals
    'Attack11': 'Attack11', 'Attack12': 'Attack11', 'Attack13': 'Attack11',
    'AttackDash': 'AttackDash',
    'AttackHi3': 'AttackHi3', 'AttackHi4': 'AttackHi4', 'AttackHi4Charge': 'AttackHi4Charge',
    'AttackLw3': 'AttackLw3', 'AttackLw4': 'AttackLw4', 'AttackLw4Charge': 'AttackLw4Charge',
    'AttackS3': 'AttackS3',
    'AttackS3Hi': 'AttackS3', 'AttackS3Lw': 'AttackS3',
    'AttackS4': 'AttackS4', 'AttackS4Charge': 'AttackS4Charge',
    'DownAttackU': 'DownAttackU', 'DownAttackD': 'DownAttackD',
    # aerials
    'AttackAirN': 'AttackAirN', 'AttackAirB': 'AttackAirB', 'AttackAirF': 'AttackAirF',
    'AttackAirHi': 'AttackAirHi', 'AttackAirLw': 'AttackAirLw',
    # The rapid-fire chain. G&W's Attack11 sets ENABLE_100, which hands over to
    # Attack100, so all three have to be G&W's or Pyra's 0.6% magic pokes and her
    # `eflame_attack100` effects keep playing on G&W's body during the rapid.
    # This was missed in 0.3.0 and is the user's "leftover Pyra animations".
    'Attack100': 'Attack100', 'Attack100Sub': 'Attack100Sub', 'Attack100End': 'Attack100End',
    # grabs and throws
    'Catch': 'Catch', 'CatchAttack': 'CatchAttack', 'CatchDash': 'CatchDash',
    'CatchTurn': 'CatchTurn', 'CatchWait': 'CatchWait',
    # CaptureDamageLw is deliberately absent. Pyra's version is a single
    # `slope!(... SLOPE_STATUS_LR)` expression function with no game/effect/sound
    # body, so it cannot put a hitbox or an effect on G&W's body and is harmless
    # left as-is. G&W's nearest counterpart, CaptureWaitHi, calls
    # `methodlua2cpp::L2CFighterAnimcmdExpressionCommon::expression_CaptureWaitHiRumble()`,
    # an internal binding that does not exist in the locked toolchain. Swapping a
    # harmless slope read for an uncompilable call would be a bad trade.
    'ThrowF': 'ThrowF', 'ThrowB': 'ThrowB', 'ThrowHi': 'ThrowHi', 'ThrowLw': 'ThrowLw',
    # up special (Fire), 0.19.0. The statuses are ported in plugin/src/status/special_hi.rs.
    'SpecialHi': 'SpecialHi', 'SpecialAirHi': 'SpecialAirHi',
    'SpecialHiOpen': 'SpecialHiOpen', 'SpecialHiClose': 'SpecialHiClose',
}

GROUPS = {
    'ground': ['Attack11', 'Attack12', 'Attack13', 'AttackDash',
               'AttackHi3', 'AttackHi4', 'AttackHi4Charge',
               'AttackLw3', 'AttackLw4', 'AttackLw4Charge',
               'AttackS3', 'AttackS3Hi', 'AttackS3Lw', 'AttackS4', 'AttackS4Charge',
               'DownAttackU', 'DownAttackD'],
    'aerial': ['AttackAirN', 'AttackAirB', 'AttackAirF', 'AttackAirHi', 'AttackAirLw'],
    'rapid': ['Attack100', 'Attack100Sub', 'Attack100End'],
    'grab': ['Catch', 'CatchAttack', 'CatchDash', 'CatchTurn', 'CatchWait',
             'ThrowF', 'ThrowB', 'ThrowHi', 'ThrowLw'],
    'special': ['SpecialHi', 'SpecialAirHi', 'SpecialHiOpen', 'SpecialHiClose'],
}

# R29
FILL_EMPTY = {'special'}
# R30: group -> [(article, donor folder, donor scripts)]
WEAPON_GROUPS = {
    'special': [('rescue', 'gamewatch_rescue', ['SpecialHi', 'SpecialAirHi']),
                ('parachute', 'gamewatch_parachute',
                 ['SpecialHi', 'SpecialAirHi', 'SpecialHiOpen', 'SpecialHiClose'])],
}
# R28
NOTIFY_KEEP = {'0x2127e37c07'}
# R27
RE_UPB_FLAG = re.compile(
    r'WorkModule::on_flag\(agent\.module_accessor, \*FIGHTER_GAMEWATCH_STATUS_SPECIAL_HI_FLAG_'
    r'(DECIDE_DIRECTION|LANDING_ENABLE|PARACHUTE_OPEN)\);')

CATEGORIES = ('game', 'effect', 'sound', 'expression')
RE_FN = re.compile(r'unsafe extern "C" fn (\w+)\(agent: &mut L2CAgentBase\) \{')
RE_LINE = re.compile(r'notify_event_msc_cmd!.*\n', re.M)
RE_ARTICLE = re.compile(r'^\s*ArticleModule::.*\n', re.M)
# R6: a G&W work-index write. Matched on the constant, not the call, because the
# call can be WorkModule::set_int, set_float, on_flag, off_flag or clear_all.
RE_WORK = re.compile(r'^\s*.*(?:FIGHTER_GAMEWATCH_INSTANCE_WORK_ID_|WEAPON_GAMEWATCH_).*\n', re.M)
RE_EMPTY_BLOCK = re.compile(r'[ \t]*if macros::is_excute\(agent\) \{\s*\}\n', re.M)
RE_ATTACH_VIS = re.compile(
    r'ItemModule::set_attach_item_visibility\(agent\.module_accessor, (true|false)\);')
RE_DEFAULT_INT64 = re.compile(
    r'VisibilityModule::set_default_int64\(agent\.module_accessor, Hash40::new\("([^"]+)"\)\)')
RE_AREA_WIND = re.compile(r'^(\s*)AREA_WIND_2ND_arg10\(', re.M)
RE_IS_FLAG = re.compile(
    r'[ \t]*WorkModule::is_flag\((agent\.module_accessor, \*[A-Z0-9_]+)\);\n'
    r'[ \t]*if\(methodlib::L2CValue::operator==\(lib::L2CValueconst&\)const\(false, true\)\)\{\n')
# R12: any statement naming a Pyra or Mythra effect handle.
RE_OWN_EFFECT = re.compile(r'^\s*.*Hash40::new\("(eflame|elght)_[a-z0-9_]+"\).*\n', re.M)
RE_WAIT_LOOP_SYNC_MOT = re.compile(r'^[ \t]*wait_loop_sync_mot\(\);[ \t]*\n', re.M)
RE_COMMON_CALL = re.compile(
    r'methodlua2cpp::(L2CFighterAnimcmd(?:Game|Effect|Sound|Expression)Common)::(\w+)\(\)(?:\(([^)]*)\))?')
RE_FALSE_STATE = re.compile(r'\b(frame|wait)\(false, (\d+)\)')
RE_WAIT_LOOP_CLEAR = re.compile(r'^([ \t]*)wait_loop_clear\(\);', re.M)
RE_THROW_ITEM_ARG3 = re.compile(r'^([ \t]*)THROW_ITEM_arg3\(', re.M)
RE_COND = re.compile(
    r'^([ \t]*)((?:WorkModule|macros)::\w+\(agent[^;\n]*\));\n'
    r'[ \t]*if\(methodlib::L2CValue::operator==\(lib::L2CValueconst&\)const\(false, (true|false)\)\)\{\n',
    re.M)
COMPAT_MACROS = ('THROW_ITEM_OFFSET', 'SHOOT_ITEM_BULLET_CHARGE', 'SHOOT_ITEM_BULLET',
                 'IS_HAVE_ITEM_KIND', 'DOWN_EFFECT', 'SET_RATE_ARTICLE_V')
RE_COMPAT = re.compile(r'\bmacros::(' + '|'.join(COMPAT_MACROS) + r')\(')
RE_GW_ARTICLE_IF = re.compile(
    r'^([ \t]*)if [^\n{]*FIGHTER_GAMEWATCH_GENERATE_ARTICLE_[A-Z_0-9]+[^\n{]*\{$', re.M)
RE_GW_ARTICLE_LINE = re.compile(r'^[^\n]*FIGHTER_GAMEWATCH_GENERATE_ARTICLE_[A-Z_0-9]+[^\n]*\n', re.M)
RE_SOUND = re.compile(r'Hash40::new\("(se_[a-z0-9_]+)"\)')

# R26: G&W's `breath`, the up-air projectile, registered on eflame as a second
# clone (plugin/src/article.rs). The donor constant is replaced before R1 runs,
# for the same reason R23's is: R1 drops any `ArticleModule::` line still
# naming a G&W article, so the id has to stop naming one first.
RE_BREATH = re.compile(r'\*FIGHTER_GAMEWATCH_GENERATE_ARTICLE_BREATH')
# `generate_article` for the breath, matched alone - unlike normal_weapon this
# article has no `change_motion` next to it, because the projectile's motion
# comes from its own init.
RE_BREATH_SPAWN = re.compile(
    r'^([ \t]*)ArticleModule::generate_article\(agent\.module_accessor, '
    r'\*FIGHTER_GAMEWATCH_GENERATE_ARTICLE_BREATH, false, -1\);\n', re.M)
RE_BREATH_SHOOT = re.compile(
    r'^([ \t]*)ArticleModule::shoot\(agent\.module_accessor, '
    r'\*FIGHTER_GAMEWATCH_GENERATE_ARTICLE_BREATH, '
    r'\*ARTICLE_OPE_TARGET_ALL, false\);\n', re.M)

# R23: G&W's `normal_weapon`, which is the one article that can be spawned now.
#
# The article is registered on eflame at boot by this mod's own plugin
# (plugin/src/article.rs, smashline clone_weapon). Moves pass eflame's LOCAL article
# index, crate::article::normal_weapon(), not G&W's global weapon kind 125.
#
# R1, R6 and R21 dropped these lines because the article could not exist. That
# was right then and is wrong now, so they are restored - for this article only.
# Every other G&W article (bomb, breath, rescue, parachute, panel, oil) is still
# dropped by R1/R6/R21, because those belong to the specials and are not
# registered. That is why R23 runs FIRST: by the time R1 sees the body these lines
# no longer name a G&W constant, so they survive.
#
# The kind work-int becomes plugin-owned per-entry storage rather than G&W's raw
# index 0x100000BD, which means nothing on an eflame agent. It has no reader yet,
# because the article's own code is the thing still to be ported; see
# plugin/src/article.rs.
RE_NW_KIND = re.compile(
    r'^([ \t]*)WorkModule::set_int\(agent\.module_accessor, '
    r'\*WEAPON_GAMEWATCH_NORMAL_WEAPON_KIND_([A-Z_0-9]+), '
    r'\*FIGHTER_GAMEWATCH_INSTANCE_WORK_ID_INT_NORMAL_WEAPON_KIND\);$', re.M)
RE_NW_EXIST = re.compile(
    r'if macros::IS_EXIST_ARTICLE\(agent, \*FIGHTER_GAMEWATCH_GENERATE_ARTICLE_NORMAL_WEAPON\) \{')
# `generate_article` is always immediately followed by the `change_motion` that
# names the clip, so the pair is matched together: the diagnostic needs the motion
# name, and a lone generate_article line does not carry it.
RE_NW_SPAWN = re.compile(
    r'^([ \t]*)ArticleModule::generate_article\([^;]*\);\n'
    r'([ \t]*)ArticleModule::change_motion\([^;]*\);\n', re.M)
RE_MOTION_NAME = re.compile(r'Hash40::new\("([a-z0-9_]+)"\)')

# The five props `normal_weapon` can show, by G&W's own name for each. The donor
# dumps print these symbolically as `WEAPON_GAMEWATCH_NORMAL_WEAPON_KIND_*`, so
# the names are authoritative and the values are not - see plugin/src/article.rs.
ARTICLE_KINDS = ('SPRAY', 'CHAIR', 'MANHOLE', 'TROPICALFISH', 'TURTLE')

# R25: see the RULES docstring.
RE_RATE_ARTICLE = re.compile(
    r'^([ \t]*)get_value_float\((\*[A-Z_0-9]+), \*SO_VAR_FLOAT_MOTION_RATE_TOTAL\);\n'
    r'[ \t]*macros::SET_RATE_ARTICLE_V\(agent, 256\);\n', re.M)

# R24: `ArticleModule::remove` takes a third argument in the locked skyline-smash
# (315e4e8) that the dump does not print. Same class of mismatch as R4's
# `set_int64` u64: the game function has always taken it and the dump's signature
# is incomplete. G&W's own `remove_exist` calls name `ARTICLE_OPE_TARGET_ALL`
# explicitly, so ALL is what his `remove` means too - it is the donor saying
# "every instance of this article", not "the first one".
# The same rule wraps the target of `shoot`, which the dump prints as a bare
# `*ARTICLE_OPE_TARGET_ALL` where the binding takes `ArticleOperationTarget`.
# That is the one compile error R26 alone did not fix: 0.12.0's first build
# failed with E0308 on `attackairhi`'s `shoot`, because the argument is present
# and correct and merely untyped. `remove_exist` needs nothing - the dump
# already prints it wrapped.
RE_REMOVE_NO_TARGET = re.compile(
    r'(ArticleModule::remove\(agent\.module_accessor, [A-Za-z0-9_:]+(?:\(\))?)\);')
# `shoot`'s target is present but the dump prints it as a raw i32 constant.
RE_SHOOT_TARGET = re.compile(
    r'(ArticleModule::shoot\(agent\.module_accessor, [A-Za-z0-9_:]+(?:\(\))?, )'
    r'\*ARTICLE_OPE_TARGET_ALL(, false\))')



def strip_body(body: str, drops: list[str]) -> str:
    """Apply R1-R4 to one function body."""
    def r27(m):
        drops.append(f'R27 up-B flag: {m.group(1)} -> plugin-owned storage')
        return (f'crate::status::special_hi::on_flag(agent.module_accessor, '
                f'crate::status::special_hi::FLAG_{m.group(1)});')
    body = RE_UPB_FLAG.sub(r27, body)

    # R25 before R23, so it still sees the donor's article constant.
    def r25(m):
        drops.append('R25 SET_RATE_ARTICLE_V(article, get_value_float(MOTION_RATE_TOTAL)) restored from the binary')
        return (f'{m.group(1)}crate::acmd::compat::SET_RATE_ARTICLE_V(agent, {m.group(2)}, '
                f'sv_animcmd::get_value_float(agent.lua_state_agent, *SO_VAR_FLOAT_MOTION_RATE_TOTAL));\n')
    body = RE_RATE_ARTICLE.sub(r25, body)

    # R26: the breath spawn and shoot, before R1 drops them and before the id
    # rewrite below turns the constant into the local index.
    #
    # Only spawn when the audited native parameter bridge is installed.
    def r26_spawn(m):
        drops.append('R26 spawn: version-checked breath parameter bridge')
        return (f'{m.group(1)}if crate::breath::ready() {{\n'
                f'{m.group(1)}    crate::breath::generate(agent.module_accessor);\n'
                f'{m.group(1)}    crate::article::note_breath(agent, "spawned");\n'
                f'{m.group(1)}}}\n')
    body = RE_BREATH_SPAWN.sub(r26_spawn, body)

    def r26_shoot(m):
        drops.append('R26 shoot: version-checked breath parameter bridge')
        return (f'{m.group(1)}if crate::breath::ready() {{\n'
                f'{m.group(1)}    ArticleModule::shoot(agent.module_accessor, '
                f'crate::article::breath(), *ARTICLE_OPE_TARGET_ALL, false);\n'
                f'{m.group(1)}    crate::article::note_breath(agent, "shot");\n'
                f'{m.group(1)}}}\n')
    body = RE_BREATH_SHOOT.sub(r26_shoot, body)

    if 'FIGHTER_GAMEWATCH_GENERATE_ARTICLE_BREATH' in body:
        drops.append('R26 article: id -> crate::article::breath()')
    body = RE_BREATH.sub('crate::article::breath()', body)

    # R23 first, so the normal_weapon lines are out of reach of R1/R6/R21 below.
    def r23_kind(m):
        name = m.group(2)
        if name not in ARTICLE_KINDS:
            drops.append(f'R23 kind: {name} is not a known normal_weapon prop, LEFT AS DUMPED')
            return m.group()
        drops.append(f'R23 kind: {name} -> plugin-owned storage, not G&W work index')
        return f'{m.group(1)}crate::article::set_kind(agent, crate::article::KIND_{name});'
    body = RE_NW_KIND.sub(r23_kind, body)

    def r23_spawn(m):
        indent, pair = m.group(1), m.group()
        name = RE_MOTION_NAME.search(pair)
        motion = name.group(1) if name else ''
        drops.append(f'R23 spawn: generate_article + change_motion {motion}')
        # The note is an addition, not donor code: the console test has no other
        # way to tell "the article never spawned" from "it spawned and is somewhere
        # else", and the motion name reads straight against the article's own
        # motion_list.bin. It goes *after* the pair so the log order matches the
        # order the calls actually happen in.
        return f'{pair}{indent}crate::article::note_spawn(agent, "{motion}");\n'
    body = RE_NW_SPAWN.sub(r23_spawn, body)

    def r23_exist(m):
        drops.append('R23 condition: IS_EXIST_ARTICLE(normal_weapon) restored')
        return 'if crate::article::is_exist(agent) {'
    body = RE_NW_EXIST.sub(r23_exist, body)

    # The article id goes last, so the spawn pattern above still sees donor text.
    if 'FIGHTER_GAMEWATCH_GENERATE_ARTICLE_NORMAL_WEAPON' in body:
        drops.append('R23 article: id -> crate::article::normal_weapon()')
    body = body.replace('*FIGHTER_GAMEWATCH_GENERATE_ARTICLE_NORMAL_WEAPON',
                        'crate::article::normal_weapon()')

    # R24: supply the target the locked binding needs and the dump omits.
    def r24_remove(m):
        drops.append('R24 remove: added ARTICLE_OPE_TARGET_ALL (dump omits the argument)')
        return f'{m.group(1)}, ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL));'
    body = RE_REMOVE_NO_TARGET.sub(r24_remove, body)

    def r24_shoot(m):
        drops.append('R24 shoot: wrapped ARTICLE_OPE_TARGET_ALL in ArticleOperationTarget')
        return f'{m.group(1)}ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL){m.group(2)}'
    body = RE_SHOOT_TARGET.sub(r24_shoot, body)

    # R1: article lines. Any ArticleModule line in these scripts is a G&W article
    # call, since eflame's own scripts are never the source here.
    #
    # The exception is a line R23 already rewrote to name the cloned article.
    # RE_ARTICLE matches on `ArticleModule::` alone, not on the id, so without
    # this the restored calls are dropped again on the very next rule and the
    # moves silently do nothing. Anything reaching here still carrying a
    # `FIGHTER_GAMEWATCH_GENERATE_ARTICLE_*` constant is a different article and
    # is dropped as before.
    def kill_article(m):
        line = m.group()
        if 'crate::article::normal_weapon()' in line:
            drops.append('R1: KEPT (R23 restored normal_weapon): ' + line.strip())
            return line
        if 'crate::article::breath()' in line:
            drops.append('R1: KEPT (R26 restored breath): ' + line.strip())
            return line
        drops.append('R1 article: ' + line.strip())
        return ''
    body = RE_ARTICLE.sub(kill_article, body)

    # R6: G&W work-index writes.
    def kill_work(m):
        drops.append('R6 work id: ' + m.group().strip())
        return ''
    body = RE_WORK.sub(kill_work, body)

    # R3: unresolvable raw-hash notify.
    def kill_notify(m):
        if any(f'new_raw({h})' in m.group() for h in NOTIFY_KEEP):
            drops.append('R28 notify KEPT: ' + m.group().strip())
            return m.group()
        drops.append('R3 notify: ' + m.group().strip())
        return ''
    body = RE_LINE.sub(kill_notify, body)

    # R13: sound names. G&W's own names pass through - see the comment above SOUND_MAP.
    def map_sound(m):
        name = m.group(1)
        if name.startswith('se_gamewatch_') or name in SOUND_KEEP:
            return m.group()
        if name in SOUND_MAP:
            drops.append(f'R13 sound: {name} -> {SOUND_MAP[name]}')
            return m.group().replace(name, SOUND_MAP[name])
        drops.append(f'R13 sound: {name} LEFT VERBATIM (not a G&W or common name; '
                     'check it resolves on eflame)')
        return m.group()
    body = RE_SOUND.sub(map_sound, body)

    # R4: the locked revision's set_int64 takes u64.
    body = body.replace(') as i64', ') as u64')

    # R8-R11: signature and conversion-artifact fixes.
    body = RE_ATTACH_VIS.sub(
        r'ItemModule::set_attach_item_visibility(agent.module_accessor, \1, 0);', body)
    body = RE_DEFAULT_INT64.sub(
        r'VisibilityModule::set_default_int64(agent.module_accessor, hash40("\1"))', body)
    body = RE_AREA_WIND.sub(r'\1macros::AREA_WIND_2ND_arg10(agent, ', body)
    body = RE_WAIT_LOOP_SYNC_MOT.sub(
        r'sv_animcmd::wait_loop_sync_mot(agent.lua_state_agent);', body)
    body = RE_IS_FLAG.sub(r'    if WorkModule::is_flag(\1) {\n', body)

    # R21: a G&W article id is an index eflame's table does not have (she has 0-4, G&W
    # 0-8), so asking whether it exists would read past her article table. The article
    # can never exist on eflame, so a condition on it is false; any other statement
    # naming one is dropped (R1 already drops ArticleModule::* calls).
    def gw_article_if(m):
        drops.append('R21 article condition: ' + m.group().strip())
        return f'{m.group(1)}if false {{ // G&W article: absent on eflame'
    body = RE_GW_ARTICLE_IF.sub(gw_article_if, body)
    def gw_article_line(m):
        drops.append('R21 article statement: ' + m.group().strip())
        return ''
    body = RE_GW_ARTICLE_LINE.sub(gw_article_line, body)

    # R15-R20. R20 runs first so R19's call match sees the compat path.
    body = RE_COMPAT.sub(r'crate::acmd::compat::\1(', body)

    def cond(m):
        neg = '!' if m.group(3) == 'false' else ''
        call = m.group(2).replace('macros::IS_HAVE_ITEM_KIND', 'crate::acmd::compat::IS_HAVE_ITEM_KIND')
        return f'{m.group(1)}if {neg}{call} {{\n'
    body = RE_COND.sub(cond, body)
    body = RE_COMMON_CALL.sub(
        lambda m: f'(&mut *(agent as *mut L2CAgentBase as *mut {m.group(1)})).{m.group(2)}({m.group(3) or ""})',
        body)
    body = RE_FALSE_STATE.sub(r'\1(agent.lua_state_agent, \2.0)', body)
    body = RE_WAIT_LOOP_CLEAR.sub(r'\1sv_animcmd::wait_loop_clear(agent.lua_state_agent);', body)
    body = RE_THROW_ITEM_ARG3.sub(r'\1macros::THROW_ITEM_arg3(agent, ', body)

    # R12: Pyra/Mythra own effect names.
    def kill_own_effect(m):
        drops.append('R12 own effect: ' + m.group().strip())
        return ''
    body = RE_OWN_EFFECT.sub(kill_own_effect, body)

    # R7: tidy blocks emptied by a drop.
    body = RE_EMPTY_BLOCK.sub('', body)
    return body


def split_functions(text: str) -> dict[str, str]:
    """Return {function_name: full_text} for each dumped ACMD function."""
    out, starts = {}, [(m.start(), m.group(1)) for m in RE_FN.finditer(text)]
    for i, (pos, name) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(text)
        out[name] = text[pos:end].rstrip() + '\n'
    return out


def gen_group(group: str, statuses: list[str]) -> str:
    drops: list[str] = []
    sources: dict[str, list[str]] = {}
    parts, installs, emitted = [], [], set()
    for pyra in statuses:
        gw = PORT[pyra]
        src = (GW / f'{gw}.txt')
        if not src.is_file():
            raise SystemExit(f'error: missing donor {src}')
        text = src.read_text(encoding='utf-8', errors='replace')
        fns = split_functions(text)
        digest = hashlib.sha256(text.encode()).hexdigest()[:12]
        sources.setdefault(gw, []).append(pyra)

        low = pyra.lower()
        for cat in CATEGORIES:
            want = f'{cat}_{low}'
            donor = f'{cat}_{gw.lower()}'
            if donor not in fns:
                if group in FILL_EMPTY:
                    drops.append(f'R29 empty {want}: donor has no {cat} script')
                    parts.append(f'unsafe extern "C" fn {want}(agent: &mut L2CAgentBase) {{}}\n')
                    emitted.add(want)
                continue
            body = strip_body(fns[donor], drops)
            body = re.sub(r'fn ' + re.escape(donor) + r'\(', f'fn {want}(', body, count=1)
            parts.append(body)
            emitted.add(want)
        installs.append(pyra)

    # Emit the wiring explicitly. A runtime lookup of `game_<status>` by string
    # is not expressible without an idents-concatenation macro, and this keeps the
    # generator dependency-free and the mapping checkable by reading the file.
    lines = ['pub fn install() {',
             '    let mut agent = Agent::new("eflame");',
             '    agent.set_costume(crate::TARGET_COSTUMES.to_vec());']
    for pyra in installs:
        low = pyra.lower()
        for cat in CATEGORIES:
            fn = f'{cat}_{low}'
            if fn in emitted:
                lines.append(f'    agent.{cat}_acmd("{cat}_{low}", {fn}, Priority::Default);')
    lines += ['    agent.install();']
    for article, folder, scripts in WEAPON_GROUPS.get(group, []):
        lines.append(f'    let mut agent = Agent::new("eflame_{article}");')
        for script in scripts:
            text = (GW_ROOT / folder / f'{script}.txt').read_text(encoding='utf-8', errors='replace')
            sources.setdefault(f'{folder}/{script}', []).append(f'eflame_{article}')
            for cat in CATEGORIES:
                donor = f'{cat}_{script.lower()}'
                fns = split_functions(text)
                if donor not in fns:
                    continue
                name = f'{article}_{donor}'
                body = strip_body(fns[donor], drops)
                body = re.sub(r'fn ' + re.escape(donor) + r'\(', f'fn {name}(', body, count=1)
                parts.append(body)
                lines.append(f'    agent.{cat}_acmd("{donor}", {name}, Priority::Default);')
        lines.append('    agent.install();')
    lines += ['}', '']
    uniq = sorted(set(drops))
    notes = ['// GEN-NOTES: {} donor script(s) -> {} eflame statuses'.format(
        len(sources), len(installs))]
    for line in uniq:
        notes.append(f'//   {line}')
    # The header is built last so it also lists the drops made in the weapon scripts.
    header = HEADER.format(drops='\n'.join(notes))
    return header + '\n' + '\n'.join(parts) + '\n'.join(lines), sources


def main() -> int:
    check = '--check' in sys.argv
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for group, statuses in GROUPS.items():
        code, sources = gen_group(group, statuses)
        path = OUT_DIR / f'{group}.rs'
        digest = hashlib.sha256(code.encode()).hexdigest()
        manifest[group] = {'file': path.name, 'sha256': digest, 'statuses': statuses,
                           'donors': {k: v for k, v in sorted(sources.items())}}
        if check:
            if not path.is_file():
                print(f'  {path.name}: MISSING')
                return 1
            if path.read_text(encoding='utf-8') != code:
                print(f'  {path.name}: STALE (differs from generator output)')
                return 1
            print(f'  {path.name}: up to date')
        else:
            path.write_text(code, encoding='utf-8')
            print(f'  wrote {path.relative_to(ROOT)}  {len(statuses)} statuses, '
                  f'{len(code.splitlines())} lines')
    man = Path(__file__).resolve().parents[1] / 'generated-manifest.json'
    man.write_text(json.dumps(manifest, indent=1) + '\n', encoding='utf-8')
    if not check:
        print(f'wrote {man.relative_to(ROOT)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
