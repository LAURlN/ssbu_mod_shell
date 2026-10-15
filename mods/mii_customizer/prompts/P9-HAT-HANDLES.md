# P9-HAT-HANDLES - everything on the headgear screen that interprets an item handle

For Space Bunny Alpha. Follow workspace AGENTS.md, this mod's AGENTS.md and STATUS.md.
No agents, commits, branches, emulator, SD access or edits to other workers' files.
Offline static analysis only; nothing is executed or patched. All paths are relative to
mods/mii_customizer/ unless marked workspace-relative; create every folder INSIDE
mods/mii_customizer/ and make scripts write there. Use `python`. Save the report and end
with task ID, DONE/PARTIAL/BLOCKED, changed files and what you could not verify. Write the
report early and extend it as you go.

Why: the mod plans to show its own entries (fighter names) in the game's native headgear
list by letting a plugin replace the list's contents while a "mod mode" flag is set. That
is only safe if every piece of code that interprets an item of that list is known. This
task finds those pieces. It does not design the hook.

Input and tools: workspace-relative gamedata/ssbu-13.0.4/main.bin, sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613 (verify first); flat
image, address == file offset; relocations 0x39c8070..0x40c9fc7 (24-byte entries). Copy
`d.py`, `relocs.py`, `lib.py` from scratch/2026-10-05_P8-HAT-NATIVE/ into your scratch
folder; run with `PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python` from the
workspace root (read mods/ssbu_mod_new/AGENTS.md before reading anything else there).

Read first, completely: research/P8-HAT-NATIVE.md (including the coordinator correction
at its top) and research/P6-HAT-UI.md sections 2 to 4. Facts to build on (B):
- Headgear list object: constructor 0x19ceb30, stored at scene+0x180 of the Mii editor
  scene 0x1808980; outfit twin 0x19c7830 at scene+0x188.
- Items: vector of 8-byte handles, begin/end/cap at obj+0x128/+0x130/+0x138, filled in
  the constructor by 0x3274c50 (headgear) / 0x3276440 (outfit). Selected handle at
  obj+0x150, backup handle at obj+0x158, sort mode at obj+0x164, flag byte at obj+0x169.
- Row filler 0x19ccb20 (x0 = list object after a -0x48 thunk at 0x19cd010, w1 = row
  index, x2 = row node): label builder 0x3288330 (`nam_mii_hat_%s`), panes `set_txt_val`,
  `set_txt_val_disable`, `selected`; ownership test 0x328b5d0.
- Native scroller object at [obj+0xf8], built by 0x3781470; cursor +0x2a0, selected
  +0x2a4, decided +0x2b4.
- Bridge handlers: get_top_index 0x19c1f00, sort_id_list 0x19c1f50, backup 0x19c2110,
  select-from-backup 0x19c2160.

Questions. Give addresses and instructions; mark runtime behaviour D.
1. Complete list of code that READS the vector at obj+0x128 or the handles at +0x150 /
   +0x158 of this class: every function in the range of this class's methods (use the
   vtables 0x50a6c00 and 0x50a69a0, the delegate handlers, the row-filler callback object
   and the Lua method thunks registered in the constructor). For each: what it does with
   the handle (compare, pass to which callee, store where).
2. Row filler in full: every call in 0x19ccb20 from entry to return, with arguments, in
   order. Which calls depend on the handle (label, ownership, icon or texture, marks) and
   which only on the row node? Is there an icon or thumbnail per row, and which call sets
   it from what?
3. Label builder 0x3288330: what happens when the handle is not found in its registry
   (the failure path): does it produce an empty label, a default, or trap? Same question
   for 0x328b5d0 and 0x3286320 with an unknown handle. Show the paths.
4. Cursor movement: when the selected row changes, is native code called that applies
   the item to the Mii model for preview? Find it: the per-frame or update method of the
   list object (which vtable slot, called from which scene state handler), how it notices
   a selection change (compares +0x2a4 or a handle with a stored previous one), and the
   call that applies the headgear (callee address, arguments, where the handle goes).
5. Decision: after the script's `get_decided_id()` / `is_finish`, which native code reads
   the decided row or handle and writes the Mii's headgear (the editor working record is
   the static at 0x5306b78; look for stores into it or calls taking it). Give the chain
   from the list object to that write, as far as it goes, and what is done on cancel
   (restore of the previous headgear).
6. Entry: when the headgear screen is opened, which native code positions the list on
   the Mii's current headgear (`set_select_id` is called from native with which value,
   computed how)?
7. `get_top_index` handler 0x19c1f00 in full (P8 described only its head): what it
   returns for which condition. And the delegate thunk for `sort_id_list`: how the mode
   argument is read from the Lua stack and what is returned to Lua.
8. A table "what a mod-mode list would have to neutralise": each native consumer from
   questions 1 to 6, the function entry address, argument registers at entry, the first
   four instruction words with a note which are PC-relative, and whether skipping the
   function entirely (returning immediately, and with which return value) looks
   harmless from its callers' use of the result. Facts and stated uncertainty only.

Deliverables: research/P9-HAT-HANDLES.md; evidence/P9-HAT-HANDLES/ with the disassembly
windows you rely on and a check script that re-reads every cited address from main.bin,
exits non-zero on mismatch, passes, and has at least three negative controls you ran.
Paste the check's last lines into the report. State plainly which questions stayed open.

Not in scope: patching, hooks, plugin code, Lua or layout edits, the edit menu dispatch
(another worker), a design.

Exclusive writes: research/P9-HAT-HANDLES.md, evidence/P9-HAT-HANDLES/,
scratch/2026-10-05_P9-HAT-HANDLES/.
