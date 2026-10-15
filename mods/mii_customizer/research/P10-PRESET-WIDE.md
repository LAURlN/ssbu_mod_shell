# P10-PRESET-WIDE - wider character presets (up to 48 float fields) and the list file

Task: `prompts/P10-PRESET-WIDE.md`. Date 2026-10-05. Worker: Space Bunny Alpha.
Status: **DONE** (Parts 1-4 complete, check script green, see Summary).

Paths are relative to `mods/mii_customizer/` unless marked workspace-relative.

Everything here is offline measurement: **B**. Nothing is **A**; no console, no
emulator, no game run, no plugin run, no SD access. **A static site proves the
engine *can* ask for a field through the hook, not that it does during play** --
the plugin log is what answers that, per field, after the console test.

## Result in short

* **114 of 369** fighter_param fields qualify (float, at least one +0x270
  site with x2 == 0, value differs between fighters); **41 chosen** for the
  wide preset: the existing ten first, unchanged and in order, plus 31 ranked
  by movement impact. 69 qualifying fields flagged for coordinator review, 4
  excluded (no hash-verified name).
* `gamedata/mii_customizer/P10-PRESET-WIDE/presets_wide.txt` - 94 presets,
  41 fields each, 41 distinct hashes, 89 003 bytes; **accepted by the plugin's
  own parser** (P7 host-side checker: `state=ok rejected=0 skipped=0`).
* `list.txt` - format `mc_list 1`, 87 entries, 2 600 bytes, 7 fighters left
  out with recorded reasons.
* Default run still byte-identical: `presets.txt` sha256
  `f6acbba17d510aae0f0a2cc49cc5417287d4f0d0a8428dbf52d3ca4505865c0d`.
* Check script `evidence/P10-PRESET-WIDE/check_preset_wide.py`: **29 PASS,
  0 FAIL**, exit 0 (regeneration compare, contract A/F models, list/preset
  cross-references, four negative controls, P7 parser).

## 1. Inputs

* `gamedata/ssbu-13.0.4/main.bin` - 13.0.4 executable, sha256
  `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`
  (pinned in the scanner; unchanged).
* `gamedata/mii_customizer/P6-PRESET-DATA/fighter_param_full.json` - the
  94-row table, 369 fields per row, sha256
  `9188c7680a86787feaee12f9537157dda64e89c37c87124af2c0bbd8196d70df`
  (pinned; unchanged).
* `gamedata/mii_customizer/P6-PRESET-DATA/files/ui/message/msg_name.msbt` -
  message labels for `list.txt` (read-only, via `tools/stat-presets/msbt.py`).
* `tools/stat-presets/stat_fields.txt` - the existing ten, **read-only**.
* P4 scanner copied into this task's scratch: `stat_reads.py` is
  byte-identical to `scratch/2026-10-04_P4-STAT-SITES/stat_reads.py`, sha256
  `28126c1bb703ecc7f79b7cc71b32d24db6b711c00bbb5f781b4dc01d44fd9a6d`.
  The original was not edited.
* P7 host-side checker, used read-only:
  `scratch/2026-10-05_P7-PRESET-ENGINE/preset_report.rs` +
  `builds/.cache/host-test/preset_report_p7.exe` (the plugin's own
  `plugin/src/preset.rs`, compiled for the host; nothing in `plugin/` was
  edited).

## 2. Part 1 - which fields qualify

Method: P4-STAT-SITES unchanged, copied into
`scratch/2026-10-05_P10-PRESET-WIDE/` (`scan_wide.py` + `stat_reads.py`).
For every field hash of all 369 table fields the scan finds code sites that
materialise the hash40 (movz/movk, gap <= 4, no sequence spanning a call) and
call through the first bl/blr inside the 0x400-byte span, records the
displacement of the object load (`+0x270`, `+0x250`, ...) and x2 at the call.

Validation before the real scan, both green:

