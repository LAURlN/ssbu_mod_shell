# P14-SWORD-FACTS - What "Mii Gunner holds the Mii Swordfighter's sword during sword moves" Needs (Facts Only)

Task: `P14-SWORD-FACTS`
Worker: Buffy (Freebuff)
Date: 2026-10-07
Status: DONE (offline facts; in-game behaviour is out of scope and marked D)
Phase: Phase 5 scoping (match side of a future "Sword" option)

> **Read-first record.** `research/P11-MOVE-PLAN.md` was read with its 2026-10-07 coordinator
> banner: much of it is unverified by its own check, and its sword statements
> (`MiiS_Sword_VIS_O_OBJShape` on `HaveR`, `sheath` on `Bust`, 70 trail textures
> `tex_miiswordsman_sword01..70.nutexb`, "Gunner cannot load donor effect banks") are exactly
> what this task measures. Result: the mesh/sheath/trail-texture statements are confirmed
> (B); the jab "bone `haver`" statement is **refuted** for the game scripts (see Q6); the
> "Gunner cannot load donor effect banks" statement is confirmed indirectly by the ownership
> rule cited in Q3 (their tier B, in-game effect on a Gunner = D).
> `research/P12-FTILT-FACTS.md` (46 lines) and `research/P12-SCRIPT-ROUTE.md` (36 lines) exist
> but are **unfinished skeletons** ("IN PROGRESS", short answers unfilled) at the time this
> task started - noted, not used as inputs.
> If read inside `mods/ssbu_mod_new/` (reference only), its `AGENTS.md` and
> `handbook/00_INDEX.md` were read first; its claims are cited as `file:line` with *their*
> evidence tier and are tier C from this task's point of view.

Evidence Tiers (this task):
- **Tier A**: Hardware / console confirmed. (None in this task.)
- **Tier B**: Measured offline from pinned local binaries and extracted game files by
  reproducible scripts; for this task only what `evidence/P14-SWORD-FACTS/check_p14_sword_facts.py`
  re-reads is B.
- **Tier C**: Pinned external source (here: the other mod's handbook/code and the kb note,
  cited `file:line`, their own tier noted).
- **Tier D**: Hypothesis / unverified deduction, or anything about what happens in-game
  (no emulator, no hardware).

Rules of this task honoured: every name and number comes from a file hashed here; files
earlier tasks extracted (e.g. workspace `gamedata/mii_customizer/P11-MOVE-PLAN/`) were used
read-only; no file is claimed missing before checking the archive index
(`mods/ssbu_mod_new/dumps/decoded/arc_files.tsv`, 590,711 lines) and `tools/REGISTRY.md`;
no memory or internet. Paths are relative to `mods/mii_customizer/` unless prefixed
workspace-relative (`gamedata/…`, `mods/ssbu_mod_new/…`, `kb/…`, `tools/…`).

All file sizes and full sha256 of every file cited below are in
`gamedata/mii_customizer/P14-SWORD-FACTS/tables/file_inventory.tsv` (265 rows, every row
re-hashed by the check). Inline hashes below are the 12-char prefix.

---

## Short answers

### Q1. The Swordfighter's sword as data

**The sword is a mesh object inside the body model, rigid-parented to the bone `HaveR`.**
It is not a separate model slot and not an article/weapon object.

- Default costume (male): `fighter/miiswordsman/model/b_normalswordman_m/c00/model.numshb`
  (795,216 B, `b22c52a0ba2a…`) holds 8 mesh objects; the sword is
  `MiiS_Sword_VIS_O_OBJShape`, parent bone `HaveR`, 0 bone influences: 686 vertex
  positions, 2,868 entries in `vertex_indices` (the `verts` column of
  `tables/mesh_objects.tsv` counts those entries, not positions). (B)
- Sheath is separate mesh objects in the same file, parented to `Bust`:
  `miiswordsman_sheath_highShape` + `miiswordsman_sheath_lowShape` on the male body
  (1,128 / 826 vertex positions; `vertex_indices` 5,376 / 3,768); a single
  `miiswordsman_sheathShape` on the female body (1,128 positions / 5,376 index entries). (B)
- Male/female are separate mesh files: `b_normalswordman_f/c00/model.numshb`
  (755,312 B, `dc332f9c1365…`), same sword object name/parent/vertex count; the two
  skeletons are byte-identical (`model.nusktb` `e0407f6169cc…`, 20,160 B, for both). (B)
