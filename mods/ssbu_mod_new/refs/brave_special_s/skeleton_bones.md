# Hero side-B skeleton comparison - is clip retargeting by bone name possible?

Measured 2026-09-30 by Buffy. Every "yes/NO/present/absent" below is **tier B** (measured
offline by a named script on named files with recorded sha256). Nothing here is evidence of
console behaviour. Where a statement is an inference it is tagged **D** and written as a
hypothesis with the experiment that would settle it.

## TL;DR

| question | answer | tier |
| --- | --- | --- |
| Does Mythra's c06/c07 skeleton have every bone the 24 side-B clips animate? | **No.** 57 of the 125 animated node names have no Mythra bone. | B |
| Missing-node breakdown | 12 mantle nodes, 40 skirt nodes, and Hilt/Waistbag/Scabbard/Shield/ShieldB. Runtime effect remains unverified. | B for counts; D for runtime |
| Is `Sword1` present in Hero and Mythra? | **Yes, in all five slots.** | B |
| Is it compatible? | Name yes. **Parent differs: Hero `HandR -> Sword1`, Mythra `HandR -> HaveR -> Sword1`.** | B |
| Is the bone literally named `sword1`? | **No such bone exists in any skeleton.** The engine-joint hash and model-track name are distinct; the case difference alone is not a dump-artifact measurement (section 5). | B |

---

## 1. Files read, and one deviation from the brief

The brief names `refs/brave_special_s/arc/fighter/brave/model/body/c00/model.nusktb` as an
input. **That file does not exist.** `refs/brave_special_s/arc/fighter/brave/model/body/`
contains only `c06/` and `c07/`, each holding a bare `model.nusktb`. The 184-file extraction
(`refs/brave_special_s/SOURCE.json`, `extraction.json`) fetched `c06` and `c07` only.

Hero c00's skeleton was therefore read from the read-only ArcExplorer dump,
`dumps/arc/fighter/brave/model/body/c00/model.nusktb`. This is the same game version
(13.0.4) and the same fighter, but a different extraction route (ArcExplorer export vs
arc-network), so it is a different provenance from c06/c07. Recorded here rather than
silently substituted.

`.nusktb` files read:

| slot | path | bytes | sha256 |
| --- | --- | --- | --- |
| brave c00 | `dumps/arc/fighter/brave/model/body/c00/model.nusktb` | 42680 | `1842a984acc4ba8e5cba2c0b25114621f559e8f15f54d289c7f084e6c025ca04` |
| brave c06 | `refs/brave_special_s/arc/fighter/brave/model/body/c06/model.nusktb` | 36712 | `35795d9bedbcf470bf2e3650fb0fa11e6e9850c96f94345a7561a32f73ce0f43` |
| brave c07 | `refs/brave_special_s/arc/fighter/brave/model/body/c07/model.nusktb` | 44128 | `7209ec0566c7bfdea8b13bc84101490f1f0d18f74eafa0b41e0a5bb2c4553c96` |
| elight c00 | `dumps/arc/fighter/elight/model/body/c00/model.nusktb` | 48136 | `5b6fbbe6f702e5ab9b14b208899799ec99f13c15e88611017b2547ac3de93f03` |
| elight c06 | `dumps/arc/fighter/elight/model/body/c06/model.nusktb` | 48136 | `5b6fbbe6f702e5ab9b14b208899799ec99f13c15e88611017b2547ac3de93f03` |
| elight c07 | `dumps/arc/fighter/elight/model/body/c07/model.nusktb` | 48136 | `5b6fbbe6f702e5ab9b14b208899799ec99f13c15e88611017b2547ac3de93f03` |

**Mythra's c00, c06 and c07 skeletons are the same file, byte for byte.** All three hashes
are `5b6fbbe6…`. The extraction that reported c06/c07 as differing from c00 in bytes was
describing Hero, not Mythra. Consequence: for Mythra, "which costume" is not a skeleton
question at all.

`.nuanmb` files read (24 files, 12 per slot): all twelve names are byte-identical between
c06 and c07 - `d01specials{start,hold,1,2,3,32}` and `d01specialairs{start,hold,1,2,3,32}`.
See `clip_sha256` in section 6.

Scripts: `scratch/2026-09-30_buffy/{skel_bones_v2.py, skel_diff.py, clip_bones.py, threeway.py,
clip_identity.py, sword_binds2.py, renames.py, case_convention.py, hash_case.py}`, all run
with `toolchains/py312/python.exe` (cp312; the vendored `ssbh_data_py` is on `sys.path` from
the old workspace per `paths.toml`). Scratch is disposable - the numbers are in this file.

---

## 2. Headline counts

| slot | bones | duplicate names | root |
| --- | --- | --- | --- |
| brave c00 | 150 | none | `Trans` |
| brave c06 | **129** | none | `Trans` |
| brave c07 | **155** | none | `Trans` |
| elight c00 / c06 / c07 | **169** (all identical) | none | `Trans` |

So c06 has **21 fewer** bones than c00 and c07 has **5 more**. The byte difference the
extraction noticed hides a 46-bone set difference in c06.

Intersections: `c00 ∩ c06` = 104, `c00 ∩ c07` = 140, `c06 ∩ c07` = 105, all three = 104.
**c06 is the outlier costume, not c07.**

