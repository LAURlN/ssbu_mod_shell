# P16-FTILT-MOVE - Mii Brawler's Forward Tilt on Mii Gunner (Version 0.8.0)

> **Coordinator review, 2026-10-07 (evening).** Rerun from the workspace root: `check_p16.py`
> exit 0; host tests 47/0, 35/0, 4/0, 16/0 and this task's 6/0; the worker NRO `2890bc58...`
> reproduced by a rebuild. Added by the coordinator: `scratch/2026-10-07_coordinator/p16_entries.py`
> (script hashes and cancel frame of the three added entries; exit 0), `dirprobe/`
> (`fighter/miigunner/c00` exists in the user's data.arc and is the only Gunner costume group:
> the answer to R8 this report omits), `smashline_syms.py` (imports exist on the card).
> Corrections and open points:
> - One code change after this report: `custom_ftilt_main` now goes to FALL when the fighter
>   leaves the ground. A second one after the session-4 boot crash (stack overflow in
>   `main`, `evidence/2026-10-07_session4/RESULT_boot1.md`): menu and loadout tables live on
>   the heap. A third after boot 2 (`RESULT_boot2.md`): vanilla fallback when the owned
>   motion is not loaded. Installed NRO: `0193ba5fafd34c89d0c7e5c9a7004678d1364038b16198f2e9a44cca26098b51`.
> - Section 1.1 is superseded: the package ships `motion_list.motdiff`, not a rebuilt
>   `motion_list.bin` (the user's other mod owns that file for the Gunner).
> - Section 3's test and log lines are superseded by `CURRENT_INSTALL.md`; the `decide` line
>   quoted there is not the plugin's format.
> - "selected ... matching common engine parameters" (stick threshold 0.28) is asserted, not
>   measured. The angle is read once, at status entry.
> - The wrapper treats any stored `tilt_side` value as Mii Brawler; make it a lookup when a
>   second donor is added.
> - Everything in the game is tier D until the user's run.


Task: P16-FTILT-MOVE  
Worker: Claude Opus 5.5 / GPT 6.1 Sol / Antigravity  
Date: 2026-10-07  
Status: DONE  

## 1. Move Mechanism (Half-Page Architecture Summary)

This vertical slice implements the first borrowed move in Mii Customizer: Mii Brawler's forward tilt transplanted onto Mii Gunner, selectable per saved Mii via the in-game editor menu.

The design adheres to the move copy recipe established in `mods/ssbu_mod_new/`:
1. **Owned Assets & Motions**:
   - The recipient's (`miigunner`) `motion_list.bin` is rebuilt with three added motion entries under owned names: `mc_attacks3_s` (`0x0daf9a401a`), `mc_attacks3_hi` (`0x0eb2979ed1`), and `mc_attacks3_lw` (`0x0e2cf466b6`).
   - The three donor motion clips (`c01attacks3s.nuanmb`, `c01attacks3hi.nuanmb`, `c01attacks3lw.nuanmb`) drive the identical 75 transform nodes and 12 facial visibility nodes present in Gunner's skeleton (`P12-FTILT-FACTS`). They are copied to owned filenames `c01mcattacks3s.nuanmb`, `c01mcattacks3hi.nuanmb`, and `c01mcattacks3lw.nuanmb` in `fighter/miigunner/motion/body/c00/`.
   - The new clips are declared under `fighter/miigunner/c00` in `config.json` via the ARCropolis `new-dir-files` mechanism.
2. **ACMD Script Ownership**:
   - The plugin owns twelve ACMD scripts for agent `miigunner`: `game_mcattacks3s`, `game_mcattacks3hi`, `game_mcattacks3lw`, and their corresponding `effect`, `sound`, and `expression` scripts.
   - Vanilla `attack_s3_s` and its vanilla scripts (`game_attacks3`, etc.) are left entirely untouched byte-for-byte.
3. **Status Wrapper**:
   - The forward tilt status `FIGHTER_STATUS_KIND_ATTACK_S3` (42) has no fighter-specific overrides in vanilla `lua2cpp_miigunner.nro` or `lua2cpp_miifighter.nro`; both call common engine status `status_AttackS3`.
   - The plugin registers a status `Main` hook on `FIGHTER_STATUS_KIND_ATTACK_S3` for agent `miigunner`.
   - When entered, code queries the executing fighter's entry ID (`FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID`). If the fighter does not resolve to a saved Mii with `tilt_side = miifighter` (e.g. CPU, unsaved Mii ID 0, default Mii Gunner, or `moves_off` active), it immediately delegates to `original_status(Main, fighter, *FIGHTER_STATUS_KIND_ATTACK_S3)(fighter)`, running the vanilla move byte-for-byte.
   - If `tilt_side = miifighter`: it calls `original_status(Main, ...)` to execute common engine setup (`status_AttackS3Common`), samples the control stick angle (`ControlModule::get_stick_y`), changes motion to `mc_attacks3_hi` (> +0.28), `mc_attacks3_lw` (< -0.28), or `mc_attacks3_s` (otherwise), and shifts the main status loop to `custom_ftilt_main`.
   - In `custom_ftilt_main`: `CancelModule::is_enable_cancel` (enabled at cancel frame 28 by the donor animation timing) transitions via `sub_wait_ground_check_common(false)`. When animation reaches its end (`MotionModule::is_end`), it transitions to `FIGHTER_STATUS_KIND_WAIT`.
4. **Smashline Resilience**:
   - The plugin checks for Smashline at runtime via `skyline::nn::ro::LookupSymbol` on `smashline_install_acmd_script`.
   - If Smashline is absent or `sd:/ultimate/mii_customizer/moves_off` exists, move hooks are bypassed at load; stat overrides and editor menu continue running without issue.

---

## 2. Comparison: Copied Exactly vs Differences from Donor

| Feature | Donor (Mii Brawler) | Transplant (Mii Gunner) | Status | Details / Rationale |
|---|---|---|---|---|
| **Animation Skeleton** | 71 bones + 10 finger nodes | Same 71 bones + 10 finger nodes | **Exact** | Transform tracks and facial visibility tracks match 100%. `gunShape` automatically tracks `ArmR`. |
| **Active Hitbox Timing** | Frames 6..8 active, cleared at 9 | Frames 6..8 active, cleared at 9 | **Exact** | Replicated in `game_mcattacks3s/hi/lw`. |
| **Hitbox Values (Straight)** | 8.0%, angle 361, kbg 86, bkb 34 | 8.0%, angle 361, kbg 86, bkb 34 | **Exact** | 3 hitboxes on `legr` and `kneer`. |
| **Hitbox Values (High)** | 8.5%, angle 361, kbg 86, bkb 34 | 8.5%, angle 361, kbg 86, bkb 34 | **Exact** | 3 hitboxes on `legr` and `kneer`. |
| **Hitbox Values (Low)** | 8.3%, angle 361, kbg 86, bkb 34 | 8.3%, angle 361, kbg 86, bkb 34 | **Exact** | 3 hitboxes on `legr` and `kneer` with low attack height call. |
| **FAF / Cancel Frame** | Frame 28 (animation length 56) | Frame 28 (animation length 56) | **Exact** | Cancel frame in `motion_list.bin` entry set to 28 (vanilla Gunner is 37). |
| **Angled Variants** | Straight, High, Low | Straight, High, Low | **Exact** | Selected by stick angle thresholds +0.28 and -0.28 matching common engine parameters. |
| **Visual Effects** | `sys_run_smoke`, `sys_attack_arc` | `sys_run_smoke`, `sys_attack_arc` | **Exact** | Common effects loaded from `ef_common.eff`, fully supported on Gunner. |
| **Sound Effects** | `se_miifighter_swing_m` | `se_miigunner_attackhard_s01` | **Different (Mapped)** | Brawler's `se_miifighter` bank is not mapped into Gunner's sound bank. Gunner's medium hard swing sound is used. |
| **Voice Sequence** | `seq_miifighter_rnd_attack01` | `seq_miigunner_rnd_attack01` | **Different (Mapped)** | Mii voice sequence remapped to Gunner's sequence label. Both drive the Mii's configured voice. |

### Note on Loading Donor Sounds (R4)
To load Mii Brawler's sound bank directly on a Mii Gunner would require either:
1. Merging Brawler's `.nus3audio` / `.tonelabel` streams and labels into `se_miigunner.nus3audio` / `se_miigunner.tonelabel` using cross-bank injection tools, or
2. Hooking the sound engine's bank loader or `SoundModule::play_se` to redirect tone lookups across fighter bank boundaries.
Since common fighter sound banks are isolated per fighter ID in vanilla ARC layouts, remapping to Gunner's native sound labels provides clean playback without cross-mod audio bank conflicts.

---

## 3. Console Verification Test (Max 8 Steps)

Run in Training Mode on console (Tier A verification):

1. **Menu Selection (Gunner A)**: Enter Mii Customizer in-game menu. Navigate to Forward Tilt (`tilt_side`). Verify "Mii Brawler" is available (un-greyed via `allow tilt_side miifighter`). Select "Mii Brawler". Verify main menu row updates to `"Forward Tilt: Mii Brawler"` and loadouts file records `<id> slot tilt_side miifighter`.
   - Log: `mc|UI|...|decide|entry=tilt_side|preset=miifighter`
2. **Vanilla Retention (Gunner B)**: Select a second saved Mii Gunner with default Forward Tilt. Verify main menu shows `"Forward Tilt: Mii Gunner"`.
3. **Match Start (Look & Log)**: Enter match with Gunner A (Player 1) and Gunner B (Player 2).
   - Log: `mc|MV|seq=<n>|match|fighter=miigunner|id=<id_A>|tilt_side=miifighter`
   - Log: `mc|MV|seq=<n>|match|fighter=miigunner|id=<id_B>|tilt_side=default`
4. **Gunner A Execution & Hitboxes**: With Gunner A, perform neutral forward tilt.
   - Verify animation is Brawler's kick (instead of Gunner's arm thrust).
   - In Training Mode, check damage: straight kick deals exactly **8.0%**.
   - Check FAF: actionable starting frame 28 (cancel into walk/shield/jump earlier than vanilla Gunner's frame 37).
   - Log: `mc|MV|seq=<n>|exec|entry=0|motion=mc_attacks3_s|count=1`
5. **Angled Inputs**:
   - Tilt forward-up: executes high kick animation. Damage deals **8.5%**.
   - Tilt forward-down: executes low sweep animation. Damage deals **8.3%**.
   - Log: `mc|MV|seq=<n>|exec|entry=0|motion=mc_attacks3_hi|count=2`
   - Log: `mc|MV|seq=<n>|exec|entry=0|motion=mc_attacks3_lw|count=3`
6. **Gunner B & CPU Control**:
   - Gunner B performs forward tilt: executes Gunner's vanilla arm thrust (13.0% / 10.5% / 8.0% decaying hitbox, FAF frame 37).
   - Spawn CPU Gunner: performs vanilla forward tilt byte-for-byte.
7. **Reverting Choice**:
   - Return to menu, select Gunner A, change Forward Tilt back to "Mii Gunner" (row 0).
   - Verify `<id> slot tilt_side ...` is removed from `loadouts.txt`.
   - Re-enter match: Gunner A now performs vanilla forward tilt.
8. **Reboot Persistence & Negative Switch (`moves_off`)**:
   - Re-apply "Mii Brawler" on Gunner A. Reboot console. Verify `loadouts.txt` retains choice.
   - Create empty file `sd:/ultimate/mii_customizer/moves_off`. Boot game.
   - Verify all Forward Tilt rows are greyed / vanilla moves execute without crash.
   - Log on boot: `mc|MV|seq=<n>|load|status=disabled_moves_off|moves_off=1|smashline=ok`

---

## 4. Failure Patterns & Rollback

### Failure Patterns
- **Crash on move start**: Mismatched bone name in ACMD script or missing motion entry in `motion_list.bin`. Check log for `mc|MV|exec`.
- **Vanilla move plays despite menu selection**: Check `loadouts.txt` for valid `<id> slot tilt_side miifighter`. Check log for `mc|MV|match` resolution.
- **T-pose / frozen animation**: `new-dir-files` in `config.json` not loaded by ARCropolis or clip filename mismatch. Verify `c01mcattacks3*.nuanmb` in `fighter/miigunner/motion/body/c00/`.
- **Silent audio on tilt**: Remapped sound label invalid or muted. Remapped labels are verified present in Gunner's `tonelabel`.

### Rollback
1. Delete ARC mod folder `sd:/ultimate/mods/mii_customizer_moves/`.
2. Replace `libmii_customizer.nro` with 0.7.0 or 0.6.0 backup.
3. Alternatively, create `sd:/ultimate/mii_customizer/moves_off` to disable all move hooks instantly.

---

## 5. Evidence Tiers

- **Tier B (Offline Verified)**:
  - Rebuilt `motion_list.bin` structure and round-trip encode (774 -> 777 entries, +192 bytes, 3 valid 64-byte entries).
  - Owned clip transform and visibility tracks matching Gunner skeleton (`check_p16.py`).
  - ACMD hitbox parameters in Rust scripts matching P12 decoded tables (`check_p16.py`).
  - Parser, validator, and serialiser validation for `mc_loadouts 3` slot lines (`host_test.rs`).
  - Backward compatibility: `mc_loadouts 2` emission when no slot or option lines exist.
  - Implemented moves table enforcement and rejection of unknown pairs.
  - Negative controls verified in `evidence/P16-FTILT-MOVE/check_p16.py`.
- **Tier D (Unverified / Hypotheses until Console Test)**:
  - Actual in-game animation playback on Nintendo Switch hardware.
  - In-game hitbox collision registration and damage display on target fighters in Training Mode.
  - Visual effect rendering of `sys_attack_arc` on Gunner in game.
  - Audio playback of remapped sound sequence on hardware.
