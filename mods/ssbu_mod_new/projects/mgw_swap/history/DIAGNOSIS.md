# Mythra / Game & Watch c07: position and camera investigation

## Current test build: v0.8.6 (2026-09-15)

The user tested v0.8.5 and confirmed that both symptoms remained. The supplied
console log is saved at
`references/mythra_gamewatch_feasibility/switch-v0.8.5.log`.
It confirms v0.8.5 loaded successfully, and identifies the return timing bug:

1. G&W queues down-B at (-55.044, 18.931, 0), facing +1.
2. After native capture, the handoff contains that correct pose.
3. Native activation invokes Mythra's Main frame callback in WAIT (status 0).
   The v0.8.5 repair runs there and consumes its saved pose.
4. Before the native restore returns, Mythra enters SPECIAL_LW_OUT (0x1e2).
   Her position AND the handoff buffer have reverted to (3.588, 26.455, 0),
   facing -1: the original Mythra departure pose.

The repair was therefore too early. `swap_handoff.rs` now keeps the outgoing
pose across those nested callbacks and applies it at 0x656720, immediately
after the native restore returns. Capture at 0x658328 refreshes the private
snapshot from the actual outgoing handoff. The two sites and their preceding
call instructions are signature-checked before hook installation. These hooks
run in both ordinary and diagnostic builds. Diagnostic hooks were consolidated
so each address is hooked only once.

The return repair uses PostureModule::init_pos to reset position history, then
restores facing and the captured ground/air situation. It updates the documented
native handoff pose fields too. It does not pin the fighter in later frames.

Camera evidence is weaker: every snapshot prints only the active partner;
v0.8.5 silently skipped unavailable IDs/accessors or validation mismatches.
Thus, the active callback's dormant-partner cleanup cannot be assumed to have
run. v0.8.6 hides Mythra's camera during her own SPECIAL_LW_STANDBY callback,
before native suspension, and enables the incoming camera once after native
restore in both directions. It logs `suppress-camera`, `restore-camera`, and
the exact reason any partner lookup is skipped. This is a targeted camera
timing correction, not a console-verified resolution of the camera symptom.

Validation: offline diagnostic release build passed; the four hook signatures
match the supplied executable. The packaged NRO matches the built NRO, with
valid NRO0 magic and declared size (98,304 bytes). The supplied log was checked
for the capture -> early repair -> native overwrite ordering above.
No v0.8.6 Switch runtime test has been performed.

Packaged file:
`mod_output/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmythra_gamewatch_swap.nro`

SHA-256: `a8236573f597b56c208204b022c301efb8d06992c30b2ee5fb3ea03f77ad7706`

Previous source and plugin backup: `mod_output/mythra_gamewatch_swap/before-v0.8.6/`.
Validation record: `mod_output/mythra_gamewatch_swap/v0.8.6-validation.json`.

Next Switch check: transform, move far away as G&W, return to Mythra; repeat on
the ground and in the air. The log should place `return pose applied AFTER
native restore` and `after-return-repair` AFTER `after-native-restore`, with
G&W's captured position and facing restored. Verify subsequent movement and
camera framing, repeated swaps, and stock loss/respawn.

## Previous attempt: v0.8.5 (2026-09-15; did not fix the symptoms)

The sections below this update describe the historical v0.8.2 investigation.
The source and packaged plugin now include a fix based on the v0.8.4 code:

- Confirmed source bug: Mythra's active-frame path overwrote `SAVED_POS_*`,
  facing, and situation with her old pose before reading them for the return
  handoff. Only G&W's down-B request now writes that frozen snapshot.
- Apply the return pose once after Mythra leaves standby. Do not pin her through
  every frame of SPECIAL_LW_OUT or move dormant bodies every frame.
- Both active callbacks now resolve the inactive partner through the entry's
  fighter IDs and disable its camera, areas, hit status, visibility, shadows,
  and items. Cleanup no longer requires the dormant partner's callback to run.
  Whether that callback stops running on the console remains unmeasured.
- Validate partner kind, entry, and costume before changing its modules. Check
  current fighter identity before running active behavior.
- Restore modules once for an object hidden by this plugin; preserve native
  XLU hit status. Removed the per-frame NORMAL hit-status override.
- Reset pending return state on entry initialization and stock lifecycle
  statuses. Clear a successful request after applying Mythra's return pose,
  rather than during an intermediate native table lookup.

Validation: offline diagnostic release build succeeded with the locked local
dependencies. Packaged NRO matches the build output, and NRO magic and declared
size are valid. Checked that each saved pose field has just one runtime writer,
inside G&W's down-B request. No Switch runtime test has been performed.

Current plugin (workspace-relative):
`mod_output/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmythra_gamewatch_swap.nro`

SHA-256: `c84540e4ecb76c8e0d4add8b9cd09871876c8216e79330a496f394e88dd70ae6`

Pre-change plugin and lib.rs backup:
`mod_output/mythra_gamewatch_swap/before-v0.8.5/`.
Build again using `mod_files/mythra_gamewatch_swap/build-diagnostic.ps1`.
The current script packages directly into `mod_output/atmosphere/` and uses
the crate's `target/` directory (the historical paths below are outdated).

Console checks: swap to G&W, walk far away, return to Mythra; repeat in the air
and facing both directions. Check that the camera follows only the active
fighter, return animation movement continues, repeated swaps work, and stock
loss/respawn does not restore a stale position. Check ordinary Mythra costumes
and a separate G&W player. Telemetry includes `[MGW-DIAG]` snapshots and a
`return pose applied once` line to distinguish native restore from our repair.

## Historical investigation

2026-09-13. Baseline source identifies itself as v0.8.2. User confirms both
directions work; return to Mythra causes a small apparently random displacement.
Camera feels off while playing GnW, but may still follow him normally.

## What is established

The partner construction hooks get far enough to create playable fighters.
The remaining swap implementation is asymmetric: Mythra uses native Element
down-special/standby/changer machinery, while GnW queues an entry-level switch
by writing `entry+0x591a`, `+0x5919`, and `+0x5920`, then hides selected modules.
GnW does not run an equivalent Element exit-status/changer sequence.

It would be incorrect to conclude that the teleport is simply caused by a
missing `PostureModule::set_pos` in Rust. The supplied native main proves:

1. Coordinator `0x6581f0` handles state 6 and selects the outgoing fighter using
   `entry+0x5918` and the pointer array at `entry+0x4160`.
2. At `0x658324` it calls `0x649980(outgoing, entry+0x41f0, flag)`.
   This saves the outgoing position at handoff+0, facing at +0x10, situation at
   +0x2b0, and velocity vectors at +0x20/+0x30. The position virtual method
   matches the exported `PostureModule::pos` wrapper's virtual slot +0x60.
3. Capture also invokes a character-specific callback at virtual slot +0x2e0.
4. Later, `0x656644` calls the activation routine `0x656ee0`, and `0x65671c`
   calls `0x64aea0(incoming, handoff, entry[0x41a0])`.
5. The latter dispatches through the incoming fighter's character-specific
   callback at virtual slot +0x2f0. Reaching the generic coordinator does not
   prove that the incoming fighter handles this restore correctly.

Thus, the position-transfer failure is narrowed to the handoff and activation
sequence, but its exact failing operation still requires runtime evidence.
Possibilities include a character callback replacing the saved position,
incoming status initialization/ground correction, or stale Element-specific
state. These are hypotheses, not confirmed causes.

## Concrete problems in the existing Rust code

- Both frame callbacks force visibility, normal hit status, area participation,
  and shadows every frame outside their short special-status exclusions. They
  do not check the entry's current fighter ID. If an inactive partner receives
  that callback, it can be re-enabled. Even on the active fighter, the repeated
  `HIT_STATUS_NORMAL` can override dodge/respawn/move invulnerability. Whether
  inactive callbacks actually occur here must be checked on the Switch.
