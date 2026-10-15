# Session 4, boot 2 - 2026-10-07 - 0.8.0 boots; menu and storage work; the kick froze in the bind pose (tier A)

Installed: plugin 0.8.0 `8198bd49ed8c0738a2d5b11649b0852f29f9dd012f2270d97e2e7876aa6ec5ca`, `menu.txt` `6e437998...`,
`ultimate/mods/mii_customizer_moves/` with a full `motion_list.bin` (`3894848c...`).
Log: `log_boot2.txt` (563 lines, sha256 `82291a9286d4e6e1...`), copied from the card.

User report: "when i have the mii brawler f tilt selected and use it ingame, i just t pose
and freeze".

What the log shows (tier A):
- The boot-1 stack fix holds: plugin loaded, `menu|state=ok|entries=25|allows=1|rejected=0`,
  `MV|load|status=registered|moves_off=0|smashline=ok`, `sites|...|probes_ok=48/48|installed=6`.
- Forward Tilt page: `list|page=entry:tilt_side|count=87|available=2`; choosing Mii Brawler
  `decide|...|row=77|preset=miifighter|action=set_slot`, `store_slot|...|result=added`,
  `SV|result=ok|bytes=116` (a version-3 file); the page reopened with `cursor=77`; row 0 later
  `action=clear_slot`, `SV|result=ok|bytes=81` (back to version 2). The slot store and both
  writer versions work.
- Match resolution per saved Mii: `MV|match|fighter=miigunner|id=0000deb5|tilt_side=miifighter`
  after the choice, `tilt_side=default` after clearing it, `id=00000000|tilt_side=default` for
  the editor preview.
- The status wrapper ran on agent `miigunner` and started the owned motion three times:
  `MV|exec|entry=0|motion=mc_attacks3_s|count=1..3`. So Smashline's status hook and the
  saved-Mii lookup inside it work for a Mii.
- 0.7.0: the Sword page opened with ONE row on the native list and cancelled cleanly
  (`list|page=entry:sword|count=1`); all four `exit` lines `equal=1|restored=0|record_equal=1`.
  No `sort|` line: sort by name was not exercised.
- Counters clean: `dropped=0|orig_null=0`. No crash report.

Why the fighter froze: `ultimate/arcropolis/conflicts.json`, written at this boot, lists
`fighter/miigunner/motion/body/c00/motion_list.bin` as shipped by both
`pyra_gamewatch_reskin` and `mii_customizer_moves`. The other mod ships a rebuilt Gunner list
(792 entries: the 774 vanilla ones + 18 of its own, its cargo-throw victim motions; card file
`5eedf4b32a5f...`). ARCropolis keeps one file per path and kept that one, so the three owned
motion kinds did not exist: `change_motion` to an unknown kind gives the bind pose, the
motion never ends and the wrapper's loop never leaves the status.

The coordinator's install record of the evening said no other mod has files under
`fighter/miigunner/`. That was wrong (a directory search on the card returned nothing and
was not double-checked); corrected in `CURRENT_INSTALL.md`.

Fix (B offline; D on the console until run):
1. The package ships `motion_list.motdiff` (`37fd45810853...`, 2188 bytes) instead of
   `motion_list.bin`. C, ARCropolis v4.0.7 source (`5f9fce9b`, `src/fs/loaders.rs`,
   `src/fs/utils.rs`): a `*.motdiff` whose name contains `motion_list` targets the `.bin` of
   the same name and is applied to `handle_load_base_file`, which returns another mod's
   physical file when there is one and the vanilla file otherwise. The card's ARCropolis
   contains the strings `motdiff` and `motion_list.yml` and links serde_yaml 0.8.26 +
   diff-struct 0.3.1; its exact version is not established.
   Offline (`tools/move-package/motdiff`, same serde_yaml version): the patch applied to the
   vanilla list gives the previously shipped list byte for byte; applied to the other mod's
   list it gives that list plus exactly our three entries (795, kinds unique).
2. Plugin `0193ba5fafd3...`: if the owned motion is not in the loaded list
   (`MotionModule::is_anim_resource`), the wrapper returns the vanilla move and logs
   `MV|missing|...|action=vanilla`. A missing animation now means a normal Gunner tilt, not a
   frozen fighter.
