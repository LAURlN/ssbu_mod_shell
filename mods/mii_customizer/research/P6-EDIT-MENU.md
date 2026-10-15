# P6-EDIT-MENU - how the Mii maker's main edit menu defines its entries and opens sub-screens

Task: tracing only. No file was edited. **DONE.**

Evidence tier: everything below is **B** (offline measurement of the pinned inputs) unless a
line is marked **D** (hypothesis). There is no tier A or C evidence here and no runtime claim.

---

## 0. Inputs, hashes and commands

### Inputs (all read-only, workspace-relative)

| path | size | sha256 |
|---|---|---|
| `gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc` (the chunk the game loads) | 10576 | `c777ecc492cea48f6ffd40112b22f96e66219d00969b570a7cc3cf8d7f4a9417` |
| `gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_edit_actor.lc` (base) | 10321 | `1f73dff133961b68dbe24641298229b9f3905a44703164563911b105eaa16908` |
| `gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc` | 927100 | `f4bf2ef0db472eb341d76c70f3ec770ae58598fff3f53d2aced7170fb4ebf212` |
| `gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_edit/blyt/make_mii_edit.bflyt` | 21004 | (the `.bflyt` member inside the archive above) |

The layout archive was **already present** under `P1-UI/`, and an unpacked copy already existed
under `P1-LAYOUT/unpacked/`, so nothing had to be extracted into `gamedata/mii_customizer/P6-EDIT-MENU/`
(that folder was created and left empty). All three tool sets were used read-only.

The prompt's expected hash for the patch chunk reproduces exactly. The base chunk and the layout
archive hashes above were measured here for the first time.

### Commands run (from the workspace root)

```bash
T=mods/mii_customizer/tools
P=gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc
B=gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_edit_actor.lc
E=gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc
X=gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_edit/blyt/make_mii_edit.bflyt
S=mods/mii_customizer/scratch/2026-10-05_P6-EDIT-MENU

python $T/lua53-inspect/lua53_inspect.py header   $P $B > $S/header.txt
python $T/lua53-inspect/lua53_inspect.py verify   $P            # exit 0, 11 checks
python $T/lua53-inspect/lua53_inspect.py summary  $P
python $T/lua53-inspect/lua53_inspect.py dis      $P > $S/dis_patch.txt
python $T/lua53-inspect/lua53_inspect.py compare  $B $P > $S/compare.txt
$T/luac53-game/bin/luac-game.exe -l -l -o $S/nul.bin $P > $S/luac_patch.txt
$T/luac53-game/bin/luac-game.exe -l -l -o $S/nul.bin $B > $S/luac_base.txt
python $T/sarc-layout/sarc_layout.py list $E > $S/layout_members.txt
python $T/bflyt-inspect/bflyt_inspect.py groups      $X > $S/groups.txt
python $T/bflyt-inspect/bflyt_inspect.py parts $X set_item > $S/parts_setitem.txt
python $T/bflyt-inspect/bflyt_inspect.py crosscheck  $X > $S/crosscheck.txt
python $S/check_p6_edit_menu.py > $S/check_run.txt            # exit 0, 264 checks
```

### Numbering convention (matters when reading this report)

Every `pc` and constant index below is **as `luac-game -l -l` prints it**: instructions are
**1-based** and constants are **1-based**. `lua53_inspect` uses 0-based lists internally; the
check script converts, so the numbers here are the numbers a reader sees in a `luac` dump and
are checked against the real chunk bytes.

Prototype names follow `lua53_inspect`: `main` is the top-level chunk, `main.pN` the Nth nested
prototype in file order. `main.p11` is `initialize` (225 instructions), which is where the whole
menu is built.

### Verification of this report

`scratch/2026-10-05_P6-EDIT-MENU/check_p6_edit_menu.py` re-derives every cited pc, opcode,
constant index, operand, upvalue-to-register resolution, group count, group member offset, part
offset, part position, part extent, part child count, owner-layout reference, message id and
animation count.

```
264 checks, 264 passed, 0 failed     -> exit 0
```

Mutation control (each mutant was written to a copy, run, and the original restored):

| mutant | change | result |
|---|---|---|
| `mut1_pc` | cited constant 45 -> 44 | exit 1, `FAIL p11 pc107 format template K45 == 'set_item_%02d'` |
| `mut2_layout` | cited part offset `0x2498` -> `0x2499` | exit 1, `FAIL part set_item_04 offset 0x2499 -- 0x2498` |
| `mut3_op` | opcode at `p4` pc25 `SELF` -> `MOVE` | exit 1, `FAIL p4 pc25 SELF 'get_decided_button_id'` |
| `mut4_count` | `selector_0` member count 8 -> 7 | exit 1, `FAIL selector_0 has 8 members -- 8` |
| `mut5_anim` | `make_mii_btn0_02_special` typo'd -> 0 matches | exit 1, `FAIL exactly 4 animations name make_mmi_btn0_02_special -- 0` |
| `mut6_reg` | main register 4's value 4 -> 3 | exit 1, 3 failures, first `FAIL main.p11 upvalue[5] resolves to main register 4 (== 4)` |
| `mut7_upval` | `p6` pc125 upvalue slot 3 -> 4 | exit 1, `FAIL p6 pc125 reads upvalue[3] (the park row)` |
| `mut8_label` | `mnu_mmiif_setup_hat_01` -> `..._09` | exit 1, `FAIL part set_item_01 carries its message ids -- missing [...]` |
| `mut9_spmove` | "five distinct sp_move ids" 5 -> 4 | exit 1, `FAIL menu-entry table: set_item_04 carries five distinct sp_move ids` |
| `mut10_order` | `IS_READ_ONLY` read before `IS_SKILL_EDITABLE` -> inverted | exit 1, 4 failures, first `FAIL main.p5: IS_READ_ONLY (pc191) is read before IS_SKILL_EDITABLE` |
| `mut11_rowid` | the 0b table's "row 4 is the IS_SKILL_EDITABLE row" -> 5 | exit 1, `FAIL menu-entry table: row 4 is the IS_SKILL_EDITABLE row` |

