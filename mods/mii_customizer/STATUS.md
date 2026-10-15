# Mii Customizer - current state

Updated: 2026-10-07. Coordinator: current user chat; workers launched manually by the user.

## Authorized scope

Separate SSBU 13.0.4 mod: Mii Gunner editor for all agreed move slots and stats, saved per fighter.
Gunner-only choices initially; other Mii classes' moves later. No roguelike or PC port.
Three concurrent Space Bunny Alpha workers maximum. Premium model use is selective.

## Current phase: 4 - vertical slice (per-Mii stat override first, editor UI second)

| Task | Worker | Status | Output |
|---|---|---|---|
| P1-UI | Space Bunny Alpha | DONE; preliminary strings/layout inventory reviewed | `research/P1-UI.md` |
| P1-ID | Space Bunny Alpha | FINISHED PARTIAL; corrected after premium audit | `research/P1-ID.md` |
| P1-CATALOG | Space Bunny Alpha | DONE; inventory reviewed, interpretation gaps flagged | `research/P1-CATALOG.md` |
| P1-UI-DECODE | Space Bunny Alpha | DONE; parser checks rerun by coordinator, two boundaries unresolved | `research/P1-UI-DECODE.md` |
| P1-CATALOG-AUDIT | Space Bunny Alpha | DONE; claim checks rerun by coordinator | `research/P1-CATALOG-AUDIT.md` |
| P1-UI-GLOBALS | Space Bunny Alpha | FINISHED PARTIAL; no target definitions in three modules | `research/P1-UI-GLOBALS.md` |
| P1-LAYOUT | Space Bunny Alpha | DONE; unchanged controls rerun, report corrected | `research/P1-LAYOUT.md` |
| P1-LUA-WRITE | Space Bunny Alpha | DONE; encoder checks rerun, all pass | `research/P1-LUA-WRITE.md` |
| P1-ID-REVIEW | Claude Opus 5.5 | FINISHED PARTIAL; reviewed, battle reader unresolved | `research/P1-ID-REVIEW.md` |
| P1-DATASET | Space Bunny Alpha | DONE; 42 catalogue checks rerun, all pass | `research/P1-DATASET.md` |
| P2-LAYOUT-STRUCTURE | Space Bunny Alpha | DONE; 71/71 checks rerun, report corrected | `research/P2-LAYOUT-STRUCTURE.md` |
| P2-SARC-WRITE | Space Bunny Alpha | DONE; 87/87 checks rerun | `research/P2-SARC-WRITE.md` |
| P2-UI-FLOW | Space Bunny Alpha | DONE; reviewed, two index errors corrected in place, native semantics unresolved | `research/P2-UI-FLOW.md` |
| P2-LAYOUT-PATCH | Space Bunny Alpha | DONE; 80/80 checks rerun, two-byte diff reproduced, install step corrected | `research/P2-LAYOUT-PATCH.md` |
| P2-STAT-API | Space Bunny Alpha | DONE; 59/59 source checks rerun; per-instance scoping unresolved | `research/P2-STAT-API.md` |
| P2-SKILL-NATIVE | Space Bunny Alpha | DONE; 174/174 rerun, get/set handlers re-read by coordinator | `research/P2-SKILL-NATIVE.md` |
| P2-LUA-EDIT | Space Bunny Alpha | DONE; 217 checks rerun; misplaced evidence/scratch moved into the mod | `research/P2-LUA-EDIT.md` |
| P2-SKILL-STORE | Claude Opus 5.5 | DONE; 88/88 rerun, copy and commit-gate instructions re-read by coordinator | `research/P2-SKILL-STORE.md` |
| P2-UI-CONSTS | Space Bunny Alpha | DONE; 179/179 rerun | `research/P2-UI-CONSTS.md` |
| P2-STAT-READS | Space Bunny Alpha | DONE; 450/450 rerun, one read site re-read by coordinator | `research/P2-STAT-READS.md` |
| P2-MATCH-READER | Claude Opus 5.5 | FINISHED PARTIAL; 95/95 rerun, ID store re-read by coordinator; match-time reader untraced | `research/P2-MATCH-READER.md` |
| P2-STAT-HOOKPOINT | Space Bunny Alpha | FINISHED PARTIAL; slot functions re-read by coordinator, worker's conclusion revised in review | `research/P2-STAT-HOOKPOINT.md` |
| P2-PLUGIN-SCAFFOLD | Space Bunny Alpha | DONE; 26/26 rerun, NRO hash matches manifest; build not repeated by coordinator | `research/P2-PLUGIN-SCAFFOLD.md` |
| P3-DIAG-PLUGIN | Claude Opus 5.5 | DONE; 36/36 and 37/37 rerun, source read by coordinator; never run in game | `research/P3-DIAG-PLUGIN.md` |
| P3-ARC-PROBES | Space Bunny Alpha | DONE; check rerun; invalid `info.toml` fixed by coordinator | `research/P3-ARC-PROBES.md` |
| P3-CUSTOMIZE-SITES | Space Bunny Alpha | DONE; 55 claims rerun; found only the script-binding caller | `research/P3-CUSTOMIZE-SITES.md` |
| P3-SPECIAL-VARIANTS | Space Bunny Alpha | DONE; 89/89 rerun; file inventory of the twelve variants | `research/P3-SPECIAL-VARIANTS.md` |
| GATE-1 | user (console) | DONE 2026-10-04; all four questions answered (tier A) | `evidence/2026-10-04_gate1/RESULT.md`, `RESULT_test2.md` |
| P4-OVERRIDE-SLICE | Claude Opus 5.5 | DONE; 35/35, 69/69, 25/25 rerun; READY FOR INSTALL, never run | `research/P4-OVERRIDE-SLICE.md` |
| P4-LUAC | Space Bunny Alpha | DONE; 9 checks rerun; compiler reads all three game chunks | `research/P4-LUAC.md` |
| P4-BRIDGE-FACTS | Space Bunny Alpha | DONE; check rerun | `research/P4-BRIDGE-FACTS.md` |
| P4-STAT-SITES | Space Bunny Alpha | DONE; tables accepted, check not rerun by coordinator | `research/P4-STAT-SITES.md` |
| GATE-2 | user (console) | DONE 2026-10-05; per-saved-Mii weight / walk speed override works (tier A) | `evidence/2026-10-05_gate2/RESULT.md` |
| P6-HAT-UI | Space Bunny Alpha | DONE; check rerun 722/722 | `research/P6-HAT-UI.md` |
| P6-EDIT-MENU | Space Bunny Alpha | DONE; check rerun 264/264 | `research/P6-EDIT-MENU.md` |
| P6-PRESET-DATA | Space Bunny Alpha | DONE (run twice by mistake; second worker verified independently); check rerun 30/30 | `research/P6-PRESET-DATA.md`, `evidence/P6-PRESET-DATA/W2-REVIEW.md` |
| P5-LUA-SOURCE | Space Bunny Alpha | FINISHED PARTIAL; all 17 prototypes identical, one header byte (`is_vararg` of main) differs | `research/P5-LUA-SOURCE.md` |
| P5-UI-API | Space Bunny Alpha | DONE; inventory of 86 UI scripts accepted (check not rerun by coordinator) | `research/P5-UI-API.md` |
| P5-MSG-PROBE | Space Bunny Alpha | DONE; message-patch probe staged in `builds/0.2.1-msg-probe/`, not installed | `research/P5-MSG-PROBE.md` |
| P7-PRESET-ENGINE | Claude Opus 5.5 | DONE; coordinator reran host 47/47, mutation 61/61, build check 98/98, preset file 8/8, build hash reproduced | `research/P7-PRESET-ENGINE.md` |
| P8-LUA-LIST | Space Bunny Alpha | DONE; check rerun 1667/0 | `research/P8-LUA-LIST.md` |
| P8-EDIT-DISPATCH | Space Bunny Alpha | STOPPED WITHOUT A REPORT; its check script has two known defects and is superseded by P9-EDIT-DISPATCH; coordinator note added | `evidence/P8-EDIT-DISPATCH/COORDINATOR-NOTE.md` |
| P8-HAT-NATIVE | Space Bunny Alpha | DONE; check rerun 221/0; corrected in place (which ctor is headgear) | `research/P8-HAT-NATIVE.md` |
| P9-EDIT-DISPATCH | Space Bunny Alpha | DONE; coordinator reran 774/0 and 6 controls (exit 1); exit value 7 chosen, >=9 traps; two coordinator corrections in the report | `research/P9-EDIT-DISPATCH.md` |
| P9-HAT-HANDLES | Space Bunny Alpha | DONE; coordinator reran 396/0 and 10 controls (exit 1); corrections propagated to P8-HAT-NATIVE | `research/P9-HAT-HANDLES.md` |
| P9-EDIT-SOURCE | Space Bunny Alpha | DONE; edit chunk byte-identical (18 prototypes); probe `builds/0.3.1-edit-probe/` verified against its manifest | `research/P9-EDIT-SOURCE.md` |
| SESSION-1 boot 1 | user (console) | RAN 2026-10-05 (partial): per-Mii stat presets work (tier A); different-length `.lc` loads; added message label did not resolve; edit probe showed no change | `evidence/2026-10-05_session1/RESULT.md`, `log_boot1.txt` |
| SESSION-1 boot 2 | user (console) | RAN 2026-10-05: explicit line beats preset, second preset, two Miis with different presets, stale ID slot harmless for a non-Mii (tier A); no ARCropolis log at `Debug` | `evidence/2026-10-05_session1/RESULT_boot2.md`, `log_boot2.txt` |
| P10-UI-SLICE | Claude Opus 5.5 | PARTIAL: stopped without report, tests or manifest; source complete and builds reproducibly (`d28aea75...`); coordinator review: site words 52/0, 0.3.0 host tests 47/0 on the new sources | `research/P10-UI-SLICE.md` (coordinator-written), `builds/0.4.0-ui/` |
| P10-EDIT-ENTRY | Space Bunny Alpha | DONE; coordinator reran `check_entry.py` (exit 0) and `build_check.py` (both chunks byte-identical); two variants staged | `research/P10-EDIT-ENTRY.md`, `builds/0.4.0-edit-entry/` |
| P10-PRESET-WIDE | Space Bunny Alpha | DONE; coordinator reran the check 29/0; 41 fields, 94 presets, `list.txt` 87 rows | `research/P10-PRESET-WIDE.md` |
| P10-HAT-OPEN | Space Bunny Alpha | DONE; coordinator rerun 472/0 after removing one impossible claim; three statements corrected in place | `research/P10-HAT-OPEN.md` |
| SESSION-2 | user (console) | RAN 2026-10-06: character list in the Mii maker works (tier A): way in A, 88 rows, decide/cancel, runtime save, Mii unchanged | `evidence/2026-10-06_session2/RESULT.md` |
| SESSION-3 | user (console) | RAN 2026-10-07: 0.5.0 installed no hook (foreign hook on a probed entry); coordinator fix 0.5.1 works (tier A): menu pages, greyed rows, literal text, save, reboot | `evidence/2026-10-07_session3/RESULT_boot1.md`, `RESULT_boot2.md` |
| P11-MENU | Claude Opus 5.5 | DONE (offline); coordinator reran check 358/0 + 11 controls, host tests 47/0 + 35/0, NRO hash; `editor.rs` and four code windows read; never run in game | `research/P11-MENU.md`, `builds/0.5.0-menu/` |
| P11-ROW-TEXT | Space Bunny Alpha | DONE; coordinator reran check 340/0 and `--neg` (exit 1); agrees with P11-MENU's text and greyed-row reading | `research/P11-ROW-TEXT.md` |
| P11-INT-PARAMS | Space Bunny Alpha | STOPPED WITHOUT A REPORT; unreviewed tables left under workspace `gamedata/mii_customizer/P11-INT-PARAMS/`; continued by P12-INT-PARAMS | `research/P11-INT-PARAMS.md` (skeleton + coordinator note) |
| P11-MOVE-PLAN | Space Bunny Alpha | DONE; check rerun 4/4, but it covers only file hashes, jab motion entries and skeleton/track counts; the rest is marked unverified in a coordinator banner | `research/P11-MOVE-PLAN.md` |
| P13-MINUS-ENTRY | GPT 6 Luna | FINISHED PARTIAL; no button mapping, no chunk; two statements corrected in a coordinator banner; superseded by the coordinator's plugin route in 0.6.0 | `research/P13-MINUS-ENTRY.md` |
| P13-KEYHELP | GPT 6 Luna | DONE; check rerun exit 0; tip replaces the Favourite tip (Minus glyph label + literal text); block reused in 0.6.0 | `research/P13-KEYHELP.md`, `builds/0.6.0-edit-keyhelp/` |
| P14-LIST-PLAYABLE | GPT 6 Luna | FINISHED PARTIAL; PARKED by the user, not reviewed, nothing shipped (the user wants a per-character, per-move feasibility pass later instead) | `research/P14-LIST-PLAYABLE.md` |
| P14-SORT-OPTIONS | worker (model not stated in the report) | DONE; coordinator reran check 389/0 and host tests 47/0 + 35/0 + 16/0, read the sort code; banner with corrections; 0.7.0 READY, never run | `research/P14-SORT-OPTIONS.md`, `builds/0.7.0-menu/` |
| P14-SWORD-FACTS | Freebuff worker | DONE per its report (13:00); NOT YET REVIEWED by the coordinator; what showing the Swordfighter's sword and trails on a Gunner during sword moves needs | `prompts/P14-SWORD-FACTS.md` |
| P12-INT-PARAMS | Space Bunny Alpha | DONE; check rerun 558/0; integer getter is the thunk `0x4e53a0`; six qualifying integer fields | `research/P11-INT-PARAMS.md` |
| P16-FTILT-MOVE | Claude Opus 5.5 / GPT 6.1 Sol / Antigravity (as named in the report) | DONE (offline); coordinator reran check_p16 (exit 0), host tests 47+35+4+16+6, reproduced the worker NRO `2890bc58...`, checked the three motion-list entries, the ARC costume group and the Smashline imports, read `moves.rs`; coordinator edits: airborne check, boot-crash fix, missing-motion fallback; package ships a motdiff; NRO now `0193ba5f...`; INSTALLED 2026-10-07 evening, not yet run |
| P17-SMASH-UP | Space Bunny Alpha | DONE (offline); coordinator reran host tests 47+35, stack frames OK (18672 bytes), motdiff roundtrip verified (781 entries); never run | `research/moves/smash_up__fox.md`, `moves/smash_up__fox/`, `builds/0.10.0-menu/` |
| SESSION-4 boot 1 | user (console) | RAN 2026-10-07: 0.8.0 `cdb4f7e0...` crashed at startup (tier A): 324 KiB stack frame in `main` on a 64 KiB stack (menu and loadout tables by value; 0.7.0 had the same defect); fixed and reinstalled | `evidence/2026-10-07_session4/RESULT_boot1.md` |
| SESSION-4 boot 2 | user (console) | RAN 2026-10-07: 0.8.0 boots; menu, Sword page, slot storage (loadouts v3), per-Mii resolution and the status wrapper on `miigunner` work (tier A); the kick froze in the bind pose because `pyra_gamewatch_reskin` owns the Gunner `motion_list.bin`; package switched to `motion_list.motdiff`, plugin falls back to vanilla when the motion is missing; reinstalled | `evidence/2026-10-07_session4/RESULT_boot2.md` |
| SESSION-4 boot 3 | user (console) | RAN 2026-10-07: **0.8.0 works** (tier A): Mii Brawler forward tilt on one Gunner, another Gunner unchanged in the same match; motdiff on top of the other mod's list; sort by name used | `evidence/2026-10-07_session4/RESULT_boot3.md` | `research/P16-FTILT-MOVE.md`, `builds/0.8.0-moves/` |
| P15-FTILT-TAKEOVER | Antigravity (as named in the report) | DONE; check rerun exit 0; coordinator banner | `research/P12-FTILT-FACTS.md` |
| P12-FTILT-FACTS | Space Bunny Alpha | NO REPORT after three hours (tables and scripts only); handed to P15-FTILT-TAKEOVER; measured contents and dependencies of Mii Brawler's forward tilt | `prompts/P12-FTILT-FACTS.md` |
| P12-SCRIPT-ROUTE | Space Bunny Alpha | DONE; check rerun 17/17; accepted as the fact base for the first-move design | `research/P12-SCRIPT-ROUTE.md` |
The user starts Freebuff workers manually; no autonomous dispatch is active. Identity-dependent
implementation and shared architecture still wait for accepted identity/runtime evidence.

