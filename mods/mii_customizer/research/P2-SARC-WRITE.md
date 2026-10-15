# P2-SARC-WRITE - conservative archive member replacement

Task: `prompts/P2-SARC-WRITE.md`. Date: 2026-10-04. Worker: Space Bunny Alpha.
Tier: **B** (offline measurement on local extracted files). No console, no
emulator, no runtime anything.

Scope respected: no BFLYT decoding or editing, no Lua, no native RE, no install
package, no Rust/crate work, no commits, no SD access, no subagents. The
originals under `gamedata/mii_customizer/P1-UI/` were only read and their
hashes re-verified unchanged at the end. No other worker's files were touched;
`STATUS.md`, `CHANGELOG.md` and `CURRENT_INSTALL.md` are the coordinator's.

## Goal, as delivered

One bounded stdlib tool, `tools/sarc-layout/`, that can list an archive,
extract a named member, re-serialise an archive unchanged, and replace exactly
one existing member with a same-length payload — preserving metadata, ordering,
original offsets, gap bytes and every other member verbatim. No external crate
was installed and none is needed.

## Inputs (exact relative paths, sha256)

| file | bytes | sha256 | changed by this task |
|---|---|---|---|
| `gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc` | 927100 | `f4bf2ef0db472eb341d76c70f3ec770ae58598fff3f53d2aced7170fb4ebf212` | no (re-verified after the run) |
| `gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_special/make_mii_special/layout.arc` | 723436 | `5ba29f4448686d89d478b17b1d5028dda2374c3e1b66cc3ac7c0f7a6abaad945` | no (re-verified after the run) |

Both match P1-LAYOUT's recorded hashes, so that report's inputs are the ones
this task read.

## 1. What was promoted from P1-LAYOUT, and what was corrected

P1-LAYOUT's scratch scripts were read, not reimplemented blind:
`scratch/2026-10-04_P1-LAYOUT/inspect_sarc.py` (parse and manifest),
`roundtrip_members.py` (member-level round trip) and `repack_4byte.py`
(hash-sorted repack). The promoted facts are the ones P1-LAYOUT measured and
this task re-confirmed independently: the header layout, the `0xFFFE` BOM read
big-endian while everything else is little-endian, the `h = h*0x65 + c` name
hash, the 16-byte SFAT entry, `0x01000000 | name_offset/4`, NUL-terminated
names padded to 4 bytes, and hash-sorted SFAT ordering.

One design difference from the P1-LAYOUT round trip, which matters for how
much the control is worth:

- **P1-LAYOUT's round trip built the new archive as `bytearray(d)`** and
  overwrote the data section in place. The header, SFAT and name table were
  carried over as raw bytes, so it could not have detected a wrong
  understanding of those fields.
- **`sarc-layout` rebuilds the whole container from parsed metadata**: magic,
  header fields, SFAT tag and header, every entry, the SFNT header, the name
  table and the data section are each re-emitted from the parsed values. The
  only bytes replayed rather than re-emitted are the ones the tool cannot
  derive — inter-member gaps and the padding between the last name and
  `data_offset`. So byte-exactness here is a real test of the parser's
  understanding, not an artefact of copying the input.

Both real archives rebuild byte-identically through this stricter path.

## 2. Unchanged control: byte-exact reconstruction

Command (from the workspace root):

```bash
python mods/mii_customizer/tools/sarc-layout/sarc_layout.py rebuild <ARC> -o out.arc
```

`rebuild` refuses to write its `-o` output at all unless the result is
byte-identical, so the control cannot pass quietly.

| archive | input sha256 | rebuilt sha256 | byte identical | members |
|---|---|---|---|---|
| `make_mii_edit` | `f4bf2ef0db472eb341d76c70f3ec770ae58598fff3f53d2aced7170fb4ebf212` | same | **true** | 111 |
| `make_mii_special` | `5ba29f4448686d89d478b17b1d5028dda2374c3e1b66cc3ac7c0f7a6abaad945` | same | **true** | 76 |

Evidence: `evidence/P2-SARC-WRITE/rebuild_make_mii_edit.json`,
`rebuild_make_mii_special.json`.

This also confirms, independently of P1-LAYOUT, that the header word at `0x10`
(`0x100` in both files) survives a re-emit untouched, and that the name table's
4-byte padding rule is reproduced by replaying it rather than deriving it.

## 3. Mutation: one same-length replacement on a synthetic archive

Per the prompt, the mutation uses a **synthetic** archive, not a guessed game
change. It is built by `scratch/2026-10-04_P2-SARC-WRITE/build_synthetic.py`,
written independently of the tool so that an encoder bug cannot hide by
validating the tool against its own output. It has 5 members, non-zero `0xA5`
filler in every gap, and non-uniform inter-member padding (16/4/12/8).

`dir/beta.bin` (512 bytes) was replaced by a different 512-byte payload:

| property | result |
|---|---|
| archive size before / after | 2233 / 2233 bytes |
| members changed | **exactly `dir/beta.bin`** (independent reparse of both files) |
| other members' sha256 | 4/4 unchanged |
| membership, member order, data offsets | unchanged |
| header metadata (incl. `0x10`, size, data_offset) | unchanged |
| SFAT name-offset fields | unchanged |
| name table (80 bytes) | unchanged |
| gap spans and gap bytes | unchanged |
| differing bytes confined to the target range | **yes** — 509 differing bytes, all inside `[1721, 2233)` |
| mutated file rebuilds byte-identically | yes |

A second, different replacement on the already-mutated file again changed only
`dir/beta.bin`, so the behaviour is repeatable rather than a one-off.

Evidence: `evidence/P2-SARC-WRITE/mutation_synthetic.json`.

### Same path at real scale, without inventing content

A **no-op** `replace` — feeding each archive's own member bytes back as the
payload — reproduces both originals exactly:

| archive | output sha256 | equals input | changed members |
|---|---|---|---|
| `make_mii_edit` | `f4bf2ef0db472eb341d76c70f3ec770ae58598fff3f53d2aced7170fb4ebf212` | yes | 0 |
| `make_mii_special` | `5ba29f4448686d89d478b17b1d5028dda2374c3e1b66cc3ac7c0f7a6abaad945` | yes | 0 |

This exercises the whole replace path on 111 members / 927 kB while changing no
game content, so it is a control rather than a claim about a patch.

## 4. Manifest comparison with the previous worker

Compared field by field against `evidence/P1-LAYOUT/manifest.json`:

| check | `make_mii_edit` | `make_mii_special` |
|---|---|---|
| header fields agree (size, data_offset, `0x10`, count, name-table offset) | yes | yes |
| membership identical | 111/111 | 76/76 |
| every member sha256 identical | 111/111 | 76/76 |
| every member offset identical | 111/111 | 76/76 |
| end-to-end extract matches the prior hash (`blyt/make_mii_edit.bflyt`, `blyt/make_mii_special.bflyt`) | yes | yes |

Two independent tools now agree on every member of both archives. Evidence:
`evidence/P2-SARC-WRITE/manifest_make_mii_edit.json`,
`manifest_make_mii_special.json`.

## 5. Refusals exercised

Every case below exits non-zero with a message naming the reason and writes no
output file.

| case | command | observed refusal |
|---|---|---|
| payload too long | `replace ... --payload payload_grow.bin` (513 vs 512) | `payload is 513 bytes, member is 512 bytes ... same-length replacement only` |
| payload too short | `replace ... --payload payload_shrink.bin` (511 vs 512) | as above, 511 |
| missing member | `replace ... no/such/member.bin` | `no member named ... this tool only replaces existing members` |
| traversal name (argument) | `extract ... ../../etc/passwd` | `contains a '..' path component` |
| traversal name (argument) | `extract ... /absolute/name.bin` | `is an absolute path` |
| traversal name (argument) | `replace ... ../escape.bin` | `contains a '..' path component` |
| traversal name **stored in the archive** | `list traversal_name.arc` | `member name '../../../ab' contains a '..' path component` |
| malformed range, out of bounds | `list out_of_bounds.arc` | `member 4 ... ends at 0x18b9, past the 1721-byte data section` |
| malformed range, overlapping | `list overlap.arc` | `members 'dir/gamma.bin' and 'zeta.bin' overlap` |
| duplicate names | `list duplicate_names.arc` | `duplicate member name 'dir/gamma.bin' (indices 0 and 1)` |
| unsupported compression | `list compressed_yaz0.arc` | `is a Yaz0 compressed SARC; only uncompressed SARC is supported` |
| unsupported BOM | `list big_endian.arc` | `is big-endian (BOM 0xfffe); only little-endian SARC is supported` |
| truncated / size mismatch | `list truncated.arc` | `header size field is 2249 but the file is 2233 bytes` |
| would overwrite the input | `replace ... -o synthetic.arc` | `output would overwrite the input` |
| write outside the workspace | `replace ... -o %TEMP%/...` | `refusing to write outside the workspace` |

New members are refused by omission: the tool has no command that adds one.

A damaged name hash is **not** a refusal — it is a legitimate container whose
metadata disagrees with its names — so it is reported as a failed check
(`names-hash-matches`) with exit 1 and no traceback, rather than crashing.

Three of these fixtures initially passed for the **wrong reason** and were
repaired rather than left alone: the duplicate-name patch was a no-op that
wrote a field back to itself; the traversal patch overwrote the wrong name slot
and changed the file length, so the refusal fired on a size mismatch instead of
on the `..` component; and the big-endian fixture wrote `ff fe` (the
little-endian marker) instead of `fe ff`. The harness now asserts the fixtures
are what they claim to be.

## 6. Checks run, with exit status

```bash
# from the workspace root
python mods/mii_customizer/scratch/2026-10-04_P2-SARC-WRITE/build_synthetic.py
python mods/mii_customizer/tools/sarc-layout/check_sarc_layout.py   # 87 checks, 87 passed, exit 0
python mods/mii_customizer/tools/sarc-layout/sarc_layout.py verify <both archives>   # exit 0 each
```

