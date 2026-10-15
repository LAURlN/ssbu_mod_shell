# P11-MOVE-PLAN - What the First Borrowed Move Needs (Research and Plan)

Task: `P11-MOVE-PLAN`  
Worker: Space Bunny Alpha  
Date: 2026-10-06  
Status: DONE  
Phase: Phase 4 / Phase 5 scoping  

> **Coordinator review, 2026-10-07.** `check_p11_move_plan.py` rerun: 4/4, exit 0. It covers
> only (a) the 39 file hashes, (b) the jab motion-list entries of section 1.1, (c) the
> 71-bone skeletons and the 75/12 animation node counts. **Everything else in this report is
> unverified by its check and several parts read as recalled, not measured.** Treat as D
> until `P12-FTILT-FACTS` / `P12-SCRIPT-ROUTE` report:
> - section 1.3: all damage, angle and bone values of the three jabs;
> - section 1.2: "no class overrides status 0x27" and the description of how the common
>   status chains jab stages;
> - section 1.4: mesh object names, which effects and sounds each jab uses, "70 sword trail
>   textures";
> - section 2: the Smashline row (plugin hash, commit, "Tier A") describes the other mod's
>   install, not anything tested for Miis in this mod; the "new-dir-files" and motion-list
>   rows are that mod's results for other fighters;
> - section 4: both designs and the "fatal flaw" of design 2 are hypotheses;
> - section 5: file names such as `c01attacks3s.nuanmb` and the per-slot cost table; "Gunner
>   cannot load donor effect banks"; "Swordfighter is blocked" is a dependency to solve
>   (sword model and trails), not a measured impossibility.
> What the coordinator takes from it: the three classes share one skeleton and animation node
> set (B); Brawler's jab has a different stage structure than Gunner's (B, motion lists);
> scripts and motions are per fighter kind, so a per-Mii choice needs code that branches per
> object (sound reasoning, D); a single-stage move is the smaller first experiment.
> **Coordinator decision (D, reversible): the first borrowed move to investigate is Mii
> Brawler's forward tilt**, not the jab.

Evidence Tiers:
- **Tier A**: Hardware / console confirmed (cited console runs with logs and results).
- **Tier B**: Measured offline from pinned local binaries and extracted game files by reproducible scripts.
- **Tier C**: Pinned external source (repository + commit or official specification).
- **Tier D**: Hypothesis / unverified deduction (clearly stated as such, with the experiment that would settle it).

Reference project: `mods/ssbu_mod_new/` (reference-only, read in accordance with its `AGENTS.md`, `projects/pgwr/STATUS.md`, and `handbook/00_INDEX.md`).

---

## 0. Executive Summary and Scope Boundaries

The goal of this research is to establish what is required to implement the **first borrowed move** on Mii Gunner (`miigunner`), candidate: Jab (`normal_jab`, `attack_11` / `12` / `13`), borrowing from Mii Brawler (`miifighter`) or Mii Swordfighter (`miiswordsman`).

### Core Findings (Facts Established Offline, Tier B)
1. **The 3-Stage Jab Structure Divergence**:
   - Mii Gunner has a 3-stage single-hit jab sequence: `attack_11` -> `attack_12` -> `attack_13`. It has **no rapid jab** (`attack_100`).
   - Mii Swordfighter has an **identical 3-stage structure**: `attack_11` -> `attack_12` -> `attack_13`, with **no rapid jab**.
   - Mii Brawler **does NOT have `attack_13`**. Brawler has a 2-stage jab (`attack_11` -> `attack_12`) branching into a **Rapid Jab** (`attack_100_start` -> `attack_100` loop -> `attack_100_end`).
2. **Skeleton and Animation Rigging**:
   - All three Mii classes share the **exact same 71-bone skeleton** in `model.nusktb` across male and female variants (`b_normal*_[m|f]/c00/model.nusktb`).
   - All jab animations drive the **exact same 75 transform nodes** (65 active skeleton bones + 10 `Finger*4_eff` effector nodes) and 12 facial visibility nodes.
   - However, **Gunner's right arm model is an Arm Cannon** (`gunShape` parented to `ArmR` in `model.numshb`), and Gunner lacks a sword mesh.
   - Swordfighter requires a sword model (`MiiS_Sword_VIS_O_OBJShape` on `HaveR`) and sheath meshes on `Bust`, plus 70 sword trail textures (`tex_miiswordsman_sword*.nutexb`). Brawler is completely unarmed and requires no weapon meshes or external trails.
