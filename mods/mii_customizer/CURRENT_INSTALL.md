# Installation readiness

## 0.10.0-moves - Fox up smash added to 0.9.0 - 2026-10-07 - BUILT, NOT INSTALLED

Record: `evidence/2026-10-07_session5/INSTALL-0.10.0.md` (hashes, backup, console steps). Only the one
finished unit was added; the other six move reports are PARTIAL or in progress. Card:
plugin `294612f5...`, menu with one new `allow smash_up fox` line, package `mii_customizer_moves` with a merged
781-entry `motion_list.motdiff` (was 779). The 0.9.0 files are the backup.

## 0.9.0-moves - up tilt + down tilt (Brawler) added to 0.8.0 - 2026-10-07 - INSTALLED, NOT RUN

Record: `evidence/2026-10-07_session5/INSTALL-0.9.0.md` (hashes, backup, console steps). Only the two
finished units were installed; the other seven move reports are PARTIAL or in progress. Card:
plugin `21494f05...`, menu with two new `allow` lines, package `mii_customizer_moves` with a merged
779-entry `motion_list.motdiff`. The 0.8.0 boot-3 log is now `mii_customizer_log_session4_boot3.txt`.

## 0.8.0-moves - first borrowed move (Mii Brawler forward tilt) + everything of 0.7.0 - 2026-10-07 - INSTALLED 2026-10-07 (evening); boot 1 crashed at startup (fixed); boot 2: boots, menu and storage work, the kick FROZE IN THE BIND POSE (motion list conflict with the other mod, fixed); third build INSTALLED AND TESTED 2026-10-07 (boot 3: works, tier A; `evidence/2026-10-07_session4/RESULT_boot3.md`)

**Boot 2 (tier A, `evidence/2026-10-07_session4/RESULT_boot2.md`):** everything up to the
move works (boot, 25-row menu, Sword page, slot stored and cleared, loadouts version 3 and
2 written, per-Mii resolution at match start, the status wrapper starting the owned
motion). The fighter then stood in the bind pose and never left the tilt: the other mod
(`pyra_gamewatch_reskin`) also ships a Gunner `motion_list.bin`, ARCropolis kept that one
(`conflicts.json`), so our three motion kinds did not exist. Changed on the card: our
`motion_list.bin` removed, `motion_list.motdiff` added (a patch ARCropolis applies on top
of whichever list is loaded), plugin replaced by a build that falls back to the vanilla
tilt when the owned motion is missing. The other mod's folder was not touched (its list
hashes `5eedf4b32a5f...` before and after). The boot-2 log was renamed on the card to
`mii_customizer_log_session4_boot2.txt`.

**Boot 1 (tier A, `evidence/2026-10-07_session4/RESULT_boot1.md`):** the first 0.8.0 NRO (`cdb4f7e0...`)
crashed before its first log line: `main` reserved 324496 bytes of stack on a 64 KiB thread,
because the menu table (123 KiB since 0.7.0) and the loadout table (77 KiB) were passed by
value. Fixed by keeping both on the heap; largest frame now 18672 bytes (0.6.0, which works:
19584). The fixed NRO `8198bd49...` replaced the crashed one on the card (verified; nothing
else changed, the six other plugins hash as before). The table and test below are current.

Installed by the coordinator at the user's request in chat ("put together and install the
latest version", card mounted as E:, label SWITCH SD). **Nothing of 0.7.0 or 0.8.0 has run in
the game.** 0.7.0 was never installed on its own; its features (sort by name, Sword page,
loadouts version 3) are part of this plugin. Manifest `builds/0.8.0-moves/MANIFEST.json`,
report `research/P16-FTILT-MOVE.md` (coordinator banner on top).

| file on the card | from | bytes | sha256 |
|---|---|---|---|
| `.../skyline/plugins/libmii_customizer.nro` (REPLACED 0.6.0 `f44fc278...`) | `builds/0.8.0-moves/libmii_customizer.nro` | 258048 | `0193ba5fafd34c89d0c7e5c9a7004678d1364038b16198f2e9a44cca26098b51` |
| `ultimate/mii_customizer/menu.txt` (REPLACED `ea1d0d4b...`; adds Sword and `allow tilt_side miifighter`) | `builds/0.8.0-moves/session/menu.txt` | 1291 | `6e4379985a8c4442819fba63adfcf318de3c5007ac49bf37b0365597236903f4` |
| `ultimate/mods/mii_customizer_moves/config.json` (new folder) | workspace `gamedata/mii_customizer/P16-FTILT-MOVE/package/mii_customizer_moves/` | 376 | `bd773e2107865681abe63da5759184b41af25b82b8e1cc9280b7c1eea0ac4435` |
| `.../fighter/miigunner/motion/body/c00/motion_list.motdiff` (since boot 2; replaces our `motion_list.bin`) | same | 2188 | `37fd45810853fe79062b4c41ef0ad0ad9382b6d15af528a10911a5e97b30846b` |
| `.../c00/c01mcattacks3s.nuanmb` | same | 40184 | `8321c7b73c7ea667342480cec5b05a7ed0e1135b88ecb6171d5eb1c7efc4ecbb` |
| `.../c00/c01mcattacks3hi.nuanmb` | same | 39800 | `1771910ca79fbd0003224c35ee89062069b2a284c778fec7abbe2278c011e233` |
| `.../c00/c01mcattacks3lw.nuanmb` | same | 40056 | `e835ac586a9924b80766cc0a6eeb31594663daeea5af007efae24671fe294d41` |

Installation record: before, the card held plugin 0.6.0 (`f44fc278...`, checked), `menu.txt`
`ea1d0d4b...` (checked, local copy `builds/0.5.0-menu/session/menu.txt`), no
`mii_customizer_moves` folder, no switch file. All seven files re-hashed on the card equal to
the table. The six other plugins hash the same before and after (arcropolis `49b6f634`,
nro_hook `ca7aec03`, smashline `5f4091ee`, arc_network `c7644991`, pyra_gamewatch_reskin
`424914c1`, one_slot_eff `e6e5659d`). The 0.6.0 log (`7604dc78...`, identical to
`evidence/2026-10-07_session3/log_boot4_0.6.0.txt`) was renamed on the card to
`mii_customizer_log_session3_boot4.txt`. Unchanged: edit script 0.6.0, `list.txt`, `names.txt`,
`presets.txt`, `loadouts.txt` (`e91f6cd0...`, copy in
`evidence/2026-10-07_session4/loadouts_before_0.8.0.txt`: `0000f58b` kirby, `0000f589` dedede,
`0000c291` sonic). CORRECTED after boot 2: `pyra_gamewatch_reskin` does ship files under
`fighter/miigunner/` (a rebuilt `motion_list.bin` and three clips); the statement made here
at install time that no other mod does was wrong.

Offline checks observed by the coordinator (2026-10-07, on the installed NRO): build 0
warnings; host tests 47/0 + 35/0 + 4/0 + 16/0 + 6/0; `tools/stack-frames/stack_frames.py`
exit 0 (and exit 1 on the crashed NRO as control); `evidence/P16-FTILT-MOVE/check_p16.py`
exit 0; `scratch/2026-10-07_coordinator/p16_entries.py` exit 0 (the three added motion-list
entries: owned kind, game / expression / sound / effect script hashes equal the names the
plugin registers, clip hashes equal the shipped file names, flags 0x0084 and cancel frame 28
copied from the donor entries); `dirprobe` on the user's `data.arc`: `fighter/miigunner/c00`
exists, is the Gunner's only costume group and already holds `motion_list.bin` and the
Gunner's clips, so the `new-dir-files` key is the right one; the six `smashline_*` names the
NRO imports all exist in the card's Smashline build; the session `menu.txt` parsed by the
plugin's own parser: 25 entries, 1 allow, 0 rejected.

### Test (one boot, then a reboot)

Gunner A = `0000f589` (stats: King Dedede), Gunner B = `0000f58b` (stats: Kirby).

0. (Since boot 2) The Brawler choice was cleared again during boot 2, so step 2 is needed.
   If the kick is missing this time, the Gunner should do its NORMAL tilt instead of freezing
   (log `MV|missing|...|action=vanilla`); report that as well.
1. Boot to the main menu. Mii Fighters -> edit **Gunner A** -> **Minus**. The menu has 25
   rows; row 2 is "Sword: Mii Swordfighter", row 5 "Forward Tilt: Mii Gunner".
