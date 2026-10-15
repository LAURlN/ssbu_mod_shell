# P6-HAT-UI - headgear/outfit selection screen, script side (bytecode trace)

**Task ID:** P6-HAT-UI
**Status:** DONE (offline tracing only; no runtime claims)
**Date:** 2026-10-05
**Scope:** bytecode-level description of the SSBU Mii maker headgear/outfit selection
screen: how its list is filled, scrolled, labelled, confirmed, and every point where
it talks to native code. No mod screen design, no chunk edits, no emulator, no console.

Evidence tiers used throughout:

| tier | meaning |
|---|---|
| **B** | offline observation - I ran a tool and read its output |
| **C** | pinned source - the chunk bytes / disassembly, quoted exactly |
| **D** | hypothesis - inference, explicitly marked |

**Every statement in this report about what a native (host) call *does* is marked D.**
Nothing here was observed running.

---

## 0. Inputs, hashes, commands

### 0.1 Files analysed

Extracted with the workspace tool `tools/arc-extract` from workspace-relative
`gamedata/ssbu-13.0.4/data.arc` into workspace-relative
`gamedata/mii_customizer/P6-HAT-UI/ui/script/menu/chara_make/`:

| file | size (B) | sha256 |
|---|---|---|
| `make_mii_hat_actor.lc` | 1042 | `bf3648f5de367907e30cd1086a3cef957ef5d5c7447ef5aac4f144116d875e9b` |
| `make_mii_hat_body_layout.lc` | 5936 | `87a3706af2bbedb2059efb10d759acb72fd984c5b3334ef5187c976d10bac199` |
| `make_mii_utility.lc` | 3263 | `ff62bea184d129d9bd94137a92ba910314f3e9ef61bb2b663c2aa698d7109f25` |
| `make_mii_body_actor.lc` | 1046 | `b2e262ed584f8c108a77502bebb200afb38c969f123405690af0d9d695cf5518` |

All four are **byte-identical** (`cmp`, exit 0) to the copies already present in
`gamedata/mii_customizer/P5-UI-API/`. I read the P6 copies extracted for this task and
used the P5 copies only for the xref/context sweep. (B)

### 0.2 Patch-version check

Read `mods/ssbu_mod_new/AGENTS.md` first, then searched the archive index
`mods/ssbu_mod_new/dumps/decoded/arc_files.tsv`. (B)

**No `ui/script_patch/` version of any of the four exists.** The index lists only
`ui/script/menu/chara_make/make_mii_*.lc`. The single `ui/script_patch/chara_make/`
entry in the whole archive is `make_mii_edit_actor.lc` (line 526810), which is a
different script (the Mii *editor*, not the maker). No patch-version delta to
report. (B)

### 0.3 Commands run

```
# extraction (all four)
python tools/arc-extract ... gamedata/ssbu-13.0.4/data.arc \
    -> gamedata/mii_customizer/P6-HAT-UI/ui/script/menu/chara_make/<name>.lc

# structural validation - ALL FOUR exit 0
python mods/mii_customizer/tools/lua53-inspect/lua53_inspect.py verify <chunk>
#   version 0x53, float32, Instruction=4, size_t=8, int=4, debug stripped,
#   constant stream fully consumed, no trailing bytes

# second, independent listing with the game's own compiler
mods/mii_customizer/tools/luac53-game/bin/luac-game.exe -l -l <chunk>   # exit 0 on all four

# evidence dumps written to mods/mii_customizer/evidence/P6-HAT-UI/
#   header_*.txt summary_*.txt protos_*.txt constants_*.txt dis_*.txt

# derivation scratch (not a deliverable)
python mods/mii_customizer/scratch/2026-10-05_P6-HAT-UI/derive.py     # -> derived.json
python mods/mii_customizer/scratch/2026-10-05_P6-HAT-UI/callflow.py    # -> callflow.txt

# the deliverable check script
python mods/mii_customizer/evidence/P6-HAT-UI/check_p6_hat_ui.py      # 317 checks, 0 failures, exit 0
```

(B for all of the above: these are observed exit codes and file outputs.)

### 0.4 Reading conventions used in this report

- `chunk` / `proto` / `pc` are as produced by `tools/lua53-inspect`; `pc` is the
  0-based instruction index inside a prototype, `@0xNNNN` is its byte offset.
- `R[n]` is register `n`, `up[n]` is upvalue `n` of the current prototype,
  `self` is always `R[0]` in these chunks (they use no implicit `self` naming, so
  I write it as `R[0]` in tables and `self` in prose).
- `_ENV` resolution: the main prototype's upvalue 0 is `_ENV`; child prototypes
  chain to `_ENV` through their upvalue descriptors. Verified per prototype, see
  section 1.3.

---

## 1. Question 1 - structure: exports, call graph, globals read but never written

### 1.1 Prototype / instruction / constant counts (B, C)

| chunk | protos | instructions | constants | main proto instrs |
|---|---|---|---|---|
| `make_mii_hat_actor` | 6 | 70 | 33 | 16 |
| `make_mii_hat_body_layout` | 16 | 568 | 216 | 53 |
| `make_mii_utility` | 5 | 134 | 94 | 55 |
| `make_mii_body_actor` | 6 | 70 | 33 | 16 |

Per-prototype instruction counts:

- `hat_actor`: main 16, p0 28, p1 11, p2 5 (1 param), p3 5 (1 param), p4 5
- `hat_body_layout`: main 53, p0 2 (2p), p1 3 (1p), p2 23 (2p), p3 12 (2p),
  p4 12 (1p), p5 113 (6p), p6 22 (6p), p7 22 (6p), p8 29 (1p), p9 12 (1p),
  p10 1, p11 142 (1p), p12 35 (1p), p13 73 (1p), p14 14 (1p)
- `utility`: main 55, p0 24 (3p), p1 24 (3p), p2 24 (3p), p3 7 (2p)
- `body_actor`: same shape as `hat_actor` (6 / 70 / 33)

### 1.2 What each chunk writes into `_ENV` (C)

`make_mii_hat_actor` and `make_mii_body_actor` write a **flat table of 6 named
functions** - this is the actor's public API to native code:

| exported name | main.proto | pc |
|---|---|---|
| `main` | main | 4-15 |
| `initialize` | p1 | 0-10 |
| `update_in` / `update_out` / `update` | p0 | 0-27 |
| `set_select_id` | p2 | 0-4 |
| `set_sort_id` | p3 | 0-4 |
| `get_decided_id` | p4 | 0-4 |
| `is_finish` | main | 0 (boolean, not a function) |

`make_mii_hat_body_layout` writes a **table** (module), built at main pc46-51
(`NEWTABLE` -> field stores -> `setmetatable` tailcall at pc50). Its 15 fields map
1:1 onto the 15 child prototypes, in this order:

| field | proto | instrs |
|---|---|---|
| `set_select_id` | p0 | 2 |
| `get_decided_id` | p1 | 3 |
| `set_enable_input` | p2 | 23 |
| `set_sort_id` | p3 | 12 |
| `update_sort_text` | p4 | 12 |
| `initialize` | p5 | 113 |
| `initialize_body` | p6 | 22 |
| `initialize_hat` | p7 | 22 |
| `update_in` | p8 | 29 |
| `update_out` | p9 | 12 |
| `update_idle` | p10 | 1 |
| `update_main` | p11 | 142 |
| `update_sub_list_window_in` | p12 | 35 |
| `update_sub_list_window` | p13 | 73 |
| `update` | p14 | 14 |

`make_mii_utility` writes **32 camera constants** (numbers) and a table with 4
functions: `set_defines_camera` (p0), `set_right_side_0_fighter_camera` (p1),
`set_right_side_1_fighter_camera` (p2), `set_head_position_fighter_camera` (p3).

### 1.3 `_ENV` upvalue indices per prototype (C, verified)

| chunk | prototypes holding `_ENV` | index |
|---|---|---|
| `hat_actor` | main, p0, p1 | 0, 0, 1 |
| `body_actor` | main, p0, p1 | 0, 0, 1 |
| `hat_body_layout` | main, p3, p5, p6, p7, p9, p11, p12, p13 | 0, 0, 0, 1, 1, -, 0, 0, 0 |
| `utility` | main, p0, p1, p2, p3 | 0 in all |

**Caveat, important:** `hat_body_layout` p9 has an upvalue `(instack=1, idx=9)` that
is **not** `_ENV` - it is the `common/ui_common` module table. p6 and p7 hold
`_ENV` at index 1. Reading p9's upvalue 0 as `_ENV` would produce wrong names.

### 1.4 Which chunk calls into which (C)

```
make_mii_hat_actor   --require-->  menu/chara_make/make_mii_hat_body_layout   (main pc0-3)
make_mii_body_actor  --require-->  menu/chara_make/make_mii_hat_body_layout   (main pc0-3)
make_mii_hat_body_layout --require--> common/state_function                 (main pc10-11)
                        --require--> common/ui_common                        (main pc14-15)
make_mii_utility     --require--> nothing; no caller found
```

