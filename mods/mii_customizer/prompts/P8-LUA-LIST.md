# P8-LUA-LIST - can a UI script build and fill a scrolling list itself?

For Space Bunny Alpha. Follow workspace AGENTS.md, this mod's AGENTS.md and STATUS.md.
No agents, commits, branches, emulator, SD access or edits to other workers' files.
Tracing only: do not edit any chunk, do not design a mod screen. All paths are relative
to mods/mii_customizer/ unless marked workspace-relative; create every folder INSIDE
mods/mii_customizer/ and make scripts write there. Game-derived files go only under
workspace-relative gamedata/mii_customizer/P8-LUA-LIST/. Use `python`. Save the report
and end with task ID, DONE/PARTIAL/BLOCKED, changed files and what you could not verify.

Why: the mod needs an in-game list of about 90 entries (fighter names) inside the Mii
maker. research/P6-HAT-UI.md showed that the headgear list is a host-made global
`scroller` whose rows Lua never fills. The same report notes that exactly two of the 86
extracted UI chunks WRITE the global `scroller`: `collection_tips_list.lc` and
`option_button_top.lc`. If a script can create a scroller and fill its rows, the mod can
own its list in Lua. This task finds out what those scripts do, from bytecode only.

Read first: research/P6-HAT-UI.md sections 2, 3, 10 and 12 (method and check style),
research/P5-UI-API.md, tools/lua53-inspect/README.md, tools/luac53-game/README.md.

Inputs (read-only, workspace-relative): the 86 chunks under
gamedata/mii_customizer/P5-UI-API/ui/script/, in particular
menu/collection/collection_tips_list.lc and menu/option/option_button_top.lc, and every
module those two `require`. If a required module is not among the 86, extract it with
workspace tools/arc-extract from gamedata/ssbu-13.0.4/data.arc into this task's gamedata
folder and record path, size and sha256. Record sha256 of every chunk you analyse.

Questions. Answer each with chunk, prototype and pc, and mark native behaviour as D.
1. Where does each of the two chunks get the object it stores in `scroller`: a
   constructor call (which global or module, which arguments), a host global under
   another name, or a call result? Quote the instructions.
2. Every method called on that object in those chunks and their modules, with argument
   counts, argument provenance and whether a return value is used. Compare with the nine
   methods listed in P6-HAT-UI section 2.2: same class or a different one?
3. Row content: is there any place where Lua sets text, an icon or a visibility flag for
   one row: a callback function passed to the scroller, a per-row loop, a pane lookup
   built from a row index, `set_text_message` / `set_text_message_args` /
   `set_text_string` on a row pane? For each: what is the row index source, what is the
   text source (constant key, table lookup, bridge return)?
4. Item count: where does the total number of rows come from (constant, table length,
   bridge call, method argument)? What is the largest count these scripts handle by
   construction, if that is visible?
5. Layout dependence: which layout root, part, group and pane names are passed to the
   scroller or used for rows? List them exactly. Do not open layout archives; names only.
6. Scrolling and paging: which input constants and scroller methods implement cursor
   movement, held-repeat and page jumps?
7. Sweep of all 86 chunks: which other chunks call any of the methods found in question
   2 or 3 on any object, and which chunks set text on a pane whose name is built with a
   row index (`string.format` with `%d` / `%02d` followed by a pane or part lookup)?
   Give a table: chunk, object or global name, row-fill evidence yes/no, count source.
   The purpose is to find the simplest screen in the game where Lua owns a list of text
   rows.
8. For the single simplest such screen: the complete list of host globals and bridge
   names it needs (read but never written), so a later task can judge whether the same
   objects exist in the Mii maker scene. State clearly that existence in another scene
   is unverified.

Deliverables: research/P8-LUA-LIST.md; evidence/P8-LUA-LIST/ with raw tool output and a
check script that re-derives every cited pc, opcode, constant and argument count from the
chunk bytes, exits non-zero on mismatch, and has at least three negative controls that
you ran (state their observed results). Run the check from the workspace root and paste
its last lines into the report.

Not in scope: native code, layout archive contents, editing or compiling any chunk,
proposing a design.

Exclusive writes: research/P8-LUA-LIST.md, evidence/P8-LUA-LIST/,
scratch/2026-10-05_P8-LUA-LIST/, workspace gamedata/mii_customizer/P8-LUA-LIST/.
