//! Task-owned vanilla cargo port specification: refs/donkey_cargo/ownership_contract.json.
//! Generated callback instructions have owned relocations, not donor calls.
//! Private test allocation only. Shared integration changes are unapplied patches.
use smash::{app::{self,lua_bind::*,sv_battle_object,BattleObjectModuleAccessor},
    lib::{L2CValue,lua_const::*},lua2cpp::*,phx::{Hash40,simd::Vector3}};
use smashline::*;
use std::cell::Cell;
mod data;
mod acmd;
core::arch::global_asm!(include_str!("callbacks.S"));
core::arch::global_asm!(include_str!("lifetime.S"));
include!("registration.rs");

#[derive(Clone,Copy)]
struct Ready { object:u32, value:bool }
thread_local! { static READY: Cell<[Ready;8]> = Cell::new([Ready{object:u32::MAX,value:false};8]); }
#[derive(Clone,Copy)]
struct Sample {object:u32,status:i32,motion:u64,bucket:i32,active:bool}
thread_local! {static SAMPLES:Cell<[Sample;8]>=Cell::new([Sample{object:u32::MAX,status:-1,motion:0,bucket:-1,active:false};8]);}

fn log(message:String) {
    use std::io::Write;
    crate::diagnostic!(println!("[pgwr:dk_cargo] {}",message));
    if let Ok(mut file)=std::fs::OpenOptions::new().create(true).append(true)
        .open("sd:/ultimate/pgwr_dk_cargo_log.txt") {
        let _=writeln!(file,"[pgwr:dk_cargo] {}",message);
    }
}

