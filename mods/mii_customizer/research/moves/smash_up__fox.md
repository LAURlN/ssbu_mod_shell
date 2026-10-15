# MV-smash_up__fox - Fox's Up Smash on Mii Gunner

Task: MV-smash_up__fox  
Move: Up Smash (`smash_up`)  
Donor: Fox (`fox`)  
Recipient: Mii Gunner (`miigunner`)  
Date: 2026-10-07  
Status: DONE  

---

## 1. Move Mechanism & Facts (Step 1)

This unit packages Fox's Up Smash (`attack_hi4` and charge `attack_hi4_hold`) as a self-contained move unit for Mii Gunner.

### 1a. Motion Entries Table
Extracted from `fighter/fox/motion/body/c00/motion_list.bin` and verified against vanilla Gunner:

| Attribute | Donor (Fox) Main | Transplant Main | Donor (Fox) Hold | Transplant Hold |
|---|---|---|---|---|
| **Motion Kind** | `attack_hi4` (`0x0acb0eb209`) | `mc_fox_attack_hi4` (`0x1140a2b154`) | `attack_hi4_hold` (`0x0f6004bca9`) | `mc_fox_attack_hi4_hold` (`0x160037fbe3`) |
| **Motion Index** | 79 | 774 (appended) | 80 | 775 (appended) |
| **Clip File** | `c04attackhi4.nuanmb` (`0x1404c0ec2e`) | `c01mcfoxattackhi4.nuanmb` (`0x1832844ba4`) | `c04attackhi4charge.nuanmb` (`0x1a7f055e81`) | `c01mcfoxattackhi4charge.nuanmb` (`0x1ed38f82a2`) |
| **Clip Size** | 50,216 bytes | 50,216 bytes | 29,991 bytes | 29,991 bytes |
| **Clip SHA256** | `3623ed82e881077755f1a5f4c5c24e6eb142b784a92cfa7fe3345464161c6b12` | Identical bytes | `bddfde5ec4dfb40a92f0224df39c148ca298f2b704c7c81525aa11bf5a882a7f` | Identical bytes |
| **Animation Length** | 64 frames (`final_frame_index` = 63.0) | 64 frames (`final_frame_index` = 63.0) | 61 frames (`final_frame_index` = 60.0) | 61 frames (`final_frame_index` = 60.0) |
| **Flags** | `0x0080` | `0x0080` | `0x0080` | `0x0080` |
| **Blend** | 0 | 0 | 0 | 0 |
| **Cancel Frame** | 56 (FAF 57) | 56 (FAF 57) | 0 | 0 |
| **Game Script** | `game_attackhi4` (`0x0ef30e51f6`) | `game_mcfoxattackhi4` (`0x133bc5e305`) | `game_attackhi4charge` (`0x149a4073e4`) | `game_mcfoxattackhi4charge` (`0x19037f9ccd`) |
| **Expression Script** | `expression_attackhi4` (`0x149f1f7c74`) | `expression_mcfoxattackhi4` (`0x19068d1738`) | `expression_attackhi4charge` (`0x1a33758b29`) | `expression_mcfoxattackhi4charge` (`0x1f743c7832`) |
| **Sound Script** | `sound_attackhi4` (`0x0f13f04449`) | `sound_mcfoxattackhi4` (`0x145f2bfb9b`) | `sound_attackhi4charge` (`0x1147a2be78`) | `sound_mcfoxattackhi4charge` (`0x1a0dfd624a`) |
| **Effect Script** | `effect_attackhi4` (`0x10366d0101`) | `effect_mcfoxattackhi4` (`0x1530c56de2`) | `effect_attackhi4charge` (`0x117498c558`) | `effect_mcfoxattackhi4charge` (`0x1b0abd56e5`) |

### 1b. ACMD Scripts Decoded

Decoded from `lua2cpp_fox.nro` (impls verified with Capstone disassembler):

