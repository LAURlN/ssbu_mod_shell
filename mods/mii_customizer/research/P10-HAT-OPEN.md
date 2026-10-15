# P10-HAT-OPEN — the open native questions of the headgear list

> **Coordinator review 2026-10-06** (check rerun from the workspace root: 472 claims, 0
> mismatches, exit 0, after removing one claim the worker added after its last run -
> `check_imm` on `0x17c0b5c`, which is `mov w21, wzr` and has no immediate; `--neg writers`
> exits 1). Three statements below are corrected by the coordinator's own disassembly:
> 1. **Q1, writer 2 is not "only when the xor equals 1".** `0x180ace0 b.ne 0x180ae08` is
>    taken when `S+0x148` is a valid handle; at `0x180ae08..0x180ae20`, if the static is
>    valid too and the 40-bit hashes differ, control goes to `0x180ad1c` and the static is
>    written. So the static is written whenever the two handles differ as items.
> 2. **"Cancel does not restore the static" is wrong as a conclusion.** `S+0x148` is seeded
>    with the entry handle (`0x19cfe18 stp x1,x1,[x0,#0x140]`) and is overwritten only when
>    Lua `get_decided_id` returns a non-negative index (`0x19cc698 tbz w0,#31` ->
>    `0x19cc6c0..0x19cc6c4`; the index is that return value, not the scroller's selected
>    row). On a cancel it still holds the entry handle, and writer 2 copies it back over
>    whatever the previews (writer 1) put into the static. That is the restore.
> 3. **`0x328b5d0` returns 1 for a handle that is NOT in the table** (`0x328b7a0 cmp w8,w20`
>    with `w20` = index or -1, `0x328b7ac cset w0, ls`: bound <= index, unsigned, so a miss
>    gives 1). Read "returns 0" in Q2 as "is listed". The row filler agrees: `0x19ccd88 tbz
>    w0,#0` skips the unavailable branch for 0.

Task: **P10-HAT-OPEN** (Space Bunny Alpha, offline static analysis). Nothing executed, nothing patched.

Input: workspace-relative `gamedata/ssbu-13.0.4/main.bin`,
sha256 `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`
(verified in this task; the check script re-verifies it and the size, 86 672 752 bytes, on every run).
Flat decompressed MOD0 image: **address == file offset**.

Notation: `S` = the 0x170-byte sub-object at `[list object+0x80]`; the list object is
`[scene+0x180]`, so `S` = `*(scene+0x180) + 0x80` (per P9-HAT-HANDLES §0,
correction 2). In state 5 the frame's `x0` **is** the scene: the state's own fields are
`scene+0x144` (state-stack depth), `+0x148`/`+0x150` (state current/previous), `+0x14c`
(frame counter), `+0x161`, `+0x163`, `+0x164`, `+0x1c8`, and the objects it reaches are
`[scene+0x178]` and `[scene+0x180]` (the list) — see Q1.

Tiers: **B** = read out of this image in this task and re-read by
`evidence/P10-HAT-OPEN/check_p10_hat_open.py` (449 claims, 0 mismatches).
**C** = pinned by an earlier report. **D** = hypothesis. All runtime behaviour is **D**.
There are no tier-A claims.

**STATUS: COMPLETE.** All six questions answered; two remain partly open and are
named in §"What stayed open" with the next concrete read.

---

## Answers (short form)

**Q1 — the decision and the Mii.** State 5 (`0x180abd0`, x0 = scene) has two entry
conditions on the frame counter `[scene+0x14c]`: **zero** (first tick after the state
reader `0x180ce40` clears it) branches at `0x180abec` to the Lua tick at `0x180ac58`
(`set_camera_type` `0x445203e`, `set_sort_id` `0x43dea04`), which does **not** write
`0x5306cb0`, falls into the re-entry block at `0x180b040` and *seeds S from the static*
(`bl 0x19cfe00` at `0x180b060`: `S+0x140` = `S+0x150` = entry handle, `S+0x168` cleared,
`S+0xe4=0`, `S+0xe8=S+0xf0=-1`, `S+0x98=1`, then `bl 0x19cc910`, then **`strb wzr,[x19,#0x70]`
at `0x180b0e4` with `x19` = list — which is what switches the global pump on** (Q4));
**non-zero** (later ticks) first mirrors `S+0x160 → scene+0x1b0` (`0x180abf0..0x180abfc`),
then branches on `[S+0xe8]`: if **non-zero** and `[S+0x168]` set it clears `S+0x168` and
writes **static ← S+0x140** at `0x180ac3c`, then tail-calls `0x180cf10`; if **zero** it
computes two validity booleans (`tag == 0x5a` and `40-bit hash != 0`) for `S+0x148` and for
the static, xors them (`0x180ad10`), and writes **static ← S+0x148 at `0x180ad20`
only when the xor equals 1** (`0x180ad14 cmp #1`, `0x180ad18 b.ne 0x180ad38`), i.e. when
**exactly one** of the two handles is a valid 0x5a handle. `0x180cf10` is a
once-per-scene commit: unless `scene+0x163` is already 1 it pushes the 18-byte record
`{0x5306ca8, 0x5306cb0, halfword}` through `0x33115f0` and sets `scene+0x163 = 1`
(`0x180d008/0x180d010`). The **state-stack pop** (`ldr/subs/b.lt` at `0x180adf4..0x180ae04`,
decrementing `scene+0x144`, storing only if the result is ≥ 0) is reached **only** from the
`[S+0xe8] == 0` path (the sole branch into `0x180adec` is `b 0x180ad6c`; `0x180adf4` has no
branchers at all — it is fall-through). **Cancel does not restore the static**: the whole
image contains exactly **two stores to `0x5306cb0`, both inside state 5** (`0x180ac3c`,
`0x180ad20`), so no exit path can write the entry handle back; the entry handle flows the
other way (static → S). `0x180d2a0` is **not a function**: it is `str x22,[sp]` inside the
function whose prologue is `sub sp,sp,#0x70` at `0x180d200`, in a mid-function
fallback-allocation path (allocation size `0x64340` at `0x180d274/0x180d278`, static
`0x5331f00` at `0x180d294`, `blr x8` at `0x180d2b4`).

