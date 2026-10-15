# P3-SPECIAL-VARIANTS - what one Gunner special variant consists of, in the files

Task: **P3-SPECIAL-VARIANTS**. Worker: Space Bunny Alpha. Date: 2026-10-04.
Prompt: `prompts/P3-SPECIAL-VARIANTS.md`. Phase: 3.

Goal: a **file-level inventory** of the game-file resources that belong to each
of Mii Gunner's twelve special variants (four slots x three vanilla variants),
with hashes, so that a later task can consider how a slot could take a different
move. This task does **not** propose that swap.

Evidence tiers: **B** = measured offline from pinned local binaries by scripts
that still exist; **C** = pinned external source; **D** = hypothesis. **No A** -
nothing was run on hardware or in an emulator. No runtime behaviour is claimed
anywhere below.

Paths are relative to `mods/mii_customizer/` unless marked workspace-relative.

Read first and corrections honoured: `research/P1-CATALOG.md`,
`research/P1-CATALOG-AUDIT.md`, `research/P1-DATASET.md`,
`tools/gunner-catalog/README.md`, `evidence/P1-DATASET/gunner_catalog.json`,
workspace-relative `kb/playbooks/extracting-single-files-from-data-arc.md` and
`tools/REGISTRY.md`. Inside `mods/ssbu_mod_new/`: `AGENTS.md`,
`projects/pgwr/STATUS.md`, `handbook/00_INDEX.md`, then only
`handbook/04_motion_lists_animation.md`, `handbook/07_articles.md` and
`handbook/09_params_prc.md`. Read-only; nothing there was modified.

---

## 0. Inputs, commands, and what was not needed

All five inputs were already extracted. **No extraction was performed by this
task** and `gamedata/mii_customizer/P3-SPECIAL-VARIANTS/` stayed empty.

| role | path (workspace-relative) | bytes | sha256 |
|---|---|---|---|
| Gunner body c00 motion list | `gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin` | 46272 | `2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba` |
| Gunner param | `gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/param/vl.prc` | 10192 | `c3600293023f7098de6e7d6e2795dfe9b9948502d0390bc0f30982e92f3bcd27` |
| common fighter param | `gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc` | 176604 | `87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2` |
| name dictionary | `mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv` | 3099694 | `6ae7f792609612370e6b9244e1d6986ebd8ced9bbb77fad49de8c568919344f4` |
| archive path index | `mods/ssbu_mod_new/dumps/decoded/arc_files.tsv` | 33805812 | `727a03c518ecb4614e8bca07202e916a9c2f4305f3f63a54b9d21a6db2c26369` |

The first hash matches the value the coordinator already verified, so the
extraction is the same one every earlier task used.

The archive index was consulted **before** concluding anything was missing. It
lists 590,711 paths and already contained every animation, weapon folder and
param this inventory needs, so `tools/arc-extract` was not run. The index was
used as a **path index**, per `handbook/09` rule R-ARC-1: the YAP container
stores hashes, not names, so nothing here was tested by grepping `data.arc`.

Commands (run from the workspace root, `python`, not `python3`):

```sh
python -B mods/mii_customizer/scratch/2026-10-04_P3-SPECIAL-VARIANTS/build_special_variants.py
python -B mods/mii_customizer/scratch/2026-10-04_P3-SPECIAL-VARIANTS/check_special_variants.py
```

The check exits **0** with **89 passed, 0 failed** (`evidence/P3-SPECIAL-VARIANTS/check_output.txt`).
The generator reads the shared readers `mlist.py` and `prc.py` by path and never
modifies them. `mlist.encode(parse(x)) == x` holds for the motion list
(`round_trip_encode_equal: true`); per the coordinator's standing correction, that
proves byte preservation only, never field meaning.

**Corrections carried in from earlier tasks and not repeated:**
`attack_s3_s` is the side/forward tilt, not a smash; the trailing `u16` packs
`cancel_frame` with `no_stop_intp` at bit `0x100` (so 334 is really 78); the AI
attack list contains no motion-kind hashes and cannot classify slots; four
`special_lw1_*` `_l` kinds share their base kind's `game_script` hash.

---

## 1. The naming rule, and proof that it holds for all twelve variants

Two independent rules were used, and an entry is assigned only when **both**
agree.

* **R1 (kind name).** A body motion entry belongs to slot `S`, variant `V` when
  the label joined on its kind hash matches
  `^special_(air_)?(n|s|hi|lw)(1|2|3)(_|$)`.
* **R2 (animation file name).** Cross-check read straight off the clip file
  name: `^[a-z]\d\d(?:special)?(air)?(n|s|hi|lw)(1|2|3)`.

