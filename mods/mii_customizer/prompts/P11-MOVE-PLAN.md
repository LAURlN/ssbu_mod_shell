# P11-MOVE-PLAN - what the first borrowed move needs (research and plan, no implementation)

For Space Bunny Alpha. Offline research; nothing is built, installed or run. Follow workspace
AGENTS.md, this mod's AGENTS.md and STATUS.md. No agents, commits, emulator, SD access. Paths
are relative to mods/mii_customizer/ unless marked workspace-relative; create every folder
INSIDE mods/mii_customizer/; extracted game files go to workspace
gamedata/mii_customizer/P11-MOVE-PLAN/. Use `python`; write scripts with the file tool, not
heredocs. Create research/P11-MOVE-PLAN.md first and extend it as you go. End with task ID,
DONE/PARTIAL/BLOCKED, changed files, checks run, open questions.

Background. The mod lets a saved Mii Gunner take a character's stats, chosen in the Mii
maker (console, tier A). The next menu will list move slots (Jab, Forward Tilt, ...) and,
per slot, the characters whose move can be used; today none is implemented, so only the
default is selectable. Your task: establish what it takes to implement the FIRST one, so the
coordinator can scope it. Candidate: the jab (`normal_jab`, attack_11/12/13) of Mii Brawler
(`miifighter`) or Mii Swordfighter (`miiswordsman`) on Mii Gunner - same skeleton family,
which is why the project plan names the other Mii classes first.

The user's other project, mods/ssbu_mod_new/, ports moves between fighters. It is reference
only: BEFORE reading anything inside it, read mods/ssbu_mod_new/AGENTS.md, the relevant
projects/<p>/STATUS.md and the pages listed in handbook/00_INDEX.md, and follow its rules.
Do not edit it, do not copy its code or handbook text into this mod: link to the page and
state the fact with its evidence tier. Do not assume its ports support Miis.

Read first: this mod's AGENTS.md section Scope (new moves must own their dependencies and
state: no fighter-kind casts, no borrowed donor state, no forced per-frame status changes, no
placeholder assets), research/P1-DATASET.md, research/P1-CATALOG.md and its audit,
research/P3-SPECIAL-VARIANTS.md, workspace kb/INDEX.md.

Deliver, as facts with sources and tiers:

1. Inventory for the Gunner jab and for each donor's jab, from the extracted game files
   (workspace tools/REGISTRY.md for extraction; dump/ is read-only): motion entries and
   animation files, the game/effect/sound/expression script entries, the status kinds
   involved and what transitions between the three stages, hitbox and damage parameters and
   where they live, effects, sounds and any article or weapon the move uses, bones the
   animation drives that the Gunner skeleton lacks or has extra (the arm cannon). Sizes and
   hashes of every file named.
2. Mechanisms available on this console for each kind of dependency, with what is known to
   work and at which tier: file replacement through ARCropolis mod folders (A for UI files in
   this mod), motion list and animation additions, script replacement through the smashline
   plugin that is on the card (state the installed version if the workspace records it, what
   it can replace per fighter kind, and whether it can do so per saved Mii at run time), param
   overrides through this mod's own hook (A for floats). Say for each which per-Mii switch is
   possible: the move must apply to one saved Gunner and not to another in the same match.
3. The per-Mii problem stated precisely: which parts of a move are per fighter KIND in the
   game's data model (shared by every Gunner) and which can be chosen per fighter OBJECT at
   run time, and what that means for "Gunner A has Brawler's jab, Gunner B has its own".
4. Two or three candidate designs for the first move, each with: what is added to the game
   files, what code runs where, how the per-Mii choice reaches it (this mod's loadout store
   keyed by saved ID is available in a hook), what could break (other Gunners, CPU, online is
   out of scope), how it honours the Scope rules above, and the smallest console experiment
   that would show it works. Rank them and say which facts are missing for each.
5. A comparison table Brawler vs Swordfighter as first donor, and whether another slot
   would be a cheaper first move than the jab, with reasons from the inventory.

Limits to state plainly: nothing is run; anything about run-time behaviour is tier D unless a
cited console result (A) or pinned source (C, URL + commit) says otherwise. No downloads of
game content; tool or framework sources may be cited from what is already in the workspace.

Check script evidence/P11-MOVE-PLAN/check_p11_move_plan.py: re-reads every file hash, size
and entry count the report cites; negative controls; exit 1 on mismatch; run it once more
AFTER your last edit and paste that output.

Exclusive writes: research/P11-MOVE-PLAN.md, evidence/P11-MOVE-PLAN/,
scratch/2026-10-06_P11-MOVE-PLAN/, workspace gamedata/mii_customizer/P11-MOVE-PLAN/.
