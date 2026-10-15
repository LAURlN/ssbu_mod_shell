# Rules for every agent working in this workspace (draft for AGENTS.md)

Short on purpose. If you break one of these you are recreating the mess this workspace replaced.
The reasons are in `PLAN.md` section 2; each rule cites the failure that produced it.

## A. Where things go

1. **Never create a top-level folder.** Work goes in an existing `src/<project>/`; new knowledge in `handbook/<topic>`;
   status in `projects/<project>/STATUS.md`. If none fits, write the proposal in `projects/<project>/TODO.md` and ask.
   *(Reason: pyra_mythra_clone, mod_output_pair, mod_backup_2, two mythra_gamewatch_swap dirs.)*
2. **Dumps are read-only.** Nothing under `dumps/` is ever edited, regenerated in place or written to. Derived data goes in
   `dumps/decoded/` with the script + version that produced it, or in `builds/`.
   Need a file that is not in `dumps/`? Add it to `dumps/MISSING.md` with the exact ARC path and why, and ask the user to dump it.
   Never approximate a missing asset.
3. **Scratch is dated and disposable**: `scratch/<YYYY-MM-DD>_<agent>/`. Anything useful must be promoted to `tools/`
   (with a docstring and a smoke test) before the session ends. Scratch is deleted after 30 days.
4. **No absolute paths in code or docs.** Use `paths.toml`. (Reason: three machines/users, drive letters moved twice.)
5. **Builds go to `builds/<project>/<version>/`** with `MANIFEST.json` (sha256 of NRO and mod tree, git commit, file count,
   toolchain). Keep the last three versions + one `last-known-good` marker. No hand-made `backups/`, `before-x`, `sd-backup-*` folders
   in source trees - the installer's automatic backup goes to `evidence/sd-backups/` and is pruned to the last five.
6. **Version everything that ships**: semantic version in the plugin banner, `info.toml`, MANIFEST, and CHANGELOG.

## B. How to record what you learn

7. **One place per fact.** Before writing a finding, search `handbook/` and `handbook/facts/facts.yaml`.
   Update the existing entry; do not append a second narrative. Never leave two rules that disagree - fix or move the loser to
   `handbook/graveyard.md` with a dated reason.
8. **Every fact has a tier and evidence:**
   - `A` hardware: console result or decoded crash report (link the file in `evidence/`)
   - `B` measured offline by a script in `tools/` (name the script and the dump file/hash it ran on)
   - `C` read from pinned third-party source (repo + commit)
   - `D` hypothesis (must be written as one, with the experiment that would settle it)
   A tier-D or offline-only statement may **not** be phrased as "works", "does", "cannot" or "proven". Compiles, lints, byte-compares
   and "the build is installed" prove nothing about behaviour.
9. **Control before claim.** Any claim of the form "X is the cause" needs a run where X is removed/present and everything else is
   identical (a vanilla negative control, the donor character as control, a good log as control). Say what the control was.
10. **A worse result is a revert, not progress.** If a change moves a crash earlier or adds a new one, restore the last bootable state,
    record the hypothesis as refuted in the graveyard, and do not try a third variant on the same premise.
11. **One state-changing change per hardware test.** If two things must change, ship two builds.
12. **Retractions are edits.** When you find an earlier statement is wrong, change it where it stands and add the correction to
    `graveyard.md` (claim, who, evidence that refuted it). Do not write "CORRECTED" beneath a still-wrong paragraph.
13. **Reports are immutable, indexes are not.** A console-run report goes to `evidence/<date>_<project>_<version>/RESULT.md`
    (what was installed with hashes, what the user did, what the log lines said, verdict) and is never rewritten afterwards.
    `STATUS.md` and `handbook/` are rewritten to reflect it.
14. **No handoff essays.** A handoff is `projects/<p>/STATUS.md` (max ~150 lines: what works, what is broken, next test, blockers)
    + links. If you write a new "read this first" document, delete or merge the old one.
15. **Dates absolute (2026-09-30), hashes full or 12+ chars, paths relative to workspace root.**

## C. How to work on a move / character (the standing method)

