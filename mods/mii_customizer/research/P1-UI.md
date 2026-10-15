# P1-UI - inventory of the native Mii Fighter editor UI

2026-10-04. Space Bunny Alpha worker, phase 1 discovery. Research only, no production code.

Status: **DONE** (bounded inventory complete). No blocker; two inspection limits recorded below.

Sources: local ARC path index `mods/ssbu_mod_new/dumps/decoded/arc_files.tsv`
(sha256 `727a03c518ecb4614e8bca07202e916a9c2f4305f3f63a54b9d21a6db2c26369`, 590711 paths) and seven
files extracted from `gamedata/ssbu-13.0.4/data.arc`
(sha256 `ef615e671e1d4907f0a707f2eb13e3cb0c8539c4e67ac51c89ef547c22b82995`) into
`gamedata/mii_customizer/P1-UI/`. Full hashes and every command are in
`evidence/P1-UI/commands_and_hashes.txt`.

## 1. Which editor this is

The Smash Ultimate Mii Fighter editor is the **`make_mii_*` ("Mii make") screen family**, all under
`ui/`. It is fully inside the game's own ARC and is driven by shipped Lua 5.3 bytecode.

No paths matching the searched names for the **Switch system Mii appearance editor** were found.
`grep -icE 'mii_studio|mii_editor|miieditor|chara_edit'` over the 590711-path index returns **0**.
SSBU only *consumes* Mii appearance data that the Switch OS already owns:

- `ui/param/database/ui_mii_body_db.prc`, `ui_mii_hat_db.prc`, `ui_mii_voice_db.prc` (ids the game accepts)
- `miihat/` (24293 paths) - hat models, and `fighter/miifighter/model/b_<bodytype>_<gender>/`
  (11526 paths under `fighter/miifighter/`) - baked Mii body base models
- the in-game editor's own colour parts (`color_00..color_11`, `set_pic_color` in `make_mii_edit`)

Coordinator correction 2026-10-04: absence of those path names does not prove an editor is
unmodifiable. Face appearance editing is outside this project's requested scope; hat, outfit and
voice controls appear in the game's own candidate resources listed below. The move/stat extension
route remains unverified; the index and string scans locate candidates, not complete ownership.

