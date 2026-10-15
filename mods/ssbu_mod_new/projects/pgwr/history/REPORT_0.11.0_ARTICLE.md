# 0.11.0: G&W's props (`normal_weapon` article), registered by this mod (Claude, 2026-09-29)

Installed on the card. Not yet run on the Switch.

## What was on the card before

This was Space Bunny's 0.8.1: plugin `ed2988e1…` plus 737 asset files, **not** 0.7.0. Its 0.10.0 had
replaced the global `libsmashline_plugin.nro` with a rebuild (`b906669d…`) and crashed. The card had been
rolled back to 0.8.1 and the known-good smashline `5f4091ee…`.

## Why 0.9.0/0.10.0 failed, and what is different now

1. **The wrong premise.** Space Bunny's claim was: "a mod NRO statically links its own smashline, so
   `clone_weapon` from a mod writes into a map nothing reads." That is false. The `smashline` crate a mod
   links (`crates/smashline/src/lib.rs`, `decl_imports!`) resolves every `smashline_*` function at runtime
   with `nn::ro::LookupSymbol` and calls into the installed plugin. The built 0.11.0 NRO imports
   `nn::ro::LookupSymbol` and contains the string `smashline_clone_weapon`. The card's smashline
   `5f4091ee` exports `smashline_clone_weapon` at 0x160a0. **The global plugin is not touched.**
2. **The wrong article id.** `ArticleModule::*` take the fighter's *local* article index. 125 is G&W's
   global weapon kind, which is what `clone_weapon` takes. The moves now pass
   `crate::article::normal_weapon()`, which is `FIGHTER_EFLAME_ARTICLE_TERM` (5) plus the index
   `clone_weapon` returns.
3. **The wrong `config.json`.** The article's folders were declared as `new-dir-infos`. But ARCropolis
   loads a fighter's files per costume group (`fighter/eflame/c0N`), and that group lists the article's
   files too. Inventing new groups gave "Cannot get file info range" and a null read in
   `fighter_initialize_object_data` (crash 01790691291). Now `new-dir-infos` is empty, and each new file
   is added to its existing `fighter/eflame/c0N` group. That is the shape the working mgw_standalone
   clone pack uses (keys are costume groups, values are full file paths).
4. **Vanilla slots.** The article table belongs to the fighter kind, and the engine loads article models
   while it initialises the fighter. So the article's files now ship for **all eight** Pyra slots. G&W's
   eight `normal_weapon` folders are byte-identical to each other. Vanilla Pyra never spawns the article.

## What G&W's code does for this article (measured in `lua2cpp_gamewatch.nro`)

* The hash of `gamewatch_normal_weapon` appears only in the three animcmd agent factories. Each builds
  an empty `L2CFighterAnimcmdBase`.
* The status factory has no case for it. It does have cases for bomb, breath, octopus and others.
* `ArticleModule::remove*` and `generate_article` calls that use NORMAL_WEAPON's constant-table slot
  (0xeb1c) appear only in the ACMD region, never in G&W's status code.

So there is **no G&W status code to port**. The article's whole behaviour is the move scripts (spawn,
`change_motion`, remove), which are ported 1:1 by R23, plus the engine descriptor that `clone_weapon`
copies.

## Changes

