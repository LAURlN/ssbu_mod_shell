# P8-LUA-LIST - can a UI script build and fill a scrolling list itself?

**Task ID:** P8-LUA-LIST
**Date:** 2026-10-05 - Space Bunny Alpha
**Scope:** bytecode tracing only. No chunk was edited, no layout archive was
opened, no design is proposed, no emulator or console was used.

Evidence tiers used throughout:

| tier | meaning |
|---|---|
| **B** | offline observation - I ran a tool and read its output |
| **C** | pinned bytes - the chunk, quoted exactly |
| **D** | hypothesis - inference, explicitly marked |

**Every statement about what a native (host) call *does* is marked D.** Nothing
here was observed running.

## Headline

**No.** In the whole 86-chunk UI script set there is **no constructor for a
scroller, anywhere**, and no per-row text fill for any scroller. The two chunks
P6-HAT-UI 2.1 called "the only two that WRITE the global `scroller`" do not
build one - both write `_ENV.scroller = nil` while clearing their module state,
and only ever read it afterwards. That correction to P6-HAT-UI is section 1.

But the question behind the task has a different and better answer, found by
the 86-chunk sweep (question 7): **Lua *does* own a list of text rows in the
game, just not through the scroller.** `make_mii_special_actor.lc` builds four
rows with a numeric `for` loop over a global count constant, fetches each row's
layout *part* by an index-formatted name, caches the row's panes in Lua tables
and sets their text with `set_text_message` - once from a Lua table lookup and
once from a bridge return value. That is the simplest such screen in the game
and it is section 8.

---

## 0. Inputs, hashes, commands

### 0.1 Files analysed

Extracted with the workspace tool `tools/arc-extract` from workspace-relative
`gamedata/ssbu-13.0.4/data.arc` into workspace-relative
`gamedata/mii_customizer/P8-LUA-LIST/`:

| file | ARC path | size (B) | sha256 |
|---|---|---|---|
| `collection_tips_list.lc` | `ui/script/menu/collection/collection_tips_list.lc` | 2647 | `89f077ccb5b92e532bbccf0ac1b171735908b8a04abb1075b8449251bba391ad` |
| `option_button_top.lc` | `ui/script/menu/option/option_button_top.lc` | 4994 | `bcfac5e252dc8cf9f6bc600f1120f959de469ee2fe89861e937b4c6aed9e8572` |
| `ui_common.lc` | `ui/script/common/ui_common.lc` | 3874 | `349448a926c74fd0cba3ea5ccdd1d9ea7ee650ed45fca8d23f29ca313cefd76f` |

All three are byte-identical (`cmp`, exit 0) to the copies already present in
`gamedata/mii_customizer/P5-UI-API/`. The two targets were extracted into this
task's folder anyway so the hashes below are this task's own. (B)

Read (not re-extracted) from the P5-UI-API extraction, because the 86-chunk
sweep needs them:

| file | ARC path | size (B) | sha256 |
|---|---|---|---|
| `make_mii_special_actor.lc` | `ui/script/menu/chara_make/make_mii_special_actor.lc` | 7799 | `ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d` |
| `make_mii_edit_actor.lc` | `ui/script/menu/chara_make/make_mii_edit_actor.lc` | 10321 | `1f73dff133961b68dbe24641298229b9f3905a44703164563911b105eaa16908` |

The `make_mii_special_actor` hash matches the coordinator-verified value in
P5-UI-API section 1, so the extraction path is independently confirmed. (B)

### 0.2 The require closure is exactly three chunks (B, C)

`collection_tips_list.lc` main pc0-3 and `option_button_top.lc` main pc0-3 both
have the identical three-instruction shape

```
GETTABUP  R[0]  up[0]  "UiScriptPlayer"     ; receiver
GETTABLE  R[0]  R[0]   "require"             ; method
LOADK     R[1]  K[2]="common/ui_common"
CALL      A=0 B=2 C=2                       ; 1 arg, 1 result
```

so both `require` exactly one module, `common/ui_common`. That module was
among the 86, so it was already available; it was extracted into this task's
folder anyway and hashed (above). `ui_common.lc` requires nothing itself -
its `main` is a 53-instruction chunk that only builds a 22-entry table of
closures and returns it under a metatable whose `__index` is that table
(main pc46-51). **The closure is therefore complete at three files.** (C)

### 0.3 Structural facts (B)

```
lua53_inspect.py verify  -> exit 0 for collection_tips_list, option_button_top, ui_common
                            (all: version 0x53, 4-byte float32, Instruction=4,
                             size_t=8, int=4, stripped, full byte consumption)
lua53_inspect.py verify  -> exit 0 for make_mii_special_actor, make_mii_edit_actor
```

| chunk | size | protos | instrs | consts | per-proto instruction counts |
|---|---|---|---|---|---|
| `collection_tips_list` | 2647 | 4 | 265 | 98 | main 16, p0 7, p1 79, p2 163 |
| `option_button_top` | 4994 | 8 | 565 | 168 | main 20, p0 92, p1 21, p2 57, p3 91, p4 66, p5 29, p6 189 |
| `ui_common` | 3874 | 23 | 345 | 117 | main 53 (+ 22 children) |

### 0.4 Reading conventions

- `chunk` / `proto` / `pc` are as produced by `tools/lua53-inspect`; `pc` is the
  0-based instruction index inside a prototype.
- `up[n]` is upvalue `n`. In **all three** analysed chunks `up[0]` is `_ENV` in
  every prototype (main's upvalue 0 is `instack=1, idx=0`, i.e. the register the
  loader installs as the environment; children chain to it through descriptors).
  For `collection_tips_list` and `option_button_top` the module table returned by
  `require` occupies main's register 0 and is what `up[0]` points at, so
  `up[0]` is a table whose `__index` chain reaches the real globals. (C)
- `nargs = CALL.B - 1`; for a `SELF`-mediated method call the receiver is one of
  them, so **real arguments = `B - 2`**. A `CALL` with `B = 0` means "up to
  `L->top`" (`lopcodes.h:250-253`) and is reported as `0*`, never guessed. (C)
- `SETTABUP` and `GETTABUP` have **different operand order**: `GETTABUP` is
  `R[A] := up[B][K[C]]` while `SETTABUP` is `up[A][K[B]] := RK[C]`
  (`lopcodes.h`). Getting this backwards silently reports every `SETTABUP` as a
  read; my first derivation pass did exactly that and had to be fixed. Recorded
  because a reader re-deriving the global tables will hit it too. (B)

### 0.5 Commands run

```
tools/arc-extract --arc gamedata/ssbu-13.0.4/data.arc \
    --out gamedata/mii_customizer/P8-LUA-LIST \
    ui/script/menu/collection/collection_tips_list.lc \
    ui/script/menu/option/option_button_top.lc \
    ui/script/common/ui_common.lc                       # exit 0, "3 extracted, 0 failed"

python mods/mii_customizer/tools/lua53-inspect/lua53_inspect.py \
    {header,summary,protos,constants,dis,verify} <chunk>
    -> evidence/P8-LUA-LIST/{header,summary,protos,constants,dis}_*.txt, verify_all.txt

python mods/mii_customizer/scratch/2026-10-05_P8-LUA-LIST/derive.py
    -> derived.json, callflow.txt        (the two targets + ui_common)
python .../sweep86.py  -> sweep.json, sweep.txt     (all 86 chunks)
python .../rowfill.py  -> rowfill.json, rowfill.txt (all 86 chunks)

python mods/mii_customizer/evidence/P8-LUA-LIST/check_p8_lua_list.py
    -> 1667 checks, 0 failures, exit 0
python .../negative_controls.py  -> exit 0, see section 9
```

---

## 1. Question 1 - where the scroller object comes from

**Answer: neither chunk constructs it. Both write `_ENV.scroller = nil` while
resetting their module state, and every later use is a plain `_ENV` read.**

