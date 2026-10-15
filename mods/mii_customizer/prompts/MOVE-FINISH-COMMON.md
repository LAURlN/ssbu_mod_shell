# MOVE-FINISH-COMMON - shared brief for workers finishing a move unit (2026-10-08)

Written by the coordinator for subagents it starts itself (the user asked for this on
2026-10-08). Each worker gets this file plus a short task of its own. Paths are relative to
`mods/mii_customizer/` unless marked workspace-relative (workspace root = the folder holding
`AGENTS.md`, `mods/`, `gamedata/`, `tools/`).

## What the user wants

A Mii Gunner whose saved Mii chose the move in the mod's menu performs the donor character's
move and it plays like the original: animation, hitboxes, timing, movement, effects, sounds,
weapon in hand if the donor holds one, and every mechanic the move has (stages, charge,
second input, projectile, landing, ...). Every other Gunner keeps the vanilla move.

Earlier workers stopped early and handed back PARTIAL reports and stand-ins. The user's
words: "I want to send a prompt and get back the working move", "they should actually
finish". So: **finish it.** You are trusted. Custom statuses, own work variables, retargeted
or rebuilt clips, added bones or helper nodes, articles and weapon models, ported effects
and sounds, new params are all allowed and expected where the move needs them. Do not hand
back a study, a plan or a list of reasons. Stop short of a part only when it is far beyond
what can be done here; then finish everything else, state exactly which part is missing and
why, and never fake it (no stand-in animation or sound presented as the donor's, nothing
reported as done that is not).

Nothing can be run in the game by you. "Finished" therefore means: the code and every asset
exist, the plugin copy builds, your check passes, and nothing the move needs is left out or
substituted. Say plainly what only the console can prove.

## What you can read (all of it is yours to use)

Game dump and extracted files (workspace-relative):
- `gamedata/ssbu-13.0.4/data.arc` - the user's full 13.0.4 archive. Any file comes out with
  workspace `tools/arc-extract` (see `kb/playbooks/extracting-single-files-from-data-arc.md`).
  Write extracted files only under `gamedata/mii_customizer/moves/<UNIT>/`.
- `gamedata/ssbu-13.0.4/main.bin` - the decompressed game executable (status constants,
  motion names, native code). `gamedata/ssbu-13.0.4/files/` - files already extracted
  (fighter, effect, sound, ui).
- `gamedata/mii_customizer/` - everything earlier mii_customizer tasks extracted and
  decoded: `P12-FTILT-FACTS/` (status registration tables, decoders' output),
  `P16-FTILT-MOVE/`, `moves/<UNIT>/` of every unit (donor clips, scripts, NROs already
  pulled), `COORD-session3/list.txt` (internal fighter names).
- `dump/` - the raw dump. Read-only, and you should not need it.

The user's other mod, workspace `mods/ssbu_mod_new/` (G&W / Pyra / Mythra; it has ported
many donor moves onto another fighter and tested them on the console). Read its `AGENTS.md`
first (it governs reading there), then `handbook/00_INDEX.md` and the pages for your job:
`04_motion_lists_animation`, `05_acmd_porting`, `06_statuses`, `07_articles`,
`08_visibility_models`, `09_params_prc`, `10_arcropolis_config_json`, `11_smashline_skyline`,
`12_native_offsets_13_0_4_only`, `graveyard.md` (what failed on the console; believe it).
- `refs/<donor>_<move>/` - pinned donor material per ported move, including decoded scripts
  and status decompiles. Existing: `cloud_attack_air_f`, `snake_attack_hi3`, `snake_grenade`,
  `snake_throw_lw`, `chrom_jab`, `mythra_ftilt_chrom`, `pikachu_attack_air_b`,
  `littlemac_attack_s4`, `lucas_attack_lw4`, `robot_attack_lw3`, `brave_special_n/s`,
  `diddy_monkey_flip`, `donkey_cargo`, `gaogaen_throw_b`, `ness_throw_b`, `younglink_neutral_b`.
- `dumps/` and `dumps/decoded/` - decompiles and disassembly helpers (Ghidra output of
  `lua2cpp_*.nro` status functions, `arc_files.tsv`, ACMD snapshots); `dumps/INDEX.md`.
- `src/pgwr/plugin/` - the working Rust plugin (custom statuses, articles, weapons, effect
  and sound handling), `src/pgwr/assets/`, `src/pgwr/tools/`, and `tools/` (audits,
  generators, effect and sound merge tools, `constmap.py`, `findhash.py`, `hashscan.py`).
