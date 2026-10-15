# P11-ROW-TEXT - literal text on a native list row, and labels for the menu (facts only)

For Space Bunny Alpha. Offline static analysis; nothing is executed or patched. Follow
workspace AGENTS.md, this mod's AGENTS.md and STATUS.md. No agents, commits, emulator, SD
access. Paths are relative to mods/mii_customizer/ unless marked workspace-relative; create
every folder INSIDE mods/mii_customizer/ (extracted game files: workspace
gamedata/mii_customizer/P11-ROW-TEXT/). Use `python`; write scripts with the file tool, not
heredocs. Create research/P11-ROW-TEXT.md FIRST and write each answer into it as soon as you
have it (another task reads it while you work). End with task ID, DONE/PARTIAL/BLOCKED,
changed files, checks run, open questions.

Background (console, tier A): the mod shows its own rows on the Mii maker's native headgear
list. Row text today comes from a hook on 0x3288330, which fills a message-key struct
`{u32 hash, u32 length, char text[0x40]}`; the row filler 0x19ccb20 then finds the panes
`set_txt_val` and `set_txt_val_disable` (0x3776360) and sets the text from that struct
(0x3779b70). So a row can only show a message label that exists in the game. The next menu
needs rows such as "Stats", "Jab", "Forward Tilt". An added label in msg_menu did not
resolve on the console. Plugin task P11-MENU (parallel, not yours) needs to know how to put
a literal string on those panes.

Input: workspace gamedata/ssbu-13.0.4/main.bin (flat; address == file offset; sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613, verify). Disassembler from
the workspace root: `PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python
mods/mii_customizer/scratch/2026-10-04_P1-ID-REVIEW/d.py win <addr> <n>`. Read first:
research/P9-HAT-HANDLES.md section 2, research/P8-HAT-NATIVE.md section 6,
research/P5-UI-API.md (text methods), research/P10-HAT-OPEN.md Q5, research/P5-MSG-PROBE.md.

Q1. `0x3779b70` and `0x3776360` end to end: arguments, what the "part" object returned
    through x8 is, how the message key becomes text (which lookup function, which message
    files or tables it searches: one file, or every loaded msbt by label hash?), and what is
    shown when the key does not exist.
Q2. The native side of the Lua method `set_text_string` (find its registration by name, as
    P1-ID-REVIEW 2.3 and P4-BRIDGE-FACTS did for other bridge names): the handler, its
    arguments (pane object, string encoding UTF-8 or UTF-16, length or terminator), and the
    function it finally calls to set literal text on a text pane. Then: can that function be
    called with what the row filler has at 0x19ccc00..0x19ccc48 (the part found by
    0x3776360)? State exactly which object each needs and how one is obtained from the other,
    or that it cannot be shown. Give entry addresses, argument registers, first four words,
    and whether any of the four is PC-relative.
Q3. Does the later row refresh (scroll, cursor move; P10-HAT-OPEN Q5: only visible rows are
    filled, slot +0x10 from 0x377c76c) call the row filler again for the same row, so text
    set once would be overwritten or must be set on every fill?
Q4. Fallback labels. With the message tools already in the mod (tools/stat-presets/msbt.py)
    and the workspace arc tools (workspace tools/REGISTRY.md), list existing labels in the
    default-language message files whose text is, or is close to, each of: Stats, Jab, Dash
    Attack, Forward/Up/Down Tilt, Forward/Up/Down Smash, Neutral/Forward/Back/Up/Down Air,
    Grab, Pummel, Forward/Back/Up/Down Throw, Neutral/Side/Up/Down Special, Default, None.
    For each: file, label, exact text, and whether that file is one the lookup of Q1
    searches. Say which wanted texts have no label.
Q5. The greyed look. In 0x19ccb20 steps 17-19e (P9-HAT-HANDLES section 2; note 0x328b5d0
    returns 1 for a handle NOT in the table): which pane, animation or flag makes a row look
    unavailable, and what the list does when the cursor is on such a row and decide is
    pressed (0x19ccea0, 0x19cd020, the Lua side in research/P6-HAT-UI.md section 4.6): is
    the decide refused, redirected to another row, or does something else open?

Rules: facts with addresses; tier B only for what your check script re-reads; runtime
behaviour is D; no hook designs. If a question does not resolve, write how far you got and
the next concrete read.

Deliver research/P11-ROW-TEXT.md (short answers first), evidence/P11-ROW-TEXT/ with
disassembly windows and check_p11_row_text.py (image hash, every cited instruction, string
and relocation; negative controls; exit 1 on mismatch; run it once more AFTER your last edit
and paste that output).

Exclusive writes: research/P11-ROW-TEXT.md, evidence/P11-ROW-TEXT/,
scratch/2026-10-06_P11-ROW-TEXT/, workspace gamedata/mii_customizer/P11-ROW-TEXT/.
