//! G&W/Pyra c06/c07 down-B uses the matching Mythra transformation visuals.
//!
//! Source: the vanilla elight SpecialLw / SpecialAirLw / SpecialLwEnd /
//! SpecialAirLwEnd effects in SSBU-Dumped-Scripts-main/smashline-hdr.
//! Native swap status, game, sound and expression scripts remain installed.
//! Aegis loads its two forms' banks (vanilla eflame Win3 also requests an
//! elight effect). One Slot Effects gives those resources explicit _cNN names.
//! Use that already loaded Mythra name directly: its automatic owner-kind
//! lookup would otherwise classify this caller as eflame and miss elight.

use smash::{app::lua_bind::WorkModule, lib::lua_const::*, lua2cpp::L2CAgentBase,
            phx::Hash40, app::sv_animcmd::frame};
use smash_script::macros;
use smashline::{Agent, Priority};

unsafe fn mythra_effect(agent: &mut L2CAgentBase, phase: &str) -> Hash40 {
    let colour = WorkModule::get_int(agent.module_accessor, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR);
    Hash40::new(&format!("elight_change_{}_c{:02}", phase, colour))
}

unsafe fn start(agent: &mut L2CAgentBase, grounded: bool) {
    let effect = mythra_effect(agent, "start");
    if macros::is_excute(agent) {
        macros::EFFECT_FOLLOW(agent, effect, Hash40::new("top"),
                              0, 10, 0, 0, 0, 0, 1.3, true);
    }
    if grounded {
        // Keep the recipient's ground-contact event at frame 7.
        frame(agent.lua_state_agent, 7.0);
        if macros::is_excute(agent) {
            macros::FOOT_EFFECT(agent, Hash40::new("null"), Hash40::new("top"),
                                0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, false);
        }
    }
    frame(agent.lua_state_agent, 11.0);
    if macros::is_excute(agent) {
        macros::EFFECT_DETACH_KIND(agent, effect, -1);
    }
}

unsafe extern "C" fn ground_start(agent: &mut L2CAgentBase) { start(agent, true); }
unsafe extern "C" fn air_start(agent: &mut L2CAgentBase) { start(agent, false); }

unsafe extern "C" fn end(agent: &mut L2CAgentBase) {
    let effect = mythra_effect(agent, "end");
    if macros::is_excute(agent) {
        macros::EFFECT_FOLLOW(agent, effect, Hash40::new("top"),
                              0, 10, 0, 0, 0, 0, 1.3, true);
    }
}

pub fn install() {
    Agent::new("eflame")
        .set_costume(crate::TARGET_COSTUMES.to_vec())
        .effect_acmd("effect_speciallw", ground_start, Priority::Default)
        .effect_acmd("effect_specialairlw", air_start, Priority::Default)
        .effect_acmd("effect_speciallwend", end, Priority::Default)
        .effect_acmd("effect_specialairlwend", end, Priority::Default)
        .install();
    crate::diagnostic!(println!("{} G&W swap effects: Mythra bank, costumes {:?}", crate::LOG, crate::TARGET_COSTUMES));
}
