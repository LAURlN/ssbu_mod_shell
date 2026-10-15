# Handoff: Diddy's Monkey Flip transplanted onto Mr. Game & Watch c07

Written 2026-09-16 so the work can continue from another machine. Read this first,
then `references/diddy_specials/monkey_flip_animation_manifest.json` for the asset
provenance and `DIAGNOSIS.md` for the older swap history.

## Where things stand

**Animation: fixed, and confirmed on hardware.** The user's words: "startup looks
and feels great now". The log signature that proves it: `special_s_start` reports
`observed_end=11.00` and `special_air_s_jump` `observed_end=36.00`, the donor's clip
lengths. Before the fix those same slots reported 17, 24 and 40 frames depending on
what the player had been doing.

Root cause, because it is not obvious and it will recur: the twelve slots in
`motion_list.bin` were mapped to animation file names that exist in **no** base Game
& Watch folder (`d01specialsstart.nuanmb` and friends). The engine parses the entry,
then fails to load that clip, and leaves the previously loaded clip playing. So each
phase lasted exactly as long as whatever was already on screen, and because the
durations seen were 17/24/40 and those are real Game & Watch clip lengths
(a02dash, a02turndash, a02run), the data looked like a timing bug in our statuses
for a long time. Two things made it invisible:

- `MotionModule::motion_kind` reports the hash that was *requested*, so it agreed
  with our request while nothing had swapped.
- Replacing a name that already exists *does* work (the Shulk fair has done so all
  along), which is the mechanism now used: the slots load Game & Watch's own
  animations for the two specials this mod already replaces, and the retargeted
  clips are written over those files.
  - `d01special*` = Judge, the native side-B, replaced by Monkey Flip.
  - `d03speciallw*` = Bucket, the native down-B, replaced by the Mythra swap.
  - `d03speciallwcatch` and `d03specialairlwcatch` are untouched spares.

**Kick: cause found, code fixed, not yet tested.** `monkey_flip_kick_frame` is
pinned at 36. The leap clip is 37 frames (0..36) and the donor's exit order checks
`MotionModule::is_end` before the kick, so the old `elapsed >= 36` window was the
single frame 36, where FALL already wins. It only ever fired because the wrong clip
was playing and the phase ran about 40 frames. The value is now read as the last
frame a kick may start on, so the whole leap is available.

**Grab: still not connecting at any range.** Everything around the box is ruled out
by now: the clip is the donor's, its length is the donor's, the ACMD runs and logs
at frame 7, the anchor name is the one Game & Watch's own working `Catch.txt` uses,
and the argument count is the donor's eight. Also falsified: the victim status (the
generic capture status does not connect either), and spacing. A deliberately
enormous catch box (twelve units, four and a half in front) is deployed to answer
the remaining question, which is not "where is the box" but "is a box created".

## Deployed artifact

NRO `ee040ef0f2dbce4115401806143865842f754087089C818A0D9F73F422D173B3`, 126976
bytes, at `mod_output/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/`.
Copy `mod_output` to the SD root; nothing outside `mod_output` belongs on the card.

## The two open questions, in order

1. **Does the kick work during the leap?** Press attack or special partway through
   the leap. Look for `[MGW-MFLIP] JUMP kick input elapsed=... kick_frame=36
   window_open=true` followed by status `0x212`.
2. **Does the twelve-unit box grab the DK?**
   - If it connects: the CATCH mechanism does work on Game & Watch and only the
     geometry needs tuning to his proportions. Next step is to bring the donor's
     3.0 / 4.0 sizes and 4.5 / 4.0 forward offsets back in gradually, testing as it
     shrinks.
   - If it still does not: the command is not producing a box. Next step is to
     compare our argument layout against the donor call field by field, since the
     remaining suspicion is that `CATCH`'s arguments are not the order assumed
     (`id, bone, size, x, y, z, status, situation`).

## Device move checklist

Carried to a second machine on 2026-09-17 and the paths were repaired there, so this
section now records the portable layout rather than the old machine's absolutes.

- Copy this whole workspace. `mod_files/mythra_gamewatch_swap/target/` is a build
  cache and can be left behind (it is large).
