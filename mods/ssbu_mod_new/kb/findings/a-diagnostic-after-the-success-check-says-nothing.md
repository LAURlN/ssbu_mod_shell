---
title: A log line after the success check reports nothing in both failure modes; and the console log is often already on the card
summary: Hero side-B's LIGHTNING arrived line was printed only after an owner lookup that can be null, so "distance signal never arrives" and "owner lookup failed" produced identical empty output for 13 Kazap attempts; and the T-0034 blocker (no log collected) existed only because nobody looked at the SD card, where the log had been sitting.
status: verified
tags: [pgwr, logging, diagnostics, negative-control, mythra, hero, mod-workspace]
updated: 2026-10-02
source: T-0052
---

## What

Two separate lessons from the same task, one about **where a diagnostic sits** and one
about **looking before declaring evidence missing**.

### 1. A log line placed after the success check cannot report either failure

`weapon.rs`'s `lightning_exec` decided "the bolt has arrived" and logged it like this:

```rust
let owner = owner(w);
if let Some(s) = state::get(owner) {   // owner can be null
    s.set(LIGHTNING_ARRIVED);
    log(format!("LIGHTNING arrived distance={:.1}", distance));   // <-- inside
}
```

`distance` is read **before** the branch, but the line printing it is **after** a lookup
that returns null. Two completely different faults therefore both emit *nothing at all*:

* (a) `distance` never reaches the threshold, so the branch is never entered;
* (b) the branch is entered and `owner` is null, so the flag is never raised.

The 2026-10-01/02 card log contains **13 Kazap attempts, 26 bolts, and zero
`LIGHTNING arrived` lines** - which is equally consistent with (a) and (b). One missing
line, two candidate fixes, and no way to choose between them from the artifact. The fix
was to log the *inputs* (life, `move_dist`, `threshold`, `owner_ok`, position) **before**
the branch, sampled, plus a separate line for the arrived-but-no-state case. Now one run
separates them.

This is the same failure shape as the 0.20.10 packaging incident, where a `PASS` was
printed from the wrong file: **a diagnostic placed downstream of the thing it measures
will happily report success while the thing is broken, and report nothing at all while
it is broken in a different way.**

### 2. "Evidence unavailable" is sometimes just "not looked at"

T-0034 closed Hero side-B level 3 with ten ranked hypotheses because
`sd:/ultimate/pgwr_hero_s_log.txt` had never been collected, and T-0052's brief said to
request it. It was **already on the card** - `sd:/ultimate/pgwr_hero_s_log.txt`, 118568
bytes, mtime 2026-10-02 00:55, next to the three other feature logs. One read-only copy
settled eight of the ten hypotheses *by counting*:

| hypothesis | verdict |
| --- | --- |
| activation flag never set | excluded - bolts spawned, which requires it |
| article never created | excluded - `SPAWN ... complete count` reaches 2 |
| bolt's Lua states never run | excluded - `LIGHTNING regular life=30` x26 |
| bolt never travels | excluded - `MAP lightning begin` x780 |
| arrival predicate | **the only survivor** |

The card is mounted read-only and at a known path; it was never a missing input. It is
the cheapest evidence in the workspace and it is *last* place anyone looks, because
"go ask the user for the log" is the natural next step when a task says the log is
missing.

## Evidence

Tier A for the log contents (it is console output, `BOOT v0.20.15`/`v0.20.16` boots on
2026-10-01/02), tier B for the counts (measured by `tools/audit_hero_side_b_log.py` v1.0.0,
which survives and reproduces every number above).

Log copied to `evidence/2026-10-02_pgwr_T-0052/pgwr_hero_s_log_card_2026-10-02.txt`,
sha256 `5311f05919164096f31a040f6f33edca4dd41d0f17d42fd50aa047b250dbdb99`, 2712 lines.

**The negative control found a bug in the analyser, not just in the log format.** The
first version of `audit_hero_side_b_log.py` reported "first unreached step" and
short-circuited, so on a synthetic log where `map` was missing it printed
`VERDICT: ... fix map` and **never showed the BOLT numbers** - hiding the one measurement
that identifies the cause, which is the entire reason the tool exists. It also matched
`LIGHTNING arrived ... but no owned state` as a *success*, because the regex was
unanchored. Both are fixed, and all three synthetic controls (success / distance-stalled
/ owner-null) are now asserted in `--smoke`, because a grader that cannot tell success
from failure, or (a) from (b), is worse than no grader.

## Why

The lesson generalises past this move: **diagnostics are evidence, and evidence placed
after a fallible check is not evidence.** When a check can return null, can be skipped,
or can be short-circuited, the log line has to sit before it and print the raw inputs -
otherwise the artifact you will analyse later is silent about exactly the case you are
trying to diagnose.

And on evidence: `AGENTS.md` rule 8 says a tier-D statement must name the experiment that
would settle it. The experiment was a file copy that took seconds, and the *card* is
right there. "Report the blocker" is correct when the blocker is real; it is a failure
mode of its own when it was one `ls` away.

## What to do instead / next

* **Put the log line before the check and print the values it compared**, not after it and
  a flag it set. If a value can be null, print the null case too - never let the failure
  mode and the success mode share an empty output.
* **Sample, do not spam.** The added `BOLT` line fires on `life % 5 == 0 || life <= 2`
  (~7 lines per bolt). An unbounded per-frame write to an SD-card log is its own bug and
  can lose the tail you need.
* **Before writing "evidence unavailable", check `sd:/ultimate/*.txt` and
  `sd:/atmosphere/crash_reports/`.** Copy the log into `evidence/` with its sha256 and note
  the card mtime; the card is read-only and reading it changes nothing.
* **Give an analyser negative controls.** Synthesise one log per expected outcome and
  assert the grader picks the right one, in `--smoke`. See
  `tools/audit_hero_side_b_log.py::smoke`.
* Still unverified: nothing here was run in game. The cause (a) vs (b) distinction for
  Kazap is *predicted* by the design of the new log line and is settled by the next
  console run, not by this task.

## Coda 2026-10-02: the design worked, and it also caught a bigger fault

The user ran the instrumented build. The `BOLT` line separated the two causes in one pass:
`owner_ok=true` on every sample excluded (b), `move_dist=0.0` against `threshold=300.0` on
every sample confirmed (a). Neither could have been read off the *old* log. Two follow-on
lessons, written up properly in
`the-donor-link-event-was-the-arrival-signal-all-along.md`: the donor's own arrival event
was arriving 30 times for 30 bolts the whole time, and the same sample line showed the
bolt's position frozen at its spawn point - so `MAP` frames never meant travel.