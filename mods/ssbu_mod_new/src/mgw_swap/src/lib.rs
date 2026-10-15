#![feature(
    proc_macro_hygiene
)]
#![allow(
    unused_imports,
    unused_macros,
    unused_variables,
    unused_assignments,
    unused_unsafe,
    non_upper_case_globals,
    non_snake_case,
    clippy::borrow_interior_mutable_const
)]

use {
    smash::{
        lua2cpp::*,
        phx::*,
        app::{sv_animcmd::*, lua_bind::*, *},
        lib::{lua_const::*, L2CValue, L2CAgent},
        hash40
    },
    smash_script::*,
    smashline::{*, Priority::*}
};

pub const TARGET_COSTUMES: [usize; 2] = [6, 7]; // Costume 7 and Costume 8.
#[inline]
pub fn is_target_costume(color: i32) -> bool {
    color >= 0 && TARGET_COSTUMES.contains(&(color as usize))
}
#[cfg(feature = "swap-diagnostics")]
mod diagnostics;
mod swap_handoff;
mod attack_air_hi;
mod throw_lw;
mod monkey_flip;
mod monkey_flip_status;
mod monkey_flip_params;
mod hero_spin3;
mod hero_spin3_params;
mod attack_air_f;
pub const FIGHTER_KIND_GAMEWATCH: i32 = 28;
pub const FIGHTER_KIND_EFLAME: i32 = 90;
pub const FIGHTER_KIND_ELIGHT: i32 = 91;

// Global Aegis sub-fighter table offset in cross2_Release.nss (rodata)
// In vanilla, this table is: [90, 91, -1] (Pyra, Mythra, END).
// 0x655320 and 0x64f820 read this table to construct sub-fighters and initialize their AI/actions.
pub const AEGIS_PAIR_TABLE_OFFSET: usize = 0x453b158;
pub const VANILLA_AEGIS_TABLE: [i32; 3] = [FIGHTER_KIND_EFLAME, FIGHTER_KIND_ELIGHT, -1];
pub const TARGET_AEGIS_TABLE: [i32; 3] = [FIGHTER_KIND_GAMEWATCH, FIGHTER_KIND_ELIGHT, -1];

// Global entry tracking
// Indexed by entry_id (0..8)
static mut ENTRY_PTRS: [*mut u8; 8] = [std::ptr::null_mut(); 8];
static mut IS_PAIRED_ENTRY: [bool; 8] = [false; 8];
static mut SWAP_REQUESTED: [bool; 8] = [false; 8];

// Frozen return-swap snapshot: G&W's down-B request seeds it and the native
// capture hook refreshes it once. Only the post-restore hook consumes it.
static mut SAVED_POS_X: [f32; 8] = [0.0; 8];
static mut SAVED_POS_Y: [f32; 8] = [0.0; 8];
static mut SAVED_POS_Z: [f32; 8] = [0.0; 8];
static mut SAVED_LR: [f32; 8] = [1.0; 8];
static mut SAVED_SITUATION: [i32; 8] = [0; 8];
static mut HOLDING_SWAP_TO_MYTHRA: [bool; 8] = [false; 8];
static mut SWAP_CAMERA_PENDING: [bool; 8] = [false; 8];
const INVALID_FIGHTER_ID: u32 = 0x50000000;
static mut HIDDEN_BY_SWAP: [[u32; 2]; 8] = [[INVALID_FIGHTER_ID; 2]; 8];

// Damage synchronization tracking
static mut SHARED_DAMAGE: [f32; 8] = [0.0; 8];
static mut PREV_ACTIVE_IDX: [u8; 8] = [0; 8];


