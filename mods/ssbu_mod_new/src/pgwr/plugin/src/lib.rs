#![feature(proc_macro_hygiene)]
#![allow(
    unused_imports,
    unused_macros,
    unused_variables,
    unused_assignments,
    unused_unsafe,
    non_upper_case_globals,
    non_snake_case,
    clippy::borrow_interior_mutable_const
)]

// Pyra c06/c07 -> Mr. Game & Watch, with move replacements on Mythra c06/c07.
//
// The transformation is the game's own Pyra<->Mythra down-B swap, so the
// Pyra/G&W half of this crate targets `eflame` and the move-replacement half
// targets `elight`:
//!
//!   * `acmd`, `article`, `params`, `status`  -> `eflame` (Pyra) c06/c07, which is G&W.
//!     G&W's own physics, up air, down throw, normals, props, and Monkey Flip on
//!     side-B (which replaced the Judge probe that used to own that button), and
//!     G&W's own up-B, Fire (`status::special_hi`, 0.19.0).
//!   * `mythra`                     -> `elight` (Mythra) c06/c07 only, for
//     Corrin's up air, Hero's Spin and Luigi's down throw.
//!
//! The two never overlap: no G&W script is replaced on Mythra, and no Mythra
//   script is replaced on Pyra, so the G&W half of the transformation is
//   unchanged and the vanilla Mythra fallback of the down-B swap still exists.
//! `gamewatch` (the real Mr. Game & Watch) is never registered at all, so none
//!   of his own code is touched. `diddy` is registered by `diddy_probe` as a
//!   **read-only observer** - one additive `on_line` callback and no status or
//!   acmd scripts - so stock Diddy is measured as the Monkey Flip donor without
//!   any of his code being replaced. See that module for why an observer is
//!   required rather than a port.
//
// Gating is done entirely by `smashline::Agent::set_costume`, not by a runtime
// `if` inside each script. In the locked smashline that gates at *install* time:
// `install_script` and `install_status_scripts` (src/create_agent.rs) compute
// `has_costume(hash, colour)` and only call `sv_set_function_hash` /
// `sv_set_status_func` when the agent's own colour is listed. An eflame or
// elight agent in c00-c05 therefore keeps the stock script pointers and is
// untouched, which is stronger than gating inside a shared script and removes
// any risk of a half-taken `else` branch. The source of that decision is quoted
// in `acmd/mod.rs`; the Mythra side, and why the gate still holds across the
// down-B transformation, is in `mythra/mod.rs`.

use {
    smash::{
        lua2cpp::*,
        phx::*,
        app::{sv_animcmd::*, lua_bind::*, *},
        lib::{lua_const::*, L2CValue, L2CAgent},
        hash40
    },
    smash_script::*,
    smashline::{*, Priority::*}
};

/// The only costumes this mod is allowed to touch.
///
/// Pyra's c06 is the 7th colour and c07 the 8th, so on the character-select grid
/// these are the two right-hand swatches. Every value in this list is the only
/// place costume gating is defined; nothing else in the crate may hard-code 6 or
/// 7. Mythra uses the same costume filter for its three move replacements.
pub const TARGET_COSTUMES: [usize; 2] = [6, 7];

/// Log prefix. Keep it short and unique so the Switch log is easy to filter.
pub const LOG: &str = "[PGWR]";

// User-requested silent release: discarded tokens are never evaluated.
#[macro_export]
macro_rules! diagnostic {
    ($($body:tt)*) => {{ #[cfg(feature = "logging")] { $($body)* } }};
}

mod acmd;
mod article;
mod breath;
#[cfg(feature = "logging")]
mod diddy_probe;
mod mythra;
mod params;
mod status;
mod swap_effects;

#[skyline::main(name = "pyra_gamewatch_reskin")]
pub fn main() {
    #[cfg(feature = "logging")]
    crate::diagnostic!(article::log(format!("[PGWR] BOOT v{}", env!("CARGO_PKG_VERSION"))));
    crate::diagnostic!(println!("{}	Pyra G&W reskin plugin v{} (G&W up-B Fire with rescue and parachute, refreshed on landing/ledge/hit; Chrom's jab on the G&W costume, drawn with Pyra's Aegis esword and the Mythra trail; G&W physics/params bridge; breath bridge; Monkey Flip on side-B with both-sided capture telemetry; Mythra c06/c07 Corrin up air, Hero spin, and Hero neutral-B and side-B on the pair's own mana meter, Luigi down throw) loaded",
        LOG, env!("CARGO_PKG_VERSION")
    ));
    crate::diagnostic!(println!("{} gated fighter=eflame costumes={:?}", LOG, TARGET_COSTUMES));
    crate::diagnostic!(println!("{} NOT registered: gamewatch (real G&W)", LOG));
    crate::diagnostic!(println!(
        "{} Mythra (elight) c06/c07 only: Corrin up air, Hero's Spin (Hi3), Hero neutral-B and side-B on the pair's own mana meter, Luigi down throw",
        LOG
    ));

    // First: the article table is cached the first time a fighter is built.
    article::install();
    article::check_kinds();
    article::install_lifetime();
    params::install();
    acmd::install();
    status::install();
    #[cfg(feature = "logging")]
    diddy_probe::install();
    mythra::install();
    swap_effects::install();
}
