---
title: Mesh weighting decides which bone an animation may move; hand bones often carry no visible geometry
summary: On the pgwr recipient the visible fist meshes are skinned to Arm/Shoulder/H_Arm with weight 1.0 and to Hand with weight 0, so translating a hand bone moves nothing on screen; translating the arm bone alone shears the mesh, and rotating/translating the shoulder carries the whole arm block rigidly.
status: verified
tags: [pgwr, ssbh, animation, skinning, research, mod-workspace]
updated: 2026-10-02
source: T-0047
---

## What

When authoring a move on a reskinned recipient, the bone you animate is not necessarily the
bone that carries the geometry you can see. Measured on Pyra c06 reskinned to G&W
(`builds/pgwr/0.20.16+robot-dtilt.4`, skeleton `02ed7ba1...`, numshb `181f4a88...`):

| mesh | influences (max vertex weight) |
|---|---|
| `RhandHold_VIS_O_OBJ_O_NOSORT_AS_OPAQUEShape` | `ArmR` 1.0, `ShoulderR` 1.0, `H_ArmR` 0.495 |
| `LhandHold_VIS_O_OBJ_O_NOSORT_AS_OPAQUEShape` | `ArmL` 1.0, `ShoulderL` 1.0, `H_ArmL` 0.495 |

`HandL` and `HandR` have **weight 0**. Three levers were then separated experimentally on the
right fist at frame 3:

| edit | fist z-extent before → after | max vertex move | result |
|---|---|---|---|
| translate `HandR` +4z | 5.751 → 5.751 | 0.001 | moves nothing visible |
| translate `ArmR` +4z | 5.751 → 4.185 | 4.000 | **shears** - vertices skinned to Shoulder stay put |
| scale `ArmR` 2.0 on its bind axis | 5.751 → 10.126 | 5.006 | lengthens the fist too; y-extent 2.42 → 4.02 |
| rotate+translate `ShoulderR` | 5.751 → 5.751 | exact | **rigid** - size preserved, torso unmoved (0.000) |

Because `Arm` and `H_Arm` are children of `Shoulder`, the shoulder is the root of the whole
visible arm block; moving it alone carries everything rigidly.

## Evidence

Tier B, offline, in `mods/ssbu_mod_new`. Promoted to `tools/measure_recipient_pose.py`
(prints `visible_arm_mesh_weights`), which reproduces every number above. Design record with
the full method comparison, body-height convention (12.8334 model units, skinned visible mesh
at idle frame 0) and pose targets:
`evidence/2026-10-02_pgwr_T-0045/T-0047_design_record.md`.

Skinning convention used, and it matters: `sum(w * world_i @ inv(bindworld_i)) * v`, with
SSBH's row-vector bind matrices transposed for column-vector FK. The two plausible wrong
forms are self-detecting - `world @ inv(bindlocal)` floats the head ~2 units above the
shoulders, `inv(bindworld) @ world` sinks the body below its own feet.

Two further facts measured in the same run:

- **`Hash40::new("top")` is a part label, not a bone.** The 165-bone recipient has `TopHave`,
  no `top`, yet every generated G&W hitbox uses `top` and works. So an ATTACK coordinate and a
  bone position are *not* directly comparable: G&W's own jab fist sits 6.236 units from a
  sphere centre of radius 4.3 when both are read in naive model units. Derive alignment
  against the capsule *axis and radius*, never by matching coordinates.
- **The model origin is the ground plane.** `Trans` sits at world (0,0,0) and the visible
  body's lowest vertex is y = -0.0811, so a bone's world y is height above the feet with no
  further conversion.

## Why

A recipe that reads like "put the wrist here" is written against `Hand*`, which in this rig
carries no visible geometry. The animation generates, the file hashes, all 165 bones get
tracks, and the on-screen result does not move - which looks exactly like a broken clip or an
unloaded motion and invites the wrong debugging. Reading the weights first costs one pass and
removes the whole class of confusion. The same run also shows `Arm`-only translation shears
rather than moving, so even picking the "obviously right" bone is wrong on its own.

## What to do instead / next

- Before authoring a pose, run `tools/measure_recipient_pose.py` and read
  `visible_arm_mesh_weights`. Animate the **root of the influencing set**, not the most
  obviously named bone.
- Prefer rigid motion (rotate+translate the set's root) over scale whenever "do not enlarge
  the hands" is a requirement; scale on this rig fattens the fist measurably (8%/16% at 1.4x,
  22%/66% at 2.0x in x/y).
- Still unverified: nothing here was rendered or run. Every claim is about model geometry, not
  about what the player sees or where the engine places a hitbox.