//! Owned 13.0.4 fireball initializer. User-authorized plugin-local exception.
//! Original Hero calls pass through; no framework plugin is changed.
use smash::app::BattleObjectModuleAccessor;
use skyline::hooks::InlineCtx;
#[path = "signatures.rs"]
mod signatures;
use std::sync::atomic::{AtomicBool, Ordering};

static READY: AtomicBool = AtomicBool::new(false);
static OWNED_INIT: AtomicBool = AtomicBool::new(false);

// Hero's decoded vl.prc object, *(*(main+0x52bb3b0)+0x1298), exists only when a real
// Hero is loaded. The fireball class constructor (main+0x33c8ea0) reads only
// map_collision_fireball{,_m,_l} {up, down, half_width} at +0x194/+0x1a4/+0x1b4.
// Offsets checked against the decoder by gen_hero_fireball_initializer.py.
#[repr(C)]
struct NativeParams {
    unused: [u8; 0x194],
    levels: [[f32; 4]; 3],
}
const fn native_params() -> NativeParams {
    let m = super::donor_params::MAP_COLLISION_FIREBALL;
    // Column 3 is the next level's shape_type, which the constructor does not read.
    NativeParams { unused: [0; 0x194], levels: [
        [m[0][0], m[0][1], m[0][2], 0.0], [m[1][0], m[1][1], m[1][2], 0.0], [m[2][0], m[2][1], m[2][2], 0.0]] }
}
static PARAMS: NativeParams = native_params();
#[no_mangle]
static mut PGWR_HERO_GAME_BASE: usize = 0;
core::arch::global_asm!(include_str!("initializer_1304.s"), options(raw));
extern "C" {
    fn pgwr_hero_fireball_owned_init(controller: *const u64,
                                   owner: *mut BattleObjectModuleAccessor) -> u64;
    pub(super) fn pgwr_hero_fireball_owned_effect(weapon: *mut BattleObjectModuleAccessor);
}

pub fn ready() -> bool { READY.load(Ordering::Acquire) }

#[no_mangle]
unsafe extern "C" fn pgwr_hero_n_charge(owner: *mut BattleObjectModuleAccessor) -> i32 {
    super::charge(owner)
}

#[no_mangle]
unsafe extern "C" fn pgwr_hero_n_param_int(_: *const (), _: u64, child: u64) -> i32 {
    super::donor_params::param_special_n_i32(child).unwrap_or(0)
}

#[no_mangle]
unsafe extern "C" fn pgwr_hero_n_param_float(_: *const (), _: u64, child: u64) -> f32 {
    super::donor_params::param_special_n_f32(child).unwrap_or(0.0)
}

#[no_mangle]
unsafe extern "C" fn pgwr_hero_fireball_param_int(_: *const (), _: u64, child: u64) -> i32 {
    super::donor_params::param_fireball_i32(child).unwrap_or(0)
}

#[no_mangle]
unsafe extern "C" fn pgwr_hero_fireball_param_float(_: *const (), _: u64, child: u64) -> f32 {
    super::donor_params::param_fireball_f32(child).unwrap_or(0.0)
}

#[skyline::hook(offset = 0x85cf70)]
unsafe fn initialize(controller: *const u64, owner: *mut BattleObjectModuleAccessor) -> u64 {
    if !super::target(owner) {
        return original!()(controller, owner);
    }
    if !ready() || !super::address_ok(controller as usize, 8) {
        crate::diagnostic!(crate::article::log("[PGWR-HERO-N] FAIL initializer unavailable or invalid controller".into()));
        return 0;
    }
    crate::diagnostic!(crate::article::log(format!("[PGWR-HERO-N] INIT begin entry={} charge={}",
                               super::entry(owner).unwrap_or(99), super::charge(owner))));
    OWNED_INIT.store(true, Ordering::Relaxed);
    let result = pgwr_hero_fireball_owned_init(controller, owner);
    OWNED_INIT.store(false, Ordering::Relaxed);
    crate::diagnostic!(crate::article::log(format!("[PGWR-HERO-N] INIT complete result={:#x}", result)));
    result
}

// Immediately AFTER ldr x21,[x8,#0x1298] in the fireball constructor; x2 is the
// spawn descriptor (+0x28 = level 0..2). Scoped to our owned initializer call, so
// a real Hero's fireball keeps his own object.
#[skyline::hook(offset = 0x33c8ec4, inline)]
unsafe fn native_map_collision(ctx: &mut InlineCtx) {
    if !OWNED_INIT.load(Ordering::Relaxed) { return; }
    let donor = ctx.registers[21].x();
    ctx.registers[21].set_x(&PARAMS as *const NativeParams as u64);
    let desc = ctx.registers[2].x() as usize;
    let level = if super::address_ok(desc, 4) { *((desc + 0x28) as *const i32) } else { -1 };
    crate::diagnostic!(crate::article::log(format!("[PGWR-HERO-N] NATIVE map collision supplied level={} hero_object={}",
                               level, if donor == 0 { "absent" } else { "present" })));
}

pub unsafe fn install() -> bool {
    let base = crate::article::game_base() as usize;
    if !super::address_ok(base, 4) {
        crate::diagnostic!(crate::article::log("[PGWR-HERO-N] FAIL invalid main base".into()));
        return false;
    }
    for &(offset, expected) in signatures::SIGNATURES {
        let actual = std::slice::from_raw_parts((base + offset) as *const u8, expected.len());
        if actual != expected {
            crate::diagnostic!(crate::article::log(format!("[PGWR-HERO-N] FAIL 13.0.4 signature offset={:#x}", offset)));
            return false;
        }
    }
    PGWR_HERO_GAME_BASE = base;
    READY.store(true, Ordering::Release);
    skyline::install_hooks!(initialize, native_map_collision);
    crate::diagnostic!(crate::article::log("[PGWR-HERO-N] READY owned initializer + map collision bridge; 13.0.4 signatures verified".into()));
    true
}
