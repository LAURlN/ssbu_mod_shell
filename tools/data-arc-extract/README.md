---
purpose: Offline, workspace-confined extraction of the patched SSBU 13.0.4 data.arc (or the unpatched base) from the local split/update NSPs
usage: python tools/data-arc-extract/run.py <discover|preflight|extract> --base PATH (--base-only | --update PATH) --prod-keys PATH [--title-keys PATH] --backend PATH --output gamedata/.../data.arc
status: experimental
lang: csharp
updated: 2026-10-02
source: T-0032 implementation; T-0031 setup scaffold; T-0030 backend contract
---

Extracts the SSBU Program content's **effective** RomFS `/data.arc` entirely offline, using the
existing hash-pinned LibHac 0.19.0 DLL. It selects the base and update Program content from
container metadata (CNMT/NCA identity), applies the update's RomFS patches over the base through
the backend, and streams only the effective `data.arc`. It never launches Ryujinx, never reads a
key file outside the explicit paths you pass, never writes to `dump/`, and never writes any
game-derived file outside `gamedata/`.

**Status is `experimental`.** The mechanism ran here end to end (see "Observed runs"), but
**archive readability and version correctness are unverified**: no ARC viewer exists inside the
workspace, so nobody has opened the result yet. The older `tools/README.md` rule that a tool must
be registered only after a real-input run is satisfied for the extraction itself; the remaining
exception is viewer compatibility, which is why the status is not `working`.

## Commands

Run from the workspace root `<workspace>`. PowerShell or Git Bash both work; the
examples below are shell-neutral except for the `setup.ps1` line.

### 1. Setup (offline restore and build, once)

```powershell
powershell -NoProfile -File .\tools\data-arc-extract\setup.ps1 -Build
```

`setup.ps1` verifies the backend SHA-256 against `backend.lock.json`, checks SDK 8.0.201 plus a
`Microsoft.NETCore.App 8.0` runtime, restores project metadata offline with a source-cleared
`NuGet.Config`, and builds into the ignored `tools/data-arc-extract/.cache/`. It installs nothing,
downloads nothing and changes no emulator configuration. Add `-BackendPath`,
`-CachePath`, `-BuildPath` or `-DotnetPath` for explicit control; every destination must stay
inside `state/` or this tool's `.cache/`.

### 2. Read-only discovery (no keys opened, no container parsing)

```bash
python tools/data-arc-extract/run.py discover --base "dump/nxdt_rw_poc/NSP/Super Smash Bros. Ultimate [01006A800016E000][v0][BASE].nsp" --base-only --prod-keys "testenv/ryujinx/data/system/prod.keys" --title-keys "testenv/ryujinx/data/system/title.keys" --backend "Ryujinx/build/LibHac.dll" --output "gamedata/ssbu/data.arc"
```

Reports resolved split parts, summed input bytes, key/backend paths and the pinned backend hash,
then stops before opening key files or any NSP content. `--update` is accepted here too.

### 3. Read-only preflight (identities, patch mode, expected size, disk budget)

```bash
python tools/data-arc-extract/run.py preflight --base "dump/nxdt_rw_poc/NSP/Super Smash Bros. Ultimate [01006A800016E000][v0][BASE].nsp" --update "dump/nxdt_rw_poc/NSP/Super Smash Bros. Ultimate 13.0.4 [01006A800016E800][v1966080][UPD].nsp" --prod-keys "testenv/ryujinx/data/system/prod.keys" --title-keys "testenv/ryujinx/data/system/title.keys" --backend "Ryujinx/build/LibHac.dll" --output "gamedata/ssbu-13.0.4/data.arc"
```

Opens the packages **read-only**, registers in-package tickets, selects the Program content and
mounts the effective RomFS, then prints identities, expected byte count and the free-space
requirement **without writing anything**.

### 4. Extraction, base only (unpatched vanilla)

```bash
python tools/data-arc-extract/run.py extract --base "dump/nxdt_rw_poc/NSP/Super Smash Bros. Ultimate [01006A800016E000][v0][BASE].nsp" --base-only --prod-keys "testenv/ryujinx/data/system/prod.keys" --title-keys "testenv/ryujinx/data/system/title.keys" --backend "Ryujinx/build/LibHac.dll" --output "gamedata/ssbu-base/data.arc"
```

### 5. Extraction, real 13.0.4 (base + update, patches applied)