This is the exact instruction in `collection_tips_list.lc` main pc6:

```
[  6] 0x83410008 @0x46  SETTABUP  A=0 B=262 C=260
      up[0] (instack=1 idx=0)[K[6]=scroller] := K[4]=None
```

`option_button_top.lc` main pc5 is the same instruction:

```
[  5] 0x82c10008 @0x42  SETTABUP  A=0 B=261 C=260
      up[0] (instack=1 idx=0)[K[5]=scroller] := K[4]=None
```

In both chunks the value assigned is the constant `None` (`K[4]`, tag `0x00`).
The value is **nil, not an object.** (C)

These instructions sit in a run of sibling `SETTABUP`s that clear the chunk's
own module-state fields, so what is happening is module-state reset, not
object creation:

| chunk | main pc | `_ENV` name | value assigned |
|---|---|---|---|
| `collection_tips_list` | 4 | `layout_view` | `None` |
| | 5 | `virtual_input` | `None` |
| | **6** | **`scroller`** | **`None`** |
| | 7 | `exit_code` | `None` |
| | 8 | `BUTTON_ID_LEFT` | `K[9]=0` |
| | 9 | `BUTTON_ID_RIGHT` | `K[11]=1` |
| | 14 | `main` | `R[4]` (the `main.p2` closure, `CLOSURE` pc13) |
| `option_button_top` | 4 | `layout_view` | `None` |
| | **5** | **`scroller`** | **`None`** |
| | 6 | `exit_code` | `None` |
| | 7 | `decided_button_id` | `None` |
| | 8 | `current_focus` | `None` |
| | 9 | `edited_menu_vibration` | `None` |
| | 18 | `main` | `R[9]` (the `main.p6` closure, `CLOSURE` pc17) |

(C, all rows asserted by the check script.)

So the three candidate answers in the question separate cleanly:

| candidate | verdict | evidence |
|---|---|---|
| a constructor call (which global, which args) | **no** - there is no `.new` / `.create` / constructor call on the scroller in either chunk. The only `.new` calls are `LayoutButtonSelector.new` (ct main.p1 pc23, ob main.p0 pc11/48) and `LayoutButtonSelectorConfig.new` (ct main.p1 pc27, ob main.p0 pc15/52) | (C) |
| a host global under another name | **no** - `scroller` is used under that exact name, everywhere | (C) |
| a call result | **no** - no `GETTABUP`/`GETTABLE`/`SELF` produces the object; it is `GETTABUP up[0]["scroller"]` read straight out of `_ENV` | (C) |

**It is a host-provided global named `scroller`, read from `_ENV`, exactly as
P6-HAT-UI 2.1 concluded for the headgear screen - and P6-HAT-UI's cross-check
note needs one correction.** P6-HAT-UI 2.1 said the two chunks "WRITE the global
`scroller`". They do, but only to `nil`. The distinction matters: a
`nil`-assignment is evidence that the *script* never creates one, and it also
means the global the script reads must be **re-bound by the host between the
chunk's load and its `main` run** - otherwise the script would be reading back
its own `nil`. **D:** that rebinding happens natively, and nothing in these three
chunks shows how.

Every read of the object has the same two-instruction prefix
(`GETTABUP _ENV["scroller"]` then `SELF <method>`), for example
`collection_tips_list` main.p1 pc10-11:

```
[ 10] 0x00420046 @0x1ab  GETTABUP  A=1 B=0 C=264   R[1] := up[0][K[8]=scroller]
[ 11] 0x00c2404c @0x1af  SELF     A=1 B=1 C=265   R[1] := R[1][K[9]=select_item]
```

---

## 2. Question 2 - every method called on that object, compared with P6 2.2

### 2.1 `collection_tips_list.lc` - four call sites on the scroller

| method | proto / SELF pc → CALL pc | nargs | argument provenance | return used |
|---|---|---|---|---|
| `select_item` | main.p1 pc11 → pc14 | 2 | `ITEM_INDEX_INIT` (GETTABUP pc12), `false` (LOADBOOL pc13, `B=0 C=0`) | no (`C=1`) |
| `set_focus` | main.p1 pc16 → pc18 | 1 | `true` (LOADBOOL pc17, `B=1 C=0`) | no |
| `set_enable` | main.p2 pc31 → pc33 | 1 | `true` (LOADBOOL pc32) | no |
| `is_cancelled` | main.p2 pc50 → pc51 | 0 | - | **yes**, `C=2`; the result is compared with `True` at pc52 (`EQ ... K[21]=True`) |

Two more `CALL`s reach a *different* object and must not be counted as scroller
calls: main.p2 pc21-24 and pc26-29 are `CALL A=0 B=0 C=1` on `up[2]` - an
upvalue object reached through a `SELF` at pc21/pc26, whose method names are the
same (`set_focus`, `set_enable`) but whose receiver register is `R[0]`, a
different value from the `GETTABUP _ENV["scroller"]` pattern. **B=0** there means
the call is variadic through `L->top`; **this tool does not resolve those and no
argument count is claimed for them.** (C)

### 2.2 `option_button_top.lc` - thirteen call sites on the scroller

| method | proto / SELF pc → CALL pc | nargs | argument provenance | return used |
|---|---|---|---|---|
| `get_selected_item` | main.p2 pc25 → pc26 | 0 | - | **yes**, `C=2`; compared with `True` at pc32 |
| `set_focus` | main.p3 pc4 → pc6 | 1 | `false` (LOADBOOL pc5) | no |
| `select_button` | main.p3 pc8 → pc10 | 1 | `MOVE R[2] R[0]` pc9 - the focus argument | no |
| `set_focus` | main.p3 pc12 → pc14 | 1 | `true` (LOADBOOL pc13) | no |
| `has_focus` | main.p3 pc23 → pc24 | 0 | - | **yes**, `C=2`; branch at pc25 |
| `select_item` | main.p3 pc38 → pc40 | 1 | `ITEM_INDEX_LAST` (GETTABUP pc39) | no |
| `select_item` | main.p3 pc48 → pc50 | 1 | `ITEM_INDEX_FIRST` (GETTABUP pc49) | no |
| `set_focus` | main.p3 pc52 → pc54 | 1 | `true` (LOADBOOL pc53) | no |
| `set_focus` | main.p3 pc56 → pc58 | 1 | `false` (LOADBOOL pc57) | no |
| `get_selected_item` | main.p3 pc60 → pc61 | 0 | - | **yes**, `C=2` |
| `set_focus` | main.p3 pc80 → pc82 | 1 | `false` (LOADBOOL pc81) | no |
| `set_focus` | main.p3 pc84 → pc86 | 1 | `false` (LOADBOOL pc85) | no |
| `special_input_is_leftward` | main.p4 pc25 → pc27 | 1 | `false` (LOADBOOL pc26) | **yes**, `C=2` |
| `special_input_is_rightward` | main.p4 pc33 → pc35 | 1 | `true` (LOADBOOL pc34) | **yes**, `C=2` |
| `select_item` | main.p6 pc12 → pc15 | 2 | `ITEM_INDEX_INIT` (pc13), `false` (LOADBOOL pc14) | no |
| `get_selected_item` | main.p6 pc89 → pc90 | 0 | - | **yes**, `C=2` |
| `get_decided_item` | main.p6 pc158 → pc159 | 0 | - | **yes**, `C=2`; compared with `ITEM_INDEX_NONE` at pc161 |

`main.p4` also calls `has_focus` (pc14 → pc15) and `get_selected_button_id`
(pc6 → pc7, pc46 → pc47) on the *selector*, and `UiSoundManager.play_se_label`
(pc62 → pc64) - those receivers are not the `GETTABUP _ENV["scroller"]`
register, so they are not scroller methods. (C)