- Costume colour slots of the default costume are one asset: all 12
  `b_normalswordman_m/c00..c11/model.numshb` are byte-identical
  (`b22c52a0ba2a…`, 795,216 B each). The Mii's *alternate* costumes are separate model
  directories (53 `b_*` dirs, 12 colour slots each, 636 `model.numshb` paths in the archive
  index); 8 sampled (`chrom`, `dunban`, `link`, `lip`, `pirate`, `robin`, `takamaru`,
  `zero`) each carry their own `MiiS_Sword_VIS_O_OBJShape` on `HaveR` with different
  `vertex_indices` counts (402…3,666; vertex positions 151…794), `robin` also has a
  `swordsheathShape` on `Bust` (56 positions), `zero` has two `MiiS_Sword_VIS_O_OBJShape`
  objects (340 and 189 positions). (B)
- Materials: `model.numatb` (2,188 B, `0c662518ca4f…`) holds exactly 2 entries,
  `def_normalswordman_m_001` and `metal_normalswordman_m_001`, shader
  `SFX_PBS_0100000008008269_opaque`; textures `def_normalswordman_m_001_{col,nor,prm}.nutexb`
  and `metal_normalswordman_m_001_{col,nor,prm}.nutexb` in the same directory (all hashed in
  the inventory). Which of the 2 materials the sword object uses could **not** be read -
  `ssbh_data_py` 0.9.1 exposes no object→material binding (D).
- Article check: the archive index knows only `fighter/miiswordsman/{ai,model,motion,param}/`;
  under `model/` only 53 `b_*` costume dirs plus `chakram` (a projectile article model) - no
  sword model directory, no sword article files. The sword geometry lives only in the body
  mesh files. (B)

### Q2. How the game shows and hides it

**No per-move show/hide mechanism was found; exactly one script in the whole
`lua2cpp_miiswordsman.nro` touches the sword's visibility, and it is not a move.** Whether
the vanilla sword is therefore always visible during moves, and what that one call draws, is
D (no runtime).

- Animation evidence: 96 extracted motion clips were scanned. The visibility group of a
  clip contains only the 12 facial nodes (`MiiFighterM_eye_*`, `MiiFighterM_mouth_*`) in 95
  clips (1 clip has no visibility group at all); **0 clips contain a non-facial visibility
  node**, so no clip hides the sword, the sheath, or any mesh. Transform tracks contain 75
  nodes including `HaveR`. (B) Example clips for two sword moves:
  `c00attack11.nuanmb` (32,824 B, `069b485743b0…`) and `c01attacks3s.nuanmb`
  (35,320 B, `39bf0dff6738…`). (B)
- Script evidence, whole-NRO instruction-word scan (movz/movk hash40 builds): the word
  `sword_hide` (hash40 `0x0ab4f18a85`) occurs **exactly once** in
  `lua2cpp_miiswordsman.nro` (file offset `0xd9fa8`), `sword` (`0x59ae5c70f`) exactly once
  (`0xd9f94`); **0 hits in `lua2cpp_miigunner.nro` and `lua2cpp_common.nro`**. (B)
- The single site: script `expression_lose` (hash40 `0x0fc95c070a`, impl `0xd9f40`,
  registered at `0xbe0e8`) calls `VisibilityModule::set_int64(accessor, x1=hash40("sword"),
  x2=hash40("sword_hide"))`; `bl` at `0xd9fdc` → plt `0x192540`. Argument order proven by
  the disassembly: the value converted first (`as_integer` on `sp+0x10`, the `sword` value)
  ends in `x1`, the second (`sp`, `sword_hide`) in `x2`. (B)
- `expression_entryr`/`expression_entryl` (impl `0xda040`) each call
  `VisibilityModule::set_whole` twice (4 call sites, args `{}` and `{"x1": "1"}`); these are
  the only other `VisibilityModule` sites in the NRO (5 total). There are **no
  `ModelModule` calls at all** in the scanned registrations. (B)
- "Have item" style calls exist in abundance - `ItemModule::set_have_item_visibility`, 46
  sites in 43 scripts - but they act on held *items*, not on body meshes. (B)
- Two sword moves (script evidence):
  - **Jab 1** (`game_attack11`, impl `0x15b3d0`): 3× `sv_animcmd::ATTACK`; each ATTACK
    builds exactly two hash40 constants - bone-slot `hash40("top")` (`0x31ed91fca`, words at
    `0x15b498..0x15b4a0`) and `hash40("collision_attr_cutup")` (`0x14860b063a`). Its
    `effect_attack11` (impl `0xb5530`) attaches the trail to the **`haver`** bone
    (hash ctor at 743,576), calls `FOOT_EFFECT` (743,172),
    `AFTER_IMAGE4_ON_WORK_arg29` (744,128) and `AFTER_IMAGE_OFF` (744,564). Its
    `expression_attack11` (impl `0xfd400`) builds `haver` but makes no visibility call. (B)
  - **Forward tilt** (`game_attacks3`, impl `0x157ce0`): one `ATTACK` at 1,409,232 with the
    same two constants (`top`, `collision_attr_cutup`). `effect_attacks3` (impl `0xb2600`)
    builds `haver` (730,924), calls `AFTER_IMAGE4_ON_WORK_arg29` (731,476) and
    `AFTER_IMAGE_OFF` (732,484). (B)