// True pre-match resource preloader hook at 0x17e5c00.
// 0x17e5c00 is called by 0x66de54 during pre-match loading to preload fighter NROs and 3D models into the Resource Cache.
// By substituting [preload_record + 0x5c] (k1) to FIGHTER_KIND_GAMEWATCH (28) here, 0x17e5c00 dispatches:
// 1. lua2cpp_gamewatch.nro queueing to L2CDynamicModuleManager via 0x17e4940(mgr, 28)
// 2. Preloading of fighter/gamewatch/model/body/<costume>/model.numdlb, skeletons, textures, and all 9 submodels
// into the Global Resource Cache (0x5331f20).
// This guarantees fighter_initialize_object_data finds Game & Watch's model at 0x35c2344, eliminating the crash.
#[skyline::hook(offset = 0x17e5c00)]
unsafe extern "C" fn preload_fighter_resources_hook(preload_record: *mut u8) {
    let entry_id = *preload_record.add(0x54) as i32;
    let k0 = *(preload_record.add(0x58) as *const i32);
    let k1 = *(preload_record.add(0x5c) as *const i32);
    let costume = *(preload_record.add(0x64) as *const i32);

    println!(
        "[Mythra-GW-Swap] 0x17e5c00 Preload: entry {}, k0={}, k1={}, costume={}",
        entry_id, k0, k1, costume
    );

    let is_target_pair = is_target_costume(costume) 
        && (k0 == FIGHTER_KIND_ELIGHT || k0 == FIGHTER_KIND_EFLAME);

    if is_target_pair {
        println!(
            "[Mythra-GW-Swap] 0x17e5c00 Preload: Substituting partner on entry {} (k0={}, k1={} -> {})",
            entry_id, k0, k1, FIGHTER_KIND_GAMEWATCH
        );

        if k0 == FIGHTER_KIND_ELIGHT {
            *(preload_record.add(0x5c) as *mut i32) = FIGHTER_KIND_GAMEWATCH;
        } else if k0 == FIGHTER_KIND_EFLAME {
            *(preload_record.add(0x58) as *mut i32) = FIGHTER_KIND_ELIGHT;
            *(preload_record.add(0x5c) as *mut i32) = FIGHTER_KIND_GAMEWATCH;
        }
    }

    call_original!(preload_record);

    // Ordinary c06/c07 G&W has no Elight fighter object, so its native preload
    // never queues Elight's effect archive. Reuse the game's own preload
    // dispatcher once with a temporary Elight kind to populate that cache.
    // Restore the record before returning; this does not change the fighter
    // kind or create an Elight fighter.
    if is_target_costume(costume)
        && k0 == FIGHTER_KIND_GAMEWATCH
        && k1 == -1
    {
        *(preload_record.add(0x58) as *mut i32) = FIGHTER_KIND_ELIGHT;
        *(preload_record.add(0x5c) as *mut i32) = -1;
        println!(
            "[Mythra-GW-Swap] 0x17e5c00 Preload: queuing Elight effects for ordinary G&W c06/c07 entry {}",
            entry_id
        );
        call_original!(preload_record);
        *(preload_record.add(0x58) as *mut i32) = k0;
        *(preload_record.add(0x5c) as *mut i32) = k1;
    }

}

pub unsafe fn is_target_pair(entry: *mut u8) -> bool {
    if entry.is_null() {
        return false;
    }
    let fighter_num = *(entry.add(0x14) as *const i32);
    let kind_0 = *(entry.add(0x18) as *const i32);
    let costume = *entry.add(0x41) as i32;
    fighter_num >= 2 
        && is_target_costume(costume) 
        && (kind_0 == FIGHTER_KIND_ELIGHT || kind_0 == FIGHTER_KIND_EFLAME)
}

pub unsafe fn is_target_swap_active(boma: *mut BattleObjectModuleAccessor) -> bool {
    let entry_id = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
    if entry_id < 0 || entry_id as usize >= IS_PAIRED_ENTRY.len() {
        return false;
    }
    let entry = ENTRY_PTRS[entry_id as usize];
    IS_PAIRED_ENTRY[entry_id as usize]
        && !entry.is_null()
        && *(entry.add(0x5918) as *const u8) == 1
        && FighterEntry::current_fighter_id(entry as *mut smash::app::FighterEntry) as u32 == (*boma).battle_object_id
}

#[skyline::hook(offset = 0x658af0)]
unsafe extern "C" fn fighter_entry_init_hook(entry: *mut u8) {
    let fighter_num = *(entry.add(0x14) as *const i32);
    let kind_0 = *(entry.add(0x18) as *const i32);
    let kind_1 = *(entry.add(0x1c) as *const i32);
    let costume = *entry.add(0x41) as i32;
    let entry_id = *(entry.add(0xe0) as *const i32);
    
    println!(
        "[Mythra-GW-Swap] FighterEntry Init: {:p} | num: {}, k0: {}, k1: {}, costume: {}, entry_id: {}",
        entry, fighter_num, kind_0, kind_1, costume, entry_id
    );

    // Clear pair tracking for this entry_id before checking
    if entry_id >= 0 && (entry_id as usize) < IS_PAIRED_ENTRY.len() {
        IS_PAIRED_ENTRY[entry_id as usize] = false;
        MATCH_WAS_READY[entry_id as usize] = false;
        SHARED_DAMAGE[entry_id as usize] = 0.0;
        PREV_ACTIVE_IDX[entry_id as usize] = 0;
        HOLDING_SWAP_TO_MYTHRA[entry_id as usize] = false;
        SWAP_CAMERA_PENDING[entry_id as usize] = false;
        SWAP_REQUESTED[entry_id as usize] = false;
        HIDDEN_BY_SWAP[entry_id as usize] = [INVALID_FIGHTER_ID; 2];
        ENTRY_PTRS[entry_id as usize] = entry;
        #[cfg(feature = "swap-diagnostics")]
        diagnostics::reset(entry_id as usize);
    }
    
    let is_target = is_target_pair(entry);

    if is_target {
        if entry_id >= 0 && (entry_id as usize) < IS_PAIRED_ENTRY.len() {
            IS_PAIRED_ENTRY[entry_id as usize] = true;
        }

        // Ensure partner kind is Game & Watch in FighterEntry
        if kind_0 == FIGHTER_KIND_ELIGHT {
            *(entry.add(0x1c) as *mut i32) = FIGHTER_KIND_GAMEWATCH;
        } else if kind_0 == FIGHTER_KIND_EFLAME {
            *(entry.add(0x18) as *mut i32) = FIGHTER_KIND_ELIGHT;
            *(entry.add(0x1c) as *mut i32) = FIGHTER_KIND_GAMEWATCH;
        }

        println!(
            "[Mythra-GW-Swap] Target c06/c07 Mythra verified on entry_id {}! (Active k0={}, k1={})",
            entry_id, *(entry.add(0x18) as *const i32), *(entry.add(0x1c) as *const i32)
        );
    }
    
    call_original!(entry);

    let sf0 = *(entry.add(0x4188) as *const *mut u8);
    let sf1 = *(entry.add(0x4190) as *const *mut u8);
    let active_sf = *(entry.add(0x4178) as *const *mut u8);
    println!(
        "[Mythra-GW-Swap] Post-Init: SF0: {:p}, SF1: {:p}, ActiveSF: {:p}",
        sf0, sf1, active_sf
    );
}

