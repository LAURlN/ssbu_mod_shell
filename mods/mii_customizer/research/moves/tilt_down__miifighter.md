# MV-tilt_down__miifighter - Mii Brawler's down tilt on Mii Gunner

Task ID: MV-tilt_down__miifighter
Status: DONE (unit built and checked offline). Nothing has run in the game: every in-game claim is tier D.
Date: 2026-10-07
Donor: `miifighter` (Mii Brawler), `gamedata/mii_customizer/COORD-session3/list.txt`
Entry: `tilt_down` (menu row "Down Tilt", `entry tilt_down slot Down Tilt` in menu.txt)
Unit: `tilt_down__miifighter`

Owned names (derived; used everywhere):
- Motion kind: `mc_miifighter_attack_lw3` (hash40 0x18ac7e2d91)
- Game script: `game_mcmiifighterattacklw3`; effect `effect_mcmiifighterattacklw3`; sound `sound_mcmiifighterattacklw3`; expression `expression_mcmiifighterattacklw3`
- Clip file: `c01mcmiifighterattacklw3.nuanmb` (donor clip `c02attacklw3.nuanmb`)

Evidence tiers used below: **B** = measured offline by a script named in the text; **D** = read or inferred, not run. Nothing is tier A.

## Coordinator banner (for the reader of this report)

- **P16-FTILT-MOVE has two errors in its expression scripts, found while doing this unit.** Its `expression_mcattacks3*` call `ControlModule::set_rumble(..., Hash40::new("rbkind_nohits"), 0, false, 0)`. The donor calls `rbkind_nohitm` (hash40 0x0db2772ed7, not 0x0d487813b4) with a fifth argument of `0x50000000`. Both facts are tier B (disassembly of `lua2cpp_miifighter.nro` at 0xdcd48 and 0xdccf4, same pattern as the down tilt; `rbkind_nohitm` confirmed in `mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv`). The in-game effect of this is unknown (tier D); it is a deviation from the copy recipe either way. This unit does not touch P16; the coordinator decides.
- The name `rbkind_nohits` is what P16 wrote, so its hash was never checked against the donor. Worth a check on the other P16 scripts too (effects and sounds were not re-checked here).

## 1. Facts (step 1)

### 1a. Donor motion entry (miifighter `motion_list.bin`, index 75) - tier B

