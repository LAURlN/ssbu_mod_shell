# P11-ROW-TEXT - literal text on a native list row, and labels for the menu (facts only)

Task ID: P11-ROW-TEXT. Status: DONE (final section).
Mode: offline static analysis; nothing executed or patched. Disassembly and file reads only.
Evidence tier: B for everything the check script re-reads; runtime behaviour marked D.

## Input

- Workspace `gamedata/ssbu-13.0.4/main.bin` (flat image; address == file offset),
  86,672,752 bytes, sha256 `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`
  (verified at run time by `check_p11_row_text.py`).
- Disassembler: `PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python
  mods/mii_customizer/scratch/2026-10-04_P1-ID-REVIEW/d.py win <addr> <n>` (workspace root).
- Extracted default-region message files: workspace
  `gamedata/mii_customizer/P11-ROW-TEXT/ui/message/` (13 msbt, from `tools/arc-extract` +
  `mods/ssbu_mod_new/dumps/decoded/arc_files.tsv`).

## Read first (as instructed)

- `research/P9-HAT-HANDLES.md` §2 (row filler call order, steps 17-19e)
- `research/P8-HAT-NATIVE.md` §6 (row drawing, message-key struct)
- `research/P5-UI-API.md` §7 (text methods, incl. `set_text_string`)
- `research/P10-HAT-OPEN.md` Q5 (row-callback vtables, visible-window fill)
- `research/P5-MSG-PROBE.md` (message files / loader, added labels)
- `research/P1-ID-REVIEW.md` §2.3, `research/P4-BRIDGE-FACTS.md` (bridge-name registration)
- `research/P6-HAT-UI.md` §4.6 (Lua decide side)

## Short answers

**Q1.** `0x3776360(x0 = row layout node, x1 = pane-name C string, x8 = out)` returns through
`x8` a wrapper `{vtable 0x523c9a8, holder*}`; the holder (fresh 0x20-byte alloc) holds
`{found pane, typedA, typedB, typedC}` (pane = layout child lookup keyed on the pane-name
hash; the three typed results come from `0x3772920 / 0x3772a30 / 0x3772b40`). The "part"
both text functions use is `holder+0x10` (the `0x3772a30` result), reached as
`[[wrapper+8]+0x10]`. `0x3779b70(x0 = wrapper, x1 = message key's text field)` copies the
label text (<= 63 bytes), rebuilds `{hash,len}` locally (seed `0x811c9dc5`, per byte
`h = h*0x89 ^ c`; this local hash is never read afterwards - the key struct's u32 hash is
**not** what the lookup uses), then calls **`0x37a3ea0(x0 = manager = *[[0x593ac60]],
x1 = label text)`**. That function walks **every node of the tree at `[mgr+0x18]`**
(in-order; end sentinel `[mgr+0x20]`) calling `0x440(node+0x88, label)`, then the **flat
vector at `[mgr+0]/[mgr+8]`, stride 0x70**: for each entry whose 3 bytes at `+0x68..+0x6a`
equal `label[0..2]` it calls `0x440(entry+0x60, label)`. `0x440` is the per-table label
lookup (group index `[t+0x20]`, bucket array `[t+0x18]`, hash call `0x7c0`, byte compare;
returns 0 on miss). The manager is the object the loader `0x1977420` fills from **all 13
`ui/message/msg_*.msbt`** (system, common, popup, name, melee, menu, spirits, campaign,
bgm, staff, tips, script, title - name table `0x5184f40`, loop `add x23,x23,#0x10; cmp
x23,#0xd0`), reading the same global `[0x593ac60]` the lookup reads. So the answer is
**every loaded msbt table held by that manager, searched by label text - not one file, and
not by the key struct's u32 hash.** Hit -> pointer to the entry's UTF-16 text -> `0x37adbc0`
expands it (0x000e/0x000f substitution blocks, cap 0x800 units) -> `0x37a1cc0(pane, ...)`
applies it. Miss -> static sentinel `0x4752ea0`, whose first UTF-16 unit is `0x0000` ->
`0x37adbc0` takes the early path `0x37adff4` (`mov w22,wzr`, NUL at `dest[0]`, returns 0)
-> `0x37a1cc0` sets **the empty string: the row label shows blank.** No error, no fallback
text (whether an empty pane is visually blank is D).

