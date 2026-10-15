# P1-UI-GLOBALS - find definitions of editor globals

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/P1-UI-DECODE.md, research/COORDINATOR-2026-10-04.md and
tools/lua53-inspect/README.md. This is an independent UI-worker follow-up; P1-ID
continues and owns saved-fighter identity/native save-to-battle tracing.

One goal: determine whether the shared Lua modules define the editor's counts/flags.
Use the existing inspector read-only; no new parser or full source decompiler.

1. Find exact indexed paths for common/ui_common, common/state_function and
   menu/chara_make/make_mii_utility. Do not assume require names equal ARC paths.
   Extract only those three chunks into workspace gamedata/mii_customizer/P1-UI-GLOBALS/.
   Read workspace tools/REGISTRY.md and the extraction playbook before extraction.
2. Run verify and xref for SKILL_COMMAND_NUM, SPECIAL_SKILL_NUM, IS_SKILL_EDITABLE
   and IS_READ_ONLY. Where present, inspect assignment instructions and their value
   provenance. Distinguish SETTABLE/SETTABUP assignments from reads and calls.
3. If a definition points to another required Lua module, follow at most two more
   small chunks. Maximum five inputs. Record numeric values only when actual
   assignment/data flow proves them. Missing writes do not prove native injection.
4. Report what this permits us to change in Lua, and one precise unresolved bridge
   or extension question for implementation. Do not trace native targets or identity.

Exclusive writes under this mod: research/P1-UI-GLOBALS.md,
evidence/P1-UI-GLOBALS/ and scratch/2026-10-04_P1-UI-GLOBALS/.
No edits to old reports, shared tools, UI assets, saves, STATUS or other workers.
No dependency installs, game launches, SD access, commits, or full main analysis.
Stop after five chunks or the first conclusive definitions. If none define the names,
return PARTIAL with the searched set and exact boundary; do not start another search project.
Include hashes, commands, relevant instruction offsets, tiers and verified/unverified
claims. Keep the report short. End saved report/chat P1-UI-GLOBALS: DONE/PARTIAL/BLOCKED,
changed files and a concrete next step. Runtime behavior remains unverified.
