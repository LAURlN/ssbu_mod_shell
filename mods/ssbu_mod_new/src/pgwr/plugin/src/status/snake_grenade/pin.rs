//! Owned clone of Snake's separate pin prop, not his item-backed grenade article.
//! Descriptor and byte signatures are audited by audit_snake_grenade_native.py.
use smash::{app::{lua_bind::*, ArticleOperationTarget}, lib::lua_const::*, lua2cpp::*, phx::Hash40};
use std::sync::atomic::{AtomicI32, Ordering};
static PIN: AtomicI32 = AtomicI32::new(-1);

pub(super) fn install() {
    let index = smashline::clone_weapon("snake", *WEAPON_KIND_SNAKE_GRENADE,
                                      "eflame", "pgwr_snake_pin", false);
    PIN.store(*FIGHTER_EFLAME_ARTICLE_TERM + index, Ordering::Release);
    crate::diagnostic!(super::log(format!("PIN READY local article={} owned pgwr_snake_pin", id())));
}
fn id() -> i32 { PIN.load(Ordering::Acquire) }
pub(super) unsafe fn generate(agent: &mut L2CAgentBase) {
    let boma = agent.module_accessor;
    if id() < 0 { crate::diagnostic!(super::log("PIN FAIL not registered".into())); return; }
    ArticleModule::generate_article(boma, id(), false, -1);
    motion(boma, false);
    crate::diagnostic!(super::log(format!("PIN spawned entry={} exists={}", super::entry(boma), ArticleModule::is_exist(boma, id()))));
}
pub(super) unsafe fn visibility(boma: *mut smash::app::BattleObjectModuleAccessor, visible: bool) {
    if id() >= 0 {
        ArticleModule::set_visibility_whole(boma, id(), visible, ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL));
    }
}
pub(super) unsafe fn motion(boma: *mut smash::app::BattleObjectModuleAccessor, inherit: bool) {
    if id() < 0 || !ArticleModule::is_exist(boma, id()) { return; }
    let name = if StatusModule::situation_kind(boma) == *SITUATION_KIND_GROUND {
        "pgwr_snake_pin_start"
    } else { "pgwr_snake_pin_air_start" };
    ArticleModule::change_motion(boma, id(), Hash40::new(name), inherit, -1.0);
}
pub(super) unsafe fn remove(boma: *mut smash::app::BattleObjectModuleAccessor) {
    if id() >= 0 { ArticleModule::remove_exist(boma, id(), ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL)); }
}
