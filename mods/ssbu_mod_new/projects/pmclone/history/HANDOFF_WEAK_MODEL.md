# Handoff for a cheaper model — Pyra/Mythra clone

Written 2026-09-28. Read `ASSESSMENT.md` first (10 minutes). This file gives you
self-contained tasks that can be checked automatically. Anything not listed here
belongs to a capable model. Your job is to make the high-volume parts ready so the
hard parts go faster, **without** introducing anything that changes how the clone plays.

## Ground rules (read these twice)

1. **Exactness is the product.** The clone must play *exactly* like the original.
   Never "improve", "clean up", reorder, round or simplify game logic or numbers.
   If a dumped script looks wrong, **flag it; do not fix it by guessing.**
2. **Stay in your lane.** Do not edit: `upstream/`, `runtime/`, `native/`,
   `tools/namespace_modules.py`, `tools/extract_missing.py`, anything under
   `../mod_files/`, or any file containing memory offsets (`0x…` addresses used
   as code locations). Do not add Skyline hooks or `from_offset` functions.
3. **Nothing goes onto the Switch.** Never write to the SD card (usually `sd:/`).
   Never ask the user to install a build. A capable model reviews first.
4. **No claims without checks.** Each task below has a "Done when" section. If you
   could not run a check, say so in your report. Do not say "should work".
5. **When unsure, stop and write it down** in `QUESTIONS.md` (create it if needed:
   task, file, line, question, what you considered). Then move to the next item.
6. Environment: Windows, Python **3.8** (no `match`, no `dict | dict`, no
   `str.removeprefix`), standard library only unless a task says otherwise.
   Rust via `cargo skyline build --release`. Work from
   `<workspace root>`.
7. Finish each task with a short entry in `reports/weak-model-log.md`: date, task,
   files created/changed, the check command, and its actual output (last lines).

Clone names used throughout (provisional, from `project.json`):
Pyra `eflame` → `cflame`, Mythra `elight` → `clight`, shared `element` → `clement`.
Article agents keep their suffix: `eflame_esword` → `cflame_esword`, etc.
Keep all of these names in **one** table per deliverable so they can be changed in one place.

---

## Task 1 — Trace diff tool (PC side, no console needed)

This is the most important task: it is what later proves "exactly the same".
A capable model will write the Switch plugin that produces the traces. You write the
tool that compares them. The format is fixed here, so both sides agree.

### Trace format (`.trace.csv`)

UTF-8 CSV, header row, one row per fighter object per game frame. First lines may be
comments beginning with `#` (metadata: `# build=…`, `# scenario=…`, `# fighter=…`).

| column | type | notes |
| --- | --- | --- |
| `frame` | int | global frame counter since the recording started |
| `slot` | int | player entry id 0–7 |
| `object` | str | **Opaque identifier; compare as a string, do not parse or validate it.** The recorder writes `fighter:<name>` (e.g. `fighter:elight`; Pyra and Mythra share a slot, so both appear every frame) and `article:<name>#<n>` (e.g. `article:elight_esword#0`, `#n` numbers several instances of the same article). |
| `kind` | int | fighter/weapon kind. **Identity field** (differs between vanilla and clone) |
| `status` | int | status kind |
| `situation` | int | ground/air/cliff |
| `motion` | hex str | motion hash40, `0x` + 10 hex digits |
| `motion_frame` | float | |
| `motion_rate` | float | |
| `pos_x`, `pos_y` | float | |
| `lr` | float | facing, ±1 |
| `speed` | str | `name=x:y;name=x:y…`, one entry per enabled kinetic energy, sorted by name |
| `damage` | float | percent |
| `hitstop` | int | remaining hitlag frames |
| `hitboxes` | str | `;`-separated active hitboxes, each `id/part/damage/angle/kbg/fkb/bkb/size/x/y/z/x2/y2/z2`, sorted by id then part; empty if none |
| `work` | str | `key=value;…` for a selected WorkModule set, sorted by key |