- Neither callback manages `CameraModule`. Re-enabling visibility and areas is
  not a complete camera activation procedure. Camera-state inheritance or an
  inactive partner remaining relevant are plausible explanations, but the
  user's description does not establish either.
- GnW's manually hidden held/attached items have no corresponding explicit
  restoration in these callbacks. Native item handling may compensate.
- `SWAP_REQUESTED` is reset at subfighter table lookup, rather than a confirmed
  completed return to gameplay, and is not reset alongside entry registration.
  That is a lifecycle weakness; it is not yet linked to the reported teleport.

Do not patch these by forcing a position or camera reset every frame: that can
mask the actual transfer failure and fight status/ground/camera logic.

## Diagnostic build

The `swap-diagnostics` feature adds read-only logging. Default builds preserve
the original source behavior. The diagnostic build also retains that behavior,
so it is a measurement build, **not a claimed fix**.

- Snapshot immediately after native outgoing-state capture.
- Snapshot immediately after the native incoming restore callback returns.
- Snapshot at down-B, active-fighter change, and five bounded follow-up frames.
- Record both partner IDs, positions (including Z), status, situation, facing,
  visibility, camera type, and coordinator fields.
- Validate four instructions against the supplied dump before installing the
  two new inline hooks. This is a local signature check, not a full executable
  version guard for the existing six hooks.

Camera target getters in the locked bindings return opaque `u64` values; their
vector/pointer ABI has not been established here. The build records camera type
instead of guessing a vector layout. A short recording remains useful for the
subtle camera symptom.

Build with `./build-diagnostic.ps1` in this source directory. It uses installed
Skyline and local dependencies offline, keeps intermediate output under
`mod_output/mythra_gamewatch_swap/target`, and packages the NRO separately.
Skyline also refreshes its target JSON under the user's Cargo directory.

Existing packaged NRO and a source snapshot were copied to
`mod_output/mythra_gamewatch_swap/baseline/`. The original install package under
`mod_output/atmosphere/` has not been replaced.

Validation: the diagnostic release build succeeded with the installed Skyline
toolchain and locked local bindings (dependency warnings remain). NRO magic and
declared file size were checked; the original package matches the baseline
byte-for-byte. No Switch runtime test has been performed by this investigation.
Diagnostic NRO SHA-256:
`687b8ffa2fe2ba12d4f14bc6d2c2e541b959d65aeae215c4648242a17eb28ee5`.

## Switch test

Temporarily replace the existing Mythra/GnW plugin on the SD card with
`mod_output/mythra_gamewatch_swap/diagnostic/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmythra_gamewatch_swap.nro`.
Destination: `sd:/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmythra_gamewatch_swap.nro`.
Load only one version of this plugin at a time. Restore the baseline NRO to undo.

Capture Skyline logs (existing method, or `cargo skyline listen --ip <Switch-IP>`;
check local `cargo skyline listen --help` for available options).

1. On a flat stage, start Mythra c07, stand still, swap to GnW, stand still,
   swap back. Wait a second between swaps.
2. Swap to GnW, walk a noticeable distance, stop, then return to Mythra.
3. Repeat airborne, once facing each direction. Include an ordinary GnW
   briefly for camera comparison if convenient.
4. Return the log containing `[MGW-DIAG]` lines and, if possible, a short video
   of the camera issue. Compilation cannot validate the in-game behavior.

Interpretation: outgoing position differing from `handoff` implicates capture;
correct `handoff` but incorrect incoming position immediately after restore
implicates activation/restore; a later jump implicates subsequent status or
collision processing. An inactive fighter becoming visible is direct evidence
of an activation/lifecycle problem. Compare X/Y/Z, not only screen position.

## Reproducible evidence

Run `python mod_files/mythra_gamewatch_swap/tools/trace_swap.py` from the workspace
to reproduce the relevant assembly. It uses the existing main memory image and
project-local Capstone. This trace refers only to the supplied executable whose
original NSO SHA-256 is
`77936fe2031e4f38316120576177090857611025e140b415d3850bac8eabd92e`.
Vanilla Element status references are the existing saved files under
`references/mythra_gamewatch_feasibility/ghidra_scripts__lua2cpp_elight.nro__...`.
The public status dumps were not independently version-matched.
# Up-B cleanup (2026-09-15)

The broken Hero Spin attempt was isolated to `src/special_hi.rs`. It replaced
Mythra's native up-B status flow with Elight status callbacks and mixed custom
motion/ACMD names (`special_hi_start`, `special_air_hi_jump`, `special_air_hi1`,
and `special_air_hi2`). That left native Mythra transitions and the attempted
Mii-style scripts active together.

The file now leaves all Mythra/Elight up-B statuses native and installs only one
targeted ACMD layer for c07's existing Elight up-B phases. The attack timing and
multi-hit/final-hit values follow Mii Swordfighter's Hero Spin data, while the
legacy status callbacks, extra kinetic changes, and mismatched `game_specialhi`
registration are gone. No Mii Swordfighter motion or effect archives were
present in this pack, so this cleanup intentionally does not pretend to provide
those missing animation assets.

The diagnostic plugin was rebuilt successfully. Switch testing is still needed
to verify the c07 up-B animation, hit timing, and interaction with the existing
swap behavior.
## 2026-09-15: Hero Spin motion transplant

The c07 up-special animation override now follows the same cross-skeleton
approach used by the existing Game & Watch c07 Shulk fair:

- Mii Swordfighter Hero Spin transform tracks are copied only when the bone
  exists in Mythra/Elight c07's skeleton.
- Mii-only helper tracks, including `Miihead` and `Finger*4_eff`, are removed.
- Mythra's native visibility and material groups are retained for each target
  motion slot.
- Each target slot receives a distinct Hero Spin phase; no phase is populated
  by duplicating one unrelated Mii animation.

The generated motions are built by `tools/build_hero_spin_assets.py` and
deployed by `deploy.py`. The Rust plugin remains responsible for the c07-only
attack behavior. Runtime validation on a Switch is still required.

## 2026-09-17: the CATCH arity defect, and what a log does and does not show

The leap's catch box was created by hand-pushing eight values into
`sv_animcmd::CATCH`. The macro that defines the command
(`smash_script::macros::CATCH`, WuBoytH/smash-script @ `fdc6144`) takes eleven
values after the agent and always pushes eleven: `id, bone, size, x, y, z`, then
one value for each of `x2/y2/z2` -- a freshly constructed `L2CValue` when the
caller passes `None`, which is the command's documented "no second point" -- then
`status, situation`. Eight pushed values therefore place
`FIGHTER_STATUS_KIND_CLUNG_DIDDY` and the situation mask in the slots the engine
reads as the second point's offsets, and the status and situation it actually
reads come from past the end of what was pushed. A box built that way runs, logs
and cannot catch anything at any size, which is why the twelve-unit diagnostic
box proved nothing about geometry.

The calls are now the macro's own, with the donor's geometry (3.0 at y 2.5 z 4.5
and 4.0 at y 5.5 z 4.0, both on `top`, both into `CLUNG_DIDDY`), taken from
`references/diddy_specials/donor_acmd/SpecialAirSJump.txt`.

A Switch log from the fixed build still shows no capture. What that log proves,
and what it does not:

- `gamewatch_frame` runs every frame of every gamewatch status, and prints
  `[MGW-MFLIP] OBS` whenever either the status **or** `CatchModule::is_catch`
  changes, with the watch window held open for 60 frames after the status block
  ends. Only `false` ever appears, so the engine's own catch flag never became
  true during any leap. That is not a sampling gap -- an earlier reading of this
  same log as "sampled too early to mean anything" was wrong.
