# P3-CUSTOMIZE-SITES - code sites that reach vtable slot +0x278, and where their two integer arguments come from

Task: `prompts/P3-CUSTOMIZE-SITES.md`. Date: 2026-10-04. Status: **DONE** (locating only).

Locating task. It answers one question: which code sites make the `+0x278` dispatch
call, and for each, where its two integer arguments come from. It interprets nothing.
No function or structure is named; no behaviour at run time is claimed. Offsets and
displacements are listed and the reader compares them.

Tiers: **B** = read from the image offline in this task. **C** = pinned prior report.
**D** = hypothesis, flagged. **B** here is offline static observation only; an emulator
run was not made and none was requested.

## Input

Workspace-relative `gamedata/ssbu-13.0.4/main.bin`, **rehashed at the start of this
task**: sha256 `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`,
86672752 bytes. Matches the value in the prompt, so the task is not BLOCKED. Flat
`MOD0` image, address == file offset. TEXT searched: `0x100 .. 0x39c8000`
(0x39c7f00 words). Check script re-verifies the hash itself.

Disassembler: capstone **5.0.1280** (the library in
`mods/ssbu_mod_new/builds/.cache/dk_cargo/python`; P1-ID-REVIEW recorded 5.0.9 and
P2-UI-CONSTS recorded 5.0.7 - the version string this build reports is recorded rather
than glossed). Python 3.12.3, `python`, not `python3`.

Copied unmodified into `scratch/2026-10-04_P3-CUSTOMIZE-SITES/`, originals not edited
(sha256 of both copies identical to the originals):

| file | sha256 |
|---|---|
| `d.py` | `ea3a8a67077f2f6a6f2ff1c78dd51b3c1af55b125139497d90d5d7cc3cdf3544` |
| `relocs.py` | `3079952b3d9ed63b8ba563a2bcc92a5ff6f3c493ca2cdfa70f7ac2edd0bff35f` |

New in this task's scratch folder: `lib.py` (shared decode helpers and the
P2-UI-CONSTS downward-`sp` prologue test), `step2_direct.py`, `step3_scan.py`,
`step35_examples.py`, `step45_sites.py`, `check_report_claims.py`.

## 1. The two blocks, read again (B)

The prompt's background is verified here, not assumed.

`0x208de60` - `evidence/P3-CUSTOMIZE-SITES/01_wrapper_0x208de60.txt`:

| address | instruction |
|---|---|
| `0x0208de60` | `ldr x0, [x0, #0x50]` |
| `0x0208de64` | `ldr x8, [x0]` |
| `0x0208de68` | `ldr x3, [x8, #0x278]` |
| `0x0208de6c` | `br x3` |

`0x4e53f0` - `evidence/P3-CUSTOMIZE-SITES/02_thunk_0x4e53f0.txt`:

| address | instruction |
|---|---|
| `0x004e53f0` | `ldr x0, [x0, #0x38]` |
| `0x004e53f4` | `ldr x8, [x0]` |
| `0x004e53f8` | `ldr x3, [x8, #0x38]` |
| `0x004e53fc` | `br x3` |

Both blocks are four instructions, not eight; instructions 5-8 of each dump continue
into unrelated code and are in the evidence files for completeness. The block at
`0x208de60` is preceded at `0x208de50` and `0x208de40` by two more blocks of the same
four-instruction shape (`+0x268` then `+0x258`), and `0x208de38` by a `+0x248` block,
all in `0x208de38..0x208de6c`. That is a displacement listing, not a claim that these
are one function.

Slot contents of the vtable at `0x4f89490`, via `R_AARCH64_RELATIVE` addends
(`03_vtable_slots.txt`):

| slot | address | addend |
|---|---|---|
| `+0x270` | `0x04f89700` | `0x004e53e0` |
| `+0x278` | `0x04f89708` | `0x004e53f0` |

Matches the background (C, P2-STAT-HOOKPOINT §2.6 and the coordinator review).

## 2. Direct users of the wrapper at `0x208de60` (B)

`step2_direct.py`, output in `04_step2_direct_users.txt`:

| search | count | detail |
|---|---|---|
| `bl`/`b` in `0x100..0x39c8000` whose target is `0x208de60` | **0** | - |
| 8-byte little-endian occurrences of `0x208de60` anywhere in the image | **1** | file `0x041bb7c8` |
| `R_AARCH64_RELATIVE` addends equal to `0x208de60` | **0** | - |

So nothing in the image calls or jumps to `0x208de60` directly. The single 8-byte
occurrence was resolved rather than left as noise: it is the `st_value` field (byte
offset 8 of a 24-byte entry) of dynamic symbol **index 6162** in the `DT_SYMTAB` at
`0x4197610` (`nchain = 7124`, C from the coordinator review). Its `st_size` is `16`,
`st_shndx` is `2`, and its `st_name` resolves through `DT_STRTAB` `0x41c11f0` to the
mangled name

```
_ZN3app8lua_bind33WorkModule__set_customize_no_implEPNS_26BattleObjectModuleAccessorEii
```

`12_string_and_symtab.txt`. Two facts are worth separating here. That this string
exists in `DT_STRTAB` and that its `st_value` is `0x208de60` are **B** (bytes read
from the image). That the entry is reachable as a call target by anything at run time
is not established - nothing in the image branches there directly, so the entry is
reached by a mechanism this task did not locate. The trailing `Eii` in the mangled
name is the ABI type of the last two parameters, i.e. two `int`s (C-consistent with the
pinned binding quoted in the prompt); the demangled meaning is not used as evidence
below.

## 3. Indirect call sites through slot `+0x278` (B)

Shape searched, exactly as specified:

- **A** `ldr xN, [xM, #0x278]`
- **B** `blr xN` or `br xN` on the same register N, within 8 instructions after A
- **C** the **nearest preceding definition** of xM (within 6 instructions before A) is
  `ldr xM, [xK]` - displacement 0, the vtable word
- **D** (filter) the **nearest preceding definition** of xK (within 12 instructions
  before A) is `ldr xK, [xJ, #0x50]`

Only the unsigned-offset `ldr` form is accepted; pre/post-index and `ldur` are not,
because the task names `ldr`. "Nearest preceding definition" is a backward walk that
stops at the first instruction writing the register, so an intervening overwrite is a
rejection, not a pass.

**Scanner validation** (`05_step3_synthetic.txt`, four synthetic sequences built from
hand-computed encodings and then decoded by capstone, plus the known wrapper):

| case | expected | result |
|---|---|---|
| `ldr x0,[x3,#0x50]` / `ldr x8,[x0]` / `ldr x3,[x8,#0x278]` / `blr x3` | match, filter D true | PASS |
| same, but `mov x8,#1` between the vtable load and the slot load | no match | PASS |
| `ldr x3,[x8,#0x270]` instead of `#0x278` | no match | PASS |
| shape matches, `ldr x0,[x3]` (no `#0x50`) | match, filter D false | PASS |
| real block at `0x208de68` | found by the unfiltered shape, filter D true | PASS |

The scan was gated on these: it does not run if any of them fails.

**Counts** (`06_step3_sites.json`):

| quantity | value |
|---|---|
| 64-bit `ldr` words with displacement `0x278` in TEXT | **977** |
| sites matching the unfiltered shape (A+B+C) | **86** |
| sites kept after filter D (xK loaded with displacement `0x50`) | **2** |

Two kept sites is a small result, so the counts are reported with their inputs rather
than as a conclusion about the game. `86` is the number of places in TEXT that load a
word at displacement `0x278` from something that was itself a loaded pointer and then
branch through it; only two of those load the pointer that feeds the slot load with
displacement `0x50` in the preceding 12 instructions.

All 86 unfiltered sites are in `06_step3_sites.json` with their register numbers and
both defining addresses. Five examples as raw windows are in
`evidence/P3-CUSTOMIZE-SITES/13_unfiltered_examples.txt`, chosen by taking every 17th
unfiltered site in address order so the sample is spread rather than clustered.

## 4. The two kept sites (B)

Full windows: `evidence/P3-CUSTOMIZE-SITES/07_site_windows.txt`
(24 instructions before, 8 after the call, raw). Machine readable:
`08_step45_sites.json`.

### Site 1 - `ldr x3, [x8, #0x278]` at `0x0208de68`, call `br x3` at `0x0208de6c`

