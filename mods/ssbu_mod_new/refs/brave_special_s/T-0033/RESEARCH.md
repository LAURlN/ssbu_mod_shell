# T-0034 - Hero side-B level-2 / level-3 failure trace (research record)

Date: 2026-10-01. Author: Buffy (Freebuff, T-0034). **Research only: no production source was
changed, nothing was built, no emulator or console run was performed** (testing is benched).

Tier legend (AGENTS.md rule 8): **A** hardware, **B** measured offline by a script that still
exists, **C** read from pinned third-party source, **D** hypothesis with its settling experiment.
Nothing in this file is evidence of console behaviour.

## 0. The observation being explained

`evidence/2026-10-01_pgwr_0.20.15/RESULT.md` (tier A for "the user said it", tier D for causes):

* installed 0.20.15, NRO `7aa0ae2440e6604bf7b243209e2a5ff263e4e5bff1f7ab2a56b1e34da873feb4`,
  mod tree `ab74b4d0d5dbf7e7abb80846d95b58b175c6fe0aba54a7699d32b9fc7eeb2e9f` (1979 files);
* level 1 (Zap) "works great";
* level 2 (Zapple) works, but "the lightning effect that should run forward from Mythra's
  blade points downward";
* level 3 (Kazap): no lightning, no finisher, "looks like Hero's no-mana (failed) Kazap
  animation";
* **no log and no crash report were collected**.

The last point decides this whole record: without `sd:/ultimate/pgwr_hero_s_log.txt` from boot,
every level-3 branch below is a hypothesis with a named discriminator, and the repair task must
collect that log before changing code. Building "the obvious fix" first would be the
R-19/R-21 pattern this lab has already paid for twice.

## 1. Inputs actually available in this workspace

| wanted | present? | note |
| --- | --- | --- |
| plugin source for the move | yes | `src/pgwr/plugin/src/mythra/hero_side_b/*.rs` |
| pinned donor NRO / decompilation | **no** | `dumps/arc/` and `dumps/exefs/` are not on this disk; `paths.toml` is redacted here. Everything NRO-side is cited from the pins in `refs/brave_special_s/` |
| packaged mod tree (staged 0.20.16, superset of installed 0.20.15) | yes | `builds/pgwr/0.20.16/ultimate/mods/pyra_gamewatch_reskin/` |
| `pgwr_hero_s_log.txt` | **no** | must come from the user |
| `dumps/scripts/SSBU-Dumped-Scripts-main` (Hero ACMD text) | **no** | only `dumps/scripts/ParamLabels.csv` exists here |

Consequence: the level-2 visual question ("which effect points where") cannot be settled by
comparing against Hero's dumped effect script text in this run; the request for that text is a
precise missing input in section 6.

## 2. Static result: the level-3 static wiring in the shipped package is intact (tier B)

Measured now with the new tool `tools/audit_hero_side_b_package.py` v1.0.0 on the staged
0.20.16 tree; full output `package_audit.json` next to this file. Control: the same parse on
Hero's pinned donor list `refs/brave_special_s/arc/fighter/brave/motion/body/c06/motion_list.bin`,
whose `special_s3` entry supplies the flags/blend/cancel tail the owned entry copies.

For **c06 and c07**, all twelve owned motion kinds exist and every script they name resolves:

| entry | game | expression / sound / effect | clip | end frame | cancel frame |
| --- | --- | --- | --- | --- | --- |
| `pgwr_hero_special_s1` | registered | all registered | present | 47 | 39 |
| `pgwr_hero_special_s2` | registered | all registered | present | 77 | 51 |
| `pgwr_hero_special_s3` | registered (`0x1656048f05` = `game_pgwrherospecials3`) | all registered | present | 77 | 70 |
| `pgwr_hero_special_s32` | registered | all registered | present | 85 | 78 |
| air variants | registered | all registered | present | 47 / 77 / 82 / 85 | same as ground |

