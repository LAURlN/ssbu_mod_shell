# Phase 1 - discover inputs and integration boundaries

2026-10-04. Three independent Space Bunny Alpha tasks; all are research, no shipping code.
Purpose: make the next implementation task small and evidence-backed, without premature
schema decisions or a complete decompilation of the menu/save systems.

| ID | Scope | Exclusive writes |
|---|---|---|
| P1-UI | Locate native Mii Fighter editor resources and extension candidates | `research/P1-UI.md`, `evidence/P1-UI/`, `scratch/2026-10-04_P1-UI/` |
| P1-ID | Locate saved-fighter identity and editor-to-match selection evidence | `research/P1-ID.md`, `evidence/P1-ID/`, `scratch/2026-10-04_P1-ID/` |
| P1-CATALOG | Inventory Gunner move slots and bounded stat candidates | `research/P1-CATALOG.md`, `evidence/P1-CATALOG/`, `scratch/2026-10-04_P1-CATALOG/` |

Workers may extract a small number of needed original files into separate workspace
`gamedata/mii_customizer/<task>/` folders using existing extraction tooling.
They may not write any other files or create new shared tools in this phase.
Exception for user-authorized rolling follow-ups on 2026-10-04: P1-UI-DECODE may create
`tools/lua53-inspect/` as specified in its prompt; P1-CATALOG-AUDIT may correct its completed
P1-CATALOG report. Both use new exclusive evidence/scratch paths. P1-ID remains independent.
Additional independent follow-ups: P1-UI-GLOBALS reads at most five Lua modules to locate
assignments; P1-LAYOUT inspects two layout archives and attempts an unchanged round trip
only with existing suitable tools. Exclusive paths and stopping limits are in their prompts.
After identity/globals reports: P1-LUA-WRITE owns lua53-inspect for checked encoding;
P1-ID-REVIEW is one premium expert audit/trace with separate report/evidence paths.
P1-LAYOUT continues. P1-DATASET now gives the third Alpha worker an independent catalogue
generator task. Limit: three Alpha workers concurrently plus the focused premium identity audit.
The dataset is provisional input data and does not choose identity/persistence/native UI contracts.
Read workspace kb and the existing mod rules/index/status before consulting its data.

Stop after the requested bounded inventory. No exhaustive binary decompilation, game launches,
dependency installation, network asset downloads or native-save changes. If an input/tool is
unavailable, record the exact limitation and finish PARTIAL/BLOCKED with a targeted next task.
Short primary-source lookups are acceptable; cite URL/commit and distinguish them from local data.

## Review gate

Coordinator reads all three reports, checks cited local paths and representative evidence,
resolves contradictions, and sets the next phase. A named candidate is not a validated hook.
Review stable identity vs Mii appearance identity, native menu edit vs replacement UI, slot list,
per-object stats, relevant preview path, and owned-resource constraints before architecture.

Premium escalation: only a specific unresolved boundary with inputs and deliverables, for example
tracing one candidate identifier into the Gunner initialization path. Do not request a whole
customization implementation or broad independent rereview from both premium models.

Console gate: none in this phase. If offline discovery cannot distinguish candidates, prepare
a small diagnostic package in a later phase before spending the user's test time.
