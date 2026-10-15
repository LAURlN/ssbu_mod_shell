//! Editor UI: "mod mode" on the native headgear list of the Mii maker. 0.4.0 showed one
//! character list; 0.5.0 shows pages (contract M of `prompts/P11-MENU.md`): a main page with
//! one row per menu entry, and per entry a character page whose unavailable rows are greyed.
//!
//! Six function-entry hooks (sites and probes in `ui.rs`, proofs in
//! `research/P11-MENU.md`):
//!
//!   * `0x180a030` dispatcher - arms mod mode when the edit menu's exit value is 7
//!     (rewritten to 1) or 1 with ZL/ZR held;
//!   * `0x180abd0` headgear state - swaps the page's list in on its first tick, keeps the
//!     game from writing the Mii's headgear while the list is open, reads the decision and
//!     puts everything back on its last tick; when the visit goes on with another page it
//!     undoes the state's pop and asks the state reader to start the state again;
//!   * `0x328b5d0` "handle is not in the item table" - answers for our list handles: 1
//!     for an unavailable row while the row filler asks, otherwise 0;
//!   * `0x3288330` message key of a handle - gives our rows their label;
//!   * `0x19cd100` `sort_id_list` - turns the request into the mode the game itself ignores;
//!   * `0x19ccb20` row filler - marks the time the availability answer applies and puts
//!     literal text on the rows that have it.
//!
//! Rules this file keeps:
//!   * while no list is open every hook hands all its argument registers to the original
//!     unchanged (the four hot ones after one atomic load);
//!   * every pointer followed here is either the hooked function's own argument, a field
//!     the original function dereferences on the same path, or checked (non-null, expected
//!     vtable) before use; a failed check means "normal headgear screen";
//!   * the headgear handle of the working record is never written while a list is open
//!     (see `tick`); it is compared with its value at the start of the visit whenever a
//!     page closes;
//!   * no file IO and no allocation per frame: the log lines are written when the user
//!     arms, opens a page, decides or leaves; the list buffer is allocated once per opened
//!     page with the game's allocator (so the game can free it like its own); the row
//!     filler's pane holder is the one allocation the game itself makes per filled row;
//!   * no `unwrap`, no `panic!`, no indexing.

use crate::list::List;
use crate::loadout::Update;
use crate::logic::LineBuf;
use crate::menu::{self, Effect, Kind, Menu, Page};
use crate::names::{self, Names};
use crate::ui::{self, Action, Dispatch, Entry, Outcome};
use crate::{emit_wait, head, push_preset_name, save_loadouts, BASE, STORE};
use core::cell::UnsafeCell;
use core::sync::atomic::{AtomicBool, AtomicU32, AtomicUsize, Ordering};
use skyline::libc::c_void;
use skyline::nn::hid;

const SLOT_ZERO: AtomicUsize = AtomicUsize::new(0);
/// Trampolines to the original code, in `ui::UI_SITE_LIST` order. Written by
/// `A64HookFunction` before it patches the site.
pub static ORIG: [AtomicUsize; ui::UI_SITES] = [SLOT_ZERO; ui::UI_SITES];
const K_DISPATCH: usize = 0;
const K_STATE5: usize = 1;
const K_UNLISTED: usize = 2;
const K_LABEL: usize = 3;
const K_SORT: usize = 4;
const K_ROWFILL: usize = 5;

/// All six hooks are installed.
static READY: AtomicBool = AtomicBool::new(false);
static MODE: ui::Mode = ui::Mode::new();
/// A hook ran without its trampoline (cannot happen once a site is patched).
static ORIG_NULL: AtomicU32 = AtomicU32::new(0);
/// `sort_id_list` requests ignored while a list was open.
static SORT_IGNORED: AtomicU32 = AtomicU32::new(0);
/// UI log lines written since boot; the log stops at [`UI_LINE_CAP`].
static UI_LINES: AtomicU32 = AtomicU32::new(0);
const UI_LINE_CAP: u32 = 3000;
/// Non-zero while the original row filler runs for a row of our list (UI thread).
static FILLING: AtomicU32 = AtomicU32::new(0);
/// Literal row text is on (`text_off` switch file absent).
static TEXT_ON: AtomicBool = AtomicBool::new(true);
/// Text panes given literal text / not found, on the page that is open.
static TEXT_SET: AtomicU32 = AtomicU32::new(0);
static TEXT_MISSED: AtomicU32 = AtomicU32::new(0);
/// Rows the row filler was asked to grey on the page that is open.
static GREYED: AtomicU32 = AtomicU32::new(0);

/// Written once at load before any hook exists, read-only afterwards.
struct LoadCell<T>(UnsafeCell<T>);
unsafe impl<T> Sync for LoadCell<T> {}
static LIST: LoadCell<List> = LoadCell(UnsafeCell::new(List::new()));
static MENU: LoadCell<Menu> = LoadCell(UnsafeCell::new(Menu::new()));
static NAMES: LoadCell<Names> = LoadCell(UnsafeCell::new(Names::new()));
/// The edited Mii's stats preset when the open page was opened: preset index + 1, 0 = none.
/// Read by the row filler hook for the main page's "Stats: <name>" (0.5.2).
static VALUE_PRESET: AtomicU32 = AtomicU32::new(0);

static SORT_ORDER: core::sync::atomic::AtomicU8 = core::sync::atomic::AtomicU8::new(ui::SORT_NUMBER);

struct NameOrderCell(UnsafeCell<[u32; crate::list::MAX_ENTRIES]>);
unsafe impl Sync for NameOrderCell {}
static NAME_ORDER: NameOrderCell = NameOrderCell(UnsafeCell::new([0; crate::list::MAX_ENTRIES]));

pub fn init_sort_order(presets: &crate::preset::Presets) {
    unsafe {
        names::compute_name_order(the_list(), the_names(), presets, &mut *NAME_ORDER.0.get());
    }
}

/// The working record as it was when the visit started. UI thread only.
struct Snapshot(UnsafeCell<[u8; ui::RECORD_SNAPSHOT]>);
unsafe impl Sync for Snapshot {}
static SNAPSHOT: Snapshot = Snapshot(UnsafeCell::new([0; ui::RECORD_SNAPSHOT]));

/// Load time only, before `install_ui`.
pub fn set_list(list: List) {
    unsafe {
        *LIST.0.get() = list;
    }
}

/// Load time only, before `install_ui`.
pub fn set_menu(menu: Box<Menu>) {
    // Heap to static directly: a `Menu` value must never pass over the load stack.
    unsafe {
        core::ptr::copy_nonoverlapping(&*menu as *const Menu, MENU.0.get(), 1);
    }
}

/// Load time only, before `install_ui`.
pub fn set_names(names: Names) {
    unsafe {
        *NAMES.0.get() = names;
    }
}

fn the_names() -> &'static Names {
    unsafe { &*NAMES.0.get() }
}

fn the_list() -> &'static List {
    unsafe { &*LIST.0.get() }
}

pub(crate) fn the_menu() -> &'static Menu {
    unsafe { &*MENU.0.get() }
}

pub fn entries() -> usize {
    the_list().len()
}

pub fn menu_entries() -> usize {
    the_menu().len()
}

pub fn set_ready(ready: bool) {
    READY.store(ready, Ordering::Release);
}

/// Load time only.
pub fn set_text(on: bool) {
    TEXT_ON.store(on, Ordering::Release);
}

