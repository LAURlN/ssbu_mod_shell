# Weak Model Task Log

## 2026-09-28: Task 1 — Trace diff tool (PC side)

- **Files created/changed**:
  - `pyra_mythra_clone/tools/trace_diff.py`
  - `pyra_mythra_clone/tools/test_trace_diff.py`
  - `pyra_mythra_clone/tools/fixtures/trace/vanilla.trace.csv`
  - `pyra_mythra_clone/tools/fixtures/trace/clone_identical.trace.csv`
  - `pyra_mythra_clone/tools/fixtures/trace/clone_float_1ulp.trace.csv`
  - `pyra_mythra_clone/tools/fixtures/trace/clone_missing_frame.trace.csv`
  - `pyra_mythra_clone/tools/fixtures/trace/clone_extra_article.trace.csv`
  - `pyra_mythra_clone/tools/fixtures/trace/clone_hitbox_order.trace.csv`
  - `pyra_mythra_clone/tools/fixtures/trace/clone_hitbox_damage.trace.csv`
  - `pyra_mythra_clone/tools/fixtures/trace/clone_speed_energy.trace.csv`
  - `pyra_mythra_clone/tools/fixtures/trace/clone_kind_diff.trace.csv`
  - `pyra_mythra_clone/tools/fixtures/trace/clone_malformed.trace.csv`
  - `pyra_mythra_clone/tools/fixtures/trace/clone_with_comments.trace.csv`

- **Check command**:
  `python -m unittest pyra_mythra_clone/tools/test_trace_diff.py`

- **Actual output**:
```
----------------------------------------------------------------------
Ran 13 tests in 0.030s

OK
```

## 2026-09-28: Task 2 — ACMD inventory

- **Files created/changed**:
  - `pyra_mythra_clone/tools/acmd_inventory.py`
  - `pyra_mythra_clone/reports/acmd-inventory.json`

- **Check command**:
  `python pyra_mythra_clone/tools/acmd_inventory.py`

- **Actual output**:
```
=== File Totals Check ===
Agent 'eflame': disk=430, json=430, match=True
Agent 'eflame_blazepillar': disk=1, json=1, match=True
Agent 'eflame_esword': disk=10, json=10, match=True
Agent 'eflame_firepillar': disk=1, json=1, match=True
Agent 'eflame_windummy': disk=1, json=1, match=True
Agent 'element_diver': disk=21, json=21, match=True
Agent 'elight': disk=436, json=436, match=True
Agent 'elight_beam': disk=1, json=1, match=True
Agent 'elight_bunshin': disk=16, json=16, match=True
Agent 'elight_exprosiveshot': disk=2, json=2, match=True
Agent 'elight_meteor': disk=2, json=2, match=True
Agent 'elight_spreadbullet': disk=2, json=2, match=True
Agent 'elight_windummy': disk=1, json=1, match=True
OVERALL FILE TOTALS: disk=924, json=924, match=True

=== Flagged Functions by Type ===
  call_not_in_other_fighters: 111
  duplicate_function_name: 0
  suspicious_comment: 0
  unbalanced_delimiters: 1
  unresolved_hash: 28
Total flagged functions: 122 / 2048
Output written to: <workspace root>\pyra_mythra_clone\reports\acmd-inventory.json
```
- **Byte-identical check**:
  Running twice produced byte-identical JSON: SHA-256 `001d9b5bee5efcae75c197efa01de71e9b7b9682931c711d9a9a2908e2e3be98`.

## 2026-09-28: Task 3 — Ported ACMD crate (`pyra_mythra_clone/moveset/`)

- **Files created/changed**:
  - `pyra_mythra_clone/moveset/Cargo.toml`
  - `pyra_mythra_clone/moveset/src/lib.rs`
  - `pyra_mythra_clone/moveset/src/names.rs`
  - `pyra_mythra_clone/moveset/src/acmd/mod.rs`
  - `pyra_mythra_clone/moveset/src/acmd/enabled.rs`
  - `pyra_mythra_clone/moveset/src/acmd/cflame.rs`
  - `pyra_mythra_clone/moveset/src/acmd/cflame_blazepillar.rs`
  - `pyra_mythra_clone/moveset/src/acmd/cflame_esword.rs`
  - `pyra_mythra_clone/moveset/src/acmd/cflame_firepillar.rs`
  - `pyra_mythra_clone/moveset/src/acmd/cflame_windummy.rs`
  - `pyra_mythra_clone/moveset/src/acmd/clight.rs`
  - `pyra_mythra_clone/moveset/src/acmd/clight_beam.rs`
  - `pyra_mythra_clone/moveset/src/acmd/clight_bunshin.rs`
  - `pyra_mythra_clone/moveset/src/acmd/clight_exprosiveshot.rs`
  - `pyra_mythra_clone/moveset/src/acmd/clight_meteor.rs`
  - `pyra_mythra_clone/moveset/src/acmd/clight_spreadbullet.rs`
  - `pyra_mythra_clone/moveset/src/acmd/clight_windummy.rs`
  - `pyra_mythra_clone/moveset/src/acmd/clement_diver.rs`
  - `pyra_mythra_clone/reports/acmd-port-fixes.md`
  - `pyra_mythra_clone/QUESTIONS.md`
  - `pyra_mythra_clone/tools/acmd_equivalence.py`

- **Check command 1 (build without features)**:
  `cargo skyline build --release` (in `pyra_mythra_clone/moveset`)

- **Actual output 1**:
```
    Finished `release` profile [optimized] target(s) in 0.21s
```

- **Check command 2 (build with feature `acmd_port`)**:
  `cargo skyline build --release --features acmd_port` (in `pyra_mythra_clone/moveset`)

- **Actual output 2**:
```
   Compiling pmclone_moveset v0.1.0 (<workspace root>\pyra_mythra_clone\moveset)
    Finished `release` profile [optimized] target(s) in 5.28s
```

- **Check command 3 (ACMD equivalence check)**:
  `python pyra_mythra_clone/tools/acmd_equivalence.py`

- **Actual output 3**:
```
ACMD Equivalence Summary:
  Total scripts examined : 2048
  Identical              : 1506
  Fixed (in fixes.md)    : 32
  Excluded (in QUESTIONS): 510
  Unexplained differences: 0

Status: PASS (0 unexplained differences)
```

## 2026-09-28: Task 4 — Scenario checklist (`tests/scenarios.md` & `tools/scenario_coverage.py`)

- **Files created/changed**:
  - `pyra_mythra_clone/tests/scenarios.md`
  - `pyra_mythra_clone/tools/scenario_coverage.py`

- **Check command**:
  `python pyra_mythra_clone/tools/scenario_coverage.py`

- **Actual output**:
```
=== Scenario Coverage Report ===
Total scenarios defined: 46
Total inventory game scripts: 488
Total game scripts covered  : 488
Uncovered game scripts      : 0

Result: PASS (100% coverage, 0 uncovered)
```