### What each costume drops and adds against c00

Only in c06 (25): `H_Head`, `S_HairC1`, `S_HairC2_null`, `S_HairLD1`, `S_HairLD2_null`,
`S_HairLU1`, `S_HairLU2_null`, `S_HairRD1`, `S_HairRD2_null`, `S_HairRU1`, `S_HairRU2_null`,
`S_HairU1`, `S_HairU2_null`, `S_SkirtFFL4_null`, `S_SkirtFFR4_null`, `S_SkirtFL4_null`,
`S_SkirtFR4_null`, `S_SkirtL4_null`, `S_SkirtLB4_null`, `S_SkirtLBB4_null`, `S_SkirtR4_null`,
`S_SkirtRB4_null`, `S_SkirtRBB4_null`, `S_Slime1`, `S_Slime2_null`.

In c00 but not c06 (46): `H_wristL`, `H_wristR`, `S_HairL1`, `S_HairL2_null`, `S_HairLB1`,
`S_HairLB2_null`, `S_HairLF1`, `S_HairLF2_null`, `S_HairR1`, `S_HairR2_null`, `S_HairRB1`,
`S_HairRB2_null`, `S_HairRF1`, `S_HairRF2_null`, `S_SkirtFFL4`, `S_SkirtFFL5`,
`S_SkirtFFL6_null`, `S_SkirtFFR4`, `S_SkirtFFR5`, `S_SkirtFFR6_null`, `S_SkirtFL4`,
`S_SkirtFL5`, `S_SkirtFL6_null`, `S_SkirtFR4`, `S_SkirtFR5`, `S_SkirtFR6_null`, `S_SkirtL4`,
`S_SkirtL5`, `S_SkirtL6_null`, `S_SkirtLB4`, `S_SkirtLB5`, `S_SkirtLB6_null`, `S_SkirtLBB4`,
`S_SkirtLBB5`, `S_SkirtLBB6_null`, `S_SkirtR4`, `S_SkirtR5`, `S_SkirtR6_null`,
`S_SkirtRB4`, `S_SkirtRB5`, `S_SkirtRB6_null`, `S_SkirtRBB4`, `S_SkirtRBB5`,
`S_SkirtRBB6_null`, `S_Waistbag1`, `S_Waistbag2_null`.

The c06 differences are costume wardrobe, not rig changes: c06 is the slime/Slime-eared
variant with a different hair mesh (`S_HairC/LD/LU/RD/RU/U1`) and no waist bag. Note the
systematic pattern `S_Skirt*4` (c00, c07) vs `S_Skirt*4_null` (c06) - the same joint with a
different name. That is a **rename**, not an addition, and it is the one class of difference
a naive name-matching retargeter gets wrong in the *opposite* direction from the brief's worry.

Only in c07 (15): `H_ArmtwistL`, `H_ArmtwistR`, `H_Head`, `S_Hilt1`, `S_Hilt2_null`,
`S_KnotL1`, `S_KnotL2_null`, `S_KnotR1`, `S_KnotR2_null`, `S_ScabbardL1`, `S_ScabbardL2_null`,
`S_ScabbardR1`, `S_ScabbardR2_null`, `S_SwordHilt1`, `S_SwordHilt2_null` - the sword-on-back
cosmetics. In c00 but not c07 (10): `H_wristL`, `H_wristR`, `S_HairLB1`, `S_HairLB2_null`,
`S_HairLF1`, `S_HairLF2_null`, `S_HairRB1`, `S_HairRB2_null`, `S_HairRF1`, `S_HairRF2_null`.

**No bone in any of the three Hero slots is renamed relative to Mythra** except the two
case-only pairs below. Section 4 has the full sorted lists.

---

## 3. Sorted bone lists

### Hero c00 (150)