**11 of 11 mutants are caught**: non-zero exit, at least one `FAIL`, and no traceback. Each mutant
was run from a throwaway copy so the script under test was never overwritten.

One further mutation was tried and deliberately **not** counted: disabling the bounds check in the
script's own `rk_const` helper is **not** detected, because that guard is defensive and this
chunk never exercises it. The scan that uses it only visits comparison opcodes, and none of the
87 comparisons in the chunk has an out-of-range RK operand. A related trap is documented in the
code: 8 operands in this chunk have `B >= 256`, and all 8 are `JMP` / `FORLOOP`, whose `B` and `C`
are halves of `Bx` rather than RK operands. An opcode-blind scan reports them as 8 phantom bad
constant references - the same defect class P2-LUA-EDIT fixed in `lua53-inspect`.

Outputs are in `evidence/P6-EDIT-MENU/mutation_*.out`, and the unmutated script that was actually
run is kept alongside them as `mutation_control_original.py`.

An earlier version of this script was written against guessed tool APIs and against guessed
expectations (87 animations, 6 parts, one `LayoutButtonSelector` constant, `RETURN` using operand
`C`). Seven of those guesses were wrong and the run caught them. The corrected values are all in
the table above; this is recorded because it is the failure mode a reader should expect from any
claim list that is not re-derived.

Two further defects in the harness itself were found and fixed this way rather than worked
around: an off-by-one that read constants with `luac`'s 1-based numbers against the tool's 0-based
list, and an opcode-blind RK scan that would have reported 8 phantom bad references. Both are
noted so a later reader does not reintroduce them.

---

## 0b. The menu entry table

The one table the task asks for. "Action when decided" is identical for all six rows because the
script has **no per-row branch** (section 2); the per-row difference is in *which* row the game
shows, which is not in this chunk (D).

| index | part name | label source (message ids in the layout) | condition | action when decided |
|---|---|---|---|---|
| 0 | `set_item_00` | `mnu_mmiif_setup_fighter_nam_00`, `..._01` | `IS_READ_ONLY` -> `set_selectable(0, false)`; `!IS_READ_ONLY && !IS_SKILL_EDITABLE` -> whole `selector0` `set_enable(false)`; otherwise selectable | `self.exit_value = selector0:get_decided_button_id()` -> 0 (`p4` pc24-27), then `p10` closes the screen |
| 1 | `set_item_01` | `mnu_mmiif_setup_hat_00`, `..._01` | same as row 0 | same, value 1 |
| 2 | `set_item_02` | `mnu_mmiif_setup_outfit_00`, `..._01` | same as row 0 | same, value 2 |
| 3 | `set_item_03` | `mnu_mmiif_setup_color` | same as row 0 | same, value 3 |
| 4 | `set_item_04` | `mnu_mmiif_setup_sp_move_00` .. `_04` (five ids) | `IS_READ_ONLY` -> not selectable (row 0 rule wins); `IS_SKILL_EDITABLE` -> `set_selectable(4, true)` **and** `select_button(4)`, so the cursor lands here; `!IS_SKILL_EDITABLE` -> whole `selector0` `set_enable(false)` | same, value 4. **This is the special-move screen's entry.** |
| 5 | `set_item_05` | `mnu_mmiif_setup_voice_00`, `_01`, `_02` | `IS_READ_ONLY` -> not selectable; otherwise selectable (also the default landing row from the read-only-**off** left-press path, `p6` pc137-145) | same, value 5 |
| sel0 / 0 | `btn_other_random` | (in `make_mii_btn2_00_try.bflyt`) | `set_selectable(0, false)` at start (`p11` pc171-175) | `self:update_random()` -> `invoke("set_random")`, directly or after popup `ID_POPUP_MMIIF_EDIT_RANDOM` (`p5` pc26-32, `p8`) |
| sel0 / 1 | `btn_other_try` | (in `make_mii_btn2_00_try.bflyt`) | `FROM_AMIIBO` -> part `set_visible(false)`; else present and the focused row | `self.exit_value = 6` + `play_se(UI_SE_ID_DECIDE)` (`p5` pc34-44). **6 is the value `p10` pc62-64 special-cases.** |

Reading the condition column: `IS_READ_ONLY` is checked **first** at every site and always wins
over `IS_SKILL_EDITABLE`. The patch's whole change is that `IS_SKILL_EDITABLE` exists at all - 4
occurrences in the patch, **0** in the base.

---

## 1. Selectors and buttons

`initialize` (`main.p11`) builds exactly **two** `LayoutButtonSelector` objects. Both are
created through `LayoutButtonSelector.new()`, stored in the module table as `selector0` and
`selector1`.

