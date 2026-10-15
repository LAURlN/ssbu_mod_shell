//! Donor NRO HOLD EXEC 0x58f0 and shared attack EXEC 0x5b00.
//! Registration attaches attack_exec to 1/2/APPEND only, never ATTACK3.
use super::state::*;
use smash::{app::lua_bind::*, lib::{L2CValue, lua_const::*}, lua2cpp::L2CFighterCommon,
            phx::Hash40};
use std::sync::atomic::Ordering;

pub(super) unsafe extern "C" fn hold_exec(fighter: &mut L2CFighterCommon) -> L2CValue {
    if let Some(state) = get(fighter.module_accessor) {
        let frame = state.hold_frames.fetch_add(1, Ordering::Relaxed) + 1;
        // Pinned param_special_s hold_frame_m=9. Exact equality is the donor trigger.
        if frame == super::params::HOLD_FRAME_M {
            MotionAnimcmdModule::call_script_single(fighter.module_accessor,
                *FIGHTER_ANIMCMD_EFFECT, Hash40::new("effect_pgwrherospecialsholdm"), -1);
        }
    }
    0.into()
}

pub(super) unsafe extern "C" fn attack_exec(fighter: &mut L2CFighterCommon) -> L2CValue {
    if let Some(state) = get(fighter.module_accessor) {
        if state.flag(DECIDE_SPARK_RIGHT) { state.right.wait_frames.fetch_add(1, Ordering::Relaxed); }
        if state.flag(DECIDE_SPARK_LEFT) { state.left.wait_frames.fetch_add(1, Ordering::Relaxed); }
    }
    0.into()
}
