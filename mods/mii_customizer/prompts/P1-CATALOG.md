# P1-CATALOG - Gunner move slots and stat inputs

You are a Space Bunny Alpha worker for the separate Mii Customizer mod. The user manually
launched you; do not delegate. Work from the workspace root. Read root AGENTS.md,
kb/INDEX.md, mods/mii_customizer/AGENTS.md, STATUS.md and phases/01_discovery.md.
Before reading the old mod, read mods/ssbu_mod_new/AGENTS.md, projects/pgwr/STATUS.md,
handbook/00_INDEX.md and relevant pages 04/05/06/09. Old mod is read-only reference.

Goal: a concrete inventory for a Gunner-only editor, not a port or a final shared schema.

1. From local Gunner script/motion/parameter inputs, catalogue normal attack slots
   (jab sequence, dash attack, tilts including observed directional variants, smashes,
   five aerials, grab/pummel/throws) and four special categories with existing alternatives.
   Note landing/ground-air/helper motions separately from user-facing move slots. Mark
   Final Smash, get-up/ledge attacks and taunts as unresolved scope rather than dropping them.
   Record exact internal names and supporting paths; unknown values stay unknown.
2. Identify up to twelve useful initial numerical stats (weight, movement, gravity/jumps,
   etc.) with exact parameter names/types and defaults if locally measurable. Don't guess
   defaults, safe ranges or claim every runtime reader uses the same table.
3. Recommend one simple stat and one normal slot for the first vertical slice; identify
   any existing per-battle-object parameter override example as a source reference only.
   A single-choice Gunner normal is a valid initial menu entry, not a move port.

Use existing tools only. Read tools/REGISTRY.md and extraction playbook before extracting
small necessary inputs into workspace gamedata/mii_customizer/P1-CATALOG/. Avoid bulk
animations/models or entire fighter folders. No code/build/menu edits, new dependencies,
emulator, SD writes or other mod changes. No Brawler/Swordfighter port in this task.

Exclusive outputs: mods/mii_customizer/research/P1-CATALOG.md and evidence/P1-CATALOG/.
Scratch if needed: mods/mii_customizer/scratch/2026-10-04_P1-CATALOG/.
Include tables, actual commands, input hashes, evidence tiers, verified/unverified status,
coverage gaps and one small next task. Stop after the bounded catalogue.
End report/chat with P1-CATALOG: DONE/PARTIAL/BLOCKED, changed files and blocker if any.
Do not update shared STATUS or other workers' files.
