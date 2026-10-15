# P2-UI-CONSTS - where the nine editor Lua globals are registered and what value each gets

Task: `prompts/P2-UI-CONSTS.md`. Date 2026-10-04. Status: **DONE** (locating only).

This is a locating task. It answers *where each name is registered* and *what value is
passed*. It deliberately does **not** interpret what the game does with any of it.
Nothing here is a runtime claim: no emulator, no console, nothing executed.

## Input

`gamedata/ssbu-13.0.4/main.bin` (workspace-relative), sha256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`, 86672752 bytes,
rehashed at the start of this task - **matches**, so the task is not BLOCKED
(`evidence/P2-UI-CONSTS/09_input_identity.txt`). Flat `MOD0` image, address == file
offset. TEXT used: `0x100..0x39c8000`.

Tiers: **B** = read from the image in this task (offline, static only). **C** = pinned
prior report (P2-SKILL-NATIVE). **D** = hypothesis, flagged. No runtime behaviour claimed.

## Result table

All nine names occur exactly once as NUL-terminated strings (counts in
`00_string_search.txt`), each with exactly one `adrp`+`add` reference site in TEXT, except
`IS_READ_ONLY`, which has **two** sites in two different functions. Both are listed.
No `R_AARCH64_RELATIVE` addend points at any of the nine strings, so there is no second,
table-mediated registration path (306167 records walked).

Every group-1 and group-2 call goes to the **same** registration function `0x33750a0`.

| name | string address | reference site (add) | enclosing function | registration function | value / value provenance | confidence note |
|---|---|---|---|---|---|---|
| `SPECIAL_SKILL_NUM` | `0x0424de53` | `0x019de49c` (adrp `0x019de498`) | `0x19ddb30` | `0x33750a0` | **3** - `mov w3, #3` at `0x019de4a8` | high. Immediate 4 bytes before the call. |
| `SKILL_COMMAND_NORMAL` | `0x04348c67` | `0x019de4c0` (adrp `0x019de4bc`) | `0x19ddb30` | `0x33750a0` | **0** - `mov w3, wzr` at `0x019de4cc` | high, but see the encoding note below. |
| `SKILL_COMMAND_SIDE` | `0x0424de65` | `0x019de4e4` (adrp `0x019de4e0`) | `0x19ddb30` | `0x33750a0` | **1** - `mov w3, #1` at `0x019de4f0` | high. Immediate 4 bytes before the call. |
| `SKILL_COMMAND_UPPER` | `0x043bd0b4` | `0x019de508` (adrp `0x019de504`) | `0x19ddb30` | `0x33750a0` | **2** - `mov w3, #2` at `0x019de514` | high. Immediate 4 bytes before the call. |
| `SKILL_COMMAND_LOWER` | `0x0432898f` | `0x019de52c` (adrp `0x019de528`) | `0x19ddb30` | `0x33750a0` | **3** - `mov w3, #3` at `0x019de538` | high. Immediate 4 bytes before the call. |
| `SKILL_COMMAND_NUM` | `0x04338b2f` | `0x019de550` (adrp `0x019de54c`) | `0x19ddb30` | `0x33750a0` | **4** - `mov w3, #4` at `0x019de55c` | high. Immediate 4 bytes before the call. |
| `INPUT_OK` | `0x04306e9b` | `0x019de570` (adrp `0x019de56c`) | `0x19ddb30` | `0x33750a0` | **6** - `mov w3, #6` at `0x019de57c` | high. Immediate 4 bytes before the call. This site is **branch-reached**: the `cbz x0, #0x19de56c` at `0x019de548` (the `SKILL_COMMAND_NUM` block) targets its own `adrp`, so this block has no `cbz` of its own and is skipped entirely when the earlier null test fails. |
| `IS_SKILL_EDITABLE` | `0x04431954` | `0x01809138` (adrp `0x01809134`) | `0x1808980` | `0x33750a0` | **not a constant** - `mov w3, w23` at `0x01809144`, where `w23` is built by `orr w23, w8, w9` at `0x0180912c` from two runtime loads (see step 4) | high for the provenance. Value is 0 or 1 at run time, never a build-time constant. |
| `IS_READ_ONLY` (site A) | `0x044119af` | `0x018090fc` (adrp `0x018090f8`) | `0x1808980` | `0x33750a0` | **not a constant** - `cset w3, ne` at `0x018090f4` from `cmp w8, #0` at `0x018090f0` over `ldrb w8, [x23]` at `0x018090ec` (see step 4) | high for the provenance. Value is 0 or 1 at run time. |
| `IS_READ_ONLY` (site B) | `0x044119af` | `0x01874eec` (adrp `0x01874ee8`) | `0x1874680` | `0x33750a0` | **not a constant** - `cset w3, eq` at `0x01874ee4` from `cmp w27, #1` at `0x01874ee0` over `ldr w27, [x19, #0xdc]` at `0x01874d50` (see step 4) | high for the provenance. Value is 0 or 1 at run time. Second registration of the same name in a different function. |

