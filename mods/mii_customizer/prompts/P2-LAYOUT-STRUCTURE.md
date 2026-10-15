# P2-LAYOUT-STRUCTURE - decode selector and part sections

Follow workspace AGENTS.md, kb/INDEX.md, mods/mii_customizer/AGENTS.md and STATUS.md.
Paths below are relative to this mod unless prefixed workspace-relative. Read
research/COORDINATOR-2026-10-04.md. Work on only this assigned task; no subagents,
commits, emulator, SD installs, framework edits or changes to other workers' files.
Inputs are read-only; derived game files go only in your workspace-relative
gamedata/mii_customizer/<TASK>/ folder. Do not copy game content into source.
Read old-mod rules/status/relevant handbook before referencing its files. Reports
must distinguish verified offline B, pinned source C and unverified interpretation D;
no runtime claims. Record input hashes, commands, actual checks, failures and limits.
Finish with DONE/PARTIAL/BLOCKED and changed files. Coordinator owns shared status.

One goal: produce a small read-only BFLYT inspector sufficient to describe the
existing Mii editor rows and selector groups. No row addition or layout mutation yet.

Read research/P1-LAYOUT.md (including coordinator corrections). Two inputs already
exist under workspace-relative gamedata/mii_customizer/P1-LAYOUT/unpacked/:
make_mii_edit/blyt/make_mii_edit.bflyt and
make_mii_special/blyt/make_mii_special.bflyt.

Coordinator independently walked sections: LE u16 header size at +6=0x14,
LE u16 section count at +0x10=58/43, each section has 4-byte tag and LE u32
size at +4; sequential traversal consumes 21004/10408 bytes exactly. +8 bytes
00000009 are not section count. Do not search for a separate block table.

Implement tools/bflyt-inspect/ with README and meaningful smoke checks. Parse header,
sections and enough grp1/prt1 structure to give selector_0 member names/count and
row-part references with exact offsets. Determine hierarchy via pas1/pae1 etc if
present; preserve unknown fields in the description. Cross-check all group names
against actual pane names; report unresolved references without assuming corruption.
Compare edit's six rows and special's four, including referenced child layouts.
Inspect at most two additional child BFLYT members if essential to understand rows.
Use primary format source if needed and pin it; no broad tool installs.

Produce a machine-readable section/group/part inventory and a short report answering
which counts/references an added row would need to update. Do not claim new animations
are unnecessary from absence of row-name strings. Do not try adding a row, rebuild
an archive, interpret native bindings or mutate Lua. Stop after these two owners and
at most two child files; unresolved semantics stay explicit.

Exclusive writes: tools/bflyt-inspect/, research/P2-LAYOUT-STRUCTURE.md,
evidence/P2-LAYOUT-STRUCTURE/, scratch/2026-10-04_P2-LAYOUT-STRUCTURE/,
workspace-relative gamedata/mii_customizer/P2-LAYOUT-STRUCTURE/.
