# P11-MENU - plugin 0.5.0: customization menu with pages

Task: **P11-MENU** (Claude Opus 5.5), 2026-10-06. Status: **DONE (offline)** - see section 14
for exactly what that covers. Paths are relative to `mods/mii_customizer/` unless marked
workspace-relative. Image: workspace `gamedata/ssbu-13.0.4/main.bin`, sha256 `f70c97d2...`
(flat, address == file offset == hook offset).

Tiers: **A** console, **B** read from the image or measured offline in this task and
re-read by `evidence/P11-MENU/check_p11_menu.py`, **D** hypothesis. **Nothing of 0.5.0 has
run in the game: every statement about what the player sees is D.** What 0.4.0 showed on the
console (session 2, A) is named where the design leans on it.

> **Coordinator review, 2026-10-07.** Rerun from the workspace root: `check_p11_menu.py`
> 358/0 (exit 0), `--selftest` all 11 controls exit 1; host tests 47/0 and 35/0; NRO sha256
> equals the manifest. `editor.rs` read in full; the reader `0x180ce40..0x180cefc`, the pop
> `0x180adf4..0x180ae04`, the decide gate `0x377e278..0x377e2a8` / `0x377e33c` and the Lua
> text call `0x335a54c..0x335a558` disassembled by the coordinator and found as described.
> Not repeated: the build and the mutation control. Contract readings of section 2 accepted.
> `research/P11-ROW-TEXT.md` (independent) agrees on the text route, on text being set inside
> the fill (its Q3), and on the greyed/refused path. The session's `menu.txt` uses the
> catalogue slot ids, so the log shows `entry:normal_jab` where section 10 says `entry:jab`,
> and the character pages have 87 rows (`list.txt` without the Mii Gunner row), not 88; the
> adapted test plan is in `CURRENT_INSTALL.md`. The `slot` loadout key proposal is parked
> until the first move defines what a choice is.

## Progress log

| step | state | observed |
|---|---|---|
| 0. report skeleton | done | this file, written before anything else |
| 1. read 0.4.0 sources, P10 reports, P9 sections 3-5 | done | |
| 2. host tests owed from 0.4.0 | done | `scratch/2026-10-06_P11-MENU/run_host_test.sh` |
| 3. menu parser, page state machine, their tests | done | `plugin/src/menu.rs`, `plugin/src/ui.rs` |
| 4. native RE: page change, greyed row, row text | done (B) | sections 4-7; evidence windows `evidence/P11-MENU/d_*.txt`, `s_*.txt` |
| 5. hooks for pages | done | `plugin/src/editor.rs`, `plugin/src/lib.rs` |
| 6. check script | done | `evidence/P11-MENU/check_p11_menu.py` |
| 7. build 0.5.0, manifest, example | done | `builds/0.5.0-menu/` |
| 8. mutation control | done | `scratch/2026-10-06_P11-MENU/mutation_control.py` |
| 9. report | done | |

## 1. What the build does (design in one page)

