# P11-INT-PARAMS - integer fighter parameters through the +0x250 getter (facts only)

For Space Bunny Alpha. Offline static analysis; nothing is executed or patched. Follow
workspace AGENTS.md, this mod's AGENTS.md and STATUS.md. No agents, commits, emulator, SD
access. Paths are relative to mods/mii_customizer/ unless marked workspace-relative; create
every folder INSIDE mods/mii_customizer/; game-derived output goes to workspace
gamedata/mii_customizer/P11-INT-PARAMS/. Use `python`; write scripts with the file tool, not
heredocs. Create research/P11-INT-PARAMS.md first and extend it as you go. End with task ID,
DONE/PARTIAL/BLOCKED, changed files, checks run, open questions.

Background (console, tier A): the plugin overrides float fighter parameters for a saved Mii
Gunner by hooking 0x4e53e0, the 4-instruction thunk in vtable slot +0x270 of vtable
0x4f89490 (object at [accessor+0x50]; field hash in x1, x2 == 0). Presets now carry 41 float
fields. Integer parameters (jump_count_max and others) go through slot +0x250 instead
(research/P4-STAT-SITES.md section 6 `jump_count_max`, example 8.2) and are not covered. A
later plugin task will add a second hook; it needs the facts below.

Input: workspace gamedata/ssbu-13.0.4/main.bin (flat; address == file offset; verify sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613). Read first:
research/P2-STAT-HOOKPOINT.md, research/P4-STAT-SITES.md, research/P10-PRESET-WIDE.md
(Part 1 method and its separate list of integer fields), research/P7-PRESET-ENGINE.md
section 2. Copy scanners into your scratch; do not edit the originals.

Q1. Slot +0x250 of vtable 0x4f89490: the function there, its full disassembly, first four
    words, whether any is PC-relative, what it forwards to (compare with 0x4e53e0, which
    forwards to another object's slot +0x30), argument and return registers (w0 int?), and
    whether other slots (+0x258, +0x260, +0x268, +0x278 ...) re-dispatch into it, as +0x268
    does into +0x270. Check the neighbouring vtables that P2-STAT-HOOKPOINT listed for the
    same class shape, so a hook on this function is known to be Mii-relevant and not
    shared with something else.
Q2. For every integer field of the fighter_param table (types from workspace
    gamedata/mii_customizer/P10-PRESET-WIDE/fighter_param_full.json): code sites that
    materialise its hash40 and call through +0x250 (count, x2 at the sites), Mii Gunner's
    value, min / max / number of distinct values over all fighters. One table. Validate the
    scanner first by reproducing P4's `jump_count_max` sites.
Q3. From Q2, the fields that qualify for a preset by the same rule as the floats (integer,
    at least one +0x250 site with x2 == 0, differs between fighters). For each, say what it
    plausibly controls and flag for coordinator review, instead of recommending: anything
    that looks like an index, an animation or model selector, a flag set, or a count that
    resources depend on (for example jumps that need extra animations: list which fighters
    have jump_count_max > 2 and whether Mii Gunner has the motions `jump_aerial_f2` etc. in
    its motion list, read-only from the files P1-DATASET used).
Q4. Bool and other non-float, non-int field types in the table: which getter slot they use
    (sites and displacement), in one short table. No further analysis.

Rules: facts with addresses; tier B only for what the check script re-reads; runtime
behaviour is D; no hook code. Deliver research/P11-INT-PARAMS.md (answers first),
evidence/P11-INT-PARAMS/ with check_p11_int_params.py (image hash, cited instructions and
relocations, the site counts; negative controls; exit 1 on mismatch; run it once more AFTER
your last edit and paste that output), tables under workspace
gamedata/mii_customizer/P11-INT-PARAMS/.

Exclusive writes: research/P11-INT-PARAMS.md, evidence/P11-INT-PARAMS/,
scratch/2026-10-06_P11-INT-PARAMS/, workspace gamedata/mii_customizer/P11-INT-PARAMS/.
