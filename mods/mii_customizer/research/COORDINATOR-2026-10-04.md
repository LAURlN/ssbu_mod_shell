# Coordinator review - 2026-10-04

User authorizes two independent follow-ups while P1-ID continues. No premium escalation/test.
Reviewed completed P1-UI and P1-CATALOG reports and representative evidence files.

Verified B with PowerShell Get-FileHash SHA256:
- `gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc`:
  `ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d`.
- `gamedata/mii_customizer/P1-CATALOG/files/fighter/miigunner/motion/body/c00/motion_list.bin`:
  `2b7ed9b6b17a6ab39cc0e6db5121b668d2de44728ac50e9051816612c7d3f4ba`.
- `gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc`:
  `87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2`.
All match reported inputs. This does not reproduce either worker's full analysis.

Corrections made in place:
- P1-UI's absence-of-path inference did not establish editor modifiability; costume/voice
  resources are in the game's own inventory. Their functionality is not this task's scope.
- P1-CATALOG calls `attack_s3_s` a smash and claims no side tilt. Those conclusions do not
  follow from the inventory; classification is pending targeted audit.
- Weight should be assessed by knockback controls, not fall speed/floatiness.

Remaining limitations:
- UI function bodies and native targets were not decoded. Statements about loops/calls and
  patch behavior remain hypotheses even when their names occur in strings.
- Catalog timing values 334/318 are raw reader outputs, not accepted cancel-frame semantics.
  Round-trip equality only proves byte preservation, not correct field interpretation.
- AI attack tables are not by themselves authoritative for player-facing editor slots.
- Shell tool availability may differ between workers; their rg observation does not describe
  this coordinator's shell, where rg executed successfully.

Next tasks: P1-UI-DECODE resolves Lua chunk structure and selected instruction evidence;
P1-CATALOG-AUDIT verifies the actual slot/grouping and timing interpretation. Both avoid
saved identity/native binding traces so P1-ID can continue without overlap.

## Follow-up progress review

Both follow-ups now report DONE; P1-ID has no saved report yet. Coordinator reran:
- `python mods/mii_customizer/tools/lua53-inspect/check_lua53_inspect.py` with all three
  existing editor chunks: all checks passed, exit 0 (B verified).
- `python mods/mii_customizer/scratch/2026-10-04_P1-CATALOG-AUDIT/check_report_claims.py`:
  0 failing claims, exit 0 (B verified). This is a selected claim check, not verification of
  all report prose or runtime semantics.

Useful new evidence: recursive Lua parsing, dispatch call sites, patched flag reads and
field-layout correlations correcting the catalogue's 334/318 timing interpretation.
No mod runtime code, menu asset changes, persistence or installed package yet.

Do not adopt these residual report inferences as settled facts:
- Missing global assignments in three chunks does not prove which native/module source defines them.
- UiScriptPlayer.invoke calls alone do not establish the implementation/registration of native targets.
- Catalogue calls get-up entries five while its own check asserts six down_attack_* entries;
  movement recovery states must not be classified as attacks just by distinct motion entries.
- The named move flag does not prove 'smashes move the fighter; tilts do not' as a general rule.

Next architectural blockers remain per-saved-fighter identity, native extension/bridge and
per-instance runtime stat reads. No console request or additional worker dispatch in this review.

## Identity/globals review and next dispatch

P1-ID and P1-UI-GLOBALS now finished PARTIAL. P1-LAYOUT has no report yet.
Neither new report's analysis has been independently reproduced by the coordinator.
The global report excludes three modules; its claims of immutable globals or necessarily
host-owned enum names do not follow from a negative search. Stop iterative broad searches.
P1-ID offers a native selected-record candidate but contains critical interpretation issues:
FNV vs CRC32 conflation, a reported nonstandard prime, impossible exact 14/27 equality to an
integer/2^64, ambiguous registration/handler identification and an untraced battle-object hop.
These claims are pending audit and must not enter implementation as verified facts.

Dispatch one bounded Claude Opus 5.5 audit/trace (P1-ID-REVIEW) and one Alpha offline Lua
writer task (P1-LUA-WRITE). Layout continues; original Alpha identity worker is idle.
No console request. Tool ownership for lua53-inspect is exclusive to P1-LUA-WRITE.

## Premium identity audit reviewed

User confirms Claude finished and all three Alpha workers remain active. Reviewed
P1-ID-REVIEW; corrected P1-ID in place and marked its annotated native trace superseded.
The former post_fighter match-handoff hypothesis was wrong; its u16 buffer is name text.
The audit supplies a stronger selection-ID -> per-player record-content association,
but no match reader. Native claims are worker offline B; coordinator has not reproduced
that disassembly. Reproduced arithmetic with Python: both inverse products modulo
2^64 equal 1, strides are 0x1B0 and 0x64340 (verified B, exit 0).

No changes to active workers' files. No premium dispatch or console request. Await
layout, Lua writer and catalogue reports before selecting integration/diagnostic work.

## All Alpha outputs reviewed; integration prerequisites scoped

P1-LUA-WRITE and P1-DATASET checks rerun, exit 0 (all Lua checks pass, catalogue
42/42). Re-ran unchanged archive reconstruction via imported roundtrip function
without writing its output report: both containers equal originals. This copies
metadata and rebuilds unchanged payload; it is not a general independent encoder.
Read P1-LAYOUT and corrected unsupported checksum/animation/alignment conclusions.
Coordinator Python sequential section walk measured header size +6=0x14 and section
count u16 +0x10=58/43; per-section tag and u32 size consume both files exactly,
21004/10408 bytes. Earlier separate table search is retired. +8 bytes 00000009 are
not block count; version meaning not independently verified. These are verified B.

Prepared three independent P2 prompts: BFLYT payload inspector, conservative SARC
same-length replacement tool and Lua selector call flow. No worker dispatch, premium
quota, native behavior edits, install package or console request. Completed report
corrections preserve original evidence as historical artifacts.

## P2 layout/archive review; two rolling follow-ups

User reports two workers finished. Reports present for P2-LAYOUT-STRUCTURE and
P2-SARC-WRITE only; P2-UI-FLOW is inferred still active. Coordinator reran
check_bflyt_inspect.py (71/71, exit 0) and check_sarc_layout.py (87/87, exit 0),
verified offline B. These are worker-authored checks, not runtime evidence.
Layout gives selector membership and row/child structure; archive tool supports
same-length replacement while preserving metadata/placement. Corrected report's
128/124/124 spacing, omitted section-count update, and claim coordinator had used
exclusive framing (the original coordinator script already used offset+size).
Corrected unsupported requirement that future growth must use a separate tool;
a reviewed explicit mode may also be suitable. No growth work now.

Prepared P2-LAYOUT-PATCH (one two-float cosmetic diagnostic, offline only) and
P2-STAT-API (two-parameter supported-API assessment) on exclusive paths. Both avoid
active Lua-flow ownership. No dispatch, premium use, user test or package. New
customization behavior still depends on Lua/native route and identity evidence.

## New coordinator: P2-UI-FLOW and P2-LAYOUT-PATCH reviewed

Took over from `HANDOFF.md`. Read `evidence/P2-UI-FLOW/dis_special_actor.txt` for
`main.p4`, `p10`, `p11`, `p13`, `p14` and the matching constant tables (verified B,
bytecode only).

Corrected in place in P2-UI-FLOW:
- Row 32 / section 5 / section 8: the sub-window write-back is `cache[command_id + 1] = d`.
  `main.p13` pc15 loads `command_id`, pc16 adds `K[7] = 1`, pc17 stores `R[1]` (the decided
  button id). The report's `command_id + 1 + d` and "flattened slot+option" were wrong; `d`
  is not an operand of the `ADD`.
- Row 21: `main.p4` pc13 is `ADD A=5 B=2 C=K[4]=1` after R[2] was overwritten with the
  cached value, so the help number shows option + 1, not row + 1.

What follows from the corrected reading: the cached value is used by Lua as a 0-based
option index (`main.p11` pc4-15: `list_parts[skill_id + 1]`, `select_button(skill_id)`), so
`get_skill_id` must return something valid in that role. `main.p14` pc22-33 is a plain
frame loop (`state:update()`, `coroutine.yield()`, repeat until `state:get() == up[5]`), and
the `set_skill_id` loop at pc34-44 follows it unconditionally. In the bytecode there is no
path that leaves the screen without that write. This narrows the report's edges 1 and 4 but
does not show what the native handlers store or when a save happens.

Not adopted: the report's reading that `IS_SKILL_EDITABLE` is "exactly the hook a mod would
want to set" (purpose is D, owner unknown), and its suggestion that the title-string probe
could be spent as a console gate now.

