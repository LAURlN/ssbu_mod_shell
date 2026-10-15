# MV-aerial_forward__cloud - Cloud's forward air on Mii Gunner

Task: MV-aerial_forward__cloud (built together with MV-special_up__cloud, which shares the sword, the
effect/sound additions and the plugin copy). Date: 2026-10-14. Status: **BUILT OFFLINE** - code and every
asset exist, the plugin copy builds, the checks pass. Nothing has run in game (tier D for everything on
screen). Tiers: B = measured offline by a script named here; C = read from pinned third-party source; D =
hypothesis for the console.

Paths: mod-relative unless marked workspace-relative. Game files come from workspace
`gamedata/ssbu-13.0.4/data.arc` (extracted by `moves/aerial_forward__cloud/mccloud_build.py::extract_inputs`
into workspace `gamedata/mii_customizer/moves/aerial_forward__cloud/{donor,recipient}/`).

## 1. What the move is now

A Gunner whose saved Mii chose `aerial_forward = cloud` does Cloud's forward air:

| part | how | source / tier |
|---|---|---|
| animation | Cloud's `c05attackairf` retargeted to the Gunner skeleton -> `mc_cloud_attack_air_f` (80 frames), Cloud's motion entry (flags 0x0080, cancel field 54) | `mccloud_retarget.py`, B |
| sword | Buster Sword article `mccloudsword` in the right hand from frame 0 until the Gunner leaves the move (section 3) | B for files, D on screen |
| hitboxes | Cloud's `game_attackairf`: frame 18 ids 0 (14%, 270 deg spike, air only), 1 (14%, 60 deg, ground only), 2 (13%, 7.8 radius), 3 (13%, `haver`); frame 20 ids 0-2 cleared, id 3 re-issued 11%; clear at 26 | decoded from `lua2cpp_cloud.nro` 0x131100, all 36 args checked, B |
| autocancel | `FIGHTER_STATUS_ATTACK_AIR_FLAG_ENABLE_LANDING` on at 3, off at 43 (Cloud's flag calls, names decoded); landing inside the window -> LANDING_ATTACK_AIR, outside -> plain LANDING | B (decode), D (behaviour) |
| landing | Cloud's `c05landingairf` -> `mc_cloud_landing_air_f` (cancel field 20), played at `sub_get_landing_motion_rate(clip, 11)`, i.e. Cloud's 11-frame lag (Gunner vanilla: 12) | fighter_param.prc, B |
| effects | `sys_smash_flash` f10, sword flare (`cloud_sword_flare` -> handle `mc_cloud_sword_flare`) f16-25 with camera-flat offset 0.2, `cloud_airf_slash` (-> `mc_cloud_airf_slash`) f17 on `top`; landing `sys_down_smoke` | B |
| trail | **none**: Cloud's `effect_attackairf` has no AFTER_IMAGE call (decoded). The ribbon the other mod added to its fair port is not Cloud's | B |
| sounds | `se_cloud_attackair_F01` f15, `se_cloud_landing02` landing f2 (Cloud's tones appended to the Gunner bank) | B |
| voice | the Mii's own `seq_miigunner_rnd_attack01` at f15 instead of `vc_cloud_attack05` (deliberate: a Mii keeps its voice) | difference |
| expression | reference joint `haver` Z/Y/X, hide held item, rumble `rbkind_nohitm` f16, `RUMBLE_HIT rbkind_slashm` f18; landing slope + `rbkind_lands` | B (fair), C (landing, refs/cloud_attack_air_f/LandingAirF.txt) |

Every other aerial of that Gunner, and every Gunner whose Mii did not choose it, stays vanilla:
`start_attack_air` returns the vanilla result unless the vanilla Main picked `attack_air_f`, the sword article
is registered and both owned motions are in the loaded list.

## 2. Code

- `moves/aerial_forward__cloud/unit.rs` (= plugin `src/unit_aerial_forward_cloud.rs`): ACMD, the main loop
  (common aerial rules), `start_attack_air`, `start_landing_attack_air`.
- `moves/aerial_forward__cloud/mccloud.rs` (= plugin `src/mccloud.rs`): sword article, per-entry work
  variables, a vanilla-status lookup that returns None instead of panicking. Shared with the up special.
- Status decode tools: `scratch/2026-10-08_MV-aerial_forward__cloud/re/nrolib.py` (annotated disassembly of a
  lua2cpp NRO: imports, lua const names, hash40 labels) and `acmd_listing.py` -> `acmd_listing.txt`.

### Exact diff of the plugin copy against `builds/.cache/plugin_base_0.10.0/`

Full text: `scratch/2026-10-08_MV-aerial_forward__cloud/integration.diff` (covers both Cloud units).
- `lib.rs`: `pub mod mccloud; pub mod unit_aerial_forward_cloud; pub mod unit_special_up_cloud;`.
- `menu.rs`: `IMPLEMENTED_MOVES` 4 -> 6 rows: `(b"aerial_forward", b"cloud")`, `(b"special_up", b"cloud")`.
- `moves.rs`: dispatchers `gunner_attack_air_main` (via `owned_status_main("aerial_forward")`),
  `gunner_landing_attack_air_main`, `gunner_special_hi_{pre,init,exec,main,end}`; `crate::mccloud::install()`
  before `Agent::new("miigunner")`; the seven `.status(...)` rows, `.on_line(Main, mccloud::sword_guard)`,
  `unit_special_up_cloud::register_statuses`, both units' `register_acmd`.
- new files: `mccloud.rs`, `unit_aerial_forward_cloud.rs`, `unit_special_up_cloud.rs` (byte-identical to the
  `moves/` files, checked with cmp). `Cargo.toml` unchanged.

Build (2026-10-14): `cargo skyline build --release -- --offline` in the copy, `CARGO_TARGET_DIR` =
`builds/.cache/MV-aerial_forward__cloud-target` -> exit 0, 0 errors, 9 warnings all in base files
(loadout.rs, menu.rs). NRO 303104 bytes, sha256 `5d88a98c4cc1fd93738406bf7d42144bcc89bcf6d94a686bdb1dd92676847ba1`.
`python -I mods/mii_customizer/tools/stack-frames/stack_frames.py <nro>` -> `OK`, exit 0.

## 3. Sword recipe (Buster Sword on the Gunner) - reusable for other sword moves

1. **Model.** Cloud's sword is not an article: it is two meshes of his body model,
   `bastar_sword_R_VIS_O_OBJShape` / `bastar_sword_L_VIS_O_OBJShape`, each single-bound (no skin weights)
   to `HaveR` / `HaveL`, vertices already in that hand bone's space (blade along +Y, 17.4 units). So a
   stand-alone model is: those two mesh objects re-parented to one bone `Have` (identity), renamed
   `mccloud_sword_r/_l`; Cloud's material `def_cloud_004` renamed `mccloud_sword` with its three nutexb copied
   unchanged; skeleton = `[Have]`; `model.numshexb` from `MeshExData.from_mesh_objects`; empty `model.nuhlpb`;
   `model.nusrcmdlb` = `model.numdlb`; `model.xmb` copied from G&W's `normal_weapon` article. Builder:
   `moves/aerial_forward__cloud/mccloud_build.py::build_sword` (ssbh_data_py). Output (shipped as is):
   `fighter/miigunner/model/mccloudsword/c00/*` (4.2 MB, mostly textures).
2. **Visibility.** The article's own clips select the blade (the article clip's Visibility track wins over any
   article-level call - reference repo handbook/08). Two one-frame clips, `a00mccloudswordr.nuanmb` (r True, l
   False) and `...l`, motion kinds `mc_cloud_sword_r` / `_l` in the article's own `motion_list.bin` (path hash
   `fighter/miigunner/motion/mccloudsword/c00`, entry layout copied from G&W's article list, tail = sound,
   effect hash) plus G&W's `update.prc`.