* `plugin/src/article.rs`: `clone_weapon("gamewatch", WEAPON_KIND_GAMEWATCH_NORMAL_WEAPON, "eflame",
  "normal_weapon", false)` runs first in `main`. It also holds the runtime local id and G&W's real
  `WEAPON_GAMEWATCH_NORMAL_WEAPON_KIND_*` values (Space Bunny's were placeholders).
* `tools/gen_acmd.py`: R23 now emits `normal_weapon()`, and the R24 regex accepts it.
* `build.py`: `ARTICLE_SLOTS` c00-c07. `build_config_json` was rewritten as above, and it asserts that
  the declared files equal the new files on disk.
* Card: plugin `758b3e70e1e88aaea3abf722400823356ad3d282fde72e74d25e7ca38a45810f`, 961 mod files.
  Backup: `sd_backups/2026-09-29_before_pgwr_0.11.0/`. Framework plugins are re-hashed and unchanged.

## Left as is, and why

* **`landing_air_n`** is still unported (UNPORTABLE: the dump mangled the article rate call). The nair
  fishbowl therefore does not switch to its landing clip.
* **The prop-kind write** stays in plugin storage. G&W's slot 0x100000BD is not his slot on an eflame
  agent, and no lua2cpp code reads it.
* **Stale staging:** `mod_output/atmosphere/.../libsmashline_plugin.nro` may still be Space Bunny's
  rebuilt one. Never run `install-to-card.sh` without `--no-smashline`.
* `mod_files/mgw_standalone/smashline_1304/src` still contains Space Bunny's `pgwr_article.rs` and
  `lib.rs` edits, so that tree no longer matches the plugin on the card.

## Console test

Log lines (`[PGWR]`) at boot: `ARTICLE registered: gamewatch weapon kind 125 as eflame_normal_weapon,
clone index 0, local article id 5`.

1. **First, vanilla Pyra c00 and c05 and Mythra** load into a match and play normally. A crash at match
   start on these means the config/file route. Rollback is the backup folder.
2. **Real G&W** still has his props.
3. c06/c07: f-tilt (stool), d-tilt (manhole), jab and rapid jab (spray), nair (fishbowl), bair and its
   landing (turtle), down taunt (spray). Each spawn logs `ARTICLE spawn: ... exists true/false`.
4. Report per move: prop visible? In the hand or somewhere else? Does it disappear afterwards?

---

# 0.11.1: prop lifetime, nair landing, leftovers (Claude, 2026-09-29)

The user tested 0.11.0 on console: the props appear. The fishbowl does not disappear properly, and the
turtle stays when Pyra is hit out of bair.

## What removes the prop in vanilla (measured)

* `lua2cpp_common.nro` builds the constant table that every lua2cpp module reads
  (`construct_bind_const_value_table` at 0x52d8c0). It holds 0x4c0d XXH64 (seed -1) name hashes at
  0x6a5b70. `scratch/constmap.py` resolves any offset. `FIGHTER_GAMEWATCH_GENERATE_ARTICLE_NORMAL_WEAPON`
  is at 0xeb1c.
* Every `ArticleModule::*` call on 0xeb1c in `lua2cpp_gamewatch.nro` is inside a move script, and those
  are all ported. G&W's status code only touches rescue/parachute/oil/octopus/food.
* The article's descriptor in `main` is G&W's article [5]: weapon 125, max 1, init callback 0xa802a0.
  Relocations applied, see `scratch/maindesc.py`. The init reads the owner's work int 0x100000BD (the
  prop kind) and a per-kind common power-up float. It has no removal logic.
* So the "remove when interrupted" rule is native code keyed on G&W as the owner. It cannot be copied.
  `article.rs::lifetime` reproduces the rule on the gated agent only: the prop is kept in the status that
  spawned it, jab into rapid jab, and aerial into its landing. It is removed on any other status. The log
  shows `ARTICLE removed: entry N left status X for Y`.

## Nair landing

The dump garbled `game_landingairn`. The compiled function (0xc0200) is
`if IS_EXIST_ARTICLE(nw) { change_motion(nw, landing_air_n); SET_RATE_ARTICLE_V(nw, get_value_float(SO_VAR_FLOAT_MOTION_RATE_TOTAL)) }`.
Generator rule R25 restores that form, and `game_landingairn` is no longer UNPORTABLE.
`compat::SET_RATE_ARTICLE_V` now takes the rate too; the old one pushed only the article id.

## Leftovers

* `mgw_standalone/smashline_1304/src` is reverted. `pgwr_article.rs` and the pre-edit `lib.rs` are parked in
  `scratch/parked_space_bunny_smashline_edits/`. No other file in that tree changed after 2026-09-27.
* The staged `mod_output/.../libsmashline_plugin.nro` is already the good `5f4091ee`.

Card: plugin `83ce5cb50fce1ec6e0e12457584e24aeb789bc4d65c909368546ea3f2bd872af`. The assets are unchanged
from 0.11.0. Backup: `sd_backups/2026-09-29_before_pgwr_0.11.1/`.

---

# 0.11.2: diagnostic build (Claude, 2026-09-29)

Console report on 0.11.1:
* The fishbowl disappears after landing, but with the wrong animation.
* The nair and bair props still do not disappear properly when Pyra is hit.
* The ledge attack does not look right.

Checked offline and ruled out:
* Ledge attack. The clip is G&W's (the only difference is resave float noise, max 8e-7). The motion
  entry is G&W's (`cliff_attack_quick` -> `g02cliffattack`, same script). All four scripts are ported,
  including `lhand_alarm` at frame 16. The prop materials and textures follow the same mapping as the
  helmet, which works. A `complete_visibility` change was tried and reverted: G&W's own clip already
  tracks AlarmM as a constant False, so the pass never touched it.
* The landing script is registered, and `landing_air_n`'s entry points to it.

Fixed:
* `article.rs` indexed per-player state by battle object id, which is not guaranteed to be below 8 for
  the Pyra/Mythra pair. When it is not, the lifetime rule silently did nothing. It now uses
  `FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID`.

Added: `sd:/ultimate/pgwr_log.txt`. It gets a boot line, and one line for each spawn (with both
existence checks and the active count), each status change while a prop is tracked (with the motion
kind), each removal, each prop that vanishes by itself, and any prop the rule was not tracking.

Card: plugin `fa328fb092537ac34c12824718d73b0fb078b72ba515e1057bac9f6a74a9ac7d`. Backup:
`sd_backups/2026-09-29_before_pgwr_0.11.2/`.
