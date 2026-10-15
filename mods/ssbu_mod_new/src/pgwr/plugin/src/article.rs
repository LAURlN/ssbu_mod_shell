//! G&W's articles, cloned onto eflame by this plugin.
//!
//! Two so far, and both are the same shape: a *weapon* article the fighter's
//! own move scripts spawn and remove, with no G&W status code behind it.
//!
//! * `normal_weapon` (0.11.0) - every prop G&W holds: the stool, the manhole
//!   cover, the fishbowl, the turtle and the spray.
//! * `breath` (0.12.1) - up air. G&W's `AttackAirHi` is two article calls and
//!   nothing else; the projectile carries its own hitbox, in donor script code,
//!   so this one is cloned with `use_original_code = true`.
//!
//! # What the `normal_weapon` article is
//!
//! One article carries every prop G&W holds: the stool (`c01attacks3s`), the
//! manhole cover (`c02attacklw3`), the fishbowl (`c05attackairn` and its landing),
//! the turtle (`c05attackairb` and its landing) and the spray (the jab chain and
//! the down taunt). Each of the article's own clips selects its prop through a
//! mesh-visibility track, which is why `build.py` copies those clips verbatim.
//!
//! # What G&W's code does for it (measured, 0.11.0)
//!
//! Nothing beyond the fighter's own move scripts. In `lua2cpp_gamewatch.nro` the
//! hash of `gamewatch_normal_weapon` appears only in the three animcmd agent
//! factories (each builds an `L2CFighterAnimcmdBase` with no scripts, which is why
//! the ACMD dump has no folder for it). The status-script factory, which builds an
//! `L2CWeaponCommon` for `bomb`, `breath`, `octopus` and the rest, has no case for
//! it. So the whole behaviour is: the owner's move spawns it, tells it which clip
//! to play (`change_motion`) and removes it; the engine-side article descriptor
//! (copied by `clone_weapon`) does the rest. There is no G&W status code to port.
//!
//! # Registration
//!
//! `smashline::clone_weapon` is an FFI call into the installed smashline plugin
//! (`smashline_clone_weapon`, `src/api.rs:304`), which owns the article-table hook
//! that reads the registration. No change to the global plugin is needed.
//! 0.10.0 (Space Bunny) wrongly assumed the opposite and rebuilt the global plugin;
//! that build crashed the game and was rolled back.
//!
//! `use_original_code = false` for `normal_weapon`: G&W's lua2cpp module is
//! never loaded for it. As measured above there is nothing in it to load.
//! `breath` is the opposite case and is the exception - see `install`.
//!
//! The article table belongs to the fighter kind, so vanilla Pyra c00-c05 also
//! carry the entry. They never spawn it (only the c06/c07 scripts do), and
//! `build.py` ships the article's files for all eight slots so loading it at match
//! start finds them.
//!
//! # The id a move passes
//!
//! `ArticleModule::*` take the fighter's *local* article index. eflame has
//! `FIGHTER_EFLAME_ARTICLE_TERM` (5) articles of her own; smashline appends clones
//! after them and returns the clone's position among the clones. So the id is
//! `TERM + returned`: 5 for `normal_weapon`, 6 for `breath`. G&W's
//! `WEAPON_KIND_GAMEWATCH_NORMAL_WEAPON` (125) and `WEAPON_KIND_GAMEWATCH_BREATH`
//! (126) are the *global weapon kinds*, which is what `clone_weapon` takes, and
//! are not valid article indices on any fighter.
//!
//! A third clone, `chrom_sword`, was registered here in 0.16.0 and removed in
//! 0.17.0. It is the reason the two above are read back from the return value
//! rather than hardcoded, and the reason the order of the two calls is documented
//! as load-bearing: dropping a clone from the middle of this sequence would
//! renumber the ones after it.

use {
    smash::{
        lua2cpp::*,
        app::{*, lua_bind::*},
        lib::{lua_const::*, L2CAgent},
    },
    smash_script::macros,
    std::sync::atomic::{AtomicI32, Ordering},
};

