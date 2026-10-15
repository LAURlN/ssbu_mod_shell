# Toolchain

Tiers: **A** hardware-confirmed (console or decoded crash report) - **B** measured offline by a script that still exists - **C** read from pinned third-party source - **D** hypothesis. Anything without a tier below is A/B unless marked otherwise. Paths in the source column refer to the *old* workspace (`modpack_test_1`); the same material now lives under `projects/*/history/`, `dumps/` and `evidence/`.

- Windows: MSYS2 (`mingw-w64-x86_64-binutils gcc`) first on PATH; `cargo +stable-x86_64-pc-windows-gnu install cargo-skyline` (3.5.0 matches skyline-rs `6b52d32`, judge by commit date not version); MSVC fails (GNU `link.exe` first on PATH); bundled rustup dlltool cannot build import libs. Run builds from `cmd` (`build_plugin.cmd`): PowerShell reports exit 255 while cargo says Finished and NRO packaging happens after that line. (A)
- `build.py` needs the **cp312** interpreter (`scratch/py312`), system Python 3.8 cannot import vendored `ssbh_data_py`. `cargo skyline build … --offline` fails until `cargo fetch` was run once online.
- **After every deploy compare the packaged NRO hash with the built NRO hash** (a deploy printed the previous build's hash). (A)
- `Cargo.toml` uses git deps pinned by `rev`; `[patch]` with the same git URL is rejected by cargo. (A, measured 2026-09-17; contradicts guide §1, see R-6)
- `install-to-card.sh`: finds card by contents, backs up, stages `.new`, verifies, rolls back. Installing is the agent's job, running the game is the user's.
