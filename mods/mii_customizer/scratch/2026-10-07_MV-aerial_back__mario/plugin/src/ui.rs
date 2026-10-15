//! Pure part of the editor UI ("mod mode" on the native headgear list): addresses and
//! instruction words the hooks rely on, the synthetic list handles, the message-key struct,
//! the entry decision, the mode state and what a decided row means. No skyline items, no
//! heap, no locks, no panicking paths, so the same file is compiled into the host test
//! (`scratch/2026-10-06_P11-MENU/host_test.rs`). The pages of 0.5.0 are in `menu.rs`.
//!
//! Every address here is module-relative on 13.0.4 and is re-read from the image by
//! `evidence/P11-MENU/check_p11_menu.py`; the proofs are in `research/P11-MENU.md`
//! (0.4.0 part: `research/P10-UI-SLICE.md`).

use crate::list::List;
use crate::logic::Site;
use core::sync::atomic::{AtomicU32, AtomicU64, Ordering};

// ---------------------------------------------------------------------------
// Hook sites (patched) and probes (compared only)
// ---------------------------------------------------------------------------

const PROLOGUE_STP4: [u32; 4] = [0xa9bc_5ff8, 0xa901_57f6, 0xa902_4ff4, 0xa903_7bfd];

/// Edit-scene state 3, the dispatcher: reads the edit menu's exit value and pushes the
/// next state. `x0` = scene.
pub const SITE_DISPATCH: Site = Site { offset: 0x180_a030, words: PROLOGUE_STP4 };
/// Edit-scene state 5, the headgear sub-screen. `x0` = scene. The only code that writes
/// the headgear handle of the working record (0x180ac3c, 0x180ad20).
pub const SITE_STATE5: Site = Site { offset: 0x180_abd0, words: PROLOGUE_STP4 };
/// "This headgear handle has no entry in the item table": `x0` = table, `x1` = handle,
/// returns 0 for a listed item and 1 for an unlisted one.
pub const SITE_UNLISTED: Site = Site { offset: 0x328_b5d0, words: PROLOGUE_STP4 };
/// Message key of a headgear handle: `x0` = out struct, `x1` = registry, `x2` = handle.
pub const SITE_LABEL: Site =
    Site { offset: 0x328_8330, words: [0xd102_c3ff, 0xf900_33f9, 0xa907_5ff8, 0xa908_57f6] };
/// `sort_id_list` handler of the headgear list: `x0` = S, `w1` = mode.
pub const SITE_SORT: Site =
    Site { offset: 0x19c_d100, words: [0xd101_c3ff, 0xa903_5ff8, 0xa904_57f6, 0xa905_4ff4] };

/// Row filler of the headgear list: `x0` = S, `w1` = row, `x2` = row node. New in 0.5.0:
/// rows are greyed and get literal text here.
pub const SITE_ROWFILL: Site =
    Site { offset: 0x19c_cb20, words: [0xd103_03ff, 0xa907_67fa, 0xa908_5ff8, 0xa909_57f6] };

pub const UI_SITES: usize = 6;
pub const UI_SITE_LIST: [Site; UI_SITES] =
    [SITE_DISPATCH, SITE_STATE5, SITE_UNLISTED, SITE_LABEL, SITE_SORT, SITE_ROWFILL];
pub const UI_SITE_NAMES: [&str; UI_SITES] =
    ["ui_dispatch", "ui_state5", "ui_unlisted", "ui_label", "ui_sort", "ui_rowfill"];

/// Game functions the UI code calls (module-relative).
pub const FN_SET_ITEM_COUNT: usize = 0x378_30e0;
pub const FN_SET_SELECT: usize = 0x19c_fe00;
pub const FN_REG_CONST: usize = 0x337_50a0;
pub const FN_ALLOC: usize = 0x392_dce0;
pub const FN_FREE: usize = 0x392_e590;
/// Pane of a row node by name: `x0` = row node, `x1` = name, `x8` = out `{vtable, holder}`;
/// the holder is 0x20 bytes from the game allocator, `holder+0x10` = the text pane or 0.
pub const FN_FIND_PANE: usize = 0x377_6360;
/// Literal text of a text pane: `x0` = text pane, `x1` = UTF-8 C string (what Lua
/// `set_text_string` calls, 0x335a558).
pub const FN_SET_TEXT_UTF8: usize = 0x37a_22f0;
/// Pane holder: the text pane.
pub const HOLDER_TEXT: usize = 0x10;

