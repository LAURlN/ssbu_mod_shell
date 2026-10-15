# P1-CATALOG - Gunner move slots and stat inputs

Task: P1-CATALOG. Worker: Space Bunny Alpha. Date: 2026-10-04.
Prompt: `prompts/P1-CATALOG.md`. Phase: `phases/01_discovery.md`.

Goal of this document: a bounded, checkable inventory of what a Gunner-only editor
could offer as move slots and as editable numbers. It is **not** a move port, not a
schema, and not a claim that any of it works in a match.

All paths are relative to the workspace root. Inputs were extracted from
`gamedata/ssbu-13.0.4/data.arc` (sha256 `ef615e671e1d...`, 13.0.4 patched) with the
existing `tools/arc-extract`; exact commands and printed hashes are in
`evidence/P1-CATALOG/EXTRACTION.md`.

Evidence tiers used here: **B** = measured offline from the local archive by a script
that still exists; **D** = hypothesis. There is **no A** in this report - nothing was
run on hardware or in an emulator.

---

## 0. How the internal names in this report were obtained

Nothing below is a recollection of the game's on-screen move names. Three hash joins
were used, all against `hash40 = (len << 32) | crc32(name)`:

1. **Animation hashes -> file paths.** Every animation hash in the Gunner body motion
   list was matched against `hash40(basename)` of every `fighter/miigunner/**/*.nuanmb`
   path in `mods/ssbu_mod_new/dumps/decoded/arc_files.tsv`. **774/774 entries resolved**,
   0 left over. This is the strongest join here: it is a closed set over the archive
   index, not a guess.
2. **Motion kind hashes -> names.** Against `ParamLabels.csv`
   (`mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv`, 93,034 labels), then a fixed
   candidate list, then - for what remained - the entry's own clip name with its
   letter/digit prefix stripped and up to four underscores inserted, each placement
   hash-checked. **572 of 774 kinds resolved** (471 from the label table, 22 from the
   fixed list, 79 from the clip-stem pass, 0 collisions).
3. **Game script hashes -> names.** `hash40("game_" + kind_name_without_underscores)`,
   checked per entry. **379 of 774 resolved.**

Reader: `mods/ssbu_mod_new/src/pgwr/tools/mlist.py` (read-only import); round trip
`encode(parse(x)) == x` asserted on every motion list read.

**What the join does not prove.** A kind hash match proves the file names that motion
kind. It says nothing about which button the player presses, what the move is called in
the game's own strings, or how the game chooses between the alternatives of one special
category. Those stay unmeasured and are listed in section 6.

---

## 1. Where the Gunner's data lives

| what | ARC path (verified present in the index) |
|---|---|
| body motion list (c00) | `fighter/miigunner/motion/body/c00/motion_list.bin` |
| body motion list (c06/c07) | `fighter/miigunner/motion/body/c06/...`, `c07/...` (present) |
| per-fighter move params | `fighter/miigunner/param/vl.prc` |
| per-fighter mesh params | `fighter/miigunner/param/expression_vl.prc` (not read in this task) |
| base stat row | `fighter/common/param/fighter_param.prc`, row 82 = `miigunner` |
| shared fight params | `fighter/common/param/common.prc`, `fighter/common/param/battle_object.prc` |
| AI move lists | `fighter/miigunner/ai/param/attack_list_param.prc`, `attack_data_param.prc` |
| Mii hat / cosmetic data | `fighter/miigunner/param/vl.prc` -> `mii_hat_node_data`, `mii_customizer` |
| spirit data | `spirits/mii/mii_gunner.bin` (listed in the index; not read) |

Gunner's internal fighter directory is **`miigunner`**; `fighter_param_table` row 82
carries `fighter_kind == fighter_kind_miigunner` (`0x166e9fae70`). Note there are also
`miifighter` (row 80), `miiswordsman` (81) and `miienemyf/s/g` (91/92/93) rows - the
"enemy" Miis are a **separate fighter kind**, which matters for any later identity work.

---

## 2. Normal attack slots

All from `fighter/miigunner/motion/body/c00/motion_list.bin`. `flags` is the raw
`u16` from the entry, `blend` the raw `u8`. `B`.