Note the receiver identity was not inferred from the method name: the rule
applied throughout is "`GETTABUP up[0] K=scroller` immediately followed by
`SELF` at register `A`, and the consumed `CALL` also at register `A`". That is
the same rule P5-UI-API 3.1 established, and it is why `set_focus` / `set_enable`
appear on non-scroller receivers without being counted here. (C)

### 2.3 Comparison with the nine methods in P6-HAT-UI 2.2

| | method | in P6 2.2 (headgear) | in P8 (these two chunks) |
|---|---|---|---|
| 1 | `set_enable` | yes | yes (ct ×2, ob ×1) |
| 2 | `set_focus` | yes | yes (ct ×1, ob ×7) |
| 3 | `select_item` | yes | yes (ct ×1, ob ×3) |
| 4 | `get_selected_item` | yes | yes (ob ×3) |
| 5 | `get_decided_item` | yes | yes (ob ×1) |
| 6 | `has_focus` | yes | yes (ob ×3) |
| 7 | `redraw_all_items` | yes | **no** - the string never appears in either chunk |
| 8 | `special_input_is_upward` | yes | **no** |
| 9 | `special_input_is_downward` | yes | **no** |
| 10 | `is_cancelled` | no | **yes** (ct ×1, ob ×1) |
| 11 | `special_input_is_leftward` | no | **yes** (ob ×1) |
| 12 | `special_input_is_rightward` | no | **yes** (ob ×1) |
| 13 | `select_button` | no | **yes** (ob ×1) |

**Same class, six of nine shared, six names differ.** The six shared names
(`set_enable`, `set_focus`, `select_item`, `get_selected_item`, `get_decided_item`,
`has_focus`) on one and the same `_ENV` global is strong evidence of one class
with a larger surface than either screen uses. **D:** that they are literally
the same C++ type is not established by bytecode; it rests on the shared global
name plus the six shared method names.

The three names unique to P8 and the three unique to P6 are the interesting
part. `special_input_is_leftward` / `_rightward` here versus
`special_input_is_upward` / `_downward` on the headgear screen are four names for
what is visibly the same job - reacting to the shoulder buttons. **D:** either
one class exposes all four and each screen uses the pair its layout needs, or
these are two classes sharing a name. `is_cancelled` and `select_button` are
absent from P6's list, and P6 lists them on the selector and `ComFrameActor`
instead - so `is_cancelled` in particular is ambiguous by name alone and was
resolved here only by the receiver rule in 2.2. (D)

Also note `select_item`'s argument count varies by call site even within one
chunk: **2 args** at ct main.p1 pc14 and ob main.p6 pc15, **1 arg** at ob main.p3
pc40 and pc50. **D:** the extra argument is a scroll/page flag; nothing in the
bytes says so. P6-HAT-UI 4.4/4.5 recorded the same two-argument form on the
headgear screen with the same `true` flag, so the shape is at least consistent
across screens.
---

## 3. Question 3 - row content: is a row ever filled from Lua?

**Answer: no, in either chunk, by any of the four mechanisms the question names.**

The check script asserts the absence of the following **as string constants of
every prototype** of both chunks (an absence assertion over the whole constant
stream, not a text search): `set_text_message`, `set_text_message_args`,
`set_text_string`, `set_item`, `get_item_num`, `set_item_num`, `item_num`,
`get_count`, `set_count`, `redraw_all_items`, `special_input_is_upward`,
`special_input_is_downward`, `new_scroller`, `Scroller`, `create_scroller`
(fifteen names, checked in both chunks).
It additionally asserts, structurally, that **no `string.format` call exists**:
it looks for `GETTABUP _ENV["string"]` feeding a `GETTABLE "format"` in any
prototype. All of these pass. (B)

Mechanism by mechanism, for `collection_tips_list` and `option_button_top`:

| mechanism asked about | present? | where it would have been | what is there instead |
|---|---|---|---|
| a callback function passed to the scroller | **no** | - | the only function-ish objects passed to the scroller are the two booleans at ct p1 pc13/pc17 and ob p6 pc14, and the index constants |
| a per-row loop | **no** | - | the only loops are `ipairs(LayoutRootList)` at ct main.p2 pc34-42 and pc142-150 (walking every layout root, calling `set_enable_input`), and no numeric `for` at all in either chunk |
| a pane lookup built from a row index | **no** | - | `option_button_top` main.p1 pc5-12 does build a *pane* name, but **not** from a row index: `get_parts(selector.get_button(0).get_name())` (section 5) |
| `set_text_message` / `_args` / `_string` on a row pane | **no** | - | neither method name appears |

What *is* set on panes in these two chunks, for completeness: **nothing.** No
`set_text_*` call at all. `option_button_top` sets a footer message through
`ComFrameActor.set_footer_message(HELP_MSG_*)` at main.p2 pc11-14, pc16-19,
pc34-37, pc46-49 and main.p6 pc130-132 (`press_cancel`) - those are frame-level
help strings, not rows. (C)

The only text-shaped names in either chunk are key-help pane names passed to
`setup_button`, which name panes rather than fill them: `set_txt_keyhelp_l`
(ct main.p1 pc42) and `set_txt_keyhelp_r` (pc47), `sel_btn_wave` and `scr_ctrl`
(ob main.p0 pc27, pc32), `btn_keyhelp_delete` (pc64). (C)

**This is the same conclusion P6-HAT-UI 2.3 reached for the headgear screen,
now established for the two chunks P6 flagged as writers as well.**

---

## 4. Question 4 - where the total item count comes from

**Answer: it does not, in either chunk. The scroller's item count is never in
Lua.**

No `get_item_num`, `set_item_num`, `item_num`, `get_count` or `set_count` name
appears in either chunk (asserted, section 3). There is no `#list`, no count
local, and no bridge whose name suggests a count - the four bridge names in
`collection_tips_list` are `update_tips_list` (×3) and `is_font_cache_ready`;
the eleven in `option_button_top` are `is_no_name_oname` (×3), `is_oname` (×3),
`set_help_message`, `open_popup`, `delete_oname`, `vibrate`, `decided_oname`.
None of them asks for a length. (C)

The count-shaped values that *do* appear, and what they really are:

| value | where | what it counts (D) |
|---|---|---|
| `SUB_CATEGORY_NUM` | ct main.p0 pc0 (`LT 0 < SUB_CATEGORY_NUM`), ct main.p2 pc104, pc107, pc119 | **not** item count - it is the page/category count. At pc104-108 Lua computes `(cur - SUB_CATEGORY_NUM) % SUB_CATEGORY_NUM` and at pc118-120 `(cur + 1) % SUB_CATEGORY_NUM`, then passes the result to `update_tips_list` (pc113, pc125). It is a **modulus for paging**, used with `ADD` (pc118) and `SUB` (pc106) and `MOD` (pc108, pc120) |
| `ITEM_INDEX_INIT` / `ITEM_INDEX_NONE` / `ITEM_INDEX_FIRST` / `ITEM_INDEX_LAST` | ct p1 pc12, p2 pc48; ob p3 pc39, pc49, p6 pc13, p6 pc68 | **sentinels**, not counts. `ITEM_INDEX_LAST` is passed straight to `select_item` (ob p3 pc38-40) which only makes sense as a sentinel |
| integer literal `2` | ob main.p6 pc119, `LT A=0 B=3 C=293` where `K[37]=2` (tag `0x13`) | the only bare numeric literal compared against a scroller index. It is a **threshold**, not a total: the guard at pc114-120 is "if not returning from cancel and the saved index is `ITEM_INDEX_NONE` and the current index `< 2`, restore focus". **D** |
| `BUTTON_ID_NONE` | ct main.p2 pc126, ob main.p6 pc144 | a "nothing selected" sentinel in the *selector* index space, not an item count |

**Largest count these scripts handle by construction: none is visible.** The
only number either script ever builds is a page index reduced modulo
`SUB_CATEGORY_NUM`, and that value is never in Lua (it comes from `_ENV`), so
even the page count is not recoverable from these chunks. (C)