/// Code the UI relies on without patching it: compared with the image before any UI hook
/// is installed, exactly like a hook site. One mismatch disables the whole UI.
pub const PROBES: usize = 48;
pub const PROBE_LIST: [Site; PROBES] = [
    // dispatcher: ldr w8,[x8,#0x128] ; tbnz w8,#31 ; ldr w9,[x19,#0x144] ; cmp w9,#0x11
    Site { offset: 0x180_a098, words: [0xb941_2908, 0x37f8_0988, 0xb941_4669, 0x7100_453f] },
    // state 5: ldr w8,[x0,#0x14c] ; mov x19,x0 ; cbz w8 ; ldr x8,[x19,#0x180]
    Site { offset: 0x180_abe4, words: [0xb941_4c08, 0xaa00_03f3, 0x3400_0368, 0xf940_c268] },
    // state 5: ldr x8,[x19,#0x180] ; ldr x8,[x8,#0x80] ; ldr w9,[x8,#0xe8] ; cbz w9
    Site { offset: 0x180_ac10, words: [0xf940_c268, 0xf940_4108, 0xb940_e909, 0x3400_0509] },
    // state 5 preview write: ldr x8,[x8,#0x140] ; adrp x9 ; str x8,[x9,#0xcb0] ; mov x0,x19
    Site { offset: 0x180_ac34, words: [0xf940_a108, 0x9001_d7e9, 0xf906_5928, 0xaa13_03e0] },
    // state 5 decide write: mov x0,x19 ; str x10,[x11,#0xcb0] ; bl 0x180cf10 ; ldr x8,[x19,#0x180]
    Site { offset: 0x180_ad1c, words: [0xaa13_03e0, 0xf906_596a, 0x9400_087b, 0xf940_c268] },
    // state 5 entry: ldr x1,[x9,#0xcb0] ; ldr x0,[x8,#0x80] ; bl 0x19cfe00 ; ldr x19,[x19,#0x180]
    Site { offset: 0x180_b058, words: [0xf946_5921, 0xf940_4100, 0x9407_1368, 0xf940_c273] },
    // scroller set-item-count, entry
    Site { offset: 0x378_30e0, words: [0xd101_03ff, 0xfd00_0be8, 0xf900_0ff5, 0xa902_4ff4] },
    // scroller set-item-count: mov w8,w1 ; str w1,[x19,#0x34] ; str w1,[x19,#0x288] ; b.lt
    Site { offset: 0x378_3110, words: [0x2a01_03e8, 0xb900_3661, 0xb902_8a61, 0x5400_00ab] },
    // set_select, entry
    Site { offset: 0x19c_fe00, words: [0xa9bd_57f6, 0xa901_4ff4, 0xa902_7bfd, 0x9100_83fd] },
    // set_select: ldp x10,x8,[x0,#0x128] ; mov x19,x0 ; stp x1,x1,[x0,#0x140] ; str x1,[x0,#0x150]
    Site { offset: 0x19c_fe10, words: [0xa952_a00a, 0xaa00_03f3, 0xa914_0401, 0xf900_a801] },
    // Lua constant registrar, entry
    Site { offset: 0x337_50a0, words: [0xd104_83ff, 0xf900_7bfc, 0xa910_4ff4, 0xa911_7bfd] },
    // allocator and free, entries
    Site { offset: 0x392_dce0, words: [0xd102_03ff, 0xa907_7bfd, 0x9101_c3fd, 0xf81f_83a0] },
    Site { offset: 0x392_e590, words: [0xd100_c3ff, 0xa902_7bfd, 0x9100_83fd, 0xf81f_83a0] },
    // sort handler mode test: cmp w1,#2 ; b.eq ; cmp w1,#1 ; b.eq  (then cbnz w1 -> return)
    Site { offset: 0x19c_d11c, words: [0x7100_083f, 0x5400_02a0, 0x7100_043f, 0x5400_0140] },
    // scroller frame function: ldr w8,[x0,#0x2a0] ; str w8,[x0,#0x2a4] ; add x8,x0,#0x2b4 ; mov w23,#-1
    Site { offset: 0x377_d2b8, words: [0xb942_a008, 0xb902_a408, 0x910a_d008, 0x1280_0017] },
    // ---- new in 0.5.0: page change through the state reader (M3) ----
    // reader: ldrsw x8,[x0,#0x144] ; cmp w8,#0x13 ; b.hs trap ; add x8,x0,x8,lsl #2
    Site { offset: 0x180_ce4c, words: [0xb981_4408, 0x7100_4d1f, 0x5400_0562, 0x8b08_0808] },
    // reader: ldr w8,[x8,#0xf8] ; ldr w9,[x0,#0x148] ; mov x19,x0 ; cmp w9,w8
    Site { offset: 0x180_ce5c, words: [0xb940_f908, 0xb941_4809, 0xaa00_03f3, 0x6b08_013f] },
    // reader, same state: ldrb w8,[x19,#0x154] ; cbz -> return ; ldp x8,x10,[x19,#0x18] ; and x9,x10,#1
    Site { offset: 0x180_cebc, words: [0x3945_5268, 0x3400_01a8, 0xa941_aa68, 0x9240_0149] },
    // reader: orr x11,x9,x8 ; cbz x11 -> 0x180ceec (no callback) ; ldr x11,[x19] ; add x0,x11,x10,asr #1
    Site { offset: 0x180_cecc, words: [0xaa08_012b, 0xb400_00eb, 0xf940_026b, 0x8b8a_0560] },
    // reader: str wzr,[x19,#0x14c] ; strb wzr,[x19,#0x154] ; ldp x29,x30 ; ldr x19 (epilogue)
    Site { offset: 0x180_ceec, words: [0xb901_4e7f, 0x3905_527f, 0xa941_7bfd, 0xf842_07f3] },
    // state 5 pop: ldr w8,[x19,#0x144] ; subs w8,w8,#1 ; b.lt ; str w8,[x19,#0x144]
    Site { offset: 0x180_adf4, words: [0xb941_4668, 0x7100_0508, 0x5400_176b, 0xb901_4668] },
    // frame update, after the handler: ldr w8,[x19,#0x14c] ; ldr w20,[x19,#0x148] ; add w8,w8,#1 ; str
    Site { offset: 0x180_eb28, words: [0xb941_4e68, 0xb941_4a74, 0x1100_0508, 0xb901_4e68] },
    // scene constructor: stp xzr,xzr,[x19,#0x18] ; str xzr,[x19,#0x10] ; str x8,[x19,#0x148] ; str w8,[x19,#0x150]
    Site { offset: 0x180_df10, words: [0xa901_fe7f, 0xf900_0a7f, 0xf900_a668, 0xb901_5268] },
    // ---- greyed rows (M2) ----
    // row filler: mov x1,x20 ; bl 0x328b5d0 ; tbz w0,#0 -> enabled ; ldrb w8,[x19,#0x169]
    Site { offset: 0x19c_cd80, words: [0xaa14_03e1, 0x9462_fa13, 0x3600_0060, 0x3945_a668] },
    // row filler, unavailable: ldr x19,[x23] ; cbz ; ldr x8,[x19] ; ldr x8,[x8,#0x1f8]
    Site { offset: 0x19c_ce2c, words: [0xf940_02f3, 0xb4ff_fe33, 0xf940_0268, 0xf940_fd08] },
    // row filler, unavailable: mov x0,x19 ; mov w1,wzr ; blr x8 ; ldr x8,[x19]
    Site { offset: 0x19c_ce3c, words: [0xaa13_03e0, 0x2a1f_03e1, 0xd63f_0100, 0xf940_0268] },
    // scroller decide: ldr x8,[x21] ; ldr x8,[x8,#0x200] ; mov x0,x21 ; blr x8
    Site { offset: 0x377_e278, words: [0xf940_02a8, 0xf941_0108, 0xaa15_03e0, 0xd63f_0100] },
    // scroller decide: tbz w0,#0 -> no decision ; ldr x8,[x21] ; ldr x8,[x8,#0x210] ; mov x0,x21
    Site { offset: 0x377_e288, words: [0x3600_05a0, 0xf940_02a8, 0xf941_0908, 0xaa15_03e0] },
    // scroller decide: tbz w0,#0 -> no decision ; ldr w8,[x19,#0x2a0] ; str w8,[x19,#0x2b0] ; b
    Site { offset: 0x377_e29c, words: [0x3600_0500, 0xb942_a268, 0xb902_b268, 0x17ff_fd71] },
    // scroller: ldr w8,[x19,#0x2b0] ; cmn w8,#1 ; b.eq ; ldr w24,[sp,#0x3c]
    Site { offset: 0x377_d648, words: [0xb942_b268, 0x3100_051f, 0x5400_00c0, 0xb940_3ff8] },
    // scroller: str w8,[x19,#0x2b4] ; fmov s8,wzr ; str w23,[x19,#0x2b0] ; b
    Site { offset: 0x377_d658, words: [0xb902_b668, 0x1e27_03e8, 0xb902_b277, 0x1400_0082] },
    // Lua get_decided_item: ldr x9,[x10] ; ldrsw x10,[x9,#0x2b4] ; b ; mov x10,xzr
    Site { offset: 0x336_30b0, words: [0xf940_0149, 0xb982_b52a, 0x1400_0003, 0xaa1f_03ea] },
    // button slot +0x1f8: ldrb w9,[x0,#0xc] ; mov w8,w1 ; and w1,w1,#1 ; strb w1,[x0,#0x1c2]
    Site { offset: 0x378_a6c0, words: [0x3940_3009, 0x2a01_03e8, 0x1200_0021, 0x3907_0801] },
    // button slot +0x200: ldrb w0,[x0,#0x1c2] ; ret
    Site { offset: 0x378_a6f0, words: [0x3947_0800, 0xd65f_03c0, 0x0000_0000, 0x0000_0000] },
    // cursor step (secondary slot +0x28): bl 0x328b5d0 ; tbz w0,#0 ; sub x8,x22,#0x128 ; ldrb w8,[x8,#0x169]
    Site { offset: 0x19c_d070, words: [0x9462_f958, 0x3600_00e0, 0xd104_a2c8, 0x3945_a508] },
    // cursor step (primary slot +0x40): bl 0x328b5d0 ; tbz w0,#0 ; ldrb w8,[x22,#0x169] ; cbz
    Site { offset: 0x19c_ceec, words: [0x9462_f9b9, 0x3600_0060, 0x3945_a6c8, 0x3400_00c8] },
    // ---- literal row text (M5) ----
    // row filler: add x8,sp,#8 ; mov x0,x22 ; bl 0x3776360 ; add x21,x21,#8   ("set_txt_val")
    Site { offset: 0x19c_cbf8, words: [0x9100_23e8, 0xaa16_03e0, 0x9476_a5d8, 0x9100_22b5] },
    // row filler: add x0,sp,#8 ; mov x1,x21 ; bl 0x3779b70 ; ldr x0,[sp,#0x10]
    Site { offset: 0x19c_cc08, words: [0x9100_23e0, 0xaa15_03e1, 0x9476_b3d8, 0xf940_0be0] },
    // row filler: stp x24,xzr,[sp,#8] ; cbz x0 ; bl 0x392e590 (free the holder) ; adrp
    Site { offset: 0x19c_cc20, words: [0xa900_fff8, 0xb400_0040, 0x947d_865a, 0xd001_4ce1] },
    // row filler: add x8,sp,#8 ; mov x0,x22 ; bl 0x3776360 ; add x0,sp,#8   ("set_txt_val_disable")
    Site { offset: 0x19c_cc34, words: [0x9100_23e8, 0xaa16_03e0, 0x9476_a5c9, 0x9100_23e0] },
    // find pane: stp x29,x30,[sp,#0x170] ; add x29,sp,#0x170 ; mov x20,x8 ; mov x8,#-0x30
    Site { offset: 0x377_6370, words: [0xa917_7bfd, 0x9105_c3fd, 0xaa08_03f4, 0x9280_05e8] },
    // find pane: str x8,[x20] ; bl 0x392dce0 ; mov x22,x0 ; cbnz x0
    Site { offset: 0x377_6458, words: [0xf900_0288, 0x9406_de21, 0xaa00_03f6, 0xb500_0260] },
    // find pane: str x22,[x20,#8] ; stp xzr,xzr,[x22,#0x10] ; stp xzr,xzr,[x22] ; ldr x8,[x19,#8]
    Site { offset: 0x377_64b0, words: [0xf900_0696, 0xa901_7edf, 0xa900_7edf, 0xf940_0668] },
    // find pane: bl 0x3772a30 ; str x0,[x22,#0x10] ; ldr x0,[x22] ; bl 0x3772b40
    Site { offset: 0x377_64f0, words: [0x97ff_f150, 0xf900_0ac0, 0xf940_02c0, 0x97ff_f191] },
    // set message: ldr x9,[x0,#8] ; ldr x9,[x9,#0x10] ; cbz x9 ; add x10,x29,#0x10
    Site { offset: 0x377_9ba8, words: [0xf940_0409, 0xf940_0929, 0xb400_0829, 0x9100_43aa] },
    // set UTF-8 text, entry
    Site { offset: 0x37a_22f0, words: [0xf81d_0ffc, 0xa901_4ff4, 0xa902_7bfd, 0x9100_83fd] },
    // set UTF-8 text: mov x1,sp ; mov w3,#1 ; mov x0,x19 ; bl 0x37a1cc0
    Site { offset: 0x37a_23d0, words: [0x9100_03e1, 0x3200_03e3, 0xaa13_03e0, 0x97ff_fe39] },
    // Lua set_text_string: ldr x8,[x21,#8] ; ldr x0,[x8,#0x10] ; cbz x0 ; bl 0x37a22f0
    Site { offset: 0x335_a54c, words: [0xf940_06a8, 0xf940_0900, 0xb400_0040, 0x9411_1f66] },
];