Also note a naming trap: the old mod's `mods/ssbu_mod_new/refs/mii_*` folders mean
**"mid-investigation", not Mii the character** (`refs/INDEX.md` line 7:
`mii_hero_spin_hi1_wrong` = wrong Hero's Spin move). Do not read them as Mii research.

## 2. Candidate files (strongest first)

Verified = path present in the local index. Inspected = extracted and opened.

| # | ARC path | Verified | Inspected | Why relevant |
|---|---|---|---|---|
| 1 | `ui/script/menu/chara_make/make_mii_special_actor.lc` | yes | yes | The **special-move selection screen controller**. Owns `LayoutButtonSelector`, the skill list, and the `get_skill_id` / `set_skill_id` calls. |
| 2 | `ui/layout/menu/make_mii_special/make_mii_special/layout.arc` | yes | yes | Layout of that screen: 4 `set_special_item_00..03` buttons in group `selector_0`, detail pane, footer. |
| 3 | `ui/script_patch/chara_make/make_mii_edit_actor.lc` | yes | yes | **Nintendo's own shipped patch** of the editor hub. Differs from base by exactly one added flag, `IS_SKILL_EDITABLE`. This is the strongest extension-point lead in the whole archive. |
| 4 | `ui/script/menu/chara_make/make_mii_edit_actor.lc` | yes | yes | The editor **hub** controller: rows `set_item_00..05`, selectors `selector_0` / `selector_1`, save/random/favourite popups. |
| 5 | `ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc` | yes | yes | Layout of the hub. Rows map to name / hat / outfit / colour / **special moves** / voice+author. |
| 6 | `ui/param/database/ui_popup_db.prc` | yes (index) | no | Holds the popup ids the hub script uses (`ID_POPUP_MMIIF_EDIT_SAVE`, `ID_POPUP_MMIIF_EDIT_RANDOM`, `ID_POPUP_MMIIF_EDIT_CANCEL`, `ID_POPUP_AMIIBO_MII_EDIT_CANCEL`). |
| 7 | `ui/replace/skill/skill_1/skill_1_mii{fighter,gunner,swordsman}_special_{normal,side,upper,lower}_0..2.bntx` | yes (index) | no | 15 icon sheets per Mii class = 4 directions x 3 icons + 3 Final Smash. These are the labels drawn per special slot. |
| 8 | `ui/layout/menu/make_mii_base/make_mii_base/layout.arc` | yes | yes | The **saved-Mii picker** (`set_parts_scr_item_00..19`, `mnu_mmiif_sel_create_mii`). Listed here for completeness; identity is P1-ID's scope. |
| 9 | `ui/script/menu/chara_make/make_mii_utility.lc` | yes (index) | no | Shared helper required by `make_mii_edit_actor.lc` (`require '!menu/chara_make/make_mii_utility'`). Will be needed by any new screen. |
| 10 | `ui/layout/menu/make_mii_special_subwindow/make_mii_special_subwindow/layout.arc` | yes (index) | no | Sub-window used by `replace_skill_subwindow`. |
| 11 | `fighter/miifighter/param/vl.prc`, `fighter/miigunner/param/vl.prc`, `fighter/miiswordsman/param/vl.prc` | yes (index) | no | The move tables the UI ultimately selects into. Slot list is P1-CATALOG's scope; noted only to close the UI -> data edge. |
| 12 | `ui/param/database/ui_chara_db.prc` | yes | yes | 487-entry fighter-id table (`paracobn`); maps the internal fighter slot ids used by the editor. Dumped, not decoded. |

Remaining uninspected `chara_make` scripts, all present in the index:
`make_mii_select_actor.lc`, `make_mii_body_actor.lc`, `make_mii_hat_actor.lc`,
`make_mii_voice_actor.lc`, `make_mii_hat_body_layout.lc`.
Layouts `make_mii_style`, `make_mii_color`, `make_mii_voice`, `make_mii_hat_body` exist too.

**Important path correction:** layout ARCs are nested one level deeper than the flat index listing
suggests. The real path is `ui/layout/menu/make_mii_special/**make_mii_special**/layout.arc`, not
`ui/layout/menu/make_mii_special/layout.arc`. The short form returns
`MISSING ... the requested resource could not be found` from `tools/arc-extract`.
Anyone scripting extraction must use the doubled name.

## 3. The editor's structure, as observed

`make_mii_edit` (hub) rows, read from the layout part names and the hub script's
`string.format('set_item_%02d', ...)` loop (`set_item_00`..`set_item_05`):

| row | parts | meaning |
|---|---|---|
| `set_item_00` | `mnu_mmiif_setup_fighter_nam_00/01` | fighter name |
| `set_item_01` | `mnu_mmiif_setup_hat_00/01` | hat |
| `set_item_02` | `mnu_mmiif_setup_outfit_00/01` | outfit / body |
| `set_item_03` | `mnu_mmiif_setup_color` | Mii colours |
| `set_item_04` | `mnu_mmiif_setup_sp_move_00..04` | **special moves (entry row)** |
| `set_item_05` | `mnu_mmiif_setup_voice_00..02`, `mnu_mmiif_setup_author_00/01` | voice + author |

Two button selectors, `selector_0` (outer) and `selector_1` (row-level). Footer/aux parts:
`mnu_mmiif_favorite`, `mnu_mmiif_setup_btn_try`, `mnu_mmiif_setup_btn_random`,
`mnu_mmiif_setup_miifighter_no_edit`, `set_footer_area`.

`make_mii_special` (the screen `set_item_04` opens):

- group `selector_0` -> `set_special_item_00`, `_01`, `_02`, `_03`
- 4 headers `category_00..category_03`, each with its own icon
  (`make_mii_icn_special_00..03`, `make_mii_icn_spselect_00..03`)
- detail pane `set_rep_special` plus `set_txt_num_current` / `set_txt_name_current` /
  `set_txt_desc_current`
- footer `set_btn_ok`, `mnu_footer_ok`, `mnu_footer_save_btn`, `set_footer_area`
- fonts `FOT-RodinNTLGPro-B64` / `-EB64` (already present in the file, so a new label field
  would not need a new font)

## 4. Which handle owns special-move selection today

All of the following is read off `make_mii_special_actor.lc`'s constant table
(`evidence/P1-UI/observed_strings.txt`); treat function *bodies* as unread.

**Established (tier B, string-level verified):**

- Two counts exist and are named: `SKILL_COMMAND_NUM` and `SPECIAL_SKILL_NUM`. `SKILL_COMMAND_NUM`
  drives `set_special_item_%02d` and `set_item_%02d` via `string.format`; `SPECIAL_SKILL_NUM`
  drives the sub-window list. The exact numeric values are **not** in the strings.
- List entries are pushed into the layout with `set_special_item_%02d`.
- The list is filled through `UiScriptPlayer.invoke` with `get_skill_name_label` and
  `get_skill_help_label`, plus `command_id`.
- The chosen value is read with `get_skill_id` and written with `set_skill_id` on the title part
  `mnu_mmiif_setup_sp_move_title` (`set_sub_title`).
- The hub is refreshed by `replace_skill` and `replace_skill_subwindow` (animation
  `play_animation_and_wait`), i.e. the hub's `mnu_mmiif_setup_sp_move_00..04` parts are filled from
  native state, not by Lua.
- The hub's editability is gated by flags read from native: `IS_READ_ONLY`, `IS_NEED_SAVE`,
  `IS_SKILL_EDITABLE`.

**Shipped-patch delta (verified, this is the headline).** Diffing the ASCII runs of
`ui/script/.../make_mii_edit_actor.lc` against `ui/script_patch/.../make_mii_edit_actor.lc`
gives exactly four added lines, all the same token, always next to `IS_READ_ONLY`:

```
+IS_SKILL_EDITABLE   (x4, one of them followed by set_selectable)
```

Everything else is byte-for-byte the same string sequence. Interpretation (tier D): Nintendo added a
runtime-gated "skills can be edited" condition to the existing hub in a later revision, and shipped
the patch layer rather than editing the base script. **The flag's backing field is unknown.**

## 5. One candidate extension point

**Add a row to the `make_mii_edit` hub, gated by a flag in the shape of `IS_SKILL_EDITABLE`.**

Concretely: a `set_item_06` row in `ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc`
(`set_item_00..05` are the taken indices), plus a `ui/script_patch/chara_make/` override of
`make_mii_edit_actor.lc` that extends the `set_item_%02d` loop and adds a `set_selectable` gate.
A new screen would then follow `make_mii_special`'s shape (a `layout.arc` + an actor `.lc` +
`ui_layout_db.prc` registration).

