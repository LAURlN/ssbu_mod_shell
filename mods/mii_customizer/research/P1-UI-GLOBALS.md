# P1-UI-GLOBALS - do the shared Lua modules define the editor's counts/flags?

2026-10-04. Space Bunny Alpha worker, follow-up to P1-UI-DECODE. Bounded read-only
analysis. No emulator, no console, no commits, no production code.

**Status: PARTIAL.** The three recommended modules were read in full and **none of
them defines any of the four names** — not as a value, not as a write, not even as
a read. The searched set and the exact boundary are in section 5. This is a real
negative result, not a failed search.

## 1. Inputs (all read-only, hashes recorded)

Three chunks only, extracted from `gamedata/ssbu-13.0.4/data.arc` into
`gamedata/mii_customizer/P1-UI-GLOBALS/`:

| ARC path | sha256 | bytes |
|---|---|---|
| `ui/script/common/ui_common.lc` | `349448a926c74fd0cba3ea5ccdd1d9ea7ee650ed45fca8d23f29ca313cefd76f` | 3874 |
| `ui/script/common/state_function.lc` | `4fee95bbcc013bfbc72463ddc62d9a8247c7b02c7bf0297d608bacb4203c8810` | 1896 |
| `ui/script/menu/chara_make/make_mii_utility.lc` | `ff62bea184d129d9bd94137a92ba910314f3e9ef61bb2b663c2aa698d7109f25` | 3263 |

The printed hashes from `arc-extract` matched an independent `sha256sum` pass
(`evidence/P1-UI-GLOBALS/input_hashes.txt`), so the extract is byte-exact.

**Paths were found in the archive index, not assumed from `require` names**, as the
prompt required. `grep` over `mods/ssbu_mod_new/dumps/decoded/arc_files.tsv` gives
exactly one hit each, at index lines 42448, 42450 and 842. In particular the
require name `common/ui_common` maps to `ui/script/common/ui_common.lc`; the
`common/` prefix in the require name is **not** an ARC path prefix, so guessing
would have been wrong.

Commands: `evidence/P1-UI-GLOBALS/extract_output.txt`. Tool reused read-only, no
new parser, nothing installed.

## 2. Structural verification

`lua53_inspect verify` exits **0** on all three, with exact byte consumption — the
load-bearing check, since a desynchronised walk would leave trailing bytes:

| chunk | protos | instructions | consumed |
|---|---|---|---|
| `ui_common.lc` | 23 | 345 | 0xf22 / 0xf22 |
| `state_function.lc` | 16 | 184 | 0x768 / 0x768 |
| `make_mii_utility.lc` | 5 | 134 | 0xcbf / 0xcbf |

Proto counts are from `summary` (`summary_all.txt`), **not** from the `constants`
dump: a prototype with zero constants does not appear in `constants`, which
undercounted `ui_common` by 1 (`main.p3`, `consts=0`) and `state_function` by 1
(`main.p0`, `consts=0`). Recorded because the error was invisible in the output
and would have shipped as a wrong number.

All three are Lua 5.3, 4-byte float32, stripped (0 upvalue names). The tool's
format notes from P1-UI-DECODE applied unchanged. Evidence:
`verify_all.txt`, `header_*.txt`, `constants_*.txt`, `dis_*.txt`.

**I ruled out a false negative before believing it.** The same query run against the
known-positive patch chunk reports `IS_SKILL_EDITABLE` 4x and `IS_READ_ONLY` 5x,
matching P1-UI-DECODE exactly (`xref_control_known_positive.txt`). A control that
finds the names when they are present makes the zero result meaningful.
`xref_baseline_chunks_recheck.txt` reproduces P1-UI-DECODE's per-chunk counts on
the two already-extracted actor chunks, so the baseline is stable.

## 3. Result: zero definitions, and a positive control for what a definition looks like

`xref` for all four names returns **0 occurrences in all three chunks**
(`xref_globals.txt`). They do not appear even as reads.

This is not an empty chunk though, and that matters. `make_mii_utility.lc` contains
**32 `SETTABUP` instructions writing 33 named globals into `_ENV`** — real global
definitions, exactly the shape we were hunting. They are all camera/pose constants
(`F_/S_/G_CAMERA_DEFAULT_POSITION_*`, `*_RIGHT_SIDE_0/1_*`, `HAT_SELECT_CAMERA_*`)
plus `MII_FIGHTER_DEFAULT_ROTATE`. Full list with instruction offsets:
`global_definitions_inventory.txt`. **Not one of the four target names is among
them.**