```bash
python tools/data-arc-extract/run.py extract --base "dump/nxdt_rw_poc/NSP/Super Smash Bros. Ultimate [01006A800016E000][v0][BASE].nsp" --update "dump/nxdt_rw_poc/NSP/Super Smash Bros. Ultimate 13.0.4 [01006A800016E800][v1966080][UPD].nsp" --prod-keys "testenv/ryujinx/data/system/prod.keys" --title-keys "testenv/ryujinx/data/system/title.keys" --backend "Ryujinx/build/LibHac.dll" --output "gamedata/ssbu-13.0.4/data.arc"
```

Command 5 is the command the lab uses. It produces the 13.0.4 archive; command 4 deliberately
produces a *different, smaller* archive and is labelled `base-only` in every report.

## Precedence and what the output means

- `--base-only` and `--update` are mutually exclusive and one is **required**. Passing both, or
  neither, is an error. An update is never silently dropped and the base is never silently
  substituted: if the update cannot be selected or mounted, the run fails with a diagnostic and
  leaves no final archive.
- With `--update`, the report says `"selection": "patched"` and `"selectedVersion":
  "13.0.4 / CNMT 1966080"`. With `--base-only` it says `"base-only"` / `"base CNMT v0"`. The
  patched archive is larger (17,600,869,448 bytes here) than the base-only one
  (14,460,050,172 bytes); a base-sized result from an `--update` run would mean no patch applied.
- **Identity comes from metadata, not filenames.** The tool parses the Meta NCAs and CNMTs, then
  requires base title `01006A800016E000` version 0 type Application, and patch title
  `01006A800016E800` version 1966080 type Patch whose `ApplicationTitleId` links to the base.
  Each CNMT's `Program` content entry is resolved to `<ncaid>.nca`, size-checked, and the
  decrypted header must be Program content with SSBU's title ID and `ContentIndex == 0` plus a
  Data section. Exactly one candidate must remain. Filenames such as `[BASE]`, `13.0.4` or
  `[UPD]` are never trusted; a DLC or mismatched package is rejected.
- The update's RomFS is **not** used as a directory overlay and `data.arc` files are never
  concatenated. The base Program NCA is mounted with `OpenFileSystemWithPatch(update, Data,
  ErrorOnInvalid)`, so block-level patch precedence is the backend's, and only the mounted
  `/data.arc` is read.

## Inputs

| argument | meaning |
|---|---|
| `--base` | Split NSP **directory** (`00`-`03`) or an already-joined NSP file. Parts are opened read-only and concatenated in memory, never joined on disk. |
| `--update` | Single-file update NSP. Split update directories are rejected. |
| `--prod-keys`, `--title-keys` | Explicit key files. No profile discovery, no default key paths, no console-key search. |
| `--backend` | The pinned LibHac 0.19.0 DLL; hashed before and after load. |
| `--output` | Final archive path. **Must be under `gamedata/`.** |
| `--workspace` | Supplied by `run.py`; a manually launched DLL must match its own workspace. |

Split handling requires two-digit part names `00`..`NN` forming a contiguous sequence from `00`,
each part a non-empty regular file, with 64-bit summed offsets. Gaps, empty parts and unexpected
files are rejected. Reads are bounded: one 16 MiB copy buffer plus a fixed 16 MiB buffer, a
16 MiB PFS0 metadata cap, 64 KiB per ticket and 16 MiB per CNMT. `ReadAllBytes` is never used on
an NSP, NCA or the archive.

An **existing joined base** can be reused explicitly by passing the joined file as `--base`; this
was exercised here and produced identical identities to the split directory
(`testenv/ryujinx/roms/Super Smash Bros. Ultimate [01006A800016E000][v0][BASE].nsp`). Prefer the
split directory as the default, since that joined copy's provenance is not the dump's.

## Outputs, temporary files and disk

- Written next to the archive, all under `gamedata/`: `data.arc` (final only on success),
  `data.arc.provenance.json` (final report), and during the run `data.arc.partial` plus
  `data.arc.provenance.json.partial` (the live journal).
- **Nothing else is written anywhere.** No join, no unpacked NSP, no full RomFS image, no staging
  copy. Tool caches live under the ignored `tools/data-arc-extract/.cache/`; `run.py` also points
  `TEMP`/`TMP` there so the runtime cannot scatter temporary files.
- Disk cost is exactly the archive plus a small report: **17,600,869,448 bytes + 1 GiB required
  headroom** for the 13.0.4 extraction (preflight reports `requiredFreeBytes`; it refuses to start
  when free space is lower). Base-only needs 14,460,050,172 + 1 GiB. Observed D: free space was
  about 685 GiB, so this is comfortable; peak RAM was not measured.
