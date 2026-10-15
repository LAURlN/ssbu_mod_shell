//! Shared by the two Cloud units (MV-aerial_forward__cloud, MV-special_up__cloud): the Buster Sword
//! article, the per-fighter state both moves keep, and a non-panicking lookup of a vanilla status.
//!
//! # The sword
//!
//! The Gunner's body has no sword mesh, and Cloud's sword is two meshes of his body model (one per hand,
//! each bound to a hand bone). So the sword is a Gunner article, `mccloudsword`:
//! `smashline::clone_weapon("gamewatch", WEAPON_KIND_GAMEWATCH_NORMAL_WEAPON, "miigunner", ...)` with no
//! donor code. That donor is the one clone the reference mod has seen rendered on the console
//! (mods/ssbu_mod_new handbook/07_articles.md, 0.11.0): a prop with no status code, spawned, given a motion
//! and removed by its owner's move. Its files (fighter/miigunner/{model,motion}/mccloudsword/c00) are
//! Cloud's sword meshes on a single bone `Have` and two one-frame clips that draw the right-hand or the
//! left-hand blade.
//!
//! The article is tied to the Gunner's hand with the engine's own model constraint, the call a vanilla
//! weapon makes on itself (measured in lua2cpp_pit.nro 0x256b0..0x257ec: remove_model_constraint, unlink,
//! link, set_model_constraint_pos_ort(link, own joint, parent joint, POSITION | ORIENTATION, true),
//! set_attribute(REFERENCE_PARENT_SCALE)). Own joint `have`, parent joint `haver` or `havel`. Cloud moves
//! the sword to the left hand for the dive (`VisibilityModule::set_int64("sword", "sword_l")` in his
//! expression scripts); here that is `set_hand`.
//!
//! The article is registered only when its model file is found under `sd:/ultimate/mods/*/`: a registered
//! article whose files are missing crashes every Gunner at match start (handbook/07). Without it both
//! units keep the vanilla move.
//!
//! Tier D for everything on screen: whether the clone renders on a Gunner and whether the constraint holds
//! it in the hand is for the console. The log lines below tell the cases apart.

use core::sync::atomic::{AtomicI32, AtomicU32, AtomicUsize, Ordering};
use smash::{
    app::{lua_bind::*, *},
    lib::lua_const::*,
    lua2cpp::*,
    phx::*,
};

use crate::{emit_wait, head, LineBuf};

pub const ARTICLE_NAME: &str = "mccloudsword";
const SWORD_MODEL_FILE: &str = "fighter/miigunner/model/mccloudsword/c00/model.numshb";

/// Gunner-local article id of the sword; -1 while it is not registered.
static SWORD: AtomicI32 = AtomicI32::new(-1);
static LOG_COUNT: AtomicU32 = AtomicU32::new(0);

// Motion kinds this mod adds for Cloud's two moves (body).
pub const MOTIONS: [&str; 8] = [
    "mc_cloud_attack_air_f",
    "mc_cloud_landing_air_f",
    "mc_cloud_special_hi",
    "mc_cloud_special_air_hi",
    "mc_cloud_special_hi2",
    "mc_cloud_special_hi2_fall",
    "mc_cloud_special_hi2_end",
    "mc_cloud_special_hi2_landing",
];

/// Cloud's `FIGHTER_CLOUD_STATUS_SPECIAL_HI_FLAG_*`, kept here because those status-flag numbers are
/// Cloud's and mean nothing on a Gunner.
pub const HI_FLAG_IS_2_SHIFT_INPUT: u32 = 1 << 0;
pub const HI_FLAG_IS_ENABLE_CONTROL: u32 = 1 << 1;
pub const HI_FLAG_FALL: u32 = 1 << 2;
pub const HI_FLAG_SHIFT: u32 = 1 << 3;
pub const HI_FLAG_SHIFT_RESERVE: u32 = 1 << 4;

/// Cloud's `FIGHTER_CLOUD_SPECIAL_HI2_HIT_OBJECT_NUM_MAX`.
pub const HIT_OBJECT_MAX: usize = 15;

/// Work variables of one Gunner (indexed by entry id).
#[derive(Clone, Copy)]
pub struct State {
    /// The sword article is out.
    pub sword_out: bool,
    /// The saved Mii chose Cloud's up special and the current SPECIAL_HI runs it.
    pub upb: bool,
    /// Cloud's SPECIAL_HI status flags (`HI_FLAG_*`).
    pub hi_flags: u32,
    /// Cloud's `FIGHTER_CLOUD_STATUS_SPECIAL_HI2_INT_FALL_FRAME`.
    pub fall_frame: i32,
    /// Cloud's `..._SPECIAL_HI2_INT_HIT_OBJECT_NUM` / `..._HIT_OBJECT_ID`.
    pub hit_num: usize,
    pub hit_ids: [u32; HIT_OBJECT_MAX],
}

const EMPTY: State = State {
    sword_out: false,
    upb: false,
    hi_flags: 0,
    fall_frame: 0,
    hit_num: 0,
    hit_ids: [0; HIT_OBJECT_MAX],
};

static mut STATE: [State; 8] = [EMPTY; 8];

pub unsafe fn state(boma: *mut BattleObjectModuleAccessor) -> Option<&'static mut State> {
    let entry = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
    if (0..8).contains(&entry) {
        Some(&mut *core::ptr::addr_of_mut!(STATE[entry as usize]))
    } else {
        None
    }
}

