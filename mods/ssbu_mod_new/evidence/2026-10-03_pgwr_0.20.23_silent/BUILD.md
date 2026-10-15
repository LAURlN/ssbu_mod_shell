# Silent performance 0.20.23 — checked package, NOT installed

Request: remove all logging so the game runs smoothly. No performance claim is established offline.

Package `builds/pgwr/0.20.23/`; NRO `424914c18e740aea67c37ed399ffe5a22208b76f10dec81e279a8285198b777e` (524288 bytes), tree `4a1f08ec99f7e079cf41bd0dddd7f4f9a5f57239fa8a590377f6fcbd4568c242` (5099 files). Current recorded installed baseline 0.20.22 preserved. No Switch SD volume mounted during final checks; no installer/card writes attempted.

Changed only diagnostic call expressions, a feature-gated token-discarding macro, release version and info version. All changed Rust files inverse-match installed source after removing wrappers/macro (LF normalized), establishing gameplay code preservation. Logging feature remains OFF, hero-mana-hud ON, hero-mana-reserved OFF. Dropped argument tokens prevent formatting, diagnostic pointer reads within log expressions, SD open/write/flush and console output. Kept engine attack-log work/alloc callbacks because they are gameplay bookkeeping, not file/console diagnostics. External/framework logging not altered; framework plugins are protected.

Verified B: 224 expressions across 38 snapshot files gated; release build finished; all six mod log paths and HUD READY diagnostic absent from binary; 25 HUD signature constants retained; packaged NRO equals built NRO; asset tree exactly preserves 0.20.22 except info.toml version. Source_changes lists shared live files receiving the same diagnostic-only edits. No test/emulator/console/commit/push.

Preparation errors: a PowerShell/Python quoting mistake in the card-check copy command produced SyntaxError, repaired before use. Card check then found zero Switch cards. Binary check initially assumed the private query-memory symbol name survives LTO and failed; replaced with direct verification of all 25 native signature constants plus inverse source preservation, then passed. No failure changed the SD card.

Install when card is mounted: use `src/pgwr/install-to-card.sh` with MGW_PACKAGE pointing to `builds/pgwr/0.20.23`, frameworks OFF. Manifest cargo_target is `silent-0.20.23/target`. Independently verify original card against 0.20.22, then candidate/package/card hashes and protected plugins. Existing installer backs up, stages, compares and rolls back.

Manual console checks:
1. Compare the same c06/c07 match and stages with 0.20.22; assess responsiveness and frame pacing. No new diagnostic markers/log entries are expected.
2. Confirm mana HUD spending/refill/swaps/stock reset, Zapple angle and aerial up-B/finisher/normal falling after the move.
3. Spot-check DK cargo, Incineroar back throw, jab sword, themed effects and loading portraits; vanilla c00/c05 controls.
4. On crash, return newest `sd:/atmosphere/crash_reports/` file and the package version/hash. No new mod boot log is expected. Existing log files remain but should not receive mod-generated entries.

Created files are listed in CREATED_FILES.json; cache files are generated build inputs/artifacts. Source change list is SOURCE_CHANGES.json; build output build.txt; manifest contains asset/source hashes. Runtime remains unverified.