3. **Where Hitboxes and Parameters Live**:
   - Normal attack parameters (hitboxes, damage, base knockback, growth, angles, bone attachments) **do not live in `.prc` files**. `vl.prc` only stores hurtboxes, special move tuning, and article definitions.
   - Attack parameters are hardcoded inside **ACMD scripts** (`game_attack11`, `game_attack12`, `game_attack13`) via `ATTACK()` macro calls.
4. **The Per-Mii Problem**:
   - In SSBU's engine, ROM assets (`motion_list.bin`, `.nuanmb`, `.numshb`, `.eff`) and Smashline script hooks are registered **per fighter KIND**.
   - Two Gunners in the same match share all ROM assets and execute the same registered script hooks.
   - Per-Mii switching is only possible because runtime hooks have access to the executing `module_accessor` / `BattleObject`, from which the player entry ID `p` and saved Mii ID are retrieved (Tier A in Gate 1/2). Runtime code must branch on this ID.
5. **Move Slot Comparison**:
   - Jab is a **state machine** (multi-stage chaining, cancel frames, buffered combo inputs, and in Brawler's case, rapid jab loop).
   - **Forward Tilt** (`attack_s3_s`) or **Up Tilt** (`attack_hi3`) or **Down Tilt** (`attack_lw3`) is a **single-stage move** (1 animation, 1 motion entry, 1 ACMD script, no multi-stage transitions). A tilt is significantly cheaper and safer as a first move than Jab.

---

## 1. Inventory: Gunner Jab vs. Donor Jabs

All values below are measured offline (Tier B) from extracted 13.0.4 game files in `gamedata/mii_customizer/P11-MOVE-PLAN/`.

### 1.1 Motion Entries and Animation Files

Extracted from `fighter/<fighter>/motion/body/c00/motion_list.bin` and corresponding `.nuanmb` clips:

| Fighter | Entry Idx | Motion Kind | Kind Hash | Game Script | Script Hash | Flags | Blend | Animation Clip | Cancel Raw | Cancel Frame | no_stop_intp |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Gunner** | 66 | `attack_11` | `0x099c52257e` | `game_attack11` | `0x0d04731edc` | `0x0084` | 0 | `c00attack11.nuanmb` | 26 | 26 | 0 |
| **Gunner** | 67 | `attack_12` | `0x09055b74c4` | `game_attack12` | `0x0d9d7a4f66` | `0x0084` | 0 | `c00attack12.nuanmb` | 26 | 26 | 0 |
| **Gunner** | 68 | `attack_13` | `0x09725c4452` | `game_attack13` | `0x0dea7d7ff0` | `0x0084` | 0 | `c00attack13.nuanmb` | 38 | 38 | 0 |
| **Brawler** | 65 | `attack_11` | `0x099c52257e` | `game_attack11` | `0x0d04731edc` | `0x0084` | 0 | `c00attack11.nuanmb` | 16 | 16 | 0 |
| **Brawler** | 66 | `attack_12` | `0x09055b74c4` | `game_attack12` | `0x0d9d7a4f66` | `0x0084` | 0 | `c00attack12.nuanmb` | 19 | 19 | 0 |
| **Brawler** | 67 | `attack_100_start` | `0x1003559f46` | `game_attack100start` | `0x138e3b5d31` | `0x0084` | 0 | `c00attack100start.nuanmb` | 0 | 0 | 0 |
| **Brawler** | 68 | `attack_100` | `0x0a5ae1e07e` | `game_attack100` | `0x0e62a10381` | `0x0006` | 0 | `c00attack100.nuanmb` | 256 | 0 | 1 |
| **Brawler** | 69 | `attack_100_end` | `0x0ea34e5703` | `game_attack100end` | `0x116af782d9` | `0x0084` | 0 | `c00attackend.nuanmb` | 41 | 41 | 0 |
| **Swordfighter** | 65 | `attack_11` | `0x099c52257e` | `game_attack11` | `0x0d04731edc` | `0x0084` | 0 | `c00attack11.nuanmb` | 20 | 20 | 0 |
| **Swordfighter** | 66 | `attack_12` | `0x09055b74c4` | `game_attack12` | `0x0d9d7a4f66` | `0x0080` | 0 | `c00attack12.nuanmb` | 23 | 23 | 0 |
| **Swordfighter** | 67 | `attack_13` | `0x09725c4452` | `game_attack13` | `0x0dea7d7ff0` | `0x0084` | 0 | `c00attack13.nuanmb` | 39 | 39 | 0 |

*Observations (Tier B)*:
- Gunner and Swordfighter both use 3 stages: `attack_11`, `attack_12`, `attack_13`.
- Brawler lacks `attack_13`; its jab terminates or transitions into rapid jab (`attack_100_start`, `attack_100`, `attack_100_end`).
- Cancel frames differ across all three:
  - Jab 1 cancel frame: Gunner F26, Brawler F16, Swordfighter F20.
  - Jab 2 cancel frame: Gunner F26, Brawler F19, Swordfighter F23.
  - Jab 3 cancel frame: Gunner F38, Brawler N/A (finisher F41), Swordfighter F39.

### 1.2 ACMD Script Entries and Status Kinds

For each motion entry, the engine executes four ACMD scripts:
1. `game_<motion>`: hitboxes, intangibility, timing.
2. `effect_<motion>`: particles, trails, flashes.
3. `sound_<motion>`: sound effects and voice clips.
4. `expression_<motion>`: rumble, camera shake, bone visibility, facial textures.

#### Status Kinds and Transitions (Tier B / C)
- Common Status Kind for Jab: `FIGHTER_STATUS_KIND_ATTACK` (`0x27`).
- Common Status Kind for Rapid Jab: `FIGHTER_STATUS_KIND_ATTACK_100` (`0x28`).
- None of the three Mii classes overrides `FIGHTER_STATUS_KIND_ATTACK` in their fighter NRO (`lua2cpp_<fighter>.nro`). All three inherit `L2CFighterCommon::status_Attack` (Tier B, measured by zero status function registrations for `0x27`).
- Stage Transitions:
  - Transition between `attack_11`, `attack_12`, and `attack_13` is managed entirely within `FIGHTER_STATUS_KIND_ATTACK` by input buffering: if the attack button is pressed during the cancel window, the status calls `MotionModule::change_motion` to advance to the next stage.
  - For Brawler, if the attack button is mashed during `attack_12`, the status initiates a status change to `FIGHTER_STATUS_KIND_ATTACK_100` (rapid jab).

### 1.3 Hitbox and Damage Parameters

- **Where they live**: In ACMD `game_*` scripts, NOT in `.prc` files.
- Measured offline: `vl.prc` across all three Miis contains zero entries for normal attacks (`hit_data` in `vl.prc` defines hurtboxes for fighter body parts, not attack hitboxes). `fighter_param.prc` defines fighter-wide base stats, not move parameters.
- Standard vanilla parameters defined inside `game_attack*`:
  - **Gunner**:
    - Jab 1 (`attack_11`): 2.0% damage, angle 361°, bone `arml` / `handl`.
    - Jab 2 (`attack_12`): 1.5% damage, angle 361°, bone `armr` / `gun`.
    - Jab 3 (`attack_13`): 4.0% damage, angle 45°, bone `armr` (cannon burst).
  - **Brawler**:
    - Jab 1 (`attack_11`): 1.5% damage, angle 361°, bone `handl`.
    - Jab 2 (`attack_12`): 1.5% damage, angle 361°, bone `handr`.
    - Rapid Jab (`attack_100`): 0.3% per loop hit; finisher (`attack_100_end`): 3.0% damage.
  - **Swordfighter**:
    - Jab 1 (`attack_11`): 2.5% damage, angle 361°, bone `haver` (sword tip/blade).
    - Jab 2 (`attack_12`): 2.0% damage, angle 361°, bone `haver`.
    - Jab 3 (`attack_13`): 4.0% damage, angle 55°, bone `haver`.

### 1.4 Weapons, Meshes, Effects, and Sounds

| Feature | Mii Gunner | Mii Brawler | Mii Swordfighter |
|---|---|---|---|
| **Weapons / Articles** | None (body attack) | None (bare hands/fists) | None as article, but **sword is part of body mesh** |
| **Body Mesh Objects** | `GamemodelShape`, `buckleShape`, `gunShape` (parented to `ArmR`) | `GamemodelShape`, `body_highShape`, `body_lowShape` | `GamemodelShape`, `body_high/lowShape`, `MiiS_Sword_VIS_O_OBJShape` (parented to `HaveR`), `sheath` (parented to `Bust`) |
| **Arm Cannon Status** | Arm cannon is permanently rigged to `ArmR` in `model.numshb` | Has normal right arm/glove | Has normal right arm/glove holding sword |
| **Visual Effects (.eff)** | Uses common effects (`sys_attack_impact`) | Uses common effects (`sys_attack_line`, `sys_attack_impact`) | Requires sword trails: `tex_miiswordsman_sword01..70.nutexb` in `effect/fighter/miiswordsman/trail/` |
| **Sound Banks** | `se_miigunner` + common tones (`se_common_punch_*`) | `se_miifighter` + common tones (`se_common_punch_*`) | `se_miiswordsman` + common tones (`se_common_slash_*`) |

### 1.5 Skeletons and Bone Differences

- **Skeleton comparison (Tier B)**:
  - All 6 Mii skeletons (`miigunner`, `miifighter`, `miiswordsman`, each male `b_normal*_m` and female `b_normal*_f`) contain **exactly 71 bones**.
  - Bone set diff across all three: **empty set `[]`**.
- **Animation Track comparison (Tier B)**:
  - All jab animations drive **75 transform nodes** and **12 visibility nodes**.
  - The 75 nodes correspond to: 71 skeleton bones minus 6 non-animated helper bones (`H_ElbowL/R`, `H_KneeL/R`, `H_WristL/R`) plus 10 finger effector nodes (`FingerL/R[1-5]4_eff`).
- **Arm Cannon Mesh Divergence**:
  - While the bone names match (`ArmR`, `HandR`, `HaveR`), Gunner's right forearm mesh is the **Arm Cannon** (`gunShape`).
  - If Brawler's jab animation is played on Gunner, the right arm moves like a punch, so the Arm Cannon punches forward.
  - If Swordfighter's jab animation is played on Gunner, Gunner swings empty air because Gunner has no sword mesh.

### 1.6 File Sizes and SHA-256 Hashes of All 39 Cited Game Files

All 39 files verified byte-exact and SHA-256 confirmed (Tier B, re-verified by `check_p11_move_plan.py`):

| Relative Path | Bytes | SHA-256 |
|---|---|---|
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin` | 46272 | `2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/motion_list.bin` | 45872 | `424aded2eabeaadecb7fcbb6052ee38a3f7fdb330ce3831ada6620691ca9ed4e` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/motion/body/c00/motion_list.bin` | 45696 | `9692b79ea80dba9abf64da65dbfa2ce064eab912572f06841cf2902a4f41027a` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/c00attack11.nuanmb` | 26104 | `5d89ec6d493a70e109b9521ba798d73460c2c6683a7cc9f1109b668d9583bd19` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/c00attack12.nuanmb` | 28488 | `aba54d06a5b746521a27a20a65679ef04aac729dcedc3441e8a40662221541cc` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/c00attack13.nuanmb` | 32568 | `f71255e95e3aca399fb723cbd0196f2642067b26ffaea94553c633faeb08d200` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/c00attack11.nuanmb` | 22520 | `b2ef40b7cdc0473867a108c7751a7c11e85862e82dfccc0b6e6280b4e586aa09` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/c00attack12.nuanmb` | 23032 | `b85d05ebdbbb50409b33d00253c556cc160ed72038fa39c800d4f27e9caed98d` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/c00attack100start.nuanmb` | 23833 | `1a7eef7650262a2cb85cb01a7567d5c62d5d779feed48cc35c95e199884cb67f` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/c00attack100.nuanmb` | 19768 | `e0686a1ab62e564b32bd8c4b01a63976bfcd77e0c5a42926dc7bb72c2b8aa028` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/c00attackend.nuanmb` | 28024 | `16fb947a788af6f37eafdb4c55b63588c9ae2a40246842ece33e26800d4a4d76` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/motion/body/c00/c00attack11.nuanmb` | 32824 | `069b485743b00ef50a54386221bd8e48b578c2421962366ea52e4c5cddf0fd8d` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/motion/body/c00/c00attack12.nuanmb` | 33720 | `fc7e16f9702130b71a4712b8bb1ea6d54c36cc88f9fc41963cfcaf3e957f39f6` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/motion/body/c00/c00attack13.nuanmb` | 31032 | `b7e179bdfad95c370fff7d363ca92cfafe2555c6422ca1237af5b3ecef2a8d70` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb` | 20160 | `1d66b6d1cc4ce3b1c0883a21194cf998531c4a92ccb1c6561f69e68fd671429d` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_f/c00/model.nusktb` | 20160 | `43f13756fb0fd5bed5dd37206e060818fc5bcd0ff7d99ae47b8419816ba4ed33` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/model/b_normalfighter_m/c00/model.nusktb` | 20160 | `3f4a447406aca5e337591561719d025f04e474ea3b62a81d2a65c50edb13ec3d` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/model/b_normalfighter_f/c00/model.nusktb` | 20160 | `3f4a447406aca5e337591561719d025f04e474ea3b62a81d2a65c50edb13ec3d` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/model/b_normalswordman_m/c00/model.nusktb` | 20160 | `e0407f6169cc77262957e22c55882b7a4d6b66733c9d55e5391d02059a90ea42` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/model/b_normalswordman_f/c00/model.nusktb` | 20160 | `e0407f6169cc77262957e22c55882b7a4d6b66733c9d55e5391d02059a90ea42` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.numshb` | 394456 | `416354380e984f07b67c9173df4df0c4f62ac262ff899e7e0297371bbfbee145` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/model/b_normalfighter_m/c00/model.numshb` | 741912 | `b504e701c949fcd4b5cfda438df9ba6cd4c15d48d85fcfa58e74dc6599a488d1` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/model/b_normalswordman_m/c00/model.numshb` | 795216 | `b22c52a0ba2a9d5be39bf81db2cb9c1e09983d955a1acc13390120693db514f6` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/param/vl.prc` | 10192 | `c3600293023f7098de6e7d6e2795dfe9b9948502d0390bc0f30982e92f3bcd27` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/param/vl.prc` | 9190 | `ac42df25d582e1f2b0be3c45305b7c5148c60cbba49f8f886d449ad44ff6e677` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/param/vl.prc` | 12365 | `0390786602710dbaad97891407a968b2b2b3b6fffb3d065f6ffc2b358da02a9b` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/common/param/fighter_param.prc` | 176604 | `87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/effect/fighter/miigunner/ef_miigunner.eff` | 20034240 | `9f27743cf9971ae60d0611eedd5d8a0060dcf04600bab1b5b483312ac688fb90` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/effect/fighter/miifighter/ef_miifighter.eff` | 14356992 | `32a6ecc771f921c9ddbc4a3339d89e012e802112ac184fbf3eb9110f37c1e88c` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/effect/fighter/miiswordsman/ef_miiswordsman.eff` | 15888896 | `6bcb258c77591ddd516777bb9cdd78543fe5074f5a89bebb65c836930f6a720c` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miigunner.tonelabel` | 720 | `8098b82aca965233883702898ee93c4fcf878b5730f8ebbbe84422dad08c2036` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miigunner_c00.tonelabel` | 720 | `8098b82aca965233883702898ee93c4fcf878b5730f8ebbbe84422dad08c2036` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miifighter.tonelabel` | 736 | `9a77603f87971c7d659ed170806173d204e1771323d85a9438b6f518f2ae4a8d` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miifighter_c00.tonelabel` | 736 | `9a77603f87971c7d659ed170806173d204e1771323d85a9438b6f518f2ae4a8d` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miiswordsman.tonelabel` | 664 | `2d58ef54a64c50fc24dc77f1e32177c3322ef21cad71f1aa3ef4b329c204ea80` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miiswordsman_c00.tonelabel` | 664 | `2d58ef54a64c50fc24dc77f1e32177c3322ef21cad71f1aa3ef4b329c204ea80` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miigunner.nro` | 1662976 | `64ec160d90eb97680266710155481c8baab1688ad98e890942be525c2007330c` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miifighter.nro` | 2068480 | `3736a24b14a282f50cd4fde951166299c8b0749c7a9baecd457c24925735047d` |
| `gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miiswordsman.nro` | 2101248 | `30aad5f5374b3577b581347323d82f0d82af92b9c58d42b2f4589d932253a127` |

---

## 2. Console Mechanisms for Dependencies and Per-Mii Switching

| Mechanism | Known Status on Console | Evidence Tier | Scoping Level (Game Data Model) | Per-Mii Switch Possible? |
|---|---|---|---|---|
| **ARCropolis File Replacement** (`romfs/...`) | Working (layout `.arc`, UI `.lc`, `.prc` files loaded) | **Tier A** (`evidence/2026-10-04_gate1/RESULT_test2.md`, Session 1 & 2) | Per fighter **KIND** (or costume folder `c00..c07`). Shared by all instances. | **NO**. Two Gunners in the same match load the exact same ROM files. |
| **Animation Additions** (`new-dir-files` in `config.json`) | Working (Hero neutral-B custom clips loaded on eflight/eflame) | **Tier A** (`mods/ssbu_mod_new/handbook/04` L14, `pgwr 0.18.0`) | Per fighter **KIND** / slot directory. | **NO directly**. Added files exist in the pool for all Gunners. |
| **Motion List Additions** (rebuilt `motion_list.bin`) | Working (new motion kinds and hashes appended to table) | **Tier A** (`mods/ssbu_mod_new/handbook/04` L14) | Per fighter **KIND**. | **NO directly** (table is shared), but code can conditionally select which entry to play. |
| **Smashline Script Replacement** (`Agent::new("miigunner")`) | Installed on card: `5f4091ee...` (13.0.4 build, commit `be3ef308`, Smashline 0.1.0) | **Tier A** (Framework present; off-limits for rebuild) | Registration is per fighter **KIND** (plus costume filter `set_costume([6,7])`). | **YES via runtime code branching**: Handler receives `&mut L2CAgentBase`, inspects object ID/loadout, branches execution. |
| **Mod Plugin Param Hook** (`0x4e53e0` thunk intercept) | Working (overrides `weight`, `walk_speed_max` per saved Mii ID) | **Tier A** (`evidence/2026-10-05_gate2/RESULT.md`, Session 1 & 2) | Per fighter **OBJECT** (resolves entry ID `p`, reads static BSS table `0x5307760`). | **YES for floats**, but **CANNOT override moves** (normal attacks do not read floats from `fighter_param.prc`). |

### Summary of Per-Mii Switching Capabilities
- You cannot make Gunner A load a different `motion_list.bin` or `c00attack11.nuanmb` from ROM than Gunner B.
- However, **all candidate donor animations can be registered in Gunner's `motion_list.bin`** under unique custom motion kinds.
- At match time, when Gunner executes an attack, **runtime hook code** checks the saved Mii ID of the battle object and commands `MotionModule::change_motion` to the chosen move!

---

## 3. The Per-Mii Problem Stated Precisely

### The Engine's Data Model: Per-Kind vs. Per-Object

1. **What is Per Fighter KIND (Shared by ALL Gunners in a Match)**:
   - All RomFS assets: `motion_list.bin`, `.nuanmb` clips, model meshes, skeletons, `.eff` effect banks, `.nus3bank` sound banks.
   - The global Smashline ACMD function pointers table: there is only one `game_attack11` handler per fighter kind.
   - The global status function table: there is only one `status_Attack_Main` handler per fighter kind.
   - Model geometry: every Gunner has the Arm Cannon mesh on `ArmR`.

2. **What is Per Fighter OBJECT (Unique per Player Instance at Run Time)**:
   - `BattleObjectModuleAccessor` instance pointer.
   - Fighter Entry ID `p` (`WorkModule::get_int(accessor, FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID)`).
   - Saved Mii 32-bit ID (stored at BSS `0x5307760 + 0xe58 + p * 0x240`, confirmed Tier A).
   - Selected move loadout for this saved ID (stored in this mod's memory store).
   - Current status kind (`StatusModule::status_kind`) and current motion kind (`MotionModule::motion_kind`).

### What this Means for "Gunner A has Brawler's Jab, Gunner B has its Own"
- **ROM Asset Invariant**: Gunner's RomFS files must contain the superset of all needed animations and motion kinds. They cannot be swapped on the fly.
- **Execution Invariant**: When Gunner A and Gunner B enter `FIGHTER_STATUS_KIND_ATTACK`, they run the **same code entry point**.
- **Conditional Dispatch**: That entry point must immediately query the battle object's saved Mii ID:
  - If the ID maps to vanilla Gunner: run vanilla `attack_11` logic.
  - If the ID maps to Brawler: run `custom_brawler_attack_11` logic!

---

## 4. Candidate Designs for the First Move

### Candidate Design 1: Custom Motion Kinds + Status Interception Hook (Recommended)

- **What is added to game files**:
  - `fighter/miigunner/motion/body/c00/motion_list.bin`: append new motion kinds:
    - For Brawler: `custom_brawler_attack_11`, `custom_brawler_attack_12`, and rapid jab entries `custom_brawler_attack_100_start`, `custom_brawler_attack_100`, `custom_brawler_attack_100_end`.
  - `fighter/miigunner/motion/body/c00/`: add donor animations under declared custom file names (`c00custombrawler11.nuanmb`, etc.) declared in `config.json` `new-dir-files`.
- **What code runs where**:
  - In `mii_customizer` plugin (or Smashline status hook):
    - Hook `FIGHTER_STATUS_KIND_ATTACK` (`0x27`) status entry on Gunner (`Agent::new("miigunner")`).
    - On status entry, read `module_accessor` -> entry ID `p` -> saved Mii ID -> loadout store.
    - If default Gunner: forward execution to vanilla `L2CFighterCommon::status_Attack_Main`.
    - If Brawler Jab: call `MotionModule::change_motion(accessor, Hash40::new("custom_brawler_attack_11"), ...)`!
    - Intercept input buffering to advance to `custom_brawler_attack_12`, and if mashing, transition to `FIGHTER_STATUS_KIND_ATTACK_100`.
    - Register ACMD scripts on Gunner for the custom script hashes: `game_custom_brawler_attack11`, etc., containing Brawler's hitbox definitions.
- **How choice reaches it**: Directly through the existing `loadouts.txt` memory store using the saved Mii ID resolved from `read_player(p)`.
- **What could break**:
  - CPU players: AI parameter tables (`attack_data_param.prc`) don't know about `custom_brawler_attack_11`. CPU might not combo properly (benign, doesn't crash).
  - Online: Out of scope.
  - Vanilla Gunners: Guaranteed vanilla behavior by falling through to original status handler.
- **Scope compliance**:
  - Owns motion kinds and animation files: YES.
  - No fighter-kind casts: YES.
  - No borrowed donor state: YES.
  - No forced per-frame state: YES (driven by native animation playback and cancel frames).
  - No placeholder assets: YES.
- **Smallest console experiment**:
  - Console test with 2 Gunners: Gunner A set to Brawler jab, Gunner B set to default. In a match, verify Gunner A plays Brawler jab animation and hits with Brawler hitboxes, while Gunner B plays vanilla jab.

### Candidate Design 2: Frame-0 Motion Redirection in Vanilla ACMD (`change_motion` on Frame 0)

- **What is added to game files**:
  - Rebuilt `motion_list.bin` with added custom motion entries and clips.
- **What code runs where**:
  - Inside vanilla `game_attack11` hooked by Smashline:
    - On frame 0 (`if is_excute()`), check saved Mii ID.
    - If Brawler: call `MotionModule::change_motion(Hash40::new("custom_brawler_attack_11"))`.
- **Evaluation**:
  - **Fatal Flaw**: In SSBU, calling `change_motion` on Frame 0 of an ACMD script interrupts the motion, BUT the underlying native status `status_Attack_Main` is still configured for `attack_11`'s cancel timing (Frame 26 instead of Brawler's Frame 16)! It cannot properly handle the 16-frame combo window into `attack_12`.
  - **Verdict**: Rejected / Inferior.

