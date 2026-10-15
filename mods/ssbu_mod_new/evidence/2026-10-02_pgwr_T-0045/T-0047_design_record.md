# T-0047 - stretched-arm pose and hitbox alignment: design and evidence

Worker research, 2026-10-02. No implementation file, recipe, builder, package or shared
status file was changed. Everything below is offline read-only measurement of the built
recipient plus the already-written ACMD. **No test, no emulator, no console run.**
Appearance and in-game alignment remain tier D.

## 1. Inputs actually inspected (paths and hashes)

All under `mods/ssbu_mod_new/`, package `builds/pgwr/0.20.16+robot-dtilt.4`, slot `c06`
(`c07` is byte-identical for every file used here except where noted):

| role | path | sha256 |
| --- | --- | --- |
| recipient skeleton | `.../fighter/eflame/model/body/c06/model.nusktb` | `02ed7ba122998f337c212f29072d44cdf6c582b23ba179f1447bece5e593be83` |
| recipient idle | `.../fighter/eflame/motion/body/c06/a00wait1.nuanmb` | `bbb8e203ee4a7bf9b0d26bdb3b35b88d54bb51c7a6145c4c1a1e2bd887de6bae` |
| staged down-tilt clip | `.../fighter/eflame/motion/body/c06/c02attacklw3.nuanmb` | `d30722b5763f7b6e4f9e4d834cf57b91b69befccd5eb4321f8fbf3bdc81f6d19` |
| skinning mesh | `.../fighter/eflame/model/body/c06/model.numshb` | `181f4a88d599f5a1b0c4860e3867b88e236c62bdccfdc0c06724b245675ef803` |
| mesh list | `.../fighter/eflame/model/body/c06/model.numdlb` | `d1565832e2afde4b16e62ba404fe9d8495f0f7d9442ad6a22d67e0dd27fa6aaf` |
| vanilla control clips | `builds/pgwr/0.20.16/.../c02attacklw3.nuanmb` | `f328174c727b7ba77bb47db6db76b4ad4588d8b88ed205e88b2da4d14199d4ab` |
| vanilla control jab | `builds/pgwr/0.20.16/.../c00attack11.nuanmb` | `b83e2c5aac7794633ec45d9af096025687b96a8c8add4ff1ef8beab826e529b5` |
| ACMD (hitbox source) | `src/pgwr/plugin/src/acmd/robot_attack_lw3.rs` | read only |
| recipe (read only) | `src/pgwr/assets/robot_dtilt/recipe.json` v2.0.0 | read only |
| builder (read only) | `src/pgwr/tools/build_robot_dtilt.py` | read only |
| G&W own scripts | `src/pgwr/plugin/src/acmd/generated/ground.rs` | read only |

The skeleton and idle hashes match the ones T-0036 recorded in
`evidence/2026-10-01_pgwr_T-0036/animation_generation.json` and the handbook, so this run
read the same recipient T-0036 authored against. `dumps/arc` is absent; no outside-workspace
export was used.

## 2. Model-to-`top` coordinate relationship

### 2.1 What was measured, and how

Skinning was resolved before any conclusion was drawn from geometry. `model.numshb` stores
per-vertex `BoneInfluence` entries carrying **bone name + vertex weight**, and mesh positions
are in bind space, so the correct transform is

```
skinned = sum_i w_i * (world_i @ inv(bindworld_i)) * v
```

Three candidate formulations were tried and the wrong two produce obviously absurd bodies,
which is itself the evidence that the chosen one is right:

| variant | `gw` mesh y range | verdict |
| --- | --- | --- |
| `world @ inv(bindworld)` | **-0.081 .. 8.224** | feet on the ground plane, head at hip height |
| `world @ inv(bindlocal)` | -0.587 .. 9.999 | head floating ~2 units above the shoulders |
| `inv(bindworld) @ world` | -2.594 .. 9.313 | body sunk below its own feet |

Chosen: **`world @ inv(bindworld)`**, column-vector FK, with `model.nusktb`'s row-vector
bind matrices transposed on the way in. This is the same convention
`build_robot_dtilt.py` already uses for its `world_pose`.

### 2.2 The model origin is the ground plane

