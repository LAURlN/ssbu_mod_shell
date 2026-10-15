# P10-EDIT-ENTRY - edit-menu script that opens the mod list (exit value 7)

Worker: Space Bunny Alpha. Date 2026-10-05.
Status: **DONE** (parts 1-3 written as each landed; closing report at the end).

Task: P10-EDIT-ENTRY. Scope is the **script side only**. Plugin 0.4.0 (P10-UI-SLICE,
parallel task, not mine) turns exit value 7 into "open the character list"; this task
publishes the value.

Evidence tier: **B** throughout unless a line says otherwise - offline measurement of
bytes and of parsed chunks. **Nothing was run**: no install, no emulator, no console.
Every sentence about what the game does with the chunk is tier **D** (hypothesis).

## Inputs

| path | sha256 / size |
|---|---|
| `gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc` | `c777ecc492cea48f6ffd40112b22f96e66219d00969b570a7cc3cf8d7f4a9417`, 10576 bytes (read-only) |
| `gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_edit_actor.lc` | `1f73dff133961b68dbe24641298229b9f3905a44703164563911b105eaa16908`, 10321 bytes (read-only) |
| `mods/mii_customizer/tools/lua-src/make_mii_edit_actor.lua` | `86648c36a9a050657ff56262d9d8d6631d7f8b0a9e54650e1a38999e2e8ec327` (P9 reconstruction) |

## Read first

`research/P9-EDIT-SOURCE.md`, `research/P6-EDIT-MENU.md` sections 1-3,
`research/P9-EDIT-DISPATCH.md` sections 3/4/6, `tools/lua-src/README.md`,
`builds/0.3.1-edit-probe/README.md`, `evidence/2026-10-05_session1/RESULT_boot2.md`.

## Part 1 - checking the coordinator's diagnosis of the 0.3.1 probe

**Verdict: the coordinator's reading holds** (B for code order, D for native
semantics). Method: `scratch/2026-10-05_P10-EDIT-ENTRY/part1_order.py`
disassembled both chunks; full listings in `part1_original_full.txt`,
`part1_probe_full.txt`, site enumeration in `part1_sites.txt`. Prototype
numbering follows `lua53_inspect` as used by P6-EDIT-MENU: `main.p4` =
`update_selector0`, `main.p5` = `update_selector1`, `main.p6` =
`update_com_frame`, `main.p9` = `update`, `main.p10` = `main()`,
`main.p11` = `initialize`.

### Order on a frame with Favorite pressed

(`main.p9`, 112 instructions original / 111 probe)

1. `virtual_input:is_cancel()` read (pc10) - not taken.
2. `INPUT_COMMON_BUTTON` pressed (pc16, via `ComFrameActor.press_decide`) -
   not taken.
3. `not FROM_AMIIBO` taken; `INPUT_FAVORITE` pressed (pc23-32, `GETTABUP`
   `INPUT_FAVORITE`) - taken. **The favourite branch runs first**:
   `UiScriptPlayer.invoke("switch_favorite")` (`LOADK` pc30) +
   `self.is_changed = true`.
4. `ComFrameActor.is_decided()` (pc34 - the chunk's **only** `is_decided`
   read) -> false; `ComFrameActor.is_cancelled()` (pc83) -> false;
   `update_com_frame()` -> false.
5. `update_selector0()` (`main.p4`) - **the probe block lives here**.
6. `update_selector1()`.

So on the same frame the favourite branch has already run and the frame's
`is_decided` slot has already been read *before* the probe block executes.

### Every `get_decided_button_id` / `is_decided` site

| site | prototype | instruction | meaning |
|---|---|---|---|
| original pc24, probe pc46 | `main.p4` | `self.exit_value = selector0:get_decided_button_id()` | the only place `update_selector0` turns a decide into an exit value |
| pc23 | `main.p5` | `local decided_id = selector1:get_decided_button_id()` | the Try/Random decide |
| pc34 | `main.p9` | `ComFrameActor.is_decided()` | the chunk's only `is_decided` read |
| probe pc43 | `main.p4` (probe only) | `ComFrameActor.press_decide()` | probe block, immediately before pc46 |
| pc83 | `main.p9` | `ComFrameActor.is_cancelled()` | companion read, listed for completeness |

