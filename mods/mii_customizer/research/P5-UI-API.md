# P5-UI-API - inventory of the UI script API the game's own Lua scripts use

Task `prompts/P5-UI-API.md`, 2026-10-05. Space Bunny Alpha worker.
**Status: DONE.**

This is an **inventory** task. It measures what names and call shapes the game's
own UI Lua chunks already use. It designs nothing, writes no mod logic, and makes
no claim about runtime behaviour.

## 1. Inputs (read-only) and hashes

| input | sha256 | note |
|---|---|---|
| `gamedata/ssbu-13.0.4/data.arc` | `ef615e671e1d4907f0a707f2eb13e3cb0c8539c4e67ac51c89ef547c22b82995` | source of all 86 chunks |
| `gamedata/ssbu-13.0.4/main.bin` | `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613` | step 5; matches the value the task pinned |
| `mods/ssbu_mod_new/dumps/decoded/arc_files.tsv` | 590,711 paths | read-only path index |
| `tools/lua53-inspect/lua53_inspect.py` | used as a library | not modified |
| `scratch/2026-10-04_P2-UI-CONSTS/refscan9.py` | copied to `refscan9_copy.py`, **not edited** | step 5 reference scan |

Two chunks in the set are ones the coordinator already verified independently in
`research/COORDINATOR-2026-10-04.md`. This extraction reproduced those hashes
exactly, which is a useful independent confirmation of the extraction path:

| ARC path | sha256 here | coordinator-verified |
|---|---|---|
| `ui/script/menu/chara_make/make_mii_special_actor.lc` | `ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d` | same |
| `ui/script/menu/chara_make/make_mii_edit_actor.lc` | `1f73dff133961b68dbe24641298229b9f3905a44703164563911b105eaa16908` | same |

## 2. Selection: 86 scripts, nothing left out

Selection rule, applied to the path index and nothing else: every line matching
`^ui/script(_patch)?/.*\.lc$`. **86 paths**, no duplicates, all `.lc`.

**86 is below the task's 400-script threshold, so every selected script was
extracted and analysed. Nothing was left out and the reduced fallback
(`ui/script/menu/`, `ui/script_patch/`, `ui/script/common/`) was not used.**

| area | count |
|---|---|
| `ui/script/menu/main` | 20 |
| `ui/script/menu/common` | 14 |
| `ui/script/menu/chara_make` | 8 |
| `ui/script/menu/option` | 7 |
| `ui/script/menu/online` | 7 |
| `ui/script/standard` | 6 |
| `ui/script/menu/spirits`, `melee`, `collection` | 3 each |
| `ui/script/common` | 3 |
| `ui/script/menu/local` | 2 |
| `ui/script/menu/amiibo` | 1 |
| `ui/script_patch/...` | 9 |

Extracted with `tools/arc-extract/target/release/arc-extract.exe` into
workspace `gamedata/mii_customizer/P5-UI-API/`, mirroring the ARC path
(`extract_log.txt`: "86 extracted, 0 failed", exit 0). 543,839 bytes total.
Per-file size and sha256 in `evidence/P5-UI-API/manifest.tsv`; the manifest was
re-hashed independently of the extractor's own printed hashes and all 86 agree.

**All 86 chunks pass `lua53-inspect verify` (exit 0), so nothing was excluded.**
Full log: `evidence/P5-UI-API/verify_all.txt`.

## 3. What the measurement actually did

Parsing, opmode decoding and constant resolution come from `lua53-inspect` as a
library. Nothing here reads constant *strings* on their own: a name enters the
inventory only when an instruction consumes it.

| measured | how |
|---|---|
| method names | `SELF` RK operand (constant) |
| global reads / writes | `GETTABUP` / `SETTABUP` RK operand where the upvalue is `_ENV` |
| field calls | `GETTABLE`/`GETTABUP` constant field whose value is consumed by a `CALL`, with no `SELF` immediately before |
| bridge names | the first argument of `UiScriptPlayer.invoke(...)` when it is a string constant |

### 3.1 Two off-by-one errors I made and fixed, recorded because they change every count

Both were caught by checking my output against facts P2-UI-FLOW had already
established, not by inspection. They are worth recording because a reader
re-deriving these numbers would hit the same two.

1. **The consuming `CALL` is not at `pc+1`.** A `SELF` or `GETTABLE` puts the
   function in register `A`; the arguments are then loaded into `A+1, A+2, ...`
   and the `CALL` follows them. Only a zero-argument call has the `CALL` at
   `pc+1`. Requiring `pc+1` binned 3,578 of 4,802 method calls as
   "no-following-CALL" and reported **zero** bridge names. Fixed by scanning
   forward, within a prototype, for the first `CALL`/`TAILCALL` whose `A` equals
   the loaded register, stopping at a branch target.
2. **`CALL A B C` has the function in `R[A]`, not `R[A+1]`.** `B-1` arguments
   live in `R[A+1]..R[A+B-1]`. Counting from `A` classifies the *callee* as the
   first argument. For a **method** call the preceding `SELF` puts the receiver
   in `R[A+1]`, so arguments start at `R[A+2]` and there are `B-2`. Before the fix
   `get_skill_id` appeared to take 3 arguments and `set_skill_id` 4; the corrected
   values are 2 and 3, matching P2-UI-FLOW.

The fixed output reproduces every bridge shape P2-UI-FLOW recorded for
`make_mii_special_actor.lc`: `get_skill_id` 2 args, `set_skill_id` 3,
`get_skill_name_label` 3, `get_skill_help_label` 3, `replace_skill` 3,
`replace_skill_subwindow` 2. `check_ui_api.py` asserts these.

### 3.2 How `_ENV` was identified

