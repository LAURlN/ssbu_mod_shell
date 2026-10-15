# Air side-B vs ground side-B: is air just ground plus a situation branch?

Measured 2026-09-30 by Buffy. Tier **B** (measured offline by the scripts named in
*Reproduction* below, over the shipped dumps).

## Short answer

**Air is the ground script with a landing-dust block deleted. There is no situation branch, no
gravity or kinetic difference, and no differing hitbox anywhere in the three pairs.**

This is a stronger result than the brief anticipated. The saving is not "about half the job" -
it is **13 lines out of 1430 (99.1%)**. The correct scoping conclusion is the opposite of the
"roughly half" guess in one important way: you still have to *register and verify* six scripts,
but the air three are mechanical derivations of the ground three, so only three scripts need
authoring and the other three need a delete-and-check pass.

| pair | ground lines | air lines | saved | air as % of ground |
| --- | --- | --- | --- | --- |
| `SpecialS1` / `SpecialAirS1` | 531 | 529 | 2 | 99.6% |
| `SpecialS2` / `SpecialAirS2` | 482 | 477 | 5 | 99.0% |
| `SpecialS32` / `SpecialAirS32` | 417 | 411 | 6 | 98.6% |
| **total** | **1430** | **1417** | **13** | **99.1%** |

Line counts are whitespace-normalised and symbol-normalised (see *Method*).

## Method, and what was controlled for

Both dumps are machine-converted, so two non-gameplay differences had to be removed before the
diff meant anything:

1. the function symbol (`specials1` vs `specialairs1`) - normalised away;
2. indentation, which the converter emits inconsistently - whitespace stripped.

After normalisation, for **each of the three pairs**, the function sets are equal (same four
functions: `game_`, `effect_`, `sound_`, `expression_`), and:

| function kind | ground | air | verdict |
| --- | --- | --- | --- |
| `game_` (hitboxes, timers, flags) | 122 | 122 | **identical** |
| `sound_` | 1090 | 1090 | **identical** |
| `expression_` | 54 | 54 | **identical** |
| `effect_` | 152 | 139 | **differs - the only difference in the whole corpus** |

Per function, the `game_`, `sound_` and `expression_` bodies are *byte-identical* after
normalisation, and their brace-depth profiles match line for line. Only `effect_` differs.

**Control against the converter-artefact reading** (AGENTS.md §F: a line present in one dump and
absent in the other may be a dropped call). Two checks argue against that here:

- *Subsequence test.* For each pair, the air `effect_` function is a strict **subsequence** of the
  ground one - same lines, same order, nothing reordered, nothing added. A converter that dropped
  arbitrary calls mid-block would not reliably produce a clean subsequence.
- *Insert count is zero.* The diff yields **delete-only** for all three pairs: 2 / 5 / 6 deletions
  and **0 insertions**. Air never has a line ground lacks, which is what a genuine ground-only
  feature (landing dust) predicts and what a lossy converter would not predict.

## Per-pair diffs

### `SpecialS1` vs `SpecialAirS1` - identical modulo situation

`game_`, `sound_`, `expression_` identical. `effect_` drops two lines, and **the frame timeline is
unchanged** (`6, 9, 6, 18, 26` in both):

```
- macros::LANDING_EFFECT(agent, Hash40::new("sys_atk_smoke"), Hash40::new("top"), 0,0,0,0,0,0, 0.9, 0,0,0,0,0,0, false);
- macros::LANDING_EFFECT(agent, Hash40::new("sys_atk_smoke"), Hash40::new("top"), 0,0,0,0,0,0,   1, 0,0,0,0,0,0, false);
```

Both are single statements deleted from inside an existing `if (is_excute)` block - the air
version still opens and closes the block, it just has nothing in it. The 6 ATTACK lines are
identical between the two (verified line-by-line), and all 6 carry
`*COLLISION_SITUATION_MASK_GA` in both.

### `SpecialS2` vs `SpecialAirS2` - differs: one whole frame block removed

`game_`, `sound_`, `expression_` identical. `effect_` drops 5 lines, and here **the timeline does
change**: ground `8, 9, 10, 12, 29, 30, 8, 12, 15`, air `8, 10, 12, 29, 30, 8, 12, 15`. Frame 9.0
is absent from air:

```
- frame(agent.lua_state_agent, 9.0);
- if macros::is_excute(agent) {
-     macros::LANDING_EFFECT(agent, Hash40::new("sys_atk_smoke"), Hash40::new("top"), 0,0,0,0,0,0, 0.9, 0,0,0,0,0,0, false);
- }
- macros::LANDING_EFFECT(agent, Hash40::new("sys_atk_smoke"), Hash40::new("top"), 0,0,0,0,0,0, 0.9, 0,0,0,0,0,0, false);
```

The whole `frame(9.0) { if (is_excute) { LANDING_EFFECT } }` block is removed and the remaining
frame numbers are **not renumbered** - air goes 8.0 then 10.0. In ACMD `frame(n)` is absolute, so
this is a timing-preserving deletion, not a shift. There are two `sys_atk_smoke` statements in the
delta because ground has that block plus a second identical one elsewhere; the second occurrence
is the separately-dropped single statement.

This is the one pair where a translator must be careful: the deletion is a **block**, so the
port must drop the whole `frame`/`wait` step, not just the effect call. Getting this wrong leaves
a `frame(9.0)` advance that air does not have.

### `SpecialS32` vs `SpecialAirS32` - differs: two blocks removed, one is not landing dust

`game_`, `sound_`, `expression_` identical. `effect_` drops 6 lines, timeline ground
`21, 22, 26, 28, 30, 34, 40` vs air `21, 22, 28, 30, 34, 40` - frame 26.0 removed:

```
- macros::LANDING_EFFECT(agent, Hash40::new("sys_down_smoke"),  ..., false);      // single statement
- }
- frame(agent.lua_state_agent, 26.0);
- if macros::is_excute(agent) {
-     macros::LANDING_EFFECT(agent, Hash40::new("sys_whirlwind_r"), ..., false);
-     macros::LAST_EFFECT_SET_RATE(agent, 0.8);
- }
```

**This pair is not purely landing dust.** The `frame(26.0)` block is dropped *together with*
`macros::LAST_EFFECT_SET_RATE(agent, 0.8)`, which is an effect-rate call, not a landing effect.
In ACMD `LAST_EFFECT_SET_RATE` is positional: it sets the rate of the most recently spawned
effect, so dropping it changes what the preceding `sys_whirlwind_r` effect does when the *next*
one spawns. A port that deletes only `LANDING_EFFECT` and keeps `LAST_EFFECT_SET_RATE` (or keeps
the frame step) will not match air.

## Classification of every differing line

All 13 differing lines across the three pairs:

| category | count | lines |
| --- | --- | --- |
| landing / ground-only effect | 7 | 4x `LANDING_EFFECT sys_atk_smoke` (S1 x2, S2 x2), `LANDING_EFFECT sys_down_smoke` (S32 x1), `LANDING_EFFECT sys_whirlwind_r` (S32 x1) |
| block scaffolding of a deleted block | 4 | `frame(...)`, `if is_excute {`, `}` x2 (S2 x3, S32 x1 beyond the above) |
| non-landing effect control | 1 | `LAST_EFFECT_SET_RATE(agent, 0.8)` (S32) |
| **situation mask** | **0** | - |
| **gravity / kinetic** | **0** | - |
| **clip name** | **0** | - |
| **differing hitbox** | **0** | - |

**Zero situation-mask changes.** Every ATTACK line in all six files uses
`*COLLISION_SITUATION_MASK_GA` (6 in S1/S1air, 1 in S2/S2air, 8 in S32/S32air) - ground *and* air.
There is no `MASK_G`-only or `MASK_A`-only hitbox anywhere in the side-B corpus. That is the
direct measurement behind "air is not a separate hitbox set".

**Zero gravity/kinetic calls.** Scanning all six files for `GravityModule`, `set_gravity`,
`KineticModule`, `FallSpeed`, `fall_speed`, `TerminalVelocity`, `get_fall_speed`,
`set_fall_speed`, `Air::`, `SITUATION_KIND`: no hits in any file, ground or air. So the
ground/air kinetic difference for this move is **not in the ACMD at all** - if it exists, it is in
the NRO status code, not the script. (Tier **D**: that this is a complete absence of situation
handling in these scripts follows from the grep, but I did not verify that the engine does not
apply one.)

## Unique lines to translate

Counting **line occurrences** (translation cost tracks emitted lines, not distinct strings - the
sound tables repeat near-identical lines that each need emitting):

