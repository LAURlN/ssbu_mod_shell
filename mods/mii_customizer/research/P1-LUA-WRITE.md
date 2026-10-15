# P1-LUA-WRITE - checked reserialization of the editor Lua chunks

2026-10-04. Space Bunny Alpha worker, follow-up to the P1-UI-DECODE Lua worker.
Bounded offline work on `tools/lua53-inspect/` only. No decompiler, no compiler,
no emulator, no console, no commits, no production UI change.

**Status: DONE.** The three editor chunks round-trip byte-identically, a
length-changing constant rewrite is demonstrated and shown to change exactly one
field, and the malformed/truncated rejection checks still pass.

## 1. Inputs (read-only, hashes re-verified after every write)

All three are the already-extracted chunks from `gamedata/mii_customizer/P1-UI/`,
unchanged by this task. Hashes re-checked at the end and identical to
P1-UI-DECODE's record:

| ARC path | sha256 | bytes |
|---|---|---|
| `ui/script/menu/chara_make/make_mii_edit_actor.lc` | `1f73dff133961b68dbe24641298229b9f3905a44703164563911b105eaa16908` | 10321 |
| `ui/script/menu/chara_make/make_mii_special_actor.lc` | `ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d` | 7799 |
| `ui/script_patch/chara_make/make_mii_edit_actor.lc` | `c777ecc492cea48f6ffd40112b22f96e66219d00969b570a7cc3cf8d7f4a9417` | 10576 |

`evidence/P1-LUA-WRITE/input_hashes.txt`. Nothing was written into
`tools/`, `source/`, or `evidence/`; generated chunks live only in
`gamedata/mii_customizer/P1-LUA-WRITE/`.

## 2. What was added

`lua53_inspect.py` gained an encoder mirroring `ldump.c` at the pinned tag
**v5.3.6** (`DumpHeader`, `DumpFunction`, `DumpString`, `DumpConstants`,
`DumpDebug`), plus a mutator, a structural comparer and a synthetic-chunk
builder. New CLI commands: `roundtrip`, `encode`, `setconst`, `compare`,
`synth`. **All seven previous commands are unchanged in behaviour**;
`verify`, `summary`, `header`, `protos`, `dis`, `constants` and `xref` produce
the same output, confirmed by re-running them and by the unchanged check set.

Five parse-side fields were added, because the loader alone does not retain
enough to write the bytes back:

- `Proto.source_is_null` - `LoadFunction` substitutes the parent's source when
  the dumped string is NULL, so without this every child proto would be
  re-encoded carrying the parent's source string.
- `Proto.source_long`, `LocVar.name_long`, `Proto.upvalue_names_long`,
  `Constant.long_form` - whether each string used the `0xFF` size-byte escape.
  `DumpString` only escapes when `size >= 0xFF`, so deriving the width from the
  length would *normalise* such a chunk instead of reproducing it.
- `verify()` gained one check, `main-upvalue-count`, comparing the header's
  main-closure upvalue byte against the main proto's descriptor count. This is
  the assertion `luaU_undump` makes, so it belonged.

Encoder rules, each taken from the pinned source rather than guessed:

- widths come from the **parsed header**, never the host, so a 4-byte
  `lua_Number` chunk stays 4-byte;
- string size is one byte, or `0xFF` + a full `size_t`, with `size = len + 1`
  (the dumped size includes the trailing NUL);
- a rewritten string is tagged `LUA_TSHRSTR` at or below
  `LUAI_MAXSHORTLEN` (40) and `LUA_TLNGSTR` above it;
- field order is `ldump.c`'s exactly: source, `linedefined`,
  `lastlinedefined`, `numparams`, `is_vararg`, `maxstacksize`, code,
  constants, upvalues, protos, `lineinfo`, `locvars`, upvalue names.

## 3. Round trips: byte-identical on all three chunks

`roundtrip` makes three *independent* comparisons, so no single coincidence can
make it pass: byte length, SHA256, and a structural diff of the re-parsed
encoder output against the original parse. The third one matters because a
hash comparison of a chunk against itself proves nothing about whether the
encoder dropped a field - the structural diff compares parsed *values*, and it
stays meaningful when a rewrite legitimately shifts every later offset.

