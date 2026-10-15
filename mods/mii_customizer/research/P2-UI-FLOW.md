# P2-UI-FLOW - Lua-side data flow of one existing special selector

2026-10-04. Space Bunny Alpha worker. Prompt: `prompts/P2-UI-FLOW.md`.
**Status: DONE, with four explicit unresolved edges (section 9).**

No implementation, no production patch, no archive/layout work, no emulator, no console,
no commits, no edits to the inspector or to any game chunk.

## 1. Inputs (read-only) and hashes

All three are the already-extracted chunks from P1-UI, re-hashed at the start and again
after all writes. **Unchanged**, and identical to the values recorded in P1-UI-DECODE
and P1-LUA-WRITE:

| ARC path | sha256 | bytes |
|---|---|---|
| `ui/script/menu/chara_make/make_mii_edit_actor.lc` | `1f73dff133961b68dbe24641298229b9f3905a44703164563911b105eaa16908` | 10321 |
| `ui/script/menu/chara_make/make_mii_special_actor.lc` | `ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d` | 7799 |
| `ui/script_patch/chara_make/make_mii_edit_actor.lc` | `c777ecc492cea48f6ffd40112b22f96e66219d00969b570a7cc3cf8d7f4a9417` | 10576 |

`evidence/P2-UI-FLOW/input_hashes.txt`. Paths are workspace-relative under
`gamedata/mii_customizer/P1-UI/`. Tool used read-only:
`mods/mii_customizer/tools/lua53-inspect/lua53_inspect.py`.

The focus is **one special direction**, taken as `command_id == 1`, the first entry of
the `SKILL_COMMAND_NUM` loop. That choice is stated explicitly because, as section 3
shows, four different indices are in play and only some of them happen to be 1.

## 2. Method, and an independent cross-check of the decoder

Everything below is bytecode evidence about files on disk. To avoid resting on a single
tool, I wrote a second, independent parser and opcode decoder
(`scratch/2026-10-04_P2-UI-FLOW/decode_check.py`) and reconciled it against
`lua53-inspect`. It reproduces the same header length, prototype count, instruction count
and constant count on all three chunks:

```
make_mii_special_actor.lc   header 0x1e (30 bytes)  protos=17  instructions=794  constants=276
make_mii_edit_actor.lc      header 0x1e (30 bytes)  protos=18  instructions=1181 constants=333
script_patch/…edit_actor.lc header 0x1e (30 bytes)  protos=18  instructions=1222 constants=338
```

`lua53-inspect verify` exits 0 on all three with exact byte consumption
(`evidence/P2-UI-FLOW/verify_three_chunks.txt`). The header length was *measured*, not
assumed: my script tries every start offset from 0x10 to 0x2f and keeps only the one that
walks to exactly the last byte with every operand in range. Only 0x1e survives.

Evidence: `evidence/P2-UI-FLOW/independent_decode.txt` (every PC this report cites,
decoded twice by independent code paths).

### 2.1 Three format facts I had to get right, and one tool defect found

Recording these because two of them were live errors in my own first pass, and one is a
real defect in the shared tool.

1. **`size_t`-width upvalue count.** `LoadFunction` reads the upvalue count with
   `loadInt` (4 bytes), not a byte. My first parser used one byte, desynchronised, and
   reported no valid start offset at all. The tool is correct.
2. **String length vs NUL.** The size byte counts the trailing NUL (`size == len + 1`;
   `get_skill_id` is stored as size `0x0d`) but the payload holds only the text bytes.
   So the text is `raw[pos+1 : pos+size]` and the next field starts at `pos+size`.
3. **iABC field order.** `C` is the *lower* field: `A` bits 6-13, `k` bit 22,
   `C` bits 14-22, `B` bits 23-31. My decoder initially had B and C swapped and
   mis-decoded `GETTABUP`. Confirmed against the raw bytes and against `lua53-inspect`'s
   own `POS_C = 14 / POS_B = 23`; after the fix both agree on every cited PC.

**Defect in `lua53-inspect`'s `xref` (not fixed by me; the tool is another task's file).**
`const_uses()` skips an instruction whose opmode is `iABx`, but `OP_JMP` is **`iAsBx`**,
whose B/C fields are the high bits of the jump offset, not RK operands. Any `JMP` whose
offset happens to have bit 8 set is therefore reported as `used via RK.B` for a constant
it never reads. Measured over all prototypes:

| chunk | iAsBx instructions | bogus `RK.B` reports | genuine iABC RK uses | `LOADK` uses |
|---|---|---|---|---|
| special actor | 33 (8 `FORLOOP`, 8 `FORPREP`, 17 `JMP`) | **33** | 336 | 93 |
| edit actor (base) | 139 | **139** | 582 | 68 |
| edit actor (patch) | 146 | **146** | 598 | 69 |

