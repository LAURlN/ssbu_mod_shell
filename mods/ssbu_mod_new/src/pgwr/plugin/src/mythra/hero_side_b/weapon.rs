//! Owned Lua states and scripts for the cloned spark and lightning weapons.
//! Statuses: pinned NRO 0x485c0/0x47ca0../0x47c10 (spark) and 0x46af0/0x45b80/
//! 0x45af0/0x457f0/0x45600/0x46080 (lightning). Game scripts: dump text checked
//! argument-for-argument against native 0x196330/0x195280/0x1941d0/0x18f4b0.
//! The cloned weapons keep their genuine work layout, so their own work ids are used.
use super::{logging::log, native, params, state::{self, LIGHTNING_ARRIVED}};
use smash::{app::{self, lua_bind::*, sv_animcmd::wait, *}, lib::{lua_const::*, L2CValue},
            lua2cpp::*, phx::{Hash40, Vector3f}};
use smash_script::{macros::*, *};
use smashline::*;

const REMOVE: u64 = 0x199c462b5d;

// Pinned vl.prc keys; the native code names them only by hash.
const SPARK_LIFE_S: u64 = 0x6fea8bbb7;
const SPARK_LIFE_M: u64 = 0x604a786d4;
const SPARK_LIFE_L: u64 = 0x673a0b642;
const LIGHTNING_LENGTH: u64 = 0xb5f9a98dc;
const LIGHTNING_SPEED: u64 = 0x50f26fef6;
const LIGHTNING_CHECK_LENGTH: u64 = 0xe8ed99520;
const RBKIND_EXPLOSION: u64 = 0x10eaa9bff4;

fn spark_life(key: u64) -> i32 {
    params::param_spark_i32(key).unwrap_or_else(|| { crate::diagnostic!(log(format!("FAIL param {:#x}", key))); 1 })
}
fn lightning_f32(key: u64) -> f32 {
    params::param_lightning_f32(key).unwrap_or_else(|| { crate::diagnostic!(log(format!("FAIL param {:#x}", key))); 0.0 })
}
unsafe fn owner(w: &mut L2CWeaponCommon) -> *mut BattleObjectModuleAccessor {
    let id = WorkModule::get_int(w.module_accessor, *WEAPON_INSTANCE_WORK_ID_INT_ACTIVATE_FOUNDER_ID) as u32;
    if app::sv_battle_object::is_active(id) { app::sv_battle_object::module_accessor(id) } else { std::ptr::null_mut() }
}
unsafe fn set_life(w: &mut L2CWeaponCommon, life: i32) {
    WorkModule::set_int(w.module_accessor, life, *WEAPON_INSTANCE_WORK_ID_INT_INIT_LIFE);
    WorkModule::set_int(w.module_accessor, life, *WEAPON_INSTANCE_WORK_ID_INT_LIFE);
}
unsafe fn remove(w: &mut L2CWeaponCommon) {
    notify_event_msc_cmd!(w, Hash40::new_raw(REMOVE));
}
unsafe extern "C" fn end(_: &mut L2CWeaponCommon) -> L2CValue { 0.into() }
unsafe extern "C" fn exec_life(w: &mut L2CWeaponCommon) -> L2CValue {
    WorkModule::dec_int(w.module_accessor, *WEAPON_INSTANCE_WORK_ID_INT_LIFE);
    0.into()
}

unsafe extern "C" fn spark_pre(w: &mut L2CWeaponCommon) -> L2CValue {
    StatusModule::init_settings(w.module_accessor, SituationKind(*SITUATION_KIND_AIR), *WEAPON_KINETIC_TYPE_NORMAL,
        *GROUND_CORRECT_KIND_AIR as u32, GroundCliffCheckKind(0), false, 0, 0, 0, 0);
    0.into()
}
unsafe extern "C" fn spark_main(w: &mut L2CWeaponCommon) -> L2CValue {
    let boma = w.module_accessor;
    let status = StatusModule::status_kind(boma);
    let (life, motion) = if status == *WEAPON_BRAVE_SPARK_STATUS_KIND_S1 { (SPARK_LIFE_S, "special_s1") }
        else if status == *WEAPON_BRAVE_SPARK_STATUS_KIND_S2 { (SPARK_LIFE_M, "special_s2") }
        else { (SPARK_LIFE_L, "special_s32") };
    set_life(w, spark_life(life));
    MotionModule::change_motion(boma, Hash40::new(motion), 0.0, 1.0, false, 0.0, false, false);
    let pos = *PostureModule::pos(boma);
    crate::diagnostic!(log(format!("SPARK {} life={} x={:.1} y={:.1}", motion, spark_life(life), pos.x, pos.y)));
    w.fastshift(L2CValue::Ptr(spark_loop as *const () as _))
}
/// 0x48450
unsafe extern "C" fn spark_loop(w: &mut L2CWeaponCommon) -> L2CValue {
    if WorkModule::get_int(w.module_accessor, *WEAPON_INSTANCE_WORK_ID_INT_LIFE) <= 0 {
        EffectModule::detach_all(w.module_accessor, 5);
        remove(w);
    }
    0.into()
}

