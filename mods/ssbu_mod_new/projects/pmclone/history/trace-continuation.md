# Recorder continuation — 2026-09-28

The pasted handoff predated source already present in `trace/`. Existing work
included mapped-input replay, native binding reads, generated instance-work IDs,
and an old compiled NRO, but no recorder README or package.

## Changes

- Version 0.1.1; runtime input hook now requires the unique signature at the
  expected 13.0.4 offset instead of installing at an unexpected address.
- Article-owner resolution accepts battle-object ID zero when the engine says
  it is active. Active-fighter lookup failure no longer treats both forms as active.
- Sessions reject missing/duplicate callbacks and missing fighter slots; missing
  start-roster members, invalid playback start values, and unsuitable perturbation
  frames are rejected. Captures are capped at 3600 input calls.
- Checked row writes/flushes, input saves, and counter writes; exclusive trace
  creation prevents accidental overwrite if counter state is lost. Completion
  footers distinguish finished traces from interrupted or invalid recordings.
  Exiting Training finalizes as invalid when observed by the hook/callback.
- PC diff retains float strings, handles NaN and signed zero correctly, rejects
  duplicate compound keys, empty traces, and invalid/incomplete recorder captures.
  Footer counts must agree with contiguous observed frame numbers.
- Added regression tests, standalone local packaging/static validation, and
  installation/removal/test instructions. Existing loader and moveset code untouched.

## Verification actually run

`cargo skyline build --release` in `trace/`, with Cargo on PATH and
`CARGO_NET_OFFLINE=true`: successful optimized build, final compile 5.53 seconds.
`cargo skyline build --release --offline` was rejected by cargo-skyline's argument
parser; the environment variable is the working offline mechanism.

`python -m unittest pyra_mythra_clone/tools/test_trace_diff.py pyra_mythra_clone/tools/test_trace_recorder_contract.py`:
19 tests passed. The malformed-input message printed during this suite is expected.

`python pyra_mythra_clone/tools/package_trace_check.py`:
signature unique at `0x1750f70`; both manually declared native symbol names present
in the local main image; NRO magic/source freshness and ZIP readback passed.
NRO: 167936 bytes, SHA-256
`2b54f5cb0edb54411bacee3bfac67525f67eecf812a7b7199815d15bdaa99945`.
Full source/build hashes are in `trace-build.json`.

After the report/build, at the user's explicit request, the NRO was copied to
`sd:/atmosphere/contents\01006A800016E000\romfs\skyline\plugins\libpmclone_trace.nro`.
Source and SD SHA-256 both equal
`2b54f5cb0edb54411bacee3bfac67525f67eecf812a7b7199815d15bdaa99945` (167,936
bytes). Read-only CHKDSK reported no file-system problems. No console run was
performed; Rust session behavior has not been exercised on hardware. The PC tests
cover comparison/parsing, not native ABI safety.

## Remaining acceptance gates

1. Verify plugin loads and callbacks/input mapping produce valid traces on console.
2. Verify repeated playback and original recording compare identically, including
   hitstop scenarios; establish hook timing instead of assuming one call = one frame.
3. Detect a known input change; separately add the originally requested controlled
   gameplay-parameter change test. Current right-taunt mode changes an input only.
4. Complete/reset unmeasured state where evidence requires it: RNG, per-joint
   hurtboxes/shield stun, status work, inactive partner sampling, article identities,
   and full replay start state. Existing reset covers only a subset.

M0 remains incomplete. A successful compile or fixture comparison does not prove
the recorder is frame-exact or a future clone is behaviorally identical.
