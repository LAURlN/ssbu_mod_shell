# Recorder freeze on D-pad up — incident report, 2026-09-28

First hardware run of the trace recorder. The game froze partway through the
arming phase and no trace was produced. M0 remains open.

## What the user reported

Training mode, normal Mythra, standing CPU out of attack range. Pressing
D-pad up froze the game. No trace, no playback, no crash dialog.

## Evidence collected

Preserved under `reports/console-2026-09-28-freeze/`.

- `pmclone_trace.log`, written 21:51:02, three lines and nothing more:
  - `pmclone_trace v0.1.1 loaded`
  - `input hook: final input mapping at main+0x1750f70 (13.0.4 expects 0x1750f70, match)`
  - `record requested; arming`
- **No crash report exists for this run.** The newest Atmosphère report is
  15:02:08, roughly seven hours *before* the recorder was installed at 21:35,
  and no report mentions the recorder.
- That stale 15:02 report is a different failure entirely: a data abort in
  `ssbu_clone_engine` (`weapon_preload_probe` → `custom_article_data_cache_insert`
  → `model_build_probe`, null deref at 0x0). It belongs to the earlier
  private-module work and must not be read as evidence about this freeze.
- The old private module loader (`/f/ultimate/mods/PyraMythraClone`, `plugin.nro`)
  is still installed and still active; it wrote `loader.log` at 21:49:50 during
  the same session. It reports "no fighter installed", so it is not the cause,
  but it is a live confound and was not isolated out of this run.

Absence of a crash report is itself the key signal: this was a lockup, not a
fault. A data abort would have produced an Atmosphère report.

## Root cause

`SESSION` is a `std::sync::Mutex`, which is **not reentrant**.

`on_fighter` runs from each fighter's Smashline Main callback. It took the
`SESSION` lock and then, still holding it, called `arm_fighter`, which called
game-mutating APIs:

- `StatusModule::change_status_force` / `change_status_request` — forcing WAIT
  on the final arm frame re-enters the fighter's status-change path, which
  re-enters the Main line, which calls `on_fighter` again on the *same thread*.
- `DamageModule::heal` / `add_damage` and `KineticModule::clear_speed_all` —
  can spawn or refresh articles, which re-enters `on_weapon`, same thread.

The re-entrant callback tried to lock the already-held non-reentrant mutex and
blocked forever. Every game thread touching a fighter then blocked, so the game
froze with no exception — exactly the observed symptom, and exactly why no crash
report was written.

`ARM_FRAMES` is 30, so the freeze lands about half a second after the press, on
the frame that forces WAIT. That matches "froze when I pressed D-pad up".

## Fix

The arm path is now two-phase, in `trace/src/session.rs`:

- `plan_arm` runs with `SESSION` held and may only **read** fighter state. It
  records start state and returns an `ArmAction` describing the writes needed
  (`pos`, `lr`, `damage`, `wait`).
- `apply_arm` performs those writes with `SESSION` **released**.
- `on_fighter` scopes the lock to the planning block and applies afterwards.

Added as defence in depth, since any future in-lock game call would reproduce
the same hang:

- A thread-local `IN_HOOK` re-entrancy guard (`enter()` / `HookGuard`) at the
  top of `on_input`, `on_fighter`, `on_weapon` and `leave_training`. A
  re-entrant callback now returns immediately instead of deadlocking or
  recursing. The training-mode check stays ahead of the guard so
  `leave_training` still works when leaving Training.

Semantics are unchanged: the same writes happen, in the same order, with the
same values and the same `left <= 1` force-WAIT rule.

## Verification

- `cargo skyline build --release`: success.
- `python -m unittest tools/test_trace_diff.py tools/test_trace_recorder_contract.py`:
  19 tests, OK.
- `python tools/package_trace_check.py`: signature unique at 0x1750f70, native
  symbol names present, package and readback verified.
- New NRO SHA-256 `d924a4c17e4ad709ce9e27d473edcd8008c67f269f505be2e5f52a45845b650e`,
  167,936 bytes, deployed to
  `atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpmclone_trace.nro`
  and read back with a matching hash.

