# measure_recipient_pose.py

Read-only geometry measurement for a built pgwr recipient. Answers the questions an
animation recipe needs **before** it is authored, so pose targets come from the recipient's
own numbers instead of guesses.

## What it measures

- **Body height `H`** in model units: skinned visible mesh at idle frame 0, ground to crown.
  Reported with its convention explicitly, because a bone-to-bone measurement gives a
  different and less useful number.
- **Limb geometry** per side: shoulder / elbow / hand world positions, upper-arm and forearm
  lengths, shoulder-to-hand, and the arm length expressed as a fraction of `H`.
- **Which bones actually drive a visible mesh** (`visible_arm_mesh_weights`): max vertex
  weight per influencing bone, restricted to the arm-related bones. This is the measurement
  that decides which bone an animation must move - a bone with weight 0 on the visible mesh
  is a no-op on screen no matter how far you translate it.
- **Non-unit world scales**, to answer whether animation-scale compensation is needed.
- Optionally, the world position of named bones in any clip at any frame (`--clip`,
  `--frame`), plus that clip's hash and end frame.

## Conventions it applies (and why they matter)

- SSBH local bind matrices are row-vector; they are transposed for column-vector FK.
- Animated `xyzw` quaternions become column-vector rotation matrices directly.
- Skinning is `sum(w * world_i @ inv(bindworld_i)) * v`.

The skinning form is the one that matters. Two plausible alternatives
(`world @ inv(bindlocal)` and `inv(bindworld) @ world`) produce bodies whose heads float
above their own shoulders or whose feet sit below the ground plane, so a wrong choice is
visible immediately in the measured extents rather than silently biasing every downstream
number. `model.numshb` stores per-vertex `BoneInfluence` entries carrying a bone *name* and
per-vertex weights, which is what this reads.

## Usage

```bash
toolchains\py312\python.exe tools\measure_recipient_pose.py \
    --package builds/pgwr/0.20.16+robot-dtilt.4 \
    --slot c06 \
    --clip c02attacklw3.nuanmb --frame 3 \
    --json evidence/pose.json
```

Requires `ssbh_data_py` and `numpy` and a complete built package. Writes nothing except the
`--json` file you name. Never runs a test, never compiles, never touches the SD card.

Defaults: `--package builds/pgwr/0.20.16`, `--slot c06`, no clip.

## Smoke test

The tool is its own smoke test - it is read-only and asserts nothing about game behaviour,
so a successful run on any built package is the check. Verified 2026-10-02 against
`builds/pgwr/0.20.16+robot-dtilt.4` slot `c06`:

- 165 bones; skeleton `02ed7ba1...`, idle `bbb8e203...`, numshb `181f4a88...`
- body height 12.8334 model units (ground y -0.0811, crown y 12.7522)
- shoulder-to-hand 3.9477 (L) / 3.9641 (R) = 0.3076 / 0.3089 of body height
- non-unit world scales: none
- `RhandHold` skinned to `ArmR` 1.0, `ShoulderR` 1.0, `H_ArmR` 0.495, **`HandR` absent**

That last line is the reason this tool exists: `HandL`/`HandR` carry no visible geometry on
this recipient, so a recipe written in terms of hand position would move nothing on screen.

## Notes and limits

- Mesh bounding spheres in `model.numdlb` are **not** used for extents; they are per-mesh
  authoring bounds and do not reflect the skinned pose. Everything here is skinned.
- Only meshes whose visibility track is enabled are counted toward body height, so props and
  the manhole/hammers cannot silently inflate `H`.
- It measures the **model**. It cannot say where the engine places a hitbox, or what the
  player sees; those need a console run.

Provenance: promoted from T-0047 scratch work (2026-10-02), which measured the robot
down-tilt's stretch target. Design record:
`evidence/2026-10-02_pgwr_T-0045/T-0047_design_record.md`.