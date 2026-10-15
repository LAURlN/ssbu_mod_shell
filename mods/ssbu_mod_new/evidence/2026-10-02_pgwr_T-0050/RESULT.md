# T-0050: Little Mac forward-smash fist trails on G&W c06/c07

2026-10-02. Supersedes the same-day BLOCKED note below; see `DELTA.json` for the original
plan, which is unchanged. The installer section is in root `CURRENT_INSTALL.md`.

Evidence tier **B** for every byte-level claim here - each one was measured by a script in
`tools/` on named files with named hashes. **No console, no emulator, no game launch, no card
access.** Nothing below says the trail draws in game; the arcade question is a hardware check
and is listed in the installer section's manual tests.

## What was blocked, and what resolved it

The earlier T-0050 run stopped on two missing inputs. Both are now in hand:

1. **The vanilla recipient** `effect/fighter/eflame/ef_eflame.eff` - 11,371,400 B, sha256
   `24512f9a020f3a1b989bebb614314381a142d769570618fd71a786356c6682e3`. It is present in the
   export named by `paths.toml [dumps] arc` (`<ArcExplorer dir>/export`, read-only for
   this task, never written, never copied into the project tree). This is the file T-0033
   asked for in `dumps/MISSING.md`.
2. **The effect converter.** The pinned source was missing, and the prebuilt binary was gone.
   Resolved from the open-source repository rather than from a binary: the commit the mod
   already pinned, `d5491138d645221ec92189eeff3ded8c43fd0a1a`, is exactly the current HEAD of
   <https://github.com/KillzXGaming/EffectLibrary> (MIT). It is now cloned to
   `refs/brave_special_n/effect_library/` (tree sha256 `fcba90ba8938515b50e303eaedf930a909d22a2c2a1a446b910ae2d9acbe66f2`)
   and `tools/fetch_effect_library.py` reproduces and verifies that state offline.
   `tools/build_hero_effect_converter.py` v1.1.0 gained `--from-source`, which compiles the
   patched pinned tree with the machine's .NET 8 SDK into `builds/.cache/hero_effect_converter/bin/`.
   The source copy, `obj/`, `bin/` and the NuGet package folder are all under `builds/.cache/`;
   nothing was installed system-wide.

   `EffectConverter.exe` `033ddc923fb3e0282df76fcccb1957bcf4834665c5aa000b9f4947a81d97e5f2`,
   `EffectLibrary.dll` `ebd94ba49c7898f1287e94abd266f55e4528882e8448e3ad7f0734077b410a94`.
   These are **not** the 2026-09-30 binaries (`e759d575…` / `62504e48…`); a different compiler
   and a different link route. The pinned *preservation patches* are byte-for-byte the same
   ones `--check` has always verified, and the merge re-export check below is the same
   assertion the Hero merges passed.

   One source edit beyond those patches: upstream `EffectConverter/Program.cs` does not
   compile, because it uses `PtclFile` (namespace `EffectLibrary.EFT2`) without importing it.
   The original relink route never noticed - it compiled only `EffectLibrary.dll` and reused a
   prebuilt converter executable. A single added `using` is the whole fix, and it is recorded
   in `builds/.cache/hero_effect_converter/MANIFEST.json`.

## A defect this task found, which would have shipped silently

T-0033 flagged that the Little Mac emitters "have not been checked against" the merge's
`ExternalModelFlag` / `Variants` assertion and that the donor bank contains one embedded
G3PR/GRTF pair. Checked: both requested emitters have `ExternalModelFlag = 0` and empty
`Variants`, so no external model is needed.

The G3PR pair turned out to be a much bigger problem than the assertion.

`merge_hero_neutral_b_effects.py` relocated colliding **texture** ids and nothing else. But
`LITTLEMAC_ATTACK_ARC` ships a model whose G3PR descriptor id is `1347192488`, and
`effect/fighter/eflame/ef_eflame.eff` already uses that same id for a *different* Pyra mesh
(`P_EflameNovaRing/ArcAlpha/1347192488.bfres`, ten emitter sets, different bytes).
`PrimitiveInfo.AddPrimitive` (pinned source, `FileData/EFT2/Primitives.cs` line ~302) opens
with

    var descPrimIndex = PrimDescTable.Descriptors.FindIndex(x => x.ID == id);
    if (descPrimIndex != -1)
        return;