```
python tools/lua53-inspect/lua53_inspect.py roundtrip \
  gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_edit_actor.lc \
  gamedata/mii_customizer/P1-UI/ui/script/menu/chara_make/make_mii_special_actor.lc \
  gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc
```

Exit **0**. Observed, per chunk:

| chunk | bytes in / out | SHA256 in = out | structural diff |
|---|---|---|---|
| `make_mii_edit_actor.lc` | 10321 / 10321 | `1f73dff1…aa16908` | none |
| `make_mii_special_actor.lc` | 7799 / 7799 | `ffa2bafa…2b40d65d` | none |
| `script_patch/make_mii_edit_actor.lc` | 10576 / 10576 | `c777ecc4…4a9417` (both) | none |

Evidence: `evidence/P1-LUA-WRITE/roundtrip_three_chunks.txt`.

**This is a real encoder verification, not a blob passthrough.** `encode` writes
an independent file to disk and the result hashes identically to the original
(`reencoded_special_actor.lc`, 7799 bytes,
`ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d`), and the
structural diff independently confirms no parsed field was lost. Encoding
happens from the `Proto` object graph built by the parser; the original bytes
are never copied through.

## 4. The length-changing mutation

### 4.1 Why a synthetic chunk, not a real one

The prompt's first choice was a real display-name literal. **There is no
suitable one in any of the three chunks, and this is a measured result rather
than an assumption.** I classified every string constant in all three chunks
(`scratch/2026-10-04_P1-LUA-WRITE/find_display_literals.py`):

- **0 unreferenced string constants** in all three chunks
  (`find_unused_literals.py`). Every single string is consumed.
- The only literals that are not plain identifiers are three format templates:
  `set_item_%02d`, `category_%02d`, `set_special_item_%02d`. Tracing each to
  its consuming instructions (`evidence/P1-UI-DECODE/dis_*.txt`) shows each is
  passed to `string.format` and the **result is then handed to
  `get_parts` / `play_animation`** - for example `main.p11` pc104-109 in the
  base editor builds `set_item_%02d` and immediately calls
  `selector0.setup_button` with it.

So these are layout **part-name formats** whose value is a native argument, not
display text. Rewriting one would change which layout part the editor addresses
- exactly the "selector / native argument" class the prompt forbids, and exactly
the sort of edit that would break the editor rather than demonstrate the write
path. There is no other candidate: everything else is a bridge name, a global,
a state/selector name or a layout part name.

The prompt's stated fallback therefore applies, and I took it: **all three real
chunks are left unmodified.**

### 4.2 What was done instead

`build_synthetic_chunk()` produces a small **valid** Lua 5.3 chunk using the
*same widths as SSBU* (29-byte header, 4-byte `lua_Number`, 8-byte `size_t`,
`Instruction` 4 bytes), with one nested prototype, one `locvar` and one upvalue
name - so it also covers the two debug sections the three real chunks lack,
being stripped. It carries one **deliberately unreferenced** string literal as
the mutation target, so "only the intended constant changed" is a claim about
the whole chunk, not about one argument path.

`setconst` **refuses by default** to touch a constant any instruction consumes,
and names the consumers if overridden with `--allow-used`. This fired for real
during development, on `main K[0]`, and is kept as a check
(`evidence/P1-LUA-WRITE/setconst_refusal.txt`).

Two growths were tested, on separate disposable files:

| case | old | new | chunk size | type tag | `0xFF` escape |
|---|---|---|---|---|---|
| short form | 37 chars | 69 chars | 331 → 363 | `0x14` LNGSTR | no (70 < 0xFF) |
| long form | 37 chars | 321 chars | 331 → 623 | `0x14` LNGSTR | **yes** |