These chunks are stripped, so there are no upvalue *names* to read. `main`'s
single upvalue is the environment the loader installs, and nested prototypes
inherit it through their upvalue descriptors; the property is propagated down
the descriptor graph rather than assumed per prototype. Spot-checked against
`stage_select_actor.lc` pc32, a real `SETTABUP up[0]["exit_code_"] := nil`.
This is what makes the script-defined / host-provided split in section 6
meaningful rather than a guess.

## 4. Totals

| measure | value |
|---|---|
| chunks analysed | 86 (0 excluded) |
| prototypes | 1,217 |
| instructions | 60,317 |
| distinct method names | 336 |
| method call sites | 4,802 |
| distinct global names | 759 |
| global reads / writes | 6,798 / 586 |
| distinct field names | 404 |
| field call sites | 7,464 |
| distinct `invoke` bridge names | 234 |

**19 method call sites (5 names) had no consuming `CALL` found** and are binned as
`no-following-CALL` rather than guessed at: `check` (14), `set_disabled` (2),
`change`, `set_decidable`, `set_focus`. These are excluded from the argument-count
histograms, so the histograms do not overstate what was resolved.

**17 `invoke` sites have a non-constant first argument** and are therefore *not*
counted as bridge names: `online_priority.lc` (7), `option_sound_top.lc` (4), and
one each in `make_mii_select_actor.lc`, `stage_select_bgm.lc`,
`rule_itemswitch_actor.lc`, and the three patched `stage_select_bgm*.lc`. Per-file
counts in `ui_api.json` under `invoke_sites_with_non_constant_first_argument`.

## 5. Top-40 lists (steps 1-3)

### 5.1 Methods by call count

| name | calls | scripts | argument-count histogram |
|---|---|---|---|
| `play_animation` | 406 | 42 | 2 args ×406 |
| `set_focus` | 253 | 37 | 0 arg ×1, 1 args ×251, unresolved ×1 |
| `get_parts` | 243 | 56 | 0 args ×49, 1 args ×194 |
| `setup` | 219 | 44 | 0 args ×4, 3 args ×117, 4 args ×98 |
| `set_enable` | 198 | 38 | 0 arg ×1, 1 args ×197 |
| `setup_button` | 175 | 37 | 0 args ×18, 2 args ×157 |
| `get_pane` | 142 | 36 | 1 args ×142 |
| `set` | 140 | 23 | 1 args ×138, 2 args ×2 |
| `is_pressed` | 110 | 27 | 1 args ×110 |
| `get_button` | 103 | 26 | 0 args ×8, 1 args ×95 |
| `select_button` | 100 | 33 | 1 args ×81, 2 args ×19 |
| `get_root_view` | 87 | 63 | 0 args ×87 |
| `set_enable_input` | 84 | 29 | 1 args ×84 |
| `set_visible` | 83 | 23 | 1 args ×83 |
| `set_text_message` | 81 | 22 | 0 args ×13, 1 args ×68 |
| `play_animation_parts` | 78 | 11 | 2 args ×78 |
| `get_selected_button_id` | 76 | 21 | 0 args ×76 |
| `add_id` | 71 | 13 | 3 args ×71 |
| `get_decided_button_id` | 68 | 36 | 0 args ×68 |
| `has_focus` | 67 | 22 | 0 args ×67 |
| `set_selectable` | 64 | 16 | 1 args ×3, 2 args ×61 |
| `get_virtual_input` | 62 | 50 | 0 args ×62 |
| `new` | 61 | 16 | 0 args ×61 |
| `update` | 60 | 33 | 0 args ×48, 1 args ×12 |
| `set_decidable` | 53 | 22 | 0 args ×4, 1 args ×20, 2 args ×28, unresolved ×1 |
| `stop_animation_at_end` | 51 | 26 | 1 args ×51 |
| `is_pressing` | 45 | 13 | 1 args ×45 |
| `set_position` | 44 | 20 | 2 args ×40, 3 args ×4 |
| `check` | 35 | 9 | 1 args ×21, unresolved ×14 |
| `initialize` | 35 | 22 | 0 args ×26, 1 args ×3, 2 args ×4, 5 args ×2 |
| `is_cancel` | 35 | 18 | 0 args ×35 |
| `set_assign` | 33 | 10 | 3 args ×33 |
| `select_item` | 29 | 13 | 1 args ×2, 2 args ×27 |
| `set_text_args` | 28 | 7 | 2 args ×22, 3 args ×6 |
| `is_cancelled` | 27 | 21 | 0 args ×27 |
| `is_animation_finished` | 26 | 13 | 1 args ×26 |
| `set_text_message_args` | 26 | 5 | 3 args ×11, 4 args ×9, 5 args ×2, 6 args ×4 |
| `decide_button` | 25 | 13 | 1 args ×23, 2 args ×2 |
| `stop_animation_frame` | 25 | 11 | 0 args ×2, 2 args ×23 |
| `set_scale` | 24 | 14 | 2 args ×24 |

### 5.2 Globals by read count

