---
title: The pgwr installer could not find the card on this machine, and had no path for an asset-only variant
summary: install-to-card.sh enumerated volumes with `ls -d /[a-z]`, which returns nothing in Git Bash on Windows, so autodetect failed outright; and with builds/.cache pruned there was no way to install a package that reuses the installed NRO.
status: verified
tags: [pgwr, installer, sd-card, git-bash, windows, tooling, mod-workspace]
updated: 2026-10-02
source: T-0042
---

## What

Two defects in `mods/ssbu_mod_new/src/pgwr/install-to-card.sh` both blocked a routine
install, and both were found only because a real install was attempted:

1. **Card autodetect could not find the card at all.** The volume scan was
   `ls -d /[a-z] | tr -d '/' | sed 's|^|/|'`. In Git Bash on Windows there are no
   single-character entries at the filesystem root, so the glob matches nothing, the
   candidate list comes out empty, and the script exits with "no volume found holding
   atmosphere/... + ultimate/mods + atmosphere" - even with the card correctly mounted
   at `E:`. This is a silent, total failure: the script's own error text blames the
   hardware ("Mount the Switch's SD card"), so it sends you off to re-seat a card
   that is already in the machine.
2. **Asset-only variants were uninstallable.** The script's central safety check is
   "a freshly built NRO exists, and it is byte-identical to the staged one", which
   exists because a packaging run once shipped another agent's stale NRO from a
   shared cargo cache. That check needs `builds/.cache/<name>/...`, and `builds/`
   had been pruned. A package that is deliberately asset-only - same NRO as the
   installed release, two animation files changed - therefore had **no** legal way to
   be installed at all.

Fixed on 2026-10-02: the scan now enumerates real volumes from `mount` and `df` with
an explicit a-z fallback, and the contents-based identity test (Skyline plugin dir +
`ultimate/mods` + `atmosphere`) still decides which volume is the card. For (2), a new
`--reused-nro` flag **replaces** the built-vs-staged check with a stronger assertion:
the staged NRO must be byte-identical to the NRO *already on the card*.

## Evidence

Tier B, all offline in `mods/ssbu_mod_new`, card mounted at `E:` throughout.

*Defect 1.* Before the fix, the candidate enumeration evaluated to the empty string:

```
$ ls -d /[a-z]
ls: cannot access '/[a-z]': No such file or directory     (exit 2)
$ ls mods/ssbu_mod_new
ls: cannot access 'builds/.cache': No such file or directory
$ MGW_PACKAGE=... bash src/pgwr/install-to-card.sh --no-smashline --dry-run
install-to-card: no volume found holding atmosphere/... + ultimate/mods + atmosphere.
```

Manual probe confirming the card was there all along, and that the identity test is
what was missing rather than the volume:

```
/e -> PLUG_OK MODS_OK ATM_OK
```

After the fix the same command prints `card: /e` and exits 0.

*Defect 2.* `builds/.cache` does not exist and the only `libpyra_gamewatch_reskin.nro`
files in the tree are the four copies inside `builds/pgwr/*/atmosphere/.../plugins/`,
i.e. packaged binaries with no corresponding build output. So the built-vs-staged
check could not run for `0.20.16+robot-dtilt.4`, whose NRO is deliberately the
already-installed `81460e74...`.

*Negative control for the new flag* - the important part, because "skip a safety
check" is exactly the kind of change that quietly removes a guard. A throwaway copy
of the package with one byte flipped in the NRO (`482a9ef8...` instead of
`81460e74...`) was rejected both ways:

```
$ MGW_PACKAGE=.../negctl bash src/pgwr/install-to-card.sh --no-smashline --reused-nro --dry-run
install-to-card: --reused-nro: the staged NRO is NOT the one already on the card.   (exit 1)

$ MGW_PACKAGE=.../negctl bash src/pgwr/install-to-card.sh --no-smashline --dry-run
install-to-card: no built reskin NRO at .../builds/.cache/pgwr-lm-target/...        (exit 1)
```

The tampered copy was deleted afterwards. So the new path is a *different* assertion,
not a hole: it can only be used to install a package whose binary is provably
identical to what is already running.

*Install and independent re-verification* (`evidence/2026-10-02_pgwr_T-0042/INSTALL.md`,
`evidence/install-record-2026-10-02_002850.json`): 1983/1983 card files equal the
package, 0 differing, 0 only-card, 0 only-package; 0 mismatches against the manifest's
own 1983 `mod_file_hashes`; the four protected framework plugins byte-unchanged. The
delta against the previously installed release is exactly the two
`c02attacklw3.nuanmb` clips.

*Line endings.* 82 of the manifest's 137 `source_hashes` mismatch the working tree,
and **all 82 are explained by CRLF/LF normalisation** (`git ls-files --eol` shows
`i/lf w/crlf`): a Windows checkout artefact, not a source change. Do not read a bulk
source-hash mismatch as tampering without testing the normalisation hypothesis first -
that check takes one pass and cleared 82 of 83 here. The single genuine difference was
`install-to-card.sh` itself, edited by this run.

No emulator, no console, no automated tests - testing was benched for T-0042.

## Why (if known)

Defect 1 is a POSIX-ism that silently does not hold in Git Bash. `ls -d /[a-z]` was
probably written for a WSL or MSYS root that does list single-letter mount points, and
it fails *quietly* rather than loudly, which is why it survived: the script still had a
hardcoded `/f /F /sdcard /mnt/sd` list ahead of it, so on the machine where the card was
`F:` the fallback list covered the case and the bug never fired. The drive letter moved
to `E:` and it fired immediately.

Defect 2 is the cost of a guard written for one package shape. The built-vs-staged
check is right for "I just compiled something" and wrong for "I deliberately changed
only assets", and there was no third option that did not involve fabricating a build
cache - which would have made the guard pass without meaning anything.

## What to do instead / next

* Use `--reused-nro` **only** for asset-only variants, and only after
  `tools/verify_installed_card.py` shows the intended delta. It is not a way to install
  a new binary.
* Anything carrying a new NRO: rebuild into the cache named by that package's
  `MANIFEST.json` (`cargo_target`) and install **without** the flag, so the
  built-vs-staged check runs.
* Run `python tools/verify_installed_card.py builds/pgwr/<ver>/ultimate/mods/pyra_gamewatch_reskin`
  after every install. It is an independent re-hash rather than a re-read of the
  installer's own success message, and it is the thing that would have caught a stale
  NRO being deployed.
* Beware: `CURRENT_INSTALL.md` claimed Little Mac 0.20.16 was "STAGED, not installed"
  when the card already held it. **Establish what is actually on the card by hashing
  it, not by reading the queue file** - and when writing a status line, prefer "verified
  on the card on <date>" over "READY, awaiting installation".
* CPython on Windows cannot see an msys `/e` mount; any tool that reads the card from
  Python needs a real `sd:/...` path. This silently produces an empty file list rather
  than an error.