P2-LAYOUT-PATCH: reran `check_layout_diagnostic.py` (80/80, exit 0). Independent Python
byte comparison of input and patched archive: equal length 723436, differing offsets exactly
0x14e42 and 0x14e46, floats at 0x14e40 read (1.0, 1.0) and (0.75, 0.75), control identical
to input, block at archive 0x14dfc is `prt1` size 772 named `set_special_item_00` (verified
B). Corrected in place: a reference to a nonexistent `P2-LAYOUT.md`, and manual step 1,
which named an `atmosphere/contents/...` path and a file backup that nothing in the
workspace supports. Install location is a coordinator decision for a later package. That
payload +60/+64 is the rendered scale remains an inference; no format source is pinned.

P2-STAT-API has no report, evidence or scratch folder on disk; launch unconfirmed.

Prepared P2-SKILL-NATIVE (locate registration sites and handler addresses for six bridge
names using the delegate pattern verified in P1-ID-REVIEW 2.3; locating only, no handler
interpretation) and P2-LUA-EDIT (fix the `xref` iAsBx defect, add append-constant,
patch-instruction and insert-instruction with jump relocation, proven on the synthetic
chunk). Both offline, exclusive paths, no overlap with P2-STAT-API. No dispatch, premium
use, package or console request. The handler-reading step after P2-SKILL-NATIVE is the
likely first premium question of phase 2.

## Three reports reviewed: SKILL-NATIVE, STAT-API, LUA-EDIT

Reran `check_claims.py` (174 checks, 0 failures, exit 0), `check_stat_api_sources.py`
(59/59, exit 0) and `check_lua53_inspect.py` on the three chunks (all pass, exit 0; special
actor input hash unchanged). These are worker-authored checks (verified B that they pass).

P2-SKILL-NATIVE. Coordinator disassembled 0x19dcf20..0x19dcf5c with the P1-ID-REVIEW
script (verified B): `cmp w1,#4; b.hs <assert>; add x8,x0,w1,sxtw; strb w2,[x8,#0x100]; ret`
and the same with `ldrb w0`. Read from the worker's function dump: obj allocated 0x150
bytes (0x19ddb80-0x19ddb94), `str xzr,[x19,#0x100]` at 0x19ddd24, `[x19+0xf8]` set to
0xc1ffff0000000000 (0x19ddcf4-0x19ddd0c), `str x19,[x23,#0x80]` at 0x19ddd80. `calls`
scan: 0x19ddb30 has exactly two `bl` callers, 0x1809814 and 0x1982fc0, each after a
0x88-byte allocation. The worker's closing section interprets the two handlers although the
prompt said not to; the reading is correct and is kept. Its "next question" names
`replace_skill` as a candidate writer of the array; the 40-instruction window shows pane and
label calls only, so that is D. The report's handler table was not otherwise reproduced.

Consequence: the special screen edits four bytes held in a scene object. The saved-record
field behind them and the copy-in/copy-out code are the next exact native question
(P2-SKILL-STORE, premium). D: record +0x140 (u32, unexplained in P1-ID-REVIEW 2.4) is the
obvious candidate; not adopted.

P2-STAT-API. Source assessment only; no instruction in the local image was read. Accepted:
both parameters are per-kind floats in row 82 (B); smashline's param override is keyed by
fighter kind (C). Not accepted as established: that the engine reads these two values through
`WorkModule::get_param_float`; the report says so itself. Its section 3 labels table rows
A/B/C/D, which collide with evidence tiers; read them as row labels. smash-rs offsets are
unpinned (C-weak). Follow-up P2-STAT-READS locates the hash uses in the image.

P2-LUA-EDIT. The worker wrote `evidence/P2-LUA-EDIT/` and `scratch/2026-10-04_P2-LUA-EDIT/`
at the workspace root instead of inside the mod; coordinator moved both into the mod and
removed the then-empty workspace `scratch/`. Scratch scripts may hold paths to the old
location and were not rerun. Lua 5.3.6 sources were fetched from upstream into scratch for
citation (allowed: pinned primary source). The check script writes one temp file outside the
workspace (system temp dir); to be changed when the tool is next touched. Mutators are
accepted as encoding tools; no claim about game loading.

Prepared P2-SKILL-STORE (premium), P2-UI-CONSTS and P2-STAT-READS. New prompts state that
evidence and scratch folders live inside the mod. No dispatch, package or console request.

## Three reports reviewed: SKILL-STORE, UI-CONSTS, STAT-READS

Reran `scratch/2026-10-04_P2-SKILL-STORE/check_claims.py` (88 checks, 0 failures, exit 0)
and `scratch/2026-10-04_P2-UI-CONSTS/check_claims.py` (179 checks, 0 failures, exit 0).
`evidence/P2-STAT-READS/check_stat_reads.py` scans the whole code range in Python and takes
several minutes; run in the background it finished with 450 passed, 0 failed, exit 0.

Coordinator disassembly with the P1-ID-REVIEW script (verified B):
- 0x180ba8c-0x180bab8: x9 = 0x5306cba; `ldur x10,[x9,#0x5e]` -> `[obj+0xf8]`; four
  `ldrb [x9,#k]` -> `strb [obj,#0x100+k]`. With W = 0x5306b78 this is W+0x142..+0x145 and
  W+0x1a0, as reported.
- 0x180d8cc-0x180d8f8: four `ldrb [x20,#0x142+k]; cmp #2; b.hi 0x180d71c`, as reported.
- 0x19de4a8 `mov w3,#3` and 0x19de55c `mov w3,#4` before `bl 0x33750a0`.
- 0x2db55b8-0x2db55d8: `ldr x8,[x20,#0x20]; ldr x0,[x8,#0x50]; ldr x8,[x0]; ldr x8,[x8,#0x270];
  x1 = 0x0607cd5541; mov x2,xzr; blr x8`, result in v0 copied to v8.
The rest of each report was not independently reproduced.

Accepted corrections to earlier material: P1-ID-REVIEW 2.4's "u32 at +0x140, u16 at +0x144"
is six separate bytes; the special choices are +0x142..+0x145 (noted in that report in
place). The previous coordinator note's D guess (+0x140..+0x143) was off by two.

Coordinator observations, not in the reports:
- 0x5306b8c, the base of the `IS_READ_ONLY` / `IS_SKILL_EDITABLE` loads, equals W+0x14, and
  the halfword at +0x10 from it is W+0x24. So both flags derive from the editor working
  record (arithmetic on two reported addresses; what those fields mean is D).
- P2-STAT-API noted the old mod hooks `WorkModule::get_param_float`. The engine sites found
  by P2-STAT-READS call the vtable slot directly. If the old mod's hook target is an exported
  wrapper, it would not see these calls. Unknown which it is; P2-STAT-HOOKPOINT asks.
- P2-STAT-READS's "zero direct callers" for most enclosing functions rests on a prologue
  heuristic that P2-UI-CONSTS showed to miss `str d8,[sp,#-N]!` prologues. Treat function
  starts in that report as candidates.

Not adopted: P2-UI-CONSTS's suggestion that the two IS_* flags may be "a mod-settable hook";
P2-SKILL-STORE's D reading that scene 0x1808980 is the Mii Fighter editor is plausible and
unverified.

Direction (D, coordinator): the vanilla field holds 0..2 per special slot and is guarded on
commit, so custom choices belong in mod-owned storage keyed by the u32 saved-fighter ID.
The remaining native unknown that gates a vertical slice is the per-player ID at match setup
(P2-MATCH-READER, premium). In parallel: the real param hook point (P2-STAT-HOOKPOINT) and a
build-only plugin skeleton (P2-PLUGIN-SCAFFOLD). The first console request, if these return
as hoped, would be one log-only diagnostic package rather than separate cosmetic probes.

## Three reports reviewed: MATCH-READER, STAT-HOOKPOINT, PLUGIN-SCAFFOLD

Reran `scratch/2026-10-04_P2-MATCH-READER/check_claims.py` (95 checks, 0 failures) and
`scratch/2026-10-04_P2-PLUGIN-SCAFFOLD/check_scaffold.py` (26 passed, 0 failed); staged NRO
sha256 `3ee95be2470d...` equals the manifest. The plugin build itself was not repeated by the
coordinator. `evidence/P2-STAT-HOOKPOINT/check_hookpoint.py` rerun: 366 passed, 0 failed, exit 0.

Coordinator disassembly (verified B):
- 0x1791a30-0x1791a5c: `ldr w8,[x20,#0x14]` -> stack, `madd x8,x23,0x240,x19`, stores to
  `[x8+0xe50..0xe68]`; the qword holding sel+0x10/sel+0x14 goes to `[x8+0xe58]`. Note the u32
  ID is the HIGH half of that qword only if sel+0x14 was placed at sp+0xc; the report gives
  `str w8,[sp,#8]`, so the ID is the low u32 at +0xe58. The report's player-0 address
  0x53085b8 = T+0xe58 is consistent with that.
