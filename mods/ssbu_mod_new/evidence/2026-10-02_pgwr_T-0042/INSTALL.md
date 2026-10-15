# T-0042 collective install record - 2026-10-02

Installer: Freebuff agent, on the user's instruction "build and install all pending
changes onto the switch in E: and tell me what to test" (task T-0042).
Automated testing and Ryujinx were benched for this run. **No console run happened.**

## What was actually pending

`CURRENT_INSTALL.md` listed two sections after the last recorded install. Only one
needed writing to the card:

| Section | Recorded state | Action this run |
|---|---|---|
| Little Mac forward smash family 0.20.16 | "READY, awaiting installation" | **Already on the card.** Verified byte-identical; no action. |
| R.O.B. down tilt, T-0036 custom animation | "STAGED ... Not installed" | **Installed.** |
| Hero side-B 0.20.15 | installed, level 2/3 open defects | Nothing to install; fixes are not packaged. |
| Snake / Monkey Flip / Cloud fair / Chrom jab / names / silent build | installed | Untouched. |

The Little Mac section's own status line was stale: the card already held 0.20.16.
`install-to-card.sh`'s last-backup marker reads `20261001-020530`, and the whole card
mod tree hashes equal to `builds/pgwr/0.20.16`, so that release was installed on
2026-10-01 without the section being updated. The angled up/down forward-smash
variants are therefore **on the card and still untested**.

## What was installed

Package `builds/pgwr/0.20.16+robot-dtilt.4/` (core 0.20.16, T-0036 animation variant).
It is 0.20.16 plus exactly two changed files, so the Little Mac family, Hero side-B,
Snake neutral-B, Monkey Flip, both Cloud sword trails, the Chrom jab, the
Ursula/Wilhelmine names and the R.O.B. dtilt's own ACMD/motion entry are all retained.

Command (from the mod workspace root):

```
MGW_PACKAGE="$PWD/builds/pgwr/0.20.16+robot-dtilt.4" \
  bash src/pgwr/install-to-card.sh --no-smashline --reused-nro
```

- NRO sha256 `81460e74313350aaf569ce832045e8586387ab4ddf10e51bfdb690a8d29ef834` (462,848 B)
  - **unchanged from what was already installed** - the change is asset-only, so no
    Rust was recompiled and no new binary was introduced.
- `libone_slot_eff.nro` sha256 `e6e5659de3c95a3ff8484f87bd8ef1c129f6c563290903f9f8b8e95177dda70b` (unchanged)
- Mod tree sha256 `66e3bc5e2c5f174271fd6d14f2dc3c4f6de4b7ca171f73382f3019d59b20b3f0` (1983 files)
- Both changed clips `d30722b5763f7b6e4f9e4d834cf57b91b69befccd5eb4321f8fbf3bdc81f6d19`
- Automatic backup `evidence/sd-backups/sd-backup-20261002-002850` (261 MB) holds the
  previous 0.20.16 tree, so the previous `c02attacklw3` clips
  (`f328174c727b7ba77bb47db6db76b4ad4588d8b88ed205e88b2da4d14199d4ab`) are recoverable.
- Framework installation **OFF** (`--no-smashline`).

## Verification, and its control

Independent re-hash after the install, not a re-read of the installer's own report
(`state/scratch/T-0042/verify_card.py`):

- card mod tree vs the package: **1983 / 1983 files, 0 differing, 0 only-card, 0 only-package.**
- card mod tree vs the package MANIFEST's own 1983 `mod_file_hashes`: **0 mismatches.**
- both `c02attacklw3.nuanmb` on the card are the new `d30722b5...`.
- protected plugins all byte-unchanged; smashline still
  `5f4091eed89c5854c2bfccb9f25b6e8da8c03ebedcaa5ab36eadebfc078bc8f7`.

Pre-install control: the same comparison run against `builds/pgwr/0.20.16` showed the
card equal to 0.20.16 in all 1983 files, and against the T-0036 package showed
**exactly 2 differing files and nothing else** - so the delta really is the two clips
and the install did not silently drop or add a file.

Forward-smash regression control (`state/scratch/T-0042/check_fsmash_entries.py`,
which imports the motion-list decoder from `tools/audit_littlemac_fsmash.py` rather
than reimplementing it). Run on both the candidate and the installed 0.20.16 tree,
the results are **identical**: all four motion kinds `attack_s4_s`,
`attack_s4_hold`, `attack_s4_hi`, `attack_s4_lw` decode in both c06 and c07 with
cancel 44/0/44/44, flags `0x84`, the four expected clips, four non-empty distinct
`game_script` words, and the recipient's own stale cancel-43 / `0x80` readings are
gone. The packaged NRO carries all 15 required handler names and all 4
forward-smash sound names. **The T-0036 change did not disturb the forward smash.**

## Two installer defects found and fixed (both were blocking, both pre-date this run)

1. **Card autodetect could not find the card on this machine.** The volume scan used
   `ls -d /[a-z]`, which returns nothing in Git Bash on Windows (there are no
   single-character root entries), so the scan produced an empty candidate list and
   the script refused to run at all. Replaced with a `mount`/`df` enumeration plus an
   explicit a-z fallback; the identity test (`$PLUG_REL` + `ultimate/mods` +
   `atmosphere`) still decides, and the refusal message now lists the volumes it saw.
2. **No way to install an asset-only variant.** The built-vs-staged NRO check needs
   the cargo cache, and `builds/.cache` had been pruned, so the one package shape
   that legitimately reuses an installed NRO could not be installed at all. Added
   `--reused-nro`, which *replaces* that check with a stronger one: the staged NRO
   must be byte-identical to the NRO already on the card.

Negative control for the new flag (`state/scratch/T-0042/`): a throwaway copy of the
package with one byte flipped in the NRO. `--reused-nro` refused it
("the staged NRO is NOT the one already on the card"), and the same package without
the flag was also refused (no built NRO). So the new path is not a hole in the
guard - it is a different, independently checked assertion. The tampered copy was
deleted.

## What is NOT established by this record

Everything about behaviour. The installed bytes are proven; not one statement here
says the down tilt looks right, that the hand meets the hitbox, that the donor sounds
play, or that the game boots. Specifically unverified: mesh deformation, palm
alignment to the full donor hitbox, slope and facing behaviour, recovery feel, and
the still-untested Little Mac **angled** forward smashes (`attack_s4_hi` / `_lw`) -
whose reachability on this fighter is an open tier-D question, not a settled one.
The logging Cargo feature is off, so this build writes no game log; absence of
`pgwr_log.txt` output is expected and is not a fault.

The manifest's 137 `source_hashes` were also re-checked: 82 differ from the working
tree **only** by CRLF/LF line-ending normalisation, which is a git-checkout artefact
on Windows and not a source change. The one genuine difference is
`src/pgwr/install-to-card.sh` itself, expected - this run edited it, and both the
0.20.16 and T-0036 manifests pre-date the edits above.