* `scan_wide.py validate` - 38 planted-sequence self-tests, `VALIDATE OK`
  (0.5 s).
* `scan_wide.py validate_p4` - reproduces P4's recorded per-field counts for
  the existing ten **exactly**:

  | field | P4 sites | via270 | this survey sites | via270 |
  |---|---|---|---|---|
  | weight | 37 | 23 | 37 | 23 |
  | walk_speed_max | 18 | 6 | 18 | 6 |
  | run_speed_max | 18 | 6 | 18 | 6 |
  | dash_speed | 27 | 3 | 27 | 3 |
  | air_speed_x_stable | 29 | 19 | 29 | 19 |
  | air_speed_y_stable | 22 | 10 | 22 | 10 |
  | air_accel_y | 102 | 28 | 102 | 28 |
  | air_accel_x_mul | 22 | 7 | 22 | 7 |
  | jump_y | 10 | 3 | 10 | 3 |
  | jump_speed_x | 25 | 6 | 25 | 6 |

  (`VALIDATE_P4 OK`.)

Whole-image scan duration, measured: **26.2 s wall** for all 369 fields
(image load 0.1 s, primary scan 18.7 s, strict cross-check scan 6.4 s,
classification 0.2 s). Both scanners (P4 copy and the independent strict
re-implementation) agreed on every field: **0 disagreements**. 3 169 code
sites in total. Re-running the scan reproduces `field_table.json`
byte-for-byte; only the `timing_seconds` note in `sites_all.json` /
`field_table.txt` changes between runs.

Outputs (workspace `gamedata/mii_customizer/P10-PRESET-WIDE/`):
`sites_all.json` (raw survey), `field_table.json` (the one table),
`field_table.txt` (human-readable), `qualifying.json` (intermediate
qualifier list - kept here, not in the mod tree, because it is derived from
game files). Every row carries: name (only when
hash-verified), hash, type, +0x270 sites, +0x250 sites, other-displacement
sites, x2 at the +0x270 sites, Mii Gunner's value, min / max over all 94
fighters, distinct-value count, qualifies + reason.

Results:

* 369 fields: **292 float**, 77 not float (i32 / hash). 23 field names are
  unverified (no hash-verified ParamLabels entry).
* Float with >= 1 +0x270 site: **132**. Of those, x2 == 0 at >= 1 site and
  the value differs between fighters: **114 qualify**.
* Float failures: 139 no +0x270 site at all, 21 no site AND same value for
  every fighter, 15 same value for every fighter, 3 have +0x270 sites but
  x2 could not be determined as 0 at any of them (2 fields: 1 unknown site
  each; 1 field: 3 unknown sites; 0 sites showed a known nonzero x2).
* Integer fields with sites through +0x250 (not usable until a later plugin
  task adds integer support) - listed separately as required:
  `jump_count_max` (1 site), `final_start_turn_frame` (1),
  `attack_lw3_rebound_count` (1), `attack_100_rebound_count` (1),
  `scroll_rate_change_frame` (1), `pickel_capture_fence_type` (2), and one
  unlabelled hash `0x19f190006a` (1). None of these is in the preset file.
* `size` (0x04f7c0246a) and friends: hash-typed, +0x270 site count 0 -
  correctly not qualifying (of its 584 sites: 567 direct reads, 13 through
  +0x250, 4 through +0x50, none through +0x270).

Caveat, repeated because it matters: a static site proves the engine *can*
ask for the field through the hook plugin 0.3.0 overrides, not that it does
so during play. The plugin log answers that per field after the console test.


## 3. Part 2 - the choice of at most 48

Choice: **41 fields** (the limit is 48, so 7 slots remain open for a later
round). Written to the NEW file `tools/stat-presets/stat_fields_wide.txt`;
`stat_fields.txt` is untouched (the check script asserts the first ten of the
wide file equal it, in order).

