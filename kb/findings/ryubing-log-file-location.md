---
title: Ryubing Windows logs prefer the executable directory and fall back to the user profile
summary: Pinned mirror writes Logs beside the Windows executable and can fall back outside a custom data root
status: unverified
tags: [ryujinx, ryubing, emulator, logging]
updated: 2026-10-01
source: T-0002; official https://docs.ryujinx.app/guides/setup-guide/; mirror https://github.com/Leuconoe/Ryubing/tree/793ca017ff4f6e48b798a62d2486405bfc42ef39
---

## What

**The inspected mirror normally writes Windows desktop logs into `<executable base>/Logs`, not the custom `-r` data root.** If creation of that directory fails, it tries `%APPDATA%/Ryujinx/Logs` even with a custom root. File logging is enabled by `Config.json` key `enable_file_log`; filenames are `Ryujinx_<version>_<yyyy-MM-dd_HH-mm-ss>.log` or `Ryujinx_Canary_<version>_<yyyy-MM-dd_HH-mm-ss>.log`. These are pinned-source conclusions, not verified emulator output or a determination of the unavailable current official release.

## Evidence

### Sources and limits (read 2026-10-01)

1. **Official source first:** https://git.ryujinx.app/ryubing/ryujinx returned web-fetch `Failed to fetch https://git.ryujinx.app/ryubing/ryujinx: (400) Timeout fetching`. Python `urllib.request.urlopen` with a 20-second timeout returned `URLError <urlopen error timed out>` for that URL and https://git.ryujinx.app/projects/Ryubing (the address linked by official docs). Current official revision and current release equivalence could not be determined.
2. **Official docs:** https://docs.ryujinx.app/ and https://docs.ryujinx.app/guides/setup-guide/ were reachable. Read the organisation https://github.com/Ryubing and its repos https://github.com/Ryubing/docs and https://github.com/Ryubing/Website. GitHub commits API pinned docs HEAD to `8bbea28d757e2582b3d954672b65b99bbbcf3199` (2026-04-15T04:31:51Z) and Website HEAD to `8286c57963b2cfabfd43ed78695c5af44ee10f35` (2026-07-25T00:38:03Z). Website is only provenance/context, not implementation evidence.
3. **Implementation fallback:** https://github.com/Leuconoe/Ryubing, **mirror, may be older than current Ryubing**, with downstream changes. All implementation links below pin commit `793ca017ff4f6e48b798a62d2486405bfc42ef39` (committer date 2026-08-05T02:20:44Z, metadata previously fetched in T-0004 and read again here). This establishes the inspected source behavior, not the behavior of the unavailable current official build. Source text and GitHub API metadata are cached only under `state/scratch/T-0003/`; no binaries were fetched.

### Directory selection