All of the above is PC-side. The freeze is **not** confirmed fixed; that needs
the same console test again.

## Run 2 — freeze fixed, now blocked on file creation

The user re-ran the test against the deployed fix.

**The freeze is gone.** Arming completes, the session advances out of `Arming`,
`next_number` runs, and the recorder reaches file creation. No hang, no crash
report. The re-entrancy fix holds on hardware.

New failure, logged twice (sessions 1 and 2):

```
session 1: cannot create sd:/ultimate/pmclone_trace/traces/0001_rec.trace.csv: Result code: 514
play refused: cannot read inputs/last.inputs: Result code: 514
session 2: cannot create sd:/ultimate/pmclone_trace/traces/0002_rec.trace.csv: Result code: 514
```

The `play refused` lines are correct behaviour: no recording was ever made, so
there is no `inputs/last.inputs` to read.

`Result code: 514` is `0x202`, FSS module 2 description 1, i.e. **PathNotFound**.

The interesting part is what does and does not work:

| Path | Result |
| --- | --- |
| `pmclone_trace/pmclone_trace.log` (append, boot) | works |
| `pmclone_trace/counter.txt` (write, each session) | works |
| `pmclone_trace/traces/0001_rec.trace.csv` (create) | **514** |
| `pmclone_trace/traces/0002_rec.trace.csv` (create) | **514** |

`traces/` physically exists on the card (created 22:07:40) and is still empty
after two attempts. So the directory is there at the FAT level but does not
resolve through FSS when a file inside it is opened. Writing straight into
`pmclone_trace/` works every time, including files written by the same session
moments earlier. Depth two resolves; the runtime-created depth three does not.

Most likely: a directory created after the SD mount is opened is written to the
volume but not registered in FSS's path resolution for the live mount.
`pmclone_trace` itself was also created at runtime but is only one level below
an existing directory, which appears to still resolve.

**This is a hypothesis, not a proven mechanism.** It is consistent with every
observation, but it has not been confirmed on hardware.

## Second fix (instrumentation only)

- `begin` no longer discards the `create_dir_all` result (`let _ =`). That
  discard is why the first run gave no clue about the 514. It now goes through
  `ensure_dir`, which logs the real error.
- `prepare_dirs` creates `pmclone_trace/`, `traces/` and `inputs/` at plugin
  init, the earliest point available, and logs each result.

Note the directories also already exist on the card, so the next run tests the
"exists before mount" case as well.

Verification: build succeeded, 19 tests pass, package/readback verified. New NRO
SHA-256 `1ceb626537bbecb4ec7cc731bde770627519c1df14dfb14d809647e8a38666c7`,
167,936 bytes, deployed and read back matching.

## Run 3 — the FSS hypothesis was WRONG

The new build logged the directory results, and they refute the theory outright:

```
pmclone_trace v0.1.1 loaded
dir ready: sd:/ultimate/pmclone_trace
dir ready: sd:/ultimate/pmclone_trace/traces
dir ready: sd:/ultimate/pmclone_trace/inputs
input hook: final input mapping at main+0x1750f70 (13.0.4 expects 0x1750f70, match)
record requested; arming
session 3: cannot create sd:/ultimate/pmclone_trace/traces/0003_rec.trace.csv: Result code: 514
```

All three `create_dir_all` calls returned **Ok**, including `traces/`. The
directory resolves perfectly well. Creating a *file inside it* is what fails.

That kills the "unregistered runtime directory" theory and moves the fault to
the file open itself. Which leaves exactly one distinguishing input: the open
mode. Every working write in this plugin uses a non-exclusive create.

| Call | Flags | Result |
| --- | --- | --- |
| `boot_log` → `pmclone_trace.log` | `.append(true).create(true)` | works |
| `fs::write` → `counter.txt` | `.create(true).truncate(true)` | works |
| `begin` → trace CSV | **`.create_new(true)`** | **514** |

`create_new(true)` is `O_EXCL`. It is the only exclusive create anywhere in the
plugin, and the only one that fails. It was introduced to implement the
"refuse to overwrite an existing trace" guarantee.

