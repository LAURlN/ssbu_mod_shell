# lua53-inspect

Bounded inspector (and matching encoder) for **Lua 5.3** precompiled chunks (`.lc`).
It parses a chunk exactly the way the reference loader does, records the byte
offset of every field, and decodes the subset of opcodes needed to answer
counting, table-field, branch and call questions.

It is **not** a decompiler. Opcodes it does not decode stay unannotated rather
than being turned into invented Lua source.

It can also write: `roundtrip` proves parse -> encode reproduces a chunk
byte-for-byte, `setconst` rewrites a single string constant, `compare` reports
every structural difference between two chunks, and since P2-LUA-EDIT three
guarded mutators -- `appendconst`, `patchins` and `insertins` -- append a
constant, replace one instruction and insert N instructions with full jump
relocation. **Reserialising or mutating a chunk successfully is evidence about
the bytes only. It is not evidence that the game would load a modified chunk,
and it is not evidence that a modified chunk would do anything sensible.**

## Status

Working. Verified on the three SSBU editor chunks of P1-UI-DECODE
(`verify` exits 0, full byte-exact consumption on all three) and re-verified
after the encoder was added in P1-LUA-WRITE (`roundtrip` exits 0 with identical
SHA256 on all three).

Extended in P2-LUA-EDIT: the `xref` iAsBx defect is fixed (see below) and three
guarded mutators were added. `check_lua53_inspect.py` now reports **217 passing
checks** on the three editor chunks, up from 155, exit 0.

No dependencies beyond the Python 3 standard library. Nothing is installed.

## Format authority

Pinned to the official reference implementation, tag **v5.3.6**:

| file | role |
|---|---|
| [lundump.c](https://github.com/lua/lua/blob/v5.3.6/lundump.c) | loader: header checks, proto order, string/constant encoding |
| (same files, `DumpFunction`/`DumpString`/`DumpHeader`) | the writer this tool's encoder mirrors |
| [ldump.c](https://github.com/lua/lua/blob/v5.3.6/ldump.c) | dumper, used to confirm what `strip` omits |
| [lopcodes.h](https://github.com/lua/lua/blob/v5.3.6/lopcodes.h) | instruction fields, sizes, positions, `BITRK` |
| [lopcodes.c](https://github.com/lua/lua/blob/v5.3.6/lopcodes.c) | opcode names and `luaP_opmodes` table |
| [lobject.h](https://github.com/lua/lua/blob/v5.3.6/lobject.h) | constant type tags |

This reads **Lua 5.3**, not LuaU. LuaU uses a different, extended chunk format
and is rejected by the version check.

## Usage

Paths are relative to the workspace root.

```bash
T=mods/mii_customizer/tools/lua53-inspect/lua53_inspect.py
G=gamedata/mii_customizer/P1-UI/ui
B=$G/script/menu/chara_make/make_mii_edit_actor.lc
S=$G/script/menu/chara_make/make_mii_special_actor.lc
P=$G/script_patch/chara_make/make_mii_edit_actor.lc

python3 $T header    $B $S $P     # header fields, sizes, endianness, float width
python3 $T summary   $B $S $P     # per-chunk totals + a row per prototype
python3 $T protos    $B           # every prototype and its sections
python3 $T dis       $B           # disassembly with byte offsets (optional max string length)
python3 $T constants $B           # constant tables with type tags and offsets
python3 $T xref      $B SKILL_COMMAND_NUM get_skill_id   # constant + every instruction using it
python3 $T verify    $B $S $P     # all structural checks, exit 0 only if clean
python3 $T roundtrip $B $S $P     # parse -> encode, compared by length, hash and structure
python3 $T encode    $S out.lc     # write a re-encoded copy
python3 $T compare   a.lc b.lc     # every structural difference, one per line
python3 $T setconst  in.lc out.lc main 6 "new text"   # rewrite ONE string constant
python3 $T appendconst in.lc out.lc main integer 7    # append ONE constant
python3 $T patchins  in.lc out.lc main 12 MOVE A=3 B=3   # replace ONE instruction
python3 $T insertins in.lc out.lc main 5 1 LOADK A=0 Bx=3  # insert N instructions
python3 $T synth     out.lc        # a small valid synthetic chunk, for tests
```

Use `python`, not `python3`, in this workspace.

`roundtrip` makes three independent comparisons (length, SHA256, and a
structural diff of the re-parsed output), so a single coincidence cannot make
it pass. `setconst` **refuses by default** to touch a constant that any
instruction consumes, and names the consuming instructions if you override it
with `--allow-used`.

`verify` and `xref` are the useful ones for analysis. `xref` reports **how** a
constant is reached, distinguishing `LOADK` (loaded into a register),
`LOADKX` (whose index is in the following `EXTRAARG`) from an `RK` operand
(used directly, e.g. `GETTABUP` reading a global name).

**Which operands are RK operands is decided by the pinned `luaP_opmodes`
table, not by a hand-written list.** That distinction is load-bearing and two
bugs lived in it (fixed in P2-LUA-EDIT):

- `JMP`/`FORPREP`/`FORLOOP`/`TFORLOOP` are **iAsBx**, and in that format `B` and
  `C` are simply the two halves of `Bx` (`lopcodes.h:50`). Their bit 8 is part
  of a jump offset, so a forward jump was being reported as an RK use of a
  constant it never reads. Measured on the three editor chunks: **33 / 139 /
  146** such instructions, every one wrongly reported, now **0**.
- iABC fields whose argument mode is **not** `OpArgK` are not RK operands
  either. `GETTABUP` `B` is `OpArgU` (an upvalue index, `lopcodes.c:82`),
  `TEST`/`TESTSET` `C` is `OpArgU` (`lopcodes.c:110-111`). Their bit 256 says
  nothing about constants.

P2-UI-FLOW 2.1 measured 336 / 582 / 598 genuine iABC RK uses. Those are
**distinct instructions**; this tool reports one row per *operand*, so its
counts are 349 / 627 / 643. The two agree exactly: 13 / 45 / 45 instructions
carry a constant in **both** `B` and `C` (mostly `SETTABLE`), which is the whole
difference.

### Checks

```bash
python3 mods/mii_customizer/tools/lua53-inspect/check_lua53_inspect.py $B $S $P
```

Per chunk: header acceptance and the 29-byte body offset, recursive parse of
every nested prototype, and these structural checks —

- `full-consumption` — the parse ends exactly on the file's last byte
- `opcodes-in-range` — every opcode number is a real 5.3 opcode
- `loadk-in-range`, `closure-in-range`, `rk-constant-in-range` — index bounds
- `jumps-in-range` — jump/test targets land inside the prototype
- `upvalue-name-count`, `locvar-pc-in-range` — debug-table sanity

Plus negative checks on deliberately damaged copies: empty and short input,
corrupted signature, wrong version, wrong format, corrupted `LUAC_DATA`, a
big-endian `LUAC_INT`, a wrong `LUAC_NUM`, an implausible size byte, truncation
at four cut points, and trailing garbage. Mutation checks confirm `verify()`
actually catches an out-of-range opcode, an out-of-range `LOADK` constant and
an out-of-range jump target, rather than silently passing.

Added in P2-LUA-EDIT:

- `check_xref_regression` (per chunk) -- the count of iAsBx instructions
  reported as constant uses is **0**, every reported RK use sits on an
  `OpArgK` field of an iABC instruction, and the iAsBx class is exactly
  `JMP`/`FORPREP`/`FORLOOP`/`TFORLOOP`.
- `check_const_use_modes` -- `rk_operands` agrees with a direct read of the
  opmode table for **all 47 opcodes**, and each of the four iAsBx opcodes plus
  `GETTABUP B` / `TEST C` / `TESTSET C` is asserted not to yield an RK operand.
- `check_mutators` -- the full positive chain on the synthetic chunk (append a
  constant, insert a `LOADK` that consumes it inside the loop body, patch one
  instruction), proving `verify`, byte-exact re-encoding, an exact structural
  diff, and that **every pre-existing jump still reaches the same instruction**;
  then one refused request per rule, each asserted to raise `EncodeError`.

The synthetic chunk (`synth`) carries a numeric `for` loop, a backward and a
forward `JMP`, and both implicit-skip pairs, so `insertins` has every shape to
relocate. Its jump offsets are derived from destination pcs, never hand-typed.

**Full consumption is the load-bearing check.** A wrong structure size, a
mis-sized float or a mis-read string length would desynchronise the walk and
leave trailing bytes, so a clean consumption result is strong evidence the
byte layout was read correctly.

## Encoder

`encode_chunk(header, proto)` writes a chunk back out in `ldump.c`'s field
order, using the widths recorded in the *parsed header* rather than the host's,
so a 4-byte-float chunk stays a 4-byte-float chunk. It preserves header widths,
floats, strings (including the `0xFF` size escape), nested prototypes,
instruction words, upvalue descriptors and every debug section.

Encoder-specific rules, all from `ldump.c`:

- **Size byte, not varint.** `DumpString` writes one byte while `size < 0xFF`
  and the `0xFF` + full `size_t` escape otherwise. `size` includes the trailing
  NUL, so it is `len + 1`. The parser records which form each string used, so
  a chunk that used the escape re-encodes identically rather than being
  normalised.
- **Type tag follows length, not use.** A rewritten string gets
  `LUA_TSHRSTR` at or below `LUAI_MAXSHORTLEN` (40) and `LUA_TLNGSTR` above it.
- **Source strings.** `LoadFunction` substitutes the parent's source when the
  dumped string is NULL, so the parser records that NULL separately; otherwise
  every child proto would be re-encoded with the parent's source string.
- **One new structural check.** `main-upvalue-count` compares the header's main
  closure upvalue byte against the main proto's descriptor count, which
  `luaU_undump` asserts.

### Limits

- **`setconst` only rewrites string constants.** `set_string_constant` refuses
  any other constant kind, an unknown proto path, and an out-of-range index. It
  cannot change an instruction word or move a prototype.
- **`--allow-used` is a claim, not a check.** The tool can tell you a constant
  is referenced; it cannot tell you whether that reference is a bridge name, a
  selector, a flag, a loop bound or a native argument. That judgement is yours.
- **Round-tripping proves the encoding, not the load.** Identical bytes and a
  passing `verify()` say the file matches the format. They say nothing about
  whether the game's loader accepts it, whether it hashes the chunk, or whether
  the UI would behave differently. Only a console run can settle that.

## Mutators (P2-LUA-EDIT)

Three guarded edits. Each is a library function plus a CLI command, each
**refuses anything it cannot prove safe against the pinned format, raises
before touching the tree, and writes no file on refusal**.

Shared CLI exit codes: `0` written, `1` refused (nothing written), `2` the
command line itself was wrong. After a successful edit every mutator re-parses
its own output and runs `verify()` on it; if `verify()` would fail, the file is
not written.

Field syntax is `OPNAME A=.. B=.. C=..` for iABC, `A=.. Bx=..` for iABx,
`A=.. sBx=..` for iAsBx and `Ax=..` for iAx. **Asking for a field the opcode's
format does not have is refused, not dropped** -- dropping it would silently
change the word. Opcodes and fields are validated from `luaP_opmodes`
(`lopcodes.c:74-123`) and the opcode comments (`lopcodes.h:171-233`), never
from a hand-written list.

### `appendconst` -- append one constant

```bash
python lua53_inspect.py appendconst in.lc out.lc <proto> <string|integer|float> <value> [--at <index>]
```

Appends **to the end only** and prints the new index, then whether that index is
still reachable as an **RK operand** (`index <= MAXINDEXRK`, i.e. 255,
`lopcodes.h:143`) or only by **LOADK**. Appending is safe for a structural
reason, not a lucky one: `LOADK`/`LOADKX` and RK operands index the constant
table *positionally* (`lopcodes.h:172-173`), so any other insertion would
silently re-point every later reference. `--at` exists only so a non-end
position is refused explicitly rather than being unreachable.

Numbers use the **chunk's own widths** from the parsed header: `sizeof
lua_Integer` and `sizeof lua_Number`. The three SSBU chunks are 4-byte floats,
so a Python double that is not exactly representable in float32 is refused
rather than silently rounded.

| refusal | why |
|---|---|
| `--at` anywhere but the end | inserting would move every later index and re-point the operands that name them |
| kind `nil` or `boolean` | nothing changes by adding them; refused rather than pretended useful |
| a float not exactly a float32 | the chunk cannot store it; rounding is a silent semantic change |
| an integer outside `lua_Integer` | does not fit the width the loader will read (`lundump.c:78`) |
| new index above `MAXARG_Bx` | no instruction could reach it |
| unknown proto path | nothing to mutate |

### `patchins` -- replace one instruction

```bash
python lua53_inspect.py patchins in.lc out.lc <proto> <pc> <OP> [fields...]
```

Replaces **one** instruction, given as opcode and fields. **A raw 32-bit word is
never accepted**: a raw word can set fields the opcode's format does not have,
and there is then nothing left to check it against. Prints the old and the new
decoded instruction.

Validated: field names against the opcode's format; each field against
`MAXARG_A`/`MAXARG_B`/`MAXARG_C`/`MAXARG_Bx`/`MAXARG_sBx`/`MAXARG_Ax`;
`LOADK Bx` and every RK operand against the real constant count; `CLOSURE Bx`
against the real nested-proto count; registers against `maxstacksize`, including
the multi-register spans quoted from the opcode comments (`LOADNIL`
`A..A+B`, `SELF` `A..A+1`, `CONCAT` `B..C`, `CALL`/`TAILCALL` `A..A+max(B,C)-1`,
`RETURN`/`VARARG` `A..A+B-2`, `SETLIST` `A..A+B`, `TFORCALL` `A..A+2+C`,
`FORPREP` `A..A+2`, `FORLOOP`/`TFORLOOP` `A..A+3`, `JMP A!=0` `A-1`); `GETUPVAL`
/`SETUPVAL`/`GETTABUP B`/`SETTABUP A` against the real upvalue count; boolean
operands of `LOADBOOL`/`TEST` against 0/1; `EQ`/`LT`/`LE` `A` against 0/1;
iAsBx targets against the code length; and the `LOADKX` / `SETLIST C=0` /
`TFORCALL` "next instruction must be X" adjacency.

`CALL`, `RETURN`, `SETLIST`, `VARARG` and `TAILCALL` with a zero count mean
"up to `L->top`" (`lopcodes.h:250-253`), which is not a value this tool can
resolve. Those operands are **left alone rather than guessed**; the registers
that *are* provable from the instruction are still checked.

### `insertins` -- insert N instructions, relocating every jump

```bash
python lua53_inspect.py insertins in.lc out.lc <proto> <pc> <N> <OP> [fields...] x N
```

Inserts N instructions at one pc and relocates every affected relative jump.

**Jump kinds handled:** the four iAsBx opcodes `JMP`, `FORPREP`, `FORLOOP` and
`TFORLOOP`. All four compute their destination as `pc + 1 + sBx` (`lvm.c:741`
`dojump`; 1208 FORLOOP, 1238 FORPREP, 1259 TFORLOOP), so one rule covers them:
a destination at or after the insertion point moves by N, and so does the jump
itself when it sits at or after that point. A jump whose offset therefore does
not change is reported as such.

**Refused rather than handled:**

- the implicit `pc++` skips of `EQ`/`LT`/`LE`/`TEST`/`TESTSET` (bit 7 of
  `luaP_opmodes` is set, `testTMode`, `lopcodes.h:287`) and of `LOADBOOL` with
  `C != 0` (`lvm.c:821`);
- the two `EXTRAARG` adjacencies, `LOADKX` (`lopcodes.h:255`, `lvm.c:814`) and
  `SETLIST` with `C = 0` (`lopcodes.h:252`, `lvm.c:1270`);
- `TFORCALL`, which always falls into the `TFORLOOP` at the next pc
  (`lvm.c:1250-1253`).

Inserting between the two halves of any of those changes what the first
instruction skips, so `protected_pair()` refuses the insertion point. Also
refused: a relocated offset that no longer fits `sBx`, and a prototype whose
`lineinfo` is present but not one entry per instruction.

`lineinfo` and `locvar` positions are **kept consistent**: inserted
instructions inherit the line of the instruction they are inserted before, and
`locvar` `startpc`/`endpc` at or after the insertion point shift by N. This is
a choice, not a derivation -- `lundump.c` loads those counts independently, so
a stale line table would still parse but would mean nothing.

**Not handled and not reasoned about:** `CALL`/`TAILCALL`/`RETURN`/`VARARG`/
`SETLIST` extents come from `L->top` at run time, not from a pc. Inserting is
no more dangerous there than anywhere else, but this tool offers no guarantee
about them.

### Not implemented, on purpose

Deleting instructions or constants, inserting or reordering prototypes, editing
upvalue descriptors, and any kind of compiler. Those need the reachability and
dataflow analysis this tool deliberately does not have. There is no decompiler
and no Lua-level type checker: `R[n]` means "the value in register n", never a
known value, so **no mutator here can promise a semantically neutral edit to an
arbitrary instruction**.

## Notes on this format

Facts established while validating against the SSBU chunks, each confirmed
against the pinned source rather than assumed:

- **These chunks use 4-byte `lua_Number` (float32), not double.** The header
  records `sizeof lua_Number = 4`, so the header is **29 bytes** and the first
  prototype starts at `0x1e`. A parser that assumes 8-byte doubles desyncs
  immediately. `LUAC_NUM` is read as a 4-byte float and equals 370.5.
- **String lengths are not variable-length integers.** `LoadString` reads one
  size byte, with `0xFF` as the only escape to a full `size_t`. The dumped
  size includes the trailing NUL, so the stored text is `size - 1` bytes.
  Treating string sizes as LEB128/ULEB128 is a common and silent mistake.
- **Upvalue descriptors and upvalue names are different counts.** `DumpUpvalues`
  always dumps the real descriptor count, but `DumpDebug` dumps the upvalue
  *name* count as 0 when the chunk is stripped. So `0 names / N upvalues` is
  the normal stripped shape and is not an error.
- These chunks are **fully stripped**: `lineinfo`, `locvars` and upvalue names
  are all zero in every prototype, because `DumpDebug` writes a count of 0 for
  each when `strip` is set. Do not expect `lineinfo` to survive; it does not.
  What *does* survive is `linedefined`/`lastlinedefined`, which `DumpFunction`
  writes unconditionally outside the debug section - those are still usable to
  line up prototypes across versions of the same script.
  (Corrected in P1-LUA-WRITE: an earlier version of this note claimed
  `lineinfo` survived. Measured: 0 lineinfo entries in all three chunks.)
- `main.pN` names prototypes in load order, which matches `CLOSURE Bx`.

## Limits

- Decode is bounded to what the task needed: counts, table fields, globals,
  branches, and calls. Other opcodes are listed with operands but not
  annotated, and are never guessed at.
- No control-flow graph, no decompilation, no constant folding, no evaluation.
  Register values are *not* tracked, so `R[n]` in an annotation means "the
  value in register n", not a known value.
- A decoded instruction is evidence about the **bytecode only**. It says nothing
  about native function bindings, runtime behaviour, or where a value is
  persisted. A `UiScriptPlayer.invoke` call site proves the name is passed to
  native code, not what native code does with it.
- Only the chunk's own bytes are read. Symbols such as `SKILL_COMMAND_NUM` that
  are read from `_ENV` but never assigned in the chunk have **no** value
  recoverable here; chasing them means reading another chunk.
