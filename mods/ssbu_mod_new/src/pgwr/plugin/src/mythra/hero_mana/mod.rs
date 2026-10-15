//! Owned mana (MP) for the **c06/c07 Pyra/Mythra pair**, spent by Hero's
//! neutral-B and side-B on Mythra.
//!
//! # Why this module exists
//!
//! The Hero moves in this crate were written with mana switched off: the donor's
//! `SUCCESS_SP` gate was hard-wired to "always affordable" and no MP value was
//! ever kept. That is the whole reason the mana system was not working - it was
//! specified and researched, and then never written. This module is that code.
//!
//! # What is the donor's, and what is ours
//!
//! The numbers, the gate and the failure shape are the donor's, and are pinned:
//!
//! * prices, maximum and recovery period: `params` (from the donor `vl.prc`,
//!   sha256 `dafa43c6...`);
//! * the gate itself, verbatim in shape - `amount <= sp` sets the success flag
//!   and the debit happens **only** on success - is `FUN_0001a230` followed by
//!   the `add_sp` call in `FUN_00016db0`
//!   (`refs/brave_special_s/flag_success_sp.c`, `refs/brave_special_n/neutral_b_status.c`);
//! * the debit sites: neutral-B shoots in its SHOOT MAIN, side-B in the three
//!   ATTACK MAIN bodies and never in the finisher.
//!
//! What is ours is the *storage and the arithmetic*. MP is a per-entry value in
//! this module's own table. No Hero work id is read or written, no Hero or
//! `FighterSpecializer_Brave` function is called, and the pair's other half is
//! never consulted through a donor interface (mod rule 17).
//!
//! # One meter for the pair, and why the entry is the key
//!
//! The table is indexed by `FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID`, the player
//! slot, and the gate accepts **either** half of the pair (`eflame` or `elight`)
//! while the entry reports c06 or c07. That is what makes the value survive the
//! down-B swap without any copy step: both halves of one player are one entry.
//! A battle object id is never used as a key - it changes across the swap, and it
//! is only ever read to confirm which half is currently the active body.
//!
//! # The frame token, stated plainly
//!
//! Passive recovery needs one advance per game frame. This module gets that from
//! the `on_line(Main)` callback the crate already uses for its other per-frame
//! work, gated on **the active half only** (`sv_battle_object::is_active`), so
//! the dormant partner cannot advance the meter a second time. That is the whole
//! dedupe mechanism.
//!
//! What it is *not* is a shared simulation-frame clock. The contract
//! (`refs/brave_special_n/T-0033/MANA_HUD_CONTRACT.md`) asks for one, and no
//! in-bindings clock exists in the locked `skyline-smash`: there is no
//! `get_frame_count` in the crate, and the alternatives the contract rejects
//! (`MotionModule::frame`, `global_table[0xe]`, wall time) are rejected for good
//! reasons. If the engine ever calls this line twice for one fighter in one
//! frame, recovery would run at double rate; the log prints the observed tick
//! count once per second so that is visible in the console log rather than
//! silent. A real clock needs a reserved hook and is listed in
//! `CURRENT_INSTALL.md` as not approved.
//!
//! # Failure is the donor's failure
//!
//! Out of MP the cast does not silently no-op. The donor's gate clears
//! `SUCCESS_SP` and the donor then *skips the projectile / the sparks / the
//! lightning* while still playing the move's motion. That is what the two
//! callers do here: no spend, no article, the motion plays out, and one
//! `REFUSE` line in the log. Nothing is invented in place of the donor's
//! failure effect, because that effect's name was not recoverable offline
//! (see `unverified` in the section in `CURRENT_INSTALL.md`).
//!
//! Crash-tail log: `sd:/ultimate/pgwr_mana_log.txt`, one line per event, never
//! per frame, and capped (see `logging`).

pub mod params;
#[cfg(feature = "hero-mana-reserved")]
pub mod damage;
// The fighter HUD gauge has its own feature, so showing the meter does not
// switch on the still-reserved hit/shield recovery in `damage`.
#[cfg(feature = "hero-mana-hud")]
mod hud;

mod logging;

use smash::{
    app::{self, lua_bind::*, BattleObjectModuleAccessor},
    lib::{lua_const::*, L2CAgent},
};
use smashline::{Agent, Main};
use std::sync::atomic::{AtomicI32, AtomicU32, AtomicU64, Ordering};

/// Pause reasons, kept as a bitmap so the log can name why recovery stopped.
pub(super) const PAUSE_FULL: u32 = 1 << 0;
pub(super) const PAUSE_SPELL: u32 = 1 << 1;
pub(super) const PAUSE_SPENT: u32 = 1 << 2;

