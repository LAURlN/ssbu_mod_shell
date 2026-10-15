# refs/ - pinned donor material per move, third-party inputs

| Folder | What | Provenance |
| --- | --- | --- |
| `diddy_monkey_flip/` | Diddy side-B ACMD (`donor_acmd/`), status `.c`, animation/parameter manifests, extract_params.py | `donor_acmd/manifest.json` (URLs, sizes, sha256); WuBoytH/SSBU-Dumped-Scripts |
| `mii_hero_spin_hi3/` | correct Hero's Spin (Hi3) animation/kinetic manifests, plus `airtime_audit.json` = measured attacker descent per hit window from `tools/audit_hero_spin_airtime.py` (regenerate with `--json`) | export dump + built plugin source |
| `mii_hero_spin_hi1_wrong/` | Hi1 = Stone Scabbard; **the wrong move** shipped for one release; PLAN.md is obsolete | kept as a warning + status `.c` files |
| `mythra_ftilt_chrom/` | Mythra/Chrom f-tilt ACMD (first mod) | `manifest.json` |
| `snake_grenade/` | Snake grenade item/status inspection; crash analysis | grenade is gated off |
| `snake_attack_hi3/` | Snake up tilt (`AttackHi3`) for Pyra c06/c07: clip, body motion list, donor skeleton, AI attack params, `vc_snake_c00`; plus `inventory.json`, and `donor_acmd/` (the four `AttackHi3` scripts as text, re-pinned 2026-10-02 - see `SOURCE.json` `corrections` and `handbook/graveyard.md` R-SNAKE-UPTILT-1) | `SOURCE.json` (live arc-network extraction 2026-10-01); `extraction.json` per-file sha256; `donor_acmd/manifest.json` per-file sha256 + commit |
| `lucas_attack_lw4/` | Lucas down smash (`AttackLw4` + `AttackLw4Hold`) for Mythra c06/c07: both clips, body motion list, donor skeleton, `ef_lucas.eff`, `se_lucas`/`vc_lucas` banks; plus `inventory.json` (measurements), `donor_acmd/` (Lucas, Mythra and R.O.B. scripts as text), a pinned G&W motion list used to cross-validate the entry parser, and a pinned vanilla Mythra skeleton/idle/motion-list as the recipient baseline. Key results: the charge kind is `attack_lw4_hold` not `attack_lw4_charge`; the motion delta is 2 bytes; `havel` is a built-in anchor, not a bone | `SOURCE.json` (offline extraction from the local 13.0.4 `data.arc` via `tools/arc-extract`, 2026-10-02); per-file sha256 in `SOURCE.json` and in each tool's `--check`; `donor_acmd/manifest.json` per-file sha256 + commit |
| `gamewatch_special_hi/` | G&W up-B (Fire): all status functions recovered from `lua2cpp_gamewatch.nro` + behaviour summary | `SOURCE.json` (sha256 of every input/output) |
| `younglink_neutral_b/`, `gamewatch_specials/` | ACMD excerpts | |
| `shulk_fair_gamewatch_fair/` | Shulk / G&W `AttackAirF` scripts, test skeleton/anim | |
| `skins/` | Black & Pink Mythra, Pink G&W (extracted; source archives remain in old workspace `skins_to_use`) | community skins; used by standalone and by pgwr colour themes |
| `clone_pack_configs/` | working ARCropolis `config.json` templates from the old clone packs (`new-dir-infos`, `new-dir-files`) | from `sd_backups/2026-09-29_before_pyra_gw_reskin`; the proven shape (`handbook/10`) |
| `swap_mod_snapshot/` | the shipping tree of the swap mod, needed as input by `src/pgwr/tools/build_mythra_moves.py` | old `mod_backup_2` |

Rule: a reference without a source record is not a reference. Add `SOURCE.json` (url, commit, date, sha256) when you add one.
Missing `SOURCE.json` on the folders above is a to-do (the old ones only had per-file manifests in some).
