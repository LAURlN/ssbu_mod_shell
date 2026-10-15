//! Hero Spin -- Mii Swordfighter's up-B -- on Mythra's c06/c07 slot (`elight`).
//!
//! Spec: references/miiswordsman_special_hi/PLAN.md, sections 2-14 plus
//! "Inputs pinned 2026-09-18". This module implements only the plugin half of
//! that plan; the five retargeted clips and the motion-list patches (loop bit on
//! `special_air_hi1`, cancel frame 45 on `special_air_hi_end`) were already
//! deployed and are not touched here.
//!
//! # Why this shape, and not the 2026-09-15 one
//!
//! `PLAN.md` section 6: the previous attempt "left native Mythra transitions and
//! the attempted Mii-style scripts active together", because it layered donor
//! status callbacks on top of the recipient's still-running native up-B flow.
//!
//! The fix is copied from the working precedent in this repository, Monkey Flip
//! (`src/monkey_flip_status.rs`), rather than invented: the entry is diverted in
//! the **`Pre` callback of the shared `FIGHTER_STATUS_KIND_SPECIAL_HI`** with
//! `StatusModule::set_status_kind_interrupt`, and the whole phase chain then runs
//! in statuses this plugin authors. The recipient's native `SPECIAL_HI`
//! `main`/`main_loop` never runs for c06/c07 (its `main_loop` is where the native
//! `sub_change_motion_by_situation` and the native
//! `MotionModule::is_end() -> SPECIAL_HI_JUMP` transition live --
//! `recipient_status/SpecialHi__main_loop.c:24-41`), so there is exactly one
//! authority for the flow. That native entry/jump/attack chain is also why an
//! ACMD-only layering cannot work for this move.
//!
//! # Recipient-authored statuses
//!
//! `PLAN.md` section 11: elight's kinds end at `FIGHTER_ELIGHT_STATUS_KIND_NUM`
//! (`FIGHTER_ELIGHT_STATUS_KIND_FINAL_SCENE04 = 0x1F0`, `NUM = 0x1F1`), and
//! elight has no loop and no end status for up-B. New kinds therefore start at
//! `0x1F1`, the same allocation style the G&W Monkey Flip port used above its
//! own fighter's maximum.
//!
//! # The donor order (PLAN.md section 8.6), reproduced, not re-invented
//!
//! ```text
//! entry:  motion end            -> JUMP
//! jump:   air-cliff check, then motion end -> LOOP
//!         air-cliff check, then grounded past frame 1 -> END
//! loop:   air-cliff check, then grounded -> END   (and it never tests is_end:
//!         the donor's SpecialHi1Loop__main_loop.c:16-33 has no is_end call at all)
//! end:    cancel path, motion end + grounded -> FIGHTER_STATUS_KIND_WAIT
//!         airborne -> FIGHTER_STATUS_KIND_FALL_SPECIAL
//! ```
//!
//! Every donor `main_loop` begins with `sub_transition_group_check_air_cliff()`,
//! and the loop/jump check it **before** anything else, so this port does too --
//! including in the entry, where the donor sets
//! `GROUND_CLIFF_CHECK_KIND_ON_DROP_BOTH_SIDES`.
//!
//! # What is deliberately not ported
//!
//! `PLAN.md` section 10 decides every Mii-only item one row at a time. Dropped
//! here, with the reason recorded there:
//!
//! * `FIGHTER_MIISWORDSMAN_INSTANCE_WORK_ID_FLAG_MOT_FRAME_INHERIT` and the
//!   `INT_GROUND_MOT` / `INT_AIR_MOT` / MTRANS work ints -- elight has no such
//!   instance work ids (`lua_const.rs:4656-4676` is the complete list of 21),
//!   and the recipient's own slots are named directly instead.
//! * `FIGHTER_MIISWORDSMAN_STATUS_WORK_ID_FLAG_ROKET_UNDER_DISABLE_CONTROL_X`
//!   (donor ACMD frame 32) -- **and specifically not**
//!   `FIGHTER_ELIGHT_STATUS_SPECIAL_HI_FLAG_CHECK_DIVE`, which shares the numeric
//!   value `0x2100000E` and means something else (rule 4 of
//!   `move_replacement_guide.md`). Nothing in the pinned donor status set reads
//!   the Mii flag either, so it would be a write with no reader.
//! * Every Mii effect (`miiswordsman_rocket_*`, `EFFECT_*_WORK` on
//!   `..._INT_EFT_ID_SWORD_FLARE`, the sword-trail helper) and every Mii sound.
//!   This module introduces no effect or sound call of any kind.
//! * The `MIISWORDSMAN_ROKET_UNDER_THRUST_*` `init_settings` keep triple, mapped
//!   to the `NONE` triple as PLAN.md section 10 requires.
//! * The four unnamed donor helpers (`FUN_71000207c0`, `..08c0`, `..1060`,
//!   `..12b0`) -- their bodies are not in the tree (PLAN.md section 13 item 2),
//!   so they are not called and not guessed at.
//!
//! # ACMD
//!
//! The five recipient slots are the slots the port's own statuses play, and each
//! gets the donor's game script for that phase, gated on the c06/c07 colour with the
//! vanilla script as the other branch:
//!
//! | recipient slot (`special_*`) | script | donor source |
//! |---|---|---|
//! | `special_hi_start` | `game_specialhistart` | donor `SpecialHi1Start` (game script: none) |
//! | `special_air_hi_start` | `game_specialairhistart` | donor `SpecialAirHi1Start` (game script: none) |
//! | `special_air_hi_jump` | `game_specialairhijump` | donor `SpecialAirHi1` (frames 1/3 windows, 7 cliff, 30 `haver`) |
//! | `special_air_hi1` | `game_specialairhi1` | donor `SpecialAirHi1Loop` (cliff check only) |
//! | `special_air_hi_end` | `game_specialairhiend` | donor `SpecialHi1End` (frame 1 box, frame 4 clear) |
//!
//! The vanilla branch is `original_acmd`, which is the script pointer smashline
//! captured before this module's registration replaced it -- the same API family
//! as the `original_status` call `monkey_flip_status.rs` already uses. It is the
//! game's own script rather than a re-typed copy of the pinned text in
//! `donor_acmd/`, which removes both the transcription risk and the temptation to
//! paste the elight-only flags the vanilla end script happens to set.
//!
//! Replacing the two start slots matters for timing, not just for tidiness:
//! elight's vanilla `game_specialhistart` halves the motion rate over its first
//! nine frames (`donor_acmd/SpecialHiStart.txt:2-19`,
//! `FT_MOTION_RATE(0.5)` then `1.0`), and the vanilla jump/loop scripts do the
//! same (`SpecialAirHiJump.txt:52-55`, `SpecialAirHi1.txt:12-15`). The donor clips
//! are authored at rate 1.0, so those rate changes would stretch the ported
//! motion and break the motion-end timings the phase chain depends on.
//!
//! On the donor's `ATTACK` boxes, the optional-triple arguments were checked
//! against the macro rather than assumed: `smash_script::macros::ATTACK`
//! (WuBoytH/smash-script @ fdc6144, `src/macros.rs:54-68`, the revision
//! `Cargo.lock` pins) always pushes twelve values, then pushes `x2`/`y2`/`z2` --
//! a real value when the argument is `Some(..)`, an empty `L2CValue` when it is
//! `None` -- then continues with the remaining arguments. So `None, None, None`
//! is the API's own representation of "no second point" and is what the donor's
//! `haver` boxes pass, while the frames-1/3 boxes pass the donor's
//! `Some(0.0), Some(4.0), Some(6.0)` triples verbatim.
use smash::{
    app::{lua_bind::*, sv_animcmd::*, *},
    hash40,
    lib::{lua_const::*, L2CValue},
    lua2cpp::*,
    phx::*,
};
use smash_script::*;
use smashline::*;
use super::hero_spin_params;
use super::is_target_costume;

