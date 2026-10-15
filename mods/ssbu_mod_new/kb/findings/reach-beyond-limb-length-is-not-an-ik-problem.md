---
title: A reach longer than the limb is not an IK problem; deform the whole block and anchor the target to the fighter's origin
summary: When a pose asks for more reach than the limb physically has, clamping two-link IK silently truncates the goal and the peak lands short. Decompose the pose into rotate-and-slide on the root of the influencing set, and anchor the target projection to the fighter's origin rather than to each limb's own idle position, so one recipe value can serve a left and a right limb that start in different places.
status: verified
tags: [pgwr, ssbh, animation, ik, hitboxes, research, mod-workspace]
updated: 2026-10-02
source: T-0048
---

## What

Two-link IK solves a two-link chain and clamps the request to the links' reach. Asking it for
a goal 5x further away than the limb is long does not fail loudly: it returns the limb at full
extension and reports the shortfall, and the rest of the goal is dropped. That shortfall is
the whole reason a hand never reaches the hitbox it was authored against.

Split the pose instead into two independent operations on the **root of the influencing set**:

1. **Aim** - rotate that root so the root-to-end direction points along a recipe direction.
2. **Slide** - translate that root by a pure shift along the same direction, so the end lands
   on the target.

Both are rigid, so nothing shears and no size changes. See
`kb/findings/mesh-weighting-decides-which-bone-an-animation-may-move.md` for why the root of
the set, and not the obviously named bone, is the one to move.

**Anchor the target to a common origin, not to each limb's own rest position.** Setting the
target as "my idle position plus N" makes a limb that hangs further back at rest land short of
one that starts forward, so a single shared value cannot serve both. Setting it as "N units
from the fighter's origin, measured along the aim direction" puts both ends in the same place
from one number. On this recipient the origin is also the ground contact plane, so the same
quantity reads as height and as forward reach.

## Evidence

Tier B, offline, in `mods/ssbu_mod_new`. Implemented as `deform_arm()` in
`src/pgwr/tools/build_robot_dtilt.py` (recipe 3.0.0) against
`builds/pgwr/0.20.16+robot-dtilt.5`, built from the approved
`builds/pgwr/0.20.16+robot-dtilt.4` baseline.

The short case, measured: a G&W arm is 3.95-3.96 units from shoulder to hand, 0.31 of a
12.8334-unit body height. The R.O.B. down-tilt capsule's forward sphere sits at z = 21, so
the reach needed is ~5.2x the arm. Recipe v2.0.0 asked for it as an IK wrist offset and the
pose peaked short; recipe v3.0.0 reaches it by slide.

Reach sweep, all measured through `retarget()` and recorded in the generation report. `reach`
is the target projection in body heights from the fighter's origin, `gap` is the signed
distance from the hand bone to the capsule surface (negative is inside):

| reach | hand z (L/R) | hand y (L/R) | extension from idle, H (L/R) | gap (L/R) |
|---|---|---|---|---|
| 0.90 | 12.33 / 12.20 | 3.28 / 2.58 | 1.220 / 0.621 | -1.32 / -0.63 |
| 1.00 | 13.59 / 13.46 | 3.05 / 2.36 | 1.318 / 0.719 | -1.62 / -0.93 |
| 1.17 | 15.74 / 15.61 | 2.66 / 1.97 | 1.486 / 0.886 | -2.13 / -1.44 |
| **1.20 (shipped)** | **16.12 / 15.99** | **2.60 / 1.90** | **1.515 / 0.916** | **-2.21 / -1.53** |
| 1.45 | 19.27 / 19.15 | 2.03 / 1.33 | 1.761 / 1.162 | -2.92 / -2.27 |

1.20 was chosen because both hands sit comfortably inside the collision volume without
crowding its forward tip at z = 24.4. The sweep is reproducible with
`state/scratch/T-0048/sweep_reach.py`.

The capsule is not copied into the tool: `active_hitbox()` parses the `ATTACK` call out of
`src/pgwr/plugin/src/acmd/robot_attack_lw3.rs` (sha256 `0e91f1de...`) on every run and records
that hash in the generation report, so the preview overlay and the reported gap cannot drift
away from the capsule the engine is actually asked to evaluate. It reads r 3.4,
`(0, 1.7, 21)` to `(0, 7, 9)` - the same numbers the research record measured.

## Why

The failure is quiet. Generation succeeds, every bone gets a finite transform, the file hashes,
the report even shows a plausible-looking pose, and only the gap to the hitbox is wrong. It is
worth checking the shortfall explicitly: the generation report now carries `arm_span` (what a
rigid arm of that length could reach) next to `slide_magnitude`, so the part of the goal that
posing cannot deliver is a number in the record instead of an absence.

Two related traps confirmed in the same file:

- **A clamped IK is silent about the clamp.** `solve_limb` returns the shortfall as a number,
  but nothing forces anyone to read it. Restricting it to the feet, where the anchor really is
  a fixed contact point, removes the ambiguity for the arms.
- **Serializing a scale is where deformation quietly corrupts rotations.** Extracting a
  quaternion from a non-orthonormal 3x3 folds the scale into the rotation, and hardcoding
  `[1, 1, 1]` in the emitted transform hides the fact that it was never measured. Decompose
  any 3x3 into an orthonormal rotation plus a positive axis-aligned scale first, then emit the
  scale you measured. On this recipient the recipe scales nothing, so the invariant is checked
  rather than assumed: the report carries `scale_written_max_deviation` (2.7e-15).

Careful with the decomposition itself: `M = R diag(s)` needs `R`'s columns to be the scaled
columns of `M` in order, so Gram-Schmidt over `M`'s own columns is the construction that
works. Eigenvectors of `M M^T` look tempting and are wrong for a rotation, whose `M M^T` is the
identity and therefore has no usable eigenbasis.

## What to do instead / next

- Before authoring, compute the limb's actual span and the target's distance from the anchor.
  If the ratio is anywhere near 1, IK is the wrong tool.
- When it is, report the shortfall rather than absorbing it: aim + slide on the set's root,
  with the target projection measured from the fighter's origin.
- Check `visible_arm_mesh_weights` first; the root of the influencing set is what moves rigidly.
- Still unverified: nothing here was rendered or run. The numbers are model geometry and the
  capsule the ACMD asks for. Whether the player sees a convincing stretch, and whether the arm
  block reads as attached at the shoulder, is tier D and needs a console run.