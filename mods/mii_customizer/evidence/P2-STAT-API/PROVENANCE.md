# P2-STAT-API - provenance

Task `P2-STAT-API`. Worker: Space Bunny Alpha. Date: 2026-10-04.
Paths are workspace-relative. Evidence tiers: **B** = measured offline from local
files by a script that still exists; **C** = read from pinned third-party source;
**D** = hypothesis. **No tier A.** Nothing was run in a game.

## Inputs read

| role | path | sha256 (first 16) | tier |
|---|---|---|---|
| common fighter params (the file both parameters live in) | `gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc` | `87fcf45c456d36d3` | B |
| reproducible Gunner catalogue (stat records) | `mods/mii_customizer/evidence/P1-DATASET/gunner_catalog.json` | `e210923b7a912b76` | B |
| old mod param bridge (implementation path A) | `mods/ssbu_mod_new/src/pgwr/plugin/src/params.rs` | `5171cc53d3f8c4b9` | C |
| old mod pinned `fighter_param` row field table | `mods/ssbu_mod_new/src/mgw_standalone/vendor/ssbu_clone_engine/clone_engine_core/src/fighter_param_row_table.rs` | `3ff0774d5e54184c` | C |
| old mod pinned per-object param copy declarations | `.../clone_engine_core/src/fighter_common_copies.rs` | `526479f0b560a9d7` | C |
| old mod pinned per-object param field table | `.../clone_engine_core/src/fighter_common_copies_table.rs` | `74e3a0f3fbfd0b8a` | C |
| old mod 13.0.4 smashline fork | `mods/ssbu_mod_new/src/mgw_standalone/smashline_1304/src/params.rs` | `9fd9f671c38b49f5` | C |

The full `fighter_param.prc` hash is
`87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2`, identical to
the one the coordinator measured independently on 2026-10-04 and to the one
P1-DATASET reported. The catalogue hash matches the value P1-DATASET published
(`e210923b7a912b760b3f5f76322640562c799a1c2042a55eeaf756e889a81081`).

## Pinned third-party sources actually read

These are cargo git checkouts already on this machine. Their revisions are the
ones the workspace's own `Cargo.lock` files pin, checked with `git rev-parse HEAD`:

| crate | repo | revision | role |
|---|---|---|---|
| skyline-rs 0.6.0 | `ultimate-research/skyline-rs` | `6b52d321275639f26c2371d8142550ba0013a5e4` | hook framework |
| skyline-smash 0.1.0 | `ultimate-research/skyline-smash` | `315e4e8bebb460ebb9f02f30f07b0f13883ba3d6` | lua2cpp declarations, `FighterParamTable` |
| smash-rs | `ultimate-research/smash-rs` | `ddacc5e19ccf8616783b6ad29265a99afd59e83b` | `WorkModule` vtable, `app::fighter` entry-id helpers |
| smashline 1.x | `HDR-Development/smashline` | `be3ef308ed8e479922da192a391e0684184af2af` | `FighterParamHolder` param override mechanism |

Revision provenance: `mods/ssbu_mod_new/builds/.cache/pikachu-airb/plugin/Cargo.lock`
pins `skyline#6b52d32…`, `skyline-smash#315e4e8…` and
`acmd-engine = smashline#be3ef30…`. The `smash-rs` checkout is present locally but
its revision is **not** pinned by that lock file, so `smash-rs` claims here are
tier C against a local checkout whose pin this task did not independently confirm.
Nothing was downloaded; no library was installed.

## Commands actually run

```sh
# the audit (59 checks, exit 0)
python -B mods/mii_customizer/evidence/P2-STAT-API/check_stat_api_sources.py

# determinism: a second run is byte-identical to the saved output
python -B mods/mii_customizer/evidence/P2-STAT-API/check_stat_api_sources.py > /tmp/run2.txt
diff -q /tmp/run2.txt mods/mii_customizer/evidence/P2-STAT-API/check_output.txt

# negative control: one wrong hash must fail loudly (exit 1)
python -B mods/mii_customizer/scratch/2026-10-04_P2-STAT-API/neg_control.py
```

Plus read-only greps over the pinned checkouts and the old mod tree, and
`git rev-parse HEAD` inside each checkout.

## Observed results

* `check_stat_api_sources.py`: **59 checks, 0 failing, exit 0**; full output in
  `check_output.txt`. A second run is byte-identical.
* Negative control (the `fighter_kind` row key perturbed by one bit) fails with
  `exactly one row carries fighter_kind_miigunner`, exit 1. The audit is not
  vacuously green.
* Independent re-decode of the `.prc`: 94 rows, exactly one row whose
  `fighter_kind` equals `hash40("fighter_kind_miigunner")`, at **index 82**;
  `weight` = `104.0` (`0x42d00000`), `walk_speed_max` = `1.0` (`0x3f800000`),
  both `float`. This reproduces P1-DATASET §4 without reading its JSON.
* The pinned old-mod row field table carries the same Hash40 for both names
  (`weight` at row offset `0x80`, `walk_speed_max` at `0x10`), inside a row of
  `0x628` bytes.
* The pinned per-object param field table (`fighter_common_copies_table.rs`,
  1238 entries over offsets `0x58`–`0x1a88`) lists **neither** parameter.

## What these results do not establish

* No game, emulator or console was run. No value was observed in a match.
* The audit reads source and file bytes. It proves where symbols and offsets are
  declared. It proves nothing about what the engine does with them at runtime.
* `smash-rs` is the one crate whose pin this task did not confirm from a lock
  file.