**Correction 2026-10-04 (P1-CATALOG-AUDIT).** The `cancel` column below is the raw
`u16` this table originally reported, and it is **not** the cancel frame. The field
holds `cancel_frame` in its low byte and a separate boolean (`no_stop_intp`) in bit
`0x100`; masking that bit changes the two "anomalous" values and leaves every other
value unchanged. The frame column is now named `cancel(raw u16)` for the bytes and
the resolved frame is given as `cancel_frame` with its `no_stop_intp` flag. Proof is
in `research/P1-CATALOG-AUDIT.md` §3 and `evidence/P1-CATALOG-AUDIT/`.

| slot | motion kind | game script | clip | flags | blend | cancel(raw u16) | cancel_frame | no_stop_intp |
|---|---|---|---|---|---|---|---|---|
| jab 1 | `attack_11` | `game_attack11` | `c00attack11.nuanmb` | 0x0084 | 0 | 26 | 26 | 0 |
| jab 2 | `attack_12` | `game_attack12` | `c00attack12.nuanmb` | 0x0084 | 0 | 26 | 26 | 0 |
| jab 3 | `attack_13` | `game_attack13` | `c00attack13.nuanmb` | 0x0084 | 0 | 38 | 38 | 0 |
| dash attack | `attack_dash` | `game_attackdash` | `c00attackdash.nuanmb` | 0x0084 | 0 | 46 | 46 | 0 |
| up tilt | `attack_hi3` | `game_attackhi3` | `c02attackhi3.nuanmb` | 0x0080 | 0 | 38 | 38 | 0 |
| down tilt | `attack_lw3` | `game_attacklw3` | `c02attacklw3.nuanmb` | 0x0080 | 0 | 41 | 41 | 0 |
| **side/forward tilt** | `attack_s3_s` | **`game_attacks3`** | `c01attacks3s.nuanmb` | 0x0080 | 0 | 37 | 37 | 0 |
| down smash | `attack_lw4` | `game_attacklw4` | `c04attacklw4.nuanmb` | 0x0084 | 0 | 53 | 53 | 0 |
| down smash (hold) | `attack_lw4_hold` | `game_attacklw4charge` | `c04attacklw4charge.nuanmb` | 0x0080 | 0 | 0 | 0 | 0 |
| up smash | `attack_hi4` | `game_attackhi4` | `c04attackhi4.nuanmb` | 0x0080 | 0 | 56 | 56 | 0 |
| up smash (hold) | `attack_hi4_hold` | `game_attackhi4charge` | `c04attackhi4charge.nuanmb` | 0x0080 | 0 | 0 | 0 | 0 |
| **forward smash** | `attack_s4_s` | **`game_attacks4`** | `c03attacks4s.nuanmb` | 0x0084 | 0 | 334 | **78** | **1** |
| forward smash (hold) | `attack_s4_hold` | `game_attacks4charge` | `c03attacks4charge.nuanmb` | 0x0084 | 0 | 0 | 0 | 0 |
| neutral air | `attack_air_n` | `game_attackairn` | `c05attackairn.nuanmb` | 0x0080 | 0 | 42 | 42 | 0 |
| forward air | `attack_air_f` | `game_attackairf` | `c05attackairf.nuanmb` | 0x0080 | 0 | 42 | 42 | 0 |
| back air | `attack_air_b` | `game_attackairb` | `c05attackairb.nuanmb` | 0x0080 | 0 | 48 | 48 | 0 |
| up air | `attack_air_hi` | `game_attackairhi` | `c05attackairhi.nuanmb` | 0x0080 | 0 | 318 | **62** | **1** |
| down air | `attack_air_lw` | `game_attackairlw` | `c05attackairlw.nuanmb` | 0x0080 | 0 | 55 | 55 | 0 |

Notes that the file itself forces, `B`:

- **Resolved 2026-10-04 (P1-CATALOG-AUDIT): `attack_s3_s` IS the forward/side tilt and
  `attack_s4_s` IS the forward smash.** The coordinator's objection to this section is
  answered. Provenance is a hash match against a fighter whose decoded field names are
  known: `attack_s3_s` -> `game_attacks3` (`0xd28325277`), clip `c01attacks3s.nuanmb`,
  flags `0x0080` with `move = false`; `attack_s4_s` -> `game_attacks4`
  (`0xdb656c7d4`), clip `c03attacks4s.nuanmb`, flags `0x0084` with `move = true`. The
  `_s` suffix is a kind-name form, not a "smash" marker; the smash role is carried by
  the `move` flag and by the `*_hold` partner entry. Both game scripts are now named -
  the `-` in the original table was a label-join miss, not an absent script.
