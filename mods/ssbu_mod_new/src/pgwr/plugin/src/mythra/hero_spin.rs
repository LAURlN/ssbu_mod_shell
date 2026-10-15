//! Hero's Spin on Mythra c06/c07, using Mii Swordfighter's real `Hi3` move.
//!
//! Ported from `mod_files/mythra_gamewatch_swap/src/hero_spin3.rs` (donor build
//! `2026-09-26.g`). The status machine, the frame data, the status ids and the
//! air kinetic are the donor's, unchanged. What is different is the gating and
//! the logging, both recorded below.
//!
//! # Why this is a status machine and not one ACMD override
//!
//! Hero's Spin is a four-phase charge-and-release move: startup, hold, ground
//! spin, aerial spin. Mii Swordfighter runs those as four separate statuses, and
//! the transitions between them are driven by whether SPECIAL_B is still held and
//! by whether the fighter has left the ground. `SPECIAL_HI` is the only status
//! this mod intercepts, in its `Pre`, and immediately routes to the phase that
//! matches the situation. Nothing in the native Elight up-B flow is left to run.
//!
//! That is the same shape the donor uses, and the same shape `status::judge`
//! uses for the side-B replacement, so it is a pattern this crate already has
//! rather than a new mechanism.
//!
//! # Gating
//!
//! Install-time, through `crate::TARGET_COSTUMES`, exactly like every other
//! override in this crate. See `super` for why that makes the donor's
//! `is_target_costume` checks and its hand-copied vanilla `Pre` unnecessary.
//!
//! # Status ids
//!
//! `FIGHTER_ELIGHT_STATUS_KIND_NUM` is `0x1F1`, so the four phases take exactly
//! the first four ids above Mythra's own table. `super` re-checks that number
//! against `lua_const` at load, so a toolchain bump that moves Mythra's table
//! fails at boot instead of silently overwriting a real status.
//!
//! # Logging
//!
//! The donor logs from inside a per-frame `Main` and gates it behind a cargo
//! feature. Per-frame printing is exactly what filled the donor's log during the
//! grenade investigation and cost a crash report, so this port logs on entry and
//! on each phase transition only. Both are bounded by the number of transitions,
//! which is a small constant, and nothing here can run more than a handful of
//! times per use of the move.

use smash::{
    app::{lua_bind::*, sv_animcmd::*, sv_kinetic_energy, *},
    hash40,
    lib::{lua_const::*, L2CValue},
    lua2cpp::*,
    phx::*,
};
use smash_script::*;
use smashline::*;

use super::hero_spin_params::{
    AIR_ACCEL_Y_SCALE, AIR_SPEED_Y_SCALE, MII_HI3_AIR_ACCEL_Y, MII_HI3_AIR_SPEED_Y_STABLE,
};
use super::{
    status_id_for, LOG_HERO_SPIN, STATUS_AIR_SPIN, STATUS_GROUND_SPIN, STATUS_HOLD, STATUS_START,
};

/// Per-entry, so each transition logs once rather than every frame it persists.
///
/// Indexed by battle object id, which the move-replacement guide's rule 8 warns
/// is not a stable handle. It only ever indexes a per-entry slot that is reset
/// in `entry_pre` and never retained across a respawn, which is the same
/// lifetime `status::judge` gives its phase array.
static mut SEEN_ENTER: [bool; 8] = [false; 8];

/// True once the air phase has been entered, so its height is logged once on the
/// way in and once on the way out instead of once per frame.
static mut SEEN_AIR: [bool; 8] = [false; 8];

/// The body's y when the air spin started, reported when the air spin ends.
static mut AIR_START_Y: [f32; 8] = [0.0; 8];

