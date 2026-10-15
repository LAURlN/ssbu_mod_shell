# P1-LAYOUT - inspect and rebuild path for the Mii editor layout archives

Task: `prompts/P1-LAYOUT.md`. Date: 2026-10-04. Worker: Space Bunny Alpha.
Tier: **B** (offline measurement on the local extracted files). No console or emulator run.

Scope respected: no Lua edits, no identity work, no production menu code, no shared tools, no
commits, no SD access, no downloads or installs. Originals under `gamedata/mii_customizer/P1-UI/`
were only read.

## Inputs (exact relative paths, sha256)

| file | bytes | sha256 |
|---|---|---|
| `gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc` | 927100 | `f4bf2ef0db472eb341d76c70f3ec770ae58598fff3f53d2aced7170fb4ebf212` |
| `gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc` | 723436 | `5ba29f4448686d89d478b17b1d5028dda2374c3e1b66cc3ac7c0f7a6abaad945` |

Both were verified unchanged after this task (identical hashes at the end of the run).

## 1. Container: it is SARC, not BFLYT and not `data.arc`

The prompt warned against assuming SARC or BFLYT. Measured result: the **outer** container *is* a
Nintendo SARC; the BFLYT/BNTX format appears only one level down, inside members. Two distinct
formats are stacked, which is the main confusion risk for the next task.

```
0x00  "SARC"
0x04  u16 header_size = 0x0014            (little endian)
0x06  u16 byte_order   = 0xFFFE            (bytes ff fe -> BE 0xFFFE, "little" per jam1garner/sarc)
0x08  u32 file_size                       (== total archive size in both files)
0x0C  u32 data_offset = 0x00002000        (member data starts here, 8 KiB aligned)
0x10  u32 0x00000100                      (constant in both files; not decoded, see limits)
0x14  "SFAT"
0x18  u16 sfat_header_size = 0x000C
0x1A  u16 member_count                    (111 edit / 76 special)
0x1C  u32 hash_key = 0x00000065
0x20  member_count * 16-byte entries
...   "SFNT" + u32 8 + NUL-terminated names, each padded to 4 bytes
0x2000 member payloads, contiguous, in SFAT order
```

Endiansness is mixed exactly as `jam1garner/sarc` describes: the header word at 0x06 is read
big-endian, everything else is little-endian. **Verified** by re-reading both archives with that
rule and getting consistent sizes and offsets.

### SFAT entry (16 bytes, little endian)

| offset | field | meaning (verified) |
|---|---|---|
| +0x00 | u32 | name hash, `h = h * 0x65 + c` per character |
| +0x04 | u32 | `0x01000000 | (name_table_offset / 4)`; bit 0x01000000 = "has name" |
| +0x08 | u32 | member data start, relative to 0x2000 |
| +0x0C | u32 | member data end, relative to 0x2000 |

Verified claims, all measured:

- **Hash algorithm**: `field0 == sfat_hash(name)` for **111/111** and **76/76** members. This is the
  algorithm in `jam1garner/sarc` (`KEY = 0x65`). I first ruled out CRC32 of the name, CRC32 of the
  data, FNV-1/1a (32 and 64), murmur3-32, djb2, sdbm, and ten CRC-32 polynomial variants
  (BZIP2/MPEG-2/POSIX/JAMCRC/XFER/CRC-32C/CRC-32D/Koopman/AUTOSAR/CDROM, and zlib) - none matched,
  and none matched on the member payload either. Dead end recorded in
  `scratch/2026-10-04_P1-LAYOUT/probe_field0.py`.
- **Name table**: names are NUL-terminated ASCII padded to 4 bytes; `name_table_offset / 4` indexes
  them, so the stored value is always a multiple of 4 and the padding must stay 4-byte granular.
  Reconstructing the offsets from the raw table matched all 111 and all 76 entries.
- **Table ordering**: SFAT entries are strictly ascending by name hash in both archives, and the
  member data section follows that same order. A repacker must sort by the hash, not by name.
