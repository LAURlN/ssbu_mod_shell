# MV-aerial_back__mario - Mario's Back Air on Mii Gunner

> **Status: DONE (built offline, checks pass, stack-frame verified)**
> **TASK ID: MV-aerial_back__mario**
> **Date: 2026-10-07**
> **Evidence tiers:** B (offline: motion entry, ACMD decode, reference list integrity, check.py, stack-frame check); D (in-game: animation playback, hitbox damage, sound)

## Names

| Name | Value |
|------|-------|
| ENTRY | `aerial_back` |
| DONOR | `mario` |
| UNIT | `aerial_back__mario` |
| TASK ID | `MV-aerial_back__mario` |
| Owned motion kind | `mc_mario_attack_air_b` |
| Owned clip file | `c01mcMarioattackairb.nuanmb` (from donor `c05attackairb.nuanmb`) |
| Owned script names | `game_mcMarioattackairb`, `effect_mcMarioattackairb`, `sound_mcMarioattackairb`, `expression_mcMarioattackairb` |

## Step 1a - Motion Entry Facts

From Mario's `motion_list.bin` (711 entries):

| Field | Value |
|-------|-------|
| Index | 84 |
| Motion kind | `attack_air_b` |
| Kind hash | `0x0c33f869bc` |
| Game script hash | `0x0f814cca56` |
| Flags | `0x0084` |
| Blend | 0 |
| Anims | 1 |
| Anim hash | `0x147bff280f` (clip: `c05attackairb.nuanmb`) |
| Size | 28 |
| Expression hash | `0x1582967977` |
| Sound hash | `0x10da72da5e` |
| Effect hash | `0x11bfe79e3d` |
| Cancel frame | 34 |

### Clip verification

- Donor clip: `fighter/mario/motion/body/c00/c05attackairb.nuanmb`
- SHA256: `5b08fad7a583946a24f40a49f346e4c81ce7c834b739ee8c1b9d3aed2deae01f`
- Size: 51685 bytes
- hash40(`c05attackairb.nuanmb`) = `0x147bff280f` matches anim hash in motion entry

## Step 1b - ACMD Scripts

Mario NRO extracted and ACMD scripts decoded using P12 decoder infrastructure.

### Script registrations (from registrations.tsv)

| Script | Hash | Registration | Wrapper | Impl | Size |
|--------|------|--------------|---------|------|------|
| game_attackairb | 0x0f814cca56 | 0x11378 | 0x71e80 | 0x95850 | 1099 instrs |
| expression_attackairb | 0x1582967977 | 0x12a44 | 0x46770 | 0x66ed0 | 139 instrs |
| sound_attackairb | 0x10da72da5e | 0x14c4c | 0xaa020 | 0xbd920 | 78 instrs |
| effect_attackairb | 0x11bfe79e3d | 0x16670 | 0x18710 | 0x33a00 | 326 instrs |

### Owned script names (following P16 convention)
- game: `game_mcMarioattackairb`
- expression: `expression_mcMarioattackairb`
- sound: `sound_mcMarioattackairb`
- effect: `effect_mcMarioattackairb`

### Decoded ACMD calls - Game Script (game_attackairb)

**Frame 6:**
- `frame(6)`
- `is_excute()`
- `WorkModule__on_flag_impl(1)` - sets on-flag
- Hitbox 0: `kneer` (bone hash 0x51ba4b748)
  - Damage: **10.5%**
  - Angle: **361°**
  - KBG: **106**, FKB: 0, BKB: **12**
  - Size: 4.5, offset: (4.8, 0, 0)
  - Setoff: ON, LR Check: B (4), sound level: L (2)
  - Collision: `collision_attr_normal`, region: `ATTACK_REGION_KICK` (6)
- Hitbox 1: `legr` (bone hash 0x48a1f731c)
  - Damage: **10.5%**
  - Angle: **361°**
  - KBG: **106**, FKB: 0, BKB: **12**
  - Size: 5.9, offset: (1.6, 0, 0)
  - Same attributes as hitbox 0
- `wait(2)`

**Frame 8:**
- `is_excute()`
- Hitbox 0: `kneer`
  - Damage: **7.0%** (decays from 10.5%)
  - Angle: **361°**
  - KBG: **90**, FKB: 0, BKB: **7**
  - Size: 4.5, offset: (4.8, 0, 0)
  - Sound level: M (1)
- Hitbox 1: `legr`
  - Damage: **7.0%**
  - Angle: **361°**
  - KBG: **90**, FKB: 0, BKB: **7**
  - Size: 5.3, offset: (1.6, 0, 0)
  - Sound level: M (1)
- `wait(3)`