/// eflame's local article index for the clone; -1 until `install` has run.
static NORMAL_WEAPON: AtomicI32 = AtomicI32::new(-1);
/// Same, for the `breath` clone (up air). -1 until `install` has run.
static BREATH: AtomicI32 = AtomicI32::new(-1);
/// Same, for the up-B pair: `rescue` (the firemen and trampoline) and `parachute`.
static RESCUE: AtomicI32 = AtomicI32::new(-1);
static PARACHUTE: AtomicI32 = AtomicI32::new(-1);

/// The local article id the generated moves pass to `ArticleModule`.
#[inline]
pub fn normal_weapon() -> i32 {
    NORMAL_WEAPON.load(Ordering::Relaxed)
}

/// The local article id for G&W's up-air breath projectile.
#[inline]
pub fn breath() -> i32 {
    BREATH.load(Ordering::Relaxed)
}

/// The local article id for G&W's up-B trampoline (`rescue`).
#[inline]
pub fn rescue() -> i32 {
    RESCUE.load(Ordering::Relaxed)
}

/// The local article id for G&W's up-B `parachute`.
#[inline]
pub fn parachute() -> i32 {
    PARACHUTE.load(Ordering::Relaxed)
}

/// Game image base for the version-checked breath parameter bridge.
pub unsafe fn game_base() -> *const u8 {
    skyline::hooks::getRegionAddress(skyline::hooks::Region::Text) as *const u8
}

/// Register the clones. Must run before any fighter is built: the installed
/// smashline caches each fighter's article table on first use.
///
/// # Order is the index
///
/// smashline keeps each fighter's clones in one `Vec` and returns the position
/// in it, and `get_static_fighter_data` appends the descriptors in that same
/// order after eflame's own five. So the *first* call is local article
/// `TERM + 0` and the second is `TERM + 1`. Swapping the two calls would not
/// crash - it would silently hand every move the other article, and the prop
/// work of 0.11.x would break with no error anywhere.
///
/// The ids are read back from the return value rather than hardcoded for the
/// same reason: this is the only number that says which article is which.
pub fn install() {
    let nw_index = smashline::clone_weapon(
        "gamewatch",
        *WEAPON_KIND_GAMEWATCH_NORMAL_WEAPON,
        "eflame",
        "normal_weapon",
        false,
    );
    let nw_id = *FIGHTER_EFLAME_ARTICLE_TERM + nw_index;
    NORMAL_WEAPON.store(nw_id, Ordering::Relaxed);

    // 0.12.0: up air. G&W's AttackAirHi is two article calls and nothing else -
    // spawn `breath` at frame 8, `shoot` it at frame 9.
    //
    // # Why this one asks for the donor's code and normal_weapon does not
    //
    // `use_original_code` is not a preference. It decides whether smashline
    // loads the *donor's* script module when the article is created
    // (`create_agent_status_weapon`, be3ef30: `get_weapon_code_dependency` ->
    // `load_fighter_module(0x1C)` -> retry the original create). With it false
    // the article's status agent is built as a bare `L2CWeaponCommon` with
    // `original_set_status_scripts = None` - an agent with **no status scripts
    // at all**.
    //
    // For `normal_weapon` that is fine, and measured: it has no donor status
    // code at all (no `gamewatch_normal_weapon` script folder), it is a dumb
    // prop whose animation its own clips select. 0.11.x proved it on hardware.
    //
    // For `breath` it was the crash. 0.12.0 first shipped this call with
    // `false` and the console froze on the exact frame the puff spawned, with
    // no `BREATH spawned` line in the log - the game died inside
    // `generate_article`. `lua2cpp_gamewatch/gamewatch_breath/AttackAirHi.txt`
    // is the projectile's own attack script, three shrinking hitboxes then a
    // strong one: that IS the damage up air does. Without the module loaded
    // the agent has nothing to run when the article enters its first status.
    //
    // So: true here, false there, and the difference is evidence, not taste.
    // Written before the call, not after: if the donor module fails to load,
    // `load_fighter_module` is followed by a `while !is_fighter_module_loaded`
    // spin, and the last line in the log would be this one - which is the whole
    // difference between "hung loading gamewatch" and "crashed somewhere else".
    crate::diagnostic!(log(format!("---- boot v{}: registering gamewatch breath with donor code", env!("CARGO_PKG_VERSION"))));
    let br_index = smashline::clone_weapon(
        "gamewatch",
        *WEAPON_KIND_GAMEWATCH_BREATH,
        "eflame",
        "breath",
        true,
    );
    let br_id = *FIGHTER_EFLAME_ARTICLE_TERM + br_index;
    BREATH.store(br_id, Ordering::Relaxed);

    crate::diagnostic!(log(format!(
        "---- boot v0.14.0: registered gamewatch weapon kind {} as eflame_normal_weapon, \
         clone index {}, local article id {}, donor code off (it has none)",
        *WEAPON_KIND_GAMEWATCH_NORMAL_WEAPON, nw_index, nw_id
    )));
    crate::diagnostic!(log(format!(
        "---- boot v0.14.0: registered gamewatch weapon kind {} as eflame_breath, \
         clone index {}, local article id {}, donor code on, spawn guarded by parameter bridge",
        *WEAPON_KIND_GAMEWATCH_BREATH, br_index, br_id
    )));
    // 0.19.0: up-B (Fire). Third and fourth clones, TERM + 2 and TERM + 3, so the two
    // above keep their ids. `rescue` and `parachute` register no weapon statuses in G&W's
    // lua2cpp (refs/gamewatch_special_hi/gamewatch_status_table.txt) - like
    // `normal_weapon` they are driven entirely by the owner's status code - so the donor
    // module is not loaded for them (`false`), and their only scripts, two visibility
    // ACMDs each, are this plugin's own copies (acmd::generated::special). Their native
    // descriptors (main+0xa7f7b0 / +0xa7fa90, tools/maindesc.py 0x1c) are copied by
    // smashline like every other clone's.
    let rs_index = smashline::clone_weapon(
        "gamewatch",
        *WEAPON_KIND_GAMEWATCH_RESCUE,
        "eflame",
        "rescue",
        false,
    );
    RESCUE.store(*FIGHTER_EFLAME_ARTICLE_TERM + rs_index, Ordering::Relaxed);
    let pc_index = smashline::clone_weapon(
        "gamewatch",
        *WEAPON_KIND_GAMEWATCH_PARACHUTE,
        "eflame",
        "parachute",
        false,
    );
    PARACHUTE.store(*FIGHTER_EFLAME_ARTICLE_TERM + pc_index, Ordering::Relaxed);
    crate::diagnostic!(log(format!(
        "---- boot v{}: registered gamewatch rescue ({}) as eflame_rescue id {} and parachute ({})          as eflame_parachute id {}, donor code off (neither has any)",
        env!("CARGO_PKG_VERSION"), *WEAPON_KIND_GAMEWATCH_RESCUE, rescue(),
        *WEAPON_KIND_GAMEWATCH_PARACHUTE, parachute()
    )));
    // 0.16.0 registered a third clone here, Chrom's Falchion, for his jab. 0.17.0
    // removed it: on hardware the article never rendered at all, and the jab now
    // draws Pyra's own esword instead (see `acmd::chrom_jab`). Nothing else read
    // `chrom_sword()`, and the two remaining clones keep their indices because they
    // are still registered first and in this order.
    crate::breath::install();
}

