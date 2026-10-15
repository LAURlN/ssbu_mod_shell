[freebuff-dispatch 2026-10-02_run1 slot 3-mythra-mana]
Workspace root: <workspace> - work from there; every path below is relative to it.
FIRST ACTION, before anything else: create the file evidence/freebuff-dispatch/2026-10-02_run1/started/3-mythra-mana.txt containing the current date and time.
LAST ACTION, only when you are completely finished (or have hit a blocker you cannot work around): write evidence/freebuff-dispatch/2026-10-02_run1/done/3-mythra-mana.json in one go, as valid JSON with the keys "slot", "status" ("READY", "PARTIAL" or "BLOCKED"), "summary", "changed_files" (list), "installer_notes" (exact build/packaging steps and flags the installer needs), "manual_checks" (numbered console checks for the user, with the vanilla control), "unverified" (list). Nobody is watching this session and nobody can answer questions: another agent is blocked until that file exists, so do not stop, do not ask, and do not write it early.
This prompt is also saved at evidence/freebuff-dispatch/2026-10-02_run1/rendered/3-mythra-mana.md.

# Task: find out why the mana system on Mythra (c06/c07) is not working, and fix it

"Mythra" here always means **Mythra (elight) costumes c06 and c07** of the Pyra/Mythra pair whose
Pyra half is reskinned to Mr. Game & Watch, in the mod `mods/ssbu_mod_new` (project `pgwr`).
Vanilla costumes c00-c05 must stay untouched.

## What the user wants

Mythra c06/c07 uses Hero's neutral-B (Frizz line) and side-B (Zap line). The user expects a working
mana (MP) system for them and reports that it is not working. Find the actual reason and fix it so
the mana system works on the console.

## What is already known (verify, do not trust blindly)

- In the current working tree the Hero moves are built with mana **off**: see the `mana=off` log
  lines and "mana excluded" comments in `src/pgwr/plugin/src/mythra/hero_neutral_b/` and
  `hero_side_b/` (`SUCCESS_SP` is always true, no price is charged, no gauge exists). So the most
  likely answer to "why is it not working" is that it was specified and researched but never
  implemented. Confirm or refute that first, including on the other local branches
  (`git branch -a`, `git log`, `git show <branch>:<path>` only; `lab/T-0049` holds the mana work).
- The specification the user agreed to is `mods/ssbu_mod_new/refs/brave_special_n/T-0033/MANA_HUD_CONTRACT.md`
  (revised by T-0046): one shared meter for the c06/c07 pair, only neutral-B and side-B spend,
  the value persists through the Pyra<->Mythra swap, and a real fighter HUD shows it. Evidence
  gathered so far is in `refs/brave_special_n/T-0046/`; see also `projects/pgwr/STATUS.md`
  (T-0049 paragraph), `projects/pgwr/TODO.md` and `kb/findings/hero-mana-audit-local-main-and-arc-boundary.md`.
- T-0049 was blocked on inputs: Hero's numeric PRC values (prices, max, recovery), the lifecycle /
  failure mapping, and the HUD pane/hook ABI. What has changed: the ARC export that
  `mods/ssbu_mod_new/paths.toml` -> `[dumps] arc` points to is available (it contains
  `fighter/brave/param`, `ui`, etc.). **You may read that export (read-only) for this task**; never
  write into it and pin what you take into `refs/brave_special_n/` with its sha256. The 13.0.4
  game binary is at `gamedata/ssbu-13.0.4/main.bin` and the full `data.arc` beside it.

## How to scope it so that something real ships

Work in this order and finish each layer before starting the next:
1. **Gameplay mana**: an owned MP value for the pair with Hero's real max, prices, natural recovery
   and recovery on hit taken from his params; neutral-B and side-B check and spend it, with Hero's
   real out-of-MP failure behaviour (not a silent no-op); persistence through the swap; reset on
   death/match start as Hero does. Owned state only - no Hero work ids, no casting to Hero.
2. **A visible readout**: the real fighter HUD gauge if it can be reached with what rule 17 allows.
3. Bounded file logging of every spend / refuse / recover / reset (one line per event, never per
   frame) so the user can send a log.

If a layer needs something rule 17 reserves (a raw-offset native hook, anything touching a framework
plugin), do not drop the task: implement everything that does not need it, put the reserved part
behind its own cargo feature that is **off by default**, byte-verify its target on the 13.0.4 image
as the existing hooks do, and say in your handoff that this feature needs the user's approval before
it is built in. Framework plugins on the card stay off limits without exception.

## Done means

- A written answer to "why was it not working", with evidence.
- The fix compiled into the plugin behind the existing `hero-side-b` feature set (plus your own
  feature only for reserved parts), with the mana numbers traceable to the pinned donor params.
- Your section in `CURRENT_INSTALL.md` says READY (or exactly what blocks it) with build steps and
  the manual console checks (including vanilla Mythra c00 and vanilla Hero as controls).

## Rules for this run (read all of it)

**Orient first.** Read `AGENTS.md` at the workspace root, then `mods/ssbu_mod_new/AGENTS.md` (it
governs everything inside the mod repo), `mods/ssbu_mod_new/projects/pgwr/STATUS.md`,
`mods/ssbu_mod_new/CURRENT_INSTALL.md` and the pages `mods/ssbu_mod_new/handbook/00_INDEX.md` lists
for your task, plus `handbook/graveyard.md` for what already failed.

**You are one of three Freebuff agents working in this same tree at the same time.** The other two
tasks are: (1-littlemac-fist-trails) proper fist trails for the Little Mac forward smash on G&W (c06/c07); (2-snake-up-tilt) give G&W (c06/c07) Snake's up tilt. Nobody is coordinating you live, so:

- Git: read-only commands only. No commit, checkout, switch, branch, stash, reset, restore or merge.
- Do not bump the version in `Cargo.toml`, do not run `tools/package_pgwr_release.py`, do not run
  `src/pgwr/install-to-card.sh`, do not touch the SD card (drive E:), do not run Ryujinx. A
  designated installer agent will do one combined build, package and install of all three tasks
  after you are all done, from the live source tree. Make that possible: wire your change into the
  normal pipeline and tell the installer exactly what to run.
- Compile-check the plugin only in your own cargo cache:
  `CARGO_TARGET_DIR=<mod repo>/builds/.cache/pgwr-fb-3-mythra-mana-target cargo skyline build --release --features snake-neutral-b,hero-side-b -- --offline`
  (see `handbook/02_toolchain.md`; add your own feature if you created one). Never use another
  cache. If the compile breaks in a file that is not yours, another agent is mid-edit: wait a few
  minutes and retry. Do not "fix" or revert their code.
- Do not run `src/pgwr/build.py` into the shared `builds/pgwr/<version>/` tree (two concurrent asset
  builds corrupt it - this has happened before). Verify your generators standalone, writing to
  `mods/ssbu_mod_new/builds/.cache/fb-3-mythra-mana/` or `mods/ssbu_mod_new/scratch/2026-10-02_fb-3-mythra-mana/`.
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