- **All five aerials exist and each has its own kind**, so the aerial group is one
  selector with five concrete values, not a range.
- **Every `attack_*` and `catch*`/`throw_*` game script in this table is now named.**
  Where this table previously showed `-`, the name is `game_` + the kind with the `_s`
  removed from an `s3_s`/`s4_s` kind (`game_attacks3`), matching the decoded reference.
- **`cancel_frame` is a per-fighter authored value, not a shared constant.** Both
  `attack_s3_s` (37) and `attack_s4_s` (78) are the *same kinds and clips* as
  GameWatch's, whose decoded values are 38 and 43. So the raw bytes here are per-fighter
  tuning, not a parsing artefact.
- Both smashes are two-entry slots (release + charge hold), so a smash is not one slot
  but a small state pair. The holds carry `cancel_frame = 0`.

## 3. The four special categories and their alternatives

The body list carries four families, each with numbered alternatives and each with a
separate air set. `B`. Alternatives are named `special_n1/2/3`, `special_s1/2/3`,
`special_hi1/2/3`, `special_lw1/2/3` by the game's own kind hashes.

### Neutral (`special_n*`) - indices 89-109

| kind | game script | clip | cancel |
|---|---|---|---|
| `special_n1_start` | `game_specialn1start` | `d00specialn1start` | 0 |
| `special_n1_hold` | - | `d00specialn1hold` | 0 |
| `special_n1_cancel` | - | `d00specialn1cancel` | 5 |
| `special_n1_fire` | - | `d00specialn1` | 40 |
| `special_n1_fire_max` | - | `d00specialn1` (same clip) | 40 |
| `special_n2_start` | - | `d00specialn2start` | 256 |
| `special_n2_loop` | - | `d00specialn2loop` | 256 |
| `special_n2_end` | - | `d00specialn2end` | 271 |
| `special_n3_start` | - | `d00specialn3start` | 0 |
| `special_n3_end` | - | `d00specialn3end` | 23 |
| `special_air_n1_*` (start/hold/cancel/jump_cancel/fire/fire_max) | - | `d00specialairn1*` | - |
| `special_air_n2_*` (start/loop/end) | - | `d00specialairn2*` | - |
| `special_air_n3_*` (start/end) | - | `d00specialairn3*` | - |

`special_n1_fire` and `special_n1_fire_max` name the **same clip** and differ only in
kind - a charge level expressed as two kinds, not two moves.

### Side (`special_s*`) - indices 110-121

`special_s1` (`d01specials1`, cancel 64), `special_s2_start/loop/end`
(`d01specials2start/loop/end`), `special_s3_1` (`d01specials31`, cancel 297),
`special_s3_2` (`d01specials32`, cancel 306), plus `special_air_s1`,
`special_air_s2_start/loop/end`, `special_air_s3_1`, `special_air_s3_2`.

Correction 2026-10-04 (P1-CATALOG-AUDIT): these `cancel` values are raw `u16` reads.
`special_s3_1` is 297 raw / **41 frames**, `special_s3_2` is 306 raw / **50 frames**, and
both carry `no_stop_intp = 1`. Same field interpretation as §2.

### Up (`special_hi*`) - indices 122-132 - **has directional variants**

| kind | clip | note |
|---|---|---|
| `special_hi1` | `d02specialhi1` | |
| `special_hi2` / `special_hi2_squat` | `d02specialhi2`, `d02specialhi2squat` | |
| `special_hi3` | `d02specialhi3` | |
| `special_hi3_start` | `d02specialhi3start` | |
| `special_air_hi1` | `d02specialairhi1` | |
| `special_air_hi2_squat` | `d02specialairhi2squat` | |
| `special_air_hi3_start` | `d02specialairhi3start` | kind hash unresolved |
| `special_air_hi3_end` | `d02specialairhi3end` | |
| **kind unresolved** `0x0d3aaf0366` | `d02specialhi3f` | forward variant |
| **kind unresolved** `0x0d3dc2c77f` | `d02specialhi3b` | back variant |

This is the "observed directional variant" the prompt asked about: the up special has
**three** directional clips (`d02specialhi3`, `...3f`, `...3b`) behind three distinct
kinds, two of which this task could not name. Recorded by clip and kind hash, not
dropped.