**`hat_actor` and `body_actor` are the only two entry points**, and both are thin.
Their main prototype is 16 instructions: build the require path, `require` the
layout module, then assign 6-7 names into `_ENV`. Their `main.p1` (`initialize`,
11 instructions) is the only real call:

| chunk | proto | pc | call | args |
|---|---|---|---|---|
| `hat_actor` | main.p1 | 9 | `initialize_hat` | 6: `LayoutRootList.make_mii_hat_body`, `LayoutRootList.com_sort_window`, global `scroller`, global `sub_list_window`, global `sub_list_window_facade` (pc2-9) |
| `body_actor` | main.p1 | 9 | `initialize_body` | same 6, identical pc2-9 |

**`make_mii_utility` is required by nobody** among the 86 UI chunks extracted for
P5-UI-API (string sweep for the module path returned 0 hits). (B) Who requires it,
if anyone, is unknown - see unresolved edges.

### 1.5 The only difference between the hat chunk and the outfit chunk (C)

`hat_actor` vs `body_actor` are near-identical: same 6/70/33 shape, and the only
substantive differences are

1. main.p0 pc3 - the title message key constant:
   `"mnu_mmiif_setup_hat_title"` vs `"mnu_mmiif_setup_outfit_title"`
2. main.p1 pc1 - which layout entry point is called:
   `initialize_hat` vs `initialize_body`
3. byte offsets shift by 1-4 because those two constants differ in length
   (e.g. `body_actor` main.p1 pc9 is `@0x0288` vs `hat_actor` `@0x0285`).

**This is the answer to Question 5 in structural terms:** the headgear/outfit switch
is *not* a branch inside one script. It is two separate actor chunks that share one
layout module and differ only in a title key and which `initialize_*` they call.
The *layout* module never learns which of the two it is serving; `initialize_hat`
(p7) and `initialize_body` (p6) are 22 instructions each and differ only in the
animation part they play (`category_01` vs `category_00`, section 6.3).

### 1.6 Globals read but never written by these four chunks (C)

Derived mechanically (`scratch/.../derive.py`, output `derived.json`) by resolving
every `GETTABUP` against the `_ENV` chain and classifying each access read/write.

| chunk | read, never written |
|---|---|
| `hat_actor` | `COMFRAME_FOOTERMESSAGEAREA_NONE`, `ComFrameActor`, `UiScriptPlayer`, `LayoutRootList`, `coroutine`, `scroller`, `sub_list_window`, `sub_list_window_facade` (+ `is_finish`, also written) |
| `body_actor` | identical set |
| `hat_body_layout` | `BUTTON_ID_NONE`, `ComFrameActor`, `INPUT_BUTTON_DOWN`, `INPUT_BUTTON_UP`, `INPUT_OPEN_SORT_WINDOW`, `LayoutButtonSelector`, `LayoutButtonSelectorConfig`, `SCROLLER_ITEM_NUM`, `UI_SE_ID_CURSOR`, `UiScriptPlayer`, `UiSoundManager`, `setmetatable`, `string`, `LayoutRootList` |
| `utility` | `MII_TYPE_SWORDSMAN`, `MII_TYPE_GUNNER`, `setmetatable`, plus the 28 camera constants it wrote itself |

**`hat_body_layout` writes no globals at all** - every one of its outputs goes
through `self` or the returned module table. (B)

---

## 2. Question 2 - the list: what object it is, and the fact that Lua never fills it

This is the headline finding of the task.

### 2.1 The scrolling list object is a host-provided global named `scroller` (C)

There is **no constructor call for the scroller anywhere in these four chunks.**
`scroller` is read from `_ENV` (`up[3]` in `hat_actor`/`body_actor` main.p1, pc2-9;
`up[3]`-derived in `hat_body_layout`) and stored unchanged into the module's state
table:

| chunk | proto | pc | code |
|---|---|---|---|
| `hat_body_layout` | main.p5 (`initialize`) | 18 | `R[?].scroller = up[3]` (the `scroller` argument) |

Cross-check (B): in the P5-UI-API classification of all 86 UI chunks, `scroller`
is a **read-only global** as far as the Mii scripts are concerned - the only two
chunks anywhere in `ui/script/` that *write* `scroller` are `collection_tips_list.lc`
and `option_button_top.lc`, and neither is a Mii script. So `scroller` is
constructed and owned by native code. (D: that the game constructs it; the fact that
these chunks only read it is B.)

### 2.2 The four methods the layout calls on it (C)

All in `hat_body_layout`. `R[0]` is the module state table.

| method | protos / pc | args | returns used |
|---|---|---|---|
| `set_enable` | p2 pc7 | `(flag)` - 2-call form | no |
| `set_focus` | p2 pc17, p8 pc12, p11 pc34, p11 pc75, p11 pc123, p13 pc36 | `(true/false)` | no |
| `select_item` | p11 pc47, p11 pc64, p8 pc5 | `(index, scroll)` - 3-call form | no |
| `redraw_all_items` | p3 pc10, p8 pc15, p13 pc68 | none | no |
| `get_selected_item` | p11 pc100 | none | **yes** (compared to `BUTTON_ID_NONE` at pc101-104) |
| `get_decided_item` | p11 pc83 | none | **yes** (stored to `self.decided_id`, pc84) |
| `has_focus` | p11 pc28, p12 pc2 | none | yes (both branch on it) |
| `special_input_is_upward` | p11 pc107 | `(true)` | yes |
| `special_input_is_downward` | p11 pc113 | `(true)` | yes |

So: cursor state is read from and driven through the scroller, but **the content of
the scroller is never touched from Lua.**

### 2.3 How many rows are visible, and how many in total - ANSWER: neither is in Lua (C)

- **Total item count: not in these chunks.** There is no `get_item_num`, no
  `set_item_num`, no `#list`, no count variable, no `invoke` that returns a count.
  The only numbers that reach the scroller's index space are `self.select_id`
  (p8 pc5) and the return of the `get_top_index` bridge (p11 pc59/64).
- **Rows per page: only as a global constant.** `SCROLLER_ITEM_NUM` is read from
  `_ENV` and used exactly once, at p11 pc43-47:
  `scroller.select_item(SCROLLER_ITEM_NUM - 1, true)`.
  That it means "rows visible per page" is **D** - the arithmetic `- 1` with a
  `true` scroll flag (jump-to-page) is consistent with it, but nothing in these
  chunks states it.
- **A row is never filled from Lua.** There is no row callback, no per-row loop, no
  `set_text_message` on a row pane, no icon/texture call, no "new"/"equipped" mark
  setter anywhere in the four chunks. The *only* `set_text_message` in the whole set
  is on the sort label pane (section 7). The only `string.format` calls build
  *animation part names*, not row text (section 6.3).

**Conclusion (C for the absence, D for the reason):** the scroller's item model -
total count, row contents, icons, marks, and the scrollbar geometry - is entirely
native. Lua's job on this screen is: hand the scroller to the layout, move the
cursor, ask native code to re-sort, and ask native code what the user decided.

### 2.4 Part and pane names actually used (C)

| name | proto / pc | use |
|---|---|---|
| `"selector_sort"` | p5 pc38-42 | `selector.setup(main_view, "selector_sort", config)` |
| `"scr_sort"` | p5 pc44-47 | `selector.setup_button("scr_sort")`; also `main_view.get_parts("scr_sort")` at pc21-24 |
| `"set_txt_list"` | p5 pc27 | `.get_pane("set_txt_list")` -> `self.sort_text_pane` |
| `"set_parts_scr_item_%02d"` | p6 pc17, p7 pc17 | `string.format(...)` -> `play_animation_parts` |
| `"category_01"` / `"category_00"` | p6 pc18, p7 pc18 | the animation name passed to `play_animation_parts` |

Only **one** pane is ever touched by name: `set_txt_list`, and it is the sort
label, not a row. (B)

### 2.5 How the item text is produced - not in Lua

Note there is **no item-info bridge** in this group. The P5-UI-API `ui_api.json`
records `sort_id_list` (3 call sites, 2 args), `get_top_index` (1 site, 1 arg),
`backup_list_selected_id` (3 sites, 1 arg) and `select_list_from_backup_id`
(3 sites, 1 arg) - **none of which is an item-info or label query**. The 4 sites in
these chunks are a strict subset of those counts. (B)

---

## 3. Question 3 - every native bridge call, with argument counts and provenance

### 3.1 The complete bridge inventory

Across all four chunks there are exactly **6 `UiScriptPlayer.invoke` call sites, all
of them in `make_mii_hat_body_layout`**, using only **4 distinct bridge names**.
`hat_actor`, `body_actor` and `utility` contain **zero** invoke calls (B).

