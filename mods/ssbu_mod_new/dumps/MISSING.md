# Files agents need that are not in dumps/

**2026-10-02: check `data.arc` first.** Any base-game file can now be extracted from the local
13.0.4 `data.arc` with the workspace tool `tools/arc-extract` (see its README at the workspace
root), into `gamedata/ssbu-13.0.4/files/`. Only list a file here if that tool reports `MISSING`.
Already extracted there: `effect/fighter/eflame/ef_eflame.eff`, `fighter/brave/param/*.prc`
(the ArcExplorer export's `fighter/brave/param/` folder is empty).

Format: exact ARC path - why - who asked - date. Known open item from the old workspace:

T-0050 rechecked 2026-10-02: original eflame bank and converter/source absent
inside lab, including ignored builds and gamedata. Local data.arc exists, but no
in-lab individual ARC reader. Export the exact eflame path to lab gamedata and
configure dumps.arc there. Configured external export not accessed. No package.

## 2026-10-01 (T-0033) - Pyra's own effect bank: `effect/fighter/eflame/ef_eflame.eff`

Needed because Little Mac's forward-smash emitters (`LITTLEMAC_ATTACK_LINE`,
`LITTLEMAC_ATTACK_ARC`) have to be merged into **Pyra's** bank to be drawable at all: only a
fighter's own `effect/fighter/<fighter>/ef_<fighter>.eff` (or the one-slot
`ef_<fighter>_c<slot>.eff`) is loaded by that fighter's effect loader. Today the donor bank is
shipped under `effect/fighter/littlemac/`, so an eflame fighter never resolves those names.
Analysis and the fix: `refs/littlemac_attack_s4/T-0033/FIST_TRAIL_FINDING.md`.

Same request covers the Cloud trail work: `effect/fighter/eflame/trail/` (the vanilla trail
folder) is useful as the byte reference for the per-slot trail cleanup in
`refs/cloud_attack_air_f/T-0033/CLOUD_TRAIL_FINDING.md`.

Pull read-only with arc-network when the console is up; `tools/fetch_arc_files.py` needs a new
set covering `effect/fighter/eflame/` (no set covers it today). Also needed by that path and
still absent: `builds/.cache/hero_effect_converter/bin/EffectConverter.exe`
(`paths.toml toolchain.hero_effect_converter`), without which no effect-bank merge can run here.

## 2026-09-30 (Buffy) - Little Mac forward smash: RESOLVED, and one thing that is NOT missing

**Resolved the same session, by extraction rather than by request.** `dumps/arc/fighter/littlemac/`
exists on disk but holds **0 of its 4290 indexed files** (index-only, like Chrom's sword
article was), and `dumps/arc/effect/fighter/littlemac/` was empty too. The console was up
with arc-network answering on 43022, so all 18 files came off it read-only into
`refs/littlemac_attack_s4/arc/`, 0 failures:

- `fighter/littlemac/motion/body/c00/motion_list.bin` (45208 B, 763 entries) and the four
  forward-smash clips `c03attacks4s`, `c03attacks4charge`, `c03attacks4hi`, `c03attacks4lw`
- `fighter/littlemac/model/body/c00/model.nusktb` (50 bones)
- `fighter/littlemac/param/{vl,expression_vl}.prc`, `fighter/littlemac/ai/param/attack_{data,list}_param.prc`
- `effect/fighter/littlemac/ef_littlemac.eff` (13,795,840 B, 44 emitters)
- `sound/bank/fighter/se_littlemac_c00.*` (74 tones), `sound/bank/fighter_voice/vc_littlemac_c00.*` (58 tones)
- `sound/sequence/fighter/littlemac.sqb`

Per-file sha256 in `refs/littlemac_attack_s4/extraction.json`, provenance and findings in
`refs/littlemac_attack_s4/SOURCE.json`, re-verify with
`toolchains/py312/python.exe tools/fetch_arc_files.py --set littlemac_attack_s4 --check`.

