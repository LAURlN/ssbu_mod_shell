# G&W up special (Fire) - donor sources

Provenance: `SOURCE.json`. Offsets below are **`lua2cpp_gamewatch.nro`-relative** (file offset = VA), never `main`.

`special_hi_status.c` is Ghidra output. It is evidence, not code: the decompiler drops the `push_lua_stack` arguments of
`sv_kinetic_energy::*` calls and the index of `global_table[...]`, collapses the vector passed to `PostureModule::set_rot`,
and prints hash40 constants without their length byte (`0x86bc4a93` = `param_special_hi` `0x1086bc4a93`). Read those
details from the disassembly (`tools/nro_decomp/nro_util.disasm`) when porting.

## Status table (tier B, `tools/nro_decomp/status_table.py`)

| Status | INIT | EXEC | PRE | MAIN (loop) | END |
| --- | --- | --- | --- | --- | --- |
| `SPECIAL_HI` (common 0x1DE) | 0x4010 | 0x3b20 | 0xc2e0 | 0xc6c0 (0x2cc80, sub 0x2cc20->0x2cab0) | 0xcd00 |
| `GAMEWATCH_SPECIAL_HI_FALL` (0x1E1) | 0x4140 | - | 0xd070 | 0xd460 (0x2c440) | 0xd7c0 |
| `GAMEWATCH_SPECIAL_HI_CLOSE` (0x1E2) | - | - | 0xd930 | 0xdd10 (0x2c100) | 0xdee0 |

`rescue` and `parachute` register **no** weapon statuses (only bomb, breath, food, octopus do), so like `normal_weapon`
they are driven by the owner: generate / change_motion / set_visibility_whole / remove, plus their own visibility ACMD.

## What the statuses do (read from the C above)

- **SPECIAL_HI pre**: situation NONE, kinetic `MOTION_AIR_ANGLE`, correct KEEP, cliff check ON_DROP_BOTH_SIDES; log mask special-hi attack, power-up bit special-hi.
- **init**: MOTION energy `set_speed_mul(param_special_hi.pass_speed_mul)`.
- **main**: on instance flag `SPECIAL_HI`; generate `rescue` and `parachute`, parachute invisible; ground -> motion `special_hi` on body + both articles, then `set_situation(AIR)` + `GroundModule::correct(AIR)` (the move leaves the ground at once); air -> `special_air_hi` only. Loop: cliff check; on motion end -> save `attack_air_kind`, go to `SPECIAL_HI_FALL`; on ground with `LANDING_ENABLE` -> `LANDING_FALL_SPECIAL` if `landing_frame > 0` else `LANDING`. Substatus: when ACMD sets `PARACHUTE_OPEN` (frame 33) the parachute becomes visible and the flag is cleared.
- **exec**: once `DECIDE_DIRECTION` (ACMD frame 9) is set: if `|stick_x| >= stick_min`, angle = `(|stick_x| - stick_min) * stick_mul` with sign from stick direction; `set_rot`, `set_stick_lr(0)`, `update_rot_y_lr`, MOTION energy `set_angle(rad(angle))`. Clears the flag.
- **end**: landing_fall_special -> `LANDING_FRAME = landing_frame`; unless going to FALL, remove parachute; reset rot; remove rescue; to LANDING / LANDING_FALL_SPECIAL clears instance flag `SPECIAL_HI`.
- **FALL pre**: situation AIR, kinetic UNIQ, keep flags `GAMEWATCH_SPECIAL_HI_*`, attr INTO_DOOR. **init**: `change_kinetic(FALL)`, GRAVITY limit/stable speed = `air_speed_y_stable * limit_y_mul`.
  **main**: restore `attack_air_kind`, enable air special + air attack groups, (re)generate parachute, motion `special_hi_open` on body and parachute.
  Loop: cliff; air special/attack transitions; ground -> CLOSE; in air, CLOSE when `global_table[0x1b]` (stick y) crosses
  `common.squat_stick_y` (`0xd87461d6d`) downward or `common.jump_stick_y` (`0xcce8375ba`) upward while `get_stick_prev_y` had not (a fresh flick). Index read from the disassembly.
  **end**: unless CLOSE: `JUMP_COUNT = JUMP_COUNT_MAX`, remove parachute.
- **CLOSE pre**: situation NONE, kinetic UNIQ. **main**: motion `special_hi_close` on body and parachute. Loop: cliff; on end -> WAIT (ground) / FALL (air).
  **end**: in air `JUMP_COUNT = JUMP_COUNT_MAX`; remove parachute.

Params (`vl.prc` `param_special_hi[0]`): stick_min 0.25, stick_mul 30.0, limit_y_mul 0.5, landing_frame 40.0, pass_speed_mul 1.1.
Pyra-side status ids: the block `0x1EE..0x1F8` belongs to Monkey Flip (`src/pgwr/plugin/src/status/mod.rs`), so Fire's `HI_FALL` / `HI_CLOSE` take the next two ids, `0x1F9` / `0x1FA`.

## Giving up-B back (tier B for the code; A for hits, D for landing until the 0.20.4 log)

`event_slots.json` (`tools/audit_event_slots.py`): G&W's fighter class clears his instance flag `SPECIAL_HI` from three vtable slots in `main`:
`+0x168` (situation change to ground/cliff, unless in SPECIAL_HI - landing and ledge), `+0x220` (hit), `+0x210` (unknown event).
His lua2cpp clears it only in SPECIAL_HI end (landing straight out of the move) and in `GIMMICK_TORNADO` main (`0x8b70`).
pgwr: Pyra's `+0x210`/`+0x220` defaults replaced (0.19.0); Pyra's and Mythra's `+0x168` forwarders wrapped (0.20.4). `src/pgwr/plugin/src/status/special_hi.rs`.