All rows cite [src/Ryujinx.Common/Configuration/AppDataManager.cs, line 127](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.Common/Configuration/AppDataManager.cs#L127) (`SetUpLogsDir`, lines 127-223) at the pinned mirror revision.

| Mode / platform | First choice | Fallback |
|---|---|---|
| Windows, UserProfile or Custom (`-r`) | `AppDomain.CurrentDomain.BaseDirectory/Logs`, beside executable | OS `ApplicationData/Ryujinx/Logs` (normally `%APPDATA%/Ryujinx/Logs`), not `BaseDirPath/Logs` for a custom root |
| Portable (all platforms) | `BaseDirPath/Logs`, e.g. `<exe>/portable/Logs` | None; returns null if directory creation fails |
| macOS, non-portable | `~/Library/Logs/Ryujinx` | `BaseDirPath/Logs` if directory creation fails |
| Linux, non-portable | OS `ApplicationData/Ryujinx/Logs`, source comment gives `~/.config/Ryujinx/Logs` | None; returns null if directory creation fails |

Important qualification: Windows fallback is triggered by an exception from `Directory.CreateDirectory`, **not by a general write-access probe**. If an existing primary directory can be resolved but a log file cannot be opened, the logger does not retry a different parent. [src/Ryujinx/Systems/Configuration/LoggerModule.cs, line 45](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Systems/Configuration/LoggerModule.cs#L45) (lines 45-76) tries only `LogsDirPath`, removes the file target on failure, and prints an error. [src/Ryujinx.Common/Logging/Targets/FileLogTarget.cs, line 76](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.Common/Logging/Targets/FileLogTarget.cs#L76) (lines 76-92) catches file-open access/IO errors and returns null. Both directory-creation attempts failing also leave no usable log directory. `SetupBasePaths` selects `LogsDirPath` during initialization ([src/Ryujinx.Common/Configuration/AppDataManager.cs, line 225](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.Common/Configuration/AppDataManager.cs#L225)); `GetOrCreateLogsDir` can repeat setup if the directory disappears ([src/Ryujinx.Common/Configuration/AppDataManager.cs, line 114](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.Common/Configuration/AppDataManager.cs#L114)).
### File name and enabling key

- [src/Ryujinx.Common/Logging/Targets/FileLogTarget.cs, line 70](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.Common/Logging/Targets/FileLogTarget.cs#L70) (lines 70-79): version from `ReleaseInformation.Version`; prefix `Ryujinx_Canary` for canary, otherwise `Ryujinx`; local `DateTime.Now` formatted `yyyy-MM-dd_HH-mm-ss`; extension `.log`. Files are opened in append mode with read sharing.
- [src/Ryujinx/Systems/Configuration/ConfigurationFileFormat.cs, line 30](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Systems/Configuration/ConfigurationFileFormat.cs#L30): config property `EnableFileLog`. [src/Ryujinx/Systems/Configuration/ConfigurationFileFormatSettings.cs, line 7](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Systems/Configuration/ConfigurationFileFormatSettings.cs#L7) constructs the serializer with default options from [src/Ryujinx.Common/Utilities/JsonHelper.cs, line 21](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.Common/Utilities/JsonHelper.cs#L21); the snake-case transformation at lines 54-82 establishes the exact JSON spelling **`enable_file_log`**. Set it to `true`. [src/Ryujinx/Systems/Configuration/ConfigurationState.cs, line 169](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Systems/Configuration/ConfigurationState.cs#L169) enables it by default; [src/Ryujinx/Systems/Configuration/LoggerModule.cs, line 45](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Systems/Configuration/LoggerModule.cs#L45) adds/removes the file target when the setting changes.
- Headless has a separate `--disable-file-logging` option ([src/Ryujinx/Headless/Options.cs, line 350](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Headless/Options.cs#L350)), not a desktop CLI logging toggle.

### Local observation and commands

Read-only `Test-Path (Join-Path $env:APPDATA 'Ryujinx/Logs')` returned `False` on 2026-10-01. The task identifies that folder as the user's 2024 config-version-51 data folder. Absence is compatible with logs beside a historical executable, but proves neither their historical location nor whether logging was enabled. No user config, key, firmware, or game contents were read/copied.

Research used web opens, Python urllib source/API fetches, and `rg`/PowerShell source reads. No emulator install or test was attempted. The official host failures were added to the existing [download-host evidence](ryubing-official-download-host.md).

## Comparison with smashlab/emu.py

| Harness behavior | Source assessment |
|---|---|
| `test()`, lines 324-325: `-r <workspace data>` and `cwd=exe.parent` | Supported desktop launch grammar (see [arguments finding](ryubing-command-line-arguments.md)); selecting Custom mode does not relocate normal Windows logs to that data root. cwd is compatible, but log placement uses executable base directory rather than cwd. |
| `_log_files()`, lines 265-267: app recursively globbed for `Logs/*.log` | Supported for Windows primary `<exe>/Logs`, even when the executable is nested below app. Also finds `<exe>/portable/Logs`. Filename patterns both match `*.log`. |
| Same recursive glob below custom data | Conservative search, but not the documented normal Windows Custom-mode location. Portable `BaseDirPath/Logs` is covered if that root lies below either scanned tree. |
| Only app and custom data searched | Incomplete when Windows falls back to `%APPDATA%/Ryujinx/Logs`, which lies outside both trees. A file-open failure can instead produce no file at all. Expanding collection there would require care to avoid collecting or altering the user's unrelated logs. No harness change made here. |

## What to do instead / next

A later harness task should ensure the workspace executable's Logs directory is writable and make missing logs an explicit diagnostic; investigate a safe isolation strategy before considering the profile fallback. Recheck against official source and an official build when available. Keep this note `unverified` until a real isolated run demonstrates the actual destination, filename, and logging setting.
