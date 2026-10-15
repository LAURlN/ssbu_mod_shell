---
title: Ryubing mirror confirms desktop -r and positional game launch
summary: Pinned source documents desktop arguments and portable precedence; current official build remains undetermined
status: unverified
tags: [ryujinx, ryubing, emulator, command-line]
updated: 2026-10-01
source: T-0002; official https://docs.ryujinx.app/guides/setup-guide/; mirror https://github.com/Leuconoe/Ryubing/tree/793ca017ff4f6e48b798a62d2486405bfc42ef39
---

## What

**`-r` is confirmed in the inspected mirror and independently documented by official Ryubing docs.** The desktop parser accepts a game path as a positional argument; an existing `portable` folder beside the executable enables portable mode without arguments. Exact options in the current official desktop release remain **undetermined**, because the source host is unavailable; this note must remain `unverified` until runtime testing.

## Evidence

### Sources and limits (read 2026-10-01)

1. **Official source first:** https://git.ryujinx.app/ryubing/ryujinx returned web-fetch `Failed to fetch https://git.ryujinx.app/ryubing/ryujinx: (400) Timeout fetching`. Python `urllib.request.urlopen` with a 20-second timeout returned `URLError <urlopen error timed out>` for that URL and https://git.ryujinx.app/projects/Ryubing (the address linked by official docs). Current official revision and current release equivalence could not be determined.
2. **Official docs:** https://docs.ryujinx.app/ and https://docs.ryujinx.app/guides/setup-guide/ were reachable. Read the organisation https://github.com/Ryubing and its repos https://github.com/Ryubing/docs and https://github.com/Ryubing/Website. GitHub commits API pinned docs HEAD to `8bbea28d757e2582b3d954672b65b99bbbcf3199` (2026-04-15T04:31:51Z) and Website HEAD to `8286c57963b2cfabfd43ed78695c5af44ee10f35` (2026-07-25T00:38:03Z). Website is only provenance/context, not implementation evidence.
3. **Implementation fallback:** https://github.com/Leuconoe/Ryubing, **mirror, may be older than current Ryubing**, with downstream changes. All implementation links below pin commit `793ca017ff4f6e48b798a62d2486405bfc42ef39` (committer date 2026-08-05T02:20:44Z, metadata previously fetched in T-0004 and read again here). This establishes the inspected source behavior, not the behavior of the unavailable current official build. Source text and GitHub API metadata are cached only under `state/scratch/T-0003/`; no binaries were fetched.

### Desktop options

Every row cites the pinned mirror parser, [src/Ryujinx/Utilities/CommandLineState.cs, line 33](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L33). These are all explicit cases in its desktop switch; no `--help`/`--version` case exists there. Values follow their option as a separate argument. ?none? means no short form is declared, not an inferred alias.

| Short form | Long form | Meaning | Source |
|---|---|---|---|
| `-r` | `--root-data-dir <path>` | Select an existing custom data root. | [src/Ryujinx/Utilities/CommandLineState.cs, line 49](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L49) |
| `-rdct` | `--rd-capture-title-format <format>` | Override the RenderDoc capture title format. | [src/Ryujinx/Utilities/CommandLineState.cs, line 63](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L63) |
| `none` | `--install-firmware <path>` | Record a firmware archive path for installation. | [src/Ryujinx/Utilities/CommandLineState.cs, line 77](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L77) |
| `-p` | `--profile <name>` | Select a user profile by name; distinct from controller input profiles. | [src/Ryujinx/Utilities/CommandLineState.cs, line 90](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L90) |
| `-f` | `--fullscreen` | Start the launched game fullscreen. | [src/Ryujinx/Utilities/CommandLineState.cs, line 104](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L104) |
| `-g` | `--graphics-backend <value>` | Override graphics backend: opengl or vulkan. | [src/Ryujinx/Utilities/CommandLineState.cs, line 110](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L110) |
| `none` | `--backend-threading <value>` | Override backend threading: auto, off, on. | [src/Ryujinx/Utilities/CommandLineState.cs, line 121](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L121) |
| `none` | `--bt <value>` | Record backend threading for the reboot path (not a single-dash alias). | [src/Ryujinx/Utilities/CommandLineState.cs, line 131](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L131) |
| `none` | `--pptc <bool>` | Override profiled persistent translation cache enablement (true/false). | [src/Ryujinx/Utilities/CommandLineState.cs, line 141](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L141) |
| `-la` | `--local-only-amiibo` | Set the local-only Amiibo flag. | [src/Ryujinx/Utilities/CommandLineState.cs, line 151](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L151) |
| `-m` | `--memory-manager-mode <enum>` | Override memory manager mode with a case-insensitive enum name. | [src/Ryujinx/Utilities/CommandLineState.cs, line 155](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L155) |
| `none` | `--system-region <enum>` | Override system region with a case-insensitive enum name. | [src/Ryujinx/Utilities/CommandLineState.cs, line 166](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L166) |
| `none` | `--system-language <enum>` | Override system language with a case-insensitive enum name. | [src/Ryujinx/Utilities/CommandLineState.cs, line 176](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L176) |
| `-i` | `--application-id <id>` | Specify the application ID used when launching the input path. | [src/Ryujinx/Utilities/CommandLineState.cs, line 186](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L186) |
| `none` | `--docked-mode` | Force docked mode. | [src/Ryujinx/Utilities/CommandLineState.cs, line 190](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L190) |
| `none` | `--handheld-mode` | Force handheld mode. | [src/Ryujinx/Utilities/CommandLineState.cs, line 193](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L193) |
| `none` | `--hide-cursor <value>` | Set cursor hiding: never, onidle, always. | [src/Ryujinx/Utilities/CommandLineState.cs, line 196](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L196) |
| `none` | `--hide-updates` | Set the flag to hide available updates. | [src/Ryujinx/Utilities/CommandLineState.cs, line 206](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L206) |
| `none` | `--software-gui` | Disable GUI hardware acceleration. | [src/Ryujinx/Utilities/CommandLineState.cs, line 209](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L209) |

