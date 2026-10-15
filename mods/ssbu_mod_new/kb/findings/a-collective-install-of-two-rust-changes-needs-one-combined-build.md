---
title: A collective install of two Rust changes is one build in a fresh cache, and the logging decision belongs to the installer
summary: Combining T-0052 and T-0053 needed one combined build in a new isolated cargo cache; keeping the `logging` feature off made the change attributable to one test but left T-0053 without its log markers.
status: verified
tags: [pgwr, installer, cargo, collective-install, logging, rule-11, mod-workspace]
updated: 2026-10-02
source: T-0056
---

## What worked

Three queued changes went onto the card as release `0.20.17` (NRO
`22bfbd01...`) in one pass:

| change | files | kind |
|---|---|---|
| T-0052 Hero side-B Zapple/Kazap | `mythra/hero_side_b/{script_acmd,weapon,attack3_acmd,fighter}.rs` | Rust |
| T-0053 Monkey Flip aerial locks | `status/{monkey_flip,special_hi}.rs` | Rust |
| T-0048 down tilt recipe 3.0.0 | two `c02attacklw3.nuanmb` | asset |

The two Rust changes touch disjoint files, so one build carries both and no conflict resolution
was needed. The recipe:

1. **Check the two diffs are disjoint before building**, not after.
2. **Build into a fresh cache** (`builds/.cache/pgwr-T0056-target`), never one another agent
   left behind. `pgwr-mflip-target` held T-0053's verification NRO built *without*
   `snake-neutral-b` / `hero-side-b`, and `pgwr-heroside-target` held T-0052's - either would
   have produced a package that installs cleanly and is wrong. Record the cache in
   `MANIFEST.json` (`cargo_target`) so `install-to-card.sh` reads the NRO from the same place.
3. **Take the mod tree from the newest verified asset package** (`0.20.16+robot-dtilt.5`) and
   bump `info.toml`, rather than re-running `build.py`: `dumps/arc` is empty in this workspace,
   so a full asset rebuild cannot reproduce donor-side inputs. The substitute control is a
   `diff -rq` against that package - here exactly one file (`info.toml`) differed, which is the
   evidence that nothing else moved.
4. Because the release carries a **new** NRO, install **without** `--reused-nro`, so the real
   built-vs-staged check runs.

## The logging decision, and what it cost

The installed baseline keeps Cargo's `logging` feature off (the 0.20.10 silent core). T-0053's
evidence is a set of `[PGWR-MFLIP] LOCK/BLOCK/REFRESH/SWAPGUARD` lines that need it.

Keeping it off is the right call for a combined install: turning it on would be a second
state-changing change in the same test (rule 11) and would change performance behaviour the user
chose deliberately. The cost is concrete and must be handed over: **Monkey Flip has no log
markers on this build and must be judged by eye.** T-0052 was unaffected because
`pgwr_hero_s_log.txt` is written independently of the feature - so the Kazap `BOLT`
discriminators still work on a silent build. Worth knowing before writing diagnostics: check
which log a feature's lines actually go to before assuming a silent release is blind.

## The one thing that blocked packaging, and the fix

`package_pgwr_release.py` compares the Hero neutral-B and Snake motion entries against the
ArcExplorer export. `dumps/arc` exists here but holds **0 files**, so validation aborted and the
package could not be written at all. `--skip-donor-checks` (tool 1.3.0) skips exactly those two
comparisons, prints a warning, records `donor_checks: "SKIPPED: ..."` in `MANIFEST.json`, and
makes `--check` refuse a manifest that claims complete donor checks. Everything else still runs:
owned clips, `config.json` declarations, handler registrations, the effect-merge hash chain,
article hashes, sound banks including Snake's retained tones.

The general lesson: when a workspace input is missing, an **explicit, recorded** opt-out beats
silently weakening the assertion or faking the input - and the manifest has to carry the omission
so the next reader does not think the check ran.

## Not verified

No console run, no emulator, no tests. The combined build is one NRO, so a crash or a regression
in the next test does not by itself say which of the two Rust changes caused it (rule 9); the
controls that were run are static only (forward-smash motion entries and the Hero side-B package
audit both decode identically on the candidate and on the previously installed tree).