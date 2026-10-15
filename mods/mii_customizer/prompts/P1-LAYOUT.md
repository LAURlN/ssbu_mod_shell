# P1-LAYOUT - establish a bounded editor layout edit path

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/P1-UI.md and research/COORDINATOR-2026-10-04.md.
Before old-mod reads, read its AGENTS.md, relevant project status and handbook index.
You are the finished catalogue worker's next task. P1-UI-GLOBALS owns Lua modules;
P1-ID owns identity. Do not overlap either. No production menu implementation yet.

One goal: determine how to inspect and rebuild the existing Mii editor layout archive
so the next implementation can add a field without corrupting its container.

Inputs already exist read-only under workspace gamedata/mii_customizer/P1-UI/:
ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc and
ui/layout/menu/make_mii_special/make_mii_special/layout.arc.

1. Identify container magic/endianness and enumerate members using an existing
   workspace tool if available. Read tools/REGISTRY.md first; inspect tool installs
   only when a workspace note explicitly points to them. Don't assume SARC or BFLYT.
2. Identify the actual layouts/animations/info files that reference set_item_00..05
   or set_special_item_00..03. Record exact member paths and structural evidence;
   ASCII name presence alone does not prove hierarchy or button behavior.
3. Establish a supported rebuild route. With an existing suitable tool, unpack into
   task-owned gamedata/mii_customizer/P1-LAYOUT/ and perform an UNMODIFIED round trip.
   Compare original vs repacked member hashes, membership and archive metadata.
   Container byte equality is useful when supported; otherwise explain differences.
   Do not modify original extracted inputs or produce an installation candidate.
4. If a tool is absent, inspect up to two primary-source tool repos/docs and recommend
   one exact pinned candidate, its format support and local dependency requirements.
   No downloads/builds/installs in this task. Stop with a precise tooling request
   instead of writing a general-purpose layout editor.

Exclusive writes under this mod: research/P1-LAYOUT.md, evidence/P1-LAYOUT/,
scratch/2026-10-04_P1-LAYOUT/. Unpacked/repacked game data stays in the task-owned
workspace gamedata/mii_customizer/P1-LAYOUT/ directory, never source/evidence/tools.
No shared tools, Lua edits, native binary RE, saves, SD access, emulator, commits or
other worker outputs. Record hashes, commands, failures, tiers, and verified/unverified
claims. Finish with a concrete minimal next layout task and prerequisite tool if needed.
Stop after the two archives and one round trip or an evidenced tooling limitation.
End saved report/chat P1-LAYOUT: DONE/PARTIAL/BLOCKED and changed files.