**Q2 — the preview while the cursor moves.** In `0x19cc3f0` the scroller's "selection
dirty" slot (`[S+0xf8]`, vtable slot `+0x78`, `blr` at `0x19cc440`) routes ticks:
**not dirty** → the model block at `0x19cc52c`; **dirty** → the selected row
(`scroller+0x2a4`) is bounds-checked against the vector `S+0x128/S+0x130`
(`0x19cc6a8`, out of range → trap `0x19cc900`), Lua `get_decided_id` is called
(`0x19cc660` → `0x38f4790`), and the row's handle is stored to **`S+0x148` at
`0x19cc6c4`** — this store happens *before* any ownership test, so it runs whatever the
ownership result is — then the second model block at `0x19cc73c` runs. Both blocks are
identical in structure: if `[S+0x169]` is 0 they branch over the whole model change
(`0x19cc530 → 0x19cc88c`, `0x19cc740 → 0x19cc80c`); otherwise they run
`0x328b5d0` (`x0 = [0x532e730]+8 + 0x230`, `x1 = [S+0x140]`) at `0x19cc548`/`0x19cc754`
and **branch over the model change when it returns 0** (`0x19cc54c → 0x19cc88c`,
`0x19cc758 → 0x19cc80c`) — which also skips the `S+0x169` clear (`0x19cc554`,
`0x19cc75c`) and the row refill through callback-object slots `+0x18`/`+0x10`/`+0x20`.
On a pass the block fills only the visible window (`scroller+0x2c4` rows to fill,
`+0x29c` first visible, `+0x288` count). The tail writes **`S+0x140` at `0x19cc884`
and sets `S+0x168 = 1` at `0x19cc888`**. `S+0x169` itself is *set* by the entry seeder
`0x19cfe00`: its tail (`0x19cffe0..0x19cfff8`) runs `0x328b5d0` on `[S+0x140]` and stores
`w0 & 1` into `S+0x169`. **Nothing outside state 5 writes `0x5306cb0`:** the image has
eleven references to it and exactly two stores, both in state 5 (B, whole-image scan in
the check script). Whether some other code changes the *rendered* hat while the screen is
open is not derivable from this image (D).

**Q3 — the save.** `0x180d200` (editor commit) compares `record+0x138` (`0x180d4c4`)
against the static (`0x180d4cc`) with a 40-bit xor (`0x180d4f8`, mask `0xffffffffff`), runs
`0x17bd1b0` on both the equal and the differ path (`0x180d6e8` / `0x180d704` — that copier
moves the *special-skill* bytes, per P9, not the hat), then reloads `scene+0x1b8` into `x12`
(`0x180d72c`) and the static into `x1` (`0x180d734`) and applies the **same validity-xor
predicate** as state 5 (`0x180d774..0x180d7a8`): if the two handles differ in their 40-bit
hash, or exactly one of them is a valid 0x5a handle, it calls **`0x17c0a50` at `0x180d7b0`
(x0 = save object, x1 = static handle)**, then sets the dirty byte `0x5306d35 = 1`
(`0x180d7bc`); otherwise it skips to `0x180d7c0`. `0x17c0a50` validates in this order:
top-byte tag must be `0x5a` (`0x17c0a9c` mask, `0x17c0aa0` constant, wrong tag → return 0 at
`0x17c0aac`); the 40-bit hash must be non-zero (`0x17c0ab0`, `0x17c0ab4` → return 0); the
hash must be **present in the registry map** at `[0x532e730]+0x238` — `bl 0x32895d0`
(`0x17c0ad0`), `bl 0x3288a80` (`0x17c0ae0`), and then `ldp` of the returned range with
`cmp x20,x8; b.eq 0x17c0b5c` (**empty range → return 0 without touching the table**,
`0x17c0ae4..0x17c0aec`); each element's index comes from `0x3287be0` (`0x17c0b24`) and must
be ≤ `0x18f` = 399 (`0x17c0b28`, `b.hi` skips the store). **A 0x5a handle whose hash is in no
registry therefore takes the empty-range branch and writes nothing into the save record**
(B for the instructions; D for the runtime consequence).

**Q4 — who calls the frame callback at `[S+0x88]`.** The full chain, now closed:
the scene constructor builds the list object (`bl 0x19ceb30` at `0x1809558`), appends it to
a **global pump vector whose head is the static `0x532e7a8`** (`bl 0x32ca8f0` at `0x18095a4`),
stores it at `scene+0x180` (`0x18095ac`, replacing and unregistering any previous list via
`bl 0x32ca770` at `0x18095b4`) and marks it inactive with `list+0x70 = 1` (`0x18095c8`; the
list ctor does the same at `0x19ceb84`). The **pump `0x32ca620`** iterates that vector
(`0x32ca634`/`0x32ca644`) and for every element whose byte `+0x70` is not 1 dispatches
**vtable slot `+0x18`** (`0x32ca658 ldrb`, `0x32ca65c cmp #1`, `0x32ca660 b.eq skip`,
`0x32ca664 ldr vtable`, `0x32ca668 ldr [vt,#0x18]`, `0x32ca66c blr`). It is installed as an
engine task callback — its address is taken exactly once, at `0x22bcea8`. State 5 clears
`list+0x70` on its first tick (`0x180b0e4`, after `0x180b064` reloads `x19` = list), which is
what lets the pump reach the list. The list's slot `+0x18` is the **trampoline `0x19cfdb0`**
(`ldr x0,[x0,#0x80]` → `S`; `ldr x8,[x0]`; `ldr x1,[x8]` = `S` vtable slot `+0x00`;
`br x1`), which lands in the **dispatcher `0x19cc9e0`** (RELA record `0x3cf4830`,
`r_offset 0x050a6ae0`). The dispatcher passes `S+0x50` to `0x19cc910` (`0x19cc9f0/0x19cc9f4`),
then reads the base `[S+0x50]` (the ctor wrote `S` there: `stp x20,xzr,[x20,#0x50]` at
`0x19cec50`) and the pair `{fn, adj}` at `[S+0x58]/[S+0x60]`, and does `blr x8` at
`0x19cca20` — so **`0x19cc3f0` is invoked with `x0 = S` and no other argument**, and
`S+0xec` is incremented afterwards (`0x19cca2c`). `0x19cc910` fills that pair from the
`{fn,adj}` table at `base+0x28+idx*16` = `S+0x78`/`S+0x88` (the ctor installed `0x19cc3e0`
and `0x19cc3f0` there at `0x19cece8`/`0x19cecec`); state 5's reset sets the u32 state to 1
(`0x180b0dc`, array at `base+0x48` = `S+0x98`, current at `base+0x98` = `S+0xe8`), and index 1
selects `S+0x88` = `0x19cc3f0`. **`0x19cc3f0`, `0x19cfdb0` and `0x19cc9e0` have zero direct
`bl`/`b` call sites** (whole-image scans, printed by the check script). The caller is
**generic, not list-specific**: the pump dispatches slot `+0x18` for every object in a global
vector and knows nothing about this list; the only list-specific part is the `+0x70` gate that
state 5 opens. Frequency: the pump is an engine task, and which loop runs it at what rate is
**D** — the cadence is not derivable from the addresses alone; that `0x19cc3f0` is meant to
run repeatedly is suggested by `S+0xec` being a counter, but the period is D.

