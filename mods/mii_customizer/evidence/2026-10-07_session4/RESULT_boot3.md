# Session 4, boot 3 - 2026-10-07 - 0.8.0 works: first borrowed move on the console (tier A)

Installed: plugin 0.8.0 `0193ba5fafd3...`, `ultimate/mods/mii_customizer_moves/` with
`motion_list.motdiff` `37fd45810853...` and three owned clips, `menu.txt` `6e437998...`.
Log: `log_boot3.txt` (406 lines, sha256 `ece89fbac14ce2ed...`), copied from the card.

User report: "sick, it all works now".

Log: `MV|load|status=registered`; `MV|match|...|id=0000f58b|tilt_side=miifighter` next to
`id=0000deb5|tilt_side=default` (two Gunners in one match, one with the move); eight `MV|exec`
lines, seven `mc_attacks3_s` and one `mc_attacks3_lw`; no `MV|missing` line; `loadouts.txt`
is version 3 with `0000f58b slot tilt_side miifighter`; `sort|page=entry:tilt_side|mode=2|order=name`
(sort by name used once); counters `dropped=0|orig_null=0`; no new crash report.
`conflicts.json` was not rewritten at this boot (still dated 21:05), i.e. no conflict.

Established (A): the card's ARCropolis applies a `motion_list.motdiff` on top of another
mod's `motion_list.bin`; declared owned clips load for a Mii Gunner; Smashline ACMD scripts
and a status wrapper work on agent `miigunner`; the choice is per saved Mii.
Not reported / not in the log: damage numbers, the high angle (`mc_attacks3_hi` never
started), cancel timing, sounds and effect, a CPU Gunner, a reboot with the choice kept,
the other mod's cargo throw on a Gunner, the `missing` fallback.
