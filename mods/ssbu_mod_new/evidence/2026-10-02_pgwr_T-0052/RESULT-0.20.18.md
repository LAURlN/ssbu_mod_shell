# T-0052 retry (2026-10-02) - Kazap cause settled, arrival re-wired to the donor's own event

Author: Buffy (Freebuff, T-0052). Tier legend per AGENTS.md rule 8: **A** hardware console
result, **B** measured offline by a surviving script, **C** pinned third-party source, **D**
hypothesis with its settling experiment. The earlier run of this task is
`RESULT.md` in this directory and is **immutable** (rule 13); this file is a second report
about a later build, not a rewrite.

## 0. The card log arrived, and it settles the question the last report left open

The previous run asked for `sd:/ultimate/pgwr_hero_s_log.txt` "from boot" of the 0.20.17
build. The user ran it. The log was on the card again, mtime 2026-10-02 02:47:

| | |
| --- | --- |
| workspace copy | `pgwr_hero_s_log_card2_2026-10-02.txt` |
| sha256 | `ff7afc8cdef4dacd692c050eba6064967023078210c3acb2c61e5f853d94e48f` |
| bytes / lines | 134262 / 3066 |
| card mtime | 2026-10-02 02:47 (read-only copy; the card was not written) |
| boots | `BOOT v0.20.15` x1, `BOOT v0.20.16` x6, `BOOT v0.20.17` x1 |

`BOOT v0.20.17` is the collective build that carries this task's Zapple rotation fix, so
the `BOLT`/`ACTIVATE` diagnostics the previous run added are present. Measured by
`tools/audit_hero_side_b_log.py` 1.1.0 (`log_audit_card2.json`):

| observation | count | what it settles |
| --- | --- | --- |
| `TRANSITION 0x1fe->0x1fc` (Kazap attempted) | 15 | level 3 really is being tried |
| `ACTIVATE lightning frame=10` | 2 | the donor's activation path runs |
| `SPAWN lightning begin` / `complete` | 30 / 30 | two bolts per Kazap, created every time |
| `LIGHTNING regular life=30` | 30 | the bolt's own Lua Main runs |
| `MAP lightning begin` | 900 | MapCorrection runs ~30 frames per bolt |
| **`BOLT` samples** | **32** | see below |
| **`EVENT begin kind=0x214e64eedd`** | **30** | the donor's own lightning event reaches our receiver, one per bolt |
| `LIGHTNING arrived` (distance predicate) | 0 | the substitute arrival route never fires |
| `TRANSITION 0x1fc->0x1fd` (finisher) | 0 | Kazap never completes |
| `FAIL` | 0 | no guarded path refused |

## 1. Cause (a) and cause (b) are no longer equally likely: (a) is measured

Every one of the 32 `BOLT` samples reads `move_dist=0.0` against `threshold=300.0` and
`owner_ok=true`:

```
BOLT life=25 move_dist=0.0 threshold=300.0 owner_ok=true x=-11.3 y=85.0
BOLT life=20 move_dist=0.0 threshold=300.0 owner_ok=true x=-11.3 y=85.0
...
BOLT life=0  move_dist=0.0 threshold=300.0 owner_ok=true x=-11.3 y=85.0
```

* **cause (b) is excluded (tier A):** `owner_ok` is `true` on every sample, so
  `owner(w)` resolves the founder and `state::get` returns the owned state. The owner
  lookup is not the fault and must not be "fixed".
* **cause (a) is the fault (tier A):** the engine never accumulates
  `WEAPON_BRAVE_LIGHTNING_INSTANCE_WORK_ID_FLOAT_MOVE_DIST` (0x7) for this cloned article
  on Mythra, while its MapCorrection runs. The arrival predicate in
  `weapon.rs::lightning_exec` therefore cannot fire at any threshold, and Kazap always
  left through `TRANSITION 0x1fc->0x0` at the clip end (5 of 15 here; the other 10 left by
  hit or interrupt).