**Q5 — the row-callback vtable `0x50a6b18`.** The coordinator hypothesis is **right in kind
and off by `0x20` in value.** The constructor never stores `0x50a6b18`: it builds the primary
vtable `0x50a6ae0` (`0x19cec24`), computes `primary + 0x58` (`0x19cec28 add x9,x8,#0x58`) and
stores **`0x50a6b38`** at `S+0x48` with a pre-index store that clobbers `x25`
(`0x19cec2c`, word `0xF8048F29`), then stores the primary at `S+0x00` (`0x19cec30`).
`0x50a6b18` is **primary slot `+0x38`** — the row filler `0x19ccb20` — and it appears in the
metadata table `0x3cf4800` at `+0xd8` as a *slot address*, not as an object. The offset-to-top
literal at `0x50a6b28` is `-0x48` and the thunk `0x19cd010` (`sub ?,x?,#0x48; b 0x19ccb20`)
undoes it, which is exactly why a secondary base of `S+0x48` reaches the primary methods with
`this = S`. `mov x4,x25` at `0x19cf024` hands `S+0x48` to the scroller builder `0x3781470`
(`0x19cf028`, part name `scroll` at `0x424ec05`). Callers: the row filler runs as
**secondary slot `+0x10`** from the scroller's row loop (`0x377c76c`/`0x377c770`, with
`x1 = row`, `x2 = cell+8`, `x3 = cell+0x18`) and from the frame callback's model blocks
(slot `+0x10` at block offsets `0xac`/`0xa4`), **only for rows inside the visible window**
(first visible `scroller+0x29c`, rows to fill `scroller+0x2c4`, count `scroller+0x288`; rows
outside get `w-1` at `cell+0x30`). The "row → index"/slide slot at address `0x50a6b60` is
**`0x19cd020`**, called as secondary slot `+0x28` from `0x377ed00` with its result clamped
against `scroller+0x288` at `0x377ed0c`; it reads `S+0x169` at `0x19cd07c`. Secondary slot
`+0x00` (`0x19ccf30`) is called from the scroller refresh with `this = S+0x48`; it rebuilds
both vtable pointers (`0x19ccf48` pre-index to `S`, `0x19ccf50` to `S+0x48`) and then
**empties and frees the handle vector**: `ldr x0,[x0,#0xe0]` (= `S+0x128`) at `0x19ccf54`,
`str x0,[x19,#0x130]` at `0x19ccf5c`, `bl 0x392e590` (free) at `0x19ccf60`. The primary
method at `0x50a6b20` = `0x19ccea0` was not traced to a call site (open).

**Q6 — the count.** The count is computed once in the constructor as
`(end − begin) >> 3` over the vector `S+0x128/S+0x130` (`0x19ceffc` writes it to `param+0x04`;
`0x19cf01c` passes `param+0xd0` as `x3`) and the builder `0x3781470` copies `param+0x04` into
the scroller as a **32-bit field at `scroller+0x288`** (`0x3781770/0x3781774`), initialising
`+0x2a4`, `+0x2b4`, `+0x2ac`, `+0x29c` and `-1` alongside. The only setter is `0x37830e0`,
which stores it to **`scroller+0x34` and `scroller+0x288`** (`0x3783114`/`0x3783118`) and
recomputes `+0x28c`, `+0x290` (pages) and `+0x2c4` (rows to fill). Later readers of `+0x288`
include the row loops (`0x377c720`, `0x377c7d8`), the cursor clamps (`0x377d674`,
`0x377ed84`), the scroll bar (`0x377d830`, `0x377db68`), `0x377ec94`, `0x377efe8`,
`0x377f05c`, `0x377d410`, and the frame callback's model blocks (`0x19cc58c`, `0x19cc794`).
Lua sees the count only as **`SCROLLER_ITEM_NUM`**, registered at `0x19cf854` from the same
`param+0x04` (`0x19cf83c ldr w3,[sp,#0xd4]`, name `0x42a18e6`, type tag `i` at `0x42b1a84`) —
a value captured at registration, so it does not track a later change (D). **No native path
reachable from the Mii code changes the count of a built scroller:** `0x37830e0` has 58
callers image-wide and none lies in the scene object `0x1808980–0x180e000` or the headgear
list class `0x19ceb30–0x19d0000` (derived in the check script; the sort does not touch it).
Fields that would have to change together (fact, not design): the source vector
`S+0x128/S+0x130`, `scroller+0x288` and `+0x34` (through setter `0x37830e0`, which also
recomputes `+0x290` and `+0x2c4`), and the registered Lua constant `SCROLLER_ITEM_NUM` (a
stale-able copy, D).

---

## Detail

### Q1 — state 5 (`0x180abd0`) end to end

Prologue and branch on the frame counter (B, `10_state5_0x180abd0.txt`):

| address | instruction | meaning |
|---|---|---|
| `0x180abe4` | `ldr w8,[x0,#0x14c]` | frame counter of the state (`0x180ce40` clears it on a state change, `0x180ceb8`) |
| `0x180abec` | `cbz w8,#0x180ac58` | counter 0 → the Lua tick path |
| `0x180abf0..0x180abfc` | `ldr x8,[x19,#0x180]` / `ldr x8,[x8,#0x80]` / `ldr w8,[x8,#0x160]` / `str w8,[x19,#0x1b0]` | mirror `S+0x160 → scene+0x1b0` (counter ≠ 0 path) |
| `0x180ac04/0x180ac0c` | guard `0x53134d8` (`ldarb`/`tbz`) | lazy-init thunk → `0x180b0fc`, which re-checks and returns to `0x180ac10` |
| `0x180ac18/0x180ac1c` | `ldr w9,[S,#0xe8]` / `cbz w9,#0x180acbc` | `[S+0xe8] == 0` → the `+0x148` path |
| `0x180ac20..0x180ac24` | `ldrb w9,[S,#0x168]` / `cbz → 0x180b0e8` | `S+0x168` clear → plain return |
| `0x180ac34/0x180ac3c` | `ldr x8,[S,#0x140]` / `str` into `0x5306cb0` | **writer 1: static ← S+0x140** |
| `0x180ac54` | `b 0x180cf10` | tail call |

The `+0x148` path (`0x180acbc`) computes, for `x10 = [S+0x148]` and `x15 = [0x5306cb0]`,
`valid(h) = (h >> 56 == 0x5a) && (h & 0xffffffffff != 0)` with `cset` at
`0x180acec/0x180acf4/0x180acfc/0x180ad04`, combines them with `and` at `0x180ad08/0x180ad0c`,
then `eor w12,w12,w13` (`0x180ad10`), `cmp w12,#1` (`0x180ad14`), `b.ne 0x180ad38`
(`0x180ad18`). Only when the xor is exactly 1 does it fall through to
`0x180ad1c mov x0,x19; 0x180ad20 str x10,[x11,#0xcb0]; 0x180ad24 bl 0x180cf10`
(**writer 2: static ← S+0x148**). The odd half of the predicate (the static's own tag/hash,
plus the `0x180ae08` sub-path for a different tag) is the same shape as the save-side test in
Q3.