/// Every integer and float argument register, so the original sees what its caller passed
/// whatever its real signature is. None of the six functions takes an argument in x8
/// (each writes x8 before it reads it).
type Raw = unsafe extern "C" fn(
    u64, u64, u64, u64, u64, u64, u64, u64, f64, f64, f64, f64, f64, f64, f64, f64,
) -> u64;

macro_rules! original {
    ($k:expr, $x0:expr, $x1:expr, $x2:expr, $x3:expr, $x4:expr, $x5:expr, $x6:expr, $x7:expr,
     $d0:expr, $d1:expr, $d2:expr, $d3:expr, $d4:expr, $d5:expr, $d6:expr, $d7:expr) => {{
        let orig = match ORIG.get($k) {
            Some(slot) => slot.load(Ordering::Relaxed),
            None => 0,
        };
        if orig != 0 {
            let f: Raw = core::mem::transmute(orig);
            f($x0, $x1, $x2, $x3, $x4, $x5, $x6, $x7, $d0, $d1, $d2, $d3, $d4, $d5, $d6, $d7)
        } else {
            ORIG_NULL.fetch_add(1, Ordering::Relaxed);
            0
        }
    }};
}

pub fn hooks() -> [*const c_void; ui::UI_SITES] {
    [
        hook_dispatch as *const c_void,
        hook_state5 as *const c_void,
        hook_unlisted as *const c_void,
        hook_label as *const c_void,
        hook_sort as *const c_void,
        hook_rowfill as *const c_void,
    ]
}

// ---------------------------------------------------------------------------
// Memory and game calls
// ---------------------------------------------------------------------------

unsafe fn rd64(addr: u64) -> u64 {
    core::ptr::read_volatile(addr as usize as *const u64)
}

unsafe fn rd32(addr: u64) -> u32 {
    core::ptr::read_volatile(addr as usize as *const u32)
}

unsafe fn rd8(addr: u64) -> u8 {
    core::ptr::read_volatile(addr as usize as *const u8)
}

unsafe fn wr64(addr: u64, value: u64) {
    core::ptr::write_volatile(addr as usize as *mut u64, value)
}

unsafe fn wr32(addr: u64, value: u32) {
    core::ptr::write_volatile(addr as usize as *mut u32, value)
}

unsafe fn wr8(addr: u64, value: u8) {
    core::ptr::write_volatile(addr as usize as *mut u8, value)
}

fn base() -> u64 {
    BASE.load(Ordering::Relaxed) as u64
}

/// `0x37830e0(&scroller_pointer, count)`: the scroller's own "set item count" (58 callers
/// in the image). Recomputes the line count and scroll range, shows or hides the row
/// parts and clamps the cursor.
///
/// The call clamps the cursor; the "selected row" copy of it is refreshed only by the
/// scroller's frame function, so it is pulled below the new count here (`ui::clamp_selected`).
unsafe fn game_set_item_count(sub: u64, count: u32) {
    let f: unsafe extern "C" fn(u64, u32) = core::mem::transmute((base() as usize).wrapping_add(ui::FN_SET_ITEM_COUNT));
    f(sub.wrapping_add(ui::S_SCROLLER as u64), count);
    let scroller = rd64(sub.wrapping_add(ui::S_SCROLLER as u64));
    if scroller != 0 {
        let selected_at = scroller.wrapping_add(ui::SCROLLER_SELECTED as u64);
        let cursor = rd32(scroller.wrapping_add(ui::SCROLLER_CURSOR as u64)) as i32;
        if let Some(row) = ui::clamp_selected(rd32(selected_at) as i32, cursor, count) {
            wr32(selected_at, row as u32);
        }
    }
}

/// `0x19cfe00(S, handle)`: what the headgear state itself calls on its first tick. Stores
/// the handle in the three current slots, clears the preview flag, tells the list script
/// the handle's index in the vector (`set_select_id`) when it is there, and sets the
/// "unlisted" flag from the handle.
unsafe fn game_set_select(sub: u64, handle: u64) {
    let f: unsafe extern "C" fn(u64, u64) = core::mem::transmute((base() as usize).wrapping_add(ui::FN_SET_SELECT));
    f(sub, handle)
}

/// `SCROLLER_ITEM_NUM = count` in the list script's globals, by the call the constructor
/// made (0x19cf830..0x19cf854). The script uses it for "up on the first row goes to the
/// last row".
unsafe fn game_set_item_num(sub: u64, count: u32) -> bool {
    let holder = rd64(sub.wrapping_add(ui::S_SCRIPT as u64));
    if holder == 0 {
        return false;
    }
    let state = rd64(holder);
    if state == 0 {
        return false;
    }
    let f: unsafe extern "C" fn(u64, u64, u64, u64) =
        core::mem::transmute((base() as usize).wrapping_add(ui::FN_REG_CONST));
    f(state, base().wrapping_add(ui::STR_ITEM_NUM as u64), base().wrapping_add(ui::STR_INT as u64), count as u64);
    true
}

unsafe fn game_alloc(bytes: u64) -> u64 {
    let f: unsafe extern "C" fn(u64, u64) -> u64 = core::mem::transmute((base() as usize).wrapping_add(ui::FN_ALLOC));
    f(0x10, bytes)
}

unsafe fn game_free(pointer: u64) {
    let f: unsafe extern "C" fn(u64) = core::mem::transmute((base() as usize).wrapping_add(ui::FN_FREE));
    f(pointer)
}

// Call a game function that returns a C++ object through the hidden result pointer in x8
// (0x3776360 does: `mov x20, x8` at 0x3776378). Rust's `extern "C"` cannot place an
// argument in x8, so the call goes through this stub: x0 = function, x1 = result buffer,
// x2 / x3 = the function's first two arguments.
core::arch::global_asm!(
    r#"
    .section .text.mc_stubs, "ax", %progbits
    .balign 4
    .global mc_call_sret
    .hidden mc_call_sret
    .type mc_call_sret, %function
mc_call_sret:
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    mov x9, x0
    mov x8, x1
    mov x0, x2
    mov x1, x3
    blr x9
    ldp x29, x30, [sp], #16
    ret
    "#
);

extern "C" {
    fn mc_call_sret(function: usize, result: *mut u64, arg0: u64, arg1: *const u8);
}

/// The two text panes of a list row part, as the row filler names them (0x19ccbf4,
/// 0x19ccc30). No `%` in either: 0x3776360 formats its name argument.
const PANE_TEXT: &[u8] = b"set_txt_val\0";
const PANE_TEXT_DISABLE: &[u8] = b"set_txt_val_disable\0";

/// Put literal text on pane `name` of row node `node`, with the two calls the game makes
/// for the same purpose: the row filler's pane lookup (`0x3776360`, result `{vtable,
/// holder}`, holder freed by the caller as at 0x19ccc14..0x19ccc28) and the callee of Lua
/// `set_text_string` (`0x37a22f0(text pane, UTF-8)`, text pane = `holder+0x10` as at
/// 0x335a54c / 0x3779bac). False when the row has no such text pane.
unsafe fn set_pane_text(node: u64, name: &[u8], text: &[u8; names::LINE_BUF]) -> bool {
    let mut result = [0u64; 2];
    mc_call_sret((base() as usize).wrapping_add(ui::FN_FIND_PANE), result.as_mut_ptr(), node, name.as_ptr());
    let holder = result.get(1).copied().unwrap_or(0);
    if holder == 0 {
        return false;
    }
    let pane = rd64(holder.wrapping_add(ui::HOLDER_TEXT as u64));
    if pane != 0 {
        let f: unsafe extern "C" fn(u64, *const u8) =
            core::mem::transmute((base() as usize).wrapping_add(ui::FN_SET_TEXT_UTF8));
        f(pane, text.as_ptr());
    }
    game_free(holder);
    pane != 0
}