`ArmL`, `ArmR`, `Bust`, `ClavicleC`, `ClavicleL`, `ClavicleR`, `FingerL10`, `FingerL11`,
`FingerL12`, `FingerL13`, `FingerL20`, `FingerL21`, `FingerL22`, `FingerL23`, `FingerL30`,
`FingerL31`, `FingerL32`, `FingerL33`, `FingerL40`, `FingerL41`, `FingerL42`, `FingerL43`,
`FingerL51`, `FingerL52`, `FingerL53`, `FingerR10`, `FingerR11`, `FingerR12`, `FingerR13`,
`FingerR20`, `FingerR21`, `FingerR22`, `FingerR23`, `FingerR30`, `FingerR31`, `FingerR32`,
`FingerR33`, `FingerR40`, `FingerR41`, `FingerR42`, `FingerR43`, `FingerR51`, `FingerR52`,
`FingerR53`, `FootL`, `FootR`, `H_wristL`, `H_wristR`, `HandL`, `HandR`, `HaveL`, `HaveR`,
`Head`, `Hilt`, `Hip`, `KneeL`, `KneeR`, `LegC`, `LegL`, `LegR`, `Neck`, `Rot`, `S_HairL1`,
`S_HairL2_null`, `S_HairLB1`, `S_HairLB2_null`, `S_HairLF1`, `S_HairLF2_null`, `S_HairR1`,
`S_HairR2_null`, `S_HairRB1`, `S_HairRB2_null`, `S_HairRF1`, `S_HairRF2_null`,
`S_SkirtFFL1`, `S_SkirtFFL2`, `S_SkirtFFL3`, `S_SkirtFFL4`, `S_SkirtFFL5`, `S_SkirtFFL6_null`,
`S_SkirtFFR1`, `S_SkirtFFR2`, `S_SkirtFFR3`, `S_SkirtFFR4`, `S_SkirtFFR5`, `S_SkirtFFR6_null`,
`S_SkirtFL1`, `S_SkirtFL2`, `S_SkirtFL3`, `S_SkirtFL4`, `S_SkirtFL5`, `S_SkirtFL6_null`,
`S_SkirtFR1`, `S_SkirtFR2`, `S_SkirtFR3`, `S_SkirtFR4`, `S_SkirtFR5`, `S_SkirtFR6_null`,
`S_SkirtL1`, `S_SkirtL2`, `S_SkirtL3`, `S_SkirtL4`, `S_SkirtL5`, `S_SkirtL6_null`,
`S_SkirtLB1`, `S_SkirtLB2`, `S_SkirtLB3`, `S_SkirtLB4`, `S_SkirtLB5`, `S_SkirtLB6_null`,
`S_SkirtLBB1`, `S_SkirtLBB2`, `S_SkirtLBB3`, `S_SkirtLBB4`, `S_SkirtLBB5`, `S_SkirtLBB6_null`,
`S_SkirtR1`, `S_SkirtR2`, `S_SkirtR3`, `S_SkirtR4`, `S_SkirtR5`, `S_SkirtR6_null`,
`S_SkirtRB1`, `S_SkirtRB2`, `S_SkirtRB3`, `S_SkirtRB4`, `S_SkirtRB5`, `S_SkirtRB6_null`,
`S_SkirtRBB1`, `S_SkirtRBB2`, `S_SkirtRBB3`, `S_SkirtRBB4`, `S_SkirtRBB5`, `S_SkirtRBB6_null`,
`S_Waistbag1`, `S_Waistbag2_null`, `Scabbard`, `Scabbard_adjust`, `Shield`, `ShieldB`,
`ShieldB_adjust`, `ShoulderL`, `ShoulderR`, `Sword1`, `Sword2`, `Throw`, `ToeL`, `ToeR`,
`Trans`, `Waist`.

### Hero c06 (129)

`ArmL`, `ArmR`, `Bust`, `ClavicleC`, `ClavicleL`, `ClavicleR`, `FingerL10`-`FingerL53`
(15 bones), `FingerR10`-`FingerR53` (15 bones), `FootL`, `FootR`, `H_Head`, `HandL`, `HandR`,
`HaveL`, `HaveR`, `Head`, `Hilt`, `Hip`, `KneeL`, `KneeR`, `LegC`, `LegL`, `LegR`, `Neck`,
`Rot`, `S_HairC1`, `S_HairC2_null`, `S_HairLD1`, `S_HairLD2_null`, `S_HairLU1`,
`S_HairLU2_null`, `S_HairRD1`, `S_HairRD2_null`, `S_HairRU1`, `S_HairRU2_null`, `S_HairU1`,
`S_HairU2_null`, `S_SkirtFFL1`-`S_SkirtFFL3`, `S_SkirtFFL4_null`, `S_SkirtFFR1`-`S_SkirtFFR3`,
`S_SkirtFFR4_null`, `S_SkirtFL1`-`S_SkirtFL3`, `S_SkirtFL4_null`, `S_SkirtFR1`-`S_SkirtFR3`,
`S_SkirtFR4_null`, `S_SkirtL1`-`S_SkirtL3`, `S_SkirtL4_null`, `S_SkirtLB1`-`S_SkirtLB3`,
`S_SkirtLB4_null`, `S_SkirtLBB1`-`S_SkirtLBB3`, `S_SkirtLBB4_null`, `S_SkirtR1`-`S_SkirtR3`,
`S_SkirtR4_null`, `S_SkirtRB1`-`S_SkirtRB3`, `S_SkirtRB4_null`, `S_SkirtRBB1`-`S_SkirtRBB3`,
`S_SkirtRBB4_null`, `S_Slime1`, `S_Slime2_null`, `Scabbard`, `Scabbard_adjust`, `Shield`,
`ShieldB`, `ShieldB_adjust`, `ShoulderL`, `ShoulderR`, `Sword1`, `Sword2`, `Throw`, `ToeL`,
`ToeR`, `Trans`, `Waist`.

### Hero c07 (155)

c00's 140 shared bones, plus `H_ArmtwistL`, `H_ArmtwistR`, `H_Head`, `S_Hilt1`, `S_Hilt2_null`,
`S_KnotL1`, `S_KnotL2_null`, `S_KnotR1`, `S_KnotR2_null`, `S_ScabbardL1`, `S_ScabbardL2_null`,
`S_ScabbardR1`, `S_ScabbardR2_null`, `S_SwordHilt1`, `S_SwordHilt2_null`; minus `H_wristL`,
`H_wristR`, `S_HairLB1`, `S_HairLB2_null`, `S_HairLF1`, `S_HairLF2_null`, `S_HairRB1`,
`S_HairRB2_null`, `S_HairRF1`, `S_HairRF2_null`.

---

## 4. Parent maps

