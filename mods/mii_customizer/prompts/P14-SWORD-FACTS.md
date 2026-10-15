# P14-SWORD-FACTS - what "a Mii Gunner holds the Mii Swordfighter's sword during sword moves" needs (facts only)

Research task, any capable worker (GPT 6 Luna or Space Bunny Alpha). Offline analysis of
extracted game files and binaries; nothing is executed, patched or installed. Follow
workspace AGENTS.md, mods/mii_customizer/AGENTS.md and STATUS.md. No agents, commits,
emulator, SD access. Paths are relative to mods/mii_customizer/ unless marked
workspace-relative; create every folder INSIDE mods/mii_customizer/; extracted or generated
game data goes to workspace gamedata/mii_customizer/P14-SWORD-FACTS/ (files earlier tasks
extracted, e.g. workspace gamedata/mii_customizer/P11-MOVE-PLAN/, are read-only for you).
Use `python`; write scripts with the file tool (no heredocs). Create
research/P14-SWORD-FACTS.md in your first minutes and extend it after every answer. End with
task ID, DONE/PARTIAL/BLOCKED, changed files, checks run, open questions.

Background. This mod lets a saved Mii Gunner take other characters' stats, and is preparing
to let it take other characters' MOVES, chosen per saved Mii in the Mii maker. The user now
asks for a "Sword" option: when a Gunner uses a borrowed sword move (first donor: Mii
Swordfighter), the selected sword - for now only the Mii Swordfighter's own - must be
visible in its hand ONLY during sword moves, and used for all of that fighter's sword moves
together with its effects (trails). Two Gunners in one match may differ. The menu side is a
separate task; this task establishes what the match side needs. Project rules that bind any
later design: a new move owns its dependencies; no fighter-kind casts, no borrowed donor
state, no forced per-frame status changes, no placeholder assets.
Read first: research/P11-MOVE-PLAN.md WITH its coordinator banner (much of it is unverified;
its sword statements are exactly what you must measure), and, if they exist and are
finished when you start, research/P12-FTILT-FACTS.md and research/P12-SCRIPT-ROUTE.md. If
you read inside mods/ssbu_mod_new/ (the user's other mod; it has put weapons and models on
other fighters), read its AGENTS.md and handbook/00_INDEX.md first; reference only, never
edit, and cite file:line instead of copying text.

Q1. The Swordfighter's sword as data. Where the sword geometry lives (which model files,
    mesh object names, which bone it is skinned or parented to, materials and textures), for
    the default sword and for the Mii's selectable costume swords if those are separate
    assets; whether the sheath is separate; male/female body variants. Sizes and sha256 of
    every file cited. Is the sword part of the body model, a separate model slot, or an
    "article"/weapon object?
Q2. How the game shows and hides it. On a vanilla Swordfighter: is the sword always visible,
    or toggled per move (visibility tracks in animations, ACMD calls such as model/mesh
    visibility or "have item" style calls, status code)? Give the mechanism with script and
    animation evidence for two sword moves and one move where it is sheathed or hidden, if
    any.
Q3. The effects. Sword trails and slash effects of the Swordfighter's normal moves: which
    effect names the scripts request (decode from lua2cpp_miiswordsman.nro; addresses), in
    which effect file each lives (fighter-specific ef_miiswordsman.eff or common), which
    textures/trail resources they need, which bones they attach to. Does a Mii Gunner's
    effect environment contain any of them? What decides which .eff a fighter can use
    (per fighter kind load? evidence from the archive/file tables, not an assumption).
Q4. The Gunner side. Does the Gunner skeleton have the bone(s) the sword and its effects
    attach to (names, hashes, parent chain, rest transforms compared with the
    Swordfighter's)? What is on the Gunner's right arm (the arm cannon mesh: which mesh
    objects, which bones) and would a held sword intersect it? Mesh visibility groups the
    Gunner model already has.
Q5. Ways a Gunner could get a sword model, each with what is measured and what is unknown:
    (a) extra mesh objects merged into the Gunner body model with a visibility switch,
    (b) a separate model attached at runtime (how does the game attach held items or
    articles to a fighter; what does the other mod do, with file:line and its evidence
    tier), (c) anything else the data suggests. For each: the files that would be added or
    replaced, whether replacement is per fighter kind (then both Gunners in a match share
    it and the switch must be per object at runtime), and the runtime call that would
    toggle visibility per fighter object. No design recommendation; one comparison table.
Q6. "Used for all sword moves": list the Swordfighter's normal and special moves that
    reference the sword (hitbox bone, trail, visibility), so a later design knows how many
    scripts depend on the sword choice. A count per move group is enough, with the method.
Q7. The closure, as one list: every file and every runtime fact that "Gunner A shows the
    Mii Swordfighter sword with its trail during a borrowed sword move while Gunner B does
    not" depends on, each marked measured (B) or assumed (D).

Deliver research/P14-SWORD-FACTS.md (short answers first), evidence/P14-SWORD-FACTS/ with
check_p14_sword_facts.py (hashes of every input file, every cited instruction word, the
mesh / bone / effect tables; at least four negative controls behind `--neg`; exit 1 on
mismatch; rerun AFTER your last report edit and paste the output), tables under workspace
gamedata/mii_customizer/P14-SWORD-FACTS/.

Rules: every name and number must come from a file you hashed; tier B only for what the
check script re-reads; everything about what happens in the game is D; do not claim a file
is missing before checking the archive index and the extraction tools (workspace
tools/REGISTRY.md); do not fill gaps from memory or the internet.

Exclusive writes: research/P14-SWORD-FACTS.md, evidence/P14-SWORD-FACTS/,
scratch/2026-10-07_P14-SWORD-FACTS/, workspace gamedata/mii_customizer/P14-SWORD-FACTS/.