Also measured on the package: both cloned articles' motion lists exist for **c00..c07** and are
declared in `config.json` under `new-dir-files` for all eight `elight` slots; and all 18
`brave_*` effect emitters the owned ACMD spawns are present in both
`effect/fighter/elight/ef_elight_c0{6,7}.eff` (e.g. `BRAVE_LIGHTNING3_LIGHTNING`,
`BRAVE_LIGHTNING2_SWORDSPARK`, `BRAVE_CHANT`, `BRAVE_LIGHTNING_SWORDFLARE4`).

Two benign findings from the same run:

* the four start/hold entries name game scripts (`game_pgwrherospecialsstart`,
  `game_pgwrherospecialshold`, `game_pgwrherospecialairsstart`, `game_pgwrherospecialairshold`)
  that **no handler registers**. Per handbook/04 an unresolved script name is a silent no-op.
  That is almost certainly correct here (start and hold carry no hitboxes and are driven from
  Rust), but it is a measurement, not an intent: **D**, settled by checking whether Hero's own
  `special_s_start` / `special_s_hold` entries name a game script with no `ATTACK` call either.
* the S3 clip is 77 frames with cancel frame 70, and the bolt's owned lifetime is 30 frames
  (`(param_lightning/flying_dist * 10 / param_lightning/speed) * -1` = `30.0*10/-10.0*-1`),
  starting around frame 13. So there is room for an arrival at ~frame 43; a timing shortfall is
  not apparent on paper. **D** - it assumes the bolt moves 10 units per frame.

So the "the clip never loaded" class of failure is *not* supported by the package bytes. What
remains are runtime branches.

## 3. Level 3: the unconditional-success path, step by step, with the file that owns each step

There is no mana read anywhere in the recipient: `params.rs` has no SP field (resolved against
`dumps/scripts/ParamLabels.csv` this session - see the mana record), `fighter.rs` never calls
Hero's setter helper, and `mod.rs` logs `mana=off`. **The donor's insufficient-SP pose cannot be
reached from this code**: no status, flag or branch for it exists. The user's "looks like the
no-mana Kazap animation" is therefore a *visual impression of an early exit*, not evidence that
a failure branch ran. Treat "insufficient-SP pose" as **excluded by construction** (tier B for
the code shape; a claim about what the user saw stays tier D).

The intended chain and every place it can depart:

| # | step | owner | departure that matches the report | discriminating log line (already emitted, `logging.rs`) |
| --- | --- | --- | --- | --- |
| 1 | charge reaches `HOLD_FRAME_L`/release → `ATTACK3` | `fighter_loops.rs:41-58` (`hold_loop`) | `hold_frames` not counting (EXEC not running) or the user released before frame 26 | `TRANSITION 0x1fe->0x1fc hold=<n>`. If absent: not a level-3 problem, the charge never reached Kazap |
| 2 | `ATTACK3` main starts, motion `pgwr_hero_special_s3` | `fighter.rs:113` (`main_attack3`) | clip not loaded → previous clip keeps playing (handbook/04) | `TRANSITION ... end=<f>` shows the end frame the list reports (70/77); a `MotionModule::frame` far past it would show the stale clip |
| 3 | game script frame 10 sets `ACTIVATE_LIGHTNING` | `attack3_acmd.rs:9-13` | script never reached frame 10 (clip shorter than expected / different clip) | none today - **add** `ACTIVATE frame` |
| 4 | spawn loop: interval `|32/speed_lightning|` = 3.2 → first bolt on the 4th frame after activation, max 2 | `fighter.rs:191-205` | `state::get` returns `None` (costume gate), or count/interval never reached | `SPAWN lightning begin status=0x1fc count=0` / `SPAWN lightning complete count=1`; `FAIL lightning log allocation owner` |
| 5 | log-group allocation before spawn | `native.rs:38-46` | owned native returns without allocating; the article may then spawn un-logged | `FAIL lightning log allocation owner` |
| 6 | article generation into the allocated Mythra slot | `articles.rs:27-38` | slot id out of range, `native::ready()` false, or the engine refuses the clone | `SPAWN ... complete count=0` (count unchanged) |
| 7 | the bolt's own Lua `Main`: life, motion `regular`, clears transition flags | `weapon.rs:85-99` | bolt exists but its states never run (weapon kind mismatch, model/list unresolved) | `LIGHTNING regular life=30` absent |
| 8 | bolt moves: `MapCorrection` → owned copy of native `main+0x33cabd0` | `weapon.rs:120-127`, `native.rs:105-116` | owner null (founder id lookup) or hook not ready → the bolt never travels | `MAP lightning begin` / `MAP lightning complete`; absent = no travel = no arrival |
| 9 | arrival: `MOVE_DIST >= param_lightning/pass_fall_dist * 10` = 300 | `weapon.rs:101-117` | `MOVE_DIST` never grows (step 8) **or** the work id is not the one the engine updates; the owned code treats it as the donor's, which is **not** independently verified | `LIGHTNING arrived distance=<x>` - the number it prints is the discriminator |
| 10 | append transition `ATTACK3 -> APPEND (0x1fd)` | `fighter.rs:207-209` via `fighter_loops.rs:27` (`next`) | arrival seen but `change_status` rejected, or APPEND not registered | `TRANSITION 0x1fc->0x1fd` |
| 11 | otherwise the status ends at the clip end | `fighter.rs:142-157` (`finish`) | - | `TRANSITION 0x1fc->0x4` (WAIT) / `->0x2` (FALL): **this line is the signature of "no arrival"** |

