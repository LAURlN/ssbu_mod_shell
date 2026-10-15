# Mii Swordfighter Hero's Spin (`Hi3`) onto Mythra c07

## Correct donor identity

`Hi1` is Stone Scabbard (upward leap, downward sword thrust). `Hi3` is Hero's
Spin. The existing `references/miiswordsman_special_hi/PLAN.md`,
`src/hero_spin.rs` and its older asset builder implement `Hi1` and are retained
as historical source only. The 2026-09-26.a build installs `src/hero_spin3.rs`.

## Game dump inventory, 2026-09-26

Donor motion-list source:
`references/miiswordsman_special_hi/motion_list_body_c00.yml:4144-4263`.

| Donor slot | Expected clip | Present in local `export/` |
| --- | --- | --- |
| `special_hi3_start` | `d02specialhi3start.nuanmb` | Yes, 20,864 bytes |
| `special_hi3_hold` | `d02specialhi3hold.nuanmb` | Yes, 22,912 bytes |
| `special_hi3` | `d02specialhi3.nuanmb` | Yes, 40,376 bytes |
| `special_air_hi3` | `d02specialairhi3.nuanmb` | Yes, 44,024 bytes |

The four verified source files are under
`dumps\arc\fighter\miiswordsman\motion\body\c00\`.
Their SHA-256 hashes and the retargeted output hashes are recorded in
`animation_manifest.json`. No `Hi1` clip is used in the new package.

## Implementation facts already available

- Local ACMD dumps contain `SpecialHi3Start.txt`, `SpecialHi3Hold.txt`,
  `SpecialHi3.txt` and `SpecialAirHi3.txt` under
  `SSBU-Dumped-Scripts-main/smashline/lua2cpp_miiswordsman/miiswordsman/`.
- `SpecialHi3.txt` and `SpecialAirHi3.txt` have the actual spin hitbox schedules;
  `SpecialHi1End.txt` has a downward-stab effect. The two option families must
  not be mixed.
- Status dumps for `SpecialHi3Hold` and `SpecialHi3End` are under the older
  `references/miiswordsman_special_hi/status/`. The hold loop enters End after
  release or motion end, and End switches between ground and air motions.
- The donor's End code calls
  `FIGHTER_KINETIC_TYPE_MIISWORDSMAN_SPECIAL_AIR_HI3`, which cannot be assumed
  valid for Mythra. A recipient-authored kinetic solution needs separate
  verification.
- The present `src/hero_spin.rs` replaces game ACMD only. Mythra's native
  effect, sound and expression scripts still run on its up-B motion slots and
  likely contribute to the reported mixed presentation. Verify on console.

## 2026-09-26.a offline result

`tools/build_hero_spin3_assets.py` parsed all four clips and retargeted 64
surviving transform tracks to Mythra c07. It patched three recipient motion-list
entries and verified 731 unrelated entries remained byte-identical. The game
ACMD bodies were generated from the local Hi3 dump by
`tools/generate_hero_spin3_acmd.py`; the generated file records each input hash.
`src/hero_spin3.rs` owns ground start, hold, release spin, and aerial spin for
c07, while other colours call vanilla statuses and ACMD. Native Mythra visual,
sound and expression scripts are suppressed on the four played c07 slots.
The Mii effect and sound resources are absent from Mythra's bank.

The donor's Hi3 End calls a dedicated Mii kinetic type. The recipient uses
Mythra's aerial jump kinetic until a console test establishes its behaviour.
The dumped `param_special_hi` `hi3_*` fields in Mii's `vl.prc` are all zero;
no guessed Mii acceleration or speed was added. The next step is a bounded
ground tap, ground hold/release, aerial use and other-costume Switch test.

## First Switch result and build 2026-09-26.b

Ground Hi3 plays and feels approximately right to the user; sword effects are
absent by design for now. The first aerial test stopped at frame 0. Its Skyline
log showed `AIR_SPIN` entered and the 85-frame motion loaded, then kinetic 6
and situation 0 caused an immediate landing transition. Build .b assigns air
Pre settings through a dedicated callback instead of inferring the incoming
status from `StatusModule::status_kind` during Pre. Awaiting console retest.

## Build 2026-09-26.d and .c trace

The .c log shows the air spin peaks near frames 24-32, then descends. Several
attempts land between frames 29 and 45, while the final air hitbox begins at
frame 47. Build .d reduces the applied Mii-derived gravity acceleration by a
further 15% and terminal fall speed by 10% to extend airtime through the final
hit. This is a feedback-driven trial. The Mii probe did not appear in the
provided log, so a direct trajectory comparison is still pending.

## Build 2026-09-26.c

The user confirmed air Hi3 now plays, but its fast fall prevents the last hit
and both versions lack a sword trail. The common fighter-parameter dump shows
Mii Swordfighter air acceleration `0.106` and terminal fall speed `1.55`,
versus Mythra `0.137` and `1.87`. Build .c applies the Mii common values for
the duration of the air spin, and uses Mythra's own sword afterimage texture
and attachment in both ground and air effects. The Mii-specific Hi3 kinetic
cannot be reproduced exactly from the available status code and zero-valued
Hi3 special params; the build includes read-only height logs for both fighters
to support a direct comparison after the next Switch test.
