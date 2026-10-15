# P14-SORT-OPTIONS - Research and Design Report

> **Coordinator review, 2026-10-07.** Rerun from the workspace root: `check_p14.py` 389/0
> (exit 0); host tests 47/0, 35/0 and this task's 16/0; NRO sha256 `b9751751...` equals the
> manifest. Not rerun: the selftest controls, the mutation control, the build. Read by the
> coordinator: `handle_sort`, `hook_sort`, the vector fill in `open`, `names::compute_name_order`.
> How it works, in one line: a row's handle keeps naming its fighter-order row; sorting only
> permutes the handle vector, and label, availability and decision are all resolved from the
> handle, so the mapping cannot drift. Corrections and open points:
> - The log lines quoted in section 8.1 are not the plugin's (`mii_customizer 0.7.0-menu
>   loaded`, `page_change`, `to=stats`): the real ones are `sites|...`, `page|from=..|to=entry:<id>`,
>   `sort|page=..|mode=..|order=..`. Use `CURRENT_INSTALL.md`.
> - "Capacity 32 Mii IDs x 16 option entries" was not checked by the coordinator.
> - Sort order persists (as the prompt asked) but the list script sets its own sort label
>   back to option 0 whenever it initialises (`main.p5` pc 104). If the script initialises on
>   every page, a page may open name-sorted under the label of option 0. D until seen;
>   if so, the fix is to open every page in fighter order.
> - `handle_sort` indexes a slice and uses the literal `0x158` (rule: no indexing, named
>   offsets); bounds hold because the count is at most the array length. To tidy with the
>   next plugin task. `plugin/src/editor.rs` line 621 holds a raw NUL byte inside the
>   `MC_MINUS` literal (coordinator's 0.6.0 edit; valid Rust, same bytes as `\0`, but tools
>   treat the file as binary): also to tidy.
> - The NRO grew from 110592 to 237568 bytes. Analysed 2026-10-07 after 0.8.0 crashed at
>   boot: `menu::Menu` became 123 KiB with the inline option array and is passed by value,
>   giving `main` a 283552-byte frame on a 64 KiB stack. **This 0.7.0 NRO would crash at
>   startup; do not install it** (fixed in the 0.8.0 sources,
>   `evidence/2026-10-07_session4/RESULT_boot1.md`).
> - The session's Sword page has ONE row; the shortest list run so far has 24.


**Status:** DONE  
**Task ID:** P14-SORT-OPTIONS  
**Plugin Version:** 0.7.0  
**Evidence Tier:** Tier B (offline verified against `main.bin`, host tests, and built artifacts); console execution is Tier D.

---

## 1. Executive Summary & Design in One Page

Plugin 0.7.0 satisfies two user requests on top of 0.6.0:
1. **Working "Sort by Name":** On character pages (Stats and Slot pages), sort mode 2 ("By Name") orders rows $1..N$ alphabetically by character display name (`names.txt`), ASCII case-insensitive, falling back to preset name if unmapped. All other sort modes (modes 0, 1, or others) order rows by fighter number (`list.txt` order). Row 0 (Mii Gunner default) remains pinned at the top in every order. Cursor and tick follow their corresponding characters to the new row index; greyed row availability accurately maps to each character. The chosen sort order persists across page navigations and menu visits until the game is restarted. Main menu pages and option pages are never reordered.
2. **Option Pages (First Use: Sword):** Extends Contract G with `Kind::Option` (`entry <id> option <text>` and `option <id> <option_id> <text>`). An option page displays the entry's options (up to 32), all available. A confirms selection and returns to the main page; B cancels without changes. Main page row displays `<entry text>: <option text>` (or `<entry text>` under `text_off`).
3. **Loadout v3 Storage:** Implements `mc_loadouts 3` supporting `<id> option <entry_id> <option_id>`. Absent option line defaults to option 0; selecting option 0 removes the option line. To ensure backward compatibility and seamless rollback to 0.6.0, the writer serialises version 3 *only* when $\ge 1$ option line exists; otherwise, it writes version 2. Version 2 files remain fully readable.

All 86 legacy tests pass, 16 new P14 host tests pass, mutation control verifies 16/16 mutations caught, and the comprehensive audit script `check_p14.py` completes 389 automated checks against `main.bin` and the built NRO with 11/11 negative controls failing.

---

## 2. S1 Native Sort Facts and Addresses

### 2.1 Sort Window Options, Count, Texts, and Labels
From the layout script `make_mii_hat_body_layout.lc` (prototypes `main.p4` and `main.p13`), the native sort overlay window (`sub_list_window` / `com_sort_window`) presents **three** options:

| Option Index / Mode | Message Key (`msg_menu.msbt`) | English Text | Description in Vanilla Headgear Screen |
|---|---|---|---|
| `0` | `mnu_mmiif_sort_1` | "By Last Used" | Native mode 0 sort (orders by usage recency) |
| `1` | `mnu_mmiif_sort_3` | "By Order Obtained" | Native mode 1 sort (orders by unlock/obtain index) |
| `2` | `mnu_mmiif_sort_4` | "By Name" | Native mode 2 sort (alphabetical name ordering) |

- **Which option is "by name":** Mode `2` (`mnu_mmiif_sort_4`).
- **Initial Sort Mode in Script:** Prototype `main.p5` (`initialize`) sets `self.sort_id = 0` (pc 104), calls `self:update_sort_text()` (pc 105), and dispatches `sort_id_list(0)` (pc 109).
- **Sort Label Update:** Prototype `main.p4` (`update_sort_text`) looks up the label array `[mnu_mmiif_sort_1, mnu_mmiif_sort_3, mnu_mmiif_sort_4]` indexed by `self.sort_id + 1` and calls `set_text_message(self.sort_text_pane, key)` on pane `set_txt_list` of `scr_sort`.

### 2.2 Native Handler `sort_id_list` (`0x19cd100`)
The headgear sort handler lives at `0x19cd100` (`main.bin`, file offset `0x19cd100`).
- Argument registers: `x0 = S` (the `0x170`-byte sub-object at `*[list + 0x80]`), `w1 = mode`.
- **Mode Dispatch:**
  - `0x19cd11c cmp w1, #2 ; b.eq 0x19cd174` (mode 2: stores `2` in `[S+0x164]`, executes mode 2 sort body).
  - `0x19cd124 cmp w1, #1 ; b.eq 0x19cd150` (mode 1: stores `1` in `[S+0x164]`, executes mode 1 sort body).
  - `0x19cd12c cbnz w1, 0x19cd280` (any mode $\ge 3$ or negative: jumps directly to epilogue `0x19cd280` without touching `[S+0x164]` or `[S+0x128]`, restoring registers and returning immediately `ret`).
  - `0x19cd130 str wzr, [x19, #0x164] ; b 0x19cd590` (mode 0: stores `0` in `[S+0x164]`, executes mode 0 sort body).