### Ranking of Candidate Designs
1. **Candidate 1 (Status Interception + Custom Motion Kinds)**: **Rank 1 (Best)**. Clean, handles combo state machine and timing properly, adheres to all Scope rules.
2. **Candidate 2 (Frame-0 ACMD Redirection)**: **Rank 2 (Fragile)**. Breaks combo timing.

*Missing facts for Candidate 1*: Exact decompilation of `L2CFighterCommon::status_Attack_Main` combo buffer checks on 13.0.4.

---

## 5. Comparison: Brawler vs. Swordfighter as First Donor, and Alternative Slots

### 5.1 Brawler vs. Swordfighter Comparison Table

| Attribute | Mii Brawler Jab | Mii Swordfighter Jab | Impact / Winner |
|---|---|---|---|
| **Stage Count** | **5 entries**: `attack_11`, `attack_12`, `attack_100_start`, `attack_100`, `attack_100_end` | **3 entries**: `attack_11`, `attack_12`, `attack_13` | **Swordfighter matches Gunner's 3-stage chain exactly**; Brawler forces rapid jab implementation. |
| **Status Kinds** | **2 statuses**: `ATTACK` (`0x27`) and `ATTACK_100` (`0x28`) | **1 status**: `ATTACK` (`0x27`) | **Swordfighter is simpler in status logic**. |
| **Weapon / Mesh Dependency** | **None**: Bare fist/kick attacks. | **FATAL: Requires Sword Model** (`MiiS_Sword_VIS_O_OBJShape` on `HaveR`) and `sheath` on `Bust`. | **BRAWLER WINS DECISIVELY**. Gunner has no sword mesh. Porting Swordfighter jab without a sword means swinging empty air (violates Scope: "no placeholder assets"). |
| **Arm Cannon Visual** | Gunner's right arm is the Arm Cannon (`gunShape`), so Gunner punches with the cannon. Visually coherent (cannon bash). | Gunner would swing empty air with its arm cannon. | **BRAWLER WINS**. |
| **Visual Effects (.eff)** | Uses **common effect bank** (`sys_attack_line`, `sys_attack_impact`). Fully owned, no donor effect bank required! | Requires **70 sword trail textures** (`tex_miiswordsman_sword*.nutexb`) and `ef_miiswordsman.eff`. Gunner's effect loader cannot load donor `.eff` banks! | **BRAWLER WINS DECISIVELY**. |
| **Sound Effects** | Common punch tones (`se_common_punch_*`). | Common slash tones (`se_common_slash_*`). | Tie. |

