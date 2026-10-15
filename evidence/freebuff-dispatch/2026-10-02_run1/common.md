## Rules for this run (read all of it)

**Orient first.** Read `AGENTS.md` at the workspace root, then `mods/ssbu_mod_new/AGENTS.md` (it
governs everything inside the mod repo), `mods/ssbu_mod_new/projects/pgwr/STATUS.md`,
`mods/ssbu_mod_new/CURRENT_INSTALL.md` and the pages `mods/ssbu_mod_new/handbook/00_INDEX.md` lists
for your task, plus `handbook/graveyard.md` for what already failed.

**You are one of three Freebuff agents working in this same tree at the same time.** The other two
tasks are: {{OTHERS}}. Nobody is coordinating you live, so:

- Git: read-only commands only. No commit, checkout, switch, branch, stash, reset, restore or merge.
- Do not bump the version in `Cargo.toml`, do not run `tools/package_pgwr_release.py`, do not run
  `src/pgwr/install-to-card.sh`, do not touch the SD card (drive E:), do not run Ryujinx. A
  designated installer agent will do one combined build, package and install of all three tasks
  after you are all done, from the live source tree. Make that possible: wire your change into the
  normal pipeline and tell the installer exactly what to run.
- Compile-check the plugin only in your own cargo cache:
  `CARGO_TARGET_DIR=<mod repo>/builds/.cache/pgwr-fb-{{SLOT}}-target cargo skyline build --release --features snake-neutral-b,hero-side-b -- --offline`
  (see `handbook/02_toolchain.md`; add your own feature if you created one). Never use another
  cache. If the compile breaks in a file that is not yours, another agent is mid-edit: wait a few
  minutes and retry. Do not "fix" or revert their code.
- Do not run `src/pgwr/build.py` into the shared `builds/pgwr/<version>/` tree (two concurrent asset
  builds corrupt it - this has happened before). Verify your generators standalone, writing to
  `mods/ssbu_mod_new/builds/.cache/fb-{{SLOT}}/` or `mods/ssbu_mod_new/scratch/2026-10-02_fb-{{SLOT}}/`.
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