unsafe extern "C" fn lightning_pre(w: &mut L2CWeaponCommon) -> L2CValue {
    StatusModule::init_settings(w.module_accessor, SituationKind(*SITUATION_KIND_AIR), *WEAPON_KINETIC_TYPE_NORMAL,
        *GROUND_CORRECT_KIND_NONE as u32, GroundCliffCheckKind(0), false, 0, 0, 0, 0);
    0.into()
}
/// T-0052 diagnostic. The bolt's own cloned work layout (pinned `lua_const`,
/// tier C): `FLOAT_HEAD`/`FLOAT_TAIL`/`FLOAT_DIR`/`FLOAT_MOVE_DIST` are the inputs
/// and outputs of the donor's extension machinery, which the owned copy of
/// `main+0x33cabd0` drives from `MapCorrection`. The 2026-10-02 card log shows
/// `MOVE_DIST` frozen at 0.0 and the bolt's position frozen at its spawn point
/// (`offset_y_lightning` = 85.0) for every frame of every bolt, so either those
/// work values are never written or the position is never integrated. Printing
/// all of them before the arrival branch makes that one run decidable; no value
/// here is used for behaviour.
unsafe fn bolt_work(boma: *mut BattleObjectModuleAccessor) -> String {
    let f = |id: i32| WorkModule::get_float(boma, id);
    format!("head={:.1} tail={:.1} dir={:.1} move_dist={:.1}",
        f(*WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLOAT_HEAD),
        f(*WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLOAT_TAIL),
        f(*WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLOAT_DIR),
        f(*WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLOAT_MOVE_DIST))
}
unsafe fn clear_transition(boma: *mut BattleObjectModuleAccessor) {
    for flag in [*WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLAG_MTRANS_SMPL_AIR,
                 *WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLAG_MTRANS_SMPL_GROUND,
                 *WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLAG_MTRANS_SMPL_MOTION_END] {
        WorkModule::off_flag(boma, flag);
    }
}
/// 0x45b80: life is fall distance over fall speed.
unsafe extern "C" fn lightning_main(w: &mut L2CWeaponCommon) -> L2CValue {
    let boma = w.module_accessor;
    GroundModule::set_collidable(boma, false);
    let life = (lightning_f32(LIGHTNING_LENGTH) * 10.0 / lightning_f32(LIGHTNING_SPEED) * -1.0) as i32;
    set_life(w, life);
    clear_transition(boma);
    MotionModule::change_motion(boma, Hash40::new("regular"), 0.0, 1.0, false, 0.0, false, false);
    crate::diagnostic!(log(format!("LIGHTNING regular life={} {}", life, bolt_work(boma))));
    w.fastshift(L2CValue::Ptr(lightning_loop as *const () as _))
}
unsafe extern "C" fn lightning_init(w: &mut L2CWeaponCommon) -> L2CValue {
    WorkModule::off_flag(w.module_accessor, *WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLAG_COLLISION_CHECK);
    0.into()
}
/// 0x457f0. Reaching the collision distance also raises the owned "bolt has
/// struck" signal the fighter's third attack waits for.
///
/// T-0052, settled 2026-10-02 from the card log (tier A): **this branch can never
/// fire on this clone and is no longer the arrival path.** The `BOLT` sample added
/// by the previous T-0052 run shows `move_dist=0.0` against `threshold=300.0` and
/// `owner_ok=true` on every sampled frame of all 30 bolts, with `MapCorrection`
/// running ~30 frames each. Cause (a) is therefore the real one - the engine does
/// not accumulate `FLOAT_MOVE_DIST` for this cloned article on Mythra - and cause
/// (b), the null owner lookup, is excluded. The owned arrival flag is now raised
/// from the donor's own lightning event in `receiver.rs`, which the same log shows
/// arriving once per bolt. This predicate is kept unchanged rather than re-pointed
/// at a smaller threshold: with the bolt not travelling, every threshold is a
/// guess, and a firing predicate would report an arrival that has not happened.
/// The position and the donor's head/tail work values are printed by `bolt_work`
/// so the travel defect is measured rather than assumed.
unsafe extern "C" fn lightning_exec(w: &mut L2CWeaponCommon) -> L2CValue {
    let boma = w.module_accessor;
    WorkModule::dec_int(boma, *WEAPON_INSTANCE_WORK_ID_INT_LIFE);
    let life = WorkModule::get_int(boma, *WEAPON_INSTANCE_WORK_ID_INT_LIFE);
    let distance = WorkModule::get_float(boma, *WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLOAT_MOVE_DIST);
    if life % 5 == 0 || life <= 2 {
        let pos = *PostureModule::pos(boma);
        crate::diagnostic!(log(format!("BOLT life={} {} threshold={:.1} owner_ok={} x={:.1} y={:.1}",
            life, bolt_work(boma), lightning_f32(LIGHTNING_CHECK_LENGTH) * 10.0,
            !owner(w).is_null(), pos.x, pos.y)));
    }
    if !WorkModule::is_flag(boma, *WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLAG_COLLISION_CHECK) {
        if lightning_f32(LIGHTNING_CHECK_LENGTH) * 10.0 <= distance {
            WorkModule::on_flag(boma, *WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLAG_COLLISION_CHECK);
            GroundModule::set_collidable(boma, true);
            GroundModule::set_correct(boma, GroundCorrectKind(*GROUND_CORRECT_KIND_AIR));
            let owner = owner(w);
            if let Some(s) = state::get(owner) {
                s.set(LIGHTNING_ARRIVED);
                crate::diagnostic!(log(format!("LIGHTNING arrived distance={:.1}", distance)));
            } else {
                crate::diagnostic!(log(format!("LIGHTNING arrived distance={:.1} but no owned state", distance)));
            }
        }
    }
    0.into()
}
/// 0x45600: face the bolt, then the owned copy of the native map collection.
unsafe extern "C" fn lightning_map(w: &mut L2CWeaponCommon) -> L2CValue {
    let boma = w.module_accessor;
    let y = if PostureModule::lr(boma) == -1.0 { 90.0 } else { -90.0 };
    PostureModule::set_rot(boma, &Vector3f { x: 0.0, y, z: 0.0 }, 0);
    let owner = owner(w);
    if !owner.is_null() { native::lightning_map(w.battle_object.cast(), owner); }
    0.into()
}
/// 0x46080: simple motion-transition bookkeeping, landing quake/rumble, removal.
unsafe extern "C" fn lightning_loop(w: &mut L2CWeaponCommon) -> L2CValue {
    let boma = w.module_accessor;
    let air = *WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLAG_MTRANS_SMPL_AIR;
    let ground = *WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLAG_MTRANS_SMPL_GROUND;
    let motion_end = *WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLAG_MTRANS_SMPL_MOTION_END;
    let situation = StatusModule::situation_kind(boma);
    if !(WorkModule::is_flag(boma, air) || WorkModule::is_flag(boma, ground) || WorkModule::is_flag(boma, motion_end)) {
        if situation == *SITUATION_KIND_GROUND {
            w.set_situation(SITUATION_KIND_GROUND.into());
            WorkModule::on_flag(boma, air);
        } else {
            w.set_situation(SITUATION_KIND_AIR.into());
            WorkModule::on_flag(boma, ground);
        }
    }
    if (WorkModule::is_flag(boma, air) && situation == *SITUATION_KIND_AIR)
        || (WorkModule::is_flag(boma, ground) && situation == *SITUATION_KIND_GROUND)
        || (WorkModule::is_flag(boma, motion_end) && MotionModule::is_end(boma)) {
        clear_transition(boma);
    }
    if situation == *SITUATION_KIND_GROUND && StatusModule::prev_situation_kind(boma) == *SITUATION_KIND_AIR
        && WorkModule::is_flag(boma, *WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLAG_IS_HEAD) {
        CameraModule::req_quake(boma, *CAMERA_QUAKE_KIND_L);
        let fighter = WorkModule::get_int(boma, *WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_INT_FIGHTER_OBJECT_ID) as u32;
        if fighter != *BATTLE_OBJECT_ID_INVALID as u32 && app::sv_battle_object::is_active(fighter) {
            ControlModule::set_rumble(app::sv_battle_object::module_accessor(fighter),
                Hash40::new_raw(RBKIND_EXPLOSION), 0, false, *BATTLE_OBJECT_ID_INVALID as u32);
        }
    }
    if WorkModule::get_int(boma, *WEAPON_INSTANCE_WORK_ID_INT_LIFE) <= 0
        || WorkModule::is_flag(boma, *WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLAG_SELF_REMOVE) {
        remove(w);
    }
    0.into()
}

