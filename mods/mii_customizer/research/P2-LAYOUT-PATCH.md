# P2-LAYOUT-PATCH - one layout-only two-float diagnostic

Task: `prompts/P2-LAYOUT-PATCH.md`. Date: 2026-10-04. Worker: Space Bunny Alpha.
Tier: **B** (offline measurement on already-extracted local files). No console,
no emulator, no runtime observation of any kind, no install, no package.

Scope respected: no Lua, no identity/runtime API work, no edits to
`tools/bflyt-inspect` or `tools/sarc-layout` (both used read-only), no other
worker's files, no `STATUS.md`/`CURRENT_INSTALL.md`/`CHANGELOG.md`, no commits,
no branches, no SD access, no agents. Inputs were read only and are re-hashed
unchanged at the end.

## Summary

**P2-LAYOUT-PATCH: DONE.**

One reproducible diagnostic now exists: a copy of the Mii special editor
`layout.arc` in which exactly two `f32` bytes' worth of meaning changed - the
two scale floats of the row part `set_special_item_00`, set to 75% of `1.0`.
The archive is the same length, has the same 76 members in the same order at
the same offsets, the same header metadata and the same gap bytes, and differs
from the original in **exactly two bytes**, both inside those two floats.

Nothing here shows that the marker works. It shows that a layout-only,
same-length change can be produced reproducibly, and it gives the coordinator a
prepared artifact to test loading with, if the Lua flow review finds it worth
testing.

## Inputs (exact paths, sha256, re-verified after the run)

| file | bytes | sha256 | changed by this task |
|---|---|---|---|
| `gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc` | 723436 | `5ba29f4448686d89d478b17b1d5028dda2374c3e1b66cc3ac7c0f7a6abaad945` | no |
| `gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_special/blyt/make_mii_special.bflyt` | 10408 | `a63cbacc09a9264ff07ac83c1b765dd0caeeaa1afd92bdb58297f774a3c0b3e8` | no |

Both match the values recorded in `research/P2-SARC-WRITE.md` and
`research/P1-LAYOUT.md` (coordinator correction: the original named a nonexistent `P2-LAYOUT.md`), so this task read the same files those reports
describe.

## The change, exactly

Located part: `prt1` at member offset `0x109c`, size 772, payload at `0x10A4`,
node type 3, children 3 (`set_txt_title`, `set_txt_num`, `set_txt_val`).
Payload offsets are from P2-LAYOUT-STRUCTURE and were **re-derived locally**:
the builder walks the block chain itself, `bflyt-inspect` is asked for the same
part, and both must agree on name, offset and both float values before anything
is written.

| field | payload offset | member offset | archive offset | original | patched |
|---|---|---|---|---|---|
| `scale_x` | `+60` | `0x10E0` | `0x14E40` | `1.0` (`0000803f`) | `0.75` (`0000403f`) |
| `scale_y` | `+64` | `0x10E4` | `0x14E44` | `1.0` (`0000803f`) | `0.75` (`0000403f`) |

Archive offsets: `data_offset 0x2000` + member `data_start 0x11D60` + member
offset. `1.0f` and `0.75f` share their low-order bytes, so only byte 2 of each
float differs:

| archive offset | field | original byte | patched byte |
|---|---|---|---|
| `0x14E42` (85570) | `scale_x` | `0x80` | `0x40` |
| `0x14E46` (85574) | `scale_y` | `0x80` | `0x40` |

The builder computes that expectation from the payload instead of assuming the
whole 4-byte span changes, then asserts the archive differs at exactly those
offsets. This was a real correction during this task: the first version of that
check expected all eight bytes to differ and failed, and the fix is the
computed expectation above.

Nothing else changed: not the row name or count, not the position
`(-20, 380)`, not the extent `1212x118`, not the selector group `selector_0`
(7 members), not the child references, not the animations, not text keys, not
Lua, not anything native.

## Deliverable

`mods/mii_customizer/tools/layout-diagnostic/`:

| file | role |
|---|---|
| `build_diagnostic.py` | the builder; parses the SARC independently, pins both inputs, locates the part twice, changes two floats, writes through `tools/sarc-layout`, verifies, and refuses anything it cannot establish |
| `check_layout_diagnostic.py` | smoke check; 80 checks, exit 0 only if all pass |
| `README.md` | usage, pinned defaults, refusals, limits |

The builder delegates the container writing to `tools/sarc-layout` (`rebuild`
for the control, `replace` for the change) and the offset confirmation to
`tools/bflyt-inspect`. It never modifies either tool.

## Outputs

