# Outstanding Questions & Decompiler Issues

This document records ambiguities, decompilation artifacts, and unresolved symbols encountered during development, in accordance with the project policy:
*"The clone must play exactly like the original game. Never change numbers, frames, conditions or the order of calls in any game script. If something looks wrong, write it in QUESTIONS.md instead of fixing it."*

---

### Question 1: Unresolved Raw Addresses in Taunt Scripts (`AppealHiR` / `AppealHiL`)
- **Agents:** `cflame`, `clight`
- **Functions:** `game_appealhir`, `game_appealhil`, `effect_appealhir`, `effect_appealhil`
- **Issue:** The dumped scripts contain calls referencing raw hex addresses (`0x3de840` and `0x357740`) instead of named Smashline/Skyline animcmd functions or hash constants.
- **Action Taken:** Commented out of registration to prevent undefined behavior and unresolved symbol errors.
- **Resolution Needed:** Identify what engine functions or macros map to addresses `0x3de840` and `0x357740`.

---

### Question 2: Decompiler Syntax Error in `AppealHiR.txt`
- **Agents:** `cflame`, `clight`
- **Functions:** `sound_appealhir`
- **Issue:** The decompiler emitted invalid nested syntax: `Hash40::new_raw(Hash40::new("l_appeal_hi_r)")`. The closing quote and parenthesis are malformed.
- **Action Taken:** Excluded from registration.
- **Resolution Needed:** Confirm whether this should be `Hash40::new("l_appeal_hi_r")` or if audio should be handled differently.

---

### Question 3: Missing Diver Sword Attachment Functions (`attach_esword_diver` / `detach_esword_diver`)
- **Agents:** `cflame`, `clight`
- **Functions:** `Final.txt`, `FinalAir.txt`, `FinalAirL.txt`, `FinalL.txt` (`game_final`, `game_finalair`, `game_finalairl`, `game_finall`)
- **Issue:** The dumped Final Smash scripts invoke `attach_esword_diver(agent.module_accessor)` and `detach_esword_diver(agent.module_accessor)`. These symbols are not exported by `skyline_smash`, `smashline`, or `smash_script`.
- **Action Taken:** Excluded from registration.
- **Resolution Needed:** Provide the function definitions or crate module containing the diver attachment routines.

---

### Question 4: Decompiler C++ Method Artifacts (`methodlua2cpp` & `methodlib`)
- **Agents:** `cflame`, `clight`
- **Functions:** Generic item swings (bat, club, firebar, lipstick, starrod, etc.) and various expression scripts.
- **Issue:** The decompiler emitted raw C++ internal class calls such as `methodlua2cpp::L2CFighterAnimcmdGameCommon::game_BatSwing1Common()()` and `methodlib::L2CValue::operator<=`. These are internal C++ symbols that do not exist in Smashline Rust.
- **Action Taken:** Excluded from registration.
- **Resolution Needed:** Replace with Smashline macro equivalents or allow the engine's default fighter common animcmds to handle generic item swings.

---

### Question 5: Missing Smashline Animation Macros
- **Agents:** `cflame`, `clight`
- **Functions:** Item shooting and throwing scripts (`lgunshoot`, `scopeairfire`, `drillshoot`, `fflowershoot`, `itemheavythrow*`, `itemlightthrow*`, etc.).
- **Issue:** The dump uses macros not defined in `smash_script::macros`:
  - `macros::THROW_ITEM_OFFSET`
  - `macros::SHOOT_ITEM_BULLET`
  - `macros::SHOOT_ITEM_BULLET_CHARGE`
  - `macros::EFFECT_FLW_POS_UNSYNC_VIS`
  - `macros::RUMBLE_FINAL_TARGET`
  - `macros::DOWN_EFFECT`
  - `macros::IS_HAVE_ITEM_KIND`
  - `macros::FLASH_SET_DIRECTION`
  - `macros::LAST_EFFECT_SET_WORK_INT`
  - `macros::CLR_SPEED`
- **Action Taken:** Excluded from registration.
- **Resolution Needed:** Implement the missing macro wrappers in a shared utility or include them in `smash_script`.

---

### Question 6: Decompiler Argument Count & Parameter Mismatches
- **Agents:** `cflame`, `clight`
- **Functions:** Various item interactions, loop synchronization, and trail effects:
  - `wait_loop_sync_mot()` (missing required frame/motion argument)
  - `wait_loop_clear()` (missing required argument)
  - `ItemModule::pickup_item(...)` (missing parameter arguments)
  - `ItemModule::use_item(...)` (missing bool argument)
  - `ItemModule::set_have_item_scale_anim(...)` (mismatched parameter count)
  - `ItemModule::set_have_item_action(...)` (mismatched parameter count)
  - `macros::AFTER_IMAGE4_ON_arg29(...)` (22 arguments supplied, macro requires 30)
  - `AREA_WIND_2ND_arg10(...)` (mismatched arguments)
  - `frame(false, ...)` (mangled frame call)
- **Action Taken:** Excluded from registration. Supplying arbitrary values would violate the strict rule prohibiting changing numbers or call conditions.
- **Resolution Needed:** Provide accurate argument signatures matching the game executable.

---

### Question 7: Unresolved `singletons` Crate Reference in Throw Scripts
- **Agents:** `cflame`, `clight`
- **Functions:** `game_throwb`, `game_throwf`, `game_throwhi`, `game_throwlw`
- **Issue:** Throw animcmds call `lua_bind::FighterCutInManager::set_throw_finish_zoom_rate(singletons::FighterCutInManager(), ...)` and `set_throw_finish_offset(...)`. The `singletons` crate is not available in the dependency tree.
- **Action Taken:** Excluded from registration.
- **Resolution Needed:** Determine how `FighterCutInManager` singleton instance is obtained in Skyline Smashline crates.

---

### Question 8: Malformed Enum Syntax in Final Smash Visual Scene
- **Agents:** `cflame`, `clight`
- **Functions:** `game_visualscene01`
- **Issue:** Dump contains `macros::FILL_SCREEN_MODEL_COLOR(..., EffectScreenLayer:*CHAR, ...)`. In Rust, `EffectScreenLayer:*CHAR` is a syntax error, and no `*EFFECT_SCREEN_LAYER_CHAR` constant exists in `lua_const`.
- **Action Taken:** Excluded from registration.
- **Resolution Needed:** Identify the integer value or constant corresponding to `EffectScreenLayer:*CHAR`.

---

### Question 9: Direct Function Calls to Macros (`physics` & `shield`)
- **Agents:** `cflame`, `clight`
- **Functions:** Smash charge expressions (`expression_attackhi4charge`, `expression_attacklw4charge`, `expression_attacks4charge`, `expression_swordswing4charge`, etc.) and shield expressions.
- **Issue:** Dump calls `physics(*MA_MSC_CMD_PHYSICS_START_CHARGE, ...)` and `shield(*MA_MSC_CMD_SHIELD_OFF, ...)` without passing the agent or using macro invocation (`physics!(agent, ...)` / `shield!(agent, ...)`).
- **Action Taken:** Excluded from registration.
- **Resolution Needed:** Verify whether converting these to `physics!(agent, ...)` / `shield!(agent, ...)` preserves exact behavioral fidelity.
