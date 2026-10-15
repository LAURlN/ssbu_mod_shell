# T-0036 offline animation authoring record — 2026-10-01

Run completed 2026-10-02 after local midnight; authoring/staging began 2026-10-01.

No automated tests, Ryujinx, console run or card installation. Status needs_review.
Generation and static source/asset inspection only (B); console appearance and
behavior remain D. `pose_preview.png` was viewed as a joint authoring preview,
not a mesh render. Source branch `lab/T-0036`; commit identified by that branch.

Inputs: pinned `refs/robot_attack_lw3/arc/fighter/robot/motion/body/c00/`
clip and motion list; actual `builds/pgwr/0.20.16/ultimate/mods/pyra_gamewatch_reskin/`
recipient c06/c07 skeleton and idle. Input hashes in `animation_generation.json`.
No external export or missing dump substitute was used.

## Commands actually used (mod root)

1. Source/bind inspection with `Get-Content`, `rg`, and `python -B -c` reading
   `ssbh_data_py` skeletons, recipient idle and donor sample values.
2. `python -B src/pgwr/tools/build_robot_dtilt.py --baseline builds/pgwr/0.20.16 --package builds/pgwr/0.20.16+robot-dtilt.2 --stage-only`
3. Same command with package suffix `.3`, after reducing out-of-reach wrist goals.
4. Final: `python -B src/pgwr/tools/build_robot_dtilt.py --baseline builds/pgwr/0.20.16 --package builds/pgwr/0.20.16+robot-dtilt.4 --stage-only --preview`
5. Static `python -B -c` reads of generation report, serialized Visibility group,
   package manifests and SHA-256 inventories. No test runner was invoked.

First draft requested right wrist beyond recipient arm reach by 2.56 units;
goals were shortened/raised to preserve recipient limb lengths. Final recipe has
zero unreachable target distances, five enabled body/hand visibility nodes,
matching c06/c07 clip hashes and recovery to recipient idle at frame 15.
All 165 recipient bones have tracks, including bind/idle-preserved grafted helpers.
Active timing 3/clear 4 and end frame 28 are preserved with donor cancel 15.
Root `Trans` retains idle translation; no skeleton or ACMD modification.

## Identity and preservation

Package `builds/pgwr/0.20.16+robot-dtilt.4/` (core 0.20.16, recipe 2.0.0).
The unchanged built NRO is packaged directly; no Rust compile or new target build.
Unique future cache name recorded: `builds/.cache/pgwr-T-0036-target`.
Exclusive shared build/metadata reservation was lab `state/pgwr-shared-build.lock`,
owner T-0036; concurrent research tasks had separate refs ownership.

- NRO: `81460e74313350aaf569ce832045e8586387ab4ddf10e51bfdb690a8d29ef834` (462848 B).
- Mod tree: `66e3bc5e2c5f174271fd6d14f2dc3c4f6de4b7ca171f73382f3019d59b20b3f0` (1983 files).
- Both clips: `d30722b5763f7b6e4f9e4d834cf57b91b69befccd5eb4321f8fbf3bdc81f6d19`.
- Manifest: `39aedf1cbaa6a0bfb6a7fc8239b870641696f6c6e4793fb4c3de8effa104a469`.
- Report: `f9ddfe4f04168943d00882bc6afad3a3fcc7b90eb5c07a560c773529af97a6e1`.

Historical baseline manifest recorded both old clips as
`ff5fa2cf86037ad2ecddb56d5ad86f12804fa96ba09264c1c86c6021f2f74d8b`;
actual pre-change local clips were
`f328174c727b7ba77bb47db6db76b4ad4588d8b88ed205e88b2da4d14199d4ab`.
Read-only inventory inspection found exactly those two deviations, no added/removed
files; actual baseline tree was
`82f3c21cdca541b8a63a77a33d3ee5ad392dfa892f5dddbe3bd69e492b2a5329`.
All other 1981 files match the historical manifest and remain identical in the stage.
The new manifest records the actual stage, rather than copying stale clip hashes.
No historical baseline files or manifest were edited.

Static source inspection: `robot_attack_lw3.rs` is unchanged; costume registration,
hitbox, effect/sound/expression handlers and slope/rumble behavior remain intact.
Generation requires each preserved motion list to contain the complete pinned donor
entry; motion list files and config routing are byte-preserved. `build.py` diff is
only a comment; its existing generator call still authors both costumes.

Full from-dump rebuild was unnecessary and unavailable because `dumps/arc` is absent.
Baseline copied generation reports remain historical; new manifest explicitly
points to `robot_dtilt_custom.json` as their down-tilt replacement record.
Console palette meshes/deformation, hand/hitbox alignment, facing/slopes, donor
sound/effect playback and recovery feel are unverified. Three checks are in the
down-tilt section of `CURRENT_INSTALL.md`. Draft stages .2 and .3 remain superseded; deletion was blocked by policy.