At the built idle frame 0 the root bone `Trans` sits at world `(0, 0, 0)` and `Rot` at
`(0, 6.194, 0)`. The visible body mesh's lowest vertex is at **y = -0.081**, i.e. the model's
own origin plane *is* the fighter's ground contact. `TopHave` is a second root bone at
`(0, 0, 0)` with identity transform. So a bone's world y is a height above the fighter's
feet, in model units, without any further conversion.

### 2.3 Relation between ATTACK coordinates and model space

**`Hash40::new("top")` does not name a bone on this recipient.** The 165-bone skeleton has
`TopHave`, not `top`; this was already recorded for the Monkey Flip catch box in
`tools/dump_gw_bones.py` and re-confirmed here by listing all 165 names. The generated G&W
scripts in `generated/ground.rs` use `Hash40::new("top")` on every hitbox, including G&W's
own moves, and those work on hardware, which establishes that **`top` is a part label, not a
joint attachment**: the engine falls back to the character's own origin frame.

Direct calibration against G&W's own jab is available and was run
(`builds/pgwr/0.20.16`, vanilla clip, frame 4, where `game_attack11` is live):

| quantity | value |
| --- | --- |
| hitbox sphere (id 1) | centre `(0, 5.2, 13.0)`, r 4.3 |
| `HandR` bone at that frame | `(-0.996, 4.768, 4.237)` at idle, moved to `z = 8.09` in the jab |
| visible fist mesh nearest vertex to the sphere centre | distance **6.236** |
| fist mesh fraction inside r 4.3 | **0.0** |
| same for the id-0 spray sphere `(0, 5.0, 6.0)` r 3.8 | **0.0** |

So G&W's own fist mesh does **not** sit inside G&W's own jab sphere when both are read in
naive model units: the mesh is ~6.2 units from a centre that is only 4.3 in radius. The
same holds for G&W's own down tilt (fist ~4.15 from a capsule axis of radius 1.2).

**Conclusion (tier B, measured; the interpretation is tier D):** ATTACK x/y/z are expressed
in the same *model-unit* space as the skeleton, but the capsule/sphere centre is offset from
the fighter's origin by a **per-attack anchor offset** that is not the bone origin, and the
radius is not a visual-contact radius either. Practically: **a hitbox coordinate is a point
in the same frame as the mesh, but equality between a bone position and a hitbox coordinate
does not hold.** Every alignment target in section 4 is therefore derived against the
capsule *axis and radius* (what the engine actually collides against), never by matching a
coordinate to a bone position. This is the same reason `tools/fair_sword_geometry.py` has
to assume the `top` anchor resolves to the origin, and its numbers are labelled as measuring
the model, not the game.

### 2.4 Joint-only evidence has a hard limit

Everything above is joint/mesh geometry. It **cannot** establish where the engine places a
hitbox in world space, because that placement is decided by `main` and by the character's
collision root, neither of which is measurable from these files. The measurable statement is
narrower and is the one the recipe should rely on: *given* that the capsule occupies the
model frame around `(0, 1.7, 21)`-`(0, 7, 9)` with r 3.4, which pose puts visible geometry
inside it. Whether the game actually evaluates that capsule there is tier A and only a
console run answers it.

## 3. Standing G&W body-height reference

Skinned visible geometry at the built idle frame 0:

| measurement | value (model units) |
| --- | --- |
| ground (lowest `gw` body vertex) | **y = -0.0811** |
| crown (highest `headm` vertex) | **y = 12.7522** |
| **body height H** | **12.8334** |
| hip bone | y = 4.6937 |
| head bone | y = 8.2543 |

**Convention adopted for this task:** `H = 12.8334` model units, measured crown-to-sole on
the *skinned visible mesh*, not bone-to-bone. Bone-to-bone would give a different and less
useful number (root-to-head-bone is 8.25), which is why the convention is stated rather than
left implicit. `H` is used for every "roughly full body height" statement below.

Visible-region extents at idle (skinned):

| region | x | y | z |
| --- | --- | --- | --- |
| body (`gw`, 4 submeshes) | 5.761 | 8.305 | 8.357 |
| head (`headm`, 4) | 5.339 | 5.436 | 5.352 |
| right fist (`rhandhold`, 4) | 2.417 | 3.942 | 4.924 |
| left fist (`lhandhold`, 4) | 2.758 | 3.555 | 4.883 |
| nose (`nosem`, 8) | 2.963 | 2.505 | 1.846 |

