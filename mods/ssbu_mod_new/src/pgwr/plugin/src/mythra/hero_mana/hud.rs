//! The pair's MP on the **real fighter HUD**: the game's own MP gauge, on the
//! player's own damage panel. Cargo feature `hero-mana-hud` (2026-10-03).
//!
//! Not a world effect and not a new layout: the vanilla fighter panel already
//! carries Hero's MP gauge for *every* player (`brave_ui_ctor` is run by the
//! panel constructor whatever the fighter), and the game itself switches it on
//! for a fighter that is not Hero - that is what Kirby's panel does when Kirby
//! copies Hero. This module asks the game to do the same thing for a c06/c07
//! Pyra/Mythra panel, with the game's own functions, and then feeds the gauge the
//! pair's owned meter through the HUD's own SP setters.
//!
//! # Route (tier B: read out of the 13.0.4 image, see `refs/brave_special_n/hud_route/`)
//!
//! Nothing is hooked and no instruction is overwritten. Three things are *called*:
//!
//! * `panel_select_part(gauge, chara, copy)` (`main+0x1426fb0`) - the panel's own
//!   part selector. Given Hero's chara id it selects part 8 (the MP gauge): the old
//!   part's reset, the brave part's init (which binds the gauge to this panel's
//!   layout row) and the layout part switch are all the game's.
//! * `H->vt[0x2e0](H, player, sp)` / `H->vt[0x2e8](H, player, sp)` - the HUD's own
//!   "set SP" and "animate to this SP total", which is exactly what
//!   `FighterSpecializer_Brave::set_sp` reaches through FighterManager events
//!   0x5c / 0x5d. They map the player to its panel themselves.
//! * `H->vt[0x2f0](H, player)` - the donor's "not enough MP" flash (event 0x5e).
//!
//! # Player to panel, and why nothing is assumed about four panels
//!
//! The entry's HUD player id is read where the donor reads it (FighterManager
//! entry object `+0x41e4`, gated by the byte at `+0x41e8`). The HUD object `H` is
//! found the way the event dispatch finds it: the delegate the HUD registered on
//! event 0x5c. The panel is then located by repeating `hud_sp_set`'s own walk -
//! player -> view handle -> panel index (the game bounds it by 8) -> panel - and
//! the gauge object is `panel + 8`, which is what the game itself passes to the
//! selector (`panel_reselect_part`). Teams, reordering and 1..8 players are the
//! game's mapping, not this module's.
//!
//! # Lifecycle
//!
//! No pointer is kept across a frame. Every frame the whole chain is derived
//! again from the two globals and every dereference is checked with
//! `svcQueryMemory` first, so a HUD that is being torn down or rebuilt is either
//! found afresh or not found at all. A form swap makes the game re-select the
//! panel's part for the new fighter kind, which takes the gauge away; the next
//! frame sees a null part and selects it again, and the value is pushed again.
//!
//! # Refusal
//!
//! `install` hashes every function this route depends on (`hud_signatures.rs`,
//! generated and checked by `tools/audit_hero_mana_native.py`) and compares the
//! vtable slots it will call through. Any mismatch leaves this module disabled
//! and changes nothing else: the meter, the spells and every other HUD work as
//! without the feature. At run time an unexpected structure (another HUD class,
//! a panel whose brave part is not where 13.0.4 puts it, a part that is neither
//! empty nor the MP gauge) refuses for that player only and says so once.
//!
//! Vanilla costumes never reach this module (`super::slot` gates on c06/c07),
//! real Hero's and every other player's panel is never looked at, and nothing is
//! written to game memory by this file - the game's own functions do the writes.
//!
//! **Unverified: everything about behaviour.** No console or emulator run exists.
use super::logging::log;
use std::sync::atomic::{AtomicBool, AtomicI32, AtomicU32, AtomicUsize, Ordering};

#[path = "hud_signatures.rs"]
mod signatures;

// ---- 13.0.4 image offsets. Every function named here is hashed by `install`. ----

