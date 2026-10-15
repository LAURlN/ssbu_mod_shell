---
purpose: Generate the character stat presets the Mii Gunner plugin will read, from the user's own extracted game files
usage: python -B mods/mii_customizer/tools/stat-presets/build_presets.py  /  python -B mods/mii_customizer/tools/stat-presets/check_presets.py
status: working (offline)
lang: python (stdlib only)
updated: 2026-10-07
---

# stat-presets

Turns the user's extracted `fighter/common/param/fighter_param.prc` into a preset
file the plugin can read, plus a machine-readable list of the fighters and the
message label that carries each one's display name.

Built for task `P6-PRESET-DATA`. Status: **working** (offline). Evidence tier
**B** -- everything is measured from pinned local files. No console, no
emulator, no runtime behaviour is claimed anywhere in this tool.

## What it is not

* Not a claim that using a preset makes a Mii play like that character. The
  tool copies the numbers in the table and nothing else.
* Not a ranking or a balance pass. The presets are in table order; no field is
  tuned, weighted or ordered by strength.
* Not a save format and not a plugin change. The plugin is untouched.
* Not an installer. It writes three files under `gamedata/` and nothing else.

## Files

| file | role |
|---|---|
| `build_presets.py` | the generator |
| `check_presets.py` | regenerates, compares and runs the negative controls; also the smoke check |
| `list_exclude.txt` | explicit, reviewed preset names to omit from `list.txt`, each with a reason |
| `msbt.py` | minimal read-only MSBT reader, enough to resolve a display-name label |
| `stat_fields.txt` | coordinator-owned list of the fields that go into a preset |
| `stat_fields_wide.txt` | P10-PRESET-WIDE: the widened list (41 fields, the first ten unchanged); `stat_fields.txt` stays authoritative for the default run |
| `stat_fields_wide_decisions.json` | P10-PRESET-WIDE: decision + reason for all 369 table fields (included / flagged / excluded / not qualifying) |

Stdlib only. `build_presets.py` imports the shared reader
`mods/ssbu_mod_new/src/pgwr/tools/prc.py` **read-only by path** and never
modifies it. `msbt.py` is a transcription of the pinned `msbt-rs` readers (see
its module docstring for the commit and the files that were read).

## Outputs

All workspace-relative, all game-derived, all outside the mod tree:

| path | content |
|---|---|
| `gamedata/mii_customizer/P6-PRESET-DATA/fighter_param_full.json` | every row, every field: hash, name if verified, type, value, f32 bits |
| `gamedata/mii_customizer/P6-PRESET-DATA/presets.txt` | the `mc_presets 1` file the plugin reads |
| `gamedata/mii_customizer/P6-PRESET-DATA/fighters.json` | name, kind hash, row index, display-name label, in preset order |

`ui/message/msg_name.msbt` and `ui/message/msg_menu.msbt` were extracted with
`tools/arc-extract` into
`gamedata/mii_customizer/P6-PRESET-DATA/files/ui/message/`. Only `msg_name.msbt`
is read by the generator; `msg_menu.msbt` is recorded in the report as the
cross-check input and is not an input to these outputs.

## Inputs (read-only)

| input | sha256 |
|---|---|
| `gamedata/mii_customizer/P1-CATALOG/files/fighter/common/param/fighter_param.prc` | `87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2` |
| `mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv` | `6ae7f792609612370e6b9244e1d6986ebd8ced9bbb77fad49de8c568919344f4` |
| `gamedata/mii_customizer/P6-PRESET-DATA/files/ui/message/msg_name.msbt` | `9efc357db8ea46e671222dbbd90bbdc0ea5455383090fae3fe2ba6017e9da3ad` |

`ParamLabels.csv` is a **name dictionary only**. A name is used only when
`hash40(name)` equals the hash it is filed under, so a wrong or stale label
makes the tool skip the row loudly rather than invent a name.

## Usage

From the workspace root:

```sh
# generate
python -B mods/mii_customizer/tools/stat-presets/build_presets.py

# check (exit 0 = every check passed)
python -B mods/mii_customizer/tools/stat-presets/check_presets.py
```

Optional arguments, all defaulting to the workspace layout and all relative:

```
--fighter-param  fighter_param.prc
--labels         ParamLabels.csv
--msg-name       msg_name.msbt
--fields         stat_fields.txt
--out-dir        gamedata/mii_customizer/P6-PRESET-DATA
--expect-hash    sha256 fighter_param.prc must have (repeatable; default = the pinned one)
--write-list     also write list.txt and fields_wide.json (P10-PRESET-WIDE)
--decisions      stat_fields_wide_decisions.json
--field-table    gamedata/mii_customizer/P10-PRESET-WIDE/field_table.json
--label-prefix   nam_chr1_00_      --list-name list.txt  --fields-json-name fields_wide.json
--list-exclude   mods/mii_customizer/tools/stat-presets/list_exclude.txt
--presets-name   presets.txt       --fighters-name fighters.json  --full-name fighter_param_full.json
```