- 0x4e5390-0x4e53fc: alternating thunks. +0x248 -> dispatch +0x250; +0x250 (0x4e53a0) ->
  `[x0+0x38]` slot +0x20; +0x258 -> +0x260; +0x260 (0x4e53c0) -> `[x0+0x38]` slot +0x28;
  +0x268 (0x4e53d0) -> +0x270; +0x270 (0x4e53e0) -> `[x0+0x38]` slot +0x30; 0x4e53f0 ->
  `[x0+0x38]` slot +0x38. None touches x1/x2.
- 0x688508-0x688584: 0x98-byte object, `stp x8(=0x4f89490), x19, [x20]`, `str x20,[x19,#0x50]`.

Review of P2-STAT-HOOKPOINT's reasoning. The worker concluded that 0x4e53d0/0x4e53e0 "cannot
consume a hash argument" because they read no argument registers. That is the wrong reading
of a tail-call thunk: x1 and x2 are left untouched and arrive unchanged in the function the
thunk branches to, with x0 rebased to `[x0+0x38]`. So the chain is consistent with: engine
site -> `[[parent+0x50]]+0x270` = 0x4e53e0 -> param object slot +0x30 (hash, hash). And the
exported wrapper 0x208de50 -> +0x268 = 0x4e53d0 -> +0x270 = 0x4e53e0. On these instructions
a hook on the wrapper (what the old mod patches) sees only callers of the wrapper, while a
hook at 0x4e53e0 sees both. This matches the +0x268 "_impl" / +0x270 declaration pair in the
pinned smash-rs binding (C) in slot numbers, though that binding's doc comment describes the
call direction the other way round. Naming the parent "module accessor" and the object
"WorkModule" remains D until a runtime log ties a parent pointer to a fighter. The report's
13-row candidate table is not needed further. Its sections 2.4-2.5 are left as written.
Coordinator recollection, unpinned and therefore D: community param-hook plugins hook raw
offsets in this same 0x4e53xx thunk block; not checked against a pinned source.

P2-MATCH-READER: accepted as PARTIAL. The ID-next-to-specials result gives a static read
candidate; timing and the meaning of `p` need the console. The offline alternative it names
(0x3311190, tail of 0x2340850) is not pursued now.

P2-PLUGIN-SCAFFOLD: accepted. `build-plugin.sh` sits at the mod root, outside the prompt's
listed write paths but inside the mod; kept. kb/reference/cargo-skyline.md updated in place
with the cold-build result, marked as not re-run by the coordinator.

Housekeeping: P2-STAT-HOOKPOINT scripts wrote ten JSON files (7.7 MB) to the workspace root;
moved to `scratch/2026-10-04_P2-STAT-HOOKPOINT/out_from_workspace_root/`.

Decision: the open questions are now runtime questions (ID slot validity at match start,
whether param requests reach 0x4e53e0 per fighter, offset convention, whether changed layout
and Lua files load). That justifies one console session with a log-only plugin plus two
toggleable file probes. P3-DIAG-PLUGIN (premium, because a faulty hook costs a console
session) and P3-ARC-PROBES (Alpha) prepare it. The Lua probe is redefined to swap in a
message key the chunk already uses, instead of the earlier unknown-key string.

## Four reports reviewed; gate-1 package assembled

Reran (all exit 0): `scratch/2026-10-04_P3-DIAG-PLUGIN/step0.py` 36/36 and `check_build.py`
37/37; `builds/0.1.0-arc-probes/check_probes.py`; `scratch/2026-10-04_P3-CUSTOMIZE-SITES/
check_report_claims.py` (all claims reproduced); `scratch/2026-10-04_P3-SPECIAL-VARIANTS/
check_special_variants.py` 89/89. NRO sha256 `ae49c1c84da3...` equals its manifest. Not
repeated: the plugin build and the host unit tests.

P3-DIAG-PLUGIN, coordinator read of `plugin/src/lib.rs` (source review, not runtime evidence):
the three hooks call the original through the trampoline with x0-x7/d0-d7 and return its
result; logging happens after the original returns; non-matching param calls take two
compares and a tail call; reads are limited to `[x0+8]` and the two static tables; the entry
stubs keep the stack 16-aligned and pass the return address as a stack argument. Assumptions
that stay open: the float return type of 0x4e53e0 (supported offline by the caller at
0x2db55dc using v0 after the call), that none of the three originals takes stack arguments
or x8, and that the card's Skyline runtime patches 4 words at an 8-aligned site like the
lab copy. The worker's two deviations (bounded extra L1/L2 lines, L2 written after return)
are accepted. `scratch/2026-10-04_P2-PLUGIN-SCAFFOLD/check_scaffold.py` no longer matches the
crate (crate is 0.1.0); the 0.0.1 NRO is unchanged.

P3-ARC-PROBES: the Lua probe's `info.toml` had an unterminated `description` string (Python
`tomllib` rejected it; the worker's check compared hashes only). Coordinator added the
closing quote and regenerated the probe manifest with the worker's `check_probes.py --write`;
payload hashes unchanged. Coordinator extracted `ui/message/msg_menu.msbt` (sha256
`4b4f3d236400...`, to `gamedata/mii_customizer/COORD-msg/`) and parsed LBL1/TXT2: label
`mnu_mmiif_setup_sp_move_title` -> "Select Special Moves", `..._width` -> "Side Special"
(verified B for this file; per-language files not read). So the Lua probe has a visible
difference if the chunk loads and `set_sub_title` resolves message keys.

P3-CUSTOMIZE-SITES: only two `[x+0x50]` slot-0x278 sites, the exported wrapper and
0x20921d0, which sits next to the string `set_customize_no` in a registration-shaped call
(D: script binding). No engine-side caller found by this shape; the match-time application
of special choices remains untraced. Also noted: the relocation array holds 306168 RELATIVE
records, not 306169.

P3-SPECIAL-VARIANTS: accepted as inventory. Four previously unnamed motion kinds were
resolved by hash match. The 4-row-per-slot param lists are the only variant-shaped tables.

Gate 1. Assembled `builds/0.1.0-gate1/` from the two reviewed builds (byte-identical copies,
`check_gate1.py`: 5 files, 0 problems) and wrote the test plan in `CURRENT_INSTALL.md`.
Two boots: plugin only, then the two file probes together (their visible signs are
independent: sub-title text and first-row size). The runtime questions it decides are listed
there. No further worker tasks are prepared; they depend on the result.

## Gate 1 results and phase 4 direction

Installed step 1 and step 2 on the card at the user's request (record in CURRENT_INSTALL.md).
Before installing, compared the card's Skyline runtime (sha256 `d3630815ee02...`) with the lab
copy the plugin analysis used: `A64HookFunction` / `A64HookFunctionV` differ only in relative
call targets and one data displacement (verified B, coordinator script run inline).

Test 1 and test 2 passed; details and the reading of the log are in
`evidence/2026-10-04_gate1/RESULT.md` and `RESULT_test2.md` (tier A). Points that change earlier
notes: the "editor range" 0x19d0950..0x19dc304 of P1-ID-REVIEW is also busy outside the Mii
editor (823 loader calls before the first Gunner match); the hooked store 0x179e440 is not the
writer that puts the IDs into the slots before a match; scene 0x1808980 is the Mii editor
(loader calls with the opened Mii's ID from its functions).

Direction. Persistence is mod-owned and keyed by the u32 saved-fighter ID; retrieval is a
static read by player index, guarded by fighter kind; application of stats is at 0x4e53e0.
What is missing for that is the parent -> player mapping, which P4-OVERRIDE-SLICE must get
from pinned bindings. For the editor UI the coordinator's working idea (D) is: compile editor
Lua from source with a format-matching luac, and use the two skill handlers as the Lua <->
plugin channel with rows the game never uses. P4-LUAC and P4-BRIDGE-FACTS gather what that
needs; no design is fixed until they return. Loadout file format v1 is defined in the
P4-OVERRIDE-SLICE prompt and is the first shared contract of this project.

## 2026-10-05: phase 4 reports reviewed; gate 2 prepared

Reran (exit 0): `scratch/2026-10-04_P4-OVERRIDE-SLICE/step0.py` 35/35, `check_build.py`
69/69, `run_host_test.sh` 25/25; `tools/luac53-game/check_luac53_game.py` 9 checks, 0 failed;
`scratch/2026-10-04_P4-BRIDGE-FACTS/check_p4.py` all passed. NRO sha256 `4477dc9acdbe...` and
example file `4c2ae058267e...` equal the report. Not rerun: the plugin build, the mutation
control, `evidence/P4-STAT-SITES/check_stat_sites.py` (whole-image scan).

P4-OVERRIDE-SLICE. Read the stubs and `resolve` in `plugin/src/lib.rs`. Accepted, including
the deviation: object id from the struct field the binding declares at accessor+8, validated by
`sv_battle_object::module_accessor(id) == parent` before any other use. The strict alternative
(`get_id_from_entry_id`) dereferences an unchecked singleton and can abort; not wanted.
Loadout-file choices in its section 2.1 are accepted as part of contract v1 (whole file refused
above 16 KiB, BOM rejected, CRLF accepted, own number parser). `FIGHTER_KIND_MIIGUNNER = 0x4A`
is binding-only until the console log shows `kind=74` for a Gunner.

P4-LUAC. lua.org publishes no checksum file; the worker instead compared every source file
with the GitHub tag v5.3.6. Accepted. `tools/luac53-game/bin/` holds built executables inside
the mod tree; kept, they are reproducible from `build.sh`.

P4-BRIDGE-FACTS. Accepted. Relevant for a channel: integers pass raw; the return value is
sign-extended w0; a hook on the two handlers would overwrite `cmp; b.hs; add; strb/ldrb`, of
which `b.hs` is PC-relative, so a replacement should implement the five instructions itself and
not rely on a relocated trampoline; the cold path ends in a non-returning import.

P4-STAT-SITES. Accepted as counts. Every float candidate has +0x270 sites, but also direct
`bl` and no-call sites, so "all uses go through the hooked getter" is not shown for any stat.

Card not mounted at review time, so gate 2 is prepared but not installed. P5 prompts written
for the UI track; they do not depend on gate 2.

## 2026-10-05: gate 2 result; UI direction from the user

Gate 2 log read by the coordinator; result in `evidence/2026-10-05_gate2/RESULT.md` (tier A).
The run was not the planned sequence (no non-Mii control, no explicit port swap), but match 4
had Gunner A on both ports and both were overridden, which covers "follows the ID, not the
port". New fact from the log-only hook: the special variant per slot is applied through slot
+0x278 with (option, slot) from one location near 0x60e9d0; that is the natural place to look
when special-move selection beyond the vanilla three is attempted.

The user asked for character stat presets selectable in the Mii maker, a headgear-style list as
the UI basis, and an entry in the Mii maker menu (single switch button acceptable, real
sub-menus preferred). The earlier coordinator idea of extra pages on the special-move screen is
dropped. Preset data must come from the user's own files at build time (rule: no game-derived
data in the mod tree), hence a generator tool and a preset file on the card. Field list starts
with the ten float candidates without `scale`; extending it is a coordinator decision after
P6-PRESET-DATA shows the other float fields and their ranges. Integer stats (jump count) need
the +0x250 getter and are not in this step.