**Q2.** Registration of `set_text_string`: name string at `0x439a8b9`; RELA record
`0x3ea70e0 {slot 0x51833e0, info 0x403, addend 0x439a8b9}`, handler slot `0x51833e8`, RELA
record `0x3ea70f8 {slot 0x51833e8, addend 0x335a490}` - inside the **`MetatableLayoutPane`**
method table `0x5183260` (`mov w2,#0x290` = 0x290 bytes, name string `0x43ccac2`,
registered by `bl 0x38f6cb0` at `0x3370e4c`, enclosing function starts `0x3370b20`).
Neighbors: `set_text_message` name `0x51833b0` -> handler `0x51833b8 -> 0x335a100`;
`set_text_message_args` `0x51833c0 -> 0x42e4844`, handler `0x51833c8 -> 0x335a1e0`;
`set_text_string_16` handler `0x51833f8 -> 0x335a570`; `clear_text_string` handler
`0x5183408 -> 0x335a620`.

Handler `0x335a490(x0 = lua_State*)`: reads the top-of-stack Lua string (type tag
`[top-0x18] & 0xf`: 2 = inline string, pointer at `top-0x20`; 7 = interned string,
`ptr+0x28`; else NULL), pops the arguments, then `x0 = [[ud+8]+0x10]` (`0x335a54c..0x335a554`)
and `x1 = UTF-8, NUL-terminated, no length argument` -> `bl 0x37a22f0` at `0x335a558`;
returns 0.

`0x37a22f0(x0 = inner text-pane, x1 = UTF-8 C string)`: strlen loop `0x37a2320..0x37a2334`,
UTF-8 -> UTF-16 conversion on its own stack (1-, 2-, 3-byte sequences; cap `cmp x2,#0x7fe`
at `0x37a23a0`), NUL-terminates, then **`mov w3,#1` (`0x37a23d4`) / `bl 0x37a1cc0` at
`0x37a23dc`**. `0x37a1cc0(x0 = pane, x1 = UTF-16, w2 = unit length, w3 = flags)` is the
function that finally commits literal text on the pane (change -> vtable `+0xe8`, then
`+0x110`; details in evidence 06/06b).

First four words, PC-relative check (adrp = `0x90000000` mask, b/bl = `0x14/0x94` mask):

| entry | words | PC-relative? |
|---|---|---|
| `0x335a490` | `f81d0ff5 a9014ff4 a9027bfd 910083fd` (`str x21,[sp,#-0x30]!; stp x20,x19,[sp,#0x10]; stp x29,x30,[sp,#0x20]; add x29,sp,#0x20`) | none |
| `0x37a22f0` | `f81d0ffc a9014ff4 a9027bfd 910083fd` (`str x28,[sp,#-0x30]!; ...`) | none |
| `0x37a1cc0` | `a9bd57fc a9014ff4 a9027bfd 910083fd` (`stp x28,x21,[sp,#-0x30]!; ...`) | none |
| `0x3779b70` (for reference) | `f81c0ffc a90157f6 a9024ff4 a9037bfd` (`str x28,[sp,#-0x40]!; stp x22,x21; stp x20,x19; stp x29,x30`) | none |
| `0x3776360` (for reference) | `d10603ff a9145ffc a91557f6 a9164ff4` (`sub sp,sp,#0x180; stp x28,x23; stp x22,x21; stp x20,x19`) | none |

