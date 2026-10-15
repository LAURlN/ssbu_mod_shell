## Costume themes

Pyra/G&W c06 uses a nearly black silhouette, grey outlines and a subtle violet
tint, with matching props. Mythra c06 keeps the
Black & Pink Mythra donor's body, sword, UI, particle bank and sword trails.
Pyra/G&W c07 uses an ivory silhouette, charcoal outlines and warm grey details,
with matching props. Mythra c07 uses ivory and
gold armour, golden hair, golden crystals and a matching sword. Skin and eye
textures, normals, and material parameter maps retain the vanilla data.

`tools/build_color_themes.py` generates the assets through Ultimate Tex 0.3.1
and Pillow/NumPy. It preserves the NUTEXB compression format, mip count and
internal resource name. Portrait recolouring changes the existing BNTX image
payloads, retaining the original container, resource names and dimensions.
Generated assets are cached by source hash, transform revision and theme.

## Effect isolation

The package includes the existing local game-13.0.4
`tools/one_slot_effects/libone_slot_eff.nro`, copied from the downloaded
Ultimate S 5.0.4 dependency. Install the package's **atmosphere** directory
alongside its **ultimate** directory so Skyline loads the dependency.

The paths follow [One Slot Effects' costume lookup and trail routing](https://github.com/Claude-1308/one-slot-effects/blob/master/src/lib.rs):

| Costume | Particle bank | Sword trails |
| --- | --- | --- |
| c00–c05 | Vanilla `ef_elight.eff` | Vanilla `trail/` |
| c06 | `ef_elight_c06.eff` | `trail_c06/` |
| c07 | `ef_elight_c07.eff` | `trail_c07/` |

Both custom banks are under `effect/fighter/elight/`. `config.json` declares
the c06 assets only in `fighter/elight/c06` and the c07 assets only in
`fighter/elight/c07`, including all five trail textures for each costume.
The package ships **no shared bank or shared trail overrides**. Removing or
omitting the dependency prevents these custom paths from being selected.

c06's bank and trails remain byte-identical to the dark donor. c07's sword
effects and trails are rebuilt from scratch using c06's dark effects (Black & Pink Mythra).
The dark crimson/black sword slashes, beams, auras, and trails are transformed into
radiant white and light gold (with pure white cores and light champagne gold edges).
The sparkle and switch effects (down-special start/end, win pose, sword passive sparkles,
smash/photon sparkles, and stars) incorporate delicate luminous light pink alongside
radiant light gold and white highlights.
Scalar/normal texture masks, alpha curves, key times, effect names,
shaders, geometry and the binary layout remain unchanged. The VFXB colour
field layout follows [Smash Effect Editor's parser](https://github.com/J0K3V/smash-effect-editor/blob/master/src/eff.rs).

`plugin/src/swap_effects.rs` routes G&W/Pyra c06/c07 down-special start/end
visuals to the corresponding `elight_change_start_c06/c07` and
`elight_change_end_c06/c07` resources. Only effect scripts are replaced;
native transformation status, gameplay, sound and expression scripts remain.
The original ground/air effect placement and scale are retained. The explicit
Mythra resource suffix avoids classifying the caller's effect bank as Pyra.

## Build and verification

From this project directory:

```powershell
../../toolchains/py312/python.exe build.py
../../toolchains/py312/python.exe tools/verify_color_themes.py
```

Build output: `../../builds/pgwr/pyra_gamewatch_reskin/`.
Set `MGW_PACKAGE` to an absolute path to build and verify in a separate staging
folder. The verified revision is staged at
`../../mod_output/pyra_gamewatch_reskin_theme_revision/`, including both NROs,
`package-sha256.json`, `theme-verification.json` and `theme-preview.png`.
It is intentionally not installed because the user assigned installation to
another concurrently running agent. That agent should use the revised theme
pipeline when producing its final combined build.
Build manifest: `build-record.json`. Verification results:
`theme-verification.json`; decoded texture/portrait preview:
`theme_preview/themes.png`.

Verification checks asset decoding, declarations and costume isolation,
c06 donor hashes, c07 emitter alpha/key timing, untouched particle masks,
and the packaged dependency. Runtime rendering, transformation and simultaneous
c06/c07 fighters still require a console check with the complete package installed.
Check ground and air down-special on c06/c07, starting once as G&W and once as
Mythra, plus vanilla c00/c05 and simultaneous c06/c07 fighters.

## c07 sword effects and glow rebuild — 2026-09-30

c07 sword effects are rebuilt from scratch using c06 Mythra's dark effects (Black & Pink Mythra).
The dark crimson/black sword slashes, beams, auras, and trails are transformed into radiant white
and light gold (pure white cores with light champagne gold body).
The sparkle and switch effects (down-special, passive sword sparkles, star flares) incorporate
delicate light pink highlights alongside radiant gold and white.
Sword edge and glow textures (`alp_light_002_col`, `def_light_004_col`, `def_light_004_emi`, `def_light_005_emi`)
use `fx_gold` champagne highlights. Verification confirms 100% bit-for-bit key count, alpha, and timing preservation.