/// The per-entry slot index, or `usize::MAX` when the object id is out of range.
///
/// Returning a sentinel rather than clamping means an out-of-range entry simply
/// never writes or reads any slot, instead of aliasing entry 7's. Same guard
/// shape as `status::judge` and `acmd::gate_trace`.
#[inline]
unsafe fn entry_id(fighter: &L2CFighterCommon) -> usize {
    let id = (*fighter.battle_object).battle_object_id as usize;
    if id < 8 {
        id
    } else {
        usize::MAX
    }
}

/// The shared `Pre` setup for all four phases.
///
/// `ground` and `start_turn` are passed explicitly rather than re-derived inside
/// the function. That is not a style choice: the donor's first build inferred the
/// situation from `StatusModule::status_kind` inside the `Pre`, where it still
/// reports the *outgoing* status. The aerial phase therefore selected
/// `GROUND_STOP` and landed at frame 0 on every attempt, which read as a missing
/// animation when it was a status-setting error. The situation is now an
/// argument chosen by the caller that knows which phase it is entering.
unsafe fn pre_common(fighter: &mut L2CFighterCommon, ground: bool, start_turn: bool) -> L2CValue {
    let boma = fighter.module_accessor;
    StatusModule::init_settings(
        boma,
        SituationKind(if ground {
            *SITUATION_KIND_GROUND
        } else {
            *SITUATION_KIND_AIR
        }),
        if ground {
            *FIGHTER_KINETIC_TYPE_GROUND_STOP
        } else {
            *FIGHTER_KINETIC_TYPE_JUMP_AERIAL
        },
        if ground {
            *GROUND_CORRECT_KIND_GROUND as u32
        } else {
            *GROUND_CORRECT_KIND_AIR as u32
        },
        GroundCliffCheckKind(if ground {
            *GROUND_CLIFF_CHECK_KIND_NONE
        } else {
            *GROUND_CLIFF_CHECK_KIND_ALWAYS_BOTH_SIDES
        }),
        true,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_NONE_FLAG,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_NONE_INT,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_NONE_FLOAT,
        0,
    );
    FighterStatusModuleImpl::set_fighter_status_data(
        boma,
        false,
        *FIGHTER_TREADED_KIND_NO_REAC,
        false,
        false,
        false,
        (*FIGHTER_LOG_MASK_FLAG_ATTACK_KIND_SPECIAL_HI
            | *FIGHTER_LOG_MASK_FLAG_ACTION_CATEGORY_ATTACK)
            as u64,
        if start_turn {
            *FIGHTER_STATUS_ATTR_START_TURN as u32
        } else {
            0
        },
        *FIGHTER_POWER_UP_ATTACK_BIT_SPECIAL_HI as u32,
        0,
    );
    0.into()
}

/// Ground startup. Requests the startup turn.
///
/// Both the native Elight `SpecialHi` `Pre` and Mii's own `SpecialHi` `Pre` set
/// `FIGHTER_STATUS_ATTR_START_TURN`; the donor found that omitting it left the
/// move unable to turn around on directional input, which it recorded as a
/// reversal bug that was really a missing attribute.
unsafe extern "C" fn pre_start(fighter: &mut L2CFighterCommon) -> L2CValue {
    pre_common(fighter, true, true)
}

/// Hold and ground-spin phases. No second startup turn.
unsafe extern "C" fn pre_ground(fighter: &mut L2CFighterCommon) -> L2CValue {
    pre_common(fighter, true, false)
}

/// Aerial entry.
///
/// `start_turn` is decided by *which status interrupted us*, which is the one
/// thing `status_kind` is reliable for inside a `Pre`. A direct aerial use
/// interrupts `SPECIAL_HI` and should turn; falling out of a ground phase
/// interrupts one of our own ids and must keep the facing the startup already
/// chose, so it must not turn again.
unsafe extern "C" fn pre_air(fighter: &mut L2CFighterCommon) -> L2CValue {
    let start_turn =
        StatusModule::status_kind(fighter.module_accessor) == *FIGHTER_STATUS_KIND_SPECIAL_HI;
    pre_common(fighter, false, start_turn)
}

