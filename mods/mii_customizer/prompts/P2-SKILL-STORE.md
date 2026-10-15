# P2-SKILL-STORE - premium: where the four special-choice bytes come from and go to

For Claude Opus 5.5 or GPT 6.1 Sol. One bounded native trace. Follow workspace
AGENTS.md, this mod's AGENTS.md and STATUS.md. No agents, commits, branches,
emulator, SD access, framework changes or edits to other workers' files. Inputs are
read-only. B is offline observation, D hypothesis; nothing here is runtime evidence.
Coordinator owns STATUS/CURRENT_INSTALL/CHANGELOG. Paths are mod-relative unless
marked workspace-relative. Save the report and end with task ID,
DONE/PARTIAL/BLOCKED, changed files and the next experiment.

Input: workspace-relative gamedata/ssbu-13.0.4/main.bin, sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613. Flat image,
address == file offset. Relocation records: bare 24-byte array at file
0x39c8070..0x40c9fc7 (see research/P2-SKILL-NATIVE.md). Disassembler: copy
scratch/2026-10-04_P1-ID-REVIEW/d.py into your scratch folder; capstone via
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python (workspace-relative).
Use `python`.

Established so far (B, coordinator re-read the instructions for items 1-3):
1. The special-move screen's Lua keeps one 0-based option index per special slot and
   calls get_skill_id(row) on entry and set_skill_id(row, option) for all rows on
   exit (research/P2-UI-FLOW.md, corrected rows 12, 15, 32).
2. Those handlers are 0x19dcf40 / 0x19dcf20: bounds check row < 4, then
   ldrb / strb at [obj + 0x100 + row]. `obj` is a 0x150-byte object allocated in
   0x19ddb30 (x19 from 0x19ddb94), vtable 0x50a6e20, stored at [outer + 0x80]
   (0x19ddd80). Its constructor zeroes [obj+0x100] (0x19ddd24) and sets
   [obj+0xf8] = 0xc1ffff0000000000 (0x19ddcf4-0x19ddd0c), a tag-0xc1 key of the
   kind P1-ID-REVIEW 2.4 found at saved-record +0x1a0.
3. `outer` is a 0x88-byte object constructed by 0x19ddb30(outer, x1, x2), called
   from exactly two sites, 0x1809814 and 0x1982fc0.
4. Saved-fighter record layout from research/P1-ID-REVIEW.md 2.4: 0x1B0 bytes,
   u32 ID at +0x000, unexplained u32 at +0x140 and u16 at +0x144, loader
   0x17c8210. Hypothesis only (D): the four option bytes are record +0x140..+0x143.

Question, in three parts. Answer each with instruction addresses.
A. Who writes non-zero values into [obj+0x100..0x103] before the screen opens, and
   from which source object and offset? Follow the value back until you reach either
   a saved-fighter record field (state the record offset) or an editor working copy
   (state its owner and offset), whichever comes first.
B. After the screen closes, who reads [obj+0x100..0x103] and where does it store
   them? Follow forward until the value lands in a working copy or record field.
C. What sets [obj+0xf8], and from what? Report only the source field; do not
   analyse the fighter-kind system.

Method constraints. Reach obj only through proven provenance: the two callers, the
[outer+0x80] slot, obj's vtable 0x50a6e20 and the scene's virtual methods. Do not
scan the binary for bare `#0x100` displacements. At most three hops in each
direction; if the chain is not closed by then, stop PARTIAL and state the exact
next address to read. Separate what the instructions show (B) from what you think
the fields mean (D). Do not trace match setup, do not design persistence, do not
propose hooks.

Why this matters: it decides whether the editor already carries per-saved-fighter
bytes we can read at match time, and whether option values above the vanilla range
could be stored without touching the save format.

Deliver research/P2-SKILL-STORE.md: a short answer to A, B, C, one table of
(address, instruction, meaning tier), and the smallest remaining unknown.

Exclusive writes: research/P2-SKILL-STORE.md, evidence/P2-SKILL-STORE/,
scratch/2026-10-04_P2-SKILL-STORE/.
