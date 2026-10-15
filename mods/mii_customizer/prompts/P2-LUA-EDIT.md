# P2-LUA-EDIT - fix xref and add guarded instruction/constant editing to lua53-inspect

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md. Work only on the task below. No agents,
commits, branches, emulator, SD access, framework changes or edits to other workers'
files. Inputs remain read-only. Keep game-derived files in your assigned
workspace-relative gamedata/mii_customizer/<task>/ folder, never source/evidence.
Report exact inputs/hashes, commands, observed checks, failures and limits. B is
offline observation, C pinned source, D hypothesis; no runtime behavior claims.
Coordinator owns STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report
and chat with task ID, DONE/PARTIAL/BLOCKED, changed files and next experiment.
Paths below are mod-relative unless marked workspace-relative.

One goal: make tools/lua53-inspect/ able to change code, not only string constants,
with the same refuse-by-default discipline it already has. You own that tool folder
for this task. This is a tool task. Do not design or write any mod Lua logic, and do
not produce a modified game chunk meant for use.

Read tools/lua53-inspect/README.md, research/P1-LUA-WRITE.md and section 2.1 of
research/P2-UI-FLOW.md. Format authority stays the pinned Lua v5.3.6 sources the
README lists (lopcodes.h, lopcodes.c, lundump.c, ldump.c); cite the exact lines you
rely on. Use `python`, not `python3`.

Part A - fix a known defect. `xref` reports OP_JMP, OP_FORLOOP and OP_FORPREP
(iAsBx) as constant uses through RK.B. Fix it so only genuine iABC RK operands and
LOADK/LOADKX-style Bx uses are reported, taking each opcode's B/C argument mode
from the luaP_opmodes table (OpArgK), not from a hand-written list. Add regression
checks: on the three editor chunks the count of iAsBx instructions reported as RK
uses must be 0 (P2-UI-FLOW measured 33, 139 and 146 before the fix), and the
genuine counts it measured (336/93, 582/68, 598/69 for RK/LOADK) must be compared
with yours; explain any difference from the bytes, do not adjust to match.

Part B - three mutators, each a library function plus a CLI command, each refusing
anything it cannot prove safe and writing nothing on refusal:
1. `appendconst`: append one constant (string, integer or float in the chunk's own
   number width) to the END of one prototype's constant table and print its index.
   Appending moves no existing index. Refuse insertion anywhere else. Report whether
   the new index is still reachable as an RK operand (index <= 255) or only by LOADK.
2. `patchins`: replace ONE instruction word in one prototype, given as opcode and
   fields, not as a raw word. Validate fields against the opcode's mode, constant
   and closure indices against table sizes, registers against maxstacksize, and jump
   targets against the code length. Print the old and new decoded instruction.
3. `insertins`: insert N instructions at one PC in one prototype and relocate every
   affected relative jump (JMP, FORLOOP, FORPREP, and the implicit skip of
   EQ/LT/LE/TEST/TESTSET/LOADBOOL C!=0 and LOADKX/SETLIST C=0 pairs, which must never be split).
   Refuse if a relocated offset no longer fits its field, if the insertion point
   splits such a pair, or if the result fails `verify`. State which jump kinds you
   handle; refuse the ones you do not.
Do not implement deletion, prototype insertion, upvalue edits or a compiler.

Prove it on the SYNTHETIC chunk from `synth` (extend `synth` if it lacks jumps or a
loop): append a constant, insert a LOADK that consumes it inside a loop body, then
show `verify`, `compare` and `roundtrip` results and that every pre-existing jump
still reaches the same instruction as before. Add negative checks for each refusal.
Then run each mutator once on a COPY of make_mii_special_actor.lc, written only to
workspace-relative gamedata/mii_customizer/P2-LUA-EDIT/, as a format check: a
semantically neutral insertion (for example `MOVE R[n] R[n]` on a register that
exists) and report size change, structural diff and verify result. That copy is a
format exercise, not a candidate for the game. The original chunks must hash the
same before and after; all existing checks must still pass.

Inputs, workspace-relative, read-only: the three chunks under
gamedata/mii_customizer/P1-UI/ui/ listed in the tool README.

Update the tool README (usage, limits, what each refusal means) and the check
script. Report in research/P2-LUA-EDIT.md what was verified, each refusal with its
exit code, and what remains unsupported. Passing checks prove the encoding only;
say so, and do not claim the game would load an edited chunk.

Exclusive writes: tools/lua53-inspect/, research/P2-LUA-EDIT.md,
evidence/P2-LUA-EDIT/, scratch/2026-10-04_P2-LUA-EDIT/,
workspace-relative gamedata/mii_customizer/P2-LUA-EDIT/.