The corollary that matters for the mod: **these two chunks contain no evidence
about whether a scroller can hold 90 rows**, because they never say how many it
holds.

---

## 5. Question 5 - layout root, part, group and pane names

Exact strings only; no layout archive was opened. (C)

### 5.1 `collection_tips_list`

| name | proto / pc | what it is passed to |
|---|---|---|
| `selector` | main.p1 pc36 | `selector.setup(layout_view, "selector", config)` - CALL pc38, `B=5` -> **3 arguments** |
| `set_txt_keyhelp_l` | main.p1 pc42 | `selector.setup_button(BUTTON_ID_LEFT, "set_txt_keyhelp_l")` - CALL pc43, `B=4` -> 2 arguments |
| `set_txt_keyhelp_r` | main.p1 pc47 | `selector.setup_button(BUTTON_ID_RIGHT, "set_txt_keyhelp_r")` - CALL pc48, 2 arguments |
| `LayoutRootList` | main.p2 pc35, pc143 | the argument to `ipairs` (CALL pc36, pc144, `C=4` -> 4 results); every entry has `set_enable_input(bool)` called on it (pc38-40, pc146-148). **D:** this is the scene's list of layout roots |

Animation names (not panes): `in` (p1 pc3, p2 pc45, pc160), `out` (p2 pc160),
`subcat_on` (p1 pc70), `subcat_off` (p1 pc75), and the tag constant
`SUB_CATEGORY_ANIM_TAG` read from `_ENV` at p1 pc7. (C)

**No pane is ever fetched by name in this chunk** - there is no `get_pane` and
no `get_parts` call anywhere in it. (C)

### 5.2 `option_button_top`

| name | proto / pc | what it is passed to |
|---|---|---|
| `selector_1` | main.p0 pc21 | `selector.setup(layout_view, "selector_1", config)` - CALL pc23, `B=5` -> 3 arguments |
| `selector_0` | main.p0 pc58 | `selector.setup(layout_view, "selector_0", config)` - CALL pc60, 3 arguments |
| `sel_btn_wave` | main.p0 pc27 | `setup_button(FOCUS_VIBRATION, "sel_btn_wave")` - CALL pc28, `B=4` |
| `scr_ctrl` | main.p0 pc32 | `setup_button(FOCUS_SCROLLER, "scr_ctrl")` - CALL pc33, `B=4` |
| `btn_keyhelp_delete` | main.p0 pc64 | `setup_button(0, "btn_keyhelp_delete")` - CALL pc65, `B=4` |

The one pane lookup, main.p1 pc5-15 - **note the name comes from the selector,
not from a row index**:

```
[  4]  GETTABUP  R[1]  layout_view
[  5]  SELF      R[1]  R[1][get_parts]          ; R[2] := receiver
[  6]  GETUPVAL  R[3]  up[1]
[  7]  SELF      R[3]  R[3][get_button]         ; R[4] := receiver
[  8]  LOADK     R[5]  K[5] = 0
[  9]  CALL      A=3 B=3 C=2                    ; get_button(0) -> 1 result
[ 10]  SELF      R[3]  R[3][get_name]
[ 11]  CALL      A=3 B=2 C=0                    ; get_name(): 0 args, multret
[ 12]  CALL      A=1 B=0 C=2                    ; get_parts(...): B=0 -> up to L->top
[ 13]  SELF      R[2]  R[1][set_visible]
[ 14]  MOVE      R[4]  R[0]
[ 15]  CALL      A=2 B=3 C=1                    ; set_visible(self): 1 arg
```

`get_parts` is called with `B = 0`, i.e. its argument count is **not
resolvable from the bytes** (variadic through `L->top`); the argument is the
result of `selector.get_button(0).get_name()`. (C)

Animation names: `on_plt_menu_lyt_00` (p0 pc83), `off_plt_menu_lyt_00` (pc88),
`in` (p6 pc47, pc52). (C)

**No group name appears in either chunk** - neither `get_group`/`get_groups` nor
any `grp_`-prefixed string. (C)

---


## 6. Question 6 - scrolling, paging, held-repeat and page jumps

### 6.1 `collection_tips_list` - category paging, not row scrolling

No method named `special_input_*` is called here at all. Movement is done with
the **shoulder-button constants** and a **modulus**, then handed to native code:

| pc | instruction | meaning |
|---|---|---|
| p2 pc70-72 | `virtual_input.is_pressed(BUTTON_EX_LEFT)`, `CALL B=3 C=2` -> 1 arg, 1 result | is the left shoulder pressed |
| p2 pc76-78 | `selector.decide_button(BUTTON_ID_LEFT)`, `CALL B=3 C=1` -> 1 arg | force the left button to decide |
| p2 pc85-87 | `virtual_input.is_pressed(BUTTON_EX_RIGHT)` | right shoulder |
| p2 pc91-93 | `selector.decide_button(BUTTON_ID_RIGHT)` | right button decide |
| p2 pc79-82, pc94-97 | `UiSoundManager.play_se_label("se_system_page_change")`, `CALL B=2 C=1` | page-change sound |
| p2 pc98-100 | `selector.get_decided_button_id()`, `CALL B=2 C=2` -> 0 args, 1 result | which button was decided |
| p2 pc104-113 | `(cur - SUB_CATEGORY_NUM) % SUB_CATEGORY_NUM` -> `invoke("update_tips_list", idx)`, `CALL B=3 C=1` -> 2 args, 0 results | page left |
| p2 pc118-125 | `(cur + 1) % SUB_CATEGORY_NUM` -> `invoke("update_tips_list", idx)` | page right |
| p2 pc126-131 | if `BUTTON_ID_NONE` then `selector.clear_selection()` | clear a stale selection |

Plus cursor initialisation at p1 pc11-18: `scroller.select_item(ITEM_INDEX_INIT, false)`
and `scroller.set_focus(true)`. (C)

`SUB_CATEGORY_NUM` is read at main.p0 pc0, inside a 7-instruction predicate
`return 0 < SUB_CATEGORY_NUM` (pc0 `GETTABUP`, pc1 `LT K[0]=0 < R[0]`, pc3
`LOADBOOL false`, pc4 `LOADBOOL true`, pc5/pc6 `RETURN`). **D:** this looks like
an "are there any sub-categories at all" guard. Its value is not in the chunk. (C)

### 6.2 `option_button_top` - cursor to first/last plus horizontal special input

| pc | instruction | meaning |
|---|---|---|
| p3 pc28 / pc29 | `selector.input_direction_is_zero()`, `CALL B=2 C=2` -> 0 args, 1 result | is the stick neutral |
| p3 pc33 / pc34 | `selector.input_direction_is_upward()` | held-up test |
| p3 pc38-40 | `scroller.select_item(ITEM_INDEX_LAST)`, `CALL B=3 C=1` -> **1 arg** | jump the cursor to the sentinel end |
| p3 pc43 / pc44 | `selector.input_direction_is_zero_x()` | held-neutral-x test |
| p3 pc48-50 | `scroller.select_item(ITEM_INDEX_FIRST)`, `CALL B=3 C=1` -> **1 arg** | jump to the other sentinel end |
| p3 pc60-61 | `scroller.get_selected_item()` -> 1 result | read the cursor |
| p4 pc25-27 | `scroller.special_input_is_leftward(false)`, `CALL B=3 C=2` -> 1 arg, 1 result | left special input, non-consuming |
| p4 pc33-35 | `scroller.special_input_is_rightward(true)`, `CALL B=3 C=2` -> 1 arg, 1 result | right special input, consuming |
| p4 pc62-64 | `UiSoundManager.play_se_label("se_system_cursor")` | cursor sound on focus change (p4 pc57-60) |
| p6 pc11-15 | `scroller.select_item(ITEM_INDEX_INIT, false)`, `CALL B=4 C=1` -> **2 args** | cursor reset on entry |
| p6 pc88-90 | `scroller.get_selected_item()` -> 1 result | read the cursor |

