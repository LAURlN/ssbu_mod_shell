//! Hero neutral-B owns its state, motions, article and resources on Mythra c06/c07.
//! Charge is stored per entry; Hero fighter work ids are never used on Mythra.
mod acmd;
mod donor_params;
mod native;
mod fighter;
mod projectile;
use smash::{app::{self, lua_bind::*, BattleObjectModuleAccessor}, lib::lua_const::*,
            lua2cpp::L2CAgentBase, phx::Hash40};
use std::sync::atomic::{AtomicI32, AtomicU32, Ordering};

pub(super) const START: i32 = 0x1f5;
pub(super) const HOLD: i32 = 0x1f6;
pub(super) const CANCEL: i32 = 0x1f7;
pub(super) const JUMP_CANCEL: i32 = 0x1f8;
pub(super) const SHOOT: i32 = 0x1f9;
pub(super) const START_M: u32 = 1;
pub(super) const CANCEL_L: u32 = 2;
pub(super) const ENABLE_CONTROL_ENERGY: u32 = 4;
pub(super) const HOP: u32 = 8;
pub(super) const REVERT_FALL_SPEED: u32 = 16;
pub(super) const TO_SHOOT: u32 = 32;
pub(super) const NORMAL_FALL_SPEED: u32 = 64;
pub(super) const CONTROL_ENERGY: u32 = 128;
pub(super) const HOPPED: u32 = 256;

struct State { charge: AtomicI32, flags: AtomicU32, next: AtomicI32, clip_probe: AtomicU32 }
impl State {
    const fn new() -> Self { Self { charge: AtomicI32::new(0), flags: AtomicU32::new(0),
                                   next: AtomicI32::new(-1), clip_probe: AtomicU32::new(0) } }
}
static STATE: [State; 8] = [State::new(), State::new(), State::new(), State::new(),
                           State::new(), State::new(), State::new(), State::new()];
static ARTICLE: AtomicI32 = AtomicI32::new(-1);

pub(super) fn address_ok(address: usize, alignment: usize) -> bool {
    address >= 0x100000000 && address < 0x8000000000 && address % alignment == 0
}

pub(super) unsafe fn target(boma: *mut BattleObjectModuleAccessor) -> bool {
    address_ok(boma as usize, 8)
        && app::utility::get_category(&mut *boma) == *BATTLE_OBJECT_CATEGORY_FIGHTER
        && app::utility::get_kind(&mut *boma) == *FIGHTER_KIND_ELIGHT
        && crate::TARGET_COSTUMES.contains(&(WorkModule::get_int(
            boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR) as usize))
}

pub(super) unsafe fn entry(boma: *mut BattleObjectModuleAccessor) -> Option<usize> {
    if !address_ok(boma as usize, 8) { return None; }
    let id = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
    if (0..8).contains(&id) { Some(id as usize) } else { None }
}

pub(super) unsafe fn charge(boma: *mut BattleObjectModuleAccessor) -> i32 {
    entry(boma).map(|id| STATE[id].charge.load(Ordering::Relaxed)).unwrap_or(0)
}

pub(super) unsafe fn flag(boma: *mut BattleObjectModuleAccessor, flag: u32) -> bool {
    entry(boma).map(|id| STATE[id].flags.load(Ordering::Relaxed) & flag != 0).unwrap_or(false)
}

pub(super) unsafe fn set_flag(boma: *mut BattleObjectModuleAccessor, flag: u32) {
    if let Some(id) = entry(boma) { STATE[id].flags.fetch_or(flag, Ordering::Relaxed); }
}

pub(super) unsafe fn generate(boma: *mut BattleObjectModuleAccessor) {
    if !native::ready() || !target(boma) { return; }
    // T-0057: out of MP the donor clears SUCCESS_SP and its article setup is
    // skipped, so no projectile exists. The move's motion still plays, which is
    // the donor's out-of-MP shape rather than a silent refusal.
    if !crate::mythra::hero_mana::cast_ok(boma) {
        crate::diagnostic!(crate::article::log(format!("[PGWR-HERO-N] SPAWN refused entry={} charge={} (no mana)",
                                   entry(boma).unwrap_or(99), charge(boma))));
        return;
    }
    let article = ARTICLE.load(Ordering::Relaxed);
    if article < 0 { return; }
    crate::diagnostic!(crate::article::log(format!("[PGWR-HERO-N] SPAWN entry={} charge={} frame={:.1}",
                               entry(boma).unwrap_or(99), charge(boma), MotionModule::frame(boma))));
    ArticleModule::generate_article(boma, article, false, -1);
    crate::diagnostic!(crate::article::log(format!("[PGWR-HERO-N] SPAWN result count={}",
                               ArticleModule::get_active_num(boma, article))));
}

