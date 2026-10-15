# pgwr - current state

## Pikachu back air — 1.0.0 — 2026-10-03 — READY, not installed

Pikachu's `AttackAirB` and `LandingAirB` on the modded `eflame` pair, c06/c07
only. Package `builds/pgwr/pikachu-airb-1.0.0/` - a **narrow 19-file delta**,
not a replacement tree - plus two source patches; NRO
`9d0ee7edb554d402cf31ff12dce989319804b65fece8b9cae3787e4cc3eddcee` (524288 B),
built twice to the same hash in `builds/.cache/pikachu-airb/plugin`. All eight
donor handlers ported verbatim from the pinned scripts and registered at
`Priority::High` over the generated G&W ones.

Measured (B): donor pinned and re-checked every run; retarget keeps 45 of 55
Transform nodes, drops exactly EarL1/L2, EarR1/R2, Hat, Have, Tail1-4, with
**0 parent-chain mismatches** compared by parent *name*, and rebuilds the
38-node donor Visibility group from the recipient's own 98-node idle; all 17
tracked limb bones move (ToeL/R move by translation only); `attack_air_b` moves
**two bytes** per slot (cancel 296->300, flags `0x0080`->`0x0084`) and
`landing_air_b` moves **zero**, because that recipient entry is already
byte-identical to the donor's; 561 `se_` and 250 `vc_` tones retained per slot
against the 6 appended; exactly one donor-identical `seq_pikachu_rnd_attack`
record. No config.json, no param, no effect, no ui, no other entry: the donor's
three effects are all common-bank `sys_*` names, so no donor emitter is merged.
**No status id** - both kinds are vanilla states.

Controls (B): an unmodified copy of the baseline snapshot, built with the same
command in the same environment, reproduces the baseline NRO
`424914c18e740aea67c37ed399ffe5a22208b76f10dec81e279a8285198b777e` byte for
byte. `tools/audit_pikachu_airb_delta.py` 128/128 with **8 negative controls
caught** and one positive control passing; `merge_pikachu_airb_sound.py --check`
PASS; donor audit's 7 controls caught plus its positive control.

Unverified (D): animation appearance, hitbox connection, sound and effect
playback, and how the landing feels. `landing_attack_air_frame_b` left at G&W's
18.0 because Pikachu's own value is unreachable offline. The G&W turtle article
no longer appears on this move - the donor has none. No install, emulator run,
console, commit, branch or push. Evidence:
`evidence/2026-10-03_pgwr_pikachu_airb/RESULT.md`; installer section
`CURRENT_INSTALL.md`.

## Silent performance 0.20.23 — INSTALLED 2026-10-03 (current card state)

User explicitly requested all logging removed. Package `builds/pgwr/0.20.23/`, isolated source `builds/.cache/silent-0.20.23/plugin/`; NRO `424914c18e740aea67c37ed399ffe5a22208b76f10dec81e279a8285198b777e` (524288 B). `logging` OFF; `hero-mana-hud` stays ON and reserved recovery OFF. 224 diagnostic call expressions (file and console) now use the existing logging feature; their arguments are not evaluated in the silent build. Diagnostic-only changes persisted to matching live modules without replacing gameplay code.

Verified B: offline build/source reversal and binary checks passed; now installed with all 5099/5099 card files and built/package/card NRO equal. Five other plugins and Skyline unchanged, frameworks OFF. Existing gameplay/assets retained, mana debit/recovery fixes excluded as pending worker work. Backup `evidence/sd-backups/sd-backup-20261003-125341`. Runtime smoothness unverified; no diagnostic markers expected. Record/test sheet: `evidence/2026-10-03_pgwr_0.20.23_silent/INSTALL.md`.


## Collective 0.20.22 — INSTALLED 2026-10-03 (superseded by silent 0.20.23)

Installed Hero level-2 side-B angle, visible battle mana HUD on both c06/c07 forms, and up-B air gravity 0.70/0.70. Package `builds/pgwr/0.20.22/`; NRO `3ab31bd34dceda31659f337867fdf67330afa691c50d565b514cd66124dd6772`; tree `3a64be3b167ac7ff864399056e0e7ce74a7b011e5a6315a5f1ba408583f74cfa`; 5099/5099 card files verified. DK cargo/Incineroar and ready-assets.1 visual fixes retained. All other plugins/Skyline unchanged; frameworks OFF, hero-mana-reserved OFF. Dashgrab excluded (no completed handoff). Backup `evidence/sd-backups/sd-backup-20261003-122846`. Build/native/HUD/angle/gravity audits passed offline; all new gameplay/UI behavior unverified. Test sheet/log markers: `evidence/2026-10-03_pgwr_0.20.22_install/INSTALL.md`.


## Hero angle / battle mana HUD — 0.1.1 — 2026-10-03 — INSTALLED in collective 0.20.22

Concrete package `builds/pgwr/zapple-mana-hud-0.1.1/`, plugin/info 0.20.21;
NRO `48291984dfc2ae4e5c0b92ab19c15312807170f643f68bc992a792f98b3c2b65`. Latest ready-assets.1 retained (5099 files; info version only).
Continues Opus: Zapple tuple (16.3,18.2,-83.5), level-2 effect only; owned MP feeds native battle gauge
for both c06/c07 forms via hero-mana-hud, with stock/entry reset and corrected eight-frame setter window.
Four isolated variants plus narrow patches; DK cargo/Incineroar retained, dashgrab/up-B gravity excluded.
Offline B: builds/audits/hashes/scope/patch application pass. Native HUD signature mismatch refuses gracefully
by source inspection; runtime drawing, angle, mapping/swaps/teardown and Main-callback regen rate unverified (D).
No card/emulator/console/commit/push. Test vanilla controls, each change alone, then combined;
11-step sheet + exact diagnostics: `evidence/2026-10-03_pgwr_zapple_mana_hud/RESULT.md`.
Installer section: CURRENT_INSTALL.md. Old cached 0.1.0 is superseded, not an asset source.


## Ready asset batch 1 — INSTALLED 2026-10-03 (retained in collective 0.20.22)

Installed Chrom jab sword visibility, costume-themed Lucas/Ness magic effects and G&W starting-form loading presentation. Package `builds/pgwr/0.20.20+ready-assets.1/`, 5099/5099 card files verified; tree `a38d16c037389f730c842fc70fbda04b033b2dfc1e70ee7f4060520702dbf153`. NRO unchanged `214dc3126430598fb5e71093f6d5d584e17e662a593b67acf0eb0b777eb66058`; shared plugin/info version remains 0.20.20. DK cargo/Incineroar and other existing gameplay preserved. All plugins unchanged, framework install OFF. Backup `evidence/sd-backups/sd-backup-20261003-114100`. New visual outcomes unverified; test sheet and evidence `evidence/2026-10-03_pgwr_ready_assets_1/INSTALL.md`.

