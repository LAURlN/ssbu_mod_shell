# P3-ARC-PROBES - two separately toggleable file-override probe folders, staged

Task: `prompts/P3-ARC-PROBES.md`. Date: 2026-10-04. Worker: Space Bunny Alpha.
Tier: **B** throughout for every claim below; the intended visible effect of each
probe is **D** (hypothesis). Nothing was installed, nothing was run on hardware or
in an emulator, no console test is requested, and nothing here says the game loads
either file.

**P3-ARC-PROBES: DONE.**

Coordinator correction 2026-10-04: `mii_customizer_probe_lua/info.toml` as delivered had an
unterminated `description` string and was not valid TOML. The closing quote was added and
`MANIFEST.json` regenerated; that file's sha256 is now `363c4c5f6e5f...`. The message-table
check suggested at the end of this report was done by the coordinator: the two keys read
"Select Special Moves" and "Side Special" in the extracted `msg_menu.msbt`.

## Summary

Two independent ARCropolis mod folders are staged under
`builds/0.1.0-arc-probes/`, each with one overridden game file and an
`info.toml`:

| folder | overrides ARC path | change |
|---|---|---|
| `mii_customizer_probe_layout/` | `ui/layout/menu/make_mii_special/make_mii_special/layout.arc` | 2 bytes: row `set_special_item_00` scale `1.0,1.0` -> `0.75,0.75` |
| `mii_customizer_probe_lua/` | `ui/script/menu/chara_make/make_mii_special_actor.lc` | 4 bytes inside one string constant: `mnu_mmiif_setup_sp_move_title` -> `mnu_mmiif_setup_sp_move_width` |

They are separate folders on purpose: a later console session can enable one,
the other or neither, which is what makes the two results attributable. They are
**not** a package, not READY, and `builds/0.1.0-arc-probes/MANIFEST.json` says so
in its `status` field: `not installed, not tested on hardware`.

The Lua probe is the one the task asked for and **not** the
`MCUZ_DIAGNOSTIC_TITLE_XXXXXXX` probe P2-UI-FLOW built: the replacement is a key
this same chunk already uses as a text label (`main.p2 K[7]`), so an unknown
message key is not introduced.

## Inputs (read-only, re-hashed unchanged at the end)

| file | bytes | sha256 | matches the prompt |
|---|---|---|---|
| `gamedata/mii_customizer/P2-LAYOUT-PATCH/patched/layout_row00_scale075.arc` | 723436 | `86044f63d4bb4456d906c8d896a4c53ed80c20a298f97bb528fffc3708f55877` | yes, no rebuild needed |
| `gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc` (original for probe A) | 723436 | `5ba29f4448686d89d478b17b1d5028dda2374c3e1b66cc3ac7c0f7a6abaad945` | (the original P2-LAYOUT-PATCH input) |
| `gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc` (original for probe B) | 7799 | `ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d` | yes |

The layout probe input was **not** regenerated: `build_diagnostic.py` was not run,
because the archive already on disk hashes to exactly the value the prompt gave.
The original `.lc` was re-extracted from `data.arc` during this task and hashes
identically to the P1-UI copy (see the archive check below), so the two paths are
the same bytes.

## The mod folder layout, and where it came from

The handbook index (`mods/ssbu_mod_new/handbook/00_INDEX.md`) names
`10_arcropolis_config_json.md` for ARCropolis, plus `17_hardware_test_protocol.md`
and `AGENTS.md` rule 23 for the collective install workflow. Lines relied on,
quoted:

- `kb/reference/ssbu-modding-stack.md`, **seed** (written from general knowledge,
  release pages checked 2026-09-25, marked untested here): *"mods:
  `ultimate/mods/<mod name>/`"* and *"A mod folder mirrors paths inside
  `data.arc`"*; and *"Extra files that do not exist in the vanilla arc need a
  `config.json` in the mod root declaring them."*
