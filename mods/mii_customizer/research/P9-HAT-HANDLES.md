# P9-HAT-HANDLES — every consumer of a headgear item handle on the Mii hat screen

Task: **P9-HAT-HANDLES** (Space Bunny Alpha, offline static analysis).

Input: workspace-relative `gamedata/ssbu-13.0.4/main.bin`
sha256 `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`, 86 672 752 bytes
(verified in this task by `sha256sum`; matches P8).
Flat decompressed MOD0 image: **address == file offset**.
Relocation array 0x39C8070..0x40C9FC7, 24-byte `{u64 r_offset, u32 r_info(0x403), u32 pad, u64 r_addend}`.

Tiers: **B** = read out of this image in this task and re-checked by
`evidence/P9-HAT-HANDLES/check_p9_hat_handles.py` (396 claims, 0 mismatches).
**C** = pinned by a prior report (P8-HAT-NATIVE / P6-HAT-UI). **D** = hypothesis.
Nothing was executed, patched or emulated; there are no tier-A claims. Everything
about *runtime* behaviour — which branch is taken for a given handle, what the
game looks like, whether a mod change is safe — is **D**.

---

## 0. Two corrections to P8-HAT-NATIVE, both material

**Correction 1 — the headgear list has its own set of handler addresses.**
P8 reported the handlers as `0x19c1f00` / `0x19c1f50` / `0x19c2110` / `0x19c2160`. Those four
functions are registered by the **outfit** constructor `0x19c7830`. The headgear
constructor `0x19ceb30` registers a **different, near-identical** set at
`0x19cd0b0` / `0x19cd100` / `0x19cd2c0` / `0x19cd310` (B). The two sets are byte-identical
only for their first few bytes, and they differ in a way that matters: the
**headgear** `get_top_index` calls `0x328b5d0` against the registry at
`+0x230`, while the **outfit** one calls `0x3286320` against `+0x240` (B). The P8 addresses
are therefore not the ones that run on the headgear screen.

**Correction 2 — the handle fields live on a 0x170-byte sub-object.**
`0x19ceb30` allocates a 0x170-byte object with `operator new(0x170, 0x10)` at
0x19ceb90 and stores it at `[this+0x80]` (0x19ced0c). The vector at `+0x128` and the
handle slots at `+0x140` / `+0x148` / `+0x150` / `+0x158` are offsets **into that
sub-object**, not into the list object the scene holds (B). Throughout this report
`S` means that sub-object, i.e. `*(scene+0x180) + 0x80`. Both P8 and this task's
prompt wrote `obj+0x128`; the field is right, the base pointer was not stated.

P8 also cited `0x19cb694` as the outfit row filler. `0x19cb694` is in the middle of
a different function (it reads bytes 0..3 of a struct and looks up
`set_item_04` / `set_txt_num_0%d`, 0x19cb6a8/0x19cb6c0). The outfit row filler's
entry was not resolved in this task (D); the headgear one, `0x19ccb20`, is.

Everything else in P8 that this task re-touched (row filler, label builder,
`nam_mii_hat_%s`, the `+0x230` ownership test, the 0x5a handle tag, the 40-bit
hash mask, `SCROLLER_ITEM_NUM` as the total count, `get_decided_item` returning a
row index) re-read correctly.

---

## 1. Q1 — the complete list of code that reads the vector or the handle slots

The class has **no rich vtable**. The list object's vtables `0x50a6c00` (headgear) and
`0x50a69a0` (outfit) hold two slots each, and the sub-object's own vtable `0x50a6ae0`
holds the sub-object's own destructor chain (B). So the methods are free functions
reached by `bl`, by a delegate vtable, or through a scroller callback object.

Scan method: walk 0x19c0000..0x19d2000 and 0x19cd000..0x19d0700, split into
functions by prologue heuristics, and report every function that touches any of
`+0x128 +0x130 +0x138 +0x140 +0x148 +0x150 +0x158 +0x164 +0x168 +0x169` as a
load/store displacement (`scratch/2026-10-05_P9-HAT-HANDLES/scan.py`; output in
`evidence/P9-HAT-HANDLES/20_scan_range_0x19c0000_0x19d2000.txt` and `80_scan_hat_only.txt`).

### 1a. Headgear-side readers (the ones that matter)

