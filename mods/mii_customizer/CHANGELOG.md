# Changelog

## Unreleased - 2026-10-04

- Created separate Mii Gunner customization project and manual three-worker phase workflow.
- Prepared bounded UI, saved-fighter identity and move/stat catalogue research prompts.
- No runtime code, build, installation, emulator or console test.
- Reviewed completed UI/catalogue discovery, checked representative hashes, corrected unsupported
  interpretations, and prepared two independent follow-ups while identity discovery continues.
- Reviewed both follow-ups and independently reran Lua inspector and catalogue claim checks;
  all passed. Identity discovery and runtime integration remain pending.
- Prepared independent shared-Lua-global and layout-rebuild prompts for the two free workers.
- Reviewed completed identity/globals reports; prepared one focused Opus identity audit
  and an Alpha Lua reserialization task while the layout task continues.
- Prepared a third independent Alpha task for a reproducible Gunner catalogue; clarified
  that the three-worker limit applies to Alpha instances, with premium work additional.
- Reviewed premium identity audit; corrected erroneous battle-handoff/name/hash/division
  claims in P1-ID and independently checked modular inverse arithmetic. A per-player
  selection link is identified offline; match setup remains unresolved. Three Alpha
  tasks confirmed active; no new premium task or console test.
- Reviewed all remaining Alpha reports; reran Lua/catalogue checks and unchanged
  archive controls. Corrected BFLYT section-count/table interpretation and unsupported
  checksum/animation/alignment conclusions; prepared three scoped P2 Alpha prompts.
- Reviewed P2 layout/archive tools; reran 71/71 and 87/87 checks. Corrected
  report framing/spacing/count-update details. Prepared independent controlled
  layout diagnostic and per-instance stat API prompts while Lua flow continues.
- Wrote HANDOFF.md for another model; reconciled status with the completed P2-UI-FLOW
  report and documented follow-up prompt launch state as unconfirmed.
- New coordinator took over. Reviewed P2-UI-FLOW against its disassembly and corrected the
  cache write-back index (`cache[command_id + 1] = option`, not a flattened index) and the
  help-number value. Reviewed P2-LAYOUT-PATCH: reran 80/80 checks, reproduced the two-byte
  archive difference independently, corrected an unsupported install path. Prepared
  P2-SKILL-NATIVE and P2-LUA-EDIT prompts. No runtime code, package or console test.
- Reviewed P2-SKILL-NATIVE (174/174 rerun; get/set handlers disassembled by coordinator:
  one byte per special slot at scene object +0x100), P2-STAT-API (59/59 rerun) and
  P2-LUA-EDIT (217 checks rerun; evidence/scratch had been written at the workspace root
  and were moved into the mod). Prepared P2-SKILL-STORE (premium), P2-UI-CONSTS and
  P2-STAT-READS prompts. No runtime code, package or console test.
- Reviewed P2-SKILL-STORE (special choices are saved-record bytes +0x142..+0x145, values
  0..2, commit refuses larger values), P2-UI-CONSTS (3 options, 4 slots as immediates) and
  P2-STAT-READS (engine fetches weight/walk speed through a per-object vtable slot). Reran
  88/88 and 179/179 checks and re-read the key instructions. Prepared P2-MATCH-READER
  (premium), P2-STAT-HOOKPOINT and P2-PLUGIN-SCAFFOLD prompts. No package or console test.
- Reviewed P2-MATCH-READER (saved ID stored per player in a static table next to the special
  bytes), P2-STAT-HOOKPOINT (float-param slot function 0x4e53e0 located; old mod hooks a
  script wrapper that re-dispatches to it) and P2-PLUGIN-SCAFFOLD (mod-owned log-only NRO
  builds). Moved stray worker JSON output from the workspace root into the mod scratch.
  Prepared P3-DIAG-PLUGIN (premium) and P3-ARC-PROBES for a single first console gate.
- At the user's request added two independent Alpha tasks for the idle slots:
  P3-CUSTOMIZE-SITES and P3-SPECIAL-VARIANTS.
- Reviewed P3-DIAG-PLUGIN, P3-ARC-PROBES, P3-CUSTOMIZE-SITES and P3-SPECIAL-VARIANTS; reran
  their checks. Fixed an unterminated string in the Lua probe's info.toml. Assembled
  `builds/0.1.0-gate1/` (log-only plugin 0.1.0-diag + two file probes) with manifest and check,
  and wrote the first console test plan in CURRENT_INSTALL.md. Not installed, not run.
- Installed gate-1 step 1 (libmii_customizer.nro 0.1.0-diag) on the SD card at the user's
  explicit request; add-only, hashes verified, other plugins unchanged. Compared the card's
  Skyline hook functions with the analysed lab copy: same logic.