| scope | occurrences |
| --- | --- |
| ground three scripts (the authoring job) | 1430 |
| air three scripts (derivation job) | 1417 |
| **air lines that are a copy of a ground line** | **1404 (99.1%)** |
| **air lines needing a human decision** | **13** |

Practical scoping:

- Author **3** scripts (`SpecialS1`, `SpecialS2`, `SpecialS32`), ~1430 lines.
- Derive **3** air scripts by deleting 2 / 5 / 6 lines, then diff against the ground translation
  to confirm zero insertions.
- Distinct-line counts (72 / 63 / 88 per pair; 153 union across all three) are **not** a work
  estimate, but they show how much boilerplate the sound tables share - useful if the port can
  emit them from a table rather than line by line.
- 1090 of the 1430 lines (76%) are `sound_`. If sounds are handled as data rather than emitted
  per line, the hand-written surface drops to ~340 lines. Worth deciding before starting.

## Scope notes for the translator

- `S32`, not `S3`. The side-B third hit has **two** dump files: `SpecialS3.txt` /
  `SpecialAirS3.txt` (47 lines each, **zero** ATTACK lines, and `effect_`/`game_`/`sound_`
  depth-profiles identical between them) and `SpecialS32.txt` / `SpecialAirS32.txt` (420 / 414
  lines, 8 ATTACK lines each). Per `SOURCE_STATUS.md`, `SpecialS3.txt`'s zero ATTACK lines are a
  dump artefact, not a design fact - so `S32` is the file with the real third hit and `S3` is the
  same move's short/stub script. **The status table registers `ATTACK3` and `ATTACK3_APPEND`; do
  not treat `SpecialS3` as evidence that the third hit has no hitboxes.** Which of `S3`/`S32` maps
  to `ATTACK3` vs `ATTACK3_APPEND` is **not established** here.
- There are **no** air variants of the other side-B scripts: no `SpecialAirS1Default`,
  `...usen`, `SpecialAirSHoldM`, `...Max`. `SpecialAirSHold.txt` (21 lines) and
  `SpecialAirSStart.txt` (5 lines) do exist and have ground counterparts
  (`SpecialSHold` 25 lines, `SpecialSStart` 5 lines) - so those two pairs are **not** covered by
  the "air = ground minus dust" result and need their own diff if the port needs them. All of
  these are small (≤27 lines) and contain zero ATTACK calls.
- `SpecialS1usen`, `SpecialS2usen`, `SpecialS32usen` (25-27 lines, zero ATTACK) and the `Default`
  siblings (17-27 lines, zero ATTACK) are additional side-B scripts not covered by the three pairs
  compared here. Whether the port needs them is not established.
- Per `refs/brave_special_s/status_table.txt`, all six of these clips are reached from the same
  six statuses; there is no air-specific status. Consistent with this measurement.

## Not established

- Which physical clip each of `SpecialS3` / `SpecialS32` serves, and whether `ATTACK3` and
  `ATTACK3_APPEND` use one each. Needs the motion list, not the ACMD dumps.
- The `S1Default` / `S1usen` / `SHold*` / `SStart` ground-air relationship (see above).
- Anything about runtime behaviour. These are text dumps; a landing effect that appears in a
  ground script cannot be shown to matter on hardware from this evidence. Tier A would require a
  console run.
- Whether the *engine* applies a situation branch on top of these scripts. The grep only shows the
  scripts contain none.

## Reproduction

Scripts, in `scratch/2026-09-30_flag_success_sp/`:

| script | what it establishes |
| --- | --- |
| `acmd_diff.py` | normalised line diff + coarse classification |
| `acmd_subset.py` | subsequence test per function; enumerates ground-only lines |
| `acmd_frames.py` | `frame()`/`wait()` timeline comparison per function |
| `acmd_balanced.py` | brace-depth profile comparison (artefact control) |
| `acmd_scope.py` | translation-size accounting and the gravity/kinetic/hitbox scans |

```
toolchains/py312/python.exe scratch/2026-09-30_flag_success_sp/acmd_subset.py
toolchains/py312/python.exe scratch/2026-09-30_flag_success_sp/acmd_scope.py
```

**Same AGENTS.md rule 3 caveat as the previous task in this session:** these scripts live in
scratch, which is deleted after 30 days, and rule 3 wants them promoted to `tools/` with a
docstring and a smoke test. The brief restricted writes to the named output file, so promotion was
deliberately skipped and is an open item.
