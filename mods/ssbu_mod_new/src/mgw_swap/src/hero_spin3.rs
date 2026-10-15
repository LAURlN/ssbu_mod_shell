//! Mythra c06/c07 Hero's Spin, using Mii Swordfighter's Hi3 clips and game ACMD.
//! The older hero_spin.rs port uses Hi1 (Stone Scabbard) and is not installed.
//! Ground start/hold/release and aerial spin are separate statuses. Air movement
//! uses Mythra's native aerial-jump kinetic as an initial, testable adaptation:
//! Mii's dedicated HI3 kinetic cannot be installed on Elight.
use smash::{
    app::{lua_bind::*, sv_animcmd::*, sv_kinetic_energy, *},
    hash40,
    lib::{lua_const::*, L2CValue},
    lua2cpp::*,
    phx::*,
};
use smash_script::*;
use smashline::*;
use super::is_target_costume;
use super::hero_spin3_params::{MGW_HI3_AIR_ACCEL_Y, MGW_HI3_AIR_SPEED_Y_STABLE};

// Small additional reductions from the donor's measured common values. The
// user reported the .c air spin still descended too quickly near its late hits.
const MGW_HI3_AIR_ACCEL_Y_SCALE: f32 = 0.85;
const MGW_HI3_AIR_SPEED_Y_SCALE: f32 = 0.90;

const START: i32 = 0x1F1;
const HOLD: i32 = 0x1F2;
const GROUND_SPIN: i32 = 0x1F3;
const AIR_SPIN: i32 = 0x1F4;

unsafe fn is_target(boma: *mut BattleObjectModuleAccessor) -> bool {
    is_target_costume(WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR))
}

// Exact Elight SpecialHi Pre setup from the 13.0.4 status dump. Keep the
// shared entry hook's non-c06/c07 path independent of the original_status
// trampoline: it has been crashing when vanilla-colour Mythra starts up-B.
unsafe fn vanilla_entry_pre(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    StatusModule::init_settings(
        boma,
        SituationKind(*SITUATION_KIND_NONE),
        *FIGHTER_KINETIC_TYPE_MOTION_CLIFF_MOVE,
        *GROUND_CORRECT_KIND_KEEP as u32,
        GroundCliffCheckKind(*GROUND_CLIFF_CHECK_KIND_NONE),
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
            | *FIGHTER_LOG_MASK_FLAG_ACTION_TRIGGER_ON) as u64,
        *FIGHTER_STATUS_ATTR_START_TURN as u32,
        *FIGHTER_POWER_UP_ATTACK_BIT_SPECIAL_HI as u32,
        0,
    );
    0.into()
}

unsafe fn change(fighter: &mut L2CFighterCommon, next: i32, reason: &str) -> L2CValue {
    #[cfg(feature = "swap-diagnostics")]
    println!(
        "[MGW-HI3] transition {:#x}->{:#x} {} frame={:.1} situation={}",
        StatusModule::status_kind(fighter.module_accessor), next, reason,
        MotionModule::frame(fighter.module_accessor),
        StatusModule::situation_kind(fighter.module_accessor),
    );
    fighter.change_status(next.into(), false.into());
    1.into()
}

unsafe extern "C" fn entry_pre(fighter: &mut L2CFighterCommon) -> L2CValue {
    if !is_target(fighter.module_accessor) {
        return vanilla_entry_pre(fighter);
    }
    let ground = StatusModule::situation_kind(fighter.module_accessor) == *SITUATION_KIND_GROUND;
    let next = if ground { START } else { AIR_SPIN };
    #[cfg(feature = "swap-diagnostics")]
    println!("[MGW-HI3] entry c{:02} -> {:#x} ground={}", WorkModule::get_int(fighter.module_accessor, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR), next, ground);
    StatusModule::set_status_kind_interrupt(fighter.module_accessor, next);
    1.into()
}

