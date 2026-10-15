---
title: Offline data.arc extraction inputs and pinned LibHac contract
summary: Local split NSP layout and LibHac 0.19.0 APIs for tickets, Program selection and base-plus-update RomFS, implemented and run by T-0032 while archive readability stayed unverified
status: verified
tags: [dump, extraction, nsp, nca, romfs, libhac, data-arc]
updated: 2026-10-02
source: T-0030; T-0031; T-0032 implementation and observed runs; official LibHac 0.19.0 metadata and local source/hash inspection
---

## Status after T-0032

The tool described here is implemented and **ran on this workspace** (2026-10-02): offline restore
and build succeeded, and both base-only and base+update extractions completed. Observed effective
sizes are 14,460,050,172 bytes (base-only) and 17,600,869,448 bytes (patched 13.0.4); the patched
SHA-256 `ef615e671e1d4907f0a707f2eb13e3cb0c8539c4e67ac51c89ef547c22b82995` was independently
recomputed and matched, with inputs unchanged. **Archive readability and 13.0.4 content correctness
remain unverified** because no ARC viewer exists inside the workspace; see
[the finding](../findings/data-arc-extraction-needs-user-viewer-check.md) and
[the playbook](../playbooks/extracting-data-arc-offline.md).

Two API details were settled by real compilation, not by metadata: `UniqueRef<T>.Dispose()` is an
obsolete **error** in 0.19.0 (use `Destroy()`), and `KeySet.CreateDefaultKeySet` plus
`IntegrityCheckLevel.ErrorOnInvalid` exist as used. The rest of this note is the original contract
and remains accurate as design rationale.

## Decision and evidence boundary

Select **LibHac 0.19.0**, consumed by a small project-local .NET 8 console application.
The local DLL has the required APIs and is byte-identical to the publisher's NuGet DLL.
Use its read-only storage abstractions rather than joining or unpacking whole NSPs.
This resolves the backend choice for T-0029; it does **not** establish successful decryption
or extraction of this dump. No backend code, extraction, tests, emulator setup or launch ran.
No keys, game payloads or `.env` were read in this research run.

**Observed:** filesystem metadata, dependency JSON, package metadata, XML documentation,
assembly API metadata and cached static IL. **Unverified:** the dump's internal content,
key coverage, CNMT/NCA pairing, library compatibility with this specific 13.0.4 patch,
compilation of the proposed application, output size, throughput and peak RAM.
The frontmatter remains `unverified` because the extraction path has not run here.

Mod context stays in [03_dumps.md](../../mods/ssbu_mod_new/handbook/03_dumps.md),
[pgwr STATUS.md](../../mods/ssbu_mod_new/projects/pgwr/STATUS.md) and
[fetch_arc_files.py](../../mods/ssbu_mod_new/tools/fetch_arc_files.py).
That tool uses live arc-network/console extraction; it is not an offline NSP backend.
No mod files were changed.

## Rediscovered local inputs

All paths below are relative to `<workspace>`. Metadata inspected 2026-10-01.
Package labels identify the intended version; they are not decrypted CNMT evidence.

| Input | Actual path | Observed bytes |
|---|---|---:|
| Split base directory | `dump/nxdt_rw_poc/NSP/Super Smash Bros. Ultimate [01006A800016E000][v0][BASE].nsp/` | directory |
| Part 00 | preceding directory + `00` | 4,294,901,760 |
| Part 01 | preceding directory + `01` | 4,294,901,760 |
| Part 02 | preceding directory + `02` | 4,294,901,760 |
| Part 03 | preceding directory + `03` | 1,754,001,760 |
| Existing joined base | `testenv/ryujinx/roms/Super Smash Bros. Ultimate [01006A800016E000][v0][BASE].nsp` | 14,638,707,040 |
| Separate update | `dump/nxdt_rw_poc/NSP/Super Smash Bros. Ultimate 13.0.4 [01006A800016E800][v1966080][UPD].nsp` | 3,931,423,648 |
| Common keys | `testenv/ryujinx/data/system/prod.keys` | 15,532 |
| External title keys | `testenv/ryujinx/data/system/title.keys` | 67,048 |
| Candidate backend | `Ryujinx/build/LibHac.dll` | 1,612,288 |

