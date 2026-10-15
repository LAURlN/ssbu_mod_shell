# Mythra up-B (Hero's Spin) — further air-gravity reduction — 2026-10-03

**Status: source complete, offline checks passed, NOT installed, no console run.**
**Hit retention is UNVERIFIED until the console run in the last section.**

Requested by the user, verbatim, from `evidence/2026-10-03_pgwr_user_verdict/RESULT.md`:
*"opponents still fall out of Mythra up-B too often"* → *"Freebuff further up-B gravity
reduction"*. Scope is the modded Mythra (stock `elight` fighter id) in costumes c06/c07 only.

---

## 1. What changed — exactly two numbers

`src/pgwr/plugin/src/mythra/hero_spin_params.rs`, the two tuning constants:

| constant | old | new | effective value (Mii common x scale) |
|---|---|---|---|
| `AIR_ACCEL_Y_SCALE` | `0.85` | **`0.70`** | accel `0.10599999` → `0.09010` → **`0.07420` u/f²** |
| `AIR_SPEED_Y_SCALE` | `0.90` | **`0.70`** | terminal `1.54999995` → `1.39500` → **`1.08500` u/f** |

Nothing else. Two `f32` literals in one file.

| file | change | sha256 |
|---|---|---|
| `src/pgwr/plugin/src/mythra/hero_spin_params.rs` | values + full tuning history | `7bfe44b1b44c29bbb198648af0dcd155742002c45b83fc5f5f7491f3ccb1a186` |
| `src/pgwr/plugin/src/mythra/hero_spin.rs` | doc comment only (`air_exec`) | `e26a05cee9310c9b8385aeed5cae662c02d061779984ef565357150b3e969eb6` |
| `tools/audit_hero_spin_airtime.py` | **new**, the audit below | `98fcb7d1317818c822209c9b44ab42f01ae553770915a2b0743f9a6be343ade4` |
| `refs/mii_hero_spin_hi3/airtime_audit.json` | **new**, generated measurement | `10680964d79d34f73192d179f3ce3af8c3fa48869f559b5b288d80372c95db3c` |

`hero_spin.rs` contains no behavioural change: `air_exec` reads the two constants, so
editing them is the whole mechanism. `hero_spin_acmd.rs` is byte-unchanged.

## 2. This is intentional custom tuning, and it is labelled as such