// In a Pre callback, status_kind can still report the outgoing status. Never
// infer which custom status is entering from it: that caused AIR_SPIN to use
// GROUND_STOP and land at frame 0 in the first Switch log.
unsafe fn pre_common(fighter: &mut L2CFighterCommon, ground: bool, start_turn: bool) -> L2CValue {
    let boma = fighter.module_accessor;
    StatusModule::init_settings(
        boma,
        SituationKind(if ground { *SITUATION_KIND_GROUND } else { *SITUATION_KIND_AIR }),
        if ground { *FIGHTER_KINETIC_TYPE_GROUND_STOP } else { *FIGHTER_KINETIC_TYPE_JUMP_AERIAL },
        if ground { *GROUND_CORRECT_KIND_GROUND as u32 } else { *GROUND_CORRECT_KIND_AIR as u32 },
        GroundCliffCheckKind(if ground { *GROUND_CLIFF_CHECK_KIND_NONE } else { *GROUND_CLIFF_CHECK_KIND_ALWAYS_BOTH_SIDES }),
        true,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_NONE_FLAG,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_NONE_INT,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_NONE_FLOAT,
        0,
    );
    FighterStatusModuleImpl::set_fighter_status_data(
        boma, false, *FIGHTER_TREADED_KIND_NO_REAC, false, false, false,
        (*FIGHTER_LOG_MASK_FLAG_ATTACK_KIND_SPECIAL_HI | *FIGHTER_LOG_MASK_FLAG_ACTION_CATEGORY_ATTACK) as u64,
        if start_turn { *FIGHTER_STATUS_ATTR_START_TURN as u32 } else { 0 },
        *FIGHTER_POWER_UP_ATTACK_BIT_SPECIAL_HI as u32, 0,
    );
    #[cfg(feature = "swap-diagnostics")]
    println!(
        "[MGW-HI3] pre ground={} outgoing={:#x} situation={} kinetic={} start_turn={} stick_x={:.3} lr={:.1}",
        ground, StatusModule::status_kind(boma),
        StatusModule::situation_kind(boma), KineticModule::get_kinetic_type(boma),
        start_turn, ControlModule::get_stick_x(boma), PostureModule::lr(boma)
    );
    0.into()
}

unsafe extern "C" fn pre_start(fighter: &mut L2CFighterCommon) -> L2CValue {
    // Both native Elight and Mii SpecialHi Pre use START_TURN. The interrupt
    // into our custom status bypasses that setup, so restore it on entry.
    pre_common(fighter, true, true)
}

unsafe extern "C" fn pre_ground(fighter: &mut L2CFighterCommon) -> L2CValue {
    pre_common(fighter, true, false)
}

unsafe extern "C" fn pre_air(fighter: &mut L2CFighterCommon) -> L2CValue {
    // Direct aerial entry interrupts SPECIAL_HI (0x1de in the Switch trace).
    // Here status_kind identifies that source, never the incoming phase.
    // Falling out of START/HOLD/GROUND_SPIN must preserve the facing already
    // chosen at startup rather than run another directional-input check.
    let start_turn = StatusModule::status_kind(fighter.module_accessor) == *FIGHTER_STATUS_KIND_SPECIAL_HI;
    pre_common(fighter, false, start_turn)
}

unsafe extern "C" fn main(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let status = StatusModule::status_kind(boma);
    let name = match status {
        START => "special_hi_start",
        HOLD => "special_air_hi1",
        GROUND_SPIN => "special_air_hi_jump",
        AIR_SPIN => "special_air_hi_end",
        _ => return 0.into(),
    };
    MotionModule::change_motion(boma, Hash40::new(name), 0.0, 1.0, false, 0.0, false, false);
    #[cfg(feature = "swap-diagnostics")]
    println!(
        "[MGW-HI3] phase status={:#x} motion={} observed={:#x} end={:.1} kinetic={} stick_x={:.3} lr={:.1}",
        status, name, MotionModule::motion_kind(boma), MotionModule::end_frame(boma),
        KineticModule::get_kinetic_type(boma), ControlModule::get_stick_x(boma), PostureModule::lr(boma),
    );
    fighter.sub_shift_status_main(L2CValue::Ptr(main_loop as *const () as _))
}

