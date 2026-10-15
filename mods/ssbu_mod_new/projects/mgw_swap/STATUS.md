# mgw_swap - Mythra <-> Game & Watch hook swap (FROZEN)

Source: `src/mgw_swap` (Rust plugin, `deploy.py`, `tools/`). History: `history/DIAGNOSIS.md` (65 KB, contains several refuted theories - read `handbook/graveyard.md` R-4, R-13..R-15 first), `history/HANDOFF.md` (Monkey Flip).
Scripts in this tree still use the old layout for output (`mod_output`); they need a path shim before use here (export paths were already repointed to `dumps/arc`).

| Item | State |
| --- | --- |
| Swap both directions (pair table `[28,91,-1]`, 11 hooks) | works; return displacement + G&W camera were the "scuffed down-B" |
| G&W fair = Shulk fair (injected `SwordR`) | works |
| Mythra uair (Corrin), dthrow (Luigi) | work |
| Mythra up-B = Hero's Spin `Hi3` | plays ground+air; late-hit tuning not reconfirmed |
| G&W side-B = Monkey Flip: animation | works |
| Monkey Flip kick | fix built, untested |
| Monkey Flip grab | never worked; see `handbook/15_grabs_catch.md` for eliminated causes and next experiment |
| Snake grenade | crashes (stack overflow), gated off |
| c06 support | built, offline-validated |
Why frozen: 2026-09-29 the user chose the reskin route (`projects/pgwr`). Reusable: Monkey Flip/Hi3/fair tooling, hook offsets (`handbook/12`, `13`).