| measurement | result |
|---|---|
| entries in the body c00 motion list | 774 |
| entries assigned | **70** |
| entries where R1 **and** R2 both match | **70 / 70** |
| entries where the two rules disagree | **0** |
| assigned entries form one contiguous run | **yes, indices 89..158** |

R2 is the load-bearing check: it reads the clip file name, an entirely
different byte field from the kind hash that R1 uses, so agreement on all 70 is
a real cross-check rather than a restatement. `motion_source.special_block_is_contiguous`
is `true` in the JSON.

**The four kinds `P1-CATALOG-AUDIT` had to record as unnamed are now resolved.**
`ParamLabels.csv` has no label for them, so the name was recovered from the
clip name and accepted **only** on a hash match: strip the leading 3-character
prefix (`d00`/`d02`/...), then try every insertion of underscores into the
remaining letters and keep a candidate only if `hash40(candidate)` equals the
entry's own kind hash. Each search returned **exactly one** hit:

| entry | kind hash | recovered name | candidates tried |
|---|---|---|---|
| 105 | `0x12772b6b5f` | `special_air_n2_end` | 16384 |
| 128 | `0x15eba8646e` | `special_air_hi3_start` | 131072 |
| 130 | `0x0d3aaf0366` | `special_hi3_f` | 1024 |
| 131 | `0x0d3dc2c77f` | `special_hi3_b` | 1024 |

`P1-CATALOG-AUDIT` recorded these two up-special directional kinds as unresolved
and warned they "must not be guessed into a UI label". This is not a guess: a
unique exhaustive search over the whole candidate space produced a name whose
hash equals the stored hash. The earlier caution still stands for *labels* - the
game's own display strings are not in these files, and none are claimed here.

With the names in hand, R1 matches all 70 and **no entry of the 70 is
unassigned**.

---

## 2. The twelve variants, one section per slot

Per-entry detail - animation files, all four script names, flags, blend and the
four timing bytes - is in `evidence/P3-SPECIAL-VARIANTS/entry_tables.txt`, which
is generated from the JSON. Nothing below is typed by hand.

### 2.1 Slot `n` (neutral) - entries 89..109

| variant | entries | ground/air | animation files | articles | param group / row |
|---|---|---|---|---|---|
| n1 | 11 | 5 / 6 | 9 distinct | none linked | `param_special_n` row 0 |
| n2 | 6 | 3 / 3 | 6 | `rapidshot_bullet` (by name only) | `param_special_n` row 1 |
| n3 | 4 | 2 / 2 | 4 | none linked | `param_special_n` row 2 |

* **n1** `special_n1_start`, `_hold`, `_cancel`, `_fire`, `_fire_max` plus the
  air mirrors `special_air_n1_start`, `_hold`, `_cancel`, `_jump_cancel`,
  `_fire`, `_fire_max`. `special_n1_fire` and `special_n1_fire_max` name the
  **same clip** `d00specialn1.nuanmb` and differ only in script hashes - one
  charge level, two kinds. The air pair does the same on
  `d00specialairn1.nuanmb`.
* **n2** `special_n2_start`/`_loop`/`_end` and the air mirror, with entry 105
  recovered as `special_air_n2_end` (clip `d00specialairn2end.nuanmb`).
* **n3** `special_n3_start`/`_end` and the air mirror.

### 2.2 Slot `s` (side) - entries 110..121

| variant | entries | ground/air | animation files | articles | param group / row |
|---|---|---|---|---|---|
| s1 | 2 | 1 / 1 | 2 | none linked | `param_special_s` row 0 |
| s2 | 6 | 3 / 3 | 6 | none linked | `param_special_s` row 1 |
| s3 | 4 | 2 / 2 | 4 | none linked | `param_special_s` row 2 |

`special_s1`/`special_air_s1`; `special_s2_start`/`_loop`/`_end` plus air;
`special_s3_1`/`special_s3_2` plus air. Note the R1 rule reads `special_s3_1` as
slot `s` variant `3` stage `1` - the direction token and the variant digit are
distinct positions in the name, which is why `s3_1` and `s3_2` are two stages of
one variant rather than two variants.

### 2.3 Slot `hi` (up) - entries 122..132

| variant | entries | ground/air | animation files | articles | param group / row |
|---|---|---|---|---|---|
| hi1 | 2 | 1 / 1 | 2 | none linked | `param_special_hi` row 0 |
| hi2 | 3 | 2 / 1 | 3 | none linked | `param_special_hi` row 1 |
| hi3 | 6 | 4 / 2 | 6 | none linked | `param_special_hi` row 2 |