### Down (`special_lw*`) - indices 133-158 - **three alternatives with sub-states**

| alternative | kinds | clips |
|---|---|---|
| 1 | `special_lw1_start`, `_loop`, `_hit`, `_end` (+ `_start_l`, `_loop_l`, `_hit_l`, `_end_l`) and the whole `special_air_lw1_*` mirror | `d03speciallw1*` |
| 2 | `special_lw2` | `d03speciallw2` (cancel 47) |
| 3 | `special_lw3_start`, `_hold`, `_hit`, `_end` (+ air mirror) | `d03speciallw3*` |

Correction 2026-10-04 (P1-CATALOG-AUDIT): each `special_lw1_*` `_l` kind shares its
base kind's `game_script` hash exactly (measured: `start`/`start_l` both
`0x148e2088ad`, `loop`/`loop_l` both `0x13f9896335`, `hit`/`hit_l` both
`0x12e4e0ec7c`, `end`/`end_l` both `0x12becef98c`) and differs only in clip. The `_l`
sub-variant is therefore a real per-direction state pair, not an alias.

Alternative 1 has a left-side sub-variant (`*_l`) both on the ground and in the air -
seven extra kinds. Alternatives 2 and 3 are single clips.

### Helper / weapon motions (not user-facing slots)

Fourteen helper motion lists exist under `fighter/miigunner/motion/<name>/c00/`, all
extracted and hashed (see `EXTRACTION.md`): `gunnercharge`, `laser`, `fullthrottle`,
`miimissile`, `supermissile`, `groundbomb`, `stealthbomb`, `stealthbomb_s`,
`bottomshoot`, `grenadelauncher`, `flamepillar`, `rapidshot_bullet`,
`attackairf_bullet`, `hat`. `B`.

Two measured facts worth carrying:

- **`motion/fullthrottle/c00/` ships five clips named `d04final.nuanmb`,
  `d04finalstart`, `d04finalu`, `d04finald`, `d04finalend`** and its motion list names
  them. Those are the Full Throttle helper's own clips, **not** a Final Smash
  dependency. Reading a clip name alone would get this exactly backwards.
- `gunnercharge/c00/motion_list.bin` and `laser/c00/motion_list.bin` are
  byte-identical (`91f314cb5d49...`).

**Not established:** which helper belongs to which special alternative. The body
motion list does not name the helpers; that link lives in the game script / article
code, which is not in the local inputs for this task. So "down special 1 = the bomb
whose helper is `stealthbomb`" is **D**, not a catalogue entry.

---

## 4. Landing / ground-air / helper motions, listed separately

These are motion kinds the game plays; they are not move slots a player picks. `B`.

| group | kinds (indices) |
|---|---|
| landing, ground | `landing_light` (48), `landing_heavy` (49) |
| landing, air, one per aerial | `landing_air_n` (84), `landing_air_f` (85), `landing_air_b` (86), `landing_air_hi` (87), `landing_air_lw` (88) - all cancel 20 |
| squat | `squat` (43), `squat_wait` (44), `squat_wait2` (45), `squat_wait_item` (46), `squat_rv` (47) |
| step / ledge-ish | `step_jump` (50), `step_pose` (51), `step_fall` (54), two unresolved kinds on `a06stepback` / `a06stepairpose` (52, 53) |
| guard | `guard_on` (55), `guard` (56), `guard_off` (57), `just_shield_off` (58), `guard_damage` (59) |
| escape | `escape` (60, script unresolved), `escape_f` (61), `escape_b` (62), `escape_air` (63), `escape_air_slide` (64), `rebound` (65) |
| locomotion | `wait`, `wait_2`, `walk_slow/middle/fast`, `run`, `dash`, `turn`, `turn_dash`, `turn_run`, `jump_*`, `fall_*` (indices 0-42) |
| damage reaction | `down_*_u` / `down_*_d` (296-313), `f01damage*`, `wall_damage`, `ceil_damage`, `furafura*` (314-325), `swallowed`, `camera_hit` |

Grab / throw / capture kinds are in section 2's sibling group below, because they *are*
player-facing.

## 5. Grab, pummel, throws

