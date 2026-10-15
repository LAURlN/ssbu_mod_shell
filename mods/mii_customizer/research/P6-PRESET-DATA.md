# P6-PRESET-DATA - character stat presets from the user's own game files

Task: `prompts/P6-PRESET-DATA.md`. Date 2026-10-05. Worker: Space Bunny Alpha.
Status: **DONE**.

Paths are relative to `mods/mii_customizer/` unless marked workspace-relative.

Everything here is offline measurement of the user's own files: **B**. The MSBT
container layout is read from pinned source: **C**. Nothing is **A**; no console
or emulator was used, the plugin was not touched, and no runtime behaviour is
claimed anywhere. **Applying a preset copies the listed numbers. This report does
not show, and must not be read as showing, that using a preset makes a Mii play
like any character.**

## Result in short

- `tools/stat-presets/` builds and checks: generator, check script, MSBT reader
  and the coordinator-owned `stat_fields.txt`.
- Three outputs, all under workspace-relative
  `gamedata/mii_customizer/P6-PRESET-DATA/`: `fighter_param_full.json`
  (7 675 802 B), `presets.txt` (25 517 B), `fighters.json` (15 530 B).
- **94 rows, 369 fields each, equal for every row.** 94 presets written, **0
  skipped**. 940 values, all re-parsed bit-for-bit.
- **`presets.txt` is 25 517 bytes. It does NOT fit the plugin's current 16 KiB
  limit** (16 384 B) -- it is 9 133 bytes over, so the limit has to be set from
  25 517, or the format needs a cheaper encoding.
- Display-name label rule holds for **82 of 94** fighters; 12 exceptions listed,
  not guessed.
- `check_presets.py`: **30 checks, 0 failed, exit 0**, including five negative
  controls that must fail and do.

## 1. Inputs, exactly

| role | path (workspace-relative) | sha256 | bytes |
|---|---|---|---|
| param table | `gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc` | `87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2` | 176 604 |
| name dictionary | `mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv` | `6ae7f792609612370e6b9244e1d6986ebd8ced9bbb77fad49de8c568919344f4` | 3 099 694 |
| display names | `gamedata/mii_customizer/P6-PRESET-DATA/files/ui/message/msg_name.msbt` | `9efc357db8ea46e671222dbbd90bbdc0ea5455383090fae3fe2ba6017e9da3ad` | 490 336 |
| cross-check only | `gamedata/mii_customizer/P6-PRESET-DATA/files/ui/message/msg_menu.msbt` | `4b4f3d23640032858334ab0b51939f3675271cad326131bcb5c70c1a4f25b26b` | 268 096 |

The `fighter_param.prc` hash matches the value in the prompt and in
`tools/gunner-catalog/README.md`. The `msg_menu.msbt` hash matches the value
P5-MSG-PROBE recorded (`research/P5-MSG-PROBE.md`), which is an independent
confirmation that both extractions are the same bytes.

Both `.msbt` files were extracted **by this task** into the task's own
`gamedata/` folder:

```
tools/arc-extract/target/release/arc-extract.exe \
  --arc gamedata/ssbu-13.0.4/data.arc --out gamedata/mii_customizer/P6-PRESET-DATA/files \
  ui/message/msg_menu.msbt ui/message/msg_name.msbt
```

`msg_menu.msbt` is not an input to the three outputs; it is recorded because the
prompt named it and because its hash cross-checks the extraction.

Nothing under `dump/` was touched. `ParamLabels.csv` and the `prc.py` reader were
used read-only.

## 2. Commands

```
python -B mods/mii_customizer/tools/stat-presets/build_presets.py
python -B mods/mii_customizer/tools/stat-presets/check_presets.py
```

Full check output: `evidence/P6-PRESET-DATA/check_output.txt`.
Report tables: `evidence/P6-PRESET-DATA/report_tables.txt`.

## 3. The full table (B)