Hero angle/HUD and dash-grab slide excluded (no ready handoff). Up-B gravity excluded (PENDING/no concrete package). Active workers' source and build inputs untouched.


## Loading presentation — Codex — 2026-10-03 — INSTALLED in ready-assets.1

Task 0.1.0, collective version left to installer. Package
`builds/pgwr/loading-presentation-0.1.0/`, MANIFEST
`d17829ecd2726972c8ed978efab9957d772217e194983b2f14da601fb862022d`.
Native category-3 and starting-form lookup measured on local main; installed
Ursula/Shadow Purple c06 and Wilhelmine/Golden Light c07 G&W artwork reused
exactly. Two eflame-first BNTX files plus semantic ui_chara/ui_layout database
union: four eflame costume routes and four loading-only layout rows. Mythra
assets/routes, names, vanilla rows and non-loading layout fields retained.
Offline B: 5098/5098 DK cargo + Incineroar baseline checked, 5095 unchanged;
task-only calculated union 5099 files; exact reproduction, round trips,
16 route checks, eight player panes and concurrency/conflict controls PASS.
No NRO/gameplay/config/framework edits. Apply after final build and UI tasks;
do not overlay stale shared PRCs. Instructions/test matrix:
`src/pgwr/tools/loading_presentation/README.md`; evidence
`evidence/2026-10-03_pgwr_loading_presentation/RESULT.md`.
Runtime/Training placement and visual fix remain unverified; no game/emulator run.
Existing decoded c07 Mythra artwork artifacts are outside this change and retained.

## User console verdict — 2026-10-03

Tier A, user report: "the latest version of the mod works great." This updates prior install-time hardware-pending notes; no individual control checklist or boot hashes were supplied. Latest recorded package is dk_cargo-0.1.1-test over shared 0.20.20 (exact tested-package association inferred). Remaining user-reported issues and six newly requested worker scopes are recorded in `evidence/2026-10-03_pgwr_user_verdict/RESULT.md`. Only the modded eflame/elight c06/c07 pair is in scope. The later user request authorizes this partial install; remaining tasks wait for readiness.


## chrom_jab_sword 1.0.0 — INSTALLED 2026-10-03 (asset-only; hardware unverified)

**The Chrom jab's blade was invisible on hardware from 0.20.0 through 0.20.20, and
the cause is now byte-proven rather than guessed at.** `build_esword_pose._build_jab_mlist`
wrote the two appended motion-list entries' animation-name hash as
`hash40('jabopen')`/`hash40('jabtoopen')`; an animation-name hash covers the file
name **with its extension**, which every vanilla entry of that article proves
(`open` -> `0xe32317ab0` == `hash40('z00open.nuanmb')`). Both jab entries therefore
named a file that does not exist, which fails silently: the article keeps playing
`z00close`, whose `flamesword` mesh visibility track is **False**, and that track
overrode the ACMD's `set_visibility_whole(true)`. The Cloud fair was never affected
— it drives the vanilla `to_open` kind. This is the R-18/R-20/R-21 family of lesson
made concrete: article-level visibility is necessary and not sufficient, and the
mesh track has the last word.

*Measured (tier B):* delta is **two files**, 884 bytes each, size preserved,
differing byte offsets per slot 804-808 and 856-860, both inside the appended
entries. `8b7be43a2435c971...` -> `1816a2913b778433...` for
`fighter/eflame/motion/esword/c06/motion_list.bin` and the same for c07. The other
22 files of the two article folders regenerate **byte-identical** to the baseline,
and no other file of the 5098-file tree differs. New
`tools/audit_chrom_jab_sword.py --check`: **96 checks, 0 failures**, all four
negative controls caught (bare-stem name, jab clip drawn=False, `attack_11` cancel
frame moved, jab clip deleted); run against the *baseline* it reports **10
failures**, so a PASS is a statement about the fix, not about the audit having run.
Preserved by measurement: `attack_11`/`_12`/`_13` still name `c00attack11.nuanmb` at
cancel 23, `attack_air_f` still names `c05attackairf.nuanmb`, `config.json` still
declares both jab clips, per-state visibility/scale unchanged (1.4 fair / 0.9 jab).

*Deliberately unchanged:* no Rust, so **no NRO rebuild and none should be copied**;
`chrom_jab.rs` documentation only. No second visibility guard
(`attack_air_f::esword_visibility_guard` stays the single owner and already lists
`attack_11`/`_12`/`_13`), and no "always show the sword" fallback — that lever would
have masked this defect while breaking the fair's put-away. Measured for the record:
`HandR` moves through 42 distinct rotations in `c00attack11.nuanmb` and `HaveR`
(the grafted `HandR -> HaveR -> Sword1 -> Sword2` chain) carries one constant local
transform, so the blade **and** the `sword1` trail both ride the hand for the whole
jab. No body-side clip change: the jab's animation and hitboxes were confirmed on
0.16.0 and are not in question.

*Expected merged mod tree* `1091b63be89a26bb319eeb38879e2d166cc66a0946e940ccea6a9e04d4f080cf`
over 5098 files, if nothing else is merged in.

*Next failure to expect, stated not guessed around:* the article's own
`game_toopen` script is not in this workspace, so whether the jab settles in its
own 0.9 state or the fair's 1.4 one is unresolvable offline — that would be a size
problem, not a visibility one. Also recorded and deliberately not shipped: the
`ADD_PARTIAL_MTION_SWORD_WHEN_CHANGEING` flag every vanilla eflame sword-drawing
script sets, because it is never cleared and so latches on during almost any move
anyway.

Package `builds/pgwr/chrom-jab-sword-1.0.0/`; installer section + 14-step test in
`CURRENT_INSTALL.md`; record `evidence/2026-10-03_pgwr_chrom_jab_sword/RESULT.md`.
**All runtime behaviour tier D** — no build, game, emulator, console or card access.

## gaogaen_throw_b 0.3.0 over 0.20.20 — INSTALLED 2026-10-03 (superseded by ready-assets.1 above)

