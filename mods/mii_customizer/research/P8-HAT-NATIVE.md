# P8-HAT-NATIVE — native side of the Mii maker headgear list

Task: **P8-HAT-NATIVE** (Space Bunny Alpha, offline static analysis).
Input: workspace-relative `gamedata/ssbu-13.0.4/main.bin`, sha256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`, 86 672 752 bytes.
Flat decompressed MOD0 image, so **address == file offset**. Relocation array
0x39C8070..0x40C9FC7, 24-byte `{u64 r_offset, u32 r_info(0x403 RELATIVE), u32 pad, u64 r_addend}`.

Evidence tiers used here:
* **B** — read out of this image in this task, re-checked by the script below.
* **C** — pinned by an earlier task's report (only `0x1808980` = Mii editor scene).
* **D** — hypothesis. Nothing here was executed; there are no tier-A claims.

Everything below is B unless marked otherwise.

---

> Coordinator correction 2026-10-05: the question this report leaves open, which constructor
> is the headgear one, is settled by evidence from P8-EDIT-DISPATCH
> (`evidence/P8-EDIT-DISPATCH/49_ctor_script_hashes.txt`, re-read by the coordinator):
> `0x19ceb30` loads the script path hash `0x2fa5c13fc6` = hash40 of
> `ui/script/menu/chara_make/make_mii_hat_actor.lc` (movz/movk at 0x19cecf8..0x19ced08), and
> `0x19c7830` loads `0x30c95391dc` = `.../make_mii_body_actor.lc`. So **ctor2 `0x19ceb30`
> (object at scene+0x180) is headgear, ctor1 `0x19c7830` (scene+0x188) is outfit** (B).
> Also: `SCROLLER_ITEM_NUM` is the TOTAL item count (section 4/5), not rows per page as
> P6-HAT-UI guessed; and the wording "its vtable" for `[x9+0x2b4]` in section 7 is loose:
> the field is in the scroller object the userdata points to. The `get_top_index` handler
> description (returns 0 or 1) is not checked by the coordinator and looks incomplete (D).

> **Coordinator correction 2, 2026-10-05** (from P9-HAT-HANDLES, 396 claims rerun): the
> corrections below supersede this report's text wherever they differ.
> 1. The four handler addresses in §0/§2 (`0x19c1f00` / `0x19c1f50` / `0x19c2110` /
>    `0x19c2160`) are the **outfit** instance's, registered by `0x19c7830`. The **headgear**
>    ctor `0x19ceb30` registers `0x19cd0b0` / `0x19cd100` / `0x19cd2c0` / `0x19cd310`, and
>    its `get_top_index` calls `0x328b5d0` against `+0x230` (outfit: `0x3286320`,
>    `+0x240`).
> 2. The vector (`+0x128`) and handle slots (`+0x140` / `+0x148` / `+0x150` / `+0x158`)
>    are offsets into a 0x170-byte sub-object at `[list object +0x80]` (`S` in
>    P9-HAT-HANDLES), not into the list object itself.
> 3. The outfit row filler is not `0x19cb694` (that address is inside a different
>    function); only the headgear filler `0x19ccb20` was resolved.
> 4. The decided handle is traced one step further: `+0x148` -> scene state 5
>    (`0x180abd0`) writes the static `0x5306cb0` (field `+0x138` of the record at
>    0x5306b78); `0x19cb2e0` then rebuilds the labels. The commit from the static into
>    the save is still open.
> 5. `get_top_index` is answered for the headgear list: it returns 1 iff `vector[0]`
>    is in the `+0x230` registry and `+0x169 == 0`; it is not a scroll position.

## 0. Summary of the answers

| Q | answer |
|---|---|
| 1 | Two near-identical constructors, `0x19c7830` and `0x19ceb30`. Same C++ list class, one instance per part on the Mii screen. |
| 2 | Handlers `0x19cd0b0` / `0x19cd100` / `0x19cd2c0` / `0x19cd310` (**headgear**; the `0x19c1fxx` set in §2 is the outfit's). Item array = `std::vector` of 8-byte handles at `S+0x128`, `S = *[list object +0x80]` (0x170-byte sub-object). Three sort modes = 0 default, 1 index order, 2 unlocked-before-locked. |
| 3 | Global `scroller` is set in four places; the Mii ones are `0x19c8240` and `0x19cf544`. Underlying type is `MetatableLayoutListScroller`, built by `0x3781470` with part name `"scroll"`. |
| 4 | `SCROLLER_ITEM_NUM` is registered as a *constant* (not a method) by `bl 0x33750a0` at `0x19c8550` / `0x19cf854`, with value `w3 = [sp+0xd4]`. |
| 5 | Count = `(obj->v_end - obj->v_begin) >> 3` at `0x19c7cf0`–`0x19c7d04`. The vector is filled by `0x3276440` (ctor1) / `0x3274c50` (ctor2) from a static table in the 3rd ctor argument. |
| 6 | **Found.** Row filler `0x19ccb20`, reached through the vtable thunk `0x19cd014`. Row text is a **message key built by formatting `nam_mii_hat_%s`** with the item's name — *not* a string pointer held by the list. |
| 7 | `get_decided_item` returns a **row index** (`ldrsw [vtable+0x2b4]`), not an item id. |
| 8 | Smallest sets listed at the end. |

---

## 1. Registration: which object owns `sort_id_list` / `get_top_index`

`sort_id_list` (0x427f3a7) and `get_top_index` (0x4290580) each occur once in the
image and each have **two** adrp+add references, both inside the same two
functions — the two constructors.

`0x19c7830` (ctor1), prologue at 0x19c7830:

```
0x019c7850: adrp  x8, #0x50a6000
0x019c7854: add   x8, x8, #0x9a0        ; = 0x50a69a0
0x019c785c: stp   x8, xzr, [x0]         ; vtable = 0x50a69a0
...
0x019c7880: mov   w1, #0x170            ; sub-object size
0x019c7890: bl    0x392dce0              ; operator new(0x170, 0x10)
...
0x019c8240: add   x1, x1, #0x678        ; = 0x436b678 "scroller"
0x019c8248: bl    0x3373f00              ; push the scroller to Lua
0x019c8300: adrp  x1, #0x4290000
0x019c8304: add   x1, x1, #0x580        ; = 0x4290580 "get_top_index"
0x019c8318: bl    0x3376540              ; register delegate + handler
0x019c83a8: adrp  x1, #0x427f000
0x019c83ac: add   x1, x1, #0x3a7        ; = 0x427f3a7 "sort_id_list"
0x019c83c0: bl    0x3376540
0x019c846c: bl    0x3376540              ; "backup_list_selected_id"
0x019c8510: bl    0x3376540              ; "select_list_from_backup_id"
```

`0x19ceb30` (ctor2) is instruction-for-instruction the same shape with a different
vtable:

```
0x019ceb50: adrp  x8, #0x50a6000
0x019ceb54: add   x8, x8, #0xc00        ; = 0x50a6c00
0x019ceb5c: stp   x8, xzr, [x0]
0x019cf544: add   x1, x1, #0x678        ; "scroller"
0x019cf54c: bl    0x3373f00
0x019cf608: add   x1, x1, #0x580        ; "get_top_index"
0x019cf61c: bl    0x3376540
0x019cf6b0: add   x1, x1, #0x3a7        ; "sort_id_list"
0x019cf6c4: bl    0x3376540
0x019cf770: bl    0x3376540              ; backup
0x019cf814: bl    0x3376540              ; select
```

Both register the **same four bridge names** and the same `"scroller"` global, so
one C++ class serves both the headgear and the outfit screen.

**Callers.** The Mii editor scene function `0x1808980` (C: identified by the
coordinator) calls both:

```
0x01809558: bl 0x19ceb30     -> obj stored at [scene+0x180]
0x01809670: bl 0x19c7830     -> obj stored at [scene+0x188]
```

and a second owner at `0x1982xxx` calls them at `0x1982c68` / `0x1982dd4`
(stored at `[parent+0x5d0]` / `[parent+0x5d8]`). Each scene-side wrapper is
allocated with size `0x88` (`mov w1,#0x88` at 0x1809534 / 0x180964c) and the
constructor separately allocates a **0x170-byte sub-object** (0x19c7880).