`gamedata/mii_customizer/P6-PRESET-DATA/fighter_param_full.json`, decoded from
`fighter_param_table`:

| question | answer |
|---|---|
| row count | **94** |
| field count per row | **369, equal for every row** (`field_count_equal_for_all_rows: true`) |
| distinct field names across rows | 369 |
| float fields | **27 448** total, i.e. **292 per row** |
| int fields (`i32`) | **2 350** total, 25 per row |
| bool fields | **1 786** total, 19 per row |
| hash fields | **3 102** total, 33 per row |
| other types | **0** |
| unlabelled field names | **23** (same 23 hashes in every row) |

Every row carries `fighter_kind` (hash `0x0c541ef0b2`), and **all 94 kind hashes
have a hash-verified `fighter_kind_<name>` label in `ParamLabels.csv`**. The
control from P1-DATASET reproduces: `hash40("fighter_kind_miigunner")` =
`0x166e9fae70` occurs in **exactly one** row, index **82**.

Names are never trusted on the strength of appearing in the CSV: the tool
re-hashes the name and only uses it if it reproduces the hash. Measured over
row 0, 346 of 369 fields had a label and **0 of them mismatched**.

Each field record carries hash, name (or null), `name_hash_verified`, type,
value, `value_f32_bits` and the exact text written into `presets.txt`. Hash
fields also carry their own value name when it verifies.

## 4. The preset file

`gamedata/mii_customizer/P6-PRESET-DATA/presets.txt`, format `mc_presets 1`:

```
mc_presets 1
# Mii Customizer stat presets, format mc_presets 1
# Generated from the user's own fighter/common/param/fighter_param.prc
# sha256 87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2
# One preset per fighter kind. Values are copied numbers from that
# table; nothing here states that using one changes how a Mii plays.

# row 82
fighter miigunner 0x166e9fae70
0x0607cd5541 104
0x0ee2ec2860 1
0x0d5aaabf9b 1.37
0xadec47ea3 1.63
0x1220fc2660 0.930000007
0x12ec5626fe 1.45000005
0x0ba18057d9 0.0979999974
0x0f71f4d4f8 0.0430000015
0x06a0d82dad 30.8999996
0x0cc9d2f2da 0.949999988
```

* **94 presets written, 0 skipped.** Rows whose kind had no verified label
  would be skipped and listed; on this file none was.
* Values are printed with `%.9g`. Nine significant decimal digits always
  round-trip a 24-bit significand, and that is **verified, not assumed**: the
  generator re-parses every value it writes and aborts on any bit difference,
  and the check script repeats the comparison with an independent reader over
  all **940** values.
* Preset names are the internal name from the `fighter_kind_` label with the
  prefix removed, and all 94 match `[a-z0-9_]`.

### Size against the plugin limit

| item | bytes |
|---|---|
| `presets.txt` | **25 517** |
| plugin's current whole-file limit | 16 384 (16 KiB) |
| over by | **9 133** |

**It does not fit.** The plugin's `too_large` rule refuses the whole file
(`research/P4-OVERRIDE-SLICE.md` 2.1), so at 25 517 bytes the file would be
refused outright and every preset would be unavailable. The coordinator has two
options, both outside this task:

1. set the preset-file limit from this measurement (**25 517**, with headroom),
   or
2. keep 16 KiB and make the format cheaper. At 25 517 bytes for 940 values the
   fixed part is ~5 117 bytes of headers, blank lines and the `fighter` lines,
   so roughly 20 400 bytes is `0x` + 10 hex digits + space + digits per value.
   Dropping the per-value field hash (the order already fixes the field) or
   shortening values would recover most of it.

This task implemented the format as the prompt specified and reports the number;
the format change is the coordinator's contract to make.

## 5. The other float fields (for extending the list)

