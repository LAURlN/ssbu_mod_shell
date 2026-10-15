# P13-MINUS-ENTRY - result

Task ID: P13-MINUS-ENTRY  
Date: 2026-10-07  
Status: **PARTIAL**  
Evidence: offline tier B where marked; player-visible behavior remains tier D.

## Findings

- `P5-UI-API.md` section 8.2 reports 28 `INPUT_*` globals and their registration values. None is named `INPUT_MINUS`. In the edit scene, `INPUT_FAVORITE` is registered as index 7 (`main.bin` `0x1809004..0x1809018`, string `0x4306e80`, `mov w3,#7` at `0x1809014`). Another context registers it as 8 (`0x19d38fc..0x19d3910`). Tier B.
- Native handlers: `is_pressed` at `0x33525e0` reads `+0x198 + 4*index`, bit 1 (`0x33526c8..0x33526e8`); `is_released` at `0x3352750` reads the same indexed words, bit 2 (`0x3352838..0x3352850`); `is_pressing` at `0x33528c0` reads `+0x264 + 4*index`, bit 4 (`0x33529a8..0x33529c0`). The adjacent `is_cancel` handler `0x3352560` reads bit 1 at `+0x1ac`. Method names are associated through the native input-method table around `0x3ea5e00..0x3ea5eb0`. These are logical per-object states, not physical Npad mappings. `INPUT_FAVORITE` being 7 therefore does not prove it is physical bit 7 or Minus bit 11.
- The edit script obtains `virtual_input` from `layout_root:get_virtual_input()`. The extracted edit `layout.info` only names layout animations and key-help parts. No per-index physical mapping or enabled-index list was recovered.
- The stock edit script checks Favorite only when `not FROM_AMIIBO`, invokes `switch_favorite`, and sets `is_changed`. The earlier entry variant intercepts that press only for focused row 1. Source inspection; not a new runtime observation.
- At dispatcher entry, the plugin checks frame state, the `+0x130` has-value byte, and exit value `[[scene+0x178]+0x80]+0x128`; value 7 is valid and is rewritten to 1. The Lua side's own exit path disables input, clears the footer except for Try, plays/waits the `out` animation, disables input and hides the layout. A native write alone does not prove that this Lua path ran.
- P4's skill bridge registration is tied to the special-move actor. No evidence establishes that the edit actor chunk can call those handlers.

## Inputs and commands

- `gamedata/ssbu-13.0.4/main.bin`, 86,672,752 bytes, SHA-256 `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613` (prior P5-UI-API identity; not re-hashed in this task).
- `gamedata/ssbu-13.0.4/data.arc` -> extracted `ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc`, 927,100 bytes, SHA-256 `f4bf2ef0db472eb341d76c70f3ec770ae58598fff3f53d2aced7170fb4ebf212`.
- Extracted `info/layout.info` (1,204 bytes, SHA-256 `cd7f655bd8968c6c65cc516c0d8b342853fbb336d42b2c418612a9f131239607`) and `blyt/make_mii_edit.bflyt` (21,004 bytes, SHA-256 `2668a7ecf146a31e5003df682208d21d3a4cd2d032d4d68e839dfe0853b6dd34`) under `gamedata/mii_customizer/P13-MINUS-ENTRY/`.
- Extraction: `tools/arc-extract/target/release/arc-extract.exe --arc gamedata/ssbu-13.0.4/data.arc --out gamedata/mii_customizer/P13-MINUS-ENTRY ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc`.
- Archive listing: `python mods/mii_customizer/tools/sarc-layout/sarc_layout.py list gamedata/mii_customizer/P13-MINUS-ENTRY/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc`.
- The requested `d.py` location did not exist. The command `python mods/ssbu_mod_new/scratch/2026-10-04_P1-ID-REVIEW/d.py win 0x19e0910 80` exited 2 with “can't open file”. After reading `mods/ssbu_mod_new/AGENTS.md` and its handbook index, one-off Capstone scans were kept under `scratch/2026-10-07_P13-MINUS-ENTRY/`.

## Recommendation and proof obligations

If a further offline pass confirms that no edit-menu virtual index carries Minus, expose a dedicated script-visible Minus query on the edit actor and take the normal Lua `exit_value = 7` return path. Prove the binding is available to this actor, the exact controller and edge semantics, decision ordering, `FROM_AMIIBO` suppression, and completion of Lua's input/footer/animation/hide teardown before dispatch consumes 7. Do not inject the native field directly until frame ordering and actor teardown have been proven.

## Not done / next experiment

The task cannot safely choose `INPUT_MINUS_INDEX` yet. Complete A1 by tracing how the `+0x198` per-index state words are populated from physical button bits for the edit menu's virtual-input object, including the controller configuration/scene scope and which slots are enabled. Then either build the additive Minus variant or, if no index carries Minus, build only the Favorite-removal variant and its requested checks. No plugin code was written.

No build candidate was created, so `build_check.py`, `negative_controls.py`, and the requested staged `check_minus.py` were not run. No emulator, console, or SD-card use. Proposed console test (five steps maximum) is in `research/P13-MINUS-ENTRY.md`; rollback is `builds/0.4.0-edit-entry/variant_entry`.