// 1. Entry-specific sub-fighter construction table selection (0x655484 in 0x655320)
// Right after csel x23, x9, x23, eq: x19 is entry, x23 is the table pointer.
#[skyline::hook(offset = 0x655484, inline)]
unsafe fn subfighter_construct_table_select_hook(ctx: &mut skyline::hooks::InlineCtx) {
    let entry = ctx.registers[19].x() as *mut u8;
    if is_target_pair(entry) {
        ctx.registers[23].set_x(TARGET_AEGIS_TABLE.as_ptr() as u64);
        println!("[Mythra-GW-Swap] 0x655484: Selected TARGET_AEGIS_TABLE for sub-fighter construction (G&W)");
    }
}

// 2. Entry-specific sub-fighter AI-action & AI-mode initialization table selection (0x64f9e8 in 0x64f820)
// Right after csel x21, x9, x21, eq: x19 is entry, x21 is the table pointer.
#[skyline::hook(offset = 0x64f9e8, inline)]
unsafe fn subfighter_ai_init_table_select_hook(ctx: &mut skyline::hooks::InlineCtx) {
    let entry = ctx.registers[19].x() as *mut u8;
    if is_target_pair(entry) {
        ctx.registers[21].set_x(TARGET_AEGIS_TABLE.as_ptr() as u64);
        println!("[Mythra-GW-Swap] 0x64f9e8: Selected TARGET_AEGIS_TABLE for sub-fighter AI init (G&W)");
    }
}

// 3. Entry-specific active sub-fighter lookup table selection (0x64fbcc in 0x64f820)
// Right after csel x9, x11, x10, eq: x19 is entry, x9 is the table pointer.
#[skyline::hook(offset = 0x64fbcc, inline)]
unsafe fn subfighter_active_select_table_hook(ctx: &mut skyline::hooks::InlineCtx) {
    let entry = ctx.registers[19].x() as *mut u8;
    if is_target_pair(entry) {
        ctx.registers[9].set_x(TARGET_AEGIS_TABLE.as_ptr() as u64);
        let entry_id = *(entry.add(0xe0) as *const i32);
        let active_idx = *(entry.add(0x5918) as *const u8);
        println!(
            "[Mythra-GW-Swap] 0x64fbcc: Selected TARGET_AEGIS_TABLE (entry {}, active_idx {})",
            entry_id, active_idx
        );
    }
}

// 4. Entry-specific sub-fighter destruction table selection (0x6516e4 in 0x6516a0)
// Right after csel x20, x9, x20, eq: x19 is entry, x20 is the table pointer.
#[skyline::hook(offset = 0x6516e4, inline)]
unsafe fn subfighter_destroy_table_select_hook(ctx: &mut skyline::hooks::InlineCtx) {
    let entry = ctx.registers[19].x() as *mut u8;
    if is_target_pair(entry) {
        ctx.registers[20].set_x(TARGET_AEGIS_TABLE.as_ptr() as u64);
        println!("[Mythra-GW-Swap] 0x6516e4: Selected TARGET_AEGIS_TABLE for sub-fighter teardown");
    }
}

static mut MATCH_WAS_READY: [bool; 8] = [false; 8];

// Safely configure Game & Watch as the active sub-fighter on target pair entry.
// Crucially, 0x4178 must hold the coordinator struct pointer (0x4188), NEVER the Fighter object!
pub unsafe fn set_active_subfighter_gw(entry: *mut u8) {
    if entry.is_null() || !is_target_pair(entry) {
        return;
    }
    *(entry.add(0x5918) as *mut u8) = 1; // Active sub-fighter index = 1 (Game & Watch)
    *(entry.add(0x5919) as *mut u8) = 1;
    *(entry.add(0x591a) as *mut u8) = 1;
    *(entry.add(0x591b) as *mut u8) = 0;
    *(entry.add(0x5920) as *mut u8) = 0;

    let sf_gw_coord = *(entry.add(0x4188) as *const *mut u8);
    if !sf_gw_coord.is_null() {
        *(entry.add(0x4178) as *mut *mut u8) = sf_gw_coord;
    }

    let text_base = skyline::hooks::getRegionAddress(skyline::hooks::Region::Text) as usize;
    let update_active_subfighter: extern "C" fn(*mut u8) = std::mem::transmute(text_base + 0x64fb70);
    update_active_subfighter(entry);
}