// Recipient-authored status kinds. elight's own kinds end at 0x1F0 with
// NUM = 0x1F1 (PLAN.md section 11); these start exactly there.
const ENTRY: i32 = 0x1F1;
const JUMP: i32 = 0x1F2;
const LOOP: i32 = 0x1F3;
const END: i32 = 0x1F4;

// Per-entry state. Keyed by entry id and owned by the battle object id, exactly
// as monkey_flip_status.rs does it, so a second fighter on the stage cannot
// corrupt this one's reading.
#[derive(Copy, Clone)]
struct SpinState {
    owner: u32,
    // The phase-entry line is printed once per status entry, not per frame.
    phase_logged: bool,
}
const EMPTY: SpinState = SpinState {
    owner: u32::MAX,
    phase_logged: false,
};
static mut STATES: [SpinState; 8] = [EMPTY; 8];

unsafe fn state(boma: *mut BattleObjectModuleAccessor) -> Option<&'static mut SpinState> {
    let id = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
    if id < 0 || id >= 8 {
        return None;
    }
    let data = &mut STATES[id as usize];
    if data.owner != (*boma).battle_object_id {
        *data = EMPTY;
        data.owner = (*boma).battle_object_id;
    }
    Some(data)
}

// The context this module runs in. Every new status is only ever entered from
// this module's own chain, and the chain is only ever entered through the
// colour-gated interrupt below, so `c06/c07` enforcement does not have to be
// repeated per status.
unsafe fn is_target(boma: *mut BattleObjectModuleAccessor) -> bool {
    is_target_costume(WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR))
}

