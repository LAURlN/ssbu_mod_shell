# P1-ID - find saved Mii Fighter identity candidates

You are a Space Bunny Alpha worker for the separate Mii Customizer mod. The user manually
launched you; do not delegate. Work from the workspace root. Read root AGENTS.md,
kb/INDEX.md, mods/mii_customizer/AGENTS.md, STATUS.md and phases/01_discovery.md.
Before reading the old mod, read mods/ssbu_mod_new/AGENTS.md, projects/pgwr/STATUS.md,
handbook/00_INDEX.md and only relevant listed pages. Old mod is read-only reference.

Goal: find evidence for how a saved Mii Fighter is identified, selected and passed to a battle.
Do not reverse engineer the whole save format or implement persistence yet.

1. Search existing local bindings, symbols, menu/script references and pinned sources for
   saved Mii Fighter records and selection/initialization identifiers.
2. Report at most three strongest candidate identifiers/structures/functions, with exact
   source locations and what each identifies. Distinguish Mii face/avatar identity, a saved
   Smash fighter build, costume, player/entry ID and transient battle-object ID. Multiple
   saved fighters could share an appearance; a name or entry ID alone is not established
   as a persistent key. Do not invent fields or read arbitrary pointers.
3. For each candidate, state what is known/unknown about rename, copy, delete/recreate,
   reboot and two Gunners in one match. Trace one editor/selection-to-match link only if
   available in existing readable source. Otherwise provide the exact smallest next RE task.

Only inspect existing local data and bounded primary-source references; pin external source
commits where possible. No actual user save writes, no requests to dump saves before checking
existing sources, no plugin code, full main decompilation, dependency installation or emulator.
Read tools/REGISTRY.md and extraction playbook before extracting a few necessary files into
workspace gamedata/mii_customizer/P1-ID/; never modify shared inputs or another project.

Exclusive outputs: mods/mii_customizer/research/P1-ID.md and evidence/P1-ID/.
Scratch if needed: mods/mii_customizer/scratch/2026-10-04_P1-ID/.
Include source paths/hashes where applicable, actual commands, evidence tiers,
verified/unverified findings, failed searches and one evidence-backed next experiment.
Stop after the three-candidate brief. End report/chat with P1-ID: DONE/PARTIAL/BLOCKED,
files changed and blocker if any. Do not update shared STATUS or other workers' files.