| # | bridge name | proto | pc | args (n) | argument provenance | return used | what it is asked to do (D) |
|---|---|---|---|---|---|---|---|
| 1 | `sort_id_list` | main.p3 (`set_sort_id`) | 7 | **2** | `R[4]` = the module state table (name receiver, first arg), `R[0].sort_id` = `self.sort_id`, the 2nd parameter of `set_sort_id` | 0 results | re-sort the native list by mode `sort_id` |
| 2 | `sort_id_list` | main.p5 (`initialize`) | 111 | **2** | `R[51]` = the module state table, `R[0].sort_id` - note `sort_id` is forced to `0` by the store at **pc104** immediately before, so this initialises the list to sort mode 0 | 0 results | same, on screen entry |
| 3 | `sort_id_list` | main.p13 (`update_sub_list_window`) | 65 | **2** | `R[24]` = the module state table, `R[0].sort_id` - but `self.sort_id` was **just overwritten at pc58** with the sub-window result | 0 results | apply the sort mode the user just picked, then `scroller.redraw_all_items()` at pc68 |
| 4 | `get_top_index` | main.p11 (`update_main`) | 59 | **1** | `R[19]` = the module state table; **the only argument is the receiver** - no sort id, no index, nothing | **1 result**, passed straight to `scroller.select_item(..., true)` at **pc64** | ask the scroller's top visible index, then jump the cursor there; **D**: it reads the native list's scroll position |
| 5 | `backup_list_selected_id` | main.p12 (`update_sub_list_window_in`) | 10 | **1** | `R[6]` = the module state table | 0 results | **D**: save the current selection so it can be restored if the user backs out of the sort window |
| 6 | `select_list_from_backup_id` | main.p13 (`update_sub_list_window`) | 40 | **1** | `R[18]` = the module state table | 0 results | **D**: restore the selection saved by #5; runs only on the cancel branch (see pc30-40) |

Grouping per the requested categories:

| category | bridges on this screen |
|---|---|
| item count | **none** |
| item info / label / icon | **none** |
| preview on the Mii model | **none** |
| confirm | **none** - confirm is `scroller.get_decided_item()` (pc83), not a bridge |
| cancel | **none** - cancel is `main_virtual_input.is_cancel()` (pc2) and `ComFrameActor.press_cancel()` (pc7) |
| category switch | **none** - the headgear/outfit switch is a different actor chunk (section 1.5) |
| list state / re-sort / scroll position | `sort_id_list`, `get_top_index`, `backup_list_selected_id`, `select_list_from_backup_id` |

**`get_top_index` is the only bridge whose return value is used at all**, and it is
the only one with a non-zero result count. (B)

### 3.2 Argument form, precisely

All 6 sites use the same 3-instruction shape:

```
GETTABUP  R,  <_ENV idx>,  "UiScriptPlayer"     ; receiver
GETTABUP  R,  <_ENV idx>,  "invoke"             ; method
CALL      A=R, B=<nargs+1>, C=<nresults+1>
```