P5 tasks appear to be running (their gamedata folders and one report exist); they are reviewed
when the user reports them done. P5-LUA-SOURCE targets the special-move script; with the new
direction its main value is proving that the local compiler reproduces game bytecode.

## 2026-10-05: P5 reports reviewed; P7 prepared

Read the three reports; read the staged `msg_menu.xmsbt`. Coordinator checks: none rerun this
round (`tools/lua-src/build_check.py` must be started from the workspace root; it reports
"not byte-identical" by design because of the one flag byte). Accepted on the reports' own
evidence, to be confirmed when these parts are next used.

P5-LUA-SOURCE: the single differing byte is `is_vararg` of the main prototype (2 in the game
file, 1 from stock 5.3.6). D: the game's chunks were dumped by an earlier 5.3.x that stored 2
for the main chunk. For chunks we compile ourselves, set that byte to 2 after compiling so the
file matches the game's convention; whether the loader cares is untested.

P5-UI-API: useful vocabulary: `set_text_message(key)`, `set_text_message_args`,
`set_text_string` exists but with only 3 call sites; `is_pressed` / `is_pressing` with
`INPUT_*` values; values are not unique per name (INPUT_OK and INPUT_COMMON_BUTTON are both 6),
so they are per-screen bindings, not global button ids.

P5-MSG-PROBE: accepted. Its observation about the loader version is recorded in STATUS; the kb
note is corrected when the version is established from the card (hash/size of the NRO against
release assets needs a download of release binaries, which the rules restrict to official
releases; not done).

P7-PRESET-ENGINE defines contracts A-D (preset file, loadout v2, who, which requests). It runs
in parallel with P6-PRESET-DATA because the preset format is fixed in both prompts. The UI
bridge and runtime saving are deliberately left out until P6-HAT-UI and P6-EDIT-MENU return.
On model choice: the user asked whether a cheaper model could take this task. The coordinator
has no evidence about that model's reliability on native hook code; the task stays specified
for the two premium models, because an error costs a console session or a crash.

## 2026-10-05: P6 reports reviewed; P8 prepared

Checks rerun by the coordinator from the workspace root: `tools/stat-presets/check_presets.py`
30/0 (twice, before and after the change below), `evidence/P6-EDIT-MENU/check_p6_edit_menu.py`
264/264, `evidence/P6-HAT-UI/check_p6_hat_ui.py` 722/0. The HAT-UI report text says 317 checks
in section 0.3 and 722 later; 722 is what runs. Reports read in full except HAT-UI section 11
tables (lines 818-980), which the check script covers.

P6-PRESET-DATA was started twice. The second worker did not rebuild; its independent
verification (`evidence/P6-PRESET-DATA/W2-REVIEW.md`) found (1) `nam_chr1_00_` is the better
display-name family (87 of 94, no line breaks), adopted as a decision, tool not yet changed;
(2) the check script left about 45 MB of regenerated game-derived files under the mod scratch
on every run. Fixed by the coordinator: temp folder is now workspace
`gamedata/mii_customizer/P6-PRESET-DATA/check-tmp/`, removed at exit; the leftover folder from
the coordinator's own first rerun was deleted. The README of the tool still names the old
scratch path in one sentence.
The report's worry that 25 517 bytes exceeds the 16 KiB limit applies to the loadout file
only; P7 contract A gives the preset file 512 KiB.

Consequences for the UI (D until the P8 tasks return): the two things the user asked for,
a headgear-style list and an entry in the edit menu, both end in native code. Three routes:
(a) a list owned by Lua, if a script can create and fill a scroller (two chunks write the
`scroller` global: tips list, options top) -> P8-LUA-LIST; (b) reuse the native headgear
list with plugin hooks on its count and row drawing -> P8-HAT-NATIVE; (c) the entry point:
where the native scene maps the decided row to a sub-screen -> P8-EDIT-DISPATCH. Fallback
that needs none of these: a selector inside the special-move screen (Lua owns its row text;
left/right through the fighter names), with the plugin reached through the skill handlers
(`set_skill_id` / `get_skill_id` with a row value >= 4, P4-BRIDGE-FACTS).
Anchors measured for the prompts (each string once in the image): `get_exit_value`
0x42e5a36, `EXIT_VALUE_DECIDE` 0x4359e6a, `sort_id_list` 0x427f3a7, `get_top_index`
0x4290580, `scroller` 0x436b678, `SCROLLER_ITEM_NUM` 0x42a18e6; no plain-text
`make_mii_hat` / `make_mii_special` / `chara_make`.

P7: no report, no `builds/0.3.0-presets/`, plugin still 0.2.0 at review time.

## 2026-10-05: P8 round reviewed; UI direction; P9 prepared

Checks rerun from the workspace root: `evidence/P8-LUA-LIST/check_p8_lua_list.py` 1667/0;
`evidence/P8-HAT-NATIVE/check_p8_hat_native.py` 221/0 (run from the mod folder as its report
says). `scratch/2026-10-05_P8-EDIT-DISPATCH/check_p8.py` FAILS (handler-table expectations
wrong at five indexes); that worker left no report. P8-LUA-LIST read: headline, sections 7, 8;
P8-HAT-NATIVE read in full.

Coordinator re-reads (capstone, this session): hash40 of the hat and body actor script paths
= 0x2fa5c13fc6 / 0x30c95391dc, and the movz/movk constants at 0x19cecf8 and 0x19c79f8 match
them, so 0x19ceb30 = headgear, 0x19c7830 = outfit. 0x19ccb20 prologue has no PC-relative
instruction in its first four words. 0x19c1f6c..0x19c1f7c: sort modes 2, 1, 0, anything else
branches away before the mode field write. 0x180a044..0x180a0c4: exit value read from
[[x19+0x178]+0x80]+0x128, negative -> other path, else state value+4 stored at
x19+0xf8+4*index with index at +0x144 (limit 0x13). 0x180ce40: state < 0xd, handler pair
loaded from x19+0x28+16*state.

Reasoning for the direction (D): a new sub-screen state needs a 14th handler in a 13-entry
table inside the scene object and a new child object; a new menu row needs a layout part that
does not exist and a layout member of different length, which the archive tool refuses. Both
are possible later. The cheap path keeps every native structure and changes behaviour in
three small places: the edit script (button -> a new exit value), `0x180a030` (plugin sees it,
sets its mode flag, substitutes 1 = headgear), and the list object (vector contents, row text,
decision). The risk is everything else that interprets the handles; that is P9-HAT-HANDLES.
Fallback stays the special-move screen selector (P8-LUA-LIST section 8).
Lua -> plugin channel candidates now known: exit value (edit screen), `sort_id_list` with a
mode outside 0..2 (headgear screen; native handler ignores it), `set_skill_id` row >= 4
(special screen). Plugin -> Lua: `get_top_index` return (integer), `get_skill_id` return.