- The log cannot report the victim. Nothing samples an opponent's position or
  state, and the OBS line only covers entry 0.
- `link=0x50000000` is this plugin's own `INVALID_FIGHTER_ID` sentinel, not an
  engine value; it means "no link node", which is consistent with "no capture".

Skeletons, checked offline rather than assumed: neither
`export/fighter/diddy/model/body/c00/model.nusktb` (85 bones) nor
`export/fighter/gamewatch/model/body/c07/model.nusktb` (45 bones) contains a bone
literally named `top`; both are CamelCase (`Hip`, `Waist`, `Bust`, `TopHave`,
`HaveL`). So `hash40("top")` is an engine-side anchor, and "the recipient does
not have that bone" does not distinguish the recipient from the donor.

The donor's own status code never claims the capture either:
`SpecialSJump_main_loop.c` has no catch branch, and `SpecialSStick_main.c` only
sets the motion, a check-dead offset and shifts to its main loop.
`SpecialSStick_main_loop.c`, `SpecialSStick_end.c` and `SpecialSStick_check_dmg.c`
call `CatchModule::update_pos_cling`, `CatchModule::cling_cut` and
`CatchModule::check_damage`, so the cling itself is engine-owned once a capture
exists.

### 2026-09-17: the catch boxes exist, and where they sit

The first per-frame measurement of the catch itself (build `2026-09-17.c`, NRO
`DA24EEF3...`) answers the question every earlier build left open.

- `CATCHBOX acmd7 grab0=true grab1=true`: the CATCH command does create both
  entries, and `acmd19` / `acmd26` show them cleared exactly where the donor clears
  them (`grab1=false` after frame 19, `grab0=false` after 26). The command, its
  arity and the donor's clear timing are all correct.
- `top = trans = waist = self` on every frame: `ModelModule::joint_global_position`
  returns the object position for all three names, so the anchor reads back as the
  fighter's own origin. The donor's offsets therefore sit 2.5 and 5.5 units above
  that origin and 4.0 / 4.5 units out of the gameplay plane.
- The nearest opponent, sampled every frame: the best of five leaps closed to
  2.53 units in x (frames 22..24) while its origin was at ground level. By then the
  air-valid donor box (id 1, `MASK_GA`) had been cleared at frame 19, and the box
  still alive (id 0) is ground-gated, 4.5 units out of plane and has a radius of
  only 3.0 -- about 0.3 units short of the victim's torso volume. During the ascent
  both donor boxes were more than 12 units above a grounded victim.
- `is_catch=false` and `capture=0x50000000` on every frame of every leap.

So the fault is box placement and box timing, not the command, and not the arity.

Unrelated but worth recording, because it cost a false alarm: Rust's
`format_args!` stores the literal pieces between placeholders as separate strings,
so a format string is never contiguous inside a binary. Probing an NRO for
`elapsed={} is_catch={}` finds nothing; probing for `is_catch` or `anchor=` finds
it. For build identification, use the banner literal, not a format string.

## 2026-09-17: two process defects, both of which produced a silently wrong deploy

Neither is about the move. Both cost a build round trip, and both fail *silently*,
which is why they are written down.

### The build that reported `Finished` and shipped nothing

`cargo skyline build --release --features swap-diagnostics` run through
powershell.exe reports exit code **255** and wraps cargo's stderr output as a
`NativeCommandError` (`RemoteException`), even when cargo itself printed
`Finished release profile [optimized] target(s) in 3.25s`. cargo-skyline's NRO
packaging happens *after* that completion line, so a failure there leaves no trace
in the cargo log at all, and the only symptom is the exit code -- which is already
being misreported.

That is what happened to this build: the log ended at `Finished`, the reported exit
code was 255, and
`target\aarch64-skyline-switch\release\libmythra_gamewatch_swap.nro` was left as the
*previous* build. Everything downstream then treated a stale artefact as fresh.

The fix is [`scratch/build_plugin.cmd`](../../scratch/build_plugin.cmd): a batch
file that puts the mingw binutils first on PATH and runs cargo itself, so the shell
is out of the picture and `%ERRORLEVEL%` is cargo's real exit code. Under cmd the
same build reports `EXIT=0`.

### The deploy that reported success and shipped the old binary

Running `deploy.py` for the new build printed
`NRO Deployed: ... SHA256: 4de85a47...`, which is the **previous** build's hash.
Nothing in the output is flagged, because `deploy.py` reports what it copied and
never compares that to what the build produced.

So: after every deploy, hash `mod_output`'s NRO and compare it with
`target\aarch64-skyline-switch\release\libmythra_gamewatch_swap.nro`. A deploy
whose hash equals the previous build's hash has shipped nothing.

### What the same investigation exposed in the Fair step

`deploy.py` pushes the Shulk Fair assets after the NRO, and on this machine that
step had always aborted at `import numpy` -- it had never run past its own imports
here. With numpy installed it now reaches
[`build_fair_assets.py`](tools/build_fair_assets.py:121), which fails with
`TypeError: list indices must be integers or slices, not tuple` because
`o.normals[0].data` is a plain list there and not an array. The Fair step still has
not completed on this machine, and that is a separate defect from the move this
document is about.

The partial run did not damage anything, and both reasons matter later: the SwordR
injection reads the *export* skeleton every time and appends the same bone at
HaveR's index, so it is idempotent and cannot accumulate bones; and the crash
happens before `model.numshb` and `model.numdlb` are written, so the already
deployed SwordM mesh was left untouched. The deployed `model.nusktb` now carries
SwordR, which is the bone the deployed `model.numshb` already named as the sword's
parent.

## 2026-09-17: the forced capture works, and one missing link explained every symptom

Build `2026-09-17.e` (NRO `335E7B2B...`) performed the grab on the Switch and
narrowed the whole remaining problem to a single call.

What worked, from the log of the leap that connected:

- `FORCE SKIPPED elapsed=20 victim=0x20000 dist=14.05 radius=7.00` on the first
  leap and `FORCE elapsed=20 victim=0x20000 dist=4.82 radius=7.00` on the second:
  the reach gate behaves as designed, and it reports by how much it missed.
- `CatchModule::set_catch(boma, victim_id)` does set the catch state: `is_catch=true`
  and `capture_object_id` returns `0x20000`.
- `CATCH HANDOFF elapsed=20 capture=0x20000 via=forced -> STICK` follows, and the
  whole later chain runs: STICK (`special_s_stick`), STICK_ATTACK, STICK_ATTACK2
  and FLIP_FALL all enter with their motions and all reach their own transitions.
  The `grab_live=false` on every CLING line is the JUMP status exit clearing the
  entries, which is correct.

What was missing, and it was one thing:

- `link=0x50000000` on every frame, before and after the forced capture.
  `CatchModule::set_catch` sets the catch state but **does not publish the
  `LINK_NO_CAPTURE` node**. Both `get_node_object_id` and `capture_object_id` report
  that same id when unset, so `0x50000000` is the engine's null object id and not
  only this plugin's sentinel.
- The victim never entered a clung status: `vstatus` stayed `0x0`, `0x1` and `0x6`
  (WAIT and WALK) for the entire cling. So `set_catch` does not route the victim
  either.
- Every other symptom in the run follows from that one gap. The cling positions were
  nonsense (`self=(12.61,13.44)` against `vpos=(16.82,0.01)`, and both slid together
  across the stage). `send_cling_throw` sends its `LinkEvent` to `LINK_NO_CAPTURE`, so
  with no link the throw event had nowhere to go and did nothing. And `catch=true` was
  still true in `FLIP_FALL` and in the following damage status, so nothing tore the
  catch down -- which is why the victim could not break off and the attacker only got
  out through the attack input.