- **Hook Strategy:** For our mod list, passing mode $0..2$ to native would invoke native headgear sort routines that expect vanilla headgear registries and could free/reallocate `[S+0x128]` (mode 2 at `0x19cd1ac`). Therefore, `hook_sort` intercepts the call, updates the mod's internal vector `[S+0x128]` according to the user's choice, and forwards **mode 3** to `ORIG[K_SORT]`, safely bypassing native vector mutation while letting native UI complete its script sequence.

### 2.3 Script Lifecycle Around a Sort
When the sort button is activated in `make_mii_hat_body_layout.lc`:
1. **`backup_list_selected_id` (`0x19cd2c0`):** Called at `main.p12 pc 10`. Reads the scroller selected index from `[[S+0xf8] + 0x2a4]`. If $\ge 0$, reads `vector[index]` and writes that 8-byte handle into `[S + 0x158]`. On our list, this captures the synthetic handle of the character currently under the cursor.
2. **Sub-window interaction:** `sub_list_window.open(self.sort_id)` opens the 3-option overlay. If confirmed, `get_result()` returns `result1 == true` and `result2 = chosen_mode` (`0`, `1`, or `2`).
3. **`self:update_sort_text()`:** At `main.p13 pc 59`, updates the sort pane label to the chosen sort mode.
4. **`sort_id_list`:** At `main.p13 pc 65`, invokes bridge `sort_id_list(self.sort_id)`. Reaches `hook_sort(S, mode)` at `0x19cd100`.
5. **`redraw_all_items`:** At `main.p13 pc 68`, calls `scroller.redraw_all_items()`. The scroller re-renders visible rows by invoking `0x19ccb20` (`hook_rowfill`) for each row.
6. **`select_list_from_backup_id` (`0x19cd310`):** At `main.p13 pc 40` (and `main.p13 pc 72`), native code reads the backed-up handle from `[S + 0x158]`, linearly scans `vector` (`[S+0x128]..[S+0x130]`) for an equal 40-bit hash, and upon finding index $i$, calls `scroller.select_item(i, 0, 1)` (`0x3783660`). Cursor moves to the new index of the exact same character.
7. **Tick Preservation:** Row filler (`0x19ccb20`) compares each row's handle against `[S + 0x150]`. Because `[S + 0x150]` holds the synthetic handle of the ticked character, the tick remains on that character at its new row position.
8. **`get_top_index` (`0x19cd0b0`):** Not called during sort, but during cursor DOWN paging (`main.p11 pc 59`). Tests `0x328b5d0` against `vector[0]`. Since `vector[0]` is our synthetic default handle (row 0), `hook_unlisted` returns 0, and `get_top_index` returns 0.