* **hi1** `special_hi1` + air mirror.
* **hi2** `special_hi2` and `special_hi2_squat`, with only an **air** squat
  (`special_air_hi2_squat`) and no air move entry.
* **hi3** `special_hi3_start`, `special_hi3`, the two recovered directional
  kinds `special_hi3_f` / `special_hi3_b` (clips `d02specialhi3f`,
  `d02specialhi3b`), the recovered `special_air_hi3_start` and the air end
  `special_air_hi3_end`. **hi3 is the only variant with directional clips.**

Ground and air entries are **not** balanced for three of the twelve: `n1` is
5/6, `hi2` is 2/1 and `hi3` is 4/2. The other nine are exactly balanced. Only
`hi2` lacks an air counterpart for a kind that has a ground one
(`special_hi2_squat` -> `special_air_hi2_squat` exists, but `special_hi2` has no
air move entry); `n1` and `hi3` are unbalanced because a variant can have more
ground stages than air ones (`n1` adds `special_air_n1_jump_cancel`, `hi3` has
two extra ground directional clips).

### 2.4 Slot `lw` (down) - entries 133..158

| variant | entries | ground/air | animation files | articles | param group / row |
|---|---|---|---|---|---|
| lw1 | 16 | 8 / 8 | 16 | none linked | `param_special_lw` row 0 |
| lw2 | 2 | 1 / 1 | 2 | none linked | `param_special_lw` row 1 |
| lw3 | 8 | 4 / 4 | 8 | none linked | `param_special_lw` row 2 |

* **lw1** `special_lw1_start`/`_loop`/`_hit`/`_end`, their `_l` forms, and the
  full air mirror of both - 16 entries, the largest variant in the file. The
  `_l` kinds share their base kind's `game_script` hash exactly (measured in
  `P1-CATALOG-AUDIT`) and differ only in clip.
* **lw2** `special_lw2` + air mirror.
* **lw3** `special_lw3_start`/`_hold`/`_hit`/`_end` plus air mirror.

---

## 3. Summary table - all twelve variants

| slot | variant | motion entries | ground/air | distinct animation files | all animation files in index | articles | param group | param row | param fields | non-zero numeric prefixes |
|---|---|---|---|---|---|---|---|---|---|---|
| n | 1 | 11 | 5/6 | 9 | yes | - | `param_special_n` | 0 | 13 | `n1` |
| n | 2 | 6 | 3/3 | 6 | yes | `rapidshot_bullet` (by name only) | `param_special_n` | 1 | 13 | `n2` |
| n | 3 | 4 | 2/2 | 4 | yes | - | `param_special_n` | 2 | 13 | `n3` |
| s | 1 | 2 | 1/1 | 2 | yes | - | `param_special_s` | 0 | 16 | `s1` |
| s | 2 | 6 | 3/3 | 6 | yes | - | `param_special_s` | 1 | 16 | `s2` |
| s | 3 | 4 | 2/2 | 4 | yes | - | `param_special_s` | 2 | 16 | `s3` |
| hi | 1 | 2 | 1/1 | 2 | yes | - | `param_special_hi` | 0 | 35 | `UNLABELLED`, `hi1` |
| hi | 2 | 3 | 2/1 | 3 | yes | - | `param_special_hi` | 1 | 35 | `hi2` |
| hi | 3 | 6 | 4/2 | 6 | yes | - | `param_special_hi` | 2 | 35 | `hi3` |
| lw | 1 | 16 | 8/8 | 16 | yes | - | `param_special_lw` | 0 | 24 | `lw1` |
| lw | 2 | 2 | 1/1 | 2 | yes | - | `param_special_lw` | 1 | 24 | `lw2` |
| lw | 3 | 8 | 4/4 | 8 | yes | - | `param_special_lw` | 2 | 24 | `lw3` |

Entries sum to **70**; indices are unique across all twelve variants (asserted
by the check). `lw` rows 0 and 1 also carry `lw3_phy_magnet_parts`, discussed in
§4.2 - that field is not a `lw3` variant value and is excluded from the last
column.

---

## 4. Script references, articles, and parameters

### 4.1 Script references in the motion entries

Every one of the 70 entries stores four script references: `game_script` in the
entry header, and `expression`, `sound` and `effect` as the first three `u64` of
the tail (`handbook/09` / `P1-CATALOG-AUDIT`). **All 280 resolved, 0 left as
hashes.** A name is emitted only when `hash40(name)` equals the stored field, so
a wrong rule would have failed loudly rather than inventing a name. Full
per-entry listing in `entry_tables.txt`; representative rows:

