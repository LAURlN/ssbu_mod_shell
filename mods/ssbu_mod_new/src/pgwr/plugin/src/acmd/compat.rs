//! `sv_animcmd` calls the dumps use that the pinned `smash_script` (fdc6144) has no
//! wrapper for.
//!
//! The raw bindings exist in skyline-smash (`cpp.rs`) and each takes only the Lua
//! state; the arguments travel on the Lua stack. These wrappers follow exactly the
//! pattern the real macros use (`macros.rs`: clear the stack, push the arguments,
//! call, clear the stack), so a generated script can call them the way the dump
//! calls the game's own.
//!
//! Argument order and types come from the dump's call sites, which are the only
//! documentation there is; nothing here was tuned by hand.
#![allow(non_snake_case)]

use {
    smash::{
        app::{sv_animcmd, *},
        lib::L2CValue,
        lua2cpp::*,
        phx::*,
    },
    smash_script::{lua_args, macros::ToF32},
};

/// `THROW_ITEM_OFFSET(x, y, ANGLE_VAR, SPEED_VAR, POWER_VAR)`: where a thrown item
/// leaves the hand, and which item variables carry its launch angle, speed, power.
#[inline(never)]
pub unsafe fn THROW_ITEM_OFFSET<A: ToF32, B: ToF32>(
    agent: &mut L2CAgentBase, x: A, y: B, angle_var: i32, speed_var: i32, power_var: i32,
) {
    agent.clear_lua_stack();
    lua_args!(agent, x.to_f32(), y.to_f32(), angle_var, speed_var, power_var);
    sv_animcmd::THROW_ITEM_OFFSET(agent.lua_state_agent);
    agent.clear_lua_stack();
}

#[inline(never)]
pub unsafe fn SHOOT_ITEM_BULLET(agent: &mut L2CAgentBase) {
    agent.clear_lua_stack();
    sv_animcmd::SHOOT_ITEM_BULLET(agent.lua_state_agent);
    agent.clear_lua_stack();
}

/// The argument is a work-int id (`FIGHTER_STATUS_ITEM_SHOOT_WORK_INT_SSCOPE_CHARGE`).
#[inline(never)]
pub unsafe fn SHOOT_ITEM_BULLET_CHARGE(agent: &mut L2CAgentBase, work_int: i32) {
    agent.clear_lua_stack();
    lua_args!(agent, work_int);
    sv_animcmd::SHOOT_ITEM_BULLET_CHARGE(agent.lua_state_agent);
    agent.clear_lua_stack();
}

/// Pushes its answer on the Lua stack like every sv_animcmd query.
#[inline(never)]
pub unsafe fn IS_HAVE_ITEM_KIND(agent: &mut L2CAgentBase, kind: i32) -> bool {
    agent.clear_lua_stack();
    lua_args!(agent, kind);
    sv_animcmd::IS_HAVE_ITEM_KIND(agent.lua_state_agent);
    let answer = agent.pop_lua_stack(1).get_bool();
    agent.clear_lua_stack();
    answer
}

/// `SET_RATE_ARTICLE_V(article, rate)`. Two arguments, read off G&W's compiled
/// `game_landingairn` (lua2cpp_gamewatch.nro 0xc032c-0xc03a4: push article id,
/// push the float from `get_value_float`, call). The dump prints only one.
#[inline(never)]
pub unsafe fn SET_RATE_ARTICLE_V(agent: &mut L2CAgentBase, article: i32, rate: f32) {
    agent.clear_lua_stack();
    lua_args!(agent, article, rate);
    sv_animcmd::SET_RATE_ARTICLE_V(agent.lua_state_agent);
    agent.clear_lua_stack();
}

/// Same argument layout as `macros::EFFECT`; only the sv_animcmd entry point differs
/// (it plays the effect at the ground contact point of a downed fighter).
#[inline(never)]
pub unsafe fn DOWN_EFFECT<
    A: ToF32, B: ToF32, C: ToF32, D: ToF32, E: ToF32, F: ToF32, G: ToF32,
    H: ToF32, I: ToF32, J: ToF32, K: ToF32, L: ToF32, M: ToF32,
>(
    agent: &mut L2CAgentBase, effect: Hash40, bone: Hash40, x_pos: A, y_pos: B, z_pos: C,
    x_rot: D, y_rot: E, z_rot: F, size: G, unk8: H, unk9: I, unk10: J, unk11: K, unk12: L,
    unk13: M, unk14: bool,
) {
    agent.clear_lua_stack();
    lua_args!(
        agent, effect, bone, x_pos.to_f32(), y_pos.to_f32(), z_pos.to_f32(), x_rot.to_f32(),
        y_rot.to_f32(), z_rot.to_f32(), size.to_f32(), unk8.to_f32(), unk9.to_f32(),
        unk10.to_f32(), unk11.to_f32(), unk12.to_f32(), unk13.to_f32(), unk14
    );
    sv_animcmd::DOWN_EFFECT(agent.lua_state_agent);
    agent.clear_lua_stack();
}
