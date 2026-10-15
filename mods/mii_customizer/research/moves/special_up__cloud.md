# MV-special_up__cloud - Cloud's up special (Climhazzard) on Mii Gunner

Task: MV-special_up__cloud (built with MV-aerial_forward__cloud: one plugin copy, one sword article, shared
effect/sound/trail additions). Date: 2026-10-14. Status: **BUILT OFFLINE** - status logic decoded from Cloud's
NRO and re-implemented, six clips retargeted, plugin copy builds, checks pass. Nothing has run in game.
Tiers: B = measured offline by a named script; D = for the console. Paths mod-relative unless marked
workspace-relative.

## 1. What the move is now

| part | how | tier |
|---|---|---|
| first press | Cloud's SPECIAL_HI: the common `super_jump_punch` framework with his `param_special_hi[0]` (lr stick 0.25, dir stick 0.625, dir mul 3.0, pass mul 1.0 / air 1.1, air accel y 0.5, air start x mul 0.67, fall x mul 0.6, landing frame 20), end status FALL_SPECIAL | B decode, D behaviour |
| rise | `mc_cloud_special_hi` / `_air_hi` (66 frames, Cloud's clips retargeted, root motion x 0.98/1.15 so the rise keeps Cloud's world height); SA_SET air f8, MOVE_TRANS f9, motion rate 0.8 from f25 | B |
| hitboxes | f7 three `top` boxes 3% (40/78/102 deg, set-off THRU), f10-12 `haver` boxes 4% (94/96/90/85/96/90 deg), clear f16; dive f12 of special_hi2: 4.5% 262 deg (air) and 45 deg; dive landing 3.5% 64 deg size 8, f1-3 | all args = decode (check.py), B |
| ledge | cliff check ALWAYS at f7, ALWAYS_BOTH_SIDES at f23 (`notify_event_msc_cmd 0x2127e37c07`), common `super_jump_punch_main` handles the grab; dive: NONE at start, ALWAYS +10, BOTH_SIDES +20 | B decode, D |
| second press | Cloud's main loop (0x1d5b0): attack/special pressed after f16 (SHIFT_RESERVE) is buffered; from f20 to f27 (SHIFT) a press or the buffer -> dive status | B |
| no second press | clip end -> FALL_SPECIAL; f25 on: air control at `air_speed_x_stable * 0.6`; falling onto ground -> FALL_SPECIAL -> landing 20 frames | B |
| dive | own statuses 0x220 HI2 (12-frame start, AIR_STOP, gravity accel -0.07, max 4.2), 0x221 HI2_FALL (speed -4.2, 50 frames, then `special_hi2_end` and FALL_SPECIAL; keeps the hitbox: FS_SUCCEEDS_KEEP_ATTACK), 0x222 HI2_LANDING (40-frame landing, common landing init/exec/exit, `status_landing_fall_special_air_fall_special`) | B |
| no tech | Cloud's CHECK_ATTACK (0x3350) + 0x1cd60: fighters hit by the dive lose their 6 PASSIVE transition terms while in DAMAGE_FLY / ROLL / METEOR | B, D |
| sword | Buster Sword article in the right hand; left hand from dive frame 9 (Cloud's `VisibilityModule::set_int64("sword","sword_l")`), back to the right at end frame 10 / landing frame 23; removed when the Gunner leaves Cloud's motions | B files, D |
| effects | speed lines (tinted 1/0.965/0.376), sword glow `cloud_climhazzard_sword`, sting, slash, slash2/3, `sys_atk_smoke`, `sys_v_smoke_a`, `sys_smash_flash`, `sys_crown`, `sys_down_smoke`; ribbon `tex_mc_cloud_sword1_red`/`tex_mc_cloud_sword2` f8-19 (air f9-19) | B |
| sounds | `se_cloud_special_H01` f1, `_H02` f10, `_H03` dive f3, `_H04` landing f2; Mii voice `seq_miigunner_rnd_attack03` (rise) / `_attack02` (dive) where Cloud plays `seq_cloud_rnd_special_h01/h02` | B; voice = difference |

Decoded functions (lua2cpp_cloud.nro sha256 `dd65acec...`): SPECIAL_HI pre 0x22ef0 / main 0xc140 / loop 0x1d5b0 /
end 0x9290 (callback 0xb900 -> common `super_jump_punch_reset_common_condition`); HI2 pre 0x232d0, main 0xd020,
loop 0x1d220, end 0x9300, check_attack 0x3350; HI2_FALL pre 0x236b0, main 0xd7e0, sub status 0x1c640, loop
0x1c820, end 0x9400; HI2_LANDING pre 0x23af0, init/exec/exit = common `sub_landing_uniq_process_*`, main 0xdf00,
end 0x95c0. ACMD: 22 scripts (table `gamedata/.../special_up__cloud/tables/acmd_calls.json`, flag/const names
added by `scratch/2026-10-08_MV-aerial_forward__cloud/re/acmd_listing.txt`). The earlier note that HI2_LANDING
had Cloud-specific INIT/EXEC/EXIT was a mis-attribution of the scan; they are common landing functions.

## 2. Integration

Statuses: SPECIAL_HI Pre/Init/Exec/Main/End are wrapped in `moves.rs`. Pre decides per press
(`mii_chose("special_up")`, sword article registered, all six motions loaded) and stores it in
`mccloud::State.upb`; the other lines follow it, else the Gunner's own function (or 0 where the Gunner has
none: Init/Exec exist only for two of its three up specials - `smashline::original_status` would panic there,
so `mccloud::vanilla_status` asks Smashline and returns None). New statuses 0x220-0x222 are registered on
`miigunner` (`unit_special_up_cloud::register_statuses`); FIGHTER_MIIGUNNER_STATUS_KIND_NUM is 0x1FA, the
coordinator owns the final ids (three consts). Work variables: `mccloud::State` per entry id.

