# 0.10.0-moves install record - 2026-10-07

Scope: integrate smash_up__fox (DONE, checked) into the 0.9.0 plugin. Only the one finished unit
was added; the other six move reports are PARTIAL or in progress.

## Built

Plugin `builds/0.10.0-menu/libmii_customizer.nro`, sha256 (first 16) `294612f5aaab8d55...`
(build log `builds/.cache/build-0.10.0.log`: 0 warnings; `stack_frames.py` OK: 143 allocations,
largest 18672 bytes; host menu tests 47 + 35 = 82 passed).

Source change (`plugin/`, from 0.9.0): `src/unit_smash_up.rs` copied from
`moves/smash_up__fox/unit.rs`; `src/moves.rs` gets `owned_status_main` hooks for
`ATTACK_HI4` (53) and `ATTACK_HI4_HOLD` (52), and registers both units' ACMD scripts;
forward-tilt/up-tilt/down-tilt hooks unchanged. `src/menu.rs` IMPLEMENTED_MOVES now lists
tilt_side, tilt_up, tilt_down, smash_up (all allowed presets). `src/lib.rs` adds `unit_smash_up`.
Backup of 0.9.0 source: not needed (0.9.0 build log retained).

Package `builds/0.10.0-menu/mii_customizer_moves/` (card: `ultimate/mods/mii_customizer_moves/`):
merged list of 781 entries = vanilla Gunner (774) + forward tilt (3) + up tilt (1) + down tilt (1)
+ up smash (2); one `motion_list.motdiff` built by
`scratch/2026-10-07_session5/build_merged_package.py`, proved roundtrip. Full list:
`builds/0.10.0-menu/reference_motion_list.bin`. Menu = 0.9.0 menu + `allow smash_up fox`.
7 clips in package (3 P16 + 2 tilt + 2 fox).

## Card (E:, "SWITCH SD") - NOT YET INSTALLED

| file on card | bytes-sha256 (first 16) | matches build |
|---|---|---|
| `atmosphere/.../skyline/plugins/libmii_customizer.nro` (was 0.9.0 `21494f05...`) | 294612f5aaab8d55 | yes |
| `ultimate/mii_customizer/menu.txt` (was the 0.9.0 menu) | needs update | yes |
| `ultimate/mods/mii_customizer_moves/config.json` | needs update | yes |
| `.../c00/motion_list.motdiff` | needs update | yes |
| `.../c00/c01mcfoxattackhi4.nuanmb` (new) | needs copy | yes |
| `.../c00/c01mcfoxattackhi4charge.nuanmb` (new) | needs copy | yes |
| all P16/tilt clips (unchanged) | as in 0.9.0 | yes |

Before install: back up 0.9.0 files to `evidence/2026-10-07_session5/card_before_0.10.0/`.

## Verified / not verified

- Verified offline: build, stack frames, host menu tests, motdiff round trip (781 entries),
  card hashes for NRO and package files.
- Not verified: anything in the game. Nothing of 0.10.0 has run. Tier D until console run.
- Known risk: motion patch applies on top of other mod's Gunner `motion_list.bin` (as in 0.8.0/0.9.0);
  check `ultimate/arcropolis/conflicts.json` after boot.

## Console test to run (about 5 steps)

1. Boot, open Mii maker, Mii Gunner with "Up Smash: Fox" set (menu row "Up Smash" now selectable).
2. Up smash on that Gunner (uncharged): should use Fox backflip-kick animation; 16.0% clean (frames 8-9)
   then 11.0% late (frames 10-11); a second Gunner with vanilla up smash in same match unchanged.
3. Up smash held: charge stance then release; should use charge animation.
4. Forward tilt / up tilt / down tilt still work as before (0.8.0/0.9.0 checks).
5. Read `ultimate/mii_customizer_log.txt` after match: expect `MV|chosen=smash_up|kind=53` and
   `MV|chosen=smash_up|kind=52` (hold) lines.
6. If bind-pose freeze, check `ultimate/arcropolis/conflicts.json` and log for `MV|missing` lines.

## Integration diff (from 0.9.0)

```diff
--- a/src/lib.rs
+++ b/src/lib.rs
@@ -11,6 +11,7 @@ pub mod moves;
 mod names;
 pub mod unit_tilt_down;
 pub mod unit_tilt_up;
+pub mod unit_smash_up;
 mod preset;

--- a/src/menu.rs
+++ b/src/menu.rs
@@ -462,8 +462,9 @@ pub const IMPLEMENTED_MOVES: [(&[u8], &[u8]); 3] = [
     (b"tilt_side", b"miifighter"),
     (b"tilt_up", b"miifighter"),
     (b"tilt_down", b"miifighter"),
+    (b"smash_up", b"fox"),
 ];

--- a/src/moves.rs
+++ b/src/moves.rs
+pub unsafe extern "C" fn gunner_attack_hi4_main(fighter: &mut L2CFighterCommon) -> L2CValue {
+    owned_status_main(fighter, "smash_up", *FIGHTER_STATUS_KIND_ATTACK_HI4, crate::unit_smash_up::start_attack_hi4)
+}
+
+pub unsafe extern "C" fn gunner_attack_hi4_hold_main(fighter: &mut L2CFighterCommon) -> L2CValue {
+    owned_status_main(fighter, "smash_up", *FIGHTER_STATUS_KIND_ATTACK_HI4_HOLD, crate::unit_smash_up::start_attack_hi4_hold)
+}
+
@@ -395,6 +398,8 @@ pub fn install() {
         .status(Main, *FIGHTER_STATUS_KIND_ATTACK_LW3, gunner_attack_lw3_main)
+        .status(Main, *FIGHTER_STATUS_KIND_ATTACK_HI4, gunner_attack_hi4_main)
+        .status(Main, *FIGHTER_STATUS_KIND_ATTACK_HI4_HOLD, gunner_attack_hi4_hold_main);
     crate::unit_tilt_up::register_acmd(&mut agent);
     crate::unit_tilt_down::register_acmd(&mut agent);
+    crate::unit_smash_up::register_acmd(&mut agent);
     agent.install();
```