Note that this also explains the depth observation from run 2 that misled me:
the working writes were all *directly* in `pmclone_trace/`, so nesting was a
confound, not the cause. Nothing about subdirectories was ever wrong.

## Third fix

Exclusive create is dropped, but the guarantee it provided is kept:

- Open with `.write(true).create(true).truncate(false)` instead of
  `.create_new(true)`.
- After opening, check the file length. Non-zero means a trace is already
  there, so log `refusing to overwrite existing ...` and abort the session —
  the same outcome the old code produced, reached without `O_EXCL`.

The length check is not atomic against a concurrent writer. That is acceptable
here and is worth stating rather than hiding: trace names are session numbered
from a single counter and only one human controller can record at a time.

Verification: build succeeded, 19 tests pass, package/readback verified. New NRO
SHA-256 `7ff072069ab6c8ba31cde6054c9095e2e23d1d2276f019c0ac318c41f15bcb5e`,
167,936 bytes, deployed and read back matching.

Still unproven on hardware. If the 514 persists with `O_EXCL` removed, then the
Horizon SD path is refusing the *filename* rather than the mode, and the next
thing to try is a shorter, simpler name.

## Run 4 — all three blockers cleared, first real capture

```
session 4 started: Record -> sd:/ultimate/pmclone_trace/traces/0004_rec.trace.csv
session 4 INVALID: duplicate object callback in frame 212
session 4 finished (duplicate object callback in frame 212): Record, 213 frames, 640 rows
```

Three rounds of blockers are now confirmed fixed on hardware:

- **No freeze.** The arming deadlock fix holds.
- **The trace file opened and was written**: `0004_rec.trace.csv`, 908,486 bytes.
  Exclusive create (`O_EXCL`) was indeed the cause of the 514.
- **The per-frame row flush works.** 640 rows across 213 frames, no hang. The
  SD-I/O-under-the-lock hazard did not materialise at this scale.

This is the first genuine state capture: three objects tracked for 213 frames
(`fighter:elight` in slot 0, `fighter:k48` CPU in slot 1, and
`article:elight_esword#0` present for all 213 frames), with the full work-value
column populated. Preserved under `reports/console-2026-09-28-run4/`.

### New finding: the Main line fires twice per frame on a status change

Frame 212 sampled `fighter:elight` twice:

```
row 643: status=0   motion=0x047dee83e5  motion_frame=54
row 644: status=39  motion=0x099c52257e  motion_frame=0
```

Status 39 at motion frame 0 is a status *transition* observed mid-frame. So
Smashline's Main line runs once for the regular per-frame update and again when
the fighter's status changes. The two calls are sequential, not nested, so the
`IN_HOOK` re-entrancy guard correctly did not suppress them.

The recorder's one-row-per-object-per-frame model was wrong. It invalidated
every capture containing a status change, which is every capture containing an
attack, which is the entire point of the tool.

Status 39 is not identified. The trace records raw numeric status and there is
no status-kind name table, which is a readability gap of its own.

### Second finding: the capture was static

Mythra stood still for all 213 frames: one motion, `x` pinned at `-35.999996`,
status 0 throughout, only the motion counter incrementing. The CPU barely moved.
**No attack sequence was captured**, so even a valid trace would have compared
nothing.

This could not be diagnosed, because the invalidation also skipped
`save_inputs`, so no `inputs/last.inputs` existed and the three `play refused`
lines were correct behaviour. The two problems compounded: the capture failed
*and* took the evidence for why with it.

## Fourth fix

- **First-wins duplicate handling.** `flush_rows` keeps the first row for a given
  `(slot, object, order)` and counts the rest, instead of invalidating. The
  sort is stable so the regular per-frame sample is the one kept, and the rule
  is identical in recording and playback, so a real difference still surfaces.
  `order` stays in the key because several articles of one name legitimately
  share a slot and object and are distinguished by battle object id. The count
  is logged at session end rather than silently swallowed.
- **Invalid sessions still save their inputs.** Without this, a bad capture also
  destroys the evidence needed to explain it, and playback can never be
  exercised. A save failure is logged without overwriting the reason the trace
  was already invalid.