| # | created at | stored as | `setup` call | group name passed to `setup` | `setup_button` calls |
|---|---|---|---|---|---|
| 1 | pc88-91 (`GETTABUP` -> `GETTABLE "new"` -> `CALL` -> `SETTABUP`) | `selector0` (K37) | pc93-97, `CALL` with B=5 (4 args: self, view, group, config) | **`selector_0`** (K40) | pc102-110, **a loop** -> 6 buttons, names built by `string.format("set_item_%02d", i)` |
| 2 | pc121-124 | `selector1` (K49) | pc126-130, `CALL` with B=5 | **`selector_1`** (K50) | pc132-135 (index 0, `btn_other_random`) and pc137-140 (index 1, `btn_other_try`) |

`LayoutButtonSelector` itself is a **single deduplicated constant** (K38 of `main.p11`), used by
both sites. The three `GETTABLE "new"` sites in `initialize` are pc81 (the
`LayoutButtonSelectorConfig`), pc89 (`selector0`) and pc122 (`selector1`).

There is a third object created here, `LayoutButtonSelectorConfig.new()` at pc80-82. It is not
a selector. It is built once, mutated between the two selectors (pc116-120 clears
`decide_se_label_code`, `cancel_se_label_code` and `error_se_label_code`, keeps
`cursor_se_label_code = "se_system_cursor"`, and sets `use_cursor_looping = false`), and the
**same table object** is passed to both `setup` calls.

### The button loop, and why there are six buttons

```
pc98   LOADK    R6 <- 0                  -- loop start value
pc99   GETUPVAL R7 <- upvalue[2]         -- loop limit
pc100  LOADK    R8 <- 1                  -- step
pc101  FORPREP  R6, 9                    -- to pc111, body pc102
pc102  GETTABUP R10 <- selector0
pc103  SELF     R10 = selector0.setup_button
pc104  MOVE     R12 <- R9                -- the loop index i
pc105  GETTABUP R13 <- string
pc106  GETTABLE R13 = string.format
pc107  LOADK    R14 <- "set_item_%02d"
pc108  MOVE     R15 <- R9
pc109  CALL     string.format            -- "set_item_%02d", i
pc110  CALL     selector0.setup_button(i, name)
pc111  FORLOOP  R6, -10                  -- back to pc102
```

The limit is `upvalue[2]`, which `p11`'s upvalue table resolves to **main's register 3**
(`upvalues[2] == (1, 3)`), and main pc13 is `LOADK R3 <- K6` where **K6 == 5** (B).

Lua's numeric `for` with start 0, limit 5, step 1 is inclusive at both ends, so the loop body
runs **6 times**, for `i = 0..5`. That yields:

| button index | part name | parent group |
|---|---|---|
| 0 | `set_item_00` | `selector_0` |
| 1 | `set_item_01` | `selector_0` |
| 2 | `set_item_02` | `selector_0` |
| 3 | `set_item_03` | `selector_0` |
| 4 | `set_item_04` | `selector_0` |
| 5 | `set_item_05` | `selector_0` |

**Which selector is the main menu the player navigates:** `selector0`, over the six `set_item_NN`
rows. `selector1` is a two-button pair (`btn_other_random`, `btn_other_try`) that shares the
screen with it; `main.p4` (`update_selector0`) returns early unless `selector0.has_focus()`, and
`main.p5` (`update_selector1`) returns early unless `selector1.has_focus()`.

Note that `set_item_04` has **no literal string constant** in `initialize`. It is registered only
by the `%02d` loop, which is why an earlier text search for `set_item_04` in the disassembly finds
nothing. This is the single most likely thing to mislead a later reader.

---

## 2. What happens when a button is decided

### The decide read is a single line, and there is no per-button branch

`main.p4` (`update_selector0`), pc24-27:

```
pc24  GETTABLE R1 <- self.selector0
pc25  SELF     R1 = selector0.get_decided_button_id
pc26  CALL     R1
pc27  SETTABLE self.exit_value = <that value>
```

pc29-33 then compares `exit_value <= 0`: when the id is not positive it resets
`selector1_selected_id = -1` and returns. Otherwise it returns `false` at pc88, and `update`
(`main.p9`, pc98-103) treats a `false` return from `update_selector0` as "keep looping".

**So the script never switches on which row was chosen.** There is no `if id == 3 then ...`
anywhere. The decided id *is* the value of `self.exit_value`, and that value is what the
`get_exit_value` accessor (`main.p12`, pc1-2, one `GETTABUP` of `exit_value` and a
`RETURN 1`) hands back out of the chunk.

### So what opens the sub-screen? Not this chunk.

This is the answer to `P2-UI-FLOW` section 6, edge 3. It is now measured rather than open:

- The chunk contains **no** `make_mii_special`, `make_mii_hat`, `make_mii_body` or
  `make_mii_base` string.
- It contains no string containing `scene`, `Screen`, `transition` or `request`.
- The only `Layout*` names it uses are `LayoutButtonSelector`, `LayoutButtonSelectorConfig` and
  `LayoutRootList`.
- The **complete** set of `UiScriptPlayer.invoke` targets in the chunk is three names:
  `set_random`, `switch_favorite`, `is_empty_name`. None of them names a screen.

