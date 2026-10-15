# T-0052 - Hero side-B on Mythra c06/c07: Zapple orientation and Kazap trace

Date 2026-10-02. Author: Buffy (Freebuff, T-0052). Source-only plus one NRO build. **No
console run, no emulator, no automated tests** (testing is benched). Tier legend per
AGENTS.md rule 8: **A** hardware, **B** measured offline by a surviving script/command,
**C** pinned third-party source, **D** hypothesis with its settling experiment.

## 0. The evidence that was missing, and that was obtained

T-0034 (`refs/brave_special_s/T-0033/RESEARCH.md`) closed on "no log was collected, so
every level-3 branch is a hypothesis". The log exists **on the card** and was read
read-only at `sd:/ultimate/pgwr_hero_s_log.txt`, then copied into the workspace:

| | |
| --- | --- |
| workspace copy | `evidence/2026-10-02_pgwr_T-0052/pgwr_hero_s_log_card_2026-10-02.txt` |
| sha256 | `5311f05919164096f31a040f6f33edca4dd41d0f17d42fd50aa047b250dbdb99` |
| bytes / lines | 118568 / 2712 |
| card mtime | 2026-10-02 00:55 |
| boots recorded | `BOOT v0.20.15` x1, `BOOT v0.20.16` x6 |

So T-0034's central blocker is closed and the level-3 hypotheses it listed can be
resolved by measurement rather than ranking. Nothing under `dumps/` was touched; the
card was only read.

## 1. Level 3 (Kazap): the trace, step by step, against the same chain T-0034 named

Counts over the whole file, every `[PGWR-HERO-S]` line classified:

| observation | count | tier |
| --- | --- | --- |
| `TRANSITION 0x1fe->0x1fc` (charge reached Kazap) | 13 | A |
| `SPAWN lightning begin` | 26 | A |
| `SPAWN lightning complete` (count rises 0->1->2) | 26 | A |
| `LIGHTNING regular life=30` (the bolt's own Lua Main ran) | 26 | A |
| `MAP lightning begin` (bolt's MapCorrection ran) | 780 | A |
| **`LIGHTNING arrived`** | **0** | A |
| `TRANSITION 0x1fc->0x0` (left Kazap at the clip end) | 4 | A |
| **`TRANSITION 0x1fc->0x1fd` (the finisher)** | **0** | A |
| any `FAIL ...` line | 0 | A |
| `TRANSITION 0x1fc->0x1fe` or other early exits | 0 | A |

Per-bolt MapCorrection frame counts are strikingly regular: for all 13 Kazaps the first
bolt ran exactly 4 MapCorrection frames and the second exactly 56, i.e. 60 per Kazap and
780 in total (780 `begin` + 780 `complete` = 1560 lines; both bolts are present
simultaneously, so these are counts of *log lines*, not bolt lifetimes). This is the
"bolt exists, its states run, the map correction runs" signature, repeated identically
13 times.

**What this settles against T-0034's ranked list:**

| T-0034 hypothesis | verdict from the log |
| --- | --- |
| step 3 `ACTIVATE_LIGHTNING` never set | **excluded**: bolts spawned, which only happens under that flag |
| step 6 article never created (`count=0`) | **excluded**: `count` reaches 2 every time |
| step 7 bolt's Lua states never run | **excluded**: `LIGHTNING regular life=30` x26 |
| step 8 bolt never travels | **excluded**: `MAP lightning begin` x780 |
| step 9 arrival predicate never satisfied | **the only survivor** - zero `LIGHTNING arrived` |
| mana / no-mana failure branch | still excluded by construction (no SP read exists) |

So the failure is **localised to the arrival predicate in `weapon.rs`
`lightning_exec`**, and the move then ends at the clip end exactly as T-0034's step 11
predicted. That is now a measurement, not a ranking.

**T-0034 step 9 stated the risk precisely**: "the arrival predicate is an owned
substitute for Hero's link event and the substitute's inputs (`FLOAT_MOVE_DIST`,
`pass_fall_dist * 10`, life 30) are unverified". The log cannot close it, because of how
the line was written:

```rust
let owner = owner(w);
if let Some(s) = state::get(owner) {          // <- owner may be null
    s.set(LIGHTNING_ARRIVED);
    log(format!("LIGHTNING arrived distance={:.1}", distance));   // <- logged INSIDE
}
```

The log line sat *after* the owner lookup, so these two causes produce **identical**
output (no line at all):

* (a) `MOVE_DIST` never reaches `LIGHTNING_CHECK_LENGTH * 10` = 300.0, so the branch is
  never entered;
* (b) the branch is entered but `owner(w)` is null (`is_active(founder_id)` false), so
  `state::get` is `None` and the flag is silently never raised.

This is the same class of bug the lab already paid for in the 0.20.10 packaging run: a
diagnostic placed so that the failure mode cannot speak. Fixing the diagnostic was
therefore required before any behavioural change to the predicate could be justified.

**Why I did not change the predicate anyway.** `LIGHTNING_CHECK_LENGTH` is `0xe8ed99520`
= 30.0 and `LIGHTNING_SPEED` is `0x50f26fef6` = -10.0 (`refs/brave_special_s/
owned_native_audit.json`, tier B from the pinned vl.prc), and the bolt's owned life is
`30 * 10 / -10 * -1` = 30 frames - which the log confirms (`life=30`). At 10 units per
frame that is 300 units of travel over its whole life, i.e. the threshold is reachable
*only on the bolt's final frame or not at all*. Whether the engine's map correction
actually accumulates `FLOAT_MOVE_DIST` at 10/frame for a **cloned** article on Mythra is
not established by anything in this workspace, and `main+0x33cabd0`'s per-frame work
writes are inside the owned native copy, which I did not disassemble further.
**Lowering the threshold, changing the comparison, or extending the lifetime would each
be a guess at a number that the one missing log line measures directly.** They are left
alone, and the discriminator that separates (a) from (b) is now emitted.

## 2. Level 2 (Zapple): the responsible effect transform

`effect_2` in `script_acmd.rs` was the only chain in the file whose forward-running
lightning was attached to `sword1` with `rot_z = 0`:

| frame | call | joint | rot_z | other chains |
| --- | --- | --- | --- | --- |
| 0 | `brave_chant_finish` | `top` | -60 | same in 1 / 2 / 3 / 32 |
| 0 | `sword_on()` -> `brave_lightning3_sword` + flare | `sword1` | **-90** | same in 1 and 32 |
| 8 | `brave_lightning3_swordspark` | `sword1` | **-90** | level 1 uses -90 at frames 6 |
| 8 | `brave_lightning3_swordspark` | `sword1` | **-90** | level 1 uses -90 at frames 6 |
| 10 | `brave_lightning2_swordspark` | `sword1` | **0** | **no other call anywhere** |

T-0034's L2-a recorded the geometric reason: Hero's `Sword1` bind basis is
`[[0,0,1],[0,-1,0],[1,0,0]]` and Mythra's is `[[0,1,0],[-1,0,0],[0,0,1]]`
(`refs/brave_special_s/skeleton_bones.md` s4, tier B, both measured from `.nusktb` with
recorded sha256). Every `sword1` effect inherits the recipient's bone space, so a
rotation literal that is correct on Hero is rotated by that much here.

Two controls make the -90 change the right one rather than a coin flip:

1. **Level 1 is the user's confirmed-working control** and it attaches the *same emitter
   family* (`brave_lightning3_swordspark`) to the *same joint* at `rot_z = -90`. A
   deviation that only exists in level 2 cannot be a property of the joint.
2. **`-90` is the file-wide convention** for `sword1`-attached lightning: `sword_on`,
   both level-1 sparks, both level-2 sparks, `effect_32`'s four calls and the finisher
   all use it. `brave_lightning2_swordspark` at frame 10 was the single exception.

A single 90-degree z deviation on a bolt that should run forward is exactly a bolt
pointing along the ground, which is the reported symptom. **Tier D until the console**:
this is internal-consistency-plus-geometry, and Hero's own `SpecialS2.txt` is not in this
workspace (T-0034 L2-b), so I cannot claim -90 is the donor's literal - only that it is
the value every working sibling on this joint already uses.

Deliberately **not** changed (each would violate rule 19/one-change-per-test, and none
has evidence):

* the joint string `sword1` (T-0034 L2-c) - unchanged; it is what Mythra's own working
  Cloud fair/jab trails use (`acmd/attack_air_f.rs`, `acmd/chrom_jab.rs`, both
  hardware-confirmed), so lowercase `sword1` demonstrably resolves on this recipient;
* level 1's and level 3's effect bodies - level 1 works, and rule 11 forbids combining
  them into one test;
* `Sword1`'s one-deeper parent (`HaveR`) and `Sword2`'s blade length (1.60884 vs 1.5) -
  separate geometry questions, not orientation.

## 3. Changes made (three files, all inside `src/pgwr/plugin/src/mythra/hero_side_b/`)

| file | change | kind |
| --- | --- | --- |
| `script_acmd.rs` | `brave_lightning2_swordspark` `rot_z` `0 -> -90` (one call in `effect_2`) | **behaviour** |
| `weapon.rs` `lightning_exec` | new bounded `BOLT life= move_dist= threshold= owner_ok= x= y=` sample (life%5, plus life<=2), logged **before** the arrival branch; the no-state case now logs too | diagnostic |
| `attack3_acmd.rs` | new `ACTIVATE lightning frame=10` (and a `without owned state` variant) | diagnostic |
| `fighter.rs` `loop_attack3` | new `APPEND lightning arrived; ...` and `APPEND skipped: ... no owned state` | diagnostic |

Sampling is ~7 `BOLT` lines per bolt; the log is an append-only crash-tail file on the
SD card, so unbounded per-frame logging would be the one thing guaranteed to make the
diagnostic worse. No locks are held over a game call and every pointer is already
range-checked; the added code only reads through existing accessors.

Nothing in the port is mana-related, no donor work IDs were introduced, no new native
hook site was added or needed, and the existing approved receiver sites are untouched.

## 4. Build and package identity

Built from the installed 0.20.16 source plus these edits only:

| | |
| --- | --- |
| cargo target cache | `builds/.cache/pgwr-heroside-target` |
| features | `snake-neutral-b`, `hero-side-b` (`logging` off) |
| build | `Finished release profile in 1m 15s`, **no errors** |
| NRO | `builds/.cache/pgwr-heroside-target/aarch64-skyline-switch/release/libpyra_gamewatch_reskin.nro` |
| bytes | 466944 |
| sha256 | `5051e5815ac85c0aa2c5bfe4c18151c9b667ddfdee76fdf5e9619624cd038096` |

Previously installed 0.20.16 NRO is
`81460e74313350aaf569ce832045e8586387ab4ddf10e51bfdb690a8d29ef834`, so **this is a new
binary and the delta is not asset-only.**

Byte-level confirmation that the change reached the binary (grep of the built NRO):
`BOLT life=` 1, `ACTIVATE lightning frame=10` 1, `APPEND lightning arrived` 1,
`owner_ok` 1, `brave_lightning2_swordspark` 1, `LIGHTNING arrived` 2.

**This build is not packaged and not installed.** `builds/pgwr/0.20.16` still holds the
old NRO, and per AGENTS rule 23 a development agent does not install. `CURRENT_INSTALL.md`
carries the handoff section.

A caveat worth recording: the first build's relative `CARGO_TARGET_DIR=../../builds/...`
resolved to `src/builds/.cache/` rather than `builds/.cache/`, because the documented
command is written from `src/pgwr/plugin` where `../../` is `src/`, not the workspace
root. The cache was moved to `builds/.cache/pgwr-heroside-target` and the stray
`src/builds/` removed; the NRO hash above is post-move and verified. The relative form
needs **three** `../` from `src/pgwr/plugin`, or an absolute path.

## 5. What is still unverified

* **No console run.** Every behavioural claim here is tier D. The build compiles and
  contains the strings; that proves nothing about what is drawn or when a status
  changes (AGENTS rule 8).
* Whether the Zapple bolt now points forward is exactly the manual check below.
* Whether Kazap completes is **not predicted** by this change - the arrival predicate is
  untouched on purpose. The `BOLT` line tells us which of (a) and (b) applies, and only
  then is a predicate change justified.
* The two open approval questions from T-0034 s6 are unchanged and still the user's:
  the `Mythra +0x170` receiver slot (`main+0x4fb2110`) is implemented and self-described
  as approved in `receiver.rs` but `CURRENT_INSTALL.md` still asks for confirmation,
  while `refs/brave_special_s/native_dependency_audit.json` lists only three authorised
  sites. **This run does not add, remove or alter any hook.**
* Hero's `SpecialS2.txt` effect text (to close L2-b) and the 13.0.4 NRO dumps are still
  not in this workspace.