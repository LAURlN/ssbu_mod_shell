# P16-FTILT-MOVE - the first borrowed move: Mii Brawler's forward tilt on a Mii Gunner, per saved Mii

Implementation task for Claude Opus 5.5 or GPT 6.1 Sol. Follow workspace AGENTS.md,
mods/mii_customizer/AGENTS.md and STATUS.md. No agents, commits, branches, emulator, SD
access; do not install anything; do not touch the framework plugins. Paths are relative to
mods/mii_customizer/ unless marked workspace-relative; create every folder INSIDE
mods/mii_customizer/. Use `python`; write scripts with the file tool (no heredocs). Write
research/P16-FTILT-MOVE.md early and keep it current. End with task ID, DONE/PARTIAL/BLOCKED,
changed files, what you could not verify.

This is a move copy, not a research project. The user has copied many moves between
fighters in their other mod, mods/ssbu_mod_new/, quickly and with a known recipe (add the
donor animation under an owned motion name, own the game / effect / sound / expression
scripts for it, play that motion when the move starts). Use that recipe. Read that repo's
AGENTS.md first, then the files research/P12-SCRIPT-ROUTE.md points to (Q2 registration API,
Q3 entry id inside a script, Q4 `tools/build_hero_neutral_b_assets.py` and the config.json
/ new-dir-files mechanism in `src/pgwr/build.py`). Reference only: never edit that repo,
and do not assume anything in it has been tried on a Mii. Do not re-measure what is already
measured; build, and let the console test find what is wrong.

## What exists

- Plugin `plugin/` (Rust, cargo-skyline, `build-plugin.sh`), current source = 0.7.0 (sort by
  name, `option` entries, loadouts version 3; built and reviewed, not yet run on the
  console; 0.6.0 is what is installed and works). It applies per-saved-Mii stat presets
  through a param hook and knows, per fighter object, which saved Mii it is: fighter kind 74,
  entry id -> saved-ID table (`resolve` / `read_player` in plugin/src/lib.rs, `logic::decide`).
  The in-game menu has a row "Forward Tilt" (menu entry id `tilt_side`, kind `slot`) that
  opens a character page; every row is greyed except the default until an
  `allow tilt_side <preset>` line exists in `menu.txt`; choosing an available row currently
  stores nothing (`slot_nothing_stored`). Design: research/P11-MENU.md and
  research/P14-SORT-OPTIONS.md, both with coordinator banners.
- Measured facts for this move, checked: research/P12-FTILT-FACTS.md. In short: Brawler's
  forward tilt has three motions (`attack_s3_hi`, `attack_s3_s`, `attack_s3_lw`; clips
  `c01attacks3hi/s/lw.nuanmb`, 56 frames, cancel frame 28, flags 0x0084), the Gunner one
  (`attack_s3_s`, 52 frames, cancel 37); the decoded Brawler `game_attacks3` (three hitboxes
  on `legr` / `kneer`, frame 6, 8.0%, 361, kbg 86, bkb 34, cleared at frame 9; hi 8.5%, lw
  8.3% with attack height calls) with every argument; effects `sys_run_smoke` and
  `sys_attack_arc` (common); sounds `se_miifighter_swing_m` and `seq_miifighter_rnd_attack01`
  (Brawler's own bank and sequence, NOT available to a Gunner); the clips drive exactly the
  node set of the Gunner's (same 71-bone skeleton); neither class overrides status
  `FIGHTER_STATUS_KIND_ATTACK_S3` (42). Disassembly of all sixteen scripts and the tables are
  under workspace gamedata/mii_customizer/P12-FTILT-FACTS/.
- Script framework on the console: the user's Smashline build for 13.0.4
  (`libsmashline_plugin.nro` `5f4091ee...`); crates pinned as in
  mods/ssbu_mod_new/src/pgwr/plugin/Cargo.toml / Cargo.lock (smashline `be3ef308...`). A
  compile-only spike that registers a `miigunner` script and reads the entry id is in
  scratch/2026-10-07_P12-SCRIPT-ROUTE/spike/ (it built offline).

## What to build (version 0.8.0)

Two saved Mii Gunners in one match: Gunner A, set to "Forward Tilt: Mii Brawler" in the
menu, performs Mii Brawler's forward tilt - Brawler's animation, hitboxes, timing (cancel
frame 28), effects, and the angled versions if you can carry them (see R3); Gunner B keeps
the Gunner's own forward tilt, untouched. The choice is made in the existing menu, stored
per saved Mii, applied without a reboot, and survives a reboot.

Requirements:
R1. Per object, not per fighter kind. Files are shared by every Gunner, so the donor move
    lives under OWNED names (owned motion kinds, owned clip file names, owned script names)
    next to the vanilla ones, and code decides per fighter object which motion a forward
    tilt plays. A Gunner whose saved Mii has no choice, an unsaved Mii (ID 0), a CPU or any
    unknown case runs the vanilla move with the vanilla scripts, byte for byte the path the
    game takes today. Vanilla `attack_s3_s` and its four scripts are not replaced.
R2. The project's rules for moves (mod AGENTS.md): no fighter-kind casts, no borrowed donor
    state, no forced per-frame status changes, no placeholder assets, no hidden failure
    presented as completion. Choose the lightest mechanism the other mod has proven for
    "play another motion for this move" and say why; if you need a status wrapper for
    ATTACK_S3 on agent `miigunner`, call the original for everything you do not change.
R3. Angled variants: Brawler has up and down angles, the Gunner has none. Preferred: all
    three as owned motions, selected the way the common status selects them for Brawler
    (find out how the angle is chosen; if the common code only looks up motions by fixed
    kind hashes, say what that means for owned names). Acceptable reduction for this build:
    the straight version only, stated plainly in the report.
R4. Sounds: Brawler's swing sound and attack-voice sequence are not loadable by a Gunner
    today. For this build use the Gunner's own equivalents (the voice is the Mii's own
    voice in either class; name the labels you chose and why) and list it in the report as
    a known difference from the donor. Do not ship or merge sound banks in this task; add
    one paragraph on what loading the donor's sound would take.