- `mods/ssbu_mod_new/handbook/10_arcropolis_config_json.md`, **C** (ARCropolis
  `fs.rs`): the `config.json` keys are `new-dir-infos`, `new-dir-infos-base`,
  `new-dir-files`, `share-to-vanilla`, `share-to-added`. That page is entirely
  about **adding files that vanilla does not have**. Both probes here replace
  files that vanilla *does* have (confirmed against the local archive, below), so
  **no `config.json` is included** - adding one would be the mechanism the
  handbook records as risky (that page's tier-A entries describe startup crashes
  from invented `new-dir-infos`).
- `mods/ssbu_mod_new/handbook/04_motion_lists_animation.md`, item 1: *"a throw is
  an in-place override of a file the base game already ships in that costume
  group, not the new-file experiment"* - the same shape as these probes.
- `info.toml` is the mod folder's metadata file. Evidence that it exists and what
  it carries, **B**: `mods/ssbu_mod_new/handbook/facts/facts.yaml`
  (`pgwr-card-state-2026-10-02-is-0-20-17`, `input_tree:
  builds/pgwr/0.20.16/ultimate/mods/pyra_gamewatch_reskin`) records a card-side
  re-hash of the whole mod folder whose delta is *"exactly the two down-tilt clips
  plus info.toml"*; `src/pgwr/build.py:1506` writes
  `display_name / authors / version / description / category`. The minimal
  `pmclone` package writes only `display_name / authors / version / description`
  (`src/pmclone/tools/package_loader_check.py:40`).
- On the requirement question the prompt raised: **no handbook page, kb note or
  fact records any file-size or hash requirement for an ARCropolis whole-file
  override.** I searched `handbook/` (all 19 pages), `handbook/facts/facts.yaml`,
  `handbook/graveyard.md` and `kb/` for size/hash/validation rules and found none.
  Both payloads were therefore made **same length as their originals anyway**
  (measured, not assumed), and `check_probes.py` fails if that ever stops being
  true. The absence of a recorded requirement is not evidence that none exists.

`mods/ssbu_mod_new` was read only. No file was copied out of it.

## Probe A - layout

Rebuilt nothing; staged the existing archive.

| | |
|---|---|
| staged sha256 | `86044f63d4bb4456d906c8d896a4c53ed80c20a298f97bb528fffc3708f55877` (723436 B) |
| original sha256 | `5ba29f4448686d89d478b17b1d5028dda2374c3e1b66cc3ac7c0f7a6abaad945` (723436 B) |
| size unchanged | yes |
| differing offsets | `0x14e42` and `0x14e46` - exactly 2 bytes |
| byte values | `0x80 -> 0x40` at both |
| floats read back | `f32` at `0x14e40` = `scale_x` `1.0 -> 0.75`; at `0x14e44` = `scale_y` `1.0 -> 0.75` |

`sarc-layout verify` on the **staged copy** (not the build folder) passes all 12
container checks and rebuilds it byte-identically
(`evidence/P3-ARC-PROBES/layout_archive_verify.txt`). The measurement matches
P2-LAYOUT-PATCH's report exactly, independently re-derived here.

What the user would look at, and what "no visible change" means: open the Mii
Gunner editor's special (moves) selection screen and compare the **first**
special-selector row against the other three; a visible result is that row
rendered at 75% size. "No visible change" would **not** show that the override was
ignored - the row's scale may be overwritten by its own `category_00` animation on
entry, and this task cannot say which (D, already flagged in P2-LAYOUT-PATCH). It
would also not distinguish "override not loaded" from "loaded but animated away";
the next test has to separate those, e.g. by perturbing something the entry
animation does not touch.

## Probe B - Lua chunk

Built with `lua53-inspect setconst --allow-used` from the original chunk.

```
python mods/mii_customizer/tools/lua53-inspect/lua53_inspect.py setconst \
  gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc \
  gamedata/mii_customizer/P3-ARC-PROBES/probe/make_mii_special_actor.lc \
  main.p14 2 "mnu_mmiif_setup_sp_move_width" --allow-used
```

