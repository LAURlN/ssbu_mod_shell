# pgwr 0.18.0 console run: Mythra c06/c07 Hero neutral-B, full-charge shot crashes

**Verdict: FAIL (tier A).** Two boots, two identical crashes at the first full-charge shot.

## What was installed
- `libpyra_gamewatch_reskin.nro` sha256 `6fa0071614783f7b04619f5f64398c0a9fa36d3f8ad0abd4705bac28eaf9df14` (0.18.0), 1362 mod files,
  tree `83fdc01a79f6a919cd055777b7d333b839c6200583ad7e65880929fd3cc9180a`. Record: `evidence/install-record-2026-09-30_034510.json`.
- Smashline `5f4091eed89c5854c2bfccb9f25b6e8da8c03ebedcaa5ab36eadebfc078bc8f7` (unchanged).

## What the user did (from the log)
Boot 1: Mythra c07, neutral-B: medium charge ended by status 0xa; full charge stored; B again -> shoot status 0x1f9, `SPAWN charge=81 frame=15`, `INIT begin`, crash.
Boot 2: Mythra c06, same sequence: full charge stored, shoot, `SPAWN`, `INIT begin`, crash. No `INIT complete` in either boot.
Log excerpt from boot: `pgwr_log_from_boot.txt` (sha256 `891aff056597f3f5f739de31e11ae6ede895e717ba55b772f8e0543beabc95b1`).

## Crash reports
- `01790734050_01006a800016e000.log` (04:07:36), sha256 `87d727c324fbcdd59955f878216eb89eda8e326d83437d9293855af099ef08c1`
- `01790734167_01006a800016e000.log` (04:09:32), sha256 `0ad523db2e3a30643665912a7994b0326163030c63044824916a1f20cf8df2cf`

Both: Data Abort, MainThread, address `0x1b4`, PC = `cross2_Release.nss + 0x33c8f18` (`ldr s0, [x21, #0x1b4]`, x21 = 0).
Stack: pgwr+0x8570 (`generate_article`) -> main+0x3d41a8/0x3d4114 -> pgwr `initialize` hook +0xa8 -> owned initializer copy pgwr+0x64c
(`controller->vtable[0x10]`, the same call the donor initializer makes at 0x85d48c) -> main+0x33a6f58 -> fireball class vtable slot +0x30 = main+0x33c8ea0.

## Reading (tier B, measured on `dumps/exefs/13.0.4/main.bin` sha256 `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`)
- `0x33c8eb8..0x33c8ec0`: `x21 = *(*(main+0x52bb3b0) + 0x1298)`, Hero's decoded `vl.prc` object; it was null in these matches (no Hero present). That it is populated only for a loaded Hero is tier D (settle: log x21 at the hook with a real Hero in the match).
  The constructor reads `map_collision_fireball{,_m,_l}` {up, down, half_width} at `+0x194/+0x1a4/+0x1b4` by spawn level (desc+0x28 = 0/1/2).
  The small and medium branches also dereference x21 (static reading; those levels were not fired in this run).
- Decoder `0x878800..0x8792ec` stores these keys at those offsets; its inline fallbacks equal the donor values (2/-2/2, 3.5/-3.5/4.5, 5/-5/5).
  Checked by `tools/gen_hero_fireball_initializer.py` v1.1.0.
- The same pattern as the G&W breath (`+0x690`, 0.12.x). The 0.18.0 audit (`refs/brave_special_n/fireball_native.json`) had listed
  "foreign-owner safety requires tracing constructor callees" as its open limitation. This crash came from that untraced path.

## Control
No vanilla or donor control was run in this session. The fault is attributed by the register state: the faulting base register is loaded
from the Hero parameter slot, not by a controlled run. The 0.18.1 hardware test must include real Hero's neutral-B as a donor control.

Follow-up build: 0.18.1 (`builds/pgwr/0.18.1/MANIFEST.json`).