- it returns without a word. So the merge would have completed, passed every check it had,
and shipped a bank in which the forward-smash arc draws **Pyra's mesh**. That is exactly the
"animates, hits, but something else is drawn" failure class, and no offline check in the
repository would have caught it.

`merge_hero_neutral_b_effects.py` is now v1.2.0:

* `.bfres` model ids are relocated exactly like `.bntx` texture ids, with the same
  reject-on-different-payload rule and a deterministic new id.
* The model's own name is relocated too (`pgwr_hero_<newid>`) with a new `HeroModelRename`
  helper. Two reasons: the pinned primitive-writer patch suffixes a duplicate model name with
  its id, which is load-bearing but makes the re-export unpredictable; and renaming in place
  leaves the old name in the container's cached name table, so the helper builds a fresh
  single-model container using the pinned dumper's own container literal. The helper proves
  that every other model field - bones, vertex buffers, indices, materials - is unchanged.
* Only the three fields that actually name a model are rewritten
  (`ParticleData.PrimitiveID`, `ParticleData.PrimitiveExID`, `ShapeInfo.PrimitiveIndex`);
  an integer that merely happens to equal an id is not touched.

## What was measured

Merged with `tools/merge_hero_neutral_b_effects.py` (donor-parameterised, as T-0050 prepared)
and driven by `tools/build_littlemac_fsmash_effect.py` v2.1.0, which is the same call
`src/pgwr/build.py` makes.

| measurement | value |
|---|---|
| slot bank `ef_eflame_c06.eff` | sha256 `6ab84bb729d89e25a0a513a3036e9748049642d56c9317c785344521fc373abc` |
| slot bank `ef_eflame_c07.eff` | sha256 `6ab84bb729d89e25a0a513a3036e9748049642d56c9317c785344521fc373abc` |
| vanilla eflame emitters preserved | 95 of 95, 0 lost |
| emitters added | exactly `LITTLEMAC_ATTACK_LINE`, `LITTLEMAC_ATTACK_ARC` |
| texture id relocations | 0 |
| model id relocations | 2 x `1347192488` -> `95091467`, name `pgwr_hero_95091467` |
| `effect/fighter/littlemac/ef_littlemac.eff` | removed from the staged tree (`c2f33cdb…`), pinned donor kept in `refs/` |
| re-export check | every decoded emitter field, opaque subsection and geometry/texture/shader payload byte-identical after packing and re-reading the bank |

The two slot banks are byte-identical to each other. That is expected and harmless: One Slot
Effects renames each entry per slot, so the same content in two files is the normal shape.
It differs from the Mythra `ef_elight_c0{6,7}.eff` pair only because that merge had to
relocate a texture for the gold theme.

`tools/audit_littlemac_fsmash.py` is v1.2.0. `check_effect` now asserts the new layout, and
asserts what the old one missed: that each slot bank **kept all 95 vanilla emitters**, so a
bank that replaced rather than merged cannot pass. Two negative controls, both run:

* the packaged 0.20.16 tree -> refuses, "ef_littlemac.eff is still shipped";
* a slot bank replaced by the vanilla bank -> refuses, "lacks emitter LITTLEMAC_ATTACK_LINE".

`tools/effect_trail_inventory.py`, before and after, on the staged tree
(`inventory_before.json`, `inventory_after.json`, with 0.20.16 as the shipped reference
`inventory_shipped_0_20_16.json`, all three beside this file):

    0.20.16 (shipped):  eflame: banks []          littlemac: banks ['ef_littlemac.eff']
    after:             eflame: banks ['ef_eflame_c06.eff', 'ef_eflame_c07.eff']
                                              littlemac: banks []