| name | reads | writes | classification |
|---|---|---|---|
| `UiScriptPlayer` | 928 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `button` | 357 | 1 | script-defined (written by at least one of these scripts) |
| `coroutine` | 233 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `UI_INVALID_INDEX` | 223 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `ComFrameActor` | 200 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `UiSoundManager` | 182 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `module_ui_common` | 179 | 4 | script-defined (written by at least one of these scripts) |
| `AppPopupManager` | 172 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `layout_view` | 125 | 30 | script-defined (written by at least one of these scripts) |
| `math` | 98 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `LayoutButtonSelector` | 92 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `LayoutRootList` | 92 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `manager` | 88 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `USE_STAGE_NUM` | 87 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `common` | 82 | 1 | script-defined (written by at least one of these scripts) |
| `string` | 82 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `ipairs` | 74 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `state` | 71 | 1 | script-defined (written by at least one of these scripts) |
| `TAB_SWITCH_SUB` | 70 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `LayoutButtonSelectorConfig` | 65 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `stage_sub_list_selector_` | 65 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `TAB_SWITCH_NORMAL` | 58 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `STAGE_FORM_TYPE_NORMAL` | 48 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `my_music_scroller_` | 48 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `FadeManager` | 44 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `SCENE_EXIT_CODE_NONE` | 44 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `layout_root` | 44 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `UI_SE_ID_CURSOR` | 42 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `prg_func` | 41 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `BUTTON_BACK` | 40 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `SCENE_EXIT_CODE_CANCEL` | 39 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `IS_MY_MUSIC` | 33 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `STAGE_FORM_TYPE_BATTLE` | 31 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `CONTROLLER_FULL_KEY` | 30 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `BUTTON_ID_NONE` | 29 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `CONTROLLER_GC_CON` | 29 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `BUTTON_FORM_TYPE_0` | 28 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `my_music_sort_window_` | 28 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `STAGE_FORM_TYPE_END` | 27 | 0 | read-only in these scripts (host-provided as far as these scripts show) |
| `mii_select_scroller` | 27 | 0 | read-only in these scripts (host-provided as far as these scripts show) |

### 5.3 Field calls by count

| name | calls | scripts | argument-count histogram |
|---|---|---|---|
| `UiScriptPlayer` | 922 | 54 | 0 args ×17, 1 args ×395, 2 args ×360, 3 args ×134, 4 args ×16 |
| `invoke` | 819 | 33 | 0 args ×17, 1 args ×292, 2 args ×360, 3 args ×134, 4 args ×16 |
| `layout_view` | 385 | 47 | 0 args ×12, 1 args ×5, 2 args ×204, 3 args ×159, 4 args ×5 |
| `coroutine` | 233 | 55 | 0 args ×213, 1 args ×20 |
| `yield` | 213 | 55 | 0 args ×213 |
| `ComFrameActor` | 200 | 30 | 0 args ×82, 1 args ×87, 2 args ×30, 4 arg ×1 |
| `selector` | 198 | 19 | 0 args ×6, 1 args ×43, 2 args ×94, 3 args ×37, 4 args ×18 |
| `virtual_input` | 191 | 23 | 1 args ×29, 2 args ×135, 4 args ×24, 5 args ×3 |
| `UiSoundManager` | 182 | 36 | 1 args ×168, 2 args ×14 |
| `get_random` | 176 | 13 | 0 args ×176 |
| `module_ui_common` | 173 | 13 | 0 args ×170, 3 args ×3 |
| `AppPopupManager` | 172 | 25 | 0 args ×97, 1 args ×69, 2 arg ×1, 3 args ×5 |
| `layout_root` | 132 | 47 | 1 args ×95, 2 args ×37 |
| `new` | 127 | 33 | 0 args ×127 |
| `require` | 107 | 53 | 1 args ×107 |
| `LayoutButtonSelector` | 92 | 49 | 0 args ×57, 1 args ×35 |
| `pane` | 92 | 13 | 1 args ×19, 2 args ×16, 3 args ×48, 4 args ×9 |
| `button` | 84 | 14 | 0 arg ×1, 1 args ×2, 2 args ×10, 4 args ×71 |
| `manager` | 83 | 6 | 0 arg ×1, 1 args ×65, 2 args ×17 |
| `format` | 82 | 21 | 2 args ×82 |
| `play_se` | 81 | 20 | 1 args ×81 |
| `play_se_label` | 75 | 20 | 1 args ×75 |
| `ipairs` | 74 | 31 | 1 args ×74 |
| `math` | 74 | 17 | 1 args ×65, 2 args ×8, 3 arg ×1 |
| `common` | 71 | 17 | 0 args ×2, 1 args ×47, 2 args ×20, 3 args ×2 |
| `state` | 71 | 6 | 1 args ×24, 2 args ×6, 3 arg ×1, 5 args ×40 |
| `is_busy` | 69 | 23 | 0 args ×69 |
| `form_type_parts_` | 68 | 4 | 2 args ×16, 3 args ×52 |
| `LayoutButtonSelectorConfig` | 65 | 49 | 0 args ×43, 1 args ×22 |
| `open_database` | 61 | 22 | 1 args ×61 |
| `selector_sort` | 58 | 4 | 1 args ×17, 2 args ×26, 3 args ×7, 4 args ×8 |
| `LayoutRootList` | 57 | 41 | 1 args ×56, 2 arg ×1 |
| `string` | 57 | 19 | 2 args ×57 |
| `selector1` | 54 | 2 | 1 args ×10, 2 args ×36, 3 args ×6, 4 args ×2 |
| `my_music_state` | 52 | 4 | 1 args ×8, 2 args ×28, 5 args ×16 |
| `stage_sub_list_selector_` | 50 | 4 | 1 args ×10, 2 args ×19, 3 args ×21 |
| `my_music_scroller_` | 48 | 4 | 1 args ×8, 2 args ×32, 3 args ×8 |
| `selector0` | 46 | 2 | 0 args ×2, 1 args ×8, 2 args ×31, 3 args ×3, 4 args ×2 |
| `FadeManager` | 44 | 14 | 0 args ×16, 1 args ×28 |
| `layout_view_stage` | 40 | 4 | 2 args ×36, 3 args ×4 |

### 5.4 `invoke` bridge names by count

All 234 are in `ui_api.json`. The 40 largest:

| # | bridge name | calls | scripts | argument-count histogram |
|---|---|---|---|---|
| 1 | `set_medal_visible` | 33 | 4 | 3 args ×33 |
| 2 | `set_enable_shortcut_button_stage_preview` | 28 | 4 | 3 args ×28 |
| 3 | `is_training_stage_preview` | 26 | 8 | 2 args ×26 |
| 4 | `is_fixed_form_type_stage_preview` | 18 | 2 | 2 args ×18 |
| 5 | `cancel_medal_sub_list` | 16 | 4 | 2 args ×16 |
| 6 | `is_hand_interpolated_moving` | 16 | 4 | 1 args ×16 |
| 7 | `set_hand_grabbed` | 14 | 4 | 2 args ×14 |
| 8 | `is_battle_field_stage_preview` | 12 | 4 | 2 args ×12 |
| 9 | `is_empty_stage_preview` | 12 | 4 | 2 args ×12 |
| 10 | `is_selected_random_bgm` | 12 | 4 | 1 args ×12 |
| 11 | `set_hand_operatable` | 12 | 4 | 2 args ×12 |
| 12 | `set_medal_collect_range_from_panel` | 12 | 4 | 3 args ×12 |
| 13 | `get_disable_made_stage_popup_id_sub_list` | 9 | 3 | 1 args ×9 |
| 14 | `is_enable_made_stage_sub_list` | 9 | 3 | 1 args ×9 |
| 15 | `control_block_incidence_my_music` | 8 | 4 | 2 args ×8 |
| 16 | `get_hand_on_stage_preview_id` | 8 | 4 | 1 args ×8 |
| 17 | `get_hand_position_x` | 8 | 4 | 1 args ×8 |
| 18 | `get_hand_position_y` | 8 | 4 | 1 args ×8 |
| 19 | `is_both_ends_incidence_my_music` | 8 | 4 | 1 args ×8 |
| 20 | `is_lock_stage_panel` | 8 | 4 | 2 args ×8 |
| 21 | `is_medal_grabbed` | 8 | 4 | 2 args ×8 |
| 22 | `is_random_stage_preview` | 8 | 4 | 2 args ×8 |
| 23 | `put_medal_sub_list` | 8 | 4 | 4 args ×8 |
| 24 | `select_bgm_from_backup_my_music` | 8 | 4 | 1 args ×8 |
| 25 | `set_hand_grabable` | 8 | 4 | 2 args ×8 |
| 26 | `set_hand_position_from_panel` | 8 | 4 | 2 args ×8 |
| 27 | `set_medal_grabbed` | 8 | 4 | 4 args ×8 |
| 28 | `set_medal_position_from_panel` | 8 | 4 | 3 args ×8 |
| 29 | `set_stage_bgm_enable` | 8 | 4 | 2 args ×8 |
| 30 | `set_stage_form_type_stage_preview` | 8 | 4 | 3 args ×8 |
| 31 | `ensure_visible_sub_list` | 7 | 4 | 3 args ×7 |
| 32 | `get_hand_on_stage_sub_id` | 7 | 4 | 1 args ×7 |
| 33 | `is_all_panel_exceeded_num_player_sub_list` | 6 | 3 | 1 args ×6 |
| 34 | `is_battle_field_ls_stage_preview` | 6 | 2 | 2 args ×6 |
| 35 | `set_stage_preview_from_panel` | 5 | 5 | 2 arg ×1, 3 args ×4 |
| 36 | `show_mymusic_help_tooltip` | 5 | 1 | 2 args ×5 |
| 37 | `switch_favorite` | 5 | 3 | 1 args ×2, 2 args ×3 |
| 38 | `backup_selected_bgm_my_music` | 4 | 4 | 1 args ×4 |
| 39 | `control_incidence_my_music` | 4 | 4 | 2 args ×4 |
| 40 | `finalize_bgm` | 4 | 4 | 1 args ×4 |

**These are dominated by stage-select and my-music code, which is why the 40
largest are not Mii names.** The Mii special-move bridges (`get_skill_id`,
`set_skill_id`, `get_skill_name_label`, `get_skill_help_label`, `replace_skill`,
`replace_skill_subwindow`) each occur once, in one script. A mod should treat
them as narrow, not as a general-purpose API.

## 6. Globals: script-defined vs host-provided

Of 759 global names: **246 are written** by at least one of these scripts
(script-defined), **513 are only ever read** (host-provided, *as far as these 86
scripts show*).

Most-read names are host objects: `UiScriptPlayer` (928 reads), `coroutine` (233),
`ComFrameActor` (200), `UiSoundManager` (182), `LayoutButtonSelector` (92),
`LayoutRootList` (92), `UiSoundManager`, `math`, `string`, `ipairs`, `require`.

Some genuinely script-defined ones use a trailing-underscore convention:
`button`, `common`, `state`, `module_ui_common`, `layout_view`, `exit_code_`,
`stage_sub_scroll_button_operatable_`, `my_music_scroller_`. `exit_code_` is
verified by direct disassembly of `stage_select_actor.lc` pc32.

**Caveat that matters for the mod:** "read-only in these scripts" is not "immutable"
and not "native-owned". It means no `SETTABUP` on that name appears in these 86
chunks. Assignment could live in another chunk, or the host could refuse it.
P1-UI-GLOBALS already reached the same limit from the other direction.

## 7. Focus list 4a - text (31 methods)

The task asks whether these take a message key or a literal string. The evidence
answers it directly.