## 2026-10-05: P7 and the P9 round reviewed; console session prepared

New coordinator took over from `HANDOFF.md`. All four in-flight tasks had delivered: P7,
P9-EDIT-DISPATCH, P9-HAT-HANDLES, P9-EDIT-SOURCE. Read the four reports in full.

Checks rerun by the coordinator (all from the workspace root unless noted): P7 `step0.py`
35/35; host tests 47/47; mutation control 61/61; `check_build.py` 98/98; `check_real_presets.py`
8/8 (940 values); `build-plugin.sh` exit 0 and the NRO hash `55a786b6...` reproduced; NRO,
example, preset file and the 0.2.0 rollback NRO hashes all equal their manifests;
P9-EDIT-DISPATCH `check_p9.py` 774/0 with six controls exit 1; P9-HAT-HANDLES
`check_p9_hat_handles.py` 396/0 with ten controls exit 1; P9-EDIT-SOURCE `build_check.py`
both chunks BYTE-IDENTICAL (edit 18 prototypes, special 17) and `negative_controls.py` 7/7;
`check_probe.py` matches the manifest; `check_probe_msg.py` 3 files 0 problems 8/8 controls;
P8-HAT-NATIVE 221/0 (run from the mod folder); P5-UI-API 35/0; P4-STAT-SITES 3327/0.

Discrepancies found and fixed. (1) P9-EDIT-DISPATCH's report quotes a 639-check run captured
at 13:23, but the delivered `check_p9.py` was extended at 13:59 and reports 774; the report
now says so and the coordinator rerun is `evidence/P9-EDIT-DISPATCH/18_coordinator_rerun.txt`.
(2) `0x180cf00` was left open by that report; the coordinator disassembled it: it is
`bl 0x39c20a0 ; udf #0`, the trap. **Exit values >= 9 abort**; values 0..8 all reach existing
states. (3) The coordinator re-read state 11 (`0x180cbc0`, reached by value 7): it returns
unless `scene+0x164 <= 0` and `[0x532e7a0]` is non-zero, then does one lookup and at most pops
one state level. **Decision: the script publishes 7; the plugin rewrites it to 1 before
`0x180a030` reads it.** Value 8 (state 12) is the editor teardown and is avoided. (4) The
§1 one-liners for states 8 and 11 in the P9 report were swapped against its own §1.2; fixed.
(5) P9-HAT-HANDLES' five corrections were propagated into P8-HAT-NATIVE as a second
correction banner plus inline fixes (headgear handler set `0x19cd0b0`/`0x19cd100`/`0x19cd2c0`/
`0x19cd310`; fields live in the 0x170-byte sub-object at `[list+0x80]`; decided handle reaches
static `0x5306cb0`; `get_top_index` returns `vector[0]`-owned and `+0x169 == 0`). (6) Added
`evidence/P8-EDIT-DISPATCH/COORDINATOR-NOTE.md` because that stopped task's check script is
superseded by `check_p9.py`.

P7 review: the source matches its report (miss path frameless, only known hashes reach
`known_request`, `x2 != 0` passes through with atomics only, `install_site` verifies the four
words before patching). Contract readings in section 1 accepted as written, including "an
unknown `preset` line also clears an earlier valid one for the same ID". Deferred: the
`loadouts.new` reader rule (only matters once the UI calls `save_loadouts`). Risk for the
session: the three new `nn::fs` imports; failure mode is "plugin does not load", rollback is
0.2.0 (`4477dc9a...`).

Go/fallback for the UI: **go for the native headgear list.** No consumer of a handle traps; an
unknown handle gets the label `nam_mii_hat_unknown`; the row text and the decided row have
identified hook points (row filler `0x19ccb20`, label builder `0x3288330`, scene state 5
`0x180abd0` writing `0x5306cb0`). Open for the premium UI task: who installs the row-callback
vtable `0x50a6b18`, what pumps `0x19cc3f0` per frame, the cancel/restore path, and the commit
of `0x5306cb0` into the save. The special-move screen selector stays the fallback and would
need none of these.

Session prepared in `CURRENT_INSTALL.md` § 0.3.0-presets: plugin 0.3.0, `presets.txt`, loadout
v2 boot 1 (`0000f589 preset fox`) and boot 2 (`purin` + explicit `weight 130.0`, `0000f58b
preset fox`), the message probe and the edit-menu probe; two boots with one card swap. The
user was asked for the card (mount + go-ahead in the current conversation).

Out of scope, not started: the kb note about this target's `fs::rename` not replacing and
`File::open` reporting a missing file as a generic error (P7 section 7.8b); the P9 report's
suggested follow-ups (owner of `+0x132`, `0x180d2a0`, the colour sub-screen). No workers in
flight; all three Alpha slots idle.

## 2026-10-05 (later): boot 1 result and the ARCropolis generation

The user ran boot 1 of the 0.3.0-presets session and reported: stat changes worked; the
special-move sub-title showed the raw key `mnu_mc_probe_title`; the Favorite test on the edit
menu did not work. Wrote `evidence/2026-10-05_session1/RESULT.md` from the report plus the
card log (`log_boot1.txt`, 164 lines). Log facts (tier A): 7 L0 lines (presets 94/10/0, loadout
v2 1 accepted, hook 0x4e53e0 match=1 installed=1), one `LO id=0000f589 preset=fox`, ten `OV`
lines with the correct fox values, 22 `F5` snapshots with the third number 0 everywhere,
`x2nz=0`/`dropped=0`/`orig_null=0`, last `L5 req=91376 src=explicit:0,preset:36037`. So the
plugin feature is verified on hardware;the explicit-override path and `x2 != 0` remain untested (boot 2 covers the explicit line).

New offline check by the coordinator (tier B, scratch `scratch/2026-10-05_SESSION1-DIAG/
scan_arc_nro.py`): ASCII strings of the card's `libarcropolis.nro` (`49b6f634...`) contain
`arcropolis::fs::loaders`, the pre-refactor `XMSBT ... the following syntax error` wording and
`orbits-95d455ae...` check-out paths; the v4.1.x markers (`modfs`, `patched cache`, handler
chain) are absent. So the card runs the old 4.0.x generation (consistent with the 13.0.4 gate:
v4.0.7/v4.0.8); the kb note naming v4.1.1 was corrected in place. `add_label` exists in that
generation too (v4.0.8 `loaders.rs` 247-275) - the known difference is the patched-size answer
that v4.1.x adds (`base_size * 2`). No ARCropolis log exists on the card after boot 1 (level
`Warn`, logs folder empty), so the message-label failure is still not separated. Boot 2 plan:
loadout swap + `logging_level` Debug + the Favorite-press detail; a control override of an
existing label on the same screen is the follow-up probe. Boot 2 and the card edits wait for
the card and a go-ahead.


## 2026-10-05 (evening): boot 2 read; P10 round prepared

New coordinator from `HANDOFF.md` revision 2. The user reported boot 2 as "everything works as
planned" and asked for bolder steps: stat changes and the sub-title change are not new to them.

Boot 2 (tier A, `evidence/2026-10-05_session1/RESULT_boot2.md`, `log_boot2.txt` 141 lines
`06083fd7...`): L0 complete, two `LO` lines, `weight` for `0000f589` `src=explicit` 130.0,
nine fields `preset=purin`, ten `preset=fox` for `0000f58b`, last `L5 req=153600 x2nz=0
dropped=0 orig_null=0 src=explicit:31,preset:89250`. The control match was A against Mario on
P2 (not Mario P1 / B P2): Mario's lines are `p=1 kind=0 id=0000f58b st=kind`, which answers the
stale-slot question. A third fighter group with all ID slots zero (`st=noid`, kind 74) is read
as the editor preview fighter (inference). No file under `ultimate/arcropolis/logs/` at `Debug`;
level restored to `Warn` (card hash equals the backup `8448814d...`). Card otherwise untouched;
seven plugin hashes unchanged.

Offline checks by the coordinator: (1) `grep` of the extracted `msg_name.msbt`: 131
`nam_mii_hat_*` labels, 107 `nam_chr1_00_*`; `msg_menu.msbt` has none of either. The list's row
text therefore needs no added label, and the failed `msg_menu` addition is off the critical
path. The user's `pyra_gamewatch_reskin` ships a `msg_name.xmsbt` that changes existing labels
(read on the card, not modified). (2) `tools/lua-src/make_mii_edit_actor.lua` lines 360-398:
`update` runs the Favorite branch (`switch_favorite`) before `update_selector0`; the 0.3.1
probe sat in `update_selector0` and called `ComFrameActor.press_decide()`, which is the frame's
confirm path (`ComFrameActor.is_decided()` a few lines later), not `selector0`'s. So the probe
was wrong by design and its console result separates nothing. Not checked: whether
`press_decide()` without frame focus is really a no-op (the user saw no save/exit, which fits).