Only five visibility nodes are enabled at idle: `gw`, `headm`, `nosem`, `lhandhold`,
`rhandhold`. Every other one of the 98 nodes is explicitly False, so the fist meshes really
are the visible hands and there is no second body mesh to worry about.

## 4. Limb axes, lengths and the frame-3 target

### 4.1 Arm geometry at idle (measured)

| | left | right |
| --- | --- | --- |
| shoulder | `(0.2694, 7.1635, -0.0904)` | `(-0.3272, 6.9345, 0.9856)` |
| elbow (`Arm*`) | `(1.1609, 7.0789, -1.8055)` | `(-0.9953, 5.3545, 1.8798)` |
| hand (`Hand*`) | `(1.3833, 5.1990, -3.3283)` | `(-0.9963, 4.7679, 4.2371)` |
| upper-arm length | 1.9348 | 1.9345 |
| forearm length | 2.4295 | 2.4292 |
| **shoulder→hand** | **3.9477** | **3.9641** |
| **as a fraction of H** | **0.3076** | **0.3089** |

So a whole arm is **~0.31 body heights**. Reaching the capsule's forward sphere
(`z = 21.0`) needs a shoulder→hand distance of **20.69 (R) / 21.79 (L)** from the idle
shoulder, i.e. a **5.22x / 5.52x** stretch. This is the single most important number in the
record: *the requested reach is not reachable by posing.* It requires actual deformation.

### 4.2 Hitbox capsule (from `robot_attack_lw3.rs`, `game_attacklw3` frame 3)

radius 3.4, endpoints `(0, 1.7, 21.0)` and `(0, 7.0, 9.0)`, active frame 3, cleared frame 4,
cancel 15.

| property | value |
| --- | --- |
| axis length | 13.1183 = **1.022 H** |
| axis direction | `(0, 0.404, -0.915)` - up and back |
| forward-most point of the whole capsule | **z = 24.4** |
| lowest point of the capsule | y = -1.7 (i.e. below the ground plane) |
| capsule mid-point | `(0, 4.35, 15.0)` |

The capsule is longer than the body is tall and it starts *below* the feet. It is a long
low forward sweep, not a point punch.

### 4.3 The staged frame-3 pose versus the capsule

From `builds/pgwr/0.20.16+robot-dtilt.4`'s clip at frame 3, current T-0036 result:

| | left | right |
| --- | --- | --- |
| shoulder | `(0.269, 5.053, 2.460)` | `(-0.327, 4.210, 3.167)` |
| elbow | `(-0.731, 3.401, 2.563)` | `(-0.640, 3.410, 4.900)` |
| hand | `(1.383, 4.199, 1.672)` | `(-0.996, 3.968, 7.237)` |
| shoulder→hand | 1.61 | 4.13 |
| hand distance to capsule axis | **7.966** | **3.646** |
| fist farthest point to capsule axis | **6.804** | **3.189** |
| fist inside r 3.4? | no | **yes** |

The right fist is already just inside the capsule at frame 3. The left fist is 6.8 units
short. Note also the left arm is *folded* (shoulder→hand only 1.61 of its 3.95 possible) -
the recipe's left wrist goal pulls it across the body.

### 4.4 Recommended frame-3 targets

Target: both fists inside the capsule, arm extended forward near the ground, peak at frame 3,
and both arms reaching roughly one body height further forward than at idle.

Using the aim-then-slide construction of section 5 with the aim direction `+Z`
(`(0, 0, 1)`) and a shoulder slide along `+Z`:

| target | left | right |
| --- | --- | --- |
| idle fist max z | 0.389 | 5.368 |
| frame-3 fist max z before | 5.239 | 8.472 |
| **target fist max z (= idle + H)** | **13.223** | **18.201** |
| **required shoulder slide along +Z** | **7.98** (0.62 H) | **9.73** (0.76 H) |
| resulting shoulder | `(0.269, 5.053, 10.44)` | `(-0.327, 4.210, 12.90)` |
| resulting hand | `(0.269, 5.053, 12.05)` | `(-0.327, 4.210, 14.03)` |
| shoulder→hand | 1.61 | 4.13 |