// ---------------------------------------------------------------------------
// Data layout (module-relative statics, object offsets)
// ---------------------------------------------------------------------------

/// Editor working record; its first u32 is the saved-fighter ID.
pub const WORK_RECORD: usize = 0x530_6b78;
/// Headgear handle of the working record (`WORK_RECORD + 0x138`).
pub const HAT_STATIC: usize = 0x530_6cb0;
/// Bytes of the working record that are compared between arm and exit.
pub const RECORD_SNAPSHOT: usize = 0x200;

/// Vtables used as object identity checks.
pub const VT_LIST_OBJECT: usize = 0x50a_6c00;
pub const VT_SUB_OBJECT: usize = 0x50a_6ae0;
pub const VT_SCROLLER: usize = 0x523_ca68;
/// `"SCROLLER_ITEM_NUM"` and `"i"` in the image's string data.
pub const STR_ITEM_NUM: usize = 0x42a_18e6;
pub const STR_INT: usize = 0x42b_1a84;

/// Scene (the 0x1e0-byte state object).
/// Pointer-to-member pair the state reader calls on a state change; zero in this scene.
pub const SCENE_CHANGE_CB: usize = 0x18;
/// State stack: 19 u32 slots, and the index of its top.
pub const SCENE_STACK: usize = 0xf8;
pub const SCENE_DEPTH: usize = 0x144;
pub const SCENE_STATE: usize = 0x148;
/// "Start the current state again" request byte of the state reader (0x180cebc).
pub const SCENE_RESTART: usize = 0x154;
pub const SCENE_FRAME: usize = 0x14c;
pub const SCENE_EDIT: usize = 0x178;
pub const SCENE_HAT: usize = 0x180;
/// Wrapper -> inner object.
pub const WRAP_INNER: usize = 0x80;
/// Edit-menu inner object.
pub const EDIT_EXIT_VALUE: usize = 0x128;
pub const EDIT_HAS_VALUE: usize = 0x130;
/// Headgear sub-object S.
pub const S_SCRIPT: usize = 0x40;
pub const S_STATE: usize = 0xe8;
pub const S_SCROLLER: usize = 0xf8;
pub const S_VEC_BEGIN: usize = 0x128;
pub const S_VEC_END: usize = 0x130;
pub const S_VEC_CAP: usize = 0x138;
pub const S_PREVIEW: usize = 0x140;
pub const S_DECIDED: usize = 0x148;
pub const S_SELECTED: usize = 0x150;
pub const S_BACKUP: usize = 0x158;
pub const S_PREVIEW_DIRTY: usize = 0x168;
pub const S_UNLISTED_FLAG: usize = 0x169;
/// Scroller.
pub const SCROLLER_COUNT: usize = 0x288;
/// Cursor row, and the copy of it the scroller's frame function makes ("selected row").
pub const SCROLLER_CURSOR: usize = 0x2a0;
pub const SCROLLER_SELECTED: usize = 0x2a4;

