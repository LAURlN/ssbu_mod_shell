//! Custom statuses this mod owns, as opposed to Pyra's or G&W's.
//!
//! # Why a new status at all
//!
//! The installed smashline (`smashline_1304`, `src/create_agent.rs:738-771`,
//! `install_status_scripts`) registers a script for a status id that can be past
//! the end of the fighter's own table, and then raises that table's count
//! (`global_table[0xC]`) to cover it. The costume filter in the same function is
//! the one `set_costume` uses, so a status registered here is only ever installed
//! for Pyra c06/c07: a c00-c05 agent keeps every stock pointer, and `elight`
//! (Mythra) and `gamewatch` are never registered at all.
//!
//! # Id allocation
//!
//! `FIGHTER_EFLAME_STATUS_KIND_NUM` is `0x1EE` in the locked `skyline-smash`
//! `lua_const.rs`, and the last real eflame status is `0x1ED` (`SPECIAL_HI_END`),
//! so `0x1EE` is the first id that cannot collide with anything Pyra has. This
//! table is the record the move-replacement guide asks for: allocate from the
//! top, never reuse, and write it down.
//!
//! | id | name | entered by |
//! | - | ---- | ---------- |
//! | `0x1EE` | `START` | ground or air side-B, via `entry_pre` on `SPECIAL_S` |
//! | `0x1EF` | `JUMP` | startup clip ending |
//! | `0x1F0` | `KICK` | attack/special input inside the donor's kick window |
//! | `0x1F1` | `KICK_LANDING` | landing during KICK |
//! | `0x1F2` | `FLIP_LANDING` | landing during JUMP |
//! | `0x1F3` | `FLIP_FALL` | KICK clip ending in the air |
//! | `0x1F4` | `STICK` | the engine reporting a capture during JUMP |
//! | `0x1F5` | `STICK_ATTACK` | attack or special input while clinging |
//! | `0x1F6` | `STICK_ATTACK2` | the cling attack clip ending |
//! | `0x1F7` | `STICK_JUMP` | jump input while clinging |
//! | `0x1F8` | `STICK_JUMP2` | the cling jump clip ending |
//! | `0x1F9` | `SPECIAL_HI_FALL` | up-B (Fire) clip ending: G&W's `0x1E1`, parachute descent |
//! | `0x1FA` | `SPECIAL_HI_CLOSE` | stick flick or landing during `SPECIAL_HI_FALL`: G&W's `0x1E2` |
//!
//! `0x1EE` used to be Judge's. Judge's status, its ACMD and its module are gone
//! from this crate: side-B is Monkey Flip now, one move cannot own the button
//! twice, and leaving an unreachable status registered would be the kind of
//! leftover this workspace's rules exist to prevent. The file-addition probe
//! Judge carried (`d01specialsl.nuanmb` under its own name, declared in the
//! mod's `config.json`) is unaffected at build level - that file is still
//! referenced by G&W's own `special_s_1_l` motion-list entry and is still
//! shipped - but nothing plays that entry any more, so the probe is no longer
//! exercised at runtime. Recorded in `projects/pgwr/STATUS.md`.
//!
//! Up-B's first phase is the common `SPECIAL_HI` itself (replaced on the gated
//! agent, as G&W's is his own), so only its two follow-ups need ids. The next
//! Snake's neutral-B reserves `0x1FB..0x207`; Gaogaen back throw owns `0x208`.
//! Next free eflame status is `0x209` (2026-10-03 user-authorized allocation).
//! Do not reuse a number from either block. The pending module is not installed.
//!
//! `install` re-checks the first id against `lua_const` at load, so a toolchain
//! bump that moves Pyra's table fails loudly at boot instead of silently
//! overwriting a real status.

pub mod monkey_flip;
mod monkey_flip_capture;
mod monkey_flip_capture_data;
pub mod monkey_flip_params;
pub mod special_hi;
pub mod snake_grenade;
pub mod gaogaen_throw_b;

/// Incineroar back throw on eflame c06/c07; allocated 2026-10-03.
pub const STATUS_GAOGAEN_THROW_B: i32 = 0x208;

// Snake follow-up block; separate from Mythra's independently allocated table.
pub const STATUS_SNAKE_N_HOLD_WAIT: i32 = 0x1FB;
pub const STATUS_SNAKE_N_HOLD_WALK_F: i32 = 0x1FC;
pub const STATUS_SNAKE_N_HOLD_WALK_BRAKE_F: i32 = 0x1FD;
pub const STATUS_SNAKE_N_HOLD_WALK_B: i32 = 0x1FE;
pub const STATUS_SNAKE_N_HOLD_WALK_BRAKE_B: i32 = 0x1FF;
pub const STATUS_SNAKE_N_HOLD_DASH_F: i32 = 0x200;
pub const STATUS_SNAKE_N_HOLD_DASH_B: i32 = 0x201;
pub const STATUS_SNAKE_N_HOLD_JUMP_SQUAT: i32 = 0x202;
pub const STATUS_SNAKE_N_HOLD_JUMP: i32 = 0x203;
pub const STATUS_SNAKE_N_HOLD_JUMP_AERIAL: i32 = 0x204;
pub const STATUS_SNAKE_N_HOLD_AIR: i32 = 0x205;
pub const STATUS_SNAKE_N_HOLD_LANDING: i32 = 0x206;
pub const STATUS_SNAKE_N_THROW: i32 = 0x207;

use smash::lib::lua_const::FIGHTER_EFLAME_STATUS_KIND_NUM;

/// First status id above `FIGHTER_EFLAME_STATUS_KIND_NUM` (`0x1EE`).
pub const STATUS_MONKEY_FLIP_START: i32 = 0x1EE;
pub const STATUS_MONKEY_FLIP_JUMP: i32 = 0x1EF;
pub const STATUS_MONKEY_FLIP_KICK: i32 = 0x1F0;
pub const STATUS_MONKEY_FLIP_KICK_LANDING: i32 = 0x1F1;
pub const STATUS_MONKEY_FLIP_FLIP_LANDING: i32 = 0x1F2;
pub const STATUS_MONKEY_FLIP_FLIP_FALL: i32 = 0x1F3;
pub const STATUS_MONKEY_FLIP_STICK: i32 = 0x1F4;
pub const STATUS_MONKEY_FLIP_STICK_ATTACK: i32 = 0x1F5;
pub const STATUS_MONKEY_FLIP_STICK_ATTACK2: i32 = 0x1F6;
pub const STATUS_MONKEY_FLIP_STICK_JUMP: i32 = 0x1F7;
pub const STATUS_MONKEY_FLIP_STICK_JUMP2: i32 = 0x1F8;
/// Up-B (Fire): G&W's `SPECIAL_HI_FALL` / `SPECIAL_HI_CLOSE` (`special_hi.rs`).
pub const STATUS_SPECIAL_HI_FALL: i32 = 0x1F9;
pub const STATUS_SPECIAL_HI_CLOSE: i32 = 0x1FA;

pub fn install() {
    assert_eq!(
        STATUS_MONKEY_FLIP_START,
        *FIGHTER_EFLAME_STATUS_KIND_NUM,
        "Monkey Flip's first status id no longer matches \
         FIGHTER_EFLAME_STATUS_KIND_NUM; re-derive the block and update the \
         allocation table in this file"
    );
    monkey_flip::install();
    special_hi::install();
    gaogaen_throw_b::install();
    #[cfg(feature = "snake-neutral-b")]
    snake_grenade::install();
}
