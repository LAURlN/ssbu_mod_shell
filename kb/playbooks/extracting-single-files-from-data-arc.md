---
title: Getting single game files out of data.arc
summary: tools/arc-extract pulls any base-game file from gamedata/ssbu-13.0.4/data.arc by ARC path; output was byte-compared with ArcExplorer and arc-network copies
status: verified
tags: [dump, extraction, data-arc, gamedata, smash-arc]
updated: 2026-10-02
source: user request 2026-10-02; runs recorded in tools/arc-extract/README.md
---

## When to use

A task needs an original game file (effect bank, param, animation, model, UI file, sound bank)
that is not already pinned in the mod's `refs/`. Use this before asking the user to export
something in ArcExplorer and before waiting for the console (`fetch_arc_files.py` over
arc-network).

## Procedure

1. Find the exact ARC path: `grep` the path index
   `mods/ssbu_mod_new/dumps/decoded/arc_files.tsv` (590,711 paths, one per line).
2. Extract into `gamedata/` (never into `dump/`, `tools/`, `kb/` or a mod source tree):

   ```
   tools/arc-extract/target/release/arc-extract.exe --arc gamedata/ssbu-13.0.4/data.arc \
     --out gamedata/ssbu-13.0.4/files <arc path> ...
   ```

   Add `--index mods/ssbu_mod_new/dumps/decoded/arc_files.tsv` to extract a whole folder
   (`fighter/brave/param/`) or a `*` pattern. If the executable is missing, build it:
   `cd tools/arc-extract && cargo build --release`.
3. Record the printed sha256 where the file is used (the mod's `refs/<donor>_<move>/`), and say
   the source was `gamedata/ssbu-13.0.4/data.arc` (sha256 `ef615e671e1d...`).
4. `MISSING` means the path is not in the archive: check the spelling against the index, and
   remember that regional files need `--region`.

## Evidence

Verified 2026-10-02: `effect/fighter/eflame/ef_eflame.eff` extracted this way is byte-identical
to the user's ArcExplorer export, and `fighter/snake/motion/body/c00/c02attackhi3.nuanmb` matches
the sha256 of the copy pulled from the console. Full output: `tools/arc-extract/README.md`.

## Limits

- Unverified for all other files; two were compared.
- The user's ArcExplorer export (`[dumps] arc` in the mod's `paths.toml`) has gaps - its
  `fighter/brave/param/` folder is empty - so do not treat a file missing there as missing from
  the game.
- Building needs the GNU Rust toolchain (pinned in the tool's `rust-toolchain.toml`); this machine
  has no MSVC linker. See `kb/reference/local-machine.md`.
