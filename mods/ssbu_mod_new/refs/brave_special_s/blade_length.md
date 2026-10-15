# Mythra's esword blade length, and the side-B trail tip

Measured 2026-09-30 by Buffy. **Tier B** for every number: measured offline by named scripts
on named files with recorded sha256. **Tier D** for anything about what the console shows.

**Nothing here is a hardware result.** Per `handbook/graveyard.md` R-21, the predecessor of
this measurement (`tools/fair_sword_geometry.py`) was refuted on the console on 2026-09-30,
and its own docstring now says its numbers measure the model, not the game. R-19 records a
second offline result that the console contradicted. Two for two.

## The number

| | value |
| --- | --- |
| **Mythra esword blade reach, c06** | **10.8739** |
| **Mythra esword blade reach, c07** | **10.8739** (identical) |
| blade span along its own axis | 13.1508 |
| Hero's blade reach, same metric, c00 | 12.0593 |
| reach ratio Mythra / Hero | **0.9017** |
| Mythra's own vanilla trail tip (`Attack12`) | 14.5 |
| Hero's own vanilla trail tip (`SpecialS1`) | 14.0 |

c06 and c07 are **byte-identical** esword models
(`model.nusktb` `3eba84dcf078336d…`, `model.numshb` `9a09d7db0f180e64…` for both slots), so
there is one blade length, not two. There is no per-costume correction to make.

## Recommended value

```
SIDE_B_TRAIL_TIP: f32 = 14.5;              // Mythra's own Attack12 value, unscaled
```

Expressed the way `chrom_jab.rs` expresses `JAB_TRAIL_TIP`, as a derived multiple rather
than a magic number, the form is:

```
/// Mythra's own `Attack12` trail tip, scaled by this move's blade factor.
const SIDE_B_TRAIL_TIP: f32 = 14.5 * SIDE_B_SIZE_FACTOR;
```

**`SIDE_B_SIZE_FACTOR = 1.0`** - and that is the whole point of the measurement. The user
decided Mythra keeps her own sword, drawn at her own vanilla size, so unlike the jab there
is no size factor to divide by: `JAB_SIZE_FACTOR` is 0.9 because the jab shrinks the blade,
and side-B does not. The derivation is the same shape as the jab's and lands on
`chrom_jab`'s existing base number rather than on a fresh literal.

The alternative — proportionally rescaling **Hero's** 14.0 by the measured blade ratio —
gives **14.0 × 0.9017 = 12.624**. It is recorded here and **not recommended**, for the reason
in the calibration section below.

### How the Rust and Python sides cross-check

Mirror `JAB_SIZE_FACTOR`, which is already guarded by `build_esword_pose.py:417` asserting
that the Python and Rust constants agree on every build. The Python side reads:

```
BLADE_REACH_MYTHRA = 10.8739   # scratch/2026-09-30_buffy/blade_final.py, esword mesh
```

and the Rust side declares `const SIDE_B_SIZE_FACTOR: f32 = 1.0;`, with a build-time
assertion that the Python blade-reach constant still hashes to the expected value. If a
future article re-export changes the mesh, the Python number moves, the assert fires, and
the trail tip is revisited instead of silently drifting. That is the same guard
`JAB_SIZE_FACTOR` has today, applied to the blade length rather than to a taste value.

## Method

The chain is the one that survives R-20 and R-21, and it is the chain
`tools/fair_sword_geometry.py` already documents:

```
owner HaveR (from the BODY clip)
  x article HaveR   (from the ARTICLE's own clip)
  x article Sword1  (from the ARTICLE's own clip)
    x the blade's own axis, tip at the mesh's own extent
```

No part of the model is "rigidly attached to the body `Sword1` bone" — that assumption is
exactly what R-21 refuted, and this measurement does not make it. The body clip contributes
only the attach pose; the blade's orientation comes from the article's own clip, read out of
`dumps/arc/fighter/elight/motion/esword/<slot>/`.

The metric, so it is reproducible: take every vertex of the `_VIS_` blade mesh
(`lightsword_VIS_O_OBJShape`, four objects, 4046 vertices), transform them into the
article's own `Sword1` space by `inverse(world_Sword1)`, find the blade's principal axis by
power iteration on the vertex covariance, and report the largest coordinate along it
(**reach**) and the full extent along it (**span**). Both are in that bone's own units,
which is the space a trail-tip argument is written in.