2. Open **Forward Tilt**: "Mii Gunner" ticked, **"Mii Brawler" selectable**, everything else
   greyed. Choose Mii Brawler: back on the menu, the row reads "Forward Tilt: Mii Brawler".
3. (0.7.0) Open **Sword**: one row, ticked; B. Open **Stats**, open the sort window, choose
   "By Name": alphabetical, "Mii Gunner" still first, tick still on King Dedede; B. Open Jab:
   which order, and what does the sort label say? B, B, leave the editor (save).
4. Training (or Smash): **P1 = Gunner A, P2 = Gunner B**. A's forward tilt should be the
   Brawler's **kick**: 8.0 %, actionable clearly earlier than the Gunner's own. Stick angled
   up while tilting: high kick 8.5 %; angled down: low kick 8.3 %. Listen for the swing
   sound and voice, look for the arc effect.
5. Gunner B's forward tilt: the Gunner's own arm-cannon tilt, as always. If easy, a CPU
   Gunner and any non-Mii fighter: normal.
6. Editor again: Gunner A, Forward Tilt -> **Mii Gunner** (first row). Match: A's own tilt is
   back. Then set **Mii Brawler** again.
7. Close the game, start it again, one match with Gunner A: still the kick.
8. Close the game and report: every step where something looked wrong, how the kick looked
   (feet, gun arm, sliding), and what steps 3 and 4 showed.

If the game crashes or hangs: note the step and what was on screen, do not retry, report.
A crash at boot or while a match with a Gunner loads points at the new folder or at the
script registration; in a tilt, at the move itself.

Log (`sd:/ultimate/mii_customizer_log.txt`): load `mc|MV|...|load|status=registered|moves_off=0|smashline=ok`
and `L0|menu|...|entries=25`; step 2 `decide|page=entry:tilt_side|...` followed by `SV|result=ok`
and a `loadouts.txt` starting `mc_loadouts 3` with `0000f589 slot tilt_side miifighter`;
match start `MV|...|match|fighter=miigunner|id=0000f589|tilt_side=miifighter` and
`id=0000f58b|tilt_side=default`; first tilts `MV|...|exec|entry=0|motion=mc_attacks3_s|count=1`
(`_hi`, `_lw` for the angles); step 3 `sort|page=entry:stats|mode=2|order=name|...`.

Decided by this test (D until seen): the game loads the three added clips and the rebuilt
motion list for a Mii; Smashline scripts and a status wrapper work on agent `miigunner`; the
per-object choice (A kicks, B does not); the remapped sounds; the 0.7.0 points (one-row list,
sort window on our list, cursor and tick after a re-sort, sort label on the next page).
Known differences from the donor, by design: the Gunner's own swing sound
(`se_miigunner_attackhard_s01`) and voice sequence; the angle is read once when the tilt
starts, from the stick (threshold 0.28).

Rollback, mildest first: empty file `ultimate/mii_customizer/moves_off` (no move scripts, the
Brawler row greyed again; stats and menu stay); delete `ultimate/mods/mii_customizer_moves/`
(then also use `moves_off`, or a chosen kick has no animation); the 0.6.0 NRO
`builds/0.6.0-menu/libmii_customizer.nro` plus `builds/0.5.0-menu/session/menu.txt` (0.6.0
reads a version-2 `loadouts.txt`; if the plugin has written version 3, put
`evidence/2026-10-07_session4/loadouts_before_0.8.0.txt` back as `loadouts.txt`).

---

## 0.7.0-menu - sort by name, Sword option page - 2026-10-07 - NEVER INSTALLED ON ITS OWN; shipped inside 0.8.0-moves (above)

Worker build (P14-SORT-OPTIONS), reviewed by the coordinator. **Nothing of it has run in the
game.** Needs the card mounted and a go-ahead.

| file on the card | from | bytes | sha256 |
|---|---|---|---|
| `.../skyline/plugins/libmii_customizer.nro` (REPLACES 0.6.0 `f44fc278...`) | `builds/0.7.0-menu/libmii_customizer.nro` | 237568 | `b9751751915cc8c2dd1e664df05137703612caa1299fdd12e1c7694b56057f88` |
| `ultimate/mii_customizer/menu.txt` (REPLACES `ea1d0d4b...`; adds the Sword entry after Stats) | `builds/0.7.0-menu/session/menu.txt` | 1259 | `975ac5e4f8087b208dd02eeea647d847dc93a0c26874c5826d200dcf2789b8a6` |

Everything else stays (edit script 0.6.0, list, names, presets, loadouts). Checks observed:
worker check 389/0; host tests 47/0 + 35/0 + 16/0; the new `menu.txt` parsed by the 0.7.0
parser: 25 entries, 0 rejected, Sword page 1 row.

Test: (1) Minus on the edit menu: 25 rows, second row "Sword: Mii Swordfighter". (2) Open
Sword: ONE row, ticked; A returns; open again, B returns. (3) Open Stats, open the sort
window, choose "By Name": characters alphabetical, "Mii Gunner" still first, cursor and tick
still on the same character. (4) Choose a character in that order, reopen Stats: the tick is
on that character. (5) Sort by one of the other two options: fighter order again. (6) With
"By Name" active go back and open Jab: which order, and what does the sort label say?
(7) Sort on the main menu: nothing reorders. (8) Leave, play a match, check the chosen
stats are the chosen character's.
Log: `sort|page=entry:stats|mode=2|order=name|cursor=..|tick=..`; `decide|...|preset=<the
character picked>`; `page|from=main|to=entry:sword`; every `exit` with `equal=1|record_equal=1`.

Tier D decided by this test: a one-row list on the native 52-row list; the sort window on
our list; cursor and tick after a re-sort; the label/order mismatch described in the
coordinator banner of `research/P14-SORT-OPTIONS.md`.
Rollback: the 0.6.0 NRO and the previous `menu.txt` (`builds/0.5.0-menu/session/menu.txt`);
0.6.0 rejects the two Sword lines of the new file and shows the other 24 entries.

---

## 0.6.0-menu - Minus opens the menu, button tip - 2026-10-07 - INSTALLED AND TESTED 2026-10-07 (user: "works"; log `evidence/2026-10-07_session3/log_boot4_0.6.0.txt`: `minus=on`, two `minus|set=1`, each followed by `arm|entry=A|value=7`; tier A)

User request: open the mod menu with Minus anywhere on the edit menu instead of Favourite
on Headgear, with a tip in the top corner. Manifest: `builds/0.6.0-menu/MANIFEST.json`.
**Nothing of it has run in the game.** Needs the card mounted and a go-ahead.

| file on the card | from | bytes | sha256 |
|---|---|---|---|
| `.../skyline/plugins/libmii_customizer.nro` (REPLACES 0.5.2 `19891678...`) | `builds/0.6.0-menu/libmii_customizer.nro` | 110592 | `f44fc278f0fd65a8db228f8c86ebf23e4317231bc084d8131181db7a0fa8c01a` |
| `ultimate/mods/mii_customizer_ui/ui/script_patch/chara_make/make_mii_edit_actor.lc` (REPLACES `0ec8b495...`) | `builds/0.6.0-menu/mii_customizer_ui/...` | 10905 | `c50b9764e043942b81ec9bb5018c2dcfdd4ab79b5e5d02f6cc1983ea8d1e3b40` |
| `ultimate/mods/mii_customizer_ui/info.toml` (REPLACES `fdf15227...`) | `builds/0.6.0-menu/mii_customizer_ui/info.toml` | see manifest | see manifest |

How it works: while the edit menu is open the plugin reads the controllers (nn::hid) once
per frame; a new Minus press sets the script global `MC_MINUS`; the edit script sees it in
its update, clears it and leaves with exit value 7, which opens the mod menu as before.
Favourite only toggles the favourite mark again. The tip's icon is the game's own Minus
glyph label and its text is "Advanced Options".

Checks (coordinator): plugin build 0 warnings; host tests 47/0 + 35/0;
`builds/0.6.0-menu/build_edit_script.py` exit 0 (generator `--strip`, compile, only
`initialize` and `update` changed, layout names, glyph label); `build_check.py` both chunks
byte-identical.

Test: (1) open the edit menu of a Gunner: the top-corner tip shows the Minus glyph and
"Advanced Options". (2) Press Minus with the cursor on Headgear: the mod menu opens; B
returns. (3) Same from another row and from the Try / Random buttons. (4) Press Favourite on
Headgear: only the favourite mark toggles; is the tip still right afterwards? (5) Open a
sub-screen (hat list) and come back: tip still right, Minus still works. (6) Minus in the
normal hat list or elsewhere does nothing new.
Log: `sites|...|minus=on`; per press `UI|minus|set=1|n=..`, then `arm|entry=A|value=7`.

