# P4-STAT-SITES - for every stat candidate, how the executable asks for it

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

Background. The console test (evidence/2026-10-04_gate1/RESULT.md, tier A) showed
that `weight` and `walk_speed_max` are requested per fighter through the function
at 0x4e53e0 (vtable slot +0x270, float getter), with the parameter hash in x1 and
x2 = 0. research/P2-STAT-READS.md listed the code sites for those two hashes. The
mod wants a list of editable stats; the catalogue has 12 candidates. For each one
we need to know whether it is requested the same way.

One goal: repeat the P2-STAT-READS site survey for all stat candidates and classify
each code site by the vtable slot it calls. Locating task; no interpretation of
what a stat does and no ranges.

Read: research/P2-STAT-READS.md (method, scanner validation, limits),
research/P1-DATASET.md and evidence/P1-DATASET/gunner_catalog.json (the 12 stat
candidates with their hashes and types), research/P2-STAT-HOOKPOINT.md section 2.6
(the thunk block 0x4e5390..0x4e53fc: slot +0x250 -> integer-style getter thunk
0x4e53a0, +0x260 -> 0x4e53c0, +0x270 -> 0x4e53e0).

Input: workspace-relative gamedata/ssbu-13.0.4/main.bin, sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613 (rehash first; stop
BLOCKED on mismatch). Copy stat_reads.py, report.py and d.py from
scratch/2026-10-04_P2-STAT-READS/ into your own scratch folder and extend the
copies; do not edit the originals. capstone:
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python (workspace-relative).

Steps.
1. Take the stat candidates from the catalogue JSON exactly as recorded (name,
   Hash40, type). State how many there are; do not add or drop any. Include
   weight and walk_speed_max as controls: your counts for them must equal
   P2-STAT-READS (37 and 18 code sites); if not, stop and explain.
2. For each hash: code-site count (same movz/movk scanner and gap rule), data-site
   count (8-byte little-endian, aligned), as in P2-STAT-READS.
3. Classify every code site by what follows it: an indirect call whose target was
   loaded with `ldr xN,[xM,#D]` - report D (expected values include 0x250, 0x260,
   0x270; report whatever is there); a direct `bl` (report target); or no call
   within the same span P2-STAT-READS used. For indirect sites also report whether
   xM came from `ldr xM,[x0]` with x0 loaded by displacement #0x50 within the 12
   instructions before (yes/no), and the value moved into x2 before the call if it
   is an immediate.
4. One table per stat: counts per class and per displacement. One overall table:
   stat, type in the catalogue, sites total, sites via +0x270, via +0x250, via
   other displacement, direct `bl`, none.
5. For any stat with zero code sites: say so, and report whether its hash occurs
   as data and where. Do not speculate how it is read.

Rules. Every listed site needs its address; full per-site lists go in evidence as
JSON, the report holds the tables and at most 5 example windows. Do not name what
a function does. Do not rank stats or recommend which to make editable.

Deliver research/P4-STAT-SITES.md plus a check script that re-derives all counts
from the image and exits nonzero on mismatch (say how long it runs).

Exclusive writes: research/P4-STAT-SITES.md, evidence/P4-STAT-SITES/,
scratch/2026-10-04_P4-STAT-SITES/.