Decision: no probe-only boot. Reasons: the milestone needs no message label; the plugin can
enter mod mode without any script (entry B: Headgear decided while ZL/ZR is held), so an
unloaded edit chunk no longer blocks it; one boot then answers the chunk question as a side
effect (entry A works or not, the marker variant tells why). Cost accepted: the premium task is
large and its runtime behaviour is D; first-boot failure is possible. Mitigations written into
the prompt: hard invariant E3 (snapshot/restore of `0x5306cb0`, logged), all-or-nothing UI hook
install with word checks, `ui_off` switch file, flushed `mc|UI|` lines, stop-and-report instead
of switching screens.

Contracts added (coordinator-owned, text in `prompts/P10-UI-SLICE.md`): E1-E6 behaviour; F
`list.txt` (`mc_list 1`, `<preset_name> <message_label>`, optional, fallback
`nam_chr1_00_<name>`); B+ read `loadouts.new` when `loadouts.txt` is missing (closes the P7
section 3 window). Contract A is unchanged; wider presets use its existing 48-field limit.

Round: P10-UI-SLICE (premium), P10-EDIT-ENTRY (script with exit value 7 on Favorite while the
Headgear row is selected; marker variant; arc index comparison of the edit and special chunks),
P10-PRESET-WIDE (float fields with +0x270 sites, at most 48; `list.txt`), P10-HAT-OPEN (state 5
exits, preview writes, save commit, frame-callback pump, vtable `0x50a6b18`, item count).
Hypothesis handed to both native tasks (D): `0x50a6b18` = `0x50a6ae0 + 0x38`, the secondary
vtable of the sub-object at `S+0x48`, which would explain why nothing references it directly.
P10-HAT-OPEN overlaps the premium task on purpose: it is the independent second reading the
coordinator will review the plugin against.

## 2026-10-06: P10 round reviewed; session 0.4.0-ui prepared

The user reported all four workers done. Three were; **P10-UI-SLICE stopped at 18:04 on
2026-10-05** with a 15-line report stub, no manifest, no tests, no check script. Its source
is complete and the NRO it staged (`d28aea75...`) rebuilds bit-identically.

Checks rerun (workspace root, real exit codes): `check_p10_hat_open.py` first 473/1 (exit 1):
the script was edited one minute after the report; the new claim `check_imm(0x17c0b5c, 0)`
targets `mov w21, wzr`, which has no immediate. Removed by the coordinator -> 472/0, exit 0;
`--neg writers` exit 1. `check_entry.py` exit 0; `build_check.py` both chunks byte-identical;
`check_preset_wide.py` 29/0. Own check for the plugin: `check_ui_sites.py` 52/0. 0.3.0 host
tests on the 0.4.0 sources 47/0.

Read by the coordinator in the image: `0x19cc444..0x19cc460`, `0x19cc640..0x19cc6dc` (the
`S+0x148` store is indexed by the `get_decided_id` result and skipped when it is negative);
`0x180acc8..0x180ad24` and `0x180ae08..0x180ae24` (static written when the handles differ as
items, not only when one is invalid); `0x328b77c..0x328b7b8` (`cset w0, ls`: 1 for a miss);
`0x19ccbdc..0x19ccc14` (label struct in `x0`, text at +8); `0x19ccd74..0x19ccd90`;
`0x37830e0..0x378311c`. These settle two disagreements between reports in favour of the
premium worker's source: the meaning of `0x328b5d0`, and decide-versus-cancel through
`S+0x148`. P10-HAT-OPEN's "cancel cannot restore" is wrong as a conclusion (the restore is
writer 2 with the seeded `S+0x148`); corrected in place.

Plugin source read in full: `ui.rs`, `editor.rs`, the changed parts of `lib.rs` and
`loadout.rs` (`load`, `Store::set_preset`, `serialise`); `list.rs` only its head. Judgement:
the hard invariant is enforced three ways (preview flag cleared every tick, native state
restored before the original's last tick, snapshot compare with restore) and backed by the
game's own save check. Not judged: anything at runtime.

Decision: package and ask for the boot now instead of first sending the premium worker back
for tests and a report. Reasons: the open questions are runtime ones (count change on a live
scroller, the hid read, `S+0xe8`, the first save); a second premium session will be needed
after the boot in any case and can then carry both the missing deliverables and the fixes;
the rollback is one file and `ui_off` switches the list off without a rebuild. Cost stated
to the user: no host tests for the new code, first-boot failure possible.

Session choices: marker variant of the edit script (Try button hidden = chunk loaded);
`loadouts.txt` with only `0000f58b preset fox`, so the wide preset is felt even if the list
fails and Gunner A's first preset comes from the list; the old explicit `weight 130.0` line
is dropped so a chosen character is not masked. Wide preset accepted with all 41 fields;
`shield_break_y` (purin 936.84) is the real table value. Fields tied to body size
(`tread_range_*`, `ladder_range_*`) are in; revisit if footstools or ladders feel off.

## 2026-10-06 (night): session 2 result; P11 round prepared

The user reported that the list "seems to be working" and asked for the menu change discussed
earlier. Log copied from the card (`evidence/2026-10-06_session2/log_boot1.txt`, 419 lines,
`f150160e...`): `ui=on installed=5`; four `arm|entry=A`; `open ... native_count=52 rows=88`;
one cancel, `decide row=87 koopag` (`store added`, `SV ok`), a reopen with `current_row=87`,
a cancel, and in a new editor scene `decide row=38 dedede` (`store changed`, `SV ok`); every
`exit` has `equal=1 restored=0 record_equal=1`. `loadouts.txt` on the card is the plugin's
own 57-byte file. So the 0.4.0 design is confirmed on hardware for way in A, and the open
question "does a replaced edit chunk load" is answered yes. Not exercised: way in B, row 0,
sort, reboot. The premium worker's untested code held; the debt (tests, check script,
report) is carried into P11-MENU as its first items.

Design for the user's request (contracts in `prompts/P11-MENU.md`): a main page with one row
per entry of a new `menu.txt` (kind `stats` or `slot`, literal text), each opening a
character page; `slot` pages grey every character without an `allow` line, so today only the
default row is available. How a page change is done is left to the worker (re-entering state
5 or resetting the list in place) with the state-stack depth as an explicit proof
obligation. Nothing is stored for slots yet: there is no move to store, and a loadout key
invented now would have to be changed when the first move defines what a choice means.
Row 0 becomes the Mii's own class (`nam_chr1_00_miigunner`, which exists) instead of the
hat label "None"; `list.txt` will be regenerated without the `miigunner` row.

Row text is the new unknown: menu entries are not existing labels. Lua has
`set_text_string` (3 call sites), so a native literal-text path exists; the premium task is
to use it, with an existing-label fallback per entry, and P11-ROW-TEXT reads the same code
independently (also: which message files the row lookup searches, candidate labels, and what
a greyed row does on decide, where a shop or unlock prompt would be a problem).

Idle-slot tasks chosen for what comes after the menu: P11-INT-PARAMS (the +0x250 getter;
jump count needs motions the Gunner may not have, asked explicitly) and P11-MOVE-PLAN (the
first borrowed move; the hard part is that scripts and motions are per fighter kind while
the choice is per saved Mii). The second reads `mods/ssbu_mod_new/` under that repo's rules,
reference only.

## 2026-10-07: new coordinator; P11 round reviewed; session 0.5.0-menu prepared; P12 round

A new chat took over coordination (read: both AGENTS files, `STATUS.md`, `HANDOFF.md`, the
tail of this log, the four P11 prompts and reports, `plugin/src/editor.rs` in full).

Delivered: P11-MENU, P11-ROW-TEXT, P11-MOVE-PLAN. **P11-INT-PARAMS stopped** at about 23:55
with its report still the skeleton and no check script; it left scanners in its scratch and
tables under workspace `gamedata/mii_customizer/P11-INT-PARAMS/` (unreviewed). No stray
files at the workspace root.

Checks rerun from the workspace root (real exit codes): `check_p11_menu.py` 358/0, exit 0;
`--selftest`: clean run 0, all 11 controls 1. `run_host_test.sh`: 47/0 and 35/0.
`check_p11_row_text.py` 340 checks green, `--neg` exit 1 with 5 mismatches.
`check_p11_move_plan.py` 4/4. NRO `565014ab...` equals the manifest. Not repeated: the
plugin build (the worker built twice with one hash) and the 102-mutation control.

Read by the coordinator in the image: `0x180ce40..0x180cf04` (reader: equal states and byte
`+0x154` set -> optional callback pair, frame counter and byte cleared; index >= 19 and
state >= 13 trap), `0x180adf4..0x180ae04` (one pop, not below zero), `0x377e278..0x377e2a8`
and `0x377e33c` (decide needs slots `+0x200` and `+0x210` to answer 1; the refusal path
stores nothing), `0x335a54c..0x335a558` (`set_text_string` -> `0x37a22f0` on
`[[ud+8]+0x10]`), `0x3776378` (`mov x20, x8`: result through x8). All as the report says.

