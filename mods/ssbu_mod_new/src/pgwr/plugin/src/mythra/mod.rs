//! Move replacements on **Mythra** (`elight`) in costumes c06 and c07.
//!
//! * up air -> Corrin's up air (`d02`)
//! * up B -> Hero's Spin (`d02`, Mii Swordfighter `Hi3`)
//! * down throw -> Luigi's down throw (`d02`)
//! * down smash -> Lucas's down smash, with his charge hold (`d02`)
//! * one mana meter for the pair, shared by neutral-B and side-B (`hero_mana`)
//!
//! Ported from `mod_files/mythra_gamewatch_swap`, which ships the same three
//! moves on the same two costumes. The moves, the frame data, the hitboxes, the
//! status ids and the air kinetic are the donor's.
//!
//! # This is a second fighter, and that is the point
//!
//! The rest of this crate targets `eflame` and nothing else: Pyra c06/c07 *is*
//! Mr. Game & Watch, and pressing down-B runs the game's own Pyra-to-Mythra
//! transformation. So "give Mythra the Hero's Spin" is a different statement
//! here than it is in the donor project. This module registers `elight`, which
//! the rest of the crate deliberately never touches, and the Pyra side is left
//! exactly as it was: G&W's up air still shoots the breath projectile, G&W's
//! down throw is still G&W's, and no G&W file, script or status is changed.
//!
//! # The gate, and why it still works after the down-B swap
//!
//! Gating is install-time, through `crate::TARGET_COSTUMES`, exactly like every
//! other override in this crate. In the locked smashline (`be3ef308`,
//! `src/create_agent.rs`) the filter is applied in both `install_script` (ACMD,
//! line 246) and `install_status_scripts` (line 738): for an agent whose own
//! colour is not listed, `sv_set_function_hash` / `sv_set_status_func` are never
//! reached and the stock pointers stay in place.
//!
//! The costume it compares against is *not* read from the active body. It comes
//! from `get_costume_from_entry_id` (`src/utils.rs:40`), which reads a field at
//! offset `100` (`0x64`) on the **entry** - the slot the player picked on the
//! character-select grid. That matters here, and it is the reason this works at
//! all: an entry created as Pyra c06 reports `6` for the entire match, including
//! the frames where Mythra is the body standing there after down-B. So
//!
//! * Pyra c06 or c07 selected -> entry reports 6 or 7 -> Mythra gets the three
//!   moves, in both the Pyra and the Mythra half of the transformation;
//! * Mythra c06 or c07 selected directly -> entry reports 6 or 7 -> same;
//! * Mythra c00-c05 selected -> entry reports 0-5 -> gate fails -> stock Mythra,
//!   every script pointer untouched.
//!
//! The third case is the negative control, and `gate_trace` below is what makes
//! the first two a reading rather than a judgement.
//!
//! # What the donor's runtime branch bought, and why it is not needed here
//!
//! The donor registers `elight` globally and checks the costume inside each
//! script, keeping a hand-copied copy of vanilla Mythra in the `else` arm. That
//! copy is roughly half the donor's two script files, and for Hero's Spin it
//! pulls in a third file, `hero_spin3_vanilla_acmd.rs`. None of it is ported,
//! because with an install-time gate those arms are unreachable. The trade is
//! explicit: this mod ships less code, and in exchange it never carries a second
//! copy of vanilla that could drift from the game.
//!
//! # Status id allocation
//!
//! `FIGHTER_ELIGHT_STATUS_KIND_NUM` is `0x1F1` in the locked `skyline-smash`, so
//! Hero's Spin takes exactly the first four ids above Mythra's own table.
//!
//! | id | name | entered by |
//! | - | ---- | ---------- |
//! | `0x1F1` | `STATUS_START` | up B on the ground, via `SPECIAL_HI` `Pre` |
//! | `0x1F2` | `STATUS_HOLD` | startup clip ending while SPECIAL_B is held |
//! | `0x1F3` | `STATUS_GROUND_SPIN` | SPECIAL_B released, or startup ended after release |
//! | `0x1F4` | `STATUS_AIR_SPIN` | up B in the air, or leaving the ground |
//!
//! `status_id_for` re-checks the number against `lua_const` at load, so a
//! toolchain bump that moves Mythra's table fails at boot instead of silently
//! overwriting a real status. This is the same guard `status::judge` uses for
//! its own `0x1EE` on `eflame`; the two are different fighters with separate
//! tables and cannot collide.

