---
title: SSBU modding stack overview
summary: The loaders, frameworks and file-format tools an SSBU mod is built from, and where each piece lives on the SD card
status: seed
tags: [skyline, arcropolis, smashline, cargo-skyline, formats, overview]
updated: 2026-10-05
source: training knowledge + release pages checked 2026-10-01
---

## Overview

Written at lab setup from general knowledge. Release versions below were read from GitHub on
2026-10-01; everything else is untested here. Verify before relying on it and upgrade this note.

Game: Super Smash Bros. Ultimate, title ID `01006A800016E000`. Mods target the final 13.0.x
update line. Code mods contain offsets that depend on the exact game version. The user's dump is
**13.0.4** (see `kb/reference/local-machine.md`); most public offsets and guides were written for
13.0.1-13.0.3, so check which version a source targets before using an address from it.

## Layers

| layer | what it does | lives at (SD card) | project |
|---|---|---|---|
| Skyline | Runtime hooking environment; loads `.nro` plugins into the game process | `atmosphere/contents/01006A800016E000/exefs/` (`subsdk9`, `main.npdm`) | github.com/skyline-dev/skyline (release `beta`, 2026-04-12) |
| ARCropolis | Skyline plugin that replaces files from the game's `data.arc` with files from mod folders | plugin: `atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libarcropolis.nro`; mods: `ultimate/mods/<mod name>/` | github.com/Raytwo/ARCropolis (v4.1.1 upstream 2026-09-25; **the user's card runs an older 4.0.x-era build**, see note below) |
| Smashline | Skyline plugin + Rust API for replacing fighter scripts (ACMD) and status scripts | `.../romfs/skyline/plugins/libsmashline_plugin.nro` | github.com/HDR-Development/smashline (v1.6.8, 2026-09-16) |
| Mod plugin | The mod's own compiled Rust code | usually `ultimate/mods/<mod name>/plugin.nro` (loaded by ARCropolis) or the Skyline plugins folder | built with cargo-skyline |

**Card reality (2026-10-05).** The card's `libarcropolis.nro` (sha256 `49b6f634...`) is an
older-generation build: its strings carry the pre-refactor `arcropolis::fs::loaders` code,
the old XMSBT wording and Orbits check-out paths; the v4.1.x `modfs`/handler-chain markers are
absent. The game is 13.0.4, which those releases gate on for v4.0.7/v4.0.8. The v4.1.1 note in
this table describes upstream, not this card. Evidence (tier B):
`mods/mii_customizer/research/P5-MSG-PROBE.md` coordinator addendum.

## File mods (ARCropolis)

A mod folder mirrors paths inside `data.arc`, for example
`ultimate/mods/my_mod/fighter/mario/model/body/c00/...` or `.../fighter/mario/param/vl.prc`.
Extra files that do not exist in the vanilla arc need a `config.json` in the mod root declaring
them. ARCropolis also applies param patches (`.prcx` / `.prcxml`) and message patches (`.xmsbt`)
instead of whole-file replacement, which keeps mods compatible with each other.

## Code mods (Rust)

- `cargo install cargo-skyline`, then `cargo skyline new <name>` / `cargo skyline build --release`.
  It uses a custom Rust std for the Switch target (`cargo skyline update-std`).
- Output is a `.nro` under `target/aarch64-skyline-switch/release/`.
- Crates commonly used: `skyline` (hooks, patching), `smash` / `skyline_smash` (game bindings),
  `smashline` (script replacement), `smash_script`.
- The HDR mod (github.com/HDR-Development/HewDraw-Remix) is the largest open-source example of
  this stack and a good place to look for how something is done.

## File formats and tools

| format | content | tools |
|---|---|---|
| `data.arc` | The game's main archive | ArcExplorer (GUI, installed at `<ArcExplorer dir>`), `smash-arc` (Rust library) |
| `.prc` | Params (fighter attributes, etc.) | prcEditor, `prc-rs` / `prcx` (diff patches), `param-xml` |
| `.numdlb/.numshb/.numatb/.nusktb/.nuanmb` | Models, meshes, materials, skeletons, animations | `ssbh_lib` / `ssbh_data` (Rust, Python bindings), SSBH Editor, Blender plugins |
| `.nutexb` | Textures | `nutexb` (Rust), ultimate_tex |
| `.msbt` | Text | `msbt` tools; ARCropolis `.xmsbt` patches |
| `.nus3audio/.nus3bank` | Audio | nus3audio-rs |
| motion_list.bin, `.bin` ACMD | Animation lists and move scripts | `motion_lib`; scripts are normally replaced in Rust via Smashline rather than edited as binaries |

Hash labels (`ParamLabels.csv`, `hashes.txt`) are needed to see readable names in params and arc
paths; they are maintained in github.com/ultimate-research.

## Open questions for the lab

- Exact game version of the user's dump, and whether current Skyline/ARCropolis releases expect it.
- Whether the Skyline `beta` release runs as-is on the current Ryubing build (see
  [emulator test environment](emulator-test-env.md)).
- What the user's own mod (`mods/ssbu_mod_new`) uses from this stack.