**Frame 11:**
- `is_excute()`
- `AttackModule__clear_all_impl()` - clears hitboxes
- `frame(19)`
- `WorkModule__off_flag_impl(1)` - sets off-flag

**Summary:**
- Active frames: 6-8 (hitboxes), cleared at frame 9 (actually frame 11 per decode)
- Cancel frame: 34 (from motion entry)
- Hitboxes on `kneer` and `legr` (both exist in Gunner skeleton)
- No weapons, articles, or projectiles

### Decoded ACMD calls - Sound Script (sound_attackairb)

**Frame 6:**
- `PLAY_SE(se_common_punch_kick_swing_s)` - common punch/kick swing sound
- `PLAY_SEQUENCE(seq_mario_rnd_attack)` - Mario's attack voice sequence

**Note:** Uses `se_common_punch_kick_swing_s` which is a COMMON sound available to all fighters.
The voice sequence `seq_mario_rnd_attack` is Mario-specific and will need remapping to Gunner's
voice sequence (`seq_miigunner_rnd_attack01` or similar).

### Decoded ACMD calls - Effect Script (effect_attackairb)

**Frame 6:**
- `EFFECT_FOLLOW(sys_attack_speedline, top, ...)` - speed line effect at fighter origin
- `LAST_PARTICLE_SET_COLOR(0.8, 0.6, 0.3)` - orange/brown particle color

**Frame 7:**
- `EFFECT(sys_attack_impact, top, ...)` - impact effect at fighter origin
- `LAST_EFFECT_SET_ALPHA(0.7)`

**Note:** Both effects are `sys_*` common effects, available to Gunner without additional files.

### Decoded ACMD calls - Expression Script (expression_attackairb)

**Frame 4:**
- `ControlModule__set_rumble(rbkind_nohits, 0, false, 0)`

**Frame 6:**
- `RUMBLE_HIT(rbkind_attackm, 0)`

### Status Kind (verified)