**Same object for hat and outfit?** Yes at the class level — one class, four
bridge names, identical handlers. There are two *instances*, one per part slot
on the Mii screen. Which instance is the hat one and which is the outfit one is
**not** settled by this task: ctor1 filters its item vector with the table at
`[0x532e730]->[8] + 0x240` (0x19c7a6c/0x19c7a70) while ctor2 uses `+0x230`
(0x19ced68/0x19ced6c), and the two vectors are filled from different offsets of
the same 3rd argument (`x24+0x60` vs `x24+0x58`, at 0x19c7a64 and 0x19ced60).
That is consistent with two different part tables but does not by itself name
"hat" or "outfit" (D).

---

## 2. The four handlers

All four are reached through `0x3376540` (delegate + handler pointer, the pattern
already pinned in P1-ID-REVIEW §2.3).

**Correction 2 applies here:** the four functions below are the ones registered by
ctor1 `0x19c7830`, the **outfit** instance. The headgear ctor `0x19ceb30` registers the
near-identical set `0x19cd0b0` / `0x19cd100` / `0x19cd2c0` / `0x19cd310`; its
`get_top_index` tests `0x328b5d0` against `+0x230` instead, and its full text is in
P9-HAT-HANDLES §7. Anything below that says "obj+0xNNN" for the vector or handle slots
means `S+0xNNN` with `S = *[list object +0x80]`.