- **No overwrite.** If the output, its `.partial` or its report already exists, the run stops and
  asks for a fresh destination. There is no resume; delete a stale `.partial` yourself after
  inspecting its journal.

## Failure and interruption behaviour

Streaming writes only to `data.arc.partial` and updates the journal at least once per GiB.
Finalization happens only after the backend reports the full expected byte count, the streamed
length matches, and every input's size and timestamps are still identical to preflight. Then the
`.partial` is renamed to the final path and the journal to the report.

If anything fails, the journal is rewritten with `"complete": false` and a `state` of `failed` or
`interrupted`. An archive at the final path is rolled back to `.partial`. Ctrl+C is handled
cleanly; a hard kill (task manager) leaves a `.partial` plus an `in-progress` journal, which is
correct and must be treated as incomplete. Both were observed here: a killed run left
`data.arc.partial` and an `in-progress` journal with a truthful `outputBytes`, and **no final
archive**. Disk exhaustion fails the same way and says so.

## Provenance and secrets

`data.arc.provenance.json` records input paths, sizes and timestamps, split part order, backend
version and SHA-256, CNMT title/version/type/`ApplicationTitleId`, CNMT SHA-256, Program NCA id,
CNMT-expected Program hash, selected content index and key generation, patch mode, expected and
written bytes, free-space figures, the streaming SHA-256 of the archive, completion state and
whether the originals were unchanged. **No key values, tickets or key file contents are ever
written**; only a conservative key *name* appears if a key is missing.

## Errors you may see

| message | meaning / action |
|---|---|
| `Choose exactly one: --base-only OR explicit --update.` | Supply exactly one. No fallback exists. |
| `Every derived output must be under gamedata/`. | Move `--output` under `gamedata/`. |
| `Traversal components are rejected` / `Symlink/junction/reparse-point paths are unsupported.` | Use a direct, real workspace path with no `..`, junction or symlink. |
| `Existing output/partial/report protected` | Pick a new destination; nothing was overwritten. |
| `Missing/unexpected split part; expected NN` / `Empty/non-file split part` | Re-export or repair the split dump. |
| `Expected ordinary uncompressed PFS0 NSP; XCI/NSZ unsupported.` | Point at the real NSP. |
| `Mismatched/DLC content: expected ... found ...` | Wrong package supplied (DLC, another title). |
| `Unsupported CNMT version N; supported ... only.` | Unsupported version; no silent downgrade. |
| `Expected exactly one application/patch CNMT` / `Expected one unambiguous SSBU Program #0` | Ambiguous or incomplete package. |
| `missing header_key / master_key_xx / titlekek_xx / key_area_key_...` | Re-export your own matching keys to the explicit workspace key paths. Only the name is printed. |
| `Personalized ticket cannot be unwrapped; supply your own matching external title.keys.` | Provide a matching `title.keys` entry. No device-key search is attempted. |
| `Backend hash mismatch` / `Loaded backend differs from pinned LibHac 0.19.0.` | Re-run pinned setup. Never edit the pin. |
| `Insufficient space; need effective archive bytes plus 1 GiB headroom.` | Free space below the reported requirement. |
| `Backend/input/integrity or disk operation failed...` | Sanitized catch-all; check identities, keys, free space and permissions. Raw backend text is suppressed so secrets cannot leak. |

Exit codes: `0` success, `1` failure with a diagnostic on stderr, `130` interrupted.

## Observed runs (2026-10-02, this workspace)

Compilation and both extractions were run here; these are observed values, not a promise:

- `setup.ps1 -Build`: offline restore and Release build, 0 warnings, 0 errors, output under
  `tools/data-arc-extract/.cache/build/bin/`.
- Base-only preflight: Program NCA `144389b9a6d0eb19c21cad297fa7dde4`, content index 0, key
  generation 8, effective `data.arc` **14,460,050,172 bytes**.
- 13.0.4 preflight and extract: base as above plus patch Program NCA
  `c641433fd07f4a934b25aeec19c4d020` (CNMT title `01006A800016E800`, version 1966080, type Patch,
  `ApplicationTitleId` `01006A800016E000`), effective `data.arc` **17,600,869,448 bytes**,
  SHA-256 `ef615e671e1d4907f0a707f2eb13e3cb0c8539c4e67ac51c89ef547c22b82995`. The hash was
  recomputed independently with Python `hashlib` and matched. Provenance reported
  `"complete": true`, `originalMetadataUnchanged: true`, and the dump parts and key files kept
  their original sizes and timestamps.