| slot | kind | script | clip | cancel |
|---|---|---|---|---|
| grab | `catch` | `game_catch` | `e00catch` | 35 |
| grab (dash) | `catch_dash` | `game_catchdash` | `e00catchdash` | 43 |
| grab (turn) | `catch_turn` | `game_catchturn` | `e00catchturn` | 38 |
| grab pull | `catch_pull` | `game_catchpull` | `e00catchpull` | 2 |
| grab wait | `catch_wait` | `game_catchwait` | `e00catchwait` | 0 |
| **pummel** | `catch_attack` | `game_catchattack` | `e00catchattack` | 7 |
| grab cut / release | `catch_cut` | `game_catchcut` | `e00catchcut` | 30 |
| forward throw | `throw_f` | `game_throwf` | `e01throwf` | 34 |
| back throw | `throw_b` | `game_throwb` | `e01throwb` | 50 |
| up throw | `throw_hi` | `game_throwhi` | `e01throwhi` | 52 |
| down throw | `throw_lw` | `game_throwlw` | `e01throwlw` | 41 |

The victim side is also in this file and is **not** a slot: `thrown_f/b/hi/lw` plus
`_dx`, `_big`, `_girl` variants (12 kinds, flags `0x00a8`) and
`capture_pulled_hi`, `capture_wait_hi`, `capture_damage_hi` and their `_lw` mirrors.
Recorded so that a later "which clip do I replace" question has the answer: the
attacker throw and the victim reaction are separate entries.

---

## 6. Explicitly unresolved scope (kept, not dropped)

None of these is settled by this task. Listed with what is known.

| item | state | what is known |
|---|---|---|
| **Final Smash** | unresolved | Ten kinds, indices 159-168: `final_start`, `final`, `final_end`, `final_air_start`, `final_air`, `final_air_end`, `final_u`, `final_d`, `final_air_u`, `final_air_d`. Clips `d04final*` in `body/c00`. **Naming trap:** `motion/fullthrottle/c00/` owns clips with the *same names* (section 3). Whether Final Smash is editor scope at all is a coordinator decision, not a discovery result. |
| **Get-up attacks** | unresolved | `down_attack_u` (301) / `down_attack_d` (310), plus `down_forward_u/d`, `down_back_u/d`, `down_bounce_u/d`, `down_wait_u/d`, `down_stand_u/d`. All present, all named; **whether the player-facing get-up option is one slot or several is not established**. |
| **Ledge / cliff** | partially unresolved | Named: `cliff_catch` (339), `cliff_wait` (340), `cliff_attack_quick` (342), `slip_attack` (350), `slip_escape_f/b` (351/352). **Unresolved kinds** on `g02cliffclimb` (341), `g02cliffescape` (343), `g02cliffjump1` (344), `g02cliffjump2` (345). |
| **Taunts** | named, scope unresolved | Six kinds, indices 260-265: `appeal_hi_r`, `appeal_hi_l`, `appeal_s_r`, `appeal_s_l`, `appeal_lw_r`, `appeal_lw_l`, clips `j01appeal*`, cancel 50. Also `win_1/2/3`, `lose`, `menu_pose`, `menu_pose_2`, `entry_l/r`, and the `share_*` / `l02share_*` set (2 unresolved kinds). |
| **Costume / colour variants** | not investigated | `b_normalgunner_*`, `b_specialforces_*`, `b_bandit_*`, ... model and motion folders exist per Mii body part. Out of this task's scope. |
| **Item motions** | out of scope | 100+ `h*` item kinds including 7 unresolved ones. Not user-facing move slots. |

---

## 7. Numerical stat candidates

### Where the Gunner's numbers live

`fighter/common/param/fighter_param.prc` -> `fighter_param_table[82]`, identified by
`fighter_kind == fighter_kind_miigunner`. 369 scalars in that row. This is the **only**
place in the local inputs where Gunner-specific weight / run speed / jump height live:
`fighter/miigunner/param/vl.prc` (854 scalars) is move/projectile data
(`param_special_*`, `param_gunnercharge`, `map_collision_*`, `hit_data`) and contains
no `weight`.

Every key below was cross-checked: the Hash40 stored in the file equals
`hash40(name)` recomputed from the label, 23/23. See
`evidence/P1-CATALOG/gunner_stat_candidates.tsv`.

### The twelve candidates

