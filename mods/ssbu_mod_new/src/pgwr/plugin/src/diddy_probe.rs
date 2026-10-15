//! Read-only observation of stock Diddy, so Monkey Flip finally has a donor control.
//!
//! # Why this module exists
//!
//! The victim half of the capture has never been measured. The one hardware run
//! that produced telemetry (0.20.2) logged 26 `VICTIM` frames, every one with
//! `victim=0xffffffff`, `link=0x50000000` (the engine's null), `is_catch=false`
//! and `dist=-1.00`: no target was ever acquired, so the log could say nothing
//! about whether a box contained a victim.
//!
//! Diddy is the donor. Nothing in this crate registers a `diddy` agent, so when
//! the user plays Diddy every `[PGWR-MFLIP]` line from that attempt is absent -
//! not because logging is broken but because our code never runs on him. That
//! leaves the one comparison that would settle the open questions (does
//! `CLUNG_DIDDY` animate on a non-Diddy victim, and what does a working capture
//! look like from the victim's side) unavailable.
//!
//! # This is an observer, not a port
//!
//! It installs **no** status scripts and **no** acmd scripts. It registers a
//! single `on_line(Main, ...)` callback, which in the locked smashline
//! (`install_line_callback_costume` -> `CALLBACKS`) is additive: a line callback
//! runs in addition to whatever the fighter's own status main already does. No
//! `sv_set_status_func` is called for Diddy, so every one of his scripts,
//! statuses, clips, hitboxes, damage and motion stay exactly as shipped.
//!
//! This matters beyond tidiness. Diddy is the control: if this module changed his
//! behaviour, the control would be measuring our own code instead of the donor,
//! and the comparison would be worthless. It also means the vanilla negative
//! control still works - stock Diddy on a stage with no Pyra present must behave
//! identically with and without this plugin.
//!
//! Nothing here writes state. Every call is a read of a module accessor, and
//! every diagnostic is bounded and one-shot per status change, so it cannot hang
//! the console (AGENTS.md rule 25).

use smash::{
    app::{lua_bind::*, *},
    hash40,
    lib::{lua_const::*, L2CValue},
    lua2cpp::*,
    phx::*,
};
use smash_script::*;
use smashline::*;

use crate::status::monkey_flip::log;

/// Log prefix, so donor lines are never confused with our own move's.
pub const LOG_DIDDY: &str = "[PGWR-DIDDY]";

/// `FIGHTER_STATUS_KIND_CLUNG_DIDDY` in the pinned `skyline-smash`. This is the
/// status the engine puts a *victim* into, and it is the one whose animatability
/// on a non-Diddy fighter is the open question.
///
/// A function rather than a `const`: the pinned bindings expose these as
/// `LuaConst`, whose `Deref` is not a `const fn`, so they cannot be deref-coerced
/// in constant position.
fn clung_diddy() -> i32 {
    *FIGHTER_STATUS_KIND_CLUNG_DIDDY
}

/// Diddy's Monkey Flip is his `SPECIAL_S` in the pinned build: the eleven-phase
/// block `SPECIAL_S_JUMP` (0x1E5) through `SPECIAL_S_DAMAGE_FALL` (0x1EF), which
/// mirrors our eleven phases one for one. These are ids in *his* table and are
/// only ever compared against Diddy's own `StatusModule::status_kind`; AGENTS.md
/// rule 19 forbids treating numeric status ids as comparable across fighters, so
/// nothing here is equated with our block.
fn monkey_flip_start() -> i32 {
    *FIGHTER_DIDDY_STATUS_KIND_SPECIAL_S_JUMP
}
fn monkey_flip_end() -> i32 {
    *FIGHTER_DIDDY_STATUS_KIND_SPECIAL_S_DAMAGE_FALL
}

/// Budgets. One line per status change plus a bounded per-frame window, so a
/// long Monkey Flip cannot flood the file.
const CHANGE_BUDGET: u32 = 24;
const FRAME_BUDGET: u32 = 90;

/// Last status we printed a `STATUS` line for, and the budgets, per entry.
/// Static rather than per-fighter state: this module must not write into
/// Diddy's WorkModule, which is his (AGENTS.md rule 19, and the same reasoning
/// as the per-entry storage in `status::monkey_flip`).
#[derive(Copy, Clone)]
struct Probe {
    last_status: i32,
    changes: u32,
    frames: u32,
    armed: bool,
}

const EMPTY: Probe = Probe { last_status: -1, changes: 0, frames: 0, armed: false };
static mut PROBE: [Probe; 8] = [EMPTY; 8];

/// Diddy's own Monkey Flip block, if these constants are the ones the pinned
/// build exposes. Guarded at runtime rather than asserted at install: if a future
/// pin renames them the observer should simply go quiet, not fail the build.
fn is_monkey_flip(status: i32) -> bool {
    status >= monkey_flip_start() && status <= monkey_flip_end()
}

/// A `Main` line callback: it returns `()`, and runs in addition to Diddy's own
/// status main rather than replacing it.
unsafe extern "C" fn observe(fighter: &mut L2CFighterCommon) {
    let boma = fighter.module_accessor;
    if boma.is_null() {
        return;
    }
    let entry = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
    if entry < 0 || entry as usize >= PROBE.len() {
        return;
    }
    let status = StatusModule::status_kind(boma);
    let clung = status == clung_diddy();
    if !is_monkey_flip(status) && !clung {
        // Leaving the block disarms the per-frame window, so a later attempt
        // gets a fresh budget instead of inheriting a spent one.
        let p = &mut *(&raw mut PROBE).cast::<Probe>().add(entry as usize);
        p.armed = false;
        p.frames = 0;
        p.last_status = -1;
        return;
    }

    let (motion, frame) = (MotionModule::motion_kind(boma), MotionModule::frame(boma));
    let situation = StatusModule::situation_kind(boma);
    let catch = CatchModule::is_catch(boma);
    let capture = CatchModule::capture_object_id(boma, false);
    let link = LinkModule::get_node_object_id(boma, *LINK_NO_CAPTURE);

    let p = &mut *(&raw mut PROBE).cast::<Probe>().add(entry as usize);

    // The transition, not the state: the line that says the engine moved him.
    if status != p.last_status && p.changes < CHANGE_BUDGET {
        p.last_status = status;
        p.changes += 1;
        crate::diagnostic!(log(format!(
            "{} STATUS entry {} status={:#x} situation={} motion={:#x} frame={:.1} catch={} capture={:#x} link={:#x}{}",
            LOG_DIDDY, entry, status, situation, motion, frame, catch, capture, link,
            if clung { " CLUNG" } else { "" }
        )));
    }

    // Per-frame, only inside the leap/kick window and only once per attempt.
    if is_monkey_flip(status) && !p.armed && p.frames < FRAME_BUDGET {
        p.armed = true;
    }
    if p.armed && p.frames < FRAME_BUDGET {
        p.frames += 1;
        crate::diagnostic!(log(format!(
            "{} FRAME entry {} status={:#x} f{:.0} motion={:#x} catch={} capture={:#x} link={:#x}",
            LOG_DIDDY, entry, status, frame, motion, catch, capture, link
        )));
    }
}

pub fn install() {
    let mut agent = Agent::new("diddy");
    // No `set_costume`: this observes stock Diddy in every costume, which is the
    // point - he is the control, not a target of the reskin.
    // No `status(...)` and no `acmd(...)`: nothing of his is replaced.
    agent.on_line(Main, observe);
    agent.install();
}
