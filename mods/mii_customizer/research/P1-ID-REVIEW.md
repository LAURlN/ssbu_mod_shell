# P1-ID-REVIEW - audit of the saved-fighter ID candidate and one battle-side hop

Task: `prompts/P1-ID-REVIEW.md`. Date 2026-10-04. Status: **PARTIAL** (closing block at the end).

Input: `gamedata/ssbu-13.0.4/main.bin`, sha256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613` (rehashed in this task). Flat image,
address == file offset; all addresses below are in that space. Pointer slots in `.data` are zero in the
file and are filled by `R_AARCH64_RELATIVE` relocations, which were read from the image where needed.

Evidence: `evidence/P1-ID-REVIEW/instruction_windows.txt` (every window cited here) and
`evidence/P1-ID-REVIEW/relocs_callers_scans.txt`. Tools: `scratch/2026-10-04_P1-ID-REVIEW/d.py`,
`prov_scan.py` (capstone 5.0.9 from `mods/ssbu_mod_new/builds/.cache/dk_cargo/python`, read-only).

Tiers: **B** = instruction sequence read in this task (verified offline, static only); **D** = my
interpretation. Nothing was executed; no runtime behaviour is established.

## 1. Verdict

- **The ID candidate survives.** The 32-bit value is the first field (`+0x00`, u32) of a 0x1B0-byte
  saved-fighter record and is the key of an id -> record-index map. (B)
- **P1-ID's "editor -> battle handoff" is wrong.** `post_fighter` writes into a context object that
  other scenes also fill with a different content-type code; with the Lua names `post_fighter` /
  `is_finished_post` / `is_busy` it is the *post (share) a fighter* action. (B for the writes, D for
  "online post".) `manager+0x5d4` is not a battle input, and P1-ID section 7's proposed next task
  (trace `+0x5d4` into `StateSetupMiiFighter`) should be dropped.
- **New link found:** a per-player function (player index bounds-checked `< 8`) takes a 0x18-byte
  selection struct holding the saved-fighter ID at `+0x14`, loads the record by that ID and writes
  its contents into a per-player table. (B) Whether that table feeds battle setup is not traced.

## 2. Audit of the four flagged issues

### 2.1 Hash (P1-ID sections 1, 3, 4)

Actual calculation, identical at 0x19d4310-0x19d433c, 0x17c8494-0x17c84c0, 0x19d18dc-0x19d1904 and
0x1791670-0x17916a0 (B):

```
h = 0x811C9DC5
for each u16 c until c == 0:   h = (h * 0x89) ^ c        ; 32-bit, multiply first, then xor
```

It is not FNV-1a (order is multiply-then-xor, multiplier 0x89 is not 0x01000193, unit is u16), not
CRC32 and not Hash40. P1-ID's "the CRC component of hash40" is false and contradicts its own verified
`hash40 = (len<<32)|crc32` decode. The claim that the three `save:/save_data/mii` sites hash `"mii"`
with this constant was **not re-verified**: a 40-instruction window at 0x17c1100 shows the string
reference at 0x17c1144 and byte loads but no such constant. Treat that claim as unverified.

### 2.2 "14/27" (P1-ID section 6, trace section 5)

`asr #4` followed by `mul` with 0x84bda12f684bda13 is the exact-division idiom for a pointer
difference: the constant is the multiplicative inverse of 27 modulo 2^64 (`M*27 mod 2^64 == 1`,
computed), so the result is `(end - begin) / (16*27) = (end - begin) / 0x1B0`, the element count of
the record vector. The second constant 0xcb6309f0975f5dc5 is the inverse of 6413 with `asr #6`:
element size 0x64340 (0x17c83fc builds that same number as a `madd` stride). (B)

Consequences: "count * 14/27 > 98", "count > 189", "stride 16" and "M is not a reciprocal divisor"
are all wrong. At 0x17c82c4-0x17c82cc the idiom is the bounds check `record_count > record_index`
before `record = base + index*0x1B0`. `is_max_num` therefore compares an element count with 98;
capacity itself was not researched (out of scope).