- One "hidden" move: **none found** - no move-state script and no clip hides the sword. The
  only sword-visibility site is the non-move `expression_lose` (what state runs it, and what
  `sword_hide` selects visually, is D). So "is the sword always visible on a vanilla
  Swordfighter?" → measured: no clip or move script toggles it (B); the answer in-game is D.

### Q3. The effects

**Normal-move trails are afterimage trails on the `haver` bone, not `.eff` effect names;
the donor-specific slash effects live in `ef_miiswordsman.eff`, which a Gunner's environment
does not contain.**

- Which effect names the normal-move scripts request (decoded from
  `lua2cpp_miiswordsman.nro`, 2,101,248 B, `30aad5f5374b…`, addresses above and in
  `tables/acmd_calls.tsv`, 80,890 rows): `effect_attack11/12/13`, `effect_attacks3`,
  `effect_attackair*`, `effect_attackdash` etc. request **`haver`/`top` bone anchors,
  `AFTER_IMAGE4_ON_WORK`/`AFTER_IMAGE_OFF` and common `sys_*` names**
  (`sys_turn_smoke`, `sys_atk_smoke`, `sys_smash_flash`, …) - 45 distinct requested names in
  total across all scripts (`tables/effect_requests.tsv`). (B)
- Slash/counter/rapid effects requested by specials: `effect_speciallw1hit` /
  `effect_specialairlw1hit` request `tex_miiswordsman_sword03`+`04` and
  `miiswordsman_counter_*`; `effect_specialhi3` / `effect_specialairhi3` request
  `tex_miiswordsman_sword05`+`06`; `effect_specialairn3end*` request
  `miiswordsman_rapid_slash_*`. (B)
- Which file each lives in:
  - `ef_miiswordsman.eff` (workspace
    `gamedata/mii_customizer/P14-SWORD-FACTS/effect/fighter/miiswordsman/ef_miiswordsman.eff`,
    15,888,896 B, `6bcb258c7759…`) contains the donor names: of the 45 requested names,
    14 contain "miiswordsman" - **9 are substrings of this bank** (`miiswordsman_chakram_t`,
    `miiswordsman_counter_flash`, `miiswordsman_counter_success`, `miiswordsman_entry`,
    `miiswordsman_hensoku_flash`, `miiswordsman_hensoku_flash_s`,
    `miiswordsman_hensoku_hit`, `miiswordsman_reflect2`, `miiswordsman_rocket_ground`);
    `bg_miiswordsman_final` and the 4 `tex_miiswordsman_sword03..06` names are not; the bank
    contains 109 case-insensitive `MIISWORDSMAN_SWORD` matches and
    `EF_MIISWORDSMAN_SWORD00`. (B)
  - `ef_miigunner.eff` (20,034,240 B, `9f27743cf997…`) contains **0** case-insensitive
    `MIISWORDSMAN_SWORD` matches and none of the donor names (e.g. `miiswordsman_counter_flash`
    → donor yes / gunner no). (B)
  - Trail textures are **not** in any `.eff`: the 4 requested `tex_miiswordsman_sword0N`
    names are substrings of *neither* bank; the textures are 70 standalone files
    `effect/fighter/miiswordsman/trail/tex_miiswordsman_sword01..70.nutexb` (e.g. `01`
    176,816 B `8001eb546628…`, `70` 89,264 B `a48feb9175b3…`). The archive index contains
    **exactly 70** `tex_miiswordsman_sword*` paths, all under that one directory. (B)
  - `sys_*` names are substrings of neither bank, and the archive index contains **no**
    `effect/common/*.eff` at all (only `effect/fighter/*` and `effect/ui/*`) - where common
    effects resolve from is unmeasured (D).