**Held-repeat is not implemented in Lua in either chunk.** The only repeated
tests are the two `is_pressed(BUTTON_EX_*)` calls in `collection_tips_list`,
which are edge tests. **D:** in `option_button_top` the analog of held-repeat is
delegated wholesale to `special_input_is_leftward/rightward`; in
`collection_tips_list` the page arithmetic runs once per decided button, not per
frame. Neither statement is about native timing. (C for the calls, D for timing.)

### 6.3 What neither chunk has

No `INPUT_*` constant is read by either chunk (their `_ENV` read sets, section
0/`derived.json`, contain no `INPUT_` name). So the headgear screen's UP/DOWN
cursor arithmetic - `select_item(SCROLLER_ITEM_NUM - 1, true)` at
`hat_body_layout` p11 pc43-47, recorded by P6-HAT-UI 4.4 - **has no
counterpart here**: these two screens leave the cursor entirely to the host and
never step it by one row. (C)

---

## 7. Question 7 - sweep of all 86 chunks

`evidence/P8-LUA-LIST/sweep.txt` and `rowfill.txt` hold the full output; the
check script re-derives the headline numbers (86 chunks, and the exact set of
chunks that write the `scroller` global) on every run.

Method: for each of the 86 chunks (77 under `ui/script/`, 9 under
`ui/script_patch/`), every `SELF` with a string-constant method, every `_ENV`
read and write, every `string.format` call with its format string, and every
pane/part lookup (`get_pane`, `get_parts`, `get_part`, `get_group`,
`get_group`, `get_button`, ...) in the same prototype.

### 7.1 Which chunks call any of the methods from questions 2 or 3

**39 of 86 chunks** contain at least one `SELF` whose method name is one of the
nine P8 names *or* one of the nine P6 names. The raw per-site table is
`sweep.txt` section A; the chunk list is section B. Concentration:

| group | chunks |
|---|---|
| Mii maker (`chara_make/`) | `make_mii_edit_actor`, `make_mii_hat_body_layout`, `make_mii_select_actor`, `make_mii_special_actor`, `make_mii_voice_actor`, plus the `script_patch` copy of `make_mii_edit_actor` |
| collection | `collection_shop_top`, `collection_tips_list`, `collection_tips_top` |
| option | `option_button_controller`, `option_button_select`, `option_button_top`, `option_language`, `option_melee_top`, `option_sound_top`, `option_top` |
| online | `online_any`, `online_onmelee`, `online_parallel`, `online_priority`, `online_watch` |
| the rest | `rule_itemswitch_actor`, `rule_stageswitch_actor`, `special_various`, `main_menu`, `main_menu_common`, `stage_select_actor`, `stage_select_bgm`, `local_mode_select`, `standard_continue`, `standard_difficulty`, and 6 of the 9 `script_patch` chunks |

`set_enable`, `set_focus`, `has_focus` and `is_cancelled` are **not**
scroller-specific - they are generic selector/frame methods appearing on
`LayoutButtonSelector`, `LayoutRoot` and `ComFrameActor` receivers as often as
on the scroller. So "39 chunks call one of these names" is *not* "39 chunks use
a scroller"; it is an upper bound. (B for the count, D for the reading)

**Exactly two chunks write the `scroller` global in all 86**, and both write
`nil` (section 1):

```
ui/script/menu/collection/collection_tips_list.lc   main pc6
ui/script/menu/option/option_button_top.lc          main pc5
```

This confirms P6-HAT-UI 2.1's cross-check and adds the missing detail that both
writes are `= None`. (B, re-asserted on every check run)

### 7.2 Which chunks set text on a pane whose name is built with a row index

`rowfill.txt` section H lists every prototype that both builds a `%d`-bearing
name with `string.format` and performs pane/part lookups. **Fifteen chunks
qualify** (section H; counted from `rowfill.txt`, not asserted by the check
script). A sixteenth, `make_mii_hat_body_layout.lc`, carries a `%d` part-name
constant (`set_parts_scr_item_%02d`, p6/p7 K[7]) but performs **no** pane/part
lookup in those prototypes, so it does not reach section H - it is listed below
from section I of the same file and is marked accordingly. The requested
table:

`row-fill` = a `set_text_*` call in the same prototype as the `%d` name builder.

| chunk | object / global name | row-fill | count source |
|---|---|---|---|
| `menu/chara_make/make_mii_special_actor.lc` | part `set_special_item_%02d` (p2 pc22) / `set_item_%02d` (p9 pc19); panes `set_txt_num`, `set_txt_title`, `set_txt_val`, `set_txt_desc` | **YES** - `set_text_message` p2 pc37-39 (text from a **Lua table lookup** `R[2][R[6]]`), p10 pc45-47 and pc56-58 (text from a **bridge return**); `set_text_number_int32` p10 pc34-36 | **a global constant read from `_ENV`**: `SKILL_COMMAND_NUM` (p2 pc14; `for` pc13-16, FORLOOP pc50) and `SPECIAL_SKILL_NUM` (p9 pc11; p10 pc17) |
| `menu/chara_make/make_mii_edit_actor.lc` | parts `set_item_00`..`set_item_03`, `set_item_05` (LOADK pc17/29/41/53/69) | **no** - fetched and *animated* (`play_animation("category_0N")`, `play_animation("value_txt")`), never texted. The one `set_item_%02d` (pc106) sits in the **selector-button** loop `FORPREP` pc100 -> `FORLOOP` pc110, i.e. it registers buttons, not rows | none: the row set is five hard-coded part names plus whatever the `%02d` button loop covers. `set_item_04` has **no string constant** in this prototype - consistent with P6-EDIT-MENU's note that it is registered only by the `%02d` loop |
| `script_patch/chara_make/make_mii_edit_actor.lc` | same | same (patch copy) | same |
| `menu/melee/rule_stageswitch_actor.lc` | part `set_part_stage_%03d` (p14 pc49) | **no** `set_text_*` in `main.p14` | loop bound is an argument, not a constant read here |
| `menu/melee/special_various.lc` | parts `set_parts_sub_btns_%02d` (p6 pc16), `set_parts_sub_btn_%02d` (p6 pc54), `set_parts_btn_%02d` (p7 pc11) | **partial** - `set_text_message` sites do exist in p6/p7 (`sweep.txt` D), but nothing here shows they land on the *indexed* panes. **D, not claimed** | not established from these prototypes |
| `menu/common/stage_select_actor.lc` + 3 `script_patch` copies | parts `mel_over_return_0%d` (p50 pc195), `mel_return_0%d` (p50 pc202) | **partial** - `set_text_message` exists in `main.p50` (pc190, pc197) and in `main.p51` of the patch copies (pc213, pc220), same prototype as the `%d` builders. **D, not claimed** - the receiver chain is not traced here | not established |
| `menu/online/online_priority.lc` | `selector_%d` (p2 pc15), `text_%02d` (p2 pc22) | **no** - the `set_text_string` sites are p1 pc14 and pc26, a *different* prototype | n/a |
| `menu/option/option_language.lc` | `set_btn_%02d` (p0 pc34, pc71) | **no** `set_text_*` in `main.p0` | n/a |
| `menu/option/option_button_controller.lc` | `ctr_set_%s` (pc39), `set_parts_ctr_%s_l/_r/_zl/_zr/_ct/_clr/_cb/_a/_b/_st/_x/_y` (pc67..pc166) | **no** `set_text_*` in `main.p10` (they are all in `main.p6`) | n/a |
| `menu/spirits/spirits_return_anim_actor.lc`, `spirits_summon_anim_actor.lc` | bare `%02d` (p1 pc21/pc47, p4 pc64/80/98, ...) | **no** `set_text_*` in any of those prototypes | n/a |
| `standard/standard_result.lc` | bare `%02d` (p1 pc163) | **partial** - `main.p1` has both `set_text_message` (pc38, pc47), `set_text_message_args` (pc54) and three `get_pane` sites fed by that format. **D, not claimed** | not established |
| `menu/chara_make/make_mii_hat_body_layout.lc` *(from section I, not H)* | `set_parts_scr_item_%02d` (p6 K[7], p7 K[7]) | **no** - no pane/part lookup at all beside the format, and its single `set_text_message` (p4 pc6) is the sort label, exactly as P6-HAT-UI 2.4 recorded | n/a |
| `menu/common/stage_select_bgm.lc`, `menu/main/main_menu*.lc`, `local_mode_select.lc`, `online_*` remainder, and every other chunk in the 86 | - | **no** | - |