// ---------------------------------------------------------------------------
// Log
// ---------------------------------------------------------------------------

fn ui_head<const N: usize>(out: &mut LineBuf<N>, what: &str) {
    head(out, "UI");
    out.s("|").s(what);
}

/// End the line and write it, unless the per-boot cap is reached.
fn ui_emit<const N: usize>(out: &mut LineBuf<N>) {
    let n = UI_LINES.fetch_add(1, Ordering::Relaxed);
    if n > UI_LINE_CAP {
        return;
    }
    if n == UI_LINE_CAP {
        let mut last: LineBuf<96> = LineBuf::new();
        ui_head(&mut last, "log_cap");
        last.s("|lines=").dec(n as u64);
        last.end_line();
        emit_wait(last.as_bytes());
        return;
    }
    out.end_line();
    emit_wait(out.as_bytes());
}

/// `direct`, `main`, `entry:<id>` or `?`.
fn push_page<const N: usize>(out: &mut LineBuf<N>, page: Option<Page>) {
    match page {
        Some(Page::Direct) => out.s("direct"),
        Some(Page::Main) => out.s("main"),
        Some(Page::Entry(entry)) => {
            out.s("entry:");
            match the_menu().entry(entry) {
                Some(e) => out.bytes(e.id()),
                None => out.s("?"),
            }
        }
        None => out.s("?"),
    };
}

// ---------------------------------------------------------------------------
// The four hot hooks
// ---------------------------------------------------------------------------

/// `0x328b5d0`: 1 when the handle has no entry in the item table. The row filler draws a
/// row whose handle is "unlisted" as a disabled button (0x19ccd88 -> 0x19cce2c), and the
/// scroller decides nothing on a disabled button (0x377e278..0x377e2a4). The two cursor
/// helpers (0x19cd020, 0x19ccea0) would also step over such a row, so our handles are
/// "unlisted" only while the row filler asks, and only for the rows the page cannot decide.
unsafe extern "C" fn hook_unlisted(
    x0: u64, x1: u64, x2: u64, x3: u64, x4: u64, x5: u64, x6: u64, x7: u64,
    d0: f64, d1: f64, d2: f64, d3: f64, d4: f64, d5: f64, d6: f64, d7: f64,
) -> u64 {
    if MODE.active_rows() != 0 {
        if let Some(row) = ui::synth_row(x1) {
            if FILLING.load(Ordering::Relaxed) != 0 && !MODE.row_available(row) {
                GREYED.fetch_add(1, Ordering::Relaxed);
                return 1;
            }
            return 0;
        }
    }
    original!(K_UNLISTED, x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7)
}

/// `0x3288330(out, registry, handle)`: the message key of a handle. For our handles the
/// key is the row's label; the struct is the one the original fills.
unsafe extern "C" fn hook_label(
    x0: u64, x1: u64, x2: u64, x3: u64, x4: u64, x5: u64, x6: u64, x7: u64,
    d0: f64, d1: f64, d2: f64, d3: f64, d4: f64, d5: f64, d6: f64, d7: f64,
) -> u64 {
    if x0 != 0 {
        if let Some(page) = Page::from_code(MODE.active_page()) {
            if let Some(row) = ui::synth_row(x2) {
                let out = &mut *(x0 as usize as *mut [u8; ui::LABEL_STRUCT]);
                ui::write_label(out, menu::row_label(page, row, the_menu(), the_list()));
                return x0;
            }
        }
    }
    original!(K_LABEL, x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7)
}

/// Reorder list vector in place and log sort line.
unsafe fn handle_sort(sub: u64, mode: u64) {
    let page = Page::from_code(MODE.active_page());
    let is_character_page = match page {
        Some(Page::Direct) => true,
        Some(Page::Entry(entry)) => {
            the_menu().entry(entry).map(|e| e.kind() != Kind::Option).unwrap_or(false)
        }
        _ => false,
    };
    if !is_character_page {
        return;
    }
    let new_order = if mode == 2 { ui::SORT_NAME } else { ui::SORT_NUMBER };
    SORT_ORDER.store(new_order, Ordering::Relaxed);

    let buffer = MODE.buffer.load(Ordering::Relaxed);
    let list = the_list();
    let count = list.len();
    if buffer != 0 && rd64(sub.wrapping_add(ui::S_VEC_BEGIN as u64)) == buffer {
        wr64(buffer, ui::row_handle(0));
        if new_order == ui::SORT_NAME {
            let mut i = 0u64;
            for &item in (*NAME_ORDER.0.get()).iter().take(count) {
                wr64(buffer.wrapping_add((i + 1) * 8), ui::row_handle(item));
                i += 1;
            }
        } else {
            for i in 0..count {
                wr64(buffer.wrapping_add((i as u64 + 1) * 8), ui::row_handle(i as u32 + 1));
            }
        }
    }

    let backed_up = rd64(sub.wrapping_add(ui::S_BACKUP as u64));
    let selected = rd64(sub.wrapping_add(ui::S_SELECTED as u64));
    let total_rows = (count + 1) as u32;

    let mut cursor_row = -1i64;
    let mut tick_row = -1i64;
    if buffer != 0 {
        for r in 0..total_rows {
            let h = rd64(buffer.wrapping_add(r as u64 * 8));
            if ui::same_item(h, backed_up) {
                cursor_row = r as i64;
            }
            if ui::same_item(h, selected) {
                tick_row = r as i64;
            }
        }
    }

    let mut out: LineBuf<192> = LineBuf::new();
    ui_head(&mut out, "sort");
    out.s("|page=");
    push_page(&mut out, page);
    out.s("|mode=").dec(mode);
    out.s("|order=").s(if new_order == ui::SORT_NAME { "name" } else { "number" });
    out.s("|cursor=").int(cursor_row);
    out.s("|tick=").int(tick_row);
    ui_emit(&mut out);
}

/// `0x19cd100(S, mode)`: modes 0..2 sort (mode 2 frees and replaces the vector); any other
/// mode returns at once (0x19cd12c). While our list is open on `S` the request becomes
/// mode 3.
unsafe extern "C" fn hook_sort(
    x0: u64, x1: u64, x2: u64, x3: u64, x4: u64, x5: u64, x6: u64, x7: u64,
    d0: f64, d1: f64, d2: f64, d3: f64, d4: f64, d5: f64, d6: f64, d7: f64,
) -> u64 {
    let mut mode = x1;
    if MODE.is_active_sub(x0) {
        SORT_IGNORED.fetch_add(1, Ordering::Relaxed);
        mode = 3;
        handle_sort(x0, x1);
    }
    original!(K_SORT, x0, mode, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7)
}