| function | what it reads | what it does with the handle |
|---|---|---|
| `0x19CEB30` ctor | writes all | `stp xzr,xzr,[S,#0x128]` zeroes the vector (0x19cece4); fills it with `bl 0x3274c50` from the static table at `[x24+0x58]` (0x19ced28); appends the Mii's current headgear if not already present; initialises `+0x140 +0x148 +0x150 +0x158` to the sentinel `0x5aff_00ff_0000_0000` (0x19cec7c/0x19cec80, stored at 0x19cec88/0x19cec90/0x19ceca4); sets `+0x168 = 0x0100` as a halfword (0x19cec8c) |
| `0x19CCB20` row filler | `+0x128` (vector), `+0x150`, `+0x148`, `+0x169` | indexes the vector by row, compares the row handle against `+0x150` (marker) and `+0x148` (tick), passes the handle to `0x3288330` and `0x328b5d0` — full trace in §2 |
| `0x19CCEA0` row → index | `+0x128`, `+0x169` | `vector[row]` → `0x328b5d0(handle)`; returns `row` if owned and `+0x169 == 0`, else `w3+row` if `w3 > 0`, else `w2` (0x19ccefc..0x19ccf1c) |
| `0x19CD020` row callback | vector at `S+0xe0` (the *scroller's* row array, not `+0x128`), `+0x169` | same ownership test and same slide rule, on the scroller-side row list (0x19cd034/0x19cd070/0x19cd07c) |
| `0x19CD0B0` get_top_index | `+0x128`, `+0x169` | `vector[0]` → `0x328b5d0` against `+0x230`; returns 1 if owned **and** `+0x169 == 0`, else 0 — full text in §7 |
| `0x19CD100` sort_id_list | `+0x128 ×7`, `+0x130`, `+0x138`, `+0x164 ×3`, `+0x158` | writes the sort mode, then tail-calls a sort body with `x0 = begin`, `x1 = end` — full text in §7 |
| `0x19CD590` sort mode 0 body | the two vectors | merges in place; calls `0x19ce440` repeatedly (a merge step) |
| `0x19CD9D0` sort mode 1 body | the two vectors | same shape, calls `0x19cde10` |
| `0x19CE730` / `0x19CE100` | the two vectors | comparator/key extraction called from the mode-0 / mode-1 bodies (0x19cd64c / 0x19cda8c) |
| `0x19CD2C0` backup | `+0xf8` scroller, `+0x2a4`, `+0x128`, writes `+0x158` | `vector[scroller->selected]` → `+0x158`; sentinel on `-1`; `0x39c0d80` on out-of-range — full text in §1b |
| `0x19CD310` select-from-backup | `+0x158`, `+0x128` | linear search of the vector for the backup handle, then `bl 0x3783660` on the scroller — full text in §1b |
| `0x19CC3F0` list frame callback | `+0x128`, `+0x140`, `+0x2a4`, `+0x148`, `+0x169` | per-frame: reads the scroller's selected row, indexes the vector, compares against `+0x140`, calls `get_decided_id` on the Lua layout, converts the returned index to a handle and stores it at `+0x148` (0x19cc6c4) — §4/§5 |
| `0x19CFE00` entry / set_select_id | `+0x128`, writes `+0x140`, `+0x150`, `+0x168`, `+0x169` | §6 |
| `0x19CCA40`, `0x19CCAB0` | `+0x128` | destructor variants: free the buffer, tear down `+0x100` and the scroller |

### 1b. The two backup handlers in full

`0x19CD2C0` — `backup_list_selected_id` (26 words, 0x19cd2c0..0x19cd30c):

```
0x019cd2c0: ldr   x8, [x0, #0xf8]        ; the scroller object
0x019cd2c4: ldrsw x8, [x8, #0x2a4]       ; scroller selected row, s32
0x019cd2c8: cmn   w8, #1                ; -1 ?
0x019cd2cc: b.eq  0x19cd2f0             ; -> store the sentinel
0x019cd2d0: ldp   x9, x10, [x0, #0x128]  ; vector begin/end
0x019cd2d4: sub   x10, x10, x9
0x019cd2d8: asr   x10, x10, #3          ; count
[13 lines of game disassembly removed for publication; regenerate them from your own 13.0.4 main with this report's check script]
```

`0x19CD310` — `select_list_from_backup_id` (0x19cd310..0x19cd3ac): reads `+0x158`,
rejects the sentinel (tag ≠ 0x5a or hash 0) at 0x19cd320/0x19cd32c, then linear-searches
the vector for a handle whose 40-bit hash matches (`eor`+`tst #0xffffffffff` at
0x19cd368/0x19cd374). On a match it falls into 0x19cd39c and calls
`0x3783660` with `x0 = [x0+0xf8]` (the scroller), `w1 = the matched index`,
`w2 = 0`, `w3 = 1`. On no match, empty vector, or sentinel it returns without
calling anything.

### 1c. The four handle slots, and who writes each

| slot | initial value | written by | read by |
|---|---|---|---|
| `+0x140` | sentinel | `0x19cfe00` (entry, `stp x1,x1`), ctor | `0x19cc3f0` (frame cb, 0x19cc468), `0x19cffa8` (fallback), scene `0x180ac34` (copies it into the static) |
| `+0x148` | sentinel | `0x19cc3f0` at 0x19cc6c4 (from the decided row), ctor | `0x19ccb20` (tick bit, 0x19ccc70), `0x19cc3f0` (compare, 0x19cc468 region), scene `0x180acbc` |
| `+0x150` | sentinel | `0x19cfe00` (entry, 0x19cfe1c), ctor | `0x19ccb20` (marker, 0x19ccb5c), scene `0x180ad38` |
| `+0x158` | sentinel | `0x19cd2c0` (backup), ctor | `0x19cd310` (select-from-backup) |

`+0x148` is **not** in P8's field list. It is the "currently previewed" handle: the
frame callback writes it from the decided row, the row filler uses it to set the
tick, and the scene compares it against the static to decide whether to redraw
the preview. This is the field a mod would most plausibly have to keep coherent
(§4, §5).

### 1d. The Lua bridge thunks registered in the constructor

Each of the four bridges is a heap delegate object whose vtable has the shared
deleter at slot 0, a destructor at slot +0x08, and the **Lua-facing method thunk**
at slot +0x10. The delegate's `+0x10` field holds the sub-object pointer, so the
thunk reaches the handlers with `x0` already corrected.

| bridge name (string addr) | delegate vtable | slot +0x10 thunk | handler it tail-calls |
|---|---|---|---|
| `get_top_index` (0x4290580) | `0x50a6b88` | `0x19cea80` | `0x19cd0b0` |
| `sort_id_list` (0x427f3a7) | `0x50a6bb0` | `0x19cd460` | `0x19cd100` |
| `backup_list_selected_id` (0x44541fe) | `0x50a6bd8` | `0x19cd3d0` | `0x19cd2c0` |
| `select_list_from_backup_id` (0x441204c) | `0x50a6bd8` | `0x19cd3d0` (same thunk) | `0x19cd310` |

Registration is `bl 0x3376540` at 0x19cf61c / 0x19cf6c4 / 0x19cf770 / 0x19cf814
(B). The thunk at slot +0x10 does the Lua stack push and `br x2` / `br x8` into
the handler — see §7 for the two that were read in full.

### 1e. The row-filler callback object

P8 left the owner of the row-filler thunk unresolved. It is **vtable `0x50a6b18`**,
identified from the typeinfo/method table at 0x3cf48d8
(`{0x50a6b18, 0x403, 0x19ccb20}`, B). Full slot map (B, from the RELA array):

| slot | method |
|---|---|
| +0x00 | `0x19ccb20` row filler |
| +0x08 | `0x19ccea0` row → index |
| +0x10 | literal `0xffffffffffffffb8` (= −0x48; the thunk's own adjustment, inlined as data) |
| +0x20 | `0x19ccf30` destructor |
| +0x28 | `0x19ccfa0` destructor variant |
| +0x30 | `0x19cd010` thunk `sub x0,x0,#0x48; b 0x19ccb20` |
| +0x38 | `0x377c0d0` (generic) |
| +0x40 | `0x377c0e0` (generic) |
| +0x48 | `0x19cd020` row slide callback |

**Who installs it is not resolved (D).** No `adrp`+`add` or relocation record in
the image points at `0x50a6b18` as a value, and the object is not reachable from
the constructor's own stores. The scroller builder `0x3781470` takes a callback
object in `x4`, and the ctor passes `x25` (the sub-object) — so this vtable belongs
to a *different*, not-yet-identified object. Open, see §9.

---

## 2. Q2 — the row filler `0x19ccb20`, every call in order

Entry: `x0` = the list object as adjusted by the −0x48 thunk (so `x0` points at the
field block whose `+0x128` is the vector), `w1` = the row index, `x2` = the row's
layout node. All of §2 is B from `evidence/P9-HAT-HANDLES/50_row_filler_0x19ccb20.txt`.

| # | address | call / action | depends on |
|---|---|---|---|
| 1 | 0x19ccb3c | `ldp x9,x10,[x0,#0x128]`; count = `(end−begin)>>3`; `cmp`/`b.ls` → 0x19cce98 | the **vector** |
| 2 | 0x19ccb58 | `ldr x20,[x9,x8,lsl #3]` — the row's handle | the **vector** |
| 3 | 0x19ccb5c | `ldr x8,[x19,#0x150]` — the selected handle | **`+0x150`** |
| 4 | 0x19ccb90/0x19ccbbc | `ldr x0,[x22,#8]` then `add x1,…#0xe2f` `"selecteditem"` **or** `add x1,…#0x3d3` `"notselecteditem"`, `fmov s0,#1.0`, **`bl 0x3777d50`** | **`+0x150` vs the row handle** (equal 40-bit hash ⇒ selected) |
| 5 | 0x19ccbdc | `ldr x1,[x8,#0x238]` — the name registry | only the **row node** |
| 6 | 0x19ccbec | `add x0,sp,#0x18; mov x2,x20;` **`bl 0x3288330`** — the label builder, `x2` = the row handle | **the handle** |
| 7 | 0x19ccc00 | `add x1,…#0x382` `"set_txt_val"`; `add x8,sp,#8; mov x0,x22` — **`bl 0x3776360`** (find the part under the row) | only the **row node** |
| 8 | 0x19ccc10 | **`bl 0x3779b70`** — set the text from the struct built in step 6 | indirectly the **handle** |
| 9 | 0x19ccc3c | `"set_txt_val_disable"`, **`bl 0x3776360`** | only the **row node** |
| 10 | 0x19ccc48 | **`bl 0x3779b70`** — the *same* text struct, second part | indirectly the **handle** |
| 11 | 0x19ccc6c | `"selected"`, **`bl 0x3776360`** | only the **row node** |
| 12 | 0x19ccc70 | `ldr x8,[x19,#0x148]`; compare its 40-bit hash against the row handle's (0x19ccc98 `eor` + `tst #0xffffffffff`) | **`+0x148` vs the handle** |
| 13 | 0x19cccc4/0x19ccce0/0x19ccce4 | `ldrb w9,[x8,#0x58]`, then `and #0xfe` (clear) or `orr #1` (set), `strb` | **`+0x148`** |
| 14 | 0x19ccce8 | `mov w0,#0x10; mov w1,#8;` **`bl 0x392dce0`** — allocate the 8-byte row icon cell | neither |
| 15 | 0x19ccd54 | `ldr x0,[x8,#0x60]` — the owner; `ldr x8,[x8,#0x18]`; `add x1,x8,#0xb0`; **`bl 0x3796970`** | only the **row node** |
| 16 | 0x19ccd70 | `str x0,[x23]` — the cell's object pointer | neither |
| 17 | 0x19ccd7c | `add x0,x8,#0x230`; `mov x1,x20`; **`bl 0x328b5d0`** — the ownership test on the row handle | **the handle** |
| 18 | 0x19ccd8c | `ldrb w8,[x19,#0x169]` — the mode flag | **`+0x169`** |
| 19a | 0x19ccd9c | `ldr x8,[x19]`; `ldr x8,[x8,#0x1f8]`; `mov w1,#1`; **`blr x8`** — owned **and** `+0x169 == 0` | **handle + `+0x169`** |
| 19b | 0x19ccdb8 | `ldr x8,[x8,#0x200]`; **`blr x8`** — returns a bool that selects branch 19c/19d | **handle** |
| 19c | 0x19ccdcc | `ldr x8,[x8,#0x210]`; **`blr x8`**; `eor w20,w0,#1` | **handle** |
| 19d | 0x19ccde0 | `ldr x8,[x8,#0x388]`; `and w1,w20,#1`; `mov w2,wzr`; **`blr x8`** | **handle** |
| 19e | 0x19cce2c | the mirrored sequence with `w1 = 0` for the *unowned* case, same slots 0x1f8/0x200/0x210/0x388 | **handle + `+0x169`** |
| 20 | 0x19ccdf8, 0x19cce08 | `bl 0x392e590` — free the two scratch objects | neither |
| 21 | 0x19cce28 | `ret` | — |

Bounds failure at 0x19cce98: `add x0,x0,#0x128; bl 0x39c0d80` — the standard
out-of-range `std::vector` accessor trap. It is reached by `b.ls` from step 1 when
`row >= count`, so it does **not** fire for a handle that is merely unknown, only
for an out-of-range row number.

**Which calls depend on the handle:** 2, 3, 4, 6, 8, 10, 12, 13, 17, 18, 19a–19e.
**Which depend only on the row node:** 7, 9, 11, 15.
**Neither:** 14, 16, 20.

**Is there an icon or thumbnail per row?** Yes — steps 14–19e. The filler allocates
an 8-byte cell, obtains a texture handle from the row node's owner
(`[owner+0x60]`, argument `owner+0x18 + 0xb0`, `0x3796970`), and then drives four
virtual slots on the cell: `+0x1f8`, `+0x200`, `+0x210`, `+0x388`, with `w1 = 1` for
an owned item and `w1 = 0` for an unowned one, and `w2 = 0` in both cases. The
texture itself is **not** derived from the handle — it comes from the row node.
The handle only selects which of the two slot-call sequences runs.

---

## 3. Q3 — what happens with an unknown handle

All three are B, from `evidence/P9-HAT-HANDLES/60_label_builder_0x3288330.txt`,
`61_fn_0x328b5d0.txt`, `62_fn_0x3286320.txt`.

### `0x3288330` (hat label builder) — produces the literal string **`unknown`**

There are two rejection gates: a bad tag at 0x328835c (`b.ne 0x32883f0`) and a zero
hash at 0x3288368 (`cbz 0x32883f0`). Both land at 0x32883f0. A well-formed handle
that is simply **absent from the registry** reaches the fallback at 0x32885a0
instead, and the fallback writes a 7-character string:

```
0x032885a0: mov   x9, #0x700000000       ; length 7
0x032885a8: mov   x9, #0x6e75            ; "un"
0x032885ac: movk  x9, #0x6e6b, lsl #16   ; "kn"
0x032885b8: movk  x9, #0x776f, lsl #32   ; "ow"
0x032885bc: movk  x9, #0x6e,   lsl #48   ; "n"
```

then hashes it in place with the same FNV-style loop (seed `0x811c9dc5`, prime
`0x89`, at 0x32885c4/0x32885c8/0x32885d8) and branches to the common tail at
0x32886ec, which formats `nam_mii_hat_%s` (0x42a06fe) via `bl 0x3a4ca0`.

So an unknown handle yields the message key **`nam_mii_hat_unknown`**. It does not
empty the label, does not use a different default, and does not trap. **This is the
single most useful fact in this report for a mod-mode list**: a synthetic handle
gets a readable, non-crashing label with no registry work at all.

> **Coordinator correction 2026-10-06:** the conclusion of this subsection is inverted.
> `cmp w8, w20 ; cset w0, ls` is true for `w20 = 0xffffffff`, so an absent handle
> returns **1**; the function answers "not in the table". Callers that see 1 take the
> unavailable / unlisted branch. Sections 2, 7 and 8 use the old reading.

### `0x328b5d0` (registry contains, 0x5a tag) — returns 0

Gates: tag must be `0x5a` (0x328b5f0/0x328b5f4) and the 40-bit hash must be
non-zero (0x328b600). A failing gate jumps to 0x328b688, which sets `w20 = −1`.
Otherwise it calls `0x3269fd0` (0x328b6ec) and keeps its return in `w20`. The
function then ends:

```
0x03287a0: cmp   w8, w20
0x03287a4: ldp   x29, x30, [sp, #0x30]
0x03287a8: ldp   x20, x19, [sp, #0x20]
0x03287ac: cset  w0, ls
0x03287b0: ldp   x22, x21, [sp, #0x10]
0x03287b4: ldp   x24, x23, [sp], #0x40
0x03287b8: ret
```

`w8` is a bound taken from the `0x4741dbb` static (0x328b77c/0x328b780/0x328b784/0x328b794),
`w20` is the index `0x3269fd0` returned. `cset w0, ls` on an **unsigned** compare
means: return 1 iff `w8 <= w20`. `0x3269fd0` returns `-1` (0x326a000) when the
table is empty and 0x326a020 sets `w0 = -1` on a hash miss, so an absent handle
yields `w20 = 0xffffffff` and the compare is false. **Result: 0, no trap, no side
effect.** A caller seeing 0 takes the "not owned" branch.

### `0x3286320` (registry contains, 0x13 tag) — identical shape, returns 0

Same function with the tag constant `0x1300000000000000` instead of
`0x5a00000000000000` (0x328633c), the same `0x3269fd0` call (0x328643c), and the
same `cset w0, ls` / `ret` ending (0x32864f0/0x32864fc/0x3286508). Gates at
0x3286344 (tag) and 0x3286350 (hash) both fall to 0x32863d8, which also sets
`w20 = −1`. **Result: 0, no trap.** This is the *outfit* screen's test, so a mod
that only replaces the headgear list never reaches it — but it is listed for
completeness because P8 cited it for headgear.

---

## 4. Q4 — cursor movement and the preview

**The per-frame path is `0x19cc3f0`, the sub-object's frame callback** (stored at
`[S+0x88]` by the ctor at 0x19cecec, B). It is not reached through a rich vtable;
it is the callback the list hands to its host. It is 0x510 bytes long: the last
`ret` is at 0x19cc8fc, so the body is 0x19cc3f0..0x19cc900. The words from
0x19cc900 to 0x19cc910 are the out-of-range tail
(`add x0,x19,#0x128; bl 0x39c0d80; bl 0x39c20a0` at 0x19cc900/0x19cc904/0x19cc908)
followed by `udf` alignment padding at 0x19cc90c.

It notices a selection change like this (0x19cc448..0x19cc498):

```
0x019cc448: ldr   x22, [x19, #0xf8]     ; the scroller
0x019cc44c: ldp   x8, x9, [x19, #0x128]  ; the vector
0x019cc450: ldrsw x20, [x22, #0x2a4]    ; the scroller's SELECTED row
0x019cc454: sub   x9, x9, x8
0x019cc458: asr   x9, x9, #3            ; count
[15 lines of game disassembly removed for publication; regenerate them from your own 13.0.4 main with this report's check script]
0x019cc498: eor   x8, x1, x21
0x019cc49c: tst   x8, #0xffffffffff
0x019cc4a0: b.ne  0x19cc73c              ; CHANGED -> do the work
0x019cc4a4: b     0x19cc88c              ; unchanged -> exit
```

So the change test is a **40-bit hash comparison between the scroller's selected
row's handle (`vector[+0x2a4]`) and the stored previous handle at `+0x140`**, with
tag-validity guards on both sides. It is not a comparison of `+0x2a4` against a
stored row number.

**The apply call.** When they differ, the code reaches 0x19cc73c, which is inside
the same function; the ownership test `bl 0x328b5d0` is at 0x19cc754 with
arguments `x0 = [reg+8] + 0x230`, `x1 = the new handle` (x19+0x140 region). On
success (0x19cc550 onward) it clears `+0x169`, then walks the animation part array
at `[scroller+0x168]`, setting bit 0 of each part's `+0x58` flag and clearing
`+0x30`, and calls slot `+0x10` on the object at `[scroller+0x160]` for each part
(0x19cc5d4/0x19cc5dc), then slots `+0x18` and `+0x20` (0x19cc5fc). This is the
Mii-model animation change, and it is **keyed on the handle's presence in the
`+0x230` registry, not on the handle's value** (B for the instruction sequence,
D for what it looks like).

