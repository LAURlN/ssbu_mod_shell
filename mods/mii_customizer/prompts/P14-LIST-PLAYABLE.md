# P14-LIST-PLAYABLE - only playable characters in the character list

Small data task, any worker (Space Bunny Alpha is enough). Follow workspace AGENTS.md,
mods/mii_customizer/AGENTS.md and STATUS.md. No agents, commits, emulator, SD access; do not
install anything. Paths are relative to mods/mii_customizer/ unless marked
workspace-relative; create every folder INSIDE mods/mii_customizer/; generated game-derived
files go to workspace gamedata/mii_customizer/P14-LIST-PLAYABLE/. Use `python`; write scripts
with the file tool (no heredocs). Write research/P14-LIST-PLAYABLE.md first and extend it.
End with task ID, DONE/PARTIAL/BLOCKED, changed files, checks run, open questions.

Background. The mod's in-game menu lists characters whose stats a Mii Gunner can take. The
list on the console comes from two files generated from the user's own game data:
`list.txt` (format `mc_list 1`: `<preset_name> <message_label>` per row, in fighter order)
and `names.txt` (format `mc_names 1`: `<preset_name> <display name>`). Current files:
workspace gamedata/mii_customizer/COORD-session3/list.txt (86 rows) and names.txt (87
lines). Generator: tools/stat-presets/build_presets.py (`build_list`, which already skips
names starting with `miienemy`), README in the same folder; names.txt is made by
scratch/2026-10-07_coordinator/make_names.py. The preset file `presets_wide.txt` (94
fighters, workspace gamedata/mii_customizer/P10-PRESET-WIDE/) stays as it is: presets may
exist for fighters that are not listed.

The user's request: "remove Giga Bowser and any other potential non-playable characters from
the list". Giga Bowser is the row `koopag`.

Do:
1. Establish, from game data and not from memory, which of the 94 fighter_param rows are
   characters a player can pick on the character select screen. Use a source in the user's
   extracted data that encodes this (for example ui/param/database/ui_chara_db.prc: which
   entries exist, their flags such as "is usable" / "can select", their order number), and
   say which field you used and why. Extract what you need with the existing tools
   (workspace tools/REGISTRY.md) into your gamedata folder. Cross-check with the names:
   a fighter without a `nam_chr1_00_<name>` label is already excluded.
   Report one table of all 94 rows: preset name, display name, in the current list
   (yes/no), playable per your source (yes/no), decision, reason. Pokemon Trainer's three
   Pokemon, the echo fighters and the three Mii classes are playable; the Mii Gunner itself
   stays out of list.txt because row 0 of every page is the Mii Gunner default. Flag
   anything doubtful for the coordinator instead of deciding silently.
2. Make the exclusion reproducible: extend tools/stat-presets/build_presets.py so the list
   skips an explicit set of preset names kept in a small text file next to it (for example
   tools/stat-presets/list_exclude.txt, one name per line with a comment giving the reason),
   in addition to the existing `miienemy` prefix rule. Do not change presets_wide.txt or any
   other output of the tool: show by hash that they are unchanged.
3. Generate the new list.txt and a matching names.txt (same lines as today minus the
   removed presets, plus the `miigunner` line that names the default) into workspace
   gamedata/mii_customizer/P14-LIST-PLAYABLE/. Row order stays fighter order.
4. Check script evidence/P14-LIST-PLAYABLE/check_list.py: both files parse under the rules
   of plugin/src/list.rs and plugin/src/names.rs (you may compile those sources into a
   small host program the way scratch/2026-10-07_coordinator/session_check.rs does, sources
   unchanged); every listed preset exists in presets_wide.txt; `koopag` is absent; the
   diff against the current files is exactly the removed rows; a negative control; exit 1
   on mismatch. Update the tool's README and its existing check if it has one.

Also report (facts only): what the plugin does when a saved Mii's stats preset is not in
the list (read plugin/src/ui.rs `current_row` and plugin/src/menu.rs `start`), since a
loadout file may still name `koopag`.

Exclusive writes: research/P14-LIST-PLAYABLE.md, evidence/P14-LIST-PLAYABLE/,
scratch/2026-10-07_P14-LIST-PLAYABLE/, tools/stat-presets/ (build_presets.py, the new
exclude file, README, its check), workspace gamedata/mii_customizer/P14-LIST-PLAYABLE/.
Do NOT edit plugin/ or the existing gamedata folders.