/// After the original filled a row of our list: literal text for the rows that have it.
/// `node` is the row node the original has just used (`ldr x0,[x22,#8]` at 0x19ccb90).
#[inline(never)]
unsafe fn after_rowfill(row: u32, node: u64) {
    if node == 0 || !TEXT_ON.load(Ordering::Relaxed) {
        return;
    }
    let page = match Page::from_code(MODE.active_page()) {
        Some(page) => page,
        None => return,
    };
    if page == Page::Main {
        let entry = match the_menu().entry(row as usize) {
            Some(entry) => entry,
            None => return,
        };
        let mut line = [0u8; names::LINE_BUF];
        match entry.kind() {
            Kind::Stats => {
                let preset = match VALUE_PRESET.load(Ordering::Relaxed) {
                    p if p != 0 => Some(p as usize - 1),
                    _ => None,
                };
                names::compose(&mut line, entry.text(), the_names().value(preset));
            }
            Kind::Slot => {
                let id = MODE.saved_id.load(Ordering::Relaxed);
                let preset = STORE.slot_of_id(id, row as usize);
                names::compose(&mut line, entry.text(), the_names().value(preset));
            }
            Kind::Option => {
                let id = MODE.saved_id.load(Ordering::Relaxed);
                let opt_idx = STORE.option_of_id(id, row as usize).unwrap_or(0);
                let opt_text = entry.option(opt_idx).map(|o| o.text()).unwrap_or(b"");
                names::compose(&mut line, entry.text(), opt_text);
            }
        }
        let text = &line;
        let shown = set_pane_text(node, PANE_TEXT, text);
        let greyed = set_pane_text(node, PANE_TEXT_DISABLE, text);
        TEXT_SET.fetch_add(shown as u32 + greyed as u32, Ordering::Relaxed);
        TEXT_MISSED.fetch_add(!shown as u32 + !greyed as u32, Ordering::Relaxed);
    } else if let Page::Entry(entry_idx) = page {
        let entry = match the_menu().entry(entry_idx) {
            Some(entry) => entry,
            None => return,
        };
        if entry.kind() == Kind::Option {
            let opt = match entry.option(row as usize) {
                Some(opt) => opt,
                None => return,
            };
            let mut line = [0u8; names::LINE_BUF];
            names::compose(&mut line, opt.text(), b"");
            let text = &line;
            let shown = set_pane_text(node, PANE_TEXT, text);
            let greyed = set_pane_text(node, PANE_TEXT_DISABLE, text);
            TEXT_SET.fetch_add(shown as u32 + greyed as u32, Ordering::Relaxed);
            TEXT_MISSED.fetch_add(!shown as u32 + !greyed as u32, Ordering::Relaxed);
        }
    }
}

/// `0x19ccb20(S, row, row node)`: fills one visible row. For a row of our list the original
/// runs with [`FILLING`] raised (see `hook_unlisted`), then the row gets its literal text.
unsafe extern "C" fn hook_rowfill(
    x0: u64, x1: u64, x2: u64, x3: u64, x4: u64, x5: u64, x6: u64, x7: u64,
    d0: f64, d1: f64, d2: f64, d3: f64, d4: f64, d5: f64, d6: f64, d7: f64,
) -> u64 {
    if !MODE.is_active_sub(x0) {
        return original!(K_ROWFILL, x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7);
    }
    FILLING.store(1, Ordering::Relaxed);
    let result = original!(K_ROWFILL, x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7);
    FILLING.store(0, Ordering::Relaxed);
    after_rowfill(x1 as u32, x2);
    result
}

// ---------------------------------------------------------------------------
// Dispatcher: arming
// ---------------------------------------------------------------------------

/// A state buffer large enough for every `nn::hid::Npad*State` (the largest, the GameCube
/// one, is 0x30 bytes); the button word is the second u64 of each.
#[repr(C, align(8))]
struct PadState([u64; 8]);

/// ZL or ZR held on any connected controller or in handheld mode, asked through the same
/// `nn::hid` functions the game imports. Called at most once per edit-menu decision.
#[inline(never)]
unsafe fn zl_or_zr_held() -> bool {
    ui::zl_or_zr(buttons_held())
}

/// The button words of every connected controller and of handheld mode, OR-ed.
#[inline(never)]
unsafe fn buttons_held() -> u64 {
    let mut buttons = 0u64;
    for id in ui::NPAD_IDS.iter() {
        let style = hid::GetNpadStyleSet(id).flags;
        let mut k = 0;
        while k < ui::STYLES {
            if style & (1u32 << k) != 0 {
                let mut state = PadState([0; 8]);
                let at = &mut state as *mut PadState;
                match 1u32 << k {
                    ui::STYLE_FULL_KEY => hid::GetNpadFullKeyState(at as *mut hid::NpadHandheldState, id),
                    ui::STYLE_HANDHELD => hid::GetNpadHandheldState(at as *mut hid::NpadHandheldState, id),
                    ui::STYLE_JOY_DUAL => hid::GetNpadJoyDualState(at as *mut hid::NpadHandheldState, id),
                    ui::STYLE_JOY_LEFT => hid::GetNpadJoyLeftState(at as *mut hid::NpadHandheldState, id),
                    ui::STYLE_JOY_RIGHT => hid::GetNpadJoyRightState(at as *mut hid::NpadHandheldState, id),
                    ui::STYLE_GC => hid::GetNpadGcState(at as *mut hid::NpadGcState, id),
                    _ => {}
                }
                buttons |= state.0.get(1).copied().unwrap_or(0);
            }
            k += 1;
        }
    }
    buttons
}

/// The edit menu's script global the plugin raises for one Minus press (0.6.0). The edit
/// script (variant `minus`) leaves with exit value 7 when it reads 1.
const MINUS_GLOBAL: &[u8] = b"MC_MINUS\0";
/// Minus was held on the previous edit-menu frame.
static MINUS_PREV: AtomicBool = AtomicBool::new(false);
/// Edit-menu frames until a raised `MC_MINUS` is lowered again; 0 = not raised.
static MINUS_TTL: AtomicU32 = AtomicU32::new(0);
/// The Minus entry is on (`minus_off` switch file absent).
static MINUS_ON: AtomicBool = AtomicBool::new(true);
static MINUS_PRESSES: AtomicU32 = AtomicU32::new(0);

/// Load time only.
pub fn set_minus(on: bool) {
    MINUS_ON.store(on, Ordering::Release);
}

/// `MC_MINUS = value` in the edit script's globals, by the call the scene builder makes for
/// the script's other integer globals (0x1808fe0..0x1809018: state = `[[inner+0x40]]`,
/// `0x33750a0(state, name, "i", value)`; `inner` is the 0x138-byte edit actor object).
unsafe fn set_minus_global(inner: u64, value: u32) -> bool {
    let holder = rd64(inner.wrapping_add(ui::S_SCRIPT as u64));
    if holder == 0 {
        return false;
    }
    let state = rd64(holder);
    if state == 0 {
        return false;
    }
    let f: unsafe extern "C" fn(u64, *const u8, u64, u64) =
        core::mem::transmute((base() as usize).wrapping_add(ui::FN_REG_CONST));
    f(state, MINUS_GLOBAL.as_ptr(), base().wrapping_add(ui::STR_INT as u64), value as u64);
    true
}

/// Once per edit-menu frame: a new Minus press raises `MC_MINUS` for two frames (the script
/// reads it in its own update, before or after this hook in the frame), unless the script
/// has already published an exit value.
#[inline(never)]
unsafe fn minus_frame(inner: u64, running: bool) {
    let ttl = MINUS_TTL.load(Ordering::Relaxed);
    if ttl != 0 {
        MINUS_TTL.store(ttl - 1, Ordering::Relaxed);
        if ttl == 1 {
            set_minus_global(inner, 0);
        }
    }
    let held = ui::minus(buttons_held());
    let was = MINUS_PREV.swap(held, Ordering::Relaxed);
    if held && !was && running && ttl == 0 {
        let set = set_minus_global(inner, 1);
        if set {
            MINUS_TTL.store(2, Ordering::Relaxed);
        }
        let n = MINUS_PRESSES.fetch_add(1, Ordering::Relaxed);
        if n < 64 {
            let mut out: LineBuf<128> = LineBuf::new();
            ui_head(&mut out, "minus");
            out.s("|set=").dec(set as u64).s("|n=").dec(n as u64 + 1);
            ui_emit(&mut out);
        }
    }
}

