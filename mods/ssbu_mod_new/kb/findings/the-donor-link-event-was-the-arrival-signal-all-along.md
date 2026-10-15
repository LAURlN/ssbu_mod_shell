---
title: The donor's own link event was the arrival signal all along, and "MapCorrection ran" never meant "the bolt moved"
summary: Hero side-B's Kazap raised its owned arrival flag from a work float the engine never accumulates for the cloned article; the donor's real query - link event 0x214e64eedd - was already arriving once per bolt through the approved receiver, 30 of 30 times, and nobody read it. The same log also shows the bolt's position frozen at its spawn point for its whole life, which refutes "MapCorrection frames => the bolt travels".
status: partially-verified
tags: [pgwr, mythra, hero, link-event, arrival, diagnostics, negative-control, retraction]
updated: 2026-10-02
source: T-0052 (retry)
---

## What

Two things, one causal chain, from the same console log.

### 1. A substitute signal was standing in for a signal that was already arriving

Hero's Kazap asks its own bolt whether it has finished, through link event
`0x214e64eedd` (lightning class callback `0x33caa70` -> Hero receiver `0x8555a0` ->
`0x85593c`). This port already patched the recipient's `+0x170` slot for that event, and
`state.rs` even says so:

```rust
/// Owned replacement for the donor's native "has the bolt struck" link-event query.
pub(super) const LIGHTNING_ARRIVED: u32 = 1 << 9;
```

But the flag was raised somewhere else entirely - in the bolt's Exec, from
`FLOAT_MOVE_DIST >= LIGHTNING_CHECK_LENGTH * 10`. The 2026-10-02 card log settles that
route as dead on this clone: 32 `BOLT` samples across 30 bolts, **every one**
`move_dist=0.0` against `threshold=300.0`, with `owner_ok=true` throughout, while
MapCorrection ran ~30 frames per bolt. The engine does not accumulate that work float for
this cloned article on Mythra. At the same time the log contains 30
`EVENT begin kind=0x214e64eedd` lines for 30 bolts, all with the owner in the third
attack - the donor's actual signal, arriving reliably, ignored.

**The fix:** raise the owned flag in the already-patched receiver when that event arrives,
once, guarded on our own third attack and our own per-move bolt count. No donor work id, no
invented distance, no new interception.

### 2. `MAP lightning begin` x900 never meant the bolt moved

The previous run of this task wrote off "the bolt never travels" because MapCorrection
frames were present, and `refs/brave_special_s/T-0033/RESEARCH.md` step 8 says the same
(`MAP` present = travel). Both are wrong here. The `BOLT` line also prints the bolt's
position, and it is **byte-identical for the whole life of every bolt** - both bolts of a
Kazap share one point - and that point's `y` is exactly
`param_special_s.offset_y_lightning` (85.0), i.e. the spawn position. MapCorrection ran
900 times and the bolt never left where it was created. Recorded as R-HERO-S-7.

## Evidence

Tier A for both (console log, read-only copy from the card),
`evidence/2026-10-02_pgwr_T-0052/pgwr_hero_s_log_card2_2026-10-02.txt`, sha256
`ff7afc8cdef4dacd692c050eba6064967023078210c3acb2c61e5f853d94e48f`, 3066 lines, booting
`v0.20.17` (the build that carried this task's Zapple fix and its `BOLT` diagnostic).

Tier B for the counts and the verdict wording: `tools/audit_hero_side_b_log.py` **1.1.0**,
which now asserts the card2 numbers in `--smoke` (15 Kazaps, 30 bolts, 32 samples,
`move_dist` min == max == 0.0, `owner_ok == ['true']`, 30 lightning events, 0 arrivals)
so this conclusion cannot be quietly edited later, alongside the existing three negative
controls and the older 2026-10-01 log.

Tier C for the event's identity: `refs/brave_special_s/link_event_native_audit.json`
(`0x33caa70` sends it; `0x8555a0`/`0x85593c` consumes it) and the pinned
`skyline-smash 315e4e8` `lua_const.rs` for the work ids. Our own copy of the handler
(`native_1304.s` `.Lhero_s_85593c`) counts the *allocated* lightning slot and releases the
donor log group; it sets nothing we can read, which is precisely why the owned flag had to
be raised on the Rust side of the same event.

**Unverified:** that the finisher now runs (tier D until hardware - nothing here was run in
game), and why the bolt does not travel. The bolt's `FLOAT_HEAD`/`FLOAT_TAIL`/`FLOAT_DIR`
are printed by the new `bolt_work()` for exactly that reason and are **unobserved**.

## Why

* **A stand-in for a signal is worse than no signal**, because it fails silently and
  forever while the real signal keeps arriving. If a port owns a replacement for a donor
  event, the first thing to check is whether the donor event is *actually being delivered*
  - that is a log count, not an argument. Here it was 30 of 30, in the very file that
  "proved" the move could not complete.
* **Frame-count evidence is not movement evidence.** `MAP` present proves a callback ran.
  Position before/after proves the bolt moved. The gap between those two is exactly where
  this bug lived for a whole task.
* The earlier finding in this family
  (`a-diagnostic-after-the-success-check-says-nothing.md`) paid off: because `BOLT` was
  printed *before* the arrival branch and printed `owner_ok`, one run separated cause (a)
  from cause (b) with no ambiguity, and both were then settled by measurement. Diagnostics
  placed before the check are what make the repair provable instead of ranked.

## What to do instead / next

* When a port substitutes a signal for a donor event, **log the donor event's arrival
  count** next to the substitute's value. If the donor event is arriving and the substitute
  is flat, the substitute is the bug - no ranking required.
* For anything that moves, log a **position delta**, not an activity count. `MAP`/exec
  frames measure that code ran; only coordinates measure that the game happened.
* Any future fix of the travel defect must be a separate build (AGENTS.md rule 11). The
  two live candidates, in order: (a) `head`/`tail` frozen => the owned copy of
  `main+0x33cabd0` is not advancing them; (b) `head`/`tail` growing => the bolt extends
  along its own head/tail and only `FLOAT_MOVE_DIST` accumulation is missing.
* Related and still open: `state::CALL_EXPLOSION` is read/written by `native_context.rs`
  and set by nothing in the port, so the donor's explosion branch cannot fire.