- **Header 0x10**: constant `0x100` in both files. The `sarc` crate writer emits the equivalent
  padding as `u16 0x0100` + 2 pad bytes, so this slot reproduces; its runtime meaning is still
  **unverified** and should be preserved verbatim rather than recomputed.

### Padding rule (the part that blocks an unmodified rebuild)

`data_offset` is 8 KiB aligned in both files, but the per-member alignment is **not** uniform:

- All 111 / 76 member starts are 16-byte aligned (0 violations in both).
- Inter-member gaps observed: 0, 4, 8, 12 bytes between ordinary members, plus large jumps for the
  two big resource members.
- `bgsh/__ArchiveShader.bnsh` starts at 0x6000 (edit) and 0x3000 (special); `timg/__Combined.bntx`
  starts at 0x1B000 (edit) and 0x18000 (special). Those are 0x2000 / 0x1000 / 0x8000 granular.
- A rule of "0x10 for everything" reproduces neither archive. A two-tier rule (0x10 for members
  under 0x4000, 0x1000 for larger) reproduces `make_mii_special` exactly but not `make_mii_edit`.
  `scratch/2026-10-04_P1-LAYOUT/derive_padding_rule.py` lists, per member, the minimum power-of-two
  alignment each start actually requires; there is no consistent single rule across both files.

Consequence: a generic SARC writer cannot reproduce these two archives byte-for-byte, and there is
no evidence the game requires it. Byte equality is a nice control, not a requirement.

## 2. Which members own `set_item_00..05` / `set_special_item_00..03`

Answer, with exact member paths:

| archive | member | sha256 | occurrences |
|---|---|---|---|
| `make_mii_edit` | `blyt/make_mii_edit.bflyt` | `2668a7ecf146a31e5003df682208d21d3a4cd2d032d4d68e839dfe0853b6dd34` | `set_item_00..05` twice each (12 total) |
| `make_mii_special` | `blyt/make_mii_special.bflyt` | `a63cbacc09a9264ff07ac83c1b765dd0caeeaa1afd92bdb58297f774a3c0b3e8` | `set_special_item_00..03` twice each (8 total) |

**No other member of either archive contains these strings.** I scanned all 111 and all 76 extracted
members (`evidence/P1-LAYOUT/set_item_ownership.json`). Specifically:

- The animations (`anim/*.bflan`, 98 in edit / 66 in special) contain **none** of them. They carry
  visual state names such as `make_mii_btn0_01_item_BlinkOn.bflan` and
  `make_mii_btn0_01_item_category_00..05.bflan`, not `set_item_NN`. Whether adding a field requires another animation is
  **unverified**; lack of row-name strings does not settle animation dependencies.
