---
title: Ryubing source accepts the lab Atmosphere mod layout
summary: A pinned Ryubing mirror accepts direct title-id exefs and romfs folders, replacement NPDM, and default-enabled mods; runtime compatibility remains untested
status: unverified
tags: [ryujinx, ryubing, skyline, arcropolis, mod-loader, sdcard]
updated: 2026-10-01
source: T-0004; official Ryubing docs and Leuconoe/Ryubing source mirror
---

## What

The inspected source accepts the lab's `sdcard/atmosphere/contents/01006A800016E000/{exefs,romfs}` layout directly, without a mod-name directory. Title IDs are matched case-insensitively. It can add Skyline's `subsdk9`, use its replacement `main.npdm`, merge the plugin files into RomFS, and enable these folder mods without creating `mods.json`.

These are source-level conclusions, **not an observed Skyline/ARCropolis boot**. The official source host was unavailable, so the implementation evidence is a **mirror, may be older than current Ryubing**, pinned below. No path migration in `smashlab/emu.py` or `config/lab.toml` is indicated by this evidence. Guest SD access is supported by the VFS routing, with a dependency-tracing limitation described in answer 6.

Related setup assumptions remain in [emulator environment](../reference/emulator-test-env.md) and [modding stack](../reference/ssbu-modding-stack.md); those seed references were not edited by this task.

## Evidence

### Sources tried, in required order