/// Largest native item count the plugin accepts before it swaps the list.
pub const NATIVE_COUNT_MAX: u64 = 4096;

pub const SORT_NUMBER: u8 = 0;
pub const SORT_NAME: u8 = 1;

// ---------------------------------------------------------------------------
// Synthetic list handles
// ---------------------------------------------------------------------------

/// Tag byte of a headgear handle.
pub const TAG: u64 = 0x5a << 56;
const TAG_MASK: u64 = 0xff << 56;
/// 40-bit hash of a synthetic handle without its row: length byte 0xfe (no hat name is 254
/// characters long; the game's own "nothing" sentinel uses 0xff with a zero checksum), then
/// "MC" and a 16-bit row.
const SYNTH_HASH: u64 = 0xfe_4d43_0000;
const SYNTH_MASK: u64 = 0xff_ffff_0000;
const ROW_MASK: u64 = 0xffff;
/// Bits 40..55 of a handle are an index hint the game checks before it uses it. A list
/// entry has hint 0; the copy kept in the "current" slots has hint 1, so that a decision
/// (the game copies the list entry) is told apart from "nothing decided" even on the same
/// row. Every comparison of two handles looks at the low 40 bits only.
const HINT_SHIFT: u32 = 40;
const HINT_MASK: u64 = 0xffff << HINT_SHIFT;
/// Row number that no list row has: "the Mii's preset is not in the list".
pub const NO_ROW: u32 = 0xffff;

/// The handle of list row `row`.
pub fn row_handle(row: u32) -> u64 {
    TAG | SYNTH_HASH | (row as u64 & ROW_MASK)
}

