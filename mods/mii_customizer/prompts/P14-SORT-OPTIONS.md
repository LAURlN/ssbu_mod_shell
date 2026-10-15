# P14-SORT-OPTIONS - plugin 0.7.0: working "sort by name", and option pages (first: Sword)

Plugin task. Recommended: Claude Opus 5.5 or GPT 6.1 Sol (GPT 6 Luna if the user prefers).
Follow workspace AGENTS.md, mods/mii_customizer/AGENTS.md and STATUS.md. No agents, commits,
branches, emulator, SD access, framework-plugin changes; do not install anything. Paths are
relative to mods/mii_customizer/ unless marked workspace-relative; create every folder
INSIDE mods/mii_customizer/. Use `python`; write scripts with the file tool (no heredocs).
WRITE research/P14-SORT-OPTIONS.md FIRST as a skeleton and extend it after every step;
deliver tests and the check script before polishing. End with task ID,
DONE/PARTIAL/BLOCKED, changed files, what you could not verify.

Where we are (console, tier A): plugin 0.6.0 works. Minus on the Mii edit menu opens the mod
menu on the native headgear list: a main page with one row per `menu.txt` entry ("Stats:
Kirby", "Jab: Mii Gunner", ...), each opening a character page (row 0 = Mii Gunner default,
then the 86 rows of `list.txt` in fighter order; on `slot` pages every row without an
`allow` line is greyed). Read: research/P11-MENU.md (design, hooks, proofs, with the
coordinator banner), plugin/src/*.rs (0.6.0: `names.rs`, the Minus code and the composed row
text are newer than that report; see the last sections of
research/COORDINATOR-2026-10-04.md), prompts/P11-MENU.md (contracts M and G stay in force
unless changed below), evidence/2026-10-07_session3/RESULT_boot2.md, research/P6-HAT-UI.md
sections 4.3 and 5.2 (the sort sub-window of the list script) and research/P8-HAT-NATIVE.md
(native `sort_id_list` handler 0x19cd100: modes 0..2 sort, others return at once). Image:
workspace gamedata/ssbu-13.0.4/main.bin (flat, address == file offset); disassembler from
the workspace root: `PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python
mods/mii_customizer/scratch/2026-10-04_P1-ID-REVIEW/d.py win <addr> <n>` (the path is under
mods/mii_customizer/, not mods/ssbu_mod_new/).

## Part 1 - sorting (user request)

"Make the sort by name option actually work, and the other options just sort the way it's
sorted right now (fighter numbers)."

Today the plugin turns every `sort_id_list` request into mode 3 while its list is open
(`hook_sort`), so the sort window opens, the label changes, and nothing is reordered.

S1. Facts first: the sort window's options on this screen (how many, their order, their
    texts and labels, which mode number each sends to `sort_id_list`), from the list script
    and the native handler; which one is "by name". What the script does around a sort
    (`backup_list_selected_id`, `sort_id_list`, `redraw_all_items`, `select_list_from_backup_id`,
    `get_top_index`, the sort label pane) and what each of those does natively on OUR list
    (synthetic handles), so cursor and tick end up on the right rows after a re-sort.
S2. Behaviour on a CHARACTER page (stats and slot pages): the "by name" option orders rows
    1..N alphabetically by display name (names.txt text, compared case-insensitively,
    byte order after ASCII folding is acceptable; a preset without a name sorts by its
    preset name); every other option gives fighter order (list.txt order). Row 0 (the
    default) always stays first. The tick stays on the same character, the cursor stays on
    the same character, greyed rows stay greyed, and a decided row must resolve to the
    right preset in every order (the row -> list entry mapping is the thing to get right;
    prove it with tests that decide every row in both orders). The chosen order persists
    across pages of one visit and across visits until the game is closed; it is not saved.
S3. The MAIN page and option pages (part 2) are never reordered: sort requests there keep
    today's behaviour.
S4. Proof obligations as in P11: no handle of ours reaches native code that would
    dereference it; the E3 invariant (the Mii's headgear handle and working record are
    unchanged by a visit) holds with sorting; no allocation or file IO per frame; log one
    line per sort (`mc|UI|sort|page=..|mode=..|order=name/number|cursor=..|tick=..`).

## Part 2 - option pages, first use: Sword (user request)

"Add an option to select the sword for the fighter (the sword will only be visible during
sword moves and the selected sword will be used for all this character's sword moves along
with its effects); for now the only option is the default Mii Swordfighter sword."

No sword move exists on a Gunner yet, so this build adds the MENU side only; what the choice
does in a match comes with the first borrowed sword move (research in parallel:
P14-SWORD-FACTS). Contract G gains a third entry kind and one line type:

  `entry <id> option <text>`            a page whose rows are this entry's own options
  `option <id> <option_id> <text>`      option_id [a-z0-9_]{1,31}, unique per entry; text as
                                        for an entry; file order = row order; at most 32 per
                                        entry; the FIRST option of an entry is its default.
  `label` may follow an `option` line?  No: options have literal text only; say in the report
                                        what a row shows with `text_off`.

O1. An option page lists the entry's options, all available, cursor and tick on the current
    choice (the default while nothing is stored). A on a row returns to the main page; B
    returns without change. The main-page row shows "<entry text>: <option text>".
O2. Storage: propose AND implement the loadout key for an option choice, since a page with
    a real choice needs one: version `mc_loadouts 3`, line `<id> option <entry_id>
    <option_id>`; absent = default; choosing the default removes the line; a line naming an
    unknown entry or option is rejected and logged; a version 2 file is still read; the
    writer emits version 3 only when at least one option line exists, otherwise version 2
    as today (so a rollback to 0.6.0 keeps reading the file while nothing is chosen). State
    the capacity (IDs x entries) and what happens when it is full. With today's menu there
    is one option, so nothing is ever written; the tests must cover a menu with several.
O3. An entry of kind `option` with no valid option line is rejected with a reason. The
    literal-text route for option rows is the main page's (set after every fill).
O4. The coordinator ships the real file: `entry sword option Sword` +
    `option sword miiswordsman Mii Swordfighter`. Put the same in the example file.

## Engineering rules (as P11)

All-or-nothing hook install after word compares, with the 0.5.1 rule for called-only
entries; switch files `ui_off`, `text_off`, `minus_off` keep working; every dereference
proven or checked; flushed, bounded `mc|UI|` lines; on any failed check fall back to the
0.6.0 behaviour for that feature and say so in the log.

## Deliver

Version 0.7.0 in builds/0.7.0-menu/ (NRO, MANIFEST.json, example/menu.txt) via
build-plugin.sh. Host tests for everything new (sort mapping in both orders with greyed
rows and with a preset that is not in the list; option pages; the parser additions; loadout
v3 read/write/rollback cases; the names used for sorting), with the existing 47 + 35 + 4
tests still passing; a mutation control over the new logic. A check script
evidence/P14-SORT-OPTIONS/check_p14.py that re-reads from main.bin every site, probe,
offset and call target the 0.7.0 plugin uses (start from evidence/P11-MENU/check_p11_menu.py,
which is bound to 0.5.0; also cover what 0.5.1-0.6.0 added: the accepted foreign hook at
0x37a22f0, the Minus global through 0x33750a0 on [[inner+0x40]], nn::hid use) and checks the
NRO and manifest; negative controls; exit 1 on mismatch. Report: design in one page, the S1
facts with addresses, the row mapping and its proof, the loadout v3 contract as implemented,
a console test of at most 8 steps with the log lines that prove each, failure patterns,
rollback (0.6.0 NRO `f44fc278...`), and a plain list of everything that is tier D.

Not in scope: Lua, layout or message files; integer parameters; any move or sword model;
removing characters from list.txt (P14-LIST-PLAYABLE does that; your code must not depend on
the row count).

Exclusive writes: plugin/, build-plugin.sh, builds/0.7.0-menu/, builds/.cache/,
research/P14-SORT-OPTIONS.md, evidence/P14-SORT-OPTIONS/, scratch/2026-10-07_P14-SORT-OPTIONS/.
