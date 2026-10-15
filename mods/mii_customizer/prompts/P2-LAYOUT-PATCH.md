# P2-LAYOUT-PATCH - first controlled layout modification

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md. Work only on the task below. No agents,
commits, branches, emulator, SD access, framework changes or edits to other workers'
files. Before reading old-mod material read its rules, project status and relevant
handbook pages. Inputs remain read-only. Keep game-derived files in your assigned
workspace-relative gamedata/mii_customizer/<task>/ folder, never source/evidence.
Report exact inputs/hashes, commands, observed checks, failures and limits. B is
offline observation, C pinned source, D hypothesis; no runtime behavior claims.
Coordinator owns STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report
and chat with task ID, DONE/PARTIAL/BLOCKED, changed files and next experiment.
Paths below are mod-relative unless marked workspace-relative.

One goal: prepare a reproducible same-length layout-only diagnostic, so a later
coordinator package can establish whether the game's editor loads our changed asset.
This does not request a console test and is not the customization UI implementation.
P2-UI-FLOW still owns Lua analysis; P2-STAT-API owns runtime API inspection.

Read research/P2-LAYOUT-STRUCTURE.md and research/P2-SARC-WRITE.md. Use
existing tools/bflyt-inspect/ and tools/sarc-layout/ read-only; do not change either.
Inputs: workspace-relative gamedata/mii_customizer/P1-UI/ui/layout/menu/
make_mii_special/make_mii_special/layout.arc, and its owning BFLYT already extracted
under gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_special/blyt/.

Create tools/layout-diagnostic/ with README and a small builder that independently
extracts/validates the pinned BFLYT from the archive, locates exactly one prt1 named
set_special_item_00, and changes ONLY its two scale floats to 75% of their original
values. Verify the offsets with the inspector and actual local fields first. Unknown
or ambiguous location, non-finite scale, zero/negative scale, unexpected input hash
or any unsupported structure must cause refusal; never guess an offset. The proposed
visible marker is a smaller first special-selection row; its visibility is unverified
because animations may overwrite scale. Do not alter row names/counts, position,
selector membership, child references, animations, text keys, Lua or native behavior.

Emit original control and changed archive ONLY into workspace-relative
gamedata/mii_customizer/P2-LAYOUT-PATCH/. Feed the modified member through the
existing same-length archive tool. Verify unchanged member count/metadata/offsets,
exactly one member changed, and ALL byte differences lie in the two selected float
fields. Reparse original/modified layouts, compare all other parsed fields, and
check input originals unchanged. Make generation deterministic and add a meaningful
negative control with an unexpected name or hash. Do not mutate supplied input files.

Report hashes, precise changed field offsets/values, original vs changed member
manifests, and concise future manual checks: open special editor, observe marker,
check selecting each direction and back/confirm still operates, remove delta to
restore baseline. Do not claim the marker works, prepare an installation directory,
package game assets into builds, mark READY, or ask the user to test. Coordinator
will decide whether to include it alongside useful diagnostics after Lua flow review.
If row scale cannot be located unambiguously, stop PARTIAL with evidence; no alternate
hack. Stop after one archive and one two-float diagnostic.

Exclusive writes: tools/layout-diagnostic/, research/P2-LAYOUT-PATCH.md,
evidence/P2-LAYOUT-PATCH/, scratch/2026-10-04_P2-LAYOUT-PATCH/,
workspace-relative gamedata/mii_customizer/P2-LAYOUT-PATCH/.