Judgement of 0.5.0: the page change writes two scene fields, and only when six conditions
hold, otherwise the visit ends as a cancel; the invariant "mod mode never changes the Mii"
keeps its 0.4.0 enforcement per page plus a per-visit snapshot; greyed rows are refused
twice (native button state, plugin step). The two independent readings (premium worker,
Alpha row-text task) agree on the text route and the greyed path; ROW-TEXT's Q3 (rows are
refilled on scroll and redraw) is what the plugin's "set text after every fill" needs.
Runtime risks named for the test: the in-place restart of state 5, a list shorter than the
native 52, the look of a disabled row, text persistence and fit.

Session files (coordinator, `scratch/2026-10-07_coordinator/make_session3.py`):
`builds/0.5.0-menu/session/menu.txt` with 24 entries. Entry ids are the P1-DATASET slot ids
(`normal_jab`, `tilt_side`, ...), because the proposed loadout key is the entry id and the
catalogue ids are the stable names this project already has. Fallback labels for the six
entries with an exact existing text (ROW-TEXT Q4). `list.txt` = the session-2 file minus the
`miigunner` row (row 0 of every character page is the Mii Gunner default). Both parsed with
the plugin's parsers compiled unchanged (`session_check.rs`): 0 rejected, 24 / 86. The plain
edit-script variant replaces the marker one (Try button back); it has not run itself.
`loadouts.txt` on the card stays (A dedede, B fox), which gives step 6 a known start row (38).

P11-MOVE-PLAN is weaker than its "DONE": the check covers hashes, jab motion entries and
skeleton/track counts; hitbox values, status behaviour, effect/sound usage, file names and
both designs are not measured. Banner added in place. What stands: one skeleton for the
three classes, different jab structures, scripts and motions per kind. Decision (D): the
first borrowed move to investigate is Brawler's forward tilt (one stage, no weapon), not the
jab the prompt named. The user's wording listed Jab and Forward Tilt as examples of menu
rows, not an order of implementation; say so in chat.

P12 round (three Alpha, no premium): P12-INT-PARAMS (finish the stopped task from its own
tables, reproduce before trusting), P12-FTILT-FACTS (measure what MOVE-PLAN asserted, for
the forward tilt: motion entries, decoded ACMD calls, dependencies, status overrides,
animation nodes), P12-SCRIPT-ROUTE (what script framework the other mod uses on the console,
its API by file:line, the path from a script to the entry id, the game's own script table,
and a compile-only spike crate under scratch). Premium is held back until the console result
or these two move reports give it a concrete job. The parked `slot` loadout key waits for
the same.

## 2026-10-07 (later): session 3 boot 1 failed safely; 0.5.1

User: mod mode "tries to open" and returns to the edit menu. Log: `probes_ok=47/48`,
`installed=0`; the entry of `0x37a22f0` reads `58000051 d61f0220 <target>` (inline hook by
another plugin, owner not identified; offset literal found in no other NRO on the card).
Record: `evidence/2026-10-07_session3/RESULT_boot1.md`. Lesson for prompts: a load probe on
the ENTRY of a function the plugin only calls must tolerate a foreign hook; probe a word
inside the body instead. The offline review could not have seen this; only 0.5.0 added that
entry to the probes.

The coordinator made the fix itself instead of spending a premium session: 17 lines in
`install_ui` (`plugin/src/lib.rs`), version 0.5.1, no other source change. Accepts only the
stub `ldr x17,#8 ; br x17` and only at `FN_SET_TEXT_UTF8`; the body probe `0x37a23d0` still
has to match. Build exit 0, 0 warnings; host tests 47/0 + 35/0. Not done: adapting
`check_p11_menu.py` (bound to the 0.5.0 package; its manifest section now fails on the
changed `lib.rs`, `Cargo.toml`, `Cargo.lock`), mutation control, a second build. Installed
with the card mounted, on the user's install go-ahead of this session and their failure
report. Risk named to the user: literal text now goes through someone else's hook
(`text_off` is the switch).

## 2026-10-07 (evening): session 3 boot 2, 0.5.1 works

Log read (`evidence/2026-10-07_session3/RESULT_boot2.md`). All four runtime questions of
P11-MENU section 10 are answered yes on hardware: in-place restart of state 5 (24 changes,
depth constant), a 24-row list on the 52-row native list, native refusal of greyed rows (no
fallback line), literal text (`text_missed=0`). First read-back of a plugin-written loadout
file after a reboot. The user edited Gunner B. Their question about Kirby's jumps: integer
parameter, out of the preset by design so far. Left open: owner of the `0x37a22f0` hook;
way in B; the fill frequency (about 1600 fills on one page) if performance ever matters.
`check_p11_menu.py` is still bound to 0.5.0; adapting it rides with the next plugin task.

## 2026-10-07 (evening): 0.5.2, current choice on the menu rows

User: "what would be really nice is if I could see in the 24 row menu what was already
selected for everything." Done by the coordinator (small, on the proven text route):
the row filler hook composes "<entry text>: <name>" for main-page rows. Names are literal
text, so they come from a new optional file `names.txt` (`mc_names 1`), generated from the
user's own `msg_name.msbt` (`nam_chr1_00_<preset>`, 87 lines incl. `miigunner`), kept under
`gamedata/`. Rejected alternative: resolving the label through the game's lookup
(`0x37a3ea0`) and composing UTF-16 natively - more native surface for the same picture, at
the price of not following the console language. Stats row: the Mii's preset at page open;
slot rows: the default, until a slot choice is stored (the parked `slot` key). Without the
file: 0.5.1 behaviour. Unknown until seen: fit of up to 27 characters in the row pane.

## 2026-10-07 (night): P13 round (Minus entry, button tip) for GPT 6 Luna

User: open the custom menu with Minus anywhere in the Mii editor instead of the Favourite
button, with a tip in the top corner ("- Advanced Options", replacing or next to the
Favourite tip); delegate to GPT 6 Luna agents, as many as useful. The coordinator has no
evidence about that model; the prompts are written like premium ones (report first, checks,
exclusive paths). Two tasks, not more: the work is one script and its two halves are the
only independent pieces. Each writes its own variant of the edit script; the coordinator
merges and packages. The unknown that decides the rest: whether the edit menu's virtual
input carries Minus at all (28 INPUT_* names, none for Minus). If not, the plugin reads
nn::hid in the dispatcher hook; P13-MINUS-ENTRY part A3 collects what that needs and a
plugin task follows. "Anywhere in the Mii editor" is read as "any row of the edit menu";
sub-screens are out of scope (said to the user).

## 2026-10-07 (late): P13 reviewed; 0.6.0 (Minus entry, tip)

P13-KEYHELP delivered a script-only tip (target 2: the Favourite tip's two text panes get
the Minus glyph label `cmn_button_nx_minus` and literal "Advanced Options"); its check
reruns clean. P13-MINUS-ENTRY came back partial: it could not map virtual input indices to
buttons (and misread the disassembler path), built nothing, and recommended a "dedicated
script-visible Minus query" without a mechanism.

Coordinator's route, found while reading `0x1808e60..0x18090b4`: the scene builder registers
this script's integer globals on the Lua state at `[[x22+0x40]]`, x22 being the 0x138-byte
inner object the dispatcher reads (P9 section 3), with `0x33750a0` - the call the plugin
already makes for `SCROLLER_ITEM_NUM` (tier A). So: per edit-menu frame the dispatcher hook
reads the pads (the hid code of way in B, generalised), and on a Minus edge with no exit
value published sets `MC_MINUS = 1`, lowering it two frames later; the script's `update`
tests the global first, clears it, and takes the same four exit statements as the
P10-EDIT-ENTRY block. The script exits by itself, so its teardown is the ordinary one.
A time-boxed attempt to find the physical mapping instead (scan for `add x, x, #0x198` /
`#0x264`) gave nothing usable and was dropped.
Risks named to the user: nn::hid has never been called by this plugin on the console
(way in B was never exercised) and is now called every edit-menu frame (`minus_off`
switches it off); the tip may be rewritten by native code after a favourite toggle.
Not done: check script for the 0.6.0 NRO, mutation control.

## 2026-10-07 (late): 0.6.0 works; P14 round

User: 0.6.0 "works" (Minus entry and tip; first real nn::hid use by the plugin and the Lua
global channel are thereby tier A by report; the log was not copied, do it at the next
mount). Three requests: (1) remove Giga Bowser and other non-playable characters from the
list; (2) sort by name must work, the other sort options keep fighter order; (3) a Sword
option (visible only during sword moves, used for all sword moves with effects; only the
Mii Swordfighter sword for now).