`ui_common.lc` and `state_function.lc` contain **0 `SETTABUP`** at all. Both are
plain module constructors: they build a local table and `setmetatable {__index=...}`
it, then return it (`ui_common` `main` pc3-50; `state_function` `main` pc0-39).
Their constants are helper *function names* (`wait_animation`, `fade_out`,
`clamp`, `setup`, `set_callback`, `advance`, …), stored into a returned table via
`SETTABLE` — **local table fields, not globals**. Confusing these two mechanisms is
the easiest way to produce a false "defined here" claim, so it is worth stating
plainly: every name in those two chunks is a module member, not an `_ENV` entry.

`dis_make_mii_utility.txt` also shows the genuine assignment form this project
would use, e.g. `main` pc2:
`SETTABUP A=0 B=256 C=257  up[0][K[0]=MII_FIGHTER_DEFAULT_ROTATE] := K[1]=60.0`.

## 4. The corroborating observation that does carry weight

Comparing *known* host-provided globals against the four unknowns in the same three
chunks (`host_globals_read_vs_write.txt`):

| name | `GETTABUP` reads | `SETTABUP` writes |
|---|---|---|
| `MII_TYPE_GUNNER` | 3 | 0 |
| `MII_TYPE_SWORDSMAN` | 3 | 0 |
| `FadeManager` | 16 | 0 |
| `Randomizer` | 2 | 0 |
| `FrameSkipManager` | 2 | 0 |
| `HowToPlayUtility` | 2 | 0 |
| `SKILL_COMMAND_NUM` | 0 | 0 |
| `SPECIAL_SKILL_NUM` | 0 | 0 |
| `IS_READ_ONLY` | 0 | 0 |
| `IS_SKILL_EDITABLE` | 0 | 0 |

`MII_TYPE_GUNNER` is unambiguously host-injected — no shipped Lua chunk could
plausibly own the game's own fighter-type enum — and these three chunks read it
three times while never writing it. The four unknowns behave **identically** in
these files: read-only, never written. That is consistent with all four being
host-injected globals rather than Lua-owned definitions (tier **D**, an inference
from pattern, not proof).

**This does not prove native injection.** The prompt says so explicitly and the
evidence agrees: absence of a write here only excludes these three files. Another
shipped `.lc` could still assign them, and 74 further `ui/script/*.lc` files remain
unextracted. What it does establish, at tier B, is the concrete fact that these
three modules are **not** the source, which is the answer P1-UI-DECODE asked for.

I did **not** follow the "definition points to another required module" step,
because nothing here defines anything to follow, and none of the three chunks
contains a `require` string constant at all (checked in `constants_*.txt`). That
trigger never fired, so 3 of the 5 permitted inputs were used. Stopping here is the
prompt's stop condition, not an early exit.

## 5. Exact boundary — what remains unsearched

Searched (3 inputs): `ui/script/common/ui_common.lc`,
`ui/script/common/state_function.lc`, `ui/script/menu/chara_make/make_mii_utility.lc`.

Not searched, so not excluded:
- the other 5 `chara_make` chunks — `make_mii_body_actor.lc`, `make_mii_hat_actor.lc`,
  `make_mii_hat_body_layout.lc`, `make_mii_select_actor.lc`, `make_mii_voice_actor.lc`
  (list: `arc_index_chara_make.txt`);
- 69 further `ui/script/**/*.lc` files (77 total in the archive).

Most promising untested hypothesis (tier D, **not** tested here): a `ui/script/common/`
"defines"-style chunk that sets up UI constants once, or the `make_mii_select_actor.lc`
/ `make_mii_body_actor.lc` siblings that host the per-slot selectors. Cheap to test
the same way: extract, `verify`, `xref`.

## 6. What this permits us to change in Lua

- **Nothing about the move counts or editability flags.** No shipped Lua we have read
  owns `SKILL_COMMAND_NUM`, `SPECIAL_SKILL_NUM`, `IS_READ_ONLY` or
  `IS_SKILL_EDITABLE`. We cannot change them by editing a UI script, and we must not
  plan on setting them from a mod script that expects them to be Lua-owned.
- **Still fully moddable in Lua:** the *control flow* around them. The patched
  `make_mii_edit_actor.lc` already proves a flag read can be made to gate behaviour
  (P1-UI-DECODE section 3), and `make_mii_utility.lc` proves shipped Lua *does*
  write `_ENV` globals when it owns them. So overriding an editability check by
  changing the code that consumes it remains open.
