---
title: A shipped effect bank or trail file is only owned if the recipient fighter's loader can reach it
summary: An .eff under effect/fighter/<donor>/ is loaded by nobody, and a per-slot trail folder may hold several files competing for one internal resource name; both are byte-checkable before any console run.
status: verified
tags: [pgwr, effects, arcropolis, one-slot-effects, nutexb, trails, research, mod-workspace]
updated: 2026-10-01
source: T-0035
---

## What

Two effect-ownership rules were measured on the packaged pgwr 0.20.16 tree and both were
violated, silently:

1. Only the *requesting* fighter's own `effect/fighter/<fighter>/` directory is searched, and
   inside it only `ef_<fighter>.eff` or `ef_<fighter>_c<slot>.eff` is accepted. Little Mac's
   forward-smash bank was shipped as `effect/fighter/littlemac/ef_littlemac.eff` (13.8 MB, 44
   emitters) and declared as a new file of the `fighter/eflame/c06` group, so an eflame fighter
   never resolved `littlemac_attack_line` / `littlemac_attack_arc` and the `EFFECT_FOLLOW` calls
   in `plugin/src/acmd/littlemac_attack_s4.rs` were no-ops.
2. A trail texture is identified by its **internal NUTEXB footer name**, which the One Slot
   Effects plugin rewrites to `<NAME>_C<slot>` so two costume slots can share a file name. Each
   `effect/fighter/eflame/trail_c06|c07/` folder holds 14 files for 7 names: two files per name,
   and four files whose name matches no `ParamLabels.csv` label at all, so they can never be
   requested.

## Evidence

Both are tier B, measured offline on 2026-10-01 in `mods/ssbu_mod_new` with
`tools/effect_trail_inventory.py --smoke` and
`tools/effect_trail_inventory.py builds/pgwr/0.20.16/ultimate/mods/pyra_gamewatch_reskin --json ...`:

* `effect/fighter/eflame/` contains no `.eff` bank at all (only `trail_c06/`, `trail_c07/`), and
  `bank_loader_fighter` for the littlemac bank is `littlemac`.
* Duplicate internal names in each slot: `TEX_CLOUD_SWORD1`, `TEX_CLOUD_SWORD2`,
  `TEX_ELIGHT_SWORD1..5`, each shared by the canonical file and a `tex_eflame_*` byte copy.
* `tex_eflame_cloud_sword1/2.nutexb` and `tex_eflame_sword4/5.nutexb` have no engine label.
* The acceptance rule and the rename hook are in the pinned upstream source
  `src/pgwr/tools/one_slot_effects_reference.rs` (`check_extension_eff_inline_hook`,
  `fighter_lookup_effect_folder`, `get_trail_folder_hash`, `get_raw_nutexb_data`).
* `dumps/decoded/arc_files.tsv:435767` shows `effect/fighter/littlemac/ef_littlemac.eff` is a
  **base-game** path, so the build's "this is a new file" guard passed only because the local
  `dumps/arc` tree is absent.

No emulator, no console, no automated test was run (testing benched for this run).

Full analysis and fixes: `mods/ssbu_mod_new/refs/littlemac_attack_s4/T-0033/FIST_TRAIL_FINDING.md`
and `mods/ssbu_mod_new/refs/cloud_attack_air_f/T-0033/CLOUD_TRAIL_FINDING.md`; the general rules
are recorded in the mod handbook at `handbook/10_arcropolis_config_json.md`.

## Why (if known)

The failure is silent by design: an unresolvable effect name produces no error, and an
undeclared or misplaced file is exactly the "animates and hits, nothing extra is drawn" shape
the mod handbook warns about. The trail symptom (Pyra c06 loses its jab/fair trails only when
c07 is in the match) has **no settled cause yet** - name collision, one-slot load order and the
never-cleared `EFF_FIGHTER_KIND` global are all still hypotheses, listed with their settling
experiments in the Cloud finding. Mythra's own trails share the same internal-name pattern and
are reported working, which rules out "a shared name across slots is fatal by itself".

## What to do instead / next

Run `tools/effect_trail_inventory.py` over a packaged tree before shipping any new effect or
trail asset; it answers "which fighter loads this bank" and "can this texture ever be requested"
in seconds, with no console. Missing inputs both fixes need:
`effect/fighter/eflame/ef_eflame.eff` (requested in the mod repo's `dumps/MISSING.md`) and the
EffectConverter at `builds/.cache/hero_effect_converter/bin/EffectConverter.exe`.

## Update 2026-10-02 (T-0054)

The eflame `trail_c06|c07` duplicate/dead-file cleanup was implemented in the mod repo (branch
`lab/T-0054`, `build_cloud_trail.build_eflame_trail_folder`): 14 -> 7 files per slot (rev 2; rev 1's 10 was rejected because re-footering tex_eflame_sword1..3 would re-theme
Pyra's ordinary vanilla trails, so no tex_eflame_* file ships), one file per
internal name, file name == footer name, Cloud ribbon and Mythra textures byte-identical. Re-reading
the pinned loader showed lookups are by footer name per `(name, slot)`, so cross-slot sharing cannot
collide in the rename table; the cleanup therefore does not claim to fix the two-player symptom. Next
evidence if the manual matrix still fails: plugin-side `SlotCache`/`EFF_FIGHTER_KIND` (reserved framework).
Details: `mods/ssbu_mod_new/refs/cloud_attack_air_f/T-0054/RESOURCE_OWNERSHIP.md`. Unverified in game.