The probe grew `main.p4` from 89 to 111 instructions; its block (pc27-44:
`get_selected_button_id` pc27, `is_pressed(INPUT_FAVORITE)` pc33-34,
`selector0:select_button()` pc39, `ComFrameActor.press_decide()` pc43) sits
immediately before the original `get_decided_button_id`, now pc46.

### Does the coordinator's reading hold? Yes

- B: `update` runs the `INPUT_FAVORITE` branch (switch_favorite) **before**
  `update_selector0`, where the probe block sits (symbolic order above,
  `part1_sites.txt`).
- The probe's conditions do become true on that frame (focus on row 1 +
  `is_pressed(INPUT_FAVORITE)`, a level-triggered read), so the probe does run
  `selector0:select_button()` and `ComFrameActor.press_decide()` - but
  `press_decide` names **ComFrameActor**, the frame's confirm button, while the
  following `get_decided_button_id()` reads **selector0's own** decided state.
  Nothing in the block makes selector0 decide, so `exit_value` is never
  assigned and `update_selector0` falls through and returns false. The script
  therefore ends the frame exactly as a stock Favorite press does: favourite
  toggled, menu still open - the observed console behaviour.
- Two same-frame facts reinforce it: (a) `update` consumed
  `ComFrameActor.is_decided()` at pc34 before the probe ran, so a frame-level
  decide could not be seen on that frame either; (b) `switch_favorite` had
  already consumed the press in `update`, which is why the console saw the
  favourite toggle and nothing else.

### What Part 1 cannot show

- **Whether the chunk loaded on console at all.** The observation "Favorite
  just toggled favourite" is identical for a loaded-but-ineffective probe and
  for the stock chunk; `RESULT_boot2.md` lists load at this path as unsettled.
- The native meaning of `ComFrameActor.press_decide()` is inferred from the
  name and call sites, not observed (D).
- That `is_pressed` is level-triggered (held) rather than edge-triggered is a
  reading of the API name, not a measurement (D).

## Part 2 - loader facts

### (a) hash40 of the path strings vs the constants the scene loads

`scratch/.../hash40_check.py`, evidence `evidence/P10-EDIT-ENTRY/hash40_check.txt`
(exit 0). Formula: `hash40 = (len(lower) << 32) | crc32(lower) & 0xffffffff`,
self-tested against `hash40("fighter_kind_miigunner") == 0x0166e9fae70` (the
self-test P9-EDIT-DISPATCH section 2 used).

| path | computed hash40 | P9-EDIT-DISPATCH s2 constant | load address | match |
|---|---|---|---|---|
| `ui/script_patch/chara_make/make_mii_edit_actor.lc` | `0x0314b141360` | `0x0314b141360` | 0x1808c98 | True |
| `ui/script/menu/chara_make/make_mii_special_actor.lc` (known to load from a mod folder on the console) | `0x03359b0338a` | `0x03359b0338a` | 0x19ddd90 | True |

Both confirmations are **verified** (run this task, exit 0).

### (b) data.arc index entries compared (read-only)

Method: `scratch/.../arc_index.py`, a custom read-only parser of the arc
FileSystem table transcribed from smash-arc 0.6.0 (`arc_file.rs`,
`filesystem.rs`, `lookups.rs`); zstd decompression via `node` because this
Python has no zstd module. Report: `evidence/P10-EDIT-ENTRY/arc_index_report.txt`
(exit 0, `--sha256`). Directory probes: `evidence/P10-EDIT-ENTRY/dirinfo_probe.txt`
(`dir_debug2..5.py`, all exit 0). Nothing outside the workspace was written;
the arc is only read.