### `get_top_index` → handler `0x19c1f00`

```
0x019c1f00: str  x19, [sp,#-0x20]!
0x019c1f0c: adrp x8, #0x532e000
0x019c1f10: ldr  x8, [x8,#0x730]         ; global
0x019c1f18: mov  x19, x0
0x019c1f1c: add  x0, x8, #0x240         ; the "known/unlocked" table
0x019c1f20: ldr  x8, [x19,#0x128]       ; item vector begin
0x019c1f24: ldr  x1, [x8]               ; first handle
0x019c1f28: bl   0x3286320              ; "does this table contain id"
0x019c1f30: ldrb w8, [x19,#0x169]       ; a one-byte mode flag on the object
```

returns `w0` = 0 or 1. Thunk `0x19c7780` reads `S-0x10` / `S+0x20` off the Lua
stack and pushes the result as a **Lua integer (tag 0x13)**, `sxtw` of `w0`.

### `sort_id_list` → handler `0x19c1f50`

Prologue:
```
0x019c1f50: sub  sp, sp, #0x70
0x019c1f54: stp  x24, x23, [sp,#0x30]
0x019c1f58: stp  x22, x21, [sp,#0x40]
0x019c1f5c: stp  x20, x19, [sp,#0x50]
```
Mode dispatch:
```
0x019c1f68: mov  x19, x0
0x019c1f6c: cmp  w1, #2        ; 0x019c1f70: b.eq 0x19c1fc4   (mode 2)
0x019c1f74: cmp  w1, #1        ; 0x019c1f78: b.eq 0x19c1fa0   (mode 1)
0x019c1f7c: cbnz w1, 0x19c20d0           ; anything else: reject, no write
0x019c1f80: str  wzr, [x19,#0x164]       ; mode 0 -> field = 0
0x019c1f9c: b    0x19c23f0               ; mode 0 sort body
0x019c1fa4: str  w8(=1), [x19,#0x164]    ; mode 1 -> field = 1
                                       ; mode 2 -> field = 20, tail-b 0x19c23f0 path
```
`obj+0x164` (32-bit) is the sort-mode field; `obj+0x169` (8-bit) is the flag the
row filler and `get_top_index` also read.

The sort bodies (`0x19c23f0`, `0x19c3720`) each call `0x3286320` (registry
"contains this id") 18 times together with `0x3283cf0` and `0x32839f0` (id→index
lookups), so the three modes order the same handles by different keys drawn from
the unlocked/known-id tables. The precise comparator for each mode is **D**; the
three mode values 0/1/2 and the field they write are B.

**Item array.** A `std::vector` of **8-byte tagged handles** at `S+0x128`
(correction 2: `S` is the 0x170-byte sub-object at `*[list object +0x80]`, not the list
object the scene holds): begin `+0x128`, end `+0x130`, capacity `+0x138`.
Count = `(end − begin) >> 3`. There is no separate count field.

### `backup_list_selected_id` → handler `0x19c2110`

```
0x019c2110: ldr  x8, [x0,#0xf8]          ; the scroller (0x3781470 object)
0x019c2114: ldrsw x8, [x8,#0x2a4]       ; scroller selected row index (s32)
0x019c2118: cmn  w8, #1                 ; -1 -> "nothing selected"
0x019c2120: ldp  x9, x10, [x0,#0x128]   ; the item vector
0x019c2124: sub  x10, x10, x9
0x019c2128: asr  x10, x10, #3           ; count
0x019c212c: cmp  x10, x8                ; bounds check
```

On `-1` it stores the sentinel `0x13ff_0000_0000_0000`; otherwise
`vector[index]` — the **item handle**, not an index — into `obj+0x158`.

### `select_list_from_backup_id` → handler `0x19c2160`

```
0x019c2160: stp  x29, x30, [sp,#-0x10]!
0x019c2168: ldr  x9, [x0,#0x158]        ; the backed-up handle
0x019c216c: mov  x8, #0x1300000000000000   ; sentinel tag
```

It linear-searches the `+0x128` vector for an equal handle and, on a match, calls
`0x3783660` with `x0 = [x0+0xf8]` (the scroller), `w1 = index`, `w2 = 0`,
`w3 = 1`. Out of range / empty calls `0x39c0d80`.

---

## 3. The global `scroller`

Four references to the string at 0x436b678:

| site | enclosing function | why it is / is not the Mii one |
|---|---|---|
| 0x19c8240 | `0x19c7830` | **Mii** — same ctor that registers `sort_id_list` |
| 0x19cf544 | `0x19ceb30` | **Mii** — twin ctor, same registrations |
| 0x182e9bc | `0x182dd50` | not Mii (no bridge registrations in that function) |
| 0x18c9e28 | `0x18c96f0` | a Mii *collection/save* screen, not the part list — that function also registers `BUTTON_DELETE` (w3 = 6) |

All four call `bl 0x3373f00`, the `MetatableLayoutListScroller` setter (the
metatable name string lives at 0x4358a4e).

**Construction arguments.** The C++ scroller is built at 0x19c7d24 by
`0x3781470` (vtable 0x523ca68, allocates 0x340 bytes):

```
0x019c7d08: mov  w8, #0x101
0x019c7d0c: adrp x2, #0x424e000
0x019c7d10: add  x2, x2, #0xc05        ; = 0x424ec05 "scroll"
0x019c7d14: add  x3, sp, #0xd0         ; config struct
0x019c7d18: mov  x1, x24               ; layout root
0x019c7d1c: mov  x4, x25
```

* x0 = the 0x340-byte scroller, written back through `*[obj+0xf8]`
  (`add x8, x20, #0xf8` at 0x19c7970, pre-writeback).
* x1 = the layout root.
* x2 = the layout part name, the literal **`"scroll"`**.
* x3 = a stack config struct at `sp+0xd0`: 8 zero bytes, a float pair
  `0x42484000_41800000` at `+0xd8`, `w8 = 0x101` stored at `+0xec`, byte 1 at
  `+0xea`.
* x4 = a callback object.

There is a second, smaller scroller class (`0x32cbe60`, vtable 0x51822f8,
0x138 bytes, fields `+0x8 = 0x100`, `+0xc = 0x4001`, `+0x10 = 1`, `+0x14 = 1`);
its vtable references `set_parts_sort_list_%02d` / `list_cnt_%02d` /
`selector_0`, which belong to the **sort sub-window**, not to the rows.

---

## 4. `SCROLLER_ITEM_NUM`

Registered as a **constant**, not a method — `bl 0x33750a0` with the shared
constants table at 0x42b1a84:

```
0x019c8538: ldr  w3, [sp,#0xd4]         ; the computed item count
0x019c853c: adrp x1, #0x42a1000
0x019c8540: add  x1, x1, #0x8e6        ; = 0x42a18e6 "SCROLLER_ITEM_NUM"
0x019c8544: adrp x2, #0x42b1000
0x019c8548: add  x2, x2, #0xa84        ; = 0x42b1a84
0x019c854c: mov  x0, x8                 ; lua table from [x20+0x40]
0x019c8550: bl   0x33750a0
```

and again in ctor2 at 0x19cf844 / `bl 0x19cf854`. `INPUT_OPEN_SORT_WINDOW` with
`w3 = 7` is registered the same way two instructions later (0x19c8564).

---

## 5. The item count

```
0x019c7cf0: ldr  x8, [x23]              ; vector end
0x019c7cf4: ldr  x9, [x26]              ; vector begin
0x019c7cf8: sub  x8, x8, x9
0x019c7d00: lsr  x8, x8, #3
0x019c7d04: str  w8, [sp,#0xd4]          ; SCROLLER_ITEM_NUM
```

So the total is just the element count of the vector at `obj+0x128` (8-byte
elements). The vector is filled *before* this, by

```
0x019c7a20: mov  x2, x24
0x019c7a24: ldr  x1, [x2], #8            ; from x24+0x60
0x019c7a28: add  x0, sp, #0xd0
0x019c7a2c: bl   0x3276440               ; fill
0x019c7a30: ldr  x0, [x20,#0x128]        ; free old buffer
...
0x019c7a4c: str  x8, [x20,#0x128]
0x019c7a54: stp  x8, x22, [x20,#0x130]
```

ctor2 uses `0x3274c50` and `x24+0x58` (0x19ced24 / 0x19ced28 / 0x19ced60).
One level deep: `0x3276440` and `0x3274c50` open `x1` as a Lua-ish table
(`ldr [x8+8]` / `ldrb [#0x20]`, `cmp #0xc` = string type check) and iterate it,
so the source is a **host-side table handed to the constructor**, not read from a
param file or the save inside these two frames. The static Mii-data table it is
built from (`x24+0x60` / `x24+0x58`) is one more level out and is **not**
resolved here. The filter predicate is `0x3286320` / `0x328b5d0`; both walk a
`phx::Hash40`-tagged value (top byte 0x5a, `and #0xffffffffff`) into a
registry table and return a bool, so the list is "handles that exist in table
X" — whether X means *unlocked* or *in use* is **D**.

---

## 6. Row drawing — **answered**

`sort` list rows are filled by **`0x19ccb20`**, reached through the two-instruction
vtable thunk:

```
0x019cd010: sub  x0, x0, #0x48
0x019cd014: b    0x19ccb20
```

Entry arguments: `x0` = the list object (adjusted by −0x48 by the thunk),
`w1` = the **row index**, `x2` = the row's layout node.

```
0x019ccb3c: ldp  x9, x10, [x0,#0x128]   ; item vector
0x019ccb4c: asr  x10, x10, #3           ; count
0x019ccb58: ldr  x20, [x9, x8, lsl #3]  ; the row's item handle
0x019ccb5c: ldr  x8, [x19,#0x150]       ; currently selected handle

; --- 1. selected / not-selected marker, s0 = 1.0
0x019ccb90: ldr  x0, [x22,#8]
0x019ccb98: add  x1, x1, #0xe2f         ; = 0x4306e2f "selecteditem"
   ... or ...
0x019ccbc4: add  x1, x1, #0x3d3         ; = 0x44533d3 "notselecteditem"
0x019ccbc8: fmov s0, #1.00000000
0x019ccbcc: bl   0x3777d50

; --- 2. ROW TEXT: build a message key from the item, then push it
0x019ccbe0: add  x0, sp, #0x18           ; out: 12-byte label struct
0x019ccbe4: mov  x2, x20                 ; the item handle
0x019ccbec: bl   0x3288330               ; -> "nam_mii_hat_%s" label
0x019ccbf4: add  x1, x1, #0x382         ; = 0x425e382 "set_txt_val"
0x019ccc00: bl   0x3776360               ; find that part under the row
0x019ccc10: bl   0x3779b70               ; set the text

; --- 3. greyed-out variant when the item is not owned
0x019ccc30: add  x1, x1, #0xc1a         ; = 0x436ac1a "set_txt_val_disable"
0x019ccc48: bl   0x3779b70

; --- 4. "selected" tick part, bit 0 of the row node's flag byte
0x019ccc60: add  x1, x1, #0x65f         ; = 0x430765f "selected"
0x019cccc4: ldrb w9, [x8,#0x58]
0x019cccc8: and  w9, w9, #0xfe          ; clear bit 0
0x019ccce0: orr  w9, w9, #1             ; or set bit 0
0x019ccce4: strb w9, [x8,#0x58]

; --- 5. ownership test -> which icon branch is used
0x019ccd7c: add  x0, x8, #0x230         ; the +0x230 table
0x019ccd80: mov  x1, x20
0x019ccd84: bl   0x328b5d0
0x019ccd8c: ldrb w8, [x19,#0x169]       ; the mode flag
; then vtable slots 0x1f8 / 0x200 / 0x210 / 0x388 on the row node
```

**The text is a message label derived from the item id, not a string pointer the
list holds.** `0x3288330` ends with

```
0x032886ec: adrp x0, #0x42a0000
0x032886f0: add  x0, x0, #0x6fe         ; = 0x42a06fe "nam_mii_hat_%s"
0x032886f4: mov  x8, x19
0x032886f8: bl   0x3a4ca0               ; format
```

and `0x3a4ca0` is a vsnprintf wrapper that additionally computes a hash over the
result and stores it: `str w0, [x19,#4]` (length) at 0x3a4d54 and `str w21,
[x19]` (FNV-style hash, seed 0x811c9dc5) at 0x3a4d7c. So each row's text is a
`{hash, length, "nam_mii_hat_<name>"}` message key.

`<name>` comes from a lookup inside `0x3288330`: the 40-bit tag of the handle is
indexed into a registry table (`0x3269900`, `0x3269fd0`, `0x3269e30`), the
resulting string is copied byte-pair-wise into the format-argument slot, and the
whole thing is hashed. The parallel function `0x32842e0` does the same with
**`nam_mii_body_%s`** (0x43feab3) and is called from the same place (0x19cb47c),
which is why one class serves hat and body.

**Where the rows come from.** `0x3781470` builds one row object per item in a
loop (`0x3782100`…`0x37822a0`): name lookup `0x3776090` at 0x37821a8, part lookup
`0x3776360` at 0x3782214, `blr [vtable+0x258]` with `w1 = 1` at 0x3782264,
`str [sp+0x20] -> [row+0x150]` at 0x3782278, `str w8 -> [row+0x1a0]` (the row
index) at 0x3782284, `blr [vtable+0x1b8]` (row refresh) at 0x378228c, and the
row is pushed into the scroller's list at 0x378229c.

The scroller's own frame function `0x3772650` is the enable/visibility toggler,
not the text filler.

---

## 7. `get_decided_item`

The name string has **no adrp xref** — it is referenced through a relocated
pointer table, which is how every host method is bound. Scanning the RELATIVE
records finds exactly one:

```
reloc record 0x3ea85e0  ->  slot 0x5183b40  addend 0x440fdbb "get_decided_item"
                                            slot 0x5183b48  addend 0x3363070
```

and the slots around it are the scroller's own Lua methods (name, handler pairs):

```
0x5183b10  select_item            0x3362ba0
0x5183b20  ensure_visible         0x3362e00
0x5183b30  get_selected_item      0x3362ff0
0x5183b40  get_decided_item       0x3363070
0x5183b50  redraw_all_items       0x33630f0
0x5183b60  special_input_is_upward 0x3363160
```

`0x3363070` (24 instructions, no prologue — it runs on the Lua stack directly):

```
0x03363070: ldr   x8, [x0,#0x10]        ; lua_State
0x033630a4: ldr   x10, [x10]            ; the scroller userdata
0x033630b0: ldr   x9, [x10]             ; its vtable
0x033630b4: ldrsw x10, [x9,#0x2b4]      ; <<< THE DECIDED ITEM
0x033630c4: mov   w9, #0x13             ; LUA_TINTEGER
0x033630c8: stur  x10, [x8,#-0x10]
0x033630cc: stur  w9,  [x8,#-8]
0x033630dc: mov   w0, #1
0x033630e0: ret
```

`get_selected_item` (`0x3362ff0`) is the same code with
`ldrsw x10,[x9,#0x2a4]` at 0x3363034.

**So `get_decided_item` returns a row index** (32-bit signed), not an item id
from the array. The scroller frame function `0x377d290` maintains both fields:

```
0x0377d2b8: ldr  w8, [x0,#0x2a0]        ; cursor
0x0377d2bc: str  w8, [x0,#0x2a4]        ; selected  = cursor
0x0377d2c0: add  x8, x0, #0x2b4
0x0377d2d0: str  x23(-1), [x8]          ; decided   = -1
0x0377d2d4: strb wzr, [x0,#0x2bc]
...
0x0377d648: ldr  w8, [x19,#0x2b0]       ; a decision was queued
0x0377d658: str  w8, [x19,#0x2b4]       ; latch it
0x0377d660: str  w23, [x19,#0x2b0]      ; clear the queue
```

**Where it becomes the Mii's headgear value.** One level down, the index never
reaches a CharInfo field directly in C++: the Lua side turns it into a handle
with `backup_list_selected_id` (`0x19c2110` reads `+0x2a4`, indexes the vector,
stores the **handle** at `obj+0x158`) and `select_list_from_backup_id`
(`0x19c2160`) searches the vector for that handle and calls the scroller. The
actual write into the Mii CharInfo happens in code that was **not** reached in
this task (D) — the hat value is applied by the Mii editor after the list window
closes, and the path from the handle to the CharInfo field is the open part of
this report.

> **Coordinator correction 2 (P9-HAT-HANDLES, B):** on the **headgear** screen the path is
> the frame callback `0x19cc3f0` (fills `+0x148` from the Lua `get_decided_id`), then scene
> state 5 `0x180abd0` compares `+0x148` with the static `0x5306cb0` and writes the static
> (`0x180ad1c..0x180ad24`); `0x19cb2e0` rebuilds the labels from it. `0x5306cb0` is field
> `+0x138` of the record at `0x5306b78`. What remains open is the commit from that static
> into the save. The `backup` / `select` pair above is the *sort window's* cancel restore,
> not the screen's (P6 §3.1).

---

## 8. Hook-point facts (not a design)

**(a) To change the item count**

| address | entry args | first four instructions |
|---|---|---|
| `0x19c7cf0` (count computation site) | in-register; reads `[x23]`, `[x26]`, writes `[sp+0xd4]` | `ldr x8,[x23]`, `ldr x9,[x26]`, `sub x8,x8,x9`, `ldr x0,[sp,#0x28]` — **no PC-relative** |
| `0x19c7d04` (`str w8,[sp,#0xd4]`) | — | — |
| `0x3276440` / `0x3274c50` (vector fillers) | `x0` = out vector, `x1` = source table, `x2` = source count/index | `sub sp,sp,#0x130` / `sub sp,sp,#0x120`, `stp …`, `stp …`, `stp …` — **no PC-relative** |
| `0x19c7830` / `0x19ceb30` (the ctors) | `x0` = this, `x1`, `x2` = source table | `stp x28,x27,[sp,#-0x60]!`, `stp x26,x25,…`, `stp x24,x23,…`, `stp x22,x21,…` — pre-indexed sp stores carry **no PC-relative immediate** (the code is position-dependent at run time, but nothing in the first four words needs rebasing) |

**(b) To supply your own row text**

*Correction 2:* the two `0x19c1fxx` rows below are the **outfit** instance's. The headgear
equivalents are `0x19cd100` (sort handler) and `0x19cd0b0` (get_top_index); the headgear
`get_top_index` also has the `adrp` at word 3 and needs rebasing (P9-HAT-HANDLES §7/§8).

