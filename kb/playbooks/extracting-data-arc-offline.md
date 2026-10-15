---
title: Extracting the patched SSBU data.arc offline
summary: Use tools/data-arc-extract to produce the 13.0.4 (or base-only) data.arc from the local split/update NSPs, with the exact commands, what to check and what stays unverified
status: verified
tags: [dump, extraction, nsp, nca, romfs, data-arc, libhac, gamedata]
updated: 2026-10-02
source: T-0032 (implementation and observed runs)
---

## When to use

Any task that needs the game's `data.arc` as a file: browsing/listing ARC contents, pulling
individual ARC files for the mod workspace, or comparing the unpatched base against 13.0.4.

Use it when the dump is available offline. It replaces the old plan of "extract by hand with a
GUI tool" and is the supported route in this lab. It does **not** cover: live console extraction
(use the mod repo's `fetch_arc_files.py` with arc-network), DLC, other titles, other game
versions, or any emulator run.

Companion notes: [the extraction reference](../reference/offline-data-arc-extraction.md) for
inputs, backend provenance and API details, and [local machine](../reference/local-machine.md).

## Steps

1. Build once (offline restore + compile, ~seconds):
   `powershell -NoProfile -File .\tools\data-arc-extract\setup.ps1 -Build`
   from `<workspace>`. Prerequisites, backend pin and recovery are in the tool
   [README](../../tools/data-arc-extract/README.md).

2. Read-only preflight. It reports identities, patch mode, expected size and disk budget without
   writing anything:

   ```bash
   python tools/data-arc-extract/run.py preflight --base "dump/nxdt_rw_poc/NSP/Super Smash Bros. Ultimate [01006A800016E000][v0][BASE].nsp" --update "dump/nxdt_rw_poc/NSP/Super Smash Bros. Ultimate 13.0.4 [01006A800016E800][v1966080][UPD].nsp" --prod-keys "testenv/ryujinx/data/system/prod.keys" --title-keys "testenv/ryujinx/data/system/title.keys" --backend "Ryujinx/build/LibHac.dll" --output "gamedata/ssbu-13.0.4/data.arc"
   ```

   For base-only content, replace `--update ...` with `--base-only`. `discover` is the weaker mode
   that stops before opening keys or NSP content.

3. Extract (13.0.4, patches applied) - the only difference from step 2 is `preflight` -> `extract`.
   Expect roughly 17.6 GB written under `gamedata/`, plus 1 GiB required headroom.

4. Read the result: `data.arc.provenance.json` beside the archive records identities, patch mode,
   byte counts and the streaming SHA-256.

5. To work with individual ARC files, open the archive in the user's own compatible ARC viewer
   (outside the workspace; deliberately untouched by agents) or ask the user to export specific
   entries into `gamedata/`. Never extract game files into `dump/`, `kb/`, `tools/` or a mod tree.

## How to check it worked

- Preflight prints `"selection": "patched"`, `"selectedVersion": "13.0.4 / CNMT 1966080"`, base
  Program NCA `144389b9a6d0eb19c21cad297fa7dde4` and patch Program
  `c641433fd07f4a934b25aeec19c4d020`, both content index 0, and `expectedBytes` 17600869448.
- Extraction ends with `COMPLETE: <bytes> bytes; SHA-256 <hash>`, the archive length equals
  `expectedBytes`, provenance says `"complete": true` and `originalMetadataUnchanged: true`, and
  no `data.arc.partial` is left.
- The 13.0.4 archive is **larger** than the base-only one (17,600,869,448 vs 14,460,050,172 bytes
  observed). A base-sized result from an `--update` run means the patch did not apply.
- Independent confirmation: recompute the SHA-256 with any tool and compare with the provenance.
- **Not** a substitute for opening the archive: see the pitfall below.

## Known pitfalls

- **No viewer means unverified.** The pipeline ran and hashes matched here, but no ARC viewer
  exists inside the workspace, so archive readability and 13.0.4 content correctness are still
  unconfirmed. A correct size and hash prove the bytes were streamed faithfully, not that they are
  the right version. Ask the user to open it - see
  [the note](../findings/data-arc-extraction-needs-user-viewer-check.md).
- **No overwrite, no resume.** An existing output, `.partial` or report stops the run. Pick a fresh
  destination or move the old one aside yourself; never delete a `.partial` before reading its
  journal.
- **Never trust the filename.** `[BASE]`, `13.0.4` and `[UPD]` are nxdumptool labels. Selection is
  metadata-based; a DLC package is rejected by title/type, not by name.
- **A hard kill is survivable but not complete.** Ctrl+C is clean; task-manager kill leaves a
  `.partial` plus an `in-progress` journal and no final archive. Treat that as incomplete.
- **Split-directory errors are specific.** Parts must be contiguous two-digit names from `00` and
  non-empty. A gap or an empty part is a re-export problem, not a tool bug.
- **Key gaps name only the key.** If a generation key is missing, the tool prints the key *name*
  and asks for the user's own re-export; it never searches profiles or downloads keys. Never paste
  key values into notes.
- **Base-only is not 13.0.4.** Base-only output is smaller and labelled; do not use it for 13.0.4
  work, and do not describe it as patched.

## Suitable tier

**worker.** The tool and commands exist and are documented; the work is running the documented
commands and reading JSON, not designing a format pipeline. It needs **user** review at the end
(one viewer check), because agent-side verification cannot settle archive readability.