/// The two spells' status id ranges, `(first, last)` inclusive.
///
/// Spelled here rather than imported so this module does not depend on the move
/// modules - `hero_side_b` is behind a Cargo feature, and the meter must behave
/// the same whether or not that feature is on. `install` asserts both against the
/// move modules' own constants, so a status allocation change fails at load
/// instead of quietly pausing on the wrong ids.
pub const NEUTRAL_SPELL: (i32, i32) = (0x1f5, 0x1f9);
pub const SIDE_SPELL: (i32, i32) = (0x1fa, 0x1fe);

/// One pair's meter. `current` holds f32 bits, as the rest of this crate does,
/// so the value can be shared with the HUD snapshot without a conversion.
pub struct Slot {
    current: AtomicU32,
    /// Passive-recovery countdown, compared against `params::RECOVER_FRAME`
    /// exactly as the donor compares its own counter.
    ticks: AtomicI32,
    /// 1 while this stock is spent, so a reset logs once per stock loss and not
    /// once per frame of the death animation.
    spent: AtomicI32,
    /// 1 once the first frame of this process has been seen for the pair, so a
    /// rematch that reuses the slot starts from the ceiling instead of
    /// inheriting the last stock's MP.
    seeded: AtomicI32,
    /// Battle object id of the half that last advanced the meter. Label only.
    owner: AtomicU32,
    /// Token of the most recent cast, and whether that cast was affordable.
    /// The donor's `FLAG_SUCCESS_SP`, owned.
    cast_token: AtomicU64,
    cast_ok: AtomicI32,
    /// Token whose debit has already been taken, so a repeated callback for the
    /// same cast cannot spend twice.
    debited: AtomicU64,
    pause: AtomicU32,
    /// Ticks observed, for the rate line in the log.
    seen: AtomicU64,
    /// Ticks at the last rate line, for the same reason.
    reported: AtomicU64,
}
impl Slot {
    const fn new() -> Self {
        Slot {
            current: AtomicU32::new(0),
            ticks: AtomicI32::new(0),
            spent: AtomicI32::new(0),
            seeded: AtomicI32::new(0),
            owner: AtomicU32::new(u32::MAX),
            cast_token: AtomicU64::new(0),
            cast_ok: AtomicI32::new(0),
            debited: AtomicU64::new(0),
            pause: AtomicU32::new(0),
            seen: AtomicU64::new(0),
            reported: AtomicU64::new(0),
        }
    }
    fn current(&self) -> f32 {
        f32::from_bits(self.current.load(Ordering::Relaxed))
    }
    fn set_current(&self, value: f32) {
        self.current.store(value.to_bits(), Ordering::Relaxed);
    }
}

static SLOTS: [Slot; 8] = [
    Slot::new(), Slot::new(), Slot::new(), Slot::new(),
    Slot::new(), Slot::new(), Slot::new(), Slot::new(),
];

/// Range-check every pointer before reading it. The callers of this module pass
/// engine-owned accessors, but the check is cheap and this is a crash-tail log.
fn address_ok(address: usize, alignment: usize) -> bool {
    address >= 0x100000000 && address < 0x8000000000 && address % alignment == 0
}

/// This pair's slot, or `None` for anything that is not a c06/c07 half of it.
///
/// The gate is the same install-time costume filter every other override in this
/// crate uses, plus a runtime check so a caller can never be handed the wrong
/// fighter: category, kind, colour, and the entry id in range.
pub unsafe fn slot(boma: *mut BattleObjectModuleAccessor) -> Option<&'static Slot> {
    if !address_ok(boma as usize, 8) {
        return None;
    }
    if app::utility::get_category(&mut *boma) != *BATTLE_OBJECT_CATEGORY_FIGHTER {
        return None;
    }
    let kind = app::utility::get_kind(&mut *boma);
    if kind != *FIGHTER_KIND_ELIGHT && kind != *FIGHTER_KIND_EFLAME {
        return None;
    }
    if !crate::TARGET_COSTUMES.contains(&(WorkModule::get_int(
        boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR) as usize)) {
        return None;
    }
    entry(boma).map(|id| &SLOTS[id])
}

/// The player slot, which is the pair's identity across the swap.
pub unsafe fn entry(boma: *mut BattleObjectModuleAccessor) -> Option<usize> {
    let id = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
    if (0..8).contains(&id) {
        Some(id as usize)
    } else {
        None
    }
}

