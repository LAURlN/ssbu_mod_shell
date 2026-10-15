---
title: Monkey Flip's aerial reuse rule failed for two separate reasons - the kick path never locked, and the entry-keyed lock record was re-owned by the swap partner
summary: 0.20.7's side-B lock was correct but only covered JUMP -> FALL; the KICK/STICK_ATTACK2 -> FLIP_FALL general lock was never ported, and the per-entry lock record reset itself on any object-id mismatch, which is exactly what Mythra landing does. Both are fixed by giving the lock an owning battle object.
status: implemented-offline
tags: [pgwr, monkey-flip, diddy, lockout, swap, statuses, transition-terms]
updated: 2026-10-02
source: T-0053
---

## What

The task asked to diagnose why the current path "can permit repeated airborne flips".
Two independent causes, both in `src/pgwr/plugin/src/status/monkey_flip.rs` /
`special_hi.rs` as of 0.20.16.

**1. The kick path set no lock at all.** The port had exactly one lock-setting exit:

```rust
if status == JUMP && next == *FIGHTER_STATUS_KIND_FALL { SIDE_LOCK[id] = (boid, true, false); }
```

The donor has three (`refs/diddy_monkey_flip/source_audit/`, `special_lockout.json`):

| donor exit | condition | instance flag | terms gated |
| --- | --- | --- | --- |
| `SpecialSJump_end` 0xd830 | next == FALL | `SPECIAL_S_INPUT_UNABLE` 0x77fc | `CONT_SPECIAL_S` |
| `SpecialSKick_end` 0xd8f0 | next == FLIP_FALL | `SPECIAL_INPUT_UNABLE` 0x77f8 | `CONT_SPECIAL_HI`, `_S`, `_LW` |
| `SpecialSStickAttack2_end` 0xdc00 | next == FLIP_FALL | `SPECIAL_INPUT_UNABLE` 0x77f8 | `CONT_SPECIAL_HI`, `_S`, `_LW` |

So the flip *with* a kick (JUMP -> KICK -> FLIP_FALL) - which is the ordinary
successful use - left up-B, down-B and side-B all available, and the donor takes
three of them away. That is the whole "kick lockout" the TODO had been carrying as
"the next separate hardware change". Note the asymmetry the donor actually has: a
leap that misses locks **only** side-B, a leap that kicks locks **all three**. Porting
one rule as "the flip lock" hides that.

**2. The lock record was keyed by entry id and reset itself on any object-id
mismatch.** Pyra and Mythra share one `FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID`, and
Mythra's `+0x168` situation wrapper calls the refresh path (`special_hi.rs`,
`elight_situation`). The old read path did:

```rust
if s.0 != (*boma).battle_object_id { *s = ((*boma).battle_object_id, false, false); }
```

so the *first read by Mythra's object* wiped Pyra's airborne side lock and gave the
flip back mid-air. Worse, the reset lived in the **query** path, so merely asking
whether the move was available could clear it. This is invisible in a no-swap test,
which is presumably why 0.20.7 read as working.

## Fix

* `Locks` (per entry) now records `owner` = the battle object that set the flag.
  `set_lock` re-owns the record when a *new* object enters the slot; `locks()`,
  `refresh_locks()` and `log_block()` return `None` for any other object, so a swap
  partner is neither blocked nor able to unlock. A record whose owner is no longer
  `sv_battle_object::is_active` is dropped, so a respawn cannot inherit it.
* A refused refresh prints one bounded `SWAPGUARD` line naming both object ids, which
  is the evidence for the swap check in the installer section.
* `end()` sets `GENERAL` on `KICK`/`STICK_ATTACK2` -> `FLIP_FALL` and `SIDE` on
  `JUMP` -> `FALL`, matching the three donor blocks and nothing else. The START
  phase's per-move reset still cannot touch either flag.
* `special_hi.rs`'s one `global_table[0x26]` callback now answers both rule sets:
  HI for `general`, S for `general || side`, LW for `general`. Fire's own
  `CONT_SPECIAL_HI` check is still there and still separate.

## Evidence

Tier B, offline, 2026-10-02.

* Donor: `tools/audit_diddy_special_lockout.py` 1.0.0 output
  `refs/diddy_monkey_flip/special_lockout.json` (three end blocks + callback `0x7920`),
  cross-read against the recovered scripts
  `refs/diddy_monkey_flip/source_audit/SpecialS{Jump,Kick,StickAttack2}_end.c`.
  `grep -l on_flag_impl refs/diddy_monkey_flip/source_audit/*.c` returns exactly those
  three end blocks plus three *status-work* flags (`MONKEY_FLIP_FLAG_SMASH`,
  `..._JUMP_START`) that the recipient already keeps as per-move phase state - so
  "these three are the only lock-setting exits" is read off the donor, not assumed.
  The callback's third flag `0x77e8` also gates `CONT_SPECIAL_HI`, but nothing in
  the Monkey Flip script set writes it, so it is not ported.
* Recipient: `cargo skyline build --release` and `--release --features logging` both
  finish clean with the change, in `builds/.cache/pgwr-mflip-target`. That proves the
  code compiles and nothing else. **No emulator, no console, no automated tests.**

## Unverified (tier D)

Everything about behaviour: whether the transition-term gate is honoured for
`CONT_SPECIAL_LW` on this recipient, whether the general lock survives an aerial in
the same airtime, whether `+0x210` (whose event is unknown; it never fired on 0.19.0)
can clear an airborne lock by firing on an ordinary status change - if it does, the
`GENERAL REFRESH entry N by class event +0x210` line is how the log will say so - and
whether Pyra's own `+0x168` landing refresh arrives while still in `FLIP_FALL`.

## Next

The package is the installer's: nothing was staged or installed by T-0053. Build with
`--with-logging` for the test, and keep the NRO from `pgwr-mflip-target` **out** of any
package - it was built without `snake-neutral-b`/`hero-side-b` and is the exact
stale-cache trap this workspace has already hit once.