Corroboration that the port was not at fault for the positions:
[`SpecialSStick_main_loop.c`](../references/diddy_specials/SpecialSStick_main_loop.c:96)
calls `CatchModule::update_pos_cling` itself, so the port's own call is faithful and
is not the cause.

Build `2026-09-18.f` (NRO `9349B1F7...`) therefore adds, in this order:

1. `LinkModule::link(boma, *LINK_NO_CAPTURE, victim_id)` before `set_catch`. This
   revision of the bindings has no `LinkModule::set_node_object_id`; `link` is the
   node-to-object setter and takes a node index and a battle object id.
2. A victim status request to `FIGHTER_STATUS_KIND_CLUNG_DIDDY`, issued **only** if
   the victim's status read back is not already that status, so the log states which
   mechanism was sufficient rather than assuming one.
3. A stale-catch reset at the start of the move, because with the catch left set the
   JUMP arm's `!is_catch` guard skips the capture and the handoff then fires on frame
   0 of the next leap, which would make a second test unreadable.

`START` also unlinks `LINK_NO_CAPTURE` so a previous move cannot leave a stale link
for the throw to follow. Whether the engine's own throw event tears the catch down
once the link exists is left to the next log rather than pre-empted.

## 2026-09-18: the hand-built capture froze the console, and what replaced it

Build `.f` (NRO `9349B1F7...`) published the capture link with `LinkModule::link`
and asked for the victim's status with `change_status_request_from_script`, and the
game froze at the moment the grab connected. The last line the console flushed is
leap frame 17 of that run, but the capture does not arm until frame 20 and the grab
was visibly happening, so the freeze is at the connection rather than at frame 17.

Both of those calls are in the suspect set and neither is donor-attested. The donor
never sets that link and never asks for the victim's status, because in vanilla the
engine does all of it at the moment of the collision match. What build `.e` had
already measured makes the shape of the failure readable: `set_catch` on its own
produced `is_catch=true` and a valid `capture_object_id`, but it published no link
and did not route the victim. So `.f` completed a capture that was never a real one,
and once the link existed the engine finally followed it.

That is the lesson, and it is not about this move: half-building an engine capture is
worse than not building one, because the individual parts are inert and only fail
once they are joined.

Build `.g` (NRO `B0305231...`) removes the hand-built capture entirely -- no
`set_catch`, no `link`, no status request -- and hands the capture back to the
engine, where the donor leaves it. What makes it reach is a single box:
`macros::CATCH(agent, 2, top, 8.0, 0.0, 2.5, 0.0, None, None, None, CLUNG_DIDDY,
MASK_GA)`, alive from ACMD frame 7 until the donor's own clear at frame 26.

The radius is a measured value rather than a guess. Two leaps have now been logged
with the victim's distance from that anchor printed every frame: the closest approach
was 2.53 units in build `.e`, and 7.20 units at leap frame 17 and still closing in
build `.f`. A sphere of radius 8.0 centred 2.5 above the anchor therefore contains a
torso whose own centre is about 7.0 units away horizontally. It is also inside the
donor's own envelope: the donor's air-valid box is a sphere of radius 4.0 centred 5.5
above and 4.0 out from the anchor, so it reaches 4.0 + sqrt(5.5^2 + 4.0^2) = 10.8 from
that same anchor.

What remains in the status loop is an observer: `NOCATCH` reports per frame how close
the nearest opponent is, which is the number the box has to be sized against, and
`NOCATCH FAR` and `NOCATCH NOVICTIM` separate "the leap never got near" from "the leap
got near and still did not catch".

Also worth recording, because it produced a false alarm in this very round: a
`findstr /C:"..."` inside `cmd /c "..."` has its inner quotes eaten by the outer
quoting, so the pattern degrades to an empty string and matches every line. A probe
written that way appears to confirm whatever it is asked to confirm -- it "found" a
string that the source no longer contained. Write `/C:pattern` with no quotes when
the pattern has no spaces.

## 2026-09-18: the box does contain the victim, and still nothing catches

Build `.g` ran without freezing, and its log removes the explanation the previous
three builds were built on. The failure is not that the box never contained the
victim.

From the leap that was aimed at the opponent:

- `CATCHBOX acmd7 grab0=true grab1=true grab2=true grab3=false`: the reach box
  exists, and `acmd19` / `acmd26` clear the entries exactly where the donor clears
  them.
- The victim's distance from the anchor, printed every frame, reached 4.82 units at
  leap frame 22 and stayed between 4.82 and 5.45 for frames 20..24. The box is a
  sphere of radius 8.0 centred 2.5 above that anchor, so its centre sat about 6.0
  units from the victim, which means the sphere enclosed them for five consecutive
  frames. `is_catch` was false on every one of those frames, and the victim was in
  `WAIT` (`vstatus=0x0`) on the ground, which is as grabbable as a fighter gets.
- The `NOCATCH` lines report exactly that: an opponent inside the reach, a live box,
  and no catch.

So the entry exists and the geometry provably overlaps the victim, and the engine
still does not register a catch. That rules out box size, box placement and the reach
radius as the cause, and it also means the old "arity defect" explanation is not
supported by anything measured: the eight-value hand push and the eleven-value macro
call produce the same live entry and the same absence of a catch. Whether the arity
matters at all was never actually tested, only assumed.

One more thing this run settled, and it is a negative result worth keeping: the
donor's own ACMD for this move contains *nothing else*.
[`SpecialAirSJump.txt`](../references/diddy_specials/donor_acmd/SpecialAirSJump.txt)
holds the two `CATCH` calls and the two `grab!` clears in `game_specialairsjump`, and
effects, sounds and an expression function after them. There is no setup call, no
`AttackModule` flag and no additional command that the port could be forgetting. The
port issues the same commands as the donor.

Also visible in the same log, and worth knowing before reading the next one: on one
attempt the leap passed the victim at leap frame 6, one frame before the donor's own
boxes are created at ACMD frame 7. That is the donor's timing, so it stays.

Build `2026-09-18.h` (NRO `31A975CA...`) therefore stops guessing and separates the
two remaining explanations with one run:

- Box 2 is unchanged: the reach box issued through `macros::CATCH`, which always
  pushes eleven values and fills the second point with an empty `L2CValue`.
- Box 3 is the *same box* pushed by hand in the donor's own shape -- the eight values
  `id, bone, size, x, y, z, status, situation` that the donor's call site passes --
  through `sv_animcmd::CATCH`. Geometry, victim status and situation mask are
  identical, so the only difference between the two boxes is the shape of the call.
- `CATCHGEO` prints, for every box, the value the engine actually stored for `size`
  and `center_pos`, raw rather than interpreted: both are declared to return a `u64`
  in this revision, so a float should surface as its bit pattern (`8.0f32` is
  `0x41000000`) and a pointer as a heap address. Reading them raw is deliberate --
  dereferencing a value of uncertain type is how a diagnostic build hangs a console,
  and one already has.

How to read the next log: if `grab3` is false the hand push created nothing at all,
which is itself the answer. If `size2` and `size3` both look like `0x41000000` and
`cpos2`/`cpos3` agree, then both shapes stored the same box, and the difference -- if
any -- is in how the command reads its tail arguments. If box 3 catches while box 2
does not, the donor's shape is the correct one and it is also the faithful port. If
neither catches while both are stored correctly, then the entry is simply not being
evaluated, and the cause is on the status side rather than in the ACMD, because our
`JUMP` is a Smashline-added status while the donor's is native -- and the next
isolation would be to issue a `CATCH` from a status the engine already knows.

## 2026-09-18: both call shapes are equivalent, and index 3 is off the end of the array

Build `.h` ran the controlled A/B -- box 2 in the macro's eleven-value shape, box 3
in the donor's own eight-value shape, identical in every other respect -- and its
telemetry buried one story and produced a new one.

