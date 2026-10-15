//! Cloned genuine spark/lightning objects with independently allocated Mythra slots.
use super::{logging::log, native, state};
use smash::{app::{lua_bind::*, BattleObjectModuleAccessor}, lib::lua_const::*};
use std::sync::atomic::{AtomicI32, Ordering};
static SPARK: AtomicI32 = AtomicI32::new(-1);
#[no_mangle]
pub(super) static PGWR_HERO_S_LIGHTNING_SLOT: AtomicI32 = AtomicI32::new(-1);
use PGWR_HERO_S_LIGHTNING_SLOT as LIGHTNING;

pub(super) unsafe fn install() {
    let spark = smashline::clone_weapon("brave", *WEAPON_KIND_BRAVE_SPARK,
        "elight", "pgwr_hero_spark", false);
    let lightning = smashline::clone_weapon("brave", *WEAPON_KIND_BRAVE_LIGHTNING,
        "elight", "pgwr_hero_lightning", false);
    SPARK.store(*FIGHTER_ELIGHT_ARTICLE_TERM + spark, Ordering::Release);
    LIGHTNING.store(*FIGHTER_ELIGHT_ARTICLE_TERM + lightning, Ordering::Release);
    crate::diagnostic!(log(format!("ARTICLES spark={} lightning={}", SPARK.load(Ordering::Acquire), LIGHTNING.load(Ordering::Acquire))));
}
pub(super) unsafe fn lightning_count(owner: *mut BattleObjectModuleAccessor) -> i32 {
    let id = LIGHTNING.load(Ordering::Acquire);
    if id < 0 || state::get(owner).is_none() { return 0; }
    ArticleModule::get_active_num(owner, id) as i32
}
pub(super) unsafe fn generate_spark(owner: *mut BattleObjectModuleAccessor) {
    generate(owner, SPARK.load(Ordering::Acquire), "spark");
}
pub(super) unsafe fn generate_lightning(owner: *mut BattleObjectModuleAccessor) {
    generate(owner, LIGHTNING.load(Ordering::Acquire), "lightning");
}
unsafe fn generate(owner: *mut BattleObjectModuleAccessor, id: i32, name: &str) {
    if !native::ready() || id < 0 || state::get(owner).is_none() {
        crate::diagnostic!(log(format!("FAIL SPAWN {} unavailable", name))); return;
    }
    crate::diagnostic!(log(format!("SPAWN {} begin status={:#x} count={}", name,
        StatusModule::status_kind(owner), ArticleModule::get_active_num(owner, id))));
    ArticleModule::generate_article(owner, id, false, -1);
    crate::diagnostic!(log(format!("SPAWN {} complete count={}", name, ArticleModule::get_active_num(owner, id))));
}
