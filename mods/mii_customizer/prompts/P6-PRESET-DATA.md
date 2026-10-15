# P6-PRESET-DATA - generate character stat presets from the user's own game files

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md (last sections). Work only on the task
below. No agents, commits, branches, emulator, SD access, framework changes or
edits to other workers' files. Inputs remain read-only. Report exact inputs/hashes,
commands, observed checks, failures and limits. B is offline observation, C pinned
source, D hypothesis; no runtime behavior claims. Coordinator owns
STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report and chat with task
ID, DONE/PARTIAL/BLOCKED, changed files and next experiment. All paths below are
relative to mods/mii_customizer/ unless marked workspace-relative. Create every
folder INSIDE mods/mii_customizer/ and make scripts write there, never into the
current directory. Use `python`, not `python3`.

Background. On the console the mod now gives one saved Mii Gunner a different
weight and walk speed from a text file (evidence/2026-10-05_gate2/RESULT.md).
Next the user wants to pick "the stats of character X" for a Mii. All fighters'
stats are rows of one table, fighter/common/param/fighter_param.prc (94 rows,
keyed by fighter kind; research/P2-STAT-API.md section 2). The preset values must
come from the user's own extracted game file at build time and must not be stored
in the mod's source tree.

One goal: a reusable tool that turns the extracted fighter_param.prc into a preset
file the plugin can read, plus a machine-readable list of the fighters with their
display-name message keys. Tool task. Do not change the plugin.

Read: tools/gunner-catalog/README.md and its readers, research/P1-DATASET.md,
research/P4-STAT-SITES.md (section 3), research/P4-OVERRIDE-SLICE.md section 2.1
(the loadout file format and parser rules the plugin already has).

Inputs (workspace-relative): gamedata/mii_customizer/P1-CATALOG/files/fighter/
common/param/fighter_param.prc (sha256
87fcf45c456d36d3f8a29a5a6d1f847124d55f8fb3db84efdc8f1490edad55c2); the label file
mods/ssbu_mod_new/dumps/scripts/ParamLabels.csv (read that repo's AGENTS.md first;
read-only); ui/message/msg_name.msbt and msg_menu.msbt from the archive if you need
them (extract with tools/arc-extract into gamedata/mii_customizer/P6-PRESET-DATA/).

Build tools/stat-presets/ with README, the generator and a check script:

1. Full table (B). Decode every row: fighter kind hash, its label if
   ParamLabels has one (hash-verified, never guessed), and every field with name
   or hash, type and value. Write it to workspace-relative
   gamedata/mii_customizer/P6-PRESET-DATA/fighter_param_full.json. Report: row
   count, field count per row (must be equal for all rows; say so), how many
   fields are float / int / bool / hash / other, and how many field names are
   unlabelled.
2. Field list. The coordinator-owned file tools/stat-presets/stat_fields.txt
   decides which fields go into presets: one field name per line, `#` comments.
   Create it with exactly these ten (the float stat candidates of the catalogue
   without `scale`): weight, walk_speed_max, run_speed_max, dash_speed,
   air_speed_x_stable, air_speed_y_stable, air_accel_y, air_accel_x_mul, jump_y,
   jump_speed_x. The tool must fail loudly if a listed field is missing from the
   table or is not a float. In the report, ALSO list (do not add) every other
   float field of the row with its Gunner value and its minimum and maximum over
   all 94 rows, so the coordinator can extend the list later.
3. Preset file, format `mc_presets 1` (coordinator contract):
     line 1: `mc_presets 1`
     `fighter <name> <kind_hash: 0x + 10 hex digits>` starts a preset; <name> is
        the fighter's internal name from the kind label with the prefix
        `fighter_kind_` removed (for example `mario`), lowercase [a-z0-9_]
     `<field_hash: 0x + 10 hex digits> <decimal value>` one line per listed
        field, in stat_fields.txt order, value printed with enough digits to
        round-trip the f32 exactly (verify by re-parsing)
     `#` comments and blank lines allowed; ASCII only; `\n` line endings.
   Rows whose kind has no verified label are skipped and listed in the report.
   Output: workspace-relative
   gamedata/mii_customizer/P6-PRESET-DATA/presets.txt. Report its size; state
   whether it fits the plugin's current 16 KiB file limit (it probably will not;
   report the number so the plugin limit can be set from it).
4. Fighter list: gamedata/.../fighters.json with, per preset in file order: name,
   kind hash, row index, and the message label that holds the fighter's display
   name if you can establish it from msg_name.msbt by a rule that holds for all
   fighters you list (state the rule, show five examples, list exceptions; if no
   rule holds, leave the field null and say so). Include the English text only
   as a count check in the report, not in files under mods/.
5. Sanity views in the report: the ten fields for mario, kirby, bowser, fox,
   miigunner, miifighter, miiswordsman next to each other; for each field the
   lowest and highest fighter. Flag rows that look like non-playable or helper
   entries (for example kinds whose names are not selectable characters) without
   removing them; the coordinator decides.
6. Check script: regenerates all three outputs from the inputs and compares;
   asserts input hashes; re-parses presets.txt with an independent reader and
   compares every value bit-for-bit with the table; negative controls (a field
   removed from the list file, a non-float field added, a corrupted input hash)
   must make it fail.

Rules. Nothing game-derived goes under mods/mii_customizer/ except hashes, counts
and the small sanity table in the report. Do not rank or balance characters. Do
not claim that using a preset makes a Mii play like that character; only the
listed numbers are copied.

Exclusive writes: tools/stat-presets/, research/P6-PRESET-DATA.md,
evidence/P6-PRESET-DATA/, scratch/2026-10-05_P6-PRESET-DATA/, workspace-relative
gamedata/mii_customizer/P6-PRESET-DATA/.
