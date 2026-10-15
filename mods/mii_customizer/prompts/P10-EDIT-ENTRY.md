# P10-EDIT-ENTRY - edit-menu script that opens the mod list (exit value 7)

For Space Bunny Alpha. Follow workspace AGENTS.md, this mod's AGENTS.md and STATUS.md.
No agents, commits, emulator, SD access. Paths are relative to mods/mii_customizer/
unless marked workspace-relative; create every folder INSIDE mods/mii_customizer/ and
make scripts write there (game-derived files: workspace
gamedata/mii_customizer/P10-EDIT-ENTRY/). Use `python`; write scripts with the file
tool, not heredocs. Create research/P10-EDIT-ENTRY.md first and extend it as you go.
End with task ID, DONE/PARTIAL/BLOCKED, changed files, checks run, open questions.

Background. The Mii editor's edit menu (script
ui/script_patch/chara_make/make_mii_edit_actor.lc, reconstructed byte-identically as
tools/lua-src/make_mii_edit_actor.lua, task P9-EDIT-SOURCE) leaves with an exit value;
native code opens the sub-screen for values 0..6. Decided: the mod uses exit value 7
(benign without the plugin; >= 9 crashes, never publish it). Plugin 0.4.0 (task
P10-UI-SLICE, parallel, not yours) turns 7 into "open the character list". Your task
is the script side. The earlier probe (builds/0.3.1-edit-probe/) did nothing on the
console: pressing Favorite on the Headgear row just toggled favourite. Coordinator
reading of the source: `update` handles INPUT_FAVORITE first (switch_favorite), then
calls update_selector0, where the probe called ComFrameActor.press_decide(); that
addresses the frame's confirm button, not selector0, so get_decided_button_id() stayed
negative. So the probe could not work whether or not the chunk loaded.

Read first: research/P9-EDIT-SOURCE.md, research/P6-EDIT-MENU.md (sections 1-3),
research/P9-EDIT-DISPATCH.md (sections 3, 4, 6), tools/lua-src/README.md,
builds/0.3.1-edit-probe/README.md, evidence/2026-10-05_session1/RESULT_boot2.md.

Part 1 - check the diagnosis (offline). From the bytecode of the 0.3.1 probe chunk and
the original, state the order in which a frame with Favorite pressed runs the
favourite branch and the probe block, and every place the chunk reads
get_decided_button_id / is_decided. Say whether the coordinator's reading holds and
what it cannot show.

Part 2 - loader facts (offline). (a) Confirm that hash40 of the path string
`ui/script_patch/chara_make/make_mii_edit_actor.lc` equals the constant the scene
loads at 0x1808c98 (P9-EDIT-DISPATCH section 2) and do the same for the special-move
chunk path, which is known to load from a mod folder on the console. (b) With the
workspace arc tools (workspace tools/REGISTRY.md), compare the data.arc index entries
of the two files and of the base ui/script/menu/chara_make/make_mii_edit_actor.lc:
existence, sizes, compression, regional / shared / redirect flags, directory. Report
any difference that could make a mod-folder replacement behave differently. Read-only.

Part 3 - the entry script. Generate (never hand-edit; extend the generator approach of
tools/lua-src/make_probe_source.py in a new script) from the byte-identical source:
- In `update`, the Favorite branch becomes: if selector0 has focus and its selected
  button is row 1 (Headgear), then set self.exit_value = 7, self.selector1_selected_id
  = -1, play the decide sound the script already uses, and return true, so `main`
  leaves exactly as it does for a decided row; otherwise switch_favorite as before.
  Nothing else changes. Not under FROM_AMIIBO (the branch already excludes it).
- Use only globals, methods and constants the original chunk already uses, and show
  that for each one (name, where the original uses it). No new INPUT_* names.
- Walk `main` after the loop for exit_value 7 and list every statement it runs,
  compared with exit value 1.
- Two variants: `entry` (as above) and `entry-marker`, which additionally does one
  unconditional audible or visible thing when the screen opens (your choice, same
  only-existing-names rule) so a console boot can tell "chunk loaded" from "not
  loaded" without pressing anything. State exactly what the user will notice.
- Post-pass the is_vararg byte as build_check.py does. The pristine reconstruction must
  still build byte-identically; rerun build_check.py and negative_controls.py and
  report real exit codes.

Deliver builds/0.4.0-edit-entry/ with two mod folders (`variant_entry/mii_customizer_ui/`
and `variant_marker/mii_customizer_ui/`, each with info.toml and the chunk at
ui/script_patch/chara_make/make_mii_edit_actor.lc), MANIFEST.json (sizes, sha256,
per-prototype deltas), README.md and check_entry.py (verifies the tree against the
manifest, parses each info.toml with tomllib, disassembles the changed prototype and
asserts the constant 7 and the absence of any constant >= 9 used as an exit value;
negative controls; exit 1 on mismatch). The generator and generated sources go in
tools/lua-src/ (new files only; do not change existing ones except README.md).

Limits to state plainly: nothing is run; whether the console loads the chunk is
unknown; local names are invented.

Exclusive writes: builds/0.4.0-edit-entry/, tools/lua-src/ (new files + README.md),
research/P10-EDIT-ENTRY.md, evidence/P10-EDIT-ENTRY/, scratch/2026-10-05_P10-EDIT-ENTRY/,
workspace gamedata/mii_customizer/P10-EDIT-ENTRY/.
