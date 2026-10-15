# P1-UI - locate Mii Fighter editor resources

You are a Space Bunny Alpha worker for the separate Mii Customizer mod. The user manually
launched you; do not delegate. Work from the workspace root. Read root AGENTS.md,
kb/INDEX.md, mods/mii_customizer/AGENTS.md, STATUS.md and phases/01_discovery.md.
Before reading the old mod, read mods/ssbu_mod_new/AGENTS.md, projects/pgwr/STATUS.md,
handbook/00_INDEX.md and only the relevant listed pages. Old mod is read-only reference.

Goal: a small inventory of the existing Smash Mii Fighter editor UI, not implementation.

1. Search the existing ARC path index and local references for Mii Fighter editor layouts,
   menu Lua/controller scripts, text labels and customization-preview inputs. Separate the
   Smash fighter editor from the Switch system Mii appearance editor.
2. List the strongest 5-15 candidate files with exact ARC/local paths and why relevant.
   Inspect at most three most relevant files with available tools. If decoding is unavailable,
   record that; do not install tools or fabricate controller names.
3. Explain which observed file/code handles existing special-move selection, if established.
   Identify one candidate extension point for adding a normal-move selector or stat field.
   Mark unknown controller-to-native boundaries explicitly. Do not promise a hook works.

Use rg first. Read tools/REGISTRY.md and kb/playbooks/extracting-single-files-from-data-arc.md
before extraction; extract only a few inputs to workspace gamedata/mii_customizer/P1-UI/.
Do not modify inputs, existing mods, shared scripts, saves, plugins or SD files. No emulator.
No production code or mockup in this task. Stop once the bounded inventory is complete.

Exclusive outputs: mods/mii_customizer/research/P1-UI.md and evidence/P1-UI/.
Scratch if needed: mods/mii_customizer/scratch/2026-10-04_P1-UI/.
Report paths, input hashes for inspected data, actual commands/checks, A/B/C/D tiers,
verified/unverified findings, exact failures and one narrowly scoped next task.
End report and chat with P1-UI: DONE/PARTIAL/BLOCKED, files changed and blocker if any.
Do not update shared STATUS or other workers' files.
