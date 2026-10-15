# P1-UI-DECODE - instruction-level decode of the three editor chunks

2026-10-04. Space Bunny Alpha worker, follow-up to P1-UI. Bounded analysis, no
production code, no emulator, no console, no commits.

**Status: DONE with two PARTIAL boundaries** (section 6). P1-ID was left alone:
nothing here traces native identifiers, saved data, or editor-to-battle bindings.

Inputs are the three already-extracted chunks, read-only, hashes unchanged from
P1-UI and re-verified:

| file | sha256 | bytes |
|---|---|---|
| `ui/script/menu/chara_make/make_mii_edit_actor.lc` | `1f73dff133961b68dbe24641298229b9f3905a44703164563911b105eaa16908` | 10321 |
| `ui/script/menu/chara_make/make_mii_special_actor.lc` | `ffa2bafab92aac574c4245372ef77698c74681ba6be9f02a8e5bb27d2b40d65d` | 7799 |
| `ui/script_patch/chara_make/make_mii_edit_actor.lc` | `c777ecc492cea48f6ffd40112b22f96e66219d00969b570a7cc3cf8d7f4a9417` | 10576 |

All full paths are under `gamedata/mii_customizer/P1-UI/`. Commands and the full
file list: `evidence/P1-UI-DECODE/commands_and_hashes.txt`.

## 1. Chunk format: two facts that broke the old parser

**Tier C, pinned.** Format authority is the official reference implementation at
tag **v5.3.6** — `lundump.c`, `ldump.c`, `lopcodes.h`, `lopcodes.c`, `lobject.h`
(`https://github.com/lua/lua/blob/v5.3.6/<file>`, retrieved as raw text). This is
**Lua 5.3, not LuaU**; LuaU uses a different chunk format and is rejected up front.

P1-UI's scratch reader (`scratch/2026-10-04_P1-UI/lc53_strings.py`) had two wrong
assumptions, and both are confirmed against the pinned source, not guessed:

1. **These chunks use 4-byte `lua_Number`, not double.** The header at offset
   `0x10` records `sizeof lua_Number = 4`. So the header is **29 bytes** and the
   first prototype starts at `0x1e` — not 32 bytes / `0x20`. Reading an 8-byte
   double for `LUAC_NUM` desynchronises the walk immediately.
2. **String lengths are not variable-length integers.** `LoadString` reads a
   *single* size byte, with `0xFF` as the only escape to a full `size_t`. The
   dumped size includes the trailing NUL, so the stored text is `size - 1` bytes.
   P1-UI's reader treated string sizes as a 7-bit varint; it happened to agree
   for values under 128, which is exactly why it looked plausible.

A third, smaller point: `DumpUpvalues` always dumps the real upvalue descriptor
count while `DumpDebug` dumps the upvalue **name** count as 0 for a stripped
chunk. So `0 names / N upvalues` is the normal stripped shape, not a defect. My
first `verify()` wrongly flagged this; the check was wrong, not the parse.

**Load-bearing evidence:** all three chunks parse recursively and consume their
final byte exactly (`verify` exits 0). A wrong structure size, a mis-sized float
or a mis-read string length would leave trailing bytes, so exact consumption is
strong evidence the byte layout was read correctly — not merely that the header
looked plausible.

| chunk | protos | instructions | constants | strings | consumed |
|---|---|---|---|---|---|
| `make_mii_edit_actor.lc` | 18 | 1181 | 333 | 293 | 10321 / 10321 |
| `make_mii_special_actor.lc` | 17 | 794 | 276 | 237 | 7799 / 7799 |
| `script_patch/make_mii_edit_actor.lc` | 18 | 1222 | 338 | 297 | 10576 / 10576 |

These chunks are stripped of debug names, but `lineinfo` survives, so
`linedefined`/`lastlinedefined` are usable to line up prototypes across versions.

## 2. What the constants and instructions actually say

Tool: `mods/mii_customizer/tools/lua53-inspect/` (see its README for usage).
Evidence: `evidence/P1-UI-DECODE/dis_*.txt`, `constants_all.txt`, `xref_*.txt`.

### `SKILL_COMMAND_NUM` and `SPECIAL_SKILL_NUM` are globals, and there is no number

P1-UI said these "live in the bytecode as literals/globals". The decode settles
which, and it is **globals only**.

Every occurrence is consumed by `GETTABUP` through its **C operand**, with
`B = 0` reading upvalue 0 — for a chunk main closure that is `_ENV`, the global
table. Full inventory from `evidence/P1-UI-DECODE/counts_numeric_evidence.txt`:

| name | occurrences | consuming instructions |
|---|---|---|
| `SKILL_COMMAND_NUM` | 5 | 6 (`main.p2` pc14, `main.p3` pc1, `main.p4` pc5, `main.p14` pc9 + pc35, `main.p15` pc59) |
| `SPECIAL_SKILL_NUM` | 3 | 3 (`main.p9` pc11, `main.p10` pc17, `main.p15` pc95) |

Worked example, `main.p2` — this is the loop that drives `set_special_item_%02d`:

```
[13] LOADK    R[3] := K[10] 1
[14] GETTABUP R[4] := up[0][K[11]=SKILL_COMMAND_NUM]   @0x334
[15] LOADK    R[5] := K[10] 1
[16] FORPREP  A=3 sBx=33 -> pc 50        ; loop 1..SKILL_COMMAND_NUM
[17] SUB      ...                        ; i - 1
[22] LOADK    R[10] := K[16] set_special_item_%02d
[24] CALL     R[9](2 args)               ; string.format
...
[50] FORLOOP  A=3 sBx=-34 -> pc 17
```

So `SKILL_COMMAND_NUM` is the loop's **upper bound read from `_ENV` at runtime**.
Critically:

- **Zero** `SETTABUP`/`SETTABLE` instructions anywhere in the chunk assign either
  name, so **neither count is defined in this chunk.**
- The complete numeric-constant inventory of the whole chunk is
  `-1, 0, 0.0, 1, 1.0, 2, 3, 4, 5, 6, 7, 8, 99, 1000`. A literal count would have
  to be in that list. It is not.

**Therefore the numeric values of `SKILL_COMMAND_NUM` and `SPECIAL_SKILL_NUM`
cannot be resolved from these three chunks.** P1-UI correctly declined to guess;
this task confirms that refusal was right, and shows the guessing would have had
no basis in these files. The chunk `require`s only `common/state_function` and
`common/ui_common`, so the definition lives in one of those or in a chunk not
extracted yet. **PARTIAL** — see section 6 for the minimal next step.

### `get_skill_id` / `set_skill_id` are native calls, not table fields

P1-UI could not say whether these were reads, calls or table fields. They are
**calls**, in `main.p14` only, and they go through `UiScriptPlayer.invoke`:

```
[12] GETTABUP R[4] := up[0][K[6]=UiScriptPlayer]
[13] GETTABLE R[4] := R[4][K[7]=invoke]
[14] LOADK    R[5] := K[8] get_skill_id
[15] SUB      ...                       ; command_id - 1
[16] CALL     R[4](2 args)
```

and the write side at pc40 with `set_skill_id`. So the names are **string
constants passed as arguments to a native dispatcher**, exactly as P1-UI
suspected for `invoke`. Two useful details: both live in the same prototype that
also reads `SKILL_COMMAND_NUM` (pc9 and pc35), and the loop at pc11 iterates
`1 .. SKILL_COMMAND_NUM`, calling `get_skill_id` once per command slot and
storing results into a table keyed by the loop variable. That is the per-slot
read pattern; it does **not** establish where the value is persisted, which stays
P1-ID's scope.

`get_skill_name_label` (3 sites) and `get_skill_help_label` (2 sites) are the
same `LOADK`-then-call shape and are listed in `xref_special_counts.txt`.

## 3. Base vs shipped patch: what actually differs

P1-UI reported "exactly four added lines, all the token `IS_SKILL_EDITABLE`",
from an ASCII scan. At prototype level the picture is sharper, and one detail
differs from the string-level reading.

**Same 18 prototypes, same order, same names, identical header.** Only five
prototypes change. Total: **+41 instructions, +5 constants, +255 bytes.**

| proto | code | constants | lines |
|---|---|---|---|
| `main` | 56 → 57 (+1) | 26 → 27 (+1) | 0..0 |
| `main.p5` | 203 → 215 (+12) | 30 → 31 (+1) | 114..209 → 115..215 |
| `main.p6` | 145 → 157 (+12) | 29 → 30 (+1) | 211..281 → 217..292 |
| `main.p10` | 104 → 107 (+3) | 36 → 37 (+1) | 399..453 → 410..466 |
| `main.p11` | 212 → 225 (+13) | 74 → 75 (+1) | 459..547 → 472..567 |

The other 13 prototypes are **instruction-for-instruction identical**; only their
`linedefined`/`lastlinedefined` shift, all by exactly **+1** (e.g. `main.p0`
38..46 → 39..47). That is the signature of a source file with one extra line
inserted before them, not of rewritten functions.

`IS_SKILL_EDITABLE` occurs **0 times in the base and exactly 4 times in the
patch**, one in each of `main.p5`, `main.p6`, `main.p10`, `main.p11`, each read by
exactly one instruction and always adjacent to `IS_READ_ONLY` (itself 5 occurrences
/ 5 uses in *both* chunks, i.e. unchanged). `IS_SKILL_EDITABLE` is always a
**`GETTABUP` global read** — a runtime flag check, never a literal and never a
function call.