The tool's own output: `main.p14 K[2] = 'mnu_mmiif_setup_sp_move_title'` ->
`'mnu_mmiif_setup_sp_move_width' (29 chars, was 29)`, one consuming instruction
named (`LOADK [2]`), `wrote ... (7799 bytes, was 7799)`, `new tag 0x04 (string)`.

### The 29-character claim was checked, not trusted

`scratch/2026-10-04_P3-ARC-PROBES/measure_keys.py` reads both constants with
lua53-inspect's own parser and prints length plus on-disk extent
(`evidence/P3-ARC-PROBES/key_lengths.txt`):

```
main.p2  K[7] 'mnu_mmiif_setup_sp_move_width'  chars=29 utf8_bytes=29 long_form=False
         tag 0x4a6, size byte 0x4a7, text 0x4a8-0x4c6, bytes on disk match the text
         uses: [(9, 'LOADK')]
main.p14 K[2] 'mnu_mmiif_setup_sp_move_title'  chars=29 utf8_bytes=29 long_form=False
         tag 0x17b2, size byte 0x17b3, text 0x17b4-0x17d0, bytes on disk match the text
         uses: [(2, 'LOADK')]
```

**Both keys are 29 characters.** The prompt's figure is correct. The prompt's
statement that `_width` is "a text label ... (main.p2 K[7])" is also correct, and
P2-UI-FLOW's reading of `main.p2` pc0-12 (a 4-entry title table
`{_normal, _width, _up, _btm}` written with `NEWTABLE B=4` + `SETLIST`, then
`set_text_message(titles[i])`) is what makes it a *label* rather than a bridge
name.

### Verification on the staged file, not the build intermediate

| check required | result |
|---|---|
| file size unchanged | 7799 -> **7799** |
| `verify` exit | **0** (11 PASS, incl. full-consumption to `0x1e77`) |
| `compare` structural differences | **exactly 1**: `main.p14.K[2]` value |
| `roundtrip` | **byte-identical**, sha256 `0ad3f815…` both sides, reparse diff none |
| differing bytes contiguous | window `0x17cc`-`0x17d0`, 4 of those 5 bytes differ, `0x17cd` is `i`->`i` (see below) |
| all differing bytes inside that one string | **yes**, all four inside text `0x17b4`-`0x17d0` |
| every other constant and instruction unchanged | yes - `compare` reports one difference total, so all other prototypes, all other constants and all 794 instructions are structurally identical; byte-level: every byte outside `0x17cc`-`0x17d0` is identical |

Full output: `evidence/P3-ARC-PROBES/lua_checks.txt` and
`evidence/P3-ARC-PROBES/byte_deltas.txt`.

Two byte-level details worth writing down because the prompt asked about them:

- **The differing bytes are not literally contiguous.** Only 4 bytes differ
  (`0x17cc` `t`->`w`, `0x17ce` `t`->`d`, `0x17cf` `l`->`t`, `0x17d0` `e`->`h`);
  `0x17cd` is `i` in `title` and `i` in `width`. So the *changed region* is a
  contiguous 5-byte window whose bytes 1 and 2 happen to coincide. Nothing
  outside that window moved, and the window sits inside the one string. Stated
  precisely rather than rounded to "contiguous".
- **The string's size byte did not move.** `0x17b3` is `30` (= len + 1) before and
  after, and `0x17d1` is the next constant's type tag (`0x04`) before and after.
  Note for anyone re-deriving offsets by hand: `ldump.c` writes no NUL, the dump
  stores only `len` bytes of text.

### `ui/script_patch/` version: re-checked, and it does not exist

P2-UI-FLOW section 6 says the special actor has no patched counterpart. Re-checked
two independent ways (`evidence/P3-ARC-PROBES/arc_index_check.txt`):

