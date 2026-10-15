# Collective install queue

## Pikachu back air on eflame c06/c07 — 1.0.0 — 2026-10-03 — READY, NOT installed

Task: give Pyra/Mythra-as-Game-&-Watch (`eflame`) Pikachu's `AttackAirB` **and** its `LandingAirB`, gated to the two modded costumes only. Package `builds/pgwr/pikachu-airb-1.0.0/`; **narrow delta of 19 files**, not a replacement tree; delta tree `db80bba18a1b6cb21593c033a1f39442320b46a87b2f77b5bd43f3003c8f2866`. NRO `9d0ee7edb554d402cf31ff12dce989319804b65fece8b9cae3787e4cc3eddcee` (524288 B), reproducible twice from the same source. Isolated source `builds/.cache/pikachu-airb/plugin`, copied from the 0.20.23 snapshot so no other agent's live edit was compiled.

**Install shape.** Overlay the 19 files under `ultimate/mods/pyra_gamewatch_reskin/`, apply `patches/acmd_mod_rs.patch` and `patches/acmd_pikachu_attack_air_b_rs.patch` to the plugin source, rebuild with
`cargo skyline build --release --features snake-neutral-b,hero-side-b,hero-mana-hud -- --offline`, take the NRO from `atmosphere/`. Do **not** copy a whole bank over one another task changed: the two `se` and two `vc` banks here are a semantic merge onto the 0.20.23 banks, so if your candidate changed them, re-run `tools/merge_pikachu_airb_sound.py --baseline <your candidate>` instead.

**What it changes.** `c05attackairb.nuanmb` and `c05landingairb.nuanmb` retargeted onto the c06/c07 skeleton, per slot; `motion_list.bin` per slot, where `attack_air_b` moves **two bytes** (cancel 296 -> 300, flags `0x0080` -> `0x0084`) and `landing_air_b` moves **zero** because the recipient entry is already byte-identical to the donor's; eight handlers registered at `Priority::High`; six tones appended (561 se / 250 vc retained per slot); one `seq_pikachu_rnd_attack` record appended to `eflame.sqb`.

**What it deliberately does not change.** No `config.json` (the clip name is already correct on both sides), no `param/`, no `effect/` (`sys_spin_wind`, `sys_attack_impact`, `sys_down_smoke` are common-bank names, so no donor emitter is merged), no `ui/`, no other motion entry, clip, bank or file. **No status id**: both kinds are vanilla `AttackAirB` / `LandingAirB` states. No hook, no raw offset, no framework plugin, `logging` still OFF.

**Behaviour the user will notice.** The G&W turtle article no longer appears on this move, because the donor has none. The landing's hitbox, rumble and slope behaviour are Pikachu's, not G&W's.

**Blockers / open items.** `landing_attack_air_frame_b` stays at G&W's `18.0` (`params.rs` hash `0x1a4262b54f`): Pikachu's own value is not reachable offline, so no number was invented. Measure on hardware if the landing feels late.