- Gate 1 test 1 ran on the console without crash. Tier A: hook offsets valid, per-fighter
  repeated float-param requests at 0x4e53e0, per-player saved-Mii ID slots filled at fighter
  creation. Wrote evidence/2026-10-04_gate1/RESULT.md. Installed the two file probes for test 2.
- Gate 1 test 2: user saw the smaller first row and the side-special sub-title; edited Lua
  and layout files load through ARCropolis (tier A, RESULT_test2.md). Gate 1 complete.
  Prepared P4-OVERRIDE-SLICE (premium; loadout file format v1), P4-LUAC, P4-BRIDGE-FACTS
  and P4-STAT-SITES.
- Reviewed P4-OVERRIDE-SLICE (plugin 0.2.0, loadout file v1; accepted with one documented
  deviation), P4-LUAC (format-matching Lua compiler), P4-BRIDGE-FACTS and P4-STAT-SITES; reran
  their checks except the slow stat scan. Wrote the gate-2 install and test plan. Prepared
  P5-LUA-SOURCE, P5-UI-API and P5-MSG-PROBE for the editor UI.
- Installed 0.2.0-override and the example loadout file on the card at the user request;
  removed the gate-1 probes; other plugins unchanged.
- Gate 2 passed on the console: per-saved-Mii weight / walk speed override works and follows
  the saved-Mii ID (tier A, evidence/2026-10-05_gate2/RESULT.md). Recorded the user's direction
  for the UI (character stat presets, headgear-style list, entry in the Mii maker menu).
  Prepared P6-HAT-UI, P6-EDIT-MENU and P6-PRESET-DATA; defined preset file format v1.
- Reviewed P5-LUA-SOURCE (source reproduces the special-move script except one header flag
  byte), P5-UI-API and P5-MSG-PROBE (message patch probe staged). Prepared P7-PRESET-ENGINE
  (premium) with the preset and loadout v2 contracts.
- Reviewed P6-HAT-UI, P6-EDIT-MENU and P6-PRESET-DATA; reran their checks (722, 264, 30).
  Changed `tools/stat-presets/check_presets.py` to keep its temporary game-derived files under
  workspace `gamedata/` and delete them at exit; removed 45 MB of such files from the mod
  scratch. Prepared P8-LUA-LIST, P8-EDIT-DISPATCH and P8-HAT-NATIVE.
- Reviewed P8-LUA-LIST and P8-HAT-NATIVE (checks rerun: 1667, 221); P8-EDIT-DISPATCH stopped
  without a report, its evidence was read and partly re-checked. Corrected P8-HAT-NATIVE in
  place (headgear constructor identified). Chose a working direction for the UI and prepared
  P9-EDIT-DISPATCH, P9-HAT-HANDLES and P9-EDIT-SOURCE.

- Rewrote HANDOFF.md for a new coordinator (state as of the running P9 round).
- New coordinator took over from HANDOFF.md. Reviewed the P7 and P9 round: reran every check
  (P7 35/47/61/98/8 plus the build hash reproduced; P9-EDIT-DISPATCH 774/0, P9-HAT-HANDLES
  396/0, P9-EDIT-SOURCE 7/7 controls and both chunks byte-identical; msg probe 8/8; P8 hat
  221/0; P4 stat sites 3327/0) and corrected two reports in place. Decided the UI entry: exit
  value 7, plugin rewrites to 1; values >= 9 abort (trap at 0x180cf00). Kept the native
  headgear-list route; fallback unchanged. Wrote the combined console session in
  CURRENT_INSTALL.md (plugin 0.3.0, presets.txt, loadout v2, message probe, edit probe) and
  asked the user for the card.

## Unreleased - 2026-10-05 (boot 1)

- Installed the 0.3.0-presets session and ran boot 1 on the console. Result (tier A,
  `evidence/2026-10-05_session1/RESULT.md`): the per-saved-Mii stat preset works (all ten
  fields overridden for `0000f589` with preset `fox`, felt in play); a Lua chunk of different
  length loads; the added message label did not resolve (raw key shown); the edit-menu Favorite
  probe showed no visible change.
- Identified the card's ARCropolis as an older-generation build from its own strings
  (`arcropolis::fs::loaders`, Orbits, old XMSBT wording; no v4.1.x `modfs` markers), consistent
  with the 13.0.4 gate (v4.0.7/v4.0.8) and with no ARCropolis log file written during boot 1.
  Corrected the `kb/reference/ssbu-modding-stack.md` ARCropolis row that named v4.1.1.
- Prepared boot 2 in `CURRENT_INSTALL.md`: loadout swap (`purin` + explicit `weight 130.0`;
  `fox` for `0000f58b`) and `logging_level` raised to `Debug`; waits for the card and a go-ahead.

