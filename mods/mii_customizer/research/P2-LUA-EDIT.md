# P2-LUA-EDIT - guarded instruction and constant editing for lua53-inspect

Task: fix the `xref` iAsBx defect and add three refuse-by-default mutators to
`tools/lua53-inspect/`. **Status: DONE.** Tool task only: no mod Lua logic was
designed or written, and no chunk was produced for use in the game.

Everything below is offline evidence about **bytes and encoding only**
(tier B), against the pinned Lua 5.3.6 sources (tier C). There is **no claim
anywhere in this report that the game would load an edited chunk**, let alone
behave differently.

## 1. Inputs, read-only, unchanged

All three hashes are identical before and after this task (re-measured at the
end of the session):

| path (workspace-relative) | sha256 | bytes |
|---|---|---|
| `gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_edit_actor.lc` | `1f73dff133961b68dbe24641298229b9f3905a44703164563911b105eaa16908` | 10321 |
| `gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc` | `ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d` | 7799 |
| `gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc` | `c777ecc492cea48f6ffd40112b22f96e66219d00969b570a7cc3cf8d7f4a9417` | 10576 |

The special-actor hash matches the coordinator's independently measured value
in `research/COORDINATOR-2026-10-04.md`, so the two agree on which file this is.

Format authority: `lua/lua` tag **v5.3.6**, fetched to
`scratch/2026-10-04_P2-LUA-EDIT/pinned-lua-5.3.6/` for line-accurate citation.

| file | sha256 |
|---|---|
| `lopcodes.h` | `f6ed980dc9cab58f1392757baabc9f1fecf5823148ca10c968c6f79fad7cda36` |
| `lopcodes.c` | `01ec54f3c53e2485e2ed43e396e9460f393e3db21782901dc656df6f41cee7e7` |
| `lundump.c` | `1183d9a46a06baf33af6900203aed8c04b3e59128f6645af0a2a6d7dd8da3a7c` |
| `ldump.c` | `a49a25e1358d49cc18bbe1b9e2b58ac3b661bc59326299b16227db41c3530823` |
| `lvm.c` | `70b57c5a2f2ba8f19d48b0dacd1ee23ee28323ba084bef2a2686348cee5d96a4` |
| `lobject.h` | `dcf71ef0b0b262db8620eab9bb5c299e4c74d9039c0647fa85ff2771df7b8eba` |

## 2. Part A - the `xref` defect, fixed

### The defect

`const_uses()` skipped instructions whose opmode was `iABx` but nothing else,
then tested `BITRK` on the raw `B` and `C` fields. Two distinct classes of
false positive came out of that, and both are gone:

1. **iAsBx instructions.** `JMP`, `FORPREP`, `FORLOOP` and `TFORLOOP` are
   **iAsBx** (`lopcodes.c:106, 115, 116, 118`). In that format `B` and `C` are
   not separate operands at all: `POS_Bx == POS_C` (`lopcodes.h:50`), so they are
   the two halves of `Bx` and bit 8 of either is part of the **jump offset**.
   Because `BITRK` is bit 8 (`lopcodes.h:134`), every jump whose `Bx` was at or
   above `2*MAXARG_sBx` had `BITRK` set in `B` and was reported as an RK use of
   a constant it never reads.
2. **iABC fields whose argument mode is not `OpArgK`.** `luaP_opmodes` packs
   the B and C modes into bits 4-5 and 2-3 (`lopcodes.c:72`), read by
   `getBMode`/`getCMode` (`lopcodes.h:284-285`). `GETTABUP` `B` is `OpArgU` --
   an upvalue index (`lopcodes.c:82`) -- and `TEST`/`TESTSET` `C` is `OpArgU`
   (`lopcodes.c:110-111`). Their bit 256 says nothing about constants either.

### The fix

`rk_operands()` is now the single place that decides this, and it reads
`OPMODES` directly. `const_uses()` and `verify()`'s `rk-constant-in-range` check
both call it, so the three cannot drift apart again. `LOADKX` is also handled
now: its constant index is not in the instruction at all but in the `Ax` of the
following `EXTRAARG` (`lopcodes.h:255`; read at `lvm.c:812-817`).

