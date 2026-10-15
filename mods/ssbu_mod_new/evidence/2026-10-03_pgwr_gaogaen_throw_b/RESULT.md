# gaogaen_throw_b — 2026-10-03 — READY, enabled installable package

User authorized choosing shared IDs on 2026-10-03. Allocated eflame 0x208 (520),
following Monkey Flip/up-B 0x1EE..0x1FA and Snake 0x1FB..0x207. Next free eflame
status is 0x209. The shared table was checked for duplicate allocations. No DK cargo
runtime dispatcher is currently registered; preserve one THROW PRE dispatch if DK is
integrated later. All registrations remain limited to eflame c06/c07.

Live source now declares/installs owned ACMD and status. The allocation environment
disable gate was replaced by the fixed reserved constant. Move diagnostics append to
`sd:/ultimate/pgwr_gaogaen_throw_b_log.txt` independently of global logging; existing
collective logging feature stays off. This agent did not access SD or run the game.

## Concrete package (B verified offline)

`builds/pgwr/gaogaen_throw_b-0.3.0/` contains the enabled plugin under its real Skyline
installation path and the complete combined mod tree. Task package 0.3.0 keeps shared
plugin/info version 0.20.20, per the user's no shared release bump instruction. This is
an enabled build, replacing the historical 0.2.0 disabled compile-only candidate.

- NRO SHA256 `5d7d9b8e565d9b38d6a73d804a36f4028e6fcd80ff92f15739ed96f3b783689b` (487424 bytes).
- Mod tree SHA256 `7a33ab21e5a6c313b20c7c6160d4b7cf92914bf759a45be11a5c4364e50bae2c`; 1992 files.
- MANIFEST.json SHA256 `70fc7e105293d910b97a0c32b40ebf81958fb55985046817e5e0134b3934c7da`.

Private offline Cargo build from current live source finished in 12.28 seconds with
features snake-neutral-b,hero-side-b; package/source/built NRO hashes match. Protected framework plugins are excluded. The installer-required libone_slot_eff.nro
is included byte-identically from 0.20.20 (not rebuilt or changed). All four custom script registration strings and enabled REGISTERED
marker are retained in the NRO. `enabled_package.py check` passed full tree and snapshot
hashes, unique status allocation, owned motion entries, all four custom registrations,
compiled/packaged equality and baseline preservation. 0.20.20 baseline has 1990 files;
only the declared 15 bank/list/config files change and 2 owned clips are added. Every
other baseline file, including Mythra assets and vanilla costumes, matches byte for byte.
The semantic sound merger checked previous samples, tones and labels while writing;
existing motion entries retain their raw bytes. Input baseline was not mutated.

Native donor audits and owned motion/offset inputs remain pinned in
`evidence/2026-10-02_pgwr_gaogaen_throw_b/` and `refs/gaogaen_throw_b/SOURCE.json`.
Donor intended behavior remains unboosted, with no Revenge system added. The pinned
back-throw impact attack is catch-only and no collateral box is invented.

## Reproduction and installation

Run verification from the mod root:

```powershell
python -B src/pgwr/tools/gaogaen_throw_b/enabled_package.py check
```

The package tool's prepare command requires a fresh destination and copies the 0.20.20
baseline, replays recorded semantic deltas and stages the enabled build. The package
manifest records final asset hashes, source snapshot, Cargo.lock, exact features and tool.
To rebuild the private source snapshot (run inside enabled-plugin):

```powershell
$taskCache = Split-Path (Get-Location).Path -Parent
$env:CARGO_HOME = Join-Path $taskCache 'cargo-home'
$env:CARGO_TARGET_DIR = Join-Path $taskCache 'runtime-target'
cargo skyline build --release --features snake-neutral-b,hero-side-b -- --offline
```

For the designated installer, from mod root in Bash/MSYS:

```bash
MGW_PACKAGE=builds/pgwr/gaogaen_throw_b-0.3.0 bash src/pgwr/install-to-card.sh --no-smashline
```

This command was not run. Existing SD installation stays at the recorded collective
release. No branches, commits, pushes, emulator runs, framework edits or shared version
changes were made. Old source/delta commands requiring status environment allocation or
an unapplied patch are historical; current live source is registered normally.

## Runtime limits and manual test (D unverified)

The compiler still warns that the binding's SIMD Vector3 return is not FFI-safe. The
native return/binding evidence is retained; offline compilation does not validate the
hook ABI, engine victim path or actual gameplay. No claim of a console pass is made.

1. Boot and retain `sd:/ultimate/pgwr_gaogaen_throw_b_log.txt` from REGISTERED status=0x208.
   DISABLED common NRO callback unavailable means failure. Keep atmosphere crash reports.
2. Test c06 and c07 separately. Use Pyra c00-c05 and native G&W as vanilla controls;
   their back throw and unrelated moves must retain prior behavior.
3. Compare unboosted vanilla Incineroar at the same damage/stage/victim. Test both
   facing directions, ledges and slopes; compare frame-50 facing reversal.
4. Use small, average and large victims/body classes. Inspect attachment and rotation;
   no T-pose, stretched limbs, hovering or early detachment.
5. Frame-step hit 28, clear 29 and release 30; compare target selection, throw launch
   at several percentages and recovery/cancel around frame 52.
6. Put a third fighter nearby: donor has no non-catch-only hitbox; compare contacts and
   verify no invented collateral damage.
7. Compare camera (-4,5), quake/rumble, smoke at 22/crown at 28, and all six sound/voice
   cues against the donor. Check ordinary/KO throws, both facings and multiple sizes.
8. Interrupt before/during/after impact when rules allow; stock loss, ledge transitions
   and rematch should leave no links, attacks, invincibility or camera residue.
9. Repeat donor control with Revenge active; recipient should stay on the unboosted
   path and acquire no Revenge multiplier/state.
10. Regress Snake down throw, Mythra Ness back throw, other moves and future DK routing.
    ENTER/VICTIM_INIT/END lines show execution markers, not gameplay pass/fail proof.

The first check attempt ran while package preparation was still completing and had
no MANIFEST yet; the final completed-package check passed. No gameplay test was run.

Installer preflight inputs checked offline: cargo_target resolves to this task cache, built/staged NRO equality passed, effect helper matches baseline, and full mod tree is present. No installer or SD discovery command was executed.