- The game dump is read only and is now kept at `<workspace_root>/export`, which is
  the default. Point `MGW_EXPORT` at it when it lives somewhere else:
  ```
  set MGW_EXPORT=<path to ArcExplorer export>
  ```
  `deploy.py`, `tools/build_monkey_flip_assets.py` and `tools/build_fair_assets.py`
  each derive the default from their own location and all honour the override,
  failing with a clear message if the dump is missing.
- `Cargo.toml` no longer contains any absolute path. Its dependencies (`skyline`,
  `skyline_smash`, `smash_script`, `smashline`) are git dependencies pinned with
  `rev =`, using the revisions read off the old checkout folder names.
  - The `[patch]` sections are gone and must not come back in the form they had.
    Their replacements were the *same git source* as the dependency they patched,
    which cargo rejects outright: "patch for `skyline_smash` points to the same
    source, but patches must point to different sources". They only ever worked
    because the replacements were paths. Nobody could have known that until a
    machine had both the git-only manifest and a working toolchain, which first
    happened on 2026-09-17.
  - Resolution without them leaves `skyline`, `skyline_macro` and `skyline_smash`
    each listed in `Cargo.lock` under two source ids - the bare URL and the `?rev=`
    URL - both pointing at the same commit. That duplication is exactly what the
    old patches collapsed. If a build ever fails on duplicate skyline items, drop
    `rev =` from the four dependencies so their source ids match the ones the
    transitive dependencies use, and let `Cargo.lock` carry the pinned commit.
  - The first build on a new machine needs network access once, and
    `build-diagnostic.ps1` passes `--offline`, so it fails until
    `.cargo/git/checkouts` has been populated. Run `cargo fetch` inside
    `mod_files/mythra_gamewatch_swap` once while online.
  - Because the path dependencies are gone, any local edits that had been made
    inside the old checkouts are no longer part of this manifest. If the old build
    depended on such edits, they have to be re-applied as patches.
- Toolchain: rustup, `cargo-skyline`, and Python with `ssbh_data_py`.
  - Corrected 2026-09-17. The earlier note that nothing was installed on the second
    machine was wrong: `%USERPROFILE%\.cargo` and `%USERPROFILE%\.rustup` both
    existed with two stable toolchains, and `~/.cargo/bin` already held `cargo.exe`
    and `rustc.exe`. `rustc is not recognized` was purely a `PATH` problem - the
    shell VSCode spawns does not include `~/.cargo/bin`. What was genuinely missing
    was `cargo-skyline` and `~/.cargo/git/checkouts`, and `build-diagnostic.log`
    shows the NRO tested through 2026-09-16 was built on another machine entirely
    (`local Cargo checkout`), so this one had never compiled the
    crate at all.
  - Working recipe here, in order:
    1. `winget install --id MSYS2.MSYS2 -e`. There is no Visual Studio on this
       machine, and `devkitPro install` contains only `msys2`, with no Switch toolchain
       and no binutils.
    2. `MSYS2 usr/bin/pacman.exe -Sy --noconfirm`, then `-S --noconfirm
       mingw-w64-x86_64-binutils mingw-w64-x86_64-gcc`. rustup's own bundled
       `dlltool` cannot build import libraries because `rust-mingw` ships no
       `as.exe`; it fails with "dlltool.exe: CreateProcess".
    3. Put `%MSYS2_MINGW_BIN%` ahead of rustup's self-contained binutils
       directory and `%USERPROFILE%\.cargo\bin`, then
       `cargo +stable-x86_64-pc-windows-gnu install cargo-skyline`. The GNU host
       toolchain works; the MSVC one cannot link here at all, because
       `c:\devkitPro\msys2\usr\bin` puts GNU coreutils' `link.exe` first on PATH,
       which fails with "link: extra operand".
    4. Every new shell needs `%USERPROFILE%\.cargo\bin` on PATH before
       `cargo skyline build`; the environment does not carry it.
  - `cargo-skyline` 3.5.0 is the correct version despite the numbers looking
    unrelated to skyline 0.6.0: the pinned skyline-rs revision 6b52d32 is dated
    2026-02-18 and cargo-skyline 3.5.0 was released 2026-02-20. Check the commit
    date rather than inferring from version numbers - inferring sent me to 2.2.2
    first, which was wrong.
  - Python is 3.8.10 and `ssbh_data_py` is still not installed, so the motion asset
    tools cannot run here yet. The NRO build does not need them.