| # | parameter name | Hash40 | type | value in row 82 | what it is |
|---|---|---|---|---|---|
| 1 | `weight` | `0x0607cd5541` | float | 104.0 | mass |
| 2 | `scale` | `0x05ec462584` | float | 1.15 | model scale |
| 3 | `walk_speed_max` | `0x0ee2ec2860` | float | 1.0 | walk top speed |
| 4 | `run_speed_max` | `0x0d5aaabf9b` | float | 1.37 | run top speed |
| 5 | `dash_speed` | `0x0adec47ea3` | float | 1.63 | dash top speed |
| 6 | `air_speed_x_stable` | `0x1220fc2660` | float | 0.93 | horizontal air control cap |
| 7 | `air_speed_y_stable` | `0x12ec5626fe` | float | 1.45 | terminal fall speed |
| 8 | `air_accel_y` | `0x0ba18057d9` | float | 0.098 | gravity accel |
| 9 | `air_accel_x_mul` | `0x0f71f4d4f8` | float | 0.043 | air accel multiplier |
| 10 | `jump_y` | `0x06a0d82dad` | float | 30.9 | jump height |
| 11 | `jump_speed_x` | `0x0cc9d2f2da` | float | 0.95 | horizontal jump speed |
| 12 | `jump_count_max` | `0x0e35ca3d82` | i32 | 2 | number of jumps |

Useful spares in the same row, measured, not guessed: `jump_squat_frame` (i32 3),
`jump_initial_y` (float 16.995), `ground_brake` (0.076), `run_accel_mul` (0.10978),
`walk_accel_mul` (0.105), `air_brake_x` (0.012), `air_brake_y` (0.015),
`air_accel_x_add` (0.01), `shield_radius` (9.1).

### What these numbers are and are not

- `B`: each value above is what row 82 of that file holds, decoded with a typed reader
  and cross-checked against `hash40(name)`.
- **Not established: that these are the values a Gunner actually runs with.** The file
  is the base table. Nothing here shows that a battle object reads row 82 unchanged, or
  that a reader which is not `WorkModule` sees the same number.
- **Not established: any safe range.** No range is proposed here. A range needs a
  measurement (what breaks, at what value) that this task did not run.
- **Correction 2026-10-04 (P1-CATALOG-AUDIT), coordinator's point adopted:** weight is
  **not** gravity or fall speed. The gravity/fall-speed numbers in this table are the
  separate keys `air_accel_y`, `air_accel_x_mul` and `air_speed_y_stable`, and
  `air_speed_y_stable` is a *terminal* velocity cap, not floatiness. Weight must be
  assessed by a controlled knockback comparison, not by how a fighter feels in the air.
- **Not established: that one edit reaches one fighter.** Row 82 is a single shared
  row for the `miigunner` kind. Whether a per-saved-Mii change can be scoped to one
  battle object is an open question that section 8 does not answer.

### Other tables, for completeness (named, not mined)

`fighter/common/param/common.prc` (794 scalars) holds engine-wide behaviour:
`shield_max`, `jump_stick_y`, `capture_cut_frame`, `run_speed_ratio_min`,
`hit_stop_*`, and so on. `fighter/common/param/battle_object.prc` (1,023 scalars) holds
damage/reaction/jostle numbers (`damage_max`, `reaction_max`, `jostle_weight_min`, ...).
Both are shared by every fighter, so changing one is not a Gunner-scoped edit.

---

## 8. Recommended first vertical slice

### One stat: `weight`

`weight`, float, Hash40 `0x0607cd5541`, value 104.0 in row 82.

Why: one scalar, one hash, no derived table, no costume interaction, and it is the
stat whose value is least likely to be recomputed from another table. It is also the
one possible first scalar. Coordinator correction 2026-10-04: weight is not gravity or fall
speed; evaluate it with a controlled knockback comparison, not floatiness. Whether the relevant
engine reader can be overridden per object remains unverified.

**Do not** start with `scale` (it feeds camera, portrait and item code), with anything
in `common.prc` / `battle_object.prc` (not Gunner-scoped), or with a jump value
(`jump_y` and `jump_initial_y` are not independent - the pair sets the jump arc, and
nothing in this task measured how).

### One normal slot: `attack_hi3` (up tilt)

Kind `attack_hi3`, script `game_attackhi3`, clip `c02attackhi3.nuanmb`, flags `0x0080`,
blend 0, cancel 38.

Why: exactly one clip, one kind, one script, no charge state, no directional variants,
no helper motion list. Its three identity fields (kind / script / clip) are all resolved
and all cross-checked, so a first menu entry can name it without inventing anything.
A single-choice Gunner up tilt is a legitimate initial menu entry - it is a **selector
over existing Gunner slots**, not a move port.