## Evidence and unresolved questions

Verified: offline parsing, catalogue, encoder and archive checks; no runtime game behavior measured in this project.
Coordinator verified three representative extracted hashes against worker reports: special editor
script, Gunner body motion list and common fighter parameter table. Review:
`research/COORDINATOR-2026-10-04.md`. Follow-ups now parse all three Lua chunks and show
dispatcher call sites; forward-tilt naming and packed timing fields have supporting offline
evidence. Coordinator reran lua53-inspect checks (all pass, exit 0) and catalogue claim audit
(0 failing claims, exit 0). These checks do not establish UI modifications or runtime behavior.
Unresolved UI boundaries: source of injected globals/counts, native dispatcher implementation,
layout mutation/loading, Lua instruction authoring, and save linkage. The reproducible P1-DATASET catalogue
supersedes preliminary prose grouping: 23 provisional slots and 12 stat candidates;
no input routing, dependency closure or stat ranges established.
Unverified: native editor extension route, stable saved-Mii identity and loadout propagation,
per-instance stat application, preview behavior, resource capacity and simultaneous custom Miis.
Prior mod research is reference material only; no compatibility claim or copied implementation.
P1-ID-REVIEW supports a u32 saved-record ID and a selection-ID-to-per-player-table path
(offline B, reviewed but native analysis not independently reproduced by coordinator). The match
reader is untraced. Earlier post_fighter battle-handoff and u16 move-list claims were wrong;
P1-ID was corrected in place and its annotated trace is superseded. Coordinator independently
verified the modular inverse arithmetic only. Rename/copy/delete/reboot identity behavior remains
unverified; no identity-dependent behavior implementation is accepted yet.
P1-UI-GLOBALS excludes only three modules as definitions; global immutability/native origin
is not established. Stop broad Lua searches and prepare an offline chunk write path instead.