// Global safe dummy buffer for voice data lookups
// In cross2_Release.nss, functions at 0x655f60, 0x656400, 0x656ee0 dereference [x8 + 0x58] -> [x9 + 0x160]
// to fetch character voice/audio metadata. Redirecting any null pointer to this static buffer safely supplies
// 0xff, causing the downstream bounds check (cmp w, #0xf; b.hi) to cleanly skip voice dispatch without aborting.
static DUMMY_VOICE_STRUCT: [u32; 0x100] = [0xff; 0x100];

#[skyline::hook(offset = 0x656fdc, inline)]
unsafe fn sound_id_null_guard_656fdc(ctx: &mut skyline::hooks::InlineCtx) {
    if ctx.registers[9].x() == 0 {
        ctx.registers[9].set_x(DUMMY_VOICE_STRUCT.as_ptr() as u64);
    }
}

#[skyline::hook(offset = 0x656e80, inline)]
unsafe fn sound_id_null_guard_656e80(ctx: &mut skyline::hooks::InlineCtx) {
    if ctx.registers[9].x() == 0 {
        ctx.registers[9].set_x(DUMMY_VOICE_STRUCT.as_ptr() as u64);
    }
}

#[skyline::hook(offset = 0x656470, inline)]
unsafe fn sound_id_null_guard_656470(ctx: &mut skyline::hooks::InlineCtx) {
    if ctx.registers[8].x() == 0 {
        ctx.registers[8].set_x(DUMMY_VOICE_STRUCT.as_ptr() as u64);
    }
}

#[skyline::hook(offset = 0x655fc8, inline)]
unsafe fn sound_id_null_guard_655fc8(ctx: &mut skyline::hooks::InlineCtx) {
    if ctx.registers[8].x() == 0 {
        ctx.registers[8].set_x(DUMMY_VOICE_STRUCT.as_ptr() as u64);
    }
}

unsafe fn hide_swap_fighter(boma: *mut BattleObjectModuleAccessor, index: usize, partner: usize) {
    #[cfg(feature = "swap-diagnostics")]
    if HIDDEN_BY_SWAP[index][partner] != (*boma).battle_object_id {
        println!("[MGW-DIAG] suppress-camera entry={} partner={} id={:#x} status={:#x}",
            index, partner, (*boma).battle_object_id, StatusModule::status_kind(boma));
    }
    CameraModule::set_whole(boma, false);
    AreaModule::set_whole(boma, false);
    VisibilityModule::set_whole(boma, false);
    HitModule::set_whole(boma, HitStatus(*HIT_STATUS_OFF), 0);
    ShadowModule::set_draw_status(boma, false);
    ItemModule::set_have_item_visibility(boma, false, 0);
    ItemModule::set_attach_item_visibility(boma, false, 0xff);
    HIDDEN_BY_SWAP[index][partner] = (*boma).battle_object_id;
}

// Drive dormancy from the ACTIVE fighter: an inactive partner is not guaranteed
// to receive on_line(Main). Resolve a fresh ID/accessor instead of caching BOMA.
unsafe fn hide_inactive_partner(entry: *mut u8, index: usize, partner: usize) {
    let id = FighterEntry::get_fighter_id(entry as *mut smash::app::FighterEntry, partner as i32, false) as u32;
    if id == INVALID_FIGHTER_ID { return; }
    let boma = sv_battle_object::module_accessor(id);
    if boma.is_null()
        || WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID) != index as i32
        || !is_target_costume(WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR))
        || WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR) != *entry.add(0x41) as i32
    { return; }
    let expected_kind = if partner == 0 { FIGHTER_KIND_ELIGHT } else { FIGHTER_KIND_GAMEWATCH };
    if utility::get_kind(&mut *boma) != expected_kind { return; }
    hide_swap_fighter(boma, index, partner);
}

unsafe fn restore_swap_fighter(boma: *mut BattleObjectModuleAccessor, index: usize, partner: usize) {
    if HIDDEN_BY_SWAP[index][partner] != (*boma).battle_object_id { return; }
    HIDDEN_BY_SWAP[index][partner] = INVALID_FIGHTER_ID;
    CameraModule::set_whole(boma, true);
    AreaModule::set_whole(boma, true);
    VisibilityModule::set_whole(boma, true);
    ShadowModule::set_draw_status(boma, true);
    ItemModule::set_have_item_visibility(boma, true, 0);
    ItemModule::set_attach_item_visibility(boma, true, 0xff);
    // Repair only the OFF state we applied, once. Never replace native XLU
    // (e.g. dodge or respawn invulnerability) with NORMAL every gameplay frame.
    if HitModule::get_whole(boma, 0) == *HIT_STATUS_OFF {
        HitModule::set_whole(boma, HitStatus(*HIT_STATUS_NORMAL), 0);
    }
}