3. **Article.** `smashline::clone_weapon("gamewatch", *WEAPON_KIND_GAMEWATCH_NORMAL_WEAPON, "miigunner",
   "mccloudsword", false)` -> local id `FIGHTER_MIIGUNNER_ARTICLE_TERM + index`. Why this donor: it is the
   clone the reference mod saw render on the console (prop without status code); its native init
   (`main+0xa802a0`, read 2026-10-08) only reads an owner work int and two `get_param_float` values, nothing
   G&W-specific that can crash. Registered only when `sd:/ultimate/mods/*/fighter/miigunner/model/mccloudsword/
   c00/model.numshb` exists, because a registered article without files crashes every Gunner at match start.
   Gunner articles exist only for `c00`, so one slot of files is enough.
4. **HaveR attach.** After `generate_article` the owner ties the article's joint `have` to its own `haver`
   with the call a vanilla weapon makes on itself (lua2cpp_pit.nro 0x256b0..0x257ec, decoded):
   `remove_model_constraint`, `unlink/link(LINK_NO_CONSTRAINT, owner id)`,
   `set_model_constraint_pos_ort(LINK_NO_CONSTRAINT, "have", "haver", POSITION|ORIENTATION, true)`,
   `set_attribute(LINK_ATTRIBUTE_REFERENCE_PARENT_SCALE, true)`; then `change_motion(mc_cloud_sword_r)` and
   `set_visibility_whole(true)`. Hand switch = same calls with `havel` and `mc_cloud_sword_l`
   (`mccloud::set_hand`). `haver` hashes case-insensitively to the Gunner's `HaveR`, same axes as Cloud's.
