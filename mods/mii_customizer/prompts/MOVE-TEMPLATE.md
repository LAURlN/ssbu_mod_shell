# MOVE-TEMPLATE - one borrowed move for the Mii Gunner (append the last two lines)

Revision 2 (2026-10-07, at the user's direction: permissive, trust the worker, the result is
the working move). The user pastes the block below into a worker and fills in the two lines
at the end. One worker = one move from one character. Several may run in parallel: every
write path contains the unit name and nobody edits the shared plugin. The coordinator
integrates and installs.

```
You are building one move for the SSBU mod mods/mii_customizer/ (workspace root = the folder
that contains AGENTS.md, mods/, gamedata/, tools/). Paths are relative to mods/mii_customizer/
unless marked workspace-relative.

GOAL: a Mii Gunner whose saved Mii has chosen this move in the mod's menu performs the move
named in the last two lines of this prompt, taken from the named character, and it plays like
the original: animation, hitboxes, timing, movement, effects, sounds, and whatever mechanics
the move has (charge, stages, angles, projectile, grab, landing, armour, ...). Every other
Gunner in the same match keeps the vanilla move. You are trusted to get there. Deliver the
finished move, not a feasibility study.

YOU MAY DO WHATEVER THE MOVE NEEDS. In particular, all of this is allowed and expected when
the move calls for it:
- custom status kinds and full status scripts (pre / init / main / exec / end, own main
  loops), own work variables, own params;
- retargeting or rebuilding the donor's animation for the Gunner's skeleton, adding bones or
  helper nodes, editing clips, new motion kinds;
- articles, weapons, projectiles and their models, motions, scripts and statuses;
- porting donor effects into the Gunner's effect bank, donor sounds into its sound bank,
  new params;
- reading and reusing anything from the user's other mod, mods/ssbu_mod_new/ (the G&W /
  Pyra / Mythra mod): it has already done all of the above for other fighters. Read its
  AGENTS.md and handbook/00_INDEX.md first, then copy its recipes, its tools and its code
  freely into your own folders. Its handbook says what works on the console and what failed;
  believe it over your own guesses.
Use your judgement and pick the route that gives the real move. Only stop short if a part is
far beyond what you can do in this task; then finish everything else, say exactly which part
is missing and why, and never fake it (no stand-in animation, no silent substitute, nothing
reported as done that is not).

WHAT ALREADY WORKS (read these first; they are your starting point, not a limit):
- research/P16-FTILT-MOVE.md with its banner, plugin/src/moves.rs,
  tools/move-package/build_p16_assets.py, evidence/2026-10-07_session4/RESULT_boot2.md and
  RESULT_boot3.md: Mii Brawler's forward tilt on a Gunner, working on the console. Owned
  motion kinds + owned clips + owned ACMD scripts, a Smashline status wrapper on agent
  `miigunner` that asks which saved Mii this fighter is, and a vanilla fallback.
- HANDOFF.md "Technical map", research/P12-FTILT-FACTS.md and the scripts in
  scratch/2026-10-07_P12-FTILT-FACTS/ and scratch/2026-10-07_P15-FTILT-TAKEOVER/: how motion
  lists, clips and ACMD scripts are read out of the game files; workspace tools/arc-extract
  gets any file out of the user's data.arc.

THE FEW FIXED POINTS (they exist so several workers can run side by side and so the result
can be installed next to the user's other mod; everything else is your call):
1. Names. ENTRY = the menu entry id of the move, one of: normal_jab normal_dash tilt_side
   tilt_up tilt_down smash_forward smash_up smash_down aerial_neutral aerial_forward
   aerial_back aerial_up aerial_down grab pummel throw_forward throw_back throw_up throw_down
   special_neutral special_side special_up special_down. DONOR = the character's internal
   fighter name (first column of workspace gamedata/mii_customizer/COORD-session3/list.txt).
   UNIT = <ENTRY>__<DONOR>, task id MV-<UNIT>. Prefix everything you add to the game with
   mc_<DONOR>_ / mc<DONOR> (motion kinds, clip files, script names, statuses, articles,
   effect and sound names) so two units never collide.
2. Where you write: moves/<UNIT>/ (source, generators, unit.json), research/moves/<UNIT>.md,
   evidence/moves/<UNIT>/, scratch/<today>_MV-<UNIT>/, builds/.cache/MV-<UNIT>-target/, and
   workspace gamedata/mii_customizer/moves/<UNIT>/ (everything extracted or generated from
   game files; game files never go into the mod tree). Do not edit plugin/, tools/, the
   status/handoff/install files, other units' folders, or anything in mods/ssbu_mod_new/:
   other workers are running next to you. Work on your own copy of plugin/ in your scratch
   folder and build it there (cargo-skyline offline as in build-plugin.sh, CARGO_TARGET_DIR =
   your target folder; do not run build-plugin.sh itself, it writes to the shared builds/).
3. Shared game files. A file that every Gunner move shares (the Gunner's motion_list.bin,
   effect bank, sound bank, param files, config.json) is never yours alone, and the user's
   other mod already replaces some of them. Do not ship a whole copy as "the" file: deliver
   your additions plus a script that applies them to any given base file (for the motion
   list: a reference list = vanilla + only your entries, as in build_p16_assets.py; the
   coordinator turns all units into one patch). Files only your unit uses (clips, article
   models, textures) ship as they are under package/.
4. Per saved Mii. Your code must act only for a Gunner whose saved Mii chose this unit, and
   fall back to the vanilla move when something it needs is not loaded (see moves.rs). Do
   not copy the saved-Mii lookup or the menu code; in your plugin copy call the existing
   ones, and in the report give the exact diff of your copy against plugin/ (that diff is
   how the coordinator merges you in).
5. The plugin loads on a 64 KiB stack: run `python tools/stack-frames/stack_frames.py <your
   nro>`; it must exit 0.
6. No commits, no emulator, no SD card, no installs, no spawning agents. Paths in what you
   write are relative. Use `python`; write scripts with the file tool, not shell heredocs.

DELIVER
- moves/<UNIT>/: the Rust module(s) of the move, unit.json (entry, donor, display name,
  everything the unit adds to the game, statuses it takes over or creates, what it needs
  merged into shared files), and the generator script(s) that rebuild every asset from the
  user's game files into your gamedata folder.
- A build of your plugin copy that compiles with your unit wired in (not a deliverable
  itself; it proves the code is real).
- evidence/moves/<UNIT>/check.py (run from the workspace root, exit 1 on mismatch): the
  generated files against a manifest, your motion entries and hashes against the names in
  the code, the values in your scripts against what you decoded from the donor.
- research/moves/<UNIT>.md, written early and kept current: how the move is built, what is
  exactly the donor's and what differs, the integration diff, a console test of at most 8
  steps with what the user should see (damage, timing, each mechanic, a second Gunner
  without the move), and anything you could not finish or could not check. Nothing has run
  in the game when you hand over, so say what the console still has to prove.
End your final message with: task id, DONE / PARTIAL / BLOCKED, the files you created, what
you ran and saw, what is left. The user only tells the coordinator "MV-<UNIT> finished".

MOVE:
FROM:
```