**One chunk is unambiguously the answer: `make_mii_special_actor.lc`.** It is
the only chunk where a per-row numeric `for` loop, an index-formatted part name,
a Lua table of cached row panes and a `set_text_message` all appear in the same
prototype. Section 8.

The honest limit: the "partial" rows are prototypes where a `%d` format and a
`set_text_*` coexist. Deciding whether the text lands on the *indexed* pane
needs per-register dataflow that this task's back-tracer does not perform.
**I am not claiming any of those rows is a row-fill.**
---

## 8. Question 8 - the simplest screen where Lua owns a list of text rows

**It is the Mii special-move screen, `ui/script/menu/chara_make/make_mii_special_actor.lc`,
and it is already inside the Mii maker scene.** Three prototypes matter:
`main.p2` (the four command rows), `main.p9` (the per-skill option rows) and
`main.p10` (where their text is actually written).

### 8.1 How the rows are built

`main.p9`, 46 instructions, is the whole row-construction loop:

```
[  2][  4][  6][  8]  NEWTABLE x4          -> list_parts, list_number_pane,
                                              list_name_pane, list_help_pane
[ 10]  LOADK     R[1] = 1
[ 11]  GETTABUP  R[2] = up[0]["SPECIAL_SKILL_NUM"]     ; the row count
[ 12]  LOADK     R[3] = 1
[ 13]  FORPREP   A=1 sBx=31  -> pc 45
--- loop body, i in R[1], 0-based index in R[4] ---
[ 19]  LOADK     R[9] = "set_item_%02d"
[ 20]  SUB       R[10] = R[4] - 1
[ 21]  CALL      A=8 B=3 C=0    string.format("set_item_%02d", i-1)
[ 22]  CALL      A=6 B=0 C=2    layout_view:get_parts(<name>)   ; B=0 -> L->top
[ 23]  SETTABLE  R[5][R[4]] = R[6]            list_parts[i] := part
[ 24..30]  list_number_pane[i] = list_parts[i]:get_pane("set_txt_num")
[ 31..37]  list_name_pane[i]   = list_parts[i]:get_pane("set_txt_val")
[ 38..44]  list_help_pane[i]   = list_parts[i]:get_pane("set_txt_desc")
[ 45]  FORLOOP   A=1 sBx=-32 -> pc 14
```

`main.p2` is the same idea at the outer level: `for R[3] = 1, SKILL_COMMAND_NUM,
1` (`FORPREP` pc16 `sBx=33` -> `FORLOOP` pc50 `sBx=-34`), fetching
`get_parts(string.format("set_special_item_%02d", i-1))` at pc19-25 and
`play_animation(string.format("category_%02d", i-1), 1.0)` at pc26-33, then
caching `set_txt_num` and `set_txt_val` per row at pc40-49.

### 8.2 How a row's text is set - two sources

**(a) from a Lua table lookup**, `main.p2` pc34-39 - the row's *title*:

```
[ 34]  SELF      R[8] := R[7]["get_pane"]         ; R[7] is the row's part
[ 35]  LOADK     R[10] = "set_txt_title"
[ 36]  CALL      A=8 B=3 C=2                     ; get_pane: 1 arg, 1 result
[ 37]  SELF      R[9] := R[8]["set_text_message"]
[ 38]  GETTABLE  R[11] := R[2][R[6]]              ; <-- table lookup, R[6] = row
[ 39]  CALL      A=9 B=3 C=1                     ; set_text_message: 1 arg
```

`R[2]` is the 4-entry table built at pc7-12 by `NEWTABLE A=2 B=4` + `SETLIST
B=4` from four `LOADK`s: `mnu_mmiif_setup_sp_move_normal`,
`mnu_mmiif_setup_sp_move_width`, `mnu_mmiif_setup_sp_move_up`,
`mnu_mmiif_setup_sp_move_btm`. **So the text source is a constant message key
chosen by row index** - not a bridge return. (C)

**(b) from a bridge return**, `main.p10` pc32-58 - the row's number, name and
help text:

```
[ 34]  SELF      R[6] := R[6]["set_text_number_int32"]
[ 35]  MOVE      R[8] = R[5]                     ; the row index itself
[ 36]  CALL      A=6 B=3 C=1                     ; 1 arg
[ 37]  GETTABUP  R[6] := up[2]["UiScriptPlayer"]
[ 38]  GETTABLE  R[6] := R[6]["invoke"]
[ 39]  LOADK     R[7] = "get_skill_name_label"
[ 40]  GETTABLE  R[8] := R[0]["command_id"]
[ 41]  SUB       R[9] = R[5] - 1
[ 42]  CALL      A=6 B=4 C=2                     ; 3 arguments, 1 result
[ 43]  GETTABLE  R[7] := R[0]["list_name_pane"]
[ 44]  GETTABLE  R[7] := R[7][R[5]]               ; the cached row pane
[ 45]  SELF      R[7] := R[7]["set_text_message"]
[ 46]  MOVE      R[9] = R[6]                     ; <-- the bridge return value
[ 47]  CALL      A=7 B=3 C=1                     ; 1 arg
[ 48..53]  same shape for "get_skill_help_label"
[ 54..58]  list_help_pane[i]:set_text_message(<result>)
```

**So: row index source = the `for` loop counter; text source = either a Lua
table of constant message keys or the return value of a `UiScriptPlayer.invoke`
bridge.** Both are plain Lua. (C)

### 8.3 The complete list of host globals and bridge names it needs

Read but **never** written by these prototypes. All are `_ENV` globals or
`UiScriptPlayer.invoke` names; none of them is created by the script.