Every skeleton has exactly one root, `Trans`, `parent_index` null. Both fighters share the
identical core chain:

```
Trans -> Rot -> Throw
             -> Hip -> Waist -> Bust -> Neck -> Head
                                 -> ClavicleC -> ClavicleL -> ShoulderL -> ArmL -> HandL -> HaveL
                                                 -> ClavicleR -> ShoulderR -> ArmR -> HandR -> HaveR
             -> LegC -> LegL -> KneeL -> FootL -> ToeL
                    -> LegR -> KneeR -> FootR -> ToeR
```

Fingers hang off `HandL`/`HandR` in a 5-per-row x 3-row web (`FingerL10` on `HandL`,
`FingerL20` on `FingerL10`, `FingerL30` on `FingerL20`, `FingerL40` on `FingerL30`,
`FingerL51` on `FingerL10`) - identical in all five files, so not reproduced.

**Parent-map differences on shared bones (tier B):**

| comparison | shared bones with a different parent |
| --- | --- |
| brave c06 vs brave c00 | **0** |
| brave c07 vs brave c00 | **0** |
| elight c06 vs brave c00 | **1** - `Sword1` |

That single difference is the whole of it:

| | Hero c00 / c06 / c07 | Mythra c00 / c06 / c07 |
| --- | --- | --- |
| `HandR` parent | `ArmR` | `ArmR` |
| `HaveR` parent | `HandR` | `HandR` |
| **`Sword1` parent** | **`HandR`** | **`HaveR`** |
| `Sword2` parent | `Sword1` | `Sword1` |

Hero hangs the sword directly off the hand and leaves `HaveR` (the article-socket bone) as a
sibling. Mythra inserts `HaveR` between the hand and the sword. `HaveR` is present and
animated in the side-B clips, so its track travels with them - but the **sword's parent is
one link deeper on the recipient**, so a `Sword1` track copied by name is applied to a bone
whose parent pose comes from a different chain. Tier **D**: I have not established whether
that produces a visible offset, and I am not going to guess. The experiment that settles it
is one console run of the side-B slash with the trail on, against Mythra's own sword-neutral
as the control.

Bind-pose transforms (tier B, `b.transform` from each file):

| bone | Hero (all three slots) | Mythra |
| --- | --- | --- |
| `HandR` | basis `[[1,0,0],[0,0,-1],[0,1,0]]`, t `(2.836, 0, 0)` | same basis, t `(2.06181, 0, 0)` |
| `HaveR` | t `(0.759174, 0.315208, 0.007207)` | t `(0.831, 0.27, 0)` |
| `Sword1` | basis `[[0,0,1],[0,-1,0],[1,0,0]]`, t `(0.759174, 0.517494, 0.007346)` | basis `[[0,1,0],[-1,0,0],[0,0,1]]`, t `(0, 0, 0)` |
| `Sword2` | identity basis, t `(1.60884, 0, 0)` | identity basis, t `(1.5, 0, 0)` |

The two skeletons' `Sword1` binds differ in **both** orientation and offset, and the
`Sword2` offset (the blade-length joint) is 1.60884 on Hero and 1.5 on Mythra. So the
trail-tip argument in the donor's `AFTER_IMAGE4_ON_arg29` (`14`) is in Hero's bone units and
Mythra's own value is `14.5` - the same order of magnitude but not the same number, and the
same shape of problem `attack_air_f.rs` already documents for the Cloud fair. Tier **B** for
the numbers; tier **D** for any claim about how the ribbon looks.

---

## 5. `sword1`: the premise needs correcting

The brief states "both fighters name the trail bone `sword1`". **No skeleton contains a bone
called `sword1`** - in Hero c00, c06, c07, Mythra c00, c06 or c07, nor in any other dumped
fighter's c00. The bone is `Sword1`, capital S, in all five files.

`Hash40::new("sword1")` appears in the dumped ACMD text and Mythra's scripts.
The model/text case comparison alone does not establish that the converter changed
the hash. The native hitbox audit now checks lowercase joint hashes against NRO
arguments (`tools/audit_hero_side_b_hitboxes.py`; canonical hashes in
`refs/brave_special_s/hitbox_native_audit.json`). Engine joint hashes and animation
Transform names require separate treatment.
Measured (tier B): across seven fighters with both a dumped c00 skeleton and dumped scripts,
**0 exact-case matches and 2113 case-insensitive-only matches**:

| fighter | script files | exact-case bone refs | match only after lowercasing |
| --- | --- | --- | --- |
| brave | 474 | 0 | 390 |
| elight | 436 | 0 | 653 |
| eflame | 430 | 0 | 452 |
| chrom | 392 | 0 | 291 |
| gamewatch | 384 | 0 | 68 |
| diddy | 377 | 0 | 163 |
| snake | 385 | 0 | 96 |

Examples: `sword1` -> `Sword1`, `handl` -> `HandL`, `havel` -> `HaveL`, `kneer` -> `KneeR`,
`rot` -> `Rot`. `hash40("sword1")` = `0x0000000613f917e1` and `hash40("Sword1")` =
`0x00000006145512d7` - CRC32 is case-sensitive on ASCII, so these are different values
(tier B).