Why this one: it is the only extension shape the game itself already demonstrates, it needs no new
framework plugin, and it sits on the row the project already needs to extend.

**I am not claiming this hook works.** Three things are unknown and each can invalidate it:
1. Whether a `layout.arc` under `ui/layout/menu/` can be replaced wholesale on 13.0.4 (tier D;
   `mods/ssbu_mod_new/handbook/10_arcropolis_config_json.md` covers ARCropolis generally but says
   nothing about layout ARCs).
2. Whether `LayoutRootList` will accept a row the native code does not know about.
3. Whether the value a new row writes can be stored at all - see section 6.

## 6. Unknown controller-to-native boundaries (explicit)

These are the strings' names only; no native target was located. None of them was traced.

| name | seen in | what is unknown |
|---|---|---|
| `get_skill_id` / `set_skill_id` | `make_mii_special_actor.lc` | Which object owns the special index; whether it is per saved fighter or per session; its field offset. **This is the single most important unknown for the project.** |
| `get_skill_name_label`, `get_skill_help_label` | `make_mii_special_actor.lc` | Native label table source; whether Gunner-only labels exist separately from `miifighter`. |
| `IS_SKILL_EDITABLE`, `IS_READ_ONLY`, `IS_NEED_SAVE` | `make_mii_edit_actor.lc` (+ patch) | Where these flags come from and whether they are writable. |
| `UiScriptPlayer.invoke` | all three scripts | The invoke table itself; which names are bound to which native functions. |
| `AppPopupManager.open_database`, `UiFighterManager` | `make_mii_edit_actor.lc` | Native managers behind the save/random flows. |
| `SKILL_COMMAND_NUM`, `SPECIAL_SKILL_NUM` | `make_mii_special_actor.lc` | Numeric values. They live in the bytecode as literals/globals, not strings, so a string scan cannot give them. |
| `fighter/miigunner/param/vl.prc` skill table | not opened | Whether the UI's skill id indexes the Gunner table directly or a shared Mii table. P1-CATALOG should own this. |

Also unestablished: nothing here has been seen at runtime. No emulator was run, per the prompt.

## 7. Inspection limits and exact failures

1. **`rg` is not installed on this machine's PATH** (`which rg` -> not found, not in any PATH entry).
   The prompt says to use rg first; `grep -E` on the same index was used instead. Same file, same
   results. This is a workspace tooling gap the coordinator may want to record.
