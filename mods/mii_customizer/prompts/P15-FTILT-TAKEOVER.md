# P15-FTILT-TAKEOVER - take over P12-FTILT-FACTS and finish it (Mii Brawler's forward tilt, measured)

For a capable worker (GPT 6 Luna, Space Bunny Alpha, or a premium model). Offline analysis
of extracted game files; nothing is executed, patched or installed. Follow workspace
AGENTS.md, mods/mii_customizer/AGENTS.md and STATUS.md. No agents, commits, emulator, SD
access. Paths are relative to mods/mii_customizer/ unless marked workspace-relative; create
every folder INSIDE mods/mii_customizer/. Use `python`; write scripts with the file tool (no
heredocs). End with task ID, DONE/PARTIAL/BLOCKED, changed files, checks run, open questions.

You are taking over a task whose first worker ran for about three hours, produced data and
scripts, and never wrote the report or the check script. The original prompt is
prompts/P12-FTILT-FACTS.md: READ IT FIRST, its questions Q1..Q6 and its rules still apply
(why this matters: the mod is about to let a saved Mii Gunner perform Mii Brawler's forward
tilt, and the design needs measured facts, not recalled ones; see also the coordinator
banner at the top of research/P11-MOVE-PLAN.md). If the first worker is still running when
you start, the user stops it; do not coordinate with it.

What the first worker left (all unreviewed; nobody has checked any of it):
- research/P12-FTILT-FACTS.md: a skeleton, every answer "(to be filled)".
- evidence/P12-FTILT-FACTS/: does not exist.
- scratch/2026-10-07_P12-FTILT-FACTS/: its scripts - parse_motions.py, anim_info.py,
  mesh_anim_compare.py (Q1, Q5); explore_nro.py, unwrap_impls.py, decode_acmd.py,
  dump_calls.py, all_calls.txt, list_hash_args.py (Q2, Q3); scan_status.py,
  probe_status_bl.py, probe_status_imm.py, probe_switch_context.py, probe_switch_use.py,
  probe_main_motion_hash.py, probe_nro_motion_import.py (Q4, where it seems to have got
  stuck); verify_tail_and_paths.py, extract_index.txt.
- workspace gamedata/mii_customizer/P12-FTILT-FACTS/: extracted inputs (fighter/, effect/,
  sound/), scripts/*.asm.txt (disassembly of the Brawler game / effect / sound / expression
  scripts for attack_s3, attack_s3_hi, attack_s3_lw and the Gunner's four attack_s3
  scripts), tables/: motion_ftilt_entries.tsv, anim_ftilt_clips.json,
  anim_track_inventory.json, mesh_objects.tsv, registrations.tsv, acmd_calls.json,
  status_regs.tsv.

HOW TO WORK - this order, and the report is written after EVERY step, not at the end:
1. In your first ten minutes: replace the skeleton with a real report head and a "Short
   answers" section that states, per question, what the left-over tables say, each marked
   "unverified, from the previous worker's table <file>". An honest partial report must
   exist from then on, whatever happens later.
2. Work in your own scratch folder scratch/2026-10-07_P15-FTILT-TAKEOVER/ (copy the scripts
   you reuse; do not edit the previous worker's folder). Hash every input file first.
3. Go question by question, Q1, Q5, Q2, Q3, Q4, Q6. For each: rerun or rewrite the script,
   compare with the left-over table, say which is right where they differ, write the answer
   into the report with addresses and file hashes, and mark it verified. Then the next.
   - Q2/Q3: the previous decoder (decode_acmd.py -> tables/acmd_calls.json) is the
     riskiest piece. Validate it before trusting it: decode one script whose values are
     independently known from this project's own evidence or from the motion list (for
     example frame numbers that must match the cancel frame / animation length of Q1, bone
     hashes that must exist in the skeleton), and state exactly which argument kinds you
     can and cannot decode. An argument you cannot decode is reported as "not decoded",
     never filled in.
   - Q4 (does either class register its own status functions for the forward tilt): time-box
     it to about 40 minutes. If it is not settled by then, write what the scan shows, how it
     was validated on a status that IS overridden (a special), and what remains open, and
     move on. A clear "open" is acceptable; hours of probing without a written result is not.
4. evidence/P12-FTILT-FACTS/check_p12_ftilt_facts.py as the original prompt specifies
   (input hashes, cited instruction words, the decoded tables, the dependency table; at
   least four negative controls behind `--neg`; exit 1 on mismatch). Write a first version
   as soon as Q1 is verified and extend it per question. Run it after your last report edit
   and paste both outputs into the report.
5. Final section: task ID P15-FTILT-TAKEOVER (finishing P12-FTILT-FACTS), status, changed
   files, checks run with exit codes, open questions, and one paragraph "what the previous
   worker's tables got wrong", even if the answer is "nothing found".

Tools you may need: workspace tools/REGISTRY.md (extraction), tools/gunner-catalog and the
P1-DATASET scripts (motion lists), workspace gamedata/mii_customizer/P11-MOVE-PLAN/ (earlier
extraction, read-only). Disassembly of the main image, from the workspace root:
`PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python python
mods/mii_customizer/scratch/2026-10-04_P1-ID-REVIEW/d.py win <addr> <n>` (the script is under
mods/mii_customizer/; only the PYTHONPATH points into the other mod). The lua2cpp NROs are
separate files; the previous worker's explore_nro.py shows how it loaded them. If you read
anything else inside mods/ssbu_mod_new/, read its AGENTS.md first; never edit it.
research/P12-SCRIPT-ROUTE.md (finished, reviewed) section Q6 already locates how
lua2cpp_miigunner.nro registers its scripts (`sv_set_function_hash`, `game_attacks3` at
0x47e34 with body 0xbc500): use it as a cross-check for your Q2 registration sites.

Rules: every number in the report comes from a file you hashed; tier B only for what the
check script re-reads; anything about what happens in the game is D; no design and no
recommendation; do not fill gaps from memory or the internet.

Exclusive writes: research/P12-FTILT-FACTS.md, evidence/P12-FTILT-FACTS/,
scratch/2026-10-07_P15-FTILT-TAKEOVER/, workspace gamedata/mii_customizer/P12-FTILT-FACTS/
(you may add files and regenerate tables there; keep the previous tables under a subfolder
`leftover/` so differences stay visible).
