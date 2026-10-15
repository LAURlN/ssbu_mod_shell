# P10-UI-SLICE - plugin 0.4.0: character list on the native headgear screen, runtime saving

Task: **P10-UI-SLICE** (Claude Opus 5.5). Status: **PARTIAL - the worker stopped on
2026-10-05 18:04 without a report.** This page is written by the coordinator (2026-10-06)
from the files the worker left. Paths are relative to `mods/mii_customizer/`.

## What the worker left

- Source, complete as far as the coordinator can read it: `plugin/src/ui.rs` (pure part:
  sites, probes, synthetic handles, mode state), `plugin/src/editor.rs` (the five hooks),
  `plugin/src/list.rs` (contract F), changes in `lib.rs` (list load, `install_ui`, `ui_off`,
  save called from the editor) and `loadout.rs` (B+, `Store::set_preset`, generation).
- `builds/0.4.0-ui/libmii_customizer.nro`, 81920 bytes, sha256
  `d28aea75f04f56665f11d46529abe940e527db433c169defbbaff6076117d74a`.
- 23 disassembly windows in `evidence/P10-UI-SLICE/`, helper scripts in
  `scratch/2026-10-05_P10-UI-SLICE/`.
- **Missing:** the report, `MANIFEST.json`, host tests for the new code (the sources name
  `scratch/2026-10-05_P10-UI-SLICE/host_test.rs`, which does not exist), the mutation
  control, the check script `evidence/P10-UI-SLICE/check_p10_ui_slice.py`, the test plan.

## Design as read from the source (D for all runtime behaviour)

Five function-entry hooks, installed all or none after 5 site and 15 probe word compares,
and not at all when `sd:/ultimate/mii_customizer/ui_off` exists:

| site | role |
|---|---|
| `0x180a030` dispatcher | exit value 7 -> rewritten to 1 and armed (entry A); value 1 with ZL or ZR held on any npad or handheld -> armed (entry B). A pending arm is dropped by the next non-arming call |
| `0x180abd0` headgear state | first tick: original runs, then the list is swapped in (own buffer from the game allocator, count through the scroller's setter `0x37830e0`, `SCROLLER_ITEM_NUM` re-registered, cursor through `0x19cfe00`); every later tick: `S+0x168` cleared before the original so the preview write `0x180ac3c` never fires; tick with `S+0xe8 == 0`: native vector, count and the three handle slots restored BEFORE the original runs, then the decision is applied |
| `0x328b5d0` | answers 0 ("listed") for synthetic handles |
| `0x3288330` | writes the row's message key (`nam_mii_hat_none_m` for row 0, the list label otherwise) |
| `0x19cd100` sort | forced to mode 3, which the game ignores |

Synthetic handles: tag `0x5a`, hash `0xfe4d43rrrr` (row in the low 16 bits). The copy placed
in the current slots carries hint bit 40, so "decided" (the game copies the list entry, hint
0, into `S+0x148`) is told from "cancelled" even on the same row. On exit the working record
(0x200 bytes from `0x5306b78`) is compared with a snapshot and the headgear handle is written
back if it differs; both values are logged (`mc|UI|exit|...|equal=`).

## Coordinator review, 2026-10-06

Observed:
- `build-plugin.sh` exit 0, 0 warnings; the NRO hash is reproduced from the sources on disk.
- `scratch/2026-10-05_coordinator/check_ui_sites.py` (workspace root): 52 checks, 0 failed -
  all 20 word records equal the 13.0.4 image and are in the NRO; the three vtable constants
  are relocated vtables; both row-0 labels exist in `msg_name.msbt`.
- The 0.3.0 host tests run against the 0.4.0 sources: 47 passed, 0 failed.
- Re-read in the image by the coordinator: the label call (`0x19ccbe0 add x0,sp,#0x18` - the
  out struct is `x0`, text at +8), the decide store (`0x19cc698..0x19cc6c4`, only for a
  non-negative `get_decided_id`), the state-5 compare (`0x180acc8..0x180ad20`,
  `0x180ae08..0x180ae20`), the `0x328b5d0` tail (1 = not in the table), the setter
  `0x37830e0` (`x0` = address of the scroller pointer, `w1` = count).
- E3 argument as the coordinator follows it: writer 1 needs `S+0x168`, cleared every tick;
  writer 2 runs only on the `S+0xe8 == 0` tick, by which time `S+0x148` again holds the
  headgear the Mii had; the save path `0x17c0a50` writes nothing for a hash that is in no
  table (P10-HAT-OPEN Q3); and the exit check restores the handle if it ever differs.

Not verified (all D): everything at runtime. In particular the scroller accepting a new
count while its script runs, `SCROLLER_ITEM_NUM` re-registration, the hid read, whether
`S+0xe8 == 0` is seen exactly once, the first `save_loadouts()` on the console, and the
behaviour of the 87-row list when it is longer or shorter than the hat list. No host test
covers `list.rs`, `ui.rs`, `Store::set_preset` or `loadout::load`.

Decision: package it for a console boot as it is (the boot answers what no offline check
can), and give the premium worker one follow-up after the boot that combines the missing
tests and report with whatever the boot shows.