/// The handle kept in the current / selected slots for row `row`.
pub fn display_handle(row: u32) -> u64 {
    row_handle(row) | (1 << HINT_SHIFT)
}

/// Row of a synthetic handle of either kind, `None` for every other value.
pub fn synth_row(handle: u64) -> Option<u32> {
    if handle & TAG_MASK == TAG && handle & SYNTH_MASK == SYNTH_HASH {
        Some((handle & ROW_MASK) as u32)
    } else {
        None
    }
}

/// How the headgear state ended.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Outcome {
    Cancel,
    /// Row index, 0 = no preset.
    Decide(u32),
}

/// Reads the decided slot at the end of the screen: a list entry (hint 0) of a row below
/// `rows` is a decision, everything else (the display copy, a real handle, garbage) is a
/// cancel.
pub fn outcome(decided: u64, rows: u32) -> Outcome {
    match synth_row(decided) {
        Some(row) if decided & HINT_MASK == 0 && row < rows => Outcome::Decide(row),
        _ => Outcome::Cancel,
    }
}

/// What a finished screen asks of the store.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Action {
    /// Cancelled: nothing changes.
    Cancelled,
    /// A row was decided for a Mii that is not saved yet (ID 0): nothing changes.
    UnsavedMii,
    /// Row 0: take the preset of this ID away.
    Clear { id: u32 },
    /// Give this ID the preset with this index.
    Set { id: u32, preset: usize },
    /// A row without a list entry (cannot happen while `rows == list.len() + 1`).
    NoEntry,
}

pub fn action(outcome: Outcome, saved_id: u32, list: &List) -> Action {
    match outcome {
        Outcome::Cancel => Action::Cancelled,
        Outcome::Decide(_) if saved_id == 0 => Action::UnsavedMii,
        Outcome::Decide(0) => Action::Clear { id: saved_id },
        Outcome::Decide(row) => match list.preset(row as usize - 1) {
            Some(preset) => Action::Set { id: saved_id, preset },
            None => Action::NoEntry,
        },
    }
}

/// Rows of the list screen: "no preset" and one per list entry.
pub fn rows(list: &List) -> u32 {
    list.len() as u32 + 1
}

/// The row that carries the tick when the screen opens: 0 without a preset, the entry's row
/// for a listed preset, [`NO_ROW`] for a preset the list does not show.
pub fn current_row(preset: Option<usize>, list: &List) -> u32 {
    match preset {
        None => 0,
        Some(preset) => match list.find_preset(preset) {
            Some(index) => index as u32 + 1,
            None => NO_ROW,
        },
    }
}

// ---------------------------------------------------------------------------
// Message key struct
// ---------------------------------------------------------------------------

/// `{u32 hash, u32 length, char text[0x40]}`: what 0x3288330 fills through 0x3a4ca0 and
/// what the row filler passes on (it hands `out + 8`, the text, to the pane setter).
pub const LABEL_STRUCT: usize = 0x48;
pub const LABEL_TEXT: usize = 8;
pub const LABEL_TEXT_MAX: usize = 0x3f;
/// Shown for row 0. Text "None" (`ui/message/msg_name.msbt`), the label of the native
/// list's own "no headgear" row.
pub const NONE_LABEL: &str = "nam_mii_hat_none_m";
/// What the game itself shows for a handle without a name.
pub const UNKNOWN_LABEL: &str = "nam_mii_hat_unknown";

/// The game's hash of a key (0x3a4d58..0x3a4d7c): seed 0x811c9dc5, `h = (h * 0x89) ^ byte`.
pub fn label_hash(text: &[u8]) -> u32 {
    let mut hash = 0x811c_9dc5u32;
    for b in text {
        hash = hash.wrapping_mul(0x89) ^ (*b as u32);
    }
    hash
}

/// Fill a message key struct with `text` (cut at 63 bytes), NUL-terminated.
pub fn write_label(out: &mut [u8; LABEL_STRUCT], text: &[u8]) {
    let text = text.get(..text.len().min(LABEL_TEXT_MAX)).unwrap_or(&[]);
    for b in out.iter_mut() {
        *b = 0;
    }
    for (dst, src) in out.iter_mut().skip(LABEL_TEXT).zip(text.iter()) {
        *dst = *src;
    }
    let hash = label_hash(text).to_le_bytes();
    let len = (text.len() as u32).to_le_bytes();
    for (dst, src) in out.iter_mut().zip(hash.iter().chain(len.iter())) {
        *dst = *src;
    }
}

/// Label of list row `row`.
pub fn row_label(row: u32, list: &List) -> &[u8] {
    if row == 0 {
        return NONE_LABEL.as_bytes();
    }
    let label = list.label(row as usize - 1);
    if label.is_empty() {
        UNKNOWN_LABEL.as_bytes()
    } else {
        label
    }
}

// ---------------------------------------------------------------------------
// Entry decision
// ---------------------------------------------------------------------------

/// Exit value the modified edit-menu script publishes (benign without the plugin).
pub const EXIT_MOD: i32 = 7;
/// Exit value of the Headgear row.
pub const EXIT_HEADGEAR: i32 = 1;
/// nn::hid button bits.
pub const BUTTON_ZL: u64 = 1 << 8;
pub const BUTTON_ZR: u64 = 1 << 9;
/// nn::hid style bits, in the order of [`STYLES`].
pub const STYLES: usize = 6;
pub const STYLE_FULL_KEY: u32 = 1 << 0;
pub const STYLE_HANDHELD: u32 = 1 << 1;
pub const STYLE_JOY_DUAL: u32 = 1 << 2;
pub const STYLE_JOY_LEFT: u32 = 1 << 3;
pub const STYLE_JOY_RIGHT: u32 = 1 << 4;
pub const STYLE_GC: u32 = 1 << 5;
/// Npad IDs asked: players 1-8 and handheld.
pub const NPAD_IDS: [u32; 9] = [0, 1, 2, 3, 4, 5, 6, 7, 0x20];