so `B` is 3 for the 2-argument sites (#1-#3) and 2 for the 1-argument sites
(#4-#6); `C` is 1 for the 0-result sites and 2 for `get_top_index`. The first
argument is the module state table in all six cases - i.e. the bridge always
receives the screen's state table as its "self"/name argument. (C)

### 3.3 Cross-check against the full-UI API survey (B)

`mods/mii_customizer/evidence/P5-UI-API/ui_api.json` records, across all 86 UI
chunks: `sort_id_list` 3 calls / 2 args, `get_top_index` 1 call / 1 arg,
`backup_list_selected_id` 3 calls / 1 arg, `select_list_from_backup_id` 3 calls /
1 arg. Our 6 sites are **exactly** the `get_top_index` site and exactly all 3
`sort_id_list` sites, but only 1 of the 3 `backup_list_selected_id` and 1 of the 3
`select_list_from_backup_id` sites. So the other two chunks that use the backup
pair are not in this task's four files. (B)

### 3.4 Other host calls that are not `invoke` but are still native boundaries

For completeness, these are host-object methods rather than string-keyed bridges,
all read from `_ENV` and therefore provided by the game (their behaviour is **D**):

| object | methods called | where |
|---|---|---|
| `ComFrameActor` | `set_sub_title`, `set_footer_area`, `press_cancel`, `is_cancelled` | hat/body actor p0 pc4/pc23; layout p11 pc7/pc130 |
| `LayoutButtonSelectorConfig` | `new()` | p5 pc31 |
| `LayoutButtonSelector` | `new()` | p5 pc35 |
| `UiSoundManager` | `play_se(UI_SE_ID_CURSOR)` | p11 pc79, p11 pc127 |
| `LayoutRootList` | `.make_mii_hat_body`, `.com_sort_window` (table lookups, passed as args) | hat/body actor main.p1 pc2-9 |

Plus the `scroller` and `sub_list_window` methods in sections 2.2 and 5.4.

---

## 4. Question 4 - input: cursor, page scroll, confirm, cancel

All of the main-screen input lives in **one prototype**: `hat_body_layout` main.p11,
`update_main`, **142 instructions**, pc0-141. It is the largest prototype in the set.

### 4.1 The state machine that wraps it (C)

`main.p5` (`initialize`, 113 instrs) registers four states, all via the same
5-argument `setup` call (pc58-85):

| state constant | name arg (up) | callback | pc |
|---|---|---|---|
| `STATE_UPDATE_NONE` | up[2] | `self.update_idle` | 64 |
| `STATE_UPDATE_MAIN` | up[3] | `self.update_main` | 71 |
| `STATE_UPDATE_SUB_LIST_WINDOW_IN` | up[4] | `self.update_sub_list_window_in` | 78 |
| `STATE_UPDATE_SUB_LIST_WINDOW` | up[5] | `self.update_sub_list_window` | 85 |

All four are `up[2]['setup'](name, self, callback, <const>, <extra>)` - five
arguments after the receiver. `up[2]` is the `common/state_function` module required
at main pc10-11. **What each argument means is D** (section 10).

`main.p14` (`update`, 14 instrs) is the driver's pump: `state.update()` at pc2,
`state.get()` at pc5, compared against `up[1]` at pc6-9, returning `true`/`false`.
That boolean is what the actor's yield loop waits on.

### 4.2 Cancel (C)

| pc | code |
|---|---|
| p11 pc1-2 | `main_virtual_input.is_cancel()` -> 1 result |
| p11 pc3-5 | branch |
| p11 pc6-7 | `ComFrameActor.press_cancel()` - no args |
| p11 pc8-9 | `state.set(up[4])` i.e. go to `STATE_UPDATE_SUB_LIST_WINDOW` |

And the reverse edge, from the sub-window state:

| pc | code |
|---|---|
| p11 pc129-130 | `ComFrameActor.is_cancelled()` -> 1 result |
| p11 pc131-135 | branch |
| p11 pc136 | `state.set(up[4])` |
| p11 pc137-140 | `main_virtual_input.set_enable(false)` |

**D:** `press_cancel()` tells the frame actor that cancel was accepted;
`is_cancelled()` reads back whether it is still in a cancelling state. The exact
semantics of both are native.

### 4.3 Sort-button selection (C)

| pc | code |
|---|---|
| p11 pc10-11 | `selector.get_decided_button_id()` -> 1 result |
| p11 pc12-15 | branch |
| p11 pc16-18 | `state.set(up[?])` -> `STATE_UPDATE_SUB_LIST_WINDOW_IN`, then `RETURN` |

This is the only exit from `update_main` other than confirm.

### 4.4 Cursor movement: UP / DOWN (C)

Focus is arbitrated first:

| pc | code |
|---|---|
| p11 pc23 | `selector.has_focus()` |
| p11 pc28 | `scroller.has_focus()` |
| p11 pc34 | `scroller.set_focus(false)` (when the selector has focus) |

Then, two branches:

**UP branch (pc37-47):**

| pc | code |
|---|---|
| p11 pc37-38 | `main_virtual_input.is_pressed(INPUT_BUTTON_UP)` -> 1 |
| p11 pc43-47 | `scroller.select_item(SCROLLER_ITEM_NUM - 1, true)` |

**DOWN branch (pc51-64):**

| pc | code |
|---|---|
| p11 pc51-52 | `main_virtual_input.is_pressed(INPUT_BUTTON_DOWN)` -> 1 |
| p11 pc56-64 | **extra work here**: `UiScriptPlayer.invoke("get_top_index")` at **pc59** (1 result), then `scroller.select_item(<result>, true)` at **pc64** |

**The asymmetry is the interesting part (C, meaning D).** Plain UP moves the cursor
by `-(rows per page)`. Plain DOWN does *not* move by `+(rows per page)` - it instead
asks native code for the list's current top index and jumps the cursor there. That
strongly suggests **D:** the last page is shorter than a full page, so
`top + SCROLLER_ITEM_NUM` can run past the end, and the game normalises DOWN by
asking the scroller where the top actually is instead of adding a constant.

### 4.5 Page scroll (shoulder buttons) (C)

| pc | code |
|---|---|
| p11 pc100 | `scroller.get_selected_item()` -> 1 |
| p11 pc101-104 | compare with `BUTTON_ID_NONE` |
| p11 pc105-106 | branch |
| p11 pc107 | `scroller.special_input_is_upward(true)` -> 1 |
| p11 pc108-112 | branch -> focus swap at pc119/123 + `UiSoundManager.play_se(UI_SE_ID_CURSOR)` at pc127 |
| p11 pc113 | `scroller.special_input_is_downward(true)` -> 1 |
| p11 pc114-118 | branch -> same focus swap + sound |

The `get_selected_item() == BUTTON_ID_NONE` guard means: **D** - the page-scroll
path only runs when the cursor is parked on the empty slot below the last item, i.e.
this is the "flip the page" behaviour.

### 4.6 Confirm (C)

| pc | code |
|---|---|
| p11 pc82-83 | `scroller.get_decided_item()` -> **1 result** |
| p11 pc84 | `R[0].decided_id = <result>` - stored into the module state table |
| p11 pc88-91 | `state.set(up[?])` -> leaves `STATE_UPDATE_MAIN` (the state that ends the screen) |
| p11 pc95 | `main_virtual_input.set_enable(false)` |

**No bridge commits the choice.** (C) The confirmed index is stored in
`self.decided_id` and handed back out through the layout's `get_decided_id`
(main.p1, 3 instructions) to `hat_actor`/`body_actor`'s `get_decided_id`
(main.p4, 5 instructions, a `TAILCALL` at pc2) - that is the value the actor's
`is_finish` flag is polled for in the yield loop (section 6.1). **D:** that is how
native code learns what the user picked.

`UiSoundManager.play_se(UI_SE_ID_CURSOR)` at **pc76-79** (cursor moved off the empty
slot) and **pc124-127** (page scroll) are the only sound cues. (C)

---

## 5. Question 5 - categories / tabs

### 5.1 Headgear <-> outfit is not in one script (C)

Already shown in section 1.5. Two chunks, `make_mii_hat_actor.lc` and
`make_mii_body_actor.lc`, are structurally identical (6 protos / 70 instructions /
33 constants each) and share `make_mii_hat_body_layout.lc`. **There is no branch,
no state and no parameter anywhere in the four chunks that selects between
headgear and outfit.** Whoever opens the screen loads one actor chunk or the other
- that decision is native. (D)

### 5.2 The only in-screen switch: the sort sub-window (C)

The one category-like switch the script does own is the **sort mode selector**,
which is a separate overlay window:

| step | proto / pc | code |
|---|---|---|
| shortcut disabled | p5 pc49-53 | `selector.set_shortcut(INPUT_OPEN_SORT_WINDOW, false)` |
| button selected | p5 pc55-57 | `selector.select_button(up[1])` |
| open | p12 pc2 | `scroller.has_focus()` gate |
| backup | p12 pc10 | `invoke("backup_list_selected_id")` |
| disable main input | p12 pc13 | `self.set_enable_input(false)` |
| show sub view | p12 pc17 | `sub_view.set_visible(true)` |
| enable sub input | p12 pc21 | `sub_virtual_input.set_enable(true)` |
| activate | p12 pc25 | `sub_list_window.activate(sub_list_window_facade)` |
| open at current | p12 pc29 | `sub_list_window.open(self.sort_id)` |
| switch state | p12 pc33 | `state.set(up[2])` -> `STATE_UPDATE_SUB_LIST_WINDOW_IN` |
| tick | p13 pc3 | `sub_list_window.update(sub_virtual_input)` |
| result | p13 pc7 | `sub_list_window.get_result()` -> **2 values** |
| busy gate | p13 pc12 | `sub_list_window.is_busy()` -> 1 |
| hide | p13 pc18 / pc22 | `sub_view.set_visible(false)` / `sub_virtual_input.set_enable(false)` |
| deactivate | p13 pc26 | `sub_list_window.deactivate(sub_list_window_facade)` |
| cancel path | p13 pc30-40 | `invoke("select_list_from_backup_id")` at pc40, then `state.set(up[2])` at pc49 |
| accept path | p13 pc58 | `self.sort_id = <result>` |
| relabel | p13 pc60 | `self.update_sort_text()` |
| re-sort | p13 pc65 | `invoke("sort_id_list")` |
| redraw | p13 pc68 | `scroller.redraw_all_items()` |
| close | p13 pc71 | `sub_list_window.close()` |

`set_enable_input` (main.p2, 23 instrs) is the single gate: pc3
`main_virtual_input.set_enable(flag)`, pc7 `scroller.set_enable(flag)`, pc11
`selector.set_enable(flag)`, pc17 `scroller.set_focus(false)`, pc21
`selector.set_focus(false)`.

**D:** `sub_list_window.get_result()`'s two return values are the sort mode and some
second value (a result/selected flag, or a "was cancelled" flag) that decides the
accept-vs-cancel branch; the branch is on the first value. Nothing in these chunks
names it.

---

## 6. The actor main loop, the selector, and the nine animation parts

### 6.1 The actor's frame loop (C) - `hat_actor` / `body_actor` main.p0, 28 instructions

| pc | code |
|---|---|
| p0 pc0 | `is_finish = false` (global write) |
| p0 pc1-4 | `ComFrameActor.set_sub_title(<"mnu_mmiif_setup_hat_title">)` / `"..._outfit_..."` |
| p0 pc6-7 | `self:update_in()` |
| p0 pc8-11 | `while is_finish == false do` |
| p0 pc12-13 | `is_finish = self:update()` - 1 result |
| p0 pc14-18 | if truthy -> `coroutine.yield()` and loop again |
| p0 pc20-23 | `ComFrameActor.set_footer_area(COMFRAME_FOOTERMESSAGEAREA_NONE)` |
| p0 pc25-26 | `self:update_out()` |

This is a **cooperative coroutine**: the actor yields back to native code every
frame while the layout decides whether the screen is finished. `is_finish` is a
**global**, written at pc0 and pc12, read at pc9 - it is the only piece of state
shared between the actor and the layout's `get_decided_id` path. (C; the
coroutine-driven framing is D.)

`update_out` (layout main.p9, 12 instrs) hides the view and disables input:
pc3 `main_view.play_animation_and_wait(...)` (an `ui_common` helper - up[0]),
pc6 `set_enable_input(false)`, pc10 `main_view.set_visible(false)`. (C)

### 6.2 The button selector (C) - `hat_body_layout` main.p5

| pc | code |
|---|---|
| pc31 | `LayoutButtonSelectorConfig.new()` -> 1 result |
| pc32 | field `is_unique_se = true` set on the config |
| pc35 | `LayoutButtonSelector.new()` -> 1 result |
| pc42 | `selector.setup(main_view, "selector_sort", <config>)` - 4 args |
| pc47 | `selector.setup_button("scr_sort")` - 3 args |
| pc53 | `selector.set_shortcut(INPUT_OPEN_SORT_WINDOW, false)` - 4 args |
| pc57 | `selector.select_button(up[1])` - 2 args |

**`is_unique_se = true` (C)** is the only configuration set. **D:** it most likely
means "single exclusive selection" for the sort-button group. Selector methods
used later: `get_decided_button_id` (p11 pc11), `has_focus` (p11 pc23),
`set_focus` (p2 pc11/pc21, p8, p11 pc71/119, p13 pc45), `set_enable` (p2 pc11),
`select_button` (p5 pc57).

### 6.3 Nine animation parts (C)

`main` pc7 loads the constant **9**. `main.p6` (`initialize_body`, 22 instrs) and
`main.p7` (`initialize_hat`, 22 instrs) both do, at pc6, a call to `initialize`
with the same 6 arguments, then:

| pc | code |
|---|---|
| p6/p7 pc7-15 | `for i = 0, up[0], 1` loop |
| p6/p7 pc17 | `string.format("set_parts_scr_item_%02d", i)` -> 1 result |
| p6/p7 pc18-19 | `main_view.play_animation_parts(<formatted name>, <"category_01"\|"category_00">)` |

The loop bound `up[0]` is a constant loaded in the enclosing chunk, and **D:** it is
the count of parts in `main_root` (the layout XML/parts tree), which is why the
literal `9` is not visible here - the loop is data-driven from the host's part list.

So the *only* per-item loop in the whole set is an **animation** loop (staggered
open animation for 9 category icons), not a row-fill loop. That distinction matters
for the mod: a long list does not need a Lua row loop, because there is none.

### 6.4 `initialize` (p5, 113 instrs) at a glance (C)

Order of operations, by pc: view/input wiring pc2-16 (`main_view.get_root_view`,
`get_virtual_input` for both the main root and the `com_sort_window` root),
`main_view.stop_animation_at_end` pc10, `self.scroller = <arg>` **pc18**,
`self.sub_view` / `self.sub_virtual_input` pc13-16, pane lookup
`main_view.get_parts("scr_sort").get_pane("set_txt_list")` **pc21-28**, selector
construction pc29-57 (section 6.2), the four state registrations pc58-85
(section 4.1), `main_view.set_visible(false)` / `sub_view.set_visible(false)` /
`sub_virtual_input.set_enable(false)` / `set_enable_input(false)` pc92-103,
`update_sort_text()` **pc106**, `sort_id = 0` store **pc104**, and finally
`invoke("sort_id_list")` at **pc111**.

`set_select_id` (main.p0, 2 instrs) and `get_decided_id` (main.p1, 3 instrs) are
the trivial accessors; `set_sort_id` (main.p3, 12 instrs) calls `update_sort_text()`
(pc2), `invoke("sort_id_list")` (pc7) and `scroller.redraw_all_items()` (pc10) - the
same three-step "relabel, re-sort, redraw" trio that p13 repeats at pc60/65/68.

---

## 7. Question 6 - text: where every visible string comes from

**All text on this screen is set from a message-key constant in Lua. Nothing is
set from a bridge return value.** (C) There is no bridge on this screen that
returns a string.

### 7.1 The two text sites, with their constants (C)

| what | chunk / proto / pc | call | constant |
|---|---|---|---|
| screen title | `hat_actor` main.p0 **pc1-4**; `body_actor` main.p0 **pc1-4** | `ComFrameActor.set_sub_title(<key>)` | `"mnu_mmiif_setup_hat_title"` / `"mnu_mmiif_setup_outfit_title"` |
| sort label | `hat_body_layout` main.p4 **pc10** | `sort_text_pane.set_text_message(tbl[sort_id + 1])` | see below |

### 7.2 The sort-label table (C)

`main.p4` (`update_sort_text`, 12 instrs) builds a 3-element table at **pc0-4**:

```
{ "mnu_mmiif_sort_1", "mnu_mmiif_sort_3", "mnu_mmiif_sort_4" }
```

and indexes it `tbl[sort_id + 1]` at **pc8-10** before calling
`set_text_message`. The pane was obtained once, at `initialize` **pc21-28**, as:

```
main_view.get_parts("scr_sort").get_pane("set_txt_list")
```

Two things worth noting: the message keys are **`_1`, `_3`, `_4`** - there is no
`_2` - and the table is 3 long. **D:** the sort modes are 0, 1, 2 mapping onto
message ids 1, 3, 4, i.e. one sort mode's message key is missing or shares a
neighbour's. Nothing in these chunks explains the gap.

### 7.3 Row labels

**There are none.** See section 2.3. The headgear/outfit row labels, their icons and
their "new"/"equipped" marks are drawn by native code from the scroller's own item
model. (C for the absence of any call; D for the native code doing it.)

---

## 8. Question 7 - what is NOT in Lua

Judged strictly from which calls exist and which do not (C for the absence, D for
the attribution to native code).

| left to native code | evidence it is absent from Lua |
|---|---|
| **construction and ownership of the list widget** (`scroller`) | no constructor call; the name is only read from `_ENV` (p5 pc18 stores the argument) |
| **the item count / total number of headgear** | no `get_item_num` / `set_item_num` / `#` / count arithmetic anywhere; no bridge returns a count |
| **per-row content: label text, icon, texture** | no `set_text_message` on a row pane, no image/icon/texture call in any of the 4 chunks |
| **"new" / "equipped" marks** | no such setter or flag appears in any constant of any of the four chunks |
| **the scrollbar, page geometry, and rows-per-page** | `SCROLLER_ITEM_NUM` is a bare global constant, used once (p11 pc43-47), never defined here |
| **actual scrolling** | `scroller.special_input_is_upward/downward(true)` (p11 pc107/113) and `select_item(i, true)` - Lua asks, native scrolls (**D**) |
| **the item list itself - which headgear exist, in what order** | `sort_id_list` (3 sites) only *re-sorts* it; nothing ever populates it |
| **commit of the confirmed choice** | confirm is `scroller.get_decided_item()` -> stored to `self.decided_id` (p11 pc83-84); no bridge writes the selection back |
| **which screen to open (headgear vs outfit)** | two separate actor chunks, chosen by the caller (section 5.1) |
| **the row animation timing** | `play_animation_parts` per part name; the part *count* is `up[0]`, i.e. host data (section 6.3) |
| **camera placement for the Mii model preview** | `make_mii_utility` calls `set_head_position_fighter`, `set_default_parameter`, `set_right_side_fighter` with numeric constants - it sets camera numbers, it does not create or update a preview (p0 pc22, p1 pc22, p2 pc22, p3 pc5) |

**In one sentence (D):** Lua owns the *frame choreography* - what is visible, which
widget has focus, which state the screen is in, what the title and sort label say -
while native code owns the *data* - which items exist, what each row looks like,
how many there are, and what the final choice means.

---

## 9. Question 8 - is any Mii class or fighter kind read here?

**Yes, but only in `make_mii_utility`, and only as a camera selector.**

| proto | pc | reads | then |
|---|---|---|---|
| `utility` main.p0 | 1-2 | `MII_TYPE_SWORDSMAN` | picks the F/S/G camera triple |
| `utility` main.p0 | 8-9 | `MII_TYPE_GUNNER` | |
| `utility` main.p1 | 1-9 | both, same shape | right-side-0 fighter camera |
| `utility` main.p2 | 1-9 | both, same shape | right-side-1 fighter camera |
| `utility` main.p3 | 0-5 | neither - just branches to one of 4 `HAT_SELECT_CAMERA_*` sets | `set_head_position_fighter(self, X, Y, LOOK_AT_Y, Z)` - 5-call form at pc5 |

**In `hat_actor`, `body_actor` and `hat_body_layout`: no fighter kind and no Mii
class is read at all.** (C) Those three chunks never touch `MII_TYPE_*`, never read
the Mii model, and never index anything by fighter. The screen is identical for
every Mii body type.

`make_mii_utility`'s 32 written constants (all `F_*_CAMERA_*`, `HAT_SELECT_CAMERA_*`)
are pure numbers - positions and translates. Its 4 exported functions take the
camera object as their 2nd parameter and push numbers into it. (C)

---

## 10. Unresolved edges

Everything in this section is **D**. None of it was observed running, and none of it
can be resolved from these four chunks alone.

1. **Where the `scroller` comes from.** No constructor in Lua; `scroller` is a
   pre-existing global. What binds it to *this* screen's list - and whether the
   binding is per-screen or per-actor - is unknown. **Needed next:** find the chunk
   that assigns `scroller`, or find the native side that does.
2. **What fills the list.** No count, no row callback, no item-info bridge. Whether
   rows come from a native Mii-data table keyed by the actor, from the part tree, or
   from a saved Mii, is unknown.
3. **`sort_id_list` (2 args: state table, sort id).** Does it sort an existing native
   array, rebuild it, or query? Does the sort id map 1:1 onto `mnu_mmiif_sort_{1,3,4}`?
   Unknown.
4. **`get_top_index` (1 arg, 1 result).** Whether the result is a row index or an
   absolute item index, and whether it can exceed the item count, is unknown. This
   matters because it is the only value that positions the cursor from outside Lua.
5. **`backup_list_selected_id` / `select_list_from_backup_id` (1 arg each).** What
   state they save/restore, and whether the save is a single slot or a stack, is
   unknown. Note the other two call sites of each are in chunks outside this task.
6. **`SCROLLER_ITEM_NUM`.** Almost certainly rows per page (**D**, from the
   `- 1` / `+ 0` page-jump arithmetic), but the value itself is a global defined
   outside these chunks.
7. **`BUTTON_ID_NONE` as a scroller selection.** The page-scroll path triggers on
   `get_selected_item() == BUTTON_ID_NONE`, i.e. a "no item" sentinel that is part of
   the scroller's index space. Whether it is a real extra row or a null is unknown.
8. **`sub_list_window.get_result()`'s two return values.** Which one is the sort id
   (assigned at p13 pc58) and what the second is, is unknown. `is_busy()` (pc12) is
   also unexplained.
9. **`LayoutButtonSelector` / `LayoutRootList` / `LayoutButtonSelectorConfig`** -
   `is_unique_se` (p5 pc32), `setup(view, name, config)`, `setup_button("scr_sort")`,
   and the `LayoutRootList.make_mii_hat_body` / `.com_sort_window` entries passed at
   actor main.p1 pc2-9. None of these names appears in any of the four chunks' other
   context.
10. **`state_function.setup(name, self, callback, const, extra)`** (5 args, four
    calls at p5 pc64/71/78/85) and `state.set` / `state.get` / `state.update`. Only
    `common/state_function`'s own chunk shows `name_`/`module_` keys; the argument
    order here is inferred from register layout, not documented.
11. **`ComFrameActor.press_cancel()` vs `is_cancelled()`.** Two different methods, one
    write-ish and one read-ish; the lifecycle between them is unknown.
12. **`play_animation_and_wait`** comes from `common/ui_common` (p8 pc23, p9 pc3 via
    up[0]) - behaviour native-side.
13. **`make_mii_utility` has no caller.** Zero hits across the 86 P5-UI-API UI chunks.
    It may be required by a non-UI script, by native code, or be dead in 13.0.4.
14. **The actor chunk choice.** Nothing in these four chunks says who loads
    `make_mii_hat_actor` vs `make_mii_body_actor`, or in what sequence.
15. **Runtime behaviour.** Nothing here was run. No emulator, no console, no video.
    All results are tier B (offline tool output) and tier C (pinned bytes).

---

## 11. Call-flow table

Columns: **chunk / proto / pc range** | **role** | **arguments and provenance** |
**return usage** | **unresolved native behaviour (D)**.

Argument counts are as they appear in the `CALL` operand `B`, where
`nargs = B - 1`. Every row below is re-derived from the chunk bytes by
`evidence/P6-HAT-UI/check_p6_hat_ui.py` (section 12).

### 11.1 `make_mii_hat_actor`

`make_mii_body_actor` is identical except where marked. (B)

| proto / pc | role | args and provenance | return usage | native behaviour (D) |
|---|---|---|---|---|
| main 0-3 | require `menu/chara_make/make_mii_hat_body_layout` | 1 arg: the module-path constant | 1 result -> module table | loads the shared layout module |
| main 4-15 | publish 6 functions plus `is_finish = false` into `_ENV` | - | - | - |
| p0 0 | `is_finish = false` | - | - | - |
| p0 1-4 | set the screen title | 1 arg: constant `"mnu_mmiif_setup_hat_title"` (body actor: `"mnu_mmiif_setup_outfit_title"`) | none | renders the header text from the message key |
| p0 6-7 | fade the view in | 1 arg: `self.update_in` | none | plays the open animation, then waits |
| p0 8-19 | **frame loop** `while is_finish == false do` | - | - | - |
| p0 12-13 | pump the layout | 1 arg: `self.update` | **1 result -> `is_finish`** | runs the state machine; returns "screen finished" |
| p0 14-18 | hand the frame back | 0 args: `coroutine.yield()` | none | resumes this coroutine on a later frame |
| p0 20-23 | clear the footer hint bar | 1 arg: global `COMFRAME_FOOTERMESSAGEAREA_NONE` | none | hides footer messages |
| p0 25-26 | fade out | 1 arg: `self.update_out` | none | plays the close animation |
| p1 2-9 | gather the 6 dependencies | - | - | - |
| p1 9 | **hand off to the layout** | **6 args**: `initialize_hat` (body actor: `initialize_body`), `LayoutRootList.make_mii_hat_body`, `LayoutRootList.com_sort_window`, global `scroller`, global `sub_list_window`, global `sub_list_window_facade` | none | the two `LayoutRootList` entries are view/parts descriptors; `scroller` is the pre-existing list object |
| p2 0-4 | forward a preset selection | 2 args: `set_select_id`, the caller's id `R[0]` | none | - |
| p3 0-4 | forward a preset sort mode | 2 args: `set_sort_id`, the caller's id `R[0]` | none | - |
| p4 0-4 | report the confirmed item | `TAILCALL` `get_decided_id` | **multret** - the value native code reads | - |

### 11.2 `make_mii_hat_body_layout` - module, accessors, gate

| proto / pc | role | args and provenance | return usage | native behaviour (D) |
|---|---|---|---|---|
| main 0-7 | load 6 numeric constants (`1 2 3 4 0 9`) and the `UiScriptPlayer` global | - | - | - |
| main 8-11 | `UiScriptPlayer.require("common/state_function")` | 1 arg: constant | 1 result -> an upvalue of the children | provides the 4-state machine helpers |
| main 12-15 | `UiScriptPlayer.require("common/ui_common")` | 1 arg: constant | 1 result -> an upvalue | provides `play_animation_and_wait` |
| main 16-45 | build the module table: 15 `CLOSURE` + `SETTABLE` pairs | - | - | - |
| main 46-52 | `setmetatable(tbl, {})`, `TAILCALL` | 2 args: the table, an empty metatable | multret -> the required module | - |
| p0 0-1 | `set_select_id(id)` | 2 args: the id | none | stores `self.select_id` |
| p1 0-2 | `get_decided_id()` | none | 1 result | returns `self.decided_id` |
| p2 0-22 | `set_enable_input(flag)` - the single input gate | 5 calls, 2 args each: `main_virtual_input.set_enable(flag)` pc3, `scroller.set_enable(flag)` pc7, `selector.set_enable(flag)` pc11, `scroller.set_focus(false)` pc17, `selector.set_focus(false)` pc21 | none | enables/disables the three input consumers |
| p3 0-11 | `set_sort_id(id)` | 2 args | none | - |
| p3 2 | relabel | 1 arg: `self.update_sort_text` | none | - |
| p3 7 | **BRIDGE `sort_id_list`** | **2 args**: state table `R[4]`, `self.sort_id` (the 2nd parameter) | **0 results** | re-sorts the native list by mode |
| p3 10 | redraw | 1 arg: `scroller.redraw_all_items` | none | re-renders every visible row |
| p4 0-4 | build the 3-entry sort-label table | constants `"mnu_mmiif_sort_1"`, `"mnu_mmiif_sort_3"`, `"mnu_mmiif_sort_4"` | - | - |
| p4 8-10 | label the sort button | 2 args: `sort_text_pane.set_text_message`, `tbl[sort_id + 1]` | none | renders the selected sort mode's name |

### 11.3 `make_mii_hat_body_layout` - `initialize` (p5, 113 instructions)

| pc | role | args and provenance | return usage | native behaviour (D) |
|---|---|---|---|---|
| 2 | main root view | 1 arg: 2nd parameter | 1 result -> `self.main_view` | view handle |
| 5 | main virtual input | 1 arg: 2nd parameter | 1 result -> `self.main_virtual_input` | input handle |
| 10 | stop-at-end animation | 2 args: `main_view.stop_animation_at_end`, 6th parameter | none | freezes animations at their last frame |
| 13 | sort-window root view | 1 arg: 3rd parameter (`LayoutRootList.com_sort_window`) | 1 result -> `self.sub_view` | view handle |
| 16 | sort-window input | 1 arg: 3rd parameter | 1 result -> `self.sub_virtual_input` | input handle |
| 18 | **store the scroller** | `self.scroller = <4th parameter>` | - | the list object is host-owned (section 2.1) |
| 21-28 | pane lookup: `main_view.get_parts("scr_sort")` then `.get_pane("set_txt_list")` | 2 args each | 1 result each -> `self.sort_text_pane` | resolves the view's parts/pane tree |
| 29-32 | `LayoutButtonSelectorConfig.new()`, then set field `is_unique_se = true` | 0 args | 1 result | config object |
| 33-35 | `LayoutButtonSelector.new()` | 0 args | 1 result -> `self.selector` | selector object |
| 38-42 | `selector.setup(main_view, "selector_sort", <config>)` | 4 args | none | binds the selector to a named view part |
| 44-47 | `selector.setup_button("scr_sort")` | 3 args | none | registers one button in the group |
| 49-53 | `selector.set_shortcut(INPUT_OPEN_SORT_WINDOW, false)` | 4 args | none | suppresses the shortcut input |
| 55-57 | `selector.select_button(<up[1]>)` | 2 args | none | pre-selects the sort button |
| 64 | register state 1 | 5 args: `setup`, name const `up[2]`, `self`, `self.update_idle`, `STATE_UPDATE_NONE` | none | defines the idle phase |
| 71 | register state 2 | 5 args: name `up[3]`, `self`, `self.update_main`, `STATE_UPDATE_MAIN` | none | defines the interactive phase |
| 78 | register state 3 | 5 args: name `up[4]`, `self`, `self.update_sub_list_window_in`, `STATE_UPDATE_SUB_LIST_WINDOW_IN` | none | defines the overlay-open phase |
| 85 | register state 4 | 5 args: name `up[5]`, `self`, `self.update_sub_list_window`, `STATE_UPDATE_SUB_LIST_WINDOW` | none | defines the overlay phase |
| 92-96 | `main_view.set_visible(false)`, `sub_view.set_visible(false)` | 2 args each | none | - |
| 100-103 | `sub_virtual_input.set_enable(false)`, `self.set_enable_input(false)` | 2 args each | none | - |
| 104 | `self.sort_id = 0` | - | - | - |
| 106 | `self.update_sort_text()` | 1 arg | none | - |
| 111 | **BRIDGE `sort_id_list`** | **2 args**: state table `R[51]`, `self.sort_id` (just set to 0) | **0 results** | initial native sort on screen entry |

### 11.4 `make_mii_hat_body_layout` - animation, transitions, `update_main`

| proto / pc | role | args and provenance | return usage | native behaviour (D) |
|---|---|---|---|---|
| p6 0-21 | `initialize_body(...)` = `initialize(...)` then the animation loop | 6 args at pc6 | none | - |
| p6 7-15 | loop `for i = 0, up[0], 1` | loop bound is an upvalue constant | - | - |
| p6 17 | `string.format("set_parts_scr_item_%02d", i)` | 2 args | 1 result | builds a per-part animation name |
| p6 19 | `main_view.play_animation_parts(<name>, "category_00")` | 3 args | none | plays the staggered open animation for that part |
| p7 0-21 | `initialize_hat(...)`, identical shape | 6 args at pc6 | 1 result from `format` | same, with `"category_01"` at pc18 |
| p8 5 | move the cursor to the incoming selection | 3 args: `scroller.select_item`, `self.select_id`, `false` | none | positions the cursor without scrolling |
| p8 8 / pc12 | `set_enable_input(true)`, `scroller.set_focus(true)` | 2 args each | none | - |
| p8 15 | `scroller.redraw_all_items()` | 1 arg | none | - |
| p8 19-23 | `main_view.set_visible(true)`, `play_animation_and_wait(main_view, <const>)` | 2 args each | none | plays the open animation to completion |
| p8 27 | `state.set(<const>)` -> `STATE_UPDATE_MAIN` | 2 args | none | switches to the interactive state |
| p9 3 | `play_animation_and_wait(main_view, <const>)` | 2 args | none | plays the close animation |
| p9 6 / pc10 | `set_enable_input(false)`, `main_view.set_visible(false)` | 2 args each | none | - |
| p10 0 | `update_idle()` - empty stub, 1 instruction | - | - | - |
| p11 2 | **cancel** detect | 1 arg: `main_virtual_input.is_cancel` | **1 result** -> branch | - |
| p11 7 | `ComFrameActor.press_cancel()` | 0 args | none | signals the frame actor that cancel was taken |
| p11 11 | sort-button detect | 1 arg: `selector.get_decided_button_id` | **1 result** -> branch | - |
| p11 18 | `state.set(<const>)` -> `STATE_UPDATE_SUB_LIST_WINDOW_IN`, then `RETURN` | 2 args | none | - |
| p11 23 / pc28 | focus arbitration | 1 arg each: `selector.has_focus`, `scroller.has_focus` | 1 result each | which consumer currently owns the input |
| p11 34 | `scroller.set_focus(false)` | 2 args | none | - |
| p11 39 | **UP** detect | 2 args: `main_virtual_input.is_pressed`, `INPUT_BUTTON_UP` | 1 result | - |
| p11 43-47 | **page-jump up** | 3 args: `scroller.select_item`, `SCROLLER_ITEM_NUM - 1`, `true` | none | scrolls the native list up one page |
| p11 53 | **DOWN** detect | 2 args: `main_virtual_input.is_pressed`, `INPUT_BUTTON_DOWN` | 1 result | - |
| p11 59 | **BRIDGE `get_top_index`** | **1 arg**: state table `R[19]` | **1 result**, passed to pc64 | reads the native list's current top row |
| p11 64 | **page-jump down** | 3 args: `scroller.select_item`, `<get_top_index result>`, `true` | none | normalises the page jump against the real top |
| p11 71 / pc75 | move focus to the scroller | 2 args each | none | - |
| p11 76-79 | `UiSoundManager.play_se(UI_SE_ID_CURSOR)` | 1 arg: the constant | none | cursor SFX |
| p11 83 | **CONFIRM read** | 1 arg: `scroller.get_decided_item` | **1 result** | returns the item the user committed to |
| p11 84 | store `self.decided_id` | - | - | - |
| p11 88-91 | leave the main state | 2 args: `state.set`, `<const>` | none | ends the screen |
| p11 95 | `main_virtual_input.set_enable(false)` | 2 args | none | - |
| p11 100 | `scroller.get_selected_item()` | 1 arg | 1 result -> compared with `BUTTON_ID_NONE` at pc101 | the cursor's current index; `BUTTON_ID_NONE` means "no row" |
| p11 107 / pc113 | page scroll | 2 args: `scroller.special_input_is_upward(true)` / `..._downward(true)` | 1 result each | shoulder-button page turn, native |
| p11 119 / pc123 | swap focus between selector and scroller | 2 args each | none | - |
| p11 124-127 | cursor SFX again | 1 arg | none | - |
| p11 130 | `ComFrameActor.is_cancelled()` | 0 args | 1 result -> branch | - |
| p11 136-140 | `state.set(<const>)`, `main_virtual_input.set_enable(false)` | 2 args each | none | - |

### 11.5 `make_mii_hat_body_layout` - sort overlay and pump

| proto / pc | role | args and provenance | return usage | native behaviour (D) |
|---|---|---|---|---|
| p12 2 | `scroller.has_focus()` | 1 arg | 1 result -> gate | - |
| p12 10 | **BRIDGE `backup_list_selected_id`** | **1 arg**: state table `R[6]` | **0 results** | saves the current selection natively |
| p12 13 / pc17 / pc21 | `self.set_enable_input(false)`, `sub_view.set_visible(true)`, `sub_virtual_input.set_enable(true)` | 2 args each | none | - |
| p12 25 | `sub_list_window.activate(self.sub_list_window_facade)` | 2 args | none | brings the overlay up |
| p12 29 | `sub_list_window.open(self.sort_id)` | 2 args | none | opens it at the current sort mode |
| p12 33 | `state.set(<const>)` -> `STATE_UPDATE_SUB_LIST_WINDOW` | 2 args | none | - |
| p13 3 | tick the overlay | 2 args: `sub_list_window.update`, `self.sub_virtual_input` | none | drives the overlay's own frame |
| p13 7 | read the overlay result | 1 arg: `sub_list_window.get_result` | **2 results** -> used at pc58 and to choose the branch | returns the sort mode plus a second, unnamed value |
| p13 12 | `sub_list_window.is_busy()` | 1 arg | 1 result -> gate | whether the overlay is still animating |
| p13 18 / pc22 / pc26 | `sub_view.set_visible(false)`, `sub_virtual_input.set_enable(false)`, `sub_list_window.deactivate(self.sub_list_window_facade)` | 2 args each | none | tears the overlay down |
| p13 29 | `self.set_enable_input(true)` | 2 args | none | - |
| p13 34-36 | `scroller.set_focus(true)` on the way back to the list | 2 args | none | hands the input focus back to the scroller |
| p13 40 | **BRIDGE `select_list_from_backup_id`** - cancel branch only | **1 arg**: state table `R[18]` | **0 results** | restores the selection saved at p12 pc10 |
| p13 45 / pc49 | `selector.set_focus(true)`, `state.set(<const>)` -> back to `STATE_UPDATE_MAIN` | 2 args each | none | - |
| p13 58 | **accept branch**: `self.sort_id = <result 1>` | - | - | - |
| p13 60 | `self.update_sort_text()` | 1 arg | none | - |
| p13 65 | **BRIDGE `sort_id_list`** | **2 args**: state table `R[24]`, `self.sort_id` (just set) | **0 results** | applies the new sort natively |
| p13 68 | `scroller.redraw_all_items()` | 1 arg | none | - |
| p13 71 | `sub_list_window.close()` | 1 arg | none | - |
| p14 2 / pc5 / pc6-10 | `update()`: `state.update()`, then `state.get()` compared with `up[1]` | 1 arg each | 1 result from `state.get()` | returns "screen finished" to the actor's frame loop |

### 11.6 `make_mii_utility`

| proto / pc | role | args and provenance | return usage | native behaviour (D) |
|---|---|---|---|---|
| main 0-54 | write 32 numeric camera constants into `_ENV`; build the 4-function table; `setmetatable` `TAILCALL` at pc52 | - | multret | - |
| p0 1-2 / pc8-9 | branch on the Mii type: `MII_TYPE_SWORDSMAN`, then `MII_TYPE_GUNNER` | - | - | - |
| p0 22 | push the default camera triple | **4 args**: camera, `F_CAMERA_DEFAULT_POSITION_X`, `..._Y`, `..._Z` | none | sets the camera's default position |
| p1 1-9, pc22 | right-side-0 fighter camera | **4 args**: camera, `F_RIGHT_SIDE_0_CAMERA_TRANSLATE_X`, `..._Y`, `F_RIGHT_SIDE_0_CAMERA_POSITION_Z` | none | moves the camera for fighter slot 0 |
| p2 1-9, pc22 | right-side-1 fighter camera | **4 args**: same shape with `F_RIGHT_SIDE_1_*` | none | fighter slot 1 |
| p3 0-5 | head-position camera, **no** type branch | **5 args**: camera, `HAT_SELECT_CAMERA_TRANSLATE_X`, `..._Y`, `HAT_SELECT_CAMERA_TRANSLATE_LOOK_AT_Y`, `HAT_SELECT_CAMERA_POSITION_Z` | none | frames the Mii head for the headgear preview |

---

## 12. Bridge-name list with argument counts

The complete set of native bridges used by this screen. `nargs` is `B - 1` on the
`CALL`; `nres` is `C - 1`.

| bridge name | nargs | nres | sites (proto/pc) | what Lua asks for (D) |
|---|---|---|---|---|
| `sort_id_list` | 2 | 0 | p3/7, p5/111, p13/65 | re-sort the native list by a sort-mode id |
| `get_top_index` | 1 | 1 | p11/59 | the native list's current top row index |
| `backup_list_selected_id` | 1 | 0 | p12/10 | save the current selection before opening the sort overlay |
| `select_list_from_backup_id` | 1 | 0 | p13/40 | restore that selection when the overlay is cancelled |

Four names, six sites, one used return value. No other `invoke` exists in any of
the four chunks, and `make_mii_hat_actor` / `make_mii_body_actor` /
`make_mii_utility` contain **zero** invoke calls. (B)

For contrast, the same four names across all 86 UI chunks, per
`evidence/P5-UI-API/ui_api.json`: `sort_id_list` 3 sites, `get_top_index` 1,
`backup_list_selected_id` 3, `select_list_from_backup_id` 3. So
`get_top_index` and `sort_id_list` are used *only* by the headgear/outfit screen,
while the backup pair is shared with two chunks outside this task. (B)

### 12.1 The check script

`evidence/P6-HAT-UI/check_p6_hat_ui.py` re-derives every pc, opcode, operand and
constant cited in this report straight from the four chunk files and **exits
nonzero on any mismatch**. It asserts:

- the four sha256 hashes and sizes in section 0.1;
- `verify` passes structurally for each chunk (version, sizes, full consumption);
- proto counts, per-proto instruction counts and constant counts (section 1.1);
- every `CLAIMS` entry - `(chunk, proto, pc, opcode, operand A/B/C/Bx, expected
  constant value)` for every instruction this report cites;
- every scroller / selector / sub_list_window call site with its argument count;
- every global read and written name, per chunk;
- that no row-fill / item-info / preview / commit API name appears in any constant
  of any of the four chunks (the section 8 claims);
- **report coverage**: it re-parses section 11 of this report and checks that every
  `(chunk, prototype, pc)` the tables cite really exists in that chunk, and that
  each of the 18 scroller call sites and all 6 bridge invocations is named by the
  report. This is what stops the report from drifting away from the bytes.

Observed run (from the workspace root, after this report was finished):

```
$ python mods/mii_customizer/evidence/P6-HAT-UI/check_p6_hat_ui.py
722 checks, 0 failures
exit 0
```

**Negative controls** (three, all correctly rejected the corrupted input):

1. flipped one byte of the instruction word at `hat_body_layout` main.p11 pc59 ->
   reported `opcode LT != CALL` **and** the file hash mismatch;
2. `setconst`-rewrote the `get_top_index` string constant to `get_sop_index` ->
   `setconst` itself refused without `--allow-used` (exit 1), and with it the script
   reported `Bx constant 'get_sop_index' != 'get_top_index'` plus the hash mismatch;
3. the report-coverage pass, via
   `scratch/2026-10-05_P6-HAT-UI/negative_control_coverage.py`: it fed the check
   script a copy of this report with the row `| p11 43-47 |` widened to
   `| p11 43-9999 |` and confirmed a nonzero exit with
   `cite/.../main.p11/pc142: report cites pc outside 142 instructions` (p11 really
   has 142 instructions, pc 0-141). Observed: doctored-report exit status **1**,
   control script exit **0** (meaning "the control succeeded").

So the checks are genuinely load-bearing, not vacuously true.

---

## 13. Summary for the mod (what this means for a ~90-entry setting list)

Stated as findings, not as a design - designing the mod screen is a later task.

1. **A long list needs no new Lua.** The screen's list is a native scroller that
   already scrolls itself; Lua only calls `select_item` and
   `special_input_is_upward/downward`. Whether 90 entries work is a question about
   the native list's item model, which these chunks never touch. **B/D.**
2. **The rows are native.** No row label, icon or mark is ever set from Lua, so a
   mod that wants "use the stats of character X" as row text has to get its text
   into whatever the native item model uses - not into a Lua callback. **D.**
3. **The one bridge that returns data is `get_top_index`**, and it returns a scroll
   position, not content. Knowing what it returns is the cheapest next fact to get.
4. **Confirmation is `scroller.get_decided_item()` -> `self.decided_id`** and leaves
   the main state; there is no commit bridge to intercept. **C.**
5. **The headgear/outfit split is two actor chunks sharing one layout module**, so
   the cheapest way to reuse this screen's choreography is to reuse
   `make_mii_hat_body_layout` from a new actor chunk rather than to add a tab inside
   it. **C** for the structure, **D** for the "cheapest way" judgement.

---

## 14. Persisted task summary

**Task ID:** P6-HAT-UI
**Status:** **DONE** - the tracing deliverable is complete. Every question 1-8 is
answered with chunk, prototype and pc ranges; all eight questions are covered in
sections 1-9. The only qualifier is evidence tier: this is **tier B (offline
observation) and C (pinned bytes) only** - no runtime behaviour is claimed anywhere,
and all native semantics are marked D.

### Changed / created files (this task's exclusive paths only)

| path | what |
|---|---|
| `research/P6-HAT-UI.md` | this report (the deliverable) |
| `evidence/P6-HAT-UI/check_p6_hat_ui.py` | re-derivation check, 722 assertions, exits nonzero on mismatch |
| `evidence/P6-HAT-UI/{header,summary,protos,constants,dis}_make_mii_{hat_actor,hat_body_layout,utility,body_actor}.txt` | raw tool output backing every cited pc |
| `scratch/2026-10-05_P6-HAT-UI/derive.py` + `derived.json` | global read/write and invoke-site derivation |
| `scratch/2026-10-05_P6-HAT-UI/callflow.py` + `callflow.txt` | per-`CALL` argument-provenance listing |
| `scratch/2026-10-05_P6-HAT-UI/negative_control_coverage.py` | proves the report-coverage check rejects a report that cites a pc the chunk does not have |
| workspace-relative `gamedata/mii_customizer/P6-HAT-UI/ui/script/menu/chara_make/make_mii_{hat_actor,hat_body_layout,utility,body_actor}.lc` | the four extracted chunks (unmodified) |

**No chunk was edited. No other worker's file was touched. No agent, commit,
branch, emulator run or SD access happened.** `STATUS.md`, `CURRENT_INSTALL.md`,
`CHANGELOG.md` and the contracts were not modified - they are the coordinator's.

### Commands that were actually run, with results

| command | result |
|---|---|
| `tools/arc-extract` on the four paths | 4 files written, sizes/hashes in section 0.1 |
| `cmp` each P6 copy against the P5-UI-API copy | identical, exit 0 (x4) |
| `lua53_inspect.py verify <chunk>` | exit 0 (x4) |
| `luac-game.exe -l -l <chunk>` | exit 0 (x4) |
| `lua53_inspect.py {header,summary,protos,constants,dis}` | 20 files written |
| `derive.py`, `callflow.py` | exit 0; outputs in `scratch/2026-10-05_P6-HAT-UI/` |
| `check_p6_hat_ui.py` | **722 checks, 0 failures, exit 0** |
| negative control 1 (flip a byte at p11 pc59) | exit 1, reported `opcode LT != CALL` + hash mismatch |
| negative control 2 (`setconst` `get_top_index` -> `get_sop_index`) | exit 1, `setconst` refused without `--allow-used`, then reported the constant mismatch + hash mismatch |
| negative control 3 (`negative_control_coverage.py`: a report citing pc 142 of a 142-instruction proto) | doctored-report exit 1 with `report cites pc outside 142 instructions`; control script exit 0 |

### Failures and limits, stated plainly

- Three earlier attempts to write this report died mid-stream on upstream timeouts
  and left no file; it was completed by appending in smaller pieces. No content
  from those attempts is missing here.
- **No runtime verification of any kind.** No emulator, no console, no video, no
  screenshots. Every statement about what native code *does* is D.
- The other two `backup_list_selected_id` / `select_list_from_backup_id` call sites
  found in the P5 survey are in chunks outside this task's scope and were not
  analysed.
- The archive index (`arc_files.tsv`) was used to answer the patch-version
  question. That index is itself a decoded listing, not the archive itself; the
  answer "no `ui/script_patch/` version exists" is tier B on that index.
- While adding the report-coverage check, the tool caught two real defects in this
  report that are now fixed: two pc ranges were one too long (`main.p0 0-2` for a
  2-instruction prototype, `main.p1 0-3` for a 3-instruction one), and the
  accept-path `scroller.set_focus(true)` at p13 pc34-36 was missing from the
  call-flow table. Both are corrected above.

### Next experiment

**Trace the native side of the list, in this order:**

1. Find where `scroller` is **assigned**. Search all `ui/script/` chunks (not just
   the 86 already extracted) for a `SETTABUP` to the name `scroller`; P5 already
   found only `collection_tips_list.lc` and `option_button_top.lc`. If neither
   constructs it, `scroller` is created natively, and the next step is a symbol or
   string sweep of the binary for `scroller`, `sort_id_list`, `get_top_index`,
   `backup_list_selected_id`, `select_list_from_backup_id` to find the registration
   table for the `UiScriptPlayer.invoke` bridge.
2. Once that table is found, the decisive question is whether the native list
   accepts an **externally supplied item list** (which would let a mod feed 90
   custom rows) or is hard-wired to the Mii headgear table. That single fact decides
   whether the mod can reuse this screen at all.
3. Cheap parallel step: dump the Mii maker's layout/parts data for
   `make_mii_hat_body` and `com_sort_window` to recover the row pane names, which
   would corroborate or refute that rows are filled natively.
