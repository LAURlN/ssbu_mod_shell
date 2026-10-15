# pgwr 0.20.0 console run: Hero neutral-B small/medium/full charge levels all release

**Verdict: PASS.** The 0.20.0 fix is confirmed on hardware. 14 shots across all three charge
levels, no crash, and the card is byte-identical to the staged build.

## What was installed

- `libpyra_gamewatch_reskin.nro` sha256 `244447f8aa46e09ffe23b80bc9778119f8a42d5056df5aaa480664c8f5c466c4`
- 1701 mod files, tree sha256 `5cc3ee90da3649833061cacf2af72c86e6090e5ba41aebe336954108a144a4ab`
  (definition: sha256 of sorted `<sha256>  ./<relative path>\n` records, as
  `tools/package_pgwr_release.py` records it)
- `libone_slot_eff.nro` `e6e5659de3c95a3ff8484f87bd8ef1c129f6c563290903f9f8b8e95177dda70b`
- Backup of the pre-install card: `evidence/sd-backups/sd-backup-20260930-051537/` (held 0.19.0)
- Installed 2026-09-30 ~05:15:48 by the concurrent agent; verified independently for this record.

Card verification was read-only and reproduced the staging definition: the card NRO matches the
staged NRO by hash, the card mod tree hashes to the same `5cc3ee90…` over the same 1701 files, and
no `.new` staging residue remains.

## The fix under test

0.20.0 corrected a wrong `global_table` slot in `mythra/hero_neutral_b/fighter.rs`: the
pad-trigger word was read from `global_table[0x10]` instead of `0x1f`, so
`FIGHTER_PAD_FLAG_SPECIAL_TRIGGER | FIGHTER_PAD_FLAG_ATTACK_TRIGGER` never matched and `TO_SHOOT`
was never set. Consequence: only the full-charge branch fired, so no small or medium fireball could
be released and the guard-cancel out of the charge was dead.

## What the log shows

Source: `sd:/ultimate/pgwr_log.txt`, `BOOT v0.20.0` at line 1362 (1786 lines total at read time).

The 0.18.1 run immediately above it is the control, and it is the evidence that made the fix
necessary - it is in the same file at lines 839-1173.

| | 0.18.1 (before) | 0.20.0 (after) |
| --- | --- | --- |
| distinct `INIT begin` charges | 1 (always `charge=81`) | 14: 6, 9, 11, 26, 29, 32, 32, 33, 36, 38, 54, 81, 81, 81 |
| `NATIVE map collision supplied level=` | 2 only | 0 x3, 1 x8, 2 x3 |
| `PROJECTILE fly level=` | 3 only | 1 x3, 2 x8, 3 x3 |

The medium threshold is 18 (donor charge thresholds 18/81). In 0.18.1 the `charge=` histogram shows
the player passing through 11, 18, 27, 33, 39, 43, 45, 50, 61, 65 and 78, yet all 12 spawns were
`charge=81`: medium charge was reached and never fired. In 0.20.0 charges of 6 through 54 all
produce spawns, and the projectile `level` field takes all three values, so small, medium and large
all release.

Zero `[PGWR-HERO-N] FAIL` lines. Boot is clean: `READY owned initializer + map collision bridge;
13.0.4 signatures verified`, `REGISTERED c06/c07 statuses=0x1f5-0x1f9 article=8 mana=off`.

## Regression check in the same run

- **0.18.1's initializer fix still holds.** No crash report on the card is newer than 0.18.0's two
  (`01790734050_…` and `01790734167_…`, both 04:07 and 04:09), and 0.20.0 fired 14 projectiles
  through the same owned initializer. The `evidence/2026-09-30_pgwr_0.18.0/RESULT.md` tier-A fault
  stays fixed.
- **up-B did not regress.** The boot shows `READY Pyra class event slots +0x210/+0x220 (write
  true/true)` and `REGISTERED c06/c07 SPECIAL_HI + 0x1f9/0x1fa rescue 7 parachute 8 refresh on`, and
  the run contains `REFRESH entry 0 by class event +0x220` lines.

## Not covered by this run

This verdict is for the Hero neutral-B charge levels only. Not exercised here and therefore not
claimed: G&W up-B behaviour beyond the boot/refresh lines, the Cloud fair, the Pyra sword, the
Chrom jab and its new `jabopen`/`jabtoopen` esword clips, and Monkey Flip. The Monkey Flip victim
telemetry produced **zero** `[PGWR-MFLIP]` lines in this log despite the move being tested on both
G&W and Diddy; that was a logging defect (every Monkey Flip line used a bare `println!`, which never
reaches the card file), fixed in 0.20.2. This report is immutable.