| entry | patch edit actor | special-move chunk (known-good mod path) | base edit actor |
|---|---|---|---|
| present in index | yes, 1 hit | yes, 1 hit | yes, 1 hit |
| path hash40 | `0x0314b141360` | `0x03359b0338a` | `0x030fbd8f53d` |
| parent hash | == `hash40('ui/script_patch/chara_make/')` True | == `hash40('ui/script/menu/chara_make/')` True | same as special |
| FileInfo flags | `0x00000010` | `0x00000010` | `0x00000010` |
| is_regional / is_localized | 0 / 0 | 0 / 0 | 0 / 0 |
| load_type | 0 | 0 | 0 |
| is_shared | False | False | False |
| compression | zstd, 4107 -> 10576 | zstd, 3308 -> 7799 | zstd, 4015 -> 10321 |
| absolute offset | `0x325aa9af8` | `0x9fcddaf8` | `0x9fcdac68` |
| sha256 of decompressed bytes == workspace copy | `c777ecc4...a9417` True | `ffa2bafa...b40d65d` True | `1f73dff1...a16908` True |
| physical folder (folder_offsets) | 38457, file_count **1** | 614, file_count **68** | 614 (shared with special) |
| DirInfo (via `file_info_indices`) | `dir_infos[26192]`, file_info range [539859, 539860) covers the file | `dir_infos[334]` = `ui/script/menu`, range [864, 932) covers the file | same as special |

