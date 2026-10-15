# luac53-game - a local Lua 5.3.6 `lua` + `luac` that speaks the game's chunk format

Builds the official Lua 5.3.6 sources into `bin/` **configured so that its
compiled chunks carry the same 29-byte header as the SSBU UI scripts** (Lua
5.3, little-endian, `sizeof lua_Number = 4`). It also proves, offline, that
this `luac`/`lua` can **read the game's own chunks**.

Purpose: the Mii editor chunks are stripped Lua 5.3 bytecode. Hand-editing
bytecode does not scale, so new editor logic should be written as Lua source
and compiled here. This tool is only the compiler; it contains no mod logic
and produces no chunk meant for the game.

Everything is project-local. Nothing is installed system-wide, no game file is
touched, and all binaries and object files are written under `bin/` only.

## Build

```bash
# from the workspace root (or anywhere - the script resolves its own directory)
bash mods/mii_customizer/tools/luac53-game/build.sh          # game build + 2 controls
bash mods/mii_customizer/tools/luac53-game/build.sh game     # just the game build
CC=gcc bash mods/mii_customizer/tools/luac53-game/build.sh   # different compiler
```

`build.sh` needs `clang` (or `gcc`) on PATH - llvm-mingw 20260616 already
provides both - and bash. It does **not** need `make` (see *Machine facts*).

Outputs in `bin/`:

| file | configuration | role |
|---|---|---|
| `luac-game.exe`, `lua-game.exe` | `-DLUA_FLOAT_TYPE=LUA_FLOAT_FLOAT` | the deliverable |
| `luac-control-double.exe`, `lua-control-double.exe` | stock (8-byte doubles) | negative control |
| `luac-control-32bit.exe`, `lua-control-32bit.exe` | `--target=i686-w64-mingw32` | negative control |
| `build-info.txt` | - | compiler version, flags, exact commands, binary hashes |
| `obj/` | - | intermediate objects (kept inside `bin/`) |

## Configuration

The three game chunks agree on every header field:

| header field | game chunks | this build | where it comes from |
|---|---|---|---|
| version / format | 0x53 / 0 | 0x53 / 0 | `lundump.c` defaults |
| `LUAC_INT` | 0x5678 | 0x5678 | `lundump.c` `LUAC_INT` |
| `LUAC_NUM` | 370.5 | 370.5 | `lundump.c` `LUAC_NUM` |
| `sizeof int` | 4 | 4 | x86_64 ABI |
| `sizeof size_t` | 8 | 8 | x86_64 ABI |
| `sizeof Instruction` | 4 | 4 | `unsigned int` in `lopcodes.h` |
| `sizeof lua_Integer` | 8 | 8 | default `LUA_INT_LONGLONG`, `luaconf.h:142-144`, `:558-560` |
| `sizeof lua_Number` | **4** | **4** | `-DLUA_FLOAT_TYPE=LUA_FLOAT_FLOAT`, `luaconf.h:146-148`, `:455-464` |
| header size | 29 bytes, main nupvalue at 0x1d | same | `ldump.c` `DumpHeader` |

Only `lua_Number` needs a non-default setting, so it is passed as a compiler
define and `src/` stays byte-identical to the upstream tarball (checked by
`verify_sources.py`). No patch file is needed.

## Usage

```bash
L=mods/mii_customizer/tools/luac53-game/bin

"$L/luac-game.exe" -s -o out.lc my_editor_source.lua   # compile, stripped (as the game chunks are)
"$L/lua-game.exe"  out.lc                             # run it locally
"$L/luac-game.exe" -p -l -l out.lc                     # list a chunk (see note)
"$L/luac-game.exe" -p -l -l <game chunk>               # reads the game's own chunks

# every check of the P4-LUAC prompt, with exit codes
python mods/mii_customizer/tools/luac53-game/check_luac53_game.py

# prove src/ is the official Lua 5.3.6 (add --fetch-tag to download the pinned git tag)
python mods/mii_customizer/tools/luac53-game/verify_sources.py --fetch-tag
```

