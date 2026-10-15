# P6-HAT-UI - how the Mii maker's headgear/outfit selection screen works (script side)

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

Background. The user wants the mod's settings chosen in the Mii maker from long
scrolling lists, and named the headgear selection screen as the model to build on,
because the mod will offer many options per setting (first use: "use the stats of
character X", about 90 entries). We have traced the special-move screen
(research/P2-UI-FLOW.md) but not the headgear/outfit screen.

One goal: a bytecode-level description of the headgear/outfit selection screen:
how its list is filled, scrolled, labelled and confirmed, and every point where it
talks to native code. Tracing task, like P2-UI-FLOW. Do not design the mod screen
and do not edit any chunk.

Inputs. Extract with workspace tool tools/arc-extract from workspace-relative
gamedata/ssbu-13.0.4/data.arc into workspace-relative
gamedata/mii_customizer/P6-HAT-UI/ (record size and sha256):
  ui/script/menu/chara_make/make_mii_hat_actor.lc
  ui/script/menu/chara_make/make_mii_hat_body_layout.lc
  ui/script/menu/chara_make/make_mii_utility.lc
  ui/script/menu/chara_make/make_mii_body_actor.lc
If gamedata/mii_customizer/P5-UI-API/ already holds them (another task extracted
all UI scripts), you may read those copies instead; say which you used. Check the
archive index (workspace-relative mods/ssbu_mod_new/dumps/decoded/arc_files.tsv;
read that repo's AGENTS.md first) for `ui/script_patch/` versions of these four
and report whether any exists; if one does, analyse the patch version and note
differences in prototype and instruction counts only.

Tools: tools/lua53-inspect (verify, protos, constants, dis, xref) and
tools/luac53-game/bin/luac-game.exe `-l -l`. Every chunk must pass `verify`.
research/P5-UI-API.md, if present, lists API names used across all UI scripts;
use it for context, the bytecode is the authority.

Questions, each answered with chunk, prototype and pc ranges:
1. Structure: what each of the four chunks exports to `_ENV` (functions, tables),
   which chunk calls into which (the hat actor versus the hat_body_layout chunk
   versus make_mii_utility), and which globals each reads that it never writes.
2. The list: which object represents the scrolling list (constructor name, setup
   calls and their constant arguments, part/pane names), how many rows are visible
   versus total (where the total count comes from: a global, an invoke, a table
   length), and how a row is filled when it scrolls into view (the callback or
   loop, and each call it makes: text, icon/texture, "new"/"equipped" marks).
3. Native bridge: every `UiScriptPlayer.invoke` (or other host call) with its name
   string, argument count, argument provenance and use of the return value. Group
   them: item count / item info / label / icon / preview on the Mii model /
   confirm / cancel / category switch.
4. Input: how cursor movement, page scrolling, confirm and cancel are detected
   (method names, input constants), and what the script does on confirm (which
   bridge call commits the choice, what state it enters).
5. Categories or tabs: does the screen switch between headgear and outfit (or
   other groups) inside one script? Show the branch points and what changes.
6. Text: for row labels and the title, is the text set from a message key
   (`set_text_message` or similar with a string) or from something a bridge call
   returns? Show examples with constants.
7. What is NOT in Lua: list the things the script clearly leaves to native code
   (for example a list widget that scrolls itself), judged only from which calls
   exist and which do not.
8. Class check: is any Mii class or fighter kind read anywhere in these chunks?

Deliver research/P6-HAT-UI.md with a call-flow table (chunk/proto, pc range, role,
arguments and provenance, return usage, unresolved native behaviour), a list of
bridge names with argument counts, and an "unresolved edges" section. Add a check
script that re-derives every cited pc/operand from the chunks and exits nonzero on
mismatch. Mark every statement about what a native call does as D.

Exclusive writes: research/P6-HAT-UI.md, evidence/P6-HAT-UI/,
scratch/2026-10-05_P6-HAT-UI/, workspace-relative gamedata/mii_customizer/P6-HAT-UI/.