**Verified (tier B, offline).** Donor pins re-checked on every run; retarget gates (45/55 Transform nodes kept, 10 dropped, **0 parent-chain mismatches**, 98 visibility nodes rebuilt from the recipient's own idle, all 17 tracked limbs measurably move); motion-list two-byte delta; bank preservation and sequence uniqueness; clean `cargo skyline build` with no new warnings; a control build of the **unmodified** snapshot reproduces the baseline NRO `424914c18e74...` byte for byte, so the shipped NRO differs only because of this task; `tools/audit_pikachu_airb_delta.py` 128/128 checks with **8 negative controls caught** and a positive control. **Not verified (tier D):** that the animation looks right, that the hitboxes connect, or that the sounds play. No install, no emulator run, no console, no commit, no branch, no push.

**Manual tests, one change at a time (rule 11), on c06 and c07:** vanilla c00/c05 as controls (this move must be untouched there). Back air from neutral and after a short hop - five jab hits then one hard finisher; confirm the hitbox tracks the visible arm, the finisher launches, and it ends in Pikachu's landing. Check the landing on a platform, on a slope and off the stage edge; the G&W turtle must **not** appear. Check the spin-wind effects on frames 2/3/12/13 and the impact effect on 24, the swing sound on 20 and the voice on the first hits. Confirm the other normals, the sword, side-B, up-B and the mana HUD are unchanged. Boot log must show no new lines.

Evidence and full check list: `evidence/2026-10-03_pgwr_pikachu_airb/RESULT.md`.

## Silent performance 0.20.23 — INSTALLED 2026-10-03 (current card state)

User explicitly requested all logging removed. Package `builds/pgwr/0.20.23/`, isolated source `builds/.cache/silent-0.20.23/plugin/`; NRO `424914c18e740aea67c37ed399ffe5a22208b76f10dec81e279a8285198b777e` (524288 B). `logging` OFF; `hero-mana-hud` stays ON and reserved recovery OFF. 224 diagnostic call expressions (file and console) now use the existing logging feature; their arguments are not evaluated in the silent build. Diagnostic-only changes persisted to matching live modules without replacing gameplay code.

Verified B: offline build/source reversal and binary checks passed; now installed with all 5099/5099 card files and built/package/card NRO equal. Five other plugins and Skyline unchanged, frameworks OFF. Existing gameplay/assets retained, mana debit/recovery fixes excluded as pending worker work. Backup `evidence/sd-backups/sd-backup-20261003-125341`. Runtime smoothness unverified; no diagnostic markers expected. Record/test sheet: `evidence/2026-10-03_pgwr_0.20.23_silent/INSTALL.md`.


## Collective 0.20.22 — INSTALLED 2026-10-03 (superseded by silent 0.20.23)

Installed Hero level-2 side-B angle, visible battle mana HUD on both c06/c07 forms, and up-B air gravity 0.70/0.70. Package `builds/pgwr/0.20.22/`; NRO `3ab31bd34dceda31659f337867fdf67330afa691c50d565b514cd66124dd6772`; tree `3a64be3b167ac7ff864399056e0e7ce74a7b011e5a6315a5f1ba408583f74cfa`; 5099/5099 card files verified. DK cargo/Incineroar and ready-assets.1 visual fixes retained. All other plugins/Skyline unchanged; frameworks OFF, hero-mana-reserved OFF. Dashgrab excluded (no completed handoff). Backup `evidence/sd-backups/sd-backup-20261003-122846`. Build/native/HUD/angle/gravity audits passed offline; all new gameplay/UI behavior unverified. Test sheet/log markers: `evidence/2026-10-03_pgwr_0.20.22_install/INSTALL.md`.


## Hero Zapple angle + battle mana HUD — Codex takeover — 2026-10-03 — INSTALLED in collective 0.20.22

Task 0.1.1; concrete package `builds/pgwr/zapple-mana-hud-0.1.1/`, plugin/banner/info 0.20.21.
MANIFEST `5e0219f203ec6cbb8a66d953ca8adc08032659b44af3bee28a44cc515893c019`; combined NRO `48291984dfc2ae4e5c0b92ab19c15312807170f643f68bc992a792f98b3c2b65`;
mod tree `7bade18fdeb9a12de6eccb66586e44b4b53f4a405e55755d910b2edf8ecb3e5f` (5099 files; info version only changed).
Baseline ready-assets.1: installed NRO `214dc3126430598fb5e71093f6d5d584e17e662a593b67acf0eb0b777eb66058`.
All installed assets, DK cargo and Incineroar source/registrations retained; dashgrab/up-B gravity excluded.

Separate controls in package controls/: angle-only, HUD-only, baseline-control; full hashes in MANIFEST.
Isolated sources `builds/.cache/mana_hud_codex/`; narrow `patches/{angle,hud,version}.patch`.
No new status id, asset/config delta or framework change. `hero-mana-hud` ON for combined/HUD-only;
`hero-mana-reserved` OFF in every variant. Native HUD integration explicitly authorized by user.
Collective installer must merge narrow patches into an isolated coherent source union, retain the latest
asset tree and choose one final version; do not broadly build live source or overlay old cached assets.
If installing this standalone candidate, use its full atmosphere/ultimate tree and exactly one NRO.

Offline B: four builds, 25 native spans + nine slots, 161 HUD checks per HUD variant, negative controls,
four joint measurements, packaged/built hashes, exact source/asset preservation and patch reproduction PASS.
Runtime unverified (D); no install, emulator, console, commit or push. Angle remains a measured-joint candidate.
HUD state resets at stock/entry boundaries and its instant-set window counts frames; swaps retain shared MP.
No blocker for controlled hardware testing. Existing Main-callback regen dedupe limit remains a test concern.

Console checks and exact log lines: `evidence/2026-10-03_pgwr_zapple_mana_hud/RESULT.md` (11 steps).
Test baseline then angle-only and HUD-only in separate boots, vanilla c00/c05 + Hero/Kirby controls,
both c06/c07 forms, spend/regen/shortage/stocks/swaps, teams/reordered slots/5-8 players and teardown/rematch.
Boot log `sd:/ultimate/pgwr_mana_log.txt`: require `HUD READY route=game-part-selector spans=25 slots=9`
and visible correct gauge; `HUD REFUSED`, `HUD SELECT-FAILED`, `HUD OFF` fail the HUD test.
READY/BIND are internal checks, not proof of drawing. Collect the log from boot and crash_reports on crash.

## Ready asset batch 1 — INSTALLED 2026-10-03 (retained in collective 0.20.22)

Installed Chrom jab sword visibility, costume-themed Lucas/Ness magic effects and G&W starting-form loading presentation. Package `builds/pgwr/0.20.20+ready-assets.1/`, 5099/5099 card files verified; tree `a38d16c037389f730c842fc70fbda04b033b2dfc1e70ee7f4060520702dbf153`. NRO unchanged `214dc3126430598fb5e71093f6d5d584e17e662a593b67acf0eb0b777eb66058`; shared plugin/info version remains 0.20.20. DK cargo/Incineroar and other existing gameplay preserved. All plugins unchanged, framework install OFF. Backup `evidence/sd-backups/sd-backup-20261003-114100`. New visual outcomes unverified; test sheet and evidence `evidence/2026-10-03_pgwr_ready_assets_1/INSTALL.md`.

Hero angle/HUD and dash-grab slide excluded (no ready handoff). Up-B gravity excluded (PENDING/no concrete package). Active workers' source and build inputs untouched.


## chrom_jab_sword 1.0.0 on dk_cargo-0.1.1-test — 2026-10-03 — **INSTALLED: asset-only in ready-assets.1**

The Chrom jab's sword is invisible on hardware through 0.20.0-0.20.20. The cause is
byte-proven, not a guess: `build_esword_pose._build_jab_mlist` wrote the appended
motion-list entries' animation-name hash as `hash40('jabopen')` /
`hash40('jabtoopen')`, but that hash covers the file name **with its extension** —
every vanilla entry of the same article proves it (`open` -> `0xe32317ab0` ==
`hash40('z00open.nuanmb')`). Both jab entries named a file that does not exist, which
is silent: the article keeps playing `z00close`, whose `flamesword` **mesh visibility
track is False**, and that track overrode the `set_visibility_whole(true)` the ACMD
issues at frame 3. The Cloud fair was unaffected because it drives the vanilla
`to_open` kind. **No Rust changed, so there is no NRO to rebuild and none should be
copied for this section** — the installed plugin binary stays valid.

Package `builds/pgwr/chrom-jab-sword-1.0.0/` (`MANIFEST.json`, `BASELINE_DELTA.json`,
`README.md`). Baseline `builds/pgwr/dk_cargo-0.1.1-test`, mod tree
`dae0bff00e20cbe3b5da37215fe82f745ac27c7d8776d180fd08644fc3be6f5e` over 5098 files.

| file | baseline | candidate |
|---|---|---|
| `fighter/eflame/motion/esword/c06/motion_list.bin` | `8b7be43a2435c97121904c6b6bfaf6f79e80c9fb1bd4b8f8c57afe0cad81cde4` | `1816a2913b77843312f7d8c19a2497677736721e68fa778b8106341f51f62b2f` |
| `fighter/eflame/motion/esword/c07/motion_list.bin` | `8b7be43a2435c97121904c6b6bfaf6f79e80c9fb1bd4b8f8c57afe0cad81cde4` | `1816a2913b77843312f7d8c19a2497677736721e68fa778b8106341f51f62b2f` |

884 bytes before and after; differing byte offsets per slot 804-808 and 856-860,
both inside the two appended entries. Nothing added, nothing removed.

**Checked (tier B, offline).** `tools/audit_chrom_jab_sword.py --check`: 96 checks,
0 failures, four negative controls caught; the same audit run against the baseline
reports 10 failures, so the PASS is about the fix and not about the audit having
run. The other 22 files of the two article folders regenerate byte-identical, and no
other file of the tree differs. `attack_11`/`_12`/`_13` still name
`c00attack11.nuanmb` at cancel 23; `attack_air_f` still names `c05attackairf.nuanmb`;
`config.json` still declares both jab clips; per-state visibility/scale unchanged
(1.4 fair / 0.9 jab).

### Installer: exactly what to run

```bash
cd mods/ssbu_mod_new
D=builds/pgwr/chrom-jab-sword-1.0.0/ultimate/mods/pyra_gamewatch_reskin
T=<your merged tree>/ultimate/mods/pyra_gamewatch_reskin

# 1. two files. No NRO, no rebuild, no config.json, no motion entry, no status id.
cp "$D/fighter/eflame/motion/esword/c06/motion_list.bin" "$T/fighter/eflame/motion/esword/c06/motion_list.bin"
cp "$D/fighter/eflame/motion/esword/c07/motion_list.bin" "$T/fighter/eflame/motion/esword/c07/motion_list.bin"

# 2. verify against the tree you actually modified
python -B tools/audit_chrom_jab_sword.py \
  --baseline builds/pgwr/dk_cargo-0.1.1-test/ultimate/mods/pyra_gamewatch_reskin \
  --candidate "$T" --check

# 3. reproducible instead of copied (writes into a temp dir; copy the two files from it)
python -B src/pgwr/tools/build_esword_pose.py c06 c07
```

This section **compiles with every other section**: it touches only the two esword
article motion lists, which no other task in the queue edits. Expected merged mod
tree `1091b63be89a26bb319eeb38879e2d166cc66a0946e940ccea6a9e04d4f080cf` over 5098
files *only if nothing else is merged in*; recompute after the merge (rule: sha256
over sorted `"<relpath>\t<sha256>\n"` rows — the same rule reproduces the baseline
hash exactly).

### Manual console test — 14 steps, vanilla controls included

`logging` stays off, so there are no `[PGWR-*]` markers for this move and none are
expected; judge by eye. Return the boot log and any new crash report regardless.

1. **Vanilla control.** Pyra **c00**: jab three times. Must match the unchanged stock-Pyra baseline jab. Then Pyra **c01-c05**: compare against their unchanged baseline; no modded Chrom override.
2. **Vanilla-costume control.** Mythra **c00**: her jab and sword presentation must match the unchanged baseline.
   She is a different fighter and must be untouched.
3. Pyra **c06**, single jab. **The blade must appear**, small (0.9x, a little
   smaller than the fair's), in the hand, and swing with the arm.
4. The blade must stay out from about frame 3 to frame 20 and be **gone by the time
   you can act again**. A blade left hanging at the hip after the move is a fail.
5. **Idle cleanup.** After the jab, stand still for three seconds and walk, dash and
   jump. No blade may appear in any of it. Then jab again: it must come back.
6. **Chain.** Jab, jab, jab (attack_11/12/13 all draw the same blade). The blade must
   reappear on each, once, and be put away after the last.
7. **Facing right**, then **facing left**: the blade must be in the hand and swing
   with the arm in both. Report which facing looks wrong if either does; this is the
   one thing the port does not decide itself.
8. **Interruption.** Have an opponent hit you mid-jab, several times. The blade must
   not remain visible during the hitstun, and must come back on the next jab.
   Also try being grabbed, ledge-climbing and getting KO'd mid-jab.
9. **Trail.** The ribbon must start and end with the blade — black/pink on c06,
   white/gold on c07 — and its tip must reach the blade tip, not stop short. A
   ribbon trailing in mid-air away from the blade is a fail.
10. Pyra **c07**, repeat steps 3, 4, 5 and 9 (white/gold trail).
11. **Forward-air control.** Pyra c06 and c07, Cloud's forward air: the sword must
    still appear, still be **larger** than the jab's, and its trail must still reach
    its tip. This is the hardware-confirmed behaviour and must not regress.
12. **No collateral.** Side-B, up-B, dash, down-B (Mythra swap) and a G&W special on
    c06/c07: none of them may show a sword.
13. **Swap.** Enter as Pyra c06, press down-B to become Mythra, and jab: it must be
    Mythra's own unchanged jab/sword presentation. Swap back and jab: the blade returns.
14. Return the boot log and, on any crash, the newest file in
    `sd:/atmosphere/crash_reports/`.

**Pass** = steps 3-10 show the blade on c06 and c07, following the arm, gone after
the move, gone on interruption, gone during unrelated moves, with its own trail;
steps 1, 2, 11, 12, 13 unchanged. **Fail** = any of: no blade at all (the fix did
not land); blade visible during unrelated moves; blade left out after the move; no
trail; fair's sword changed in size or timing; c00-c05 or Mythra c00 changed.

**Known gap to expect, and how to read it:** the article's own `game_toopen` script
is not available in this workspace, so if the blade shows up at the *fair's* size
rather than the jab's, that is this open question and **not** a visibility failure —
report it as "blade visible but too big" and say so in these words.

**Blockers:** none for the port. All behaviour is tier D until step 14 comes back.
This agent did not install, did not touch the card, did not run the game or the
emulator, did not rebuild the NRO, and made no commit, branch or push.

## Loading presentation — Codex — 2026-10-03 — INSTALLED in ready-assets.1

- Task package **0.1.0**: `builds/pgwr/loading-presentation-0.1.0/`;
  MANIFEST SHA-256 `d17829ecd2726972c8ed978efab9957d772217e194983b2f14da601fb862022d`.
  Delta tree `8fa909b0540d840b666e999e03233d4a2b3acd24d0d2ed5574d7bce61f6ad804`.
- Baseline: latest installed `dk_cargo-0.1.1-test`, includes Incineroar on 0.20.20;
  5098/5098 checked. Inherit NRO `214dc3126430598fb5e71093f6d5d584e17e662a593b67acf0eb0b777eb66058`;
  no NRO rebuild is required by this asset-only task. Installer owns collective version.
- Source/tool: `src/pgwr/tools/loading_presentation/{package.py,audit.py,README.md}`.
  Four delta files: ui_chara_db.prc, ui_layout_db.prc, chara_3_eflame_first_06/07.bntx.
  Exact per-file hashes in MANIFEST and evidence RESULT.md. Theme/name pair retained:
  Ursula Shadow Purple c06; Wilhelmine Golden Light c07. Mythra is not replaced.
- **Shared overlap:** both PRCs are semantic patches. After final build and other
  naming/UI unions, run from mod root:
  `python -B src/pgwr/tools/loading_presentation/package.py apply --candidate builds/pgwr/INSTALLER_VERSION/ultimate/mods/pyra_gamewatch_reskin`.
  Do not copy task PRCs over a collective candidate. Tool retains unrelated fields
  and rejects occupied incompatible rows/routes/portrait edits; record returned hashes.
  No config declaration change (all paths exist in ARC), no IDs/framework dependencies.
- Offline checks PASS: native chara_3/form/count/cNN mapping; four-file identical
  reproduction; typed PRC round trips; name/CSS preservation and conflict controls;
  eight player panes; 16 costume/start/count routes. Calculated task-only union:
  5099 files, 5095 unchanged, 3 changed + 1 added, tree
  `0f768dec7d0992903022406c4df368f65c0a0808e21427c389e5318b45f64c95`.
- No hard offline blocker. Hardware unverified; no installation/SD/emulator/game run.
  Ten-step test matrix covers both costumes/starts, Training, Versus P1–P8 and
  4/5-player route boundary, mixed entries, vanilla c00/c05 and stock G&W controls,
  CSS/HUD/results/names/swap/gameplay regressions. See README and
  `evidence/2026-10-03_pgwr_loading_presentation/RESULT.md`. No new runtime log marker;
  retain `sd:/ultimate/pgwr_log.txt` from boot and any new crash report.
  Existing decoded c07 Mythra art artifacts are preserved, outside this G&W change.

## User console verdict — 2026-10-03

Tier A, user report: "the latest version of the mod works great." This updates prior install-time hardware-pending notes; no individual control checklist or boot hashes were supplied. Latest recorded package is dk_cargo-0.1.1-test over shared 0.20.20 (exact tested-package association inferred). Remaining user-reported issues and six newly requested worker scopes are recorded in `evidence/2026-10-03_pgwr_user_verdict/RESULT.md`. Only the modded eflame/elight c06/c07 pair is in scope. The later user request authorizes this partial install; remaining tasks wait for readiness.


## dk_cargo 0.1.1-test on Gaogaen 0.3.0 / 0.20.20 — INSTALLED 2026-10-03 (superseded by ready-assets.1 above)

User-authorized cargo test installation, 5098/5098 mod files verified; built/package/card
NRO `214dc3126430598fb5e71093f6d5d584e17e662a593b67acf0eb0b777eb66058`. Tree `dae0bff00e20cbe3b5da37215fe82f745ac27c7d8776d180fd08644fc3be6f5e`.
Backup `evidence/sd-backups/sd-backup-20261003-095401`. Protected plugins and Skyline byte-unchanged;
framework installation OFF. Shared version remains 0.20.20, private IDs 0x400..0x411.
Includes existing Snake/Lucas/Ness/Incineroar changes; other pending tasks excluded.
No game/emulator run. Record `evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test_install/INSTALL.md`.
Hardware test/log from boot: `evidence/2026-10-03_pgwr_dk_cargo/RESULT.md`.


## dk_cargo 0.1.0-test on Gaogaen 0.3.0 / 0.20.20 — INSTALLED 2026-10-03 (superseded by controlled retest above)

User-authorized cargo test installation, 5098/5098 mod files verified; built/package/card
NRO `270bc6723393767b7ae0dd639faae821fe0ffde6357938a552bed41a7faa7795`. Tree `dae0bff00e20cbe3b5da37215fe82f745ac27c7d8776d180fd08644fc3be6f5e`.
Backup `evidence/sd-backups/sd-backup-20261003-090320`. Protected plugins and Skyline byte-unchanged;
framework installation OFF. Shared version remains 0.20.20, private IDs 0x400..0x411.
Includes existing Snake/Lucas/Ness/Incineroar changes; other pending tasks excluded.
No game/emulator run. Record `evidence/2026-10-03_pgwr_dk_cargo-0.1.0-test_install/INSTALL.md`.
Hardware test/log from boot: `evidence/2026-10-03_pgwr_dk_cargo/RESULT.md`.


## gaogaen_throw_b 0.3.0 on 0.20.20 — INSTALLED 2026-10-03 (superseded by cargo test above)

Incineroar back throw on G&W `eflame` c06/c07, owned status `0x208`, installed as the **only** READY
section in this queue. All gameplay unverified; nothing here has been run on hardware. The four
0.20.20 moves it sits on top of (Snake down throw, Lucas down smash, Ness back throw) are still
unexercised too.

NRO `5d7d9b8e565d9b38d6a73d804a36f4028e6fcd80ff92f15739ed96f3b783689b` (487,424 B, **new binary**);
mod tree `7a33ab21e5a6c313b20c7c6160d4b7cf92914bf759a45be11a5c4364e50bae2c` (1992 files); manifest
`builds/pgwr/gaogaen_throw_b-0.3.0/MANIFEST.json`. Cargo cache read from the package manifest
(`gaogaen_throw_b/runtime-target`), features `snake-neutral-b,hero-side-b`, `logging` **off**.
Backup `evidence/sd-backups/sd-backup-20261003-021215`. Framework installation OFF; all four
protected plugins byte-unchanged (smashline still `5f4091ee…`).

Delta vs the installed 0.20.20: **15 changed files + 2 added owned clips, nothing removed.**
Independently measured here, not taken on trust: motion lists 841 → 842 entries with exactly one key
added and **zero existing entries altered**; sound banks 548 → 553 (`se`) and 244 → 245 (`vc`) with
every prior tone record and audio blob byte-equal as a prefix; `config.json` differs only by the two
new clip declarations (plus an LF → CRLF line-ending change). Pre-install card read confirmed 0.20.20
1990/1990 equal; post-install card read confirmed 1992/1992 equal against the package **and** against
the manifest's own hashes, with a recomputed card tree hash equal to `7a33ab21…`.

Excluded as not READY: **dk_cargo** (INCOMPLETE — no runtime Rust, no integration NRO) and **T-0054**
(PENDING — candidate staged only). Shared plugin/`info.toml` version deliberately stays 0.20.20.

Record: `evidence/2026-10-03_pgwr_0.20.20+gaogaen_throw_b/INSTALL.md` and
`evidence/install-record-2026-10-03_021215.json`. **Test sheet (13 steps, vanilla + donor controls):
`evidence/2026-10-03_pgwr_0.20.20+gaogaen_throw_b/RESULT.md`.** Read the log from boot at
`sd:/ultimate/pgwr_gaogaen_throw_b_log.txt`; crash reports under `sd:/atmosphere/crash_reports/`.

**Tooling defect found during this install:** `tools/verify_installed_card.py` cross-checks a manifest
key named `mod_file_hashes`, which this task's manifest does not use (it uses `mod_files`), so its
manifest line printed "0 entries" and was vacuous here. Its file-by-file comparison was unaffected and
passed. The real manifest check was done directly against `mod_files`. The tool should accept both
key names.

## Collective 0.20.20 — INSTALLED 2026-10-02 (superseded on the card by the install above)

Snake down throw, Lucas down smash and Ness back throw are installed together; all gameplay unverified. Individual delta audits and fresh combined build passed; card rehash 1990/1990 equal, protected plugins unchanged. NRO `7242d2f5af32bcc5304aa0e94930fe22ac689bd21db9b213f2ecfdac5fbf2098`; tree `10cd7a07a629897aa24c775173cffbfa13f071c5308f19fe0b483995a9f78abc`. Backup `evidence/sd-backups/sd-backup-20261002-193356`. Full record and corrected eight-step test: `evidence/2026-10-02_pgwr_0.20.20/INSTALL.md`. DK cargo and Incineroar back throw excluded as incomplete. Logging remains off; no new per-move pass markers expected.







## dk_cargo — Codex — 2026-10-03 — INSTALLED: controlled cargo-throw retest

**dk_cargo (2026-10-03, Codex): 0.1.1-test INSTALLED for hardware retest; corrected throws unverified.**

0.1.0 hardware A: user reports pickup, carrying/walking/jumping and grab release
successful; cargo throws crash. All three reports share a null capture object
reference at main+0x483130 during stock victim Thrown motion lookup.
Evidence: `evidence/2026-10-03_pgwr_dk_cargo-0.1.0-test_hardware/RESULT.md`.

Retest package `builds/pgwr/dk_cargo-0.1.1-test/`; NRO
`214dc3126430598fb5e71093f6d5d584e17e662a593b67acf0eb0b777eb66058` (581632 bytes), manifest `144d8a3ee2990a97a04230a860039bbe188a8e4384658b80443066f41da3014d`.
5098 assets unchanged, tree `dae0bff00e20cbe3b5da37215fe82f745ac27c7d8776d180fd08644fc3be6f5e` (sorted path/TAB/hash/LF).
Single behavioral change: three owned End/Exit comparisons accept queued stock
victim carry/thrown semantic aliases so capture can survive to owned Pre routing.
Diagnosis remains D until controlled retest; no claim that throws now work.
Offline B: isolated release build, exact three-call-site delta, 8448 compiled
comparison controls, same assets/IDs, preserved source baseline and NRO checks passed.

Existing shared 0.20.20 / Gaogaen/Snake/Lucas/Ness baseline retained. No live shared
registration or framework changes. Four-file integration.patch still unapplied.
ID requirement unchanged: 15 attacker + 3 victim roles per eligible table, 18 on
eflame; production unallocated, private test IDs 0x400..0x411. Native generic
capture/shared-motion and actual victim native pickup scripts remain dependencies.
Host physics, attachment geometry, all four directional throws and death/swap/
interruption cleanup need hardware verification. No new reserved hook blocker.

Reproduction: `src/pgwr/tools/dk_cargo/revision.py prepare`; private snapshot
`builds/.cache/dk_cargo/test-plugin-0.1.1`, cargo-home under dk_cargo, target
`builds/.cache/dk_cargo/runtime-target-0.1.1`; offline cargo skyline build with
snake-neutral-b,hero-side-b, then `revision.py package`/`check` and
`check_transition.py`. Completed snapshots/packages remain immutable.
Assets inherit 0.1.0 ASSET_DELTA.json; zero new asset/config/motion/bank edits.
Full pins, hashes, controls and test sheet: `evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test/RESULT.md`.

Test c06/c07 pickup, carry, jumping and escape first as the 0.1.0 positive control.
Then four ground cargo throws, both facings, and repeat airborne. Expect
`REGISTERED task=dk_cargo-0.1.1-test`, `VICTIM_ROUTE stock=0xc7 owned=0x411`,
advancing throw clips and one actual release. Compare vanilla DK/Pyra and unrelated
throws. Fail: same crash, missing victim route, frozen clips, stale links/control.
Log from boot: `sd:/ultimate/pgwr_dk_cargo_log.txt`; crash reports:
`sd:/atmosphere/crash_reports/`. Remaining twelve-step full checklist is in the
0.1.0 offline RESULT.md. No game/emulator has been run by this agent.

Updated 2026-10-02. User instruction: development agents prepare their changes here;

one designated installer agent installs the requested changes together when the user asks.

Canonical workflow: `AGENTS.md` rule 23. Preserve other agents' sections.



**2026-10-02, T-0056:** everything that was on the card before that run is now recorded as

**tested** - see the "Tested 2026-10-02" line under each installed section. That marking is

the user's declaration ("mark everything that is installed on the SD card right now as

tested") plus what is on the card itself: boots of the installed core in

`sd:/ultimate/pgwr_snake_log.txt` (0 FAIL/REFUSED lines, archived as

`evidence/2026-10-02_pgwr_T-0056/pgwr_snake_log_card_2026-10-02.txt`, sha256 `d146f7ae...`)

and `sd:/ultimate/pgwr_hero_s_log.txt`, and no crash report newer than 2026-09-30 04:09, i.e.

none from any 0.20.13-0.20.16 run. **Where the user gave no verdict, the item is marked

"exercised", not "passing"** - nothing in this file claims a result nobody reported.



## Lucas / Ness effect themes on Mythra c06/c07 — Claude — 2026-10-03 — INSTALLED in ready-assets.1

- Task package **0.1.0**: `builds/pgwr/lucas_ness_effect_theme-0.1.0/`, MANIFEST sha256
  `42631f4f413679c49bb335e1960a4f62cfd4d8805f7a690d851b475ef2836f25`, delta tree
  `c2ca1592e3286d70093b03ed3248b43233e5ad6b9ab72704f91c5dcd581a04fe` (2 files).
  - `effect/fighter/elight/ef_elight_c06.eff` `79d1fcc0d4688bd8902d624ac79fbded0f8b2bd1ba0fb9d25f310ab755f19d8f`
    (input `fcdd6caa49b5d8b7c50a9c44a612acfba757556560b7b79d5561af4b41ecbc17`)
  - `effect/fighter/elight/ef_elight_c07.eff` `d7217697ac7e6af58440de6b61d7f5d0c632905a3cc219632fd9d5b38387ab98`
    (input `1734bb5443e28b956c5c7bb478aac94030dbaee2b22a319ea13d3f37ef26648b`)
- Baseline: latest installed `dk_cargo-0.1.1-test` (includes Incineroar and DK cargo over shared
  0.20.20), tree `dae0bff0...` recomputed equal. Asset-only: **no NRO, config.json, motion, sound,
  param, status id or framework change**; inherits NRO `214dc3126430...`. Installer owns the version.
- What it is: `LUCAS_PSI_HOLD`, `LUCAS_PSI_ATK_LW`, `NESS_PSI_RUSH` re-coloured to the costume
  palettes (c06 scarlet/crimson/magenta/violet, c07 white/gold/light pink). Tool
  `tools/customize_lucas_ness_effects.py` 1.0.0 (sha256 `11b21eb3dc4f7912...`).
- **Shared overlap:** the two elight banks. This is a semantic merge. If no other READY task
  changes them, the two package files equal what the tool produces and may be copied. If another
  task's candidate bank differs from the inputs above, do **not** copy; run, from the mod root,
  per slot, then put each output in place of the candidate bank:
  `python -B tools/customize_lucas_ness_effects.py --slot c06 --recipient builds/pgwr/INSTALLER_VERSION/ultimate/mods/pyra_gamewatch_reskin/effect/fighter/elight/ef_elight_c06.eff --output builds/.cache/INSTALLER_CACHE/ef_elight_c06.eff`
  (same for c07). It keeps every other emitter set/texture/model, refuses if another set now
  uses the two owned textures, is a no-op on an already themed bank, and writes a `.theme.json`
  record. Re-check a copied package with `--verify-package builds/pgwr/lucas_ness_effect_theme-0.1.0`.
- Offline checks PASS (B): `--check`; `--package` (converter byte round trip, 3543 unrelated
  decoded entries identical, closed colour-field list, raw diff 122,719 / 124,164 bytes with 0
  outside 20 owned emitter blocks and 2 owned textures, reproducible, idempotent, three negative
  controls); `--verify-package`; concurrent-addition control; loader resolution (bank declared
  under `fighter/elight/c0X` only, one bank entry per resource, plugin requests all three names).
- Unverified (D): appearance in game. Not a packaging blocker. Blockers: none.
- Visual console checks (no log needed): on Mythra c07 the down-smash orb/bursts are white-gold
  with pink accents and the back-throw PSI is pink-white rings with gold streaks; on c06 scarlet
  with violet/magenta accents and magenta-violet rings with scarlet streaks; no yellow/green/blue
  donor colours on either. Controls: other c06/c07 effects, Mythra c00, real Lucas/Ness, damage,
  timing and sounds unchanged. Full 7 steps, preview sheet and records:
  `evidence/2026-10-03_pgwr_lucas_ness_effect_theme/RESULT.md`.
- This agent did not install, touch the card, run the game/emulator, rebuild the NRO, commit,
  branch or push.

## Installer procedure



1. Read each requested section. READY means a concrete checked package; PENDING means

   unfinished work, and BLOCKED identifies a dependency. Do not install a pending source tree.

2. Coordinate with active agents before any shared build. Resolve overlapping Rust modules,

   status allocations, motion lists, sound banks and `config.json` in the combined source.

   Multiple changes to one NRO require a combined build; copying several NROs is not a merge.

3. Build one semantic version under `builds/pgwr/<version>/`; ensure banner, `info.toml`,

   CHANGELOG and MANIFEST agree. Record full NRO/tree hashes, source hashes, toolchain,

   file count and included queue sections. Compare packaged and built NRO hashes.

4. Install only at the user's request through `src/pgwr/install-to-card.sh`, with framework

   installation OFF. Verify the entire staged tree and protected plugin hashes; retain the

   automatic backup and install record. No framework rebuild/overwrite is authorized here.

5. Update the collective record below and included sections. Provide one numbered test

   with vanilla controls and exact pass/fail log markers; request `sd:/ultimate/pgwr_log.txt`

   from boot and new `sd:/atmosphere/crash_reports/` files on a crash.

6. When the user declares a set of installed sections "tested", record it as **tested /

   exercised**, with the provenance (their words, the on-card logs, crash-report timestamps).

   Do not promote an item to "passing" unless a verdict was actually reported for it, and say

   so plainly where none was - see the 2026-10-02 note at the top of this file.



The user's request for collective installation permits combining requested READY changes

for that test. Record the combination explicitly: it is not evidence isolating the cause

of a failure. Use a controlled follow-up if attribution is needed (rules 9 and 11).## Last recorded card state




- **Current: gaogaen_throw_b 0.3.0 over 0.20.20, installed 2026-10-03 02:12:15 by the Freebuff
  designated installer (user request: "install the current changes to the switch").**

  NRO `5d7d9b8e565d9b38d6a73d804a36f4028e6fcd80ff92f15739ed96f3b783689b` (487,424 B, new binary);
  mod tree `7a33ab21e5a6c313b20c7c6160d4b7cf92914bf759a45be11a5c4364e50bae2c` (1992 files); package
  `builds/pgwr/gaogaen_throw_b-0.3.0`, cache `gaogaen_throw_b/runtime-target`, features
  `snake-neutral-b,hero-side-b`, `logging` off. Shared plugin/info version stays 0.20.20.

  Contents: the whole of 0.20.20 (which is itself 0.20.19 + Snake down throw, Lucas down smash,
  Ness back throw) **plus** Incineroar back throw on G&W c06/c07 at status `0x208`. Delta against
  0.20.20: 15 changed files, 2 added owned clips, 0 removed. DK cargo and T-0054 excluded as not
  READY. Backup `evidence/sd-backups/sd-backup-20261003-021215`. Framework installation OFF; four
  protected plugins byte-unchanged (smashline still `5f4091ee…`). Card re-hashed before the write
  (1990/1990 equal against 0.20.20) and after (1992/1992 equal against the package and the manifest).

  **Hardware test pending.** Test sheet:
  `evidence/2026-10-03_pgwr_0.20.20+gaogaen_throw_b/RESULT.md`; record:
  `evidence/2026-10-03_pgwr_0.20.20+gaogaen_throw_b/INSTALL.md` and
  `evidence/install-record-2026-10-03_021215.json`. No gameplay claim is made for any of the five
  moves now on the card.

- Previous card state (0.20.20, installed 2026-10-02 19:33:56; see its own section above).

- Earlier card state (0.20.19 installed 2026-10-02 17:16:04 by Claude, designated installer, user request):**

  Collective install of the three Freebuff tasks: Little Mac fist trails (T-0050), Snake up tilt,

  Hero mana - plus the T-0052 Kazap arrival change (0.20.18) that was already in the tree.

  NRO `1771152551c8a4a0de85a9a0e766ff63ccafeaa9f431251880824c3b214f3b72` (471,040 B, new binary);

  mod tree `755e3e5543ddcea7a204e3ba3a5696a6cb0488687e7e4c8358d41b60765b0ea2` (1984 files);

  cache `builds/.cache/pgwr-fbrun1-target`, features `snake-neutral-b,hero-side-b`, `logging` and

  `hero-mana-reserved` off. Delta vs 0.20.17: 19 changed, 2 added, 1 removed. Backup

  `evidence/sd-backups/sd-backup-20261002-171604`. Framework installation OFF, four protected

  plugins byte-unchanged. Post-install re-hash 1984/1984 equal. Assembled as 0.20.17 plus measured

  deltas, not by a `build.py` run. Record and checks: `evidence/2026-10-02_pgwr_0.20.19/INSTALL.md`.

  **Hardware test pending; use the manual tests in the three Freebuff sections below.**

- Previous card state (0.20.17):



- **Current: 0.20.17 installed 2026-10-02 02:20:35 by the T-0056 designated installer.**

  Collective install of the three changes that were queued: **T-0052** (Hero side-B Zapple

  orientation + Kazap arrival diagnostics), **T-0053** (Monkey Flip kick/general aerial

  lockout + swap guard) and **T-0048** (R.O.B. down tilt, stretched-arm recipe 3.0.0).

  - NRO sha256 `22bfbd01421280f61c15bdde54b9674df87e9beeccd28108f3a1bdeef960f901` (466,944 B)

    - **a new binary**; the previous card NRO was `81460e74...`. Not an asset-only install,

      so `--reused-nro` was *not* used.

  - Mod tree sha256 `730dd088d7999fd633736caab998a0f884d86631dcd36a7f6a3ce20327858394`

    (1983 files); manifest `builds/pgwr/0.20.17/MANIFEST.json`; cargo cache

    `builds/.cache/pgwr-T0056-target`, features `snake-neutral-b,hero-side-b`, `logging` off.

  - Delta against the previous card state (0.20.16+robot-dtilt.4): **exactly three mod files** -

    both `c02attacklw3.nuanmb` (now `06fb085e...`) and `info.toml` (0.20.16 -> 0.20.17).

    0 added, 0 removed.

  - Automatic backup `evidence/sd-backups/sd-backup-20261002-022035` holds the previous tree.

    Framework installation OFF; all four protected plugins byte-unchanged (smashline still

    `5f4091ee...`).

  - Independent post-install re-hash (`tools/verify_installed_card.py`): 1983/1983 equal,

    0 only-card, 0 only-package, 0 mismatches against the manifest's own hashes.

  - Records: `evidence/2026-10-02_pgwr_T-0056/INSTALL.md`,

    `evidence/install-record-2026-10-02_022035.json`. **Hardware test pending.**

  - Installer decisions worth knowing: the `logging` feature stays **off**, so T-0053's

    `[PGWR-MFLIP]` markers do not appear on this build and Monkey Flip must be judged by eye;

    and `package_pgwr_release.py` gained `--skip-donor-checks` because `dumps/arc` is empty,

    which is recorded in the manifest rather than hidden.

- Previous card state (0.20.16+robot-dtilt.4, 2026-10-02, **now marked tested**):



- **Current: T-0036 robot-dtilt.4 installed 2026-10-02, hardware test pending.** Installed by

  the Freebuff designated installer for task T-0042, on the user's request to "build and

  install all pending changes onto the switch in E:".

  - NRO sha256 `81460e74313350aaf569ce832045e8586387ab4ddf10e51bfdb690a8d29ef834` (462,848 B)

    - **unchanged from what was already on the card**; the change is asset-only, so no Rust

    was recompiled and no new plugin binary went onto the card.

  - Mod tree sha256 `66e3bc5e2c5f174271fd6d14f2dc3c4f6de4b7ca171f73382f3019d59b20b3f0`

    (1983 files); manifest `builds/pgwr/0.20.16+robot-dtilt.4/MANIFEST.json`.

  - Automatic backup `evidence/sd-backups/sd-backup-20261002-002850` (261 MB) holds the

    previous 0.20.16 tree. Framework installation OFF. All four protected plugins

    byte-unchanged (smashline still `5f4091ee...`).

  - Record: `evidence/2026-10-02_pgwr_T-0042/INSTALL.md`, `evidence/install-record-2026-10-02_002850.json`.

  - Installed with `MGW_PACKAGE=builds/pgwr/0.20.16+robot-dtilt.4 src/pgwr/install-to-card.sh

    --no-smashline --reused-nro`. `--reused-nro` is new; see the note under the R.O.B. section.

  - **Tested 2026-10-02 (T-0056): exercised on hardware by the user** (recipe 2.0.0's two

    down-tilt clips, `d30722b5...`, were the ones on the card). Superseded on the card by the

    recipe 3.0.0 clips in 0.20.17, so its visual verdict no longer applies to what is installed

    now.

- **Correction to this file's own record:** the Little Mac 0.20.16 release was **already

  installed** before this run, on 2026-10-01, even though its section said "STAGED, not

  installed". The whole card tree and the NRO hash equal to `builds/pgwr/0.20.16`, and

  `src/pgwr/.last-sd-backup` reads `20261001-020530`. So the **angled up/down forward smashes

  are on the card and are still untested.** Verified, not assumed: 1983/1983 files equal.

- Previous card state (0.20.15, **now marked tested** - see its section below, which keeps its

  own 2026-10-01 hardware verdicts):



- Independently verified pgwr **0.20.15** installation on 2026-10-01 (installed by the root agent at the user's request:

  "install it along with the new stuff on CURRENT_INSTALL.md"; Hero side-B was the only READY section); **hardware test pending**.

- NRO sha256 `7aa0ae2440e6604bf7b243209e2a5ff263e4e5bff1f7ab2a56b1e34da873feb4`; mod tree

  `ab74b4d0d5dbf7e7abb80846d95b58b175c6fe0aba54a7699d32b9fc7eeb2e9f` (1979 files); `builds/pgwr/0.20.15/MANIFEST.json`.

- Automatic backup `evidence/sd-backups/sd-backup-20261001-010808` holds 0.20.14. All 1979 card files re-hashed equal;

  the four protected plugins unchanged (smashline `5f4091ee...`). Installed with `--no-smashline`, `PGWR_CARGO_TARGET=pgwr-heroside-target`.

- Contents: 0.20.14 plus Hero side-B on Mythra c06/c07 (test in its section below). The user's install request was taken

  as confirmation of the Mythra `+0x170` receiver hook recorded in `receiver.rs`.

- Previous card state (0.20.14):

- Contents: installed 0.20.13 (Snake neutral-B, Monkey Flip, R.O.B. dtilt, Cloud trails, Chrom

  jab, c06 Ursula / c07 Wilhelmine) **plus Little Mac's forward smash and its charge hold on

  c06/c07**. **Excluded:** Hero side-B (NOT READY) and the angled up/down forward smash.

  > The exclusion of the angled variants was **wrong** and is reversed in 0.20.16 - see that

  > section. The "needs an authorized native routing hook" part was the error: no separate

  > status is needed, because the motion-list entry carries its own `game_script`, and the

  > plugin registers all four handler sets. Nothing native is hooked.

- Note on this release: the first packaging attempt silently picked up a **stale NRO** from a

  shared cargo cache (the packager selects its cache from `MANIFEST.json`). It was caught by

  grepping the packaged binary for the move's own sound names and rebuilding against the cache

  the packager actually reads. Worth remembering when auditing any package.

  > **Now fixed properly, in 0.20.16.** `package_pgwr_release.py` takes `--cargo-target` and

  > writes the cache it used into `MANIFEST.json`; `install-to-card.sh` reads it back from

  > there; and `package_pgwr_release.py --check` refuses a package whose recorded cache is not

  > the one the NRO was read from. `tools/audit_littlemac_fsmash.py::check_handlers` also

  > greps the packaged NRO for every handler and sound name, so a `PASS` can no longer hide

  > a wrong binary.



## Snake neutral-B — Codex continuation



**INSTALLED: 0.20.11 independently verified. TESTED 2026-10-02 (T-0056): the user exercised

it on hardware; the card log for the 0.20.16 core contains Snake `BOOT v0.20.16` sessions with

0 `FAIL`/`REFUSED` lines and no crash report since 2026-09-30.** Updated 2026-09-30.



- Target: G&W replacing Pyra c06/c07. Source: `src/pgwr/plugin/src/status/snake_grenade/`.

- Concrete package: `builds/pgwr/0.20.11/`; manifest: `MANIFEST.json` there.

- NRO sha256 `00a6c76555cfaa8bacb38322dad5096ae42c53a600d75c2efe0f9eec1fc33206`.

- Mod tree sha256 `e2c6ebf75e2cb1211a4dcaa37556541302afcb685e162acf2a5957140b023c7c` (1932 files).

- Baseline: installed 0.20.10, retaining Cloud fair/jab trails, Monkey Flip and quiet

  global diagnostics. Only Cargo feature `snake-neutral-b` enabled; `logging` remains off.

  Snake alone writes crash-tail diagnostics to `sd:/ultimate/pgwr_snake_log.txt`.

- Owned statuses `0x1FB..0x207`; next Pyra allocation `0x208`; costume gate `[6,7]`.

  Includes 29 motions/58 body clips, 152 cloned-pin files, translated lower-body

  dispatch and donor ACMD, nine exact donor sounds, genuine grenade item handling

  and the previously authorized signature-checked life bridge. No framework changes.

- Dependencies resolved: donor SQB and fifteen lower clips extracted read-only,

  hashes pinned in `refs/snake_grenade/{sequence,lower_body}/extraction.json`.

  No remaining packaging blocker. Prior crash R-11 remains unresolved by hardware.

- Required offline checks passed: release compilation; built/packaged NRO equality;

  generated ACMD comparison; native/lower/compiled-ABI audits; body/pin/config checks;

  preservation of all 457 existing tones per bank; package validation and baseline

  delta audit. Evidence: `refs/snake_grenade/{lower_translation_audit,compiled_guard_audit,

  body_assets_audit,sound_merge_audit}.json`, `builds/pgwr/0.20.11/BASELINE_DELTA.json`.

  Delta: 211 new mod files, ten intended overrides, no removed files; all other

  baseline files and old motion entries compare exactly. These are offline results.

- Installer: use this concrete package if Snake is the only requested new READY change.

  For other requested changes, coordinate a combined source/build and recheck shared

  NRO, status IDs, motion lists, sound banks and config. Do not include pending work.

  Stage with `--snake-neutral-b --stage-only`; assets need `PGWR_SNAKE_NEUTRAL_B=1`.

  Follow rule 23 and retain protected framework plugins. Development agent did not install.



Test after designated installation (return the entire Snake log **from boot**):



1. Fresh boot without stock Snake. Require `[PGWR-SNAKE-N] BOOT v0.20.11`,

   `[PGWR-SNAKE-N] READY life bridge 13.0.4 signature verified; owned life=150`

   and `[PGWR-SNAKE-N] REGISTERED` for c06/c07 and the reserved statuses.

2. Vanilla Pyra c00 negative control: normal neutral-B, no Snake `PULL`/`HOLD` events.

3. c06 ground neutral-B, hold B: verify pull, pin appearance/removal, advancing hold.

   Require `PULL ok`, `HOLD MOTION`; ground base/upper end frames should be 50.

4. Hold B while walking both ways, dashing, braking, jumping and landing. Check

   advancing owned clips with `LOWER`/`HOLD MOTION` transitions and donor step sounds.

5. Pull/hold in air, double jump and land; airborne full hold end frame should be 40.

   Repeat ground/air coverage on c07, including its pin and sound playback.

6. Release B or press A to throw high/middle/low on ground and in air. Require

   `THROW` and `RELEASE` with the chosen throw motion; verify the item leaves the hand.

7. Check two-grenade limit, grounded shield/drop and hit interruption. Verify fuse

   counts descend and items actually explode; creation alone is not a pass.

8. Opponent picks up and throws back. Compare stock Snake in a separate control run

   for fuse/explosion behavior; save both logs. Check retained jab/fair/side-B/up-B.

9. Return `sd:/ultimate/pgwr_snake_log.txt` from its BOOT line and any new

   `sd:/atmosphere/crash_reports/` files. Unexpected `FAIL`/`REFUSED`, frozen clips,

   missing pin/sounds, failed pickup/explosion or crash fails. On a worse crash,

   designated installer restores 0.20.10 and records the controlled result.



## Monkey Flip aerial side-B lock ? root



**INSTALLED: 0.20.7 independently verified. TESTED 2026-10-02 (T-0056): exercised on hardware

by the user. The T-0053 section below is its successor and is what 0.20.17 now ships.**



- User replied ?ready? to installing this exact package on 2026-09-30; this thread is its designated installer. Included scope is the Monkey Flip side-B lock only; pending Snake registration/assets are not included.

- Source: `src/pgwr/plugin/src/status/{monkey_flip,special_hi}.rs`; copied donor end/availability evidence: `refs/diddy_monkey_flip/special_lockout.json`.

- Package: `builds/pgwr/0.20.7/`; MANIFEST pins source hashes, toolchain, version and 1701 mod files. No status IDs or config entries are added; existing capture setup/asset content is retained. Side-B callback composes with Fire's availability callback.

- NRO sha256 `8dea58a20e8c06bfa71f8818818bf91649103a2b04d3de33522e70dff1b629f8`; mod tree `0a883520e042c06f7a1ccf675e1e183ff63d31d1942e5ab960733035344158d2`.

- Checks: release compilation, package validation and built/staged NRO equality; donor instruction audit and capture syscall ABI audit. Console test pending.

- Test: `projects/pgwr/STATUS.md`, next Monkey Flip test. Vanilla Pyra c00 control; c06/c07 no-kick/no-grab aerial miss, second side-B denied, landing/hit refresh; capture preserved and attack/jump releases checked separately. Require SIDE LOCK/BLOCK/REFRESH consequences and full `sd:/ultimate/pgwr_log.txt` from boot; crash reports under `sd:/atmosphere/crash_reports/`.

- Known gaps: victim T-pose deferred by user; kick/general HI/S/LW lock is the next separate hardware change. No framework replacement.



## Monkey Flip aerial locks: kick + swap - Buffy (T-0053)



**INSTALLED 2026-10-02 in 0.20.17 by the T-0056 designated installer. Hardware test pending.**

The code below is now what is on the Switch, compiled together with T-0052 (file-disjoint

source trees) into NRO `22bfbd01421280f61c15bdde54b9674df87e9beeccd28108f3a1bdeef960f901`.

**Because that release keeps the `logging` feature off (an installer decision, so the test is

one state-changing change and the 0.20.10 silent core is preserved), the `[PGWR-MFLIP]` markers

below will NOT appear: judge this by eye, not from the log.** No automated tests, no Ryujinx.



History: this section was source-only until 2026-10-02. The 0.20.7 line above was the card

state until then. This is the item that section listed as "the next separate hardware change".



- **Target:** G&W replacing Pyra c06/c07 - Monkey Flip (side-B) aerial reuse. This change

  adds the donor's *kick* lockout and repairs the side lock's swap bypass. It does not

  touch the capture receiver, the releases, the G&W props, or any asset, status id,

  work id, motion list or `config.json` entry.

- **Source (this agent's whole diff):** `src/pgwr/plugin/src/status/monkey_flip.rs`

  (new `Locks` record replacing `SIDE_LOCK`; three lock-setting exits in `end()`) and

  `src/pgwr/plugin/src/status/special_hi.rs` (one composed `global_table[0x26]` callback,

  four refresh call sites repointed). No other file is modified.

- **What the donor actually does** (tier B, `refs/diddy_monkey_flip/special_lockout.json`,

  `tools/audit_diddy_special_lockout.py` 1.0.0, cross-read with

  `refs/diddy_monkey_flip/source_audit/SpecialS{Jump,Kick,StickAttack2}_end.c`):

  - `JUMP` end -> `FALL`: `SPECIAL_S_INPUT_UNABLE`, gates `CONT_SPECIAL_S` only.

  - `KICK` end -> `FLIP_FALL`: `SPECIAL_INPUT_UNABLE`, gates `CONT_SPECIAL_HI`, `_S`, `_LW`.

  - `STICK_ATTACK2` end -> `FLIP_FALL`: same general flag.

  - Callback `0x7920` reads those flags; neutral-B and the aerials are not in it.

  Those three are the only lock-setting exits in the whole donor script set.

- **The two defects fixed** (full write-up: `kb/findings/monkey-flip-aerial-locks-need-an-object-owned-record.md`):

  1. Only the first exit was ported, so the *kick* path - the ordinary successful flip -

     locked nothing and up-B/down-B/side-B all stayed live in the air.

  2. The lock record was keyed by entry id and re-owned itself on any object-id

     mismatch. Pyra and Mythra share an entry id, so Mythra landing re-read the slot

     and wiped Pyra's airborne lock mid-air. The record now belongs to the battle

     object that set it; another object is neither blocked nor able to unlock, and a

     refused refresh prints one `SWAPGUARD` line with both object ids.

- **Bounded log lines** (need a build with `--with-logging`, feature `logging`; log

  `sd:/ultimate/pgwr_log.txt`):

  `[PGWR-MFLIP] LOCK entry N SIDE S (JUMP -> FALL)` / `... GENERAL HI/S/LW (KICK -> FLIP_FALL)`

  / `(STICK_ATTACK2 -> FLIP_FALL)`; `BLOCK entry N SIDE CONT_SPECIAL_S disabled` /

  `BLOCK entry N GENERAL CONT_SPECIAL_HI/S/LW disabled`; `SIDE REFRESH entry N by <event>` /

  `GENERAL REFRESH entry N by <event>`; `SWAPGUARD entry N keeps <lock> airborne lock;

  object <a> is not the owner <b> (<event>)`. One line per transition, never per frame.

  Refresh `why` strings are the native sources: `ground/ledge (+0x168)`, `hit (+0x220)`,

  `class event +0x210`, `rebirth/dead/entry`, `Mythra ground/ledge (+0x168)`.

- **Offline checks done here:** `cargo skyline build --release` and the same with

  `--features logging` both compile clean (`Finished`, no new warnings in the two files).

  **That is the only check.** No behavioural evidence of any kind exists for this change.

- **WARNING for the installer:** `builds/.cache/pgwr-mflip-target/` holds a verification

  NRO (`518fbc2560cd68b61da48e340ad8b9d4fd36af941e0dcb29a9c597bc5f3615d2`, 307,200 B) built

  **without** `snake-neutral-b` / `hero-side-b`. It is a compile artefact, not a package.

  Do not stage or install it - that is the stale-cache failure this file already records.

  Build the release in the normal cache with the same features the installed baseline

  uses, and record that cache in `MANIFEST.json` as usual.

- **Status: INSTALLED as part of 0.20.17 (2026-10-02), together with T-0052's disjoint

  Hero side-B change.** Rule 11's single-change preference was overridden by the user's

  explicit request to "install the new changes"; the two share one NRO and one test, so a

  failure there does not by itself attribute a cause (rule 9). The stale-cache warning below

  was honoured: the release was built in the new `builds/.cache/pgwr-T0056-target` with

  features `snake-neutral-b,hero-side-b`, and the packaged NRO carries the `SWAPGUARD`,

  `GENERAL HI/S/LW` and `PGWR-MFLIP` marker strings.



**Manual test after designated installation** (return `sd:/ultimate/pgwr_log.txt` **from

boot**, plus any new `sd:/atmosphere/crash_reports/` file). Compare with stock Diddy in a

separate control run for steps 2-6.



1. Boot. Require the `[PGWR-MFLIP] Monkey Flip: side-B on eflame c06/c07, donor statuses

   0x1ee-0x1f8` line and `[PGWR-UPB] REGISTERED ... refresh on`. Any `[PGWR-UPB] FAIL`

   means the refresh hooks did not install - stop, the locks would never clear.

2. **Vanilla negative control:** Pyra c00 and Mythra c00. Side-B and up-B behave exactly

   as vanilla and produce no `[PGWR-MFLIP]` LOCK/BLOCK/REFRESH lines.

3. **One flip per airtime, no kick.** c06: jump, side-B (leap that misses), then press

   side-B again before landing. The second press must do nothing. Pass log:

   `LOCK entry N SIDE S (JUMP -> FALL)` then `BLOCK entry N SIDE CONT_SPECIAL_S disabled`.

   **Up-B must still work** in the same airtime after a no-kick leap (donor asymmetry).

4. **Kick lockout.** c06: jump, side-B, press attack inside the kick window so the kick

   happens, then before landing press **up-B**, then down-B, then side-B. All three must

   do nothing. Pass log: `LOCK entry N GENERAL HI/S/LW (KICK -> FLIP_FALL)` and

   `BLOCK entry N GENERAL CONT_SPECIAL_HI/S/LW disabled`. A working aerial attack or a

   working neutral-B in that same airtime is correct and is the control that the lock is

   not simply freezing the fighter.

5. **Restoration.** (a) Land: `GENERAL REFRESH entry N by ground/ledge (+0x168)`, then

   side-B and up-B work again. (b) Repeat the kick, then get hit in the air:

   `GENERAL REFRESH entry N by hit (+0x220)`. (c) Repeat the kick, then grab the ledge

   and ledge-jump. (d) Repeat the kick and lose the stock: no lock must survive the

   respawn (no `BLOCK` line after `REFRESH ... rebirth/dead/entry`).

   If a refresh line appears that names `class event +0x210` **while airborne**, say so:

   that event's meaning is unknown, and it would mean the lock is shorter than the donor's.

6. **Swap cannot bypass it.** c06: jump, side-B, kick, then press down-B to swap to

   Mythra while still in the air, land as Mythra, swap back to Pyra. Side-B and up-B must

   both still be dead until Pyra herself lands. Pass log: `SWAPGUARD entry N keeps

   GENERAL airborne lock; object <mythra> is not the owner <pyra> (Mythra ground/ledge

   (+0x168))`. Mythra's *own* up-B must be unaffected by this.

7. **Capture preserved.** c06: side-B into an opponent so the leap captures, then the

   cling attack (-> `STICK_ATTACK2` -> `FLIP_FALL`): the throw must still happen and, per

   the donor, the general lock must be set (`GENERAL HI/S/LW (STICK_ATTACK2 -> FLIP_FALL)`).

   Also check the jump-out release and the plain release still work.

8. **Fire unchanged.** c06: up-B, drift down, land, up-B again - still refreshes, props

   and parachute unchanged. Up-B inside a Monkey Flip lockout must be denied (step 4).

9. Repeat 3-5 on **c07**; the two slots share one code path but not one record.

10. Regression sweep on c06/c07: jab, fair, Snake neutral-B, up-B, side-B on the ground,

    Pyra<->Mythra swap on the ground.



**Fail:** any `SWAPGUARD` line that is *not* accompanied by the move staying locked; a

second usable flip/up-B in one airtime after a kick; a lock that survives a landing or a

hit; up-B usable after a no-kick leap; capture/release regressed; Fire regressed; c00

changed; any crash (send the report and restore the last known good per rule 10).



**Unverified before the run:** the gate itself is tier D - it is donor-evidenced source

logic on the recipient, and 0.20.7's side-only version was reported working, but

`CONT_SPECIAL_LW` on this recipient, the `+0x210` reset event's real trigger, and the

swap behaviour have never been observed on hardware.



## Cloud Forward Air Custom Sword Trails (c06 & c07) — Antigravity



**INSTALLED: 0.20.8 independently verified; hardware test passed on 2026-09-30. Still

installed in 0.20.17 and re-checked by eye on 2026-10-02 (T-0056).**



- Target: G&W replacing Pyra c06/c07 Forward Air (`AttackAirF`).

- Purpose: Replace placeholder Mythra sword trail with custom Cloud sword trail copies (`tex_cloud_sword1`, `tex_cloud_sword2`).

- Source tool: `src/pgwr/tools/build_cloud_trail.py` (smoke tested).

- Integration: `src/pgwr/tools/build_color_themes.py` (deploys to `effect/fighter/eflame/trail_c06` and `trail_c07`), `src/pgwr/plugin/src/acmd/attack_air_f.rs` (routes `tex_cloud_sword1`/`2`).

- Color scheme mapping:

  - c06: Black & Pink Mythra theme (deep crimson/black core `[118, 0, 0]`, rich crimson midtone `[124, 0, 30]`, radiant magenta-pink edge `[145, 8, 90]`).

  - c07: Radiant White & Champagne Gold theme (pure white core `[255, 255, 255]`, radiant light champagne gold body `[255, 235, 170]`, warm gold edge `[248, 215, 140]`).

- Textures generated and offline verified:

  - `src/pgwr/assets/custom_cloud_trails/trail_c06/tex_cloud_sword1.nutexb` (351,408 B, sha256 `46a28ff16702c856711584cfb92cf571efd301eb5ff8b2baeb46110f0970a2f8`)

  - `src/pgwr/assets/custom_cloud_trails/trail_c06/tex_cloud_sword2.nutexb` (351,408 B, sha256 `8da2fce9c2b65c11dce8e6e0200b7dd6d61399aeddd564f3a626ff7b29d4d647`)

  - `src/pgwr/assets/custom_cloud_trails/trail_c07/tex_cloud_sword1.nutexb` (351,408 B, sha256 `c5b6adf679102d05777dae7ce592c300fa658e4efea971168449c25f54394017`)

  - `src/pgwr/assets/custom_cloud_trails/trail_c07/tex_cloud_sword2.nutexb` (351,408 B, sha256 `8da2fce9c2b65c11dce8e6e0200b7dd6d61399aeddd564f3a626ff7b29d4d647`)

- Checks: NUTEXB format `0x405` (Rgba8UnormSrgb), 9 mips, dimensions 256x256, internal resource names `TEX_CLOUD_SWORD1` / `TEX_CLOUD_SWORD2` bit-for-bit preserved from donor. Exact donor alpha channel preserved.

- Hardware result: Verified and working on console (evidence `evidence/2026-09-30_pgwr_0.20.8/RESULT.md`).



## Chrom Jab Custom Cloud Sword Trails (c06 & c07) — Antigravity



**INSTALLED: 0.20.9 hardware test passed on 2026-09-30. Still installed in 0.20.17 and

re-checked by eye on 2026-10-02 (T-0056).**



- Target: G&W replacing Pyra c06/c07 Jab (`Attack11`).

- Purpose: Replace placeholder Mythra sword trail (`tex_elight_sword1/2`) with custom Cloud sword trail copies (`tex_cloud_sword1`, `tex_cloud_sword2`).

- Source: `src/pgwr/plugin/src/acmd/chrom_jab.rs`.

- Integration: Routes `tex_cloud_sword1`/`2` via `AFTER_IMAGE4_ON_arg29` with `JAB_TRAIL_TIP` (14.5 * 0.9 = 13.05). Registers `effect_attack11/12/13`, `sound_attack11/12/13`, `expression_attack11/12/13`.

- Color themes: c06 Black & Pink (dark crimson/magenta-pink) and c07 Radiant Gold (white/champagne gold), using the already-deployed textures in `effect/fighter/eflame/trail_c06` and `trail_c07`.

- Package: `builds/pgwr/0.20.9/` (NRO `5ab7bdc591c2cfa577e4ea36080df2f57d3f558d08523ed2a000b48162945dc2`, mod tree `b7b42a95dd8a78a8af83c97f2aa9204c0f4be942db94b7a263d5506f095c0bab`, 1709 files).

- Hardware result: Verified and working on console (evidence `evidence/2026-09-30_pgwr_0.20.9/RESULT.md`).



## Silent Performance Build (Diagnostics & Logging Silenced) — Antigravity



**INSTALLED: 0.20.10 independently verified. TESTED 2026-10-02 (T-0056): exercised by the

user; this silent core is what every later release, 0.20.17 included, still builds on.**



- Target: G&W replacing Pyra c06/c07, move replacements on Mythra c06/c07.

- Purpose: Remove all runtime disk logging (`sd:/ultimate/pgwr_log.txt`) and per-frame observer callbacks so the character's gameplay feel can be evaluated smoothly without SD card I/O latency or CPU observer overhead.

- Package: `builds/pgwr/0.20.10/MANIFEST.json`.

- NRO sha256: `2ba2d1821cd822401affa5d20dfa7da5c44f5147483a7dfed8e593a68c58f0ee` (297,984 bytes).

- Mod tree sha256: `ede8c200198ee7faa542f9abe20f5bb98ab6a4b7ccb0ac0b005bab5f10eb167f` (1721 files).

- Diagnostic & Logging Silencing:

  - `src/pgwr/plugin/Cargo.toml`: Introduced opt-in `logging` feature (disabled by default in release builds).

  - `src/pgwr/plugin/src/article.rs`: `article::log` is a zero-cost no-op when `logging` feature is inactive; active file I/O retained under `#[cfg(feature = "logging")]`.

  - `src/pgwr/plugin/src/status/monkey_flip.rs`: `monkey_flip::log` is a zero-cost no-op when `logging` feature is inactive; active file I/O retained under `#[cfg(feature = "logging")]`.

  - `src/pgwr/plugin/src/lib.rs`: `diddy_probe::install()` per-frame observer callback on stock Diddy is disabled when `logging` is inactive; boot logging silenced.

  - `src/pgwr/plugin/src/acmd/mod.rs` & `mythra/mod.rs`: `gate_trace` per-frame `on_line` callbacks disabled when `logging` is inactive.

  - Zero disk writes to `sd:/ultimate/pgwr_log.txt` during gameplay.

- Logging Backup:

  - Exact 0.20.9 diagnostic source files backed up byte-for-byte in `evidence/logging_backup_0.20.9/` (with SHA256 checksums and restore procedures).

  - Can be re-enabled on any subsequent install either via `Cargo.toml` feature `default = ["logging"]` / `src/pgwr/build-plugin.sh --with-logging`, or by restoring backed-up files.

- Retained Functional Features:

  - Chrom jab custom Cloud sword trails (`tex_cloud_sword1`/`2`) on c06 and c07 (0.20.9).

  - Cloud forward air custom sword trails (`tex_cloud_sword1`/`2`) on c06 and c07 (0.20.8).

  - Monkey Flip aerial side-B lockout and capture handling (0.20.7).

  - G&W Up-B Fire with parachute and landing/ledge/hit refresh (0.19.0).

  - All G&W normals, articles (normal_weapon, breath), and physics bridges.

- Offline Checks:

  - Release build compiled cleanly with `cargo skyline build --release -- --offline`.

  - Full release validation with `tools/package_pgwr_release.py --version 0.20.10 --check` PASSED.

- Test Instructions:

  1. Character feel & fluidity: perform forward air, jab, side-B, and up-B repeatedly in training / match mode; verify absence of stutter or micro-freezes.

  2. Cloud sword trails: verify ribbons remain rendered with dark crimson/magenta (c06) and white/gold (c07) on jab and forward air.

  3. Monkey Flip: verify aerial lockout and capture functions as normal.

  4. Vanilla control: verify vanilla Pyra/Mythra on c00 remains completely unaffected.



## Little Mac forward smash family on G&W c06/c07 — Buffy



**0.20.14 INSTALLED and hardware-confirmed 2026-10-01 (TIER A). 0.20.16 INSTALLED

(verified present on the card 2026-10-02) and re-installed unchanged inside 0.20.17.

TESTED 2026-10-02 (T-0056): the user exercised the forward-smash family on hardware. The

angled up/down variants were exercised too, but **no verdict was reported for them**, so the

tier-D routing question below stays open - "exercised" is not "routed".**



- **Target:** G&W replacing Pyra c06/c07 — the forward smash (`AttackS4`), its charge hold

  (`AttackS4Charge`), and **the up/down-angled variants (`AttackS4Hi`/`AttackS4Lw`)** added in

  0.20.16. Replaces G&W's own prop-spawning forward smash. Up smash and down smash are

  untouched and stay G&W's.

- **0.20.14 result — TIER A, hardware:** the user reports the forward smash "works great, also

  animation wise", and G&W's prop correctly no longer appears. The neutral punch and its

  charge hold are validated; 0.20.16 changes nothing on that code path.

- **0.20.16 status: INSTALLED.** Package `builds/pgwr/0.20.16/`, manifest `MANIFEST.json`

  there. The card was found on 2026-10-02 to already hold this exact release (NRO and all

  1983 mod files byte-equal), so no install action was needed; the "STAGED, not installed"

  line in this section was stale. It is also the baseline the T-0036 down-tilt variant was

  built on, and that variant is now on the card. **The angled variants still need the

  hardware test below - nothing in this workspace has ever seen them run.**

  - NRO sha256 `81460e74313350aaf569ce832045e8586387ab4ddf10e51bfdb690a8d29ef834` (462,848 B).

  - Mod tree sha256 `06bacd78dc28833d172374745bb6ae6763c39999f084bff8204b392d6b322686` (1983 files).

- **Baseline:** the **installed 0.20.15** (Hero side-B on Mythra), via

  `PGWR_UI_BASELINE=builds/pgwr/0.20.15/ultimate/mods/pyra_gamewatch_reskin`.

  Snake neutral-B, Monkey Flip, R.O.B. dtilt, the Cloud forward-air and jab trails, the Chrom

  jab, the Hero side-B and the c06 Ursula / c07 Wilhelmine naming are all retained. Cargo

  features `snake-neutral-b` and `hero-side-b`; `logging` stays off, so this release writes no

  game log - request the crash-tail log from a crash, and judge the move by eye.

- **Build in an isolated cargo cache, and it is recorded in the package.** Built and packaged

  in `builds/.cache/pgwr-lm-target/`, not the shared one:



  ```bash

  # build

  cd src/pgwr/plugin

  PATH=/c/msys64/mingw64/bin:$PATH \

  CARGO_TARGET_DIR=../../builds/.cache/pgwr-lm-target \

  cargo skyline build --release --features snake-neutral-b,hero-side-b -- --offline



  # mod tree

  cd ../..

  PATH=/c/msys64/mingw64/bin:$PATH \

  PGWR_SNAKE_NEUTRAL_B=1 PGWR_HERO_SIDE_B=1 \

  PGWR_UI_BASELINE=builds/pgwr/0.20.15/ultimate/mods/pyra_gamewatch_reskin \

  toolchains/py312/python.exe src/pgwr/build.py



  # package - --cargo-target is what stops the wrong agent's NRO being packaged

  toolchains/py312/python.exe tools/package_pgwr_release.py \

    --version 0.20.16 --snake-neutral-b --hero-side-b --cargo-target pgwr-lm-target \

    --scope "Little Mac's forward smash family (neutral + charge + up/down angled) on Pyra c06/c07 reskinned to G&W, on the installed 0.20.15 baseline"



  # install. The cache is read from the package's own MANIFEST.json, so no

  # environment variable is needed; PGWR_CARGO_TARGET only overrides it.

  bash src/pgwr/install-to-card.sh --no-smashline

  ```



  `MANIFEST.json` carries `"cargo_target": "pgwr-lm-target"`, and `install-to-card.sh` resolves

  `PGWR_CARGO_TARGET` -> the manifest's `cargo_target` -> the feature-derived default, in that

  order. `--check` now also asserts the manifest's recorded cache is the one the NRO was read

  from. This exists because a packaging run on 2026-10-01 shipped another agent's stale NRO

  while still printing `PASS`; grepping the packaged binary for this move's own sound names is

  what caught it, and `check_handlers` in the audit now does that automatically.

- **Sources:**

  - ACMD: `src/pgwr/plugin/src/acmd/littlemac_attack_s4.rs` (registered `Priority::High`

    in `acmd/mod.rs`, over the generated G&W `AttackS4`/`AttackS4Charge`).

  - Animation/motion: `src/pgwr/tools/build_littlemac_fsmash.py`.

  - Effect bank: `tools/build_littlemac_fsmash_effect.py`.

  - Audit: `tools/audit_littlemac_fsmash.py` (v1.1.0).

  - Donor: `refs/littlemac_attack_s4/` - 18 files pulled live over arc-network, 0 failures

    (`dumps/arc/fighter/littlemac` is **empty on disk**, 0 of 4290 indexed files).

    Provenance and findings: `refs/littlemac_attack_s4/SOURCE.json`.

    Re-verify: `toolchains/py312/python.exe tools/fetch_arc_files.py --set littlemac_attack_s4 --check`.

  - Audit: `refs/littlemac_attack_s4/audit_0_20_14.json`, reproducible with

    `toolchains/py312/python.exe tools/audit_littlemac_fsmash.py --package builds/pgwr/0.20.14 --baseline builds/pgwr/0.20.13/ultimate/mods/pyra_gamewatch_reskin`.

- **What the port contains (all donor's own, no substitutions):**

  - His `attack_s4_s` and `attack_s4_hold` motion entries taken whole - cancel frame **44**

    against G&W's 43, flags 0x84 against 0x80 - and verified byte-for-byte in the built

    motion lists of both slots.

  - Two retargeted clips, `c03attacks4s.nuanmb` (52 frames) and `c03attacks4charge.nuanmb`

    (61 frames). Both names already exist on the recipient, so **no new motion file** and no

    motion `config.json` declaration.

  - Hitboxes, effects, rumble, slope and the charge `physics!` call, from his own

    `game_/effect_/sound_/expression_attacks4` and `..._attacks4charge`.

  - Sounds `se_littlemac_smash_s02` + `vc_littlemac_attack05`, merged into Pyra's c06/c07

    banks (`tools/merge_donor_sound.py`, which gained `DONOR_ROOTS` because his banks live in

    `refs/`). **No stand-in sounds** (rule 17).

  - `effect/fighter/littlemac/ef_littlemac.eff` shipped byte-exact and declared in

    `config.json` for `littlemac_attack_line`; both required emitters verified.

- **Measured fit:** 46 of his 50 bones survive onto the built 165-bone recipient, with **0

  parent mismatches**; the whole `Bust -> ClavicleC -> ClavicleR -> ShoulderR -> ArmR ->

  HandR -> HaveR` chain keeps identical parents and every hitbox is parented to `armr`.

  The 4 dropped bones are helpers (`H_ClavicleR/L`, `H_SholderR/L`).

- **Expected on-screen change:** G&W's prop (manhole cover / turtle / fishbowl) no longer

  appears on the forward smash, because his version spawned one and Little Mac's is a bare

  punch. That is the point of the port, not a regression.

- **Offline checks (all passed, none of them behavioural):** release compile clean;

  built == packaged NRO; donor motion entries byte-compared; clip retarget re-read after

  save; all four sound names resolve by `crc32(lower)`; effect emitters present; package

  validation; baseline delta = **4 files added, 4 intended overrides, 0 unexpected,

  0 removed**; and the packaged NRO carries all **15** handler names and all **4** sound

  names. **This says nothing about whether the punch plays, looks right or is audible, and

  nothing about whether the engine routes to the angled kinds.**

- **The angled forward smash, added in 0.20.16 - and why the earlier "blocked" verdict was wrong.**

  0.20.14 shipped only the neutral punch and the charge hold, on the argument that the angled

  variants were unreachable: Pyra/Mythra/G&W have no `attack_s4_hi`/`attack_s4_lw` motion

  kinds, the 39,156-entry const table has no `S4_HI`/`S4_LW`, and eflame's recovered status

  table registers exactly one smash status, so the clips "would be files the engine can never

  call" and a native hook would be needed (rule 17).

  **That inference was wrong, and the reasoning error is worth recording.** What is true is

  only that `attack_s4_hi`, `attack_s4_lw` and `hash40` of either appear **nowhere** in

  `main.bin` - 0 ASCII hits, 0 u64 hits across all 86,672,752 bytes. What does not follow is

  that they are unreachable, because of this measurement: **65 of the 72** fighters with a c00

  motion list on disk *do* carry both angled kinds, pointing at their own

  `c03attacks4hi`/`c03attacks4lw` clips, with the same `game_script` split

  (`game_attacks4`/`game_attacks4hi`/`game_attacks4lw`/`game_attacks4charge`). The 7 that lack

  the pair are `chrom diddy eflame elight gamewatch miiswordsman younglink`. A convention 65

  shipped fighters follow and 7 do not is **missing content, not a missing engine route** - and

  if the engine truly could not reach the angled kinds, those 65 entries would be dead weight

  in their own files, which they are not: Little Mac's angled forward smash is a real, working,

  played move in the base game.

  The missing `FIGHTER_STATUS_KIND_ATTACK_S4_HI` is likewise not evidence against it: the

  angled variants need no separate status, because **the motion-list entry carries its own

  `game_script` field**. A motion entry with no script registered for it is precisely a move

  that animates and hits nothing, which is why 0.20.16 registers all four handler sets rather

  than relying on the entry alone.

  All three parts of the mechanism are inside the mod - the motion entries from the pinned

  donor list, the clips from the retarget, the scripts from the plugin - so **no native hook

  is involved and rule 17 is not engaged.**

  **What remains open is tier D and is what this run tests:** whether the engine asks for the

  angled kinds on *this* recipient at all. A "no" costs nothing - an unrouted entry is inert -

  and a "yes" gives Little Mac's real angled f-smash. Evidence:

  `refs/littlemac_attack_s4/SOURCE.json` -> `angled_variants`.

  - `c03attacks4hi.nuanmb` / `c03attacks4lw.nuanmb` are **new file names** in each slot, so

    they are declared in `config.json`; the audit checks against the pristine export that the

    base game really lacks both the kinds and the clips, so "new" is measured, not assumed.

- **No new status ids.** This port takes no `0x1EE+` allocation; Pyra's next free id remains

  `0x208` (Snake reserves `0x1FB..0x207`). No framework plugin is touched.

- **Installer:** 0.20.14 was installed as `builds/pgwr/0.20.14/` on the user's explicit

  instruction, with framework installation OFF. Record

  `evidence/install-record-2026-10-01_002928.json`; automatic backup

  `evidence/sd-backups/sd-backup-20261001-002928` holds 0.20.13. Built/package/card NRO

  and all 1933 mod files verified byte-identical; protected framework plugins unchanged.

  Installed by the development agent **at the user's request**, which overrides the usual

  rule 23 split for that release only. **0.20.16 is not installed**; the development agent

  stages it and the user installs (rule 23).



**Test after designated installation** (no log is produced by this release; judge by eye and

return any crash report). Steps 1-8 are the 0.20.14 test, already passed; re-run them as a

regression check on 0.20.16. **Steps 9-12 are new and are the point of this release.**



1. Fresh boot. Confirm the game loads and the costume gate is intact.

2. **Vanilla negative control:** Pyra c00 and Mythra c00. Forward smash must be *unchanged*

   vanilla - no Little Mac animation, no new sound. Standalone Mr. Game & Watch on c06/c07

   must also be untouched vanilla.

3. c06 ground forward smash (side + B, no tilt). Expect: Little Mac's straight right-arm

   punch animation, **no G&W prop appearing**, a two-hit connect with his timing.

4. c06 hold B to charge, then release: expect his 61-frame charge wind-up (smoke, the

   charging shimmer, `rbkind_smashhold1/2` rumble) instead of G&W's charge pose.

5. c07: repeat steps 3 and 4. The clips and motion entries are byte-identical across c06/c07,

   so both costumes must show the same punch.

6. Hit a target with the forward smash on both c06 and c07. Expect his 20%/18% two-hit

   values and his own impact effects - **not** Pyra's sword explosion effect.

7. Sound check: the hit must play Little Mac's own smash sound and voice line, not a Pyra

   stand-in and not silence. Both were merged into Pyra's banks; a silent smash means the

   merge did not take and is a fail.

8. Regression sweep, all on c06 and c07: jab (Chrom + Cloud trail), forward air (Cloud

   trail), down tilt (R.O.B. speedlines), neutral-B (Snake grenade), side-B (Monkey Flip),

   up-B (G&W Fire), and **up smash and down smash, which are still G&W's and must be

   unchanged**.

9. **c06 up-angled forward smash** (forward + up + B, no tilt). Expect Little Mac's

   **upward** punch, his `littlemac_attack_arc` slash arc, and the higher-pitched

   `se_littlemac_smash_s03`. It must **not** be the neutral punch and must not be G&W's.

10. **c06 down-angled forward smash** (forward + down + B, no tilt). Expect his **low**,

    sweeping variant with the arc mirrored to his facing, hitting low (a crouching

    opponent should be hit), and `se_littlemac_smash_s04`. Note the down-angled one is

    deliberately his *weaker* move: 24% damage at 21 base knockback against the neutral

    20%/18% at 87, so it should feel like a low poke, not a finisher.

11. Charge the angled variants too (hold B, then release) - the charge hold is shared, so

    the wind-up should be his 61-frame shimmer in all three directions.

12. c07: repeat 9-11, and confirm **vanilla Pyra c00 and Mythra c00 angled forward smashes

    are untouched** - they must still be their own stock moves.



Fail criteria: forward smash still shows G&W's animation or spawns a prop; charge hold keeps

G&W's pose; no sound or Pyra's sword sound instead of Little Mac's; vanilla Pyra c00 or

standalone G&W changed; up/down smash changed; any new crash.



**On the angled variants, the one honest reading:** if steps 9-10 still show the *neutral*

punch, that is **not** a crash and **not** a regression - it is the tier-D open question

coming back negative, and it means the engine does not ask for the angled kinds on this

fighter. Everything else in the release still stands. If they show Little Mac's angled

punches with his arc and his own sounds, the variants work and the port is complete.



## Character Naming (c06 Ursula & c07 Wilhelmine) — Antigravity



**INSTALLED: 0.20.13 independently verified. TESTED 2026-10-02 (T-0056): the Ursula/Wilhelmine

naming was exercised on hardware by the user.** Updated 2026-09-30.



- Installed by the root designated installer as part of the collective 0.20.13 package; this

  section's two files are byte-identical to the staged package hashes recorded below

  (`6eae9fbc…` ui_chara_db.prc, `95d9c3f5…` msg_name.xmsbt).

- The R.O.B. dtilt package 0.20.12 deliberately kept the *old* name files via

  `PGWR_UI_BASELINE`; 0.20.13 is the deliberate installer decision to combine them, so

  0.20.13's mod tree is 0.20.12 plus exactly these two files (plus `info.toml` version).

- Verified offline on the card tree: 5 target entries route n06=6/n07=7, 40 xmsbt entries

  (URSULA/WILHELMINE 5 each, Ursula/Wilhelmine 15 each), 121 database rows unchanged, and

  standalone `ui_chara_gamewatch` still n06=n07=0. **These are offline results, not behaviour.**



- Target: Pyra/Mythra costume slots c06 and c07 (both Pyra/G&W and Mythra).

  - Costume c06: display name "Ursula" (CSS uppercase banner: "URSULA") regardless of whether Pyra (G&W) or Mythra is active.

  - Costume c07: display name "Wilhelmine" (CSS uppercase banner: "WILHELMINE") regardless of whether Pyra (G&W) or Mythra is active.

- Concrete Staged Package: `builds/pgwr/staged_names/`

  - `ui/param/database/ui_chara_db.prc`: sha256 `6eae9fbca490ff8bfacf13461bb54b97c804b34d62de43352867b3c045032f5c` (34,753 bytes)

  - `ui/message/msg_name.xmsbt`: sha256 `95d9c3f51caa54454778ae5b1ae2b07c2417af90156f9ef9575cad6408dabdb7` (3,365 bytes)

- Source Implementation:

  - Tool: `src/pgwr/tools/build_custom_names.py` (smoke test passed with `--check`).

  - Source Message Patch: `src/pgwr/ui/message/msg_name.xmsbt`.

  - Build Pipeline Integration: `src/pgwr/build.py` (`build_name_database()` & `build_names()`).

- Database & Message Mapping:

  - `ui_chara_db.prc`: Routes `n06_index -> 6` and `n07_index -> 7` across all 5 fighter database entries:

    `ui_chara_eflame_first`, `ui_chara_eflame_only`, `ui_chara_elight_first`, `ui_chara_elight_only`, `ui_chara_element`.

  - Layout index fields `c06_index` and `c07_index` remain 0 to preserve UI layout positioning.

  - Standalone `ui_chara_gamewatch` remains 100% untouched (`n06_index = 0`, `n07_index = 0`), guaranteeing vanilla Mr. Game & Watch on the roster is unaffected.

  - Costumes c00–c05 remain 100% untouched (`n00_index..n05_index = 0`).

  - `msg_name.xmsbt`: Generates 40 XML entries covering categories 0..3 (`nam_chr0` unlock, `nam_chr1` CSS portrait banner, `nam_chr2` battle/results HUD, `nam_chr3` CSS icon) for all 5 name IDs.

- Offline Checks:

  - `tools/build_custom_names.py --check` validation PASSED: verified 10 index rewrites, vanilla slot preservation, and exact XML labels.

  - PRC round-trip verification: non-target rows and vanilla tables match byte-for-byte.

- Test Instructions (when collectively installed):

  1. Boot game, navigate to CSS, select Pyra/Mythra slot.

  2. Select costume c06: verify CSS portrait banner displays "URSULA" and character name displays "Ursula". Toggle between Pyra (G&W) and Mythra; verify "Ursula" displays for both.

  3. Select costume c07: verify CSS portrait banner displays "WILHELMINE" and character name displays "Wilhelmine". Toggle between Pyra (G&W) and Mythra; verify "Wilhelmine" displays for both.

  4. Enter match / training mode on c06 and c07: verify HUD name and victory / results screen name display "Ursula" and "Wilhelmine".

  5. Negative controls:

     a. Select vanilla Pyra/Mythra costumes c00–c05: verify default "Pyra", "Mythra", and "Pyra / Mythra" names display normally.

     b. Select standalone Mr. Game & Watch (slot 26) on costumes c06 and c07: verify default "Mr. Game & Watch" displays normally.



## Hero side-B on Mythra c06/c07 - Claude (continuing Codex/Buffy work)



**INSTALLED: 0.20.15; hardware 2026-10-01: level 1 pass, level 2 blade bolt points down, level 3 fails** (`evidence/2026-10-01_pgwr_0.20.15/RESULT.md`). Re-tested by the user on 2026-10-02 (T-0056 marking), still with the same three verdicts. T-0052 (next subsection) supersedes "fixes in progress": its one behavioural fix and the Kazap discriminators are now **installed** in 0.20.17.



- Target: Mythra (`elight`) c06/c07 side-B becomes Hero's Zap / Zapple / Kazap, mana excluded

  (always the "success" branch). Owned statuses `0x1FA..0x1FE` on the elight table.

- Package `builds/pgwr/0.20.15/`, manifest `MANIFEST.json` (features `snake-neutral-b`, `hero-side-b`;

  cargo target `builds/.cache/pgwr-heroside-target`).

  NRO sha256 `7aa0ae2440e6604bf7b243209e2a5ff263e4e5bff1f7ab2a56b1e34da873feb4`;

  mod tree sha256 `ab74b4d0d5dbf7e7abb80846d95b58b175c6fe0aba54a7699d32b9fc7eeb2e9f` (1979 files).

  Built NRO == packaged NRO; `package_pgwr_release.py --check` passes.

- Baseline: the installed 0.20.14 source (verified against its MANIFEST source hashes) + this change only.

  Delta vs 0.20.14: +46 files (24 Mythra body clips, 16 spark/lightning article motion lists c00-c07,

  3 Hero trail textures in `effect/fighter/elight/trail_c06` and `trail_c07`); changed: both Mythra c06/c07

  `motion_list.bin`, both `ef_elight_c06/c07.eff` (16 Hero side-B emitter sets appended after neutral-B's),

  `config.json`, `info.toml`. Nothing removed. Sounds: none new (neutral-B already merged all Hero banks + brave.sqb).

- Rebuild: `PGWR_SNAKE_NEUTRAL_B=1 PGWR_HERO_SIDE_B=1 python src/pgwr/build.py`; then

  `cargo skyline build --release --features snake-neutral-b,hero-side-b` with

  `CARGO_TARGET_DIR=builds/.cache/pgwr-heroside-target` (build-plugin.sh has no flag for this yet); then

  `tools/package_pgwr_release.py --version 0.20.15 --snake-neutral-b --hero-side-b --cargo-target pgwr-heroside-target`.

- Source: `src/pgwr/plugin/src/mythra/hero_side_b/` (Cargo feature `hero-side-b`, off by default).

  Fighter statuses translated from the pinned Hero NRO decomp; spark/lightning Lua statuses and scripts owned in

  Rust (hitboxes checked against native code); effect/sound/expression from the dump's success branch.

  Native: the previous agent's signature-checked owned copies at `0x85d580`, `0x85dad0`, `0x33cbb20` plus the

  Mythra receiver slot `main+0x4fb2110` (`receiver.rs` header records it as user-approved 2026-10-01; the

  older TODO entry says pending - **user, please confirm; if not approved, do not install**).

  No framework plugin change.

- Tier D / known deviations (need the console):

  1. Kazap's switch to the finishing slash is triggered when the owned lightning bolt reaches its collision

     distance (replaces Hero's native "has the bolt struck" link-event query).

  2. Sword flare effect uses Hero's costume-4 variant (`brave_lightning_swordflare4`); the real per-costume

     mapping lives in the game's main executable, unmeasured.

  3. Trail uses Hero's textures/offsets with Mythra's own 14.5 tip; alignment unverified.

  4. 57 of 125 animated Hero bones (mantle/skirt/shield/scabbard) have no Mythra bone and are dropped.

- Crash-tail log: `sd:/ultimate/pgwr_hero_s_log.txt` (independent of global logging).



Test after designated installation (send `pgwr_hero_s_log.txt` and `pgwr_log.txt` **from boot**, plus any new

`sd:/atmosphere/crash_reports/` file):



1. Boot. Require `[PGWR-HERO-S] BOOT v0.20.15`, `[PGWR-HERO-S] READY EVENT Mythra +0x170 ...`,

   `[PGWR-HERO-S] READY native three approved interceptions...`, `[PGWR-HERO-S] ARTICLES spark=.. lightning=..`

   and `[PGWR-HERO-S] REGISTERED c06/c07 statuses=0x1fa-0x1fe mana=off`. Any `FAIL` line = stop.

2. Vanilla control: Mythra c00 side-B is her normal Ray of Punishment; no `[PGWR-HERO-S] ENTRY` line.

3. Mythra c06 (or Pyra c06 then down-B), tap side-B vs a CPU: short Zap (charge <9 frames). Expect

   `ENTRY`, `TRANSITION 0x1fe->0x1fa`, on hit `TARGET ...` then `SPAWN spark ... count=1` and `SPARK special_s1`.

4. Hold side-B ~0.5 s: Zapple (`->0x1fb`, `SPARK special_s2`), medium flash at 9 frames of charge.

5. Hold side-B until the max flash: Kazap (`->0x1fc`), `SPAWN lightning`, `LIGHTNING arrived`, `->0x1fd`

   (finishing slash), `SPARK special_s32` if it hits. Note if the lightning looks/hits right.

6. Repeat 3-5 in the air (air clips, slight hop on the Kazap finisher).

7. Repeat 3-5 on c07.

8. Listen: charge sound + voice, Zap/Zapple/Kazap voice lines, spark sounds. Note any silence.

9. Watch the sword: lightning sword/flare effects and trail; note misalignment (tier D items 2-3).

10. Regression: Mythra c06 neutral-B (Hero fireball) and up-B (Hero spin) still work; G&W side (Pyra c06) unchanged.



Pass: 3-7 run through without a stuck state, crash, or `FAIL` line, and 2 is vanilla. Fail: crash (send the

report), stuck in a side-B status, `FAIL ...` lines, missing `LIGHTNING arrived` (Kazap never finishes), or T-pose.



### T-0052 (2026-10-02) — Zapple orientation fix + Kazap trace — Buffy



#### T-0052 retry, 2026-10-02 — READY, needs a designated installer (version 0.20.18)



**The 0.20.17 part is installed and has been run.** The card log arrived

(`evidence/2026-10-02_pgwr_T-0052/pgwr_hero_s_log_card2_2026-10-02.txt`, sha256

`ff7afc8cdef4dacd692c050eba6064967023078210c3acb2c61e5f853d94e48f`, 3066 lines,

`BOOT v0.20.17`), and it **settles** the Kazap question rather than narrowing it:



- 15 Kazap attempts, 30 bolts, every stage reached (activation, spawn, the bolt's own

  states, MapCorrection ~900 frames).

- **Cause (a) measured:** all 32 `BOLT` samples read `move_dist=0.0` against

  `threshold=300.0` with `owner_ok=true`. The engine does not accumulate

  `FLOAT_MOVE_DIST` for this cloned article on Mythra; the arrival predicate could never

  fire at any threshold. Cause (b), the null owner, is excluded.

- **The bolt does not move** — its position is byte-identical for its whole life

  (`y = 85.0 = param_special_s.offset_y_lightning`, its spawn point). This refutes the

  earlier "travel excluded" wording; see graveyard R-HERO-S-7.

- **The donor's own lightning event `0x214e64eedd` arrives 30 times for 30 bolts**, with

  the owner in the third attack — the very signal `state.rs` says the owned flag replaces.



**Behavioural change (exactly one, rule 11):** `receiver.rs` raises the owned

`LIGHTNING_ARRIVED` flag when that event arrives, once, gated on our own `ATTACK3` and our

own per-move bolt count; all three suppression reasons are logged. No donor work id, no

invented distance, no new interception (the `Mythra +0x170` slot was already patched).

`weapon.rs`'s distance predicate is deliberately **unchanged**.



**Diagnostics only:** `bolt_work()` prints the bolt's own `FLOAT_HEAD`/`FLOAT_TAIL`/

`FLOAT_DIR` next to `MOVE_DIST` at Main and in each bounded `BOLT` sample, so the next log

decides whether the donor extension machinery writes them. Nothing about travel is changed.



- **Version:** `0.20.17` -> `0.20.18` (`src/pgwr/plugin/Cargo.toml`).

- **Built NRO:** `62c36331435fbefa247a18699aa90c151f0a09aa5e7804c806697afceb09ee7e`

  (466944 B) at

  `builds/.cache/pgwr-heroside-target/aarch64-skyline-switch/release/libpyra_gamewatch_reskin.nro`,

  features `snake-neutral-b,hero-side-b`, clean in 17.69s. Installed 0.20.17 NRO is

  `22bfbd01421280f61c15bdde54b9674df87e9beeccd28108f3a1bdeef960f901`. **NEW binary — the

  delta is not asset-only**, so install without `--reused-nro`.

- **Build command note:** use an absolute `CARGO_TARGET_DIR`, or `../../../builds/.cache/`

  from `src/pgwr/plugin`; `../../builds/` resolves to `src/builds/`.

- **Not packaged, not installed** (rule 23). Files touched: `mythra/hero_side_b/receiver.rs`,

  `weapon.rs`, `Cargo.toml` — the `script_acmd.rs` Zapple fix from the first run is unchanged.

- **Evidence:** `evidence/2026-10-02_pgwr_T-0052/RESULT-0.20.18.md`,

  `log_audit_card2.json`, `kb/findings/the-donor-link-event-was-the-arrival-signal-all-along.md`.

  Tool `tools/audit_hero_side_b_log.py` 1.1.0 (`--smoke` pins both card logs + 3 negative controls).

- **Unverified: all behaviour.** Whether the finisher now plays is tier D; nothing was run

  in game.



**Manual checks after designated installation** (send `sd:/ultimate/pgwr_hero_s_log.txt` **from boot**):



1. Boot. First line `[PGWR-HERO-S] BOOT v0.20.18` — that string is how you know this build is under test. Same four READY/REGISTERED lines. Any `FAIL` = stop.

2. Vanilla control: Mythra c00 side-B is her Ray of Punishment; no `[PGWR-HERO-S] ENTRY`.

3. No-regression: c06 tap side-B (<9 frames) → `TRANSITION 0x1fe->0x1fa`, `SPAWN spark ... count=1`, `SPARK special_s1`.

4. **Zapple (verdict still owed from 0.20.17):** hold to ~0.5 s; the blade's forward lightning must point **forward**. `->0x1fb`, `SPARK special_s2`.

5. **Kazap (the new change):** hold to the max flash. Require `->0x1fc`, `ACTIVATE lightning frame=10`, `SPAWN lightning`, `BOLT ...`, then `EVENT begin kind=0x214e64eedd`, **`EVENT arrival kind=0x214e64eedd bolts=N frame=F`**, then `APPEND lightning arrived; switching to the finisher`, then `TRANSITION 0x1fc->0x1fd`, **and the finisher must visibly play**.

6. If step 5 instead shows `EVENT arrival suppressed: owner is not in the third attack`, `... no bolt counted for this move`, or `EVENT arrival already raised; ignored`, report which one — each is a distinct gate, not a vague failure.

7. Report the `BOLT` `head=`/`tail=`/`dir=` numbers and whether `x`/`y` change over the bolt's life. Constant → the extension machinery never writes them. Growing → the bolt extends and only `MOVE_DIST` is missing.

8. Repeat 3-5 in the air, on both facings, and on c07.

9. Regression: Mythra c06 neutral-B and up-B; Pyra c06 side-B unchanged; Snake neutral-B and Monkey Flip untouched.



#### T-0052 first run — INSTALLED in 0.20.17 by the T-0056 designated installer



**INSTALLED 2026-10-02 in 0.20.17 by the T-0056 designated installer, together with T-0053.

The user has since run it; see the retry section above for what the log showed.** NRO on

the card: `22bfbd01421280f61c15bdde54b9674df87e9beeccd28108f3a1bdeef960f901` (built from

the same source in `builds/.cache/pgwr-T0056-target`, features

`snake-neutral-b,hero-side-b`). The built NRO named below is that run's earlier

verification build, superseded by it. The `BOLT` diagnostics live in

`pgwr_hero_s_log.txt`, which is written independently of the `logging` feature, so they

**did** appear. Record: `evidence/2026-10-02_pgwr_T-0056/INSTALL.md`.



- **Baseline:** installed 0.20.16 (`81460e74...`, tree `06bacd78...`, 1983 files) plus these edits only.

- **Behavioural change (exactly one, per rule 11):** `script_acmd.rs` `effect_2` —

  `brave_lightning2_swordspark` on `sword1` now uses `rot_z = -90` instead of `0`. It was

  the only `sword1`-attached lightning emitter in the whole file not using `-90`; level 1

  uses the same joint and emitter family at `-90` and is the user's working control.

  Hero's `Sword1` bind basis differs from Mythra's by that much

  (`refs/brave_special_s/skeleton_bones.md` s4). **Tier D until hardware** — still unverified.

- **Diagnostics (no behaviour change):** `BOLT life=/move_dist=/threshold=/owner_ok=/x=/y=`

  sampled at `life%5` and `life<=2` and logged **before** the arrival branch; `ACTIVATE

  lightning frame=10`; `APPEND lightning arrived; ...`; and a line for the

  arrived-but-no-owned-state case. These exist because the old `LIGHTNING arrived` line sat

  *after* a null-able owner lookup, so two different faults both logged nothing. **They did

  their job:** see the retry section.

- **Built NRO:** `5051e5815ac85c0aa2c5bfe4c18151c9b667ddfdee76fdf5e9619624cd038096`

  (466944 B) at `builds/.cache/pgwr-heroside-target/aarch64-skyline-switch/release/libpyra_gamewatch_reskin.nro`,

  features `snake-neutral-b,hero-side-b`, no errors. Superseded on the card by `22bfbd01...`.

- **Rebuild caveat:** the documented relative `CARGO_TARGET_DIR=../../builds/.cache/...`

  resolves to `src/builds/` from `src/pgwr/plugin`. Use `../../../builds/.cache/...`, or an

  absolute path.

- **No new hook, no new status, no mana.** Existing approved receiver sites untouched.

- **Evidence:** `evidence/2026-10-02_pgwr_T-0052/RESULT.md` + `log_audit.json`; card log

  archived with sha256. Tool `tools/audit_hero_side_b_log.py` v1.0.0 (`--smoke`).

- **The Kazap blocker was localised but NOT fixed in this run** — superseded by the retry

  section above.

- **Installer:** done on 2026-10-02 - combined with T-0053 in 0.20.17 after checking that the

  two diffs touch disjoint files (`mythra/hero_side_b/*` against `status/{monkey_flip,special_hi}.rs`).

  Pending work (T-0050) was not included.



## R.O.B. down tilt (AttackLw3) on G&W c06/c07 — Claude



### T-0036 custom animation — 2026-10-01



**INSTALLED 2026-10-02 by the T-0042 designated installer. TESTED 2026-10-02 (T-0056): exercised

on hardware by the user. Those clips (`d30722b5...`) were superseded on the card an hour later

by T-0048's recipe 3.0.0 clips (`06fb085e...`) inside 0.20.17, so whatever the verdict was, it

described an animation that is no longer installed - the T-0048 checks below are now the live

ones.**

Exclusive shared-build/metadata reservation was lab `state/pgwr-shared-build.lock`, owner

T-0036; concurrent research handoffs owned their refs only. No automated tests/Ryujinx.

The lock file no longer exists, so no other agent holds the build now.



- **Installer note (2026-10-02), needed to reproduce this install.** `builds/.cache` had

  been pruned, so the installer's "built NRO exists and equals the staged one" check could

  not run for an asset-only variant that reuses the installed NRO verbatim. Rather than

  fake a cache, `install-to-card.sh` gained `--reused-nro`, which **replaces** that check

  with a stronger one: the staged NRO must be byte-identical to the NRO already on the

  card. Verified with a negative control (a one-byte-tampered copy was refused, with and

  without the flag). Use `--reused-nro` for asset-only variants; drop it and rebuild into

  the cache named by `MANIFEST.json` for anything that carries a new NRO.



- Package: `builds/pgwr/0.20.16+robot-dtilt.4/`; core/plugin/info version 0.20.16,

  custom recipe 2.0.0. Complete baseline retained; only both `c02attacklw3.nuanmb`

  change (1983 mod files). No framework plugins changed. Do not merge pending research.

- NRO reused unchanged: `81460e74313350aaf569ce832045e8586387ab4ddf10e51bfdb690a8d29ef834`.

  Mod tree: `66e3bc5e2c5f174271fd6d14f2dc3c4f6de4b7ca171f73382f3019d59b20b3f0`.

  Both clips: `d30722b5763f7b6e4f9e4d834cf57b91b69befccd5eb4321f8fbf3bdc81f6d19`.

  Manifest: `39aedf1cbaa6a0bfb6a7fc8239b870641696f6c6e4793fb4c3de8effa104a469`.

  Baseline manifest had stale hashes for these two clips only; actual baseline and

  preservation details are recorded in `evidence/2026-10-01_pgwr_T-0036/REVIEW.md`.

- Source: `src/pgwr/tools/build_robot_dtilt.py`,

  `src/pgwr/assets/robot_dtilt/recipe.json`; `build.py` changes only a comment.

  Dependencies: baseline built recipient skeleton/idle and pinned R.O.B. timing clip/list.

  No input blocker for this stage. Full from-dump rebuild unavailable (`dumps/arc` absent);

  Rust compilation unnecessary for asset-only variant; unique reserved cache

  `builds/.cache/pgwr-T-0036-target`. No card access/install attempted.

- Generation command from mod root:

  `python -B src/pgwr/tools/build_robot_dtilt.py --baseline builds/pgwr/0.20.16 --package builds/pgwr/0.20.16+robot-dtilt.4 --stage-only --preview`.

  Draft stages .2 and .3 remain superseded; deletion was blocked by policy. Recipe and source hashes in manifest;

  detailed report/preview `evidence/2026-10-01_pgwr_T-0036/`.

- B evidence: 165 recipient transform tracks, 29 samples/end 28; no unreachable IK

  targets; idle foot anchors; recovery at 15; only five idle body meshes enabled.

  Byte preservation includes complete donor motion entry (cancel 15), c06/c07 routing,

  frame-3 attack/frame-4 clear gameplay, donor effects/sounds/rumble and all other moves.

  D/unverified: mesh deformation, palm alignment to the full donor hitbox, slopes,

  facing mirroring and recovery feel. Joint preview supplies no hardware verdict.



Manual checks after designated installation (three checks):



1. Compare stock R.O.B. grounded down tilt as timing control. Confirm Pyra c00 still

   has vanilla down tilt, appearance and sounds. Core boot banner remains 0.20.16 if

   logging is enabled; absence of logs is normal with this unchanged silent NRO.

2. On c06 and c07, whiff/hit grounded down tilt facing both directions on level ground.

   Judge coherent crouch, torso/arms/legs, low palm strike at frame 3, hand/hitbox

   alignment, donor effects/sounds/rumble, idle recovery/cancel 15 and no manhole props.

3. Repeat both costumes/facings on upward/downward slopes; watch foot sliding,

   floor clipping and pose/recovery. Spot-check jab, angled forward smashes, fair,

   Snake neutral-B and Pyra/Mythra swap. Send console judgment/screenshots and any

   boot log or `atmosphere/crash_reports/` report if a regression occurs.



Pass is the user's console judgment of pose/alignment plus unchanged controls;

fail is malformed pose, visible props, changed timing, vanilla regression or crash.



### T-0048 stretched-arm animation variant — 2026-10-02



**INSTALLED 2026-10-02 in 0.20.17 by the T-0056 designated installer, together with T-0052 and

T-0053. Console appearance and hand/hitbox alignment remain unverified; the user judges this

one in game.** Both clips on the card are `06fb085e...` (verified by hash after install); the

package's other NRO, `libone_slot_eff.nro`, is unchanged. No automated tests, no Ryujinx.



- **Target:** the same R.O.B. down tilt, re-authored so both arms thrust forward and low by

  roughly one standing G&W body height, with the frame-3 hands inside the donor's own capsule.

  Recipe 3.0.0 replaces recipe 2.0.0's IK wrist goals. Design input was subtask T-0047's record

  `evidence/2026-10-02_pgwr_T-0045/T-0047_design_record.md`.

- **Why the old pose fell short:** 2.0.0 asked `solve_limb` for wrist goals about 5.2x the

  recipient's arm length (measured arm span 3.9477 L / 3.9641 R). `solve_limb` clamps to the

  link reach, so the unreachable part of each goal was silently dropped and frame 3 peaked

  short of the capsule. 3.0.0 removes the arms from that IK entirely and deforms each arm as a

  rigid block rooted at `Shoulder{L,R}`: rotate the shoulder onto the recipe's aim direction,

  then slide it along that direction until the hand sits `arm_reach * H` from the fighter's

  origin (`H` = 12.8334 model units, the skinned visible body height). Anchoring to the origin

  rather than to each arm's own idle hand is what lets one shared recipe value put both hands

  in the same place; the left arm hangs further back at rest.

- **Package:** `builds/pgwr/0.20.16+robot-dtilt.5/`, core 0.20.16, animation recipe **3.0.0**.

  Staged from the latest complete approved baseline `builds/pgwr/0.20.16+robot-dtilt.4`

  (confirmed as the current card state at execution time). The superseded `.2`/`.3` drafts were

  not used and no asset was rebuilt.

  - Mod tree `a976ff51bc04c69fefbbd758ee779a0ca25904f9d175d015cbf09d4c4dc0d491` (1983 files).

  - Both clips `06fb085e436a7e49862f1c64223afd6c659cc68c35ae55f8b99a2f6443f22060`

    (baseline `d30722b5...`).

  - `MANIFEST.json` `ef1246962b3e8e0651b5cf3723037c3f1072c1a099b1b2f3000270800b7a4aaa`;

    generation report `robot_dtilt_custom.json`

    `d39df6bcfbc368136ec8aac4ce010a04f8cf39cc5696894d48407e1d6eaf23b0`; preview PNG

    `0f37622cc6937baceed6864dc403429bf52f2129f40aa957abd9b3f0ed4d16a8`.

  - Source: `src/pgwr/tools/build_robot_dtilt.py`

    `c724cdfbc9e143127c2f2cff008810e1c2f8e1a1dcea29250f36e221373f418c`,

    `src/pgwr/assets/robot_dtilt/recipe.json`

    `457de008153b8cd1ea90bda900300223579e8bed3bb062707074a4edea8d35b1`. `build.py` unchanged;

    `retarget()` and `deploy_for_slot()` keep their signatures, so the full-build path is

    unaffected.

  - Reserved cargo target `builds/.cache/pgwr-T-0048-target` (recorded only; no Rust build was

    needed). Shared-build reservation: lab `state/pgwr-shared-build.lock`, owner **T-0048**,

    taken when free and refused when another task held it, released on exit.

- **Generation command from the mod root:**



  ```bash

  python -B src/pgwr/tools/build_robot_dtilt.py \

    --baseline builds/pgwr/0.20.16+robot-dtilt.4 \

    --package  builds/pgwr/0.20.16+robot-dtilt.5 \

    --stage-only --preview

  ```



- **Preserved, verified offline:** 1983 files in and out, **0 added, 0 removed**, and exactly

  two changed - `fighter/eflame/motion/body/c06/c02attacklw3.nuanmb` and its `c07` twin. Both

  packaged NROs are byte-equal to the baseline (`libpyra_gamewatch_reskin.nro`

  `81460e74313350aaf569ce832045e8586387ab4ddf10e51bfdb690a8d29ef834`, `libone_slot_eff.nro`

  `e6e5659de3c95a3ff8484f87bd8ef1c129f6c563290903f9f8b8e95177dda70b`); the staging script now

  *refuses* a package whose NROs differ rather than merely recording that they were reused.

  Gameplay, the donor's complete `attack_lw3` motion entry (flags 0x80, cancel 15), c06/c07

  routing, the costume gate, `config.json`, donor effects/sounds/rumble, the frame-3 active /

  frame-4 clear timing and the 28-frame duration are all unchanged - none of those files moved.

  Feet stay planted with zero IK shortfall; all 165 bones keep explicit tracks including the

  grafted helpers; visibility is still the recipient idle's, so no manhole.

- **Transform serialization, changed as required.** `decompose()` splits any 3x3 into an

  orthonormal rotation plus a positive axis-aligned scale, `quaternion()` orthonormalizes

  first, and the emitted transform carries the bone's measured scale instead of a hardcoded

  `[1,1,1]`. This recipe still scales nothing, so hand/head/body proportions are preserved by

  construction and the invariant is *checked*: `scale_written_max_deviation` 2.7e-15.

- **Measured frame 3 (identical for c06 and c07):** hands at `(0.269, 2.596, 16.115)` and

  `(-0.327, 1.902, 15.990)` - 1.52 / 0.92 body heights forward of each arm's own idle

  position, 1.25 body heights forward of the fighter, near the ground. Both are **inside** the

  donor capsule (`r` 3.4, `(0,1.7,21)` to `(0,7,9)`), by 2.21 and 1.53 units from its surface.

  The capsule is parsed out of `robot_attack_lw3.rs` at run time (`0e91f1de...`), not copied.

  Peak at frame 3, hold at 4, retraction through 6/8/12, and exact idle recovery at frame 15

  (max bone displacement 4.87e-07).

- **D/unverified:** how the stretched arms look as mesh, and whether the palms line up with what

  the engine actually evaluates. The rigid block preserves the fist's size exactly, but whether

  a shoulder slid ~9 units forward reads as a stretch or as a detached arm cannot be measured

  offline. Facing mirroring, slopes, foot sliding, floor clipping and recovery feel are all

  untested. The joint preview renders no mesh and gives no hardware verdict. Note frames 1, 2

  and 4 also place hand geometry inside the capsule; gameplay is unaffected (the ACMD still

  activates on frame 3 and clears on frame 4) but it is stated rather than left to be found.

- **Evidence:** `evidence/2026-10-02_pgwr_T-0045/T-0048_animation_record.md`;

  finding `kb/findings/reach-beyond-limb-length-is-not-an-ik-problem.md`.

- **Installer:** done. The `.5` asset tree was carried into the new release `0.20.17` (which

  also carries T-0052 and T-0053 in its NRO), so it went on with

  `MGW_PACKAGE=builds/pgwr/0.20.17 src/pgwr/install-to-card.sh --no-smashline` and *without*

  `--reused-nro`, because that release carries a new binary.



Manual checks for the user, in this order (all on c06 and c07, both facings):



1. **Vanilla negative control:** Pyra c00 and Mythra c00 down tilt unchanged, and standalone

   Mr. Game & Watch on c06/c07 untouched. Stock R.O.B. down tilt in a separate run as the

   timing reference.

2. c06 grounded down tilt on level ground, whiffing: does the crouch read as coherent, do both

   arms thrust forward and **low, roughly a body height out and near the ground**, and does it

   look like a stretch or like a detached arm? This is the judgement only you can make.

3. Same whiff facing the other way - is the pose mirrored correctly, with no left/right mix-up?

4. Hit a target: the palm contact should land on the hitbox at frame 3, low. Report 5% damage

   at angle 361, the R.O.B. swing/impact sounds and his voice, the speedline effects, and no

   manhole cover.

5. Repeated down tilts: does the return to idle look natural, and is input actionable at frame

   15 with nothing stuck?

6. Upward and downward slopes: watch for foot sliding, floor clipping and the same pose issues.

7. Regression sweep: jab, forward air, fair, Snake neutral-B, Pyra/Mythra swap, and Little

   Mac's angled forward smashes.



Pass is your console judgment of the pose and the palm/hitbox alignment plus unchanged controls;

fail is a malformed or detached-looking pose, a visible prop, changed timing, a vanilla

regression, or a crash (send any new `sd:/atmosphere/crash_reports/` file).



### Historical installed package record (superseded animation; retained provenance)



**INSTALLED: 0.20.13 independently verified. TESTED 2026-10-02 (T-0056): exercised on

hardware by the user, then superseded by the T-0036 and T-0048 down-tilt packages.**

Updated 2026-09-30.



- Installed by the root designated installer as part of the collective 0.20.13 package.

  The 0.20.13 mod tree is byte-identical to the checked 0.20.12 tree for every R.O.B. dtilt

  file (both `c02attacklw3.nuanmb`, both motion lists, the `se_*`/`vc_*` banks and

  `eflame.sqb`); the only differences are `info.toml` and the two naming files.

- The plugin NRO was recompiled for 0.20.13 from an isolated source copy so the build stays

  exactly on this feature set; `acmd::robot_attack_lw3` is present and the known tier-D

  retarget risk (11 of 82 donor nodes) is unchanged.



- Target: G&W replacing Pyra c06/c07; replaces G&W's manhole-cover down tilt. Mythra and c00-c05 untouched.

- Concrete package: `builds/pgwr/0.20.12/`; manifest `MANIFEST.json`; delta audit `ROBOT_DTILT_DELTA.json` there.

- NRO sha256 `e8bf3f0713489bad278e937c8a22baa8498ce393761dee94940d35734303165c`.

  Mod tree sha256 `3854a891f94b0591240526a0d47aede0ab7ed4f940e5b1dd64eba090e4f3f1ee` (1932 files).

- Baseline: the installed 0.20.11 (Snake neutral-B feature kept on, logging off, names exactly as

  installed via `PGWR_UI_BASELINE`). Build with `PGWR_SNAKE_NEUTRAL_B=1 PGWR_UI_BASELINE=builds/pgwr/0.20.11/ultimate/mods/pyra_gamewatch_reskin`,

  then `build-plugin.sh --snake-neutral-b --stage-only`, then `tools/package_pgwr_release.py --version 0.20.12 --snake-neutral-b`.

  Stage with `--snake-neutral-b --stage-only`. No new Cargo feature, no new status ids, no config.json change.

- Delta vs 0.20.11 (audited): 18 changed files, none added/removed: both `c02attacklw3.nuanmb`, both

  motion lists (only the `attack_lw3` entry), `se_eflame_c06/c07` and `vc_eflame_c06/c07` (append-only),

  `eflame.sqb` (+1 record), `info.toml`. **Names: this package keeps the installed 0.20.11 name files;

  the newer Ursula/Wilhelmine patch (Antigravity section) is NOT included.** Combine with it only as a

  deliberate installer decision (rebuild without `PGWR_UI_BASELINE`).

- Donor material (live-extracted read-only, hashes in `refs/robot_attack_lw3/extraction.json`): `c02attacklw3.nuanmb`,

  motion list (entry: cancel frame 15, flags 0x80), `se_robot_c00`, `vc_robot_c00`, `robot.sqb`. ACMD: WuBoytH dump

  `lua2cpp_robot/robot/AttackLw3.txt` (tier C). Sources: `src/pgwr/plugin/src/acmd/robot_attack_lw3.rs`,

  `src/pgwr/tools/build_robot_dtilt.py`, `tools/merge_robot_dtilt_sound.py`, `tools/audit_robot_dtilt_delta.py`.

- Sounds (exact donor tones, no stand-ins): `se_robot_swing_m`, `se_robot_attackhard_L01`, `se_robot_landing01`;

  voice `vc_robot_attack01..04` through the donor's `seq_robot_rnd_attack` record.

- **Known risk (tier D):** only 11 of R.O.B.'s 82 animated nodes exist on G&W's skeleton (root, hip, neck,

  clavicles, shoulders, hand anchors). Legs and forearms get no track and may show rest pose or look wrong.

  Hitboxes are on `top`, so the hit itself does not depend on the pose. No bone mapping was invented.

  Tier D as well: the donor dump's colour-tint branches are read from text with lost braces; c06/c07 use

  the donor's colour-6/7 speedline tints; R.O.B.'s region-flag branch is not carried (other fighter's work id).

- Dependencies/blockers: none open. Not combined with Hero side-B or any pending work.



Test after designated installation (keep `sd:/ultimate/pgwr_log.txt` from boot; Snake's own log stays separate):



1. Fresh boot; require `[PGWR] BOOT v0.20.12` (global logging is off, so absence of other lines is normal).

2. Vanilla control: Pyra c00 down tilt is her normal move (no R.O.B. kick, no robot voice).

3. Pyra c06, ground down tilt (stick down + A): a single low kick, hit at about frame 3, no manhole cover

   appears. Record what the body does (pose, legs, arms) — this is the open question above.

4. Same on c07.

5. Hit a target: 5% at angle 361, low-height hit, kick impact sound. Listen for the R.O.B. swing/impact

   sounds and the R.O.B. voice (one of four takes) on each use; note if any are silent.

6. Whiff and check the recovery: input is actionable at frame 15 (donor cancel) and nothing is stuck.

7. Regression on c06: jab, forward tilt, up tilt, down smash, grab still G&W/Chrom as before.

8. Regression: Snake neutral-B still boots (`[PGWR-SNAKE-N] BOOT v0.20.12`) — unchanged from 0.20.11's test.



Pass: steps 3-6 behave as described on both costumes with the vanilla control unchanged. Fail: manhole cover still

appears (old G&W script won), T-pose/collapsed body, silence where sounds are listed, stuck/endless animation, a

new crash (report `sd:/atmosphere/crash_reports/`). A collapsed body alone is the known retarget risk, not a crash.



## Collective installation record



2026-10-02, Freebuff designated installer (task T-0042), user request: "build and install

all pending changes onto the switch in E: and tell me what to test". Installed the only

genuinely pending item, **T-0036's R.O.B. down-tilt custom animation**, as package

**0.20.16+robot-dtilt.4**. NRO `81460e74313350aaf569ce832045e8586387ab4ddf10e51bfdb690a8d29ef834`

(unchanged - asset-only change, no recompile); mod tree

`66e3bc5e2c5f174271fd6d14f2dc3c4f6de4b7ca171f73382f3019d59b20b3f0` (1983 files). Delta

against the previously installed 0.20.16 is **exactly the two `c02attacklw3.nuanmb`

clips**, `d30722b5763f7b6e4f9e4d834cf57b91b69befccd5eb4321f8fbf3bdc81f6d19`. Automatic

backup `evidence/sd-backups/sd-backup-20261002-002850`. Framework installation OFF;

protected plugins byte-unchanged. Record

`evidence/2026-10-02_pgwr_T-0042/INSTALL.md`, `evidence/install-record-2026-10-02_002850.json`.



- **The Little Mac 0.20.16 section was stale and has been corrected.** The card already

  held 0.20.16 (NRO and all 1983 files verified equal) before this run, installed

  2026-10-01 without this file being updated. Nothing was reinstalled for it, and its

  **angled up/down forward smashes remain untested on hardware** - that is the single

  most important thing in the test below.

- **Regression control run before installing:** the Little Mac forward-smash motion

  entries and the packaged NRO's handler/sound names were decoded in both the candidate

  and the installed 0.20.16 tree, and the results are identical. So installing T-0036 did

  not disturb the forward smash.

- **Two pre-existing installer defects were found and fixed, both of which had been

  blocking this install** (see `src/pgwr/install-to-card.sh`): the volume scan used

  `ls -d /[a-z]`, which returns nothing in Git Bash on Windows, so **card autodetect

  could not find the card on this machine at all**; and there was no way to install an

  asset-only variant once the cargo cache was pruned. Anyone who tried to install

  anything here before this run would have hit the first one.

- **Not evidence about behaviour.** Bytes are proven; nothing here says the down tilt

  looks right or that the game boots. No console run, no emulator, no tests - benched.

  Logging is off in this build, so no game log is written; its absence is not a fault.



2026-09-30, root designated installer, user requested "build and install all pending updates"

and confirmed that **Hero side-B and the Little Mac forward smash must not be included yet**.

Installed both READY sections as one package **0.20.13**: **R.O.B. down tilt (AttackLw3)** and

**Character Naming (c06 Ursula / c07 Wilhelmine)**, retaining the installed 0.20.11 baseline

with Snake neutral-B still enabled. NRO `57128f65b667d574ad6da54fff353e8e200b1b98afbbb4e6b3407b9ba33622ae`;

mod tree `2fcfaa992a62dca741e5bd3dfc5cfcad53b1d24f173bd0939a5aadf051b0f31d` (1932 files);

built/package/card NRO and all 1932 mod files independently hash-verified equal. Manifest

`builds/pgwr/0.20.13/MANIFEST.json`; record `evidence/install-record-2026-09-30_235634.json`;

automatic backup `evidence/sd-backups/sd-backup-20260930-235634` holds 0.20.11. Framework

installation OFF; the four protected plugins are byte-unchanged (smashline still

`5f4091ee…`).



- **Combination note (rules 11 and 23).** This is a deliberate collective install of two READY

  changes, not an attribution-isolating test: a failure does not by itself identify which of the

  two caused it. The two are file-disjoint (R.O.B. touches motion/sound; naming touches two UI

  data files), and 0.20.13's delta against 0.20.12 is exactly `info.toml` plus those two name

  files, so a controlled follow-up is straightforward.

- **Concurrent-agent handling.** Another agent was building 0.20.14 (Little Mac forward smash)

  in the same tree during this install: it had bumped `Cargo.toml` to 0.20.14 and wired the

  f-smash into both `build.py` and the plugin. Its `builds/pgwr/0.20.14/` has no plugin NRO and

  no MANIFEST, so the f-smash is **not** built and was excluded, as the user directed. To avoid

  editing another agent's live inputs (rule 23), the 0.20.13 NRO was compiled from

  `scratch/2026-09-30_installer/plugin` (a copy of `src/pgwr/plugin`) with the f-smash module,

  consts and install call removed. The live tree, `build.py` and the other agent's

  `pgwr-snake-target` cache NRO (`b73337b7…`) were left exactly as found; the cache NRO was

  restored after install. `src/pgwr/plugin/Cargo.toml` in the live tree is the other agent's

  0.20.14 and was not reverted.

- **Two build failures were self-inflicted and are not defects.** Early attempts raced: a

  timed-out `build.py` was still running, and two detached copies wrote the same output tree,

  producing a spurious `tone name collision` and a missing-file error. Both cleared after

  killing the stray processes; a single clean asset build exited 0 (1942 files). Do not read

  those errors as toolchain problems.

- Hardware test pending; use the combined test in the two included sections (names first, then

  the R.O.B. dtilt steps), and return `sd:/ultimate/pgwr_snake_log.txt` **from boot** plus any new

  `sd:/atmosphere/crash_reports/` files.

- **Card removed after verification.** The install completed and was independently hash-verified

  while the card was still mounted; the SD card was then unplugged/ejected, so the card can no

  longer be re-read from this machine. Re-insert it before the hardware test. If the card is

  re-inserted showing 0.20.11 instead, re-run

  `MGW_PACKAGE=<root>/builds/pgwr/0.20.13 src/pgwr/install-to-card.sh --no-smashline`; note that

  this compares against `builds/.cache/pgwr-snake-target`, whose NRO is the other agent's

  `b73337b7…`, so stage this package's NRO there first (the installer only reads that path).



2026-09-30, root installer, user requested 0.20.7 by replying ?ready?. Included only **Monkey Flip aerial side-B lock ? root**; pending Snake registration/assets not included. No shared rebuild was needed: the checked 0.20.7 NRO/tree were installed unchanged, with current manifest source hashes matching. Manifest/hashes are above; automatic backup `evidence/sd-backups/sd-backup-20260930-130439` holds 0.20.6. Install record `evidence/install-record-2026-09-30_130439.json` confirms built/package/card NRO equality, 1701 mod-file matches and unchanged protected plugins. Hardware test pending; next test linked from the included section.



2026-09-30, installer, user requested installation of Cloud sword trail along with any other potentially pending changes. Installed **Cloud Forward Air Custom Sword Trails (c06 & c07)** while retaining **Monkey Flip aerial side-B lock**; pending Snake neutral-B registration/assets remain uninstalled per queue. Built package 0.20.8; NRO and 1709 mod files byte-verified on card. Automatic backup `evidence/sd-backups/sd-backup-20260930-134152` holds 0.20.7. Install record `evidence/install-record-2026-09-30_134152.json` confirms card/built NRO equality, 1709 mod-file matches, and unchanged protected plugins. Hardware test passed.



2026-09-30, installer, user requested collective installation of 0.20.9. Installed **Chrom Jab Custom Cloud Sword Trails (c06 & c07)** while retaining **Cloud Forward Air Custom Sword Trails** and **Monkey Flip aerial side-B lock**; pending Snake neutral-B registration/assets remain uninstalled per queue. Built package 0.20.9; NRO and 1709 mod files byte-verified on card. Automatic backup `evidence/sd-backups/sd-backup-20260930-142122` holds 0.20.8. Install record `evidence/install-record-2026-09-30_142122.json` confirms card/built NRO equality, 1709 mod-file matches, and unchanged protected plugins. Hardware test passed.



2026-09-30, installer, user requested installation of 0.20.10 silent performance build ("now do the install"). Installed **Silent Performance Build (Diagnostics & Logging Silenced)** while retaining **Chrom Jab Custom Cloud Sword Trails**, **Cloud Forward Air Custom Sword Trails**, and **Monkey Flip aerial side-B lock**; pending Snake neutral-B registration/assets remain uninstalled per queue. Built package 0.20.10; NRO and 1721 mod files byte-verified on card. Automatic backup `evidence/sd-backups/sd-backup-20260930-145657` holds 0.20.9. Install record `evidence/install-record-2026-09-30_145657.json` confirms card/built NRO equality, 1721 mod-file matches, and unchanged protected plugins. Hardware test pending.



2026-09-30, root designated installer, user requested "install now". Installed **Snake neutral-B — Codex continuation** as checked 0.20.11, retaining the installed 0.20.10 baseline. No other new READY sections; Hero side-B and other pending work excluded. NRO and all 1932 mod files independently hash-verified; protected framework plugins unchanged. Record: `evidence/install-record-2026-09-30_222459.json`. Automatic backup: `evidence/sd-backups/sd-backup-20260930-222459` (holds 0.20.10). Hardware test pending; use the nine-step Snake test above.



## Build-only collective batch console-89c7baa998178f244493 — 2026-10-02



**TESTED 2026-10-02 (T-0056): this batch's payload is what was on the card and was exercised by

the user; it is now superseded by 0.20.17.** Reused coherent versioned

package `builds/pgwr/0.20.16+robot-dtilt.4/`; no package mutation or new Rust binary.

Included custom R.O.B. down tilt and complete 0.20.16 baseline (Little Mac angled

forward smashes, Snake, Monkey Flip, Cloud/Chrom trails, silent core, Hero moves

and Ursula/Wilhelmine names). T-0042 uses this same payload; its installer fix

is completed workspace tooling, not a console artifact. Research/PENDING work,

superseded .2/.3 drafts, suggested followups and protected frameworks excluded.



Local hash inventory: 1983/1983 files equal MANIFEST; no extras/missing files.

NRO `81460e74313350aaf569ce832045e8586387ab4ddf10e51bfdb690a8d29ef834`;

tree `66e3bc5e2c5f174271fd6d14f2dc3c4f6de4b7ca171f73382f3019d59b20b3f0`;

manifest `39aedf1cbaa6a0bfb6a7fc8239b870641696f6c6e4793fb4c3de8effa104a469`.

NRO equals local baseline and historical T-0042 installation hash. Cache is pruned;

no fresh compile/reproducibility claim. Only substantive manifest source difference

is T-0042's completed installer fix; 82 others are CRLF/LF only. No unfinished

runtime or asset source changes detected. Evidence:

`evidence/2026-10-02_pgwr_console-89c7baa998178f244493-build/VERIFY.json`.



**No connected device read or written in this phase.** Prior card records above

remain historical. Next installer uses `src/pgwr/install-to-card.sh` with

`--no-smashline --reused-nro`, automatic backups/staging/comparison/rollback;

refuse if current card NRO differs. No tests/emulator; behavior still unverified.

Combined numbered console checklist is in VERIFY.json and the lab result JSON.





## T-0050 ? Little Mac fist effect-bank merge (2026-10-02)



**INSTALLED 2026-10-02 in 0.20.19 (banks taken from this section's generated output; see `evidence/2026-10-02_pgwr_0.20.19/INSTALL.md`). Hardware test pending.** Before that: READY as source. Both blockers are gone; see `evidence/2026-10-02_pgwr_T-0050/RESULT.md`

for the measurements. Not packaged, not installed, no console run.**



*What changed since the BLOCKED note above:* the vanilla recipient

`effect/fighter/eflame/ef_eflame.eff` (11,371,400 B, sha256 `24512f9a020f…`) is readable in

the export named by `paths.toml [dumps] arc`, and the effect converter is rebuilt from its

pinned open-source commit instead of a lost binary.



### Inputs and where they came from



| what | value |

|---|---|

| EffectLibrary source | `https://github.com/KillzXGaming/EffectLibrary` @ `d5491138d645221ec92189eeff3ded8c43fd0a1a` (MIT), cloned to `refs/brave_special_n/effect_library/`, tree sha256 `fcba90ba8938…`. Fetch/verify with `python tools/fetch_effect_library.py --check` |

| converter build | `python tools/build_hero_effect_converter.py --from-source` -> `builds/.cache/hero_effect_converter/bin/` (gitignored). `EffectConverter.exe` sha256 `033ddc923fb3…`, `EffectLibrary.dll` `ebd94ba49c78…`, plus `HeroTextureRename.exe` and `HeroModelRename.exe` |

| converter SDK | the machine's .NET 8 SDK, project-local: source copy, `obj/`, `bin/` and the NuGet folder all live under `builds/.cache/hero_effect_converter/`. Nothing installed system-wide |

| donor bank | `refs/littlemac_attack_s4/arc/effect/fighter/littlemac/ef_littlemac.eff`, 13,795,840 B, sha256 `c2f33cdb2157…` (unchanged) |

| vanilla recipient | read-only from the export; never copied into the tree, never written |



The one source edit beyond the pinned preservation patches: upstream

`EffectConverter/Program.cs` does not compile (it uses `PtclFile`, which lives in

`EffectLibrary.EFT2`, without importing it). The old relink route never noticed because it

compiled only `EffectLibrary.dll` against a prebuilt converter. One added `using` fixes it.



### What the merge produces (measured, tier B)



Both slot banks are byte-identical to each other and are, for both slots:



    effect/fighter/eflame/ef_eflame_c06.eff   sha256 6ab84bb729d8…

    effect/fighter/eflame/ef_eflame_c07.eff   sha256 6ab84bb729d8…



95 vanilla eflame emitters preserved, 2 added (`LITTLEMAC_ATTACK_LINE`,

`LITTLEMAC_ATTACK_ARC`), 0 lost. Re-export compared field by field against the staged tree:

every decoded emitter field, every opaque subsection, every geometry/texture/shader payload

byte-identical.



**Defect found and fixed while doing this (would have shipped silently):** the merge only

relocated *texture* ids. `LITTLEMAC_ATTACK_ARC` carries a G3PR model whose id `1347192488` is

also used by a **different** Pyra mesh, and `PrimitiveInfo.AddPrimitive` returns silently when

an id already exists - so the arc would have drawn Pyra's model instead of Little Mac's.

`merge_hero_neutral_b_effects.py` is now 1.2.0: it relocates model ids as well as texture ids,

renames the `.bfres` and its model name, and rewrites exactly the three fields that name a

model (`ParticleData.PrimitiveID`, `ParticleData.PrimitiveExID`, `ShapeInfo.PrimitiveIndex`).

`1347192488` -> `95091467`, name -> `pgwr_hero_95091467`.



### What the installer must run



```bash

cd mods/ssbu_mod_new

# 1. the pinned converter source (already present; this only verifies it)

python tools/fetch_effect_library.py --check

# 2. the repaired converter (writes only into builds/.cache/)

python tools/build_hero_effect_converter.py --from-source

# 3. cheap input smoke test

python tools/build_littlemac_fsmash_effect.py --check

# 4. the normal asset build - this is what produces both slot banks.

#    MGW_EXPORT must be a full export; the default dumps/arc does not exist here.

MGW_EXPORT=<full export> PGWR_SNAKE_NEUTRAL_B=1 PGWR_HERO_SIDE_B=1 python src/pgwr/build.py

```



No `Cargo.toml` version bump is needed for the effect part: **no Rust changed**. The

installer still has to do the combined build for slots 2 and 3, and should keep whatever

version bump their changes imply.



`src/pgwr/build.py` already called `littlemac_s4_eff.build(MOD, …)` and declared

`effect/fighter/eflame/ef_eflame_{slot}.eff` per costume group (that wiring landed with

T-0050 on `lab/T-0050` and is already in the working tree). After the build:



```bash

python tools/audit_littlemac_fsmash.py --package builds/pgwr/<version>

python tools/effect_trail_inventory.py builds/pgwr/<version>/ultimate/mods/pyra_gamewatch_reskin

```



Expected: inventory shows `eflame: banks ['ef_eflame_c06.eff', 'ef_eflame_c07.eff']` and

`littlemac: banks []`; the audit passes check 5 and the baseline delta shows the two new

banks as **additions** plus `config.json`, with 0 unexpected changes.



`check_effect` has two negative controls, both run and both refusing: the 0.20.16 package

(fails: the donor-folder bank is still shipped) and a slot bank replaced by the vanilla bank

(fails: lacks `LITTLEMAC_ATTACK_LINE`).



### Manual console checks (12 steps, with controls)



Vanilla control is **Pyra c00 and Mythra c00 forward smash**, which must look exactly as it

does today - that is the check that the per-costume bank did not leak into the vanilla slots.

The visual donor control is **real Little Mac**, whose neutral line and angled arcs are what

c06/c07 should now match.



1. Boot fresh. Keep `sd:/ultimate/pgwr_log.txt` from boot, and `atmosphere/crash_reports/`

   on any crash. Confirm the banner version.

2. **Vanilla control:** Pyra c00 and Mythra c00 forward smash. Unchanged animation, sound,

   hitbox, no arc, no missing G&W effects.

3. Pyra c06, neutral forward smash, facing right. A thin straight *line* draws from the fist

   at ~frame 13 and lasts as long as the punch. Pass = the line appears and reads as Little

   Mac's, not as a white flash.

4. Same, facing left. Pass = the line appears in both facings.

5. Pyra c06, neutral forward smash **fully charged** (hold the button through the charge).

   Pass = the line still draws, and the charge hold behaves as before.

6. Pyra c06, up-angled forward smash (forward + up), both facings. A curved *arc* sweeps

   from the fist and retires about frame 18 - it must not linger. Pass = arc appears and is

   gone before the recovery pose.

7. Pyra c06, down-angled forward smash (forward + down), both facings. Same arc, different

   path, retiring about frame 21. The two facings must use the two *different* arc poses

   (the donor's `SO_VAR_FLOAT_LR` branch); if both look identical, the branch is not running.

8. Repeat steps 3-7 on Pyra **c07**. Pass = c07 matches c06.

9. Put c06 and c07 in one match, repeat 3-7, then transform to Mythra and back and repeat.

   Pass = the trail follows the slot, survives the transform, and does not stick to the

   wrong one.

10. **Interrupt check:** start a forward smash and get hit, land, or change state part-way

    through. Pass = no leftover line or arc in the recovery.

11. **Item and neighbour control:** hold an item and forward-smash - the item must stay

    hidden and the trail must still appear. Then check unrelated G&W effects (jab, Cloud

    fair, smash charge, entry, up-B props) and Mythra's Hero effects, before and after

    repeated forward smashes. Pass = nothing missing or altered. A missing G&W prop or

    Pyra sword effect here means the slot bank replaced rather than merged.

12. **Donor control:** on real Little Mac, compare the neutral line and both arcs. Pass =

    c06/c07 look like the same effects he gets.



Fail signs: no line and no arc on any angle (the bank is not being loaded - check the

inventory first); an arc that never retires; arc present but visibly the *wrong* mesh;

any unrelated c06/c07 effect missing.



**Tier D, not claimed anywhere:** whether the line and arcs actually draw on screen, whether

the angled kinds are even requested by the engine on this recipient (unchanged open question

from 0.20.15/0.20.16 - a negative answer is inert, not a regression), and every appearance

judgement above. Nothing in this section was run on hardware.



### Blockers and dependencies



None outstanding. Depends on nothing from slots 2 and 3 and overlaps no Rust module, so it

merges cleanly with them. Files touched: two new files under

`effect/fighter/eflame/`, a removed `effect/fighter/littlemac/ef_littlemac.eff`, and

`config.json`. The pinned donor in `refs/` stays (it is the merge donor and the provenance).

No vanilla `ef_eflame.eff` override, no protected-plugin change, c00-c05 and standalone

Mr. Game & Watch untouched.



## T-0054 - eflame c06/c07 trail resource ownership (2026-10-02)



**PENDING / candidate staged, not READY.** Branch `lab/T-0054`. Source changes:

`src/pgwr/tools/build_cloud_trail.py` (`build_eflame_trail_folder`), `build_color_themes.py`

(calls it). Staged trail folders only (not a package): `builds/pgwr/T-0054-candidate/effect/fighter/eflame/trail_c06|c07`

(10 files each, was 14). Full build not run (inputs absent/benched). Delta, loader reading and

manual matrix: `refs/cloud_attack_air_f/T-0054/RESOURCE_OWNERSHIP.md`. Independent of T-0050 bank;

merge cleanly with it. Cause of the two-player symptom and hardware result UNVERIFIED.

## Snake up tilt (AttackHi3) on G&W c06/c07 - Freebuff slot 2 (2026-10-02)



**INSTALLED 2026-10-02 in 0.20.19 (staged with this section's tools on the 0.20.17 tree; combined delta audit PASS). Hardware test pending.**



**READY to be combined into the collective build; NOT packaged by me and NOT installed.**

Everything below is tier B offline evidence (compiles, byte-equal, audits pass). Nothing

here says how the move looks or hits: no console, no emulator, no automated test (rule 8).



### What this change is



G&W (Pyra c06/c07) uses Snake's up tilt instead of his own, on those two costumes only.

Four parts, all owned by this mod (rule 17):



| part | source | file |

|---|---|---|

| game/effect/sound/expression scripts | Snake's own `AttackHi3` text dump, tier C, pinned at `refs/snake_attack_hi3/donor_acmd/` | `src/pgwr/plugin/src/acmd/snake_attack_hi3.rs` |

| animation | Snake's `c02attackhi3.nuanmb` retargeted onto the **built** c06/c07 skeleton | `src/pgwr/tools/build_snake_uptilt.py` |

| timing | Snake's raw `attack_hi3` motion entry, whole: **cancel frame 38**, flags **0x84**, `game_script` `game_attackhi3` | same tool + `src/pgwr/build.py` |

| sounds | `se_snake_attackhard_h01` + the `seq_snake_rnd_attack` record, which selects `vc_snake_attack01..04` (measured out of the record by CRC32, not assumed) | `tools/merge_snake_uptilt_sound.py` |



`AttackHi3` is a vanilla status kind, so **no new status id** is allocated; the next free

Pyra id stays `0x208`. Gated by `set_costume(crate::TARGET_COSTUMES)` on the same agent as

every other override, registered at `Priority::High` over the generated G&W `AttackHi3`

(rule 18).



### Pinned sources (hashes)



| file | sha256 |

|---|---|

| `refs/snake_attack_hi3/arc/.../c02attackhi3.nuanmb` | `f5151e106cbf78764159adf326e36e761d1800dfa189c06cfd77bfd76d9f5f71` (45,760 B) |

| `refs/snake_attack_hi3/arc/.../motion_list.bin` | `b70e42ca1e6ea143301349e268af5a7e98d391d0321a39c79a4187ef6fd39c34` (45,740 B) |

| `refs/snake_attack_hi3/donor_acmd/snake__AttackHi3.txt` | `99cc3499cfa39bfc...` (7,070 B) - WuBoytH/SSBU-Dumped-Scripts @ `59004685238a3f6f93bae905d3a4e079701c40b4` |

| `refs/snake_attack_hi3/donor_acmd/robot__AttackLw3.txt` | `65b13e7c00a04a1d...` (6,629 B) - the **control**, see below |

| `refs/snake_grenade/arc/.../se_snake_c00.*` | `88057e12...` / `4e09776a...` / `8692a0a7...` |

| `refs/snake_attack_hi3/arc/.../vc_snake_c00.*` | `12d080d0...` / `b8a677da...` / `d8280363...` |

| `refs/snake_grenade/sequence/.../snake.sqb` | `90370dcfeaed1e27498c1eaf4dc6e2a64d03d79e6a2df8ac1daa7f45df44ce0b` |



**The ACMD text was re-pinned, because the tree it used to live in is gone.**

`projects/pgwr/TODO.md` cites

`dumps/scripts/SSBU-Dumped-Scripts-main/smashline/lua2cpp_snake/snake/AttackHi3.txt`, but

`dumps/scripts/` in this workspace holds only `ParamLabels.csv` and

`gamewatch_motion_list.yml`, and the external export named by `paths.toml` `[dumps] arc`

has almost no files in it. Approximating the script is forbidden by rule 17, so the same

pinned commit the project already uses (`refs/brave_special_n/acmd_pin.json`,

`tools/fetch_donor_acmd.py`) was fetched again and hashed. R.O.B.'s `AttackLw3.txt` came

from the same commit as a **control**: the shipped `acmd::robot_attack_lw3` was written

from exactly that file, so reading the two side by side is what establishes how much the

dump loses (R.O.B.'s loses braces around its region-JP branch and prints an `is_excute`

inside an `else`; Snake's AttackHi3 has **no** branch, no article call and no work-id

write, so nothing had to be dropped).



### Measured offline (tier B)



* Motion entry: cancel **38**, flags **0x84**, blend 0, `game_script` `0xef3bca119`

  (`hash40("game_attackhi3")`), animation `0x138caf3e29` (`hash40("c02attackhi3.nuanmb")`).

  Raw entry sha256 `3c1cd8b9e4094a1e2a9569bfb5371522b5a98b6d1534dfbcf52200c698bede21`.

* Clip: 87 transform nodes -> **77 kept** on the built recipient, 10 dropped (`FaceN` and the

  nine `S_Bandanna*` nodes), **0 case-only matches**, Visibility replaced by the recipient

  idle's 98 nodes, Material group dropped. 48 frames.

* **The leg chain carries the kick** (this is the R.O.B. down-tilt failure the user

  rejected, so it is measured and asserted, not assumed): against the recipient idle,

  `LegL` 92.6 deg / `LegR` 78.0, `KneeL` 97.8 / `KneeR` 80.6, `FootL` 102.6 / `FootR` 54.4,

  `ToeL` 0.0 deg but 0.59 units of translation, `ToeR` 7.1 deg / 0.59 units.

  `deploy_for_slot` refuses to write if any of the eight is static.

* Sound merge: `se_eflame_c06/c07` **543 tones retained byte-for-byte**, exactly

  `se_snake_attackhard_H01` appended; `vc_eflame_c06/c07` **240 retained**, exactly

  `vc_snake_attack01..04` appended; `eflame.sqb` **13 records retained**, the

  `seq_snake_rnd_attack` record appended (14 total). The sequence append is idempotent: a

  record already present is compared byte-for-byte with the donor, never duplicated.

* Plugin: compiles with `cargo skyline build --release --features snake-neutral-b,hero-side-b`

  in cache `builds/.cache/pgwr-fb-2-snake-up-tilt-target`, no errors.

  NRO `75deff8de447f8f4d171539d8791f046e5c190a60901b05b5ec9ddef809dc313`, 466,944 B,

  and it carries `game_attackhi3`, `effect_attackhi3`, `sound_attackhi3`,

  `expression_attackhi3`, `se_snake_attackhard_h01`, `seq_snake_rnd_attack`,

  `sys_attack_arc_b`, `sys_turn_smoke`, `rbkind_attackm`.

* Delta audit passes against the **installed 0.20.17**: 18 changed files, 0 added,

  0 removed, 0 outside the up-tilt set, `attack_hi3` the only motion-list change in either

  slot, banks and sqb append-only, no c00-c05 file in the delta. Three negative controls

  fire (unchanged baseline; `--combined` on an exact delta; one clip reverted).

  Report: `evidence/2026-10-02_pgwr_snake_uptilt/SNAKE_UPTILT_DELTA.json`; sound report:

  `snake_uptilt_sound.json`.



**Not claimed:** anything about how it looks, hits, connects or feels. No console, no

emulator, no automated test.



### Installer: exactly what to run



No new Cargo feature (it is unconditional, like `robot_attack_lw3` and

`littlemac_attack_s4`). Version is already `0.20.18` in `plugin/Cargo.toml` - do not bump it

again unless another agent has.



```bash

# from mods/ssbu_mod_new, with MGW_EXPORT pointing at the full export

python src/pgwr/build.py

python tools/audit_snake_uptilt_delta.py --baseline 0.20.17 --version <new version>

# if other slots' changes ride along in the same build:

python tools/audit_snake_uptilt_delta.py --baseline 0.20.17 --version <new version> \

    --combined "<which other changes>"

```



Expected from `build.py`: `snake_uptilt` in the per-slot `build_motion` record with

`legs_all_moving: true` and `motion_entry.cancel: 38`, and `snake_uptilt_sound` in the

asset record with `retained_tones` 543 (se) / 240 (vc). `python tools/merge_snake_uptilt_sound.py --check`

runs the merge plus its negative control offline and needs no package.



Do **not** copy my cache NRO in: it was built from the live source tree while the other two

slots were mid-edit. Build once, from the finished tree.



### Manual console test (12 steps, vanilla control included)



Vanilla control is **Pyra c00** (and a real Snake if the user has one in the lab) plus

**Pyra c06/c07 before this build** - i.e. compare against the 0.20.17 G&W up tilt the user

already knows.



1. Boot fresh and open the log from boot. On this build the only expected new marker is

   nothing: global `logging` stays off, so judge this run by eye and by the crash-report

   folder, not by log lines.

2. **Vanilla control:** Pyra c00, do the up tilt five times. It must be Pyra's own up tilt,

   unchanged, with the sword out. Nothing about it should look like a kick.

3. Pyra c06, up tilt five times. Pass: a **high leg kick**, no manhole, no G&W prop, and the

   blue arc sweep + turn smoke appear from above. Fail: G&W's old up tilt, or no kick at all.

4. Pyra c07, same five times. Pass: same kick, same arc, on the gold costume.

5. Timing: the move must stay out of hitstun recovery noticeably **longer** than G&W's up

   tilt - cancel frame 38 against G&W's shorter one. Watch that you can act out of it

   around frame ~38 and not before.

6. Hit a training dummy with the kick. Pass: three boxes, `ATTACK_REGION_KICK`, the arc

   effect on connect. Fail: no hit, or the boxes in the wrong place (see step 9).

7. Sound: pass = one Snake hard-attack hit sound plus a Snake attack grunt (a voice line

   that is **not** Pyra's). Fail: silence, or Pyra's own up-tilt sound.

8. Rumble: pass = a light `nohitm` rumble at the start and a distinct `rbkind_attackm`

   hit rumble at frame 6; it must feel like a kick, not like G&W's arm.

9. **Hitbox placement - the open question.** Snake's script parents boxes on `top`, `kneel`

   and `legl`; the built c06/c07 skeleton has none of those three names (it has

   `LegL`/`KneeL`, and `top` is a built-in anchor G&W's own up tilt already uses). This was

   left exactly as the donor wrote it on purpose. Pass: the boxes sit at the kick. Fail: the

   boxes sit at the fighter's origin or nowhere sensible. If it fails, that is the single

   thing to change next, and the ACMD module says so.

10. Facing: kick left and kick right; both must aim the same way relative to the facing, and

    the arc must mirror. Slopes: kick on a slope, boxes must stay on the ground side.

11. Regression sweep on c06 **and** c07: jab, down tilt, forward smash, up-B Fire, side-B

    Monkey Flip, up air. All must behave exactly as on 0.20.17 - this change touches only

    `attack_hi3`, its clip and two banks.

12. Return `sd:/ultimate/pgwr_log.txt` from boot, and any new

    `sd:/atmosphere/crash_reports/` file. Crash = revert to 0.20.17 and report (rule 10).



Fail signs: G&W's own up tilt still plays; the up tilt is silent; the leg chain holds rest

pose; the move cancels far too early; a crash report newer than the install.



## Hero mana (MP) for the c06/c07 Pyra/Mythra pair - Freebuff slot 3 (2026-10-02)



**INSTALLED 2026-10-02 in 0.20.19 without `hero-mana-reserved`. Hardware test pending.** Before that: the playable mana system is READY. Recovery-on-hit remains reserved and disabled. The fighter HUD now has an explicitly authorized

separate feature and READY candidate in the Codex takeover section above. Nothing here needs a new asset file

or a new status id - it is Rust only, so it merges into the collective build with zero

asset delta.**



### Why the mana was not working (the answer, with evidence)



It was written with mana off, not broken. The Hero moves hard-wired the donor's

affordability gate to "always yes" and never kept an MP value. In the tree this task

started from: `hero_neutral_b/fighter.rs` logged `mana=off`; `hero_side_b/fighter.rs` said

"Mana is excluded by the user's instruction: SUCCESS_SP is always true";

`hero_neutral_b/donor_params.rs` said "Mana prices excluded"; `hero_side_b/params.rs` said

"no mana fields"; `lib.rs` announced "Hero neutral-B without mana". T-0046/T-0049 changed

the specification but stopped at BLOCKED waiting for the numeric PRC values, and those

values turned out to be the only input the implementation needed.



### What ships



One MP meter per player, owned by the plugin, shared by both halves of the pair and

therefore surviving the down-B swap: the table is keyed by the entry/player slot and both

`eflame` and `elight` are accepted for a c06/c07 entry. Neutral-B and side-B are the only

things that spend it. Hero Spin and every other move are untouched.



Donor numbers, all measured out of the pinned donor `vl.prc` (sha256 `dafa43c6...`), not

remembered: **max 100**, N1/N2/N3 = **6 / 16 / 36**, S1/S2/S3 = **8 / 18 / 42**, passive

recovery **+1 every 60 frames**, hit and shield multipliers 0.8 each (read, not applied -

see blockers). The gate is the donor's: `price <= mp` decides, and the debit happens

**only** on success, once per cast, at the donor's own sites - neutral-B's SHOOT MAIN, and

side-B's ATTACK1/2/3 MAINs. The Kazap finisher does not spend a second time, exactly as in

the donor's call list.



Out of MP is the donor's out of MP, not a silent no-op: the motion plays, nothing is spent,

and no projectile / no sparks / no lightning is created, because those are the paths the

donor itself gates on `SUCCESS_SP`.



Reset to full on `DEAD` / `REBIRTH` / `ENTRY`, once per stock, and on the first frame of a

new match, so a rematch cannot inherit the last stock's MP. Passive recovery pauses while

a spell is charging - the donor's own `DISABLE_SP_AUTO_RECOVER` behaviour - and while the

meter is full.



### Log



Always on, independent of the `logging` feature: **`sd:/ultimate/pgwr_mana_log.txt`**, one

line per event and never per frame, capped at 4000 lines per boot (it prints `BUDGET` once

when it trips). Lines: `REGISTERED` at load with every number and every Hash40 key, `INIT`,

`RESET`, `CAST`, `SPEND`, `REFUSE` with the shortfall, `RECOVER`, `DEBIT-SUPPRESSED`,

`STOCK-END`, and one `TICK` line per 60 frames carrying the observed frame rate. Request

this file **from boot**.



### Sources, hashes, dependencies



| item | value |

| --- | --- |

| code | `src/pgwr/plugin/src/mythra/hero_mana/{mod.rs,params.rs,logging.rs}` (+ `damage.rs`, `hud.rs`, feature off) |

| edits | `mythra/mod.rs` (3 lines), `hero_neutral_b/{mod.rs,fighter.rs}`, `hero_side_b/{mod.rs,fighter.rs}`, `plugin/Cargo.toml` (one new feature), `lib.rs` banner wording |

| evidence | `refs/brave_special_n/T-0057/{SOURCE.md,hero_mana_params.json,reserved_sites.json}` |

| donor param | `fighter/brave/param/vl.prc`, 18,685 B, sha256 `dafa43c6...`, from `gamedata/ssbu-13.0.4/data.arc` sha256 `ef615e67...` |

| tools | `tools/dump_hero_mana_params.py` v1.0.0, `tools/audit_hero_mana_native.py` v1.0.0 (both new, both read-only) |

| 13.0.4 image | `gamedata/ssbu-13.0.4/main.bin` sha256 `f70c97d2...`; all 9 reserved sites MATCH |

| my compile check | NRO 471,040 B, sha256 `1189bd1cb551c2901e5b6b005759dd04b5cc187ccd6b9d500261a507440ee565`, cache `builds/.cache/pgwr-fb-3-mythra-mana-target`, features `snake-neutral-b,hero-side-b` |

| status ids | none new - reuses the Hero `0x1F5..0x1F9` and `0x1FA..0x1FE` blocks |

| new assets | none - **zero asset delta** |



`hero-mana-reserved` is a new Cargo feature and is **off by default**; the installer must

not pass it. Three feature sets were compile-checked - `snake-neutral-b,hero-side-b` (the

ship one), `snake-neutral-b` alone, and `snake-neutral-b,hero-side-b,hero-mana-reserved` -

and all three compile.



### Blockers (not built, not approved)



1. **The fighter HUD gauge.** Explicitly authorized 2026-10-03; source and checked package now READY via `hero-mana-hud`. It calls the measured native selector/SP functions without installing a hook. See the Codex takeover section and `refs/brave_special_n/hud_route/SOURCE.md`; runtime remains unverified.

2. **Recovery on being hit or blocking.** Reserved: the recipient owns no path that

   observes this fighter being hit, and the donor's is at `main+0x854610` / `0x854a4c`

   (byte-verified) with the event ABI unrecovered. Rewarding from our own projectile hit,

   or every frame from a "was hit" flag, would both be wrong, and neither is implemented.



### Build steps for the designated installer



Nothing special - this is Rust only, so the normal collective build covers it:



    # 1. the usual combined plugin build, all tasks' changes in the tree

    CARGO_TARGET_DIR=<mod repo>/builds/.cache/<your-cache> cargo skyline build --release \

      --features snake-neutral-b,hero-side-b -- --offline

    # 2. the usual asset build and packaging

    python src/pgwr/build.py

    python tools/package_pgwr_release.py --cargo-target <your-cache> ...

    # 3. the usual install

    MGWR_PACKAGE=builds/pgwr/<version> src/pgwr/install-to-card.sh --no-smashline



Flags: `hero-mana-reserved` **must not** be passed. The version bump in

`src/pgwr/plugin/Cargo.toml` and `info.toml` belongs to the installer - I did not touch

either. I did not run `build.py`, the packager, `install-to-card.sh` or Ryujinx, and did

not touch the SD card.



### Manual console test (12 steps, vanilla control included)



Vanilla control: **Mythra c00** and **real Hero** in the same match. Both must behave

exactly as before, and neither may produce a `[PGWR-MANA]` line.



1. Boot fresh and pull `sd:/ultimate/pgwr_mana_log.txt` **from boot**. Pass: the first

   line is `[PGWR-MANA] REGISTERED max=100.0 recover_frame=60 recover_sp=1.0 ...` and it

   names the prices. Fail: no such file, or `max=` anything but 100.0.

2. **Vanilla control:** Mythra c00, use neutral-B and side-B ten times. Pass: no MP

   anywhere, no meter behaviour, and not one `[PGWR-MANA]` line for that player. Real

   Hero: his own MP bar untouched.

3. Pyra c06, swap to Mythra with down-B. Pass: a `TICK` line appears

   (`... frames=60 mp=100.0/100.0 pause=0x0`) about once a second while Mythra is active,

   and `form=` says `mythra`. Fail: no TICK lines at all - the per-frame hook is not

   firing, so recovery is not running either; report that first, it invalidates 4-8.

4. **Initial value:** on a fresh stock the log must show `mp=100.0/100.0`. Fail: anything

   else.

5. **Neutral-B level 1** (tap B, release early, press B again to shoot). Pass: one

   `CAST ... price=6.0`, one `SPEND entry=N form=mythra label=N1 price=6.0 100.0 -> 94.0`,

   and the fireball appears. Fail: a `SPEND` with no `CAST`, a wrong price, or no

   projectile after a successful `SPEND`.

6. **Neutral-B levels 2 and 3** (hold longer): pass = `price=16.0` and `price=36.0`, meter

   down by exactly those. Real Hero control: his N1/N2/N3 cost the same 6/16/36 on his own

   bar, which is the number to argue with if these look wrong.

7. **Side-B, all three levels** (tap, medium hold, full hold): pass = `label=S1 price=8.0`,

   `S2 price=18.0`, `S3 price=42.0`. A full Kazap that lands and finishes must show

   **exactly one** `S3` spend. Fail: a second `S3` spend, or any spend labelled `N*`.

8. **Out of MP:** keep casting until the log shows `REFUSE ... short=`. Pass: a `REFUSE`

   naming the shortfall, **no** `SPEND` for that cast, the casting motion still playing,

   and **no fireball / no sparks / no lightning**; MP never negative. Fail: a free spell, a

   silent nothing at all, or MP below 0.

9. **Swap persistence:** spend down to about 30, swap to Pyra with down-B, swap back. Pass:

   the lines before and after show the same `entry=` and an MP that neither jumped to 100

   nor dropped. Idle as Pyra for ten seconds too: the meter must keep recovering at the

   same rate, because the meter belongs to the pair.

10. **Recovery rate:** from a partial meter, count `RECOVER +1.0` lines over about ten

    seconds standing still. Pass: roughly one per second (the donor's 1 SP per 60 frames).

    Fail: none, or clearly more than one per second - that would mean the per-frame hook

    fires more than once per frame, and the `TICK frames=` numbers are the measurement to

    send. While *holding* a charge the meter must **not** recover (`pause=0x2`).

11. **Stock loss and rebirth:** lose a stock. Pass: exactly one `RESET by=stock` line, not

    one per frame of the death animation, and the meter back at 100.0. In a rematch, pass:

    it also starts at 100.0 and never inherits the old value.

12. **Regression sweep** on c06 **and** c07: Hero Spin (up-B), Corrin up air, Luigi down

    throw, Snake neutral-B, Monkey Flip side-B, G&W up-B, R.O.B. down tilt, Little Mac

    forward smash. All must behave exactly as on the previously installed build, and

    **nothing but the two Hero spells may log a SPEND**. Then return

    `sd:/ultimate/pgwr_mana_log.txt` and `sd:/ultimate/pgwr_log.txt` from boot, plus any

    new `sd:/atmosphere/crash_reports/` file. A crash means reverting to the last known

    good card state and reporting it (rule 10).



Fail signs summary: no `[PGWR-MANA]` file; `max=` not 100; a `SPEND` with no `CAST`; a

`REFUSE` that still produced a projectile; a `SPEND` for Hero Spin; MP below zero; more

than one `RESET` per stock; two spends for one Kazap; recovery while charging; a crash

report newer than the install.



## gaogaen_throw_b — 2026-10-03 — INSTALLED (was: READY, enabled installable package)

**INSTALLED 2026-10-03 02:12:15 on top of the installed 0.20.20, by the Freebuff designated installer
at the user's request ("install the current changes to the switch"). Hardware test pending: nothing in
this section has been run on the console, on Ryujinx, or in any automated test.** NRO
`5d7d9b8e565d9b38d6a73d804a36f4028e6fcd80ff92f15739ed96f3b783689b` (487,424 B, new binary); mod tree
`7a33ab21e5a6c313b20c7c6160d4b7cf92914bf759a45be11a5c4364e50bae2c` (1992 files). Card was confirmed
at 0.20.20 (1990/1990 equal) before writing and 1992/1992 equal after, against the package and
against the manifest's own hashes; recomputed card tree hash equals the manifest. Backup
`evidence/sd-backups/sd-backup-20261003-021215`; framework installation OFF, all four protected
plugins byte-unchanged. Record: `evidence/2026-10-03_pgwr_0.20.20+gaogaen_throw_b/INSTALL.md`;
**test sheet: `.../RESULT.md`**; machine record `evidence/install-record-2026-10-03_021215.json`.
`logging` stays off; this move's own log is `sd:/ultimate/pgwr_gaogaen_throw_b_log.txt`.
Shared plugin/info version deliberately remains 0.20.20. The development notes below describe the
pre-install state and are kept as the design record.

---

User-authorized eflame ID **0x208** is allocated and registered in live source; next free
ID is 0x209. No environment value or unapplied patch is needed to enable this move.
Package: `builds/pgwr/gaogaen_throw_b-0.3.0/`, enabled NRO plus full combined mod tree.
NRO SHA256 `5d7d9b8e565d9b38d6a73d804a36f4028e6fcd80ff92f15739ed96f3b783689b` (487424 bytes).
Tree SHA256 `7a33ab21e5a6c313b20c7c6160d4b7cf92914bf759a45be11a5c4364e50bae2c` (1992 files).
Manifest SHA256 `70fc7e105293d910b97a0c32b40ebf81958fb55985046817e5e0134b3934c7da`.

Offline enabled build, source/hash/registration/status checks and semantic asset
preservation passed. Based on 0.20.20: exactly 15 changed asset files and 2 owned clips;
all other baseline files preserved. Includes existing Snake/Lucas/Ness moves. Shared
plugin/info version remains 0.20.20; task package identity is 0.3.0, no shared bump.
No Revenge system; intended unboosted donor. No competing THROW PRE runtime is present;
compose one dispatcher if DK cargo is added later.

Not installed at the time this section was written; installed 2026-10-03 (see the header).
Runtime unverified, including the pinned SIMD hook ABI warning. Source/logger/package reproduction, installer command and ten manual
checks: `evidence/2026-10-03_pgwr_gaogaen_throw_b/RESULT.md`.
Move log: `sd:/ultimate/pgwr_gaogaen_throw_b_log.txt` (REGISTERED/ENTER/VICTIM_INIT/END).

## Lucas down smash (AttackLw4 + AttackLw4Hold) on Mythra c06/c07 — Buffy (2026-10-02)

**INSTALLED in collective 0.20.20; hardware unverified. Development notes below describe the pre-install state; the stale concurrent compile blocker is resolved by the combined build. See the collective record above.**




**INSTALLED in collective 0.20.20; hardware unverified. Development notes below describe the pre-install state; the stale concurrent compile blocker is resolved by the combined build. See the collective record above.**





**PENDING: source complete and the delta is packaged and audited, but NOT installed and

NOT hardware-tested. No console run, no emulator, no automated test.**



- **Target:** Mythra (`elight`) c06/c07 — Lucas's complete down-smash family, replacing

  **stock Mythra's** down smash on those two costumes. Not the G&W half: the other three

  concurrent tasks target `eflame`, and this one targets `elight`. Registering on

  `elight` is what makes it a different statement from the Little Mac forward smash

  (`acmd::littlemac_attack_s4`), which is on `eflame`.

- **Readiness: PENDING, and the reason is not this work.** The delta is a concrete,

  checked package; what is missing is the console verdict, which only the user can

  produce. There is no source-level blocker.

- **Package:** `builds/pgwr/T-0060-lucas-downsmash/` — a **delta only**, not a full

  release. 24 mod files; mod tree

  `f8666b2494f444809a7284bfc0d0e9e694620a6ea8ff837d0a5d1b4851e9fdc6`.

  Audit: `BASELINE_DELTA.json` there. Manifest: `MANIFEST.json`.

- **Baseline: the installed 0.20.19 card tree, not vanilla.** It carries the 25 Hero

  neutral-B/side-B motion entries, so Mythra's motion lists are **759** entries. Comparing

  against vanilla would report 25 changes this task did not make. Baseline NRO

  `1771152551c8a4a0de85a9a0e766ff63ccafeaa9f431251880824c3b214f3b72`.

- **Measured delta:** **16 overrides + 4 vanilla-path clip overrides, 0 removed,

  0 unrequested, no new file name, no `config.json` change, no new status id, no

  c00-c05 file.** All 759 motion entries compared; only `attack_lw4` differs, and only in

  its cancel u16.

- **Source (this agent's whole diff):**

  - `src/pgwr/plugin/src/mythra/lucas_attack_lw4.rs` (new, the donor's 7 ACMD scripts)

  - `src/pgwr/plugin/src/mythra/mod.rs` (**4 narrow additions**: `pub mod`, `LOG_LW4`,

    one `install()` call, and two doc/log lines)

  - `src/pgwr/tools/build_lucas_downsmash.py` (retarget)

  - `tools/audit_lucas_lw4_donor.py`, `tools/apply_lucas_downsmash_motion_list.py`,

    `tools/merge_lucas_downsmash_sound.py`, `tools/build_lucas_downsmash_effect.py`,

    `tools/audit_lucas_downsmash_delta.py`

  - `refs/lucas_attack_lw4/` (pins + `SOURCE.json` + `inventory.json`)

  No shared-tree file other than `mythra/mod.rs` was written, and nothing else was

  regenerated.

- **Three findings the installer should know about, because each would have shipped a

  wrong move:**

  1. **The charge hold is `attack_lw4_hold`, not `attack_lw4_charge`** (hash40

     `0xfee188235`). The kind and the script name are not a mechanical pair: the kind is

     `attack_lw4_hold` and its `game_script` is `game_attacklw4charge`. A first pass

     looking for `attack_lw4_charge` found nothing and read as a missing donor file.

     Proven by re-parsing **G&W's** list and matching every field against

     `dumps/scripts/gamewatch_motion_list.yml`, an independent dump of a different

     fighter's list.

  2. **The motion-list delta is 2 bytes.** Lucas `attack_lw4` cancel **316** vs Mythra 56,

     differing at entry-relative offsets **[62, 63]** (absolute 5526/5527 in the baseline

     list) and nowhere else. `attack_lw4_hold` is **byte-identical** between the two

     fighters, so nothing is written for it.

  3. **`havel` is not a bone on either fighter** — it is the engine's built-in hand anchor,

     like `top`. The donor's effect anchors are used unchanged rather than remapped.

- **Retarget:** 66 of 68 transform nodes survive, 2 dropped (`Bat`, `BatL` — his bat, so the

  move needs no article), 0 case-only matches, **0 parent mismatches** (parent chains

  compared by name between the two skeletons, which a plain name filter cannot do). All 17

  real limb bones present and measurably moving; the build refuses to ship a static one.

  `LegL/R` 127/129°, `KneeL/R` 103°, `ShoulderL/R` 122/139°, `ArmL/R` 106/86°,

  `HandL/R` 100/108°, `Hip` 66°.

- **Assets are recipient-owned, never donor folders.** An `.eff` under

  `effect/fighter/lucas/` is loaded by nobody (`kb/findings/

  effect-ownership-of-donor-banks-and-per-slot-trails.md`), so `LUCAS_PSI_HOLD` and

  `LUCAS_PSI_ATK_LW` are merged into the already-declared `ef_elight_c06/c07.eff`

  (128 → 130 emitters each, **0 lost**, 0 texture/model ids relocated). Sounds append to

  Mythra's own banks: all **389** SE and **233** VC baseline tones per slot preserved

  byte-for-byte and in order, **+5 SE** (`se_lucas_smash_l01..l04`, `se_lucas_pk_charge`)

  and **+1 VC** (`vc_lucas_attack07`). **No stand-in sounds** (rule 17).

- **No shared status id needed** — `attack_lw4`/`attack_lw4_hold` are vanilla kinds, so

  Mythra's `0x1F1..0x1F4` (Hero's Spin) is untouched and the next free id is unchanged.

  **Nothing for the installer to allocate.**

- **⚠ Build caveat, and it is the installer's to resolve.** The shared plugin does **not

  currently compile**: the concurrent Ness back-throw agent's

  `src/pgwr/plugin/src/mythra/ness_throw_b.rs` references an unlinked `singletons` crate

  (2 × E0433). That file is not mine and was not edited. This task's module was compiled

  from an isolated copy with only that one module removed, giving NRO

  `b51dcb278e444e864a50729a764115725ef927bc905a01a6f1b1e34402898160` (475,136 B), features

  `snake-neutral-b,hero-side-b`, `logging` off, cache

  `builds/.cache/pgwr-fb-4-lucas-downsmash-target`. **That NRO is a verification artefact,

  not the package** — build from the shared source once the concurrent work compiles, and

  compare. That NRO carries all 21 checked markers: 7 handler names, `PGWR-LW4`,

  `elight`, 6 sound names, 2 effect names, 3 rumble names, `collision_attr_elec`.

- **Integration commands** (run from the mod root; the installer owns the combined tree):



  ```bash

  # 1. the shared source must compile first (currently blocked by ness_throw_b.rs)

  (cd src/pgwr/plugin && CARGO_TARGET_DIR=../../../builds/.cache/<installer-cache> \

     cargo skyline build --release --features snake-neutral-b,hero-side-b -- --offline)



  # 2. overlay this delta onto the combined mod tree

  cp -r builds/pgwr/T-0060-lucas-downsmash/ultimate/mods/pyra_gamewatch_reskin/. \

        <combined>/ultimate/mods/pyra_gamewatch_reskin/



  # 3. re-audit the combined tree against the recorded baseline

  python tools/audit_lucas_downsmash_delta.py --package <combined>



  # 4. compare the newly built NRO against the verification NRO above

  #    (a mismatch is expected only from other agents' code; confirm the 21 markers)

  ```



  Do **not** stage the verification NRO from step 1's cache blindly — this is the

  stale-cache failure `CURRENT_INSTALL.md` already records once.

- **Offline checks done here (all passed, none behavioural):** donor pins; parser

  cross-validated against G&W's independent dump; release compile clean with **no new

  warnings**; clips re-read after saving; sound pins/script-coverage/cleanliness plus a

  **negative control** (a damaged pre-existing tone is rejected); effect merge with the

  converter's decoded-field and opaque-subsection equality checks; delta audit with **three

  negative controls firing**.

- **Evidence:** `evidence/2026-10-02_pgwr_T-0060_lucas_downsmash/RESULT.md` (immutable);

  `refs/lucas_attack_lw4/inventory.json`; `builds/pgwr/T-0060-lucas-downsmash/BASELINE_DELTA.json`.

- **Unverified: all behaviour.** No console, no emulator, no tests.



**Manual test after designated installation** (this release writes no game log — the

`logging` feature stays off, so **judge by eye**; return any new

`sd:/atmosphere/crash_reports/` file and `sd:/ultimate/pgwr_log.txt` from boot if one

appears). Compare against **stock Lucas** in a separate control run for steps 3-8.



1. Boot. Confirm the game loads, Mythra c06 and c07 are selectable, and the costume gate

   holds (see step 10 for the control).

2. **Vanilla negative control:** Mythra c00 and Pyra c00. The down smash must be

   completely unchanged vanilla Mythra — her sword, her own three-hit frame data, her own

   sound. No Lucas animation, no PSI orb, no Lucas sound.

3. **c06 charge hold.** Hold down + B. Expect Lucas's own charge pose: a PSI orb held

   at the **left hand**, the standing wind, the `rbkind_smashhold1` rumble, and the

   *charge loop* tone. It must **not** be Mythra's sword-open charge.

4. **Charge to full (past frame 61).** Expect the second hold rumble

   (`rbkind_smashhold2`) and the pose to hold rather than snapping.

5. **Release the charged smash.** Expect **three separate** hits out of one sweep:

   17 / 14 / 11 damage. Read the per-hit numbers in training mode. The donor calls

   `set_target_category(0, NO_IF)` after the first two frames so one sweep does not

   re-hit the same target, so a target that takes 17 and stops is correct and 17+14+11

   cumulatively is not.

6. **Release an uncharged (tap) smash.** All three hits must still come out with the

   same 17/14/11 - it is not a charge-only move.

7. **Effects.** Each of the three hits must spawn its own PSI sweep arc, and the arcs

   must **grow** across the sequence (1.25, then 1.3, then 1.45), with `sys_dash_smoke`

   at the foot on each. Three separate growing arcs is what proves the donor's

   `effect_attacklw4` is running rather than a stand-in.

8. **Sounds.** Frame 7 must play Lucas's own release tone and cut the charge loop;

   frame 16 his **voice line**; then one tone per hit. A silent smash, or Mythra's

   sword sound, means the merge did not take and is a fail.

9. **Low hit and facing.** This is a low poke: a **crouching** opponent must be hit by

   all three frames. Then face right and face left - the sweep and its hitboxes must

   mirror with the fighter, the charge orb must stay at the **left hand** relative to

   facing, and the wind must push the same way both times. A sweep that only works in

   one direction is a fail.

10. **Interruption, and the cancel frame.** Get hit during the charge hold (the orb

    should disappear, not persist) and get hit mid-sweep after the first hit (the

    remaining hits should stop). Then confirm the move can be cancelled into up or

    side smash only after the last hitbox clears at frame 42. That is the only way to

    confirm the 2-byte motion-list patch took effect at runtime.

11. **c07 repeats steps 3-10.** The clips and motion entries are byte-identical across

    the two costumes (measured), so both must behave the same. If only one changed, the

    other slot's files were not overlaid.

12. **Regression sweep on Mythra c06/c07:** up air (Corrin), side-B (Hero's Spin), down

    throw (Luigi), neutral-B and side-B (Hero on the pair's mana meter), and the

    Pyra-Mythra down-B swap in both directions. Then the G&W half on Pyra c06/c07:

    forward smash (Little Mac), up tilt (Snake), down tilt (R.O.B.), neutral-B (Snake

    grenade), side-B (Monkey Flip), up-B (G&W Fire). None of these may change.

13. Confirm **vanilla Mythra in c00-c05** and **standalone Lucas** are untouched.

    Standalone Lucas must still be fully stock - that is the control for "this really

    is Lucas's move and not an approximation of it".



**Fail:** the down smash still shows Mythra's sword animation or her own sound; a

missing PSI orb, a missing or wrong-count set of sweeps, or a silent smash; one sweep

hitting a target three times cumulatively where stock Lucas would not; a cancel before

frame 42 or one long after it; the charge pose or charge sound not appearing; the orb

straying from the left hand in one facing; any regression across the twelve moves in

step 12; any change to c00-c05 or to standalone Lucas; any new crash (send the report

and restore the last known good per rule 10).



**On the cancel frame, the one honest reading:** step 10's early/late cancel test is the

only part of this port that no offline check can settle. The 2-byte patch is measured

and the audit proves the other 758 entries are byte-identical, but whether the engine

honours cancel 316 on *this* recipient is tier D until the console says so. If the move

feels cancelable far too early, that is this patch not having taken effect (or having

been overlaid onto a tree that already had a different list) - report it exactly as

observed rather than as a vague "feels wrong".



---



## Snake down throw (ThrowLw) on G&W c06/c07 — Snake down throw agent (2026-10-02)

**INSTALLED in collective 0.20.20; hardware unverified. Development notes below describe the pre-install state; the stale concurrent compile blocker is resolved by the combined build. See the collective record above.**




**INSTALLED in collective 0.20.20; hardware unverified. Development notes below describe the pre-install state; the stale concurrent compile blocker is resolved by the combined build. See the collective record above.**





**PENDING — NOT installed, no console run, no emulator.** Labelled by move rather

than by slot: another concurrent entry above calls itself "Freebuff slot 4".



### What this change is



Vanilla Snake's **down throw** on Pyra/G&W costumes c06 and c07, replacing G&W's

own down throw on those two costumes only. Every other move and every vanilla

costume is untouched.



ACMD: `plugin/src/acmd/snake_throw_lw.rs` (new, mine)

Assets/motion: `src/pgwr/tools/build_snake_throw_lw.py` (new, mine)

Sounds: `tools/merge_snake_throw_lw_sound.py` (new, mine)

Donor inventory: `tools/audit_snake_throw_lw_donor.py` (new, mine)

Delta audit: `tools/audit_snake_throw_lw_delta.py` (new, mine)

Pinned donor: `refs/snake_throw_lw/`

Delta package: `builds/pgwr/snake-throw-lw-delta/`

Record: `evidence/2026-10-02_pgwr_snake_throw_lw/RESULT.md`



### The move kind is `throw_lw`, NOT `AttackLw4`



Worth stating loudly, because the two differ by one word and **both exist in

Snake**. `AttackLw4` is the **down smash**. Three measurements settle it:



| kind | game script | clip | cancel |

|---|---|---|---|

| `throw_lw` | `game_throwlw` | `e01throwlw.nuanmb` | 48 |

| `attack_lw4` | `game_attacklw4` | `c04attacklw4.nuanmb` | 56 |



1. Snake's `attack_data_param.prc` has an `attack_lw4` AI record at

   `cancel_frame: 56` and **no** `throw_lw` record at all.

2. `game_attacklw4` opens with `START_SMASH_HOLD`, `se_common_smash_start_02`,

   `rbkind_smashhold1` and `PHYSICS_START_CHARGE`, with an `AttackLw4Charge`

   follow-up clip. Those are down-smash marks.

3. `AttackLw4.txt` / `AttackLw4Charge.txt` are pinned at the same commit purely

   as the control. The audit asserts `throw_lw` and `attack_lw4` never name the

   same game script, so a future revision that merged them would be caught.



`refs/snake_throw_lw/donor_acmd/` holds all three, sha256 in `manifest.json`.



### The victim's prone outcome is `collision_attr_lay`, not knockback



The donor's throw box reads damage 9.0, angle 270, with **kbg, fkb and bkb all

zero**. There is no launch to copy, so "damage plus a downward launch" would be a

*different move*, not a simplification. `collision_attr_lay` routes the victim

into the engine's generic `FIGHTER_STATUS_KIND_LAY_DOWN` (0x56) rather than the

`DAMAGE_FLY*` family, and the victim then runs its own get-up.



Concretely, all three parts of capture/release are carried verbatim:



1. the capture box — `ATTACK_ABS(..., CATCH, 0, 2.0, 361, 100, 0, 60, ...)`,

   `ATTACK_LR_CHECK_B`;

2. the release — `ATK_HIT_ABS(THROW, Hash40::new("throw"), target, group, no)` at

   frame 35, reading the three `FIGHTER_STATUS_THROW_WORK_INT_TARGET_*` ids;

3. the `collision_attr_lay` attribute on the throw box.



Nothing victim-side ships: `e01thrownlw` / `e01throwndxlw` live under the

*victim's* own fighter folder in the base game, so every opponent already plays

its own correct prone clip.



### Measured delta (tier B) — overlay on 0.20.19, 10 files



Delta root: `builds/pgwr/snake-throw-lw-delta/ultimate/mods/pyra_gamewatch_reskin`

MANIFEST: `builds/pgwr/snake-throw-lw-delta/MANIFEST.json`

(`2150b01bc3b6bb416adaf4b85e2456a6dfe0f4a89f442929def9c338f6626881`)



| file | delta sha256 |

|---|---|

| `fighter/eflame/motion/body/c06/e01throwlw.nuanmb` | `28381e8bc06e410b4c44583564eb362bb202b5add948dd04acd42e47127d79da` |

| `fighter/eflame/motion/body/c07/e01throwlw.nuanmb` | `28381e8bc06e410b4c44583564eb362bb202b5add948dd04acd42e47127d79da` |

| `fighter/eflame/motion/body/c06/motion_list.bin` | `524d8fc95e0a6396dec54e4b2468acc07ac97ff6ce162bd7f3c2466acd4277a0` |

| `fighter/eflame/motion/body/c07/motion_list.bin` | `524d8fc95e0a6396dec54e4b2468acc07ac97ff6ce162bd7f3c2466acd4277a0` |

| `sound/bank/fighter/se_eflame_c06.nus3audio` | `12bbc3f14d3ce2d3b3e6353f6d8b3252cd28e6f10010eae441cf109341963a85` |

| `sound/bank/fighter/se_eflame_c06.nus3bank` | `c81848142bbfb8e10b6e79ec77f4b5ca302d88731ce9012a11c7cb679a787444` |

| `sound/bank/fighter/se_eflame_c06.tonelabel` | `f961410ded27222bceae17871986fa64254150c529203f964d3e721306675adb` |

| `sound/bank/fighter/se_eflame_c07.nus3audio` | `12bbc3f14d3ce2d3b3e6353f6d8b3252cd28e6f10010eae441cf109341963a85` |

| `sound/bank/fighter/se_eflame_c07.nus3bank` | `c81848142bbfb8e10b6e79ec77f4b5ca302d88731ce9012a11c7cb679a787444` |

| `sound/bank/fighter/se_eflame_c07.tonelabel` | `f961410ded27222bceae17871986fa64254150c529203f964d3e721306675adb` |



* `throw_lw` is the **only** changed entry of **841**, per slot. Cancel

  **50 -> 48**, flags `0x80` unchanged, **file size preserved** (both entries are

  28 bytes, so a pure in-place splice). The tool asserts every other entry is

  byte-identical.

* `attack_lw4` (down smash) cancel still **34**, asserted untouched.

* Clip: **77 of 87** transform nodes kept; the 10 dropped are `FaceN` and the

  nine `S_Bandanna*`; 0 case-only matches; **every limb bone measured moving**

  against the recipient idle (`deploy_for_slot` refuses a static limb).

* Sound: **544** tones retained byte-for-byte per slot, **4** appended.

* No new clip file names, therefore **no `config.json` change**. No c00-c05 file,

  no Mythra file, no `status/mod.rs` edit, **no shared version bump**.



### Four tones ship, not the two the script names



`se_snake_catch_tight` is the **only kind-1 (sequence) tone among the 111** in

`se_snake_c00`, and it references `se_snake_catch_tight_01` and

`se_snake_catch_tight_01_layer` by **bank-relative index 92/93**. Those are

rebased to 545/546. The shared codec's `group_links` decodes donor tone kinds 0

and 3 and asserts on others, and correctly refused; appending only the two named

tones would have left the grab sound pointing at two unrelated tones already at

index 92/93 in Pyra's 544-tone bank, with every byte-level check still passing.

Two negative controls back this (truncated bank; unrebased donor index).



No `PLAY_SEQUENCE` is played, so **`eflame.sqb` is deliberately not written**.



### An empty `effect_throwlw` is registered on purpose



Snake's `ThrowLw` defines no effect script; G&W's defines four

(`sys_smash_flash_s` at 1 and 22, `sys_down_smoke` at 21, `sys_landing_smoke` at

35). Simply omitting the handler would leave the generated Default one installed

and G&W's effects playing over Snake's silent throw. Per `handbook/04` ("port

what the donor has, empty what only the recipient has") an empty handler is

registered at High priority. Found by inspecting the built NRO, not by reading

the donor.



### Shared-file dependency



`src/pgwr/plugin/src/acmd/mod.rs` — three narrow hunks, already applied to the

working tree; an unapplied copy is kept at

`refs/snake_throw_lw/integration/0001-acmd-mod-add-snake_throw_lw.patch` for

re-application if another agent's edit to the same file conflicts:



1. `pub mod snake_throw_lw;`

2. the `table::THROW_LW` description line

3. `snake_throw_lw::install();` after `snake_attack_hi3::install();`



**No conflict with the other three concurrent tasks is expected:** they work on

Mythra (`mythra/mod.rs`) or on `gaogaen_throw_b` in `acmd/`. The one shared

surface is `acmd/mod.rs`.



### Status ids requested



**None.** `ThrowLw` is a vanilla status kind entered from the grab, so this move

allocates nothing. **Next free Pyra id remains `0x208`** (unchanged).



### Installer: exactly what to run



    # from the mod repo root, D = the delta overlay, T = your merged tree

    D=builds/pgwr/snake-throw-lw-delta/ultimate/mods/pyra_gamewatch_reskin

    T=builds/pgwr/<your-version>/ultimate/mods/pyra_gamewatch_reskin

    for f in fighter/eflame/motion/body/c06/e01throwlw.nuanmb \

             fighter/eflame/motion/body/c07/e01throwlw.nuanmb \

             fighter/eflame/motion/body/c06/motion_list.bin \

             fighter/eflame/motion/body/c07/motion_list.bin \

             sound/bank/fighter/se_eflame_c06.nus3audio \

             sound/bank/fighter/se_eflame_c06.nus3bank \

             sound/bank/fighter/se_eflame_c06.tonelabel \

             sound/bank/fighter/se_eflame_c07.nus3audio \

             sound/bank/fighter/se_eflame_c07.nus3bank \

             sound/bank/fighter/se_eflame_c07.tonelabel ; do

      cp "$D/$f" "$T/$f"

    done



    # re-derive the same delta from scratch instead (equivalent, reproducible):

    python src/pgwr/tools/build_snake_throw_lw.py \

      --baseline builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin --out "$D"

    python tools/merge_snake_throw_lw_sound.py --check

    python tools/merge_snake_throw_lw_sound.py \

      --baseline builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin --output "$D"



    # verify after copying

    python tools/audit_snake_throw_lw_delta.py --baseline "$T" --delta "$D"



If your merged tree already carries another agent's motion-list or bank edits,

run the two generators against **your** tree instead of 0.20.19 and re-run the

audit; both are append-only and refuse a baseline they were not measured on.



**Do not reuse this task's NRO.** `ed9a790e7c8ab690ad6d38ad564cb99d47dfb1a8b18e873fc9395c066a4d1185`

(471,040 B) is a *verification* artifact built from a copy of the crate in which

the three in-flight modules were commented out, because

`src/mythra/ness_throw_b.rs` does not compile (unresolved crate `singletons`).

Rebuild from the merged source.



### Manual console test (12 steps, vanilla control included)



1. Boot fresh and keep `sd:/ultimate/pgwr_log.txt` **from boot**.

2. **Vanilla control.** Pick Pyra c00. Grab an opponent and press down+attack.

   Down throw must behave exactly as before (G&W's), with the G&W throw flash and

   smoke effects. This is the negative control for the costume gate.

3. Also confirm Mythra c00's down throw is unchanged (it is a different fighter

   and must be untouched).

4. Pick **Pyra c06**. Grab an opponent and press down+attack. Expect Snake's

   animation, 9% damage, **no flash/smoke effects**, and Snake's grab and throw

   sounds.

5. Judge the release: the victim must be **let go**, and must go **down prone on

   the ground and then get up** — not launched upward and not launched hard along

   the floor. Report which of those three you actually see.

6. Compare with **stock Snake** as the donor control: same damage, same prone

   outcome, same get-up.

7. Pick **Pyra c07** and repeat step 5.

8. **Vanilla-costume control.** Pyra c01-c05 must still show G&W's down throw with

   its effects.

9. Confirm **the down smash is untouched**: on c06/c07, down+attack *without* a

   grab must still be G&W's down smash with its own effects and sound.

10. Confirm the other throws are untouched on c06/c07: forward, back and up throw

    must still be G&W's, with G&W's effects.

11. Watch for the **known risk**: if the victim is never released, or the game

    stalls at the throw, report it immediately and stop — that is the `throw`

    bone, which is not on the built c06/c07 skeleton. Do not keep retrying.

12. Return the boot log and, on any crash, the new file in

    `sd:/atmosphere/crash_reports/`.



**Pass / fail markers.** With `logging` off there are no `[PGWR-*]` lines for this

move and none are expected. Pass = steps 4-7 behave like stock Snake, steps 2, 3,

8, 9 and 10 are unchanged. Fail = any of: the victim is never released; the game

stalls or crashes in the throw; c00-c05 changed; the down smash changed; the

other three throws changed; G&W's throw effects still play on c06/c07; or the

grab sound plays but is audibly the wrong/layered sample.



### Blockers



- **None for the port itself.** It is source-complete, packaged and audited.

- Blocked for *installation* only by the shared build: the tree does not compile

  while `src/mythra/ness_throw_b.rs` is in flight. Whoever owns that file must

  resolve the `singletons` import.

- Runtime behaviour is **tier D** until step 12 comes back. Nothing in this

  section has been run on hardware, on Ryujinx, or in any automated test.

---



## Ness back throw (`throw_b`) on Mythra c06/c07 — Buffy (2026-10-02) — **READY (source + delta), NOT installed**

**INSTALLED in collective 0.20.20; hardware unverified. Development notes below describe the pre-install state; the stale concurrent compile blocker is resolved by the combined build. See the collective record above.**




**INSTALLED in collective 0.20.20; hardware unverified. Development notes below describe the pre-install state; the stale concurrent compile blocker is resolved by the combined build. See the collective record above.**





### What this change is



Vanilla Ness's back throw on Mythra c06/c07, gated by costume like every other

Mythra move in this crate. Donor `ness`, recipient `elight`. The four ACMD

scripts are the donor's target-costume branch **verbatim**; the attacker

animation is Ness's own retargeted; the release, the absolute throw

damage/angle/knockback, the timing, the rumble and the effects/sounds are the

donor's. **No donor behaviour is approximated and nothing is substituted with a

stand-in.**



The small delta is measured, not assumed: Ness's and Mythra's `throw_b` motion

entries are **byte-identical except offset 62**, the cancel frame (Ness 53,

Mythra 36), and **both name the same clip file** `e01throwb.nuanmb`. So this is

one `.nuanmb` and one byte per slot — no alias, no spare clip name, no new

declared file, and **no `config.json` change at all** (the file already exists in

the base game in that costume group).



| | value (donor's) |

|---|---|

| absolute throw | `ATTACK_ABS(THROW, 0, 11.0, 135, 130, 0, 15)` = 11 startup, **135 damage, 130 base knockback, 15 angle** |

| catch | `ATTACK_ABS(CATCH, 0, 3.0, 361, 100, 0, 60)` |

| release | frame 27, `ATK_HIT_ABS(THROW, "throw", ...)` on the `Throw` bone |

| camera | `CHECK_FINISH_CAMERA(-5, 18)` |

| cancel frame | **53** (was 36) |

| rumble | `rbkind_elecattack` 24 at frame 2, `rbkind_attackm` 0 at frame 27 |

| effect | `ness_psi_rush` (donor-owned, merged) |

| sounds | `se_ness_throw_pk01`, `se_ness_throw_pk02`, `se_ness_pk_s`, `seq_ness_rnd_attack` |



**Status ids required: NONE.** `throw_b` is a vanilla kind already in Mythra's own

list and status table, and the donor writes no fighter work id. This task

requests **no** allocation from the shared Mythra range and does not compete with

any other agent for one.



### Three donor omissions kept deliberately (not porting slips)



1. **No `REVERSE_LR`.** Mythra's vanilla back throw reverses facing; Ness's does

   not. Measured against ten other fighters' `ThrowB` at the pinned commit: six

   omit it (kirby, pikachu, snake, younglink, ness) and six use it (mario,

   luigi, robot, cloud, gaogaen, gamewatch). So it is per-fighter, not a

   back-throw convention, and adding one would be inventing donor behaviour.

   **Console step 3 decides how it reads.**

2. **No pickup-frame `ATTACK` box / `set_catch_only_all`.** Ness catches with the

   `ATTACK_ABS(CATCH)` pair alone. Mythra's and Luigi's both have the box —

   because those throws do.

3. **No `AttackModule::clear_all` after the release.**



Also absent from the donor and not reintroduced:

`FT_ATTACK_ABS_CAMERA_QUAKE`.



### Two calls dropped — the cut-in framing (read before judging step 8)



The donor sets the throw-finish cut-in zoom rate `2.0` and offset `(0, 5, 0)`.

**These are not ported.** The pinned `skyline-smash` 315e4e8 declares

`FighterCutInManager`'s two methods but exposes no accessor for the manager

instance, and the crate has no `singletons` module, so the calls cannot be

written (verified three independent ways, including the same wall already hit by

`acmd/monkey_flip.rs` and by pmclone excluding Mythra's own vanilla `throw_b`).



No hand-built pointer and no raw-offset hook was used — rule 17 forbids both

without the user's decision on reserved work. **Consequence:** the throw finish

*camera* is the donor's, but the cut-in uses the default zoom and offset. A known,

bounded gap; not an approximation of a value.



### Victim side: nothing to port



The victim plays **its own** fighter's `thrown_b` clip. Mythra keeps hers, so

Ness's `e01thrownb` / `e01throwndxb` / `e01throwngirlb` are deliberately **not**

imported — they are Ness reacting to being thrown, and importing them would

change how Mythra behaves when *someone else* throws her.



### Pinned sources (hashes)



Donor ACMD text: `WuBoytH/SSBU-Dumped-Scripts` @

`59004685238a3f6f93bae905d3a4e079701c40b4`, in `refs/ness_throw_b/donor_acmd/`

(`ness__ThrowB.txt` sha256

`ce67f672edadf6dd7294ed5da2fe5e335d0264fcbf70b240d11a01aa46298bfb`). Full

provenance, controls and measurements: `refs/ness_throw_b/SOURCE.json`.



Donor binaries: read read-only out of the local 13.0.4 `data.arc` with

`tools/arc-extract` into `gamedata/` — clip `e01throwb.nuanmb` sha256

`376d65d66708585911a91cc8132c8354fd5ce754e2b079752972ecfae1c52d52`,

`motion_list.bin` `7a6b5066…`, `ef_ness.eff` `5aab79ed…`, `se_ness_c00.*`,

`vc_ness_c00.*`, `ness.sqb` `8fc0ee19…`.



### Measured offline (tier B) — delta on 0.20.19, **19 files**



`builds/pgwr/ness-throw-b-candidate/ult_mod`, overlaid on the baseline

`builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin`. Per-file hashes and

every assertion: `evidence/2026-10-02_pgwr_T-0060_ness_throw_b/DELTA.json`.



| file | baseline -> candidate |

|---|---|

| `fighter/elight/motion/body/c06/e01throwb.nuanmb` | **added** (override of a vanilla file) `0b7da3fdab095231891808682d9c9795fba5d05c369f89ac77bb87b98e5de6ee` |

| `fighter/elight/motion/body/c07/e01throwb.nuanmb` | **added**, byte-identical to c06 |

| `fighter/elight/motion/body/c06/motion_list.bin` | `0efe5732fe98afa8e1c742e467e1b408dc1fb0be0269b11831bee980d2fb3059` -> `3d1ea0aa4dcd2b3ef1a5eb8bc1523fe1a80fd2e8e0868d572bb589e438a79fae` |

| `fighter/elight/motion/body/c07/motion_list.bin` | `0efe5732…` -> `3d1ea0aa…` (identical; the two lists are byte-equal) |

| `effect/fighter/elight/ef_elight_c06.eff` | `c7a2b4b0dff6a523a1b311eea52ca29a1c437b600edc9b445aaf810f2461e0e3` -> `41d416d6b89ee8a303f801abe50652a6ab6ecdc26aac75be24b963f0cbebb3cf` |

| `effect/fighter/elight/ef_elight_c07.eff` | `d4f06243582516dae66099f24a6a777a1f61cf0d326100dd3c8d59353f3d97bb` -> `2c0a8af5a64de42d7ee70f7bae60b30c861446eed6dae1d4da7ab9fe45123983` |

| `sound/bank/fighter/se_elight_c0{6,7}.*` | 3 files/slot; 389 tones preserved + 3 appended |

| `sound/bank/fighter_voice/vc_elight_c0{6,7}.*` | 3 files/slot; 233 tones preserved + 4 appended |

| `sound/sequence/fighter/elight.sqb` | `seq_ness_rnd_attack` appended once (idempotent) |



Exact per-file hashes for the nine sound files are in `DELTA.json`.



**Retarget:** 66 of Ness's 68 transform nodes exist on Mythra's skeleton; the two

dropped are `Bat` / `BatL` (his baseball bat). No case-only matches. The limb

chain is *measured* moving, not merely present — `Throw` 179.32 deg and 30.80

units of translation, `LegL/R` 112.59/100.72 deg, `ArmL/R` 109.95/57.97 deg.

Measured against Mythra's vanilla skeleton, because pgwr replaces Pyra's

skeleton with G&W's but leaves Mythra's vanilla (verified: the package ships no

`fighter/elight/model/body/c06/model.nusktb`).



**Effect banks:** 127 vanilla emitters -> 128, **0 lost**, 1 added

(`NESS_PSI_RUSH`), each slot. 0 texture and 0 model ids relocated — the table is

reported anyway, because T-0050 found a duplicate id that merged "successfully"

and drew the wrong mesh.



**Sound banks:** every pre-existing sample byte, tone record and tone label

compared before and after; a negative control truncates a written bank and the

check fires. The four `vc_ness_attack*` tones were **measured out of the

`seq_ness_rnd_attack` record by CRC32**, not hand-listed; without them the

sequence would resolve to silence.



**`audit_ness_throw_b.py --check` passes** and its three negative controls all

fire (a motion list with `throw_hi` altered is rejected; a candidate shipping

`effect/fighter/ness/` is rejected; a bank missing `se_ness_throw_pk01` is

rejected). It also proves **only** `throw_b` moved: `throw_f` 28, `throw_hi` 30,

`throw_lw` 46 and all four `thrown_*` entries are byte-identical to the

baseline.### Installer: exactly what to run



```bash

cd mods/ssbu_mod_new



# 1. the asset delta, overlaid on the baseline tree

CAND=builds/pgwr/0.20.19/ultimate/mods/pyra_gamewatch_reskin

cp -r builds/pgwr/ness-throw-b-candidate/ult_mod/. "$CAND"/



# 2. the Rust: rebuild. THIS IS NOT AN ASSET-ONLY DELTA.

#    Use a cache of your own; do not reuse another agent's.

export CARGO_TARGET_DIR="$PWD/builds/.cache/pgwr-installer-throwb-target"



# 3. re-run the audit against the tree you just modified

python -B tools/audit_ness_throw_b.py --check --candidate "$CAND"

```



Reproduction from scratch (each step independent and re-runnable):



```bash

python -B src/pgwr/tools/build_ness_throw_b.py --check

python -B tools/merge_ness_throw_effects.py --check

python -B tools/merge_ness_throw_sound.py --check

```



### Conflict with a concurrently running task — read this



`tools/build_lucas_downsmash_effect.py` (Lucas down smash, same Mythra costumes)

merges `LUCAS_PSI_HOLD` and `LUCAS_PSI_ATK_LW` into **the same two files**,

`effect/fighter/elight/ef_elight_c06.eff` and `..._c07.eff`, against the same

0.20.19 baseline.



**The two effect deltas cannot both be applied by copying files.** They must be

merged in sequence, each taking the other's output as its recipient:



```bash

python -B tools/merge_ness_throw_effects.py \

  --recipient <tree>/effect/fighter/elight/ef_elight_c06.eff \

  --output    <tree>/effect/fighter/elight/ef_elight_c06.eff   # and c07

```



Then re-run `audit_ness_throw_b.py --check`. It asserts **no vanilla emitter was

lost** but does not know about Lucas's two, so confirm the final emitter count is

**130** (127 vanilla + `NESS_PSI_RUSH` + the two Lucas emitters).



The sound banks and the motion lists do not collide with another task's files as

far as this task is concerned, but re-run the audit after the collective merge

regardless.



The Snake down throw section above records that the tree failed to compile while

`src/mythra/ness_throw_b.rs` was in flight. That was the transient `singletons`

error and it is **resolved** — the file compiles today; see below.



### Build verification (tier B) — and what this build is NOT



Compiled clean (no errors) with `snake-neutral-b,hero-side-b`, `logging` off, in

the isolated cache `builds/.cache/pgwr-fb-4-ness-throw-b-target`:



```

NRO sha256 86a4b27678eb96f6066e3fc32bbc4b99849681981222311923e5bc3c4dadbbb9

size       479232 bytes

```



`tools/verify_nro.py` confirms the binary carries `PGWR-NESSTHB`, `game_throwb`,

`effect_throwb`, `sound_throwb`, `expression_throwb`, `ness_psi_rush`,

`se_ness_throw_pk01`, `seq_ness_rnd_attack`, `rbkind_elecattack` — and that

`throw_lw` (the shipped Luigi down throw) is **still present**.



**That NRO is not a deliverable.** The working tree contains other agents'

uncommitted work (T-0057 mana, Lucas down smash), so this is a *verification*

build, not an installable artifact. An installer must rebuild from the merged

tree and re-hash; **do not ship this hash.** Two rebuilds of the same source

already produced two different hashes at the same size, so it is not reproducible

from the source alone — which is why `tools/verify_nro.py` exists.



### Manual console test (12 steps, vanilla control included)



Boot fresh and keep `sd:/ultimate/pgwr_log.txt` **from boot**. `logging` is off,

so no `[PGWR-*]` lines appear for this move and none are expected — judge by eye.

The boot banner must list `Ness back throw` among the Mythra replacements.



1. **Vanilla control.** Mythra c00: grab and back-throw. Must be stock Mythra —

   her own animation, her own effects, her own sound, nothing Ness-like. Then

   Mythra c05, same.

2. Mythra **c06**, grab, back-throw (grab while holding back). Expect Ness's

   animation: the PK-style swing behind, PSI rushing toward the grab.

3. **Facing, right vs left.** Throw facing right, then facing left, and compare.

   The move carries **no `REVERSE_LR`** (see above), so this is the step that

   settles whether the back throw reads correctly. Report whether Mythra turns

   around in each direction.

4. **Release timing.** Release is frame 27; cancel frame is 53. Throw a still

   opponent: they must be held, then released on Ness's beat, not Mythra's

   faster vanilla throw.

5. **Victim sizes.** Throw a small (Pichu), a medium (Sheik) and a large

   (Bowser) opponent. All three must be caught and thrown; none may pass

   through, snap free, or launch at a wildly different distance.

6. **Launch.** Expect Ness's **11 damage / angle 135 / KBG 130 / BKB 15** — noticeably

   harder and more sideways than Mythra's vanilla back throw. Against a stock

   100 % target the percentage must read meaningfully higher.

7. **Interruption.** Start a throw, then have the victim DI (double jump) or an

   ally hit them before release; it must behave like Ness's. Then start a throw

   at a platform edge and confirm nothing stalls.

8. **Cut-in (known gap).** The throw-finish cut-in is expected to use the

   **default** zoom/offset rather than the donor's 2.0 / (0,5,0), because those

   two calls are unreachable in this toolchain. A plain default framing is a

   **pass**; anything worse (wrong camera, freeze, crash) is a fail.

9. **Effects and sounds.** The PSI rush must actually be drawn on Mythra — that

   is the `NESS_PSI_RUSH` merge; without it the throw would animate and hit with

   nothing drawn. You must hear the PK grab and swing, and **Ness's voice** on

   the release (the `seq_ness_rnd_attack` record plus the four merged

   `vc_ness_attack` tones). A silent or Mythra-voiced release means the sequence

   merge did not land.

10. **Other throws untouched.** On c06/c07 the forward throw, up throw and

    **down throw** must all still be Mythra's own (the down throw is the

    already-shipped Luigi port). No PSI on any of them.

11. **Swap.** Enter as Pyra c06, press down-B to become Mythra, then back-throw:

    must be Ness's throw. Also test Mythra c06 selected directly.

12. Return the boot log and, on any crash, the newest file in

    `sd:/atmosphere/crash_reports/`.



**Pass / fail.** Pass = steps 2-9 behave like real Ness (modulo the step 8

cut-in gap) and steps 1, 10, 11 show c00-c05 and the other three throws

unchanged. Fail = any of: c00-c05 changed; another throw changed; no PSI drawn;

the victim is never released; the game stalls or crashes mid-throw; the voice is

Mythra's or silent; or the throw behaves like vanilla Mythra's, which would mean

the ACMD registration did not take.



### Blockers



- **None for the port itself.** Source complete, assets complete, audited, builds

  clean, delta checked with hashes.

- **The cut-in zoom/offset gap** above is a real, bounded limitation needing a

  user decision (reserved raw-offset work). It does not block this move.

- **The effect-bank sequencing conflict with the Lucas down smash** must be

  resolved by whoever performs the collective merge.

- **Runtime behaviour is tier D until step 12 comes back.** Nothing here has been

  run on hardware, on Ryujinx, or in any automated test.




## Hero's Spin up-B air gravity 0.70/0.70 on Mythra c06/c07 — 2026-10-03 — INSTALLED in collective 0.20.22

Installer update: source delta independently packaged, built/audited and card-verified in 0.20.22. The original development-stage notes below explain why the worker verification NRO was excluded; that NRO was not used.

**No installation is requested by this agent.** Development agent; rule 23 applies. Collective
release versioning is the installer's, so nothing here bumps the shared plugin/`info.toml` version
and no package is staged: the change is two Rust constants and the installer rebuilds from source.

- **Scope:** the modded Mythra (stock `elight`) in costumes c06/c07 only. User request, from
  `evidence/2026-10-03_pgwr_user_verdict/RESULT.md`: *"opponents still fall out of Mythra up-B too
  often"* → *"further up-B gravity reduction"*.
- **The entire diff:** `src/pgwr/plugin/src/mythra/hero_spin_params.rs`,
  `AIR_ACCEL_Y_SCALE` **0.85 → 0.70** and `AIR_SPEED_Y_SCALE` **0.90 → 0.70**. Effective accel
  0.09010 → **0.07420** u/f², terminal 1.39500 → **1.08500** u/f. `hero_spin.rs` has a doc-comment
  change on `air_exec` only; `hero_spin_acmd.rs` is byte-identical. New:
  `tools/audit_hero_spin_airtime.py` and `refs/mii_hero_spin_hi3/airtime_audit.json`.
- **No coordination needed with the other scopes:** no status id, no asset, no motion-list entry, no
  sound or effect bank, no `config.json`, no shared-file edit outside my two files. Nothing to
  merge in sequence.
- **Hashes:** `hero_spin_params.rs` `7bfe44b1b44c29bbb198648af0dcd155742002c45b83fc5f5f7491f3ccb1a186`;
  `hero_spin.rs` `e26a05cee9310c9b8385aeed5cae662c02d061779984ef565357150b3e969eb6`;
  `audit_hero_spin_airtime.py` `98fcb7d1317818c822209c9b44ab42f01ae553770915a2b0743f9a6be343ade4`;
  `airtime_audit.json` `10680964d79d34f73192d179f3ce3af8c3fa48869f559b5b288d80372c95db3c`.
- **Offline checks passed:** `python tools/audit_hero_spin_airtime.py --check` PASS with two negative
  controls; offline release build clean with no new warnings; NRO
  `f2634b91fa4e5360f9de235d0f6b735c68b8dac574636680a0e61b2ac37ecda4` (487,424 B), reproducible, and
  **different** (`65107e7b67bc701848465094c89a618552fcce363398cd3fb8911b67eb59c552`) when the same
  tree is rebuilt at the old values — which is the control proving the two constants are genuinely
  compiled into the binary.
- **Do not package `builds/.cache/pgwr-fb-upb-gravity-target`.** It was built from the shared source
  while four other agents were editing it, so the NRO carries their in-flight work as well. It is a
  **verification artefact only**. This is the stale-cache hazard this file already records: rebuild
  from the shared source in a cache the installer controls, and compare that NRO against
  `f2634b91…` only for *this file's* contribution.
- **Build recipe** (`cargo skyline build` rejects `--offline`; use `CARGO_NET_OFFLINE=true`, and give
  `CARGO_TARGET_DIR` as an **absolute** path — a relative one resolves against the crate directory
  and lands outside `builds/`):

  ```bash
  cd src/pgwr/plugin
  CARGO_NET_OFFLINE=true \
  CARGO_TARGET_DIR="<repo>/builds/.cache/<installer-chosen-cache>" \
  cargo +skyline-v3 skyline build --release --features snake-neutral-b,hero-side-b
  ```

  `logging` stays off, so the console test is judged by eye; the existing
  `[PGWR-HI3] air spin y <a> -> <b>` height line still exists and may appear in the Skyline console,
  but treat it as a bonus, not a requirement.
- **Preserved on purpose:** launch, the frame 47/48 finisher, all damage/knockback/hitbox geometry
  and frame data, the landing and motion-end transitions, `end()`'s `AttackModule::clear_all` and
  jostle restore, statuses `0x1F1..0x1F4`, the costume gate, motions and trail. No fighter-wide
  parameter, no victim gravity, no opponent constraint, no unrelated attack buff.
- **Not bundled on purpose:** moving `JostleModule::set_status(false)` from frame 11 to frame 8. The
  first hitbox opens at frame 8 with jostle still on, so that one frame can still be pushed off the
  target — a real one-frame retention gap, and a one-line fix, but it edits donor frame data and
  bundling it would make this a two-state-changing-change package (rule 11). If retention is still
  poor on the run below, it is the first candidate for the next controlled build.

**Unverified: all behaviour.** The descent numbers are tier-B arithmetic on two pinned source files;
that lower gravity keeps more of a hitstun opponent inside the boxes is **tier D** and is the whole
point of the change. No console, no emulator, no SD access, no card.

### Console test after a designated installer packages it (9 steps, training mode)

1. **Vanilla negative control.** Mythra c00 and c01: up-B is stock Mythra's, jump arc unchanged.
2. **Pyra c06 control.** G&W's own up-B still throws the breath projectile with its parachute.
3. **Ground start, no target.** Mythra c06 and c07: hold and release up-B. The ground spin and hold
   state must be identical to the installed build — this change cannot reach them.
4. **Retention (the point).** Aerial use over a standing opponent, at least ten attempts, counting
   how many land fewer than all ten boxes. Repeat the same ten on the currently installed build.
   Pass: fewer drop-outs, never more.
5. **Damage and size.** Repeat 4 against a 0 % and a 120 %+ target, and against a **small** fighter
   (Little Mac) and a **large** one (Bowser). Small opponents are the band argument's worst case.
6. **Both facings, both entries.** Repeat 4 facing right and left, entered once from a jump apex and
   once from a rising up-B, so the seven-frame 31→38 window is entered at different vertical speeds.
   Add a DI attempt off the first hit to check it does not break the string.
7. **Finisher.** The frame 47/48 finisher must still connect and still launch with the same force.
8. **Landing, recovery, cleanup, no hover.** Land mid-spin: recovery immediate and normal. Get hit
   mid-spin: no stuck spin and no hitbox left after the move. After the move you must fall at
   Mythra's normal rate, not the slowed one.
9. **Regression sweep on c06 and c07.** Corrin up air, Hero neutral-B, Hero side-B, Luigi down
   throw, Lucas down smash, Ness back throw; Pyra/G&W side unchanged.

**Fail:** fewer hits than the installed build; a finisher that no longer launches; a lingering
hitbox after the move ends; any hover or floaty fall *after* the move ends; vanilla Mythra or
Pyra c06 changed; any crash (send `sd:/atmosphere/crash_reports/`).

Full record: `evidence/2026-10-03_pgwr_upb_gravity/RESULT.md`.