`evidence/P2-UI-FLOW/xref_false_positives.txt`. **Impact on this report: none.** Every
use site I rely on is either a `LOADK` or a `GETTABUP`/`GETTABLE` `RK.C`, all of which are
genuine; I re-derived each one from the raw bytes. But any future worker reading `xref`
output must discard `JMP` rows, and a name whose only listed uses are `JMP` rows is
probably genuinely unused. A one-line fix (`or OPMODES[i.op] & 3 == _IASBX`) belongs to
whoever owns the tool.

## 3. The four indices, kept distinct

This is the part that most needs stating plainly, because three of them are numerically
equal for `command_id == 1` and equating them by that coincidence would be wrong.

| name | what it is | range in this chunk | established by |
|---|---|---|---|
| **UI row / direction index** | which special-move *slot* the user is on; drives `category_%02d` and `set_special_item_%02d` | `0 .. SKILL_COMMAND_NUM-1` | `main.p2` pc13-16, `main.p15` pc58-62 |
| **skill direction** | *not present as a distinct value.* The 4-entry title table in `main.p2` pc7-12 is indexed by the row index | `1..4` titles vs `1..SKILL_COMMAND_NUM` rows | `main.p2` pc38 `R[2][R[6]]` |
| **option number** | which alternative inside one slot; indexes `set_item_%02d` | `0 .. SPECIAL_SKILL_NUM-1` | `main.p15` pc94-98, `main.p9` pc10-13 |
| **native command index** | the value actually passed to `get_skill_id` / `set_skill_id` | **row index − 1**, so `0 .. SKILL_COMMAND_NUM-2` | `main.p14` pc15, pc41 |
| **class** | **absent.** No Mii class is read anywhere in this flow | — | section 7 |

Two consequences worth stating because they are easy to get backwards:

- The **`main.p2` title table is indexed by the raw loop variable**, not by
  `loopvar - 1`. `main.p2` pc17 computes `R[1] = R[6] - 1` for the *part name*
  (`set_special_item_%02d`), but pc38 indexes the 4-element title table with `R[6]`
  unadjusted. So the title table is 1-based while the part name is 0-based. If
  `SKILL_COMMAND_NUM > 4` the title lookup would run off the end of that table; whether
  that ever happens is unresolved (section 9, edge 2).
- The **native command index is 0-based while the selector button id is 0-based too, but
  they are offset by one**: `get_skill_id` receives `row - 1`, and `main.p4`/`main.p10`
  index the cached table with `selected_id + 1`. Both directions of the same convention
  are visible, which is what makes it trustworthy rather than a coincidence.

## 4. Call-flow table (focus: `command_id == 1`)

Chunk: `make_mii_special_actor.lc`. "est." marks argument provenance that is established
from the bytecode; "unresolved" marks native behaviour.

