# Session 4, boot 1 - 2026-10-07 - 0.8.0 crashed at startup (tier A)

Installed: plugin 0.8.0 `cdb4f7e03b2aa1b0220bc871e6321b2d4405b5d987af3f27c3e1651293963a17` (258048 bytes), `menu.txt` `6e437998...`,
`ultimate/mods/mii_customizer_moves/` (5 files), the rest as in `CURRENT_INSTALL.md`.

User report: "now it crashes on startup". Two attempts, two crash reports, identical apart
from addresses (copied here unchanged): `01791399134_01006a800016e000.log`,
`01791399154_01006a800016e000.log` (20:52:16 and 20:52:36). No `mii_customizer_log.txt` was
written: the plugin died before its first log line.

What the report says: Data Abort, result 0x4A8. PC = Skyline `getRegionAddress + 0x4`, LR =
`mii_customizer + 0xb71c` (`main + 0x3c`). Stack region `426c191000-426c1a1000` (64 KiB),
FP `426c1a0fb0`, **SP `426c151860`: 0x3f7a0 bytes below the bottom of the stack**. So `main`
had reserved about 0x4f750 bytes and the first store of its first callee hit unmapped memory.

Cause (B, `tools/stack-frames/stack_frames.py`, which reads `sub sp, sp, #imm` out of an NRO):

| NRO | largest frame | file offset | ran? |
|---|---|---|---|
| 0.6.0 `f44fc278...` | 19584 | 0x84d4 | works (tier A) |
| 0.7.0 `b9751751...` | 283552 | 0x9c54 | never installed; would have crashed the same way |
| 0.8.0 `cdb4f7e0...` | 324496 | 0xb6f4 (`main` is at 0xb6e0) | this crash |
| 0.8.0 fixed `8198bd49...` | 18672 | 0xb4f8 | not yet run |

`menu::Menu` grew to 123272 bytes with 0.7.0's option pages (48 entries x 32 inline options)
and `loadout::Table` to 76808 bytes with option and slot lines (sizes from
`scratch/2026-10-07_coordinator/sizes.rs`); both were returned by value by their parsers and
copied in `main` (everything is inlined into it). Not a fault of the move, the new mod
folder or Smashline: the game never got that far, so those are still untested.

Fix: `Menu::boxed()` / `Table::boxed()` allocate on the heap and initialise in place; the
parsers, `load_with_validator` and `Store::snapshot*` return the box; `editor::set_menu`
copies heap to static. Host tests adapted to the boxed types (comparisons and `&*m` only):
47/0, 35/0, 4/0, 16/0, 6/0. Sources as they were before the fix:
`builds/.cache/src_0.8.0_before_stackfix/`.

Lesson for reviews: host tests and source reading cannot see this; every plugin build gets
the stack-frame check before READY.
