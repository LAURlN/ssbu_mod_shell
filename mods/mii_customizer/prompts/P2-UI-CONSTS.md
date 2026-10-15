# P2-UI-CONSTS - locate the values the game gives to nine editor Lua globals

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md. Work only on the task below. No agents,
commits, branches, emulator, SD access, framework changes or edits to other workers'
files. Inputs remain read-only. Report exact inputs/hashes, commands, observed
checks, failures and limits. B is offline observation, C pinned source, D
hypothesis; no runtime behavior claims. Coordinator owns
STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report and chat with task
ID, DONE/PARTIAL/BLOCKED, changed files and next experiment. All paths below are
relative to mods/mii_customizer/ unless marked workspace-relative. Create your
evidence and scratch folders INSIDE mods/mii_customizer/, not at the workspace root.

One goal: find where the executable registers nine Lua global names and what value
each receives. Locating task; no interpretation of what the game does with them.

Names, exactly. Group 1 (special screen): SPECIAL_SKILL_NUM, SKILL_COMMAND_NUM,
SKILL_COMMAND_NORMAL, SKILL_COMMAND_SIDE, SKILL_COMMAND_UPPER, SKILL_COMMAND_LOWER,
INPUT_OK. Group 2 (editor screen): IS_SKILL_EDITABLE, IS_READ_ONLY.

Input: workspace-relative gamedata/ssbu-13.0.4/main.bin, sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613 (rehash first; stop
BLOCKED on mismatch). Flat image, address == file offset.

Read research/P2-SKILL-NATIVE.md first. It already found that group 1's strings are
referenced inside function 0x19ddb30 and passed to `bl 0x33750a0`, with string
addresses listed, and its full dump of that function is
evidence/P2-SKILL-NATIVE/02_enclosing_function_0x19ddb30.txt. Reuse its scratch
scripts by copying them into your own scratch folder; do not edit the originals.
capstone: PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python
(workspace-relative). Use `python`, not `python3`.

Steps.
1. Group 1: at each of the seven call sites of 0x33750a0, report every argument
   register at the call (x0..x4, w and x forms, and d0/s0 if a float is set up),
   with the instruction that defines it. A value is established only if its
   definition is an immediate or adrp target inside the window you dump. If it comes
   from a load or an earlier register, give that provenance as far as the enclosing
   function shows it and mark it "not a constant".
2. Dump the first 60 instructions of 0x33750a0 as a raw window, and state only which
   argument registers it reads before its first call. This is to tell an integer
   value argument from a float or a pointer; do not analyse further.
3. Group 2: find each string (NUL-terminated, count occurrences including zero),
   its adrp+add reference sites, the enclosing function start, and apply step 1 to
   the call that receives the name. If the registration function is not 0x33750a0,
   say which it is and dump its first 60 instructions too.
4. For IS_SKILL_EDITABLE and IS_READ_ONLY only: if the value is not a constant,
   report the load it comes from (base register, offset, and where that base
   register was defined inside the enclosing function). Stop there. Do not chase the
   object across functions.

Every claim needs instruction addresses. Do not infer a value from a name
("NORMAL is probably 0"). Do not match bare immediates across the binary. If the
same name is registered in more than one function, list every site.

Deliver research/P2-UI-CONSTS.md with one table: name, string address, reference
site, enclosing function, registration function, value or value provenance,
confidence note. Add a check script that re-derives each address and value from
the image and exits nonzero on any mismatch. Raw windows go in evidence.

Exclusive writes (all under mods/mii_customizer/): research/P2-UI-CONSTS.md,
evidence/P2-UI-CONSTS/, scratch/2026-10-04_P2-UI-CONSTS/.