### 2.3 Registration, calling convention, vector index (P1-ID section 4)

- Not a vtable slot. 0x19d2cf0-0x19d2d60 allocates a 0x28-byte delegate:
  `[+0x00]` = vtable 0x50a6d28 (x23, set at 0x19d2a34), `[+0x08]` = 0, `[+0x10]` = x27,
  `[+0x18]` = 0x19d41f0, `[+0x20]` = 0, then registers it under `"post_fighter"` via 0x3376540. (B)
- x27 is the scene object: `mov x27, x0` at 0x19d0fec in the enclosing function 0x19d0fb0, reloaded
  from `[x29-0x58]`. (B)
- Vtable 0x50a6d28 relocates to {0x19c2210, 0x19dc640, **0x19dc650**}. The invoke thunk 0x19dc650
  takes the top Lua value (type tag 0x13 integer used directly; tag 3 float is floored and
  converted) into x1, then does a standard pointer-to-member call:
  `x0 = [d+0x10] + ([d+0x20] >> 1)`, `x2 = [d+0x18]`, `br x2` (0x19dc71c-0x19dc744). (B)
  So the handler is `0x19d41f0(x0 = scene object, w1 = Lua integer)`. P1-ID's address is right; its
  mechanism description is not.
- Vector `self+0x178` (begin/end/cap at +0x178/+0x180/+0x188) is built in the same function
  0x19d0fb0: reserve `map_size + 1`, **push 0** (0x19d11f0 `str wzr,[x19],#4`), then for record index
  0..count-1 push `[sp+0x200]`, the first u32 of the record copy (0x19d1970-0x19d1974, slow path
  0x19d1a50-0x19d1a5c). (B) Skip conditions inside the loop were not enumerated.
- Handler bounds: `w1 >= 1` and `w1 < size`, then `ids[w1]` with **no** index adjustment
  (0x19d420c-0x19d4244). Index 0 is the zero sentinel and is rejected. "1-based list index" is
  correct only in that sense; the mapping list position -> record is `ids[k] = id of the k-th record
  that the loop accepted`. (B)
- P1-ID's open point "is the `self+0x178` vector the same array the `%s_%d.bin` loop walks at
  `[x19+0xc0]`" stays open. Not needed: the ID's meaning is fixed by the two bullets above.

### 2.4 Record load / "global merge" vs. handoff

- 0x17c8210(`x0` = saved-fighter manager, `w1` = id, `x2` = out): rejects id 0; lower-bound search
  in a red-black map (header at `inner+0x50`, size `inner+0x58`, node key u32 `+0x1c`, value s32
  `+0x20`); bounds check (2.2); `record = [inner+0x18] + index*0x1B0`; byte `record+0x1a9` must be 0;
  then copies the record out. `inner = [x0]`, and callers obtain x0 as `[[[0x5313510]]+0x88]`. (B)
- 0x17c8530 is the matching "is this id valid" predicate (same lookup, returns bool). (B)
- Out-struct / record layout as far as the copy shows it (B for offsets, D for meanings):

  | offset | content |
  |---|---|
  | +0x000 | u32 saved-fighter ID (memcpy of 0x110 bytes starts here; this is what the editor list stores) |
  | +0x110 / +0x114 | u32 name hash (2.1) / u32 name length |
  | +0x118..+0x12c | u16[11] zero-terminated name, max 10 units |
  | +0x130, +0x138 | two u64 tagged keys, top byte 0x13 and 0x5a, low 40 bits a hash. D: hat/body-type ids |
  | +0x140..+0x145 | six separate bytes. +0x142..+0x145 are the four special-move choices, values 0..2 (B, `research/P2-SKILL-STORE.md`; coordinator correction 2026-10-04, this row originally read "+0x140, +0x144: u32, u16 - meaning unknown"). +0x140, +0x141 meaning unknown |
  | +0x148..+0x1a0 | 0x58 bytes copied as a block. D: Mii appearance blob |
  | +0x1a0 | u64 tagged key, top byte 0xc1 (same tag the selection struct in section 3 tests). D: character id |
  | +0x1a8 / +0x1a9 | u8 / u8 flag that must be 0 for a usable record |