| entry | kind | game | expression | sound | effect |
|---|---|---|---|---|---|
| 89 | `special_n1_start` | `game_specialn1start` | `expression_specialn1start` | `sound_specialn1start` | `effect_specialn1start` |
| 92/93 | `special_n1_fire` / `_fire_max` | `game_specialn1fire` / `game_specialn1firemax` | `expression_specialn1fire` / `...firemax` | `sound_…` | `effect_…` |
| 122 | `special_hi1` | `game_specialhi1` | `expression_specialhi1` | `sound_specialhi1` | `effect_specialhi1` |
| 133/141 | `special_lw1_start` / `_start_l` | **both** `game_speciallw1start` | **both** `expression_speciallw1start` | **both** `sound_speciallw1start` | **both** `effect_speciallw1start` |

These are **names only**, exactly as the motion list stores them. No script body
was read (`handbook/09` notes `dumps/scripts/SSBU-Dumped-Scripts-main` is absent
from this workspace), so nothing is said about what any of them does.

The `special_lw1_*` `_l` rows re-confirm the `P1-CATALOG-AUDIT` measurement from
a second angle: the `_l` kinds share **all three** tail script hashes with their
base kinds, not just `game_script`. They differ only in clip.

### 4.2 Articles / weapons

The archive index shows **14 separate weapon/article folders** under
`fighter/miigunner/`, excluding the 49 `b_*` body-costume folders:

| folder | model folder | motion folder | ARC files | motion list entries | entry kind names | variant link |
|---|---|---|---|---|---|---|
| `attackairf_bullet` | - | yes | 1 | 1 | `fly` | not linked |
| `bottomshoot` | - | yes | 1 | 1 | `shoot` | not linked |
| `flamepillar` | - | yes | 1 | 2 | `shoot`, `pillar` | not linked |
| `fullthrottle` | yes | yes | 23 | 5 | `final_start`, `final`, `final_u`, `final_d`, `final_end` | not linked |
| `grenadelauncher` | yes | yes | 17 | 2 | `fly`, `explode` | not linked |
| `groundbomb` | yes | yes | 18 | 3 | `fly`, `fly_flash`, `burst_attack` | not linked |
| `gunnercharge` | - | yes | 1 | 2 | `charge`, `shoot` | not linked |
| `hat` | - | yes | 1 | 1 | `dummy` | not linked |
| `laser` | - | yes | 1 | 2 | `charge`, `shoot` | not linked |
| `miimissile` | yes | yes | 18 | 2 | `homing`, `h_burst` | not linked |
| `rapidshot_bullet` | - | yes | 1 | 4 | `fly`, `fly_throw_b`, `fly_throw_hi`, `fly_throw_hi_2` | **n / variant 2, by name only** |
| `stealthbomb` | - | yes | 1 | 2 | `move`, `tame` | not linked |
| `stealthbomb_s` | - | yes | 1 | 1 | `move` | not linked |
| `supermissile` | yes | yes | 18 | 2 | `straight`, `s_burst` | not linked |

Only **five** have a `model/` folder (`fullthrottle`, `grenadelauncher`,
`groundbomb`, `miimissile`, `supermissile`); the other nine are motion-only in
`c00`. Each folder's `motion/c00/motion_list.bin` was parsed and hashed
(individually in `articles[].local_motion_list.sha256`). Per `handbook/07`, an
article is per fighter *kind* across all 8 slots, and `fullthrottle` is Final
Smoke, not a special variant - its kinds are `final_*`, and it is listed here
only because it is an archive folder under `fighter/miigunner/`.

**Exactly one link is measurable, and it is a name link.** The seven
`param_special_n` row-1 field names `n2_rapidshot_shoot_x`, `…_shoot_y`,
`…_shoot_speed`, `…_air_shoot_x`, `…_air_shoot_y`, `…_angle_throw_b`,
`…_angle_throw_hi` share the token `rapidshot` with the archive folder
`rapidshot_bullet`, and those seven fields are the ones that are **non-zero in
row 1 and zero in rows 0, 2 and 3**. That is recorded as
`link_basis: BY_NAME_ONLY`. It is a shared string in two files. Nothing in the
body motion list, the `rapidshot_bullet` motion list or the param file
references the other by name or id, so **this is NOT a dependency** and is not
offered as one.

The link test deliberately requires the param field to be non-zero **in that
row**. Every row shares one field-name set, so a name-only test would have
linked `rapidshot_bullet` to all three neutral variants at once - which was the
first version of this script's output, and was wrong.