Runner-up if a jab reads better in the UI: `attack_11` (`game_attack11`,
`c00attack11.nuanmb`, cancel 26), same properties.

### Existing per-battle-object parameter override example - source reference only

The reference mod already contains one, and it is worth reading before designing ours:

`mods/ssbu_mod_new/src/pgwr/plugin/src/params.rs` hooks
`WorkModule::get_param_int` / `WorkModule::get_param_float`, receives
`boma: *mut BattleObjectModuleAccessor`, gates on
`get_category(boma) == FIGHTER` + `get_kind(boma)` + the instance colour work id, and
returns a substituted value before falling through to `original!()`.

What that establishes, and what it does not:

- It establishes (tier **B** by source inspection of a shipped, console-tested mod -
  the *runtime* behaviour is tier A and is not re-verified here) that **reads** of
  fighter parameters pass through a per-battle-object entry point that already receives
  the battle object.
- Its query shape for `fighter_param_table` attributes is
  `parent == 0 || parent == hash40("common")` with the child hash (see
  `get_fighter_param_float`, params.rs:293-311), which is the shape a `weight` lookup
  would take.
- It does **not** establish that writing the shared `fighter_param.prc` row is
  per-object. It is a **read-side redirect**, not a per-object override table. Using it
  as "we can therefore change one Gunner's weight" would be exactly the leap this
  phase is supposed to avoid.
- Two related references, also read-only: `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_spin.rs`
  (`air_exec`) writes KineticModule energies **on one fighter's battle object** from a
  status-scope `Exec` callback, for one status only - a real example of a per-object
  write, but of a kinetic, not of a parameter row. And
  `mods/ssbu_mod_new/src/mgw_standalone/vendor/ssbu_clone_engine/docs/wiki/PARAMETERS.md`
  is explicit that engine attributes are read past `ParamConfig`'s hooks, so a
  ParamConfig entry only half applies.

The mod repo's own extractors
(`mods/ssbu_mod_new/src/pgwr/tools/extract_gw_params.py`,
`mods/ssbu_mod_new/src/mgw_swap/tools/extract_hero_spin3_params.py`) show the
generation pattern: read the `.prc`, emit a Rust table with the source path and SHA-256
in the header, never hand-write a number.

---

## 9. Coverage gaps and limitations

1. **ACMD / game scripts are not local.** The dumped script tree
   (`dumps/scripts/SSBU-Dumped-Scripts-main`) is absent from this workspace. Script
   *names* were recovered by hash; script *bodies* were not read. Everything about hit
   boxes, damage, hitstop and which helper an alternative spawns is therefore outside
   this report. `vl.prc` does carry `hit_data` and `map_collision_*` per move, which is
   the next place to look.2. **202 of 774 motion kinds are still unnamed** (149 of them have no animation at all
   and look like pure script/state entries). Of the 53 that carry a clip, every one
   is an item move, a ledge / sleep / furafura / step state, an `a03jumpf` locomotion
   entry, a `share_*` set, or one of the two directional up-special variants
   (`0x0d3aaf0366` on `d02specialhi3f`, `0x0d3dc2c77f` on `d02specialhi3b`).
   **No user-facing normal, special, grab, pummel, throw or Final Smash kind is
   unresolved.** Correction 2026-10-04 (P1-CATALOG-AUDIT): this claim survives, but
   the earlier statement that `attack_s3_s` had no game script was wrong - it is
   `game_attacks3`. The label table simply has no `game_*` entries, so game scripts
   must be matched by the kind-name form, and §2's `-` cells are now filled.
3. **No costume coverage.** Only `c00` was decoded for the body list. `c06`/`c07` exist
   and should be checked before assuming one script per slot.
4. **Clip-name ambiguity.** Animation resolution hashes the *basename*, so identical
   basenames in different motion folders collide. This bit `d04final*` (section 3). For
   the body list itself this is not a problem, because every clip it names is under
   `body/c00`.
