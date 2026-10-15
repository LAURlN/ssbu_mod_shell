# Mii Customizer handoff - 2026-10-07 (revision 5)

For the model that takes over coordination of the user's Mii Gunner customization mod. Read
this first, then the workspace `AGENTS.md`, this mod's `AGENTS.md`, `STATUS.md` (task table
and the "Next user action" block at its end), the top section of `CURRENT_INSTALL.md`, and the
sections of `research/COORDINATOR-2026-10-04.md` dated 2026-10-07. Read task reports only as
needed. This file replaces every earlier handoff.

Paths are relative to `mods/mii_customizer/` unless marked workspace-relative.
Evidence tiers: A console, B offline measurement, C pinned source, D hypothesis.

## 1. Goal, and what the user wants now

A SSBU 13.0.4 mod: in the game's Mii maker, give a saved Mii Gunner other characters' stats
and, next, other characters' moves, saved per fighter. No roguelike, no PC port.

The user's direction as of 2026-10-07, in order:
1. The menu foundation is what they are using and polishing (done items in section 4).
2. Next real step: the first borrowed MOVE. Coordinator decision (reversible, said to the
   user): Mii Brawler's forward tilt on a Gunner, per saved Mii, because it is one stage
   and needs no weapon.
3. A "Sword" option: the selected sword is visible only during sword moves and used for all
   of that fighter's sword moves with its effects. Menu side built (0.7.0); match side is
   research (P14-SWORD-FACTS).
4. Later, "once the foundation is working, we'll go through the characters one by one":
   per character and per move, how feasible it is on a Gunner (skeleton match, weapons,
   mechanics). The user gave examples: Pyra/Mythra moves fine except down special; Steve
   hard throughout; any normal from a character with the Gunner's bone structure is easy.
   Do NOT filter the character list now; P14-LIST-PLAYABLE is parked.

## 2. How the work is organised

- You coordinate; you do not dispatch. You scope bounded tasks and write prompts; the user
  starts workers by hand and tells you when they are done. Do not spawn agents.
- The user cannot open the prompt files: **paste every prompt in full in chat, in a code
  block**, and also save it under `prompts/`.
- Workers: up to three Space Bunny Alpha (Freebuff) at once; GPT 6 Luna (the user offered
  "as many as you see fit" on 2026-10-07); Claude Opus 5.5 / GPT 6.1 Sol are scarce.
  Observed on 2026-10-07: Alpha does long offline fact tasks well but two of them stopped
  or ran for hours without writing their report; one Luna delivered a clean script task,
  another came back partial on native reverse engineering. Give native RE and plugin work
  to a premium model or do small pieces yourself.
- The coordinator has made small plugin changes itself this session (0.5.1 probe rule,
  0.5.2 names, 0.6.0 Minus entry) with host tests and a console test each. That worked and
  saved premium quota; keep such changes small and say what was not checked.
- After each round: read the reports, rerun their check scripts from the workspace root,
  re-read key instructions yourself, put corrections in a coordinator banner at the top of
  the report, then update `STATUS.md`, `CHANGELOG.md`, `CURRENT_INSTALL.md` (when a package
  changes) and append a dated section to `research/COORDINATOR-2026-10-04.md`.
- Reply to the user briefly and in plain language; they do not read the reports.

Practical traps:
- Bash heredocs that contain Python or prompts with quotes break. Write files with the file
  tool and run them (`scratch/2026-10-07_coordinator/` has every script of this session).
- Use `python`. Check scripts run from the workspace root; those that disassemble need
  `PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python`. The disassembler is
  `mods/mii_customizer/scratch/2026-10-04_P1-ID-REVIEW/d.py win <addr> <n>` (a worker once
  looked for it under `mods/ssbu_mod_new/`).
- Game-derived files go under workspace `gamedata/mii_customizer/<task>/`, never in the mod
  tree. Check the workspace root for stray files after each round (clean so far).
