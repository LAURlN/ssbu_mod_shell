---
title: The user's mod workspace mods/ssbu_mod_new - map for lab agents
summary: Verified local paths and machine prerequisites for the cloned mod repo, including missing analysis inputs and unresolved user decisions.
status: verified
tags: [mod-workspace, pgwr, paths, toolchain, setup]
updated: 2026-10-01
source: T-0012
---

## Overview

The ignored paths.toml resolves the matching 13.0.4 main, an external G&W NRO and the tracked ParamLabels.csv.
Python 3.12.3 and the manifest's Skyline Rust/cargo-skyline versions are available; a build has not been attempted.
main.bin, dumped scripts, repo toolchains/caches, mingw on this session's PATH and Ghidra are missing; some tools bypass paths.toml.

This is the user's mature mod source, evidence and reference workspace, cloned on 2026-10-01 at HEAD `8362332cf0c87120d3b674942c480a633ff8a09b`. Its [AGENTS.md](../../mods/ssbu_mod_new/AGENTS.md) governs everything inside it; stricter rules apply alongside the lab rules. Knowledge about the game and mod lives in that repo and is linked here, never copied. This note records machine integration only. T-0021 changed no tracked mod files and ran no build or emulator test because it changed no game behaviour.

Checks were run on 2026-10-01. Raw evidence and one-off standard-library scripts are in `state/scratch/T-0012/` relative to the lab root: `tool-versions.txt`, `machine-audit.json`, `check_paths-output.txt`, `import-lines-tools.txt`, `import-lines-pgwr.txt`, `arc-path-lines.txt`, and `questions.md`. The verified frontmatter applies to observed local facts; recorded old-workspace contents and explicitly unverified requirements are distinguished below. [local-machine.md](local-machine.md) still contains a pre-clone missing-repo statement; the final T-0012 subtask owns its update.

## Where the rules and the knowledge are

| file | purpose |
|---|---|
| [AGENTS.md](../../mods/ssbu_mod_new/AGENTS.md) | Rules governing every read and change inside the repo. |
| [handbook/00_INDEX.md](../../mods/ssbu_mod_new/handbook/00_INDEX.md) | Task-to-handbook map. |
| [handbook/graveyard.md](../../mods/ssbu_mod_new/handbook/graveyard.md) | Retracted claims and failed approaches. |
| [projects/pgwr/STATUS.md](../../mods/ssbu_mod_new/projects/pgwr/STATUS.md) | Current project state and next checks. |
| [CURRENT_INSTALL.md](../../mods/ssbu_mod_new/CURRENT_INSTALL.md) | Collective installer readiness and installation record. |
| [dumps/INDEX.md](../../mods/ssbu_mod_new/dumps/INDEX.md) | Recorded data layout and provenance. |
| [dumps/MISSING.md](../../mods/ssbu_mod_new/dumps/MISSING.md) | Missing-input requests and their resolutions. |
| [tools/README.md](../../mods/ssbu_mod_new/tools/README.md) | Mod analysis and packaging tools and invocation guidance. |
| [refs/INDEX.md](../../mods/ssbu_mod_new/refs/INDEX.md) | Pinned reference material index. |
| [evidence/INDEX.md](../../mods/ssbu_mod_new/evidence/INDEX.md) | Test and audit evidence index. |
| [builds/pgwr/0.20.16/MANIFEST.json](../../mods/ssbu_mod_new/builds/pgwr/0.20.16/MANIFEST.json) | Staged release identity, hashes and recorded toolchain. |

## paths.toml on this machine