Reading (B for the absences, **D** for the consequence): the chunk's job ends when it publishes a
button id. Whatever owns the Mii editor scene reads `exit_value` through `get_exit_value()` and
opens the headgear, outfit, colour, voice or special-move screen itself, mapping the integer id to
a screen. **The mapping from row id to screen lives outside this chunk and is not in the mod's
extracted inputs.** That is the single most important thing a mod author needs to know and it is
exactly what this task could not reach offline.

`main.p10` (`main`, the frame loop) shows what the script does with the value afterwards:

| pc | instruction range | effect |
|---|---|---|
| pc43-45 | `GETTABUP EXIT_VALUE_DECIDE` -> `SETTABUP exit_value` -> `SETTABUP selector1_selected_id = -1` | resets to a neutral decided value on entering the loop |
| pc62-64 | `exit_value` vs `upvalue[2]`, which is main's register 7 = `R3 + 1` = **6** | if the value is 6, `ComFrameActor.set_button(COMFRAME_FOOTERBUTTON_NONE)`; otherwise `ComFrameActor.hide_frame(true)` |
| pc75-81 | `LT 0 - 0` on `exit_value` | if `exit_value < 0`: `is_end = true`, `set_camera_type(MAKE_MII_CAMERA_DEFAULT)` |
| pc82-85 | `play_animation_and_wait(layout_view, "out")` | plays the closing animation |
| pc94-106 | `UiFighterManager.is_active(FIGHTER_ENTRY_ID_SELF)` loop | yields until the scene is really finished |

`EXIT_VALUE_DECIDE` and `EXIT_VALUE_CANCEL` are read out of the environment (`_ENV`), not defined
in the chunk, and their numeric values are **not** recoverable from this input.

### `selector1`'s two buttons

`main.p5` (`update_selector1`), pc23-44:

| decided id | instruction range | effect |
|---|---|---|
| `upvalue[0]` (pc26) = main register 5 = **0**, `btn_other_random` | pc26-32 | `self:update_random()`, return false |
| `upvalue[1]` (pc34) = main register 6 = **1**, `btn_other_try` | pc34-44 | `self.exit_value = upvalue[2]` (pc37, main register 7 = **6**), `UiSoundManager.play_se(UI_SE_ID_DECIDE)` (pc39-42), return true |

So `btn_other_try` is the one button that sets `exit_value` to **6** - which is exactly the value
`main.p10` pc62-64 special-cases. That is the concrete sense in which "try" leaves this screen
differently from the six rows, and it is visible entirely from the script (B).

`update_random` (`main.p8`, 38 instructions):

| pc | effect |
|---|---|
| pc1-12 | if `visible_popup_random` is false: `play_se(UI_SE_ID_DECIDE)`, `UiScriptPlayer.invoke("set_random")`, `is_changed = true` |
| pc14-37 | otherwise open popup `ID_POPUP_MMIIF_EDIT_RANDOM`, `coroutine.yield()` while `AppPopupManager.is_busy()`, and on `POPUP_RESULT_YES` invoke `set_random`, clear `visible_popup_random`, set `is_changed = true` |

### Sounds actually played

| sound | where |
|---|---|
| `UI_SE_ID_CURSOR` | `p4` pc83-86, `p5` pc120-123 / 141-144 / 153-156 / 175-178 / 187-190, `p6` pc151-154 |
| `UI_SE_ID_DECIDE` | `p5` pc39-42, `p8` pc4-7, `p9` pc52-55 / 63-66 / 71-74 |
| `UI_SE_ID_CANCEL` | `p7` pc9-12 |
| `play_se_label("se_system_save")` | `p9` pc76-79 |
| config-driven: `se_system_fixed` on decide, `se_system_cursor` on cursor, both on `selector0` only | `p11` pc84-87 / 119 |

`selector1`'s config has `decide_se_label_code = nil` (pc117), so the `UI_SE_ID_DECIDE` and
`se_system_save` calls in `p5` / `p9` are **script-level**, not selector-driven.

### Animations started in `initialize`

`layout_view.play_animation(name, 1.0)` is called on `set_item_00`, `set_item_01`, `set_item_02`,
`set_item_03` and `set_item_05` (part lookups at pc17-19, 29-31, 41-43, 53-55, 69-71):

| part | animation names played |
|---|---|
| `set_item_00` | `category_00`, `value_txt` |
| `set_item_01` | `category_01`, `value_txt` |
| `set_item_02` | `category_02`, `value_txt` |
| `set_item_03` | `category_03`, `value_color`, `color_00` |
| `set_item_05` | `category_04`, `value_txt` |

`set_item_04` gets **no** `play_animation` in `initialize` - it is the only one of the six with
no animation call. `layout_view.stop_animation_at_end("out")` runs at pc13-15.

---

## 3. Conditions

All flag reads are `GETTABUP ... C = RK(<name>)` against `upvalue[0]`, which is `_ENV`; each is
followed by a `TEST`/`JMP` pair. Counts across the whole chunk: `IS_READ_ONLY` **5**,
`FROM_AMIIBO` **5**, `IS_SKILL_EDITABLE` **4**.