The first ten are the console-proven fields, unchanged and in the same order:
`weight`, `walk_speed_max`, `run_speed_max`, `dash_speed`,
`air_speed_x_stable`, `air_speed_y_stable`, `air_accel_y`,
`air_accel_x_mul`, `jump_y`, `jump_speed_x`.

The 31 added, ranked by how much they shape how a fighter moves and lands,
in that order:

| # | group | fields |
|---|---|---|
| 11-13 | ground movement | `run_accel_add`, `guard_speed_limit`, `shoot_dash_speed_b` |
| 14-17 | air movement | `air_brake_x`, `air_brake_y`, `air_ground_speed_brake`, `damage_fly_top_air_accel_y` |
| 18-27 | jumps | `jump_initial_y`, `jump_aerial_y`, `jump_speed_x_max`, `mini_jump_y`, `cliff_jump_y`, `cliff_jump_x_speed`, `passive_wall_jump_y_speed`, `passive_wall_jump_x_speed`, `passive_wall_x_speed`, `passive_ceil_x_speed` |
| 28-29 | gravity and fall / braking | `dive_speed_y`, `ground_brake` |
| 30 | landing | `item_lift_speed_max` |
| 31-32 | friction | `wind_resistance`, `shield_break_y` |
| 33-41 | the rest | `charge_final_attack_mul`, `charge_final_attack_reaction_mul`, `throw_item_speed_mul`, `throw_item_power_mul`, `tread_range_h`, `tread_range_add_h`, `tread_range_w`, `ladder_range_w`, `ladder_range_offset_y` |

114 fields qualified, so the cut was needed. Every decision for all 369
fields - included, flagged, excluded, not qualifying - with its reason is in
`tools/stat-presets/stat_fields_wide_decisions.json` (and merged into
`fields_wide.json`). The cut, by category:

* **255 not qualifying** - fails the Part 1 criterion (no +0x270 site with
  x2 == 0, or the value does not differ between fighters, or not a float).
* **69 flagged for coordinator review instead of included** (all of them
  would otherwise qualify):
  * 31 look like indexes (small integer-valued sets, slot/choice semantics,
    e.g. `attack_s4_smash_hold_attack_up`, `cursor_offset_y`, `se_pitch_big`),
  * 18 have a 0 or a negative value on at least one fighter
    (e.g. `walk_accel_mul`, `jump_speed_x_mul`, `ice_jump_speed_y_mul`),
  * 18 are size/scale-like (e.g. `scale`, `height`, `egg_scale`),
  * 2 look like frame counts stored as floats tied to animation length
    (e.g. `final_end_jump_y`).
* **4 excluded**: qualifying, but no hash-verified field name, so the
  generator could not resolve them in a name list (hashes
  `0x293cf74337`, `0x294bf073a1`, `0x29a5fe128d`, `0x2c816b267a`).

Nothing above is runtime evidence; it is a data choice over offline
measurements. The ranking is a judgement call - the coordinator can promote
a flagged field by moving it into `stat_fields_wide.txt` (the flag reasons
are there to be reviewed, not as vetoes).


## 4. Part 3 - generated files

`tools/stat-presets/build_presets.py` gained options; **defaults are
unchanged**: `--fields`, `--out-dir` (plus `--presets-name`, `--fighters-name`,
`--full-name`, `--list-name`, `--fields-json-name`, `--decisions`,
`--field-table`, `--label-prefix`) and the opt-in `--write-list` that also
writes `list.txt` and `fields_wide.json`.

**Byte-identity of the default run, verified** (regenerated into a temporary
folder under `gamedata/mii_customizer/P10-PRESET-WIDE/` by the check script,
compared, then removed):

    presets.txt  sha256 f6acbba17d510aae0f0a2cc49cc5417287d4f0d0a8428dbf52d3ca4505865c0d
                 (required: f6acbba17d510aae0f0a2cc49cc5417287d4f0d0a8428dbf52d3ca4505865c0d)

