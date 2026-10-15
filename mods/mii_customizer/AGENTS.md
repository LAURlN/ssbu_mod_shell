# Mii Customizer - agent rules

Read workspace `AGENTS.md`, this file, `STATUS.md`, and your assigned prompt before working.
Paths here are relative to this mod unless explicitly identified as workspace-relative.

## Scope

- Separate SSBU 13.0.4 mod, initially Mii Gunner only. Target: in-game Mii Fighter editor with
  selectors for move slots and editable stats, persistent per-saved-fighter loadouts.
- Initial library is vanilla Gunner moves (including existing special alternatives).
  Later phases add Brawler and Swordfighter moves. No roguelike or PC port in this project.
- Native Mii editor integration is the goal. A mockup or external config editor is not equivalent.
  If integration is blocked, report evidence; do not silently substitute another interface.
- New moves must own their dependencies and state. No fighter-kind casts, borrowed donor state,
  forced per-frame status changes, placeholder assets, or hidden failures presented as completion.

## Coordination and quota

- The coordinating chat scopes tasks, reviews all results, integrates shared changes and releases
  the next phase. The user copies prompts and starts workers manually. Never operate Freebuff,
  auto-dispatch workers, spawn subagents, message other chats or invoke premium agents yourself.
- At most three Space Bunny Alpha workers run together. Prompts must define one bounded task,
  allowed write paths, deliverables and stop conditions. Finish your task; do not take another.
- User authorized rolling independent follow-ups on 2026-10-04: completed workers may receive
  new tasks while another worker continues. Keep the three-worker limit and exclusive paths;
  wait for prerequisite reports before dependent implementation or shared integration.
- Claude Opus 5.5 / GPT 6.1 Sol are reserved for specific architecture, native RE, integration or
  debugging problems that require them. Provide an evidence-backed escalation brief instead of
  repeatedly guessing. The coordinator gives the user a focused prompt when escalation is needed.
- Workers write only assigned paths. Coordinator owns `STATUS.md`, `CURRENT_INSTALL.md`,
  `CHANGELOG.md`, phase plans and shared contracts. No shared source/build edits during another task.
- Do not edit the existing `ssbu_mod_new` project. Read its rules before using it as a reference;
  link canonical facts rather than copying its handbook. Do not assume its ports support Miis.
- No commits, branches, remote pushes, publishing or system-wide installs without user instruction.

## Evidence and outputs

- A: console evidence; B: offline measurements or explicitly requested emulator runs;
  C: pinned external source (URL + commit); D: hypothesis. Mark observed results verified and
  unchecked claims unverified. Source inspection and compilation do not establish runtime behavior.
- Reports include exact relative input paths, hashes for binary/data claims, commands, concise
  results, failures, limitations and the next experiment. Do not claim a missing file until you
  check the local archive index and existing extraction tools. No arbitrary pointer probing.
- Evidence belongs in `evidence/<task>/`; research in `research/<task>.md`. Scratch is
  `scratch/<YYYY-MM-DD>_<task>/`. Reusable mod tools go in `tools/<name>/` with README and a smoke check.
- Inputs are read-only. Extraction goes to workspace `gamedata/`, with task-specific output folders
  when needed to avoid collisions. Never copy game assets into source for convenience.
- No absolute machine paths in code/docs. Use relative paths or a future project `paths.toml`.
- End with task ID, DONE/PARTIAL/BLOCKED, changed files, observed checks and unresolved questions.
  Persist that summary in your report so the user need only tell the coordinator you finished.

## Testing and releases

- Do not run the emulator or console, install to SD, or modify framework plugins.
- Coordinator requests a console test only when it resolves a runtime blocker or validates a
  meaningful coherent batch. Always state which decisions depend on the test and why offline
  evidence cannot settle them. Avoid tests for each cosmetic or independently checkable change.
- Batch compatible checks in one package; retain separate toggles/variants for causal controls.
  Include a vanilla control, two differently configured Gunners where relevant, concise numbered
  steps, expected outcomes, required evidence and rollback instructions.
- READY requires a concrete versioned package, manifest hashes and offline checks. Builds belong
  in `builds/<version>/`, caches in `builds/.cache/`. User controls installation and game runs.
- Unknown identity, corrupt config or unsupported loadout must have an explicit safe default.
  Version custom data; validate numeric values and isolate state per battle object. Do not extend
  or overwrite the native save format until that design has been reviewed.
