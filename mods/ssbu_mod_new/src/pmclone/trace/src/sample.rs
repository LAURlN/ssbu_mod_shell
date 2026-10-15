//! Reads one trace row from a fighter or weapon. Only exported game functions
//! (lua_bind / app) are used, so nothing here depends on memory offsets.
//! Column meanings: see trace/README.md.
use core::sync::atomic::{AtomicUsize, Ordering};
use std::fmt::Write;

use smash::app::{self, lua_bind::*, BattleObjectModuleAccessor};
use smash::lib::lua_const::*;
use smash::lua2cpp::{L2CFighterCommon, L2CWeaponCommon};
use smashline::{Agent, Main};

use crate::names;
use crate::session::{self, Row};
use crate::work_ids::{self, W};

/// Attack ids checked per object. ACMD in the base game uses ids 0-7.
const ATTACK_IDS: i32 = 8;

pub fn install() {
    Agent::new("fighter").on_line(Main, fighter_line).install();
    Agent::new("weapon").on_line(Main, weapon_line).install();
}

unsafe extern "C" fn fighter_line(fighter: &mut L2CFighterCommon) {
    session::on_fighter(fighter.module_accessor);
}

unsafe extern "C" fn weapon_line(weapon: &mut L2CWeaponCommon) {
    session::on_weapon(weapon.module_accessor);
}

extern "C" {
    #[link_name = "\u{1}_ZN3app8lua_bind38FighterManager__get_fighter_entry_implEPNS_14FighterManagerENS_14FighterEntryIDE"]
    fn get_fighter_entry(manager: *mut u8, entry: i32) -> *mut u8;
    #[link_name = "\u{1}_ZN3app8lua_bind37FighterEntry__current_fighter_id_implEPNS_12FighterEntryE"]
    fn entry_current_fighter_id(entry: *mut u8) -> u32;
}

static FIGHTER_MANAGER: AtomicUsize = AtomicUsize::new(0);

/// The battle object id of the fighter that currently controls this entry
/// (for Pyra/Mythra: whichever of the two is out). None if it cannot be read.
pub unsafe fn current_fighter_id(entry: i32) -> Option<u32> {
    let mut holder = FIGHTER_MANAGER.load(Ordering::Relaxed);
    if holder == 0 {
        skyline::nn::ro::LookupSymbol(
            &mut holder,
            "_ZN3lib9SingletonIN3app14FighterManagerEE9instance_E\0".as_ptr(),
        );
        if holder == 0 {
            return None;
        }
        FIGHTER_MANAGER.store(holder, Ordering::Relaxed);
    }
    let manager = *(holder as *const *mut u8);
    if manager.is_null() {
        return None;
    }
    let entry_ptr = get_fighter_entry(manager, entry);
    if entry_ptr.is_null() {
        return None;
    }
    Some(entry_current_fighter_id(entry_ptr))
}

const FIGHTER_ENERGIES: [(&str, fn() -> i32); 8] = [
    ("control", || *FIGHTER_KINETIC_ENERGY_ID_CONTROL),
    ("damage", || *FIGHTER_KINETIC_ENERGY_ID_DAMAGE),
    ("env_wind", || *FIGHTER_KINETIC_ENERGY_ID_ENV_WIND),
    ("gravity", || *FIGHTER_KINETIC_ENERGY_ID_GRAVITY),
    ("ground_movement", || *FIGHTER_KINETIC_ENERGY_ID_GROUND_MOVEMENT),
    ("jostle", || *FIGHTER_KINETIC_ENERGY_ID_JOSTLE),
    ("motion", || *FIGHTER_KINETIC_ENERGY_ID_MOTION),
    ("stop", || *FIGHTER_KINETIC_ENERGY_ID_STOP),
];

/// Fields shared by fighters and weapons, from `kind` to `hitstop` inclusive,
/// plus the hitbox column. Hitbox details that do not fit the fixed hitbox tuple
/// are added to `work` as `hb<id>.<field>` keys.
unsafe fn common_fields(
    boma: *mut BattleObjectModuleAccessor,
    kind: i32,
    speed: &str,
    damage: f32,
    work: &mut Vec<(String, String)>,
) -> String {
    let pos = &*PostureModule::pos(boma);
    let mut f = String::with_capacity(256);
    let _ = write!(
        f,
        "{},{},{},{:#012x},{},{},{},{},{},{},{},{},",
        kind,
        StatusModule::status_kind(boma),
        StatusModule::situation_kind(boma),
        MotionModule::motion_kind(boma),
        MotionModule::frame(boma),
        MotionModule::rate(boma),
        pos.x,
        pos.y,
        PostureModule::lr(boma),
        speed,
        damage,
        // Spec asks for remaining hitlag frames. The binding for
        // StopModule::get_hit_stop_real_frame has an uncertain return type, so
        // v0.1 writes 1 while the object is in hitlag and 0 otherwise.
        StopModule::is_stop(boma) as i32,
    );
    let mut boxes = Vec::new();
    for id in 0..ATTACK_IDS {
        if !AttackModule::is_attack(boma, id, false) {
            continue;
        }
        let d = AttackModule::attack_data(boma, id, false);
        if d.is_null() {
            continue;
        }
        let d = &*d;
        boxes.push(format!(
            "{}/0/{}/{}/{}/{}/{}/{}/{}/{}/{}/{}/{}/{}",
            id, d.power, d.vector, d.r_eff, d.r_fix, d.r_add, d.size, d.x, d.y, d.z, d.x2, d.y2, d.z2
        ));
        let p = format!("hb{}.", id);
        work.push((p.clone() + "node", format!("{:#x}", d.node)));
        work.push((p.clone() + "attr", format!("{:#x}", d.attr)));
        work.push((p.clone() + "stop_frame", format!("{}", d.stop_frame)));
        work.push((p.clone() + "stop_delay", format!("{}", d.stop_delay)));
        work.push((p.clone() + "slip", format!("{}", d.slip)));
        work.push((p.clone() + "check_type", format!("{:#x}", d.check_type)));
        work.push((p.clone() + "target_situation", format!("{:#x}", d.target_situation)));
        work.push((p.clone() + "target_lr", format!("{:#x}", d.target_lr)));
        work.push((p.clone() + "target_part", format!("{:#x}", d.target_part)));
        work.push((p.clone() + "sound", format!("{}/{}", d.sound_level, d.sound_attr)));
    }
    f.push_str(&boxes.join(";"));
    f
}

