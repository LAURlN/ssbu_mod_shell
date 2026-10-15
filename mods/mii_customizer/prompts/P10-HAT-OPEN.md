# P10-HAT-OPEN - the open native questions of the headgear list (facts only)

For Space Bunny Alpha. Offline static analysis; nothing is executed or patched. Follow
workspace AGENTS.md, this mod's AGENTS.md and STATUS.md. No agents, commits, emulator,
SD access. Paths are relative to mods/mii_customizer/ unless marked workspace-relative;
create every folder INSIDE mods/mii_customizer/. Use `python`; write scripts with the
file tool, not heredocs. Create research/P10-HAT-OPEN.md FIRST, write each answer into
it as soon as you have it (another task reads this file while you work), and end with
task ID, DONE/PARTIAL/BLOCKED, changed files, checks run, open questions.

Background. The mod will show a list of characters on the Mii maker's native headgear
screen ("mod mode") and must never change the Mii's real headgear or let a made-up
item reach the save. Plugin task P10-UI-SLICE (parallel, not yours) builds the hooks.
P9-HAT-HANDLES section 9 left questions open that decide whether that is safe. Answer
them from the image.

Input: workspace gamedata/ssbu-13.0.4/main.bin (flat; address == file offset; sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613, verify it).
Disassembler, from the workspace root: `PYTHONPATH=mods/ssbu_mod_new/builds/.cache/
dk_cargo/python python mods/mii_customizer/scratch/2026-10-04_P1-ID-REVIEW/d.py win
<addr> <n>`; relocation helpers in scratch/2026-10-05_P9-HAT-HANDLES/ (copy, do not
edit). Read first: research/P9-HAT-HANDLES.md (all), research/P8-HAT-NATIVE.md
(banners, sections 3-7), research/P9-EDIT-DISPATCH.md (sections 1, 1.2, 5).
S = the 0x170-byte sub-object at [list object+0x80]; list object = [scene+0x180].

Questions, in this order of importance:

Q1. The decision and the Mii. Walk headgear state 5 (0x180abd0) end to end. For each
    way the screen can end (decide, cancel, any other): which fields it reads (S+0x160
    -> scene+0x1b0, S+0x148, S+0x140, S+0x150, S+0x164), under exactly which condition
    it writes the static 0x5306cb0 (0x180ad20), what 0x180cf10 does (scene+0x163,
    0x5306ca8, 0x33115f0), when it pops the state stack, and whether cancel restores
    the static to the entry handle and from where. Also read 0x180d2a0 and say what it
    is.
Q2. The preview while the cursor moves. In the frame callback 0x19cc3f0: every path
    from "selected row changed" to a write of S+0x140 / S+0x148 / S+0x169 or a call
    that changes the model; which of them run when the ownership test 0x328b5d0
    returns 0 for the selected handle. Does anything outside 0x19cc3f0 and state 5
    write 0x5306cb0 or the model's hat while the list is open (enumerate all writers of
    0x5306cb0; P9 lists eleven references)?
Q3. The save. In the function(s) around 0x180d4c4 / 0x180d4cc / 0x180d734 and the
    editor commit 0x180d200: how the headgear handle goes from the static into the
    saved record, what validates it, and what happens for a handle with tag 0x5a whose
    hash is in no registry.
Q4. Who calls the frame callback stored at [S+0x88]: the loader of that slot and the
    `blr`, how often (per frame or per event), with which arguments, and whether the
    caller is specific to this list or generic.
Q5. The row-callback vtable 0x50a6b18. Coordinator hypothesis to test: it is not a
    separate object but the secondary vtable of S itself (0x50a6ae0 + 0x38, installed
    at S+0x48; the thunk 0x19cd010 subtracts 0x48 and the literal at slot +0x10 is the
    offset-to-top -0x48). Look for stores into [S+0x48] in ctor 0x19ceb30 and for
    `add xN, x25, #0x48` feeding the scroller builder 0x3781470 (x4). Then: who calls
    slots +0x00 / +0x08 / +0x48 (row filler, row -> index, slide) and when (which rows:
    all, or only visible ones; on scroll; on demand).
Q6. The count. Where the scroller keeps the item count after 0x3781470 (field offset,
    width), every later reader of it (cursor clamp, scroll bar, row callbacks), what
    Lua does with the constant SCROLLER_ITEM_NUM registered at 0x19cf854 (see
    research/P6-HAT-UI.md), and whether any existing native path changes the count of
    a built scroller (for example the sort or a rebuild). State which fields would have
    to change together for a different count; do not design the change.

Rules. Facts with addresses, tier B only for what your check script re-reads; mark
everything about runtime behaviour D. Where an earlier report is wrong, say so with
the instruction that shows it. If a question does not resolve, write how far you got
and the next concrete read. Do not propose hooks or designs.

Deliver research/P10-HAT-OPEN.md (answers first, one short paragraph per question,
then the detail), evidence/P10-HAT-OPEN/ (disassembly windows and
check_p10_hat_open.py: verifies the image hash, re-reads every cited instruction,
displacement, branch target, string and relocation, negative controls, exit 1 on
mismatch; say from which folder it must be started).

Exclusive writes: research/P10-HAT-OPEN.md, evidence/P10-HAT-OPEN/,
scratch/2026-10-05_P10-HAT-OPEN/.