Incineroar back throw on G&W `eflame` c06/c07 at owned status `0x208`, installed as the only READY
queue section. **All gameplay unverified — nothing on the card has been run on hardware.** NRO
`5d7d9b8e565d9b38d6a73d804a36f4028e6fcd80ff92f15739ed96f3b783689b`; tree
`7a33ab21e5a6c313b20c7c6160d4b7cf92914bf759a45be11a5c4364e50bae2c` (1992 files). Delta vs 0.20.20:
15 changed, 2 added, 0 removed. dk_cargo and T-0054 excluded as not READY. Backup
`evidence/sd-backups/sd-backup-20261003-021215`; framework installation OFF; protected plugins
unchanged. Record `evidence/2026-10-03_pgwr_0.20.20+gaogaen_throw_b/INSTALL.md`; **test sheet
`.../RESULT.md`**; log `sd:/ultimate/pgwr_gaogaen_throw_b_log.txt`. `logging` off; shared
plugin/info version stays 0.20.20.

**Five moves now on the card, none hardware-verified:** Little Mac fist trails, Snake up tilt, Hero
mana, Snake down throw, Lucas down smash, Ness back throw, plus this Incineroar back throw. The next
single test that settles the most is the gaogaen sheet, since it also regresses the others.

**hero_spin_gravity (2026-10-03, Freebuff): Mythra c06/c07 up-B air gravity 0.85/0.90 → 0.70/0.70 —
installed in collective 0.20.22; build/card verified, no console run, retention unverified.**

The whole change is two `f32` constants in `plugin/src/mythra/hero_spin_params.rs`;
`hero_spin.rs` got a doc comment only and `hero_spin_acmd.rs` is byte-identical. Effective accel
0.09010 → 0.07420 u/f², terminal 1.39500 → 1.08500 u/f. User request: "opponents still fall out of
Mythra up-B too often".

*It is deliberate custom tuning and now says so.* Mii's dedicated `Hi3` kinetic cannot be installed
on `elight`, so the mod rescales Mii's *common* air values by hand; the header records the chain
(.c 1.00/1.00 → .d 0.85/0.90 → now) and retracts the earlier "the donor's own tuning" wording.

*The values came from a measurement.* New tier-B tool `tools/audit_hero_spin_airtime.py` reads the
constants out of the Rust source and the donor's own `ATTACK` literals out of the ACMD (positions
from locked `smash_script` `fdc6144`) and reports, per hit window, the attacker descent since the
previous window as a fraction of that window's box band — `gap/band`, the offline form of "the
opponent fell out", since jostle is off for the whole string and every box is a one-frame window.
Binding window 31 → 38, the only seven-frame hole in the donor's schedule: **0.81 → 0.63**. String
descent 58.2 → 45.8 u. Stops at 0.70 because below ~0.55 the move stops reading as falling.

*No hover:* the phase still exits on ground contact and at the end of the 85-frame motion, and
`air_exec` is registered on `STATUS_AIR_SPIN` alone. `--check` asserts strict monotonicity.

**Deliberately not bundled:** moving `JostleModule::set_status(false)` from frame 11 to frame 8 —
the first box opens with jostle still on, a genuine one-frame retention gap, but it edits donor
frame data and would make this a two-change package (rule 11). It is the first candidate for the
next controlled build if retention is still poor.

Offline: audit `--check` PASS with 2 negative controls; offline release build clean, no new warnings;
NRO `f2634b91fa4e5360f9de235d0f6b735c68b8dac574636680a0e61b2ac37ecda4` (487,424 B), reproducible,
and **different** (`65107e7b…`) rebuilt at the old values — the constants are compiled in. Cache
`builds/.cache/pgwr-fb-upb-gravity-target`. **That NRO is a verification artefact, not a package**:
it was compiled from the shared tree while other agents were editing it. No status id, asset,
motion entry, sound/effect bank or `config.json` change, so nothing to conflict over.
Evidence and 9-step console test: `evidence/2026-10-03_pgwr_upb_gravity/RESULT.md`; installer
section and test sheet in `CURRENT_INSTALL.md`.

## Collective 0.20.20 — INSTALLED 2026-10-02 (superseded on the card by the install above)

Snake down throw, Lucas down smash and Ness back throw are installed together; all gameplay unverified. Individual delta audits and fresh combined build passed; card rehash 1990/1990 equal, protected plugins unchanged. NRO `7242d2f5af32bcc5304aa0e94930fe22ac689bd21db9b213f2ecfdac5fbf2098`; tree `10cd7a07a629897aa24c775173cffbfa13f071c5308f19fe0b483995a9f78abc`. Backup `evidence/sd-backups/sd-backup-20261002-193356`. Full record and corrected eight-step test: `evidence/2026-10-02_pgwr_0.20.20/INSTALL.md`. DK cargo and Incineroar back throw excluded as incomplete. Logging remains off; no new per-move pass markers expected.









## Lucas / Ness effect themes on Mythra c06/c07 — 2026-10-03 — READY, not installed

