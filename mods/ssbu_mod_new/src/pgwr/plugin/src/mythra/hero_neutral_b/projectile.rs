//! Owned fireball Lua states. The cloned weapon retains its genuine work layout.
use super::*;
use smash::{app::{sv_kinetic_energy, *}, lib::L2CValue, lua2cpp::*, phx::*};
use smash_script::*;
use smashline::*;
fn int(name: &str) -> i32 { donor_params::param_fireball_i32(smash::hash40(name)).unwrap() }
fn float(name: &str) -> f32 { donor_params::param_fireball_f32(smash::hash40(name)).unwrap() }

unsafe extern "C" fn pre(w: &mut L2CWeaponCommon) -> L2CValue {
    StatusModule::init_settings(w.module_accessor, SituationKind(*SITUATION_KIND_AIR), *WEAPON_KINETIC_TYPE_NORMAL,
        *GROUND_CORRECT_KIND_AIR as u32, GroundCliffCheckKind(0), false, 0, 0, 0, 0);
    0.into()
}
unsafe fn lifetime(w: &mut L2CWeaponCommon, count: i32) {
    WorkModule::set_int(w.module_accessor, count, *WEAPON_INSTANCE_WORK_ID_INT_INIT_LIFE);
    WorkModule::set_int(w.module_accessor, count, *WEAPON_INSTANCE_WORK_ID_INT_LIFE);
}
unsafe extern "C" fn fly(w: &mut L2CWeaponCommon) -> L2CValue {
    let boma = w.module_accessor;
    let status = StatusModule::status_kind(boma);
    let level = if status == *WEAPON_BRAVE_FIREBALL_STATUS_KIND_FLY_S { 1 }
                else if status == *WEAPON_BRAVE_FIREBALL_STATUS_KIND_FLY_M { 2 } else { 3 };
    let suffix = match level { 1 => "s", 2 => "m", _ => "l" };
    lifetime(w, int(&format!("life_{}", suffix)));
    if level == 3 { WorkModule::set_int(boma, 0, *WEAPON_BRAVE_FIREBALL_INSTANCE_WORK_ID_INT_GROUND_EFFECT_COUNT); }
    MotionModule::change_motion(boma, Hash40::new(&format!("special_n{}", level)), 0.0, 1.0, false, 0.0, false, false);
    let lr = PostureModule::lr(boma);
    let speed = float(if level == 1 { "speed_x_s" } else if level == 2 { "speed_x_m" } else { "init_speed_x_l" }) * lr;
    w.clear_lua_stack(); lua_args!(w, *WEAPON_KINETIC_ENERGY_RESERVE_ID_NORMAL, speed, 0.0);
    sv_kinetic_energy::set_speed(w.lua_state_agent);
    if level == 3 {
        w.clear_lua_stack(); lua_args!(w, *WEAPON_KINETIC_ENERGY_RESERVE_ID_NORMAL, float("accel_x_l") * lr, 0.0);
        sv_kinetic_energy::set_accel(w.lua_state_agent);
        w.clear_lua_stack(); lua_args!(w, *WEAPON_KINETIC_ENERGY_RESERVE_ID_NORMAL, float("max_speed_x_l"), -1.0);
        sv_kinetic_energy::set_limit_speed(w.lua_state_agent);
    }
    crate::diagnostic!(crate::article::log(format!("[PGWR-HERO-N] PROJECTILE fly level={} life={} motion_end={:.1}",
                               level, int(&format!("life_{}", suffix)), MotionModule::end_frame(boma))));
    w.fastshift(L2CValue::Ptr(fly_loop as *const () as _))
}
unsafe fn remove(w: &mut L2CWeaponCommon, reason: &str) -> L2CValue {
    crate::diagnostic!(crate::article::log(format!("[PGWR-HERO-N] PROJECTILE remove reason={} status={:#x}", reason, StatusModule::status_kind(w.module_accessor))));
    EffectModule::detach_all(w.module_accessor, 5);
    notify_event_msc_cmd!(w, Hash40::new_raw(0x199c462b5d));
    0.into()
}
unsafe fn burst_to(w: &mut L2CWeaponCommon, level: i32, reason: &str) -> L2CValue {
    EffectModule::detach_all(w.module_accessor, 5);
    let status = match level { 1 => *WEAPON_BRAVE_FIREBALL_STATUS_KIND_BURST_S,
        2 => *WEAPON_BRAVE_FIREBALL_STATUS_KIND_BURST_M, _ => *WEAPON_BRAVE_FIREBALL_STATUS_KIND_BURST_L };
    crate::diagnostic!(crate::article::log(format!("[PGWR-HERO-N] PROJECTILE burst level={} reason={} frame={:.1}", level, reason, w.global_table[0xe].get_f32())));
    w.change_status(status.into(), false.into());
    0.into()
}
unsafe extern "C" fn fly_loop(w: &mut L2CWeaponCommon) -> L2CValue {
    let boma = w.module_accessor;
    let status = StatusModule::status_kind(boma);
    let level = if status == *WEAPON_BRAVE_FIREBALL_STATUS_KIND_FLY_S { 1 }
                else if status == *WEAPON_BRAVE_FIREBALL_STATUS_KIND_FLY_M { 2 } else { 3 };
    let life = WorkModule::get_int(boma, *WEAPON_INSTANCE_WORK_ID_INT_LIFE);
    let attack = WorkModule::is_flag(boma, *WEAPON_BRAVE_FIREBALL_INSTANCE_WORK_ID_FLAG_ATTACK);
    if life <= 0 {
        if level == 3 && attack { return burst_to(w, level, "hit at expiry"); }
        return remove(w, "life expired");
    }
    let frame = w.global_table[0xe].get_f32();
    let hit_wall = WorkModule::is_flag(boma, *WEAPON_BRAVE_FIREBALL_INSTANCE_WORK_ID_FLAG_HIT_WALL);
    let wall_wait = if level == 3 { 1.0 } else { 2.0 };
    if hit_wall && frame >= wall_wait { return burst_to(w, level, "wall stop finished"); }
    if !hit_wall && w.sub_ground_module_is_touch_all_consider_speed().get_bool() && frame >= 1.0 {
        WorkModule::on_flag(boma, *WEAPON_BRAVE_FIREBALL_INSTANCE_WORK_ID_FLAG_HIT_WALL);
        if frame > 1.0 { return burst_to(w, level, "wall collision"); }
        StopModule::set_other_stop(boma, 2, StopOtherKind(0));
    }
    if attack { return burst_to(w, level, "native hit flag"); }
    if level == 1 && life == int("deccel_start_frame_s") {
        w.clear_lua_stack(); lua_args!(w, *WEAPON_KINETIC_ENERGY_RESERVE_ID_NORMAL, 0.0, 0.0);
        sv_kinetic_energy::set_stable_speed(w.lua_state_agent);
        w.clear_lua_stack(); lua_args!(w, *WEAPON_KINETIC_ENERGY_RESERVE_ID_NORMAL, float("speed_x_s") / life as f32, 0.0);
        sv_kinetic_energy::set_brake(w.lua_state_agent);
    }
    if level == 2 {
        for (attack_id, work_id) in [(0, *WEAPON_BRAVE_FIREBALL_INSTANCE_WORK_ID_INT_EFFECT_HANDLE_M_0),
                                    (1, *WEAPON_BRAVE_FIREBALL_INSTANCE_WORK_ID_INT_EFFECT_HANDLE_M_1)] {
            if !AttackModule::is_attack(boma, attack_id, false) {
                let handle = WorkModule::get_int(boma, work_id);
                if handle != 0 { EffectModule::detach(boma, handle as u32, 5); WorkModule::set_int(boma, 0, work_id); }
            }
        }
    }
    0.into()
}
unsafe extern "C" fn burst(w: &mut L2CWeaponCommon) -> L2CValue {
    let boma = w.module_accessor;
    let status = StatusModule::status_kind(boma);
    let large = status == *WEAPON_BRAVE_FIREBALL_STATUS_KIND_BURST_L;
    let suffix = if large { "l" } else if status == *WEAPON_BRAVE_FIREBALL_STATUS_KIND_BURST_M { "m" } else { "s" };
    if large { GroundModule::set_collidable(boma, false); lifetime(w, int("burst_frame_l")); }
    MotionModule::change_motion(boma, Hash40::new(&format!("burst_{}", suffix)), 0.0, 1.0, false, 0.0, false, false);
    w.clear_lua_stack(); lua_args!(w, *WEAPON_KINETIC_ENERGY_RESERVE_ID_NORMAL, 0.0, 0.0);
    sv_kinetic_energy::set_speed(w.lua_state_agent);
    w.clear_lua_stack(); lua_args!(w, *WEAPON_KINETIC_ENERGY_RESERVE_ID_NORMAL, 0.0, 0.0);
    sv_kinetic_energy::set_accel(w.lua_state_agent);
    w.clear_lua_stack(); lua_args!(w, *WEAPON_KINETIC_ENERGY_RESERVE_ID_NORMAL, 0.0, 0.0);
    sv_kinetic_energy::set_limit_speed(w.lua_state_agent);
    w.fastshift(L2CValue::Ptr(burst_loop as *const () as _))
}
unsafe extern "C" fn burst_loop(w: &mut L2CWeaponCommon) -> L2CValue {
    if StatusModule::status_kind(w.module_accessor) == *WEAPON_BRAVE_FIREBALL_STATUS_KIND_BURST_L
        && WorkModule::get_int(w.module_accessor, *WEAPON_INSTANCE_WORK_ID_INT_LIFE) <= 0 {
        return remove(w, "large burst finished");
    }
    0.into()
}
unsafe extern "C" fn exec(w: &mut L2CWeaponCommon) -> L2CValue {
    let boma = w.module_accessor;
    WorkModule::dec_int(boma, *WEAPON_INSTANCE_WORK_ID_INT_LIFE);
    let status = StatusModule::status_kind(boma);
    if status == *WEAPON_BRAVE_FIREBALL_STATUS_KIND_FLY_L {
        WorkModule::inc_int(boma, *WEAPON_BRAVE_FIREBALL_INSTANCE_WORK_ID_INT_GROUND_EFFECT_COUNT);
        if WorkModule::get_int(boma, *WEAPON_BRAVE_FIREBALL_INSTANCE_WORK_ID_INT_GROUND_EFFECT_COUNT) >= int("effect_check_frame_fly") {
            WorkModule::set_int(boma, 0, *WEAPON_BRAVE_FIREBALL_INSTANCE_WORK_ID_INT_GROUND_EFFECT_COUNT);
            native::pgwr_hero_fireball_owned_effect(boma);
        }
    } else if status == *WEAPON_BRAVE_FIREBALL_STATUS_KIND_BURST_L
        && w.global_table[0xe].get_f32() == int("effect_check_frame_burst") as f32 {
        native::pgwr_hero_fireball_owned_effect(boma);
    }
    0.into()
}
unsafe extern "C" fn end(_: &mut L2CWeaponCommon) -> L2CValue { 0.into() }
pub(super) fn install() {
    let mut agent = Agent::new("elight_pgwr_hero_fireball");
    for status in [*WEAPON_BRAVE_FIREBALL_STATUS_KIND_FLY_S, *WEAPON_BRAVE_FIREBALL_STATUS_KIND_FLY_M,
        *WEAPON_BRAVE_FIREBALL_STATUS_KIND_FLY_L, *WEAPON_BRAVE_FIREBALL_STATUS_KIND_BURST_S,
        *WEAPON_BRAVE_FIREBALL_STATUS_KIND_BURST_M, *WEAPON_BRAVE_FIREBALL_STATUS_KIND_BURST_L] {
        agent.status(Pre, status, pre); agent.status(End, status, end);
        let flying = [*WEAPON_BRAVE_FIREBALL_STATUS_KIND_FLY_S, *WEAPON_BRAVE_FIREBALL_STATUS_KIND_FLY_M,
                      *WEAPON_BRAVE_FIREBALL_STATUS_KIND_FLY_L].contains(&status);
        agent.status(Main, status, if flying { fly } else { burst });
        if flying || status == *WEAPON_BRAVE_FIREBALL_STATUS_KIND_BURST_L { agent.status(Exec, status, exec); }
    }
    agent.install();
}
