# P8-HAT-NATIVE - native side of the headgear list: where its rows and count come from

For Space Bunny Alpha. Follow workspace AGENTS.md, this mod's AGENTS.md and STATUS.md.
No agents, commits, branches, emulator, SD access or edits to other workers' files.
Offline static analysis only; nothing is executed or patched. All paths are relative to
mods/mii_customizer/ unless marked workspace-relative; create every folder INSIDE
mods/mii_customizer/ and make scripts write there. Use `python`. Save the report and end
with task ID, DONE/PARTIAL/BLOCKED, changed files and what you could not verify.

Why: the user wants the mod's selection lists to look and behave like the Mii maker's
headgear list. research/P6-HAT-UI.md showed that the script never fills that list: the
list object is a host-made global `scroller`, there is no count and no row text in Lua,
and the only bridge calls are `sort_id_list`, `get_top_index`, `backup_list_selected_id`
and `select_list_from_backup_id`. Whether the mod can reuse this list depends on how the
native side supplies the item count and draws a row. This task locates that code.

Input: workspace-relative gamedata/ssbu-13.0.4/main.bin, sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613 (verify first). Flat
image: address == file offset. Relocation array 0x39c8070..0x40c9fc7, 24-byte entries.
Disassembler and helpers: copy `d.py`, `relocs.py`, `lib.py` from
scratch/2026-10-04_P3-CUSTOMIZE-SITES/ into your scratch folder; run with
`PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python` from the workspace root
(read mods/ssbu_mod_new/AGENTS.md before reading anything else in that folder).

Read first: research/P6-HAT-UI.md (sections 2, 3, 4, 10, 13), research/P1-ID-REVIEW.md
section 2.3 (bridge registration: delegate + handler pointer), research/P2-SKILL-NATIVE.md
and research/P4-BRIDGE-FACTS.md (how handlers were located from name strings and how Lua
arguments are read from the stack), STATUS.md.

Known anchors (B, measured by the coordinator; each occurs once in the image):
`sort_id_list` at 0x427f3a7, `get_top_index` at 0x4290580, `sub_list_window` at
0x4290570, `sub_list_window_facade` at 0x4348c43, `scroller` at 0x436b678,
`mii_select_scroller` at 0x426e989, `SCROLLER_ITEM_NUM` at 0x42a18e6. Mii editor scene
function 0x1808980 (tier A that it is the editor scene).

Questions. Give addresses and the instructions you read; mark runtime behaviour D.
1. Registration: find the references to `sort_id_list` and `get_top_index` and the
   function(s) that register them (delegate object, handler pointer). Which scene object
   owns them, how large is it, and which constructor builds it? Is the same object used
   for both the headgear and the outfit screen?
2. Handlers: disassemble the handlers of `sort_id_list`, `get_top_index`,
   `backup_list_selected_id` and `select_list_from_backup_id`. For each: which fields of
   the scene object it reads and writes (offsets, widths), what it calls, what it returns
   to Lua. For `sort_id_list`: where is the item array (pointer, element size, count
   field), and what are the three sort modes comparing?
3. The global `scroller`: find the reference to the string at 0x436b678 that belongs to
   this scene (there may be several users; list all and say which is the Mii one and
   why). What native type is pushed to Lua under that name (vtable address, constructor),
   and with which construction arguments (layout root, part name pattern, visible row
   count, total count, callbacks)?
4. `SCROLLER_ITEM_NUM`: where is it registered and with which value?
5. Item count: which field holds the total number of list entries, and who computes it
   (from which table: unlocked headgear, a param file, the save)? One call level deep is
   enough; name the callee addresses beyond that.
6. Row drawing: find the function that fills one visible row (called by the scroller
   with a row or item index). What does it set: a text by message key hash, a text by
   string, a texture, a visibility flag for marks? Give the calls and their constant
   arguments. In particular: is the row text taken from a message label derived from the
   item id, or from a string pointer the list holds?
7. Decision: what does `get_decided_item` return (row index or item id from the array),
   and where does the scene turn that into the Mii's headgear value? One level deep.
8. For a later hook: list the smallest set of functions a plugin would have to intercept
   to (a) change the item count and (b) supply its own row text, with address, argument
   registers at entry, and whether the first four instructions contain PC-relative
   instructions. This is a list of facts, not a design; say what remains unknown.

Deliverables: research/P8-HAT-NATIVE.md; evidence/P8-HAT-NATIVE/ with the raw disassembly
windows you rely on and a check script that re-reads every cited address (instruction
words, operands, string contents, pointers) from main.bin and exits non-zero on
mismatch, with at least three negative controls you ran. Paste the check's last lines
into the report. State plainly which questions stayed open and how far you got on each.

Not in scope: patching, hooks, plugin code, Lua edits, layout files, the edit menu's
row-to-screen dispatch (another worker has that), a design.

Exclusive writes: research/P8-HAT-NATIVE.md, evidence/P8-HAT-NATIVE/,
scratch/2026-10-05_P8-HAT-NATIVE/.