Ranked by what the report most likely is, all **D** until the log exists:

1. **step 8/9 - the bolt never travels, so arrival never happens and the move ends at the clip
   end.** It explains "no lightning *and* no finisher" with one cause, and it is the branch the
   own code documents as unreplaced (a native link event became a distance guess).
2. **step 7 - the bolt exists but its Lua states never run**, so it is invisible and inert.
3. **step 6 - the article was never created** (`SPAWN ... complete count=0`).
4. **step 3 - `ACTIVATE_LIGHTNING` never set**, so no bolt is even attempted.
5. **step 1 - the charge never reached level 3** (test-method issue, not a code fault).

A sixth possibility worth naming because the report says "no lightning": the bolt spawns and
arrives but is **invisible** while the finisher then *does* run - the user reported no finisher,
so this is unlikely, and `LIGHTNING arrived` settles it in one line.

Receiver involvement, precisely: `receiver.rs` handles four event kinds, and
`pgwr_hero_s_owned_link_receiver` is the state-setting body. The arrival signal in this port does
**not** come from the receiver (step 9 is the owned replacement), so a receiver failure can
explain a missing explosion/`CALL_EXPLOSION` behaviour but cannot by itself explain a missing
finisher. `EVENT begin kind=...` lines tell the two apart.

## 4. Level 2: "the lightning effect points downward"

What the recipient spawns during Zapple, from `script_acmd.rs` `effect_2` (the only chain in the
file whose sword-attached effects use `rot_y = 0` instead of `-90`):

| frame | call | joint | rot |
| --- | --- | --- | --- |
| 0 | `EFFECT_FOLLOW brave_chant_finish` | `top` | -60 |
| 0 | `sword_on()`: `brave_lightning3_sword` + `brave_lightning_swordflare4` | `sword1` | **-90** |
| 8 | `EFFECT_FOLLOW brave_lightning3_swordspark` | `sword1` | **0** |
| 9 | `EFFECT_FOLLOW brave_lightning3_swordspark` | `sword1` | **0** |
| 10 | `EFFECT_FOLLOW brave_lightning2_swordspark` | `sword1` | **0** |
| 12 | `EFFECT_DETACH_KIND brave_lightning3_swordspark` | - | - |
| 29-30 | detach / `sword_off()` | - | - |

Candidates, each with its discriminator:

* **L2-a (measurement, tier B, the strongest static candidate): Mythra's `Sword1` bind basis is
  rotated relative to Hero's.** `refs/brave_special_s/skeleton_bones.md` section 4 records Hero
  `Sword1` basis `[[0,0,1],[0,-1,0],[1,0,0]]` versus Mythra `[[0,1,0],[-1,0,0],[0,0,1]]` - a
  ~90 degree difference in the bone space every one of these effects inherits, plus `Sword1`'s
  parent is one link deeper on Mythra (`HaveR`). Any rotation literal that was correct on Hero
  is off by that much here. Discriminator: one build with the three `rot_y = 0` calls changed to
  `-90` (rule 11: single change per hardware test), compared against Mythra's own sword trail as
  the control. If the effect then points forward, the cause is established.