/// `nn::hid` NpadButton Minus.
pub const BUTTON_MINUS: u64 = 1 << 11;

pub fn minus(buttons: u64) -> bool {
    buttons & BUTTON_MINUS != 0
}

pub fn zl_or_zr(buttons: u64) -> bool {
    buttons & (BUTTON_ZL | BUTTON_ZR) != 0
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
#[repr(u32)]
pub enum Entry {
    /// The script published 7.
    A = 1,
    /// The Headgear row with ZL or ZR held.
    B = 2,
}

impl Entry {
    pub fn name(self) -> &'static str {
        match self {
            Entry::A => "A",
            Entry::B => "B",
        }
    }
}

/// What the dispatcher hook does with the exit value it is about to let the game read.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Dispatch {
    /// Not ours: nothing is changed.
    Pass,
    /// Value 7: rewrite it to 1 and arm.
    ArmA,
    /// Value 1 with ZL/ZR: arm, the value stays.
    ArmB,
    /// Value 7 but the list cannot be shown: the value stays 7 (the game's state 11).
    RefuseA,
}

/// `ready`: all UI hooks are installed. `entries`: rows there are to show (list entries
/// plus menu entries). `held` is asked only for value 1 when a page can be shown.
pub fn dispatch(value: i32, ready: bool, entries: usize, held: impl FnOnce() -> bool) -> Dispatch {
    let usable = ready && entries != 0;
    if value == EXIT_MOD {
        if usable {
            Dispatch::ArmA
        } else {
            Dispatch::RefuseA
        }
    } else if value == EXIT_HEADGEAR && usable && held() {
        Dispatch::ArmB
    } else {
        Dispatch::Pass
    }
}

// ---------------------------------------------------------------------------
// Mode state
// ---------------------------------------------------------------------------

pub const PHASE_IDLE: u32 = 0;
/// The dispatcher armed; the headgear state has not started yet.
pub const PHASE_PENDING: u32 = 1;
/// The headgear list shows the character list.
pub const PHASE_ACTIVE: u32 = 2;

/// "No cursor hint" in [`Mode`].
pub const NO_HINT: u32 = u32::MAX;
/// Words of the "row can be decided" mask: 129 rows at most.
pub const AVAIL_WORDS: usize = 3;

/// What the plugin remembers during a visit of mod mode. A visit starts when the dispatcher
/// arms and spans every page until mod mode is left. Written on the UI thread only; the
/// predicates read by hooks that can run elsewhere ([`Mode::active_rows`],
/// [`Mode::is_active_sub`], [`Mode::row_available`]) are single atomic loads.
pub struct Mode {
    phase: AtomicU32,
    entry: AtomicU32,
    scene: AtomicU64,
    sub: AtomicU64,
    rows: AtomicU32,
    /// Page code (`menu::Page::code`) of the page that is open or about to open.
    page: AtomicU32,
    /// Cursor row wanted for the page about to open, [`NO_HINT`] for the page's default.
    hint: AtomicU32,
    /// 1 from the first opened page of a visit until the visit ends.
    visit: AtomicU32,
    /// Pages opened in this visit after the first one.
    changes: AtomicU32,
    /// State-stack depth while the open page's headgear state runs.
    depth: AtomicU32,
    avail: [AtomicU64; AVAIL_WORDS],
    /// The native list while ours is in place.
    pub real_begin: AtomicU64,
    pub real_end: AtomicU64,
    pub real_cap: AtomicU64,
    pub buffer: AtomicU64,
    pub hat_before: AtomicU64,
    pub saved_id: AtomicU32,
    pub unlisted_flag: AtomicU32,
}

/// A started screen as the hook needs it at the end.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct Opened {
    pub entry: Entry,
    pub scene: u64,
    pub sub: u64,
    pub rows: u32,
    pub page: u32,
    pub depth: u32,
}

/// A page waiting for the first tick of the headgear state.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct Pending {
    pub entry: Entry,
    pub page: u32,
    /// Cursor row wanted, `None` for the page's default.
    pub hint: Option<u32>,
    /// False for the first page of a visit: the Mii is snapshotted when it opens.
    pub in_visit: bool,
}

/// What [`Mode::clear_pending`] dropped.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Dropped {
    Nothing,
    /// An arm that never reached the headgear state.
    Arm,
    /// The next page of a visit: the visit is over without its last page.
    Page,
}

const AVAIL_ZERO: AtomicU64 = AtomicU64::new(0);

impl Mode {
    pub const fn new() -> Self {
        Mode {
            phase: AtomicU32::new(PHASE_IDLE),
            entry: AtomicU32::new(0),
            scene: AtomicU64::new(0),
            sub: AtomicU64::new(0),
            rows: AtomicU32::new(0),
            page: AtomicU32::new(0),
            hint: AtomicU32::new(NO_HINT),
            visit: AtomicU32::new(0),
            changes: AtomicU32::new(0),
            depth: AtomicU32::new(0),
            avail: [AVAIL_ZERO; AVAIL_WORDS],
            real_begin: AtomicU64::new(0),
            real_end: AtomicU64::new(0),
            real_cap: AtomicU64::new(0),
            buffer: AtomicU64::new(0),
            hat_before: AtomicU64::new(0),
            saved_id: AtomicU32::new(0),
            unlisted_flag: AtomicU32::new(0),
        }
    }

    pub fn phase(&self) -> u32 {
        self.phase.load(Ordering::Acquire)
    }

    fn entry_of(&self) -> Option<Entry> {
        match self.entry.load(Ordering::Relaxed) {
            1 => Some(Entry::A),
            2 => Some(Entry::B),
            _ => None,
        }
    }