/// A page of a running visit was waiting for the headgear state and something else ran
/// first: the visit is over. The Mii was checked when its last page closed.
fn visit_lost(place: &str, scene: u64) {
    let mut out: LineBuf<160> = LineBuf::new();
    ui_head(&mut out, "visit_lost");
    out.s("|at=").s(place).s("|scene=").hex(scene);
    ui_emit(&mut out);
}

/// Before the dispatcher runs: when it is about to read the edit menu's exit value (same
/// conditions as 0x180a044..0x180a098), decide whether that value opens mod mode.
#[inline(never)]
unsafe fn before_dispatch(scene: u64) {
    let mut armed = false;
    // 0x180a050: frame counter 0 takes another path that does not read the value.
    if READY.load(Ordering::Acquire) && scene != 0 && rd32(scene.wrapping_add(ui::SCENE_FRAME as u64)) != 0 {
        let wrapper = rd64(scene.wrapping_add(ui::SCENE_EDIT as u64));
        let inner = if wrapper != 0 { rd64(wrapper.wrapping_add(ui::WRAP_INNER as u64)) } else { 0 };
        if inner != 0 && MINUS_ON.load(Ordering::Relaxed) {
            minus_frame(inner, rd8(inner.wrapping_add(ui::EDIT_HAS_VALUE as u64)) == 0);
        }
        // 0x180a064: without the "has a value" flag the value is not read either.
        if inner != 0 && rd8(inner.wrapping_add(ui::EDIT_HAS_VALUE as u64)) != 0 {
            let value_at = inner.wrapping_add(ui::EDIT_EXIT_VALUE as u64);
            let value = rd32(value_at) as i32;
            let shown = entries() + menu_entries();
            let decision = ui::dispatch(value, true, shown, || zl_or_zr_held());
            let entry = match decision {
                Dispatch::ArmA => Some(Entry::A),
                Dispatch::ArmB => Some(Entry::B),
                _ => None,
            };
            let first = menu::first_page(the_menu());
            if let Some(entry) = entry {
                armed = MODE.arm(entry, scene, first.code());
                if armed && entry == Entry::A {
                    wr32(value_at, ui::EXIT_HEADGEAR as u32);
                }
            }
            if decision != Dispatch::Pass {
                let mut out: LineBuf<256> = LineBuf::new();
                ui_head(&mut out, if armed { "arm" } else { "arm_refused" });
                out.s("|entry=").s(if value == ui::EXIT_MOD { "A" } else { "B" });
                out.s("|value=").int(value as i64);
                out.s("|entries=").dec(entries() as u64);
                out.s("|menu=").dec(menu_entries() as u64);
                out.s("|page=");
                push_page(&mut out, Some(first));
                out.s("|id=").hex_fixed(rd32(base().wrapping_add(ui::WORK_RECORD as u64)) as u64, 8);
                out.s("|hat=").hex(rd64(base().wrapping_add(ui::HAT_STATIC as u64)));
                out.s("|depth=").dec(rd32(scene.wrapping_add(ui::SCENE_DEPTH as u64)) as u64);
                out.s("|scene=").hex(scene);
                ui_emit(&mut out);
            }
        }
    }
    if !armed && MODE.clear_pending() == ui::Dropped::Page {
        visit_lost("dispatch", scene);
    }
}

unsafe extern "C" fn hook_dispatch(
    x0: u64, x1: u64, x2: u64, x3: u64, x4: u64, x5: u64, x6: u64, x7: u64,
    d0: f64, d1: f64, d2: f64, d3: f64, d4: f64, d5: f64, d6: f64, d7: f64,
) -> u64 {
    before_dispatch(x0);
    original!(K_DISPATCH, x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7)
}

// ---------------------------------------------------------------------------
// Headgear state: open, keep, close
// ---------------------------------------------------------------------------

/// The objects of the headgear screen, each checked before it is used.
#[derive(Clone, Copy)]
struct Screen {
    sub: u64,
    begin: u64,
    end: u64,
    cap: u64,
    count: u64,
}

/// `scene -> list object -> S -> scroller`, with the vtables the constructors store
/// (0x19ceb5c, 0x19cec30, 0x3781544) and a sane item vector whose length is the
/// scroller's item count.
unsafe fn examine(scene: u64) -> Result<Screen, &'static str> {
    let base = base();
    if base == 0 || scene == 0 {
        return Err("no_base");
    }
    let object = rd64(scene.wrapping_add(ui::SCENE_HAT as u64));
    if object == 0 {
        return Err("no_list_object");
    }
    if rd64(object) != base.wrapping_add(ui::VT_LIST_OBJECT as u64) {
        return Err("list_vtable");
    }
    let sub = rd64(object.wrapping_add(ui::WRAP_INNER as u64));
    if sub == 0 {
        return Err("no_sub_object");
    }
    if rd64(sub) != base.wrapping_add(ui::VT_SUB_OBJECT as u64) {
        return Err("sub_vtable");
    }
    let scroller = rd64(sub.wrapping_add(ui::S_SCROLLER as u64));
    if scroller == 0 {
        return Err("no_scroller");
    }
    if rd64(scroller) != base.wrapping_add(ui::VT_SCROLLER as u64) {
        return Err("scroller_vtable");
    }
    let begin = rd64(sub.wrapping_add(ui::S_VEC_BEGIN as u64));
    let end = rd64(sub.wrapping_add(ui::S_VEC_END as u64));
    let cap = rd64(sub.wrapping_add(ui::S_VEC_CAP as u64));
    let count = match ui::vector_count(begin, end, cap) {
        Some(count) => count,
        None => return Err("vector"),
    };
    if rd32(scroller.wrapping_add(ui::SCROLLER_COUNT as u64)) as u64 != count {
        return Err("count_mismatch");
    }
    Ok(Screen { sub, begin, end, cap, count })
}

unsafe fn sub_of(scene: u64) -> u64 {
    let object = rd64(scene.wrapping_add(ui::SCENE_HAT as u64));
    if object == 0 {
        0
    } else {
        rd64(object.wrapping_add(ui::WRAP_INNER as u64))
    }
}

/// The page cannot be shown: this headgear state runs as the normal headgear screen, and a
/// visit that was going on is over.
fn refuse(reason: &str, scene: u64) {
    MODE.disarm();
    let mut out: LineBuf<160> = LineBuf::new();
    ui_head(&mut out, "open_refused");
    out.s("|reason=").s(reason).s("|scene=").hex(scene);
    ui_emit(&mut out);
}