#### `game_mcfoxattackhi4` (impl `0xc97d0`):
- **Frame 3.0**: `WorkModule::on_flag(*FIGHTER_STATUS_ATTACK_FLAG_START_SMASH_HOLD)` (smash charge window enabled).
- **Frame 8.0**: Active clean hitboxes (duration 2 frames, frames 8..9):
  - **Hitbox 0**: Bone `kneer`, Damage `16.0%`, Angle `80°`, KBG `97`, FKB `0`, BKB `30`, Size `4.1`, Offset `(0.0, 1.0, 0.0)`, Sound Level `L`, Sound Attr `KICK`, Region `KICK`, cutup attribute.
  - **Hitbox 1**: Bone `kneer`, Damage `16.0%`, Angle `80°`, KBG `97`, FKB `0`, BKB `30`, Size `5.7`, Offset `(3.0, 2.1, 0.0)`, Sound Level `L`, Sound Attr `KICK`, Region `KICK`, cutup attribute.
  - **Hitbox 2**: Bone `top`, Damage `16.0%`, Angle `80°`, KBG `97`, FKB `0`, BKB `30`, Size `2.0`, Offset `(0.0, 3.0, 10.0)`, Sound Level `L`, Sound Attr `KICK`, Region `KICK`, cutup attribute.
- **Frame 9.0**: `AttackModule::clear(2, false)` (removes `top` scoop hitbox).
- **Frame 10.0**: Late hitboxes (duration 2 frames, frames 10..11):
  - **Hitbox 0**: Bone `kneer`, Damage `11.0%`, Angle `361°`, KBG `100`, FKB `0`, BKB `10`, Size `4.1`, Offset `(0.0, 1.0, 0.0)`, Sound Level `M`, Sound Attr `KICK`, Region `KICK`, cutup attribute.
  - **Hitbox 1**: Bone `kneer`, Damage `11.0%`, Angle `361°`, KBG `100`, FKB `0`, BKB `10`, Size `4.7`, Offset `(2.9, 1.4, 0.0)`, Sound Level `M`, Sound Attr `KICK`, Region `KICK`, cutup attribute.
- **Frame 12.0**: `AttackModule::clear_all`.

#### `game_mcfoxattackhi4charge` (impl `0xcae80`):
- Empty (standard in SSBU during hold status).

#### `effect_mcfoxattackhi4` (impl `0x94870`):
- **Frame 1.0**: `EFFECT(sys_smash_flash, top, 0.0, 17.0, 4.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, true)`.
- **Frame 7.0**: `LANDING_EFFECT(sys_h_smoke_a, top, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.9, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, false)`.
- **Frame 8.0**: donor-only `fox_smash_arc` omitted per project rules (Gunner lacks `ef_fox.eff` bank).
- **Frame 27.0**: `FOOT_EFFECT(sys_landing_smoke_s, top, -1.5, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, false)`.

#### `effect_mcfoxattackhi4charge` (impl `0x949c0`):
- **Frame 5.0**: `FOOT_EFFECT(sys_run_smoke, top, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 12.0, 0.0, 4.0, 0.0, 0.0, 0.0, false)`.
- **Frame 10.0**: `EFFECT(sys_smash_flash_s, toer, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 2.0, 2.0, 2.0, 0.0, 0.0, 0.0, false)`.

#### `sound_mcfoxattackhi4` (impl `0x117390`):
- **Frame 4.0**: `STOP_SE(se_common_smash_start)`.
- **Frame 8.0**: Remapped to Gunner's native labels:
  - `PLAY_SEQUENCE(seq_miigunner_rnd_attack03)` (replaces donor `vc_fox_attack06`).
  - `PLAY_SE(se_miigunner_smash_h01)` (replaces donor `se_fox_smash_h01`).
- **Frame 27.0**: `PLAY_SE(se_miigunner_landing01)` (replaces donor `se_fox_landing01`).

#### `sound_mcfoxattackhi4charge` (impl `0x117490`):
- **Frame 2.0**: `PLAY_SE(se_common_smash_start)` (common smash sound retained).

