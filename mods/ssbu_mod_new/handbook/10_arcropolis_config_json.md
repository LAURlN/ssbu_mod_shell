# ARCropolis config.json

Tiers: **A** hardware-confirmed (console or decoded crash report) - **B** measured offline by a script that still exists - **C** read from pinned third-party source - **D** hypothesis. Anything without a tier below is A/B unless marked otherwise. Paths in the source column refer to the *old* workspace (`modpack_test_1`); the same material now lives under `projects/*/history/`, `dumps/` and `evidence/`.

- Keys `new-dir-infos` (JSON array of path strings), `new-dir-infos-base` (map), `new-dir-files`, `share-to-vanilla`, `share-to-added`. Processing order (source): reshare -> new dirs -> add missing files -> unshare -> new-dir-files. `.prc`, `.nuanmb`, `motion_list.bin` are eligible added files. (C, ARCropolis `fs.rs`)
- Fighter files load **per costume group** (`fighter/<f>/c0N`); add article files to the existing group via `new-dir-files`. Inventing new dir-infos gave `Cannot get file info range for 'Unknown'` + Data Abort 0x20 in `fighter_initialize_object_data`. Supplying a `new-dir-infos-base` guess made it *worse* (startup crash `d4200020` in arcropolis). Working template = the standalone clone pack config. (A)
- A message that also appears in known-good logs is benign (`File discovery collected path '.../config.json' but it does not exist`). Run the good pack as a control before trusting an alarming line. (A)
- Root-HANDOFF Monkey Flip failure = mod with **no** config.json at all; it is not evidence about the file-add route.
- **An effect bank is only reachable by the fighter whose directory holds it** (2026-10-01, B:
  `tools/effect_trail_inventory.py`; One Slot Effects `check_extension_eff_inline_hook`,
  main+0x355f66c). Inside `effect/fighter/<fighter>/` the loader accepts only
  `ef_<fighter>.eff`, or `ef_<fighter>_c<slot>.eff` when that slot has a one-slot bank, and it only
  ever searches the *requesting* fighter's folder. So filing a donor bank under
  `effect/fighter/<donor>/` ships 13 MB that nobody loads, and the ACMD calls into it are silent
  no-ops - the "animates and hits, nothing extra is drawn" shape. Port a donor emitter by merging
  it into the recipient's bank (`tools/merge_hero_neutral_b_effects.py`), never by shipping the
  donor's file. Live example and fix: `refs/littlemac_attack_s4/T-0033/FIST_TRAIL_FINDING.md`.
- **`new-dir-files` is group-scoped, and "not in dumps/arc" is not "not in the game"**
  (2026-10-01, B). `build.py`'s `add(slot, path)` appends to the *group's* list, so a path under a
  different tree (`effect/fighter/littlemac/...` declared under `fighter/eflame/c06`) is at best
  inert. Its guard `require(not (EXPORT / path).exists())` is only as complete as the local export:
  `dumps/arc` is partial or absent, so it passed for a file that **does** exist in the base ARC
  (`dumps/decoded/arc_files.tsv` proves it). Check the ARC index, not the export, before treating a
  path as new.
- **Trail textures are resolved by the NUTEXB footer name, and one-slot plugins rename it**
  (2026-10-01, B/C). `get_raw_nutexb_data` (main+0x355ff00) rewrites the loaded trail's internal
  name to `<NAME>_C<slot>` and maps the original name to it per slot, which is why both slots can
  ship files called `tex_cloud_sword1.nutexb`. Two files in one slot folder with the same internal
  name therefore become two registrations of one resource, and a file whose name matches no
  `ParamLabels.csv` entry can never be requested at all. Inventory and cleanup:
  `refs/cloud_attack_air_f/T-0033/CLOUD_TRAIL_FINDING.md`. T-0054 (2026-10-02, B) stages one file per internal name (file name == footer name) for eflame c06/c07: `refs/cloud_attack_air_f/T-0054/RESOURCE_OWNERSHIP.md`; hardware effect unverified.

- **T-0050 merge executed (2026-10-02, B for bytes, D for behaviour):** Little Mac's fist
  emitters are now merged into recipient-owned `effect/fighter/eflame/ef_eflame_c06.eff` and
  `..._c07.eff` (sha256 `6ab84bb729d8…`, 95 vanilla emitters kept, 2 added) and the
  donor-folder bank is no longer shipped. Two generalisable facts:
  - **Model ids collide exactly like texture ids, and the collision is silent.**
    `PrimitiveInfo.AddPrimitive` returns without a word when a G3PR descriptor id is already
    in the table, so a donor emitter that shares an id with the recipient's *different* mesh
    merges "successfully" and draws the wrong model. `merge_hero_neutral_b_effects.py` 1.2.0
    relocates `.bfres` ids and names alongside `.bntx`, rewriting only
    `ParticleData.PrimitiveID`, `ParticleData.PrimitiveExID` and `ShapeInfo.PrimitiveIndex`.
  - **A `.eff` bank is not a text format you can edit; round-trip it or do not trust it.**
    Renaming a model in place leaves the old name in the container's cached name table, and
    `Alignment`/`DataAlignment` are not round-tripped by the reader, so a hand-built
    container is not the file the dumper would have written. The repaired converter plus a
    re-export field-by-field comparison is what makes the merge checkable at all.
  Evidence and both negative controls: `evidence/2026-10-02_pgwr_T-0050/RESULT.md`.
  Behaviour on hardware is **unverified**; the full `build.py` run is still outstanding because
  `dumps/arc` does not exist in this checkout and `src/pgwr/tools/build_chrom_jab.py`
  hard-codes that path instead of honouring `MGW_EXPORT`.
- **The pinned effect converter can be rebuilt from source (2026-10-02, C).**
  `EffectLibrary` / `EffectConverter` at `d5491138d645221ec92189eeff3ded8c43fd0a1a` is
  <https://github.com/KillzXGaming/EffectLibrary> (MIT), fetched and verified by
  `tools/fetch_effect_library.py`, compiled project-locally into `builds/.cache/` by
  `tools/build_hero_effect_converter.py --from-source`. Upstream `Program.cs` does not compile
  on its own (missing `using EffectLibrary.EFT2;`); the tool adds that one line. A lost
  prebuilt converter binary is therefore never again a reason to skip an effect merge.
- **Re-theming a merged donor emitter set: colour lives in three places, one of them a texture
  (2026-10-03, B: `tools/customize_lucas_ness_effects.py` on `ef_elight_c06/c07.eff`
  `fcdd6caa49b5...` / `1734bb5443e2...`).** Constant `ParticleColor.Color0/1`, the live
  `EmitterStatic.Color0/1` keys (type `Animated8Key`, or `3` = random pick among keys at time 0),
  and - for emitters with `ColorCombinerProcess` 1 and white constants - the texture itself
  (`ef_lucas_flash00`, `ef_ness_flash00`). Recolouring only the constants leaves those sprites
  in donor colours. Texture ids are bank-global, so re-hue a texture in place only after
  measuring that no other set samples it (the shared `3332780892` / `3167451124` masks are
  greyscale and need nothing). The pinned converter reproduces these banks byte-for-byte when
  nothing is edited, which makes a raw-byte diff an independent preservation check. How it looks
  in game is unverified (D). Record: `evidence/2026-10-03_pgwr_lucas_ness_effect_theme/RESULT.md`.