| key | value | consumed by | state |
|---|---|---|---|
| `workspace.root` | `"."` | Local configuration/example metadata; use must be checked per tool | example retained; no runtime consumer asserted |
| `workspace.old_root` | `""` | Local configuration/example metadata; use must be checked per tool | intentionally empty; console/card and optional conversion remain unconfigured |
| `dumps.arc` | `"<ArcExplorer dir>/export"` | tools/audit_hero_neutral_b.py and other TOML-aware asset audits | G&W NRO exists; full export comparison deferred to later subtask |
| `dumps.exefs` | `"dump/nxdt_rw_poc/NCA FS/User/Extracted/Super Smash Bros. Ultimate 13.0.4 [01006A800016E800][v1966080][UPD]/Program #0/0"` | tools/main_image.py and TOML-aware native audits | main exists and matches; main.bin absent |
| `dumps.scripts` | `"dumps/scripts/SSBU-Dumped-Scripts-main"` | tools/audit_hero_neutral_b.py (including ParamLabels split expression) | tree absent; sibling ParamLabels.csv resolves |
| `toolchain.python312` | `"python"` | Local configuration/example metadata; use must be checked per tool | python resolves to 3.12.3; hard-coded interpreter consumers remain unsatisfied |
| `toolchain.msys2_mingw` | `""` | src/pgwr/build-plugin.sh prepends this folder to PATH | empty: where.exe found no mingw bin folder; no WinLibs substitution made |
| `toolchain.cargo_skyline` | `"3.5.0"` | Local configuration/example metadata; use must be checked per tool | installed 3.5.0 |
| `toolchain.ghidra` | `"11.1.2"` | Local configuration/example metadata; use must be checked per tool | expected version only; install not found |
| `toolchain.ghidra_home` | `""` | tools/nro_decomp/run_ghidra.sh documentation; implementation reads GHIDRA_HOME environment | empty: no install found by permitted checks |
| `toolchain.arc_network_dll` | `""` | Local configuration/example metadata; use must be checked per tool | intentionally empty; console/card and optional conversion remain unconfigured |
| `toolchain.effect_converter` | `""` | Local configuration/example metadata; use must be checked per tool | intentionally empty; console/card and optional conversion remain unconfigured |
| `toolchain.roslyn_csc` | `""` | Local configuration/example metadata; use must be checked per tool | intentionally empty; console/card and optional conversion remain unconfigured |
| `toolchain.dotnet_runtime` | `""` | Local configuration/example metadata; use must be checked per tool | intentionally empty; console/card and optional conversion remain unconfigured |
| `toolchain.hero_effect_converter` | `"builds/.cache/hero_effect_converter/bin/EffectConverter.exe"` | Hero effect conversion tools | example retained; executable absent |
| `switch.sd_drive` | `""` | Local configuration/example metadata; use must be checked per tool | intentionally empty; console/card and optional conversion remain unconfigured |
| `switch.arc_network_ip` | `""` | Local configuration/example metadata; use must be checked per tool | intentionally empty; console/card and optional conversion remain unconfigured |
| `switch.game_version` | `"13.0.4"` | Local configuration/example metadata; use must be checked per tool | example retained; no runtime consumer asserted |
| `card_do_not_touch.plugins` | `["libarcropolis.nro", "libarc_network.nro", "libnro_hook.nro", "libsmashline_plugin.nro"]` | Local configuration/example metadata; use must be checked per tool | example retained; no runtime consumer asserted |
| `card_do_not_touch.smashline_good_sha256` | `"5f4091eed89c5854c2bfccb9f25b6e8da8c03ebedcaa5ab36eadebfc078bc8f7"` | Local configuration/example metadata; use must be checked per tool | example retained; no runtime consumer asserted |

Absolute Windows paths use forward slashes and quoted TOML strings. Repo rule 4 reserves paths.toml for absolute paths. `Path('mods/ssbu_mod_new') / value` selects an absolute value directly. `python state/scratch/T-0012/check_paths.py` verifies identical sections/keys to the example and the existence checks: main=True, main.bin=False, external G&W NRO=True, ParamLabels=True, scripts tree=False, mingw folder-or-empty=True. `git -C mods/ssbu_mod_new check-ignore -v paths.toml` reports `.gitignore:2:/paths.toml`; the unadorned check-ignore prints `paths.toml`.

## What the repo expects and what this machine has