## Phase sequence (provisional; gates are mandatory)

1. Locate UI inputs, identity candidates and Gunner slot/stat inputs; review evidence and choose
   minimal next experiment. Escalate narrowly if native RE needs a premium model.
2. Implement a vertical slice: native editor entry, one selector/stat, mod-owned persistence and
   loadout retrieval. Shared identity/schema contract agreed before parallel implementation.
3. First useful hardware gate: reach editor, save/reload, correct preview/match application and
   two Gunners with different settings. Instrument only what this gate needs.
4. Complete agreed Gunner slot/stat editor, validation, defaults and lifecycle handling.
5. Add Brawler/Swordfighter moves incrementally with dependency and conflict checks.

Special-selector Lua semantics after coordinator review of P2-UI-FLOW (offline B, read from
`evidence/P2-UI-FLOW/dis_special_actor.txt`): the screen keeps one table `cache[row + 1]`
holding a 0-based option index per special slot. It is filled from `get_skill_id(row)` on
entry, overwritten by `cache[command_id + 1] = decided option` in the sub-window, previewed
through `replace_skill(row, option)` on every help-text update, and written back with
`set_skill_id(row, cache[row + 1])` for every row once the screen's state loop ends, with no
cancel branch around that write. What the native handlers do with these values is unverified.
The registration pattern for such bridge names is known from P1-ID-REVIEW 2.3 (delegate +
handler pointer), which makes locating the six skill handlers a bounded offline task.

