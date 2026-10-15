# P2-MATCH-READER - premium: how a saved Mii's special bytes and ID reach the match

For Claude Opus 5.5 or GPT 6.1 Sol. One bounded native trace. Follow workspace
AGENTS.md, this mod's AGENTS.md and STATUS.md. No agents, commits, branches,
emulator, SD access, framework changes or edits to other workers' files. Inputs are
read-only. B is offline observation, D hypothesis; nothing here is runtime evidence.
Coordinator owns STATUS/CURRENT_INSTALL/CHANGELOG. All paths are relative to
mods/mii_customizer/ unless marked workspace-relative; create evidence and scratch
folders inside mods/mii_customizer/. Save the report and end with task ID,
DONE/PARTIAL/BLOCKED, changed files and the next experiment.

Input: workspace-relative gamedata/ssbu-13.0.4/main.bin, sha256
f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613. Flat image,
address == file offset. Relocation records: bare 24-byte array at file
0x39c8070..0x40c9fc7. Disassembler: copy scratch/2026-10-04_P2-SKILL-STORE/d.py,
rel.py and chain.py into your own scratch folder; capstone via
PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python (workspace-relative).
Use `python`.

Read first: research/P2-SKILL-STORE.md (whole), research/P1-ID-REVIEW.md section 3.

Established (B, offline):
1. A saved fighter is a 0x1B0 record: u32 ID at +0x000, the four special choices as
   bytes at +0x142..+0x145 (values 0..2; the editor commit 0x180d200 refuses to
   store anything above 2), tag-0xc1 key at +0x1a0. Loader 0x17c8210(mgr, id, out).
2. 0x17914d0(ctx, player, sel) reads the saved ID from sel+0x14, loads the record
   and passes a local struct to 0x179e440, which stores into a per-player entry
   G+0x3670 + player*0x1c8 (G = 0x53040f0). Record bytes +0x140..+0x198 are among
   what is copied. Its only caller 0x1791390 handles players 0 and 1 from selection
   structs G+0x1890 and G+0x18a8.
3. The loader 0x17c8210 has 139 `bl` callers, 117 of them inside the editor range.

Question, in order. Stop at the first part you cannot close and report PARTIAL.
A. In 0x17914d0 / 0x179e440, at which offset inside the per-player entry do record
   bytes +0x142..+0x145 land? Give the copy instructions.
B. Who reads that entry offset? Enumerate readers with base-register provenance
   from G+0x3670 (or from a pointer proven to hold it). For each reader: function
   start, what it does with the four bytes (stores them where), and its callers'
   count. Follow the bytes forward at most three hops, aiming for the point where
   they are handed to fighter creation for a match (D if you name it; give the
   evidence that makes you think so, e.g. a fighter-kind key or entry id written
   beside them).
C. Independently of B: list the non-editor callers of 0x17c8210 (the 22 outside
   0x19d0950..0x19dc304), each with its enclosing function and where its ID
   argument comes from, one line each. Mark any whose ID comes from a per-player
   or per-entry structure rather than from G's two selection structs.
D. From A-C, answer plainly: at the last point you reached, is the saved-fighter
   u32 ID still available next to the special bytes (same struct, or a struct
   reachable from the same base), or has only record content been carried forward?
   State the struct, offset and the instruction that shows it, or say it is absent.

Method constraints. Provenance-bound only: a read counts if its base register is
derived inside the dumped window from G, from an argument you traced, or from a
proven pointer slot. No bare-displacement scans across the binary. Separate what
instructions show (B) from meaning (D). Do not design hooks, persistence or UI.
Do not analyse the fighter-kind system beyond noting where a kind key sits.

Why this matters: the mod needs, at match start, one value per player that
identifies which saved Mii is being used, so it can look up that Mii's custom
loadout. The answer decides between hooking a reader found here and needing a
console log run to find it.

Deliver research/P2-MATCH-READER.md: short answers to A-D, one table of
(address, instruction, meaning, tier), a claim-check script, and the single
smallest remaining unknown. If the chain cannot be closed offline, say exactly
which two or three addresses a log-only console diagnostic should watch and what
each logged value would decide.

Exclusive writes: research/P2-MATCH-READER.md, evidence/P2-MATCH-READER/,
scratch/2026-10-04_P2-MATCH-READER/.