**Can `0x37a22f0` be called with what the row filler has at `0x19ccc00..0x19ccc48`? YES.**
Objects: `0x3779b70` takes the *wrapper* (`x0`, at `sp+8` in the filler) and derives its
pane via `ldr x9,[x0,#8]; ldr x9,[x9,#0x10]` (`0x3779ba8/0x3779bac`) = `[[wrapper+8]+0x10]`.
The Lua handler derives the *same* pane from its userdata: `ldr x8,[ud,#8]; ldr x0,[x8,#0x10]`
(`0x335a54c/0x335a550`). At `0x19ccc00..0x19ccc48` the wrapper sits at `sp+8`
(`[sp+8] = vtable 0x523c9a8`, `[sp+0x10] = holder*`, written by `0x3776360` at
`0x3776458/0x37764b0`), so `0x37a22f0`'s `x0` is obtained with exactly two loads from the
state the filler already has:

```
ldr x8, [sp, #0x10]      ; holder = [wrapper+8]
ldr x0, [x8, #0x10]      ; pane = [holder+0x10]  (cbz -> skip, as at 0x335a554)
; x1 = pointer to a NUL-terminated UTF-8 literal
bl 0x37a22f0
```

That is the same object `0x3779b70` hands to `0x37a1cc0` at `0x3779ca8`, so a literal set
this way and the message-key text land on one and the same pane.

**Q3. YES - the same row is filled again, so text set outside a fill is overwritten and
must be set on every fill.** The row filler runs as callback slot `+0x10` through the thunk
`0x19cd010` (`sub x0,x0,#0x48; b 0x19ccb20`; secondary vtable base `0x50a6b38`, slot
`0x50a6b48`, RELA `0x3cf4938`; the primary table's slot `+0x38` at `0x50a6b18` -> `0x19ccb20`
directly, RELA `0x3cf48d8`). Call sites of slot `+0x10`: the scroller visible-row loop
(`ldr x8,[x8,#0x10]; blr x8` at `0x377c76c/0x377c770`) and the two model blocks of the
frame callback `0x19cc3f0` (`blr` at `0x19cc5dc` and `0x19cc7e4`). That path re-runs when:

- **scroll** changes the first visible row: `str w20,[scroller+0x29c]` at `0x377db50` then
  `bl 0x377c6d0` at `0x377db54` (the redraw entry whose loop contains `0x377c76c`);
- Lua **`redraw_all_items`** (`0x33630f0`) calls `bl 0x377c6d0` at `0x3363140` (P6-HAT-UI:
  `update_sub_list_window` redraws after every `sort_id_list`);
- the frame callback's model blocks run whenever `[S+0x169] != 0` (gate
  `ldrb w8,[x19,#0x169]; cbz` at `0x19cc52c/0x19cc530`), the flag is cleared inside
  (`strb wzr` at `0x19cc554`/`0x19cc75c`), the ownership test `bl 0x328b5d0` at
  `0x19cc548` passes, and the block then loops `[scroller+0x2c4]` visible rows calling
  slot `+0x10`.

Each fill re-executes `0x3779b70` with the message key (`0x19ccc10`/`0x19ccc48`), which
overwrites whatever the panes show. Consequence for P11-MENU: literal text set **outside**
the fill survives only until the next fill of that row; it must be (re)set on every fill
(i.e. from inside the fill path, after `0x3779b70`).

**Q4. Fallback labels** - default-language (region `us_en`) extraction, all 13 files.
Full listing with CLOSE matches: `evidence/P11-ROW-TEXT/25_q4_label_scan.txt`.
Exact text matches (raw TXT2 repr shows a trailing `\x00` only - one label,
`pop_opt_btn_key_noassign_grab`, carries a trailing space `"Grab \x00"`; no control codes
in any of them):

