# P10-UI-SLICE - premium: plugin 0.4.0, character list in the Mii maker + saving

For Claude Opus 5.5 or GPT 6.1 Sol. Follow workspace AGENTS.md, this mod's AGENTS.md
and STATUS.md. No agents, commits, branches, emulator, SD access, framework-plugin
changes or edits to other workers' files. Do not install anything; the coordinator
packages and installs. All paths are relative to mods/mii_customizer/ unless marked
workspace-relative; create every folder inside mods/mii_customizer/. Use `python`,
write scripts with the file tool (no heredocs). Start the report file early and extend
it; end with task ID, DONE/PARTIAL/BLOCKED, changed files and what you could not verify.

Where we are (console, tier A, evidence/2026-10-05_session1/RESULT.md and
RESULT_boot2.md): plugin 0.3.0 gives a saved Mii Gunner the ten movement stats of a
named character preset from sd:/ultimate/mii_customizer/presets.txt, chosen per saved
ID in loadouts.txt; explicit lines win; two Miis with different presets work. The user
edits that file on a PC. The user now wants to pick the character INSIDE the Mii maker
from a long list built on the headgear selection screen. That is this task: the first
build in which the choice is made and saved in the game. It is the main milestone.

Read first: HANDOFF.md (sections 5, 6), research/P9-HAT-HANDLES.md (all),
research/P8-HAT-NATIVE.md (correction banners, sections 3-8), research/P9-EDIT-DISPATCH.md
(sections 1-5, 7), research/P6-HAT-UI.md (sections 2, 4, 13), research/P7-PRESET-ENGINE.md
(sections 1-3, 7), plugin/src/*.rs, plugin/README.md, workspace
kb/reference/cargo-skyline.md. Image: workspace gamedata/ssbu-13.0.4/main.bin (flat;
address == file offset == hook offset). Disassembler, from the workspace root:
`PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python
mods/mii_customizer/scratch/2026-10-04_P1-ID-REVIEW/d.py win <addr> <n>`.
Earlier reports are tier B at best and contain corrected errors: re-read every
instruction your hooks depend on and put those reads in your own check script.

## What the user must see (contract E, coordinator-owned)

E1. In the Mii Fighters editor of a saved Mii Gunner, "mod mode" opens the NATIVE
    headgear list screen showing characters instead of hats: row 0 = no preset, then
    one row per entry of the list (contract F), text from the game's own message
    labels. It scrolls like the hat list.
E2. Deciding a row sets that preset for the edited Mii (saved ID = u32 at static
    0x5306b78, the editor working record), row 0 clears it (explicit weight /
    walk_speed_max lines of that ID stay), updates the in-memory store so the next
    match uses it without a reboot, and writes loadouts.txt with save_loadouts().
    Cancel changes nothing. Saved ID 0 (a Mii not saved yet): no store change, no
    write, one log line, the screen closes normally.
E3. HARD INVARIANT: mod mode never changes the Mii. The headgear handle in static
    0x5306cb0, the outfit, and every other field of the working record are bit-equal
    when mod mode ends to what they were when it began, the preview model does not
    change hat while the cursor moves, and no synthetic handle can reach the save.
    Enforce it in code (snapshot at arm, verify/restore at exit) and log both values.
    These are the user's real saved Miis.
E4. Without mod mode armed, every hook passes its arguments to the original unchanged
    and the hat and outfit screens behave as shipped.
E5. Two ways in; build both unless one is shown to be unsafe (say which and why):
    A. the edit-menu script publishes exit value 7 (task P10-EDIT-ENTRY builds that
       script; decided earlier: values >= 9 trap at 0x180cf00, 7 is benign without the
       plugin). The plugin turns 7 into 1 (open headgear) before the dispatcher
       0x180a030 uses it (value read at 0x180a098) and arms mod mode.
    B. plugin only, no script: the exit value is already 1 (Headgear row decided) and
       ZL or ZR is held on any connected controller or in handheld at that moment
       (read through the nn::hid npad state API or a better-evidenced source; you
       choose and justify). B exists because it is not yet known whether a replaced
       edit-menu chunk loads on the console.
    Mod mode is disarmed when the headgear state ends, however it ends.
E6. Nice to have, only if it falls out of the design: cursor starts on the Mii's
    current preset and that row carries the tick. Sorting (sort_id_list) does nothing
    in mod mode. The screen title and help text may stay "Headgear" in this build.

## Contract F: list file (new), and one change to contract B

F. sd:/ultimate/mii_customizer/list.txt, read once at load, never written, at most
   16 KiB: line 1 exactly `mc_list 1`; then `<preset_name> <message_label>` per line in
   display order; `#` comments, blank lines, spaces or tabs, `\n` or `\r\n`;
   preset_name as in contract A; label [a-z0-9_]{1,63}; at most 128 entries. A line
   naming a preset that is not loaded, a duplicate preset or a malformed line is
   rejected and logged; the rest stay. File absent or bad first line: the list is all
   loaded presets in file order with label `nam_chr1_00_<name>`. (P10-PRESET-WIDE
   generates the file; write a small synthetic one for tests.) Row 0 uses an existing
   label you pick by evidence (msg_name.msbt has nam_mii_hat_none_m / _f).
B+. At load, if loadouts.txt does not exist and loadouts.new exists and parses, read
   loadouts.new as the loadout file and log that; this closes the window in P7 section 3.
   Nothing else in contracts A-D changes; presets.txt may now carry up to 48 fields.

## Known facts to build on (B unless marked; verify what you use)

- Scene: Mii editor scene built by 0x1808980 (state 0), six children; headgear list
  object at scene+0x180 from ctor 0x19ceb30, built ONCE per editor scene. State stack at
  scene+0xf8, index +0x144; dispatcher 0x180a030 pushes value+4; headgear state 5 =
  0x180abd0.
- List: sub-object S = [list object+0x80] (0x170 bytes). Items = std::vector of 8-byte
  handles at S+0x128 (tag 0x5a, 40-bit hash), filled in the ctor via 0x3274c50. Slots
  S+0x140 previous, +0x148 previewed/decided, +0x150 selected, +0x158 backup, +0x169
  flag. Row filler 0x19ccb20 (w1 = row, x2 = row node) builds the message key through
  0x3288330 (`nam_mii_hat_%s`; unknown handle -> `nam_mii_hat_unknown`, no trap) and
  sets it on `set_txt_val` / `set_txt_val_disable`; ownership test 0x328b5d0 returns 0
  for unknown handles. Frame callback 0x19cc3f0 (stored at [S+0x88]) turns the Lua
  layout's decided row into the handle at +0x148; state 5 compares it with the static
  0x5306cb0 and WRITES the static at 0x180ad20, then 0x180cf10.
- The item count is fixed at construction: SCROLLER_ITEM_NUM is registered as a Lua
  constant (0x19cf854) and the scroller is built by 0x3781470 in the ctor. Making the
  count follow mod mode is part of your design problem.
- Both label families are in ui/message/msg_name.msbt (131 nam_mii_hat_*, 107
  nam_chr1_00_*), so no message file needs changing. Do not rely on added labels: an
  added msg_menu label did not resolve on this console's ARCropolis (4.0.x era).
- Open (D), resolve what your design needs: who pumps 0x19cc3f0; the owner of the
  row-callback vtable 0x50a6b18 (coordinator guess: it is the secondary vtable of S at
  S+0x48, 0x50a6ae0+0x38, since its thunk subtracts 0x48); the cancel/restore path; the
  commit of 0x5306cb0 into the save (0x180d4cc, 0x180d734); state 0x180d2a0. Task
  P10-HAT-OPEN studies these in parallel; if research/P10-HAT-OPEN.md exists when you
  need a fact, use it after checking it, but do not wait for it.
- Plugin: the store is atomics-only with no runtime writer yet; OV/L3 once-marks will
  hide a changed preset unless you reset them; save_loadouts() has never run on the
  console (File::create over an existing path, sync_all, remove_file, rename untested).
  The editor preview fighter has saved ID 0 in the slot and gets vanilla stats (A).

## Engineering rules

- Each new hook site: compare the instruction words you replace with the 13.0.4 image
  before patching, as install_site does. If ANY UI site mismatches, install none of the
  UI hooks; the stat engine must still load. If sd:/ultimate/mii_customizer/ui_off
  exists, install none of the UI hooks either. Prefer few hooks and inline (mid-
  function) hooks only where the register state is proven in your check script.
- No guessing at pointers: every dereference in a hook is either proven by the image
  or null/range-checked. A wrong assumption must end in "normal hat screen", not in a
  crash or a changed Mii.
- File IO only at decide time, never per frame. No allocation in per-frame hooks.
- Log `mc|UI|` lines, flushed per line and bounded: sites installed; arm (entry A/B,
  saved id, hat handle before); list built (count, first label); decide (row, preset
  name) or cancel; exit (hat handle after, equal=0/1); `mc|SV|` from the save with the
  step that ended it. A crash must be locatable from the last line.
- If the native list cannot be made to satisfy E3/E4 with evidence you can defend,
  STOP and report PARTIAL or BLOCKED with that evidence and the smallest reduced
  variant you would ship. Do not switch to another screen or an external editor.

## Deliver

Version 0.4.0, builds/0.4.0-ui/ (NRO, MANIFEST.json, example/list.txt synthetic),
built with build-plugin.sh. Host unit tests for the list parser, B+, the store update
(set/clear preset, concurrent resolve), serialise round trip after an update, and the
mode state machine (arm, decide, cancel, disarm, ID 0); a mutation control; a check
script (exit 1 on mismatch, with negative controls) that re-reads from main.bin every
address, word and offset the hooks rely on and checks the NRO for the sites and
exports. Report research/P10-UI-SLICE.md: the design in one page, every hook with its
proof, what happens in normal mode, the E3 argument step by step, a console test plan
of at most 10 user steps for two saved Gunners (A = 0000f589, B = 0000f58b) covering
both entries, decide, cancel, row 0, a match after choosing without reboot, a reboot
check of the saved file, and the normal hat and outfit screens; the log lines that
prove each; failure patterns and the rollback (0.3.0 NRO `55a786b6...`); and a plain
list of everything that is tier D.

Not in scope: Lua, layout or message files; integer parameters; other Mii classes;
a new menu row; install scripts.

Exclusive writes: plugin/, build-plugin.sh, builds/0.4.0-ui/, builds/.cache/,
research/P10-UI-SLICE.md, evidence/P10-UI-SLICE/, scratch/2026-10-05_P10-UI-SLICE/.
