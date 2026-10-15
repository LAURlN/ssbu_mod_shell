# P5-LUA-SOURCE - reconstruct the Lua source of make_mii_special_actor.lc

Worker: Space Bunny Alpha. Phase 5 UI track. Date 2026-10-05.
Result: **PARTIAL** - all 17 prototypes byte-identical, one byte of the file is
not reachable from Lua source with stock Lua 5.3.6.

Evidence tier: everything below is **B** (offline measurement on the chunk's
bytes). No console run, no emulator run, no claim about runtime behaviour.

## Inputs

| path | sha256 / size |
|---|---|
| `gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc` | `ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d`, 7799 bytes (read-only input, unmodified) |
| `mods/mii_customizer/evidence/P4-LUAC/listings/special_actor.luac-l-l.txt` | P4-LUAC listing, used as a cross-check against a freshly regenerated one |
| `mods/mii_customizer/tools/luac53-game/bin/luac-game.exe` | P4-LUAC compiler, `-DLUA_FLOAT_TYPE=LUA_FLOAT_FLOAT` |

`verify_sources.py` rerun: "release tarball vs unpacked src/: 61 files
compared, 61 identical, 0 different", exit 0 (B) - the compiler is stock
Lua 5.3.6 with only the float-width configuration changed.

## Deliverables

| path | sha256 |
|---|---|
| `tools/lua-src/make_mii_special_actor.lua` | `650b757e824cb6cb71108d802fa9713c5c0d9de3a83fa55ed17d392cf364270d` |
| `tools/lua-src/build_check.py` | `7054d22935ba88e5e4f28d4a1dd0a1c3523c13a3bda2c30c5012938242f8ec7e` |
| `tools/lua-src/README.md` | `1d901d662f06acb32f2f8bd943084166859661c8b4fefeff8db8341985f7a76a` |
| `evidence/P5-LUA-SOURCE/check_vararg_byte.py` | `78a66e1db0f93e3a6918b96d51f45d418b1df47aff587e95a34c07e2f8532c5f` |

Scratch (not deliverables): `scratch/2026-10-05_P5-LUA-SOURCE/` holds
`cmp_protos.py`, `diff_listing.py`, `fit_lines.py` and the vararg probes.
Output artefact: `gamedata/mii_customizer/P5-LUA-SOURCE/make_mii_special_actor.lc`,
sha256 `8e9b0ea06ea64756b598aedbc2064a65b5caf877f616f9e089c57802285598da`, 7799 bytes.

## Result

```
$ python mods/mii_customizer/tools/lua-src/build_check.py
original gamedata/.../make_mii_special_actor.lc  7799 bytes  sha256 ffa2bafa...b40d65d
compiled gamedata/.../P5-LUA-SOURCE/...lc        7799 bytes  sha256 8e9b0ea0...985598da
NOT byte-identical; per-prototype table follows
```

Byte diff over the whole 7799-byte file (B):

```
differing offsets: [40]      ->  exactly one byte, 0x28
original 0x28 = 0x02         mine 0x28 = 0x01
```

0x28 is `is_vararg` of the **main** prototype. Everything else - all 17
prototypes' instruction words, constant tables, upvalue descriptors, register
counts and line numbers - is identical.

### Per-prototype table

`main` and `main.p0`..`main.p15`; `o/m` is original/mine. Saved verbatim in
`evidence/P5-LUA-SOURCE/cmp_protos_output.txt`.

