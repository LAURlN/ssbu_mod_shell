# MV-tilt_up__miifighter - Mii Brawler's Up Tilt on Mii Gunner

Task: MV-tilt_up__miifighter  
Move: Up Tilt (`tilt_up`)  
Donor: Mii Brawler (`miifighter`)  
Recipient: Mii Gunner (`miigunner`)  
Date: 2026-10-07  
Status: DONE  

---

## 1. Move Mechanism & Facts

This unit packages Mii Brawler's Up Tilt (`attack_hi3`) as a self-contained move unit for Mii Gunner.

### 1a. Motion Entries Table
Extracted from `fighter/miifighter/motion/body/c00/motion_list.bin` and verified against vanilla Gunner:

| Attribute | Donor (Mii Brawler) | Transplant (Mii Gunner) | Notes |
|---|---|---|---|
| **Motion Kind** | `attack_hi3` (`0x0acbfc42e6`) | `mc_miifighter_attack_hi3` (`0x187f36ba92`) | Single-stage, non-angled |
| **Motion Index** | 74 | 774 (appended) | Extends vanilla list from 774 to 775 entries |
| **Clip File** | `c02attackhi3.nuanmb` (`0x138caf3e29`) | `c01mcmiifighterattackhi3.nuanmb` (`0x1f6a741a18`) | Shipped in `fighter/miigunner/motion/body/c00/` |
| **Clip Size / SHA256** | 35,704 bytes / `1d70f70d2dba773d1b33d8c69eac2296da1457eb887c38434da043ab167eff7d` | Identical bytes | Extracted from vanilla `data.arc` |
| **Animation Length** | 56 frames (`final_frame_index` = 55.0) | 56 frames (`final_frame_index` = 55.0) | Measured via `ssbh_data_py` |
| **Flags** | `0x0080` | `0x0080` | Exact match |
| **Blend** | 0 | 0 | Exact match |
| **Cancel Frame** | 30 (FAF 31) | 30 (FAF 31) | Vanilla Gunner is cancel frame 38 (FAF 39) |
| **Game Script** | `game_attackhi3` (`0x0ef3bca119`) | `game_mcmiifighterattackhi3` (`0x1a99dad299`) | Owned ACMD script |
| **Expression Script** | `expression_attackhi3` (`0x149fed8c9b`) | `expression_mcmiifighterattackhi3` (`0x20b4af7ef0`) | Owned ACMD script |
| **Sound Script** | `sound_attackhi3` (`0x0f1302b4a6`) | `sound_mcmiifighterattackhi3` (`0x1bea0846e4`) | Remapped to Gunner sound labels |
| **Effect Script** | `effect_attackhi3` (`0x10369f11fe`) | `effect_mcmiifighterattackhi3` (`0x1cac66b8a9`) | Common `sys_*` system effects |

### 1b. ACMD Scripts Decoded

Decoded from `lua2cpp_miifighter.nro` (impls verified with Capstone disassembler):

#### `game_mcmiifighterattackhi3` (impl `0x150fe0`):
- **Frame 5.0**: Active hitboxes (duration 8.0 frames, active 5..12):
  - **Hitbox 0**: Bone `arml`, Damage `6.0%`, Angle `96°`, KBG `130`, FKB `0`, BKB `28`, Size `4.0`, Offset `(0.0, 0.0, 0.0)`, Sound Level `M`, Sound Attr `PUNCH`, Region `PUNCH`.
  - **Hitbox 1**: Bone `arml`, Damage `6.0%`, Angle `96°`, KBG `130`, FKB `0`, BKB `28`, Size `5.2`, Offset `(4.0, 0.0, 0.0)`, Sound Level `M`, Sound Attr `PUNCH`, Region `PUNCH`.
- **Frame 13.0** (Frame 5 + Wait 8): `AttackModule::clear_all`.

#### `effect_mcmiifighterattackhi3` (impl `0x9d6a0`):
- **Frame 5.0**: `EFFECT_FOLLOW_FLIP_ALPHA(sys_attack_arc_c, sys_attack_arc_c, top, 0.0, 11.5, 3.0, -62.0, 9.0, 90.0, 0.8, true, EF_FLIP_YZ, 0.3)`, Rate `1.5`.
- **Frame 9.0**: `EFFECT_ALPHA(sys_attack_impact, top, 2.0, 24.0, -1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 360.0, false, 0.4)`.
- **Frame 24.0**: `LANDING_EFFECT(sys_landing_smoke_s, top, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, false)`.