- Bones: effect scripts attach to `haver` (71 scripts' requests include it), `top` (115),
  `handl`/`handr`; trail = afterimage work on `haver`. (B)
- Does a Mii Gunner's effect environment contain any of them? **No** - 0 donor names and 0
  `MIISWORDSMAN_SWORD` matches in `ef_miigunner.eff`; the 70 trail textures exist only under
  `effect/fighter/miiswordsman/`. (B)
- What decides which `.eff` a fighter can use: the workspace kb note
  `kb/findings/effect-ownership-of-donor-banks-and-per-slot-trails.md` (status `verified`,
  their tier B, measured with `mods/ssbu_mod_new/tools/effect_trail_inventory.py`): *only the
  requesting fighter's own `effect/fighter/<fighter>/` directory is searched, and inside it
  only `ef_<fighter>.eff` or `ef_<fighter>_c<slot>.eff` is accepted*; trail textures are
  identified by their internal NUTEXB footer name and renamed per slot by the One Slot
  Effects plugin (pinned upstream source named in that note). Archive evidence in line with
  it: every fighter's bank sits in its own `effect/fighter/<kind>/` directory (590,711-line
  index), and the sword trail folder exists only for `miiswordsman`. Whether a Gunner
  requesting donor names would fail *in this mod's setup* remains D (no run).

### Q4. The Gunner side

**The Gunner skeleton has every bone the sword and its effects use, with an identical
name list and parent chain; the only relevant rest difference is `HaveR`'s local
translation, and at rest the sword's box overlaps the arm cannon's box.**

- All four skeletons (`b_normalswordman_m/f`, `b_normalgunner_m/f` `model.nusktb`, 20,160 B
  each; `e0407f6169cc…`, `e0407f6169cc…`, `1d66b6d1cc4c…`, `43f13756fb0f…`) have **71 bones
  with identical names and identical parent indices**; **32 of 71** local rest transforms
  differ across the four skeletons (rule: the 5-decimal-rounded 4x4 local matrix is not
  identical in all four files; this includes gender asymmetries such as some finger bones).
  The right-arm chain
  `Trans→Rot→Hip→Waist→Bust→ClavicleR→ShoulderR→ArmR→HandR→HaveR` is identical
  everywhere. (B)
- Rest transforms on the chain: `ShoulderR`/`ArmR`/`HandR` locals are identical between the
  classes; **`HaveR` local translation differs**: Swordfighter
  `(0.995895, 0.01364, 0)` vs Gunner `(1.35, 0.15, 0)` (rotation part identical). World rest
  translation of `HaveR`: Swordfighter `(-6.200, 9.611, 0.000)` vs Gunner
  `(-6.554, 9.475, 0.000)`; `HandR` is `(-5.204, 9.625, 0.000)` on both. (B)
- Effect bone: effects attach to `haver` (lowercase hash `0x51a07c0e7`; the skeleton spells
  it `HaveR`) - the Gunner skeleton has that bone (index 16). Note the scripts' hitbox bone
  `top` (`0x31ed91fca`) exists in **no** sampled skeleton (the four Miis plus donkey,
  gamewatch, elight - 117/45/169 bones) and in no animation node set; how the engine
  resolves `top` is D. (B)
- Gunner right arm: `b_normalgunner_m/c00/model.numshb` (394,456 B, `416354380e98…`) has 3
  objects: `GamemodelShape` (6,081 vertex positions, `vertex_indices` 28,602, skinned to
  44 bones), `buckleShape` (153 positions / 648 index entries, skinned to `Hip`/`Waist`),
  **`gunShape` - the arm cannon: 1,597 vertex positions (`vertex_indices` 6,264),
  rigid-parented to `ArmR`, 0 bone influences**. Female equivalent has the same structure
  (`e63c36a1dcb6…`; gun 1,597 positions / 6,264 index entries). (B)
- Mesh visibility groups the Gunner model already has = the 3 groups in
  `model.numshexb` (336 B): `Gamemodel`, `buckle`, `gun` (spheres:
  gun `c=(2.9166,-0.0010,0.3313) r=2.7835` in gun-local space). The Swordfighter body has 6
  (male: `Gamemodel`, `miiswordsman_sheath_high`, `miiswordsman_sheath_low`, `MiiS_Sword`,
  `body_high`, `body_low`). (B)
- Intersection (rest pose only): placing the Swordfighter sword mesh under the *Gunner's*
  `HaveR` rest matrix gives AABB `[-8.106, 9.196, -1.651] .. [-4.987, 9.794, 9.686]`; the
  `gunShape` under `ArmR` gives `[-8.951, 8.182, -1.574] .. [-3.968, 11.794, 1.628]`. The
  boxes overlap on all three axes (per-axis intersection `3.12 / 0.597 / 3.202`); on the
  female pair the numbers are identical. A held sword at rest therefore sits inside the arm
  cannon's bounding box. Whether the *surfaces* intersect, and what happens in animated
  poses, is D (AABB ≠ surfaces, rest ≠ animation). (B)

### Q5. Ways a Gunner could get a sword model (comparison table, no recommendation)