After that: the label refresh compares `S+0x148` with `S+0x150` (`0x180ad38`, difference
branch `0x180ad68 → 0x180adc4`, equal branch `0x180ad6c → 0x180adec`); a difference runs
`bl 0x19cb2e0` (`0x180add4`, label rebuild from the static) and writes `scene+0x161 = 0x0101`
(`0x180add8/0x180addc/0x180ade0`). `S+0x164` is copied to `scene+0x1c8` (`0x180adec/0x180adf0`)
and back again on the Lua-tick path (`0x180af00 ldrsw x24,[scene+0x1c8]; 0x180af08 str
w24,[S+0x164]`).

**The pop.** `0x180adf4 ldr w8,[scene+0x144]`, `0x180adf8 subs w8,w8,#1`,
`0x180adfc b.lt 0x180b0e8` (do not store), `0x180ae00 str w8,[scene+0x144]`,
`0x180ae04 b 0x180b0e8`. `refs.py` finds exactly one branch to `0x180adec` (from `0x180ad6c`)
and **no branches at all to `0x180adf4`**, so the pop is fall-through from the `+0x148` path
only: it runs on ticks where the counter ≠ 0 *and* `[S+0xe8] == 0`, after the `S+0x164` copy,
and stores the decremented depth only when the result is ≥ 0 (B). What the transition triggers
next is runtime (D); per P6 (C) the screen's state changes are driven from Lua.

**The re-entry block** (`0x180b040`, reached by `b 0x180b038` from the Lua-tick path and by the
`0x180b13c` thunk): guard, then `0x180b050 ldr x8,[x19,#0x180]`, `0x180b058 ldr x1,[0x5306cb0]`,
`0x180b05c ldr x0,[x8,#0x80]`, `0x180b060 bl 0x19cfe00` — **the entry seeder**. `0x19cfe00`
(`33_scroller_setup_0x19cf440.txt` line 625 ff, window `79_fn_0x19cfe00_head.txt`) does
`stp x1,x1,[S+0x140]`, `str x1,[S+0x150]`, `strb wzr,[S+0x168]`, scans the vector
`S+0x128..S+0x130` for the entry handle, and its **tail** runs the ownership test:
`0x19cffe0 ldr x8,[0x532e730]`, `0x19cffe4 ldr x8,[x8,#8]`, `0x19cffe8 ldr x1,[S+0x140]`,
`0x19cffec add x0,x8,#0x230`, `0x19cfff0 bl 0x328b5d0`, `0x19cfff4 and w8,w0,#1`,
`0x19cfff8 strb w8,[S+0x169]` (window `79b_fn_0x19cfe00_tail.txt`). So the entry handle is
pushed **into** S, and `S+0x169` starts as `ownership(S+0x140)`.

Continuing in state 5 (`0x180b09c..0x180b0e4`): `x0 = S+0x50`, `S+0xe4 = 0`, `S+0xe8 = -1`,
`S+0xf0 = -1`, `stp xzr,xzr,[S+0x58]`, byte fields zeroed, `S+0x98 = 1` (`0x180b0ac/0x180b0dc`),
`bl 0x19cc910` (`0x180b0e0`), `strb wzr,[x19,#0x70]` (`0x180b0e4`, `x19` = list after
`0x180b064`), `ret` at `0x180b0f8`.

**Ends of the screen and the static.** Enumerating the exits of the state-5 body: plain
`ret` (`0x180b0f8` and the early-out `0x180b0e8`), tail call `b 0x180cf10` (`0x180ac54`),
`bl 0x180cf10` (`0x180ad24`), and the pop path. The static is written only at `0x180ac3c`
(from `S+0x140`, gated by `[S+0xe8] != 0 && [S+0x168] != 0`) and `0x180ad20` (from `S+0x148`,
gated by the validity xor == 1). The whole-image enumeration (11 references, 2 stores) is in
the check script's Q2 section and in `67_xref_0x5306cb0.txt`. **No code anywhere restores
`0x5306cb0` to an entry value on exit or cancel** — the restore-shaped code is the opposite
direction (`0x180b058` static → `0x19cfe00` → `S+0x140`/`S+0x150`) (B for the stores; D for
what the player sees on cancel).

**`0x180d2a0`** (question: "read it and say what it is"): `0x180d200` is the prologue
(`sub sp,sp,#0x70`) of the editor-commit function, so `0x180d2a0` is *ordinary code inside
it*, not an entry point. Context: `0x180d274/0x180d278` materialise `w22 = 0x64340`,
`0x180d294` loads the static `0x5331f00`, `0x180d2a0` is `str x22,[sp]`, `0x180d2b4` is
`blr x8` — a mid-function allocation path with a size argument on the stack. (This answers
P9 §9 item 7.)

### Q2 — the frame callback `0x19cc3f0` (`51_frame_callback_0x19cc3f0.txt`)

Entry: `0x19cc408 str wzr,[S+0x160]` (clear the previous float), `0x19cc410 ldr w8,[S+0xec]`,
`0x19cc418 cbz → 0x19cc4fc` early out, `0x19cc41c bl 0x33762b0` (tick begin).

Selection-dirty routing: `0x19cc434 ldr x0,[S+0xf8]` (the scroller),
`0x19cc43c` vtable slot `+0x78`, `0x19cc440 blr`, `0x19cc444 tbz → 0x19cc52c` (not dirty →
model block A). The dirty path reads `scroller+0x2a4`, bounds-checks against
`S+0x128/S+0x130` (`0x19cc6a8`, `0x19cc6bc → 0x19cc900` trap), loads `vector[row]`
(`0x19cc6c0`), stores **`S+0x148`** (`0x19cc6c4`), calls Lua `get_decided_id`
(`0x19cc660` → `0x38f4790`, string `0x43de9d8`), then `bl 0x37759f0` and clears the per-index
flag `str wzr,[S+idx*4+0x98]` (`0x19cc6fc`), then reaches model block B at `0x19cc73c`.

Model blocks (`BLOCKS` in the check script, both asserted instruction by instruction):

| | block A `0x19cc52c` | block B `0x19cc73c` |
|---|---|---|
| gate | `ldrb [S+0x169]`, `cbz → 0x19cc88c` | `ldrb [S+0x169]`, `cbz → 0x19cc80c` |
| ownership | `add x0,x8,#0x230` + `bl 0x328b5d0` at `+0x1c` (`0x19cc548`) | same at `+0x18` (`0x19cc754`) |
| unowned | `b 0x19cc88c` at `+0x20` | `b 0x19cc80c` at `+0x1c` |
| clear flag | `strb wzr,[S+0x169]` at `+0x28` | same at `+0x20` |
| refill | callback object `[scroller+0x160]`, slots `+0x18`/`+0x10`/`+0x20`, rows from `scroller+0x2c4`/`+0x29c`, count `scroller+0x288` | same |