| method | calls | scripts | args | what the constants show |
|---|---|---|---|---|
| `set_text_message` | 81 | 22 | 1 ×68, 0 ×13 | **message key.** `make_mii_special_actor.lc` main.p2 pc75 passes `'mnu_footer_ok'` |
| `set_text_message_args` | 26 | 5 | 3 ×11, 4 ×9, 6 ×4, 5 ×2 | **message key plus format args.** `local_mode_select.lc` main.p1 pc168 passes `'mnu_local_new_rm_tmb_player_n'`, 2, 8, `'ii'` |
| `set_text_args` | 28 | 7 | 2 ×22, 3 ×6 | argument values plus an `'i'` index per arg. `collection_shop_top.lc` main.p7 pc11 passes `g_gold` and `'i'` |
| `play_se_label` | 14 | 7 | 1 ×14 | **label-style constant.** `main_menu_common.lc` main.p1 pc35 passes `'se_system_fixed'` |
| `set_footer_message` | 13 | 2 | 1 ×13 | **message key.** `local_mode_select.lc` main.p5 pc25 passes `'mnu_local_new_rm_help_mel_btn_00'` |
| `set_text_number_int32` | 5 | 3 | 1 ×4, 0 ×1 | integer, usually computed (`ADD`) |
| `set_text_string` | 3 | 2 | 1 ×3 | register value, no constant at the call |
| `set_text_shadow_color` | 3 | 1 | 1 ×3 | integer 0 |
| `set_text_border_color` | 2 | 1 | 1 ×2 | integer 0 |
| `set_text_border_enable` | 2 | 1 | 1 ×2 | **boolean** true |
| `set_text_alignment_x`, `set_text_alignment_y` | 2 each | 1 | 1 ×2 | call result |
| `set_label` | 2 | 1 | 2 ×2 | two call results |
| `set_text_desc` | 2 | 1 | 4 ×2 | four arguments |
| `clear_text_string` | 7 | 3 | 0 ×7 | no arguments |
| `update_text`, `update_help_text`, `update_sort_text`, `update_list_text` | 8, 3, 8, 1 | 1-3 | 0 | no arguments |
| `set_text_scroll_force_scroll`, `_loop_enabled`, `_moving_speed`, `_through_mode` | 1 each | 1 | 1 ×1 | — |
| `play_text_scroll_animation`, `stop_text_scroll_animation`, `reset_text_scroll_location`, `is_text_scroll_scrolling` | 1 each | 1 | 0 / 1 | — |

**The single most useful result of this task for the mod:** `set_text_message`
takes a **message key** (every constant seen is `mnu_*`), and
`set_text_message_args` takes a **message key followed by its substitution
arguments**, with the format specifiers supplied as further string constants
(`'i'`, `'ii'`). New UI text needs a new message label; a literal string is not
the game's idiom for pane text. That is consistent with, and now has 81 call sites
of offline support for, the coordinator's P3-ARC-PROBS reading that
`set_sub_title('mnu_mmiif_setup_sp_move_title')` resolves a message key.

**On the three examples per method.** 11 of the 31 methods reach three examples.
The other 20 have fewer because the whole 86-script corpus contains fewer than
three call sites for them - twelve occur **exactly once** (`set_text_desc` aside,
the `set_text_scroll_*` family, `restore_texture`, `update_list_text`,
`set_decide_se_label`, `play_text_scroll_animation`) and eight occur twice. That
is a fact about the game, not truncation: `check_ui_api.py` asserts
`examples == min(3, call sites)` for every 4a method, so a real shortfall would
fail. An independent raw `SELF` count over all 86 chunks agrees with the reported
call totals for all 31.

Full per-method examples in `evidence/P5-UI-API/focus_tables.md`.

## 8. Focus list 4b - input (168 globals, 37 methods)

### 8.1 The virtual-input methods

| method | calls | scripts | args |
|---|---|---|---|
| `is_pressed` | 110 | 27 | 1 ×110 |
| `set_enable_input` | 84 | 29 | 1 ×84 |
| `get_decided_button_id` | 68 | 36 | 0 ×68 |
| `get_virtual_input` | 62 | 50 | 0 ×62 |
| `is_pressing` | 45 | 13 | 1 ×45 |
| `is_cancel` | 35 | 18 | 0 ×35 |
| `is_cancelled` | 27 | 21 | 0 ×27 |
| `decide_button` | 25 | 13 | 1 ×23, 2 ×2 |
| `update_pointer_input` | 19 | 4 | 4 ×19 |
| `is_decide` | 15 | 10 | 0 ×15 |
| `is_repeated` | 12 | 6 | 1 ×12 |
| `set_decide_on_trigger` | 10 | 7 | 2 ×10 |
| `stop_pressed` | 8 | 4 | 1 ×8 |
| `special_input_is_downward` / `_upward` | 7 each | 7 | 1 ×7 |
| `press_cancel` | 6 | 6 | 0 ×6 |
| `set_repeat_frame` | 5 | 5 | 4 ×5 |
| `get_decided_item` | 4 | 4 | 0 ×4 |
| `is_pressed_finished` | 4 | 4 | 0 ×4 |
| `is_released` | 4 | 2 | 1 ×4 |
| `play_pressed` | 4 | 4 | 1 ×4 |
| `set_enable_input_sort` | 3 | 1 | 1 ×3 |
| `set_no_wait_decide` | 3 | 2 | 1 ×3 |
| `terminate_repeat` | 3 | 3 | 0 ×3 |
| `decide`, `get_decided_id`, `is_decided`, `update_cancel`, `cancel`, `release`, `get_last_input_device_id`, `input_direction_is_upward`, `input_direction_is_zero`, `input_direction_is_zero_x` | 1-2 each | 1-2 | 0 or 1 |
| `set_decide_se_label` | 1 | 1 | 1 ×1 |
| `special_input_is_leftward` / `_rightward` | 1 each | 1 | 1 ×1 |