Native side of the special selector (offline B; coordinator disassembled 0x19dcf20/0x19dcf40
and read the constructor lines): `set_skill_id`/`get_skill_id` only bounds-check row < 4 and
write/read one byte at `obj + 0x100 + row`, where `obj` is a 0x150-byte scene object built in
0x19ddb30 and zeroed there. So a saved Gunner's special choices pass through four bytes in
that object. Who fills them from the saved record and who copies them back is not traced; no
range check on the option value exists in these two handlers. `replace_skill` (0x19dd1a0)
references a `set_rep_special` pane and is not shown to change a fighter (D).
Stats: `weight` and `walk_speed_max` are per-kind rows in the common table; a per-object
accessor hook shape exists in the old mod (C), but whether the engine reads these two values
through it, how often, and how two Gunners would be told apart are unresolved.
lua53-inspect can now append constants and patch/insert instructions with jump relocation
(encoding verified offline only).

Saved special choices (offline B): the four option bytes are saved-record `+0x142..+0x145`,
loaded into a static editor working record at 0x5306b78, copied to the screen object on entry
and back on exit (0x180ba20). Values are 0..2; `SPECIAL_SKILL_NUM` = 3 and `SKILL_COMMAND_NUM`
= 4 are immediates in 0x19ddb30. The editor commit 0x180d200 skips the store when any of the
four bytes is above 2, so extra options cannot simply be stored in the vanilla field.
`IS_READ_ONLY` / `IS_SKILL_EDITABLE` are computed from bytes at working record `+0x14` and
`+0x24` (0x5306b8c, 0x5306b9c). Supersedes the "u32 at +0x140, u16 at +0x144" reading.
Stats (offline B): 37 code sites build the `weight` hash and 18 the `walk_speed_max` hash; 21
of the listed ones call through vtable slot 0x270 of the object at `[accessor+0x50]` with the
hash in x1. That is a per-object indirect call at each use site. Which function sits in that
slot, and whether the old mod's hook catches these engine calls, is not established.
Design consequence (coordinator, D): custom loadouts need mod-owned storage keyed by the saved
fighter's u32 ID, and the open runtime-side question is how to get that ID per player at match
start.