**The arity story is dead.** `grab3=true` with a valid `node3` on every CATCHBOX
line: the hand push in the donor's own shape creates a live entry exactly as the
macro's shape does. So the two shapes differ in nothing this move can observe, the
original hand-pushed code was not broken in the way it was believed to be, and the
"arity defect" explanation that this whole port was rebuilt around has no measurement
behind it.

**`GrabModule::size` is not a per-box readback.** It returned the identical value for
all four boxes, `0x41a3ead300`, even though the donor passes 3.0 and 4.0 and this port
passes 8.0 and 8.0. Whatever that call returns, it is not the size of the box it is
asked about. Reading it was a dead end, and the raw-value approach generally was:
without the module's struct definitions, a `u64` return is not interpretable. The
lesson is to range-check and interpret, not to print raw and hope.

**`GrabModule::center_pos` returns a pointer per entry.** The returns for boxes 0, 1
and 2 came back exactly `0xC0` apart -- the stride between grab entries -- while box
3's came back in a different region of the heap entirely. An array of three entries
with a fourth index being written past its end is not something to leave in a build,
so box 3 and its clear are gone.

Same outcome as `.g` on the thing that matters: with box 2 (radius 8.0) alive through
frame 25, the closest approach was `dist=7.04` at frame 25, and `is_catch` was false
on every frame of every leap in the run.

Build `2026-09-18.i` (NRO `FAB973DB...`) does two things.