- `plugin/src/editor.rs` contains a raw NUL byte in the `MC_MINUS` literal (line ~621), so
  `grep` needs `-a`. Tidy it with the next plugin change.
- The plugin loads on a 64 KiB stack. Run `python tools/stack-frames/stack_frames.py <nro>`
  on every build; never hold a `Menu` or `Table` by value (use `::boxed()`).
- `pyra_gamewatch_reskin` ships files for most fighters, including the Gunner's
  `motion_list.bin`. Never ship a whole shared file; ship an ARCropolis patch
  (`motion_list.motdiff` from `tools/move-package/motdiff`) and read
  `ultimate/arcropolis/conflicts.json` after a boot.
- Do not read inside `mods/ssbu_mod_new/` without first reading its `AGENTS.md`; never edit
  it. Do not run the emulator. No commits (the workspace is not a git repo).

## 3. The SD card

Workspace rule: never install yourself. Practice in this project: the user mounts the card
(drive `E:`, label "SWITCH SD") and says "install" in chat; then the coordinator copies the
package files, verifies sha256 on the card, renames the old log, and records it. Every
install needs the card mounted AND a go-ahead in the current conversation for that package.
Reading the mod's own log and `loadouts.txt` off a mounted card is fine. Leave everything
else alone: the framework plugins (Skyline, ARCropolis, `libsmashline_plugin.nro`
`5f4091ee...`, arc_network, nro_hook, one_slot_eff) and `ultimate/mods/pyra_gamewatch_reskin`.

Card paths: plugin `atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmii_customizer.nro`;
data `ultimate/mii_customizer/` (`presets.txt`, `list.txt`, `names.txt`, `menu.txt`,
`loadouts.txt`); edit script `ultimate/mods/mii_customizer_ui/`; log
`ultimate/mii_customizer_log.txt`. Switch files (empty files in `ultimate/mii_customizer/`):
`ui_off`, `text_off`, `minus_off`.

On the card now (since 2026-10-07 evening, not yet run): **plugin 0.8.0** (third build `0193ba5f...`; history in `evidence/2026-10-07_session4/RESULT_boot1.md` and `RESULT_boot2.md`),
`ultimate/mods/mii_customizer_moves/` (P16 package), `menu.txt` with 25 entries and one
`allow`, the 0.6.0 edit script (`c50b9764...`), `names.txt`, wide presets, the 86-row
`list.txt`, `loadouts.txt` as the plugin saved it (three saved Miis have presets).

## 4. What works on the console (tier A)

- Per-saved-Mii stat presets (41 float stats of any of 94 fighters) applied in matches,
  several Miis at once, saved by the plugin and read back after a reboot.
- The mod menu inside the Mii maker, drawn on the native headgear list: a main page (one
  row per `menu.txt` entry, literal text, "Stats: Kirby" style current values), character
  pages per entry, greyed rows for unavailable choices, page changes by restarting the
  headgear state in place, the Mii's headgear and working record unchanged by any visit.
- Entry: Minus on the edit menu (plugin reads nn::hid, raises the Lua global `MC_MINUS`
  through `0x33750a0`, the edit script leaves with exit value 7). Button tip "Minus
  Advanced Options" replaces the Favourite tip.
- Never exercised: way in B (ZL/ZR), `text_off`, `ui_off`, `minus_off`, CPU players, more
  than two players, other modes.
- Known gap the user noticed: Kirby's extra jumps do not come with Kirby's stats (integer
  parameter, different getter; see section 6).
- Unknown: which other plugin hooks the game's text setter `0x37a22f0`. 0.5.1+ accepts
  that hook; text goes through it without trouble.

Session records: `evidence/2026-10-07_session3/` (`RESULT_boot1.md`, `RESULT_boot2.md`,
logs of the 0.5.2 and 0.6.0 runs).

## 5. Waiting right now