Neither constant is a donor value and neither was ever read off a Mii trace. Mii Swordfighter's
dedicated `Hi3` kinetic lives in `miiswordsman`'s own parameter block and cannot be installed on
`elight`; the mod therefore adapts Mii's *common* air values for the aerial phase and rescales
them by hand. The file header now says so in those words ("INTENTIONALLY CUSTOM TUNING, not
donor data … meant to be retuned again by hand"), records the whole chain back to build .c, and
warns against "restoring" 1.0. The prior header described the numbers as "the donor's own tuning
from an observed Switch trace", which was wrong: they are the donor *project's* tuning, derived
from one trace of this move on this recipient.

## 3. The audit: attacker descent versus multihit retention

`tools/audit_hero_spin_airtime.py` 1.0.0 is a new tier-B tool. It reads the four `f32`
constants straight out of `hero_spin_params.rs` (so it cannot drift from what compiles) and parses
the donor's own `ATTACK` literals out of `hi3_air_spin` in `hero_spin_acmd.rs` to recover each
window's frame, box radius and vertical offsets. Argument positions come from the locked
`smash_script` checkout `fdc6144` `src/macros.rs`:

```
ATTACK(agent, id, part, bone, damage, angle, kbg, fkb, bkb, size, x, y, z, x2, y2, z2, ...)
```

so `size` is the shared box radius and `y` / `y2` the two box centres above the `bone`
(`top`). A window's **band** is `[min(y,y2) - size, max(y,y2) + size]`.

**The relationship that matters.** Hero's Spin retention is geometric. Jostle is switched **off**
at frame 11 (`JostleModule::set_status(false)`) and back on only after the frame-48 finisher, so
the attacker passes *through* the target instead of being pushed off it, and every one of the ten
boxes is a **one-frame** window (`frame(N)` → `wait(1.0)` → `AttackModule::clear_all`). A target
can therefore only be hit again if it is still inside the next box. The attacker is descending
throughout, so the descent between two windows is exactly how much of the previous box's height is
already gone. `gap/band` is that number: the descent since the previous window opened, divided by
the vertical span the current window's boxes cover. At or above ~1.0 consecutive windows cannot
span one height any more, which is the offline form of "the opponent fell out".

**The binding window is 31 → 38.** It is the only seven-frame hole in the donor's schedule; every
other gap is three to five frames.

| | frames 8→11 | 16→19 | 22→26 | **31→38** | 38→47 |
|---|---|---|---|---|---|
| **old** 0.85 / 0.90, worst gap/band | 0.23 | 0.30 | 0.43 | **0.81** | 0.61 |
| **new** 0.70 / 0.70, worst gap/band | 0.18 | 0.23 | 0.33 | **0.63** | 0.48 |

Cumulative attacker descent over the whole string:

| | descent @ f38 | @ f47 (finisher 1) | @ f49 (string end) | @ f85 (motion end) |
|---|---|---|---|---|
| Mii raw, 1.00 / 1.00 | 48.3 | 62.3 | 65.4 | 121.2 |
| **old** 0.85 / 0.90 | 42.9 | 55.5 | 58.2 | 108.5 |
| **new** 0.70 / 0.70 | 33.8 | 43.6 | 45.8 | 84.8 |
| Mythra free fall (reference) | 59.2 | 76.0 | 79.8 | 147.1 |

So the retune cuts the descent across the string by about 21%, and takes the one binding window
from "almost exactly its own box height" to clearly inside it.

**Why not lower.** Below roughly 0.55 the descent over the 85-frame motion drops toward a third of
Mythra's own fall and the move stops reading as falling at all. 0.70 keeps 85 units of descent over
85 frames — clearly in free fall, and half of what Mythra would cover in the same time — while
still moving the binding window by a measurable 0.18.

**Why not higher.** 0.85/0.90 is what is installed and what the user is reporting against.

### The honest limit of this measurement

`gap/band` measures the *attacker's* motion against the *attacker's own box*. It is not a model of
the victim. A real target here is in hitstun, and no pinned file in this workspace records hitstun
gravity, so the tool cannot say how fast a hitstun victim falls. The `freefall` column uses
Mythra's common air values as a bound only: it already shows the attacker drifting *upward*
relative to a freely falling Mythra opponent at every window, and the victim's own descent
offsets some of the attacker-side gap. That is precisely why the value was chosen from the
measured descent numbers plus the two observed traces rather than from this table alone, and why
retention remains tier D until the console run.

## 4. No permanent hover, and the exits are untouched

The air phase has two independent exits, both already in `hero_spin.rs` and both unchanged:

* `main_loop` → `FIGHTER_STATUS_KIND_LANDING_FALL_SPECIAL` the frame the fighter touches ground;
* `main_loop` → `FIGHTER_STATUS_KIND_FALL_SPECIAL` when the 85-frame donor motion ends.

`air_exec` is registered as an `Exec` callback on `STATUS_AIR_SPIN` alone, so it stops being called
the moment either exit fires and normal gravity resumes immediately. `--check` asserts the descent
stays strictly monotone for all 85 frames; a scale of 0.0 is a checked negative control that reads
as zero descent, so that assertion is not vacuous.

## 5. Preserved, deliberately

Nothing else was touched, and each of these is stated so a regression is attributable:

* **Launch** — the frame 47/48 finisher boxes (damage 5.0, base kb 361/200, the
  `GROUND_CLIFF_CHECK_KIND_ALWAYS` / `_BOTH_SIDES` notifications) are byte-unchanged; they live in
  `hero_spin_acmd.rs`, which this task did not modify.
* **Damage, knockback, hitbox sizes and offsets, frame data** — byte-unchanged, same reason.
* **Landing / recovery** — the two transitions above, unchanged.
* **Interruption cleanup** — `end()` still runs `AttackModule::clear_all` on all four phases and
  restores `JostleModule::set_status(true)` for the air phase, unchanged.
* **Status ids** `0x1F1..0x1F4`, the `FIGHTER_ELIGHT_STATUS_KIND_NUM` load-time assertion, the
  install-time `set_costume([6,7])` gate, the motion names and the sword trail — unchanged.
* **Scope of the value** — read only by `hero_spin::air_exec`, so it affects the attacker's own
  fall during the aerial phase and nothing else. No fighter-wide parameter, no victim gravity, no
  opponent constraint, no unrelated attack buff.

### Considered and deliberately NOT bundled

* **Moving `JostleModule::set_status(false)` from frame 11 to frame 8.** The first hitbox opens at
  frame 8 with jostle still *on*, so on that one frame the attacker can still be pushed off the
  target before the spin has begun overlapping it. This is a genuine, narrowly-bounded retention
  gap and it is a one-line change. It is **not** in this build: it edits donor frame data in
  `hero_spin_acmd.rs`, and shipping it with the retune would put two state-changing changes in one
  package (rule 11), so a failure could not be attributed. It is recorded here as the first
  candidate for the *next* controlled build if retention is still poor.
* **Any victim-side change** (hitstun scaling, victim gravity, a blanket opponent constraint) —
  outside the requested scope and outside this mod's ownership of other fighters.

## 6. Offline checks run here

| check | result |
|---|---|
| `python tools/audit_hero_spin_airtime.py --check` | **PASS** — windows `[8,11,16,19,22,26,31,38,47,48]` parsed from the ACMD, descent 45.8 u at frame 49, worst gap/band 0.63 at frame 38, 2 negative controls fired |
| `cargo +skyline-v3 skyline build --release --features snake-neutral-b,hero-side-b` (offline) | **Finished**, 1m47s cold. No new warnings; `grep -i hero_spin` over the diagnostics is empty |
| NRO, tuned 0.70/0.70 | `f2634b91fa4e5360f9de235d0f6b735c68b8dac574636680a0e61b2ac37ecda4`, 487,424 B |
| NRO **negative control**, same tree rebuilt at 0.85/0.90 | `65107e7b67bc701848465094c89a618552fcce363398cd3fb8911b67eb59c552` — **different**, so the two constants are genuinely compiled into the binary and not optimised away or dead |
| NRO rebuilt again at 0.70/0.70 | `f2634b91…` again — reproducible |
| markers in the NRO | `PGWR-HI3` 1, `Mii Swordfighter Hi3` 1, `special_air_hi_end` 1, `air spin` 2 |
| isolated cache | `builds/.cache/pgwr-fb-upb-gravity-target` (gitignored), features `snake-neutral-b,hero-side-b`, `logging` off |

**This NRO is a verification artefact, not a package.** It was compiled from the shared source tree
while four other agents were editing it, so it contains their in-flight work as well as this task's
change, and no manifest pins it. The installer must rebuild from the shared source and compare
against `f2634b91…` for *this file's contribution only*, exactly as the stale-cache warning in
`CURRENT_INSTALL.md` requires. No status id, asset, motion entry, sound bank, effect bank or
`config.json` entry is involved, so there is nothing to conflict with the other four scopes.

Build command used (note the absolute target path; a relative `CARGO_TARGET_DIR` resolves against
the crate directory and lands in the wrong tree):

```bash
cd src/pgwr/plugin
CARGO_NET_OFFLINE=true \
CARGO_TARGET_DIR="<repo>/builds/.cache/pgwr-fb-upb-gravity-target" \
cargo +skyline-v3 skyline build --release --features snake-neutral-b,hero-side-b
```

`cargo skyline build` does not accept `--offline`; `CARGO_NET_OFFLINE=true` is the working form on
cargo-skyline 3.5.0 / cargo-skyline's own arg parser.

## 7. Console test after the installer packages it

Run in training mode. 1-3 and 8 are the controls; judge 4-7 by eye, the release has `logging` off.
`AIR_START_Y` / `SEEN_AIR` height logging still exists in `hero_spin.rs` and prints
`[PGWR-HI3] air spin y <a> -> <b> over the phase`; under `logging` off it goes to the Skyline
console rather than `pgwr_log.txt`, so treat it as a bonus, not a requirement.

1. **Vanilla negative control.** Mythra c00 and c01. Up-B behaves exactly as stock Mythra. No
   `PGWR-HI3` behaviour change, no altered jump arc.
2. **Pyra c06 control.** The Pyra half is untouched: G&W's own up-B still throws the breath
   projectile with its parachute.
3. **Ground start, no target.** Mythra c06 and c07: up-B, hold, release. The ground spin and the
   held state must be exactly as before this change — this change cannot reach them, and if the
   ground spin looks different, something other than this task's edit is responsible.
4. **Retention, the point of the change.** Aerial use over a standing opponent. Repeat at least ten
   times and count how many attempts land fewer than all ten boxes. Compare against the same
   ten attempts on the currently installed build. Pass: fewer drop-outs, never more.
5. **Retention across damage and size.** Repeat 4 with (a) a fresh 0 % target and (b) a target at
   120 %+, and against (a) a small fighter and (b) a large one — Little Mac and Bowser both exist
   in training. Small opponents are the worst case for the band argument; check them explicitly.
6. **Both facings and both entry routes.** Repeat 4 facing right and facing left, and once entered
   from a jump apex and once from a rising up-B, so the seven-frame 31→38 window is entered with
   different vertical speed.
7. **Finisher and knockback.** Confirm the frame 47/48 finisher still connects and still launches
   with the same force, and that the target is knocked away normally afterwards. The finisher is
   byte-unchanged, so any change here is a regression.
8. **Landing, recovery and interruption.** Land mid-spin: recovery must be immediate and normal.
   Get hit mid-spin: no stuck spin, no missing `end()` cleanup (hitbox must not persist after the
   move), and you must be able to act normally. Confirm you do **not** hover: after the spin ends
   you must fall at Mythra's normal rate, not the slowed one.
9. **Regression sweep on c06 and c07.** Corrin up air, Hero neutral-B, Hero side-B, Luigi down
   throw, Lucas down smash, Ness back throw, and the Pyra/G&W side unchanged.

Return any new `sd:/atmosphere/crash_reports/` file, and the console output if you have it.

**Fail:** fewer hits than the installed build, a finisher that no longer launches, a missing or
weak hit after the move ends (a cleanup failure), any hover or floaty fall *after* the move ends,
vanilla Mythra or Pyra c06 changed, or a crash.

**Unverified before the run:** everything behavioural. The descent numbers are tier B arithmetic on
two pinned source files; that lower gravity keeps more of a hitstun victim inside the boxes is
tier D, and it is the whole point of the change.