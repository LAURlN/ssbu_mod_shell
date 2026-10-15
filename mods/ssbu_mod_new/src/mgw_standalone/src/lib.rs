#![feature(proc_macro_hygiene)]
//! Standalone clone discovery probe. No legacy entry-memory hooks are installed.
//! A single CSS entry expands into native-form Mythra and Pyra clones.
use smash::{app::lua_bind::*, lib::lua_const::*, lua2cpp::L2CFighterCommon};
use std::sync::atomic::{AtomicUsize, Ordering};

// These two public C ABI functions are copied from the pinned engine API's
// signatures (0.3.1-beta.1, clone_engine_api/src/lib.rs). Dynamic lookup allows
// the probe to fail closed when the runtime is absent without importing a
// second version of the user's Smash bindings.
static IDENTITY_FN: AtomicUsize = AtomicUsize::new(0);
static ENTRY_FN: AtomicUsize = AtomicUsize::new(0);
unsafe fn symbol(cache: &AtomicUsize, name: &[u8]) -> usize {
    let cached = cache.load(Ordering::Acquire);
    if cached != 0 { return cached; }
    let mut address = 0usize;
    skyline::nn::ro::LookupSymbol(&mut address, name.as_ptr());
    if address != 0 { cache.store(address, Ordering::Release); }
    address
}
unsafe fn identity(name: &[u8]) -> i32 {
    let address = symbol(&IDENTITY_FN, b"clone_engine_kind_for_identity\0");
    if address == 0 { return -1; }
    let query: unsafe extern "C" fn(*const std::os::raw::c_char) -> i32 = std::mem::transmute(address);
    query(name.as_ptr().cast())
}
unsafe fn entry_kind(entry: i32) -> i32 {
    if !(0..8).contains(&entry) { return -1; }
    let address = symbol(&ENTRY_FN, b"clone_engine_get_entry_kind\0");
    if address == 0 { return -1; }
    let query: unsafe extern "C" fn(i32) -> i32 = std::mem::transmute(address);
    query(entry)
}

#[derive(Clone, Copy)]
struct Observation { object: u32, status: i32, remaining: u8 }
const EMPTY: Observation = Observation { object: u32::MAX, status: -1, remaining: 24 };
// Each form gets its own observation cell per player, so unexpected double
// construction remains visible instead of alternating one shared cached object.
static mut OBS: [[Observation; 8]; 2] = [[EMPTY; 8]; 2];

unsafe fn sample(fighter: &mut L2CFighterCommon, form: usize, force: bool) {
    let boma = fighter.module_accessor;
    let entry = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
    if !(0..8).contains(&entry) { return; }
    let name: &[u8] = if form == 0 { b"mgw_mythra\0" } else { b"mgw_pyra\0" };
    let expected = identity(name);
    let selected = entry_kind(entry);
    let state = &mut OBS[form][entry as usize];
    let object = (*boma).battle_object_id;
    let status = StatusModule::status_kind(boma);
    if state.object != object || force { *state = Observation { object, ..EMPTY }; }
    if !force && (state.status == status || state.remaining == 0) { return; }
    state.status = status;
    state.remaining = state.remaining.saturating_sub(1);
    let base = smash::app::utility::get_kind(&mut *boma);
    println!("[MGW-CLONE] form={} entry={} object={:#x} expected={} selected={} base={} color={} status={:#x} situation={} pos=({:.2},{:.2})",
        if form == 0 { "mythra" } else { "pyra" }, entry, object, expected, selected, base,
        WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR), status,
        StatusModule::situation_kind(boma), PostureModule::pos_x(boma), PostureModule::pos_y(boma));
    if expected < 0 || (selected != expected && !(form == 1 && selected == identity(b"mgw_mythra\0"))) {
        println!("[MGW-CLONE] IDENTITY MISMATCH: stop this test and keep the full startup log");
    }
}
unsafe extern "C" fn mythra_start(f: &mut L2CFighterCommon) { sample(f, 0, true); }
unsafe extern "C" fn pyra_start(f: &mut L2CFighterCommon) { sample(f, 1, true); }
unsafe extern "C" fn mythra_frame(f: &mut L2CFighterCommon) { sample(f, 0, false); }
unsafe extern "C" fn pyra_frame(f: &mut L2CFighterCommon) { sample(f, 1, false); }

#[skyline::main(name = "mgw_clone_probe")]
pub fn main() {
    println!("[MGW-CLONE] build p16-pair: one CSS slot, cloned Mythra and Pyra, native down-special enabled; experimental");
    smashline::Agent::new("mgw_mythra")
        .on_start(mythra_start)
        .on_line(smashline::Main, mythra_frame)
        .install();
    smashline::Agent::new("mgw_pyra")
        .on_start(pyra_start)
        .on_line(smashline::Main, pyra_frame)
        .install();
}
