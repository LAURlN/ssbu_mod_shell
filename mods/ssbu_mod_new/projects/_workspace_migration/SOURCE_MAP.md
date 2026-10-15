# Source map: every top-level item in modpack_test_1 and where it goes

Legend: **KEEP** = becomes part of test_2 (moved), **MINE** = extract knowledge/tools then archive, **ARCHIVE** = cold storage,
**DELETE** = regenerable or junk (after your OK), **?** = your decision.
Sizes are from the survey (files / MB).

| Item | Size | What it is | Disposition |
| --- | --- | --- | --- |
| `mod_files/pyra_gamewatch_reskin` | mixed | the live project (plugin, build.py, tools, reports) | **KEEP** -> `src/pgwr`. Drop `__pycache__`, 9x `sd-backup-*` (-> `evidence/sd-backups`, keep last 3), `crash-reports` -> `evidence/`. Reports -> `projects/pgwr/history/` after mining |
| `mod_files/mythra_gamewatch_swap` | 26 top files + src/tools | hook swap project | **KEEP frozen** -> `src/mgw_swap`. Drop `target/`, `build2..5*.log`, `deploy3..8.log`, `__pycache__`, `tools/.deps`. `backups/` + `prototypes/` -> archive |
| `mythra_gamewatch_swap/` (root) | 6 files | leftover v0.8.5/v0.8.6 NROs + validation | **ARCHIVE** (guide §11 already asked to consolidate) |
| `mod_files/mgw_standalone` | 7.7 GB total mod_files | Clone Engine project | **KEEP frozen** -> `src/mgw_standalone`: `src/`, `tools/`, `smashline_1304/`, `pack/`, `*.patch`, `README/ARCH/DIAGNOSIS/MISSING_DUMPS`, validation json. `evidence/`+`latest_logs/` -> `evidence/`. **DELETE**: `target*` (3 dirs), `staging/` (p1-p8 x many, permission-denied dirs), `downloads/`, `vendor/` clones (re-fetchable, pinned commits noted) |
| `pyra_mythra_clone` | 16k files / 2.9 GB | Astra's copy-everything clone + trace recorder | **MINE + ARCHIVE**. Keep `README/HANDOFF/ASSESSMENT/QUESTIONS`, `tools/`, `trace/`, `runtime/`, `moveset/` source, `reports/trace-freeze-incident*.md`, `reports/acmd-*`. `editable/` (~2.9 GB) **DELETE** (regenerable by `prepare.py`); `native/`, `test_output/`, `build/` archive; `reports/console-2026-09-28-freeze` (60+ 160 KB crash logs, mostly duplicates) keep 3, archive rest |
| `export/` | 25k / 4.2 GB | ArcExplorer dump, 13.0.4, partial (98 fighters) | **KEEP** -> `dumps/arc/` (move). Superset of the 36 later network extractions (verify) |
| `Super Smash Bros. Ultimate 13.0.4 […][UPD]/` | 5 files / ~43 MB main | original ExeFS (main, npdm, rtld, sdk, subsdk0) | **KEEP** -> `dumps/exefs/13.0.4/` |
| `pyra_mythra_clone/reference/dumps/{exefs,images}` | 42 MB + 86 MB | duplicate ExeFS + flat image | **KEEP one flat image** (`main.bin`), delete the duplicates after hash-check |
| `references/mythra_gamewatch_feasibility` | 250 files / 93 MB | ASSESSMENT, `main_memory.bin` (dup flat image), symbols json, Ghidra scripts `.c`, `python_tools` (lz4, capstone), swap trace, switch log | **MINE**: symbols json + ghidra scripts -> `dumps/decoded/`; `inspect_main.py` -> `tools/`; rest archive; delete `main_memory.bin` dup |
| `references/diddy_specials`, `miiswordsman_special_hi(3)`, `mythra_ftilt`, `snake_grenade`, `younglink_neutral_b`, `gamewatch_specials`, loose `AttackAirF_*` | ~140 MB | pinned donor ACMD/status/manifests per move | **KEEP** -> `refs/<donor>_<move>/` with a `SOURCE.json` each. Snake grenade -> `refs/` + note "crashes, gated off". Loose duplicates (`AttackAirF_shulk/gamewatch` x2, `test_*`) delete |
| `references/ParamLabels.csv`, `gamewatch_motion_list.yml`, `inject_monkey_flip.py` | 3 MB | param labels, motion list dump, key tool | **KEEP** -> `dumps/scripts/`, `tools/` |
| `SSBU-Dumped-Scripts-main` | 77k / 107 MB | WuBoytH ACMD dumps (copy) | **KEEP** -> `dumps/scripts/SSBU-Dumped-Scripts/` (note commit) or replace by a shallow clone at pinned commit |
| `scratch/` | 7k / 1.2 GB | ~150 one-off scripts, py312 runtime, wheels, vendor, ghidra, logs | **MINE**: promote tools (see PLAN §6). `py312`, `whl`, `vendor` -> `toolchains/` (gitignored) or reinstall; `ghidra/ghidra_11.1.2_PUBLIC` **DELETE** (re-download; keep `ghidra_scripts/` and `analyze_main.sh`); rest -> `archive/scratch_old` then delete after 30 days. `tree.json` (10 MB) and `cand.txt` delete |
| `reports/` | 6 files | user-console RESULT.md runs (2026-09-29) | **KEEP** -> `evidence/` (rename with version) |
| `mod_output/` | 2.4k / 195 MB | staging of what goes to SD (4 trees: atmosphere, ultimate (old swap+probe), new_standalone, pyra_gamewatch_reskin) | pgwr tree -> `builds/pgwr/0.14.0`; old swap/probe trees -> archive |
| `mod_output backup`, `mod_output_pair`, `mod_backup_2` | 26 + 102 + 104 MB | old SD trees / p16 pair / probe zip | **ARCHIVE** (p16 pair: keep manifest only) |
| `sd_backups/` | 5.4k / 518 MB | 11 timestamped copies of the SD mod dir | keep `before_pyra_gw_reskin` (has the original clone packs' config.json templates, referenced by 3 docs) + latest; rest **DELETE**/archive |
| `skins_to_use/` | 271 / 79 MB | black-and-pink Mythra, pink G&W (rar/zip + extracted) | **KEEP** -> `refs/skins/` (they are inputs to standalone). Delete extracted dup or zip |
| `chrom_c07_ftilt` | 1.1k / 487 MB | the *first* mod, Chrom ftilt on Mythra; mostly `target/` | **MINE** (Cargo.toml/lock compat notes) then archive; delete `target` |
| `George v3.0 by LilyLambda`, `ssbuGeorgeMoveset-main` | 60 MB | other people's mods used as reference | **?** shelve in `other_mods/` or delete |
| `skyline-rs-template-smash_smashline` | 20 files | template repo | **ARCHIVE** (or re-clone) |
| `.agents/rules/{movemakerguide, move_replacement_guide, move_reployment_guide}.md` | 125 KB | the rules the agents obeyed | **MINE** into handbook + `AGENTS.md`, then archive the originals (they contain claims now refuted, see triage) |
| `HANDOFF.md`, `GEMINI_MYTHRA_GAMEWATCH_HANDOFF.md`, `README.txt` | 28 KB | root notes: Monkey Flip handoff (mostly still valid), Gemini feasibility brief (historical), 1-paragraph readme | HANDOFF -> mine into `handbook/15`, `projects/mgw_swap`; GEMINI -> archive; README.txt -> delete |
| `01a0a728-905a-773b-ab35-b375addf303e/` | 7 MB | Antigravity/Gemini task dump (conversation json) | **ARCHIVE** (possibly mine for the ExeFS-trace work, not read) |
| `.freebuff/`, `.gitattributes`, `build.log`, `stdout.log` (310 KB), `.git` (empty) | small | tool leftovers | delete logs; keep `.gitattributes` idea; re-init git in test_2 |

## Notes

- `mod_files/pyra_gamewatch_reskin` and `mgw_standalone/smashline_1304` are coupled: the good smashline plugin on the card
  (`5f4091ee…`) is built from `smashline_1304`, and pgwr's `install-to-card.sh` points at `mgw_standalone/target-smashline`.
  Keep `smashline_1304` source in `src/mgw_standalone/` and change the installer default first (see AGENT_RULES §22).
- `pyra_mythra_clone` and `mgw_standalone/vendor/clone_pack_workbench/arc_index/arc_files.tsv` (vanilla filename index) are read by tools
  in both places: move the tsv into `dumps/decoded/arc_files.tsv` and update the paths.
- The Ghidra project under `scratch/ghidra/proj` is 5 KB per the docs (nothing persisted) - safe to drop.
- `mod_files/pyra_gamewatch_reskin/plugin` currently builds against `mgw_standalone` output paths and `scratch/py312`; `build.py` needs a
  path shim (`paths.toml`) before the move is safe.