Copy recipes, tools and code from there freely into your own folders. Never write there.

This mod: `HANDOFF.md` ("Technical map", section 5b "Move units"), `plugin/src/moves.rs`
(`owned_status_main`, `mii_chose`, the vanilla fallback), `plugin/src/unit_smash_up.rs` and
`moves/smash_up__fox/` (a finished unit with two statuses), `moves/tilt_up__miifighter/`,
`research/P16-FTILT-MOVE.md`, `tools/move-package/` (motion list builder, `motdiff`),
`scratch/2026-10-07_MV-aerial_forward__cloud/` (a clip retargeted to the Gunner skeleton with
the other mod's recipe), `tools/stack-frames/`.
Console facts that cost a boot each: the other mod replaces the Gunner's `motion_list.bin`,
so whole copies of shared Gunner files get dropped by ARCropolis (first mod wins); patch
files (`.motdiff`, `.prcx`, `.xmsbt`) are applied on top of whichever file loads. The
plugin's load thread has a 64 KiB stack.

## Fixed points (so workers can run side by side and the result can be installed)

1. UNIT = `<ENTRY>__<DONOR>`, task id `MV-<UNIT>`. Prefix everything you add to the game
   with `mc_<DONOR>_` / `mc<DONOR>` (motion kinds, clip files, script names, statuses,
   articles, effect and sound names).
2. Write only in: `moves/<UNIT>/`, `research/moves/<UNIT>.md`, `evidence/moves/<UNIT>/`,
   `scratch/2026-10-08_MV-<UNIT>/` (the unit's older scratch folder is yours too),
   `builds/.cache/MV-<UNIT>-target/`, workspace `gamedata/mii_customizer/moves/<UNIT>/`.
   Game-derived files go only into that gamedata folder. Do not edit `plugin/`, `tools/`,
   `STATUS.md`, `HANDOFF.md`, `CURRENT_INSTALL.md`, `CHANGELOG.md`, other units' folders, or
   anything in `mods/ssbu_mod_new/`. Other workers run next to you right now.
3. Plugin: copy `builds/.cache/plugin_base_0.10.0/` (the current source: three Brawler
   tilts and Fox's up smash integrated) into your scratch folder, wire your unit in there
   and build it offline the way `build-plugin.sh` does, with `CARGO_TARGET_DIR` set to
   `builds/.cache/MV-<UNIT>-target/`. Do not run `build-plugin.sh` itself. Call the existing
   saved-Mii lookup (`mii_chose` / `owned_status_main`); do not copy it. Act only for a
   Gunner whose Mii chose this unit and fall back to vanilla when a needed motion is not
   loaded.
4. Shared Gunner files (motion list, effect bank, sound bank, param files, `config.json`):
   never ship a whole copy as "the" file. Deliver your additions and a script that applies
   them to any base file (motion list: a reference list = vanilla + only your entries, as
   `tools/move-package/build_p16_assets.py` does). Files only your unit uses (clips, article
   models, textures) ship as they are under your gamedata `package/`.
5. `python tools/stack-frames/stack_frames.py <your nro>` must exit 0.
6. No commits, no emulator, no SD card, no installs, no downloads of game content, no
   spawning agents. Relative paths in everything you write. Use `python`; write scripts with
   the file tool, not shell heredocs.

## Deliver

- `moves/<UNIT>/`: `unit.rs` (plus further modules if needed), `unit.json` (entry, donor,
  display name, everything added to the game, statuses taken over or created, what must be
  merged into shared files), `build_assets.py` (rebuilds every asset from the user's game
  files into your gamedata folder).
- Your plugin copy building with 0 errors, and the stack check passing.
- `evidence/moves/<UNIT>/check.py` (run from the workspace root, exit 1 on mismatch):
  generated files against a manifest, motion entries and hashes against the names in the
  code, script values against what you decoded from the donor.
- `research/moves/<UNIT>.md` rewritten to the current truth (replace stale PARTIAL text, do
  not append beneath it): how the move is built, what is exactly the donor's and what
  differs, the exact diff of your plugin copy against `builds/.cache/plugin_base_0.10.0/`,
  a console test of at most 8 steps with what the user should see, what the console still
  has to prove.

Your final message goes to the coordinator, not the user. Make it short and exact: task id;
DONE / PARTIAL / BLOCKED; files created; the commands you ran and what they printed (build
result, check exit code, stack check); every part of the move that is not the donor's or is
missing, with the reason; what you could not check offline.