1. The local ARC path index `mods/ssbu_mod_new/dumps/decoded/arc_files.tsv`
   (590,711 paths) contains **one** line matching `make_mii_special_actor`:
   line 841, `ui/script/menu/chara_make/make_mii_special_actor.lc`. `ui/script_patch/`
   holds 9 paths in total and `ui/script_patch/chara_make/` holds exactly one,
   `make_mii_edit_actor.lc` (line 526810).
2. A direct lookup in the archive itself with `tools/arc-extract`, not the index:
   `arc-extract --arc gamedata/ssbu-13.0.4/data.arc --out <dir>
   ui/script/menu/chara_make/make_mii_special_actor.lc
   ui/script_patch/chara_make/make_mii_special_actor.lc` -> the base path
   extracts as 7799 B / `ffa2bafa…` and the `script_patch` path is reported
   `MISSING ... the requested resource could not be found`, exit 1.

So overriding `ui/script/menu/chara_make/make_mii_special_actor.lc` targets the one
copy that exists. The re-extracted copy was written to
`gamedata/mii_customizer/P3-ARC-PROBES/arc_check/` and hashes identically to the
P1-UI original.

## Staging, manifest and the check script

```
builds/0.1.0-arc-probes/
  MANIFEST.json
  check_probes.py
  mii_customizer_probe_layout/
    info.toml
    ui/layout/menu/make_mii_special/make_mii_special/layout.arc
  mii_customizer_probe_lua/
    info.toml
    ui/script/menu/chara_make/make_mii_special_actor.lc
```

Each probe folder holds **only** its `info.toml` and its one payload - no
`config.json`, no `plugin.nro`, nothing borrowed from another probe.
`MANIFEST.json` records, per file: `probe_folder`, `path`, `bytes`, `sha256`,
`role`, and for payloads `arc_path`, `original_path`, `original_bytes`,
`original_sha256`, `size_unchanged`, `differing_byte_count`,
`differing_byte_offsets`; plus `directories`, and top-level
`status: "not installed, not tested on hardware"`.

The two `info.toml` entries carry the same field set with `arc_path`,
`original_path`, `original_bytes`, `original_sha256`, `size_unchanged`,
`differing_byte_count` and `differing_byte_offsets` **explicitly `null`** plus a
`note` saying why: they are mod-folder metadata, not files in `data.arc`, so
there is no original to compare them against. Emitting the fields as null rather
than omitting them is deliberate - a reader (or a script) should not have to
guess from a missing key whether "no original" or "not measured" was meant.

`check_probes.py` re-derives all of it from the staged bytes and the originals and
exits nonzero on any mismatch, an unexpected extra **file or directory**, a
missing file, a drifting original input hash, or a payload whose length no longer
matches its original (a same-length rewrite cannot shift later offsets, so a size
change would mean the override is not a drop-in replacement). Verified:

```
python mods/mii_customizer/builds/0.1.0-arc-probes/check_probes.py
4 file(s) checked, 0 mismatch(es)
PASS: staged tree matches MANIFEST.json        exit 0
```

Eight negative controls, each reverted immediately
(`evidence/P3-ARC-PROBES/check_controls.txt`): extra file, extra empty directory,
one byte flipped in the layout payload, Lua payload truncated by one byte, Lua
payload deleted, layout payload copied into the Lua probe folder, `info.toml`
removed, `info.toml` version bumped - **all eight exit 1 with a specific
message**. Controls 2 and 6 **failed to be caught by the first version of the
script** (it walked files only, so an added empty directory or an added payload
path with no manifest entry slipped through in the wrong-folder case only because
the manifest was the thing being compared); it was fixed to walk directories as
well and the controls were rerun. That is recorded rather than quietly fixed,
because it is the reason to trust the controls at all.

The three most load-bearing controls were rerun against the **final** script and
manifest, with the real output in
`evidence/P3-ARC-PROBES/check_controls_final.txt`: extra file -> exit 1; Lua
payload truncated by one byte -> exit 1 with four messages including the explicit
"not a drop-in replacement"; both probes present in one folder -> exit 1 with five
messages; restored tree -> exit 0.

