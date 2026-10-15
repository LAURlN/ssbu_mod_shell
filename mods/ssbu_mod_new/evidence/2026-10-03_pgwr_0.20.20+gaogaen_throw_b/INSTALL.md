# Install record — 2026-10-03 02:12:15 — gaogaen_throw_b 0.3.0 on the installed 0.20.20

Installed by the Freebuff designated installer at the user's request ("install the current changes
to the switch"). AGENTS.md rule 23. Framework installation OFF.

Machine-readable record: `evidence/install-record-2026-10-03_021215.json`.
Backup of the previous card state: `evidence/sd-backups/sd-backup-20261003-021215`.

## What went on the card

| artifact | sha256 |
|---|---|
| `libpyra_gamewatch_reskin.nro` (487,424 B, **new binary**) | `5d7d9b8e565d9b38d6a73d804a36f4028e6fcd80ff92f15739ed96f3b783689b` |
| `libone_slot_eff.nro` (unchanged, copied in from 0.20.20) | `e6e5659de3c95a3ff8484f87bd8ef1c129f6c563290903f9f8b8e95177dda70b` |
| mod tree, 1992 files | `7a33ab21e5a6c313b20c7c6160d4b7cf92914bf759a45be11a5c4364e50bae2c` |

Package: `builds/pgwr/gaogaen_throw_b-0.3.0/` (`MANIFEST.json` `70fc7e10…`). Cargo cache read from
the package's own `MANIFEST.json` (`gaogaen_throw_b/runtime-target`); no shared cache was used, so
the "built NRO == staged NRO" check really did compare against this package's build.

Protected plugins re-hashed after the write, all four byte-unchanged:
`libsmashline_plugin.nro` `5f4091ee…` (the known-good patched 13.0.4 build),
`libarcropolis.nro` `49b6f634…`, `libarc_network.nro` `c7644991…`,
`libnro_hook.nro` `ca7aec03…`.

Shared plugin/`info.toml` version is deliberately **still 0.20.20** — the task package identity is
0.3.0 and no shared release bump was authorised.

## What was on the card before, and how that was confirmed

0.20.20: NRO `7242d2f5…`, mod tree `10cd7a07…`, 1990 files. Confirmed by an independent re-hash
**before** anything was written, not assumed from the previous record:
`tools/verify_installed_card.py builds/pgwr/0.20.20/ultimate/mods/pyra_gamewatch_reskin` →
1990/1990 equal, 0 differing, 0 only-card, 0 only-package, and 0 card-vs-manifest mismatches.

## Scope: what was installed and what was left out

Installed: **only** `gaogaen_throw_b` (Incineroar back throw on G&W `eflame` c06/c07, owned status
`0x208`). It is the sole READY section in `CURRENT_INSTALL.md`.

Deliberately **not** installed:

- `dk_cargo` — section reads INCOMPLETE / NOT READY. No runtime Rust, no integration NRO, no
  registration patch exists.
- `T-0054` eflame c06/c07 trail resource ownership — PENDING, candidate staged, not READY.
- Hero mana *reserved* parts — not built.
- Everything else in the queue was already on the card inside 0.20.20.

No combined rebuild was required or performed. This package is already a complete 1992-file tree
derived from the installed 0.20.20 and carries its own enabled NRO, so installing it *is* the merge
rather than an approximation of one. No other agent's live build or test input was touched.

## Delta against the installed 0.20.20

**15 changed files + 2 added owned clips = 17. Nothing removed.** Every other file of the 1990-file
baseline is byte-identical.

- `config.json`
- `fighter/eflame/motion/body/c06/motion_list.bin`, `.../c06/pgwrgaogaenthrowb.nuanmb` (added)
- `fighter/eflame/motion/body/c07/motion_list.bin`, `.../c07/pgwrgaogaenthrowb.nuanmb` (added)
- `sound/bank/fighter/se_eflame_c06.nus3{audio,bank}` + `.tonelabel` (3 files)
- `sound/bank/fighter/se_eflame_c07.nus3{audio,bank}` + `.tonelabel` (3 files)
- `sound/bank/fighter_voice/vc_eflame_c06.nus3{audio,bank}` + `.tonelabel` (3 files)
- `sound/bank/fighter_voice/vc_eflame_c07.nus3{audio,bank}` + `.tonelabel` (3 files)