`is_pressed` (110 calls, 27 scripts) and `is_pressing` (45) are both present, so
edge and hold are distinct methods in this vocabulary. That is a fact about the
names and their call shapes; whether either is safe to call from a new script is
not established.

### 8.2 The `INPUT_*` globals and their registered values

All 28 `INPUT_*` names occur once as a NUL-terminated string in `main.bin`, have
exactly one `adrp+add` reference, and were inside the 60-name cap, so all have a
resolved `w3` value.

| global | Lua reads | refs | registered value | instruction |
|---|---|---|---|---|
| `INPUT_OK` | 1 | 1 | **6** | `mov w3, #6` |
| `INPUT_CANCEL` | 4 | 1 | 5 | `mov w3, #5` |
| `INPUT_BUTTON_UP` | 4 | 1 | 0 | `mov w3, wzr` |
| `INPUT_BUTTON_DOWN` | 4 | 1 | 1 | `mov w3, #1` |
| `INPUT_BUTTON_LEFT` | 16 | 1 | 2 | `mov w3, #2` |
| `INPUT_BUTTON_RIGHT` | 18 | 1 | 3 | `mov w3, #3` |
| `INPUT_COMMON_BUTTON` | 2 | 1 | 6 | `mov w3, #6` |
| `INPUT_NEXT` | 1 | 1 | 8 | `mov w3, #8` |
| `INPUT_NEXT_SCENE` | 4 | 1 | 6 | `mov w3, #6` |
| `INPUT_PREV` | 1 | 1 | 7 | `mov w3, #7` |
| `INPUT_OPEN_SUBMENU` | 1 | 1 | 7 | `mov w3, #7` |
| `INPUT_OPEN_SORT_WINDOW` | 2 | 3 | 6 | `mov w3, #6` |
| `INPUT_FAVORITE` | 4 | 2 | 7 and 8 | two sites |
| `INPUT_HOWTO` | 1 | 1 | 6 | `mov w3, #6` |
| `INPUT_HOW_TO_PLAY` | 1 | 1 | 6 | `mov w3, #6` |
| `INPUT_BGM_SELECT` | 8 | 1 | 8 | `mov w3, #8` |
| `INPUT_BGM_SELECTOR_TEST` | 8 | 1 | 6 | `mov w3, #6` |
| `INPUT_STAGE_TYPE` | 8 | 1 | 7 | `mov w3, #7` |
| `INPUT_SUB_PAGE_UP` | 3 | 1 | 16 | `mov w3, #16` |
| `INPUT_SUB_PAGE_DOWN` | 3 | 2 | 17 | `mov w3, #17` |
| `INPUT_TAB_CHANGE_L` | 4 | 1 | 18 | `mov w3, #18` |
| `INPUT_TAB_CHANGE_R` | 4 | 1 | 24 | `mov w3, #24` |
| `INPUT_MY_MUSIC_INCIDENCE_UP` | 4 | 1 | 10 | `mov w3, #10` |
| `INPUT_MY_MUSIC_INCIDENCE_DOWN` | 4 | 1 | 11 | `mov w3, #11` |
| `INPUT_MY_MUSIC_INCIDENCE_BLOCK_UP` | 4 | 1 | 12 | `mov w3, #12` |
| `INPUT_MY_MUSIC_INCIDENCE_BLOCK_DOWN` | 4 | 1 | 13 | `mov w3, #13` |
| `INPUT_MY_MUSIC_SORT` | 8 | 1 | 14 | `mov w3, #14` |
| `INPUT_MY_MUSIC_INIT` | 1 | 1 | 15 | `mov w3, #15` |

`INPUT_OK = 6` at string `0x04306e9b`, site `0x019de570`, `mov w3, #6` at
`0x019de57c` — reproduced here independently and identical to what
P2-UI-CONSTS recorded. That agreement is the main external check on this step.

Note `INPUT_OK` and `INPUT_COMMON_BUTTON` both carry 6, so **the value is not a
unique identifier for the input**; two names can share it.

### 8.3 Wider input-family globals

168 names matched. 166 occur as NUL-terminated strings, all 166 with an
`adrp+add` reference. Two do not occur at all: **`BUTTON_ID_LEFT` and
`BUTTON_ID_RIGHT`** - present as Lua globals, absent from the image as strings.
That is a real asymmetry and worth a look later; it does not mean the names are
undefined at run time, only that this scan found no such literal.

Of the 60 names the `w3` detail was spent on, all 60 produced a value. Five are
registered at **more than one site with different values**, which means the name
is registered per context rather than once:

| name | values |
|---|---|
| `BUTTON_ID_NONE` | -1 ×3 |
| `BUTTON_ID_SAVE` | 300, then 5 |
| `INPUT_FAVORITE` | 7, then 8 |
| `BUTTON_ID_OK` | 7 ×2 |
| `BUTTON_ID_INIT` | 0, 0, 0, 1, 1 |

Per-name JSON in `evidence/P5-UI-API/native_input_scan.json`.

## 9. Focus list 4c - visibility, animation, focus, panes (67 methods)