// Diagnostic telemetry for elight / eflame / gamewatch frame
unsafe extern "C" fn elight_frame(fighter: &mut L2CFighterCommon) {
    #[cfg(feature = "swap-diagnostics")]
    diagnostics::frame(fighter);
    let boma = fighter.module_accessor;
    let slot = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR);
    let status = StatusModule::status_kind(boma);
    let prev_status = StatusModule::prev_status_kind(boma, 0);
    let entry_id = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);

    if is_target_costume(slot) 
        && entry_id >= 0 
        && (entry_id as usize) < IS_PAIRED_ENTRY.len() 
        && IS_PAIRED_ENTRY[entry_id as usize]
    {
        let is_ready = smash::app::sv_information::is_ready_go();
        if is_ready {
            MATCH_WAS_READY[entry_id as usize] = true;
        } else if MATCH_WAS_READY[entry_id as usize] {
            MATCH_WAS_READY[entry_id as usize] = false;
            // Match has ended while controlling Mythra ("GAME!" appeared).
            // Force active sub-fighter cleanly to Game & Watch so the victory screen loads G&W!
            let entry = ENTRY_PTRS[entry_id as usize];
            if !entry.is_null() && is_target_pair(entry) {
                set_active_subfighter_gw(entry);
                println!(
                    "[Mythra-GW-Swap] Match ended on Mythra! Switched active subfighter to G&W (entry {})",
                    entry_id
                );
            }
        }
    }
    
    if StatusModule::is_changing(boma) {
        if status == *FIGHTER_STATUS_KIND_SPECIAL_LW
            || status == *FIGHTER_ELEMENT_STATUS_KIND_SPECIAL_LW_STANDBY
            || status == *FIGHTER_ELEMENT_STATUS_KIND_SPECIAL_LW_OUT 
        {
            println!(
                "[Mythra-GW-Swap][ELight] Entry {}: Slot {} entered status {:#X} (prev {:#X})",
                entry_id, slot, status, prev_status
            );
        }
    }

    if is_target_costume(slot) {
        // Corrin Up Air frame-38 cancel (FAF 39)
        if status == *FIGHTER_STATUS_KIND_ATTACK_AIR {
            let motion_kind = MotionModule::motion_kind(boma);
            if motion_kind == hash40("attack_air_hi") {
                let motion_frame = MotionModule::frame(boma);
                if motion_frame >= 38.0 {
                    CancelModule::enable_cancel(boma);
                }
            }
        }

        // Luigi Down Throw frame-41 cancel (FAF 42)
        if status == *FIGHTER_STATUS_KIND_THROW {
            let motion_kind = MotionModule::motion_kind(boma);
            if motion_kind == hash40("throw_lw") {
                let motion_frame = MotionModule::frame(boma);
                if motion_frame >= 41.0 {
                    CancelModule::enable_cancel(boma);
                }
            }
        }
    }

    if is_target_costume(slot) 
        && entry_id >= 0 
        && (entry_id as usize) < IS_PAIRED_ENTRY.len() 
        && IS_PAIRED_ENTRY[entry_id as usize] 
    {
        let entry = ENTRY_PTRS[entry_id as usize];
        if !entry.is_null() {
            let active_idx = *(entry.add(0x5918) as *const u8);

            if active_idx == 0 && FighterEntry::current_fighter_id(entry as *mut smash::app::FighterEntry) as u32 == (*boma).battle_object_id {
                // Mythra is the active sub-fighter
                // Damage synchronization
                if PREV_ACTIVE_IDX[entry_id as usize] != 0 {
                    PREV_ACTIVE_IDX[entry_id as usize] = 0;
                    let cur = DamageModule::damage(boma, 0);
                    let target = SHARED_DAMAGE[entry_id as usize];
                    if target > cur {
                        DamageModule::add_damage(boma, target - cur, 0);
                    }
                } else if status == *FIGHTER_STATUS_KIND_REBIRTH {
                    SHARED_DAMAGE[entry_id as usize] = 0.0;
                } else {
                    SHARED_DAMAGE[entry_id as usize] = DamageModule::damage(boma, 0);
                }

                // The console log shows dormant fighters cannot be resolved
                // through the usual lookup. Disable the outgoing camera while
                // Mythra's own accessor is still valid, before native capture.
                if status == *FIGHTER_ELEMENT_STATUS_KIND_SPECIAL_LW_STANDBY {
                    hide_swap_fighter(boma, entry_id as usize, 0);
                    SWAP_CAMERA_PENDING[entry_id as usize] = true;
                }
                hide_inactive_partner(entry, entry_id as usize, 1);
                if !HOLDING_SWAP_TO_MYTHRA[entry_id as usize]
                    && status != *FIGHTER_STATUS_KIND_SPECIAL_LW
                    && status != *FIGHTER_ELEMENT_STATUS_KIND_SPECIAL_LW_STANDBY
                {
                    restore_swap_fighter(boma, entry_id as usize, 0);
                }

                // Cancel a pending return across stock/match lifecycle changes.
                if status == *FIGHTER_STATUS_KIND_DEAD || status == *FIGHTER_STATUS_KIND_REBIRTH
                    || status == *FIGHTER_STATUS_KIND_ENTRY
                {
                    HOLDING_SWAP_TO_MYTHRA[entry_id as usize] = false;
                    SWAP_REQUESTED[entry_id as usize] = false;
                    SWAP_CAMERA_PENDING[entry_id as usize] = false;
                }
                // Native activation calls this frame callback before restoring
                // Element's old pose. swap_handoff applies our snapshot later.
            } else if active_idx == 1 {
                hide_swap_fighter(boma, entry_id as usize, 0);
            }
        }
    }
}

