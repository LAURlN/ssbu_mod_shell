# Motion lists / animation

Tiers: **A** hardware-confirmed (console or decoded crash report) - **B** measured offline by a script that still exists - **C** read from pinned third-party source - **D** hypothesis. Anything without a tier below is A/B unless marked otherwise. Paths in the source column refer to the *old* workspace (`modpack_test_1`); the same material now lives under `projects/*/history/`, `dumps/` and `evidence/`.

- `hash40(name) = (len << 32) | crc32(name)`; the motion-list animation-name hash **includes** the extension (`hash40('d01specials.nuanmb')`). (root HANDOFF, guide §7)
- `motion_list.bin`: header `magic(hash40 "motion") u64, motion_path u64, count u64`; entry = 24-byte header
  (`kind, game_script u64, flags u16, blend u8, animations u8, size u32`) + animation hashes padded to 4 + tail;
  `size % 8 == 4` -> last 2 bytes hold the **cancel frame**. Copy donor entries **whole**; round-trip assert. (guide §7, 2026-09-29 entries)
- The entry carries per-move timing (cancel frame, blend), so porting only clips gives wrong FAF (Pyra's list gave G&W jab cancel 22 vs 16). (guide 2026-09-29 "new file names")
- `motion_path` in the list is not the folder animations load from (vanilla G&W c07 names `c00`). (root HANDOFF trap 6)
- **`MotionModule::motion_kind` only echoes the request** - not evidence a clip loaded. Use `end_frame`/`frame` of the playing clip; a clip that failed to load leaves the previous clip playing. (root HANDOFF; this is the Monkey Flip root cause)
- `.prc` beside the motions are per-fighter and skeleton specific: `ik.prc`, `scharge.prc`, `update.prc`, `flip.prc`; leaving Pyra's on a G&W skeleton dislocated legs. (guide, fixed in 0.7.0, A)
- Retarget by bone-name intersection; drop donor-only tracks (`Miihead`, `Finger*4_eff`); c06/c07 skeletons of Pyra/Mythra and of G&W are byte-identical. (guide, Hi3 manifests)
- **Reusing a clip file name instead of adding one**: a motion entry names its clip by file-name hash, and pgwr ships a donor clip under a *spare* eflame name rather than under its own name, because a name the base install does not have is not resolved *unless it is declared* (root HANDOFF trap 1 was about undeclared names). **Declared new names do load (A, 2026-09-30):** Hero neutral-B adds new kinds (`pgwr_hero_special_n_start` ...) naming new clips (`pgwrherospecialnstart.nuanmb` ...) listed under `new-dir-files` `fighter/elight/c0N`; `evidence/2026-09-30_pgwr_0.18.0/pgwr_log_from_boot.txt` shows `motion=0x1920438ca3 ... end=7.0` and `0x14c7a6c6ff ... end=73.0`, the new clips' own lengths (7, 73). So the spare-name pool below is a choice, not a limit; a donor with more clips than spares ships them under declared new names. The spare pool is `{clips Pyra's own list names} - {clips the rebuilt list still names}`; because each of Pyra's kinds whose entry is rewritten to a stand-in *stops* naming its original clip, those names are unreachable from the new list by construction - asserted in `build_motion` (`referenced <= written`). Measured for c06/c07 2026-09-30: pool 40, G&W's clips take 19, Monkey Flip's twelve take the next 12 (including `d04final*`, `d04visualscene01/02`, `h14gekikarawaitface`), 9 left over. The residual risk is code that loads a clip *by name* outside the list; measured in the same build, exactly one name is loaded that way (`a00defaulteyelid`) and it is not in the pool. (B)
- Mii option identity: `Hi1` = Stone Scabbard, `Hi3` = Hero's Spin (an entire release shipped the wrong one). Verify a move's identity from game script behaviour, not from its suffix. (guide 2026-09-26)
- **Rig compatibility limits name-intersection retargets.** Historical R.O.B. down tilt
  retained 11/82 nodes, leaving robot-specific torso/limbs unrepresented (B, prior
  generator 1.0.0). The user rejected both prior clips in T-0036; no isolated failure
  cause is established. Version 2.0.0 of `src/pgwr/tools/build_robot_dtilt.py` replaces
  this move's filtering with an authored recipient motion; other retargeters are unchanged.

## T-0036 custom recipient down tilt (2026-10-01)

**B: generated/static asset evidence; D: appearance and in-game hand/hitbox alignment.**
Recipe `src/pgwr/assets/robot_dtilt/recipe.json` uses frame-zero built recipient idle
and actual bind matrices for every other bone. Local SSBH row-vector bind matrices
are transposed for column-vector FK; animated xyzw quaternions are converted directly.
Two-link IK uses recipient upper/lower limb translation lengths, foot anchors from
idle, forward knee poles and lowered elbow poles. Waist/Bust share forward lean;
Neck counters it. There is no bone stretch or broad skeleton edit. The left hand
guards the torso while the right palm extends low, then both return to idle by 15.

Pinned R.O.B. clip SHA-256 `dd265d1cbad5d36ae5b4401c335893d2e3f578fc8319960381109758f13d6879`
supplies duration 28 (29 samples); complete pinned `attack_lw3` entry supplies cancel
15/flags 0x80. ACMD remains unchanged: active 3, clear 4, donor sounds/effects/rumble.
Recipient skeleton SHA-256 `02ed7ba122998f337c212f29072d44cdf6c582b23ba179f1447bece5e593be83`
is recorded with both idle hashes and recipe hash in
`evidence/2026-10-01_pgwr_T-0036/animation_generation.json`.

The first authoring draft requested a wrist outside recipient reach; revised goals
have zero IK unreachable distance in the final generation report. Both final clips
hash `d30722b5763f7b6e4f9e4d834cf57b91b69befccd5eb4321f8fbf3bdc81f6d19`.
All 165 recipient bones receive 29 transform samples, including helper/grafted bones
held at their own idle/bind transforms. Visibility retains 98 explicit recipient
idle nodes; only `GW`, `HeadM`, `LhandHold`, `NoseM`, `RhandHold` are enabled.
Material groups are absent. No manhole or unrelated prop track is enabled.

Stage command (from mod root, under exclusive T-0036 shared-build reservation):
`python -B src/pgwr/tools/build_robot_dtilt.py --baseline builds/pgwr/0.20.16 --package builds/pgwr/0.20.16+robot-dtilt.4 --stage-only --preview`.
Earlier authoring commands used suffixes `.2` and `.3`, without `--preview`; those
draft stages remain superseded and must not be installed. The PNG is a joint authoring preview,
not a mesh render or a game test. No automated tests or Ryujinx were run.
Full asset rebuild is unnecessary here and `dumps/arc` is absent; the complete local
0.20.16 release was used. Plugin version/NRO remain 0.20.16; recipe version is 2.0.0,
package identity is the versioned animation variant. Rust was not recompiled; unique
future Cargo cache reserved as `builds/.cache/pgwr-T-0036-target`.
Only the two down-tilt clips differ among 1983 mod files, so motion routing/entries,
model bind transforms, gameplay, sounds/effects and unrelated assets are retained.
Console controls/checks and staged identity: own section of `CURRENT_INSTALL.md`.

## T-0048 stretched-arm recipe 3.0.0 (2026-10-02)

Recipe 2.0.0 asked the two-link `solve_limb` for wrist goals about 5.2x the recipient's
measured arm length (shoulder-to-hand 3.9477 L / 3.9641 R against a target near 20.7 out).
`solve_limb` clamps a request to the links' reach, so the unreachable part of each goal was
dropped without an error and frame 3 peaked short of the donor capsule. Recipe 3.0.0 removes
the arms from that IK: `solve_limb` is now feet only, and a new `deform_arm()` deforms each
arm as a rigid block rooted at `Shoulder{L,R}` - rotate the shoulder so the shoulder-to-hand
line points along the recipe's `arm_aim`, then translate it by a pure shift along that same
direction until the hand sits `arm_reach * H` from the fighter's origin. `Arm{L,R}`,
`Hand{L,R}` and the `H_*` helpers are children and ride along untouched.

Two conventions worth carrying forward:

- **Anchor the target to the fighter's origin, not to each limb's own rest position.** An
  idle-relative target makes a limb that starts further back land short, so one shared recipe
  value cannot serve a left and a right limb. Measured here: at frame 3 the hands land at
  z 16.115 (L) and 15.990 (R), 1.25 body heights forward, both inside the donor capsule.
- **Decompose any bone 3x3 into an orthonormal rotation plus a positive axis-aligned scale
  before reading a quaternion.** `quaternion()` used to extract straight from the matrix, which
  folds scale silently into the rotation, and the emit path hardcoded `[1,1,1]`, so nothing
  ever measured whether a bone had been scaled. The 3.0.0 path decomposes by Gram-Schmidt
  over the matrix's own columns (eigenvectors of `M M^T` are wrong here - a rotation's is the
  identity and has no usable eigenbasis), writes the bone's measured scale, and the generation
  report carries `scale_written_max_deviation` (2.7e-15: this recipe scales nothing, and the
  invariant is now checked rather than assumed).

The capsule in the preview overlay and the report's hitbox gap is parsed out of
`src/pgwr/plugin/src/acmd/robot_attack_lw3.rs` at run time and that file's hash is recorded,
so the authoring diagram cannot drift from the capsule the engine is asked to evaluate.

Stage command (mod root, under the shared-build reservation named by `--task-id`):
`python -B src/pgwr/tools/build_robot_dtilt.py --baseline builds/pgwr/0.20.16+robot-dtilt.4 --package builds/pgwr/0.20.16+robot-dtilt.5 --stage-only --preview`.
Recipe 3.0.0, both clips `06fb085e436a7e49862f1c64223afd6c659cc68c35ae55f8b99a2f6443f22060`,
1983 mod files with only the two down-tilt clips changed and both packaged NROs byte-unchanged.
No automated tests, Ryujinx, console run or card access; mesh appearance and palm/hitbox
alignment remain tier D. Record:
`evidence/2026-10-02_pgwr_T-0045/T-0048_animation_record.md`; finding:
`kb/findings/reach-beyond-limb-length-is-not-an-ik-problem.md`.


## Snake up tilt (2026-10-02, Freebuff slot 2)

**B: measured offline by `src/pgwr/tools/build_snake_uptilt.py` and `tools/audit_snake_uptilt_delta.py`.
D: how it looks and hits.** Recipe: `src/pgwr/plugin/src/acmd/snake_attack_hi3.rs`,
`refs/snake_attack_hi3/`, evidence `evidence/2026-10-02_pgwr_snake_uptilt/`.

- **A name-intersection retarget must be checked for limbs that survived the filter and
  still do not move.** That is precisely what the user rejected on the R.O.B. down tilt, and
  node coverage alone cannot see it: Snake's up tilt keeps 77 of 87 transform nodes on the
  built c06/c07 recipient, but "87 -> 77" would have been reported just the same for a clip
  whose legs sat in rest pose. `leg_motion()` compares every kept track against the
  recipient's own idle and `deploy_for_slot` raises if any of `LegL/R`, `KneeL/R`,
  `FootL/R`, `ToeL/R` is static. Measured: `LegL` 92.6 deg / `LegR` 78.0, `KneeL` 97.8 /
  `KneeR` 80.6, `FootL` 102.6 / `FootR` 54.4, and `ToeL`/`ToeR` translate 0.59 units with
  0.0 and 7.1 degrees of rotation - so "moved" must mean rotation **or** translation, not
  rotation alone.
- **A clip can be longer than its own cancel frame.** Snake's `c02attackhi3` is 48 frames,
  his expression script ends at 32 and his `attack_hi3` motion entry cancels at 38, so the
  last ten frames are never played. That is the donor's own arrangement and the entry is
  copied whole; it is a fact to record, not a bug to repair.
- **The donor's ACMD text is not always in the tree.** `dumps/scripts/SSBU-Dumped-Scripts-main`
  is gone from this workspace and the export `paths.toml` names is nearly empty, so a donor
  script that earlier notes point at has to be re-pinned from the pinned upstream commit
  (`refs/snake_attack_hi3/donor_acmd/`, per-file sha256). Re-pin a **control** alongside it:
  R.O.B.'s `AttackLw3.txt` was pulled at the same commit because the shipped
  `acmd::robot_attack_lw3` was written from exactly that file, which is how the dump's
  conversion errors were judged before any line was ported. Snake's `AttackHi3` had none -
  no branch, no lost braces, no article call, no work-id write - so nothing was dropped.
- **A donor `.tonelabel` need not name every tone it ships.** `merge_hero_neutral_b_sound.labels_read`
  asserts full coverage, which is right for a recipient bank and wrong for a donor:
  `vc_snake_c00.tonelabel` has **34 entries for 48 audio files**. `merge_snake_uptilt_sound.py`
  reads donors with `labels_read_partial`, which checks every entry that is present and
  tolerates the missing ones.

## Porting a throw: four measured facts (Ness back throw on Mythra, 2026-10-02)

**B** unless marked. All four were measured, not recalled, and each one removes work that every
other throw port in this project would otherwise assume it needs. Recipe: `refs/ness_throw_b/`,
`tools/audit_ness_throw_b.py`.

1. **A throw usually needs no alias, no spare clip name and no `config.json` entry.**
   `throw_f` / `throw_b` / `throw_hi` / `throw_lw` are *shared* motion kinds, and the
   animation-name hash inside the entry includes the file extension — so both fighters' lists name
   the **same file**, `e01throwb.nuanmb`. Measured for Ness vs Mythra: identical kind hash
   `0x74e9acdb1`, identical `game_script` `hash40("game_throwb")`, identical flags `0x0081`, and a
   single differing byte, the cancel frame. So a throw is an in-place override of a file the base
   game already ships in that costume group, not the new-file experiment `build_motion` does for
   G&W's clips. Check the two `anims` hashes before planning an alias. Snake's *up tilt* is the
   contrasting case — there the donor clip name genuinely does not exist on the recipient.
2. **The motion-list delta for a throw is usually one byte.** Copy the donor entry whole and only
   the cancel frame moves. Prove it rather than assuming: diff the two entries and assert the
   differing offsets. `src/pgwr/tools/mlist.py` exists for exactly this, and its
   `encode(parse(x)) == x` round trip is what makes "no other entry changed" checkable.
3. **`REVERSE_LR` in a back throw is per-fighter, not a back-throw convention.** Mythra's vanilla
   `throw_b` has it at the pickup frame; Ness's does not anywhere. A sweep of ten other fighters'
   `ThrowB` at the pinned commit `5900468523` splits 6/6: kirby, pikachu, snake, younglink and
   ness omit it; mario, luigi, robot, cloud, gaogaen and gamewatch use it — at varying frames and
   either side of `CHECK_FINISH_CAMERA`. So a donor's omission is authored, not a dump artifact,
   and adding one back is inventing donor behaviour. Grade the facing by eye on hardware.
4. **Audit victim dependencies separately.** Ordinary throws use the victim's authored
   `thrown_*` entries; do not replace those clips when importing an attacker throw.
   DK cargo is an exception requiring a sharing-route audit: tier-B measurements of
   94 motion lists found empty cargo entries and 15 actual donor pose templates.
   Empty entries alone do not establish missing assets. The native capture-parent
   sharing route and Pickel overlays are now measured offline; owned aliases/full
   body-variant template tracks are packaged in dk_cargo 0.1.0-test. Runtime
   attachment remains unverified (`refs/donkey_cargo/native_pose_route.json`,
   `evidence/2026-10-03_pgwr_dk_cargo/RESULT.md`).

**A bindings gap worth knowing before writing a throw.** The donor's
`FighterCutInManager::set_throw_finish_zoom_rate` / `set_throw_finish_offset` calls need a manager
instance. The pinned `skyline-smash` 315e4e8 declares both methods but exposes **no accessor**, and
the crate has no `singletons` module; using that nonexistent module fails E0433.
Three places in this repo have already hit it: `acmd/monkey_flip.rs` (dropped for Diddy's cling
attack), `src/pmclone/moveset/src/acmd/cflame.rs` (which excluded Mythra's *own* vanilla
`throw_b`), and `mythra/ness_throw_b.rs`. `CHECK_FINISH_CAMERA` is unaffected, so the throw finish
*camera* still ports; those implementations omit donor cut-in framing. **Correction
2026-10-02 (B):** the pinned 13.0.4 main exports the eight-byte data symbol
`_ZN3lib9SingletonIN3app19FighterCutInManagerEE9instance_E` at `0x52b8850`.
`src/pgwr/tools/dk_cargo/native.py` pins its address and size in
`refs/donkey_cargo/native_message_sites.json`. A task-owned extern-symbol
declaration is a candidate route without a raw-offset hook or framework change;
pointer checks, ABI/build and runtime behavior remain unverified. The bindings
gap alone is insufficient evidence that reserved work is required.

**Mythra is not the eflame case.** pgwr replaces Pyra's skeleton with G&W's but leaves **Mythra's
vanilla skeleton in place** — measured: the package ships no
`fighter/elight/model/body/c06/model.nusktb`, only `.nutexb` textures. So a Mythra retarget filters
against the ARC skeleton, which is what the game actually loads. That is the opposite of every
eflame move in this project, which must filter against the *built* grafted skeleton. Mythra c06
and c07 skeletons are byte-identical, so the two slots' clips come out identical.

## Retargeting a donor air clip onto the eflame pair (pikachu-airb 1.0.0, B, 2026-10-03)

Measured for `c05attackairb.nuanmb` (final frame index 53.0; groups Transform 55,
Visibility 38, Material 1) and `c05landingairb.nuanmb` (final frame index 30.0),
both against the **built** c06/c07 skeletons (165 bones each; the donor has 77).

* **45 of 55** Transform nodes survive. The ten that do not are exactly
  `EarL1, EarL2, EarR1, EarR2, Hat, Have, Tail1..Tail4` - costume appendages
  Game & Watch has no bones for. Dropping them is the correct outcome, not a
  failure, but it must be **listed and asserted** rather than silently filtered:
  a filter that reports "kept 45" without the names cannot distinguish a costume
  appendage from a mistyped lookup.
* **Parent chains must be compared by parent *name*, not index** (re-confirmed
  here on 45 nodes, 0 mismatches). The two skeletons have different bone counts
  and different index spaces by construction, so an index comparison is noise.
* **The donor's Visibility group is 38 nodes and none of them exist on the
  recipient's idle.** Filtering it to nothing leaves the mesh visibility state
  undefined for the move. The group is rebuilt from the recipient's **own idle
  clip** (98 nodes) instead - not from the donor's, which would carry names the
  recipient does not have. The Material group (1 node) is dropped outright.
* **A limb can move by translation with zero rotation.** `ToeL` and `ToeR`
  measure 0.0 degrees of rotation across the whole clip but 0.329 / 0.340 of
  translation, so a "did this bone rotate?" gate produces a false positive. The
  gate is "did rotation **or** translation change", and the result carries both
  numbers so a reader can see which it was. All 17 tracked limb bones move; the
  largest is `Hip` at 176.6 degrees.
* **`ElbowL` / `ElbowR` are not bones on either fighter** (both carry
  `H_ElbowL` / `H_ElbowR`). They were removed from the tracked set so the
  static-limb gate cannot cry wolf about a bone that was never there.
* **A donor motion entry may already be byte-identical to the recipient's.**
  `landing_air_b` differed at **zero** offsets, so the only thing that needed
  shipping there was the retargeted clip and the scripts. The sibling
  `attack_air_b` entry differed at exactly **two** offsets, `[16, 62]` - the
  `flags` halfword (`0x0080` -> `0x0084`) and the `cancel` `u16` at the tail
  (296 -> 300). Expect the delta size to be wildly uneven between the two kinds
  of a single move; an audit that asserts "this entry changed" without first
  measuring it will fail on the entry that correctly did not.
* The animation-name hash covers the file name **with its extension**, as the
  Chrom jab established: `c05attackairb.nuanmb` is named by both the donor and
  the recipient, so this move needs **no `config.json` alias**.