// G&W's `WEAPON_GAMEWATCH_NORMAL_WEAPON_KIND_*`, the values his moves write. The
// generated code names them as constants, so they are restated here from the
// locked lua_const; `check_kinds` logs if the two ever drift apart.
pub const KIND_SPRAY: i32 = 0x0;
pub const KIND_MANHOLE: i32 = 0x1;
pub const KIND_TROPICALFISH: i32 = 0x3;
pub const KIND_TURTLE: i32 = 0x4;
pub const KIND_CHAIR: i32 = 0x5;

/// Logs if the restated kind values ever disagree with the locked lua_const.
pub fn check_kinds() {
    let pairs = [
        ("SPRAY", KIND_SPRAY, *WEAPON_GAMEWATCH_NORMAL_WEAPON_KIND_SPRAY),
        ("MANHOLE", KIND_MANHOLE, *WEAPON_GAMEWATCH_NORMAL_WEAPON_KIND_MANHOLE),
        ("TROPICALFISH", KIND_TROPICALFISH, *WEAPON_GAMEWATCH_NORMAL_WEAPON_KIND_TROPICALFISH),
        ("TURTLE", KIND_TURTLE, *WEAPON_GAMEWATCH_NORMAL_WEAPON_KIND_TURTLE),
        ("CHAIR", KIND_CHAIR, *WEAPON_GAMEWATCH_NORMAL_WEAPON_KIND_CHAIR),
    ];
    for (name, ours, theirs) in pairs {
        if ours != theirs {
            crate::diagnostic!(println!("{} ARTICLE kind {} is {} here but {} in lua_const", crate::LOG, name, ours, theirs));
        }
    }
}