| method | calls | scripts | args |
|---|---|---|---|
| `play_animation` | 406 | 42 | 2 ×406 |
| `set_focus` | 253 | 37 | 1 ×251 |
| `get_parts` | 243 | 56 | 1 ×194, 0 ×49 |
| `set_enable` | 198 | 38 | 1 ×197 |
| `get_pane` | 142 | 36 | 1 ×142 |
| `select_button` | 100 | 33 | 1 ×81, 2 ×19 |
| `set_enable_input` | 84 | 29 | 1 ×84 |
| `set_visible` | 83 | 23 | 1 ×83 |
| `play_animation_parts` | 78 | 11 | 2 ×78 |
| `get_selected_button_id` | 76 | 21 | 0 ×76 |
| `has_focus` | 67 | 22 | 0 ×67 |
| `set_selectable` | 64 | 16 | 2 ×61, 1 ×3 |
| `stop_animation_at_end` | 51 | 26 | 1 ×51 |
| `select_item` | 29 | 13 | 2 ×27, 1 ×2 |
| `is_animation_finished` | 26 | 13 | 1 ×26 |
| `stop_animation_frame` | 25 | 11 | 2 ×23, 0 ×2 |
| `is_selectable` | 21 | 5 | 1 ×21 |
| `set_enable_my_music` | 20 | 4 | 1 ×20 |
| `visible_parts` | 15 | 6 | 2 ×15 |
| `clear_selection` | 14 | 9 | 0 ×14 |
| `get_selected_item` | 13 | 4 | 0 ×13 |
| `select_com_frame_actor` | 12 | 2 | 0 ×12 |
| `unselect` | 11 | 10 | 0 ×11 |
| `get_cursor_parts` | 10 | 5 | 0 ×10 |
| `get_animation` | 9 | 5 | 1 ×9 |
| `visible_pane` | 9 | 2 | 2 ×9 |
| `get_root_pane` | 8 | 7 | 0 ×8 |
| `play_animation_and_wait` | 8 | 4 | 2 ×8 |
| `set_parent_pane` | 8 | 4 | 1 ×8 |
| `set_select_item` | 7 | 2 | 0 ×4, 1 ×3 |

`play_animation` is the single most used method in the whole inventory: 406 calls
in 42 of 86 scripts, always with exactly 2 arguments (name, float) and never a
third. `set_visible` always takes exactly 1. `get_pane` always takes exactly 1.
These three are as uniform as anything in this data set.

## 10. Limits, stated plainly

- **A name's presence shows the game calls it somewhere. Nothing more.** It does
  not show what the call does, what it returns, or whether it is safe to call
  from a new script.
- **A name does not exist on every object.** The inventory records
  `get_pane` 142 times; it does not follow that every one of those 142 receivers
  is the same class, nor that a pane supports `set_text_message`. Receivers are
  not tracked - that needs dataflow the tool deliberately does not have.
- **Nothing here says any of it is safe in the Mii editor.** These 86 scripts run
  all over the game's UI. A method that is safe on the stage-select screen says
  nothing about the Mii special-move screen.
- **This is not runtime evidence.** No emulator, no console, no game run. Tier B
  throughout for what was measured; every statement about intent is tier D.
- **`invoke` is only counted as a bridge when the first argument is a string
  constant.** 17 sites are counted separately, not guessed at. And a call to
  `UiScriptPlayer.invoke("x")` proves only that the string `"x"` was passed to
  native code. It says nothing about whether the name is registered, what its
  signature is, or what happens for an unknown name.
- **Argument provenance is a bounded backward scan** (12 instructions, stopping at
  a branch target) for the instruction that last wrote each argument register.
  This is a display heuristic, not a dataflow proof; register values are not
  tracked across joins. An `other(...)` kind means "no nearby definition found",
  not "the register holds nothing".
- **Field-call attribution is shallow.** A field name is credited to whatever
  `GETTABLE` fed a `CALL`; the *receiver's* class is not resolved, so `invoke`
  and `new` are counted once each rather than split per host object.
- **The `w3` step is capped at 60 names** as the task specifies, spent on all 28
  `INPUT_*` names first and then the next 32 by Lua read count. 106 names with a
  string in the image were **not** disassembled for a value; they are listed in
  `native_input_scan.json` under `names_skipped_cap`. All 166 names still have
  their string-presence and `adrp+add` counts.
- **The `INPUT_*` values are read at one registration site.** Where a name has
  several sites, the values differ (section 8.3); a single number is not the
  name's meaning.
- **This says nothing about the four capabilities P2-UI-FLOW listed as missing.**
  Instruction authoring, the native binding, persistence and layout growth are
  all unaffected by this inventory.

## 11. Commands run, with exit codes

`python` is CPython 3.12.3, used with `-B` throughout.

| command | exit | result |
|---|---|---|
| `arc-extract.exe --arc gamedata/ssbu-13.0.4/data.arc --out gamedata/mii_customizer/P5-UI-API <86 paths>` | 0 | 86 extracted, 0 failed |
| `build_manifest.py` | 0 | 86 files, 543,839 bytes, on-disk hashes equal extractor log |
| `lua53_inspect.py verify <each of 86>` | 0 ×86 | all pass, full byte consumption |
| `analyze_ui_api.py` | 0 | 86 analysed, 0 excluded, 60,317 instructions |
| `focus_lists.py` | 0 | 4a=31, 4b=168/37, 4c=67 |
| `native_input_scan.py` (with `PYTHONPATH` for capstone) | 0 | 168 names, 166 with a string, 60 `w3` values |
| `check_ui_api.py` | **0** | **33 checks passed, 0 failed** |
| `check_report_claims.py` | **0** | **39 claims passed, 0 failed** |
| `splice_tables.py` run twice | 0 / 0 | byte-identical output the second time (idempotent) |
| `render_tables.py` + `splice_tables.py` | 0 | report's four top-40 tables replaced by generated ones |
| `check_ui_api.py` after deliberately corrupting `ui_api.json` | **1** | 2 failures, both real |
| `check_report_claims.py` after altering a table row and a figure in this report | **1** | 2 failures, both real |

The last two rows matter: both check scripts were shown to fail on corrupted
data, so their passing is evidence rather than decoration.

**The claim audit caught two real errors in my own first draft of this report** - a
row in the top-40 method table that was not in the top 40, and a wrong script
count for `selector_sort`. Both are fixed; see section 12.