| # | chunk / proto | PC range (byte offsets) | role | arguments & provenance | return usage | unresolved native behaviour |
|---|---|---|---|---|---|---|
| 1 | special / `main` | pc52 (`@0x0fe`) | export `_ENV.main = p14` | — | — | how the host invokes `main` |
| 2 | special / `main` | pc54 (`@0x106`) | export `_ENV.initialize = p15` | — | — | ditto |
| 3 | special / `main.p15` | pc0-18 (`@0x1882`-`@0x18ca`) | bind `layout_root`/`layout_view`/`virtual_input` from `LayoutRootList[1]`; force `out` animation, hide | `LayoutRootList[1]` est. (global table read) | ignored | whether `set_visible(false)`/`stop_animation_at_end` are safe pre-layout |
| 4 | special / `main.p15` | pc38-83 (`@0x190a`-`@0x19ce`) | same for the second layout root, `LayoutRootList[2]` | est. | ignored | ditto |
| 5 | special / `main.p15` | pc38-50 (`@0x191a`-`@0x193e`) | build `LayoutButtonSelectorConfig`: `directional_degree=0.0`, `input_direction_only_y=true`, `is_unique_se=true`, `decide_se_label_code=nil`, `cancel_se_label_code=se_system_cancel`, `cursor_se_label_code=nil`, `error_se_label_code=nil` | all est. (literal constants) | config object | — |
| 6 | **special / `main.p15`** | **pc48-72 (`@0x1942`-`@0x19a2`)** | **`selector = LayoutButtonSelector.new()`; `selector:setup(layout_view, "selector_0", config)`; then `for i = 0 .. SKILL_COMMAND_NUM-1`: `selector:setup_button(string.format("set_special_item_%02d", i))`** | `SKILL_COMMAND_NUM` est. global read at pc59 (bit 8 of C set ⇒ RK ⇒ constant); loop var est. `0`→`N-1`; **button id == row index** | none | the native meaning of a `setup_button` part name; `SKILL_COMMAND_NUM`'s value |
| 7 | special / `main.p15` | pc73-83 (`@0x19a6`-`@0x19ce`) | `setup_button("set_btn_ok")`, `setup_button("set_footer_area")`, then `config.is_unique_se = false` | est. | none | — |
| 8 | special / `main.p15` | pc84-108 (`@0x19d2`-`@0x1a32`) | **second** `selector` (sub-window): `for i = 0 .. SPECIAL_SKILL_NUM-1`: `setup_button(string.format("set_item_%02d", i))` | `SPECIAL_SKILL_NUM` est. global read at pc95; **option number == loop var, 0-based** | none | `SPECIAL_SKILL_NUM`'s value |
| 9 | special / `main.p15` | pc109-178 (`@0x1a36`-`@0x1b4e`) | register the two state tables' `state_in/out/update/setup` handlers against `state_function` state ids `STATE_NONE`, `STATE_MAIN_IN/OUT/UPDATE`, `STATE_SUB_SETUP/IN/OUT/UPDATE`; then call `initialize` on both tables | est. | ignored | how `common/state_function` dispatches these |
| 10 | special / `main.p14` | pc0-3 (`@0x16d8`) | `ComFrameActor:set_sub_title("mnu_mmiif_setup_sp_move_title")` | **the one constant I propose as a diagnostic** (section 8) | ignored | whether `set_sub_title` treats it as a message key or literal text |
| 11 | special / `main.p14` | pc4-7 (`@0x16e8`) | `up[1].set(up[2])` on the state object | est. | ignored | `state_function` API |
| 12 | **special / `main.p14`** | **pc8-18 (`@0x16f8`-`@0x1720`)** | **`for i = 1 .. SKILL_COMMAND_NUM`: `cache[i] = UiScriptPlayer.invoke("get_skill_id", i - 1)`** | `cache` is the upvalue table `up[3]` est. (pc17 `SETTABUP up[3][R[3]]`); `i-1` est. (pc15 `SUB` against `K[4]=1`); **native command index = `i-1`** | return value stored, unvalidated | **what `get_skill_id` returns and whether it is a save id** — the single most important unknown |
| 13 | special / `main.p14` | pc19-24 (`@0x1724`) | `up[4].update_text()`; `up[1].update()` | est. | ignored | — |
| 14 | special / `main.p14` | pc25-33 (`@0x173c`-`@0x175c`) | `coroutine.yield()` in a spin loop guarded by `up[1].get()` vs `up[5]` | `up[5]` is a number constant est. | loop exit | what `get()` returns; why yield in a UI callback |
| 15 | **special / `main.p14`** | **pc34-44 (`@0x1760`-`@0x1788`)** | **`for i = 1 .. SKILL_COMMAND_NUM`: `UiScriptPlayer.invoke("set_skill_id", i - 1, cache[i])`** | all three args est.: name `LOADK` pc40, index `SUB` pc41, value `GETTABUP up[3][R[3]]` pc42; `CALL B=4` ⇒ **3 args** | **return value discarded** (`C=1`) | whether `set_skill_id` persists, and to what |
| 16 | special / `main.p2` | pc0-12 (`@0x2fc`-`@0x32c`) | per-table init: `prev_selected_id=0`, `decided_id=-1`, two pane caches; build the 4-entry title table `{mnu_mmiif_setup_sp_move_normal, _width, _up, _btm}` via `NEWTABLE B=4` + `SETLIST B=4 C=1` | est. | — | title strings are message keys or part names (unresolved) |
| 17 | special / `main.p2` | pc13-50 (`@0x330`-`@0x3c4`) | `for i = 1 .. SKILL_COMMAND_NUM`: `get_parts(format("set_special_item_%02d", i-1))`, `play_animation(format("category_%02d", i-1), 1.0)`, then fill `list_number_pane[i]`, `list_text_pane[i]` from `set_txt_num`/`set_txt_val`; **and** `get_pane("set_txt_title"):set_text_message(titles[i])` | loop var est.; **`i-1` est. for part/animation names, `i` est. for the title table** | pane objects cached | — |
| 18 | special / `main.p2` | pc51-75 (`@0x3c8`-`@0x428`) | cache the three help panes (`set_txt_num_current`, `set_txt_name_current`, `set_txt_desc_current`) and `get_parts("set_btn_ok"):get_pane("set_txt_00"):set_text_message("mnu_footer_ok")` | est. | pane objects | — |
| 19 | special / `main.p3` | pc0-21 (`@0x682`-`@0x6d6`) | `update_list_text`: `for i = 1 .. SKILL_COMMAND_NUM`: `invoke("get_skill_name_label", i-1, cache[i])`; write `list_number_pane[i]` and `list_text_pane[i]` | `CALL B=4` ⇒ **3 args**: name, `i-1`, `cache[i]` — all est. | label stored into panes | whether the label call mutates anything |
| 20 | **special / `main.p4`** | **pc0-8 (`@0x79f`-`@0x7bf`)** | **`update_help_text`: `id = selector:get_selected_button_id()`; `if id < 0 or SKILL_COMMAND_NUM <= id then return end`** | `SKILL_COMMAND_NUM` est. read pc5-6; **`get_selected_button_id` result validated against `[0, SKILL_COMMAND_NUM)`** | early return | whether the native id can be out of that range in practice |
| 21 | special / `main.p4` | pc9-14 (`@0x7c3`) | `skill = cache[id + 1]` (`ADD` pc9, `GETTABUP` pc10); `help_number_pane:set_text_number_int32(skill + 1)` (coordinator correction: pc13 is `ADD A=5 B=2`, and R[2] already holds the cached value, so the number shown is the option + 1, not the row + 1) | **`id+1` into the cache** — the 1-based convention of row 12, seen from the read side | — | — |
| 22 | special / `main.p4` | pc15-34 (`@0x7db`-`@0x827`) | `invoke("get_skill_name_label", id, skill)`; `invoke("get_skill_help_label", id, skill)`; write help panes | `CALL B=4` ⇒ 3 args each; est. | strings stored | — |
| 23 | **special / `main.p4`** | **pc35-49 (`@0x82b`-`@0x867`)** | **`layout_view:play_animation(format("category_%02d", id), 1.0)`; then `invoke("replace_skill", id, skill)`** | est.; `CALL B=4` ⇒ **2 args** | **discarded** | **what `replace_skill` does** — name suggests a live preview apply; unestablished |
| 24 | special / `main.p6` | pc0-24 (`@0xa2d`) | `state_in`: `selector:select_button(0, true)`, `prev_selected_id=0`, `update_help_text()`, enable input, show, `play_animation_and_wait("in")`, set state | est. | — | — |
| 25 | special / `main.p8` | pc0-44 (`@0xbe2`-`@0xc96`) | `state_update` cursor movement: read `get_selected_button_id`, compare to `up[1]`, `select_button(id)`, cursor SE, `update_help_text`, update `prev_selected_id`, `visible_parts("cursor", …)`, `selector:set_selectable(up[1], …)` | `up[1]`/`up[2]` are numeric constants est. | — | what the compared constants are |
| 26 | **special / `main.p8`** | **pc45-96 (`@0xc96`-`@0xd62`)** | **`is_cancel()` → `ComFrameActor:press_cancel()`; else `is_pressed(INPUT_OK)` → `selector:decide_button(...)`; then `decided_id = selector:get_decided_button_id()`; `if decided_id >= 0` → `play_se(UI_SE_ID_DECIDE)`, set state; else `play_se(UI_SE_ID_INFOWINDOW_OPEN)`; and `if ComFrameActor:is_cancelled()` → disable input, set state** | the confirm/back split is **est.** from the two `EQ/LE` tests and the two `play_se` calls | `decided_id` stored in the table | which state each branch enters (constants are numbers, not resolved) |
| 27 | **special / `main.p10`** | **pc0-5 (`@0x112b`-`@0x113f`)** | **`state_setup` (sub-window entry): `command_id = up[0].decided_id`; `skill_id = cache[command_id + 1]`** | `up[0]` is the **first** state table est. (its `decided_id` was written by row 26); `ADD` pc3, `GETTABUP` pc4 | stored on `self` | — |
| 28 | special / `main.p10` | pc6-15 (`@0x1143`) | `play_animation(format("category_%02d", command_id), 1.0)` | est. | — | — |
| 29 | **special / `main.p10`** | **pc16-59 (`@0x116b`-`@0x1217`)** | **`for j = 1 .. SPECIAL_SKILL_NUM`: reset each `list_parts[j]` to `selectedoff`, set `list_number_pane[j]:set_text_number_int32(j)`, `invoke("get_skill_name_label", command_id, j-1)` → `list_name_pane[j]`, `invoke("get_skill_help_label", command_id, j-1)` → `list_help_pane[j]`** | `CALL B=4` ⇒ 3 args each; **`command_id` (the direction) and `j-1` (the option) are passed as separate arguments** — the clearest single place the two indices are provably distinct | strings stored | — |
| 30 | special / `main.p10` | pc60-68 (`@0x121b`) | `invoke("replace_skill_subwindow", command_id)`; set state | `CALL B=3` ⇒ 1 arg | discarded | ditto as row 23 |
| 31 | special / `main.p11` | pc0-28 (`@0x13ca`) | `state_in` (sub): show, `list_parts[skill_id + 1]:play_animation("selectedon", 1.0)`, `selector:select_button(skill_id)`, enable, `play_animation_and_wait("in")` | `skill_id + 1` into `list_parts` est. | — | — |
| 32 | **special / `main.p13`** | **pc0-25 (`@0x15df`-`@0x1643`)** | **`state_update` (sub): if `selector:is_cancelled()` → set state and return; else `d = selector:get_decided_button_id()`; `if d >= 0` then `cache[command_id + 1] = d`; `update_text()`; set state** | **`cache[command_id + 1] = d` is the write-back**: `GETTABLE` pc15 (`R[2] = command_id`), `ADD` pc16 (`R[2] = R[2] + K[7]`, K[7] = 1), `SETTABUP up[2][R[2]] := R[1]` pc17. The cache is indexed by slot only (same `command_id + 1` as rows 21 and 27) and the stored value is the 0-based option id. (Coordinator correction 2026-10-04: the original text said `command_id + 1 + d` and "flattened slot+option"; `d` is not an operand of the `ADD`.) | written to the shared cache | **this is where a user choice enters the cache that row 15 later persists** |
| 33 | special / `main.p5` | pc0-4 | `update_text` → calls `update_list_text` then `update_help_text` | est. | — | — |
| 34 | special / `main.p1` | pc0-12 | `virtual_input:set_enable(true)`, `selector:set_focus(true)` | est. | — | — |