Floats are written with `repr`-exact precision (the plugin will print the full value).
**Compare floats exactly by default** (`--float-tol` defaults to 0).

**Spec update, 2026-09-28, matching the recorder that now exists (`trace/README.md`):**
- Compare every field as a **string first**; only if the strings differ and
  `--float-tol` > 0, compare numerically. (The recorder can print `NaN` and `-0`;
  `NaN` must equal `NaN`, and `-0` vs `0` counts as a difference at tol 0.)
- `work` omits keys whose value is `0`. A key present in one row and missing in
  the other is a difference, reported like `work INT_FOO 3 != (absent)`.
- `hitstop` is currently `1`/`0` (in hitlag or not), not a frame count.
- `hitboxes` field `part` is always `0`; extra hitbox details are in `work` as `hb<id>.<field>` keys.
- Lines starting with `#` can also appear before the header (metadata).

### What to build

`tools/trace_diff.py`:

```
python pyra_mythra_clone/tools/trace_diff.py VANILLA.trace.csv CLONE.trace.csv
    [--ignore kind] [--float-tol 0] [--max-report 50] [--json out.json]
```

- Align rows by `(frame, slot, object)`. Missing/extra rows are differences.
- `kind` is ignored by default (identity field); other `--ignore` columns are opt-in.
- Compound fields (`speed`, `hitboxes`, `work`) are parsed and compared per item,
  so the report says e.g. `frame 212 slot 0 fighter: hitboxes id=1 damage 6.0 != 6.5`.
- Output: `IDENTICAL` and exit 0, or the **first diverging frame** prominently, then
  up to `--max-report` differences, and exit 1. Exit 2 for malformed input,
  with the line number.
- Optional `--json`: machine-readable list of differences.

`tools/test_trace_diff.py` (unittest): at least these cases —
identical files; float differs by 1 ulp (must be reported at tol 0, not at tol 1e-6);
missing frame; extra article row; hitbox order differs but content is equal (must be
IDENTICAL); hitbox damage differs; speed energy present in one only; `kind` differs
only (IDENTICAL by default; reported when the user passes `--ignore ""`); malformed row → exit 2; comment lines ignored.
Put small fixture files under `tools/fixtures/trace/`.

**Done when:** `python -m unittest pyra_mythra_clone/tools/test_trace_diff.py` passes,
and the log entry includes that output.

---

## Task 2 — ACMD inventory

Source (read only): `SSBU-Dumped-Scripts-main/smashline/lua2cpp_{eflame,elight,element}/<agent>/*.txt`.
Each file holds one or more `unsafe extern "C" fn <category>_<name>(agent: &mut L2CAgentBase)`
functions, where category is `game`, `effect`, `sound` or `expression`.

Write `tools/acmd_inventory.py` → `reports/acmd-inventory.json`:

- Per agent: file count, and per file the function names with category and line count.
- A `flags` list per function for things a human must review:
  - `Hash40::new_raw(` (unresolved hash),
  - a call to a function or macro that does not appear anywhere in the
    `SSBU-Dumped-Scripts-main/smashline` folder for another fighter (possible dump error),
  - unbalanced braces/parentheses,
  - `// ` comments containing `TODO`, `unknown` or `error`,
  - duplicate function names across files of the same agent.
- Totals per agent and overall.

**Done when:** the JSON's file totals equal the file counts on disk (print both
from the script), running it twice gives byte-identical JSON, and the log entry lists
the totals and the number of flagged functions per flag type.

---

## Task 3 — Ported ACMD crate (feature-gated, off by default)

Goal: the clone's own copy of every ACMD script, ready to take over one script at a
time **after** traces prove each one equal. Nothing in this crate may run by default.