/// `*(*(main + this))` is the FighterManager (`brave_set_sp_sender`).
const FIGHTER_MANAGER_REF: usize = 0x52b_84f8;
/// HUD root singleton read by every `hud_sp_*` handler.
const HUD_ROOT: usize = 0x52c_2420;
/// Mode object the handlers consult before touching a panel.
const MODE_ROOT: usize = 0x532_e8b0;
/// The callback of the delegate the HUD registers on event 0x5c.
const DELEGATE_SP_SET: usize = 0x137_8650;
/// The two HUD classes that share `hud_sp_set` / `hud_sp_add` / `hud_sp_short`.
const HUD_CLASS: [usize; 2] = [0x506_1780, 0x506_1ba0];
const PANEL_SELECT_PART: usize = 0x142_6fb0;
const BRAVE_PART_VTABLE: usize = 0x506_5d58;
const SP_QUEUE_DESCRIPTOR: usize = 0x506_4f78;

// ---- layouts, each read out of the function named beside it ----

const EVENT_SP_SET: usize = 0x5c;
const EVENT_KINDS_MIN: u32 = 0x5f; // the donor raises 0x5e only when the count is >= 0x5f
const FM_LISTS: usize = 0x8; // FighterManager -> listener lists
const FM_ENTRIES: usize = 0x20; // + 8 * entry -> entry object
const ENTRY_HUD_PLAYER: usize = 0x41e4;
const ENTRY_HUD_FLAG: usize = 0x41e8;
const HUD_PLAYER_TABLE: usize = 0x18; // H -> table, stride 0x260, view index at +0xc
const HUD_PLAYER_STRIDE: usize = 0x260;
const HUD_DEFAULT_VIEW: usize = 0xc50;
const HUD_VIEW_ARRAY: usize = 0xc68;
const VIEW_ACTIVE: usize = 0x70;
const VIEW_INNER: usize = 0xb0;
const INNER_PANELS: usize = 0x1910;
const PANEL_STRIDE: usize = 0x3e0;
const PANEL_GAUGE: usize = 0x8;
const GAUGE_PART: usize = 0x8;
const GAUGE_BRAVE_PART: usize = 0x300;
const GAUGE_BRAVE_UI: usize = 0x310;
const GAUGE_PANEL_INDEX: usize = 0x390;
const GAUGE_LAYOUT: usize = 0x398;
const LAYOUT_ROWS: usize = 0x80;
const ROW_STRIDE: usize = 0xd90;
const ROW_BRAVE_BINDING: usize = 0xf78;
const BRAVE_UI_STATE: usize = 0x28;
const STATE_QUEUE_DESCRIPTOR: usize = 0xd0;
const STATE_QUEUE_CAPACITY: usize = 0xd8;
const STATE_QUEUE_BUFFER: usize = 0xf8;
const STATE_TARGET: usize = 0x258;
const STATE_SIZE: usize = 0x280;
const PANELS: i32 = 8; // the game's own bound in every handler

/// Hero's chara id as the selector takes it: tag 0xc1, an index hint that is
/// out of range on purpose (`ui_chara_kind` then searches by hash), and
/// `hash40("ui_chara_brave")`.
const CHARA_TAG: u64 = 0xc1ff_ff00_0000_0000;
const CHARA_BRAVE: u64 = CHARA_TAG | 0x0e_29e0_5d6a;
/// The game's own "no copy ability" argument (`panel_reselect_part`).
const CHARA_NONE: u64 = CHARA_TAG;

// ---- bounded behaviour ----

/// Frames between two part selections for one player.
const SELECT_COOLDOWN: i32 = 12;
/// More selections than this inside `THRASH_WINDOW` frames means the game keeps
/// taking the part away, and fighting it every frame would flicker.
const THRASH_LIMIT: u32 = 20;
const THRASH_WINDOW: u32 = 600;
/// Selections that left the part unselected before this player is given up.
const SELECT_FAILURES: u32 = 3;
/// Frames after a selection during which the value is set instantly, not animated.
const SET_FRAMES: i32 = 8;
/// BIND/REBIND and LOST lines written per player before only every 50th is.
const BIND_LINES: u32 = 40;

type SpSetter = unsafe extern "C" fn(*mut u8, i32, f32);
type SpShort = unsafe extern "C" fn(*mut u8, i32);
type SelectPart = unsafe extern "C" fn(*mut u8, u64, u64);