unsafe fn spark_attacks(agent: &mut L2CAgentBase, quake: i32, main: (f32, u64, i32, i32, f32),
                        wide: (f32, u64, i32, i32, f32), pillar: f32) {
    QUAKE(agent, quake);
    ATTACK(agent, 0, 0, Hash40::new("top"), main.0, main.1, main.2, 0, main.3, 8.0, 0.0, main.4, 0.0, None, None, None, 0.4, 1.0, *ATTACK_SETOFF_KIND_OFF, *ATTACK_LR_CHECK_F, false, 0, 0.0, 0, false, false, false, true, true, *COLLISION_SITUATION_MASK_GA, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_elec"), *ATTACK_SOUND_LEVEL_L, *COLLISION_SOUND_ATTR_ELEC, *ATTACK_REGION_MAGIC);
    ATTACK(agent, 1, 0, Hash40::new("top"), wide.0, wide.1, wide.2, 0, wide.3, wide.4, 0.0, main.4, 0.0, None, None, None, 0.4, 1.0, *ATTACK_SETOFF_KIND_OFF, *ATTACK_LR_CHECK_POS, false, 0, 0.0, 0, false, false, false, true, false, *COLLISION_SITUATION_MASK_GA, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_elec"), *ATTACK_SOUND_LEVEL_L, *COLLISION_SOUND_ATTR_ELEC, *ATTACK_REGION_MAGIC);
    ATTACK(agent, 2, 0, Hash40::new("top"), pillar, 58, 40, 0, 100, 6.0, 0.0, 22.0, 0.0, Some(0.0), Some(75.0), Some(0.0), 0.4, 1.0, *ATTACK_SETOFF_KIND_OFF, *ATTACK_LR_CHECK_POS, false, 0, 0.0, 0, false, false, false, true, false, *COLLISION_SITUATION_MASK_GA, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_elec"), *ATTACK_SOUND_LEVEL_S, *COLLISION_SOUND_ATTR_ELEC, *ATTACK_REGION_MAGIC);
}
unsafe extern "C" fn spark_game_s1(agent: &mut L2CAgentBase) {
    if is_excute(agent) {
        spark_attacks(agent, *CAMERA_QUAKE_KIND_S, (9.0, 53, 80, 70, 10.0), (5.0, 53, 80, 70, 15.0), 2.5);
    }
}
unsafe extern "C" fn spark_game_s2(agent: &mut L2CAgentBase) {
    if is_excute(agent) {
        spark_attacks(agent, *CAMERA_QUAKE_KIND_M, (14.0, 58, 60, 80, 12.0), (10.0, 58, 60, 80, 17.0), 5.0);
        ControlModule::set_rumble(agent.module_accessor, Hash40::new("rbkind_attackl"), 0, true, *BATTLE_OBJECT_ID_INVALID as u32);
    }
}
unsafe extern "C" fn spark_game_s32(agent: &mut L2CAgentBase) {
    if is_excute(agent) {
        spark_attacks(agent, *CAMERA_QUAKE_KIND_L, (16.0, 44, 134, 24, 12.0), (12.0, 58, 70, 24, 18.0), 6.0);
        ControlModule::set_rumble(agent.module_accessor, Hash40::new("rbkind_explosionm"), 0, true, *BATTLE_OBJECT_ID_INVALID as u32);
    }
}
unsafe fn spark_effect(agent: &mut L2CAgentBase, name: &str, scale: f32) {
    if is_excute(agent) {
        EFFECT(agent, Hash40::new(name), Hash40::new("top"), 0, 0, 0, 0, 0, 0, scale, 0, 0, 0, 0, 0, 0, true);
    }
}
unsafe extern "C" fn spark_effect_s1(agent: &mut L2CAgentBase) { spark_effect(agent, "brave_lightning1_spark", 1.0) }
unsafe extern "C" fn spark_effect_s2(agent: &mut L2CAgentBase) { spark_effect(agent, "brave_lightning2_spark", 1.0) }
unsafe extern "C" fn spark_effect_s32(agent: &mut L2CAgentBase) { spark_effect(agent, "brave_lightning2_spark", 1.2) }
unsafe extern "C" fn spark_sound(agent: &mut L2CAgentBase) {
    smash::app::sv_animcmd::frame(agent.lua_state_agent, 2.0);
    if is_excute(agent) { PLAY_SE(agent, Hash40::new("se_brave_special_s02")); }
}

unsafe extern "C" fn lightning_game(agent: &mut L2CAgentBase) {
    if is_excute(agent) {
        ATTACK(agent, 0, 0, Hash40::new("top"), 12.0, 56, 40, 0, 100, 7.5, 0.0, 0.0, 0.0, Some(0.0), Some(0.0), Some(0.0), 0.5, 1.0, *ATTACK_SETOFF_KIND_OFF, *ATTACK_LR_CHECK_POS, false, 0, 0.0, 0, true, true, false, false, false, *COLLISION_SITUATION_MASK_GA, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_elec"), *ATTACK_SOUND_LEVEL_L, *COLLISION_SOUND_ATTR_ELEC, *ATTACK_REGION_MAGIC);
    }
    wait(agent.lua_state_agent, 2.0);
    if is_excute(agent) {
        ATTACK(agent, 0, 0, Hash40::new("top"), 10.0, 64, 40, 0, 100, 6.0, 0.0, 0.0, 0.0, Some(0.0), Some(14.0), Some(0.0), 0.1, 1.0, *ATTACK_SETOFF_KIND_OFF, *ATTACK_LR_CHECK_POS, false, 0, 0.0, 0, true, true, false, false, false, *COLLISION_SITUATION_MASK_GA, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_elec"), *ATTACK_SOUND_LEVEL_L, *COLLISION_SOUND_ATTR_ELEC, *ATTACK_REGION_MAGIC);
    }
}
unsafe extern "C" fn lightning_effect(agent: &mut L2CAgentBase) {
    if is_excute(agent) {
        EFFECT_FOLLOW(agent, Hash40::new("brave_lightning3_lightning"), Hash40::new("top"), 0, 0, 0, 0, 0, 0, 1, true);
    }
}

pub(super) fn install() {
    let mut spark = Agent::new("elight_pgwr_hero_spark");
    for status in [*WEAPON_BRAVE_SPARK_STATUS_KIND_S1, *WEAPON_BRAVE_SPARK_STATUS_KIND_S2,
                   *WEAPON_BRAVE_SPARK_STATUS_KIND_S32] {
        spark.status(Pre, status, spark_pre);
        spark.status(Main, status, spark_main);
        spark.status(End, status, end);
        spark.status(Exec, status, exec_life);
    }
    spark.game_acmd("game_specials1", spark_game_s1, Priority::Low);
    spark.game_acmd("game_specials2", spark_game_s2, Priority::Low);
    spark.game_acmd("game_specials32", spark_game_s32, Priority::Low);
    spark.effect_acmd("effect_specials1", spark_effect_s1, Priority::Low);
    spark.effect_acmd("effect_specials2", spark_effect_s2, Priority::Low);
    spark.effect_acmd("effect_specials32", spark_effect_s32, Priority::Low);
    for name in ["sound_specials1", "sound_specials2", "sound_specials32"] {
        spark.sound_acmd(name, spark_sound, Priority::Low);
    }
    spark.install();

    let status = *WEAPON_BRAVE_LIGHTNING_STATUS_KIND_REGULAR;
    let mut lightning = Agent::new("elight_pgwr_hero_lightning");
    lightning.status(Pre, status, lightning_pre);
    lightning.status(Main, status, lightning_main);
    lightning.status(End, status, end);
    lightning.status(Init, status, lightning_init);
    lightning.status(Exec, status, lightning_exec);
    lightning.status(MapCorrection, status, lightning_map);
    lightning.game_acmd("game_regular", lightning_game, Priority::Low);
    lightning.effect_acmd("effect_regular", lightning_effect, Priority::Low);
    lightning.install();
}