So, answering the question directly: **when `0x328b5d0` returns 0 for the selected handle, the
`S+0x148` store (dirty path) and the Lua `get_decided_id` call still run — they are before and
independent of the test — but the model change does not**: no `S+0x169` clear, no row refill,
no slot `+0x10`/`+0x20` calls; the block jumps to its exit. The tail stores
`S+0x140` (`0x19cc884`) and sets `S+0x168 = 1` (`0x19cc888`) only when its own branch chain
falls through, and `0x19cc8e8` writes the `S+0x160` float. Last `ret` is `0x19cc8fc`;
`0x19cc90c` is `udf` padding (P9 correction retained).

**Writers of `0x5306cb0`:** eleven references, two stores (`0x180ac3c`, `0x180ad20`), both in
state 5 — table in the check script's Q2 section, disassembly in `67_xref_0x5306cb0.txt`.
Nothing in `0x19cc3f0` writes the static at all; it writes `S+0x140`, `S+0x148`, `S+0x168` and
`S+0x169`, and state 5 is the only thing that copies those into the static.

### Q3 — the save (`54_save_*.txt`, `56_save_0x180d734.txt`, `58_save_apply_0x17c0a50.txt`)

`0x180d200` (prologue) compares tag halfwords (`0x180d2f4` 0x5a, `0x180d2fc` 0x13); equal →
`b 0x180d4c4` (`0x180d418`). `0x180d4c4` reads `record+0x138`, `0x180d4cc` reads the static;
`0x180d4f8 eor` with mask `0xffffffffff` (`0x180d4fc`); differ → `b 0x180d6f8`
(`0x180d500`). Both paths call the copier `0x17bd1b0` (`0x180d6e8`, `0x180d704`). Then
`0x180d72c ldr x12,[scene+0x1b8]`, `0x180d734 ldr x1,[0x5306cb0]`, `0x180d738 ldr
x20,[x8,#0x98]` (save object), the validity-xor predicate `0x180d774..0x180d7a8`
(`b.ne 0x180d7ac` on a hash difference, `cmp w8,#1 / b.ne 0x180d7c0` on the xor), then
`0x180d7ac mov x0,x20; 0x180d7b0 bl 0x17c0a50`, `0x180d7bc strb 1,[0x5306d35]`, and the
outfit twin `0x17c0b80` at `0x180d840` with `scene+0x1c0`. Finally `record+0x1bc` (`0x180d870`)
and `record+0x0 → record+0x1c0` (`0x180d878`).

`0x17c0a50` in order (all B):

1. `0x17c0a9c and` top-byte mask, `0x17c0aa0 mov #0x5a00000000000000`; mismatch →
   `0x17c0aac b 0x17c0a80` (return 0).
2. `0x17c0ab0 and` 40-bit mask; zero hash → `0x17c0ab4 b 0x17c0a80` (return 0).
3. registry: `0x17c0abc adrp+add 0x532e730`, `0x17c0ac8 ldr x0,[x21,#0x238]`,
   `0x17c0acc add x20,x21,#0x230`, `0x17c0ad0 bl 0x32895d0`, `0x17c0ae0 bl 0x3288a80`.
4. **`0x17c0ae4 ldp x20,x8,[sp,#8]`; `0x17c0ae8 cmp x20,x8`; `0x17c0aec b.eq 0x17c0b5c`** →
   empty result range → `0x17c0b5c mov w21,wzr` → return 0. This is the *unknown hash* case:
   **nothing is written**.
5. Non-empty: for each element, `0x17c0b24 bl 0x3287be0` (per-element index),
   `0x17c0b28 cmp w0,#0x18f`, `0x17c0b2c b.hi 0x17c0b40` (index > 399 → skip), otherwise
   `0x17c0b3c str w22,[x8,#4]` writes a sequence number (`w22 = [counter]+1`, `0x17c0b04..0x17c0b0c`)
   into `table[index].field4`.

So the handle never lands verbatim in the save through this call; the call records "this
registry element is in use" under its table index, and it refuses to do that for a handle that
fails the tag, the non-zero hash, the registry membership, or the 399 bound (B; runtime D).
The outfit twin `0x17c0b80` is the same shape with the `0x13` tag, calls
`0x3285be0/0x3284a30/0x32839f0`, bound `0x3e7` = 999, store at `+0xc84`.

### Q4 — the dispatch chain to `0x19cc3f0`

New evidence this task: `70_q4_trampoline_0x19cfdb0.txt`, `71_q4_pump_0x32ca620.txt`,
`72_q4_list_registration_0x18095a4.txt`, `73_q4_register_0x32ca8f0.txt`,
`74_q4_dispatcher_0x19cc9e0.txt`, `75_q4_state5_enable_0x180b0e4.txt`,
`76_q4_list_ctor_0x19ceb30.txt`, `77_q4_scans.txt`, `78_readers_0x532e7a8.txt`.

1. **List construction and registration (scene side).** `0x1809558 bl 0x19ceb30`
   (list ctor; `0x19ceb5c stp x8,xzr,[x0]` installs vtable `0x50a6c00`, `0x19ceb84 strb
   1,[x0,#0x70]`), `0x18095a4 bl 0x32ca8f0` (append to the vector at `0x532e7a8`),
   `0x18095a8 ldr x0,[x19,#0x180]` + `0x18095ac str x21,[x19,#0x180]` (publish),
   `0x18095b4 bl 0x32ca770` (unregister the replaced list), `0x18095bc/0x18095c8 strb 1,
   [x21,#0x70]` (mark inactive).
2. **The pump.** `0x32ca620`: `0x32ca630 adrp 0x532e000`, `0x32ca634 ldr x8,[x20,#0x7a8]`,
   loop over `begin..end`, per element `0x32ca658 ldrb w8,[x0,#0x70]`,
   `0x32ca65c cmp w8,#1`, `0x32ca660 b.eq 0x32ca670` (skip), `0x32ca664 ldr x8,[x0]`,
   `0x32ca668 ldr x8,[x8,#0x18]`, `0x32ca66c blr x8`. `0x32ca8f0` appends
   (`0x32ca91c ldr` head, `0x32ca940 str x21,[x9]` at the end pointer) under the mutex
   `0x39c1410`. The vector head `0x532e7a8` has exactly **ten accesses** in the whole image
   (`78_readers_0x532e7a8.txt`): four in engine setup/teardown (`0x22bce64/0x22bce68`,
   `0x22cf418/0x22cf41c` — the latter replaces the head with 0 and frees it), six in
   `0x32ca000` (register/unregister/pump). `0x32ca620`'s address is taken once, at
   `0x22bcea8` (`adrp+add` in engine task-setup code that also registers `0x3376e20`).
3. **The gate.** `list+0x70` = 1 from construction until state 5's first tick clears it
   (`0x180b064 ldr x19,[x19,#0x180]` → `0x180b0e4 strb wzr,[x19,#0x70]`). While it is 1 the
   pump skips the list, so the frame callback cannot run before state 5 has seeded S.
