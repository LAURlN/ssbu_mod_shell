# P2-MATCH-READER - how a saved Mii's special bytes and ID reach the match

Task: `prompts/P2-MATCH-READER.md`. Date 2026-10-04. Status: **PARTIAL** (A, C, D closed; B
enumerated but not followed to fighter creation).

Nothing here is runtime evidence. **B** = instructions read from the image in this task.
**D** = interpretation / hypothesis.

## Input

`gamedata/ssbu-13.0.4/main.bin` (workspace-relative), sha256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`, rehashed, matches
(`evidence/P2-MATCH-READER/00_input_identity.txt`). Flat image, address == file offset.

Names used below: `G = 0x53040f0`, `T = G+0x3670 = 0x5307760`. Code reaches `T` in two
equivalent forms: `adrp/add 0x5307760`, or `0x52c4180 + 0x435e0` (`G` lies inside the static
object at `0x52c4180`, the same one that holds the editor working record `W`).
`S` = the 0x190-byte struct copied by `0x16b6bb0` / `0x15547e0` (both are S copy functions).

## Short answers

**A. Entry offset (closed, B).** The four bytes land at **per-player entry `+0xa2..+0xa5`**:
`T + p*0x1c8 + 0xa2`, i.e. `0x5307802..0x5307805` for player 0, `0x53079ca..` for player 1.
Chain: loader output record at `sp+0x240`; `0x17918b4/0x17918b8` copy the qword at record
`+0x140` (`sp+0x380`) to local `sp+0x480`, which is `S+0x68` of the local struct `L = sp+0x3f0`
(`S = L+0x28`); `0x179e440` calls `0x16b6bb0(dst = entry+0x38, src = L+0x28)`
(`0x179e60c-0x179e618`); inside it `0x16b6d18/0x16b6d24` copy `S+0x68..+0x77` verbatim. So
record `+0x140` -> entry `+0xa0`, and `+0x142..+0x145` -> `+0xa2..+0xa5`. No clamp on this path.

**B. Readers (enumerated, not closed).** No instruction with `T`-derived base reads entry
`+0xa0..+0xa5` directly. The bytes leave the table only as part of whole-`S` copies whose
source is `entry+0x38`. Nine such sites (table below). Each copies `S` to a stack local or
into another object; none of them touches `S+0x6a..+0x6d` itself, and none writes a
fighter-kind key or entry id beside the copy that I could tie to fighter creation. A further
scan of all 604 callers of the two `S` copy functions found no load of `S+0x68..+0x6f` from
a stack-local copy (`evidence/P2-MATCH-READER/13_local_S_readers.txt`; its 15 hits in
`0x178c150` are scan overrun into later functions, the one in `0x23889f0` loads a qword at
`+0x68` and was not read further). So the consumer takes `S` by pointer through a call I
did not follow. Hop budget used: one hop per site. **This is where the trace stops.**

What the table is, from its writers (D): a general per-player "current fighter info" store
that several scenes refresh and several scenes copy from; not a match-setup structure in
itself. Writers found with `T`-derived base, same pattern each time (ID from a selection
source -> `0x17c8210` -> `0x179e440`): `0x17914d0` (players 0,1), `0x25cc840` (players
0..N-1, N = 1 or 4, six callers `0x23a0394..0x23b23b8`), `0x25cb100`, `0x1961590`, plus
more in `0x230c4f0..0x231c548` not read.

**C. Non-editor callers of `0x17c8210`** (22, list below). Seven take the ID from a
per-player or per-entry structure rather than from G's two selection structs. The most
useful one: **`0x230f2a4` in `0x230d4c0` reads the ID from `T + 0xe58 + p*0x240`**, a
second per-player table that sits directly behind the first one.

**D. Is the ID still next to the special bytes? Yes, same static base, same player index.**
`0x17914d0` does not only store record content. After `0x179e440` it also writes the
selection struct's three u32 (`sel+0xc`, `sel+0x10`, `sel+0x14`) to a second table:
`0x1791a30 ldr w8,[x20,#0x14]` / `0x1791a34 str w8,[sp,#8]` / `0x1791a40 madd x8,x23,0x240,[ctx]`
/ `0x1791a44 ldp x10,x11,[sp]` / `0x1791a58 str x11,[x8,#0xe58]`. So:

| value | location | player 0 |
|---|---|---|
| special bytes (record `+0x142..+0x145`) | `T + 0xa2 + p*0x1c8` | `0x5307802` |
| saved-fighter u32 ID (record `+0x000`, `sel+0x14`) | `T + 0xe58 + p*0x240` | `0x53085b8` |

Both are indexed by the same `p` (0..7) off the same base. `0x25cc840` writes the same pair
for each player (`0x25cd328 stp x9,x10,[x24,#8]` with `x24 = T+p*0x240+0xe50`, then
`0x25cd3d0 bl 0x179e440`), and `0x230d4c0` reads the ID back from there to load the record
(`0x230eca0`, `0x230ecb8`, `0x230f238`, `0x230f2a4`). `0x2340850` copies both together into
another object (`S` to `obj+0xaf20`, ID qword to `obj+0xb0c8`). This supersedes limit 1 in
P1-ID-REVIEW section 3 ("the per-player entry receives record contents, not the ID"): true for
the 0x1c8 entry, but the ID is stored 0xe58 further in the same block by the same function.

Not shown (D): that `p` equals the match entry id, that these slots are current at match
start for every mode, and that CPU / non-local players are filled.

## Table

| address | instruction | meaning | tier |
|---|---|---|---|
| `0x1791774-0x1791778` | `add x2,sp,#0x240` / `bl 0x17c8210` | record -> `sp+0x240` | B |
| `0x17918b4`, `0x17918b8` | `ldr x8,[sp,#0x380]` / `str x8,[sp,#0x480]` | record `+0x140..+0x147` -> `L+0x90` = `S+0x68` | B |
| `0x1791904-0x179190c` | `add x2,sp,#0x3f0` / `bl 0x179e440` | store `L` into entry `p` | B |
| `0x179e60c-0x179e618` | `add x1,x2,#0x28` / `add x0,x8,#0x38` / `bl 0x16b6bb0` | `S` -> `entry+0x38` | B |
| `0x16b6d18`, `0x16b6d24` | `ldp x9,x10,[x20,#0x68]` / `stp x9,x10,[x19,#0x68]` | **A:** `S+0x68..+0x77` verbatim -> entry `+0xa0..+0xaf` | B |
| `0x1791a30-0x1791a58` | `ldr w8,[x20,#0x14]` ... `str x11,[x8,#0xe58]` | **D:** saved ID -> `T+0xe58+p*0x240` | B |
| `0x25cce80` | `ldr w9,[x8,#0x14]` (x8 = `[[[0x5328f98]]+0x68] + p*0x78`) | `0x25cc840`: ID from a 0x78-stride per-player array | B; "character-select slots" D |
| `0x25cd080-0x25cd0e4` | `ldr w28,[sp,#0x278]` ... `bl 0x17c8210` | `0x25cc840`: load record for that ID | B |
| `0x25cd314-0x25cd328` | `ldr x9,[sp,#0x278]` / `stp x9,x10,[x24,#8]` | `0x25cc840`: ID -> `T+0xe58+p*0x240` | B |
| `0x25cd3d0` | `bl 0x179e440` (x0 = `T`, w1 = player) | `0x25cc840`: record content -> entry `p` | B |
| `0x230eca0`, `0x230ecb8`, `0x230f238-0x230f2a4` | `ldr x8,[x20,#0xe58]` / `stp x8,x10,[sp,#0x78]` / `ldr w20,[sp,#0x78]` / `bl 0x17c8210` | `0x230d4c0`: ID read back from the second table | B |
| `0x18384f4` | `add x1,x8,x9` (`+0x43618`) / `bl 0x15547e0` | reader 1: fn `0x1837d30`, `S[p]` -> `sp+8`; 0 direct callers | B |
| `0x1897a78` | `add x1,x8,x9` / `bl 0x16b6bb0` | reader 2: fn `0x1896640`, `S[p]` -> `[x29-0x58]`; 1 direct caller (`b` at `0x189c8f8`) | B |
| `0x19617e8` | `add x1,x20,#0x38` / `bl 0x15547e0` | reader 3: fn `0x1961590`, `S[0]` -> local, then rewrites entry 0; 0 direct callers | B |
| `0x230ed38` | `add x1,x8,#0x38` / `bl 0x15547e0` | reader 4: fn `0x230d4c0`, `S[p]` -> `sp+0x548`; 0 direct callers | B |
| `0x2316290` | `add x1,x8,x9` / `bl 0x15547e0` | reader 5: fn `0x23146b0`, `S[p]` -> `sp+0x20`, two float->s16 fields set beside it; 0 direct callers | B |
| `0x2341bf4`, `0x2341c0c`, `0x2341c3c` | `add x1,x8,#0x38` / `bl 0x16b6bb0`; `ldr x13,[x8,#0xe58]` / `str x13,[x26,x10]` | reader 6: fn `0x2340850`, `S[p]` -> `obj+0xaf20` and ID qword -> `obj+0xb0c8`; 0 direct callers | B |
| `0x25cb350` | `add x1,x8,#0x38` / `bl 0x15547e0` | reader 7: fn `0x25cb100(player)`, read-modify-write of entry; 2 callers (`0x188c084`, `0x24a2f9c`) | B |
| `0x25ccc18` | `add x1,x8,#0x38` / `bl 0x15547e0` | reader 8: fn `0x25cc840`, read-modify-write of entry; 6 callers | B |
| `0x3311574-0x331157c` | `add x2,x8,x9` / `b 0x3311190` | reader 9: fn `0x3311530(obj, player)` tail-calls `0x3311190([obj+8], player, &S[p])`; 2 callers (`0x1806dc4`, `0x1806ddc`); `0x3311190` not read | B |

Function starts come from a prologue heuristic (`scratch/.../fs.py`). "0 direct callers" means
no `bl`/`b` to that start; no relocation slot points at the four I checked (`0x230d4c0`,
`0x2340850`, `0x1896640`, `0x23a0180`), so those starts are unverified.

### C. The 22 non-editor callers of `0x17c8210`

`*` = ID from a per-player / per-entry structure, not from G's two selection structs.

| call | function | ID argument comes from |
|---|---|---|
| `0x14ebba4`, `0x14ebd28`, `0x14ebed0` `*` | `0x14e58f0` | `[obj + 0x26c + i*0x18]`, the 3-entry array of P1-ID-REVIEW path 1 (`0x14ebb08`) |
| `0x1791778` | `0x17914d0` | `[sel+0x14]`, `sel = G+0x1890 / G+0x18a8` |
| `0x180fcb4` | `0x180faf0` | editor list `[x+0x178][cursor]` (P2-SKILL-STORE) |
| `0x1810070` | `0x180fe50` | scene field `[x19+0x100]`, set just before from the scene's own list |
| `0x18102d0` | `0x1810130` | same scene field `[x19+0x100]` |
| `0x1ccb708` | `0x1ccb2d0` | `[x19+0x5d4]`; x19 also uses `+0x5d0/+0x5d8/+0x5e0` (D: the post context of P1-ID-REVIEW 2.4) |
| `0x230f2a4` `*` | `0x230d4c0` | **`[T + 0xe58 + p*0x240]`** (`0x230eca0`) |
| `0x23710fc` | `0x2370f30` | `[x2+0x14]` of its third argument; caller `0x236f410` passes `G+0x18a8`, caller `0x236f3e8` not resolved |
| `0x2372a38` | `0x2371d80` | stack slot `sp+0x7b4`; only zero stores seen, non-zero writer not traced |
| `0x23a1024` `*` | `0x23a0d20` | `[entry+0x14]` of an array reached from `[0x5328f98]` (`0x23a0e7c`; key at `+8`, byte at `+0x10`) |
| `0x23a3fc4` | `0x23a3b70` | stack slot `sp+0x228` filled from `w23`; same code shape as `0x23a0d20`, source not re-read |
| `0x23a59b8` | `0x23a5140` | stack slot `sp+0x248` <- `sp+0x5c` <- `w10` at `0x23a55f8`; not traced further |
| `0x23b2ee4` | `0x23b2a90` | stack slot `sp+0x228` filled from `w23`; same shape, not re-read |
| `0x23bab0c`, `0x23bae4c` `*` | `0x23b9320` | scene field `[x19+0xaa8]` |
| `0x23bac80`, `0x23bb440` `*` | `0x23b9320` | scene field `[x19+0x8f8]` (0x1b0 below the other; two per-entry slots) |
| `0x24933e8` `*` | `0x24931b0` | `[x + 0x26c + i*0x18]` (`0x24932b8`), same shape as path 1; base not verified |
| `0x24cab70` `*` | `0x24caaf0` | `[[[[0x5313510]]+0x158]..] + i*0x3d700 + 0x3d6dc`, i = argument or `[x0+0x1c]`, i <= 2 |
| `0x25cd0e4` `*` | `0x25cc840` | per player: `[[[0x5328f98]]+0x68] + p*0x78 + 0x14`, or the 0x18-stride `+0x26c` slot, or the 0x3d700-stride `+0x3d6dc` slot |

## Method, checks, failures, limits

- `scratch/2026-10-04_P2-MATCH-READER/scan.py`: linear constant tracker (adrp, add, mov/movk,
  madd) that reports instructions forming an address inside `T .. T+0xe40+8*0x240` from an
  in-function adrp. 1539 hits in 93 clusters (`evidence/.../04_scan_T_region.txt`,
  classified in `05_scan_classified.txt`). `classify.py` maps hits to table and entry offset.
- `check_claims.py`: **95 checks, 0 failures, exit 0** (`evidence/.../14_claim_check.txt`).
  Re-disassembles every cited instruction, re-derives `0xa2`, `0x5307802`, `0x53085b8`, the
  139 / 22 caller counts and the caller lists.
- Limits of the scan: it only sees bases built from an adrp in the same function. Code that
  gets `T` through a pointer argument (as `0x17914d0` does through `ctx[0]`) is invisible to
  it unless I followed the caller. State is tracked linearly, not per branch.
- Failed approach: looking for a reader of `S+0x6a` in stack-local `S` copies
  (`scopy.py`). No genuine hit; the function-end test overruns and produced false hits.
- Not read: the roughly 80 other clusters that touch the tables (mostly offsets `+0x0..+0x58`
  of the entry, i.e. `S+0..+0x20`: player number, a u32 state, the two 0xc1 keys). The `S`
  struct stored at second-table entry `+0x98` is copied around but was not shown to receive
  record bytes.

## Smallest remaining unknown

Whether `T + 0xe58 + p*0x240` holds the right saved-fighter ID for match player `p` at the
moment a match starts. Offline evidence gives the address, its writers and one reader; it does
not give timing or the mapping from `p` to the match's entry id.

Log-only console diagnostic, three watch points (register arguments and one fixed static
address only, no pointer chasing):

1. **Entry of `0x179e440`**: log `w1` (player), the u32 at `T + 0xe58 + w1*0x240` and the
   return address. Decides which writer runs for a normal versus-mode start and for which
   players. If it never fires between character select and match start, the table is not on
   the match path.
2. **Entry of `0x17c8210`**: log `w1` (ID) and the return address. Decides which of the 22
   non-editor callers loads each player's record before the match; return address `0x230f2a8`
   or `0x25cd0e8` confirms the table path found here.
3. **At the mod's intended match-start point** (any existing fighter-init hook): log the eight
   u32 at `T + 0xe58 + p*0x240` and the four bytes at `T + 0xa2 + p*0x1c8`. Decides whether a
   plain static read is enough: with two differently configured Gunners as P1 and P2 the two
   IDs must differ and the bytes must match each Mii's saved specials.

Prerequisite carried over from P1-ID-REVIEW: confirm on one known offset that file offsets
equal module-relative offsets at runtime.

## Closing summary

- **Task ID:** P2-MATCH-READER
- **Status:** PARTIAL (B not followed to fighter creation; A, C, D answered)
- **Changed files:**
  - `research/P2-MATCH-READER.md` (new)
  - `evidence/P2-MATCH-READER/` (new): `00_input_identity.txt` .. `14_claim_check.txt`
  - `scratch/2026-10-04_P2-MATCH-READER/` (new): `d.py`, `rel.py`, `chain.py` (unmodified
    copies), `scan.py`, `classify.py`, `fs.py`, `scopy.py`, `check_claims.py`
- **Observed checks:** input hash matches; 95/95 instruction, offset and caller-count claims
  re-derived.
- **Out of scope, noticed:** P1-ID-REVIEW section 3 limit 1 is incomplete (the ID is stored in
  the adjacent table by the same function). That report is another worker's file and was not
  edited.
- **Next experiment:** the three-point log-only run above. Offline alternative, one bounded
  task: read `0x3311190` and the tail of `0x2340850` (the two readers that hand `S` on by
  pointer or into a longer-lived object) and check for a fighter-kind key written beside it.
