#![feature(proc_macro_hygiene)]

//! `mii_customizer` 0.6.0 - character stat presets per saved Mii, chosen in the Mii maker
//! from a menu of things to customize.
//!
//! Stat engine (unchanged from 0.3.0), one hook: the float-param thunk `0x4e53e0`. For a request whose hash is one of the
//! field hashes of `sd:/ultimate/mii_customizer/presets.txt` (or `weight` /
//! `walk_speed_max`), with `x2 == 0`, coming from the work object of a fighter of an
//! accepted kind (Mii Gunner), it returns the value that
//! `sd:/ultimate/mii_customizer/loadouts.txt` gives that player's saved-fighter ID: an
//! explicit line first, else the value of the ID's preset. Every other request, and every
//! doubt, returns the original value. Design, offline checks and the reading guide for the
//! log: `research/P7-PRESET-ENGINE.md`; identity: `research/P4-OVERRIDE-SLICE.md`.
//!
//! Rules this file keeps:
//!   * the hook is installed only when the four instruction words at its site equal the
//!     audited ones (`logic::SITE_PARAM`), otherwise it is skipped and logged;
//!   * only fixed-size statics and atomics, no threads, no `unwrap`, no `panic!`, no
//!     `skyline::hook` macro (its generated code unwraps);
//!   * both files are read once, at load, before the hook exists;
//!   * a request for any other hash costs one bounded table lookup and a tail jump: no
//!     game call, no allocation, no file IO, no lock (`preset::FieldTable::find`);
//!   * a request with `x2 != 0` is counted and passed on by the same tail jump;
//!   * kind, category and entry id come from the pinned `skyline_smash` binding
//!     (`resolve`); nothing about a fighter is cached between requests;
//!   * the identity lookup runs under a per-thread re-entry guard that falls through to
//!     the original value;
//!   * the log gate is a try-lock taken only after the original has returned.
//!
//! Editor UI (`editor.rs` + the pure `ui.rs` / `list.rs` / `menu.rs`): six more hooks turn
//! the native headgear list of the Mii maker into the pages of "mod mode": a main page
//! with one row per entry of `sd:/ultimate/mii_customizer/menu.txt`, and per entry a
//! character page (0.4.0 had the character page only, which is still what opens without a
//! menu file). A decided row of the stats page is the edited Mii's preset: the store is
//! updated and `save_loadouts` is called. Design, proofs and the test plan:
//! `research/P11-MENU.md` (0.4.0: `research/P10-UI-SLICE.md`). The UI hooks are installed
//! only when every UI site and every probe matches the audited words and
//! `sd:/ultimate/mii_customizer/ui_off` does not exist; the stat engine does not depend on
//! them. `sd:/ultimate/mii_customizer/text_off` keeps the hooks and switches literal row
//! text off (rows then show their fallback labels).

mod editor;
mod list;
mod loadout;
mod logic;
mod menu;
pub mod moves;
mod names;
pub mod unit_tilt_down;
pub mod unit_tilt_up;
pub mod unit_smash_up;
pub mod unit_aerial_back_mario;
mod preset;
mod ui;

use core::arch::{asm, global_asm};
use core::cell::UnsafeCell;
use core::sync::atomic::{AtomicBool, AtomicU32, AtomicU64, AtomicUsize, Ordering};
use logic::{Enter, Facts, FieldFlags, Ident, LineBuf, SeenTable, Site, St, ThreadGuard};
use preset::{FIELDS, NAME_BUF};
use skyline::hooks::{getRegionAddress, A64HookFunction, Region};
use skyline::libc::c_void;
use smash::app::lua_bind::WorkModule;
use smash::app::{sv_battle_object, utility, BattleObjectModuleAccessor};
use smash::lib::lua_const::{
    BATTLE_OBJECT_CATEGORY_FIGHTER, FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID, FIGHTER_KIND_MIIGUNNER,
};

const LOG_TAG: &str = "mii_customizer";
const LOG_PATH: &str = "sd:/ultimate/mii_customizer_log.txt";
const PRESET_PATH: &str = "sd:/ultimate/mii_customizer/presets.txt";
const LOADOUT_PATH: &str = "sd:/ultimate/mii_customizer/loadouts.txt";
/// Written by `save_loadouts` only, in the folder of the loadout file.
const LOADOUT_TMP_PATH: &str = "sd:/ultimate/mii_customizer/loadouts.new";
const LIST_PATH: &str = "sd:/ultimate/mii_customizer/list.txt";
const MENU_PATH: &str = "sd:/ultimate/mii_customizer/menu.txt";
const NAMES_PATH: &str = "sd:/ultimate/mii_customizer/names.txt";
/// When this file exists no UI hook is installed (the stat engine still loads).
const UI_OFF_PATH: &str = "sd:/ultimate/mii_customizer/ui_off";
/// When this file exists rows keep their message labels: no literal text is set.
const TEXT_OFF_PATH: &str = "sd:/ultimate/mii_customizer/text_off";
const MINUS_OFF_PATH: &str = "sd:/ultimate/mii_customizer/minus_off";
const VARIANT: &str = "menu";

/// The audited sites, kept as records so the build check can find offsets and expected
/// words in the NRO: the stat hook, then the six UI hooks in `ui::UI_SITE_LIST` order.
#[used]
#[no_mangle]
pub static MC_SITES: [Site; 1 + ui::UI_SITES] = [
    logic::SITE_PARAM,
    ui::SITE_DISPATCH,
    ui::SITE_STATE5,
    ui::SITE_UNLISTED,
    ui::SITE_LABEL,
    ui::SITE_SORT,
    ui::SITE_ROWFILL,
];
const SITE_NAMES: [&str; 1 + ui::UI_SITES] =
    ["param", "ui_dispatch", "ui_state5", "ui_unlisted", "ui_label", "ui_sort", "ui_rowfill"];
/// Code the UI relies on without patching it; compared like a site before any UI hook is
/// installed.
#[used]
#[no_mangle]
pub static MC_PROBES: [Site; ui::PROBES] = ui::PROBE_LIST;

static BASE: AtomicUsize = AtomicUsize::new(0);
/// Trampoline to the original code. `A64HookFunction` writes it itself, before it patches
/// the site (research/P3-DIAG-PLUGIN.md, step 0c).
static ORIG_PARAM: AtomicUsize = AtomicUsize::new(0);

static LOG_BUSY: AtomicBool = AtomicBool::new(false);
static SEQ: AtomicU32 = AtomicU32::new(0);
static DROPPED: AtomicU32 = AtomicU32::new(0);
static ORIG_NULL: AtomicU32 = AtomicU32::new(0);