The fist ends up at `z = 13.2` (L) and `z = 18.2` (R), against a capsule whose forward sphere
reaches `z = 24.4` and whose near end is `z = 21.0`. **The right fist lands inside the
capsule's forward sphere; the left lands in the capsule's mid-body.** Both are inside the
collision volume, and neither overshoots past `z = 24.4`.

## 5. Chosen deformation method

### 5.1 Mesh weighting decides which bone to move

Measured max vertex weights on the two visible arm meshes:

| mesh | influences (max weight) |
| --- | --- |
| `RhandHold_VIS_O_OBJ_O_NOSORT_AS_OPAQUEShape` | `ArmR` 1.0, `ShoulderR` 1.0, `H_ArmR` 0.495 |
| `LhandHold_VIS_O_OBJ_O_NOSORT_AS_OPAQUEShape` | `ArmL` 1.0, `ShoulderL` 1.0, `H_ArmL` 0.495 |

**`Hand{L,R}` has weight 0 on the visible fists.** This is the decisive measurement: the
hand bone is *not* what carries the visible hand, so "move the hand bone forward" does
nothing on screen. Verified directly - translating `HandR` by `(0,0,4)` moves the fist mesh
by a maximum of **0.001** units.

Three candidate levers were measured on the right fist at frame 3:

| method | fist z-extent before → after | max vertex move | verdict |
| --- | --- | --- | --- |
| translate `HandR` +4z | 5.751 → 5.751 | 0.001 | **moves nothing visible** |
| translate `ArmR` +4z | 5.751 → 4.185 | 4.000 | **shears** (extent shrinks) - the mesh is skinned to Arm *and* Shoulder, so moving one slides vertices relative to each other |
| scale `ArmR` 2.0 on its own bind axis | 5.751 → **10.126** | 5.006 | lengthens the arm **and the fist** - y-extent 2.42 → 4.02, so the hand visibly fattens |
| scale `ArmR` 1.5 on its axis | 5.751 → 7.913 | 2.503 | same problem, half as bad |
| **rotate + translate `ShoulderR`** (the set's root) | 5.751 → 5.751 | exact | **rigid: size preserved, no shear** |

Because `ArmR` and `H_ArmR` are both children of `ShoulderR`, rotating and translating
`ShoulderR` alone carries the entire visible arm block rigidly. Fist extent is preserved to
1e-3 at every slide value tested, and the torso's own vertices move **0.000** (the `gw` mesh
is not skinned to any arm bone).

### 5.2 Chosen method

**Per-arm: rotate the `Shoulder{L,R}` bone so the arm block points along a recipe-supplied
aim direction, then translate `Shoulder{L,R}` along +Z by the recipe's slide amount.
No bone scale anywhere. No mesh, material or skeleton edit. `Hand{L,R}` untouched.**

This satisfies the "without enlarging hands/body or distorting unrelated bones" requirement
by construction: rigid motion preserves the fist's size exactly (measured), and the torso,
legs, head and props are untouched (measured, 0.000 vertex movement).

Cost, measured across the aim/slide grid:

| shoulder slide (R) | arm↔torso min distance | still attached? | fist inside r 3.4? |
| --- | --- | --- | --- |
| 0.0 | 0.137 | yes | yes |
| 1.0 | 0.175 | yes | yes |
| 2.0 | 1.036 | no | yes |
| 3.0 | 1.854 | no | yes |
| 4.0 | 2.750 | no | yes |

The arm block separates from the torso above ~1.5 units of slide. At the recommended 9.73
slide the arm is fully detached and floating forward of the body - which is precisely what a
"stretched arm thrust" should look like, but it is a visible gap and the user must judge it.

### 5.3 Why not scale

Arm-axis scaling was measured and rejected on the numbers: it is the only lever that reaches
far without detaching, but at the 1.4x needed to bring the right fist to the capsule edge it
already grows the fist's cross-section by 8% in x and 16% in y, and at 2.0x by 22% / 66%. The
task requires no hand enlargement, so the shoulder-slide route is chosen and the detachment
cost is disclosed instead of hidden.

### 5.4 Peak and recovery

Recipe keys at frame 3 carry the peak; the existing smoothstep interpolation between keys
already returns both arms to idle by cancel frame 15, and the clip ends at 28. Recommended
key values to add to `recipe.json` v3.0.0 (per arm, as `[dx, dy, dz]`):