For the other 13 folders there is **no** measured link to any variant. Naming
them by what they appear to do would be a guess, so `variant_link` is `null` and
`variant_link_basis` is `NOT_LINKED`.

### 4.3 Parameters in the Gunner's own `vl.prc`

`fighter/miigunner/param/vl.prc` (10192 bytes) is a root struct with **42**
top-level groups. Group kind and size:

| group | type | entries | named for a special variant? |
|---|---|---|---|
| `param_special_n` | list | 4 | **yes** |
| `param_special_s` | list | 4 | **yes** |
| `param_special_hi` | list | 4 | **yes** |
| `param_special_lw` | list | 4 | **yes** |
| `hit_data` | list | 10 | no |
| `hit_target` | list | 3 | no |
| `map_coll_data` | list | 6 | no |
| `jostle_map_coll_data` | list | 6 | no |
| `virtual_node_data_hit` | list | 10 | no |
| `virtual_node_data_hit_flip` | list | 4 | no |
| `hit_data_ground_bomb` | list | 1 | no |
| `hit_data_flamepillar` | list | 2 | no |
| `mii_hat_node_data` | list | 7 | no |
| `param_private` | struct | 9 fields | no (all `final_laser_*`/`final_a_*`) |
| `cliff_hang_data` | list | 1 | no |
| `param_hat`, `param_laser`, `param_reflector`, `param_miimissile`, `param_groundbomb`, `param_attack_airf`, `param_flamepillar`, `param_bottomshoot`, `param_stealthbomb`, `param_fullthrottle`, `param_gunnercharge`, `param_supermissile`, `param_stealthbomb_s`, `param_grenadelauncher`, `param_rapidshot_bullet`, `param_attackairf_bullet` | list | 1 each | no |
| `map_collision_{laser,groundbomb,miimissile,flamepillar,stealthbomb,gunnercharge,fullthrottle,supermissile,grenadelauncher,rapidshot_bullet,attack_airf_bullet}` | struct | 4 fields each | no |

Only the four `param_special_*` groups are named for a special variant. The
352 field paths in `vl.prc` whose name contains "special" all live in those four
groups and nowhere else.

Field names, hashes and values for all four groups are in theJSON (`params.vl_prc.special_variant_groups.<token>.rows[i].fields`), every one with
its hash verified. Fields per row: `param_special_n` **13**, `param_special_s`
**16**, `param_special_hi` **35**, `param_special_lw` **24**.

**One field is unlabelled.** `param_special_hi` carries
`UNLABELLED_0x250a27ba9b`, float `0.7` in row 0 and `0.0` in rows 1-3. It stays
a hash; `ParamLabels.csv` has no name for it and none was invented. Its
non-zero-in-row-0-only pattern means it behaves like an `hi1` field, but that is
an observation about values, not a name.

### 4.4 Special-named fields in the common `fighter_param` table

`fighter_param_table` has **94 rows**. The Gunner row is **row 82**, found
uniquely by `fighter_kind == hash40("fighter_kind_miigunner")`, and holds **369**
keys. **Eleven** of them have "special" in the label - the same eleven names in
every row of the table, so none is Gunner-specific:

| field | hash | type | value | value name |
|---|---|---|---|---|
| `special_s_brake` | `0x0fb53839e9` | float | `0.2` (`0x3e4ccccd`) | - |
| `trail_special_s_joint_id` | `0x187367db00` | hash | `21914596379` | `waist` |
| `trail_special_lw_rebound_air` | `0x1c08c51661` | hash | `53843765742` | `damage_air_1` |
| `trail_special_lw_rebound_ground` | `0x1fc14378fa` | hash | `33781844542` | `rebound` |
| `trail_special_lw_rebound_fall_comp_frame` | `0x281b06d9e5` | float | `6.0` (`0x40c00000`) | - |
| `dolly_super_special2_offset_x` | `0x1da00f670f` | float | `0.0` | - |
| `dolly_super_special2_offset_y` | `0x1dd7085799` | float | `3.0` (`0x40400000`) | - |
| `dolly_super_special2_offset_z` | `0x1d4e010623` | float | `1.0` (`0x3f800000`) | - |
| `dolly_super_special2_offset_x_ground` | `0x24724ea534` | float | `0.0` | - |
| `dolly_super_special2_offset_y_ground` | `0x24bee4a5aa` | float | `5.0` (`0x40a00000`) | - |
| `dolly_super_special2_offset_z_ground` | `0x24306ba249` | float | `1.0` (`0x3f800000`) | - |