unsafe extern "C" fn main_loop(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let status = StatusModule::status_kind(boma);
    let ground = StatusModule::situation_kind(boma) == *SITUATION_KIND_GROUND;
    if status == AIR_SPIN {
        if fighter.sub_transition_group_check_air_cliff().get_bool() {
            return 1.into();
        }
        if ground {
            return change(fighter, *FIGHTER_STATUS_KIND_LANDING_FALL_SPECIAL, "air spin landed");
        }
        if MotionModule::is_end(boma) {
            return change(fighter, *FIGHTER_STATUS_KIND_FALL_SPECIAL, "air spin ended");
        }
        return 0.into();
    }
    if !ground {
        return change(fighter, AIR_SPIN, "left ground");
    }
    match status {
        START if MotionModule::is_end(boma) => {
            if ControlModule::check_button_off(boma, *CONTROL_PAD_BUTTON_SPECIAL) {
                change(fighter, GROUND_SPIN, "start ended after release")
            } else {
                change(fighter, HOLD, "start ended while held")
            }
        }
        HOLD if ControlModule::check_button_off(boma, *CONTROL_PAD_BUTTON_SPECIAL) => {
            change(fighter, GROUND_SPIN, "special released")
        }
        GROUND_SPIN if MotionModule::is_end(boma) => {
            change(fighter, *FIGHTER_STATUS_KIND_WAIT, "ground spin ended")
        }
        _ => 0.into(),
    }
}

unsafe extern "C" fn end(fighter: &mut L2CFighterCommon) -> L2CValue {
    AttackModule::clear_all(fighter.module_accessor);
    if StatusModule::status_kind(fighter.module_accessor) == AIR_SPIN {
        JostleModule::set_status(fighter.module_accessor, true);
    }
    0.into()
}

// The Mii's dedicated Hi3 kinetic is not usable on Elight. Apply the Mii's
// measured common air gravity and terminal fall speed to the recipient's air
// kinetic for this phase. See references/miiswordsman_special_hi3/kinetic_manifest.json.
unsafe extern "C" fn air_exec(fighter: &mut L2CFighterCommon) -> L2CValue {
    fighter.clear_lua_stack();
    lua_args!(fighter, *FIGHTER_KINETIC_ENERGY_ID_GRAVITY, -MGW_HI3_AIR_ACCEL_Y * MGW_HI3_AIR_ACCEL_Y_SCALE);
    sv_kinetic_energy::set_accel(fighter.lua_state_agent);
    fighter.clear_lua_stack();
    lua_args!(fighter, *FIGHTER_KINETIC_ENERGY_ID_GRAVITY, MGW_HI3_AIR_SPEED_Y_STABLE * MGW_HI3_AIR_SPEED_Y_SCALE);
    sv_kinetic_energy::set_stable_speed(fighter.lua_state_agent);
    #[cfg(feature = "swap-diagnostics")]
    trace_height(fighter, "elight");
    0.into()
}

#[cfg(feature = "swap-diagnostics")]
unsafe fn trace_height(fighter: &mut L2CFighterCommon, label: &str) {
    let boma = fighter.module_accessor;
    let frame = MotionModule::frame(boma) as i32;
    if (0..=56).contains(&frame) && frame % 8 == 0 {
        println!(
            "[MGW-HI3] height {} frame={} y={:.2} situation={} kinetic={}",
            label, frame, (*PostureModule::pos(boma)).y,
            StatusModule::situation_kind(boma), KineticModule::get_kinetic_type(boma)
        );
    }
}

// Read-only donor measurement for comparing the transfer with a Mii
// Swordfighter configured to use Hi3. It runs only in diagnostic builds.
#[cfg(feature = "swap-diagnostics")]
unsafe extern "C" fn donor_probe(fighter: &mut L2CFighterCommon) {
    if MotionModule::motion_kind(fighter.module_accessor) == hash40("special_air_hi3") {
        trace_height(fighter, "miiswordsman");
    }
}