Rows 12, 15, 19, 23, 27, 29 and 32 are the ones that matter for a mod: they are the only
places in this chunk where a value crosses into or out of native code.

## 5. End-to-end flow for `command_id == 1`

```
p14 pc8-18    for i = 1..N:  cache[i]  = invoke("get_skill_id",  i-1)   -> cache[1]
p14 pc34-44   (after the state loop)  invoke("set_skill_id", i-1, cache[i])   -- see caveat
p2  pc13-50   for i = 1..N:  part = get_parts("set_special_item_00")        <- i-1 = 0
                        play_animation("category_00", 1.0)
                        title pane text = titles[1]            <- i = 1, NOT 0
p15 pc58-72   for i = 0..N-1: setup_button("set_special_item_00")
p15 pc94-108  for j = 0..M-1: setup_button("set_item_00")                  (sub selector)
p8  pc64-96   decided_id = get_decided_button_id()   -> 0 means the first button
p10 pc0-5     command_id = 0 ;  skill_id = cache[0 + 1] = cache[1]
p10 pc16-59   for j = 1..M:  get_skill_name_label(0, j-1)   -> the M option labels
p13 pc11-17   d = get_decided_button_id() ;  cache[0 + 1] = d      (corrected, see row 32)
p4  pc15-49   invoke("get_skill_name_label", 0, cache[0+1]) ; invoke("replace_skill", 0, skill)
```