The row has **292 float fields**; ten are in `stat_fields.txt`, so **282 are
not**, and **9 of those 282 are unlabelled** (hash only). The complete table --
field, hash, Gunner value, minimum and maximum over all 94 rows, and which
fighter holds each extreme -- is in **`evidence/P6-PRESET-DATA/report_tables.txt`
section C**, with the following summary. It is listed, **not added**: the field
list stays at the ten the prompt specified.

Extremes of the ten preset fields (all 94 rows):

| field | min | fighter | max | fighter |
|---|---|---|---|---|
| `weight` | 62 | pichu | 150 | koopag |
| `walk_speed_max` | 0.62 | gaogaen | 1.575 | marth |
| `run_speed_max` | 1.18 | gaogaen | 3.85 | sonic |
| `dash_speed` | 1.45 | pickel | 2.45 | elight |
| `air_speed_x_stable` | 0.735 | dedede | 1.344 | yoshi |
| `air_speed_y_stable` | 0.98 | purin | 2.2 | koopag |
| `air_accel_y` | 0.053 | purin | 0.23 | fox |
| `air_accel_x_mul` | 0.02 | snake | 0.105 | peach |
| `jump_y` | 16.5 | pickel | 50.51 | falco |
| `jump_speed_x` | 0.57 | popo | 1 | ness |

The 282 other float fields fall into recognisable groups by name, which is the
practical way to choose an extension: movement (`air_brake_x`, `air_brake_y`,
`air_ground_speed_brake`, `air_accel_x_add`), size and offsets
(`badge_scale`, `backshield_offset_y`, `*_offset_*`), damage-scaling helpers
(`attack_100_rebound_distance`, `attack_lw4_smash_hold_attack_up`), and many
character-specific ones (`barrel_attack_size` for donkey, `baitocrane_offset_y`
for yoshi). Several take **negative** values across the table, for example
`0x29a5fe128d` from -12 (ridley) to 1 (fox) and `0x2c816b267a` from -85 (marth)
to 60 (diddy), so adding them to a preset would copy negative numbers and the
coordinator's parser would have to accept them. **That is a reason to think
twice before extending the list, not a change made here.**

## 6. The fighter list and the display-name label

`fighters.json`, one entry per preset in file order:

```json
{"name": "mario", "kind_hash": "0x1254206ce1", "row_index": 0,
 "display_name_label": "nam_chr0_00_mario"}
```

**Rule, measured:** the display name of a fighter kind whose internal name is
`N` is the message label **`nam_chr0_00_<N>`** in `ui/message/msg_name.msbt`.
It holds for **82 of 94**. Five examples:

| fighter | label |
|---|---|
| mario | `nam_chr0_00_mario` |
| donkey | `nam_chr0_00_donkey` |
| link | `nam_chr0_00_link` |
| samus | `nam_chr0_00_samus` |
| yoshi | `nam_chr0_00_yoshi` |

`msg_name.msbt` holds 3 839 labels, 85 of them with the `nam_chr0_00_` prefix,
**0 undecodable** by the reader.

The rule is not universal, and the tool does not paper over it. The other four
families (`nam_chr1_00_`, `nam_chr2_00_`, `nam_chr3_00_`, `nam_chr_no_00_`)
resolve for 87, 90, 83 and 86 kinds respectively -- **no family other than
`nam_chr0_00_` covers all of them**, so using one as a fallback would be a guess
about which screen reads which label. **The 12 exceptions keep
`display_name_label: null` and are listed in
`display_name_label_rule_exceptions`:**

`kirby`, `popo`, `nana`, `pzenigame`, `pfushigisou`, `plizardon`, `eflame`,
`elight`, `koopag`, `miienemyf`, `miienemys`, `miienemyg`.

For reference, `eflame` and `elight` do exist but only with `_first` / `_only`
suffixes (`nam_chr0_00_eflame_first`), and the three `miienemy*` kinds have only
`nam_chr2_00_` labels. Picking either form would be a guess, so neither was
picked.

**English text is a count only, per the prompt.** Of the 82 resolved labels,
82 carry non-empty text after stripping NUL/CR/LF/spaces; 693 characters total.
No display text is written into any file under `mods/`.