Ways in A and B are unchanged (dispatcher hook: exit value 7 rewritten to 1, or value 1 with
ZL/ZR). A **visit** of mod mode now spans several **pages**, all shown on the native
headgear list exactly the way 0.4.0 showed its one list (own handle vector swapped in after
the headgear state's first tick, native list put back before its last tick):

| page | rows | A | B |
|---|---|---|---|
| **main** | one per `menu.txt` entry, in file order, literal text, no tick | opens that entry's page | leaves mod mode (edit menu), as cancel did in 0.4.0 |
| **entry, kind `stats`** | row 0 = `nam_chr1_00_miigunner` (default), then one per `list.txt` entry; all available; cursor and tick on the Mii's preset, else row 0 | sets the preset (row 0 clears) exactly as 0.4.0 (store, `save_loadouts`), then main page | main page, cursor on the entry |
| **entry, kind `slot`** | same rows; a row is available only when it is row 0 or its preset has an `allow` line for that entry; the others are greyed; cursor and tick on row 0 | available row: main page, **nothing stored**; greyed row: nothing happens | main page, cursor on the entry |
| **direct** (no usable `menu.txt`) | the 0.4.0 character list, row 0 = `nam_mii_hat_none_m` | as 0.4.0, leaves | leaves |

- **Page change (M3):** on the headgear state's last tick the original pops the state stack;
  when the visit goes on, the plugin puts the depth back (the slot still holds state 5) and
  raises the state reader's own "start the current state again" byte. The next frame the
  reader clears the frame counter and the headgear state runs its first tick again - the
  first tick 0.4.0 already used to open its list. The player sees the list close and open.
- **Greyed rows (M2):** the plugin's answer to "is this handle unlisted?" is 1 for an
  unavailable row, but only while the row filler asks. The row filler then disables the
  row's button, which is the game's own look for an unavailable item, and the scroller's
  decide code ignores a disabled button.
- **Row text (M5):** after the original row filler has filled a main-page row (with the
  entry's fallback label), the plugin puts the literal text on the row's two text panes
  through the pane lookup the row filler uses and the function Lua `set_text_string` calls.
- **E3 (M4):** unchanged mechanism, now per visit: snapshot when the first page opens;
  the headgear handle and the 0x200-byte working record are compared when every page closes
  (`mc|UI|page ... equal=1|record_equal=1`), and logged in full once per visit
  (`mc|UI|exit`). A further page opens only for a Mii that is exactly as the visit found it.
- **Hooks:** the five of 0.4.0 plus the row filler `0x19ccb20`. All or none, after 6 site and
  48 probe word compares; none with `ui_off`. New switch file `text_off`: hooks on, literal
  text off (rows show their fallback label).
- **Per frame:** one byte write and one read in the headgear-state hook, atomics in the
  others; no file IO, no allocation by the plugin. Per filled row with literal text: two
  pane lookups, each with the 0x20-byte holder allocation the game's own lookup makes and
  frees (rows are filled when they scroll into view, not every frame).

## 2. Contract readings and decisions the coordinator should know

1. **Text of an `entry` line** (G: "printable UTF-8"): accepted = 1..40 bytes, valid UTF-8,
   no C0/C1 control character, no DEL, **no character above U+FFFF**. Reason: the game's
   UTF-8 reader `0x37a22f0` decodes one-, two- and three-byte sequences only
   (`0x37a2348..0x37a238c`); a four-byte sequence would be shown as garbage. Rejected with
   `bad_text`.
2. **`#` comments:** a line whose first non-blank character is `#` is a comment; after the
   fields of a `label` / `allow` line a `#` starts a comment; **inside an `entry` line `#` is
   text** ("Jab #1" is possible). The text is trimmed of blanks at both ends.
3. **Order:** `label` / `allow` must come after their `entry` line (`unknown_id` otherwise).
   `allow` for the `stats` entry is rejected (`not_slot`): all its rows are available anyway.
   A second `label` for one entry is rejected (`dup_label`), the first stays.
4. **Fallback label of a main-page row:** the entry's `label`, else `nam_mii_hat_unknown`
   (what the game itself shows for a handle without a name). It is visible only if literal
   text fails or is switched off.
5. **Tick on the main page:** none. **Slot pages:** tick on row 0, because nothing is stored
   for a slot and the default is what is in effect.
6. **`dispatch` usable** when there is anything to show: list entries + menu entries != 0.
7. **Unavailable row reported as decided** (cannot happen through the button path, section
   5; possible in principle through the pointer path): nothing changes, the same page opens
   again with the cursor on that row (`action=refused_unavailable`). No popup, shop or dialog
   exists on any path the plugin adds.
8. **UI log cap** raised from 600 to 3000 lines per boot (a page change is 4-5 lines).
9. `builds/0.5.0-menu/example/menu.txt` has no `allow` line (one is shown commented out).

### Proposed loadout key for slots (not implemented, as instructed)

`mc_loadouts 3`, new key `slot`: `<id> slot <entry_id> <preset_name>`, for example
`0000f589 slot jab mario`. Absent = the default (Mii's own class). At load a line is rejected
when the entry id is not in the menu, the preset is unknown, or the entry has no `allow` line
for it (`not_allowed`), so a stale file can never select an unimplemented move. Keyed by the
entry **id** (not its row) so the menu can be reordered. Store: per ID one byte per menu
entry (48 x `preset + 1`). The slot page would then start cursor and tick on that row, and
row 0 would remove the line. Version 3 because a version 2 reader (0.3.0 / 0.4.0) rejects the
unknown key line by line, which would silently drop choices after a rollback.

## 3. Hooks

Hook = `A64HookFunction` on the function entry; the original runs through the trampoline
with all sixteen argument registers passed on. The first five instructions of each site are
position-independent (check section F). x8 is not an input of any of them.

| site | arguments (B) | not armed / no list open | list open |
|---|---|---|---|
| `0x180a030` dispatcher | `x0` = scene | drops whatever was pending (one compare-exchange), then original | not called (the scene is in state 5) |
| `0x180abd0` headgear state | `x0` = scene | phase idle: original at once | sections 4, 8 |
| `0x328b5d0` unlisted test | `x1` = handle | original | synthetic handle: `1` if the row filler is running and the row is unavailable, else `0`; any other handle: original |
| `0x3288330` message key | `x0` = out struct, `x2` = handle | original | synthetic handle: writes the row's label into the struct (hash, length, text) |
| `0x19cd100` sort | `x0` = S, `w1` = mode | original | mode forced to 3, which goes straight to the epilogue (`0x19cd12c cbnz w1, 0x19cd280`) |
| `0x19ccb20` row filler | `x0` = S, `w1` = row, `x2` = row node | original | raise `FILLING`, original, lower it; then literal text if the row has one |

`0x19ccb20` proof (B, `d_rowfill_0x19ccb20.txt`): it is primary slot `+0x38` of the
sub-object vtable `0x50a6ae0` and is reached through the thunk `0x19cd010`
(`sub x0,x0,#0x48 ; b 0x19ccb20`), which is secondary slot `+0x10`; both land on the patched
entry. `0x19ccb3c ldp x9,x10,[x0,#0x128]` (x0 = S), `0x19ccb58 ldr x20,[x9,x8,lsl #3]` (row
index from w1), `0x19ccb74 mov x22,x2`, `0x19ccb90 ldr x0,[x22,#8]` (the row node is
dereferenced by the original before the plugin uses it). The function calls `0x328b5d0`
exactly once (`0x19ccd84`), so `FILLING` covers exactly the row's own availability question.

## 4. M3: how a page changes, and the state-stack argument

Facts (B; `d_state_reader_0x180ce40.txt`, `d_frame_update_0x180ead0.txt`,
`d_state5_end_0x180acbc.txt`, `s_scene_restart_byte.txt`):

1. Per frame `0x180ead0` calls the reader `0x180ce40` (`0x180eaf4`), then the current state's
   handler (`0x180eb24 blr`), then increments the frame counter `scene+0x14c`
   (`0x180eb28..0x180eb34`).
2. The reader loads the stack index `scene+0x144` (traps at >= 19, `0x180ce50`), the state in
   that slot (`scene+0xf8+4*index`) and the current state `scene+0x148`. Different: it
   installs the new handler and clears the frame counter (`0x180ceb8`). **Equal**
   (`0x180ce6c b.eq 0x180cebc`): `ldrb w8,[x19,#0x154]`; zero -> return; non-zero -> if the
   pair at `scene+0x18/+0x20` is non-null call it (`0x180cec4..0x180cee8`), then
   `str wzr,[x19,#0x14c]` and `strb wzr,[x19,#0x154]` (`0x180ceec`, `0x180cef0`).
3. In the scene code `0x1808980..0x180f400` the byte `+0x154` has four references: that one
   load and three stores of zero (`0x180cef0`, `0x180df20`, `0x180e168`). The game never sets
   it in this scene. The only store to `[x19,#0x18/#0x20]` is the constructor's
   `stp xzr,xzr,[x19,#0x18]` (`0x180df10`): the callback pair is null.
4. State 5 with `S+0xe8 == 0` (list script ended) always reaches
   `0x180adf4 ldr w8,[x19,#0x144] ; subs w8,w8,#1 ; b.lt ; str w8,[x19,#0x144]`: one pop,
   never below zero. The popped slot keeps its value 5.
5. State 5 with frame counter 0 (`0x180abec cbz`) is the first tick: it seeds S from the
   static (`0x180b060 bl 0x19cfe00`), resets the list's own state machine and re-activates
   the list in the pump (`0x180b0e4`). Session 2 ran this first tick four times on one list
   object, three of them in the same scene (A).
6. The dispatcher (state 3, `0x180a030..0x180a5b0`) never references `scene+0x180`: nothing
   state 3 does between two headgear visits touches the list object.

Mechanism (`editor.rs` `finish` -> `reenter`), in the hook after the original's last tick:

```
read depth_now = [scene+0x144], slot = [scene+0xf8+4*depth_open], current = [scene+0x148],
     restart = [scene+0x154], pair = [scene+0x18], [scene+0x20]
require (ui::can_reenter): 1 <= depth_open <= 18, depth_now + 1 == depth_open, slot == 5,
        current == 5, restart == 0, pair == (0, 0)
then    [scene+0x144] = depth_open ; [scene+0x154] = 1 ; remember the next page
```

Next frame: reader sees top == current == 5 and the byte set, calls nothing (pair null),
clears the frame counter and the byte; the handler runs with frame counter 0 = first tick;
the hook lets the original run it and then opens the remembered page like 0.4.0 opened its
list. If any requirement fails nothing is written, the visit ends (`mc|UI|exit|reason=...`)
and the game continues to the edit menu as after a cancel.

**Depth argument.** `depth_open` is read on the page's first tick. The plugin writes the
depth only in `reenter`, only the value `depth_open`, and only when the current depth is
exactly `depth_open - 1`. So after every page change the depth equals the depth of the first
page, whatever the number of changes; it cannot grow. The last page ends with the native pop
alone, as in 0.4.0. Each change is logged with `depth=`; `mc|UI|exit` logs `depth_open` and
`depth_now` (= `depth_open - 1`). Host test `visit_walkthrough` runs eleven changes against
a simulated stack; `reentry_conditions` covers every refusal.

**Why not through state 3** (pop, let the dispatcher push 5 again): it needs the dispatcher's
first tick to be skipped or the edit menu to restart and be dismissed without input; more
state, and no instruction-level advantage. Kept as the fallback design if the console shows a
problem with an immediate restart (section 12).

**If the remembered page never opens** (another state gets pushed in between, or the scene
goes away): the pending page is dropped by the next dispatcher call or by a headgear tick
that is not a first tick (`mc|UI|visit_lost`); the headgear state that was restarted runs as
the normal headgear screen. The restart byte, if still set, is consumed by the reader on the
next state change (the change path falls through `0x180ceb8` into `0x180cebc`), where it only
clears a frame counter that is already zero.

## 5. M2: what a greyed row is and what A does on it

Facts (B; `d_rowfill_0x19ccb20.txt`, `d_scroller_decide_0x377e150.txt`,
`d_button_0x378a6c0.txt`, `s_button_vtables.txt`, `d_cursor_step_*.txt`):

1. Row filler: `0x19ccd84 bl 0x328b5d0` on the row's handle; result bit 0 clear -> "enabled"
   branch (`0x19ccda0` slot `+0x1f8` with `w1 = 1`); set and `S+0x169 == 0` -> `0x19cce2c`:
   the row's button object, slot `+0x1f8` with `w1 = 0`, then slot `+0x388` (its look).
   In mod mode `S+0x169` is 0: `set_select` (`0x19cfff0..0x19cfff8`) stores the unlisted test
   of the cursor handle there, and outside the row filler the plugin answers 0.
2. The button class family: exactly nine vtables (all in `0x523c000..0x5240000`, where the
   scroller's vtable also lies) have `0x378a6c0` in slot `+0x1f8`, and the same nine have
   `0x378a6f0` in slot `+0x200`. `0x378a6c0`: `strb w1,[x0,#0x1c2]` (+ a redraw call);
   `0x378a6f0`: `ldrb w0,[x0,#0x1c2] ; ret`. So slot `+0x1f8(0)` makes slot `+0x200` answer 0.
3. Scroller decide (`0x377e230..0x377e2a4`): takes the cursor row part's button
   (`ldr x21,[x8,#0x28]`), calls slot `+0x200` (`tbz w0,#0 -> 0x377e33c`), then slot `+0x210`
   (same test), and only then `str w8,[x19,#0x2b0]` (pending decided row = cursor row).
   `+0x2b0` becomes `+0x2b4` at `0x377d658`, and Lua `get_decided_item` (`0x3363070`) returns
   `+0x2b4`. At `0x377e33c` the only thing that happens is one virtual call (slot `+0x30`) on
   the optional object `[scroller+0x140]`.
4. So **A on a greyed row: the scroller records no decision; the list script sees nothing; at
   most one call on `[scroller+0x140]`** (`0x377e33c`, then slot `+0x30` at `0x377d618`). The
   scroller has several such optional objects, each called through slot `+0x30` at the same
   place for one kind of event (`+0xb0` at `0x377d610`, `+0x110` at `0x377f0b0`, `+0x140`
   here); an event sound or callback for "refused" is the likely meaning (D). The branch
   itself contains nothing else.
5. The cursor helpers `0x19cd020` (secondary slot `+0x28`, called by the scroller when the
   cursor moves) and `0x19ccea0` skip a row the unlisted test flags: one extra row when
   moving one way, no move at all the other way (`0x19cd084..0x19cd08c`). With a list that is
   mostly greyed the cursor would jump and get stuck. That is why the plugin answers
   "unlisted" only while the row filler runs: the cursor moves over greyed rows normally.

Not proven (D): that the button the row filler disables (found by name through `0x3796970`)
is the object the scroller reads at `row part+0x28`; that the row parts' class is one of the
nine. The second writer of `+0x2b0`, `0x3780014`, is a pointer/touch path that tests another
flag (slot `+0x230`, byte `+0x1c6`); whether a disabled button can be chosen that way was not
traced. **Whatever the native side does, the plugin itself refuses**: `menu::step` turns a
decided unavailable row into "same page again, nothing stored" (host tests `page_steps`,
`visit_walkthrough`; mutation "unavailable row can be decided" is caught).

## 6. M5: the row-text route taken - literal text, with the label as fallback

`research/P11-ROW-TEXT.md` did not exist when this was done; the route below is this task's
own reading (B; `d_lua_set_text_string_0x335a490.txt`, `d_lua_set_text_message_0x335a100.txt`,
`d_find_pane_0x3776360.txt`, `d_set_message_0x3779b70.txt`, `d_set_text_utf8_0x37a22f0.txt`,
`s_lua_pane_methods.txt`).

1. The row filler sets a row's text with two calls per pane:
   `0x3776360(x0 = row node, x1 = pane name, x8 = result)` (`0x19ccbf8..0x19ccc00`) and
   `0x3779b70(x0 = &result, x1 = message key)` (`0x19ccc08..0x19ccc10`), for `set_txt_val` and
   `set_txt_val_disable`; then it frees `result[1]` (`0x19ccc14..0x19ccc28`).
2. `0x3776360` writes `result = {vtable 0x523c9a8, holder}` (`0x3776458`, `0x37764b0`), the
   holder being 0x20 zeroed bytes from the game allocator; `holder+0x10` = the pane as a text
   pane (`0x37764f0 bl 0x3772a30 ; str x0,[x22,#0x10]`).
3. `0x3779b70` is what Lua `set_text_message` calls (`0x335a1b0`); it reads
   `[[x0+8]+0x10]` and returns if that is null (`0x3779ba8..0x3779bb0`).
4. Lua `set_text_string` (method table `0x51833e0 -> 0x335a490`) reads the **same**
   `[[ud+8]+0x10]`, null-checks it and calls `0x37a22f0(text pane, UTF-8 C string)`
   (`0x335a54c..0x335a558`). `0x37a22f0` converts to UTF-16 on its own stack (at most 0x7fe
   units, null string handled) and calls `0x37a1cc0`.

So the plugin (`editor.rs` `set_pane_text`, after the original row filler returns) does, for
each of the two pane names: `0x3776360(node, name, result)` -> `pane = [result[1]+0x10]` ->
if non-null `0x37a22f0(pane, text)` -> free `result[1]` with `0x392e590`. The pane names are
the plugin's own NUL-terminated copies (no `%`; `0x3776360` formats its name argument).
`x8` is passed through a nine-instruction assembly stub (`mc_call_sret`), found byte for byte
in the NRO by the check script.

Safety net: the original has already put the entry's fallback label on the row, so a failed
lookup leaves a readable row; `text_set` / `text_missed` are counted per page and logged when
the page closes; `sd:/ultimate/mii_customizer/text_off` turns the route off without a rebuild.
Only main-page rows have literal text. Character rows keep their `list.txt` labels.

Not proven (D): that text set this way stays until the row is filled again (the Lua API
offering both setters on the same pane suggests it does); how a text longer than the pane is
drawn; whether the font has every character a menu file might use.

## 7. Game functions the plugin calls

| function | call | proof (B) |
|---|---|---|
| `0x37830e0` set item count | `(&S+0xf8, count)` | as 0.4.0 (A: 52 -> 88 -> 52 in session 2); `0x3783114/0x3783118` |
| `0x19cfe00` set_select | `(S, handle)` | what state 5 itself calls on its first tick (`0x180b060`); `0x19cfe18/1c` |
| `0x33750a0` Lua constant | `(state, "SCROLLER_ITEM_NUM", "i", count)` | the constructor's call `0x19cf83c..0x19cf854` (A: `item_num_set=1`) |
| `0x392dce0` / `0x392e590` alloc / free | list buffer per opened page; holder free | entries probed; `0x377645c`, `0x19ccc28` call them |
| `0x3776360` find pane (new) | `(row node, name, x8 = result)` | section 6 |
| `0x37a22f0` set UTF-8 text (new) | `(text pane, C string)` | section 6 |
| `nn::hid` npad state | entry B only | as 0.4.0 (never exercised on the console) |

New scene fields touched: read `scene+0x18`, `+0x20`, `+0xf8+4*depth`, `+0x148`, `+0x154`,
write `scene+0x144` and `scene+0x154` (section 4). Every offset constant of `ui.rs` is tied to
an instruction in check section E.

## 8. E3 across a visit (M4)

Unchanged from 0.4.0 per page (console result: equal four times out of four):

1. Writer 1 of the headgear static (`0x180ac3c`) needs `S+0x168`; the hook clears it before
   the original on every tick while a list is open.
2. Before the original's last tick the hook restores the native vector, count and the three
   handle slots to the headgear the Mii had **when the visit started** (`close`), so writer 2
   (`0x180ad20`) and the label refresh find nothing changed.
3. The save path writes nothing for a hash in no table (P10-HAT-OPEN Q3).

New for pages:

4. The snapshot (0x200 bytes of the working record, the headgear handle, the saved ID) is
   taken when the first page opens and kept for the visit.
5. After every page's last tick `finish` compares the handle (restoring it if it ever
   differed) and the record. A page change is made only when both are equal and the ID is
   unchanged; the `page` line says `equal=1|record_equal=1`.
6. When the next page opens, the handle and ID must again equal the visit's (`open`:
   `mii_changed` -> normal headgear screen, visit over).
7. `mc|UI|exit` is written once per visit with both handles, `equal`, `restored`,
   `record_equal`, `record_diff_at`, the number of pages and the two depths.
8. Between pages no list is open (`Mode::page_closed`): the unlisted, label, sort and row
   hooks pass everything to the original, so the original's first tick of the next page sees
   the unmodified game.

E4: with nothing armed the six hooks do what the table in section 3 says; the row filler hook
is one atomic load and a tail call for every list that is not ours (hat list, and it is not
the outfit list's function at all).

## 9. Log lines (all `mc|UI|...`, flushed per line)

| line | when | fields that matter |
|---|---|---|
| `L0|menu|...` | load | `state=ok|entries=N|labels=|allows=|rejected=|first_page=main` ; `menu_reject|line=|reason=` ; one `menu_entry|n=|id=|kind=|allowed=|label=|text=` per entry |
| `sites` | load | `ui=on|sites_ok=6/6|probes_ok=48/48|installed=6|entries=|menu=|text=on` |
| `arm` | dispatcher | `entry=A|value=7|...|page=main|id=|hat=|depth=` |
| `open` | first tick of a page, before anything is changed | `page=main` / `entry:<id>` / `direct`, `rows=`, `depth=`, `native_count=` |
| `list` | page in place | `count=|available=|cursor=|tick=|row0=|preset=|text=|item_num_set=1` |
| `decide` | page ended with a decision | `page=|row=|label=|preset=|action=` one of `open_entry`, `set`, `clear`, `slot_nothing_stored`, `refused_unavailable`, `none_id0`, `none_id_changed`; `greyed_fills=|text_set=|text_missed=` |
| `cancel` | page ended with B | `page=|slot=` and the same three counters |
| `store`, `SV` | a stats row was decided for a saved Mii | as 0.4.0 |
| `page` | the visit goes on | `from=|to=|depth=|n=|cursor=|hat=|equal=1|record_equal=1` |
| `exit` | once per visit | `reason=leave` (or why a page change was refused), `hat_before=|hat_after=|equal=|restored=|record_equal=|record_diff_at=|pages=|depth_open=|depth_now=` |
| `open_refused`, `visit_lost`, `stale`, `reentry`, `close_unexpected`, `arm_refused` | something was not as expected; the game continues with its own screen | `reason=` / `at=` |

## 10. Console test plan (10 user steps)

Card (coordinator): 0.5.0 NRO, the real `menu.txt`, `list.txt`, wide presets, the edit
script for way in A, `loadouts.txt` as it is (A `0000f589` = dedede, B `0000f58b` = fox). No
`ui_off`, no `text_off`. Delete the old log first.

| # | do | expect on screen | log lines that prove it |
|---|---|---|---|
| 1 | Boot. Mii Fighters, edit Gunner A, enter mod mode (way in A). | **Main page**: one row per menu entry with its text (Stats, Jab, ...), no tick, cursor on the first row. Title may still say Headgear. | `L0|menu|state=ok|entries=24|rejected=0`; `sites|ui=on|sites_ok=6/6|probes_ok=48/48`; `arm|...|page=main`; `open|page=main|rows=24|depth=D`; `list|page=main|count=24|available=24|cursor=0|tick=-1` |
| 2 | Move to **Jab**, press A. | List closes and reopens as a character list: first row "Mii Gunner" with cursor and tick, **every other row greyed**. | `decide|page=main|row=1|action=open_entry|...|text_set>0|text_missed=0`; `page|from=main|to=entry:jab|depth=D|n=1|equal=1|record_equal=1`; `open|page=entry:jab|rows=88|depth=D`; `list|...|available=1|cursor=0|tick=0|row0=nam_chr1_00_miigunner` |
| 3 | Move down onto greyed rows (also scroll a page), press **A several times** on one. | Cursor moves over greyed rows like over normal ones. A does nothing (a refusal sound is fine). No dialog. | **no new line** while pressing A. (If `decide|...|action=refused_unavailable` and `page|from=entry:jab|to=entry:jab` appear, the list closed and reopened on the same page: the fallback worked, the native refusal did not - report it.) |
| 4 | Press **B**. | Main page, cursor on Jab. | `cancel|page=entry:jab|...|greyed_fills>0`; `page|from=entry:jab|to=main|depth=D|n=2|cursor=1`; `list|page=main|...|cursor=1` |
| 5 | Open Jab again, press A on **Mii Gunner**. | Main page, cursor on Jab. | `decide|page=entry:jab|row=0|label=nam_chr1_00_miigunner|preset=-|action=slot_nothing_stored`; `page|...|to=main`; no `store`, no `SV` |
| 6 | Open **Stats**. Pick another character (say Kirby) with A. | Stats page: all rows normal, cursor and tick on King Dedede. After A: main page, cursor on Stats. | `list|page=entry:stats|count=88|available=88|cursor=38|tick=38|...|preset=dedede` (88 and 38 with today's `list.txt`); `decide|page=entry:stats|row=..|preset=kirby|action=set`; `store|...|result=changed|preset=kirby`; `SV|result=ok`; `page|from=entry:stats|to=main` |
| 7 | Open Stats, press A on the first row (**clear**). Open Stats once more and pick Kirby again. | First: tick was on Kirby. After the clear and reopening: cursor and tick on row 0. | `decide|...|row=0|action=clear`; `store|result=changed|preset=-`; `SV|result=ok`; then `list|...|cursor=0|tick=0|preset=-`; then `action=set ... preset=kirby` |
| 8 | **Ten page changes in a row**: five times open any entry and leave it with B. Then **B on the main page**. Move around the edit menu. | Each change is a close/open of the list. After the last B the edit menu is back and works. | ten more `page` lines, all `depth=D`, `n` counting up, all `equal=1|record_equal=1`; then `cancel|page=main`; **one** `exit|entry=A|reason=leave|hat_before=X|hat_after=X|equal=1|restored=0|record_equal=1|pages=..|depth_open=D|depth_now=D-1` |
| 9 | Open the **normal Headgear** screen (A on Headgear, no ZL/ZR): look, move, cancel. Open the outfit screen, cancel. Leave the editor (save). Play a **match**, Gunner A against Gunner B. | The hat list is the normal one (52 hats, real names, real preview). In the match A has Kirby's stats, B Fox's. | no `mc|UI|` line for the normal screens; `OV|id=0000f589|...|preset=kirby` |
| 10 | **Reboot** the game, play one more match (or just boot), send the log and `loadouts.txt`. | A still Kirby. | `L0|loadout|...|state=ok`; `LO|id=0000f589|preset=kirby`; `loadouts.txt` has `0000f589 preset kirby` |

Optional, if time: way in B (hold ZL or ZR while pressing A on Headgear; `arm|entry=B|value=1`);
one boot with an empty file `text_off` (rows show fallback labels; `sites|...|text=off`).

Decisions that depend on this test and cannot be settled offline: whether the immediate
restart of the headgear state is clean; whether a list shorter than the native 52 rows
behaves (main page: 24 rows; session 2 only showed a longer one); whether the disabled look
and the refusal on A are what the image suggests; whether literal text shows and fits.

## 11. Failure patterns

| what is seen | last / telling log line | meaning | do |
|---|---|---|---|
| crash or freeze right after A on the main page | last line `page|...`, no `open` | the restart of the headgear state | rollback; report the line |
| crash or freeze when a page appears | last line `open|...` without `list` | list swap, count or cursor on this page size | rollback; note `rows=` |
| main-page rows show "???" or one identical odd text | `text_set=0|text_missed>0` in the next `decide`/`cancel` | pane lookup found no text pane | cosmetic; add `label` lines or `text_off` |
| crash while the main page draws, fine with `text_off` | last line `list|page=main|...|text=1` | literal text route | use `text_off` |
| slot page: no row greyed | `greyed_fills=0` | the row filler did not ask, or `S+0x169` was set | report; choices are still refused by the plugin |
| slot page: cursor skips rows or sticks | - | a cursor helper asked while a row was being filled | report |
| A on a greyed row closes and reopens the same page | `decide|...|action=refused_unavailable` | native refusal did not hold, fallback did | harmless; report |
| A on a main-page row returns to the edit menu | `exit|reason=not_popped` / `slot_state` / `current_state` / `restart_set` / `change_callback` / `mode_state` | the scene was not as section 4 assumes; nothing was written | report the reason |
| real hats appear after choosing an entry | `open_refused|reason=..` or `visit_lost|at=..` | fallback to the normal headgear screen | leave with B; report |
| `exit|...|equal=0|restored=1` or `record_equal=0` | | E3 was broken (and the handle put back) | stop, rollback, send the log |
| `page` lines with a growing `depth=` | | cannot happen by section 4 | stop, rollback |
| edit menu dead after leaving mod mode | `exit` line present | resume of state 3 after several pages | rollback |
| `sites|ui=off|...|probes_ok<48` | a `ui_probe ... match=0` line | image is not what was audited | nothing is hooked; report |

## 12. Rollback

- Fastest: create the empty file `sd:/ultimate/mii_customizer/ui_off` (no UI hook; stat
  engine and saved presets keep working).
- 0.4.0 behaviour inside 0.5.0: remove `menu.txt` (direct page; the row filler hook then only
  passes through).
- Previous build: `builds/0.4.0-ui/libmii_customizer.nro`, sha256
  `d28aea75f04f56665f11d46529abe940e527db433c169defbbaff6076117d74a`. `loadouts.txt` written
  by 0.5.0 is the same `mc_loadouts 2` format.
- If the immediate restart turns out to be the problem: the alternative in section 4 (let the
  pop stand, re-push state 5 from the dispatcher hook on state 3's first tick, optionally
  after a few frames).

## 13. Checks run in this task (observed)

| check | command (workspace root) | result |
|---|---|---|
| build | `bash mods/mii_customizer/build-plugin.sh` | exit 0, 0 warnings; `builds/0.5.0-menu/libmii_customizer.nro` 102400 bytes, sha256 `565014abfb483cb08ab12c153676f82787ed92a94b14eee89f598c150335ec27`; built twice, same hash |
| host tests | `bash mods/mii_customizer/scratch/2026-10-06_P11-MENU/run_host_test.sh` | 0.3.0 tests on the new sources **47 passed, 0 failed**; new tests **35 passed, 0 failed** (output: `evidence/P11-MENU/host_test_output.txt`) |
| mutation control | `python mods/mii_customizer/scratch/2026-10-06_P11-MENU/mutation_control.py` | **102 mutations, 102 caught, 0 missed**, exit 0. The first run caught 101: "next page without a visit" slipped through, one assertion was added to `mode_pages_of_one_visit`, and the whole control was run again (output: `evidence/P11-MENU/mutation_control_output.txt`) |
| image + NRO check | `PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python mods/mii_customizer/evidence/P11-MENU/check_p11_menu.py` | **358 checks, 0 failed**, exit 0 (output: `evidence/P11-MENU/check_output.txt`) |
| negative controls | same script, `--selftest` | clean run exit 0; all 11 controls (`word`, `disasm`, `call`, `entry`, `offset`, `static`, `scan`, `reloc`, `label`, `nro`, `manifest`) exit 1; selftest exit 0 (output: `evidence/P11-MENU/selftest_output.txt`) |

What the host tests cover: `list.rs` (well-formed file, every reject reason reachable through
a file, fallback states, limits); `ui.rs` (synthetic handles, `outcome`, `action`,
`current_row`, the label struct against an independent hash, `dispatch`, the mode state
machine for one page, for a visit of eleven pages, for dropped and stolen pending pages,
`can_reenter`, `clamp_selected`, `first_difference`, `vector_count`, `same_item`, the site
table); `Store::set_preset` (set, clear, unchanged, full, ID 0, explicit values stay, OV
marks, serialise round trip, and two million updates against three reader threads that
accept only the old or the new value); `loadout::load` (all combinations of contract B+);
`menu.rs` (constants, well-formed file, thirty reject cases, text and id limits, 48-entry
limit, file states, the delivered example, page codes, rows, availability, labels and text,
cursor and tick, every step, and a whole visit against a simulated state stack).
Not reachable through a file and therefore untested: `list::Reject::TooManyEntries` (128
presets at most can exist).

What the check script covers: sections A-H of its docstring - 55 word records against the
image, 114 instructions by their disassembly text, 14 function entries and 10 call sites, 24
offset constants each tied to an instruction, the whole-range facts of sections 4 and 5, three
message labels, and the NRO (records, strings, the call stub, the stat hook's unknown-hash
path, manifest hashes).

## 14. Everything that is tier D (never run)

1. The whole page mechanism at runtime: undoing the pop and the restart byte; the list
   restarting one frame after its script ended; ten changes in a row.
2. A list **shorter** than the native 52 rows (main page; any short example menu). Session 2
   showed only 88 rows.
3. Greyed rows: that the unavailable branch gives the look the player knows; that A on such a
   row does nothing; what the call on `[scroller+0x140]` is; touch / pointer input on a greyed
   row.
4. That the cursor moves normally over greyed rows.
5. Literal text: that it shows, fits and stays; `text_set` / `text_missed` values.
6. Cursor without tick (main page), tick on another row than the cursor (after a refused
   row): written through `S+0x148` / `S+0x150` as 0.4.0's never-exercised "preset not in the
   list" case.
7. Row 0 of a stats page clearing a preset (not exercised in session 2), now behind the menu.
8. Way in B (ZL/ZR), still never exercised; the sort button while a page is open.
9. `text_off`, `ui_off` with 0.5.0; a malformed `menu.txt` on the card (host-tested only).
10. The row filler hook on the normal headgear screen (pass-through by construction).
11. A reboot reading a `loadouts.txt` written by the plugin (was open after session 2 too).
12. The proposed `slot` loadout key - a proposal, nothing implemented.

Could not verify at all in this task: anything in the game. No emulator, no console.

## 15. Files

Changed (all inside the exclusive paths):

- `plugin/src/menu.rs` (new), `plugin/src/ui.rs`, `plugin/src/editor.rs`, `plugin/src/lib.rs`,
  `plugin/Cargo.toml`, `plugin/Cargo.lock` (version only), `plugin/README.md`
- `build-plugin.sh` (variant `menu` from 0.5.0; 0.4.x stays `ui`)
- `builds/0.5.0-menu/libmii_customizer.nro`, `MANIFEST.json`, `example/menu.txt`
- `builds/.cache/` (cargo target, build log, host-test binaries)
- `research/P11-MENU.md` (this file)
- `evidence/P11-MENU/`: `check_p11_menu.py`, `check_output.txt`, `selftest_output.txt`,
  `host_test_output.txt`, `mutation_control_output.txt`, 23 disassembly windows `d_*.txt`,
  4 scans `s_*.txt`
- `scratch/2026-10-06_P11-MENU/`: `host_test.rs`, `run_host_test.sh`, `mutation_control.py`,
  `write_manifest.py`, tools `scan.py`, `strx.py`, `reltab.py`, `btnvt.py`, `btnvt2.py`,
  `words.py`, one-off edit helpers `splice_mode.py`, `mode_new.rs.txt`, `readme_edit.py`

Not touched: `STATUS.md`, `CURRENT_INSTALL.md`, other tasks' files, the 0.4.0 package.

Process note: a few one-off shell here-documents were used during the work (inline checks,
the README edit helper, a report number fix), against the prompt's "write scripts with the
file tool, no heredocs". Every delivered script was written as a file.

Out of scope, noticed:

- `plugin/README.md` still described 0.3.0 (the 0.4.0 task never updated it); brought to 0.5.0.
- `scratch/2026-10-05_P7-PRESET-ENGINE/check_build.py` and `mutation_control.sh` are bound to
  the 0.3.0 package. The part that matters for later versions (the stat hook's unknown-hash
  path has no call and no stack write) is re-checked for the 0.5.0 NRO in
  `check_p11_menu.py` section H: 26 instructions, clean.
- 0.4.0's sources named a host test and a check script under `P10-UI-SLICE` that never
  existed; the comments now point at this task's files.

## Final summary

**Task ID: P11-MENU - DONE (offline deliverables complete; nothing run in the game).**

- Delivered: plugin 0.5.0 (`builds/0.5.0-menu/`, NRO `565014ab...`, manifest, example menu),
  pages per contract M with literal row text and greyed rows, the menu parser per contract G,
  the host tests and mutation control owed from 0.4.0 plus the new ones, the check script
  with negative controls, this report.
- Nothing reduced: all of M1-M5 is implemented. Literal text has a switch (`text_off`) and a
  label fallback; greyed rows have a plugin-side refusal behind the native one.
- Verified here: build (reproducible), host tests 47 + 35, mutation control, 358 image/NRO
  checks, 11 negative controls. See section 13 for the exact numbers.
- Not verified: everything at runtime (section 14). The first console boot decides the four
  questions at the end of section 10.
- For the coordinator: the contract readings in section 2 (text restrictions, `#` rule,
  order of lines, `not_slot`), the new switch file `text_off`, 6 sites / 48 probes in the load
  log, and the `slot` loadout key proposal.