static ENABLED: AtomicBool = AtomicBool::new(false);

core::arch::global_asm!(
    ".section .text.pgwr_mana_hud_query_memory, \"ax\", %progbits",
    ".global pgwr_mana_hud_query_memory", ".hidden pgwr_mana_hud_query_memory",
    ".type pgwr_mana_hud_query_memory, %function", ".p2align 2",
    "pgwr_mana_hud_query_memory:", "str x1, [sp, #-16]!", "svc 0x6",
    "ldr x2, [sp], #16", "str w1, [x2]", "ret",
    ".size pgwr_mana_hud_query_memory, .-pgwr_mana_hud_query_memory",
);
extern "C" {
    fn pgwr_mana_hud_query_memory(info: *mut u64, page: *mut u32, address: usize) -> u32;
}

/// Is `[address, address + size)` readable memory? Rule 25: every pointer this
/// module follows is checked before it is read.
unsafe fn mapped(address: usize, size: usize) -> bool {
    let Some(end) = address.checked_add(size) else { return false };
    if address < 0x10000 || size == 0 {
        return false;
    }
    let mut info = [0u64; 6];
    let mut page = 0;
    pgwr_mana_hud_query_memory(info.as_mut_ptr(), &mut page, address) == 0
        && info[3] as u32 & 1 != 0
        && address as u64 >= info[0]
        && end as u64 <= info[0].saturating_add(info[1])
}

unsafe fn read<T: Copy>(address: usize) -> Option<T> {
    if address % std::mem::align_of::<T>() != 0 || !mapped(address, std::mem::size_of::<T>()) {
        return None;
    }
    Some(*(address as *const T))
}

/// A pointer field: readable, non-null and 8-aligned.
unsafe fn pointer(address: usize) -> Option<usize> {
    read::<usize>(address).filter(|p| *p != 0 && *p % 8 == 0)
}

fn base() -> usize {
    unsafe { crate::article::game_base() as usize }
}

fn fnv1a64(bytes: &[u8]) -> u64 {
    let mut hash = 0xcbf2_9ce4_8422_2325u64;
    for byte in bytes {
        hash = (hash ^ *byte as u64).wrapping_mul(0x100_0000_01b3);
    }
    hash
}

/// Why a frame did nothing. The first three are ordinary (no battle HUD right
/// now); the rest are refusals and are logged once per player.
#[derive(Clone, Copy, PartialEq)]
enum Miss {
    NoManager,
    NoPlayer,
    NoHud,
    HudClass,
    View,
    Panel,
    Gauge,
    State,
    Binding,
}
impl Miss {
    fn refusal(self) -> Option<(u32, &'static str)> {
        match self {
            Miss::NoManager | Miss::NoPlayer | Miss::NoHud => None,
            Miss::HudClass => Some((1 << 0, "the HUD object is not one of the two 13.0.4 classes this route knows")),
            Miss::View => Some((1 << 1, "the player's view handle did not resolve as hud_sp_set resolves it")),
            Miss::Panel => Some((1 << 2, "panel index or panel array out of the game's own bounds")),
            Miss::Gauge => Some((1 << 3, "the panel's brave part is not where 13.0.4 puts it")),
            Miss::State => Some((1 << 4, "the panel's SP state is not the 13.0.4 object")),
            Miss::Binding => Some((1 << 5, "the panel's layout row has no MP gauge binding")),
        }
    }
}
const REFUSED_OTHER_PART: u32 = 1 << 6;

/// Everything one frame needs, derived from the globals this frame.
struct Found {
    hud: usize,
    class: usize,
    player: i32,
    panel_index: i32,
    gauge: usize,
    state: usize,
}

