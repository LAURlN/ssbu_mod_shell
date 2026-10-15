# P2-UI-FLOW - trace editor selection and skill calls

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

One goal: establish exact Lua-side data flow for one existing special selector,
and identify the smallest extension point for a future Gunner customization entry.
No implementation or native binary reverse engineering in this task.

Read research/P1-UI-DECODE.md, research/P1-LUA-WRITE.md, research/P1-ID-REVIEW.md,
and tools/lua53-inspect/README.md. Use the inspector read-only on the three existing
chunks in workspace-relative gamedata/mii_customizer/P1-UI/ui/:
script/menu/chara_make/make_mii_edit_actor.lc,
script/menu/chara_make/make_mii_special_actor.lc,
script_patch/chara_make/make_mii_edit_actor.lc.
Do not edit the inspector or any game chunks. The other workers own archive/layout
handling. Do not chase injected global definitions in more modules.

Trace register values and branches around selector setup, selected_item access,
get_skill_id/set_skill_id invocations, class checks, confirm/back transitions and
preview/try entry. Focus on one special direction; compare corresponding paths in
base vs patched editor only when needed. Limit detailed analysis to eight relevant
prototypes and list any untraced edge. Distinguish UI row index, skill direction,
option number, class and saved-record ID; never equate them by numeric coincidence.

Provide a compact call-flow table with chunk/prototype/PC ranges, arguments whose
provenance is established, return usage and unresolved native behavior. Offer
pseudocode only where instructions support it; names alone are not evidence.
Identify a proposed entry point and list the exact missing capability for adding
one selector/stat screen: layout, Lua instruction edit/compiler, native binding or
persistence. The current tool rewrites string constants only, so do not assume it
can inject functions. Say whether a safe visible diagnostic exists without breaking
part names or printf formats; a negative answer is acceptable with evidence.

No more broad string searches, production patch, config format or save design.
Stop at this call-flow plus one concrete next implementation proposal.

Exclusive writes: research/P2-UI-FLOW.md, evidence/P2-UI-FLOW/,
scratch/2026-10-04_P2-UI-FLOW/,
workspace-relative gamedata/mii_customizer/P2-UI-FLOW/.
