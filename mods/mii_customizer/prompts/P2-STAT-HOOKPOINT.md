# P2-STAT-HOOKPOINT - locate the function the engine actually calls for float params

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md. Work only on the task below. No agents,
commits, branches, emulator, SD access, framework changes or edits to other workers'
files. Inputs remain read-only. Report exact inputs/hashes, commands, observed
checks, failures and limits. B is offline observation, C pinned source, D
hypothesis; no runtime behavior claims. Coordinator owns
STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report and chat with task
ID, DONE/PARTIAL/BLOCKED, changed files and next experiment. All paths below are
relative to mods/mii_customizer/ unless marked workspace-relative. Create your
evidence and scratch folders INSIDE mods/mii_customizer/, not at the workspace root.

Background (B, from research/P2-STAT-READS.md, re-read by the coordinator at
0x2db55b8-0x2db55d8): engine code fetches `weight` like this:
    ldr x8,[x20,#0x20] ; ldr x0,[x8,#0x50] ; ldr x8,[x0] ; ldr x8,[x8,#0x270]
    mov x1,<hash> ; mov x2,xzr ; blr x8
That is an indirect call through slot 0x270 of the vtable of the object at
[accessor+0x50]. 21 listed sites use this shape. A hook placed on an exported
wrapper function would not see these calls; only the function stored in that
vtable slot does.

One goal: find the address of the function stored in that vtable slot, and find
out what the old mod's hook actually patches. Locating task. Do not build a hook.

Input: workspace-relative gamedata/ssbu-13.0.4/main.bin, sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613 (rehash first; stop
BLOCKED on mismatch). Flat image, address == file offset; code 0x100..0x39C8000;
relocation records are a bare 24-byte array at file 0x39c8070..0x40c9fc7 (see
research/P2-SKILL-NATIVE.md for how it was validated; copy its relocs.py and d.py
into your scratch folder, do not edit the originals). capstone:
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python (workspace-relative).
Use `python`, not `python3`.

Part 1 - what the old mod hooks. Before reading inside mods/ssbu_mod_new/ read its
AGENTS.md, projects/pgwr/STATUS.md and handbook/00_INDEX.md, then
handbook/09_params_prc.md and 11_smashline_skyline.md. Read-only; change nothing
there. From src/pgwr/plugin/src/params.rs and the pinned skyline-smash source that
research/P2-STAT-API.md cites, establish: which symbol or address
`#[skyline::hook(replace = WorkModule::get_param_float)]` resolves to; whether that
is an exported symbol of the game executable (look the name up in the image's
dynamic symbol table and give its address) and dump its first 20 instructions.
State whether that function is itself the slot-0x270 target or a wrapper that
loads [x0+0x50] and jumps through the vtable. Quote any handbook statement, with
its tier, about whether engine-internal reads (not script calls) were observed to
change. Do not paraphrase a tier-C/D statement as observed.

Part 2 - the vtable slot. Find vtables whose slot at +0x270 could be the target:
a) Scan the relocation array for runs of consecutive 8-byte slots that all
   relocate to code addresses and are at least 0x288 bytes long. For each run,
   record its start and the code addresses at +0x248, +0x250, +0x268, +0x270,
   +0x278, +0x280 (the offsets research/P2-STAT-API.md section 3 lists).
b) Reduce the candidates with evidence, not names: the wrapper from Part 1 (if it
   is a wrapper) or its neighbours may reference nothing useful, so instead use
   construction sites: for each candidate vtable address, find adrp+add code
   references to it and report the store that installs it into an object and the
   allocation size of that object if visible in the window.
c) If more than 12 candidates remain, list them all in evidence, report the count,
   and stop PARTIAL. Do not pick one by guesswork.
For each surviving candidate dump the first 40 instructions of its +0x270 function
and state only: argument registers read, direct `bl` targets, and whether x1/x2
are compared against or passed on unchanged.

Rules. Every claim needs addresses. Do not name a class from its shape. Do not
state that a candidate "is WorkModule" unless a construction site ties it to an
object stored at [accessor+0x50]; if you can show such a store (object pointer
written to offset 0x50 of another object), report it with addresses and mark the
link B; otherwise the candidate list is the result.

Deliver research/P2-STAT-HOOKPOINT.md (answers to Part 1 and Part 2, one candidate
table, limits) plus a check script that re-derives each listed address from the
image and exits nonzero on mismatch. Raw windows go in evidence.

Exclusive writes (all under mods/mii_customizer/): research/P2-STAT-HOOKPOINT.md,
evidence/P2-STAT-HOOKPOINT/, scratch/2026-10-04_P2-STAT-HOOKPOINT/.