## 7. Sanity views (B)

Ten preset fields for seven kinds, exact `f32` values as written. Bowser's
internal kind name is **`koopa`** (row 13), which is why that column is
`koopa`.

| | mario | kirby | koopa | fox | miigunner | miifighter | miiswordsman |
|---|---|---|---|---|---|---|---|
| row | 0 | 5 | 13 | 6 | 82 | 80 | 81 |
| `weight` | 98 | 79 | 135 | 77 | 104 | 94 | 100 |
| `walk_speed_max` | 1.15499997 | 0.976999998 | 0.901000023 | 1.523 | 1 | 1.25999999 | 1.07000005 |
| `run_speed_max` | 1.75999999 | 1.727 | 1.97099996 | 2.40199995 | 1.37 | 1.91999996 | 1.58000004 |
| `dash_speed` | 1.93599999 | 1.89999998 | 2.25500011 | 2.08999991 | 1.63 | 1.87 | 1.74000001 |
| `air_speed_x_stable` | 1.20799994 | 0.839999974 | 1.15499997 | 1.11000001 | 0.930000007 | 1.14999998 | 1.16999996 |
| `air_speed_y_stable` | 1.5 | 1.23000002 | 1.76999998 | 2.0999999 | 1.45000005 | 1.91999996 | 1.54999995 |
| `air_accel_y` | 0.0869999975 | 0.064000003 | 0.125 | 0.230000004 | 0.0979999974 | 0.169 | 0.105999999 |
| `air_accel_x_mul` | 0.0700000003 | 0.0649999976 | 0.0399999991 | 0.0799999982 | 0.0430000015 | 0.0579999983 | 0.0500000007 |
| `jump_y` | 36.3300018 | 25.3700008 | 33 | 35 | 30.8999996 | 35 | 28.2999992 |
| `jump_speed_x` | 0.949999988 | 0.850000024 | 0.899999976 | 0.680000007 | 0.949999988 | 0.949999988 | 0.949999988 |

**Controls that passed.** `miigunner` (row 82) reproduces the P1-DATASET §4
values exactly -- `weight` 104.0 `0x42d00000`, `walk_speed_max` 1.0,
`run_speed_max` 1.3700000047683716, `dash_speed` 1.6299999952316284,
`air_speed_x_stable` 0.9300000071525574, `air_speed_y_stable` 1.4500000476837158,
`air_accel_y` 0.09799999743700027, `air_accel_x_mul` 0.0430000014603138,
`jump_y` 30.899999618530273, `jump_speed_x` 0.949999988079071. An independent
decode of the same row therefore agrees with the catalogue.

**Second control.** The three Mii kinds sit close together and inside the field
extremes: `weight` 94 / 100 / 104 where the table spans 62 to 150;
`walk_speed_max` 1.26 / 1.07 / 1.00 where it spans 0.62 to 1.575. The Mii rows
do not look like a mis-picked row.

## 8. Rows that look like non-playable or helper kinds -- FLAGGED, NOT REMOVED

All 94 rows stay in `presets.txt`. Eleven are flagged for the coordinator's
decision:

| name | row | why flagged |
|---|---|---|
| popo | 14 | Ice Climbers partner of nana |
| nana | 15 | Ice Climbers partner of popo |
| pzenigame | 33 | no `nam_chr0_00_` display label |
| pfushigisou | 34 | no `nam_chr0_00_` display label |
| plizardon | 35 | no `nam_chr0_00_` display label |
| koopag | 90 | no `nam_chr0_00_` display label |
| miienemyf | 91 | name marks it an enemy Mii; only `nam_chr2_00_` label |
| miienemys | 92 | name marks it an enemy Mii; only `nam_chr2_00_` label |
| miienemyg | 93 | name marks it an enemy Mii; only `nam_chr2_00_` label |
| eflame | 77 | labels carry `_first` / `_only` suffixes |
| elight | 78 | labels carry `_first` / `_only` suffixes |

