# Session 2026-10-06 - plugin 0.4.0-ui, character list in the Mii maker - result

Tier A (console). Written by the coordinator from the user's chat report ("it seems to be
working") and the log left on the card, copied to `log_boot1.txt` (419 lines, 81905 bytes,
sha256 `f150160e85424bb86dabc97c7d9f0e111cf7ff7fe27a4ad0321dc84d2202eaa9`). One boot is in the
log (one set of `L0` lines). Installed files: `CURRENT_INSTALL.md` section 0.4.0-ui.

## Log

- Load: `presets ... state=ok presets=94 hashes=41 field_lines=3854 rejected=0`; `loadout ...
  origin=main state=ok accepted=1`; `list ... state=ok accepted=87 entries=87`; no `match=0`
  line; `UI|sites|ui=on|sites_ok=5/5|probes_ok=15/15|installed=5`.
- Four openings of the list, all `arm|entry=A|value=7` for `id=0000f589`: native headgear
  count 52 replaced by 88 rows (`item_num_set=1`).
  1. cancel -> `exit ... equal=1 restored=0 record_equal=1`.
  2. `decide|row=87|label=nam_chr1_00_koopag|preset=koopag|action=set` -> `store ...
     result=added`, `SV|result=ok|step=0|bytes=57`.
  3. opened with `current_row=87 preset=koopag`, cancel.
  4. (new editor scene) `decide|row=38 ... preset=dedede` -> `store ... result=changed`,
     `SV|result=ok`.
  Every `exit` line: `hat_before == hat_after` (`0x5a00000fa9efa5ea`), `record_equal=1`,
  `orig_null=0`.
- Card afterwards: `loadouts.txt` = `mc_loadouts 2` / `0000f58b preset fox` / `0000f589 preset
  dedede` (57 bytes, written by the plugin).
- Stat engine: 46 `OV` lines; 32 of the 41 field hashes were requested (`RQ`); last `L5`:
  `req=76800 x2nz=0 dropped=0 orig_null=0 src=preset:39422`.

## Findings (tier A)

1. **The replaced edit-menu chunk at `ui/script_patch/chara_make/make_mii_edit_actor.lc`
   loads**, and its exit value 7 reaches the dispatcher: way in A works. (This closes the
   open loader question from session 1.)
2. **The native headgear list accepts a different item count and plugin-supplied rows**:
   88 rows on a list built for 52, names from `nam_chr1_00_*`, scrolling, cursor placed on the
   current preset on re-entry.
3. **Decide and cancel are told apart correctly**, the choice is applied to the store and
   **`save_loadouts()` works on the console** (create, write, sync, read back, delete, rename).
4. **The Mii is not changed**: headgear handle and the first 0x200 bytes of the working
   record equal before and after, four times out of four; the restore path never ran.
5. No crash or hang reported.

## Not exercised in this boot (from the log)

Way in B (ZL/ZR), row 0 (clear), the sort button while the list is open (`sort_ignored=0`),
a reboot reading the saved file (the plugin's own write was read back, not re-parsed at
load), 9 of the 41 fields (never requested during this play), CPU players, more than two
players. Whether the user checked the normal hat and outfit screens and the Try marker is
not in the log.
