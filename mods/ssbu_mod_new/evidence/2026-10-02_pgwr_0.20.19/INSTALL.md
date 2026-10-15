# pgwr 0.20.19 - collective install of three Freebuff tasks, 2026-10-02

Installer: Claude, on the user's request ("when they are all done, install the changes they made
to the switch in E:"). Dispatch run: workspace `evidence/freebuff-dispatch/2026-10-02_run1/`.

**On the card before:** 0.20.17, verified by hash before anything was written
(`tools/verify_installed_card.py`: 1983/1983 equal, 0 manifest mismatches).
**On the card now:** 0.20.19, installed 2026-10-02 17:16:04.

| item | value |
|---|---|
| package | `builds/pgwr/0.20.19/`, manifest `MANIFEST.json` there |
| reskin NRO | `1771152551c8a4a0de85a9a0e766ff63ccafeaa9f431251880824c3b214f3b72` (471,040 B) - new binary |
| one_slot_eff NRO | `e6e5659de3c95a3ff8484f87bd8ef1c129f6c563290903f9f8b8e95177dda70b` (unchanged) |
| mod tree | `755e3e5543ddcea7a204e3ba3a5696a6cb0488687e7e4c8358d41b60765b0ea2` (1984 files) |
| cargo cache | `builds/.cache/pgwr-fbrun1-target`, features `snake-neutral-b,hero-side-b`; `logging` and `hero-mana-reserved` off |
| framework install | OFF (`--no-smashline`); smashline `5f4091ee...`, arcropolis `49b6f634...`, arc_network `c7644991...`, nro_hook `ca7aec03...` byte-unchanged |
| backup | `evidence/sd-backups/sd-backup-20261002-171604` (holds 0.20.17) |

## What is in it

1. **Little Mac forward-smash fist trails** (Freebuff slot 1 / T-0050): `effect/fighter/eflame/ef_eflame_c06.eff`
   and `_c07.eff` (both `6ab84bb729d8...`) added, `effect/fighter/littlemac/ef_littlemac.eff` removed,
   `config.json` declares the two banks in the `fighter/eflame/c06|c07` groups.
2. **Snake up tilt on G&W c06/c07** (slot 2): two `c02attackhi3.nuanmb`, two eflame `motion_list.bin`,
   twelve `se_`/`vc_eflame_c06|c07` bank files, `eflame.sqb`; ACMD in the plugin.
3. **Hero mana for the c06/c07 pair** (slot 3): Rust only. HUD gauge and recovery-on-hit are behind
   `hero-mana-reserved`, which is **not** built in (needs the user's approval).
4. **Carried along, not one of the three tasks:** the T-0052 Hero side-B Kazap arrival change that
   was built as 0.20.18 but never packaged. It was already in the working tree, so a build from the
   live tree necessarily contains it.

Mod-tree delta against 0.20.17: 19 changed, 2 added, 1 removed (1983 -> 1984 files).
**Not included:** T-0054 trail cleanup (PENDING, not requested).

## How it was assembled (not a `build.py` run)

`src/pgwr/build.py` cannot run in this workspace (no full export). As for 0.20.17, the package is
the installed tree plus measured deltas: `tools/stage_snake_uptilt_candidate.py --baseline
builds/pgwr/0.20.17 --version 0.20.19 --nro <combined NRO>` for the up tilt, then the two banks
from slot 1's `builds/.cache/fb-1-littlemac-fist-trails/generated/`, the bank removal and the
`config.json` edit by hand, then `tools/package_pgwr_release.py --version 0.20.19
--snake-neutral-b --hero-side-b --cargo-target pgwr-fbrun1-target --skip-donor-checks`.
**The three agents' edits to `build.py` have therefore never been executed.**

## Offline checks (none behavioural)

- Combined release compile clean (only the known dead-code warnings); built NRO == packaged NRO ==
  card NRO.
- `package_pgwr_release.py --check`: PASS, 1984 files. Its two donor motion comparisons were
  skipped (recorded in the manifest), as for 0.20.17.
- `audit_snake_uptilt_delta.py --baseline 0.20.17 --version 0.20.19 --combined ...`: PASS -
  `attack_hi3` is the only motion-list change, banks and sqb append-only, NRO carries the names.
- `audit_littlemac_fsmash.py` (with `MGW_EXPORT` = files extracted from `data.arc`): every
  functional check PASS, including "slot banks own both fist emitters and keep all 95 vanilla
  emitters" and, for the first time against real vanilla files, "recipient really lacks
  attack_s4_hi/lw". Its last line is `FAIL: 3 file(s) changed outside the intended overrides` -
  those three are the Snake up-tilt clip x2 and `eflame.sqb`, i.e. the other change in this build.
- `effect_trail_inventory.py`: `eflame: banks ['ef_eflame_c06.eff', 'ef_eflame_c07.eff']`, no
  `littlemac` bank folder.
- `check_forward_smash_package.py` and `audit_hero_side_b_package.py`: identical output on 0.20.17
  and 0.20.19 apart from the NRO hash.
- Post-install re-hash: 1984/1984 equal, 0 only-card, 0 only-package, 0 manifest mismatches.

Tool changes made by the installer: `package_pgwr_release.py` checks the final sound banks against
the last merge in the chain (now `snake_uptilt_sound.json`); `audit_snake_uptilt_delta.py`
tolerates other changes' added/removed files under `--combined`; `audit_littlemac_fsmash.py`
honours `MGW_EXPORT`. `stage_snake_uptilt_candidate.py` still crashes writing its final record
when `--baseline` is a relative path (after staging is complete) - not fixed.

## Not verified - everything that matters

No console run, no emulator. Whether the game boots, the trails draw, the kick looks and hits
right, and the mana gates and recovers is unknown until the user's test. Four state-changing
changes share this build (the user asked for the three together), so a failure does not by itself
attribute a cause (rules 9, 11).

**New always-on log:** `sd:/ultimate/pgwr_mana_log.txt` writes about one line per second while
Mythra c06/c07 is active (capped at 4000 lines per boot). If the game stutters once a second,
suspect this first.

**Rollback:** `evidence/sd-backups/sd-backup-20261002-171604`.