The `dolly_super_special2_*` fields are Final Smash / super-dolly camera offsets
and carry the word "special" incidentally; they do not name a special variant.
The four `trail_special_*` fields name effect trails by hash and are the only
special-named Gunner fields that point at an effect resource. What a field does
is deliberately **not** explained here.

### 4.5 Effects and sounds

Only what the motion entries name directly: the `effect_*` and `sound_*` script
names in §4.1, all 140 of them, by name only. **No effect bank and no sound bank
was opened** - no `.eff`, `.sqb` or trail file was read, and no claim is made
about any of them.

---

## 5. What in these files selects between variants 1, 2 and 3

This was asked directly, so it is answered with the bytes and nothing more.
Four candidates were examined; two exist, two do not.

**(a) A four-row param table per slot - exists. `B`.**
`param_special_n`, `_s`, `_hi`, `_lw` are each a **4-row list**. Measured, for
all four groups:

* all four rows carry **the same field-name set** (`shared_field_name_set: true`);
* in rows 0, 1 and 2 the **only** fields holding a non-zero numeric value are
  those whose name starts with that row's own variant token - row 0's `n1_*`,
  row 1's `n2_*`, row 2's `n3_*`, and so on for `s`, `hi`, `lw`;
* **row 3 has every numeric field at zero**;
* one field, `param_special_lw`'s `lw3_phy_magnet_parts`, holds the **same
  non-numeric value `23356055229` in all four rows**, including row 3. It is
  tagged `hash`, so it has no numeric zero; the JSON names it separately under
  `non_numeric_fields_holding_one_value_in_every_row` rather than letting it
  quietly break the "row 3 is zero" statement.

So the bytes show a per-slot table where **row `i` carries variant `i+1`'s
numeric values and row 3 is a numeric-zero row**. That is the whole claim.
**Which code indexes this list, and with what value, is not established by these
files.** The coordinator's P2 work found the editor's four option bytes hold
`0..2` per slot; whether that byte is the row index here is exactly the kind of
link that needs a measurement, not an assumption.

**(b) Position in the motion list - exists as order, not as a stored field. `B`.**
The 70 special entries are one contiguous run, ordered neutral 1/2/3, then side
1/2/3, then up 1/2/3, then down 1/2/3, with ground kinds before their air
mirrors inside each variant. An entry's index is a **position in this file**,
not a selector field.

**(c) A variant index in the motion entry - does not exist. `B`.**
The entry header is `kind_hash, game_script_hash, flags_u16, blend_u8,
animation_count_u8, size_u32`, then the animation hashes, then the tail (three
script hashes plus `xlu_start`, `xlu_end`, `cancel_frame`, `no_stop_intp`). There
is **no** variant index, slot number or option id in the header or the tail.

**(d) A three-rows-per-slot table - none found in these files. `B`.**
`hit_target` has 3 rows but no special-named fields; `hit_data` has 10 rows,
also with no special-named fields. The variant-shaped table is the 4-row one in
(a).

**(e) The naming suffix - exists as convention. `B` for the convention, `D` for
any claim that it drives anything.** The variant number is carried in the motion
kind name (`special_n1…`, `special_lw3…`) and in the clip file name
(`d00specialn1…`, `d03speciallw3…`). That is a naming convention read off the
files. Nothing here shows it is consulted when the game picks a variant.

---

## 6. Unassigned Gunner motion entries that look special-related

**26 entries** in the body c00 list carry "special" in a label or a clip name but
match neither R1 nor R2, so they belong to none of the twelve variants. They are
listed rather than dropped:

* **4 entries, indices 34-37** - `fall_special`, `fall_special_f`,
  `fall_special_b`, `landing_fall_special`, clips `a04fallspecial*.nuanmb`. The
  word "special" here is part of a fall/landing name, not a special variant.
* **22 entries, indices 712-743** - victim-side reactions carrying another
  fighter's name: `gaogaen_special_s_thrown_big`, `shizue_special_s_thrown_{f,b,hi,lw}`
  with `_dx`/`_girl`/`_big` suffixes, `jack_special_hi_thrown`,
  `jack_special_hi_pulled{,_dx,_girl,_big}`. All 22 have `flags = 0x00a8` and
  **zero animations** (`animation_count = 0`). They are other characters' throw
  reactions in Gunner's own motion list, not Gunner moves.

None of the 26 was force-fitted into a variant. `P1-CATALOG-AUDIT`'s caution
stands: movement recovery and victim states must not be classified as attacks
merely because they have distinct motion entries.

---

## 7. Limits

1. **No A evidence.** No console, no emulator, no build. Nothing here shows the
   game *reads* any of it. Every value is file-level (`B`).