- The "global 512-entry u16 id list with FNV checksum" is the **fighter name**: 0x19d42bc-0x19d433c
  copies the zero-terminated u16 string at out+0x118 into `ctx+0x1d0` (cap 0x1ff units + terminator),
  stores its length at `+0x1cc` and its hash at `+0x1c8`. It overwrites from index 0; it does not
  merge. No special-move or costume indices are involved. (B)
- 0x19d4340-0x19d4478 does not copy "colour ids": it checks the two tagged keys (+0x138 tag 0x5a,
  +0x130 tag 0x13) against two tables and two predicates and sets a result code at `ctx+0xbf0`
  (1 or 2). Meaning D.
- The context `ctx = [[0x5324ca8]+8]` is gated by `ctx+0x198 == 1` and is also written by
  0x1eabc24, 0x1ac3ee8 and 0x1ae7d10, which store 1, 2 and 4 to the u16 at `ctx+0x5d0` where
  `post_fighter` stores 0; the latter two also clear the same `ctx+0xbf0`. A provenance-bound scan (base
  register loaded from 0x5324ca8 in the same function) finds **no reader** of `ctx+0x5d4` other than
  `post_fighter` itself. (B) So this path carries {content type, id, name} to a multi-content
  "post" service; it is not appearance, not specials and not battle setup.

## 3. Downstream trace (two paths, per the prompt limit)

Method: followed callers of the verified loader 0x17c8210 (argument provenance is explicit at every
call site) instead of matching immediates. 139 `bl` callers; 117 are in the editor scene range
0x19d0950-0x19dc304.

### Path 1 - 0x14ebba4 / 0x14ebd28 / 0x14ebed0: not per-player (preserved, not pursued)

0x14ebaac-0x14ebc60 (B): object `[[0x5328fb0]]` holds three 0x18-byte entries at `+0x258`
(cursor byte `+0x2d5`, taken modulo 3): `{u8 used @+0, u64 tagged key @+8, u32 id @+0x14}`. For each:
validity check 0x17c8530, load 0x17c8210, then the 0x58-byte block out+0x148 is queued under a lock
into `[[0x593a6a0]]+0x24d0`. Reached only when a mode value is 7 or 8. No player index anywhere.
It shows that (character key, saved-fighter ID) pairs exist outside the editor; it is not a
per-player association.

### Path 2 - 0x1791778: per-player association (the new link)

`0x17914d0(x0 = ctx, w1 = player, x2 = sel)` (B, windows `path2_*`):

```
0x17914f0  cmp w1,#8 ; b.hs exit              player index 0..7
0x17914f8  x8 = [ctx+0] ; entry = x8 + player*0x1c8   per-player table, read: +0x10, name +0x1c.., +0x34, +0x38
0x17916d0  x1 = [sel+0]                       u64 tagged key; tag byte compared with 0xc1, low 40 bits != 0
0x1791724  w8 = byte [sel+8]
0x179176c  x0 = [ctx+0x10]                    saved-fighter manager
0x1791770  w1 = [sel+0x14]                    <-- saved-fighter ID
0x1791778  bl 0x17c8210                       record -> sp+0x240
0x1791780-0x17918fc  record name (+0x118), keys +0x130/+0x138 and +0x140..+0x198
                     copied into the local player struct at sp+0x3f0 (+0x68, +0x80, +0x88, +0x90..+0xe8)
0x1791900  x0 = [ctx+0] ; w1 = player ; x2 = sp+0x3f0 ; bl 0x179e440
0x179e44c  cmp w1,#8 ; dst = x0 + player*0x1c8 + 0x10      per-player store
```