| wanted | file | label | exact text |
|---|---|---|---|
| Stats | msg_menu | `mnu_coll_record_top_count`, `mnu_record_count_title` | `Stats` |
| Grab | msg_common | `cmn_hold` | `Grab` |
| Grab | msg_menu | `mnu_opt_btn_key_hold`, `mnu_spirits_select_refine_sort_03` | `Grab` |
| Grab | msg_popup | `pop_opt_btn_key_noassign_grab` | `Grab` |
| Grab | msg_tips | `tip_title_0995` | `Grab` |
| Neutral Special | msg_melee | `mel_training_cp_attack` | `Neutral Special` |
| Neutral Special | msg_menu | `mnu_mmiif_setup_sp_move_normal` | `Neutral Special` |
| Side Special | msg_menu | `mnu_mmiif_setup_sp_move_width` | `Side Special` |
| Up Special | msg_menu | `mnu_mmiif_setup_sp_move_up` | `Up Special` |
| Down Special | msg_menu | `mnu_mmiif_setup_sp_move_btm` | `Down Special` |
| Default | msg_menu | `mnu_opt_btn_ctrl_init` | `Default` |
| None | msg_melee | `mel_chara_select_spirits_none_short`, `mel_chara_select_without`, `mel_rule_item_freq_00`, `mel_training_shift0` | `None` |
| None | msg_menu | `mnu_controller_assign_none`, `mnu_opt_melee_radar_00`, `mnu_replay_movie_edit_cap_bg_none`, `mnu_replay_movie_edit_trs_type_none`, `mnu_shop_buy_slot_none`, `mnu_spirits_itemview_none` | `None` |

**Wanted texts with no exact label (18):** Jab, Dash Attack, Forward Tilt, Up Tilt,
Down Tilt, Forward Smash, Up Smash, Down Smash, Neutral Air, Forward Air, Back Air,
Up Air, Down Air, Pummel, Forward Throw, Back Throw, Up Throw, Down Throw. `Forward Smash`
has not even a CLOSE hit anywhere in the 13 files.

Closest existing texts (all contain the phrase; none is a bare row label):

- Dash Attack -> `nam_spirits_skill_dash_attack_offense_up` (msg_name) = `Dash Attack ▲`
  (raw `Dash Attack \ue092`) - carries a stat-up icon code.
- Forward/Up/Down Tilt -> only inside longer texts, e.g. `tip_title_2002` (msg_tips) =
  `Terry: Burning Knuckle (Forward Tilt Special)`; `nam_technique_explain_*` sentences.
  The bare word exists: `cam_info_tilt` (msg_campaign) and `mel_pause_roll_txt`
  (msg_melee) = `Tilt`.
- Up/Down Smash -> sentences only (`nam_spirits_hint_personal_smash_hi` etc.).
- Airs -> sentences (`nam_spirits_hint_personal_air_attack_*` = `• The enemy favors ... air
  attacks`); result-stat nouns exist: `mel_result_item_20` = `Air Attacks`.
- Jab / Pummel / throws -> sentences only (`tip_title_0250` = `Donkey Kong: Forward Throw
  Info`, `mel_result_item_23` = `Throws`).
- Useful neighbors not asked for: `mnu_opt_btn_key_smash`/`mnu_opt_btn_key_oth_smash`
  (msg_menu) = `Smash Attack`; `mel_training_cp_smash_side` (msg_melee) = `Side Smash`;
  `mel_result_item_21` = `Smash Attacks`.

**Is each file one the Q1 lookup searches? Yes - all 13 are.** The loader `0x1977420`
formats `ui/message/msg_%s.msbt` (`0x439a9ae`) for the 13 names in table `0x5184f40`
(`system ... title`, verified through the RELA addends of each name pointer), builds 13
records (loop ends at `cmp x23,#0xd0`), and then walks the vector of the manager at the
same global `[0x593ac60]` the lookup reads (`0x1977624..` vs `0x3779c60..`). The
vector path of `0x37a3ea0` selects an entry by the label's own first 3 bytes, and every
label in each extracted file starts with its file's 3-char code (`bgm`x2696, `mnu`x3342,
`mel`x1337, ... - histogram in evidence 25), so each file's labels resolve through its own
entry; the tree path tries every table anyway.

**Q5. The greyed look and decide.** In the row filler's steps 17-19e (after the icon/cell
object is fetched from the row node by `0x3796970`, keyed on the row node's name hash, and
stored in the 8-byte cell allocated at `0x19ccce8`):

- `bl 0x328b5d0` at `0x19ccd84` tests the row handle against the registry at
  `registry+0x230`; it returns 1 for a handle **not** in the table (P9 correction).