Script: `scratch/2026-09-30_buffy/blade_final.py`, run with
`toolchains/py312/python.exe`. Intermediates in `scratch/2026-09-30_buffy/blade_final.json`.
Scratch is disposable (rule 3); promoting this to `tools/` is a follow-up, not done here
because this is a read-only research task.

## Calibration, and why it failed

The obvious validation is to run the identical measurement on Hero — whose blade is in his
**body** model, on the body `Sword1` bone — and check that it reproduces the 14.0 his own
`SpecialS1` passes. **It does not.** The two fighters' own overshoot factors disagree:

| | ACMD trail tip | measured reach | tip / reach |
| --- | --- | --- | --- |
| Hero, `SpecialS1` | 14.0 | 12.0593 | **1.1609** |
| Mythra, `Attack12` | 14.5 | 10.8739 | **1.3335** |

So the trail argument is **not** a fixed multiple of the mesh's blade reach. Something else
sets it — most likely the trail's own start offset, its `-90` roll, the 1.4 width, or the
trail texture's own tiling — none of which is measured here.

The proposed **14.5** comes from Mythra's own dumped `Attack12` trail argument.
This is a provenance-based candidate, tier D for alignment on the port. The cited
0.15.1 sword visibility and 0.17.0 shipment do not establish correct trail alignment;
the prior hardware-validation claim is retracted (graveyard R-HERO-S-4).
The report's failed proportional calibration also leaves **12.624** unvalidated.
The implementation must recheck the full owner/article chain and trail attachment,
then compare against Mythra's stock trail in the console test before claiming alignment.

Note also that `chrom_jab.rs` already scales 14.5 by `JAB_SIZE_FACTOR` = 0.9 and calls the
result correct-in-shape. `JAB_TRAIL_TIP` = 13.05. If the blade shrinks, the ribbon shrinks.
Side-B needs the identical edit with a factor of 1.0, which is why the constant is written
as a product rather than as `14.5`.

## What the measurement does establish

1. The reported geometry ratio is **0.9017** (10.8739 vs 12.0593). This is an
   offline model measurement; it does not establish a proportional trail correction.
2. **c06 and c07 need no separate number** — the esword model files are byte-identical
   across the two slots. Tier B.
3. Hero's **14.0** has no validated geometric transfer rule in this report.
4. **14.5 × 1.0** is the proposed Mythra trail candidate, tier D for port alignment.
   Source provenance is the dumped stock `Attack12` argument; no side-B console
   alignment result is recorded here.

## The article states, for whoever wires the ACMD

`dumps/arc/fighter/elight/motion/esword/c06/` holds eight clips. The article's
`motion_list.bin` has exactly **five** entries: `wait`, `open`, `close`, `to_open`,
`to_close` (kinds recovered by hash40 brute force; the kind names are confirmed because
`build_esword_pose.py` already relies on `close` being entry 0 and on `open`/`to_open`
existing by those names). **The four `d01specials*` clips are not referenced by Mythra's
esword motion list at all.**

That is worth flagging for the port: Mythra already has four side-B-named sword clips
sitting in her esword article folder, unused by her own motion list. Per `AGENTS.md` rule 20
("does the donor's own clip/script already do this?") and the user's no-shortcuts standard,
those are the first thing to try before authoring new article states. Their reach in
`Sword1` space varies a lot over the clip — 9.33 to 11.06 on `d01specials1`, up to 34.10 on
`d01specialsmovel@30` — because `d01specialsmovel`/`mover` swing the whole article far out
(Hero's Monkey Flip poses, which on Mythra c06/c07 are Pyra's side-B). Whether those are the
right poses for *our* side-B is a separate question this task does not answer.

## `swing.prc`: does the per-costume difference matter?

`swing.prc` differs per costume — c00 `28389c7440762c92…`, c06 `8981a9794e2bba1f…`, c07
`747f764d266abcff…` (13585 / 9470 / 11701 bytes; full digests in the hash list below).
Decoded with `src/pgwr/tools/prc.py`, the
top-level array is keyed by hash and holds **64 entries in c00, 44 in c06, 64 in c07**, with
c07 carrying a group of 522 leaf values where c06 has 6.

The dumped trail-tip argument is a literal float: Hero's 14.0 and Mythra's 14.5
appear in `AFTER_IMAGE4_ON_arg29`. No complete trace of the trail path or
`swing.prc` readers was performed. Independence from `swing.prc` remains a tier-D
hypothesis, to be tested with identical port assets/ACMD across c06/c07.