| file | bytes | sha256 |
|---|---|---|
| `gamedata/mii_customizer/P2-LAYOUT-PATCH/control/layout_original.arc` | 723436 | `5ba29f4448686d89d478b17b1d5028dda2374c3e1b66cc3ac7c0f7a6abaad945` (identical to the input) |
| `gamedata/mii_customizer/P2-LAYOUT-PATCH/patched/layout_row00_scale075.arc` | 723436 | `86044f63d4bb4456d906c8d896a4c53ed80c20a298f97bb528fffc3708f55877` |
| `gamedata/mii_customizer/P2-LAYOUT-PATCH/member/make_mii_special.scale075.bflyt` | 10408 | `ea4f8c4fcf9af521ab1faf1459efb6ada081be93da201f83cc39dc22e9c5b106` |

Also written by `sarc-layout` itself:
`control/rebuild.json` and `patched/replace.json` (the latter reports
`changed_members: ["blyt/make_mii_special.bflyt"]`, `unchanged_member_count: 75`,
`metadata_identical: true`, `gaps_identical: true`, `size_unchanged: true`).

## Original vs changed member manifest

Full manifests are in `evidence/P2-LAYOUT-PATCH/manifest_compare.json`
(all 76 members of all three archives, with offsets, name-offset fields and
sha256). Summary:

| property | control vs original | patched vs original |
|---|---|---|
| member count | 76 / 76 | 76 / 76 |
| membership identical | yes | yes |
| changed members | none | `blyt/make_mii_special.bflyt` only |
| members whose offset or name-offset field moved | none | none |
| header fields identical | yes | yes |
| gap spans and gap bytes identical | yes | yes |
| archive size | unchanged | unchanged (723436) |
| archive hash | equal to the input | differs |
| differing byte offsets | none | `0x14E42`, `0x14E46` |

Inside the changed member, reparsing both layouts and comparing every parsed
field gives one difference: the target part's `scale`, `1.0,1.0` -> `0.75,0.75`.
The 43-block chain, the part's offset, size, node type, marker, name, position,
extent, child count and child names are identical.

## Commands run, with exit status

From the workspace root. `python` works here; `python3` is a Windows Store
alias that exits 49.

```bash
# confirm the inputs are the pinned ones
python -c "import hashlib; [print(hashlib.sha256(open(p,'rb').read()).hexdigest()) for p in [...]]"

python mods/mii_customizer/tools/bflyt-inspect/bflyt_inspect.py rows \
  gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_special/blyt/make_mii_special.bflyt \
  set_special_item                        # exit 0, 4 rows, 00 @0x109c

python mods/mii_customizer/tools/layout-diagnostic/build_diagnostic.py --dry-run   # exit 0
python mods/mii_customizer/tools/layout-diagnostic/build_diagnostic.py             # exit 0, 18 checks
python mods/mii_customizer/tools/layout-diagnostic/check_layout_diagnostic.py     # exit 0, 80/80
python mods/mii_customizer/scratch/2026-10-04_P2-LAYOUT-PATCH/compare_manifests.py # exit 0
```

Evidence: `evidence/P2-LAYOUT-PATCH/diagnostic.json` (the builder's 18 checks,
field offsets, hashes), `checks.json` and `checks.txt` (80 checks),
`manifest_compare.json` (full manifests and the two differing bytes), plus its
console output in `manifest_compare.txt`.

## What the checks cover

Builder (18 checks, all pass):

- both inputs re-hashed at the end and unchanged;
- the control is byte-identical to the input;
- the hashes predicted in process before writing equal the hashes of the files
  `sarc-layout` actually wrote;
- archive size unchanged; member count, membership, header metadata and every
  member's start/end/name-offset unchanged;
- exactly one member changed;
- every differing archive byte lies inside one of the two 4-byte floats, and
  the differing set equals the bytes the two floats account for;
- the member payload itself differs only inside those two floats;
- the part is re-located at the same offset after the change, and every other
  parsed field matches;
- both floats equal the requested value at the same offsets.

Smoke check (80 checks, all pass), written against the real CLIs and the files
on disk rather than the builder's own bookkeeping:

- `sarc-layout verify` accepts the input, the control and the patched archive;
- `bflyt-inspect` finds the row at `0x109c` in the emitted payload and reads
  `scale = [0.75, 0.75]` there, and `[1.0, 1.0]` in the original;
  `bflyt-inspect verify` accepts both layouts;
- the three archives are the same length; the patched one differs at exactly
  `0x14E42` and `0x14E46`, which map back into the two scale fields;
- determinism: two `--dry-run` runs produce identical reports and predict the
  same hashes that were written;