Source: `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/motion_list.bin`, 45872 bytes, 764 entries, sha256 `424aded2eabeaadecb7fcbb6052ee38a3f7fdb330ce3831ada6620691ca9ed4e` (matches P12's record). Parsed by `scratch/2026-10-07_MV-tilt_down__miifighter/parse_mlist.py`; every name checked by `name_check.py` (all six MATCH).

| field | value |
|---|---|
| kind | `attack_lw3` 0x0a18b4d5e5 |
| game script | `game_attacklw3` 0x0e20f4361a |
| expression | `expression_attacklw3` 0x144ca51b98 |
| sound | `sound_attacklw3` 0x0fc04a23a5 |
| effect | `effect_attacklw3` 0x10e5d786fd |
| clip | `c02attacklw3.nuanmb` 0x13e14607b0 |
| flags | 0x0084 |
| blend | 0 |
| cancel frame | 28 |
| size | 28 |

Only one entry carries `attack_lw3`. There are no angled down-tilt variants (the forward tilt has three; this one has one). So the menu entry needs no stick-angle choice.

Clip: `fighter/miifighter/motion/body/c00/c02attacklw3.nuanmb`, 36472 bytes, sha256 `f0b1b4099cbfffb0b210e076295ff11239dfdcbab55b69c688f5df6f4bebac4b`, extracted from the user's `gamedata/ssbu-13.0.4/data.arc` with `tools/arc-extract` (tier B, into `gamedata/mii_customizer/moves/tilt_down__miifighter/extract/`). `final_frame_index` 41.0, so **42 frames** (forward tilt: 56).

### 1b. Donor ACMD scripts (decoded from `lua2cpp_miifighter.nro`, tier B)

Decoder: `scratch/2026-10-07_MV-tilt_down__miifighter/decode_acmd.py` (a copy of P12's decoder, pointed at the `attack_lw3` names; output `gamedata/mii_customizer/moves/tilt_down__miifighter/tables/acmd_calls.json`). Argument order checked against smash-script's `ATTACK`, `FOOT_EFFECT`, `EFFECT_FOLLOW_FLIP_ALPHA` macros (`~/.cargo/git/checkouts/smash-script-cb158d447e5f0892/fdc6144/src/macros.rs`, a tool install we were pointed to by P12). Constant values from the pinned `lua_const.rs` in the skyline-smash checkout. Every hash argument name re-hashed: `verify_names.py`, all OK.

Game script (`game_attacklw3`, impl 0x1500e0..0x150c54, 733 instructions):
- frame 2 (is_excute): `FighterAreaModuleImpl::enable_fix_jostle_area(boma, 0.0, 3.0)`.
- frame 7 (is_excute):
  - ATTACK id 0: part 0, bone `kneer`, damage 8.0, angle 80, kbg 90, fkb 0, bkb 50, size 4.0, offset (4.8, 0.0, 0.0), hitlag 1.0, sdi 1.0, setoff ON, LR check POS, trip 0.2, rehit 0, direct true, ground_air mask GA (3), hitbits ALL (63), collision part ALL (31), effect `collision_attr_normal`, sound level M (1), sound attr KICK (2), region KICK (6).
  - ATTACK id 1: identical except size 3.5 and offset (-2.0, 0.0, 0.0).
  - `AttackModule::set_attack_height_all(boma, ATTACK_HEIGHT_LOW, false)` (the constant is read from constant-table offset 0xe7c4, resolved to ATTACK_HEIGHT_LOW = 0x0).
- wait 2 (frames 7 to 9); frame 9: `AttackModule::clear_all`.
- frame 16 (is_excute): `enable_fix_jostle_area(boma, 2.0, 3.0)`.
- frame 26 (is_excute): `enable_fix_jostle_area(boma, 4.0, 3.0)`.
- Hitboxes are active frames 7 and 8, cleared at 9. Two hitboxes, not three.
- The `enable_fix_jostle_area` and `set_attack_height` arguments are not decoded by the tool (the `lua_bind` calls have no argument records). They come from disassembling the stack-object setup around each call (0x1501a0..0x1501d8, 0x150b0c..0x150b40, 0x150bf0..0x150c18, 0x150994..0x1509dc). Tier B by reading the instructions; not run.

Effect script (`effect_attacklw3`, 249 instructions):
- frame 6 (is_excute): `FOOT_EFFECT(sys_turn_smoke, top, 0,0,0, 0,0,0, 1.0, 0,0,0,0,0,0, false)`.
- frame 6: `EFFECT_FOLLOW_FLIP_ALPHA(sys_attack_arc, sys_attack_arc, top, -2.0, 2.0, 0.0, 180.0, -178.0, 0.0, 1.0, true, EF_FLIP_YZ, 0.3, 0, 0, false)`. The donor pushes 16 Lua values; the smash-script macro takes 13.

Sound script (`sound_attacklw3`, 78 instructions):
- frame 6: `PLAY_SE(se_miifighter_swing_l)`, `PLAY_SEQUENCE(seq_miifighter_rnd_attack01)`.

Expression script (`expression_attacklw3`, 328 instructions):
- start (is_excute): `slope(MA_MSC_CMD_SLOPE_SLOPE, SLOPE_STATUS_LR)`.
- frame 4: `slope(MA_MSC_CMD_SLOPE_SLOPE_INTP, SLOPE_STATUS_TOP, 3)`.
- frame 5: `ControlModule::set_rumble(boma, rbkind_nohitm, 0, false, 0x50000000)`.
- frame 7: `RUMBLE_HIT(rbkind_attackm, 0)`.
- frame 10: `slope(MA_MSC_CMD_SLOPE_SLOPE_INTP, SLOPE_STATUS_LR, 8)`.

Status: `FIGHTER_STATUS_KIND_ATTACK_LW3` = 0x2C (44) (lua_const.rs). Donor's tilt runs the common engine status. Static scan (`P12-FTILT-FACTS/tables/status_regs.tsv`, tier B as P12 produced it): no statically resolved registration of kind 0x2C in either `lua2cpp_miifighter.nro` or `lua2cpp_miigunner.nro`. **Not fully excluded:** each NRO has 37 registrations whose kind is `RUNTIME_VALUE(get_int)` and was not resolved by the scan. An override hidden behind one of those cannot be ruled out offline. Console test step 1 covers it (below).

### 1c. Gunner compatibility (stop condition check) - tier B

Script: `scratch/2026-10-07_MV-tilt_down__miifighter/compat2.py`. Gunner skeletons: `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_{m,f}/c00/model.nusktb` (71 bones each).

| check | result |
|---|---|
| transform nodes in the donor clip | 75 |
| of them, in the Gunner skeleton | 65 |
| not in the Gunner skeleton | 10: `FingerL14_eff`..`FingerL54_eff`, `FingerR14_eff`..`FingerR54_eff` (effect helper nodes) |
| skeleton bones not animated by the clip | 6: `H_ElbowL`, `H_ElbowR`, `H_KneeL`, `H_KneeR`, `H_WristL`, `H_WristR` (constraint helpers) |
| visibility nodes | 12: `MiiFighterM_eye_*` (9) and `MiiFighterM_mouth_*` (3) |
| **the Gunner's own `attack_lw3` clip** (extracted: `fighter/miigunner/motion/body/c00/c02attacklw3.nuanmb`, final_frame_index 50.0) | **same 75 transform node set and same 12 visibility node set** (set equality, check 10) |
| clip against the Gunner skeleton of the other gender | same result (`b_normalgunner_f`) |

So the donor clip drives exactly the nodes the Gunner's own down-tilt clip drives. This is not a retarget; the stop condition ("a different skeleton") is not hit.

Hitbox and effect bones:
- `kneer`: not a literal skeleton name in either Mii Gunner skeleton. The skeleton has `KneeR`. The Gunner's own vanilla `attack_lw3` hitbox uses the lowercase alias `armr` (decoded from the Gunner's own `game_attacklw3`, `ArmR` in the skeleton), so the engine maps lowercase alias names to skeleton bones. The unit uses `kneer` as the donor does. Tier B for the pattern; the mapping is not run in-game.
- `top`: engine origin (the Gunner's own down tilt uses it too). Not a skeleton bone.
- `armr` (the Gunner's own hitbox) is not needed by this unit.

### 1d. Dependencies beyond animation and hitboxes

| category | result |
|---|---|
| articles / weapons / projectiles | none (no `ArticleModule`, no spawn call in any of the four scripts) |
| grab / throw victim sets | none |
| work ids or params read by scripts | none (the `lua_bind` calls are AttackModule, FighterAreaModuleImpl, ControlModule only) |
| donor-only effects (not `sys_*`) | none. `sys_turn_smoke` and `sys_attack_arc` are `sys_*` and stay (rule). Offline check of their presence in `ef_common.eff` is **inconclusive**: `ef_common.eff` holds no ASCII `sys_` names and the control `sys_run_smoke` (used by the Gunner's own script) also misses, so the search method does not work on this file. Tier D for their existence on the Gunner. |
| donor-only sounds | `se_miifighter_swing_l` and `seq_miifighter_rnd_attack01`. **Absent** from the Gunner: `se_miifighter_swing_l` crc32 not in `se_miigunner.tonelabel`; `seq_miifighter_rnd_attack01` not in `miigunner.sqb` (tier B, `find_names.py`). Replaced by the Gunner's own labels (below). |
| extra statuses | none beyond `ATTACK_LW3` (taken over, see the status section) |

Stop conditions: none hit. The unit is buildable.

## 2. Unit (step 2)

Files (all written by this task):
- `moves/tilt_down__miifighter/unit.rs`: the four scripts (values as decoded), `register_acmd`, `start_attack_lw3`, `custom_dtilt_main`. No log helpers, no saved-Mii lookup, no `.status(...)`, no `.install()`.
- `moves/tilt_down__miifighter/unit.json`: the table in machine-readable form, with the known differences.
- `moves/tilt_down__miifighter/build_assets.py`: builds the package and the reference list (see below).
- Workspace `gamedata/mii_customizer/moves/tilt_down__miifighter/`:
  - `package/fighter/miigunner/motion/body/c00/c01mcmiifighterattacklw3.nuanmb` (36472 bytes, byte-identical to the donor clip)
  - `reference/motion_list_vanilla_plus_owned.bin` (46336 bytes = vanilla Gunner 774 entries + 1; the list the coordinator's merged patch must reproduce)
  - `manifest.json` (sizes, sha256 of every input and output, and the added entry's hashes)
  - `extract/` (the two donor/Gunner clips, from `tools/arc-extract`), `tables/` (decoder output)
- **Not written**, on purpose: `package/.../motion_list.bin`, `motion_list.motdiff`, `config.json`. The coordinator merges every unit.

Added motion entry (`build_assets.py` output, `manifest.json` "added_motion"):

| field | value |
|---|---|
| kind `mc_miifighter_attack_lw3` | 0x18ac7e2d91 |
| game `game_mcmiifighterattacklw3` | 0x1a4a92459a |
| expression `expression_mcmiifighterattacklw3` | 0x2067e7e9f3 |
| sound `sound_mcmiifighterattacklw3` | 0x1b3940d1e7 |
| effect `effect_mcmiifighterattacklw3` | 0x1c7f2e2faa |
| clip `c01mcmiifighterattacklw3.nuanmb` | 0x1f079d2381 |
| flags / blend / cancel / size | 0x0084 / 0 / 28 / 28 (copied from the donor entry) |

### Status taken over

`FIGHTER_STATUS_KIND_ATTACK_LW3` (44), `Main` only. `start_attack_lw3(fighter, vanilla)`:
1. If `MotionModule::is_anim_resource(boma, mc_miifighter_attack_lw3)` is false, return `vanilla` unchanged.
2. Otherwise `change_motion(mc_miifighter_attack_lw3, 0.0, 1.0, false, ...)` and `sub_shift_status_main(custom_dtilt_main)`.
3. `custom_dtilt_main`: cancel frame (28) runs `sub_wait_ground_check_common(false)`; leaving the ground goes to FALL; motion end goes to WAIT. This mirrors P16's `custom_ftilt_main` (tier D: the common `status_AttackLw3` was not decoded, so "the way the common status does" is P16's reading, not a checked copy).

The wrapper must call the vanilla Main first, then `start_attack_lw3`, only for a Gunner whose saved Mii chose `tilt_down` = `miifighter`. No stick angle and no stage: one motion.

## 3. Check (step 3)

`evidence/moves/tilt_down__miifighter/check.py`, run from the workspace root. Exit 0 only if all real checks pass and all three negative controls are detected.

Last run (2026-10-07, offline, exit 0):
```
1. package files          ok  (size and sha256 vs manifest.json)
2. reference list         ok  (774 + 1 = 775; kinds unique)
3-4. hashes, flags, cancel ok  (all six hashes; flags 0x0084; cancel 28 = donor)
5. ATTACK arguments       ok  (both hitboxes, all 36 arguments vs acmd_calls.json)
6-7. timing and values    ok  (frame/wait sequences of 4 scripts; jostle args; ATTACK_HEIGHT_LOW; rbkind_nohitm; 0x50000000)
8. bones                  ok  (kneer -> KneeR in both skeletons; top = engine origin)
9. sounds                 ok  (se_miigunner_attackhard_l01 crc32 and seq_miigunner_rnd_attack02 hash40 in the Gunner files; donor labels absent)
10. clip                  ok  (byte-identical to donor; node sets equal the Gunner's own clip; 42 frames)
11. negative controls     detected x3: corrupted manifest sha256; hitbox damage 9.9; corrupted motion record kind
ALL TILT_DOWN__MIIFIGHTER CHECKS PASSED
```

Known limit of the check: the values in check 6–7 for `enable_fix_jostle_area` and `set_attack_height` are compared with the disassembly results recorded in `unit.json` (the decoder cannot read those calls), so that part is only as good as the disassembly.

## 4. Build proof (the copy of the plugin)

Private copy: `scratch/2026-10-07_MV-tilt_down__miifighter/plugin/` (Cargo.toml and Cargo.lock identical to `plugin/`; `src/` copied; `src/tilt_down_miifighter.rs` = `unit.rs`).
- `cargo skyline build --release -- --offline`, `CARGO_TARGET_DIR=mods/mii_customizer/builds/.cache/MV-tilt_down__miifighter-target`, PATH as `build-plugin.sh`: **exit 0**, 1m34s, no errors, no warnings naming the unit. Log: `scratch/2026-10-07_MV-tilt_down__miifighter/build.log`.
- NRO (not a deliverable): `builds/.cache/MV-tilt_down__miifighter-target/aarch64-skyline-switch/release/libmii_customizer.nro`, 258048 bytes, sha256 `247c11314d1bad2c61f8f86b15d420aaa82376b51d4d6e11bfe4dfb77708780c`.
- `python tools/stack-frames/stack_frames.py <nro>`: **exit 0**; 129 frame allocations; largest 18672 bytes at 0xbad0 (limit 24576).

Diff of the copy against `plugin/` (the integration recipe, also saved as `scratch/2026-10-07_MV-tilt_down__miifighter/integration.diff`):

```diff
--- plugin/src/lib.rs
+++ copy/src/lib.rs
@@ -45,6 +45,7 @@
 mod logic;
 mod menu;
 pub mod moves;
+pub mod tilt_down_miifighter;
 mod names;
 mod preset;
 mod ui;

--- plugin/src/menu.rs
+++ copy/src/menu.rs
@@ -462,8 +462,9 @@
-pub const IMPLEMENTED_MOVES: [(&[u8], &[u8]); 1] = [
+pub const IMPLEMENTED_MOVES: [(&[u8], &[u8]); 2] = [
     (b"tilt_side", b"miifighter"),
+    (b"tilt_down", b"miifighter"),
 ];

--- plugin/src/moves.rs
+++ copy/src/moves.rs
@@ -395,4 +395,7 @@
         .expression_acmd("expression_mcattacks3lw", expression_mcattacks3lw, Priority::Default)
         .status(Main, *FIGHTER_STATUS_KIND_ATTACK_S3, gunner_attack_s3_main)
         .install();
+    let mut unit_agent = Agent::new("miigunner");
+    crate::tilt_down_miifighter::register_acmd(&mut unit_agent);
+    unit_agent.install();
 }
```
Plus the new file `src/tilt_down_miifighter.rs` (= `moves/tilt_down__miifighter/unit.rs`).

The copy does **not** wire the status wrapper (the coordinator's job; the prompt forbids the saved-Mii lookup in the unit). So `start_attack_lw3` compiles but is not called in the copy.

## 5. Integration recipe (for the coordinator)

1. Plugin: add `moves/tilt_down__miifighter/unit.rs` as `src/tilt_down_miifighter.rs`; apply the three hunks above (or the merged equivalents when more units are added). Keep `IMPLEMENTED_MOVES` in step with `menu.txt` `allow` lines.
2. Status wrapper: register `Main` for `FIGHTER_STATUS_KIND_ATTACK_LW3` (44) on `miigunner`. The wrapper calls `original_status(Main, fighter, 0x2C)(fighter)`, then, for a Gunner whose saved Mii has the `tilt_down` slot = `miifighter`, returns `crate::tilt_down_miifighter::start_attack_lw3(fighter, vanilla)`. The existing P16 wrapper handles only `ATTACK_S3` (42); both must dispatch from one status function per kind.
3. Menu: `entry tilt_down slot Down Tilt` is already in menu.txt. Add `allow tilt_down miifighter` to un-grey the row. Loadout line for a choice: `<id> slot tilt_down miifighter` (`mc_loadouts 3`, the same version the P16 slot uses).
4. Motion list: append the unit's entry to the ONE merged `motion_list.motdiff` (with P16's three entries, so the merged list must be 778 entries). Check it against a merged reference list.
5. ARCropolis `config.json`: `new-dir-files` for `fighter/miigunner/c00` gets `fighter/miigunner/motion/body/c00/c01mcmiifighterattacklw3.nuanmb` (merged with P16's three).
6. After merge: rerun this unit's `check.py` (needs the reference list), the stack-frame check, and the merged package's own checks.

## 6. Known differences from the donor

1. SE `se_miifighter_swing_l` -> `se_miigunner_attackhard_l01`: the SE the Gunner's own `attack_lw3` plays (its `sound_attacklw3` decodes to exactly this). crc32 present in `se_miigunner.tonelabel`. Tier B.
2. Sequence `seq_miifighter_rnd_attack01` -> `seq_miigunner_rnd_attack02`: the Gunner's own sequence for this move. The `attack01` index also exists in `miigunner.sqb`; `attack02` was chosen because the Gunner uses it here. Tier B for presence, D for which one sounds right.
3. Effects: none omitted. `sys_turn_smoke` and `sys_attack_arc` kept (rule for `sys_*`). Their existence on the Gunner is not verified offline (tier D).
4. `EFFECT_FOLLOW_FLIP_ALPHA`: 16 Lua values pushed by hand (the smash-script macro takes 13). The last three are `0, 0, false`, as the donor pushes.
5. Size values: the decoder typed FOOT_EFFECT's size and EFFECT_FOLLOW's size as integer 1; the unit pushes 1.0 (same number in the game's float read). Tier D on the game side only in the sense that it is not run.
6. Rumble kind `rbkind_nohitm` and u32 `0x50000000`: exactly the donor's values (P16 differs; see the coordinator banner).

Not a difference: the hitbox bone `kneer` (donor uses it on the Gunner's own skeleton via the alias).

## 7. Console test (for the user; at most 6 steps; nothing run yet)

Install only after the coordinator merges this unit with the others and the user says so.

1. Gunner A: Menu > Down Tilt > Mii Brawler (row reads "Down Tilt: Mii Brawler"). Gunner B (another saved Mii): leave Down Tilt at "Mii Gunner". Expected: loadouts file has `<id_A> slot tilt_down miifighter` and no line for B.
2. Match A (P1) vs B (P2) in training. A: neutral down tilt. Expected: Brawler's low kick, the sequence is 42 frames (not the Gunner's 50), two hits on the kick, 8.0% per hit, knockback angle 80 (nearly vertical). B: its own down tilt.
3. A: down tilt, then check the actionable frame: from frame 28 (cancel) the Gunner can walk, jump or shield, earlier than the Gunner's own down tilt (frame 37 in the forward-tilt analogue; not measured for down tilt).
4. A: down tilt on a shield and on a Gunner standing on a ledge; the low-attack height (ATTACK_HEIGHT_LOW) and jostle values should look like Brawler's.
5. Negative control: a third saved Mii (CPU or unsaved) performs the vanilla Gunner down tilt, no crash.
6. Reboot; loadouts line persists; then `moves_off` present: all Down Tilt rows grey / vanilla moves run with no crash.

Expected log lines: none are defined here (the coordinator's wrapper defines its own, as P16 did for `exec`/`missing`). Rollback: remove `sd:/ultimate/mods/mii_customizer_moves/` (the package), or create `moves_off`.

## 8. Open items (not verified; need the console or a later task)

- **Status override**: 37 runtime-kind registrations per NRO are unresolved in the P12 scan. A hidden `ATTACK_LW3` override cannot be excluded offline. Decision the console test should settle: the vanilla down tilt for a CPU must match the Gunner's own `attack_lw3` behaviour in step 5.
- **Effect names on the Gunner**: `sys_turn_smoke` and `sys_attack_arc` are not verified present (the offline name search cannot read `ef_common.eff`).
- **The common `status_AttackLw3`**: the ground / fall handling in `custom_dtilt_main` is P16's pattern, not a checked copy of the common status.
- **Unit `enable_fix_jostle_area` and `set_attack_height` arguments**: read from disassembly, not from the decoder.
- **P16 expression rumble**: `rbkind_nohits` and u32 `0` in P16 disagree with the donor (both forward and down). Not fixed here.
- P16's effects and sounds were not re-checked against the donor (out of scope).

## 9. Files, commands, and what was not checked

Created: the files listed in section 2, `evidence/moves/tilt_down__miifighter/check.py`, `research/moves/tilt_down__miifighter.md` (this file), the scratch folder `scratch/2026-10-07_MV-tilt_down__miifighter/` (parse, name, decode, disassembly, compat and label scripts; the plugin copy; `build.log`; `integration.diff`), the cargo target `builds/.cache/MV-tilt_down__miifighter-target/`, and the workspace `gamedata/mii_customizer/moves/tilt_down__miifighter/`.

Read but not written: `plugin/` (only copied), `mods/ssbu_mod_new/` (`dumps/decoded/arc_files.tsv`, `dumps/scripts/ParamLabels.csv`, `tools/nro_decomp/`, `builds/.cache/dk_cargo/python`; the decoder ran with `PYTHONDONTWRITEBYTECODE=1` so nothing was written there), the cargo checkouts (`smash-script`, `skyline-smash`, `smashline`), and `gamedata/`.

Not checked: game behaviour of any kind; the common status code; the effect files; the P16 effects and sounds; the menu's `allow` line and loadout key in the live plugin (only the table row is in the copy); the motion patch merge.
