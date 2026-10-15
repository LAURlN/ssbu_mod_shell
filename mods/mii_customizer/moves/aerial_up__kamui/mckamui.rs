//! Corrin's Omega Yato for the Mii Gunner (MV-aerial_up__kamui): the `mckamuisword` article.
//!
//! Same construction as the Cloud units' `mccloud.rs` (research/moves/aerial_forward__cloud.md, section 3), for
//! Corrin's single right-hand blade:
//! - Article: `smashline::clone_weapon("gamewatch", WEAPON_KIND_GAMEWATCH_NORMAL_WEAPON, "miigunner", "mckamuisword")`,
//!   no donor code. Its files are `fighter/miigunner/model/mckamuisword/c00/*` (Corrin's three Omega Yato meshes on
//!   one bone `Have`) and `fighter/miigunner/motion/mckamuisword/c00/*` (one clip, kind `mc_kamui_sword`, Visibility
//!   `mckamui_sword` True).
//! - Registered only when some mod folder on the card ships the model file. A registered article without its files
//!   crashes every Gunner at match start, so without them the unit keeps the vanilla move.
//! - Hand: the engine's own model constraint, `have` to the Gunner's `haver` (the same calls a vanilla weapon makes on
//!   itself; measured in lua2cpp_pit.nro 0x256b0..0x257ec by the Cloud units).
//! - Removal: when the Gunner leaves the owned motions (`mc_kamui_attack_air_hi`, `mc_kamui_landing_air_hi`), the
//!   sword is removed. Corrin's own END (`status_end_AttackAir` path) removes his article the same way.
//!
//! Tier D for everything on screen. The log lines `MV|kamui_sword|...` tell the cases apart.

use core::sync::atomic::{AtomicI32, AtomicU32, Ordering};
use smash::{
    app::{lua_bind::*, *},
    lib::lua_const::*,
    lua2cpp::*,
    phx::*,
};

use crate::{emit_wait, head, LineBuf};

pub const ARTICLE_NAME: &str = "mckamuisword";
/// The article's own motion kind (its clip draws the blade through the `mckamui_sword` Visibility track).
pub const ARTICLE_MOTION: &str = "mc_kamui_sword";
/// Owner motions that keep the sword out.
pub const OWNER_MOTIONS: [&str; 2] = ["mc_kamui_attack_air_hi", "mc_kamui_landing_air_hi"];
const SWORD_MODEL_FILE: &str = "fighter/miigunner/model/mckamuisword/c00/model.numshb";

/// Gunner-local article id of the sword; -1 while it is not registered.
static SWORD: AtomicI32 = AtomicI32::new(-1);
static LOG_COUNT: AtomicU32 = AtomicU32::new(0);
/// The sword is out, per entry id (the Gunner's `FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID`, 0..8).
static mut SWORD_OUT: [bool; 8] = [false; 8];

unsafe fn entry_of(boma: *mut BattleObjectModuleAccessor) -> Option<usize> {
    let entry = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
    if (0..8).contains(&entry) {
        Some(entry as usize)
    } else {
        None
    }
}

unsafe fn sword_out(boma: *mut BattleObjectModuleAccessor) -> bool {
    entry_of(boma).map(|e| (*core::ptr::addr_of!(SWORD_OUT))[e]).unwrap_or(false)
}

unsafe fn set_sword_out(boma: *mut BattleObjectModuleAccessor, out: bool) {
    if let Some(e) = entry_of(boma) {
        (*core::ptr::addr_of_mut!(SWORD_OUT))[e] = out;
    }
}

/// True when some mod folder on the card ships the sword model.
fn sword_files_present() -> bool {
    let Ok(dir) = std::fs::read_dir("sd:/ultimate/mods") else {
        return false;
    };
    for entry in dir.flatten() {
        if entry.path().join(SWORD_MODEL_FILE).exists() {
            return true;
        }
    }
    false
}

/// Registers the article. Must run before any fighter is built (called from `moves::install`).
pub fn install() {
    let present = sword_files_present();
    if present {
        let index = smashline::clone_weapon(
            "gamewatch",
            *WEAPON_KIND_GAMEWATCH_NORMAL_WEAPON,
            "miigunner",
            ARTICLE_NAME,
            false,
        );
        SWORD.store(*FIGHTER_MIIGUNNER_ARTICLE_TERM + index, Ordering::Release);
    }
    let mut out: LineBuf<192> = LineBuf::new();
    head(&mut out, "MV");
    out.s("|kamui_sword|files=").s(if present { "found" } else { "missing" });
    out.s("|article=");
    let id = article_id();
    if id >= 0 {
        out.dec(id as u64);
    } else {
        out.s("none|action=kamui_moves_stay_vanilla");
    }
    out.end_line();
    emit_wait(out.as_bytes());
}

