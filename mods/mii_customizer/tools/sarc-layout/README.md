# sarc-layout

A conservative reader/writer for **Nintendo SARC** archives, built for one
question: *can the bytes of one existing member be swapped without the
container moving?*

It lists an archive, extracts a member by name, re-serialises an unchanged
archive byte-for-byte, and replaces exactly one existing member with a
**same-length** payload. Everything else it refuses out loud.

Python 3 standard library only. Nothing to install, no external crate, no
build step.

## Status

Working. `check_sarc_layout.py` runs 87 checks and exits 0. Verified offline
(B) on both Mii editor `layout.arc` files (111 and 76 members), which rebuild
byte-identically, and on a synthetic archive with non-uniform gap padding.

**This tool proves container behaviour only.** A byte-identical rebuild is
evidence about the file format. It is not evidence that the game accepts a
modified archive, and nothing here tests for runtime checksums.

## Usage

Paths are relative to the workspace root. On this machine `python` works and
`python3` is a Windows Store alias that does not, so use `python`.

```bash
T=mods/mii_customizer/tools/sarc-layout/sarc_layout.py
E=gamedata/mii_customizer/P1-UI/ui/layout/menu/make_mii_edit/make_mii_edit/layout.arc

python $T list     $E                              # header fields + every member
python $T list     $E --json out.json              # same, as JSON
python $T extract  $E blyt/make_mii_edit.bflyt -o member.bflyt
python $T rebuild  $E -o rebuilt.arc               # control: must be byte-identical
python $T replace  $E blyt/make_mii_edit.bflyt --payload member.bflyt -o patched.arc
python $T verify   $E                              # structural checks, exit 0 if clean
```

`rebuild` refuses to write its output unless the result is byte-identical to
the input, so the control cannot silently pass.

### Checks

```bash
python mods/mii_customizer/tools/sarc-layout/check_sarc_layout.py
```

Covers, all against real or independently built data:

- both real archives parse, pass structural checks and rebuild byte-identically,
  and are unchanged at the end of the run
- member manifest agreement with the P1-LAYOUT manifest (membership, every
  member sha256, every member offset)
- a synthetic archive replaces one member; an independent reparse confirms
  exactly that member changed and that header metadata, SFAT name-offset
  fields, name table, member order, offsets, gap spans and gap bytes did not,
  and that **every** differing byte lies inside the target member
- a no-op `replace` (a member's own bytes as the payload) reproduces each real
  archive exactly, exercising the replace path at 111 members / 927 kB without
  inventing game content
- refusals: payload too long, payload too short, missing member, traversal
  names (`..`, absolute, backslash), out-of-bounds range, overlapping ranges,
  duplicate names, an archive whose stored member name escapes, Yaz0
  compression, big-endian BOM, truncation, writing over the input, writing
  outside the workspace
- a damaged name hash is reported as a **failed check** with exit 1, not a crash

The synthetic archives and damaged variants are built by
`scratch/2026-10-04_P2-SARC-WRITE/build_synthetic.py`, deliberately written
separately from the tool so an encoder bug cannot hide by validating the tool
against its own output.

## What it preserves

On `replace` the output differs from the input **only** inside the target
member's byte range. Everything else is carried over verbatim:

- the `0x10` header word (copied, never recomputed — its meaning is unverified)
- the SFAT table, including every entry's name hash and name-offset field
- member ordering, which is by name hash, not by name
- every member's original start and end offsets
- the name table and the padding between the last name and `data_offset`
- every inter-member gap byte

Gap and padding bytes are **captured at parse time and replayed**, never
regenerated. P1-LAYOUT showed there is no single padding rule reproducing both
real archives, so deriving them would be a guess.

## Refusals

Each of these exits non-zero with a message naming the reason, and writes no
output file:

| refusal | why |
|---|---|
| payload length != member length | no growth, no shrink; offsets of everything after the member would move |
| member name not present | this tool replaces existing members only |
| `..`, absolute, backslash or non-normalised member names | path traversal; checked both for names stored *inside* an archive and for names passed on the command line |
| member range outside the data section | would read or write out of bounds |
| two member ranges overlap | ambiguous ownership of the same bytes |
| duplicate member names | name lookup would be ambiguous |
| Yaz0 / Zstd / YazR container | compression is out of scope, not guessed at |
| big-endian BOM | only the little-endian variant is implemented |
| header size field disagreeing with the file length | truncated or malformed input |
| output path equal to the input path, or outside the workspace | inputs are read-only |

## Limits

- **Same length only.** Growing or shrinking a member moves every later member
  and changes the file size. That is deliberately not implemented; see the
  growth note below.
- **No new members.** Adding a member means touching the name table, the SFAT
  count and the hash ordering, and the loader's expected name is unknown
  (P1-LAYOUT, tier D). Refused by omission.
- **Uncompressed, little-endian, SFAT-header 0x0C** only. Other header sizes are
  refused rather than interpreted.
- **No streaming.** The whole archive is read into memory; these files are
  under 1 MB, so that is fine here and would not be for large archives.
- **Reads the whole name table as one slice.** A name table extending past
  `data_offset` cannot occur, since `data_offset` bounds it by construction.
- **`rebuild` is an encoder, not a repacker.** It reproduces the input
  archive's layout. It does not normalise or realign anything, and it will not
  produce a "clean" archive.
- **No BFLYT/BNTX awareness.** Members are opaque bytes here. Decoding or
  editing the BFLYT payload is a separate task
  (`P2-LAYOUT-STRUCTURE` owns group/part decoding).

## Why four-byte repacking is not approved for shipping

A 4-byte-aligned repack of these two archives preserves all 111 and all 76
member payloads and their hashes exactly, but it is **not byte-identical** and
it is 5288 / 6736 bytes smaller than the originals, because it collapses the
original inter-member padding (measured in P1-LAYOUT). That is a container
change with no evidence behind it:

- the original per-member padding rule is still unknown, so a repack discards
  information rather than reproducing an intended layout;
- the game was never shown to accept a repacked archive at all.

So repacking stays out of the shipping path. `sarc-layout` deliberately offers
no repack mode: same-length replacement changes only the bytes the mod
intends to change, which is the smallest possible claim to have to defend.

Future growth support should remain a **separate, separately justified tool**
rather than a mode added here, because it is a different risk: it changes the
file size and the offsets of every later member, so it needs its own evidence
about padding rules and loader tolerance before it can be trusted. Keeping it
separate keeps the conservative path's byte-exactness intact.