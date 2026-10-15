# P9-EDIT-SOURCE - reconstruct make_mii_edit_actor.lua, then stage one probe

Worker: Space Bunny Alpha. Date 2026-10-05.
Result: **DONE** - all 18 prototypes byte-identical after a one-byte `is_vararg`
post-pass, and one probe package staged. **Nothing was run.** See
[Limits](#limits) before using any of this.

Evidence tier: **B** throughout. Every claim is offline measurement of bytes and
of the parsed chunk. No console run, no emulator run, no claim about runtime
behaviour.

## Inputs

| path | sha256 / size |
|---|---|
| `gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc` | `c777ecc492cea48f6ffd40112b22f96e66219d00969b570a7cc3cf8d7f4a9417`, 10576 bytes (read-only, unmodified) |
| `mods/mii_customizer/tools/luac53-game/bin/luac-game.exe` | P4-LUAC compiler, `-DLUA_FLOAT_TYPE=LUA_FLOAT_FLOAT` |

Note this is the **`script_patch`** chunk, not the base one under
`ui/script/menu/chara_make/`. The patch is the version the game loads, and it
is 10576 bytes against the base's smaller size, so they are different files.

## Deliverables

| path | sha256 |
|---|---|
| `tools/lua-src/make_mii_edit_actor.lua` | `86648c36a9a050657ff56262d9d8d6631d7f8b0a9e54650e1a38999e2e8ec327` |
| `tools/lua-src/build_check.py` | `9e77c7b99a651567ccf889c41272df7ec83adafde4be6240f2f8a8bd860c76a6` |
| `tools/lua-src/compare_chunks.py` | `e59f0d5b8e4ff5a80066ed6601184c02259032658486571bbb297259aae4100f` |
| `tools/lua-src/negative_controls.py` | `78d061ca392f4ae9cdf7ae788e4bbcfcbcfc026dce8f84cd9847df51ac8247e4` |
| `tools/lua-src/make_probe_source.py` | `e6d2e10e54605bf328582d1bed5bdbabccd03a194016aea87bb84772f1d9201b` |
| `tools/lua-src/make_mii_edit_actor_probe.lua` (generated) | `c3f72c8e53627bb490f8ddc3308fc930d3dbb8219b9525ea4d705486462e1ce3` |
| `builds/0.3.1-edit-probe/check_probe.py` | `ab382513b37f79f406b7c8865ca71f3b4f04bf9a7fb16d50ab5d41ffd6b0c13e` |
| `builds/0.3.1-edit-probe/…/make_mii_edit_actor.lc` | `41ce713e552383a5db8b2288be2c87951b20bcebd8cdb84831ffc5dac9ddda3c`, 10739 bytes |

Scratch (not deliverables): `scratch/2026-10-05_P9-EDIT-SOURCE/` holds the
generator `fit.py`, the comparator and diff helpers, and the candidate-shape
harnesses. Evidence: `evidence/P9-EDIT-SOURCE/`.

## Part 1 result

`build_check.py` now checks both reconstructed chunks. For the edit chunk:

```
$ python mods/mii_customizer/tools/lua-src/build_check.py
...
original .../make_mii_edit_actor.lc  10576 bytes  sha256 c777ecc4...a9417
-- per-prototype comparison after the post-pass --
bytes orig 10576  mine 10576  IDENTICAL
prototypes differing: 0 of 18
final gamedata\...\make_mii_edit_actor.lc  10576 bytes  sha256 c777ecc4...a9417
BYTE-IDENTICAL  (18 prototypes, all fields, sha256 c777ecc4...a9417)
```

Per prototype, as the task asked. "instr" is the instruction count, "const" the
constant count, "lines" is `linedefined`/`lastlinedefined`:

| prototype | instr | const | 1st diff | upvalues | lines |
|---|---|---|---|---|---|
| `main` | 57 | 27 | none | OK | 0/0 |
| `main.p0` | 23 | 7 | none | OK | 39/47 |
| `main.p1` | 3 | 1 | none | OK | 49/51 |
| `main.p2` | 5 | 4 | none | OK | 53/56 |
| `main.p3` | 5 | 4 | none | OK | 58/61 |
| `main.p4` | 89 | 25 | none | OK | 66/113 |
| `main.p5` | 215 | 31 | none | OK | 115/215 |
| `main.p6` | 157 | 30 | none | OK | 217/292 |
| `main.p7` | 88 | 20 | none | OK | 294/339 |
| `main.p8` | 38 | 18 | none | OK | 341/358 |
| `main.p9` | 112 | 31 | none | OK | 360/405 |
| `main.p10` | 107 | 37 | none | OK | 410/466 |
| `main.p11` | 225 | 75 | none | OK | 472/567 |
| `main.p12` | 3 | 1 | none | OK | 570/572 |
| `main.p13` | 8 | 4 | none | OK | 575/580 |
| `main.p14` | 2 | 1 | none | OK | 583/585 |
| `main.p15` | 13 | 4 | none | OK | 588/597 |
| `main.p16` | 72 | 18 | none | OK | 600/634 |

Totals: 1222 instructions, 338 constants, 46 upvalue descriptors. All match.

## The is_vararg byte

Before the post-pass, the file is identical except for **one byte**, at offset
**0x28**: the main prototype's `is_vararg`. The game ships `2`; this compiler
writes `1`.

`lundump`/`ldump` lay a prototype out as source, `linedefined`,
`lastlinedefined`, `numparams`, `is_vararg`, `maxstacksize`, and `ldump.c` writes
`is_vararg` straight through with no normalisation. Stock Lua 5.3.6 cannot
produce `2` there: `lparser.c` `mainfunc()` sets `fs->f->is_vararg = 1`
unconditionally for the main chunk, so no Lua source can change it. All three
SSBU editor chunks carry `2`. **verified** (B) by reading the bytes and by the
post-pass producing an identical file.

`build_check.py` writes that one byte, then **re-reads the patched file from
disk** and re-runs both the per-prototype comparison and a plain byte
comparison, so the verdict it reports is about the bytes that exist, not about
an in-memory buffer. It refuses to write unless the byte is currently `1` and
the original holds `2`, so it cannot silently paper over a different difference.

The offset is derived, not hardcoded: the main prototype's own offset comes from
the parse, `is_vararg` is 10 bytes in for a stripped prototype, and the two
neighbouring bytes are checked against the parsed `numparams` and `maxstacksize`
before anything is written. My first attempt computed the offset from an assumed
chunk-header size and got 0x2d instead of 0x28; the derived-and-validated form
is what shipped, and a negative control shifts the derivation by one to prove
the guard fires.

## Codegen facts worth keeping

These are the non-obvious source shapes this chunk needed. All **verified** (B)
by compiling and diffing instructions.

- `AppPopupManager.is_busy()` / `.get_result()` are called with **dot**, not
  colon: `GETTABLE` + `CALL B=1`, not `SELF`. Popup ids are **string literals**,
  so `AppPopupManager.open_database("ID_POPUP_…")`.
- `p4`: the guard is `if 0 <= self.exit_value then`, not `if not (0 <= …)`, and
  the trailing `is_moved` block sits **inside the `else`**.
- `p9`: the tail is `if ComFrameActor.is_decided() … elseif … else <3 ifs> end` —
  an `else` is present, not a bare `if` pair.
- `p10` focus branch: `edit_state.selector1_selected_id >= 0 or (IS_READ_ONLY and
  not IS_SKILL_EDITABLE)`. The `>=` and the `and not` order are what reproduce
  the two `TEST` C-flags (`C=0` for `IS_READ_ONLY`, `C=1` for
  `IS_SKILL_EDITABLE`); the mirror image gives the same shape with both flags
  swapped.
- `p10` wait loop: `repeat / if edit_state:update() == true then break end /
  coroutine.yield() / until false`. A plain `while … do coroutine.yield() end`
  compiles without the `LOADBOOL false` + `TEST` pair at the tail, and
  `until false` is what produces it.
- `p10` trailing loop: `if edit_state.exit_value < 0 then while
  UiFighterManager.is_active(FIGHTER_ENTRY_ID_SELF) == false do
  coroutine.yield() end end`. Note `== false`, not `~= false`; the `EQ` A-flag
  distinguishes them and only one of the two matches.
- `p13`: `is_end()` returns **1** when `edit_state.is_end == true` and 0
  otherwise. This was the last mismatch; I had it backwards at first and the
  constant table caught it. `OP_EQ`'s A field is compared as `res != A`, so
  `A=0` means "skip the next jump when *not* equal".
- **Line numbers are load-bearing.** `lastlinedefined` is the line of the
  function's own `end`, so padding *after* the `end` does nothing. The generator
  inserts the blank lines **inside** the function, immediately before the
  closing `end`. This was the last systematic mismatch: 12 of 18 prototypes had
  a `lastlinedefined` below the original's.

## Negative controls

A check that only ever prints "BYTE-IDENTICAL" proves nothing, so
`negative_controls.py` breaks the build seven ways and asserts each is caught.
Each control runs in a throw-away copy of the workspace layout, so the real
source, the real `build_check.py` and the original chunk are never touched.

```
$ python mods/mii_customizer/tools/lua-src/negative_controls.py
baseline: an unmodified copy of the workspace must pass
  build_check.py edit -> exit 0, output sha256 c777ecc4...a9417

control                                caught  what the check said
source file deleted                    yes     exit 1  missing input: …make_mii_edit_actor.lua
string constant changed                yes     exit 1  prototypes differing: 2 of 18
statement added                        yes     exit 1  prototypes differing: 4 of 18
comparison operator changed            yes     exit 1  prototypes differing: 2 of 18
is_vararg post-pass disabled           yes     exit 1  prototypes differing: 1 of 18
post-pass offset shifted by one        yes     exit 1  prototypes differing: 1 of 18
function moved down one line           yes     exit 1  prototypes differing: 6 of 18

reconstructed source unchanged by the controls: True  sha256 86648c36…
original game chunk unchanged by the controls: True  sha256 c777ecc4…

controls caught 7 of 7
```

Two of these are worth singling out. *"post-pass disabled"* removes the byte
write and the check correctly fails on `is_vararg`, so the post-pass is not
carrying a real difference. *"post-pass offset shifted by one"* makes the
derivation compute 0x29; the guard catches it, so the pass cannot write to a
guessed offset.

The two probe-package controls were run by hand the same way: flipping one byte
of the staged chunk and adding an unexpected file to the probe folder were both
reported as `files: does not match the tree on disk`, exit 1, and the tree was
restored afterwards.

Two of my own harnesses were wrong before they were right, and both are worth
recording so nobody copies the pattern: the first negative-control suite edited
paths inside a staged copy of `build_check.py` and matched nothing because
`os.path.join` produces different separators than the workspace-relative string
being replaced; and its "unchanged source" assertion compared a hash to itself.
Both were replaced with a self-contained staged workspace and hashes captured
before the run.

## Part 2: the probe

Package: `builds/0.3.1-edit-probe/`, probe folder
`mii_customizer_probe_edit/`, payload at
`ui/script_patch/chara_make/make_mii_edit_actor.lc`.

The probe source is **generated** from the byte-identical source by
`make_probe_source.py`, never hand-edited, so the pristine reconstruction keeps
building to the pristine bytes. The block goes immediately in front of the
original `self.exit_value = self.selector0:get_decided_button_id()` line in
`update_selector0`:

```lua
if MC_PROBE_EXIT_VALUE ~= 0
    and self.selector0:get_selected_button_id() == MC_PROBE_EXIT_VALUE
    and self.virtual_input:is_pressed(INPUT_FAVORITE) == true then
    self.selector0:select_button(MC_PROBE_EXIT_VALUE)
    ComFrameActor.press_decide()
end
```

With `MC_PROBE_EXIT_VALUE = 1`, while `selector0` has focus and its selected
button is row 1 (Headgear), one extra press of the Favorite button makes the
script behave as if row 1 had been decided: the **shipped** lines below consume
the state, so the same `exit_value` (1), the same `selector1_selected_id = -1`,
the same `return true`, the same return value from the update function, and the
decide sound the selector widget plays on its own decide path.

### Why INPUT_FAVORITE

The button may only use an input constant and an input object/method the chunk
already reads. The chunk reads six input constants, all through
`self.virtual_input`, and calls `is_pressed`, `is_pressing`, `is_released` and
`is_cancel` on it. `INPUT_COMMON_BUTTON` is out because `update` already feeds
it to `ComFrameActor.press_decide()` — using it would be the normal decide, not
an extra one. `INPUT_BUTTON_LEFT/RIGHT/UP/DOWN` are out because they are the
cursor keys, each read in one of three handlers with its own `is_moved`
bookkeeping, and stealing one fights that state machine. `INPUT_FAVORITE` is
read exactly once, in `update`, under `not FROM_AMIIBO`; on the stock edit
screen it drives `switch_favorite`. The probe tests its own conditions first, so
on a qualifying press it takes that frame.

**This is a judgement call about which button is least disruptive, not a
measurement.** It is the least-conflicted of the six, not a proven-good choice.

### Measured effect on the chunk

Only two prototypes change logically; everything else shifts:

| prototype | change |
|---|---|
| `main` | instructions 57 → 58, maxstacksize 14 → 15 (the new local) |
| `main.p4` | instructions 89 → 111, constants 25 → 29 (the probe) |
| `main.p0`…`main.p16` (rest) | instructions identical; only `linedefined`/`lastlinedefined` shift, and `p10`…`main.p16` also shift upvalue indices because the new local takes a slot |

The probe guards short-circuit in the right order in the compiled code: pc24 is
the `~= 0` test, pc30 the selected-id test, pc36 the Favorite press. Each guard
jumps to pc45, the untouched `get_decided_button_id()` line, so a non-matching
frame costs nothing but a few reads.

**163 bytes longer than the original.** That matters and is called out in the
package README: unlike the P3 same-length rewrite, this one fails any length
check a same-length probe would have passed.

### Two claims I had to correct

- I first wrote that setting `MC_PROBE_EXIT_VALUE = 0` makes the compiler fold
  the block away. It does not: the value is a local, so the test stays. Measured
  — 10739 bytes and 111 instructions in `main.p4` with the probe set to `1`
  *and* to `0`. It is a runtime disable only. For a chunk with no probe code in
  it, delete the region; `make_probe_source.py --strip` does that and asserts
  the result is byte-for-byte the base source, which is how "purely additive" is
  checked rather than assumed.
- I first reported "9726 differing bytes" between the probe chunk and the
  original. That number is mostly offset shifting and is not meaningful. The
  manifest now reports `prototype_deltas` instead, which is the honest measure.

## Limits

- **Nothing was run.** No install, no emulator, no console. Every behavioural
  sentence in this note and in the probe README is a hypothesis supported by
  reading the bytecode.
- **Acceptance of a locally compiled chunk at
  `ui/script_patch/chara_make/make_mii_edit_actor.lc` is untested.** This is the
  central unknown of Part 2. The mod loader may hash the file, may require the
  original length, or may simply load it; nothing here distinguishes those. The
  probe chunk is 163 bytes longer, so it fails any length check.
- Byte identity with a *local* compiler is not evidence that the *game's* build of
  the same source would match. The `is_vararg = 2` byte is itself proof that the
  shipped chunks were not produced by stock `luac`: something in the game's
  toolchain sets it. So "my chunk is byte-identical to the game's" and "the game
  would accept my chunk" are different claims, and only the first is established.
- **Local names are invented.** A stripped chunk stores no local or upvalue
  names, so every name in the source is mine.
- **The blank lines are load-bearing**, not cosmetic. Moving a function's first
  or last line breaks the build, and the negative controls show the check catches
  it.
- Reconstructed with `luac53-game` only. The `luac-control-*` builds were not
  used.
- The line numbers of the shipped source are inferred from the stored
  `linedefined`/`lastlinedefined`. They are reproduced exactly, but the shipped
  file's *contents* between those lines are unknowable — only the code that
  survives compilation is recoverable, so comments and any dead code the original
  had are absent here.
- The probe's claim that `ComFrameActor.press_decide()` is what makes a focused
  selector decide is inferred from `update`'s own use of it for
  `INPUT_COMMON_BUTTON`. It was not observed.
