//! Three initialization hooks plus the approved Mythra recipient event wrapper.
//! Original Hero calls retain original callbacks. Runtime coverage is unverified.
use super::{logging::log, native_context::Scope, registration, state};
use smash::app::{lua_bind::StatusModule, BattleObjectModuleAccessor};
use std::sync::atomic::{AtomicBool, Ordering};
#[path = "native_signatures.rs"] mod signatures;
#[path = "native_params.rs"] mod native_params;
static READY: AtomicBool = AtomicBool::new(false);
#[no_mangle]
static mut PGWR_HERO_S_GAME_BASE: usize = 0;
core::arch::global_asm!(include_str!("native_1304.s"), options(raw));
core::arch::global_asm!(
    ".section .text.pgwr_hero_s_query_memory, \"ax\", %progbits",
    ".global pgwr_hero_s_query_memory", ".hidden pgwr_hero_s_query_memory",
    ".type pgwr_hero_s_query_memory, %function", ".p2align 2",
    "pgwr_hero_s_query_memory:", "str x1, [sp, #-16]!", "svc 0x6",
    "ldr x2, [sp], #16", "str w1, [x2]", "ret",
    ".size pgwr_hero_s_query_memory, .-pgwr_hero_s_query_memory",
);
extern "C" {
    fn pgwr_hero_s_query_memory(info: *mut u64, page: *mut u32, address: usize) -> u32;
    fn pgwr_hero_s_owned_spark_init(controller: *const u64, owner: *mut BattleObjectModuleAccessor) -> u64;
    fn pgwr_hero_s_owned_lightning_init(controller: *const u64, owner: *mut BattleObjectModuleAccessor) -> u64;
    fn pgwr_hero_s_owned_spark_class(this: *mut (), weapon: *mut (), descriptor: *const ());
    fn pgwr_hero_s_owned_lightning_map(weapon: *mut ());
    fn pgwr_hero_s_owned_lightning_log_alloc(owner: *mut BattleObjectModuleAccessor, ignored_work: i32);
}
pub(super) unsafe fn mapped(address: usize, size: usize) -> bool {
    let Some(end) = address.checked_add(size) else { return false };
    if address < 0x10000 || size == 0 { return false; }
    let mut info = [0u64; 6];
    let mut page = 0;
    pgwr_hero_s_query_memory(info.as_mut_ptr(), &mut page, address) == 0
        && info[3] as u32 & 1 != 0 && address as u64 >= info[0]
        && end as u64 <= info[0].saturating_add(info[1])
}
pub(super) fn ready() -> bool { READY.load(Ordering::Acquire) }
pub(super) unsafe fn allocate_lightning_group(owner: *mut BattleObjectModuleAccessor) {
    if !ready() || !mapped(owner as usize, 0x190) || state::get(owner).is_none() {
        crate::diagnostic!(log("FAIL lightning log allocation owner")); return;
    }
    let _scope = Scope::enter(owner);
    pgwr_hero_s_owned_lightning_log_alloc(owner, 0);
}