Tier **B** that the trail tip is a literal (read directly out of the dumped ACMD text).
Tier **D** that `swing.prc` cannot influence the ribbon — I did not trace every reader of
the file. If a hardware run shows the ribbon behaving differently on c06 than c07 with
identical ACMD, this is the first file to suspect.

## sha256 of every file read

```
3eba84dcf078336d76c7900b3e819a2e4bad88cb3b4ed7a8c1772efe777efa24  dumps/arc/fighter/elight/model/esword/c06/model.nusktb
3eba84dcf078336d76c7900b3e819a2e4bad88cb3b4ed7a8c1772efe777efa24  dumps/arc/fighter/elight/model/esword/c07/model.nusktb
9a09d7db0f180e646fa624cea28b6d0d17f3f45b3dbd583a363b91a32d77c0ba  dumps/arc/fighter/elight/model/esword/c06/model.numshb
9a09d7db0f180e646fa624cea28b6d0d17f3f45b3dbd583a363b91a32d77c0ba  dumps/arc/fighter/elight/model/esword/c07/model.numshb
1842a984acc4ba8e5cba2c0b25114621f559e8f15f54d289c7f084e6c025ca04  dumps/arc/fighter/brave/model/body/c00/model.nusktb
6000da1734e722106368552f272f0d7f08de3275de372560c99f1825237841eb  dumps/arc/fighter/brave/model/body/c00/model.numshb
4d90678221f999c74f25fc3d5900106ee1d45c21a90a687b3f8a36b32baf96f9  refs/brave_special_s/arc/fighter/brave/motion/body/c06/d01specials1.nuanmb
28389c7440762c92f5741aa0fd4c01be0dde397fc72c3db7bb517055654d55a5  refs/brave_special_s/arc/fighter/brave/motion/body/c00/swing.prc
8981a9794e2bba1f1fa1c78e1d20e7d45e39d60323280b1f48b583aed25aba8c  refs/brave_special_s/arc/fighter/brave/motion/body/c06/swing.prc
747f764d266abcff615c4be494f735eb0aa949f8126da4bee317aa198c4b402a  refs/brave_special_s/arc/fighter/brave/motion/body/c07/swing.prc
```

Body and article clips read (sha256 in `scratch/2026-09-30_buffy/blade_final.json`):
`dumps/arc/fighter/elight/motion/esword/c0{6,7}/{z00toopen,z00open,d01specials1,
d01specials2,d01specialsmovel,d01specialsmover}.nuanmb`,
`dumps/arc/fighter/elight/motion/body/c0{6,7}/c00attack12.nuanmb`,
`dumps/arc/fighter/elight/motion/body/c0{6,7}/motion_list.bin`,
`dumps/arc/fighter/elight/model/body/c0{6,7}/model.nusktb`.

All ten digests above are full-length and were produced by `sha256sum` in this session.
Body and article clip digests, all full-length, are in
`scratch/2026-09-30_buffy/blade_final.json`; the side-B clips listed in
`skeleton_bones.md` section 8 carry the same bytes under c06 and c07.

## What I could NOT establish

1. **Why Mythra passes 14.5 when her blade reach measures 10.8739.** The calibration
   against Hero failed, so the trail argument's true determinant is unknown. Tier **D**.
   Settling it needs the effect system's own reading of `AFTER_IMAGE4_ON_arg29` argument 10
   — i.e. `main.bin`, which is a native-decompilation task, not a dump read.
2. **Whether 14.5 looks right on the side-B clip.** Tier **D**, and unanswerable offline.
   The control is Mythra's own `Attack12` and `AttackS3` trails on the same console session:
   if those render correctly and the side-B trail does not, the difference is in the clip's
   pose or article state, not in the number.
3. **Whether the article's unused `d01specials*` clips are the right poses for our side-B.**
   Tier **D**. Not investigated beyond measuring their reach.
4. **Whether `swing.prc` has any reader on the trail path.** Tier **D**, as above.
5. **Hero's c06/c07 blade.** Only c00's body model is in `dumps/`, so Hero's per-costume
   blade reach is unmeasured. His clips are byte-identical across c06/c07, and the body
   skeletons differ only in wardrobe, so his blade is very likely identical too — but that is
   tier **D** and it does not affect the recommendation, which uses Mythra's blade only.