**`SKILL_COMMAND_NORMAL` encoding note (worth recording, it cost real time).** Its word at
`0x019de4cc` is `0x2a1f03e3`. Bits 28:23 are `010100`, i.e. the **ORN** immediate class, not
the ORR class (`100100`) the other six use. Decoding it with ORR semantics yields **2**, which
is wrong - that was a real intermediate error in this task, caught by the cross-checks below.
Three independent methods agree the value is **0**: capstone 5.0.7 prints `mov w3, wzr`;
LLVM 22.1.8 `llvm-objdump` prints `mov w3, wzr`; and `mov w3, wzr` assembles back to exactly
`0x2a1f03e3`. The check script pins the word and the text rather than trusting arithmetic.

## Step 1 - argument registers at the seven group-1 call sites

Window dumped: `0x019de480..0x019de584` (`evidence/P2-UI-CONSTS/02_group1_window.txt`).
The seven `bl 0x33750a0` calls are at `0x019de4ac`, `0x19de4d0`, `0x19de4f4`, `0x19de518`,
`0x19de53c`, `0x19de560`, `0x19de580`. Exactly 7 of the 700 image-wide call sites of
`0x33750a0` fall inside `0x19ddb30..0x19de6b0`.

Each site sets the same five arguments in the same shape:

| arg | defining instruction | provenance |
|---|---|---|
| `x0` | `ldr x0, [x8]` at `0x019de490` (28 bytes before the call; 24 for `INPUT_OK`) | **not a constant.** `x8` is itself `ldr x8, [x19, #0x40]` at `0x019de48c` - a pointer loaded from the owner object. Null-tested by `cbz x0, #0x19de56c` before the call. |
| `x1` | `adrp`+`add` pair, e.g. `adrp x1, #0x424d000` at `0x019de498` / `add x1, x1, #0xe53` at `0x019de49c` | **established**: the name string, an immediate/adrp target inside the dumped window. |
| `x2` | `adrp x2, #0x42b1000` at call-12 / `add x2, x2, #0xa84` at call-8 | **established**: `0x042b1a84`, identical at all seven sites. This address is inside the rodata blob and has **no** `R_AARCH64_RELATIVE` relocation; the file bytes there spell `i\0` following `mantle\0`. What it designates is not determined here (D). |
| `x3` | `mov w3, #N` at call-4 | **established**: the value in the table above. |
| `x4` | last definition anywhere in the enclosing function is `mov w4, #1` at `0x019ddd84` | **not a constant at the call.** 59 `bl`/`blr` instructions lie between `0x019ddd84` and `0x019de4ac`, and `x4` is caller-saved, so its value when the registration call is made is not established by anything in the enclosing function. Reported as *not a constant*; the literal 1 is **not** claimed. |
| `x5` | none | never written anywhere in `0x19ddb30..0x19de6b0`. Uninitialised at the call. |
| `d0`/`s0` | none | **no float setup.** There is not a single float instruction (`fmov`/`fcvt`/`fcsel`/...) in the whole of `0x19ddb30..0x19de6b0`. The three `fmov s0, #1.0` in the disassembly are at `0x19deac4`, `0x19dec88`, `0x19ded00`, all *after* the function's `ret` at `0x19de6b0`, i.e. in a different function. |

Argument order at the call is therefore `(x0=owner/Lua state pointer, x1=name string,
x2=0x42b1a84, x3=value)`. Nothing is passed in a float register.

## Step 2 - what `0x33750a0` reads before its first call

Raw 60-instruction window: `evidence/P2-UI-CONSTS/03_regfn_0x33750a0.txt`. Stated without
further analysis, as instructed. The first call is `bl 0x372cf50` at `0x3375118`.