It arms the grab module explicitly, right after the CATCH calls, because a box that
exists, is cleared on the donor's schedule and provably enclosed the victim while
`is_catch` stayed false is what a module that was never armed looks like:
`GrabModule::sleep(boma, false)` (the module's own wake call),
`set_size_mul(boma, 1.0)` (guarding a zero multiplier, which would scale every box to
nothing and produce exactly this symptom), `set_check_front(boma, false)` (the
front-facing requirement is a module-wide flag here, not a per-box one) and
`set_size(boma, 2, 8.0)` (re-stating the reach box's size after the fact, in case the
command's own size argument never lands in that slot).

More importantly, it reports the measurement that was missing for this entire
investigation: the **centre the engine actually stored** for entries 0, 1 and 2,
interpreted rather than printed raw. The box has always been *assumed* to sit at the
anchor plus its offset, and that assumption was only ever tested for the joint, never
for the box. A `catch_center` helper reads each pointer, range-checked first because
reading an arbitrary address is how a diagnostic build hangs a console and this family
has done that once. If `centre2` tracks the fighter at `self + (0, 2.5, 0)`, the box is
where it is believed to be and the failure is not geometry. If `centre2` sits still,
or sits at the stage origin, or does not track at all, then the box has been in the
wrong place in every run so far and the module's own positioning is the fix.

## 2026-09-18: the log reader was reading the wrong numbers

`scratch/summarise_mflip_log.py` is the tool that turns a captured log into the answer,
and it was wrong in three ways at once. All three were silent, which makes this the same
class of defect as the deploy that echoed the previous build's hash.

**Its vocabulary had drifted from the sources.** It parsed `OBS` and `CATCH ACMD` and
inferred "no capture" from their silence. `OBS` is worse than merely stale as a witness:
it prints only when the status *or* the catch *changes* (`lib.rs:561`) and only within 60
frames of leaving the Monkey Flip block (`lib.rs:552-558`), so its silence is not evidence
of anything, and the old tool's headline conclusion rested on exactly that silence.
`CATCHGEO`, `CATCHW`, `NOCATCH`, `GRABARM` and `CATCH HANDOFF` - every line the current
build actually emits - were not parsed at all.

**Two capture-group indices were wrong.** `CATCHW dist=` was read from group 17, which is
`vpos.x`: the tool would have reported a coordinate as a distance. Every `CLING` field
after `end=` was one group early, so `is_catch` was reading `end`. `NOCATCH FAR dist=` was
read from group 2, which is the victim's object id.

`NOCATCH FAR` is the odd one out: it was caught by a self-check rather than by reading,
which is why the file now carries one. `GROUP_COUNTS` asserts every pattern's
capture-group count at start-up and refuses to run on a log when a pattern and its index
contract disagree:

    summarise_mflip_log.py is out of step with the sources it parses:
      NOCATCH_FAR: 4 capture groups, expected 3

That message is the whole value. A wrong index does not raise; it reports a
plausible-looking number, and a plausible-looking number is what all three of these
defects produced.

**A fixture now pins it.** `scratch/fixture_mflip_i.log` reproduces one line per
`println!` format string of the current sources, in two attempts that exercise both
geometry verdicts, and it is written so that a wrong index is visible: the `dist=` values
deliberately differ from the `vpos=` x values (4.82 against 16.82 and 34.82). It also
holds the negative case, an attempt with no capture, where the tool has to say so rather
than say nothing.

For the `.i` test this means the `centre2` question is now read mechanically and
classified against the fighter's own origin, so the next log yields one of four stated
verdicts rather than a paragraph to interpret.

## 2026-09-18: what the donor does not do, and the one state it never establishes

Build `2026-09-18.j` (NRO `790B9164...`) changes exactly one thing about the grab: it
asks the grab module for the activation state the donor never asks for. Two of my own
hypotheses died on the way there, both by reading rather than by testing.

**The donor's leap status does nothing grab-specific.** `SpecialSJump_main_loop.c` and
`SpecialSJump_main.c` - the leap's own status code, both pinned in the tree - contain no
`GrabModule`, `CatchModule` or `LinkModule` call at all. Their engine calls are motion,
work-int, transition-term, cancel and stop calls only. So the port has not omitted a
status-side grab call, and there is nothing further to copy from the donor's status: in
Diddy's game the catch happens without his status touching the grab system, which means
the engine's own per-frame grab evaluation converts the box into a catch, and the only
thing in our port that could stop it is the module's state.

**`set_rebound` is not something Monkey Flip does - which is precisely why it matters.**
It is in the Catch ACMD of every fighter in the dump tree, this recipient included
(`lua2cpp_gamewatch/gamewatch/Catch.txt:3-4`), and in every other grabbing special
(Yoshi `SpecialN`, Wario `SpecialNOpenWait`, Lucario `SpecialS`, Gaogaen
`SpecialSStart`), always `true` when the grab goes live and `false` when it ends.
Monkey Flip's ACMD does not call it and neither does its status. So in Diddy's game
something outside the move establishes that state, and a port that reimplements only the
move and runs none of that surrounding machinery establishes nothing. That is a
mechanism which fits every measurement taken so far: an entry that is live, positioned,
overlapping and never acted on is what an unactivated module looks like.

The leap therefore calls, at frame 7 and in this order, `set_rebound(true)`,
`sleep(false)`, `set_size_mul(1.0)`, `set_check_front(false)` and `set_size(2, 8.0)`, and
at frame 26 - the donor's own last frame, where every Catch ACMD drops it -
`set_rebound(false)`. These are one hypothesis asked five ways, not five hypotheses: all
five are ways of putting the module into its active state.

Two new readings decide the next step, and both are mechanical now:

* `GRABARM acmd7 rebound=...` says whether the activation took at all. If it reads false
  in the very frame it was set, the module is rejecting the call and the state has to be
  established somewhere else.
* `CATCHW ... rebound=...` on every sampled window frame says whether it held while the
  victim was inside the box.

If rebound reads true and holds through the window while the box still catches nothing,
then the module's active state is eliminated as well, and what remains is that the engine
does not evaluate grab entries for a status Smashline added. That is separable without
guessing: issue a `CATCH` from a status the engine already knows and see whether that one
catches, which distinguishes "our status is not eligible" from "our command is wrong".

The deploy is now verified mechanically: `scratch/verify_nro.py` prints an NRO's hash,
size and marker counts, so the failure mode where a deploy copies the previous binary
while reporting success cannot pass unnoticed again. For `.j` the built and deployed
hashes are both `790b916481f04cc0ce9e115c45ecdcc0be3cc0f757182a716c0e6219aa98e470`, and the
deployed binary contains `2026-09-18.j`, `GRABDIS` and `rebound=` while the `.i` banner is
absent from it.

## 2026-09-18: rebound took, held, and the box was never around the victim

Log from build `2026-09-18.j`: three leaps, victim present in all three.

`GRABARM acmd7 rebound=true` on every leap, so the module **accepted** the activation.
`CATCHW ... rebound=true` on every sampled frame from elapsed 6 to 24, and
`GRABDIS acmd26 rebound=false` where the donor drops it. Boxes 0, 1 and 2 live with valid
nodes throughout, `vsit=0` and the victim's status 0x0/0x1/0x6 - an ordinary standing
fighter - while `is_catch` is false on every frame of every leap.

That eliminates the whole module-activation family: `set_rebound(true)`, `sleep(false)`,
`set_size_mul(1.0)`, `set_check_front(false)` and `set_size(2, 8.0)`. It was the last
explanation that a change *inside this move* could have fixed, and it is now closed.

### A correction: the box has never been shown to contain the victim

`dist=` is the full 3D distance between the two fighters' origins, so it already includes
the height difference - and the height difference is the whole story. The leap carries the
fighter to y = 6.5 .. 10.0 (every leap in this log is `situation=2`, air) while the victim
stands at y = 0.11, and this box is centred 2.5 units *above* the fighter again.

At the closest approach of the third leap, `dist=7.65` at elapsed 20: fighter
(-21.95, 7.06, 0.10), so the box centre is at y = 9.56, and the victim is at
(-25.15, 0.11, 0.10). That puts the box centre 9.98 from the victim against a radius of
8.0. **The victim was outside the box.**

The earlier claim that build `.g` had shown "a live radius-8.0 box enclosing the victim
while is_catch stayed false" was inferred from a bare `dist=4.82`; it did not account for
the 2.5-unit offset above a fighter that is already airborne, and it does not stand as
evidence. Exactly one thing remains unobserved for this move: a live box that genuinely
contains the victim, with the engine free to convert it.

### `CATCHGEO` at acmd7 measures the previous leap

In all three leaps the acmd7 line reports either zeros or precisely the values the
*previous* leap's acmd26 reported: attempt 2's acmd7 `centre0/1/2` are
(-26.05,2.61,-0.50), (-27.92,11.98,-0.50), (-30.55,2.61,-0.50), and attempt 1's acmd26 are
those same three numbers. The stored centre is written after the frame that creates the
box, so reading it in that same frame returns the old box's value - the acmd7 sample in the
build `.i` design could never have measured what it was meant to measure.

Read at acmd19 and acmd26 the centres do track the fighter at roughly the intended offset:
`centre2 - self` is (0.13,3.25,0.00), (-0.10,3.25,0.00) and (-1.76,3.25,-0.10) at acmd19,
and (-0.32,2.50,0.00), (-0.08,2.50,0.00) at acmd26. So the box is where the arguments put
it, and the `.i` reading of "centre equals the fighter origin" was a timing artifact rather
than a positioning fault.

### Parked here, with the next experiment already specified

Monkey Flip's grab is parked with side-B left exactly as it behaves now: the leap, the
boxes on the donor's schedule, the kick, no catch and no freeze. If it is ever resumed, the
next experiment is arithmetic rather than guesswork, because the log now gives both
positions:

* at the closest approach measured so far the fighter is at y ~ 7.1 and the victim at
  y ~ 0.11, so a box of radius 8.0 centred on the fighter's own origin (offset 0.0 instead
  of 2.5) puts the victim 7.65 from the centre - inside it - and
* centring it lower still, at offset -2.5, puts the victim 5.08 from the centre.

So the next build should drop or invert the y offset rather than enlarge the radius, and
should log the box-to-victim distance directly instead of the fighter-to-victim distance
that has been standing in for it. If a victim genuinely inside a live box still produces no
catch, the remaining hypothesis is that the engine does not evaluate grab entries for a
status Smashline added, and the test for that is a `CATCH` issued from a status the engine
already knows.
## 2026-09-26: Mythra up-B uses the wrong Mii option

The reported Switch behavior is a glitched mix of Mythra's up-B and a downward
sword thrust. The donor identity is now confirmed from the local game files:
Mii Swordfighter's `Hi1` is Stone Scabbard (rising slash and downward thrust),
while Hero's Spin is `Hi3`. `references/miiswordsman_special_hi/PLAN.md` asserts
the opposite at its original section 1, and `src/hero_spin.rs`,
`tools/build_hero_spin_assets.py`, the animation manifest and all five packaged
c07 animations use `Hi1` status/ACMD/clip files. The end ACMD uses
`game_specialhi1end`; its effect script names `miiswordsman_rocket_stab`.
This explains the downward stab without relying on a kinetic hypothesis.

Offline package checks: the five c07 clips and motion list match the existing
manifest, and the shipped NRO (SHA-256
`1528c657b389452a27abcae7dcacfb6f8424eff0f56215a65cbe26aa00913b81`)
contains the `2026-09-18.k` `MGW-HSPIN` banner. The package is internally
consistent but implements the wrong move. A separate possible contributor to
the glitched presentation is that the code installs only game ACMD, leaving
Mythra's native effect, sound and expression scripts on the played slots; no
console log yet isolates those visual/audio layers.

The local Mii dump has `d02specialairhi3.nuanmb` but is missing
`d02specialhi3start.nuanmb`, `d02specialhi3hold.nuanmb` and
`d02specialhi3.nuanmb`. The real Hero's Spin needs a new `Hi3`-based plan and
status/ACMD implementation; changing a filename or the current phase labels
cannot convert Stone Scabbard into it. No gameplay files were changed in this
diagnosis.

## 2026-09-26: Hi3 replacement packaged for Switch test

The user supplied the three ground `Hi3` clips missing from the local dump.
Their hashes, along with the already present air clip, are pinned in
`references/miiswordsman_special_hi3/animation_manifest.json`.
`tools/build_hero_spin3_assets.py` retargeted all four clips to Mythra c07,
read them back, and checked that 731 unrelated motion-list entries stayed
byte-identical. The unused old Hi1 `d02specialairhistart.nuanmb` was removed
from the shipping tree after comparison with the backup.

`src/lib.rs` installs `hero_spin3.rs` in place of `hero_spin.rs`. The new c07
status flow owns start, hold, ground spin and air spin. Its three game ACMD
bodies come from the local Mii Hi3 dumps; their source SHA-256 hashes are in
`src/hero_spin3_acmd.rs`. The non-c07 path calls the original status and ACMD.
The c07 path suppresses Mythra's native effect, sound and expression scripts
on the four played slots to avoid the prior mixed presentation. Mii-specific
effects and sounds are absent from Mythra's resource bank. The air phase uses
Mythra's `JUMP_AERIAL` kinetic because the donor's dedicated Mii Hi3 kinetic
cannot be used on Mythra; its motion on hardware remains to be measured.

The diagnostic NRO compiled and deployment succeeded. The packaged NRO is
139,264 bytes, SHA-256
`d81a00ac83ae6bd0fd481d4688d2c50ed354196a4299906fe25aee359a2faac1`,
with valid `NRO0` header, declared size, and `MGW-HI3` / `2026-09-26.a`
markers; it matches the built artifact. All four shipped clips and the motion
list match the new manifest. Full results are in
`mod_files/mythra_gamewatch_swap/backups/before-hi3/hi3-validation.json`.
No Switch runtime test has occurred. Next: test c07 ground tap, hold/release,
aerial use, and another Mythra costume; capture `[MGW-HI3]` log lines.

## 2026-09-26: Aerial Hi3 frame-0 landing fixed in build .b

The user's first Switch test found that ground Hero's Spin feels right but
aerial up-B only resets momentum. The supplied Skyline log shows c07 air entry
selected status `0x1f4` and the 85-frame `special_air_hi_end` motion, but its
kinetic was `6` (ground stop) and it changed to landing status `0x19` at frame
0 with `situation=0` on every aerial attempt. The clip itself was loaded, so
this is a status-setting error rather than a missing asset.

`src/hero_spin3.rs` previously chose ground or air settings in the Pre callback
by reading `StatusModule::status_kind`, which can still refer to the outgoing
status there. Build `2026-09-26.b` registers separate ground and air Pre
callbacks, each passing an explicit situation/kinetic selection. It adds a
`[MGW-HI3] pre` line so the next Switch log can confirm air settings. The
diagnostic NRO compiled and the complete deploy plus Hi3 payload verifier
passed. Packaged NRO: 143,360 bytes, SHA-256
`85efe535f9aeb13d2081fe75b56ba8aa237e225beff96efc44206034eaff7b66`.
The user has not yet tested this second build on Switch.

## 2026-09-26: Air height and sword trail, build .c

The user confirmed the air status now plays in build .b. The remaining
observations are no sword trail, too much downward travel, and an aerial final
hit that misses. Mythra's common air acceleration in the user's game dump is
`0.137`; Mii Swordfighter's is `0.106`. Their stable fall speeds are `1.87`
and `1.55`, respectively. The source file and hashes are recorded in
`references/miiswordsman_special_hi3/kinetic_manifest.json`. The Mii Hi3
special-parameter fields in `vl.prc` are zero, and its dedicated Hi3 kinetic
is not available to Elight, so this build adapts the sourced common Mii air
gravity and terminal speed while the Hi3 air status runs. The exact ascent
remains unverified.

The effect scripts now create Mythra's own `tex_elight_sword3`/
`tex_elight_sword2` afterimage on `sword1`, using her verified AttackAirHi
trail call and the donor Hi3 on/off frames (ground 2-42; air 4-54). No Mii
effect resource is invoked. The diagnostic build logs Mythra's height during
the air spin and has a read-only Mii Swordfighter Hi3 motion probe, allowing a
direct console comparison if the height or final hit still differs.

Build .c compiled and the complete deploy plus payload verifier passed.
Packaged NRO: 143,360 bytes, SHA-256
`abbef54e6d60a81fffb53a66491f749f064760212c3b322ab505937aef6ac993`.
Console verification of .c is pending.

## 2026-09-26: late-hit window, build .d

The user supplied the .c Switch trace. It records the Mythra air spin climbing
to its apex around frames 24-32, then descending; multiple attempts transitioned
to landing at frames 29, 39, 43, and 45. The donor air script's finisher runs
at frames 47-48, so those attempts leave the air status before the finisher.
Build .d applies a further modest reduction to the .c Mii-derived gravity
acceleration (85%) and terminal fall speed (90%) to keep the spin airborne
longer through the finisher window. This is a trial tune from the user's
feedback; the exact Mii trajectory is not established because no donor trace
was included.

Build .d compiled and passed the full deploy/payload verification. NRO:
143,360 bytes, SHA-256
`c5fb2eb69d38d9e2c27ef58441ab10726d91e25d6fda3fdfb81e0ef40acc4931`.
The next Switch test should confirm whether the frame-47 finisher runs more
often and whether opponents remain in the hitboxes through the last strike.

## 2026-09-26: restore Hero's Spin startup turnaround, build .g

The user reports that c07 Hero's Spin cannot turn around on input. Its custom
Pre callbacks set status attributes to zero, while both pinned native entry
dumps (`references/miiswordsman_special_hi/recipient_status/SpecialHi__pre.c:71`
and `status/SpecialHi__pre.c:72`) set `FIGHTER_STATUS_ATTR_START_TURN`.
The c07 interrupt bypasses the native Pre setup. This is the identified code
omission; reversal on hardware remains to be verified.

Build `2026-09-26.g` restores that native attribute on the ground START phase
and direct aerial entry. The air Pre identifies the interrupted SPECIAL_HI
source (0x1de, observed consistently in the supplied Switch trace); its air
situation and kinetic remain selected explicitly. HOLD, GROUND_SPIN and an
air transition from a ground phase do not request a second startup turn.
The non-c07 branch and its local vanilla ACMD fallbacks are unchanged.
No animation, hitbox, gravity or terminal-speed values were modified.

The offline release build succeeded with existing project warnings. The
payload verifier passed: built and packaged NRO match, NRO0 header and size
are valid, the .g marker is present, and all four clips and the motion list
match the existing manifest. NRO: 143,360 bytes, SHA-256
`fafb1edaecc56645ecbefcd499181cb9e1a0f6874bdb258fe08b8876643675ed`.
No full asset redeploy was needed for this source-only correction. Backup
source, previous .f NRO and .g validation record are in
`mod_files/mythra_gamewatch_swap/backups/before-hi3-turn/`.

Install the packaged `libmythra_gamewatch_swap.nro` at
`sd:/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/`, replacing
the existing file and retaining only one installed copy of this plugin.
To revert, install the NRO from the backup folder at that same SD path.
Switch checks (not yet run):

1. Face right, use up-left+B, then face left and use up-right+B. Repeat on
   ground and in the air. Each initial spin should face the requested side.
2. Use straight-up+B facing either direction: keep the original facing.
3. Charge on ground, then hold the opposite direction before releasing:
   the HOLD/release phases should not perform another startup turn. Also
   check a ground-to-air continuation if the stage allows it.
4. Try normal up-B with another Mythra costume to check the vanilla path.

Diagnostic evidence: `[MGW-HI3] build 2026-09-26.g` identifies the binary;
`pre ... start_turn=true` confirms the entry attribute is requested;
`phase ... lr=` records the resulting facing (+1 right, -1 left), paired
with `stick_x`. Follow-up phases should report `start_turn=false`.

## 2026-09-26: G&W c07 real Snake grenade object test, .p1

The user requested the actual Snake grenade and authorized starting the port.
`src/snake_grenade.rs` now installs a c07-only neutral-B entry and status 0x220.
It spawns `ITEM_KIND_SNAKEGRENADE` through native ItemModule and returns to
normal item handling. This is the first hardware gate: one owned grenade at a
time, A to throw and grab to drop. Snake's pull/hold/throw animations,
B-release controls, three throw strengths, movement and native grenade limit
remain to be ported. The actual item's fuse and attacks are not recreated.

The supplied item NRO initializes a Snake grenade countdown via its native
`snakegrenade::life()` function. Source inspection and API provenance are
under `references/snake_grenade/`. The user supplied the requested body clips,
skeleton and parameter files during this turn; their hashes and raw parameter
rows are recorded in `asset_audit.json`. The donor binary motion list is still
absent, with a pinned public text dump available.

The prototype preserves held items when creation is blocked, validates live
item identity, tracks each owner independently, and drops a held native grenade
before the paired G&W body becomes dormant on swap. Native ItemManager exports
used by the built plugin were checked against the user's main symbol dump.
The previous .g Hero's Spin plugin is backed up in `backups/before-grenade-p1/`.
The shipping tree contains a single updated `libmythra_gamewatch_swap.nro`.

Build and payload checks passed. NRO 151,552 bytes; SHA-256
`23bf74b4236d2cd95dfeb98e7511c40da1d851a898bd8c3e27ac2e91d4e2d238`.
Full test/install/rollback instructions: `references/snake_grenade/PROGRESS.md`.
The immediate Switch gate is real-item creation and native fuse/throw/drop/
pickup with no Snake in the match, then swap cleanup and other-costume Chef.
Capture `[MGW-GRENADE]` lines. No runtime test has been performed by the agent.

## 2026-09-26: fuse lookup crash follow-up, .p2 and .p3

The user's .p2 Switch report repeats the same data abort at
`cross2_Release.nss+0x1674e9c` in `snakegrenade::life()+0xc`, fault address 0.
The initial c07-only Snake resource preload did not make the Snake-specific
`FighterParamAccessor2` entry available (and the supplied log excerpt did not
include the preload diagnostic). Do not reinstall .p1
(`23bf74b4236d2cd95dfeb98e7511c40da1d851a898bd8c3e27ac2e91d4e2d238`) or .p2
(`33bc430f9d067475e6a9b417b7cb77fe5c7128e5325e1dcbc1fa8f4a811d396b`).

Build .p3 hooks the exact `snakegrenade::life()` entry at main offset
`0x1674e90` and returns the game's stock 150-frame fuse value. The native item
script remains responsible for fuse countdown, physics, collision and
explosion. This is a global hook while the plugin is loaded, but the return
value matches the normal Snake grenade fuse. Offline compilation, package
equality, build markers, and Hi3 asset checks pass. Runtime hook resolution and
the item test still need confirmation on Switch. See
`references/snake_grenade/CRASH_ANALYSIS_2026-09-26.md` and `PROGRESS.md`.

## 2026-09-26: the .p3 crash is a stack overflow, and the life() theory is dead

Do not reinstall .p1, .p2 or .p3. All three crash, and none of them crash for
the reason recorded above.

The new Switch report faults at `cross2+0x395fba4`, roughly 14 MB away from
`0x1674e9c`. The `life()` hook is no longer the fault site, so patching
`life()` did not fix anything; it just let execution continue one call further
before it died. Disassembling `references/mythra_gamewatch_feasibility/main_memory.bin`
at the new PC gives a bare prologue and nothing else:

    0x395fba0: sub  sp, sp, #0x20
    0x395fba4: stp  x29, x30, [sp, #0x10]   <== faulting PC

The stack region is `0x598bd3f000`-`0x598be3f000`, 1 MB. SP at the fault was
`0x598bd3efd0`, which is 48 bytes *below* the floor of that region, and the
reported fault address `0x598bd3efe0` is exactly `sp + 0x10`, the `stp`
target. The report's `Fault Address: 0x0` is a red herring.

`ReturnAddress[12]` through `[31]` are twenty identical frames at
`cross2+0x4deff8`, an indirect self-call:

    0x4dedec: ldr  x0, [x8, #0x190]
    0x4dedf0: ldr  x8, [x0]
    0x4dedf4: ldr  x8, [x8, #0xf0]
    0x4dedf8: blr  x8
    0x4dedfc: ...

Atmosphere dumps only 32 stack words with `RA[00]` most recent, so those twenty
are the outermost sliver of a stack that is thousands of frames deep. The call
path is game -> our hook trampoline at `0x08002d54` ->
`sys_line_status_shift_control` -> smashline -> `malloc` (resolved as
`malloc @0x353be80` with `size=0x78`, so `0x353bea4` is `malloc+0x24`) -> a
string/alloc chain in `0x392xxx` -> the prologue above.

No `snakegrenade` frame and no item frame appears anywhere in the new stack.

Note that `main_symbols.json` is not stored in address order; sort it before
bisecting. It holds only 4918 symbols with addresses, topping out at
`0x7447000`, and does not cover `0x395xxxx`, so the crash site can only be
resolved by disassembly.

### Build .p4: the bisect

The Snake grenade is now behind a cargo feature that is off by default, so a
default build contains none of it. `#[cfg(feature = "snake-grenade")]` guards
`mod snake_grenade` itself in `src/lib.rs` plus all three call sites
(`reset`, `drop_before_swap`, `install`), which means the `0x1674e90` hook, the
c07 costume agent and the `0x220` probe status are not compiled into the NRO at
all rather than merely being skipped at runtime. The hot-path `println!` inside
`snakegrenade_life_hook` is now one-shot behind a relaxed `AtomicBool`; it ran
on every call during item init, and the log filled before the faulting frame
could be dumped.

    .p4  f90bf1246f810d6ed2e7f877018d5d1980497fa8d37cf030afcd8fab626ff5ad
         143360 bytes, no MGW-GRENADE strings in the binary

One build, one test, and the result is decisive either way:

- Still overflows: the grenade was never the cause and the bisect moves to the
  hook trampoline and the smashline status dispatch.
- Clean: the native-item strategy cannot be repaired by patching more of the
  Snake item script. The same script also calls `set_life_type`,
  `set_bomb_countdown`, `send_bomb_link_event` at `0x1674eb0`,
  `EffectModule__set_sync_scale_impl` and
  `ModelModule__set_mesh_visibility_impl`, several of which are Snake-param
  bound the same way `life()` was, so each patch unblocks one call and exposes
  the next. The grenade has to be reimplemented as a self-contained projectile
  with no `FighterParamAccessor2` dependency at all.

The known-clean rollback NRO is still
`fafb1edaecc56645ecbefcd499181cb9e1a0f6874bdb258fe08b8876643675ed` in
`backups/before-grenade-p1/`.

## 2026-09-26.c06c07 — user-authorized extension to costume 7 and 8

All enabled c07 replacements and the paired swap now also support c06. Every
move gate, preload gate, pair selection, dormancy and return-handoff costume
check uses the shared `is_target_costume` predicate / `[6, 7]` list. Partner
access also requires the exact owning entry costume. State remains per-entry.
The non-target Hero Spin local vanilla callbacks and all hitbox/kinetic values
are retained. The optional grenade module's filters are extended too, but its
.p4 Cargo feature stays OFF; this build does not resolve the grenade crash.

`tools/extend_costume_assets.py` is now part of deploy.py. It applies the c07
motion delta to stock c06, reuses the 19 compatible clips and adds the existing
sword to the original c06 G&W body. All five model files are read back and
compared after removing the additions: original c06 geometry, skeleton and
materials are preserved. Sword mesh/material/bone/texture references validate.
The sword uses the same injected resources as c07; c06's base appearance stays
intact. Stock c06/c07 skeletons are byte-identical for both fighters.

Offline: release build and full deploy passed, 37 c06 assets validated; all
pre-existing c07 assets remain byte-identical to the pre-extension snapshot.
Motion validation preserves 731 unrelated Elight entries and 744 unrelated
G&W entries (12 added Monkey Flip motions and two fair timing changes). NRO0
header and declared size pass, package matches build, MGW-GRENADE marker absent.
Source comparison confirms unchanged Hi3 game scripts/vanilla ACMD fallbacks.
A supplemental host Rust executable check could not link because the host
resolves GNU link.exe rather than the MSVC linker; no host runtime test is
claimed. The actual Switch-target release compilation succeeded.

NRO: 143360 bytes, SHA-256 `aadadfbfce1abce1f59aedc9182e76d9c3071bf5b713450deb7cb3f6b4542a29`.
Records: `c06-assets-validation.json`, `c06c07-payload-validation.json`.
Snapshot/rollback: `backups/before-c06-extension` (incoming .p4 NRO and source).
Installation, exact SD paths, bounded console tests, expected diagnostics and
rollback are in `INSTALL-C06-C07.md`. Startup identifies `[MGW-SLOTS] build
2026-09-26.c06c07 costumes=[6, 7] grenade=false`. Hero Spin entry logs identify
the actual costume. No Switch runtime test has been performed for this build.