Tier D, decided by this test: the plugin's first real nn::hid read (a crash or freeze on
entering the edit menu would point there: create `ultimate/mii_customizer/minus_off`);
whether `MC_MINUS` reaches the script; glyph rendering, fit and persistence of the tip.
Rollback: 0.5.2 NRO + `builds/0.4.0-edit-entry/variant_entry/` (Favourite on Headgear).

---

## 0.5.2-menu - current choice shown on the menu rows - 2026-10-07 - INSTALLED AND RUN 2026-10-07 (log `evidence/2026-10-07_session3/log_boot3_0.5.2.txt`: names 87/0, one main-page visit, text_set=702, text_missed=0; the user reported it looked good, tier A)

User request after session 3: see on the 24-row menu what is selected for each entry.
0.5.2 writes "<entry>: <character>" on each main-page row: the Stats row shows the Mii's
stats preset (or Mii Gunner when none), every move row shows Mii Gunner (nothing can be
chosen for a move yet). Names come from a new optional card file. Manifest:
`builds/0.5.2-menu/MANIFEST.json`. Needs the card mounted and a go-ahead.

| file on the card | from | bytes | sha256 |
|---|---|---|---|
| `.../skyline/plugins/libmii_customizer.nro` (REPLACES 0.5.1 `9cdcbd67...`) | `builds/0.5.2-menu/libmii_customizer.nro` | 110592 | `19891678bdf1cfd81573b8ec9776fb4296562deb2782cc809507eea2a83a15b2` |
| `ultimate/mii_customizer/names.txt` (new) | workspace `gamedata/mii_customizer/COORD-session3/names.txt` | 1353 | `a0c20055dbe1510a0b8ba35c2c71a355ab13c8ec1c40781a68080ce4315458e4` |