/// After the original first tick of a headgear state a page waits for: put the page's list
/// in place. Any failure before the swap leaves the normal headgear screen.
#[inline(never)]
unsafe fn open(scene: u64, pending: ui::Pending) {
    let list = the_list();
    let menu = the_menu();
    let page = match Page::from_code(pending.page) {
        Some(page) => page,
        None => return refuse("no_page", scene),
    };
    let rows = menu::rows(page, menu, list);
    if rows == 0 {
        return refuse("no_rows", scene);
    }
    let screen = match examine(scene) {
        Ok(screen) => screen,
        Err(reason) => return refuse(reason, scene),
    };
    let sub = screen.sub;
    let depth = rd32(scene.wrapping_add(ui::SCENE_DEPTH as u64));
    let hat_now = rd64(base().wrapping_add(ui::HAT_STATIC as u64));
    let id_now = rd32(base().wrapping_add(ui::WORK_RECORD as u64));
    let flag = rd8(sub.wrapping_add(ui::S_UNLISTED_FLAG as u64));
    // The Mii as it was when the visit started: taken with the first page, and required
    // unchanged for every further one.
    let (hat, id) = if pending.in_visit {
        (MODE.hat_before.load(Ordering::Relaxed), MODE.saved_id.load(Ordering::Relaxed))
    } else {
        (hat_now, id_now)
    };
    if hat_now != hat || id_now != id {
        return refuse("mii_changed", scene);
    }

    // Written before anything is changed, so a crash in the steps below is locatable.
    let mut out: LineBuf<320> = LineBuf::new();
    ui_head(&mut out, "open");
    out.s("|page=");
    push_page(&mut out, Some(page));
    out.s("|entry=").s(pending.entry.name());
    out.s("|id=").hex_fixed(id as u64, 8);
    out.s("|hat_before=").hex(hat);
    out.s("|native_count=").dec(screen.count);
    out.s("|rows=").dec(rows as u64);
    out.s("|depth=").dec(depth as u64);
    out.s("|S=").hex(sub);
    out.s("|unlisted_flag=").dec(flag as u64);
    ui_emit(&mut out);

    let buffer = game_alloc(rows as u64 * 8);
    if buffer == 0 || buffer & 7 != 0 {
        return refuse("alloc", scene);
    }
    let is_character_page = match page {
        Page::Direct => true,
        Page::Entry(entry) => {
            menu.entry(entry).map(|e| e.kind() != Kind::Option).unwrap_or(false)
        }
        _ => false,
    };
    let order = if is_character_page {
        SORT_ORDER.load(Ordering::Relaxed)
    } else {
        ui::SORT_NUMBER
    };
    if order == ui::SORT_NAME {
        wr64(buffer, ui::row_handle(0));
        let mut i = 0u64;
        for &item in (*NAME_ORDER.0.get()).iter().take(list.len()) {
            wr64(buffer.wrapping_add((i + 1) * 8), ui::row_handle(item));
            i += 1;
        }
    } else {
        let mut row = 0u32;
        while row < rows {
            wr64(buffer.wrapping_add(row as u64 * 8), ui::row_handle(row));
            row += 1;
        }
    }
    if !pending.in_visit {
        let snapshot = &mut *SNAPSHOT.0.get();
        core::ptr::copy_nonoverlapping(
            base().wrapping_add(ui::WORK_RECORD as u64) as usize as *const u8,
            snapshot.as_mut_ptr(),
            ui::RECORD_SNAPSHOT,
        );
        MODE.hat_before.store(hat, Ordering::Relaxed);
        MODE.saved_id.store(id, Ordering::Relaxed);
    }
    MODE.real_begin.store(screen.begin, Ordering::Relaxed);
    MODE.real_end.store(screen.end, Ordering::Relaxed);
    MODE.real_cap.store(screen.cap, Ordering::Relaxed);
    MODE.unlisted_flag.store(flag as u32, Ordering::Relaxed);
    VALUE_PRESET.store(STORE.preset_of_id(id).map(|p| p as u32 + 1).unwrap_or(0), Ordering::Relaxed);
    TEXT_SET.store(0, Ordering::Relaxed);
    TEXT_MISSED.store(0, Ordering::Relaxed);
    GREYED.store(0, Ordering::Relaxed);
    let mask = menu::available_mask(page, menu, list);
    if !MODE.activate(pending.entry, scene, sub, rows, page.code(), depth, &mask) {
        game_free(buffer);
        return refuse("mode_busy", scene);
    }
    MODE.buffer.store(buffer, Ordering::Relaxed);

    // From here on the list is ours until `close`.
    let end = buffer.wrapping_add(rows as u64 * 8);
    wr64(sub.wrapping_add(ui::S_VEC_BEGIN as u64), buffer);
    wr64(sub.wrapping_add(ui::S_VEC_END as u64), end);
    wr64(sub.wrapping_add(ui::S_VEC_CAP as u64), end);
    game_set_item_count(sub, rows);
    let opt_choice = match page {
        Page::Entry(entry) if menu.entry(entry).map(|e| e.kind()) == Some(Kind::Option) => {
            Some(STORE.option_of_id(id, entry).unwrap_or(0) as u32)
        }
        Page::Entry(entry) if menu.entry(entry).map(|e| e.kind()) == Some(Kind::Slot) => {
            let preset = STORE.slot_of_id(id, entry);
            Some(ui::current_row(preset, list))
        }
        _ => None,
    };
    let start = menu::start(page, menu, list, STORE.preset_of_id(id), pending.hint.or(opt_choice));
    // The cursor row; the three current slots then hold its display copy.
    game_set_select(sub, ui::display_handle(start.cursor));
    if start.tick != start.cursor {
        // The tick is drawn on the row whose handle is in these two slots (0x19ccb5c,
        // 0x19ccc70); `ui::NO_ROW` is the handle of no row.
        wr64(sub.wrapping_add(ui::S_DECIDED as u64), ui::display_handle(start.tick));
        wr64(sub.wrapping_add(ui::S_SELECTED as u64), ui::display_handle(start.tick));
    }
    let item_num = game_set_item_num(sub, rows);

    let mut out: LineBuf<320> = LineBuf::new();
    ui_head(&mut out, "list");
    out.s("|page=");
    push_page(&mut out, Some(page));
    out.s("|count=").dec(rows as u64);
    out.s("|available=").dec(mask.iter().map(|w| w.count_ones() as u64).sum());
    out.s("|cursor=").dec(start.cursor as u64);
    out.s("|tick=").int(if start.tick == ui::NO_ROW { -1 } else { start.tick as i64 });
    out.s("|row0=").bytes(menu::row_label(page, 0, menu, list));
    push_preset_name(&mut out, STORE.preset_of_id(id));
    out.s("|text=").dec(TEXT_ON.load(Ordering::Relaxed) as u64);
    out.s("|item_num_set=").dec(item_num as u64);
    out.s("|hat_now=").hex(rd64(base().wrapping_add(ui::HAT_STATIC as u64)));
    ui_emit(&mut out);
}

/// Last tick of an open list, before the original runs its end-of-screen code: give the
/// game its own list, count and current handles back. After this the three current slots
/// hold the headgear the Mii had when the visit started, which is also what the working
/// record holds, so the original's two comparisons (0x180acbc.., 0x180ad38..) find no
/// change: no write to the record, no "changed" flags.
#[inline(never)]
unsafe fn close(sub: u64) -> u64 {
    let decided = rd64(sub.wrapping_add(ui::S_DECIDED as u64));
    let buffer = MODE.buffer.load(Ordering::Relaxed);
    let begin = MODE.real_begin.load(Ordering::Relaxed);
    let end = MODE.real_end.load(Ordering::Relaxed);
    let cap = MODE.real_cap.load(Ordering::Relaxed);
    let hat = MODE.hat_before.load(Ordering::Relaxed);
    let flag = MODE.unlisted_flag.load(Ordering::Relaxed);
    let ours = buffer != 0 && rd64(sub.wrapping_add(ui::S_VEC_BEGIN as u64)) == buffer;
    // The hooks stop answering for our handles; none is left in the list after the swap.
    MODE.page_closed();
    if ours {
        wr64(sub.wrapping_add(ui::S_VEC_BEGIN as u64), begin);
        wr64(sub.wrapping_add(ui::S_VEC_END as u64), end);
        wr64(sub.wrapping_add(ui::S_VEC_CAP as u64), cap);
        game_free(buffer);
        let count = (end.wrapping_sub(begin) / 8) as u32;
        game_set_item_count(sub, count);
        game_set_item_num(sub, count);
        // The script's start index for the next visit: the index of the Mii's headgear,
        // as the next first tick will set it again; row 0 when it is not in the list.
        let mut found = false;
        let mut at = begin;
        while at < end {
            if ui::same_item(rd64(at), hat) {
                found = true;
                break;
            }
            at = at.wrapping_add(8);
        }
        game_set_select(sub, if found { hat } else { rd64(begin) });
    } else {
        let mut out: LineBuf<192> = LineBuf::new();
        ui_head(&mut out, "close_unexpected");
        out.s("|reason=vector_replaced|S=").hex(sub).s("|buffer=").hex(buffer);
        ui_emit(&mut out);
    }
    wr64(sub.wrapping_add(ui::S_PREVIEW as u64), hat);
    wr64(sub.wrapping_add(ui::S_DECIDED as u64), hat);
    wr64(sub.wrapping_add(ui::S_SELECTED as u64), hat);
    wr8(sub.wrapping_add(ui::S_PREVIEW_DIRTY as u64), 0);
    wr8(sub.wrapping_add(ui::S_UNLISTED_FLAG as u64), (flag & 1) as u8);
    decided
}