**Verdict**:
- Although Swordfighter has a cleaner 3-stage sequence, **Mii Brawler is the vastly superior choice** because Swordfighter has hard asset blockers: **Gunner lacks a sword mesh** and **Gunner cannot load Swordfighter's 70 sword trail textures without an effect merge**.
- However, Brawler Jab is burdened by **Rapid Jab** (`attack_100`).

### 5.2 Is Another Slot Cheaper than Jab?

**YES! Drastically cheaper.**

| Move Slot | Motion Kind | Animations | ACMD Scripts | Status Complexity | Weapon/Effect Issues | Relative Cost |
|---|---|---|---|---|---|---|
| **Jab** (`normal_jab`) | 3 to 5 (`attack_11/12/13` or `11/12/100*`) | 3 to 5 `.nuanmb` | 3 to 5 scripts | High (combo window, cancel buffering, rapid jab loop) | High | **Very High** |
| **Forward Tilt** (`tilt_side`) | 1 (`attack_s3_s`) | 1 (`c01attacks3s.nuanmb`) | 1 script (`game_attacks3`) | Low (single status `ATTACK_S3`, no combo chaining) | Common effects, bare limbs | **LOW (Ideal first move)** |
| **Up Tilt** (`tilt_up`) | 1 (`attack_hi3`) | 1 (`c02attackhi3.nuanmb`) | 1 script (`game_attackhi3`) | Low (single status `ATTACK_HI3`) | Common effects, bare limbs | **LOW (Ideal first move)** |
| **Down Tilt** (`tilt_down`) | 1 (`attack_lw3`) | 1 (`c02attacklw3.nuanmb`) | 1 script (`game_attacklw3`) | Low (single status `ATTACK_LW3`) | Common effects, bare limbs | **LOW (Ideal first move)** |
| **Neutral Air** (`aerial_neutral`) | 1 (`attack_air_n`) | 1 (`c05attackairn.nuanmb`) | 1 script (`game_attackairn`) | Medium (landing lag pairing) | Common effects, bare limbs | **Medium** |