// The recipient slot names, selected explicitly. The donor selects its motion
// through MTRANS work ints that elight does not have (PLAN.md section 10), so the
// recipient motion is named directly -- the same choice monkey_flip_status.rs
// makes for its phases.
unsafe fn motion(fighter: &mut L2CFighterCommon, name: &str) {
    MotionModule::change_motion(
        fighter.module_accessor,
        Hash40::new(name),
        0.0,
        1.0,
        false,
        0.0,
        false,
        false,
    );
    #[cfg(feature = "swap-diagnostics")]
    println!(
        "[MGW-HSPIN] MOTION requested={} hash={:#x} observed_kind={:#x} end={:.2} rate={}",
        name,
        hash40(name),
        MotionModule::motion_kind(fighter.module_accessor),
        MotionModule::end_frame(fighter.module_accessor),
        MotionModule::rate(fighter.module_accessor)
    );
}

// Telemetry, transitions only. Every status change this module issues goes
// through here so a transition cannot be silent.
#[cfg(feature = "swap-diagnostics")]
unsafe fn phase_name(status: i32) -> &'static str {
    match status {
        ENTRY => "entry",
        JUMP => "jump",
        LOOP => "loop",
        END => "end",
        _ => "other",
    }
}

#[cfg(feature = "swap-diagnostics")]
unsafe fn log_phase(fighter: &mut L2CFighterCommon) {
    let boma = fighter.module_accessor;
    let status = StatusModule::status_kind(boma);
    println!(
        "[MGW-HSPIN] PHASE {} status={:#x} motion={:#x} situation={} frame={:.2} end={:.2} is_end={}",
        phase_name(status),
        status,
        MotionModule::motion_kind(boma),
        StatusModule::situation_kind(boma),
        MotionModule::frame(boma),
        MotionModule::end_frame(boma),
        MotionModule::is_end(boma)
    );
}

unsafe fn change(fighter: &mut L2CFighterCommon, status: i32, input: bool, reason: &str) -> L2CValue {
    #[cfg(feature = "swap-diagnostics")]
    println!(
        "[MGW-HSPIN] TRANSITION from={:#x} ({}) to={:#x} ({}) reason={} situation={} frame={:.2}",
        StatusModule::status_kind(fighter.module_accessor),
        phase_name(StatusModule::status_kind(fighter.module_accessor)),
        status,
        phase_name(status),
        reason,
        StatusModule::situation_kind(fighter.module_accessor),
        MotionModule::frame(fighter.module_accessor)
    );
    fighter.change_status(status.into(), input.into());
    1.into()
}

// ---------------------------------------------------------------------------
// Entry: the shared SPECIAL_HI callback, diverted for c06/c07 only.
// ---------------------------------------------------------------------------

