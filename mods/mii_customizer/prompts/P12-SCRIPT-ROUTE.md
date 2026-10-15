# P12-SCRIPT-ROUTE - how mod code can own a Mii Gunner move script per fighter object (facts only)

For Space Bunny Alpha. Offline: reading sources, binaries and existing notes; one compile-only
experiment. Nothing is run in the game, nothing installed. Follow workspace AGENTS.md, this
mod's AGENTS.md and STATUS.md. No agents, commits, emulator, SD access, no system-wide
installs, no edits to framework plugins. Paths are relative to mods/mii_customizer/ unless
marked workspace-relative; create every folder INSIDE mods/mii_customizer/. Use `python`;
write scripts with the file tool, not heredocs. Create research/P12-SCRIPT-ROUTE.md in your
first minutes and extend it after every answer. End with task ID, DONE/PARTIAL/BLOCKED,
changed files, checks run, open questions.

Background. This mod's plugin (plugin/, Rust, built by build-plugin.sh with cargo-skyline;
workspace kb/reference/cargo-skyline.md) hooks game functions directly and already knows, per
fighter object, which saved Mii it is (research/P7-PRESET-ENGINE.md section 2,
plugin/src/lib.rs: fighter kind 74, entry id -> saved-ID table). The next step is a borrowed
move: a Gunner whose saved Mii chose "Brawler forward tilt" must run other hitbox / effect /
sound scripts and another animation for that move than a Gunner that did not, in the same
match. research/P11-MOVE-PLAN.md sketches "register scripts for miigunner through Smashline
and branch on the saved ID inside them"; none of that is established for this mod. This task
collects the facts a designer needs. The user's other mod, mods/ssbu_mod_new/, replaces move
scripts for other fighters and is the reference: read its AGENTS.md first, then
handbook/00_INDEX.md and the pages it lists for ACMD/status scripts, motion additions and the
build; reference only, never edit it, and do not assume anything in it works for Miis.

Q1. What is on the console for scripts. From mods/ssbu_mod_new/CURRENT_INSTALL.md and its
    handbook (do not read the SD card): which script framework plugin(s) and versions are
    installed (Smashline or other), where that is recorded, and which crate version / git
    commit ssbu_mod_new builds against (Cargo.toml, Cargo.lock). Quote file and line.
Q2. The API as used there, with file:line examples: registering an ACMD game / effect /
    sound / expression script for a fighter; registering or wrapping a status function;
    calling the original script from a replacement (is that possible, and how); per-frame
    callbacks; how the fighter is named (agent name string or kind) and whether costume or
    other filters exist. For each: evidence tier in that repo (console-tested or not).
Q3. Inside such a script function: how to get from the function's argument to the
    BattleObjectModuleAccessor / the entry id, with file:line examples; and whether that
    yields what plugin/src/lib.rs needs for its saved-ID lookup (name the function there).
Q4. Motion change: how ssbu_mod_new plays a motion kind that the fighter's original
    motion_list.bin did not have (the handbook says added animations and motion entries work
    on the console): which tool rebuilds motion_list.bin, the config.json / new-dir-files
    mechanism, and the exact list of files one added motion needs. File:line and tier.
Q5. Mii specifics, by reading only: does anything in ssbu_mod_new or in the pinned framework
    source (if a local copy exists in a cargo cache or under mods/ssbu_mod_new/; do not
    download) treat Mii fighters differently (agent names `miifighter`, `miiswordsman`,
    `miigunner`; costume slots; custom special variants)? Say "not found" if not found.
Q6. Without the framework: how does the game itself pick the function for `game_attacks3`
    of a fighter? Describe, from the 13.0.4 lua2cpp_miigunner.nro extracted under workspace
    gamedata/mii_customizer/P11-MOVE-PLAN/ and existing notes, where the script hash ->
    function table lives and how it is filled (registration call sites, table layout), so a
    designer can judge whether a direct hook is an alternative. Addresses and words; no hook
    code.
Q7. Compile-only experiment. In scratch/2026-10-07_P12-SCRIPT-ROUTE/spike/ create a separate
    minimal plugin crate (NOT plugin/, and do not touch build-plugin.sh) that depends on the
    same framework crate version as Q1 and registers one ACMD game script for `miigunner`
    `game_attacks3` whose body reads the entry id and then does nothing else. Build it with
    cargo-skyline using a CARGO_TARGET_DIR under builds/.cache/p12-script-route/, offline
    first (`-- --offline`); if a crate is missing from the local cargo cache, stop that step
    and report which crate and version, do not fetch without saying so in the report. Record
    the command, exit code, warnings, NRO size and sha256, and the imported symbols of the
    NRO that the framework must provide at load. Do not stage it under builds/<version>/.
    A build that succeeds proves only that it compiles.
Q8. One table for the designer: each candidate mechanism (framework ACMD replacement with a
    branch; framework status wrapper; direct hook of the script lookup; motion change at
    status start) x what is console-proven in ssbu_mod_new / what is only read / what is
    unknown for Miis. No recommendation.

Deliver research/P12-SCRIPT-ROUTE.md (short answers first), evidence/P12-SCRIPT-ROUTE/ with
check_p12_script_route.py (re-reads every quoted file:line, every hash and every cited
instruction word; at least three negative controls behind `--neg`; exit 1 on mismatch; rerun
AFTER the last report edit and paste the output).

Rules: quote, do not paraphrase from memory; C tier needs repository + commit; anything about
behaviour in the game that this mod has not tested is D for this mod, whatever tier it has in
ssbu_mod_new. Do not copy ssbu_mod_new handbook text into this mod; cite path and line.

Exclusive writes: research/P12-SCRIPT-ROUTE.md, evidence/P12-SCRIPT-ROUTE/,
scratch/2026-10-07_P12-SCRIPT-ROUTE/, builds/.cache/p12-script-route/.