R5. Menu and storage. `allow tilt_side miifighter` in `menu.txt` un-greys the "Mii Brawler"
    row on the Forward Tilt page. Deciding it stores the choice; deciding row 0 (Mii Gunner)
    removes it; the main page row shows "Forward Tilt: Mii Brawler"; cursor and tick start
    on the stored choice. Loadout file: stay in `mc_loadouts 3`, new line
    `<id> slot <entry_id> <preset_name>`, same writer rule as the option lines (version 3
    only when such a line exists), rejected and logged when the entry or preset is unknown
    or the pair is not implemented.
R6. The plugin holds the table of implemented (entry id, preset) pairs - today exactly
    (`tilt_side`, `miifighter`). An `allow` line for a pair that is not in that table is
    rejected at load with a reason, so the menu can never offer a move the code cannot
    perform. Write the table so the next move is one more row plus its scripts.
R7. Where the code lives is your call (this crate with the Smashline crates added at the
    other mod's pins, or a second NRO): choose what keeps the saved-ID lookup in one place
    and say what the plugin now needs from the framework at load, and what happens when the
    framework is absent (the stat presets and the menu must keep working).
R8. Game files. The package ships the rebuilt Gunner `motion_list.bin`, the owned clip(s)
    and whatever declaration the loader needs for added files, as an ARCropolis mod folder
    (name it `mii_customizer_moves`). Establish which motion directories and costume slots
    a Mii Gunner actually loads (only `c00`? the earlier catalogue task saw `c06`/`c07`)
    and cover them. These are files derived from the user's game: build them with a script
    from the user's own extracted data into workspace
    gamedata/mii_customizer/P16-FTILT-MOVE/package/, never into the mod tree; the mod tree
    gets the generator, the manifest (paths, sizes, hashes) and the Rust source.
R9. Switches and logging: an empty file `sd:/ultimate/mii_customizer/moves_off` disables
    every move feature at load (menu rows greyed again, vanilla moves); bounded, flushed log
    lines: at load what was registered; per match start for each Gunner which move set it
    resolved to (`mc|MV|...|id=..|tilt_side=miifighter` or `default`); the first few times
    the owned motion is actually started for a fighter.
R10. Housekeeping while you are in the plugin: replace the raw NUL byte in the `MC_MINUS`
    literal in plugin/src/editor.rs (about line 621) with the escape, and in `handle_sort`
    remove the slice indexing and name the literal offset 0x158.

## Deliver

- Plugin 0.8.0 via build-plugin.sh in builds/0.8.0-moves/ (NRO, MANIFEST.json, the
  session `menu.txt` = builds/0.7.0-menu/session/menu.txt plus the `allow` line), the
  package generator and its manifest, the generated package under the gamedata path above.
- Host tests for the new parser, storage and table logic (the existing 47 + 35 + 4 + 16
  must still pass; runners: scratch/2026-10-06_P11-MENU/run_host_test.sh,
  scratch/2026-10-07_coordinator/names_test.rs,
  scratch/2026-10-07_P14-SORT-OPTIONS/host_test.rs). A check script
  evidence/P16-FTILT-MOVE/check_p16.py: the package against its manifest; the rebuilt
  motion list parses and differs from the original only by the added entries; every owned
  hash in the Rust source equals the hash in the motion list; the hitbox values in the Rust
  scripts equal the decoded table of P12-FTILT-FACTS; the NRO against the manifest; negative
  controls; exit 1 on mismatch.
- Report research/P16-FTILT-MOVE.md: the mechanism in half a page; what is copied exactly
  and what differs from the donor (sounds, angles, anything else); a console test of at
  most 8 steps (Gunner A with the move against Gunner B without: look, hit, damage numbers
  in training mode against the values above, cancel timing, the angled inputs, a CPU
  Gunner, removing the choice, a reboot) with the log lines for each; failure patterns;
  rollback (0.7.0 or 0.6.0 NRO, delete the `mii_customizer_moves` folder, `moves_off`); a
  plain list of what is tier D - which is everything in the game until the user runs it.

Not in scope: other moves or donors, swords, sound banks, integer parameters, Lua, layout.

Exclusive writes: plugin/, build-plugin.sh, builds/0.8.0-moves/, builds/.cache/,
research/P16-FTILT-MOVE.md, evidence/P16-FTILT-MOVE/, scratch/2026-10-07_P16-FTILT-MOVE/,
tools/move-package/ (if you make the generator reusable), workspace
gamedata/mii_customizer/P16-FTILT-MOVE/.