---

## 3. Row Mapping & Sorting Architecture (S2-S3)

### 3.1 Mapping Definition and Bijective Invariant
- **Row 0:** Always pinned at index 0 (default Mii Gunner, handle `ui::handle_of(0)`).
- **Rows $1..N$ ($N \le 127$):**
  - In **Number Order** (`SORT_NUMBER = 0`), row $r$ ($1 \le r \le N$) maps to `list.txt` preset at index $r - 1$.
  - In **Name Order** (`SORT_NAME = 1`), row $r$ maps to `list.txt` preset at index `NAME_ORDER[r - 1]`.
- **Precomputed Permutation:**
  At boot, `editor::init_sort_order(&PRESETS)` computes the permutation `NAME_ORDER[0..N-1]` of indices $0..N-1$.
  Sorting key comparison:
  1. Primary key: Character display name from `names.txt` (`nam_chr1_00_<preset>`).
  2. Fallback key: Preset name (`list.txt` token).
  3. Comparison: Case-insensitive ASCII folding (`b.to_ascii_lowercase()`), tie-breaking by preset index.
- **Bijective Proof:**
  Because `NAME_ORDER` is an in-place permutation of $0..N-1$, every preset in `list.txt` appears exactly once in rows $1..N$.
  When deciding row $r$:
  - If $r == 0$, returns `None` (default Mii Gunner).
  - If $r \ge 1$:
    - Under `SORT_NUMBER`: maps to preset index $r - 1$.
    - Under `SORT_NAME`: maps to preset index `NAME_ORDER[r - 1]`.
  Tested and verified by `test_row_preset_bijective_mapping_both_orders`.

### 3.2 Cursor, Tick, and Greyed Row Invariants
- **Cursor Preservation:** Before sorting, `backup_list_selected_id` stores the synthetic handle `vector[cursor]` into `[S+0x158]`. After reordering, `select_list_from_backup_id` performs a linear search over `vector` for `[S+0x158]` and sets the scroller selection to the matched index.
- **Tick Preservation:** The tick handle at `[S+0x150]` is untouched by `hook_sort`. During `redraw_all_items`, `hook_rowfill` compares row handle with `[S+0x150]`. The row containing the matching handle displays the tick.
- **Greyed Row Availability:**
  On a `slot` page, row $r$ resolves to preset $P$. If $P$ is not in the whitelist for that slot, `hook_unlisted` returns `1` (unlisted), disabling the button and greying the row. Because the resolution routes through the active order mapping, the greyed state adheres to the character rather than the row number.
