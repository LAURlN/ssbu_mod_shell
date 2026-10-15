# P2-STAT-READS - locate where the executable asks for weight and walk_speed_max

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

One goal: list the code sites in the executable that use the two parameter hashes,
so a later reader can tell whether these values are fetched per use or copied once.
Locating task. Do not decide that question yourself, and do not build or design a hook.

Hashes (from research/P2-STAT-API.md section 2): weight 0x0607cd5541,
walk_speed_max 0x0ee2ec2860.

Input: workspace-relative gamedata/ssbu-13.0.4/main.bin, sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613 (rehash first; stop
BLOCKED on mismatch). Flat image, address == file offset; code is 0x100..0x39C8000.
Copy scratch/2026-10-04_P1-ID-REVIEW/d.py into your scratch folder as a starting
disassembler; capstone via
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python (workspace-relative).
Use `python`, not `python3`.

Read research/P2-STAT-API.md sections 3, 4 and 7 for context only.

Steps.
1. Code sites. A 40-bit constant is built in AArch64 by a mov/movz followed by movk
   instructions on the same register. Scan the code range for sequences that
   compose exactly each hash in one register (allow the 2 or 3 instructions to be
   adjacent or separated by at most 4 other instructions that do not write that
   register). Validate your scanner first: it must find a hash you plant in a
   synthetic byte buffer, and must not report a sequence where an intervening
   instruction overwrites the register. Report the count per hash, including zero.
2. Data sites. Search the whole image for each hash as an 8-byte little-endian
   value (also try with the top 24 bits non-zero masked off, i.e. match the low 40
   bits at 8-byte alignment). Report offsets and counts. Do not interpret tables.
3. For each code site (if more than 25 per hash, take the first 25 by address and
   say how many were left): the enclosing function start candidate, a window of 12
   instructions before and 20 after, which register holds the hash, the first `bl`
   or `blr` after it with its target (for `blr`, the load that produced the target
   register, e.g. `ldr x8, [x8, #0x270]`), and what the same window shows about the
   other hash-like argument (a second 40-bit constant, if one is built nearby).
4. For each distinct enclosing function, list its direct `bl` callers (count, and
   the first 10 addresses). Do not go further up.
5. One summary table: hash, site, enclosing function, call target or vtable
   offset, number of callers of the enclosing function.

Rules. Every claim needs instruction addresses. Do not name what a function does
("this is the walk status"), do not guess when it runs, do not connect anything to
fighter kind or to Mii. Vtable offsets may be compared with the declared 0x270
(`get_param_float`) from P2-STAT-API as a plain equal/not-equal observation. Zero
code sites is a valid and useful result; report it and stop after step 2.

Deliver research/P2-STAT-READS.md plus a check script that re-derives every listed
site from the image and exits nonzero on mismatch. Raw windows go in evidence.

Exclusive writes (all under mods/mii_customizer/): research/P2-STAT-READS.md,
evidence/P2-STAT-READS/, scratch/2026-10-04_P2-STAT-READS/.