/// The HUD object, through the delegate it registered on event 0x5c
/// (`fm_listener_registration`, `fm_delegate_sp_set`, `fm_delegate_invoke`).
unsafe fn hud_object(manager: usize) -> Result<(usize, usize), Miss> {
    if read::<u32>(manager).ok_or(Miss::NoManager)? < EVENT_KINDS_MIN {
        return Err(Miss::NoHud);
    }
    let lists = pointer(manager + FM_LISTS).ok_or(Miss::NoHud)?;
    let head = lists + EVENT_SP_SET * 0x18 + 8;
    let mut node = pointer(head).ok_or(Miss::NoHud)?;
    // The list is circular through `head`; 64 is far above any listener count
    // and bounds the walk if the list is not what it should be.
    for _ in 0..64 {
        if node == head {
            break;
        }
        if let Some(delegate) = pointer(node + 0x10) {
            if read::<usize>(delegate + 0x18) == Some(base() + DELEGATE_SP_SET)
                && read::<usize>(delegate + 0x20) == Some(0)
            {
                let owner = pointer(delegate + 0x10).ok_or(Miss::NoHud)?;
                let hud = pointer(owner + 0x20).ok_or(Miss::NoHud)?;
                let vtable = read::<usize>(hud).ok_or(Miss::NoHud)?;
                return match HUD_CLASS.iter().position(|c| base() + *c == vtable) {
                    Some(class) => Ok((hud, class)),
                    None => Err(Miss::HudClass),
                };
            }
        }
        node = pointer(node).ok_or(Miss::NoHud)?;
    }
    Err(Miss::NoHud)
}

/// The panel of `player`, by `hud_sp_set`'s own walk.
unsafe fn locate(entry: usize) -> Result<Found, Miss> {
    let manager = pointer(base() + FIGHTER_MANAGER_REF)
        .and_then(|reference| pointer(reference))
        .ok_or(Miss::NoManager)?;
    let entry_object = pointer(manager + FM_ENTRIES + 8 * entry).ok_or(Miss::NoPlayer)?;
    if read::<u8>(entry_object + ENTRY_HUD_FLAG).ok_or(Miss::NoPlayer)? == 0 {
        return Err(Miss::NoPlayer);
    }
    let player = read::<i32>(entry_object + ENTRY_HUD_PLAYER).ok_or(Miss::NoPlayer)?;
    if !(0..PANELS).contains(&player) {
        return Err(Miss::NoPlayer);
    }
    let (hud, class) = hud_object(manager)?;

    let root = pointer(base() + HUD_ROOT).ok_or(Miss::NoHud)?;
    let views = pointer(root + 8).and_then(|p| pointer(p)).ok_or(Miss::NoHud)?;
    let table = pointer(hud + HUD_PLAYER_TABLE).ok_or(Miss::View)?;
    let view_index = read::<i32>(table + player as usize * HUD_PLAYER_STRIDE + 0xc).ok_or(Miss::View)?;
    let handle = match view_index {
        -1 => views + HUD_DEFAULT_VIEW,
        0..=7 => pointer(views + HUD_VIEW_ARRAY + 8 * view_index as usize).ok_or(Miss::View)?,
        _ => return Err(Miss::View),
    };
    // `hud_handle_valid`: a null view, an inactive view or panel index -1 is "no
    // HUD for this player right now", not a fault.
    let view = match read::<usize>(handle + 8).ok_or(Miss::View)? {
        0 => return Err(Miss::NoHud),
        slot => pointer(slot).ok_or(Miss::View)?,
    };
    if read::<u8>(view + VIEW_ACTIVE).ok_or(Miss::View)? == 0 {
        return Err(Miss::NoHud);
    }
    let panel_index = read::<i32>(handle + 0x14).ok_or(Miss::View)?;
    if panel_index == -1 {
        return Err(Miss::NoHud);
    }
    // The handlers leave the panel alone in this mode; so does this module.
    if let Some(mode) = read::<usize>(base() + MODE_ROOT).filter(|p| *p != 0) {
        if let Some(inner) = pointer(mode + 8) {
            if read::<u32>(inner + 0x138).unwrap_or(0) != 0
                && read::<u8>(inner + 0x2b8).unwrap_or(0) == 0xb
            {
                return Err(Miss::NoHud);
            }
        }
    }
    if !(0..PANELS).contains(&panel_index) {
        return Err(Miss::Panel);
    }
    let panels = pointer(view + VIEW_INNER)
        .and_then(|inner| pointer(inner + INNER_PANELS))
        .ok_or(Miss::Panel)?;
    let gauge = panels + panel_index as usize * PANEL_STRIDE + PANEL_GAUGE;
    if !mapped(gauge, PANEL_STRIDE - PANEL_GAUGE) {
        return Err(Miss::Panel);
    }

    // The gauge must be the 13.0.4 object: its brave part embedded at +0x300
    // with this gauge as owner, and its own panel index equal to the one the
    // view handle gave.
    if read::<usize>(gauge + GAUGE_BRAVE_PART) != Some(base() + BRAVE_PART_VTABLE)
        || read::<usize>(gauge + GAUGE_BRAVE_PART + 8) != Some(gauge)
        || read::<i32>(gauge + GAUGE_PANEL_INDEX) != Some(panel_index)
    {
        return Err(Miss::Gauge);
    }
    let ui = pointer(gauge + GAUGE_BRAVE_UI).ok_or(Miss::Gauge)?;
    let state = pointer(ui + BRAVE_UI_STATE).ok_or(Miss::State)?;
    if !mapped(state, STATE_SIZE)
        || read::<usize>(state + STATE_QUEUE_DESCRIPTOR) != Some(base() + SP_QUEUE_DESCRIPTOR)
        || read::<u64>(state + STATE_QUEUE_CAPACITY) != Some(12)
        || read::<usize>(state + STATE_QUEUE_BUFFER) != Some(state + 0x100)
    {
        return Err(Miss::State);
    }
    Ok(Found { hud, class, player, panel_index, gauge, state })
}