/// Which half of the pair this accessor is, for a log line.
fn form(boma: *mut BattleObjectModuleAccessor) -> &'static str {
    unsafe {
        if app::utility::get_kind(&mut *boma) == *FIGHTER_KIND_EFLAME {
            "pyra"
        } else {
            "mythra"
        }
    }
}

/// The pair's current MP, or the ceiling when the caller is not one of ours.
pub unsafe fn current(boma: *mut BattleObjectModuleAccessor) -> f32 {
    slot(boma).map_or(params::SP_MAX, |s| s.current())
}

/// The pair's ceiling.
#[allow(dead_code)]
pub fn max() -> f32 {
    params::SP_MAX
}

/// `(current, max)` for the HUD layer. Immutable, so the renderer can read it
/// without touching this module's state.
pub unsafe fn snapshot(boma: *mut BattleObjectModuleAccessor) -> (f32, f32) {
    (current(boma), params::SP_MAX)
}

/// The donor's `add_sp`, in owned arithmetic.
///
/// * a positive delta below `params::ADD_EPSILON` is not applied at all, which is
///   the guard measured at `main+0x853890`;
/// * a negative delta larger in magnitude than the current value is replaced by
///   zero before the clamp, so MP cannot go negative;
/// * the result is clamped to `[0, max]`, which is the donor's clamp.
fn add(s: &Slot, delta: f32) -> f32 {
    let before = s.current();
    let mut amount = delta;
    if amount > 0.0 && amount < params::ADD_EPSILON {
        return before;
    }
    if amount < 0.0 && -amount > before {
        amount = 0.0;
    }
    let after = (before + amount).clamp(0.0, params::SP_MAX);
    s.set_current(after);
    after
}

/// Open a cast and return its token.
///
/// The donor calls its gate once per cast from the attack / SHOOT MAIN. Doing it
/// the same way here is what keeps a second callback for the same cast - an
/// inherited motion, a repeated `Main`, the finisher - from spending twice:
/// `try_spend` only debits a token it has not debited before.
pub unsafe fn begin_cast(boma: *mut BattleObjectModuleAccessor, label: &str, price: f32) -> u64 {
    let Some(s) = slot(boma) else { return 0 };
    let token = s.cast_token.fetch_add(1, Ordering::Relaxed) + 1;
    s.cast_ok.store(0, Ordering::Relaxed);
    crate::diagnostic!(logging::log(format!(
        "CAST entry={} form={} label={} price={} mp={:.1}",
        entry(boma).unwrap_or(99), form(boma), label, price, s.current()
    )));
    token
}

/// The donor's gate plus debit, in one call.
///
/// `price <= current` is the donor's comparison (`FUN_0001a230`), and the debit
/// happens only on success (`FUN_00016db0`). Returns whether the cast may
/// proceed; on `false` nothing was spent and the caller must not create its
/// projectile, sparks or lightning.
pub unsafe fn try_spend(
    boma: *mut BattleObjectModuleAccessor,
    token: u64,
    price: f32,
    label: &str,
) -> bool {
    let Some(s) = slot(boma) else {
        // Not our pair: the moves are gated, so reaching here means the gate
        // changed under us. Spend nothing and let the move run, which is the
        // behaviour of the mana-off build this replaces.
        return true;
    };
    if token != 0 && s.debited.load(Ordering::Relaxed) == token {
        // Same cast, second callback. The donor debits once in the MAIN body;
        // re-debiting here would charge twice for one spell.
        crate::diagnostic!(logging::log(format!(
            "DEBIT-SUPPRESSED label={} token={} mp={:.1}", label, token, s.current()
        )));
        return s.cast_ok.load(Ordering::Relaxed) != 0;
    }
    let before = s.current();
    if price <= before {
        if token != 0 {
            s.debited.store(token, Ordering::Relaxed);
        }
        s.cast_ok.store(1, Ordering::Relaxed);
        let after = add(s, -price);
        crate::diagnostic!(logging::log(format!(
            "SPEND entry={} form={} label={} price={} {} -> {:.1}",
            entry(boma).unwrap_or(99), form(boma), label, price, before, after
        )));
        true
    } else {
        s.cast_ok.store(0, Ordering::Relaxed);
        crate::diagnostic!(logging::log(format!(
            "REFUSE entry={} form={} label={} price={} mp={:.1} short={:.1}",
            entry(boma).unwrap_or(99), form(boma), label, price, before, price - before
        )));
        // The donor's own "not enough MP" gauge flash (it raises event 0x5e).
        #[cfg(feature = "hero-mana-hud")]
        if let Some(id) = entry(boma) {
            hud::shortage(id);
        }
        false
    }
}