**Nothing further is needed for the forward smash, and one part of the request cannot be
supplied by any dump.** The up/down-angled forward smash is not a missing file: Pyra, Mythra
and G&W have no `attack_s4_hi` / `attack_s4_lw` motion kinds and no such status, only 7 of 72
fighters lack the angled pair (ours are three of them), the const table has zero
`S4_HI`/`S4_LW` entries, and eflame's status table registers exactly one smash status. So
there is no ARC path to request - it needs a native input-to-status hook, which is a
user-authorization question, not a dump. Details and the ready-to-use clips:
`refs/littlemac_attack_s4/SOURCE.json` -> `blocked_variants`.

## Requested 2026-09-30 - Hero side-B article motion lists (Codex) - resolved

All 16 lists for spark/lightning c00..c07 were extracted read-only on 2026-09-30
after the user's "you can dump now" authorization, with zero failures. They are
pinned separately in `refs/brave_special_s/article_motions/arc/`; provenance and
full hashes: `refs/brave_special_s/article_motions/{SOURCE,extraction}.json`.
The six paths below were the original request; remaining slots were included
for the cloned article's complete costume coverage. Dumps were not modified.

- `fighter/brave/motion/spark/c00/motion_list.bin`
- `fighter/brave/motion/spark/c06/motion_list.bin`
- `fighter/brave/motion/spark/c07/motion_list.bin`
- `fighter/brave/motion/lightning/c00/motion_list.bin`
- `fighter/brave/motion/lightning/c06/motion_list.bin`
- `fighter/brave/motion/lightning/c07/motion_list.bin`

## Earlier requests

- `sound/sequence/fighter/brave.sqb` - **resolved 2026-09-30** by read-only arc-network extraction into `refs/brave_special_n/sound/arc/sound/sequence/fighter/brave.sqb`, 1392 bytes, sha256 `46167a0cec8c8452d527b25dd5afafa49fe8162341fc437e53a9c0041fafc3fa`; provenance `refs/brave_special_n/sound/extraction.json`. Used for original voice sequence membership and weights.

- `fighter/brave/motion/body/c00/motion_list.bin` - Hero neutral-B donor entries, animation mapping, blend/flags/cancel timing for Mythra c06/c07 - Codex - 2026-09-30; **resolved** by live read-only extraction into `refs/brave_special_n/motion_list.bin`, sha256 `300bb59a9ff9a5cec74f6f315a93ca5673f96a14ebbe871e932f2dc37579888f` (808 entries); provenance `refs/brave_special_n/extraction.json`.

- Old standalone-clone sound banks (not dependencies of the active reskin; clone packs still alias them):
  - `sound/bank/fighter/se_elight_c00.nus3audio`
  - `sound/bank/fighter/se_elight_c00.nus3bank`
  - `sound/bank/fighter/se_elight_c00.tonelabel`
  - `sound/bank/fighter/se_gamewatch_c00.nus3audio`
  - `sound/bank/fighter/se_gamewatch_c00.nus3bank`
  - `sound/bank/fighter/se_gamewatch_c00.tonelabel`
  - `sound/bank/fighter_voice/vc_elight_c00.nus3audio`
  - `sound/bank/fighter_voice/vc_elight_c00.nus3bank`
  - `sound/bank/fighter_voice/vc_elight_c00.tonelabel`
  - `sound/bank/fighter_voice/vc_elight_cheer_c00.nus3audio`
  - `sound/bank/fighter_voice/vc_elight_cheer_c00.nus3bank`
  - `sound/bank/fighter_voice/vc_elight_cheer_c00.tonelabel`
  - `sound/bank/fighter_voice/vc_gamewatch_c00.nus3audio`
  - `sound/bank/fighter_voice/vc_gamewatch_c00.nus3bank`
  - `sound/bank/fighter_voice/vc_gamewatch_c00.tonelabel`
  - `sound/bank/fighter_voice/vc_gamewatch_cheer_c00.nus3audio`
  - `sound/bank/fighter_voice/vc_gamewatch_cheer_c00.nus3bank`
  - `sound/bank/fighter_voice/vc_gamewatch_cheer_c00.tonelabel`
