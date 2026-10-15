# T-0033 - Finding 1: why the Little Mac forward-smash fist trail is absent

Owner: task T-0033 (research child of T-0035). Date: 2026-10-01. Evidence tier: **B** for every
byte-level claim below (all measured from files in this tree with
`tools/effect_trail_inventory.py` and the scripts named in the text). **Nothing here is a claim
about what the console draws**; there is no hardware run in this task.

## Verdict in one line

The two donor emitter calls are already in the ACMD and they are correct, but the bank that
*holds* those emitters is shipped into **another fighter's effect folder**
(`effect/fighter/littlemac/ef_littlemac.eff`), so the fighter that plays the move - `eflame`
(Pyra/G&W c06/c07) - never loads them and the calls are silent no-ops. Do **not** add a generic
`sys_*` slash: that would replace the donor's fist trail with a common effect rather than porting
it, which is the stand-in shape `AGENTS.md` rule 17 forbids.

## The three links in the chain, each measured

1. **The ACMD calls the donor's own emitters** (tier B, source read).
   `plugin/src/acmd/littlemac_attack_s4.rs`:
   - `effect_attacks4` line 154: `EFFECT_FOLLOW(agent, Hash40::new("littlemac_attack_line"),
     Hash40::new("top"), -1, 8.5, -10, 0, 4, 0, 1.05, false)` at frame 13.
   - `effect_attacks4hi` line 263: `EFFECT_FOLLOW(... "littlemac_attack_arc" ...)` + `LAST_EFFECT_SET_RATE(1.5)`
     at frame 13, `EFFECT_OFF_KIND("littlemac_attack_arc")` at frame 18.
   - `effect_attacks4lw` lines 376-387: the donor's `SO_VAR_FLOAT_LR` branch, two arc poses,
     `LAST_EFFECT_SET_RATE(1.4)`, `EFFECT_OFF_KIND` at frame 21.
   All 15 handlers are registered at `Priority::High` for `Agent::new("eflame")` with
   `TARGET_COSTUMES`, lines 487-517.

2. **The emitters exist, in the donor bank, and the mod ships that bank byte-exact** (tier B).
   `refs/littlemac_attack_s4/arc/effect/fighter/littlemac/ef_littlemac.eff`,
   13,795,840 B, sha256 `c2f33cdb2157be04d80940182aced6ae762c004f9b08ea4ec3929749ea2b2228`,
   44 emitter names parsed from the EFFN prefix, including `LITTLEMAC_ATTACK_LINE` and
   `LITTLEMAC_ATTACK_ARC` (both also present in `dumps/scripts/ParamLabels.csv` as
   `littlemac_attack_line` = `0x152ba1d378` and `littlemac_attack_arc` = `0x14c5bcbe8d`, so the
   *names* are engine-known and resolve fine). The packaged copy at
   `builds/pgwr/0.20.16/ultimate/mods/pyra_gamewatch_reskin/effect/fighter/littlemac/ef_littlemac.eff`
   hashes identically to the pinned donor. The bank has one embedded `G3PR` (model) and one
   `GRTF` (texture) section.

3. **No fighter that plays this move ever loads that bank** (tier B, the decisive link).
   - `tools/effect_trail_inventory.py` over the packaged tree reports
     `effect/fighter/eflame/` holds **no `.eff` bank at all** (only `trail_c06/`, `trail_c07/`),
     and `effect/fighter/littlemac/ef_littlemac.eff` is loaded, if anything, by the **Little Mac**
     fighter kind (`bank_loader_fighter: littlemac`), never by `eflame`.
     Inventory: `T-0033/fist_trail_inventory.json`.
   - The acceptance rule is in the pinned One Slot Effects source,
     `src/pgwr/tools/one_slot_effects_reference.rs` `check_extension_eff_inline_hook` (main+
     0x355f66c, lines 299-341): while loading a fighter's effect bank the game walks the entries
     of `effect/fighter/<fighter>/` and **only accepts the file whose name hash is
     `ef_<fighter>.eff`, or `ef_<fighter>_c<slot>.eff` when that slot has a one-slot bank**.
     Anything else in that folder is rejected. A bank in *another* fighter's folder is not even
     searched, because the search directory is the requesting fighter's own folder
     (`fighter_lookup_effect_folder`, main+0x60bf1c).
   - Consequence: Pyra's emitter resolution happens against the base game's
     `effect/fighter/eflame/ef_eflame.eff` (that path exists in the shipped ARC index,
     `dumps/decoded/arc_files.tsv:435767` shows `effect/fighter/littlemac/ef_eflame.eff` ->
     littlemac; the eflame bank is likewise listed as `effect/fighter/eflame/ef_eflame.eff`).
     That bank contains no `LITTLEMAC_ATTACK_LINE`, so `Hash40("littlemac_attack_line")` does not
     resolve and the call produces no emitter - the "animates, hits, but nothing extra is drawn"
     shape that `AGENTS.md` section F warns about.