/// Takes up-B away from Mythra and routes it into the right phase.
///
/// Registered on the stock `SPECIAL_HI` id, so a Mythra in c00-c05 keeps the
/// game's own `Pre` and never reaches this function.
unsafe extern "C" fn entry_pre(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let id = entry_id(fighter);
    if id != usize::MAX {
        SEEN_ENTER[id] = false;
        SEEN_AIR[id] = false;
    }

    let ground = StatusModule::situation_kind(boma) == *SITUATION_KIND_GROUND;
    let next = if ground { STATUS_START } else { STATUS_AIR_SPIN };

    if id == usize::MAX || !SEEN_ENTER[id] {
        if id != usize::MAX {
            SEEN_ENTER[id] = true;
        }
        crate::diagnostic!(println!(
            "{} entry id={} colour={} ground={} -> status {:#x}",
            LOG_HERO_SPIN,
            if id == usize::MAX { 99 } else { id },
            WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR),
            ground,
            next
        ));
    }

    // `set_status_kind_interrupt` rather than `change_status`: the donor's
    // Switch traces show this running before the native `Pre` has finished, and
    // the interrupt form does not queue a second transition behind it.
    StatusModule::set_status_kind_interrupt(boma, next);
    1.into()
}

unsafe fn change(fighter: &mut L2CFighterCommon, next: i32, reason: &str) -> L2CValue {
    let boma = fighter.module_accessor;
    let id = entry_id(fighter);
    crate::diagnostic!(println!(
        "{} transition {:#x} -> {:#x} ({}) frame={:.1} y={:.2}",
        LOG_HERO_SPIN,
        StatusModule::status_kind(boma),
        next,
        reason,
        MotionModule::frame(boma),
        (*PostureModule::pos(boma)).y
    ));
    if id != usize::MAX && SEEN_AIR[id] && next != STATUS_AIR_SPIN {
        crate::diagnostic!(println!(
            "{} air spin y {:.2} -> {:.2} over the phase",
            LOG_HERO_SPIN,
            AIR_START_Y[id],
            (*PostureModule::pos(boma)).y
        ));
    }
    fighter.change_status(next.into(), false.into());
    1.into()
}

/// Plays the phase's motion once and hands control to the loop.
///
/// The motion kinds are Mythra's own `special_hi_start`, `special_air_hi1`,
/// `special_air_hi_jump` and `special_air_hi_end`. Those are the slots the build
/// writes the retargeted Mii `Hi3` clips into, so the name stays a stock Elight
/// motion kind and only the clip behind it changes.
unsafe extern "C" fn main(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let id = entry_id(fighter);
    let name = match StatusModule::status_kind(boma) {
        STATUS_START => "special_hi_start",
        STATUS_HOLD => "special_air_hi1",
        STATUS_GROUND_SPIN => "special_air_hi_jump",
        STATUS_AIR_SPIN => "special_air_hi_end",
        _ => return 0.into(),
    };
    MotionModule::change_motion(boma, Hash40::new(name), 0.0, 1.0, false, 0.0, false, false);
    if id != usize::MAX && name == "special_air_hi_end" && !SEEN_AIR[id] {
        SEEN_AIR[id] = true;
        AIR_START_Y[id] = (*PostureModule::pos(boma)).y;
    }
    fighter.sub_shift_status_main(L2CValue::Ptr(main_loop as *const () as _))
}