| part / control | index | condition | what happens | instruction range |
|---|---|---|---|---|
| all six `set_item_NN` | 0-5 | `IS_READ_ONLY` true | `selector0:set_selectable(i, false)` for every `i` in a second `FORPREP`/`FORLOOP` (pc144-153) | `p11` pc141-153 |
| `set_item_04` (special row) | 4 | `IS_SKILL_EDITABLE` true **and** `IS_READ_ONLY` false | `selector0:set_selectable(upvalue[5], true)` then `selector0:select_button(upvalue[5])`, so the cursor **lands on row 4** | `p11` pc154-166 |
| all of `selector0` | - | `IS_SKILL_EDITABLE` false **and** `IS_READ_ONLY` false | `selector0:set_enable(false)` - the whole main menu is disabled | `p11` pc167-170 |
| `btn_other_try` | sel1/1 | always at start | `selector1:set_selectable(upvalue[3]=0, false)` then `selector1:select_button(upvalue[4]=1)` - present but not selectable, and it is the focused row | `p11` pc171-179 |
| `btn_other_try` | sel1/1 | `FROM_AMIIBO` true | `layout_view:get_parts("btn_other_try"):set_visible(false)` | `p11` pc211-217 |
| `set_btn_keyhelp_00` | - | `FROM_AMIIBO` true | `set_visible(false)` | `p11` pc218-224 |
| confirm button | - | `FROM_AMIIBO` false | `play_se(UI_SE_ID_DECIDE)` | `p9` pc49-56 |
| confirm button | - | `FROM_AMIIBO` true **and** `UiScriptPlayer.invoke("is_empty_name")` | `play_se(UI_SE_ID_DECIDE)` | `p9` pc57-67 |
| confirm button | - | `FROM_AMIIBO` true, name not empty, `IS_READ_ONLY` true | `play_se(UI_SE_ID_DECIDE)` | `p9` pc68-75 |
| confirm button | - | `FROM_AMIIBO` true, name not empty, not read-only | `play_se_label("se_system_save")` | `p9` pc76-79 |
| cancel | - | `IS_NEED_SAVE` false and `is_changed` false | falls through to the popup path | `p7` pc1-14 |
| cancel | - | `FROM_AMIIBO` true | popup `ID_POPUP_MMIIF_EDIT_SAVE`; on NO, popup `ID_POPUP_AMIIBO_MII_EDIT_CANCEL` | `p7` pc15-63 |
| cancel | - | `FROM_AMIIBO` false | popup `ID_POPUP_MMIIF_EDIT_CANCEL` | `p7` pc64-85 |
| focus restore | - | `selector1_selected_id > 0` or (`IS_READ_ONLY` and `IS_SKILL_EDITABLE`) | `selector1:set_focus(true)`, else `selector0:set_focus(true)` | `p10` pc21-38 |
| cursor movement | - | `IS_READ_ONLY` and `IS_SKILL_EDITABLE` | left press focuses `selector0` and `select_button(upvalue[3])` = main register 4 = **4** (pc119-126); else focuses `selector1` and `select_button(upvalue[2])` = main register 6 = **1** (pc128-136) | `p6` pc112-136 |
| cursor movement | - | `IS_READ_ONLY` false | `selector0:set_focus(true)` and `select_button(upvalue[4])` = main register 3 = **5** | `p6` pc137-145 |

The cursor park row is read through three different upvalue slots in three different prototypes,
and all three resolve to main's **register 4**, which is `LOADK R4 <- K7` with **K7 == 4** in the
patch (B):

| site | upvalue slot | resolves to |
|---|---|---|
| `p11` pc159, pc164 | `upvalue[5]` | main register 4 = 4 |
| `p5` pc203 | `upvalue[5]` | main register 4 = 4 |
| `p6` pc125 | `upvalue[3]` | main register 4 = 4 |

In the base chunk main pc14 is `LOADK R4 <- K7` with **K7 == 0** (B). That single integer is the
row the cursor is parked on, and it is the whole behavioural difference of the patch in that
region.

A second integer, main register 3 (**5**, `K6`), is read as a *button index* rather than a loop
limit in three places: `p5` pc118 (`upvalue[4]`), `p6` pc144 (`upvalue[4]`), and `p11` pc145
inside the read-only loop. So **5** is both the inclusive loop bound and a directly used row id.

---

## 4. Where each label comes from

Labels are **layout-side**, not script-side. The chunk contains **no** text-setting call at all:
there is no constant matching `set_message*` or `set_text*` (B).

Each `set_item_NN` part embeds four or more `txt1` sub-blocks in its `prt1` tail, and each carries
its message id as a literal string in that tail. The ids, read out of the part tails (B):

| row | part | message ids found in the tail |
|---|---|---|
| 0 | `set_item_00` | `mnu_mmiif_setup_fighter_nam_00`, `mnu_mmiif_setup_fighter_nam_01` (each twice: enabled and `_dis` variant) |
| 1 | `set_item_01` | `mnu_mmiif_setup_hat_00`, `mnu_mmiif_setup_hat_01` |
| 2 | `set_item_02` | `mnu_mmiif_setup_outfit_00`, `mnu_mmiif_setup_outfit_01` |
| 3 | `set_item_03` | `mnu_mmiif_setup_color` (once - this row has no value text) |
| 4 | `set_item_04` | `mnu_mmiif_setup_sp_move_00` .. `_04`, five ids |
| 5 | `set_item_05` | `mnu_mmiif_setup_voice_00`, `_01`, `_02` |
| sel1/0 | `btn_other_random` | (in `make_mii_btn2_00_try.bflyt`, not this file) |

Each part has a `_dis` (disabled) text child as well, and `set_item_03` and `set_item_05` carry
extra `set_txt_val*` children. Which id lands in which child slot is **not** established - the
`prt1` tail after the child records is explicitly undecoded by `bflyt-inspect` (tier B
measurement, semantics unverified).

