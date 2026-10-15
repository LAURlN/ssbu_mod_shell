# P1-DATASET - reproducible Gunner catalogue for the editor

Worker: Space Bunny Alpha, third free instance. Follow root AGENTS.md, kb/INDEX.md,
this mod's AGENTS.md and STATUS.md. Read research/P1-CATALOG.md,
research/P1-CATALOG-AUDIT.md and research/COORDINATOR-2026-10-04.md.
Before old-project reads follow its AGENTS.md, relevant status and handbook index.

Goal: generate a small machine-readable Gunner catalogue from measured local inputs.
This is editor INPUT DATA, not a final loadout/save schema or runtime implementation.
Do not use saved identity, Lua counts or layout assumptions; those workers remain active.

1. Create tools/gunner-catalog/ with a stdlib-only generator, README and meaningful
   validation. Reuse existing input readers read-only if useful; don't modify shared readers.
   Inputs are the pinned Gunner c00 motion list and common fighter_param.prc already extracted.
   Recompute output from those binaries; do not blindly serialize prose tables.
2. Emit evidence/P1-DATASET/gunner_catalog.json with format_version and input provenance
   (relative paths/full hashes). Stable identifiers describe user actions: jab sequence,
   dash attack, three tilts, three smashes, five distinct aerials, grab family, pummel,
   four throws and four special directions. Gunner normals each have one available choice;
   each special direction has three existing alternatives. This is a PROVISIONAL editor
   grouping, not proof of native routing. Group helper motions as dependencies rather than
   user choices. Jab stages stay within a sequence, not freely mixed independent attacks.
3. Store verified motion-kind/script/animation hashes and names where known; retain
   unknown names explicitly. Preserve raw flags and separated timing bytes as raw authored
   data, not runtime frame promises. Do not fabricate dependency closure for specials.
   Display names may be plain English author labels, clearly distinguished from game strings.
4. Include the twelve numerical stat candidates from P1-CATALOG, decoded types/defaults
   and hashes, with runtime override support and safe ranges marked UNKNOWN. No inferred
   ranges or cross-stat independence. Keep Final Smash, get-up, ledge and taunts explicitly
   pending scope; don't enumerate recovery movements as get-up attacks.
5. Validate determinism, unique slot/choice identifiers, expected five aerial slots,
   binary hash joins for known references, correct stat types and Gunner row identity.
   Include a negative control for a wrong input hash or unresolved/mismatched known reference.
   Prove byte-field separation for representative raw 334/318 entries. Coverage gaps should
   be machine-readable, not silently omitted. Do not claim a complete move port.

Exclusive writes under this mod: tools/gunner-catalog/, research/P1-DATASET.md,
evidence/P1-DATASET/ and scratch/2026-10-04_P1-DATASET/.
No other outputs. Original inputs read-only; avoid new extraction/dependencies.
No changes to Lua inspector (P1-LUA-WRITE owns it), layouts (P1-LAYOUT), identity
(Opus P1-ID-REVIEW), old reports/mods, shared status/contracts, saves or SD.
No build/plugin, emulator, console, commits, installs or subagents.
If a reader/dependency isn't available, report the precise missing capability rather
than developing a new general PRC library. Stop after catalogue, validation and short report.
End report/chat P1-DATASET: DONE/PARTIAL/BLOCKED with changed files and observed checks.
