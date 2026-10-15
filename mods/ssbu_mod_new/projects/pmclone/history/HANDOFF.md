# Developer handoff

**Latest continuation:** [Handoff to Space Bunny Alpha](HANDOFF_SPACE_BUNNY_ALPHA.md)
contains the deployed recorder checkpoint, next console test, known gaps, and
current authorization context. Start there when resuming this session.

## Recorder continuation, 2026-09-28

The partially implemented `trace/` recorder has been reviewed, hardened and built
as v0.1.1. Use [trace/README.md](trace/README.md) for the first hardware test and
limitations. Isolated package: `test_output/PyraMythra_trace_check.zip`; NRO is also
published locally under `../mod_output/new_standalone`, then installed on the SD
at the user's request as recorded below.
The ZIP contains only the recorder plus instructions/manifest, not the old loader.

Build and static package checks passed; 19 PC comparison tests passed. Evidence:
[reports/trace-build.json](reports/trace-build.json) and
[reports/trace-continuation.md](reports/trace-continuation.md).
**SD deployment: 2026-09-28.** At the user's explicit request, copied only
`libpmclone_trace.nro` to `sd:/atmosphere/contents\01006A800016E000\romfs\skyline\plugins\`.
SHA-256 verified as
`2b54f5cb0edb54411bacee3bfac67525f67eecf812a7b7199815d15bdaa99945`.
Read-only CHKDSK reported no file-system problems. This is a file-copy verification,
not a console test. **M0 is not complete:** exact replay timing is unproven and
full state restoration/measurement is incomplete. Next: record normal Mythra,
replay twice, collect all three traces plus the log. Do not begin clone crash-chain
work on an assumed passing recorder baseline.

**Read [ASSESSMENT.md](ASSESSMENT.md) first (2026-09-28).** It supersedes the
"Proposed continuation" section below: exactness now comes from running the
original code via Clone Engine and verifying each replacement with frame traces;
native relocation is parked. Cheaper-model tasks: [HANDOFF_WEAK_MODEL.md](HANDOFF_WEAK_MODEL.md).

Updated 2026-09-28. This project is **not a playable clone**. The latest artifact
is the installed, console-untested trace recorder. The earlier private-module
loading diagnostic passed its console test. No new fighter kind, character-select
entry, transformation registration or clone gameplay hooks exist yet.

Dump acquisition update: **resolved 2026-09-28** — all 36 missing archive inputs
extracted, live archive copies identical to earlier exports, title screen reports
13.0.4 (matches the ExeFS dump; build ID not read from the process). The refused
connection was a deleted `libarc_network.nro` on the SD, not Arc Explorer. Evidence:
`reports/live-verification-2026-09-28.json`. Original request: [DUMP_REQUEST.md](DUMP_REQUEST.md).

Earlier note: ExeFS is now
snapshotted and decoded reproducibly inside this project, with verified segment
hashes and exact agreement with the earlier main analysis image. The archive
inventory identified 36 additional missing inputs. Live archive comparison and
running executable identity remain unverified; the network archive connection
is currently refused. This does not change the gameplay implementation status.

## Requirement and working boundaries

Create one additional selectable Pyra/Mythra pair, with eight costumes, while
the originals remain available. Character-specific assets, code, parameters,
articles and transformation state must have independent ownership so edits to
the clone do not alter the originals. Copying a vtable while retaining the
original function pointers does not meet that requirement.

The current design shares general engine services. Any uncertain dependency
must be investigated before classifying it as a shared service. Complete
character independence is a target, not a property established by the loader test.

Work in this directory; earlier experiments are not the implementation base.
Some original dumps/tools are still referenced outside it (listed below).
The user performs console testing. The SD card was most recently mounted at
`sd:/`. The earlier read-only restriction was superseded for recorder installation
by the user's explicit request, and that installation is complete (see above).
Publish locally to `../mod_output/new_standalone`; it contains multiple diagnostic
artifacts, so use the isolated recorder ZIP for recorder-only installation.
The Switch address previously used was `192.168.2.166`.

## Proven checkpoint and limitations

| Area | Evidence and current result |
| --- | --- |
| Asset copies | `reports/assets.json` and `summary.json`: 9,234 independent files, 1,002,428,554 bytes, no missing files in the named-resource inventory |
| Motion references | 90 motion lists retargeted; no unresolved directories or missing referenced animations in that check |
| Private modules | `reports/namespaced-modules.json`: cflame, clight, clement; 27 exported factories; 2,315 relocations |
| Console loader | `reports/console-loader-2026-09-28/loader.log` and `result.json`: 11 + 11 + 5 factories inside private executable images; three isolation guards passed; all four SD NRO hashes matched the built files |
| Character-native code | 22 directly imported functions and 143 candidate class-method roots inventoried; raw snapshots are not executable relocated implementations |
| Playable clone | Not implemented or tested |

The console test did **not call the factories**. NRO imports initially resolve
against existing game symbols. The loader checks those slots, then withholds
factory access until private character implementations are supplied. The test
passed because the copied modules loaded and this guard remained closed. It
does not demonstrate independent gameplay, complete data ownership, coexistence,
or that every character-specific dependency has been identified.

The initial package put `plugin.nro` in the wrong folder. The user moved it into
Skyline's plugins folder, which produced the passing test. The packager and local
output are corrected. The passing evidence belongs to the exact recorded hashes;
future changed binaries need their own console evidence.

## Code and report map

| File/directory | Responsibility |
| --- | --- |
| `tools/prepare.py` | Copy resources, preserve edit conflicts, retarget motion lists, generate asset reports |
| `tools/extract_missing.py` | Read archive resources using Arc Explorer's DLL/network archive service |
| `tools/audit_native.py` | Parse NRO dynamic symbols, imports and relocations |
| `tools/namespace_modules.py` | Rename modules/exports, rebuild ELF lookup tables, generate NROs and `runtime/src/modules.rs` |
| `tools/inventory_native_classes.py` | Inspect main class/vtable tables and unwind records; inventory method dependencies |
| `tools/snapshot_references.py` | Preserve vanilla ACMD text and shared database references |
| `tools/package_loader_check.py` | Package the diagnostic ZIP and publish the local SD tree; validate NRO copies |
| `runtime/src/lib.rs` | Worker waits for common imports, loads modules, records diagnostics; no gameplay registration |
| `runtime/src/loader.rs` | NRR registration, private images/BSS, hash/symbol checks, guarded character-import rebinding |
| `runtime/src/modules.rs` | Generated paths, hashes, exports and character import slots; regenerate rather than hand-edit |
| `native/main-functions`, `native/class-functions` | Research snapshots, not ready-to-run native code |
| `reference/acmd`, `reference/shared` | 924 script references and eight shared database snapshots |
| `upstream/clone_engine` | Reference implementation, pinned in README; pointer copying alone is insufficient |

The rebinding API accepts declared owned code ranges, verifies replacement
addresses and writes import slots. It is currently unused. Range membership
alone cannot establish that the replacement's transitive calls/data are private;
the dependency audit and future executable mapping must establish that first.
Loaded module allocations deliberately remain resident until process exit.

## Build and package

Observed local environment: Windows PowerShell, Python 3.8.10, cargo-skyline
3.5.0, rustup toolchain `skyline-v3`. Host rustc reports 1.98.1; cargo-skyline
uses its Switch toolchain. `runtime/Cargo.lock` pins resolved dependencies and
`Cargo.toml` pins skyline-rs. A fresh-machine toolchain bootstrap has not been
validated. The class inventory imports Capstone from the existing reference
tools directory; the global Python installation also has Capstone 5.0.9.

From the workspace root (`<workspace root>`):

```powershell
Push-Location .\pyra_mythra_clone\runtime
try {
    cargo skyline build --release
    if ($LASTEXITCODE -ne 0) { throw 'Runtime build failed' }
} finally {
    Pop-Location
}
python .\pyra_mythra_clone\tools\package_loader_check.py
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
```

The package currently contains only four NROs and diagnostic metadata, not the
prepared asset collection. Correct SD layout:

```text
atmosphere/contents/01006A800016E000/romfs/skyline/plugins/plugin.nro
ultimate/mods/PyraMythraClone/info.toml
ultimate/mods/PyraMythraClone/native/modules/lua2cpp_cflame.nro
ultimate/mods/PyraMythraClone/native/modules/lua2cpp_clight.nro
ultimate/mods/PyraMythraClone/native/modules/lua2cpp_clement.nro
```

Do not install a second copy of the runtime under another plugin filename.
Disabling the ARCropolis folder alone does not disable a Skyline plugin.
The local packager overwrites its generated outputs; preserve manual edits
before running it. It removes the old misplaced local plugin only when its
bytes match the runtime being packaged. It does not write to the SD card.

## Inputs needed by another contributor

The project folder alone is not a complete clean-machine reproduction bundle.
Keep the following user-supplied inputs available or adapt the scripts' paths:

- `../export`: original extracted resources, including the three original NROs.
- `../mod_files/mgw_standalone/vendor/clone_pack_workbench/arc_index/arc_files.tsv`:
  vanilla filename index, reused as data only; SHA-256 recorded in the asset report.
- `../references/mythra_gamewatch_feasibility/main_memory.bin`: main image,
  SHA-256 `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`.
- `../references/mythra_gamewatch_feasibility/python_tools`: existing Capstone
  dependency location used by the class inventory.
- `ArcExplorer tools directory`: installed archive DLL used
  only when further extraction is needed. Close Arc Explorer during extraction
  because the archive server serialized clients in this session.

The README lists the preparation commands. Do not re-extract all resources just
to build the existing diagnostic. The current main image predates this work and
has not been matched against the running console's executable build; the loader
test does not validate main offsets. Validate the executable identity before
using those offsets in live code.

Reproduction gap: the 22 `native/main-functions` disassembly snapshots were
created during investigation; `audit_native.py` does not regenerate those
snapshots. Preserve them and add a reproducible generator before relying on them
as build inputs. The 143 class-method snapshots have a checked-in generator.

`summary.json` reports asset preparation. `runtime_implemented: false` means
the playable runtime is absent, not that the diagnostic loader is absent.
Use `loader-build.json` and the dated console evidence for loader status.
Historical extraction recovery reports describe an earlier disk-space failure.

## Proposed continuation and acceptance gates

1. **Establish the native dependency boundary.** Verify the main image/version,
   then trace calls and data from the 22 direct imports and 143 candidate roots.
   Record each edge as private character code/data, justified generic engine
   service, or unresolved. Current candidate inventory has 144 external direct
   branches, 342 PC-relative references and 551 indirect transfers. Shared
   function pointers across classes are clues, not proof of generic behavior.
   The next concrete deliverable should be a reproducible dependency manifest
   with offsets, bounds, classifications, reasons and unresolved entries.
2. **Make the required native copies executable.** Implement relocation or
   equivalent independent implementations for the audited character code/data.
   Cover PC-relative addressing, direct/indirect branches, jump tables, vtables,
   writable state and any exception/unwind requirements. Establish executable
   allocation/cache handling and object lifetime. Fail on unsupported cases.
   Validate relocation targets and preservation of shared-call targets before
   connecting `bind_character_imports`. Do not open the guard just to get a slot.
3. **Finish private resource routing.** Trace internal sound/effect/parameter/UI/
   script identifiers and shared database rows; assign private identities and
   ownership. A private directory name does not isolate an embedded identifier.
   Keep a manifest of original-to-clone identities and any shared dependencies.
4. **Integrate the character pair.** Establish fighter/article allocation and
   lifetimes, then roster entry, both forms, transformations, damage/stocks,
   Final Smash and results. Evaluate the pinned engine's extension points;
   native pair support and independence are not established. First smoke-test
   one form in a match, then articles and the other form, then switching.
5. **Prove behavior and edit independence.** Test originals and clone together,
   every costume, attacks, both switch directions, respawn, Final Smash, Kirby
   copy, results and rematch. Make one controlled clone-only asset edit,
   parameter edit and character-function edit; confirm the originals remain
   unchanged. Preserve logs, hashes and a test matrix for each build.

This is substantial reverse engineering. A separate selectable icon is not the
hardest remaining piece, and there is not enough evidence for a reliable finish
date. If native dependencies cannot be isolated using the current approach,
document that result and reassess the implementation before claiming completion.

## Console testing protocol

The user installs/tests builds. For the current diagnostic, close Smash before
copying, then start a normal match within five minutes of launching Smash.
Inspect `ultimate/pyra_mythra_clone/loader.log`. Required completion:

```text
PRIVATE_MODULE_LOAD_CHECK_PASSED: all 27 factories belong to private executable images; no fighter installed
```

Also require all three module counts (11, 11, 5), three guard-pass lines, and
matching artifact hashes. A missing completion or `REFUSED` is incomplete/failure.
Preserve Atmosphere crash reports if present and correlate their timestamps with
the test; an older crash report is not evidence that the current build crashed.
Copy evidence to a new local dated report folder without modifying the SD.
Future tests need explicit checks for the newly implemented behavior; the above
loader message will never by itself prove the full clone works.
