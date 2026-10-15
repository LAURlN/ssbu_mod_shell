# MV-aerial_up__kamui - Corrin's Up Air on Mii Gunner

Task: MV-aerial_up__kamui. Move: up air (`aerial_up`, donor kind `attack_air_hi`). Donor: Corrin (`kamui`).
Recipient: Mii Gunner (`miigunner`). Plugin base: the coordinator's integrated `mods/mii_customizer/plugin/src`.
Status: BUILT OFFLINE (second pass, 2026-10-14). Animation, hitboxes, timing, motion entries, landing clip, sword
article, sound tone, trail textures, plugin copy and stack check pass (tier B). Still missing: Corrin's effect
`kamui_sword_flare` (the trail's flare name); the landing ACMD scripts (not decoded). Nothing has run in game (tier D).

## 1. Short answer

- Skeleton: the 47 Corrin-only nodes (wings, mantle, shirttails, spear, face, mouth, lips) are dropped as the Cloud
  precedent does; 64 nodes are kept on the Gunner's 75-node idle set. `haver` is `HaveR` (hash40 is case-insensitive),
  present on both skeletons.
- Sword: Corrin's Omega Yato is three rigid meshes `Kamui_Weapon_VIS_O_OBJShape` in his body model, bound to `HaveR`.
  Built as the Gunner article `mckamuisword` (Cloud's recipe, section 3 of `research/moves/aerial_forward__cloud.md`),
  attached to `haver` with the engine's constraint calls, shown for the move and its landing, removed when the owner's
  motion ends. Registered only when its model file is on the card.
- Sounds: `se_kamui_attackair_H01` is appended to the Gunner's `se_miigunner` bank (89 -> 90 tones), additions only,
  by `mckamui_sounds.py`. Corrin's voice sequence is replaced by the Gunner's own sequence (the Cloud voice rule).
- Status decode: Corrin's ATTACK_AIR END and LANDING_ATTACK_AIR MAIN are now read (section 4). Their work is reproduced
  as far as it applies to a Gunner: the sword is removed on the move's end; the landing lag comes from Corrin's
  `landing_attack_air_frame_hi` (9, the Gunner's is 13); the ENABLE_LANDING window decides landing attack vs landing.
- Trail: the two textures are renamed to the owned footer names `TEX_MC_KAMUI_SWORD1/2` (as the Cloud units do). Whether the
  Gunner's loader finds them in `effect/fighter/miigunner/trail/` is unverified; the Cloud finding is the same placement.

## 2. Facts (tier B unless marked)

- Motion entries (donor `fighter/kamui/motion/body/c00/motion_list.bin`, 733 entries): `attack_air_hi` index 86, flags
  0x0080, cancel field 38; `landing_air_hi` index 91, flags 0x0080, cancel field 20. Owned entries copy the donor bytes and
  replace only the kind, the game/expression/sound/effect hashes and the clip hash.
- Clips: `c05attackairhi.nuanmb` (58 frames, 111 transform, 34 visibility incl. `Kamui_Weapon`), `c05landingairhi.nuanmb`
  (30 frames). Both retargeted: 64 pose nodes kept, 47 dropped, legs and hip moving (gates pass). Ground correction on Rot:
  attack +0.17..+8.66, landing +0.29..+4.71 (unverified visually).
- ACMD (`tables/acmd_calls.json`, P12 decoder): game: flag ENABLE_LANDING on frame 4, three ATTACK calls (bone `haver`,
  damage 10, angle 70, KBG 97, BKB 55, size 5.5, offsets y 0/4/8, z -1) at frame 7, `wait` 6, clear_all at 13, flag off at 38.
  Effect: `AFTER_IMAGE4_ON_arg29` at 6 (29 arguments; textures `tex_kamui_sword1/2`, name `kamui_sword_flare`), off at 12.
  Sound: `PLAY_SE se_kamui_attackair_h01` and `PLAY_SEQUENCE seq_kamui_rnd_attack_air` at 4. Expression: rumble at 5
  (not decoded, left out), `RUMBLE_HIT rbkind_slashm` at 7.
- Corrin's status registrations (`tables/status_regs.tsv`): ATTACK_AIR END `bl 0x1c1c` (function `0x117a0`);
  LANDING_ATTACK_AIR MAIN `bl 0x1d9c` (function `0x120c0`).
- Landing lag (fighter_param.prc): Corrin `landing_attack_air_frame_hi` 9.0, Gunner 13.0.
- Hitbox bone `haver`: `HaveR` on both skeletons (check 6).

### 2a. Corrin's two statuses, decoded (new in this pass)

Method: `llvm-objdump` on an ELF wrapper of the NRO code (`scratch/2026-10-14_MV-aerial_up__kamui/raw_to_elf.py`), with the
bl stubs named from the NRO's relocation table (`name_stubs.py`, `annotate.py`). Listings:
`gamedata/mii_customizer/moves/aerial_up__kamui/tables/disasm_kamui_nro_*.txt`.

- ATTACK_AIR END (`0x117a0`): reads two Corrin table ids (work `0xa7ac`, `0xa7b0` through `0x1ad000+0xb18`); if
  `ArticleModule::is_exist` for the first, and the second article's id differs, it calls `ArticleModule::remove` on Corrin's
  own article(s); then `VisibilityModule::set_whole(bool)` on the body; then the common `status_end_AttackAir`.
  Reproduced for the Gunner as: the sword is removed when the owner's motion ends (`mckamui::sword_guard`), and the
  Gunner's own END runs as vanilla. The body visibility is not touched (the Gunner has no Corrin visibility state).
- LANDING_ATTACK_AIR MAIN (`0x120c0`): `WorkModule::off_flag` on one Corrin table id (`0xa7b4`), then the common
  `status_LandingAttackAir`. The flag is Corrin's state; the Gunner has no such id, so nothing is copied.
- Landing decision: the common ATTACK_AIR path uses ENABLE_LANDING. The unit's Main does the same: ground contact with the
  flag set goes to LANDING_ATTACK_AIR, otherwise to LANDING. The engine's exact rule is not decoded (tier D).
- Not decoded: the LANDING_ATTACK_AIR END-like functions at `0x12150`, `0x1227c` (set_float with table `0x5e0`), which
  belong to other Corrin statuses; not registered for ATTACK_AIR or LANDING_ATTACK_AIR.

## 3. What is built

- `moves/aerial_up__kamui/unit.rs`: the move's ACMD (flags, ATTACK x3, clear, trail, sound, rumble), `custom_attack_air_hi_main`
  (cancels, ground rule above, FALL at motion end), `start_attack_air` (returns its input unless motion is `attack_air_hi` and
  the unit is ready), `in_kamui_up`, `start_landing_attack_air` (landing clip at rate 9 frames).
- `moves/aerial_up__kamui/mckamui.rs`: the `mckamuisword` article (install, `ready`, `show`, `attach_hand` (`have` to `haver`),
  `hide`, `sword_guard`). Log lines `MV|kamui_sword|...` (up to 12).
- `moves/aerial_up__kamui/mckamui_sword.py`: the article's model, materials, textures, one-frame clip, article motion list.
- `moves/aerial_up__kamui/mckamui_sounds.py` (+ `mckamui_sound_codec.py`, a copy of the Cloud codec): tone append,
  additions only, `--base <dir with se_miigunner.*> --output <dir>`. Output recorded in `se_miigunner.merge.json`.
- `moves/aerial_up__kamui/build_assets.py`: rebuilds everything from the donor and recipient extracts. Run:
  `python -I mods/mii_customizer/moves/aerial_up__kamui/build_assets.py`. Output on 2026-10-14:
  ```
  clip: ... c01mckamuiattackairhi.nuanmb frames=58 transform_nodes=75 pose=64 dropped_donor_nodes=47
  landing clip: ... c01mckamuilandingairhi.nuanmb pose=64
  reference: 776 entries (vanilla 774 + 2)
  sword: mckamuisword objects=3 materials=['mckamui_sword_001', 'mckamui_sword_002', 'mckamui_sword_003']
  sound: 89 -> 90 tones
  ```
- Gamedata (`gamedata/mii_customizer/moves/aerial_up__kamui/`): `package/` (25 files: two clips, the sword model and its
  motion, two trail textures), `reference/motion_list_vanilla_plus_owned.bin` (vanilla + 2 entries), `reference/sound/bank/fighter/`
  (`se_miigunner.*`, vanilla + 1 tone), `manifest.json`, `tables/retarget_report.json`, `tables/disasm_*.txt`.
- Plugin copy `scratch/2026-10-14_MV-aerial_up__kamui/plugin/` (from `mods/mii_customizer/plugin/src`). Diff:
  `scratch/2026-10-14_MV-aerial_up__kamui/integration.diff` (81 lines). Changes:
  - `lib.rs`: `pub mod mckamui;`, `pub mod unit_aerial_up_kamui;`
  - `menu.rs`: `IMPLEMENTED_MOVES` becomes 9 entries, adds `(b"aerial_up", b"kamui")`
  - `moves.rs`: row `("aerial_up", b"kamui", crate::unit_aerial_up_kamui::start_attack_air)` in `gunner_attack_air_main`;
    `was_kamui_up` read before the vanilla landing Main and `start_landing_attack_air(fighter, was_kamui_up)` after it;
    `crate::mckamui::install()` after `mccloud::install()`; `.on_line(Main, crate::mckamui::sword_guard)` after the Cloud guard;
    `unit_aerial_up_kamui::register_acmd` after the Cloud registration
  - `src/unit_aerial_up_kamui.rs` and `src/mckamui.rs`: byte-identical to the two sources in `moves/aerial_up__kamui/`.
- Build: `cargo skyline build --release -- --offline` in the scratch plugin, `CARGO_TARGET_DIR=builds/.cache/MV-aerial_up__kamui-target`,
  log `builds/.cache/MV-aerial_up__kamui-build2.log`: `Finished release profile [optimized] target(s) in 7.27s`, exit 0, no
  warning from the new files (after removing one unused import). NRO sha256
  `18aea5120985c8e3e24e72f687731c6197f625836ea957c58214c597d31e7a28`.
- Stack check: `python -I tools/stack-frames/stack_frames.py <nro>`: `210 frame allocations, limit 24576 bytes`, largest
  `18672 bytes at file offset 0x12098`, `OK`, exit 0.

## 4. Checks run

`python -I mods/mii_customizer/evidence/moves/aerial_up__kamui/check.py` (from the workspace root), final run:

```
1 manifest: 25 package file(s), 5 reference file(s) match
2-3 clips: attack 58 frames, landing 30 frames, both 75 transform nodes on the Gunner idle set
4 motion list: 776 entries (vanilla 774 + 2), hashes OK, flags 0x0080, cancel 38 and 20
5 unit.rs: 3 ATTACK calls and the 29-argument trail call match the decode; game frames [4.0, 7.0, 13.0, 38.0], effect [6.0, 12.0], sound [4.0], expression [7.0]
6 bone haver = HaveR on the Corrin and Gunner skeletons (hash40 case-insensitive)
7 gates: legs moving (attack and landing), world-space nodes as listed; landing lag 9.0 (Gunner 13.0); ground correction attack [0.17434, 8.65754], landing [0.29273, 4.70907]
8 sword article: 3 rigid objects on ['Have'], materials ['mckamui_sword_001', 'mckamui_sword_002', 'mckamui_sword_003'], clip Visibility mckamui_sword True, article motion entry hashes match
9 sound: se_miigunner 89 -> 90 tones, base prefix kept, label resolves
10 trail: two textures, owned footer names, only the 64-byte name field differs from the donor
11 plugin copy: unit and sword identical to the sources, wiring present, NRO sha256 18aea5120985c8e3, stack check exit 0
12 negative controls: damage, frame, cancel field, landing lag and sword object count all rejected
PASS: aerial_up__kamui offline checks
exit 0
```

The first run of the check failed on its own sequence test (it matched a doc comment); fixed in the check, not the unit.

## 5. Not done, or not the donor's

1. **Effect `kamui_sword_flare` (missing).** The trail's name argument is Corrin's effect handle in `ef_kamui.eff` (9.3 MB,
   extracted). Cloud ported his handles into the Gunner's bank with `mccloud_effects.py`; the same port for Corrin is not built.
   Without it the trail draws its textures but not the flare.
2. **Landing ACMD scripts (missing).** `game/effect/sound/expression_mckamuilandingairhi` are named in the landing motion entry
   but not registered: the landing clip plays, its donor effects and sounds do not (not decoded in this pass).
3. **Voice sequence (substituted, Cloud's rule).** `seq_kamui_rnd_attack_air` is Corrin's voice; the Gunner's
   `seq_miigunner_rnd_attack02` plays on the same frame. Declared, not hidden.
4. **Trail placement (unverified).** `effect/fighter/miigunner/trail/tex_mc_kamui_sword{1,2}.nutexb`, footer names rewritten.
   Cloud's finding (the same folder, footer-name requests) is the basis; whether this Gunner's loader finds it is tier D.
5. **Rumble at frame 5** (kind not decoded): left out.
6. **Landing scripts and the sword's z-order/size** are visual questions for the console.

## 6. Coordinator merges

- Motion list: merge `reference/motion_list_vanilla_plus_owned.bin` (two entries) with the other units' entries.
- `se_miigunner`: merge `reference/sound/bank/fighter/se_miigunner.*` (one tone) with the other units' tones. The script
  `mckamui_sounds.py` takes any base bank; a bank that already has Cloud's tones must be used as the base for both.
- ARCropolis `new-dir-files` from `manifest.json` (`config_needed_by_coordinator`): folders
  `fighter/miigunner/motion/body/c00`, `fighter/miigunner/model/mckamuisword/c00`, `fighter/miigunner/motion/mckamuisword/c00`,
  `effect/fighter/miigunner/trail`.
- Dispatch: `FIGHTER_STATUS_KIND_ATTACK_AIR` has one dispatcher with three rows; the landing hook is a second call in
  `gunner_landing_attack_air_main`. Article registration (`mckamui::install`) must come before fighters load, as the Cloud one.
- Session menu: allow `aerial_up` / `kamui`.

## 7. Console test (at most 8 steps, for the user)

Prerequisites: the merged package and plugin, the menu entry set on Gunner A. Nothing is installed by this worker.

1. Boot. Expect `MV|kamui_sword|files=found|article=<id>` (or `missing`, then Corrin's move stays vanilla).
2. Gunner A, up air (set to Corrin). Expect the `exec` line for `aerial_up`, the Corrin up-air motion, and the sword in the right
   hand from the first frame (`MV|kamui_sword|hand=r|...|exist=1`).
3. Watch the three hitboxes from about frame 7: damage 10 each.
4. Land during the up air. Expect the landing clip at the faster rate (landing lag 9) and the sword still in hand.
5. Gunner A, forward air and back air. Expect the Cloud and Mario moves, no `aerial_up` line.
6. Gunner B (up air vanilla). Expect the vanilla up air, byte for byte as before.
7. Sword after the move: expected removed when the Gunner leaves the owner's motion.
8. Sound: expected the Corrin up-air swing from frame 4 (tone appended), plus the Gunner's own voice line. Trail: expected only if the loader finds the textures.

## 8. Still tier D (console only)

Whether the article renders on a Gunner and sits in the hand (constraint); the trail loader; the landing rate; the ground
correction (+8.66 attack); the ENABLE_LANDING rule for landing; the sound playing.

## 9. Files

Unit: `moves/aerial_up__kamui/{unit.rs, mckamui.rs, mckamui_sword.py, mckamui_sounds.py, mckamui_sound_codec.py, build_assets.py, unit.json}`.
Evidence: `evidence/moves/aerial_up__kamui/check.py`. Gamedata: `gamedata/mii_customizer/moves/aerial_up__kamui/`.
Scratch: `scratch/2026-10-14_MV-aerial_up__kamui/` (plugin/, integration.diff, raw_to_elf.py, name_stubs.py, annotate.py,
patch scripts). Builds: `builds/.cache/MV-aerial_up__kamui-target/`, `builds/.cache/MV-aerial_up__kamui-build2.log`.