| proto | instr o/m | const o/m | 1st diff | upvalues | lines | maxstack |
|---|---|---|---|---|---|---|
| main | 56/56 | 24/24 | - | OK | 0/0,0/0 | 22/22 |
| main.p0 | 1/1 | 0/0 | - | OK | 41/41,42/42 | 2/2 |
| main.p1 | 13/13 | 4/4 | - | OK | 44/44,48/48 | 5/5 |
| main.p2 | 77/77 | 34/34 | - | OK | 53/53,90/90 | 13/13 |
| main.p3 | 23/23 | 9/9 | - | OK | 92/92,99/99 | 10/10 |
| main.p4 | 51/51 | 21/21 | - | OK | 101/101,118/118 | 10/10 |
| main.p5 | 5/5 | 2/2 | - | OK | 120/120,123/123 | 3/3 |
| main.p6 | 25/25 | 10/10 | - | OK | 125/125,135/135 | 5/5 |
| main.p7 | 13/13 | 5/5 | - | OK | 137/137,141/141 | 4/4 |
| main.p8 | 111/111 | 29/29 | - | OK | 143/143,190/190 | 7/7 |
| main.p9 | 47/47 | 18/18 | - | OK | 195/195,212/212 | 11/11 |
| main.p10 | 70/70 | 24/24 | - | OK | 214/214,236/236 | 11/11 |
| main.p11 | 29/29 | 13/13 | - | OK | 238/238,248/248 | 5/5 |
| main.p12 | 21/21 | 7/7 | - | OK | 250/250,258/258 | 4/4 |
| main.p13 | 26/26 | 9/9 | - | OK | 260/260,271/271 | 5/5 |
| main.p14 | 46/46 | 15/15 | - | OK | 276/276,296/296 | 8/8 |
| main.p15 | 180/180 | 52/52 | - | OK | 302/302,355/355 | 11/11 |

"1st diff -" means every instruction word matches. The only per-prototype
difference the tool reports is `main`'s `is_vararg`, covered below.

## The one byte stock Lua 5.3.6 cannot reproduce

This is the "anything in the original that stock luac 5.3.6 cannot reproduce"
section, and it is a genuine positive result rather than a failure to find the
right source.

**Smallest example that shows it** (`scratch/2026-10-05_P5-LUA-SOURCE/vararg/`):

```
$ printf 'local x = 1\n' > min.lua          # one line, one local
$ mods/mii_customizer/tools/luac53-game/bin/luac-game.exe -s -o min.lc min.lua
$ python mods/mii_customizer/tools/lua53-inspect/lua53_inspect.py protos min.lc
  proto main @0x1e .. 0x58
    ...
  main.is_vararg = 1
```

A one-line source cannot be smaller than that, and it already carries
`is_vararg = 1`. Six sources were compiled to confirm nothing reaches 2 (B):

| source | main `is_vararg` |
|---|---|
| empty file | 1 |
| `local x = 1` | 1 |
| `local x = ...` | 1 |
| `local function v(...) return ... end` + `return v(1)` | 1 |
| `print(...)` | 1 |
| `local t = {...}` | 1 |

**Why it is unreachable.** In the pinned source,
`tools/luac53-game/src/lua-5.3.6/src/lparser.c:1617`:

```c
static void mainfunc (LexState *ls, FuncState *fs) {
  ...
  fs->f->is_vararg = 1;  /* main function is always declared vararg */
```

That assignment is unconditional. `is_vararg` is a property of the *function*,
not of anything the source says, and the main chunk is always vararg. The
comment right above the function says so: "compiles the main function, which is
a regular vararg function with an upvalue named LUA_ENV". `ldump.c:174` writes
the byte straight through (`DumpByte(f->is_vararg, D)`) and `lundump.c:216`
reads it straight back (`f->is_vararg = LoadByte(S)`) with no validation, so
2 is a perfectly loadable value - the game's loader just never sees it from
this compiler.

**It is not specific to this chunk.** All three SSBU editor chunks have main
`is_vararg == 2` (B):

| chunk | main `is_vararg` |
|---|---|
| `make_mii_special_actor.lc` | 2 |
| `make_mii_edit_actor.lc` | 2 |
| `script_patch/.../make_mii_edit_actor.lc` | 2 |

No prototype inside `make_mii_special_actor.lc` has `is_vararg` set, so this is
a property of how the game's toolchain compiled its main chunks, not of the
script's content.

**What this means, carefully.** The original was produced by a compiler that
differs from stock 5.3.6 code generation in this single field. Reconstructing
the *source* is complete - the source is right, and it compiles to 7798 of 7799
identical bytes. Reaching byte identity needs either a one-line change to
`mainfunc()` in `luac53-game` or a post-pass that rewrites that single byte.
**Neither was done**: it is outside this task's scope, it changes a tool another
worker owns, and the task explicitly forbids fixing a difference by editing
bytes. Flagging it is the deliverable.

**Not established:** which toolchain the game actually used, whether the game's
loader cares about the value, and whether a chunk with `is_vararg = 1` would be
accepted. Those are tier D / untested.

