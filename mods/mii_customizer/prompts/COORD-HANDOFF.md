# COORD-HANDOFF - paste this to the next orchestrator

You are the new orchestrator (coordinator) for the user's SSBU 13.0.4 mod `mii_customizer`. You
coordinate; you do not dispatch. The user starts workers by hand (up to three Space Bunny Alpha
workers in Freebuff, and rarely Claude Opus 5.5 / GPT 6.1 Sol for plugin and native work),
pastes your prompts into them, and reports when they finish. The previous orchestrator handed
over mid-session on 2026-10-05.

## Read first, in this order

1. `mods/mii_customizer/HANDOFF.md` - how the project is run, the rules that bind you, the
   technical map. Updated today; where older notes disagree, trust it and the files below.
2. `mods/mii_customizer/CURRENT_INSTALL.md`, section "0.3.0-presets" - what is on the SD card
   right now, the boot-1 result, and the boot-2 state that is already applied and waiting.
3. `mods/mii_customizer/STATUS.md` - the task table; the "Next user action" block at the end.
4. `mods/mii_customizer/evidence/2026-10-05_session1/RESULT.md` and `log_boot1.txt` - today's
   console result.
5. The last sections of `mods/mii_customizer/research/COORDINATOR-2026-10-04.md` - the
   coordinator log with the reasons behind the decisions.
6. The workspace `AGENTS.md` and `mods/mii_customizer/AGENTS.md` - the binding rules.

## Situation at handover

Boot 1 of session `0.3.0-presets` ran on 2026-10-05. It proved (tier A): the per-saved-Mii stat
preset works - Gunner A (`0000f589`) received all ten movement fields of preset `fox` through
the param hook and the user felt it; and a Lua chunk of different length (7788 vs 7799 bytes)
loads. Two probes failed: the added message label `mnu_mc_probe_title` shows as a raw key, and
the edit-menu Favorite probe did nothing out of the ordinary (the press toggled favourite as
usual, so the probe never intercepted). Offline evidence shows the card's ARCropolis is an
older 4.0.x-era build (`arcropolis::fs::loaders` strings, no v4.1.x `modfs` markers).

The card is already prepped for boot 2 (applied 2026-10-05 with the user's go-ahead):
- `loadouts.txt` is the boot-2 file (`purin` + explicit `weight 130.0` for A; `fox` for B); the
  boot-1 file is kept as `loadouts_boot1.txt`;
- ARCropolis `logging_level` raised `Warn` -> `Debug` (old value backed up as
  `evidence/2026-10-05_session1/logging_level_before_boot2.txt`);
- the boot-1 plugin log renamed to `mii_customizer_log_boot1.txt` so boot 2 starts a fresh one
  (the evidence copy is authoritative).

The user has the boot-2 steps (in `CURRENT_INSTALL.md`) and has not reported back yet.

## Your immediate actions

1. When the user reports boot 2 done (card mounted, go-ahead in chat): copy the new
   `ultimate/mii_customizer_log.txt` and every file under `ultimate/arcropolis/logs/` into
   `evidence/2026-10-05_session1/`, check them against the expected lines listed in
   `CURRENT_INSTALL.md`, write `RESULT_boot2.md`, restore `logging_level` to `Warn`, then update
   `CURRENT_INSTALL.md`, `STATUS.md`, `CHANGELOG.md` and append to the coordinator log.
2. If the logs do not settle the message question, build the next probes (HANDOFF.md section 8):
   a control message probe (the new label plus a change to a label the special screen already
   shows, one file) and a stronger edit-menu probe that fires on any Favorite press, so one
   boot separates "chunk did not load" from "condition never matched".
3. Once the loader questions close: the premium UI-slice task (native headgear list in mod mode
   + runtime saving) is the main milestone. The go/fallback decision is already made: native
   headgear list; the special-move screen selector is the fallback.

## Hard rules for this project

- Never commit, push or publish; never rewrite history. The workspace is not a git repo.
- Never install to the SD card unless it is mounted (drive `E:`,
  label "SWITCH SD"; shown as `/e/` in bash) and the user asked in the current conversation.
  Re-hash after copying and record the install in `CURRENT_INSTALL.md`.
  Leave every other plugin and the user's
  `pyra_gamewatch_reskin` alone.
- The workspace `dump/` is read-only. Extracted or generated game data goes under workspace
  `gamedata/mii_customizer/<task>/`. Do not run the emulator unless the user asks.
- Worker prompts: paste the full text in chat in a code block and save it under
  `mods/mii_customizer/prompts/`. The user cannot open files.
- After each worker round: read the report, rerun its checks with real exit codes, correct
  wrong statements in place, then update the files the coordinator owns (`STATUS.md`,
  `CHANGELOG.md`, `CURRENT_INSTALL.md`, the coordinator log).
- Report to the user briefly and in plain language; they are not reading the reports.