/// Give the store what a decided stats row asks for, and save.
#[inline(never)]
unsafe fn apply(action: Action, id: u32) {
    let update = match action {
        Action::Set { id, preset } => Some(STORE.set_preset(id, Some(preset))),
        Action::Clear { id } => Some(STORE.set_preset(id, None)),
        _ => None,
    };
    if let Some(update) = update {
        let mut out: LineBuf<192> = LineBuf::new();
        ui_head(&mut out, "store");
        out.s("|id=").hex_fixed(id as u64, 8);
        out.s("|result=").s(update.name());
        push_preset_name(&mut out, STORE.preset_of_id(id));
        out.s("|ids=").dec(STORE.len() as u64);
        out.s("|generation=").dec(STORE.generation() as u64);
        ui_emit(&mut out);
        // The file is written whenever a row was decided for a saved Mii and the store
        // holds the choice, also when it already did (the file may not exist yet).
        if update != Update::Full && update != Update::ZeroId {
            save_loadouts();
        }
    }
}

/// Give the store what a decided option row asks for, and save.
#[inline(never)]
unsafe fn apply_option(id: u32, entry: usize, option: usize) {
    let update = STORE.set_option(id, entry, option);
    let mut out: LineBuf<192> = LineBuf::new();
    ui_head(&mut out, "store_option");
    out.s("|id=").hex_fixed(id as u64, 8);
    out.s("|entry=");
    if let Some(e) = the_menu().entry(entry) {
        out.bytes(e.id());
        out.s("|option=");
        if let Some(opt) = e.option(option) {
            out.bytes(opt.id());
        } else {
            out.s("default");
        }
    } else {
        out.dec(entry as u64);
    }
    out.s("|result=").s(update.name());
    out.s("|ids=").dec(STORE.len() as u64);
    out.s("|generation=").dec(STORE.generation() as u64);
    ui_emit(&mut out);
    if update != Update::Full && update != Update::ZeroId {
        save_loadouts();
    }
}

/// Give the store what a decided slot row asks for, and save.
#[inline(never)]
unsafe fn apply_slot(id: u32, entry: usize, row: u32, list: &crate::list::List) {
    let preset = if row == 0 {
        None
    } else {
        list.preset(row as usize - 1)
    };
    let update = STORE.set_slot(id, entry, preset);
    let mut out: LineBuf<192> = LineBuf::new();
    ui_head(&mut out, "store_slot");
    out.s("|id=").hex_fixed(id as u64, 8);
    out.s("|entry=");
    if let Some(e) = the_menu().entry(entry) {
        out.bytes(e.id());
    } else {
        out.dec(entry as u64);
    }
    out.s("|preset=");
    push_preset_name(&mut out, preset);
    out.s("|result=").s(update.name());
    out.s("|ids=").dec(STORE.len() as u64);
    out.s("|generation=").dec(STORE.generation() as u64);
    ui_emit(&mut out);
    if update != Update::Full && update != Update::ZeroId {
        save_loadouts();
    }
}

/// The visit goes on with another page: undo the pop the original has just made
/// (0x180adf4..0x180ae00; the stack slot still holds the headgear state) and raise the
/// state reader's "start the current state again" byte (0x180cebc..0x180cef0). The next
/// frame the reader clears the frame counter and the byte, and the headgear state runs its
/// first tick, which opens the page. Returns the reason when the scene is not as expected;
/// nothing is written then.
#[inline(never)]
unsafe fn reenter(opened: &ui::Opened, next: Page, hint: Option<u32>) -> Result<u32, &'static str> {
    let scene = opened.scene;
    let slot_at = scene.wrapping_add(ui::SCENE_STACK as u64).wrapping_add((opened.depth as u64).wrapping_mul(4));
    let view = ui::StackView {
        depth_open: opened.depth,
        depth_now: rd32(scene.wrapping_add(ui::SCENE_DEPTH as u64)),
        // Only read when the depth is a stack index (checked first by `can_reenter`).
        slot_state: if opened.depth < ui::STACK_SLOTS { rd32(slot_at) } else { u32::MAX },
        current_state: rd32(scene.wrapping_add(ui::SCENE_STATE as u64)),
        restart: rd8(scene.wrapping_add(ui::SCENE_RESTART as u64)),
        change_cb: (
            rd64(scene.wrapping_add(ui::SCENE_CHANGE_CB as u64)),
            rd64(scene.wrapping_add(ui::SCENE_CHANGE_CB as u64 + 8)),
        ),
    };
    ui::can_reenter(&view)?;
    let changes = match MODE.next_page(scene, next.code(), hint) {
        Some(changes) => changes,
        None => return Err("mode_state"),
    };
    wr32(scene.wrapping_add(ui::SCENE_DEPTH as u64), opened.depth);
    wr8(scene.wrapping_add(ui::SCENE_RESTART as u64), 1);
    Ok(changes)
}