**The two callers of the frame callback's decision path.** The frame callback also
asks the Lua layout for a decision: `ldrb`/`cmp` on the stack at 0x19cc4a8..0x19cc4d8
walks the Lua stack looking for `get_decided_id` (0x43de9d8), calls
`0x38f4a10` / `0x38f4570` for a miss and `bl 0x38f4790` for a hit (0x19cc660).
The returned index is bounds-checked against the vector at 0x19cc6a8..0x19cc6bc
and, if in range, converted to a handle and stored at `+0x148` (0x19cc6c0/0x19cc6c4).
That is the write §5 picks up.

**Where the frame callback is pumped from** is **not** resolved (D). It is stored
as raw data at `[S+0x88]` and has no `bl` callers in the image, so it is invoked
through a function pointer held by the list host. The scroller's own frame function
`0x377d290` (from P8) maintains `+0x2a0` / `+0x2a4` / `+0x2b4`; that is C from P8,
not re-verified here.

---

## 5. Q5 — the decision, and where the handle reaches the Mii record

**The headgear working slot is the static at `0x5306cb0`, not `0x5306b78`.**
`0x5306b78` is the editor working record P4/P6 identified, and `0x5306cb0` sits
inside it: 0x5306cb0 − 0x5306b78 = 0x138. The headgear handle is its 8-byte field
at `+0x138`. All eleven code references to `0x5306cb0` in the image were enumerated
(`evidence/P9-HAT-HANDLES/74_xref_0x5306cb0.txt`, B):

