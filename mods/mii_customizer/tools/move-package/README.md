# Move Package Generator (`tools/move-package/`)

## Purpose
Builds the ARCropolis mod package for `mii_customizer` move transplants (version 0.8.0: P16-FTILT-MOVE).

## Usage
```bash
python tools/move-package/build_p16_assets.py
```

## Outputs
- Package staged under workspace `gamedata/mii_customizer/P16-FTILT-MOVE/package/mii_customizer_moves/`:
  - `config.json`: declarations under `new-dir-files` for `fighter/miigunner/c00`
  - `fighter/miigunner/motion/body/c00/motion_list.bin`: rebuilt motion list with the 3 owned forward-tilt entries
  - `fighter/miigunner/motion/body/c00/c01mcattacks3s.nuanmb`: owned horizontal clip (from Brawler donor)
  - `fighter/miigunner/motion/body/c00/c01mcattacks3hi.nuanmb`: owned upward angled clip (from Brawler donor)
  - `fighter/miigunner/motion/body/c00/c01mcattacks3lw.nuanmb`: owned downward angled clip (from Brawler donor)
- Manifest generated at `tools/move-package/manifest.json`.

## Since 2026-10-07 (session 4): a patch, not a motion list

The package ships `motion_list.motdiff`, not `motion_list.bin`: the user's other mod ships its
own Gunner `motion_list.bin`, ARCropolis keeps one file per path, and a `.motdiff` is applied
on top of whichever list is loaded. The full rebuilt list is written to workspace
`gamedata/mii_customizer/P16-FTILT-MOVE/reference/` as the reference the patch must reproduce.

`motdiff/` is the small Rust tool the generator calls (motion_list_rs 1.5.0, serde_yaml
pinned to 0.8.26, the version the card's ARCropolis links). Build once, from `motdiff/`:
`cargo +stable-x86_64-pc-windows-gnu build --release --target-dir ../../../builds/.cache/motdiff-target`.
Usage: `motdiff diff <a.bin> <b.bin> <out.motdiff>`, `motdiff patch <base.bin> <in.motdiff> <out.bin>`.
Smoke check: the generator itself patches the vanilla list and compares with the reference.
Status: working offline; the console has not yet loaded a motdiff of this mod.
