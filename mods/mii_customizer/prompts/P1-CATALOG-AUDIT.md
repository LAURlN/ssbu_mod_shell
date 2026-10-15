# P1-CATALOG-AUDIT - verify slot grouping and suspicious timing fields

Follow workspace AGENTS.md, kb/INDEX.md, mods/mii_customizer/AGENTS.md and STATUS.md.
Read your completed research/P1-CATALOG.md and research/COORDINATOR-2026-10-04.md.
Before old-mod reads, follow its AGENTS.md, project status and handbook index.
P1-ID continues independently. Do not touch identity/save/native UI binding research.

One goal: make the proposed Gunner slot inventory dependable before a UI consumes it.

1. Resolve attack_s3_s vs attack_s4_s from the original motion list and existing labels,
   bindings or status/script references. Verify forward-tilt coverage and directional variants.
   A missing local script body is not proof the move is absent. Record exact provenance.
2. Check 4-6 representative motion entries, including attack_s4_s (reported 334),
   attack_air_hi (318), attack_hi3 and a jab. Pin raw offsets/bytes and investigate the reader's
   cancel interpretation with existing format evidence. Round-trip equality alone is not
   semantic validation. If undecidable, explicitly retain raw unknown fields and do not
   report them as frames. Do not rewrite shared motion-list tools.
3. Produce one compact candidate user-facing slot table: group jab sequence, smash
   hold/start/release, aerial landing, grab variants and special sub-states as dependencies
   where appropriate. Each of the five aerial directions has its own selectable slot.
   Use the already-decoded AI attack list only as a cross-check, not an authoritative UI list.
   Keep Final Smash/get-up/ledge/taunts explicitly pending scope decisions.
4. Correct your completed P1-CATALOG.md in place where findings are refuted. Preserve
   uncertainty; weight is not gravity/fall speed, and independent overrides remain unverified.

Exclusive writes under this mod: research/P1-CATALOG-AUDIT.md, research/P1-CATALOG.md
(completed report corrections only), evidence/P1-CATALOG-AUDIT/ and
scratch/2026-10-04_P1-CATALOG-AUDIT/. Reuse prior inputs read-only; only if necessary extract
up to three small extra files into workspace gamedata/mii_customizer/P1-CATALOG-AUDIT/.
Check tools registry first. No bulk asset extraction, dependency installation, production
code, shared tool edits, saves, SD, emulator, console, commits or other worker edits.
Don't spend time resolving every unnamed helper. Stop after the slot table, representative
timing audit and corrections; return PARTIAL with a specific next question if necessary.
Report commands, raw evidence/hashes, tiers, verified/unverified claims and limitations.
End report/chat P1-CATALOG-AUDIT: DONE/PARTIAL/BLOCKED and changed files.
