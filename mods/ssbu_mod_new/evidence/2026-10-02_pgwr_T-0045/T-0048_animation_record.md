# T-0048 - stretched-arm down-tilt animation: authoring and staging record

Worker run 2026-10-02, branch `lab/T-0048`, staged from the approved baseline
`builds/pgwr/0.20.16+robot-dtilt.4` (confirmed against `CURRENT_INSTALL.md` at execution time:
that is the "Last recorded card state", installed 2026-10-02 by the T-0042 designated
installer, hardware test still pending).

**No automated test, no Ryujinx, no console run, no card access.** Everything below is offline
generation and static inspection (tier B). Console appearance and alignment remain tier D.

## Command actually run (mod root, CPython 3.12.3, ssbh_data_py 0.9.1, numpy 2.2.2)

```bash
python -B src/pgwr/tools/build_robot_dtilt.py \
  --baseline builds/pgwr/0.20.16+robot-dtilt.4 \
  --package  builds/pgwr/0.20.16+robot-dtilt.5 \
  --stage-only --preview
```

Exit 0. The superseded `.2` and `.3` drafts (T-0036's) were not used and not rebuilt.

## What the recipe and the builder now do

Design input: `evidence/2026-10-02_pgwr_T-0045/T-0047_design_record.md` (subtask 0).

Recipe 2.0.0 asked `solve_limb` for wrist goals about **5.2x the recipient's arm length**
(measured arm span 3.9477 L / 3.9641 R against a target roughly 20.7 out). `solve_limb` clamps
to the link reach, so the unreachable part of each goal was silently dropped and the frame-3
pose peaked short of the capsule. Recipe 3.0.0 does not push those goals through the old IK:

- `solve_limb` is now **feet only**, documented as such.
- New `deform_arm()` deforms each arm as a **rigid block rooted at `Shoulder{L,R}`**: rotate the
  shoulder so the shoulder-to-hand line points along the recipe's `arm_aim`, then translate the
  shoulder by a pure shift along that same direction until the hand sits `arm_reach * H` from
  the fighter's origin. `Arm{L,R}`, `Hand{L,R}` and the `H_*` helpers are children and ride
  along untouched.
- The target is anchored to the **origin**, not to each arm's own idle hand. The left arm hangs
  further back at rest, so an idle-relative target would land it short and one shared recipe
  value could not serve both arms.
- `H = 12.8334` model units (skinned visible mesh, ground -0.0811 to crown 12.7522, idle frame 0),
  measured by `tools/measure_recipient_pose.py` and recorded in the recipe with its provenance.

Transform serialization, as the task required:

- `decompose()` splits any 3x3 into an orthonormal rotation plus a positive axis-aligned scale
  by Gram-Schmidt over the matrix's own columns. Verified exact on a non-orthonormal test
  matrix (round-trip error 0.0) and on all 165 recipient bones (max 9.6e-07, float noise in
  the `.nusktb` itself); minimum `det(rotation)` 0.9999999999999998.
- `quaternion()` orthonormalizes before extracting, so a scale can no longer be folded
  silently into the rotation.
- The emitted `Transform` now carries the bone's **actual** scale instead of a hardcoded
  `[1,1,1]`, and the weight lerp interpolates scale alongside rotation and translation.
- The recipe still scales nothing. That is now a measured invariant rather than an accident of
  the emit path: `scale_written_max_deviation` = 2.7e-15 across all 29 frames and 165 bones,
  and `base_bone_scale_deviation` = 5.2e-07 (the recipient's own bind noise). Hands, head and
  body keep their proportions by construction, because the arm deformation is rigid.

Shared-build coordination, adapted from the hardcoded T-0036 identity:

- `--task-id` (default `T-0048`, or `PGWR_BUILD_TASK`) drives the reservation owner, the report
  identity, the manifest `task`/`scope`, and the reserved cargo target name
  (`builds/.cache/pgwr-T-0048-target`; no Rust build was needed).
- The lab lock `state/pgwr-shared-build.lock` is **taken when free and refused when held**: a
  live reservation owned by another task aborts the run with that owner named. It was free
  here, was held for the duration, and was released in a `finally` block (verified absent after
  the run, including after an intentional mid-run failure during development).
- `animation_version` in the report is read from the recipe, not hardcoded.

Preview (`--preview`, build work, not a test):

- Seven panels - frames **0, 1, 2, 3, 4, 6, 15** - each with its own pose but **one shared
  z/y bound and one shared scale** across all panels, so a stretched arm is never clipped and
  the overlay is directly comparable between frames.
- Draws every bone (not the first 31), highlighting the arm chains, plus the donor capsule as a
  stadium **in the same mapping** as the joints. The capsule is parsed out of
  `robot_attack_lw3.rs` at run time, not copied.
- Output `robot_dtilt_pose_preview.png`, 2960x746, 39,589 B,
  sha256 `0f37622cc6937baceed6864dc403429bf52f2129f40aa957abd9b3f0ed4d16a8`.
- Offline geometry check of the preview's own transform: shared bound z -12.40..23.00,
  y -7.12..14.21 at 10.96 px/unit; tightest clearance from any bone or capsule point to its
  panel edge **37.92 px**, so nothing is clipped. Pixel check confirms the capsule fill, both
  capsule outlines, and both arm colours are drawn. This is a joint diagram; it renders no
  mesh and makes no hardware claim.

## Measured result (identical for c06 and c07 - both clips hash the same)

| measurement | value |
| --- | --- |
| clip sha256 (both slots) | `06fb085e436a7e49862f1c64223afd6c659cc68c35ae55f8b99a2f6443f22060` |
| baseline clip sha256 (replaced) | `d30722b5763f7b6e4f9e4d834cf57b91b69befccd5eb4321f8fbf3bdc81f6d19` |
| frame 3 hand L | `(0.269, 2.596, 16.115)` |
| frame 3 hand R | `(-0.327, 1.902, 15.990)` |
| frame 3 shoulder L / R | `(0.269, 2.780, 15.091)` / `(-0.327, 1.937, 15.798)` |
| arm extension from idle, body heights | L 1.515, R 0.916 |
| hand forward of origin, body heights | L 1.256, R 1.246 |
| capsule (`r` 3.4, `(0,1.7,21)`->`(0,7,9)`) surface gap | L -2.215 (**inside**), R -1.532 (**inside**) |
| arm span (what posing alone could reach) | L 3.9477, R 3.9641 |
| shoulder slide | L `(0, -1.758, 9.769)`, R `(0, -1.606, 8.921)` |
| slide beyond what a rigid arm could reach | L 5.821, R 4.957 |
| leg IK shortfall (feet) | 0.0 at every frame |
| max bone displacement from idle at frame 15 and 28 | 4.87e-07 |
| all transforms finite | yes, asserted per bone per frame |

Anticipation and retraction ramp, read back from the staged generation report for the shipped
recipe 3.0.0 (`arm_reach` 1.20). `gap` is the signed distance from the hand bone to the
capsule surface, negative meaning inside; `ext` is the hand's forward displacement from its own
idle position in body heights.

| frame | ext H (L/R) | inside capsule (L/R) | surface gap (L/R) |
| --- | --- | --- | --- |
| 0 | 0.000 / 0.000 | no / no | 9.14 / 1.95 |
| 1 | 0.551 / 0.375 | no / yes | 3.20 / -1.64 |
| 2 | 1.374 / 0.889 | yes / yes | -1.68 / -2.88 |
| 3 | 1.515 / 0.916 | yes / yes | -2.21 / -1.53 |
| 4 | 1.466 / 0.867 | yes / yes | -2.07 / -1.38 |
| 6 | 0.978 / 0.640 | no / yes | 0.43 / -2.59 |
| 8 | 0.332 / 0.245 | no / yes | 5.39 / -0.75 |
| 12 | 0.068 / 0.055 | no / no | 8.33 / 1.29 |
| 15 | 0.000 / 0.000 | no / no | 9.14 / 1.95 |

Frames 1, 2 and 4 also place geometry inside the capsule. That is not a change to gameplay -
the ACMD still activates the hitbox on frame 3 and clears it on frame 4, and that file is
untouched - but it is stated rather than left for the user to discover.

## Package and preservation

`builds/pgwr/0.20.16+robot-dtilt.5/`, core version 0.20.16, animation recipe 3.0.0.

| artifact | sha256 |
| --- | --- |
| `MANIFEST.json` | `ef1246962b3e8e0651b5cf3723037c3f1072c1a099b1b2f3000270800b7a4aaa` |
| `robot_dtilt_custom.json` (generation report) | `d39df6bcfbc368136ec8aac4ce010a04f8cf39cc5696894d48407e1d6eaf23b0` |
| `robot_dtilt_pose_preview.png` | `0f37622cc6937baceed6864dc403429bf52f2129f40aa957abd9b3f0ed4d16a8` |
| mod tree (1983 files) | `a976ff51bc04c69fefbbd758ee779a0ca25904f9d175d015cbf09d4c4dc0d491` |
| `libpyra_gamewatch_reskin.nro` (unchanged) | `81460e74313350aaf569ce832045e8586387ab4ddf10e51bfdb690a8d29ef834` |
| `libone_slot_eff.nro` (unchanged) | `e6e5659de3c95a3ff8484f87bd8ef1c129f6c563290903f9f8b8e95177dda70b` |
| `src/pgwr/tools/build_robot_dtilt.py` | `c724cdfbc9e143127c2f2cff008810e1c2f8e1a1dcea29250f36e221373f418c` |
| `src/pgwr/assets/robot_dtilt/recipe.json` | `457de008153b8cd1ea90bda900300223579e8bed3bb062707074a4edea8d35b1` |
| `src/pgwr/plugin/src/acmd/robot_attack_lw3.rs` (hitbox source, unchanged) | `0e91f1deeddd711a3c026406e5ae4f746ef1061985e67f948069229c87ba4732` |

Baseline delta, recomputed independently after staging: **1983 files in, 1983 out, 0 added,
0 removed**, and exactly two changed - `fighter/eflame/motion/body/c06/c02attacklw3.nuanmb`
and its `c07` twin. Nothing else in the mod tree moved, and both packaged NROs are byte-equal
to the baseline (the staging script now refuses a package whose NROs differ, not just records
that they were reused). The recomputed mod-tree hash matches the manifest's `artifacts.mod_tree`.

Preserved, by inspection of the unchanged baseline bytes and of the untouched source:

- Gameplay: ACMD, hitbox (r 3.4 capsule, frame 3 active, frame 4 clear), effects, sounds,
  rumble, slope commands, damage 5.0 / angle 361 / knockback 100, duration 28, cancel 15.
- The donor's complete raw `attack_lw3` motion-list entry in both slots (flags 0x80, cancel 15,
  R.O.B.'s own script hashes) - the staging script asserts it is still present in each motion
  list before and after.
- Costume gate `[6,7]`, c06/c07 routing, `config.json`, all other moves and sounds.
- Recipient skeleton and idle byte-identical; visibility copied from recipient idle (98 nodes,
  no Material tracks, no skeleton edit); all 165 bones keep explicit tracks including the
  grafted helpers; feet planted with zero IK shortfall.
- No manhole: G&W's own `AttackLw3` remains overridden by R.O.B.'s, which spawns no article.
- `build.py` is unchanged; `retarget()` and `deploy_for_slot()` keep their signatures
  (`retarget` gained one optional keyword), so the full-build path is unaffected.

## Unverified - needs the user's console judgment

Everything about behaviour. Specifically:

- how the stretched arms look as **mesh**: the rigid block preserves the fist's size exactly by
  construction, but whether a shoulder slid ~9 units forward reads as a stretch or as a
  detached arm is not measurable offline. This is the highest-risk visual outcome and it was
  disclosed as such in subtask 0's design record.
- whether the palms line up with what the engine actually evaluates. The capsule is read from
  the ACMD, but where the engine places a `top` hitbox in world space is decided by `main`,
  which none of these files can answer (G&W's own jab fist sits 6.236 units from its own
  sphere centre when both are read in model units).
- whether the engine applies the non-unit scale channel at all. This recipe writes unit scale,
  so the shipped pose does not depend on it; the scale-aware path is there so a future
  deformation cannot silently corrupt rotations.
- facing (mirroring), slopes, foot sliding, floor clipping, recovery feel, repeated down
  tilts, and whether the frame 3-4 pose reads as deliberate.
- c07 was measured separately (its own generation ran and its report is in the package); the
  two clips are byte-identical, so any difference on screen would be the costume's own meshes.

Manual checks are in the R.O.B. down-tilt section of `CURRENT_INSTALL.md`.