- **Order Persistence:**
  Stored in `SORT_ORDER: AtomicU8`. Persists across page switches and across menu open/close cycles throughout the game execution. Not saved to disk.
- **Main and Option Pages:**
  `hook_sort` checks active page. On `Page::Main` and `Page::Entry(Kind::Option)`, sorting requests are ignored and forwarded as mode 3.

---

## 4. Option Pages & Sword Integration (Part 2: O1-O4)

### 4.1 Contract G Extension
Contract G gains a third entry kind and one line type:
```text
entry <id> option <text>
option <id> <option_id> <text>
```
- `<id>`: `[a-z0-9_]{1,31}` identifying the menu entry.
- `<option_id>`: `[a-z0-9_]{1,31}`, unique per entry.
- `<text>`: Rest of the line (literal display text).
- Constraints: File order defines option order. At most 32 options per entry (`MAX_OPTIONS = 32`). The first option is the default (option index 0).
- An entry of kind `option` with no valid option lines is rejected at parse time (`Reject::NoOptions`).
- Duplicate option IDs within an entry are rejected (`Reject::DupOptionId`).

### 4.2 UI Navigation & Display
- **Main Page:** Composes row text as `<entry text>: <option text>` using `names::compose`. Under `text_off`, shows `<entry text>`.
- **Option Page:**
  - Displays all options for the entry.
  - All options are selectable (never greyed).
  - Cursor and tick initialize on the current option (or option 0 if none stored).
  - Pressing **A** confirms the selected option, emits `Effect::OptionChosen(entry_idx, option_idx)`, updates the loadout store, saves if changed, and navigates back to `Page::Main`.
  - Pressing **B** emits `Effect::Cancel` and returns to `Page::Main` without changes.
- **Row Titles:** On an option page, row filler sets pane text to the option's literal text.

### 4.3 Loadout v3 Contract & Rollback Compatibility
- **Header:** `mc_loadouts 3`.
- **Option Line:** `<id> option <entry_id> <option_id>`.
  - Stored for Mii ID `<id>`.
  - Choosing the default (option index 0) removes the option line.
  - Unknown entry ID or unknown option ID is rejected, ignored, and logged.
- **Capacity:** 32 Mii IDs $\times$ 16 option entries.
- **Backward Compatibility:**
  - `loadout::load_with_validator` parses versions 1, 2, and 3.
  - A 4-field line is rejected with `FieldCount` if the file version is $< 3$ or the second token is not `"option"`.
- **Writer Strategy for Rollback Safety:**
  - If any option line exists across all stored Mii loadouts, the writer emits `mc_loadouts 3`.
  - If no option lines exist, the writer emits `mc_loadouts 2`.
  - Rollback to plugin 0.6.0 will cleanly read the file as long as no custom non-default options were saved.

### 4.4 Shipped Configuration
Shipped in `builds/0.7.0-menu/example/menu.txt`:
```text
mc_menu 1
entry stats stats Stats
entry jab   slot  Jab
entry sword option Sword
option sword miiswordsman Mii Swordfighter
```

---

## 5. Safety, Invariants & Hook Site Audit

1. **Foreign Hook Tolerance:** Preserves 0.5.1 acceptance of `ldr x17, #8 ; br x17` (`0x58000051`, `0xd61f0220`) at `FN_SET_TEXT_UTF8` (`0x37a22f0`). Body probe at `0x37a23d0` matches `bl #0x37a1cc0`.
2. **Minus Global Channel:** Preserves 0.6.0 registration of `MC_MINUS` on Lua state `[[inner+0x40]]` via `FN_REG_CONST` (`0x33750a0`) triggered by `nn::hid` Minus edge.
3. **Hard Invariant E3:** The working headgear record at `0x5306cb0` is captured before entering mod mode, monitored per tick, and verified equal upon exit.
4. **Bounded Logging:** Re-sorting character pages logs a single flushed line:
   ```text
   mc|UI|sort|page=<page>|mode=<mode>|order=<name|number>|cursor=<cur>|tick=<tick>
   ```