// The donor's entry is the shared `FIGHTER_STATUS_KIND_SPECIAL_HI = 0x1DE`
// (PLAN.md section 8.2: there is no `FIGHTER_MIISWORDSMAN_STATUS_KIND_SPECIAL_HI`
// in the bindings), which is the kind elight's own up-B entry uses as well. So
// the divert is installed on that shared kind and the other colours are handed
// straight back to the vanilla callback -- the non-target branch rule of
// `move_replacement_guide.md` section 1.
pub unsafe extern "C" fn entry_pre(fighter: &mut L2CFighterCommon) -> L2CValue {
    if !is_target(fighter.module_accessor) {
        return original_status(Pre, fighter, *FIGHTER_STATUS_KIND_SPECIAL_HI)(fighter);
    }
    #[cfg(feature = "swap-diagnostics")]
    println!(
        "[MGW-HSPIN] ENTRY divert status={:#x} -> {:#x} colour={} situation={}",
        StatusModule::status_kind(fighter.module_accessor),
        ENTRY,
        WorkModule::get_int(fighter.module_accessor, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR),
        StatusModule::situation_kind(fighter.module_accessor)
    );
    StatusModule::set_status_kind_interrupt(fighter.module_accessor, ENTRY);
    1.into()
}

// `pre` for the four authored phases. Settings are the donor's, from
// PLAN.md section 8, with the two recorded substitutions: the elight-authored
// keep triple (PLAN.md section 10, no `FIGHTER_STATUS_WORK_KEEP_FLAG_ELIGHT_*`
// exists) and the log mask of the shared SPECIAL_HI attack kind.
pub unsafe extern "C" fn pre(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let status = StatusModule::status_kind(boma);
    // (situation, kinetic, ground correct, cliff check, tail)
    let (situation, kinetic, ground, cliff, tail) = match status {
        // SpecialHi__pre.c:32-52
        ENTRY => (
            *SITUATION_KIND_NONE,
            *FIGHTER_KINETIC_TYPE_UNIQ,
            *GROUND_CORRECT_KIND_KEEP,
            *GROUND_CLIFF_CHECK_KIND_ON_DROP_BOTH_SIDES,
            0,
        ),
        // SpecialHi1Jump__pre.c:33-44
        JUMP => (
            *SITUATION_KIND_AIR,
            *FIGHTER_KINETIC_TYPE_UNIQ,
            *GROUND_CORRECT_KIND_AIR,
            *GROUND_CLIFF_CHECK_KIND_ON_DROP,
            0,
        ),
        // SpecialHi1Loop__pre.c:33-89 -- same as the jump's, with
        // _FS_SUCCEEDS_KEEP_ATTACK as the init_settings tail.
        LOOP => (
            *SITUATION_KIND_AIR,
            *FIGHTER_KINETIC_TYPE_UNIQ,
            *GROUND_CORRECT_KIND_AIR,
            *GROUND_CLIFF_CHECK_KIND_ON_DROP,
            *FS_SUCCEEDS_KEEP_ATTACK,
        ),
        // SpecialHi1End__pre.c:33-44 -- note the forced GROUND situation and
        // GROUND_STOP kinetic: the end phase is grounded by construction.
        _ => (
            *SITUATION_KIND_GROUND,
            *FIGHTER_KINETIC_TYPE_GROUND_STOP,
            *GROUND_CORRECT_KIND_GROUND,
            *GROUND_CLIFF_CHECK_KIND_NONE,
            0,
        ),
    };
    StatusModule::init_settings(
        boma,
        SituationKind(situation),
        kinetic,
        ground as u32,
        GroundCliffCheckKind(cliff),
        true,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_NONE_FLAG,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_NONE_INT,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_NONE_FLOAT,
        tail,
    );
    FighterStatusModuleImpl::set_fighter_status_data(
        boma,
        false,
        *FIGHTER_TREADED_KIND_NO_REAC,
        false,
        false,
        false,
        (*FIGHTER_LOG_MASK_FLAG_ATTACK_KIND_SPECIAL_HI
            | *FIGHTER_LOG_MASK_FLAG_ACTION_CATEGORY_ATTACK
            | if status == ENTRY {
                *FIGHTER_LOG_MASK_FLAG_ACTION_TRIGGER_ON
            } else {
                0
            }) as u64,
        if status == ENTRY {
            *FIGHTER_STATUS_ATTR_START_TURN as u32
        } else {
            0
        },
        *FIGHTER_POWER_UP_ATTACK_BIT_SPECIAL_HI as u32,
        0,
    );
    if let Some(data) = state(boma) {
        data.phase_logged = false;
    }
    0.into()
}

// ---------------------------------------------------------------------------
// main: the phase's motion, on the first frame of the status only.
// ---------------------------------------------------------------------------