#### `expression_mcfoxattackhi4` (impl `0xce9e0`):
- **Frame 0.0**: `slope!(MA_MSC_CMD_SLOPE_SLOPE, SLOPE_STATUS_LR)`.
- **Frame 3.0**: `AttackModule::set_attack_reference_joint_id(toer, ...)`, `slope!(MA_MSC_CMD_SLOPE_SLOPE_INTP, SLOPE_STATUS_L, 3)`.
- **Frame 6.0**: `ControlModule::set_rumble(rbkind_nohitl, 0, false, 0)`, `slope!(MA_MSC_CMD_SLOPE_SLOPE_INTP, SLOPE_STATUS_NONE, 2)`.
- **Frame 8.0**: `RUMBLE_HIT(rbkind_attackl, 0)`.
- **Frame 22.0**: `slope!(MA_MSC_CMD_SLOPE_SLOPE_INTP, SLOPE_STATUS_LR, 3)`.
- **Frame 27.0**: `ControlModule::set_rumble(rbkind_lands, 0, false, 0)`.

#### `expression_mcfoxattackhi4charge` (impl `0xceb40`):
- **Frame 0.0**: `physics!(MA_MSC_CMD_PHYSICS_START_CHARGE, 0.8, 0.8, -1, 0.9, 0.7, 0.2, "invalid")`, `slope!(MA_MSC_CMD_SLOPE_SLOPE, SLOPE_STATUS_LR)`, `ControlModule::set_rumble(rbkind_smashhold1, 0, true, 0)`.
- **Frame 61.0**: `ControlModule::set_rumble(rbkind_smashhold2, 0, true, 0)`.

#### Status Handling:
- Both Fox and Mii Gunner run up smash under common engine statuses `FIGHTER_STATUS_KIND_ATTACK_HI4` (53 / `0x35`) and `FIGHTER_STATUS_KIND_ATTACK_HI4_HOLD` (52 / `0x34`).
- Neither `lua2cpp_fox.nro` nor `lua2cpp_miigunner.nro` overrides status 52 or 53.
- `unit.rs` provides `start_attack_hi4`, `start_attack_hi4_hold`, and `custom_attack_hi4_main` for seamless status wrapping.

### 1c. Skeleton & Compatibility Comparison

Measured by comparing `c04attackhi4.nuanmb` tracks with Gunner skeleton (`model.nusktb`, 71 bones):
- **Humanoid compatibility**: Fox uses standard humanoid bone structure (`trans`, `rot`, `hip`, `waist`, `bust`, `head`, `arm*`, `leg*`, `knee*`, `foot*`, `toe*`, `hand*`).
- **Nodes in clip lacking in Gunner**: `Face`, `Jaw`, `Nose`, `Reflector`, `Tail1`, `Tail2`, `Tail3` (Fox-specific aesthetic nodes, safely ignored by engine for Gunner).
- **Gunner skeleton bones left unanimated**: Mii constraint helper bones (`H_Wrist*`, `H_Elbow*`, `H_Knee*`) - identical to Gunner's own vanilla clips.
- **Hitbox & effect attachment bones**: `kneer` (`KneeR`), `toer` (`ToeR`), and `top` (engine origin). All exist natively in Gunner skeleton.

### 1d. Dependencies & Stop Condition Analysis
- **Articles / weapons / projectiles**: None. Fox's up smash is an unassisted physical backflip kick.
- **Donor-only effects**: `fox_smash_arc` omitted per project rules. Common `sys_*` effects retained.
- **Donor-only sounds**: Remapped to native Gunner equivalents (`seq_miigunner_rnd_attack03`, `se_miigunner_smash_h01`, `se_miigunner_landing01`).
- **Work IDs / Parameters**: None read beyond common `FIGHTER_STATUS_ATTACK_FLAG_START_SMASH_HOLD`.
- **Stop Conditions**: None triggered.

---

## 2. Comparison: Copied Exactly vs Differences from Donor

