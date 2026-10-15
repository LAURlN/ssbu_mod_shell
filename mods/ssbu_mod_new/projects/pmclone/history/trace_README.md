# Trace recorder diagnostic v0.1.1

This is a first hardware test, not a playable clone or a proven frame-exact
recorder. M0 is incomplete until repeat playback produces valid, identical traces
and a controlled change is detected. No hardware results exist for this build.

## Install and remove

Use `test_output/PyraMythra_trace_check.zip`. With Smash fully closed, copy its
`atmosphere` folder to the SD root. The only plugin added is
`atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpmclone_trace.nro`.
Skyline and the existing compatible Smashline plugin are prerequisites; neither
is replaced or bundled. Do not install the moveset crate or a clone for this test.
Avoid other input/gameplay hooks (including Training Modpack) for the baseline.
Remove this NRO and restart Smash to uninstall; recorded files can be retained.

The packager also publishes that single NRO to `mod_output/new_standalone`.
That folder contains older loader-test files: use the ZIP to isolate this test.
The development tools never write to the SD card.

## First Switch test

1. Start Training mode with normal Mythra and a standing CPU on a flat, hazard-free
   stage. Use normal speed, default taunt mappings, no items, both fighters grounded,
   and put the CPU out of attack range. Start at 0 percent. Do not pause, reset,
   change speed, swap forms, or exit Training during a capture.
2. Tap D-pad up, release it, and wait one second. Perform a short neutral attack
   sequence, wait until idle, then tap D-pad down. Up arms for 30 input calls and
   then records; down stops. There is no on-screen recorder indicator yet.
3. Tap D-pad left and release it. This replays the last recording and automatically
   stops at its end. Wait longer than the original recording, then repeat left
   once more. Both replays must start in Mythra form with the same fighters present.
4. Close Smash before collecting files. Copy `ultimate/pmclone_trace/` back to the
   PC, especially `pmclone_trace.log`, `inputs/` and `traces/`. Keep the build hash
   from `trace-build.json`. If Smash crashes, retain the matching Atmosphere report.
5. Compare the two `*_play_last.trace.csv` files (different numbered prefixes):

   ```powershell
   python pyra_mythra_clone/tools/trace_diff.py PATH_TO_FIRST_PLAY PATH_TO_SECOND_PLAY --ignore none --json replay-diff.json
   ```

   Exit 0 means identical **captured fields**. Exit 1 reports differences; exit 2
   means unusable input, including an unfinished or invalid recorder session.
   Also compare the original `*_rec.trace.csv` against the first playback.
   Send all three traces and the log even if they differ; do not hide fields or
   increase tolerance to make the baseline pass.

Taunt commands are active in Training only: up record, left replay, down stop,
right replay with one input frame replaced by neutral. Captures are capped at
3600 input calls (about one minute at 60 calls/second). Inputs are stored as
`inputs/NNNN.inputs` and `inputs/last.inputs`. No Training Modpack is required.

## Controlled difference test (after baseline passes)

The right-taunt test changes input, not a gameplay parameter. Choose an attack
press or nonzero stick frame in `inputs/last.inputs`, counting `i` lines from zero.
Write `frame N` in `ultimate/pmclone_trace/perturb.txt`; default N is 60. The selected
input must be non-neutral and within the recording or playback is refused.
Tap right to create a `*_perturbed.trace.csv`. Compare against an ordinary playback;
expect a reported divergence if that input affected the move. Removing a buffered
or redundant input may legitimately leave state unchanged. A deliberate gameplay
parameter change remains a separate, future M0 acceptance test.

Optional `play.txt` contains a plain filename such as `0001.inputs` to select an
older recording. Omit it to use `last.inputs`. Do not hand-edit input start states.

## What is captured, and what is not

The CSV header matches `HANDOFF_WEAK_MODEL.md`. Rows are sampled by Smashline Main
callbacks and grouped between the selected controller's input-mapping calls.
That timing is experimental: it has not been proved to equal every simulation
frame, especially during hitstop. Pausing, missing callbacks, duplicate callbacks,
missing fighter slots, file errors, and leaving Training invalidate the session.
A completion footer records frame/row totals; the PC tool rejects incomplete files.

- Fighters: status, situation, motion/hash/frame/rate, position X/Y, facing, damage,
  enabled kinetic-energy X/Y speeds plus summed speed, selected instance work.
- Articles with resolvable fighter owners: status/motion/position, summed speed,
  LIFE, hitboxes. Raw battle-object IDs sort same-kind instances into `#0`, `#1`,
  etc. These are per-frame ordinals, not persistent spawn identities.
- Attack IDs 0..7: fields from the pinned skyline-smash `AttackData` layout.
  Part is a placeholder zero. Additional bone/attribute/hitlag/SDI fields are in
  `work`. This is not full collision state or all hitbox parts.
- `hitstop` is a boolean `StopModule::is_stop`, not remaining hitlag frames.
- Missing coverage: per-joint hurtboxes, shield stun, status work/int64 work,
  weapon per-energy state, unobserved inactive partner objects, RNG, and hidden
  engine state. Inactive forms appear only if their Main callback executes.
- Start restoration covers position, facing, damage, speed clearing, and WAIT.
  It does **not** restore a full save state, RNG, stale moves, articles, shield,
  CPU state, hidden partner state, or every WorkModule value. Equal replays are
  an experiment to run, not a guarantee of this reset strategy.
- Only one human controller is replayed. Use a standing CPU for the smoke test.
  Clone fighter naming has a base-kind adapter; clone article naming is unfinished.
  Instance work includes IDs/timers that may expose additional reset/normalization
  requirements; do not ignore them without an explicit review.

## Build and verification

From `trace/`, with Cargo on PATH:

```powershell
$env:CARGO_NET_OFFLINE = 'true'
cargo skyline build --release
```

From the workspace root:

```powershell
python -m unittest pyra_mythra_clone/tools/test_trace_diff.py pyra_mythra_clone/tools/test_trace_recorder_contract.py
python pyra_mythra_clone/tools/package_trace_check.py
```

The packager verifies the input signature occurs exactly once at main+0x1750f70
in the local dump, checks the two manually declared native symbol names, validates
NRO magic/source freshness, and verifies packaged bytes. These static checks do
not establish ABI correctness or match the live process build ID. Runtime hooking
is refused unless the signature matches uniquely at the expected offset.

Input-hook reference: [UltimateTrainingModpack mapping hook](https://github.com/jugeeya/UltimateTrainingModpack/blob/main/src/training/mod.rs)
and [signature definitions](https://github.com/jugeeya/UltimateTrainingModpack/blob/main/src/common/offsets.rs).
Struct reads use the locally pinned skyline-smash 315e4e8 bindings; callback
registration uses Smashline be3ef30. Dependencies remain locked in Cargo.lock.
