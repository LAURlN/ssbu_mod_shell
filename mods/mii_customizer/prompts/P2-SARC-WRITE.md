# P2-SARC-WRITE - conservative archive member replacement

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

One goal: promote the useful P1-LAYOUT scratch parsing into a bounded stdlib
SARC replacement tool with an unchanged control and one same-length mutation.
This is coordinator authorization to create this mod-local tool; no extra approval
or external crate install is required. Read research/P1-LAYOUT.md and its corrections.

Inputs: original two layout.arc files under workspace-relative
gamedata/mii_customizer/P1-UI/ui/layout/menu/{make_mii_edit/make_mii_edit,
make_mii_special/make_mii_special}/layout.arc. Inspect existing P1-LAYOUT scripts
rather than reimplementing blind. Build tools/sarc-layout/ with README.

Implement list/manifest, safe named extraction, byte-exact unchanged reconstruction,
and replace ONE EXISTING named member. Initial support is same-length payloads only;
refuse growth/shrink, new members, duplicate names, traversal paths, overlapping or
out-of-bounds ranges and unsupported compression/BOM explicitly. Preserve archive
metadata, ordering, original offsets, gap bytes and every other member verbatim.
Never overwrite the input. No generic repack/alignment guess is needed now.

Validate both original archives and reconstruct each to exact original hash.
For mutation use a synthetic archive, not a guessed game change: replace a known
member by a same-length different payload, independently reparse and confirm exactly
that member changed, metadata/other members/gaps did not. Exercise meaningful
refusals for wrong size, missing member and malformed ranges/path escape. Compare
at least one real member manifest with the prior worker's manifest. This proves
container behavior only, not game's acceptance or absence of runtime checksums.

No BFLYT decoding/editing, Lua, native RE, install package or Rust dependencies.
Stop at the bounded tool plus controls; document how future growth support remains
separate and why four-byte repacking is not currently approved for shipping.

Exclusive writes: tools/sarc-layout/, research/P2-SARC-WRITE.md,
evidence/P2-SARC-WRITE/, scratch/2026-10-04_P2-SARC-WRITE/,
workspace-relative gamedata/mii_customizer/P2-SARC-WRITE/.