pub unsafe fn hi_flag(boma: *mut BattleObjectModuleAccessor, flag: u32) -> bool {
    state(boma).map(|s| s.hi_flags & flag != 0).unwrap_or(false)
}

pub unsafe fn set_hi_flag(boma: *mut BattleObjectModuleAccessor, flag: u32, on: bool) {
    if let Some(s) = state(boma) {
        if on {
            s.hi_flags |= flag;
        } else {
            s.hi_flags &= !flag;
        }
    }
}

// ---------------------------------------------------------------------------
// Vanilla status lookup that cannot panic
// ---------------------------------------------------------------------------

/// `smashline::original_status` panics when the fighter has no vanilla function for that line (the
/// Gunner registers INIT / EXEC of SPECIAL_HI only for two of its three up specials). This asks the
/// installed Smashline the same question and returns `None` instead.
pub unsafe fn vanilla_status(
    fighter: &mut L2CFighterCommon,
    line: smashline::StatusLine,
    kind: i32,
) -> Option<unsafe extern "C" fn(&mut L2CFighterCommon) -> smash::lib::L2CValue> {
    static ADDR: AtomicUsize = AtomicUsize::new(0);
    let mut addr = ADDR.load(Ordering::Acquire);
    if addr == 0 {
        let mut value = 0usize;
        let res = skyline::nn::ro::LookupSymbol(
            &mut value,
            b"smashline_get_original_status\0".as_ptr() as *const skyline::libc::c_char,
        );
        if res != 0 || value == 0 {
            return None;
        }
        ADDR.store(value, Ordering::Release);
        addr = value;
    }
    let get: extern "C" fn(&mut L2CFighterCommon, smashline::StatusLine, i32) -> Option<core::ptr::NonNull<()>> =
        core::mem::transmute(addr);
    get(fighter, line, kind).map(|p| core::mem::transmute(p.as_ptr()))
}

/// Runs the vanilla function of `line` for `kind`, or returns 0 when the Gunner has none.
pub unsafe fn run_vanilla(
    fighter: &mut L2CFighterCommon,
    line: smashline::StatusLine,
    kind: i32,
) -> smash::lib::L2CValue {
    match vanilla_status(fighter, line, kind) {
        Some(f) => f(fighter),
        None => smash::lib::L2CValue::new_int(0),
    }
}

// ---------------------------------------------------------------------------
// Sword article
// ---------------------------------------------------------------------------

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

/// Registers the article. Must run before any fighter is built (Smashline caches a fighter's article
/// table on first use), so it is called from `moves::install`.
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
    out.s("|cloud_sword|files=").s(if present { "found" } else { "missing" });
    out.s("|article=");
    let id = article_id();
    if id >= 0 {
        out.dec(id as u64);
    } else {
        out.s("none|action=cloud_moves_stay_vanilla");
    }
    out.end_line();
    emit_wait(out.as_bytes());
}

pub fn article_id() -> i32 {
    SWORD.load(Ordering::Acquire)
}

/// The sword article is registered and every owned motion of `kinds` is in the loaded motion list.
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
    out.s("|cloud_sword|").s(what);
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

/// Draws the right- or left-hand blade and ties the article to that hand.
pub unsafe fn set_hand(boma: *mut BattleObjectModuleAccessor, left: bool) {
    let id = article_id();
    let sword = article_boma(boma);
    if sword.is_null() {
        return;
    }
    ArticleModule::change_motion(
        boma,
        id,
        Hash40::new(if left { "mc_cloud_sword_l" } else { "mc_cloud_sword_r" }),
        false,
        -1.0,
    );
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
        Hash40::new(if left { "havel" } else { "haver" }),
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
        if left { "hand=l" } else { "hand=r" },
        true,
        LinkModule::get_model_constraint_target_joint(sword),
        LinkModule::get_model_constraint_flag(sword),
    );
}

/// Puts the sword in the hand (spawns the article when it is not out).
pub unsafe fn show(boma: *mut BattleObjectModuleAccessor, left: bool) {
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
    set_hand(boma, left);
    ArticleModule::set_visibility_whole(boma, id, true, ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL));
    if let Some(s) = state(boma) {
        s.sword_out = true;
    }
}

/// Removes the sword.
pub unsafe fn hide(boma: *mut BattleObjectModuleAccessor) {
    let id = article_id();
    if id >= 0 && ArticleModule::is_exist(boma, id) {
        ArticleModule::remove_exist(boma, id, ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL));
    }
    if let Some(s) = state(boma) {
        s.sword_out = false;
    }
}

fn is_cloud_motion(motion: u64) -> bool {
    MOTIONS.iter().any(|k| smash::hash40(k) == motion)
}

/// Once per frame on every Gunner: when the sword is out and the Gunner no longer plays one of Cloud's
/// motions (move ended, hit, grabbed, ledge, KO), the sword is removed. It acts on that transition only.
pub unsafe extern "C" fn sword_guard(fighter: &mut L2CFighterCommon) {
    let boma = fighter.module_accessor;
    let Some(s) = state(boma) else { return };
    if s.sword_out && !is_cloud_motion(MotionModule::motion_kind(boma)) {
        hide(boma);
    }
}
