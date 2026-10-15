# P2-SKILL-STORE - where the four special-choice bytes come from and go to

Task: `prompts/P2-SKILL-STORE.md`. Date 2026-10-04. Status: **DONE** (offline static trace).

Nothing here is runtime evidence. **B** = instructions read from the image in this task.
**C** = pinned prior report. **D** = interpretation / hypothesis.

## Input

`gamedata/ssbu-13.0.4/main.bin` (workspace-relative), sha256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`, rehashed, matches
(`evidence/P2-SKILL-STORE/00_input_identity.txt`). Flat image, address == file offset.
capstone 5.0.7. Vtable slots read from the bare relocation array at `0x39c8070..0x40c9fc7`.

## Short answer

The prompt's hypothesis is **off by two bytes**. The four option bytes are saved-record
**`+0x142, +0x143, +0x144, +0x145`** (row 0..3), not `+0x140..+0x143`. They straddle what
P1-ID-REVIEW 2.4 listed as "u32 at +0x140, u16 at +0x144". `+0x140` and `+0x141` are two
other bytes (meaning D, unknown).

Between the saved record and the screen object sits a **static editor working record `W` at
`0x5306b78`**, with the same 0x1B0 layout as a saved record plus extra fields up to at least
`+0x1d8`. It lives in the static object at `0x52c4180` (lazy init `0x17641a0`, guard
`0x53134d8`), at offset `0x429f8`.

**A. Who fills `[obj+0x100..0x103]` before the screen opens.**
The scene that owns `outer` in slot `[scene+0x198]` (constructor caller `0x1809814`, enclosing
function `0x1808980`). Its function `0x180ba20`, entry branch (`[scene+0x14c] == 0`), copies
`W+0x142..+0x145` (addresses `0x5306cba..0x5306cbd`) to `obj+0x100..+0x103` at
`0x180ba9c-0x180bab8`, then tail-calls `0x19de890(outer)`. That is hop 1 and already an editor
working copy. Hop 2: `W` is filled by `0x17c8210(manager, id, W)` at `0x180fcb4`, whose copy
`0x17c84d8/0x17c84e4` moves record `+0x140..+0x14f` verbatim. So the chain closes at
**saved-fighter record `+0x142..+0x145`** in two hops. No clamp and no range check on this
path. Other writers of `W`: default-record init `0x17bd350(W)` at `0x180fc58` and `0x22f7e40`
(all four bytes 0), and `0x32e0680(.., [W+0x1d8], W)` at `0x22f8f74` (second store, see below).

**B. Who reads `[obj+0x100..0x103]` after the screen closes.**
The same function `0x180ba20`, exit branch (`[scene+0x14c] != 0`, taken once `[obj+0xe0] == 0`).
`0x180ba58-0x180bb28` compares each `obj+0x100+row` with `W+0x142+row` and stores it into `W`
when different. If any differed it sets `[scene+0x161] = 1` and calls `0x19cb2e0` and
`0x180cf10(scene)`. That is hop 1, landing in the working copy `W`. The value is stored as is;
no range check here.
Hops 2-3 (commit, function `0x180d200`): a temporary 0x64340-byte full record is filled from
the stored one, `0x17bd1b0(temp, W)` overlays `W` (including `+0x140..+0x14f`, `0x17bd2fc`),
and `0x180d9c4-0x180d9d0` memcpys the temp over the manager's stored element
`[[inner]+0] + index*0x64340`, followed by `0x17c7bc0(inner, id)` and `[inner+0xfc] = 1`.
**That store is gated: `0x180d8cc-0x180d8f8` skips it (frees the temp, stores nothing) if any
of `temp+0x142..+0x145` is greater than 2.**

**C. What sets `[obj+0xf8]`.**
`0x180ba94-0x180ba98`: an unaligned 8-byte load from `0x5306cba + 0x5e = 0x5306d18`, which is
**`W+0x1a0`**, the tag-0xc1 key of the working record (record `+0x1a0`). The constructor value
`0xc1ffff0000000000` is only the placeholder.

### Second holder (not the saved-fighter path)

The other constructor caller, `0x1982fc0` (enclosing `0x197fba0`, slot `[scene+0x5e8]`), does the
same thing against a different store, in function `0x1987cb0`:

- entry (`0x1987e10-0x1987eac`): builds a default 0x1B0 record on the stack, fills it with
  `0x32e0680([[0x532e7b0]+8], id = [0x5306d50], sp)`, then copies `sp+0x1a0 -> obj+0xf8` and
  `sp+0x142..+0x145 -> obj+0x100..+0x103`. `0x5306d50` is `W+0x1d8`.
- exit (`0x1987d5c-0x1987f14`): `0x32deaa0` returns a pointer `p` into a table of 0x400-byte
  entries keyed by a u32 at entry `+0`; `p = entry + 0x2b8`. The bytes live at
  **`p+0x13..p+0x16`**. Changed values are written back there with no range check.
- Both readers of that store (`0x32e0cb4-0x32e0cf4`, `0x1987d74-0x1987db0`) replace any value
  greater than 2 with 0.

What this second store is was not analysed (D: another per-entry fighter data set that reuses
the same special-move screen, e.g. a non-saved-Mii context). It is listed because the prompt
required reaching `obj` through both callers.

## Table

| address | instruction | meaning | tier |
|---|---|---|---|
| `0x1809814` | `bl 0x19ddb30` | constructs `outer` for scene 1 | B |
| `0x1809868` | `str x21, [x19, #0x198]` | scene 1 keeps `outer` at `+0x198` | B |
| `0x1982fc0` | `bl 0x19ddb30` | constructs `outer` for scene 2 | B |
| `0x1983014` | `str x23, [x19, #0x5e8]` | scene 2 keeps `outer` at `+0x5e8` | B |
| `0x50a6e20` slots | `0x19dcd90, 0x32cb650, 0x32cb760, 0x32cb7c0, 0x32cb800, 0x19dcd40, 0x19dcdf0` | `obj` vtable; none of the three class-specific methods touches `+0xf8..+0x103` | B |
| `0x50a6f18` slots | `0x19de6c0, 0x19de780, 0x32ca8d0, 0x19de840, 0x19de850, -, -, 0x19dee10, 0x19def10` | `outer` vtable; no access to `obj+0x100..+0x103` in `0x19de6c0..0x19df07c` | B |
| `0x180ba2c-0x180ba38` | `ldr w8,[x0,#0x14c]` / `ldr x9,[x0,#0x198]` / `cbz w8, 0x180ba78` | scene-1 function: counter 0 = entry branch | B; "state-step counter" D |
| `0x180ba88` | `ldr x8, [x9, #0x80]` | `obj` | B |
| `0x180ba8c-0x180ba90` | `adrp/add x9 = 0x5306cba` | `W+0x142` | B |
| `0x180ba94-0x180ba98` | `ldur x10,[x9,#0x5e]` / `str x10,[x8,#0xf8]` | **C:** `obj+0xf8 = W+0x1a0` | B |
| `0x180ba9c-0x180bab8` | 4x `ldrb w, [x9,#k]` / `strb w, [x8,#0x100+k]` | **A hop 1:** `obj+0x100+k = W+0x142+k` | B |
| `0x180bac8` | `b 0x19de890` | start the screen (`outer`) | B; "start" D |
| `0x180fc3c` | `ldr w1, [x10, x9, lsl #2]` | id = u32 list `[x+0x178]`[cursor] | B; "editor list cursor" D |
| `0x180fca8-0x180fcb4` | `x2 = 0x5306b78` / `bl 0x17c8210` | **A hop 2:** saved record -> `W` | B |
| `0x17c84d8`, `0x17c84e4` | `ldp x9,x10,[x8,#0x140]` / `stp x9,x10,[x19,#0x140]` | loader copies record `+0x140..+0x14f` verbatim (0x1B0-array path) | B |
| `0x17bd57c`, `0x17bd588` | `ldp x8,x9,[x20,#0x140]` / `stp x8,x9,[x19,#0x140]` | same for the loader's 0x64340-element path (`0x17c8434 bl 0x17bd420`) | B |
| `0x180fc58` | `bl 0x17bd350` (x0 = `W`) | alternative: default record, bytes 0 | B; "new fighter" D |
| `0x180ba3c-0x180ba44` | `ldr w8,[obj,#0xe0]` / `cbnz` | exit branch waits for `obj+0xe0 == 0` | B; "screen finished" D |
| `0x180ba60-0x180ba6c`, `0x180bacc` | `ldrb w12,[0x5306cba]` / `ldrb w10,[x9,#0x100]` / `cmp` / `strb w10,[0x5306cba]` | **B hop 1:** `W+0x142 = obj+0x100` if different | B |
| `0x180bad8-0x180baec` | same for `#0x101` / `0x5306cbb` | row 1 | B |
| `0x180baf4-0x180bb08` | same for `#0x102` / `0x5306cbc` | row 2 | B |
| `0x180bb10-0x180bb28` | same for `#0x103` / `0x5306cbd` | row 3 | B |
| `0x180bb38-0x180bb4c` | `bl 0x19cb2e0` / `strb 1,[x19,#0x161]` / `bl 0x180cf10` | on change: two calls and a flag | B; "refresh preview, mark dirty" D |
| `0x180d320-0x180d328` | `ldr w1,[0x5306b78]` / `bl 0x17c8530` | commit: is `W`'s id a stored fighter | B |
| `0x180d3c4-0x180d3d4` | `madd x1, idx, 0x64340, base` / `bl memcpy` | temp = stored full element | B |
| `0x180d6e8`, `0x180d704`, `0x180d428` | `bl 0x17bd1b0` (x0 = temp, x1 = `W`) | **B hop 2:** `W` overlaid on temp | B |
| `0x17bd2fc`, `0x17bd308` | `ldp x8,x9,[x20,#0x140]` / `stp x8,x9,[x19,#0x140]` | that overlay copies `+0x140..+0x14f` | B |
| `0x180d8cc-0x180d8f8` | 4x `ldrb w9,[x20,#0x142+k]` / `cmp w9,#2` / `b.hi 0x180d71c` | **store is skipped if any byte > 2** | B |
| `0x180d9c4-0x180d9d0` | `madd x22, idx, 0x64340, base` / `bl memcpy(x22, temp)` | **B hop 3:** temp -> manager's stored element | B |
| `0x180da08-0x180da10` | `bl 0x17c7bc0` / `strb 1,[inner,#0xfc]` | post-store call and flag | B; "refresh 0x1B0 array, mark save dirty" D |
| `0x1987e7c` | `bl 0x32e0680` | scene 2: entry -> stack record | B |
| `0x1987e88-0x1987eac` | `ldr [sp,#0x1a0]` -> `str [obj,#0xf8]`; `ldrb [sp,#0x142+k]` -> `strb [obj,#0x100+k]` | scene 2 entry | B |
| `0x1987db4-0x1987dfc` | `ldrb [obj,#0x100+k]`, compare with clamped `p+0x13+k` | scene 2 exit read | B |
| `0x1987ef4-0x1987f14` | `bl 0x32deaa0` / `strb [x0,#0x13+k]` | scene 2 exit store, no range check | B |
| `0x32e0cb4-0x32e0cf4` | `ldrb [x24,#0x13+k]` / `cmp #2` / `csel wzr,..,hi` / `strb [x19,#0x142+k]` | second store reader clamps > 2 to 0 | B |
| `0x32e0ca4-0x32e0cb0` | `[x24+0x12] -> +0x140`, `[x24+0xa0] -> +0x141` | record `+0x140/+0x141` are separate bytes | B; meaning unknown |

Chain scan used to reach `obj`: `scratch/2026-10-04_P2-SKILL-STORE/chain.py` follows only
`[r,#slot] -> [r,#0x80] -> access`, with register copies tracked. Slot `0x198`: 1 seed hit, slot
`0x5e8`: 9 hits, all in the two functions above. No bare `#0x100` scan was done.

## What this means for the two project questions (D, from the B facts above)

1. **The editor does carry per-saved-fighter bytes.** They are four bytes of the saved record,
   and P1-ID-REVIEW path 2 (C) already shows record `+0x140..+0x198` being copied into the
   per-player entry `G+0x3670 + p*0x1c8`. That block contains `+0x142..+0x145`. Whether the
   match reads them from there is the still-untraced hop from that report.
2. **Values above 2 do not survive the vanilla commit.** The Lua handler and both copies in
   `0x180ba20` accept any byte, so the working record `W` can hold a larger value while the
   editor is open. The commit `0x180d200` then drops the whole store when any byte is above 2.
   So "store a bigger option index in the existing field" does not work without changing that
   gate, and the second store's readers would clamp it to 0 anyway.

## Checks, failures, limits

- `scratch/2026-10-04_P2-SKILL-STORE/check_claims.py`: **88 checks, 0 failures, exit 0**
  (`evidence/P2-SKILL-STORE/18_claim_check.txt`). It re-disassembles every cited instruction
  and re-derives the three offsets (`0x142`, `0x1a0`, `0x1d8`).
- No failed approach to record: the first provenance scan closed both holders.
- Not verified: anything at runtime. Which screen the scene at `0x1808980` is on the console
  (D: the Mii Fighter editor, since it loads `W` through the saved-fighter loader). When and
  from which button `0x180d200` runs (it has callers `0x180a52c`, `0x180aadc`; not read).
  What `0x17c7bc0`, `0x19cb2e0`, `0x180cf10` do. The branch at `0x180d718` that also skips the
  store when byte `[[[0x5313510]]+1]` is non-zero. The meaning of record `+0x140`, `+0x141`,
  `+0x146`, `+0x147`.
- The commit's compare block before `0x180d6a8` (lines 140-300 of
  `evidence/P2-SKILL-STORE/15_commit_fn_0x180d200.txt`) was dumped but only its tail was read;
  it decides whether `[temp+0x90]` is cleared, not whether the bytes are stored.

