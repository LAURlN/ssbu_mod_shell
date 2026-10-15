# P4-BRIDGE-FACTS - how Lua arguments reach the skill handlers, and what a hook there must respect

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md. Work only on the task below. No agents,
commits, branches, emulator, SD access, framework changes or edits to other workers'
files. Inputs remain read-only. Report exact inputs/hashes, commands, observed
checks, failures and limits. B is offline observation, C pinned source, D
hypothesis; no runtime behavior claims. Coordinator owns
STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report and chat with task
ID, DONE/PARTIAL/BLOCKED, changed files and next experiment. All paths below are
relative to mods/mii_customizer/ unless marked workspace-relative. Create your
evidence and scratch folders INSIDE mods/mii_customizer/ and make scripts write
there, never into the current directory. Use `python`, not `python3`.

Background (B). The Mii special-move screen's Lua calls
UiScriptPlayer.invoke("get_skill_id", row) and invoke("set_skill_id", row, value).
Native handlers: set 0x19dcf20, get 0x19dcf40, each `cmp w1,#4; b.hs <cold>;
add x8,x0,w1,sxtw; strb/ldrb [x8,#0x100]; ret`. They are reached through
delegates: set_skill_id via vtable 0x50a6e78, invoke thunk 0x19dd950;
get_skill_id via vtable 0x50a6ea0, thunk 0x19dd7d0 (research/P2-SKILL-NATIVE.md).
The coordinator is considering these two handlers as a channel between editor Lua
and the mod's plugin (rows the game never uses would carry mod requests). Before
anyone designs that, we need plain facts about the path. Locating/reading task; do
not design the channel and do not write hook code.

Input: workspace-relative gamedata/ssbu-13.0.4/main.bin, sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613 (rehash first; stop
BLOCKED on mismatch). Flat image, address == file offset. Copy d.py, relocs.py and
lib.py from scratch/2026-10-04_P3-CUSTOMIZE-SITES/ into your scratch folder; do not
edit the originals. capstone:
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python (workspace-relative).

Questions. Answer each with instruction addresses; raw windows go in evidence.
1. Thunk 0x19dd950 (two-argument form, used by set_skill_id and replace_skill).
   Dump it completely (to its last return/tail branch). Report: how it obtains
   each Lua argument (which calls, with which index/immediate), which Lua value
   types it accepts (compare-with-type-tag instructions and their immediates),
   what it does for each accepted type before passing the value on (for example a
   float-to-integer conversion: name the instructions), what it does when the type
   is not accepted or an argument is missing, in which registers the handler
   receives its arguments, and how the handler is called (pointer-to-member load,
   `br`/`blr`). research/P1-ID-REVIEW.md section 2.3 describes the one-argument
   thunk 0x19dc650; use it as a comparison, not as an assumption.
2. Thunk 0x19dd7d0 (get_skill_id). Same questions, plus: what happens to the
   handler's return value - which register is read (w0 or x0, any sign or zero
   extension, any masking), which function receives it, and with what type tag or
   push call it is handed back to Lua. research/P2-SKILL-NATIVE.md says this thunk
   reads the handler pointer at delegate +0x28 first and +0x18 as fallback; show
   both paths and say which one the registration at 0x19de1a0-0x19de1bc uses.
3. The two handlers. For 0x19dcf20 and 0x19dcf40: the instruction words of the
   whole function including its cold block; which of the first four words is
   PC-relative; every direct branch or call in the image that targets the function
   start or any address inside it; every relocated pointer equal to the function
   start (expected: none besides the delegate construction, which builds the
   address in code - show the adrp/add). What is 0x39c20a0, the target of the cold
   block's `bl`: dump its first 12 instructions and state only whether it returns.
4. The same facts as question 3 for replace_skill 0x19dd1a0 and
   replace_skill_subwindow 0x19dd250, first 8 words only.
5. In function 0x19ddb30, between the allocation of the 0x150-byte object and the
   six registrations: is the object's address (x19) or the outer object's (x23)
   stored into any static (adrp-addressed) location? List each store whose base is
   an adrp-derived address. This is to learn whether the live screen object can be
   found from a static address; report what the instructions show and nothing more.
6. From research/P2-SKILL-STORE.md: the editor working record W is at static
   0x5306b78 and its first u32 is the saved-fighter ID. Re-verify with the
   instructions at 0x180fca8-0x180fcb4 and 0x180d320-0x180d328 that both use
   0x5306b78, and list any other adrp+add materialisation of exactly 0x5306b78 in
   the code range (count and addresses).

Rules. Every claim needs addresses. Separate what instructions show (B) from what
you think it means (D). Do not name Lua API functions from their shape unless a
string or symbol in the image names them; describe them by address and observed
arguments. Do not propose a design.

Deliver research/P4-BRIDGE-FACTS.md with one section per question and a short
table "value passed from Lua -> value seen by handler" for integers, floats and
other types, plus a check script that re-derives every cited instruction from the
image and exits nonzero on mismatch.

Exclusive writes: research/P4-BRIDGE-FACTS.md, evidence/P4-BRIDGE-FACTS/,
scratch/2026-10-04_P4-BRIDGE-FACTS/.
