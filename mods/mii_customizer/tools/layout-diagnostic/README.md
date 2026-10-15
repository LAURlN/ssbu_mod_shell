# layout-diagnostic

Builds **one** layout-only diagnostic: a copy of the Mii special editor
`layout.arc` in which the two scale floats of the row part
`set_special_item_00` are set to 75% of their original values.

That is the whole change. The intended visible effect is a smaller first
special-selection row, so that a later test can answer one question: *does the
game's editor load our changed layout asset at all?*

**Whether the row is actually visible is unverified.** An animation may
overwrite the scale at runtime. That is precisely why this is a diagnostic and
not a feature. Nothing here has been run on hardware or in an emulator, and
nothing here establishes that the game accepts a modified archive.

## Status

Working. `check_layout_diagnostic.py` runs 80 checks and exits 0. Tier **B**,
offline measurement on already-extracted local files.

Python 3 standard library only. It reuses two existing tools read-only:
`tools/sarc-layout` writes the archive, `tools/bflyt-inspect` independently
confirms where the part is. Neither was modified.

## Usage

Paths are relative to the workspace root. On this machine `python` works;
`python3` is a Windows Store alias that exits 49.

```bash
T=mods/mii_customizer/tools/layout-diagnostic/build_diagnostic.py

python $T                 # write the control, the patched archive and the report
python $T --dry-run       # verify and predict hashes, write nothing

python mods/mii_customizer/tools/layout-diagnostic/check_layout_diagnostic.py
```

Every default is pinned, so the plain invocation is the reproducible one:

| default | value |
|---|---|
| archive | `gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc` |
| archive sha256 | `5ba29f4448686d89d478b17b1d5028dda2374c3e1b66cc3ac7c0f7a6abaad945` |
| member | `blyt/make_mii_special.bflyt` |
| member sha256 | `a63cbacc09a9264ff07ac83c1b765dd0caeeaa1afd92bdb58297f774a3c0b3e8` |
| cross-checked against | `gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_special/blyt/make_mii_special.bflyt` |
| part | `set_special_item_00` (must match exactly one `prt1`) |
| factor | `0.75` |
| output folder | `gamedata/mii_customizer/P2-LAYOUT-PATCH/` |
| report | `mods/mii_customizer/evidence/P2-LAYOUT-PATCH/diagnostic.json` |

## What it does, in order

1. **Independent SARC read.** The archive is parsed by this file's own reader,
   so the extraction is never validated against the tool that later writes it.
2. **Pin the inputs.** A different archive hash or member hash is a refusal, not
   a patch. The extracted member is also compared byte-for-byte with the
   separately extracted `.bflyt`, so both extraction paths must agree.
3. **Locate the part twice.** A local block walk must find exactly one `prt1`
   whose name starts with the requested name, and `bflyt-inspect` must agree on
   the name, the block offset and both float values. Only then are the offsets
   re-read from the real bytes.
4. **Change two floats.** `scale_x` at payload+60 and `scale_y` at payload+64 of
   the located part, each multiplied by the factor and re-packed as `<f`. The
   result must be the same length and still start with `FLYT`.
5. **Predict, then write.** The output hashes are computed first through
   `tools/sarc-layout`, which re-serialises the container itself. Only if the
   unchanged rebuild is byte-identical to the input is anything written.
6. **Verify what was written.** Re-parsed independently: same member count,
   same membership, same header metadata, same per-member start/end/name-offset,
   exactly one changed member, every differing archive byte inside one of the
   two floats, the part re-located at the same offset after the change, and
   every other parsed field (block chain, node type, marker, name, position,
   extent, child names, child count) identical.
7. **Prove the inputs are untouched**, last.

## Refusals

Each of these exits 2 with a reason on stderr and writes no file:

| refusal | why |
|---|---|
| archive sha256 differs from the pinned value | patching an unrecognised game file is never safe |
| member sha256 differs, or the extracted member disagrees with the pinned `.bflyt` | same, one level down |
| member payload is not `FLYT` | a `.bflan` or other member is not a layout; unsupported structure |
| `prt1` block walk does not consume the member exactly | the format model does not hold; no offset guessing |
| zero or more than one part matches the name | ambiguous location |
| inspector and local walk disagree on name, offset or scale | two readers disagree, so trust neither |
| node type is not 3, or child records do not fit | unsupported structure |
| original or requested scale is non-finite | NaN/Inf are refused, not written |
| original or requested scale is zero or negative | refused |
| requested scale does not fit in an `f32`, or overflows to non-finite | refused |
| output resolves to a supplied input, or inside an input tree | inputs are read-only |
| output outside the workspace | refused |
| unchanged rebuild is not byte-identical | the control would be meaningless, so nothing is written |
| any post-write verification fails | the run fails; the report is not written |

## Files it produces

| path | what |
|---|---|
| `gamedata/mii_customizer/P2-LAYOUT-PATCH/control/layout_original.arc` | unchanged control, byte-identical to the input |
| `gamedata/mii_customizer/P2-LAYOUT-PATCH/patched/layout_row00_scale075.arc` | the diagnostic, same length as the input |
| `gamedata/mii_customizer/P2-LAYOUT-PATCH/member/make_mii_special.scale075.bflyt` | the same-length patched member payload |
| `.../control/rebuild.json`, `.../patched/replace.json` | reports written by `sarc-layout` itself |
| `mods/mii_customizer/evidence/P2-LAYOUT-PATCH/diagnostic.json` | this tool's own check list and field offsets |
| `mods/mii_customizer/evidence/P2-LAYOUT-PATCH/checks.json` | the smoke check's results |

Game-derived files stay in the task's `gamedata/` folder. This tool never writes
into a source tree, and it never modifies a supplied input.

## Measured for this layout

| field | member offset | archive offset | original | patched |
|---|---|---|---|---|
| `scale_x` | `0x10E0` | `0x14E40` (`0x14E42` differs) | `1.0` | `0.75` |
| `scale_y` | `0x10E4` | `0x14E44` (`0x14E46` differs) | `1.0` | `0.75` |

`1.0f` is `00 00 80 3F` and `0.75f` is `00 00 40 3F`, so only one byte per float
changes. That is why the whole archive differs by exactly two bytes, and the
tool checks against that computed expectation rather than assuming the full
4-byte spans change.

## Limits

- **Same length only.** No member is added, removed, renamed, grown or shrunk,
  and no archive is repacked. Same-length replacement is the smallest claim
  that has to be defended.
- **Two floats, one part.** No row name, row count, position, selector group
  membership, child reference, animation, text key, Lua or native behaviour is
  touched.
- **Unverified**: that the game, the emulator or the console accepts a modified
  `layout.arc`; that there is no runtime checksum; that these two floats are
  the row's rendered scale rather than some other transform (the offsets are
  measured, the meaning is inferred); and that the row's visibility survives
  whatever the animations do.
- **One layout.** Other editor rows and other `layout.arc` files are out of
  scope; each would need its own pinned hashes and its own part.
- The refusal for a non-finite or non-positive **original** scale is implemented
  in the same validation used for the requested values, but the measured inputs
  are `1.0`, so the smoke check exercises that branch through requested values
  (factors `0`, `-1`, `inf`, `1e39`) rather than through a synthetic corrupt
  layout, which would mean copying game data into the repository.
- Nothing here is an installation directory or a release package. The
  coordinator decides what, if anything, ships alongside other diagnostics.

See `research/P2-LAYOUT-PATCH.md` for the full run, hashes, commands and limits.