/// Whether the current cast was affordable, i.e. the owned `SUCCESS_SP`.
pub unsafe fn cast_ok(boma: *mut BattleObjectModuleAccessor) -> bool {
    slot(boma).map_or(true, |s| s.cast_ok.load(Ordering::Relaxed) != 0)
}

/// Is this accessor inside one of the Hero spells this crate owns?
///
/// The donor pauses its own passive recovery while the neutral-B HOLD is
/// charging (`DISABLE_SP_AUTO_RECOVER` in the pinned HOLD entry), because
/// charging is when the player is deciding whether to spend. The same pause
/// covers the side-B hold, whose own entry is a spell entry and must not refill
/// (contract: "Side-B `main_entry` means spell entry and MUST NOT refill MP").
fn casting(boma: *mut BattleObjectModuleAccessor) -> bool {
    unsafe {
        let status = StatusModule::status_kind(boma);
        (NEUTRAL_SPELL.0..=NEUTRAL_SPELL.1).contains(&status)
            || (SIDE_SPELL.0..=SIDE_SPELL.1).contains(&status)
            || status == *FIGHTER_STATUS_KIND_SPECIAL_N
            || status == *FIGHTER_STATUS_KIND_SPECIAL_S
    }
}

fn stock_spent(boma: *mut BattleObjectModuleAccessor) -> bool {
    unsafe {
        let status = StatusModule::status_kind(boma);
        status == *FIGHTER_STATUS_KIND_DEAD
            || status == *FIGHTER_STATUS_KIND_REBIRTH
            || status == *FIGHTER_STATUS_KIND_ENTRY
    }
}

/// Seed the pair's meter if this is the first frame it has been seen.
///
/// Without this a slot reused by a later match would inherit the previous
/// match's MP; every stock also goes through `DEAD`/`ENTRY`, which resets
/// anyway, but the seed makes a rematch safe even if the entry statuses change.
unsafe fn seed(s: &Slot) {
    if s.seeded.compare_exchange(0, 1, Ordering::Relaxed, Ordering::Relaxed).is_ok() {
        s.set_current(params::SP_MAX);
        s.ticks.store(0, Ordering::Relaxed);
        crate::diagnostic!(logging::log(format!("INIT mp={:.1} max={}", params::SP_MAX, params::SP_MAX)));
    }
}

/// One reset per stock loss. `DEAD` runs for many frames; the donor refills at
/// the stock boundary, not every frame of the death.
unsafe fn reset_stock(s: &Slot, why: &str) {
    if s.spent.swap(1, Ordering::Relaxed) == 0 {
        s.set_current(params::SP_MAX);
        s.ticks.store(0, Ordering::Relaxed);
        crate::diagnostic!(logging::log(format!("RESET by={} mp={:.1}", why, params::SP_MAX)));
    }
}

/// One passive-recovery advance, called once per frame for the active half.
unsafe fn advance(s: &Slot) {
    let before = s.current();
    if before >= params::SP_MAX {
        s.pause.fetch_or(PAUSE_FULL, Ordering::Relaxed);
        return;
    }
    let ticks = s.ticks.fetch_add(1, Ordering::Relaxed) + 1;
    if ticks >= params::RECOVER_FRAME {
        s.ticks.store(0, Ordering::Relaxed);
        let after = add(s, params::RECOVER_SP);
        crate::diagnostic!(logging::log(format!("RECOVER +{} {:.1} -> {:.1}", params::RECOVER_SP, before, after)));
    }
}