**Caveat that must not be glossed:** row 15's write-back loop runs *after* row 14's state
loop, i.e. the `set_skill_id` batch happens when the state machine returns, not
immediately on each pick. The cache written by row 32 is what row 15 then flushes. I have
**not** established that ordering as correct at runtime — it is what the bytecode says the
control flow is, and the `coroutine.yield()` at pc27 makes the actual interleaving
unresolved (edge 1).

## 6. Base vs patched editor, only where needed

The special actor has **no** patched counterpart: `script_patch/` contains only
`make_mii_edit_actor.lc`. So the base/patch comparison applies only to the editor's
skills selector, and only one thing about it matters here.

Confirmed independently in this task, from `xref` and the disassembly:

- `IS_SKILL_EDITABLE`: **0 occurrences in the base, exactly 4 in the patch**, at
  `main.p5` pc193, `main.p6` pc115, `main.p10` pc26, `main.p11` pc153 — each read by one
  `GETTABUP` with `B` = an upvalue holding `_ENV`, each immediately followed by a
  `TEST`/`JMP` pair.
- `IS_READ_ONLY`: **5 occurrences and 5 uses in both chunks, unchanged.** The patch reads
  it *first* at every site and only then consults `IS_SKILL_EDITABLE`.
- At `main.p11` pc153-160 (patch) the pattern is: read `IS_SKILL_EDITABLE`; if set,
  `selector0:set_selectable(up[5], true)`, then `select_button(...)`; the base falls
  straight through to `set_enable(false)`.

Reading: the shipped patch makes the skills selector *selectable and focusable* when the
host sets `IS_SKILL_EDITABLE`, and disabled otherwise, with read-only still winning. That
is the game acknowledging that skills are editable — and it is **exactly the hook a mod
would want to set**. It is also a host-provided runtime flag, so a mod cannot simply
assign it from Lua without knowing who owns it (P1-UI-GLOBALS established only that these
three chunks do not define it).

`btn_other_try` (the try/preview button) exists at `main.p11` pc138 and pc199 in both
chunks, wired into `selector1` as a button and hidden when `FROM_AMIIBO`. **No
`make_mii_special` string exists in either editor chunk**, so the editor does not name the
special-move scene; how the special screen is entered is **not** established (edge 3).

## 7. The class check: absent, and that is a measured result

There is **no Mii class test anywhere in this flow.** A byte-level search of all three
chunks for `MII_TYPE`, `GUNNER`, `BRAWLER`, `SWORD`, `_CLASS`:

- `make_mii_special_actor.lc`: **no match at all.** Not one of those byte sequences occurs
  in the file.
- both `make_mii_edit_actor.lc`: `MII_TYPE` occurs only inside the single token
  `EDIT_MII_TYPE` (2 occurrences each, at `main.p11` pc189/202 and `main.p16` pc31/41),
  which is a **camera** enum — it is compared against `MAKE_MII_CAMERA_DEFAULT`,
  `MAKE_MII_CAMERA_RIGHT_SIDE_0/1`, `MAKE_MII_CAMERA_HEAD` and passed to
  `set_defines_camera` / `set_right_side_*_fighter_camera`. It has nothing to do with
  Mii class.