Wide run (workspace `gamedata/mii_customizer/P10-PRESET-WIDE/`), all
regenerated byte-identically by the check script:

| file | bytes | sha256 (first 16) | limits |
|---|---|---|---|
| `presets_wide.txt` | 89 003 | `8c763e77ce8d8f6e` | contract A: 512 KiB / 128 / 48 / 48 - all pass, 94 presets, 41 fields and 41 hashes each |
| `list.txt` | 2 600 | `f74048de7a825d9a` | contract F: 16 KiB / 128 lines - 87 entries, labels all `nam_chr1_00_*` and resolvable |
| `fields_wide.json` | 257 426 | `e7a8de0e28ad1a31` | 369 rows, every one carries a decision |
| `fighters.json` | 15 535 | `53f37ee31cf744d2` | unchanged P6 shape |
| `fighter_param_full.json` | 7 675 807 | `c46dcd3e344b45f7` | unchanged P6 shape |

`list.txt`: line 1 is exactly `mc_list 1`, then comment lines, then
`<preset_name> <message_label>` in fighter_param table order.

**Fighters left out of `list.txt` (7 of 94), with the reason each:**

| row | fighter | reason |
|---|---|---|
| 14 | `popo` | no label `nam_chr1_00_popo` in msg_name.msbt |
| 15 | `nana` | no label `nam_chr1_00_nana` in msg_name.msbt |
| 77 | `eflame` | no label `nam_chr1_00_eflame` in msg_name.msbt |
| 78 | `elight` | no label `nam_chr1_00_elight` in msg_name.msbt |
| 91 | `miienemyf` | preset name starts with `miienemy` (contract: left out) |
| 92 | `miienemys` | preset name starts with `miienemy` |
| 93 | `miienemyg` | preset name starts with `miienemy` |

No fighter was left out for empty or multi-line text, and none for a label
failing `[a-z0-9_]{1,63}`. (Separately, `fighters.json`'s *display-name*
rule uses `nam_chr0_00_*` and holds for 82/94 - that is a different label
family and does not gate `list.txt`.)

**Five list lines with the resolved text** (text read from msg_name.msbt,
not written to any file):

| list line | resolved text |
|---|---|
| `mario nam_chr1_00_mario` | Mario |
| `donkey nam_chr1_00_donkey` | Donkey Kong |
| `link nam_chr1_00_link` | Link |
| `samus nam_chr1_00_samus` | Samus |
| `yoshi nam_chr1_00_yoshi` | Yoshi |

**Validation of `presets_wide.txt` against the plugin's rules:** the P7
host-side checker *can* take a file path (`preset_report <file> --dump`), so
it was run as required; its output:

    state=ok bytes=89003 lines=4142 presets=94 hashes=41 field_lines=3854 rejected=0 skipped=0
    fields n=41 probe_max=2
    fields_per_preset min=41 max=41 longest_name=12

That is the plugin's own `preset.rs` parsing the file (host build; `plugin/`
not edited). On top of that, the check script re-checks every limit with its
own independent model of contract A (see section 6).


## 5. Part 4 - sanity table

Generated by `scratch/2026-10-05_P10-PRESET-WIDE/sanity_table.py` into
workspace `gamedata/mii_customizer/P10-PRESET-WIDE/sanity_table.md` (values
read straight from `presets_wide.txt` - the numbers the plugin would hand
the engine). Every chosen field, side by side; a backticked field name marks
a field where at least one of the five characters deviates from Mii
Gunner by >= 25% of the Gunner value - 28 of 41 fields are marked, those are
what the user should feel first.