- `tbz w0,#0 -> 0x19ccd94` (`0x19ccd88`): handle in table -> **normal branch**, cell
  vtable slot `+0x1f8` called with `w1 = 1` (`0x19ccda4..0x19ccdb0`).
- handle not in table **and** `ldrb w8,[S+0x169]; cbz -> 0x19cce2c`
  (`0x19ccd8c/0x19ccd90`): **greyed branch**, slot `+0x1f8` called with `w1 = 0`
  (`0x19cce3c..0x19cce44`).

Slot `+0x1f8` = `0x378a6c0`: `and w1,w1,#1; strb w1,[x0,#0x1c2]` (`0x378a6cc`) plus a
redraw-tail check. So **the unavailable look is the per-row cell/button byte `+0x1c2 = 0`**
(normal rows get `1`); getter slot `+0x200` = `0x378a6f0` (`ldrb w0,[x0,#0x1c2]`), slot
`+0x210` = `0x378a710` (`+0x1c3`). The pair sits at `0x523d000/0x523d008` - nine
button-class vtables share it, the first at base `0x523ce08` (`+0x1f8` RELA `0x4092758`,
`+0x200` RELA `0x4092770`). Both branches then call slot `+0x388` with a bit derived from
`+0x200`/`+0x210` and `w2 = 0` (`0x19ccde4..0x19ccdf0` / `0x19cce80..0x19cce8c`); what
that slot does visually is D. It is not a colour animation chosen by the filler. The two
text panes (`set_txt_val` at `0x19ccc00` and `set_txt_val_disable` at `0x19ccc3c`) both get
the same message-key text in steps 3-6; which of them is displayed when is not decided in
steps 17-19e (D - an animation elsewhere).

**Decide on such a row: refused, not redirected.** The decide gate reads the cursor row's
cell object (`x21 = [row+0x28]`), and requires both slot `+0x200` (`blr` at `0x377e284`,
`tbz -> 0x377e33c` at `0x377e288`) and slot `+0x210` (`0x377e298/0x377e29c`) to return 1.
A greyed row answers `+0x1c2 = 0` -> refused. Only the passing path stores the decision
`str w8,[scroller+0x2b0]` at `0x377e2a4`; the refusal path `0x377e33c` does at most one
virtual call on the optional object `[scroller+0x140]` (`cbnz -> 0x377d618`, slot `+0x30`
per P11-MENU) and joins the common tail `0x377d86c` **without storing anything**. Lua side
(P6-HAT-UI §4.6, corroborated by P11-MENU §5): `get_decided_item` returns the previous
stale value (`+0x2b4`); `if 0 <= decided_id then ... return else` falls through to the
shoulder/page branch - no error, no popup, no other row substituted. So: the decide press
on a greyed row decides nothing and nothing opens from it.

**Cursor movement** (`0x19ccea0` "row -> index", `0x19cd020` "slide"): both take
`(x0 = list object, w1 = row, w2 = fallback, w3 = step)` - the slide variant is called with
`this = S+0x48` (its vector `[x0+0xe0]` is the same `[S+0x128]`), as secondary slot `+0x28`
from `0x377ed00` (P10 Q5). Both call `bl 0x328b5d0` (`0x19cceec` / `0x19cd070`) and test
`[S+0x169]`; when the handle is not in the table and the flag is 0 they do **one**
`csel`: `row + step` if `step > 0`, else the caller's fallback
(`0x19ccf10..0x19ccf18`, `0x19cd084..0x19cd08c`) - one step, no loop over further
unlisted rows; otherwise the row index passes through unchanged. P11-MENU traced the
callers: the cursor skips a flagged row by one extra row moving one way and does not move
at all the other way. Helper `0x19cd0b0` returns 1 exactly for (first handle unlisted AND
`[S+0x169] == 0`) - the same condition the greyed branch uses
(`0x19cd0d8..0x19cd0f0`).

## Evidence files

`evidence/P11-ROW-TEXT/` (disassembly windows; all from the pinned image):