| kind | name | where | used for |
|---|---|---|---|
| host object | `UiScriptPlayer` | p10 pc37, pc48 (`GETTABUP up[2]`) | the bridge dispatcher |
| host object | `layout_view` | p2 pc18, p9 pc15, p10 pc11 (a field of the module's own state table) | the scene's view |
| host object | `LayoutButtonSelector` / `LayoutButtonSelectorConfig` | p0 / p1 (screen chrome only) | cursor buttons |
| host object | `LayoutRootList` | main | the scene's root list |
| host object | `ComFrameActor` | main | frame help text / cancel |
| host object | `UiSoundManager` | main | cursor and decide sounds |
| host constant | `string` | p2 pc20, p9 pc17, p10 pc6 | `string.format` for row names (this is a Lua base global, not a host object) |
| host constant | `SKILL_COMMAND_NUM` | p2 pc14 | **the row count of the command list** |
| host constant | `SPECIAL_SKILL_NUM` | p9 pc11, p10 pc17 | **the row count of the option list** |
| host constant | `UI_SE_ID_CURSOR`, `UI_SE_ID_DECIDE`, `UI_SE_ID_INFOWINDOW_OPEN`, `INPUT_OK` | main | sounds / confirm |
| host method | `layout_view:get_parts(name)` | p2 pc19, p9 pc16 | the row part, by index-formatted name |
| host method | `layout_view:get_pane(name)` | p2 pc34, p2 pc52-54 | a pane on a part |
| host method | `part:get_pane(name)` | p9 pc27, pc34, pc41 | the row's panes |
| host method | `part:play_animation(name, t)` | p2 pc26 | the row's category animation |
| host method | `pane:set_text_message(key)` | p2 pc37, p10 pc45, pc56 | **the row text** |
| host method | `pane:set_text_number_int32(n)` | p10 pc34 | the row number |
| bridge | `get_skill_name_label` (3 args, 1 result) | p3 pc10, p4 pc20, p10 pc42 | **the row name text** |
| bridge | `get_skill_help_label` (3 args, 1 result) | p4 pc30, p10 pc53 | the row help text |
| bridge | `replace_skill` (3 args, 0 results) | p4 pc49 | writes the chosen option |
| bridge | `replace_skill_subwindow` (2 args, 0 results) | p10 pc64 | sub-window variant |
| bridge | `get_skill_id` (2 args, 1 result) | p14 pc16 | reads the saved option |
| bridge | `set_skill_id` (3 args, 0 results) | p14 pc43 | writes the saved option |

The chunk writes only `main` and `initialize` into `_ENV` (main pc52, pc54) - its
own exports - and never assigns any of the names above. (B, C)

### 8.4 What this does and does not settle for the mod

- **Settled (C):** a UI script in this game can own a list of text rows outright,
  build the row count in Lua, fetch each row's panes from the layout by an
  index-formatted name, cache them in Lua tables and set their text. The count
  comes from a **global constant read from `_ENV`**, not from `#table` - so the
  number of rows is bounded by what the layout declares, not by a Lua array.
- **Settled (C):** the scroller is not involved in this at all.
- **D, and explicitly not verified:** whether `SKILL_COMMAND_NUM`,
  `SPECIAL_SKILL_NUM`, `layout_view`, `get_parts`, `get_pane`,
  `set_text_message` and `set_text_number_int32` **exist and behave the same way
  in another scene**. Their existence and semantics in the *Mii special-move
  screen* is what was measured. Existence in the Mii *maker* menu screens beyond
  this one chunk is **unverified** - the only evidence that they generalise is
  that 21 other chunks in the 86 call `get_pane`/`get_parts`, and that
  `make_mii_edit_actor.lc` (same scene, same directory) uses
  `layout_view:get_parts("set_item_0N")` the same way.
- **D:** the largest row count visible anywhere in these 86 chunks is
  `SKILL_COMMAND_NUM` / `SPECIAL_SKILL_NUM`, whose values are not in the chunks.
  Per STATUS.md the coordinator has these elsewhere as 4 and 3 respectively; this
  task did not re-derive them and does not rely on them. So **this report
  contains no evidence that a 90-row Lua-owned list fits any existing layout.**

---

## 9. The check script and its negative controls

### 9.1 What it asserts

`evidence/P8-LUA-LIST/check_p8_lua_list.py` re-derives every pc, opcode,
operand, constant and argument count cited above, straight from the chunk bytes,
and exits non-zero on any mismatch. It asserts:

1. the **size and sha256** of all five analysed chunks (section 0.1);
2. `lua53-inspect verify` passes structurally for each of them;
3. the **per-prototype instruction counts** of the three target chunks;
4. **290 per-instruction claims** - `(chunk, proto, pc, opcode, A, B, C, Bx)` -
   for every instruction this report quotes, including the operand shapes that
   carry the argument counts (`CALL B=4` -> 2 arguments after `SELF`);
5. **absence assertions**: none of the fifteen forbidden names appears in any
   constant of `collection_tips_list` or `option_button_top` (the list has 17
   entries; the two Lua base-global names `string` and `format` are excluded
   from the per-constant test and covered instead by the structural
   `string.format`-call test below), and neither chunk contains a
   `string.format` call;
6. the **86-chunk sweep facts**: exactly 86 chunks under `ui/script/` +
   `ui/script_patch/`, and the exact set of chunks writing the `scroller`
   global is `{collection_tips_list.lc, option_button_top.lc}`.

### 9.2 Observed run, from the workspace root

```
$ python mods/mii_customizer/evidence/P8-LUA-LIST/check_p8_lua_list.py
1667 checks, 0 failures
exit 0
```

(Same text in `evidence/P8-LUA-LIST/check_run_output.txt`.)

The check script accepts `P8_GD_ROOT` / `P5_GD_ROOT` environment variables so
the negative controls can point the identical assertions at a damaged copy
without touching `gamedata/`. With no variables set it reads the real files.

### 9.3 Negative controls - three, all run, with observed results

Driven by `scratch/2026-10-05_P8-LUA-LIST/negative_controls.py`; full output in
`evidence/P8-LUA-LIST/negative_controls_output.txt`.

**Control 1 - byte flip in a cited instruction.** Flipped one bit of the byte at
the instruction offset of `collection_tips_list` `main.p2` pc108, which this
report cites as `MOD` (the page-index modulus). Observed:

```
--- control 1: flip one byte at main.p2 pc108 (MOD)
    exit 1  (rejected, as required)
    1667 checks, 2 failures
      FAIL collection_tips_list sha256 3074f50a... != 89f077cc...
      FAIL collection_tips_list/main.p2/pc108 opcode POW != MOD
```

Both the hash guard and the per-instruction claim fired, and the reported
opcode (`POW`) is exactly the neighbouring opcode in `OPNAMES`, which is what a
one-bit change in the low 6 bits produces. **Rejected, exit 1.**

**Control 2 - rewrite a cited constant.** `setconst` of
`update_tips_list` -> `update_tops_list` at `collection_tips_list` `main.p1`
K[33], the bridge name this report cites at pc62. The CLI **refused** first:

```
--- control 2: CLI setconst without --allow-used
    exit 1 (refused)
      target      main.p1 K[33] = 'update_tips_list'
      new text    'update_tops_list' (16 chars, was 16)
      REFUSING: this constant is read by 1 instruction(s):
```

Driven through the library to force the damage anyway, the check then reported:

```
    exit 1  (rejected, as required)
    1667 checks, 1 failures
      FAIL collection_tips_list sha256 58a59985... != 89f077cc...
```

**Rejected, exit 1.** Note the rewrite was the same length, so only the hash
guard could catch it - the per-instruction claims all still resolved, because
the claim table checks operand *shape*, and the bridge-name claim at pc62 checks
the `Bx` index, which did not move. That is the correct division of labour and
is stated here rather than hidden.

**Control 3 - inject a name the report asserts is absent.** Appended the string
constant `set_text_message` to `collection_tips_list` `main.p2` as K[46].
Observed:

```
    exit 1  (rejected, as required)
    1667 checks, 3 failures
      FAIL collection_tips_list size 2665 != 2647
      FAIL collection_tips_list sha256 fda54f74... != 89f077cc...
      FAIL collection_tips_list unexpectedly contains constant 'set_text_message'
```

**Rejected, exit 1.** This is the control that matters most for section 3's
absence claims: it shows the "no `set_text_message` here" statement is a real
assertion over the constant stream, not a comment.

Two integrity runs bracket the controls: the baseline check before them and a
rerun after both pass with `1667 checks, 0 failures, exit 0`, and the script
re-hashes the real `gamedata/` files at the end and reports
`gamedata/ untouched: True (collection_tips_list sha256 89f077cc...)`.
Control summary line: `controls: ALL BEHAVED AS EXPECTED`, exit 0.

---

## 10. Unresolved edges

All **D**. None can be resolved from these chunks.

1. **Who assigns the host `scroller`.** Both writers assign `nil`. The global
   must therefore be rebound natively between chunk load and `main` run. What
   binds it, and whether the binding is per-scene or per-actor, is unknown.
2. **Whether the scroller class has a count setter.** No chunk in the 86 calls
   one, so the 90-row question is untouched by this task.
3. **`special_input_is_leftward/rightward` vs `..._upward/..._downward`.** One
   class with four methods, or two classes sharing the global name?
4. **`select_item`'s second argument.** Present at ct p1 pc14 and ob p6 pc15,
   absent at ob p3 pc40/pc50. **D:** a scroll/page flag.
5. **`SUB_CATEGORY_NUM`'s value**, and therefore the number of tips pages.
6. **`option_button_top` main.p6 pc119's literal `2`** - a threshold whose
   meaning is not derivable from the guard around it.
7. **`SKILL_COMMAND_NUM` and `SPECIAL_SKILL_NUM`** - the two row counts of the
   simplest Lua-owned list. Not in these chunks.
8. **The "partial" rows of the section 7.2 table** - whether the text lands on
   the indexed pane. Needs per-register dataflow this task did not do.
9. **Whether any of section 8.3's objects exist outside the special-move
   screen.** Unverified, explicitly.
10. **Runtime behaviour.** Nothing here was run. No emulator, no console, no
    video. Every result is tier B (offline tool output) or C (pinned bytes).

---

## 11. Persisted task summary

**Task ID:** P8-LUA-LIST
**Status:** **DONE** - all eight questions answered with chunk, prototype and
pc; every cited pc, opcode, constant and argument count is re-derived by the
check script; three negative controls were run and each rejected its input.
The only qualifier is evidence tier: **tier B and C only. No runtime behaviour
is claimed anywhere, and all native semantics are marked D.**

### Answer in one paragraph

A UI script **cannot** build or fill a scrolling list through the scroller: no
chunk in the 86 constructs one, the only two that write the `scroller` global
write `nil`, and neither sets any row text or item count. A UI script **can**
own a list of text rows by a different route, and the game already does it in
`make_mii_special_actor.lc`: a numeric `for` over a global count constant,
`layout_view:get_parts(string.format("set_item_%02d", i-1))` per row, the row's
panes cached in Lua tables, and `pane:set_text_message(...)` fed either from a
Lua table of constant message keys or from a `UiScriptPlayer.invoke` return
value. Whether that route works at 90 rows, and whether its host objects exist
outside that one screen, is **unverified**.

### Changed / created files (this task's exclusive paths only)

| path | what |
|---|---|
| `research/P8-LUA-LIST.md` | this report (the deliverable) |
| `evidence/P8-LUA-LIST/check_p8_lua_list.py` | re-derivation check, 1667 assertions, exits non-zero on mismatch |
| `evidence/P8-LUA-LIST/check_run_output.txt` | the observed run (`1667 checks, 0 failures`) |
| `evidence/P8-LUA-LIST/negative_controls_output.txt` | the three controls, verbatim |
| `evidence/P8-LUA-LIST/{header,summary,protos,constants,dis}_collection_tips_list.txt`, `..._option_button_top.txt`, `verify_all.txt` | raw `lua53-inspect` output |
| `evidence/P8-LUA-LIST/dis_make_mii_special_actor.txt`, `dis_make_mii_edit_actor.txt` | raw disassembly of the section 7/8 chunks |
| `evidence/P8-LUA-LIST/callflow.txt`, `derived.json` | per-call-site globals, methods and bridges for the three target chunks |
| `evidence/P8-LUA-LIST/sweep.txt`, `sweep.json` | the 86-chunk method/global/format sweep |
| `evidence/P8-LUA-LIST/rowfill.txt`, `rowfill.json` | the 86-chunk pane/row-fill scan |
| `scratch/2026-10-05_P8-LUA-LIST/derive.py`, `sweep86.py`, `rowfill.py`, `negative_controls.py`, `part6-7.md`, `part8-end.md`, `negctl/` | derivation scratch (not deliverables) |
| workspace-relative `gamedata/mii_customizer/P8-LUA-LIST/ui/script/menu/collection/collection_tips_list.lc`, `.../menu/option/option_button_top.lc`, `.../common/ui_common.lc` | the three extracted chunks (unmodified) |

**No chunk was edited.** No other worker's file was touched. No agent, commit,
branch, emulator run or SD access happened. `STATUS.md`, `CURRENT_INSTALL.md`,
`CHANGELOG.md` and the contracts were not modified - they are the coordinator's.

### Commands actually run, with results

| command | result |
|---|---|
| `tools/arc-extract` on the three paths | exit 0, "3 extracted, 0 failed"; hashes in section 0.1 |
| `cmp` each P8 copy against the P5-UI-API copy | identical, exit 0 (x3) |
| `lua53_inspect.py verify <chunk>` | exit 0 (x5) |
| `lua53_inspect.py {header,summary,protos,constants,dis}` | 12 files written |
| `derive.py` | exit 0; `derived.json`, `callflow.txt` |
| `sweep86.py` | exit 0; 86 chunks, 39 with a hit, 2 scroller writers |
| `rowfill.py` | exit 0; 14 chunks with a `%d` part builder + pane lookup |
| `check_p8_lua_list.py` | **1667 checks, 0 failures, exit 0** |
| negative control 1 (flip a bit at main.p2 pc108) | exit 1: `opcode POW != MOD` + hash mismatch |
| negative control 2 (`setconst update_tips_list` -> `update_tops_list`) | CLI refused (exit 1) then, forced, exit 1 with hash mismatch |
| negative control 3 (append `set_text_message` to main.p2) | exit 1: size, hash and `unexpectedly contains constant 'set_text_message'` |
| post-control rerun + gamedata re-hash | `1667 checks, 0 failures`, exit 0; `gamedata/ untouched: True` |

### Failures and limits, stated plainly

- **No runtime verification of any kind.** No emulator, no console, no video.
  Every statement about what native code *does* is D.
- **The check script caught 16 transcription errors in my own claim table** on
  its first run (an off-by-one on several `option_button_top` pcs, a reversed
  `SETTABUP` operand reading, and a wrong argument-count note). All were fixed
  against the disassembly and the table now passes clean. Recorded because it is
  the evidence that the check is load-bearing rather than vacuous.
- **Nine of the section 7.2 rows are marked "partial"** - a `%d` format and a
  `set_text_*` coexist in a prototype, but nothing here shows the text lands on
  the indexed pane. I am not claiming them as row-fills.
- **The argument count of `option_button_top` main.p1 pc12
  (`get_parts(...)`) is not resolvable** from the bytes: `CALL B=0` means "up to
  `L->top"`. No count is claimed for it or for `main.p1 pc11`.
- **No layout archive was opened.** Every layout name in section 5 is a string
  constant in a chunk, quoted exactly. Nothing about pane existence, part
  contents or row capacity is established.
- **The `read_files` tool mis-parsed arguments throughout this session**, so all
  file reads went through `cat`/`sed` instead. No file was affected.
- **Section 7.2's "special_various / stage_select_actor / standard_result"
  rows would need a finer dataflow pass** to resolve either way. That is the
  obvious next cheap piece of work if the coordinator wants a second candidate
  screen.

### Next experiment

Ordered by value per unit of effort:

1. **Get the values of `SKILL_COMMAND_NUM` and `SPECIAL_SKILL_NUM`, and find the
   layout's row-part inventory for the Mii special screen.** Together these say
   what row count a Lua-owned list has ever been driven to. Cheap: the constants
   are probably immediates in the same native constructor P2-UI-FLOW already
   found (it recorded `SKILL_COMMAND_NUM = 4` and `SPECIAL_SKILL_NUM = 3` as
   immediates in `0x19ddb30`, offline B - this report does not rely on that and
   did not re-derive it).
2. **Sweep `main.bin` for the `set_text_message` / `set_text_number_int32` /
   `get_parts` / `get_pane` binding table.** If those four are one common host
   base class, they are the objects a mod list needs, and their availability
   across scenes follows from that rather than from a per-screen guess.
3. **Resolve the three "partial" rows of section 7.2** with a per-register
   dataflow pass, to see whether a second, non-Mii screen owns its text rows the
   same way - useful as an independent second instance if the first is rejected.
4. **Leave the scroller alone.** Nothing in the 86 chunks suggests a
   script-side count setter, and P8-HAT-NATIVE is the right place to settle it.