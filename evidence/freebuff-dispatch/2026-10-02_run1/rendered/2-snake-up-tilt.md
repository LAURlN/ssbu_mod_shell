[freebuff-dispatch 2026-10-02_run1 slot 2-snake-up-tilt]
Workspace root: <workspace> - work from there; every path below is relative to it.
FIRST ACTION, before anything else: create the file evidence/freebuff-dispatch/2026-10-02_run1/started/2-snake-up-tilt.txt containing the current date and time.
LAST ACTION, only when you are completely finished (or have hit a blocker you cannot work around): write evidence/freebuff-dispatch/2026-10-02_run1/done/2-snake-up-tilt.json in one go, as valid JSON with the keys "slot", "status" ("READY", "PARTIAL" or "BLOCKED"), "summary", "changed_files" (list), "installer_notes" (exact build/packaging steps and flags the installer needs), "manual_checks" (numbered console checks for the user, with the vanilla control), "unverified" (list). Nobody is watching this session and nobody can answer questions: another agent is blocked until that file exists, so do not stop, do not ask, and do not write it early.
This prompt is also saved at evidence/freebuff-dispatch/2026-10-02_run1/rendered/2-snake-up-tilt.md.

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

## Rules for this run (read all of it)

**Orient first.** Read `AGENTS.md` at the workspace root, then `mods/ssbu_mod_new/AGENTS.md` (it
governs everything inside the mod repo), `mods/ssbu_mod_new/projects/pgwr/STATUS.md`,
`mods/ssbu_mod_new/CURRENT_INSTALL.md` and the pages `mods/ssbu_mod_new/handbook/00_INDEX.md` lists
for your task, plus `handbook/graveyard.md` for what already failed.

**You are one of three Freebuff agents working in this same tree at the same time.** The other two
tasks are: (1-littlemac-fist-trails) proper fist trails for the Little Mac forward smash on G&W (c06/c07); (3-mythra-mana) find out why the mana system on Mythra (c06/c07) is not working, and fix it. Nobody is coordinating you live, so:

- Git: read-only commands only. No commit, checkout, switch, branch, stash, reset, restore or merge.
- Do not bump the version in `Cargo.toml`, do not run `tools/package_pgwr_release.py`, do not run
  `src/pgwr/install-to-card.sh`, do not touch the SD card (drive E:), do not run Ryujinx. A
  designated installer agent will do one combined build, package and install of all three tasks
  after you are all done, from the live source tree. Make that possible: wire your change into the
  normal pipeline and tell the installer exactly what to run.
- Compile-check the plugin only in your own cargo cache:
  `CARGO_TARGET_DIR=<mod repo>/builds/.cache/pgwr-fb-2-snake-up-tilt-target cargo skyline build --release --features snake-neutral-b,hero-side-b -- --offline`
  (see `handbook/02_toolchain.md`; add your own feature if you created one). Never use another
  cache. If the compile breaks in a file that is not yours, another agent is mid-edit: wait a few
  minutes and retry. Do not "fix" or revert their code.
- Do not run `src/pgwr/build.py` into the shared `builds/pgwr/<version>/` tree (two concurrent asset
  builds corrupt it - this has happened before). Verify your generators standalone, writing to
  `mods/ssbu_mod_new/builds/.cache/fb-2-snake-up-tilt/` or `mods/ssbu_mod_new/scratch/2026-10-02_fb-2-snake-up-tilt/`.
  If `build.py` has an output-directory override, you may run the full asset build into your own
  directory there.
- Shared files (`plugin/src/lib.rs`, `plugin/src/acmd/mod.rs`, `plugin/src/mythra/mod.rs`,
  `plugin/Cargo.toml` features, `src/pgwr/build.py`, `CURRENT_INSTALL.md`, `STATUS.md`,
  `CHANGELOG.md`, `TODO.md`, handbook pages, `facts.yaml`): re-read the file immediately before
  every edit, make small additive edits to your own lines/section, never rewrite a whole file from
  memory and never remove another agent's lines. Put everything else in new files of your own.
- There are uncommitted changes in the tree from earlier tasks (Hero side-B 0.20.18, Monkey Flip
  locks, installer fixes). They are intentional. Leave them alone.

**Inputs.** The game dump under `dump/` is read-only. Extracted game files are in `gamedata/`. The
ARC export named by `mods/ssbu_mod_new/paths.toml` (`[dumps] arc`) may be read, never written.
Never download game content, keys or firmware. Never approximate a missing asset.

**Standard.** Mod rule 17 applies: the mod owns what it uses (own scripts, own copied
clips/effects/sounds/params, no stand-ins, no calling another fighter's code at runtime, no "hide
it" hacks). Gate by costume c06/c07 (rule 18). Framework plugins are off limits (rule 22).

**Honesty.** No console and no emulator are available to you, so nothing you do can prove behaviour.
Say "compiles", "byte-equal", "audit passes" for what you measured and mark everything else
unverified with its tier (rule 8). Do not write "works".

**Record before you finish** (mod rules 7, 12, 28): your own section in `CURRENT_INSTALL.md`
(readiness, sources, hashes, dependencies, blockers, numbered manual console test of at most ~12
steps with the vanilla control and pass/fail signs), `projects/pgwr/STATUS.md`,
`projects/pgwr/CHANGELOG.md`, the handbook / `handbook/graveyard.md` for what you learned and what
failed, promoted tools in `tools/` with a docstring and smoke test. Leave no `*.log` / `*.bak`
leftovers in source directories.

**Keep going until it is finished.** You cannot ask anyone anything. When you hit an obstacle,
diagnose it and find another proper route; record dead ends and continue. Only if every proper route
is exhausted do you stop, and then the done file must say status "BLOCKED" or "PARTIAL" with the
exact evidence and what is needed. Then perform the LAST ACTION from the top of this prompt.

