# P10-PRESET-WIDE - wider character presets and the list file

For Space Bunny Alpha. Follow workspace AGENTS.md, this mod's AGENTS.md and STATUS.md.
No agents, commits, emulator, SD access. Paths are relative to mods/mii_customizer/
unless marked workspace-relative; create every folder INSIDE mods/mii_customizer/.
Everything extracted or generated from game files goes under workspace
gamedata/mii_customizer/P10-PRESET-WIDE/, never into the mod tree, and check scripts
must clean up temporary game-derived files. Use `python`; write scripts with the file
tool, not heredocs. Create research/P10-PRESET-WIDE.md first and extend it as you go.
End with task ID, DONE/PARTIAL/BLOCKED, changed files, checks run, open questions.

Background (console, tier A): plugin 0.3.0 gives a saved Mii Gunner the stats of a
character preset. It overrides a field only when the engine asks for it through the
per-fighter float getter 0x4e53e0 (vtable slot +0x270 of the object at [accessor+0x50],
field hash in x1, x2 == 0). Today a preset has ten movement fields
(tools/stat-presets/stat_fields.txt); all ten were requested and overridden on the
console. The user wants a Mii to feel much more like the chosen character. The plugin
accepts up to 48 fields per preset and 48 distinct field hashes per file with no code
change, so the next step is data: more fields, chosen by evidence.

Read first: tools/stat-presets/README.md and its scripts, research/P6-PRESET-DATA.md,
evidence/P6-PRESET-DATA/W2-REVIEW.md, research/P4-STAT-SITES.md (method, sections 2-5,
9), prompts/P7-PRESET-ENGINE.md (contract A), research/P7-PRESET-ENGINE.md section 1.

Part 1 - which fields qualify. For every field of the fighter_param table (369 per
row in fighter_param_full.json) whose type is float: find the code sites in workspace
gamedata/ssbu-13.0.4/main.bin that materialise its hash40 and call through slot +0x270
with the P4-STAT-SITES shape. Reuse that scanner by copying it into your scratch (do
not edit the original); validate it first by reproducing P4's site counts for the
existing ten fields. Output one table: field name (if verified), hash, type, number of
+0x270 sites, number of sites with another displacement, x2 at the sites, Mii Gunner's
value, min / max over all fighters, number of distinct values. A field qualifies if it
is float, has at least one +0x270 site with x2 == 0, and differs between fighters.
List integer fields with sites through +0x250 separately (not usable yet; a later
plugin task needs them). Whole-image scans can take minutes; say how long.

Part 2 - choose at most 48. The existing ten stay first, in the same order. Add the
qualifying fields; if more than 38 qualify, rank by how much they shape how a fighter
moves and lands (ground and air movement, jumps, gravity and fall, landing, friction,
then the rest) and put the cut in the report with the reason for each decision. Flag
for coordinator review instead of including: size/scale-like fields, anything whose
values look like indexes, frame counts stored as floats that tie to animation length,
and fields where any fighter has 0 or a negative value. Write the choice to a NEW
file tools/stat-presets/stat_fields_wide.txt; do not change stat_fields.txt.

Part 3 - generate. Give build_presets.py options for the field file and the output
folder (defaults unchanged). `presets.txt` from the default options must stay
byte-identical (sha256 f6acbba17d510aae0f0a2cc49cc5417287d4f0d0a8428dbf52d3ca4505865c0d;
show it). New outputs under workspace gamedata/mii_customizer/P10-PRESET-WIDE/:
- `presets_wide.txt`, format `mc_presets 1` (contract A: at most 512 KiB, 128 presets,
  48 fields per preset, 48 distinct hashes, names [a-z0-9_]{1,31}, finite values).
- `list.txt`, new format `mc_list 1` (contract F of prompts/P10-UI-SLICE.md): line 1
  exactly `mc_list 1`, then `<preset_name> <message_label>` per line in fighter_param
  table order; only fighters whose label `nam_chr1_00_<name>` exists in
  ui/message/msg_name.msbt with non-empty single-line text; names starting with
  `miienemy` left out; at most 128 lines, at most 16 KiB, label [a-z0-9_]{1,63}.
  Report every fighter left out and why, and show five lines with the resolved text.
- `fields_wide.json`: the Part 1 table plus the decision per field.
Validate presets_wide.txt against the plugin's rules: if a P7 host-side checker
(scratch/2026-10-05_P7-PRESET-ENGINE/, read-only, do not edit plugin/) can take a file
path, run it and report its output; otherwise check with your own model of contract A
and say that.

Part 4 - sanity table for the coordinator. For Mii Gunner and for mario, fox, purin,
ganon, kirby: every chosen field's value side by side, with the fields that differ
most from the Gunner marked. This is what the user will feel in the next test.

Check script evidence/P10-PRESET-WIDE/check_preset_wide.py: regenerates into a
temporary folder under workspace gamedata/, compares, checks every limit and the
list/preset cross-references, runs negative controls (a 49th field, a duplicate name,
a list line naming a missing preset, a label that does not exist), removes its
temporary files, exits 1 on any mismatch. Update tools/stat-presets/README.md.

Limits to state plainly: nothing is run in the game; a static site proves the engine
can ask through the hook, not that it does during play (the plugin log shows that
per field after the console test).

Exclusive writes: tools/stat-presets/ (stat_fields.txt read-only),
research/P10-PRESET-WIDE.md, evidence/P10-PRESET-WIDE/,
scratch/2026-10-05_P10-PRESET-WIDE/, workspace gamedata/mii_customizer/P10-PRESET-WIDE/.