Per-player saved ID (offline B): the function that stores a saved Mii's record content per
player also stores its u32 ID in an adjacent static table, `T + 0xe58 + p*0x240` with
T = 0x5307760; special bytes sit at `T + 0xa2 + p*0x1c8`. Several scenes write these slots.
Not shown: that `p` is the match player, or that the slots are current when a match starts.
Float-param hook point (offline B for the instructions, D for the naming): slot +0x270 of
vtable 0x4f89490 is the 4-instruction thunk 0x4e53e0, which forwards x1/x2 unchanged to
another object's slot +0x30; that vtable's object is stored at `[parent+0x50]`, the shape
the engine's weight/walk-speed call sites use. Slot +0x268 (used by the exported script
wrapper the old mod hooks) re-dispatches +0x270, so a hook at 0x4e53e0 would see both paths.
Build: the mod has its own plugin crate (`plugin/`, `build-plugin.sh`) producing a 36864-byte
log-only NRO, `builds/0.0.1-scaffold/`; never loaded by the game.

Gunner special variants (offline B): 70 motion entries in one contiguous run cover the twelve
variants; each slot has a 4-row param list in `vl.prc` where row i carries variant i+1's values.
No variant index is stored in motion entries. What code selects the row is not established.
The engine-side caller of the special-variant setter was not found by shape scan: the only
`[x+0x50]` slot-0x278 call sites are the exported wrapper and one script-binding function.

Console results, gate 1 test 1 (tier A, `evidence/2026-10-04_gate1/RESULT.md`): image file
offsets are the console's Text offsets; 0x4e53e0 is called per fighter object for weight and
walk_speed_max, repeatedly during a match, from engine and from another module; the saved-Mii ID
and special bytes of local players 0 and 1 are in the static slots when the fighters are created
(Gunner A = 0xf589 in slot 0, Gunner B = 0xf58b in slot 1). Open: parent object -> player index,
CPU / more players / other modes, stale slots for non-Mii players after a Mii match.

Console results, gate 1 test 2 (tier A, `evidence/2026-10-04_gate1/RESULT_test2.md`): the game
loads an edited editor Lua chunk and an edited editor layout archive from ARCropolis mod folders
(same-length edits; different-length files untested).

Plan for the vertical slice (coordinator, D where it predicts): (1) plugin 0.2.0 applies weight /
walk speed per saved Mii from `sd:/ultimate/mii_customizer/loadouts.txt` (format v1 defined in
`prompts/P4-OVERRIDE-SLICE.md`), keyed by the slot ID; console test with one overridden Gunner
and one vanilla Gunner. (2) Editor UI: write Lua as source with a matching local compiler
(P4-LUAC) and talk to the plugin through the existing skill get/set handlers (facts gathered by
P4-BRIDGE-FACTS); design follows after those return. (3) Stat list from P4-STAT-SITES.

On the card now: plugin 0.1.0-diag and both file probes (cosmetic: smaller first row, wrong
sub-title on the Mii special-move screen). They are removed/replaced with the next install.

Phase 4 offline results (B): all 11 float stat candidates have call sites through slot +0x270
(the hooked getter); `jump_count_max` is an integer and goes through +0x250. Lua integers reach
the skill handlers unmodified in w1/w2 and a handler return in w0 comes back to Lua as a signed
integer; the two handlers are 5-instruction functions with one PC-relative word, reached only
through their delegates; the editor working record (first u32 = saved ID) is static at 0x5306b78;
the live screen object is not stored in any static by its constructor. A local Lua 5.3.6 compiler
(`tools/luac53-game/`) produces the header format of the game and lists all three game chunks;
whether the game accepts a chunk compiled by it is untested.

UI direction (coordinator, D): reuse the Mii special-move screen with extra pages (for example
shoulder buttons switch from the four special rows to four stat rows, each with three options),
written as Lua source, texts from added message labels, values exchanged with the plugin through
`get_skill_id` / `set_skill_id` with row numbers the game never uses, the edited Mii identified by
the static working record. Nothing of this is designed in detail until P5 returns.

Console results, gate 2 (tier A, `evidence/2026-10-05_gate2/RESULT.md`): with plugin
0.2.0 Gunner A (ID 0000f589) had weight 130 and walk speed 1.6 on either port while Gunner B
stayed vanilla; the user confirmed the difference in play. Fighter kind 74, entry id = slot
index, vtable 0x4f89490 confirmed for two local players. The engine applies special choices by
calling slot +0x278 with (w1 = option 0..2, w2 = slot 0..3) from around 0x60e9d0..0x60ea24.
Not exercised: non-Mii fighters with 0.2.0, stale slots, CPU players, more than two players.

User direction, 2026-10-05 (chat): next, let the player choose between different characters'
stat loadouts in the Mii maker. Lists will be long, so build on the headgear selection screen
rather than the 3-option special screen. Minimum acceptable entry point: one button in the Mii
maker that switches to the modded settings (training-modpack style, but better); preferred:
proper integration into the main Mii maker menu with real sub-menus.

Coordinator plan (D): presets are generated from the user's own fighter_param.prc into a file on
the card (format `mc_presets 1`, defined in `prompts/P6-PRESET-DATA.md`); the loadout file gains
a preset reference per saved Mii; the UI is a list screen modelled on the headgear screen, opened
from a new edit-menu entry, talking to the plugin through an existing bridge call. P6-HAT-UI and
P6-EDIT-MENU establish what that needs; the plugin work (premium) follows once they and
P6-PRESET-DATA return. This supersedes the earlier "extra pages on the special-move screen" idea.

On the card: plugin 0.2.0-override and the example loadout file. No probes.

P5 results (offline B unless marked): a reconstructed Lua source of the special-move script
compiles with the local compiler to the original bytes in all 17 prototypes; the only differing
byte is the main function's `is_vararg` flag (original 2, stock 5.3.6 writes 1), which can be set
after compiling. Pane text in the game's scripts is set through message keys
(`set_text_message`, 81 call sites); 28 `INPUT_*` constants and their values are known. The file
loader's pinned source (C) supports message patch files that ADD labels
(`ui/message/msg_menu.xmsbt`); a probe with one new label and a different-length Lua chunk is
staged. The loader version on the card is not established; the kb note naming v4.1.1 is doubtful
(that version requires game 13.0.5).

