# P5-LUA-SOURCE - reconstruct Lua source that compiles to the original special-move screen chunk

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

Background. tools/luac53-game/ builds a Lua 5.3.6 compiler whose output has the
game's chunk format (research/P4-LUAC.md). The game loads an edited copy of
ui/script/menu/chara_make/make_mii_special_actor.lc (console, tier A). To change
that screen's behaviour we want its logic as Lua source.

One goal: a Lua source file which, compiled with
`tools/luac53-game/bin/luac-game.exe -s`, gives a chunk BYTE-IDENTICAL to the
original make_mii_special_actor.lc (workspace-relative
gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc,
7799 bytes, sha256
ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d). The success
test is mechanical; there is nothing to argue about. Do not change any behaviour
and do not produce a chunk meant for the game.

Material you may use: the original chunk; `luac-game -l -l` listings
(evidence/P4-LUAC/listings/); tools/lua53-inspect (dis, constants, protos,
compare); research/P2-UI-FLOW.md (its call-flow table was corrected by the
coordinator in rows 21 and 32; treat it as a guide, the bytecode is the authority).
No decompiler downloads; write the source by reading the bytecode.

Method.
1. Work prototype by prototype (17 prototypes: main and main.p0..p15). Write the
   function, compile the whole file, and compare with lua53-inspect `compare` and a
   per-prototype diff of instruction words and constant tables. Build one script
   scratch/.../cmp_protos.py that prints, for every prototype: instruction count
   original/yours, constant count original/yours, first differing pc, and
   upvalue descriptor equality. Use it after every change.
2. Things that decide byte identity and are easy to get wrong: order in which
   locals are declared (register numbers), order of first use of constants
   (constant table order), `local function` versus `local f = function`, upvalue
   order (order of first capture), method call `a:b()` versus `a.b(a)`, numeric for
   versus while, `not`/comparison operand order, integer versus float literals
   (`1` vs `1.0`), `linedefined`/`lastlinedefined` of every function (they are
   stored even in stripped chunks, so each function must start and end on the same
   LINE NUMBERS as the original: read them with lua53-inspect `protos` and place
   the code on those lines; blank lines are free).
3. Record every construct you had to try more than once, with what the wrong
   attempt compiled to. That list is part of the deliverable.

Deliverables.
- tools/lua-src/make_mii_special_actor.lua : the reconstructed source. It contains
  only what the bytecode implies; names of locals are your choice (they are not
  stored), but choose descriptive ones and add a short comment per function saying
  which prototype it is (main.pN) and what it does in plain words.
- tools/lua-src/build_check.py : compiles the source to workspace-relative
  gamedata/mii_customizer/P5-LUA-SOURCE/make_mii_special_actor.lc and exits 0 only
  if the result is byte-identical to the original (compare sha256 and length);
  otherwise prints the per-prototype table from step 1 and exits 1.
- tools/lua-src/README.md : purpose, how to run the check, status, limits.
- research/P5-LUA-SOURCE.md : result, the per-prototype table, the list from
  step 3, and anything in the original that stock luac 5.3.6 cannot reproduce.

Stop conditions. DONE = byte-identical. If after honest effort some prototypes
still differ, stop PARTIAL and report exactly which prototypes are identical and,
for each remaining one, the first differing instruction with both decodings. Do
not "fix" a difference by editing bytes, and do not relax the check. If you find
evidence that the original was produced by a compiler that differs from stock
5.3.6 code generation (same source cannot produce these bytes), say so with the
smallest example you can construct; that is a valuable result.

Do not: start on the two edit_actor chunks, add features, rename game strings,
or copy the compiled chunk into builds/.

Exclusive writes: tools/lua-src/, research/P5-LUA-SOURCE.md,
evidence/P5-LUA-SOURCE/, scratch/2026-10-05_P5-LUA-SOURCE/, workspace-relative
gamedata/mii_customizer/P5-LUA-SOURCE/.
