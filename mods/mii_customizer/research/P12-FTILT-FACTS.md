# P12-FTILT-FACTS - Mii Brawler's forward tilt, measured

> **Coordinator review, 2026-10-07.** Finished by the takeover worker in about fifteen
> minutes from the first worker's tables. `check_p12_ftilt_facts.py` rerun: all checks
> passed, exit 0 (`--neg` not rerun). Read, not independently re-derived: the decoded
> hitbox values, the dependency table, the status scan. Accepted as reference for
> `prompts/P16-FTILT-MOVE.md`; a wrong value here shows up in training mode, which is the
> test that counts. Points the coordinator takes: Brawler's tilt has three angled motions,
> the Gunner's one; cancel frame 28 against 37; effects are common; the two sounds are
> Brawler's own and not loadable by a Gunner today; no status override in either class.


Task: `P15-FTILT-TAKEOVER` (finishing `P12-FTILT-FACTS`)  
Worker: Antigravity  
Date: 2026-10-07  
Status: DONE  

Evidence tiers as in the mod AGENTS.md:
- A: console evidence
- B: offline measurement re-read by `evidence/P12-FTILT-FACTS/check_p12_ftilt_facts.py`
- C: pinned external source
- D: hypothesis / unverified

Inputs (all hashed directly from the workspace):
| File | SHA-256 | Size (bytes) |
|---|---|---|
| `gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miifighter.nro` | `3736a24b14a282f50cd4fde951166299c8b0749c7a9baecd457c24925735047d` | 2068480 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miigunner.nro` | `64ec160d90eb97680266710155481c8baab1688ad98e890942be525c2007330c` | 1662976 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miiswordsman.nro` | `30aad5f5374b3577b581347323d82f0d82af92b9c58d42b2f4589d932253a127` | 2101248 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_m/c00/model.nusktb` | `1d66b6d1cc4ce3b1c0883a21194cf998531c4a92ccb1c6561f69e68fd671429d` | 20160 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/model/b_normalgunner_f/c00/model.nusktb` | `43f13756fb0fd5bed5dd37206e060818fc5bcd0ff7d99ae47b8419816ba4ed33` | 20160 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/model/b_normalfighter_m/c00/model.nusktb` | `3f4a447406aca5e337591561719d025f04e474ea3b62a81d2a65c50edb13ec3d` | 20160 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/model/b_normalfighter_f/c00/model.nusktb` | `3f4a447406aca5e337591561719d025f04e474ea3b62a81d2a65c50edb13ec3d` | 20160 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/model/b_normalswordman_m/c00/model.nusktb` | `e0407f6169cc77262957e22c55882b7a4d6b66733c9d55e5391d02059a90ea42` | 20160 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miigunner/motion/body/c00/motion_list.bin` | `2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba` | 46272 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miifighter/motion/body/c00/motion_list.bin` | `424aded2eabeaadecb7fcbb6052ee38a3f7fdb330ce3831ada6620691ca9ed4e` | 45872 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/fighter/miiswordsman/motion/body/c00/motion_list.bin` | `9692b79ea80dba9abf64da65dbfa2ce064eab912572f06841cf2902a4f41027a` | 45696 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/effect/fighter/miifighter/ef_miifighter.eff` | `32a6ecc771f921c9ddbc4a3339d89e012e802112ac184fbf3eb9110f37c1e88c` | 14356992 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/effect/fighter/miigunner/ef_miigunner.eff` | `9f27743cf9971ae60d0611eedd5d8a0060dcf04600bab1b5b483312ac688fb90` | 20034240 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miifighter.tonelabel` | `9a77603f87971c7d659ed170806173d204e1771323d85a9438b6f518f2ae4a8d` | 736 |
| `gamedata/mii_customizer/P11-MOVE-PLAN/sound/bank/fighter/se_miigunner.tonelabel` | `8098b82aca965233883702898ee93c4fcf878b5730f8ebbbe84422dad08c2036` | 720 |
| `gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miigunner/motion/body/c00/c01attacks3s.nuanmb` | `cce167a2ea41cda96167808c9407f9243182b8d7b63751d91a90ca091acd36ef` | 30840 |
| `gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miifighter/motion/body/c00/c01attacks3s.nuanmb` | `8321c7b73c7ea667342480cec5b05a7ed0e1135b88ecb6171d5eb1c7efc4ecbb` | 40184 |
| `gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miifighter/motion/body/c00/c01attacks3hi.nuanmb` | `1771910ca79fbd0003224c35ee89062069b2a284c778fec7abbe2278c011e233` | 39800 |
| `gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miifighter/motion/body/c00/c01attacks3lw.nuanmb` | `e835ac586a9924b80766cc0a6eeb31594663daeea5af007efae24671fe294d41` | 40056 |
| `gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miiswordsman/motion/body/c00/c01attacks3s.nuanmb` | `39bf0dff673825b1dde3755c3f8fea2126075ceb556d9367d04e4c2b3d2abaee` | 35320 |
| `gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miigunner/model/b_normalgunner_f/c00/model.numshb` | `e63c36a1dcb6fdae21d621404e25af816a3e7d121c9961a0d6e64549d52350b2` | 397160 |
| `gamedata/mii_customizer/P12-FTILT-FACTS/fighter/miifighter/model/b_normalfighter_f/c00/model.numshb` | `2c29d651ca40bf37c0a9b81ae7e614693695548d91381c327171500555e9f8d2` | 747936 |
| `gamedata/mii_customizer/P12-FTILT-FACTS/effect/system/common/ef_common.eff` | `8ff5bad0681cc922dfc4988acfb0212def0514d717bb62b4df17b916d04e0023` | 33453584 |
| `gamedata/mii_customizer/P12-FTILT-FACTS/sound/bank/fighter/se_miifighter.nus3audio` | `4403475694640d1e92e31863db9bdaa7422acaa5d79d131bbf2eb2542edb35db` | 912640 |
| `gamedata/mii_customizer/P12-FTILT-FACTS/sound/bank/fighter/se_miigunner.nus3audio` | `737d102deba8e5cd9ec67d3fdb8fa27f835d6c2ac185386706c29d2e6f278cb3` | 1311040 |
| `gamedata/mii_customizer/P12-FTILT-FACTS/sound/sequence/fighter/common.sqb` | `5dac3404b5b275365604b25864f68d9f8719decf1fb3a1e1a2e3d1f45c269a00` | 132 |
| `gamedata/mii_customizer/P12-FTILT-FACTS/sound/sequence/fighter/miifighter.sqb` | `1fc365058843393190855780cb00af018d53764f9f60d43287c4cc9b78757eee` | 1392 |
| `gamedata/mii_customizer/P12-FTILT-FACTS/sound/sequence/fighter/miigunner.sqb` | `9bbc64ab95f14cd2a9e2b7aa296b194164616da0d94f6545e47b9589c178da58` | 1312 |

---

## Short answers

- **Q1 (Motion entries)**:
  - `miigunner` has 1 entry: index 70 (`attack_s3_s`, kind `0x0b7dd72b57`, anim `c01attacks3s.nuanmb`, flags `0x0080`, cancel frame 37). Animation length: 52 frames (final_frame_index 51.0).
  - `miifighter` has 3 entries with angled variants:
    - index 71: `attack_s3_hi` (kind `0x0cba28ee97`, anim `c01attacks3hi.nuanmb`, flags `0x0084`, cancel frame 28). Animation length: 56 frames (final_frame_index 55.0).
    - index 72: `attack_s3_s` (kind `0x0b7dd72b57`, anim `c01attacks3s.nuanmb`, flags `0x0084`, cancel frame 28). Animation length: 56 frames (final_frame_index 55.0).
    - index 73: `attack_s3_lw` (kind `0x0c244b16f0`, anim `c01attacks3lw.nuanmb`, flags `0x0084`, cancel frame 28). Animation length: 56 frames (final_frame_index 55.0).
  - `miiswordsman` has 1 entry: index 69 (`attack_s3_s`, kind `0x0b7dd72b57`, anim `c01attacks3s.nuanmb`, flags `0x0084`, cancel frame 35). Animation length: 46 frames (final_frame_index 45.0).
  - *Correction from leftover table*: The previous worker left all animation frame counts as `null` in `anim_ftilt_clips.json`; all have now been measured and verified via `final_frame_index`.
- **Q2 (Scripts)**:
  - `miifighter` registers 3 game scripts (`game_attacks3` at reg 0x43cc4 / impl 0x152c60; `game_attacks3hi` at reg 0x43ca8 / impl 0x153cb0; `game_attacks3lw` at reg 0x43ce0 / impl 0x151ba0), 3 effect scripts (reg 0x4776c / impl 0x9e550, reg 0x47750 / impl 0x9eae0, reg 0x47788 / impl 0x9dfc0), 3 sound scripts sharing 1 implementation (impl 0x179c90, regs 0x45bac, 0x45bc8, 0x45be4), and 3 expression scripts sharing 1 implementation (impl 0xdcba0, regs 0xa8760, 0xa8744, 0xa877c).
  - Brawler `game_attacks3` has active hitboxes on frames 6..8 (3 hitboxes on `legr` and `kneer`, 8.0% damage, 361°, kbg 86, bkb 34; ends at frame 9 via `AttackModule::clear_all_impl`).
  - Gunner `game_attacks3` (reg 0x47e4c / impl 0xed530) has motion slowdown at frame 2 (rate 0.625), rate restoration at frame 10 (rate 1.0), and 3 decaying hitboxes on `top` (13.0% at f10, 10.5% at f12, 8.0% at f14), ending at frame 16.
- **Q3 (Dependencies of Brawler scripts)**:
  - Bones: `legr` (`LegR`), `kneer` (`KneeR`), `top` (fighter origin). All exist in Gunner's model / engine. Available without mod: YES.
  - Effects: `sys_run_smoke`, `sys_attack_arc`. Both are common system effects in `ef_common.eff`. Available without mod: YES.
  - Sounds: `se_miifighter_swing_m` and `seq_miifighter_rnd_attack01`. Both are fighter-specific to Brawler (`se_miifighter.tonelabel` tone idx 25 and `miifighter.sqb` offset 92). Neither exists in Gunner's sound bank/sequence. Available without mod: NO.
  - Articles/weapons: None used by any forward-tilt script. Available without mod: YES.
- **Q4 (Status)**:
  - Forward tilt runs under standard common fighter status `FIGHTER_STATUS_KIND_ATTACK_S3` (enum value 42 / 0x2a).
  - Neither `lua2cpp_miifighter.nro` nor `lua2cpp_miigunner.nro` registers status functions for `ATTACK_S3` (0 overrides across all 731 status function registrations in both NROs). Both rely entirely on the engine's common attack status. Validated via positive controls on `FIGHTER_STATUS_KIND_SPECIAL_N` (0xe4), which both classes override.
- **Q5 (Animation compatibility)**:
  - Transform tracks: 75 identical nodes in Brawler and Gunner clips (symmetric difference is empty set `set()`). Matches the 71-bone Mii skeleton + 10 finger helper effect nodes - 6 constraint bones.
  - Visibility tracks: 12 identical facial expression tracks (`MiiFighterM_eye_*`, `MiiFighterM_mouth_*`). Diff is empty set.
  - Material tracks: 0 in all tilt clips.
  - Mesh objects: Gunner has `gunShape` (parented to `ArmR`) and `buckleShape`; Brawler lacks these and has `body_highShape` / `body_lowShape`. Brawler animation does not drive mesh objects directly; `gunShape` tracks `ArmR` in Gunner's skeleton hierarchy automatically.
- **Q6 (Closure list)**:
  - Every asset and runtime requirement classified into Measured (B) vs Assumed (D). The animation, hitboxes, and effects are fully compatible offline; only sound playback requires donor bank handling or custom mapping.

---

## Q1. Motion entries

All motion entries for the forward-tilt family were extracted from `fighter/<class>/motion/body/c00/motion_list.bin` for all three Mii classes and verified bit-for-bit:

### Forward-tilt motion entry table
| Class | Index | Motion Kind | Kind Hash | Game Script | Expression Script | Sound Script | Effect Script | Flags | Blend | Anims | Cancel Frame | Raw Size |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `miigunner` | 70 | `attack_s3_s` | `0x0b7dd72b57` | `0x0d28325277` | `0x137f8a3d23` | `0x0e43cef37d` | `0x0fb1b90bcf` | `0x0080` | 0 | `c01attacks3s.nuanmb` | 37 | 28 |
| `miifighter` | 71 | `attack_s3_hi` | `0x0cba28ee97` | `0x0f3d88dd77` | `0x153e526e56` | `0x1066b6cd7f` | `0x110323891c` | `0x0084` | 0 | `c01attacks3hi.nuanmb` | 28 | 28 |
| `miifighter` | 72 | `attack_s3_s` | `0x0b7dd72b57` | `0x0d28325277` | `0x137f8a3d23` | `0x0e43cef37d` | `0x0fb1b90bcf` | `0x0084` | 0 | `c01attacks3s.nuanmb` | 28 | 28 |
| `miifighter` | 73 | `attack_s3_lw` | `0x0c244b16f0` | `0x0fa3eb2510` | `0x15a0319631` | `0x10f8d53518` | `0x119d40717b` | `0x0084` | 0 | `c01attacks3lw.nuanmb` | 28 | 28 |
| `miiswordsman` | 69 | `attack_s3_s` | `0x0b7dd72b57` | `0x0d28325277` | `0x137f8a3d23` | `0x0e43cef37d` | `0x0fb1b90bcf` | `0x0084` | 0 | `c01attacks3s.nuanmb` | 35 | 28 |

### Animation file measurements
Measured using `ssbh_data_py.anim_data.read_anim`:
- `fighter/miigunner/motion/body/c00/c01attacks3s.nuanmb`:
  - SHA-256: `cce167a2ea41cda96167808c9407f9243182b8d7b63751d91a90ca091acd36ef`
  - `final_frame_index`: **51.0** (total length: **52 frames**, indexed 0..51)
- `fighter/miifighter/motion/body/c00/c01attacks3s.nuanmb`:
  - SHA-256: `8321c7b73c7ea667342480cec5b05a7ed0e1135b88ecb6171d5eb1c7efc4ecbb`
  - `final_frame_index`: **55.0** (total length: **56 frames**, indexed 0..55)
- `fighter/miifighter/motion/body/c00/c01attacks3hi.nuanmb`:
  - SHA-256: `1771910ca79fbd0003224c35ee89062069b2a284c778fec7abbe2278c011e233`
  - `final_frame_index`: **55.0** (total length: **56 frames**, indexed 0..55)
- `fighter/miifighter/motion/body/c00/c01attacks3lw.nuanmb`:
  - SHA-256: `e835ac586a9924b80766cc0a6eeb31594663daeea5af007efae24671fe294d41`
  - `final_frame_index`: **55.0** (total length: **56 frames**, indexed 0..55)
- `fighter/miiswordsman/motion/body/c00/c01attacks3s.nuanmb`:
  - SHA-256: `39bf0dff673825b1dde3755c3f8fea2126075ceb556d9367d04e4c2b3d2abaee`
  - `final_frame_index`: **45.0** (total length: **46 frames**, indexed 0..45)

### Observations on Q1:
1. Angled forward-tilt variants exist **only** for Mii Brawler (`attack_s3_hi` and `attack_s3_lw`). Mii Gunner and Mii Swordfighter have only `attack_s3_s`.
2. Mii Gunner's tilt flags are `0x0080`, whereas Brawler's and Swordfighter's tilt flags are `0x0084` (bit 2 is set, `0x04`).
3. Mii Brawler's tilt cancel frame is **28** across all three variants (horizontal, hi, lw). Gunner's cancel frame is **37**. Swordfighter's cancel frame is **35**.
4. The 28-byte tail of each entry encodes:
   - bytes 0..7: Expression script hash (u64)
   - bytes 8..15: Sound script hash (u64)
   - bytes 16..23: Effect script hash (u64)
   - bytes 24..25: Unknown u16 (`0x0000`)
   - bytes 26..27: Cancel frame u16 (`28`, `37`, or `35`)

---

## Q5. Animation compatibility

Measured directly from the extracted model and animation files:

### Track and node comparison
- **Transform tracks**: Exactly **75 nodes** in all 5 forward-tilt clips.
  - The node set in `miifighter_s`, `miifighter_hi`, and `miifighter_lw` is **identical** to `miigunner_s` (symmetric difference is empty set `set()`).
  - Composition: 71 skeleton bones (all bones in `gunner_m` and `gunner_f` skeleton except the 6 helper constraint bones `H_Wrist*`, `H_Elbow*`, `H_Knee*`), plus 10 finger tip helper effect nodes (`FingerL14_eff`, `FingerL24_eff`, `FingerL34_eff`, `FingerL44_eff`, `FingerL54_eff` and the 5 on R).
- **Visibility tracks**: Exactly **12 nodes** in both Brawler and Gunner tilt clips (symmetric difference is empty set `set()`):
  - `MiiFighterM_eye_ANGER`, `MiiFighterM_eye_BLINK`, `MiiFighterM_eye_FRUSTRATED`, `MiiFighterM_eye_NORMAL`, `MiiFighterM_eye_SMILE`, `MiiFighterM_eye_SORROW`, `MiiFighterM_eye_SURPRISE`, `MiiFighterM_eye_WINK_LEFT`, `MiiFighterM_eye_WINK_RIGHT`, `MiiFighterM_mouth_CLOSE`, `MiiFighterM_mouth_LIKE`, `MiiFighterM_mouth_OPEN`.
- **Material tracks**: **0** material tracks exist in any forward-tilt clip.

### Skeleton comparison
- `gunner_m`, `gunner_f`, `fighter_m`, and `fighter_f` skeletons (`model.nusktb`) each have **71 bones** with identical names in the exact same hierarchy order.
- SHA-256 hashes:
  - `gunner_m`: `1d66b6d1cc4ce3b1c0883a21194cf998531c4a92ccb1c6561f69e68fd671429d`
  - `gunner_f`: `43f13756fb0fd5bed5dd37206e060818fc5bcd0ff7d99ae47b8419816ba4ed33`
  - `fighter_m`: `3f4a447406aca5e337591561719d025f04e474ea3b62a81d2a65c50edb13ec3d`
  - `fighter_f`: `3f4a447406aca5e337591561719d025f04e474ea3b62a81d2a65c50edb13ec3d`

### Mesh objects comparison
- `b_normalgunner_m` / `b_normalgunner_f` mesh objects (3):
  - `GamemodelShape` (unparented / root skin)
  - `buckleShape` (unparented / belt skin)
  - `gunShape` (parent bone: **`ArmR`**)
- `b_normalfighter_m` mesh objects (6):
  - `GamemodelShape` (x2)
  - `body_highShape` (x2)
  - `body_lowShape` (x2)
- `b_normalfighter_f` mesh objects (5):
  - `GamemodelShape`
  - `body_highShape` (x2)
  - `body_lowShape` (x2)

### Compatibility conclusion:
1. Mii Gunner has `gunShape` (attached to `ArmR`) and `buckleShape` which Brawler lacks.
2. Brawler has `body_highShape` and `body_lowShape` which Gunner lacks.
3. Neither animation drives mesh objects directly; animations drive only the 75 skeleton/helper transform nodes and 12 facial visibility nodes.
4. Because `gunShape` is rigged/parented to bone `ArmR`, when Gunner plays Brawler's tilt animation, `gunShape` automatically moves in sync with `ArmR` without any missing node errors or unbound tracks.

---

## Q2. Scripts

Located in `lua2cpp_miifighter.nro` and `lua2cpp_miigunner.nro`:

### Registration sites and function addresses
| Fighter | Script | Hash | Reg Site | Wrapper | Size (B) | Impl Start | Impl End | Instrs |
|---|---|---|---|---|---|---|---|---|
| `miifighter` | `game_attacks3hi` | `0x0f3d88dd77` | `0x43ca8` | `0xe4930` | 124 | `0x153cb0` | `0x1548c0` | 772 |
| `miifighter` | `game_attacks3` | `0x0d28325277` | `0x43cc4` | `0xe49c0` | 124 | `0x152c60` | `0x153870` | 772 |
| `miifighter` | `game_attacks3lw` | `0x0fa3eb2510` | `0x43ce0` | `0xe4a50` | 124 | `0x151ba0` | `0x152814` | 797 |
| `miifighter` | `sound_attacks3` | `0x0e43cef37d` | `0x45bac` | `0x15dde0` | 124 | `0x179c90` | `0x179dc8` | 78 |
| `miifighter` | `sound_attacks3hi` | `0x1066b6cd7f` | `0x45bc8` | `0x15de70` | 124 | `0x179c90` | `0x179dc8` | 78 |
| `miifighter` | `sound_attacks3lw` | `0x10f8d53518` | `0x45be4` | `0x15df00` | 124 | `0x179c90` | `0x179dc8` | 78 |
| `miifighter` | `effect_attacks3hi` | `0x110323891c` | `0x47750` | `0x499d0` | 124 | `0x9eae0` | `0x9eecc` | 251 |
| `miifighter` | `effect_attacks3` | `0x0fb1b90bcf` | `0x4776c` | `0x49a60` | 124 | `0x9e550` | `0x9e968` | 262 |
| `miifighter` | `effect_attacks3lw` | `0x119d40717b` | `0x47788` | `0x49af0` | 124 | `0x9dfc0` | `0x9e3dc` | 263 |
| `miifighter` | `expression_attacks3hi` | `0x153e526e56` | `0xa8744` | `0xac610` | 164 | `0xdcba0` | `0xdcf9c` | 255 |
| `miifighter` | `expression_attacks3` | `0x137f8a3d23` | `0xa8760` | `0xac6e0` | 124 | `0xdcba0` | `0xdcf9c` | 255 |
| `miifighter` | `expression_attacks3lw` | `0x15a0319631` | `0xa877c` | `0xac770` | 124 | `0xdcba0` | `0xdcf9c` | 255 |
| `miigunner` | `game_attacks3` | `0x0d28325277` | `0x47e4c` | `0xbc500` | 124 | `0xed530` | `0xee3e0` | 940 |
| `miigunner` | `sound_attacks3` | `0x0e43cef37d` | `0x49fe0` | `0xf6be0` | 124 | `0x10e620` | `0x10e758` | 78 |
| `miigunner` | `effect_attacks3` | `0x0fb1b90bcf` | `0x4bf94` | `0x4f8d0` | 124 | `0x7fd80` | `0x801e4` | 281 |
| `miigunner` | `expression_attacks3` | `0x137f8a3d23` | `0x88b84` | `0x8c790` | 124 | `0xb6c50` | `0xb6e68` | 134 |

### Brawler `game_attacks3` decoded ACMD call sequence
Implementation address: `0x152c60..0x153870` (772 instructions, SHA-256: `59706bc975b708bf0726c1956579b743c228a84de9df72a691e64a988c5e8ff3`)

1. **Frame 6** (`0x152cb0`): `app::sv_animcmd::frame(6)`
2. **Frame 6** (`0x152ce0`): `app::sv_animcmd::is_excute()`
3. **Frame 6** (`0x152f98`): `app::sv_animcmd::ATTACK` (Hitbox ID 0)
   - Part: 0
   - Bone: `legr` (`0x048a1f731c`)
   - Damage: **8.0%**
   - Angle: **361°** (Sakurai angle)
   - KBG: **86**
   - FKB: **0**
   - BKB: **34**
   - Size: **3.5**
   - Offset: X = 3.0, Y = 0.0, Z = 0.0
   - Setoff: `ATTACK_SETOFF_KIND_ON` (1)
   - LR Check: `ATTACK_LR_CHECK_F` (3)
   - Collision Attr: `collision_attr_normal` (`0x15a2c502b3`)
   - Sound Level: `ATTACK_SOUND_LEVEL_M` (1)
   - Sound Attr: `COLLISION_SOUND_ATTR_KICK` (2)
   - Region: `ATTACK_REGION_KICK` (6)
4. **Frame 6** (`0x153324`): `app::sv_animcmd::ATTACK` (Hitbox ID 1)
   - Part: 0
   - Bone: `kneer` (`0x051ba4b748`)
   - Damage: **8.0%**
   - Angle: **361°**
   - KBG: **86**, FKB: **0**, BKB: **34**
   - Size: **4.0**
   - Offset: X = 5.3, Y = 0.0, Z = 0.0
   - Same collision attributes and sound settings as Hitbox 0.
5. **Frame 6** (`0x1536ac`): `app::sv_animcmd::ATTACK` (Hitbox ID 2)
   - Part: 0
   - Bone: `legr` (`0x048a1f731c`)
   - Damage: **8.0%**
   - Angle: **361°**
   - KBG: **86**, FKB: **0**, BKB: **34**
   - Size: **2.5**
   - Offset: X = -0.5, Y = 0.0, Z = 0.0
   - Same collision attributes and sound settings as Hitbox 0.
6. **Frame 6** (`0x1537e8`): `app::sv_animcmd::wait(3)`
7. **Frame 9** (`0x153818`): `app::sv_animcmd::is_excute()`
8. **Frame 9** (`0x153848`): `app::lua_bind::AttackModule__clear_all_impl()` (hitboxes deactivated)

*Angled variants comparison*:
- `game_attacks3hi` (impl `0x153cb0`): Active on frame 6, damage is **8.5%** across all 3 hitboxes, and calls `AttackModule__set_attack_height_all_impl(AttackHeight_HIGH)`. Clears at frame 9.
- `game_attacks3lw` (impl `0x151ba0`): Active on frame 6, damage is **8.3%** across all 3 hitboxes, and calls `AttackModule__set_attack_height_all_impl(AttackHeight_LOW)`. Clears at frame 9.

### Gunner `game_attacks3` decoded ACMD call sequence (for comparison)
Implementation address: `0xed530..0xee3e0` (940 instructions, SHA-256: `ae5ea0a54f3bcab70682f22cf9607db02557a7e4d800af6ccb4134bf0c8c61d3`)

1. **Frame 2** (`0xed5c4`): `app::sv_animcmd::FT_MOTION_RATE(0.625)` (startup rate slowdown)
2. **Frame 10** (`0xed648`): `app::sv_animcmd::FT_MOTION_RATE(1.0)` (restored normal rate)
3. **Frame 10** (`0xed940`): `app::sv_animcmd::ATTACK` (Hitbox ID 0, initial stage)
   - Bone: `top` (`0x031ed91fca`)
   - Damage: **13.0%**
   - Angle: **361°**, KBG: **56**, BKB: **56**
   - Size: **2.0**, pos1: (0.0, 8.0, 8.0), pos2: (0.0, 8.0, 14.0)
   - Region: `ATTACK_REGION_ENERGY` (25)
4. **Frame 12** (`0xedda4`): `app::sv_animcmd::ATTACK` (Hitbox ID 0, decaying stage 2)
   - Damage: **10.5%**, Size: **1.5**, pos1: (0.0, 8.0, 6.0), pos2: (0.0, 8.0, 17.0)
5. **Frame 14** (`0xee208`): `app::sv_animcmd::ATTACK` (Hitbox ID 0, decaying stage 3)
   - Damage: **8.0%**, Size: **1.0**, pos1: (0.0, 8.0, 6.0), pos2: (0.0, 8.0, 21.0)
6. **Frame 16** (`0xee3bc`): `app::lua_bind::AttackModule__clear_all_impl()` (hitboxes deactivated)

### Decoder validation note:
- All 620 arguments across the 16 forward-tilt scripts were decoded without a single unresolved argument (`unresolved_count == 0`).
- Argument types decoded: `int`, `float`, `bool`, `hash` (`phx::Hash40`), `const` (via `const_value_table__E`), `global` (`L2CValue::NIL`).
- Dynamic runtime values assigned earlier (e.g. from `WorkModule::get_int`) are unsupported by static instruction decoding and flagged as `not decoded` / `runtime` (none occur within the forward-tilt ACMD scripts).

---

## Q3. Dependencies of the Brawler scripts

Every resource referenced by the four Brawler forward-tilt scripts was evaluated against Mii Gunner's vanilla files:

### Dependency table
| Category | Resource Name | Hash40 | Scope | Source File | Gunner Has Resource? | Available on Gunner without adding files? | Evidence |
|---|---|---|---|---|---|---|---|
| Bone | `legr` | `0x048a1f731c` | Skeleton (`LegR`) | `model.nusktb` | Yes | **Yes** | Bone `LegR` present in `gunner_m` and `gunner_f` `model.nusktb` |
| Bone | `kneer` | `0x051ba4b748` | Skeleton (`KneeR`) | `model.nusktb` | Yes | **Yes** | Bone `KneeR` present in `gunner_m` and `gunner_f` `model.nusktb` |
| Bone | `top` | `0x031ed91fca` | Engine battle object | Engine origin | Yes | **Yes** | Used as origin in vanilla Gunner `game_attacks3` and `effect_attacks3` |
| Effect | `sys_run_smoke` | `0x0d0da6e3c0` | Common system effect | `ef_common.eff` | Yes | **Yes** | Common effect in `ef_common.eff`; also called at frame 11 in Gunner's vanilla `effect_attacks3` |
| Effect | `sys_attack_arc` | `0x0e27bc68a2` | Common system effect | `ef_common.eff` | Yes | **Yes** | Common melee swipe arc in `ef_common.eff` |
| Sound | `se_miifighter_swing_m` | `0x151ab62b9e` | Fighter sound bank | `se_miifighter.nus3audio` | No | **No** | Tone index 25 in `se_miifighter.tonelabel`; absent from `se_miigunner.tonelabel` |
| Sound | `seq_miifighter_rnd_attack01` | `0x1b34be8874` | Fighter sound sequence | `miifighter.sqb` | No | **No** | Entry at offset 92 in `miifighter.sqb`; absent from `miigunner.sqb` (Gunner has `seq_miigunner_rnd_attack01`) |
| Article/Weapon | *(none)* | *(none)* | n/a | n/a | Yes | **Yes** | No articles or weapons generated or referenced by Brawler tilt scripts |

---

## Q4. Status

### Status kind
- Forward tilt runs under standard common fighter status: **`FIGHTER_STATUS_KIND_ATTACK_S3`** (numeric value **`42`** / **`0x2a`**).

### Overrides in character NROs
- Scanning `lua2cpp_miifighter.nro` and `lua2cpp_miigunner.nro` for all calls to:
  - `_ZN7lua2cpp12L2CAgentBase18sv_set_status_funcERKN3lib8L2CValueES4_Pv`
  - `_ZN7lua2cpp12L2CAgentBase21sv_delete_status_funcERKN3lib8L2CValueES4_`
  across all 731 status function registrations in both NROs revealed:
  - **Zero registrations** for status kind 42 (`FIGHTER_STATUS_KIND_ATTACK_S3`) in `miifighter`.
  - **Zero registrations** for status kind 42 (`FIGHTER_STATUS_KIND_ATTACK_S3`) in `miigunner`.
  - Forward tilt is handled entirely by the common status code in the main executable / `lua2cpp_common.nro`.

### Scanner validation on overridden statuses
- Validated via positive controls on special moves:
  - `FIGHTER_STATUS_KIND_SPECIAL_N` (value `0xe4`):
    - `miifighter`: registered at `0x7b8` (`STATUS_PRE`), `0x7f8` (`STATUS_MAIN`), `0x838` (`STATUS_END`), `0xa5b4` (`INIT_STATUS`), `0xa5f4` (`EXEC_STATUS`).
    - `miigunner`: registered at `0x1aa8` (`STATUS_PRE`), `0x1ae8` (`STATUS_MAIN`), `0x1b28` (`STATUS_END`).
  - `FIGHTER_STATUS_KIND_SPECIAL_S` (value `0xc4`), `SPECIAL_HI` (value `0xb8`), `SPECIAL_LW` (value `0xd0`), and `FINAL` (value `0xdc`) are also correctly located and reported in `status_regs.tsv`.

---

## Q6. The closure list

Everything required for a Mii Gunner to execute Mii Brawler's forward tilt with Brawler's hitboxes, animations, effects, and sounds:

1. **Motion List Entry** [Tier B]:
   - Gunner's `motion_list.bin` must have an entry matching Brawler's tilt: cancel frame 28, flags `0x0084`, size 28, linking to `c01attacks3s.nuanmb`.
   - Angled variants (`attack_s3_hi`, `attack_s3_lw`) require adding their respective motion entries to `motion_list.bin`.
2. **Animation Asset** [Tier B]:
   - File `fighter/miigunner/motion/body/c00/c01attacks3s.nuanmb` (or donor file copied from Brawler).
   - Animation length: 56 frames (final frame 55.0).
   - Node set: 75 transform nodes and 12 visibility nodes. Zero node mismatch with Gunner's skeleton.
   - Mesh tracking: `gunShape` tracks parent bone `ArmR` in Gunner's skeleton without modifications.
3. **Game Script (Hitboxes & Timing)** [Tier B]:
   - Hitbox registration for `game_attacks3` (and angled variants if used).
   - Active frames: 6..8 (startup 6, wait 3, clear at 9).
   - Bones: `legr` and `kneer` (present in Gunner's skeleton) and `top` (present in engine).
   - No weapon or article spawning.
4. **Effect Script** [Tier B]:
   - `effect_attacks3` calls `sys_run_smoke` and `sys_attack_arc` from `ef_common.eff`. Available on Gunner with zero added files.
5. **Sound Script & Sound Bank** [Tier B / Tier D]:
   - `sound_attacks3` calls `se_miifighter_swing_m` and `seq_miifighter_rnd_attack01`.
   - Neither exists in Gunner's vanilla sound bank (`se_miigunner.nus3audio`) or sequence (`miigunner.sqb`). [Tier B]
   - Without sound bank redirection or remapping, Gunner calling Brawler's vanilla sound script will be silent or missing the swing SE. [Tier D]
   - Runtime redirection of sound labels to Gunner's equivalent (`se_miigunner_attackhard_s01` / `seq_miigunner_rnd_attack01`) or injection of Brawler's sound bank. [Tier D]
6. **Status Handler** [Tier B]:
   - Common engine status `FIGHTER_STATUS_KIND_ATTACK_S3` (42). Neither fighter overrides this status; no custom status handler replication is needed.
7. **Per-Mii Runtime Dispatch** [Tier D]:
   - Runtime hook intercepting motion selection or ACMD script execution per saved-Mii loadout (Smashline / plugin hook).

---

## Verification output

Output of `evidence/P12-FTILT-FACTS/check_p12_ftilt_facts.py`:

```
=== Checking input file hashes (28 files) ===
OK: All 28 input files matched expected SHA-256 and size.

