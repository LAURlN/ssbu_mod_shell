# P12-FTILT-FACTS - what Mii Brawler's forward tilt is made of, measured (facts only)

For Space Bunny Alpha. Offline analysis of extracted game files; nothing is executed,
patched or installed. Follow workspace AGENTS.md, this mod's AGENTS.md and STATUS.md. No
agents, commits, emulator, SD access. Paths are relative to mods/mii_customizer/ unless marked
workspace-relative; create every folder INSIDE mods/mii_customizer/; extracted or generated
game data goes to workspace gamedata/mii_customizer/P12-FTILT-FACTS/ (the files P11-MOVE-PLAN
extracted are in workspace gamedata/mii_customizer/P11-MOVE-PLAN/, read-only for you). Use
`python`; write scripts with the file tool, not heredocs. Create research/P12-FTILT-FACTS.md
in your first minutes and extend it after every answer. End with task ID,
DONE/PARTIAL/BLOCKED, changed files, checks run, open questions.

Background. The mod lets a saved Mii Gunner choose stats in the Mii maker (works on the
console). Next comes the first borrowed MOVE: a Mii Gunner that performs Mii Brawler's
forward tilt, chosen per saved Mii, while another Gunner in the same match keeps its own.
research/P11-MOVE-PLAN.md proposed forward tilt as the cheapest first move, but several of
its statements were written from memory and are NOT measured (see the coordinator banner at
its top): hitbox numbers, which scripts exist, which effects and sounds are used, the file
name of the tilt animation, whether a class overrides the status. This task measures them.
Read that report and its banner first. If you read anything inside mods/ssbu_mod_new/ (tools,
handbook pages on ACMD, motion lists, lua2cpp NROs), read its AGENTS.md first; it is
reference only, never edit it.

Fighters: miigunner (target), miifighter (Brawler, donor); miiswordsman only where a
question says "all three".

Q1. Motion entries. For all three classes, every motion_list.bin entry of the forward tilt
    family (attack_s3_s and any hi / lw angled variants - say which exist): index, motion
    kind hash, the four script hashes, animation file name(s), flags, blend, cancel frame,
    every other field of the entry. One table. State how many frames each animation has.
Q2. Scripts. In lua2cpp_miifighter.nro and lua2cpp_miigunner.nro: locate the functions
    registered for game_attacks3 (and the effect_, sound_, expression_ ones, and angled
    variants if they exist) - registration site, function address, size. For the Brawler
    game script, list every ACMD call in order with its frame/timing and all arguments
    (attack id, part, bone hash, damage, angle, kbg, fkb, bkb, size, offsets, effect,
    level, sound, attribute...), decoded from the instructions/constants, each with its
    address. Same for Gunner's, for comparison. If you cannot decode an argument, say so;
    do not fill it in from memory or from the internet.
Q3. Dependencies of the Brawler scripts. Every effect hash, sound label hash, bone hash and
    article/weapon reference used by the four Brawler forward-tilt scripts. For each: is it a
    common resource (name the common file it is in) or fighter-specific; if fighter-specific,
    does Mii Gunner's own effect file / sound bank / skeleton have the same name? One table
    with a yes/no "available on a Gunner without adding files" column and the evidence.
Q4. Status. Which status kind runs the forward tilt, and whether lua2cpp_miifighter.nro or
    lua2cpp_miigunner.nro registers its own status functions for it (pre/main/end/exec...),
    with the registration sites; or that neither does, shown by a scan you describe (what
    pattern, how validated on a status that IS overridden, e.g. a special).
Q5. Animation compatibility. Node sets of Brawler's forward-tilt animation(s) vs Gunner's:
    transform, visibility, material tracks; any node in one and not the other; any track that
    drives something the Gunner model does not have. Which Gunner mesh objects exist that
    Brawler lacks and the reverse (m and f bodies).
Q6. The closure, as one list: every file and every runtime fact that "Gunner plays Brawler's
    forward tilt with Brawler's hitboxes, effects and sounds" depends on, each marked
    measured (B) or assumed (D). No design, no recommendation.

Deliver research/P12-FTILT-FACTS.md (short answers first), evidence/P12-FTILT-FACTS/ with
check_p12_ftilt_facts.py (hashes of every input file, every cited instruction word, the
decoded script tables, the dependency table; at least four negative controls behind `--neg`;
exit 1 on mismatch; rerun AFTER your last report edit and paste the output), tables under
workspace gamedata/mii_customizer/P12-FTILT-FACTS/.

Rules: every number in the report must come from a file you hashed; tier B only for what the
check script re-reads; anything about what happens in the game is D. Do not claim a file is
missing before checking the local archive index and the existing extraction tools
(workspace tools/REGISTRY.md).

Exclusive writes: research/P12-FTILT-FACTS.md, evidence/P12-FTILT-FACTS/,
scratch/2026-10-07_P12-FTILT-FACTS/, workspace gamedata/mii_customizer/P12-FTILT-FACTS/.
