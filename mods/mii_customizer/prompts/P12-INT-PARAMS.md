# P12-INT-PARAMS - finish P11-INT-PARAMS: report and check for the integer-parameter getter

For Space Bunny Alpha. Offline static analysis; nothing is executed or patched. Follow
workspace AGENTS.md, this mod's AGENTS.md and STATUS.md. No agents, commits, emulator, SD
access. Paths are relative to mods/mii_customizer/ unless marked workspace-relative; create
every folder INSIDE mods/mii_customizer/. Use `python`; write scripts with the file tool, not
heredocs. End with task ID, DONE/PARTIAL/BLOCKED, changed files, checks run, open questions.

The previous worker on this question stopped without writing its report. What it left:
- prompts/P11-INT-PARAMS.md: the four questions Q1..Q4. They still apply; read it first.
- research/P11-INT-PARAMS.md: an empty skeleton with a coordinator banner.
- scratch/2026-10-06_P11-INT-PARAMS/: its scripts (q1_thunks.py, scan_int.py, q3_data.py,
  make_tables.py, probe_mlist.py, probe_anims.py and others). Unreviewed.
- workspace gamedata/mii_customizer/P11-INT-PARAMS/: int_table.md/.json (Q2),
  sites250.md, others_table.md/.json (Q4), sites_int.json. Unreviewed.
- evidence/P11-INT-PARAMS/: empty.

Your job is to turn that into a finished, checked report. Do NOT start from zero and do NOT
trust the tables: reproduce them.

ORDER OF WORK (write the report after each step, not at the end):
1. Replace the skeleton body of research/P11-INT-PARAMS.md (keep the coordinator banner) with
   a "Short answers" section holding Q2 and Q4 as they stand in the left-over tables, marked
   "unverified, left by the previous worker". Do this within your first minutes.
2. Q1 (nothing was left for it): slot +0x250 of vtable 0x4f89490 in workspace
   gamedata/ssbu-13.0.4/main.bin (verify sha256 f70c97d2...7613). The function, full
   disassembly, first four words and whether any is PC-relative, what it forwards to (compare
   0x4e53e0 in slot +0x270), argument and return registers, which other slots re-dispatch into
   it, and whether the same function sits in vtables of other classes. Write it into the report.
3. Rerun the left-over scanners from a copy in scratch/2026-10-07_P12-INT-PARAMS/ and compare
   with the left-over tables; first validate by reproducing P4's `jump_count_max` sites
   (research/P4-STAT-SITES.md section 6 and example 8.2). Any difference: say which is right
   and why. Then mark Q2 and Q4 verified or corrected.
4. Q3: the integer fields that qualify for a preset (integer, at least one +0x250 site with
   x2 == 0, value differs between fighters). For each: Mii Gunner's value, min/max/distinct
   values over all fighters, what it plausibly controls (D), and a flag for coordinator review
   when it is an index, a selector, a flag set or a count that resources depend on. For
   `jump_count_max`: which fighters have more than 2, and whether Mii Gunner's motion list
   (the file P1-DATASET used, read-only) has the motions those fighters use for extra jumps.
5. evidence/P11-INT-PARAMS/check_p11_int_params.py: image hash, every cited instruction word
   and relocation, the site counts of Q2/Q4, Q1's slot contents; at least four negative
   controls behind `--neg` that must each fail; exit 1 on any mismatch. Run it once more
   AFTER your last edit of the report and paste both outputs into the report.

Disassembler, from the workspace root:
`PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python
mods/mii_customizer/scratch/2026-10-04_P1-ID-REVIEW/d.py win <addr> <n>`.

Rules: facts with addresses; tier B only for what the check script re-reads; runtime
behaviour is D; no hook code; no recommendation which fields to ship.

Exclusive writes: research/P11-INT-PARAMS.md, evidence/P11-INT-PARAMS/,
scratch/2026-10-07_P12-INT-PARAMS/, workspace gamedata/mii_customizer/P11-INT-PARAMS/.
Do not edit the previous worker's scratch folder.
