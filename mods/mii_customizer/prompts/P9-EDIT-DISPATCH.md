# P9-EDIT-DISPATCH - finish the edit-scene dispatch report from existing evidence

For Space Bunny Alpha. Follow workspace AGENTS.md, this mod's AGENTS.md and STATUS.md.
No agents, commits, branches, emulator, SD access or edits to other workers' files.
Offline static analysis only; nothing is executed or patched. All paths are relative to
mods/mii_customizer/ unless marked workspace-relative; create every folder INSIDE
mods/mii_customizer/ and make scripts write there. Use `python`. Save the report and end
with task ID, DONE/PARTIAL/BLOCKED, changed files and what you could not verify.

Situation: the task P8-EDIT-DISPATCH (prompts/P8-EDIT-DISPATCH.md, read it for the method
and tool setup) stopped without writing a report. It left 56 evidence files in
evidence/P8-EDIT-DISPATCH/ and scripts in scratch/2026-10-05_P8-EDIT-DISPATCH/, including
a check script `check_p8.py` that currently FAILS (five wrong handler-table
expectations). Treat all of that as unreviewed notes by someone else: reuse it, but
re-read every instruction you cite from workspace-relative gamedata/ssbu-13.0.4/main.bin
(sha256 f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613). Copy what you
need into your own folders; do not edit the old ones.

What the coordinator already re-read (B) and you can build on:
- `0x180a030` (a method of the Mii editor scene, scene in x19): reads the edit script's
  exit value as `w8 = [[[x19+0x178]+0x80]+0x128]` (0x180a07c..0x180a098); negative goes to
  0x180a1cc; otherwise pushes state `w8 + 4` at `x19 + 0xf8 + 4*index`, index at
  `x19+0x144`, limit 0x13 (0x180a0a0..0x180a0c4); then special cases value 5
  (0x180a0cc) and value 6 (0x180a0d0).
- `0x180ce40`: takes the top state, requires state < 0xd, loads a pointer-to-member pair
  from `x19 + 0x28 + 16*state` and calls it.
- The scene function 0x1808980 stores six child objects at scene+0x178..+0x1a0
  (0x1809498..0x1809934). Child constructors load their script by path hash through
  `bl 0x32caa90` with x3 = hash40 of the path: 0x19ceb30 -> make_mii_hat_actor,
  0x19c7830 -> make_mii_body_actor, 0x19ddb30 -> make_mii_special_actor,
  0x19e33e0 -> make_mii_voice_actor (evidence file 49).
- `get_exit_value` is called at 0x19ca8ec..0x19ca92c and the integer result is stored at
  obj+0x128 (0x19ca93c..0x19ca94c: `mov x8,x19; ldr x9,[x8,#0x10]!; str w0,[x8,#0x118]`),
  which has the same offset as the field 0x180a030 reads; that `obj` is the object at
  `[[scene+0x178]+0x80]` is likely but NOT established.

Deliver a report that answers, with addresses and instructions:
1. The state table: where the 13 handler pairs at scene+0x28 are written (in 0x1808980 or
   elsewhere), and for each state 0..12 the handler address and one line on what it does.
   Which state shows the edit menu, which ones run the name, headgear, outfit, colour,
   special-move and voice sub-screens (tie each to the child object slot it uses and, via
   the constructor's script hash, to its script).
2. The six child slots +0x178..+0x1a0: constructor address, object size, script path
   (hash and matched string) for each. For slots whose constructor shows no script hash
   (0x19e0910, 0x19c9340 in evidence file 49), say what they are as far as readable.
3. The exit value: follow it from the script call (0x19ca8ec) to the field 0x180a030
   reads. Is it the same object, and which instruction copies or exposes it? Give the
   exact meaning of the three flag bytes read at +0x130, +0x131, +0x132.
4. Value by value, what 0x180a030 does for exit values 0, 1, 2, 3, 4, 5, 6, for 7 and
   above, and for negative values: which states get pushed, in which order, and what
   else is written. State plainly what happens for value 7 (state 11) and 8 (state 12)
   according to the code: do they land in existing handlers?
5. Return: how a sub-screen state ends (pop of the state stack: where is +0x144
   decremented) and how the edit menu state is resumed.
6. `EXIT_VALUE_DECIDE`, `EXIT_VALUE_CANCEL`, `IS_SKILL_EDITABLE`, `IS_READ_ONLY`,
   `FROM_AMIIBO`: where they are registered (evidence file 01 names 0x1808f40) and with
   which values or source fields.
7. Hook facts: for the instruction range 0x180a098..0x180a0c8, which registers are live
   and free; and for function entry 0x180a030, the first four instruction words and
   whether any is PC-relative. No design.

Deliverables: research/P9-EDIT-DISPATCH.md; evidence/P9-EDIT-DISPATCH/ with the windows
you rely on and a check script that re-reads every cited address from main.bin, exits
non-zero on mismatch, passes, and has at least three negative controls you ran. Paste the
last lines of the check run into the report. Write the report early and extend it as you
go, so that a stop does not lose the results again.

Not in scope: patching, hooks, plugin code, Lua edits, the headgear list internals.

Exclusive writes: research/P9-EDIT-DISPATCH.md, evidence/P9-EDIT-DISPATCH/,
scratch/2026-10-05_P9-EDIT-DISPATCH/.