Flag-name note: `is_regional` (bit 15), `is_localized` (bit 16) and
`is_redirect` (bit 4) are **local names** for those bits (mine, not the
game's). Bit 4 is not distinctive: a histogram over all 629588 FileInfo records
finds 11 distinct flag values, of which `0x10` alone is 180599 files (28.7%)
and 78.8% of all records have bit 4 set.

### The directory story (why the first report draft said "no DirInfo")

- A **full scan of all 33804 DirInfo records finds no entry** keyed or named
  `chara_make` in either tree: no `hash40('ui/script/menu/chara_make')`, no
  `hash40('ui/script_patch/chara_make')`, no `name == hash40('chara_make')`
  (`dir_debug2/3`). The string-level directory exists only in the `file_paths`
  parent hashes, where all three verify as `hash40(dir + '/')`.
- The correct chain from a file to its DirInfo is
  `file_paths[n][0].index -> file_info_indices -> (dir_infos index,
  file_infos index)`; for all three files the DirInfo's
  `file_info_start_index..+file_count` range covers the returned
  `file_infos` index (`dir_debug4/5`). Searching by parent-directory hash
  cannot work for `chara_make`, so `arc_index.py` was fixed to use this chain
  and the stale "no DirInfo entry" lines were removed from the report.
- `dir_hash_to_info[i].key == dir_infos[i].path.hash` holds for 33804 of 33804
  entries, so the hash table and the DirInfo table are aligned 1:1.
- The patch file's DirInfo is keyed by the file path **without `.lc`**
  (`hash40('ui/script_patch/chara_make/make_mii_edit_actor')`), its `name` is
  `hash40('chara_make/make_mii_edit_actor')` and its `parent` is
  `hash40('ui/script_patch')`. This is a patch-tree pattern, not a property of
  this one file: 11783 DirInfos have path length >= 40, 724 have exactly the
  shape (path length >= 40, file_count 1, no children, flags 0), and
  `ui/script_patch` has 9 child entries of length 39..50 of which ours is one
  (`dir_debug5`).
- Both menu files' physical folder (614) is the folder the DirInfo
  `ui/script/menu` points at (its `path` index is 614); the patch file has its
  own 1-file folder (38457). Both folders carry
  `directory_index = 0xffffff`.

### Conclusion

**No index difference was found that would make a mod-folder replacement
behave differently.** All three files: exist, resolve by full-path `hash40`
identically (the lookup P9-EDIT-DISPATCH section 2 shows the scene perform),
share the same flag word `0x10` (bit 4 set, not regional, not localized), the
same `load_type` 0, sit below the shared-section offset (`is_shared` False)
in the main file section, and are zstd-compressed with matching sha256.
The only structural differences are the directory grouping (dedicated 1-file
folder plus file-stem DirInfo under `ui/script_patch` vs a shared 68-file
folder plus the `ui/script/menu` DirInfo) and the natural per-file sizes.
Whether the loader resolves a mod-folder replacement at the patch path
exactly like the known-good special-move path **cannot be settled from index
entries** (tier D); the index itself gives no flag that separates them.

Limits for Part 2: the parser is mine (layouts transcribed from the pinned
crate source; every table is bounds-checked against header counts, and the
three sha256 round-trips prove the path chain resolves to the real bytes).
52037772 of 52332508 decompressed index bytes are consumed; the ~295 KB tail
was not attributed to any table. Nothing was extracted, written or modified
in the arc.

## Part 3 - the entry script

### 3.1 What was generated, and how

Generator (new file): `tools/lua-src/make_entry_source.py`, modelled on
`make_probe_source.py`: it reads the byte-identical
`tools/lua-src/make_mii_edit_actor.lua`, never edits it, replaces two anchors
with marker-delimited blocks, and in `--strip` mode removes the marked regions
from both generated files and asserts byte-for-byte equality with the base.
Run record: `evidence/P10-EDIT-ENTRY/entry_source_gen.txt` - generate exit 0,
`--strip` exit 0 (both variants purely additive).

Generated outputs (do not edit; regenerate instead):

| file | lines | variant |
|---|---|---|
| `tools/lua-src/make_mii_edit_actor_entry.lua` | 643 | `entry` |
| `tools/lua-src/make_mii_edit_actor_entry_marker.lua` | 646 | `entry-marker` |

The entry block (generated source lines 367-375; the anchor is the shipped
Favorite branch, base source lines 366-369):

```lua
        if self.virtual_input:is_pressed(INPUT_FAVORITE) == true then
            -- >>> ENTRY BLOCK START (P10-EDIT-ENTRY) >>>
            if self.selector0:has_focus() == true
                and self.selector0:get_selected_button_id() == 1 then
                self.exit_value = 7
                self.selector1_selected_id = -1
                UiSoundManager.play_se(UI_SE_ID_DECIDE)
                return true
            end
            -- <<< ENTRY BLOCK END (P10-EDIT-ENTRY) <<<
            UiScriptPlayer.invoke("switch_favorite")
            self.is_changed = true
        end
```

Placement (B for code order): the 0.3.1 probe failed inside
`update_selector0`; this block sits in `update`'s own Favorite branch - the
code that already owns this input on this screen - and never reads
`get_decided_button_id()`; it assigns `exit_value` itself, exactly as
`RESULT_boot2.md` concluded ("A correct entry sets `self.exit_value`
itself"). `return true` is what makes `main()` break its loop, so the screen
leaves on the same frame a decided row would.

The marker block (generated source lines 553-555):

```lua
    -- >>> ENTRY-MARKER BLOCK START (P10-EDIT-ENTRY) >>>
    edit_state.layout_view:get_parts("btn_other_try"):set_visible(false)
    -- <<< ENTRY-MARKER BLOCK END (P10-EDIT-ENTRY) <<<
```

placed after the shipped `FROM_AMIIBO` block's `end` in `initialize` (base
line 543), so it is unconditional. It is the same parts lookup +
`set_visible(false)` the shipped `FROM_AMIIBO` branch runs itself (base line
541), which is evidence the parts node exists at that point in the script's
lifetime.

**What the user notices with the marker variant:** the edit menu opens
without its **Try button** - the right-hand Random/Try column shows Random
only. Stock chunk (or `entry` variant): the Try button is there. Nothing has
to be pressed. Use `entry` for real use; the marker variant is a load test.

### 3.2 Every name in the blocks, and where the original chunk uses it

Entry block - all names already ship in the chunk (line numbers are
`make_mii_edit_actor.lua`):

| name | kind | where the original uses it |
|---|---|---|
| `INPUT_FAVORITE` | host global | `update` :366, the branch test the block sits in - the chunk's only read of this input |
| `virtual_input:is_pressed` | method | `update` :366 (this branch); `update_selector0` (LEFT/RIGHT); `update_com_frame` (all four cursor keys) |
| `FROM_AMIIBO` | host global | the enclosing guard `elseif not FROM_AMIIBO` :365; also the decide branch :375, `update_selector1`, `update_com_frame`, `update_cancel`, `initialize` :540 |
| `selector0:has_focus` | method | `update_selector0` :67 (its first line), `update_selector1` :119, `update_com_frame` :229 |
| `selector0:get_selected_button_id` | method | the name ships on the sibling selector: `update_selector1` :134 `self.selector1:get_selected_button_id()`. Both selectors are the same class (`LayoutButtonSelector.new()` at `initialize` :494 and :507), so the method exists on `selector0`'s metatable |
| `exit_value` (field) | field | `update_selector0` :77 - the decided-row store this block mirrors - plus `update_selector1` :130, `update_cancel` :296/306/314/324, `main` :434/:439/:446 (the post-loop reads), `initialize` :527 |
| `selector1_selected_id` | field | `= -1` at `update_selector0` :79 (same store the block mirrors), `main` :425, `initialize` :528 |
| `UiSoundManager.play_se` | host function | 13 call sites (7 `UI_SE_ID_CURSOR`, 5 `UI_SE_ID_DECIDE`, 1 `UI_SE_ID_CANCEL`); the block reuses the exact TRY-branch shape `exit_value = ... ; play_se(UI_SE_ID_DECIDE) ; return true` from `update_selector1` :130-132 |
| `UI_SE_ID_DECIDE` | host global | :131 (`update_selector1` TRY), :343 (`update_random`), :376/:378/:380 (`update` decide branch) |
| `return true` | language | `update_selector0` :80, `update_selector1` :132, `update_cancel`, `update` decide/cancel branches |
| the literal `1` | number | the chunk's own row numbering: `initialize` :504 `select_button(0)`, `select_button(CURSOR_PARK_ROW)` (=4), `setup_button` loop `0..MENU_ROW_LAST` (=5); row 1 is `set_item_01` = Headgear (P6-EDIT-MENU section 0b) |
| the literal `7` | number | **new** - the exit value this task assigns; the chunk contains no literal 7 before this block |

No new `INPUT_*` name, no new host API, no new method: the block's condition
and body are assembled from names the shipped chunk already reads or calls.

Marker block:

| name | kind | where the original uses it |
|---|---|---|
| `edit_state.layout_view` | field | `initialize` :486 (`get_root_view()`), :541-542, and `main` :411/:445 |
| `get_parts` | method | `initialize` :477 and the two `FROM_AMIIBO` statements :541/:542 |
| `set_visible` | method | `initialize` :541/:542 (on the same parts node), `main` :411/:445 (on the view) |
| `"btn_other_try"` | string constant | `initialize` :513 (`setup_button(TRY_BUTTON_ID, "btn_other_try")`) and :541 |

### 3.3 `main()` after the loop: exit value 7 compared with exit value 1

Base source lines 433-450 (the post-loop of `main`, `main.p10`). Both values
are >= 0 and != 6 (`EXIT_VALUE_TRY`), so they take identical branches:

| base line | statement | exit 7 | exit 1 |
|---|---|---|---|
| 433 | `edit_state.layout_root:set_enable_input(false)` | runs | runs |
| 434-438 | `exit_value == EXIT_VALUE_TRY (6)` ? `hide_frame(true)` : **`set_button(COMFRAME_FOOTERBUTTON_NONE)`** | else branch | else branch |
| 439-442 | `exit_value < 0` ? `is_end = true; set_camera_type(...)` : skip | skipped | skipped |
| 443 | `UiCommon.play_animation_and_wait(layout_view, "out")` | runs | runs |
| 444 | `edit_state:set_enable_input(false)` | runs | runs |
| 445 | `layout_view:set_visible(false)` | runs | runs |
| 446-450 | `exit_value < 0` ? wait for `UiFighterManager` : skip | skipped | skipped |

The statement sequence is **identical**; the two values differ only in what
`get_exit_value()` hands to native code. Per P9-EDIT-DISPATCH section 4: the
dispatcher `0x180a030` pushes `value + 4` onto the state stack, so exit 1
pushes state 5 (the headgear sub-screen, the normal decide flow) while exit 7
pushes state 11, whose handler `0x180cbc0` gates on `scene+0x164` and a
static, touches no child and traps nowhere - **benign without the plugin**.
Exit >= 9 would push an out-of-range state and land at `0x180cf00`
(`bl 0x39c20a0 ; udf #0`, a trap), which is why `check_entry.py` asserts no
constant >= 9 is ever stored to `exit_value`. On the entry frame the script
also skips `switch_favorite` (the block returns first), so the favourite is
toggled **not** at all that frame and `is_changed` is left alone (B for the
code path; D for what a player observes).

### 3.4 Builds, checks, real exit codes

Delivered tree `builds/0.4.0-edit-entry/`: two mod folders, `MANIFEST.json`,
`README.md`, `check_entry.py`.

| variant chunk | bytes | sha256 | vs original 10576 |
|---|---|---|---|
| `variant_entry/.../make_mii_edit_actor.lc` | 10745 | `0ec8b495...ff4eb8a` | +169 |
| `variant_marker/.../make_mii_edit_actor.lc` | 10773 | `dc47a9e6...2690ae` | +197 |

Per-prototype deltas (from MANIFEST.json): `main.p9` (update) instructions
112 -> 130, constants 31 -> 38, lines 360-405 -> 360-414; the marker
variant's `main.p11` (initialize) instructions 225 -> 232, lines 472-567 ->
481-579; every prototype defined after `update` shifts its recorded line
numbers by +9 (+12 for the marker variant) with **instructions identical**.
`maxstacksize`, `numparams` and upvalue descriptors are unchanged everywhere.

Disassembled `exit_value` stores (identical in both variants; the entry store
is the one new literal):

| prototype | pc | opcode | value |
|---|---|---|---|
| main.p4 | 26 | SETTABLE | register (dynamic, CALL - the decided row) |
| main.p5 | 37 | SETTABLE | register (dynamic, GETUPVAL - TRY=6) |
| main.p7 | 7/36/59/82 | SETTABLE | register (dynamic, GETTABUP - EXIT_VALUE_CANCEL/DECIDE) |
| **main.p9** | **38** | **SETTABLE** | **K[15] integer 7** (the entry) |
| main.p10 | 43 | SETTABUP | register (dynamic, GETTABUP - initialize's DECIDE) |
| main.p11 | 180 | SETTABUP | register (dynamic, GETTABUP) |

Checks run this task, with their real exit codes (all captured under
`evidence/P10-EDIT-ENTRY/`):

| command | evidence file | exit |
|---|---|---|
| `make_entry_source.py` | `entry_source_gen.txt` | 0 |
| `make_entry_source.py --strip` | `entry_source_gen.txt` | 0 |
| `check_entry.py --build --write` (regenerate, compile, post-pass, stage, manifest, verify) | `entry_build_run.txt` | 0 |
| `check_entry.py` (verify only) | `entry_check_run.txt` | 0 |
| `check_entry.py --neg-all` (5/5 controls caught) | `entry_negative_controls_run.txt` | 0 |
| `tools/lua-src/build_check.py` (pristine reconstruction) | `build_check_run.txt` | 0 - both chunks BYTE-IDENTICAL |
| `tools/lua-src/negative_controls.py` | `negative_controls_run.txt` | 0 - 7/7 caught, sources unchanged |
| `scratch/.../hash40_check.py` (part 2a) | `hash40_check.txt` | 0 |
| `scratch/.../arc_index.py --sha256` (part 2b) | `arc_index_report.txt` | 0 |
| `scratch/.../dir_debug2-5.py` (part 2b directory probes) | `dirinfo_probe.txt` | 0 each |

The five `check_entry.py` negative controls (each injects one error into an
in-memory copy; disk is never touched): manifest byte count, missing `version`
key in `info.toml`, assertions run against the original chunk (no constant 7),
the integer constant 7 rewritten to 9 in the parsed chunk, and the
`is_vararg` byte flipped 2 -> 1. All five were caught (exit 1),
`--neg-all` exit 0.

**Failure recorded:** an intermediate revision of `check_entry.py`'s
`main()` had a control-flow bug - with **no arguments** it fell through to
`return 0` without running `verify()`, so the first "verify" evidence capture
was a false pass (exit 0, no output). Caught by noticing the missing output,
fixed (`no args -> verify()`), and both `entry_check_run.txt` and
`entry_negative_controls_run.txt` were re-captured afterwards. The
`--build --write` and `--neg` paths were unaffected (they returned through
their own branches).

The is_vararg post-pass was done by importing and reusing
`build_check.is_vararg_offset` (derives the offset from the parsed chunk,
validates it against `numparams`/`maxstacksize`, refuses unless the build
holds 1 and the original holds 2), applied at 0x28 for both variants.

### 3.5 Limits (part 3)

- **Nothing was run.** No install, no emulator, no console. Whether the game
  loads a locally compiled, changed-length chunk at this path is the same open
  question it was for the 0.3.1 probe; the entry behaviour on screen is tier D.
- The marker's visible effect (Try button gone) is a code-reading claim; the
  only precedent for `get_parts(...):set_visible(false)` running at that point
  is the shipped FROM_AMIIBO branch (B for the statement, D for the effect).
- Local names are invented (a stripped chunk stores none). Row 1 = Headgear
  comes from P6-EDIT-MENU's layout reading, not from a runtime observation.
- Plugin 0.4.0's half of the handshake (7 -> character list) is P10-UI-SLICE,
  not this task.

## Closing report

**Task ID: P10-EDIT-ENTRY. Status: DONE.** Evidence tier B throughout;
nothing run; runtime statements are D.

Changed files (all inside the assigned exclusive paths):

- `research/P10-EDIT-ENTRY.md` (this report)
- `builds/0.4.0-edit-entry/`: `check_entry.py`, `MANIFEST.json`, `README.md`,
  `variant_entry/mii_customizer_ui/{info.toml, ui/script_patch/chara_make/make_mii_edit_actor.lc}`,
  `variant_marker/mii_customizer_ui/{info.toml, ui/script_patch/chara_make/make_mii_edit_actor.lc}`
- `tools/lua-src/` (new files only + README): `make_entry_source.py`,
  `make_mii_edit_actor_entry.lua` (generated),
  `make_mii_edit_actor_entry_marker.lua` (generated), `README.md` (edits)
- `evidence/P10-EDIT-ENTRY/`: `arc_index_report.txt`, `dirinfo_probe.txt`,
  `hash40_check.txt`, `entry_source_gen.txt`, `entry_build_run.txt`,
  `entry_check_run.txt`, `entry_negative_controls_run.txt`,
  `build_check_run.txt`, `negative_controls_run.txt`
- `scratch/2026-10-05_P10-EDIT-ENTRY/`: `part1_order.py`,
  `part1_original_full.txt`, `part1_probe_full.txt`, `part1_sites.txt`,
  `arc_index.py` (+ `find_dirs` replaced by the `file_info_indices` chain),
  `arc_debug.py`, `dir_debug.py`, `dir_debug2.py`-`dir_debug5.py`,
  `hash40_check.py`
- workspace `gamedata/mii_customizer/P10-EDIT-ENTRY/`: `entry_build.lc`,
  `marker_build.lc` (compiled intermediates, game-derived)

Not touched: the byte-identical source, existing lua-src checks (except the
README), other builds, `dump/`, SD, remotes, `STATUS.md`.

Checks run: see the exit-code table in section 3.4 (all 0, controls all
caught). Verified: both variants are purely additive (`--strip`), the
pristine reconstruction still builds byte-identically, the staged trees
match the manifest, both `info.toml` parse, `main.p9` stores integer 7 to
`exit_value`, and no store carries a constant >= 9.

Open questions:

1. Does the loader accept a changed-length chunk at
   `ui/script_patch/chara_make/make_mii_edit_actor.lc`? (Unchanged since
   0.3.1; only a console boot settles it.)
2. Does Favorite-on-Headgear actually produce exit 7 on console, and does
   plugin 0.4.0 then open the character list? (Needs the user's console run;
   P10-UI-SLICE owns the plugin half.)
3. Is `btn_other_try` visibly present on the edit screen at open, so the
   marker's absence is noticeable? (The FROM_AMIIBO branch says yes; not
   observed.)
4. Why the patch tree keys DirInfos by file stem without extension (part 2b)
   - unresolved, and not needed for delivery; no index flag separates the
   patch path from the known-good special-move path.