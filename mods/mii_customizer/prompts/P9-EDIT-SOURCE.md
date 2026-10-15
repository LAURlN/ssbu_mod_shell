# P9-EDIT-SOURCE - Lua source of the Mii edit menu script, plus one input probe

For Space Bunny Alpha. Follow workspace AGENTS.md, this mod's AGENTS.md and STATUS.md.
No agents, commits, branches, emulator, SD access or edits to other workers' files.
Do not install anything. All paths are relative to mods/mii_customizer/ unless marked
workspace-relative; create every folder INSIDE mods/mii_customizer/ and make scripts write
there. Game-derived files (original or rebuilt chunks, disassembly of them is fine as
evidence text) go only under workspace-relative gamedata/mii_customizer/P9-EDIT-SOURCE/,
except the one probe file named below. Use `python`. Save the report and end with task
ID, DONE/PARTIAL/BLOCKED, changed files and what you could not verify. Write the report
early and extend it as you go.

Why: the mod will add its entry point to the Mii maker's edit menu (the screen with the
rows Name, Headgear, Outfit, Colour, Special Moves, Voice). That script must be editable
as source. P5-LUA-SOURCE did the same for the special-move script; repeat its method.

Read first: research/P5-LUA-SOURCE.md and tools/lua-src/ (method, build_check.py, the
known one-byte difference: main prototype `is_vararg` is 2 in game files and 1 from the
local compiler), research/P6-EDIT-MENU.md (complete trace of this chunk; note it numbers
pcs 1-based as luac prints them), research/P5-UI-API.md (input constants and
`is_pressed` / `is_pressing` usage), tools/luac53-game/README.md,
tools/lua53-inspect/README.md, builds/0.1.0-arc-probes/ and research/P3-ARC-PROBES.md (how
a Lua probe package for the file loader is laid out, with info.toml and manifest).

Input (read-only, workspace-relative):
gamedata/mii_customizer/P1-UI/ui/script_patch/chara_make/make_mii_edit_actor.lc, 10576
bytes, sha256 c777ecc492cea48f6ffd40112b22f96e66219d00969b570a7cc3cf8d7f4a9417. This
patch version is the one the game loads.

Part 1 - source.
Write `tools/lua-src/make_mii_edit_actor.lua` so that compiling it with
tools/luac53-game gives a chunk whose every prototype (instructions, constants, upvalue
descriptors, nested prototype order, parameter counts, stack sizes) equals the original.
Extend tools/lua-src/build_check.py (or add a sibling script with the same conventions) to
build and compare this second file per prototype and to apply and verify the `is_vararg`
byte fix so the final file is byte-identical to the original. Report per prototype:
identical or the exact differences. Local variable names are free (debug info is
stripped); comment the source where P6-EDIT-MENU explains what a block does.

Part 2 - one probe variant (only if part 1 reaches byte identity after the flag fix).
Purpose: show on the console that script code added by the mod can react to a button in
the edit menu and leave the menu through the existing exit path. Behaviour to add, and
nothing else: while `selector0` has focus and its selected button is row 1 (Headgear),
pressing one extra button makes the script behave exactly as if row 1 had been decided
(same sound, `exit_value = 1`, same return value from the update function as the normal
decide path). Choosing the button: use only an input constant and an input object and
method that THIS chunk already reads and calls somewhere (list all of them with pcs
first); if the chunk has no usable button test of its own, stop part 2 and report which
names would be needed and which other Mii maker chunks read them, without guessing that
they exist in this scene. Keep the added code in one clearly marked block of the source,
controlled by a single constant `MC_PROBE_EXIT_VALUE = 1` at the top.
Build the variant with the same toolchain and flag fix. Verify structurally: all
prototypes except the edited one identical to the original; the edited one differs only
by the added block (show the instruction diff); `lua53_inspect verify` passes.
Package it as builds/0.3.1-edit-probe/ in the layout the earlier Lua probe used
(folder `mii_customizer_probe_edit/` with the chunk at
`ui/script_patch/chara_make/make_mii_edit_actor.lc`, info.toml, MANIFEST with sizes and
sha256, a check script, README with the exact console steps and what the user should
see). This one built chunk is the only game-derived file allowed in the mod tree, as with
the earlier probes. Not installed by you.

State clearly in the report: nothing here is run; whether the game accepts a chunk
produced by the local compiler at this path is untested (the earlier accepted probes were
same-length constant edits), so this probe also answers that.

Deliverables: the source file, the extended build check, research/P9-EDIT-SOURCE.md,
evidence/P9-EDIT-SOURCE/ (build and compare output, the instruction diff, negative
controls: at least three source or byte mutations the check must catch, with observed
results), builds/0.3.1-edit-probe/ if part 2 is reached.

Not in scope: native code, the plugin, layouts, message files, other scripts, any design
of the final menu.

Exclusive writes: tools/lua-src/make_mii_edit_actor.lua, tools/lua-src/build_check.py and
new files in tools/lua-src/, research/P9-EDIT-SOURCE.md, evidence/P9-EDIT-SOURCE/,
scratch/2026-10-05_P9-EDIT-SOURCE/, builds/0.3.1-edit-probe/, workspace
gamedata/mii_customizer/P9-EDIT-SOURCE/.
