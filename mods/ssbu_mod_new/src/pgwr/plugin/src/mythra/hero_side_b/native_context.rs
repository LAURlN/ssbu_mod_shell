//! Scoped owner context for copied native callbacks; never aliases Hero work.
//! Callers must validate the owner accessor before entering this scope.
use super::state::{self, State};
use smash::app::BattleObjectModuleAccessor;
use std::{cell::Cell, sync::atomic::Ordering};

thread_local! { static OWNER: Cell<*mut BattleObjectModuleAccessor> = Cell::new(std::ptr::null_mut()); }
pub(super) struct Scope(*mut BattleObjectModuleAccessor);
impl Scope {
    pub(super) unsafe fn enter(owner: *mut BattleObjectModuleAccessor) -> Self {
        Self(OWNER.with(|slot| slot.replace(owner)))
    }
}
impl Drop for Scope {
    fn drop(&mut self) { OWNER.with(|slot| slot.set(self.0)); }
}
unsafe fn current() -> Option<&'static State> {
    // Cell borrow ends before invoking the engine's generic accessor checks.
    let owner = OWNER.with(Cell::get);
    state::get(owner)
}
pub(super) fn active() -> bool { OWNER.with(|slot| !slot.get().is_null()) }
pub(super) fn owner() -> *mut BattleObjectModuleAccessor { OWNER.with(Cell::get) }

#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_special_float(_: *const (), _: u64, child: u64) -> f32 {
    super::params::param_special_s_f32(child).unwrap_or_else(|| {
        crate::diagnostic!(super::logging::log(format!("FAIL unknown special_s float key={:#x}", child)));
        0.0
    })
}
macro_rules! float_field {
    ($name:ident, $field:ident) => {
        #[no_mangle]
        unsafe extern "C" fn $name(_: *const (), _: i32) -> f32 {
            current().map(|s| f32::from_bits(s.$field.load(Ordering::Relaxed))).unwrap_or(0.0)
        }
    };
}
float_field!(pgwr_hero_s_generate_x, generate_x);
float_field!(pgwr_hero_s_generate_y, generate_y);
float_field!(pgwr_hero_s_generate_lr, generate_lr);
float_field!(pgwr_hero_s_lightning_offset, lightning_offset_x);

#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_lightning_owner(_: *const (), _: i32) -> u32 {
    current().map(|s| s.lightning_owner.load(Ordering::Relaxed)).unwrap_or(u32::MAX)
}
#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_lightning_team(_: *const (), _: i32) -> i32 {
    current().map(|s| s.lightning_team.load(Ordering::Relaxed)).unwrap_or(-1)
}
#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_spark_log_get(_: *const (), _: i32) -> i32 {
    current().map(|s| s.spark_log_group.load(Ordering::Relaxed)).unwrap_or(-1)
}
#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_spark_log_set(_: *const (), value: i32, _: i32) {
    if let Some(s) = current() { s.spark_log_group.store(value, Ordering::Relaxed); }
}
#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_spark_log_ref(_: *const (), _: i32) {
    if let Some(s) = current() { s.spark_log_references.fetch_add(1, Ordering::Relaxed); }
}
#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_explosion_get(_: *const (), _: i32) -> bool {
    current().map(|s| s.flag(state::CALL_EXPLOSION)).unwrap_or(false)
}
#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_explosion_set(_: *const (), _: i32) {
    if let Some(s) = current() { s.set(state::CALL_EXPLOSION); }
}
#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_lightning_article_count(_: *const (), _: i32) -> i32 {
    super::articles::lightning_count(owner())
}
#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_lightning_log_get(_: *const (), _: i32) -> i32 {
    current().map(|s| s.lightning_log_group.load(Ordering::Relaxed)).unwrap_or(-1)
}
#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_lightning_log_set(_: *const (), value: i32, _: i32) {
    if let Some(s) = current() { s.lightning_log_group.store(value, Ordering::Relaxed); }
}
#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_lightning_owner_set(_: *const (), value: u32, _: i32) {
    if let Some(s) = current() { s.lightning_owner.store(value, Ordering::Relaxed); }
}
#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_lightning_team_set(_: *const (), value: i32, _: i32) {
    if let Some(s) = current() { s.lightning_team.store(value, Ordering::Relaxed); }
}
#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_spark_log_ref_get(_: *const (), _: i32) -> i32 {
    current().map(|s| s.spark_log_references.load(Ordering::Relaxed)).unwrap_or(0)
}
#[no_mangle]
unsafe extern "C" fn pgwr_hero_s_spark_log_ref_set(_: *const (), value: i32, _: i32) {
    if let Some(s) = current() { s.spark_log_references.store(value, Ordering::Relaxed); }
}