| expected by the repo (which file says so) | found on this machine (command and key output) | satisfied |
|---|---|---|
| In-repo dumps/arc (dumps/INDEX.md) | `python -B state/scratch/T-0012/audit_machine.py`: directory absent. paths.toml points to <ArcExplorer dir>/export; `check_paths.py` finds prebuilt/nro/release/lua2cpp_gamewatch.nro there. Later subtask compares exports. | partly |
| ExeFS main (dumps/INDEX.md, dumps/decoded/main_inventory.json) | `audit_machine.py` hashes all five files read-only: main is 42,910,639 bytes, sha256 77936fe2031e4f38316120576177090857611025e140b415d3850bac8eabd92e; size and hash match repo. | yes |
| main.bin at configured ExeFS (tools/main_image.py, dumps/INDEX.md) | `check_paths.py`: exefs/main.bin=False; in-repo dumps/exefs/13.0.4 also absent. Recorded expected flat image: 86,672,752 bytes, sha256 f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613. Not created; destination question recorded. | no |
| Dumped scripts tree, recorded 77,532 files (dumps/INDEX.md); smashline-hdr subfolder (tools references) | `Get-ChildItem mods/ssbu_mod_new/dumps/scripts -Name`: ParamLabels.csv, gamewatch_motion_list.yml only. `audit_machine.py`: both requested tree and smashline-hdr absent. No download; user question recorded. | no |
| toolchains/py312/python.exe and toolchains/python_tools (tools/README.md, tools/nro_decomp/run_ghidra.sh, tools/main_image.py, tools/nro_decomp/nro_util.py) | `audit_machine.py`: toolchains and python_tools absent. `python --version`: Python 3.12.3 available via paths.toml, but run_ghidra.sh hard-codes the missing interpreter. inspect_main.py actually inserts ROOT/python_tools (also absent because no repo-root folder exists), despite INDEX's toolchains/python_tools wording. | partly |
| Third-party Python imports (tools/*.py, tools/nro_decomp/*.py, src/pgwr/build.py, src/pgwr/tools/*.py) | `rg -n '^\s*(from|import) ' ... -g '*.py'` saved import lines; `audit_machine.py` parsed every file with AST, excluded stdlib/repo files, found no syntax errors, and ran `python -B -c 'import NAME; ...'` for every external module. Outcomes detailed below. | partly |
| Rust and cargo-skyline (handbook/02_toolchain.md, staged MANIFEST.json) | `rustup toolchain list`: stable GNU and MSVC, nightly-2026-02-14 GNU and MSVC, skyline-v3. `cargo skyline --version`: 3.5.0. `rustc +skyline-v3 -vV`: 1.95.0-nightly (a423f68a0 2026-02-13), host x86_64-pc-windows-gnu; rustc line equals manifest. Required stable GNU exists. Build viability untested. | yes |
| MSYS2/mingw-w64 GCC and binutils first on PATH (handbook/02_toolchain.md, src/pgwr/build-plugin.sh) | `Test-Path C:/msys64`: False. `where.exe gcc`, `dlltool`, `as`, `c++filt`: all exit 1, no matches (German output in tool-versions.txt). Planner reported llvm-mingw/WinLibs, but neither resolves in this run's PATH; no bin folder identified by the prescribed commands, so key remains empty. | no |
| Ghidra 11.1.2 and Java (paths.example.toml, tools/nro_decomp/run_ghidra.sh) | GHIDRA_HOME empty; `where.exe analyzeHeadless`: no match. `Get-ChildItem -LiteralPath <root> -Name` filtered for ghidra at C:/, <drive>:/, C:/Program Files: no names; no deeper search. `java -version`: 1.8.0_461. Ghidra 11 needing JDK 17 or newer is unverified recall; no local Ghidra README found or read. | no |
| Optional effect converter .NET support (paths.example.toml, converter keys) | `dotnet --list-sdks`: 2.1.818, 5.0.408, 8.0.201. `dotnet --list-runtimes`: NETCore 2.1.30/5.0.17/6.0.27/8.0.2, AspNetCore All 2.1.30 and App 2.1.30/5.0.17/8.0.2, WindowsDesktop 5.0.17/6.0.27/8.0.2. Empty converter keys retained; no converter configured or tested. | partly |
| builds/.cache and hero_effect_converter; evidence/sd-backups (paths.example.toml, AGENTS.md, STATUS.md) | `audit_machine.py`: both folders absent; builds/.cache/hero_effect_converter/bin/EffectConverter.exe absent. No caches or backups created. | no |
| Console and SD card installation workflow (repo AGENTS.md rule 23; lab rules) | User task establishes no console/card in lab; no card probing or access performed. Lab agents never install to the card. Empty switch keys preserved. | no |
| Old modpack_test_1 inputs (dumps/decoded/main_inventory.json source; dumps/INDEX.md) | Read only the repo records: %USERPROFILE%/OneDrive/Dokumente/ChatGPT/modpack_test_1 is the recorded old workspace, described as holding ARC export, main.bin, scripts, py312 and scratch/ghidra. Outside permitted lab scope: not opened, listed or tested. Question asks whether it exists and read-only referencing is allowed. | no (not verified) |

External Python module checks (full source-file/line inventory and exact subprocess output in machine-audit.json):

| module | command | observed result |
|---|---|---|
| `PIL` | `python -B -c "import PIL"` plus importlib.metadata version lookup | 11.0.0; ['pillow']; pillow 11.0.0; exit 0 |
| `capstone` | `python -B -c "import capstone"` plus importlib.metadata version lookup | ModuleNotFoundError: No module named 'capstone'; exit 1 |
| `lz4` | `python -B -c "import lz4"` plus importlib.metadata version lookup | ModuleNotFoundError: No module named 'lz4'; exit 1 |
| `numpy` | `python -B -c "import numpy"` plus importlib.metadata version lookup | 2.2.2; ['numpy']; numpy 2.2.2; exit 0 |
| `pyprc` | `python -B -c "import pyprc"` plus importlib.metadata version lookup | None; ['pyprc']; pyprc 1.0.0; exit 0 |
| `ssbh_data_py` | `python -B -c "import ssbh_data_py"` plus importlib.metadata version lookup | None; ['ssbh_data_py']; ssbh_data_py 0.9.1; exit 0 |

ExeFS identity, measured by `hashlib.file_digest` in `audit_machine.py` (read-only binary streams):

| file | bytes | sha256 |
|---|---|---|
| `main` | 42910639 | `77936fe2031e4f38316120576177090857611025e140b415d3850bac8eabd92e` |
| `main.npdm` | 1508 | `a3bdf0862fd4dea1f16c7522107f88a97cf4de03ce9dbd745adc4976564639b6` |
| `rtld` | 7435 | `bc52eeaae18053433a64caeeed0c12b63fd29fbde635346d732203ec41f585f0` |
| `sdk` | 5374456 | `8d20111b4f1dd9a301901ed9c2a0f31ce5678076f7b233bfb8bdbafe52f955f1` |
| `subsdk0` | 3535964 | `2ac9587ec0d20a2bda42d7a8f04574f18af3e047d9864a599070d57666b1811e` |

Hard-coded in-repo ARC path consumers are not satisfied by paths.toml. The task's grep search was performed with the equivalent `rg -n "dumps/arc|'dumps' / 'arc'" mods/ssbu_mod_new/tools mods/ssbu_mod_new/src/pgwr -g '*.py' -g '*.sh'`; raw matching lines are in arc-path-lines.txt. Inspection distinguishes executable path assignments from documentation/comments. Consumers (relative to mod root):

- `src/pgwr/build.py`
- `src/pgwr/tools/article_table.py`
- `src/pgwr/tools/build_chrom_jab.py`
- `src/pgwr/tools/build_cloud_fair.py`
- `src/pgwr/tools/build_cloud_trail.py`
- `src/pgwr/tools/build_custom_names.py`
- `src/pgwr/tools/build_esword_pose.py`
- `src/pgwr/tools/build_hero_spin.py`
- `src/pgwr/tools/build_littlemac_fsmash.py`
- `src/pgwr/tools/build_monkey_flip.py`
- `src/pgwr/tools/build_mythra_moves.py`
- `src/pgwr/tools/build_robot_dtilt.py`
- `src/pgwr/tools/extract_gw_params.py`
- `src/pgwr/tools/fair_sword_geometry.py`
- `src/pgwr/tools/gen_common.py`
- `src/pgwr/tools/prereq_motion.py`
- `src/pgwr/tools/sound_names.py`
- `src/pgwr/tools/untracked_meshes.py`
- `src/pgwr/tools/verify_breath_bridge.py`
- `src/pgwr/tools/verify_color_themes.py`
- `tools/audit_littlemac_fsmash.py`
- `tools/build_littlemac_fsmash_effect.py`
- `tools/constmap.py`
- `tools/dump_param_special_s.py`
- `tools/inject_monkey_flip.py`
- `tools/merge_donor_sound.py`
- `tools/nro_decomp/nro_util.py`
- `tools/nro_decomp/smoke_test.py`

Some of these allow MGW_EXPORT or an argument override; paths.toml alone does not supply it. tools/fetch_arc_files.py and tools/gen_snake_neutral_b.py matched documentation/comments rather than an executable hard-coded ARC input in this search. No consumer was edited or run. No build readiness is claimed.