| address | role |
|---|---|
| 0x18094b4 | **entry**: `ldp`/`ldr` from `0x5306cb0` into `sp+0xb8..0x110`, then a `new(0x88)` — the screen state is seeded from the static when the Mii editor scene is built |
| 0x180b058 | **entry**: `ldr x1,[0x5306cb0]`, `ldr x0,[S]`, `bl 0x19cfe00` — positions the list on the Mii's current headgear (§6) |
| 0x1809c2c | reads the static into a comparison (`lsr x8,x20,#0x38`, `cmp x8,#0x5a`) — a tag check on the same handle elsewhere in the scene |
| 0x19cb3e8 | inside `0x19cb2e0`: `ldr x2,[0x5306cb0]` then `bl 0x3288330` — **the preview label is built from the static's handle**, not from `+0x148` |
| 0x180ac38/0x180ac3c | **the preview write** (§5 chain step 2) |
| 0x180acc4 | the comparison that triggers it |
| 0x180b058 → 0x19cfe00 | as above |
| 0x180d4cc | reads the static and compares it against `[x20+0x138]` — the commit check |
| 0x180d734 | reads the static again in the same function |
| 0x1812b4c, 0x1815094 | read the static's first field and `+0x68` for an unrelated call to `0x33115f0` (0x1812b70 / 0x18150b8) — different screens, same record |

