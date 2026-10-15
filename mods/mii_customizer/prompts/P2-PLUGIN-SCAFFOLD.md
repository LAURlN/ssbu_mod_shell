# P2-PLUGIN-SCAFFOLD - a mod-owned Skyline plugin skeleton that builds and only logs

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md. Work only on the task below. No agents,
commits, branches, emulator, SD access, framework changes or edits to other workers'
files. Report exact inputs/hashes, commands, observed checks, failures and limits.
B is offline observation, C pinned source, D hypothesis; a successful build is not
runtime evidence. Coordinator owns STATUS/CURRENT_INSTALL/CHANGELOG/contracts.
Finish saved report and chat with task ID, DONE/PARTIAL/BLOCKED, changed files and
next experiment. All paths below are relative to mods/mii_customizer/ unless marked
workspace-relative. Create every folder INSIDE mods/mii_customizer/.

One goal: give this mod its own minimal Skyline plugin crate that compiles to an
NRO with the machine's existing toolchain and does nothing in the game except write
one identifying line to a log file. No hooks, no game function calls, no offsets.
This is build infrastructure for a later diagnostic. It is not installed and not
marked READY.

Read first: workspace-relative kb/reference/cargo-skyline.md,
kb/reference/local-machine.md and kb/reference/ssbu-modding-stack.md. Then, after
reading mods/ssbu_mod_new/AGENTS.md, its projects/pgwr/STATUS.md and
handbook/00_INDEX.md, read handbook/11_smashline_skyline.md and look at how
src/pgwr/plugin/ is laid out (Cargo.toml, Cargo.lock pins, .cargo config, the
build command its notes prescribe, how it logs to a file). That project is a
REFERENCE ONLY: copy no source files from it, change nothing in it, do not build
it, and do not reuse its target directory.

Build this:
- `plugin/` : a new crate, name `mii_customizer`, crate-type cdylib, depending only
  on `skyline` pinned to the exact git revision the old plugin's Cargo.lock uses
  (state the revision). No smashline, no skyline-smash, no other dependency unless
  the build cannot work without it; justify each one you add.
- `#[skyline::main(name = "mii_customizer")]` entry that writes exactly one line,
  `mii_customizer <version> loaded`, where version comes from Cargo.toml
  (`env!("CARGO_PKG_VERSION")`, start at 0.0.1). Write it with skyline's own
  logging macro AND append it to a file `sd:/ultimate/mii_customizer_log.txt`
  using only std/skyline file APIs the old plugin already uses successfully for its
  own log (cite the lines you modelled it on). File errors must be ignored, never
  unwrap or panic. No threads, no allocation-heavy work, no pointer reads.
- A build script or documented command, run from the workspace, that uses the
  installed cargo-skyline exactly as kb/reference/cargo-skyline.md prescribes, with
  the cargo target directory at `builds/.cache/plugin-target/` (not inside
  `plugin/`). Do not install any toolchain, do not run `cargo skyline install`,
  `run`, `listen` or anything that talks to a console or network device. Fetching
  the pinned crates through cargo is allowed (project-local dependency).
- On success copy the NRO to `builds/0.0.1-scaffold/libmii_customizer.nro` and write
  `builds/0.0.1-scaffold/MANIFEST.json` with: sha256 and size of the NRO, crate
  version, skyline revision, rustc and cargo-skyline versions, exact build command,
  and the statement "not installed, not tested on hardware".
- `plugin/README.md`: how to build, what the plugin does, what it does not do.

Checks to run and report with exit codes: the build itself; that the NRO exists and
starts with the expected NRO magic at the offset the format uses (state the offset
and what you read); that the built binary contains the version string and the log
path string; a second build from clean cache state is not required, but state
whether the NRO hash is stable across two consecutive builds.

If the build fails: record the exact command, the full error text in evidence, and
your best explanation. Try at most two distinct fixes that stay inside this crate
and the documented toolchain. Do not change global cargo/rustup configuration, do
not install software, do not touch the old mod. Then stop PARTIAL.

Do not: add any hook, call any game function, add install scripts, write to an SD
card or emulator directory, add config or save files, or describe the plugin as
working in the game. Add a kb note only if you learn a new fact about this
machine's toolchain; put it in the report as a suggestion for the coordinator
instead of editing workspace-level kb yourself.

Deliver research/P2-PLUGIN-SCAFFOLD.md with the commands, outputs, hashes and
limits.

Exclusive writes (all under mods/mii_customizer/): plugin/, builds/0.0.1-scaffold/,
builds/.cache/plugin-target/, research/P2-PLUGIN-SCAFFOLD.md,
evidence/P2-PLUGIN-SCAFFOLD/, scratch/2026-10-04_P2-PLUGIN-SCAFFOLD/.