**A second, larger fact falls out of the same lines: the bolt does not move.** `x` and `y`
are byte-identical across the whole life of a bolt (`-11.3 / 85.0` for the first Kazap,
`-24.6 / 85.0` for the second), and both bolts of a Kazap share one point. `y = 85.0` is
exactly `param_special_s.offset_y_lightning` (0.0 / 85.0, pinned in
`refs/brave_special_s/owned_native_audit.json`), i.e. the spawn point from the owned
native initializer. So `MapCorrection` runs 30 times per bolt and the bolt never leaves
where it was created. This **refutes** the previous report's "bolt travel excluded"
(`RESULT.md` s1, and R-HERO-S-7 in `handbook/graveyard.md`): a MapCorrection frame count
proves the callback ran, not that anything moved.

## 2. The correction: raise the owned arrival flag from the donor's own event

`state.rs` already declares `LIGHTNING_ARRIVED` as the owned replacement for the donor's
"has the bolt struck" query, and `fighter.rs::loop_attack3` waits on nothing else. The
implementation raised it from the bolt's `FLOAT_MOVE_DIST`, which section 1 shows is dead.

The donor's actual query is visible in this same log: `EVENT begin kind=0x214e64eedd`
appears **30 times for 30 bolts**, always with `status=0x1fc` (our third attack), always
arriving at the bolt's end of life. That is the event
`refs/brave_special_s/link_event_native_audit.json` documents (lightning class callback
`0x33caa70` sends it; Hero's receiver recognises it and enters `0x85593c`), and it already
reaches our approved `Mythra +0x170` wrapper.

Change made, in `src/pgwr/plugin/src/mythra/hero_side_b/receiver.rs` only:

* after the owned translation returns, when `kind == 0x214e64eedd` and the owner is in
  `ATTACK3` and `lightning_count > 0` (our own per-move spawn counter, cleared by
  `state::start`, so a bolt left over from an earlier move cannot raise it), set
  `LIGHTNING_ARRIVED` once and log `EVENT arrival kind=0x214e64eedd bolts=N frame=F`.

Why this and nothing else:

* it is **owned** - one bit in our own state, the same bit the loop already reads;
* **no donor work id** is read or written by the new code;
* **no distance signal is invented** - the threshold stays at 300 and the predicate stays
  as it is, because with a bolt that never moves *every* threshold is a guess and a firing
  predicate would report an arrival that has not happened;
* **no new interception** - this is the slot the previous run already patched, and the
  event already arrives through it;
* the three suppression paths each log their reason, so "nothing happened" can never be
  mistaken for "nothing was tried".

Tier **D** until hardware: that the finisher now runs and looks right. What the log
*does* establish (tier A) is only that the event arrives once per bolt.

## 3. The travel defect is now measured, not assumed - and it is not fixed here

Rule 11 allows one state-changing change per hardware test, so the bolt-not-moving defect
got diagnostics, not a fix. `weapon.rs` gained `bolt_work()`, which prints the bolt's own
cloned work layout (pinned `lua_const`, tier C: `FLOAT_HEAD` 0x3, `FLOAT_TAIL` 0x4,
`FLOAT_DIR` 0x6, `FLOAT_MOVE_DIST` 0x7) at the bolt's Main and in each bounded `BOLT`
sample. Those are the values the donor's extension machinery reads and writes, so one run
now separates:

* `head`/`tail` frozen while `MAP` runs -> the owned copy of `main+0x33cabd0` is not
  writing them, and the travel bug is inside that copy;
* `head`/`tail` growing but `x`/`y` still frozen -> the bolt extends along its own head/tail
  (it has both, and a `DIR`), the anchor position is *meant* to stay put, and the defect is
  only the missing `FLOAT_MOVE_DIST` accumulation - in which case the distance predicate
  becomes repairable with a measured value instead of a guess.

Until that log exists, whether the Kazap bolt *should* translate or extend is tier D, and
this report does not claim either. A note worth keeping: `state::CALL_EXPLOSION` is read
and written by `native_context.rs` but **set by nothing in the port**, so the donor's
explosion branch in the same map correction cannot currently fire; that is the next
discriminator after travel, and it is out of this task's scope.

The Zapple change (`rot_z 0 -> -90` on `brave_lightning2_swordspark`, shipped in 0.20.17)
is untouched by this run. **Its orientation is still unverified** - the log cannot see
effect orientation, only the user's eye can.

## 4. Build identity

| | |
| --- | --- |
| version | `0.20.17` -> `0.20.18` (`src/pgwr/plugin/Cargo.toml`, rule 6) |
| command | `cargo skyline build --release --features snake-neutral-b,hero-side-b` from `src/pgwr/plugin` |
| cargo cache | `builds/.cache/pgwr-heroside-target` (absolute `CARGO_TARGET_DIR`; the documented relative form resolves to `src/builds/`) |
| result | `Finished release profile in 17.69s`, **no errors**, pre-existing warnings only |
| NRO | `builds/.cache/pgwr-heroside-target/aarch64-skyline-switch/release/libpyra_gamewatch_reskin.nro` |
| bytes | 466944 |
| sha256 | `62c36331435fbefa247a18699aa90c151f0a09aa5e7804c806697afceb09ee7e` |
| marker strings in the NRO | `EVENT arrival kind=` 1, `head=` 1, `BOLT life=` 1, `APPEND lightning arrived` 1, `brave_lightning2_swordspark` 1, `0.20.18` present |
| installed 0.20.17 NRO | `22bfbd01421280f61c15bdde54b9674df87e9beeccd28108f3a1bdeef960f901` |

**A new binary, so this is not an asset-only delta**; it must be installed without
`--reused-nro`. It is **not packaged and not installed** (AGENTS.md rule 23): the handoff
is the T-0052 section of `CURRENT_INSTALL.md`.

## 5. What is still unverified

* No console run, no emulator, no automated game tests (benched by the user's policy).
* That the finisher now plays: tier D. The event arriving is measured; the status change
  it causes is not.
* That the Zapple bolt points forward: unchanged tier D, still the user's eye.
* Whether the bolt travels at all: the position evidence is tier A, the *cause* is not
  diagnosed; `head`/`tail`/`dir` are new in this build and unobserved.
* The `Mythra +0x170` receiver slot remains formally unconfirmed in
  `CURRENT_INSTALL.md` / `refs/brave_special_s/native_dependency_audit.json` (three
  authorised sites listed). **This run adds, removes and alters no hook**; it only adds
  behaviour inside the already-patched wrapper.

## 6. Manual checks (send `sd:/ultimate/pgwr_hero_s_log.txt` **from boot**)

1. Boot. First line `[PGWR-HERO-S] BOOT v0.20.18` - that string is how you know this build
   is the one under test. Same four READY/REGISTERED lines as before. Any `FAIL` = stop.
2. Vanilla control: Mythra c00 side-B is her Ray of Punishment; no `[PGWR-HERO-S] ENTRY`.
3. No-regression on Zap: Mythra c06 (or Pyra c06 then down-B), tap side-B under 9 frames.
   Expect `TRANSITION 0x1fe->0x1fa`, `SPAWN spark ... count=1`, `SPARK special_s1`.
4. Zapple: hold side-B to ~0.5 s. The forward-running lightning from the blade must point
   **forward**. Expect `TRANSITION 0x1fe->0x1fb` and `SPARK special_s2`. Report which way
   the bolt points - this is the pass/fail for the 0.20.17 fix.
5. **Kazap (the change in this build):** hold to the max flash. Expect
   `->0x1fc`, `ACTIVATE lightning frame=10`, `SPAWN lightning`, `BOLT` lines, then
   `EVENT begin kind=0x214e64eedd`, then **`EVENT arrival kind=0x214e64eedd bolts=N frame=F`**,
   then `APPEND lightning arrived; switching to the finisher`, then
   `TRANSITION 0x1fc->0x1fd` - and the finisher must visibly play.
6. If instead you see one of these, it is the discriminator, not a vague failure:
   `EVENT arrival suppressed: owner is not in the third attack` / `... no bolt counted for
   this move` / `EVENT arrival already raised; ignored`.
7. Report the `BOLT` `head=`/`tail=`/`dir=` numbers and whether `x`/`y` change over the
   bolt's life. Constant -> the extension machinery is not writing them. Growing -> the
   bolt extends and only `move_dist` is missing.
8. Repeat 3-5 in the air, facing both left and right, and on c07.
9. Regression: Mythra c06 neutral-B (Hero fireball) and up-B (Hero spin) still work; Pyra
   c06 side-B unchanged; Snake neutral-B and Monkey Flip untouched.