# P2-LAYOUT-STRUCTURE - selector and part section decode

Task: `prompts/P2-LAYOUT-STRUCTURE.md`. Date: 2026-10-04. Worker: Space Bunny Alpha.
Tier: **B** (offline measurement on already-extracted local files). No console,
no emulator, no archive rebuild.

Scope respected: no Lua edits, no identity work, no archive rebuild, no shared
tool edits, no commits, no SD access, no downloads or installs. Inputs under
`gamedata/mii_customizer/P1-LAYOUT/` were read only and are re-hashed below to
show they are unchanged.

## Deliverable

`mods/mii_customizer/tools/bflyt-inspect/` - a read-only BFLYT inspector with a
README and a 71-check smoke test. It parses the header, the block chain,
`grp1` groups and `prt1` parts, and emits a machine-readable inventory.

## Inputs (exact relative paths, sha256, re-verified at end of run)

| file | bytes | sha256 |
|---|---|---|
| `gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_edit/blyt/make_mii_edit.bflyt` | 21004 | `2668a7ecf146a31e5003df682208d21d3a4cd2d032d4d68e839dfe0853b6dd34` |
| `gamedata/mii_customizer/P1-LAYOUT/unpacked/make_mii_special/blyt/make_mii_special.bflyt` | 10408 | `a63cbacc09a9264ff07ac83c1b765dd0caeeaa1afd92bdb58297f774a3c0b3e8` |

Both hashes match those recorded in `research/P1-LAYOUT.md`. The two child
layouts inspected (the prompt allows at most two):

| file | bytes | sha256 |
|---|---|---|
| `.../make_mii_edit/blyt/make_mii_btn0_01_item.bflyt` | 7976 | `3ffd801b9d6a6db9623ee9c086d4f3b25c9d9ba8fe9ae65fc953872e3a95169c` |
| `.../make_mii_edit/blyt/make_mii_btn0_02_special.bflyt` | 13132 | `96d5fd5d1dc15875bfe8ca557020e9d9cdff4b7aed599baf6b57177847e25ca7` |

## 1. Inclusive section framing (clarified)

Verified offline B: section size includes its 8-byte tag/size header. The next
section is at offset+size. This agrees with the coordinator's actual prior traversal;
there was no offset+8+size in that check. An exclusive-size draft of this worker's
scanner failed and was corrected. All 58/43 sections consume 21004/10408 bytes.

## 2. Decoded structures

Header (little-endian): magic `FLYT`, BOM `ff fe` at +4, `u16 header_size`=0x14
at +6, an **unverified** word at +8, `u32 file_size`=actual size at +0x0C,
`u16 block_count`=58/43 at +0x10.

`grp1` payload = 36-byte preamble + `count` 24-byte NUL-padded name slots, with
`count` at payload+34 and two always-zero bytes at +32 (**meaning unverified**).
`36 + count*24` equals every `grp1` payload length exactly across all four files.

`prt1` payload = 78-byte fixed header (`u16` node type=3, `u16` marker, 32-byte
name at +4, `f32` x/y at +36, scale at +60, extent at +68, `u16` child count at
+76) + `child_count` 40-byte child records with an inline name at record+10.

The region after the child records holds a padding gap, an owner layout name and
further embedded blocks. The tool reports it as a list of names with offsets and
does **not** claim to have decoded it.

### The marker field is not a constant - two false alarms I caused

The `u16` at payload+2 of a name-bearing block takes the values `0x0000`,
`0x00ff`, `0x0200`, `0x02ff` and `0x06ff` across 123 node blocks in four files,
and every block carrying one of them has a valid name.

I twice gated name detection on a guessed marker. Both times the tool silently
skipped real nodes and reported **false unresolved references**: first
`nul_keyhelp`, `maker`, `favorite`, `notice_unedit`, then `set_txt_name_00..03`.
Both were bugs in my scanner, not defects in the files. Name detection now uses
only the name, and the smoke check asserts every node block yields a name so the
regression cannot return unnoticed. Recorded because the failure mode was a
plausible-looking "unresolved reference" report.

## 3. Rows and selectors

`make_mii_edit.bflyt`, `selector_0` @0x4ff0, count 8 @0x501a, 8 members at
+24 stride from 0x501c:

`set_item_00..05`, `btn_cursor`, `set_footer_area`