`verify()`'s existing `rk-constant-in-range` check had the same conflation --
it tested both `B` and `C` whenever *C*'s mode was `OpArgK`, which would have
read `GETTABUP`'s upvalue index `B` as a constant. It was latent rather than
firing, because `MAXUPVAL` is 255 and `BITRK` is bit 8. It now uses the same
helper. **No check was weakened or removed.**

### Counts, and why they differ from P2-UI-FLOW 2.1

Measured over all prototypes of each chunk
(`evidence/P2-LUA-EDIT/xref_counts_before_fix.txt`,
`xref_counts_after_fix.txt`, `check_lua53_inspect_after.txt`):

| chunk | iAsBx instrs | reported as RK uses **before** | **after** | RK operands | RK on distinct instrs | LOADK | LOADKX |
|---|---|---|---|---|---|---|---|
| special actor | 33 | **33** | **0** | 349 | **336** | 93 | 0 |
| edit actor (base) | 139 | **139** | **0** | 627 | **582** | 68 | 0 |
| edit actor (patch) | 146 | **146** | **0** | 643 | **598** | 69 | 0 |

- **"after" is 0 on all three chunks.** Required, and measured.
- **The before-column reproduces P2-UI-FLOW's 33 / 139 / 146 exactly.** Per
  opcode (special actor): `FORLOOP` 8 (`BITRK` on C), `FORPREP` 8 (on B),
  `JMP` 17 (16 on B, 1 on C) -- 33. `BITRK` lands on `B` when `Bx >= 131072`,
  i.e. `sBx >= 1`, a **forward** jump; `FORLOOP` is always backward, so its bit
  lands on `C` instead. That is why every one of the 33 was caught: a jump in
  one direction or the other always sets bit 8 somewhere in `Bx`.
- **The genuine counts reproduce P2-UI-FLOW's 336 / 582 / 598 exactly, under a
  different counting unit.** `const_uses()` returns one row per **operand**, and
  P2-UI-FLOW counted one row per **instruction**. The difference is exactly the
  number of instructions carrying a constant in *both* `B` and `C`: **13, 45,
  45**. 349-13=336, 627-45=582, 643-45=598. Those are mostly `SETTABLE`
  (`RK.B` 38 / `RK.C` 13 on the special actor). **Nothing was adjusted to make
  the numbers match**; the reconciliation is arithmetic and is checkable from
  the byte breakdown in the evidence file.
- Per-opcode breakdown of the genuine RK uses, special actor: `GETTABUP` 71,
  `GETTABLE` 97, `SELF` 97, `EQ` 5, `ADD` 6, `SUB` 9, `LT` 1, `LE` 2,
  `SETTABLE` 38+13, `SETTABUP` 10.
- **Every reported use was re-decoded a second time straight from the file**,
  reading the 4 raw bytes at the instruction's own recorded offset and
  re-checking the constant index. 349 / 627 / 643 re-decodes, **0 mismatches**.

## 3. Part B - three mutators

Each is a library function plus a CLI command. All three validate the request
against the pinned format, raise `EncodeError` **before touching the tree**, and
the CLI writes **no file** on refusal. After a successful edit each re-parses
its own output and runs `verify()` on it; if `verify()` would fail, the file is
not written.

Exit codes: `0` written, `1` refused (nothing written), `2` bad command line.

### 3.1 `appendconst` / `append_constant`

Appends one string, integer or float to the **end** of one prototype's constant
table and prints the index, then whether it is still reachable as an **RK
operand** or only by **LOADK**.

Appending is safe for a structural reason rather than a lucky one: `LOADK`,
`LOADKX` and RK operands index the constant table *positionally*
(`lopcodes.h:172-173`), so any other insertion silently re-points every later
reference. `--at` exists only so a non-end position is refused explicitly.

Reachability uses `MAXINDEXRK`, which is `BITRK - 1` == **255**
(`lopcodes.h:143`) -- `BITRK` is bit 8 of a 9-bit field, so an RK operand names
only the low 8 bits of the constant index. Both branches were exercised:
`K[7]` reported RK-possible, and a table grown past 256 entries reported
`K[256]: LOADK only`.

Numbers use the **chunk's own widths** from the parsed header, not the host's.
The three SSBU chunks are 4-byte floats, so a double that is not exactly a
float32 is **refused** rather than silently rounded (0.1 would be stored as
0.10000000149011612).