Defaults reproduce the P6 outputs **byte for byte**: without `--write-list`
and with default names, `presets.txt` still hashes to
`f6acbba17d510aae0f0a2cc49cc5417287d4f0d0a8428dbf52d3ca4505865c0d`
(asserted by `evidence/P10-PRESET-WIDE/check_preset_wide.py`).

## The `mc_presets 1` format

```
mc_presets 1
# Mii Customizer stat presets, format mc_presets 1
# Generated from the user's own fighter/common/param/fighter_param.prc
# sha256 87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2
...
fighter mario 0x1254206ce1
0x0607cd5541 98
0x0ee2ec2860 1.15499997
...
```

* **Line 1 is the version line.** Comments and blank lines are allowed
  *after* it, never before it: the plugin's existing loadout parser refuses a
  file whose first line is not exactly the version line, so a leading comment
  would get the whole file rejected. The generator asserts this before writing
  and `check_presets.py` requires it with an independent reader. The file is
  pure ASCII with `\n` endings.
* `fighter <name> <kind_hash>` starts a preset. `<name>` is the kind's internal
  name from the `fighter_kind_` label with that prefix removed, lowercase
  `[a-z0-9_]`. `<kind_hash>` is `0x` plus ten hex digits.
* One `<field_hash> <value>` line per listed field, in `stat_fields.txt` order.
  Values are printed with `%.9g`, which is more decimal digits than binary32
  needs, so each value re-parses to the same f32. The generator re-parses every
  value it writes and aborts if any bit pattern differs; the check script
  repeats the comparison with an independent reader.

## The field list

`stat_fields.txt` decides which fields go into a preset: one field name per
line, `#` comments. The generator **fails loudly** if a listed field is missing
from the table or is not a float, before writing anything. The current list is
the ten float stat candidates of the P1-DATASET catalogue without `scale`.
`jump_count_max` (i32) is deliberately absent: it needs the `+0x250` integer
getter, not the `+0x270` float one.

The 282 other float fields of the row, with the Gunner value and the minimum
and maximum over all 94 rows, are listed in
`research/P6-PRESET-DATA.md` section 5 so the list can be extended later.
It has been extended: P10-PRESET-WIDE surveyed all 369 fields against the
13.0.4 image and wrote `stat_fields_wide.txt` (see the section below); the
per-field survey with values and decisions is
`gamedata/mii_customizer/P10-PRESET-WIDE/fields_wide.json`.

## P10-PRESET-WIDE: the wide list and `list.txt`

`stat_fields_wide.txt` widens the preset from 10 to **41 fields** (limit 48).
Its first ten are `stat_fields.txt` unchanged and in the same order; the rest
were chosen by evidence - float, at least one `+0x270` code site with
x2 == 0 in the 13.0.4 image, value differs between fighters - then ranked by
movement impact. How each of the 369 fields was decided, and why, is in
`stat_fields_wide_decisions.json` and `research/P10-PRESET-WIDE.md`.

Wide run (workspace-relative, all game-derived, outside the mod tree):

```sh
python -B mods/mii_customizer/tools/stat-presets/build_presets.py \
  --fields mods/mii_customizer/tools/stat-presets/stat_fields_wide.txt \
  --out-dir gamedata/mii_customizer/P10-PRESET-WIDE \
  --presets-name presets_wide.txt --write-list
```

Outputs in `gamedata/mii_customizer/P10-PRESET-WIDE/`:

| path | content |
|---|---|
| `presets_wide.txt` | `mc_presets 1`, 94 presets x 41 fields, 89003 bytes, 41 distinct hashes (contract A limits 512 KiB / 128 / 48 / 48) |
| `list.txt` | Historical P10 `mc_list 1`: `<preset_name> <message_label>` in table order, 87 entries, 2600 bytes; labels resolve in `msg_name.msbt`, `miienemy*` and unlabelled fighters left out |
| `fields_wide.json` | the Part 1 field table (sites, x2, values) merged with the per-field decision |
| `sanity_table.md` | Part 4: the 41 fields side by side for the Gunner + mario/fox/purin/ganon/kirby |
| `fighters.json`, `fighter_param_full.json`, `field_table.*`, `sites_all.json` | same shapes as the P6 / P10 survey outputs |

Check, from the workspace root (exit 0 = all green):