The reason column is what the **names and the message file** show. It is not a
claim about what the engine does with these kinds, and no claim that they are
unselectable is made here. The overlap with the 12 label exceptions is not a
coincidence worth reading into: a kind with no `nam_chr0_00_` label is also a
kind the select screen does not appear to name that way.

Note that `koopag` (row 90) is the heaviest and fastest row in the table
(`weight` 150, `air_speed_y_stable` 2.2), so if the coordinator filters by flag,
the extremes in section 5 change.

## 9. The MSBT reader (C for layout, B for the read)

`tools/stat-presets/msbt.py` is a stdlib-only transcription of the readers in
`RoccoDev/msbt-rs` at commit `9837597fe8e8349b6b079a0d17b9ac224df3984d`, cloned
read-only by P5-MSG-PROBE into
`scratch/2026-10-05_P5-MSG-PROBE/msbt-rs`. Files read there: `src/lib.rs`
(header, `read_lbl1`, `read_txt2`, `skip_padding`, `PADDING_CHAR`),
`src/section.rs`, `src/section/lbl1.rs`, `src/section/txt2.rs`.

Two things the probe had to get right, both found by measurement:

* the header is 32 bytes with `section_count` at 14 and `file_size` at 18 -- the
  `us_en` file reads `section_count` 3, `file_size` 490 336, which equals the
  real file length, so the offsets are confirmed rather than assumed;
* **TXT2 offsets are relative to the start of the section body (the
  `string_count` field), not to the first offset entry.** With the wrong base
  every string was shifted by four bytes and decoded to plausible-looking
  garbage (`'yonetta\x00In'` instead of `'Bayonetta\x00'`), which is exactly the
  kind of error that survives a casual look. The check is that all 3 839 labels
  decode, which they do, and that `nam_chr0_00_mario` reads `Mario`.

Strings keep their trailing NUL and control codes; nothing is stripped, because
the caller records what the file actually holds.

## 10. Checks actually run

`python -B mods/mii_customizer/tools/stat-presets/check_presets.py` ->
**30 checks, 0 failed, exit 0**. Full output:
`evidence/P6-PRESET-DATA/check_output.txt`.

1. **Pinned inputs** -- the three input hashes asserted first.
2. **Regeneration** -- all three outputs rebuilt into
   `scratch/2026-10-05_P6-PRESET-DATA/` and compared byte-for-byte with the
   committed files; again under `PYTHONHASHSEED` 0, 1 and 12345.
3. **Independent re-parse** -- `presets.txt` read by a tokenizer inside the
   check script that shares no code with the generator, strict about CRLF, bare
   CR, non-ASCII, field counts and value syntax; **940 values compared
   bit-for-bit** with the `.prc`.
4. **Contract structure** -- version line, field order equal to
   `stat_fields.txt`, no duplicate presets, names `[a-z0-9_]`, every name
   traceable to a hash-verified kind label, `fighters.json` in preset order and
   with matching hashes, label-rule coverage recorded, full-table row count and
   equal field count, no absolute paths in the JSON, `stat_fields.txt`
   unchanged.
5. **Negative controls** -- each must fail, and each does:
   * a field removed from the list changes the output;
   * a non-float field added is refused with
     `stat_fields.txt lists 'jump_count_max' but its type is i32, expected float`,
     **and no preset file is written**;
   * a corrupted expected hash is refused with the actual hash printed, **and no
     preset file is written**;
   * a tampered value in a copied `presets.txt` is caught by the bit
     comparison. This fourth one exists because the first control alone would
     still pass if the comparison never compared anything;
   * a comment placed **before** the version line is rejected, and comments
     **after** it are accepted. This fifth one guards a real defect found in
     this task's own first output: the generator emitted five header comments
     before `mc_presets 1`, so line 1 was a comment. The plugin's existing
     loadout parser refuses a file whose first line is not exactly the version
     line (`bad_version_line_bom`, `research/P4-OVERRIDE-SLICE.md` 2.1), so
     that file would have been refused whole. The generator now emits the
     version line first and asserts it before writing; the check script
     requires it independently.