### 3.2 `patchins` / `patch_instruction`

Replaces **one** instruction, given as opcode and fields, and prints the old and
new decoded instruction. **A raw 32-bit word is never accepted** -- a raw word
can set fields the opcode's format does not have, and there is then nothing
left to check it against.

Validated: field names against the opcode's format; every field against
`MAXARG_A`/`MAXARG_B`/`MAXARG_C`/`MAXARG_Bx`/`MAXARG_sBx`/`MAXARG_Ax`;
`LOADK Bx` and every RK operand against the real constant count; `CLOSURE Bx`
against the real nested-proto count; registers against `maxstacksize`,
including the multi-register spans quoted from the opcode comments
(`lopcodes.h:171-233`) -- `LOADNIL` `A..A+B`, `SELF` `A..A+1`, `CONCAT` `B..C`,
`CALL`/`TAILCALL` `A..A+max(B,C)-1`, `RETURN`/`VARARG` `A..A+B-2`, `SETLIST`
`A..A+B`, `TFORCALL` `A..A+2+C`, `FORPREP` `A..A+2`, `FORLOOP`/`TFORLOOP`
`A..A+3`, `JMP A!=0` up from `A-1`; upvalue indices for `GETUPVAL`/`SETUPVAL`/
`GETTABUP B`/`SETTABUP A` against the real descriptor count; `EQ`/`LT`/`LE` `A`
and `LOADBOOL`/`TEST` boolean operands against 0/1; iAsBx targets against the
code length; and the `LOADKX` / `SETLIST C=0` / `TFORCALL` adjacency.

One real bug was found and fixed **inside this task's own new code** while
writing these checks: the first version of the B/C operand loop read a `JMP`'s
`B` as a register, because `JMP`'s B mode is `OpArgR` (`lopcodes.c:106`). That
is the *same* conflation Part A exists to remove. The loop is now guarded by
`mode == iABC`, and `check_const_use_modes` asserts the iAsBx opcodes never
yield an RK operand.

### 3.3 `insertins` / `insert_instructions`

Inserts N instructions at one pc and relocates every affected relative jump.

**Jump kinds handled: the four iAsBx opcodes `JMP`, `FORPREP`, `FORLOOP`,
`TFORLOOP`.** All four compute their destination as `pc + 1 + sBx` (`lvm.c:741`
`dojump`; 1208 FORLOOP, 1238 FORPREP, 1259 TFORLOOP), so one rule covers them:
a destination at or after the insertion point moves by N, and the jump itself
moves by N when it sits at or after that point.

**Refused rather than handled** (inserting between the halves changes what the
first instruction skips):

| adjacency | pinned source |
|---|---|
| `EQ`/`LT`/`LE`/`TEST`/`TESTSET` + its jump | `testTMode`, bit 7 of `luaP_opmodes` (`lopcodes.h:287`); `donextjump` (`lvm.c:744`) |
| `LOADBOOL` with `C != 0` + next | `lvm.c:821` |
| `LOADKX` + `EXTRAARG` | `lopcodes.h:255`, `lvm.c:814` |
| `SETLIST` with `C = 0` + `EXTRAARG` | `lopcodes.h:252`, `lvm.c:1270` |
| `TFORCALL` + `TFORLOOP` | `lvm.c:1250-1253` |

Also refused: a relocated offset that no longer fits `sBx`; a prototype whose
`lineinfo` is present but not one entry per instruction.

`lineinfo` and `locvar` positions are kept consistent: inserted instructions
inherit the line of the instruction they are inserted before, and `locvar`
`startpc`/`endpc` at or after the insertion point shift by N. **This is a
choice, not a derivation** -- `lundump.c` loads those counts independently
(`lundump.c:187-192`), so a stale line table would still parse but would mean
nothing.

`CALL`/`TAILCALL`/`RETURN`/`VARARG`/`SETLIST` extents come from `L->top` at run
time, not from a pc. Insertion is no more dangerous there than anywhere else,
but this tool offers **no guarantee** about them and says so.

## 4. What was verified, and how

`evidence/P2-LUA-EDIT/` (all commands run from the workspace root, `python`
not `python3`):