| address | entry args | first four instructions |
|---|---|---|
| `0x19ccb20` (row filler) | `x0` = list object (thunk subtracts 0x48), `w1` = row index, `x2` = row node | `sub sp,sp,#0xc0`, `stp x26,x25,…`, `stp x24,x23,…`, `stp x22,x21,…` — **no PC-relative** |
| `0x19cd010`/`0x19cd014` (the vtable thunk to it) | `x0` = row | `sub x0,x0,#0x48`, `b 0x19ccb20` |
| `0x3288330` (hat label builder) | `x8` = sret label struct, `x1` = registry, `x2` = item handle | `sub sp,sp,#0xb0`, `str x25,…`, `stp x24,x23,…`, `stp x22,x21,…` — **no PC-relative** |
| `0x32842e0` (body label builder) | same shape, formats `nam_mii_body_%s` | same |
| `0x3779b70` (the "set text on a layout part" call) | `x0` = out struct, `x1` = part | — |
| `0x3a4ca0` (format + hash) | `x8` = sret, `x0` = format string | `sub sp,sp,#0x130`, `stp x28,x21,…`, `stp x20,x19,…`, `stp x29,x30,…` — **no PC-relative** |
| `0x19c1f50` (sort handler, outfit) | `x0` = this, `w1` = mode, Lua args on `S-0x20` | `sub sp,sp,#0x70`, `stp x24,x23,…`, `stp x22,x21,…`, `stp x20,x19,…` — **no PC-relative** |
| `0x19c1f00` (get_top_index handler, outfit) | `x0` = this | `str x19,[sp,#-0x20]!`, `stp x29,x30,…`, `add x29,sp,#0x10`, **`adrp x8,#0x532e000`** — **word 3 (0x19c1f0c) IS PC-relative** and must be rebased |
| `0x19c2110` / `0x19c2160` (backup / select handlers) | `x0` = this | `ldr x8,[x0,#0xf8]` / `stp x29,x30,[sp,#-0x10]!`, … — **no PC-relative** |

**Still unknown for a hook design** (all D / out of scope here):
* ~~which of `0x19c7830` / `0x19ceb30` is the hat instance on a given screen~~ — settled
  by correction 2 (`0x19ceb30` = headgear);
* the exact comparator for each of the three sort modes;
* what the `+0x230` / `+0x240` tables actually mean (unlocked? in-use? cosmetics);
* the commit of the chosen handle from the static `0x5306cb0` into the Mii save;
* whether the row filler at `0x19ccb20` is shared with non-Mii scrollers
  (it is reached through a vtable slot whose owner was not identified — the two
  list-object vtables 0x50a69a0 / 0x50a6c00 do **not** contain 0x19cd014, so the
  callback object that owns it is constructed elsewhere and was not resolved).

---

## 9. Check script

`evidence/P8-HAT-NATIVE/check_p8_hat_native.py` re-reads every cited address from
`main.bin` — instruction words, branch targets (b / bl / b.cond), adrp+add pairs
resolved to string addresses, string contents, and RELATIVE relocation records —
and exits non-zero on any mismatch. It first verifies the input's sha256 and
size and exits 2 if either differs.

```
cd mods/mii_customizer
export PYTHONPATH=../ssbu_mod_new/builds/.cache/dk_cargo/python
python evidence/P8-HAT-NATIVE/check_p8_hat_native.py
```

Last lines (full log in `evidence/P8-HAT-NATIVE/27_check_script_output.txt`):

```
P8-HAT-NATIVE check: 221 claims, 0 mismatches
negative-control mode: off
exit=0
```

### Negative controls (all four exit 1)

| mode | injected fault | result |
|---|---|---|
| `--neg word` | expects `0xdeadbeef` at 0x19c7d04 instead of `0xb900d7e8` | `MISMATCH: NEG wrong count-store word at 0x019c7d04 expected 0xdeadbeef got 0xb900d7e8` → exit 1 |
| `--neg string` | expects `nam_mii_body_%s` at 0x42a06fe | `MISMATCH: NEG wrong label format string at 0x042a06fe expected 'nam_mii_body_%s' got 'nam_mii_hat_%s'` → exit 1 |
| `--neg reloc` | expects addend `0x4441001` in slot 0x5183b40 instead of `0x440fdbb` | `MISMATCH: NEG wrong method-table addend no RELATIVE record for slot 0x5183b40 addend 0x4441001` → exit 1 |
| `--neg branch` | expects the call at 0x19ccbec to target 0x19ccb20 instead of 0x3288330 | `MISMATCH: NEG wrong label-builder call branch at 0x019ccbec expected target 0x19ccb20 got 0x3288330` → exit 1 |