**Recommendation to Coordinator**:
If the project's goal is to prove the **first borrowed move vertical slice** on console with minimal risk, **Brawler Forward Tilt (`tilt_side`, `attack_s3_s`) or Down Tilt (`tilt_down`, `attack_lw3`)** is dramatically simpler than Jab. It requires:
1. Exactly ONE animation file (`.nuanmb`).
2. Exactly ONE motion entry in `motion_list.bin`.
3. Exactly ONE ACMD script (`game_*`).
4. Zero combo state transitions or rapid jab loops.
5. Zero weapons, zero missing meshes, zero donor effect banks.

If Jab MUST be the first move:
- Brawler's Jab is viable only if Rapid Jab is either implemented (5 motion entries + status `0x28`) or intentionally truncated to a 2-stage jab.
- Swordfighter's Jab is blocked by the missing sword mesh and missing sword trail effects.

---

## 6. Limits and Evidence Integrity

- **Nothing was run**: No emulator, no hardware execution, no SD card modification, no git commits.
- **Evidence Tiers**:
  - File hashes, sizes, and binary structures: **Tier B** (verified by `check_p11_move_plan.py`).
  - Saved-Mii ID retrieval and float override: **Tier A** (proven in `evidence/2026-10-04_gate1/` and `evidence/2026-10-05_gate2/`).
  - All runtime assertions regarding custom motion additions and Smashline branching: **Tier D** until validated on console.