```sh
python -B mods/mii_customizer/evidence/P10-PRESET-WIDE/check_preset_wide.py
```

It regenerates the wide **and** the default outputs into a temp folder under
`gamedata/mii_customizer/P10-PRESET-WIDE/`, compares them byte for byte,
validates contract A and contract F with its own model, checks the
list/preset cross-references in both directions, runs four negative controls
(a 49th field, a duplicate preset name, a list line naming a missing preset,
a label that does not exist), runs the plugin's own parser
(`builds/.cache/host-test/preset_report_p7.exe`, built read-only from the P7
scratch), and removes its temp folder. 29 checks, all passing as of
2026-10-05.

That P10 check captures the historical 87-entry list and predates the P14
exclusions. Its list regeneration comparison is expected to differ now that
the default generator excludes `koopag` and `miigunner`; use the P14 checker
below for the current list. The old P10 evidence files remain unchanged.

## Measured results

94 rows, 369 fields each (equal for every row), 94 presets written and 0 skipped,
`presets.txt` 25517 bytes. **It does not fit the plugin's current 16 KiB file
limit** -- see section 5 of the report for the number to set the limit from.

## Display-name label rule

`display_name_label = "nam_chr0_00_" + <fighter internal name>`, resolved in
`ui/message/msg_name.msbt`. It holds for 82 of the 94 kinds. The other families
(`nam_chr1_00_`, `nam_chr2_00_`, `nam_chr3_00_`, `nam_chr_no_00_`) do not
resolve for all kinds, so they are **not** used as a fallback: choosing one
would be a guess about which screen reads it. Where the rule does not hold the
field is `null` and the kind is listed in
`display_name_label_rule_exceptions`.

Only the label is stored. The English text stays in the game file and appears
in the report as a count only.

## Checks

`check_presets.py`, **31 checks, 0 failed, exit 0** (including the P14 exclusion-file assertion):

1. **Pinned inputs** -- the three input hashes are asserted before anything else.
2. **Regeneration** -- all three outputs are rebuilt into
   workspace `gamedata/mii_customizer/P6-PRESET-DATA/check-tmp/` (removed at exit) and compared byte-for-byte, and again
   under `PYTHONHASHSEED` 0, 1 and 12345.
3. **Independent re-parse** -- `presets.txt` is read by a tokenizer inside the
   check script that shares no code with the generator, is strict about CRLF,
   bare CR, non-ASCII, field counts and value syntax, and compares every value
   **bit-for-bit** with the `.prc` (940 values).
4. **Contract structure** -- version line, field order equal to
   `stat_fields.txt`, one preset per kind, names matching `[a-z0-9_]`, every
   name traceable to a hash-verified kind label, `fighters.json` in the same
   order as `presets.txt`, no absolute paths in the JSON.
5. **Negative controls** -- each must fail:
   * a field removed from the list changes the output;
   * a non-float field added (`jump_count_max`) is refused with
     `expected float`, and no preset file is written;
   * a corrupted expected hash is refused, and no preset file is written;
   * a tampered value in a copied `presets.txt` is caught by the bit
     comparison, which is what keeps control (a) from being vacuous;
   * a comment before the version line is rejected while comments after it are
   accepted.

## P14-LIST-PLAYABLE: current list filtering

The default explicit exclusions are `koopag` (the character database marks it
as a boss with `can_select=false` and `disp_order=-1`) and `miigunner` (row 0
is the Mii Gunner default on each character page). The existing `miienemy*`
prefix rule remains. These exclusions change `list.txt` only; all 94 presets
remain in `presets_wide.txt`.

The current generated files are under workspace
`gamedata/mii_customizer/P14-LIST-PLAYABLE/`. Generate them and run the source
and parser checks from the workspace root:

```sh
python -B mods/mii_customizer/scratch/2026-10-07_P14-LIST-PLAYABLE/make_outputs.py
python -B mods/mii_customizer/evidence/P14-LIST-PLAYABLE/check_list.py
```

The P14 checker compares all non-list generated outputs by SHA-256 with the
P10 artifacts and validates both files against the plugin contracts. The
older P10 evidence remains the record of the 87-row pre-filter list.

The check never writes to `stat_fields.txt` or to `gamedata/`; it asserts the
field list is unchanged.

## Limits

* The tool reads the table; it does not show the engine reads it unchanged.
  Per-row runtime application is not established (P2-STAT-API).
* The label file decides names, not playability. The P14 report determines
  selectability from the extracted character database and records the field
  and special cases in `research/P14-LIST-PLAYABLE.md`.
* Display-name coverage is 82 of 94. The 12 exceptions are listed rather than
  filled in with a guessed label.