Verification: build succeeded, 19 tests pass, package/readback verified. New NRO
SHA-256 `9616a6a71fd98686f25f1ae21d7a2c29ee57a401d87d1b06bd958c9090dc8db5`,
167,936 bytes, deployed and read back matching.

Still unverified on hardware. The next run should produce a *complete* trace
from an actual attack sequence, plus a playable `inputs/last.inputs`.

## Run 5 — first complete M0 dataset, and the control fails

All three sessions finished clean, no `INVALID`:

```
session 5 started: Record   -> 0005_rec.trace.csv
session 5: 3 extra Main callbacks dropped (first-wins)
session 5 finished (stopped by user): Record, 318 frames, 954 rows
session 6 started: Play     -> 0006_play_last.trace.csv
session 6: 6 extra Main callbacks dropped (first-wins)
session 6 finished (end of inputs): Play, 318 frames, 954 rows
session 7 started: Play     -> 0007_play_last.trace.csv
session 7: 9 extra Main callbacks dropped (first-wins)
session 7 finished (end of inputs): Play, 318 frames, 954 rows
```

Footers all read `# complete frames=318 rows=954`. `inputs/0005.inputs` and
`last.inputs` were written, so playback ran for the first time. Preserved under
`reports/console-2026-09-28-run5/`.

The fourth fix is confirmed: 3, 6 and 9 extra callbacks were dropped instead of
invalidating. This also confirms the run 4 diagnosis, because status 39 turns out
to be the attack status (below) and every extra callback lands on an attack.

**The attack landed this time.** Mythra left WAIT at frame 132 and stayed in
status 39 for 98 frames (132-229) on motion `0x099c52257e`. That is the same
motion hash seen in run 4's frame-212 duplicate, so run 4's invalidation was
caused by the attack itself changing status, exactly as theorised.

### The comparison, and why it is not yet interpretable

| Comparison | Differences | Of |
| --- | --- | --- |
| recording vs playback 1 | 707 | 1414 |
| **playback 1 vs playback 2 (control)** | **652** | 1304 |

The control replays the *same inputs* twice. It is not clean either, and it
carries almost all of the signal. So the current differences are not evidence
that a replay behaves differently from its recording; they are evidence that two
sessions do not start from the same game state.

The differences decompose exactly:

- **`INT_ATTACK_SERIAL`**, 3 in one playback and 6 in the other, on all 318
  frames. A monotonically increasing attack counter that arming never resets.
  It is the *only* work value that differs between the two playbacks; the set
  of work keys is otherwise identical.
- **`article:elight_esword#0` `motion_frame`**, differing on all 318 frames, with
  `pos_x`/`pos_y` following on 8. The sword's animation phase persists across
  sessions because arming does not touch article state.
- **`fighter:k82` `motion`**, 55 frames, in the recording-versus-playback
  comparison only. The CPU is AI driven and its state is not restored.

`fighter:elight` `motion_frame` is *identical* between the two playbacks on all
318 frames, so the forced-WAIT restart does reset the fighter's animation phase
correctly. The article is the part that does not reset.

### What this means for M0

The milestone as written asks for equal captured fields between a recording and
its playback. That question cannot be answered until the control is clean,
because today the two are not distinguishable. The acceptance gate has to move
one step earlier:

> **Two playbacks of the same inputs must be byte-identical before a
> recording-versus-playback comparison means anything.**

These are all arming-reset gaps, not clone problems, and the handoff already
predicted them: article state, stale moves and CPU state were all listed as
things arming does not restore. The tool is now precise enough to name them
individually, which is the real progress here.

Nothing here was fixed by suppressing fields or loosening tolerance. The
comparison was run at zero tolerance with `--ignore none`, exactly as specified.

## Run 6 — REGRESSION: crash on attack, both new fixes reverted

I introduced this. Two changes went in together to attack the run 5 control
differences, and the next run crashed.

```
record requested; arming
session 8 started: Record -> .../0008_rec.trace.csv
session 8 INVALID: frame 0 has no callbacks; pause, missing Smashline, or timing mismatch
```

