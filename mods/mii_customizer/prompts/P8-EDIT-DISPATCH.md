# P8-EDIT-DISPATCH - native side of the Mii edit menu: who reads the chosen row and opens the sub-screen

For Space Bunny Alpha. Follow workspace AGENTS.md, this mod's AGENTS.md and STATUS.md.
No agents, commits, branches, emulator, SD access or edits to other workers' files.
Offline static analysis only; nothing is executed or patched. All paths are relative to
mods/mii_customizer/ unless marked workspace-relative; create every folder INSIDE
mods/mii_customizer/ and make scripts write there. Use `python`. Save the report and end
with task ID, DONE/PARTIAL/BLOCKED, changed files and what you could not verify.

Why: research/P6-EDIT-MENU.md showed that the edit menu script only publishes the decided
row (0..5, or 6 for "try") through `exit_value` / `get_exit_value()`, and that it reads
host globals (`IS_READ_ONLY`, `IS_SKILL_EDITABLE`, `FROM_AMIIBO`, `EXIT_VALUE_DECIDE`,
`EXIT_VALUE_CANCEL`). The mapping from row to sub-screen is native. The mod wants to add
its own entry there, so it needs to know where that mapping is and how a sub-screen
script is started.

Input: workspace-relative gamedata/ssbu-13.0.4/main.bin, sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613 (verify first). Flat
image: address == file offset. Relocation array 0x39c8070..0x40c9fc7, 24-byte entries.
Disassembler and helpers: copy `d.py`, `relocs.py`, `lib.py` from
scratch/2026-10-04_P3-CUSTOMIZE-SITES/ into your scratch folder; run with
`PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python` from the workspace root
(read mods/ssbu_mod_new/AGENTS.md before reading anything else in that folder).

Read first: research/P6-EDIT-MENU.md (sections 0b, 2, 6, 8), research/P1-ID-REVIEW.md
section 2.3 (how a bridge name is registered: delegate + handler pointer),
research/P2-SKILL-NATIVE.md and research/P4-BRIDGE-FACTS.md (method that located the skill
handlers from their name strings, and how Lua arguments are read), STATUS.md.

Known anchors (B, measured by the coordinator; each string occurs once in the image):
`get_exit_value` at 0x42e5a36, `EXIT_VALUE_DECIDE` at 0x4359e6a, `mode_make_mii_edit` at
0x425e171, `set_skill_id` at 0x4348c5a. Mii editor scene function 0x1808980 (tier A that
it is the editor scene). Special-move scene object constructor 0x19ddb30. There is NO
string `make_mii_hat`, `make_mii_special` or `chara_make` in the image, so script paths
are not stored as plain text; expect 40-bit hashes or a table.

Questions. For each answer give addresses and the instructions you read; mark every
statement about runtime behaviour D.
1. `get_exit_value`: find every reference to the string (ADRP+ADD pairs and relocated
   pointers). Which function calls the script function of that name, how is the result
   converted (integer, float), and where is it stored?
2. Follow that stored value: find the compare chain or jump table that turns it into an
   action. Give a table: value -> target code address -> what that target does in one
   line, as far as readable (which object it constructs, which function it calls). The
   values of interest are 0..6 and the negative / cancel case.
3. How is a sub-screen started from there? Identify the call that loads or starts a UI
   script (arguments: a hash, an index, a pointer to a descriptor?). List the constant
   arguments for each of the sub-screens. If they are 40-bit hashes, try to match them by
   hashing the candidate paths with the workspace hash40 implementation (crc32 of the
   lowercase string, length in the top byte; use the one in
   mods/ssbu_mod_new/tools if present, otherwise write it and test it against
   hash40("fighter_kind_miigunner") == 0x166e9fae70). Candidates:
   `ui/script/menu/chara_make/make_mii_<x>_actor.lc`, the same without extension, without
   the `ui/script/` prefix, and bare `make_mii_<x>_actor`, for x in hat, body, special,
   edit, base, color, voice, name. Report matches and non-matches.
4. Is there one place that knows the special-move screen specifically (the path that ends
   in the constructor 0x19ddb30)? Show the chain from the value-4 branch to it.
5. Host globals: find where `EXIT_VALUE_DECIDE` and `EXIT_VALUE_CANCEL` are given their
   values (the function that registers named numbers into the script environment). Report
   the two values, and the registration function's address and signature as far as
   readable. Use the same method for `IS_SKILL_EDITABLE`, `IS_READ_ONLY`, `FROM_AMIIBO`
   (find the strings first; report counts) and say where their values come from
   (compare with STATUS.md: W+0x14 / W+0x24 of the editor working record at 0x5306b78).
6. Return path: after a sub-screen ends, where does control come back and is the edit
   menu script started again from its beginning? Only as far as visible in the same
   function(s).
7. For a later hook: which single function, if any, sees both the decided row value and
   decides what to open, with the value in a register at a stable instruction? Give
   address, register, and whether the first four instructions of that function contain
   PC-relative instructions (list them).

Deliverables: research/P8-EDIT-DISPATCH.md; evidence/P8-EDIT-DISPATCH/ with the raw
disassembly windows you rely on and a check script that re-reads every cited address
(instruction words, operands, string contents, table entries) from main.bin and exits
non-zero on mismatch, with at least three negative controls you ran. Paste the check's
last lines into the report. State the limits plainly: what was not found, and every edge
you followed only partly.

Not in scope: patching, hooks, plugin code, Lua edits, layout files, the headgear list
internals (another worker has those), a design.

Exclusive writes: research/P8-EDIT-DISPATCH.md, evidence/P8-EDIT-DISPATCH/,
scratch/2026-10-05_P8-EDIT-DISPATCH/.