So the special selector is **not** class-gated in Lua. Whether the *native* side refuses
Gunner-only options, or gates the whole screen, is unresolved. This matters directly for
the mod: a Gunner-only restriction cannot be implemented by copying a Lua branch, because
there is no branch to copy. Any Gunner gating will have to come from a new capability.

## 8. Proposed entry point, and the exact missing capability

**Proposed entry point (smallest one that exists today):** row 27-29 plus row 32 in
`make_mii_special_actor.lc` — `main.p10` (`state_setup`) and `main.p13`
(`state_update`, sub). Concretely, the two facts a mod would build on are:

1. `cache` (the `up[3]`/`up[2]` table) is the **single in-memory map from direction →
   chosen option**, indexed `direction + 1` for both the write (row 32, corrected) and
   the reads (rows 21, 27). The value is used by Lua as a 0-based option index:
   `main.p11` pc4-15 does `list_parts[skill_id + 1]` and `selector:select_button(skill_id)`.
   So what `get_skill_id` returns must be usable as an option index below
   `SPECIAL_SKILL_NUM` (B for the Lua usage; what native code maps it to is still open).
2. The **only** exit to native is `set_skill_id(native_index, value)` (row 15), and the
   only entry is `get_skill_id(native_index)` (row 12).

That is a genuine, minimal seam: everything else in the screen is layout plumbing.

**The exact missing capability.** To add one selector/stat screen you would need **all
four** of these; the first is the hard blocker and the current tool cannot do it:

| capability | status | evidence |
|---|---|---|
| **Lua instruction editing / compiler** | **MISSING — the blocker.** `set_string_constant` refuses any non-string constant, cannot insert or delete a constant, cannot change an instruction word, cannot move a prototype. `LOADK Bx` and RK operands index the constant table *positionally*, so insertion would silently invalidate every later reference. | `tools/lua53-inspect/README.md` "Limits"; P1-LUA-WRITE §6 |
| **native binding** | **MISSING.** `get_skill_id`/`set_skill_id`/`replace_skill`/`get_skill_name_label` are string names handed to `UiScriptPlayer.invoke`. No trace establishes the registry, the signature, or whether an unknown name is ignored, errors, or crashes. | rows 12/15/19/23/30 |
| **persistence** | **MISSING.** Row 15's return value is discarded and nothing in these chunks says where the values land. P1-ID-REVIEW's saved-record trace stops at native offsets and never reaches this call. | rows 15, 32; P1-ID-REVIEW §3 |
| **layout** | **PARTIAL, and owned by another task.** The screen needs parts named `set_special_item_%02d`, `set_item_%02d`, `category_%02d`, `selector_0`. A new selector needs matching parts; `SKILL_COMMAND_NUM` and `SPECIAL_SKILL_NUM` are read from globals and their values are unknown, so the required part count is unknown. | rows 6, 8, 16 |

So: **layout** is a packaging problem another task is on; **instruction editing**,
**native binding** and **persistence** are all genuinely missing, and the last three
cannot be closed offline from these three files.

## 9. Is there a safe visible diagnostic? Yes — with one caveat

**Yes, and I measured it rather than assuming it.** `mnu_mmiif_setup_sp_move_title` at
`main.p14 K[2]` (pc2, `LOADK`, byte `0x17b2`) is a good candidate:

- It is a **display** string, not a bridge name, selector name, state name or layout part
  name. Its only consumer is the single `LOADK` at pc2, which feeds
  `ComFrameActor:set_sub_title(...)` at pc0-3. Rewriting it cannot change which part the
  screen addresses, cannot change control flow, and cannot change a `printf`-style format
  (the three `%02d` templates in this chunk are layout part-name formats and are
  explicitly *not* touched).
- `setconst` **refuses it by default** (exit 1, "read by 1 instruction"), which is the
  guard working. With `--allow-used` and an **exactly 29-character** replacement
  (`MCUZ_DIAGNOSTIC_TITLE_XXXXXXX`), the result is measurably surgical:

| check | result |
|---|---|
| file size | 7799 → **7799 bytes** (unchanged) |
| differing byte offsets | **28**, contiguous, `0x17b4`–`0x17d0` (inside the one string) |
| `compare` structural diff | **exactly 1**: `main.p14.K[2]` value |
| `verify` | exit 0 |
| `roundtrip` | byte-identical, `sha256 61068c40…`, no reparse diff |

Two earlier attempts at 26/27/28 characters **did** change the file size (7799 → 7797/7798)
and shifted every later offset. They still passed `verify` and `compare`, which is exactly
why "one structural difference" is not sufficient evidence on its own — **same length
must be checked separately.** Evidence: `probe_samelen*.txt`.