| field | Mii Gunner | mario | fox | purin (Jigglypuff) | ganon | kirby | max dev |
|---|---|---|---|---|---|---|---|
| `weight` | 104 | 98 | 77 | 68 | 118 | 79 | 35% |
| `walk_speed_max` | 1 | 1.155 | 1.523 | 0.735 | 0.767 | 0.977 | 52% |
| `run_speed_max` | 1.37 | 1.76 | 2.402 | 1.271 | 1.34 | 1.727 | 75% |
| `dash_speed` | 1.63 | 1.936 | 2.09 | 1.65 | 1.87 | 1.9 | 28% |
| `air_speed_x_stable` | 0.93 | 1.208 | 1.11 | 1.332 | 0.83 | 0.84 | 43% |
| `air_speed_y_stable` | 1.45 | 1.5 | 2.1 | 0.98 | 1.65 | 1.23 | 45% |
| `air_accel_y` | 0.098 | 0.087 | 0.23 | 0.053 | 0.108 | 0.064 | 135% |
| `air_accel_x_mul` | 0.043 | 0.07 | 0.08 | 0.08 | 0.03 | 0.065 | 86% |
| `jump_y` | 30.9 | 36.33 | 35 | 19.79 | 25.49 | 25.37 | 36% |
| `jump_speed_x` | 0.95 | 0.95 | 0.68 | 0.7 | 0.9 | 0.85 | 28% |
| `run_accel_add` | 0.044 | 0.044 | 0.044 | 0.044 | 0.033 | 0.044 | 25% |
| guard_speed_limit | 1.3 | 1.3 | 1.3 | 1.3 | 1.3 | 1.3 | 0% |
| `shoot_dash_speed_b` | 1.0432 | 1.23904 | 1.3376 | 1.056 | 1.1968 | 1.216 | 28% |
| `air_brake_x` | 0.012 | 0.015 | 0.015 | 0.0375 | 0.015 | 0.015 | 213% |
| `air_brake_y` | 0.015 | 0.015 | 0.015 | 0.038 | 0.015 | 0.015 | 153% |
| `air_ground_speed_brake` | 0.036 | 0.045 | 0.045 | 0.1125 | 0.045 | 0.045 | 213% |
| damage_fly_top_air_accel_y | 0.076944 | 0.074928 | 0.067872 | 0.064848 | 0.081648 | 0.068544 | 16% |
| `jump_initial_y` | 16.995 | 19.9815 | 19.25 | 10.8845 | 14.0195 | 13.9535 | 36% |
| `jump_aerial_y` | 32.3 | 36.33 | 37 | 19.79 | 26 | 22 | 39% |
| `jump_speed_x_max` | 1.3 | 1.3 | 1.7 | 1.35 | 1.8 | 1.3 | 38% |
| mini_jump_y | 14.6 | 17.54 | 16.4 | 11.26 | 12.24 | 12.24 | 23% |
| cliff_jump_y | 35.45 | 38.165 | 37.5 | 29.895 | 32.745 | 32.685 | 16% |
| cliff_jump_x_speed | 0.6 | 0.6 | 0.6 | 0.6 | 0.6 | 0.6 | 0% |
| `passive_wall_jump_y_speed` | 2.1 | 2.3 | 3.3 | 1.6 | 2.6 | 2 | 57% |
| passive_wall_jump_x_speed | 1.3 | 1.3 | 1.4 | 1.3 | 1.3 | 1.3 | 8% |
| passive_wall_x_speed | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0.5 | 0% |
| `passive_ceil_x_speed` | 1 | 1 | 0.7 | 0.9 | 1 | 0.9 | 30% |
| `dive_speed_y` | 2.32 | 2.4 | 3.36 | 1.568 | 2.64 | 1.968 | 45% |
| `ground_brake` | 0.076 | 0.102 | 0.115 | 0.087 | 0.125 | 0.116 | 64% |
| `item_lift_speed_max` | 1.08 | 1.0262 | 0.83092 | 0.7094 | 1.21068 | 0.82908 | 34% |
| wind_resistance | 0.8 | 0.7 | 0.8 | 0.8 | 0.8 | 0.8 | 13% |
| `shield_break_y` | 40.67 | 44.1 | 58 | 936.84 | 40 | 34 | 2204% |
| `charge_final_attack_mul` | 0.7 | 0.95 | 0.7 | 0.7 | 0.7 | 0.7 | 36% |
| charge_final_attack_reaction_mul | 0.985 | 0.91 | 0.9525 | 0.92 | 0.944 | 0.967 | 8% |
| throw_item_speed_mul | 1.01333 | 0.993333 | 0.923333 | 0.893333 | 1.06 | 0.93 | 12% |
| throw_item_power_mul | 1 | 1 | 1 | 0.95 | 1 | 1 | 5% |
| `tread_range_h` | 6 | 6 | 6 | 3 | 6 | 7 | 50% |
| tread_range_add_h | 2 | 2 | 2 | 2 | 2 | 2 | 0% |
| `tread_range_w` | 7 | 7 | 6 | 3 | 6 | 6 | 57% |
| ladder_range_w | 6 | 6 | 6 | 6 | 6 | 6 | 0% |
| `ladder_range_offset_y` | 10 | 10 | 8 | 10 | 10 | 6 | 40% |