This is the block at `0x208de60` from §1; it is found by the scan as a site in its own
right, not added by hand.

| item | value |
|---|---|
| vtable load | `0x0208de64` `ldr x8, [x0]` (displacement 0, x0) |
| displacement-`0x50` load | `0x0208de60` `ldr x0, [x0, #0x50]` (base x0, i.e. the same register as the incoming x0) |
| call | `0x0208de6c` `br x3`, 1 instruction after the slot load |

**w1 provenance.** No instruction in the window `0x0208de0c..0x0208de8c` writes x1.
The value at the call is whatever entered this entry point with. *Provenance leaves the
window* in the sense that the register is never defined here at all.

**w2 provenance.** The nearest definition in the window is `0x0208de28`
`ldr x2, [x8, #0x220]`, but `br x3` at `0x0208de2c` lies between it and the call, so
that definition belongs to a separate four-instruction entry that does not reach this
call by any path visible in the window. **x2 is not written by any of the four
instructions at `0x208de60..0x208de6c`**; it is an incoming value. Reported as *block
boundary, provenance leaves the window*, not as "loaded from `+0x220`".

**Loops.** No backward branch whose loop body contains `0x0208de6c` was found within
400 instructions above and 200 below the call. No `cmp` bound is visible.

**Enclosing function candidate.** Nearest prologue at or above the call by the
P2-UI-CONSTS downward-`sp` test: `0x0208d940` `sub sp, sp, #0x30`. A `ret` at
`0x0208db4c` lies between that candidate and the call, so the candidate's own extent
ends before the site; the block at `0x208de60` has no prologue of its own. This is
reported as a mechanical result of the specified test, and the `ret` is recorded so the
reader can discount it.

**Direct callers of `0x0208d940`:** 2 - `0x02138794` and `0x021399a8`. These are
callers of the prologue candidate, i.e. of the function the test attributes, not of the
`+0x278` dispatch itself, which has zero direct callers (§2).

### Site 2 - `ldr x8, [x8, #0x278]` at `0x020922fc`, call `blr x8` at `0x02092308`

This is the only `blr`-style site found.

```
0x020922e4: ldr x21, [x8, #0x50]     <- displacement-0x50 load, 6 instructions before the slot load
0x020922f8: ldr x8, [x21]            <- vtable load, 1 instruction before the slot load
0x020922fc: ldr x8, [x8, #0x278]     <- slot load (A)
0x02092300: mov x0, x21
0x02092304: mov w1, w20
0x02092308: blr x8                  <- call (B)
```

| item | value |
|---|---|
| vtable load | `0x020922f8` `ldr x8, [x21]` (displacement 0, base x21) |
| displacement-`0x50` load | `0x020922e4` `ldr x21, [x8, #0x50]` (base x8) |
| call | `0x02092308` `blr x8`, 3 instructions after the slot load |

**w1 provenance.** `0x02092304` `mov w1, w20`. x20 is not written anywhere in the
24-instruction window `0x020922a8..0x02092328`, so inside the window the answer is
*provenance leaves the window*. One step further out, still by reading instructions
only: in the prologue candidate's range, `0x0209221c` is `mov x20, x0`, and `x0` is not
written between `0x020921d0` and the `bl` at `0x02092218`, so x0 is that entry point's
first argument register; `0x02092218` is `bl 0x38f4000` and `mov x20, x0` takes its
32-bit return value. So the chain inside the image is
`w1 <- w20 <- w0 (return of bl 0x38f4000 at 0x02092218) <- argument 0 of the entry at
0x020921d0`. Reported as a chain of instruction addresses; what that value means is
not determined here. (`10_fn_0x20921d0_head.txt`.)

**w2 provenance.** `0x020922d0` `mov w2, wzr` - **immediate 0**. The path is not
blocked: `b 0x020922f4` at `0x020922d4` has its target inside the span between the
definition and the call, so the value 0 does reach the call on that path.

**Loops.** The window contains a backward branch `b.lo 0x020922b8` at `0x020922cc`, but
its body `0x020922b8..0x020922cc` **ends before** the call at `0x02092308`, so the call
is not inside it. Searching `call-400 .. call+200` instructions for a backward `b`/`bl`
whose body `[target, branch]` contains the call returns **none**. That loop's body
contains no `cmp <reg>, #imm` at all, so no bound is visible. No loop counting 0..3 or
0..4 is visible around this site, and no `cmp #2` or `cmp #3` bound on w1 or w2 is
visible anywhere in the window.

