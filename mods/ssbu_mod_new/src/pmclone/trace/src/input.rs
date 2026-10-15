//! Controller hook: records and replays the final mapped inputs of one player.
//!
//! Hook point: the game's "final input mapping" function, the same one the
//! UltimateTrainingModpack hooks for its input recording (`OFFSET_FIM`). It is
//! located at runtime by byte signature rather than a hard-coded address; on
//! 13.0.4 the signature was verified to occur exactly once, at main+0x1750f70
//! (checked against reference/dumps/images/main.bin on 2026-09-28).
use core::sync::atomic::{AtomicUsize, Ordering};

use crate::session;

/// First 8 instructions of the input mapping function (UltimateTrainingModpack
/// `NEEDLE_FIM`, src/common/offsets.rs).
const NEEDLE_FIM: [u8; 32] = [
    0xff, 0x03, 0x02, 0xd1, 0xf7, 0x23, 0x00, 0xf9, 0xf6, 0x57, 0x05, 0xa9, 0xf4, 0x4f, 0x06,
    0xa9, 0xfd, 0x7b, 0x07, 0xa9, 0xfd, 0xc3, 0x01, 0x91, 0x3f, 0x04, 0x00, 0x31, 0xe0, 0x77,
    0x00, 0x54,
];
/// Where the needle sits in the 13.0.4 executable. Only used for the log line.
const EXPECTED_13_0_4: usize = 0x1750f70;

static FIM_OFFSET: AtomicUsize = AtomicUsize::new(0);

/// Final per-player input for one frame (UltimateTrainingModpack `MappedInputs`).
#[repr(C)]
#[derive(Clone, Copy, Default, PartialEq, Eq, Debug)]
pub struct MappedInputs {
    pub buttons: u32,
    pub lstick_x: i8,
    pub lstick_y: i8,
    pub rstick_x: i8,
    pub rstick_y: i8,
}

#[skyline::hook(offset = FIM_OFFSET.load(Ordering::Relaxed))]
unsafe fn final_input_mapping(
    mappings: *mut u8,
    player_idx: i32,
    out: *mut MappedInputs,
    controller_struct: *mut u8,
    arg: bool,
) {
    call_original!(mappings, player_idx, out, controller_struct, arg);
    if !smash::app::smashball::is_training_mode() {
        session::leave_training();
        return;
    }
    if out.is_null() {
        return;
    }
    session::on_input(player_idx, &mut *out);
}

/// Returns the offset of `needle` in main's text if it occurs exactly once.
unsafe fn find_unique(needle: &[u8]) -> Option<usize> {
    let start = skyline::hooks::getRegionAddress(skyline::hooks::Region::Text) as *const u8;
    let end = skyline::hooks::getRegionAddress(skyline::hooks::Region::Rodata) as *const u8;
    let text = core::slice::from_raw_parts(start, end.offset_from(start) as usize);
    let mut found = None;
    // Instructions are 4-byte aligned, so only aligned positions are candidates.
    let mut i = 0;
    while i + needle.len() <= text.len() {
        if text[i..i + needle.len()] == *needle {
            if found.is_some() {
                return None;
            }
            found = Some(i);
        }
        i += 4;
    }
    found
}

pub fn install() {
    match unsafe { find_unique(&NEEDLE_FIM) } {
        Some(offset) if offset == EXPECTED_13_0_4 => {
            FIM_OFFSET.store(offset, Ordering::Relaxed);
            session::boot_log(&format!(
                "input hook: final input mapping at main+{:#x} (13.0.4 expects {:#x}{})",
                offset,
                EXPECTED_13_0_4,
                if offset == EXPECTED_13_0_4 { ", match" } else { ", DIFFERENT GAME BUILD?" }
            ));
            skyline::install_hook!(final_input_mapping);
        }
        _ => session::boot_log(
            "input hook: signature not found exactly once; recording/playback DISABLED",
        ),
    }
}