unsafe extern "C" fn eflame_frame(fighter: &mut L2CFighterCommon) {
    let boma = fighter.module_accessor;
    let slot = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR);
    let status = StatusModule::status_kind(boma);
    let prev_status = StatusModule::prev_status_kind(boma, 0);
    
    if StatusModule::is_changing(boma) {
        if status == *FIGHTER_STATUS_KIND_SPECIAL_LW
            || status == *FIGHTER_ELEMENT_STATUS_KIND_SPECIAL_LW_STANDBY
            || status == *FIGHTER_ELEMENT_STATUS_KIND_SPECIAL_LW_OUT 
        {
            let entry_id = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
            println!(
                "[Mythra-GW-Swap][EFlame] Entry {}: Slot {} entered status {:#X} (prev {:#X})",
                entry_id, slot, status, prev_status
            );
        }
    }
}

pub const GAMEWATCH_STATUS_KIND_SPECIAL_LW_WAIT_START: i32 = 0x1E3;

// Monkey Flip capture observation state. Per entry id, so a second G&W on the
// stage cannot corrupt the reading.
#[cfg(feature = "swap-diagnostics")]
static mut MFLIP_OBS_STATUS: [i32; 8] = [-1; 8];
#[cfg(feature = "swap-diagnostics")]
static mut MFLIP_OBS_CATCH: [bool; 8] = [false; 8];
#[cfg(feature = "swap-diagnostics")]
static mut MFLIP_OBS_WATCH: [i32; 8] = [0; 8];