## Unreleased - 2026-10-05 (boot 2, P10 round prepared)

- Boot 2 ran on the console (tier A, `evidence/2026-10-05_session1/RESULT_boot2.md`): explicit
  line beats the preset per field, second preset, two Miis with different presets, stale ID
  slot harmless for a non-Mii fighter. ARCropolis wrote no log at `Debug`; `logging_level`
  restored to `Warn` on the card. New coordinator took over from `HANDOFF.md` revision 2.
- Offline: both label families the list needs are in `msg_name.msbt`; the 0.3.1 Favorite probe
  could not work by design (source order re-read), so it says nothing about chunk loading.
- Decided to skip a probe-only boot and go for the UI milestone. Prepared P10-UI-SLICE
  (premium; plugin 0.4.0, contracts E, F, B+), P10-EDIT-ENTRY, P10-PRESET-WIDE, P10-HAT-OPEN.

## Unreleased - 2026-10-06 (P10 round reviewed, session 0.4.0-ui ready)

- Reviewed P10-EDIT-ENTRY, P10-PRESET-WIDE and P10-HAT-OPEN; reran their checks (exit 0;
  472/0 for HAT-OPEN after removing one claim that could not pass). Corrected in place:
  three statements in P10-HAT-OPEN (second write path, cancel restore, meaning of
  `0x328b5d0`) and the inverted `0x328b5d0` conclusion in P9-HAT-HANDLES.
- P10-UI-SLICE stopped without report, tests or manifest. Coordinator read the source,
  reproduced the NRO hash, checked all 20 site/probe word records against the image
  (`scratch/2026-10-05_coordinator/check_ui_sites.py`, 52/0), ran the 0.3.0 host tests on the
  new sources (47/0), wrote `research/P10-UI-SLICE.md` and `builds/0.4.0-ui/MANIFEST.json`.
- Wrote session `0.4.0-ui` in `CURRENT_INSTALL.md` (READY, not installed).
- Installed session 0.4.0-ui on the card (2026-10-06, user go-ahead); hashes verified.

## Unreleased - 2026-10-06 (session 2 result, P11 round prepared)

- Session 2 ran on the console: the in-game character list works (tier A,
  `evidence/2026-10-06_session2/RESULT.md`); the edit-menu chunk loads; runtime saving works;
  the Mii is unchanged by mod mode.
- Recorded the user's direction for a paged customization menu. Defined contracts M and G.
  Prepared P11-MENU (premium), P11-ROW-TEXT, P11-INT-PARAMS, P11-MOVE-PLAN.

## Unreleased - 2026-10-07 (P11 round reviewed, session 0.5.0-menu ready, P12 round prepared)

- New coordinator took over (2026-10-07). Reviewed the P11 round: P11-MENU (plugin 0.5.0,
  pages on the native headgear list; check 358/0 with 11 controls, host tests 47/0 + 35/0,
  NRO hash, source and four code windows re-read), P11-ROW-TEXT (340/0), P11-MOVE-PLAN (4/4;
  unverified parts marked in a banner). P11-INT-PARAMS stopped without a report and is
  continued by P12-INT-PARAMS. Wrote the session's `menu.txt` (Stats + 23 slots) and a
  `list.txt` without the Mii Gunner row, parsed both with the plugin's own parsers, and
  staged session `0.5.0-menu` as READY (not installed, never run). Decided to investigate
  Mii Brawler's forward tilt as the first borrowed move; prepared P12-INT-PARAMS,
  P12-FTILT-FACTS and P12-SCRIPT-ROUTE. No console test yet.