Create `pyra_mythra_clone/moveset/` as a Skyline cdylib crate:
- Copy the dependency lines exactly from
  `upstream/clone_engine/custom_fighters/template_v2/Cargo.toml` (same revisions),
  minus `the_csk_collection_api` and `param_config`, which are not needed yet.
- `src/names.rs`: the one table mapping vanilla agent → clone agent name.
- One module per agent (`src/acmd/cflame.rs`, `src/acmd/cflame_esword.rs`, …),
  containing the functions copied from the dump **verbatim**.
- `src/acmd/mod.rs`: an `install()` that registers every function with
  `smashline::Agent::new(<clone name>).game_acmd/effect_acmd/sound_acmd/expression_acmd(...)`,
  using the script name derived from the function name (`game_specials` → `"game_specials"`).
- `src/lib.rs`: `#[skyline::main(name = "pmclone_moveset")]` whose main function calls
  `acmd::install()` **only** under `#[cfg(feature = "acmd_port")]`. Default features: none.
- Per-script enabling list: `src/acmd/enabled.rs` with an empty allow-list. Registration
  skips anything not in the list, even with the feature on. (Scripts get enabled one at a
  time by whoever runs the trace comparison.)

Compile fixes: you will need some (the dump author says the dumps are "mostly
usable"). Allowed fixes are purely syntactic or import-related: missing `use`,
type annotation, `as` casts the compiler demands, a macro name that exists under a
different path. **Every** fix is recorded in `reports/acmd-port-fixes.md` as
`agent / function / before / after / reason`. Anything that would change a number,
a frame, a condition or the order of calls is **not allowed**: comment the whole
function out of registration, add it to `QUESTIONS.md`, and keep going.

Write `tools/acmd_equivalence.py`: for each ported function, normalise whitespace
and compare its token stream to the dump's. The only allowed differences are the
entries in `acmd-port-fixes.md`. Report `n identical / n fixed / n excluded`.

**Done when:**
`cargo skyline build --release` succeeds in `pyra_mythra_clone/moveset` **both**
without features and with `--features acmd_port`, the equivalence script reports
0 unexplained differences, and the log entry has both build tails and the script
summary. Do not package or deploy the NRO.

---

## Task 4 — Scenario checklist

`tests/scenarios.md`: the list of recorded-input scenarios used for trace comparison
(the recordings themselves will be made on the console later).

Each scenario: id (`S-001`…), fighter (Pyra/Mythra/both), stage (Training, Final
Destination form), start (position, percent, facing, grounded/air), inputs in plain
words with frame counts, what it covers (script names from Task 2), and a
`needs:` field for special setup (CPU dummy action, item, ledge…).

Coverage requirements:
- every `game_` script from `reports/acmd-inventory.json` appears in the `covers`
  of at least one scenario;
- swap (down special) in both directions from: standing, running, jumping, falling,
  landing lag, shield, ledge hang, during a move's endlag;
- Final Smash for each; respawn; ledge get-up variants; grab/pummel/all throws;
  a hit taken during each special; Kirby inhaling each and using the copy ability.

Write `tools/scenario_coverage.py` that parses `tests/scenarios.md` and lists any
`game_` script not covered.

**Done when:** the coverage script prints `0 uncovered`, and the log entry says so.

---

## Not your tasks (leave these to a capable model)

Clone Engine changes and pair support; the crash chain from `mod_files/mgw_standalone`;
anything in `main` (offsets, disassembly, kind checks); the trace **plugin** on the
Switch side; decompiling status scripts; relocating native code; asset/param
identity routing; deciding when a ported script gets enabled.

Later, once a capable model has written decompiled status scripts and one reviewed
worked example of a port, status-script transliteration will be handed down with
the same rules as Task 3 (verbatim, feature-gated, trace-verified).

## Report back

When you stop, append to `reports/weak-model-log.md` a summary: which tasks are
done (with check outputs), which are partial and why, and everything added to
`QUESTIONS.md`. Do not edit `HANDOFF.md` or `ASSESSMENT.md`.