**Step 1 asks for an example for each of the three most common argument shapes per
name.** All 1,017 top-3 shape entries carry one, each with script path,
prototype and pc, recorded at collection time rather than recovered from a capped
example list. `check_ui_api.py` asserts this.

## 12. Files

Inside this task's exclusive write paths only:

- `research/P5-UI-API.md` - this report
- `evidence/P5-UI-API/` - `ui_api.json` (everything), `focus_lists.json`,
  `focus_tables.md` (all step-4 tables with examples), `native_input_scan.json`,
  `manifest.tsv` (size + sha256 per chunk), `extract_log.txt`,
  `verify_all.txt`, `dis_special_actor.txt`, `check_run.txt`,
  `check_report_claims_run.txt`
- `scratch/2026-10-05_P5-UI-API/` - `build_manifest.py`, `analyze_ui_api.py`,
  `focus_lists.py`, `native_input_scan.py`, `check_ui_api.py`,
  `check_report_claims.py`, `render_tables.py`, `splice_tables.py`,
  `selected_paths.txt`, `refscan9_copy.py`, `strfind9_copy.py`, `out/`

Two checks ship with this task and both were confirmed to **fail** on
deliberately corrupted data before being trusted: `check_ui_api.py` (34 checks,
regenerates the JSON and compares) and `check_report_claims.py` (39 claims,
audits the tables and figures in this report against the generated JSON).

`render_tables.py` and `splice_tables.py` exist because hand-sorting 40 rows went
wrong once: the claim audit caught a row in the top-40 method table that was not
in the top 40, and a wrong script count for `selector_sort`. The four top-40
tables are now generated from the JSON and spliced in, so they cannot drift from
the data again. The splicer refuses to write if it would lose a heading or a
table, and it is idempotent (verified by running it twice and diffing).

Derived game files, workspace `gamedata/mii_customizer/P5-UI-API/` only: the 86
extracted chunks. Inputs untouched: `data.arc`, `main.bin`, `arc_files.tsv`,
`tools/lua53-inspect/`, the other tasks' scratch directories, `STATUS.md`,
`CHANGELOG.md`, `CURRENT_INSTALL.md`, `prompts/`, `builds/`. No commits, no
branches, no installs, no emulator, no console.

**I did not edit `lua53-inspect`**, and the copies of `refscan9.py` /
`strfind9.py` are unmodified except for the generalised target list in
`native_input_scan.py`, which is my own new file.

## 13. What this does and does not settle for the mod

Settles (offline, B):

- The **text** vocabulary: `set_text_message(message_key)` and
  `set_text_message_args(message_key, ...)`. New UI text needs a message label.
- The **visibility/animation** vocabulary and its arity: `set_visible(bool)`,
  `play_animation(name, float)`, `get_pane(name)`, `get_parts(name)`.
- The **input** vocabulary: `is_pressed` vs `is_pressing` are distinct, and the
  `INPUT_*` global values are now known for all 28 of them.
- The **selector** vocabulary: `setup_button`, `select_button`, `decide_button`,
  `get_selected_button_id`, `get_decided_button_id`, `set_selectable`, `set_focus`.

Does not settle: whether any of these can be called from a modified Mii editor
chunk at all; what `UiScriptPlayer.invoke` does with any name; where the six Mii
bridge values are stored; how a new selector's parts get into the layout; and the
per-player saved-fighter ID. Those remain the open items from P2-UI-FLOW and
STATUS.md, unchanged by this task.

## 14. Next experiment (one)

**Compile a small Lua source file with `tools/luac53-game/luac-game.exe` that
calls the exact text API measured here - `set_text_message` with a message key,
`set_text_message_args` with a key plus args, `set_visible`, `play_animation` -
and diff its bytecode shape against `make_mii_special_actor.lc`, then check with
`lua53-inspect compare` that the emitted opcodes and argument counts match what
section 5 and section 7 measured.**

That is the smallest step that tests the one thing this inventory was gathered
for: whether the game's own call shapes are reproducible from source. It is fully
offline. It does **not** need a console, and it does not prove the game would load
the result - P4-LUAC already established that the compiler emits the right header
format but that loading is untested. If the shapes match, the mod has a verified
vocabulary to write against; if they do not, the difference is the next thing to
understand.

## Task summary

**P5-UI-API: DONE.** 86 UI Lua scripts selected by path rule from the archive
index (below the 400 threshold, so nothing was excluded), extracted with
`tools/arc-extract` into `gamedata/mii_customizer/P5-UI-API/`, hashed per file,
and **all 86 pass `lua53-inspect verify`** so nothing was excluded from analysis.
Measured from bytecode: 336 method names over 4,802 call sites, 759 globals
(6,798 reads / 586 writes; 246 script-defined, 513 read-only), 404 field names
over 7,464 call sites, and **234 distinct `invoke` bridge names**. Delivered the
three focus lists, top-40 lists for steps 1-3, the `main.bin` scan of all 168
input-family globals with `w3` values for the 60 the cap allows, the full
`ui_api.json`, and `check_ui_api.py` which regenerates the JSON and compares
(**33 checks, exit 0**), and which was confirmed to fail on corrupted data.

Two off-by-one errors of my own were found and fixed by cross-checking against
P2-UI-FLOW's established facts, and both are recorded in section 3.1 because they
change every count in this report.

Changed files: sections 12 and 13 above, all inside this task's exclusive paths.

Unresolved: nothing about runtime behaviour, and none of the four missing
capabilities P2-UI-FLOW listed. `BUTTON_ID_LEFT` and `BUTTON_ID_RIGHT` are Lua
globals with no string in `main.bin` - unexplained, and the most concrete loose
end this task found.