Split by what can run in parallel, not by request number: only one task may own `plugin/`,
so the sort and the menu side of the sword option are one plugin task (P14-SORT-OPTIONS,
0.7.0), the list is a data task (P14-LIST-PLAYABLE), and the match side of the sword is a
facts task (P14-SWORD-FACTS) because no sword move exists on a Gunner yet. The sword menu
entry is a new entry kind `option` (rows are the entry's own options, not characters): a
`slot` page would have shown 86 greyed characters under a "Mii Gunner" default, which is
not what a sword choice is. Loadout version 3 with an `option` key is defined in the prompt
(written only when an option line exists, so 0.6.0 can still read the file after a
rollback while nothing is chosen). This supersedes the parked `slot` key proposal only for
options; slots still wait for the first move. From the 94 presets the list holds 86; the
only row the coordinator knows to be non-playable is `koopag`; the task has to show it from
game data.

## 2026-10-07 (midday): round review; 0.7.0 staged; list filter parked

Delivered: P12-INT-PARAMS, P12-SCRIPT-ROUTE, P14-SORT-OPTIONS, P14-LIST-PLAYABLE (partial).
Still running at 12:45: P12-FTILT-FACTS (report untouched since its skeleton, scratch
active) and P14-SWORD-FACTS.

User on P14-LIST-PLAYABLE: disagrees with its result and with the question; what matters is
per character and per move how feasible a move is on a Gunner. Parked; list unchanged. The
coordinator's prompt had asked the narrow question (selectable on the character select
screen); the worker's table was not reviewed.

P14-SORT-OPTIONS: checks rerun (389/0; 47/0, 35/0, 16/0). Code read: handles stay tied to
fighter-order rows and only the vector is permuted, so the label hook, the availability
mask and the decision all follow the character; that is the right shape. Weak points
recorded in the report banner: invented log lines in its test plan, indexing and a literal
offset in `handle_sort`, an unanalysed doubling of the NRO, and a consequence of the
coordinator's own spec: persisting the order while the script resets its label on
initialise. Shipped as built; the console decides (test step 6). Session `menu.txt` gets the
Sword entry directly after Stats: equipment before the 23 move rows.

0.6.0 log copied (`log_boot4_0.6.0.txt`): `minus=on`, two presses, both armed. A third saved
Mii (`0000c291`) appears with preset `sonic`: the user is using the mod on other Miis.

Next premium task is the first borrowed move. Inputs: P12-SCRIPT-ROUTE (done),
P12-FTILT-FACTS and P14-SWORD-FACTS (running). Not scoped before the facts are in.

## 2026-10-07 (12:50): handoff; forward-tilt task handed over

At the user's request: `HANDOFF.md` revision 5 (replaces all earlier ones) and
`prompts/P15-FTILT-TAKEOVER.md`. The first P12-FTILT-FACTS worker has tables for Q1, Q2/Q3,
Q5 and a long series of status probes (Q4), but an untouched skeleton report and no check
script after three hours. The takeover prompt forces a partial report in the first minutes,
a per-question verify-then-write loop, a validation step for the ACMD decoder, and a time
box on Q4. 0.7.0 is still not installed.

## 2026-10-07 (13:15): forward-tilt facts done; P16 written as a build task

The user asked why the forward tilt was made so complicated when move copies in their
other mod are fast. Fair: the coordinator had carried the menu work's evidence-first style
(right there, where a wrong native guess crashes the game) over to a move copy, where a
wrong value is visible in training mode and cheap to fix. Decision with the user: no more
research rounds before the first move; one implementation task using the other mod's recipe.

The takeover worker finished P12-FTILT-FACTS in about fifteen minutes (check exit 0), which
gives P16 its hitbox table for free. What P16 adds beyond a routine copy: the per-object
choice (owned motion and script names next to the vanilla ones, vanilla path untouched for
every other Gunner), slot storage in loadouts version 3, a table of implemented (entry,
preset) pairs that gates `allow` lines, and this mod's first ARCropolis fighter files
(generated into gamedata, not the mod tree). Stated reductions the prompt allows: straight
tilt only if angled owned motions are hard; the Gunner's own swing sound and voice sequence
instead of Brawler's bank. Sound banks, swords, integer stats: out of scope.
P16 builds on the 0.7.0 sources, which have not run on the console; if 0.7.0 shows a
problem, fix it before or together with reviewing 0.8.0.

## 2026-10-07 (evening): coordinator change; P16 reviewed; 0.8.0 installed

The user asked a new chat to take over as coordinator and to put together and install the
latest version. Latest = 0.8.0 (P16), which contains 0.7.0; neither had run or been installed.

Review of P16 (all offline, B): `check_p16.py` exit 0; host tests 47/0 + 35/0 + 4/0 + 16/0 +
6/0; the worker's NRO `2890bc58...` reproduced bit for bit by a rebuild. The worker's check
covers only kind, clip hash and flags of the added entries, so the coordinator added
`scratch/2026-10-07_coordinator/p16_entries.py`: game, expression, sound and effect script
hashes of each added entry equal the names registered in `moves.rs`, and the tail (cancel
frame 28) equals the donor entry. The report does not answer the prompt's costume-group
question (R8); `scratch/2026-10-07_coordinator/dirprobe/` (smash-arc 0.6.0, read-only on the
user's data.arc) shows `fighter/miigunner/c00` present with 502 files including the Gunner's
motion list and clips, `c01` absent, `fighter/miifighter/c00` and `fighter/elight/c06`
(the other mod's proven key shape) present as controls. The six `smashline_*` imports exist
in the card's Smashline NRO (`smashline_syms.py`).

Read in `moves.rs`: the wrapper calls the original Main for every Gunner without a stored
choice and returns its value (vanilla path); with a choice it calls the original, changes the
motion to the owned kind picked from stick Y at entry and installs its own main loop. That
loop had no airborne branch; added (situation not ground -> FALL), the only coordinator
change. Any stored slot value counts as "miifighter", which is right while the table has one
row and must become a lookup with the second move. `moves_off` is tested with
`Path::exists`, the other switches with `fs::metadata`; same effect. Not checked: that the
stick threshold 0.28 equals the game's own angle parameter (the report asserts it).

What the report claims without evidence and the console decides: clips load for a Mii,
scripts and status wrapper run on `miigunner`, sounds. The section-3 test in the report is
replaced by the eight steps in `CURRENT_INSTALL.md` (its `decide` log line was written from
memory; the real one is `decide|page=entry:tilt_side|...`).

Installed with the card mounted (E:) under the request above: seven files, all re-hashed
equal; the other six plugins unchanged. P14-SWORD-FACTS is still unreviewed.

## 2026-10-07 (late evening): 0.8.0 crashed at boot; stack overflow; fixed

Full record: `evidence/2026-10-07_session4/RESULT_boot1.md`. The crash report gave it away
directly (SP below the stack region inside the plugin's `main`). My review missed it, and so
did the review of 0.7.0: the "NRO doubled, not analysed" note in the P14 banner was this
defect showing. A `Menu` is 123 KiB and a `Table` 77 KiB; the load thread has 64 KiB.
New standing check before any plugin is called READY: `tools/stack-frames/stack_frames.py`
(default limit 24 KiB; 0.6.0's 19.6 KiB is the largest frame known to work).
Still open after the fix: the save path also built two tables per save on the game's
thread; they are on the heap now, so that risk went with the same change. `Table::new` and
`Menu::new` remain as const constructors for statics and tests; do not use them for locals.
What this boot did NOT test: anything of the move, the new mod folder, Smashline scripts.

## 2026-10-07 (night): boot 2 - the move's motion list lost against the other mod; motdiff

Record: `evidence/2026-10-07_session4/RESULT_boot2.md`. Two things to keep:

1. **Any fighter file this mod ships can collide with `pyra_gamewatch_reskin`**, which ships
   files for most fighters (its cargo-throw victim motions add entries to every fighter's
   body motion list). Before a package is READY: compare its file list with the folders on
   the card and read `ultimate/arcropolis/conflicts.json` after the first boot. For motion
   lists the answer is a `motion_list.motdiff`; for other shared files (params: `.prcx`,
   messages: `.xmsbt`) ARCropolis has the same kind of patch file. Clips under owned names
   and `new-dir-files` entries do not collide.
2. **A move must fail to vanilla.** The wrapper now checks that the owned motion exists
   before switching to it. Every later move gets the same check.

The motdiff must be written in serde_yaml 0.8 form (enum variants as single-key maps); the
0.9 form with YAML tags would not parse in the card's ARCropolis. `tools/move-package/motdiff`
pins 0.8.26 for that reason (crate fetched from crates.io into the user's cargo cache, a
project-local build dependency).

Open, D: whether the card's ARCropolis applies the patch as the v4.0.7 source says (its
version is not established); whether `is_anim_resource` answers false for a kind that is
missing from the list (if it answers true the fallback does not trigger and a missing
motion would freeze again).