pub unsafe extern "C" fn main(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let status = StatusModule::status_kind(boma);
    let first = state(boma).map(|data| !data.phase_logged).unwrap_or(false);
    if first {
        match status {
            ENTRY => {
                // The donor's entry keeps a ground start motion and an air start
                // motion and lets MTRANS pick (PLAN.md section 4). The recipient
                // names its own two slots instead (PLAN.md section 2).
                let ground = StatusModule::situation_kind(boma) == *SITUATION_KIND_GROUND;
                // SpecialHi__main.c:20-32: the one required parameter, written to
                // the reserve kinetic motion speed multiplier. This is the spin's
                // rise speed, and it is the only donor value the chain needs
                // besides the landing frame written in `end` below.
                WorkModule::set_float(
                    boma,
                    hero_spin_params::value("hi1_jump_speed_mul"),
                    *FIGHTER_STATUS_WORK_ID_FLOAT_RESERVE_KINETIC_MOTION_SPEED_MUL,
                );
                motion(
                    fighter,
                    if ground {
                        "special_hi_start"
                    } else {
                        "special_air_hi_start"
                    },
                );
            }
            // SpecialHi1Jump__main.c:19-31 / SpecialHi1Loop__main.c:19-31 /
            // SpecialHi1End__main.c:19-31 set the donor's motion work ints, which
            // are dropped; the recipient slot for each phase is named here.
            JUMP => motion(fighter, "special_air_hi_jump"),
            LOOP => motion(fighter, "special_air_hi1"),
            END => motion(fighter, "special_air_hi_end"),
            _ => {}
        }
        #[cfg(feature = "swap-diagnostics")]
        log_phase(fighter);
        if let Some(data) = state(boma) {
            data.phase_logged = true;
        }
    }
    fighter.sub_shift_status_main(L2CValue::Ptr(main_loop as *const () as _))
}

// ---------------------------------------------------------------------------
// main_loop: the donor's conditions, in the donor's order.
// ---------------------------------------------------------------------------

pub unsafe extern "C" fn main_loop(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let status = StatusModule::status_kind(boma);
    let ground = StatusModule::situation_kind(boma) == *SITUATION_KIND_GROUND;
    // Every donor main_loop begins with this, and the jump's and the loop's do it
    // before anything else (SpecialHi1Jump__main_loop.c:18,
    // SpecialHi1Loop__main_loop.c:16). The end phase is the exception, and that
    // is the donor's own: its `pre` asks for GROUND_CLIFF_CHECK_KIND_NONE
    // (SpecialHi1End__pre.c:33-44) and its main_loop starts at the cancel path
    // instead (SpecialHi1End__main_loop.c:20).
    if status != END && fighter.sub_transition_group_check_air_cliff().get_bool() {
        #[cfg(feature = "swap-diagnostics")]
        println!(
            "[MGW-HSPIN] TRANSITION from={:#x} ({}) to=engine reason=air-cliff group check returned true",
            status,
            phase_name(status)
        );
        return 1.into();
    }
    match status {
        ENTRY => {
            // SpecialHi__main_loop.c:22 and :75-77 -- motion end to the jump.
            if MotionModule::is_end(boma) {
                return change(fighter, JUMP, false, "entry motion end");
            }
        }
        JUMP => {
            // SpecialHi1Jump__main_loop.c:22-25, then :27-41. The donor's order:
            // motion end first, and only then the grounded test.
            if MotionModule::is_end(boma) {
                return change(fighter, LOOP, false, "jump motion end");
            }
            // Which way the donor's unnamed
            // `operator_(aLStack64 /*1.0*/, aLStack80 /*frame*/)` comparison
            // reads is listed as an open question in PLAN.md section 14; the two
            // readings differ only at frames 0 and 1, and `frame > 1.0` is the one
            // that matches the move ("do not end on the launch frame itself",
            // PLAN.md section 8.3).
            if ground && MotionModule::frame(boma) > 1.0 {
                return change(fighter, END, false, "jump grounded after launch frame");
            }
        }
        LOOP => {
            // SpecialHi1Loop__main_loop.c:16-33. The donor loop never calls
            // MotionModule::is_end; its only script-side exit is grounding. The
            // clip it plays is declared looping in the recipient's motion list,
            // which is what keeps this from holding its last frame.
            if ground {
                return change(fighter, END, false, "loop grounded");
            }
        }
        END => {
            // SpecialHi1End__main_loop.c:20-84.
            if CancelModule::is_enable_cancel(boma) {
                if fighter.sub_wait_ground_check_common(false.into()).get_bool() {
                    if !fighter.sub_air_check_fall_common().get_bool() {
                        return 1.into();
                    }
                }
            }
            if MotionModule::is_end(boma) && ground {
                return change(
                    fighter,
                    *FIGHTER_STATUS_KIND_WAIT,
                    false,
                    "end motion end while grounded",
                );
            }
            if !ground {
                return change(
                    fighter,
                    *FIGHTER_STATUS_KIND_FALL_SPECIAL,
                    false,
                    "end airborne",
                );
            }
        }
        _ => {}
    }
    0.into()
}