unsafe extern "C" fn gamewatch_frame(fighter: &mut L2CFighterCommon) {
    #[cfg(feature = "swap-diagnostics")]
    diagnostics::frame(fighter);
    let boma = fighter.module_accessor;
    let slot = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR);
    let status = StatusModule::status_kind(boma);
    let prev_status = StatusModule::prev_status_kind(boma, 0);
    let entry_id = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);

    // Monkey Flip capture observation.
    //
    // This runs every frame for every gamewatch fighter regardless of which
    // status it holds, and that is the entire point. If the engine moves c06/c07 out
    // of the Monkey Flip status block, our own status main_loop stops running and
    // structurally cannot report where we went -- which is why the previous
    // attempt produced no signal. This callback keeps running either way.
    //
    // The script-side claim on the capture is disabled in monkey_flip_status.rs
    // for this build, so anything logged here is the engine's own behaviour.
    //
    // Monkey Flip's status ids are 0x210..=0x21A; they are still hardcoded here
    // rather than imported because the consts are private to monkey_flip_status.
    #[cfg(feature = "swap-diagnostics")]
    if is_target_costume(slot) && entry_id >= 0 && entry_id < 8 {
        let idx = entry_id as usize;
        let mflip_ours = status >= 0x210 && status <= 0x21A;
        if mflip_ours {
            MFLIP_OBS_WATCH[idx] = 60;
        } else if MFLIP_OBS_WATCH[idx] > 0 {
            MFLIP_OBS_WATCH[idx] -= 1;
        } else {
            MFLIP_OBS_STATUS[idx] = status;
            MFLIP_OBS_CATCH[idx] = false;
        }
        if mflip_ours || MFLIP_OBS_WATCH[idx] > 0 {
            let catch = CatchModule::is_catch(boma);
            if status != MFLIP_OBS_STATUS[idx] || catch != MFLIP_OBS_CATCH[idx] {
                MFLIP_OBS_STATUS[idx] = status;
                MFLIP_OBS_CATCH[idx] = catch;
                let link = LinkModule::get_node_object_id(boma, *LINK_NO_CAPTURE) as u32;
                println!(
                    "[MGW-MFLIP] OBS entry={} status={} ({:#x}) prev={:#x} ours={} situation={} catch={} link={:#x} motion={:#x} frame={:.2}",
                    entry_id, status, status, prev_status, mflip_ours,
                    StatusModule::situation_kind(boma), catch, link,
                    MotionModule::motion_kind(boma), MotionModule::frame(boma)
                );
            }
        }
    }

    if is_target_costume(slot) {
        let fair_active = status == *FIGHTER_STATUS_KIND_ATTACK_AIR
            && MotionModule::motion_kind(boma) == hash40("attack_air_f");
        let sword_visibility = hash40(if fair_active { "no_null" } else { "null" });
        VisibilityModule::set_status_default_int64(boma, hash40("SwordM"), sword_visibility);
        VisibilityModule::set_int64(
            boma,
            hash40("SwordM"),
            sword_visibility,
        );
    }
    
    if StatusModule::is_changing(boma) {
        println!(
            "[Mythra-GW-Swap][G&W] Entry {}: Slot {} entered status {:#X} (prev {:#X})",
            entry_id, slot, status, prev_status
        );
    }

    // Check for Down-Special (0x1DF / FIGHTER_STATUS_KIND_SPECIAL_LW or 0x1E3 / SPECIAL_LW_WAIT_START) on paired c06/c07 Game & Watch
    if is_target_costume(slot) 
        && entry_id >= 0 
        && (entry_id as usize) < IS_PAIRED_ENTRY.len() 
        && IS_PAIRED_ENTRY[entry_id as usize] 
    {
        let is_ready = smash::app::sv_information::is_ready_go();
        if is_ready {
            MATCH_WAS_READY[entry_id as usize] = true;
        }

        let entry = ENTRY_PTRS[entry_id as usize];
        if !entry.is_null() {
            let active_idx = *(entry.add(0x5918) as *const u8);

            if active_idx == 1 && FighterEntry::current_fighter_id(entry as *mut smash::app::FighterEntry) as u32 == (*boma).battle_object_id {
                // Game & Watch is currently the active fighter on stage
                if status == *FIGHTER_STATUS_KIND_DEAD || status == *FIGHTER_STATUS_KIND_REBIRTH
                    || status == *FIGHTER_STATUS_KIND_ENTRY
                {
                    HOLDING_SWAP_TO_MYTHRA[entry_id as usize] = false;
                    SWAP_REQUESTED[entry_id as usize] = false;
                    SWAP_CAMERA_PENDING[entry_id as usize] = false;
                }
                // Damage synchronization
                if PREV_ACTIVE_IDX[entry_id as usize] != 1 {
                    PREV_ACTIVE_IDX[entry_id as usize] = 1;
                    let cur = DamageModule::damage(boma, 0);
                    let target = SHARED_DAMAGE[entry_id as usize];
                    if target > cur {
                        DamageModule::add_damage(boma, target - cur, 0);
                    }
                } else if status == *FIGHTER_STATUS_KIND_REBIRTH {
                    SHARED_DAMAGE[entry_id as usize] = 0.0;
                } else {
                    SHARED_DAMAGE[entry_id as usize] = DamageModule::damage(boma, 0);
                }

                hide_inactive_partner(entry, entry_id as usize, 0);
                let pos = *PostureModule::pos(boma);
                let lr = PostureModule::lr(boma);
                let situation = StatusModule::situation_kind(boma);

                if !SWAP_REQUESTED[entry_id as usize]
                    && status != *FIGHTER_STATUS_KIND_SPECIAL_LW
                    && status != GAMEWATCH_STATUS_KIND_SPECIAL_LW_WAIT_START
                {
                    restore_swap_fighter(boma, entry_id as usize, 1);
                }

                // Shulk Fair cancel and landing lag on G&W c06/c07
                let motion = MotionModule::motion_kind(boma);
                if motion == hash40("attack_air_f") {
                    if MotionModule::frame(boma) >= 42.0 {
                        CancelModule::enable_cancel(boma);
                    }
                } else if status == *FIGHTER_STATUS_KIND_LANDING_ATTACK_AIR && motion == hash40("landing_air_f") {
                    MotionModule::set_rate(boma, 2.4);
                }

                if (status == *FIGHTER_STATUS_KIND_SPECIAL_LW || status == GAMEWATCH_STATUS_KIND_SPECIAL_LW_WAIT_START)
                    && !SWAP_REQUESTED[entry_id as usize]
                {
                    SWAP_REQUESTED[entry_id as usize] = true;
                    HOLDING_SWAP_TO_MYTHRA[entry_id as usize] = true;
                    SWAP_CAMERA_PENDING[entry_id as usize] = true;
                    SAVED_POS_X[entry_id as usize] = pos.x;
                    SAVED_POS_Y[entry_id as usize] = pos.y;
                    SAVED_POS_Z[entry_id as usize] = pos.z;
                    SAVED_LR[entry_id as usize] = lr;
                    SAVED_SITUATION[entry_id as usize] = situation;
                    println!(
                        "[Mythra-GW-Swap][G&W] Down-Special on c06/c07 detected on entry {}! Triggering swap back to Mythra...",
                        entry_id
                    );

                    // Update entry's native position fields
                    *(entry.add(0x445c) as *mut f32) = pos.x;
                    *(entry.add(0x4460) as *mut f32) = pos.y;
                    *(entry.add(0x4464) as *mut f32) = pos.z;
                    *(entry.add(0x41f0) as *mut f32) = pos.x;
                    *(entry.add(0x41f0 + 4) as *mut f32) = pos.y;
                    *(entry.add(0x41f0 + 8) as *mut f32) = pos.z;
                    *(entry.add(0x41f0 + 0x10) as *mut f32) = lr;
                    *(entry.add(0x41f0 + 0x2b0) as *mut i32) = situation;

                    // Target index 0 = Mythra (entry->kind[0] = 91)
                    *(entry.add(0x591a) as *mut u8) = 0;
                    *(entry.add(0x5919) as *mut u8) = 0;
                    // Set sub-fighter switch state to 6 so native coordinator (0x6581f0) executes the swap on next frame
                    *(entry.add(0x5920) as *mut u8) = 6;

                    // Hide Game & Watch immediately while the swap executes.
                    hide_swap_fighter(boma, entry_id as usize, 1);

                    println!(
                        "[Mythra-GW-Swap][G&W] Entry {} subfighter switch to Mythra queued at ({:.2}, {:.2}, {:.2}) facing {:.1}!",
                        entry_id, pos.x, pos.y, pos.z, lr
                    );
                }
            } else if active_idx == 0 {
                hide_swap_fighter(boma, entry_id as usize, 1);
            }
        }
    }
}

