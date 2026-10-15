//! Hero's side-B (Zap / Zapple / Kazap) on Mythra c06/c07, behind Cargo feature
//! `hero-side-b`. Owned statuses `0x1FA..0x1FE`; the pair's mana meter is
//! `super::hero_mana` (T-0057): ATTACK1/2/3 debit it exactly where the donor's
//! three ATTACK MAIN bodies debit, and the finisher does not.
//!
//! * `fighter` / `fighter_loops` / `exec`: the donor's 25 status callbacks (NRO-translated)
//! * `game_acmd` / `attack3_acmd` / `script_acmd`: fighter scripts
//! * `articles` / `weapon`: cloned spark + lightning with owned Lua states and scripts
//! * `native` / `receiver`: signature-checked owned copies of the Hero-reading native
//!   initializers and the Mythra event receiver (user-approved sites only)
//!
//! Crash-tail log: `sd:/ultimate/pgwr_hero_s_log.txt`.
mod articles;
mod attack3_acmd;
mod exec;
mod fighter;
mod fighter_loops;
mod game_acmd;
mod logging;
mod native;
mod native_context;
mod params;
mod receiver;
mod registration;
mod script_acmd;
mod state;
mod weapon;

use smash::{app::{self, lua_bind::*, BattleObjectModuleAccessor}, hash40, lib::lua_const::*};

/// This spell's status span, `(first, last)` inclusive, for `hero_mana`.
/// `hero_mana` asserts its own copy against this at install, so a change to the
/// allocation fails at load rather than pausing recovery on the wrong ids.
pub(super) const SPELL_SPAN: (i32, i32) = (registration::ATTACK1, registration::HOLD);

unsafe fn owned_weapon(boma: *mut BattleObjectModuleAccessor, kind: i32) -> bool {
    if boma.is_null() || app::utility::get_category(&mut *boma) != *BATTLE_OBJECT_CATEGORY_WEAPON
        || app::utility::get_kind(&mut *boma) != kind { return false; }
    let founder = WorkModule::get_int(boma, *WEAPON_INSTANCE_WORK_ID_INT_ACTIVATE_FOUNDER_ID) as u32;
    app::sv_battle_object::is_active(founder)
        && state::get(app::sv_battle_object::module_accessor(founder)).is_some()
}

/// Hero's vl.prc is not loaded for Mythra; answer the donor keys from the pinned copy.
pub unsafe fn handle_param_int(boma: *mut BattleObjectModuleAccessor, parent: u64, child: u64) -> Option<i32> {
    if parent == hash40("param_spark") && owned_weapon(boma, *WEAPON_KIND_BRAVE_SPARK) {
        return params::param_spark_i32(child);
    }
    if parent == hash40("param_lightning") && owned_weapon(boma, *WEAPON_KIND_BRAVE_LIGHTNING) {
        return params::param_lightning_i32(child);
    }
    if parent == hash40("param_special_s") && state::get(boma).is_some() {
        return params::param_special_s_i32(child);
    }
    None
}
pub unsafe fn handle_param_float(boma: *mut BattleObjectModuleAccessor, parent: u64, child: u64) -> Option<f32> {
    if parent == hash40("param_spark") && owned_weapon(boma, *WEAPON_KIND_BRAVE_SPARK) {
        return params::param_spark_f32(child);
    }
    if parent == hash40("param_lightning") && owned_weapon(boma, *WEAPON_KIND_BRAVE_LIGHTNING) {
        return params::param_lightning_f32(child);
    }
    if parent == hash40("param_special_s") && state::get(boma).is_some() {
        return params::param_special_s_f32(child);
    }
    None
}

pub fn install() {
    crate::diagnostic!(logging::log(format!("BOOT v{}", env!("CARGO_PKG_VERSION"))));
    unsafe {
        if !native::install() {
            crate::diagnostic!(logging::log("FAIL native install; Mythra side-B left stock"));
            return;
        }
        articles::install();
    }
    registration::install(fighter::callbacks());
    game_acmd::install();
    script_acmd::install();
    weapon::install();
    crate::diagnostic!(logging::log(format!("REGISTERED c06/c07 statuses={:#x}-{:#x} mana=on (pair meter, T-0057)",
                         registration::ATTACK1, registration::HOLD)));
}