The script itself had three bugs that the first run exposed and that were fixed
before the final run: a broken sign-extension helper (`sx`), a branch decoder
that handled only `b`/`bl` and used the wrong field for `b.cond`, and inverted
booleans in the PC-relative prologue test. A first pass also found **five wrong
addresses in this report** (the `sort_id_list` / `scroller` adrp+add pairs and
the `notselecteditem` pair were cited at the branch rather than at the `add`),
all corrected above.

---

## 10. What stayed open

* **Q1.** One class, two instances — settled. *Which instance is the hat one* —
  settled by correction 2 (`0x19ceb30` = headgear); §1's text below is superseded.
* **Q2.** Handlers, offsets, widths, calls, the item array layout and the three
  mode values — settled. *The exact comparator of each sort mode* — open (D).
* **Q3.** All four `scroller` users, which two are the Mii ones, the native type
  and its construction arguments — settled. *The meaning of the config struct at
  `sp+0xd0` and of `x4`* — open (D).
* **Q4.** Registration site, call and value — settled.
* **Q5.** The count field, who computes it, and the immediate source (a host
  table handed to the ctor) — settled one level deep as asked. *What fills that
  table, and whether the `+0x230`/`+0x240` tables mean "unlocked"* — open (D).
* **Q6.** **Settled.** Row filler `0x19ccb20`, its calls, the part names, the
  marker bit, and — the actual question — the text is a **message key built by
  formatting `nam_mii_hat_%s` with the item's name**, hashed by `0x3a4ca0`. Not a
  string pointer stored by the list.
* **Q7 (mostly).** `get_decided_item` returns a **row index** (`ldrsw [vtable+0x2b4]`)
  — settled. *Where that becomes the Mii's headgear value* — correction 2 traces it to
  the static `0x5306cb0`; the commit from there into the save is the open part.
* **Q8.** Address, entry registers and PC-relative status for eight candidate
  interception points — settled. *Which instance to hook for the hat screen* —
  open.

**No runtime verification of any kind.** Everything is static reading of the
image; there are no tier-A claims. The Mii editor scene identification of
`0x1808980` is tier C.

## 11. Files

Written by this task:

* `research/P8-HAT-NATIVE.md` (this file)
* `evidence/P8-HAT-NATIVE/check_p8_hat_native.py`
* `evidence/P8-HAT-NATIVE/27_check_script_output.txt`
* `evidence/P8-HAT-NATIVE/16_fn_0x3288330_nam_mii_hat.txt` (+ `.calls`)
* `evidence/P8-HAT-NATIVE/17_fn_0x19cb2e0_label_builder.txt` (+ `.calls`)
* `evidence/P8-HAT-NATIVE/18_fn_0x19d5580.txt`
* `evidence/P8-HAT-NATIVE/19_scroller_region_strings.txt`
* `evidence/P8-HAT-NATIVE/20_row_loop_0x3781470.txt`
* `evidence/P8-HAT-NATIVE/21_fn_0x19ccb20.txt` — the row filler
* `evidence/P8-HAT-NATIVE/22_fn_0x19ccea0_row_dispatch.txt`
* `evidence/P8-HAT-NATIVE/23_scroller_method_table_0x5183b40.txt`
* `evidence/P8-HAT-NATIVE/24_ctor_call_sites.txt`
* `evidence/P8-HAT-NATIVE/25_ctor_vtables_and_reg.txt`
* `evidence/P8-HAT-NATIVE/26_handler_entry_words.txt`
* `scratch/2026-10-05_P8-HAT-NATIVE/{h,fn,vtscan,cbp,d,lib,relocs}.py`

Earlier in this task: `00_input_identity.txt`, `01_string_occurrences.txt`,
`02_xrefs.txt`, `03_name_table_0x19c8xxx.txt`, `04_ctor_0x19c7830.txt`,
`05_editor_scene_calls.txt`, `06_delegate_vtables.txt`, `07_ctor_0x19ceb30.txt`,
`08_reg_block_0x19cf5xx.txt`, `09_editor_scene_0x1808980.txt`,
`10_handler_get_top_index_0x19c1f00.txt`,
`11_handler_sort_id_list_0x19c1f50.txt` (+ `_head`),
`12_thunk_get_top_index_0x19c7780.txt`, `13_count_and_scroller_ctor.txt`,
`14_scroller_vtable_scan.txt`, `15_handlers_backup_select.txt`.

Next experiment for whoever picks this up: from `0x19ccb20`'s item handle,
follow `0x3269900` / `0x3269fd0` / `0x3269e30` to find which host table maps a
40-bit handle to its name string — that table is the real "list of hats", and it
is also what a mod would have to extend to add a row.