## Commands run, with exit status

All from the workspace root. `python`, never `python3`.

| command | exit |
|---|---|
| `python -c` hash/size of the three inputs above | 0 |
| `python .../lua53_inspect.py verify gamedata/.../make_mii_special_actor.lc` (original) | 0, 11 PASS |
| `python mods/mii_customizer/scratch/2026-10-04_P3-ARC-PROBES/measure_keys.py` | 0 |
| `python .../lua53_inspect.py setconst <orig> <probe> main.p14 2 mnu_mmiif_setup_sp_move_width --allow-used` | 0 |
| `python .../lua53_inspect.py verify <staged lua payload>` | 0, 11 PASS |
| `python .../lua53_inspect.py roundtrip <staged lua payload>` | 0, BYTE-IDENTICAL |
| `python .../lua53_inspect.py compare <original> <staged lua payload>` | 0, exactly 1 difference |
| `python mods/mii_customizer/tools/sarc-layout/sarc_layout.py verify <staged layout payload>` | 0, all_pass: True |
| `python .../byte_deltas.py` | 0 |
| `tools/arc-extract/target/release/arc-extract.exe --arc gamedata/ssbu-13.0.4/data.arc --out gamedata/mii_customizer/P3-ARC-PROBES/arc_check ui/script/menu/chara_make/make_mii_special_actor.lc ui/script_patch/chara_make/make_mii_special_actor.lc` | **1** - by design: 1 extracted, 1 `MISSING` (this is the negative result that proves no `script_patch` copy exists) |
| `python mods/mii_customizer/builds/0.1.0-arc-probes/check_probes.py --write` | 0 |
| `python mods/mii_customizer/builds/0.1.0-arc-probes/check_probes.py` | 0 |
| the eight negative controls above | 1 each |

Not run: `tools/layout-diagnostic/build_diagnostic.py` (the input hash already
matched, so there was nothing to regenerate), any emulator, any console, any
install.

## Limits - what is not established

- **Unverified (D): that the game loads either override.** No file here was
  installed, opened, or run anywhere. A file that ARCropolis never reads, a
  directory the loader does not scan, a plugin that is not enabled - all of these
  would produce "no visible change" and none of them is excluded.
- **Unverified (D): the intended visible effect of each probe.** Probe A assumes
  the row's scale survives the entry animation; probe A's own report already
  flags that the row may be animated. Probe B assumes
  `ComFrameActor.set_sub_title` resolves the key as a message key and that the
  `_width` label's text differs visibly from the `_title` label's text. Neither is
  checked. Even if the file loads, the screen could look unchanged for either
  reason.
- **No requirement found, no requirement satisfied by knowledge.** As above, the
  handbook records no file-size or hash rule for ARCropolis whole-file overrides.
  Same-length is a precaution this task takes, not a documented constraint.
