# gaogaen_throw_b — READY for collective integration — 2026-10-02

Recipient: **G&W / eflame c06/c07**. This is READY as an owned source and checked asset
package for collective integration. No live registration, installation, SD access,
emulator/game run, framework change, branch, commit, push or shared release bump was
made. Runtime behavior remains unverified. The collective installer must assign one
custom eflame status and compile the combined plugin before this can be installed.

## Package and checked handoff

Package: `builds/pgwr/gaogaen_throw_b-0.2.0/`.

| artifact | SHA256 |
| --- | --- |
| PACKAGE.json | `f57c63887f55407fb17c643be4a4051fc39ec7d607d291ccd0ce9f61ead9b0f9` |
| compile-only-disabled/libpyra_gamewatch_reskin.nro | `bb2eca782b92010f748e606ed841d208f60e8bf3579fdf820f1a985f41e9e3a0` |
| integration.patch | `fbb7ac52a7dd9bd1c28550aa1a7236bf3878dbf9fd94e8ad519af2ffd936e422` |

The package manifest pins task payload/source hashes, private build snapshot, registration
baselines and the 0.20.20 merge baseline. `ASSET_MANIFEST.json` keeps the original
0.20.19 delta baseline. Replay changes into an installer-owned tree with the semantic
merger; do not copy premerged baseline banks/lists/config over current collective files.

Offline checks passed:

- Isolated Cargo release compile against current collective 0.20.20 source, features
  `snake-neutral-b,hero-side-b`; completed in 11.20 seconds. Compiler warnings,
  including `Vector3` improper FFI layout, are preserved in `BUILD_LOG.txt`.
- Runtime-source equality and all 94 fighter-kind/table rows and 282 exact offset
  float bits: `runtime_package.py --check`.
- Baseline/payload hashes and original 0.20.19 semantic replay; current 0.20.20
  preservation for every prior motion entry, sound sample/tone/label and config value.
  Duplicate merge rejection left all smoke destination bytes unchanged.
- Native route/parameter/expression instructions and donor collision call graph;
  current narrow source patch passed `git apply --check` and remains unapplied.
- Built and packaged disabled NRO byte equality. The recorded `PGWR_GAOGAEN_THROW_B_STATUS`
  was unset, so this NRO disables this move and is **not installable**.

## What the source ports

Owned files:

- `src/pgwr/plugin/src/acmd/gaogaen_throw_b.rs`
- `src/pgwr/plugin/src/status/gaogaen_throw_b.rs`
- `src/pgwr/plugin/src/status/gaogaen_throw_b_data.rs`

The four pinned donor scripts retain exact game/effect/sound/expression commands. The
throw absolute has damage 0, angle 47, KBG 340, BKB 57, LR_CHECK_B. Frame 28 creates
the 14-damage capsule and sets finish camera (-4,5); 29 clears it; 30 applies the
absolute to saved target object/group/hit number; 50 reverses LR. Effects and all six
sound/voice tones are owned/declared for c06/c07. The two raw cursor commands resolve
to generic ordinary cursor/name-cursor flags (`0x20000030/31`). No Incineroar-only
sound, effect, work ID or specializer is called on eflame.

The copied attacker animation owns motion kind `pgwr_gaogaen_throw_b` and file
`pgwrgaogaenthrowb.nuanmb`. 76/123 transform tracks are retained; 47 unused donor
facial/tail/toe tracks are omitted. The existing eflame clip is used only for c06/c07.
Motion, sound and config changes are additive.

The status router reads stock `throw_b`, retains throw direction work for the native
common initializer, and plays the owned attacker motion. The shared initializer sends
the normal `throw_b` link event with target ids, selecting victim `thrown_b`. The pinned
common victim routine calls `CaptureModule::thrown` on the victim, selects/maintains
its victim clip/link, applies flip and scale, requests thrown offsets, then updates the
constraint translate offset. The candidate supplies all victim back offsets from the
pinned donor table inside that owned victim-init window; it leaves native flip/scale,
base offset combination and cleanup intact. The generic throw-status predicate bridge
recognizes the custom attacker status and its linked victim. End calls common throw
cleanup and restores owned attacks/invincibility state.

