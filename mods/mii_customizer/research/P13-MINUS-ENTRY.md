# P13-MINUS-ENTRY

> **Coordinator review, 2026-10-07.** PARTIAL as stated: no index-to-button mapping, no chunk,
> no check script. Two corrections: (1) the disassembler path in the prompt was
> `mods/mii_customizer/scratch/2026-10-04_P1-ID-REVIEW/d.py`; the worker looked under
> `mods/ssbu_mod_new/` and concluded it was absent. (2) "No clean existing channel from the
> plugin to this script" is wrong: the scene builder sets this script's integer globals with
> `0x33750a0(state, name, "i", value)`, state = `[[inner+0x40]]`
> (`0x1808fe0..0x1809018`, read by the coordinator), the same call the plugin already makes
> on the list script (`item_num_set=1`, tier A). Plugin 0.6.0 uses it: nn::hid Minus edge in
> the dispatcher hook -> global `MC_MINUS = 1` for two frames -> the script's own exit path
> with value 7. So the script still tears itself down normally, which answers the report's
> A3 concern. Whether any virtual index carries Minus stays unknown and is no longer needed.
> The handler facts of A1 (state words at `+0x198 + 4*index`) were not rechecked.

Status: PARTIAL. This offline pass resolved the Lua query shape and existing exit lifecycle, but not the physical-button-to-virtual-index binding. No entry chunk was built because the requested B deliverable depends on that distinction. No plugin edits, emulator run, console run, SD access, commit, branch, or agent delegation.

## Short answers

- A1: **unresolved**. The edit scene registers `INPUT_FAVORITE` as virtual index 7, but the native query handler reads a per-object indexed state array; available offline evidence does not connect any index to physical Npad Minus bit 11. The `INPUT_*` inventory has no `INPUT_MINUS` name. Do not ship a Minus-specific Lua test based on a guessed index.
- A2: the stock edit script's Favorite branch calls `switch_favorite` under `not FROM_AMIIBO`; the existing entry variant diverts only Favorite on Headgear. No Minus-specific behavior is established.
- A3: a dispatcher-only write of native exit value 7 is insufficient evidence that the Lua coroutine exits through its own teardown. Recommended route if A1 stays negative: a script-visible Minus query for this actor followed by the normal Lua exit path; prove binding attachment and teardown before packaging.
- Part B: not built; its trigger index is unresolved.

## Method and evidence

### Step 0 - scope and baseline

- Read workspace `AGENTS.md`, `kb/INDEX.md`, `mods/mii_customizer/AGENTS.md`, and `STATUS.md` [verified: read 2026-10-07].
- Read the applicable prior research `P5-UI-API.md` (section 8.2), `P9-EDIT-DISPATCH.md` (sections 3-5), and `P4-BRIDGE-FACTS.md`, plus the Lua source README, generator, existing entry source and build/negative-control scripts [verified: read 2026-10-07].
- Baseline target chunk exists at `gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc` (10,576 bytes); the pinned main image exists at `gamedata/ssbu-13.0.4/main.bin` (86,672,752 bytes) [verified: filesystem metadata].
- Before invoking the referenced disassembler under `mods/ssbu_mod_new`, read that repository's `AGENTS.md`, handbook index and project status, per workspace rule [verified: read 2026-10-07]. No files in that repository were changed.
- `main.bin` hash from P5-UI-API: `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613` [verified by the prior manifest; not independently rehashed in this task].
- The prompt's disassembler path `mods/ssbu_mod_new/scratch/2026-10-04_P1-ID-REVIEW/d.py` is absent in this checkout (`python ... d.py win 0x19e0910 80` exited 2: “can't open file”). After reading that repository's `AGENTS.md`, a one-off Capstone scan in `scratch/2026-10-07_P13-MINUS-ENTRY/scan_main.py` recovered relevant input code windows from the flat image.
- Extracted the edit layout archive to the authorized task output: 927,100 bytes, sha256 `f4bf2ef0db472eb341d76c70f3ec770ae58598fff3f53d2aced7170fb4ebf212`. Its `layout.info` contains animation names and `set_btn_keyhelp_00`, not a physical input map; this extraction does not settle the missing binding.

## Part A - input and dispatch facts

### A1 - native virtual input

**Measured offline (tier B):** P5-UI-API section 8.2 lists 28 registered `INPUT_*` globals and values. It has no `INPUT_MINUS` or other name explicitly denoting Minus. The edit scene registers `INPUT_FAVORITE` with value 7 at `0x1809004..0x1809018` (string at `0x4306e80`, `mov w3,#7` at `0x1809014`). Another context registers that global with value 8 at `0x19d38fc..0x19d3910`. These are virtual indices, not demonstrated physical Npad bit numbers.

The `is_pressed` handler at `0x33525e0` obtains the integer input index, computes `index*4`, reads the word at input-object offset `+0x198+index*4`, and returns bit 1 (`ubfx ..., #1, #1`, `0x33526c8..0x33526e8`). The corresponding `is_released` handler at `0x3352750` reads the same indexed word and extracts bit 2 (`0x3352838..0x3352850`). `is_pressing` at `0x33528c0` reads a parallel indexed word at `+0x264+index*4` and extracts bit 4 (`0x33529a8..0x33529c0`). The adjacent `is_cancel` handler at `0x3352560` reads bit 1 from `+0x1ac`. Handler/name association is from the native input-method table around `0x3ea5e00..0x3ea5eb0`; instruction behavior is read from the pinned main image. This establishes object-owned logical-state arrays, **not** which physical button populates each slot. The edit script obtains `virtual_input` from `layout_root:get_virtual_input()`; neither this handler code nor the inspected `layout.info` proves a slot-to-Npad mapping.