Use exact model names when retargeting Transform tracks. Preserve measured engine
joint hashes in ACMD; a model's capitalized name alone does not justify rewriting
those hashes. Runtime joint resolution and trail alignment remain untested here.
The previous assertion that lowercasing was a dump artifact is retracted in
handbook graveyard R-HERO-S-6. Sword visibility and shipping a trail-tip change
are not evidence of trail alignment (R-HERO-S-4).

---

## 6. Every bone the side-B clips reference, three-way

The 24 side-B `.nuanmb` files animate an **identical set of 125 node names** - verified: one
distinct node-name tuple across all 24 files. All 125 carry a populated `Transform` track;
none is a bare placeholder. Each file also carries a `Visibility` group (48 nodes) and a
`Material` group (2 nodes).

Of the 125:

| | count |
| --- | --- |
| present in brave c00 **and** c06 **and** c07 **and** Mythra | **68** |
| absent from Mythra | 57 |
| absent from brave c00 | 12 |
| absent from brave c06 | 23 |
| absent from brave c07 | 12 |
| case-only rename into Mythra | **0** |

The 12 absent from c00 are `S_MantleC1`-`C4`, `S_MantleL1`-`L4`, `S_MantleR1`-`R4`. These
are **absent from every Hero costume skeleton, present only in Chrom's** (`dumps/arc/fighter/
chrom/model/body/c0{0,1,2,3}/model.nusktb`, which is the only dumped fighter that has them).
They are absent from Mythra too. So Hero's own side-B clips animate twelve bones Hero does
not have, and Mythra's donor-copied clips will do exactly the same. The clips are simply
superset-shaped and the recipient's retargeter drops what it does not recognise - which is
what `tools/build_hero_neutral_b_assets.py` already does (`transforms.nodes = [n for n in
original_nodes if n.name in bones]`) and what its `dropped_bones` field records.

The 57 absent from Mythra decompose as:

- **12** `S_Mantle*` - absent from Hero as well (above).
- **40** `S_Skirt*` - Hero's skirt cloth, absent from the measured Mythra skeleton.
- **5** other nodes: `Hilt`, `S_Waistbag1`, `Scabbard`, `Shield`, `ShieldB`.

2026-09-30 recheck: `tools/audit_hero_side_b.py` 1.0.0 measures this partition
from the c06 S1 clip and Mythra skeleton with full input hashes in
`native_dependency_audit.json`. The earlier 45-skirt partition and header claim
that those skirt bones were absent from Hero were retracted (graveyard R-HERO-S-3).

`Hilt`, `Scabbard`, `Shield`, `ShieldB` and their `_adjust` bones are the only non-skirt Hero
bones the clips touch that Mythra lacks.

### Full three-way table (125 rows, one per animated node)

`parent` column is `c00 / c06 / c07 / elight`; `-` means the bone is not in that skeleton.

| bone | brave c00 | brave c06 | brave c07 | elight | parent c00/c06/c07/elight |
| --- | --- | --- | --- | --- | --- |
| `ArmL` | yes | yes | yes | yes | ShoulderL / ShoulderL / ShoulderL / ShoulderL |
| `ArmR` | yes | yes | yes | yes | ShoulderR / ShoulderR / ShoulderR / ShoulderR |
| `Bust` | yes | yes | yes | yes | Waist / Waist / Waist / Waist |
| `ClavicleC` | yes | yes | yes | yes | Bust / Bust / Bust / Bust |
| `ClavicleL` | yes | yes | yes | yes | ClavicleC / ClavicleC / ClavicleC / ClavicleC |
| `ClavicleR` | yes | yes | yes | yes | ClavicleC / ClavicleC / ClavicleC / ClavicleC |
| `FingerL10` | yes | yes | yes | yes | HandL / HandL / HandL / HandL |
| `FingerL11` | yes | yes | yes | yes | FingerL10 x4 |
| `FingerL12` | yes | yes | yes | yes | FingerL11 x4 |
| `FingerL13` | yes | yes | yes | yes | FingerL12 x4 |
| `FingerL20` | yes | yes | yes | yes | FingerL10 x4 |
| `FingerL21` | yes | yes | yes | yes | FingerL20 x4 |
| `FingerL22` | yes | yes | yes | yes | FingerL21 x4 |
| `FingerL23` | yes | yes | yes | yes | FingerL22 x4 |
| `FingerL30` | yes | yes | yes | yes | FingerL20 x4 |
| `FingerL31` | yes | yes | yes | yes | FingerL30 x4 |
| `FingerL32` | yes | yes | yes | yes | FingerL31 x4 |
| `FingerL33` | yes | yes | yes | yes | FingerL32 x4 |
| `FingerL40` | yes | yes | yes | yes | FingerL30 x4 |
| `FingerL41` | yes | yes | yes | yes | FingerL40 x4 |
| `FingerL42` | yes | yes | yes | yes | FingerL41 x4 |
| `FingerL43` | yes | yes | yes | yes | FingerL42 x4 |
| `FingerL51` | yes | yes | yes | yes | FingerL10 x4 |
| `FingerL52` | yes | yes | yes | yes | FingerL51 x4 |
| `FingerL53` | yes | yes | yes | yes | FingerL52 x4 |
| `FingerR10` | yes | yes | yes | yes | HandR x4 |
| `FingerR11` | yes | yes | yes | yes | FingerR10 x4 |
| `FingerR12` | yes | yes | yes | yes | FingerR11 x4 |
| `FingerR13` | yes | yes | yes | yes | FingerR12 x4 |
| `FingerR20` | yes | yes | yes | yes | FingerR10 x4 |
| `FingerR21` | yes | yes | yes | yes | FingerR20 x4 |
| `FingerR22` | yes | yes | yes | yes | FingerR21 x4 |
| `FingerR23` | yes | yes | yes | yes | FingerR22 x4 |
| `FingerR30` | yes | yes | yes | yes | FingerR20 x4 |
| `FingerR31` | yes | yes | yes | yes | FingerR30 x4 |
| `FingerR32` | yes | yes | yes | yes | FingerR31 x4 |
| `FingerR33` | yes | yes | yes | yes | FingerR32 x4 |
| `FingerR40` | yes | yes | yes | yes | FingerR30 x4 |
| `FingerR41` | yes | yes | yes | yes | FingerR40 x4 |
| `FingerR42` | yes | yes | yes | yes | FingerR41 x4 |
| `FingerR43` | yes | yes | yes | yes | FingerR42 x4 |
| `FingerR51` | yes | yes | yes | yes | FingerR10 x4 |
| `FingerR52` | yes | yes | yes | yes | FingerR51 x4 |
| `FingerR53` | yes | yes | yes | yes | FingerR52 x4 |
| `FootL` | yes | yes | yes | yes | KneeL x4 |
| `FootR` | yes | yes | yes | yes | KneeR x4 |
| `HandL` | yes | yes | yes | yes | ArmL x4 |
| `HandR` | yes | yes | yes | yes | ArmR x4 |
| `HaveL` | yes | yes | yes | yes | HandL x4 |
| `HaveR` | yes | yes | yes | yes | HandR x4 |
| `Head` | yes | yes | yes | yes | Neck x4 |
| `Hilt` | yes | yes | yes | **NO** | Scabbard x3 / - |
| `Hip` | yes | yes | yes | yes | Rot x4 |
| `KneeL` | yes | yes | yes | yes | LegL x4 |
| `KneeR` | yes | yes | yes | yes | LegR x4 |
| `LegC` | yes | yes | yes | yes | Hip x4 |
| `LegL` | yes | yes | yes | yes | LegC x4 |
| `LegR` | yes | yes | yes | yes | LegC x4 |
| `Neck` | yes | yes | yes | yes | Bust x4 |
| `Rot` | yes | yes | yes | yes | Trans x4 |
| `S_MantleC1` | **NO** | **NO** | **NO** | **NO** | - / - / - / - |
| `S_MantleC2` | **NO** | **NO** | **NO** | **NO** | - |
| `S_MantleC3` | **NO** | **NO** | **NO** | **NO** | - |
| `S_MantleC4` | **NO** | **NO** | **NO** | **NO** | - |
| `S_MantleL1` | **NO** | **NO** | **NO** | **NO** | - |
| `S_MantleL2` | **NO** | **NO** | **NO** | **NO** | - |
| `S_MantleL3` | **NO** | **NO** | **NO** | **NO** | - |
| `S_MantleL4` | **NO** | **NO** | **NO** | **NO** | - |
| `S_MantleR1` | **NO** | **NO** | **NO** | **NO** | - |
| `S_MantleR2` | **NO** | **NO** | **NO** | **NO** | - |
| `S_MantleR3` | **NO** | **NO** | **NO** | **NO** | - |
| `S_MantleR4` | **NO** | **NO** | **NO** | **NO** | - |
| `S_SkirtFFL1` | yes | yes | yes | **NO** | Hip x3 / - |
| `S_SkirtFFL2` | yes | yes | yes | **NO** | S_SkirtFFL1 x3 / - |
| `S_SkirtFFL3` | yes | yes | yes | **NO** | S_SkirtFFL2 x3 / - |
| `S_SkirtFFL4` | yes | **NO** | yes | **NO** | S_SkirtFFL3 / - / S_SkirtFFL3 / - |
| `S_SkirtFFR1` | yes | yes | yes | **NO** | Hip x3 / - |
| `S_SkirtFFR2` | yes | yes | yes | **NO** | S_SkirtFFR1 x3 / - |
| `S_SkirtFFR3` | yes | yes | yes | **NO** | S_SkirtFFR2 x3 / - |
| `S_SkirtFFR4` | yes | **NO** | yes | **NO** | S_SkirtFFR3 / - / S_SkirtFFR3 / - |
| `S_SkirtFL1` | yes | yes | yes | **NO** | Hip x3 / - |
| `S_SkirtFL2` | yes | yes | yes | **NO** | S_SkirtFL1 x3 / - |
| `S_SkirtFL3` | yes | yes | yes | **NO** | S_SkirtFL2 x3 / - |
| `S_SkirtFL4` | yes | **NO** | yes | **NO** | S_SkirtFL3 / - / S_SkirtFL3 / - |
| `S_SkirtFR1` | yes | yes | yes | **NO** | Hip x3 / - |
| `S_SkirtFR2` | yes | yes | yes | **NO** | S_SkirtFR1 x3 / - |
| `S_SkirtFR3` | yes | yes | yes | **NO** | S_SkirtFR2 x3 / - |
| `S_SkirtFR4` | yes | **NO** | yes | **NO** | S_SkirtFR3 / - / S_SkirtFR3 / - |
| `S_SkirtL1` | yes | yes | yes | **NO** | Hip x3 / - |
| `S_SkirtL2` | yes | yes | yes | **NO** | S_SkirtL1 x3 / - |
| `S_SkirtL3` | yes | yes | yes | **NO** | S_SkirtL2 x3 / - |
| `S_SkirtL4` | yes | **NO** | yes | **NO** | S_SkirtL3 / - / S_SkirtL3 / - |
| `S_SkirtLB1` | yes | yes | yes | **NO** | Hip x3 / - |
| `S_SkirtLB2` | yes | yes | yes | **NO** | S_SkirtLB1 x3 / - |
| `S_SkirtLB3` | yes | yes | yes | **NO** | S_SkirtLB2 x3 / - |
| `S_SkirtLB4` | yes | **NO** | yes | **NO** | S_SkirtLB3 / - / S_SkirtLB3 / - |
| `S_SkirtLBB1` | yes | yes | yes | **NO** | Hip x3 / - |
| `S_SkirtLBB2` | yes | yes | yes | **NO** | S_SkirtLBB1 x3 / - |
| `S_SkirtLBB3` | yes | yes | yes | **NO** | S_SkirtLBB2 x3 / - |
| `S_SkirtLBB4` | yes | **NO** | yes | **NO** | S_SkirtLBB3 / - / S_SkirtLBB3 / - |
| `S_SkirtR1` | yes | yes | yes | **NO** | Hip x3 / - |
| `S_SkirtR2` | yes | yes | yes | **NO** | S_SkirtR1 x3 / - |
| `S_SkirtR3` | yes | yes | yes | **NO** | S_SkirtR2 x3 / - |
| `S_SkirtR4` | yes | **NO** | yes | **NO** | S_SkirtR3 / - / S_SkirtR3 / - |
| `S_SkirtRB1` | yes | yes | yes | **NO** | Hip x3 / - |
| `S_SkirtRB2` | yes | yes | yes | **NO** | S_SkirtRB1 x3 / - |
| `S_SkirtRB3` | yes | yes | yes | **NO** | S_SkirtRB2 x3 / - |
| `S_SkirtRB4` | yes | **NO** | yes | **NO** | S_SkirtRB3 / - / S_SkirtRB3 / - |
| `S_SkirtRBB1` | yes | yes | yes | **NO** | Hip x3 / - |
| `S_SkirtRBB2` | yes | yes | yes | **NO** | S_SkirtRBB1 x3 / - |
| `S_SkirtRBB3` | yes | yes | yes | **NO** | S_SkirtRBB2 x3 / - |
| `S_SkirtRBB4` | yes | **NO** | yes | **NO** | S_SkirtRBB3 / - / S_SkirtRBB3 / - |
| `S_Waistbag1` | yes | **NO** | yes | **NO** | Hip / - / Hip / - |
| `Scabbard` | yes | yes | yes | **NO** | Scabbard_adjust x3 / - |
| `Shield` | yes | yes | yes | **NO** | HandL x3 / - |
| `ShieldB` | yes | yes | yes | **NO** | ShieldB_adjust x3 / - |
| `ShoulderL` | yes | yes | yes | yes | ClavicleL x4 |
| `ShoulderR` | yes | yes | yes | yes | ClavicleR x4 |
| **`Sword1`** | **yes** | **yes** | **yes** | **yes** | **`HandR` / `HandR` / `HandR` / `HaveR`** |
| `Sword2` | yes | yes | yes | yes | Sword1 x4 |
| `Throw` | yes | yes | yes | yes | Rot x4 |
| `ToeL` | yes | yes | yes | yes | FootL x4 |
| `ToeR` | yes | yes | yes | yes | FootR x4 |
| `Trans` | yes | yes | yes | yes | - (root) |
| `Waist` | yes | yes | yes | yes | Hip x4 |

`x4` means all four skeletons agree.

### The `S_Skirt*4` rename inside Hero

`S_SkirtFFL4` exists in c00 and c07; c06 calls the same joint `S_SkirtFFL4_null`. Nine
skirt joints are renamed this way, plus `S_Waistbag1` is absent from c06 entirely. Because
the **side-B clips are byte-identical across c06 and c07** and animate the un-suffixed
`S_Skirt*4` names, **c06's own clips reference skirt bones c06's skeleton does not have**
(11 nodes: `S_SkirtFFL4`, `S_SkirtFFR4`, `S_SkirtFL4`, `S_SkirtFR4`, `S_SkirtL4`,
`S_SkirtLB4`, `S_SkirtLBB4`, `S_SkirtR4`, `S_SkirtRB4`, `S_SkirtRBB4`, `S_Waistbag1`). Tier
**B** for the measurement. That vanilla c06 side-B still shows a coat in game (a tier-A
observation a reader with the console can make in one second) would confirm the drops are
inert; until then this is tier **D**.

---

## 7. Verdict on retargeting

**Possible, with two named caveats. (Tier B for the comparison; tier D for the runtime.)**

- **68 of 125** animated nodes resolve by exact name in Mythra's c06 and c07, and the two
  skeletons are the same file, so a single bone set serves both slots.
- **57** resolve to nothing. 12 of them (`S_Mantle*`) are absent from Hero too, so the
  donor's skeleton lacks them; 40 are Hero's skirt cloth and five are the other nodes
  listed above, absent from the measured Mythra skeleton. Runtime results are unverified.
  Filtering unmatched tracks is the existing `tools/build_hero_neutral_b_assets.py` route; its
  `dropped_bones` field exists to record it. Carrying them into the shipped clip would be
  pointless weight, not a correctness risk - but I have not measured what the engine does with
  a node that has no bone.
- **The bone that matters for the trail, `Sword1`, is present in all five slots.** Its
  parent differs on the recipient (section 4), and its bind transform differs in orientation
  and offset. Those are the two things to watch on hardware.
- **`Sword2` is the blade-length joint** and its offset differs (1.60884 vs 1.5). The donor's
  trail-tip argument `14` is in Hero units.

### What I could not establish

1. **Whether the engine resolves `Hash40("sword1")` to the bone named `Sword1`.** Tier **D**.
   The dump lowercases (measured, section 5); the donor NRO is the authority on the literal
   string and needs a `movz`/`movk` reconstruction in `lua2cpp_brave.nro`, i.e. Ghidra or
   the `tools/hashscan.py` movz/movk index. That is the single next step that would turn
   section 5 from "the dump is untrustworthy here" into "here is the string Hero passes".
2. **Whether the one-deep parent difference on `Sword1` is visible.** Tier **D**. Settled by
   one console run of the side-B slash against Mythra's own sword-neutral control.
3. **Whether dropping the 57 unmatched nodes is inert at runtime.** Tier **D**. The vanilla
   control is c06 Hero's own side-B: if Hero's coat and scabbard still behave, the drops are
   inert.
4. **Whether c00 should also be read from the arc-network route** to match c06/c07's
   provenance. `refs/brave_special_s/arc/.../body/c00/model.nusktb` does not exist and was
   never fetched; `dumps/MISSING.md` should carry the request if the provenance difference
   matters to the installer.

### Control used

The byte-identity of Mythra's c00/c06/c07 skeletons is the control for the costume question:
if c06 and c07 had differed, the "one skeleton per slot" reasoning would need redoing. It is
the same file three times, so one bone set is the answer for Mythra. On the Hero side, the
control is that c06 and c07's **clips** are byte-identical while their **skeletons** differ by
26 bones - clips shared across a costume change, skeletons not.

---

## 8. sha256 of every file read

`.nusktb` (6):

```
1842a984acc4ba8e5cba2c0b25114621f559e8f15f54d289c7f084e6c025ca04  dumps/arc/fighter/brave/model/body/c00/model.nusktb
35795d9bedbcf470bf2e3650fb0fa11e6e9850c96f94345a7561a32f73ce0f43  refs/brave_special_s/arc/fighter/brave/model/body/c06/model.nusktb
7209ec0566c7bfdea8b13bc84101490f1f0d18f74eafa0b41e0a5bb2c4553c96  refs/brave_special_s/arc/fighter/brave/model/body/c07/model.nusktb
5b6fbbe6f702e5ab9b14b208899799ec99f13c15e88611017b2547ac3de93f03  dumps/arc/fighter/elight/model/body/c00/model.nusktb
5b6fbbe6f702e5ab9b14b208899799ec99f13c15e88611017b2547ac3de93f03  dumps/arc/fighter/elight/model/body/c06/model.nusktb
5b6fbbe6f702e5ab9b14b208899799ec99f13c15e88611017b2547ac3de93f03  dumps/arc/fighter/elight/model/body/c07/model.nusktb
```

`.nuanmb` (24; each sha256 is the value for **both** c06 and c07, which are byte-identical):

```
e54a2ba3e7e19081...  d01specialairs1.nuanmb
11bbf62967cc08f5...  d01specialairs2.nuanmb
7d6c33139579bb9f...  d01specialairs3.nuanmb
5194734bcac1ed01...  d01specialairs32.nuanmb
434655cf56b19b65...  d01specialairshold.nuanmb
13b69ac921567d93...  d01specialairsstart.nuanmb
4d90678221f999c7...  d01specials1.nuanmb
7732338b65a0c157...  d01specials2.nuanmb
2299747e4dd4761d...  d01specials3.nuanmb
fe537939cd8fcb3d...  d01specials32.nuanmb
98b089ad0ec9b810...  d01specialshold.nuanmb
1d3c545e09efdb54...  d01specialsstart.nuanmb
```

(12-clip 16-hex prefixes; the full values are in `scratch/2026-09-30_buffy/skeleton_data.json`
and are re-derivable with `sha256sum` on the two directories.)

Other files read for cross-reference, not hashed: `dumps/arc/fighter/{brave,elight,chrom}/
model/body/*/model.numatb`, `.numdlb`, `.numshb` (string scans only),
`dumps/scripts/SSBU-Dumped-Scripts-main/smashline/lua2cpp_{brave,elight,eflame,chrom,
gamewatch,diddy,snake}/*/*.txt`, `tools/findhash.py`, `tools/hashscan.py`,
`tools/probe_bone_names.py`, `tools/build_hero_neutral_b_assets.py`,
`src/pgwr/tools/fair_sword_geometry.py`, `src/pgwr/plugin/src/acmd/attack_air_f.rs`.
