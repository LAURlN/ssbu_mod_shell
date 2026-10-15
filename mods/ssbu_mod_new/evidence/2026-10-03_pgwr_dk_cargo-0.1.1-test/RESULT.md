**dk_cargo (2026-10-03, Codex): 0.1.1-test READY for controlled cargo-throw retest; NOT INSTALLED.**

0.1.0 hardware A: user reports pickup, carrying/walking/jumping and grab release
successful; cargo throws crash. All three reports share a null capture object
reference at main+0x483130 during stock victim Thrown motion lookup.
Evidence: `evidence/2026-10-03_pgwr_dk_cargo-0.1.0-test_hardware/RESULT.md`.

Retest package `builds/pgwr/dk_cargo-0.1.1-test/`; NRO
`214dc3126430598fb5e71093f6d5d584e17e662a593b67acf0eb0b777eb66058` (581632 bytes), manifest `144d8a3ee2990a97a04230a860039bbe188a8e4384658b80443066f41da3014d`.
5098 assets unchanged, tree `dae0bff00e20cbe3b5da37215fe82f745ac27c7d8776d180fd08644fc3be6f5e` (sorted path/TAB/hash/LF).
Single behavioral change: three owned End/Exit comparisons accept queued stock
victim carry/thrown semantic aliases so capture can survive to owned Pre routing.
Diagnosis remains D until controlled retest; no claim that throws now work.
Offline B: isolated release build, exact three-call-site delta, 8448 compiled
comparison controls, same assets/IDs, preserved source baseline and NRO checks passed.

Existing shared 0.20.20 / Gaogaen/Snake/Lucas/Ness baseline retained. No live shared
registration or framework changes. Four-file integration.patch still unapplied.
ID requirement unchanged: 15 attacker + 3 victim roles per eligible table, 18 on
eflame; production unallocated, private test IDs 0x400..0x411. Native generic
capture/shared-motion and actual victim native pickup scripts remain dependencies.
Host physics, attachment geometry, all four directional throws and death/swap/
interruption cleanup need hardware verification. No new reserved hook blocker.

Reproduction: `src/pgwr/tools/dk_cargo/revision.py prepare`; private snapshot
`builds/.cache/dk_cargo/test-plugin-0.1.1`, cargo-home under dk_cargo, target
`builds/.cache/dk_cargo/runtime-target-0.1.1`; offline cargo skyline build with
snake-neutral-b,hero-side-b, then `revision.py package`/`check` and
`check_transition.py`. Completed snapshots/packages remain immutable.
Assets inherit 0.1.0 ASSET_DELTA.json; zero new asset/config/motion/bank edits.
Full pins, hashes, controls and test sheet: `evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test/RESULT.md`.

Comparison controls: TRANSITION_CHECK.json evaluates exact compiled scalar
comparison branches, not a game/capture simulation. CHECKS.json includes linked
adapter disassembly. SOURCE.json pins the two changed runtime files and all
unchanged shared files. Native instruction labels/ABI remain; only three BL
targets differ in callbacks.S. Only other change is task boot version 0.1.1.

Reproduce existing candidate: python -B src/pgwr/tools/dk_cargo/revision.py check;
python -B src/pgwr/tools/dk_cargo/check_transition.py. Build command/source/cache
are in SOURCE.json and BUILD.txt in package. No build was run on shared source.

Controlled hardware retest:

1. Boot marker 0.1.1, baseline pickup/carry/jump/escape on c06/c07 unchanged.
2. Ground forward/back/up/down throws, both facings: victim stock c7 -> owned411
   route, advancing attacker/victim clips and exactly one actual release.
3. Repeat four directions airborne; landing/recovery/control restored.
4. Vanilla DK/Pyra controls and unrelated throws; then interruption/death/swap
   cleanup and the complete twelve-step 0.1.0 checklist. Return log from boot and
   crash reports. If earlier crash/new failure occurs, revert to backed-up 0.1.0
   and record the control before another variant. No causality claim yet.