unsafe fn ready_key(bma:*mut BattleObjectModuleAccessor)->Option<(usize,u32)> {
    if bma.is_null(){return None;}
    let entry=WorkModule::get_int(bma,*FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
    if !(0..8).contains(&entry){return None;}
    Some((entry as usize,(*bma).battle_object_id))
}
unsafe fn set_ready(bma:*mut BattleObjectModuleAccessor,value:bool) {
    if let Some((index,object))=ready_key(bma) {
        READY.with(|state| {let mut rows=state.get();rows[index]=Ready{object,value};state.set(rows);});
    }
}
unsafe fn get_ready(bma:*mut BattleObjectModuleAccessor)->bool {
    if let Some((index,object))=ready_key(bma) {
        return READY.with(|state| {let row=state.get()[index];row.object==object&&row.value});
    }
    false
}

pub unsafe fn owns_attacker(bma:*mut BattleObjectModuleAccessor)->bool {
    crate::params::is_target_fighter(bma)
        && (data::BASE..data::BASE+15).contains(&StatusModule::status_kind(bma))
}
unsafe fn owns_movement(bma:*mut BattleObjectModuleAccessor)->bool {
    owns_attacker(bma) && (data::BASE..data::BASE+10).contains(&StatusModule::status_kind(bma))
}
pub unsafe fn owns_victim(bma:*mut BattleObjectModuleAccessor)->bool {
    if bma.is_null() || !LinkModule::is_link(bma,*LINK_NO_CAPTURE) {return false;}
    let parent=LinkModule::get_parent_object_id(bma,*LINK_NO_CAPTURE) as u32;
    if parent==*BATTLE_OBJECT_ID_INVALID as u32 || !sv_battle_object::is_active(parent){return false;}
    owns_attacker(sv_battle_object::module_accessor(parent))
}
pub unsafe fn owns_throw_kind(fighter:&mut L2CFighterCommon,kind:i32)->bool {
    // Compose with the existing exported generic throw classifier hook. This
    // does not modify the native raw-offset hook set or Gaogaen ownership.
    (data::BASE+11..data::BASE+15).contains(&kind) && owns_attacker(fighter.module_accessor)
        || kind==data::BASE+17 && owns_victim(fighter.module_accessor)
}

fn cleanup_state_match(left:i32,right:i32,stock_carry:i32,stock_thrown:i32)->bool {
    left==right || (left==stock_carry && right==data::BASE+16)
        || (left==stock_thrown && right==data::BASE+17)
}
#[no_mangle]
unsafe extern "C" fn pgwr_dkc_cleanup_status_eq(left:&L2CValue,right:&L2CValue)->bool {
    // Only owned Carry End and shared START/CARRY Exit call this adapter.
    // Native event receiver queues stock c7 before Pre redirects to owned 411.
    // Keep the existing capture across that transition; unrelated exits retain
    // their donor cleanup. These are semantic aliases, not equal numeric IDs.
    cleanup_state_match(left.get_i32(),right.get_i32(),
        *FIGHTER_STATUS_KIND_SHOULDERED_DONKEY,*FIGHTER_STATUS_KIND_SHOULDERED_DONKEY_THROWN)
}

unsafe extern "C" fn on_start(fighter:&mut L2CFighterCommon) {
    // Framework callbacks execute under a registry read lock. Only write the
    // already-created Lua table here: no game API, logging, or registry calls.
    fighter.global_table[0x45].assign(&L2CValue::I32(data::BASE));
}
unsafe extern "C" fn observe(fighter:&mut L2CFighterCommon) {
    let bma=fighter.module_accessor;
    let (index,object)=match ready_key(bma){Some(key)=>key,None=>return};
    let status=StatusModule::status_kind(bma);
    let active=(data::BASE..data::BASE+18).contains(&status);
    let previous=SAMPLES.with(|state|state.get()[index]);
    if !active {
        if previous.object==object && previous.active {
            crate::diagnostic!(log(format!("RELEASE object={} from={:#x} to={:#x} capture_link={} motion={:#x} frame={:.1}",
                object,previous.status,status,LinkModule::is_link(bma,*LINK_NO_CAPTURE),MotionModule::motion_kind(bma),MotionModule::frame(bma))));
            SAMPLES.with(|state|{let mut rows=state.get();rows[index].active=false;state.set(rows);});
        }
        return;
    }
    let motion=MotionModule::motion_kind(bma);let frame=MotionModule::frame(bma);
    // Initial, advancing and periodic samples, at most once per 30 motion
    // frames after the first three. No locks/references cross game calls.
    let bucket=if frame<1.0 {0} else if frame<16.0 {1} else {2+(frame as i32/30)};
    if previous.object==object&&previous.active&&previous.status==status&&previous.motion==motion&&previous.bucket==bucket {return;}
    SAMPLES.with(|state|{let mut rows=state.get();rows[index]=Sample{object,status,motion,bucket,active};state.set(rows);});
    crate::diagnostic!(log(format!("STATE object={} kind={} status={:#x} motion={:#x} frame={:.1} end={:.1} situation={} capture_link={}",
        object,app::utility::get_kind(&mut *bma),status,motion,frame,MotionModule::end_frame(bma),StatusModule::situation_kind(bma),LinkModule::is_link(bma,*LINK_NO_CAPTURE))));
    if status<data::BASE+15 && LinkModule::is_linked(bma,*LINK_NO_CAPTURE) {
        let victim=LinkModule::get_node_object_id(bma,*LINK_NO_CAPTURE) as u32;
        if victim!=*BATTLE_OBJECT_ID_INVALID as u32 && sv_battle_object::is_active(victim) {
            let vb=sv_battle_object::module_accessor(victim);
            if !vb.is_null() {crate::diagnostic!(log(format!("VICTIM object={} status={:#x} motion={:#x} frame={:.1} end={:.1} clatter={:.1}",
                victim,StatusModule::status_kind(vb),MotionModule::motion_kind(vb),MotionModule::frame(vb),MotionModule::end_frame(vb),ControlModule::get_clatter_time(vb,0))));}
        }
    }
}
unsafe fn bridge(fighter:&mut L2CFighterCommon,stock:i32,owned:i32)->L2CValue {
    if owns_victim(fighter.module_accessor) {
        StatusModule::set_status_kind_interrupt(fighter.module_accessor,owned);
        crate::diagnostic!(log(format!("VICTIM_ROUTE object={} stock={:#x} owned={:#x}",
            (*fighter.module_accessor).battle_object_id,stock,owned)));
        return 1.into();
    }
    original_status(Pre,fighter,stock)(fighter)
}
unsafe extern "C" fn bridge_start(f:&mut L2CFighterCommon)->L2CValue {
    bridge(f,*FIGHTER_STATUS_KIND_SHOULDERED_DONKEY_START,data::BASE+15)
}
unsafe extern "C" fn bridge_carry(f:&mut L2CFighterCommon)->L2CValue {
    bridge(f,*FIGHTER_STATUS_KIND_SHOULDERED_DONKEY,data::BASE+16)
}
unsafe extern "C" fn bridge_thrown(f:&mut L2CFighterCommon)->L2CValue {
    bridge(f,*FIGHTER_STATUS_KIND_SHOULDERED_DONKEY_THROWN,data::BASE+17)
}

/// Called only by the approved +0x170 extension, after its existing range guard.
pub unsafe fn on_event(bma:*mut BattleObjectModuleAccessor,kind:u64)->bool {
    if !owns_movement(bma){return false;}
    if kind==0xb319a8b44 {
        CatchModule::set_send_cut_event(bma,false);
    } else if kind!=0x21ba53a92c {return false;}
    crate::diagnostic!(log(format!("ESCAPE event={:#x} object={} status={:#x}",kind,(*bma).battle_object_id,StatusModule::status_kind(bma))));
    StatusModule::change_status_request_from_script(bma,*FIGHTER_STATUS_KIND_CATCH_CUT,false);
    true
}
/// Called only by the approved +0x210 extension; keep existing refresh handlers.
pub unsafe fn on_reset(bma:*mut BattleObjectModuleAccessor) {
    if owns_movement(bma) {
        crate::diagnostic!(log(format!("INTERRUPT object={} status={:#x} -> END",(*bma).battle_object_id,StatusModule::status_kind(bma))));
        StatusModule::change_status_request_from_script(bma,data::BASE+10,false);
    }
}

#[no_mangle]
unsafe extern "C" fn pgwr_dkc_reset_storage(fighter:&mut L2CFighterCommon) {
    set_ready(fighter.module_accessor,false);
    crate::diagnostic!(log(format!("PICKUP object={} status={:#x}",(*fighter.module_accessor).battle_object_id,StatusModule::status_kind(fighter.module_accessor))));
}
#[no_mangle]
unsafe extern "C" fn pgwr_dkc_exit_storage(fighter:&mut L2CFighterCommon) {
    let next=fighter.global_table[0xb].get_i32();
    if !(data::BASE..data::BASE+15).contains(&next) {
        set_ready(fighter.module_accessor,false);
        crate::diagnostic!(log(format!("CLEANUP object={} next={:#x} catch={}",(*fighter.module_accessor).battle_object_id,next,
            CatchModule::is_catch(fighter.module_accessor))));
    }
}
#[no_mangle]
pub unsafe extern "C" fn pgwr_dkc_is_flag(bma:*mut BattleObjectModuleAccessor,id:i32)->bool {
    if id==data::READY_FLAG {get_ready(bma)} else {WorkModule::is_flag(bma,id)}
}
#[no_mangle]
pub unsafe extern "C" fn pgwr_dkc_on_flag(bma:*mut BattleObjectModuleAccessor,id:i32) {
    if id==data::READY_FLAG {set_ready(bma,true)} else {WorkModule::on_flag(bma,id)}
}
#[no_mangle]
pub unsafe extern "C" fn pgwr_dkc_off_flag(bma:*mut BattleObjectModuleAccessor,id:i32) {
    if id==data::READY_FLAG {set_ready(bma,false)} else {WorkModule::off_flag(bma,id)}
}
#[no_mangle]
unsafe extern "C" fn pgwr_dkc_lift(bma:*mut BattleObjectModuleAccessor,enabled:bool) {
    // Only the common flag is needed by the shared kinetics. The donor native
    // constructor's modifier vector is represented in our walk parameter reads.
    if enabled {WorkModule::on_flag(bma,*FIGHTER_INSTANCE_WORK_ID_FLAG_LIGHT_WEIGHT)}
    else {WorkModule::off_flag(bma,*FIGHTER_INSTANCE_WORK_ID_FLAG_LIGHT_WEIGHT)}
}
extern "C" {
    #[link_name="_ZN3lib8L2CValueC1EN3phx6Hash40E"]
    fn hash_value_ctor(value:*mut u8,hash:Hash40);
    #[link_name="_ZN3lib9SingletonIN3app19FighterCutInManagerEE9instance_E"]
    static CUTIN:*mut app::FighterCutInManager;
}
#[no_mangle]
unsafe extern "C" fn pgwr_dkc_hash_value(value:*mut u8,hash:u64) {
    hash_value_ctor(value,Hash40::new_raw(data::own_hash(hash)));
}
#[no_mangle]
unsafe extern "C" fn pgwr_dkc_param_int(bma:*mut BattleObjectModuleAccessor,group:u64,key:u64)->i32 {
    if group==smash::hash40("param_private")&&key==0x13a4988083 {return 0;}
    if group==smash::hash40("common") {
        if let Some(value)=data::common_param(key){return value as i32;}
    }
    WorkModule::get_param_int(bma,group,key)
}
#[no_mangle]
unsafe extern "C" fn pgwr_dkc_param_float(bma:*mut BattleObjectModuleAccessor,group:u64,key:u64)->f32 {
    if group==smash::hash40("common") {
        if let Some(value)=data::common_param(key){return value;}
    }
    let value=WorkModule::get_param_float(bma,group,key);
    if key==0 && (group==smash::hash40("walk_speed_max") || group==smash::hash40("walk_accel_mul")
        || group==smash::hash40("walk_accel_add")) && owns_attacker(bma) {
        return value*1.1;
    }
    value
}
#[no_mangle]
unsafe extern "C" fn pgwr_dkc_thrown_offset(_accessor:*mut app::FighterParamAccessor2,kind:i32,direction:i32)->Vector3 {
    if let Some(row)=data::offset(kind,direction){return Vector3::new(row[0],row[1],row[2]);}
    crate::diagnostic!(log(format!("FAIL unsupported victim offset kind={} direction={}",kind,direction)));
    Vector3::new(0.0,0.0,0.0)
}
unsafe fn cutin()->*mut app::FighterCutInManager {
    let address=&CUTIN as *const _ as usize;
    assert!(super::monkey_flip_capture::mapped(address,8,false),"cargo cut-in singleton range");
    let value=CUTIN;
    assert!(super::monkey_flip_capture::mapped(value as usize,8,false),"cargo cut-in object range");
    value
}

pub fn install() {
    unsafe {
        let mut attacker=Agent::new("eflame");attacker.set_costume(crate::TARGET_COSTUMES.to_vec());
        attacker.on_start(on_start);register_attacker(&mut attacker);acmd::register_attacker(&mut attacker);attacker.install();
        // The pinned framework checks the actual fighter hash's costume set
        // for wildcard status scripts. Register both groups so eflame/elight
        // custom slots and all other costumes receive victim routing coverage.
        let mut victims=Agent::new("fighter");victims.on_line(Main,observe);register_victim(&mut victims);victims.install();
        let mut filtered=Agent::new("fighter");filtered.set_costume(crate::TARGET_COSTUMES.to_vec());
        register_victim(&mut filtered);filtered.install();
        // ACMD installation in the pinned framework uses the concrete fighter
        // hash only. Wildcard status support does not imply wildcard ACMD.
        for &name in data::VICTIM_AGENTS {
            let mut scripts=Agent::new(name);acmd::register_victim(&mut scripts);scripts.install();
            if name=="eflame" || name=="elight" {
                let mut gated=Agent::new(name);gated.set_costume(crate::TARGET_COSTUMES.to_vec());
                acmd::register_victim(&mut gated);gated.install();
            }
        }
    }
    crate::diagnostic!(log(format!("REGISTERED task=dk_cargo-0.1.1-test private_ids={:#x}..{:#x} costumes={:?} production=unallocated",data::BASE,data::BASE+17,crate::TARGET_COSTUMES)));
}