`mnu_mmiif_setup_sp_move_title` was already resolved to "Select Special Moves" by P3-ARC-PROBES
from `ui/message/msg_menu.msbt`; that file was not re-read here.

---

## 5. Layout

`gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_edit/blyt/make_mii_edit.bflyt` - 58 blocks,
7 groups, 6 `set_item` parts. All offsets below are file offsets in that `.bflyt` (B).

### Selector groups

| group | block offset | entries | members (in order) | entry offsets |
|---|---|---|---|---|
| `RootGroup` | 0x004f48 | 0 | - | - |
| `all` | 0x004f7c | 3 | `anim_L_00`, `nul_keyhelp`, `anim_B_00` | 0x004fa8, 0x004fc0, 0x004fd8 |
| **`selector_0`** | **0x004ff0** | **8** | `set_item_00`, `set_item_01`, `set_item_02`, `set_item_03`, `set_item_04`, `set_item_05`, `btn_cursor`, `set_footer_area` | 0x00501c + 24*n |
| **`selector_1`** | **0x0050dc** | **2** | `btn_other_random`, `btn_other_try` | 0x005108, 0x005120 |
| `maker_grp` | 0x005138 | 1 | `maker` | 0x005164 |
| `favorite_grp` | 0x00517c | 1 | `favorite` | 0x0051a8 |
| `unedit_grp` | 0x0051c0 | 1 | `notice_unedit` | 0x0051ec |

`selector_0`'s count field is at 0x00501a. All 16 group members across the file resolve to a node
defined in the same file (`crosscheck`: 16 group members, 16 resolved, 0 unresolved).

Note the group has **8** members while the script sets up **6** buttons. `btn_cursor` and
`set_footer_area` are decorative members of the group, never passed to `setup_button` (B).

### The six row parts

| index | part | `prt1` offset | position (x, y) | extent (w, h) | child records | owner layout referenced | label source |
|---|---|---|---|---|---|---|---|
| 0 | `set_item_00` | 0x001410 | (-515.0, 316.0) | (772.0, 113.0) | 6 | `make_mii_btn0_01_item` | `mnu_mmiif_setup_fighter_nam_*` |
| 1 | `set_item_01` | 0x0018a8 | (-515.0, 214.0) | (772.0, 113.0) | 6 | `make_mii_btn0_01_item` | `mnu_mmiif_setup_hat_*` |
| 2 | `set_item_02` | 0x001d20 | (-515.0, 112.0) | (772.0, 113.0) | 6 | `make_mii_btn0_01_item` | `mnu_mmiif_setup_outfit_*` |
| 3 | `set_item_03` | 0x0021a8 | (-515.0, 10.0) | (772.0, 113.0) | 6 | `make_mii_btn0_01_item` | `mnu_mmiif_setup_color` |
| 4 | `set_item_04` | **0x002498** | (-515.0, **-220.0**) | (772.0, **362.0**) | **18** | **`make_mii_btn0_02_special`** | `mnu_mmiif_setup_sp_move_00..04` |
| 5 | `set_item_05` | 0x003534 | (-515.0, -452.0) | (772.0, 113.0) | 6 | `make_mii_btn0_01_item` | `mnu_mmiif_setup_voice_*` |