Only caller, 0x1791390 (B), builds ctx from a static object `G = 0x53040f0`:
`ctx = {G+0x3670, [[0x532e730]+8]+0x160, [[[0x5313510]]+0x88], G+0x1880, G}` and calls
`0x17914d0(ctx, 0, G+0x1890)` and `0x17914d0(ctx, 1, G+0x18a8)`. 0x1791390 is called from
0x230d844 (right after `G[0]` is initialised) and 0x2370b64.

Smallest proven association (B):

> player index p in {0,1} -> selection struct `G+0x1890 + p*0x18` = `{u64 character key (tag 0xc1) @+0,
> u8 @+8, u32 saved-fighter ID @+0x14}` -> record `0x17c8210(mgr, ID)` -> per-player entry
> `G+0x3670 + p*0x1c8` receives the record's name, the two tagged keys and record bytes +0x140..+0x198.

Limits, stated precisely:

1. The per-player entry receives record **contents**, not the ID. The ID stays in the selection
   struct. Record `+0x000` is not copied by this function.
2. This caller covers players 0 and 1 only. The table and the setter 0x179e440 accept 0..7; other
   writers of the table were not enumerated.
3. **Missing hop:** who reads `G+0x3670 + p*0x1c8` (or the selection struct) when a match is set up,
   and whether that reader is on the path of the `StateSetupMiiFighter` reference at 0x1341d64.
   Not traced; both allowed paths are used. Nothing here shows what G is (D: persistent
   last-used fighter settings re-resolved after save load).
4. Which record bytes hold the special-move choices is not established. `+0x140` (u32) / `+0x144`
   (u16) are the only copied fields with no assigned meaning (D).

## 4. Is there enough for a diagnostic implementation?

For a **log-only** diagnostic, yes; for anything that changes behaviour, no.

- Hook entry of 0x17c8210 and log `w1` (ID) plus the return address; hook entry of 0x17914d0 and log
  `w1` (player) and the u32 at `x2+0x14`. Both read only register arguments and one field of an
  argument whose address is a known static (`G+0x1890` / `G+0x18a8`); no arbitrary pointer reads.
- Unverified prerequisite: that file offsets in `main.bin` equal module-base-relative offsets at
  runtime. Adrp targets resolve consistently in this image, which supports it, but check one offset
  already proven on console in the old project before building.

What one console run with that log would settle (offline evidence cannot, because the remaining
readers are reached through relocated pointers and scene state):

1. Whether 0x17c8210 is called with each player's ID between character select and match start,
   and from which return addresses - this names the battle-side reader directly (the missing hop).
2. Whether two different Mii Gunners produce two different IDs at that moment, and whether
   0x17914d0 fires for local players at all or only at save load.
3. As a by-product, whether IDs persist across reboot (same values logged in two sessions).

Suggested run: vanilla control (no Mii) / two differently configured Gunners as P1 and P2 /
reboot and repeat. The delete/recreate lifecycle is a separate question and is not a prerequisite.

Offline next step if a console run is not wanted yet: enumerate `bl` callers of 0x179e440 and the
functions that take `G+0x3670` (adrp 0x5304000 + `#0xf0`, then `#0x3670`), keeping the base-register
provenance rule used here; stop at the first one that also writes a fighter-kind or entry-id field.

## 5. Exact corrections for `research/P1-ID.md` (coordinator to apply; not edited by this task)

1. Section 1 item 1: delete "which is the FNV-1a 32 offset basis - i.e. the CRC component of the
   game's `hash40`". Replace with: "0x811C9DC5 is the seed of a separate 32-bit u16-string hash
   (`h = h*0x89 ^ c`); its use at these three sites is unverified."
2. Section 1 item 3 and the table rows that call the ID "the thing the editor hands to the
   battle-entry code": replace with "read by `post_fighter`, which is the post/share action, not
   match entry". Add: "the ID is the u32 at record +0x000; `ids[0]` is a zero sentinel".
