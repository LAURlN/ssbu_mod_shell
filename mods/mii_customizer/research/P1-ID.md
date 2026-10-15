# P1-ID - saved Mii Fighter identity candidates (corrected)

Status: **FINISHED PARTIAL**. Coordinator corrected this report on 2026-10-04 after
`research/P1-ID-REVIEW.md`. That audit is the canonical source for native addresses,
instruction windows and field layouts; consult it before implementing anything.

## Inputs and retained evidence

Main: workspace-relative `gamedata/ssbu-13.0.4/main.bin`, 86,672,752 bytes, SHA256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`.
Original extracted inputs: workspace-relative `gamedata/mii_customizer/P1-ID/`;
hashes in `evidence/P1-ID/extracted_inputs_sha256.txt`. Original scratch scripts remain
in `scratch/2026-10-04_P1-ID/` as historical investigation artifacts.

**Superseded:** `evidence/P1-ID/post_fighter_trace.txt` mixes disassembly with incorrect
annotations. Preserve it as historical evidence, but use
`evidence/P1-ID-REVIEW/instruction_windows.txt` and `relocs_callers_scans.txt` instead.
Its battle-handoff, move-list, FNV and division interpretations are rejected.

## Accepted candidate and limits

The premium worker's offline inspection (B, not runtime evidence) identifies:

- A u32 saved-fighter ID at record +0x000, an ID-to-index map, and record stride 0x1B0.
  Loader 0x17c8210 rejects ID 0 and requires record validity byte +0x1a9 == 0.
- The editor ID vector at scene +0x178 begins with a zero sentinel; the post_fighter
  handler uses ids[k] with k >= 1 and k < size, without subtracting one.
- A new per-player association: selection at G+0x1890+p*0x18 holds ID at +0x14;
  0x17914d0 loads that record and setter 0x179e440 copies record contents into
  G+0x3670+p*0x1c8, G=0x53040f0. Observed caller supplies p=0 and p=1.
  The function supports indices <8, but other players' writers were not enumerated.
- The ID stays in the selection struct; this path does not copy it into the per-player
  table. The match-setup reader remains untraced. G's purpose is unverified (D).

Name/appearance and class/work IDs are not substitutes for a saved-fighter identity.
Pinned skyline-smash constants from the original report remain reference material
only; their role in the new propagation route has not been verified.
Save-file naming claims were not re-audited. Stability under rename, copy,
delete/recreate and reboot remains unverified (D). Two players may select the same
saved record, so player identity and saved-record identity must be kept distinct.

## Corrections to the original investigation

1. post_fighter is not an established battle handoff. Its context contains content
   type, ID and name; post/share is the worker's interpretation (D). Do not pursue
   context +0x5d4 as an accepted match input.
2. Context +0x1c8/+0x1cc/+0x1d0 contain name hash, length and UTF-16 name text;
   there is no demonstrated merged list of move IDs.
3. Name hashing is h=(h*0x89)^u16, seed 0x811C9DC5, 32-bit, until zero.
   It is not FNV-1a, CRC32 or Hash40. Hash use at save-path sites is unverified.
4. Registration creates a 0x28-byte delegate with scene, member-function address
   and adjustment; it does not store the handler as a vtable slot. See the audit.
5. The multiplication constants implement exact division: inverse of 27 modulo
   2^64 after ASR #4 yields division by 0x1B0; inverse of 6413 after ASR #6 yields
   division by 0x64340. The old exact 14/27 assertion and count >189 are false.
   is_max_num compares an element count with 98; capacity was not researched.
6. Tagged-key availability checks were mislabeled as colour copying. Special-choice
   field meanings remain unverified; +0x140/+0x144 are candidates only (D).

## Verification and next step

Coordinator verified both modular inverse products equal 1 modulo 2^64 and the
strides 16*27=0x1B0, 64*6413=0x64340 using Python (B). Coordinator reviewed but did
not independently reproduce the native disassembly. No console or emulator run.

Next missing link: the match-setup reader of the selection struct/per-player table.
A provenance-bound caller trace or a reviewed log-only diagnostic could resolve it.
No behavioral hook, persistence schema or test package is accepted from this report.
