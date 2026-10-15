# Session 2026-10-05, boot 1 - plugin 0.3.0 + loader probes - result

Tier A (console). Written by the coordinator from the user's chat report and the log the user
left on the card, copied to `log_boot1.txt` (164 lines, sha256
`75b68a93782ebec31df13fea06ee1ac268d72ab00e273c9e60d3f5b9fd9d7ebf`). Not rewritten afterwards.

## What was installed

See `CURRENT_INSTALL.md` § 0.3.0-presets and its installation record: plugin 0.3.0-presets
(`libmii_customizer.nro` sha256 `55a786b6...`), `presets.txt` (`f6acbba1...`, 94 fighters),
boot-1 `loadouts.txt` (`38b74661...`, `0000f589 preset fox`), the message probe
(`mii_customizer_probe_msg/`, different-length 7788-byte chunk + new label `mnu_mc_probe_title`)
and the edit-menu probe (`mii_customizer_probe_edit/`, 10739-byte chunk; Favorite decides the
focused row). Packages `builds/0.3.0-presets/`, `builds/0.2.1-msg-probe/`, `builds/0.3.1-edit-probe/`.

## What the user did and reported (chat, 2026-10-05)

- "the stat changes worked" - the per-Mii preset was felt in play.
- The Mii special-move screen sub-title showed the raw key `mnu_mc_probe_title` instead of text.
- The Favorite-button test on the edit menu "didn't work"; the exact on-screen behaviour (favorite
  toggled as usual / nothing / other) was not yet reported at the time of writing.
- No crash or hang reported.

## Log (`log_boot1.txt`, tags `mc|...`)

- 7 `L0` lines: plugin 0.3.0-presets loaded (`base=0x62a2e04000`, `accepted_kinds=74`); `presets`
  ok (25517 bytes, 94 presets, 10 hashes, 940 field lines, 0 rejected); `loadout` ok (v2, 34
  bytes, 1 accepted, `overrides=on`); hook site `0x4e53e0` `match=1`, `installed=1`; `load_done
  base_ok=1`.
- 1 `LO` line: `id=0000f589|preset=fox`.
- 10 `OV` lines, all `id=0000f589|src=preset|preset=fox|p=1`, with the expected fox values:
  weight 104.0 -> 77.0, walk_speed_max 1.0000 -> 1.5230, run_speed_max 1.3700 -> 2.4020, dash
  1.6300 -> 2.0900, air_speed_x 0.9300 -> 1.1100, air_speed_y 1.4500 -> 2.1000, accel_y 0.0980 ->
  0.2300, accel_x_mul 0.0430 -> 0.0800, jump_y 30.9 -> 35.0, jump_speed_x 0.9500 -> 0.6800.
- 22 `F5` snapshots: all ten field hashes were requested; the third number (the hook's second,
  `x2`, argument) is 0 in every snapshot; `L5` counters stay `x2nz=0`, `dropped=0`, `orig_null=0`;
  last `L5`: `req=91376|...|st=ok:36037,rt:39,kind:10,noid:19051,noent:36239|src=explicit:0,preset:36037`.
- 14 `L4` lines: saved IDs `0000f589` (p0) and `0000f58b` (p1) in the slots, as in gate 1.
- No `X2` line (the `x2 != 0` path was never exercised this boot).

## Findings

1. **Tier A: per-saved-Mii stat presets work on the console.** The plugin loaded, read both
   files, and all ten movement fields for saved ID `0000f589` were overridden with preset `fox`
   values through the param hook; the user saw the change in play. The explicit-override path was
   not exercised (boot-1 file has no `weight` line) and `x2 != 0` never occurred.
2. **Tier A: a Lua chunk whose length differs from the original loads.** The sub-title showed the
   raw key of the new label, so the changed `make_mii_special_actor.lc` (7788 vs 7799 bytes) is
   in effect. This answers gate 1's open "different length" question for `.lc` files.
3. **Tier A: the added message label did not resolve.** A raw key is what a failed message lookup
   shows. Why is not yet known: the merged msg_menu may not reach the game, may be refused at
   read time, or the lookup may miss. Boot 1 left no ARCropolis log to read -
   `ultimate/arcropolis/logs/` on the card is empty and `logging_level` is `Warn` (see 5).
4. **Tier A: the Favorite-button edit probe produced no visible change** per the user. Whether the
   edit chunk loaded at all or its condition never matched is unresolved; the exact on-screen
   behaviour of the press separates "loaded but condition false" from "not loaded" only partly -
   a follow-up detail question is open.
5. **Tier B (offline, new on 2026-10-05): the card's ARCropolis is an older-generation build.**
   Strings in the card's `libarcropolis.nro` (sha256 `49b6f634...`) contain
   `arcropolis::fs::loaders`, the old `XMSBT ... could not be read due to the following syntax
   error` wording and `orbits-...` cargo check-out paths; the v4.1.x `modfs` / `patched cache`
   strings are absent. That is consistent with the 13.0.4 version gate (v4.0.7/v4.0.8) and with
   the earlier D-inference; it refutes the kb note that named v4.1.1 (corrected in place). Label
   addition exists in that line too (`scratch/.../scratch_loaders_v408.rs:247-275`), so the
   feature is not missing; the known difference is the patched-size answer (v4.1.x replies
   `base_size * 2`; the old line has no equivalent hook).

## What this does not settle

- Which matches of the checklist were actually played; the log alone cannot say.
- Whether the message failure is "patch not served", "served but larger than the size the game
  allocated", or "label lookup miss". Separating these needs an ARCropolis log at a verbose level
  and/or a control change that overrides an existing label in the same file.
- Whether the edit chunk loaded. The Favorite press report will narrow this; a positive control
  (unconditional visible change on the edit screen) would settle it.

## Next

Boot 2 (planned in `CURRENT_INSTALL.md`): loadout swap (`purin` + explicit `weight 130.0` for
`0000f589`; `fox` for `0000f58b`), `logging_level` raised to `Debug`, and the user's Favorite
report. If boot 2's log still does not separate the message causes, the next probe is a control
override of an existing label on the same screen (single changed file, two visible outcomes).