Measured vs unknown for each route; "files per" = what the replacement granularity is
(measured from the archive index: model and effect paths are keyed by fighter kind **and**
costume slot, e.g. `fighter/miigunner/model/b_normalgunner_m/c00..c11/model.numshb` exists -
12 slots; two Gunners in one match share any file unless their costume slots differ, which
the game makes happen is D).

| | (a) extra mesh objects merged into the Gunner body model | (b) separate model attached at runtime (article/prop) | (c) held-item route (what the data suggests) |
|---|---|---|---|
| What is measured (B) | Sword is exactly this on the donor: a mesh object rigid-parented to `HaveR` inside `model.numshb` (Q1); Gunner skeleton has `HaveR` (Q4); Gunner `model.numshexb` already defines per-object groups `Gamemodel`/`buckle`/`gun`; vanilla per-object visibility exists: `VisibilityModule::set_int64(accessor, "sword", "sword_hide")` (1 site) and `set_whole` (4 sites) in the donor NRO | The donor fighter already spawns models at runtime: 20× `ArticleModule::generate_article`, 6× `shoot_exist` in its NRO; the game keeps article models in per-kind dirs (`fighter/miiswordsman/model/chakram/`, Gunner itself has `fullthrottle`, `grenadelauncher`, `groundbomb`, `miimissile`, `supermissile` under `fighter/miigunner/model/`); held-item swing machinery exists: motion kinds `item_sword_swing_1/3/4/dash` (motion list idx 376/377/378/380) whose registered game scripts (`0x106d9009da`@`0x45a84`, `0x10839e68f6`@`0x45aa0`, `0x101dfafd55`@`0x45abc`, `0x13ac2fdc4c`@`0x45ad8`) call `ItemModule::set_have_item_action` (12 scripts total do) | Base game ships held-sword items: `item/beamsword/`, `item/killsword/`, `item/thundersword/` (model+param in archive index); `ItemModule::set_have_item_visibility` has 46 sites in 43 donor scripts |
| Other-mod reference (C; their tier) | adding a mesh needs all four model files consistent + bounding sphere + visibility track (`mods/ssbu_mod_new/handbook/08_visibility_models.md:9`, their A); per-state mesh names come from `param_visibility_data_body` (`…/08_visibility_models.md:5`, their B) | `clone_weapon` from the mod plugin works (`mods/ssbu_mod_new/handbook/07_articles.md:7`, their A); article table is per fighter kind and article models must ship for all 8 slots (`…/07_articles.md:3,5`, their B/A); attach chain for their eflame sword: owner `HaveR` → article's own `HaveR` → `Sword1`, and *an article-level visibility call does not make a mesh appear - the mesh's own visibility track wins* (`…/08_visibility_models.md:11,12`, their B); `ArticleModule::set_visibility_whole` call sites e.g. `mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/attack_air_f.rs:69,192,277,324` | (no reference mod claim found for items) |
| Files added/replaced | `fighter/miigunner/model/b_normalgunner_{m,f}/c00..c11/model.numshb` (+ `model.numshexb` group/bounding data, `model.numatb` if materials added; `model.nusktb` only if bones change) = up to 24 slots of numshb; plus a visibility state definition (`param_visibility_data_body` lives in the per-kind param files) | a new model directory (like `fighter/miigunner/model/<article>/c00..`), an article-table/agent registration (in `main`, per kind), plus the visibility ACMD or clip tracks | item model files under `item/<name>/` (already exist for the sword items) or a copied/new item kind |
| Replacement granularity | per (fighter kind, costume slot): both Gunners of the same slot share the file; the *switch* must then be per battle object at runtime | per fighter kind (article table is per kind; models load at fighter init per `…/07_articles.md:5`) - shared by all Gunners; per-object switching at runtime | per item instance (items are individual objects) |
| Runtime toggle call that is per fighter object | `VisibilityModule::set_int64(module_accessor, group, state)` - measured once in the donor NRO (`bl 0xd9fdc`); `VisibilityModule::set_whole(module_accessor, bool)` measured 4×; both take the object's `BattleObjectModuleAccessor` → per object. What each selects visually is D | `ArticleModule::set_visibility_whole` (other mod's call sites above) **but** the mesh's own visibility track in the clip that is playing wins (`…/08_visibility_models.md:11`) → toggling a merged mesh needs a clip track or a `VisibilityModule`-style group, not only the article call | `ItemModule::set_have_item_visibility(module_accessor, bool, …)` (46 measured sites) |
| Unknown (D) | whether a merged mesh can be kept out of view reliably between moves; how `sword_hide` maps to meshes; per-slot authoring of 24 files | whether the mod's clone route (A on their setup) works for a Mii Gunner in this mod; pose/scale of an attached article on Gunner's `HaveR`; the two-Gunner difference | whether held-item routing can be restricted to a move window without per-frame forcing (project rule forbids forced per-frame status changes) |

