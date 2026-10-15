# bflyt-inspect

Read-only inspector for **BFLYT** UI layout files (`.bflyt`) as they exist in the
Mii editor `layout.arc` archives. It parses the container, blocks, groups
(`grp1`) and parts (`prt1`), and prints them as a machine-readable inventory
with byte offsets.

It exists to describe the editor rows and selector groups that are already in
the game, so that any later attempt to add a row knows exactly which counts and
references exist. It **never writes** a `.bflyt` and never rebuilds an archive.

**Reading this tool's output does not establish that the game would load a
modified file.** Nothing here has been run on hardware or in an emulator.

## Status

Working and self-checking. `verify` exits 0 on all four files measured in
P2-LAYOUT-STRUCTURE; `check_bflyt_inspect.py` reports 71 passing checks, exit 0.

No dependencies beyond the Python 3 standard library. Nothing is installed.

## Usage

Paths are relative to the workspace root.

```bash
T=mods/mii_customizer/tools/bflyt-inspect/bflyt_inspect.py
B=gamedata/mii_customizer/P1-LAYOUT/unpacked
E=$B/make_mii_edit/blyt/make_mii_edit.bflyt
S=$B/make_mii_special/blyt/make_mii_special.bflyt

python3 $T header    $E                 # header fields and exact-walk result
python3 $T blocks    $E                 # every block: tag, offset, size
python3 $T groups    $E                 # grp1 names, counts, member offsets
python3 $T parts     $E set_item        # prt1 nodes with children and tail names
python3 $T rows      $E set_item        # just the row parts
python3 $T crosscheck $E                # resolve every group member in-file
python3 $T inventory $E --out /tmp/e.json   # machine-readable JSON
python3 $T verify    $E $S              # structural checks, exit 0 only if clean

python3 mods/mii_customizer/tools/bflyt-inspect/check_bflyt_inspect.py
```

`--edit PATH` and `--special PATH` let the smoke check run against other
extracted layouts.

`header`, `blocks`, `groups`, `crosscheck` and `verify` accept **one or more
files** and report on each. For `verify`, a failure in **any** file makes the
exit status nonzero, and a parse error in any file is reported rather than
skipped. `parts`, `rows` and `inventory` take exactly one file.

> An earlier version of the argument handling read only the first file and
> discarded the rest, so `verify good.bflyt corrupt.bflyt` exited 0 - a false
> pass that would hide a corrupt input. Fixing that then broke
> `rows FILE PREFIX`, which printed nothing and still exited 0. The smoke check
> now exercises every command through the real CLI and asserts on both exit
> status and output, so neither failure mode can return silently.

## Measured format

Everything below is tier **B**: measured offline on the extracted files named in
`research/P2-LAYOUT-STRUCTURE.md`. Fields whose meaning was not established are
labelled as such in both this file and the tool's output.

### Header

| offset | size | field | note |
|---|---|---|---|
| +0x00 | 4 | `"FLYT"` | magic |
| +0x04 | 2 | `ff fe` | byte-order mark |
| +0x06 | 2 | `u16` header_size | 0x14 in every file measured |
| +0x08 | 4 | word | **unverified**; not the block count |
| +0x0C | 4 | `u32` file_size | equals the real file size in both owners |
| +0x10 | 2 | `u16` block_count | 58 (edit), 43 (special) |

All multi-byte header fields are little-endian.

### Block framing

A block is a 4-byte ASCII tag followed by a little-endian `u32` size at +4.

**The size covers the tag and the size field themselves.** The next block begins
at `offset + size`, *not* `offset + 8 + size`. Walking `block_count` blocks from
`header_size` lands exactly on end-of-file for all four files measured, with no
gap and no overlap.

> This makes the inclusive framing explicit. The coordinator's earlier check
> already advanced by offset+size and remains correct. An exclusive-size draft
> of this worker's inspector failed and was corrected before delivery.

### Groups (`grp1`)

36-byte preamble, then `count` fixed-size name slots:

| payload offset | size | field |
|---|---|---|
| +0 | 32 | group name, NUL-padded |
| +32 | 2 | (value 0 in every group measured; **meaning unverified**) |
| +34 | 2 | `u16` entry count |
| +36 | 24 each | NUL-padded member name |

`36 + count * 24` equals every `grp1` payload length exactly, in all four files.

### Parts (`prt1`)

| payload offset | size | field |
|---|---|---|
| +0 | 2 | `u16` node type; 3 on every part measured |
| +2 | 2 | `u16` marker; **not a constant** (see below) |
| +4 | 32 | node name, NUL-padded |
| +36 | 8 | `f32` x, `f32` y |
| +60 | 8 | `f32` scaleX, scaleY |
| +68 | 8 | `f32` width, height |
| +76 | 2 | `u16` child record count |
| +78 | 40 each | child record, inline name at record+10 |

After the child records come a padding gap, an owner layout name, and further
embedded blocks. The tool reports that region as a list of names with absolute
offsets and **does not claim to have decoded it**.

### The marker field is not a constant

The `u16` at payload+2 of a name-bearing block takes at least these values
across the four files measured, and **every** block carrying one of them has a
valid name:

`0x0000`, `0x00ff`, `0x0200`, `0x02ff`, `0x06ff`

Name detection therefore uses only the name itself. Two earlier drafts of this
tool gated it on a guessed marker and produced **false "unresolved group member"
reports** by skipping real nodes (`nul_keyhelp`, `maker`, `favorite`,
`notice_unedit`, `set_txt_name_00`..`03`). The smoke check now asserts that every
node block yields a name, so that regression cannot return silently.

### Empty marker blocks

`pas1`, `pae1`, `grs1` and `gre1` are all size 8 (header only, no payload) in
every file measured. This is reported as a measurement. It is **not** a claim
about what the loader does with them.

## What `crosscheck` does

For every `grp1` member name, it looks for a node of that name defined in the
same file (`prt1`, `pan1`, `bnd1`, `txt1`, `wnd1`, `pic1`) and reports the
defining block offsets.

Current result: **61 of 61 group members resolve** across the four files
(16 in `make_mii_edit`, 10 in `make_mii_special`, 20 in
`make_mii_btn0_01_item`, 15 in `make_mii_btn0_02_special`).

An unresolved member would be reported as unresolved. It would **not** be called
corruption: a member may legitimately name a node defined in a child layout
archive. No unresolved references remain in these four files, so that path is
untested against a real unresolved case.

## Files

| file | role |
|---|---|
| `bflyt_inspect.py` | the inspector; importable (`load`, `crosscheck_groups`, `row_parts`) |
| `check_bflyt_inspect.py` | smoke check; 71 checks, exit 0 only if all pass |

The smoke check also asserts the tool stays read-only, by rejecting bad magic,
truncated files and out-of-range block sizes, and by checking the source
contains no write calls. It exercises every command through the real CLI and
asserts on both exit status and output, so a command that silently ignores an
argument fails the check rather than passing quietly.

## Limitations

- **Unverified**: that the game accepts any modified `.bflyt`. Nothing here was
  loaded by the game, the emulator or the console.
- **Unverified**: the meaning of the header word at +0x08, the `grp1` preamble
  bytes at +32, the `prt1` marker at +2, and the whole `prt1` tail after the
  child records.
- **Unverified**: whether `set_item_06` is a legal next row index, and whether a
  new node needs a matching animation. Absence of row-name strings in the
  animation members does **not** settle that (see P1-LAYOUT).
- The tool models four block types with inline names. Blocks that carry names in
  some other way (`usd1`, `mat1`, `txl1`, `cnt1`, `lyt1`) are listed in the block
  walk but their payloads are not decoded.
- Group entries are name slots. Whether a group member is meant to be read as an
  index into another table is not established.

See `research/P2-LAYOUT-STRUCTURE.md` for hashes, commands and the full
row/selector comparison.