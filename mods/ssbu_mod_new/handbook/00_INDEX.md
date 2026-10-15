# Handbook index: "I want to ... -> read ..."

Everything here is distilled from the ~30 agent-written documents in the old workspace, filtered by evidence tier
(see the tier legend at the top of each file). Retracted claims are in `graveyard.md`. Original narratives are kept in
`../projects/*/history/` and `../archive/legacy_docs/` for reference only; **they contain claims that were later refuted.**

| I want to ... | Read |
| --- | --- |
| understand how a move gets copied from one character to another, and how hard it is | `01_pipeline_overview.md` |
| set up the machine, build the plugin/assets, install to the SD card | `02_toolchain.md`, `../AGENTS.md` (section D) |
| find / dump game files, scripts, motion lists, params | `03_dumps.md`, `../dumps/INDEX.md` |
| add or retarget animations, edit `motion_list.bin` | `04_motion_lists_animation.md` |
| port ACMD (game/effect/sound/expression scripts) from the dumps | `05_acmd_porting.md` |
| make custom statuses / ids / kinetics; understand what statuses are | `06_statuses.md` |
| add a projectile / prop / article (clone_weapon) | `07_articles.md`, `10_arcropolis_config_json.md` |
| fix visibility (props, extra meshes), add bones/meshes | `08_visibility_models.md` |
| read or change parameters (`.prc`, `vl.prc`, `expression_vl.prc`) | `09_params_prc.md` |
| write the ARCropolis `config.json` for new files | `10_arcropolis_config_json.md` |
| hook / gate with smashline & skyline; what the bindings lack | `11_smashline_skyline.md` |
| find something in the game binary; offsets for 13.0.4 | `12_native_offsets_13_0_4_only.md` |
| the Mythra <-> Pyra/G&W pair swap machinery | `13_swap_pairs.md` |
| make a stand-alone clone character (Clone Engine) | `14_clone_engine.md` |
| make a grab / catch work | `15_grabs_catch.md` |
| read a crash report or a log | `16_crash_and_log_reading.md` |
| hand a build to the user for testing | `17_hardware_test_protocol.md` |
| repair battle loading portraits and costume/starting-form layout mapping | `18_loading_presentation.md` |
| know what was already tried and failed | `graveyard.md` |

Project state ("what works right now"): `../projects/pgwr/STATUS.md` (live), `mgw_swap`, `mgw_standalone`, `pmclone`.

Known gaps in this handbook (nobody has verified them; do not treat absence as "not a problem"):
sounds/effects playback validation (Hero banks now have offline merge checks; see `07_articles.md`), stats/params port, taunts/final smash/results,
status-script decompilation workflow (Ghidra on the fighter NROs), Kirby copy, general CSS/UI (loading portraits: see `18_loading_presentation.md`; standalone portraits: see standalone p2 notes).