    /// The dispatcher saw an arming exit value on `scene`: a new visit that will open
    /// `page` first. Refused while a screen is open.
    pub fn arm(&self, entry: Entry, scene: u64, page: u32) -> bool {
        if scene == 0 || page == 0 || self.phase() == PHASE_ACTIVE {
            return false;
        }
        self.entry.store(entry as u32, Ordering::Relaxed);
        self.scene.store(scene, Ordering::Relaxed);
        self.page.store(page, Ordering::Relaxed);
        self.hint.store(NO_HINT, Ordering::Relaxed);
        self.visit.store(0, Ordering::Relaxed);
        self.changes.store(0, Ordering::Relaxed);
        self.phase.store(PHASE_PENDING, Ordering::Release);
        true
    }

    /// A dispatcher call that does not arm: whatever waits for the headgear state is
    /// dropped, so it cannot turn a later normal visit into mod mode.
    pub fn clear_pending(&self) -> Dropped {
        if self.phase.compare_exchange(PHASE_PENDING, PHASE_IDLE, Ordering::AcqRel, Ordering::Acquire).is_err() {
            return Dropped::Nothing;
        }
        let dropped = if self.visit.swap(0, Ordering::Relaxed) != 0 { Dropped::Page } else { Dropped::Arm };
        self.page.store(0, Ordering::Relaxed);
        self.scene.store(0, Ordering::Relaxed);
        dropped
    }

    /// First tick of the headgear state on `scene`: the page that waits for it, if any.
    /// Whatever waited is consumed either way; a page of another scene ends the visit.
    pub fn take_pending(&self, scene: u64) -> Option<Pending> {
        if self.phase.compare_exchange(PHASE_PENDING, PHASE_IDLE, Ordering::AcqRel, Ordering::Acquire).is_err() {
            return None;
        }
        let page = self.page.load(Ordering::Relaxed);
        let found = if scene != 0 && self.scene.load(Ordering::Relaxed) == scene && page != 0 {
            self.entry_of().map(|entry| Pending {
                entry,
                page,
                hint: match self.hint.load(Ordering::Relaxed) {
                    NO_HINT => None,
                    row => Some(row),
                },
                in_visit: self.visit.load(Ordering::Relaxed) != 0,
            })
        } else {
            None
        };
        if found.is_none() {
            self.visit.store(0, Ordering::Relaxed);
            self.page.store(0, Ordering::Relaxed);
        }
        found
    }

    /// The list is swapped in: from here on the hooks answer for synthetic handles. `depth`
    /// is the state-stack depth of the running headgear state, `avail` the rows that can be
    /// decided.
    pub fn activate(
        &self, entry: Entry, scene: u64, sub: u64, rows: u32, page: u32, depth: u32, avail: &[u64; AVAIL_WORDS],
    ) -> bool {
        if scene == 0 || sub == 0 || rows == 0 || page == 0 || self.phase() != PHASE_IDLE {
            return false;
        }
        self.entry.store(entry as u32, Ordering::Relaxed);
        self.scene.store(scene, Ordering::Relaxed);
        self.sub.store(sub, Ordering::Relaxed);
        self.rows.store(rows, Ordering::Relaxed);
        self.page.store(page, Ordering::Relaxed);
        self.depth.store(depth, Ordering::Relaxed);
        for (cell, word) in self.avail.iter().zip(avail.iter()) {
            cell.store(*word, Ordering::Relaxed);
        }
        self.visit.store(1, Ordering::Relaxed);
        self.phase.store(PHASE_ACTIVE, Ordering::Release);
        true
    }

    /// Rows of the open list, 0 when no list is open.
    #[inline(always)]
    pub fn active_rows(&self) -> u32 {
        if self.phase.load(Ordering::Acquire) == PHASE_ACTIVE {
            self.rows.load(Ordering::Relaxed)
        } else {
            0
        }
    }

    /// True when a list is open on sub-object `sub`.
    #[inline(always)]
    pub fn is_active_sub(&self, sub: u64) -> bool {
        self.phase.load(Ordering::Acquire) == PHASE_ACTIVE && sub != 0 && self.sub.load(Ordering::Relaxed) == sub
    }

    /// Whether row `row` of the open page can be decided; false when no list is open.
    #[inline(always)]
    pub fn row_available(&self, row: u32) -> bool {
        if row >= self.active_rows() {
            return false;
        }
        match self.avail.get(row as usize / 64) {
            Some(word) => word.load(Ordering::Relaxed) & (1u64 << (row % 64)) != 0,
            None => false,
        }
    }

    /// Page code of the open page, 0 when no list is open.
    #[inline(always)]
    pub fn active_page(&self) -> u32 {
        if self.phase.load(Ordering::Acquire) == PHASE_ACTIVE {
            self.page.load(Ordering::Relaxed)
        } else {
            0
        }
    }

    /// The open screen, when the headgear state that is ticking is the one that opened it.
    pub fn opened(&self, scene: u64, sub: u64) -> Option<Opened> {
        if self.phase() != PHASE_ACTIVE
            || self.scene.load(Ordering::Relaxed) != scene
            || self.sub.load(Ordering::Relaxed) != sub
        {
            return None;
        }
        let entry = if self.entry.load(Ordering::Relaxed) == Entry::B as u32 { Entry::B } else { Entry::A };
        Some(Opened {
            entry,
            scene,
            sub,
            rows: self.rows.load(Ordering::Relaxed),
            page: self.page.load(Ordering::Relaxed),
            depth: self.depth.load(Ordering::Relaxed),
        })
    }