The joined base size equals the sum of parts (13.633 GiB); equality of contents was **not** checked.
Default to the split directory, avoiding reliance on that unverified joined copy. The update is
3.661 GiB. Key-file timestamps are 2024-05-08; their contents and sufficiency are unknown.
The separate `...01006A800016F001...DLC.nsp` is outside this extraction contract.

`Ryujinx/build/Ryujinx.deps.json` lines 412-418 declares `LibHac/0.19.0`, asset
`lib/net7.0/LibHac.dll`, assembly/file version `0.19.0.0`; lines 1687-1692 records its
NuGet identity. `Ryujinx.runtimeconfig.json` targets .NET 8. This is the local older
`LibHac` package, **not** the `Ryujinx.LibHac 0.21.0-alpha.133` dependency mentioned in
the [Ryubing finding](../findings/ryubing-mod-directories-and-sdcard-atmosphere-contents.md).
That finding's unavailable fork source is not needed for this selected package.

## Provenance and runtime

Official package: [LibHac 0.19.0](https://www.nuget.org/packages/LibHac/0.19.0).
Direct immutable-version artifact:
[libhac.0.19.0.nupkg](https://api.nuget.org/v3-flatcontainer/libhac/0.19.0/libhac.0.19.0.nupkg).
This run retrieved its 651,221 bytes in memory for metadata/docs and DLL comparison only.

- Package SHA-256: `1431267861db5ff68216315b164f10c0edab4df162cedf5429bf8a143b76de19`.
- Local and official DLL SHA-256: `df35642dd8d43472414a58a45fb7c5c22858764abf114ea09bff7bb08bad5b16`.
- Publisher nuspec: Alex Barney, MIT, target `net7.0`, no declared package dependencies.
- Declared original source commit: `cd4004af194a51712812c680f0a028ba9152c0f8` at
  [Thealexbarney/LibHac](https://github.com/Thealexbarney/LibHac).
  The original repository returned HTTP 404 on this run. This is a **package-declared**
  source commit, not a source checkout we inspected. Package hashes pin the usable artifact;
  signature verification was not performed and no mirror is substituted.

`dotnet --list-sdks` / `--list-runtimes` rediscovered SDK 8.0.201 and NETCore runtime 8.0.2.
There is no .NET 7 runtime in that listing. Target the new application at `net8.0` and reference
the compatible package asset; .NET 8 execution remains unverified. Do not launch a net7 app
and assume its missing runtime will roll forward. No system-wide runtime installation is needed
for the proposed net8 application.

## Project-local setup prepared by T-0031

The setup source now lives at `tools/data-arc-extract/` (superseding the proposed
`tools/offline-data-arc/` name). See its [README](../../tools/data-arc-extract/README.md)
for exact PowerShell setup/build commands and recovery instructions. T-0031 follows
the user preference for referencing the compatible existing DLL in place rather
than the earlier package-restore preference. `backend.lock.json` records assembly
version, DLL/package hashes, official package URL and package-declared source commit.
No package dependencies are declared; the hash-checked local reference is the lock.

`setup.ps1` checks backend identity and SDK 8.0.201/runtime 8.0 prerequisites, performs
an offline metadata restore using a source-cleared NuGet.Config, and optionally builds.
The net8.0 project is an empty library scaffold; T-0032 must add executable source and
explicit Compile items. Source contains no third-party distribution. Default cache and
build outputs are under `tools/data-arc-extract/.cache/`; explicit destinations may
also be under ignored `state/`. CLI home, NuGet package/HTTP/plugin/scratch caches and
TEMP/TMP are redirected there for child SDK commands, then restored. Path validation
rejects destinations outside these roots and existing junction/symlink ancestors.
No SDK/backend download, system installation or emulator configuration change is made.
Official-package recovery is documented, with both package and DLL hash verification;
SDK recovery uses Microsoft's official .NET 8 archive and published checksum.

**Observed in T-0031:** reread source/contract and local DLL SHA-256, again matching
`df35642dd8d43472414a58a45fb7c5c22858764abf114ea09bff7bb08bad5b16`.
**Observed in T-0032:** `setup.ps1 -Build` succeeded offline on SDK 8.0.201 (0 warnings, 0 errors),
so the T-0031 statements about setup and compilation no longer being executed are superseded;
.NET 8 execution of the pinned net7.0 backend also works. The older tool rule requiring a
real-input run is now satisfied for extraction, and the registry entry stays `experimental`
only because viewer compatibility is unconfirmed. Firmware and Ryujinx execution remain
unnecessary prerequisites.

The tool's `.gitignore` covers `.cache/`, `bin/` and `obj/`; `run.py` is the root-level launcher,
and `Program.cs` is the only compile item (`EnableDefaultCompileItems` is off). `run.py` pins the
adjacent `LibHac.dll` hash before launch and rejects a caller-supplied `--workspace`.

## Concrete interfaces (0.19.0 metadata, not executed)

Namespaces: `LibHac.Common.Keys`, `LibHac.Tools.FsSystem`,
`LibHac.Tools.FsSystem.NcaUtils`, `LibHac.FsSystem`, `LibHac.Tools.Es`,
`LibHac.Tools.Ncm`, `LibHac.Common`, `LibHac.Fs.Fsa`.
The following are call shapes, not a complete compiled program.

```csharp
var keys = KeySet.CreateDefaultKeySet();
ExternalKeyReader.ReadKeyFile(keys, prodPath, titlePath, null, null);
// Arguments: common keys, title keys, console keys, optional logger.

// Each FileStream must be FileAccess.Read and remain alive through extraction.
IStorage partStorage = new StreamStorage(partStream, leaveOpen: true);
IStorage baseStorage = new ConcatenationStorage(orderedPartStorages, leaveOpen: true);
var basePfs = new PartitionFileSystem();
basePfs.Initialize(baseStorage).ThrowIfFailure();
// Update uses a single StreamStorage and its own PartitionFileSystem.

// EnumerateEntries(pfs, "/", "*", SearchOptions.Default) or EnumerateEntries(pfs).
// OpenFile(ref UniqueRef<IFile>, U8Span path, OpenMode.Read); inspect every Result.
// Keep UniqueRef alive: file.AsStorage() is a bounded view, not a payload copy.
var nca = new Nca(keys, ncaFile.Get.AsStorage());

var ticket = new Ticket(ticketFile.Get.AsStream());
byte[] encryptedKey = ticket.GetTitleKey(keys);
// Only if non-null and exactly 16 bytes, and no conflicting existing entry:
keys.ExternalKeySet.Add(new LibHac.Fs.RightsId(ticket.RightsId),
    new LibHac.Spl.AccessKey(encryptedKey)).ThrowIfFailure();

var metadata = new Cnmt(cnmtFile.Get.AsStream());
// Inspect TitleId, TitleVersion, Type, ApplicationTitleId and ContentEntries.

var patchedFs = baseProgram.OpenFileSystemWithPatch(updateProgram,
    NcaSectionType.Data, IntegrityCheckLevel.ErrorOnInvalid);
// Explicit base-only mode instead calls baseProgram.OpenFileSystem(...).
```

`NcaSectionType.Data` is the Program RomFS selector; **Code** selects ExeFS. Do not
invent a `NcaSectionType.Romfs` enum or confuse `NcaContentType.Data` with Program content.
`nca.Header` exposes `ContentType`, `TitleId`, `ContentIndex`, `KeyGeneration`,
`RightsId` and `HasRightsId`; `SectionExists` and `GetFsHeader` support section checks.
Open `/data.arc` with `OpenMode.Read`, `IFile.GetSize(out long)`, and repeated
`IFile.Read(out long bytesRead, long offset, Span<byte> buffer)`; reject short reads.

The publisher XML specifies explicit key filenames and skipping null filename arguments.
Use no default profile discovery and no unfiltered logger: key-parser messages must not
expose values. Tickets are PFS0 entries ending `.tik`; do not derive title keys from filenames.
Static IL indicates `Ticket.GetTitleKey` returns the first 16 bytes for a common ticket,
or RSA-unwrapped bytes for a personalized ticket, and may return null without the device
RSA key. These are still **titlekek-encrypted** keys: register them in `ExternalKeySet`,
not as already-decrypted AES keys. `Nca.GetDecryptedTitleKey` applies the generation's
titlekek. Load explicit `title.keys` first; an existing matching RightsId can satisfy a
personalized ticket without requiring a device key. Reject conflicting key entries in memory.

## Split strategy, Program identity and patch precedence

1. Validate the base directory's two-digit part names form a contiguous sequence starting
   at `00`, with no gaps, empty parts or unexpected files. Validate lengths, 64-bit summed
   offsets and bounds before constructing the ordered `IList<IStorage>`. Local parts
   `00`-`03` are contiguous. Open all input handles read-only.
2. Initialize PFS0 over that concatenation and the single update storage. Enumerate entries
   and parse tickets in memory before opening rights-managed sections. Retain the root
   storages, file refs and streams until all derived filesystems have been disposed.
3. Open Meta NCAs (`NcaContentType.Meta`), their Data filesystem, and `.cnmt` files.
   Require the base application CNMT title `01006A800016E000`, version 0, and patch CNMT
   `01006A800016E800`, version 1966080, linked `ApplicationTitleId` to the base.
   Record the internal evidence; labels alone do not satisfy these checks.
4. Use each CNMT's `ContentEntries` whose `Type` is `LibHac.Ncm.ContentType.Program`
   to resolve `NcaId` to the corresponding PFS0 `.nca`, checking size and hash provenance.
   Confirm the decrypted NCA header is Program and select `ContentIndex == 0` with a
   Data section. Require one matching base/update Program pair; stop on ambiguity or
   missing referenced content. A patch **CNMT** has the E800 title ID; do not require
   its Program NCA header to have that ID. Pair Program identity using header title and
   content index, with the CNMT relationship as the authority. Reject other applications,
   Control/Manual NCAs and DeltaFragment entries; do not choose the largest NCA.
5. Call **baseProgram.OpenFileSystemWithPatch(updateProgram, Data, ErrorOnInvalid)**.
   Cached IL shows base storage installed as indirect-storage slot 0 and patch storage
   as slot 1, with patch relocation metadata and verification. Non-relocated patch data
   uses the patch storage directly. This indicates block-level patch precedence, not
   a directory overlay. Read `/data.arc` from that mounted filesystem only.

An update's standalone RomFS is **not** the complete patched archive. Do not concatenate
`data.arc` files, overlay a separately extracted update directory, disable integrity checks
after an error, or silently fall back to vanilla. A deliberate `--base-only` mode must
have a separately labelled report and cannot claim 13.0.4 output.

`smashlab/emu.py` `_split_parts` supplies the numeric-name discovery idea;
`_join_split_dump` supplies 16 MiB streaming and temporary-name/rename ideas. The former
does not reject gaps and `game_file` trusts size equality for an existing join. Strengthen
validation in the new tool; do not call those orchestrator functions or edit `emu.py`.

## Finite implementation contract and resource budget

Implement one reusable offline tool accepting `--base`, `--update`, `--prod-keys`,
`--title-keys`, `--output` and explicit `--base-only`. Confine paths to the workspace;
output must be under `gamedata/` and must not overwrite inputs, keys or an existing final
archive without explicit replacement. Default paths may be supplied in documentation,
but the reusable tool takes paths as arguments. No console, SD card, emulator config,
or mod changes are required.

Before any large write, report backend identity, selected package/CNMT/Program identities,
mounted `/data.arc` length and disk budget. Then stream exactly that length to
`gamedata/.../data.arc.partial`, calculating SHA-256. Flush/close and rename only on success.
Write a sidecar report with input paths/sizes, part order, package version/hash, CNMT
versions, NCA IDs/hashes, selected Program index, patch mode, output bytes/hash and errors.
Do not put key values or raw tickets into reports. Failure leaves a clearly labelled
partial and never labels it complete. Catch and sanitize missing-key and integrity errors.
No new task files or test subtasks are part of this contract.

With virtual concatenation, additional payload disk = **A** (mounted archive size),
plus small package/build/report storage; no extra 13.633 GiB join, NSP unpack or full RomFS
image is needed. A transactional replacement retaining an older archive needs another A.
Query A and actual free space at implementation time; reserve A plus a proposed 1 GiB
headroom before a fresh write. T-0032 observed 17,600,869,448 bytes needed plus the 1 GiB headroom requirement
(`requiredFreeBytes` 18,674,611,272) for the patched extraction, with roughly 685 GiB free on D:.
The mod's historical 15 GB warning is not current D: metadata.
Do not remove the existing join to reclaim disk in this task.

Use one reusable 16 MiB copy buffer, never `ReadAllBytes` on NSP/NCA/archive inputs.
RAM additionally includes PFS0/CNMT/RomFS metadata, library caches, patch trees and the
.NET runtime. Their sizes and peak RAM are unmeasured; a fixed small-memory guarantee
is unsupported. Proposed operational budget: 512 MiB with graceful error on insufficient
memory; confirm or revise after an authorized manual extraction, rather than allocating A.
This research run downloaded only code/package documentation, not game content.

## Prerequisites and manual review

- Input files, local DLL and SDK 8.0.201 + .NET 8 runtime are present; setup, restore and build
  were run successfully in T-0032, and the executable contract below is implemented.
- Missing header/master/key-area/titlekek generations: report the exact missing **name or
  generation**, never its value; the user must re-export their own keys into the explicit
  workspace key path. Do not search their profile or download keys/firmware/game data.
- Missing rights key: try matching in-package common tickets in memory. If only personalized
  tickets exist and external title.keys has no matching entry, ask for the user's own
  exported title key (preferred) or device console keys at an explicit workspace path.
- Unsupported NCA generation/format or patch API failure: stop with sanitized error and
  selected IDs. Do not swap to a mirror/fork or claim base-only output is patched. Source
  availability would need renewed official provenance research before changing the pin.

Manual checks for the user are the three in the tool README: setup plus read-only preflight,
the offline extraction with provenance/`.partial` inspection, and opening the resulting archive in
a compatible ARC viewer and extracting one known entry into `gamedata/`. The first two were
executed here as observed runs; the third cannot be done by an agent. No in-game check applies.

## Sources and inspection records

Accessed 2026-10-01. Official package URLs and source commit are above. Scratch records in
`state/scratch/T-0030/`: `nuget-provenance.json`, `official-LibHac.nuspec`,
`official-LibHac.xml`, `current-metadata-api.txt`. The stopped run's `api-signatures.txt`,
`static-api-il.txt`, `additional-api-il.txt` and hashed `LibHac.package.dll` were reused;
the current official DLL comparison establishes the same binary identity. Static metadata
was read with its existing scratch dnfile 0.18.0 parser; no LibHac assembly was loaded/executed.

Alternative inspected and rejected for this contract: official
[SciresM/hactool 1.4.0 source](https://github.com/SciresM/hactool/tree/3121a5bf08cd81d3a99719feb2cab3b60767afd5),
commit `3121a5bf08cd81d3a99719feb2cab3b60767afd5`.
[main.c](https://github.com/SciresM/hactool/blob/3121a5bf08cd81d3a99719feb2cab3b60767afd5/main.c)
supports PFS0, `--basenca`, `--romfsdir`, `--suppresskeys`;
[nca.c](https://github.com/SciresM/hactool/blob/3121a5bf08cd81d3a99719feb2cab3b60767afd5/nca.c)
implements BKTR base/patch reads. However,
[utils.c](https://github.com/SciresM/hactool/blob/3121a5bf08cd81d3a99719feb2cab3b60767afd5/utils.c)
and main.c implicitly search profile key files even with `-k`, and there is no explicit
title-key-file option or integrated ticket input route in that CLI. Using it here would
require extra adaptation to meet workspace isolation and ticket handling. It was not run
and is not marked `does-not-work`. Cached release source filenames start `release-`.