- G&W sounds (67 of `se_gamewatch_*` are unreachable from eflame): need a plan for copying banks; see `src/pgwr/sound-inventory.json` and `handbook/` gap list.
- `fighter/cloud/motion/body/c00/motion_list.bin` - Cloud forward air / landing cancel frames and flags - live dumped via arc-network on 2026-09-29, stored in `refs/cloud_attack_air_f/motion_list.bin` (sha256 `3e94783c769e4a02f97427f561db1c3ce2b4236ce0ecd6dfaa77697a6dc34623`).
- `fighter/cloud/param/vl.prc` - Cloud fighter parameters - live dumped via arc-network on 2026-09-29, stored in `refs/cloud_attack_air_f/vl.prc` (sha256 `596bae5a0c7ac2f957d2170a2d3eb5b4766119c304ddf785046289bd0f375db5`).
- `fighter/cloud/model/body/c00/model.nusktb` - Cloud skeleton hierarchy - live dumped via arc-network on 2026-09-29, stored in `refs/cloud_attack_air_f/model.nusktb` (sha256 `064da9170fe890822613cb746069f800bf44fa0776f7162e40598096270971ac`).

## Requested 2026-09-30 (Buffy) - Chrom's jab / Falchion on the G&W costume

**Resolved 2026-09-30, same session.** The console was up with Smash running and arc-network answering on 43022, so
all of it was extracted live rather than requested: **139 files, 0 failures**, into `refs/chrom_jab/arc/` mirroring
the ARC tree. Per-file sha256 and sizes are in `refs/chrom_jab/extraction.json`, provenance in
`refs/chrom_jab/SOURCE.json`, and the tool is reusable - `tools/fetch_arc_files.py` (new; `--check` re-verifies an
existing extraction without touching the console). Post-extraction findings worth knowing: the article skeleton is
only `HaveR -> Sword` and its single mesh is skinned to `Sword`; the blade runs along +z with its tip at 10.908
(the Aegis blade's tip is 11.39); and every sword file is byte-identical across all eight costumes. The text below
is kept as the record of what was asked for.

Needed only if the jab shows Chrom's own Falchion instead of the Aegis esword (see `projects/pgwr/PLAN_CHROM_JAB.md`).
Both directories exist in `dumps/arc/` but are **empty**, and `dumps/decoded/arc_files.tsv` lists exactly 17 files per
costume for all eight costumes with identical names (136 total), so this request is exact rather than approximate:

- `fighter/chrom/model/sword/c00..c07/` - 14 files per costume: `model.numdlb`, `model.numshb`,
  `model.numshexb`, `model.nusktb`, `model.nusrcmdlb`, `model.nuhlpb`, `model.numatb`, `model.xmb`,
  `dark_model.numatb`, `light_model.numatb`, `metamon_model.numatb`, `met_chrom_001_col.nutexb`,
  `met_chrom_001_nor.nutexb`, `met_chrom_001_prm.nutexb`
- `fighter/chrom/motion/sword/c00..c07/` - 3 files per costume: `motion_list.bin`, `j00entryl.nuanmb`,
  `j00entryr.nuanmb`

Why this article and not the Aegis sword: Chrom's sword has **no pose clips**, only the two entry animations, so its
transform comes from the body bone it hangs off. The Aegis article owns its pose in its own clips (graveyard
R-20/R-21).

Cheap extras, same run:

- `fighter/chrom/model/body/c00/model.nusktb` - the donor skeleton, to place `sword1` and to check the graft; Cloud's
  was pinned into `refs/cloud_attack_air_f/` for exactly this reason.
- `fighter/chrom/param/vl.prc`, `fighter/chrom/param/expression_vl.prc` - `dumps/arc/fighter/chrom/param/` is empty.
  Not needed for the jab (its hitboxes are inline in the ACMD) but wanted for any further Chrom move.

Not requested:

- `sound/bank/fighter/se_chrom.*` (27 entries in the index, none dumped). The convention is to substitute the
  recipient's own SE (`se_eflame_swing_s01`), so the bank is only needed if Chrom's own swing sound is wanted.
- Anything for the jab's trail: `dumps/arc/effect/fighter/chrom/` already holds `ef_chrom.eff` and
  `trail/tex_chrom_sword1.nutexb` + `trail/tex_chrom_sword2.nutexb`, the exact pair his `AFTER_IMAGE4_ON_arg29` names.
- Status/ACMD native code: `dumps/arc/prebuilt/nro/release/lua2cpp_chrom.nro` and `lua2cpp_eflame.nro` are already
there (Ghidra input if the jab's chain flags ever need reading rather than inferring).

## Requested 2026-09-30 (Buffy) - Hero side-B (SPECIAL_S) for Mythra c06/c07, no mana system

**Resolved 2026-09-30 (extracted by Claude, console up).** All **184 files** (A 136 + B 26 + C 18 + D 4), 0 failures, into
`refs/brave_special_s/arc/`; per-file sha256 in `refs/brave_special_s/extraction.json`, provenance `SOURCE.json`,
re-verify with `tools/fetch_arc_files.py --set brave_special_s --check`. Byte comparisons run on the result (B):
the sword article (`model/blue` 14 files, `motion/blue` 3 files) is **identical across c00-c07**; the 24 c06/c07
`d01special(air)s*` clips are **identical to c00's**; the c06 and c07 body `motion_list.bin` are **identical to the pinned
c00 list** (`refs/brave_special_n/motion_list.bin`); `swingblend/scharge/update/ik/flip.prc` are identical to c00, but
**`swing.prc` differs** per costume, and the c06/c07 **skeletons differ from c00** (bytes; the bone set was not compared).
The request text below is kept as the record.

**Scope change 2026-09-30 (user): Mythra keeps her OWN sword. Hero's sword article is not used.** So section A's
`fighter/brave/{model,motion}/blue` files are extracted but **not consumed** - they stay pinned as evidence and are
not a dependency of the port. Nothing needs re-dumping for this change; the port simply drops A from its closure.
What replaces A is already in `dumps/` and needs no extraction:

- Mythra's blade is her own `FIGHTER_ELIGHT_GENERATE_ARTICLE_ESWORD` article (`fighter/elight/model/esword/c06,c07`,
  complete on disk; `lightsword_VIS_O_OBJShape` + `lightsword_lowShape`, skeleton `Root -> HaveR -> Sword1`).
  Her body model carries **no** sword mesh (0 sword-named shapes in `model/body/c06/model.numdlb`), so her sword is
  the article and always was.
- Hero's is the opposite: `brave_sword_VIS_O_OBJShape` is inside his **body** model
  (`fighter/brave/model/body/c00/model.numdlb`), on a body `Sword1` bone. That asymmetry is why A existed and why
  dropping it is a real simplification, not a shortcut.
- Both fighters name the trail bone `sword1`, so the donor's `AFTER_IMAGE4_ON_arg29` calls retarget by name onto her
  article bone unchanged. Hero's side-B draws `tex_brave_sword1`/`tex_brave_sword2`; Mythra's own five
  (`tex_elight_sword1..5.nutexb`) are already in `dumps/arc/effect/fighter/elight/trail/` and are what her existing
  attacks use with the identical macro shape (`tex_elight_sword1`+`sword2`, same arg29 signature). Her c06/c07 trail
  banks are already rebuilt and routed by `one_slot_effects` per `src/pgwr/COLOR_THEMES.md`.
- Opening/closing her blade reuses her own `WEAPON_ELIGHT_ESWORD_MOTION_PART_SET_KIND_OPEM_CLOSE` `to_open`/`to_close`
  partials, which her current `SpecialSStart.txt`/`SpecialSEnd.txt` already call - the same route the 0.9x esword
  fair and the Chrom jab take (`src/pgwr/tools/build_esword_pose.py`, `plugin/src/mythra/attack_air_hi.rs`).

Consequence for the trail: Hero's side-B numbers (`tex_brave_sword*`, trail tip, `1.4` width, `-90` roll) become
*donor* values against *her* textures. Her blade is a different length from his, so the trail tip is **not** a
donor constant - it must be derived per blade the way `chrom_jab.rs` derives `JAB_TRAIL_TIP` from Mythra's 14.5,
or the ribbon will detach from the hilt. That is a measured value, not a copy.

Scope: Hero's side-B sword slashes (`SPECIAL_S`, clips `d01specials*` / `d01specialairs*`) on Mythra `elight`
c06/c07. **The Special-Move gauge (mana) system is deliberately excluded** - no charged levels, no
`param_special_s` mana price/failure branches, exactly as the neutral-B port dropped mana. Everything below is
the uncharged slashes plus the sword article they draw. Donor = `brave`; sword article = Hero's `BLUE` article
(`FIGHTER_BRAVE_GENERATE_ARTICLE_BLUE`, i.e. `fighter/brave/model/blue` + `motion/blue`).

`dumps/arc/fighter/brave/` holds 275 of the 4102 files `dumps/decoded/arc_files.tsv` lists for Hero
(`comm` diff, 3827 missing). Almost all of that is costume c01-c07 body model/motion we do not need; the list
below is the exact side-B closure: **164 required files** (A 120 + B 26 + C 18), plus 20 optional extras
(16 appeal clips in A, 4 in D). Everything else side-B needs is already in `dumps/`. **After the scope change the
live closure is B 26 + C 18 + D 4 = 48 files** (and B/C are byte-identical to c00's per the comparisons above, so
c00's already-dumped copies may serve as the donor, subject to that being confirmed rather than assumed).

### A. Hero sword article, all eight costumes - 136 files, 120 required (nothing on disk; the `blue` dirs are empty)

**SUPERSEDED 2026-09-30 (user): not consumed - Mythra uses her own sword.** Extracted and pinned anyway; see the
scope change above. Kept as the record of what was asked and of the body-mesh-vs-article asymmetry.

`fighter/brave/model/blue/c00..c07/` - 14 files per costume (Byleth-sword model; `model.numdlb`, `model.numshb`,
`model.numshexb`, `model.nusktb`, `model.numatb`, `model.nusrcmdlb`, `model.nuhlpb`, `model.xmb`,
`dark_model.numatb`, `light_model.numatb`, `metamon_model.numatb`, `def_blue_001_{col,nor,prm}.nutexb`).
`fighter/brave/motion/blue/c00..c07/motion_list.bin` - 8 files, the article's own motion list.
`fighter/brave/motion/blue/c00..c07/j01appeallwl.nuanmb` + `j01appeallwr.nuanmb` - 16 files, cheap with the rest.

Why all eight, not just c06/c07: rule 17, the mod owns what it uses, and the neutral-B port cloned its fireball
for all eight slots and declared each in `config.json`. Same shape here. c00 is the reference; c06/c07 are the
slots Mythra actually wears.
Also settles, as tier B: whether Hero's sword model bytes are identical across the eight costumes (if they are,
one set + eight declarations is provably enough).

### B. Hero body motion, target costumes - 26 files

- `fighter/brave/motion/body/c06/` and `c07/`: `d01specials1.nuanmb`, `d01specials2.nuanmb`, `d01specials3.nuanmb`,
  `d01specials32.nuanmb`, `d01specialshold.nuanmb`, `d01specialsstart.nuanmb`,
  `d01specialairs1.nuanmb`, `d01specialairs2.nuanmb`, `d01specialairs3.nuanmb`, `d01specialairs32.nuanmb`,
  `d01specialairshold.nuanmb`, `d01specialairsstart.nuanmb` - 24 files.
  **c00's twelve are already on disk** (`dumps/arc/fighter/brave/motion/body/c00/`, 137 files), so c00 needs nothing.
- `fighter/brave/motion/body/c06/motion_list.bin`, `c07/motion_list.bin` - 2 files.
  c00's is already pinned: `refs/brave_special_n/motion_list.bin`, 808 entries, sha256 `300bb59a9ff9a5cec…`.
  The pinned copy is c00's only; the c06/c07 lists are separate files and are not derivable from it.

Why c06/c07 clips at all when c00's exist: the clips are per-costume files and their bone tracks are what get
retargeted onto Mythra's skeleton; using the c06/c07 donors keeps donor timing/flags identical to the costume
being replaced. If the c06/c07 clips turn out byte-identical to c00's, that is a measured result, not an assumption.

### C. Hero body `.prc` trail/blend params - 18 files

`fighter/brave/motion/body/c00/`, `c06/`, `c07/`: `swing.prc`, `swingblend.prc`, `scharge.prc`, `update.prc`,
`ik.prc`, `flip.prc` - 6 files x 3 costumes. **None are on disk** for any Hero costume.

`swing.prc` / `swingblend.prc` are what make the blade draw its ribbon at all; `scharge.prc` covers the charged
look. Mythra c06 already has its own six (`dumps/arc/fighter/elight/motion/body/c06/`), so this is a like-for-like
donor swap rather than a new mechanism - but the donor's own values are the whole point, and they are unreadable
without these files.

### D. Cheap extras, same run

- `fighter/brave/model/body/c06/model.nusktb`, `c07/model.nusktb` - 2 files. Settles as tier B whether Hero's
  skeleton is identical across costumes, which is the assumption the track retargeting rests on. c00's is on disk.
- `fighter/brave/ai/param/attack_data_param.prc`, `attack_list_param.prc` - 2 files. Not needed for a player-side
  port; wanted only so Mythra's CPU does not use her own side-B numbers against Hero's animation.

### Already in `dumps/` - not requested

- Recipient: `fighter/elight/` is complete (3924 files) - body model + `model/esword/c06,c07`, `motion/body/c06`
  (including her own `d01specials.nuanmb`, which this move replaces), `d01specialscatch/end/start.nuanmb`, the six
  `.prc`, `param/vl.prc`. Mythra's `Sword1`/`Sword2` bones are present in `model/body/c06/model.nusktb`.
- Donor scripts: `dumps/scripts/SSBU-Dumped-Scripts-main/smashline/lua2cpp_brave/brave/` has `SpecialS1/2/3/32`,
  `SpecialSStart`, `SpecialSHold{,M,Max}`, `SpecialS1/32Default`, `SpecialS1/32usen`, `SpecialAirS1/2/3/32`,
  `SpecialAirSStart`, `SpecialAirSHold`, `SwordSwing1/3/4`, `SwordSwing4Charge`, `SwordSwingDash` and the five
  `KillSwordSwing*Common` scripts. `brave_blue/` holds only `AppealLwL/R`, so the sword article's own status code
  has to come from the NRO, as the fireball's did.
- Donor native code: `dumps/arc/prebuilt/nro/release/lua2cpp_brave.nro` - Ghidra input for the `SPECIAL_S`
  status rows and the `L2CFighterAnimcmdGameCommon::game_SwordSwing*Common` helpers, the same route
  `refs/brave_special_n/{neutral_b_status.c,fireball_native.json}` used.
- Donor params: `dumps/arc/fighter/brave/param/vl.prc` (18685 B) - `param_special_s` read with
  `src/pgwr/tools/prc.py`, as `gen_hero_fireball_initializer.py` did for `param_special_n`.
- Donor effects: `dumps/arc/effect/fighter/brave/ef_brave.eff` + `trail/tex_brave_sword1/2/3.nutexb` - the exact
  three the side-B scripts name, plus `brave_chant`, `brave_chant_finish`, `brave_lightning{1_hold,2_swordspark,
  3_sword,3_swordspark}` inside `ef_brave.eff`.
- Donor sounds: `dumps/arc/sound/bank/fighter/se_brave.{nus3bank,nus3audio,tonelabel}` (4359440 B / 82776 B) and
  `sound/sequence/fighter/brave.sqb` already pinned at `refs/brave_special_n/sound/arc/` (1392 B,
  sha256 `46167a0cec8c8452…`).

### How to get it

`tools/fetch_arc_files.py` (new 2026-09-30, reusable, `--check` re-verifies without the console) pulled 139
Chrom files live on 2026-09-30 at arc-network `192.168.2.166:43022`. If the console is up with Smash running,
this request is one extraction run, not a manual dump - say the word and I will run it. Otherwise these are the
paths to pull by hand. Destination on extraction: `refs/brave_special_s/` with `extraction.json` + `SOURCE.json`,
mirroring `refs/brave_special_n/`.

## Requested 2026-09-30 (Claude) - Snake neutral-B grenade on Pyra c06/c07

**Resolved 2026-09-30, same session.** 35 files, 0 failures, into `refs/snake_grenade/arc/` (`extraction.json`, `SOURCE.json`,
`tools/fetch_arc_files.py --set snake_grenade --check`). Correction to the list below: `fighter/snake/model/grenade/c00` is
**empty** in `dumps/` (index entry only), so its 15 files were extracted too. The two models are different objects:
the fighter `grenade` article is the **pin** (bones `Root, Ring, Trigger`), `item/snakegrenade` is the **grenade body**
(`Have, Rot`). The item's motion list has 7 model-only states (`appear have fall throw born lost wait_ground`, no clips);
Snake's body list has 14 `special_(air_)n_*` entries, all naming clips already in `dumps/`.

Needed live (arc-network, console + Smash running), read-only into `refs/snake_grenade/arc/` via `tools/fetch_arc_files.py`:

- `fighter/snake/motion/body/c00/motion_list.bin` - names, flags, blend and cancel data for the 13 `d00specialn*` clips already in `dumps/`; without it the port would invent timings.
- `fighter/snake/motion/grenade/c00/motion_list.bin` is already in `dumps/` (checked); `fighter/snake/model/grenade/c01..c07` are empty in `dumps/` (c00, c04 present) - only c00 is needed, the mod ships c00 for all slots.
- `sound/bank/fighter/se_snake_c00.{nus3audio,nus3bank,tonelabel}` - `se_snake_special_n01..n04` (pin, throw, explosion); no stand-in sounds allowed (rule 17). Not in `dumps/` (`se_snake*` absent from the 554 fighter banks).
- `item/snakegrenade/model/body/c00/*` (12 files) and `item/snakegrenade/motion/body/c00/motion_list.bin` - the thrown item's own model/clips (`Appear`/`Born`/`Throw` names), to compare with `fighter/snake/model/grenade/c00` and decide which the copy uses.
- `item/snakegrenade/script/animcmd/body/{game,effect,sound}.lc` - to byte-check the WuBoytH text decompile of the explosion (`luas/item/snakegrenade/...`), which is tier C.
- `effect/fighter/snake/` is empty in `dumps/`; only needed if the Snake fighter effect files (`ef_snake.eff`) turn out to be referenced; the neutral-B scripts use only `sys_*` effects (`sys_smash_flash`, `sys_run_smoke`, `sys_bomb_a/b`), so it is **not** requested now.

### Additional request 2026-09-30 (Codex continuation) — resolved

Read-only extraction: `refs/snake_grenade/sequence/extraction.json`; 1012 bytes,
sha256 `90370dcfeaed1e27498c1eaf4dc6e2a64d03d79e6a2df8ac1daa7f45df44ce0b`.
The original request below records why it was needed.

- Exact ARC path: `sound/sequence/fighter/snake.sqb`. Missing from both `dumps/arc/`
  and `refs/snake_grenade/arc/`. Needed to audit/copy the sequence records resolving
  Snake neutral-B's `se_snake_special_n01..n04`, alongside the already extracted
  bank/audio/labels. The four simple tone records and encoded samples have passed
  offline merging into both Pyra banks; that is not a playback result.
- User: please dump this file, or make Smash with arc-network available for the
  designated extraction agent. Destination: `refs/snake_grenade/sequence/arc/sound/sequence/fighter/snake.sqb`,
  with extraction provenance and SHA-256. Do not invent a sequence record.

### Additional lower-body request 2026-09-30 (Codex) — resolved

All 15 exact paths below extracted on 2026-09-30 with zero failures and hash-checked.
Provenance and per-file hashes: `refs/snake_grenade/lower_body/extraction.json`.
The original request below records why they were needed.

Exact donor clips referenced by Snake's motion list and common item-shoot routines.
Needed for proper owned hold movement; existing primary clips do not supply them.
User: please dump these or make Smash with arc-network available for read-only extraction.
Set `snake_grenade_lower_body`; destination `refs/snake_grenade/lower_body/arc/`.
Sequence set: `snake_grenade_sequence`. Record extraction provenance and hashes.

- `fighter/snake/motion/body/c00/h10itemlegswait.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegswalkf.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegswalkb.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegsdashf.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegsdashb.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegsbrakef.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegsbrakeb.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegsjumpsquat.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegslanding.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegsslowf.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegsmiddlef.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegsfastf.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegsslowb.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegsmiddleb.nuanmb`
- `fighter/snake/motion/body/c00/h10itemlegsfastb.nuanmb`

## 2026-10-02 (T-0049) - Hero mana/HUD offline prerequisites

Unavailable inside the lab workspace, not claimed absent from this machine. Export from the local 13.0.4 ARC to lab `gamedata/ssbu-13.0.4/arc/` with original paths, or authorize read-only access to the configured external export:

- `fighter/brave/param/vl.prc` - six prices, max/passive/hit/shield values.
- `prebuilt/nro/release/lua2cpp_brave.nro` - failure/pause/lifecycle and full parameter-read paths; pinned SHA256 in the contract.
- `prebuilt/nro/release/lua2cpp_common.nro` - shared constant/status/method mapping.
- `ui/layout/info/info_melee/info_melee/layout.arc` and `ui/param/info/hud_param.prc` - owned fighter pane/layout resources.

Main is available and decoded in lab `gamedata/ssbu-13.0.4/main.bin`; it is not a missing input. Contract: `refs/brave_special_n/T-0033/MANA_HUD_CONTRACT.md`. No running console needed for this request.

## 2026-10-02 — gaogaen_throw_b native throw prerequisites — RESOLVED

Recovered workspace-local vanilla **13.0.4** files with correct original paths:

- `prebuilt:/nro/release/lua2cpp_gaogaen.nro` — donor status registrations/common
  throw setup and native/ACMD dependency cross-checks for victim/collateral behavior.
- `prebuilt:/nro/release/lua2cpp_common.nro` — shared throw/victim motion selection,
  capture transforms, constants and cleanup; also requested above by T-0049.

Inputs are under workspace `gamedata/ssbu-13.0.4/gaogaen_throw_b/native/prebuilt;/nro/release/`.
The previous missing-input claim was wrong: paths without the `prebuilt:/` namespace
returned MISSING. The corrected path resolved, but the shared extractor could not
write a colon filename on Windows. Task-local extraction fixes namespace output
sanitization without changing shared tools. Both NRO headers and SHA256 checked;
task evidence `NATIVE_INPUTS.json` pins originals. No user-supplied input needed.
The local main was measured and remains available; its Gaogaen lua2cpp factories are
undefined imports, not embedded donor functions. Evidence and complete remaining
scope: `evidence/2026-10-02_pgwr_gaogaen_throw_b/RESULT.md`. No game run required.
