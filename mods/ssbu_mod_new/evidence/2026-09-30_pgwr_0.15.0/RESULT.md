# 2026-09-30 pgwr 0.15.0 - console result

Installed 2026-09-30 00:41; report from the user the same session. Record:
`evidence/install-record-2026-09-30_0041.json`, manifest `builds/pgwr/0.15.0/MANIFEST.json`.

Card: NRO `b924fd0f…`, 1259 mod files, `libone_slot_eff` `e6e5659d…`, smashline `5f4091ee…` (untouched).
This install deliberately carried two sessions' work at once (the fair sword fix + the Monkey Flip port), so it
was never going to be clean attribution. Verdicts below are per-feature because the two failed and passed
independently.

## What the user did and saw

> "so all the side b changes work exactly as intended, the fair seems exactly like in the previous build,
> sword always visible and wrong angle, probably also too small"

## Verdict

| Feature | Verdict |
| --- | --- |
| Side-B Monkey Flip (leap, kick, leap/landing, donor behaviour) | **PASS - first hardware confirmation of the 0.15.0 port** |
| Fair sword fix (grip angle, hiding outside the fair, size) | **FAIL - no observable change; all three faults unchanged** |
| Fair sword size | unchanged by design (R-19); the user still reads it as too small, so the *perception* is unresolved |

The log was not supplied. `sd:/ultimate/pgwr_log.txt` from boot is still wanted, mainly to confirm the
`[PGWR-MFLIP]` phase trace behind the pass and to check no crash-report covers this run.

## Why the sword fix did nothing

Both shipped mechanisms were verified present on the card and are inert:

1. `build.py::hide_esword()` scales the esword skeleton's `Root` basis by 1e-3. Read back off the card:
   `Root` scale `(0.001, 0.001, 0.001)`, every other bone identity. **No observable effect.**
2. The body fair clip carries a `Sword1` track (37 transform nodes; 0.14.1 had 36). **No observable effect**
   on the blade's angle.

Offline structure that explains both (tier B, `dumps/arc/fighter/eflame`):

- The esword article has its **own motion list and eight clips** -
  `fighter/eflame/motion/esword/c06/{z00open, z00close, z00toopen, z00toclose, d01specials1, d01specials2,
  d01specialsmovel, d01specialsmover}.nuanmb` plus `motion_list.bin` and `update.prc`. The mod ships **none**
  of them, so the article plays vanilla Pyra poses.
- **All eight clips animate `HaveR`, `Sword1` and `Sword_flameA..E`. None animates `Root`.** So the sword's
  pose relative to the hand is *entirely* the article's own animation, and `Root` is the only bone whose bind
  pose could still apply.
- The vanilla esword skeleton is **all-identity** on all eight bones (`Root > HaveR > Sword1 > Sword_flameA..E`),
  so the blade's placement comes from animation, not from bind geometry.
- Consequence 1: a track on the grafted **body** bone `Sword1` cannot re-angle the blade - the article is posed
  by its own clips, not by that bone. That kills the `build_cloud_fair` approach as shipped.
- Consequence 2: scaling `Root` in the bind pose has no visible effect, which is the one bone left. The
  precise mechanism (the engine not applying the root joint's bind scale to an article) is **D**; that the
  shipped 1e-3 changed nothing on screen is **A**.

## Not a regression

`hide_esword()` copies the **vanilla** esword directory, so it replaced the file 0.14.1 shipped
(`874f68eb…`) rather than extending it. Checked: 0.14.1's skeleton is semantically identical to vanilla - all
eight bones identity, same parents, same names - so the byte difference is just a `ssbh_data_py` re-save.
Nothing semantic was thrown away.

## The lever that is left

The article's own clips are the only thing that poses *or* sizes the sword, and they are **per costume**
(`fighter/eflame/motion/esword/c06|c07`), so overriding them touches c06/c07 and leaves vanilla Pyra c00-c05
alone. That makes one file group solve both halves of the original complaint:

- **Hiding:** scale `Sword1` (or `HaveR`) toward zero in the clips that pose the resting/open sword. This is
  what the retired `hide_esword()` collapse was reaching for, and unlike `Root` it is a bone the clips
  actually animate, so it wins.
- **The fair:** one clip holding the blade along Cloud's swing at native size, selected by the motion-part call
  the fair ACMD already makes (`WEAPON_EFLAME_ESWORD_MOTION_PART_SET_KIND_OPEM_CLOSE`). Selecting a motion
  part once at the clip's start is a state change, not a per-frame force, so rule 19 is satisfied.

Open before building: which clip the article plays when nothing sets a part (its `motion_list.bin` default),
and whether the motion "parts" map 1:1 onto those eight clip names the way `OPEM_CLOSE` implies.

**Not built.** Another session was actively working in the tree at the time of writing, so nothing was
rebuilt or reinstalled after this report, and the handbook/graveyard updates below are deliberately still
pending.

## Handbook / graveyard edits - APPLIED 2026-09-30 01:25

(The tree went quiet and the user cleared a build+install, so these are no longer pending; kept
here so the reasoning is in one place. What was written:)

- `handbook/graveyard.md`: **R-20** (the model `Root` scale) and **R-21** (the body-clip `Sword1`
  track), both **X on hardware**, plus a caveat on R-19 saying its numbers came from the tool whose
  blade model R-21 refutes.
- `handbook/08_visibility_models.md`: the Aegis-sword entry rewritten around the article's own clip
  visibility, and the old rigid-attachment entry replaced with "an article is posed by its own clips".
- `tools/fair_sword_geometry.py`: docstring now opens with STALE MODEL and says its numbers measure
  the model, not the game.
- `projects/pgwr/STATUS.md`: card state, the fair and Monkey Flip feature-matrix rows (Monkey Flip now
  hardware-verified), and the workaround table.
- `projects/pgwr/CHANGELOG.md`: the sword fix under 0.15.1.

The fix itself is `tools/build_esword_pose.py`, built and installed as 0.15.1;
see `evidence/install-record-2026-09-30_0123.json`.

## Original note (superseded)

## Pending handbook / graveyard edits (not yet applied - shared files, other session active)

- `handbook/graveyard.md`, new rows:
  - **R-20** | "Scaling the esword skeleton's `Root` basis in the model hides the Aegis sword" | `build.py::hide_esword()` 0.15.0 | **X on hardware** (this run). Root is the only esword bone no article clip animates, and scaling it had no visible effect. The article's own clips are the lever.
  - **R-21** | "A body clip's `Sword1` track re-poses the attached esword article" | `build_cloud_fair.sword_node()` 0.15.0 | **X on hardware** (this run: angle unchanged). The article's pose comes from `fighter/eflame/motion/esword/c06/*`, which animate `HaveR`/`Sword1`/`Sword_flame*`, not from the grafted body bone.
- `handbook/08_visibility_models.md`: the Aegis-sword entry currently describes the model-scale + fair-clip-track design as the working lever; it needs the R-20/R-21 correction and the "the article's own clips own its pose" fact.
- `handbook/07_articles.md`: worth adding that an article's pose and size come from its **own** per-costume motion folder, so a body clip can only move the hand, never the article.
- `projects/pgwr/STATUS.md`: feature matrix rows for Monkey Flip (upgrade to verified) and fair (still failing, new cause), and the workaround table entry for `hide_esword()`.