5. **Removal.** `mccloud::sword_guard` (on_line Main): when the sword is out and the motion is none of the
   eight Cloud kinds -> `remove_exist`. Acts on the transition only.
6. **Trail.** Not used by the fair (Cloud has none). For Climhazzard: Cloud's ribbon textures copied to the
   Gunner's own trail folder `effect/fighter/miigunner/trail/tex_mc_cloud_sword1_red.nutexb` /
   `tex_mc_cloud_sword2.nutexb`, with only the 64-byte NUTEXB footer name rewritten to the file name (trails
   are requested by footer name), requested by `AFTER_IMAGE4_ON_arg29(tex_mc_cloud_sword1_red,
   tex_mc_cloud_sword2, 12, haver ...)`. The vanilla Gunner has no trail folder: that the folder is found once
   ARCropolis adds it is D.
7. **Effects/sounds** go into the Gunner's own bank (`mccloud_effects.py`, `mccloud_sounds.py`), never a donor
   folder (workspace kb/findings/effect-ownership-of-donor-banks-and-per-slot-trails.md).

For Corrin's up air: steps 1-5 apply with the donor mesh/bone names swapped; check first whether the donor
weapon is a body mesh (as here) or already an article (then clone that article instead and still verify its
native init offline).

## 4. Shared Gunner files (additions, not whole files)

Built by `moves/aerial_forward__cloud/build_assets.py` against the vanilla files into
`gamedata/mii_customizer/moves/aerial_forward__cloud/reference/`; the coordinator re-runs the scripts on the
merged base:
- motion list: `motion_list_vanilla_plus_owned.bin` (774 + 2 entries, sha256 `8b850847cd74e9fa...`).
- `ef_miigunner.eff`: `mccloud_effects.py --base <bank> --output <bank>` adds 8 handles for both units
  (MC_CLOUD_SWORD_FLARE, _AIRF_SLASH, _SPEEDLINE, _CLIMHAZZARD_SWORD/_STING/_SLASH/_SLASH2/_SLASH3); vanilla 60 ->
  68 handles, 0 id relocations, re-dump compares every decoded field (sha256 `6a1cce88ab467c32...`).
- `se_miigunner.*`: `mccloud_sounds.py --base <dir> --output <dir>` appends 6 tones (89 -> 95), byte copies,
  tone names not prefixed (renaming would mean rewriting records).
- `config.json` `new-dir-files` under `fighter/miigunner/c00`: the 19 package files of the manifest.

## 5. Checks run (2026-10-14)

- `python -I mods/mii_customizer/moves/aerial_forward__cloud/build_assets.py` -> clips 80 / 47 frames, 18 donor
  nodes dropped each, reference 776 entries, sword 2 meshes, effects +8, sounds +6, 19 package files.
- `python -I mods/mii_customizer/evidence/moves/aerial_forward__cloud/check.py` -> `ALL CHECKS PASSED`, exit 0
  (both units; manifests, motion entries vs code names and Cloud's entries, all ATTACK args vs decode,
  effect/trail/sound names vs merged banks, params vs vl.prc / fighter_param, sword model and clips).
  `--negative`: 3 of 3 mutations caught (spike angle, dive fall frames, effect name).

## 6. Console test (at most 8 steps)

Package: plugin copy NRO + both units' package files + the three reference additions merged by the coordinator.
1. Boot. Log: `MV|cloud_sword|files=found|article=<n>` (n = 14 if no other clone). `files=missing` = article files not installed.
2. Gunner A (Mii chose forward air Cloud and up special Cloud), Gunner B vanilla, training.
3. A forward air: Cloud's swing, Buster Sword in the right hand (log `cloud_sword|hand=r|... target_joint=0x5..` once), slash arc and flare, Cloud's swing sound; sword gone after the move.
4. A forward air an opponent offstage early in the hit (frames 18-19): spike. Grounded opponent: 60 deg launch. Damage 14/13/11.
5. A land during the swing: 11-frame landing with Cloud's landing pose; land after frame 43: normal landing (autocancel).
6. A neutral/back/up/down air: vanilla Gunner, no sword.
7. B forward air: vanilla (shot), no sword, no `chosen` log line.
8. A sword placement: if the blade is at A's feet or not drawn, report which (see section 7).

Rollback: remove the menu `allow` line or create `sd:/ultimate/mii_customizer/moves_off`.

## 7. What only the console can show (tier D)

- That the cloned `normal_weapon` article renders on a Gunner and that the model constraint holds it in
  `haver` (the reference mod's failed `chrom_sword` clone, R-22, rendered nothing; that clone had no
  `change_motion`, this one has). The `cloud_sword|hand=` log prints the constraint target joint and flags read back.
- The retargeted animation's look; landing lag 11 via `sub_get_landing_motion_rate`; the spike and launch angles.
- That `mc_cloud_*` effect handles and the two appended tones resolve in game.
