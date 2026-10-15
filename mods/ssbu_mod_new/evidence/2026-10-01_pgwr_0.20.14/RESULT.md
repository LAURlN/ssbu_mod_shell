# pgwr 0.20.14 - hardware result

**Date:** 2026-10-01
**Package:** `builds/pgwr/0.20.14/`
**Agent:** Buffy
**Verdict:** **TIER A - hardware.** PASS.

## What was tested

Little Mac's forward smash (`AttackS4`) and its charge hold (`AttackS4Charge`) on Pyra
c06/c07 wearing the Mr. Game & Watch reskin, replacing G&W's own prop-spawning punch.

## What the user reported

> "The mac f-smash works great, also animation wise."

Read against what the release was supposed to deliver:

| Claimed | Result |
| --- | --- |
| Little Mac's straight right-arm punch animation | **Confirmed** - "animation wise" works |
| The move functions | **Confirmed** - "works great" |
| G&W's prop no longer spawns on this move | **Confirmed** - the user had listed the prop as the thing being fixed, and did not report it |

This is the first **tier A** result for this move. Everything recorded for 0.20.14 before
this run was tier B (measured offline) or tier D (hypothesis), and is now superseded on
this point.

## What this result does NOT cover

- **The up/down-angled variants.** They were not in 0.20.14 at all. They are added in
  0.20.16 and are **tier D until that package's own run** - see
  `CURRENT_INSTALL.md` test steps 9-12. A negative result there is inert, not a regression.
- **How the punch looks frame by frame.** "Works great" is a functional judgement. Nothing
  here measures the retarget's fidelity to Little Mac's original pose beyond the offline
  geometry checks (46/50 bones kept, 0 parent mismatches, arm chain intact).
- **Charge-hold timing in detail.** The user did not separately call out the wind-up; it is
  covered by the same "works great".

## Integrity of what was installed

Recorded in `evidence/install-record-2026-10-01_002928.json`, with automatic backup
`evidence/sd-backups/sd-backup-20261001-002928` holding the previous 0.20.13 state.

- NRO sha256 `e8bf3f0713489bad278e937c8a22baa8498ce393761dee94940d35734303165c` (335,872 B),
  **built == packaged == on card**, confirmed with `cmp`.
- Mod tree sha256 `cf778b3c5cef9d7db3738cf5f79023cd095dcee98a6626c0528a7e81e9b10604`,
  1933 files, every one re-hashed directly off the card and byte-identical.
- Protected framework plugins unchanged; `libsmashline_plugin.nro` =
  `5f4091eed89c5854c2bfccb9f25b6e8da8c03ebedcaa5ab36eadebfc078bc8f7`. Installed with
  `--no-smashline`.

## The packaging incident this release is also the cautionary tale for

The first packaging attempt **printed `PASS` and shipped the wrong binary**: the packager
picked its cargo target dir by a hardcoded name derived from the enabled feature, so it
read another agent's stale NRO out of the shared cache. Every structural check still passed,
because the mod tree was correct - only the plugin was wrong.

It was caught by one thing: grepping the *packaged* NRO for this move's own sound names
(`se_littlemac_smash_s02`, `vc_littlemac_attack05`), which were absent from the stale binary
and present in the freshly built one.

Both halves of that lesson are now enforced in 0.20.16 rather than remembered:

- `tools/package_pgwr_release.py --cargo-target <name>` records the cache it used in
  `MANIFEST.json`, and `--check` asserts the recorded cache is the one the NRO was read from.
  Pointing a check at another agent's cache now fails loudly
  (`packaged NRO differs from built NRO`) instead of passing.
- `tools/audit_littlemac_fsmash.py::check_handlers` greps the packaged NRO for all 15 handler
  names and all 4 sound names, so a missing handler cannot pass an audit again.

`install-to-card.sh` resolves the cache as `PGWR_CARGO_TARGET` -> the package's own
`MANIFEST.json` -> the feature-derived default, and echoes which one it chose, so a package
built in an isolated cache is installed from that same cache.