Lucas down-smash (`LUCAS_PSI_HOLD`, `LUCAS_PSI_ATK_LW`) and Ness back-throw (`NESS_PSI_RUSH`)
PSI re-coloured inside each costume's measured palette: c06 scarlet/crimson/magenta/violet,
c07 white/gold/light pink. Asset-only two-file overlay `builds/pgwr/lucas_ness_effect_theme-0.1.0/`
on the latest installed `dk_cargo-0.1.1-test`; c06 `79d1fcc0d4688bd8...`, c07 `d7217697ac7e6af5...`,
delta tree `c2ca1592e3286d70...`. Tool `tools/customize_lucas_ness_effects.py` 1.0.0 is a semantic
merge (apply it to the installer's candidate bank, do not copy over a bank another task changed).
B: 17 emitter colour edits + 2 owned star textures per slot; every other decoded entry (3543) and
every byte outside 20 owned emitter blocks / 2 owned textures identical; reproducible, idempotent,
three negative controls and a concurrent-addition control pass; bank resolves through the existing
`fighter/elight/c0X` declaration. No NRO/config/motion/sound change. D: appearance in game.
Evidence, preview and 7 visual checks: `evidence/2026-10-03_pgwr_lucas_ness_effect_theme/RESULT.md`.

**ness-throw-b (2026-10-02, Freebuff): vanilla Ness's back throw (`throw_b`) on Mythra c06/c07. READY

as source + a checked 19-file delta, NOT packaged as a release, NOT installed, no console run.

All runtime behaviour unverified.** The port is complete and small because the donor and the

recipient turned out to agree almost everywhere: the `throw_b` motion entries are

**byte-identical except offset 62** (the cancel frame, Ness 53 vs Mythra 36) and **both name the

same clip file** `e01throwb.nuanmb`, so there is no alias, no spare name, **no `config.json`

change** and one byte of motion-list delta per slot. New:

`plugin/src/mythra/ness_throw_b.rs` (the four donor scripts verbatim, install-time

`set_costume([6,7])`), `src/pgwr/tools/mlist.py` (byte-faithful motion-list reader, promoted out of

scratch after the scratch dir was pruned mid-session), `src/pgwr/tools/build_ness_throw_b.py`

(retarget + one-byte patch, refuses to ship a static limb), `tools/merge_ness_throw_effects.py`

(`NESS_PSI_RUSH` into `ef_elight_c06/c07.eff`), `tools/merge_ness_throw_sound.py`

(`se_ness_throw_pk01/02` + `se_ness_pk_s`, the four `vc_ness_attack*` **measured out of the

sequence record by CRC32**, and the `seq_ness_rnd_attack` record), `tools/audit_ness_throw_b.py`.

*Measured:* 66 of Ness's 68 nodes exist on Mythra's skeleton, dropped are exactly `Bat`/`BatL`,

0 case-only; the limb chain moves (`Throw` 179.32 deg / 30.80 units, `LegL/R` 112.59/100.72 deg);

127 vanilla emitters preserved per slot with exactly 1 added and 0 id relocations; 389 `se_` and

233 `vc_` baseline tones preserved byte-for-byte; plugin compiles clean in

`builds/.cache/pgwr-fb-4-ness-throw-b-target` and the NRO carries all four handler names plus

every resource name while `throw_lw` (Luigi) is still present. `audit_ness_throw_b.py --check`

passes with all three negative controls firing, and proves **only** `throw_b` moved.

*Three donor omissions kept, each measured not assumed:* no `REVERSE_LR` (a ten-fighter sweep at

the pinned commit shows six fighters omit it, so it is per-fighter, not a back-throw convention),

no pickup-frame `ATTACK` box, no `clear_all` after release. **The throw-finish cut-in zoom/offset

is NOT the donor's** — the pinned `skyline-smash` has no `FighterCutInManager` accessor and no

`singletons` module, so those two calls are unreachable; verified three ways and left as a stated

gap rather than approximated. `CHECK_FINISH_CAMERA(-5, 18)` is the donor's.

**No custom status id requested** — `throw_b` is vanilla and the donor touches no fighter work

id, so this task competes with no other agent for one.

*Conflict:* the concurrent Lucas down smash merges two different emitters into the **same two**

`ef_elight_c0{6,7}.eff` from the same baseline; the two must be merged in sequence, not applied

by copying files (command in `CURRENT_INSTALL.md`).

Records: `refs/ness_throw_b/SOURCE.json`, `evidence/2026-10-02_pgwr_T-0060_ness_throw_b/`,

installer section + 12-step console test in `CURRENT_INSTALL.md`.

*Labelled by move rather than by task number:* a concurrent agent's entry below claims **T-0060**

for Lucas's down smash, so that id is ambiguous in this file. Also noted there: the Lucas entry

still says "the shared plugin does not currently compile - a concurrent agent's

`ness_throw_b.rs`", which is now **false** - the `singletons` error it refers to was this task's

transient mid-flight state and the tree compiles today (both with and without

`snake-neutral-b,hero-side-b`).

**snake_throw_lw (2026-10-02, Snake down throw agent): vanilla Snake's DOWN THROW

on the live G&W body, eflame c06/c07 - source complete, delta packaged and

audited, PENDING, NOT installed, no console run.** (Labelled by move rather than

by slot number: another agent's concurrent entry below calls itself "Freebuff

slot 4", so the slot labels collide and this entry avoids them.)

ACMD `plugin/src/acmd/snake_throw_lw.rs`; clip + motion entry by

`src/pgwr/tools/build_snake_throw_lw.py`; sounds by

`tools/merge_snake_throw_lw_sound.py`; donor inventory

`tools/audit_snake_throw_lw_donor.py`; delta audit

`tools/audit_snake_throw_lw_delta.py`. Delta is an **overlay** on 0.20.19,

10 files: `builds/pgwr/snake-throw-lw-delta/`, MANIFEST

`builds/pgwr/snake-throw-lw-delta/MANIFEST.json` (`2150b01bc3b6bb4...`).

*Two findings that are the reason this is more than a damage number:*

**(1) The down throw is `throw_lw`, not `AttackLw4`.** `AttackLw4` is Snake's

**down smash** - his `attack_data_param.prc` carries an `attack_lw4` AI record at

cancel 56 and no `throw_lw` record, `game_attacklw4` opens with

`START_SMASH_HOLD` / `rbkind_smashhold1` / `PHYSICS_START_CHARGE` with an

`AttackLw4Charge` follow-up, and the two kinds' clips and cancel frames differ

(`e01throwlw` 48 vs `c04attacklw4` 56). `AttackLw4.txt` is pinned at the same

commit as the control that settles it; the audit asserts the two kinds never name

the same game script.

**(2) The victim is put down prone by `collision_attr_lay`, not by knockback.**

The donor's throw box is damage 9.0, angle 270, with **kbg/fkb/bkb all zero** -

there is no launch to copy. `collision_attr_lay` routes the victim to the

engine's `FIGHTER_STATUS_KIND_LAY_DOWN` (0x56) instead of `DAMAGE_FLY*`, and the

get-up is the victim's own state, so nothing victim-side ships here.

*Also found:* `se_snake_catch_tight` is the **only kind-1 (sequence) tone among

the 111** in `se_snake_c00` and references its two children by bank-relative

index 92/93, so appending the two named tones alone would have left the grab

sound pointing at two unrelated tones in Pyra's 544-tone bank while every

byte-check passed. Four tones are appended and 92/93 are rebased to 545/546, with

two negative controls. And Snake's `ThrowLw` has **no effect script**, so an

empty `effect_throwlw` is registered at High to supersede G&W's four effects -

found by inspecting the built NRO, not by reading the donor.

*Measured:* `throw_lw` is the only changed entry of **841** per slot, cancel

50 -> 48, flags 0x80 unchanged, file size preserved; `attack_lw4` (down smash)

cancel still 34 and untouched; clip 77 of 87 nodes kept with **all limbs measured

moving**; 544 tones retained byte-for-byte; **no new clip names so no

config.json**, no c00-c05 file, no Mythra file, no `status/mod.rs` change, no

version bump. **`ThrowLw` is a vanilla status kind, so NO custom status id is

allocated or requested; next free Pyra id stays `0x208`.** Shared-file edit is

three narrow hunks in `acmd/mod.rs` with an unapplied copy in

`refs/snake_throw_lw/integration/`. *Unverified: all behaviour* - no console, no

emulator, no tests, no card access. Record:

`evidence/2026-10-02_pgwr_snake_throw_lw/RESULT.md`.

**Build caveat for the installer:** `src/mythra/ness_throw_b.rs` (another agent,

in flight) does not compile - unresolved crate `singletons` - so the tree does

not build as a whole. My module was compiled and its NRO inspected in a *copy* of

the crate under `builds/.cache/snake-throw-lw-crate`; that NRO

(`ed9a790e7c8ab690...`, 471,040 B) is a **verification artifact, not shippable**.



**T-0060 (2026-10-02, Freebuff slot 4): Lucas's down smash on Mythra c06/c07 -

source complete, delta packaged and audited, PENDING, NOT installed, no console run.**

The full down-smash family: `AttackLw4` plus the `AttackLw4Hold` charge, all **seven**

of the donor's own scripts, his own clips and motion metadata, his 17/14/11 three-hit

frame data, his effects and his sounds. Registered on `elight` c06/c07, so it replaces

**stock Mythra's** down smash there - the G&W half of this mod is untouched, and the

three concurrent `eflame` tasks are untouched. ACMD

`plugin/src/mythra/lucas_attack_lw4.rs`; clips and motion by

`src/pgwr/tools/build_lucas_downsmash.py`; sounds by

`tools/merge_lucas_downsmash_sound.py`; effects by

`tools/build_lucas_downsmash_effect.py`; measurement by

`tools/audit_lucas_lw4_donor.py`; the 2-byte motion patch by

`tools/apply_lucas_downsmash_motion_list.py`; scope by

`tools/audit_lucas_downsmash_delta.py`. Only `mythra/mod.rs` was touched in the

shared tree (4 narrow additions).

*Three findings that would each have shipped a wrong move.* **(1)** The charge hold is

`attack_lw4_hold`, **not** `attack_lw4_charge` - a first pass looking for the latter

found nothing and read as a missing donor file, and the kind and the script name are not

a mechanical pair (kind `attack_lw4_hold`, script `game_attacklw4charge`). Proven by

re-parsing **G&W's** list and matching every field against

`dumps/scripts/gamewatch_motion_list.yml`, an independent dump of a different fighter.

**(2)** The motion-list delta is **two bytes**: Lucas `attack_lw4` cancel **316** against

Mythra's 56, differing at entry-relative offsets [62, 63] and nowhere else, while

`attack_lw4_hold` is **byte-identical** between the two fighters and needs no change at

all. **(3)** `havel`, which the charge orb is parented on, is **not a bone on either

fighter** - it is the engine's built-in hand anchor, the same class of name as `top`, so

the donor's anchors are used unchanged rather than remapped.

*Measured:* 66 of 68 transform nodes survive on the Mythra skeleton, 2 dropped

(`Bat`/`BatL`, his bat - so the move needs no article), 0 case-only matches and **0 parent

mismatches** (parent chains compared by name, which a name filter cannot do). All **17**

real limb bones present and measurably moving, and the build refuses to ship a static

one - the R.O.B. down tilt lesson. `LegL/R` 127/129 deg, `KneeL/R` 103, `ShoulderL/R`

122/139, `ArmL/R` 106/86, `HandL/R` 100/108, `Hip` 66. An earlier draft of that

measurement listed `ElbowL/R` and `WaistL/R`, which are **not bones on either fighter**,

so they reported as static forever; a gate that counts absent bones as static limbs is a

gate that cries wolf.

*Assets are recipient-owned, never donor folders:* `LUCAS_PSI_HOLD` and

`LUCAS_PSI_ATK_LW` merged into the already-declared `ef_elight_c06/c07.eff` (128 -> 130

emitters, **0 lost**, 0 texture/model ids relocated), because an `.eff` under

`effect/fighter/lucas/` is loaded by nobody. Sounds append to Mythra's own banks: all

**389** SE and **233** VC baseline tones per slot preserved byte-for-byte and in order,

**+5 SE** and **+1 VC**; no stand-in sounds (rule 17). **No `config.json` change** (both

clip names already exist at the same vanilla ARC path, asserted against

`dumps/decoded/arc_files.tsv`), **no new status id** (`attack_lw4`/`attack_lw4_hold` are

vanilla kinds, so Hero's Spin `0x1F1..0x1F4` and the next free id are untouched -

**nothing for the installer to allocate**), **no `elight.sqb` append** (the donor plays

no `PLAY_SEQUENCE`, read out of both pinned scripts), and no c00-c05 file touched.

*Package:* `builds/pgwr/T-0060-lucas-downsmash/`, a **delta only** - 24 mod files, mod

tree `f8666b2494f444809a7284bfc0d0e9e694620a6ea8ff837d0a5d1b4851e9fdc6`, audit

`BASELINE_DELTA.json` there. **Baseline is the installed 0.20.19 card tree, not vanilla**

- it carries the 25 Hero motion entries, so Mythra's lists are 759 entries and a vanilla

comparison would blame this task for 25 changes. Measured delta vs that baseline:

**16 overrides + 4 vanilla-path clip overrides, 0 removed, 0 unrequested**, all 759

entries compared with only `attack_lw4` changed. Compiled clean (no new warnings) in

`builds/.cache/pgwr-fb-4-lucas-downsmash-target`, features `snake-neutral-b,hero-side-b`,

`logging` off; NRO `b51dcb278e444e864a50729a764115725ef927bc905a01a6f1b1e34402898160`

(475,136 B) carrying all **21** checked markers.

***Build caveat, and it is the installer's:*** the shared plugin **does not currently

compile** - the concurrent Ness back-throw agent's

`src/pgwr/plugin/src/mythra/ness_throw_b.rs` references an unlinked `singletons` crate

(2 x E0433). Not my file, not edited. This task's module was compiled from an isolated

copy with only that module removed, so the NRO above is a **verification artefact, not

the package**; the installer must build from the shared source once that work compiles

and compare.

**Unverified: all behaviour** - no console, no emulator, no tests. Install section with

the 13-step test and integration commands: own section in `CURRENT_INSTALL.md`; evidence

`evidence/2026-10-02_pgwr_T-0060_lucas_downsmash/RESULT.md`, pins and inventory

`refs/lucas_attack_lw4/`.



**dk_cargo (2026-10-03, Codex): 0.1.1-test INSTALLED for hardware retest; corrected throws unverified.**

Card 5098/5098 files and NRO checked; frameworks unchanged. Install record:
`evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test_install/INSTALL.md`.


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

## gaogaen_throw_b — 2026-10-03 — READY: enabled installable package (G&W / eflame c06/c07)

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

Not installed; no SD/game/emulator access. Runtime unverified, including the pinned SIMD
hook ABI warning. Source/logger/package reproduction, installer command and ten manual
checks: `evidence/2026-10-03_pgwr_gaogaen_throw_b/RESULT.md`.
Move log: `sd:/ultimate/pgwr_gaogaen_throw_b_log.txt` (REGISTERED/ENTER/VICTIM_INIT/END).

## Feature state



Little Mac forward smash family (2026-09-30; neutral installed 2026-10-01, angled added

2026-10-01): **0.20.14 on the card and hardware-confirmed; 0.20.16 staged with the angled

variants, hardware result pending.** Forward smash, charge hold and the up/down-angled

variants on c06/c07 are Little Mac's own; ACMD `plugin/src/acmd/littlemac_attack_s4.rs`

(15 registered handlers), assets `tools/build_littlemac_fsmash.py`, donor pinned in

`refs/littlemac_attack_s4/` (18 files pulled live, since `dumps/arc/fighter/littlemac` is

empty on disk). His own motion entries - four of them, taken whole, cancel 44 vs G&W's 43 -

and four retargeted clips; 46/50 bones kept with 0 parent mismatches. Sounds are his own,

merged into Pyra's banks - no stand-ins.

**The earlier "the angled variants are unreachable" verdict was wrong and has been reversed.**

It rested on the name being absent from `main.bin`, which is true but does not imply

unreachable: 65 of the 72 fighters with a c00 motion list on disk *do* carry `attack_s4_hi` /

`attack_s4_lw` with their own clips, and the 7 that do not are simply characters whose angled

forward smash was never authored. No separate status is needed either - the motion-list entry

carries its own `game_script`, and the plugin registers all four handler sets to match. No

native hook is involved. What is still **tier D** is only whether the engine asks for those

kinds on this recipient; the 0.20.16 hardware run answers it, and a negative answer is inert

rather than a regression. Audit `refs/littlemac_attack_s4/audit_0_20_16.json`, tool

`tools/audit_littlemac_fsmash.py` (v1.1.0, which now also asserts the packaged NRO carries

every handler name and sound name this move needs).



Character Naming c06/c07 (2026-09-30): **Staged in `builds/pgwr/staged_names/`; READY in `CURRENT_INSTALL.md`**.

Tool `src/pgwr/tools/build_custom_names.py` routes `n06_index -> 6` ("Ursula") and `n07_index -> 7` ("Wilhelmine") for Pyra/Mythra pairs across categories 0..3 in `msg_name.xmsbt`. Vanilla slots and standalone G&W untouched. Not installed to card.



Hero side-B (2026-10-01): **INSTALLED 0.20.15 (2026-10-01), hardware test pending**.

Mythra c06/c07 side-B = Hero Zap/Zapple/Kazap, statuses `0x1FA..0x1FE`, feature `hero-side-b`.

Mana was off here until T-0057 (2026-10-02), which gave the pair its own meter; side-B

spends it in ATTACK1/2/3 and not in the finisher. Tier D until hardware.

Fighter + spark/lightning statuses and scripts owned in `src/pgwr/plugin/src/mythra/hero_side_b/`; native owned

copies at the three approved sites + Mythra receiver slot (approval recorded only in `receiver.rs`; confirm).

Tier-D items (Kazap finisher trigger, flare variant, trail tip) and the test: `CURRENT_INSTALL.md`.

Crash-tail log: `sd:/ultimate/pgwr_hero_s_log.txt`.



Snake neutral-B continuation (2026-09-30): **0.20.11 installed/verified; hardware pending**.

Canonical package/hashes/test: `CURRENT_INSTALL.md`; workflow: `AGENTS.md` rule 23.

Manifest: `builds/pgwr/0.20.11/MANIFEST.json`; baseline delta: `BASELINE_DELTA.json` there.

Opt-in `snake-neutral-b`; reserved Pyra `0x1FB..0x207`, next `0x208`.

Owned lower dispatch/ACMD, 29 motions/58 body clips, 152 pin files and nine donor

sounds are packaged with genuine item handling and authorized life bridge.

Release compilation, generator/native/lower/ABI checks, sound preservation and

package/baseline comparison pass offline. No console behavior verdict.

Global logging stays off; Snake crash-tail log: `sd:/ultimate/pgwr_snake_log.txt`.

Inputs/provenance: `refs/snake_grenade/{sequence,lower_body}/extraction.json`.

New-file inventory: `builds/pgwr/0.20.11/CREATED_FILES.json`;

continuation inventory: `refs/snake_grenade/CONTINUATION_FILES.json`.



| Feature | Evidence / current limitation |

| --- | --- |

| Pyra c06/c07 G&W body, motions and costume gate | Earlier console confirmation; vanilla controls still required on this release |

| Tilts, smashes, dash, grabs and throws | User previously described them as mostly right; small issues remain |

| G&W props | Appeared on 0.11.0; interrupt/landing fixes still need coverage |

| G&W up-air breath | Parameter bridge compiled; no fresh console verification |

| Pyra jab | Chrom hitboxes/animation confirmed on 0.16.0; cloned sword was inert (R-22). 0.20.0 gives it its own article states at 0.9x and its own trail tip. 0.20.9 routes custom Cloud sword trails (`tex_cloud_sword1/2`, recolored for c06 Black & Pink and c07 White & Champagne Gold) replacing placeholder Mythra trail; offline packaged, hardware test pending. **The 0.20.0-0.20.20 jab states never rendered: the appended motion-list entries hashed the clip name without its `.nuanmb` extension, so the article stayed on `z00close` whose `flamesword` track is False and overrode the ACMD's `set_visibility_whole(true)`. Byte-proven and fixed in `chrom_jab_sword` 1.0.0 (2026-10-03, two-file asset delta, READY, not installed, runtime tier D)** |

| Cloud fair / Pyra sword | Sword visibility confirmed on 0.15.1. 0.17.0's trail-tip change (`14.5 * 1.4`) is included; alignment untested, blade angle unresolved. 0.20.8: replaced Mythra trail with custom Cloud sword trails (`tex_cloud_sword1/2`) recolored for c06 (Black & Pink) and c07 (White & Gold) via `src/pgwr/tools/build_cloud_trail.py`; **confirmed working on hardware on 2026-09-30** |

| Monkey Flip | Animation/leap/kick confirmed on 0.15.0; 0.20.6 captures; victim T-pose; 0.20.7 side-B reuse restriction and capture releases **confirmed working on hardware on 2026-09-30** |

| Mythra Corrin uair, Hero Spin and Luigi dthrow | Registered c06/c07; still need fresh console coverage. **Hero Spin up-B air gravity retuned 2026-10-03: `AIR_ACCEL_Y_SCALE` 0.85 → 0.70, `AIR_SPEED_Y_SCALE` 0.90 → 0.70 (two literals, `mythra/hero_spin_params.rs`), installed in collective 0.20.22, retention unverified. Binding hit window 31→38 gap/band 0.81 → 0.63 measured by `tools/audit_hero_spin_airtime.py`. Finisher, frame data, landing/recovery and cleanup untouched. Evidence `evidence/2026-10-03_pgwr_upb_gravity/RESULT.md`** |

| Mythra Hero neutral-B | 0.18.0 crashed on full-charge shot (A); 0.18.1 supplies the constructor's map-collision params; 0.18.1 log shows 12 full shots without crash, user verdict not yet recorded. **0.20.0: small/medium charge levels were unshootable - `global_table[0x10]` pad-trigger read fixed to `0x1f`; 0.20.0 installed, hardware test pending** |

| Dark c06 / gold c07 themes | Offline asset checks pass; confirm appearance and effects on hardware. Lucas down-smash and Ness back-throw PSI themed to match 2026-10-03 (`lucas_ness_effect_theme-0.1.0`, READY, not installed, appearance unverified) |

| Judge | Removed; Monkey Flip owns side-B |

| G&W up-B Fire | Works on hardware (user, 2026-09-30, 0.20.x): move, props, parachute. Refresh came back only when hit (A); 0.20.4 adds landing/ledge via slot `+0x168` for Pyra and Mythra, untested |

| Down smash | **Lucas `AttackLw4` + `AttackLw4Hold` on Mythra c06/c07 (T-0060, 2026-10-02): source complete, delta packaged and audited, PENDING, not installed, behaviour unverified.** Seven donor scripts in `mythra/lucas_attack_lw4.rs`, registered on `elight` c06/c07 so it replaces stock Mythra there and leaves the G&W half alone. Clips retargeted 66/68 nodes, 0 parent mismatches, all 17 limb bones moving; `attack_lw4` cancel 56 -> 316 is a 2-byte motion delta and `attack_lw4_hold` needed none; PSI emitters merged into the recipient-owned `ef_elight_c06/c07.eff`; 5 SE + 1 VC tone appended with all 389/233 baseline tones preserved. No config change, no new status id, no c00-c05 file. Install section and 13-step test in `CURRENT_INSTALL.md`; evidence `evidence/2026-10-02_pgwr_T-0060_lucas_downsmash/`. The shared plugin does not currently compile - a concurrent agent's `ness_throw_b.rs` - so this task's compile used an isolated copy and its NRO is a verification artefact, not the package |

| Down tilt | T-0036 custom G&W recipient clip (165 tracks), staged variant `0.20.16+robot-dtilt.4`; preserves R.O.B. gameplay, frame-3 active/frame-4 clear, cancel 15, effects/sounds/rumble. Prior filtered clips rejected by user. Console pose/alignment judgment pending; no new hardware claim |

| Up tilt | **Snake `AttackHi3` implemented on c06/c07 2026-10-02 (Freebuff slot 2), audited, READY, not installed.** Scripts `acmd/snake_attack_hi3.rs`, clip + motion entry `build_snake_uptilt.py` (cancel frame 38, flags 0x84, 77 of 87 nodes kept, leg chain measured moving), sounds `merge_snake_uptilt_sound.py` (543/240 baseline tones preserved, `se_snake_attackhard_H01` + `vc_snake_attack01..04` + the `seq_snake_rnd_attack` record appended). Donor text re-pinned at `refs/snake_attack_hi3/donor_acmd/` because `dumps/scripts/` no longer has it. Delta audit passes vs installed 0.20.17. Behaviour unverified; hitbox bones `top`/`kneel`/`legl` absent on the recipient is the one open item. |

| Down throw | **Snake `ThrowLw` on c06/c07, 2026-10-02, audited, PENDING, not installed.** The move kind is `throw_lw` (`game_throwlw`), **not** `AttackLw4`, which is Snake's down smash - proven by his `attack_data_param.prc` (an `attack_lw4` record at cancel 56, no `throw_lw` record), by `game_attacklw4`'s `START_SMASH_HOLD`/`rbkind_smashhold1`/`PHYSICS_START_CHARGE`, and by an `AttackLw4Charge` follow-up. `game_throwlw` / `sound_throwlw` / `expression_throwlw` ported verbatim plus a deliberately empty `effect_throwlw` (the donor has none, so G&W's four down-throw effects stop). Motion entry is Snake's whole: cancel **50 -> 48**, 1 of 841 entries per slot, `attack_lw4` untouched at 34. Clip 77 of 87 nodes kept, all limbs measured moving. Sounds: **four** tones appended, because `se_snake_catch_tight` is the only kind-1 sequence tone in `se_snake_c00` and its child indices 92/93 are rebased to 545/546; 544 baseline tones preserved. **Victim prone via `collision_attr_lay` -> `LAY_DOWN`, not knockback** (kbg/fkb/bkb are all zero). No new status id, no config.json. Behaviour unverified. |

| Neutral-B | Snake grenade 0.20.11 ready for collective installation, hardware pending; `0x1FB..0x207` reserved, next Pyra id `0x208`. Chef not ported |

| Remaining G&W/Diddy sounds and effects | Incomplete; existing stand-ins/unresolved donor resources are outside this Hero port |

| Stats, hurtboxes, taunts, Final Smash/results/Kirby/CPU | Incomplete |

| Character Naming (c06 Ursula, c07 Wilhelmine) | Tool `build_custom_names.py` generated `ui_chara_db.prc` (n06->6, n07->7) & 40 `msg_name.xmsbt` entries; staged in `builds/pgwr/staged_names/`, READY in `CURRENT_INSTALL.md`; not installed on card |



## Hero neutral-B implementation and evidence



- User authorized building, installing and the plugin-local, byte-verified native initializer hook. The combined 0.17.0/0.18.0 run is explicitly requested despite the standing one-change rule.

- Five recipient statuses `0x1F5..0x1F9` follow Mythra's Hero Spin block. Six projectile statuses use the genuine cloned fireball's own weapon layout. State uses per-entry atomics rather than Hero fighter work IDs.

- Thirteen owned motion registrations per slot retain donor timing/flags and twelve distinct ground/air clips. Transform tracks are retargeted by matching bones and round-trip compared. Fireball model/motions are copied for all eight slots and declared in the fighter costume groups.

- Donor charge thresholds 18/81, kinetic parameters, cancels and successful shot ACMD are translated; mana prices/failure branches omitted. Hero's input is a second B/A press to shoot; releasing B alone is not its shoot trigger.

- The fireball class constructor `main+0x33c8ea0` reads Hero's decoded vl.prc object `*(*(main+0x52bb3b0)+0x1298)`, which was null on 0.18.0 hardware.

  An inline hook at `0x33c8ec4` supplies `map_collision_fireball{,_m,_l}` from the pinned vl.prc during our own initializer call only.

  Other native `+0x1298` readers are Hero fighter code, other Hero weapons' classes (vtables `0x51b04d8`, `0x51b2268`) or spell-list UI (`+0x360`); none are in the fireball class.

- Copied native initialization and ember helper use owned charge/parameter callbacks. Full 13.0.4 donor signatures are checked before registration. Original Hero calls retain the original initializer. Framework plugins were not rebuilt or replaced.

- Sixteen Hero effect resources retain donor fields/geometry/textures/shaders through re-export checks. Gold c07's texture collision is relocated with texture-field/mip controls. Sound merge preserves sample bytes, rebases random-group children and appends exact SQB records.

- File logging covers boot, gate, charge, transitions, playing clip frame/end, initializer entry/exit, article counts and projectile flight/hit/burst/removal.

- All results above are source/serialization/compilation evidence, **not a claim of console behavior**.



Evidence: `refs/brave_special_n/{SOURCE.json,DEPENDENCIES.json,acmd_pin.json,neutral_b_status.c,shoot_control.c,fireball_native.json,owned_initializer.json}`;

`refs/brave_special_n/sound/{SOURCE.json,extraction.json}`;

`evidence/build-archives/pgwr-0.18.0/{hero_neutral_b_assets.json,hero_neutral_b_sound.json,generated_effects/*.merge.json,MANIFEST.json}`.

Tools: `tools/{audit_hero_neutral_b.py,audit_hero_fireball_native.py,gen_hero_fireball_initializer.py,gen_hero_neutral_b_acmd.py,build_hero_neutral_b_assets.py,merge_hero_neutral_b_sound.py,merge_hero_neutral_b_effects.py,package_pgwr_release.py}`.



0.20.9 controlled console run is recorded in `evidence/2026-09-30_pgwr_0.20.9/RESULT.md`.

Current package tests are in `CURRENT_INSTALL.md`; Hero side-B source inventory:

`refs/brave_special_s/CREATED_FILES.json`.



## Pending up-B test (carried from 0.20.4)



1. Boot fresh; keep `sd:/ultimate/pgwr_log.txt` from `[PGWR] BOOT v0.20.6`. Boot lines: `[PGWR-UPB] READY Pyra class event slots ...`,

   `[PGWR-UPB] READY Pyra class +0x168 situation wrap`, `[PGWR-UPB] READY Mythra class +0x168 situation wrap`, `REGISTERED ... refresh on`.

2. Vanilla control: Pyra c00 and Mythra c00 land, jump, grab ledge normally; no `[PGWR-UPB]` lines from them.

3. Pyra c06: up-B, drift down, land, up-B again - must work. Log: `REFRESH entry N by G&W ground/ledge (+0x168)`.

4. Up-B, then cancel the parachute with an aerial and land - must refresh the same way.

5. Up-B, then grab the ledge - must refresh; up-B from the ledge jump.

6. Up-B in the air, press up-B again before landing - must NOT work (no refresh line in between).

7. Up-B, swap to Mythra (down-B), land as Mythra, swap back, up-B - must work. Log: `REFRESH entry N by Mythra ground/ledge (+0x168)`.

8. Get hit after up-B - still refreshes (`+0x220`).

9. Jab: the blade should be a touch smaller than before (0.9, first time on the card). Return the log from boot; on a crash, the crash report.



Fail: any `[PGWR-UPB] FAIL` (that slot's refresh is off), up-B usable twice in one airtime, or no refresh after landing.



## Monkey Flip / remaining diagnostics



Sources: `src/pgwr/plugin/src/status/monkey_flip.rs`, `monkey_flip_params.rs`, `src/pgwr/plugin/src/acmd/monkey_flip.rs`, `src/pgwr/tools/build_monkey_flip.py`.

Pyra status block `0x1EE..0x1F8` is separate from Mythra's status table. No per-frame state forcing is added.

`[PGWR-MFLIP] VICTIM`, `VICTIMSTATUS`, `CATCH HANDOFF`, `CLING` logs cover the unconfirmed victim half; compare a standing c06/c07 grab and real Diddy as controls before attributing a failure.

Live boxes without a handoff, a handoff with no advancing victim clip, an unchanged WAIT/WALK victim, and a connection freeze are different observations; none establish a cause without a controlled run. Existing camera accessor, donor effects and voice gaps remain.

Carrier clips include spare `d04final*` / `d04visualscene*` names; watch transformation/Final Smash for regressions. Retire spare-name carriers and old stand-ins through the standing own-status/own-assets method.



## Build/install workflow



`build.py` defaults to the Cargo semantic version directory; `build-plugin.sh --stage-only` uses `builds/.cache/pgwr-target` and stages that version's NRO.

`install-to-card.sh` autodetects the card, defaults framework installation OFF, backs up, verifies .new files/tree, and rolls back on failure.

Historical `history/HANDOFF_*` instructions describe a retired global-plugin approach and must not drive installation.

New-file inventory: `evidence/build-archives/pgwr-0.18.0/CREATED_FILES.json`; 0.19.0 up-B files are listed in CHANGELOG 0.19.0.



## Up-B (Fire) sources



`refs/gamewatch_special_hi/` (recovered status C, status table, `event_slots.json`); `src/pgwr/plugin/src/status/special_hi.rs`;

`src/pgwr/plugin/src/acmd/generated/special.rs` (`src/pgwr/tools/gen_acmd.py` R27-R30); `tools/{audit_event_slots.py,main_image.py,maindesc.py}`; `tools/nro_decomp/`.

Known gaps: sounds use the project's R2 stand-ins (`wave10_mi/hi` -> `se_eflame_swing_m01`, `wave03_mi` -> `se_eflame_throw_f01`; `wave10_lo` silent); G&W's up-B has no effect scripts in the dump, so none are played.