2. **Script bodies are unavailable.** `dumps/scripts/SSBU-Dumped-Scripts-main` is
   absent, so the ~280 script names are names only. No statement is made about
   what any of them does, or about dependencies between variants.
3. **Which article belongs to which variant is unknown** for 13 of the 14
   folders. The one link that exists is a shared string, recorded as
   `BY_NAME_ONLY`, and is explicitly not a dependency.
4. **The 4-row param table's indexer is unknown.** §5(a) shows the shape. What
   code reads row `i`, and whether the editor's 0..2 option byte is that index,
   is not established.
5. **Animation name resolution is a basename join and is ambiguous.** Motion names
   hash *with* the extension, and these basenames are shared across fighters:
   every one of the 70 clips resolves to between 9 and 93 ARC paths, spanning 31
   fighter folders (`ike`, `miienemyg`, `nana`, `trail`, ...). All 70 do have
   exactly **one** `fighter/miigunner/` path, and the JSON keeps the full list
   plus a `miigunner_arc_paths` subset so the collision stays visible. The claim
   made is "present under `fighter/miigunner/`", not "uniquely present".
6. **Only `body/c00` was read.** `c06`/`c07` costume sets exist and were not
   decoded, so one script per variant per costume set is **not** established.
   `P1-CATALOG-AUDIT` left this open and it is still open.
7. **`xlu_start`/`xlu_end`/`cancel_frame`/`no_stop_intp` are authored bytes.**
   Their layout was pinned for GameWatch body c00 by `P1-CATALOG-AUDIT` and
   applied here on the strength of identical layout - an inference across
   fighters, not a separate Gunner decode.
8. **One unlabelled param field** (`UNLABELLED_0x250a27ba9b`) remains a hash.
9. **Not attempted, by scope:** how a slot could take a different move, normals,
   Brawler, Swordfighter, Final Smash scope, get-up/ledge/taunt scope. Final
   Smash appears only as an archive folder, not as a special variant.
10. **A shared-name link is not a dependency** - this is enforced in the JSON
    schema (`link_basis` is only ever `BY_NAME_ONLY` or `NOT_LINKED`, asserted by
    the check) and repeated here so it cannot be read past.
11. **No runtime behaviour is claimed anywhere in this report.** Source
    inspection and byte measurement do not establish it.

---

## 8. Deliverables and how to re-run them

| file | role |
|---|---|
| `research/P3-SPECIAL-VARIANTS.md` | this report |
| `evidence/P3-SPECIAL-VARIANTS/special_variants.json` | the machine-readable inventory (674 KB) |
| `evidence/P3-SPECIAL-VARIANTS/entry_tables.txt` | per-entry listing generated from the JSON |
| `evidence/P3-SPECIAL-VARIANTS/check_output.txt` | inventory check output, 89 passed / 0 failed |
| `evidence/P3-SPECIAL-VARIANTS/report_claims_output.txt` | prose check output, 111 passed / 0 failed |
| `scratch/2026-10-04_P3-SPECIAL-VARIANTS/build_special_variants.py` | generator |
| `scratch/2026-10-04_P3-SPECIAL-VARIANTS/check_special_variants.py` | inventory check |
| `scratch/2026-10-04_P3-SPECIAL-VARIANTS/check_report_claims.py` | prose-vs-data check |

```sh
# regenerate
python -B mods/mii_customizer/scratch/2026-10-04_P3-SPECIAL-VARIANTS/build_special_variants.py
# verify the inventory: regenerates, compares, asserts every input sha256; nonzero on mismatch
python -B mods/mii_customizer/scratch/2026-10-04_P3-SPECIAL-VARIANTS/check_special_variants.py
# verify the report's numbers against the JSON
python -B mods/mii_customizer/scratch/2026-10-04_P3-SPECIAL-VARIANTS/check_report_claims.py
```

`check_report_claims.py` exists because the first two errors below were found by
a check and then **re-checked in prose**: it re-derives every number in this
report from the committed JSON, so a stale figure in the text fails loudly.

The check: asserts each of the five input sha256s; rebuilds and requires the
result to be **byte-identical** to the committed JSON; repeats the rebuild under
three `PYTHONHASHSEED` values; re-hashes every emitted motion kind, script and
param field name; asserts the 70/70 rule agreement, the contiguous 89..158 run,
the four-row table's shape per slot, the single by-name-only article link, and
that no absolute path appears. Negative controls include a broadened naming rule,
the correct rule rejecting a non-special kind, a doctored entry count, a
tampered recorded hash, and a wrong input file (the builder exits nonzero).
Rebuild temp files are written inside this task's scratch folder, never into the
current directory or the system temp dir.