**Enclosing function candidate.** Nearest prologue at or above the call:
`0x020921d0` `str x23, [sp, #-0x40]!` (the 64-bit pre-indexed form the P2-UI-CONSTS
correction is about). No `ret` lies between it and the call.

**Direct callers of `0x020921d0`:** **0** direct `bl`/`b` in TEXT; also **0** 8-byte
pointers and **0** `R_AARCH64_RELATIVE` addends equal to it (checked with the same
method as §2, `09_xref_0x20921d0.txt` and the relocation walk). An `adrp`+`add` pair
materialises `0x20921d0` at `0x02092828`, so the address is built at run time rather
than branched to (`11_addr_materialisation_0x20921d0.txt`). That the entry is reached
this way is **D**; only the instructions are **B**.

### Why `0x020921d0` is worth the reader's attention (B bytes, D link)

At `0x0209281c..0x02092830` (`11_addr_materialisation_0x20921d0.txt`):

```
0x0209281c: adrp x1, #0x439d000
0x02092820: add  x1, x1, #0x46a      ; = 0x439d46a, bytes spell "set_customize_no"
0x02092824: adrp x2, #0x2092000
0x02092828: add  x2, x2, #0x1d0      ; = 0x20921d0
0x0209282c: add  x0, sp, #8
0x02092830: bl   0x3728640
```

Two separate **B** facts: the string `set_customize_no` occurs **exactly once** in the
whole image, at `0x439d46a`, NUL-terminated (`set_customize_no_impl` occurs zero
times); and `0x20921d0` is materialised into the adjacent argument register 8 bytes
later. The **D** inference - that this is a registration pairing the string with this
function address - is adjacency plus the observation that the surrounding code is the
same shape as other name/address pairs in this image (C: P2-UI-CONSTS §2 records
`adrp`+`add` name-and-value registration of nine editor globals). This is listed for
the coordinator to weigh; this task does not rely on it for any site.

## 5. Summary table (B, one row per kept site)

| site (`ldr` / call) | enclosing function candidate (downward-`sp` prologue) | w1 provenance | w2 provenance | loop / bound notes | direct callers of the candidate |
|---|---|---|---|---|---|
| `0x0208de68` / `br x3` `0x0208de6c`; base load `0x0208de60` `ldr x0,[x0,#0x50]` | `0x0208d940` `sub sp, sp, #0x30`; a `ret` at `0x0208db4c` ends that candidate's extent before the site | never written in the window - incoming argument register | nearest def `0x0208de28` `ldr x2,[x8,#0x220]` is behind a `br x3` at `0x0208de2c`; not written in the block - incoming | no loop body contains the call; no `cmp` bound visible | 2: `0x02138794`, `0x021399a8` |
| `0x020922fc` / `blr x8` `0x02092308`; base load `0x020922e4` `ldr x21,[x8,#0x50]` | `0x020921d0` `str x23, [sp, #-0x40]!`; no `ret` between candidate and call | `0x02092304` `mov w1, w20`; x20 undefined in the window -> leaves the window; outside: `0x0209221c` `mov x20,x0` after `bl 0x38f4000` at `0x02092218` | `0x020922d0` `mov w2, wzr` - **immediate 0**; path not blocked (`b 0x020922f4` at `0x020922d4`) | no loop body contains the call (the `b.lo` at `0x020922cc` ends before it); no `cmp #2`/`#3` bound visible | 0 direct `bl`/`b`; 0 pointers; 0 relocation addends; address materialised at `0x02092828` |

## Observed checks, failures and limits

Commands, all from the workspace root unless stated:

```
sha256sum gamedata/ssbu-13.0.4/main.bin
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
  python mods/mii_customizer/scratch/2026-10-04_P3-CUSTOMIZE-SITES/step2_direct.py
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
  python mods/mii_customizer/scratch/2026-10-04_P3-CUSTOMIZE-SITES/step3_scan.py
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
  python mods/mii_customizer/scratch/2026-10-04_P3-CUSTOMIZE-SITES/step45_sites.py
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python \
  python mods/mii_customizer/scratch/2026-10-04_P3-CUSTOMIZE-SITES/check_report_claims.py
```