const COUNTER_ZERO: AtomicU32 = AtomicU32::new(0);
const WORD_ZERO: AtomicU64 = AtomicU64::new(0);
/// Requests for a known hash with `x2 == 0`.
static REQ_COUNT: AtomicU32 = AtomicU32::new(0);
/// Requests for a known hash with `x2 != 0` (passed through untouched).
static X2NZ_COUNT: AtomicU32 = AtomicU32::new(0);
/// Per field index: requests with `x2 == 0`, overridden requests, requests with `x2 != 0`.
static FIELD_REQ: [AtomicU32; FIELDS] = [COUNTER_ZERO; FIELDS];
static FIELD_OV: [AtomicU32; FIELDS] = [COUNTER_ZERO; FIELDS];
static FIELD_X2: [AtomicU32; FIELDS] = [COUNTER_ZERO; FIELDS];
/// The first `x2 != 0` request per field: its `x2` and return address, logged later from
/// a request that is allowed to log.
static X2_FIRST: FieldFlags = FieldFlags::new();
static X2_VALUE: [AtomicU64; FIELDS] = [WORD_ZERO; FIELDS];
static X2_LR: [AtomicU64; FIELDS] = [WORD_ZERO; FIELDS];
static X2_PENDING: AtomicU64 = AtomicU64::new(0);
/// Fields requested at least once with `x2 == 0`; for the once-per-field `RQ` line.
static RQ_FIRST: FieldFlags = FieldFlags::new();
/// Requests per outcome, indexed by `St as usize`.
static ST_COUNTS: [AtomicU32; logic::ST_COUNT] = [COUNTER_ZERO; logic::ST_COUNT];
const ST_ORDER: [St; logic::ST_COUNT] = [
    St::Ok, St::Off, St::Vtable, St::NoParent, St::BackPtr, St::Reentry, St::GuardFull, St::Category,
    St::RoundTrip, St::Category2, St::KindMismatch, St::EntryMismatch, St::EntryRange, St::NotGunner,
    St::NoSlotId, St::NoEntry,
];
/// Overridden requests per source, indexed by `loadout::Src as usize`.
static SRC_COUNTS: [AtomicU32; loadout::SRC_COUNT] = [COUNTER_ZERO; loadout::SRC_COUNT];
/// Logging only: which fighters were seen and which fields were reported for them.
static SEEN: SeenTable = SeenTable::new();

static PRESETS: preset::Presets = preset::Presets::new();
pub(crate) static STORE: loadout::Store = loadout::Store::new();
static GUARD: ThreadGuard = ThreadGuard::new();

/// Fixed file buffer. The two read buffers are one byte longer than their limit so that a
/// longer file is noticed. All three are touched only at load, on the loading thread
/// before the hook exists, and by `save_loadouts` under `SAVE_BUSY`.
struct Buf<const N: usize>(UnsafeCell<[u8; N]>);
unsafe impl<const N: usize> Sync for Buf<N> {}
static PRESET_BUF: Buf<{ preset::MAX_FILE + 1 }> = Buf(UnsafeCell::new([0; preset::MAX_FILE + 1]));
static LIST_BUF: Buf<{ list::MAX_FILE + 1 }> = Buf(UnsafeCell::new([0; list::MAX_FILE + 1]));
static MENU_BUF: Buf<{ menu::MAX_FILE + 1 }> = Buf(UnsafeCell::new([0; menu::MAX_FILE + 1]));
static FILE_BUF: Buf<{ loadout::MAX_FILE + 1 }> = Buf(UnsafeCell::new([0; loadout::MAX_FILE + 1]));
static SAVE_BUF: Buf<{ loadout::MAX_FILE }> = Buf(UnsafeCell::new([0; loadout::MAX_FILE]));
static SAVE_BUSY: AtomicBool = AtomicBool::new(false);

/// Every integer and float argument register, so the original sees what the caller
/// passed whatever its real signature is. x8 is not an input of the thunk (it overwrites
/// x8 before reading it).
type RawF32 = unsafe extern "C" fn(
    u64, u64, u64, u64, u64, u64, u64, u64, f64, f64, f64, f64, f64, f64, f64, f64,
) -> f32;

// Entry stub. The hook target is this hand-written function, not a Rust one.
//
// `mc_hook_param` (unchanged since 0.1.0, console-tested in gates 1 and 2) passes the
// caller's return address as a ninth integer argument on the stack and leaves x0-x7 /
// v0-v7 untouched on the way in; the Rust function returns the f32 result in s0. Reading
// x30 from inside a Rust function is not reliable here: with opt-level "z" the outliner
// inserted a `bl` before the read in the first 0.1.0 build (research/P3-DIAG-PLUGIN.md,
// 2.3).
global_asm!(
    r#"
    .section .text.mc_stubs, "ax", %progbits
    .balign 4
    .global mc_hook_param
    .hidden mc_hook_param
    .type mc_hook_param, %function
mc_hook_param:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    sub sp, sp, #16
    str x30, [sp]
    bl {param}
    add sp, sp, #16
    ldp x29, x30, [sp], #16
    ret
    "#,
    param = sym mc_param_impl,
);

extern "C" {
    fn mc_hook_param();
}

/// Append `bytes` (one or more complete lines) with one open/write/close.
/// Every error is ignored. Never waits: if another thread is writing, the lines are
/// dropped and counted (visible as `dropped=` in L5 and as a gap in `seq`).
fn emit(bytes: &[u8]) {
    use std::io::Write;

    if bytes.is_empty() {
        return;
    }
    if LOG_BUSY.swap(true, Ordering::Acquire) {
        DROPPED.fetch_add(1, Ordering::Relaxed);
        return;
    }
    if let Ok(mut file) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(LOG_PATH)
    {
        let _ = file.write_all(bytes);
        let _ = file.flush();
    }
    LOG_BUSY.store(false, Ordering::Release);
}

/// As [`emit`], for the few user-driven lines (editor UI, save): when another thread is
/// writing, retry for a bounded number of spins instead of dropping at once. Never called
/// from the per-request hook.
pub(crate) fn emit_wait(bytes: &[u8]) {
    let mut spins = 0u32;
    while LOG_BUSY.load(Ordering::Acquire) && spins < 2_000_000 {
        core::hint::spin_loop();
        spins += 1;
    }
    emit(bytes);
}

/// `mc|<event>|seq=<n>` - start of every line.
pub(crate) fn head<const N: usize>(out: &mut LineBuf<N>, event: &str) {
    let seq = SEQ.fetch_add(1, Ordering::Relaxed);
    out.s("mc|").s(event).s("|seq=").dec(seq as u64);
}

fn rel(addr: u64) -> u64 {
    addr.wrapping_sub(BASE.load(Ordering::Relaxed) as u64)
}

fn load32(cells: &[AtomicU32], index: usize) -> u64 {
    cells.get(index).map(|c| c.load(Ordering::Relaxed)).unwrap_or(0) as u64
}

fn bump(cells: &[AtomicU32], index: usize) {
    if let Some(cell) = cells.get(index) {
        cell.fetch_add(1, Ordering::Relaxed);
    }
}