// ---------------------------------------------------------------------------
// end
// ---------------------------------------------------------------------------

pub unsafe extern "C" fn end(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let status = StatusModule::status_kind(boma);
    // The donor's game scripts clear their own boxes on their own frames
    // (frame 6, 45 and 4). This is the repo's standing status-exit cleanup
    // (monkey_flip_status.rs `end`), so a box cannot outlive the status that
    // owns it if the chain leaves early.
    AttackModule::clear_all(boma);
    if status == END {
        // SpecialHi1End__end.c:19-31 -- the only place the landing length is set,
        // written on the way out so the following landing animation reads it.
        // Second required parameter of the move, and the second of the only two
        // keys this module asks hero_spin_params for.
        WorkModule::set_float(
            boma,
            hero_spin_params::value("hi1_land_weak_frame"),
            *FIGHTER_INSTANCE_WORK_ID_FLOAT_LANDING_FRAME,
        );
    }
    0.into()
}

// ---------------------------------------------------------------------------
// ACMD: the donor's game scripts on the five recipient slots, c06/c07 only.
// ---------------------------------------------------------------------------

// The vanilla branch. `original_acmd` is the script pointer smashline captured
// for this agent before this module's registration replaced it, so this is the
// recipient's own script and not a copy. Other Mythra colours therefore keep
// their native up-B scripts exactly.
unsafe fn vanilla(agent: &mut L2CAgentBase, name: &str) {
    original_acmd(agent, Hash40::new(name))(agent);
}

unsafe fn acmd_is_target(agent: &mut L2CAgentBase) -> bool {
    is_target(agent.module_accessor)
}

// Entry, ground start. The donor's own start phase has no game script at all
// (references/miiswordsman_special_hi/acmd/SpecialHi1Start.txt defines only
// `effect_specialhi1start` and `expression_specialhi1start`), so for c06/c07 this
// contributes nothing -- and that is what removes the vanilla rate change
// (donor_acmd/SpecialHiStart.txt:2-19) that would otherwise stretch the ported
// start clip.
pub unsafe extern "C" fn elight_game_specialhistart(agent: &mut L2CAgentBase) {
    if !acmd_is_target(agent) {
        vanilla(agent, "game_specialhistart");
        return;
    }
}

// Entry, air start. Same reasoning as the ground start.
pub unsafe extern "C" fn elight_game_specialairhistart(agent: &mut L2CAgentBase) {
    if !acmd_is_target(agent) {
        vanilla(agent, "game_specialairhistart");
        return;
    }
}

