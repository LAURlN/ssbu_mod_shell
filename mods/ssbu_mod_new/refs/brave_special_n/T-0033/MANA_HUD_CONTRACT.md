# Hero mana and fighter HUD implementation contract

Revised 2026-10-02 by T-0049 for T-0046; replaces the 2026-10-01 T-0034 draft.
Revised 2026-10-02 again by T-0057: the six prices, the ceiling and the recovery
period are now measured, and the vanilla HUD MP gauge is identified. T-0057's own
measurements are owned by `../T-0057/`; this file stays the contract.
Canonical contract remains here; new measurements are owned by `../T-0046/`.
**Gameplay mana is implemented** (`src/pgwr/plugin/src/mythra/hero_mana/`, T-0057)
and **hit/shield recovery remains reserved**, disabled behind `hero-mana-reserved`.
Revision 2026-10-03 (Codex takeover): user explicitly authorized project-owned native HUD
integration. The separate `hero-mana-hud` feature now has a checked READY package at
`builds/pgwr/zapple-mana-hud-0.1.1/`. It calls the measured game part selector/SP handlers
without installing an interception; earlier hook candidates below remain historical design
inputs, not current HUD prerequisites. Canonical route: `../hud_route/SOURCE.md`; hardware
behavior unverified (D). Simulation-clock and damage callbacks remain outside this feature.

Tiers: A console; B offline byte/source measurement; C pinned external source;
D design/hypothesis requiring confirmation. No new A evidence exists. Instructions
and source inspection do not establish gameplay.

## Scope and retractions

T-0046 supersedes historical mana-off instructions: one per-player shared meter
for each c06/c07 Pyra/Mythra pair, surviving both swap directions. Only neutral-B
and side-B spend. Hero Spin and unrelated moves keep their current rules. A real
fighter HUD is required; charge effects or effects above characters do not satisfy
it. Do not rebuild or replace a protected global framework plugin.

The six levels are Frizz/Frizzle/Kafrizz and Zap/Zapple/Kazap, not six helper call
sites. One neutral-B helper call selects three prices; up-B/unknown calls are outside
this scope. Side-B `main_entry` means spell entry and MUST NOT refill MP. Recovery
must advance outside spells and across both forms, once per eligible game frame.

Withdrawn: side-B prices must be literals because trimmed recipient params lack
SP keys; the complete donor parameter read must be recovered. Withdrawn: main is
missing; T-0049 decoded the local 13.0.4 NSO. Withdrawn: mana without HUD completes
this goal, world effects are recommended, swap persistence needs a preference
answer, or only side-B EXEC should recover mana.

## Evidence and available inputs

Existing B pins: `../neutral_b_status.c`, `../shoot_control.c`,
`../../brave_special_s/{FLAG_SUCCESS_SP.md,flag_success_sp.c,SOURCE_STATUS.md}`,
`../../brave_special_s/native_dependency_audit.{json,asm.txt}`. Read their Ghidra
marshalling/hash truncation caveats. Pinned Hero NRO SHA256:
`dc5edcde314f0c461ba0ab08d9e9deef5ede9d5b4ed324141678b9966d43b7a2`.