- refusals, each exiting nonzero with a reason and writing nothing: ambiguous
  part name (`set_special_item`, 4 matches), unknown part name
  (`set_special_item_04`, 0 matches), wrong archive hash, wrong archive (the
  `edit` layout), wrong member hash, a member that is not a `FLYT`
  (`anim/make_mii_special_in.bflan`), factor `0`, factor `-1`, factor `inf`,
  factor `1e39` (f32 overflow), an output folder inside `P1-LAYOUT`, and an
  output folder inside the input archive's own directory;
- the two read-only input trees are unchanged by file set and sizes after the
  whole run, and the patched diagnostic is still in place after the refusals.

## Manual checks for a later console test

Not requested now, and not performed. If the coordinator decides to test loading
with this diagnostic:

1. (Coordinator correction 2026-10-04: the worker's original step named an
   `atmosphere/contents/ui/...` path and a backup of an existing file. That path was
   not derived from anything in this workspace and no such file exists to back up; the
   game file lives inside `data.arc`.) The install location and loader are **not
   decided here**. A future coordinator package will name them in `CURRENT_INSTALL.md`
   after checking the old mod's install notes; the patched archive would be delivered as
   a file override for ARC path
   `ui/layout/menu/make_mii_special/make_mii_special/layout.arc`.
2. Open the Mii Gunner editor, go to the special (moves) selection screen, and
   look at the **first** special-selection row.
3. Expected if the change is loaded and visible: that row renders smaller than
   the other three. Expected if it is not visible: nothing changes, which is
   equally informative - an animation may overwrite the scale at runtime, and
   this task cannot say which.
4. Check that selecting each direction (up/down through the four special
   slots) and Confirm/Back still behave as before.
5. Remove the override file to confirm the baseline returns.

Any result from step 3 is a **new** observation, not a confirmation of this
report: nothing offline can predict it.

## Limits and unresolved questions

- **Unverified**: that the game, emulator or console accepts a modified
  `layout.arc`. Nothing was loaded anywhere.
- **Unverified**: that there is no runtime checksum or validation of these
  bytes. This task cannot test for it.
- **Unverified**: that payload offsets 60/64 are the row's rendered scale. The
  offsets are measured and double-read; the *meaning* is inferred from
  P2-LAYOUT-STRUCTURE, and no primary format source was consulted or pinned.
- **Unverified**: that the row is visible at all, for the animation reason
  above. The marker is a hypothesis (tier D) about appearance; the byte change
  is a measurement (tier B).
- The refusal for a non-finite or non-positive **original** scale shares its
  validation with the requested value, but the measured originals are `1.0`, so
  the smoke check exercises that branch through requested values rather than
  through a synthetic degenerate layout, which would mean putting a copy of
  game data in the repository.
- One layout, one row, one factor. Nothing here says anything about adding a
  row (P2-LAYOUT-STRUCTURE's four open questions are untouched), about the
  `edit` layout, or about other archive members.
- This is not a package, not a version, not an installation directory, and it
  is not marked READY. The coordinator decides whether it ships alongside
  other diagnostics after reviewing the Lua flow.

## Changed files

Exclusive paths only:

- `mods/mii_customizer/tools/layout-diagnostic/build_diagnostic.py`
- `mods/mii_customizer/tools/layout-diagnostic/check_layout_diagnostic.py`
- `mods/mii_customizer/tools/layout-diagnostic/README.md`
- `mods/mii_customizer/research/P2-LAYOUT-PATCH.md` (this report)
- `mods/mii_customizer/evidence/P2-LAYOUT-PATCH/` - `diagnostic.json`,
  `checks.json`, `checks.txt`, `manifest_compare.json`, `manifest_compare.txt`
- `mods/mii_customizer/scratch/2026-10-04_P2-LAYOUT-PATCH/` - manifest
  comparison script, three `sarc-layout list` dumps, two
  `bflyt-inspect inventory` dumps, one earlier `spec.json`
- `gamedata/mii_customizer/P2-LAYOUT-PATCH/` - `control/`, `patched/`, `member/`

Not touched: `gamedata/mii_customizer/P1-UI/` and
`gamedata/mii_customizer/P1-LAYOUT/` (inputs, re-hashed unchanged),
`tools/bflyt-inspect/`, `tools/sarc-layout/`, other workers' folders,
`STATUS.md`, `CURRENT_INSTALL.md`, `CHANGELOG.md`, git.

## Suggested next experiment

Have the coordinator review `research/P2-UI-FLOW.md` first. If the Lua flow
review shows the special editor is reachable and its rows are laid out from this
layout, then this diagnostic is the cheapest possible loading probe: one file,
two floats, no Lua change, and a rollback that is deleting one file. If the
flow review shows the row scale is overwritten by animation on entry, a
different, still layout-only marker would be needed - position of a row that is
not animated, for instance - and that choice should wait until someone has read
the flow report.

**Task P2-LAYOUT-PATCH: DONE.**