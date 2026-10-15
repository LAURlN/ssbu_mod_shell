---
title: Emulator test environment (Ryujinx)
summary: How the lab's portable Ryujinx is laid out, where binaries may come from, what a test run produces, and which parts are still untested
status: seed
tags: [ryujinx, testing, emulator, skyline, arcropolis]
updated: 2026-10-01
source: lab setup 2026-10-01
---

## Overview

`python -m smashlab emu ...` manages a Ryujinx install that lives entirely inside the workspace, so
tests never touch the user's own emulator. The harness code is `smashlab/emu.py`; settings are in
`config/lab.toml` under `[emu]`.

**State on 2026-10-01: the harness is written but has never completed a real run**, because the
emulator download host was down and the game dump was not available yet. Everything below about
Ryujinx behaviour (arguments, log location, mod folders) is from general knowledge and must be
confirmed by the first agent that gets a run through. Update this note when you do.

## Layout

| path | content |
|---|---|
| `testenv/ryujinx/app/` | The emulator build (`lab emu install`) |
| `testenv/ryujinx/data/` | Portable data dir, passed to Ryujinx with `-r` |
| `testenv/ryujinx/data/system/` | `prod.keys`, `title.keys` (imported from the user's old install by `lab emu setup`) |
| `testenv/ryujinx/data/bis/system/Contents/registered/` | Firmware (imported the same way) |
| `testenv/ryujinx/data/sdcard/` | The emulated SD card: `atmosphere/contents/<title id>/...`, `ultimate/mods/...` |
| `testenv/scenarios/*.toml` | Test scenarios |
| `testenv/runs/<id>/` | Output of each test run |

## Where binaries may come from

- **Ryujinx**: only the official Ryubing project. Download endpoint:
  `https://update.ryujinx.app/download/query?os=win&arch=x64&rc=stable` (this is what the buttons on
  `https://ryujinx.app/download` call). Source and releases: `https://git.ryujinx.app`. Search
  engines list many look-alike "Ryujinx download" sites; they are not the project and must not be
  used. See [finding](../findings/ryubing-official-download-host.md).
- **Skyline, ARCropolis, Smashline**: latest GitHub releases of the repos listed in
  `[[emu.sd_packages]]`, fetched by `lab emu install-sd`.
- **Keys, firmware, game**: only from the user. Never download these.

## Commands

```
lab emu status        # checklist: emulator, keys, firmware, game dump, skyline, arcropolis, mods
lab emu install       # download + unpack Ryujinx
lab emu setup         # create data dir, import keys/firmware, patch Config.json for unattended runs
lab emu install-sd    # Skyline + ARCropolis + Smashline onto the emulated SD card
lab emu deploy <dir>  # copy a mod folder to sdcard/ultimate/mods/<name>; a .nro goes to the plugins folder
lab emu undeploy <name>
lab emu test [scenario] [--seconds N]
```

## What a test run does

1. Starts `Ryujinx.exe -r <data dir> <game path>`.
2. Plays the scenario: at given times it takes a screenshot of the emulator window or presses a key.
3. Kills the emulator after the scenario's `seconds`.
4. Copies the new emulator log, applies the rules in `[emu.log_rules]` and the scenario's
   `expect_log` / `forbid_log` patterns, and writes `report.json` with `verdict` and `reasons`.
5. If a Jev key is configured, Jev reads the log excerpt and can turn a "pass" into a "fail" when
   it is confident the log shows a crash or setup error.

Screenshots are plain PNG files; agents with vision can open them to see what was on screen.

## Limits

- The window must be visible; a run grabs keyboard focus. One run at a time.
- A passing boot test means "did not crash within N seconds", nothing more.
- Key presses reach the game only if Ryujinx has a keyboard input profile for player 1. Check
  `Config.json` (`input_config`) after the first manual start and record the mapping here.
- Gameplay feel, visuals in motion, online, and real hardware need the user.

## Unverified assumptions to check on the first real run

- `-r` / `--root-data-dir` is still the argument for a custom data directory.
- Log files appear under a `Logs/` folder in the app dir or data dir.
- Ryujinx loads `sdcard/atmosphere/contents/<title id>/exefs` (Skyline) from the emulated SD card.
  The alternative location is `data/mods/contents/<title id>/<mod name>/exefs`.
- The `updates.json` format written by `lab emu setup` for the game update.
- Skyline plugin log output is visible in the Ryujinx log when guest logging is enabled.
- Firmware from the user's 2024 install is new enough for the game version in the dump.