Then, on the player's next attack, the game died. Crash report
`01790628549_01006a800016e000.log` at 22:49:16, preserved under
`reports/console-2026-09-28-crash-setframe/`:

```
Type:      User Break          (deliberate SDK assert via nnosBreak, not a fault)
Thread:    MainThread
LR:        nnosBreak + 0x10
  L2CFighterCommon::status_Attack_Main_button     (lua2cpp_common.nrs + 0x7a5d0)
  L2CFighterCommon::status_Attack_Main
  L2CFighterBase::bind_hash_call_call_line_status
  smashline + 0x147a8
```

### What was changed, and why both were reverted

Two things went in together, which was a process mistake: with one data point
there is no way to attribute the fault between them.

1. `apply_arm` zeroed `INT_ATTACK_SERIAL` via `WorkModule::set_int`.
2. `on_weapon` called `MotionModule::set_frame(boma, 0.0, false)` on every
   article while arming.

Both are reverted. The reasoning for each:

- **The article `set_frame` is the better fit for the first symptom.** "frame 0
  has no callbacks" means the smashline Main dispatch stopped producing rows
  before the recording began, which is the weapon Main line. `MotionModule` is
  the *fighter* motion API; articles have a different motion system and the
  correct entry point has not been identified.
- **The serial reset is the better fit for the crash itself.** The assert is in
  `status_Attack_Main_button`, the fighter's attack button handler. Zeroing a
  monotonic serial the game uses for attack bookkeeping is exactly the kind of
  value that must not be zero, and we left it at zero across the whole session.

Neither is proven. Both are recorded as suspects in the source next to the
reverted code so the next attempt does not repeat them blind.

### Honest process note

Shipping two state-mutating changes in a single build, on the critical path,
with no way to attribute a crash between them, is what turned a two-line
diagnosis into a revert. The next state-reset attempt should reintroduce one
change per build.

### Reverted state

Deployed NRO SHA-256
`b0b86987d408281924c32fea9c3f1c9f700950ca6f399b4946110bf15dcf7592`, 167,936
bytes, readback verified. Build clean with no warnings, 19 tests pass, package
verified. Functionally this is the run 5 recorder again, so the control will go
back to roughly 652 differences and no new information is lost.

## Not yet addressed

- **Article animation phase is not reset, and the obvious fix crashes.** See run
  6. `MotionModule::set_frame` on a weapon is not valid; the weapon-specific
  path still has to be found.
- **`INT_ATTACK_SERIAL` is not reset, and zeroing it is suspected of tripping
  an SDK assert** in `status_Attack_Main_button`. If this state ever needs to be
  made reproducible, it needs a valid non-zero starting value, not zero.
- **The 514 file-creation failure is now fixed and confirmed on hardware.**
  `O_EXCL` was the cause. The earlier FSS-directory theory was wrong and should
  not be repeated.
- **Status kinds are recorded as bare numbers with no name mapping.** Status 39
  could not be identified from the trace, which makes captures hard to read and
  slows down exactly the kind of analysis run 4 needed.
- **No playback has ever run.** It needs one valid recording, which now also
  requires an attack sequence that actually changes state.
- **Synchronous SD I/O still runs while `SESSION` is held.** `begin`,
  `flush_rows` and `finish` do `std::fs` writes from inside the input-mapping
  hook. A slow FAT32 write on the input thread is an independent way to freeze
  the game, and it will bite during recording rather than arming. Refactoring
  the I/O off the lock is the next known hazard and was deliberately not
  attempted blind, alongside the real fixes.
- **Once a trace file finally opens, the row-flush path is untested on
  hardware.** That is where the 64 KiB buffered writes land every frame, and it
  is where the SD I/O freeze hazard above would first appear.
- The old private module loader and `libarcropolis` / `libnro_hook` /
  `libsmashline_plugin` are still live on the card. This run was not a clean
  baseline. Removing or isolating them is the user's call, not this session's.
- The 15:02 `ssbu_clone_engine` crash is a separate, older, unexplained failure.
