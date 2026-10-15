# P6-PRESET-DATA - second worker: independent verification (2026-10-05)

Status: **DONE as a verification, nothing rebuilt.** This prompt was started twice. The other
worker finished the tool, outputs and report (`research/P6-PRESET-DATA.md`, 05:18) while this
worker was waiting for the user's answer on the collision. This worker did not edit any of its
files. Tier B (offline), no runtime claim.

## What this worker wrote

- this file
- `scratch/2026-10-05_P6-PRESET-DATA/w2_msbt.py`, `w2_cover.py`, `w2_verify.py` (own readers)
- created and removed again: workspace `gamedata/mii_customizer/P6-PRESET-DATA/extract/` (a
  second extraction of the two message files, byte-identical to the other worker's `files/`),
  and the temp folder left by one run of `check_presets.py` (see finding 2)

## Inputs and outputs checked (sha256, workspace-relative)

| file | sha256 | bytes |
|---|---|---|
| `gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc` | `87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2` | 176604 |
| `mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv` | `6ae7f792609612370e6b9244e1d6986ebd8ced9bbb77fad49de8c568919344f4` | - |
| `gamedata/mii_customizer/P6-PRESET-DATA/files/ui/message/msg_name.msbt` | `9efc357db8ea46e671222dbbd90bbdc0ea5455383090fae3fe2ba6017e9da3ad` | 490336 |
| `gamedata/mii_customizer/P6-PRESET-DATA/presets.txt` | `f6acbba17d510aae0f0a2cc49cc5417287d4f0d0a8428dbf52d3ca4505865c0d` | 25517 |
| `gamedata/mii_customizer/P6-PRESET-DATA/fighters.json` | `66217c37088a5f37b2a7ef7edbd4aa5cde8e328340b7d8d23affeb7c2b6202d4` | 15530 |
| `gamedata/mii_customizer/P6-PRESET-DATA/fighter_param_full.json` | `9188c7680a86787feaee12f9537157dda64e89c37c87124af2c0bbd8196d70df` | 7675802 |

## Commands (from the workspace root)

```sh
python -B mods/mii_customizer/scratch/2026-10-05_P6-PRESET-DATA/w2_verify.py   # 0 fails
python -B mods/mii_customizer/tools/stat-presets/check_presets.py              # 30 checks, 0 failed, exit 0
```

## Observed (verified)

`w2_verify.py` shares no code with `tools/stat-presets/`; it decodes the table with the
shared `prc.py` and parses `presets.txt` and the MSBT with its own code.

- Table: 94 rows, 369 fields in every row; per row 292 float, 25 i32, 19 bool, 33 hash, no
  other type; 23 field names without a hash-verified label. Same numbers as the report.
- `presets.txt`: line 1 `mc_presets 1`, ASCII only, `\n` only, 94 presets, preset i is table
  row i, every name is `fighter_kind_<name>` re-hashed to the row's kind, ten field lines per
  preset in `stat_fields.txt` order, kind hashes and names unique.
- All 940 values equal the table's f32 bit-for-bit under a correctly rounded parse.
- All 940 values also equal the table bit-for-bit under a model of the parser the plugin
  already has (`plugin/src/loadout.rs` `parse_decimal`: u64 mantissa / f64 power of ten, cast
  to f32). Longest value token 12 characters, no exponent, no sign; so the existing number
  syntax (at most 18 digits) reads this file exactly. The other worker's check does not test
  this model.
- `fighters.json` has the same order, names, kind hashes and row indexes as `presets.txt`;
  every non-null label exists in `msg_name.msbt`.
- 25517 bytes: does not fit the plugin's 16 KiB (16384) limit, as reported.

## Findings for the coordinator

1. **Display-name label family: `nam_chr1_00_<name>` is the better rule.** The tool uses
   `nam_chr0_00_<name>` (82 of 94; `kirby` has no such label, and 5 of the 82 texts contain a
   line break). Measured here: `nam_chr1_00_<name>` exists for **87 of 94** and none of the 87
   texts contains a line break; it adds `kirby`, `pzenigame`, `pfushigisou`, `plizardon`,
   `koopag`. Exceptions under that rule: `popo`, `nana`, `eflame`, `elight`, `miienemyf`,
   `miienemys`, `miienemyg` (for the first four, labels exist only under other names:
   `ice_climber`, `eflame_only`, `elight_only`; not a rule). `nam_chr2_00_` covers 90 but 11
   texts contain a line break. The report's reason for choosing chr0 ("no family other than
   chr0 covers all") does not match its own counts. Which screen uses which family is not
   established (D); for a one-line list entry chr1 is the measured better fit. Changing it is a
   one-constant edit in the other worker's tool; not done here.
2. **`check_presets.py` leaves game-derived data under `mods/`.** Each run creates
   `scratch/2026-10-05_P6-PRESET-DATA/check-<random>/` with six copies of the full table JSON
   and preset files (45 MB, observed after the run above) and does not delete it. That breaks
   "nothing game-derived under mods/mii_customizer/". The folder from this worker's run was
   removed by hand. Fix: put the temp folder under workspace
   `gamedata/mii_customizer/P6-PRESET-DATA/` and delete it at exit; also the scratch path is
   hardcoded with a date inside a reusable tool.
3. The corrupted-hash negative control passes a wrong *expected* hash; no control feeds a
   modified input file. Equivalent for the hash assertion, noted for completeness.

## Not checked

The generator source line by line; the 282-row "other float fields" table and the sanity
tables in the report (only the type counts behind them); the non-playable flags;
`msg_menu.msbt`. No runtime behaviour.

## Next experiment

Unchanged from the main report (size limit decision, then a single-field preset on the
console). Before that: decide finding 1 and regenerate `fighters.json` once.