- **`make_mii_utility.lc` is a working precedent** for a chunk that sets globals at
  load time: 33 constants written to `_ENV` from `main`, no metatable indirection.
  If a Lua-side override is ever wanted, this is the shape to copy — and the file is
  a script, so it is replaceable. Tier B for the mechanism, tier D for suitability.
- **Naming caveat for implementation:** `ui_common`/`state_function` export *module
  members*, so `require` results are tables. Do not assume a require'd module can
  define a bare global; in these two it cannot.

## 7. One precise unresolved question for implementation

> If `SKILL_COMMAND_NUM` and `SPECIAL_SKILL_NUM` are host-injected `_ENV` globals
> rather than Lua-owned constants, does the host re-seed them per state entry, or
> only at UI-script load? That decides whether a mod can override the slot count by
> assigning the global **once** at script load, or must instead intercept the
> consumers (`FORPREP` loops in `make_mii_special_actor.lc` `main.p2/p3/p4`, the
> `1..SKILL_COMMAND_NUM` reads at `main.p14` pc9/pc35 and `main.p15` pc59).

That is a single question with two testable answers, it is answerable offline from
the already-extracted actor chunks plus one more `ui/script/common/` chunk, and it
is the difference between "override a global" and "patch the loops". It does not
touch identity, save data or native binding, so P1-ID is unaffected.

## 8. Evidence tiers

| tier | claim |
|---|---|
| **B** verified offline | the three sha256 hashes; exact byte consumption on all three; the zero-occurrence xref for all four names; the same query finding 4/5 occurrences in the known-positive control; 32 `SETTABUP` / 33 globals in `make_mii_utility`, 0 `SETTABUP` in the other two; the read/write table in section 4; no `require` constant in any of the three |
| **C** pinned source | the chunk/opcode format, inherited from the tool's v5.3.6 pinning (not re-derived here) |
| **A** console | **none.** No run was performed. |
| **D** hypothesis | that the four names are host-injected like `MII_TYPE_GUNNER`; the section 5 ranking of untested chunks; that a Lua-side override is a viable route at all |

Runtime behaviour is **unverified**. No editor was opened; this is bytecode on disk.

## 9. One correction to my own first pass

My first read/write count script grepped for `[NAME]` and returned 0 for everything,
including names that are plainly present. The tool renders constants as `K[n]=name`,
not `[name]`. The all-zero table was a broken pattern, not a finding. Re-run with
`-F "$name]"` (`host_globals_read_vs_write.txt`) and the numbers above are correct.
Recorded because the broken version would have "confirmed" a false conclusion.

## Task summary

**P1-UI-GLOBALS: PARTIAL** — the recommended modules are conclusively **not** the
source; the searched set is closed at 3 chunks and section 5 is the exact boundary.

Changed files, all inside this mod's assigned paths:
- `research/P1-UI-GLOBALS.md` (this report)
- `evidence/P1-UI-GLOBALS/` — 19 files: `extract_output.txt`, `input_hashes.txt`,
  `verify_all.txt`, `summary_all.txt`, `xref_globals.txt`, `xref_control_known_positive.txt`,
  `xref_baseline_chunks_recheck.txt`, `global_definitions_inventory.txt`,
  `host_globals_read_vs_write.txt`, `arc_index_chara_make.txt`,
  `header_{ui_common,state_function,make_mii_utility}.txt`,
  `constants_{ui_common,state_function,make_mii_utility}.txt`,
  `dis_{ui_common,state_function,make_mii_utility}.txt`

Observed checks (exit statuses captured directly, not through a filter):
`verify` exit 0 on all three chunks; `summary` exit 0; `xref` exit 1 on all three,
which is this tool's documented "name not found" status, not a crash. Python 3.12.3,
stdlib only.

Untouched: `STATUS.md`, `CHANGELOG.md`, `CURRENT_INSTALL.md`, other workers' paths,
`mods/ssbu_mod_new/`, shared `tools/`, UI assets, saves, SD card. No new parser, no
dependency installs, no emulator, no commits, no native tracing, no identity work.

Next step, one bounded extraction: pull the remaining `ui/script/common/*.lc`
chunks and run the identical `verify` + `xref` on the four names. If they are also
absent, the "host-injected" reading becomes the working assumption and phase 1 should
stop searching Lua and record that boundary rather than escalate to native RE on
the strength of two offline reports.