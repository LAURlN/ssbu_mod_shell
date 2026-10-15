//! Owned, unboosted Gaogaen back throw. Eflame status 0x208 allocated 2026-10-03.
//! Native evidence: evidence/2026-10-02_pgwr_gaogaen_throw_b/ROUTES.json.
//! No Gaogaen specializer or Gaogaen work storage is used on the recipient.
use smash::{app::{self, lua_bind::*, sv_battle_object, BattleObjectModuleAccessor},
    lib::{L2CValue, lua_const::*}, lua2cpp::*, phx::{Hash40, simd::Vector3}};
use smashline::*;
use std::{cell::Cell, sync::atomic::{AtomicI32, Ordering}};
#[path = "gaogaen_throw_b_data.rs"] mod data;
static OWN_STATUS: AtomicI32 = AtomicI32::new(-1);
thread_local! { static OWN_VICTIM_INIT: Cell<bool> = Cell::new(false); }
struct VictimContext(bool);
impl Drop for VictimContext {
    fn drop(&mut self) { OWN_VICTIM_INIT.with(|v| v.set(self.0)); }
}

fn log(text: String) {
    use std::io::Write;
    crate::diagnostic!(println!("[pgwr:gaogaen_throw_b] {}", text));
    if let Ok(mut f) = std::fs::OpenOptions::new().create(true).append(true)
        .open("sd:/ultimate/pgwr_gaogaen_throw_b_log.txt") {
        let _ = writeln!(f, "[pgwr:gaogaen_throw_b] {}", text);
    }
}

unsafe fn owns_attacker(bma: *mut BattleObjectModuleAccessor) -> bool {
    let id = OWN_STATUS.load(Ordering::Relaxed);
    id >= 0 && !bma.is_null() && app::utility::get_kind(&mut *bma) == *FIGHTER_KIND_EFLAME
        && StatusModule::status_kind(bma) == id
}

unsafe fn owns_victim(bma: *mut BattleObjectModuleAccessor) -> bool {
    if bma.is_null() || !LinkModule::is_link(bma, *LINK_NO_CAPTURE) { return false; }
    let parent = LinkModule::get_parent_id(bma, *LINK_NO_CAPTURE, true) as u32;
    if parent == *BATTLE_OBJECT_ID_INVALID as u32 || !sv_battle_object::is_active(parent) {
        return false;
    }
    owns_attacker(sv_battle_object::module_accessor(parent))
}

// These are ordinary exported game symbols, not raw-offset/framework hooks.
extern "C" {
    #[link_name = "_ZN7lua2cpp16L2CFighterCommon20status_Thrown_commonEv"]
    fn native_thrown_common(fighter: &mut L2CFighterCommon) -> L2CValue;
}

#[skyline::hook(replace = native_thrown_common)]
unsafe extern "C" fn thrown_common(fighter: &mut L2CFighterCommon) -> L2CValue {
    let owned = owns_victim(fighter.module_accessor);
    let previous = OWN_VICTIM_INIT.with(|v| v.replace(owned));
    let _context = VictimContext(previous);
    // Keep the victim's own clip, links, stop callback, flip, scale and cleanup.
    let result = original!()(fighter);
    if owned { crate::diagnostic!(log(format!("VICTIM_INIT kind={} motion={:#x}",
        app::utility::get_kind(&mut *fighter.module_accessor),
        MotionModule::motion_kind(fighter.module_accessor)))); }
    result
}

#[skyline::hook(replace = FighterParamAccessor2::thrown_offset)]
unsafe extern "C" fn thrown_offset(accessor: *mut app::FighterParamAccessor2,
    captor_kind: i32, victim_kind: i32, direction: i32) -> Vector3 {
    if OWN_VICTIM_INIT.with(|v| v.get()) && captor_kind == *FIGHTER_KIND_EFLAME
        && direction == 1 && victim_kind >= 0 && victim_kind < 94 {
        // Native accessor aliases 0x4c to 0x4b before indexing its row map.
        let kind = if victim_kind == 0x4c { 0x4b } else { victim_kind } as usize;
        let v = data::BACK_OFFSETS[kind];
        return Vector3::new(v[0], v[1], v[2]);
    }
    original!()(accessor, captor_kind, victim_kind, direction)
}

#[skyline::hook(replace = smash::lua2cpp::L2CFighterCommon_sub_is_not_throw_status_kind)]
unsafe extern "C" fn is_not_throw(fighter: &mut L2CFighterCommon, kind: L2CValue) -> L2CValue {
    if kind.get_i32() == OWN_STATUS.load(Ordering::Relaxed)
        && (owns_attacker(fighter.module_accessor) || owns_victim(fighter.module_accessor)) {
        return false.into();
    }
    original!()(fighter, kind)
}

unsafe extern "C" fn entry_pre(fighter: &mut L2CFighterCommon) -> L2CValue {
    let bma = fighter.module_accessor;
    if WorkModule::get_int64(bma, *FIGHTER_STATUS_CATCH_WAIT_WORK_INT_MOTION_KIND)
        == Hash40::new("throw_b").hash {
        StatusModule::set_status_kind_interrupt(bma, OWN_STATUS.load(Ordering::Relaxed));
        return 1.into();
    }
    original_status(Pre, fighter, *FIGHTER_STATUS_KIND_THROW)(fighter)
}