Plugin: compiles. `CARGO_TARGET_DIR=builds/.cache/pgwr-fb-1-littlemac-fist-trails-target
cargo skyline build --release --features snake-neutral-b,hero-side-b -- --offline` finished
with no errors (warnings only, all in another agent's `hero_side_b/state.rs`). The built NRO
contains `effect_attacks4`, `effect_attacks4hi`, `effect_attacks4lw`, `littlemac_attack_line`
and `littlemac_attack_arc`. **No Rust source changed for this task** - the ACMD was already
correct; only the bank it resolves against was wrong.

## What is still unverified, and why

* **Everything about behaviour** (tier D). No console, no emulator, tests benched by the
  user's standing decision. Whether the line and both arcs draw, whether the arc mesh is now
  Little Mac's rather than Pyra's, whether the angled motion kinds are requested at all on
  this recipient, and every appearance judgement are hardware questions.
* **The full `src/pgwr/build.py` run.** Attempted and it stops for an unrelated, pre-existing
  reason: `dumps/arc` does not exist in this checkout and `src/pgwr/tools/build_chrom_jab.py`
  hard-codes that path instead of honouring `MGW_EXPORT`
  (`FileNotFoundError: dumps\arc\fighter\chrom\motion\body\c00\motion_list.bin`). The Snake
  feature additionally needs donor clips the ArcExplorer export does not carry. So the merge
  was verified by running the exact call `build.py` makes, with the exact arguments, and the
  wiring in `build.py` was read rather than executed end to end. **The installer must run
  step 4 of the procedure in `CURRENT_INSTALL.md`; it is the first thing that has not been
  run here.**
* `check_baseline` and `check_handlers` as a whole-package audit, for the same reason: they
  need a finished package. `check_effect` was run directly on the staged tree.
* The four donor ACMD dumps that T-0033 listed as unpinned are still not on disk, so the
  transcription in `plugin/src/acmd/littlemac_attack_s4.rs` still cannot be re-verified
  against the donor's own text. This is unchanged by the fix, which touches no ACMD.

## Dead ends worth keeping

* **Rebuilding the converter with `csc` against a prebuilt `EffectConverter.exe`**
  (`toolchain.effect_converter` / `roslyn_csc`) is not recoverable: both `paths.toml` entries
  are empty and no such binary exists anywhere in the tree. The SDK route replaces it and needs
  only the pinned sources.
* **Relocating the model id by renaming the `.bfres` file alone** re-exported to a *different*
  model: the pinned primitive-writer patch renames a duplicate model name to `<name>_<id>`, so
  the staged file and the re-read bank disagreed. Renaming the model up front, into a fresh
  container, is what makes the round trip exact.
* **Building a fresh `ResFile` by copying the header fields read back from the file** produced
  a 30,056 B container where the bank holds 33,640 B: `Alignment` and `DataAlignment` are not
  round-tripped by the reader. The dumper's own container literal is the only correct source
  for them.
* **Copying the model container's alignment into the payload comparison** is not possible for
  the same reason; those three container fields are excluded from the helper's field
  comparison, and everything else - the whole model - is compared.

## Files

Evidence beside this report: `fist_effect_merge_record.json` (the tool's own record for both
slots), `audit_check_effect.json`, `inventory_before.json` / `inventory_after.json` /
`inventory_shipped_0_20_16.json`, `effect_library_provenance.json` (repo, commit, licence,
content tree hash), `converter_build_manifest.json` (pinned source, every binary's sha256,
the one added `using`).

Changed: `tools/merge_hero_neutral_b_effects.py` (1.2.0),
`tools/build_littlemac_fsmash_effect.py` (2.1.0),
`tools/build_hero_effect_converter.py` (1.1.0, `--from-source` route),
`tools/audit_littlemac_fsmash.py` (1.2.0, `check_effect`).
New: `tools/fetch_effect_library.py`, `refs/brave_special_n/effect_library/` (pinned clone).
`src/pgwr/build.py` needed no change: its `littlemac_s4_eff.build(...)` call and its
`add(slot, 'effect/fighter/eflame/ef_eflame_{slot}.eff')` declarations arrived with T-0050 on
`lab/T-0050` and are already in the working tree (`git diff ffba235` is empty for all three
T-0050 files; only CRLF line endings differ on disk).
