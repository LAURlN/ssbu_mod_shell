# Lucas down smash / Ness back throw effect themes on Mythra c06/c07 — 2026-10-03

Offline record (tier B for bytes and decoded fields, tier D for appearance in game).
No console, no emulator, no SD card, no install, no NRO rebuild, no commit.

## What was asked

Theme the PSI effects of Lucas's down smash and Ness's back throw on the modded Mythra body
(`elight` c06/c07) so they match each costume's existing effects: c06 scarlet/dark, c07 luminous
white/gold. Gameplay, timing, animation, sounds and hitboxes must not move.

## Inputs (recorded)

| input | value |
| --- | --- |
| baseline package | `builds/pgwr/dk_cargo-0.1.1-test` (latest recorded install: DK cargo 0.1.1-test over Incineroar 0.3.0 over shared 0.20.20) |
| baseline mod tree | `dae0bff00e20cbe3b5da37215fe82f745ac27c7d8776d180fd08644fc3be6f5e` (5098 files), recomputed here and equal to the install record |
| `effect/fighter/elight/ef_elight_c06.eff` | `fcdd6caa49b5d8b7c50a9c44a612acfba757556560b7b79d5561af4b41ecbc17` (14,698,064 B) |
| `effect/fighter/elight/ef_elight_c07.eff` | `1734bb5443e28b956c5c7bb478aac94030dbaee2b22a319ea13d3f37ef26648b` (15,402,576 B) |
| converter | EffectLibrary `d5491138d645221ec92189eeff3ded8c43fd0a1a`, `builds/.cache/hero_effect_converter/bin/` (hashes in MANIFEST) |
| tool | `tools/customize_lucas_ness_effects.py` 1.0.0, sha256 `11b21eb3dc4f7912533b341109c2e21b50415b8de70896f218c4819abc667547` |

The two banks are byte-identical in 0.20.20, gaogaen_throw_b-0.3.0 and dk_cargo-0.1.1-test: the
Incineroar and DK cargo additions did not touch them.

## Existing costume themes (measured first, `P_Elight*` colour keys of the installed banks)

- **c06**: saturated red at hue 0 dominates (590 keys, from `(0.23,0,0)` to `(1,0,0)`), then
  white cores (288), violet hue 270 (180) and magenta hue 300 (122).
- **c07**: white/grey (657), pale and champagne gold hue 30-60 (575), light pink hue 330 (264).

Both banks still held the three donor sets in the donors' stock colours (Lucas: yellow, blue,
orange, violet; Ness: green, cyan, blue, pink) - identical in c06 and c07.

## What changed

Three emitter sets, 20 emitters, in each slot's own bank:
`LUCAS_PSI_HOLD` -> `P_LucasPsiHold` (4), `LUCAS_PSI_ATK_LW` -> `P_LucasPsiAttackLw` (8),
`NESS_PSI_RUSH` -> `P_NessPsiRush` (8).

- **17 emitters**: constant `Color0`/`Color1`, the live `Color0` keys and, where a glow lift
  helps, `ColorScale` (c06 hexagons 1.2 -> 1.3; c07 stars 1.2 -> 1.4, hexagons 1.2 -> 1.35,
  Ness line/rings 1.3 -> 1.45).
- **3 emitters** draw a colour-baked star sprite with white constants, so the sprite itself
  is re-hued: `ef_lucas_flash00` (id 621195579, used by `P_LucasPsiAttackLw/flash1` and
  `P_LucasPsiHold/flash2`) and `ef_ness_flash00` (id 97457052, `P_NessPsiRush/flash2`).
  Alpha, size, format, mip count and the white core are kept. Both textures are used by no
  other emitter set in either bank (measured; the tool refuses to run otherwise).

Palette per slot (full table: `THEMES` / `TEXTURES` in the tool; picture: `theme_preview.png`):

- **c06** scarlet `(1,0.07,0.12)`, crimson, blood `(0.45,0,0.03)`, magenta `(1,0.09,0.78)`,
  violet `(0.59,0,1)`, rose-white cores. Lucas reads scarlet with violet/magenta accents; Ness
  keeps its ring/line/flash contrast as magenta-violet rings, scarlet lines, rose flash.
- **c07** white, ivory, pale/light/champagne gold, light pink `(1,0.78,0.88)`. Lucas reads
  white-gold with pink hexagon accents; Ness reads pink-white rings with gold lines.

The texture ids shared with other sets (`3332780892`, `3167451124`, model `2121125346`) are
greyscale/data masks and are **not** touched.

## Output

`builds/pgwr/lucas_ness_effect_theme-0.1.0/` — a two-file asset overlay, MANIFEST sha256
`42631f4f413679c49bb335e1960a4f62cfd4d8805f7a690d851b475ef2836f25` (copy beside this file).