**The caveat:** a same-length rewrite proves the *encoding* and that the edit is
localised. It proves **nothing** about whether the game loads a modified chunk. The
editor may not even open. Only a console run settles that, and per the mod rules I
performed none. So the honest statement is: *a safe visible diagnostic exists offline; its
runtime effect is untested.*

I wrote the probe only to `gamedata/mii_customizer/P2-UI-FLOW/` (game-derived output goes
to `gamedata/`), produced **no install candidate**, and left `builds/` untouched.

## 10. Unresolved edges (explicit, not filled in)

1. **The `coroutine.yield()` interleaving in `main.p14` pc25-33.** Whether `set_skill_id`
   (row 15) flushes before or after the user's pick is consumed is not established. The
   apparent ordering in section 5 is what the control flow says, not an observed one.
2. **The 4-entry title table vs `SKILL_COMMAND_NUM`.** If `SKILL_COMMAND_NUM > 4`,
   `main.p2` pc38 indexes past the table. Unknown until the count's value is known.
3. **How the special screen is entered.** `make_mii_special` appears in **no** chunk I
   read; `btn_other_try` is wired but nothing here names the destination.
4. **What `get_skill_id` returns** — a skill id, an index, a save id? — and whether
   `replace_skill` is a live preview apply. Both are native and both gate the whole design.
5. **`SKILL_COMMAND_NUM` / `SPECIAL_SKILL_NUM` values.** Still unresolved (P1-UI-GLOBALS
   excluded only three modules as their definition site); this task did not chase them,
   per the prompt.

## 11. Evidence tiers

| tier | claim |
|---|---|
| **B** verified offline | input hashes unchanged; `verify` exit 0 with exact byte consumption on all three; independent second parser reproducing header length, proto/instruction/constant counts on all three; every PC, offset, constant index and operand cited above; the four-index distinction (rows 12/15/19/23/27/29/32); `IS_SKILL_EDITABLE` 0→4 sites with `IS_READ_ONLY` unchanged at 5/5; absence of any Mii class token from the special chunk and `EDIT_MII_TYPE` being a camera enum; the same-length display-string rewrite (size, 28 contiguous differing bytes, 1 structural diff, `verify`/`roundtrip` exit 0); the `xref` iAsBx false-positive counts |
| **C** pinned source | Lua 5.3 chunk layout and iABC field positions (`lua/lua` v5.3.6: `lundump.c`, `ldump.c`, `lopcodes.h`, `lopcodes.c`, `lobject.h`) — as cross-checked against the bytes, not merely recalled |
| **A** console | **none.** No run was performed. Nothing here is evidence about runtime behaviour, and the display-string diagnostic is untested at runtime. |
| **D** interpretation | that `replace_skill` is a live preview apply; that `IS_SKILL_EDITABLE` is the game's own "skills may be edited" gate (mechanism is tier B, purpose is D); that the title strings are message keys rather than part names; the runtime ordering in section 5 |

## 12. Commands run, with exit codes

All from the workspace root. `python` is CPython 3.12.3; `python3` is the Windows Store stub
and fails (exit 49), so `python -B` was used throughout.

| command | exit | result |
|---|---|---|
| `lua53_inspect.py verify B S P` | 0 | all pass, exact consumption on all three |
| `lua53_inspect.py header/summary/dis/constants B S P` | 0 | 6 evidence files |
| `lua53_inspect.py protos B S` | 0 | upvalue descriptor tables |
| `lua53_inspect.py xref S SKILL_COMMAND_NUM …` | 0 | counts in `xref_special_counts.txt` |
| `lua53_inspect.py xref B/P EDIT_MII_TYPE btn_other_try …` | **1** | expected: names with 0 occurrences make `xref` exit 1 |
| `decode_check.py S B P` | 0 | independent walk agrees on all three chunks |
| `xref_false_positives.py` | 0 | 33 / 139 / 146 bogus `RK.B` rows |
| `setconst S out main.p14 2 …` (no override) | **1** | refused: constant is read — the guard working |
| `setconst --allow-used S out main.p14 2 <29 chars>` | 0 | 7799 → 7799 bytes |
| `lua53_inspect.py compare S out` | 0 | exactly 1 structural difference |
| `lua53_inspect.py verify / roundtrip out` | 0 / 0 | clean / byte-identical |
| `sha256sum` on all three inputs, after all writes | 0 | **all three unchanged** |

## 13. Changed files

Inside this task's exclusive write paths only:

- `research/P2-UI-FLOW.md` — this report
- `evidence/P2-UI-FLOW/` — `input_hashes.txt`, `verify_three_chunks.txt`,
  `header_three_chunks.txt`, `summary_three_chunks.txt`, `summary_special.txt`,
  `protos_special.txt`, `protos_edit_base.txt`, `constants_special.txt`,
  `constants_edit_base.txt`, `constants_edit_patch.txt`, `dis_special_actor.txt`,
  `dis_edit_base.txt`, `dis_edit_patch.txt`, `xref_special_counts.txt`,
  `xref_edit_base_flags.txt`, `xref_edit_patch_flags.txt`,
  `xref_edit_base_selectors.txt`, `xref_display_strings.txt`,
  `xref_false_positives.txt`, `independent_decode.txt`, `cited_windows_special.txt`,
  `cited_windows_edit_base_vs_patch.txt`, `probe_samelen*.txt`