The clearest site, `main.p11` (the "skills editable" branch), base pc153-156
versus patch pc153-169:

```
patch:
[153] GETTABUP R[6] := up[1][K[54]=IS_SKILL_EDITABLE]   @0x1fd0
[154] TEST     if not (R[6] <=> 0) then pc++
[155] JMP      pc -> 166
[156..164]  selector0:set_selectable(idx, true); selector0:select_button(idx)
[166] GETTABUP R[6] := up[0][selector0]
[167] SELF     R[6] := R[6][set_enable]
[168] LOADBOOL A=8 B=0        ; false
[169] CALL     R[6](2 args)   ; -> selector0:set_enable(false)
```

base at the same point does the `set_enable(false)` **unconditionally**. So the
patch's effect is: when `IS_SKILL_EDITABLE` is true, the skills selector is made
selectable and focused; otherwise it is disabled. This is now **instruction-level
verified**, upgrading P1-UI's tier-D reading. Note the `set_selectable` name
itself is *not* new — one constant, read by 2 instructions in the base and 3 in
the patch. What is new is the `IS_SKILL_EDITABLE` test gating around it.

**Correction to my own first pass, recorded because it changes a number.** I first
described the `main` proto delta as "one integer constant 4 added at K[6]". That
is true but incomplete: the constant-table shift (`K[9] set_enable_input` →
`K[10]`) is a *consequence* of inserting one literal into the integer sequence at
pc13-19, which also raises `maxstack` 13 → 14. A register-consumption check shows
**neither the base nor the patched integer sequence is read by any decoded
instruction in that prototype**, so what the added `4` feeds is *not* established
by this decode. It must not be read as a count, id or selector index. This is the
honest limit of a bounded, non-decompiling read, and it is the one place where the
patch's main-proto change remains unexplained. The other four sites are fully
explained.

## 4. Evidence tier summary

| tier | claim |
|---|---|
| **C** pinned source | the chunk layout: header fields, proto order, string/constant encoding, opcode tables, from `lua/lua` v5.3.6 |
| **B** verified offline | all three headers; byte-exact full consumption on all three; the 108 self-checks; every offset, constant, opcode and use-site quoted above; the per-proto base/patch deltas; that `IS_SKILL_EDITABLE` is a `GETTABUP` read at exactly 4 sites; that `get_skill_id`/`set_skill_id` are called via `UiScriptPlayer.invoke`; that neither count has a literal or an assignment |
| **A** console | none. No run was performed. |
| **D** hypothesis | that the patched source is a one-line-later revision of the same Lua file (strongly supported by the uniform +1 line shift, still an inference); what the added integer literal in `main` feeds; that `IS_SKILL_EDITABLE` is the game's own "skills may be edited" runtime gate (tier D about *purpose*; the *mechanism* is tier B) |

## 5. Tool promoted

`mods/mii_customizer/tools/lua53-inspect/` — parser, `verify`/`xref`/`dis`
commands, README with the format notes, and `check_lua53_inspect.py`.

Checks are meaningful rather than decorative: full byte-exact consumption,
recursive nested-prototype parsing, opcode/constant/proto/jump bounds, and
negative tests that the parser *refuses* empty, short, wrong-signature,
wrong-version, wrong-format, corrupted-`LUAC_DATA`, big-endian, wrong-`LUAC_NUM`,
bad-size-byte and truncated input, plus mutation tests proving `verify()` really
catches an out-of-range opcode, an out-of-range `LOADK` constant and an
out-of-range jump target. **108 checks pass, exit 0** across all three chunks
(`evidence/P1-UI-DECODE/selfcheck_all.txt`). Python 3.12.3, stdlib only, nothing
installed.

Building the checks found **two real defects in my own tool**, both fixed: a wrong
`upvalue-name-count` rule that misread stripped chunks, and a `verify()` that
*crashed* on an out-of-range opcode instead of reporting FAIL. A third bug was
more consequential: `xref` originally searched only for `LOADK`, so it reported
`SKILL_COMMAND_NUM` as having **0 uses** — while it is in fact read 6 times via
`GETTABUP`. Any constant consumed as an RK operand was invisible. Fixed to report
`LOADK` and `RK.B`/`RK.C` separately.

Scratch, not promoted: `lc53_diff.py` (positional diff — kept because it shows
*why* naive diffing is misleading here) and `lc53_align.py` (difflib alignment on
value-resolved tokens, which is what made the real delta readable).

## 6. Unresolved boundaries and one recommended next task