Before it, the function reads **`x0`, `x1`, `x2` and `x3`**, and no `d`/`s` register:

- `x0` - `mov x20, x0` at `0x033750dc`, then dereferenced `ldr x0, [x0]` at `0x0337510c`.
- `x1` - `mov x19, x1` at `0x033750e8`; null-checked by `cbz x19, #0x337519c` at `0x03375124`.
- `x2` - `mov x8, x2` at `0x033750e4`, then `mov x1, x8` at `0x033750f0`.
- `x3` - `str x3, [sp, #0x88]` at `0x033750c8` (spilled to the outgoing argument area).
- `x4`..`x7` are only stored (`stp x4, x5, [sp, #0x90]`, `stp x6, x7, [sp, #0xa0]`).
- `d0`..`d7` are only stored (`stp q0, q1, [sp]` and the neighbouring `stp q2..q7`).

So the value argument arrives in a **general-purpose register as an integer**, not as a
float and not as a pointer - which is what distinguishes an integer value argument from
the other two possibilities the step asked about.

## Step 3 - group 2: reference sites and enclosing functions

| name | reference site | enclosing function | start evidence | extent |
|---|---|---|---|---|
| `IS_READ_ONLY` (A) | `0x018090fc` | `0x1808980` | `sub sp, sp, #0x190` at `0x01808980`, preceded by `udf #0` padding at `0x0180897c` | ends at the next prologue `stp x20, x19, [sp, #-0x20]!` at `0x01809e60` |
| `IS_SKILL_EDITABLE` | `0x01809138` | `0x1808980` (same function as the row above) | as above | as above |
| `IS_READ_ONLY` (B) | `0x01874eec` | `0x1874680` | `str d8, [sp, #-0x70]!` at `0x01874680`, preceded by `udf #0` at `0x0187467c` | epilogue `ldr d8, [sp], #0x70` at `0x018751e4`, `ret` at `0x018751e8` |

Both sites reach the **same registration function `0x33750a0`** as group 1, so there is no
second registration function to dump. Raw windows: `04_group2_windows.txt`,
`05_group2_prologues.txt`.

**Correction to the note on `0x1874570`.** The backward `fstart` scan returns `0x1874570`
for `0x01874eec`, but that is a **different, earlier function** that ends in `ret` at
`0x0187466c`. The real enclosing function of site B is `0x1874680`. The root cause is now
identified and is not merely "the scan ran too far": the first word of `0x1874680` is
`0xfc190fe8` = `str d8, [sp, #-0x70]!`, a 64-bit pre-indexed store that the inherited
`fstart.py` opcode masks (`0xD10003FF`, `0xA98003E0`) do not match. Verified by
assembler round-trip (`10_prologue_encodings.txt`): `str d8, [sp, #-0x70]!` assembles to
exactly `0xfc190fe8`. `check_claims.py` therefore identifies prologues by observable
downward-`sp` behaviour instead, and asserts that `0x1874680` is the **nearest** prologue
above the call, not merely an address smaller than it.

Argument registers at the group-2 calls:

- `x0` - `ldr x0, [x8]` (site A `0x018090dc`, site B `0x01874ed8`): **not a constant**, a
  pointer loaded from `[x22 + 0x40]` / `[x26 + 0x40]`, then `cbz`-tested.
- `x1` - the name string, established inside the window.
- `x2` - `0x043ccb7b` at **all three** group-2 sites (`adrp`+`add`, e.g. `0x01809100`/
  `0x01809104`). A *different* x2 from group 1's `0x042b1a84`. No relocation there either;
  the file bytes spell `b\0` following `VI_BUTTON_SELECTOR_NEXT\0`. What it designates is
  not determined here (D).
- `x3` - not a constant at any group-2 site; provenance in step 4.
- `x4`/`w4` - `mov w4, #1` at `0x01808c88` is the only write in the function before
  `0x01809148`, with **31** intervening `bl`/`blr`; **not a constant** at the call.
