# 0.9.0-moves install record - 2026-10-07 (session 5)

Scope the user set: "install all 9", then "or everything that is ready to install". Of the nine
move units in `research/moves/`, only two are DONE and checked offline: `tilt_up__miifighter`
(Brawler up tilt) and `tilt_down__miifighter` (Brawler down tilt). Not installed:
- `normal_jab__miifighter`: PARTIAL, stages 1-2 only; its report says the rapid-jab stages are a stand-in.
- `special_up__cloud`, `special_neutral__snake`, `aerial_forward__cloud`, `aerial_up__kamui`:
  PARTIAL, stop conditions hit, nothing built.
- `aerial_back__mario`, `smash_up__fox`: IN PROGRESS, no deliverable.

## Built and installed

Plugin `builds/0.9.0-moves/libmii_customizer.nro`, sha256 `21494f052fdd74f8bdf808f080376d56e41a9efd452443b456a42cfc65b171df`
(build log `builds/.cache/build-0.9.0.log`: 0 warnings; `tools/stack-frames/stack_frames.py` OK;
host menu tests `scratch/2026-10-06_P11-MENU/run_host_test.sh`: 35 passed, 0 failed).

Source change (`plugin/`, from 0.8.0): `src/unit_tilt_up.rs` and `src/unit_tilt_down.rs` are the unit
files copied unchanged; `src/moves.rs` gets `owned_status_main` plus hooks for `ATTACK_HI3` (43) and
`ATTACK_LW3` (44), and registers both units' ACMD scripts; the forward-tilt hook is unchanged.
`src/menu.rs` IMPLEMENTED_MOVES now lists tilt_side, tilt_up, tilt_down (all `miifighter`).
Backup of 0.8.0 source: `scratch/2026-10-07_session5/plugin_src_0.8.0/`.

Package `builds/0.9.0-moves/mii_customizer_moves/` (card: `ultimate/mods/mii_customizer_moves/`):
merged list of 779 entries = vanilla Gunner (774) + forward tilt (3) + up tilt (1) + down tilt (1);
one `motion_list.motdiff` (75b1a279...), built by `scratch/2026-10-07_session5/build_merged_package.py`,
which proved that the patch applied to the vanilla list reproduces the merged list byte for byte.
Full list: `gamedata/mii_customizer/S5-MERGE/reference/motion_list_vanilla_plus_owned.bin`.
Menu `builds/0.9.0-moves/session/menu.txt` = 0.8.0 menu + `allow tilt_up miifighter` + `allow tilt_down miifighter`.

## Card (E:, "SWITCH SD") - installed 2026-10-07 after the user's "install" in chat

| file on card | bytes-sha256 (first 16) | matches build |
|---|---|---|
| `atmosphere/.../skyline/plugins/libmii_customizer.nro` (was 0.8.0 `0193ba5f...`) | 21494f052fdd74f8 | yes |
| `ultimate/mii_customizer/menu.txt` (was the 0.8.0 menu) | f268b3eba293ebd9 | yes |
| `ultimate/mods/mii_customizer_moves/config.json` | 912d567cede1c584 | yes (sha compared, all 7 files) |
| `.../c00/motion_list.motdiff` | 75b1a27947c8baf5 | yes |
| `.../c00/c01mcmiifighterattackhi3.nuanmb` (new) | 1d70f70d2dba773d | yes |
| `.../c00/c01mcmiifighterattacklw3.nuanmb` (new) | f0b1b4099cbfffb0 | yes |
| `.../c00/c01mcattacks3{s,hi,lw}.nuanmb` (unchanged P16 clips) | as in CURRENT_INSTALL | yes |

Before the install: `evidence/2026-10-07_session5/card_before_0.9.0/` (plugin 0.8.0, menu,
package folder, log) with `SHA256SUMS.txt`. The 0.8.0 boot-3 log was renamed on the card to
`ultimate/mii_customizer_log_session4_boot3.txt` (copy in the backup folder). Other plugins were not
touched (their files are unchanged in the directory listing; no hashes were recorded for them).

## Verified / not verified

- Verified offline: build, stack frames, host menu tests, motdiff round trip, card hashes.
- Not verified: anything in the game. Nothing of 0.9.0 has run. Tier D until the user's console run.
- Known risk: the motion patch applies on top of the other mod's Gunner `motion_list.bin` (as in 0.8.0);
  check `ultimate/arcropolis/conflicts.json` after the boot.

## Console test to run (about 6 steps)

1. Boot, open Mii maker, Mii Gunner with "Up Tilt: Mii Brawler" set (menu row "Up Tilt" is now selectable).
2. Up tilt on that Gunner: it should use the Brawler up-tilt animation; a second Gunner with vanilla up tilt in the same match should be unchanged.
3. Set "Down Tilt: Mii Brawler" on the same Gunner, then down tilt: the Brawler down-tilt animation should play.
4. Forward tilt still works as before (0.8.0 check).
5. Read `ultimate/mii_customizer_log.txt` after the match: expect `MV|chosen=tilt_up|kind=43` and `MV|chosen=tilt_down|kind=44` lines.
6. If the bind pose freezes, check `ultimate/arcropolis/conflicts.json` and the log for `MV|missing` lines; report the log and the card's `conflicts.json`.