Boundaries this task hit, all stated as limits rather than filled in:

1. **`SKILL_COMMAND_NUM` / `SPECIAL_SKILL_NUM` numeric values — unresolved.** They
   are `_ENV` globals, never assigned in these three chunks, and no plausible
   literal exists in the chunk. **PARTIAL.**
2. **The added integer literal in `main` — unexplained.** Not consumed by any
   decoded instruction in that prototype. **PARTIAL.**
3. **Native behaviour — out of scope and untouched.** `UiScriptPlayer.invoke` call
   sites prove a name reaches native code, not what native code does. No
   identifier, save or editor-to-battle binding was traced; that is P1-ID's.
4. **A decoded instruction is not runtime or native-target proof.** Everything in
   section 2 and 3 is bytecode evidence about files on disk.

**Recommended single next UI task (minimal, and it does not overlap P1-ID):**

> Decode `ui/script/common/ui_common.lc` and `ui/script/common/state_function.lc`
> (and `ui/script/menu/chara_make/make_mii_utility.lc`) with the now-working
> `lua53_inspect`, and locate the **assignment** of `SKILL_COMMAND_NUM`,
> `SPECIAL_SKILL_NUM`, `IS_READ_ONLY` and `IS_SKILL_EDITABLE`.

That is the single blocking unknown for the editor's slot count, it is one
extraction plus one `xref`, and it resolves item 1 directly with the same method
that resolved everything else. It reads shared UI constant definitions only — it
does not touch identity, saved data or native bindings, so P1-ID can keep running.
Note `arc-extract` is already available for the extraction step
(`tools/REGISTRY.md`), and layout ARCs need the doubled nested path name recorded
in P1-UI.

If those modules do not assign the names either, the honest outcome is that the
counts come from the native side, and the answer is to stop and report that
boundary rather than escalate to native RE on the strength of this report.

## Task summary

**P1-UI-DECODE: DONE** (two boundaries PARTIAL, item 1 and 2 in section 6)

Changed files, all inside this mod's assigned paths:

- `research/P1-UI-DECODE.md` (this report)
- `evidence/P1-UI-DECODE/` — 16 files: `commands_and_hashes.txt`, `header_dump.txt`,
  `proto_summary.txt`, `constants_all.txt`, `verify_all.txt`, `selfcheck_all.txt`,
  `counts_numeric_evidence.txt`, `patch_skill_editable_sites.txt`,
  `align_edit_base_vs_patch.txt`, `positional_diff_edit.txt`,
  `dis_special_actor.txt`, `dis_edit_actor_base.txt`, `dis_edit_actor_patch.txt`,
  `xref_special_counts.txt`, `xref_edit_base.txt`, `xref_edit_patch.txt`
- `tools/lua53-inspect/` — `lua53_inspect.py`, `check_lua53_inspect.py`, `README.md`
- `scratch/2026-10-04_P1-UI-DECODE/` — `lc53_align.py`, `lc53_diff.py`

Observed checks: `verify` exit 0 on all three chunks with exact byte consumption;
`check_lua53_inspect.py` 108 PASS / 0 FAIL, exit 0; all four scripts parse as
valid Python. Re-run after the final tool edit (see below), with exit statuses
captured directly rather than through an output filter.

Untouched: `STATUS.md`, `CHANGELOG.md`, `CURRENT_INSTALL.md`, `phases/`, other
workers' paths, `mods/ssbu_mod_new/`, shared `tools/`, saves, framework plugins,
and the SD card. No emulator, no console, no commits, no production UI changes.
Inputs read-only. No new dependency and no tool installation.

**Scope-verification correction.** An earlier note in this session claimed scope
was confirmed by `git status`. That was wrong: `<workspace>` is **not a git
repository** (`git rev-parse` exits 128, "not a git repository"), so the empty
output proved nothing. Scope was re-verified by modification time instead: every
coordinator file (`STATUS.md` 13:17, `CHANGELOG.md` 13:17, `CURRENT_INSTALL.md`
12:54, `AGENTS.md` 13:17, `phases/01_discovery.md` 13:17, `prompts/` 12:54-13:18)
and every other worker's output (`evidence/P1-UI/` 13:10-13:11,
`evidence/P1-CATALOG/` 13:02-13:13) still carries a pre-session timestamp, while
only the four assigned paths carry post-session times. Input `.lc` hashes are
byte-identical to those recorded in P1-UI.

Two rough edges found and fixed in the final pass, both re-verified afterwards:
a missing or unreadable path produced a raw `FileNotFoundError` traceback (now a
one-line `error: ...` with exit 1), and a stray `__pycache__/` had been created
in the tool directory by an import (removed; it is not a deliverable).