fn finish_work(mut work: Vec<(String, String)>) -> String {
    work.sort();
    let mut out = String::with_capacity(work.len() * 24);
    for (i, (k, v)) in work.iter().enumerate() {
        if i > 0 {
            out.push(';');
        }
        out.push_str(k);
        out.push('=');
        out.push_str(v);
    }
    out
}

unsafe fn push_work(
    boma: *mut BattleObjectModuleAccessor,
    table: &[(&str, i32, W)],
    prefix: &str,
    work: &mut Vec<(String, String)>,
) {
    for &(name, id, kind) in table {
        let value = match kind {
            W::Int => WorkModule::get_int(boma, id).to_string(),
            W::Flag => (WorkModule::is_flag(boma, id) as i32).to_string(),
            W::Float => WorkModule::get_float(boma, id).to_string(),
        };
        // Zero values are omitted to keep rows small (most instance work is 0).
        // A missing key therefore means 0/false; a value change still shows as a
        // key that is present in one row and absent in the other.
        if value != "0" {
            work.push((format!("{}{}", prefix, name), value));
        }
    }
}

pub unsafe fn fighter_row(boma: *mut BattleObjectModuleAccessor, entry: i32, active: bool) -> Row {
    let kind = app::utility::get_kind(&mut *boma);
    let base = names::base_fighter_kind(kind);

    let mut speeds: Vec<String> = Vec::new();
    for (name, id) in FIGHTER_ENERGIES.iter() {
        let id = id();
        if KineticModule::is_enable_energy(boma, id) {
            let e = KineticModule::get_energy(boma, id) as *mut smash::app::KineticEnergy;
            if !e.is_null() {
                speeds.push(format!(
                    "{}={}:{}",
                    name,
                    KineticEnergy::get_speed_x(e),
                    KineticEnergy::get_speed_y(e)
                ));
            }
        }
    }
    speeds.push(sum_speed(boma));
    speeds.sort();

    let mut work = Vec::with_capacity(560);
    work.push(("active".to_string(), (active as i32).to_string()));
    push_work(boma, work_ids::COMMON, "", &mut work);
    match base {
        names::KIND_EFLAME => {
            push_work(boma, work_ids::ELEMENT, "element.", &mut work);
            push_work(boma, work_ids::EFLAME, "eflame.", &mut work);
        }
        names::KIND_ELIGHT => {
            push_work(boma, work_ids::ELEMENT, "element.", &mut work);
            push_work(boma, work_ids::ELIGHT, "elight.", &mut work);
        }
        _ => {}
    }

    let damage = DamageModule::damage(boma, 0);
    let mut fields = common_fields(boma, kind, &speeds.join(";"), damage, &mut work);
    fields.push(',');
    fields.push_str(&finish_work(work));
    Row {
        slot: entry,
        object: format!("fighter:{}", names::fighter_name(base)),
        order: (*boma).battle_object_id,
        article: false,
        fields,
    }
}

unsafe fn sum_speed(boma: *mut BattleObjectModuleAccessor) -> String {
    let attr = *KINETIC_ENERGY_RESERVE_ATTRIBUTE_MAIN;
    format!(
        "sum={}:{}",
        KineticModule::get_sum_speed_x(boma, attr),
        KineticModule::get_sum_speed_y(boma, attr)
    )
}

/// Owner fighter's entry for a weapon, following at most one weapon-owns-weapon link.
unsafe fn weapon_owner_entry(boma: *mut BattleObjectModuleAccessor) -> Option<i32> {
    let mut id = WorkModule::get_int(boma, *WEAPON_INSTANCE_WORK_ID_INT_LINK_OWNER) as u32;
    for _ in 0..2 {
        if id == 0x50000000 || !app::sv_battle_object::is_active(id) {
            return None;
        }
        let owner = app::sv_battle_object::module_accessor(id);
        if owner.is_null() {
            return None;
        }
        match id >> 28 {
            0 => {
                let entry = WorkModule::get_int(owner, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
                return if (0..8).contains(&entry) { Some(entry) } else { None };
            }
            1 => id = WorkModule::get_int(owner, *WEAPON_INSTANCE_WORK_ID_INT_LINK_OWNER) as u32,
            _ => return None,
        }
    }
    None
}

pub unsafe fn weapon_row(boma: *mut BattleObjectModuleAccessor) -> Option<Row> {
    let entry = weapon_owner_entry(boma)?;
    let kind = app::utility::get_kind(&mut *boma);
    let mut work = Vec::new();
    work.push((
        "LIFE".to_string(),
        WorkModule::get_int(boma, *WEAPON_INSTANCE_WORK_ID_INT_LIFE).to_string(),
    ));
    let mut fields = common_fields(boma, kind, &sum_speed(boma), 0.0, &mut work);
    fields.push(',');
    fields.push_str(&finish_work(work));
    Some(Row {
        slot: entry,
        object: format!("article:{}", names::weapon_name(kind)),
        order: (*boma).battle_object_id,
        article: true,
        fields,
    })
}