| evidence file | what it shows |
|---|---|
| `xref_counts_before_fix.txt` | per-opcode, per-field breakdown of the defect |
| `xref_counts_after_fix.txt` | the three chunks after the fix, 0 iAsBx uses, plus raw re-decode |
| `check_lua53_inspect_after.txt` | the shipped check suite: **217 passing checks, exit 0** |
| `verify_three_chunks_after.txt` | `verify` exit 0 on the three originals |
| `roundtrip_three_chunks_after.txt` | `roundtrip` exit 0, 3/3 BYTE-IDENTICAL |
| `mutator_proof_and_refusals.txt` | refusal exit-code table + the synthetic chain |
| `real_chunk_exercise.txt` | each mutator once on a copy of a real chunk |

### 4.1 Check suite

`python mods/mii_customizer/tools/lua53-inspect/check_lua53_inspect.py <the
three chunks>` -> **217 PASS, exit 0** (was 155). Nothing was skipped, weakened
or suppressed. New groups:

- `check_xref_regression`, per chunk: iAsBx reported as a constant use is 0;
  every RK use sits on an `OpArgK` field of an iABC instruction; the iAsBx
  class is exactly the four expected opcodes.
- `check_const_use_modes`: `rk_operands` agrees with a direct read of the
  opmode table for **all 47 opcodes**, and each of the four iAsBx opcodes plus
  `GETTABUP B` / `TEST C` / `TESTSET C` yields no RK operand.
- `check_mutators`: the full positive chain, then one refused request per rule.

`synth` was extended so `insertins` has every shape to relocate: a numeric
`for` loop (`FORPREP`/`FORLOOP`), a forward and a **backward** `JMP`, and both
implicit-skip pairs (`EQ`+`JMP`, `LOADBOOL C!=0`). Every jump offset is derived
from its destination pc by a helper, never hand-typed, so the fixture cannot
carry an off-by-one. `maxstacksize` went 3 -> 8 because the loop uses R3..R6
(`FORLOOP` writes `R(A+3)`).

### 4.2 Synthetic proof chain

`appendconst` -> `insertins` a `LOADK` consuming the new constant inside the
loop body -> `verify` / `compare` / `roundtrip`:

- appended `K[7] = "p2_lua_edit_marker"`, reported RK-possible; `K[0..6]`
  unchanged in tag, kind and value; `compare` shows exactly one difference,
  `main.constants: 7 != 8`.
- inserted `LOADK A=7 Bx=7` at pc 11. Relocation, exactly as the rule predicts:

  ```
  pc6  JMP      sBx +2 -> +2   target pc 9  -> pc 9    (jump before, target before)
  pc8  JMP      sBx -6 -> -6   target pc 3  -> pc 3    (jump before, target before)
  pc9  FORPREP  sBx +2 -> +3   target pc 12 -> pc 13   (jump before, target after)
  pc12 FORLOOP  sBx -3 -> -4   target pc 10 -> pc 10   (jump after, target before)
  ```

  **Both directions exercised**, plus the no-change case.
- `verify` exit 0 (all 10 checks PASS). `roundtrip` **BYTE-IDENTICAL**, same
  sha256, no reparse diff. `compare` against the pre-append chunk shows
  exactly three expected lines: code 15->16, constants 7->8, lineinfo extended.
- **Every pre-existing jump still reaches the same instruction**: for each, the
  new target is the mapped old target and the instruction decoded there has the
  same opcode. Every non-jump pre-existing instruction is unmoved with an
  unchanged word. The relocated set is exactly the 4 iAsBx jumps.
- `lineinfo` stays one entry per instruction (16 for 16).
- `const_uses` then finds the new constant consumed by a `LOADK` at pc 11, so
  the inserted load is real, not decorative.
- `patchins` on top of that replaced exactly one word, kept the length, passed
  `verify` and round-tripped.

### 4.3 Format exercise on a COPY of a real chunk

Input read-only, worked on a copy; outputs only to
`gamedata/mii_customizer/P2-LUA-EDIT/`. **This copy is a format exercise, not
a candidate for the game.**

| run | size | structural diff vs source | `verify` |
|---|---|---|---|
| `appendconst main string` (K[24]) | 7799 -> 7837 (**+38**) | `main.constants: 24 != 25` only | exit 0, 0 FAIL |
| `patchins main pc0 GETTABUP A=0 B=0 C=256` | 7799 -> 7799 (**+0**) | **no structural differences** | exit 0, 0 FAIL |
| `insertins main pc30 MOVE A=10 B=10` | 7799 -> 7803 (**+4**) | `main.code: 56 != 57` only | exit 0, 0 FAIL |