/// The MP gauge's layout binding for this panel must exist before the brave part
/// is initialised on it (`brave_part_init` binds row + 0xf78, `brave_ui_setup`
/// then reads through it unconditionally).
unsafe fn binding_present(found: &Found) -> bool {
    let Some(rows) = pointer(found.gauge + GAUGE_LAYOUT).and_then(|l| pointer(l + LAYOUT_ROWS))
    else {
        return false;
    };
    let field = rows + found.panel_index as usize * ROW_STRIDE + ROW_BRAVE_BINDING;
    matches!(pointer(field), Some(layout) if mapped(layout, 0x1a0))
}

unsafe fn vcall<T: Copy>(object: usize, slot: usize) -> T {
    let vtable = *(object as *const usize);
    std::mem::transmute_copy::<usize, T>(&*((vtable + slot) as *const usize))
}

/// Per-player bookkeeping. Counters and log gates only - never a game pointer
/// that is used again (`gauge` is compared, not followed).
struct Player {
    bound: AtomicBool,
    dead: AtomicBool,
    refused: AtomicU32,
    frames: AtomicU32,
    cooldown: AtomicI32,
    set_frames: AtomicI32,
    selects: AtomicU32,
    failures: AtomicU32,
    losts: AtomicU32,
    window_start: AtomicU32,
    window_selects: AtomicU32,
    gauge: AtomicUsize,
}
impl Player {
    const fn new() -> Self {
        Player {
            bound: AtomicBool::new(false),
            dead: AtomicBool::new(false),
            refused: AtomicU32::new(0),
            frames: AtomicU32::new(0),
            cooldown: AtomicI32::new(0),
            set_frames: AtomicI32::new(0),
            selects: AtomicU32::new(0),
            failures: AtomicU32::new(0),
            losts: AtomicU32::new(0),
            window_start: AtomicU32::new(0),
            window_selects: AtomicU32::new(0),
            gauge: AtomicUsize::new(0),
        }
    }
    fn refuse_once(&self, entry: usize, bit: u32, why: &str) {
        if self.refused.fetch_or(bit, Ordering::Relaxed) & bit == 0 {
            crate::diagnostic!(log(format!("HUD REFUSED entry={} reason={}", entry, why)));
        }
    }
    fn off(&self, entry: usize, why: &str) {
        if !self.dead.swap(true, Ordering::Relaxed) {
            crate::diagnostic!(log(format!("HUD OFF entry={} reason={} (meter and spells unaffected)", entry, why)));
        }
    }
}
static PLAYERS: [Player; 8] = [
    Player::new(), Player::new(), Player::new(), Player::new(),
    Player::new(), Player::new(), Player::new(), Player::new(),
];

