# pgwr 0.20.17 - collective install (T-0056), 2026-10-02

**What was on the card before this run:** `0.20.16+robot-dtilt.4`, installed 2026-10-02 00:28:50
by the T-0042 designated installer. Verified by hash before anything was written: mod tree
`66e3bc5e...`, 1983 files, byte-identical to `builds/pgwr/0.20.16+robot-dtilt.4`, NRO
`81460e74...`, both `c02attacklw3.nuanmb` `d30722b5...`.

**What is on the card now:** `0.20.17`, installed by this run at 2026-10-02 02:20:35.

| item | value |
|---|---|
| package | `builds/pgwr/0.20.17/` |
| manifest | `builds/pgwr/0.20.17/MANIFEST.json` |
| reskin NRO | `22bfbd01421280f61c15bdde54b9674df87e9beeccd28108f3a1bdeef960f901` (466,944 B) - **new binary** |
| one_slot_eff NRO | `e6e5659de3c95a3ff8484f87bd8ef1c129f6c563290903f9f8b8e95177dda70b` (unchanged) |
| mod tree | `730dd088d7999fd633736caab998a0f884d86631dcd36a7f6a3ce20327858394` (1983 files) |
| cargo cache | `builds/.cache/pgwr-T0056-target` (new, isolated) |
| features | `snake-neutral-b`, `hero-side-b` (`logging` **off**) |
| framework install | OFF (`--no-smashline`) |
| backup | `evidence/sd-backups/sd-backup-20261002-022035` (holds the 0.20.16+robot-dtilt.4 tree) |

## What went on the card, and why

Three changes were requested together ("install the new changes"). They are file-disjoint in
the source tree, so one combined build carries all of them:

1. **T-0052 - Hero side-B (Mythra c06/c07) Zapple orientation + Kazap diagnostics.**
   `brave_lightning2_swordspark` on `sword1` now uses `rot_z = -90` (the only behavioural
   change in that task), plus the bounded `BOLT` / `ACTIVATE lightning` / `APPEND lightning
   arrived` diagnostics. Kazap's arrival predicate was **not** changed, on purpose.
2. **T-0053 - Monkey Flip aerial locks.** The donor's `KICK -> FLIP_FALL` general lockout
   (HI/S/LW) is ported, the side lock now belongs to the battle object that set it, and a
   refused refresh prints one `SWAPGUARD` line.
3. **T-0048 - R.O.B. down tilt, stretched-arm recipe 3.0.0.** Asset-only: the two
   `c02attacklw3.nuanmb` clips, now `06fb085e...` (were `d30722b5...`).

Mod-tree delta against the previous card state is **exactly three files**: the two c06/c07
`c02attacklw3.nuanmb` and `info.toml` (version `0.20.16` -> `0.20.17`). 0 added, 0 removed.

**Excluded:** T-0050 (Little Mac fist effect merge, BLOCKED on missing donor bank and
converter inside the lab), T-0049 / T-0034 (research only), T-0054 / T-0055 (no package yet).
The Mythra `+0x170` receiver hook is not a new change: it is already in the installed
baseline and is untouched by this release.

**Logging stays OFF**, so this release writes no `pgwr_log.txt`. That is a deliberate
installer decision, not an omission: re-enabling the `logging` feature would be a second
state-changing change in the same test (rule 11) and would undo 0.20.10's silent build.
Consequence: the `[PGWR-MFLIP]` LOCK/BLOCK/REFRESH/SWAPGUARD markers from T-0053 will **not**
appear on this build and Monkey Flip must be judged by eye. The Hero side-B log
(`sd:/ultimate/pgwr_hero_s_log.txt`) is independent of that feature and will contain the new
`BOLT` lines.

## Offline checks (none of them behavioural)

- Release compile clean, features `snake-neutral-b,hero-side-b`, cache
  `builds/.cache/pgwr-T0056-target`, 1m21s. The only warnings are the pre-existing dead-code
  ones from T-0052's diagnostics.
- Built NRO == staged NRO == NRO now on the card (`22bfbd01...`).
- NRO carries the new markers: `BOLT life=`, `ACTIVATE lightning`, `APPEND lightning arrived`,
  `SWAPGUARD`, `GENERAL HI/S/LW`, `PGWR-MFLIP`.
- `package_pgwr_release.py --check` PASS, 1983 files, tree `730dd088...`.
- **Regression control** (`tools/check_forward_smash_package.py`), candidate vs the currently
  installed tree: identical output - all four `attack_s4_*` kinds in c06 and c07, cancel
  44/0/44/44, flags 0x84, four distinct non-empty `game_script` words, and all 15 handler +
  4 sound names in the NRO. Installing this release did not disturb the forward smash.
- `tools/audit_hero_side_b_package.py` on candidate and on the installed tree: identical
  output, the same 8 known "start/hold game script not registered" entries that T-0034
  already recorded (silently inert start/hold entries, not a regression).
- Post-install independent re-hash (`tools/verify_installed_card.py`, not a re-read of the
  installer's output): card 1983 files, 0 differing, 0 only-card, 0 only-package, and 0
  mismatches against the manifest's 1983 `mod_file_hashes`.
- Protected plugins byte-unchanged: smashline `5f4091ee...`, arcropolis `49b6f634...`,
  arc_network `c7644991...`, nro_hook `ca7aec03...`.

## Not verified - everything that matters

No console run, no emulator, no test suite (all benched). **Not evidence about behaviour:**
whether the Zapple bolt now points forward, whether Kazap completes, whether the Monkey Flip
kick lockout and the swap guard hold, whether the stretched-arm down tilt reads as a strike or
as a detached arm, and whether the game boots at all. Byte equality proves only that the card
holds what this package contains.

One package check could not run: the ArcExplorer export (`dumps/arc`) exists but is empty, so
the Hero neutral-B and Snake motion entries cannot be compared against the donor export. The
packager was run with `--skip-donor-checks`, which skips exactly those two comparisons,
prints a warning and records `"donor_checks": "SKIPPED: ..."` in `MANIFEST.json`. Everything
else in the package check still ran. The mod tree is byte-identical to the already-verified
`0.20.16+robot-dtilt.5` except `info.toml`, which is the substitute control for those entries.

**Rollback:** `evidence/sd-backups/sd-backup-20261002-022035` (plus the older
`sd-backup-20261002-002850`, which holds the pre-T-0036 0.20.16 tree).

Machine-readable record: `evidence/install-record-2026-10-02_022035.json`.