- `scratch/2026-10-04_P2-UI-FLOW/` — `decode_check.py`,
  `xref_false_positives.py`, `field_layout_probe.py`

Derived game files, workspace `gamedata/mii_customizer/P2-UI-FLOW/` only:
`probe_display.lc`, `probe_display_samelen.lc`.

Untouched: `STATUS.md`, `CHANGELOG.md`, `CURRENT_INSTALL.md`, `prompts/`, `phases/`,
`builds/`, all `research/P1-*`, `tools/lua53-inspect/` (including the `xref` defect — not
mine to edit), other workers' `P2-*` paths, `mods/ssbu_mod_new/`, workspace `tools/`, the
`dump/`, the original chunks, any save, SD card or emulator state. No commits, no
branches, no installs, no production UI change.

**I did not edit the inspector**, so the `xref` `iAsBx` defect in §2.1 is reported, not
fixed. It should be handed to the tool's owner.

## 14. Next experiment (one, concrete)

**Add the instruction-editing capability to `lua53-inspect` — a `setint`/`patchword`
mutator plus a `LOADK Bx` and RK operand fixup pass — and prove it by taking the
synthetic chunk from P1-LUA-WRITE and inserting a constant that an existing `LOADK` then
consumes, with `verify`, `compare` and `roundtrip` all clean.**

That is the smallest thing that unblocks a real selector addition, and it is fully
offline and testable. It does **not** by itself produce a working mod: `get_skill_id`'s
return meaning, the `invoke` registry and persistence all remain native unknowns, and per
P1-LUA-WRITE §11 the first hardware gate is still a single same-length constant rewrite
run on console. If the coordinator would rather spend the gate now, the §8 display-string
probe is packaged and ready, but it must ship with a vanilla control.

## Task summary

**P2-UI-FLOW: DONE** — 34-row call-flow table over the special actor. Six prototypes get
detailed multi-row treatment, within the prompt's budget of eight: `main.p15` (7 rows),
`main.p14` (6), `main.p4` (4), `main.p10` (4), `main.p2` (3), `main.p8` (2). Six more are
covered by one row each as pass-overs, named so they are not mistaken for untraced:
`main.p1`, `p3`, `p5`, `p6`, `p11`, `p13` — of which `main.p13` is the one that matters,
because row 32 is the `cache[command_id+1+d] = d` write-back. Two editor prototypes
(`main.p11`, `p16`) are cited only for the patch comparison and the class check. Four of
the special actor's 16 prototypes are **not in the table at all** and are therefore
untraced edge cases, not oversights: `main.p0` (a single `RETURN`), `main.p7`
(`state_out`, a thin `play_animation_and_wait("out")` wrapper mirroring `main.p6`),
`main.p9` (the sub-window's pane cache: the `SPECIAL_SKILL_NUM` loop at pc10-45 fills `list_parts`/`list_number_pane`/`list_name_pane`/`list_help_pane` from `set_item_%02d`, `set_txt_num`, `set_txt_val`, `set_txt_desc` — same shape as `main.p2` pc13-50 but with **no** `play_animation` call),
and `main.p12` (sub `state_out`, mirroring `main.p11`). The four indices kept distinct with
the two offset conventions proven from both directions; get/set skill id traced end to
end with argument provenance; no Mii class check exists in Lua (measured); proposed entry
point = the `cache` table plus the `set_skill_id` call; the exact missing capabilities
listed (instruction editing is the blocker, plus native binding and persistence);
a safe visible diagnostic **exists** and was built and verified offline, with the
same-length caveat and the runtime caveat both stated.

Changed files, commands and observed exit codes are in §12 and §13 and are persisted
above, so the coordinator only needs to be told the task is finished.

### Two corrections to earlier reports, made here and not edited in place

1. **P1-UI-DECODE §2 "the loop at pc11 iterates 1..SKILL_COMMAND_NUM, calling
   `get_skill_id` once per command slot and storing results into a table keyed by the
   loop variable"** — correct, and this task adds the detail it lacked: the value passed
   to native is `i - 1`, so the **cache is 1-based while the native index is 0-based**.
   Read back at `main.p4` pc9-10 and `main.p10` pc3-4 as `id + 1`. Anyone reasoning about
   slot indices from the cache must apply the offset.
2. **P1-UI-DECODE §2 "the loop at pc11 … `SKILL_COMMAND_NUM`"** is quoted in three
   reports as if the count were per-*class*. Nothing in these chunks supports that: there
   is no class read at all (§7). The count is read once from a global and used as both a
   loop bound and a validity ceiling (`main.p4` pc5-6). Whether it is per-class is
   **unverified**, and the mod must not assume it is.