/// Stock/entry boundary: discard diagnostic state, never follow an old pointer.
/// Called once by the owned meter's boundary latch; swaps do not reset this.
pub(super) fn reset(entry: usize) {
    let Some(me) = PLAYERS.get(entry) else { return };
    me.bound.store(false, Ordering::Relaxed);
    me.dead.store(false, Ordering::Relaxed);
    me.refused.store(0, Ordering::Relaxed);
    me.frames.store(0, Ordering::Relaxed);
    me.cooldown.store(0, Ordering::Relaxed);
    me.set_frames.store(SET_FRAMES, Ordering::Relaxed);
    me.window_start.store(0, Ordering::Relaxed);
    me.window_selects.store(0, Ordering::Relaxed);
    me.failures.store(0, Ordering::Relaxed);
    me.gauge.store(0, Ordering::Relaxed);
}

/// One frame for the active half of a c06/c07 pair: make sure the panel shows
/// the MP gauge, and make the gauge show `mp`.
pub(super) unsafe fn frame(entry: usize, form: &str, mp: f32) {
    if !ENABLED.load(Ordering::Acquire) || entry >= PLAYERS.len() {
        return;
    }
    let me = &PLAYERS[entry];
    if me.dead.load(Ordering::Relaxed) {
        return;
    }
    let now = me.frames.fetch_add(1, Ordering::Relaxed) + 1;
    if me.cooldown.load(Ordering::Relaxed) > 0 {
        me.cooldown.fetch_sub(1, Ordering::Relaxed);
    }

    let found = match locate(entry) {
        Ok(found) => found,
        Err(miss) => {
            if let Some((bit, why)) = miss.refusal() {
                me.refuse_once(entry, bit, why);
            }
            if me.bound.swap(false, Ordering::Relaxed) {
                let count = me.losts.fetch_add(1, Ordering::Relaxed) + 1;
                if count <= BIND_LINES || count % 50 == 0 {
                    crate::diagnostic!(log(format!("HUD LOST entry={} count={} (battle HUD gone, hidden or rebuilt)",
                                entry, count)));
                }
            }
            return;
        }
    };

    let brave_part = found.gauge + GAUGE_BRAVE_PART;
    let part = read::<usize>(found.gauge + GAUGE_PART).unwrap_or(usize::MAX);
    if part != brave_part {
        if part != 0 {
            // Neither empty nor the MP gauge: some other fighter part owns this
            // panel. Not expected for eflame/elight; leave it alone.
            me.refuse_once(entry, REFUSED_OTHER_PART, "the panel already shows another fighter part");
            return;
        }
        if me.cooldown.load(Ordering::Relaxed) > 0 {
            return;
        }
        if !binding_present(&found) {
            if let Some((bit, why)) = Miss::Binding.refusal() {
                me.refuse_once(entry, bit, why);
            }
            return;
        }
        // Rate limit: the game takes the part away on a form swap, which is one
        // selection each. A burst is something else, and is not fought.
        if now.wrapping_sub(me.window_start.load(Ordering::Relaxed)) > THRASH_WINDOW {
            me.window_start.store(now, Ordering::Relaxed);
            me.window_selects.store(0, Ordering::Relaxed);
        }
        if me.window_selects.fetch_add(1, Ordering::Relaxed) + 1 > THRASH_LIMIT {
            me.off(entry, "the game keeps removing the MP gauge part");
            return;
        }
        me.cooldown.store(SELECT_COOLDOWN, Ordering::Relaxed);

        let select: SelectPart = std::mem::transmute(base() + PANEL_SELECT_PART);
        select(found.gauge as *mut u8, CHARA_BRAVE, CHARA_NONE);

        if read::<usize>(found.gauge + GAUGE_PART) != Some(brave_part) {
            let failures = me.failures.fetch_add(1, Ordering::Relaxed) + 1;
            crate::diagnostic!(log(format!(
                "HUD SELECT-FAILED entry={} player={} panel={} attempt={}",
                entry, found.player, found.panel_index, failures
            )));
            if failures >= SELECT_FAILURES {
                me.off(entry, "the part selector did not select the MP gauge for Hero's chara id");
            }
            return;
        }
        me.failures.store(0, Ordering::Relaxed);
        me.set_frames.store(SET_FRAMES, Ordering::Relaxed);
        let count = me.selects.fetch_add(1, Ordering::Relaxed) + 1;
        let unbound = !me.bound.swap(true, Ordering::Relaxed);
        let moved = me.gauge.swap(found.gauge, Ordering::Relaxed) != found.gauge;
        let first = unbound || moved;
        if count <= BIND_LINES || count % 50 == 0 {
            crate::diagnostic!(log(format!(
                "HUD {} entry={} form={} player={} panel={} class={} selects={} mp={:.1}",
                if first { "BIND" } else { "REBIND" }, entry, form, found.player,
                found.panel_index, if found.class == 0 { "a" } else { "b" }, count, mp
            )));
        }
    } else if !me.bound.swap(true, Ordering::Relaxed) {
        // Already selected (a HUD this module bound before a `LOST`).
        me.gauge.store(found.gauge, Ordering::Relaxed);
    }

    // Count observed frames, including frames whose MP is already current.
    // Otherwise the first eight later spells would all use the instant setter.
    let instant = me.set_frames.load(Ordering::Relaxed) > 0;
    if instant { me.set_frames.fetch_sub(1, Ordering::Relaxed); }
    // The gauge shows what its SP state targets; push only when that differs.
    let Some(target) = read::<f32>(found.state + STATE_TARGET) else { return };
    if target.to_bits() == mp.to_bits() {
        return;
    }
    if instant {
        let set: SpSetter = vcall(found.hud, 0x2e0);
        set(found.hud as *mut u8, found.player, mp);
    } else {
        // Animated, as the donor's own spend and recovery are. A repeated push
        // before the HUD consumed the last one is coalesced by `hud_sp_add_queue`.
        let add: SpSetter = vcall(found.hud, 0x2e8);
        add(found.hud as *mut u8, found.player, mp);
    }
}