### The chain from the list object to the write

1. **Lua** calls `scroller.get_decided_item()`; the scroller returns the row index
   from `[scroller+0x2b4]` (C, P8). The layout stores it in `self.decided_id` and
   leaves its state (C, P6 §4.6).
2. **Native frame callback `0x19cc3f0`** finds `get_decided_id` on the Lua layout,
   calls it (0x19cc660), bounds-checks the index against the vector
   (0x19cc6a8..0x19cc6bc) and stores the resulting **handle** at `+0x148`
   (0x19cc6c0/0x19cc6c4).
3. **Scene state handler `0x180abd0`** compares `+0x148` with the static
   (0x180acbc `ldr x10,[x8,#0x148]`, 0x180acc4 `ldr x15,[0x5306cb0]`), doing the
   same 40-bit-hash-with-tag-guards test as §4 (0x180acc8..0x180ae20). On a
   difference it **writes the handle into the static**:
   `0x180ad1c: mov x0,x19; 0x180ad20: str x10,[x11,#0xcb0]; 0x180ad24: bl 0x180cf10`
   (B, `73_scene_state_0x180abd0.txt`).
4. It also calls **`0x19cb2e0`** (0x180add4), which rebuilds the on-screen labels
   from the static (0x19cb3e8) and, at 0x19cb47c, from the body static via the
   `nam_mii_body_%s` builder `0x32842e0`.
5. `0x180cf10` is the guard-and-commit tail (0x180ac54 tail-calls it): it checks
   `scene+0x163` (already committed?), then pushes a *different* static,
   `0x5306ca8`, through `0x33115f0` and sets `scene+0x163 = 1` (0x180d010).

So: the decided row becomes a handle at `+0x148`, the handle reaches the Mii's
headgear field through the **static `0x5306cb0`**, and the visible model is redrawn
by `0x19cb2e0` plus the animation-part walk in the frame callback.

**The commit out of the static into the save is not fully traced (D).** 0x180d4cc
and 0x180d734 read the static and compare it against `[x20+0x138]`; the actual
save write is in the function containing 0x180d4c4, which this task did not walk
end to end. What *is* B: `0x17bd1b0` (called at 0x180d428, 0x180d6e8, 0x180d704)
copies the *special-skill* bytes from `0x5306b78`, **not** the headgear field — it
touches `+0x118..+0x12a` of the destination and is not part of the hat path.

### Cancel

**Cancel does not restore the previous headgear through this path (D).** P6 §4.2
(C) established that cancel is `ComFrameActor.press_cancel()` from Lua, which
does not read the decided row. The only restore-shaped native code found is
`backup_list_selected_id` / `select_list_from_backup_id` (`0x19cd2c0` /
`0x19cd310`), and P6 §3.1 shows Lua calls the second **only on the cancel branch
of the sub-list-window state** (p13 pc40) — that is the *sort* window's cancel, not
the screen's. On the main screen the confirmed path is p11 pc1–p9: cancel →
`press_cancel()` → `state.set(STATE_UPDATE_SUB_LIST_WINDOW)`. Whether leaving the
screen restores the pre-screen headgear, and if so where, is **not resolved**;
the candidates are the `+0x140` slot (which holds the entry value) and 0x180cf10's
once-per-scene commit. This is the largest open item in this report.

---

## 6. Q6 — entry: positioning the list on the Mii's current headgear

The call is at **0x180b058/0x180b060**: `ldr x1,[0x5306cb0]`, `ldr x0,[x8,#0x80]`,
`bl 0x19cfe00` (B). The value passed is **the raw 8-byte headgear handle straight
out of the static** — no index, no lookup, no conversion.

`0x19cfe00` (`subobj, handle`) does the conversion (B,
`76_fn_0x19cfe00.txt`):

```
0x019cfe10: ldp   x10, x8, [x0, #0x128]  ; the vector
0x019cfe18: stp   x1, x1, [x0, #0x140]    ; +0x140 = handle (previous)
0x019cfe1c: str   x1, [x0, #0x150]        ; +0x150 = handle (selected)
0x019cfe24: strb  wzr, [x0, #0x168]       ; clear the halfword flag
0x019cfe28: b.eq  0x19cffdc               ; empty vector -> fallback
0x019cfe2c..0x19cfe94:                    ; linear scan of the vector
0x019cfe98:                                ; found it
   ... push a Lua object, then either
0x019cfed8:  add x1,…#0xd26 "set_select_id"  -> bl 0x38f4570  (0x19cfee0)   miss
   or
0x019cff60:  add x2,…#0xd26 "set_select_id"  -> bl 0x38f4790  (0x19cff68)   hit
0x019cffdc:                                ; fallback: not in the vector
0x019cffe8:  ldr x1, [x19, #0x140]
0x019cffec:  add x0, x8, #0x230
0x019cfff0:  bl 0x328b5d0
0x019cfff4:  and w8, w0, #1
0x019cfff8:  strb w8, [x19, #0x169]        ; +0x169 = owned?
```

So the value given to `set_select_id` is **the handle's own index in the vector**,
found by a linear scan comparing 40-bit hashes with tag guards
(0x19cfe40..0x19cfe94). If the handle is not in the vector, `set_select_id` is
still called (the miss branch at 0x19cfed8/0x19cfee0) and `+0x169` is set from
`0x328b5d0` on the handle. The other caller of `0x19cfe00` is 0x19873d4, which
builds the handle first with `bl 0x32892b0` from `[reg+0x238]` and
`[x0+0x9c]` (0x19873b8/0x19873bc/0x19873c8) — that is the other Mii list screen
(B for the call shape, D for which screen it is).

---

## 7. Q7 — `get_top_index` in full, and the `sort_id_list` thunk

### `0x19cd0b0` — `get_top_index` handler, 20 words, complete

```
[20 lines of game disassembly removed for publication; regenerate them from your own 13.0.4 main with this report's check script]
```

**Returns 1** iff `vector[0]` is in the `+0x230` registry **and** `+0x169 == 0`.
**Returns 0** otherwise, including on an empty vector (where `ldr x1,[x8]` reads
`vector_begin[0]` on an empty allocation — a latent read past the end if the vector
is empty; whether the ctor can leave it empty is **D**). It reads only
`vector[0]`, not the scroller's top index — so the name is misleading and P8's
"returns 0 or 1, looks incomplete" is right about the value but wrong about the
cause: the *decision* is about the first row's ownership, not about scrolling.

