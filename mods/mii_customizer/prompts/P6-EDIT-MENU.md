# P6-EDIT-MENU - how the Mii maker's main edit menu defines its entries and opens sub-screens

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md (last sections). Work only on the task
below. No agents, commits, branches, emulator, SD access, framework changes or
edits to other workers' files. Inputs remain read-only. Report exact inputs/hashes,
commands, observed checks, failures and limits. B is offline observation, C pinned
source, D hypothesis; no runtime behavior claims. Coordinator owns
STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report and chat with task
ID, DONE/PARTIAL/BLOCKED, changed files and next experiment. All paths below are
relative to mods/mii_customizer/ unless marked workspace-relative. Create every
folder INSIDE mods/mii_customizer/ and make scripts write there, never into the
current directory. Use `python`, not `python3`.

Background. The user wants one new entry in the Mii maker's edit menu that opens
the mod's settings (ideally a proper sub-menu). The edit menu is driven by
ui/script_patch/chara_make/make_mii_edit_actor.lc (the patched version is the one
the game uses; the base version is ui/script/menu/chara_make/make_mii_edit_actor.lc)
and the layout ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc. Earlier
tasks looked at flags in this script (research/P2-UI-FLOW.md section 6,
research/P1-UI-DECODE.md) but nobody has described how its entries are built or
how choosing one opens the headgear, outfit, voice or special-move screen.

One goal: describe, from bytecode and layout bytes, how the edit menu's entries
are defined and what happens when one is chosen. Tracing task. Do not design the
new entry and do not edit any file.

Inputs (workspace-relative, already extracted; re-hash them):
  gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc
    (sha256 c777ecc492cea48f6ffd40112b22f96e66219d00969b570a7cc3cf8d7f4a9417)
  gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_edit_actor.lc
  the edit layout: locate ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc
  under gamedata/mii_customizer/P1-UI/ or P1-LAYOUT/; if it is not there, extract
  it with workspace tool tools/arc-extract into workspace-relative
  gamedata/mii_customizer/P6-EDIT-MENU/ and record size and sha256.
Tools: tools/lua53-inspect, tools/luac53-game/bin/luac-game.exe `-l -l`,
tools/sarc-layout and tools/bflyt-inspect (read their READMEs; use, do not edit).

Questions. Analyse the PATCH script; mention the base script only where it
differs. Cite chunk, prototype and pc ranges, or layout member and byte offsets.
1. Selectors and buttons: every `LayoutButtonSelector` (or similar) the script
   creates, the group name passed to `setup`, and every `setup_button` call with
   its part name, in order. Which of them form the main vertical/grid menu the
   player navigates? Give the button index each part gets.
2. For each main-menu button: what the script does when it is decided. Follow the
   decided button id to the branch that handles it and report the calls made
   (bridge names passed to `UiScriptPlayer.invoke`, state changes, animations,
   sounds). In particular find how the special-move screen and the headgear and
   outfit screens are opened: a bridge call with a name, a state id, a scene
   request? Show the instruction ranges. research/P2-UI-FLOW.md edge 3 notes that
   no `make_mii_special` string occurs in this chunk; say what is passed instead.
3. Conditions: which buttons are hidden, disabled or skipped under which flags
   (`IS_READ_ONLY`, `IS_SKILL_EDITABLE`, `FROM_AMIIBO`, others). One table.
4. Texts: where each button's label comes from (layout text with a message id
   stored in the layout, or a script call with a key).
5. Layout: in the edit layout's main `.bflyt`, list the parts that correspond to
   the buttons of question 1 (name, parent, position, size, the layout file each
   part references) and the selector groups (`grp1` or equivalent) with their
   member lists. State how many button parts exist that the script never sets up,
   if any (spare parts would matter for adding an entry). List the animation
   files in the archive whose names mention these parts.
6. Return path: when a sub-screen closes, what brings control back to this menu
   (a state the script waits in, a bridge call it polls)?
7. What a new entry would have to touch, as a plain list of facts, not a design:
   the places in this script that hold a button count or iterate over buttons, the
   layout structures that would need an additional part or group member, and any
   native call that receives a button index or count.

Deliver research/P6-EDIT-MENU.md with: a table of menu entries (index, part name,
label source, condition, action when decided), the open/return mechanism for
sub-screens, the layout part table, and an "unresolved edges" section. Add a
check script that re-derives every cited pc/operand and layout offset and exits
nonzero on mismatch. Mark statements about native behaviour as D.

Exclusive writes: research/P6-EDIT-MENU.md, evidence/P6-EDIT-MENU/,
scratch/2026-10-05_P6-EDIT-MENU/, workspace-relative
gamedata/mii_customizer/P6-EDIT-MENU/.