/// The donor's "not enough MP" flash, for a refused cast.
pub(super) unsafe fn shortage(entry: usize) {
    if !ENABLED.load(Ordering::Acquire) || entry >= PLAYERS.len() {
        return;
    }
    let me = &PLAYERS[entry];
    if me.dead.load(Ordering::Relaxed) || !me.bound.load(Ordering::Relaxed) {
        return;
    }
    let Ok(found) = locate(entry) else { return };
    if read::<usize>(found.gauge + GAUGE_PART) != Some(found.gauge + GAUGE_BRAVE_PART) {
        return;
    }
    let short: SpShort = vcall(found.hud, 0x2f0);
    short(found.hud as *mut u8, found.player);
}

/// Hash every function the route depends on and compare the vtable slots it
/// calls through. A mismatch disables this module and nothing else.
pub(super) fn install() {
    let base = base();
    unsafe {
        for &(offset, length, expected, id) in signatures::SPANS {
            if !mapped(base + offset, length) {
                crate::diagnostic!(log(format!("HUD REFUSED signature {} at {:#x}: not readable; HUD gauge off", id, offset)));
                return;
            }
            let actual = fnv1a64(std::slice::from_raw_parts((base + offset) as *const u8, length));
            if actual != expected {
                crate::diagnostic!(log(format!(
                    "HUD REFUSED signature {} at {:#x}+{:#x}: {:#018x} != {:#018x}; HUD gauge off",
                    id, offset, length, actual, expected
                )));
                return;
            }
        }
        for &(slot, target, id) in signatures::SLOTS {
            if read::<usize>(base + slot) != Some(base + target) {
                crate::diagnostic!(log(format!("HUD REFUSED slot {} at {:#x}; HUD gauge off", id, slot)));
                return;
            }
        }
    }
    ENABLED.store(true, Ordering::Release);
    crate::diagnostic!(log(format!(
        "HUD READY route=game-part-selector spans={} slots={} chara={:#x} (no hook installed)",
        signatures::SPANS.len(), signatures::SLOTS.len(), CHARA_BRAVE
    )));
}