#### `sound_mcmiifighterattackhi3` (impl `0x179b30`):
- **Frame 5.0**: Remapped to Gunner's native labels:
  - `PLAY_SE(se_miigunner_swing_m)` (replaces donor `se_miifighter_swing_m`).
  - `PLAY_SEQUENCE(seq_miigunner_rnd_attack02)` (replaces donor `seq_miifighter_rnd_attack02`).

#### `expression_mcmiifighterattackhi3` (impl `0xdc4e0`):
- **Frame 0.0**: `slope!(MA_MSC_CMD_SLOPE_SLOPE, SLOPE_STATUS_LR)`.
- **Frame 3.0**: `ControlModule::set_rumble(rbkind_nohitm, 0, false, 0)`.
- **Frame 5.0**: `RUMBLE_HIT(rbkind_attackm, 0)`.
- **Frame 6.0**: `slope!(MA_MSC_CMD_SLOPE_SLOPE_INTP, SLOPE_STATUS_NONE, 3)`.
- **Frame 20.0**: `slope!(MA_MSC_CMD_SLOPE_SLOPE_INTP, SLOPE_STATUS_LR, 3)`.
- **Frame 24.0**: `ControlModule::set_rumble(rbkind_lands, 0, false, 0)`.

#### Status Handling:
- Both donor and recipient run up tilt under common engine status `FIGHTER_STATUS_KIND_ATTACK_HI3` (43 / `0x2b`).
- Neither `lua2cpp_miifighter.nro` nor `lua2cpp_miigunner.nro` overrides `ATTACK_HI3` (0 overrides across all registrations). Both use engine default `status_AttackHi3Common`.

### 1c. Skeleton & Compatibility Comparison

Measured by comparing `c02attackhi3.nuanmb` tracks with Gunner skeleton (`model.nusktb`, 71 bones):
- **Transform tracks**: Exactly 75 nodes in donor clip and Gunner clip. Symmetric difference is empty set `set()`.
- **Visibility tracks**: Exactly 12 facial visibility tracks (`MiiFighterM_eye_*`, `MiiFighterM_mouth_*`). Symmetric difference is empty set `set()`.
- **Nodes in clip lacking in skeleton**: Exactly 10 finger effect helper nodes (`FingerL14_eff` .. `FingerR54_eff`). Identical to Gunner's own animations.
- **Gunner skeleton bones left unanimated**: Exactly 6 constraint bones (`H_WristL`, `H_ElbowL`, `H_WristR`, `H_ElbowR`, `H_KneeL`, `H_KneeR`). Identical to Gunner's own animations.
- **Hitbox & Effect attachment bones**: `arml` (`ArmL`) and `top`. Both exist natively in Gunner skeleton.

### 1d. Dependencies & Stop Condition Analysis
- **Articles / weapons / projectiles**: None used.
- **Donor-only effects**: None (`sys_attack_arc_c`, `sys_attack_impact`, `sys_landing_smoke_s` are in `ef_common.eff`).
- **Donor-only sounds**: `se_miifighter_swing_m` and `seq_miifighter_rnd_attack02` remapped to native Gunner equivalents `se_miigunner_swing_m` and `seq_miigunner_rnd_attack02`.
- **Work IDs / Parameters**: None read.
- **Stop Conditions**: None triggered. Unit is viable without retargeting or article dependencies.

---

## 2. Comparison: Copied Exactly vs Differences from Donor

| Feature | Donor (Mii Brawler) | Unit (Mii Gunner Transplant) | Status | Notes |
|---|---|---|---|---|
| **Animation Skeleton** | 71 bones + 10 finger nodes | Same 71 bones + 10 finger nodes | **Exact** | Transform and visibility tracks match 100%. |
| **Hitbox Damage** | 6.0% (both hitboxes) | 6.0% (both hitboxes) | **Exact** | Active frames 5..12 on `arml`. |
| **Hitbox Angles / Knockback** | 96°, KBG 130, BKB 28 | 96°, KBG 130, BKB 28 | **Exact** | Replicated in `game_mcmiifighterattackhi3`. |
| **Hitbox Sizes** | 4.0 and 5.2 | 4.0 and 5.2 | **Exact** | Identical radius and offsets. |
| **FAF / Cancel Frame** | Frame 30 (FAF 31, length 56) | Frame 30 (FAF 31, length 56) | **Exact** | Replaces Gunner's frame 38 cancel. |
| **Visual Effects** | `sys_attack_arc_c`, `sys_attack_impact`, `sys_landing_smoke_s` | `sys_attack_arc_c`, `sys_attack_impact`, `sys_landing_smoke_s` | **Exact** | Common system effects loaded from `ef_common.eff`. |
| **Sound Effect** | `se_miifighter_swing_m` | `se_miigunner_swing_m` | **Mapped** | Remapped to Gunner's own medium swing sound. |
| **Voice Sequence** | `seq_miifighter_rnd_attack02` | `seq_miigunner_rnd_attack02` | **Mapped** | Remapped to Gunner's own attack voice sequence. |