unsafe extern "C" fn pre(fighter: &mut L2CFighterCommon) -> L2CValue {
    let bma = fighter.module_accessor;
    StatusModule::init_settings(bma, app::SituationKind(*SITUATION_KIND_GROUND),
        *FIGHTER_KINETIC_TYPE_MOTION, *GROUND_CORRECT_KIND_GROUND_CLIFF_STOP as u32,
        app::GroundCliffCheckKind(*GROUND_CLIFF_CHECK_KIND_NONE), true,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_THROW_FLAG, *FIGHTER_STATUS_WORK_KEEP_FLAG_THROW_INT,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_THROW_FLOAT, 0);
    FighterStatusModuleImpl::set_fighter_status_data(bma, false, *FIGHTER_TREADED_KIND_NO_REAC,
        false, true, false, (*FIGHTER_LOG_MASK_FLAG_THROW | *FIGHTER_LOG_MASK_FLAG_ACTION_CATEGORY_KEEP) as u64,
        (*FIGHTER_STATUS_ATTR_HIDE_NAME_CURSOR | *FIGHTER_STATUS_ATTR_DISABLE_TURN_DAMAGE) as u32,
        *FIGHTER_POWER_UP_ATTACK_BIT_THROW as u32, 0);
    0.into()
}

unsafe extern "C" fn init(fighter: &mut L2CFighterCommon) -> L2CValue {
    // Direction work remains throw_b, so the shared event selects thrown_b.
    // The playing attacker motion is independently owned below.
    fighter.sub_throw_uniq_process_init()
}

unsafe extern "C" fn main(fighter: &mut L2CFighterCommon) -> L2CValue {
    let bma = fighter.module_accessor;
    ItemModule::set_have_item_visibility(bma, false, 0);
    let rate = WorkModule::get_float(bma, *FIGHTER_STATUS_THROW_WORK_FLOAT_MOTION_RATE);
    MotionModule::change_motion(bma, Hash40::new("pgwr_gaogaen_throw_b"), 0.0, rate,
        false, 0.0, false, false);
    fighter.ThrowLogCommon();
    if !StopModule::is_stop(bma) { fighter.ThrowUniq(); }
    fighter.global_table[0x14].assign(&L2CValue::Ptr(uniq as *const () as _));
    crate::diagnostic!(log(format!("ENTER status={} clip_end={} target={}", OWN_STATUS.load(Ordering::Relaxed),
        MotionModule::end_frame(bma), WorkModule::get_int(bma, *FIGHTER_STATUS_THROW_WORK_INT_TARGET_OBJECT))));
    fighter.sub_shift_status_main(L2CValue::Ptr(main_loop as *const () as _))
}

unsafe extern "C" fn uniq(fighter: &mut L2CFighterCommon) -> L2CValue { fighter.ThrowUniq() }
unsafe extern "C" fn main_loop(fighter: &mut L2CFighterCommon) -> L2CValue { fighter.status_Throw_Main() }
unsafe extern "C" fn end(fighter: &mut L2CFighterCommon) -> L2CValue {
    AttackModule::clear_all(fighter.module_accessor);
    if WorkModule::is_flag(fighter.module_accessor, *FIGHTER_STATUS_THROW_FLAG_INVINCIBLE) {
        HitModule::set_whole(fighter.module_accessor, app::HitStatus(*HIT_STATUS_NORMAL), 0);
        WorkModule::off_flag(fighter.module_accessor, *FIGHTER_STATUS_THROW_FLAG_INVINCIBLE);
    }
    crate::diagnostic!(log(format!("END next={} frame={}", fighter.global_table[0xb].get_i32(),
        MotionModule::frame(fighter.module_accessor))));
    fighter.status_end_Throw()
}

fn common_loaded(info: &skyline::nro::NroInfo) {
    if info.name == "common" {
        skyline::install_hooks!(thrown_common, is_not_throw);
    }
}

/// Fixed user-authorized allocation; registration is enabled in ordinary builds.
pub fn install() {
    let id = crate::status::STATUS_GAOGAEN_THROW_B;
    assert_eq!(*FIGHTER_EFLAME_STATUS_KIND_NUM, 0x1ee);
    assert!(id > crate::status::STATUS_SNAKE_N_THROW);
    OWN_STATUS.store(id, Ordering::Relaxed);
    skyline::install_hooks!(thrown_offset);
    if skyline::nro::add_hook(common_loaded).is_err() {
        OWN_STATUS.store(-1, Ordering::Relaxed);
        crate::diagnostic!(log("DISABLED common NRO callback unavailable".into()));
        return;
    }
    Agent::new("eflame").set_costume(crate::TARGET_COSTUMES.to_vec())
        .status(Pre, *FIGHTER_STATUS_KIND_THROW, entry_pre)
        .status(Pre, id, pre).status(Init, id, init).status(Main, id, main)
        .status(End, id, end).install();
    crate::diagnostic!(log(format!("REGISTERED status={:#x} fighter=eflame costumes={:?}", id, crate::TARGET_COSTUMES)));
}