`COLLISION.json` audits the bounded native `game_throwb` function and pinned script:
one ordinary attack setup is called and immediately made catch-only; two other setup
calls define throw/catch absolutes. The donor contains **no non-catch-only collateral
box**, so none is fabricated or needed from the donor source.

Revenge audit: donor native code has a THROW-related Revenge-off branch, but no
Revenge system is enabled on the recipient. Intended behavior is the **unboosted vanilla
throw**. No Gaogaen Revenge flags/timer/rate/specializer are copied. Runtime effects,
voice playback, launch and camera behavior remain unverified.

## Allocation, integration and limits

The collective installer must choose **one unused eflame custom status ID**, after
checking DK cargo and every other reservation. This task deliberately selects no shared
number. Set that collectively assigned decimal value as
`PGWR_GAOGAEN_THROW_B_STATUS` in the combined offline build; the absent/invalid value
leaves the runtime disabled. Package `integration.patch` only adds our ACMD/status module
and install calls. If DK cargo also routes stock THROW PRE, compose both directions in
one dispatcher; do not register competing THROW PRE handlers. Mythra/Ness back throw
has no same-recipient conflict. Preserve other c06/c07 bank/list/config additions by
replaying semantic deltas.

The compiled function type-checks, but the Skyline binding's `phx::simd::Vector3` hook
return raises an FFI layout warning. The symbol/binding matches the native SIMD-q0 return;
compile output cannot confirm hook ABI at runtime. The native CaptureModule receiver
and every gameplay outcome likewise remain unverified. These are disclosed runtime
risks, not additional static donor gaps. No emulator or console run was performed.

Dependencies: workspace Python 3.12, `ssbh_data_py`, existing sound/PRC codecs; private
Capstone 5.0.7 cache; installed Skyline toolchain and pinned Cargo.lock/Cargo cache.
No system packages installed. Native binaries were recovered locally from the corrected
`prebuilt:/nro/release/` ARC namespace and pinned in `NATIVE_INPUTS.json`; no user dump
input remains missing. A prior missing-input statement was retracted and recorded in
`handbook/graveyard.md`.

Reproduce from the mod root:

```powershell
python -B src/pgwr/tools/gaogaen_throw_b/routes.py
python -B src/pgwr/tools/gaogaen_throw_b/engine_audit.py
python -B src/pgwr/tools/gaogaen_throw_b/collision_audit.py
python -B src/pgwr/tools/gaogaen_throw_b/runtime_package.py --check
python -B src/pgwr/tools/gaogaen_throw_b/handoff.py --check
git apply --check builds/pgwr/gaogaen_throw_b-0.2.0/integration.patch
```

After the installer allocates the ID and prepares the combined tree, apply/check the
patch, run `pipeline.py merge --target <installer-owned fresh mod tree>`, then build
offline with the allocated status environment. Do not install the included disabled
NRO. Files, hashes, source snapshot and baseline manifest are indexed in
`CREATED_FILES.json` and `builds/pgwr/gaogaen_throw_b-0.2.0/PACKAGE.json`.

## Manual console checks after integration

Runtime remains unverified. Compare vanilla Gaogaen with Revenge off, eflame c06/c07,
vanilla G&W and eflame c00-c05. Test both starting facings and ledges; small, average and
large victims; victim attachment, rotation, frame-30 release and post-release recovery;
collateral contacts (expect none from this donor attack); launch at several percentages;
camera (-4,5), quake/rumble, effects and each sound/voice cue; interruption before/during/
after impact and cleanup; and unrelated throws/moves including DK cargo/Snake routing.
Check custom entry/exit/victim-init logs, boot logs and crash reports, then repeat with a
vanilla recipient costume as the negative control.
