# MANIFEST

What this folder contains, what was left out and why, and every change made to copied files. The copy was produced by [`tools/showcase-export/export.py`](tools/showcase-export/export.py) on 2026-10-15; its machine-readable report is [`tools/showcase-export/export-report.json`](tools/showcase-export/export-report.json).

## Included

Same relative layout as the original workspace, so paths inside the documents resolve.

| area | what |
|---|---|
| workspace root | `AGENTS.md` (+ `CLAUDE.md` / `GEMINI.md` pointers), `kb/` (index, playbooks, findings, reference, journal, templates), `tools/` (README, REGISTRY, `arc-extract` and `data-arc-extract` source, `freebuff-dispatch`), `evidence/freebuff-dispatch/` (prompts and run records of the dispatch experiment) |
| `mods/ssbu_mod_new/` | `AGENTS.md`, `README.md`, `CURRENT_INSTALL.md`, `.gitignore`, `paths.example.toml`, `handbook/` (all pages, `graveyard.md`, `facts/facts.yaml`), `projects/` (every `STATUS.md`, plans, changelogs, history), `evidence/` (every `RESULT.md` / `INSTALL.md` / `REVIEW.md`, install records, audit and verification JSON), `tools/` (all audit, build and check scripts), `kb/findings/`, `dumps/INDEX.md` + `MISSING.md`, `refs/*` provenance only (`SOURCE.json`, `*manifest.json`, notes), `src/` (plugin and pipeline source except the game-derived files below; build scripts, manifests, validation records) |
| `mods/mii_customizer/` | `AGENTS.md`, `README.md`, `STATUS.md`, `HANDOFF.md`, `CHANGELOG.md`, `CURRENT_INSTALL.md`, `build-plugin.sh`, `phases/`, `prompts/` (all), `research/` (all reports incl. per-move reports), `evidence/` (check scripts, `RESULT*.md`, check outputs), `plugin/` (`Cargo.toml`, `Cargo.lock`, README, own source modules), `moves/*/` (`unit.json`, asset build and retarget scripts), `tools/` (own tools), `scratch/` (only check scripts and host tests that copied documents reference by path; see `NEEDS_DECISION.md`) |
| new files | `README.md`, `MANIFEST.md`, `NEEDS_DECISION.md`, `dump/README.md`, `gamedata/README.md`, `tools/showcase-export/` (scripts, README, report), one row added to `tools/REGISTRY.md` |

## Left out, by category

| category | entries |
|---|---:|
| raw log / disassembly / card listing (evidence text) | 799 |
| game-format or binary file (model, texture, animation, sound, effect, param, NRO, executable, compiled Lua) | 748 |
| game disassembly | 694 |
| pinned donor material / decoded game data (refs) | 636 |
| decoded game table | 33 |
| large measured output (regenerate with its check script) | 26 |
| log | 25 |
| decoded game data output (regenerate with its check script) | 21 |
| cache | 20 |
| move unit: ACMD / status code ported from the donor fighter | 17 |
| ported ACMD | 16 |
| generated from game params | 12 |
| game Lua script | 9 |
| generated ACMD | 8 |
| third-party source copy | 6 |
| ported decompiled game status code | 4 |
| game instruction signatures | 4 |
| relocated game machine code | 4 |
| build cache | 3 |
| vendored third-party code | 3 |
| vendored Python packages | 3 |
| translated from game NRO code | 3 |
| agent transcript / log | 2 |
| build outputs (NRO, packages) | 2 |
| git metadata | 2 |
| image (game renders / previews) | 2 |
| generated from game data | 2 |
| translated from game native code | 2 |
| generated from third-party bindings | 2 |
| ACMD ported from game scripts (heuristic) | 2 |
| scratch (only files referenced by exact path are copied) | 2 |
| describes the user's Google account tier (login details) | 1 |
| stray copy written to the wrong place by a worker (canonical copy is in mods/mii_customizer) | 1 |
| game files extracted from the dump | 1 |
| compiled Lua output | 1 |
| own dispatcher mixed with ported Mii Brawler ACMD | 1 |
| built binaries | 1 |
| downloaded third-party archives | 1 |
| third-party Lua 5.3.6 source | 1 |
| agent tool state | 1 |
| old snapshots incl. game files | 1 |
| third-party / donor material | 1 |
| runtime state | 1 |
| machine-local config | 1 |
| scratch listing | 1 |
| decompiled / decoded game data | 1 |
| dumped game scripts | 1 |
| build archives | 1 |
| old copy of plugin source incl. ported game code | 1 |
| SD card backups | 1 |
| image | 1 |
| vendored third-party code (Smashline fork) | 1 |
| vendored Python packages + DLLs | 1 |
| game models/textures/effects | 1 |
| renders of game models | 1 |
| machine-local marker | 1 |
| code generated from game scripts | 1 |
| ported decompiled game code | 1 |
| generated translation of game code | 1 |
| third-party README (code not included) | 1 |
| third-party license (code not included) | 1 |
| game ACMD text and .prc params | 1 |
| ACMD ported from game scripts | 1 |