| file | contents |
|---|---|
| `01_set_text_0x3779b70.txt` | whole `0x3779b70`: key copy/hash, `0x37a3ea0` call at `0x3779c70`, `0x37adbc0` at `0x3779c9c`, `0x37a1cc0` at `0x3779cb0` |
| `02_find_part_0x3776360.txt` | whole `0x3776360`: wrapper write `0x3776458/0x37764b0`, child lookup `blr`, `0x3772920/a30/b40` fills |
| `03_row_filler_0x19ccb20_head.txt` | filler head: `bl 0x3288330` (`0x19ccbec`), both `set_txt_val*` finds + `0x3779b70` calls (`0x19ccc00..0x19ccc48`), `selected` find |
| `04_lookup_0x37a3ea0.txt` | full lookup: tree walk + vector prefix compare + sentinel `0x4752ea0` |
| `05_msg_0x37adbc0.txt` | UTF-16 expander; early `cbz x1`/`cbz w8` exits, substitution blocks |
| `06_apply_0x37a1cc0.txt`, `06b_apply_tail_0x37a1e50.txt` | final literal-text setter |
| `07/08/09_part_0x3772920/0x3772a30/0x3772b40.txt` | typed sub-object getters |
| `10_set_text_string_0x335a490.txt` | Lua handler (arg decode, `bl 0x37a22f0` at `0x335a558`) |
| `11_set_text_message_0x335a100.txt` | sibling handler -> `bl 0x3779b70` |
| `12_setstr_0x37a22f0.txt` | UTF-8 -> UTF-16 -> `0x37a1cc0` |
| `13_row_filler_greyed_0x19ccd70.txt` | registry test + normal branch (`w1 = 1`) |
| `13b_row_filler_greyed_branch_0x19cce2c.txt` | greyed branch (`w1 = 0`), `+0x388` call |
| `14_slide_0x19cd020.txt` | slide helper incl. `csel` at `0x19cd08c` |
| `15_row_filler_cell_0x19ccce8.txt` | cell alloc + icon fetch `0x3796970` |
| `16_row_to_index_0x19ccea0.txt` | row->index helper incl. `csel` at `0x19ccf18` and predicate tail |
| `17_icon_0x3796970.txt` | hash-keyed icon/cell lookup |
| `18_decide_0x377e200.txt` | decide gate: `+0x200`/`+0x210` tests, store at `0x377e2a4` |
| `19_scroll_step_0x377ec60.txt` | scroll step; slot `+0x28` call at `0x377ed08` |
| `20_decide_refused_0x377e33c.txt` | refusal path (no store) |
| `21_select_item_0x3783660.txt`, `22_apply_select_0x3781260.txt` | selection path (Q3 context) |
| `23_msg_load_0x19773c0.txt`, `24_msg_load_names_0x19774dc.txt` | msbt loader: format strings, 13-entry loop, manager vector walk |
| `25_q4_label_scan.txt` | Q4 scan: per-file label counts, 3-char prefix histogram, exact/close matches, missing list, short-vocabulary dump, raw TXT2 reprs of cited labels |
| `26_msg_name_table_0x5184f40.txt` | 13 entries: 3-char tag + relocated name (`system ... title`) |
| `27_frame_fill_0x19cc530.txt` | frame-callback model blocks: `[S+0x169]` gate, `0x328b5d0`, flag clear, loops, slot `+0x10` calls |
| `28_scroll_redraw_0x377db48.txt` | `str [+0x29c]` + `bl 0x377c6d0` |
| `29_redraw_all_0x33630f0.txt` | Lua `redraw_all_items` -> `bl 0x377c6d0` |
| `30_scroller_row_loop_0x377c714.txt` | visible-row loop, slot `+0x10` at `0x377c76c` |
| `31_lookup_hit_and_miss_tails.txt` | `0x440` success return (`0x568`: pointer = bucket base + index); `0x37adbc0` miss tail (returns 0) |
| `32_callback_vtable_slots.txt` | RELA slot map of the row-callback vtables + thunk `0x19cd010` |

## Check script