All six are `node_type = 3`, scale 1.0/1.0, x = -515.0. Rows step by -102 in y. `set_item_04` is
the odd one: it is **362 units tall** instead of 113, its 18 child records are
`set_txt_title`, `set_txt_num_00..03`, `set_txt_name_00..03` and their `_dis` twins, and it is the
only part referencing `make_mii_btn0_02_special`. The gap in y between row 3 (10.0) and row 5
(-452.0) is exactly where row 4's extra 249 units of height sit: this row is the special-move
summary block, not a normal one-line row (B for the geometry, **D** for the "it shows a summary
list" reading).

There is no parent field recorded for these parts beyond the group they appear in: all six are
children of `selector_0` by group membership, and the `.bflyt` has no separate parent pointer
that `bflyt-inspect` decodes.

### Spare parts the script never sets up

**Zero spare row parts exist.** The layout has exactly `set_item_00` .. `set_item_05` and nothing
higher; `set_item_06` does not exist (B). Within `selector_0`, the members that are never passed
to `setup_button` are `btn_cursor` and `set_footer_area`, which are not button parts at all.

This matters for the mod's goal: **there is no free row to take.** Adding an entry cannot reuse a
spare part, because there is not one.

### Animation members naming these parts

98 of the archive's 111 members are `.bflan`. No animation member names any `set_item_*` part (B) -
they are named after the **owner layout** instead:

| owner layout | animation members | count |
|---|---|---|
| `make_mii_btn0_01_item` | `..._category_00` .. `_05` | 6 |
| `make_mii_btn0_01_item` | `..._color_00` .. `_11` | 12 |
| `make_mii_btn0_01_item` | `..._value_txt`, `..._value_color` | 2 |
| `make_mii_btn0_01_item` | `..._BlinkOn`, `..._BlinkOff`, `..._OnOff`, `..._Disable` | 4 |
| `make_mii_btn0_02_special` | `..._BlinkOn`, `..._BlinkOff`, `..._OnOff`, `..._Disable` | 4 |
| `make_mii_btn2_00_try` | `_SelectOn`, `_SelectOff`, `_BlinkOn`, `_BlinkOff`, `_OnOff`, `_Disable`, `_Decide` | 7 |
| `make_mii_edit` | `in`, `out`, `maker_on`, `maker_off`, `favorite_on`, `favorite_off`, `unedit_on`, `unedit_off` | 8 |
| `com_csr_lct0_01` | `SelectOn`, `SelectOff`, `width_13px`, `width_18px`, `width_lock` | 5 |
| `com_btn_keyhelp_00` | `BlinkOn`, `BlinkOff`, `OnOff`, `Disable` | 4 |

Every `set_item_NN` row except `set_item_04` shares `make_mii_btn0_01_item`'s animation set.
`set_item_04` has its own, and its four states are exactly the standard
Blink/OnOff/Disable set - the same set `make_mii_btn2_00_try` uses, so the special row already
has a complete button-state animation set.

---

## 6. Return path from a sub-screen

**This chunk does not wait for a sub-screen and has no return bridge call.** It never opens one
(section 2), so there is nothing to poll.

What actually happens is a single handoff through `exit_value`:

1. `update_selector0` (`p4` pc27) writes the decided button id into `self.exit_value`.
2. `main` (`p10`) breaks its `update()` loop when `update()` returns false (`p10` pc47-57) and
   plays `play_animation_and_wait(layout_view, "out")` (pc82-85).
3. `p10` pc75-81 sets `is_end = true` when `exit_value < 0`, and `main.p13` (`is_end`) returns
   `1` while it is false, `0` when true.
4. `main.p12` (`get_exit_value`) returns `self.exit_value` to the host.

The host owns the actual transition. `exit_value` is the only channel between this chunk and the
scene that hosts it, and the host must have already mapped the integer to a screen. **D:** the
"ComFrameActor" and `UiScriptPlayer` calls suggest a shared frame-actor layer, but nothing here
shows the host reading `exit_value` or the round trip.

---

## 7. What a new entry would have to touch - facts, not a design

Places in this script that hold a button count or iterate over buttons:

| fact | where | evidence |
|---|---|---|
| the count of main-menu buttons is the integer constant `K6` in `main` (value 5), loaded into register 3 and used as a `FORPREP` limit, giving 6 iterations | `main` pc13; `p11` pc98-101 | B |
| the row name is generated, not listed: `"set_item_%02d"` formatted with the loop index | `p11` pc105-110, K45 | B |
| `set_item_00/01/02/03/05` also appear as **literal** part names, for `get_parts` + `play_animation` | `p11` pc18, 30, 42, 54, 70 (K11, 16, 18, 20, 24) | B |
| `set_item_04` has **no** literal; it is registered only by the loop, and receives no `play_animation` | `p11` - | B |
| a second loop re-iterates the same buttons to disable them, `FORPREP` pc147 / `FORLOOP` pc153 | `p11` pc144-153 | B |
| the cursor park row is a separate integer, `K7` in `main` (patch 4, base 0), read through `upvalue[5]` of `p11` and `p5` and `upvalue[3]` of `p6` - all three resolve to main register 4 | `main` pc14; `p11` pc159, 164; `p5` pc203; `p6` pc125 | B |
| the same `K6` (== 5) is read as a button index too, via `upvalue[4]` of `p5`/`p6` and `upvalue[2]` of `p11` | `p11` pc145; `p5` pc118; `p6` pc144 | B |
| `selector1` button ids are main registers 5 and 6 (0 and 1), read as `upvalue[3]`/`upvalue[4]` of `p11` and `upvalue[0]`/`upvalue[1]` of `p5`, `upvalue[1]`/`upvalue[2]` of `p6` | `main` pc15-16; `p11` pc133, 138, 173, 178; `p5` pc26, 34; `p6` pc102, 107 | B |
| `btn_other_try` sets `exit_value` to main register 7 (== 6), the value `p10` special-cases | `p5` pc37; `p10` pc63 | B |

Layout structures that hold the rows:

| fact | where | evidence |
|---|---|---|
| `grp1` block `selector_0` at 0x004ff0, **count field at 0x00501a**, currently 8 | `make_mii_edit.bflyt` | B |
| member names are 24-byte NUL-padded slots at 0x00501c + 24*n | same | B |
| adding a row means another `prt1` part plus one more `grp1` slot **and** a count bump | same | B for the layout of the structures; the arithmetic is structural, not a claim the loader re-reads the count (D) |
| the two spare group members `btn_cursor`, `set_footer_area` are not button parts and carry no owner layout reference for a row | same | B |
| row geometry is per-part `prt1` fields: y steps by -102, x is -515.0, extent 772.0 x 113.0 | parts at 0x001410..0x003534 | B |
| `sarc-layout` refuses to add or grow a member, so a **new** `prt1` part inside the existing `make_mii_edit.bflyt` keeps the member count at 111 and the archive size fixed, but the `make_mii_edit.bflyt` member itself would change length and `sarc-layout` would refuse that as a same-length replace | `tools/sarc-layout/README.md` limits | B (the tool's documented refusal) |

Native calls that receive a button index or a count:

| call | what it receives | where | tier |
|---|---|---|---|
| `selector0.setup_button(i, name)` | `i = 0..5` | `p11` pc110 | B that it is called; **D** that the native side uses `i` as anything but a registration order |
| `selector0.set_selectable(i, false)` in the read-only loop | `i = 0..5` | `p11` pc148-152 | B / D |
| `selector0.select_button(4)` - main register 4, the park row | the integer 4 | `p11` pc164, `p5` pc203, `p6` pc125 | B / D |
| `selector0.select_button(5)` - main register 3 | the integer 5 | `p5` pc118, `p6` pc144 | B / D |
| `selector0.get_decided_button_id()` | - | `p4` pc25 | B |
| `selector0.get_selected_button_id()` | - | `p5` pc46 | B |
| `selector1.set_selectable(0, false)` / `select_button(1)` | 0, 1 | `p11` pc171-179 | B / D |
| `LayoutButtonSelector.setup(view, group_name, config)` - **`group_name` is a string, so the native side resolves the button set from the layout group**, not from a count | `p11` pc97, pc130 | B that the group name is passed; **D** that the native side reads the group |
| `play_animation(name, 1.0)` on `layout_view` | an animation name string | `p11` pc23-79 | B |
| `UiScriptPlayer.invoke(name)` | one of exactly three names | `p8` pc11, `p9` pc32, `p9` pc60 | B |

The `setup` call receiving a **group name string** rather than a button list is the fact that
decides whether a new part has to be added to the `grp1` group at all. If the native selector
walks the group, adding a part without adding a group member would leave it unregistered; if it
only uses the index passed to `setup_button`, the group is decorative. **This is unresolved and
is the highest-value next experiment** (see below).

---

## 8. Unresolved edges

1. **The row-id -> screen mapping is outside this chunk.** The chunk publishes an integer through
   `exit_value` and returns. Which screen opens for which id, and in the owner, is not in the
   extracted inputs. This is the blocker for the mod's goal and it is now a *located* unknown
   rather than an open one: the answer is in the native code that drives this chunk (the scene at
   0x1808980, which gate 1 identified as the Mii editor).
2. **`EXIT_VALUE_DECIDE` / `EXIT_VALUE_CANCEL` values are unknown.** They come from `_ENV`, so the
   numeric meaning of `exit_value` 0..5 vs 6 (`p10` pc62) vs negative cannot be stated.
3. **Whether `LayoutButtonSelector.setup` reads the `grp1` group at runtime** is not shown. This
   decides whether a new part needs a group entry, and it is answerable from the native
   `setup` implementation.
4. **Which message id lands in which text child** inside each `prt1` tail is undecoded; the tail
   after the child records has no agreed field semantics.
5. **`get_decided_button_id` is assumed to return the index passed to `setup_button`.** The chunk
   stores it into `exit_value` and never inspects it, so this is an assumption (D), not a
   measurement. A negative-when-nothing-decided convention is implied by pc29 but not proven.
6. **Whether `selector1`'s `select_button(1)` on a non-selectable button is legal** at pc176-179
   is not established. The script sets it up unconditionally.
7. **Nothing was run.** No emulator, no console, no modified file. Every behavioural statement
   about the game's response to a button id is D.

---

## 9. Next experiment

Locate and disassemble the native `LayoutButtonSelector.setup` and
`LayoutButtonSelector.get_decided_button_id` in the main image, and check two things:

- whether `setup`'s third argument (`selector_0` / `selector_1`) is used to enumerate members of
  the `grp1` group, or ignored in favour of only the indices passed to `setup_button`
  (resolves edge 3 above);
- whether `get_decided_button_id` returns the `setup_button` index unchanged (resolves edge 5).

Both are offline and bounded, and the same pass should show the caller that consumes
`get_exit_value()` and turns it into a screen - which resolves edge 1 and is the actual blocker
for the mod.

---

## Summary

- Task: **P6-EDIT-MENU**. Status: **DONE** (tracing; nothing designed, nothing edited).
- Evidence tier: **B** throughout, **D** for every statement about native behaviour.
- Changed/created files, all inside the assigned paths:
  - `research/P6-EDIT-MENU.md` (this report)
  - `scratch/2026-10-05_P6-EDIT-MENU/check_p6_edit_menu.py` (the check script)
  - `scratch/2026-10-05_P6-EDIT-MENU/check_run.txt` and the raw tool output
    (`luac_patch.txt`, `luac_base.txt`, `dis_patch.txt`, `groups.txt`, `parts_setitem.txt`,
    `crosscheck.txt`, `layout_members.txt`, `header.txt`, `compare.txt`, `mut/`)
  - `evidence/P6-EDIT-MENU/` (check script, check run, 11 mutation outputs, raw tool output)
  - `gamedata/mii_customizer/P6-EDIT-MENU/` created, **empty** - no extraction was needed.
- No other worker's file, and no `STATUS.md` / `CURRENT_INSTALL.md` / `CHANGELOG.md` / contract,
  was touched. No commit, branch, emulator run or SD access.
- Observed checks: `check_p6_edit_menu.py` **264/264, exit 0**; `lua53_inspect verify` on the
  patch chunk **11/11, exit 0**; 11 mutation controls all **exit 1** with at least one expected failing
  check and no traceback; input sha256 all three match.
- Not verified: everything about runtime behaviour, the id-to-screen mapping, the `_ENV` flag
  values, and whether the game would load a modified chunk or layout.
- Out of scope, noticed but not started: nothing else. The `set_item_04` geometry oddity (362
  units tall, 18 children, its own layout and animation set) is described above but not
  investigated.