Plugin diff, build, stack check: see `research/moves/aerial_forward__cloud.md` section 2 (one copy for both;
NRO sha256 `5d88a98c4cc1fd93...`, build exit 0, stack check OK).

Assets (`python -I mods/mii_customizer/moves/special_up__cloud/build_assets.py`, 2026-10-11): six clips
(66/66/12/2/20/36 frames) in `gamedata/mii_customizer/moves/special_up__cloud/package/`, reference motion list
774 + 6 entries (sha256 `78a8066d7a136362...`). Sword, trails, effect and sound additions come from the
forward-air unit (`gamedata/mii_customizer/moves/aerial_forward__cloud/`, see that page section 3-4; this
script builds them first if missing). Coordinator: menu `allow special_up cloud`, `new-dir-files` for the six
clips, merge the six motion entries.

Check: `python -I mods/mii_customizer/evidence/moves/special_up__cloud/check.py` -> `ALL CHECKS PASSED`, exit 0
(manifest, the six entries vs code names and Cloud's entries, 12 ATTACKs x 36 args vs decode, 14 params vs
vl.prc, effect/trail/sound names vs merged banks, sword assets).

## 3. Differences from Cloud

- Limit Break versions not ported (no gauge on a Gunner); battle-log notifications of Cloud's main left out.
- Voice: the Mii's own sequences (above).
- Effect handles prefixed `mc_cloud_`; sword-glow/flare names that Cloud reads from instance work ids are named directly (Buster Sword variants).
- Sword = article tied to the Gunner's hand bones (it sits in the arm-cannon hand), not a body mesh.
- Clips retargeted (18 donor-only nodes dropped); root motion scaled by model scale ratio (that the engine scales root motion by model scale is D).

## 4. Console test (at most 8 steps, same package as forward air)

1. Boot: `MV|cloud_sword|files=found|article=<n>`.
2. Gunner A (chose Cloud up special) grounded up special: rise with sword in right hand, speed lines, ribbon, `se_cloud_special_H01/H02`; log `chosen=special_up`.
3. A: no second press -> special fall, sword gone, 20-frame landing.
4. A: press attack or special during the rise (after the flash) -> pause, sword to left hand, straight dive, 40-frame landing with shockwave; sword back to the right hand, then gone.
5. A dive into an opponent offstage: spike; opponent cannot tech against a wall/floor while launched.
6. A up special from below a ledge (no dive): ledge grab; dive near a ledge after 10 frames: ledge grab.
7. A air up special: same rise from the air (`special_air_hi`).
8. Gunner B (vanilla up special, any of the three variants): unchanged, no sword.

## 5. What only the console can show (tier D)

Sword rendering/attachment (see the forward-air page, section 7), the super_jump_punch rise height and drift on
the Gunner with the scaled root motion, ledge grabs, the dive's tech lock on victims, that custom statuses
0x220-0x222 install on `miigunner`, that the trail folder `effect/fighter/miigunner/trail/` (new for the
Gunner) is found, and that the merged effects and tones play.