- The appended index is `K[24]`, still **RK-possible** (`24 <= 255`).
- `patchins` was chosen as an **identity** re-patch on purpose. Its output is
  byte-identical to the source (same sha256 `ffa2bafa...`), which is the point:
  a real instruction -- including an `RK.C` operand with `BITRK` set -- survives
  the opcode+fields validate -> assemble -> encode path bit-for-bit. A
  **non-identity** patch of an arbitrary instruction cannot be proven
  behaviour-preserving without dataflow analysis, which this tool deliberately
  does not have; that is stated rather than glossed over.
- The insertion used `MOVE R[10] R[10]` on `main` (maxstack 22, so R[10]
  exists) -- structurally neutral. `main` has **no** iAsBx jumps, so nothing
  needed relocating there.
- To exercise relocation on **real game data**, a second insertion at
  `main.p14` pc 13 (inside the for-loop body: head pc 12, `FORLOOP` pc 18)
  relocates all 5 of that proto's jumps, again in both directions:

  ```
  pc11 FORPREP sBx +6 -> +7   target pc18 -> pc19  (expected pc19)  OK
  pc18 FORLOOP sBx -7 -> -8   target pc12 -> pc12  (expected pc12)  OK
  pc33 JMP     sBx-12 -> -12  target pc22 -> pc23  (expected pc23)  OK
  pc37 FORPREP sBx +6 -> +6   target pc44 -> pc45  (expected pc45)  OK
  pc44 FORLOOP sBx -7 -> -7   target pc38 -> pc39  (expected pc39)  OK
  ```

- Refusals on the **real** chunk, all exit 1 with no file written: a register
  past `maxstacksize` 22; `--at 0` on a 24-constant table; an insertion at pc 33
  of `main.p14` that would split the `EQ`(pc 32)+`JMP`(pc 33) pair; a jump
  target past the code length.
- **The original chunk hashes the same before and after**
  (`ffa2bafa...` == `ffa2bafa...`).

## 5. Every refusal, with its exit code

All 25 exit 1, all with **no file written**
(`evidence/P2-LUA-EDIT/mutator_proof_and_refusals.txt`):

| command | refusal |
|---|---|
| `appendconst --at 0` | constants can only be APPENDED; inserting would move every later index |
| `appendconst boolean` | appends string/integer/float only |
| `appendconst nil` | appends string/integer/float only |
| `appendconst float 0.1` | not exactly representable in float32 |
| `appendconst integer 2**64` | does not fit this chunk's 8-byte `lua_Integer` |
| `appendconst main.p99` | no such prototype |
| `patchins` `LOADK Bx=99` | `Bx` past the constant table |
| `patchins` `MOVE A=99` | register past `maxstacksize` |
| `patchins` `MOVE A=1 Bx=2` | iABC has no `Bx` field; dropping it would silently change the word |
| `patchins` unknown opcode | unknown opcode |
| `patchins` `JMP sBx=9999` | target 10006 outside `0..15` |
| `patchins` pc 999 | pc does not exist |
| `patchins` `CLOSURE Bx=9` | past the nested proto count |
| `patchins` `EQ B=355` | `RK.B` names `K[99]`, past the constant table |
| `patchins` `GETUPVAL B=9` | upvalue index past the descriptor count |
| `patchins` `MOVE A=300` | field does not fit `0..255` |
| `patchins` `LOADKX A=0` | must be followed by `EXTRAARG` |
| `insertins` pc 6 | would split the `EQ`+`JMP` pair |
| `insertins` pc 14 | would split the `LOADBOOL C=1`+next pair |
| `insertins` `N=0` | nothing to insert |
| `insertins` pc 99 | outside `0..15` |
| `insertins` `MOVE A=99` | register past `maxstacksize` |
| `insertins` unknown opcode | unknown opcode |
| `insertins` `TFORCALL` | must be followed by `TFORLOOP` |
| `insertins` `SETLIST C=0` | must be followed by `EXTRAARG` |

