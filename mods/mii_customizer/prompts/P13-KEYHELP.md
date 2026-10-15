# P13-KEYHELP - a "- Advanced Options" button tip on the Mii edit menu

For GPT 6 Luna. Follow workspace AGENTS.md, mods/mii_customizer/AGENTS.md and STATUS.md. No
agents, commits, branches, emulator, SD access, framework-plugin changes; do not install
anything. Paths are relative to mods/mii_customizer/ unless marked workspace-relative; create
every folder INSIDE mods/mii_customizer/; game-derived output (extracted layouts, message
files, dumps) goes to workspace gamedata/mii_customizer/P13-KEYHELP/, never into the mod
tree. Use `python`; write scripts with the file tool (no heredocs). WRITE
research/P13-KEYHELP.md FIRST as a skeleton and extend it after every step. End with task ID,
DONE/PARTIAL/BLOCKED, changed files, what you could not verify.

Context. The mod adds its own menu to the Mii editor (works on the console). A parallel task
(P13-MINUS-ENTRY) makes the Minus button open it from the edit menu. The user wants the
player to be told: "a tip in the top corner. You can just overwrite the ZL Favourite tip
with '- Advanced Options', or add it next to it if that's easy." So on the edit menu
(script ui/script_patch/chara_make/make_mii_edit_actor.lc; reconstructed source
tools/lua-src/make_mii_edit_actor.lua, byte-identical when compiled with tools/luac53-game;
read tools/lua-src/README.md) there is a button tip showing the Favourite button and the
word Favourite. Target, in order of preference:
  (1) keep the Favourite tip and add a second tip "<Minus glyph> Advanced Options" next to it;
  (2) replace the Favourite tip's content with "<Minus glyph> Advanced Options".
Text is English, literal.

What is known (verify what you use): layout facts of the edit screen in
research/P6-EDIT-MENU.md (parts `set_btn_keyhelp_00`, layout `com_btn_keyhelp_00` with
animations BlinkOn/BlinkOff/OnOff/Disable, group `favorite_grp`, pane `nul_keyhelp`; the
script hides `set_btn_keyhelp_00` when FROM_AMIIBO); the footer is driven through
`ComFrameActor.set_button(COMFRAME_FOOTERBUTTON_*)`. Lua pane methods exist for text:
`set_text_message(label)` and `set_text_string(utf8)` (research/P5-UI-API.md section 7;
research/P11-ROW-TEXT.md Q2: MetatableLayoutPane, handler 0x335a490 -> 0x37a22f0, which
decodes 1-3 byte UTF-8 only). On the console: a replaced edit chunk loads, including one of
different length (tier A); a same-length edited layout archive loads (tier A, gate 1 test
2); different-length layout archives are untested and tools/sarc-layout only replaces
members of the same length; an ADDED message label did not resolve (session 1), replacing
an existing label's text was never tried. The mod's plugin sets literal text on native list
rows through 0x3776360 + 0x37a22f0 (tier A), which shows the text setter works at runtime.
Tools: tools/bflyt-inspect, tools/sarc-layout, tools/lua53-inspect, workspace
tools/REGISTRY.md for extraction; 13 extracted message files are under workspace
gamedata/mii_customizer/P11-ROW-TEXT/ui/message/ (read-only for you). Image: workspace
gamedata/ssbu-13.0.4/main.bin; disassembler from the workspace root:
`PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python
mods/mii_customizer/scratch/2026-10-04_P1-ID-REVIEW/d.py win <addr> <n>`.

Part A - facts (offline; tier B only for what your check script re-reads).
A1. Anatomy of the Favourite tip on the edit menu: which layout file and part instance it
    is, its pane tree (text panes, picture panes, names, sizes, positions, text box size and
    alignment, font), which animation shows it, and where its two pieces come from: the word
    (message label? which, in which msbt, exact us_en text) and the button glyph (a
    character code inside the text - give the code units - or a picture pane with a
    texture, or set natively from the virtual-input mapping?). Who sets them: the layout's
    baked text, the Lua script, or native code (function and call site).
A2. How the game writes a button glyph in text: the code units / tag sequence for the Minus
    button in the game's message files (find an existing us_en label that shows Minus and
    give its raw units), and whether such a sequence can pass through `set_text_string`
    (UTF-8, 1-3 byte sequences, straight to 0x37a1cc0 without the tag expander 0x37adbc0:
    are glyphs private-use characters of the font, or tags that only `set_text_message`
    expands?). If only a label can carry the glyph: list existing us_en labels whose text is
    exactly a Minus glyph, or Minus glyph + a short word.
A3. Whether anything rewrites the tip after the script sets it (per frame, on focus change,
    on favourite toggle, on returning from a sub-screen: does the script run its init
    again?), i.e. where the script must set the text so that it stays.
A4. Option (1), a second tip: is there an unused keyhelp part instance or pane on this
    layout, or would it need a new pane (different-length layout, untested route)? Can the
    existing tip carry both in one text ("ZL Favourite   - Advanced Options") within its
    text box, given size and alignment?

Part B - deliverable: the best variant your facts support, script-only if at all possible.
B1. A generator in the style of tools/lua-src/make_entry_source.py - new file
    tools/lua-src/make_keyhelp_source.py - that derives
    tools/lua-src/make_mii_edit_actor_keyhelp.lua from the byte-identical reconstruction by
    adding one or more marked blocks (purely additive; provide a `--strip` proof). The block
    sets the tip per target (1) if A4 allows it in script, else (2). Not when FROM_AMIIBO.
    No pane or part name may be guessed: each must be shown to exist in the layout the
    screen loads. Say what the Lua binding does for a missing pane or part (error that kills
    the screen, or nil), with the handler's address.
B2. Compile (game header, `is_vararg` post-pass as build_check.py does), stage as
    builds/0.6.0-edit-keyhelp/mii_customizer_ui/ (info.toml modelled on
    builds/0.4.0-edit-entry/variant_entry/; chunk at
    ui/script_patch/chara_make/make_mii_edit_actor.lc), MANIFEST.json and
    builds/0.6.0-edit-keyhelp/check_keyhelp.py (rebuild + compare, per-prototype instruction
    diff against the original, every pane/part name checked against the extracted layout,
    negative control, exit 1 on mismatch). build_check.py and negative_controls.py must
    still pass.
B3. If script-only cannot do it, do not fake it: deliver Part A, state exactly what blocks
    it, and describe the smallest other route (same-length layout edit, replacing an
    existing label's text through a message patch, or the plugin's text route) with what
    each would need. If a same-length layout edit suffices, you may stage it as a second
    folder builds/0.6.0-edit-keyhelp/layout_variant/ with its own check.

Report: short answers first; every name, offset and code unit cited with its file and hash;
what is tier D (everything about what the player sees: fit, glyph rendering, persistence);
a console test of at most 4 steps; rollback.

Exclusive writes: research/P13-KEYHELP.md, evidence/P13-KEYHELP/,
scratch/2026-10-07_P13-KEYHELP/, builds/0.6.0-edit-keyhelp/,
tools/lua-src/make_keyhelp_source.py, tools/lua-src/make_mii_edit_actor_keyhelp.lua, workspace
gamedata/mii_customizer/P13-KEYHELP/. Do NOT edit plugin/, tools/lua-src/make_entry_source.py,
tools/lua-src/README.md or any other existing file; P13-MINUS-ENTRY works on the same script
in parallel with its own variant file, and the coordinator merges the two.