3. Section 3, last paragraph: delete the "global 512-entry u16 array ... FNV-1a 32 hash ... native
   per-Mii list of u16 ids" passage. Replace with: "`ctx+0x1c8/+0x1cc/+0x1d0` hold hash, length and
   UTF-16 text of the fighter name for the post context."
4. Section 4: "vtable slot written ... = handler address" -> "0x28-byte delegate
   {vtable 0x50a6d28, 0, scene object, fn 0x19d41f0, adj 0}; invoke thunk 0x19dc650 passes
   `x0 = scene object`, `w1 = Lua integer`". "UiFighterManager singleton" for x20 -> "post context
   `[[0x5324ca8]+8]`"; the object passed to 0x17c8210 is `[[[0x5313510]]+0x88]`.
   "u16 fields record+0x118..+0x12a" -> "name". "merge u16 list, hard cap 512" -> "copy name".
   "w11 = 0x89 = 137 = FNV-1a prime" -> "multiplier 0x89; not an FNV prime".
   "colour ids -> manager+0xbf8" -> "availability checks on tagged keys +0x130/+0x138; result code
   at ctx+0xbf0". Delete the sentence "That is a complete editor->battle handoff for the identity of
   the saved fighter."
5. Section 6: replace the 14/27 analysis with "exact division by 0x1B0 (inverse of 27 mod 2^64 after
   `asr #4`); `is_max_num` compares a record count with 98; second path divides by 0x64340".
   Keep "capacity not researched".
6. Section 7: drop "Trace `manager+0x5d4` forward into battle entry setup"; replace with the missing
   hop in section 3 above.
7. Section 8 table: row 3 ("global u16 id list") -> remove; row 2 add the field table from 2.4.
8. `evidence/P1-ID/post_fighter_trace.txt` carries the same errors in its sections 1, 4 and 5; mark it
   superseded by `evidence/P1-ID-REVIEW/instruction_windows.txt` rather than editing it.

## 6. Not done / not verified

- No runtime evidence of any kind. "post = online share" and all field meanings are D.
- Loop skip conditions in 0x19d0fb0, the 0x64340-element container, save-file naming and capacity
  were not examined.
- `mods/ssbu_mod_new/` was used only for the cached capstone package; its handbook was not consulted
  for these addresses.

## Closing block

**P1-ID-REVIEW: PARTIAL**

Checks run (all observed): main.bin sha256; disassembly of every window in the evidence file;
relocation lookup of vtable 0x50a6d28; modular inverses of both multipliers (`M*27 == 1`,
`M*6413 == 1` mod 2^64); `bl` caller enumeration of 0x17c8210, 0x17c8530, 0x17914d0, 0x1791390;
provenance scan for `[[0x5324ca8]+8]+0x5d4`.

Corrections: hash is `h*0x89 ^ u16`, not FNV-1a/CRC/Hash40; "14/27" is exact division by 0x1B0;
handler is reached through a delegate + pointer-to-member thunk, index is unadjusted with a zero
sentinel at 0; the "u16 id list" is the fighter name; `post_fighter` is not a battle handoff.

New proven link: player index (0/1) -> `G+0x1890 + p*0x18` selection struct with saved-fighter ID at
`+0x14` -> 0x17c8210 -> per-player entry `G+0x3670 + p*0x1c8` (G = 0x53040f0), via 0x1791390 ->
0x17914d0 -> 0x179e440. Missing hop: the match-setup reader of that table / selection struct.

Changed files (all new, inside the allowed paths):

- `research/P1-ID-REVIEW.md`
- `evidence/P1-ID-REVIEW/instruction_windows.txt`
- `evidence/P1-ID-REVIEW/relocs_callers_scans.txt`
- `scratch/2026-10-04_P1-ID-REVIEW/d.py`
- `scratch/2026-10-04_P1-ID-REVIEW/prov_scan.py`

Not touched: `research/P1-ID.md`, `STATUS.md`, other workers' files, `mods/ssbu_mod_new/`, `dump/`.
No commits, no emulator, no installs, no subagents.
