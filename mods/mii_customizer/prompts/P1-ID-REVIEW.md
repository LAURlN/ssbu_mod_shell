# P1-ID-REVIEW - expert audit of identity candidate and one battle link

Model: Claude Opus 5.5. One focused premium task; preserve quota. Follow root AGENTS.md,
kb/INDEX.md, this mod's AGENTS.md and STATUS.md. Read research/P1-ID.md and its
evidence/P1-ID/post_fighter_trace.txt. Before old-project reads, follow its rules/index/status.
P1-LAYOUT is active; P1-LUA-WRITE is independent. Neither owns native identity analysis.

Goal: adjudicate the saved-fighter ID candidate and, if sound, trace ONE missing hop
toward a per-player/per-battle-object association. No save editor or full architecture.

First audit these specific issues against original instructions, not the prose:
- FNV-1a is not CRC32/Hash40. 0x811c9dc5 suggests an FNV basis but is insufficient
  to identify the algorithm. A reported multiplier 0x89 is not the standard 32-bit
  FNV prime. Report the actual calculation only if its instruction sequence is clear.
- A nontrivial rational such as 14/27 cannot equal an integer divided by 2^64 exactly.
  Packed vector-size/division idioms need full instruction/data-flow interpretation;
  do not derive capacity by multiplying a real-valued ratio. Capacity is out of scope.
- An adrp/add string xref and a nearby vtable-related store are not enough to prove a
  handler address/calling convention. Verify registration indirections, argument flow
  and vector bounds/index adjustment for post_fighter before accepting field offsets.
- Record load/global resource-list merge does not prove editor-to-battle handoff.
  Separate appearance/costume resource indices from special selections and saved identity.

Then, only if the candidate survives, follow the verified selected-record ID/state
through one downstream call path toward StateSetupMiiFighter or per-player setup.
Do not scan every matching immediate and assume a common object. Prefer call chains
with demonstrated object provenance. Pin main hash once and give instruction windows
with relative offsets and exact argument provenance. No arbitrary live-pointer reading.

Report the smallest proven association (or precise missing hop), whether there is enough
evidence for a diagnostic implementation, and exactly what a later console test would
settle. Do not require stability across deletion to use an ID: that is a lifecycle
question to solve explicitly, not a prerequisite to investigate read-side association.
No native saves, save dumps, SD/emulator access, framework patches, commits or installations.

Exclusive writes: research/P1-ID-REVIEW.md, evidence/P1-ID-REVIEW/ and
scratch/2026-10-04_P1-ID-REVIEW/ under this mod. Existing inputs/scripts read-only.
Do not edit P1-ID.md yet: provide exact corrections for coordinator integration.
Maximum two candidate downstream paths after the audit; stop if both fail, preserving
disassembly/errors and an exact next step. No full main decompilation or capacity research.
No subagents. Concise report, no repeated narration. End report/chat
P1-ID-REVIEW: DONE/PARTIAL/BLOCKED with checks, corrections, new proven link and changed files.