pub fn article_id() -> i32 {
    SWORD.load(Ordering::Acquire)
}

/// The sword article is registered and every owner motion of `kinds` is in the loaded motion list.
pub unsafe fn ready(boma: *mut BattleObjectModuleAccessor, kinds: &[&str]) -> bool {
    article_id() >= 0 && kinds.iter().all(|k| MotionModule::is_anim_resource(boma, Hash40::new(k)))
}

unsafe fn log_sword(boma: *mut BattleObjectModuleAccessor, what: &str, exist: bool, joint: u64, flag: u64) {
    let count = LOG_COUNT.fetch_add(1, Ordering::Relaxed);
    if count >= 12 {
        return;
    }
    let mut out: LineBuf<192> = LineBuf::new();
    head(&mut out, "MV");
    out.s("|kamui_sword|").s(what);
    out.s("|entry=").dec(WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID) as u64);
    out.s("|status=").dec(StatusModule::status_kind(boma) as u64);
    out.s("|exist=").dec(exist as u64);
    out.s("|target_joint=").hex(joint);
    out.s("|flag=").hex(flag);
    out.end_line();
    emit_wait(out.as_bytes());
}

unsafe fn article_boma(boma: *mut BattleObjectModuleAccessor) -> *mut BattleObjectModuleAccessor {
    let id = article_id();
    if id < 0 || !ArticleModule::is_exist(boma, id) {
        return core::ptr::null_mut();
    }
    let article = ArticleModule::get_article(boma, id);
    if article.is_null() {
        return core::ptr::null_mut();
    }
    let object_id = smash::app::lua_bind::Article::get_battle_object_id(article) as u32;
    sv_battle_object::module_accessor(object_id)
}

/// Ties the article's `have` joint to the Gunner's right hand (`haver`) and starts the owned article clip.
pub unsafe fn attach_hand(boma: *mut BattleObjectModuleAccessor) {
    let id = article_id();
    let sword = article_boma(boma);
    if sword.is_null() {
        return;
    }
    ArticleModule::change_motion(boma, id, Hash40::new(ARTICLE_MOTION), false, -1.0);
    let owner = (*boma).battle_object_id;
    LinkModule::remove_model_constraint(sword, true);
    if LinkModule::is_link(sword, *LINK_NO_CONSTRAINT) {
        LinkModule::unlink(sword, *LINK_NO_CONSTRAINT);
    }
    LinkModule::link(sword, *LINK_NO_CONSTRAINT, owner);
    LinkModule::set_model_constraint_pos_ort(
        sword,
        *LINK_NO_CONSTRAINT,
        Hash40::new("have"),
        Hash40::new("haver"),
        (*CONSTRAINT_FLAG_POSITION | *CONSTRAINT_FLAG_ORIENTATION) as u32,
        true,
    );
    LinkModule::set_attribute(
        sword,
        *LINK_NO_CONSTRAINT,
        LinkAttribute { _address: *LINK_ATTRIBUTE_REFERENCE_PARENT_SCALE as u8 },
        true,
    );
    log_sword(
        boma,
        "hand=r",
        true,
        LinkModule::get_model_constraint_target_joint(sword),
        LinkModule::get_model_constraint_flag(sword),
    );
}

/// Puts the Omega Yato in the hand (spawns the article when it is not out).
pub unsafe fn show(boma: *mut BattleObjectModuleAccessor) {
    let id = article_id();
    if id < 0 {
        return;
    }
    if !ArticleModule::is_exist(boma, id) {
        ArticleModule::generate_article(boma, id, false, -1);
    }
    if !ArticleModule::is_exist(boma, id) {
        log_sword(boma, "spawn_failed", false, 0, 0);
        return;
    }
    attach_hand(boma);
    ArticleModule::set_visibility_whole(boma, id, true, ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL));
    set_sword_out(boma, true);
}

/// Removes the sword.
pub unsafe fn hide(boma: *mut BattleObjectModuleAccessor) {
    let id = article_id();
    if id >= 0 && ArticleModule::is_exist(boma, id) {
        ArticleModule::remove_exist(boma, id, ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL));
    }
    set_sword_out(boma, false);
}

fn is_owner_motion(motion: u64) -> bool {
    OWNER_MOTIONS.iter().any(|k| smash::hash40(k) == motion)
}

/// Once per frame on every Gunner: when the sword is out and the Gunner no longer plays one of the owned motions
/// (move ended, hit, grabbed, ledge, KO), the sword is removed. It acts on that transition only.
pub unsafe extern "C" fn sword_guard(fighter: &mut L2CFighterCommon) {
    let boma = fighter.module_accessor;
    if sword_out(boma) && !is_owner_motion(MotionModule::motion_kind(boma)) {
        hide(boma);
    }
}
