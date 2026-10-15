# P4-LUAC - a local Lua 5.3.6 compiler for the game's chunk format

**Task:** P4-LUAC (Space Bunny Alpha). **Status: DONE** (with one documented
deviation in step 1, below). Date: 2026-10-05. All paths are relative to the
workspace root unless marked mod-relative. Tier B throughout: offline
observation of bytes and of a locally built program. No runtime claim.

**Result in one line:** `tools/luac53-game/` builds the official Lua 5.3.6
sources into a `lua` + `luac` whose compiled chunks carry a **byte-identical
30-byte header prefix** to the game's UI chunks, and whose `luac -l -l`
**loads and lists all three original game chunks** with per-prototype
instruction and constant counts that agree with lua53-inspect for all 53
prototypes. 9 checks, 0 failures, exit 0.

**Not shown (the two things that matter most):**

1. **The game has never loaded a chunk from this compiler.** The only tier A
   evidence is `mods/mii_customizer/evidence/2026-10-04_gate1/RESULT_test2.md`,
   where the game loaded an *edited original* chunk. A matching header is
   necessary, not sufficient.
2. **No source reproduces an original chunk.** Nothing here claims that any
   test source corresponds to a game script. Header equality is not code
   equality, and the compiler here is stock 5.3.6: if the game's build differs
   in codegen, chunks from this build may still differ in code.

---

## Inputs (read-only, unchanged)

| path | sha256 |
|---|---|
| `gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_edit_actor.lc` | `1f73dff133961b68dbe24641298229b9f3905a44703164563911b105eaa16908` |
| `gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc` | `ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d` |
| `gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc` | `c777ecc492cea48f6ffd40112b22f96e66219d00969b570a7cc3cf8d7f4a9417` |

The second hash matches the one the coordinator already verified in
`research/COORDINATOR-2026-10-04.md`.

## Step 1 - source

| item | value |
|---|---|
| URL | `https://www.lua.org/ftp/lua-5.3.6.tar.gz` |
| size | 303770 bytes |
| sha256 | `fc5fd69bb8736323f026672b1b7235da613d7177e72558893a0bdcd320466d60` |
| md5 | `83f23dbd5230140a3770d5f54076948d` |
| unpacked to | `mods/mii_customizer/tools/luac53-game/src/lua-5.3.6/` (unmodified) |
| cross-check | `https://codeload.github.com/lua/lua/tar.gz/refs/tags/v5.3.6`, 369921 bytes, sha256 `5bcfaee2664e62c7ba5fecdd0e3497964b1bd4fdba63b366902e4bcb8ebd200a` |