| row | part @ | size | pos | extent | children |
|---|---|---|---|---|---|
| `set_item_00` | 0x1410 | 1176 | (-515, 316) | 772x113 | 6 |
| `set_item_01` | 0x18a8 | 1144 | (-515, 214) | 772x113 | 6 |
| `set_item_02` | 0x1d20 | 1160 | (-515, 112) | 772x113 | 6 |
| `set_item_03` | 0x21a8 | 752 | (-515, 10) | 772x113 | 6 |
| `set_item_04` | 0x2498 | 4252 | (-515, -220) | 772x362 | 18 |
| `set_item_05` | 0x3534 | 1560 | (-515, -452) | 772x113 | 6 |

Row Y positions descend 316, 214, 112, 10, -220, -452: a vertical stack with
mostly 102-unit spacing, and a 230-unit gap above `set_item_04` because that
row is 362 tall. Consistent with rows, and consistent with the layout having
room for one more row only if something else also changes.

`make_mii_special.bflyt`, `selector_0` @0x2770, count 7 @0x279a:
`set_special_item_00..03`, `set_btn_ok`, `cursor`, `set_footer_area`.

| row | part @ | size | pos | extent | children |
|---|---|---|---|---|---|
| `set_special_item_00` | 0x109c | 772 | (-20, 380) | 1212x118 | 3 |
| `set_special_item_01` | 0x13a0 | 772 | (-20, 252) | 1212x118 | 3 |
| `set_special_item_02` | 0x16a4 | 772 | (-20, 128) | 1212x118 | 3 |
| `set_special_item_03` | 0x19a8 | 772 | (-20, 4) | 1212x118 | 3 |

Measured successive Y differences are 128, 124 and 124 units, versus the larger irregular gaps in `edit`.
The two editors do not share a row-layout convention, so a row added to one
gives no direct template for the other.

Both archives are internally consistent: **61 of 61 group members across the
four files resolve** to a node name defined in the same file (16 / 10 / 20 / 15).
No corruption and no unresolved references.

### Referenced child layouts

Each row part's tail names its owner layout. `set_item_00..03` and `set_item_05`
name `make_mii_btn0_01_item`; `set_item_04` names `make_mii_btn0_02_special`.
Both exist in the same archive, and both parse cleanly (79/79 and 88/88 checks).
`btn_other_try`/`btn_other_random` name `make_mii_btn2_00_try`. So a row's
visual is defined in a **different** `.bflyt`, which is where any matching
`txt1`/`pic1` node edits would go.

## 4. Answer: what an added row would have to update

Measured, offline, and stated as counts and references rather than as a recipe.

**Definitely present and would need to change, if a row is added:**

1. The `prt1` block itself, with the new row name, a position, and its own
   child records. Row parts are separate `prt1` blocks at `item_detail` +12.
2. The `selector_0` `grp1` entry count at payload+34 (currently 8 in `edit`,
   7 in `special`), since a new row is a new group member.
3. The 24-byte member name slot for the new row, appended at the end of the
   `selector_0` entry list.
4. The `file_size` header field at +0x0C and section count at +0x10 must
   reflect inserted sections; enlarged grp1/prt1 sections need correct size fields.
   Later section locations shift in the sequential stream. Growing an archive
   member also requires a reviewed archive placement strategy.

**Required by the format but with unverified semantics - must be checked, not
assumed:**

5. Whether `set_item_06` is a legal next index. The naming is suggestive, but
   nothing measured establishes that the loader accepts a new index, and no
   loader was inspected.
6. Whether the row's text nodes need new entries in the owner child layout
   (`make_mii_btn0_01_item.bflyt`) and whether those child layouts need their
   own count updates. I did not decode their internal group/part references in
   detail.
7. Whether new animations are required. The animation members contain no
   `set_item_NN` strings (P1-LAYOUT), but per the prompt and P1-LAYOUT I do
   **not** claim that absence settles it. Unverified either way.
8. Whether `info/layout.info` must list anything new. Still open from P1-LAYOUT.

**Explicitly not established:** what the `u16` at `grp1`+32 does (always 0 here),
what the `prt1` marker at +2 means, and whether a group member is an index into
another table rather than a name.

So: a new row is **not** a one-field edit. It is a new `prt1`, a group count and
entry, plus an unavoidable re-layout of every later block offset and a `file_size`
correction - and four open questions that offline work cannot settle.

## 5. A false pass I found and fixed

A final acceptance pass against the README's own documented interface showed that
`verify` read only the first file argument and silently discarded the rest, so
`verify <clean>.bflyt <corrupt>.bflyt` **exited 0**. A verification tool that
passes on a corrupt input is worse than none. Fixed so that
`header`/`blocks`/`groups`/`crosscheck`/`verify` process every file given and
return a nonzero status if any fails.