- Base-only extract (same session, then deleted to reclaim 14 GiB):
  14,460,050,172 bytes, SHA-256 `f15156141f065283385e5efee77256f1ea72d5970f17a70292a153388a2253a8`.
- Rejection paths exercised: DLC package rejected with
  `Mismatched/DLC content: expected Application title 01006A800016E000, found AddOnContent 01006A800016F001`;
  split gap, empty part, non-PFS0 content, `--base-only` + `--update` together, neither flag,
  `..` traversal, output outside `gamedata/`, output outside the workspace and output equal to an
  input file were all rejected with their specific messages.
- The 13.0.4 archive currently on disk is `gamedata/ssbu-13.0.4/data.arc` (gitignored).

**Unverified:** whether an ARC viewer can open either archive, and whether the patched archive is
really 13.0.4 content rather than a correctly-sized wrong payload. Neither the base-only nor the
patched archive has been opened. Peak RAM, throughput and viewer compatibility are also unmeasured.

## Manual checks for the user

Exactly three, in order:

1. **Setup + read-only preflight.** Run
   `powershell -NoProfile -File .\tools\data-arc-extract\setup.ps1 -Build`, then the command-3
   `preflight` line above. **Pass** if it ends with `"selection": "patched"`,
   `"selectedVersion": "13.0.4 / CNMT 1966080"`, base Program
   `144389b9a6d0eb19c21cad297fa7dde4` at content index 0, patch Program
   `c641433fd07f4a934b25aeec19c4d020`, `expectedBytes` 17600869448, an output under `gamedata/`
   and no file created anywhere. **Fail** if prerequisites are reported missing, the identities
   differ, or any file appears outside `gamedata/`.

2. **Extraction, completion and provenance.** Delete nothing first; because no-overwrite is
   enforced, either use a fresh `--output` (for example `gamedata/ssbu-13.0.4-check/data.arc`) or
   move the existing `gamedata/ssbu-13.0.4/data.arc` aside, then run the command-5 `extract` line.
   **Pass** if the last line is `COMPLETE: 17600869448 bytes; SHA-256
   ef615e671e1d4907f0a707f2eb13e3cb0c8539c4e67ac51c89ef547c22b82995`, `data.arc` is exactly
   17,600,869,448 bytes, `data.arc.provenance.json` says `"complete": true` with
   `originalMetadataUnchanged: true` and no key values, and **no `data.arc.partial` remains**.
   Also confirm the dump parts still show their original sizes and timestamps. **Fail** if a
   `.partial` survives, the provenance disagrees with the archive, or any original changed.

3. **Read the archive in a viewer, yourself.** There is **no ARC viewer inside the workspace**;
   the compatible viewer this lab knows about is the user's own ArcExplorer install outside it, and
   this task deliberately did not touch that path. Either open
   `gamedata\ssbu-13.0.4\data.arc` in that existing ArcExplorer, or
   provide an equivalent workspace-local compatible ARC viewer as a prerequisite. Browse a few
   representative entries and extract exactly one known entry into `gamedata/` only (for example
   under `gamedata/ssbu-13.0.4/viewer-check/`). **Pass** if the archive opens, the file tree looks
   like normal SSBU data, and the one extracted file is readable; **fail** if it refuses to open or
   the tree is garbled. Do not start the game and do not copy assets outside the workspace.

Archive readability and 13.0.4 version correctness are settled only by check 3.

## Recovery

- Missing/wrong `dotnet`: point `-DotnetPath` at a complete SDK 8.0.201 distribution already inside
  the workspace. Do not install globally.
- Missing/incompatible backend: supply another workspace-local DLL matching `backend.lock.json`,
  or acquire only the pinned official `officialPackage` URL into `state/dependencies/` and verify
  the package SHA-256 **before** unpacking. Never substitute a fork or edit the pin.
- Stale `.partial`/report: read its journal, then delete it yourself and choose a fresh output.

## Out of scope

No emulator launch, no game/key download, no modification of `dump/`, no copying of game files out
of the workspace and no mod changes. Backend/API and resource details live in
[kb/reference/offline-data-arc-extraction.md](../../kb/reference/offline-data-arc-extraction.md) and
the step-by-step procedure in [kb/playbooks/extracting-data-arc-offline.md](../../kb/playbooks/extracting-data-arc-offline.md).
