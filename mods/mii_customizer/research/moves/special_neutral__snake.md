# MV-special_neutral__snake - Snake's Hand Grenade on Mii Gunner

Task ID: MV-special_neutral__snake
Status: BUILT OFFLINE. Code and every asset exist, the plugin copy builds, the stack check and `check.py` pass. Nothing has run in the game on a Gunner.
Date: 2026-10-11 (stages S1, S2: 2026-10-07; this file replaces the earlier PARTIAL report)
Donor: `snake`. Entry: `special_neutral`. Unit: `special_neutral__snake`. Prefix `mc_snake_` / `mcsnake`.
Paths are relative to `mods/mii_customizer/` unless they start with `gamedata/` or `mods/` (workspace-relative).

## 1. How the move is built

The move is a port of Snake's own status code, taken from the user's other mod, where the same port runs on the console on another fighter (`mods/ssbu_mod_new/src/pgwr/plugin/src/status/snake_grenade/`, hardware log `mods/ssbu_mod_new/evidence/2026-10-02_pgwr_T-0056/`, tier A for that fighter only). The grenade is the game's real item `ITEM_KIND_SNAKEGRENADE`; its fuse, bounce, hitboxes, explosion and damage are the item's own script and are not touched.

| part | where | what |
|---|---|---|
| gate | plugin copy `src/moves.rs` | three wrappers on `FIGHTER_STATUS_KIND_SPECIAL_N` (Pre, Main, End). Pre calls `mii_chose(fighter, "special_neutral")` and `unit::decide`. Main and End ask `unit::active`. Any other Gunner gets `original_status(..)` on all three lines, also in the same match. |
| fallback | `unit.rs` `decide` | the move is taken only when all 29 owned motions are loaded (`MotionModule::is_anim_resource`) and the fuse bridge is usable. Otherwise the vanilla neutral special runs and one log line says why. |
| statuses | `unit.rs` | start (`SPECIAL_N` itself), 12 hold statuses (wait, walk f/b, walk brake f/b, dash f/b, jump squat, jump, jump aerial, air, landing), throw, ear close. Created ids `0x1FA..0x207` (`STATUS_BASE` = `FIGHTER_MIIGUNNER_STATUS_KIND_NUM`). |
| item | `unit.rs` `pull`, `release`, `drop_held` | `ItemModule::have_item` in the start script; `Item::throw_attack` with Snake's `param_special_n` speeds at the three strengths; `Item::fall` when the move is left any other way; at most two grenades out (`get_num_of_ownered_item`), the third press plays the fail motion. |
| lower body | `unit.rs` `mod lower` | owned translations of the common item-shoot routines that name motions (wait, walk blend slow/middle/fast, brake, dash, jump squat, landing), upper body as a partial motion (`mc_snake_special_n_hold`). |
| pin | `unit.rs` `mod pin` | clone of Snake's pin prop (`WEAPON_KIND_SNAKE_GRENADE`) as Gunner article `mc_snake_pin`, shown from frame 9 of the pull, removed when the start status ends. |
| fuse | `unit.rs` `mod fuse` | see section 3. |
| ear close | `unit.rs` `watch_grenades`, `ear_close_event` | see section 2. |
| scripts | `unit.rs` `mod acmd` | 69 scripts (game, effect, sound, expression) for the 29 motions. |
| assets | `moves/special_neutral__snake/build_assets.py` | 29 clips, pin files, reference motion list, reference sound banks. |

### Assets (all under `gamedata/mii_customizer/moves/special_neutral__snake/`)

- `package/fighter/miigunner/motion/body/c00/c01mcsnake*.nuanmb`: 29 clips. 14 for Snake's `special_(air_)n_*` kinds and 15 for his `item_shoot_legs_*` kinds. The vanilla Gunner list has only 4 of those 15 leg kinds (`walk_f`, `walk_b`, `jump_squat`, `landing`), so all 15 are owned.
- `package/fighter/miigunner/model/mc_snake_pin/c00..c11/` (15 files each) and `.../motion/mc_snake_pin/c00..c11/` (3 clips and a motion list with the kinds renamed to `mc_snake_pin_start`, `mc_snake_pin_air_start`, `mc_snake_pin_start_kirby`). Byte copies of `fighter/snake/model/grenade/c00` and `fighter/snake/motion/grenade/c00`. Twelve slots because the Gunner body has `c00..c11`; which slot folder a cloned article reads on a Mii is not known offline.
- `reference/motion_list_vanilla_plus_owned.bin` (774 + 29 entries, sha256 `95237b28f189...`), `reference/sound/bank/fighter/se_miigunner{,_c00}.*` (89 + 9 tones). References, not files to ship.
- `manifest.json` (264 files with size and sha256, the 29 motion rows, the `config.json` additions), `tables/retarget_report.json`.