## Two packaging defects that must be fixed with it (tier B)

Both come from `build.py::build_config_json` line 1339:

```python
add('c06', 'effect/fighter/littlemac/ef_littlemac.eff')
```

* `add()` appends the path to `declared['fighter/eflame/c06']`. A file that lives in
  `effect/fighter/littlemac/` is therefore declared as a new file of the **eflame c06 costume
  group**. That is at best inert (the group loader never looks there) and at worst an
  inconsistent ARCropolis entry.
* `add()` guards with `require(not (EXPORT / path).exists())` - "not a base-game file". That guard
  passed only because the local export is partial: `effect/fighter/littlemac/ef_littlemac.eff`
  **is** a base-game file (`dumps/decoded/arc_files.tsv:435767`), it is simply absent from the
  on-disk `dumps/arc` tree. So the mod, as packaged, declares a *duplicate* of a real ARC path.
  The same guard would have caught it if the export were complete. **This is a latent trap for
  every `add()`-based declaration**: absence from `dumps/arc` is not evidence of a new file.

Also note the donor-bank copy is **13.8 MB for two emitters**, and the audit
`refs/littlemac_attack_s4/audit_0_20_16.json` only asserts
`/effect/sha256 = c2f33cdb...` and that the emitters are inside those bytes. It never checks that
the recipient's bank contains them - which is why this passed every offline gate.

## Smallest owned-resource fix

Give the *recipient* its own per-costume bank that contains the two emitters, and delete the
cross-fighter declaration. Concretely:

1. **Build `effect/fighter/eflame/ef_eflame_c06.eff` and `ef_eflame_c07.eff`**: a byte copy of the
   base game's `ef_eflame.eff` with `LITTLEMAC_ATTACK_LINE` + `LITTLEMAC_ATTACK_ARC` merged in.
   This is exactly the shape that already ships and works for Mythra
   (`effect/fighter/elight/ef_elight_c06.eff`, 128 emitters, 13,690,448 B; see
   `builds/pgwr/0.20.16/generated_effects/ef_elight_c06.merge.json` where the recipient was the
   Mythra skin bank `e15f8380...` and the donor `ef_brave.eff`). One Slot Effects then serves it:
   `get_raw_eff_data` renames each entry to `<name>_c<slot>` and `get_new_effect_name` rewrites
   the ACMD's `littlemac_attack_line` request to `littlemac_attack_line_c06`
   (`one_slot_effects_reference.rs` lines 420-499 and 576-648). c00-c05 keep vanilla
   `ef_eflame.eff`, which is the costume gate `AGENTS.md` rule 18 wants.
   Do **not** ship a replacement `ef_eflame.eff`: that would change Pyra's vanilla slots.
2. **Declare** `effect/fighter/eflame/ef_eflame_c06.eff` under `fighter/eflame/c06` and
   `..._c07.eff` under `fighter/eflame/c07` (one per slot - they are different files, so the
   "declared once" comment at build.py:1333-1338 does not apply).
3. **Remove** `add('c06', 'effect/fighter/littlemac/ef_littlemac.eff')` and the
   `littlemac_s4_eff.build(MOD)` call, or repoint that tool at the merge. Keep the pinned donor
   in `refs/` as provenance; it stays the merge *donor*.
4. The ACMD needs **no change**: the emitter names, the bone (`top`), the rates, the arc's
   `EFFECT_OFF_KIND` frames and the `SO_VAR_FLOAT_LR` branch are already the donor's.

Rejected alternatives, with reasons:

* *Rename the donor file to `effect/fighter/eflame/ef_eflame_c06.eff`.* Accepted by the loader,
  but it would replace **all** of Pyra's effects for c06/c07 with Little Mac's 44 emitters -
  every G&W prop, Pyra sword and `sys_*` companion that the mod relies on. Not acceptable.