| item | state | what to do |
|---|---|---|
| **0.8.0-moves** (P16, contains 0.7.0) | reviewed and **INSTALLED 2026-10-07 evening**, never run | wait for the user's run of the eight steps at the top of `CURRENT_INSTALL.md`, then read the log off the card and write `evidence/2026-10-07_session4/RESULT.md` |
| **0.7.0-menu** (P14-SORT-OPTIONS: sort by name on character pages, `option` entry kind with the Sword page, loadouts version 3) | never installed on its own; shipped inside 0.8.0 | (as written before the install:) install on the user's go-ahead; eight test steps and expected log lines are at the top of `CURRENT_INSTALL.md`; read the coordinator banner in `research/P14-SORT-OPTIONS.md` first (label/order mismatch risk, one-row list, invented log lines in the worker's own test plan) |
| **P12-FTILT-FACTS** (measured contents of Brawler's forward tilt) | DONE by the takeover worker (P15), check rerun exit 0, coordinator banner | reference for P16 |
| **P16-FTILT-MOVE** (the first borrowed move, plugin 0.8.0) | DONE, reviewed (coordinator banner in the report), installed | (as written before:) review when it returns: rerun its checks and host tests, read the per-object decision and the vanilla fall-through, then package a console test with two Gunners. It builds on the 0.7.0 sources, so install and test 0.7.0 first if the user has not |
| **P14-SWORD-FACTS** (sword model, visibility, trails; ways a Gunner could show a sword) | report says DONE (13:00); **not reviewed** | rerun `evidence/P14-SWORD-FACTS/` check, read, add a banner; it feeds the first sword move, not P16 |
| **P14-LIST-PLAYABLE** | PARKED by the user; unreviewed; it edited `tools/stat-presets/` | nothing, unless the user returns to it; if the preset tool is used again, review those edits first |

## 5b. Move units (since 2026-10-07 night)

0.8.0 works on the console (`evidence/2026-10-07_session4/RESULT_boot3.md`). The user now
starts move workers from `prompts/MOVE-TEMPLATE.md` (revision 2: the user
wants these prompts permissive and outcome-first; workers may build statuses, retarget
animation, add articles, port effects and sounds; do not reintroduce stop-condition gating); each delivers `moves/<UNIT>/` (unit.rs,
unit.json, build_assets.py), `research/moves/<UNIT>.md`, `evidence/moves/<UNIT>/check.py` and
assets under workspace `gamedata/mii_customizer/moves/<UNIT>/`, and never edits `plugin/`.
Coordinator's job per batch: rerun each check, read each unit.rs, wire units into the plugin
(dispatcher per status kind, donor looked up from the stored slot, `IMPLEMENTED_MOVES` rows,
`allow` lines in `menu.txt`), merge all units' added motion-list entries into ONE
`motion_list.motdiff` and one `config.json`, stack-frame check, install on the user's word.

## 6. What comes next (coordinator's plan, D)

1. **First borrowed move** (premium task, written 2026-10-07 as `prompts/P16-FTILT-MOVE.md`
   after the user pointed out that move copies are routine in their other mod and should
   not be treated as research: the prompt says build with that mod's recipe and let the
   console find what is wrong). Inputs:
   `research/P12-SCRIPT-ROUTE.md` (done, accepted: the user's Smashline build on the card
   can register ACMD and status scripts for agent `miigunner`; a script can reach the entry
   id, which is what this plugin's saved-ID lookup needs; originals can be called; an added
   motion needs the clip, a rebuilt `motion_list.bin` and its scripts; nothing Mii-specific
   found; all D for Miis), the forward-tilt facts, and the sword facts for what a later
   sword move adds. Shape to ask for: Gunner A set to "Forward Tilt: Mii Brawler" plays
   Brawler's animation with Brawler's hitboxes, effects and sounds; Gunner B in the same
   match keeps its own; choice made on the existing `slot` page (an `allow tilt_side
   miifighter` line un-greys the row) and stored per saved Mii. Open design points to settle
   in that prompt: whether the move code lives in this plugin crate or a second NRO built
   against the Smashline crate (`be3ef308`, as the other mod pins it); the loadout key for
   a slot choice (P11-MENU proposed `<id> slot <entry_id> <preset>`; 0.7.0 already took
   `mc_loadouts 3` for `option` lines, so define slots within version 3); ARCropolis files
   for the added motion (first time this mod ships fighter files). Project rules for moves
   are in this mod's `AGENTS.md` ("New moves must own their dependencies...").
   Expect a console gate: two Gunners, one with the move.
2. **Integer stats** (`research/P11-INT-PARAMS.md`, done): the integer getter is the thunk
   `0x4e53a0` in slot +0x250, twin of the hooked `0x4e53e0`. `jump_count_max` is the field a
   player notices. Open: what the game does when a Gunner has more jumps than jump motions.
   Small plugin task plus one console check; can ride with another plugin change.
3. **Per-character, per-move feasibility** pass, when the user asks for it (section 1.4).
4. Housekeeping for the next plugin task: adapt one check script to the current plugin
   version (`evidence/P14-SORT-OPTIONS/check_p14.py` is the newest), remove the NUL byte and
   the indexing / literal offset in `handle_sort`, look at why the NRO doubled to 237 KB.

## 7. Technical map (details are in `STATUS.md` and the reports)

- **Game image**: workspace `gamedata/ssbu-13.0.4/main.bin`, flat, address == file offset ==
  Skyline text offset, sha256 `f70c97d2...7613`.
- **Plugin**: crate `plugin/`, built by `build-plugin.sh` (cargo-skyline, offline; workspace
  `kb/reference/cargo-skyline.md`) into `builds/<version>-menu/`. Sources: `lib.rs` (load,
  stat hook at `0x4e53e0`, file loading, log), `editor.rs` (the six UI hooks, pages, Minus),
  `ui.rs` (sites, probes, offsets, mode state machine), `menu.rs`, `list.rs`, `names.rs`,
  `loadout.rs`, `preset.rs`, `logic.rs`. Design and proofs: `research/P11-MENU.md`; later
  additions are described only in the coordinator log and in `research/P14-SORT-OPTIONS.md`.
  No source snapshots exist per version (no git): the manifests hold hashes only.
- **Host tests**: `scratch/2026-10-06_P11-MENU/run_host_test.sh` (47 + 35),
  `scratch/2026-10-07_coordinator/names_test.rs` (4),
  `scratch/2026-10-07_P14-SORT-OPTIONS/host_test.rs` (16).
- **Edit script**: `tools/lua-src/` (byte-identical reconstruction, generators per variant;
  the installed one is `make_minus_source.py` -> `builds/0.6.0-menu/`, built and checked by
  `builds/0.6.0-menu/build_edit_script.py`). Compiler `tools/luac53-game/`.
- **Card data files**: formats `mc_presets 1`, `mc_list 1`, `mc_names 1`, `mc_menu 1`
  (kinds `stats`, `slot`, `option`), `mc_loadouts 2` / `3`. Generators:
  `tools/stat-presets/`, `scratch/2026-10-07_coordinator/make_session3.py`, `make_names.py`.
  Session copies: workspace `gamedata/mii_customizer/COORD-session3/`,
  `builds/0.7.0-menu/session/menu.txt`.
- **Other mod as reference**: `mods/ssbu_mod_new/` (move scripts, added motions, Smashline
  build for 13.0.4). Reference only.

## 8. Where things are

`STATUS.md` (state; long, the end is current) - `CURRENT_INSTALL.md` (packages, test plans,
what is on the card; newest on top) - `CHANGELOG.md` - `research/COORDINATOR-2026-10-04.md`
(every review and decision with reasons) - `prompts/` (every prompt) - `research/` (one
report per task, coordinator banners on top) - `evidence/<task>/` (check scripts, raw
output, console logs) - `scratch/<date>_<task>/` - `builds/` (packages with manifests) -
`plugin/` - `tools/` - workspace `gamedata/mii_customizer/` (everything extracted or
generated from game files).
