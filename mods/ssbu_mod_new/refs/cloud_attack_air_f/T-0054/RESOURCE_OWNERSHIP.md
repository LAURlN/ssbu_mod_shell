# T-0054 - eflame c06/c07 trail resource ownership (staged candidate)

Date 2026-10-02. Branch `lab/T-0054`. Source/offline only; nothing run in game or emulator.
Root cause of the two-player ribbon loss is **not established** (tier D); this only removes a
proven resource-registration ambiguity.

## Loader behaviour read (tier C, `src/pgwr/tools/one_slot_effects_reference.rs`, shipped plugin not changed)
* Requests resolve by internal footer name: `get_raw_nutexb_data` records `hash(name) -> hash(NAME_C<slot>)`
  per slot and adds `hash(name)` to `FIGHTER_EFFECT_NAMES[EFF_FIGHTER_KIND]`; `make_after_image`
  rewrites both texture hashes using the owner's `INT_COLOR`. The file name is never consulted, so the
  rename key `(name, slot)` is per slot and simultaneous c06/c07 requests do not share a rewritten name.
* Trail folder choice and the "has trail" decision are cached per (fighter, slot) (`SlotCache`);
  `one_slot_cleanup` does not clear `EFF_FIGHTER_KIND`. Both are plugin-side and are NOT touched here;
  if the matrix still fails after this candidate they are the next evidence to hand back (reserved framework).

## Requested names per slot
`tex_cloud_sword1/2` (Cloud jab + fair), `tex_elight_sword1..5` (Mythra-derived scripts): each shipped once.
Pyra's own vanilla scripts request `tex_eflame_sword1/2/3` (and ThrowLw `tex_eflame_sword1` + `tex_elight_sword2`).
Baseline files for those carried `TEX_ELIGHT_SWORDn` footers, so those requests never matched a registered
name and Pyra kept her vanilla trail. **Decision (rev 2):** keep exactly that behaviour - no `tex_eflame_*`
file is shipped. (Rev 1 re-footered them as `TEX_EFLAME_SWORDn`, which would have re-themed every ordinary
Pyra trail with Mythra art; reverted as out of scope.) If themed ordinary Pyra trails are wanted, that is a
separate user decision.

## Delta per slot (14 -> 7 files; see trail_inventory.json for hashes)
| file | action |
|---|---|
| tex_cloud_sword1/2, tex_elight_sword1..5 | retained, **byte-identical** (black/pink c06, white/gold c07 preserved) |
| tex_eflame_cloud_sword1/2 | removed (no label; byte copies of cloud files, double registration) |
| tex_eflame_sword1..5 | removed (duplicate `TEX_ELIGHT_SWORDn` registrations; 4/5 have no label; 1..3 never matched) |

Not changed: ACMD, jab/fair geometry/timing, `config.json` structure (build.py declares `trail_<slot>/*.nutexb`
by glob, so declarations follow the folder), T-0050 `ef_eflame_<slot>.eff` / fist merge, Mythra `elight/*`.

## Manual matrix (user, in game; none done)
Same for each row: note jab ribbon AND fair ribbon visible + colour, sword blade present, effects intact.
1. Pyra c00 alone (vanilla control).  2. c06 alone.  3. c07 alone.
4. P1 c06 + P2 c07.  5. P1 c07 + P2 c06 (load order).  6. Rematch of 4, then of 5.
7. Form swap (Pyra<->Mythra) in c06 alone then in 4.  8. Pyra c06 + Mythra c06/c07 (cross-kind, H3).
9. Pyra c06 + Mario (control).  10. Mythra c06/c07 trails and Little Mac fist effect unchanged.
Pass: both ribbons in own colours in 4/5/6. If a slot still loses it, the cause is plugin/load side;
record which slot and whether order swaps it.