    /// The open page's list is back to the native one and the visit goes on: the hooks stop
    /// answering for synthetic handles until the next page opens.
    pub fn page_closed(&self) {
        self.phase.store(PHASE_IDLE, Ordering::Release);
        self.rows.store(0, Ordering::Relaxed);
        self.sub.store(0, Ordering::Relaxed);
        self.buffer.store(0, Ordering::Relaxed);
    }

    /// The visit goes on with `page` on the same scene (cursor on `hint`), to be opened by
    /// the next first tick of the headgear state. Only between [`Mode::page_closed`] and
    /// that tick. Returns the number of page changes of the visit so far.
    pub fn next_page(&self, scene: u64, page: u32, hint: Option<u32>) -> Option<u32> {
        if scene == 0
            || page == 0
            || self.phase() != PHASE_IDLE
            || self.visit.load(Ordering::Relaxed) == 0
            || self.scene.load(Ordering::Relaxed) != scene
        {
            return None;
        }
        self.page.store(page, Ordering::Relaxed);
        self.hint.store(hint.unwrap_or(NO_HINT), Ordering::Relaxed);
        let changes = self.changes.fetch_add(1, Ordering::Relaxed).wrapping_add(1);
        self.phase.store(PHASE_PENDING, Ordering::Release);
        Some(changes)
    }

    /// Page changes of the visit so far.
    pub fn changes(&self) -> u32 {
        self.changes.load(Ordering::Relaxed)
    }

    /// True from the first opened page of a visit until the visit ends. (Host tests only.)
    #[allow(dead_code)]
    pub fn in_visit(&self) -> bool {
        self.visit.load(Ordering::Relaxed) != 0
    }

    /// Back to idle, whatever the phase was; the visit is over.
    pub fn disarm(&self) {
        self.phase.store(PHASE_IDLE, Ordering::Release);
        self.rows.store(0, Ordering::Relaxed);
        self.sub.store(0, Ordering::Relaxed);
        self.scene.store(0, Ordering::Relaxed);
        self.buffer.store(0, Ordering::Relaxed);
        self.page.store(0, Ordering::Relaxed);
        self.visit.store(0, Ordering::Relaxed);
    }
}

/// State number of the headgear sub-screen.
pub const STATE_HEADGEAR: u32 = 5;
/// Slots of the scene's state stack; the reader traps on an index that is not below this.
pub const STACK_SLOTS: u32 = 19;

/// What the plugin reads of the scene right after the headgear state's last tick.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub struct StackView {
    /// Depth while the page's headgear state ran.
    pub depth_open: u32,
    /// Depth now, after the original's pop.
    pub depth_now: u32,
    /// The state stored in stack slot `depth_open` (the pop leaves it in place).
    pub slot_state: u32,
    /// `scene+0x148`, the state the reader last made current.
    pub current_state: u32,
    /// `scene+0x154`.
    pub restart: u8,
    /// The pair at `scene+0x18`.
    pub change_cb: (u64, u64),
}

/// May the headgear state be entered again by putting the depth back to `depth_open` and
/// raising the restart byte? Only when the scene is exactly as the proof assumes: the
/// original popped one level off a headgear state that is still the current state, nobody
/// asked for a restart, and the reader would call no callback.
pub fn can_reenter(view: &StackView) -> Result<(), &'static str> {
    if view.depth_open == 0 || view.depth_open >= STACK_SLOTS {
        return Err("depth_range");
    }
    if view.depth_now.wrapping_add(1) != view.depth_open {
        return Err("not_popped");
    }
    if view.slot_state != STATE_HEADGEAR {
        return Err("slot_state");
    }
    if view.current_state != STATE_HEADGEAR {
        return Err("current_state");
    }
    if view.restart != 0 {
        return Err("restart_set");
    }
    if view.change_cb != (0, 0) {
        return Err("change_callback");
    }
    Ok(())
}

/// The selected row to store after the item count became `count`, `None` when the stored
/// one can stay. The list's own tick indexes the item vector with the selected row and
/// traps on a row that is not below the count (0x19cc45c); the scroller refreshes the
/// selected row from the cursor only in its own frame function, so a count that shrinks
/// below a stale selected row has to pull it in at once. -1 ("none") is left alone.
pub fn clamp_selected(selected: i32, cursor: i32, count: u32) -> Option<i32> {
    if selected < 0 || (selected as u32) < count {
        return None;
    }
    if cursor >= 0 && (cursor as u32) < count {
        Some(cursor)
    } else {
        Some(0)
    }
}

/// First offset at which two snapshots of the working record differ.
pub fn first_difference(before: &[u8], after: &[u8]) -> Option<usize> {
    if before.len() != after.len() {
        return Some(before.len().min(after.len()));
    }
    before.iter().zip(after.iter()).position(|(a, b)| a != b)
}

/// Sanity of a native `std::vector` of 8-byte handles: its element count, `None` when the
/// three pointers do not describe one of 1..=[`NATIVE_COUNT_MAX`] elements.
pub fn vector_count(begin: u64, end: u64, cap: u64) -> Option<u64> {
    if begin == 0 || end <= begin || cap < end || begin & 7 != 0 {
        return None;
    }
    let bytes = end - begin;
    if bytes & 7 != 0 || bytes / 8 > NATIVE_COUNT_MAX {
        return None;
    }
    Some(bytes / 8)
}

/// Two headgear handles are "the same item" for the game when both are well-formed (tag
/// 0x5a, non-zero 40-bit hash) with equal hashes, or both are not (0x19cfe40..0x19cfe94).
pub fn same_item(a: u64, b: u64) -> bool {
    let well = |h: u64| h & TAG_MASK == TAG && h & 0xff_ffff_ffff != 0;
    match (well(a), well(b)) {
        (true, true) => (a ^ b) & 0xff_ffff_ffff == 0,
        (false, false) => true,
        _ => false,
    }
}
