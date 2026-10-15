# evidence/ - immutable console results, crash reports, logs

New entries: `evidence/<YYYY-MM-DD>_<project>_<version>/RESULT.md` (what was installed with hashes, what the user did, log lines seen, verdict). Never rewrite; update `projects/<p>/STATUS.md` and the handbook instead.

| Folder | Content |
| --- | --- |
| `2026-10-03_pgwr_upb_gravity/` (`RESULT.md`) | Mythra c06/c07 up-B / Hero's Spin air-gravity retune 0.85/0.90 → 0.70/0.70: measured descent-per-hit-window audit, hashes, NRO negative control, 9-step console test. **Offline only, not installed, retention unverified** |
| `2026-10-03_pgwr_pikachu_airb/` (`RESULT.md`) | Pikachu's `AttackAirB` + `LandingAirB` on eflame c06/c07 1.0.0: donor pins, retarget gates (45/55 nodes, 0 parent mismatches), a **two-byte** `attack_air_b` motion delta and a **zero-byte** landing delta, bank/sequence merge, clean release build, an unmodified-snapshot control rebuild that reproduces the baseline NRO byte for byte, delta audit 128/128 with 8 negative controls caught, the note the mana agent needs, and a 10-step console test. **Offline only, READY, not installed; runtime unverified (D)** |
| `user_console_runs_2026-09-29/` | pgwr console runs 1-3 (gate confirmed), prereq, article run (0.10.0 crash and the invalid-run addendum) |
| `pgwr_crash_reports_2026-09-29/` | Atmosphere reports for the breath (0.12.0/.1) crashes |
| `mgw_standalone_crashes_p1-p6/`, `mgw_standalone_logs_p8-p11/` | decoded crash chain of the Mythra clone (see `handbook/14`) |
| `pmclone_*` | trace-recorder runs (freeze, 514, first capture, control comparison, set_frame crash), private-module loader check |
| `install-record-0.14.0.json`, `install-record-2026-09-29_2330.json` | earlier recorded card states |
| `install-record-2026-09-30_0041.json` | the 0.15.0 card: Monkey Flip passed on hardware, the fair sword fix was inert |
| `install-record-2026-09-30_0123.json` | 0.15.1: sword visibility fix - the first card where the sword hid outside the fair |
| `install-record-2026-09-30_0139.json` | 0.15.2: NRO `930eb327…`, 1233 files, blade 1.4x |
| `install-record-2026-09-30_0218.json` | the 0.16.0 card: Chrom's jab and his Falchion cloned onto eflame. Never run |
| `install-record-2026-09-30_051537.json` | the 0.20.0 card: Hero neutral-B charge levels fixed and the Chrom jab esword pose clips. Installed by the concurrent agent ~05:15:48; record written afterwards from a read-only re-verification. Superseded by 054617 |
| `install-record-2026-09-30_054617.json` | 0.20.2 first install: Chrom jab `JAB_SIZE_FACTOR` 1.0 -> 0.9 |
| `install-record-2026-09-30_055128.json` | 0.20.2 reinstalled with the Monkey Flip logging fix. Same NRO `e614f3de…` as 054617 - one shared binary carries both changes |
| `install-record-2026-09-30_061334.json` | **current** card: 0.20.3, NRO `d9ea48fa…`, 1701 files. Adds the read-only Diddy donor observer and the nearest-opponent probe. No console run yet |
| `2026-09-30_pgwr_0.20.0/` (`RESULT.md`) | **PASS**: 14 Hero shots across charge levels 1/2/3, no crash, card byte-verified. Also records the Monkey Flip logging defect found in this run |
| *(no entry)* | **0.17.0 is built and staged but has no install record because it was never installed** - the user asked on 2026-09-30 that the card be left alone. Manifest `builds/pgwr/0.17.0/MANIFEST.json`; staged NRO `307ba0d3…`, 1233 files. The row above therefore still describes the card |
| `sd-backups/sd-backup-20260930-021808/` | the 0.15.2 card, kept as the rollback point for the 0.16.0 install (`card-mod-folder.tar` + `plugins/`) |
| `2026-09-30_pgwr_0.15.0/` (`RESULT.md`) | console result of the 0.15.0 run, per feature; the sword diagnosis and the two refuted levers |
| `2026-09-30_0041_card-diff.txt`, `2026-09-30_0123_card-diff.txt` | what each install actually changed, diffed against the pre-install backup |
| `sd-backups/sd-backup-20260930-004121` | the 0.14.1 card, kept as the rollback point for the 0.15.0 bundle install |
| `swap_2026-09-15_switch-v0.8.5.log` | swap return-pose log |
Not copied (still in modpack_test_1): ~60 near-duplicate crash logs in `pyra_mythra_clone/reports/console-2026-09-28-freeze`, `sd_backups`, `sd-backup-*` inside the old pgwr folder.