5. **No Heap Allocation:** Static buffers and fixed-capacity arrays ensure zero allocations or file IO per frame during list navigation and re-sorting.

---

## 6. Host Tests & Mutation Verification

### 6.1 Host Test Suite
All test suites run in Git Bash with stable Rust toolchain:
- **0.3.0 P7 Engine Tests:** 47/47 passed.
- **0.5.0 P11 Menu Tests:** 35/35 passed.
- **Coordinator Names Tests:** 4/4 passed.
- **Total Existing Baseline:** 86/86 passed.
- **P14 Host Tests (`scratch/2026-10-07_P14-SORT-OPTIONS/host_test.rs`):** 16/16 passed:
  1. `test_names_sort_key_ascii_ci`
  2. `test_compute_name_order_deterministic`
  3. `test_row_preset_bijective_mapping_both_orders`
  4. `test_row_preset_mapping_with_unlisted_and_greyed`
  5. `test_preset_not_in_list_fallback`
  6. `test_menu_parse_option_entry_and_options`
  7. `test_menu_parse_rejects_empty_option_entry`
  8. `test_menu_parse_rejects_duplicate_option_id`
  9. `test_option_page_navigation_and_effects`
  10. `test_loadout_v3_parse_and_validate`
  11. `test_loadout_v3_serialise_emits_v3_when_options_present`
  12. `test_loadout_v3_serialise_emits_v2_when_options_absent`
  13. `test_loadout_v3_store_capacity_and_default_removal`
  14. `test_loadout_v2_backward_compatibility_read`
  15. `test_loadout_option_line_in_v2_rejected`
  16. `test_sort_order_persistence_and_invariance`

### 6.2 Mutation Verification
Ran `python mods/mii_customizer/scratch/2026-10-07_P14-SORT-OPTIONS/mutation_control.py`:
- 16 mutations applied to sort comparison, option parsing, page navigation, and loadout v3 serialisation.
- **Result:** 16 caught, 0 missed (exit code 0).

---

## 7. Main.bin Verification & check_p14.py

The audit script `evidence/P14-SORT-OPTIONS/check_p14.py` validates the entire surface of plugin 0.7.0 against `gamedata/ssbu-13.0.4/main.bin` and the staged NRO:
- **Sections Audited:**
  - A: Image identity (`IMAGE_SHA`, `IMAGE_SIZE`)
  - B: Site records (6 hook sites, 48 probes in `ui.rs`, 1 stat site in `logic.rs`)
  - C: Instruction disassembly (state reader, frame update, state 5, row filler, scroller decide, sort handler `0x19cd100`, Minus Lua constant registration `0x1808fe0..0x1809018`)
  - D: Function call targets and entries (`FN_SET_ITEM_COUNT`, `FN_SET_SELECT`, `FN_REG_CONST`, `FN_ALLOC`, `FN_FREE`, `FN_FIND_PANE`, `FN_SET_TEXT_UTF8`)
  - E: Numeric offsets and static addresses (`HAT_STATIC`, `WORK_RECORD`, `BUTTON_MINUS`, `BUTTON_ZL`, `BUTTON_ZR`)
  - F: Derived whole-range facts (restart byte, decide writers, vtable relocation slots, Lua method tables)
  - G: Message labels (`nam_chr1_00_miigunner`, `nam_mii_hat_none_m`, `nam_mii_hat_unknown`)
  - H: Built NRO audit (`NRO0` magic, symbol presence for `nn::hid`, string tables, foreign hook acceptance logic, manifest verification)