- `x5`/`w5` - never written in `0x1808980..0x01809148`.
- `d0`/`s0` - **differs between the two group-2 functions, and is reported rather than
  assumed absent.** Site A's function `0x1808980` contains **no** float instruction at all
  before `0x01809148`. Site B's function `0x1874680` *does* set up `s0`: `fmov s0, #1.0` at
  `0x01874ba4`, `fmov s8, wzr` at `0x01874d04`, `fcmp s8, #0.0` at `0x01874d18`, `fmov s0,
  #1.0` at `0x01874d1c` and `fcsel s0, s8, s0, hi` at `0x01874d20`. These sit on an earlier
  unrelated path and **are not the registered argument**: the value argument is `w3` from
  `cset` at `0x01874ee4`, and `0x33750a0` reads no float register before its first call
  (step 2), so a float left in `s0` cannot be what the third argument carries.

## Step 4 - load provenance for the two non-constant values

Stopped at the load, as instructed; the objects were not chased across functions.

**`IS_SKILL_EDITABLE`** (site A, `0x01809148`). `w3` comes from `w23` (`mov w3, w23` at
`0x01809144`), which is `orr w23, w8, w9` at `0x0180912c` over two independent loads:

- base register `x23`, defined at `0x018090e4`/`0x018090e8` inside the same window as
  `adrp x23, #0x5306000` + `add x23, x23, #0xb8c` = **`0x05306b8c`**.
  - `ldrb w8, [x23]` at `0x01809114` -> offset `+0`; `cmp w8, #0` `0x0180911c`;
    `cset w8, eq` `0x01809120`.
  - `ldrh w9, [x23, #0x10]` at `0x01809118` -> offset `+0x10`; `cmp w9, #0` `0x01809124`;
    `cset w9, ne` `0x01809128`.

So the registered value is `(byte[0x5306b8c] == 0) OR (halfword[0x5306b8c+0x10] != 0)`.
`0x05306b8c` is **past the end of the file image** (file ends at `0x52a8570`, so this
address is 386588 bytes beyond EOF) and has no relocation: it is a runtime zero-initialised
`.bss` slot. Its contents are therefore **not knowable from the image**, and the check
script asserts exactly that (`0x05306b8c > len(data)`).

**`IS_READ_ONLY` site A** (`0x01809108`). `cset w3, ne` at `0x018090f4` over `cmp w8, #0`
at `0x018090f0` over `ldrb w8, [x23]` at `0x018090ec` -> base `x23` = **`0x05306b8c`**,
offset `+0`, defined by the same `adrp`+`add` pair at `0x018090e4`/`0x018090e8`.
Value = `(byte[0x5306b8c] != 0)`. Same out-of-file `.bss` slot, so not knowable offline.

**`IS_READ_ONLY` site B** (`0x01874ef8`). `cset w3, eq` at `0x01874ee4` over `cmp w27, #1`
at `0x01874ee0`; `w27` from `ldr w27, [x19, #0xdc]` at `0x01874d50` -> base register
**`x19`**, offset **`+0xdc`**. `x19` is defined **inside the enclosing function `0x1874680`**
at `0x018746ac` as `mov x19, x0`, i.e. the incoming object pointer. Value =
`(*(u32 *)(x19 + 0xdc) == 1)`. Stopped there.

## Method and commands

```
sha256sum gamedata/ssbu-13.0.4/main.bin
export PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python
python mods/mii_customizer/scratch/2026-10-04_P2-UI-CONSTS/strfind9.py    # step 1/3 strings
python mods/mii_customizer/scratch/2026-10-04_P2-UI-CONSTS/refscan9.py    # step 3 refs
python mods/mii_customizer/scratch/2026-10-04_P2-UI-CONSTS/w.py A N       # raw windows
python mods/mii_customizer/scratch/2026-10-04_P2-UI-CONSTS/d.py calls 0x33750a0
python mods/mii_customizer/scratch/2026-10-04_P2-UI-CONSTS/d.py fstart ADDR
python mods/mii_customizer/scratch/2026-10-04_P2-UI-CONSTS/fstarts.py A B
python mods/mii_customizer/scratch/2026-10-04_P2-UI-CONSTS/addend.py 0x… # reloc addends
python mods/mii_customizer/scratch/2026-10-04_P2-UI-CONSTS/elfwrap.py A N out.elf
llvm-objdump -d --no-show-raw-insn out.elf                              # independent decode
clang --target=aarch64-none-elf -c -x assembler - -o a.o               # round-trip encode
python mods/mii_customizer/scratch/2026-10-04_P2-UI-CONSTS/check_claims.py
```

