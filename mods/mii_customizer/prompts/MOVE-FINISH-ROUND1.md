# MOVE-FINISH round 1 - 2026-10-08 - workers started by the coordinator (Claude subagents)

At the user's request the coordinator started these itself. Every worker reads
`prompts/MOVE-FINISH-COMMON.md` first; its own task names the unit, where it stands, what
"finished" means and the matching reference in the other mod.

| task | model | to finish | main reference |
|---|---|---|---|
| MV-aerial_forward__cloud + MV-special_up__cloud (one worker, shared sword) | Opus 5.5 | Buster Sword in hand, slash effect, trail, sounds, landing; Climhazzard statuses (rise, second-input dive, fall, landing, ledge), retargeted clips | other mod `refs/cloud_attack_air_f/`, handbook 07 / 08 |
| MV-special_neutral__snake | Opus 5.5 | stages S3-S6: statuses, grenade item, fuse bridge, lower-body clips, unit files, build, check | other mod `src/pgwr/plugin/src/status/snake_grenade/`, `refs/snake_grenade/` |
| MV-tilt_up__snake | Haiku 5.5 | redo the stub: facts, retargeted clip, scripts, Snake effects and sounds, unit files, build, check | other mod `refs/snake_attack_hi3/` |
| MV-normal_jab__miifighter | Haiku 5.5 | own status code for jab 1 -> 2 -> rapid -> finisher; rapid-jab scripts decoded; `kneel` bone; Brawler effect and sounds | other mod `refs/chrom_jab/` |
| MV-aerial_up__kamui | Haiku 5.5 | retarget, unit files, Corrin's sword in hand, effects and sounds, build, check | `scratch/2026-10-07_MV-aerial_forward__cloud/`, other mod handbook 07 / 08 |

Not given to a worker: MV-aerial_back__mario (reported DONE; coordinator reviews and
integrates), the three Brawler tilts and Fox's up smash (integrated in 0.9.0 / 0.10.0).
Base for every plugin copy: `builds/.cache/plugin_base_0.10.0/` (snapshot of `plugin/`).
