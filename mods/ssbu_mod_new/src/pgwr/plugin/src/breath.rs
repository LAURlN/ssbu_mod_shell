//! 13.0.4 breath clone parameter bridge. See REPORT_0.14.0_UPAIR.md.
//! Keep the native constructor and donor status/ACMD; provide only the missing
//! G&W parameters. Never publish a fake fighter parameter object to the game.
use smash::{app::{self, lua_bind::*, BattleObjectModuleAccessor}, lib::lua_const::*};
use skyline::hooks::InlineCtx;
use std::sync::atomic::{AtomicBool, Ordering};

static READY: AtomicBool = AtomicBool::new(false);
static SPAWNING: AtomicBool = AtomicBool::new(false);

// Decoder at main+0xa98138..0xa98684 and export/fighter/gamewatch/param/vl.prc.
// The constructor reads only +0x118, +0x11c and +0x12c. Padding makes those
// addresses valid without pointer arithmetic outside an allocation.
#[repr(C)]
struct NativeParams {
    unused: [u8; 0x118],
    pos_x: f32,
    pos_y: f32,
    life: i32,
    interval: i32,
    speed_y: f32,
    scale: f32,
}
static PARAMS: NativeParams = NativeParams {
    unused: [0; 0x118], pos_x: 0.5, pos_y: 21.5,
    life: 34, interval: 7, speed_y: 8.5, scale: 1.9,
};

pub fn ready() -> bool { READY.load(Ordering::Relaxed) }

unsafe fn target_fighter(boma: *mut BattleObjectModuleAccessor) -> bool {
    !boma.is_null()
        && app::utility::get_category(&mut *boma) == *BATTLE_OBJECT_CATEGORY_FIGHTER
        && app::utility::get_kind(&mut *boma) == *FIGHTER_KIND_EFLAME
        && crate::TARGET_COSTUMES.contains(&(WorkModule::get_int(
            boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR) as usize))
}

unsafe fn target_breath(boma: *mut BattleObjectModuleAccessor) -> bool {
    if boma.is_null()
        || app::utility::get_category(&mut *boma) != *BATTLE_OBJECT_CATEGORY_WEAPON
        || app::utility::get_kind(&mut *boma) != *WEAPON_KIND_GAMEWATCH_BREATH {
        return false;
    }
    // Founder survives reflection; using the current link owner would make the
    // movement interval disappear when another fighter reflects the puff.
    let founder = WorkModule::get_int(boma, *WEAPON_INSTANCE_WORK_ID_INT_ACTIVATE_FOUNDER_ID) as u32;
    if !app::sv_battle_object::is_active(founder) { return false; }
    target_fighter(app::sv_battle_object::module_accessor(founder))
}

// Immediately AFTER ldr x24,[x8,#0x690]. x23 is the breath module accessor.
// This constructor is breath-specific. The scope covers only our synchronous
// generate_article call, never a real G&W spawn or another fighter's projectile.
#[skyline::hook(offset = 0x33fc140, inline)]
unsafe fn native_params(ctx: &mut InlineCtx) {
    if SPAWNING.load(Ordering::Relaxed) {
        let boma = ctx.registers[23].x() as *mut BattleObjectModuleAccessor;
        if !boma.is_null() && app::utility::get_kind(&mut *boma) == *WEAPON_KIND_GAMEWATCH_BREATH {
            ctx.registers[24].set_x(&PARAMS as *const NativeParams as u64);
            crate::diagnostic!(crate::article::log("BREATH native spawn parameters supplied".into()));
        }
    }
}

pub unsafe fn handle_param_int(boma: *mut BattleObjectModuleAccessor, parent: u64, child: u64) -> Option<i32> {
    if parent == smash::hash40("param_breath") && target_breath(boma) {
        if child == smash::hash40("life") {
            crate::diagnostic!(crate::article::log("BREATH donor status parameters supplied: life 34".into()));
            return Some(PARAMS.life);
        }
        if child == smash::hash40("move_interval") {
            return Some(PARAMS.interval);
        }
    }
    None
}

pub unsafe fn handle_param_float(boma: *mut BattleObjectModuleAccessor, parent: u64, child: u64) -> Option<f32> {
    if parent == smash::hash40("param_breath") && target_breath(boma) {
        if child == smash::hash40("speed_y") { return Some(PARAMS.speed_y); }
        if child == smash::hash40("scale_mul") { return Some(PARAMS.scale); }
        if child == smash::hash40("pos_offset_x") { return Some(PARAMS.pos_x); }
        if child == smash::hash40("pos_offset_y") { return Some(PARAMS.pos_y); }
    }
    None
}

pub unsafe fn generate(boma: *mut BattleObjectModuleAccessor) {
    if !ready() || !target_fighter(boma) { return; }
    let previous = SPAWNING.swap(true, Ordering::Relaxed);
    ArticleModule::generate_article(boma, crate::article::breath(), false, -1);
    SPAWNING.store(previous, Ordering::Relaxed);
}

pub fn install() {
    unsafe {
        let base = crate::article::game_base();
        // Verify the whole native constructor before installing any of the hooks.
        let expected = include_bytes!("breath_init_1304.bin");
        let actual = std::slice::from_raw_parts(base.add(0x33fc110), expected.len());
        if actual != expected {
            crate::diagnostic!(crate::article::log("BREATH disabled: native constructor differs from audited 13.0.4".into()));
            return;
        }
        skyline::install_hooks!(native_params);
    }
    READY.store(true, Ordering::Relaxed);
    crate::diagnostic!(crate::article::log("BREATH parameter bridge ready: life 34, interval 7, speed 8.5, scale 1.9".into()));
}
