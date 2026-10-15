[freebuff-dispatch 2026-10-02_run1 slot 1-littlemac-fist-trails]
Workspace root: <workspace> - work from there; every path below is relative to it.
FIRST ACTION, before anything else: create the file evidence/freebuff-dispatch/2026-10-02_run1/started/1-littlemac-fist-trails.txt containing the current date and time.
LAST ACTION, only when you are completely finished (or have hit a blocker you cannot work around): write evidence/freebuff-dispatch/2026-10-02_run1/done/1-littlemac-fist-trails.json in one go, as valid JSON with the keys "slot", "status" ("READY", "PARTIAL" or "BLOCKED"), "summary", "changed_files" (list), "installer_notes" (exact build/packaging steps and flags the installer needs), "manual_checks" (numbered console checks for the user, with the vanilla control), "unverified" (list). Nobody is watching this session and nobody can answer questions: another agent is blocked until that file exists, so do not stop, do not ask, and do not write it early.
This prompt is also saved at evidence/freebuff-dispatch/2026-10-02_run1/rendered/1-littlemac-fist-trails.md.

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

## Rules for this run (read all of it)

**Orient first.** Read `AGENTS.md` at the workspace root, then `mods/ssbu_mod_new/AGENTS.md` (it
governs everything inside the mod repo), `mods/ssbu_mod_new/projects/pgwr/STATUS.md`,
`mods/ssbu_mod_new/CURRENT_INSTALL.md` and the pages `mods/ssbu_mod_new/handbook/00_INDEX.md` lists
for your task, plus `handbook/graveyard.md` for what already failed.

**You are one of three Freebuff agents working in this same tree at the same time.** The other two
tasks are: (2-snake-up-tilt) give G&W (c06/c07) Snake's up tilt; (3-mythra-mana) find out why the mana system on Mythra (c06/c07) is not working, and fix it. Nobody is coordinating you live, so:

- Git: read-only commands only. No commit, checkout, switch, branch, stash, reset, restore or merge.
- Do not bump the version in `Cargo.toml`, do not run `tools/package_pgwr_release.py`, do not run
  `src/pgwr/install-to-card.sh`, do not touch the SD card (drive E:), do not run Ryujinx. A
  designated installer agent will do one combined build, package and install of all three tasks
  after you are all done, from the live source tree. Make that possible: wire your change into the
  normal pipeline and tell the installer exactly what to run.
- Compile-check the plugin only in your own cargo cache:
  `CARGO_TARGET_DIR=<mod repo>/builds/.cache/pgwr-fb-1-littlemac-fist-trails-target cargo skyline build --release --features snake-neutral-b,hero-side-b -- --offline`
  (see `handbook/02_toolchain.md`; add your own feature if you created one). Never use another
  cache. If the compile breaks in a file that is not yours, another agent is mid-edit: wait a few
  minutes and retry. Do not "fix" or revert their code.
- Do not run `src/pgwr/build.py` into the shared `builds/pgwr/<version>/` tree (two concurrent asset
  builds corrupt it - this has happened before). Verify your generators standalone, writing to
  `mods/ssbu_mod_new/builds/.cache/fb-1-littlemac-fist-trails/` or `mods/ssbu_mod_new/scratch/2026-10-02_fb-1-littlemac-fist-trails/`.
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