* **L2-b (transcription): the level-2 arguments may not match Hero's script.** `script_acmd.rs`
  was translated from dumped ACMD text that is **not present in this workspace**. Discriminator:
  fetch Hero's `SpecialS2.txt` effect script with `tools/fetch_donor_acmd.py` and diff the three
  spawn calls argument-for-argument. Until then every level-2 rotation claim is tier D.
* **L2-c (joint resolution): the joint is named `sword1` (lowercase) while the bone is `Sword1`.**
  `hash40("sword1") = 0x613f917e` and `hash40("Sword1") = 0x6145512d7` are different (tier B,
  `skeleton_bones.md` section 5), and whether the engine resolves the lowercase hash is recorded
  there as unsettled (tier D). If it resolves to nothing, the effect inherits the model root's
  orientation - which is a plausible way to see a bolt pointing down. Discriminator: same single
  build as L2-a, changing the joint string instead of the rotation, or a one-line log of the
  effect's bone at spawn.
* **L2-d (wrong effect): the user may be looking at the level-1 trail still attached.** Zapple
  spawns no `AFTER_IMAGE4_ON`, but level 1 does and level 2's `sword_off()` runs at frame 30. A
  leftover level-1 ribbon would point along Mythra's own trail axis. Discriminator: one session,
  no other change: watch whether the artifact survives a cancelled level 1 immediately before.
* **L2-e (not a visual at all): the `brave_lightning2_swordspark` hit region.** `game_2` has one
  6.0/361/90 attack plus `FT_SHOOTING_ATTACK_GROUND_CHECK_NEW`; if the user is reading the
  training-mode hitbox overlay, the "bolt" is `ATTACK 0`. Discriminator: turn the overlay off.

Nothing above is a cause yet. L2-a/L2-c are the two that a single console build separates.

## 5. What is *not* the cause, on the evidence

* Not mana / not the donor's failed branch: no SP read, price or failure status exists in the
  recipient (`params.rs`, `fighter.rs`, `registration.rs`, and the boot log's own
  `mana=off` line).
* Not a missing/unresolved motion entry, script name, article motion list or effect emitter in
  the shipped package (section 2, tier B on the staged bytes).
* Not a "the level-3 code path is the neutral-B one" mix-up: `ATTACK3` has no `Exec` and no
  `CheckAttack`, matching the donor table (`SOURCE_STATUS.md`), and the neutral-B fireball lives
  in a separate module and statuses.

## 6. Exact inputs and hook decisions this needs (approval boundaries)

Inputs to request from the user, in priority order:

1. `sd:/ultimate/pgwr_hero_s_log.txt` **from boot**, plus `sd:/atmosphere/crash_reports/` if any.
   Build identity is already pinned by the report (0.20.15 NRO hash above); if the user tests a
   different build, the log's own `[PGWR-HERO-S] BOOT v<version>` line identifies it.
2. Hero's `SpecialS2.txt` effect/script dump (via `tools/fetch_donor_acmd.py` if the console is
   available, otherwise the repository copy) - needed to close L2-b.
3. If a level-3 `main+0x33cabd0` replacement is chosen: **no new hook site is required**. The
   bolt's `MapCorrection` already calls an owned copy of that function
   (`weapon.rs:120-127` → `native::lightning_map`), and the owner-flag read inside it is already
   translated to owned state (`pgwr_hero_s_explosion_get` at `native_1304.s` `0x2003` region).
   What is reserved is any change that needs the *engine's* bolt velocity or the real Hero
   map-collection caller - that would be a fifth interception and needs explicit approval
   (AGENTS rule 17).
4. The `Mythra +0x170` receiver slot (`main+0x4fb2110`) is implemented and self-described as
   user-approved on 2026-10-01 (`receiver.rs` header) but `CURRENT_INSTALL.md` still asks for
   confirmation and `refs/brave_special_s/native_dependency_audit.json` lists only three
   authorised sites. **That discrepancy is an approval question for the user, not a coding task.**