`check_claims.py` re-derives every address and value in this report **directly from the
image** - it never reads the window scripts or the saved evidence. It decodes raw words
itself (`struct` for data, capstone for text) and compares: **179 checks, 0 failures,
exit 0** (`evidence/P2-UI-CONSTS/06_claim_check.txt`).

**The check script was itself tested for false negatives.** A check that can only pass
proves nothing, so ten deliberate corruptions were each applied to a pristine copy and the
script re-run. All ten exited nonzero: wrong value (1->9); the `SKILL_COMMAND_NORMAL` 0->2
ORN trap; a string address off by one; site B's function start changed to the wrong
`0x1874570`; site A's start changed to `0x1809e60`; an altered expected hash; a dropped
`IS_READ_ONLY` reference site; a wrong registration function; a wrong first call target in
`0x33750a0`; and a false "no float instructions" claim.

One of those ten originally **passed when it should have failed**, which exposed a real
weakness: the function-start assertions were bare `start <= call` inequalities, so any
smaller address satisfied them. They now assert that the attributed start is the *nearest*
prologue above the call and that no prologue intervenes between start and call. That is a
strengthened check, not a relaxed one - it rejects strictly more wrong attributions than
before.

Scratch scripts `d.py`, `w.py`, `fstart.py`, `strfind.py`, `refscan.py`, `relocs.py` were
**copied unmodified** from `scratch/2026-10-04_P2-SKILL-NATIVE/`; the originals were not
edited. `strfind9.py`, `refscan9.py`, `fstarts.py`, `scanpro.py`, `addend.py`, `elfwrap.py`
and `check_claims.py` are new in this task's scratch folder.

### Two corrections to the inherited tooling

1. **`refscan.py` (prior task) loses targets that share a page.** It stored one target per
   page in a dict, so with `SPECIAL_SKILL_NUM` `0x0424de53` and `SKILL_COMMAND_SIDE`
   `0x0424de65` both on page `0x0424d000`, whichever was inserted last silently masked the
   other and `SPECIAL_SKILL_NUM` appeared to have **zero** references. `refscan9.py` maps
   each page to a *list* and prints the collision explicitly. This is a bug in the
   inherited script, not in the game data.
2. **`fstart.py` (prior task) names the wrong function for site B, and now we know why.**
   Its 4000-word backward scan returns `0x1874570`, a different function ending in `ret`
   at `0x0187466c`. The cause is a missing opcode form, not just scan range: the real start
   `0x1874680` begins with `0xfc190fe8` (`str d8, [sp, #-0x70]!`), a 64-bit pre-indexed
   store that neither of the script's masks matches. Confirmed by assembler round-trip
   (`10_prologue_encodings.txt`). `fstarts.py` enumerates prologues in a range, and
   `check_claims.py` classifies a prologue by observable downward-`sp` behaviour.

### Decoder cross-check (this is what caught the `0x2a1f03e3` error)

capstone here is **5.0.7** (P1-ID-REVIEW recorded 5.0.9; the difference is recorded, not
glossed). Because my own logical-immediate decoder disagreed with capstone on
`0x019de4cc`, every group-1 value word was confirmed three ways
(`07_llvm_crosscheck.txt`, `08_assembler_roundtrip.txt`):

1. capstone 5.0.7 decode,
2. LLVM **22.1.8** `llvm-objdump` decode of the same bytes,
3. re-encoding the disassembler's reading with `clang --target=aarch64-none-elf` and
   comparing words - **all seven round-trip exactly**.

## Observed checks, failures and limits

- Input hash re-verified at task start; matches. Not BLOCKED.
- All nine names: exactly one NUL-terminated occurrence each. Zero bare (unterminated)
  occurrences of any of the nine.
- Reference sites: exactly one per name except `IS_READ_ONLY`, which has two, in two
  different enclosing functions. Listed both times.
- **No relocation addend** points at any of the nine strings across 306167
  `R_AARCH64_RELATIVE` records, so no table-mediated second registration path.
- The three intermediate failures above were **fixed**, not suppressed: the wrong values
  came from a bad inherited script, a wrong function start, and my own misreading of an
  ORN word. Each is corrected at its cause and the corrections are recorded.
