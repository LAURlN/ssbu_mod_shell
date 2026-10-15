# dk_cargo 0.1.1-test

Controlled throw-crash retest candidate: `builds/pgwr/dk_cargo-0.1.1-test/`.
0.1.0 hardware: user reports pickup/carry/jumping/release successful; cargo throws
crash. Three reports show a null capture object at native shared-motion lookup.
0.1.1 changes only three owned cleanup comparisons to recognize queued stock
victim roles before owned Pre routing. Build/8448 compiled comparison checks
passed; corrected throws remain unverified. Assets and status IDs unchanged;
shared 0.20.20 / Gaogaen/Snake/Lucas/Ness baseline retained. Current installation
and backup record: CURRENT_INSTALL.md. Frameworks and shared registration unchanged.

Runtime: `src/pgwr/plugin/src/status/dk_cargo/`. Reviewed specification:
`refs/donkey_cargo/ownership_contract.json`; native closure, parameters, exact
victim callbacks and motion-sharing route are pinned there. Task-owned ARM64
callbacks retain C++ status-result ABI and replace donor relocations, IDs,
private storage and fighter-specific helpers. Generic capture/motion engine
interfaces remain dependencies. Pickup preserves actual victim native `thrown_f`
scripts; cargo-specific victim scripts are owned and registered per kind.

`integration.patch` is unapplied: four narrow changes compose registration,
approved +0x170/+0x210 extensions and the existing Gaogaen exported classifier.
Requirement: 15 attacker + 3 victim states per eligible table; 18 on eflame.
Production allocation remains pending. Private `0x400..0x411` is audited above
native counts and disjoint from current shared IDs; do not promote it silently.

Run from the mod root with the already-cached dependencies:

```powershell
python -B src/pgwr/tools/dk_cargo/revision.py check
python -B src/pgwr/tools/dk_cargo/check_transition.py
```

Rebuild the frozen private source without editing it:

```powershell
$cargoTaskRoot = (Resolve-Path builds/.cache/dk_cargo).Path
$env:CARGO_HOME = Join-Path $cargoTaskRoot 'cargo-home'
$env:CARGO_TARGET_DIR = Join-Path $cargoTaskRoot 'runtime-target-0.1.1'
Push-Location (Join-Path $cargoTaskRoot 'test-plugin-0.1.1')
cargo skyline build --release --features snake-neutral-b,hero-side-b -- --offline
Pop-Location
python -B src/pgwr/tools/dk_cargo/revision.py check
```

Check rejects source/artifact drift. Fresh generation order on recorded baseline:
For the narrow 0.1.1 revision, `revision.py prepare` clones the immutable 0.1.0
private source and copies only the two changed cargo files; build as above, then
`revision.py package`. Do not rerun on an already prepared/completed candidate.
The full 0.1.0 asset/runtime generation order was:
param_contract.py, pose_route.py, closure.py, victim_registration.py, ownership.py,
emit_callbacks.py, generate_runtime.py --test-base 0x400, integration.py prepare,
private build, package_assets.py, package.py. Completed packages/snapshots are
immutable; select a new task package/cache name for revisions. refresh-owned is
pre-package repair only, never during compilation. Early check.py/record.py are
research.1 tooling; do not use them to finalize a runtime candidate.

ASSET_DELTA.json records baseline/changed hashes, actual costume-list raw append
rows, config unions, input hashes, local victim clips and full shared templates.
baseline_pins.json and animation/sound/effect audits pin 28 attacker clips, four
bank merges, sequence and two effect merges. Repeat semantic bank merges against
a different collective baseline. Native shared template tracks are all retained
(26 or 67 by body variant); Pickel retains local overlay and metadata. Exact ARC
extraction is under workspace gamedata; dumps remain read-only.

Checks cover private source preservation, 94 owned callbacks, exact 18 victim
slots, ID disjointness, donor import exclusion, syscall guard, list prefixes,
unique aliases, full template tracks, native clip equality, config unions and
append-only bank/sequence preservation. SIMD Vector3 layout warning remains;
verify_linked.py measures this exact linked SIMD return and epilogue. Runtime
ABI is unverified. Host G&W baseline physics remain with owned cargo kinetics
and native 1.1 walk modifiers. Geometry/attachment require console review.

Installer directions and twelve hardware checks with exact diagnostic markers:
evidence/2026-10-03_pgwr_dk_cargo/RESULT.md. Task logging is always enabled at
sd:/ultimate/pgwr_dk_cargo_log.txt. Compilation does not verify capture/release.
No additional reserved hook requirement has been established. Preserved hardware
evidence: evidence/2026-10-03_pgwr_dk_cargo-0.1.0-test_hardware/RESULT.md.
Controlled retest: evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test/RESULT.md.