- **Timing (measured, single run each, this machine).** `step2_direct.py` 4.4 s;
  `step3_scan.py` 3.1 s; `step45_sites.py` 2.7 s; `step35_examples.py` 0.2 s;
  `check_report_claims.py` **9.3 s**. The check re-runs the whole step-3 scan and the
  `bl`/`b` caller pass itself rather than trusting the stored JSON, and still finishes
  in seconds - the expensive-looking parts are `array('I')` word loops, not capstone.
  Nothing here takes minutes. Timings are wall clock via `time.time()` around a
  subprocess, not a per-phase breakdown.
- Input hash re-verified at task start and again by the check script; matches. Not
  BLOCKED.
- Scanner validated on four synthetic sequences and on the known block at
  `0x208de68` before the image scan ran; the scan is gated on those passing.
- `check_report_claims.py`: **55 checks, 0 failures, exit 0**
  (`15_check_output.txt`). It re-hashes the input, re-reads both four-instruction
  blocks, re-walks the relocation array for the two vtable slots, re-runs the branch /
  pointer / relocation searches, re-runs the four synthetic cases, re-runs the entire
  977-candidate scan, re-derives both sites' `w1`/`w2` provenance, loops, prologue
  candidate and caller counts from the image, and requires the report to mention every
  listed address and count.
- **Bookkeeping defect in the inherited `relocs.py --bounds`, recorded not hidden.**
  It reports "contiguous `R_AARCH64_RELATIVE` record array: file `0x39c8070 ..
  0x40c9fc7` (306169 records, 7348056 bytes)". The walk stops at the first position
  that is not a `0x403` record, but the printed byte/record counts are
  `(fwd + REC - back)`, which includes that one foreign slot. Counting only
  `r_info == 0x403` in that extent gives **306168** records, and the excluded trailing
  slot at `0x40c9fb0` has `r_info = 0x401`, `pad = 3`. The check script asserts both
  numbers so the discrepancy stays visible. This changes no site or count in this
  report; it matters only for anyone quoting a "records walked" total from
  `relocs.py`, including earlier notes in this project.
- Six intermediate failures in this task, all fixed at the cause and none suppressed
  (a seventh finding, the `relocs.py --bounds` arithmetic, is reported above rather
  than fixed, because `relocs.py` is an input this task was told not to edit):
  (a) `capstone.arm64` was not imported, so operand-type constants raised
  `AttributeError`; (b) capstone exposes the memory operand as `op.mem`, not `op.base`,
  which raised `AttributeError`; (c) a leftover no-op `if` was left in the matcher and
  removed; (d) the first provenance walk crossed four-instruction entry blocks and
  reported a `+0x220` load as w2's source for the site whose own four instructions
  never write x2 - fixed by adding the block-boundary rule, after which the answer is
  "incoming value"; (e) the first loop search only looked inside the 24-instruction
  window and reported "no loops" before any wider decode existed - fixed by scanning
  `call-400 .. call+200` and requiring the loop body to contain the call; (f) the check
  script itself failed twice on its first run - once because it read `op.base` where
  capstone gives `op.mem.base`, once because its expectation for `0x02092820` named the
  `adrp` address when the `add` is there, and once because its report-presence needles
  used the unpadded form while the report writes `0x0208de60`. All three were checker
  defects, not report defects; they were fixed in the checker and the run above is the
  one that passes.
- **`0x0208de60` has zero direct callers in the image.** Whatever reaches it is not a
  `bl`, a `b`, an 8-byte pointer or a relocation addend. That path was not located by
  this task and is not claimed.
- **`0x020921d0` has zero direct callers, pointers and relocation addends**; an
  `adrp`+`add` materialises the address at `0x02092828`. Reaching the entry at run time
  is **D**, not observed.
- **Prologue attribution is a candidate, not a fact.** The downward-`sp` test returns
  `0x0208d940` for the site at `0x0208de6c`, and a `ret` at `0x0208db4c` shows that
  candidate's extent ends before the site. Both facts are printed so the reader can
  discount the attribution.
- **Limits.** Static only: nothing was executed, no emulator, no console, no runtime
  behaviour claimed. The scan sees only the `ldr`-unsigned-offset form and only
  displacements written as `#0x278`; a slot reached via `ldur`, a pre-indexed `ldr`,
  a register-offset address, a computed index or a copied descriptor is out of scope by
  construction and is **not** claimed not to exist. Filter D looks back only 12
  instructions, so a longer distance would be missed. The `blr xN`/`br xN` search stops
  at the first register branch after the slot load, so a site that loads the slot, calls
  something else and branches to the slot later would be missed. The 86 unfiltered sites
  are a shape count, not a list of places the engine sets a special variant, and no
  claim is made that a shape match implies the object at `+0x50` is the same kind of
  object for every one of them.
