# P3-CUSTOMIZE-SITES - locate where the engine applies a fighter's special-move choice

Follow workspace AGENTS.md, kb/INDEX.md, this mod's AGENTS.md and STATUS.md.
Read research/COORDINATOR-2026-10-04.md. Work only on the task below. No agents,
commits, branches, emulator, SD access, framework changes or edits to other workers'
files. Inputs remain read-only. Report exact inputs/hashes, commands, observed
checks, failures and limits. B is offline observation, C pinned source, D
hypothesis; no runtime behavior claims. Coordinator owns
STATUS/CURRENT_INSTALL/CHANGELOG/contracts. Finish saved report and chat with task
ID, DONE/PARTIAL/BLOCKED, changed files and next experiment. All paths below are
relative to mods/mii_customizer/ unless marked workspace-relative. Create your
evidence and scratch folders INSIDE mods/mii_customizer/, and make your scripts
write their output files there too, never into the current directory.

Background (B unless marked). A saved Mii stores four special-move choices as bytes
0..2. The exported script wrapper `WorkModule__set_customize_no_impl` at 0x208de60
is `ldr x0,[x0,#0x50]; ldr x8,[x0]; ldr x3,[x8,#0x278]; br x3`: it calls slot
+0x278 of the vtable of the object at [accessor+0x50]. For vtable 0x4f89490 (the
object stored at [parent+0x50], research/P2-STAT-HOOKPOINT.md section 2.6) slot
+0x278 is 0x4e53f0: `ldr x0,[x0,#0x38]; ldr x8,[x0]; ldr x3,[x8,#0x38]; br x3`.
The pinned binding declares it as set_customize_no(module, variant: i32,
move_no: i32) (C, research/P2-STAT-API.md section 3). D: this is how the engine
tells a fighter which special variant each slot uses.

One goal: list the code sites that make this call, and for each one show where its
two integer arguments come from. Locating task. Do not interpret beyond that.

Input: workspace-relative gamedata/ssbu-13.0.4/main.bin, sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613 (rehash first; stop
BLOCKED on mismatch). Flat image, address == file offset; code 0x100..0x39C8000.
Copy d.py and relocs.py from scratch/2026-10-04_P2-STAT-HOOKPOINT/ into your own
scratch folder; do not edit the originals. capstone:
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python (workspace-relative).
Use `python`, not `python3`.

Steps.
1. Re-read and record the eight instructions at 0x208de60 and 0x4e53f0 so the
   background above is verified by you, not assumed.
2. Direct users of the wrapper: `bl`/`b` to 0x208de60, and 8-byte pointers to it
   in the image (and relocation addends equal to it). Report counts and addresses.
3. Indirect call sites: scan the code range for the shape
   `ldr xN,[xM,#0x278]` followed within 8 instructions by `blr xN` (or `br xN`),
   where xM was loaded by `ldr xM,[xK]` (a vtable load) within the 6 instructions
   before. Report the total count. Then keep only sites where, within the 12
   instructions before, xK itself was loaded with displacement #0x50
   (`ldr xK,[xJ,#0x50]`). Report that count and list every such site. Validate the
   scanner on synthetic instruction sequences first (one that must match, one where
   the register is overwritten in between, one with a different displacement) and
   on the known wrapper at 0x208de60, which must be found by the unfiltered shape.
4. For each kept site (if more than 30, take the first 30 by address and say how
   many were left): a window of 24 instructions before and 8 after; the
   instructions that define w1 and w2 at the call, each followed back inside that
   window until you reach an immediate, a load (give base register, displacement
   and where the base was defined in the window), an argument register of the
   enclosing function, or the window edge ("provenance leaves the window"). Note
   whether the site sits inside a loop that counts 0..3 or 0..4 (give the compare
   instruction) and whether a `cmp #2` / `cmp #3` bound on the value is visible.
5. For each distinct enclosing function start candidate (nearest prologue above the
   site; use the downward-sp test from research/P2-UI-CONSTS.md, not the old
   fstart masks), list direct `bl` callers: count and first 10.
6. One summary table: site, enclosing function, w1 provenance, w2 provenance,
   loop/bound notes, caller count.

Rules. Every claim needs instruction addresses. Do not name functions or
structures ("this is fighter init"). Do not connect anything to Mii, to saved
records or to the tables in research/P2-MATCH-READER.md, even if an offset looks
familiar; list displacements and let the reader compare. Zero kept sites is a valid
result: report the unfiltered count, show five example unfiltered sites as raw
windows, and stop.

Deliver research/P3-CUSTOMIZE-SITES.md plus a check script that re-derives every
listed site and count from the image and exits nonzero on mismatch. If the check
takes minutes, say how long. Raw windows go in evidence.

Exclusive writes (all under mods/mii_customizer/): research/P3-CUSTOMIZE-SITES.md,
evidence/P3-CUSTOMIZE-SITES/, scratch/2026-10-04_P3-CUSTOMIZE-SITES/.