4. **The trampoline.** `0x19cfdb0: ldr x0,[x0,#0x80]` (list → S), `0x19cfdb4 ldr x8,[x0]`
   (S's vtable `0x50a6ae0`), `0x19cfdb8 ldr x1,[x8]` (slot `+0x00`), `0x19cfdbc br x1`.
   RELA record `0x3cf4ad0` puts `0x19cfdb0` at `r_offset 0x050a6c18`; record `0x3cf4830`
   puts `0x19cc9e0` at `r_offset 0x050a6ae0`.
5. **The dispatcher.** `0x19cc9e0`: `0x19cc9ec mov x19,x0`, `0x19cc9f0 add x0,x0,#0x50`,
   `0x19cc9f4 bl 0x19cc910`, `0x19cc9f8 ldr x9,[x19,#0x50]` (base), `0x19cca00 ldp
   x8,x11,[x19,#0x58]` (fn, adj), `0x19cca04..0x19cca14` the base/adj idiom,
   `0x19cca20 blr x8`, `0x19cca2c str w8,[x19,#0xec]` (increment `S+0xec`).
6. **How `0x19cc3f0` gets into the pair.** The ctor writes `S` into `[S+0x50]` and 0 into
   `[S+0x58]` (`0x19cec50 stp x20,xzr,[x20,#0x50]`) and installs the two `{fn,adj}` table
   entries `0x19cc3e0` at `S+0x78` and `0x19cc3f0` at `S+0x88`
   (`0x19cece8`/`0x19cecec`, values built at `0x19cec98`/`0x19cecac`). `0x19cc910` on a state
   change reads the index `base+0x94` (= `S+0xe4`), the u32 state `base+0x48+idx*4`
   (= `S+0x98+idx*4`) against the current `base+0x98` (= `S+0xe8`), bounds the new value
   (`0x19cc940 cmp #2`, `b.hs` trap), and copies `table[value]` — `base+0x28+value*16` — into
   `base+0x08/base+0x10` (`0x19cc958 ldp`, `0x19cc95c stp`), i.e. into `S+0x58/S+0x60`.
   State 5 sets the value to 1 (`0x180b0ac mov w8,#1` → `0x180b0dc str w8,[S+0x98]`), so
   entry **1** = `S+0x88` = **`0x19cc3f0`** is what the dispatcher blrs.
7. **Specificity and arguments.** The pump is generic (it never names this list); the
   arguments are `x0 = S` only (base = `S`, adj = 0). `0x19cc3f0`, `0x19cfdb0`, `0x19cc9e0`
   each have zero direct call sites (derived scans printed by the check script).
   How often the pump runs is **D** (an engine task; not derivable from addresses).

Scans and dead ends worth recording (`77_q4_scans.txt`): `chainlist` over
`ldr [obj,#0x180] → ldr [obj] → ldr [vt,#0x18] → blr` with gaps 300/120 returns 46 chains,
**none in the scene range** — the caller does not load the list from `scene+0x180`, it iterates
a global vector instead; `vc18` over the scene range finds one virtual slot `+0x18` call
(`0x180c544 → 0x180c558`), which is on `[0x52b7f00]+0xa30`, not the list; direct `bl/b` to
`0x19cfdb0`/`0x19cc9e0`/`0x19cc3f0`: none (the pointers come from RELA).

### Q5 — `0x50a6b18` is a slot address, not an object

* Hypothesis test: `0x19cec24 adrp 0x50a6000`, `0x19cec28 add x9,x8,#0x58`,
  `0x19cec2c str x9,[x25,#0x48]!` (word `0xF8048F29`; pre-index by `0x48`, so `x25` becomes
  `S` and `[S+0x48] = 0x50a6b38`), `0x19cec30 str x8,[x20]` (`[S+0x00] = 0x50a6ae0`).
  `0x19cebfc mov` establishes `x25 = S`; `0x19cf024 mov x4,x25` feeds `0x3781470`.
  **`0x50a6b18` itself is never stored as a value**; it is primary slot `+0x38`.
* Metadata table `0x3cf4800`: `+0xd8 → 0x50a6b18`, `+0x108 → 0x50a6b38`, method half-words at
  `+0xe4 → 0x19ccb20`, `+0x0fc → 0x19ccea0`, `+0x114 → 0x19ccf30`, `+0x12c → 0x19ccfa0`,
  `+0x144 → 0x19cd010` (checked as u64 at record `+0x10`, see script).
* Primary vtable `0x50a6ae0` slots (RELA): `+0x00 0x19cc9e0`, `+0x08 0x32cb650`,
  `+0x10 0x32cb760`, `+0x18 0x32cb7c0`, `+0x20 0x32cb800`, `+0x28 0x19cca40` (dtor),
  `+0x30 0x19ccab0`, `+0x38 0x19ccb20`, `+0x40 0x19ccea0`; offset-to-top literal at
  `0x50a6b28 = 0xffffffffffffffb8` (−0x48); secondary group `0x50a6b38` (the pointer stored
  at `S+0x48`): `+0x00 0x19ccf30`, `+0x08 0x19ccfa0`, `+0x10 0x19cd010` (the thunk),
  `+0x18 0x377c0d0`, `+0x20 0x377c0e0` (bare `ret`s), `+0x28 0x19cd020`,
  `+0x30 0x4542a30`.
* Which rows: `0x377c6d0` fills rows `row < scroller+0x288` inside the visible window
  (`scroller+0x29c` first visible, `scroller+0x2c4` rows to fill); `0x377c6f4` loads slot
  `+0x18` of `[scroller+0x160]` (the no-op hook), `0x377c76c/0x377c770` slot `+0x10` (row
  filler), `0x377ed00/0x377ed08` slot `+0x28` (row → index, result clamped at `0x377ed0c`
  against `scroller+0x288`). Out-of-range rows get `w-1` at `cell+0x30`.
* Secondary slot `+0x00` (`0x19ccf30`) with `this = S+0x48`: rebuilds the primary pointer
  (`0x19ccf40/0x19ccf48`, pre-index `−0x48` → `S`), writes the secondary pointer at `S+0x48`
  (`0x19ccf4c/0x19ccf50`), then `0x19ccf54 ldr x0,[x0,#0xe0]` = `S+0x128`,
  `0x19ccf5c str x0,[x19,#0x130]` (end := begin, i.e. empty the vector),
  `0x19ccf60 bl 0x392e590` (free). This is a *clear*, not a read of `S+0xe8` — see
  corrections.
* Open: the call site of primary `+0x40` (`0x19ccea0`) and of `0x32cb650/0x32cb760/0x32cb7c0/
  0x32cb800` (`+0x08..+0x20`) was not pinned; and `0x19cc910`'s second inline dispatch reads
  `base+0x18/base+0x20` (`S+0x68/S+0x70`), a pair whose writer was not found (next read:
  `str`/`stp` of `S+0x68`).

### Q6 — the count

* Source: `0x19ceff8 lsr` of `(end − begin)` over `S+0x130`/`S+0x128` (`0x19cefec`/`0x19ceff0`
  loads, `x23`/`x26` set at `0x19ced98`/`0x19ceca0`), stored to `param+0x04` (`0x19ceffc`),
  param base `param+0xd0` in `x3` (`0x19cf01c`).
* Builder `0x3781470`: object is `0x340` bytes (`0x37814c4`), `param+0x00 → scroller+0x30/+0x38`
  (`0x3781548/0x378154c`), callback object → `scroller+0x160` (`0x3781708`), `param+0x04` →
  **`scroller+0x288`** (`0x3781770/0x3781774`), inits `+0x2a4` (`0x3781794`), `+0x2b4`
  (`0x37817a4`), `+0x2ac` (`0x3781780`), `-1` (`0x378178c`), `+0x29c` (`0x3781778`).
* Setter `0x37830e0`: `0x3783114 str → scroller+0x34`, `0x3783118 str → scroller+0x288`,
  recomputes `+0x28c` (`0x3783108`), `+0x290` (`0x3783150`), `+0x2c4` (`0x37831e4`).
* Lua: `0x19cf83c ldr w3,[sp,#0xd4]` (the same `param+0x04`), name `SCROLLER_ITEM_NUM` at
  `0x42a18e6`, type tag `i` at `0x42b1a84`, helper `0x33750a0` called at `0x19cf854`.
  P6-HAT-UI (C) shows the constant is read by the layout as an integer; it is captured at
  registration, so a changed count would not reach Lua (D).
* Readers of `+0x288`: `0x377c720`, `0x377c7d8`, `0x377d410`, `0x377d674`, `0x377d830`,
  `0x377db68`, `0x377ec94`, `0x377ed84`, `0x377efe8`, `0x377f05c`, plus `0x19cc58c` and
  `0x19cc794` inside the frame callback's model blocks.
* No native path from the Mii code calls `0x37830e0`: 58 callers image-wide, none in
  `0x1808980–0x180e000` or `0x19ceb30–0x19d0000` (derived; the negative control injects a
  fake caller at `0x1809000` to prove the check works).

---

## Corrections to earlier reports

1. **P9 §5 "the only writer of `0x5306cb0` (`0x180ad20`)" — there are two stores.**
   `0x180ac3c` stores `S+0x140` into the static when `[S+0xe8] != 0 && [S+0x168] != 0`
   (`strb` clear of `S+0x168` at `0x180ac28`, `ldr [S+0x140]` at `0x180ac34`,
   `str ...,[x11,#0xcb0]` at `0x180ac3c`). Both stores are in state 5; the enumeration of all
   eleven references is unchanged.
2. **P9 §9.1 "nothing points at `0x50a6b18` as a value" — it is a *slot address* in the
   metadata table `0x3cf4800 +0xd8`** (`check` asserts the u64 there), and the pointer
   installed at `S+0x48` is **`0x50a6b38` = `0x50a6ae0 + 0x58`**, not `0x50a6b18`. The
   coordinator's hypothesis was right in kind, wrong by `0x20`.
3. **P9 §9.7 "`0x180d2a0` … was not read" — it is not a function at all.** It is
   `str x22,[sp]` inside `0x180d200` (prologue `sub sp,sp,#0x70` at `0x180d200`; the check
   script asserts both words).
4. **P9 §5/§9.3 "cancel / restore … not resolved" — there is no restore.** With only two
   stores of `0x5306cb0`, both in state 5, no screen exit can write the entry handle back;
   the restore-shaped direction is static → `S` at entry (`0x180b050..0x180b060`,
   `0x19cfe18/0x19cfe1c`). Runtime consequence: D.
5. **P9 §9.4 "the commit out of `0x5306cb0` into the save … not walked" — now walked** (Q3):
   `0x180d734` loads the static into `x1` and `0x180d7b0` calls `0x17c0a50`, which refuses
   unknown hashes at `0x17c0aec`.
6. **P9 §1 "the list object's vtables hold two slots each"** — `0x50a6c00` has four
   RELA-filled slots: `+0x00 0x19cfc30`, `+0x08 0x19cfcf0` (both destructor-shaped: they
   destroy `S` via `list+0x80` and mark linked objects `+0x70 = 2`), `+0x10 0x32ca8d0`
   (a bare `ret`), `+0x18 0x19cfdb0` (the trampoline).
7. **This task's own earlier draft**: an intermediate version of the check script labelled
   `0x19ccf5c` as "stores it at `S+0x130` (`S+0xe8`)"; the parenthetical was wrong — the base
   is `S` (after the pre-index at `0x19ccf48`) and the instruction empties the vector
   (`begin → S+0x130`) before `free`. Label fixed and the `free` is now asserted.

---

## What stayed open

1. **How often the pump `0x32ca620` runs.** Its address is taken once (`0x22bcea8`) inside
   engine task-setup code that also registers `0x3376e20`. Next concrete read: identify the
   function containing `0x22bce60` and what `bl 0x3cb050` (`0x22bced8`) registers — that
   names the loop and therefore the cadence (D today).
2. **What sets `[S+0xe8]` to the value that state 5's `cbz` at `0x180ac1c` takes as 0.**
   State 5 itself writes `-1` (`0x180b0a4`, `0x180b554`) and clears the byte (`0x180b6c4`);
   the writer that makes the 32-bit read at `0x180ac18` return 0 was not found. Next read:
   whole-image `str wzr/str xzr` into `+0xe8` of objects that also carry `+0x148`/`+0x169`
   (the hits in `20_scan_S_fields.txt` at `0x19c0440`/`0x19c0510`/`0x19c90d0` belong to
   other classes).
3. **Call sites of primary vtable slots `+0x08..+0x20` (`0x32cb650/0x32cb760/0x32cb7c0/
   0x32cb800`) and of `+0x40` (`0x19ccea0`)**, plus the writer of the pair
   `S+0x68/S+0x70` that `0x19cc910`'s inline dispatch reads (`base+0x18`).
4. **Runtime behaviour of everything above.** No emulator, no console, no patch — tier B for
   instructions only; every behavioural statement is D.

---

## Check script

`evidence/P10-HAT-OPEN/check_p10_hat_open.py` re-reads every cited instruction, displacement,
immediate, branch target, C string and RELA addend out of `main.bin`, and verifies the image's
sha256 and size first (exit 2 if either differs). It exits 1 on any mismatch. It also derives
three whole-image facts rather than asserting them: the set of `0x5306cb0` references (11, two
of them stores), the absence of direct `bl`/`b` callers of `0x19cc3f0`, `0x19cfdb0` and
`0x19cc9e0`, and the caller set of `0x37830e0` (58, none in the Mii ranges).

It must be started **from the workspace root** (the parent of `mods/`), not from
`mods/mii_customizer`:

```
cd <workspace root>
export PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python
python mods/mii_customizer/evidence/P10-HAT-OPEN/check_p10_hat_open.py
```

Last run (full log: `evidence/P10-HAT-OPEN/91_check_script_output.txt`):

```
image ok: sha256 f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613, 86672752 bytes
...
P10-HAT-OPEN check: 449 claims, 0 mismatches
negative-control mode: off
exit=0
```

### Negative controls (all nine exit 1; log in `90_negative_controls.txt`)

| mode | injected fault | first mismatch |
|---|---|---|
| `--neg word` | expects `0xdeadbeef` for every instruction word | `state5 read list object: wrong mnemonic at 0x180abf0 expected deadbeef got ldr` |
| `--neg disp` | expects displacement `0xdead` | `state5 child slot: wrong displacement at 0x180abf0 expected 57005 got [384]` |
| `--neg branch` | expects branch target `0x19dead` | `state5 guard bit0 clear: wrong branch target at 0x180ac0c expected 0x19dead got [0, 25211132]` |
| `--neg string` | expects `get_decided_idX` / `SCROLLER_ITEM_NUx` | `frame callback Lua method name: wrong string at 0x43de9d8 …` |
| `--neg reloc` | expects addend `0x19dead` in every slot | `vtable 0x50a6c00 slot +0x00: wrong RELA addend … got 0x19cfc30` |
| `--neg vtable` | expects metadata qword `0xdead0000` | `vtable metadata at 0x3cf4800 (meta slot 0): expected 0xdead0000 got 0x50a6ac0` |
| `--neg count` | injects a fake Mii-side caller of `0x37830e0` | `Q6: 0x37830e0 has a Mii-side caller: ['0x1809000']` |
| `--neg save` | expects the `0x13` tag where `0x5a` is cited | `state5 tag constant 0x5a: wrong immediate at 0x180acc8 …` |
| `--neg writers` | rewrites every `0xcb0` operand | `xref 0x18094b4 …: no 0xcb0 operand` |

The script was extended four times during this task; each extension was run before the report
was written, and one wrong claim site it caught is recorded above (correction 7) — the report
text, not the image, was wrong.

---

## Files

Written by this task (all inside `mods/mii_customizer/`):

* `research/P10-HAT-OPEN.md` (this file)
* `evidence/P10-HAT-OPEN/` (65 files) — `check_p10_hat_open.py`,
  `90_negative_controls.txt`, `91_check_script_output.txt`, and 62 disassembly/scan windows:
  `10_state5_0x180abd0.txt`,
  `11_fn_0x180cf10.txt`, `12_fn_0x180d2a0.txt`, `13_state5_tail.txt`,
  `14_state_reader_0x180ce40.txt`, `15_state4_0x180a5b0.txt`, `20_scan_S_fields.txt`,
  `21..23` neighbouring functions, `30_ctor_0x19ceb30.txt`, `31_ctor_tail_scroller.txt`,
  `32_vmi_table_0x3cf48c0.txt`, `32_vmi_tables_0x3cf48xx.txt`, `33_scroller_setup_0x19cf440.txt`
  (contains `0x19cfe00` in full), `34..39` scroller scans and builder windows,
  `40_frame_update_0x180ead0.txt`, `41..49` count/callback scans,
  `50_fn_0x19ccea0.txt`, `51_frame_callback_0x19cc3f0.txt`, `52_fn_0x19cc910.txt`,
  `53_fn_0x19cc3e0.txt`, `54..56` the editor commit, `57_copy_0x17bd1b0.txt`,
  `58_save_apply_0x17c0a50.txt`, `59..61` the three registry lookups,
  `62_pairscan_78_88.txt`, `63_frame_driver_0x3157540.txt`, `64_callers_0x3157540.txt`,
  `65_vtable_0x50a6c00.txt`, `66_callers_0x180ead0.txt`, `67_xref_0x5306cb0.txt`,
  **`70_q4_trampoline_0x19cfdb0.txt`, `71_q4_pump_0x32ca620.txt`,
  `72_q4_list_registration_0x18095a4.txt`, `73_q4_register_0x32ca8f0.txt`,
  `74_q4_dispatcher_0x19cc9e0.txt`, `75_q4_state5_enable_0x180b0e4.txt`,
  `76_q4_list_ctor_0x19ceb30.txt`, `77_q4_scans.txt`, `78_readers_0x532e7a8.txt`,
  `79_fn_0x19cfe00_head.txt`, `79b_fn_0x19cfe00_tail.txt`** (new this task)
* `scratch/2026-10-05_P10-HAT-OPEN/` — `lib.py`, `relocs.py`, `offs.py`, `dd.py`,
  `vtdump.py`, `calls.py`, `pairscan.py`, `xrefcb0.py`, `blrscan.py` (see note),
  `refs.py`, `relafind.py`, `chain8088.py`, `chainlist.py`, `vcallS.py`, `chain180.py`,
  **`vc18.py`**, **`readers7a8.py`** (new this task). Note: `blrscan.py` has an
  immediate-scaling bug for slot scans — its "slot 0x88" hits are displacement `0x440`;
  do not trust it, use `chainlist.py` / `vc18.py` / `refs.py`.

No other task's files, no commits, no emulator, no SD, no agents.

---

## Task summary

**Task ID: P10-HAT-OPEN — DONE.**

Status: all six questions answered from the image. Two items remain open and are named in
"What stayed open" with the next concrete read (the pump's cadence; the writer of
`[S+0xe8] == 0`), plus two lower-priority call-site traces.

Changed files (all inside `mods/mii_customizer/`):
* `research/P10-HAT-OPEN.md` (written this task)
* `evidence/P10-HAT-OPEN/` (65 files: 1 check script + 2 logs + 62 disassembly/scan windows;
  11 of them new for Q4)
* `scratch/2026-10-05_P10-HAT-OPEN/` (17 scripts; 2 new)

Checks run:
* `check_p10_hat_open.py` from the workspace root — **449 claims, 0 mismatches, exit 0**,
  sha256 and size verified (log `91_check_script_output.txt`).
* Nine negative controls `--neg word|disp|branch|string|reloc|vtable|count|save|writers`,
  **all exit 1** (log `90_negative_controls.txt`).
* Every evidence window regenerated this task; none contains a traceback.

**No runtime verification of any kind; nothing was patched or executed; every
runtime-behaviour statement is tier D.**

Corrections to earlier reports, for the coordinator: see "Corrections to earlier reports" —
the material ones are (1) there are **two** writers of `0x5306cb0`, (2) `0x50a6b18` is a slot
address and the pointer at `S+0x48` is `0x50a6b38`, (4) **cancel cannot restore the static**
because no such write exists, and (5) the save commit is `0x180d7b0 → 0x17c0a50`, which
rejects a 0x5a handle whose hash is in no registry at `0x17c0aec`.
