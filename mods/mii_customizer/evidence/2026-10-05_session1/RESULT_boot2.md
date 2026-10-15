# Session 2026-10-05, boot 2 - plugin 0.3.0, loadout swap - result

Tier A (console). Written by the coordinator from the user's chat report ("everything works
as planned") and the log the user left on the card, copied to `log_boot2.txt` (141 lines,
23229 bytes, sha256 `06083fd7b969e4c9565b12d2b0f8466de7f43308195dc82b07549b4312223684`).
Not rewritten afterwards.

## What was on the card

As recorded in `CURRENT_INSTALL.md` section "Boot 2 - APPLIED": plugin 0.3.0-presets
(`55a786b6...`), `presets.txt` (`f6acbba1...`), `loadouts.txt` = the boot-2 file
(`f974c906...`: `0000f589 preset purin` + `0000f589 weight 130.0`, `0000f58b preset fox`),
both probe folders, ARCropolis `logging_level` = `Debug`.

## Log (`log_boot2.txt`)

| expected (CURRENT_INSTALL.md) | observed |
|---|---|
| plugin and files loaded | 7 `L0` lines: `0.3.0-presets loaded`, `accepted_kinds=74`; `presets ... state=ok presets=94 hashes=10 rejected=0`; `loadout ... state=ok version=2 bytes=78 accepted=3 preset_lines=2 ids=2`; site `0x4e53e0` `match=1`, `installed=1`; `load_done base_ok=1` |
| one `LO` line per ID | `id=0000f589 preset=purin weight=130.0000 walk_speed_max=-`; `id=0000f58b preset=fox weight=- walk_speed_max=-` |
| explicit line wins | `L3`/`OV` for `weight` (`h=0x0607cd5541`) `id=0000f589`: `orig=104.0000 v=130.0000 src=explicit` (seq 63/64 and again in match 2, seq 124) |
| A's other nine fields from `purin` | nine `OV` lines `id=0000f589 src=preset preset=purin` (0.0530, 19.79, 0.98, 0.08, 0.735, 0.70, 1.332, 1.65, 1.271) |
| B = `fox` | ten `OV` lines `id=0000f58b src=preset preset=fox p=1`, same values as boot-1 A (weight 77.0, run 2.402, ...) |
| non-Mii untouched | match 2: `p=1 kind=0` (Mario; `orig` 98.0 / 36.33 / 1.76 ...) all `ov=0 st=kind` |
| nothing broke | last `L5`: `req=153600 x2nz=0 dropped=0 orig_null=0 parent_overflow=0`, `st=ok:89281,rt:15,kind:53029,noid:11275`, `src=explicit:31,preset:89250`; no `reent`, no `gfull`, no `X2` line |

Additional observations:

1. **Match 2 was Gunner A (P1) against Mario (P2)**, not "Mario P1, Gunner B P2" as listed.
   This is a better control than planned for one open question: Mario sat on player index 1
   while slot 1 still held Gunner B's saved ID (`L4 ... p1=0000f58b:02020202`, `L3 ... p=1
   kind=0 id=0000f58b ... st=kind`). **A stale saved-Mii ID in a non-Mii player's slot does
   not cause an override** (tier A); the kind guard decides.
2. Third fighter group (slots 8/9, `L4` shows all ID slots zero): `p=0 kind=74 id=00000000
   st=noid`, 11275 requests. That is the Gunner model in the Mii editor (the user opened the
   special-move screen). **The editor preview fighter has no saved ID in the slot, so it uses
   the game's own stats** (tier A for the log lines; the reading "this is the editor preview"
   is the coordinator's inference from the order of events).
3. `x2nz=0` again: the `x2 != 0` path of the getter has still never been exercised.
4. **ARCropolis wrote no log file at `Debug`.** `ultimate/arcropolis/logs/` is still empty;
   only `mod_cache` (17:16) and `cache/13.0.4/offsets.toml` changed. So the raised level did
   not help with the message-label question; this build apparently does not log to a file
   (or only with a logger attached). `logging_level` was restored to `Warn` afterwards
   (card file sha256 `8448814d...`, equal to the backup).

## Findings

1. **Tier A: explicit lines beat the preset, per field.** A had `purin` for nine fields and
   `weight 130.0` from its explicit line.
2. **Tier A: a second preset and two Miis with different presets in one match work.**
3. **Tier A: stale ID slots are harmless for non-Mii fighters** (observation 1).
4. The user reported the play feel as planned and no crash or hang.
5. The message-label question is **not** answered by this boot (no loader log exists).
   The Favorite probe was not repeated.

## Offline readings added the same day (tier B/D, coordinator)

- Both label families the UI needs already exist in the game's `ui/message/msg_name.msbt`:
  131 `nam_mii_hat_*` labels (including `nam_mii_hat_unknown`, `nam_mii_hat_none_m/_f`) and
  107 `nam_chr1_00_*` labels; `msg_menu.msbt` has neither (B, grep of the extracted files).
  So a character list on the headgear screen needs **no added message label**. The failed
  probe label was an addition to `msg_menu`; the user's own `pyra_gamewatch_reskin` changes
  existing `msg_name` labels through an `.xmsbt` on the same loader.
- Why the Favorite probe showed nothing, read from the reconstructed source
  (`tools/lua-src/make_mii_edit_actor.lua`, lines 360-398 and 66-81): `update` handles
  `INPUT_FAVORITE` first (`switch_favorite`), then calls `update_selector0`, where the probe
  called `ComFrameActor.press_decide()`. That call asks the frame (the confirm button), not
  `selector0`, to decide; `selector0:get_decided_button_id()` stays negative, so nothing
  follows. The probe's design could not work **whether or not the chunk loaded** (D for the
  runtime reading; B for the source order). A correct entry sets `self.exit_value` itself.

## What this does not settle

- Whether a replaced chunk at `ui/script_patch/chara_make/make_mii_edit_actor.lc` loads.
- Why an added `msg_menu` label does not resolve (not needed for the next milestone).
- CPU players, more than two players, other modes.