- `info/layout.info` does **not** contain them either. It is a NUL-separated list of the archive's
  own entry names: `make_mii_edit.bflyt`, `in`, `out`, `maker_off`, `maker_on`, `favorite_off`,
  `favorite_on`, `unedit_off`, `unedit_on`, then the common animation stems.
  (`make_mii_special`'s is the same shape with `category_00..03`.)
  **Unverified** whether the loader requires a new name here; it must be checked before adding a
  member.
- The other `.bflyt` files (`make_mii_btn0_01_item.bflyt`, `make_mii_btn0_02_special.bflyt`,
  `make_mii_btn2_00_try.bflyt`, `com_*`) do not contain them.

### Structural evidence inside the owning BFLYT (not ASCII presence alone)

Both owning files have the same shape. Measured header bytes for `make_mii_edit.bflyt`:

```
0x00  "FLYT"
0x04  BOM bytes ff fe          (BE u16 = 0xFFFE; note SARC carries its BOM at 0x06 instead)
0x06  u16 LE = 0x0014
0x08  bytes 00 00 00 09        (not block count; version interpretation unverified)
0x0C  u32 LE = file_size       (21004 for make_mii_edit, 10408 for make_mii_special)
0x10  u16 LE = 58 / 43        (section count, verified by coordinator traversal)
```

`set_item_NN` occurs in **two structurally distinct places** in `make_mii_edit.bflyt`:

1. **Node records** (offsets 5148, 6324, 7468, 8628, 9380, 13632). Each occurrence is preceded by a
   parent-pointer record header and a `prt1` tag, e.g. at 0x1410: `70 72 74 31` = `"prt1"`,
   `98 04 00 00`, `03 00`, `ff 00`, then the name. The six records are interleaved with their
   neighbouring node names: `..._nam_01` before `set_item_01`, `..._tup_hat_01` before
   `set_item_02`, `...outfit_01` before `set_item_03`, `...tup_color` before `set_item_04`,
   `...sp_move_04` before `set_item_05`. These are the six editor rows the Lua `set_item_%02d` loop
   drives (P1-UI-DECODE).
2. **A selection-set / text table** (offsets 20508..20628). These six sit at a strict 24-byte
   stride (20508, 20532, 20556, 20580, 20604, 20628), each followed by NUL padding out to the
   stride. The table is preceded by `grp1` + `ec 00 00 00` and the name `selector_0` at 0x4FF8.
   `make_mii_special.bflyt` shows the identical pattern: `grp1` + `04 00 00 00` + `selector_0` at
   0x2798, then `set_special_item_00..03` at 10140, 10164, 10188, 10212 (again 24-byte stride).

So the hierarchy claim has real support: there is a `selector_0` group holding an ordered,
fixed-stride list, and separately the per-row node records. What is **not** established is that
`set_item_06` would be the next free slot, that the 24-byte stride is a count-bearing struct rather
than a name+padding array, or how the loader binds Lua indices to these nodes. Those remain tier D.

Coordinator correction (verified offline B, 2026-10-04): these files have sequential
sections beginning at header size 0x14, each with tag +0 and LE u32 size +4.
Walking the 58/43 sections consumes exactly 21004/10408 bytes. The earlier search
for a separate tag table was a dead end; section +8 of the file is not block count.
Group/part payload decoding is still needed; P2-LAYOUT-STRUCTURE now owns it.

## 3. Round trip

Three measurements, all in `evidence/P1-LAYOUT/`.

### (a) Member-level unmodified round trip - byte-exact

`scratch/2026-10-04_P1-LAYOUT/roundtrip_members.py`. Rebuilt the data section from the extracted
members at their original offsets with the original gap padding, then reassembled the container:

| archive | data section sha256 | rebuilt data sha256 | data equal | container equal |
|---|---|---|---|---|
| `make_mii_edit` | `2abbd359bd940b65a67144fa6d032fb545f48bc4f43647a9b92554f37e7a1774` | same | **True** | **True** |
| `make_mii_special` | `06c6287152823f041cb9b639294159b7d4e9389488151e3d1cca8af7759c0367` | same | **True** | **True** |

Container byte equality holds. This reconstructs the unchanged payload and copies the original metadata. It does
not test modified data or establish that container/runtime checksums are absent.

### (b) 4-byte sequential repack - membership and hashes preserved, bytes differ

`scratch/2026-10-04_P1-LAYOUT/repack_4byte.py` -> `gamedata/mii_customizer/P1-LAYOUT/repacked/`.

| archive | original size / sha256 | repacked size / sha256 | byte equal | membership | member hashes |
|---|---|---|---|---|---|
| `make_mii_edit` | 927100 / `f4bf2ef0...` | 921812 / `9dce536ee3a4f205ffe857493ea74d439691a0f25bbd295faf79dea2f8dc7eff` | False | equal, 111 | **equal, 111/111** |
| `make_mii_special` | 723436 / `5ba29f44...` | 716700 / `03d528aa9c69662cca6210ef94c54b58a310b36c11bcc371773701e4a3a6b728` | False | equal, 76 | **equal, 76/76** |

Difference explained: 5288 and 6736 bytes respectively, which is the difference in inter-member
padding, not data loss. Every member payload re-extracts to the same sha256. So a 4-byte-aligned
repack is **content-preserving but not byte-identical**, and byte equality should not be used as the
acceptance criterion for the mod.

### (c) `jam1garner/sarc` writer simulation - cannot reproduce these archives

`scratch/2026-10-04_P1-LAYOUT/simulate_sarc_writer.py`, reproducing that crate's `src/writer.rs`
byte layout (measured, not run):

| archive | member align | simulated size | byte equal | members preserved |
|---|---|---|---|---|
| `make_mii_edit` | 0x2000 (crate default) | 1737580 | False | yes |
| `make_mii_edit` | 0x4 | 921812 | False | yes |
| `make_mii_special` | 0x2000 | 1278220 | False | yes |
| `make_mii_special` | 0x4 | 716700 | False | yes |

The crate's 0x2000 per-member alignment nearly doubles the archive size (1.74 MB vs 0.93 MB), which
also matters if these archives ever need to fit a mod payload budget. It is a correct SARC writer,
just not a faithful one for these two files.

## 4. Tooling status

**No workspace tool can write SARC.** Checked before writing anything:

- `tools/REGISTRY.md` (read first, as instructed): only `data-arc-extract`, `arc-extract`,
  `freebuff-dispatch`.
- `tools/arc-extract` uses `smash-arc = 0.6.0`, which is `data.arc`-only: its `ArcFile` requires
  magic `0xABCDEF9876543210` and it is read-only. Pointed at a `layout.arc` it does not apply.
- The vendored crate source at `~/.cargo/registry/src/*/smash-arc-0.6.0/` contains no SARC code
  (grep for `SARC`/`sarc` in `src/*.rs`: no hits).
- `tools/` has no ARC writer. The mod's own `tools/` holds only `lua53-inspect`.

Per the prompt's step 4 I inspected two primary sources and stopped there. No download, build or
install was performed.

### Pinned candidate: `sarc` crate 1.2.0

- Crate: `sarc`, version **1.2.0**, crates.io, MIT.
- Repository: <https://github.com/jam1garner/sarc> (primary source, read at `master` on 2026-10-04).
- Documentation: <https://docs.rs/sarc>.
- Authors field on crates.io: `jam1garner`. Same author as `smash-arc`, which this workspace already
  vendors at `=0.6.0`, so the local Rust toolchain situation is known-good: `rust-toolchain.toml`
  pins `stable-x86_64-pc-windows-gnu` because this machine has no MSVC linker
  (see `tools/arc-extract/README.md`).
- Format support confirmed by reading `src/lib.rs`, `src/parser.rs`, `src/writer.rs`:
  - reads and writes SARC and Yaz0/Zstd-compressed SARC;
  - implements exactly the hash, entry layout, name-table 4-byte padding and
    `hash-sorted SFAT` rules this archive uses - this is why the crate was identifiable from the
    constant `0x65` and the `0x01000000` attribute bit;
  - `SarcFile { byte_order, files }` with `SarcEntry { name, data }` is a sufficient API for
    extract-modify-repack.
- Local dependency requirements: a normal `cargo` project inside `tools/` (no Python, no uv, no
  network at run time). Runtime deps are `nom` and `binwrite`; `yaz0`/`zstd` are behind optional
  features that are **not** needed here because the game archives are uncompressed SARC.
- **Known gap, measured**: its writer hardcodes 0x2000 per-member alignment, so it will not
  reproduce these archives byte-for-byte (section 3c). Runtime acceptance of its changed alignment is unverified even if member hashes match; if a smaller
  output matters, the alignment constant needs a one-line local change, which would be a fork, not
  an upstream-supported configuration.

### Alternative considered and rejected

`sarc-rs` 1.0.0 (crates.io, <https://github.com/NiceneNerd/sarc-rs>) is advertised as "parsing and
creating Nintendo SARC files". I did not inspect its source beyond the listing, so its handling of
the Smash-specific `0x01000000` name-attribute bit, the `0x65` hash and 4-byte name padding is
**unverified**. Do not choose it over `sarc` 1.2.0 without reading its writer first.

## 5. Answer to the task's question

How the layout archive can be inspected and rebuilt without corrupting its container:

1. Parse with the documented SARC layout. Use `sarc` 1.2.0 for read and write.
2. To add an editor field: replace `blyt/make_mii_edit.bflyt` with a modified copy and repack.
   Member hashes and membership are offline checks; runtime acceptance of changed alignment remains unverified.
3. Name the new member to match the loader's expectation - **unknown**, and this is the open
   question. A `set_item_06` hypothesis is tier D.
4. Update `info/layout.info` - **unknown** whether required. Same tier D.
5. Animation requirements for new rows are unverified; missing row-name strings are insufficient.
6. Do not rely on the SFNT `0x100` header field being recomputable - copy it.
7. Validate with member-hash and membership comparison against the original manifest
   (`evidence/P1-LAYOUT/manifest.json`), not container byte equality.

## Concrete minimal next layout task (coordinator revised)

See `prompts/P2-LAYOUT-STRUCTURE.md`: read-only group/part payload inspection;
sequential section traversal is already established. Archive tooling is separately
assigned in `prompts/P2-SARC-WRITE.md`, using same-length replacements and original
metadata/offsets. No crate installation or user approval is required for that scoped
mod-local tool. General growing/repacked archive runtime support remains unverified.

## Limitations and unresolved questions

- **Unverified**: that the game accepts a repacked `layout.arc` at all. Nothing here was loaded by
  the game, the emulator or the console. Byte equality was never claimed as required.
- **Unverified**: meaning of the SARC header word at 0x10 (`0x100`).
- **Unverified**: the exact per-member padding rule. No single rule reproduces both archives; the
  measured minimum alignments are recorded in the scratch script for the next worker.
- **Verified B**: sequential BFLYT section boundaries; **unresolved**: selector/part payload semantics.
- **Unresolved**: whether `set_item_06` is a legal next index, and whether `layout.info` must list a
  new name.
- `sarc-rs` not inspected beyond its listing.
- Tier note: everything here is **B**. No runtime behaviour of any kind was measured.

## Changed files

Exclusive writes only, all inside this mod's assigned paths:

- `mods/mii_customizer/research/P1-LAYOUT.md` (this report)
- `mods/mii_customizer/evidence/P1-LAYOUT/checks.json`
- `mods/mii_customizer/evidence/P1-LAYOUT/manifest.json`
- `mods/mii_customizer/evidence/P1-LAYOUT/roundtrip.json`
- `mods/mii_customizer/evidence/P1-LAYOUT/repack_4byte.json`
- `mods/mii_customizer/evidence/P1-LAYOUT/sarc_writer_simulation.json`
- `mods/mii_customizer/evidence/P1-LAYOUT/set_item_ownership.json`
- `mods/mii_customizer/scratch/2026-10-04_P1-LAYOUT/` (probe, parse, round-trip and evidence scripts)
- `gamedata/mii_customizer/P1-LAYOUT/` (task-owned unpacked members, manifests, repacked output)

Not touched: `gamedata/mii_customizer/P1-UI/` (inputs, hashes re-verified unchanged), any Lua, any
identity work, shared tools, `STATUS.md`, git.

## Summary

**P1-LAYOUT: DONE** (reviewed; corrected section traversal and unsupported inferences).

Established: both archives are SARC (little endian, `0xFFFE`), fully parsed and enumerated;
`set_item_00..05` live in `blyt/make_mii_edit.bflyt` and `set_special_item_00..03` in
`blyt/make_mii_special.bflyt`, and nowhere else; an unmodified round trip is **byte-exact**; a
4-byte repack preserves all 111 and all 76 member hashes and membership but not container bytes.
Coordinator chose a smaller mod-local stdlib replacement tool instead of adding a crate;
see P2-SARC-WRITE. General repack acceptance remains unverified.
Next: group/part inspection and conservative member tooling under the two P2 prompts.
