# Collective 0.20.22 — installed 2026-10-03

User request: "now install the new changes including the up b gravity one".

Included: Hero level-2 side-B visual rotation correction; real battle mana gauge for the modded eflame/elight c06/c07 pair; Hero's Spin aerial gravity scales 0.70/0.70 (previous 0.85/0.90). Dashgrab has no completed handoff and is excluded. All previous move registrations, DK cargo/Incineroar, Chrom jab sword, Lucas/Ness themes and loading assets retained.

Package `builds/pgwr/0.20.22/`, isolated source `builds/.cache/collective-0.20.22/plugin/`; plugin/banner/info 0.20.22. NRO `3ab31bd34dceda31659f337867fdf67330afa691c50d565b514cd66124dd6772` (585728 bytes). Mod tree `3a64be3b167ac7ff864399056e0e7ce74a7b011e5a6315a5f1ba408583f74cfa` (5099 files). Backup `evidence/sd-backups/sd-backup-20261003-122846`.

Verified offline (B): original card matched ready-assets.1 exactly; isolated source union adds only Cargo version/lock and hero_spin_params.rs to the checked Hero source. Only two executable constants differ in that params file. Release build finished; existing DK Vector3 FFI warnings remain. Native 25 spans/nine slots match; HUD audit 161 checks with negative NRO control; angle constants present only in angle candidate; gravity audit against the actual source snapshot passed both negative controls. Built/package/card NRO equality and all 5099 package/card file hashes verified. All five other plugin hashes and Skyline files unchanged. All prior asset paths/hashes unchanged except info.toml version. hero-mana-reserved and logging features OFF; hero-mana-hud ON. No new status IDs. No game/emulator run or commit.

Runtime remains unverified (D), including gauge drawing/lifecycle/mapping and whether the slower descent improves retention. User explicitly requested collective installation; diagnostic Hero controls remain available in `builds/pgwr/zapple-mana-hud-0.1.1/controls/` and carry the older gravity. They are not installed. For a regression, isolate changes rather than interpreting a combined result as cause.

Build first encountered the existing Skyline target-json PermissionDenied; approved tool execution allowed the build. Snapshot gravity audit wrapper initially used a relative path against an absolute root (ValueError); corrected to resolved paths, then passed. Installer launch initially lacked Git coreutils in Bash PATH; explicit Git usr/bin/mingw64/bin fixed it before any SD write. No failed card mutation preceded this install.

## Console test (9 steps)

1. Fresh boot, modded c06 and c07. Require BOOT v0.20.22 and `[PGWR-MANA] HUD READY route=game-part-selector spans=25 slots=9`. READY alone does not prove drawing.
2. Start once as Mythra and once as G&W. Mana gauge should be visible on that player's damage panel, initially 100.
3. Spend mana with Hero neutral-B and side-B, idle to refill, drain below the price and retry. Gauge should track SPEND/RECOVER/REFUSE and shortage. Charging should not refill.
4. Swap ten times; gauge stays on both bodies and mana remains shared. Lose a stock: RESET to 100. End/rematch and return through CSS: no stale gauge.
5. Level-2 side-B on c06/c07: ground/air and both facings. Judge the bolt angle. Level 1/3, damage and launch should retain prior behavior.
6. Aerial up-B over an opponent: ten attempts each at low/high percent, against a small/large fighter, both facings/costumes. Count dropouts and confirm finisher. Ground up-B should retain prior behavior.
7. Land or take a hit during aerial spin: no stuck hitboxes/hover; normal falling after the move. G&W up-B should retain prior behavior.
8. Vanilla Pyra/Mythra c00/c05, real Hero and Kirby-copy-Hero controls. Then two modded pairs/teams and 5–8 players if available: each gauge must belong to its player. Spot-check DK cargo, Incineroar, jab sword, themed effects and loading portraits.
9. Return logs from boot: `sd:/ultimate/pgwr_mana_log.txt` and `sd:/ultimate/pgwr_log.txt`; newest `sd:/atmosphere/crash_reports/` on crash. `HUD REFUSED`, `HUD SELECT-FAILED`, or `HUD OFF` fail the HUD test. BIND/REBIND should map the correct player; SPEND/RECOVER/RESET establish meter events, not visible rendering.

Evidence: PRE_INSTALL.json, POST_INSTALL.json, SOURCE_DELTA.json, build.txt, native_audit.json, hud_audit.json, angle_audit.json, gravity_audit.txt and installer-output.txt in this directory.