Everything else stays. Checks: build 0 warnings; host tests 47/0 + 35/0; names tests 4/0.
Test (short): open the menu for a Gunner with a preset: first row "Stats: <character>",
other rows "...: Mii Gunner". Change the stats character, return: the row follows. Clear it:
"Stats: Mii Gunner". Look for text that is cut off or shrunk on the long rows ("Neutral
Special: Mii Gunner"). Log: `L0|names|...|state=ok|accepted=87|rejected=0|default=Mii Gunner`.
Rollback: delete `names.txt` (rows as in 0.5.1) or the 0.5.1 NRO.

---

## 0.5.1-menu - customization menu with pages - 2026-10-07 - INSTALLED AND TESTED 2026-10-07 (works, tier A; `evidence/2026-10-07_session3/RESULT_boot2.md`)

Boot 1 with 0.5.0 (`evidence/2026-10-07_session3/RESULT_boot1.md`, tier A): the plugin
installed **no** UI hook, because another plugin on the card has an inline hook on the entry
of the text setter `0x37a22f0`, one of the 48 load probes (`probes_ok=47/48`). Favorite on
Headgear then just returned to the edit menu. **0.5.1** (`builds/0.5.1-menu/libmii_customizer.nro`,
102400 bytes, sha256 `9cdcbd676abdf48b97c18592f64f22815e807f04012b099462c7fa38a19518da`)
accepts that hook at that one entry and is on the card now (verified); the 0.5.0 log was
renamed to `mii_customizer_log_session3_boot1.txt`. Everything else below is unchanged: same
files, same ten test steps, same expected log lines, plus one new load line
`L0|ui_probe_entry_hooked=0x37a22f0|accepted=1` and `sites|ui=on|...|probes_ok=48/48|installed=6`.
Extra failure pattern: a crash or wrong text when the menu draws -> create `text_off`.

### (as written for 0.5.0)

Mod mode now opens a menu (Stats + 23 move slots); each row opens a character list. On the
Stats page every character can be chosen, as in 0.4.0. On a move page only "Mii Gunner" (the
default) can be chosen and every other character is greyed, because no move exists yet.
**None of the new parts has run in the game** (page changes, greyed rows, literal row text,
a list shorter than the native one). Report: `research/P11-MENU.md`; worker manifest
`builds/0.5.0-menu/MANIFEST.json`; session files and hashes `builds/0.5.0-menu/SESSION.json`.
Installed: all five files copied and sha256-verified on the card (E:); the old log was renamed to
`mii_customizer_log_session2.txt`; no `ui_off` / `text_off`. Backup of what was replaced (0.4.0 NRO,
marker edit script, info.toml, loadouts.txt): `evidence/2026-10-07_install_backup/`.

| file on the card | from | bytes | sha256 |
|---|---|---|---|
| `atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmii_customizer.nro` (REPLACES 0.4.0 `d28aea75...`) | `builds/0.5.0-menu/libmii_customizer.nro` | 102400 | `565014abfb483cb08ab12c153676f82787ed92a94b14eee89f598c150335ec27` |
| `ultimate/mii_customizer/menu.txt` (new) | `builds/0.5.0-menu/session/menu.txt` | 1184 | `ea1d0d4b841c72c8fbe0062c45cfbfb1016414c1e5780597e5a0d7d5e01f3c66` |
| `ultimate/mii_customizer/list.txt` (REPLACES `f74048de...`; same file without the Mii Gunner row) | workspace `gamedata/mii_customizer/COORD-session3/list.txt` | 2568 | `82e941bf09f554ed1600b89bae5b5e9c91dc6b23332a14a78c37b8cb17398cac` |
| `ultimate/mods/mii_customizer_ui/ui/script_patch/chara_make/make_mii_edit_actor.lc` (REPLACES the marker variant `dc47a9e6...`) | `builds/0.4.0-edit-entry/variant_entry/mii_customizer_ui/...` | 10745 | `0ec8b49554a3e190be4ec7747a3918f3533f11276250a577ad2bfe829ff4eb8a` |
| `ultimate/mods/mii_customizer_ui/info.toml` (REPLACES `fb2fe26b...`) | `builds/0.4.0-edit-entry/variant_entry/mii_customizer_ui/info.toml` | 633 | `fdf15227d094a7838f3977d3c8071d3458fa80310ec38dd10149c1c5ad550538` |

Unchanged on the card: `presets.txt` (wide, `8c763e77...`), `loadouts.txt` as the plugin
saved it (A `0000f589` = `dedede`, B `0000f58b` = `fox`). At install: rename
`ultimate/mii_customizer_log.txt` to `mii_customizer_log_session2.txt`; make sure no
`ui_off` / `text_off` file exists in `ultimate/mii_customizer/`. Nothing else is touched.

Offline checks observed by the coordinator (2026-10-07): worker check 358/0 with 11 negative
controls; host tests 47/0 + 35/0; NRO hash equals the manifest; the three card text files
parsed by the plugin's own parsers (`scratch/2026-10-07_coordinator/session_check.rs`):
presets 94, list 86 rows, menu 24 entries / 6 labels / 0 rejected; main page 24 rows, each
character page 87 rows, 87 available on Stats and 1 on a move page.

The edit script is now the plain variant: **the Try button is back**. This variant differs
from the tested marker variant only by the missing marker statement and has not run itself.
If Favorite on Headgear does nothing, use way in B (hold ZL or ZR, press A on Headgear).

### Test (one boot, then a reboot check)

1. Boot. Mii Fighters -> edit **Gunner A** -> on **Headgear** press **Favorite**. Expect a
   list of 24 rows: Stats, Jab, Dash Attack, ... Down Special. No tick anywhere.
2. Move to **Jab**, press A. The list closes and reopens as a character list: first row
   "Mii Gunner" with cursor and tick, **every other row greyed**.
3. Move down onto greyed rows (scroll a page too) and press **A several times** on one.
   Nothing should happen (a refusal sound is fine). Does the cursor move over greyed rows
   normally, or does it skip or stick?
4. Press **B**: back on the menu, cursor on Jab.
5. Open Jab again, press A on **Mii Gunner**: back on the menu.
6. Open **Stats**: all rows normal, cursor and tick on King Dedede. Choose **Kirby**: back on
   the menu, cursor on Stats.
7. Open Stats, press A on the first row (**Mii Gunner** = clear). Open Stats again: tick on
   the first row. Choose **Kirby** again.
8. Five times: open any row and leave with B (ten page changes). Then **B on the menu**: the
   normal edit menu is back; move around in it.
9. Open the **normal** Headgear screen (A on Headgear): usual hats, do not change one; cancel.
   Open Outfit, cancel. Leave the editor (save). One match, Gunner A against Gunner B: A
   should feel like Kirby, B like Fox.
10. Close the game, start it again, one more match (or just boot), close, and report: any
    step where something looked wrong, and how the text and the greyed rows looked.

If the game crashes or hangs: note the step and what was on screen, do not retry, report.

Decisions that depend on this test and that offline evidence cannot settle: whether
restarting the headgear state in place is clean (else: the alternative of P11-MENU section
4); whether a list shorter than the native 52 rows behaves; whether the greyed look and the
refusal on A are the game's own; whether literal text shows, fits and stays.

Rollback, mildest first: empty file `ultimate/mii_customizer/text_off` (rows show fallback
labels; most rows then show the "unknown" label); remove `menu.txt` (0.4.0 behaviour: the
character list opens directly); empty file `ui_off` (no list at all, stats keep working);
the 0.4.0 NRO `builds/0.4.0-ui/libmii_customizer.nro` (`d28aea75...`).

### What the log should show (`sd:/ultimate/mii_customizer_log.txt`, all `mc|UI|...`)

| step | lines |
|---|---|
| load | `L0|menu|state=ok|entries=24|...|rejected=0`; `sites|ui=on|sites_ok=6/6|probes_ok=48/48|installed=6` |
| 1 | `arm|entry=A|value=7|...|page=main`; `open|page=main|...|rows=24|depth=D`; `list|page=main|count=24|available=24|cursor=0|tick=-1` |
| 2 | `decide|page=main|row=1|...|action=open_entry|...|text_set>0|text_missed=0`; `page|from=main|to=entry:normal_jab|depth=D|n=1|...|equal=1|record_equal=1`; `list|...|count=87|available=1|cursor=0|tick=0|row0=nam_chr1_00_miigunner` |
| 3 | no new line while pressing A (a `decide|...|action=refused_unavailable` means the plugin's fallback refused, not the game) |
| 4 | `cancel|page=entry:normal_jab|...|greyed_fills>0`; `page|from=entry:normal_jab|to=main|...|cursor=1` |
| 5 | `decide|page=entry:normal_jab|row=0|...|action=slot_nothing_stored`; no `store`, no `SV` |
| 6 | `list|page=entry:stats|count=87|available=87|cursor=38|tick=38|...|preset=dedede`; `decide|...|preset=kirby|action=set`; `store|...|result=changed`; `SV|result=ok` |
| 7 | `decide|...|row=0|...|action=clear`; `SV|result=ok`; `list|...|cursor=0|tick=0`; then `action=set` kirby |
| 8 | ten `page` lines, all the same `depth=D`, `equal=1|record_equal=1`; `cancel|page=main`; one `exit|...|reason=leave|...|equal=1|restored=0|record_equal=1|...|depth_open=D|depth_now=D-1` |
| 9 | no `mc|UI|` line for the normal screens; `OV|id=0000f589|...|preset=kirby` |
| 10 | `LO|id=0000f589|preset=kirby`; `loadouts.txt` has `0000f589 preset kirby` |

Failure patterns: `research/P11-MENU.md` section 11.

---

## 0.4.0-ui - character list in the Mii maker - 2026-10-06 - INSTALLED AND TESTED (works, tier A; `evidence/2026-10-06_session2/RESULT.md`)

First build in which the character is chosen and saved in the game. **Nothing of the list
has run anywhere.** The plugin task stopped before its tests and report; the coordinator
reviewed the source and reran what exists (`research/P10-UI-SLICE.md`). Manifest:
`builds/0.4.0-ui/MANIFEST.json`.

| file on the card | from | bytes | sha256 |
|---|---|---|---|
| `.../skyline/plugins/libmii_customizer.nro` (REPLACES 0.3.0 `55a786b6...`) | `builds/0.4.0-ui/libmii_customizer.nro` | 81920 | `d28aea75f04f56665f11d46529abe940e527db433c169defbbaff6076117d74a` |
| `ultimate/mii_customizer/presets.txt` (REPLACES the 10-field file `f6acbba1...`) | workspace `gamedata/mii_customizer/P10-PRESET-WIDE/presets_wide.txt` | 89003 | `8c763e77ce8d8f6e...` (full hash in the manifest) |
| `ultimate/mii_customizer/list.txt` (new) | workspace `gamedata/mii_customizer/P10-PRESET-WIDE/list.txt` | 2600 | `f74048de7a825d9a...` |
| `ultimate/mii_customizer/loadouts.txt` (REPLACES the boot-2 file `f974c906...`) | `builds/0.4.0-ui/session/loadouts_session2.txt` | 157 | `f65013058dd8fd32...` |
| `ultimate/mods/mii_customizer_ui/` (2 files, new folder) | `builds/0.4.0-edit-entry/variant_marker/mii_customizer_ui/` | 11502 | `info.toml` `fb2fe26b...`; `make_mii_edit_actor.lc` `dc47a9e6...` |

Also at install: delete `ultimate/mods/mii_customizer_probe_msg/` and
`ultimate/mods/mii_customizer_probe_edit/` (the special-move sub-title returns to normal);
delete `loadouts_boot1.txt` / `loadouts_boot2.txt`; rename `ultimate/mii_customizer_log.txt`
to `mii_customizer_log_boot2.txt`. Nothing else is touched.

What each part does:
- **Plugin 0.4.0**: the stat engine of 0.3.0 plus the editor list. Way in A: Favorite on the
  Headgear row (needs the edit script below to load). Way in B: hold ZL or ZR while pressing
  A on the Headgear row (plugin only). The headgear screen then lists "None" + 87 characters;
  A on a row gives the edited Gunner that character's stats and writes `loadouts.txt`; B
  leaves without a change. The Mii's real headgear is checked and restored on exit.
- **`presets.txt` (wide)**: 94 fighters, 41 float stats each (the ten of before plus jumps,
  gravity/fall, air and ground friction, fast fall, and smaller ones; `research/P10-PRESET-WIDE.md`).
- **`list.txt`**: 87 rows, names from the game's own labels.
- **`loadouts.txt`**: Gunner B (`0000f58b`) = `fox`; Gunner A has no line.
- **Edit script (marker variant)**: adds way in A; as a load indicator the edit menu shows
  **no Try button**. If Try is there, the script did not load.

### Test (one boot, then a reboot check)

1. Boot to the main menu. Mii Fighters -> edit **Gunner A**. Look at the right column: is the
   **Try** button missing? (Either answer is fine; note it.)
2. Move to **Headgear**, press **Favorite** (the button that normally toggles the favourite
   mark). If the headgear screen opens with character names: way in A works. If it only
   toggles the favourite mark: back on Headgear, **hold ZL (or ZR) and press A**.
3. In the list: scroll down a few pages and back, press the sort button once, then press **B**.
   You should be back in the edit menu, the Mii's hat unchanged.
4. Open the list again, choose **Kirby**, press A. Check the Mii still wears its own hat.
5. Open the **normal** Headgear screen (A on Headgear, nothing held): it must be the usual
   hat list, same hats, same cursor. Do not change the hat. Open Outfit once and leave.
6. Leave the editor (save if it asks). Smash, 2 players: **P1 = Gunner A, P2 = Gunner B**,
   Final Destination. A should feel like Kirby (light, floaty, low gravity), B like Fox.
7. Back in the editor: open the list for Gunner A again - the cursor/tick should be on Kirby.
   Choose the first row (**None**). One more match: A is a normal Gunner again.
8. Close the game, start it again, one match A vs B: A normal, B Fox (the saved file).
9. Close the game and report, including any step where something looked wrong.

If the game crashes or hangs: note the step and what was on screen, do not retry, report.
Rollback: the 0.3.0 NRO (`builds/0.3.0-presets/`, `55a786b6...`); or, to keep the wide
presets and switch only the list off, an empty file `ultimate/mii_customizer/ui_off`.

### What the log should show (`sd:/ultimate/mii_customizer_log.txt`)

| claim | lines |
|---|---|
| files loaded | `L0 ... presets ... presets=94 hashes=41 rejected=0`; `L0 ... loadout ... origin=main state=ok`; `L0 ... list ... state=ok ... entries=87` |
| list hooks in | 5 `ui_site` and 15 `ui_probe` lines `match=1`; `UI|sites|ui=on|...|installed=5` |
| way in | `UI|arm|entry=A` or `entry=B`, then `UI|open|...|rows=88`, `UI|list|count=88` |
| cancel | `UI|cancel`, `UI|exit|...|equal=1|restored=0|record_equal=1` |
| choice | `UI|decide|row=..|...|preset=kirby|action=set`, `UI|exit ... equal=1`, `UI|store|...|result=added`, `SV|result=ok|step=0` |
| applied without reboot | `OV` lines `id=0000f589 ... preset=kirby` after the choice |
| cleared | `UI|decide|row=0|...|action=clear`, `SV|result=ok` |
| after reboot | `LO` lines: only `id=0000f58b preset=fox` |

---


## 0.3.0-presets + loader probes - character stat presets per saved Mii - 2026-10-05 - INSTALLED AND TESTED (boots 1 and 2 ran; presets work, tier A)

Boot 1 ran on 2026-10-05: the per-Mii stat preset works on the console (tier A) and the
different-length Lua chunk loads; the added message label did not resolve and the Favorite
edit-menu probe showed no visible change. Full record: `evidence/2026-10-05_session1/RESULT.md`
(+ `log_boot1.txt`). Boot 2 (loadout swap, ARCropolis logging raised) is prepared below and
needs the card mounted and a go-ahead in the current conversation.

The offline checks passed and were rerun by the coordinator on 2026-10-05 (host tests 47/47,
mutation control 61/61, binary/source 98/98, preset file 8/8, build hash reproduced; probe
manifests verified). After boot 1, new offline evidence: the card's ARCropolis is an
older-generation build (`libarcropolis.nro` strings: `arcropolis::fs::loaders`, Orbits; no
v4.1.x `modfs` markers), consistent with v4.0.7/v4.0.8. The coordinator copies files only when
the card is mounted and the user asks in the current conversation.

Package sources: plugin `builds/0.3.0-presets/`, preset file workspace
`gamedata/mii_customizer/P6-PRESET-DATA/presets.txt`, session loadout files
`builds/0.3.0-presets/session/`, probes `builds/0.2.1-msg-probe/` and
`builds/0.3.1-edit-probe/`. Reports: `research/P7-PRESET-ENGINE.md`,
`research/P9-EDIT-SOURCE.md`, `research/P5-MSG-PROBE.md`.

| file on the card | from | bytes | sha256 |
|---|---|---|---|
| `atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmii_customizer.nro` (REPLACES 0.2.0-override `4477dc9a...`) | `builds/0.3.0-presets/libmii_customizer.nro` | 65536 | `55a786b63681935d709e7f4375ccf951dbe279a938d8bf731019a7541ac800dc` |
| `ultimate/mii_customizer/presets.txt` (new file) | `gamedata/mii_customizer/P6-PRESET-DATA/presets.txt` | 25517 | `f6acbba17d510aae0f0a2cc49cc5417287d4f0d0a8428dbf52d3ca4505865c0d` |
| `ultimate/mii_customizer/loadouts.txt` (REPLACES the v1 gate-2 file `4c2ae058...`) | `builds/0.3.0-presets/session/loadouts_boot1.txt` | 34 | `38b7466199687a8df1fc89559e6bb791d4d75916772830575f02b24786be9a2e` |
| `ultimate/mii_customizer/loadouts_boot2.txt` (new file, used after boot 1) | `builds/0.3.0-presets/session/loadouts_boot2.txt` | 78 | `f974c906bd31a357de1cc12c9e7bf31ca233e20fb2b2a8e0355545c877b710f0` |
| `ultimate/mods/mii_customizer_probe_msg/` (3 files, new folder) | `builds/0.2.1-msg-probe/mii_customizer_probe_msg/` | 9366 | `info.toml` `e50d337a...`; `msg_menu.xmsbt` `9726ae82...`; `make_mii_special_actor.lc` `2ff0182c...` |
| `ultimate/mods/mii_customizer_probe_edit/` (2 files, new folder) | `builds/0.3.1-edit-probe/mii_customizer_probe_edit/` | 11365 | `info.toml` `138837b4...`; `make_mii_edit_actor.lc` `41ce713e...` |

The full probe hashes above are in each package's `MANIFEST.json`; re-hash both folders just
before copying. Before installing, check that `ultimate/mods/mii_customizer_probe_lua/` and
`ultimate/mods/mii_customizer_probe_layout/` are absent (they were removed with gate 2) and
that no other folder ships `make_mii_special_actor.lc` or `make_mii_edit_actor.lc`. Delete
`ultimate/mii_customizer_log.txt` if present. Nothing else on the card is touched; the
framework plugins and `ultimate/mods/pyra_gamewatch_reskin` stay as they are.

What each part does:
- **Plugin 0.3.0** (`research/P7-PRESET-ENGINE.md`): a saved Mii Gunner (kind 74, saved ID
  non-zero) gets, for each of the ten field hashes in `presets.txt`, the value of the preset
  its ID names in `loadouts.txt`; explicit `weight` / `walk_speed_max` lines win over the
  preset. Everything else returns the game value. It reads both files once at load, writes
  only its log. Known risk: the NRO imports three `nn::fs` functions 0.2.0 did not
  (`DeleteFile`, `RenameFile`, `RenameDirectory`, pulled in by the compiled-in but never
  called `save_loadouts`). If the runtime cannot resolve them, the plugin does not load and
the log has no `mc|` lines; it does not change anything else.
- **`presets.txt`**: 94 fighters, the ten movement stats of each, generated from the user's own
  param file (`tools/stat-presets/`, P6-PRESET-DATA).
- **`loadouts.txt` boot 1**: Gunner A (`0000f589`) uses preset `fox` (fast, light, falls hard).
  Gunner B has no line and stays vanilla.
- **`loadouts_boot2.txt`**: Gunner A uses `purin` (slow, floaty, low jump) plus an explicit
  `weight 130.0`; Gunner B uses `fox`. Boot 2 is the explicit-beats-preset and second-preset
  check.
- **Message probe** (`research/P5-MSG-PROBE.md`): adds one new label `mnu_mc_probe_title` =
  "MC probe 0.2.1" and ships the special-move chunk at 7788 bytes instead of 7799. It answers
  whether a brand-new message label merges and whether a different-length Lua chunk loads.
- **Edit probe** (`research/P9-EDIT-SOURCE.md`): ships the edit-menu chunk at 10739 bytes
  instead of 10576 (a different length again). While the Headgear row is selected, one press
  of the **Favorite** button makes the script behave exactly as if that row had been decided.

### Session (one install; boot 1, a card swap, boot 2)

Boot 1
1. Boot the game to the main menu (all files above installed, boot-1 loadout in place).
2. **Match 1.** P1 = Gunner A (0000f589), P2 = Gunner B. 2 players, stock, no items, Final
   Destination, hazards off. Ground: stand both together, walk both the same way, then dash
   and run across the stage, each twice. Air: both full-hop together and do nothing; both
   full-hop holding toward each other; one running jump each; one double jump each. Then B
   grabs A and up-throws, and A grabs B and up-throws (near 0 %). Quit.
3. **Match 2, ports swapped.** P1 = Gunner B, P2 = Gunner A. Run once, full-hop once. Quit.
4. **Match 3, control.** P1 = Mario, P2 = Kirby. Run and full-hop, ~20 seconds. Quit.
5. **Edit probe check.** Mii Fighters -> edit Gunner A. With the **Headgear** row selected
   (row 1), press **Favorite** once: the headgear selection screen should open, exactly as if
   you had pressed the normal decide button on that row. Control: press Favorite while another
   row is selected (for example Outfit) — it should do whatever it normally does and nothing
   else. Leave the editor without changing anything.
6. **Message probe check.** On Gunner A's **special-move screen**, read the sub-title: it
   should say `MC probe 0.2.1`. If it shows the raw key `mnu_mc_probe_title` or is blank, the
   chunk loaded but the label did not resolve; if it shows `Select Special Moves`, the chunk
   did not load. Move the cursor over the rows, leave without changing anything.
7. Close the game. Leave the log on the card and tell the coordinator boot 1 is done.

The coordinator then swaps the loadout file and deletes the log (card mounted, at the user's
request); or the user renames `loadouts.txt` -> `loadouts_boot1.txt` and `loadouts_boot2.txt`
-> `loadouts.txt` and deletes the log, then boots again.

Boot 2
8. **Match 4.** P1 = Gunner A, P2 = Gunner B. Repeat step 2 completely.
9. **Match 5, control.** P1 = Mario, P2 = Gunner B. Run and full-hop both, ~20 s. Quit.
10. Close the game. Read (or hand over) both logs.

### What the logs should show (P7 report section 5.4; log at `sd:/ultimate/mii_customizer_log.txt`)

| claim | lines |
|---|---|
| plugin and files loaded | `L0` lines with `0.3.0-presets loaded`, `accepted_kinds=74`, `presets\|...\|state=ok\|presets=94\|hashes=10\|rejected=0`, `loadout\|...\|state=ok\|version=2`, `site=0x4e53e0 ... match=1`, `installed=1` |
| A got preset `fox`, B nothing (boot 1) | one `LO` line `id=0000f589\|preset=fox\|...`; no `LO` for `0000f58b` |
| which fields the engine asks through the hook | `F5` line before the control match: each hash's first number; `RQ` lines record the first request |
| the override applied | `L3` lines with `id=0000f589\|ov=1\|src=preset` and `OV` lines `id=0000f589\|h=...\|src=preset\|preset=fox` |
| B and non-Mii untouched | `L3` with `id=0000f58b` all `ov=0\|st=noent`; non-Mii lines `st=kind`; Mario/Kirby normal |
| follows the saved Mii, not the port | match 2 `L3` lines `id=0000f589` have `p=1` and `ov=1` |
| boot 2 explicit line wins | `L3` for `weight` (`h=0x0607cd5541`) `id=0000f589` shows `v=130.0000\|src=explicit` while the other nine fields are `src=preset\|preset=purin`; B is `src=preset\|preset=fox` |
| nothing broke | last `L5`: `dropped=0`, `orig_null=0`, no `reent`, no `gfull`; no `X2` line unless the engine requested a known hash with `x2 != 0` |

Expected in play (D until seen): boot 1 A walks and runs clearly faster than B, falls faster,
flies higher from throws. Boot 2 A floats and jumps low, is slower on the ground, and is thrown
less high (explicit 130 beats `fox`'s 77); B moves like boot-1 A. Mario and Kirby normal. The
ten copied stats are only movement values: special moves, double-jump height and other
non-listed stats stay the Gunner's.

If the game crashes or hangs: note the step. Attribution: (1) remove the two probe folders and
retry — matches do not touch them, so a boot crash with them present is most likely the plugin;
(2) if it still fails, restore the 0.2.0-override NRO (`builds/0.2.0-override/libmii_customizer.nro`,
`4477dc9a...`) and the v1 loadout file, and report. Do not leave a half-copied plugin on the card.

Rollback: 0.2.0 NRO back; `presets.txt` deleted; `loadouts.txt` back to the gate-2 v1 file;
`loadouts_boot2.txt` deleted; both probe folders deleted. 0.3.0 writes nothing but its log.

### Installation record

Installed 2026-10-05 by the coordinator at the user's request in chat (card mounted, "card is
already in"). Before: `libmii_customizer.nro` was 0.2.0-override (`4477dc9a...`, checked before
replacing); `ultimate/mii_customizer/loadouts.txt` was the gate-2 v1 file (`4c2ae058...`,
538 bytes); `ultimate/mods/` held only `pyra_gamewatch_reskin`; the two old probe folders were
absent. Renamed `ultimate/mii_customizer_log.txt` (gate-2 log `96d89990...`, identical copy
already in `evidence/2026-10-05_gate2/log_boot1.txt`) to `mii_customizer_log_gate2.txt`.

| file on the card | after hash |
|---|---|
| `.../skyline/plugins/libmii_customizer.nro` (0.3.0) | `55a786b6...` |
| `ultimate/mii_customizer/presets.txt` | `f6acbba1...` |
| `ultimate/mii_customizer/loadouts.txt` (boot 1) | `38b74661...` |
| `ultimate/mii_customizer/loadouts_boot2.txt` | `f974c906...` |
| `ultimate/mods/mii_customizer_probe_msg/` (3 files) | `e50d337a` / `9726ae82` / `2ff0182c` |
| `ultimate/mods/mii_customizer_probe_edit/` (2 files) | `138837b4` / `41ce713e` |

The six other plugins hashed identically before and after (arc_network `c7644991`, arcropolis
`49b6f634`, nro_hook `ca7aec03`, one_slot_eff `e6e5659d`, pyra_gamewatch_reskin `424914c1`,
smashline `5f4091ee`). `pyra_gamewatch_reskin` ships no `chara_make` script and its message
file is `msg_name.xmsbt`, so neither probe conflicts with it.

Boot 1 ran on 2026-10-05. Result: `evidence/2026-10-05_session1/RESULT.md` (tier A). Card state
after boot 1 (checked while mounted): `ultimate/mii_customizer/loadouts.txt` still the boot-1
file `38b74661...`, `loadouts_boot2.txt` `f974c906...` and `presets.txt` `f6acbba1...` untouched
by the game; `ultimate/mii_customizer_log.txt` holds the boot-1 log (copy already in the
evidence folder); `ultimate/arcropolis/logs/` is empty (logging_level `Warn`); the
`mod_cache`/`presets` config files were rewritten by the game during the boot (16:19) and still
list the two probe folders and `pyra_gamewatch_reskin`.

### Boot 2 - RAN 2026-10-05 (result: `evidence/2026-10-05_session1/RESULT_boot2.md`)

Result (tier A): explicit `weight 130.0` beat preset `purin` for `0000f589`, the other nine
fields came from `purin`; `0000f58b` got `fox`; Mario on player index 1 with Gunner B's stale ID
in the slot was left alone (`st=kind`); counters clean. ARCropolis wrote no log at `Debug`.
Card state after boot 2 (checked while mounted, 2026-10-05): `loadouts.txt` still the boot-2
file `f974c906...`; new `ultimate/mii_customizer_log.txt` `06083fd7...` (23229 B, copied to
`evidence/2026-10-05_session1/log_boot2.txt`, left on the card); `logging_level` restored to
`Warn` by the coordinator (`8448814d...`, equal to the backup); the seven plugins hash as
before; both probe folders still present (the special-move sub-title shows the raw key
`mnu_mc_probe_title` until they are removed with the next install).

Applied before the boot, at the user's go-ahead with the card mounted (chat, 2026-10-05):

| change | detail | verified after |
|---|---|---|
| loadout swap | `loadouts.txt` (boot 1, `38b74661...`) renamed to `loadouts_boot1.txt`; `loadouts_boot2.txt` (`f974c906...`) copied to `loadouts.txt` | `loadouts.txt` `f974c906...` (78 B); `loadouts_boot1.txt` `38b74661...`; `loadouts_boot2.txt` and `presets.txt` unchanged |
| boot-1 log kept | `ultimate/mii_customizer_log.txt` renamed to `mii_customizer_log_boot1.txt` | on-card copy sha256 `75b68a93...` equal to `evidence/2026-10-05_session1/log_boot1.txt` |
| logging raised | ARCropolis `logging_level`: `Warn` -> `Debug`; old 4-byte value backed up as `evidence/2026-10-05_session1/logging_level_before_boot2.txt` (`8448814d...`); new file 5 bytes, `1a03bd2f...` | readback shows `Debug` |

If the ARCropolis log turns out missing or noisy, restore the old value by writing `Warn` back
into `ultimate/arcropolis/config/1152970916651726665/14749781827137943432/logging_level`.

Boot-2 game steps (user):

1. Boot to the main menu, then one match: **P1 = Gunner A** (`0000f589`, now `purin` + explicit
   `weight 130.0`), **P2 = Gunner B** (now `fox`). Walk, run, full-hop; B grabs A and up-throws,
   then A grabs B and up-throws near 0 %. Quit.
2. Control match: **P1 = Mario, P2 = Gunner B**; run and full-hop, ~20 s. Quit.
3. Open Gunner A's special-move screen once and read the sub-title (raw key expected again).
   Optional: open the edit menu once so the log sees it; the Favorite press behaviour is already
   reported (it toggled favourite as usual) - no need to repeat it.
4. Close the game; leave the card as is and report back. The coordinator reads the new
   `ultimate/mii_customizer_log.txt` and the ARCropolis log, if one appeared under
   `ultimate/arcropolis/logs/`.

Expected if it works: A floats, jumps low, is slow on the ground, and is thrown less high than
B (explicit 130 beats fox's 77); B feels like boot-1 A; Mario normal. Log: A's ten fields
`src=preset|preset=purin` except `weight` `src=explicit`; B `src=preset|preset=fox`.

---

## 0.2.0-override - per-saved-Mii weight / walk speed - 2026-10-05 - INSTALLED AND TESTED 2026-10-05 (works; `evidence/2026-10-05_gate2/RESULT.md`)

First build that changes behaviour. Never run in the game. Package: `builds/0.2.0-override/`
(`MANIFEST.json`; report `research/P4-OVERRIDE-SLICE.md`).

| file on the card | from | bytes | sha256 |
|---|---|---|---|
| `atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmii_customizer.nro` (REPLACES 0.1.0-diag `ae49c1c8...`) | `builds/0.2.0-override/libmii_customizer.nro` | 53248 | `4477dc9acdbef341638a89174df5f2b8946125e0cfa24f10358cc8ad4abf59c9` |
| `ultimate/mii_customizer/loadouts.txt` (new folder and file) | `builds/0.2.0-override/example/loadouts.txt` | - | `4c2ae058267ea4fb2147b54d9408cae79e09b41d2b8ee4486e6f8583bbbe3ea1` |

Also at install: remove the two gate-1 probe folders `ultimate/mods/mii_customizer_probe_layout/`
and `ultimate/mods/mii_customizer_probe_lua/` (the Mii special-move screen returns to normal),
and move the old `ultimate/mii_customizer_log.txt` aside so the new log starts clean.
Not touched: every other plugin, `ultimate/mods/pyra_gamewatch_reskin`, save data.

What it does: for a fighter that the game itself reports as a Mii Gunner on player index p, if the
saved-Mii ID in slot p has a line in `loadouts.txt`, requests for `weight` / `walk_speed_max`
return the value from the file. Everything else returns the game value. The example file gives
Gunner A (ID 0000f589) weight 130 and walk speed 1.6; Gunner B (0000f58b) has no line and stays
vanilla. One extra log-only hook records when the engine applies special-move choices.

Offline checks observed by the coordinator on 2026-10-05: image facts 35/35, binary and source
69/69, host unit tests 25/25, NRO and example hashes equal the report. Not repeated: the build and
the mutation control (worker: 17/17). Accepted deviation: the object id of the fighter is read
from the struct field the binding declares and then confirmed through an exported game function.

Risks: the identity lookup calls six game functions from inside the param hook; if one of them
misbehaves a match could crash on load. A wrong assumption gives vanilla behaviour, not a wrong
fighter, as far as the code and its tests show. Value ranges are test proposals, not known safe.

### Test (one boot; rules: 2 players, stock, no items, Final Destination)

1. Boot to the main menu.
2. Control: P1 Mario, P2 Kirby (not characters of the existing mod). Walk both (stick tilted, not
   dashing) 10 seconds, one grab + up throw each way, quit.
3. Match 1: P1 = Gunner A, P2 = Gunner B. Walk both side by side in the same direction, twice.
4. Same match: at 0 % B grabs A and up-throws (no pummel), then A grabs B and up-throws. Watch
   how high each goes. Trade hits to about 80 % each and repeat both throws.
5. Quit. Note who walked faster and who flew higher.
6. Match 2, ports swapped: P1 = Gunner B, P2 = Gunner A. Repeat steps 3-4. Quit.
7. One minute: P1 = Mario, P2 = Gunner B. Walk both, quit.
8. Close the game, mount the card, report.

Expected if it works (D until seen): Gunner A walks clearly faster than B on either port and goes
less high from the up throw; B, Mario and Kirby are normal. Dash and run are unchanged.
If it crashes: note the step; the coordinator then runs the no-file control (same plugin, file
renamed) to separate the identity lookup from the hook itself.

Log reading: `research/P4-OVERRIDE-SLICE.md` sections 4.3 and 4.4.
Rollback: put back `builds/0.1.0-diag/libmii_customizer.nro` or delete the NRO; delete
`ultimate/mii_customizer/`.

### Installation record

Installed 2026-10-05 by the coordinator at the user request in chat (card mounted, "you can
install"). Replaced `libmii_customizer.nro` 0.1.0-diag (`ae49c1c8...`, checked before replacing)
with 0.2.0-override; card copy re-hashed `4477dc9acdbef341...`. Created
`ultimate/mii_customizer/loadouts.txt` (`4c2ae058267ea4fb...`). Removed the two probe folders
(each held exactly its 2 known files). Renamed the old log on the card to
`ultimate/mii_customizer_log_gate1.txt` (copy kept as
`evidence/2026-10-04_gate1/card_log_before_gate2.txt`). The six other plugins hash the same before
and after; `ultimate/mods/` holds only `pyra_gamewatch_reskin`.
Test run by the user on 2026-10-05: no crash, override visible in play; the user played four
Gunner-only matches instead of the listed steps (see RESULT.md for what the log covers).

---

## 0.1.0-gate1 - first console diagnostic gate - 2026-10-04 - INSTALLED AND TESTED (both tests passed)

Diagnostic only. It adds no feature. The user installs and runs it; no agent touches the card.
Nothing in this package has been loaded by the game or an emulator. "READY" means: a concrete
package exists, its hashes are recorded and the offline checks passed. It says nothing about
behaviour in the game.

### Package

`builds/0.1.0-gate1/` (manifest `MANIFEST.json`, check `check_gate1.py`: 5 files, 0 problems).
Folders mirror the SD card root.

| step folder | file on the card | bytes | sha256 |
|---|---|---|---|
| `step1_plugin/` | `atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmii_customizer.nro` | 45056 | `ae49c1c84da39cf454f41811c75ed5e22cde21cfd63a9b530b592b15ee8c96af` |
| `step2_probes/` | `ultimate/mods/mii_customizer_probe_layout/info.toml` | 304 | `ad88837b61f6eef9352fa5087fdec84e6ea7eda1b73b3290d0636a53ba75cc8a` |
| `step2_probes/` | `ultimate/mods/mii_customizer_probe_layout/ui/layout/menu/make_mii_special/make_mii_special/layout.arc` | 723436 | `86044f63d4bb4456d906c8d896a4c53ed80c20a298f97bb528fffc3708f55877` |
| `step2_probes/` | `ultimate/mods/mii_customizer_probe_lua/info.toml` | 309 | `363c4c5f6e5f04376d4dd6b02978cbee319802aba57c08ff067b9f363987afb9` |
| `step2_probes/` | `ultimate/mods/mii_customizer_probe_lua/ui/script/menu/chara_make/make_mii_special_actor.lc` | 7799 | `0ad3f815620f5990f3d74f53fbd0b974de0d25846d21c7da018f2fee526e8da2` |

All five are NEW paths on the card. Nothing existing is replaced. If a copy tool asks to
overwrite a file, stop and report it.

What each part does:
- Plugin 0.1.0-diag (`research/P3-DIAG-PLUGIN.md`): three hooks that call the original game
  function unchanged and write lines to `sd:/ultimate/mii_customizer_log.txt`. A hook is only
  installed if the four instruction words at its address match the 13.0.4 image; otherwise it is
  skipped and the log says so.
- Layout probe (`research/P2-LAYOUT-PATCH.md`): first row of the Mii special-move screen scaled to
  75 %. Two bytes differ from the original file.
- Lua probe (`research/P3-ARC-PROBES.md`): the sub-title of that screen uses the side-special
  label instead of the screen title. Four bytes differ from the original file. In the extracted
  default-language message file the two texts are "Select Special Moves" and "Side Special"
  (coordinator read `ui/message/msg_menu.msbt`, labels 1045 and 1048); other languages not read.

Dependencies: Skyline and ARCropolis as already on the card. No smashline dependency. The
existing mod and the framework plugins are not touched.
Possible conflict: another plugin hooking the same three addresses (0x4e53e0, 0x179e440,
0x17c8210). Not checked against the plugins on the card; the load-time word check covers it.

Offline checks observed by the coordinator on 2026-10-04: plugin step 0 36/36, binary and source
check 37/37, NRO hash equals its manifest; probe check 4 files 0 mismatches (after the coordinator
fixed a missing closing quote in the Lua probe's `info.toml` and regenerated that manifest);
gate package check 5 files 0 problems. Not repeated by the coordinator: the plugin build itself
and the host unit tests (worker reports 12/12).

Known risks, stated plainly: the hooks have never run. A crash at boot or when a match loads is
possible. The Skyline runtime on the card was not compared with the copy the hook analysis used.
The layout or Lua file could make the Mii special-move screen misbehave; that is why they are a
separate step.

### Decisions that depend on this test, and why offline work cannot settle them

1. Is each player's saved-Mii ID in the static slot when a match starts (so the mod can look up a
   per-Mii loadout by player)? Offline work found the slots and their writers, not their timing.
2. Do weight / walk-speed requests go through the hooked function, per fighter object and
   repeatedly (so a per-Gunner stat override is possible there)?
3. Are file offsets of the 13.0.4 image the offsets the hook API uses on the console?
4. Does the game load a changed editor layout and a changed editor Lua file through ARCropolis?
   Every UI change in this project depends on that.

### Before installing (vanilla state, a few minutes)

P0. Have two saved Mii Gunners: **A** with the FIRST option in all four special slots, **B** with
    the THIRD option in all four. Create or edit them now if needed, and save.

### Test 1 - plugin only (first boot)

1. Copy the contents of `builds/0.1.0-gate1/step1_plugin/` to the card root (one file). If
   `ultimate/mii_customizer_log.txt` exists on the card, delete it.
2. Boot the game to the main menu.
3. Control match: Smash, 2 players, two non-Mii fighters of clearly different weight (for example
   Mario as P1, Kirby as P2). Walk both left and right about 10 seconds, one hit, quit the match.
4. Match with P1 = Gunner A, P2 = Gunner B. Walk both, one hit, about 20 seconds, quit.
5. Leave Smash. Open the Mii Fighters menu, open Gunner A for editing, enter the special-move
   screen, leave it without changing anything, go back to the main menu.
6. Repeat step 4 with the same assignment (A = P1, B = P2).
7. Close the game normally.
8. Copy `ultimate/mii_customizer_log.txt` from the card to
   `mods/mii_customizer/evidence/2026-10-04_gate1/test1_log.txt` (create the folder).

If the game crashes or freezes: note at which step, copy the log anyway, copy the newest file from
`atmosphere/crash_reports/`, and remove the NRO before the next boot.

### Test 2 - file probes (second boot, only if test 1 booted and played normally)

9.  Copy the contents of `builds/0.1.0-gate1/step2_probes/` to the card root (two mod folders
    under `ultimate/mods/`). If ARCropolis shows a mod list, make sure both
    "Mii Customizer probe" entries are enabled.
10. Boot, open the Mii Fighters menu, open Gunner A for editing, enter the special-move screen.
11. Look at two things and take a photo or screenshot:
    a) the sub-title of the screen: normal screen title, or the side-special label
       (English: "Select Special Moves" versus "Side Special");
    b) the FIRST special row compared with the other three: same size, or visibly smaller.
12. Move the cursor over all four rows, open one row's option list, back out, then leave the
    screen without changing anything. Note anything that behaves differently from normal.
13. Close the game. Copy the log again as `test2_log.txt` in the same evidence folder.

### What to send back

The two log files, which Gunner was P1 in each match, the photo and the two observations from
step 11, anything odd from step 12, and the step number plus crash report if anything crashed.

### Reading the result (short form; full tables in `research/P3-DIAG-PLUGIN.md` section 3.2)

| observation | meaning |
|---|---|
| L0 lines: three sites `match=1`, `installed=1` | offset convention confirmed on the console |
| L4 during the Gunner match: players 0 and 1 show two different non-zero IDs with special bytes `00000000` and `02020202` on the expected sides | ID slots are valid at fighter creation; a static read by player index is enough |
| IDs swapped, zero, or stale | the slot is not a reliable match-time source; L1/L2 return addresses say where to look next |
| L3 lines with weights matching the two control fighters on different `parent` values, counts growing during the match | this is the per-fighter float-param getter and it is read repeatedly; an override there is viable |
| no L3 lines although the param hook is installed | requests for these two values take another path |
| sub-title shows the side-special label | the game loads our changed Lua chunk |
| first row smaller | the game loads our changed layout, and row scale survives the entry animation |
| sub-title changed but row unchanged (or the reverse) | file loading works for one type; for the unchanged one, "not loaded" and "loaded but no visible effect" are not yet separated |
| neither changed | overrides not picked up, or both effects invisible; next step is checking the ARCropolis mod list / log, not more guessing |

### Rollback

Delete from the card: `atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmii_customizer.nro`,
`ultimate/mods/mii_customizer_probe_layout/`, `ultimate/mods/mii_customizer_probe_lua/`, and
`ultimate/mii_customizer_log.txt`. The package changes no save data and no existing file.

### Installation record

2026-10-04, step 1 installed by the coordinator at the user's explicit request in chat (the card
was mounted as a removable volume labelled SWITCH SD). Copied one new file,
`atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libmii_customizer.nro`; card copy
re-hashed `ae49c1c84da39cf454f41811c75ed5e22cde21cfd63a9b530b592b15ee8c96af`, 45056 bytes, equal
to the package. Target did not exist before; nothing was overwritten. The six other plugins
(arcropolis, nro_hook, smashline `5f4091ee...`, arc_network, pyra_gamewatch_reskin `424914c1...`,
one_slot_eff) hashed identically before and after. `ultimate/mods/` still holds only
`pyra_gamewatch_reskin`; the existing mod stays installed and active during the test. No old
`ultimate/mii_customizer_log.txt` was present.
Card Skyline runtime `exefs/subsdk9`: 47456 bytes, sha256 `d3630815ee02...`, NOT the lab copy
(`9959ecb1...`) that the hook analysis read. Coordinator decompressed the card copy (read-only,
to `builds/.cache/skyline_subsdk9_card_flat.bin`) and compared `A64HookFunction` (0x43fc on the
card, 0x43d8 lab, both 0x128 bytes) and `A64HookFunctionV` instruction by instruction: only
relative call targets and one data-slot displacement differ (6 and 10 instructions), no
difference in logic. So the 4-word patch form applies to the card's runtime as well (offline B).
Test 1 ran on 2026-10-04 without crash; result `evidence/2026-10-04_gate1/RESULT.md` (tier A):
offset convention, per-fighter repeated param requests and per-player saved-Mii ID slots confirmed.
Step 2 installed by the coordinator afterwards, same day, under the same user request: copied
`ultimate/mods/mii_customizer_probe_layout/` and `ultimate/mods/mii_customizer_probe_lua/` (4 files,
all re-hashed equal to the package; neither folder existed before). `ultimate/mods/` now holds
`pyra_gamewatch_reskin` plus the two probes. The plugin stays installed. The test-1 log was left
on the card (a removal was blocked by the tool's path protection), so test 2 appends to it; the
second boot starts again at `seq=0`. ARCropolis may need the two new mods enabled in its mod list.
Because the existing mod is active, test 1's control match and Gunner matches must not use the
characters that mod changes.
Test 2 ran on 2026-10-04: both probes visible, no crash (`evidence/2026-10-04_gate1/RESULT_test2.md`).
Card state after gate 1: plugin 0.1.0-diag and both probe folders still installed. The probes are
cosmetic leftovers and are to be removed with the next install (or earlier on request).

### 0.4.0-ui - installation record

Installed 2026-10-06 by the coordinator at the user's go-ahead in chat (card mounted).
Before: plugin 0.3.0 `55a786b6...`, boot-2 `loadouts.txt`, 10-field `presets.txt`, both probe
folders. Done: boot-2 log renamed `mii_customizer_log_boot2.txt`; NRO, `presets.txt`,
`list.txt`, `loadouts.txt` copied; `loadouts_boot1/2.txt` and both probe folders deleted;
`mods/mii_customizer_ui/` (marker variant) copied. Re-hashed on the card: NRO `d28aea75...`,
`presets.txt` `8c763e77...`, `list.txt` `f74048de...`, `loadouts.txt` `f6501305...`, script
`dc47a9e6...`, `info.toml` `fb2fe26b...`, all equal to the package. The other six plugins hash
as before; `pyra_gamewatch_reskin` untouched. Waiting for the user's boot.

Boot ran 2026-10-06 (tier A, `evidence/2026-10-06_session2/RESULT.md`): way in A works (the
edit chunk loads), 88 rows on the native list, cancel and decide correct, two saves
`result=ok`, headgear and working record equal on all four exits, no crash. Card state after
the boot (checked while mounted): `loadouts.txt` written by the plugin (`0000f58b preset fox`,
`0000f589 preset dedede`, 57 bytes); the log left in place (copy in the evidence folder); the
marker variant of the edit script is still installed, so the edit menu has no Try button
until the next install.