Verification: `python mods/mii_customizer/evidence/P5-LUA-SOURCE/check_vararg_byte.py`
-> 22 checks, all ok, exit 0 (B).

## Construct list - things that took more than one attempt

Recorded as required. "compiled to" gives the wrong attempt's output.

1. **`X == true` / `X ~= true` instead of `not X`.** `if not g() then` compiles
   to `TEST 1 1`. The chunk has `EQ 0 1 -2` (compare against the `true`
   constant). Correct form: `if g() == true then` -> `EQ 0 1 K(true)`. Used in
   `main.p8` (four sites) and `main.p13`. Writing `not g() == true` looks
   equivalent but parses as `(not g()) == true` and compiled to
   `NOT 1 1; EQ 0 1 K(true)` - one instruction too many.

2. **`==` maps to `A=0`, `~=` maps to `A=1`** in Lua 5.3.6 comparisons, which is
   the opposite of the intuition from the operand order. In
   `lcode.c:codecomp`, `OPR_NE` uses `condjump(fs, OP_EQ, 0, ...)` and `==`/
   `<`/`<=` use `condjump(fs, OP_EQ, 1, ...)`, and the A field is the
   *negation* flag, not a register. My first reading of `LE 0 -25 2` in
   `main.p8` was `not (0 <= decided_id)`; the correct form is `if 0 <= decided_id then`.

3. **`local f = X` versus using `X` directly** changes the register the value
   lives in and hence every later instruction. `main.p8` has
   `GETUPVAL 1 2; GETTABLE 2 0 -5; SELF 2 2 -7; MOVE 4 1` - the `99` is loaded
   into R1 and then *moved* into the argument register. That only happens if the
   source assigns it to a local first:
   `selected_id = OK_BUTTON_ID; self.selector:select_button(selected_id)`.
   Passing `OK_BUTTON_ID` inline compiled to `GETUPVAL 4 2; CALL 2 3 1`.

4. **Same trap for `X` reused as a name in a chained call.** `main.p3` and
   `main.p4` and `main.p10` each need the `invoke(...)` result in a local
   (`local name = ...`) before the next statement uses it, otherwise the
   register is freed and reused.

5. **`a:b()` versus `a.b(a)`.** `GETTABLE` + `SELF` + extra `MOVE` + `CALL`
   versus `GETTABLE` + `MOVE` + `CALL`. `main.p6` needed
   `StateFunction:set(...)`, not `StateFunction.set(StateFunction, ...)`.

6. **`local selectable = true; if c then selectable = false end`** versus
   `local selectable = a ~= b`. The first compiles to
   `LOADBOOL; EQ; JMP; LOADBOOL`, the second to `EQ; JMP; LOADBOOL; LOADBOOL`.
   `main.p8` has the former shape.

7. **`if/else` versus two statements with an early `return`.** `main.p13`
   compiled to a `JMP 0 15` (to pc 26) after the first branch. Two independent
   `if`s and a `return` do not produce that jump; only
   `if c then ... else ... end` does.

8. **`elseif` versus a second `if`.** `main.p8` pc 50-54 is a `JMP 0 10`
   skipping the `elseif` arm. A separate `if` would not emit it.

9. **Line numbers are part of the format.** `linedefined` and
   `lastlinedefined` survive stripping, so every function had to start and end
   on its original line (41, 44, 53, 92, 101, 120, 125, 137, 143, 195, 214,
   238, 250, 260, 276, 302). `scratch/2026-10-05_P5-LUA-SOURCE/fit_lines.py`
   inserts blank lines to place them and refuses when a body does not fit its
   window - which forced several bodies to be written more compactly than I
   first wrote them.

10. **Trailing padding inside a body is free, a comment line is not.**
    Inserting blank lines before a function's `end` keeps `lastlinedefined`
    where it belongs; the same number of *comment* lines would too, but any
    inserted *statement* would change the bytecode.

11. **`local` declaration order fixes register numbers.** The four slot-id
    locals (`0,1,2,3`) and the two button-id locals (`99`, `1000`) are
    dead values as far as the bytecode is concerned - they exist only to shift
    the registers of the upvalues that follow. They had to be declared in
    exactly this order, after the eight state ids.

## Commands run