Coordinator notes from the table:

* Biggest felt differences: `air_accel_y` (up to 135%), `air_brake_x/y` and
  `air_ground_speed_brake` (purin brakes 3x harder than the Gunner),
  `run_speed_max` (fox 75% faster), `shield_break_y` (purin 936.84 vs the
  Gunner's 40.67 - a 23x outlier worth a look before trusting it, it is what
  the table says).
* `guard_speed_limit`, `cliff_jump_x_speed`, `passive_wall_x_speed`,
  `tread_range_add_h`, `ladder_range_w` are identical across these six -
  they were still chosen because other fighters do differ; they just do not
  show in this sample.


## 6. Checks

All run from the workspace root, all observed green:

1. `scan_wide.py validate` - 38 planted-sequence self-tests of the copied
   scanner -> `VALIDATE OK` (0.5 s).
2. `scan_wide.py validate_p4` - P4's recorded site counts for the existing
   ten reproduced exactly -> `VALIDATE_P4 OK`.
3. Whole-image scan re-run (26.2 s) -> `field_table.json` regenerated
   byte-for-byte (sha256 `6ab81cfc4c8e8a00d2b441ed13afa5ee201e44b6059d6b85f9c788afed188662`);
   only the `timing_seconds` note differs between runs.
4. Default generator run into a temp folder -> `presets.txt` sha256
   `f6acbba17d510aae0f0a2cc49cc5417287d4f0d0a8428dbf52d3ca4505865c0d`,
   byte-identical as required (temp folder removed).
5. Wide generator re-run over the delivered files -> all five outputs
   byte-identical to their delivered sha256s (listed in section 4).
6. **`evidence/P10-PRESET-WIDE/check_preset_wide.py` -> 29 PASS, 0 FAIL,
   exit 0** (full output: `evidence/P10-PRESET-WIDE/check_run.log`). It
   regenerates wide + default into `gamedata/.../_check_tmp/`, compares,
   validates contract A and contract F with its own model, checks the
   list/preset cross-references both directions, runs the four negative
   controls, runs the P7 parser, and removes the temp folder (verified
   absent at the end).
7. Negative controls, each confirmed to be caught:
   * (a) a 49-field list -> generator refuses: `lists 49 fields; contract A
     allows at most 48 per preset`, no preset file written;
   * (b) `fighter mario` duplicated -> `line 53: duplicate preset name
     'mario'`;
   * (c) list line `no_such_preset nam_chr1_00_mario` -> `list names preset
     'no_such_preset' which is not in presets_wide.txt`;
   * (d) label `nam_chr1_00_no_such_label` -> `does not exist in
     msg_name.msbt`.
8. P7 host-side checker on `presets_wide.txt` -> `state=ok ... rejected=0
   skipped=0`, `fields_per_preset min=41 max=41` (section 4).
