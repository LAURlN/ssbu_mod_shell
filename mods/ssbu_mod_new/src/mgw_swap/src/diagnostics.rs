//! Read-only swap telemetry; enabled with the swap-diagnostics feature.
use super::*;

static mut LAST_ACTIVE: [u32; 8] = [0x50000000; 8];
static mut FRAMES_LEFT: [u8; 8] = [0; 8];
static mut LAST_DOWN_B: [bool; 8] = [false; 8];

pub unsafe fn reset(index: usize) {
    LAST_ACTIVE[index] = 0x50000000;
    FRAMES_LEFT[index] = 0;
    LAST_DOWN_B[index] = false;
}

unsafe fn tracked_entry(entry: *mut u8) -> Option<usize> {
    if entry.is_null() { return None; }
    // Match a live registration before interpreting an entry passed by a hook.
    for index in 0..8 {
        if ENTRY_PTRS[index] == entry && IS_PAIRED_ENTRY[index] && is_target_pair(entry) {
            return Some(index);
        }
    }
    None
}

pub(super) unsafe fn snapshot(entry: *mut u8, phase: &str, include_handoff: bool) {
    let index = match tracked_entry(entry) { Some(i) => i, None => return };
    println!("[MGW-DIAG] {} entry={} current={} next={} requested={} state={} flags={:#x} mode={} aux={}/{}/{}",
        phase, index, *entry.add(0x5918), *entry.add(0x5919), *entry.add(0x591a),
        *entry.add(0x5920), *entry.add(0x591f), *entry.add(0x591b),
        *entry.add(0x5931), *entry.add(0x5932), *entry.add(0x5934));
    if include_handoff {
        // Verified in supplied main: 0x6499fc..0x649a14 saves PostureModule::pos
        // at handoff+0; 0x6499e8 saves lr at +0x10, 0x649a40 situation at +0x2b0.
        let saved = entry.add(0x41f0);
        println!("[MGW-DIAG] handoff pos=({:.3},{:.3},{:.3}) lr={:.1} situation={}",
            *(saved as *const f32), *(saved.add(4) as *const f32),
            *(saved.add(8) as *const f32), *(saved.add(0x10) as *const f32),
            *(saved.add(0x2b0) as *const i32));
    }
    for partner in 0..2 {
        let id = FighterEntry::get_fighter_id(entry as *mut smash::app::FighterEntry, partner, false) as u32;
        if id == 0x50000000 {
            println!("[MGW-DIAG] partner={} unavailable: invalid fighter ID", partner);
            continue;
        }
        let boma = sv_battle_object::module_accessor(id);
        if boma.is_null() {
            println!("[MGW-DIAG] partner={} id={:#x} unavailable: null accessor", partner, id);
            continue;
        }
        let actual_entry = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
        if actual_entry != index as i32 {
            println!("[MGW-DIAG] partner={} id={:#x} unavailable: entry mismatch {}", partner, id, actual_entry);
            continue;
        }
        let kind = utility::get_kind(&mut *boma);
        if kind != FIGHTER_KIND_ELIGHT && kind != FIGHTER_KIND_GAMEWATCH {
            println!("[MGW-DIAG] partner={} id={:#x} unavailable: kind {}", partner, id, kind);
            continue;
        }
        let pos = &*PostureModule::pos(boma);
        println!("[MGW-DIAG] partner={} id={:#x} kind={} status={:#x} prev={:#x} situation={} pos=({:.3},{:.3},{:.3}) lr={:.1} visible={} camera_type={}",
            partner, id, kind, StatusModule::status_kind(boma), StatusModule::prev_status_kind(boma, 0),
            StatusModule::situation_kind(boma), pos.x, pos.y, pos.z,
            PostureModule::lr(boma), VisibilityModule::is_visible(boma), CameraModule::get_camera_type(boma));
    }
}

pub unsafe fn frame(fighter: &mut L2CFighterCommon) {
    let boma = fighter.module_accessor;
    let index = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
    if index < 0 || index >= 8 { return; }
    let index = index as usize;
    let entry = ENTRY_PTRS[index];
    if tracked_entry(entry).is_none() { return; }
    let id = FighterEntry::current_fighter_id(entry as *mut smash::app::FighterEntry) as u32;
    if id != (*boma).battle_object_id { return; }
    let status = StatusModule::status_kind(boma);
    let kind = utility::get_kind(&mut *boma);
    let down_b = status == *FIGHTER_STATUS_KIND_SPECIAL_LW
        || (kind == FIGHTER_KIND_GAMEWATCH && status == *FIGHTER_GAMEWATCH_STATUS_KIND_SPECIAL_LW_WAIT_START);
    if id != LAST_ACTIVE[index] || (down_b && !LAST_DOWN_B[index]) {
        snapshot(entry, if id != LAST_ACTIVE[index] { "active-changed" } else { "down-b" }, false);
        LAST_ACTIVE[index] = id;
        FRAMES_LEFT[index] = 16;
    } else if FRAMES_LEFT[index] > 0 {
        // At most five follow-up snapshots per swap; no permanent frame spam.
        let left = FRAMES_LEFT[index];
        if left == 16 || left == 15 || left == 13 || left == 9 || left == 1 {
            println!("[MGW-DIAG] follow-up frame={}", 17 - left);
            snapshot(entry, "follow-up", false);
        }
        FRAMES_LEFT[index] -= 1;
    }
    LAST_DOWN_B[index] = down_b;
}

pub fn install() {
    println!("[MGW-DIAG] v0.8.6: native handoff repair and pre-dormancy camera cleanup");
}
