# P4-BRIDGE-FACTS - how Lua arguments reach the skill handlers, and what a hook there must respect

Task: `prompts/P4-BRIDGE-FACTS.md`. Date 2026-10-04. Status: **DONE** (offline static, locating/reading only).
No emulator, console or SD access; nothing executed. **B** = instruction read from the image in
this task; **C** = pinned prior report; **D** = hypothesis. No runtime behaviour is claimed.

## Input and method

`gamedata/ssbu-13.0.4/main.bin` (workspace-relative), sha256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`, 86672752 bytes.
Rehashed at the start of this task - **matches** (`evidence/P4-BRIDGE-FACTS/00_input_identity.txt`).
Flat `MOD0` image, address == file offset. capstone 5.0.7 via the pinned
`mods/ssbu_mod_new/builds/.cache/dk_cargo/python`. Tools: unmodified copies of `d.py`,
`relocs.py`, `lib.py` from `scratch/2026-10-04_P3-CUSTOMIZE-SITES/`, plus `rawwin.py`,
`analyze.py`, `q5_backward.py`, `check_p4.py` in `scratch/2026-10-04_P4-BRIDGE-FACTS/`.

Commands (from `mods/mii_customizer/`):

```
sha256sum gamedata/ssbu-13.0.4/main.bin
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python scratch/2026-10-04_P4-BRIDGE-FACTS/analyze.py
PYTHONPATH=... python scratch/2026-10-04_P4-BRIDGE-FACTS/q5_backward.py
PYTHONPATH=... python scratch/2026-10-04_P4-BRIDGE-FACTS/check_p4.py   # 318 checks, 0 failures, exit 0
```

Raw windows: `evidence/P4-BRIDGE-FACTS/03_handler_windows.txt`, `03b_handler_words.txt`,
`04*/05*` (the two thunks), `06_thunk_0x19dc650_ref.txt`, `07_thunk_0x19dd480.txt`,
`08_analyze.txt`, `09_q5_backward.txt`, `10_string_handler_0x3907950.txt`,
`11_extra_windows.txt`, `12_claim_check.txt`.

## How to read the Lua-stack offsets

Both thunks receive `x0` = the delegate object `d` and `x1` = a lua-state/stack-structure
pointer `p` (saved as x20/x19). Every argument is read **directly from the Lua stack**, never
through an indexed API call:

- `[p+0x10]` is the stack top S (a byte address).
- `[p+0x20]` holds a pointer whose dereference is a stack lower bound used in the cleanup.

A Lua value there is a 16-byte slot: value at +0, type tag (u32) at +8. So the value at
`S-0x10` has its tag at `S-0x8`. The **last** pushed argument is `S-0x10`; the one before it is
`S-0x20`. The one-argument reference thunk `0x19dc650` (C, P1-ID-REVIEW 2.3; re-read here,
`06_thunk_0x19dc650_ref.txt`) reads only `S-0x10` and passes it in `x1` - which fixes the
direction: **the two-argument thunk's `S-0x20` slot is the first Lua argument, `S-0x10` the
second.**

---

## Q1. Thunk `0x19dd950` (two-argument form: `set_skill_id`, `replace_skill`)

Full function `0x19dd950..0x19ddac4` (tail branch) plus cold blocks `0x19ddac8..0x19ddb24`;
words in `evidence/P4-BRIDGE-FACTS/04b_thunk_0x19dd950_words.txt`. Register roles: `d = x19`
(delegate, from x0 at `0x19dd974`), `p = x20` (from x1 at `0x19dd970`).

**Argument 1 ("row")** - read first, from `S-0x20`:

| step | address | instruction |
|---|---|---|
| S | `0x19dd964` | `ldr x8, [x1, #0x10]` |
| slot | `0x19dd968` | `sub x21, x8, #0x20` |
| type tag | `0x19dd96c` | `ldur w8, [x8, #-0x18]` |

Type dispatch (`0x19dd978`..`0x19dd9a4`) then produces a value in `x21`:

- tag `0x13` (integer): `0x19dd978` `cmp w8,#0x13`; `b.ne 0x19dd988`; `0x19dd980` `ldr x21,[x21]`
  (the raw 64-bit value); `0x19dd984` `b 0x19dd9e8` (done).
- reload tag at `0x19dd988` `ldr w8,[x21,#8]` (same address): `0x19dd98c` `cmp w8,#0x13`;
  `0x19dd990` `b.eq 0x19dd980`.
- tag `3` (float): `0x19dd994` `cmp w8,#3`; `0x19dd998` `b.eq 0x19ddac8` (cold block).
- other tags: `0x19dd99c` `and w8,w8,#0xf`; `0x19dd9a0` `cmp w8,#4`; `0x19dd9a4` `b.ne 0x19dd9e4`
  (reject → `x21 = 0`); tag&0xf==4 (string) falls to `0x19dd9a8`.
- string path `0x19dd9a8..0x19dd9e0`: `x0 = [x21] + 0x18` (byte data of the string object),
  `x1 = sp` (scratch), `bl 0x3907950`; then the string length is recomputed
  (`0x19dd9bc` `ldrb w9,[x8,#8]`, `cmp #4` short/long at `0x19dd9c0`, len+1 at `0x19dd9d4`),
  `x21 = sp` (`0x19dd9d8`), and if the call's return equals len+1 it loops back to `0x19dd988`
  (so the parsed value in the stack buffer is treated as the argument); otherwise reject.
- reject: `0x19dd9e4` `mov x21, xzr`.
- float cold `0x19ddac8..0x19ddaf4`: `ldr s0,[x21]`; c1 = `[0x44718f4]` = `0xdf000000` (`-2^63`);
  `0x19ddad4` **`frintm s0, s0`** (floor); `fcmp`/`b.lt 0x19dd9e4` rejects `< -2^63`
  (`0x19ddadc`); c2 = `[0x4471e68]` = `0x5f000000` (`+2^63`); `fcmp`/`b.pl 0x19dd9e4` rejects
  `>= 2^63` or unordered/NaN (`0x19ddaec`); `0x19ddaf0` **`fcvtzs x21, s0`** (float→signed 64-bit,
  round toward zero); `0x19ddaf4` `b 0x19dd9e8`.

**Argument 2 ("value")** - read from `S-0x10`, identical dispatch, result in `x2`:

| step | address | instruction |
|---|---|---|
| slot | `0x19dd9e8`/`0x19dd9ec` | `ldr x8,[x20,#0x10]` / `sub x22,x8,#0x10` |
| type tag | `0x19dd9f0` | `ldur w8, [x8, #-8]` |
| integer | `0x19dd9fc` | `ldr x2, [x22]` |
| reject | `0x19dda60` | `mov x2, xzr` |
| float | `0x19ddaf8..0x19ddb24` | same `frintm`/range/`fcvtzs x2, s0` (`0x19ddb20`) |

**Stack cleanup** `0x19dda64..0x19dda94`: `x8 = *[p+0x20]`, `x8 += 0x10`; while `S < x8`, it
writes `0x10` to top and `str wzr,[x9,#8]` (clears the two slots to nil); finally
`0x19dda94` `str x8, [p, #0x10]` resets the top. This is the "pop both arguments" step; a hook
that runs after the thunk sees the stack already reset.

**Handler call** `0x19dda98..0x19ddac4`:

```
0x19dda98  ldp x8, x3, [x19, #0x10]   ; x8 = d[+0x10] (owner), x3 = d[+0x18] (handler/member)
0x19dda9c  ldr x9, [x19, #0x20]       ; x9 = d[+0x20]
0x19ddaa0  add x0, x8, x9, asr #1     ; pointer-to-member: x0 = d[+0x10] + (d[+0x20]>>1)
0x19ddaa4  tbz w9, #0, 0x19ddab0      ; low bit 0 -> non-virtual, keep x3
0x19ddaa8  ldr x8, [x0]
0x19ddaac  ldr x3, [x8, x3]           ; else virtual: x3 = vtable[d[+0x18]]
0x19ddab0  mov w1, w21                ; w1 = argument 1
0x19ddab4..0x19ddac0  restore frame / sp
0x19ddac4  br x3                      ; TAIL BRANCH (not blr)
```

So the handler is reached with **`x0` = owner object** (here the 0x150-byte screen object),
**`w1` = argument 1 (row)**, **`x2` = argument 2 (value)**. `br x3` is a tail branch, so the
handler returns straight to the thunk's caller; there is no return-value handling here.

**Registration actually used by `set_skill_id`** (`0x19de0ec..0x19de104`): vtable 0x50a6e78
(`0x19de0ec` `adrp x21`, `0x19de0f0` `add x21,x21,#0xe78`); handler built in code as
`0x19de0f4` `adrp x8,#0x19dc000` + `0x19de0f8` `add x8,x8,#0xf20` = `0x19dcf20`;
`0x19de0fc` `str x21,[x0]`; `0x19de100` `str xzr,[x0,#0x20]`; `0x19de104`
`stp x19, x8, [x0,#0x10]`. So `d[+0x10]=owner`, `d[+0x18]=0x19dcf20`, `d[+0x20]=0` - the thunk's
primary `+0x18` path, non-virtual.

**Accepted types (B):** integer tag `0x13` (64-bit value used as is), float tag `3` (floored,
range-checked, `fcvtzs`), string tag `&0xf == 4` (parsed by `0x3907950`; accepted only if the
whole string is consumed). **Not accepted** (nil, boolean, lightuserdata, table, function,
userdata, thread, or a failed string parse) become `x21 = 0` / `x2 = 0`. **There is no argument
count check**: if an argument is absent, the 16-byte slot below the top is read anyway; a slot
whose tag is not one of the accepted ones is treated as rejected (0). The call `0x3907950` takes
`x0 = string bytes (TString+0x18)`, `x1 = sp` and, on the observed re-dispatch on `[sp+8]`/`[sp]`,
writes a Lua TValue into that buffer (D); the prologue (`10_string_handler_0x3907950.txt`) is a
`__ctype_b`-table byte loop (table `0x4861970`) - no symbol string names it.

---

## Q2. Thunk `0x19dd7d0` (`get_skill_id`, one Lua argument)

Full function `0x19dd7d0..0x19dd8f4` (`ret`), cold block `0x19dd8f8..0x19dd934`;
words in `evidence/P4-BRIDGE-FACTS/05b_thunk_0x19dd7d0_words.txt`. `d = x20` (x0), `p = x19` (x1).

**Argument** - `S-0x10`: `0x19dd7e4` `ldr x8,[x1,#0x10]`; `0x19dd7e8` `sub x21,x8,#0x10`;
`0x19dd7ec` `ldur w8,[x8,#-8]`. Dispatch identical in shape to Q1: integer `0x13` →
`0x19dd800` `ldr x1,[x21]`; float `3` → cold `0x19dd908..0x19dd934` with `frintm` (`0x19dd914`),
range check against `0xdf000000`/`0x5f000000`, and `0x19dd930` `fcvtzs x1, s0`; string
`&0xf==4` → `0x19dd828..0x19dd860` (same `0x3907950` parse); reject → `0x19dd864`
`mov x1, xzr`. Stack cleanup `0x19dd868..0x19dd898` (resets top to `*[p+0x20]+0x10`).

**Handler call - primary path `+0x28` first:**

```
0x19dd89c  ldp x8, x11, [x20, #0x28]  ; x8 = d[+0x28], x11 = d[+0x30]
0x19dd8a0  ldr x10, [x20, #0x10]      ; owner
0x19dd8a4  and x9, x11, #1
0x19dd8a8  orr x12, x9, x8
0x19dd8ac  cbz x12, 0x19dd8f8         ; both zero -> fallback
0x19dd8b0  add x0, x10, x11, asr #1   ; pointer-to-member
0x19dd8b4  cbz x9, 0x19dd8c0          ; non-virtual -> call x8
0x19dd8b8  ldr x9, [x0]
0x19dd8bc  ldr x8, [x9, x8]           ; virtual
0x19dd8c0  blr x8                     ; CALL (not tail branch)
```

**Fallback path `+0x18`** (`0x19dd8f8..0x19dd904`): `ldp x8,x9,[d+0x18]`;
`add x0, x10, x9, asr #1`; `tbnz w9,#0` → virtual via `0x19dd8b8`; else `b 0x19dd8c0`.

**Return value handed back to Lua** (`0x19dd8c4..0x19dd8e0`):

```
0x19dd8c4  ldr x9, [x19, #0x10]   ; top
0x19dd8c8  sxtw x8, w0            ; sign-extend ONLY the low 32 bits
0x19dd8cc  str x8, [x9]           ; value
0x19dd8d0  mov w8, #0x13
0x19dd8d4  str w8, [x9, #8]       ; type tag 0x13 (integer)
0x19dd8d8  ldr x8, [x19, #0x10]
0x19dd8dc  add x8, x8, #0x10
0x19dd8e0  str x8, [x19, #0x10]   ; top += 0x10
```

So: **`w0` is sign-extended (`sxtw`) to 64 bits, stored as the Lua value, with type tag `0x13`
(integer), pushed inline** (no push call); only the low 32 bits of the handler's return are used;
there is no masking or zero-extension. `0x19dd8f4` `ret`.

**Which registration path is used.** `0x19de19c..0x19de1b4`: `0x19de19c` `adrp x9,#0x19dc000` +
`0x19de1a0` `add x9,x9,#0xf40` = `0x19dcf40`; vtable 0x50a6ea0 built at `0x19de194`/`0x19de198`;
`0x19de1ac` `stp x19, xzr, [x0,#0x10]` → `d[+0x10]=owner`, **`d[+0x18]=0`**;
`0x19de1b0` `str xzr,[x0,#0x30]` → `d[+0x30]=0`; `0x19de1b4` `stp xzr, x9, [x0,#0x20]` →
`d[+0x20]=0`, **`d[+0x28]=0x19dcf40`**. Because `d[+0x28] != 0`, the **primary `+0x28` path is
used** (and `+0x30 == 0` so `x9 = 0`, i.e. non-virtual). The `+0x18` fallback is explicitly
disarmed (`d[+0x18] = 0`, `d[+0x20] = 0`).

---

## Q3. The two handlers `0x19dcf20` (set) and `0x19dcf40` (get)

Whole functions (`03b_handler_words.txt`):

```
set 0x19dcf20: 7100103f  cmp w1,#4
    0x19dcf24: 54000082  b.hs 0x19dcf34
    0x19dcf28: 8b21c008  add x8, x0, w1, sxtw
    0x19dcf2c: 39040102  strb w2, [x8, #0x100]
    0x19dcf30: d65f03c0  ret
    0x19dcf34: a9bf7bfd  stp x29, x30, [sp, #-0x10]!   (cold block)
    0x19dcf38: 910003fd  mov x29, sp
    0x19dcf3c: 947f9459  bl 0x39c20a0
get 0x19dcf40: 7100103f  cmp w1,#4
    0x19dcf44: 54000082  b.hs 0x19dcf54
    0x19dcf48: 8b21c008  add x8, x0, w1, sxtw
    0x19dcf4c: 39440100  ldrb w0, [x8, #0x100]
    0x19dcf50: d65f03c0  ret
    0x19dcf54: a9bf7bfd  stp x29, x30, [sp, #-0x10]!   (cold block)
    0x19dcf58: 910003fd  mov x29, sp
    0x19dcf5c: 947f9451  bl 0x39c20a0
```

**PC-relative word among the first four:** only **word 2** (index 1), the `b.hs`, at `0x19dcf24`
/ `0x19dcf44`. Words 1, 3, 4 (`cmp`, `add`, `strb`/`ldrb`) are not PC-relative.

**Direct branches/calls in the image targeting the function start or an address inside it:**
for `0x19dcf20`, exactly one - the internal `0x19dcf24 b.hs -> 0x19dcf34`. For `0x19dcf40`,
**none**. (Scan over the whole TEXT range; `analyze.py`/`check_p4.py`.)

**Relocated pointers equal to the function start:** **none** for either handler (no
`R_AARCH64_RELATIVE` addend equals `0x19dcf20`/`0x19dcf40`), and **no raw 8-byte qword** equals
either address in the file. The address is only built in code, in the delegate construction:
`0x19de0f4` `adrp x8,#0x19dc000` + `0x19de0f8` `add x8,x8,#0xf20` (set) and `0x19de19c`
`adrp x9,#0x19dc000` + `0x19de1a0` `add x9,x9,#0xf40` (get).

**`0x39c20a0`, the cold block's `bl` target** (`08_analyze.txt`, `11_extra_windows.txt`). First
12 instructions:

```
[12 lines of game disassembly removed for publication; regenerate them from your own 13.0.4 main with this report's check script]
```

These are three 4-instruction **indirect-branch (PLT-style) stubs**; the window contains **no
`ret`** and each entry terminates in `br x17`. The slot `0x529f208` holds file qword `0x39bfa70`
(no `R_AARCH64_RELATIVE` record for that slot), and `0x39bfa70` is itself a resolver entry
(`stp x16,x30,[sp,#-0x10]!; adrp x16,#0x529d000; ldr x17,[x16,#0xef8]; add x16,x16,#0xef8; br x17`).
So on these instructions **`0x39c20a0` does not return in-line - it leaves by indirect branch**;
whether the eventual resolved callee returns is not visible in this window. Both cold blocks have
no epilogue after the `bl` (control would otherwise fall into the next function), which is what a
compiler emits for a noreturn call (D).

---

## Q4. `replace_skill 0x19dd1a0` and `replace_skill_subwindow 0x19dd250` (first 8 words)

```
[17 lines of game disassembly removed for publication; regenerate them from your own 13.0.4 main with this report's check script]
```

**PC-relative among the first 8 words:** **none** in either function (all are a frame save, `add`
and `mov`/`ldr` with immediate offsets).

**Direct branches/calls targeting start/inside.** `replace_skill` (main `0x19dd1a0..0x19dd240`,
cold `0x19dd244` `bl 0x39c0d80` at `0x19dd244`, padding `0x19dd248` `udf #0`): exactly two, both
internal - `0x19dd1c4 b.eq -> 0x19dd244` and `0x19dd224 cbz x19 -> 0x19dd230`.
`replace_skill_subwindow` (main to `0x19dd468` `ret`, extra block `0x19dd46c` `bl 0x39c0d80`,
`0x19dd470 cbz x0,0x19dd478`, `0x19dd474 b 0x392e590`, `0x19dd478 ret`): **11** inbound branches,
all internal - `0x19dd284 b.ls -> 0x19dd46c`, `0x19dd2dc`, `0x19dd2f0`, `0x19dd334`, `0x19dd374`,
`0x19dd380`, `0x19dd3bc`, `0x19dd3fc`, `0x19dd408`, `0x19dd444` (all `cbz`), and `0x19dd470
cbz -> 0x19dd478`.

**Relocated pointers equal to the function start:** **none** for either (no RELATIVE addend, no
raw qword). The addresses are built in code: `0x19de39c` `adrp x8,#0x19dd000` + `0x19de3a0`
`add x8,x8,#0x1a0` (replace_skill) and `0x19de444` `adrp x9,#0x19dd000` + `0x19de448`
`add x9,x9,#0x250` (replace_skill_subwindow), stored into the delegates at `0x19de3a8` /
`0x19de454` (`+0x18` each).

Note the cold blocks of these two call **`0x39c0d80`**, not `0x39c20a0` - a different target from
the two skill handlers (addresses only; not interpreted).

---

## Q5. Are `x19` (object) or `x23` (outer object) stored to a static address in `0x19ddb30`?

Function `0x19ddb30..0x19de6b0`. The 0x150-byte object is allocated at `0x19ddb8c`
`mov w0,#0x10` / `0x19ddb90` `bl 0x392dce0` (with `w1 = 0x150` at `0x19ddb80`), and
`0x19ddb94` `mov x19, x0` takes the result. The outer object is `x23` (`0x19ddb6c mov x23, x0`).
The six registrations then build delegate objects and store their fields (`0x19de0ec..`,
`0x19de1a4..`, ...).

**Result (B):** within `0x19ddb30..0x19de6b0` there is **no store whose base is an adrp-derived
address that carries x19 or x23** - and, more strongly, **no store with an adrp-derived base at
all**. Two independent methods agree, both exit 0:

- `analyze.py` q5 - forward tracking that invalidates a register's adrp provenance on **any**
  write: 0 stores.
- `q5_backward.py` - for every store, walks the base register back to its most recent definition
  and roots the chain in an `adrp`: 0 stores (`09_q5_backward.txt`).

Stores that look adrp-based in a naive scan are false positives from register reuse, verified
explicitly: `x8` is set to the object at `0x19ddbf0` `mov x8, x19`, so `0x19ddc08`
`str xzr,[x8,#0x30]!` writes the **object**, not a static; the earlier `adrp` value that had
been in x8 was consumed by `0x19ddba0` `ldr x0,[x8,#0xf00]`. Stores of the object go to heap fields, e.g.
`0x19ddd80` `str x19,[x23,#0x80]` (object into the outer object's `+0x80`).

The adrp materialisations that do exist in this function are used as loaded values/arguments and
as bases of object-relative writes, never as static store bases: vtable 0x50a6e20
(`0x19ddbf4/f8`), 0x50a6ef0 (`0x19de440` region), 0x50a6f18 (`0x19ddb50/f4`), and a code-embedded
table near `0x19dcc70`/`0x19dcc80`. Conclusion for the live object: **on these instructions the
screen object (`x19`) and the outer object (`x23`) cannot be found from any static address written
inside this constructor.** (The scene keeps the outer object at `[scene+0x198]` / `[scene+0x5e8]`,
per C in P2-SKILL-STORE; those stores are outside this function and were not re-scanned here.)

---

## Q6. The editor working record `W` at `0x5306b78`

**`0x180fca8..0x180fcb4`:**

```
0x180fca8: f001d7b5  adrp x21, #0x5306000
0x180fcac: 912de2b5  add x21, x21, #0xb78      ; x21 = 0x5306b78
0x180fcb0: aa1503e2  mov x2, x21
0x180fcb4: 97fee157  bl 0x17c8210               ; loader(pass W as x2)
```

**`0x180d31c..0x180d328`:**

```
0x180d31c: b001d7da  adrp x26, #0x5306000
0x180d320: b94b7b41  ldr w1, [x26, #0xb78]       ; w1 = first u32 of W (saved-fighter ID)
0x180d324: aa1503e0  mov x0, x21
0x180d328: 97feec82  bl 0x17c8530
```

Both use `0x5306b78` (B). The second site reaches it through `adrp x26` + `ldr [x26,#0xb78]`
(`0x180d31c`/`0x180d320`); the first loads `W` in `x21` and passes it in `x2`. The first u32 of
`W` (`[0x5306b78]`) is read into `w1` at the commit-check call - consistent with `W+0` being the
saved-fighter ID (C, P2-SKILL-STORE).

**All `adrp+add` materialisations of exactly `0x5306b78` in the code range: 14.**

| # | adrp | add |
|---|---|---|
| 1 | `0x1809a94` | `0x1809a98` |
| 2 | `0x180d41c` | `0x180d420` |
| 3 | `0x180d6d4` | `0x180d6d8` |
| 4 | `0x180d6f8` | `0x180d6fc` |
| 5 | `0x180d864` | `0x180d868` |
| 6 | `0x180d8a4` | `0x180d8bc` |
| 7 | `0x180d8b8` | `0x180d8bc` |
| 8 | `0x180fc4c` | `0x180fc50` |
| 9 | `0x180fca8` | `0x180fcac` |
| 10 | `0x1812b24` | `0x1812b28` |
| 11 | `0x181506c` | `0x1815070` |
| 12 | `0x19cadc4` | `0x19cadc8` |
| 13 | `0x22f7e34` | `0x22f7e38` |
| 14 | `0x22f8f64` | `0x22f8f68` |

(Sites 6 and 7 share the completion `0x180d8bc`; the materialisation count is 14, giving 12
distinct `add` completions. The `0x180d31c`/`0x180d320` use above is an `adrp+ldr` and is not in
this list.)

---

## Value passed from Lua → value seen by the handler

For both thunks; argument 1 = first Lua arg (`set_skill_id`/`replace_skill` row), argument 2 =
second Lua arg (value). Handler sees arg1 in `w1` (`mov w1, w21`), arg2 in `x2`.

| Lua value (type tag) | thunk action (addresses) | value seen by handler |
|---|---|---|
| integer `0x13` | `ldr x21/x2, [slot]` directly (`0x19dd980`, `0x19dd9fc`) | raw 64-bit value; handler reads `w1`/`w2` = low 32 bits (no check, no masking at the thunk) |
| float `3` | `frintm` floor, range `[-2^63, 2^63)`, `fcvtzs` to signed 64-bit (`0x19ddad4/0x19ddaf0`, `0x19ddb04/0x19ddb20`, `0x19dd914/0x19dd930`) | truncated integer: floor of the float, e.g. `2.9 -> 2`, `-2.1 -> -3`; handler reads low 32 bits |
| string with `tag & 0xf == 4` | `bl 0x3907950` with the string bytes and `sp` buffer; accepted only if bytes consumed == strlen+1 (`0x19dd9a8..e0`, `0x19dda24..5c`, `0x19dd828..60`); then re-dispatched as integer/float | as the parsed integer/float above; a non-numeric or partially numeric string -> rejected (0) |
| nil, boolean, lightuserdata, table, function, userdata, thread | not matched; `mov x21, xzr` / `mov x2, xzr` (`0x19dd9e4`, `0x19dda60`, `0x19dd864`) | `0` |
| missing argument | no count check; reads `S-0x20`/`S-0x10` anyway | whatever tag sits there; if not accepted, `0` (D for "missing", B for "no count check") |
| handler return (`get_skill_id`) | `sxtw x8, w0`; tag `0x13`; top += 0x10 (`0x19dd8c8..e0`) | Lua integer = sign-extended low 32 bits of the handler's `w0` |

---

## Observed checks, failures and limits

- Input sha256 rehash matched (`00_input_identity.txt`).
- `check_p4.py`: **318 checks, 0 failures, exit 0** (`12_claim_check.txt`). It re-reads every
  word cited above (both thunks whole, both handlers whole with cold blocks, both replace
  functions' first 8 words, the registration sites, the `0x39c20a0` window, the Q6 sites and
  constants), plus the structural claims: PC-relative classification, inbound-branch sets,
  absence of relocated pointers equal to the four starts, the Q5 zero-store result, and the
  14-entry `0x5306b78` xref set.
- No failed approach to record. The first Q5 forward scan produced 10 false hits because it did
  not invalidate a scratch register's adrp provenance on a `mov`; fixed, and cross-checked with
  the independent backward scan. The buggy intermediate output is not retained as evidence.
- Limits: everything here is static. No runtime claim that these thunks are actually invoked,
  or that the arguments have the listed Lua types in play. `0x3907950` is described by address
  and observed arguments only; naming it a number/string parser is D. The "noreturn" reading of
  the cold-block call is D. The `+0x20`/base semantics of `p` are described by offset, not named.
  Whether the two skill handlers are the only such bridge is out of scope.

## Closing summary

- **Task ID:** P4-BRIDGE-FACTS
- **Status:** DONE
- **Changed files:**
  - `research/P4-BRIDGE-FACTS.md` (new, this file)
  - `evidence/P4-BRIDGE-FACTS/` (new): `00_input_identity.txt`, `03_handler_windows.txt`,
    `03b_handler_words.txt`, `04_thunk_0x19dd950.txt`, `04b_thunk_0x19dd950_words.txt`,
    `05_thunk_0x19dd7d0.txt`, `05b_thunk_0x19dd7d0_words.txt`, `06_thunk_0x19dc650_ref.txt`,
    `07_thunk_0x19dd480.txt`, `08_analyze.txt`, `09_q5_backward.txt`,
    `10_string_handler_0x3907950.txt`, `11_extra_windows.txt`, `12_claim_check.txt`
  - `scratch/2026-10-04_P4-BRIDGE-FACTS/` (new): `d.py`, `relocs.py`, `lib.py` (unmodified
    copies), `rawwin.py`, `analyze.py`, `q5_backward.py`, `check_p4.py`
- **Verified checks:** input hash; 318/318 claim checks exit 0; Q5 result reproduced by two
  independent methods; the two-argument thunk's `S-0x20`/`S-0x10` argument ordering confirmed
  against the one-argument reference thunk `0x19dc650`.
- **Next experiment (offline):** follow the handler's `x0` back to the object on the *other*
  input type - i.e. whether anything writes the `+0x100` bytes other than the four rows already
  covered by P2-SKILL-STORE - is not needed for the bridge itself; the open bridge question is
  whether the `0x3907950` string path can be relied on for arbitrary Lua strings, which needs a
  runtime trace (console, tier A) since its accepted set depends on the parser's behaviour, not on
  the instructions around it.