P6 results (offline B; native behaviour D): the headgear list is a host-made object
(`scroller` global). The script never fills it: no item count, no row text, no icon call; it
only moves the cursor, asks for a re-sort and reads the decided item. Headgear and outfit are
two thin actor scripts sharing one layout module. The edit menu builds six rows
`set_item_00..05` by a loop (limit constant 5), the layout has no spare row part, and the
script only publishes the decided row through `exit_value`; which sub-screen opens for which
row is decided in native code. So neither "reuse the headgear list" nor "add a menu entry" is
a script-only change. Preset data: 94 table rows, 369 fields each; `presets.txt` (ten fields
per fighter, 25 517 bytes) is generated under workspace `gamedata/` and fits contract A of
P7 (512 KiB). Its values also parse bit-exactly under a model of the plugin's number parser.
Display names: `nam_chr1_00_<name>` exists for 87 of 94 kinds and has no line breaks;
coordinator decision: the UI list uses that family (regenerate `fighters.json` when the UI
task needs it) and leaves out `miienemy*`; the other exceptions are decided with the UI.

P8 results (offline B; runtime D). No UI script constructs a scrolling list; the two chunks
that write `scroller` only clear it. The one screen where Lua owns text rows is the
special-move screen (fixed row parts from its layout, text by message key). The native
headgear list: object built by `0x19ceb30` (headgear, scene+0x180) / `0x19c7830` (outfit,
scene+0x188); items are a vector of 8-byte handles at `S+0x128`, `S = *[list object +0x80]`
(the count is its length); a row is filled by `0x19ccb20` (row index in w1), which builds the
message key `nam_mii_hat_<name>` through `0x3288330` and sets it on pane `set_txt_val`;
`sort_id_list` ignores modes other than 0..2 (headgear handler `0x19cd100`; the `0x19c1f50`
set is the outfit's). The edit scene (from the unfinished P8-EDIT-DISPATCH evidence, re-read by
the coordinator): `0x180a030` reads the script exit value at `[[scene+0x178]+0x80]+0x128` and
pushes state `value + 4` on a state stack (scene+0xf8, index +0x144); `0x180ce40` runs one of at
most 13 state handlers from a table at scene+0x28; each sub-screen object is built once in the
scene constructor and loads its script by path hash (`0x32caa90`).
Working direction (D, coordinator): no new native state and no new row at first. Entry by a
button press in the edit menu script that leaves with a new exit value; a plugin hook in
`0x180a030` turns that into "open the headgear screen in mod mode"; in mod mode the plugin
supplies the item count and row text of the native list (fighter names through the game's own
`nam_chr1_00_<name>` labels) and takes the decided row as the preset choice. Whether that is
safe depends on what else uses the item handles (icon, model preview, commit): P9-HAT-HANDLES.

P7/P9 results (offline B unless marked; coordinator reruns 2026-10-05). P7 delivered plugin
0.3.0-presets: NRO `55a786b6...` (hash reproduced by a coordinator rebuild), preset file
parser, loadout v2 with `preset` lines, explicit-beats-preset resolution, bounded logging,
`save_loadouts()` compiled in but called by nothing. The coordinator accepted the report's
contract readings (section 1 tables) and its bounded logging changes; the `loadouts.new`
reader rule is deferred to before the first UI save; risk to watch on the next boot: the three
new `nn::fs` imports. P9-EDIT-DISPATCH: exit values 0..8 all reach existing states (value 7 ->
state 11, benign without the plugin; value 8 -> editor teardown), >= 9 reaches the trap
`0x180cf00` (`bl 0x39c20a0; udf`) -- **decided: the mod script publishes 7 and the plugin
rewrites it to 1** before the dispatcher read. P9-HAT-HANDLES: no handle consumer traps; an
unknown handle yields the label `nam_mii_hat_unknown`; the decided row reaches `+0x148` and the
static `0x5306cb0`; cancel/restore and the commit into the save remain open. P9-EDIT-SOURCE:
the edit-menu chunk is reconstructed byte-identically (18 prototypes) and a different-length
probe is staged; nothing was run.

Session 1 result, boot 2 (tier A, `evidence/2026-10-05_session1/RESULT_boot2.md`): explicit
lines beat the preset per field; a second preset and two Miis with different presets in one
match work; a stale saved-Mii ID in a non-Mii player's slot causes no override; the editor
preview fighter has ID 0 and keeps the game's stats. ARCropolis wrote no log file at `Debug`
(level restored to `Warn`). Offline the same day: `nam_mii_hat_*` and `nam_chr1_00_*` are both
in `msg_name.msbt`, so the character list needs no added label; the 0.3.1 Favorite probe could
not work by design (it asked the frame, not `selector0`, to decide), so "does a replaced edit
chunk load" is still open and no longer blocks the milestone (plugin-only entry B).