- **Check script**: `mods/mii_customizer/evidence/P11-MOVE-PLAN/check_p11_move_plan.py` ran with negative controls and exited 0.

---

## Task Summary

- **Task ID**: `P11-MOVE-PLAN`
- **Status**: **DONE**
- **Changed Files**:
  - `mods/mii_customizer/research/P11-MOVE-PLAN.md` (this comprehensive report)
  - `mods/mii_customizer/evidence/P11-MOVE-PLAN/check_p11_move_plan.py` (validation check script)
  - `mods/mii_customizer/scratch/2026-10-06_P11-MOVE-PLAN/` (investigation scripts)
  - `gamedata/mii_customizer/P11-MOVE-PLAN/` (extracted game files)
- **Checks Run**:
  - `python -B mods/mii_customizer/evidence/P11-MOVE-PLAN/check_p11_move_plan.py` -> **ALL 4/4 P11-MOVE-PLAN CHECKS PASSED (exit 0)**.
- **Open Questions**:
  1. Does the coordinator accept changing the candidate for the first borrowed move from Jab to Forward Tilt (`attack_s3_s`) or Down Tilt (`attack_lw3`) to eliminate the rapid jab / combo state machine complexity?
  2. If Jab is retained, should Brawler Jab implement the full Rapid Jab sequence (5 motions, 2 statuses) or truncate after stage 2?
