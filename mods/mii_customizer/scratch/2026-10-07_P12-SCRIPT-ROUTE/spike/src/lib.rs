//! P12-SCRIPT-ROUTE compile-only spike (Q7). NOT the mod's plugin crate.
//!
//! Registers exactly one ACMD game script, `game_attacks3` for `miigunner`, whose body
//! reads the fighter's entry id and does nothing else. A successful build proves only
//! that this registration compiles against the pinned framework crates; nothing here has
//! ever been loaded by the game.
//!
//! Exclusive write scope: scratch/2026-10-07_P12-SCRIPT-ROUTE/ and
//! builds/.cache/p12-script-route/. Not staged under builds/<version>/.

use smash::app::lua_bind::WorkModule;
use smash::lib::lua_const::FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID;
use smash::lua2cpp::L2CAgentBase;
use smashline::{*, Priority::*};

/// Read the entry id of the executing fighter and stop. No branch, no game call
/// beyond the read itself.
pub unsafe extern "C" fn game_attacks3(agent: &mut L2CAgentBase) {
    let _entry_id: i32 = WorkModule::get_int(
        agent.module_accessor,
        *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID,
    );
}

pub fn install() {
    Agent::new("miigunner")
        .game_acmd("game_attacks3", game_attacks3, Default)
        .install();
}

#[skyline::main(name = "p12_spike")]
pub fn main() {
    install();
}