## Smallest remaining unknown

Does the match-time reader take the specials from the per-player entry that P1-ID-REVIEW found
(`G+0x3670 + p*0x1c8`, G = `0x53040f0`)? The setter `0x179e440` copies record `+0x140..` to
entry-local offsets starting at the local struct's `+0x90`; the exact entry offset of the four
bytes and its reader are not known.

## Closing summary

- **Task ID:** P2-SKILL-STORE
- **Status:** DONE
- **Changed files:**
  - `research/P2-SKILL-STORE.md` (new)
  - `evidence/P2-SKILL-STORE/` (new): `00_input_identity.txt` .. `18_claim_check.txt`
  - `scratch/2026-10-04_P2-SKILL-STORE/` (new): `d.py` (unmodified copy), `rel.py`,
    `chain.py`, `check_claims.py`
- **Observed checks:** input hash matches; 88/88 instruction and offset claims re-derived.
- **Out of scope, noticed:** P1-ID-REVIEW 2.4 describes `+0x140` as a u32 and `+0x144` as a
  u16; this trace shows six separate bytes at `+0x140..+0x145`. That report is another
  worker's file and was not edited.
- **Next experiment:** in `0x17914d0` (`0x1791780-0x17918fc`) and `0x179e440`, find the
  per-player entry offset that receives record `+0x142..+0x145`, then enumerate readers of that
  entry offset with the same provenance-bound method (base register derived from
  `G+0x3670`). One offline task, no console needed.