P8 reported the outfit twin `0x19c1f00` as calling `0x3286320` against `+0x240`;
that is B for the outfit class and does not run on the hat screen.

### `0x19cd460` — the `sort_id_list` Lua thunk, argument read and return

```
[20 lines of game disassembly removed for publication; regenerate them from your own 13.0.4 main with this report's check script]
...
0x019cd4f4: mov   x1, xzr                 ; DEFAULT: x1 = 0
0x019cd4f8: ...                            ; grow the Lua stack by 1
0x019cd52c: ldp   x8, x2, [x19, #0x10]   ; x0 = sub-object, x2 = handler
0x019cd530: ldr   x9, [x19, #0x20]
0x019cd534: add   x0, x8, x9, asr #1
0x019cd544: ldp   x29, x30, [sp, #0x30]
0x019cd554: br    x2                     ; TAIL-CALL the handler
```

and the float branch, for a Lua number argument:

```
0x019cd558: ldr   s0, [x21]
0x019cd560: ldr   s1, [0x44718f4]         ; lower bound
0x019cd564: frintm s0, s0
0x019cd568: fcmp   s0, s1
0x019cd56c: b.lt   0x19cd4f4             ; below range -> 0
0x019cd570: ldr   s1, [0x4471e68]         ; upper bound
0x019cd578: fcmp   s0, s1
0x019cd57c: b.pl   0x19cd4f4             ; above range -> 0
0x019cd580: fcvtzs x1, s0                ; else truncate to integer
```

So: **the mode argument is read off the top Lua stack slot**, with integer → float →
string-coercion → default-0, and the float is range-checked against two constants
before truncation. The thunk then **tail-calls the handler and returns nothing to
Lua** — no stack slot is pushed for a result. That matches P6 §3.1 (0 results for
all three `sort_id_list` sites, C).

The `get_top_index` thunk `0x19cea80` is the contrasting shape: it reserves one
stack slot (`str wzr,[x9,#8]` at 0x19ceaa8, growing to `+0x10` at 0x19ceac0),
tail-calls the handler, and pushes `sxtw w0` as a **LUA_TINTEGER (tag 0x13)**
(0x19ceaf0/0x19ceaf4/0x19ceaf8), then returns 1 (0x19ceb14 `ret` after the stack
bump). One result, matching P6 §3.1 (C).

---

## 8. Q8 — what a mod-mode list would have to neutralise

Facts and stated uncertainty only; this is not a design.

| # | consumer | entry | argument registers at entry | first four words (hex) | PC-relative? | skipping it: return value, and is it harmless from callers' use? |
|---|---|---|---|---|---|---|
| 1 | ctor | `0x19ceb30` | `x0` = this, `x1`/`x2` = host tables | `0xa9ba6ffc 0xa90167fa 0xa9025ff8 0xa90357f6` | no | no return value. **Not skippable**: it allocates the sub-object the scene stores at `scene+0x180`, so skipping it leaves a null pointer that 0x180abf4 dereferences |
| 2 | row filler | `0x19ccb20` | `x0` = list object (thunk already applied −0x48), `w1` = row index, `x2` = row node | `0xd10303ff 0xa90767fa 0xa9085ff8 0xa90957f6` | no | no return value; the row's panes are simply never filled. **Looks harmless** — the only callers are scroller-side vtable dispatches that use nothing afterwards. Rows would render blank, not crash (D) |
| 3 | row → index | `0x19ccea0` | `x0` = list object, `w1` = row, `w2`/`w3` = fallbacks | `0xa9bd57f6 0xa9014ff4 0xa9027bfd 0x910083fd` | no | returns `w0`, consumed by the scroller as a row index. Returning 0 keeps the cursor on row 0 and never leaves range, so the value cannot be used to index out of bounds (D). Returning 0 is the safe choice (D) |
| 4 | row slide cb | `0x19cd020` | `x0` = list object, `w1` = row, `w2`/`w3` = fallbacks | `0xa9bd57f6 0xa9014ff4 0xa9027bfd 0x910083fd` | no | same shape as #3; returns `w0` as a row index. Return 0 (D) |
| 5 | get_top_index | `0x19cd0b0` | `x0` = this (sub-object) | `0xf81e0ff3 0xa9017bfd 0x910043fd 0xb001cb08` | **yes — word 3 (0x19cd0bc) is `adrp x8,#0x532e000` and must be rebased** | returns 0 or 1. The Lua thunk pushes it as an integer, and P6 §4.4 (C) shows the script feeding it straight to `scroller.select_item(idx, true)`. Return 0 keeps the cursor at the top (D). Note the thunk's register order: the value is pushed via `sxtw`, so a return of 0 is passed as 0, not as a bool (B) |
| 6 | sort_id_list | `0x19cd100` | `x0` = this, `w1` = mode, Lua args on the stack | `0xd101c3ff 0xa9035ff8 0xa90457f6 0xa9054ff4` | no | returns nothing to Lua (the thunk pushes no result, §7). Skipping the whole handler leaves `+0x164` at whatever it was and leaves the vector in its current order — **looks harmless** (D). Note `cbnz w1,0x19cd280` at 0x19cd12c already rejects any mode ≥ 3 by returning with no write, so mode validation exists |
| 7 | backup | `0x19cd2c0` | `x0` = this | `0xf9407c08 0xb982a508 0x3100051f 0x54000120` | no | returns nothing. If skipped, `+0x158` keeps its previous value; the only consumer, #8, would then restore the wrong row. **Not harmless** unless #8 is also neutralised (D) |
| 8 | select-from-backup | `0x19cd310` | `x0` = this | `0xa9bf7bfd 0x910003fd 0xf940ac09 0xd2eb4008` | no | returns nothing. If skipped, the scroller is never repositioned — **looks harmless** for a mod list, but it is also the cancel-restore path (P6 §3.1, C) so skipping it changes cancel behaviour (D) |
| 9 | sort_id_list thunk | `0x19cd460` | `x0` = delegate, `x1` = lua_State | `0xd10103ff 0xf9000bf5 0xa9024ff4 0xa9037bfd` | no | returns 0 results. If it returns immediately without tail-calling, Lua sees no result and no error — matching the declared 0-result form (B for the form, D for the outcome) |
| 10 | get_top_index thunk | `0x19cea80` | `x0` = delegate, `x1` = lua_State | `0xf81e0ff3 0xa9017bfd 0x910043fd 0xf9401028` | no | must push exactly one integer or the script's stack arity breaks (C from P6: 1 result used). **Not skippable**; the handler must still be entered. Returning 0 with the slot pushed is safe (D) |
| 11 | set_select_id | `0x19cfe00` | `x0` = sub-object, `x1` = the handle from `0x5306cb0` | `0xa9bd57f6 0xa9014ff4 0xa9027bfd 0x910083fd` | no | returns nothing, but it also writes `+0x140` and `+0x150`, which #1, #5 and the scene all read. **Not skippable**; skipping it leaves the previous entry's handles in place, and `+0x140` is what the frame callback compares against to detect a change (§4) |
| 12 | frame callback | `0x19cc3f0` | `x0` = this | `0xa9bc5ff8 0xa90157f6 0xa9024ff4 0xa9037bfd` | no | returns nothing (last `ret` at 0x19cc8fc). Skipping it stops the `+0x148` write, so #14 never sees a change and the preview never updates. **Not skippable if the preview must work** (D) |
| 13 | preview label refresh | `0x19cb2e0` | `x0` = scene-owned object | `0xd10583ff 0xfd007be8 0xa9106ffc 0xa91167fa` | no | returns nothing; it only writes text into panes. **Looks harmless** (D) |
| 14 | scene preview apply | `0x180abd0` | `x0` = scene | `0xa9bc5ff8 0xa90157f6 0xa9024ff4 0xa9037bfd` | no | returns nothing, but it is the **only** writer of `0x5306cb0` found (0x180ad20). Skipping it means the Mii's headgear field never changes — which for a mod list is arguably the goal, but it also skips the `+0x164`→`scene+0x1c8` copy (0x180adec/0x180adf0) and the `+0x144` decrement (0x180adf4..0x180ae00) (B for the sequence, D for the effect) |
| 15 | hat label builder | `0x3288330` | `x8` = sret label struct, `x1` = registry, `x2` = the handle | `0xd102c3ff 0xf90033f9 0xa9075ff8 0xa90857f6` | no | returns nothing. **Shared with the outfit screen** (0x32842e0 is its twin) but this entry is hat-only by the format string. Skipping it leaves the row's label struct uninitialised — the caller then passes it to `0x3779b70` at 0x19ccc10 (D) |
| 16 | registry contains (0x5a) | `0x328b5d0` | `x0` = a table object, `x1` = the handle | `0xa9bc5ff8 0xa90157f6 0xa9024ff4 0xa9037bfd` | no | returns 0 or 1 in `w0`, tested by every caller. Returning **1** (owned) makes all rows take the owned branches: #2's cell sequence with `w1 = 1`, #5's `get_top_index` → 1, #4's no-slide path, #12's apply path. Returning 0 is what an unowned vanilla item already does, so **1 is the mod-friendly value** (D) |
| 17 | sort mode 0 body | `0x19cd590` | `x0` = begin, `x1` = end, `x0`/`x1` reloaded from `+0x128` by the caller | `0xa9bc5ff8 0xa90157f6 0xa9024ff4 0xa9037bfd` | no | returns nothing; reached by a tail-call from #6 after it has already written `+0x164`. Skipping it leaves the mode field written but the order unchanged (D) |
| 18 | sort mode 1 body | `0x19cd9d0` | same | `0xa9bc5ff8 0xa90157f6 0xa9024ff4 0xa9037bfd` | no | as #17 (D) |