No recommendation is made; this is a comparison only.

### Q6. Swordfighter moves that reference the sword

Method: `tables/acmd_scripts.tsv` (1,061 registrations, 603 named) + `tables/acmd_calls.tsv`
(80,890 rows) + `tables/motion_scripts.tsv` (765 motion-list entries) from
`lua2cpp_miiswordsman.nro`; a script counts as "referencing the sword" if it constructs a
have-bone hash (`haver`/`havel`/`HaveR`/`HaveL`), requests a name containing "sword"
(`miiswordsman_*`, `tex_miiswordsman_sword*`) as an EFFECT-family argument, or contains a
`VisibilityModule`/have-item visibility call. Names were mapped to motion kinds by the same
candidate derivation as the motion list (kind names, anim stems, side-stripped stems).
Result: **216 classified scripts (161 named + 55 hex-only), of which 46 carry a visibility
call** (`tables/sword_scripts.tsv`, `tables/family_counts.tsv`). (B)

| group | kinds | classified scripts | with sword bone | with effect request | with visibility |
|---|---|---|---|---|---|
| jab (`attack_11/12/13`) | 3 | 6 | 6 | 3 | 0 |
| tilt (`attack_s3_s`, `attack_hi3`, `attack_lw3`) | 3 | 5 | 5 | 3 | 0 |
| aerial | 5 | 11 | 11 | 5 | 1 |
| smash | 4 | 5 | 3 | 3 | 2 |
| other normal (`attack_dash`) | 1 | 2 | 2 | 1 | 0 |
| special | 50 | 83 | 49 | 41 | 29 |
| other/state (appeal, entry, dash, final, …) | 46 | 49 | 20 | 46 | 3 |

Caveats that a later design must carry:
- The classified set contains only scripts that reference the sword by the rule above;
  `game_attack11/12/13` and `game_attacks3` are **not** in it, because their ATTACK calls
  pass `hash40("top")`, not a have-bone hash (Q2). So the jab/tilt *hitboxes* do not ride
  `haver` on the donor - **this refutes P11-MOVE-PLAN's unverified "jab bone `haver`"
  claim** (its coordinator banner flagged it as unverified). Which bone `top` resolves to is
  D (it exists in no skeleton we sampled). (B)
- Scripts whose names stayed hex (55) were classified but cannot be attributed to a move
  group; per-group counts therefore only cover the 161 named scripts. (B)
- The 46 have-item-visibility scripts drive *items*, and the 2 `VisibilityModule` named
  scripts are `expression_entryr/l`; per-move sword visibility does not exist (Q2). (B)

### Q7. The closure list: what "Gunner A shows the Swordfighter sword with its trail during a borrowed sword move while Gunner B does not" depends on

Files (all B - hashed and re-read by the check unless noted):

1. `gamedata/mii_customizer/P14-SWORD-FACTS/fighter/miiswordsman/model/b_normalswordman_{m,f}/c00/model.numshb` - sword + sheath geometry (`b22c52a0ba2a…` / `dc332f9c1365…`). (B)
2. Same dirs: `model.nusktb` (bone `HaveR` etc., `e0407f6169cc…`), `model.numshexb` (groups), `model.numatb` + 6 textures (materials the sword renders with). (B)
3. `gamedata/mii_customizer/P14-SWORD-FACTS/fighter/miigunner/model/b_normalgunner_{m,f}/c00/model.numshb` (+`nusktb`, `numshexb`, `numatb`, textures) - the file option (a) would replace; per-slot copies `c01..c11` exist for both genders (archive index, B) - 24 numshb paths total. (B)
4. Donor animation clips `fighter/miiswordsman/motion/body/c00/*.nuanmb` (96 extracted) - prove no clip toggles sword visibility and that `HaveR` is animated. Borrowed clips would run on Gunner's rig - visual result D. (B)
5. `fighter/miiswordsman/motion/body/c00/motion_list.bin` (45,696 B, `9692b79ea80d…`) - motion kind → game-script hash mapping (765 entries). (B)
6. `prebuilt;/nro/release/lua2cpp_miiswordsman.nro` (2,101,248 B, `30aad5f5374b…`) - all game/effect/expression scripts: trails on `haver`, `expression_lose` sword visibility, `top` hitbox bones. (B)
7. `prebuilt;/nro/release/lua2cpp_miigunner.nro` (`64ec160d90eb…`) and `lua2cpp_common.nro` (`43876f961a80…`) - contain 0 `sword`/`sword_hide` visibility words (negative evidence). (B)
8. `effect/fighter/miiswordsman/ef_miiswordsman.eff` (`6bcb258c7759…`) - donor effect bank. (B)
9. `effect/fighter/miiswordsman/trail/tex_miiswordsman_sword01..70.nutexb` (70 files; `01` `8001eb546628…`). (B)
10. `effect/fighter/miigunner/ef_miigunner.eff` (`9f27743cf997…`) - lacks every donor name. (B)
11. `mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv` (93,034 lines) - hash40 label source for every name cited (`0x031ed91fca,top`, `0x0ab4f18a85,sword_hide`, …). (B)
12. `mods/ssbu_mod_new/dumps/decoded/arc_files.tsv` (590,711 lines) - archive index proving paths, slots and what does not exist. (B)
13. Option-dependent additions: (a) edited Gunner `model.numshb/numshexb/numatb` per slot; (b) a new `fighter/miigunner/model/<article>/…` directory + article registration; (c) `item/<name>/…` files. Existence of the *patterns* is B; the new files themselves do not exist yet (D).

