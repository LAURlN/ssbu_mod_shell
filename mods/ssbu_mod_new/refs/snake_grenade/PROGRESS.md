# G&W c07: actual Snake grenade

## Current deliverable: bisect build with the grenade compiled out, 2026-09-26.p4

    NRO   f90bf1246f810d6ed2e7f877018d5d1980497fa8d37cf030afcd8fab626ff5ad
    size  143360 bytes

This build contains none of the Snake grenade code. A new cargo feature
`snake-grenade`, off by default, gates `mod snake_grenade` in `src/lib.rs`
along with its three call sites, so the `0x1674e90` `life()` hook, the c07
costume agent and the `0x220` probe status are not compiled in rather than
being skipped at runtime. Confirm with
`grep -ac MGW-GRENADE libmythra_gamewatch_swap.nro`, which must print 0.

Install this one and report what happens on a normal match with c07, no
grenade attempt. Do not test the neutral-B grenade in this build: it is not
present.

The result is decisive either way. If it still crashes, the grenade was never
the cause and the search moves to the hook trampoline and the smashline status
dispatch. If it is clean, the native-item strategy is unfixable by patching
more of the Snake item script, because that script reaches Snake-bound
parameters through several functions, not just `life()`, and each patch unblocks
one call and exposes the next. The grenade then has to be rewritten as a
self-contained projectile. See DIAGNOSIS.md for the disassembly.

## Previous deliverable: native object test with fuse fallback, 2026-09-26.p3

Superseded, and it must not be reinstalled. The .p1, .p2 and .p3 builds all
crash. The cause was diagnosed as a null read in `snakegrenade::life()`; that
was wrong. The real fault is a stack overflow from runaway recursion, at
`cross2+0x395fba4`, roughly 14 MB away from the `life()` code. Patching
`life()` only moved the crash one call further along. The full evidence is in
`mod_files/mythra_gamewatch_swap/DIAGNOS.md` under "the .p3 crash is a stack
overflow".

The text below describes what .p3 was built to do, kept for history.

`src/snake_grenade.rs` is installed on Game & Watch c07 only, with both
Smashline's costume filter and runtime fighter/costume checks. Neutral-B
interrupts Chef into the reserved custom status 0x220, creates the real
`ITEM_KIND_SNAKEGRENADE` (0x96), and returns to the normal wait/fall status.
Use standard item controls: A to throw, grab to drop. This first test limits
creation to one owned grenade at a time. It does not yet reproduce Snake's
pull animation, B-release throws, three throw strengths or hold movement.
Those are explicitly outstanding full-port work, not claimed native parity.

The .p1 and .p2 tests both crashed while the item initialized its fuse if Snake
was not in the match. Atmosphere reported a null read at
`cross2_Release.nss+0x1674e9c`, inside `snakegrenade::life()+0xc`. The .p2
preloaded Snake's NRO and fighter resources, but that did not initialize the
missing parameter-accessor entry. The .p3 build hooks that exact function and
returns the stock fuse value, 150 frames (2.5 seconds), so the native item
script can continue. The native item still handles the countdown, physics,
hitboxes and explosion. The hook is global while this plugin is loaded; it
returns the stock fuse value for Snake grenades regardless of who creates one.
It did not work: .p3 crashed too, at a different address, as a stack overflow.

The item itself uses the game's existing grenade fuse, physics, hitboxes and
effects. The plugin neither recreates the explosion nor edits the item's
parameters. A zero-speed native drop releases a held grenade before the paired
G&W body becomes dormant during the Mythra swap. Other held items are preserved
when neutral-B is pressed. Creation is refused if the native item manager is
unavailable or an owned grenade is already active. Observation state is tagged
with the fighter object ID and reset at fighter-entry initialization.

## Evidence

- `manifest.json`: 110 pinned public status and motion-list reference files.
- `recipient_status/SpecialN__pre.c` and its manifest: native G&W entry setup,
  reproduced as a defensive fallback for any unexpected non-c07 dispatch.
- `native_item_inspection.txt`: user's 13.0.4 item NRO initializes the native
  grenade countdown through `snakegrenade::life()` at NRO-relative 0x7c921c
  and `item::set_bomb_countdown()` at 0x7c9254. These are analysis addresses;
  the mod does not hook them or transplant their callbacks.
- `asset_audit.json`: newly supplied Snake skeleton, 14 body-motion references
  (including shared clips), and `vl.prc` parameter rows with SHA-256 hashes.
  The binary body motion_list.bin remains absent; the pinned textual motion
  list is available. Its absence does not affect this native-item test.
- Native `ItemManager` singleton, owned-item count and `ItemModule::have_item`
  imports in the built NRO all exist in the supplied main executable's exports.

## Install and test

Built/package: `mod_output/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmythra_gamewatch_swap.nro`

Install at `sd:/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmythra_gamewatch_swap.nro`,
replacing the existing file. Keep one installed version of this plugin. The
existing animation package stays installed; this test adds no animation files.
The binary includes the Hero's Spin .g turnaround fix.

SHA-256: `3315323b8e8884448384f9e674902d1c07445a921271d576cc4baa4affcd23368`

1. Start a match with no Snake present. On c07 G&W, press neutral-B once.
   Confirm the game no longer crashes and the actual grenade appears. The log
   should show `before-have` followed by
   `[MGW-GRENADE] native life lookup fallback: 150 frames`.
2. Hold one until it explodes. Then create another and throw with A; create
   another and drop with grab. Check bounce and explosion, and let an opponent
   pick up a dropped grenade. Test with no other item held first.
3. Try neutral-B with a held item or with your grenade still active: the test
   should refuse another spawn. It must work again once that grenade is gone.
4. On the paired c07, pull one and swap to Mythra: the grenade should be dropped
   into the stage before G&W disappears, then finish its native fuse normally.
5. Test another G&W costume's Chef, and Mythra c07's Hero's Spin turnaround.

Send the `[MGW-GRENADE]` log lines with observations. `before-have` identifies
the creation attempt, `spawned ... kind=0x96` confirms the native item identity,
`item-state` records its native status changes, and `drop-before-swap` records
release at the swap boundary. `item-gone` alone does not prove an explosion;
verify that visually. `observed_frames` is a fighter callback count, not a
precise item lifetime measurement, and stops while the owner is dormant.

Rollback: replace the installed NRO with
`mod_files/mythra_gamewatch_swap/backups/before-grenade-p1/libmythra_gamewatch_swap.nro`
(the prior .g build, SHA-256
`fafb1edaecc56645ecbefcd499181cb9e1a0f6874bdb258fe08b8876643675ed`).

## Verification and next gate

Offline build and payload checks passed, including NRO header/size, exact
built-versus-packaged equality, grenade .p3/life-hook and Hero's Spin .g markers,
and the existing Hi3 motion manifest. Results:
`mod_files/mythra_gamewatch_swap/backups/after-grenade-life-hook/payload-validation.json`.
The crashing .p1 NRO had SHA-256
`23bf74b4236d2cd95dfeb98e7511c40da1d851a898bd8c3e27ac2e91d4e2d238`; .p2
also crashed at the same instruction (SHA-256
`33bc430f9d067475e6a9b417b7cb77fe5c7128e5325e1dcbc1fa8f4a811d396b`). Do not
reinstall either one. No Switch runtime result exists yet. Do not label this a completed Snake
neutral-B port until the native object test passes and the dedicated input,
motion, limit and throw behavior has been implemented and tested.

After that gate: retarget the supplied clips, trace native throw velocities
and constraints from the supplied parameters/native code, implement startup,
hold and three throw variants, and verify interruption/landing/swap cleanup.