=== Checking cited instruction words in NROs ===
OK: All 15 miifighter words and 9 miigunner words verified.

=== Checking Q1 motion entries & animation lengths ===
OK: Motion entries and animation frame counts verified.

=== Checking Q2 decoded ACMD calls ===
OK: Decoded ACMD calls, timing, and hitboxes verified.

=== Checking Q3 dependencies table ===
OK: Dependency table and sound bank absences verified.

=== Checking Q4 status registration scan ===
OK: Status registration scan verified (no ATTACK_S3 override, positive controls passed).

=== Checking Q5 animation & mesh compatibility ===
OK: Animation node sets and mesh object sets verified.

=======================================================
ALL P12-FTILT-FACTS CHECKS PASSED (exit 0)
=======================================================
```

Output of negative control run (`check_p12_ftilt_facts.py --neg`):

```
=== Running Negative Controls (--neg) ===
  Control 1 PASSED: Corrupted input hash correctly rejected.
  Control 2 PASSED: Corrupted instruction word correctly rejected.
  Control 3 PASSED: Wrong cancel frame claim (37 instead of 28) correctly rejected.
  Control 4 PASSED: False sound bank claim (claiming Gunner has swing_m) correctly rejected.
  Control 5 PASSED: False status override claim correctly rejected.

All 5 negative controls caught their discrepancies as expected.
Exiting with code 1 as specified for --neg run.
```

---

## Task summary

- **Task ID**: `P15-FTILT-TAKEOVER` (finishing `P12-FTILT-FACTS`)
- **Status**: DONE
- **Changed files**:
  - `mods/mii_customizer/research/P12-FTILT-FACTS.md`
  - `mods/mii_customizer/evidence/P12-FTILT-FACTS/check_p12_ftilt_facts.py`
  - `mods/mii_customizer/scratch/2026-10-07_P15-FTILT-TAKEOVER/` (scratch scripts, hashes, and dumps)
  - `gamedata/mii_customizer/P12-FTILT-FACTS/tables/leftover/` (preserves all 7 original unreviewed tables)
  - `gamedata/mii_customizer/P12-FTILT-FACTS/tables/motion_ftilt_entries.tsv` (updated with cancel frames & script hashes)
  - `gamedata/mii_customizer/P12-FTILT-FACTS/tables/anim_ftilt_clips.json` (updated with exact frame counts)
  - `gamedata/mii_customizer/P12-FTILT-FACTS/tables/ftilt_dependencies.tsv` (new verified dependency table)
- **Checks run**:
  - `python mods/mii_customizer/evidence/P12-FTILT-FACTS/check_p12_ftilt_facts.py` (Exit code: 0)
  - `python mods/mii_customizer/evidence/P12-FTILT-FACTS/check_p12_ftilt_facts.py --neg` (Exit code: 1)
- **Open questions**:
  - Sound strategy for borrowed moves: whether to remap Brawler's `se_miifighter_swing_m` to Gunner's `se_miigunner_attackhard_s01` via a script patch, or load Brawler's `se_miifighter.nus3audio` bank as an auxiliary bank on Gunner.
  - Runtime per-Mii move dispatch mechanism (Smashline script hooks per battle object entry ID).

### What the previous worker's tables got wrong:
1. **Animation frame counts left unpopulated**: In `tables/anim_ftilt_clips.json`, the previous worker recorded `frame_count: null` and `max_node_frame_count: null` for all clips because it queried non-existent attributes instead of `final_frame_index` on `AnimData`. We corrected this by reading `final_frame_index` directly (Gunner: 52 frames; Brawler: 56 frames; Swordfighter: 46 frames).
2. **Undecoded script hashes in motion entry tails**: In `tables/motion_ftilt_entries.tsv`, the previous worker dumped the 28-byte entry tail as raw hex (`tail_hex`) rather than decoding the three 64-bit script hashes (`expression`, `sound`, `effect`) and the cancel frame stored within it.
3. **Runaway status probing (Q4 rabbit hole)**: The previous worker got confused by multi-level function wrappers and runtime argument loads in the status registration scanner, writing 6 separate probe scripts without answering whether `FIGHTER_STATUS_KIND_ATTACK_S3` was overridden. Our analysis established that neither fighter registers status functions for `ATTACK_S3` (value 42 / 0x2a), both relying on the engine's common status functions.
4. **Missing check script and empty report**: The previous worker did not create `evidence/P12-FTILT-FACTS/check_p12_ftilt_facts.py` and left `research/P12-FTILT-FACTS.md` as an empty skeleton.