- Build and deploy, from the workspace root:
  ```
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Set-Location 'mod_files/mythra_gamewatch_swap'; ./build-diagnostic.ps1"
  python mod_files/mythra_gamewatch_swap/deploy.py
  ```
  The first is the NRO build (`--features swap-diagnostics`), the second rebuilds all
  motion assets, copies the NRO and the two elight animations, and prints the SHA-256.
- Verify the payload without the console:
  `python scratch/check_deployed_mflip.py` (needs `MGW_EXPORT`) and
  `python scratch/decode_log_names.py` for naming status ids and motion hashes.
- Verify the workspace is still portable after any further move:
  `python scratch/verify_portable_paths.py`. It asserts that every pipeline script
  derives the workspace root from its own location, that the hop counts are correct
  (`deploy.py` needs three `os.path.dirname` calls, while the tools one directory
  deeper need `parents[3]`), and that no live line in the pipeline names a drive path.
  Comments are excluded from the scan, because they deliberately quote the old paths.
- PowerShell execution policy blocks `build-diagnostic.ps1` on a fresh profile; the
  `-ExecutionPolicy Bypass` above is required, not optional.
- Two terminal traps that cost time during the move: the default shell in this
  project has been `cmd.exe`, so `Get-ChildItem` and friends fail when typed directly
  and have to be run as `powershell -NoProfile -Command "..."`; and a bare `| find`
  resolves to the MSYS `find`, which walks the entire filesystem instead of counting
  lines.

## Traps already paid for, do not repeat

1. **Newly added animation names never load.** Only names that already exist in the
   base install are replaced and loaded. Added names are silently ignored.
2. **`MotionModule::motion_kind` is not evidence that a clip loaded**; it echoes the
   request.
3. **`end_frame` told the truth** about the clip that was playing. The error was
   assuming that clip was ours.
4. `deploy.py` used to run `references/inject_monkey_flip.py`, which copies Diddy's
   files byte for byte, so every deploy silently reverted any retargeting.
5. `smash_script::macros::CATCH` always pushes **eleven** arguments; a `None` becomes
   an empty value rather than an omission, and the donor call has eight. We push the
   donor's eight directly through `smash::app::sv_animcmd::CATCH`.
6. `motion_path` in `motion_list.bin` is not the folder animations are read from:
   vanilla Game & Watch c07 names `c00` as well.
7. Do not guess status ids. `0xE` is FALL, `0x41/0x42/0x43/0x46` are the *player*
   being captured and thrown, `0x48/0x49` are DAMAGE_AIR/DAMAGE_FLY, `0x75`-`0x7C`
   are cliff states. `scratch/decode_log_names.py` names them from
   `lua_const.rs` instead.
8. The visibility group's node names are **bone** names, not mesh object names: 0 of
   the 94 visibility nodes overlap the 98 mesh objects of the c07 model. A check that
   compares the two is meaningless.
9. In `motion_list.bin`, the animation name hash includes the extension:
   `hash40('d01specials.nuanmb')`.
10. Rewriting a motion's carrier means the *file* holds the new clip, so the
    carrier's own move would animate wrongly if it were still reachable. Both
    carriers belong to specials this mod replaces.

## Known loose ends

- Four recipient nodes get no donor track although Game & Watch normally animates
  them: `BodyHaveN`, `HeadHaveN`, `Sparky`, `TopHave`. They hold their rest pose for
  every phase of this move. The other four uncovered nodes, `H_ArmL`, `H_ArmR`,
  `H_KneeL`, `H_KneeR`, appear in 0 of 323 Game & Watch motions and are inert.
- The leap's floor clip is a single frame shorter than the pinned kick frame, which
  is the whole reason the kick needed reinterpretation. If the donor's counter turns
  out to start somewhere other than zero, the window should be re-derived rather than
  kept.
- The catch box's growth spurt from 3.0 to 12.0 is a diagnostic and must be reduced
  before this is playable.
