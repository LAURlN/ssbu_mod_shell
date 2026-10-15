# P5-UI-API - inventory of the UI script API the game's own Lua scripts use

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md. Work only on the task below. No agents,
commits, branches, emulator, SD access, framework changes or edits to other workers'
files. Inputs remain read-only. Report exact inputs/hashes, commands, observed
checks, failures and limits. B is offline observation, C pinned source, D
hypothesis; no runtime behavior claims. Coordinator owns
STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report and chat with task
ID, DONE/PARTIAL/BLOCKED, changed files and next experiment. All paths below are
relative to mods/mii_customizer/ unless marked workspace-relative. Create every
folder INSIDE mods/mii_customizer/ and make scripts write there, never into the
current directory. Use `python`, not `python3`.

Background. The mod will add logic to the Mii special-move screen's Lua script.
We know the handful of calls that script already makes (research/P2-UI-FLOW.md).
To write new screen logic we need to know which other calls the game's own UI
scripts make on the same kinds of objects: text panes, layout views, selectors,
virtual input, sound. The safest vocabulary is one the game already uses.

One goal: a machine-generated inventory of method names, global names and call
shapes used across the game's UI Lua scripts, with emphasis on (a) putting text
into a pane, (b) reading input buttons, (c) showing/hiding and animating parts.
Inventory task. Do not design anything and do not write mod logic.

Inputs. The archive path index workspace-relative
mods/ssbu_mod_new/dumps/decoded/arc_files.tsv (read that repo's AGENTS.md first;
read-only). Select every path under `ui/script/` and `ui/script_patch/` ending in
`.lc`; report the count. Extract them with the existing workspace tool
tools/arc-extract from workspace-relative gamedata/ssbu-13.0.4/data.arc into
workspace-relative gamedata/mii_customizer/P5-UI-API/ (see
kb/playbooks/extracting-single-files-from-data-arc.md). Record size and sha256 per
file in a manifest. If there are more than 400 scripts, extract all of
`ui/script/menu/` and `ui/script_patch/` plus `ui/script/common/` and say what was
left out.

Tools: tools/lua53-inspect (parse, constants, dis; use it as a library) and
tools/luac53-game/bin/luac-game.exe `-l -l` if you prefer its listing. Every chunk
must pass lua53-inspect `verify`; list any that does not and exclude it.

What to extract, by a script, from the bytecode (not by reading strings alone):
1. Method calls: every `SELF` instruction gives a method name (constant operand).
   Count per name, number of scripts using it, and the argument count from the
   following `CALL` (B operand) as a histogram. For the three most common argument
   shapes per name, show one example with script path, prototype and pc, including
   the kinds of the arguments when they are constants or `LOADK`/`LOADBOOL`
   immediately before the call (string / integer / float / boolean / other).
2. Global reads and writes: `GETTABUP`/`SETTABUP` on the `_ENV` upvalue with a
   constant key. Count per name, read/write counts, scripts. Separate names that
   are written by some script (script-defined) from names only ever read
   (host-provided, as far as these scripts show).
3. Field calls: `GETTABLE`/`GETTABUP` of a constant field followed by `CALL`
   without `SELF` (for example `UiScriptPlayer.invoke`, `string.format`). Same
   statistics. For `invoke`, list the distinct first-argument strings (bridge
   names) with counts and scripts.
4. Focus lists, taken from 1-3 and printed as separate tables:
   a) every method whose name contains `text`, `string`, `message`, `number`,
      `label` (case-insensitive);
   b) every global whose name starts with `INPUT_` or contains `PAD`, `BUTTON`,
      `KEY`, and every method containing `press`, `trigger`, `repeat`, `release`,
      `hold`, `input`, `cancel`, `decide`;
   c) every method containing `visible`, `anim`, `enable`, `focus`, `select`,
      `parts`, `pane`.
   For 4a give, per method, three real call examples with their constant
   arguments, so a reader can see whether a method takes a message key or a
   literal string.
5. For the globals of 4b: search workspace-relative gamedata/ssbu-13.0.4/main.bin
   (sha256 f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613) for
   each name as a NUL-terminated string and report whether it occurs and how many
   adrp+add code references it has (reuse refscan9.py from
   scratch/2026-10-04_P2-UI-CONSTS/, copied, not edited). For names registered
   through `bl 0x33750a0` with an immediate in w3 right before the call (the
   pattern research/P2-UI-CONSTS.md documents), report the value. Cap this step at
   60 names; say which were skipped.

Deliver evidence/P5-UI-API/ui_api.json (everything), research/P5-UI-API.md (the
tables of step 4, top-40 lists for steps 1-3, limits) and a check script that
regenerates the JSON from the extracted chunks and compares. State limits
plainly: a name's presence shows the game calls it somewhere, not what it does,
not that it exists on every object, and not that it is safe in the Mii editor.

Exclusive writes: research/P5-UI-API.md, evidence/P5-UI-API/,
scratch/2026-10-05_P5-UI-API/, workspace-relative gamedata/mii_customizer/P5-UI-API/.
