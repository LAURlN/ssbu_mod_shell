# Task: give G&W (c06/c07) Snake's up tilt

"G&W" here always means the Mr. Game & Watch reskin that replaces **Pyra (eflame) costumes c06 and
c07** in the mod `mods/ssbu_mod_new` (project `pgwr`). Vanilla costumes c00-c05 and standalone
Mr. Game & Watch must stay untouched.

## What the user wants

Up tilt (`AttackHi3`) on G&W c06/c07 becomes Snake's up tilt: his animation retargeted onto the
recipient, his hitboxes and timing, his own effects, sounds and rumble. It replaces G&W's own up
tilt on those two costumes only.

## What is already known (verify, do not trust blindly)

- The donor set is already pinned in `mods/ssbu_mod_new/refs/snake_attack_hi3/` (clip, motion list,
  skeleton, `vc_snake_c00`, AI params; `SOURCE.json`, `extraction.json`, `inventory.json`) and the
  measured plan is in `mods/ssbu_mod_new/projects/pgwr/TODO.md`, section "Snake up tilt (AttackHi3)
  on Pyra c06/c07". Follow that plan unless you measure something that contradicts it: ACMD module
  `plugin/src/acmd/snake_attack_hi3.rs` from the dumped `AttackHi3.txt`, asset tool
  `src/pgwr/tools/build_snake_uptilt.py` modelled on the R.O.B. down-tilt tool, Snake's raw
  `attack_hi3` motion entry (cancel 38, flags 0x84), the sound merge for
  `se_snake_attackhard_h01` / `seq_snake_rnd_attack` chained after the Snake neutral-B merge, and a
  delta audit. Read the "deliberate non-issues" there before "fixing" bone names.
- The working examples are the R.O.B. down tilt (`acmd/robot_attack_lw3.rs`, `build_robot_dtilt.py`,
  its section in `CURRENT_INSTALL.md`) and the Little Mac forward smash. Note what the user rejected
  about the first R.O.B. down-tilt clips (filtered retarget left limbs in rest pose; see
  `handbook/04_motion_lists_animation.md` and the T-0036/T-0048 records) and do not repeat it: the
  up tilt is a leg kick, so check that the legs actually carry the motion on the recipient skeleton.
- If you need a donor file that is not pinned, the ARC export that `mods/ssbu_mod_new/paths.toml`
  -> `[dumps] arc` points to is available. **You may read that export (read-only) for this task**;
  never write into it and pin what you take into `refs/snake_attack_hi3/` with its sha256.

## Done means

- The plugin registers the move's game/effect/sound/expression scripts for c06/c07 only, the asset
  pipeline (`src/pgwr/build.py`) produces the clip, motion entry and merged sound banks, and every
  existing tone in the banks is preserved (prove it).
- An offline audit of the delta against the installed 0.20.17 package exists and passes.
- Your section in `CURRENT_INSTALL.md` says READY (or exactly what blocks it) with hashes, build
  steps and the manual console checks.

{{COMMON}}
