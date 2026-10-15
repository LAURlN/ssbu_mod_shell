# P11-MENU - premium: plugin 0.5.0, customization menu with pages + finish 0.4.0's proofs

For Claude Opus 5.5 or GPT 6.1 Sol. Follow workspace AGENTS.md, this mod's AGENTS.md
and STATUS.md. No agents, commits, branches, emulator, SD access, framework-plugin
changes or edits to other workers' files. Do not install anything. Paths are relative to
mods/mii_customizer/ unless marked workspace-relative; create every folder inside
mods/mii_customizer/. Use `python`; write scripts with the file tool (no heredocs).
The previous task on this plugin stopped without a report: WRITE THE REPORT FIRST as a
skeleton and extend it after every step, and deliver tests and the check script before
polishing. End with task ID, DONE/PARTIAL/BLOCKED, changed files, what you could not verify.

Where we are (console, tier A, evidence/2026-10-06_session2/RESULT.md): plugin 0.4.0 works.
Favorite on the Headgear row of the Mii editor opens the native headgear list showing 88
plugin rows instead of 52 hats; decide sets a character stat preset for the edited saved
Mii, applies it without reboot and saves loadouts.txt; cancel changes nothing; the Mii's
headgear and working record were bit-equal before and after, four times out of four.
Read research/P10-UI-SLICE.md (coordinator-written; the design as read from the source),
plugin/src/*.rs, research/P10-HAT-OPEN.md (with the coordinator banner), prompts/P10-UI-SLICE.md
(contracts E, F, B+ stay in force unless changed below), research/P9-EDIT-DISPATCH.md
sections 3-5. Image: workspace gamedata/ssbu-13.0.4/main.bin; disassembler from the workspace
root: `PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python
mods/mii_customizer/scratch/2026-10-04_P1-ID-REVIEW/d.py win <addr> <n>`.

## What the user asked for (their words, 2026-10-06)

"Instead of opening a character selection, we open a menu containing things like [Stats,
Jab, Forward Tilt, etc.] and then when you select one of those it opens a list of characters
you can pick those from. It's important that it doesn't show all characters, or maybe does
show all, but all the ones where we haven't implemented the moves yet are greyed out. So for
now the Mii Gunner (default) is the only available one and selected by default."

## Contract M (coordinator-owned): pages

M1. Mod mode (ways in A and B unchanged) opens the MAIN page on the native headgear list:
    one row per menu entry (contract G), in file order. A on a row opens that entry's page.
    B leaves mod mode back to the edit menu, as cancel does today.
M2. An ENTRY page lists: row 0 = the default (the Mii's own class; label
    `nam_chr1_00_miigunner`), then one row per list.txt entry (contract F).
    - kind `stats`: every row is available. A sets the preset (row 0 clears it) exactly as
      0.4.0 does (store update, save), then returns to the main page. Cursor and tick start
      on the Mii's current preset, else row 0.
    - kind `slot`: a row is available only if the entry has an `allow` line for that preset.
      Today no entry has one, so only row 0 is available, and it carries the tick and the
      cursor. Unavailable rows are shown greyed out with the game's own look for an
      unavailable item and cannot be decided: A on one must change nothing and must not open
      any popup, shop or dialog (find out what the game does for such a row and prevent
      anything beyond "nothing happens", a refusal sound is fine). A on an available row
      returns to the main page. Nothing is stored for slot entries in this build; do not
      invent a loadout key (propose one in the report).
    - B on an entry page returns to the main page, cursor on the entry it came from.
M3. How a page change happens is your design: re-entering the headgear state (the state
    stack of P9-EDIT-DISPATCH section 4/5), resetting the list in place, or something
    better evidenced. A visible close/re-open transition is acceptable; a crash, a stuck
    screen, a lost edit-menu return path or a state-stack leak is not (the stack is 19 deep
    and traps beyond; show that N page changes leave its depth where it was).
M4. Contract E3 holds across the whole visit, however many pages: the Mii's headgear handle
    and working record at the end equal those at the first arm; logged once per visit, and
    every page change logged (`mc|UI|page|from=..|to=..|depth=..`). E4 holds: normal headgear
    and outfit screens untouched.
M5. Row text. Menu entries carry literal text (G). The 0.4.0 label hook can only show an
    existing message label. Find the native path that puts a literal string on the row's
    text panes (Lua has `set_text_string`, 3 call sites, research/P5-UI-API.md; the row
    filler 0x19ccb20 sets `set_txt_val` and `set_txt_val_disable` through 0x3776360 /
    0x3779b70) and use it for rows that have literal text. If you cannot make that safe with
    evidence, use each entry's optional `label` (an existing message label) and say so
    plainly. Task P11-ROW-TEXT studies the same question in parallel; use
    research/P11-ROW-TEXT.md if it exists when you need it, after checking it; do not wait.

## Contract G: menu file (new)

sd:/ultimate/mii_customizer/menu.txt, read once at load, never written, at most 16 KiB.
Line 1 exactly `mc_menu 1`. Then, `#` comments and blank lines allowed, `\n` or `\r\n`:
  `entry <id> <kind> <text>`   id [a-z0-9_]{1,31}, unique; kind `stats` or `slot`; text =
                               rest of the line, trimmed, 1..40 bytes of printable UTF-8.
                               At most 48 entries; at most one `stats` entry.
  `label <id> <message_label>` optional fallback label [a-z0-9_]{1,63} for that entry.
  `allow <id> <preset_name>`   that preset is available on that slot entry's page.
A malformed line, an unknown id or preset, a duplicate: that line is rejected and logged,
the rest stay. File absent, bad first line or no valid entry: mod mode opens the character
list directly, exactly as 0.4.0 (one implicit `stats` page, B leaves). The coordinator ships
the real file (Stats + 23 move slots); write a small one for tests and the example.

## Also owed from 0.4.0 (do these early)

- Host unit tests for list.rs, ui.rs (synthetic handles, outcome, action, mode state
  machine, clamp_selected, same_item, label struct), Store::set_preset with a concurrent
  resolve, loadout::load (B+), the new menu parser and the page state machine; the 0.3.0
  tests in scratch/2026-10-05_P7-PRESET-ENGINE/ must still pass. A mutation control.
- A check script evidence/P11-MENU/check_p11_menu.py (exit 1 on mismatch, negative controls)
  that re-reads from main.bin every site, probe, offset and call target the plugin uses and
  checks the NRO; scratch/2026-10-05_coordinator/check_ui_sites.py is a minimal start.
- Known wrong statements to keep out of your reasoning: 0x328b5d0 returns 1 for a handle
  that is NOT in the table; the headgear static has two writers (0x180ac3c, 0x180ad20), and
  cancel restores it through S+0x148.

## Engineering rules (as P10, restated)

All-or-nothing install after word compares; `ui_off` switch file; every dereference proven
or checked; no file IO or allocation per frame; flushed, bounded `mc|UI|` lines so a crash
is locatable; on any failed check fall back to "normal headgear screen". If pages cannot be
made safe, ship the smallest safe reduction (for example: main page only for kind `slot`
entries shown greyed with the stats list reachable) and say exactly what is reduced; do not
switch to another screen.

## Deliver

Version 0.5.0 in builds/0.5.0-menu/ (NRO, MANIFEST.json, example/menu.txt) via
build-plugin.sh (add the variant name). Report research/P11-MENU.md: design in one page,
each hook and each game call with its proof, the M3 mechanism with the state-stack argument,
the E3 argument, what a greyed row does on A, the row-text route taken, a console test plan
of at most 10 user steps (main page, a slot page with only Mii Gunner available, a greyed
row, the stats page with a choice and a clear, B at each level, ten page changes in a row,
the normal hat screen, a match, a reboot), the log lines that prove each, failure patterns,
rollback (0.4.0 NRO `d28aea75...`), and a plain list of everything that is tier D.

Not in scope: Lua, layout or message files; integer parameters; implementing any move;
other Mii classes; a new edit-menu row.

Exclusive writes: plugin/, build-plugin.sh, builds/0.5.0-menu/, builds/.cache/,
research/P11-MENU.md, evidence/P11-MENU/, scratch/2026-10-06_P11-MENU/.