- A fourth defect was found by testing the checker itself: its function-start assertions
  were weak enough to accept the wrong enclosing function, which is the very mistake this
  report documents. Fixed by asserting nearest-prologue, not inequality.
- `d0`/`s0` at the group-2 calls is **not** uniformly absent: site B's function does set up
  `s0` before the call. It is reported explicitly rather than omitted; it is not the
  registered argument, and `0x33750a0` reads no float register before its first call.
- `x4` at every site is reported as **not a constant** rather than as `1`. At each site the
  literal `1` is written far earlier in the enclosing function with many caller-saved-clobbering
  calls in between (59 in `0x19ddb30`, 31 in `0x1808980`), so claiming `1` would be wrong.
- **Limits.** No runtime behaviour claimed; nothing executed. Values are what the code
  passes, not what Lua observes. `0x05306b8c` lies past EOF in `.bss`, so the two `IS_*`
  values cannot be resolved offline - only their provenance can. `0x042b1a84` and
  `0x043ccb7b` are recorded as the literal arguments passed in `x2`; what they designate is
  **not** established (D). Whether `0x19ddb30`, `0x1808980` and `0x1874680` are the only
  places these names are ever registered was checked only to the extent of the TEXT-wide
  `adrp`+`add`/`ldr`/`str` scan and the relocation-addend walk; a dynamically built name
  (string concatenation at run time) would not be found by either, and none is claimed.
- The enclosing-function spans for group 2 are pinned by prologue/epilogue evidence, but
  `0x1808980` is a large function (~5.2 KB) and only the windows quoted above were read.
  The prologue test recognises three shapes by behaviour; a compiler emitting a frame
  allocation in a form outside those three would make the nearest-prologue assertion fail
  loudly rather than silently mis-attribute, which is the intended failure direction.

## Smallest next question

`IS_SKILL_EDITABLE` and `IS_READ_ONLY` are now pinned to two runtime reads that live in
`.bss` at `0x05306b8c` (out of file) and in a scene object at `x19+0xdc`, and the group-1
values are constants in one function. The smallest open question that would change what a
mod can do: **what writes `0x05306b8c` and `x19+0xdc` before these registrations run?**
That is answerable offline the same way this task was - a TEXT-wide store scan for
`str/strb/strh` into those offsets - and it decides whether the two `IS_*` flags are
per-screen constants or a mod-settable hook. That is the first candidate to promote to the
next task; it is **not** started here.

---

## Closing summary

- **Task ID:** P2-UI-CONSTS
- **Status:** DONE
- **Changed files:**
  - `research/P2-UI-CONSTS.md` (new, this file)
  - `evidence/P2-UI-CONSTS/` (new): `00_string_search.txt`, `01_reference_sites.txt`,
    `02_group1_window.txt`, `03_regfn_0x33750a0.txt`, `04_group2_windows.txt`,
    `05_group2_prologues.txt`, `06_claim_check.txt`, `07_llvm_crosscheck.txt`,
    `08_assembler_roundtrip.txt`, `09_input_identity.txt`, `10_prologue_encodings.txt`
  - `scratch/2026-10-04_P2-UI-CONSTS/` (new): unmodified copies `d.py`, `w.py`, `fstart.py`,
    `strfind.py`, `refscan.py`, `relocs.py`; new `strfind9.py`, `refscan9.py`, `fstarts.py`,
    `scanpro.py`, `addend.py`, `elfwrap.py`, `check_claims.py`, `group1_values.elf`,
    plus raw outputs
- **Verified checks:** input sha256 rehash matched; **179/179** address, word, text and
  value claims re-derived from the image with exit 0; **10/10** deliberate corruptions of
  the check script rejected with a nonzero exit; all seven group-1 value words round-trip
  through the LLVM 22.1.8 assembler; no relocation addend points at any of the nine strings.
- **Unresolved / out of scope:** what the game does with any of these values; the contents
  of `0x05306b8c` (past EOF) and of `x19+0xdc`; the meaning of the `x2` pointers
  `0x042b1a84` and `0x043ccb7b`; whether a run-time-built name string could register any
  of the nine (neither scan would find it).
- **Next experiment:** trace the writers of `0x05306b8c` and of `x19+0xdc` in
  `0x1874680` with a TEXT-wide store scan, to establish whether `IS_SKILL_EDITABLE` and
  `IS_READ_ONLY` are fixed constants or a mod-settable hook (see above).