9. `sanity_table.py` regenerated `sanity_table.md` (section 5).

## 7. Limits

* **Nothing is run in the game.** A static site proves the engine *can* ask
  for a field through slot +0x270 with x2 == 0 - the shape plugin 0.3.0
  overrides - **not that it does so during play**. After the next console
  test the plugin log shows, per field, which of the 41 were actually
  requested and overridden; that is the evidence that upgrades this.
* Everything here is evidence tier **B** (offline measurement of the user's
  own files). An emulator run would also be B; only the console is A.
* The ranking in Part 2 is a judgement about feel, not a measurement. The
  69 flagged fields are held back for coordinator review, not vetoed.
* `list.txt` carries labels only; the visible text stays in msg_name.msbt.
* `presets_wide.txt` copies numbers per fighter. It says nothing about how a
  preset interacts with the Mii's own move set or with editing UI (P7/P10
  UI slice are separate tasks).


## Summary

**Task P10-PRESET-WIDE - DONE.**

Changed / created files (all inside `mods/mii_customizer/` unless noted):

| path | what |
|---|---|
| `research/P10-PRESET-WIDE.md` | this report |
| `tools/stat-presets/build_presets.py` | options `--fields` / `--out-dir` / names / `--write-list`; list.txt + fields_wide.json builders; defaults unchanged |
| `tools/stat-presets/stat_fields_wide.txt` | NEW - the 41 chosen fields (`stat_fields.txt` untouched) |
| `tools/stat-presets/stat_fields_wide_decisions.json` | NEW - decision + reason for all 369 fields |
| `tools/stat-presets/README.md` | updated: wide field list, options, outputs, check script |
| `scratch/2026-10-05_P10-PRESET-WIDE/` | `scan_wide.py` (copied P4 method + self-test + validate_p4), `stat_reads.py` (byte-identical P4 copy), `p4_scan_all_reference.py`, `derive_table.py`, `choose_fields.py`, `sanity_table.py`, `d.py`, `qualifying.json` |
| `evidence/P10-PRESET-WIDE/check_preset_wide.py` | the check script (29 checks, negative controls, temp cleanup) |
| `evidence/P10-PRESET-WIDE/build_wide.log`, `check_run.log` | captured run outputs |
| workspace `gamedata/mii_customizer/P10-PRESET-WIDE/` | `sites_all.json`, `field_table.json`, `field_table.txt`, `qualifying.json`, `presets_wide.txt`, `list.txt`, `fields_wide.json`, `fighters.json`, `fighter_param_full.json`, `sanity_table.md` |

Checks run: scanner self-test (38 OK), P4 reproduction (10/10 exact),
full scan 26.2 s (0 scanner disagreements), default sha256 byte-identity,
wide regeneration byte-compare (5/5), contract A/F own-model validation,
list/preset cross-references both ways, four negative controls all caught,
P7 plugin parser `state=ok`, check script 29 PASS / 0 FAIL exit 0.

Open questions for the coordinator:

1. `shield_break_y` for `purin` is 936.84 against ~40 for everyone else in
   the sample - the table says so, but worth a sanity look before trusting
   it in play (it may be intentional).
2. 7 of the 48 slots are still free; candidates are the 69 flagged fields
   (18 with 0/negative values, 31 index-like, 18 scale-like, 2 frame-like).
   Promoting any of them is a one-line change to `stat_fields_wide.txt`.
3. Four qualifying hashes have no hash-verified name (`0x293cf74337`,
   `0x294bf073a1`, `0x29a5fe128d`, `0x2c816b267a`) - if ParamLabels grows a
   name for them they become listable.
4. `popo`, `nana`, `eflame`, `elight` have no `nam_chr1_00_*` label, so they
   are absent from `list.txt`; say if another label family should name them.
5. The console test decides which of the 41 fields the engine actually
   asks for at runtime - the plugin log, not this file, answers that.