/// The per-frame callback. Registered for both halves of the pair, gated on the
/// c06/c07 entry, and it returns immediately for the dormant half.
unsafe extern "C" fn line(agent: &mut L2CAgent) {
    let object_id = (*agent.battle_object).battle_object_id;
    // The partner half of the pair is not the body standing there; only the
    // active one advances the shared meter.
    if !app::sv_battle_object::is_active(object_id) {
        return;
    }
    let boma = agent.module_accessor;
    let Some(s) = slot(boma) else { return };
    seed(s);
    s.owner.store(object_id, Ordering::Relaxed);

    let spent = stock_spent(boma);
    if spent {
        s.pause.fetch_or(PAUSE_SPENT, Ordering::Relaxed);
        #[cfg(feature = "hero-mana-hud")]
        if s.spent.load(Ordering::Relaxed) == 0 {
            if let Some(id) = entry(boma) { hud::reset(id); }
        }
        reset_stock(s, "stock");
        show(boma, s);
        return;
    }
    if s.spent.swap(0, Ordering::Relaxed) != 0 {
        crate::diagnostic!(logging::log(format!("STOCK-END mp={:.1}", s.current())));
    }

    if casting(boma) {
        s.pause.fetch_or(PAUSE_SPELL, Ordering::Relaxed);
    } else {
        s.pause.store(0, Ordering::Relaxed);
        advance(s);
    }
    show(boma, s);

    // One rate line per 60 observed frames, so the log shows how fast the meter
    // actually advances without writing a line per frame.
    let seen = s.seen.fetch_add(1, Ordering::Relaxed) + 1;
    if seen - s.reported.load(Ordering::Relaxed) >= params::RECOVER_FRAME as u64 {
        s.reported.store(seen, Ordering::Relaxed);
        let (mp, ceiling) = snapshot(boma);
        crate::diagnostic!(logging::log(format!(
            "TICK entry={} form={} frames={} mp={:.1}/{:.1} pause={:#x}",
            entry(boma).unwrap_or(99), form(boma), seen, mp, ceiling,
            s.pause.load(Ordering::Relaxed)
        )));
    }
}

/// Put the meter on the player's fighter HUD. A no-op without `hero-mana-hud`.
#[allow(unused_variables)]
unsafe fn show(boma: *mut BattleObjectModuleAccessor, s: &Slot) {
    #[cfg(feature = "hero-mana-hud")]
    if let Some(id) = entry(boma) {
        hud::frame(id, form(boma), s.current());
    }
}

pub fn install() {
    assert_eq!(
        NEUTRAL_SPELL.0, crate::mythra::hero_neutral_b::START,
        "hero_mana's neutral-B status range no longer matches the move's allocation"
    );
    assert_eq!(
        NEUTRAL_SPELL.1, crate::mythra::hero_neutral_b::SHOOT,
        "hero_mana's neutral-B status range no longer matches the move's allocation"
    );
    #[cfg(feature = "hero-side-b")]
    {
        assert_eq!(
            SIDE_SPELL.0, crate::mythra::hero_side_b::SPELL_SPAN.0,
            "hero_mana's side-B status range no longer matches the move's allocation"
        );
        assert_eq!(
            SIDE_SPELL.1, crate::mythra::hero_side_b::SPELL_SPAN.1,
            "hero_mana's side-B status range no longer matches the move's allocation"
        );
    }
    crate::diagnostic!(println!(
        "{} Hero mana: pair meter max={} prices N[{}, {}, {}] S[{}, {}, {}] \
         recover=+{} every {} frames (owned, no Hero work ids); \
         fighter HUD gauge: feature hero-mana-hud; hit-recovery stays reserved \
         behind hero-mana-reserved",
        crate::LOG, params::SP_MAX,
        params::PRICE_NEUTRAL[0], params::PRICE_NEUTRAL[1], params::PRICE_NEUTRAL[2],
        params::PRICE_SIDE[0], params::PRICE_SIDE[1], params::PRICE_SIDE[2],
        params::RECOVER_SP, params::RECOVER_FRAME
    ));
    unsafe {
        // Both halves, so the meter follows the pair through the down-B swap.
        for kind in ["eflame", "elight"] {
            let mut agent = Agent::new(kind);
            agent.set_costume(crate::TARGET_COSTUMES.to_vec());
            agent.on_line(Main, line);
            agent.install();
        }
    }
    crate::diagnostic!(logging::log(format!(
        "REGISTERED max={} recover_frame={} recover_sp={} \
         hit_mul={} shield_mul={} \
         keys max={:#x} n=[{:#x},{:#x},{:#x}] s=[{:#x},{:#x},{:#x}]",
        params::SP_MAX, params::RECOVER_FRAME, params::RECOVER_SP,
        params::RECOVER_DAMAGE_MUL, params::RECOVER_SHIELD_MUL,
        params::keys::SP_MAX,
        params::keys::SP_SPECIAL_N1, params::keys::SP_SPECIAL_N2, params::keys::SP_SPECIAL_N3,
        params::keys::SP_SPECIAL_S1, params::keys::SP_SPECIAL_S2, params::keys::SP_SPECIAL_S3
    )));
    #[cfg(feature = "hero-mana-hud")]
    hud::install();
    #[cfg(not(feature = "hero-mana-hud"))]
    crate::diagnostic!(logging::log("HUD absent: built without the hero-mana-hud feature"));
}
