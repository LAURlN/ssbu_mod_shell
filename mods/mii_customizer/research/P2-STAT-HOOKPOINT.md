# P2-STAT-HOOKPOINT - which function the engine's slot-0x270 calls reach, and what the old mod's hook patches

Task `P2-STAT-HOOKPOINT`. Worker: Space Bunny Alpha. Date 2026-10-04.
Prompt: `prompts/P2-STAT-HOOKPOINT.md`. Coordinator review:
`research/COORDINATOR-2026-10-04.md`.

**Locating task. No hook was built and nothing was run.** Every claim below is a
static read of one file, or a quote from pinned source. **No tier A. No emulator,
no console, no SD access, no commits, no branches, no edits to other workers'
files.** Tiers: **B** offline measurement of the local image; **C** pinned external
source; **D** hypothesis.

## Headline

The two questions have different answers and the difference is the useful result.

1. **The old mod's hook patches an exported `lua_bind` wrapper at `0x208de50`,
   which is 4 instructions long and dispatches through vtable slot `+0x268`.**
2. **The 21 engine call sites P2-STAT-READS found dispatch through slot
   `+0x270`.**

`+0x268` and `+0x270` are different slots, so on the evidence in this task the
hook is on a different entry point than the engine reads. **This is a statement
about two different offsets in the image (B), not a claim about what the hook
does at runtime (unverified).** Whether replacing `0x208de50` also changes what
the `+0x270` call sites observe depends on runtime behaviour that no offline read
here can settle - a hook framework may redirect the vtable, may only patch the
one entry, or the two entries may forward to each other. §1.5 says what would
settle it.

3. **§2.6 (added on a second pass): the `+0x268`/`+0x270` architecture the prompt
   describes does exist in this image, at two vtables.** Vtables `0x4f73738` and
   `0x4f89490` have a `+0x268` slot (`0x4e53d0`) that loads the vtable and branches
   through slot `+0x270`, and the `0x4f89490` instance is stored at **offset
   `+0x50` of a parent object** (`str x20, [x19, #0x50]` @`0x688584`, B). This is
   the closest structural match found. It is **not** shown to be `WorkModule`: the
   `+0x270` body reads no argument registers and rebases through `[x0+0x38]`.

Two corrections to an earlier draft of this report are recorded in place, in §2.4
and §2.2; both concerned construction-site attribution and both are now asserted
by the check script. §2.6 exists because the Part 2 reduction (filter F4) was
found to discard exactly the forwarder-shaped evidence the prompt asks about.

## 1. Part 1 - what the old mod actually hooks

### 1.1 The symbol resolution (C, read from pinned source)

`#[skyline::hook(replace = WorkModule::get_param_float)]` in
`mods/ssbu_mod_new/src/pgwr/plugin/src/params.rs:348` resolves through
`skyline-smash` `315e4e8`, **not** through `smash-rs`. The plugin depends on
`skyline_smash` (`src/pgwr/plugin/Cargo.toml:60`), whose `[lib] name = "smash"` is
why the source says `use smash::...`. In that crate `app::WorkModule` is an
`extern "C"` block, so `WorkModule::get_param_float` is an imported function with
a `#[link_name]` (`src/cpp.rs:11420`):

```rust
#[link_name = "\u{1}_ZN3app8lua_bind32WorkModule__get_param_float_implEPNS_26BattleObjectModuleAccessorEmm"]
pub fn get_param_float(
    module_accessor: *mut root::app::BattleObjectModuleAccessor,
    parent_param: libc::c_ulong,
    child_param: libc::c_ulong,
) -> f32;
```

The `\u{1}` prefix is skyline's marker for a symbol resolved from the host module's
dynamic symbol table. So the hook target is the mangled name
`_ZN3app8lua_bind32WorkModule__get_param_float_implEPNS_26BattleObjectModuleAccessorEmm`,
**not** a vtable slot.

Note the `impl` in the mangled name. That is the same word `smash-rs`
`ddacc5e` `src/app/modules/work.rs:1213-1216` uses for the entry it declares at
**`+0x268`**, whose doc comment says *"This function is called internally by
`get_param_float`"* and *"This function is not exported by the main executable,
the name is assumed"*. That comment is wrong about the export; §1.2 shows it is
exported. **That contradiction is reported rather than resolved.**

### 1.2 The symbol is exported, at 0x208de50 (B)

Located by parsing the MOD0 dynamic section of the image, then the `DT_SYMTAB`
at `0x4197610` with `DT_STRTAB` at `0x41c11f0`. `DT_HASH` (`0x4181748`) gives
`nchain = 7124` symbols.

| dynsym index | address | size | symbol |
|---|---|---|---|
| 5475 | **`0x208de50`** | `0x10` | `_ZN3app8lua_bind32WorkModule__get_param_float_implEPNS_26BattleObjectModuleAccessorEmm` |
| 4794 | `0x208de30` | `0x10` | `...WorkModule__get_param_int_impl...` |
| 2385 | `0x208de40` | `0x10` | `...WorkModule__get_param_int64_impl...` |
| 6162 | `0x208de60` | `0x10` | `...WorkModule__set_customize_no_impl...` |

### 1.3 First 20 instructions at 0x208de50 (B)

Exactly 4 instructions, then the next function:

```
0x0208de50: ldr     x0, [x0, #0x50]
0x0208de54: ldr     x8, [x0]
0x0208de58: ldr     x3, [x8, #0x268]      <-- slot +0x268
0x0208de5c: br      x3
0x0208de60: ldr     x0, [x0, #0x50]      (next function: set_customize_no_impl)
0x0208de64: ldr     x8, [x0]
0x0208de68: ldr     x3, [x8, #0x278]
0x0208de6c: br      x3
0x0208de70: stp     x22, x21, [sp, #-0x30]!
   ... 12 more instructions of the next function ...
```

Raw window: `evidence/P2-STAT-HOOKPOINT/win_0x208de30_24.txt`.

**This answers the prompt's Part 1 question directly:** the function at the hook
address is a **wrapper that loads `[x0+0x50]` and tail-jumps through the vtable
at slot `+0x268`**. It is not the slot-`+0x270` target.

The whole `lua_bind WorkModule` block `0x208db50..0x208de70` is 48 such 4-instruction
thunks with the identical shape (`ldr x0,[x0,#0x50]` / `ldr x8,[x0]` /
`ldr xN,[x8,#imm]` / `br xN`), each dispatching to a different slot. Their 48
distinct slot offsets are the requirement set used in Part 2. Full listing with
each slot: `evidence/P2-STAT-HOOKPOINT/step2b_workmodule_thunks.txt`.

| thunk | slot | thunk | slot | thunk | slot |
|---|---|---|---|---|---|
| `0x208db50` | `+0x00b` | `0x208dc50` | `+0x01d` | `0x208dd70` | `+0x031` |
| `0x208db60` | `+0x00c` | `0x208dc60` | `+0x01e` | `0x208dd80` | `+0x032` |
| `0x208db70` | `+0x00e` | `0x208dc70` | `+0x01f` | `0x208dd90` | `+0x033` |
| `0x208db80` | `+0x00f` | `0x208dc80` | `+0x021` | `0x208dda0` | `+0x034` |
| `0x208db90` | `+0x010` | `0x208dc90` | `+0x022` | `0x208ddb0` | `+0x035` |
| `0x208dba0` | `+0x011` | `0x208dca0` | `+0x024` | `0x208ddc0` | `+0x036` |
| `0x208dbb0` | `+0x012` | `0x208dcd0` | `+0x027` | `0x208ddd0` | `+0x037` |
| `0x208dbc0` | `+0x013` | `0x208dce0` | `+0x028` | `0x208dde0` | `+0x038` |
| `0x208dbd0` | `+0x014` | `0x208dcf0` | `+0x029` | `0x208ddf0` | `+0x039` |
| `0x208dbe0` | `+0x016` | `0x208dd00` | `+0x02a` | `0x208de00` | `+0x03f` |
| `0x208dbf0` | `+0x017` | `0x208dd10` | `+0x02b` | `0x208de10` | `+0x040` |
| `0x208dc00` | `+0x018` | `0x208dd20` | `+0x02c` | `0x208de20` | `+0x044` |
| `0x208dc10` | `+0x019` | `0x208dd30` | `+0x02d` | `0x208de30` | `+0x049` |
| `0x208dc20` | `+0x01a` | `0x208dd40` | `+0x02e` | `0x208de40` | `+0x04b` |
| `0x208dc30` | `+0x01b` | `0x208dd50` | `+0x02f` | **`0x208de50`** | **`+0x04d` (= +0x268)** |
| `0x208dc40` | `+0x01c` | `0x208dd60` | `+0x030` | `0x208de60` | `+0x04f` |

Two of the 50 16-byte slots in that range are not thunks (`0x208dcb0` is the
last half of `set_flag`, which continues past the 16-byte stride, and
`0x208dcc0` is `br x3` + three `udf` padding words). 48 decode as thunks.

`0x208dcc0` is worth one note: it is `br x3` followed by `udf #0` padding, i.e. it
is the tail of the `set_flag` entry, not a thunk. It is excluded.

### 1.4 The engine sites use +0x270, not +0x268 (B)

The coordinator's own re-read, re-derived here by decoding the instruction
fields rather than by trusting the text:

```
0x02db55b8: ldr     x8, [x20, #0x20]      rn=x20, rt=x8, imm=0x20
0x02db55bc: ldr     x0, [x8, #0x50]       rn=x8,  rt=x0, imm=0x50
0x02db55c0: ldr     x8, [x0]              rn=x0,  rt=x8, imm=0
0x02db55c4: ldr     x8, [x8, #0x270]      rn=x8,  rt=x8, imm=0x270   <-- slot +0x270
0x02db55c8: mov     x1, #0x5541
0x02db55cc: movk    x1, #0x7cd, lsl #16
0x02db55d0: movk    x1, #6, lsl #32       -> x1 = 0x0607cd5541 (the `weight` hash)
0x02db55d4: mov     x2, xzr
0x02db55d8: blr     x8
```

So the site loads `[accessor+0x50]`, then `[that+0x270]`, and passes the hash in
`x1` with `x2 = 0`. **The `+0x268`/`+0x270` difference is measured from the two
instruction streams, not inferred from a binding.**

### 1.5 What is NOT established here

The exported wrapper at `0x208de50` has **zero direct `bl` callers** anywhere in
`0x100..0x39C8000`, and exactly **one 8-byte pointer to it in the image**, at
`0x41b7760`. That single pointer sits in what is plainly a registration table:

```
0x41b7750: 0x10
0x41b7758: 0x0002001200_06cb3   (name hash)
0x41b7760: 0x208de50            (function pointer)
0x41b7768: 0x10                 (size = 16 bytes = 4 instructions, matches)
0x41b7770: 0x0002001200_04e8f   (next name hash)
0x41b7778: 0x3669d0             (next function pointer)
0x41b7780: 0x30                 (next size)
```

A name hash / pointer / size triple in `.rodata` is the shape of the `lua2cpp`
export table (C, consistent with the `lua_bind` prefix in the symbol and with
skyline-smash's `lua2cpp` module existing in the same crate). **This is an
inference from table shape and is marked D.** It is consistent with the wrapper
being reachable from the script marshalling layer rather than from engine C++
call sites, but the table is not decoded far enough here to prove what reads it.

**Therefore: I cannot state that the old mod's hook misses the engine reads.** I
can state that the hook address and the engine call sites are different
addresses resolving different vtable slots. Whether replacing `0x208de50`
changes the `+0x270` result is a runtime question this task did not and cannot
answer. This is the single most important limit in this report.

### 1.6 Handbook statements on whether engine-internal reads change

**No handbook statement in `mods/ssbu_mod_new/handbook/` addresses this.** The
three pages the prompt names were read in full:

- `handbook/09_params_prc.md` - about `.prc` files, extraction, labels, and
  `vl.prc` lookups. Nothing about a `get_param_float` hook, slot offsets, or
  whether a hook changes an engine-internal read. The nearest line is about a
  *different* mechanism: *"`G&W`'s `param_breath` ... is read by the breath
  constructor from the **owner's decoded param object**; an eflame owner lacks it
  - solved by the 0.14.0 parameter bridge (built, untested; `07`)"* - which is a
  statement about a named bridge, marked *built, untested*, i.e. **not tier A**.
- `handbook/11_smashline_skyline.md` - Skyline/smashline mechanics: patching
  `.text` via `Patch::in_text` (A), TCP log truncation (A), mutex reentrancy (A),
  Main double-fire (A), costume gating (A gate, C mechanism). Nothing about param
  hooks or engine-internal reads.
- `handbook/graveyard.md` - no entry for `get_param`, param hooks, or internal
  reads (searched).

`projects/pgwr/STATUS.md` lists the param bridge as **"In-game physics/params
improved ... unverified"**-class work throughout; nothing records an observation
that an engine-internal read changed. **There is no tier-A, B, C or D statement
to quote, and none is paraphrased as observed.**

## 2. Part 2 - the vtable slot

### 2.1 (a) Run scan (B)

`RELATIVE` records parsed from the bare 24-byte array at file `0x39c8070..0x40c9fc7`:
**306167 records parsed of 306169 slots** in the array. The two skipped are not
`R_AARCH64_RELATIVE`. The record layout was re-validated here against the vtable
`0x50a6d28` that P1-ID-REVIEW already decoded: `+0` → `0x19c2210`, `+8` →
`0x19dc640`, `+0x10` → `0x19dc650`, all three matching that report.

Grouping slots that are consecutive at stride 8 and all relocate into the code
range `0x100..0x39C8000`, keeping runs of at least `0x288` bytes: **928 runs.**
Full table with `+0x248/+0x250/+0x268/+0x270/+0x278/+0x280`:
`evidence/P2-STAT-HOOKPOINT/step2a_runs.txt`.

**Completeness check.** A vtable whose pointers were written directly into the
file rather than relocated would be invisible to this scan. Scanning every 8-byte
qword past `.text` for the same shape finds **2** such runs, `0x4861ae8` and
`0x529df00`; both are dense pools whose `+0x270` slot is a duplicate of its
neighbours and neither answers the thunk set. **No file-resident vtable was
missed.** Evidence: `step2e_completeness.txt`, and the check script asserts both
addresses.

### 2.2 (b) Reduction, and the filter that failed

Four filters, each measured. Two of them did not work and are reported as such.

| filter | survivors | what it measured |
|---|---|---|
| F0 contiguous code run ≥ `0x288` | 928 | §2.1 |
| F1 code pointer at all 48 thunk slots | **928** | **vacuous - rejected** |
| F2 `+0x248/+0x258/+0x268/+0x278` four distinct, `+0x280` present | 926 | |
| F3 `+0x270` forwards to `+0x268` (direct `b`/`bl`, or vtable load + `blr`) | **0** | strict direction |
| F3' either direction, wider window | 8 | self-referential - rejected |
| F4 both slots are real bodies (`ret`-terminated, ≥ 8 instructions) | 212 vtables → **13 distinct slot pairs** | |
| **F5** `+0x268` or `+0x270` is a ≤4-insn `br`/`blr` forwarder | **11 runs / 9 tables** | **added after F4 was found to hide evidence, §2.6** |

**F1 was vacuous.** Every one of the 928 runs already carries a code pointer at
all 48 offsets the `lua_bind` block dispatches to. That set therefore
discriminates nothing on its own, and the report does not claim it as a filter.

**F3 found nothing in the strict direction**, i.e. **no candidate vtable's `+0x270`
entry forwards to its own `+0x268` entry** within 400 instructions. The looser
both-directions variant found 8, but inspection showed they were a function
branching through a vtable slot that held *itself*, which is recursion, not
forwarding. Both variants and the rejection are in
`step2b_reduce.txt`, `step2b_reduce_wide.txt`, `step2b_reduce_strict.txt`.

F4 is what carries the reduction: of 926 structurally eligible vtables, the
`+0x268`/`+0x270` bodies must be real code rather than 1-2 instruction stubs. The
stubs are extremely common - `+0x268` is a bare `ret` in 611 of 926 cases
(`0x33be610`, 525 tables; `0x68da70`, 76 tables) and `+0x270` is
`mov w0,#1; ret` in 561 cases (`0x33be620`, 504 tables). Those cannot be the
function an engine call site with a hash in `x1` reaches into.

That leaves **13 distinct `(+0x268, +0x270)` slot pairs**, one per table row below.
This is within the prompt's "more than 12" boundary, and the list is the result.

**F4 is itself defective, and the defect matters.** F4 requires both slots to be
`ret`-terminated bodies of ≥ 8 instructions. But the shape the task is actually
looking for - a slot that loads the vtable and branches through another slot - is
*by nature* a 3-instruction tail forwarder, so F4 removes exactly the evidence it
should preserve. §2.6 re-scans without that filter. The 13-row table below is
therefore a list of *substantive* candidates, not a complete list of vtables
whose `+0x268`/`+0x270` are related, and §2.6 supersedes it where they overlap.

### 2.3 The candidate table (B)

Every row re-derived from the relocation array by `evidence/P2-STAT-HOOKPOINT/check_hookpoint.py`.

| # | vtable | `+0x248` | `+0x250` | `+0x258` | `+0x260` | `+0x268` | **`+0x270`** | `+0x278` | `+0x280` | x1 read? |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `0x04f4a788` | `0xd4760` | `0xd47e0` | `0xd4720` | `0xd47a0` | `0xd4820` | **`0xd4860`** | `0xd48e0` | `0xd4960` | yes |
| 2 | `0x04f6d5b0` | `0x474120` | `0x474330` | `0x4743e0` | `0x474460` | `0x474560` | **`0x4747a0`** | `0x474b60` | `0x474c10` | **yes** |
| 3 | `0x04f6f448` | `0x490ae0` | `0x490af0` | `0x490b40` | `0x490b50` | `0x490b60` | **`0x490bd0`** | `0x490be0` | `0x490c50` | no |
| 4 | `0x04f6f900` | `0x49cf50` | `0x49d600` | `0x49d680` | `0x49d740` | `0x49d880` | **`0x49d9c0`** | `0x49d9f0` | `0x49da20` | no |
| 5 | `0x04f70d18` | `0x4af4f0` | `0x4af510` | `0x4af520` | `0x4af580` | `0x4af5e0` | **`0x4af630`** | `0x4af680` | `0x4af6b0` | no |
| 6 | `0x04f767b0` | `0x403a20` | `0x57ec80` | `0x4078b0` | `0x405e10` | `0x57ee90` | **`0x57efd0`** | `0x57f1c0` | `0x4078c0` | no |
| 7 | `0x04f7f210` | `0x66b580` | `0x66bf00` | `0x66a9a0` | `0x66af10` | `0x66b3f0` | **`0x66c470`** | `0x3a7d30` | `0x613210` | no |
| 8 | `0x04f85dd8` | `0x6c3db0` | `0x4034f0` | `0x4078b0` | `0x405e10` | `0x6c42e0` | **`0x406570`** | `0x6c47e0` | `0x6c4870` | no |
| 9 | `0x05061780` | `0x1367a10` | `0x1367b00` | `0x1367bf0` | `0x1367ce0` | `0x1367e10` | **`0x1367f00`** | `0x1367fc0` | `0x1368100` | no |
| 10 | `0x05076138` | `0x403a20` | `0x1611940` | `0x4078b0` | `0x405e10` | `0x405e20` | **`0x406570`** | `0x407040` | `0x4078c0` | no |
| 11 | `0x05203650` | `0x33be5e0` | `0x33be5f0` | `0x33be600` | `0x33be100` | `0x34b5da0` | **`0x34b5f20`** | `0x34b5f50` | `0x33be640` | **yes** |
| 12 | `0x05213aa8` | `0x403a20` | `0x4034f0` | `0x34e7c90` | `0x34e7ca0` | `0x34e7d40` | **`0x406570`** | `0x407040` | `0x4078c0` | no |
| 13 | `0x052a7be0` | `0x4162e0` | `0x416480` | `0x417460` | `0x4174d0` | `0x417580` | **`0x417610`** | `0x4177e0` | `0x417950` | no |

The "x1 read?" column is a further measurement: the call sites pass the hash in
`x1`, so a `+0x270` body that never touches `x1` cannot be the function that
answers such a call. Argument reads include a register used as a **memory base**
(`ldr x8,[x0,#0x198]` reads `x0`) - an earlier pass that looked only at register
operands reported false negatives here and was corrected before the table was
fixed.

Rows 2, 11 and 1 are the only ones whose `+0x270` reads `x1`. Row 13 and the 186
tables sharing the pair `(+0x268=0x25d6ff0, +0x270=0x25d7150)` are excluded from
F4 by the substantive-body rule, and `0x25d7150` never touches `x1` in its first
48 instructions - checked and asserted, so the exclusion does not hide a reader.

### 2.4 (b) Construction sites (B)

For the three `x1`-reading candidates, `adrp+add` references to the vtable
address were found from a full adrp index (489450 instructions, 4400 pages) and
the store that installs the vtable was read.

| vtable | reference | construction function | allocation | install site |
|---|---|---|---|---|
| `0x4f6d5b0` (row 2) | `adrp 0x33ba084` / `add 0x33ba088` → `0x4f6d5b0` | starts `0x33ba010` | `mov w0,#0x10` @`0x33ba024`, `mov w1,#0x70` @`0x33ba028`, `bl 0x392dce0` @`0x33ba02c` → **0x70 bytes, align 0x10** | `stp x8, x19, [x0]` @`0x33ba094` |
| `0x4f87118` (same pair as row 2) | `adrp 0x689f88` / `add 0x689f8c` → `0x4f87118` | starts `0x689f40` | `mov w0,#0x10` @`0x689f70`, `mov w1,#0x70` @`0x689f74`, `bl 0x392dce0` @`0x689f78` → **0x70 bytes, align 0x10** | `stp x8, x19, [x21]` @`0x689f94` |
| `0x5203650` (row 11) | `adrp 0x43fc80` / `add 0x43fc84` → `0x5203650` | tail of a function ending `ret` @`0x43fc90` | none in window | `str x9, [x8, #0x118]` @`0x43fc88` → writes to global `0x5331118` |

Raw windows: `evidence/P2-STAT-HOOKPOINT/ctor_0x4f6d5b0.txt`,
`ctor_0x4f87118.txt`, `ctor_0x5203650.txt`, and the earlier wider
`step2d_ctor_0x33ba088*.txt`.

**None of these three stores its object at offset `0x50` of another object.**
Searching their construction windows for a store at `#0x50` returns nothing. So
for the three `x1`-reading candidates the link the prompt asks for - *an object
pointer written to offset `0x50` of another object* - **was not found**, and per
the prompt's rule **none of these three is called `WorkModule` here.**

That statement applies to these three only. A wider re-scan, in the same pass that
produced §2.6, **did** find a vtable whose object is stored at a parent's `+0x50`:
vtable `0x4f89490`, stored by the large builder described in §2.6.3. §2.4's
"absent" is a statement about three candidates, not about the image.

Two observations recorded without interpretation:
- `0x4f6d5b0` and `0x4f87118` carry the **same** `(+0x268, +0x270)` pair
  (`0x474560` / `0x4747a0`) and are built by two structurally identical
  functions that both allocate **0x70** bytes, align `0x10`, and end with the
  same `stp x8, x19, [obj]` head install followed by `strh`/`stp` field
  zeroing. One class in two builders, or two classes sharing a base - not
  decided here.
- `0x5203650` is installed into a **global** at `0x5331118`, not into a heap
  object. That is why its construction window shows no allocation.

**Correction 1, applied while writing this report.** The `adrp` index for
`0x4f6d5b0` returns page `0x4f6d000`; the page-based lookup surfaced three
`adrp+add` builders in the page range `0x33b9f70..0x33ba0d0`, and an earlier
draft of this table attributed the 0x390-byte allocation at `0x33b9f84..0x33b9f8c`
to the `0x4f6d5b0` constructor. Re-reading the window shows that is wrong: the
function starting `0x33b9f70` (alloc **0x390**, `ret` @`0x33ba008`) builds
`adrp 0x51ac000` / `add #0x988` → **`0x51ac988`** and installs that at
`str x8, [x20]` @`0x33b9ff4`. `0x4f6d5b0` is installed by the *next* function,
`0x33ba010..0x33ba0c8`, which allocates **0x70** bytes. Both were picked up only
because they share the 4 KiB page containing the `adrp`. The check script asserts
both vtable values so the two cannot be conflated again.

**Correction 2, applied while writing this report.** The `0x4f87118` row's
"construction function starts `0x689f40`" is also wrong, and in a way that
invalidated the original `+0x50` search. `0x689f40` is not a function start at
all; it is a point inside one large builder that runs `0x6882d0` (a real
`sub sp, sp, #0x90` prologue, `mov x19, x0` saving the parent) to `ret` @`0x68b464`
- roughly 12 KB. That function allocates about fifteen sub-objects and installs a
different vtable into each. Searching only the 48-instruction window around
`0x689f94` found no `+0x50` store because the store is ~4 KB earlier, at
`0x688584`. Both corrections are asserted in the check script.

### 2.5 The three `+0x270` functions that read x1

Only three claims per function, as the prompt asks: argument registers read,
direct `bl` targets, and whether `x1`/`x2` are compared against or passed on
unchanged. 48-instruction windows are in `evidence/P2-STAT-HOOKPOINT/`.

**Row 2, `0x4747a0`** (240-instruction body; `evidence/.../slot270_0x4747a0.txt`)

| property | measured |
|---|---|
| arguments read | `x0` @`0x4747c8` (into `x19`); `x1` @`0x4747c4` as **`and w22, w1, #0xff`**; `x2` @`0x474890`, `0x4748a8`, `0x47490c` |
| direct `bl` targets | `0x15b0590` (×2), `0x39c0220`, `0x39c0230` |
| `blr` sites | 13 (`0x4747fc`, `0x474818`, `0x474834`, `0x474850`, `0x47486c`, `0x4748bc`, `0x474914`, `0x474928`, `0x47495c`, `0x474a0c`, `0x474a30`, `0x474ab0`, `0x474b08`) |
| `x1` compared against a constant | **no** `cmp`/`subs` of `x1` against an immediate anywhere in the body |
| `x1` passed on | **yes** - no write to `x1` before the `bl`s, so it arrives in those calls unchanged; `x1` is finally read at `0x474a48` and `0x474b14` |
| `x2` | read at three sites, not compared against an immediate |

`x1` is masked to 8 bits before use, so a 40-bit hash cannot survive as one
value. That is recorded, not interpreted.

**Row 11, `0x34b5f20`** (11-instruction body; `evidence/.../slot270_0x34b5f20.txt`)

| property | measured |
|---|---|
| arguments read | `x0` @`0x34b5f2c`, `0x34b5f30`, `0x34b5f5c`, `0x34b5f60`, `0x34b5fa0`; **`x1` @`0x34b5f28`** as `ldr x8,[x1,#0x20]` - a memory base, so `x1` is dereferenced as a **pointer**, not as a hash |
| `x2` | not read |
| direct `bl` targets | none |
| `blr` | `0x34b5f38` (`blr x8`), target loaded by `ldr x8,[x8,#0x110]` @`0x34b5f34` |
| `x1` compared against a constant | no |
| body | `cmp w0,#0x15` @`0x34b5f3c`, `cset w0,eq` @`0x34b5f40`, `ret` @`0x34b5f48`, `udf` padding @`0x34b5f4c` |

**Row 1, `0xd4860`** (15-instruction body; `evidence/.../slot270_0xd4860.txt`)

| property | measured |
|---|---|
| arguments read | `x0` @9 sites. **`x1` is written, not read**: `mov x1, x0` @`0xd4870` |
| direct `bl` targets | `0xb1b90` @`0xd486c`, `0x130810` @`0xd4878`, `0x10ead0` @`0xd4888` |
| `x2` | not read |
| `x1` compared against a constant | no - and it cannot be an input at all, since the first thing the body does after `bl 0xb1b90` is overwrite it |

**Consequence for the candidate set.** Of the three `x1`-reading `+0x270`
bodies, **none consumes `x1` as a 40-bit hash**: row 2 truncates it to 8 bits,
row 11 dereferences it as a pointer, row 1 overwrites it. So the filter
"reads `x1`" is **necessary but not sufficient**, and no candidate here has been
shown to be the function a `weight`-hash call site reaches. **Row 2 is the only
one whose body is large enough to contain a hash-map lookup, and that is a
statement about length, not about what it looks up.** Stated as D, not adopted.

### 2.6 Forwarder-shaped slots (B) - found after F4 was found to hide them

F4's "both slots are `ret`-terminated bodies of ≥ 8 instructions" rule discards
every slot of the form

```
ldr x8, [x0] ; ldr x3, [x8, #0xNNN] ; br x3
```

which is the shape the task is looking for. Re-scanning all 928 runs for slots
whose body is ≤ 4 instructions ending in `br`/`blr`
(`scratch/.../forwarders.py`, output `evidence/.../step2f_forwarders.txt`):

**2.1 `+0x268` is a forwarder - 2 runs.** Both point at the same code:

| vtable | `+0x248` | `+0x250` | `+0x258` | `+0x260` | `+0x268` | `+0x270` | `+0x278` |
|---|---|---|---|---|---|---|---|
| `0x04f73738` | `0x4e5390` | `0x4e53a0` | `0x4e53b0` | `0x4e53c0` | `0x4e53d0` | `0x4e53e0` | `0x4e53f0` |
| `0x04f89490` | `0x4e5390` | `0x4e53a0` | `0x4e53b0` | `0x4e53c0` | `0x4e53d0` | `0x4e53e0` | `0x4e53f0` |

The two vtables share their entire `+0x248..+0x278` block and differ only at
`+0x280` (`0x3b1760` vs `0x6f1ef0`). Bodies:

```
0x4e53d0  ldr x8, [x0]
0x4e53d4  ldr x3, [x8, #0x270]     <-- +0x268 dispatches slot +0x270
0x4e53d8  br  x3
0x4e53dc  udf #0

0x4e53e0  ldr x0, [x0, #0x38]      <-- +0x270 rebases onto another object
0x4e53e4  ldr x8, [x0]
0x4e53e8  ldr x3, [x8, #0x30]      <-- then dispatches ITS slot +0x30
0x4e53ec  br  x3
```

This is the **`+0x268` → `+0x270`** direction, which is the reverse of what F3
tested; F3's "0 survivors" is therefore a statement about one direction only and
does not mean no vtable relates the two slots.

Note what the chain does **not** do: neither body reads `x1` or `x2`. Both just
re-thread `x0`. So this pair cannot itself consume a hash argument, and
`0x4e53d0` is a forwarding shim, not the parameter reader.

**2.2 `+0x270` is a forwarder - 9 runs**, in two groups:

| vtable(s) | `+0x270` | body shape | other slot |
|---|---|---|---|
| `0x04f73738`, `0x04f89490` | `0x4e53e0` | `[x0+0x38]` then slot `+0x30` | `0x4e53d0` |
| `0x051b08c8`, `0x051c3868`, `0x051e4fd0` | `0x33c8690`, `0x33f6b90`, `0x3444140` | slot `+0x1c0` | `0x33be610` |
| `0x051b7f98`, `0x051d1460`, `0x051e0580`, `0x051f3ba8` | `0x33dc980`, `0x34131b0`, `0x3433f90`, `0x346c8b0` | slot `+0x1d0` | `0x33be610` |

The seven tables in the last two rows share `+0x268 = 0x33be610`, which is the
bare-`ret` stub that F4 used to exclude them. They are a delegating class whose
`+0x270` re-dispatches at `+0x1c0` or `+0x1d0` - not the slot pair the task wants,
but they are the only other place in the image where `+0x270` is a pure forwarder.

**2.3 The `+0x50` link, found (B).** Vtable `0x4f89490` is the one table whose
object is demonstrably stored at offset `+0x50` of a parent object. In the large
builder `0x6882d0`..`ret` @`0x68b464`:

```
0x688508  mov  w1, #0x98
0x68850c  mov  w0, #0x10
0x688510  bl   #0x392dce0            ; allocate 0x98 bytes, align 0x10
0x688514  mov  x20, x0
0x688520  adrp x8, #0x4f89000
0x688524  add  x8, x8, #0x490        ; = 0x4f89490
0x68852c  stp  x8, x19, [x20]        ; install vtable + parent back-pointer
...
0x688538  mov  w8, #0xf1c0
0x68855c  str  x20, [x19, x8]        ; file it at parent+0xf1c0
0x688560  cbnz x20, #0x68857c
   ... (on the null path x20 is replaced by a global sentinel)
0x688584  str  x20, [x19, #0x50]     ; and at parent+0x50
```

`x20` is not written between `0x68852c` and `0x688584` on the non-null path
(asserted), so both stores receive the same object: the `0x4f89490` instance is
reachable at both `parent+0x50` and `parent+0xf1c0`.

This is the closest structural match to the prompt's hypothesis found anywhere:
an object at `[parent+0x50]` whose vtable's `+0x268` dispatches `+0x270`.
**It is still not a claim that this is `WorkModule`.** The `+0x270` body rebases
through `[x0+0x38]` and dispatches slot `+0x30` of a *different* object, reads no
argument registers, and the identity of the parent at `x19` is unknown. What it
establishes is that the `+0x50` architecture the prompt describes **does exist in
this image**, at exactly two vtables.

## 3. Limits

1. **No tier A. No runtime.** Nothing here shows what any of these functions
   does when called, how often, or whether a hook on `0x208de50` changes what a
   `+0x270` call site returns.
2. **The central question is not answered.** Two different offsets (`+0x268` for
   the exported wrapper, `+0x270` for the engine sites) is a measurement. The
   consequence for the old mod's hook is **unverified**. No candidate is
   established as the slot-`+0x270` target.
3. **No construction site ties any candidate to an object stored at
   `[accessor+0x50]`.** Per the prompt's rule, no candidate is named
   `WorkModule`.
4. **F1 was vacuous and two F3 variants were rejected as unsound.** The
   surviving reduction rests on F4 (substantive bodies), which is a
   length/shape test. It cannot tell a real implementation from a long stub that
   ignores both arguments.
5. **The `lua2cpp` table at `0x41b7758` is inferred from shape (D).** It was not
   decoded, and what reads it was not traced.
6. **The `smash-rs` doc comment is self-contradictory** - it says
   `get_param_float_impl` "is not exported by the main executable" while
   `_ZN3app8lua_bind32WorkModule__get_param_float_impl...` **is** in the dynamic
   symbol table at `0x208de50`. Reported, not resolved. Note also that
   `smash-rs` is **not** the crate the plugin uses (it uses `skyline-smash`),
   so its `+0x268`/`+0x270` declaration is a C-tier cross-check on the image,
   not the hook's actual binding.
7. **Function boundaries are linear-scan estimates.** Bodies are cut at the first
   `ret` (`0xD65F03C0`, compared in full - masking with `0xFFFFFC1F` collides with
   `br x16` and made an earlier pass report every body as 400 instructions) or at
   `udf` padding. A body with an early-exit path may be reported short.
8. **Two script defects were found and fixed during this task**, both by tests
   rather than inspection: the `ret` mask collision above, and an argument-read
   detector that ignored memory bases. Both had produced plausible-looking wrong
   output. The check script asserts the corrected behaviour so they cannot recur
   silently.
9. **Nothing was extracted, downloaded, installed or built.** No Rust was
   compiled, no framework or shared contract touched, `STATUS.md`,
   `CHANGELOG.md` and `CURRENT_INSTALL.md` not edited.
10. **The Part 2 reduction is not a proof of absence.** F4 (both slots
   `ret`-terminated, ≥ 8 instructions) discards forwarder-shaped slots, which are
   the shape the prompt describes. §2.6 re-scans without it and finds the
   `+0x268` → `+0x270` pair at two vtables, one of whose objects is stored at a
   parent's `+0x50`. The 13-row table is a list of *substantive* candidates and
   must not be read as "these are all the vtables where the two slots are
   related". F3's 0 survivors likewise covers one direction only.
11. **`0x4f89490` is not shown to be `WorkModule`.** What is measured (B): it is
   stored at `parent+0x50`, and its `+0x268` dispatches `+0x270`. What is not
   known: the identity of the parent at `x19`, the identity of the object reached
   through `[x0+0x38]`, and whether anything passes an argument through this
   chain - neither body reads `x1` or `x2`.

## 4. Commands

```
sha256sum gamedata/ssbu-13.0.4/main.bin
# -> f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613   MATCH

PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python \
  mods/mii_customizer/evidence/P2-STAT-HOOKPOINT/check_hookpoint.py
# -> 366 passed, 0 failed ; exit 0
```

Scratch scripts, all under `scratch/2026-10-04_P2-STAT-HOOKPOINT/`:
`dyn.py` (dynamic tags), `dynsym.py` (symbol lookup), `vtables.py` (F0),
`reduce.py` / `reduce2.py` / `reduce3.py` (F1-F3), `sizes.py` (F4),
`pairs.py` (collapse + refs), `argread.py` / `final.py` (argument reads),
`complete.py` (file-resident completeness), `thunks.py`, `adrpidx.py`, `dumps.py`,
`forwarders.py` (F5, §2.6), plus unmodified copies of `relocs.py` and `d.py` from
`scratch/2026-10-04_P2-SKILL-NATIVE/`.

## 5. Next experiment

**One thing, and it is not offline.** The next question cannot be settled by more
disassembly, because it is about what a hook *does*:

> Build one log-only plugin that counts calls to the exported wrapper at
> `0x208de50` and calls reaching `+0x270`, and run it with two fighters in one
> match. If the `+0x270` count is non-zero while the `0x208de50` count is zero,
> the old mod's hook provably does not see engine-internal reads and the
> per-instance substitution it performs is script-only. If both counters move
> together, the hook does reach them and P2-STAT-API's path A is live.

This is exactly the P2-PLUGIN-SCAFFOLD crate the coordinator has already scoped,
plus one hook on each of the two entry points. It needs the first console gate
and a user-approved test; **no emulator run is proposed and none was performed.**

Two smaller offline items, if they are wanted before then:

1. **Decode the table at `0x41b7750`** far enough to identify what reads it. That
   would turn §1.5's D into a B and settle whether `0x208de50` is reachable only
   through the script marshalling layer. Bounded: one table, one xref sweep.
2. **Compare `+0x268` and `+0x270` on row 2's vtable for a hash-map lookup.** The
   `+0x268` body (`0x474560`, 141 instructions) was not read for a Hash40 constant
   because the task's reduction did not require it. A single 40-bit constant
   search over one function would say whether the pair does param lookup at all.

## 6. Summary

Task `P2-STAT-HOOKPOINT` - **PARTIAL**.

**Changed files**, all inside the exclusive write paths, nothing else touched:

* `research/P2-STAT-HOOKPOINT.md` (this report, new)
* `evidence/P2-STAT-HOOKPOINT/check_hookpoint.py` (new)
* `evidence/P2-STAT-HOOKPOINT/check_output.txt` (new)
* `evidence/P2-STAT-HOOKPOINT/` 39 raw window/table files (new)
* `scratch/2026-10-04_P2-STAT-HOOKPOINT/` 17 scripts incl. copies of `relocs.py`
  and `d.py` (new)

No extraction, no dependency installed, no Rust built, no framework or shared
contract touched, no UI/layout/catalogue analysis, no install package. Inputs
read-only. `STATUS.md`, `CHANGELOG.md`, `CURRENT_INSTALL.md`, the coordinator
review and other workers' reports were not edited.

**Observed checks:** `check_hookpoint.py` **366 passed, 0 failed, exit 0**.
Negative controls: perturbing one reported `+0x270` value (`0x4f6d5b0 +0x270` set
to its own `+0x268` value), and separately the §2.6 vtable constant
(`0x4f89490` → `0x4f89491`), each make the script report `1 failed` and exit 1 -
the checks do fail on a wrong address. Input sha256 re-verified inside the script
on every run.

**Verified (B):** the hook resolves to the exported symbol at `0x208de50`; that
symbol is a 4-instruction wrapper loading `[x0+0x50]` and branching through slot
`+0x268`; the engine call sites use slot `+0x270` with the hash in `x1`; 306167
relocations parse from the documented array; 928 candidate runs; 13 distinct
substantive slot pairs remain; three of their `+0x270` bodies read `x1`, and none
consumes it as a 40-bit hash; no file-resident vtable was missed; **vtables
`0x4f73738` and `0x4f89490` have a `+0x268` that dispatches `+0x270`, and the
`0x4f89490` object is stored at a parent's `+0x50`** (§2.6); none of the three
`x1`-reading candidates stores its object at `+0x50`.

**Verified (C):** `skyline-smash` `315e4e8` resolves the hook path to the
`lua_bind` symbol with that mangled name; `smash-rs` `ddacc5e` declares
`+0x268` as an `_impl` entry and `+0x270` as the public one.

**Unverified (D):** that the table at `0x41b7758` is the `lua2cpp` export table;
that row 2's `+0x270` is a param lookup; that replacing `0x208de50` does or does
not change what the `+0x270` sites return.

**Blocker:** the runtime relationship between the exported wrapper and the
slot-`+0x270` dispatch. Offline evidence narrows it to two addresses and a slot
difference and cannot go further.

**Correction record.** Two errors in an earlier draft of this report were found
on a verification pass and are fixed in place: (1) the 0x390-byte allocation at
`0x33b9f84` belongs to a builder that installs `0x51ac988`, not `0x4f6d5b0`;
(2) the `0x4f87118` "construction function" is not a function at `0x689f40` but a
point inside a ~12 KB builder at `0x6882d0`, which invalidated the original
`+0x50` search and hid §2.6's finding. Both are now asserted by the check script.
Separately, filter F4 was found to discard the forwarder-shaped slots the task
asks about, and §2.6 was added because of it. Recorded here because all four were
found by re-reading code that had already produced plausible output, not by any
test failing first.