unsafe fn vanilla(agent: &mut L2CAgentBase, name: &str) {
    // These four original Elight game scripts are copied from the local dump
    // into hero_spin3_vanilla_acmd.rs. Smashline's original_acmd lookup can
    // return its unreachable-script sentinel for unregistered presentation
    // categories; never dispatch through that sentinel on other costumes.
    match name {
        "game_specialhistart" => vanilla_game_specialhistart(agent),
        "game_specialairhi1" => vanilla_game_specialairhi1(agent),
        "game_specialairhijump" => vanilla_game_specialairhijump(agent),
        "game_specialairhiend" => vanilla_game_specialairhiend(agent),
        _ => (),
    }
}

unsafe extern "C" fn hi3_ground_hold(agent: &mut L2CAgentBase) {
    if !is_target(agent.module_accessor) {
        vanilla(agent, "game_specialairhi1");
    }
}

// Use Elight's own proven sword trail textures and sword1 attachment from
// AttackAirHi.txt. The donor's Mii textures/effects are not in Elight's bank.
unsafe fn sword_trail_on(agent: &mut L2CAgentBase) {
    macros::AFTER_IMAGE4_ON_arg29(
        agent, Hash40::new("tex_elight_sword3"), Hash40::new("tex_elight_sword2"), 6,
        Hash40::new("sword1"), 0, 0, -0.08, Hash40::new("sword1"), 15.5, 0, -0.08,
        true, Hash40::new("null"), Hash40::new("sword1"),
        0, 0, 0, 0, 0, 0, 1, 0, *EFFECT_AXIS_X, 0,
        *TRAIL_BLEND_ALPHA, 101, *TRAIL_CULL_NONE, 1.4, 0.1,
    );
}

unsafe extern "C" fn fx_ground(agent: &mut L2CAgentBase) {
    if !is_target(agent.module_accessor) { return; }
    frame(agent.lua_state_agent, 2.0);
    if macros::is_excute(agent) { sword_trail_on(agent); }
    frame(agent.lua_state_agent, 42.0);
    if macros::is_excute(agent) { macros::AFTER_IMAGE_OFF(agent, 3); }
}

unsafe extern "C" fn fx_air(agent: &mut L2CAgentBase) {
    if !is_target(agent.module_accessor) { return; }
    frame(agent.lua_state_agent, 4.0);
    if macros::is_excute(agent) { sword_trail_on(agent); }
    frame(agent.lua_state_agent, 54.0);
    if macros::is_excute(agent) { macros::AFTER_IMAGE_OFF(agent, 3); }
}
include!("hero_spin3_vanilla_acmd.rs");
include!("hero_spin3_acmd.rs");

pub fn install() {
    #[cfg(feature = "swap-diagnostics")]
    println!("[MGW-HI3] build 2026-09-26.g restore native START_TURN on c06/c07 ground/air entry; retain non-c06/c07 local ACMD fallbacks");
    let mut agent = Agent::new("elight");
    agent.status(Pre, *FIGHTER_STATUS_KIND_SPECIAL_HI, entry_pre);
    for kind in START..=AIR_SPIN {
        let phase_pre = match kind {
            START => pre_start,
            AIR_SPIN => pre_air,
            _ => pre_ground,
        };
        agent.status(Pre, kind, phase_pre).status(Main, kind, main).status(End, kind, end);
    }
    agent.status(Exec, AIR_SPIN, air_exec);
    agent.install();
    #[cfg(feature = "swap-diagnostics")]
    Agent::new("miiswordsman").on_line(Main, donor_probe).install();
    Agent::new("elight")
        .game_acmd("game_specialhistart", hi3_ground_start, Priority::Default)
        .game_acmd("game_specialairhi1", hi3_ground_hold, Priority::Default)
        .game_acmd("game_specialairhijump", hi3_ground_spin, Priority::Default)
        .game_acmd("game_specialairhiend", hi3_air_spin, Priority::Default)
        .effect_acmd("effect_specialairhijump", fx_ground, Priority::Default)
        .effect_acmd("effect_specialairhiend", fx_air, Priority::Default)
        .install();
}