```bash
# input identification
sha256sum gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc
python mods/mii_customizer/tools/lua53-inspect/lua53_inspect.py header|protos|constants <chunk>

# compiler provenance
python mods/mii_customizer/tools/luac53-game/verify_sources.py

# per-prototype comparison (after every change)
python mods/mii_customizer/scratch/2026-10-05_P5-LUA-SOURCE/cmp_protos.py \
    gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc \
    gamedata/mii_customizer/P5-LUA-SOURCE/make_mii_special_actor.lc --verbose

# the check itself
python mods/mii_customizer/tools/lua-src/build_check.py
python mods/mii_customizer/evidence/P5-LUA-SOURCE/check_vararg_byte.py
```

## Observed checks

| check | result |
|---|---|
| `verify_sources.py` | 61/61 files identical to the official 5.3.6 release, exit 0 (B) |
| `cmp_protos.py` (full table) | 17/17 prototypes identical apart from main `is_vararg`; saved in `evidence/P5-LUA-SOURCE/cmp_protos_output.txt` (B) |
| `build_check.py` | exits 1, prints the table; length matches (7799/7799), sha256 differs (B) |
| `check_vararg_byte.py` | 22 checks, all ok, exit 0 (B) |
| six-source vararg probe | main `is_vararg` == 1 in every case (B) |
| `make_mii_edit_actor.lc`, `script_patch/.../make_mii_edit_actor.lc` | main `is_vararg` == 2 in both (B) |

`build_check.py` exits 1 by design: the check was not relaxed and the output
bytes were not edited.

## Limits and not-established

- **No runtime claim.** Nothing here was run in the game or an emulator. Byte
  equality says the source compiles to the shipped chunk; it does not say the
  game would accept a *modified* chunk, hash it, or behave differently.
- **The one-byte gap is a tool question, not a source question.** Whether to
  patch `mainfunc()` in `luac53-game`, or add a one-byte post-pass, or find the
  real game toolchain, is the coordinator's call - it touches a tool P4-LUAC
  owns.
- **Local names are invented.** A stripped chunk stores no names; the
  descriptive names here are mine.
- **Behaviour of native calls is out of scope.** The bytecode shows which names
  are passed to `UiScriptPlayer.invoke` and friends; it does not show what they
  do. Nothing in this report changes or questions the P2-UI-FLOW call-flow table
  except where noted inline above (rows read as bytecode, not as prose).
- **Not started, per the task:** the two `edit_actor` chunks. The `is_vararg`
  finding very likely applies to them too (both carry 2), which is why the
  reconstruction of `special_actor` was worth finishing first, but no source was
  written for them.

## Next experiment

The cheapest useful next step is one line: in a *copy* of
`tools/luac53-game/src/lua-5.3.6/src/lparser.c`, change `mainfunc()`'s
`fs->f->is_vararg = 1;` to `2`, rebuild `luac-game.exe` as a separate binary,
and rerun `build_check.py`. If it then reports `BYTE-IDENTICAL` with exit 0,
that closes this task exactly, and it tells us the game's toolchain differs
from stock 5.3.6 in this field and nothing else that matters for these chunks.
That change is the coordinator's to authorise because it modifies a tool another
worker owns; it was deliberately not done here.

The second question worth a console run, if the UI track ever needs it: whether
the game accepts a chunk whose main `is_vararg` is 1. That is a runtime
question and nothing offline can settle it.

## Changed files

- `tools/lua-src/make_mii_special_actor.lua` (new)
- `tools/lua-src/build_check.py` (new)
- `tools/lua-src/README.md` (new)
- `evidence/P5-LUA-SOURCE/check_vararg_byte.py` (new)
- `evidence/P5-LUA-SOURCE/original.listing.txt` (new, regenerated listing)
- `evidence/P5-LUA-SOURCE/cmp_protos_output.txt` (new, saved tool output)
- `scratch/2026-10-05_P5-LUA-SOURCE/` (new: `cmp_protos.py`, `diff_listing.py`, `fit_lines.py`, `vararg/` probes)
- `gamedata/mii_customizer/P5-LUA-SOURCE/make_mii_special_actor.lc` (new build artefact, comparison only)
- `research/P5-LUA-SOURCE.md` (this report)

Not touched: `STATUS.md`, `CURRENT_INSTALL.md`, `CHANGELOG.md`, prompts, any other
worker's files, the input chunk, `builds/`, and the two `edit_actor` chunks.