/// The player slot (0-7). Pyra and Mythra are two battle objects sharing one slot,
/// so the battle object id is not guaranteed to be below 8; the entry id is.
#[inline]
unsafe fn entry(boma: *mut BattleObjectModuleAccessor) -> usize {
    WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID) as usize
}

/// Appends one line to `sd:/ultimate/pgwr_log.txt` and prints it.
///
/// Diagnostic, not donor behaviour: the TCP log is not captured on the console, so
/// the prop's lifecycle is written to the card where it can be read after a test.
/// Only events are written (spawn, status change while a prop exists, removal),
/// never one line per frame.
#[cfg(feature = "logging")]
pub fn log(line: String) {
    use std::io::Write;
    crate::diagnostic!(println!("{} {}", crate::LOG, line));
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open("sd:/ultimate/pgwr_log.txt")
    {
        let _ = writeln!(f, "{}", line);
    }
}

#[cfg(not(feature = "logging"))]
#[inline(always)]
pub fn log(_line: String) {}

/// Which prop this entry last asked for, by entry id.
///
/// G&W keeps it in his instance work int 0x100000BD. On an eflame agent that index
/// is not his slot, so writing it there could clobber something of Pyra's. Nothing
/// in lua2cpp reads it (see the module notes); if an engine-side reader exists it
/// is in `main` and has not been found. Kept here so the donor's write is not
/// silently discarded.
static mut ARTICLE_KIND: [i32; 8] = [-1; 8];

#[inline]
pub unsafe fn set_kind(agent: &mut L2CAgentBase, kind: i32) {
    let id = entry(agent.module_accessor);
    if id < 8 {
        ARTICLE_KIND[id] = kind;
    }
}

pub unsafe fn kind(agent: &L2CAgentBase) -> i32 {
    let id = entry(agent.module_accessor);
    if id < 8 { ARTICLE_KIND[id] } else { -1 }
}

/// The owner status each entry's prop was spawned in; -1 when it has none.
static mut SPAWN_STATUS: [i32; 8] = [-1; 8];
/// The last owner status `lifetime` logged for each entry, so only changes are logged.
static mut LAST_STATUS: [i32; 8] = [-1; 8];

/// Whether a prop spawned in status `spawned` may still exist in status `now`.
///
/// Only the continuations G&W's own scripts carry the prop into: the jab spray into
/// the rapid jab (`attack_100` / `attack_100_end` only call `change_motion`), and an
/// aerial's prop into its landing (`landing_air_n` / `landing_air_b` do the same).
fn may_keep(spawned: i32, now: i32) -> bool {
    now == spawned
        || (spawned == *FIGHTER_STATUS_KIND_ATTACK && now == *FIGHTER_STATUS_KIND_ATTACK_100)
        || (spawned == *FIGHTER_STATUS_KIND_ATTACK_AIR && now == *FIGHTER_STATUS_KIND_LANDING_ATTACK_AIR)
}