5. **AI tables were extracted but not mined** (`attack_list_param.prc` 2,530 scalars,
   0 unlabelled keys; `attack_data_param.prc`). They are a cross-check on which slots
   the game itself considers selectable, and are the obvious next input.
   **Correction 2026-10-04 (P1-CATALOG-AUDIT): this cross-check was attempted and is
   not usable for slot classification.** `attack_list_param.prc` contains **zero**
   occurrences of any Gunner `attack_*` motion-kind hash, so it cannot name a slot.
   Its 34 attack keys are AI *input/action* fields (`attack_quick_s`,
   `attack_power_s`, `attack_air_f_e`, ...), a different vocabulary from motion kinds.
   Do not present it as a player-facing slot list.
6. **No runtime evidence at all.** No console, no emulator, no build. Every runtime
   statement in this report is marked D or explicitly attributed to the reference mod.
7. **Mii identity is untouched.** Which saved-Mii maps to which battle object is P1-ID
   work; this report says nothing about it beyond "row 82 is keyed by kind, not by
   saved Mii".

## 10. One small next task

**Decode `fighter/miigunner/ai/param/attack_list_param.prc` and cross-tabulate it
against the 22 slots in section 2 plus the four special families in section 3.**

Why it is the right size: the file is already extracted and decoded (2,530 scalars,
zero unlabelled keys), it needs no new tooling, and it answers a question this report
cannot - *which of these slots does the game itself treat as a distinct, offered
choice?* That is the difference between a menu entry list and a motion dump (18 normal
slots in section 2, 11 grab/pummel/throw slots in section 5, four special families with
3 + 3 + 3 + 3 alternatives), and it is the last cheap input before Phase 2 has to
choose.

Deliverable: `research/P1-CATALOG-AI.md` plus `evidence/P1-CATALOG-AI/`. Deliverable
size: one table and a short gap list. Stop after that.

Escalation is **not** requested from this task. Nothing found here needs native RE to
continue; the open questions (per-object scope, safe ranges) need a measurement, not a
disassembly.

---

## Summary

- **P1-CATALOG: DONE** (bounded catalogue complete; gaps listed, not guessed away).
- **Changed files** (all inside this task's exclusive write paths):
  - `mods/mii_customizer/research/P1-CATALOG.md` (this report)
  - `mods/mii_customizer/evidence/P1-CATALOG/EXTRACTION.md`
  - `mods/mii_customizer/evidence/P1-CATALOG/gunner_body_c00_motion_list.json`
  - `mods/mii_customizer/evidence/P1-CATALOG/gunner_body_c00_motion_list_resolved.json`
  - `mods/mii_customizer/evidence/P1-CATALOG/gunner_body_c00_slots.txt`
  - `mods/mii_customizer/evidence/P1-CATALOG/gunner_vl_prc_labelled.tsv`
  - `mods/mii_customizer/evidence/P1-CATALOG/gunner_fighter_param_row82.tsv`
  - `mods/mii_customizer/evidence/P1-CATALOG/gunner_stat_candidates.tsv`
  - `mods/mii_customizer/evidence/P1-CATALOG/fighter_common_param_fighter_param_labelled.tsv`
  - `mods/mii_customizer/evidence/P1-CATALOG/fighter_common_param_common_labelled.tsv`
  - `mods/mii_customizer/evidence/P1-CATALOG/fighter_common_param_battle_object_labelled.tsv`
  - `mods/mii_customizer/evidence/P1-CATALOG/fighter_miigunner_ai_param_attack_list_param_labelled.tsv`
  - `mods/mii_customizer/scratch/2026-10-04_P1-CATALOG/` (3 scratch scripts, disposable)
- **Extraction outputs** (outside the mod tree, as the phase allows):
  `gamedata/mii_customizer/P1-CATALOG/files/` - 21 files, no animations, no models.
- **Observed checks:** motion-list round trip on 15 files; 774/774 animation hashes
  resolved; 572/774 kinds named; 379/774 game scripts named; 23/23 stat key hashes
  equal `hash40(name)`; Gunner row identity confirmed by `fighter_kind`.
- **Unresolved questions:** per-battle-object scope for a stat edit; safe ranges;
  Final Smash / get-up / ledge / taunt scope; which helper belongs to which special
  alternative; two directional up-special kind names.
  **Resolved 2026-10-04 by P1-CATALOG-AUDIT:** whether a side tilt exists (it does -
  `attack_s3_s` / `game_attacks3`), and the meaning of the `cancel` column (the raw
  `u16` packs `cancel_frame` with a `no_stop_intp` bit in `0x100`).
- **Blockers:** none.
