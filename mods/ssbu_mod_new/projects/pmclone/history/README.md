# Pyra & Mythra independent clone

**INCOMPLETE: no playable character slot yet. The private-module loader passed
its console test on 2026-09-28 after the user moved the runtime into Skyline's
plugins folder. Do not install `editable/` as a mod.**

Target: one additional selectable transforming pair, eight costumes, copied
character assets and character-specific functions. General game engine services
remain shared. Originals and clone must coexist.

Start with [HANDOFF.md](HANDOFF.md) for the current checkpoint, exact build
commands, external inputs, next milestones and acceptance criteria.
See [DUMP_REQUEST.md](DUMP_REQUEST.md) for the current missing dump list and
reproducible ExeFS verification procedure.

## Project contents

- `editable/fighter/cflame`, `clight`, `clement`: independent copies of Pyra,
  Mythra and Element resources. All eight costume folders are included.
- `editable/camera`, `effect`, `sound`, `ui`: separate character-resource copies.
- `editable/prebuilt/nro/release`: separate copies of all three character
  modules, retaining the original embedded symbols as clean input binaries.
- `native/modules`: generated copies with unique module/factory names and rebuilt
  SysV/GNU ELF hash tables. Executable instructions and relocations are preserved.
- `runtime`: compiled Skyline loader. It verifies file hashes, allocates separate
  images/BSS, waits for required imports, checks factory addresses fall inside
  the private executable images, and blocks factory access until character-specific
  native imports have private implementations. The rebinding interface is present
  but not connected to completed native copies yet.
- `test_output/PyraMythra_private_module_loader_check.zip`: console loader check
  only, with install/removal instructions. No fighter or gameplay hooks.
- `native/main-functions`: bytes and disassembly of 22 directly imported
  character-specific functions in main. These are research inputs, NOT
  relocatable or registered implementations.
- `native/class-functions`: raw snapshots of 143 candidate native method roots
  across 17 fighter/article classes, bounded using the main executable's unwind
  records. Dependencies are audited, not assumed closed or executable.
- `reference/acmd`, `reference/shared`: 924 vanilla script references and eight
  shared database snapshots, for future private behavior/row implementations.
- `upstream/clone_engine`: clean upstream 0.4.0-beta.1, commit
  `a2c8cea7df4eedab7364979aa2c8ace2ba5446cf`. No earlier experimental patches.
- `reports`: hashes, missing-resource inventory, motion-reference checks,
  native imports/relocations and extraction status.

Copied files are regular independent files, not hardlinks or symlinks. NTFS
compression was enabled on the new project to reduce disk use. Existing dump
files were not overwritten; network extraction added missing files to `../export`.
The provisional clone names have NOT been registered as game kinds.

## Acquisition history and current reports

C: temporarily reached zero free bytes. The user freed roughly 27 GB and
extraction resumed. `reports/recovery.json` is a historical recovery record,
not the current completion status. One interrupted audio file was preserved in
`reports/interrupted-files` and fetched again. Report writes are now atomic so
a failed write cannot truncate the last complete report.

Consult `reports/summary.json` for current asset counts and unresolved motion
references, and `reports/assets.json` for per-file hashes. None of the earlier
mod directories were deleted to make room. Even a complete filename inventory
does not make this a playable mod; the runtime work below remains necessary.

## Reproduce preparation

Run from the workspace root with Python 3.8+:

```powershell
python pyra_mythra_clone/tools/prepare.py
python pyra_mythra_clone/tools/extract_missing.py
python pyra_mythra_clone/tools/prepare.py
python pyra_mythra_clone/tools/audit_native.py
python pyra_mythra_clone/tools/snapshot_references.py
python pyra_mythra_clone/tools/namespace_modules.py
python pyra_mythra_clone/tools/inventory_native_classes.py
```

Build the loader from `pyra_mythra_clone/runtime` using `cargo skyline build
--release`, then run `tools/package_loader_check.py` from the project/workspace.
`runtime/Cargo.lock` pins its resolved dependencies. The loader check's required
console evidence is documented in the ZIP's `START_HERE.txt`.

The packager also publishes directly into `../mod_output/new_standalone`.
The runtime belongs at
`atmosphere/contents/01006A800016E000/romfs/skyline/plugins/plugin.nro`,
with the three private modules under `ultimate/mods/PyraMythraClone/native/modules`.
The initial packager incorrectly put the runtime in the mod folder. Console
evidence is saved at `reports/console-loader-2026-09-28`: all four NRO hashes
match, all 27 private factories resolved, and all three isolation guards passed.
This verifies module loading only; factories were not called and no fighter
was registered. SD access while collecting this evidence was read-only.

The default archive index is the existing vanilla filename index in
`mod_files/mgw_standalone/vendor/clone_pack_workbench/arc_index/arc_files.tsv`.
This is input data only, not an import of the earlier mod implementation.
Pass `--index` and `--export` to use other locations. Its SHA-256 is recorded.

Close Arc Explorer while extracting and keep Smash running. The extractor uses
its installed `smash_arc.dll` and the archive server on port 43022. Only archive
reads occur on the Switch. Region 2 (US English, Arc Explorer's default) is
used. Other languages need separate extraction; changing `--region` does not
replace existing files. Interrupted `.pmclone-part` files are preserved for
inspection, not accepted as completed files.

Preparation preserves user edits and reports conflicts, checks write readback,
rejects links as output, retargets motion-list directory hashes and checks the
referenced animations exist. It keeps local texture/material filenames intact.
Filename matching is not proof of complete dependency closure.

## Remaining function independence

The pinned engine's `clone_engine_core/src/vtable_copy.rs` copies function
pointers; those still call the original functions. Its reconciliation can also
adopt changed original pointers. This is insufficient for the requested clone.

The three character NROs have 27 exported factories and 2,315 relocation
entries. Their imports include 22 distinct character-specific routines in main,
which themselves call other code and reference data. Renaming an NRO or copying
function bytes does not resolve these dependencies or isolate their state.
The native class audit also finds 144 external direct branches, 342 PC-relative
references and 551 indirect transfers in the candidate methods. Some are generic
engine operations; that distinction must be established before enabling them.

Remaining work:

1. Identify shared database rows and internal references in sounds, effects,
   UI, parameters and scripts. The current named-resource inventory is copied;
   additional dependencies may still need extraction.
2. Complete private character-native implementations and bind their imports in
   the already tested module loader. Follow native call/data dependencies and
   isolate character state. Audit embedded kinds and hashes.
3. Implement one roster entry owning both forms, transformation, articles,
   loading/destruction, stocks/damage, Final Smash and results.
4. Test originals and clone together on console, all eight costumes, attacks,
   both switch directions, respawn, Final Smash, Kirby copy, results/rematch.
5. Demonstrate clone-only asset, parameter and function changes leave originals
   unchanged. Only then package a playable release.

The main dump predates this session and was not freshly verified against the
running console. Static resource checks are not evidence of working gameplay.

Sources: [pinned engine](https://github.com/PropaSmike/ssbu_clone_engine/tree/a2c8cea7df4eedab7364979aa2c8ace2ba5446cf),
[Arc Explorer bindings](https://github.com/ScanMountGoat/SmashArcNet/blob/main/SmashArcNet/RustBindings.cs).