`presets.txt` came out byte-identical on every rebuild, so the generator is
deterministic.

## 11. Limits and what is not shown

* **No runtime claim.** These are numbers read out of a file. Whether the engine
  reads a preset row unchanged, whether a preset can be applied to one saved Mii
  per instance, and whether a preset changes how a Mii plays are all unverified
  and outside this task. P2-STAT-API leaves per-instance scoping unresolved and
  P4-STAT-SITES accepted only the counts, not "all uses go through the hooked
  getter".
* **`presets.txt` does not fit the 16 KiB limit** and would be refused whole
  today. Section 4 gives the number and the two ways out.
* **Display-name coverage is 82 of 94**, not 94. The 12 exceptions are null, not
  guessed.
* **Nine of the 282 other float fields are unlabelled**, and some take negative
  values; the list was not extended.
* **Playability flags are a reading of names and message labels**, not a
  measurement of what the game can select. Nothing was removed.
* The MSBT reader covers LBL1 and TXT2 only. Other sections are skipped by their
  declared size. Nothing in this task needs them.
* The tool pins one `fighter_param.prc` hash. On another game build the
  generator refuses it rather than emitting a preset file against an unverified
  table.

## 12. Changed files

| path | kind |
|---|---|
| `tools/stat-presets/build_presets.py` | new |
| `tools/stat-presets/check_presets.py` | new |
| `tools/stat-presets/msbt.py` | new |
| `tools/stat-presets/stat_fields.txt` | new (coordinator-owned content, as specified) |
| `tools/stat-presets/README.md` | new |
| `evidence/P6-PRESET-DATA/check_output.txt` | new |
| `evidence/P6-PRESET-DATA/report_tables.txt` | new |
| `research/P6-PRESET-DATA.md` | new (this file) |
| `scratch/2026-10-05_P6-PRESET-DATA/` | probes and the report-data script |
| `gamedata/mii_customizer/P6-PRESET-DATA/**` | generated data (outside the mod tree) |

Nothing else was modified. No commits, no branches, no plugin change, no
emulator run, no SD access.

## 13. Next experiment

**Set the plugin's preset-file limit and prove a preset is read.** The data side
is done and measured; the open question is on the runtime side and is the
coordinator's:

1. Coordinator picks the size contract from section 4 -- raise the limit to
   25 517+ or shrink the format -- and that is a plugin change, deliberately not
   made here.
2. Then one console test with a single saved Mii and a **single-field** preset
   (`weight` only) to establish that the file is parsed, the preset is found and
   the value reaches the engine. Tier A, and the first thing that would show
   anything at runtime. With a 25 KiB file and 94 presets, a second question
   worth answering in the same run: which kind hash does the UI list first, and
   does the list order match `fighters.json`?

If the limit is not raised, the fallback experiment is to keep 16 KiB and emit
only a chosen subset of fighters, which needs a coordinator decision about which
and is not a data problem.

## Summary

**P6-PRESET-DATA: DONE.** Built `tools/stat-presets/` (generator, check script,
MSBT reader, field list); produced `fighter_param_full.json`, `presets.txt` and
`fighters.json` under `gamedata/mii_customizer/P6-PRESET-DATA/`. Measured 94
rows x 369 fields, 94 presets, 0 skipped, 940 values verified bit-for-bit, 28
checks passing including five negative controls. **`presets.txt` is 25 517 bytes
and does not fit the current 16 KiB plugin limit** -- the coordinator's
decision. Display-name labels resolve for 82 of 94 fighters; 12 exceptions are
left null. 282 other float fields are listed with ranges for a later decision.
No runtime behaviour is claimed. Next: set the size contract, then one console
test with a single-field preset.