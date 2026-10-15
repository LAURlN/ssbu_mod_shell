# P4-LUAC - build a local Lua 5.3.6 compiler that produces the game's chunk format

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md. Work only on the task below. No agents,
commits, branches, emulator, SD access, framework changes or edits to other workers'
files. Inputs remain read-only. Report exact inputs/hashes, commands, observed
checks, failures and limits. B is offline observation, C pinned source, D
hypothesis; no runtime behavior claims. Coordinator owns
STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report and chat with task
ID, DONE/PARTIAL/BLOCKED, changed files and next experiment. All paths below are
relative to mods/mii_customizer/ unless marked workspace-relative. Create every
folder INSIDE mods/mii_customizer/ and make scripts write there, never into the
current directory. Use `python`, not `python3`.

Background. The game's UI scripts are stripped Lua 5.3 chunks with 4-byte floats
and 8-byte integers (tools/lua53-inspect/README.md, "Notes on this format"). The
console test showed the game loads an edited chunk
(evidence/2026-10-04_gate1/RESULT_test2.md). Editing bytecode by hand does not
scale. If we can compile Lua source into this exact format, new editor logic can be
written as source.

One goal: a project-local `luac` (and `lua`) built from the official Lua 5.3.6
sources, configured so its output has the same header as the game's chunks, plus
proof that it reads the game's chunks. Tool task. Do not write any mod logic and
do not produce a chunk meant for the game.

Steps.
1. Source. Download the official lua-5.3.6 source archive from lua.org (primary
   upstream; this is tool source, not game content). Record URL, size and sha256,
   and compare the sha256 with the checksum lua.org publishes for that file; stop
   BLOCKED if they differ. Unpack under tools/luac53-game/src/ unmodified. Nothing
   is installed system-wide.
2. Configuration. From the three game chunks' headers (use lua53_inspect.py
   `header`; inputs under workspace-relative gamedata/mii_customizer/P1-UI/ui/,
   listed in the lua53-inspect README) list every header field: sizes of int,
   size_t, Instruction, lua_Integer, lua_Number, and LUAC_INT / LUAC_NUM. Derive
   the luaconf settings that reproduce them and apply them through compiler
   defines or one documented patch file kept next to the sources (show the diff).
   Cite the luaconf.h lines you rely on.
3. Build with the compiler already on this machine (`clang`/`gcc` from llvm-mingw
   on PATH; do not install anything). One build script,
   tools/luac53-game/build.sh, output in tools/luac53-game/bin/. Record compiler
   version and exact commands.
4. Checks, each with exit code, collected in one script
   tools/luac53-game/check_luac53_game.py:
   a) compile a small test source with `luac -s`; its first header bytes (up to
      the main function's upvalue-count byte) must be byte-identical to the same
      bytes of each of the three game chunks;
   b) lua53-inspect `verify` and `roundtrip` accept the compiled test chunk;
   c) `luac -l -l` on each of the three ORIGINAL game chunks must load and list
      them without error; save the listings to evidence. Compare, per prototype,
      the instruction count and constant count of the listing with lua53-inspect's
      `summary`; they must agree for every prototype;
   d) the built `lua` runs the compiled test chunk and prints the expected output;
      a float value printed by the test shows 4-byte float behaviour (state what
      you printed and why it distinguishes float from double);
   e) negative control: a luac built with default (double) numbers, or the test
      chunk with one header byte changed, is rejected by the format check in (a)
      or by the game-format `lua`; show that the check fails when it should;
   f) determinism: compiling the same source twice gives identical bytes.
5. A second, slightly larger test source that uses the constructs the editor
   chunks use (local functions and upvalues, tables with string keys, numeric for
   loops, method calls with `:`, string.format, integer and float constants,
   comparison chains). Compile it, then show with lua53-inspect that opcodes and
   constant tags fall inside the set that occurs in the game chunks (list any
   opcode or tag that the game chunks never use).

Deliver tools/luac53-game/README.md (purpose, build, usage, status, limits),
research/P4-LUAC.md, and a kb suggestion for the coordinator if a machine fact is
new. State plainly what is not shown: that the game accepts a chunk produced by
this compiler (only an edited original has been loaded so far), and that a given
source reproduces an original chunk.

Do not: decompile or reconstruct game scripts, edit lua53-inspect, write into
gamedata except workspace-relative gamedata/mii_customizer/P4-LUAC/ for listings of
game chunks if you prefer to keep them out of evidence, or add binaries anywhere
but tools/luac53-game/bin/.

Exclusive writes: tools/luac53-game/, research/P4-LUAC.md, evidence/P4-LUAC/,
scratch/2026-10-04_P4-LUAC/, workspace-relative gamedata/mii_customizer/P4-LUAC/.