Additional entry-point options, consumed before the desktop/headless split: [src/Ryujinx/Program.cs, line 165](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Program.cs#L165).

| Short form | Long form | Meaning |
|---|---|---|
| none; bare alias `nogui` | `--no-gui` | Run the separate headless entry point and its parser. |
| none | `--core-dumps` | Permit core dumps instead of calling `OsUtils.SetCoreDumpable(false)`; source comments concern Linux. |

Backend/cursor/bool/enum conversion is in [src/Ryujinx/Program.cs, line 368](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Program.cs#L368) (lines 368-435). The profile-name lookup, including fallback to the last opened user if no name matches, is in [src/Ryujinx.HLE/HOS/Services/Account/Acc/AccountManager.cs, line 31](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.HLE/HOS/Services/Account/Acc/AccountManager.cs#L31). Parser recognition alone does not establish that every optional feature was exercised here.

### Game path and portable precedence

The desktop switch default assigns each unrecognized token to `LaunchPathArg`, so the last such token wins (including unknown option spellings). Use one positional game path; shell-quote a path with spaces. [src/Ryujinx/Utilities/CommandLineState.cs, line 212](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Utilities/CommandLineState.cs#L212) and [src/Ryujinx/Program.cs, line 291](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Program.cs#L291) show that the path, optional application ID, and fullscreen flag are passed to `MainWindow.DeferLoadApplication`. Thus the harness's argument list `Ryujinx.exe -r <data dir> <game path>` matches this desktop grammar.

[src/Ryujinx.Common/Configuration/AppDataManager.cs, line 49](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx.Common/Configuration/AppDataManager.cs#L49) (lines 49-108) establishes this precedence:

- Default: OS application-data directory plus `Ryujinx` (user-home fallback if the OS application-data path is empty).
- If `<executable base>/portable` exists, select it automatically. macOS also checks beside the `.app` bundle.
- A custom `-r` path overrides portable/default **if it already exists** and differs from the computed default user-profile path. A missing custom directory logs an error and retains the previous portable/default choice. Passing the default user-profile path explicitly does not displace an existing portable folder in this implementation.
- Relative custom paths are converted with `Path.GetFullPath`, so the process working directory matters to them.

Official docs corroborate folder-based mode and `-r`: [docs/guides/setup-guide.md, lines 715-748, docs commit 8bbea28d757e2582b3d954672b65b99bbbcf3199](https://github.com/Ryubing/docs/blob/8bbea28d757e2582b3d954672b65b99bbbcf3199/docs/guides/setup-guide.md#L715). Fullscreen and positional launch are illustrated at [lines 751-759 of the same file](https://github.com/Ryubing/docs/blob/8bbea28d757e2582b3d954672b65b99bbbcf3199/docs/guides/setup-guide.md#L751).

### Separate headless options (not desktop aliases)

`--no-gui`/`nogui` changes parser: [src/Ryujinx/Headless/HeadlessRyujinx.cs, line 85](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Headless/HeadlessRyujinx.cs#L85). These explicit `Option` attributes are all declared without short forms in [src/Ryujinx/Headless/Options.cs, line 197](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Headless/Options.cs#L197) (lines 197-440). The following summaries are transcribed from attribute help text; they describe the declared headless interface, not runtime tests. In particular headless `--root-data-dir` has **no declared `-r` alias**. Do not mix these with the desktop table.

| Short form | Long form | Meaning | Source line |
|---|---|---|---|
| none | `--use-main-config` | Use the settings from what was configured via the UI. | 197 |
| none | `--disable-main-input-config` | Do not use the input-related settings from what was configured via the UI. | 200 |
| none | `--root-data-dir` | Set the custom folder path for Ryujinx data. | 203 |
| none | `--profile` | Set the user profile to launch the game with. | 206 |
| none | `--display-id` | Set the display to use - especially helpful for fullscreen mode. [0-n] | 209 |
| none | `--fullscreen` | Launch the game in fullscreen mode. | 212 |
| none | `--exclusive-fullscreen` | Launch the game in exclusive fullscreen mode. | 215 |
| none | `--exclusive-fullscreen-width` | Set horizontal resolution for exclusive fullscreen mode. | 218 |
| none | `--exclusive-fullscreen-height` | Set vertical resolution for exclusive fullscreen mode. | 221 |
| none | `--input-profile-1` | Set the input profile in use for Player 1. | 226 |
| none | `--input-profile-2` | Set the input profile in use for Player 2. | 229 |
| none | `--input-profile-3` | Set the input profile in use for Player 3. | 232 |
| none | `--input-profile-4` | Set the input profile in use for Player 4. | 235 |
| none | `--input-profile-5` | Set the input profile in use for Player 5. | 238 |
| none | `--input-profile-6` | Set the input profile in use for Player 6. | 241 |
| none | `--input-profile-7` | Set the input profile in use for Player 7. | 244 |
| none | `--input-profile-8` | Set the input profile in use for Player 8. | 247 |
| none | `--input-profile-handheld` | Set the input profile in use for the Handheld Player. | 250 |
| none | `--input-id-1` | Set the input id in use for Player 1. | 253 |
| none | `--input-id-2` | Set the input id in use for Player 2. | 256 |
| none | `--input-id-3` | Set the input id in use for Player 3. | 259 |
| none | `--input-id-4` | Set the input id in use for Player 4. | 262 |
| none | `--input-id-5` | Set the input id in use for Player 5. | 265 |
| none | `--input-id-6` | Set the input id in use for Player 6. | 268 |
| none | `--input-id-7` | Set the input id in use for Player 7. | 271 |
| none | `--input-id-8` | Set the input id in use for Player 8. | 274 |
| none | `--input-id-handheld` | Set the input id in use for the Handheld Player. | 277 |
| none | `--enable-keyboard` | Enable or disable keyboard support (Independent from controllers binding). | 280 |
| none | `--enable-mouse` | Enable or disable mouse support. | 283 |
| none | `--hide-cursor` | Change when the cursor gets hidden. | 286 |
| none | `--list-input-profiles` | List input profiles. | 289 |
| none | `--list-input-ids` | List input IDs. | 292 |
| none | `--disable-ptc` | Disables profiled persistent translation cache. | 297 |
| none | `--enable-internet-connection` | Enables guest Internet connection. | 300 |
| none | `--disable-fs-integrity-checks` | Disables integrity checks on Game content files. | 303 |
| none | `--fs-global-access-log-mode` | Enables FS access log output to the console. | 306 |
| none | `--vsync-mode` | Sets the emulated VSync mode (Switch, Unbounded, or Custom). | 309 |
| none | `--custom-refresh-rate` | Sets the custom refresh rate target value (integer). | 312 |
| none | `--disable-shader-cache` | Disables Shader cache. | 315 |
| none | `--enable-texture-recompression` | Enables Texture recompression. | 318 |
| none | `--disable-docked-mode` | Disables Docked Mode. | 321 |
| none | `--system-language` | Change System Language. | 324 |
| none | `--system-region` | Change System Region. | 327 |
| none | `--system-timezone` | Change System TimeZone. | 330 |
| none | `--system-time-offset` | Change System Time Offset in seconds. | 333 |
| none | `--memory-manager-mode` | The selected memory manager mode. | 336 |
| none | `--audio-volume` | The audio level (0 to 1). | 339 |
| none | `--use-hypervisor` | Uses Hypervisor over JIT if available. | 342 |
| none | `--lan-interface-id` | GUID for the network interface used by LAN. | 345 |
| none | `--disable-file-logging` | Disables logging to a file on disk. | 350 |
| none | `--enable-debug-logs` | Enables printing debug log messages. | 353 |
| none | `--disable-stub-logs` | Disables printing stub log messages. | 356 |
| none | `--disable-info-logs` | Disables printing info log messages. | 359 |
| none | `--disable-warning-logs` | Disables printing warning log messages. | 362 |
| none | `--disable-error-logs` | Disables printing error log messages. | 365 |
| none | `--enable-trace-logs` | Enables printing trace log messages. | 368 |
| none | `--disable-guest-logs` | Disables printing guest log messages. | 371 |
| none | `--enable-fs-access-logs` | Enables printing FS access log messages. | 374 |
| none | `--enable-net-logs` | Enables printing net log messages. | 377 |
| none | `--graphics-debug-level` | Change Graphics API debug log level. | 380 |
| none | `--resolution-scale` | Resolution Scale. A floating point scale applied to applicable render targets. | 385 |
| none | `--max-anisotropy` | Max Anisotropy. Values range from 0 - 16. Set to -1 to let the game decide. | 388 |
| none | `--aspect-ratio` | Aspect Ratio applied to the renderer window. | 391 |
| none | `--backend-threading` | Whether or not backend threading is enabled. The "Auto" setting will determine whether threading should be enabled at runtime. | 394 |
| none | `--disable-macro-hle` | Disables high-level emulation of Macro code. Leaving this enabled improves performance but may cause graphical glitches in some games. | 397 |
| none | `--graphics-shaders-dump-path` | Dumps shaders in this local directory. (Developer only) | 400 |
| none | `--graphics-backend` | Change Graphics Backend to use. | 403 |
| none | `--preferred-gpu-vendor` | When using the Vulkan backend, prefer using the GPU from the specified vendor. | 406 |
| none | `--anti-aliasing` | Set the type of anti aliasing being used. [None/Fxaa/SmaaLow/SmaaMedium/SmaaHigh/SmaaUltra] | 409 |
| none | `--scaling-filter` | Set the scaling filter. [Bilinear/Nearest/Fsr/Area] | 412 |
| none | `--scaling-filter-level` | Set the scaling filter intensity (currently only applies to FSR). [0-100] | 415 |
| none | `--dram-size` | Set the RAM amount on the emulated system. | 420 |
| none | `--ignore-missing-services` | Enable ignoring missing services. | 423 |
| none | `--ignore-controller-applet` | Enable ignoring the controller applet when your game loses connection to your controller. | 426 |
| none | `--skip-user-profiles-manager` | Enable skips the Profiles Manager popup during gameplay. Select the desired profile before starting the game | 429 |
| none | `--enable-gdb-stub` | Enables the GDB stub so that a developer can attach a debugger to the emulated process. | 434 |
| none | `--gdb-stub-port` | Specifies which TCP port the GDB stub listens on. | 437 |
| none | `--suspend-on-start` | Suspend execution when starting an application. | 440 |

Headless positional input is required at index 0: [src/Ryujinx/Headless/Options.cs, line 445](https://github.com/Leuconoe/Ryubing/blob/793ca017ff4f6e48b798a62d2486405bfc42ef39/src/Ryujinx/Headless/Options.cs#L445). Library-generated help/version options were not traced; no desktop support for them is asserted.

## Comparison with smashlab/emu.py

| Harness behavior | Source assessment |
|---|---|
| `test()`, lines 324-325: executable, `-r`, data directory, positional game path | Supported by the mirror and official docs for desktop launch. The custom directory must exist; `setup()` creates it. Current official-release behavior remains untested. |
| `cwd = exe.parent` | Compatible; makes relative paths resolve from the executable folder. Portable discovery uses `AppDomain.CurrentDomain.BaseDirectory`, independently of cwd. The harness uses resolved workspace paths. |
| `_log_files()`, lines 265-267: recursive `Logs/*.log` below app and data | See [log finding](ryubing-log-file-location.md): covers primary Windows and portable paths but misses the Windows profile fallback with a custom root. |

## What to do instead / next

Recheck these symbols against official source when the host returns and validate with an official binary in a later task. This run did not install, boot, or run any emulator test and does not claim runtime verification. Harness and reference files were left unchanged.