Therefore “no script constant named Minus” is verified, but “no virtual index carries Minus” is **not** established. Mapping all 28 names to physical buttons, the exact `is_pressed` / `is_pressing` / `is_released` handler-name association, and the edit menu object's enabled indices remain unresolved. The supplied clue that Npad Minus is bit 11 does not bridge those gaps. This prevents a safe B1 index choice.

### A2 - existing edit-menu reaction

**Verified from source:** stock `edit_state.update` checks `is_cancel()`, then `is_pressed(INPUT_COMMON_BUTTON)` (calls `ComFrameActor.press_decide()`), and then, only under `not FROM_AMIIBO`, checks `is_pressed(INPUT_FAVORITE)`, invokes `switch_favorite`, and sets `is_changed=true`. There is no focus condition in the stock Favorite behavior. The earlier generated `entry` source intercepts Favorite only when `selector0` is focused on row 1; it publishes 7 and returns before `switch_favorite`. The reported tier-A boot evidence establishes that exit value 7 is benign without the plugin; this pass did not repeat that test.

### A3 - plugin dispatcher route and script exit behavior

**Verified offline from `research/P9-EDIT-DISPATCH.md` and current plugin source:** `hook_dispatch` calls `before_dispatch(scene)` before original `0x180a030`. `before_dispatch` requires `READY`, a nonzero scene frame counter (`scene+0x14c`), a non-null edit wrapper/inner object, and nonzero `+0x130`; it reads `[[scene+0x178]+0x80]+0x128`. The scene's `+0x130` flag gates whether dispatch reads the value. The Lua native callback at `0x19ca590` sets `+0x130` and stores `get_exit_value()` into `+0x128` each frame. Value 7 is valid (state 11); the existing plugin rewrites 7 to 1 before dispatch.

To make Minus end the **script**, a native value write must be accompanied by a script-visible decision that causes `edit_state:update()` to return `true`, and must be observed by the dispatcher after the script callback has stored the result and raised `+0x130`. A dispatcher-entry write alone does not establish that ordering. After an update returns true, Lua disables layout input, clears the footer except for Try, waits for the `out` animation, disables input again and hides the layout (source lines 430-460). Skipping those steps could leave an active or visible edit actor under the pushed menu; static evidence cannot call that safe.

P4's `get_skill_id` / `set_skill_id` delegates are registered in the special-move actor's binding setup (for example the get registration at `0x19de19c..0x19de1b4`). No evidence shows those delegates are installed in the edit actor's Lua environment or callable by this chunk; they are not a clean existing channel. **Recommended mechanism if A1 stays negative:** add a dedicated script-visible Minus query to this actor's host binding and let `edit_state.update` take an explicit exit-7 return path. Before packaging, prove the callback is bound to this actor, reads the intended controller and edge, runs before ordinary selection logic, is suppressed for `FROM_AMIIBO`, and lets the normal Lua disable/footer/out/hide sequence complete before the dispatcher consumes value 7. This is a proposal with proof obligations, not implemented or runtime-verified.

## Part B - deliverable

Not built. A source variant cannot choose a physical Minus index until A1 is resolved. The Favorite-on-Headgear block remains in the generated source, and no chunk is staged under `builds/0.6.0-edit-minus/`.

## Verification and limitations

- Offline checks: prior P5/P9 reports were read; the edit `layout.arc` extraction matches its pinned 927,100-byte hash. One-off source inspection confirmed indexed state access. The physical mapping remains unresolved. `build_check.py`, `negative_controls.py` and B-stage checks were not run because there is no candidate variant.
- Tier A console behavior: not tested in this task; player-visible behavior remains tier D until a console run.
- Tier B offline evidence: input global registrations and indexed state-array access were read from the pinned main image; see A1. No B-stage package evidence.
- Console test plan (maximum five steps), for the eventual integrated build: (1) open the Mii edit menu; (2) press Minus on Headgear and confirm the mod menu opens without toggling Favorite; (3) return and repeat from another row; (4) repeat from Random and Try focus; (5) press Favorite on Headgear and confirm it only toggles Favorite. All player-visible outcomes remain tier D pending the user's console run.
- Rollback: `builds/0.4.0-edit-entry/variant_entry`.

## Final report

- Task ID: P13-MINUS-ENTRY
- Status: PARTIAL
- Changed files: `research/P13-MINUS-ENTRY.md`; one-off scanner scripts in `scratch/2026-10-07_P13-MINUS-ENTRY/`; extracted layout files in `gamedata/mii_customizer/P13-MINUS-ENTRY/`.
- Could not verify: complete physical-button mapping for every virtual index; whether any edit-menu index carries Minus; whether P4 skill bridges are callable from the edit chunk; teardown safety for dispatcher-only injection; any packaged variant; player-visible behavior.