New B main measurements: `../T-0046/main_provenance.json` and native listings there.
Source main SHA256 `77936fe2031e4f38316120576177090857611025e140b415d3850bac8eabd92e`;
build ID `3eae0063b12fd81e99fb5980ba56297049ea94f9000000000000000000000000`.
Every decoded NSO section matched its embedded SHA256. Derived flat SHA256:
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`.
Image: lab `gamedata/ssbu-13.0.4/main.bin`, never written into dump. Existing tools:
`tools/main_image.py`, NSO section algorithm from `tools/inspect_main.py`;
one-off capture scripts: lab `state/scratch/T-0049/{native_audit,follow_native,hud_xrefs,detail_native}.py`.

`paths.toml:[dumps].arc` points outside the lab. This run obeyed the stay-inside rule
and did not inspect that export. Recursive workspace inventory found no Hero/common
NRO or Hero vl.prc. This is unavailable INSIDE the authorized workspace, not an
assertion that it is absent from this machine. The local patched data.arc exists;
`tools/data-arc-extract` extracts the container, not individual ARC entries. No
in-workspace ARC reader was identified; the live extractor needs a running console
and was not invoked. External source retrieval did not supply a pinned HUD source;
no third-party HUD code/offset has been adopted.

## All six prices and spending contract

Labels/hashes are B from `dumps/scripts/ParamLabels.csv`; labels do not supply
numbers. Thresholds: neutral `donor_params.rs`/pinned status C; side
`param_special_s.json`/`SOURCE_STATUS.md`. Counts are donor charge counters, not
input-to-hit animation time. Ground/air share a level.

| Level | Charge count | Price key (Hash40) | Debit site in Hero NRO | Numeric price |
| --- | --- | --- | --- | --- |
| Frizz N1 | below 18 | sp_special_n1 `0x0d3fd79c7d` | SHOOT MAIN `0xce38` | **6.0** |
| Frizzle N2 | 18..80 | sp_special_n2 `0x0da6decdc7` | same selected branch | **16.0** |
| Kafrizz N3 | 81+ | sp_special_n3 `0x0dd1d9fd51` | same selected branch | **36.0** |
| Zap S1 | below 9 | sp_special_s1 `0x0dc0bbf061` | ATTACK1 MAIN `0xe830` | **8.0** |
| Zapple S2 | 9..25 | sp_special_s2 `0x0d59b2a1db` | ATTACK2 MAIN `0xeab0` | **18.0** |
| Kazap S3 | 26+ | sp_special_s3 `0x0d2eb5914d` | ATTACK3 MAIN `0xed80` | **42.0** |

T-0057 measured all six, plus `sp_max` **100.0**, `recover_sp` **1.0**,
`sp_recover_frame` **60**, `sp_recover_damage_mul` **0.8** and
`sp_recover_shield_mul` **0.8**, out of the pinned donor `vl.prc`
(`fighter/brave/param/vl.prc`, sha256 `dafa43c6...`, container
`gamedata/ssbu-13.0.4/data.arc` sha256 `ef615e67...`). Tool
`tools/dump_hero_mana_params.py`; report `../T-0057/hero_mana_params.json`. Every
key above was predicted from `ParamLabels.csv` and matches the decoded file, so
the label table and the file agree. `param_special_n[0]` repeats the neutral
prices; entries 1-3 are zero; the side-B prices exist only in `param_private`.

The side-B level thresholds used here are `hold_frame_m` 9 and `hold_frame_l` 26
from `param_special_s`, which is what the recipient's own HOLD already counts
against.

Neutral SHOOT MAIN `0xcc20` selects `param_special_n` child price then calls
`0x16db0 -> 0x1a230`. Side MAINs also pass parameter-read amounts (setter example
in FLAG_SUCCESS_SP.md). Recover their full parent/child reads from original NRO
and full vl.prc, rather than inferring literals from a subsection's absence.

**Done (T-0057):** the parent/child reads are `get_param_float(boma,
hash40("param_special_n"), <price hash>)` for neutral and `param_private`'s
`sp_special_s*` for side, and all six values are measured - see the table above.
No familiar number was used; the gate's `<=`, the "debit only on success" rule
and the finisher's exemption are re-read from the pinned `flag_success_sp.c` and
`neutral_b_status.c` and are quoted in `../T-0057/SOURCE.md` §4.

The shared gate compares amount <= current SP, sets success on affordability,
clears it otherwise; debit happens only on success, once in attack/SHOOT MAIN before
article creation. Proposed owned `try_spend(entry,stock_generation,cast_token,price)`
caches the decision/debit against duplicate callbacks. Do not spend in HOLD, at hit,
on motion inheritance or again in S3_APPEND. Charge/cancel alone has no debit;
post-debit interruption gets no invented refund. Do not downgrade to a cheaper spell.

Failure needs donor game/effect/sound/expression and motion/cancel timing. Neutral
`generate()`/ACMD must use the cast outcome. Side `sparks()` and S3 lightning
activation must gate it; successful hitboxes must retain the donor failure split.
Donor `0x28ce0` returns on false success; `0x29760` needs success AND lightning.
Complete failed-cast timing is unresolved until original NRO/ACMD is recovered.
Never call Hero's helper/specializer or alias its work IDs on either recipient.
Uncertain donor add_sp marshalling does not require a runtime donor call: own arithmetic.

## Recovery and lifecycle: measured shape, missing numbers/events

New evidence: `../T-0046/{sp_native,recovery_native,lifecycle_hud_native}.asm.txt`.
Offsets below are Hero's decoded parameter object at
`*(*(main+0x52bb3b0)+0x1298)`, not PRC file offsets or recipient work indices.

| Rule | Measured 13.0.4 shape | Missing prerequisite |
| --- | --- | --- |
| Start/max assignment | `0x852840` loads +0xb0, writes max float index 0x52, then same clamped value to SP index 0x53 | vl.prc sp_max value; complete creation/stock caller mapping |
| Passive recovery | `0x853500` path increments int 0x100000c0; compares int +0xb4; after pause check calls add_sp with float +0xb8, then zeros counter | exact sp_recover_frame/recover_sp values and decoded-field association |
| Pauses | branches for global stop, stop-related module queries, status 0x1d6, SP >= max, flag 0x200000e5 at `0x85362c` | common NRO resolves methods/status/flag; all set/clear paths |
| Neutral charge pause | pinned neutral HOLD entry sets DISABLE_SP_AUTO_RECOVER | all clears/exits/interruptions and side-B pause paths |
| Hit/shield recovery | `0x854610` event entry leads to `0x854a4c`; bit selects float +0xbc or +0xc0, multiplies computed damage then add_sp | multiplier values, bit semantics, event ABI and all filters |
| Positive add precision | `0x853890` adds f32 9.999999747378752e-06 (main+0x4471970) only for positive delta, then clamps [0,max] | faithful recipient f32 policy once donor values recovered |
| Overlarge negative delta | abs(delta) > current SP changes negative delta to zero before clamp | owned affordability must precede debit |
| Reset | refill-shaped method `0x852840`; class method `0x852bf0` writes min(0,max) to SP | distinguish creation/death/rebirth/reset dispatch; do not label zeroing method death from body alone |

Relevant PRC labels: sp_max `0x0634ffda6c`, sp_recover_frame `0x100012301a`,
recover_sp `0x0a5a302e1e`, sp_recover_damage_mul `0x15db7b9842`,
sp_recover_shield_mul `0x1595084712`. Start=max is a measured assignment shape;
100, a passive rate, hit/shield multipliers and death/refill timing are NOT measured
values/events in this run. Native event recovery is not side-B-only. Translate
its filters/scaling; do not award from a persistent infliction flag every frame or
assume priced spells also grant mana without donor evidence.

## Shared state and current integration audit

Proposed owner: sibling `src/pgwr/plugin/src/mythra/hero_mana.rs`, accessible from
both forms, separate from move phase state. One eight-entry table with pair identity,
match/stock generation, current/max f32 bits, recovery counter/pause reasons, last
simulation-frame token, cast token and HUD layout generation. Gate selected entry
costume c06/c07, accept active eflame OR elight. Range-check entry 0..7; never use
battle-object ID as persistence key. Object IDs only validate current active ownership.

B source inspection: neutral `hero_neutral_b/mod.rs` has an elight-only target gate,
its own charge/flags table and unconditional generate. `fighter.rs::shoot_main`
clears phase flags; end clears charge. Its elight-only lifecycle repeatedly clears
charge/flags on DEAD/ENTRY. Preserve move semantics; none is a shared initialization
clock. Side `state.rs::get` also excludes eflame; `State::start` resets per-cast
flags/targets/counts on `fighter.rs::main_entry`. Attack MAINs assume success.
Place affordability in attack/SHOOT MAIN before motion/ACMD observes success, never
inside the spell-entry state reset. Current mana=off logs describe the shipped baseline.

Proposed APIs: begin_match, begin_stock, end_match, begin_cast/try_spend,
advance(game_frame,active_snapshot), record_damage(event_token,damage,shield),
snapshot_for_hud. Lifecycle generation guards make calls idempotent. Initialize/reset
only at recovered donor lifecycle boundaries. Repeated DEAD must not refill repeatedly;
ENTRY from swap/recreated subfighter must not create a new stock. End-match invalidates
identity so later reuse of the same entry does not inherit MP.

Advance for the active form throughout gameplay. First callback for
(match,entry,simulation_frame) advances once; duplicate Main on status change and
partner callbacks do not double-recover. Use a shared simulation-frame token, not
MotionModule::frame, status global_table[0xe], wall time or HUD render updates.
No locally resolved clock API/site yet: engineering gate, not user preference.
Preserve donor stop/hitstop/pause and counter ordering after recovery is completed.
Do not hold locks over engine calls. Damage event tokens prevent duplicate awards.
Swap preserves MP, counter phase and stock identity; active snapshots replace dormant
pointers. Reset MP/counter/cast tokens once per actual stock. HUD visibility on death
and rebirth is separate. Independent c06/c07 players retain independent state/panels.

## Actual HUD route and reserved-hook hand-back

Indexed resources: `ui/layout/info/info_melee/info_melee/layout.arc`
(arc_files.tsv:419943), `ui/param/info/hud_param.prc`. Candidate route: owned extension
of actual fighter HUD layout, not a new arbitrary directory.

**Corrected by T-0057 (2026-10-02): the layout has been extracted, and it already
contains the MP gauge.** `ui/layout/info/info_melee/info_melee/layout.arc`,
2,166,040 B, sha256 `c382a6e575e48102aff492fdc2bfd9c8a9cab6d9a0843b61224e4ab15e9c25c3`,
pulled from `gamedata/ssbu-13.0.4/data.arc` with `tools/arc-extract` and
byte-identical to the ArcExplorer copy. Named inside it:
`blyt/info_melee_lct_player_sp.bflyt` (instance `info_melee_lct_player_sp`); panes
`sp_00`..`sp_03` and `sp_bg`, `sp_bgC`, `sp_bgLT`, `sp_bgRT`;
`anim/info_melee_lct_player_00_sp.bflan`, `..._01_sp.bflan` and
`anim/info_melee_lct_player_sp_sp.bflan` with `_anim_in` / `_anim_loop` /
`_anim_out`; HUD events `MELEE_GAUGE_SP_GET` / `MELEE_GAUGE_SP_USE`; setters
`set_fxui_sp_get`, `set_fxui_sp_use`, `set_sp`, `set_sp_flash`.
So the "MP resources are not established" worry is gone and the route below
changes shape: **author no new pane subtree at all, drive the existing one.**
What is still unknown is what makes the game draw it for a c06/c07 entry, i.e.
the SP event the HUD consumes. `ui/param/info/hud_param.prc` is still not
extracted and is still wanted.
The old line about Hero wind-command textures is withdrawn as unhelpful rather
than wrong: the MP gauge is the resource, and it is named above.

New B trace: `../T-0046/{hud_xrefs.json,hud_dispatch.asm.txt,detail_native.asm.txt,lifecycle_hud_native.asm.txt}`.

| Callback/resource path | 13.0.4 evidence | Limit |
| --- | --- | --- |
| HUD update task registration | `0x13540e4` stores adapter 0x138a710 alongside HudManager::update string | task registration, not safe hook site |
| Task adapter | 0x138a710 bytes `080440f9000140f9bab70014` | manager load then tail-branch to 0x13b8600 |
| HUD update target | 0x13b8600 bytes `ff8302d1ea1300fde923036dfc6f04a9` | measured 16 bytes; full ABI not recovered |
| Match-start registration | 0x2271e48/0x2274c7c name notification pointing to 0x2256b00 | teardown not established |
| Match-start adapter | 0x2256b00 bytes `fd7bbfa9fd030091e2efcf97e0031f2a` | calls 0x1652a90 |
| UI component lookup | 0x1b6c004 references brave, calls 0x3777b30; handle stored in row-derived +0x688 | parent/row stride/type unresolved |
| Meter events | SP init/set event 0x5c; add event 0x5d; payload includes mapped player integer and SP float | native entry lookup +0x41e4/+0x41e8; consumer ABI unresolved |

Proposed route (D): copy/extend existing layout with owned pgwr_mana pane subtree
and dependencies, anchor to actual per-fighter panel. Use engine entry-to-panel
mapping, including reorder, teams and 1..8 players; do not hard-code 1..4 rectangles.
Only target pairs show gauge and numeric text; swaps retain identity. Match start/
layout recreation binds handles; HUD update reads immutable snapshots; teardown
invalidates handles before release. Never retain a pane pointer across layout
generation, death, player removal or rematch. No global HUD framework is authorized.

AGENTS.md rule 17: "If the proper route needs something reserved (raw-offset hook,
rebuilding a global framework plugin), stop and hand back with the evidence".
The 2026-10-03 user authorization covers project-owned native HUD integration. Clock and damage callbacks remain separate; prior projectile/article approvals did not authorize them.
Before subtask 6 implements any interception, its hand-back must name each chosen
entry/slot, full overwrite span/signature on the main hash above, ABI/register
preservation, original forwarding order, target-entry filter, overlap with existing
hooks, pointer guards, layout teardown and mismatch behavior. Mismatch disables
only this feature while leaving original routing intact. Plugin-local implementation
and owned assets only; protected framework files stay untouched.

These are measured candidates, not approval to intercept an unknown ABI. Full pane,
teardown, frame and damage hook contracts remain prerequisites. Do not copy an
offset from another game version.

T-0057 re-verified all four HUD/clock byte signatures on the 13.0.4 image and they
still MATCH, so the candidates are live; that is a statement about the bytes, not
an approval to intercept an ABI that is still unrecovered. The frame clock has no
in-bindings implementation at all - see the mana module's own docstring, which
states the limitation and the measurable consequence instead of hiding it.

## Indispensable input request and remaining gates

**Status 2026-10-02 (T-0057): items 1, 2 and 4a are closed; 3 and 4b are not.**

1. `fighter/brave/param/vl.prc` - **GOT.** sha256 `dafa43c6...`, from
   `gamedata/ssbu-13.0.4/data.arc` (`ef615e67...`). Six prices, max and recovery
   all measured; see the price table above and `../T-0057/`. The reason this was
   thought unavailable is a dead end, recorded in `../T-0057/SOURCE.md` §2: the
   ArcExplorer export has an **empty** `fighter/brave/param/`, and a file missing
   from that export is not missing from the game.
2. `prebuilt/nro/release/lua2cpp_brave.nro` - **GOT** (ArcExplorer export,
   sha256 `dc5edcde...`, equal to the pinned hash). Note for the record: Hero's
   SP code is in `main`, not in this NRO - offsets like `0x854610` are past the
   end of a 2.9 MB file.
3. `prebuilt/nro/release/lua2cpp_common.nro` - **still wanted** for the status /
   method mapping behind the HUD ABI.
4. `ui/layout/info/info_melee/info_melee/layout.arc` - **GOT** and the MP gauge
   is identified in it. `ui/param/info/hud_param.prc` - **still wanted**.

Current implementation boundary (2026-10-03):

* **HUD gauge**: no current source/package blocker. Explicitly authorized native calls are
  packaged under `hero-mana-hud`; native signature/structure checks pass (B), drawing,
  mapping and lifecycle remain unverified (D). No clock or HUD interception is installed.
* **Hit/shield recovery**: still not built. Damage-event ABI at `main+0x854610` /
  `0x854a4c` remains outside this task, behind disabled `hero-mana-reserved`.

The owned meter's existing active-Main-callback recovery counter is preserved; it is not
a shared simulation-frame clock. Hardware must check its rate through status changes.

## Manual checks for a future implementation (not run or queued)

1. Vanilla c00 Mythra/Pyra and real Hero controls: unchanged moves/HUD.
2. Target start/max; compare all six prices and selected-level failure against Hero;
   cancel charging and interrupt after debit. No repeated debit on inherited motion.
3. Compare idle regen, charge/pause, hitstop and hit/shield awards; log one advance
   per eligible simulation frame and one award per collision event.
4. Spend and swap repeatedly both directions; idle as each form: no refill or extra
   recovery. Stock loss/rebirth/rematch resets exactly at recovered donor points.
5. Both c06/c07 plus vanilla/real Hero: independent MP and correctly mapped panels
   in 2/4/8-player/team layouts; removal/layout recreation leaves no stale gauge.
   Return eventual feature log from boot.

Unverified: six numeric prices, passive values, all pause/failure timing, lifecycle
event identity, collision filtering, game clock, pane/teardown ABI and all gameplay.