`evidence/P11-ROW-TEXT/check_p11_row_text.py` - stdlib-only, reads the pinned image and
the extracted msbt files. It verifies: image sha256; all 125 cited instruction words;
38 decoded branch targets (independently decoded from the words); the 20 cited entry
prologues are not PC-relative; the two `adrp` pages for global `[0x593ac60]`; the 16
cited RELA records (MetatableLayoutPane slots, row-callback vtables, button vtables) plus
the derived base `0x523ce08`; all cited strings incl. the 13 name-table strings; the
13-entry name table (tags + relocated name pointers); the sentinel's first UTF-16 unit;
sha256 of all 13 msbt files; per-file label counts; the 3-char-prefix property of every
label in all 13 files; every exact-match label's raw text; the 18 wanted texts with no
exact label and the 8 with one; and that `Forward Smash` appears nowhere. Negative
controls (`--neg`): 5 deliberate corruptions (sentinel unit, exact label, one instruction
word, one branch target, one relocation addend) must each print `MISMATCH` and the run
must exit 1. Exit 1 on any mismatch in the normal run, 0 otherwise.

Run (workspace root):

```
python mods/mii_customizer/evidence/P11-ROW-TEXT/check_p11_row_text.py
```

Output (both modes; the final post-edit rerun reproduced the green run line exactly):

```
$ python mods/mii_customizer/evidence/P11-ROW-TEXT/check_p11_row_text.py
check_p11_row_text: 340 checks run
PASS: all checks green

$ python mods/mii_customizer/evidence/P11-ROW-TEXT/check_p11_row_text.py --neg
check_p11_row_text: 343 checks run
MISMATCH: sentinel 0x4752ea0 first UTF-16 unit expected 0xffff got 0x0000
MISMATCH: msg_menu.msbt::mnu_record_count_title expected 'Jab\x00' got 'Stats\x00'
MISMATCH: NEG word at 0x378a6cc expected 0xdeadbeef got 0x39070801
MISMATCH: NEG branch at 0x19ccbec expected target 0x19ccb20 got 0x3288330
MISMATCH: NEG RELA 0x3ea70f8 addend expected 0x335a100 got 0x335a490
FAIL: 5 mismatches (negative controls detected, as expected)
```

## Limitations / open questions

- **D (console/emulator only):** what byte `cell+0x1c2 = 0` renders as; what slot `+0x388`
  and the `[scroller+0x140]` slot `+0x30` call do; whether an empty pane (`Q1` miss path)
  is visually blank; whether an *added* msg_menu label resolves on console (P5-MSG-PROBE
  territory - the lookup machinery itself does search all loaded tables, B).
- The manager's tree node set at `[mgr+0x18]` was not enumerated node by node; the walk
  structure (try every node's `+0x88` table) is verified, the identity of the nodes is not.
- The direction mapping in the two cursor helpers (which `csel` branch is "up") is
  P11-MENU's caller trace; my verified fact is the single-`csel`, one-step behaviour.
- `set_text_args` (`0x51833d8`) handler address not fetched; `clear_text_string`'s handler
  (`0x335a620`) not disassembled (out of scope).
- Where `[S+0x169]` is *set* (only its clear at `0x19cc554/0x19cc75c` and its tests were
  traced) is open.

## Final

- Task ID: **P11-ROW-TEXT**
- Status: **DONE**
- Changed files: `research/P11-ROW-TEXT.md`, `evidence/P11-ROW-TEXT/` (35 files incl.
  `check_p11_row_text.py`), `scratch/2026-10-06_P11-ROW-TEXT/` (`p11_scan.py`,
  `q4_labels.py`, `cited_words.txt`, `cited_words1.txt`), workspace
  `gamedata/mii_customizer/P11-ROW-TEXT/` (13 extracted msbt).
- Checks run: `check_p11_row_text.py` (340 checks, PASS) and `--neg` (5 deliberate
  corruptions detected, exit 1); Q4 scan ran to completion (exit 0). The green run was
  repeated after the final edit to this file with identical output.
- Open questions: see Limitations.
