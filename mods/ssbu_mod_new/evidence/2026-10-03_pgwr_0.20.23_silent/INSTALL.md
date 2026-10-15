# Silent performance 0.20.23 — installed 2026-10-03

User requested: "while i wait, install the rurrent logless version for now".

Installed exactly the previously checked `builds/pgwr/0.20.23/` package, with no rebuild or pending live-source inclusion. Mana side-B spending/attack-recovery corrections are excluded; they remain a separate worker task. The reported level-1/level-2 mana issue is not fixed by this logging-only release.

NRO `424914c18e740aea67c37ed399ffe5a22208b76f10dec81e279a8285198b777e` (524288 bytes). Tree `4a1f08ec99f7e079cf41bd0dddd7f4f9a5f57239fa8a590377f6fcbd4568c242` (5099 files). Automatic backup `evidence/sd-backups/sd-backup-20261003-125341`.

Verified B: card initially matched 0.20.22; isolated source, package and built NRO still matched their manifest hashes before installation. Installer ran with frameworks OFF, automatic backup/staging/cmp/diff/rollback. Afterward 5099/5099 card file hashes and plugin hash matched 0.20.23; all five other plugin hashes and Skyline files unchanged. The release disables all 224 mod diagnostic call sites and argument evaluation (logging OFF). Earlier binary checks found no six mod log-file paths and retained all 25 HUD safety signatures. HUD ON, reserved recovery OFF. All earlier gameplay/assets retained except info version. No game/emulator run or commit.

Runtime performance and gameplay remain unverified. Test the same setup/stage as before to assess frame pacing. No mod diagnostic pass/fail or boot markers are emitted; identify by package hash. Existing old logs are retained and are not fresh evidence.

## Console checks

1. Play the same c06/c07 match/stage as before and compare responsiveness/frame pacing.
2. Confirm mana HUD display/swapping, Zapple visual angle and reduced up-B gravity/finisher/normal falling afterward. Side-B level-1/2 spending and attack-based recovery remain known pending issues.
3. Spot-check DK cargo/Incineroar, jab sword/themes/loading art and vanilla Pyra/Mythra c00/c05. Report any crash with newest `sd:/atmosphere/crash_reports/` file; no new mod boot log is expected.

Evidence: PRE_INSTALL.json, POST_INSTALL.json, installer-output.txt; earlier BUILD.md/source change list/build.txt; MANIFEST.json in package. Created files are listed in CREATED_FILES.json.