| frame | aim direction | slide | weight |
| --- | --- | --- | --- |
| 0 | identity | 0.0 | 0.0 |
| 1 | interpolate | 0.25 × peak | 0.35 |
| 2 | interpolate | 0.75 × peak | 0.8 |
| **3** | `(0, 0, 1)` | **L 7.98 / R 9.73** | **1.0** |
| 4 | interpolate | 0.95 × peak | 1.0 |
| 6 | interpolate | 0.55 × peak | 0.8 |
| 8 | interpolate | 0.25 × peak | 0.5 |
| 12 | interpolate | 0.05 × peak | 0.2 |
| 15 | identity | 0.0 | 0.0 |
| 28 | identity | 0.0 | 0.0 |

The existing `weight` channel already lerps every bone toward idle, so the slide and aim
must be applied *before* that lerp in `solve_limb`'s output, exactly as `hip`/`lean_deg` are.
No change to the cancel frame (15), the clip end (28), the active/clear frames (3/4), the
hitbox, the effects, the sounds or the rumble is required or proposed.

## 6. Acceptable alignment tolerance

| quantity | tolerance | why |
| --- | --- | --- |
| fist → capsule axis distance | **≤ 3.4 (the radius)** is a pass; **≤ 2.0** is comfortable | this is the collision volume itself |
| arm↔torso detachment | ≤ 1.5 units still reads as attached; 1.5-3.0 reads as a stretch; > 3.0 looks detached | measured gap column above |
| fist cross-section growth | **≤ 1.02** | the requirement is "no enlarged hands"; 1.02 is the noise floor of the measurement |
| torso vertex movement | must be **0.000** | any non-zero means an unrelated bone was touched |
| frame-3 peak timing | hitbox active frame 3, cleared frame 4 - the pose peak must be frame 3 | already fixed by the ACMD |
| recovery | both arms back at idle by cancel 15 | existing recipe contract |

## 7. Deformation risks

1. **Arm detachment.** Unavoidable with this method at the required reach. Measured gap at
   the recommended slide is well past 3.0. Highest-risk visual outcome; needs a human eye.
2. **Shear if `Arm{L,R}` is moved alone.** Measured: translating `ArmR` shrank the fist's
   z-extent 5.751 → 4.185. If an implementer moves the arm bone instead of the shoulder,
   the fist visibly squashes. This is the most likely implementation mistake.
3. **Scaling the arm fattens the hand.** Measured cross-section growth is 8%/16% at 1.4x
   and 22%/66% at 2.0x. Explicitly out of bounds.
4. **The `Hand{L,R}` trap.** Moving the hand bone is a no-op on screen (0.001). A recipe
   written in terms of "hand position" targets will appear to do nothing.
5. **`H_Arm{L,R}` at weight 0.495.** These helper bones are half-weighted into the fists and
   are children of `Shoulder{L,R}`, so the shoulder route handles them correctly. An
   implementer who edits them would get a partial, asymmetric result.
6. **Both arms share `ClavicleC` via `Bust`.** The existing `lean_deg` already rotates
   `Waist`/`Bust`; the shoulder slide is applied in the shoulder's *parent* frame, so it does
   not compound with the lean. Changing this order would silently scale the slide.
7. **Left arm starts folded** (shoulder→hand 1.61 of 3.95 at frame 3). The aim rotation
   unfolds it, which is correct, but it changes the left arm's silhouette a lot more than the
   right's. Asymmetry in the result is expected, not a bug.

## 8. Implementation recipe (for T-0051, which owns the builder and recipe)

`src/pgwr/tools/build_robot_dtilt.py`, in `retarget()`, inside the per-frame loop, after the
existing `solve_limb` calls for the arms and before the `weight` lerp:

1. Read two new per-arm recipe fields: `aim` (a unit direction, default `(0, 0, 1)`) and
   `slide` (a scalar along that direction's +Z, default 0.0).
2. For each arm, with `si = ids[f'Shoulder{sfx}']` and `hi = ids[f'Hand{sfx}']`:
   - `parent = bones[si].parent_index`
   - rotate: `local[si][:3,:3] = world[parent][:3,:3].T @ turn(world[hi][:3,3] - world[si][:3,3], aim) @ world[si][:3,:3]`
   - translate: `local[si][:3,3] += world[parent][:3,:3].T @ (aim * slide)`
   - recompute `world` between the two steps.
3. Do **not** touch `Arm{L,R}`, `Hand{L,R}`, `H_Arm{L,R}` translations, and do **not** write
   a non-unit scale. `Transform([1,1,1], ...)` in the existing emit path already guarantees
   this; leave it.
4. The existing `weight` lerp then carries the slide back to zero by cancel 15 unchanged.

`turn()` already exists in the builder and handles the 180-degree case. `solve_limb` and the
weight lerp need no modification.

## 9. Optional Diddy reference

`refs/diddy_monkey_flip/` contains Diddy's Monkey Flip material (NRO decompilation, ACMD,
motion list) but **no `c02attacklw3` clip and no Diddy skeleton**. `dumps/arc` is absent, so
no Diddy down-tilt input exists locally and none was fetched (no authorized network pull in
this task). **The optional Diddy reference is unavailable and did not block this work**; the
recipient's own G&W geometry and its own scripts supplied the calibration instead, which is
the stronger source anyway since it is the rig actually being deformed.

If a Diddy comparison is wanted later, `tools/fetch_arc_files.py --set <name>` would need a
new set entry for `diddy/motion/body/c00/c02attacklw3.nuanmb`; that is a separate,
user-authorized step.

## 10. Read-only commands and how to reproduce

All from the mod root (`mods/ssbu_mod_new`), CPython 3.12.3, `ssbh_data_py` 0.9.1,
`numpy` 2.2.2. Nothing writes into the mod tree.

```bash
# the promoted tool: body height, limb geometry, mesh weights, clip pose
python -B tools/measure_recipient_pose.py \
  --package builds/pgwr/0.20.16+robot-dtilt.4 --slot c06 \
  --clip c02attacklw3.nuanmb --frame 3 --json /tmp/pose.json

# hashes of every input this record used
python - <<'PY'
import hashlib, pathlib
for rel in ['fighter/eflame/model/body/c06/model.nusktb',
            'fighter/eflame/model/body/c06/model.numshb',
            'fighter/eflame/model/body/c06/model.numdlb',
            'fighter/eflame/motion/body/c06/a00wait1.nuanmb',
            'fighter/eflame/motion/body/c06/c02attacklw3.nuanmb']:
    p = pathlib.Path('builds/pgwr/0.20.16+robot-dtilt.4/ultimate/mods/pyra_gamewatch_reskin')/rel
    print(hashlib.sha256(p.read_bytes()).hexdigest(), rel)
PY

# `top` is not a bone: the 165 recipient bone names
python - <<'PY'
import ssbh_data_py as s
sk = s.skel_data.read_skel('builds/pgwr/0.20.16+robot-dtilt.4/ultimate/mods/pyra_gamewatch_reskin/fighter/eflame/model/body/c06/model.nusktb')
names = [b.name for b in sk.bones]
print(len(names), 'top' in names, 'TopHave' in names)
PY
```

The aim/slide grids in sections 4.4 and 5.2 came from scratch scripts under
`state/scratch/T-0047/` (`aim_forward.py`, `final_tradeoff.py`, `deform_risk.py`,
`shoulder_slide.py`, `vanilla_control.py`, `calibrate_units.py`). The one number a reader
will want to re-derive independently is the mesh weighting in 5.1, because the whole method
selection rests on `Hand{L,R}` having zero weight; `tools/measure_recipient_pose.py` prints it
under `visible_arm_mesh_weights`.

## 11. What remains unverified

Everything about **behaviour**. Specifically unverified:

- that the engine places the `top` capsule where section 2.3 assumes (tier A needed);
- that any of this looks right on screen - the frame-3 pose was never rendered as a mesh
  image, only measured numerically;
- the detached-arm appearance at the recommended slide;
- whether the aim rotation reads as an arm thrust or as a broken shoulder;
- that c07 behaves identically (files are byte-identical for every input used, so it should,
  but it was not measured separately);
- no automated test, no Ryujinx run, no console run, no card access.

The joint/mesh evidence supports the *method selection* strongly (the weighting measurement
is unambiguous and the three levers were separated experimentally). It does not and cannot
support any claim about what the player sees.