`check_luac53_game.py` prints one line per check with its exit code, writes
`evidence/P4-LUAC/CHECK_SUMMARY.txt`, `evidence/P4-LUAC/check_run_output.txt`
and the `luac -l -l` listings of the three game chunks under
`evidence/P4-LUAC/listings/`, and exits 0 only if every check passed. It never
writes outside the mod, and it reads the game chunks only.

`testsrc/test_header.lua` and `testsrc/test_editor_constructs.lua` are the two
compiler test sources (no mod logic).

## Sources

| item | value |
|---|---|
| URL | `https://www.lua.org/ftp/lua-5.3.6.tar.gz` (primary upstream) |
| size | 303770 bytes |
| sha256 | `fc5fd69bb8736323f026672b1b7235da613d7177e72558893a0bdcd320466d60` |
| md5 | `83f23dbd5230140a3770d5f54076948d` |
| unpacked to | `src/lua-5.3.6/` (unmodified) |
| upstream checksum | **none published** - `lua-5.3.6.tar.gz.sha256` and `.md5` both return HTTP 404 (checked 2026-10-05) |

Because upstream publishes no checksum, authenticity is established a second,
stronger way: every C source and header of the unpacked tree is byte-identical
to the official repository at tag **v5.3.6**
(`https://codeload.github.com/lua/lua/tar.gz/refs/tags/v5.3.6`, sha256
`5bcfaee2664e62c7ba5fecdd0e3497964b1bd4fdba63b366902e4bcb8ebd200a`) - 59/59
identical, plus 61/61 against the release tarball itself. Re-runnable with
`verify_sources.py`.

## Status

Working. Rebuilt from scratch on 2026-10-05 with clang 22.1.8
(llvm-mingw 20260616, target x86_64-w64-windows-gnu); 26 s for all three
variants. `check_luac53_game.py`: 9 checks, 0 failures, exit 0.

Verified (tier B, offline):

- a compiled test source's first 30 header bytes are identical to all three
  game chunks;
- the built `luac -l -l` loads and lists all three game chunks (exit 0), and
  per-prototype instruction and constant counts agree with lua53-inspect's
  `summary` for all 53 prototypes (18 + 17 + 18);
- the built `lua` runs the compiled chunk and shows float32 behaviour;
- lua53-inspect `verify` and `roundtrip` accept the compiled chunks;
- compiling the same source twice gives identical bytes.

## Limits - what this does **not** show

- **The game has never loaded a chunk from this compiler.** The only console
  evidence is `evidence/2026-10-04_gate1/RESULT_test2.md`, where the game
  loaded an *edited original* chunk. A byte-identical header is necessary, not
  sufficient: the loader may check more, or the ARC/mod loader may do
  something else entirely.
- **No source reproduces an original chunk.** Nothing here claims that
  `test_header.lua` or any other source corresponds to a game script; matching
  a header says nothing about matching code.
- **Header equality is not code equality.** The compiler is stock 5.3.6. If
  the game's build differs in codegen (or was built with different `-O` or a
  patched compiler), chunks from this build may still differ in code.
- Built for Windows x86_64. The chunk header only depends on the ABI sizes
  (`int` 4, `size_t` 8, `Instruction` 4, `lua_Integer` 8, `lua_Number` 4) and
  endianness, all of which the Switch's AArch64 build shares - but that is a
  **hypothesis (D)**, not measured here: no aarch64 build of this tool was run.
- Windows binaries only; no POSIX build. `bin/` contents are not committed
  anywhere.
- The `luac -l -l` listings in `evidence/P4-LUAC/listings/` contain heap
  pointers printed by `luac.c` `PrintHeader`, so those addresses differ between
  runs. Everything else in them is stable.
- **`luac -l -l file` also writes `luac.out`** into the current directory:
  `luac.c` `pmain` prints the listing and then dumps unless `-p` ("parse only")
  is given. Every listing command here therefore passes `-p`; without it a
  check run scatters `luac.out` files wherever it was started.
- No `readline` support in `lua`; interactive editing is plain stdin.

## Machine facts (new, for the kb)

- `make` is **not** on PATH on this machine; `mingw32-make` is, next to clang in
  the llvm-mingw bin directory. Builds that assume `make` fail.
- lua.org publishes no per-file checksums for release tarballs (404 on
  `.sha256` and `.md5`); upstream verification needs the pinned GitHub tag.