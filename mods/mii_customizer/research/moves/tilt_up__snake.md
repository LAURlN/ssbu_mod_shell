# MV-tilt_up__snake - Snake's Up Tilt on Mii Gunner

Task ID: MV-tilt_up__snake
Date: 2026-10-08
Worker: Claude (Haiku 5.5), single session
Status: BUILT OFFLINE. Every part is written, the plugin copy builds, the stack check and `evidence/moves/tilt_up__snake/check.py` pass. Nothing has run in the game. Console proof is listed in section 6.
Donor: `snake` (attack_hi3, Snake's up tilt). Recipient: Mii Gunner (`miigunner`). Entry: `tilt_up`. Status taken over: `FIGHTER_STATUS_KIND_ATTACK_HI3` (43).
Owned names (prefix `mc_snake_` / `mcsnake`, `attackhi3` kept): motion kind `mc_snake_attack_hi3`, clip `c02mcsnakeattackhi3.nuanmb`, scripts `game_mcsnakeattackhi3`, `effect_mcsnakeattackhi3`, `sound_mcsnakeattackhi3`, `expression_mcsnakeattackhi3`.

This file replaces the earlier stub. The stub's claims were wrong in three places: the cancel frame is 38 (not 0), the scripts are Snake's own `attackhi3` scripts (not eflame's), and the clip was never retargeted.

## 1. Facts (tier B: measured offline by a script in this folder; the donor text is tier C)

| item | value | measured by |
|---|---|---|
| donor motion entry | `attack_hi3`, index 73 of 764 in Snake's body `motion_list.bin`; kind `0xacbfc42e6` | `scratch/2026-10-08_MV-tilt_up__snake/donor_entry.py` |
| entry fields | flags `0x0084`, blend 0, 1 animation (`c02attackhi3`, hash `0x138caf3e29`), size field 28, cancel frame **38** (u16 at tail+26) | same |
| entry script tail | expression `0x149fed8c9b`, sound `0xf1302b4a6`, effect `0x10369f11fe`, game `0xef3bca119` = hash40 of `game_attackhi3` etc. | same |
| donor scripts | decoded from `lua2cpp_snake.nro` (`0x39f10`, `0x3bee8`, `0x3dc58`, `0x6e6f8` registrations); tables in `gamedata/mii_customizer/moves/tilt_up__snake/tables/acmd_calls.json` | `scratch/2026-10-08_MV-tilt_up__snake/decode_unit.py` |
| donor clip | `c02attackhi3.nuanmb`, sha256 `f5151e10...5f71` (45760 bytes); groups Transform 87, Visibility 26, Material 2 | `ssbh_data_py` read |
| Gunner skeleton | `b_normalgunner_m/c00/model.nusktb`, 71 bones (sha256 `1d66b6d1...29`) | P11 pinned copy |
| Snake skeleton | `fighter/snake/model/body/c00/model.nusktb`, 97 bones | extracted from `data.arc` |

Donor script content (decoded; it agrees with the pinned third-party text in `refs/snake_attack_hi3/donor_acmd/snake__AttackHi3.txt` on every frame, bone and value the check compares):
- Game: frame 6 three `ATTACK`s on `top` (hitbox ids 0-2, damage 14.5, angle 95, kbg 82, fkb 0, bkb 65); frame 7 three on `top` (second set); frame 8 `kneel` x2 and `legl` (damage 14.5, bkb 65); frame 9 `kneel` x2 and `legl` (damage 13.5, kbg 88, bkb 50); `AttackModule::clear_all` at frame 14.
- Sound: frame 6 `PLAY_SEQUENCE(seq_snake_rnd_attack)` and `PLAY_SE(se_snake_attackhard_h01)`.
- Effect: frame 6 `EFFECT_FOLLOW(sys_attack_arc_b, top, ...)`, `LAST_EFFECT_SET_RATE(0.9)`, `FOOT_EFFECT(sys_turn_smoke, top, ...)`.
- Expression: start slope SLOPE_STATUS_R; frame 4 `set_rumble(rbkind_nohitm)`; frame 6 `RUMBLE_HIT(rbkind_attackm)`; frame 32 slope INTP LR 4.

What the earlier stub got wrong: "Snake reuses eflame's scripts" is false. The donor's own `*_attackhi3` registrations exist and decode. The stub's cancel 0 came from reading the wrong field.

## 2. What is the donor's and what differs

Copied exactly from the donor: the motion entry (flags, blend, animation count, cancel frame 38, script tail order), every ATTACK value and frame, the effect/sound/expression calls and the donor's own sound names. `check.py` compares these against the decode.

Differences (each one is in `moves/tilt_up__snake/unit.json` too):

1. **Skeleton (retarget).** 23 of the donor's 87 Transform nodes have no Gunner bone: ClavicleC, DownlipC/L/R, FaceN, Jaw, LegC, Mouth_group, S_BandannaC1-4, S_BandannaL1-5, Tongue, UplipC, UplipL1/L2, UplipR1/R2. They are dropped. 64 nodes are kept, all 26 Visibility and 2 Material tracks are kept whole. The recipe is the snake grenade unit's recipe. Gunner bones the clip does not drive keep their skeleton pose: H_ElbowL/R, H_KneeL/R, H_WristL/R, Miihead. The leg chain (Hip, Waist, LegL/R, KneeL/R, FootL/R) is verified to survive. Note: the brief said "about 22"; the measured count is 23.
2. **Hitbox bones.** `kneel` and `legl` are on the Gunner (`KneeL`, `LegL`, case-folded; Smash hashes are case-insensitive). `top` is on neither skeleton (the Snake one has 97 bones and no `top`). `top` is an engine anchor, not a model bone. It is kept as the donor names it, the same as the other mod's up tilt and the Brawler tilt. Nothing is remapped.
3. **Sounds (ported, not swapped).** The Gunner's voice comes from the Mii voice banks, not from a Gunner-named voice bank (the ARC index has none; only `vc_mii_*` and `vc_kirby_copy_miigunner`). The Gunner's own attack voice `seq_miigunner_rnd_attack01..03` names `vc_mii_attack01..10`, and those tones are in 36 `vc_mii_*` banks. Snake's own additions are:
   - `se_snake_attackhard_h01` (kind 0, single sample) appended to `se_miigunner` and `se_miigunner_c00` (both carry the same 89 tone names; the shared bank is included in case the costume bank is not the one the game loads).
   - `vc_snake_attack01..04` (the four tones the donor record names, measured by CRC32) appended to each of the 36 `vc_mii_*` banks that hold the Gunner's attack voice.
   - `seq_snake_rnd_attack`: the exact `snake.sqb` record appended to `miigunner.sqb` (19 to 20 records).
   Sample bytes and tone records are copied unchanged. The donor's `vc_snake_c00.tonelabel` does not name every tone (the other mod's tool records 34 entries for 48 tones), so the build reads it with a partial reader that still checks every entry it has. Every appended tone resolves by CRC. The GRP/DTON/PACK chunks of each recipient equal the donor's (asserted).
4. **Effects.** `sys_attack_arc_b` and `sys_turn_smoke` are common `sys_*` effects, used as they are. No effect bank is touched.
5. **Status.** The Gunner's own ATTACK_HI3 status is replaced by `start_attack_hi3` in `unit_tilt_up_snake.rs`, which copies the Brawler status body (ground check, fall, end to WAIT). In the plugin copy the Brawler `tilt_up` wiring is replaced by Snake's (see section 4). The coordinator's donor lookup replaces that wiring.

## 3. Build (what ran, and what it printed)

- `python -I mods/mii_customizer/moves/tilt_up__snake/build_assets.py` (run from the workspace root). Output:
  ```
  retarget: kept 64 transform nodes, removed 23
  motion list: 775 entries, owned entry index 774
  sound: 38 banks, voice banks 36, sqb 20 records
  manifest: ...\gamedata\mii_customizer\moves\tilt_up__snake\manifest.json
  build complete
  ```
  The 38 banks are 2 SE banks and 36 voice banks. The inputs were pulled from `data.arc` with `tools/arc-extract` (126 files in one call, then `se_miigunner.*` by the build, which pulls any listed file that is missing). Every donor input is pinned by sha256 in the script and re-checked on each run.
- Plugin copy: `scratch/2026-10-08_MV-tilt_up__snake/plugin/` (copy of `builds/.cache/plugin_base_0.10.0/` with the wiring below). Build: `cargo skyline build --release -- --offline` in that folder, with `CARGO_TARGET_DIR=builds/.cache/MV-tilt_up__snake-target`. Last output: `Finished release profile [optimized] target(s) in 5.84s` (exit 0; the crate recompiled after the final line-ending fix). The build printed 9 warnings ("never used" items in the base plugin). None names the new module.
- NRO: `builds/.cache/MV-tilt_up__snake-target/aarch64-skyline-switch/release/libmii_customizer.nro` (270336 bytes).
- Stack check: `python -I tools/stack-frames/stack_frames.py <that nro>` printed `146 frame allocations, limit 24576 bytes`, largest 18672 bytes at 0xd288, then `OK`, exit 0.
- Check: `python -I mods/mii_customizer/evidence/moves/tilt_up__snake/check.py` printed `PASS: 718 checks (manifest, pins, motion list, clip, script values, sounds, bones, plugin, NRO, negative controls)`, exit 0. Two negative controls fire inside the check: a damaged donor damage value (15.5) must be caught, and a wrong cancel frame (30) must be caught. Both were caught.

## 4. Plugin diff against `builds/.cache/plugin_base_0.10.0/`

Full diff: `scratch/2026-10-08_MV-tilt_up__snake/plugin_vs_base.diff` (43 lines). Summary:
- `src/lib.rs`: `pub mod unit_tilt_up_snake;` added after `pub mod unit_tilt_up;`.
- `src/moves.rs`: header comment updated; `gunner_attack_hi3_main` calls `crate::unit_tilt_up_snake::start_attack_hi3` instead of `crate::unit_tilt_up::start_attack_hi3`; `crate::unit_tilt_up_snake::register_acmd(&mut agent);` added after the Brawler `register_acmd` (which stays, and registers names nothing dispatches).
- `src/unit_tilt_up_snake.rs`: new. Game/effect/sound/expression scripts, `register_acmd`, `custom_snake_attack_hi3_main`, `start_attack_hi3` (self-contained: `is_anim_resource` guard, returns `vanilla` when the owned motion is not loaded).
- No other file differs. The base's LF line endings are kept.

## 5. Files

Written in this folder (`mods/mii_customizer/`):
- `moves/tilt_up__snake/unit.rs` (copy of the plugin module), `unit.json`, `build_assets.py`
- `evidence/moves/tilt_up__snake/check.py`
- `research/moves/tilt_up__snake.md` (this file)
- `scratch/2026-10-08_MV-tilt_up__snake/`: plugin copy, `decode_unit.py`, `donor_entry.py`, `probe_voice.py`, `probe_banks.py`, `build.log`, `plugin_vs_base.diff`
- `builds/.cache/MV-tilt_up__snake-target/` (target dir and NRO)

In the workspace gamedata (`gamedata/mii_customizer/moves/tilt_up__snake/`):
- `package/fighter/miigunner/motion/body/c00/c02mcsnakeattackhi3.nuanmb` (retargeted clip, 44K)
- `reference/motion_list_vanilla_plus_owned.bin` (775 entries: 774 vanilla + owned; sha256 `33d713ea...`)
- `reference/sound/` (merged reference banks: 2 SE, 36 voice, `miigunner.sqb`; about 27 MB)
- `extracted/` (data.arc pulls, about 29 MB), `tables/` (decoded donor ACMD calls and registrations), `manifest.json`
- The earlier stub files there (`unit.rs`, `unit.json`, `facts.*`, a copy of the un-retargeted clip) were removed.

## 6. Console test (for the user; nothing here was run)

Pre-condition: a build that includes this unit's motion entry, clip and sound additions. The installer applies them to the live files (see `unit.json` shared_files_needing_merge).

1. Boot with the plugin and the saved Mii set so that its `tilt_up` is Snake. Confirm the log line `MV|match|...` and no `missing` line for `mc_snake_attack_hi3`.
2. Start a match with that Gunner and a plain Gunner as the vanilla control.
3. Press up tilt on the Gunner with the Snake choice. The animation should be Snake's kick, retargeted: no arm swing, legs leading.
4. Watch the hit. The kick should hit at the frames of the donor (the top hitbox first, then the kneel/leg hitbox). Look at the hitbox display if available.
5. Listen for the Snake hard-attack sound and the Snake voice line on the same attack. The voice line should be one of the four Snake attack lines.
6. Repeat with the vanilla Gunner: the move should be the vanilla up tilt.
7. Check that the effect at the start is the donor's `sys_attack_arc_b` arc, and the foot smoke.

Pass: steps 3 to 5 as described, and step 6 vanilla. Fail: a bind-pose or frozen Gunner (the owned motion did not resolve), a silent hit (sound tones not resolved in the live bank), or a missing voice line while the SE plays.

## 7. What only the console can prove (all of it is tier D until then)

- The retargeted clip looks right on the Gunner's body (the 23 dropped nodes are face and bandanna; the Gunner has no equivalents).
- The owned motion resolves (`is_anim_resource` true) on the merged motion list, and the clip plays to its end frame.
- The hitboxes land where the donor's do. The `top` anchor behaves as on the other mod's up tilt.
- The Snake SE tone plays through `se_miigunner` or `se_miigunner_c00` (the game may load only one of them; both have the tone).
- The Snake voice plays through the saved Mii's voice bank. This depends on which `vc_mii_*` bank the Gunner's Mii voice loads; all 36 attack-voice banks have the tones, but the game's choice is not verified.
- `seq_snake_rnd_attack` resolves in `miigunner.sqb`.
- Nothing about damage, knockback or feel is measured offline.

## 8. Open items and out of scope

- The plugin copy replaces the Brawler `tilt_up` dispatch. Only one donor can be dispatched per `tilt_up`. The coordinator's lookup must keep Snake's `start_attack_hi3` in that slot, or call it from its donor lookup.
- The shared files (motion list, two SE banks, 36 voice banks, `miigunner.sqb`) must be merged by the installer. Do not copy the reference files over the live ones without the additions check (`check.py` section 6).
- Out of scope: the snake grenade unit (same prefix, separate unit) and the other mod (`mods/ssbu_mod_new/`), which was read only.