The first fix over-corrected: it treated the second file as a usage error, and
`rows FILE PREFIX` then printed nothing while still exiting 0. Both bugs are now
covered by smoke checks that assert on real exit status and real output.

## 6. Verification performed

All commands run from the workspace root; every one exits 0.

```bash
python mods/mii_customizer/tools/bflyt-inspect/check_bflyt_inspect.py
# 71/71 checks passed

T=mods/mii_customizer/tools/bflyt-inspect/bflyt_inspect.py
B=gamedata/mii_customizer/P1-LAYOUT/unpacked
python $T verify $B/make_mii_edit/blyt/make_mii_edit.bflyt          # 116/116, exit 0
python $T verify $B/make_mii_special/blyt/make_mii_special.bflyt    # 80/80, exit 0
python $T verify $B/make_mii_edit/blyt/make_mii_btn0_01_item.bflyt  # 79/79, exit 0
python $T verify $B/make_mii_edit/blyt/make_mii_btn0_02_special.bflyt # 88/88, exit 0
```

Checks include: the block walk consuming each file exactly, blocks tiling with
no gap or overlap, every `grp1` payload exactly explained by its entry count,
`prt1` child records fitting, every group member resolving in-file, marker values
being measured values, row Y ordering, and rejection of bad magic / truncated
files / out-of-range sizes. The smoke check also asserts the source contains no
write calls, that every multi-file command processes each file given, that a
corrupt second file yields a nonzero exit, and that every documented command
produces output on its documented arguments.

Evidence in `evidence/P2-LAYOUT-STRUCTURE/`: four `inventory_*.json`,
four `verify_*.txt`, and `check_bflyt_inspect.txt`.

Derived data was written only to this task's scratch folder. No new
game-derived files were produced, so
`gamedata/mii_customizer/P2-LAYOUT-STRUCTURE/` was created per the prompt's
path assignment but is intentionally empty.

## 7. Limitations

- **Unverified**: that the game, emulator or console accepts any modified
  `.bflyt` or repacked `layout.arc`. Nothing was run on hardware or in an
  emulator. Compilation and parsing establish nothing about runtime behaviour.
- **Unverified**: the four open questions in section 4, especially the legality
  of `set_item_06` and the animation requirement.
- The `prt1` tail is decoded only as far as the offset of its owner name and
  embedded block tags. Its internal field meanings are not established.
- The `prt1` tail after the child records is reported by offset and name only.
  Its internal structure is not decoded.
- `usd1`, `mat1`, `txl1`, `cnt1` and `lyt1` payloads are not decoded.
- Whether a group member should be read as an index rather than a name is open.
- The cross-check's "unresolved" path is untested against a genuinely unresolved
  reference, because none remain in these four files.
- No primary format source was consulted or pinned. Everything above was
  derived from these files alone, so field *meanings* stay inferences even
  though the *offsets and counts* are measurements.

## Changed files

Exclusive paths only:

- `mods/mii_customizer/tools/bflyt-inspect/bflyt_inspect.py`
- `mods/mii_customizer/tools/bflyt-inspect/check_bflyt_inspect.py`
- `mods/mii_customizer/tools/bflyt-inspect/README.md`
- `mods/mii_customizer/research/P2-LAYOUT-STRUCTURE.md` (this report)
- `mods/mii_customizer/evidence/P2-LAYOUT-STRUCTURE/` (4 inventories, 4 verify logs, 1 check log)
- `mods/mii_customizer/scratch/2026-10-04_P2-LAYOUT-STRUCTURE/` (15 probe scripts)
- `gamedata/mii_customizer/P2-LAYOUT-STRUCTURE/` (created per assignment, intentionally empty)

Not touched: the P1-LAYOUT inputs (re-hashed unchanged), any Lua, any identity
work, shared `tools/`, `STATUS.md`, git.

## Summary

**P2-LAYOUT-STRUCTURE: DONE.**

Established (tier B): the inclusive block-size framing; the `grp1` 36+24n layout
and `prt1` 78-byte header with 40-byte child records; `selector_0` as 8 members
in `edit` and 7 in `special`; the six and four row parts with exact offsets,
positions and extents; the owner child layouts each row references; and that all
61 group members resolve in-file with no corruption.

Clarified: section framing is inclusive, agreeing with the earlier coordinator traversal;
and a marker-field bug in my own tool that had produced four false "unresolved"
reports.

The mod question is answered: adding a row requires a new `prt1`, a `selector_0`
count and 24-byte entry, a `file_size` fix and a re-layout of all later block
offsets, plus four open questions this task did not settle - notably
whether `set_item_06` is legal and whether new animations are required. Neither
is claimed either way.