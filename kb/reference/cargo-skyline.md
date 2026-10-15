---
title: cargo-skyline build tool
summary: Installed cargo-skyline 3.5.0 and its subcommands for building Skyline plugins
status: verified
tags: [cargo-skyline, skyline, build, toolchain]
updated: 2026-10-03
source: T-0001
---

## Overview

cargo-skyline 3.5.0 is a Cargo subcommand for building and deploying Skyline plugins for the Nintendo Switch. It provides a simplified interface for building NRO plugins, managing dependencies, and deploying to a Switch console over FTP.

## Installed version

**cargo-skyline 3.5.0** is installed and functional on the lab machine.

## Subcommands

| subcommand | purpose |
|---|---|
| `build` | Build the current plugin as an NRO |
| `check` | Check if the current plugin builds and emit any errors found |
| `clean-project` | Clean a pre-existing project files no longer needed for the latest version |
| `clippy` | Emit beginner-helpful lints and warnings |
| `cp` | Copy a file over FTP |
| `doc` | Document the current plugin and its dependencies |
| `help` | Prints help message for the given subcommand |
| `install` | Build the current plugin and install to a switch over FTP |
| `list` | List the files in the plugin directory for the given game |
| `listen` | Listen for logs being output from a switch running skyline at the given ip |
| `new` | Create a new plugin from a template |
| `package` | Package plugin and latest Skyline into a zip file for release |
| `restart` | Install the current plugin and listen for skyline logging |
| `restart-game` | Restart the given game using restart-plugin |
| `rm` | Delete a file in the plugin directory for the given game |
| `run` | Install the current plugin and listen for skyline logging |
| `self-update` | Update cargo-skyline command |
| `set-ip` | Set the IP address of the switch to install to |
| `show-ip` | Show the currently configured IP address |
| `update` | Update libraries for current plugin folder |
| `update-std` | Download the latest stdlib for aarch64-skyline-switch |

## Verification

Verified 2026-10-01 by running:
- `cargo skyline --version` → `cargo-skyline 3.5.0`
- `cargo skyline --help` → showed the subcommands listed above

## Invoking a build from the agent shell (verified 2026-10-03)

* `cargo` and `cargo-skyline` are at `%USERPROFILE%\.cargo\bin` (resolved as
  `/c/Users/<user>/.cargo/bin` from Git Bash). `which cargo cargo-skyline rustc`
  finds all three.
* **`MSYS2_MINGW_BIN` is not set on this machine and no `dlltool` is present**
  (`/mingw64/bin/dlltool.exe` and `/usr/bin/dlltool.exe` both absent), so the
  `%MSYS2_MINGW_BIN%` prefix in `mods/ssbu_mod_new/tools/build_plugin.cmd` expands
  to nothing. A warm `target/` tree still builds fine — the `aarch64-skyline-switch`
  cdylib links with rust-lld and the host-side tools are already compiled.
* A **cold** target tree builds here for a crate that depends only on `skyline`
  (`6b52d32`): `cargo skyline build --release -- --offline` from an empty
  `CARGO_TARGET_DIR` exited 0 in about 41 s on 2026-10-04 (reported by the
  mii_customizer scaffold task, `mods/mii_customizer/research/P2-PLUGIN-SCAFFOLD.md`;
  the coordinator re-checked the resulting NRO hash, not the build itself, so treat
  as unverified by a second run). The compiler that produces the NRO is
  cargo-skyline's own toolchain, rustc 1.95.0-nightly (a423f68a0), not the rustc on
  PATH. A cold build of a crate with the larger smashline dependency set has not
  been exercised.
* Calling `cmd //c build.cmd` from Git Bash fails to find the file unless the path
  is written `.\build.cmd`; Git Bash's path mangling turns the bare name into
  something cmd cannot resolve, and the stderr is misleading
  (`Der Befehl "mods" ist entweder falsch geschrieben`).
* Because of that, the pikachu-airb task builds **directly from Git Bash** with
  `cargo skyline build --release --features ... -- --offline > log 2>&1` and reads
  `$?` — bash reports cargo's real exit code, and the build log is kept next to the
  isolated tree (`builds/.cache/pikachu-airb/build*.log`). The batch file in that
  directory is kept as documentation of the intended command, not as the runner.