Entries count files, except whole folders (`target/`, `builds/`, vendored crates, `assets/`, the `scratch/` roots), which count once. Per-folder detail: `excluded_by_folder` in the report.

Never walked (outside the copied roots): `dump/`, `gamedata/`, `Ryujinx/`, `testenv/`, workspace `builds/` and `scratch/`, and the stray root `moves/` folder (a duplicate of `mods/mii_customizer/moves/aerial_back__mario` that a worker wrote to the wrong place).

In short: nothing taken from the game (dumps, extractions, models, textures, animations, sounds, effects, params, Lua and ACMD scripts, decoded tables, disassembly, relocated machine code, built NROs); no third-party code (vendored crates, Smashline fork, Clone Engine, Lua 5.3.6, Python wheels and DLLs, `*_reference.rs` copies); no logs, crash reports, agent transcripts, SD-card backups, build outputs or caches; no machine-local config (`paths.toml`).

## Game-derived source files left out

Files a build needs that were ported or generated from the game's own scripts, parameters or code, or copied from third-party sources. Where the file header names a generator, it is listed: rerun it against your own dump. Files without a generator were ported by hand and must be ported again (for example with `mods/ssbu_mod_new/tools/fetch_donor_acmd.py` and `mods/ssbu_mod_new/handbook/05_acmd_porting.md`). `mods/ssbu_mod_new/src/pmclone/moveset/src/acmd/` (15 files of ported ACMD) is left out as a whole; `.s`/`.S` relocated machine code appears below only where it sat in the plugin source.