Runtime facts:

R1. Sword rides bone `HaveR`; Gunner has `HaveR` (identical chain; local offset differs `(0.9959,0.0136,0)` vs `(1.35,0.15,0)`). (B)
R2. Per-object visibility lever exists: `VisibilityModule::set_int64(accessor, group, state)` (measured once, `bl 0xd9fdc`) / `set_whole` (4 sites); both are per battle-object. What `sword_hide` draws = D.
R3. No clip has a sword visibility node; per-move show/hide through clip tracks would require new visibility nodes/tracks (feasibility D).
R4. Effect-ownership rule: only the requesting fighter's own `effect/fighter/<kind>/` dir is searched (`kb/findings/effect-ownership-of-donor-banks-and-per-slot-trails.md`, their B); applying it to a Gunner requesting donor effects = D.
R5. Trail textures resolve by internal NUTEXB footer name, per-slot renamed by One Slot Effects (same kb note, their B/C). D in this mod's setup.
R6. Normal-move trails are `AFTER_IMAGE4_ON_WORK` on `haver` driven by `effect_*` scripts (B); that a borrowed `effect_*` script would run on a Gunner object is D.
R7. Rest-pose AABB of sword vs arm cannon overlaps (B); in-animation intersection = D.
R8. Files are per (kind, slot) (B); that two Gunners in one match can differ only via slot/runtime state = D.
R9. Article route mechanics (attach chain, track-wins rule, `clone_weapon`, per-kind table) = C from `mods/ssbu_mod_new` `file:line` (their A/B), untested here.
R10. Held-item levers: `set_have_item_visibility` (46 sites, B), `set_have_item_action` (12 sites, B), sword items exist in archive (B); their behaviour on a Gunner = D.

---

## Method

- Extraction (workspace `gamedata/mii_customizer/P14-SWORD-FACTS/`, 265 files, logged in
  `scratch/2026-10-07_P14-SWORD-FACTS/extract_log*.txt`): body models (4), 12
  `b_normalswordman_m` colour slots, 8 alternate-costume `model.numshb` samples, motion
  clips (attack/special/dash, 96), 70 trail textures, both `.eff` banks, all three
  `lua2cpp_*.nro`, `motion_list.bin`, both Mii Gunner sample clips. Shared `tools/arc-extract`
  fails on `prebuilt:/` paths (Windows error 123); extraction used the patched build
  `mods/ssbu_mod_new/builds/.cache/dk_cargo/arc-target/release/arc-extract.exe` (exact paths
  need no index; folder args needed literal expansion).
- Scripts (all in `scratch/2026-10-07_P14-SWORD-FACTS/`, outputs `*_run.txt`):
  `q1_mesh_tables.py` (mesh/material/costume tables), `q2_vis_scan.py` (96 clips' groups +
  whole-NRO movz/movk word scan), `q_acmd_scan.py` (registration + call scan of
  `lua2cpp_miiswordsman.nro` with thunk resolution and register-built hash40 capture),
  `q3_q6_analyze.py` (effect requests, bank presence, classification, family counts),
  `q4_rest_diff.py` (rest transforms), `q4_geometry.py` (meshex groups + rest AABB),
  `q4_sanity.py` (matrix-convention validation), `dbg_attack_args.py`/`dbg_window.py`
  (ATTACK argument windows), `dbg_setint64.py` (set_int64 argument order),
  `gen_pins.py` (check pins), `eff_strings.py`, `anim_introspect.py`, `nro_strings.py`.
