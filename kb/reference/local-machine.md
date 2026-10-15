---
title: This machine - installed toolchains, existing tools, and where the user's files are
summary: Versions of the build tools on the lab machine, tools that already exist outside the workspace, and the state of the dump and the user's mod repo
status: verified
tags: [environment, toolchain, setup]
updated: 2026-10-03
source: lab setup 2026-10-01 (commands run on the machine)
---

## Overview

Windows 11, workspace at `<workspace>`. Shells: PowerShell 5.1 and Git Bash. Checked on
2026-10-01 by running each tool's version command.

## Toolchains

| tool | version | note |
|---|---|---|
| Rust | cargo/rustc 1.98.1, default toolchain `stable-x86_64-pc-windows-msvc` | also `nightly-2026-02-14` and a `skyline-v3` toolchain |
| cargo-skyline | 3.5.0 | already installed; the `skyline-v3` toolchain suggests its std has been set up before. Not yet used to build anything in this lab. |
| Python | 3.12.3, uv 0.12.15 | the orchestrator needs only the standard library |
| Node | 24.19.0 | runs the agent CLIs |
| .NET SDK | 8.0.201 | |
| git | installed; `gh` is not | |

## Agent CLIs

| CLI | version | login state |
|---|---|---|
| claude | 2.1.286 | (removed for publication) |
| codex | 0.159.3 | (removed for publication) |
| gemini | 0.62.0 | (removed for publication) |
| freebuff | 0.2.11 | interactive only, see [finding](../findings/freebuff-has-no-headless-mode.md) |

## Existing tools outside the workspace

- ArcExplorer: `<ArcExplorer dir>\ArcExplorer.exe` (GUI for browsing/extracting `data.arc`;
  has an `export` folder next to it that may hold earlier extractions - not inspected).
- An old Ryujinx data folder at `%APPDATA%\Ryujinx` (config version 51, last used 2024) holding
  `prod.keys`, `title.keys` and 232 firmware entries. `lab emu setup` imports keys and firmware
  from there. No Ryujinx executable was found on the machine.

## Game dump (provided 2026-10-01)

Made with nxdumptool, under `dump/nxdt_rw_poc/`. **Game version 13.0.4** (update `v1966080`).

| path under `dump/nxdt_rw_poc/` | content |
|---|---|
| `NSP/Super Smash Bros. Ultimate [01006A800016E000][v0][BASE].nsp/` | Base game as a FAT32-split NSP: a *folder* with parts `00`-`03` (13.63 GB total). Ryujinx cannot open this; `lab emu setup` joins it into `testenv/ryujinx/roms/`. |
| `NSP/Super Smash Bros. Ultimate 13.0.4 [01006A800016E800][v1966080][UPD].nsp` | Update 13.0.4 (3.66 GB) |
| `NSP/Super Smash Bros. Ultimate [01006A800016F001][v65536][DLC].nsp` | One DLC entry (121 KB, so it is an unlock/ticket-sized package, not content) |
| `NCA FS/User/Extracted/...13.0.4...[UPD]/Program #0/0/` | Extracted ExeFS of 13.0.4: `main` (40.9 MB), `main.npdm`, `rtld`, `sdk`, `subsdk0`. This is the executable to analyse for offsets and hooks. |

Not in the dump: an extracted `data.arc` / romfs. File-mod work that needs vanilla files has to
extract them first (ArcExplorer, or a tool built for the lab); that is an open task.

## User-provided inputs still missing

- **`mods/ssbu_mod_new`**: the GitHub repo had no commits on 2026-10-01, see `mods/README.md`.
- **Ryujinx**: not installed yet, see [finding](../findings/ryubing-official-download-host.md).

## Update 2026-10-02: no MSVC linker (verified)

The default Rust toolchain is `stable-x86_64-pc-windows-msvc`, but no `link.exe` is installed, so
host programs cannot be linked with it (`linker link.exe not found`; in Git Bash the symptom is
`link: extra operand`). Host tools must pin `stable-x86_64-pc-windows-gnu`, which links on its
own, with a `rust-toolchain.toml` as `tools/arc-extract` does. Skyline plugin builds are not
affected (they use the `skyline-v3` toolchain).

## Update 2026-10-02: gaogaen_throw_b task-local analysis dependency (verified)

Capstone **5.0.7** was installed with pip `--target` only under
`mods/ssbu_mod_new/builds/.cache/gaogaen_throw_b/python`; no system Python package
was changed. The task's native audit imported it successfully. Its isolated Cargo
home and target are likewise under that task's `builds/.cache` directory, seeded from
the installed Cargo dependency cache and used with `--offline`. The offline Skyline
compile passed with tool execution permission after the sandbox denied `dlltool.exe`.
Mod findings/build evidence are linked rather than copied here:
`mods/ssbu_mod_new/evidence/2026-10-02_pgwr_gaogaen_throw_b/RESULT.md`.

Verified 2026-10-02 again for the collective 0.20.20 build: the sandbox returned `error calling dlltool 'dlltool.exe': Zugriff verweigert (os error 5)`; the same offline build passed with tool execution permission. Task-specific Cargo home and target stayed under the mod's `builds/.cache/pgwr-collective-02020-{home,target}`; no system dependency was installed. Install/build evidence: `mods/ssbu_mod_new/evidence/2026-10-02_pgwr_0.20.20/INSTALL.md`.

## 2026-10-03: SD folder rename failure and verified retry

Verified: ready-assets.1 installation returned `mv: cannot move ... Permission denied` at the final staged-directory rename. The canonical installer automatically rolled back; independent comparison confirmed every baseline mod file and plugin hash restored. The identical package then installed and passed its full card rehash when all card reads were sequential. A concurrent read-only staging-directory traversal was in flight during the first failure; directory-handle contention is an unverified hypothesis, not an established cause. Avoid overlapping progress traversals with the installer folder swap. Evidence and exact failure output: `mods/ssbu_mod_new/evidence/2026-10-03_pgwr_ready_assets_1/INSTALL.md` and `installer-first-attempt.txt` in that folder. No dependency or system-software installation was involved.