---

## 3. Console Verification Test (Max 6 Steps)

Run in Training Mode on console (Tier A verification):

1. **Menu Selection (Gunner A)**: Enter Mii Customizer in-game menu. Navigate to Up Tilt (`tilt_up`). Select "Mii Brawler". Verify main menu displays `"Up Tilt: Mii Brawler"` and `loadouts.txt` contains `<id> slot tilt_up miifighter`.
2. **Vanilla Retention (Gunner B)**: Select a second saved Mii Gunner with default Up Tilt. Verify main menu shows `"Up Tilt: Mii Gunner"`.
3. **Match Start**: Enter match with Gunner A (Player 1) and Gunner B (Player 2). Verify log contains `mc|MV|...|tilt_up=miifighter` for Gunner A and `tilt_up=default` for Gunner B.
4. **Gunner A Execution & Hitboxes**: With Gunner A, perform up tilt:
   - Plays Brawler's upward punch animation (instead of Gunner's upward arm cannon thrust).
   - In Training Mode, verify damage: deals exactly **6.0%**.
   - Check FAF: actionable on frame 31 (cancel frame 30, earlier than vanilla Gunner's frame 39).
5. **Gunner B & CPU Control**:
   - Gunner B performs up tilt: executes Gunner's vanilla cannon thrust (11.0% / 9.0% damage, cancel frame 38).
   - CPU Gunner performs vanilla up tilt byte-for-byte.
6. **Revert / Negative Switch**:
   - Return to editor menu, set Gunner A Up Tilt back to "Mii Gunner". Re-enter match and verify vanilla up tilt executes.
   - Alternatively, test `sd:/ultimate/mii_customizer/moves_off` to ensure all move overrides are cleanly bypassed.

---

## 4. Integration Recipe for Coordinator

The unit was proven to compile offline against the plugin crate. Below is the exact unified diff for integrating `tilt_up__miifighter` into `plugin/`:

```diff
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -45,6 +45,7 @@
 mod logic;
 mod menu;
 pub mod moves;
+pub mod tilt_up__miifighter;
 mod names;
 mod preset;
 mod ui;

--- a/src/menu.rs
+++ b/src/menu.rs
@@ -462,8 +462,9 @@
     }
 }
 
-pub const IMPLEMENTED_MOVES: [(&[u8], &[u8]); 1] = [
+pub const IMPLEMENTED_MOVES: [(&[u8], &[u8]); 2] = [
     (b"tilt_side", b"miifighter"),
+    (b"tilt_up", b"miifighter"),
 ];
 
 pub fn is_move_implemented(entry_id: &[u8], preset_name: &[u8]) -> bool {

--- a/src/moves.rs
+++ b/src/moves.rs
@@ -47,6 +47,13 @@
     } else {
         None
     };
+    let up_slot = if saved_id != 0 {
+        crate::editor::the_menu()
+            .find_id(b"tilt_up")
+            .and_then(|e_idx| crate::STORE.slot_of_id(saved_id, e_idx))
+    } else {
+        None
+    };
     let mut out: LineBuf<192> = LineBuf::new();
     head(&mut out, "MV");
     out.s("|match|fighter=miigunner|id=").hex_fixed(saved_id as u64, 8);
     out.s("|tilt_side=").s(if tilt_slot.is_some() { "miifighter" } else { "default" });
+    out.s("|tilt_up=").s(if up_slot.is_some() { "miifighter" } else { "default" });
     out.end_line();
     emit_wait(out.as_bytes());
 }
@@ -358,6 +366,31 @@
     fighter.sub_shift_status_main(L2CValue::Ptr(custom_ftilt_main as *const () as _))
 }
 
+pub unsafe extern "C" fn gunner_attack_hi3_main(fighter: &mut L2CFighterCommon) -> L2CValue {
+    let boma = fighter.module_accessor;
+    let entry_id = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);
+    let tilt_slot = if entry_id >= 0 {
+        crate::read_player(entry_id as u32).and_then(|(saved_id, _)| {
+            if saved_id != 0 {
+                crate::editor::the_menu()
+                    .find_id(b"tilt_up")
+                    .and_then(|e_idx| crate::STORE.slot_of_id(saved_id, e_idx))
+            } else {
+                None
+            }
+        })
+    } else {
+        None
+    };
+
+    if tilt_slot.is_none() {
+        return original_status(Main, fighter, *FIGHTER_STATUS_KIND_ATTACK_HI3)(fighter);
+    }
+
+    let vanilla = original_status(Main, fighter, *FIGHTER_STATUS_KIND_ATTACK_HI3)(fighter);
+    crate::tilt_up__miifighter::start_attack_hi3(fighter, vanilla)
+}
+
 pub fn install() {
     let active = is_active();
     let mut out: LineBuf<192> = LineBuf::new();
@@ -377,7 +410,8 @@
     out.end_line();
     emit_wait(out.as_bytes());
 
-    Agent::new("miigunner")
+    let mut agent = Agent::new("miigunner");
+    agent
         .game_acmd("game_mcattacks3s", game_mcattacks3s, Priority::Default)
         .game_acmd("game_mcattacks3hi", game_mcattacks3hi, Priority::Default)
         .game_acmd("game_mcattacks3lw", game_mcattacks3lw, Priority::Default)
@@ -389,7 +423,9 @@
         .expression_acmd("expression_mcattacks3s", expression_mcattacks3s, Priority::Default)
         .expression_acmd("expression_mcattacks3hi", expression_mcattacks3hi, Priority::Default)
         .expression_acmd("expression_mcattacks3lw", expression_mcattacks3lw, Priority::Default)
-        .status(Main, *FIGHTER_STATUS_KIND_ATTACK_S3, gunner_attack_s3_main)
-        .install();
+        .status(Main, *FIGHTER_STATUS_KIND_ATTACK_S3, gunner_attack_s3_main);
+    crate::tilt_up__miifighter::register_acmd(&mut agent);
+    agent.status(Main, *FIGHTER_STATUS_KIND_ATTACK_HI3, gunner_attack_hi3_main);
+    agent.install();
 }
```

In addition, `src/tilt_up__miifighter.rs` is added to the plugin crate containing the unit code from `moves/tilt_up__miifighter/unit.rs`.

---

## 5. Offline Verification

- **Asset Generation (`build_assets.py`)**: Executed cleanly (exit 0). Generated `package/fighter/miigunner/motion/body/c00/c01mcmiifighterattackhi3.nuanmb`, reference `motion_list_vanilla_plus_owned.bin` (46,336 bytes, 775 entries), and `manifest.json`.
- **Verification Script (`check.py`)**: Ran from workspace root (exit 0). Passed all checks:
  - Package files against `manifest.json` (sizes, SHA-256).
  - Reference motion list parsed, validated count (774 -> 775) and flags/cancel frame.
  - Rust hashes and hitbox parameters equal decoded table.
  - Skeletons and bone names verified against Gunner `model.nusktb`.
  - All 3 negative controls passed.
- **Plugin Offline Build (`cargo skyline build`)**: Compiled in scratch copy with target dir `builds/.cache/MV-tilt_up__miifighter-target/` (exit 0).
- **Stack Frames Check (`stack_frames.py`)**: Executed against the built NRO:
  - 134 frame allocations, largest allocation 18,672 bytes (well below 24,576-byte limit on 64 KiB stack). Exit 0: OK.

---

## 6. Evidence Tiers

- **Tier B (Offline Measurement & Verification)**:
  - `motion_list.bin` entry 74 in Brawler and entry 71 in Gunner parsed from game dump.
  - Transform and visibility tracks compared via `ssbh_data_py` (75 transform nodes, 12 visibility nodes).
  - ACMD scripts disassembled and decoded from `lua2cpp_miifighter.nro` via Capstone.
  - Package manifest verification, offline compilation, and stack frame analysis.
- **Tier D (In-Game Console Behavior)**:
  - Actual in-game animation playback, hitbox collision registering 6.0% in Training Mode, sound playback, and cancel timing on hardware.