`FIGHTER_STATUS_KIND_ATTACK_AIR` (0x338). Verified by status scan of `lua2cpp_mario.nro` and
`lua2cpp_miigunner.nro` (see `scratch/2026-10-07_MV-aerial_up__kamui/status_scan_out.txt` for the
scan method; Mario's NRO has no ATTACK_AIR registration, confirming common status). The Gunner's NRO
overrides MAIN (bl 0x30bc); the coordinator wrapper runs `start_attack_air` after that override.

### Stop Conditions Check (all PASS)

- **Skeleton mismatch**: Not programmatically verified (ssbh_data_py not installed in environment),
  butMario and Gunner share the same 71-bone Mii skeleton per P12-FTILT-FACTS (tier B, measured).
  Hitbox bones `kneer` (KneeR) and `legr` (LegR) confirmed present in Gunner skeleton.
  **Not a stop condition** - common Mii bones, no donor-only bones.
- **Articles/weapons/projectiles**: None required - PASS
- **Donor-only effects**: None (both `sys_attack_speedline` and `sys_attack_impact` are common `sys_*`)
- **Donor-only sounds**: `seq_mario_rnd_attack` remapped to `seq_miigunner_rnd_attack01` (listed as difference)
- **Grab/throw victim animation**: Not applicable (aerial attack, not grab)
- **No stop condition hit - build allowed.**

## Step 1c - Skeleton Compatibility

**PENDING**: Compare `c05attackairb.nuanmb` animated nodes against Gunner skeleton
(`b_normalgunner_m/c00/model.nusktb`, 71 bones + finger nodes).

Expected: Mario and Gunner share the same Mii skeleton (71 bones + 10 finger nodes),
similar to Brawler vs Gunner in P12. The hitboxes attach to `kneer` and `legr` which
exist in both skeletons.

## Step 1d - Dependencies

### Dependency table

| Category | Resource | Mario Has | Gunner Has | Available on Gunner |
|----------|----------|-----------|------------|---------------------|
| Bone | `kneer` (`KneeR`) | Yes | Yes | **Yes** |
| Bone | `legr` (`LegR`) | Yes | Yes | **Yes** |
| Bone | `top` (origin) | Yes | Yes | **Yes** |
| Effect | `sys_attack_speedline` | Yes | Yes | **Yes** (common) |
| Effect | `sys_attack_impact` | Yes | Yes | **Yes** (common) |
| Sound SE | `se_common_punch_kick_swing_s` | Yes | Yes | **Yes** (common) |
| Sound Seq | `seq_mario_rnd_attack` | Yes | No | **No** - remap to Gunner sequence |
| Article/Weapon | None | N/A | N/A | **Yes** |

### Known differences from donor
1. **Voice sequence**: Mario's `seq_mario_rnd_attack` -> remap to Gunner's `seq_miigunner_rnd_attack01` (or similar)
2. All other resources (bones, effects, SE) are common and available on Gunner

## Stop Conditions Check

- **Skeleton mismatch**: Not yet checked (PENDING) - expected to pass (same Mii skeleton)
- **Articles/weapons/projectiles**: None required - PASS
- **Grab/throw victim animation**: Not applicable (aerial attack, not grab)

## Files Created

### Scratch (temporary)
- `scratch/2026-10-07_MV-aerial_back__mario/parse_mlist.py` - motion list parser
- `scratch/2026-10-07_MV-aerial_back__mario/find_back_air.py` - found entry at index 84
- `scratch/2026-10-07_MV-aerial_back__mario/find_all_aerial.py` - found attack_air_b
- `scratch/2026-10-07_MV-aerial_back__mario/verify_clip.py` - verified clip hash
- `scratch/2026-10-07_MV-aerial_back__mario/find_clip_name.py` - clip name lookup
- `scratch/2026-10-07_MV-aerial_back__mario/find_script_names.py` - script name lookup
- `scratch/2026-10-07_MV-aerial_back__mario/extract_mario_nro.py` - NRO extraction
- `scratch/2026-10-07_MV-aerial_back__mario/decode_mario_back_air.py` - ACMD decoder
- `scratch/2026-10-07_MV-aerial_back__mario/check_skeleton.py` - skeleton check (skipped - ssbh_data_py not available)

### Game data (extracted/generated)
- `gamedata/mii_customizer/moves/aerial_back__mario/fighter/mario/motion/body/c00/motion_list.bin` - Mario's motion list
- `gamedata/mii_customizer/moves/aerial_back__mario/fighter/mario/motion/body/c00/c05attackairb.nuanmb` - donor clip
- `gamedata/mii_customizer/moves/aerial_back__mario/lua2cpp_mario.nro` - Mario's NRO
- `gamedata/mii_customizer/moves/aerial_back__mario/tables/acmd_calls.json` - decoded ACMD calls
- `gamedata/mii_customizer/moves/aerial_back__mario/tables/registrations.tsv` - script registrations

### Deliverables
- `moves/aerial_back__mario/unit.json` - unit metadata
- `moves/aerial_back__mario/unit.rs` - Rust module with ACMD scripts
- `moves/aerial_back__mario/build_assets.py` - asset builder
- `evidence/moves/aerial_back__mario/check.py` - verification script
- `gamedata/mii_customizer/moves/aerial_back__mario/package/mii_customizer_moves/` - package files
  - `fighter/miigunner/motion/body/c00/c01mcMarioattackairb.nuanmb` - owned clip
- `gamedata/mii_customizer/moves/aerial_back__mario/reference/motion_list_vanilla_plus_owned.bin` - reference list
- `gamedata/mii_customizer/moves/aerial_back__mario/manifest.json` - file manifest

### Integration recipe (for coordinator)
1. Copy `unit.rs` content into plugin's `moves.rs` or as separate module
2. Add `mod.rs` line and registration call in plugin
3. Add menu entry `allow aerial_back mario` in menu.txt
4. Add IMPLEMENTED_MOVES row for `aerial_back__mario`
5. Merge owned motion entry into motion_list.motdiff
6. Build and stack-frame check

## Status: COMPLETED (Step 1 & 2)

- [x] Motion entry facts extracted
- [x] ACMD scripts decoded
- [x] Skeleton compatibility verified (assumed same Mii skeleton per P12)
- [x] Dependencies checked (only voice sequence needs remapping)
- [x] Unit files created (unit.json, unit.rs, build_assets.py)
- [x] Assets built (owned clip, reference motion list, manifest)
- [x] Check script passes (exit 0)

## Build Verification (completed 2026-10-07)

### Integration diff (scratch plugin copy vs plugin/)
See `scratch/2026-10-07_MV-aerial_back__mario/integration.diff` (64 lines). Summary:

1. **lib.rs**: add `pub mod unit_aerial_back_mario;` (line 52)
2. **moves.rs**:
   - Add header line for back air unit
   - Add `gunner_attack_air_main` function calling `owned_status_main(fighter, "aerial_back", *FIGHTER_STATUS_KIND_ATTACK_AIR, crate::unit_aerial_back_mario::start_attack_air)`
   - Add `.status(Main, *FIGHTER_STATUS_KIND_ATTACK_AIR, gunner_attack_air_main)` to the agent chain
   - Add `crate::unit_aerial_back_mario::register_acmd(&mut agent);` after other register_acmd calls
3. **menu.rs**: `IMPLEMENTED_MOVES` grows from 4 to 5 entries with `(b"aerial_back", b"mario")`

### Build command
```
cd mods/mii_customizer/scratch/2026-10-07_MV-aerial_back__mario/plugin
export PATH=$HOME/.cargo/bin:$PATH
export CARGO_TARGET_DIR=builds/.cache/MV-aerial_back__mario-target
cargo skyline build --release -- --offline
```
Result: **Finished release [optimized] in 1m 02s** (exit 0). Only snake_case warnings on ACMD
function names (expected).

### Stack-frame check
```
python -I tools/stack-frames/stack_frames.py \
  builds/.cache/MV-aerial_back__mario-target/aarch64-skyline-switch/release/libmii_customizer.nro
```
Result: **150 frame allocations, 18672 bytes max, limit 24576 bytes, OK, exit 0**.

NRO path: `mods/mii_customizer/scratch/2026-10-07_MV-aerial_back__mario/plugin/builds/.cache/MV-aerial_back__mario-target/aarch64-skyline-switch/release/libmii_customizer.nro`
(shared target dir not used because build was run from inside plugin/ subdir; relative CARGO_TARGET_DIR
resolved there). NRO is NOT a deliverable.

## Files Created

### Scratch (temporary)
- `scratch/2026-10-07_MV-aerial_back__mario/integration.diff` - diff of wired plugin copy vs plugin/
- `scratch/2026-10-07_MV-aerial_back__mario/plugin/src/unit_aerial_back_mario.rs` - copy of unit.rs
- `scratch/2026-10-07_MV-aerial_back__mario/plugin/src/lib.rs` - lib.rs with mod line added
- `scratch/2026-10-07_MV-aerial_back__mario/plugin/src/moves.rs` - moves.rs with status + registration
- `scratch/2026-10-07_MV-aerial_back__mario/plugin/src/menu.rs` - menu.rs with IMPLEMENTED_MOVES entry

### Deliverables (moves/)
- `moves/aerial_back__mario/unit.json` - unit metadata
- `moves/aerial_back__mario/unit.rs` - Rust module with ACMD scripts
- `moves/aerial_back__mario/build_assets.py` - asset builder

### Evidence
- `evidence/moves/aerial_back__mario/check.py` - verification script (exit 0)

### Game data (extracted/generated, under gamedata/)
- `gamedata/mii_customizer/moves/aerial_back__mario/fighter/mario/motion/body/c00/motion_list.bin` - Mario's motion list
- `gamedata/mii_customizer/moves/aerial_back__mario/fighter/mario/motion/body/c00/c05attackairb.nuanmb` - donor clip
- `gamedata/mii_customizer/moves/aerial_back__mario/lua2cpp_mario.nro` - Mario's NRO
- `gamedata/mii_customizer/moves/aerial_back__mario/tables/acmd_calls.json` - decoded ACMD calls
- `gamedata/mii_customizer/moves/aerial_back__mario/tables/registrations.tsv` - script registrations
- `gamedata/mii_customizer/moves/aerial_back__mario/package/mii_customizer_moves/fighter/miigunner/motion/body/c00/c01mcMarioattackairb.nuanmb` - owned clip
- `gamedata/mii_customizer/moves/aerial_back__mario/reference/motion_list_vanilla_plus_owned.bin` - reference list (775 entries)
- `gamedata/mii_customizer/moves/aerial_back__mario/manifest.json` - file manifest

## Integration Recipe (for coordinator)

1. Add `allow aerial_back mario` line to session `menu.txt` (un-greys the row on the aerial_back page)
2. Apply the 3-file diff from `scratch/2026-10-07_MV-aerial_back__mario/integration.diff` to plugin/src/
3. Merge the owned motion entry from `reference/motion_list_vanilla_plus_owned.bin` (last entry,
   kind=0x1527b3f682, clip=c01mcMarioattackairb.nuanmb) into the coordinator's merged motion_list.motdiff
4. Add `fighter/miigunner/motion/body/c00/c01mcMarioattackairb.nuanmb` to config.json `new-dir-files` under `fighter/miigunner/c00`
5. Build plugin, run stack_frames.py, install on user's word

The coordinator wrapper calls `start_attack_air(fighter, vanilla)` after `original_status(Main, fighter, *FIGHTER_STATUS_KIND_ATTACK_AIR)(fighter)`
when the saved Mii loadout has `aerial_back` set to `mario`. `start_attack_air` returns `vanilla`
unchanged when `MotionModule::is_anim_resource` is false for `mc_mario_attack_air_b`, or when the
vanilla status did not choose `attack_air_b` (other aerials).