JSON contains names, hashes, counts and numeric values only. No game file was
copied into the mod tree.

### Three errors this task's own checks caught

Recorded because all three would have shipped wrong numbers:

1. **`param_special_lw` row 3 is not all zeros.** The first draft asserted "row 3
   holds all zeros" for all four groups. The check failed: `lw3_phy_magnet_parts`
   (a `hash`-typed field, value `23356055229`, label `trans`) is identical in all
   four rows. Corrected to "every **numeric** field at zero", with the exception
   named explicitly in the JSON.
2. **`rapidshot_bullet` was linked to all three neutral variants.** The link test
   matched on the param *field name* alone, but every row of `param_special_n`
   shares one field-name set, so the seven `n2_rapidshot_*` names matched in all
   four rows. Corrected to require the field to be non-zero **in that row**, which
   leaves a single link: `rapidshot_bullet` -> neutral variant 2.
3. **Two wrong figures survived into this report's first draft** and were caught
   only by `check_report_claims.py`: `param_special_lw` was described as 22
   fields per row (**24**), and `hi2` was called the only variant with an
   unbalanced ground/air split (it is one of **three**: `n1`, `hi2`, `hi3`).
   Both corrected above. This is the argument for checking the prose against the
   data rather than trusting that a correct generator implies a correct report.

---

## Summary

- **P3-SPECIAL-VARIANTS: DONE.**
- **Changed files** (all inside this task's exclusive write paths):
  - `research/P3-SPECIAL-VARIANTS.md` (this report)
  - `evidence/P3-SPECIAL-VARIANTS/special_variants.json`
  - `evidence/P3-SPECIAL-VARIANTS/entry_tables.txt`
  - `evidence/P3-SPECIAL-VARIANTS/check_output.txt`
  - `evidence/P3-SPECIAL-VARIANTS/report_claims_output.txt`
  - `scratch/2026-10-04_P3-SPECIAL-VARIANTS/build_special_variants.py`
  - `scratch/2026-10-04_P3-SPECIAL-VARIANTS/check_special_variants.py`
  - `scratch/2026-10-04_P3-SPECIAL-VARIANTS/check_report_claims.py`
  - plus 18 `explore*.py` scratch scripts, disposable
- **No extraction.** `gamedata/mii_customizer/P3-SPECIAL-VARIANTS/` was created
  and left empty; the archive index was consulted first and everything needed was
  already present. No shared tool, dump, or other worker's file was modified;
  `mlist.py` and `prc.py` were imported read-only by path. `git status` shows no
  change under `mods/ssbu_mod_new/`.
- **Observed checks:** `check_special_variants.py` -> **89 passed, 0 failed,
  exit 0**. `check_report_claims.py` -> **111 passed, 0 failed, exit 0**.
  Rebuilt JSON byte-identical to the committed file across three `PYTHONHASHSEED`
  values. All five input sha256s re-verified, the first matching the
  coordinator's earlier value. 70/70 motion entries assigned with both naming
  rules agreeing; four previously unnamed kinds resolved by unique exhaustive hash
  search; 280/280 script names hash-verified; 352 `vl.prc` field values and 11
  `fighter_param` Gunner-row values read; 14 article folders enumerated. Three
  wrong claims in my own drafts were caught by these checks and corrected above.
- **Verified (B):** the twelve variants and their 70 motion entries; the naming
  rule and its agreement with an independent clip-name rule; every animation file
  present under `fighter/miigunner/`; the per-entry script names; the
  `vl.prc` group/row/field layout including the 4-row `param_special_*` tables;
  the article folder inventory and its single by-name-only link; that no variant
  index exists in a motion entry.
- **Unverified / D:** any runtime behaviour; which article belongs to which
  variant; what the 4-row table's indexer does; back-tilt routing (P1-ID's lane);
  `c06`/`c07`; the meaning of any param or script field.
- **Blockers:** none.
- **Next experiment (offline, and the obvious one):** decode
  `fighter/miigunner/motion/body/c06/motion_list.bin` and `c07` and diff the
  70 special entries against `c00`. That closes limit 6 with two files already in
  the archive index, needs no extraction decision, and is the one remaining
  input that would change the entry count in this inventory.
  **Second, if a link is wanted rather than an inventory:** search the pinned
  fighter NRO for the reader of `param_special_*` to establish whether the
  editor's 0..2 option byte indexes that 4-row table. That is native RE and
  should be a premium-scoped question, not guessed from these files.