/// After the original's last tick of a page: check the hard invariant, act on the
/// decision, then either go on with the next page or end the visit.
#[inline(never)]
unsafe fn finish(opened: ui::Opened, decided: u64) {
    let list = the_list();
    let menu = the_menu();
    let hat_before = MODE.hat_before.load(Ordering::Relaxed);
    let id_at_open = MODE.saved_id.load(Ordering::Relaxed);
    let hat_at = base().wrapping_add(ui::HAT_STATIC as u64);
    let hat_after = rd64(hat_at);
    let equal = hat_after == hat_before;
    if !equal {
        // Cannot happen by construction; if it does, the Mii gets its headgear back.
        wr64(hat_at, hat_before);
    }
    let snapshot = &*SNAPSHOT.0.get();
    let now = core::slice::from_raw_parts(base().wrapping_add(ui::WORK_RECORD as u64) as usize as *const u8, ui::RECORD_SNAPSHOT);
    let difference = ui::first_difference(snapshot, now);
    let id = rd32(base().wrapping_add(ui::WORK_RECORD as u64));

    let page = Page::from_code(opened.page);
    let outcome = ui::outcome(decided, opened.rows);
    // A record that is no longer the one the visit started with gets no choice and no
    // further page.
    let step = match page {
        Some(page) if id == id_at_open => menu::step(page, outcome, id, menu, list),
        _ => menu::Step { next: None, effect: Effect::Nothing },
    };

    let mut out: LineBuf<320> = LineBuf::new();
    match outcome {
        Outcome::Decide(row) => {
            ui_head(&mut out, "decide");
            out.s("|page=");
            push_page(&mut out, page);
            out.s("|row=").dec(row as u64);
            if let Some(page) = page {
                out.s("|label=").bytes(menu::row_label(page, row, menu, list));
            }
            match step.effect {
                Effect::Store(Action::Set { preset, .. }) => push_preset_name(&mut out, Some(preset)),
                Effect::SlotChosen { row } if row > 0 => {
                    let preset = list.preset(row as usize - 1);
                    push_preset_name(&mut out, preset)
                }
                _ => push_preset_name(&mut out, None),
            };
            out.s("|action=").s(match step.effect {
                Effect::Store(Action::Set { .. }) => "set",
                Effect::Store(Action::Clear { .. }) => "clear",
                Effect::Store(Action::UnsavedMii) => "none_id0",
                Effect::Store(Action::NoEntry) => "none_no_entry",
                Effect::Store(Action::Cancelled) => "none",
                Effect::SlotChosen { row } => if row == 0 { "clear_slot" } else { "set_slot" },
                Effect::OptionChosen { .. } => "set_option",
                Effect::Refused { .. } => "refused_unavailable",
                Effect::Nothing if id != id_at_open => "none_id_changed",
                Effect::Nothing if step.next.is_some() => "open_entry",
                Effect::Nothing => "none",
            });
        }
        Outcome::Cancel => {
            ui_head(&mut out, "cancel");
            out.s("|page=");
            push_page(&mut out, page);
            out.s("|slot=").hex(decided);
        }
    }
    out.s("|id=").hex_fixed(id as u64, 8);
    out.s("|greyed_fills=").dec(GREYED.load(Ordering::Relaxed) as u64);
    out.s("|text_set=").dec(TEXT_SET.load(Ordering::Relaxed) as u64);
    out.s("|text_missed=").dec(TEXT_MISSED.load(Ordering::Relaxed) as u64);
    ui_emit(&mut out);

    match step.effect {
        Effect::Store(action) => apply(action, id),
        Effect::OptionChosen { entry, option } => apply_option(id, entry, option),
        Effect::SlotChosen { row } => {
            if let Some(Page::Entry(entry)) = page {
                apply_slot(id, entry, row, list);
            }
        }
        _ => {}
    }

    // The next page only for a Mii that is exactly as the visit found it.
    let mut left = "leave";
    if let Some((next, hint)) = step.next {
        if !equal || difference.is_some() {
            left = "mii_changed";
        } else {
            match reenter(&opened, next, hint) {
                Ok(changes) => {
                    let mut out: LineBuf<320> = LineBuf::new();
                    ui_head(&mut out, "page");
                    out.s("|from=");
                    push_page(&mut out, page);
                    out.s("|to=");
                    push_page(&mut out, Some(next));
                    out.s("|depth=").dec(opened.depth as u64);
                    out.s("|n=").dec(changes as u64);
                    out.s("|cursor=").int(hint.map(|h| h as i64).unwrap_or(-1));
                    out.s("|hat=").hex(hat_after);
                    out.s("|equal=1|record_equal=1");
                    ui_emit(&mut out);
                    return;
                }
                Err(reason) => left = reason,
            }
        }
    }

    // The visit is over: once per visit, the Mii before and after.
    let mut out: LineBuf<384> = LineBuf::new();
    ui_head(&mut out, "exit");
    out.s("|entry=").s(opened.entry.name());
    out.s("|reason=").s(left);
    out.s("|hat_before=").hex(hat_before);
    out.s("|hat_after=").hex(hat_after);
    out.s("|equal=").dec(equal as u64);
    out.s("|restored=").dec(!equal as u64);
    out.s("|record_equal=").dec(difference.is_none() as u64);
    out.s("|record_diff_at=").int(difference.map(|d| d as i64).unwrap_or(-1));
    out.s("|pages=").dec(MODE.changes() as u64 + 1);
    out.s("|depth_open=").dec(opened.depth as u64);
    out.s("|depth_now=").dec(rd32(opened.scene.wrapping_add(ui::SCENE_DEPTH as u64)) as u64);
    out.s("|sort_ignored=").dec(SORT_IGNORED.load(Ordering::Relaxed) as u64);
    out.s("|orig_null=").dec(ORIG_NULL.load(Ordering::Relaxed) as u64);
    ui_emit(&mut out);
    MODE.disarm();
}

/// One tick of the headgear state while a list may be open. Returns the screen and the
/// decided slot when this is the last tick.
#[inline(never)]
unsafe fn tick(scene: u64) -> Option<(ui::Opened, u64)> {
    let sub = sub_of(scene);
    let opened = match MODE.opened(scene, sub) {
        Some(opened) => opened,
        None => {
            // A list is marked open, but not for this scene and sub-object: the screen it
            // belonged to is gone. Nothing of it is touched.
            let mut out: LineBuf<160> = LineBuf::new();
            ui_head(&mut out, "stale");
            out.s("|scene=").hex(scene).s("|S=").hex(sub);
            ui_emit(&mut out);
            MODE.disarm();
            return None;
        }
    };
    // 0x180ac20: a set flag makes the original copy S+0x140 into the working record and
    // update the preview model. Cleared before the original can read it, on every tick.
    wr8(sub.wrapping_add(ui::S_PREVIEW_DIRTY as u64), 0);
    // 0x180ac18: state 0 of the list's own state machine = its script has ended.
    if rd32(sub.wrapping_add(ui::S_STATE as u64)) == 0 {
        return Some((opened, close(sub)));
    }
    None
}

unsafe extern "C" fn hook_state5(
    x0: u64, x1: u64, x2: u64, x3: u64, x4: u64, x5: u64, x6: u64, x7: u64,
    d0: f64, d1: f64, d2: f64, d3: f64, d4: f64, d5: f64, d6: f64, d7: f64,
) -> u64 {
    if MODE.phase() == ui::PHASE_IDLE || x0 == 0 {
        return original!(K_STATE5, x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7);
    }
    let scene = x0;
    // 0x180abe4: frame counter 0 = first tick of the state.
    if rd32(scene.wrapping_add(ui::SCENE_FRAME as u64)) == 0 {
        if MODE.phase() == ui::PHASE_ACTIVE {
            // The state starts again while a list is still marked open: put the native
            // list back first if it is this screen's, then treat the visit as a normal one.
            let sub = sub_of(scene);
            if MODE.opened(scene, sub).is_some() {
                close(sub);
            }
            MODE.disarm();
            let mut out: LineBuf<160> = LineBuf::new();
            ui_head(&mut out, "reentry");
            out.s("|scene=").hex(scene);
            ui_emit(&mut out);
            return original!(K_STATE5, x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7);
        }
        let pending = MODE.take_pending(scene);
        let result = original!(K_STATE5, x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7);
        match pending {
            Some(pending) => open(scene, pending),
            None => visit_lost("state5_other_scene", scene),
        }
        return result;
    }
    if MODE.phase() != ui::PHASE_ACTIVE {
        // Something waits for a first tick and this headgear state is not on its first
        // tick: not ours.
        if MODE.clear_pending() == ui::Dropped::Page {
            visit_lost("state5_running", scene);
        }
        return original!(K_STATE5, x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7);
    }
    let ended = tick(scene);
    let result = original!(K_STATE5, x0, x1, x2, x3, x4, x5, x6, x7, d0, d1, d2, d3, d4, d5, d6, d7);
    if let Some((opened, decided)) = ended {
        finish(opened, decided);
    }
    result
}