* *Give each slot its own one-slot eflame bank only for the angled variants.* Same as (1); the
  neutral `attack_s4` needs `LITTLEMAC_ATTACK_LINE` from the same bank, so there is no smaller
  variant.

### Precise missing inputs

| what | why it is needed | where it comes from |
|---|---|---|
| **`effect/fighter/eflame/ef_eflame.eff`** (the vanilla eflame bank) | **RESOLVED 2026-10-02** (T-0050). Present in the export named by `paths.toml [dumps] arc`, 11,371,400 B, sha256 `24512f9a020f...`. Read-only; never copied into the project tree. | resolved |
| the EffectConverter (`paths.toml toolchain.hero_effect_converter` = `builds/.cache/hero_effect_converter/bin/EffectConverter.exe`) | **RESOLVED 2026-10-02** (T-0050, see `evidence/2026-10-02_pgwr_T-0050/RESULT.md`). The pinned source is the public MIT repo KillzXGaming/EffectLibrary at that exact commit; `tools/fetch_effect_library.py` fetches and verifies it and `build_hero_effect_converter.py --from-source` compiles it into `builds/.cache/`. The `ExternalModelFlag` / `Variants` assertion **passes** for both emitters (measured, tier B). | resolved |
| a donor-parameterised merge | `merge_hero_neutral_b_effects.merge()` hard-codes the Hero donor and `required()` from `refs/brave_special_n`. A Little Mac variant is a ~20-line change (take `LITTLEMAC_ATTACK_LINE`/`LITTLEMAC_ATTACK_ARC`, donor `ef_littlemac.eff`) or a sibling tool. | `tools/` in this repo |
| the four donor ACMD dumps (`AttackS4.txt`, `AttackS4Charge.txt`, `AttackS4Hi.txt`, `AttackS4Lw.txt` of `lua2cpp_littlemac`) | `refs/littlemac_attack_s4/SOURCE.json` cites them as the transcription source, but they are **not on disk and not pinned under `refs/`** (`dumps/scripts` holds only `ParamLabels.csv` and `gamewatch_motion_list.yml`), so the transcription in the ACMD cannot be re-verified offline. | `tools/fetch_arc_files.py` cannot fetch these (they are a GitHub dump, not ARC); they must be copied from the user's dump repo into `refs/littlemac_attack_s4/acmd/` |

## What stays unverified

* **Added 2026-10-02 (T-0050).** The two inputs this finding was blocked on are resolved and
  the merge has since run; the fix it prescribed is built and measured
  (`evidence/2026-10-02_pgwr_T-0050/RESULT.md`). Two things this finding did not anticipate
  and that are now on record: the donor emitters carry **no** external model or variants
  (measured), and the merge as written at the time would have produced a bank drawing the
  **wrong mesh**, because a G3PR descriptor id collides silently - see `handbook/graveyard.md`
  R-EFF-MERGE-1. Corrected in `merge_hero_neutral_b_effects.py` 1.2.0.
* Whether the emitter draws at runtime - that is a hardware check (below).
* Whether the angled `attack_s4_hi` / `attack_s4_lw` kinds are even requested by the engine on this
  recipient (already tier D from the 0.20.15/0.20.16 work; unchanged by this finding).

## Manual checks for the user (in game, 1-2 minutes each)

1. **Neutral f-smash, both facings.** Pyra c06: forward-smash right, then left. A thin
   *white/grey straight line* should draw from the fist at ~frame 13 and last as long as the
   punch. Currently: nothing extra. Pass = the line appears in both facings; it is the donor's
   line, not a white flash.
2. **Up-angled f-smash** (forward + up). A curved *arc* should sweep and then retire about frame
   18 (it must not linger). Both facings.
3. **Down-angled f-smash** (forward + down). Same arc, different arc path, retiring ~frame 21.
   Facing right vs left must use the two *different* arc poses (the `SO_VAR_FLOAT_LR` branch) - if
   both facings look identical, the branch is not running.
4. **Negative control:** hold an item and f-smash - the item must stay hidden and the trail must
   still appear (this is `ItemModule::set_have_item_visibility`, unchanged by the fix).
5. **Vanilla control:** Pyra c00 / Mythra c00 f-smash must look exactly as it does today (no
   Little Mac arc, no missing G&W effects). This is the check that the per-costume bank did not
   leak into the vanilla slots.
6. If the angled variants still do not appear, that is the separate tier-D question from
   0.20.15/0.20.16 and this fix does not change it - report it as such rather than as a
   regression.