Shared Gunner files are not shipped as whole copies. `build_assets.py apply-motion <base> <out>` appends the 29 entries to any Gunner motion list. `build_assets.py apply-sound <base stem> <out stem>` appends the nine tones to any bank triple. Both refuse a base that already has them.

### Retarget

The six S1 clips (name filter only) were replaced. All 29 clips use the recipe of `moves/aerial_forward__cloud/build_assets.py` (the other mod's handbook recipe): rotation from the donor, translation = Gunner idle + (donor frame - donor idle), world-space transfer for the four nodes whose parent differs (`ClavicleL/R`, `LegL/R`), a vertical ground-contact correction on `Rot`, Visibility from the Gunner idle, Material dropped. 23 Snake-only nodes are dropped (`ClavicleC`, `LegC`, `FaceN`, `Jaw`, `Mouth_group`, `Tongue`, 3 `Downlip*`, 5 `Uplip*`, 9 `S_Bandanna*`). `Miihead` and the ten finger-tip nodes stay at the Gunner idle. `special_n_hold` is Snake's upper-body layer (76 nodes, no `Trans`/`Rot`/`Hip`/legs); it stays partial (53 nodes written). Frame counts equal the donor clips.

### Sounds

Same method as `moves/tilt_up__snake/build_assets.py` (`append_tones`): sample bytes and tone records unchanged, appended after the Gunner's own 89 tones, labels rebased. Nine tones from `se_snake_c00`: `se_snake_special_n01`, `_n02`, `_n03`, `_n04`, `se_snake_step_left_m`, `se_snake_step_right_m`, `se_snake_dash_stop`, `se_snake_jump01`, `se_snake_landing02`. Both `se_miigunner` and `se_miigunner_c00` get them (the two vanilla files are byte-identical). `_n04` is the explosion sound the item script plays; the other eight are played by `unit.rs`. None of the nine is a key in `snake.sqb`, so the Gunner's sequence file needs nothing. The up tilt unit adds `se_snake_attackhard_h01` to the same banks; the two additions do not overlap, apply one after the other.

### Effects

Only common effects: `sys_smash_flash`, `sys_run_smoke`, `sys_down_smoke`, `sys_jump_aerial`. No effect bank is touched. The explosion effects are the item's.

## 2. What is exactly the donor's and what differs

Exactly the donor's:
- The 29 motion entries: flags, blend, cancel frames (throw lw 26, m 28, hi 32, close 1, fail 28), script slots. Only kind, clip and script names are repointed.
- Script frames and arguments. `check.py` compares 22 scripts (ground set and air start) with the decode of the user's `lua2cpp_snake.nro` (`tables/acmd_calls.json`): pull at frame 0, pin visible at 9, motion rate 0.5 from 16, throw at 9 / 8 / 10, flash and sound frames. The air and leg scripts are the other mod's generated file with names changed only (compared body by body).
- Throw speeds and thresholds from `fighter/snake/param/vl.prc`: m 1.1 / 1.0, hi 2.5 / 0.3 (stick rate >= 0.4), lw 0.2 / 1.8 (rate <= -0.4), fuse 150, ear close distance 45.
- Status flow: status settings, sub-status for B release and A press, shield cancel on the ground, jump and double jump while holding, landing, two-grenade limit, fail motion.

Different:
1. **Skeleton.** Retargeted clips (above).
2. **Hand.** The Gunner holds items in the left hand (its `h01lightthrowf` clip moves `HandL` 12.6 units, Snake's moves `HandR` 18.6). Snake's native article init (`main+0x11b6c60`) attaches the grenade to `haver`. The unit calls `ItemModule::set_have_item_constraint_joint(haver)` after the pull, in every hold INIT and in THROW main (the common item-shoot exit resets the constraint when a hold is left for THROW), and `reset_have_item_constraint_node` when the move is left. The Gunner's right forearm is its arm cannon, so the grenade sits at the cannon end. Not donor-like in look; the animation and the throw origin are.
3. **Article.** No item-backed article: Snake's article 13 callbacks read his params and compare the owner's status with his `0x1EF`. The unit does what the shoot callback does (`update_log_attack_info`, `set_power_up(1.0)`, `throw_attack` with the owner's `power_special_n`, x mirrored when facing left).
4. **Ear close.** Snake's native link-event handler (`main+0x11b6010`) enters `SPECIAL_N_EAR_CLOSE` when the grenade's BORN init sends event `0x248952aeca` to its create owner, the owner is in WAIT (status 0) or already in ear close, and the explosion is within 45 units. The Gunner's handler ignores that event. The unit polls the grenades this entry pulled once per frame and applies the same three conditions when one enters `ITEM_STATUS_KIND_BORN`. At most one frame later than the donor. The other mod left this state out.
5. **Movement speed while holding** is the Gunner's own (the common code reads the fighter's params).
6. **Not ported:** Snake's `CYPHER_FALL` jump lock (belongs to his up special).

Corrections to the earlier report: `game_specialnclose`, `game_specialnhold` and the air jump game script are empty in the NRO (their 268-byte wrappers call no body; the old decoder attached a neighbour's body). The entry at index 99 is `special_n_throw_fail`.

## 3. The fuse bridge and the other mod's hook

`app::snakegrenade::life()` (`main+0x1674e90`) is `*(*(*(main+0x52bb3b0)+0x7e0)+0xf0)`. The item script calls it from exactly one place (`lua2cpp_item.nro+0x7c921c`, the coroutine of the item's first status), synchronously inside `have_item`. Without Snake in the match the chain is null.

The other mod's plugin hooks this function at boot, after comparing its bytes, and returns 150 for every grenade whenever Snake's parameters are missing. Coexistence rules in this unit:
- Nothing is patched at load. A patch at load would change the bytes and make the other plugin's check fail, which switches its grenade off.
- The first time a Gunner takes the move (in a match), the six instruction words are read. Originals: this plugin installs its own hook. First word is a branch (`b`, or `ldr x16/x17, #8`): another bridge owns the function, nothing is installed and the unit relies on it. Anything else: the move is refused and the Gunner keeps vanilla.
- The own hook returns 150 only while this unit's `have_item` call is running and only when Snake's chain is unreadable. Every other call runs the original unchanged. With Snake in the match the grenade gets Snake's own value.

So the function is never hooked twice. With both plugins on the card the other mod's bridge serves both; without it (or with its Snake feature off) this plugin's own hook serves only this unit.

## 4. Plugin copy

`scratch/2026-10-08_MV-special_neutral__snake/plugin/`, built with `CARGO_TARGET_DIR=builds/.cache/MV-special_neutral__snake-target`, `cargo skyline build --release -- --offline`: exit 0, 0 errors. NRO 311,296 bytes, sha256 `bb1344d6697b...` (rebuild changes it). `python tools/stack-frames/stack_frames.py <nro>`: largest frame 18,688 bytes, exit 0.

Diff against `builds/.cache/plugin_base_0.10.0/`:
- new `src/unit_special_neutral_snake.rs` = `moves/special_neutral__snake/unit.rs` (byte-identical, 2467 lines).
- `src/lib.rs`: `+pub mod unit_special_neutral_snake;` after `pub mod unit_smash_up;`.
- `src/menu.rs`: `IMPLEMENTED_MOVES` length 4 -> 5, `+(b"special_neutral", b"snake"),`.
- `src/moves.rs`:
  - three new functions before `install()`: `gunner_special_n_pre` (`mii_chose(fighter, unit::ENTRY)`, `unit::decide`, else `original_status(Pre, ..)`), `gunner_special_n_main` and `gunner_special_n_end` (`unit::active`, else `original_status`);
  - in `install()`: `crate::unit_special_neutral_snake::prepare();` before `Agent::new("miigunner")`; three `.status(Pre|Main|End, *FIGHTER_STATUS_KIND_SPECIAL_N, ..)` lines appended to the chain; `crate::unit_special_neutral_snake::register(&mut agent);` after the smash-up registration.
- `Cargo.toml`, `Cargo.lock`: unchanged.

For the coordinator: `mii_chose` answers "any donor chosen for this entry"; when a second neutral-special donor exists, the wrapper needs the donor lookup. `menu.txt` needs `allow special_neutral snake`. Status ids `0x1FA..0x207` and the first cloned Gunner article are taken by this unit.

## 5. Checks run

- `python -I mods/mii_customizer/moves/special_neutral__snake/build_assets.py`: 29 clips, 774 + 29 entries, 228 pin files, 2 banks, manifest 264 files.
- `python -I mods/mii_customizer/evidence/moves/special_neutral__snake/check.py`: `PASS: 1314 checks`, exit 0. Three negative controls fire inside it (damaged cancel frame, damaged `life()` word, damaged script frame).
- The check also confirms that every game symbol the NRO imports is exported by `main` or `lua2cpp_common.nro`.

## 6. Console test (8 steps)

Needs a build with this unit wired in, the motion entries, clips, pin files, sound additions and `allow special_neutral snake`. Two Gunners: A with Neutral Special set to Snake, B default. No Snake in the match. Send `sd:/ultimate/mii_customizer_log.txt` from boot.

1. Gunner B, neutral special: the vanilla move. Gunner A, neutral special on the ground, tap B: Snake's pull animation, pin in the left hand, grenade at the right arm, pull sound, then a middle throw. Log: `snake_n|fuse_state` (b=2 with the other mod's bridge, b=1 own hook), `snake_n|pull_ok` with b=150.
2. Hold B: A keeps the grenade. Walk both ways, dash, jump, double jump, land: Snake's leg clips, upper body holds the grenade, step and landing sounds.
3. Release B with the stick neutral, forward and back: middle, far (hi) and short lobbed (lw) throws. Log `snake_n|release` b=1, 2, 0.
4. Hold the grenade until it explodes in the hand: about 2.5 seconds after the pull, A takes the damage.
5. Pull, press shield: A returns to idle, the grenade drops at the feet. Stand next to it: when it explodes A covers the ears (`snake_n|ear_close`) if A was idle.
6. Throw two grenades quickly, press B a third time while both exist: the fail motion, no third grenade.
7. Same in the air: air pull, air hold, air throws.
8. After a throw, pick up an ordinary item with A: it is held in the left hand as usual. B's neutral special still vanilla.

Fail signs: frozen or bind-pose Gunner (motions not resolved; the log then shows `vanilla_motion_missing` and A should simply have the vanilla move), crash at the pull (fuse), no grenade (`pull_fail`), grenade in the left hand during the move, silent pull or throw (tones not in the loaded bank), no pin (article files not found: the move still works).

## 7. What only the console can prove

- That smashline registers statuses `0x1FA..0x207` and the three `SPECIAL_N` wrappers on `miigunner`, and that `original_status` returns the Gunner's own Pre / Main / End for the non-chosen Gunner.
- The item route on a Gunner: `have_item`, the fuse (own hook installed during a match, or the other mod's bridge), throw, drop, explosion. Tier A exists for the other fighter only.
- The pin article: whether a cloned weapon loads for a Mii and from which slot folder.
- The `haver` constraint and how the grenade looks at the arm cannon.
- The retargeted clips' look (pose, feet, the partial upper-body layer over the legs).
- Sounds: which of `se_miigunner` / `se_miigunner_c00` the game loads, and whether the item's explosion tone `se_snake_special_n04` resolves through the Gunner's bank.
- Ear close timing.
- Kirby copying a Gunner with this move was not considered.

## 8. Evidence tiers

- B (measured offline here): everything in sections 1 to 5; native facts read from `gamedata/ssbu-13.0.4/main.bin` (sha256 `f70c97d2...7613`) and the extracted NROs with `scratch/2026-10-08_MV-special_neutral__snake/mcdis.py`.
- A (other mod, other fighter): the item lifecycle and the status port.
- D: all behaviour on a Gunner.

## 9. Files

- `moves/special_neutral__snake/`: `unit.rs`, `unit.json`, `build_assets.py`
- `evidence/moves/special_neutral__snake/check.py`
- `research/moves/special_neutral__snake.md` (this file)
- `scratch/2026-10-08_MV-special_neutral__snake/`: `plugin/` (the plugin copy), `build.log`, `gen_unit_acmd.py` (writes the ACMD module of `unit.rs` from the other mod's generated file), `write_unit_json.py`, `mcdis.py`, `list_donor.py`
- `gamedata/mii_customizer/moves/special_neutral__snake/`: `package/`, `reference/`, `manifest.json`, `tables/`, extracted inputs (ARC paths mirrored; `prebuilt;/` holds the NROs)
- `builds/.cache/MV-special_neutral__snake-target/`: cargo target

Tool notes: `tools/arc-extract` cannot write `prebuilt:/` paths on Windows; the unit's older scratch copy (`scratch/2026-10-07_MV-special_neutral__snake/arc-extract`) maps them to `prebuilt;/`. `build_assets.py` needs none of those. Capstone for `mcdis.py` is read from `mods/ssbu_mod_new/builds/.cache/dk_cargo/python` (nothing installed).