| file | sha256 | bytes |
| --- | --- | --- |
| `effect/fighter/elight/ef_elight_c06.eff` | `79d1fcc0d4688bd8902d624ac79fbded0f8b2bd1ba0fb9d25f310ab755f19d8f` | 14,698,064 (unchanged size) |
| `effect/fighter/elight/ef_elight_c07.eff` | `d7217697ac7e6af58440de6b61d7f5d0c632905a3cc219632fd9d5b38387ab98` | 15,402,576 (unchanged size) |

Delta tree (sorted path TAB sha256 LF): `c2ca1592e3286d70093b03ed3248b43233e5ad6b9ab72704f91c5dcd581a04fe`.
No NRO, no `config.json`, no motion, sound, param or model file.

## Checks run (all passed, `--package` then `--verify-package`)

1. **Converter round trip**: decoding and re-exporting each untouched recipient reproduces it
   byte-for-byte (sha equal), so decoded-field statements are statements about the recipient.
2. **Decoded preservation**: 3619 decoded entries per slot compared after re-export; the 3543
   outside the three sets are identical (every other emitter's fields, every texture, model,
   shader, animation block, the name table and set order; 130 sets before and after).
3. **Closed field list**: inside the three sets only `ParticleColor.Color0/1 R,G,B`,
   `EmitterStatic.Color0.Keys[0..2].X/Y/Z` and `EmitterStatic.ColorScale` differ. Key times,
   alpha, scale, emission, shape, render state, shaders, models, `EASL`/`CADP` are equal.
4. **Independent raw-byte diff** (no converter): c06 122,719 and c07 124,164 changed bytes, **0**
   outside the 20 owned emitter blocks (of 827) and the 2 owned textures (of 111 / 113); the
   emitter table, texture table and every texture header are equal.
5. **Reproducible**: a second build from the same input gives the same sha256; the texture
   encoder output is pinned by hash.
6. **Idempotent**: the merge applied to its own output changes 0 bytes.
7. **Negative controls, all fired**: one byte of an unrelated emitter
   (`P_ElightSwordBeamS/center1`) -> rejected; one pixel byte of an unrelated texture
   (`ef_bayonetta_light01`) -> rejected; the unthemed recipient presented as themed -> rejected.
8. **Concurrent-addition control** (`concurrent_control.json`): the c06 recipient was first
   extended with a stand-in for another agent's work (`NESS_PSI_CATCH`, 131 sets, sha
   `dbea9ed63102...`, not the recorded input). The theme merged onto it with the same 122,719
   changed bytes, 0 outside the owned ranges, the stand-in set present and field-identical.
9. **Loader resolution**: each bank is `effect/fighter/elight/ef_elight_c0X.eff`, declared in
   the baseline `config.json` under `new-dir-files["fighter/elight/c0X"]` and nowhere else; the
   package ships no donor folder; `libone_slot_eff.nro` is present; each of the three resource
   names has exactly one bank entry resolving to its emitter set; every texture the 20 emitters
   sample is in the output bank; the installed plugin `214dc3126430...` carries
   `lucas_psi_hold`, `lucas_psi_atk_lw`, `ness_psi_rush`.

## Gameplay preservation

The delta contains no script, plugin, motion, param or sound file. Hitboxes, damage, frame
data, animation and sound are defined outside the `.eff` and are byte-identical because their
files are not in the delta. Inside the bank, effect timing and shape fields are in check 3.

## Not verified

Appearance in game (tier D): additive glow strength, how dark the c06 crimson reads over bright
stages, whether c07 washes out. Only the console can show that.

## Console checks (visual, about 3 minutes; log not needed)

1. Training, Mythra **c07**, hold down smash: charge orb at the hand is white-gold, no
   orange/yellow-green.
2. Release: three bursts are white stars with gold/pink hexagons, no blue/yellow.
3. Mythra c07 back throw: PSI is pink-white rings, gold streaks, no green/cyan/blue.
4. Mythra **c06**, same three: orb scarlet/magenta; bursts scarlet with violet/magenta
   hexagons; throw magenta-violet rings with scarlet streaks. No yellow, green or blue.
5. Control - c06/c07 side-B, neutral-B, forward smash, Photon Edge: unchanged from before.
6. Control - Mythra c00 down smash/back throw and real Lucas/Ness: vanilla, unchanged.
7. Hit a CPU with all three hits of the down smash and the throw on both slots: damage,
   knockback, timing and sounds as before.

Fail: any donor-coloured (yellow/green/blue/orange) particle in steps 1-4, any change in 5-7, a
missing effect, or a crash (send `sd:/atmosphere/crash_reports/`).