| file | reason | generator |
|---|---|---|
| `mods/mii_customizer/moves/aerial_back__mario/unit.rs` | move unit: ACMD / status code ported from the donor fighter | - |
| `mods/mii_customizer/moves/aerial_forward__cloud/unit.rs` | move unit: ACMD / status code ported from the donor fighter | - |
| `mods/mii_customizer/moves/aerial_up__kamui/unit.rs` | move unit: ACMD / status code ported from the donor fighter | - |
| `mods/mii_customizer/moves/normal_jab__miifighter/unit.rs` | move unit: ACMD / status code ported from the donor fighter | - |
| `mods/mii_customizer/moves/smash_up__fox/unit.rs` | move unit: ACMD / status code ported from the donor fighter | - |
| `mods/mii_customizer/moves/special_neutral__snake/unit.rs` | move unit: ACMD / status code ported from the donor fighter | - |
| `mods/mii_customizer/moves/special_up__cloud/unit.rs` | move unit: ACMD / status code ported from the donor fighter | - |
| `mods/mii_customizer/moves/tilt_down__miifighter/unit.rs` | move unit: ACMD / status code ported from the donor fighter | - |
| `mods/mii_customizer/moves/tilt_up__miifighter/unit.rs` | move unit: ACMD / status code ported from the donor fighter | - |
| `mods/mii_customizer/moves/tilt_up__snake/unit.rs` | move unit: ACMD / status code ported from the donor fighter | - |
| `mods/mii_customizer/plugin/src/moves.rs` | own dispatcher mixed with ported Mii Brawler ACMD | - |
| `mods/mii_customizer/plugin/src/unit_aerial_back_mario.rs` | own dispatcher mixed with ported Mii Brawler ACMD | - |
| `mods/mii_customizer/plugin/src/unit_aerial_forward_cloud.rs` | own dispatcher mixed with ported Mii Brawler ACMD | - |
| `mods/mii_customizer/plugin/src/unit_smash_up.rs` | own dispatcher mixed with ported Mii Brawler ACMD | - |
| `mods/mii_customizer/plugin/src/unit_special_up_cloud.rs` | own dispatcher mixed with ported Mii Brawler ACMD | - |
| `mods/mii_customizer/plugin/src/unit_tilt_down.rs` | own dispatcher mixed with ported Mii Brawler ACMD | - |
| `mods/mii_customizer/plugin/src/unit_tilt_up.rs` | own dispatcher mixed with ported Mii Brawler ACMD | - |
| `mods/mii_customizer/plugin/src/unit_tilt_up_snake.rs` | own dispatcher mixed with ported Mii Brawler ACMD | - |
| `mods/mii_customizer/scratch/2026-10-07_MV-aerial_back__mario/plugin/src/moves.rs` | ACMD ported from game scripts (heuristic) | - |
| `mods/mii_customizer/scratch/2026-10-07_MV-aerial_back__mario/plugin/src/unit_aerial_back_mario.rs` | ACMD ported from game scripts (heuristic) | - |
| `mods/ssbu_mod_new/refs/diddy_monkey_flip/source_audit/motion_lib_asm.rs` | pinned donor material / decoded game data (refs) | - |
| `mods/ssbu_mod_new/refs/diddy_monkey_flip/source_audit/motion_lib_disasm.rs` | pinned donor material / decoded game data (refs) | - |
| `mods/ssbu_mod_new/refs/diddy_monkey_flip/source_audit/motion_lib_mlist.rs` | pinned donor material / decoded game data (refs) | - |
| `mods/ssbu_mod_new/refs/donkey_cargo/lua_const.rs` | pinned donor material / decoded game data (refs) | - |
| `mods/ssbu_mod_new/src/mgw_swap/src/attack_air_f.rs` | ported decompiled game status code | - |
| `mods/ssbu_mod_new/src/mgw_swap/src/attack_air_hi.rs` | ported decompiled game status code | - |
| `mods/ssbu_mod_new/src/mgw_swap/src/hero_spin3_acmd.rs` | ported decompiled game status code | `mods/ssbu_mod_new/src/mgw_swap/tools/generate_hero_spin3_acmd.py` |
| `mods/ssbu_mod_new/src/mgw_swap/src/hero_spin3_params.rs` | ported decompiled game status code | `mods/ssbu_mod_new/src/mgw_swap/tools/extract_hero_spin3_params.py` |
| `mods/ssbu_mod_new/src/mgw_swap/src/hero_spin3_vanilla_acmd.rs` | ported decompiled game status code | - |
| `mods/ssbu_mod_new/src/mgw_swap/src/hero_spin_params.rs` | ported decompiled game status code | `mods/ssbu_mod_new/src/mgw_swap/tools/extract_hero_spin_params.py` |
| `mods/ssbu_mod_new/src/mgw_swap/src/monkey_flip.rs` | ported decompiled game status code | - |
| `mods/ssbu_mod_new/src/mgw_swap/src/monkey_flip_params.rs` | ported decompiled game status code | `references/diddy_specials/extract_params.py` (not in this copy) |
| `mods/ssbu_mod_new/src/mgw_swap/src/monkey_flip_status.rs` | ported decompiled game status code | - |
| `mods/ssbu_mod_new/src/mgw_swap/src/throw_lw.rs` | ported decompiled game status code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/attack_air_f.rs` | ported ACMD | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/chrom_jab.rs` | ported ACMD | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/gaogaen_throw_b.rs` | ported ACMD | `mods/ssbu_mod_new/src/pgwr/tools/gaogaen_throw_b/pipeline.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/littlemac_attack_s4.rs` | ported ACMD | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/monkey_flip.rs` | ported ACMD | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/pikachu_attack_air_b.rs` | ported ACMD | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/robot_attack_lw3.rs` | ported ACMD | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/snake_attack_hi3.rs` | ported ACMD | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/snake_throw_lw.rs` | ported ACMD | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/attack_air_hi.rs` | ported decompiled game code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_mana/hud_signatures.rs` | generated from game params | `mods/ssbu_mod_new/tools/audit_hero_mana_native.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_mana/params.rs` | generated from game params | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_neutral_b/acmd.rs` | translated from game NRO code | `mods/ssbu_mod_new/tools/gen_hero_neutral_b_acmd.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_neutral_b/donor_params.rs` | translated from game NRO code | `mods/ssbu_mod_new/tools/gen_hero_fireball_initializer.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_neutral_b/fighter.rs` | translated from game NRO code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_neutral_b/initializer_1304.s` | translated from game NRO code | `mods/ssbu_mod_new/tools/gen_hero_fireball_initializer.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_neutral_b/signatures.rs` | translated from game NRO code | `mods/ssbu_mod_new/tools/gen_hero_fireball_initializer.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/fighter.rs` | translated from game NRO code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/fighter_loops.rs` | translated from game NRO code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/game_acmd.rs` | translated from game NRO code | `mods/ssbu_mod_new/tools/gen_hero_side_b_game_acmd.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/native_1304.s` | translated from game NRO code | `mods/ssbu_mod_new/tools/gen_hero_side_b_native.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/native_params.rs` | translated from game NRO code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/native_signatures.rs` | translated from game NRO code | `mods/ssbu_mod_new/tools/gen_hero_side_b_native.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/params.rs` | translated from game NRO code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/receiver.rs` | translated from game NRO code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/script_acmd.rs` | translated from game NRO code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_spin_acmd.rs` | ported decompiled game code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_spin_params.rs` | ported decompiled game code | `mods/ssbu_mod_new/src/mgw_swap/tools/extract_hero_spin3_params.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/lucas_attack_lw4.rs` | ported decompiled game code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/ness_throw_b.rs` | ported decompiled game code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/throw_lw.rs` | ported decompiled game code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/params.rs` | generated from game params | `mods/ssbu_mod_new/src/pgwr/tools/extract_gw_params.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/dk_cargo/acmd.rs` | relocated game machine code | `mods/ssbu_mod_new/src/pgwr/tools/dk_cargo/generate_runtime.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/dk_cargo/callbacks.S` | relocated game machine code | `mods/ssbu_mod_new/src/pgwr/tools/dk_cargo/emit_callbacks.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/dk_cargo/data.rs` | relocated game machine code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/dk_cargo/lifetime.S` | relocated game machine code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/gaogaen_throw_b_data.rs` | translated from game native code | `mods/ssbu_mod_new/src/pgwr/tools/gaogaen_throw_b/runtime_package.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/monkey_flip.rs` | translated from game native code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/monkey_flip_capture.rs` | translated from game native code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/monkey_flip_capture_data.rs` | translated from game native code | `mods/ssbu_mod_new/tools/gen_mflip_capture_data.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/monkey_flip_params.rs` | translated from game native code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/snake_grenade/acmd.rs` | translated from game native code | `mods/ssbu_mod_new/tools/gen_snake_neutral_b.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/snake_grenade/lower.rs` | translated from game native code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/snake_grenade/mod.rs` | translated from game native code | - |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/snake_grenade/native_signatures.rs` | translated from game native code | `mods/ssbu_mod_new/tools/audit_snake_grenade_native.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/snake_grenade/params.rs` | translated from game native code | `mods/ssbu_mod_new/tools/gen_snake_neutral_b.py` |
| `mods/ssbu_mod_new/src/pgwr/plugin/src/status/special_hi.rs` | translated from game native code | - |
| `mods/ssbu_mod_new/src/pgwr/tools/eff_reference.rs` | third-party source copy | - |
| `mods/ssbu_mod_new/src/pgwr/tools/one_slot_effects_reference.rs` | third-party source copy | - |
| `mods/ssbu_mod_new/src/pgwr/tools/texture_cli/bntx_reference.rs` | third-party source copy | - |
| `mods/ssbu_mod_new/src/pgwr/tools/texture_cli/lib_reference.rs` | third-party source copy | - |
| `mods/ssbu_mod_new/src/pgwr/tools/texture_cli/main_reference.rs` | third-party source copy | - |
| `mods/ssbu_mod_new/src/pgwr/tools/texture_cli/nutexb_reference.rs` | third-party source copy | - |
| `mods/ssbu_mod_new/src/pmclone/runtime/src/modules.rs` | generated from third-party bindings | `mods/ssbu_mod_new/src/pmclone/tools/namespace_modules.py` |
| `mods/ssbu_mod_new/src/pmclone/trace/src/work_ids.rs` | generated from third-party bindings | `mods/ssbu_mod_new/src/pmclone/tools/gen_trace_work_ids.py` |

## Redactions and edits in copied files

Automatic replacements (rules in `export.py`): workspace absolute paths to relative paths (bare root to `<workspace>`, old root to `<old workspace path>`); user-profile paths to `%USERPROFILE%`; the ArcExplorer install path to `<ArcExplorer dir>`; SD-card drive letters to `sd:/`; other drive-letter paths to `<drive>:/`; the machine account name to `<user>`; e-mail addresses to `<email>` (none were found).

| file | replacements |
|---|---|
| `AGENTS.md` | workspace path x2 |
| `evidence/freebuff-dispatch/2026-10-02_run1/luna/run-result.json` | workspace path x2 |
| `evidence/freebuff-dispatch/2026-10-02_run1/rendered/1-littlemac-fist-trails.md` | workspace path x1 |
| `evidence/freebuff-dispatch/2026-10-02_run1/rendered/2-snake-up-tilt.md` | workspace path x1 |
| `evidence/freebuff-dispatch/2026-10-02_run1/rendered/3-mythra-mana.md` | workspace path x1 |
| `kb/INDEX.md` | manual edit x1 |
| `kb/findings/claude-and-codex-clis-report-real-subscription-limits.md` | manual edit x1 |
| `kb/findings/data-arc-extraction-needs-user-viewer-check.md` | workspace path x1 |
| `kb/findings/luna-desktop-codex-home-and-edge-approval.md` | user home path x1 |
| `kb/journal/2026-10-02.md` | SD card path x1 |
| `kb/playbooks/extracting-data-arc-offline.md` | workspace path x1 |
| `kb/playbooks/user-driven-workflow.md` | workspace path x1, user home path x1, SD card path x2 |
| `kb/reference/local-machine.md` | workspace path x1, tool install path x1, manual edit x4 |
| `kb/reference/mod-workspace.md` | workspace path x1, user home path x1, tool install path x2, drive path x1 |
| `kb/reference/offline-data-arc-extraction.md` | workspace path x1 |
| `kb/reference/ssbu-modding-stack.md` | tool install path x1 |
| `mods/mii_customizer/evidence/P2-LAYOUT-PATCH/checks.json` | workspace path x4 |
| `mods/mii_customizer/evidence/P2-SARC-WRITE/checks.json` | user home path x1 |
| `mods/mii_customizer/research/P1-UI-DECODE.md` | workspace path x1 |
| `mods/mii_customizer/tools/gunner-catalog/validate_catalog.py` | drive path x2 |
| `mods/ssbu_mod_new/evidence/2026-10-02_pgwr_T-0050/RESULT.md` | tool install path x1 |
| `mods/ssbu_mod_new/evidence/2026-10-02_pgwr_T-0052/RESULT.md` | SD card path x1 |
| `mods/ssbu_mod_new/evidence/2026-10-02_pgwr_T-0060_ness_throw_b/DELTA.json` | workspace path x2 |
| `mods/ssbu_mod_new/evidence/2026-10-02_pgwr_snake_uptilt/RESULT.md` | tool install path x1 |
| `mods/ssbu_mod_new/evidence/2026-10-03_pgwr_ready_assets_1/JAB_AUDIT.json` | workspace path x2 |
| `mods/ssbu_mod_new/evidence/install-record-0.14.0.json` | drive path x1 |
| `mods/ssbu_mod_new/evidence/install-record-2026-09-29_2330.json` | drive path x1 |
| `mods/ssbu_mod_new/evidence/install-record-2026-09-30_0041.json` | drive path x1 |
| `mods/ssbu_mod_new/evidence/install-record-2026-09-30_0123.json` | drive path x1 |
| `mods/ssbu_mod_new/evidence/install-record-2026-09-30_0139.json` | drive path x1 |
| `mods/ssbu_mod_new/evidence/install-record-2026-09-30_0218.json` | drive path x1 |
| `mods/ssbu_mod_new/evidence/install-record-2026-09-30_0227.json` | SD card path x1, drive path x1 |
| `mods/ssbu_mod_new/evidence/pmclone_loader_check/result.json` | SD card path x1 |
| `mods/ssbu_mod_new/evidence/user_console_runs_2026-09-29/console-2026-09-29-article/RESULT.md` | SD card path x1 |
| `mods/ssbu_mod_new/evidence/user_console_runs_2026-09-29/console-2026-09-29-prereq/RESULT.md` | SD card path x2 |
| `mods/ssbu_mod_new/evidence/user_console_runs_2026-09-29/console-2026-09-29-run1/RESULT.md` | SD card path x2 |
| `mods/ssbu_mod_new/handbook/facts/facts.yaml` | tool install path x1, SD card path x2 |
| `mods/ssbu_mod_new/kb/findings/a-diagnostic-after-the-success-check-says-nothing.md` | SD card path x3 |
| `mods/ssbu_mod_new/kb/findings/pgwr-card-autodetect-and-asset-only-installs.md` | workspace path x1, SD card path x1 |
| `mods/ssbu_mod_new/projects/_workspace_migration/KNOWLEDGE_TRIAGE.md` | account name x2 |
| `mods/ssbu_mod_new/projects/_workspace_migration/PLAN.md` | account name x2 |
| `mods/ssbu_mod_new/src/mgw_swap/deploy.py` | user home path x1 |
| `mods/ssbu_mod_new/src/pgwr/install-record-0.14.0.json` | drive path x1 |
| `mods/ssbu_mod_new/src/pgwr/tools/package_pikachu_airb.py` | SD card path x1 |
| `mods/ssbu_mod_new/tools/README.md` | SD card path x1 |
| `mods/ssbu_mod_new/tools/audit_hero_mana_native.py` | tool install path x1 |
| `mods/ssbu_mod_new/tools/verify_installed_card.py` | SD card path x2 |
| `tools/REGISTRY.md` | manual edit x1 |
| `tools/data-arc-extract/README.md` | workspace path x2 |

Manual edits (the `manual edit` entries above; exact rules in `TEXT_EDITS` in `export.py`):

- `kb/INDEX.md`: removed the row that linked the left-out Google-account finding.
- `kb/findings/claude-and-codex-clis-report-real-subscription-limits.md`: "this Pro account" became "the account used" (subscription tier).
- `kb/reference/local-machine.md`: the CLI login-state values replaced by "(removed for publication)".

Disassembly removed from reports (runs of 12 or more instruction lines replaced by a one-line note):

- `mods/mii_customizer/evidence/P2-STAT-READS/summary_weight.md`: 18 lines
- `mods/mii_customizer/research/P4-BRIDGE-FACTS.md`: 29 lines
- `mods/mii_customizer/research/P4-STAT-SITES.md`: 29 lines
- `mods/mii_customizer/research/P9-EDIT-DISPATCH.md`: 33 lines
- `mods/mii_customizer/research/P9-HAT-HANDLES.md`: 68 lines

Redactions that touch code (check before running these scripts):

- `mods/ssbu_mod_new/tools/verify_installed_card.py`: the default card path became `sd:/ultimate/mods/...`; pass your card's real path.
- `mods/mii_customizer/tools/gunner-catalog/validate_catalog.py`: a guard that asserts no absolute drive path appears in its output now tests for the placeholder `<drive>:/`; restore the drive letter if you rely on it.
- Workspace-path replacements in JSON records (`checks.json`, `install-record-*.json`, ...) only change recorded strings, not behaviour.

Left out for personal-data reasons: `kb/findings/gemini-cli-rejects-this-google-account.md` (describes the user's Google account tier).

Left out as third-party leftovers whose code was already excluded: `mods/ssbu_mod_new/src/pgwr/tools/one_slot_effects/UPSTREAM_README.md`, `mods/ssbu_mod_new/src/pgwr/tools/texture_cli/LICENSE`.

Written by hand after the export run (a rerun of `export.py` does not reproduce them): `README.md`, `MANIFEST.md` (by `make_manifest.py`), `NEEDS_DECISION.md`, `dump/README.md`, `gamedata/README.md`, and the `tools/showcase-export/` scripts and README. The `showcase-export` row in `tools/REGISTRY.md` is added by `export.py` (`TEXT_EDITS`).

## Final checks (2026-10-15, `tools/showcase-export/check_export.py`)

| check | result |
|---|---|
| e-mail addresses | 0 |
| account / personal names (machine account, real name) | 0 |
| user-profile paths (`C:\Users\...`) | 0 |
| drive-letter paths | 10 in 7 files (not counting this table), all justified: standard install locations (`C:/msys64`, `C:\Program Files\dotnet`, `c:\devkitPro`), an elided `C:\...` in a note, and string literals in path-guard checks (`validate_catalog.py`, `check_presets.py`, `patch_examples.py` escape sequence `f:\n`) |
| phone-number pattern | 23 in 9 files (not counting this table), all hex dumps or byte counts in research reports (`0001 0005 0002`, `86 672 752`) |
| key / token / secret / password / Bearer | about 1,900 occurrences of the words (dictionary keys, param-hash keys, `prod.keys` file names, tokenizer variables); a targeted scan for assigned secret values, `Bearer` headers and known token formats (`sk-`, `ghp_`, `AKIA`, `AIza`, `xox*`) found none (one hit: a Rust variable `let token = s.cast_token...`) |
| hex longer than 64 | 2, the same sha256 written with one extra digit in two snake-grenade notes |
| base64-like strings | 21 in 19 files, all file paths (`atmosphere/contents/01006A800016E000/...`) or a mixed-case sha256 |
| files over 200 KB | 1: `mods/ssbu_mod_new/CURRENT_INSTALL.md` (209 KB, agent-written install records; plain text) |
| non-text files | 0 |
| relative links in README.md, MANIFEST.md, NEEDS_DECISION.md | all resolve |