/// Removes the prop once the owner has left the move that spawned it.
///
/// # Why this is ours and not ported
///
/// In vanilla the prop disappears when G&W is hit out of a move, or when an aerial
/// ends in the air. None of G&W's lua2cpp code does that: every `ArticleModule`
/// call on NORMAL_WEAPON's constant (lua2cpp_common const table offset 0xeb1c,
/// resolved by its XXH64 name hash) is in a move script, and each of those is
/// ported. The status code only touches the special-move articles (rescue,
/// parachute, oil, octopus, food). So the removal is native code in `main` that
/// keys on G&W as the owner and does not run for an eflame owner. It cannot be
/// copied, so this reproduces the observable rule instead. It runs only on the
/// gated c06/c07 agent.
unsafe extern "C" fn lifetime(agent: &mut L2CAgent) {
    let boma = agent.module_accessor;
    let id = entry(boma);
    if id >= 8 {
        return;
    }
    let nw = normal_weapon();
    let active = ArticleModule::get_active_num(boma, nw);
    let exists = ArticleModule::is_exist(boma, nw);
    let now = StatusModule::status_kind(boma);
    if SPAWN_STATUS[id] < 0 {
        if active > 0 || exists {
            crate::diagnostic!(log(format!("entry {} UNTRACKED prop: status {:#x} exists {} active {}", id, now, exists, active)));
            SPAWN_STATUS[id] = now;
            LAST_STATUS[id] = now;
        }
        return;
    }
    if now != LAST_STATUS[id] {
        crate::diagnostic!(log(format!(
            "entry {} status {:#x} -> {:#x} (spawned in {:#x}) exists {} active {} motion {:#x}",
            id, LAST_STATUS[id], now, SPAWN_STATUS[id], exists, active,
            MotionModule::motion_kind(boma)
        )));
        LAST_STATUS[id] = now;
    }
    if !exists && active == 0 {
        crate::diagnostic!(log(format!("entry {} prop gone by itself in status {:#x}", id, now)));
        SPAWN_STATUS[id] = -1;
        return;
    }
    if !may_keep(SPAWN_STATUS[id], now) {
        ArticleModule::remove_exist(boma, nw, ArticleOperationTarget(*ARTICLE_OPE_TARGET_ALL));
        crate::diagnostic!(log(format!(
            "entry {} REMOVED prop: left status {:#x} for {:#x}; after remove exists {} active {}",
            id, SPAWN_STATUS[id], now,
            ArticleModule::is_exist(boma, nw), ArticleModule::get_active_num(boma, nw)
        )));
        SPAWN_STATUS[id] = -1;
    }
}

pub fn install_lifetime() {
    smashline::Agent::new("eflame")
        .set_costume(crate::TARGET_COSTUMES.to_vec())
        .on_line(smashline::Main, lifetime)
        .install();
}

/// Logged just after each spawn, so the log can tell "never spawned" from
/// "spawned but not visible". Also records the spawning status for `lifetime`.
#[inline]
pub unsafe fn note_spawn(agent: &mut L2CAgentBase, motion: &str) {
    let boma = agent.module_accessor;
    let id = entry(boma);
    let status = StatusModule::status_kind(boma);
    if id < 8 {
        SPAWN_STATUS[id] = status;
        LAST_STATUS[id] = status;
    }
    let exists = is_exist(agent);
    crate::diagnostic!(log(format!(
        "entry {} (object {:#x}) SPAWN motion {} prop {} article id {} status {:#x} \
         IS_EXIST_ARTICLE {} is_exist {} active {}",
        id, (*agent.battle_object).battle_object_id, motion, kind(agent), normal_weapon(), status,
        exists, ArticleModule::is_exist(boma, normal_weapon()),
        ArticleModule::get_active_num(boma, normal_weapon())
    )));
}

/// `IS_EXIST_ARTICLE` on the clone.
#[inline]
pub unsafe fn is_exist(agent: &mut L2CAgentBase) -> bool {
    macros::IS_EXIST_ARTICLE(agent, normal_weapon())
}

/// Logged after up air shoots the breath, and once more on the frame after, so
/// the log can tell "never spawned" from "spawned and then vanished".
///
/// Unlike `note_spawn` this does not touch the `lifetime` state: the breath is a
/// projectile that outlives the move on purpose, and `lifetime` exists to hold a
/// *held* prop across a status change. Registering it there would delete the
/// projectile the moment Pyra lands, which is the opposite of the move.
#[inline]
pub unsafe fn note_breath(agent: &mut L2CAgentBase, stage: &str) {
    let boma = agent.module_accessor;
    let id = entry(boma);
    let br = breath();
    crate::diagnostic!(log(format!(
        "entry {} (object {:#x}) BREATH {} article id {} status {:#x} \
         IS_EXIST_ARTICLE {} is_exist {} active {}",
        id, (*agent.battle_object).battle_object_id, stage, br,
        StatusModule::status_kind(boma),
        macros::IS_EXIST_ARTICLE(agent, br),
        ArticleModule::is_exist(boma, br),
        ArticleModule::get_active_num(boma, br)
    )));
}