/// The saved-fighter ID and the four special bytes of player `p` from the two static
/// tables. `None` when `p >= 8` or the module base is unknown.
pub(crate) unsafe fn read_player(p: u32) -> Option<(u32, [u8; 4])> {
    let base = BASE.load(Ordering::Relaxed);
    if base == 0 {
        return None;
    }
    let id_at = logic::id_addr(base, p)?;
    let sp_at = logic::special_addr(base, p)?;
    let id = core::ptr::read_volatile(id_at as *const u32);
    let sp = core::ptr::read_volatile(sp_at as *const [u8; 4]);
    Some((id, sp))
}

/// Unique per live thread and never 0: the thread pointer register.
#[inline(always)]
fn thread_id() -> u64 {
    let tid: u64;
    unsafe {
        asm!("mrs {}, tpidrro_el0", out(reg) tid, options(nomem, nostack, preserves_flags));
    }
    tid
}

/// `|preset=<name>` or `|preset=-`.
pub(crate) fn push_preset_name<const N: usize>(out: &mut LineBuf<N>, preset: Option<usize>) {
    let mut name = [0u8; NAME_BUF];
    let len = match preset {
        Some(preset) => PRESETS.name(preset, &mut name),
        None => 0,
    };
    out.s("|preset=");
    match name.get(..len) {
        Some(name) if len != 0 => out.bytes(name),
        _ => out.s("-"),
    };
}

fn push_totals<const N: usize>(out: &mut LineBuf<N>) {
    head(out, "L5");
    out.s("|req=").dec(REQ_COUNT.load(Ordering::Relaxed) as u64);
    out.s("|x2nz=").dec(X2NZ_COUNT.load(Ordering::Relaxed) as u64);
    out.s("|parents=").dec(SEEN.distinct() as u64);
    out.s("|parent_overflow=").dec(SEEN.overflow() as u64);
    out.s("|dropped=").dec(DROPPED.load(Ordering::Relaxed) as u64);
    out.s("|orig_null=").dec(ORIG_NULL.load(Ordering::Relaxed) as u64);
    // Requests per outcome; only non-zero ones are printed. `ok` = overridden.
    out.s("|st=");
    let mut any = false;
    for (st, counter) in ST_ORDER.iter().zip(ST_COUNTS.iter()) {
        let n = counter.load(Ordering::Relaxed);
        if n != 0 {
            if any {
                out.s(",");
            }
            any = true;
            out.s(st.name()).s(":").dec(n as u64);
        }
    }
    out.s("|src=explicit:").dec(load32(&SRC_COUNTS, loadout::Src::Explicit as usize));
    out.s(",preset:").dec(load32(&SRC_COUNTS, loadout::Src::Preset as usize));
    out.end_line();
}

/// `F5`: per known field hash, requests with `x2 == 0` / overridden / requests with
/// `x2 != 0`, since boot. A field that shows `0/0/0` in the last F5 line of a session was
/// not requested through this hook up to that line.
#[inline(never)]
fn emit_field_totals() {
    let mut out: LineBuf<2048> = LineBuf::new();
    head(&mut out, "F5");
    let count = PRESETS.fields.len();
    out.s("|n=").dec(count as u64);
    let mut field = 0;
    while field < count {
        out.s("|").hash40(PRESETS.fields.hash_of(field));
        out.s("=").dec(load32(&FIELD_REQ, field));
        out.s("/").dec(load32(&FIELD_OV, field));
        out.s("/").dec(load32(&FIELD_X2, field));
        field += 1;
    }
    out.end_line();
    emit(out.as_bytes());
}

/// `X2`: once per field, the first request that had `x2 != 0`.
#[inline(never)]
fn emit_x2_firsts() {
    let pending = X2_PENDING.swap(0, Ordering::AcqRel);
    let mut out: LineBuf<1024> = LineBuf::new();
    let mut field = 0;
    let mut lines = 0;
    while field < FIELDS {
        if pending & (1u64 << field) != 0 {
            // Eight lines fill the buffer; the rest wait for the next flush.
            if lines == 8 {
                X2_PENDING.fetch_or(pending >> field << field, Ordering::AcqRel);
                break;
            }
            lines += 1;
            head(&mut out, "X2");
            out.s("|h=").hash40(PRESETS.fields.hash_of(field));
            out.s("|x2=").hex(X2_VALUE.get(field).map(|c| c.load(Ordering::Relaxed)).unwrap_or(0));
            out.s("|ra=").hex(rel(X2_LR.get(field).map(|c| c.load(Ordering::Relaxed)).unwrap_or(0)));
            out.s("|passed_through=1");
            out.end_line();
        }
        field += 1;
    }
    emit(out.as_bytes());
}

// ---------------------------------------------------------------------------
// Identity of a parent, through the pinned skyline_smash binding only
// ---------------------------------------------------------------------------