Decision 2026-10-05 (coordinator, at the user's request to move faster): no further probe-only
boot. The loader questions ride along with the first real UI build. Contracts added in
`prompts/P10-UI-SLICE.md`: E (what the user sees; hard invariant: mod mode never changes the
Mii), F (`list.txt`, `mc_list 1`), B+ (`loadouts.new` is read when `loadouts.txt` is missing).
The message-label question is parked: nothing in the milestone needs an added label.

P10 round, reviewed 2026-10-06. The three Alpha tasks delivered; the premium plugin task
stopped after writing and building the code. Facts that changed: `0x328b5d0` answers 1 for a
handle that is NOT in the table (P9 had it inverted; corrected in place); the headgear
handle of the working record has two writers, both in state 5, and cancel restores it
through `S+0x148`, which only a non-negative `get_decided_id` overwrites; the save path
`0x17c0a50` writes nothing for an unknown hash; the scroller has a count setter
(`0x37830e0`) that the Mii code never calls; the list's frame callback is driven by a global
pump (`0x32ca620`) gated by `list+0x70`. The edit and special chunks have the same arc index
properties, so nothing offline predicts that the edit chunk will not load. Presets can carry
41 evidenced float fields. Session `0.4.0-ui` is READY in `CURRENT_INSTALL.md`.

Console result, session 2 (tier A, `evidence/2026-10-06_session2/RESULT.md`): the replaced
edit-menu chunk loads and exit value 7 arms mod mode; the native headgear list shows 88
plugin rows on a list built for 52; decide and cancel are told apart; the choice is applied
without reboot and `save_loadouts()` works; the Mii's headgear and working record were equal
on every exit. Not exercised: way in B, row 0, the sort button, a reboot.

User direction 2026-10-06: mod mode should open a menu of things to customize (Stats, Jab,
Forward Tilt, ...); each opens a character list; characters whose move is not implemented
are greyed out; for now only the Mii Gunner default is available and selected. Contracts M
(pages) and G (`menu.txt`, `mc_menu 1`) are in `prompts/P11-MENU.md`.

P11 round, reviewed 2026-10-07 (offline B unless marked; nothing of 0.5.0 has run). Plugin
0.5.0 (`565014ab...`) implements contract M completely: a main page from `menu.txt` and one
character page per entry, all on the native headgear list. A page change undoes state 5's own
pop of the state stack and sets the reader's restart byte `scene+0x154`, which the game
itself never sets in this scene (the depth is only ever written back to the value it had when
the first page opened). A greyed row is the game's own disabled button (`+0x1c2 = 0`), reached
by answering "unlisted" only while the row filler asks; the scroller's decide code ignores a
disabled button, and the plugin refuses such a row as well. Literal text goes through the
row filler's pane lookup `0x3776360` and Lua `set_text_string`'s callee `0x37a22f0`, set
after every fill; P11-ROW-TEXT confirms independently that rows are refilled on scroll and
redraw, that the label lookup searches all 13 message files by label text, and that only
Stats, Grab and the four specials have an exact existing label (used as fallbacks in the
session's `menu.txt`). New switch file `text_off`. Session `0.5.0-menu` is INSTALLED (2026-10-07), untested, in
`CURRENT_INSTALL.md`: 24 menu entries with the catalogue slot ids, `list.txt` without the Mii
Gunner row (86 rows), the plain edit script (Try button back).
P11-MOVE-PLAN (B only for the part its check covers): the three Mii classes share one 71-bone
skeleton and animation node set; Brawler's jab is two stages plus a rapid jab where Gunner's
has three stages. Coordinator decision (D): investigate Mii Brawler's **forward tilt** as the
first borrowed move; P12-FTILT-FACTS and P12-SCRIPT-ROUTE collect what a design needs.
Integer parameters: no reviewed result yet (P12-INT-PARAMS).

Session 3 boot 1 (tier A, `evidence/2026-10-07_session3/RESULT_boot1.md`): 0.5.0 installed no
UI hook because the entry of `0x37a22f0` carries another plugin's inline hook (probe 47/48);
exit value 7 without the hook returned to the edit menu harmlessly; the plain edit script
loads. Coordinator fix 0.5.1 (`9cdcbd67...`, accepts that hook stub at that one called-only
entry; host tests 47/0 + 35/0; worker check script not adapted) is installed, untested. Open:
which plugin owns that hook.

Session 3 boot 2 (tier A, `evidence/2026-10-07_session3/RESULT_boot2.md`): **0.5.1 works.**
Main page (24 rows on the 52-row native list), literal row text (`text_missed=0`, through the
foreign hook), 24 page changes at constant stack depth, slot pages with one available row
and greyed rows, stats set / clear with the tick following, four saves, the Mii unchanged on
every exit, Kirby's stats in a match, and the plugin-written `loadouts.txt` read back after
a reboot. Not exercised: way in B, `text_off`, `ui_off`. The row filler runs much more often
than once per scroll step (about 1600 greyed fills on one page). Jump count is not part of a
preset (integer parameter; P12-INT-PARAMS).

0.5.2 (coordinator; ran 2026-10-07, user: the row text looked good, tier A): main-page rows show "<entry>: <current choice>"
from an optional `names.txt` (`mc_names 1`, preset name + literal character name, generated
from the user's `msg_name.msbt`); new module `plugin/src/names.rs`; the value is read once
per page open. D: whether the longer text fits the row.

0.6.0 (coordinator; installed and run 2026-10-07, user: "works", tier A by report, log not
yet copied): Minus on the edit menu. The script cannot be shown
to see Minus (P13-MINUS-ENTRY, partial), so the plugin reads nn::hid in the dispatcher hook
and raises the edit script's global `MC_MINUS` through `0x33750a0` on `[[inner+0x40]]`
(scene builder `0x1808fe0..0x1809018`); the script leaves with exit value 7 by its own exit
path. Tip from P13-KEYHELP. Favourite-on-Headgear entry removed. New switch file `minus_off`.
D: first real hid read by this plugin; the global reaching the script; the tip's look.

Round reviewed 2026-10-07 (midday). 0.6.0 confirmed by its log (Minus entry, tier A).
0.7.0 (P14-SORT-OPTIONS) is READY: sort by name on character pages by permuting the handle
vector (handles keep naming fighter-order rows), a third entry kind `option` with its own
rows (session `menu.txt`: Sword, one option), loadouts version 3 written only when an option
line exists. Integer parameters: getter thunk `0x4e53a0` known, `jump_count_max` is the
field that matters and needs a console answer about missing jump motions. Script route:
Smashline (the user's 13.0.4 build on the card) can register scripts for `miigunner` and a
script can reach the entry id; nothing Mii-specific was found; all of it D for Miis.
User direction 2026-10-07: do not filter the character list now; later go through the
characters one by one, per move (skeleton, weapons, mechanics). Foundation first.

## Next user action

Coordinator changed on 2026-10-07 (evening, at the user's request); the new coordinator
reviewed P16 and installed 0.8.0.

- 0.8.0 works (boot 3). Next: the user runs move workers from `prompts/MOVE-TEMPLATE.md`
  (one move unit each, `MV-<entry>__<donor>`, exclusive paths, parallel-safe) and tells the
  coordinator which finished; the coordinator reviews, integrates all units into the plugin
  and ONE merged motdiff, builds 0.9.0 and installs. Before the first unit comes back the
  coordinator turns `moves.rs` into a dispatcher (per-entry wrapper, lookup of the chosen
  donor instead of "any value = Mii Brawler").
- (done) Run the eight test steps of **0.8.0-moves** (top of `CURRENT_INSTALL.md`): Gunner A gets
  "Forward Tilt: Mii Brawler" in the menu and should kick; Gunner B keeps its own tilt. The
  same boot covers the never-run 0.7.0 features (Sword page, sort by name).
- P14-SWORD-FACTS is finished and still waits for the coordinator's review.
- On the card now: plugin 0.8.0, third build (`0193ba5f...`), `ultimate/mods/mii_customizer_moves/`
  (`motion_list.motdiff` + three clips + `config.json`), `menu.txt` (25 entries, one `allow`), the 0.6.0 edit
  script, `names.txt`, wide presets, the 86-row `list.txt`, `loadouts.txt` as the plugin
  saved it (version 2, three Miis with stat presets).

## Session 5 install (2026-10-07, at the user's request)

- Installed 0.9.0-moves: Brawler up tilt and down tilt added to the Gunner, on top of the forward tilt
  (`evidence/2026-10-07_session5/INSTALL-0.9.0.md`). Offline checks passed; never run in game (tier D).
- Not installed (not ready): normal_jab (PARTIAL stand-in), special_up, special_neutral, aerial_forward,
  aerial_up (PARTIAL, stop conditions), aerial_back and smash_up (in progress, no deliverable).
- Next: the user runs the six steps in `evidence/2026-10-07_session5/INSTALL-0.9.0.md` and reports the log.

## Move round 1 (2026-10-08)

- Running (coordinator-started Claude subagents, `prompts/MOVE-FINISH-ROUND1.md`): Cloud forward air +
  up special (Opus), Snake grenade (Opus), Snake up tilt, Brawler jab, Corrin up air (Haiku).
- MV-aerial_back__mario: check rerun 2026-10-08, exit 0; code not yet read, not integrated.
- Card state per `CURRENT_INSTALL.md`: 0.9.0 installed and never run; 0.10.0 (adds Fox up smash) built,
  not installed. Card was not mounted on 2026-10-08.
- Next for the coordinator: review returning units, make `moves.rs` look up the chosen donor per entry
  (several aerial units share ATTACK_AIR; two up tilts share ATTACK_HI3), merge shared-file additions,
  build the next version.

### 2026-10-14 integration in `plugin/src` (verified offline, tier B/D; nothing run on console)
- Donor dispatcher: `moves.rs` `owned_status_main(fighter, kind, &[(entry, donor, start)])`; a unit runs
  only when the saved Mii chose that donor (preset name) for that entry; units on one status are chained.
- Fixed: `loadout::serialise` wrote the first `IMPLEMENTED_MOVES` donor of an entry instead of the chosen
  one (`menu::slot_names` ignores the preset); now writes the stored preset's name. Host test
  `scratch/2026-10-14_COORD-integration/host_test.rs` 2/2; P7 47/47, P11 35/35, P14 16/16, P16 6/6.
- Integrated: Mario back air (`unit_aerial_back_mario.rs`; fixed raw flag `1` ->
  `FIGHTER_STATUS_ATTACK_AIR_FLAG_ENABLE_LANDING`, keeps the Gunner's ATTACK_AIR loop so autocancel works),
  Cloud forward air + up special (`mccloud.rs`, `unit_aerial_forward_cloud.rs`, `unit_special_up_cloud.rs`,
  statuses 0x220-0x222, Buster Sword article), Snake up tilt (`unit_tilt_up_snake.rs`).
  Build `builds/.cache/coord-target` 0 errors, stack check OK; unit checks of all four exit 0.
- Other mod (`pgwr` 0.20.23 installed, 0.20.24 newest) ships from shared Gunner/Mii files only
  `fighter/miigunner/motion/body/c00/motion_list.bin` (checked in their `MANIFEST.json`, 2026-10-14). So
  `se_miigunner(_c00)`, `vc_mii_*`, `miigunner.sqb`, `ef_miigunner.eff` can ship as ONE merged file each
  (vanilla + every unit's additions, applied in sequence); the motion list stays a `.motdiff`.
- Retarget gap: Mario back air and Fox up smash clips are the donors' raw clips (not retargeted to the
  Gunner skeleton); a retarget pass with Cloud's `mccloud_retarget.py` recipe is running. Mario's script and
  clip names were lowercased (`mcmarioattackairb`) to match every other unit.
- Not yet: shared-file merges (motdiff, effect/sound banks, sqb, config.json, menu `allow` lines), version
  number, package. Snake grenade gets its own test build. Running: jab (Haiku), Corrin up air pass 2 (Haiku).