## 7. Repair contract handed to the implementation task (exact file ownership)

Nothing below was implemented.

1. **Get the log first** (owner: whoever runs the console test). No code change before it.
2. **Level 3**, in this order, each a separate build per rule 11:
   * if `SPAWN lightning` is absent → owner `fighter.rs:191-205` + `attack3_acmd.rs` (add an
     `ACTIVATE` log line before changing behaviour);
   * if `SPAWN ... complete count=0` → owner `articles.rs` (slot/allocation);
   * if `LIGHTNING regular` is absent → owner `weapon.rs:85-99`;
   * if `MAP` is absent → owner `weapon.rs:120-127` / `native.rs:105-116`;
   * if `MAP` is present but `LIGHTNING arrived` never prints → owner `weapon.rs:101-117`: the
     arrival predicate is an owned substitute for Hero's link event and the substitute's inputs
     (`FLOAT_MOVE_DIST`, `pass_fall_dist * 10`, life 30) are unverified. Fix the predicate, not
     the timing.
   * `TRANSITION 0x1fc->0x1fd` absent while `arrived` present → owner `fighter_loops.rs:27`.
3. **Level 2**: one build testing L2-a (rotations) with Mythra's own trail as the control; a
   second build testing L2-c (joint string). Owner: `script_acmd.rs` `effect_2` only - do not
   touch level 1 or 3's effect bodies in the same build.
4. **Logging additions** that every one of these needs and that do not exist yet, owner
   `logging.rs` call sites in `attack3_acmd.rs` / `weapon.rs` / `articles.rs`: one line at
   activation, one line per bolt frame with `LIFE` and `MOVE_DIST`, one line on the append
   decision. Keep them on the existing crash-tail file.

## 8. Manual checks for the user (not run here)

1. Boot fresh, copy `sd:/ultimate/pgwr_hero_s_log.txt` **from boot** to evidence. Confirm the
   first line is `[PGWR-HERO-S] BOOT v...` and that it matches the build you are running.
2. Mythra c06, hold side-B to the max flash (Kazap). Paste every `[PGWR-HERO-S]` line from that
   one input, in order. The four lines that matter: `TRANSITION 0x1fe->0x1fc`,
   `SPAWN lightning ...`, `LIGHTNING regular life=...`, `LIGHTNING arrived ...`, and whichever
   `TRANSITION` leaves `0x1fc`.
3. Same on c07, once, to separate a costume-only difference.
4. Level 2 with the hitbox overlay **off**, and once with it **on**, and say which one the
   "downward lightning" was in the first place (L2-e).
5. Control: real Hero side-B in the same session, level 2 and level 3, for the timing and pose
   reference.
6. Vanilla control: Mythra c00 side-B unchanged.

## 9. Unresolved hypotheses, written as hypotheses

* H1 - the bolt never travels, so no arrival and no finisher (steps 8/9). Settled by steps 8-9's
  log lines.
* H2 - the arrival predicate reads a work id the engine does not update for this clone (step 9).
  Settled by logging `MOVE_DIST` per bolt frame; a constant 0 with `MAP` present is the signature.
* H3 - the bolt's Lua states do not run (step 7). Settled by the absence of `LIGHTNING regular`.
* H4 - the article is never created (step 6). Settled by `SPAWN ... complete count=0`.
* H5 - `ACTIVATE_LIGHTNING` never set (step 3). Settled by adding the activation log line.
* H6 - the level-2 downward effect is a bone-space rotation offset (L2-a) rather than a bad
  literal or an unresolved joint (L2-b/L2-c). Settled only by the two single-change builds.
* H7 - the four unresolved start/hold game scripts matter. Considered unlikely; settled by
  checking Hero's own start/hold entries for the same shape.

## 10. Files produced by this task

* `refs/brave_special_s/T-0033/RESEARCH.md` (this file)
* `refs/brave_special_s/T-0033/package_audit.json` (tier B output of the tool below)
* `tools/audit_hero_side_b_package.py` (documented in the `tools/README.md` table; the repo
  convention is flat scripts, not one directory per tool)