- **`info.toml` contents are not validated against a loader.** Its three keys
  follow the shape of the other mod folders in the mod repo; nothing here tested
  that this loader, at this version, accepts them or shows the mod at all. (The
  mod repo's own test sheet asks a user to confirm "the mod's `info.toml` still
  loads", so that is itself an A-tier observation, not a B-tier one.)
- **`config.json` deliberately absent.** If a later step needs the override to be
  reachable through a path the loader only scans under a declared entry, that
  would be a new question, and the handbook page for it is the one that also
  documents crashing on invented entries.
- **Probe B edits a chunk, not a patch.** `main.p14 K[2]` is the only consumer and
  its only use is `set_sub_title` (P2-UI-FLOW row 10). That is a bytecode reading,
  not a statement about what `set_sub_title` does with the string.
- **`tools/lua53-inspect` was used, not modified.** `tools/sarc-layout` was used,
  not modified. `tools/layout-diagnostic` was not modified and not run.
- Five of this task's own steps needed fixing mid-run, all described rather than
  quietly patched: the check script did not walk directories (controls 2 and 6
  slipped through); `measure_keys.py` first called a function name the tool does
  not have (`parse_chunk`; it is `load_chunk`); `byte_deltas.py` initially sliced
  one byte too far and printed a spurious float read at `0x17d1`, which is the
  next constant's type tag rather than a NUL (`ldump.c` writes no NUL); and -
  worth stating because it is the kind of damage that looks like a content change -
  one of my own *control* scripts re-wrote a staged `info.toml` through Python text
  mode, which on Windows turned its LF endings into CRLF and left a mutated file
  behind after the control was "reverted". The check script caught it (hash
  mismatch, exit 1), both `info.toml` files were normalised to LF by writing bytes
  explicitly, the manifest was regenerated, and every payload check was rerun
  afterwards. **Only the two `info.toml` files were affected by this; both probe
  payloads kept their hashes throughout** (`86044f63…` and `0ad3f815…`).

## What the user would look at, one sentence per probe

**Probe A (layout):** open the Mii Gunner editor's special-move selection screen
and look at the **first** special-selector row against the other three; a visible
effect would be that row drawn at 75% size, and "no visible change" would be
consistent with *either* the override not being loaded *or* being loaded and then
overwritten by the row's `category_00` entry animation, so this probe alone cannot
distinguish those two.

**Probe B (Lua):** open the same screen and look at the **sub-title** above it;
the intended sign is that it reads the side-special ("width") label text instead
of the normal special-moves title, and "no visible change" would be consistent
with the chunk not being loaded, the key not resolving as a message key, or the two
labels rendering the same string in this game's message table - the last of which
is checkable offline but was not checked here.

## Changed files

Exclusive paths only:

- `mods/mii_customizer/builds/0.1.0-arc-probes/` - `MANIFEST.json`,
  `check_probes.py`, and the two probe folders (2 `info.toml` + 2 payloads)
- `mods/mii_customizer/research/P3-ARC-PROBES.md` (this report)
- `mods/mii_customizer/evidence/P3-ARC-PROBES/` - `arc_index_check.txt`,
  `byte_deltas.txt`, `check_controls.txt`, `check_controls_final.txt`,
  `key_lengths.txt`, `layout_archive_verify.txt`, `lua_checks.txt`,
  `probe_check.txt`
- `mods/mii_customizer/scratch/2026-10-04_P3-ARC-PROBES/` - `measure_keys.py`,
  `byte_deltas.py`
- workspace-relative `gamedata/mii_customizer/P3-ARC-PROBES/` - `probe/`
  (the generated Lua chunk) and `arc_check/` (the archive re-extraction used for
  the `script_patch` check)

Not touched: `gamedata/mii_customizer/P1-UI/`,
`gamedata/mii_customizer/P2-LAYOUT-PATCH/` (both re-hashed unchanged at the end),
`mods/ssbu_mod_new` (read-only; no file copied out), `tools/lua53-inspect`,
`tools/sarc-layout`, `tools/layout-diagnostic`, other workers' folders,
`STATUS.md`, `CURRENT_INSTALL.md`, `CHANGELOG.md`, git.

## Suggested next experiment

The coordinator decides whether a console session is requested at all. If one is,
these two probes should go in it **separately toggleable, tested one at a time with
a vanilla control**, because their results are only attributable if they are not
mixed. The highest-value addition to the same session, and the one that would make
probe A's negative result interpretable, is a *third* layout marker that the entry
animation cannot overwrite - e.g. a row position rather than a row scale - so that
"invisible" can be split into "not loaded" versus "loaded and animated away".
Offline, before that session, the cheapest next step is checking the game's
message table for the two keys (`mnu_mmiif_setup_sp_move_title` vs
`mnu_mmiif_setup_sp_move_width`) to confirm probe B would actually differ on
screen, and pinning the ARCropolis release's own requirement (if any) on file
length, since that requirement is currently simply undocumented here.

**Task P3-ARC-PROBES: DONE.**