unsafe extern "C" fn main_loop(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let status = StatusModule::status_kind(boma);
    let ground = StatusModule::situation_kind(boma) == *SITUATION_KIND_GROUND;

    if status == STATUS_AIR_SPIN {
        if fighter.sub_transition_group_check_air_cliff().get_bool() {
            return 1.into();
        }
        if ground {
            return change(
                fighter,
                *FIGHTER_STATUS_KIND_LANDING_FALL_SPECIAL,
                "air spin landed",
            );
        }
        if MotionModule::is_end(boma) {
            return change(fighter, *FIGHTER_STATUS_KIND_FALL_SPECIAL, "air spin ended");
        }
        return 0.into();
    }

    if !ground {
        return change(fighter, STATUS_AIR_SPIN, "left the ground");
    }

    match status {
        STATUS_START if MotionModule::is_end(boma) => {
            if ControlModule::check_button_off(boma, *CONTROL_PAD_BUTTON_SPECIAL) {
                change(fighter, STATUS_GROUND_SPIN, "startup ended after release")
            } else {
                change(fighter, STATUS_HOLD, "startup ended while held")
            }
        }
        STATUS_HOLD
            if ControlModule::check_button_off(boma, *CONTROL_PAD_BUTTON_SPECIAL) =>
        {
            change(fighter, STATUS_GROUND_SPIN, "special released")
        }
        STATUS_GROUND_SPIN if MotionModule::is_end(boma) => {
            change(fighter, *FIGHTER_STATUS_KIND_WAIT, "ground spin ended")
        }
        _ => 0.into(),
    }
}

unsafe extern "C" fn end(fighter: &mut L2CFighterCommon) -> L2CValue {
    AttackModule::clear_all(fighter.module_accessor);
    if StatusModule::status_kind(fighter.module_accessor) == STATUS_AIR_SPIN {
        JostleModule::set_status(fighter.module_accessor, true);
    }
    0.into()
}

/// Applies Mii Swordfighter's measured air gravity and terminal speed.
///
/// The donor's dedicated `Hi3` kinetic lives in Mii Swordfighter's own
/// parameter block and cannot be installed on `elight`, so the donor adapts the
/// common air values for the duration of the air phase. The two scale factors
/// are **intentional custom tuning of this mod, not the donor's data and not a
/// measured Mii value**: `hero_spin_params` records the full history, the
/// measured descent-per-hit-window numbers behind the current 0.70 / 0.70, and
/// why the phase still ends on its own rather than hovering.
///
/// Registered on `STATUS_AIR_SPIN` only, so this applies to the attacker's own
/// fall for the duration of the aerial phase and to nothing else. It runs once
/// per frame as an `Exec` callback, which is what keeps the values applied, and
/// it stops being called the moment the phase ends - the landing transition to
/// `LANDING_FALL_SPECIAL` and the motion-end transition to `FALL_SPECIAL` both
/// leave this status, so normal gravity resumes immediately.
unsafe extern "C" fn air_exec(fighter: &mut L2CFighterCommon) -> L2CValue {
    fighter.clear_lua_stack();
    lua_args!(
        fighter,
        *FIGHTER_KINETIC_ENERGY_ID_GRAVITY,
        -MII_HI3_AIR_ACCEL_Y * AIR_ACCEL_Y_SCALE
    );
    sv_kinetic_energy::set_accel(fighter.lua_state_agent);
    fighter.clear_lua_stack();
    lua_args!(
        fighter,
        *FIGHTER_KINETIC_ENERGY_ID_GRAVITY,
        MII_HI3_AIR_SPEED_Y_STABLE * AIR_SPEED_Y_SCALE
    );
    sv_kinetic_energy::set_stable_speed(fighter.lua_state_agent);
    0.into()
}

/// Mythra's own sword trail, borrowed rather than the donor's.
///
/// The donor's Mii trail textures and effects are not in `elight`'s effect bank.
/// These two calls are the donor's own substitution, taken from Mythra's
/// `AttackAirHi.txt` and verified to load; they attach to `sword1`, which is
/// Mythra's sword-hand bone. On c06/c07 that sword is hidden by the build's
/// `hide_esword` pass for the *Pyra* side, but this is `elight`, whose sword is
/// stock and still present, so the trail has something to attach to.
unsafe fn sword_trail_on(agent: &mut L2CAgentBase) {
    macros::AFTER_IMAGE4_ON_arg29(
        agent,
        Hash40::new("tex_elight_sword3"),
        Hash40::new("tex_elight_sword2"),
        6,
        Hash40::new("sword1"),
        0,
        0,
        -0.08,
        Hash40::new("sword1"),
        15.5,
        0,
        -0.08,
        true,
        Hash40::new("null"),
        Hash40::new("sword1"),
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        0,
        *EFFECT_AXIS_X,
        0,
        *TRAIL_BLEND_ALPHA,
        101,
        *TRAIL_CULL_NONE,
        1.4,
        0.1,
    );
}