## Checks that were actually run

Offline, tier B, by this installer:

1. `python -B src/pgwr/tools/gaogaen_throw_b/enabled_package.py check` → **PASS**: enabled NRO
   equality/registrations/status allocation, 1990 baseline files preserved except the 15 declared
   changes plus 2 owned clips, full tree and source hashes.
2. Pre-install card read vs `builds/pgwr/0.20.20` → 1990/1990 equal (see above).
3. Built NRO == staged NRO, `5d7d9b8e…` in both (enforced by the installer from the manifest's cache).
4. `--dry-run` before writing: card `/e`, 1992 files, hashes as listed above, nothing written.
5. Post-install `tools/verify_installed_card.py` vs the package tree → **1992/1992 equal**, 0 differing,
   0 only-card, 0 only-package.
6. Post-install cross-check against the manifest's own `mod_files` table → **0 mismatches**;
   an independently recomputed card tree sha256 equals the manifest's `mod_tree_sha256`
   (`7a33ab21…`).
7. Four protected plugin hashes after the write: unchanged.

### Measurements taken independently here, not taken on trust

- **Motion lists** (`c06` and `c07`), parsed with the project's entry decoder: **841 → 842 entries**.
  Exactly one key added (`0x14efb93f11`), appended at index 841. Zero keys removed, **zero existing
  entries changed bytes**, relative order of all shared keys preserved. The size delta is +64 B
  (2 × 32 B).
- **Sound banks**, decoded with the project's `tools/merge_hero_neutral_b_sound.py` codec:

  | bank | tones | prior tone records | prior audio blobs |
  |---|---|---|---|
  | `se_eflame_c06` / `c07` | 548 → 553 (+5 each) | byte-equal prefix | byte-equal prefix |
  | `vc_eflame_c06` / `c07` | 244 → 245 (+1 each) | byte-equal prefix | byte-equal prefix |

  So no pre-existing tone was lost, reordered or rebased in any of the four banks. (The raw files are
  not byte-prefix-preserving because new sample data is inserted, not appended — the codec-level
  check is the meaningful one.)
- **`config.json`**, compared as parsed JSON: `new-dir-infos`, `new-dir-infos-base`,
  `share-to-vanilla`, `share-to-added` identical; no key added or removed; the only per-costume
  change is one added file entry per slot. *Note:* the file's line endings changed LF → CRLF, which
  is cosmetic for arcropolis but is why the raw bytes differ from the baseline.
- **NRO marker scan**: the new binary carries `pgwr_gaogaen_throw_b_log.txt`, `REGISTERED status=`,
  `VICTIM_INIT kind=` and `pgwrgaogaenthrowb`. Markers for the previously shipped moves are unchanged
  against the 0.20.20 binary (`PGWR-NESSTHB` 1, `snake_grenade` 2, `pgwrsnake` 69, `lucas` 8,
  `Mythra` 12, `game_throwb` 1, `v0.20.20` 5) — the new build did not drop Snake, Lucas or Ness.

### One tooling defect found

`tools/verify_installed_card.py` cross-checks a manifest key named `mod_file_hashes`. This task's
`MANIFEST.json` does not use that key — it uses `mod_files` — so that script's manifest line printed
"0 entries, card mismatches 0" and was **vacuous** for this package. Its file-by-file card-vs-package
comparison is unaffected and passed. The real manifest cross-check was run directly against
`mod_files` and passed 1992/1992. Recorded rather than hidden; the tool should learn both key names.

## Not verified

Nothing here says anything about gameplay. **Runtime is unverified (tier D).** The compiler still
warns that the move's binding returns a SIMD `Vector3` across FFI; that hook ABI is unverified and
compilation cannot settle it. Snake down throw, Lucas down smash and Ness back throw from 0.20.20
are also still unexercised on hardware. No emulator was run.

`logging` remains OFF, so no `[PGWR-*]` global log lines exist. The move writes its own file
`sd:/ultimate/pgwr_gaogaen_throw_b_log.txt` independently of that feature, which is what the test
reads.

Test instructions: `RESULT.md` in this directory. Rollback: `evidence/sd-backups/sd-backup-20261003-021215`
(the installer also rolls back automatically if its own verification fails; it did not fire).