1. **Official source (a):** [requested repository](https://git.ryujinx.app/ryubing/ryujinx) and [repository address linked by the official docs](https://git.ryujinx.app/projects/Ryubing). Both web fetches returned `Failed to fetch ...: (400) Timeout fetching`; Python `urllib.request.urlopen(..., timeout=15)` returned `URLError <urlopen error timed out>` for both on 2026-10-01. Current official source revision could not be determined. No binary was downloaded.
2. **Official documentation (b):** [setup guide, Managing Mods](https://docs.ryujinx.app/guides/setup-guide/#managing-mods), [Ryubing organisation](https://github.com/Ryubing), and its [docs repository](https://github.com/Ryubing/docs). The guide contains both manual Atmosphere installation and a mod-manager section. Pinned docs revision **`8bbea28d757e2582b3d954672b65b99bbbcf3199`**, committer timestamp `2026-04-15T04:31:51Z`, obtained from GitHub's commits API. [File `docs/guides/setup-guide.md`, lines 285-346](https://github.com/Ryubing/docs/blob/8bbea28d757e2582b3d954672b65b99bbbcf3199/docs/guides/setup-guide.md#L285) documents mod types, enabled-by-default imports, named folders in `mods/contents`, and direct ExeFS/RomFS under the SD Atmosphere title folder. This corroborates the layout but does not answer the executable details.
3. **Fallback source (c), used for implementation answers:** [Leuconoe/Ryubing](https://github.com/Leuconoe/Ryubing), explicitly described by its owner as a mirror with an optional local MCP bridge. **Mirror, may be older than current Ryubing; it also contains downstream changes.** Pinned revision **`793ca017ff4f6e48b798a62d2486405bfc42ef39`**, committer timestamp `2026-08-05T02:20:44Z`, obtained from GitHub's commits API. Only source text/API metadata were fetched into `state/scratch/T-0004/`; no mirror binaries were downloaded. No equivalence to a current official release is asserted.

All source citations below point to that complete pinned mirror revision, not a moving branch. File paths and symbols/line numbers are included in each answer.

### 1. Search bases and expected structure

For a normal NCA game (including the NCA loaded from an NSP/XCI), [file `src/Ryujinx.HLE/Loaders/Processes/Extensions/NcaExtensions.cs`, `Load`, lines 42-49](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/Loaders/Processes/Extensions/NcaExtensions.cs#L42) calls `CollectMods` with **both** `GetModsBasePath()` and `GetSdModsBasePath()`. These resolve by default to `<data>/mods` and `<data>/sdcard/atmosphere`: [file `src/Ryujinx.Common/Configuration/AppDataManager.cs`, `GetModsPath` / `GetSdModsPath`, lines 325-326](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.Common/Configuration/AppDataManager.cs#L325). Non-null `CustomModsPath` and `CustomSdModsPath` replace those respective search bases; these are additional configurable locations, not extra unconditional searches.

Under **either base** the loader recognizes:

| Relative structure | Interpretation |
|---|---|
| `contents/<title id>/exefs/`, `contents/<title id>/romfs/` | Direct Atmosphere-style loose files |
| `contents/<title id>/<mod name>/{exefs,romfs}/` | Named mods; arbitrary wrapper directories are recursively searched until a recognized payload directory is reached |
| `contents/<title id>/romfs.bin`, `contents/<title id>/exefs.nsp` | Image containers checked directly at the application-folder root |
| `contents/<title id>/cheats/<16-hex-build-id>.txt`, or `<mod name>/cheats/<16-hex-build-id>.txt` | Cheat files; not title IDs as filenames |
| `exefs_patches/<patch name>/{<build-id>.ips,*.pchtxt}` | Global NSO patches, immediate files in each patch-name directory |
| `nro_patches/<patch name>/{<build-id>.ips,*.pchtxt}` | Global runtime NRO patches; these directories do not install or discover plugin NROs |

[File `src/Ryujinx.HLE/HOS/ModLoader.cs`, constants, `EnsureBaseDirStructure`, `QueryPatchDirs`, `QueryApplicationDir`, `AddModsFromDirectory`, `QueryCheatsDir`, `CollectMods`, and `ApplyProgramPatches`, lines 31-43, 150-203, 223-307, 334-382, 424-457, 771-843](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/HOS/ModLoader.cs#L150) supplies these rules. NSO patches are also read from the discovered `exefs` directories (`ApplyNsoPatches`, lines 707-718). IPS build-ID matching is a string comparison after trimming trailing zeroes, not title-ID matching. `kip_patches` is recognized by the collection code, but automatic creation is commented out and KIP support carries a TODO; it is not a usable Skyline installation route.

The outer scan checks each search base and its immediate children for `contents` or patch directories. It does not search a legacy `<data>/load` folder or arbitrary locations on disk. Application and installed DLC IDs are collected by `NcaExtensions.Load`; exact relevant program IDs matter for multi-program games. An unpacked-NCA launch differs: [file `src/Ryujinx.HLE/Loaders/Processes/Extensions/LocalFileSystemExtensions.cs`, `Load`, line 18](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/Loaders/Processes/Extensions/LocalFileSystemExtensions.cs#L18) supplies no search paths. The lab's configured NSP/XCI route is the relevant route here.

### 2. Direct Atmosphere folders and title-ID case

**Yes, direct folders are accepted.** `QueryContentsDir` finds the title directory, `QueryApplicationDir` passes that directory directly to `AddModsFromDirectory`, and the latter recognizes child `exefs` and `romfs` immediately. It also recurses through other directory names, so named folders work under both bases. The direct mod's diagnostic name is the title-folder name (`dir.Name`), rather than an empty unnamed-mod label; the planner's layout recollection was right but its naming detail was imprecise.

**Yes, title-ID directory matching is explicitly case-insensitive**, including on hosts where directory names are normally case-sensitive: `FindApplicationDir` uses `_dirEnumOptions.MatchCasing = MatchCasing.CaseInsensitive`. Recognized payload directory names use `StrEquals` with `OrdinalIgnoreCase`. This does not make every payload filename case-insensitive; executable filenames are constructed literally and depend on host filesystem behavior.

Source: [file `src/Ryujinx.HLE/HOS/ModLoader.cs`, `_dirEnumOptions`, `StrEquals`, `FindApplicationDir`, `AddModsFromDirectory`, `QueryContentsDir`, lines 126-144, 163-203, 309-332](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/HOS/ModLoader.cs#L126).

### 3. ExeFS replacement, addition, and NPDM

Recognized extensionless executable filenames, in load order, are **`rtld`, `main`, `subsdk0` through `subsdk9`, `sdk`**. [File `src/Ryujinx.HLE/Loaders/Processes/ProcessConst.cs`, `ExeFsPrefixes`, lines 5-23](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/Loaders/Processes/ProcessConst.cs#L5) defines the fixed slots and `/main.npdm` path.

The original game fills available NSO slots; absent files leave null slots. `ApplyExefsMods` assigns an NSO from the mod into the named slot regardless of whether an original NSO exists there. Thus it **replaces an existing module or adds an absent module**, including `subsdk9`. Only those fixed names are loaded; arbitrary extra names are ignored. First replacement wins on conflicts, with a warning. `<name>.stub` removes a slot unless a replacement exists. The first found `main.npdm` is loaded into a replacement `MetaLoader`.

Sources: [file `src/Ryujinx.HLE/HOS/ModLoader.cs`, `ApplyExefsMods`, lines 603-690](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/HOS/ModLoader.cs#L603), and [file `src/Ryujinx.HLE/Loaders/Processes/Extensions/FileSystemExtensions.cs`, `Load`, lines 50-80, 112-124](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/Loaders/Processes/Extensions/FileSystemExtensions.cs#L50). The latter explicitly selects `modLoadResult.Npdm`, filters null modules only **after** applying mods, and passes that metadata and the NSOs to process initialization. [File `src/Ryujinx.HLE/Loaders/Processes/ProcessLoaderHelper.cs`, `LoadNsos`, lines 238-244, 317, 386-392](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/Loaders/Processes/ProcessLoaderHelper.cs#L238) uses the selected NPDM, including kernel capabilities. Therefore the replacement NPDM is honored, not merely detected. This establishes the mechanism Skyline requires, not binary compatibility.

### 4. RomFS layering and plugin visibility

`ApplyRomFsMods` builds a merged RomFS: enabled loose files first, enabled `romfs.bin` files next, original game files last where their paths have not already been supplied. New paths can be added as well as replaced. Duplicate mod file paths are skipped after the first occurrence; directory enumeration is not an explicit user-defined priority order. Unmodified game files remain available. If no mod files exist it returns the original storage.

Sources: [file `src/Ryujinx.HLE/HOS/ModLoader.cs`, `ApplyRomFsMods` / `AddFiles`, lines 476-569](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/HOS/ModLoader.cs#L476), and [file `src/Ryujinx.HLE/Loaders/Processes/Extensions/NcaExtensions.cs`, `Load`, lines 77-88](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/Loaders/Processes/Extensions/NcaExtensions.cs#L77), which installs the merged storage for the process. Consequently `romfs/skyline/plugins/libarcropolis.nro` becomes filesystem path `/skyline/plugins/libarcropolis.nro` in the game's RomFS, accessible through the guest's `rom:/` mount. Reading and loading those plugin files is Skyline's job; Ryujinx does not execute them simply because they exist.

### 5. Default enablement and mods.json

**Folder mods found on disk are enabled by default.** `QueryApplicationDir` looks for `<data>/games/<application-id in lowercase hex>/mods.json`, starts with an empty `ModMetadata`, and optionally deserializes the file. `AddModsFromDirectory` looks for an entry whose `Path` exactly equals the payload directory's parent full path. If no entry matches, `modData?.Enabled ?? true` enables the folder. An existing matching entry with `Enabled: false` disables it. A missing metadata file requires no UI action. Malformed metadata is logged and the default metadata remains in use.

Sources: [file `src/Ryujinx.HLE/HOS/ModLoader.cs`, `QueryApplicationDir`, lines 269-307, and `AddModsFromDirectory`, lines 167-188](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/HOS/ModLoader.cs#L269); [file `src/Ryujinx.Common/Configuration/ModMetadata.cs`, constructor](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.Common/Configuration/ModMetadata.cs#L5); [file `src/Ryujinx.Common/Configuration/Mod.cs`, `Name`, `Path`, `Enabled`](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.Common/Configuration/Mod.cs#L3). Global patch directories are created as enabled by `QueryPatchDirs`.

**Cheats differ:** [same ModLoader file, `EnableCheats`, lines 760-768](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/HOS/ModLoader.cs#L760) reads selected cheats from `<data>/mods/contents/<title id>/cheats/enabled.txt`; discovery alone does not activate them. The official guide independently documents cheats as initially disabled (docs file lines 382-391).

### 6. Custom data directory and guest SD

The source routes the emulated SD to the selected data root. [File `src/Ryujinx/Utilities/CommandLineState.cs`, `ParseArguments`, lines 49-58](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L49) recognizes `-r` and `--root-data-dir`; [file `src/Ryujinx/Program.cs`, `Initialize`, line 258](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Program.cs#L258) passes the value to `AppDataManager.Initialize`. [File `src/Ryujinx.Common/Configuration/AppDataManager.cs`, `Initialize`, lines 84-104 and `DefaultSdcardDir`, line 37](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.Common/Configuration/AppDataManager.cs#L84) selects the custom root **only if it already exists**; otherwise it logs a fallback to the profile/portable root.

[File `src/Ryujinx.HLE/FileSystem/VirtualFileSystem.cs`, `GetSdCardPath`, line 114, `MakeFullPath`, lines 152-184, and `InitializeFsServer`, lines 187-209](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/FileSystem/VirtualFileSystem.cs#L114) resolves `sdcard` relative to `BaseDirPath`, creates the filesystem server rooted there, and marks its emulated SD inserted. [File `src/Ryujinx.HLE/HOS/Services/Fs/IFileSystemProxy.cs`, `OpenSdCardFileSystem`, lines 151-164](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/HOS/Services/Fs/IFileSystemProxy.cs#L151) exposes the server's SD filesystem to the guest.

**Inference from these sources:** with the lab's existing `-r testenv/ryujinx/data` root, guest `sd:/ultimate/mods` corresponds to `testenv/ryujinx/data/sdcard/ultimate/mods`. The default filesystem server's internal subdirectory selection is delegated to `Ryujinx.LibHac` version `0.21.0-alpha.133` ([file `Directory.Packages.props`, package-version declaration](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/Directory.Packages.props)). That dependency's implementation was not independently traced: candidate repository API URLs `https://api.github.com/repos/Ryubing/LibHac` and `https://api.github.com/repos/Leuconoe/LibHac` each returned `HTTP Error 404: Not Found`. Runtime access and ARCropolis's own mount/read behavior remain unverified. `CustomSdModsPath` changes the mod search base; it does not relocate the guest SD. `CustomSdCardPath` carries a VFS-not-implemented TODO in `AppDataManager` lines 40-43.

### 7. Settings, PPTC, and NRO loading

No master mod-enable switch, guest-network condition, or ignore-missing-services gate occurs in the inspected `NcaExtensions.Load`, `CollectMods`, `ApplyExefsMods`, or `ApplyRomFsMods` paths cited above. Those functions perform discovery and application automatically. This is a statement about these source paths, not a guarantee that every Skyline/ARCropolis build runs with default settings.

**PPTC:** [ModLoader file, `ApplyExefsMods`, lines 649-653 and 685-687](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/HOS/ModLoader.cs#L649) hashes replacement NSO bytes. `FileSystemExtensions.Load` lines 112-118 passes that hash as a cache selector, and [file `src/Ryujinx.HLE/HOS/ArmProcessContextFactory.cs`, `Create`, lines 121-123](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/HOS/ArmProcessContextFactory.cs#L121) uses `default` if absent. [File `src/ARMeilleure/Translation/PTC/Ptc.cs`, `Initialize`, lines 111-156](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/ARMeilleure/Translation/PTC/Ptc.cs#L111) incorporates the selector into the cache path. In this mirror, changing Skyline's NSO bytes selects a different cache; a blanket claim that all ExeFS changes require a manual purge is unsupported. **However**, this hash does not cover `main.npdm`, `.stub` choices, or IPS/IPSwitch patch contents. Cache safety for those changes could not be determined from this limited trace. A later controlled test should use a fresh cache or disable PPTC while varying such inputs. The [pinned official docs, PPTC section, lines 593-631](https://github.com/Ryubing/docs/blob/8bbea28d757e2582b3d954672b65b99bbbcf3199/docs/guides/setup-guide.md#L593) document default enablement and troubleshooting purges, not a mandatory mod-loading purge.

**Missing services:** [file `src/Ryujinx.HLE/HOS/Services/Sm/IUserInterface.cs`, `GetService`, lines 109-115](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/HOS/Services/Sm/IUserInterface.cs#L109) uses `IgnoreMissingServices` to warn rather than throw for an absent service. It is not a prerequisite for discovering mods. Whether the particular Skyline/ARCropolis releases request absent services, and hence require this setting, **could not be determined** by reading Ryujinx alone; no boot was authorized.

**NROs:** [file `src/Ryujinx.HLE/HOS/Services/Ro/IRoInterface.cs`, `ParseNro`, lines 114-200](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/HOS/Services/Ro/IRoInterface.cs#L114) checks registration/hash, structure and alignment and invokes `ApplyNroPatches`. There is no general enable-NRO setting in that path. This standard guest service is not proof of Skyline's custom plugin loader compatibility. No guest internet access is needed by the inspected filesystem mod loader; whether ARCropolis's optional network features affect startup **could not be determined** from these sources. Do not turn guest internet on merely to make local mod discovery work.

### Local commands and observations

- Read `AGENTS.md`, `kb/INDEX.md`, `kb/README.md`, the finding template, all relevant indexed emulator/modding/machine notes, `tools/REGISTRY.md`, `config/lab.toml`, and `smashlab/emu.py`. Ran `python -m smashlab kb search ryujinx`.
- `rg` was unavailable in PowerShell (`CommandNotFoundException`); used `Select-String` and numbered Python source reads instead.
- Read-only `Get-ChildItem` name listings of the explicitly permitted `%APPDATA%/Ryujinx` directories found `mods/{contents,exefs_patches,nro_patches}` and `sdcard/atmosphere/{contents,exefs_patches,nro_patches}`. Both contents directories held `01008f6008c5e000`; `games/01008f6008c5e000/mods.json` exists (`Test-Path=True`). This is another title, not SSBU. No profile file contents, keys, firmware, or game assets were read/copied.
- GitHub API commit/tree reads and pinned raw-source downloads provided the revisions and source above. Cached text is confined to `state/scratch/T-0004/`.
- No emulator installation, SD installation, deploy, undeploy, setup, or boot command was run. No game dump was touched. This task does not validate ZIP internal layout or the compatibility of release binaries.
- Baseline `git status --short` already showed `?? smashlab/` and `?? config/` because the workspace has not tracked those directories yet. Final `git status --short smashlab config` likewise shows those existing untracked directories, not task edits. Content hashes before documentation edits and after checks are identical: `smashlab/emu.py` SHA-256 `bbf6016c3637a7ff2d7ab1651fd4d38d1fbdaa2696b4dff859c7933919e6d6ac`; `config/lab.toml` SHA-256 `a6aff5e56155dd40515c60a764baeda0bd255189eb3d759252ebc4401393e6a5`.

## Why (if known)

The loader shares a recursive payload-directory scanner between native mods and Atmosphere mods. Its fixed executable array deliberately retains missing slots until modifications are applied, and its metadata fallback explicitly enables unlisted mods. These mechanisms explain why the lab's direct Atmosphere paths are supported by the inspected source.

## What to do instead / next

Keep the present layout for now. Recheck the same symbols in the official revision once its host returns, then test a normal NSP/XCI boot with clear loader logs for `subsdk9`, `main.npdm`, and merged RomFS. A runtime test must establish actual Skyline/ARCropolis/Smashline behavior and SD reads; this finding must remain `unverified` until that happens. Review cache handling for NPDM-only/stub/patch changes and strengthen readiness checks to require both Skyline files. These are follow-ups, not edits made here.

## Comparison with smashlab/emu.py

Here `<data>` is `testenv/ryujinx/data`, and `<tid>` is `01006A800016E000`. Verdicts compare the inspected source mechanism with the lab behavior; `matches` does not mean a successful emulator test. There are no source-established layout mismatches and therefore no required relocation edits in `emu.py` or `lab.toml`.

| Lab path or behaviour | emu.py function / lab.toml key | What the source says | Verdict |
|---|---|---|---|
| Skyline exefs path: `<data>/sdcard/atmosphere/contents/<tid>/exefs/{subsdk9,main.npdm}` | `install_sd`, lines 144-150; `status`, lines 161, 171; `emu.sd_packages` Skyline `dest`, lab.toml line 130 | Both search bases accept direct title-level ExeFS; fixed slot can add subsdk9 and replacement NPDM is used (answers 1-3) | matches |
| Plugins romfs path: `<data>/sdcard/atmosphere/contents/<tid>/romfs/skyline/plugins/*.nro` | `deploy`, line 191; `status`, lines 172-173; Smashline `dest`, lab.toml line 142; ARCropolis ZIP root `dest`, line 136 | Direct RomFS is merged; these relative paths enter guest RomFS (answers 2, 4). Archive internal layout was not audited | matches |
| ultimate/mods path: `<data>/sdcard/ultimate/mods/<name>` and `ultimate/arcropolis/...` | `_paths`, lines 31-35; `setup`, line 85; directory `deploy`, line 195; `undeploy`, line 203; `emu.data_dir`, lab.toml line 116 | VFS routes SD beneath selected data root; these are guest SD files for ARCropolis, not Ryujinx RomFS mod directories (answer 6, dependency caveat) | matches |
| Uppercase title ID in SD paths | `status`, lines 160-161; `deploy`, line 191; `emu.title_id`, lab.toml line 114; SD package destinations lines 130, 142 | `FindApplicationDir` explicitly uses case-insensitive enumeration (answer 2) | matches |
| Mod enabled-by-default; harness writes no mods.json | `install_sd`, `deploy`; no enabling metadata step | Empty/missing metadata defaults folder mods to enabled; exact matching disabled entry overrides this (answer 5) | matches |
| Custom data root passed with `-r` | `_paths`, lines 31-35; `test` launch, line 279; `emu.data_dir`, line 116 | CLI accepts argument; existing custom root becomes BaseDirPath, absent root falls back (answer 6) | matches |
| Skyline readiness checks only subsdk9 | `status`, line 171 | Source separately loads main.npdm if present; this check proves only one file exists, not that required metadata or runtime compatibility is present (answer 3) | undetermined |
| Deploying a .nro copies it to Skyline RomFS; undeploy handles directory mods only | `deploy`, lines 183-200; `undeploy`, lines 202-207 | RomFS makes plugin bytes visible; executing/removing those plugins is not a Ryujinx mod-manager operation (answer 4) | matches |
| Harness does not alter PPTC, missing-service or guest-network settings | `_patch_config`, lines 113-125 | No loader prerequisite found; cache selector covers replacement NSOs, other mutations and plugin service needs still need testing (answer 7) | undetermined |