2. **No Lua 5.3 decompiler is available** (`lua`, `luac`, `luajit` all absent; no existing tool in
   `tools/` or `mods/ssbu_mod_new/tools/`). A stock Lua 5.3 chunk parser was written in scratch and
   parses the 32-byte header correctly (`1bLua` 0x53, LUAC_INT 0x5678, LUAC_NUM 370.5) but then
   fails to walk the proto body, so **the constant tables were read by printable-ASCII scan, not by
   a real parse**. Every string quoted in this report is a literal byte run from the file, which is
   why no line numbers, call sites or argument order can be given. Scratch script:
   `scratch/2026-10-04_P1-UI/lc53_strings.py`.
3. **The layout ARCs were read by the same ASCII scan**, not by a BNTX/FLYT parser. The part names
   are real and de-duplicated, but their parent/child structure and z-order are not established.
   The `set_item_00..05` row mapping in section 3 is an inference from names plus the script's
   `set_item_%02d` formatting, cross-checked by `make_mii_edit_actor.lc`'s `category_00..04` loop -
   tier B for the names, tier D for the mapping.
4. **`ui/param/database/ui_popup_db.prc` was not extracted or decoded** - index-only listing.
5. No file under `mods/ssbu_mod_new/` was modified. No emulator, no SD access, no commits.

## 8. Evidence tier summary

| tier | claim |
|---|---|
| **B** verified offline | The `make_mii_*` ARC paths listed in section 2 exist in `data.arc`; the extracted file hashes; every string and part name quoted above; the four-line `IS_SKILL_EDITABLE` patch delta; `mii_studio`/`mii_editor` absent from the index; the seven `ui/param/database/ui_mii_*` ids exist. |
| **A** console | none. No run was performed. |
| **C** pinned external | none. No network lookup was needed or made. |
| **D** hypothesis | the `set_item_*` row mapping; "the `IS_SKILL_EDITABLE` patch is Nintendo's own revision gate"; `set_item_06` being the next free row; layout-ARC replaceability. |

Verified / unverified split: everything about **file existence, names and byte content** is
verified. Everything about **runtime behaviour, native bindings and saved-data storage** is
unverified.

## 9. Suggested next task (one, narrowly scoped)

**`P1-UI2 - resolve `get_skill_id` / `set_skill_id` offline, or declare it blocked.**

One question only: does the value chosen on the `make_mii_special` screen land in the saved
per-fighter Mii entry, and where? Bounded method, no new tooling:
1. Confirm the numeric value of `SKILL_COMMAND_NUM` / `SPECIAL_SKILL_NUM` by decoding the two
   chunks properly (a correct LuaU 5.3 chunk reader, ~100 lines, scratch only). This also
   confirms whether the flag `IS_SKILL_EDITABLE` is read or called, which the string scan cannot say.
2. Cross-check `fighter/miigunner/param/vl.prc` skill entries against the 12
   `ui/replace/skill/.../skill_1_miigunner_special_*.bntx` icons, to see whether the UI's
   `skill_id` is the same index space.
3. If both steps come back ambiguous, stop and report BLOCKED with the exact boundary and the
   minimal input needed - do **not** escalate to native RE on the strength of this report.

This is deliberately one step, because it is the only question in section 6 that can be attacked
offline, and it decides whether the section 5 extension point is worth building.

## Task summary

**P1-UI: DONE**

Files created (exclusive paths only):
- `mods/mii_customizer/research/P1-UI.md` (this report)
- `mods/mii_customizer/evidence/P1-UI/commands_and_hashes.txt`
- `mods/mii_customizer/evidence/P1-UI/arc_index_hits.txt`
- `mods/mii_customizer/evidence/P1-UI/observed_strings.txt`
- `mods/mii_customizer/evidence/P1-UI/layout_part_names.txt`
- `mods/mii_customizer/scratch/2026-10-04_P1-UI/lc53_strings.py` (partial Lua 5.3 reader, scratch)

Extracted read-only inputs: `gamedata/mii_customizer/P1-UI/` (7 files).

Changed nothing else. Did not touch `STATUS.md`, other workers' paths, `mods/ssbu_mod_new/`,
shared tools, saves, plugins or the SD card. No emulator, no commits.

Blocker: none for this task. Open question for the coordinator: `rg` is not on PATH, and no Lua 5.3
decompiler exists in the workspace - decide whether either becomes a shared tool before phase 2.