**Deviation, stated plainly: lua.org publishes no checksum for that file.**
`https://www.lua.org/ftp/lua-5.3.6.tar.gz.sha256` and
`.../lua-5.3.6.tar.gz.md5` both returned **HTTP 404** from lua.org's nginx on
2026-10-05, and the FTP index (`https://www.lua.org/ftp/`) lists the tarballs
without any checksum file. Homebrew-core, the luarocks manifest and
nixpkgs 21.08 were checked and no longer carry a 5.3.6 entry. So the prompt's
"compare with the checksum lua.org publishes" cannot be performed literally -
there is nothing to compare against, and the BLOCKED condition ("if they
differ") therefore cannot arise. Instead of stopping, the download is verified
a second way that is **stronger**: every C source and header of the unpacked
tree is byte-identical to the official repository at the pinned tag **v5.3.6**.

```
python mods/mii_customizer/tools/luac53-game/verify_sources.py --fetch-tag   # exit 0
release tarball vs unpacked src/: 61 files compared, 61 identical, 0 different
official git tag v5.3.6 vs unpacked src/: 59 files compared, 59 identical, 0 different
```

Saved as `evidence/P4-LUAC/SOURCE_VERIFICATION.txt`. (The two non-compared sets
are the release tarball's generated `Makefile`/`lua.hpp`/`luac.c` and the git
tag's test files; the 59 + 61 files are every `.c` and `.h`.) The coordinator
may prefer a stricter gate before any console use; the tool script makes that
re-checkable.

## Step 2 - header fields and the derived configuration

Measured with `lua53-inspect header` on all three chunks
(`evidence/P4-LUAC/game_chunk_headers.txt`, exit 0). All three agree:

| header field | value | offset | source of the setting |
|---|---|---|---|
| signature `1bLua` + `LUAC_DATA` | as stock | 0x00-0x09 | `ldump.c:184 DumpHeader` |
| version / format | 0x53 / 0 | 0x0a-0x0b | `lundump.c:245-249` |
| `sizeof int` | 4 | 0x0c | x86_64 ABI |
| `sizeof size_t` | 8 | 0x0d | x86_64 ABI |
| `sizeof Instruction` | 4 | 0x0e | `unsigned int` (`lopcodes.h`) |
| `sizeof lua_Integer` | 8 | 0x0f | default `LUA_INT_LONGLONG`: `luaconf.h:142-144`, `luaconf.h:558-564` |
| `sizeof lua_Number` | **4** | 0x10 | **`-DLUA_FLOAT_TYPE=LUA_FLOAT_FLOAT`**: default is `LUA_FLOAT_DOUBLE` (`luaconf.h:146-148`), the float branch sets `LUA_NUMBER float` (`luaconf.h:455-457`) |
| `LUAC_INT` | 0x5678 | 0x11-0x18 | `lundump.c` constant |
| `LUAC_NUM` | 370.5 | 0x19-0x1c | `lundump.c` constant, read as float32 |
| main closure nupvalues | 1 | 0x1d | `lundump.c:277 LoadByte` |

Header length 29 bytes, first prototype at 0x1e - identical to the three game
chunks. Only `lua_Number` differs from a stock 64-bit build, so the
configuration is a **single compiler define** and `src/` needs no patch:

```
-DLUA_FLOAT_TYPE=LUA_FLOAT_FLOAT
```

Consequence worth knowing for later work: with a float build
`LUA_NUMBER_FMT` is `"%.7g"` (`luaconf.h:464`), so `print(0.3333...)` and any
float `tostring` in the game produce 7 significant digits, and
`LUAI_UACNUMBER` stays `double` (`luaconf.h:461`) so printed numbers are
computed in double from float32 inputs.

## Step 3 - build

Compiler already on this machine, nothing installed:
`clang version 22.1.8`, target `x86_64-w64-windows-gnu` (llvm-mingw
20260616-ucrt-x86_64), linker `ld.lld`.

```
bash mods/mii_customizer/tools/luac53-game/build.sh        # exit 0, ~26 s
```

Flags: `-O2 -Wall -Wextra -std=gnu99 -DLUA_COMPAT_5_2` (the upstream Makefile
defaults, `src/lua-5.3.6/src/Makefile:10-14`) plus the variant defines. One
`clang -c` per file, then one link per program; `bin/build-info.txt` records
the compiler version, the flags, the exact command shape and the hashes of
every binary. Binaries and object files go to `bin/` and `bin/obj/` only.

Built variants: `game` (the deliverable), `control-double` (stock config) and
`control-32bit` (`--target=i686-w64-mingw32`). Only one upstream warning is
emitted (`lundump.c:244`, `LUA_SIGNATURE + 1` string arithmetic) - it is
upstream code and was left alone.

Two build failures were hit and fixed while writing the script, both in my
script rather than in Lua: linking `lua` from an object directory that also
held `luac.o` gave `duplicate symbol: main`, and the first library list
omitted `linit.c`, giving `undefined symbol: luaL_openlibs`.

One upstream behaviour worth knowing: **`luac -l -l file` also writes
`luac.out`** into the current directory - `luac.c` `pmain` prints the listing
and then dumps unless `-p` ("parse only") is given. Two `luac.out` files were
created outside the tool directory before this was noticed (one in the mod
root, one in `tools/luac53-game/`); both were deleted, every listing command
now passes `-p`, and no `luac.out` is produced by a check run any more.

## Step 4 - checks

`python mods/mii_customizer/tools/luac53-game/check_luac53_game.py` -> **exit 0,
9 checks, 0 failures**. Full output: `evidence/P4-LUAC/check_run_output.txt`;
summary: `evidence/P4-LUAC/CHECK_SUMMARY.txt`.

| id | check | exit | observed |
|---|---|---|---|
| a | compiled header identical to all three game chunks | 0 | 30 bytes `1b4c7561530019930d0a1a0a 04 08 04 08 04 78 5600000000000000 00 40 b943 01` - identical to all three, zero differing offsets |
| b | `lua53-inspect verify` + `roundtrip` on the compiled chunk | 0 | both exit 0; full-consumption 0x103/0x103 |
| c | `luac -p -l -l` on the three original chunks | 0 | 18/17/18 prototypes, 1181/794/1222 instructions and 333/276/338 constants, **listing and inspector agree per prototype** (53/53) |
| d | built `lua` runs the chunk, float32 visible | 0 | see below |
| e | negative controls | 0 | E1-E5 all rejected, see below |
| f | determinism | 0 | same source compiled twice -> identical sha256, twice over |
| 5 | editor-construct source vs the game opcode/tag sets | 0 | no constant tag outside the game set; 3 opcodes outside (listed) |
| g | `luac -s` gives the same stripped debug shape | 0 | every prototype of both compiled chunks has a NULL source and empty debug tables, like all 53 game prototypes |
| b2 | `lua53-inspect verify` on both compiled chunks | 0 | 11 structural checks pass on each |

**(d) what the test prints and why it separates float32 from double.**
Expected values are derived in Python with `struct` (float32 semantics), not
copied from a run:

```
3                          integer arithmetic, lua_Integer subtype
integer                    the chunk has an integer type
9223372036854775807        math.maxinteger: 2^63-1, so lua_Integer is 8 bytes
0.10000000149011612        %.17g of float32(0.1) widened to double
true                       0.1+0.2 == 0.3, true in float32, FALSE in double
0.3333333                  float32 division printed with LUA_NUMBER_FMT %.7g
```

The discriminating lines are `0.10000000149011612` and `true`. The same
source compiled by the stock **double** control build and run with the double
control `lua` prints `0.10000000000000001` and `false` - observed, not
assumed. One correction made during the task: `math.type(0.1)` was originally
used as the width check and **does not discriminate** (decimal literals are
of float *subtype* in Lua 5.3 whatever the build), so it was replaced by
`math.maxinteger`.

**(e) negative controls, all rejected as they should be:**

| id | input | expected | observed |
|---|---|---|---|
| E1 | same source, stock double `luac` | header differs | `sizeof lua_Number` byte 0x10 = 8, and `LUAC_NUM` region differs - differs from the game header |
| E2 | `--target=i686-w64-mingw32`, float define | header differs | `sizeof size_t` byte 0x0d = 4 - one byte off the game header |
| E3 | our chunk with byte 0x10 changed 4 -> 8 | inspector rejects | `verify` exit 1, `PARSE ERROR: float format mismatch: LUAC_NUM 2.68e-314 at offset 0x11 != 370.5` |
| E4 | game-format `lua` on that mutated chunk | rejects | exit 1, `lua_Number size mismatch in precompiled chunk` (`lundump.c:235-238 fchecksize`) |
| E5 | game-format `lua` on the double-built chunk | rejects | exit 1, same message |

The control that makes E1-E5 meaningful: the **same** `lua` accepts the three
game chunks (check c), so the rejection is about the header, not about the
file being a precompiled chunk.

**(c) listings** are saved to `evidence/P4-LUAC/listings/*.luac-l-l.txt`. They
contain heap addresses printed by `luac.c` `PrintHeader` ("at 0000..."), so
those addresses differ between runs; everything else is stable. The listing
command is `luac -p -l -l`; see the `luac.out` note in step 3.

## Step 5 - editor-construct source

`tools/luac53-game/testsrc/test_editor_constructs.lua` (local functions and
upvalues, tables with string keys, numeric `for`, method calls with `:`,
`string.format`, integer and float constants, comparison chains, `table.concat`).
Compiled: 1265 bytes, sha256
`7e3bbd0792306db4364ef30603dba9c32016d277339d4ea0c3526ec8246767c8`, 7
prototypes, 147 instructions, `verify` clean.

Measured with lua53-inspect:

- **Constant tags: the test uses {0 nil, 1 boolean, 3 float, 4 integer, 19
  string} - exactly the set the three game chunks use, no more.** The game
  chunks contain no other constant type, so this compiler cannot emit one here.
- **Opcodes the test uses that NO game chunk uses (3):**
  `SETUPVAL` (the `n = n + ...` write to a captured upvalue in `makeCounter`),
  `LEN` (the `#CONFIG.label` operator), `TESTSET` (the `elseif` chain).
  All three are forced by the constructs the prompt asked for; they are
  ordinary 5.3 opcodes and the game's own loader knows them, but no editor
  chunk happens to contain them. Listed in the check output so a later author
  knows the difference.
- For reference, the 22 opcodes **no** game chunk uses: `LOADKX SETUPVAL MUL
  MOD POW DIV IDIV BAND BOR BXOR SHL SHR UNM BNOT NOT LEN CONCAT TESTSET
  TFORCALL TFORLOOP VARARG EXTRAARG`. The game chunks use 25 of 47.

**The checker itself was verified to fail.** A green run only means something
if a wrong input turns it red, so the double-built `luac` was temporarily put
in place of `luac-game.exe` and the script was re-run: **exit 1, 4 of 9 checks
failed** (a, c, e and the determinism/`verify` pair), exactly where the format
should have been caught. Output kept at
`scratch/2026-10-04_P4-LUAC/failpath-run.txt`. The real binary was restored and
the whole build plus all checks were re-run afterwards: exit 0, 9/9 pass, and
that run is the one saved in `evidence/P4-LUAC/`.

## Files

Created (all inside the exclusive write paths):

- `mods/mii_customizer/tools/luac53-game/build.sh` - the only build script
- `mods/mii_customizer/tools/luac53-game/check_luac53_game.py` - all checks
- `mods/mii_customizer/tools/luac53-game/verify_sources.py` - source authenticity
- `mods/mii_customizer/tools/luac53-game/README.md` - purpose, build, usage, status, limits
- `mods/mii_customizer/tools/luac53-game/testsrc/test_header.lua`, `test_editor_constructs.lua`
- `mods/mii_customizer/tools/luac53-game/src/lua-5.3.6/` (unpacked upstream), `dl/`
- `mods/mii_customizer/tools/luac53-game/bin/` - `luac-game.exe`, `lua-game.exe`, two controls, `build-info.txt`, `obj/`
- `mods/mii_customizer/evidence/P4-LUAC/` - `CHECK_SUMMARY.txt`, `check_run_output.txt`, `SOURCE_VERIFICATION.txt`, `game_chunk_headers.txt`, `listings/`
- `mods/mii_customizer/scratch/2026-10-04_P4-LUAC/` - compiled test chunks, tag tarball
- `mods/mii_customizer/research/P4-LUAC.md` - this file

Nothing outside those paths was written. `tools/lua53-inspect/` is untouched
(imported read-only). No binary exists outside `tools/luac53-game/bin/`. No
`gamedata/` write was needed - the listings went to `evidence/`.

## Limits

- See the two bold statements at the top: no game acceptance, no
  source-to-original reproduction.
- Windows x86_64 binaries only. The header depends only on ABI sizes and
  endianness, which the Switch AArch64 build shares (int 4, size_t 8,
  Instruction 4, lua_Integer 8, lua_Number 4 - **D**, not measured: no aarch64
  build of this tool was run or executed).
- Nothing about how the game *finds* or loads a chunk is shown: ARC entry
  names, `.lc` vs source expectations and mod-loader behaviour are outside this
  task. Check (c) proves this `luac` can read a chunk file, not that the game
  would.
- The build embeds paths/timestamps, so the **binaries** are not bit-identical
  between builds (two builds gave different `.exe` hashes). Chunk output *is*
  deterministic (check f).
- Codegen is stock 5.3.6. Whether the game's own chunks came from this exact
  compiler configuration (same Lua version, same codegen) is unknown; only the
  header is demonstrated to match.

## kb suggestion for the coordinator (not written to kb/ by this task)

Two machine facts are new and belong in `kb/reference/local-machine.md`
(coordinator edits; no agent-owned kb file was touched here):

1. **There is no `make` on PATH; `mingw32-make` is**, next to `clang` in the
   llvm-mingw 20260616-ucrt-x86_64 bin directory. Anything that assumes `make`
   fails on this machine, and `gmake` does not exist either. clang 22.1.8
   (target `x86_64-w64-windows-gnu`, `ld.lld`) builds and runs C/C++ natively,
   including `-target=i686-w64-mingw32` 32-bit binaries.
2. **lua.org publishes no checksums for its release tarballs**:
   `.../lua-5.3.6.tar.gz.sha256` and `.md5` both 404, and the FTP index has no
   checksum files. Verifying a Lua release therefore means diffing against the
   pinned GitHub tag (`codeload.github.com/lua/lua/tar.gz/refs/tags/v5.3.6`),
   which is what `tools/luac53-game/verify_sources.py` does.

## Next experiment

Offline, cheap and directly useful for the coordinator's "write editor Lua as
source" plan: **take the header-identical compiled chunk and check it against
the two facts gate 1 established** - that the game accepts an *edited original*
chunk, and that it loads scripts from ARCropolis mod folders. Concretely,
before any console test, extend `check_luac53_game.py` with a *structural
compatibility* probe: load `make_mii_special_actor.lc`, `luac -l -l` it, and
diff our compiler's `luac -l -l` output shape (prototype ordering, upvalue
shape of the main closure, `CALL`/`GETTABUP` patterns against `_ENV`) against
the real thing, so a source file written for the editor is known to use the
same calling shape the chunks use.

The first console experiment, when the coordinator wants one, is the only thing
that can close the main gap: replace one editor chunk with a `luac -s` chunk
compiled from a source file that reproduces the original's *visible* behaviour
plus one harmless extra (the same sub-title probe as P3-ARC-PROBES, which is
known to be visible if the chunk loads), keeping the file length irrelevant -
because a compiled chunk has a different length than the original, this also
tests the untested "different-length file" case from `RESULT_test2.md`.