/// Ground spin trail, on frames 2-42. The donor's timing.
unsafe extern "C" fn fx_ground(agent: &mut L2CAgentBase) {
    frame(agent.lua_state_agent, 2.0);
    if macros::is_excute(agent) {
        sword_trail_on(agent);
    }
    frame(agent.lua_state_agent, 42.0);
    if macros::is_excute(agent) {
        macros::AFTER_IMAGE_OFF(agent, 3);
    }
}

/// Air spin trail, on frames 4-54. The donor's timing.
unsafe extern "C" fn fx_air(agent: &mut L2CAgentBase) {
    frame(agent.lua_state_agent, 4.0);
    if macros::is_excute(agent) {
        sword_trail_on(agent);
    }
    frame(agent.lua_state_agent, 54.0);
    if macros::is_excute(agent) {
        macros::AFTER_IMAGE_OFF(agent, 3);
    }
}

/// The hold phase has no donor game script at all.
///
/// In the donor this function is a guard that forwards non-c06/c07 Mythra back
/// to her own `game_specialairhi1` and does nothing for c06/c07. With the branch
/// gone it is an empty body, and it still has to be registered: the point is to
/// *suppress* the stock script. Mii's `Hi3` has no hold-phase script, and if
/// this registration were dropped, c06/c07 would fall through to Mythra's own
/// `SpecialAirHi1` while the status machine is playing the retargeted hold
/// clip, putting her vanilla up-B effects and hitboxes on top of the spin.
unsafe extern "C" fn hi3_ground_hold(_agent: &mut L2CAgentBase) {}

include!("hero_spin_acmd.rs");

pub fn install() {
    // Fail loudly rather than overwrite a real status if the toolchain moves
    // Mythra's table out from under these four ids.
    let _ = status_id_for();

    crate::diagnostic!(println!(
        "{} Hero's Spin: Mii Swordfighter Hi3, statuses {:#x}-{:#x}, costumes {:?}",
        LOG_HERO_SPIN,
        STATUS_START,
        STATUS_AIR_SPIN,
        crate::TARGET_COSTUMES
    ));

    let mut agent = Agent::new("elight");
    agent.set_costume(crate::TARGET_COSTUMES.to_vec());
    agent.status(Pre, *FIGHTER_STATUS_KIND_SPECIAL_HI, entry_pre);
    for kind in STATUS_START..=STATUS_AIR_SPIN {
        let phase_pre = match kind {
            STATUS_START => pre_start,
            STATUS_AIR_SPIN => pre_air,
            _ => pre_ground,
        };
        agent
            .status(Pre, kind, phase_pre)
            .status(Main, kind, main)
            .status(End, kind, end);
    }
    agent.status(Exec, STATUS_AIR_SPIN, air_exec);
    agent.install();

    let mut acmd = Agent::new("elight");
    acmd.set_costume(crate::TARGET_COSTUMES.to_vec());
    acmd.game_acmd("game_specialhistart", hi3_ground_start, Priority::Default)
        .game_acmd("game_specialairhi1", hi3_ground_hold, Priority::Default)
        .game_acmd("game_specialairhijump", hi3_ground_spin, Priority::Default)
        .game_acmd("game_specialairhiend", hi3_air_spin, Priority::Default)
        .effect_acmd("effect_specialairhijump", fx_ground, Priority::Default)
        .effect_acmd("effect_specialairhiend", fx_air, Priority::Default)
        .install();
}