- Disassembly: `mods/ssbu_mod_new` cached `nro_flatten`/`nro_util` + capstone (their tools,
  read-only). Tables: 16 TSVs under
  `gamedata/mii_customizer/P14-SWORD-FACTS/tables/` (file_inventory 265, mesh_objects 21,
  materials 8, skeleton_bones 284, costume_sword_objects 46, rest_transform_diff 71,
  rest_aabb 6, meshex_groups 17, acmd_scripts 1061, acmd_calls 80890, motion_scripts 765,
  effect_requests 45, sword_scripts 216, visibility_sites 51, family_counts 7; the 16th
  file, `sword_effects.tsv` (139 rows), is the superseded v1 constructed-name list, kept
  for traceability).
- Matrix convention (row-major, translation in row 3, `world = local @ parent`, row-vector
  `v @ M`) was validated two ways: world deltas preserve local translation magnitudes
  (`HandR→HaveR = (-0.996,-0.014,0)` vs local `(0.9959,0.0136,0)`, same for Gunner
  `(1.35,0.15,0)`), and the sword grip (raw local y≈0) lands exactly at `HandR`'s world
  position after transform. (B)
- Check: `evidence/P14-SWORD-FACTS/check_p14_sword_facts.py` re-hashes all 265 inventory
  files, pins key file hashes, instruction words (movz/movk triples and `bl` targets for
  `sword`/`sword_hide`/`top`/`collision_attr_cutup`/`set_int64`), re-derives mesh/bone/
  meshex/AABB/animation/effect-bank/archive-index facts from the game files, cross-checks
  the TSV tables and report anchors; `--neg` holds negative controls, `--selftest` runs the
  helpers in-process.

## Limitations

- No emulator, no console: everything about what the game *shows* or *does* is D, including
  whether the vanilla sword is ever hidden, what `sword_hide` selects, whether donor effects
  resolve on a Gunner, and whether a sword and the arm cannon visibly intersect in motion.
- Object→material binding inside `model.numshb` could not be read with `ssbh_data_py` 0.9.1
  (no attribute), so "which material the sword uses" stays D; the two candidate materials
  and their textures are enumerated (B).
- The word-triple scan only detects hash40 constants built as `movz+movk+movk` in three
  consecutive instructions; a hash built any other way would be missed (none observed in
  the sampled sites).
- 55 classified scripts have no resolvable name; per-move-group counts cover the 161 named
  scripts only.
- AABBs are axis-aligned boxes at the rest pose sampled every 7th vertex; they neither
  prove surface intersection nor say anything about animated poses.
- `research/P12-FTILT-FACTS.md` and `research/P12-SCRIPT-ROUTE.md` were unfinished
  skeletons at task start and were not used as inputs.
- Workspace rule `code_search` (ripgrep) is broken on this host (ENOENT); all searches used
  `grep`/python. This is an environment note; it could not be filed in `kb/` because this
  task's write scope is exclusive to the four P14 paths.
- Knowledge placement: mod facts belong in the mod repo's handbook and environment facts in
  `kb/`, but this task's exclusive-write scope forbade writing there; this report is the
  single record for P14.

## Task Summary

- **Task ID**: `P14-SWORD-FACTS`
- **Status**: DONE (offline facts; in-game behaviour correctly left as D)
- **Changed files**:
  - `research/P14-SWORD-FACTS.md` (this report)
  - `evidence/P14-SWORD-FACTS/check_p14_sword_facts.py`
  - `scratch/2026-10-07_P14-SWORD-FACTS/` (scripts, run outputs, extraction logs)
  - workspace `gamedata/mii_customizer/P14-SWORD-FACTS/` (265 extracted files + 15 tables)
- **Checks run**: `evidence/P14-SWORD-FACTS/check_p14_sword_facts.py` -
  clean run: 608 checks, 0 failures, exit 0 (11 groups: inventory 266, pinned 149,
  instructions 34, mesh 19, bones 37, effects 21, arc 16, tables 29, animations 7,
  labels 4, report 26); `--neg`: 8 negative controls, 8/8 detected, exit 1;
  `--selftest`: 25 helper checks OK, exit 0. The clean run was repeated after this
  last report edit and its output is pasted in the final message.
- **Open questions**:
  1. What does `set_int64("sword","sword_hide")` actually draw, and does any game state
     besides `expression_lose` reach it? (needs a console/emulator observation)
  2. Which material the `MiiS_Sword_VIS_O_OBJShape` object uses (needs an ssbh reader that
     exposes the binding, or a manual numshb parse).
  3. How the ATTACK bone argument `top` resolves on skeletons that contain no `top` bone
     (needs `main`'s AttackModule/BoneModule decompilation - out of this task's scope).
  4. Whether borrowed donor `effect_*` scripts would find `ef_miiswordsman.eff` names when
     running as `miigunner` (the kb ownership rule says no; confirming needs a run).
  5. Whether two Gunners in one match differ only by costume slot files or also need
     runtime state (design input; game behaviour D).