- The block at `0x208de60` and the block at `0x4e53f0` are tail branches: neither reads
  an argument register, so `x1`/`x2`/`x3` pass through unchanged. That is stated as
  what the four instructions do; where they lead is out of this task's scope.

## Summary for the coordinator

**Task ID** P3-CUSTOMIZE-SITES. **Status DONE** (locating only).

**Changed files** (all under `mods/mii_customizer/`):

- `research/P3-CUSTOMIZE-SITES.md` (this report)
- `evidence/P3-CUSTOMIZE-SITES/01_wrapper_0x208de60.txt`
- `evidence/P3-CUSTOMIZE-SITES/02_thunk_0x4e53f0.txt`
- `evidence/P3-CUSTOMIZE-SITES/03_vtable_slots.txt`
- `evidence/P3-CUSTOMIZE-SITES/04_step2_direct_users.txt`
- `evidence/P3-CUSTOMIZE-SITES/05_step3_synthetic.txt`
- `evidence/P3-CUSTOMIZE-SITES/06_step3_sites.json` (all 86 unfiltered + 2 kept)
- `evidence/P3-CUSTOMIZE-SITES/07_site_windows.txt` (raw windows, provenance, loops)
- `evidence/P3-CUSTOMIZE-SITES/08_step45_sites.json`
- `evidence/P3-CUSTOMIZE-SITES/09_xref_0x20921d0.txt`
- `evidence/P3-CUSTOMIZE-SITES/10_fn_0x20921d0_head.txt`
- `evidence/P3-CUSTOMIZE-SITES/11_addr_materialisation_0x20921d0.txt`
- `evidence/P3-CUSTOMIZE-SITES/12_string_and_symtab.txt`
- `evidence/P3-CUSTOMIZE-SITES/13_unfiltered_examples.txt`
- `evidence/P3-CUSTOMIZE-SITES/14_examples_log.txt`
- `evidence/P3-CUSTOMIZE-SITES/15_check_output.txt`
- `scratch/2026-10-04_P3-CUSTOMIZE-SITES/{d.py,relocs.py,lib.py,step2_direct.py,step3_scan.py,step35_examples.py,step45_sites.py,check_report_claims.py}`

**Headline numbers (B).** 0 direct `bl`/`b` to `0x208de60`; 1 pointer to it, which is
the `st_value` of exported symbol
`_ZN3app8lua_bind33WorkModule__set_customize_no_implEPNS_26BattleObjectModuleAccessorEii`;
977 `ldr` words at displacement `0x278` in TEXT; 86 unfiltered shape matches; **2**
sites that also load the `+0x50` base within 12 instructions.

**Next experiment.** The interesting open question this task raises but does not
answer is the same one from the fighter side with the reverse direction: at
`0x020922e4` the base register x8 comes from `0x020922d8` `ldr x8, [x8]`, with
`0x020922e0` `mov x8, xzr` as the alternative, i.e. **the object whose `+0x50` is
loaded here is reached through a pointer chain, and the chain's origin is still
unknown offline**. The bounded follow-up is: dump the `adrp`+`add` materialisation of
that chain's head from `0x020921d0`'s range and follow it to its first parameter load,
which is the same shape of question as the untraced match-time reader but one function
below. Console-free. The `0x0208de60` entry has no direct caller at all; if the
coordinator needs that path, the next offline step is the `DT_SYM`/`DT_HASH` reach of
symbol index 6162, not a code scan.