# Task: proper fist trails for the Little Mac forward smash on G&W (c06/c07)

"G&W" here always means the Mr. Game & Watch reskin that replaces **Pyra (eflame) costumes c06 and
c07** in the mod `mods/ssbu_mod_new` (project `pgwr`). Vanilla costumes c00-c05 and standalone
Mr. Game & Watch must stay untouched.

## What the user wants

The Little Mac forward smash on G&W (neutral, charge, and the up/down-angled variants) works on the
console, but his fist trails do not show. Give the move its proper fist trails on both c06 and c07:
Little Mac's own `littlemac_attack_line` / `littlemac_attack_arc` effects (and anything else his
forward-smash effect scripts spawn), looking like they do on Little Mac. No stand-in effects.

## What is already known (verify, do not trust blindly)

- The cause was measured offline: the bank was shipped as `effect/fighter/littlemac/ef_littlemac.eff`,
  which an eflame fighter's loader never searches, so the `EFFECT_FOLLOW` calls in
  `src/pgwr/plugin/src/acmd/littlemac_attack_s4.rs` are no-ops. Read
  `kb/findings/effect-ownership-of-donor-banks-and-per-slot-trails.md`,
  `mods/ssbu_mod_new/refs/littlemac_attack_s4/T-0033/FIST_TRAIL_FINDING.md` and
  `mods/ssbu_mod_new/handbook/10_arcropolis_config_json.md`.
- A previous attempt (T-0050) prepared a recipient-owned merge of the donor emitter sets into the
  eflame c06/c07 bank but was blocked on two inputs. Read
  `mods/ssbu_mod_new/evidence/2026-10-02_pgwr_T-0050/RESULT.md` and `DELTA.json`, the T-0050 section
  of `CURRENT_INSTALL.md`, and the sources `tools/build_littlemac_fsmash_effect.py`,
  `tools/merge_hero_neutral_b_effects.py`, `src/pgwr/build.py`. Check whether the `lab/T-0050`
  branch holds work that is not in the current working tree (`git log`/`git show` only).
- The two blockers, and what has changed:
  1. The original `effect/fighter/eflame/ef_eflame.eff`. It now exists in the ARC export that
     `mods/ssbu_mod_new/paths.toml` -> `[dumps] arc` points to. **You may read that export
     (read-only) for this task**; never write into it and never copy more than the files you need.
  2. The effect converter (`builds/.cache/hero_effect_converter/bin/EffectConverter.exe`, built by
     `tools/build_hero_effect_converter.py`) is missing and its pinned source is absent. Solve this
     yourself: find out what the tool was (see the Hero neutral-B effect merge records and the
     CHANGELOG), and either rebuild it from its official open-source repository at a pinned commit
     into `builds/.cache/` (project-local only, record repo, commit and sha256), or write the bank
     merge so it does not need it. Do not install anything system-wide.
- The Hero neutral-B effect merge already ships merged effects for Mythra the same way; use it as
  the working example and the control.

## Done means

- Both slot banks exist as concrete build outputs and the build pipeline (`src/pgwr/build.py`)
  produces them, with every existing effect resource of those banks preserved (prove it with an
  inventory before/after, e.g. `tools/effect_trail_inventory.py`).
- The misplaced donor-folder bank is no longer shipped or declared, unless you show it is needed.
- `tools/audit_littlemac_fsmash.py::check_effect` matches the new layout.
- Your section in `CURRENT_INSTALL.md` says READY (or exactly what blocks it) with hashes,
  build steps and the manual console checks.

{{COMMON}}