#[skyline::main(name = "mythra_gamewatch_swap")]
pub fn main() {
    #[cfg(feature = "swap-diagnostics")]
    diagnostics::install();
    swap_handoff::install();
    println!("[Mythra-GW-Swap] Partner Substitution Plugin v0.8.6 (Bidirectional Mythra <-> G&W Swap) Loaded!");
    println!("[MGW-SLOTS] build 2026-09-26.c06c07 costumes={:?}", TARGET_COSTUMES);
    
    // Fix Smash Ultimate engine bug at 0x35c23a4 (null-dereference when model is not cached):
    // Replace `mov x8, xzr` (0xaa1f03e8) with `b #0x35c2464` (0x14000030).
    // This allows 0x35c22e0 to cleanly return NULL instead of crashing.
    let patch_res = skyline::patching::Patch::in_text(0x35c23a4).data(0x14000030u32);
    if let Err(e) = patch_res {
        println!("[Mythra-GW-Swap] Warning: Failed to apply engine model lookup patch: {:?}", e);
    } else {
        println!("[Mythra-GW-Swap] Successfully applied engine model cache fallback patch at 0x35c23a4!");
    }

    skyline::install_hook!(preload_fighter_resources_hook);
    skyline::install_hook!(fighter_entry_init_hook);
    skyline::install_hook!(subfighter_construct_table_select_hook);
    skyline::install_hook!(subfighter_ai_init_table_select_hook);
    skyline::install_hook!(subfighter_active_select_table_hook);
    skyline::install_hook!(subfighter_destroy_table_select_hook);
    skyline::install_hook!(match_end_pre_teardown_hook);
    skyline::install_hook!(fighter_match_teardown_hook);
    skyline::install_hook!(sound_id_null_guard_656fdc);
    skyline::install_hook!(sound_id_null_guard_656e80);
    skyline::install_hook!(sound_id_null_guard_656470);
    skyline::install_hook!(sound_id_null_guard_655fc8);
    
    attack_air_hi::install();
    throw_lw::install();
    monkey_flip::install();
    hero_spin3::install();
    attack_air_f::install();

    Agent::new("elight")
        .on_line(Main, elight_frame)
        .install();
        
    Agent::new("eflame")
        .on_line(Main, eflame_frame)
        .install();

    Agent::new("gamewatch")
        .on_line(Main, gamewatch_frame)
        .install();
}

/// Right before looping over fighters in match teardown (0x1492a3c):
/// x21 contains the global FighterManager pointer (*0x52b84f8).
/// Ensure any target pair entries have active subfighter cleanly set to Game & Watch (1)
/// so that 0x658af0 / 0x64f820 naturally initializes Game & Watch as active!
#[skyline::hook(offset = 0x1492a3c, inline)]
unsafe fn match_end_pre_teardown_hook(ctx: &mut skyline::hooks::InlineCtx) {
    let fighter_manager = ctx.registers[21].x() as *const *const *mut u8;
    if !fighter_manager.is_null() {
        let entries_table = *fighter_manager;
        if !entries_table.is_null() {
            for slot in 0..8 {
                let entry = *entries_table.add(4 + slot);
                if !entry.is_null() && is_target_pair(entry) {
                    set_active_subfighter_gw(entry);
                    println!(
                        "[Mythra-GW-Swap] 0x1492a3c: Match end! Ensured active subfighter is G&W (slot {})",
                        slot
                    );
                }
            }
        }
    }
}

/// At match teardown (0x65a760), Aegis (kinds 90/91) normally branches to 0x65a848 to load
/// victory cutscene props (`windummy`/`winsword`) onto the inactive partner.
/// For our custom Mythra <-> G&W pair on c06/c07, G&W does not have Aegis victory props.
/// By setting w8 = 99 and w9 = 99 for our target pair, the game skips 0x65a848 and branches
/// directly to 0x65ab34 (standard single-fighter match teardown), completely preserving
/// vanilla behavior for slots c00-c05.
#[skyline::hook(offset = 0x65a760, inline)]
unsafe fn fighter_match_teardown_hook(ctx: &mut skyline::hooks::InlineCtx) {
    let entry = ctx.registers[19].x() as *mut u8;
    if is_target_pair(entry) {
        ctx.registers[8].set_x(99);
        ctx.registers[9].set_x(99);

        // Always force active subfighter to Game & Watch (index 1) for the victory screen!
        set_active_subfighter_gw(entry);
    }
}