Plus, in the check script only (needs an in-memory fixture the CLI cannot
build): a relocated offset that no longer fits `sBx`, and the **verify gate** --
a tree that encodes but fails `verify()` is not written. The gate did not fire
in any CLI-tested case, because the mutator's own validation is at least as
strict as `verify()`; it is there as a backstop and its refusal path is
asserted directly.

## 6. What remains unsupported

- **Nothing here says the game would load an edited chunk.** A passing
  `verify()`, a byte-exact round-trip and a clean structural diff are evidence
  about **encoding** only. Whether the game's loader accepts a modified chunk,
  whether it hashes it, and whether the UI would behave differently are all
  open and can only be settled on the console.
- **No compiler, no decompiler, no dataflow analysis.** `R[n]` means "the value
  in register n", never a known value. **No mutator can promise a semantically
  neutral edit to an arbitrary instruction.**
- **Not implemented, on purpose:** deleting instructions or constants, inserting
  or reordering prototypes, editing upvalue descriptors, merging or splitting
  prototypes, and constant-table de-duplication. Insertion of a constant at any
  position other than the end is refused.
- **Line/local-variable bookkeeping is a stated policy, not a proof.** The
  chunk format loads `lineinfo` and `locvar` counts independently, so there is
  no way to *derive* the right values; they are kept consistent by rule and the
  rule is documented.
- **Unvalidated as a whole:** `CALL`/`TAILCALL`/`RETURN`/`VARARG`/`SETLIST`
  `top`-relative extents. Provable register operands of those opcodes are still
  checked; the rest is left alone.
- `LOADKX` is reported by `const_uses` only when the following `EXTRAARG` is
  present. A malformed chunk with a missing follower is not attributed to any
  index. **Measured: 0 `LOADKX` in all three editor chunks**, so this path is
  exercised only by the synthetic fixture.

## 7. Changed files

| path | change |
|---|---|
| `tools/lua53-inspect/lua53_inspect.py` | Part A fix (`rk_operands`, `const_uses`, `verify`); three mutators + CLI commands; `synth` extended; `MAXARG_A/B/C/Ax`, `MAXINDEXRK`; docstring corrections |
| `tools/lua53-inspect/check_lua53_inspect.py` | `check_xref_regression`, `check_const_use_modes`, `check_mutators`; 155 -> 217 checks |
| `tools/lua53-inspect/README.md` | usage, the `xref` fix and counts, a Mutators section with a refusal table, updated limits and status |
| `research/P2-LUA-EDIT.md` | this report |
| `evidence/P2-LUA-EDIT/*` | 7 evidence files |
| `scratch/2026-10-04_P2-LUA-EDIT/` | pinned sources, 5 scripts, outputs |
| `gamedata/mii_customizer/P2-LUA-EDIT/` | 3 chunk copies (format exercise only) |

No other worker's files were touched. No commits, branches, emulator runs, SD
access or framework changes. `STATUS.md`, `CURRENT_INSTALL.md`, `CHANGELOG.md`
and the shared contracts are the coordinator's and were left alone.

One incidental correction, doc-only: the module docstring claimed
`dis <file> <proto_path>`, but `dis` takes an optional leading **digit** string
limit and disassembles every prototype. Passing a proto name made the tool try
to open it as a path. Corrected in the docstring and in `_cmd_dis`; no
behaviour changed.

## 8. Next experiment

The interesting question this task does **not** answer is whether a
*behaviourally* meaningful edit is achievable, which needs two things the tool
deliberately does not have:

1. **A register-value model for one bounded function**, not a general one. The
   natural first target is the one P2-UI-FLOW already characterises: `main.p14`
   pc 34-44, the unconditional `set_skill_id` write-back loop. If a
   register-value-at-pc resolver is added for a *single* named prototype with
   its assumptions written down, `patchins` could assert a genuinely
   non-identity, provably behaviour-preserving edit instead of the identity
   patch used here. That is the smallest step that would turn this tool from a
   format exerciser into an authoring tool.
2. **A console gate for one such edit**, bundled with a useful diagnostic
   rather than spent on a cosmetic change. Nothing here can substitute for it.

Independently of (1): the coordinator's stated blockers are still
per-saved-fighter identity, the native bridge, and per-instance runtime stat
reads. `insertins`/`patchins` do not move any of them, and a worker should not
treat this tool as unblocking them.