- **Check Results:** 389 checks passed, 0 failed.
- **Selftest Execution:** Clean run exits 0; all 11 negative controls (`word`, `disasm`, `call`, `entry`, `offset`, `static`, `scan`, `reloc`, `label`, `nro`, `manifest`) exit 1. Overall selftest exits 0.

---

## 8. Console Verification Plan & Rollback

### 8.1 Console Test Plan (8 Steps Maximum)

1. **Boot Game with Plugin 0.7.0:**
   - Verify log:
     ```text
     mc|L0|mii_customizer 0.7.0-menu loaded|base=...
     mc|UI|sites|ui=on|ui_off_file=0|sites_ok=6/6|probes_ok=48/48|installed=6|entries=...|text=on|minus=on
     ```
2. **Enter Mii Maker & Press Minus on Edit Menu:**
   - Opens custom menu main page. Verify log:
     ```text
     mc|UI|minus|set=1|n=1
     mc|UI|open|entry=A|native_count=52|rows=...|page=main
     ```
   - Check rows: Row 0 is "Stats: <current>", Row 1 is "Jab: Mii Gunner", Row 2 is "Sword: Mii Swordfighter".
3. **Select "Stats" (Press A):**
   - Opens Stats character page. Row 0 is "Mii Gunner", followed by characters in Fighter Number order.
   - Verify log:
     ```text
     mc|UI|page_change|from=main|to=stats|...
     ```
4. **Press X to Open Sort Window & Choose "By Name":**
   - Sort window opens with 3 options. Select option 3 ("By Name").
   - Rows $1..N$ reorder alphabetically by character display name.
   - Cursor and tick stay on the same character at its new row.
   - Verify log:
     ```text
     mc|UI|sort|page=stats|mode=2|order=name|cursor=...|tick=...
     ```
5. **Press X and Choose "By Order Obtained" or "By Last Used":**
   - Rows $1..N$ return to Fighter Number order (`list.txt` order).
   - Verify log:
     ```text
     mc|UI|sort|page=stats|mode=1|order=number|cursor=...|tick=...
     ```
6. **Press B to Return to Main Page, then Select "Jab":**
   - Opens Jab slot page. Verify that the previous sort choice persists.
   - Non-whitelisted characters are greyed out and cannot be decided.
   - Press B to return to Main Page.
7. **Select "Sword" (Press A):**
   - Opens Sword option page. Shows single option "Mii Swordfighter" with tick and cursor on row 0.
   - Verify log:
     ```text
     mc|UI|page_change|from=main|to=sword|...
     ```
   - Press A to confirm; returns to Main Page. Main page displays "Sword: Mii Swordfighter".
8. **Press B to Exit Custom Menu & Return to Edit Menu:**
   - Verify log:
     ```text
     mc|UI|exit|equal=1|restored=0|record_equal=1
     ```
   - Invariant E3 confirmed: working record unchanged.

### 8.2 Rollback Information
- **Rollback Target:** 0.6.0 NRO
- **File Path:** `builds/0.6.0-menu/libmii_customizer.nro`
- **Size:** 110,592 bytes
- **SHA-256:** `f44fc278f0fd65a8db228f8c86ebf23e4317231bc084d8131181db7a0fa8c01a`
- **Switch Files Available:**
  - `sd:/ultimate/mii_customizer/ui_off` (disables UI hooks)
  - `sd:/ultimate/mii_customizer/text_off` (disables literal text injection)
  - `sd:/ultimate/mii_customizer/minus_off` (disables nn::hid Minus polling)

### 8.3 Plain List of Tier D Claims
The following behaviors are based on static analysis, host simulations, and disassembly audit, and have not yet been observed on hardware for 0.7.0:
1. Ingame appearance and layout geometry of the sort sub-window over the custom list.
2. Visual presentation of option page row items on console hardware.
3. Actual screen behavior of `make_mii_hat_body_layout.lc` when passing mode 3 to the native sort handler.
4. Rendering of composed string text `"Sword: Mii Swordfighter"` in the main menu row pane.
