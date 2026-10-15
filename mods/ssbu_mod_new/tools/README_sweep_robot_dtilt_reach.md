# sweep_robot_dtilt_reach.py

Chooses (or re-checks) the R.O.B. down-tilt recipe's `arm_reach` by **measuring** what each
candidate reach actually does against the donor hitbox, instead of guessing.

`arm_reach` in `src/pgwr/assets/robot_dtilt/recipe.json` is in standing body heights and is
the target projection of the hand along the recipe's aim direction, measured from the fighter's
origin. A recipient arm is only ~0.31 body heights long, so every candidate reaches far past
what posing alone can do, and the useful question is not "is the pose right" but "where do the
hands end up relative to the capsule". That is what this prints.

## Usage

```bash
python -B tools/sweep_robot_dtilt_reach.py
python -B tools/sweep_robot_dtilt_reach.py \
    --package builds/pgwr/0.20.16+robot-dtilt.5 --slot c06 --reach 1.0 1.2 1.4
```

Defaults: `--package builds/pgwr/0.20.16+robot-dtilt.4`, `--slot c06`,
`--out state/scratch/robot_dtilt_reach`, and a default candidate list around the shipped
value. Requires `ssbh_data_py`, `numpy` and `Pillow` (Pillow only if you also render a
preview; the sweep itself does not need it) plus a complete built package.

## What it prints

One row per candidate:

- `hand z/y` - the hand bone's world position at frame 3.
- `extH` - the hand's forward displacement from its **own idle** position, in body heights.
  Left and right differ because the arms start in different places; that asymmetry is expected,
  not a bug, and is the reason the recipe anchors to the origin instead.
- `gap` - signed distance from the hand bone to the capsule **surface**; negative means inside.
- `inside` - whether both hands are inside.

The capsule is parsed out of `src/pgwr/plugin/src/acmd/robot_attack_lw3.rs` at run time by
`build_robot_dtilt.active_hitbox()`, so it is the real one, never a copy. JSON output
(`reach_sweep.json`) also records that file's hash.

## Safety and limits

- Writes only its own output directory. It **edits the recipe to test each candidate and
  restores it byte-for-byte in a `finally` block**, so a crash mid-run cannot leave a swept
  recipe behind. Verify with `git diff src/pgwr/assets/robot_dtilt/recipe.json` if unsure.
- Authors each candidate through the real `retarget()` path, so the numbers are the numbers
  the staged generator produces.
- Never writes into `builds/pgwr/`, never compiles Rust, never touches the SD card, runs no
  test and boots no emulator.
- It measures the **model** against the **capsule the ACMD asks for**. It cannot say where the
  engine places that hitbox in world space, and it says nothing about how the pose looks.
  Both remain tier D; only a console run answers them.

## Smoke test

Verified 2026-10-02 against `builds/pgwr/0.20.16+robot-dtilt.4` slot `c06`, which reproduced
the reach table recorded in
`kb/findings/reach-beyond-limb-length-is-not-an-ik-problem.md`: at `reach` 1.20 the hands land
at z 16.115 / 15.990 with surface gaps -2.21 / -1.53 (both inside), and at 1.45 they reach
z 19.3, crowding the capsule's forward tip at z 24.4. A successful run on any built package,
with the recipe unchanged afterwards, is the check.

Provenance: promoted from T-0048 scratch work (2026-10-02), which chose the shipped
`arm_reach`. Design record:
`evidence/2026-10-02_pgwr_T-0045/T-0047_design_record.md`; implementation record:
`evidence/2026-10-02_pgwr_T-0045/T-0048_animation_record.md`.