pub mod attack_air_hi;
pub mod hero_mana;
pub mod hero_spin;
pub mod hero_spin_params;
pub mod hero_neutral_b;
#[cfg(feature = "hero-side-b")]
pub mod hero_side_b;
pub mod ness_throw_b;
pub mod throw_lw;
pub mod lucas_attack_lw4;

use smash::{
    app::lua_bind::*,
    lib::{lua_const::*, L2CAgent},
    lua2cpp::*,
    phx::*,
};
use smashline::*;

use crate::LOG;

pub const LOG_HERO_SPIN: &str = "[PGWR-HI3]";
pub const LOG_UPAIR: &str = "[PGWR-AIRHI]";
pub const LOG_DTHROW: &str = "[PGWR-THROWLW]";
pub const LOG_LW4: &str = "[PGWR-LW4]";
/// Ness's back throw, `throw_b`, on the same two costumes. Separate prefix so a
/// log line can name which throw it came from.
pub const LOG_THROW_B: &str = "[PGWR-NESSTHB]";

/// Hero's Spin phase status ids. `0x1F1`-`0x1F4`, see the table above.
pub const STATUS_START: i32 = 0x1F1;
pub const STATUS_HOLD: i32 = 0x1F2;
pub const STATUS_GROUND_SPIN: i32 = 0x1F3;
pub const STATUS_AIR_SPIN: i32 = 0x1F4;

/// Fail loudly if the toolchain ever moves Mythra's status table.
///
/// `status::judge` does the same for `eflame`. A panic here happens at load,
/// before any fighter is built, which is the only moment it is still safe.
#[inline]
pub fn status_id_for() -> i32 {
    assert_eq!(
        STATUS_START,
        *FIGHTER_ELIGHT_STATUS_KIND_NUM,
        "Hero's Spin status ids no longer match FIGHTER_ELIGHT_STATUS_KIND_NUM; \
         re-derive them and update the allocation table in this file"
    );
    STATUS_START
}

/// Proof that the Mythra gate is live, readable from the log rather than by eye.
///
/// Mirrors `acmd::gate_trace`, which does the same job for `eflame`. It is
/// registered on a costumed `elight` agent, so smashline only ever installs it
/// for an entry reporting c06 or c07 - which means a line naming a costume is
/// positive proof that the entry passed the gate, and that Mythra in c00-c05
/// producing no such line in the same match is the negative control.
///
/// `battle_object` is the agent's object id, not a stable handle, so it is only
/// used as a label and never retained.
static mut GATE_SEEN: [bool; 8] = [false; 8];

unsafe extern "C" fn gate_trace(agent: &mut L2CAgent) {
    let colour = WorkModule::get_int(agent.module_accessor, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR);
    let id = WorkModule::get_int(agent.module_accessor, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID) as usize;
    if id < 8 && !GATE_SEEN[id] {
        GATE_SEEN[id] = true;
        crate::diagnostic!(crate::article::log(format!(
            "{} MYTHRA GATE ACTIVE: entry {} is Mythra, running c06/c07 move \
             replacements, reported colour {}",
            LOG, id, colour
        )));
    }
}

pub fn install() {
    status_id_for();

    crate::diagnostic!(println!(
        "{} Mythra c06/c07 move replacements: Corrin up air, Hero's Spin, Luigi down throw, \
         Lucas down smash, Ness back throw",
        LOG
    ));

    attack_air_hi::install();
    hero_spin::install();
    hero_mana::install();
    hero_neutral_b::install();
    #[cfg(feature = "hero-side-b")]
    hero_side_b::install();
    throw_lw::install();
    lucas_attack_lw4::install();
    ness_throw_b::install();

    // Same gate as every override above, so this line can only appear for an
    // entry reporting c06 or c07.
    #[cfg(feature = "logging")]
    Agent::new("elight")
        .set_costume(crate::TARGET_COSTUMES.to_vec())
        .on_line(Main, gate_trace)
        .install();
}