/// Kind, category and entry id of the fighter whose module accessor is `parent`.
///
/// Called only after `logic::pointer_guard` passed, i.e. `parent` is the object that a
/// work object of vtable 0x4f89490 names as its parent and that points back to it at
/// +0x50 - the shape the exported `lua_bind` wrappers expect of a
/// `BattleObjectModuleAccessor*`.
///
/// Sources (all in skyline_smash 315e4e8, `src/cpp.rs` / `src/lua_const.rs`):
///   * `app::utility::get_category(&mut accessor)` - the binding's own inline reading of
///     its declared field `battle_object_id` (no game call);
///   * `app::sv_battle_object::{module_accessor, category, kind, entry_id}(id)` - exported;
///   * `app::utility::get_kind(&mut accessor)` - exported;
///   * `app::lua_bind::WorkModule::get_int(accessor, FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID)`
///     - exported.
/// Nothing that takes the accessor is called before the object registered under the id
/// is shown to be a fighter whose module accessor is this very pointer.
#[inline(never)]
unsafe fn resolve(parent: u64) -> Ident {
    let accessor = parent as *mut BattleObjectModuleAccessor;
    let fighter_cat = *BATTLE_OBJECT_CATEGORY_FIGHTER;
    let mut facts = Facts {
        fighter_cat,
        cat_accessor: utility::get_category(&mut *accessor),
        round_trip: false,
        cat_object: -1,
        kind_accessor: -1,
        kind_object: -2,
        entry_accessor: -1,
        entry_object: -2,
    };
    if facts.cat_accessor == fighter_cat {
        let id = (*accessor).battle_object_id;
        facts.round_trip = sv_battle_object::module_accessor(id) as u64 == parent;
        if facts.round_trip {
            facts.cat_object = sv_battle_object::category(id);
        }
        if facts.round_trip && facts.cat_object == fighter_cat {
            facts.kind_object = sv_battle_object::kind(id);
            facts.entry_object = sv_battle_object::entry_id(id);
            facts.kind_accessor = utility::get_kind(&mut *accessor);
            facts.entry_accessor = WorkModule::get_int(accessor, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
        }
    }
    logic::identify(&facts)
}

// ---------------------------------------------------------------------------
// The hook: float-param thunk 0x4e53e0
// ---------------------------------------------------------------------------

#[inline(always)]
unsafe fn call_param(
    x0: u64, x1: u64, x2: u64, x3: u64, x4: u64, x5: u64, x6: u64, x7: u64,
    d0: f64, d1: f64, d2: f64, d3: f64, d4: f64, d5: f64, d6: f64, d7: f64,
) -> f32 {
    let orig = ORIG_PARAM.load(Ordering::Relaxed);
    if orig != 0 {
        let f: RawF32 = core::mem::transmute(orig);
        return f(x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7);
    }
    // No trampoline: do what the four replaced instructions do.
    //   ldr x0,[x0,#0x38] ; ldr x8,[x0] ; ldr x3,[x8,#0x30] ; br x3
    ORIG_NULL.fetch_add(1, Ordering::Relaxed);
    let inner = core::ptr::read((x0 as usize).wrapping_add(0x38) as *const u64);
    let vtable = core::ptr::read(inner as usize as *const u64);
    let target = core::ptr::read((vtable as usize).wrapping_add(0x30) as *const usize);
    let f: RawF32 = core::mem::transmute(target);
    f(inner, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7)
}

/// Count a request for a known hash that has `x2 != 0`. Atomics only: this runs before
/// the original and must not disturb its arguments or make a call.
#[inline(always)]
fn note_x2(field: usize, x2: u64, lr: u64) {
    X2NZ_COUNT.fetch_add(1, Ordering::Relaxed);
    if let (Some(count), Some(value), Some(ra)) = (FIELD_X2.get(field), X2_VALUE.get(field), X2_LR.get(field)) {
        count.fetch_add(1, Ordering::Relaxed);
        if X2_FIRST.first(field) {
            value.store(x2, Ordering::Relaxed);
            ra.store(lr, Ordering::Relaxed);
            X2_PENDING.fetch_or(1u64 << field, Ordering::AcqRel);
        }
    }
}

unsafe extern "C" fn mc_param_impl(
    x0: u64, x1: u64, x2: u64, x3: u64, x4: u64, x5: u64, x6: u64, x7: u64,
    d0: f64, d1: f64, d2: f64, d3: f64, d4: f64, d5: f64, d6: f64, d7: f64,
    lr: u64,
) -> f32 {
    // Contract D. Every hash that is in no loaded file leaves here, by a tail jump to the
    // original. Kept free of anything that needs a stack frame: the rest lives in
    // `known_request`, which has the same signature so that it is reached by a tail jump
    // too and looks the field up again (known hashes only).
    if PRESETS.fields.find(x1).is_none() {
        return call_param(x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7);
    }
    known_request(x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7, lr)
}

/// A request whose hash is a known field hash.
#[inline(never)]
unsafe extern "C" fn known_request(
    x0: u64, x1: u64, x2: u64, x3: u64, x4: u64, x5: u64, x6: u64, x7: u64,
    d0: f64, d1: f64, d2: f64, d3: f64, d4: f64, d5: f64, d6: f64, d7: f64,
    lr: u64,
) -> f32 {
    let field = match PRESETS.fields.find(x1) {
        Some(field) => field,
        None => return call_param(x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7),
    };
    if x2 != 0 {
        note_x2(field, x2, lr);
        return call_param(x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7);
    }
    let orig = call_param(x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7);
    param_event(x0, x1, field, lr, orig)
}

/// Decide, log, and return the value the caller gets: the loadout value when every
/// condition holds, otherwise `orig`.
#[inline(never)]
unsafe fn param_event(x0: u64, hash: u64, field: usize, lr: u64, orig: f32) -> f32 {
    let total = REQ_COUNT.fetch_add(1, Ordering::Relaxed).wrapping_add(1);
    bump(&FIELD_REQ, field);

    // Condition 1. The original has just dereferenced x0, so [x0] and [x0+8] are
    // readable; [parent+0x50] is read only for the vtable whose constructor stores the
    // parent (0x688508-0x688584).
    let base = BASE.load(Ordering::Relaxed);
    let mut vt = 0u32;
    let mut parent = 0u64;
    let mut back = 0u64;
    if x0 != 0 {
        vt = logic::vtable_class(base, core::ptr::read_volatile(x0 as usize as *const u64));
        if vt != 0 {
            parent = core::ptr::read_volatile((x0 as usize).wrapping_add(8) as *const u64);
        }
        if vt == 1 && parent != 0 {
            back = core::ptr::read_volatile(
                (parent as usize).wrapping_add(logic::PARENT_WORK_OFFSET) as *const u64,
            );
        }
    }
    let mut ident = Ident::unknown(logic::pointer_guard(x0, vt, parent, back));

    // Condition 2, only when there is something to apply: without a usable loadout file
    // no game function is called from here.
    if ident.st == St::Ok {
        if STORE.len() == 0 {
            ident = Ident::unknown(St::Off);
        } else {
            match GUARD.enter(thread_id()) {
                Enter::Entered(slot) => {
                    ident = resolve(parent);
                    GUARD.leave(slot);
                }
                Enter::Reentry => ident = Ident::unknown(St::Reentry),
                Enter::Full => ident = Ident::unknown(St::GuardFull),
            }
        }
    }

    // Condition 3.
    let mut slot_id = 0u32;
    if ident.st == St::Ok {
        if let Some((id, _)) = read_player(ident.player as u32) {
            slot_id = id;
        }
    }
    let decision = logic::decide(&ident, &logic::ACCEPTED_KINDS, slot_id, &STORE, &PRESETS, field);
    let value = match decision.value {
        Some(v) => v,
        None => orig,
    };
    bump(&ST_COUNTS, decision.st as usize);
    if decision.value.is_some() {
        bump(&FIELD_OV, field);
        if let Some(src) = decision.src {
            bump(&SRC_COUNTS, src as usize);
        }
    }

    // The store generation is part of the key: after a choice in the editor the same
    // fighter is logged again (L3 / L4), and `set_preset` cleared the OV marks.
    let generation = (STORE.generation() as u64).wrapping_mul(0x9e37_79b9_7f4a_7c15);
    let seen = SEEN.observe(logic::seen_key(parent, &ident, slot_id) ^ (generation << 1), field);
    let first_apply = decision.value.is_some() && STORE.first_apply(decision.entry, field);
    let first_request = RQ_FIRST.first(field);
    let due = logic::totals_due(total);
    let x2_pending = X2_PENDING.load(Ordering::Relaxed) != 0;
    if !seen.log && !seen.is_new && !first_apply && !first_request && !due && !x2_pending {
        return value;
    }

    let src_name = match decision.src {
        Some(src) => src.name(),
        None => "-",
    };
    let mut out: LineBuf<1536> = LineBuf::new();
    if first_request {
        head(&mut out, "RQ");
        out.s("|h=").hash40(hash);
        out.s("|field=").dec(field as u64);
        out.s("|vt=").dec(vt as u64);
        out.s("|parent=").hex(parent);
        out.s("|ra=").hex(rel(lr));
        out.s("|orig=").f32_dec(orig);
        out.end_line();
    }
    if seen.log {
        head(&mut out, "L3");
        out.s("|h=").hash40(hash);
        out.s("|slot=").dec(seen.slot.unwrap_or(99) as u64);
        out.s("|x0=").hex(x0);
        out.s("|parent=").hex(parent);
        out.s("|ra=").hex(rel(lr));
        out.s("|p=").int(ident.player as i64);
        out.s("|kind=").int(ident.kind as i64);
        out.s("|id=").hex_fixed(slot_id as u64, 8);
        out.s("|ov=").dec(decision.value.is_some() as u64);
        out.s("|orig=").f32_dec(orig);
        out.s("|v=").f32_dec(value);
        out.s("|bits=0x").hex_fixed(value.to_bits() as u64, 8);
        out.s("|vt=").dec(vt as u64);
        out.s("|st=").s(decision.st.name());
        out.s("|src=").s(src_name);
        out.end_line();
    }
    if first_apply {
        head(&mut out, "OV");
        out.s("|id=").hex_fixed(slot_id as u64, 8);
        out.s("|h=").hash40(hash);
        out.s("|src=").s(src_name);
        push_preset_name(&mut out, STORE.preset_of(decision.entry));
        out.s("|p=").int(ident.player as i64);
        out.s("|parent=").hex(parent);
        out.s("|orig=").f32_dec(orig);
        out.s("|new=").f32_dec(value);
        out.s("|newbits=0x").hex_fixed(value.to_bits() as u64, 8);
        out.s("|ra=").hex(rel(lr));
        out.end_line();
    }
    if seen.is_new {
        head(&mut out, "L4");
        out.s("|parent=").hex(parent);
        out.s("|slot=").dec(seen.slot.unwrap_or(99) as u64);
        out.s("|kind=").int(ident.kind as i64);
        out.s("|p=").int(ident.player as i64);
        let mut p = 0u32;
        while p < logic::PLAYERS as u32 {
            if let Some((id, sp)) = read_player(p) {
                logic::push_player(&mut out, p, id, sp);
            }
            p += 1;
        }
        out.end_line();
        if ident.kind == logic::KIND_MIIGUNNER {
            moves::log_match_start(slot_id);
        }
    }
    if seen.is_new || due {
        push_totals(&mut out);
    }
    emit(out.as_bytes());
    if seen.is_new || due {
        emit_field_totals();
    }
    if x2_pending {
        emit_x2_firsts();
    }
    value
}

// ---------------------------------------------------------------------------
// Saving (called by the editor UI when a row is decided)
// ---------------------------------------------------------------------------

const SAVE_STEPS: [&str; 11] = [
    "ok", "busy", "serialise", "self_check", "create_new", "write_new", "flush_new", "read_back",
    "read_back_differs", "remove_old", "rename_new",
];

fn os_code(e: &std::io::Error) -> i64 {
    e.raw_os_error().map(|c| c as i64).unwrap_or(-1)
}

/// Write the in-memory loadout state to `LOADOUT_PATH`. Returns an index into
/// `SAVE_STEPS` (0 = written), the text length and an OS error code.
///
/// `nn::fs::RenameFile` does not replace an existing file (the target's std maps its
/// `0x402` to `AlreadyExists`), so "replace" is: write `loadouts.new` completely, flush,
/// read it back and compare, delete `loadouts.txt`, rename `loadouts.new` to
/// `loadouts.txt`. Until the delete the old file is intact whatever happens. A power loss
/// between the delete and the rename leaves no `loadouts.txt` and a complete, verified
/// `loadouts.new`, which the next boot reads (contract B+, `loadout::load`).
unsafe fn save_locked() -> (usize, usize, i64) {
    use std::io::Write;

    let table = STORE.snapshot_with_validator(editor::the_menu());
    let text = &mut *SAVE_BUF.0.get();
    let len = match loadout::serialise(&table, &PRESETS, text) {
        Ok(len) => len,
        Err(_) => return (2, 0, 0),
    };
    let text = match text.get(..len) {
        Some(text) => text,
        None => return (2, 0, 0),
    };
    // The text must read back as exactly the state it was made from.
    let (back, report) = loadout::parse_with_validator(text, &PRESETS, editor::the_menu());
    if report.state != loadout::FileState::Ok || report.rejected != 0 || back != table {
        return (3, len, 0);
    }

    let mut file = match std::fs::File::create(LOADOUT_TMP_PATH) {
        Ok(file) => file,
        Err(e) => return (4, len, os_code(&e)),
    };
    if let Err(e) = file.write_all(text) {
        return (5, len, os_code(&e));
    }
    if let Err(e) = file.sync_all() {
        return (6, len, os_code(&e));
    }
    drop(file);

    let check = &mut *FILE_BUF.0.get();
    match read_file(LOADOUT_TMP_PATH, check) {
        Ok(read) if check.get(..read) == Some(text) => {}
        Ok(_) => return (8, len, 0),
        Err((_, code)) => return (7, len, code),
    }

    if let Err(e) = std::fs::remove_file(LOADOUT_PATH) {
        if e.kind() != std::io::ErrorKind::NotFound {
            return (9, len, os_code(&e));
        }
    }
    if let Err(e) = std::fs::rename(LOADOUT_TMP_PATH, LOADOUT_PATH) {
        return (10, len, os_code(&e));
    }
    (0, len, 0)
}

/// Save the loadout state (see `save_locked`). One `mc|SV|` log line per call. Never
/// waits: a second caller while a save runs gets `busy`.
pub(crate) fn save_loadouts() -> u32 {
    let (step, len, code) = if SAVE_BUSY.swap(true, Ordering::Acquire) {
        (1, 0, 0)
    } else {
        let done = unsafe { save_locked() };
        SAVE_BUSY.store(false, Ordering::Release);
        done
    };
    let mut out: LineBuf<192> = LineBuf::new();
    head(&mut out, "SV");
    out.s("|result=").s(SAVE_STEPS.get(step).copied().unwrap_or("?"));
    out.s("|step=").dec(step as u64);
    out.s("|bytes=").dec(len as u64);
    out.s("|os_error=").int(code);
    out.end_line();
    emit_wait(out.as_bytes());
    step as u32
}

/// Exported since 0.3.0; in 0.4.0 the editor UI is the caller of `save_loadouts`. 0 =
/// written.
#[no_mangle]
pub extern "C" fn mc_save_loadouts() -> u32 {
    save_loadouts()
}

// ---------------------------------------------------------------------------
// L0 / LO - load
// ---------------------------------------------------------------------------

unsafe fn read_words(addr: usize) -> [u32; 4] {
    let mut words = [0u32; 4];
    for (k, w) in words.iter_mut().enumerate() {
        *w = core::ptr::read_volatile(addr.wrapping_add(4 * k) as *const u32);
    }
    words
}

fn push_words<const N: usize>(out: &mut LineBuf<N>, words: &[u32; 4]) {
    for (k, w) in words.iter().enumerate() {
        if k != 0 {
            out.s(",");
        }
        out.hex_fixed(*w as u64, 8);
    }
}

/// Emit to the file and, at load only, to Skyline's TCP log.
pub(crate) fn emit_load<const N: usize>(out: &LineBuf<N>) {
    if let Ok(text) = core::str::from_utf8(out.as_bytes()) {
        skyline::println!("{}", text.trim_end());
    }
    emit(out.as_bytes());
}

/// Read at most `buf.len()` bytes of `path`. The error is (`absent` | `unreadable`, OS
/// error code or -1). `File::open` of this target reports a missing file as a generic
/// error, so existence is asked first.
fn read_file(path: &str, buf: &mut [u8]) -> Result<usize, (&'static str, i64)> {
    use std::io::Read;

    if let Err(e) = std::fs::metadata(path) {
        let state = if e.kind() == std::io::ErrorKind::NotFound { "absent" } else { "unreadable" };
        return Err((state, os_code(&e)));
    }
    let mut file = match std::fs::File::open(path) {
        Ok(file) => file,
        Err(e) => return Err(("unreadable", os_code(&e))),
    };
    let mut len = 0usize;
    loop {
        let rest = match buf.get_mut(len..) {
            Some(rest) if !rest.is_empty() => rest,
            _ => break,
        };
        match file.read(rest) {
            Ok(0) => break,
            Ok(n) => len = len.saturating_add(n),
            Err(e) => return Err(("unreadable", os_code(&e))),
        }
    }
    Ok(len)
}

fn file_off(what: &str, path: &str, state: &str, os_error: i64) {
    let mut out: LineBuf<256> = LineBuf::new();
    head(&mut out, "L0");
    out.s("|").s(what).s("|path=").s(path);
    out.s("|state=").s(state);
    out.s("|os_error=").int(os_error);
    out.end_line();
    emit_load(&out);
}

/// Read and parse the preset file once. Anything but a well-formed file leaves no preset;
/// the two named keys stay known either way.
fn load_presets() {
    PRESETS.init_named();
    // Sole user of the buffer: this runs once, before the hook is installed.
    let buf = unsafe { &mut *PRESET_BUF.0.get() };
    match read_file(PRESET_PATH, buf) {
        Err((state, code)) => file_off("presets", PRESET_PATH, state, code),
        Ok(len) => {
            let report = preset::parse(buf.get(..len).unwrap_or(&[]), &PRESETS);
            let mut out: LineBuf<320> = LineBuf::new();
            head(&mut out, "L0");
            out.s("|presets|path=").s(PRESET_PATH);
            out.s("|state=").s(report.state.name());
            out.s("|bytes=").dec(len as u64);
            out.s("|lines=").dec(report.lines as u64);
            out.s("|presets=").dec(PRESETS.len() as u64);
            out.s("|hashes=").dec(PRESETS.file_hashes() as u64);
            out.s("|field_lines=").dec(report.fields as u64);
            out.s("|rejected=").dec(report.rejected as u64);
            out.s("|skipped=").dec(report.skipped as u64);
            out.end_line();
            emit_load(&out);
            for (line, why) in report.rejects() {
                let mut out: LineBuf<128> = LineBuf::new();
                head(&mut out, "L0");
                out.s("|presets_reject|line=").dec(*line as u64).s("|reason=").s(why.name());
                out.end_line();
                emit_load(&out);
            }
        }
    }
    // Every hash the hook reacts to, in field-index order; the first two are the named keys.
    let mut out: LineBuf<1280> = LineBuf::new();
    head(&mut out, "L0");
    let count = PRESETS.fields.len();
    out.s("|fields|n=").dec(count as u64);
    out.s("|probe_max=").dec(PRESETS.fields.probe_max() as u64);
    let mut field = 0;
    while field < count {
        out.s("|").dec(field as u64).s("=").hash40(PRESETS.fields.hash_of(field));
        field += 1;
    }
    out.end_line();
    emit_load(&out);
}

/// Read and parse the loadout file once. Anything but a well-formed file leaves the
/// store empty, which makes every request return the original value. Contract B+: when
/// `loadouts.txt` does not exist, a well-formed `loadouts.new` (left by a save that was
/// interrupted between its delete and its rename) is read instead.
fn load_loadouts() {
    // Sole user of the buffer: this runs once, before the hook is installed.
    let buf = unsafe { &mut *FILE_BUF.0.get() };
    let mut path = LOADOUT_PATH;
    let mut len = 0usize;
    let main = match read_file(LOADOUT_PATH, buf) {
        Ok(read) => {
            len = read;
            loadout::Probe::Bytes(&[])
        }
        Err((state, code)) => {
            file_off("loadout", LOADOUT_PATH, state, code);
            if state == "absent" {
                loadout::Probe::Absent
            } else {
                loadout::Probe::Unreadable
            }
        }
    };
    let mut new = loadout::Probe::Absent;
    if main == loadout::Probe::Absent {
        match read_file(LOADOUT_TMP_PATH, buf) {
            Ok(read) => {
                len = read;
                path = LOADOUT_TMP_PATH;
                new = loadout::Probe::Bytes(&[]);
            }
            Err((state, code)) => {
                file_off("loadout_new", LOADOUT_TMP_PATH, state, code);
                return;
            }
        }
    } else if main == loadout::Probe::Unreadable {
        return;
    }
    // Whichever file was read is in `buf`; hand it to the probe that stands for it.
    let bytes: &[u8] = buf.get(..len).unwrap_or(&[]);
    let (main, new) = match (main, new) {
        (loadout::Probe::Bytes(_), _) => (loadout::Probe::Bytes(bytes), loadout::Probe::Absent),
        (main, loadout::Probe::Bytes(_)) => (main, loadout::Probe::Bytes(bytes)),
        other => other,
    };
    let (table, report, origin) = loadout::load_with_validator(main, new, &PRESETS, editor::the_menu());
    let usable = origin != loadout::Origin::Off && report.state == loadout::FileState::Ok;
    if usable {
        STORE.publish(&table);
    }

    let mut out: LineBuf<320> = LineBuf::new();
    head(&mut out, "L0");
    out.s("|loadout|path=").s(path);
    out.s("|origin=").s(origin.name());
    out.s("|state=").s(report.state.name());
    out.s("|version=").dec(report.version as u64);
    out.s("|bytes=").dec(len as u64);
    out.s("|lines=").dec(report.lines as u64);
    out.s("|accepted=").dec(report.accepted as u64);
    out.s("|preset_lines=").dec(report.preset_lines as u64);
    out.s("|option_lines=").dec(report.option_lines as u64);
    out.s("|slot_lines=").dec(report.slot_lines as u64);
    out.s("|replaced=").dec(report.replaced as u64);
    out.s("|rejected=").dec(report.rejected as u64);
    out.s("|cleared=").dec(report.cleared as u64);
    out.s("|ids=").dec(STORE.len() as u64);
    out.s("|overrides=").s(if STORE.len() != 0 { "on" } else { "off" });
    out.end_line();
    emit_load(&out);

    for (line, why) in report.rejects() {
        let mut out: LineBuf<128> = LineBuf::new();
        head(&mut out, "L0");
        out.s("|loadout_reject|line=").dec(*line as u64).s("|reason=").s(why.name());
        out.end_line();
        emit_load(&out);
    }
    if usable {
        for entry in table.entries() {
            let mut out: LineBuf<192> = LineBuf::new();
            head(&mut out, "LO");
            out.s("|id=").hex_fixed(entry.id as u64, 8);
            push_preset_name(&mut out, entry.preset);
            out.s("|preset_fields=").dec(entry.preset.map(|p| PRESETS.field_count(p)).unwrap_or(0) as u64);
            for (key, name) in loadout::KEY_NAMES.iter().enumerate() {
                out.s("|").s(name).s("=");
                match (entry.has.get(key), entry.value.get(key)) {
                    (Some(true), Some(value)) => {
                        out.f32_dec(*value);
                    }
                    _ => {
                        out.s("-");
                    }
                }
            }
            out.end_line();
            emit_load(&out);
        }
    }
}

/// Read and parse the list file once (contract F) and hand the list to the editor.
fn load_list() {
    // Sole user of the buffer: this runs once, before any hook is installed.
    let buf = unsafe { &mut *LIST_BUF.0.get() };
    let mut os_error = 0i64;
    let mut unreadable = false;
    let bytes = match read_file(LIST_PATH, buf) {
        Ok(len) => Some(len),
        Err((state, code)) => {
            os_error = code;
            unreadable = state != "absent";
            None
        }
    };
    let bytes: Option<&[u8]> = bytes.map(|len| buf.get(..len).unwrap_or(&[]));
    let (list, report) = list::parse(bytes, &PRESETS);

    let mut out: LineBuf<320> = LineBuf::new();
    head(&mut out, "L0");
    out.s("|list|path=").s(LIST_PATH);
    out.s("|state=").s(if unreadable { "unreadable" } else { report.state.name() });
    out.s("|os_error=").int(os_error);
    out.s("|fallback=").dec(report.fallback as u64);
    out.s("|lines=").dec(report.lines as u64);
    out.s("|accepted=").dec(report.accepted as u64);
    out.s("|rejected=").dec(report.rejected as u64);
    out.s("|entries=").dec(list.len() as u64);
    out.s("|first=").bytes(list.label(0));
    out.end_line();
    emit_load(&out);
    for (line, why) in report.rejects() {
        let mut out: LineBuf<128> = LineBuf::new();
        head(&mut out, "L0");
        out.s("|list_reject|line=").dec(*line as u64).s("|reason=").s(why.name());
        out.end_line();
        emit_load(&out);
    }
    editor::set_list(list);
}

/// Read and parse the menu file once (contract G) and hand the menu to the editor. Anything
/// but a well-formed file with at least one entry leaves no menu: mod mode then opens the
/// character list directly, as 0.4.0 did.
fn load_menu() {
    // Sole user of the buffer: this runs once, before any hook is installed.
    let buf = unsafe { &mut *MENU_BUF.0.get() };
    let mut os_error = 0i64;
    let mut unreadable = false;
    let bytes = match read_file(MENU_PATH, buf) {
        Ok(len) => Some(len),
        Err((state, code)) => {
            os_error = code;
            unreadable = state != "absent";
            None
        }
    };
    let bytes: Option<&[u8]> = bytes.map(|len| buf.get(..len).unwrap_or(&[]));
    let (menu, report) = menu::parse_filtered(bytes, &PRESETS, moves::is_active());

    let mut out: LineBuf<320> = LineBuf::new();
    head(&mut out, "L0");
    out.s("|menu|path=").s(MENU_PATH);
    out.s("|state=").s(if unreadable { "unreadable" } else { report.state.name() });
    out.s("|os_error=").int(os_error);
    out.s("|lines=").dec(report.lines as u64);
    out.s("|entries=").dec(menu.len() as u64);
    out.s("|labels=").dec(report.labels as u64);
    out.s("|allows=").dec(report.allows as u64);
    out.s("|rejected=").dec(report.rejected as u64);
    out.s("|first_page=").s(if menu.len() != 0 { "main" } else { "direct" });
    out.end_line();
    emit_load(&out);
    for (line, why) in report.rejects() {
        let mut out: LineBuf<128> = LineBuf::new();
        head(&mut out, "L0");
        out.s("|menu_reject|line=").dec(*line as u64).s("|reason=").s(why.name());
        out.end_line();
        emit_load(&out);
    }
    let mut index = 0;
    while let Some(entry) = menu.entry(index) {
        let mut out: LineBuf<256> = LineBuf::new();
        head(&mut out, "L0");
        out.s("|menu_entry|n=").dec(index as u64);
        out.s("|id=").bytes(entry.id());
        out.s("|kind=").s(entry.kind().name());
        out.s("|allowed=").dec(entry.allowed() as u64);
        out.s("|label=").bytes(if entry.label().is_empty() { b"-" } else { entry.label() });
        out.s("|text=").bytes(entry.text());
        out.end_line();
        emit_load(&out);
        index += 1;
    }
    editor::set_menu(menu);
}

/// Read and parse the optional names file once (0.5.2) and hand it to the editor. Runs after
/// `load_menu` and reuses its buffer (load time, single thread).
fn load_names() {
    let buf = unsafe { &mut *MENU_BUF.0.get() };
    let mut os_error = 0i64;
    let mut unreadable = false;
    let bytes = match read_file(NAMES_PATH, buf) {
        Ok(len) => Some(len),
        Err((state, code)) => {
            os_error = code;
            unreadable = state != "absent";
            None
        }
    };
    let bytes: Option<&[u8]> = bytes.map(|len| buf.get(..len).unwrap_or(&[]));
    let (names, report) = names::parse(bytes, &PRESETS);

    let mut out: LineBuf<320> = LineBuf::new();
    head(&mut out, "L0");
    out.s("|names|path=").s(NAMES_PATH);
    out.s("|state=").s(if unreadable { "unreadable" } else { report.state.name() });
    out.s("|os_error=").int(os_error);
    out.s("|lines=").dec(report.lines as u64);
    out.s("|accepted=").dec(report.accepted as u64);
    out.s("|rejected=").dec(report.rejected as u64);
    out.s("|first_reject=").dec(report.first_reject as u64);
    out.s("|default=").bytes(if names.default_name().is_empty() { b"-" } else { names.default_name() });
    out.end_line();
    emit_load(&out);
    editor::set_names(names);
}

/// True when the words at `site` equal the audited ones. One `L0` line either way.
unsafe fn check_words(what: &str, name: &str, base: usize, site: &Site) -> bool {
    let found = read_words(base.wrapping_add(site.offset as usize));
    let matches = logic::words_equal(&found, &site.words);
    let mut out: LineBuf<256> = LineBuf::new();
    head(&mut out, "L0");
    out.s("|").s(what).s("=").hex(site.offset).s("|name=").s(name);
    out.s("|expected=");
    push_words(&mut out, &site.words);
    out.s("|found=");
    push_words(&mut out, &found);
    out.s("|match=").dec(matches as u64);
    out.end_line();
    emit_load(&out);
    matches
}

/// Install the six UI hooks, all or none: `ui_off` absent, every UI site and every probe
/// equal to the audited words.
unsafe fn install_ui(base: usize) {
    let off = std::fs::metadata(UI_OFF_PATH).is_ok();
    let text_off = std::fs::metadata(TEXT_OFF_PATH).is_ok();
    editor::set_text(!text_off);
    let minus_off = std::fs::metadata(MINUS_OFF_PATH).is_ok();
    editor::set_minus(!minus_off);
    let mut sites_ok = 0u32;
    let mut probes_ok = 0u32;
    if !off {
        for (site, name) in ui::UI_SITE_LIST.iter().zip(ui::UI_SITE_NAMES.iter()) {
            sites_ok += check_words("ui_site", name, base, site) as u32;
        }
        for site in MC_PROBES.iter() {
            let mut ok = check_words("ui_probe", "probe", base, site);
            // 0.5.1: the entry of the UTF-8 text setter is only called, never patched, by
            // this plugin. Another plugin may have hooked it (session 3: `ldr x17, #8 ;
            // br x17` found there); the game's own callers go through that hook too, so it
            // is accepted and logged. The setter's body is still probed at 0x37a23d0.
            if !ok && site.offset as usize == ui::FN_SET_TEXT_UTF8 {
                let found = read_words(base.wrapping_add(site.offset as usize));
                let hooked = found.get(0).copied() == Some(0x5800_0051) && found.get(1).copied() == Some(0xd61f_0220);
                let mut out: LineBuf<160> = LineBuf::new();
                head(&mut out, "L0");
                out.s("|ui_probe_entry_hooked=").hex(site.offset).s("|accepted=").dec(hooked as u64);
                out.end_line();
                emit_load(&out);
                ok = hooked;
            }
            probes_ok += ok as u32;
        }
    }
    let all = !off && sites_ok as usize == ui::UI_SITES && probes_ok as usize == ui::PROBES;
    let mut installed = 0u32;
    if all {
        for (k, hook) in editor::hooks().iter().enumerate() {
            if let Some(slot) = editor::ORIG.get(k) {
                install_site(1 + k, base, *hook, slot);
                installed += (slot.load(Ordering::Relaxed) != 0) as u32;
            }
        }
    }
    let ready = installed as usize == ui::UI_SITES;
    editor::set_ready(ready);

    let mut out: LineBuf<256> = LineBuf::new();
    head(&mut out, "UI");
    out.s("|sites|ui=").s(if ready { "on" } else { "off" });
    out.s("|ui_off_file=").dec(off as u64);
    out.s("|sites_ok=").dec(sites_ok as u64).s("/").dec(ui::UI_SITES as u64);
    out.s("|probes_ok=").dec(probes_ok as u64).s("/").dec(ui::PROBES as u64);
    out.s("|installed=").dec(installed as u64);
    out.s("|entries=").dec(editor::entries() as u64);
    out.s("|menu=").dec(editor::menu_entries() as u64);
    out.s("|text=").s(if text_off { "off" } else { "on" });
    out.s("|minus=").s(if minus_off { "off" } else { "on" });
    out.end_line();
    emit_load(&out);
}

unsafe fn install_site(index: usize, base: usize, hook: *const c_void, slot: &AtomicUsize) {
    let (site, name) = match (MC_SITES.get(index), SITE_NAMES.get(index)) {
        (Some(site), Some(name)) => (site, *name),
        _ => return,
    };
    let addr = base.wrapping_add(site.offset as usize);
    let found = read_words(addr);
    let matches = logic::words_equal(&found, &site.words);

    // Written before the patch, so a crash inside the install still leaves this line.
    let mut out: LineBuf<256> = LineBuf::new();
    head(&mut out, "L0");
    out.s("|site=").hex(site.offset).s("|name=").s(name);
    out.s("|expected=");
    push_words(&mut out, &site.words);
    out.s("|found=");
    push_words(&mut out, &found);
    out.s("|match=").dec(matches as u64);
    out.end_line();
    emit_load(&out);

    let mut out: LineBuf<256> = LineBuf::new();
    head(&mut out, "L0");
    out.s("|site=").hex(site.offset).s("|name=").s(name);
    if matches {
        A64HookFunction(
            addr as *const c_void,
            hook,
            slot.as_ptr() as *mut *mut c_void,
        );
        let tramp = slot.load(Ordering::Relaxed);
        let after = read_words(addr);
        out.s("|installed=").dec((tramp != 0) as u64);
        out.s("|trampoline=").hex(tramp as u64);
        out.s("|after=");
        push_words(&mut out, &after);
    } else {
        out.s("|installed=0|reason=words_differ");
    }
    out.end_line();
    emit_load(&out);
}

#[skyline::main(name = "mii_customizer")]
pub fn main() {
    let base = unsafe { getRegionAddress(Region::Text) } as usize;
    BASE.store(base, Ordering::Relaxed);

    let mut out: LineBuf<384> = LineBuf::new();
    head(&mut out, "L0");
    out.s("|").s(LOG_TAG).s(" ").s(env!("CARGO_PKG_VERSION")).s("-").s(VARIANT).s(" loaded");
    out.s("|base=").hex(base as u64);
    out.s("|T=").hex(base.wrapping_add(logic::TABLE_BASE) as u64);
    if let (Some(id0), Some(sp0)) = (logic::id_addr(base, 0), logic::special_addr(base, 0)) {
        out.s("|id_p0=").hex(id0 as u64).s("|special_p0=").hex(sp0 as u64);
    }
    out.s("|hook_param=").hex(mc_hook_param as unsafe extern "C" fn() as usize as u64);
    // The binding's constants, as compiled in, next to the kinds this build accepts.
    out.s("|gunner_kind=").int(*FIGHTER_KIND_MIIGUNNER as i64);
    out.s("|accepted_kinds=");
    for (k, kind) in logic::ACCEPTED_KINDS.iter().enumerate() {
        if k != 0 {
            out.s(",");
        }
        out.int(*kind as i64);
    }
    out.s("|fighter_cat=").int(*BATTLE_OBJECT_CATEGORY_FIGHTER as i64);
    out.s("|entry_work_id=").hex(*FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID as u32 as u64);
    out.end_line();
    emit_load(&out);

    // Before the hook, so neither table changes while a request can read it. Presets
    // first: a `preset` line of the loadout file is checked against their names.
    load_presets();
    load_list();
    load_menu();
    load_loadouts();
    load_names();
    editor::init_sort_order(&PRESETS);
    moves::install();

    if base != 0 {
        unsafe {
            install_site(0, base, mc_hook_param as *const c_void, &ORIG_PARAM);
            // After the stat engine, and never a condition for it.
            install_ui(base);
        }
    }

    let mut out: LineBuf<256> = LineBuf::new();
    head(&mut out, "L0");
    out.s("|load_done|base_ok=").dec((base != 0) as u64);
    out.end_line();
    emit_load(&out);
}