- Installed session 0.5.0-menu on the card (2026-10-07, user go-ahead); hashes verified; backup in evidence/2026-10-07_install_backup/.
- Session 3 boot 1: 0.5.0 installed no UI hook (foreign inline hook on the probed entry 0x37a22f0). Coordinator built 0.5.1 (probe accepts that stub at that entry), host tests 47/0 + 35/0, installed and verified on the card. Not tested.
- Session 3 boot 2: 0.5.1 works on the console (tier A): menu pages, greyed rows, literal row text, stats set/clear, saving, reboot. Result recorded.
- Built 0.5.2 at the user's request: main-page rows show the current choice ("Stats: Kirby"); new optional names.txt and names.rs; host tests 47/0 + 35/0 + 4/0. READY, not installed.
- Installed 0.5.2 and names.txt on the card (2026-10-07, user go-ahead); hashes verified.
- User request: Minus opens the mod menu anywhere on the edit menu, with a button tip. Prepared P13-MINUS-ENTRY and P13-KEYHELP for GPT 6 Luna workers (the user's choice of model).
- Reviewed the P13 round (GPT 6 Luna): P13-KEYHELP done (check rerun), P13-MINUS-ENTRY partial and corrected in place. Coordinator built 0.6.0: plugin reads Minus (nn::hid) on the edit menu and signals the script through a Lua global; edit script variant `minus` with the keyhelp block; host tests 47/0 + 35/0, script build check exit 0. READY, not installed.
- 0.5.2 ran on the console: names.txt loaded (87/0), composed row text set without a miss (log_boot3_0.5.2.txt); visual fit not yet reported.
- 0.5.2 row text confirmed good by the user. Installed 0.6.0-menu on the card (2026-10-07, user go-ahead); hashes verified.
- 0.6.0 works on the console (user report): Minus opens the menu, button tip. User asked for three more tasks; prepared P14-LIST-PLAYABLE, P14-SORT-OPTIONS (plugin 0.7.0) and P14-SWORD-FACTS.
- Reviewed P12-INT-PARAMS (558/0), P12-SCRIPT-ROUTE (17/17) and P14-SORT-OPTIONS (389/0, host tests 47+35+16; sort code read); banners added. P14-LIST-PLAYABLE parked at the user's request. 0.6.0 confirmed by its log. Staged session 0.7.0-menu (menu.txt with the Sword entry). READY, not installed.
- Wrote HANDOFF.md revision 5 for the next coordinator and P15-FTILT-TAKEOVER (finish the forward-tilt facts task from the first worker's unreviewed tables).
- Forward-tilt facts finished by the takeover worker (check rerun exit 0). At the user's request replaced further research with an implementation task: wrote P16-FTILT-MOVE (plugin 0.8.0, first borrowed move). P14-SWORD-FACTS reported done, not yet reviewed.
- New coordinator took over (2026-10-07 evening). Reviewed P16-FTILT-MOVE: check and host tests rerun (47+35+4+16+6), worker NRO `2890bc58...` reproduced by rebuild, the three added motion-list entries checked field by field, `fighter/miigunner/c00` confirmed in the user's data.arc as the Gunner's only costume group, Smashline imports matched against the card's build. One coordinator edit in `moves.rs` (leaving the ground during the borrowed tilt goes to FALL); NRO `cdb4f7e0...`, manifest regenerated. Installed 0.8.0-moves on the card at the user's request (plugin, `menu.txt`, new folder `ultimate/mods/mii_customizer_moves/`); hashes verified, other plugins unchanged. Includes the never-run 0.7.0 features. Not run yet.
- Session 4 boot 1: 0.8.0 crashed at startup. Crash report read: stack overflow in the plugin's `main` (324496-byte frame, 64 KiB stack) from the menu and loadout tables being passed by value since 0.7.0. Coordinator fix: both tables heap-allocated and initialised in place; new check `tools/stack-frames/` (0.6.0 19584 / 0.7.0 283552 / crashed 324496 / fixed 18672 bytes); host tests adapted and passing. Fixed NRO `8198bd49...` installed on the card, verified. Not run yet.
- Session 4 boot 2: 0.8.0 boots and the menu, slot storage and per-Mii move resolution work on the console; the borrowed tilt froze in the bind pose. Cause: `pyra_gamewatch_reskin` ships its own Gunner `motion_list.bin` and ARCropolis kept it (`conflicts.json`). Package now ships `motion_list.motdiff` (new tool `tools/move-package/motdiff`, checked against both the vanilla and the other mod's list); plugin returns the vanilla move when the owned motion is not loaded (`0193ba5f...`). Installed, verified; the other mod untouched. Not run yet.
- Session 4 boot 3: 0.8.0 works on the console (user report + log): first borrowed move, per saved Mii, alongside the other mod's Gunner motion list. Wrote `prompts/MOVE-TEMPLATE.md`: a reusable, parallel-safe worker prompt for one move unit (`moves/<entry>__<donor>/`); the coordinator integrates units and installs.
- `prompts/MOVE-TEMPLATE.md` revision 2 at the user's direction: permissive and outcome-first (custom statuses, retargeting, articles, effect and sound ports, free reuse of the other mod's recipes); only the parallel-work and shared-file constraints remain.
- 2026-10-08: surveyed the move units (integrated: Brawler forward/up/down tilt, Fox up smash; DONE unreviewed: Mario back air; unfinished: Brawler jab, Cloud forward air and up special, Corrin up air, Snake grenade and up tilt). At the user's request the coordinator now starts Claude subagents itself: wrote `prompts/MOVE-FINISH-COMMON.md` (shared brief with all reference sources) and started round 1 (`prompts/MOVE-FINISH-ROUND1.md`: two Opus 5.5 workers, three Haiku 5.5 workers). Snapshot of `plugin/` for the workers: `builds/.cache/plugin_base_0.10.0/`.