Both are `LUA_TLNGSTR` because both exceed `LUAI_MAXSHORTLEN` = 40, which is
what `ldump.c` would write; only the 321-char case needs the escape. Confirmed
in the emitted bytes: the payload at `0x95` is preceded by
`ff 42 01 00 00 00 00 00 00` - `0xFF` then a little-endian `size_t` of 322,
which is `len + 1`.

For each case, `compare` against the pre-mutation chunk reports **exactly one**
structural difference, and it is the intended constant:

```
main.K[6]: tag=4 kind=string value='p1_lua_write_inert_literal_replace_me' long=False
       != tag=20 kind=string value='P1_LUA_WRITE_MUTATED_XXXX…' long=True
```

Independently confirmed in the same check run: **all instruction words in every
prototype are unchanged** (the full word list is compared, not a count), every
proto's `linedefined`/`lastlinedefined`/`numparams`/`is_vararg`/`maxstacksize`
match, upvalue descriptors and names match, `lineinfo` and `locvars` match, and
both mutated chunks pass `verify()` and re-encode identically.

Evidence: `mutation_compare_long.txt`, `mutation_compare_short.txt`,
`roundtrip_synthetic_and_mutants.txt`, `verify_synthetic_and_mutants.txt`.

**Offsets necessarily move** after a growth - that is the point of the test -
which is exactly why `compare` compares parsed values and not offsets. Nothing
was hand-edited: every mutated file came out of `encode_chunk`.

## 5. Malformed / truncated rejection still passes

`check_lua53_inspect.py` runs **155 passing checks, exit 0** (108 before this
task; 47 added). Full output `evidence/P1-LUA-WRITE/checks_final.txt`, negative
group extracted to `rejection_checks_negative.txt`.

Nothing was weakened to achieve this. The parser's guards are untouched; the
only change on that side is the one *added* check. Preserved and still passing:

- empty input, 3-byte prefix, corrupted signature, non-5.3 version byte, bad
  format byte, corrupted `LUAC_DATA`, big-endian `LUAC_INT`, wrong `LUAC_NUM`,
  implausible size byte;
- truncation at four cut points (25%, 50%, 90%, 99.9%);
- trailing garbage, which must be *reported* rather than ignored;
- mutation checks proving `verify()` catches an out-of-range opcode, an
  out-of-range `LOADK` constant and an out-of-range jump target, rather than
  silently passing.

Note the distinction: `grep FAIL` finds 9 hits in `checks_final.txt`, but **zero
lines begin with `FAIL`**. Each of those 9 is the *expected* quoted output inside
a PASS line, e.g.
`PASS verify() catches an out-of-range LOADK constant: FAIL loadk-in-range: …`.
That is the negative test doing its job.

Baseline before my edits was captured first (`baseline_checks.txt`,
`baseline_verify.txt`, both exit 0) so "still passes" is a comparison, not an
assertion.

## 6. Limits

**What the tool can write.** Header widths, floats, integers, booleans, nil,
strings (both size forms), nested prototypes, instruction words, upvalue
descriptors, `lineinfo`, `locvars` and upvalue names.

**What it deliberately will not write.**

- Only **string constants** can be rewritten. `set_string_constant` refuses any
  other constant kind, an unknown proto path and an out-of-range index.
- It **cannot insert or delete constants**, nor change an instruction word.
  This is not an oversight: `LOADK Bx` and `RK` operands index the constant
  table **positionally**, so inserting a constant silently invalidates every
  later reference. Length changes are safe because positions do not move;
  insertion would need operand fixup that is not implemented and not tested.
- The **prototype tree shape is fixed**. The nested order is load order and
  `CLOSURE Bx` depends on it.

**Why this is not proof the game loads modified scripts.** Round-tripping proves
the bytes match a format I read out of pinned reference source. It does **not**
establish that:

- the game uses this loader, or this exact dump path, for these files;
- the chunk is not integrity-checked, hashed, or validated against a manifest
  before `luaU_undump` sees it;
- a modified chunk would be accepted rather than rejected with a load error;
- the UI would behave differently, or behave *sensibly*, if it were.

**Offline evidence cannot settle any of those.** Only a console run can, and
per the mod rules no emulator, console or install was performed. The correct
next step is a single gated console experiment, not more offline work.

