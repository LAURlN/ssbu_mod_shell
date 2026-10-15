//! Native game_specials3/game_specialairs3: activate lightning at frame 10.
//! Evidence: acmd_native_registrations.json, implementation NRO+0x115590.
//! Successful charged release is unconditional; no recipient SP read.
use super::state::{get, ACTIVATE_LIGHTNING};
use smash::{app::sv_animcmd::frame, lua2cpp::L2CAgentBase};
use smash_script::macros::is_excute;

pub(super) unsafe extern "C" fn game(agent: &mut L2CAgentBase) {
    frame(agent.lua_state_agent, 10.0);
    if is_excute(agent) {
        if let Some(state) = get(agent.module_accessor) {
            state.set(ACTIVATE_LIGHTNING);
            // T-0052: absent from every previous log. The 2026-10-01 card log shows
            // bolts spawning, which implies this ran, but nothing recorded it
            // directly, so "the script never reached frame 10" stayed possible.
            crate::diagnostic!(super::logging::log("ACTIVATE lightning frame=10"));
        } else {
            crate::diagnostic!(super::logging::log("ACTIVATE lightning frame=10 without owned state"));
        }
    }
}