| Feature | Donor (Fox) | Unit (Mii Gunner Transplant) | Status | Notes |
|---|---|---|---|---|
| **Animation Track Structure** | 71 humanoid bones + 7 Fox-specific | Humanoid bones animated | **Exact** | Humanoid skeleton animated 1:1; unused nodes ignored. |
| **Hitbox Damage (Clean)** | 16.0% (3 hitboxes) | 16.0% (3 hitboxes) | **Exact** | Active frames 8..9 on `kneer` and `top`. |
| **Hitbox Damage (Late)** | 11.0% (2 hitboxes) | 11.0% (2 hitboxes) | **Exact** | Active frames 10..11 on `kneer`. |
| **Hitbox Angles / Knockback** | 80° (clean), 361° (late) | 80° (clean), 361° (late) | **Exact** | Replicated in `game_mcfoxattackhi4`. |
| **FAF / Cancel Frame** | Frame 56 (FAF 57, length 64) | Frame 56 (FAF 57, length 64) | **Exact** | Replaces Gunner's multi-hit up smash. |
| **Visual Effects** | `sys_*` flash/smoke + `fox_smash_arc` | `sys_*` flash/smoke retained | **Omitted** | `fox_smash_arc` omitted per rules (recipient lacks `ef_fox.eff`). |
| **Voice Line** | `vc_fox_attack06` | `seq_miigunner_rnd_attack03` | **Mapped** | Remapped to Gunner's own attack voice sequence. |
| **Sound Effects** | `se_fox_smash_h01`, `se_fox_landing01` | `se_miigunner_smash_h01`, `se_miigunner_landing01` | **Mapped** | Remapped to Gunner's own smash and landing sounds. |
| **Charge Sound** | `se_common_smash_start` | `se_common_smash_start` | **Exact** | Common engine sound retained. |

---

## 3. Console Verification Test (Max 6 Steps)

Run in Training Mode on console (Tier A verification):

1. **Menu Selection (Gunner A)**: Open Mii Customizer in-game menu. Select Up Smash (`smash_up`) -> Fox. Verify menu displays `"Up Smash: Fox"`.
2. **Vanilla Retention (Gunner B)**: Select a second saved Mii Gunner with default Up Smash. Verify menu shows `"Up Smash: Mii Gunner"`.
3. **Match Start**: Enter match with Gunner A (Player 1) and Gunner B (Player 2). Verify debug log records `smash_up=fox` for Gunner A and `smash_up=default` for Gunner B.
4. **Smash Execution & Charge (Gunner A)**:
   - Perform uncharged up smash: Gunner performs Fox's backflip kick. Deals **16.0%** clean (frame 8..9) or **11.0%** late (frame 10..11).
   - Hold smash button: Gunner enters smash charge stance (`mc_fox_attack_hi4_hold`), releases on button release with increased damage up to 1.4x (22.4%).
   - Actionable on frame 57 (FAF 57).
5. **Gunner B & CPU Control**:
   - Gunner B performs up smash: executes vanilla multi-hit explosion up smash.
   - CPU Gunner executes vanilla up smash without interference.
6. **Revert / Bypass**:
   - Revert Gunner A setting back to default in menu. Verify vanilla up smash returns immediately.

---

## 4. Integration Recipe for Coordinator

The unit was proven to compile offline against the plugin crate. Below is the exact diff for integrating `smash_up__fox` into `plugin/`:

```diff
diff --git a/plugin/src/lib.rs b/plugin/src/lib.rs
index 5fc43e4..546ea08 100644
--- a/plugin/src/lib.rs
+++ b/plugin/src/lib.rs
@@ -48,6 +48,7 @@ pub mod moves;
 mod names;
 pub mod unit_tilt_down;
 pub mod unit_tilt_up;
+pub mod unit_smash_up;
 mod preset;
 mod ui;
 
diff --git a/plugin/src/menu.rs b/plugin/src/menu.rs
index 0c9c3cc..05d0097 100644
--- a/plugin/src/menu.rs
+++ b/plugin/src/menu.rs
@@ -462,10 +462,11 @@ impl Menu {
     }
 }
 
-pub const IMPLEMENTED_MOVES: [(&[u8], &[u8]); 3] = [
+pub const IMPLEMENTED_MOVES: [(&[u8], &[u8]); 4] = [
     (b"tilt_side", b"miifighter"),
     (b"tilt_up", b"miifighter"),
     (b"tilt_down", b"miifighter"),
+    (b"smash_up", b"fox"),
 ];
 
 pub fn is_move_implemented(entry_id: &[u8], preset_name: &[u8]) -> bool {

diff --git a/plugin/src/moves.rs b/plugin/src/moves.rs
index 0598bea..6d8a145 100644
--- a/plugin/src/moves.rs
+++ b/plugin/src/moves.rs
@@ -410,6 +410,14 @@ pub unsafe extern "C" fn gunner_attack_lw3_main(fighter: &mut L2CFighterCommon)
     owned_status_main(fighter, "tilt_down", *FIGHTER_STATUS_KIND_ATTACK_LW3, crate::unit_tilt_down::start_attack_lw3)
 }
 
+pub unsafe extern "C" fn gunner_attack_hi4_main(fighter: &mut L2CFighterCommon) -> L2CValue {
+    owned_status_main(fighter, "smash_up", *FIGHTER_STATUS_KIND_ATTACK_HI4, crate::unit_smash_up::start_attack_hi4)
+}
+
+pub unsafe extern "C" fn gunner_attack_hi4_hold_main(fighter: &mut L2CFighterCommon) -> L2CValue {
+    owned_status_main(fighter, "smash_up", *FIGHTER_STATUS_KIND_ATTACK_HI4_HOLD, crate::unit_smash_up::start_attack_hi4_hold)
+}
+
 pub fn install() {
     let active = is_active();
     let mut out: LineBuf<192> = LineBuf::new();
@@ -446,8 +454,11 @@ pub fn install() {
         .expression_acmd("expression_mcattacks3lw", expression_mcattacks3lw, Priority::Default)
         .status(Main, *FIGHTER_STATUS_KIND_ATTACK_S3, gunner_attack_s3_main)
         .status(Main, *FIGHTER_STATUS_KIND_ATTACK_HI3, gunner_attack_hi3_main)
-        .status(Main, *FIGHTER_STATUS_KIND_ATTACK_LW3, gunner_attack_lw3_main);
+        .status(Main, *FIGHTER_STATUS_KIND_ATTACK_LW3, gunner_attack_lw3_main)
+        .status(Main, *FIGHTER_STATUS_KIND_ATTACK_HI4, gunner_attack_hi4_main)
+        .status(Main, *FIGHTER_STATUS_KIND_ATTACK_HI4_HOLD, gunner_attack_hi4_hold_main);
     crate::unit_tilt_up::register_acmd(&mut agent);
     crate::unit_tilt_down::register_acmd(&mut agent);
+    crate::unit_smash_up::register_acmd(&mut agent);
     agent.install();
 }
```

In addition, `plugin/src/unit_smash_up.rs` is added to the plugin crate by copying `moves/smash_up__fox/unit.rs`.

---

## 5. Offline Verification

- **Asset Generation (`build_assets.py`)**: Executed cleanly (exit 0). Generated:
  - `package/fighter/miigunner/motion/body/c00/c01mcfoxattackhi4.nuanmb` (50,216 bytes)
  - `package/fighter/miigunner/motion/body/c00/c01mcfoxattackhi4charge.nuanmb` (29,991 bytes)
  - Reference `motion_list_vanilla_plus_owned.bin` (46,400 bytes, 776 entries = vanilla 774 + 2 owned)
  - `manifest.json` (sizes, SHA-256)
- **Verification Script (`check.py`)**: Ran from workspace root (exit 0). Passed all checks:
  - Package files against `manifest.json` (sizes, SHA-256).
  - Reference motion list parsed, validated count (774 -> 776) and flags/cancel frames.
  - Rust hashes and hitbox parameters equal decoded table.
  - Skeletons and bone names verified against Gunner `model.nusktb`.
  - All 4 negative controls passed.
- **Plugin Offline Build (`cargo skyline build`)**: Compiled in scratch copy with target dir `builds/.cache/MV-smash_up__fox-target/` (exit 0).
- **Stack Frames Check (`stack_frames.py`)**: Executed against the built NRO:
  - 143 frame allocations, largest allocation 18,672 bytes (well below 24,576-byte limit on 64 KiB stack). Exit 0: OK.

---

## 6. Evidence Tiers

- **Tier B (Offline Measurement & Verification)**:
  - `motion_list.bin` entries 79 & 80 in Fox and entries in Gunner parsed from game dump.
  - Track structures compared via `ssbh_data_py` against `model.nusktb`.
  - ACMD scripts disassembled and decoded from `lua2cpp_fox.nro` via Capstone.
  - Package manifest verification, offline compilation, and stack frame analysis.
- **Tier D (In-Game Console Behavior)**:
  - In-game animation playback, hitbox collision registering 16.0% / 11.0% in Training Mode, sound playback, charge stance, and cancel timing on hardware.