16. Follow `handbook/01_pipeline_overview.md`: classify the tier, pin sources into `refs/<donor>_<move>/` (URL, commit, date, sha256),
    list dependencies (bones, articles, work ids, effects, sounds, params, statuses), find what is missing, ask for dumps.
17. **User's "no shortcuts" standard (2026-09-29):** the mod owns what it uses. Custom statuses and motion kinds instead of cramming
    into an existing state; copied clips/articles/effects/sounds/params instead of calling another fighter's code at runtime; no
    stand-in sounds, no "hide it" hacks presented as done. If the proper route needs something reserved (raw-offset hook,
    rebuilding a global framework plugin), stop and hand back with the evidence; do not choose a cheaper route.
18. **Gate by costume** (`set_costume([6,7])` at install time) and verify with the log line + vanilla negative control.
19. Never force state per frame; never cast objects to another fighter kind; never equate numeric status/work ids across fighters.
20. Check "does the donor's own clip/script already do this?" (e.g. `untracked_meshes.py` on the original export) before adding code.
21. Check the shipped dumps for the game binary/NRO **before** declaring native behaviour unrecoverable.

## D. Building, installing, testing

22. **Framework plugins on the card are off limits**: `libsmashline_plugin.nro` (13.0.4 build `5f4091ee…`), `libarcropolis.nro`,
    `libarc_network.nro`, `libnro_hook.nro`, Skyline itself. Do not rebuild or overwrite them. (Reason: 0.10.0 rebuilt smashline and crashed at match start.)
23. Installing to the card is the agent's job, running the game is the user's. Use `tools/install-to-card.sh` (autodetects the card by
    contents, backs up, stages `.new`, verifies with `cmp`/`diff -r`, auto-rolls back). After every build compare packaged vs built hash.
24. Hand the user: what is on the card (hashes), a numbered test of at most ~12 steps including the vanilla control, the exact log lines
    that mean pass / fail, and where the log and crash report will be (`sd:/ultimate/<x>_log.txt`, `atmosphere/crash_reports/`).
    Ask for the log **from boot**.
25. Add file logging for anything that can crash (Skyline's TCP log loses its tail). Every diagnostic that can hang the console
    (reading arbitrary pointers, locks held over game calls) must be range-checked / lock-free.
26. Do not edit files while a build or console test of that project is in progress unless the change is the test. Changing `config.json`
    or the asset tree under a live test invalidates it.

## E. Session protocol

27. **Start**: read `AGENTS.md` (this), `projects/<p>/STATUS.md`, and the handbook files listed in `handbook/00_INDEX.md` for your task. Nothing else is required.
28. **End**: update `STATUS.md`, `CHANGELOG.md`, any handbook/fact entries, promote tools out of scratch, and list every file you created
    outside `scratch/` in your final message. Leave the tree with no `*.log`, `*.bak`, `build2/3/4` style leftovers in source dirs.
29. Do not copy dumps or assets into project trees "for convenience". Reference them through `paths.toml`. (Reason: `pyra_mythra_clone/editable`
    holds 2.9 GB of copies; C: reached 0 free.)
30. Disk is scarce (15 GB free). Never keep `target/` build caches outside `builds/.cache` (gitignored); never unpack Ghidra or other tool distributions inside the workspace.

## F. Things that are almost always wrong (learned the hard way)

- `MotionModule::motion_kind` proves a clip was requested, not loaded. Check the playing clip's end frame.
- Adding motion-list entries that name files the game/mod do not resolve makes the previous clip keep playing (no error).
- Grab boxes, articles, status ids: a live box or spawned article does not mean the engine acts on it. Log the consequence (`is_catch`, victim status), not the setup.
- A Data Abort with a smashline frame on the stack is usually not smashline's fault; read the frames above it.
- A log line that also appears in a known-good log is background noise.
- `Result code: 514` on SD create = try non-exclusive create.
- `#[patch]` with the same git source as the dependency is rejected by cargo.
- Do not derive addresses from public dumps (`0x710…`); they are NRO-relative or wrong version. Verify by instruction bytes on the 13.0.4 image before hooking.
- Dump text is evidence, not code (conversion errors, printed `frame(false,N)`, dropped args).