`check_sarc_layout.py` also invokes the tool through its CLI as a subprocess
and asserts on the **exit code** for every case, so a refusal that accidentally
exited 0 would fail the run. Results in
`evidence/P2-SARC-WRITE/checks.json`.

Environment note: `python3` on this machine is a Windows Store alias that exits
49 with a "Python was not found" message. Use `python` (3.12.3). Recorded
because P1-LAYOUT's scripts assume `python3`.

## 7. Why four-byte repacking is still not approved for shipping

Unchanged from P1-LAYOUT's measurement, restated because the tool was built
against it:

- A 4-byte repack preserves all 111 / 76 member payloads and their hashes, but
  is **not** byte-identical: it is 5288 / 6736 bytes smaller than the originals
  because it collapses the original inter-member padding.
- The original per-member padding rule is still **unknown**; P1-LAYOUT showed no
  single rule reproduces both archives. A repack therefore *discards*
  information rather than reproducing an intended layout.
- The game has never been shown to accept a repacked archive at all.

So `sarc-layout` ships **no repack mode**. Same-length replacement changes only
the bytes the mod intends to change, which is the smallest claim that has to be
defended. Byte equality is a control here, not a shipping requirement.

## 8. How growth support stays separate

Growth and shrink move every later member and change the file size. That is a
different risk with different evidence needs (padding rules, loader tolerance,
size budget), so it needs a **separately reviewed implementation and validation**,
whether added as an explicit mode here or implemented separately. Keeping it out also keeps the conservative path's
byte-exactness intact: as long as `sarc-layout` can only produce same-length
output, "the output differs from the input only inside the target member"
stays a checkable invariant. If growth is ever approved, it must explicitly document and check its different invariants, and it should
begin by deriving the real padding rule from more samples rather than assuming
4-byte alignment.

## Limitations and unresolved questions

- **Unverified**: that the game accepts any modified `layout.arc`. Nothing was
  loaded by the game, the emulator or the console.
- **Unverified**: the absence of runtime checksums. This task cannot test for
  them; a correct-looking container could still be rejected.
- **Unverified**: the meaning of the header word at `0x10`. The tool copies it
  and never recomputes it.
- **Unverified**: the per-member padding rule. Gap bytes are replayed, not
  derived, so byte-exactness does not depend on solving this.
- **Not implemented, by design**: adding, removing or renaming members, growth,
  shrink, compression, big-endian, other SFAT header sizes, streaming.
- **Tier D carried over, not re-litigated here**: whether `set_item_06` is a
  legal next row and whether `layout.info` must list a new name (P1-LAYOUT).
  Both are BFLYT/loader questions that this container task does not touch.

## Changed files

Exclusive writes only:

- `mods/mii_customizer/tools/sarc-layout/sarc_layout.py`
- `mods/mii_customizer/tools/sarc-layout/check_sarc_layout.py`
- `mods/mii_customizer/tools/sarc-layout/README.md`
- `mods/mii_customizer/research/P2-SARC-WRITE.md` (this report)
- `mods/mii_customizer/evidence/P2-SARC-WRITE/` — `checks.json`,
  `manifest_make_mii_edit.json`, `manifest_make_mii_special.json`,
  `verify_make_mii_edit.json`, `verify_make_mii_special.json`,
  `rebuild_make_mii_edit.json`, `rebuild_make_mii_special.json`,
  `mutation_synthetic.json`
- `mods/mii_customizer/scratch/2026-10-04_P2-SARC-WRITE/build_synthetic.py`
- `gamedata/mii_customizer/P2-SARC-WRITE/` — `synthetic/`, `rebuilt/`,
  `mutated/`

Not touched: `gamedata/mii_customizer/P1-UI/` (inputs, hashes re-verified
unchanged), `gamedata/mii_customizer/P1-LAYOUT/`, `evidence/P1-LAYOUT/`,
another worker's files, shared `tools/`, `STATUS.md`, `CHANGELOG.md`,
`CURRENT_INSTALL.md`, git.

## Summary

**P2-SARC-WRITE: DONE.**

Both original `layout.arc` files parse, pass all structural checks and rebuild
**byte-identically** through an independent encoder that re-emits the header,
SFAT, name table and data section from parsed metadata. One existing member was
replaced with a same-length different payload on a synthetic archive, and an
independent reparse confirmed exactly that member changed while metadata,
ordering, offsets, name table, gap spans and gap bytes did not; on both real
archives a no-op replacement reproduces the originals exactly. Every member's
hash and offset agrees with the P1-LAYOUT manifest (111/111 and 76/76). Growth,
shrink, new members, duplicate names, traversal paths, overlapping or
out-of-bounds ranges, compression and big-endian inputs are all refused
explicitly and write nothing. `check_sarc_layout.py` reports 87 checks, 87
passed, exit 0.

This establishes container behaviour only. Whether the game accepts a modified
archive remains unverified and is not settled by anything here.

Next: group/part payload decoding (`P2-LAYOUT-STRUCTURE`) and the Lua selector
flow (`P2-UI-FLOW`).