I also did **not** chase the layout/identity work owned by other workers, made
no production UI change, and built **no install candidate**: `builds/` was not
touched.

## 7. Corrections to P1-UI-GLOBALS overclaims

Per the prompt, corrected here only; I did not edit that report.

1. **"Absence of an assignment does not prove a global is immutable."** That
   report reached the right conclusion but its framing ("read-only, never
   written") could be misread as a property of the *global*. It is a property of
   *those three files*. The same name could be assigned by any other chunk, and
   74 `ui/script/*.lc` files remain unextracted. Nothing observed here supports
   the word "immutable".
2. **Host-injected is an inference, not a finding.** `MII_TYPE_GUNNER` being
   host-provided is well argued. Extending that to `SKILL_COMMAND_NUM` &
   `SPECIAL_SKILL_NUM` is a **pattern argument** (tier D), and the report's own
   table shows all four unknowns also have **0 reads** in those chunks - i.e.
   they are *absent*, not read-only. "Read-only" and "not present" are different
   claims, and only the second is what was measured.
3. **An enum is not necessarily host-owned.** A `_ENV` global named like an enum
   is consistent with host injection, but equally consistent with a Lua module
   that assigns it at load time - which is precisely what `make_mii_utility.lc`
   demonstrably does for 33 other names. The naming convention carries no
   ownership information on its own.

None of this changes that report's actual answer: the three recommended modules
are **not** the source. It is a real negative result.

## 7b. Correction to this tool's own README (and to P1-UI-DECODE)

Both said the editor chunks are stripped of debug *names* "but `lineinfo`
survives". **That is wrong, and I measured it rather than assuming it:**
`lineinfo` has **0 entries in every prototype of all three chunks**, exactly
like `locvars` and upvalue names. The chunks are fully stripped, as
`DumpDebug` writes a count of 0 for all three sections when `strip` is set.

The *conclusion* those notes drew is still sound, but for a different reason:
`linedefined`/`lastlinedefined` survive because `DumpFunction` writes them
unconditionally **outside** the debug section, not because any debug data was
kept. That matters here, because the encoder's debug-section path has **no
coverage from the real chunks at all** - the synthetic chunk is what exercises
`locvars` and upvalue names, and it also carries `lineinfo`.

I corrected the README (a file inside my exclusive write path) and added two
regression checks (155 total, up from 108) so this stays measured rather than
remembered. I did **not**
edit `research/P1-UI-DECODE.md`, which is outside my write paths; its section 1
carries the same wrong premise and should be fixed by the coordinator or its
author.

## 8. Evidence tiers

| tier | claim |
|---|---|
| **B** verified offline | byte-identical round trips on all three chunks (length + SHA256 + structural diff); the re-encoded file on disk hashing identically; exactly one structural difference per mutation with all instruction words unchanged; both size-escape forms correct in the emitted bytes; 0 lineinfo entries in all three chunks (fully stripped) with 17/18, 16/17, 17/18 protos at a non-zero linedefined; 155 checks passing, exit 0; originals' hashes unchanged after all writes; 0 unreferenced string constants and the three format literals all traced to `get_parts`/`play_animation` |
| **C** pinned source | the chunk layout, field order and string-size rule (`lundump.c`, `ldump.c`, `lopcodes.h`, `lopcodes.c`, `lobject.h`, tag v5.3.6) |
| **A** console | **none.** No run was performed. Nothing here is evidence about runtime behaviour. |
| **D** hypothesis | that the game would load a modified chunk; that the three format literals are the only safe-looking real targets; anything about layout or identity |

## 9. Commands and results

All from the workspace root. Note `python3` on this machine resolves to the
Windows Store alias stub and fails with exit 49; `python` is CPython 3.12.3 and
is what every command below used.

| command | exit | result |
|---|---|---|
| `python <tool> verify B S P` (baseline, before edits) | 0 | all pass |
| `python check_lua53_inspect.py B S P` (baseline) | 0 | 108 checks |
| `python <tool> roundtrip B S P` | **0** | 3× byte-identical, 3× structural diff none |
| `python <tool> encode S <out>` | 0 | wrote 7799 bytes, `identical to input: True` |
| `python <tool> synth <out>` | 0 | wrote 331-byte valid chunk |
| `python <tool> setconst <synth> <out> main 0 x` | **1** | refused: constant is referenced |
| `python <tool> setconst <synth> <out> main 6 <321 chars>` | 0 | 331 → 623 bytes, tag `0x14`, escape used |
| `python <tool> setconst <synth> <out> main 6 <69 chars>` | 0 | 331 → 363 bytes, tag `0x14`, no escape |
| `python <tool> verify <both mutants>` | 0 | all pass |
| `python <tool> roundtrip <synth + both mutants + real re-encode>` | **0** | 4× byte-identical |
| `python <tool> compare <synth> <long mutant>` | 0 | exactly 1 difference: `main.K[6]` |
| `python <tool> compare <synth> <short mutant>` | 0 | exactly 1 difference: `main.K[6]` |
| `python check_lua53_inspect.py B S P` (final) | **0** | **155 checks**, zero failing lines |

## 10. Changed files

Inside this mod's exclusive write paths only:

- `tools/lua53-inspect/lua53_inspect.py` - encoder, mutator, comparer, synthetic
  builder, 5 new commands, 5 new parse-side fields, 1 new check
- `tools/lua53-inspect/check_lua53_inspect.py` - encoder and mutation check
  groups (108 → 155 checks)
- `tools/lua53-inspect/README.md` - encoder usage, rules and limits
- `research/P1-LUA-WRITE.md` - this report
- `evidence/P1-LUA-WRITE/` - 15 files (see below)
- `scratch/2026-10-04_P1-LUA-WRITE/` - 5 files: `survey_chunks.py`,
  `find_display_literals.py`, `find_unused_literals.py`, and the two one-shot
  patch scripts that applied the edits

Generated chunks, in workspace `gamedata/mii_customizer/P1-LUA-WRITE/` (game-derived
output goes here, never into the mod's `tools/`/`source/`/`evidence/`):
`synthetic_marker.lc`, `synthetic_mutated_long.lc`, `synthetic_mutated_short.lc`,
`reencoded_special_actor.lc`.

Evidence files: `input_hashes.txt`, `baseline_verify.txt`, `baseline_checks.txt`,
`roundtrip_three_chunks.txt`, `verify_three_chunks.txt`,
`summary_three_chunks.txt`, `verify_after_encoder.txt`,
`checks_after_encoder.txt`, `checks_final.txt`,
`rejection_checks_negative.txt`, `roundtrip_synthetic_and_mutants.txt`,
`verify_synthetic_and_mutants.txt`, `mutation_compare_long.txt`,
`mutation_compare_short.txt`, `setconst_refusal.txt`.

Untouched: `STATUS.md`, `CHANGELOG.md`, `CURRENT_INSTALL.md`, `builds/`,
`prompts/`, `phases/`, `research/P1-UI*.md`, other workers' paths,
`mods/ssbu_mod_new/`, workspace `tools/`, the `dump/`, the original chunks, any
save, SD card or emulator state. No commits, no branches, no installs.

## 11. Next experiment

One bounded console gate, when the coordinator wants it: replace the *format*
literal only, in a **single** file, with a same-shape string of the same length
(`category_%02d` → `category_%0Zd` style, or a same-length visibly-wrong name),
so a UI difference would be unambiguous while the file's size and every offset
stay identical. Observe whether the editor still opens and whether the addressed
part changed. That single run separates "the write path is usable on console"
from "byte-identical reserialization works", which this task proved only the
second half of. Keep a vanilla control in the same batch.

## Task summary

**P1-LUA-WRITE: DONE** — three byte-identical round trips, one controlled
length-changing mutation proven to alter exactly one field, 155 checks passing,
all three real chunks unmodified.

Changed files, commands and observed exit codes are in sections 9 and 10 and are
persisted above, so the coordinator only needs to be told the task is finished.