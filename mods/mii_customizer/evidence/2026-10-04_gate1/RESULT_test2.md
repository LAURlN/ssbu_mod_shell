# Gate 1, test 2 - file probes on the console - 2026-10-04

Tier A (console). Written by the coordinator; not rewritten afterwards.

## What was installed

In addition to the plugin of test 1: `ultimate/mods/mii_customizer_probe_layout/` (layout.arc
sha256 `86044f63d4bb...`, 2 bytes differ from the original) and
`ultimate/mods/mii_customizer_probe_lua/` (make_mii_special_actor.lc sha256 `0ad3f815620f...`, 4
bytes differ from the original). Package `builds/0.1.0-gate1/step2_probes/`. Existing mod
`pyra_gamewatch_reskin` active.

## What the user did and reported (chat, 2026-10-04)

Opened the Mii special-move screen. "the neutral special row is smaller than the others and it
says side special instead of special moves as the menu title. apart from that nothing crashed or
behaved weirdly".

## Log

`test2_log_full.txt` (sha256 `34fc9ff3949a...`, 152 lines): the 137 lines of test 1 followed by the
second boot, 15 lines, `seq` 0..14. L0: all three sites `match=1`, `installed=1` again (second
boot, different module base). L2 seq 12-14: loader called with id `0x0000f58b` from the editor
return addresses `0x1810074`, `0x18102d4`, `0x180fcb8` (the user opened the other Gunner this time).
No match was played, so no L3/L4 lines.

## Findings

1. The game loads a changed `ui/script/menu/chara_make/make_mii_special_actor.lc` from an
   ARCropolis mod folder: the sub-title showed the side-special label. `set_sub_title` resolves
   its argument as a message key.
2. The game loads a changed `ui/layout/menu/make_mii_special/make_mii_special/layout.arc`: the
   first row was drawn smaller. The two floats at part payload +60/+64 are the rendered scale of
   that row, and the entry animation does not overwrite it.
3. No size- or hash-based rejection of either file was observed (both were same-length edits; a
   different-length file is still untested).
4. The screen stayed usable (user report; no specific interactions listed).

Control: test 1 on the same day without the probes, where the user reported nothing unusual.

## Verdict

Gate question 4 is answered: edited Lua chunks and edited layout archives for the Mii editor are
picked up through ARCropolis. Untested: files whose length differs from the original, added
layout parts, added files that do not exist in the base game.