#[skyline::hook(offset = 0x85d580)]
unsafe fn spark_init(controller: *const u64, owner: *mut BattleObjectModuleAccessor) -> u64 {
    if !mapped(owner as usize, 0x190) {
        crate::diagnostic!(log("FAIL spark owner unreadable")); return 0;
    }
    if state::get(owner).is_none() { return original!()(controller, owner); }
    let status = StatusModule::status_kind(owner);
    if !ready() || !mapped(controller as usize, 8)
        || ![registration::ATTACK1, registration::ATTACK2, registration::APPEND].contains(&status) {
        crate::diagnostic!(log(format!("FAIL spark initializer status={:#x}", status))); return 0;
    }
    crate::diagnostic!(log(format!("INIT spark begin status={:#x}", status)));
    let _scope = Scope::enter(owner);
    let result = pgwr_hero_s_owned_spark_init(controller, owner);
    crate::diagnostic!(log(format!("INIT spark complete result={:#x}", result)));
    result
}
#[skyline::hook(offset = 0x85dad0)]
unsafe fn lightning_init(controller: *const u64, owner: *mut BattleObjectModuleAccessor) -> u64 {
    if !mapped(owner as usize, 0x190) {
        crate::diagnostic!(log("FAIL lightning owner unreadable")); return 0;
    }
    if state::get(owner).is_none() { return original!()(controller, owner); }
    let status = StatusModule::status_kind(owner);
    if !ready() || !mapped(controller as usize, 8) || status != registration::ATTACK3 {
        crate::diagnostic!(log(format!("FAIL lightning initializer status={:#x}", status))); return 0;
    }
    crate::diagnostic!(log(format!("INIT lightning begin status={:#x}", status)));
    let _scope = Scope::enter(owner);
    let result = pgwr_hero_s_owned_lightning_init(controller, owner);
    crate::diagnostic!(log(format!("INIT lightning complete result={:#x}", result)));
    result
}
#[skyline::hook(offset = 0x33cbb20)]
unsafe fn spark_class(this: *mut (), weapon: *mut (), descriptor: *const ()) {
    if !super::native_context::active() { return original!()(this, weapon, descriptor); }
    if !mapped(weapon as usize, 0x91)
        || !mapped(descriptor as usize, 0x2c) {
        crate::diagnostic!(log("FAIL spark class arguments unreadable")); return;
    }
    let level = *((descriptor as usize + 0x28) as *const i32);
    let accessor = *((weapon as usize + 0x20) as *const usize);
    if !(0..=2).contains(&level) || !mapped(accessor, 0x60) {
        crate::diagnostic!(log("FAIL spark class level or accessor")); return;
    }
    let collision = *((accessor + 0x58) as *const usize);
    if !mapped(collision, 8) { crate::diagnostic!(log("FAIL spark collision module")); return; }
    let vtable = *(collision as *const usize);
    if !mapped(vtable, 0x370) { crate::diagnostic!(log("FAIL spark collision vtable")); return; }
    for slot in [0xc8, 0x368] {
        let function = *((vtable + slot) as *const usize);
        if !mapped(function, 4) { crate::diagnostic!(log("FAIL spark collision callback")); return; }
    }
    crate::diagnostic!(log("CLASS spark owned parameters begin"));
    pgwr_hero_s_owned_spark_class(this, weapon, descriptor);
    crate::diagnostic!(log("CLASS spark owned parameters complete"));
}

/// Call only for the genuine cloned lightning object; owner remains Mythra.
pub(super) unsafe fn lightning_map(weapon: *mut (), owner: *mut BattleObjectModuleAccessor) -> bool {
    if !ready() || !mapped(weapon as usize, 0x28) || !mapped(owner as usize, 0x190)
        || state::get(owner).is_none() { crate::diagnostic!(log("FAIL lightning map arguments")); return false; }
    let _scope = Scope::enter(owner);
    crate::diagnostic!(log("MAP lightning begin"));
    pgwr_hero_s_owned_lightning_map(weapon);
    crate::diagnostic!(log("MAP lightning complete"));
    true
}
pub(super) unsafe fn install() -> bool {
    let base = crate::article::game_base() as usize;
    for &(offset, signature) in signatures::SIGNATURES {
        let Some(address) = base.checked_add(offset) else { crate::diagnostic!(log("FAIL main address overflow")); return false };
        if !mapped(address, signature.len())
            || std::slice::from_raw_parts(address as *const u8, signature.len()) != signature {
            crate::diagnostic!(log(format!("FAIL native 13.0.4 signature offset={:#x}", offset))); return false;
        }
    }
    PGWR_HERO_S_GAME_BASE = base;
    if !super::receiver::install() { return false; }
    skyline::install_hooks!(spark_init, lightning_init, spark_class);
    READY.store(true, Ordering::Release);
    crate::diagnostic!(log("READY native three approved interceptions; 13.0.4 signatures verified"));
    true
}
