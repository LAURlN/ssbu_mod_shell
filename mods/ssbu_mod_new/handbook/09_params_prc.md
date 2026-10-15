# Parameters and `.prc`

Tier legend: `AGENTS.md` rule 8.

- **Never guess a gameplay value.** Extract from the donor `.prc` and generate a Rust table with the source path and SHA-256 in the header
  (`src/mgw_swap/src/monkey_flip_params.rs`, `src/pgwr/tools/extract_gw_params.py`). Prefix project-local constants (`mgw_`, `pgwr_`). (A/B)
- `pyprc` cannot enumerate keys and cannot add one. Use `src/pgwr/tools/prc.py` (typed read/write). Stock files have an unsorted hash table starting with hash 0;
  every struct's ref table is sorted by hash *value*; the writer keeps that but does not reproduce stock bytes. (B)
- Labels for hashes: `dumps/scripts/ParamLabels.csv`.
- Motion-folder `.prc` (`ik.prc`, `scharge.prc`, `update.prc`, `flip.prc`) are per fighter and skeleton specific; wrong ones dislocate legs (A).
- `fighter/<f>/param/expression_vl.prc` holds `param_visibility_data_body` (mesh groups) - lowercase mesh hashes; see `08`. Only add keys the recipient lacks and prove no mesh-name overlap with any of its costumes.
- `fighter/<f>/param/vl.prc` holds move params. G&W's `param_breath` (`pos_offset_x/y`, `life`, `move_interval`, `speed_y`, `scale_mul`) is read by the breath constructor from the **owner's decoded param object**; an eflame owner lacks it - solved by the 0.14.0 parameter bridge (built, untested; `07`).
- Air movement values come from the donor PRC, effect resources from the recipient (Hi3 lesson). Mythra common air gravity 0.137 / terminal 1.87; the Hi3 build scales the Mii values (0.106 / 1.55) down: 1.00/1.00 at build .c, 0.85/0.90 at .d, **0.70/0.70 since 2026-10-03**. These are hand-retuned, never donor data, because Mii's dedicated `Hi3` kinetic cannot be installed on `elight`. **B:** `tools/audit_hero_spin_airtime.py` measures what they do (descent per hit window against each window's donor box band, worst gap/band 0.81 → 0.63 at frame 38); `refs/mii_hero_spin_hi3/airtime_audit.json`, evidence `evidence/2026-10-03_pgwr_upb_gravity/RESULT.md`. Retention is still **D** until a console run. (A, tuning unfinished)
- Parameters that the dump does not print (ItemModule args, `change_motion` arity) must come from the compiled function, not from guessing (`05`, `06`).
- `FighterParamAccessor2` entries for other fighters (Snake) are not initialised for a foreign owner - null reads/stack overflow in the grenade attempt (A).

## Recovering a donor `vl.prc` that looks missing (T-0057, tier B)

The Hero SP values were blocked for a day because `fighter/brave/param/` is **empty in the
user's ArcExplorer export**. That directory being empty says nothing about the base game.
The supported route is already in this workspace:

1. find the ARC path in `dumps/decoded/arc_files.tsv` (it lists all 590,711 paths);
2. `tools/arc-extract/target/release/arc-extract.exe --arc gamedata/ssbu-13.0.4/data.arc
   --out gamedata/ssbu-13.0.4/files <arc path>` and keep the printed sha256;
3. decode it. `tools/dump_hero_mana_params.py` is the SP-specific example: it prints each
   wanted value with **the Hash40 the donor looks it up by**, read out of the file rather
   than from the label list, so the label table and the file can be checked against each
   other. Here all eleven keys matched, which is a real cross-check and not a formality.

Two things this settles that are worth remembering:

* **Do not read a value out of a NRO's parameter-read marshalling.** The NRO reads by
  Hash40 at runtime; the value is in the `.prc` and nowhere else. The Hash40 is the join.
* **Do not grep `data.arc` for a path** to test whether an entry exists (R-ARC-1). The YAP
  container stores hashes, not names, so the search returns nothing and looks exactly like
  "the file is not in the game".

Hero's own SP block, for reference: `param_private.sp_max` 100, `recover_sp` 1,
`sp_recover_frame` 60, `sp_recover_damage_mul` / `sp_recover_shield_mul` 0.8,
`sp_special_n1..3` 6 / 16 / 36, `sp_special_s1..3` 8 / 18 / 42, from
`fighter/brave/param/vl.prc` sha256 `dafa43c6...` (`refs/brave_special_n/T-0057/`).
