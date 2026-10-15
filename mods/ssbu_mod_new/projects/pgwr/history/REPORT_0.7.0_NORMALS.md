# 0.7.0: normals pass (Claude, 2026-09-29)

Installed on the card. **Nothing here has been run on the Switch.** It was built,
asserted and byte-compared offline only.

## What the user reported, and the causes found

| Symptom | Cause found | Fix in 0.7.0 | Confidence |
| --- | --- | --- | --- |
| Legs dislocate / stick while the rest moves | (a) Pyra's `ik.prc` and `scharge.prc` (foot IK, smash-charge foot IK) had her weights and target feet on G&W's skeleton; (b) 33 shared motions carried Pyra's flags/blend (`turn`, `turn_dash`, `escape_f`, `run`, ...) | G&W's `ik.prc`, `scharge.prc`, `update.prc`, `flip.prc`; G&W's motion-list entries whole | Plausible, not proven. Both are real mismatches; I could not observe the glitch, so which one (or both) causes it is unconfirmed |
| Old Pyra sword on nair/bair | G&W has no `effect_attackairn/b` script, so the generator emitted none and Pyra's own sword-trail scripts kept running | Empty overrides for every eflame script G&W lacks (50) | High: cause is directly visible in the script sets |
| Invisible props (fishbowl on nair, helmet + head on up smash, stool on f-tilt) | Mesh-group tables (`head`, `helmet`, `hand`, `lhand`, ...) live in `param/expression_vl.prc`; Pyra's has none, so every `VisibilityModule::set_int64` in the ported scripts was a no-op | G&W's five `param_visibility_data_*` tables merged into eflame's file | High for the mechanism; the exact groups per move are unverified |
| "Are there leftover Pyra animations outside specials?" | Yes, several layers, see below | | |

## Leftover Pyra content outside specials (answer)

* **Animations: none reachable any more.** Pyra's motion list gave every shared move her own
  cancel frames and blends (jab 22 vs G&W 16, up smash 64 vs 39, dash 30 vs 18). The list is now
  G&W's (746 kinds, entries copied byte-identical). The build asserts that every clip name in
  it is written by the build. Pyra-only kinds (specials, final, swap, entry) are kept but play
  G&W stand-in clips.
* **Scripts: 948 Pyra ACMD scripts, only 110 were overridden.** Now covered (non-special
  motions): 388 ported from G&W, 75 skipped as identical to Pyra's own (R14), 50 emptied.
* **Still Pyra's, deliberately or not yet:**
  * 183 `sound_*` scripts (Pyra's footsteps and voice). Needs G&W's sound bank, not a script port.
  * 19 item-handling scripts the dump cannot express (dropped arguments): `game_swordswing1/3/4/dash`,
    `clubswing1/3/4`, `itemlightget/eat`, `itemheavyget`, `downeatd/u`, `landingairn` and four
    expression/effect scripts. Reasons are in `generated-common-manifest.json` (`unported`).
  * Every special, final smash, entry and the swap scenes (kept on purpose).
  * The status code itself (see below).

## What changed

* `build.py`: G&W motion list; 20 clips with names eflame lacks are stored under spare eflame
  names (alias); G&W's four motion `.prc` files; `expression_vl.prc` merge. The "new file name"
  prerequisite from 0.6.0 is **removed** (see the correction in `move_replacement_guide.md`:
  console evidence says new file names do not load).
* `tools/prc.py`: typed `.prc` reader/writer.
* `tools/gen_common.py` + `generated/common.rs`: the remaining non-special scripts.
* `tools/gen_acmd.py`: rules R15-R21. `plugin/src/acmd/compat.rs`: six missing `sv_animcmd` wrappers.
* Installed `libpyra_gamewatch_reskin.nro` 4d74191056230bdb0d7693d32f72b2177c3338096b749c5ead72320e8e60576b
  (151552 bytes) and the asset tree (736 files). Backup: `sd_backups/2026-09-29_before_pgwr_0.7.0/`.
  Rollback: copy that folder's contents back. Framework plugins untouched (re-hashed, identical).

## Known gaps in the normals (not fixed here)

1. **Up tilt / up smash variants.** G&W has `attack_hi3_l`, `attack_hi4_r`, `attack_hi4_hold_r`; his status
   code picks the variant. Pyra's status plays the base one. Needs custom statuses.
2. **Jab chain.** Pyra's statuses still run jab 1-2-3 (params, and 12/13 scripts point to G&W's jab).
   G&W's jab is one hit then rapid. Needs the jab params/status.
3. **Article props.** Jab/down-smash `normal_weapon`, f-air bomb, u-air breath: dropped (R1/R6/R21).
4. **Per-fighter param file.** `virtual_node_data`/`effect_emit_node_data` in `expression_vl.prc` are Pyra's
   (changing them would change vanilla Pyra): items/hats attach at Pyra's positions.
5. **`hide_esword` and the visibility-completion pass** are still workarounds (handoff item 8).
6. Stats, hurtboxes, model scale: Pyra's.

## Risks, in the order to suspect them

1. **Vanilla Pyra c00-c05 fails to load or looks wrong** -> `fighter/eflame/param/expression_vl.prc`. It is per
   fighter, so it is the one change that reaches vanilla Pyra. My PRC writer keeps the format's invariants
   (checked with two independent readers, and 110 mesh names cannot collide) but is not byte-identical to stock.
   Fix = delete that one file from the mod folder.
2. **c06/c07 will not load / crashes at character select or match start** -> `motion_list.bin` is 47.7 KB, up
   from Pyra's 43.4 KB. ARCropolis should patch sizes, but this is the first large growth on hardware.
3. **Crash during one specific move** -> a ported script. Each is generated 1:1 from the dump; name the
   move and it maps to one function in `generated/common.rs`.

## Console test

Boot log (filter `[PGWR]`): `plugin v0.7.0 ...`, `gated fighter=eflame costumes=[6, 7]`,
`GATE ACTIVE ... colour 6` (or 7) once a c06/c07 fighter exists.

1. **First**: vanilla Pyra c00, c03, c05 and Mythra load and play normally.
2. c06 and c07 load. No "1"/"2" signs, no hammer, no second G&W, no Pyra sword.
3. Legs: walk, run, dash, turn, run-turn, jump, land, crouch, dodge, and **charge a smash** (all three).
   Tell me which move if the legs still stick.
4. Props: nair (fishbowl), up smash (helmet and head), f-tilt (stool), other aerials/tilts.
5. nair/bair: no sword. Jab/tilts/smashes/aerials should feel like G&W (timing changed: shorter jab, dash, etc.).
6. Down-B swap both ways still works. Side-B Judge (0.6.0) still works.
