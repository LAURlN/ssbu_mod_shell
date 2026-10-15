//! Repair the return only AFTER native activation and character restoration.
//! v0.8.5 console logs prove on_line(Main) runs inside that native sequence.
use super::*;

unsafe fn paired_index(entry: *mut u8) -> Option<usize> {
    if entry.is_null() { return None; }
    (0..8).find(|&i| ENTRY_PTRS[i] == entry && IS_PAIRED_ENTRY[i] && is_target_pair(entry))
}

// x19 is FighterEntry, immediately after 0x649980 captures the outgoing fighter.
#[skyline::hook(offset = 0x658328, inline)]
unsafe fn after_capture(ctx: &skyline::hooks::InlineCtx) {
    let entry = ctx.registers[19].x() as *mut u8;
    if let Some(index) = paired_index(entry) {
        if HOLDING_SWAP_TO_MYTHRA[index] && *entry.add(0x5918) == 1 && *entry.add(0x5919) == 0 {
            // Prefer the final outgoing pose over the earlier down-B frame.
            // Keep our own copy: the Element restore overwrites this buffer.
            let saved = entry.add(0x41f0);
            SAVED_POS_X[index] = *(saved as *const f32);
            SAVED_POS_Y[index] = *(saved.add(4) as *const f32);
            SAVED_POS_Z[index] = *(saved.add(8) as *const f32);
            SAVED_LR[index] = *(saved.add(0x10) as *const f32);
            SAVED_SITUATION[index] = *(saved.add(0x2b0) as *const i32);
        }
    }
    #[cfg(feature = "swap-diagnostics")]
    diagnostics::snapshot(entry, "after-native-capture", true);
}

// x19 is FighterEntry, immediately after 0x64aea0 and its character callback.
// This runs after the early WAIT callback and the SPECIAL_LW_OUT initialization
// observed in switch-v0.8.5.log. No frame callback may consume the saved pose.
#[skyline::hook(offset = 0x656720, inline)]
unsafe fn after_restore(ctx: &skyline::hooks::InlineCtx) {
    let entry = ctx.registers[19].x() as *mut u8;
    #[cfg(feature = "swap-diagnostics")]
    diagnostics::snapshot(entry, "after-native-restore", true);
    let index = match paired_index(entry) { Some(i) => i, None => return };
    let partner = *entry.add(0x5918) as usize;
    if partner > 1 || (!SWAP_CAMERA_PENDING[index] && !HOLDING_SWAP_TO_MYTHRA[index]) { return; }
    let id = FighterEntry::get_fighter_id(entry as *mut smash::app::FighterEntry, partner as i32, false) as u32;
    if id == INVALID_FIGHTER_ID { return; }
    let boma = sv_battle_object::module_accessor(id);
    if boma.is_null()
        || utility::get_kind(&mut *boma) != if partner == 0 { FIGHTER_KIND_ELIGHT } else { FIGHTER_KIND_GAMEWATCH }
        || WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID) != index as i32
        || !is_target_costume(WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR))
        || WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_COLOR) != *entry.add(0x41) as i32
    { return; }

    // The incoming object may not have existed during the previous active frame,
    // so HIDDEN_BY_SWAP alone cannot restore its camera. End the camera handoff
    // once for either direction, after native state inheritance has finished.
    if SWAP_CAMERA_PENDING[index] {
        CameraModule::set_whole(boma, true);
        SWAP_CAMERA_PENDING[index] = false;
        #[cfg(feature = "swap-diagnostics")]
        println!("[MGW-DIAG] restore-camera entry={} partner={} id={:#x} after-native-restore", index, partner, id);
    }
    if !HOLDING_SWAP_TO_MYTHRA[index] || partner != 0 { return; }

    let pos = Vector3f { x: SAVED_POS_X[index], y: SAVED_POS_Y[index], z: SAVED_POS_Z[index] };
    let lr = SAVED_LR[index];
    let situation = SAVED_SITUATION[index];
    if !pos.x.is_finite() || !pos.y.is_finite() || !pos.z.is_finite() || !lr.is_finite()
        || (situation != *SITUATION_KIND_GROUND && situation != *SITUATION_KIND_AIR)
    {
        println!("[Mythra-GW-Swap] Entry {} rejected invalid native return pose", index);
        HOLDING_SWAP_TO_MYTHRA[index] = false;
        SWAP_REQUESTED[index] = false;
        return;
    }

    // init_pos updates position history too; set_pos alone leaves the old
    // previous position for interpolation/collision after a long-distance swap.
    StatusModule::set_situation_kind(boma, SituationKind(situation), false);
    GroundModule::correct(boma, GroundCorrectKind(if situation == *SITUATION_KIND_GROUND {
        *GROUND_CORRECT_KIND_GROUND
    } else {
        *GROUND_CORRECT_KIND_AIR
    }));
    PostureModule::init_pos(boma, &pos, false, false);
    PostureModule::set_lr(boma, lr);
    PostureModule::update_rot_y_lr(boma);

    // Keep the documented native handoff fields consistent with the repair.
    let saved = entry.add(0x41f0);
    *(saved as *mut f32) = pos.x;
    *(saved.add(4) as *mut f32) = pos.y;
    *(saved.add(8) as *mut f32) = pos.z;
    *(saved.add(0x10) as *mut f32) = lr;
    *(saved.add(0x2b0) as *mut i32) = situation;

    restore_swap_fighter(boma, index, 0);
    HOLDING_SWAP_TO_MYTHRA[index] = false;
    SWAP_REQUESTED[index] = false;
    println!("[Mythra-GW-Swap] Entry {} return pose applied AFTER native restore at ({:.3}, {:.3}, {:.3}) lr={:.1}",
        index, pos.x, pos.y, pos.z, lr);
    #[cfg(feature = "swap-diagnostics")]
    diagnostics::snapshot(entry, "after-return-repair", true);
}

pub fn install() {
    unsafe {
        let text = skyline::hooks::getRegionAddress(skyline::hooks::Region::Text) as *const u8;
        // Validate both call instructions and both hook sites against the dump.
        let signatures = [(0x658324, 0x97ffc597u32), (0x658328, 0x394002a8),
                          (0x65671c, 0x97ffd1e1), (0x656720, 0x394092c8)];
        for (offset, expected) in signatures {
            if *(text.add(offset) as *const u32) != expected {
                println!("[Mythra-GW-Swap] Native return repair disabled: instruction mismatch at {:#x}", offset);
                return;
            }
        }
        skyline::install_hooks!(after_capture, after_restore);
        println!("[Mythra-GW-Swap] Native handoff hooks installed (v0.8.6)");
    }
}