// Jump phase: the donor's `game_specialairhi1` body
// (references/miiswordsman_special_hi/acmd/SpecialAirHi1.txt:1-38; the ground
// twin `SpecialHi1.txt` is identical for the game script). Two attack windows on
// frames 1 and 3, the cliff-check notify on frame 7, two more boxes on `haver` at
// frame 30 -- and the donor's frame-32 Mii work-flag write is dropped, per
// PLAN.md section 12 / section 10.
pub unsafe extern "C" fn elight_game_specialairhijump(agent: &mut L2CAgentBase) {
    if !acmd_is_target(agent) {
        vanilla(agent, "game_specialairhijump");
        return;
    }
    frame(agent.lua_state_agent, 1.0);
    if macros::is_excute(agent) {
        KineticModule::add_speed(
            agent.module_accessor,
            &Vector3f {
                x: 0.0,
                y: 0.5,
                z: 0.0,
            },
        );
        macros::ATTACK(agent, 0, 0, Hash40::new("top"), 4.0, 92, 100, 96, 0, 4.0, 0.0, 7.0, 6.0, Some(0.0), Some(4.0), Some(6.0), 1.3, 1.0, *ATTACK_SETOFF_KIND_ON, *ATTACK_LR_CHECK_POS, false, 0, 0.0, 0, false, false, false, false, true, *COLLISION_SITUATION_MASK_GA, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_cutup"), *ATTACK_SOUND_LEVEL_M, *COLLISION_SOUND_ATTR_CUTUP, *ATTACK_REGION_SWORD);
        macros::ATTACK(agent, 1, 0, Hash40::new("top"), 4.0, 92, 100, 96, 0, 3.5, 0.0, 7.0, 13.0, Some(0.0), Some(4.0), Some(13.0), 1.3, 1.0, *ATTACK_SETOFF_KIND_ON, *ATTACK_LR_CHECK_POS, false, 0, 0.0, 0, false, false, false, false, true, *COLLISION_SITUATION_MASK_GA, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_cutup"), *ATTACK_SOUND_LEVEL_M, *COLLISION_SOUND_ATTR_CUTUP, *ATTACK_REGION_SWORD);
        AttackModule::set_add_reaction_frame(agent.module_accessor, 0, 4.0, false);
        AttackModule::set_add_reaction_frame(agent.module_accessor, 1, 4.0, false);
    }
    frame(agent.lua_state_agent, 3.0);
    if macros::is_excute(agent) {
        macros::ATTACK(agent, 0, 0, Hash40::new("top"), 4.0, 92, 100, 60, 0, 4.0, 0.0, 7.0, 6.0, Some(0.0), Some(4.0), Some(6.0), 1.3, 1.0, *ATTACK_SETOFF_KIND_ON, *ATTACK_LR_CHECK_POS, false, 0, 0.0, 0, false, false, false, false, true, *COLLISION_SITUATION_MASK_GA, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_cutup"), *ATTACK_SOUND_LEVEL_M, *COLLISION_SOUND_ATTR_CUTUP, *ATTACK_REGION_SWORD);
        macros::ATTACK(agent, 1, 0, Hash40::new("top"), 4.0, 92, 100, 60, 0, 3.5, 0.0, 7.0, 13.0, Some(0.0), Some(4.0), Some(13.0), 1.3, 1.0, *ATTACK_SETOFF_KIND_ON, *ATTACK_LR_CHECK_POS, false, 0, 0.0, 0, false, false, false, false, true, *COLLISION_SITUATION_MASK_GA, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_cutup"), *ATTACK_SOUND_LEVEL_M, *COLLISION_SOUND_ATTR_CUTUP, *ATTACK_REGION_SWORD);
        AttackModule::set_add_reaction_frame(agent.module_accessor, 0, 4.0, false);
        AttackModule::set_add_reaction_frame(agent.module_accessor, 1, 4.0, false);
    }
    frame(agent.lua_state_agent, 6.0);
    if macros::is_excute(agent) {
        AttackModule::clear_all(agent.module_accessor);
    }
    frame(agent.lua_state_agent, 7.0);
    if macros::is_excute(agent) {
        notify_event_msc_cmd!(
            agent,
            Hash40::new_raw(0x2127e37c07),
            *GROUND_CLIFF_CHECK_KIND_ALWAYS_BOTH_SIDES
        );
    }
    frame(agent.lua_state_agent, 30.0);
    if macros::is_excute(agent) {
        macros::ATTACK(agent, 0, 0, Hash40::new("haver"), 3.0, 268, 180, 39, 0, 5.0, 0.0, 16.0, 0.0, None, None, None, 1.0, 0.0, *ATTACK_SETOFF_KIND_ON, *ATTACK_LR_CHECK_POS, false, 0, 0.0, 0, false, false, false, false, true, *COLLISION_SITUATION_MASK_A, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_cutup"), *ATTACK_SOUND_LEVEL_L, *COLLISION_SOUND_ATTR_CUTUP, *ATTACK_REGION_SWORD);
        macros::ATTACK(agent, 1, 0, Hash40::new("haver"), 3.0, 361, 100, 20, 0, 5.0, 0.0, 16.0, 0.0, None, None, None, 1.0, 0.0, *ATTACK_SETOFF_KIND_ON, *ATTACK_LR_CHECK_POS, false, 0, 0.0, 0, false, false, false, false, true, *COLLISION_SITUATION_MASK_G, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_cutup"), *ATTACK_SOUND_LEVEL_L, *COLLISION_SOUND_ATTR_CUTUP, *ATTACK_REGION_SWORD);
    }
    frame(agent.lua_state_agent, 45.0);
    if macros::is_excute(agent) {
        AttackModule::clear_all(agent.module_accessor);
    }
}

// Loop phase: the donor's `game_specialairhi1loop`
// (references/miiswordsman_special_hi/acmd/SpecialAirHi1Loop.txt:1-5) is the
// cliff-check notify and nothing else, on frame 0 -- which is what makes the
// donor's loop status's first instruction (`sub_transition_group_check_air_cliff`)
// meaningful while the loop is running.
pub unsafe extern "C" fn elight_game_specialairhi1(agent: &mut L2CAgentBase) {
    if !acmd_is_target(agent) {
        vanilla(agent, "game_specialairhi1");
        return;
    }
    if macros::is_excute(agent) {
        notify_event_msc_cmd!(
            agent,
            Hash40::new_raw(0x2127e37c07),
            *GROUND_CLIFF_CHECK_KIND_ALWAYS_BOTH_SIDES
        );
    }
}

// End phase: the donor's `game_specialhi1end`
// (references/miiswordsman_special_hi/acmd/SpecialHi1End.txt:1-10; the air twin
// is identical, which is why one recipient end slot serves both).
pub unsafe extern "C" fn elight_game_specialairhiend(agent: &mut L2CAgentBase) {
    if !acmd_is_target(agent) {
        vanilla(agent, "game_specialairhiend");
        return;
    }
    frame(agent.lua_state_agent, 1.0);
    if macros::is_excute(agent) {
        macros::ATTACK(agent, 0, 0, Hash40::new("top"), 8.0, 55, 93, 0, 103, 8.0, 0.0, 6.0, -4.0, Some(0.0), Some(6.0), Some(4.5), 2.1, 1.0, *ATTACK_SETOFF_KIND_OFF, *ATTACK_LR_CHECK_POS, false, 0, 0.0, 0, false, false, false, false, true, *COLLISION_SITUATION_MASK_GA, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_normal"), *ATTACK_SOUND_LEVEL_L, *COLLISION_SOUND_ATTR_KICK, *ATTACK_REGION_SWORD);
    }
    frame(agent.lua_state_agent, 4.0);
    if macros::is_excute(agent) {
        AttackModule::clear_all(agent.module_accessor);
    }
}

pub fn install() {
    #[cfg(feature = "swap-diagnostics")]
    println!(
        "[MGW-HSPIN] build 2026-09-18.k: Hero Spin on elight c06/c07, statuses {:#x}..{:#x} (entry/jump/loop/end), donor ACMD on the five recipient slots, no effects and no sounds",
        ENTRY, END
    );

    // The entry, on the shared kind, colour-gated, with the vanilla callback as
    // the other branch.
    let mut agent = Agent::new("elight");
    agent.status(Pre, *FIGHTER_STATUS_KIND_SPECIAL_HI, entry_pre);
    for kind in ENTRY..=END {
        agent
            .status(Pre, kind, pre)
            .status(Main, kind, main)
            .status(End, kind, end);
    }
    agent.install();

    // The donor's game scripts. Only the game category is registered: the effect,
    // sound and expression scripts stay the recipient's own, and this module calls
    // no effect or sound macro itself.
    Agent::new("elight")
        .game_acmd(
            "game_specialhistart",
            elight_game_specialhistart,
            Priority::Default,
        )
        .game_acmd(
            "game_specialairhistart",
            elight_game_specialairhistart,
            Priority::Default,
        )
        .game_acmd(
            "game_specialairhijump",
            elight_game_specialairhijump,
            Priority::Default,
        )
        .game_acmd(
            "game_specialairhi1",
            elight_game_specialairhi1,
            Priority::Default,
        )
        .game_acmd(
            "game_specialairhiend",
            elight_game_specialairhiend,
            Priority::Default,
        )
        .install();
}