pub(super) unsafe fn voice_sequence(agent: &mut L2CAgentBase, level: i32) -> Hash40 {
    agent.clear_lua_stack();
    app::sv_animcmd::GET_VOICE_REGION(agent.lua_state_agent);
    let region = agent.pop_lua_stack(1).get_i32();
    let english = [*VOICE_US_EN, *VOICE_US_FR, *VOICE_EU_EN, *VOICE_EU_FR,
                   *VOICE_EU_IT, *VOICE_US_SP, *VOICE_EU_SP, *VOICE_EU_NL, *VOICE_EU_RU]
                   .contains(&region);
    Hash40::new(&format!("seq_brave_rnd_special_n{}_{}", level, if english { "en" } else { "jp" }))
}

pub(super) unsafe fn takeout_se(agent: &mut L2CAgentBase, sound: Hash40) {
    agent.clear_lua_stack(); smash_script::lua_args!(agent, sound);
    app::sv_animcmd::SET_TAKEOUT_SE(agent.lua_state_agent); agent.clear_lua_stack();
}
pub(super) unsafe fn effect_work_int(agent: &mut L2CAgentBase, work: i32) {
    agent.clear_lua_stack(); smash_script::lua_args!(agent, work);
    app::sv_animcmd::LAST_EFFECT_SET_WORK_INT(agent.lua_state_agent); agent.clear_lua_stack();
}

unsafe fn target_weapon(boma: *mut BattleObjectModuleAccessor) -> bool {
    if !address_ok(boma as usize, 8) || app::utility::get_category(&mut *boma) != *BATTLE_OBJECT_CATEGORY_WEAPON
        || app::utility::get_kind(&mut *boma) != *WEAPON_KIND_BRAVE_FIREBALL { return false; }
    let founder = WorkModule::get_int(boma, *WEAPON_INSTANCE_WORK_ID_INT_ACTIVATE_FOUNDER_ID) as u32;
    app::sv_battle_object::is_active(founder) && target(app::sv_battle_object::module_accessor(founder))
}
pub unsafe fn handle_param_int(boma: *mut BattleObjectModuleAccessor, parent: u64, child: u64) -> Option<i32> {
    if parent == smash::hash40("param_fireball") && target_weapon(boma) {
        return donor_params::param_fireball_i32(child);
    }
    if parent == smash::hash40("pgwr_hero_n") && target(boma) { return donor_params::param_special_n_i32(child); }
    None
}
pub unsafe fn handle_param_float(boma: *mut BattleObjectModuleAccessor, parent: u64, child: u64) -> Option<f32> {
    if parent == smash::hash40("param_fireball") && target_weapon(boma) {
        return donor_params::param_fireball_f32(child);
    }
    if target(boma) {
        if parent == smash::hash40("pgwr_hero_n") { return donor_params::param_special_n_f32(child); }
        if (START..=SHOOT).contains(&StatusModule::status_kind(boma)) {
            if child == 0 { return donor_params::common_f32(parent); }
            if parent == 0 || parent == smash::hash40("common") { return donor_params::common_f32(child); }
        }
    }
    None
}
pub fn install() {
    unsafe {
        if !native::install() { return; }
        let index = smashline::clone_weapon("brave", *WEAPON_KIND_BRAVE_FIREBALL,
                                           "elight", "pgwr_hero_fireball", false);
        ARTICLE.store(*FIGHTER_ELIGHT_ARTICLE_TERM + index, Ordering::Relaxed);
    }
    acmd::install(); projectile::install(); fighter::install();
    crate::diagnostic!(crate::article::log(format!("[PGWR-HERO-N] REGISTERED c06/c07 statuses={:#x}-{:#x} article={} mana=on (pair meter, T-0057)",
                               START, SHOOT, ARTICLE.load(Ordering::Relaxed))));
}