**Stated uncertainty.** Every "looks harmless" is a reading of the instruction
sequence and the callers' use of the return value, not an observation. None of it
was executed. In particular: (a) whether the scroller tolerates a row whose filler
never ran is **D** — #2 and #3 are the two functions whose skip-safety matters
most and neither is verified; (b) #16's return value 1 has not been observed to
make a mod handle behave like a hat anywhere; (c) the `+0x230` registry is only
known to be a hash table keyed by the 40-bit handle (B for the lookup shape at
0x3269fd0) — what populates it is **not** resolved.

---

## 9. What stayed open

1. **The owner of vtable `0x50a6b18`** (the row-filler callback object). Its slots
   are known (B) and `0x3781470` takes a callback in `x4`, but nothing in the image
   points at `0x50a6b18` as a value, so which object carries it — and therefore
   what calls slots 0x38/0x40/0x48 of it — is unresolved (D).
2. **What pumps `0x19cc3f0`** per frame. It has no `bl` callers; it is data at
   `[S+0x88]`. The per-frame caller is unresolved (D).
3. **Cancel / restore.** No native restore of the previous headgear was found.
   P6's cancel branch is the sort sub-window, not the screen. The candidates
   (`+0x140`, 0x180cf10's one-shot commit) were not followed through (D).
4. **The commit out of `0x5306cb0` into the save.** 0x180d4cc and 0x180d734 read
   and compare it; the writing function was not walked end to end (D).
5. **The exact sort comparators** for modes 0 and 1. The bodies at 0x19ce730 /
   0x19ce100 and the merges at 0x19ce440 / 0x19cde10 were located but not read
   line by line (D). The mode values 0/1/2 and the `+0x164` write are B.
6. **The `+0x230` / `+0x240` tables' meaning** — "unlocked", "in use" or
   "cosmetics". `0x328b5d0` only shows a hash-table membership test (B). What
   populates them is unresolved (D).
7. **The scene's `0x180d2a0` state**, the second hat-screen state handler, was
   found in the offset scan but not read (D).
8. **The outfit row filler's entry.** P8's `0x19cb694` is in the middle of another
   function; the outfit twin of `0x19ccb20` was not located (D). Only the headgear
   one matters for a mod that only replaces the hat list, which is why this was not
   pursued.
9. **What the third constructor argument's static table at `[x24+0x58]` contains**
   — i.e. where the vanilla handle list itself comes from. The ctor reads it and
   hands it to `0x3274c50` (B); one level out was not resolved (D).
10. **No runtime verification of any kind.** Every runtime-behaviour statement in
    this report is D. The Mii editor scene identification of `0x1808980` is C.

---

## 10. Check script

`evidence/P9-HAT-HANDLES/check_p9_hat_handles.py` re-reads every address cited
above from `main.bin`: instruction mnemonics, memory displacements and immediates
(decoded from capstone's operand objects, so the ldp/stp split-imm7 encodings are
handled), `b`/`bl`/`b.cond`/`cbz` branch targets, C string contents, and RELA
addends for 19 vtable slots. It verifies the input's sha256 and size first and
exits 2 if either differs. It exits 1 on any mismatch. It also derives the frame
callback's last `ret` by scanning for it rather than trusting a cited address, so
that fact is machine-checked too.

```
cd <workspace root>
export PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python
python mods/mii_customizer/evidence/P9-HAT-HANDLES/check_p9_hat_handles.py
```

Last lines (full log in `evidence/P9-HAT-HANDLES/91_check_script_output.txt`):

```
P9-HAT-HANDLES check: 396 claims, 0 mismatches
negative-control mode: off
exit=0
```

### Negative controls (all ten exit 1; log in `90_negative_controls.txt`)

| mode | injected fault | result |
|---|---|---|
| `--neg word` | expects `0xdeadbeef` at 0x19ccb20 | `MISMATCH: NEG wrong instruction word at 0x19ccb20 expected 3735928559 got 3506635775` → exit 1 |
| `--neg branch` | expects the call at 0x19cce98 to target 0x19ccb20 | `MISMATCH: NEG wrong call target at 0x19cce98 expected 27052832 got None` → exit 1 |
| `--neg string` | expects `notselecteditem` at 0x4306e2f | `MISMATCH: NEG wrong part name at 0x4306e2f expected 'notselecteditem' got 'selecteditem'` → exit 1 |
| `--neg reloc` | expects addend 0x19ccea0 in slot 0x50a6b18 | `MISMATCH: NEG wrong RELA addend for slot 0x50a6b18 expected 27053728 got 27052832` → exit 1 |
| `--neg vtable` | same, via the vtable-slot claim | `MISMATCH: NEG wrong row-callback slot 0 expected 27053728 got 27052832` → exit 1 |
| `--neg ctor` | expects the sub-object size 0x171 | `MISMATCH: NEG wrong sub-object size expected 369 got 368` → exit 1 |
| `--neg row` | expects the label-builder call to target 0x19ccb20 | `MISMATCH: NEG wrong label-builder branch expected 27052832 got 52986672` → exit 1 |
| `--neg label` | expects `nam_mii_body_%s` at 0x42a06fe | `MISMATCH: NEG wrong label format string expected 'nam_mii_body_%s' got 'nam_mii_hat_%s'` → exit 1 |
| `--neg registry` | expects the 0x13 tag inside 0x328b5d0 | `MISMATCH: NEG wrong handle tag in 0x328b5d0 expected 1369094286720630784 got None` → exit 1 |
| `--neg static` | expects offset 0xca8 at 0x180acc4 | `MISMATCH: NEG wrong headgear static offset expected 3240 got 3248` → exit 1 |

The script itself had four rounds of bugs before the final run, each found by
running it rather than by reading it: the workspace-root path was one level short
(`parents[3]` → `parents[4]`); hand-rolled bit masks for `ldp`/`stp` unsigned
displacements were wrong because those encodings split the immediate across two
fields, so all offset reads were replaced with capstone operand decoding; about
twenty claim *sites* were off by 4 or 8 bytes, which the mismatch list located
one by one; and the first-four-words test wrongly asserted that no entry has a
PC-relative word, when `0x19cd0b0` does have an `adrp` at word 3 — that entry is now
checked as the single documented exception. The report above was corrected to match
at each step; the row filler's four cell-slot offsets, the `+0x148` field and the
`0x5aff_00ff_0000_0000` sentinel all came out of this process.

A final completion pass caught two further errors, this time in the report rather
than the script: the frame callback was described as ending at 0x19cc90c with a
trailing `ret` (0x19cc90c is `udf` alignment padding; the last real `ret` is at
0x19cc8fc, so the body is 0x510 bytes), and the evidence folder was described as
holding 40 files when it holds 51. Both are corrected above, and the frame
callback's extent is now *derived* by the check script rather than asserted in
prose, so the same error cannot recur silently.

---

## 11. Files

Written by this task:

* `research/P9-HAT-HANDLES.md` (this file)
* `evidence/P9-HAT-HANDLES/check_p9_hat_handles.py`
* `evidence/P9-HAT-HANDLES/91_check_script_output.txt`
* `evidence/P9-HAT-HANDLES/90_negative_controls.txt`
* Disassembly windows relied on: `10_vtable_0x50a6c00.txt`,
  `11_vtable_0x50a69a0.txt`, `12_vtable_0x50a6ae0.txt`, `13_delegate_vtables.txt`,
  `14_vtable_0x50a6b18_row_callback.txt`, `16_typeinfo_table_0x3cf47xx.txt`,
  `17_vtables_full.txt`, `18_callback_slots.txt`, `20_scan_range_0x19c0000_0x19d2000.txt`,
  `22_delegate_vtables_full.txt`, `23_lua_bridge_thunks.txt`, `24_sort_thunk_tail.txt`,
  `25_first_four_words.txt`, `30..36` ctor and delegate windows,
  `41..44` the four handlers, `45/46` the sort bodies, `50_row_filler_0x19ccb20.txt`,
  `51_row_dispatch_0x19ccea0.txt`, `52_thunk_0x19cd010.txt`,
  `60_label_builder_0x3288330.txt`, `61_fn_0x328b5d0.txt`, `62_fn_0x3286320.txt`,
  `70..79` the scene, the statics and the strings, `80_scan_hat_only.txt`
* `scratch/2026-10-05_P9-HAT-HANDLES/{d,relocs,lib}.py` (copied from P8) plus
  `scan.py`, `vt.py`, `vtdump.py` written here

Next experiment for whoever picks this up: find what installs vtable `0x50a6b18`.
Everything about the row's visual state funnels through slots 0x00/0x08/0x30/0x48
of that object, so its owner is the last unknown between "the mod owns the vector"
and "the rows behave".

---

## 12. Task summary

**Task ID: P9-HAT-HANDLES — DONE (partially open, as listed in §9).**

Status: all eight questions answered from the image; ten sub-questions remain open
and are named in §9, of which the material ones for a mod-mode list are the owner
of the row-callback vtable, what pumps the frame callback, and the cancel path.

Verified: the check script, 396 claims, 0 mismatches, exit 0, plus ten
negative controls all exiting 1. The input's sha256 and size were verified.
**No runtime verification of any kind; nothing was patched or executed; every
runtime-behaviour statement is tier D.**

Changed files (all inside `mods/mii_customizer/`, no other worker's files touched):
* `research/P9-HAT-HANDLES.md` (new)
* `evidence/P9-HAT-HANDLES/` (new, 51 files: 1 check script + 1 pass log + 1 negative-control log + 48 disassembly/table windows)
* `scratch/2026-10-05_P9-HAT-HANDLES/` (new, 7 scripts)

Corrections to earlier reports, to be propagated by the coordinator:
1. P8-HAT-NATIVE's four handler addresses (`0x19c1f00`/`0x19c1f50`/`0x19c2110`/
   `0x19c2160`) are the **outfit** screen's. The headgear ones are
   `0x19cd0b0`/`0x19cd100`/`0x19cd2c0`/`0x19cd310`, and they call a different
   registry function against a different table.
2. The vector and handle fields are offsets into a 0x170-byte sub-object at
   `*(scene+0x180) + 0x80`, not into the list object itself.
3. P8's outfit row-filler address `0x19cb694` is inside a different function.
4. The headgear working handle is the static `0x5306cb0` (field `+0x138` of the
   record at `0x5306b78`), not `0x5306b78` itself.
5. `get_top_index` does not return a scroll position; it returns whether
   `vector[0]` is in the `+0x230` registry and `+0x169 == 0`.

Out of scope, not started: patching, hooks, plugin code, Lua or layout edits, the
edit-menu dispatch, and any design.
