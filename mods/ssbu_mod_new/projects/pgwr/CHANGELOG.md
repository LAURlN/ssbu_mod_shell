# Changelog

## pikachu-airb 1.0.0 — 2026-10-03 — READY, not installed

- Pikachu's `AttackAirB` and `LandingAirB` on the modded `eflame` pair, gated to
  c06/c07. Eight handlers ported verbatim from pinned donor scripts at
  `Priority::High`; owned clips, sounds and sequence record (rule 17), no
  stand-ins and no framework plugin.
- Narrow 19-file delta plus two source patches; NRO
  `9d0ee7edb554d402cf31ff12dce989319804b65fece8b9cae3787e4cc3eddcee`, reproducible
  twice, built in an isolated copy of the 0.20.23 snapshot so no other agent's
  live edit was compiled. `logging` OFF, the same three features as 0.20.23.
- Motion list: `attack_air_b` moves two bytes per slot (cancel 296->300, flags
  `0x0080`->`0x0084`); `landing_air_b` moves zero because it was already
  byte-identical. No config.json, param, effect, ui or other entry. No status id.
- Offline B: retarget gates, delta audit 128/128, 8 negative controls caught
  with a positive control, and a control build of the unmodified snapshot that
  reproduces the baseline NRO byte for byte. Runtime unverified (D).
  Evidence: `evidence/2026-10-03_pgwr_pikachu_airb/RESULT.md`.

## 0.20.23 — 2026-10-03 — INSTALLED; runtime unverified

- Silent release: 224 diagnostic file/console call sites feature-gated, including argument formatting. Existing logging feature OFF. User request overrides required crash-tail output for this release.
- All 0.20.22 gameplay and assets retained; isolated source reversal, binary log-path/HUD-signature checks and release build passed. Performance unverified on console.
- Later user-requested installation verified 5099 files and protected plugins. Pending mana fixes excluded. Record/test sheet: `evidence/2026-10-03_pgwr_0.20.23_silent/INSTALL.md`.

## 0.20.22 — 2026-10-03 — installed; runtime unverified

- Collective Hero Zapple angle, owned battle mana HUD on both forms, and Hero Spin air gravity scales 0.70/0.70.
- Preserved all installed assets/previous moves and framework plugins. Isolated build and offline audits passed; all card hashes verified. Dashgrab excluded.
- Record/test sheet: `evidence/2026-10-03_pgwr_0.20.22_install/INSTALL.md`.

## 0.20.21 candidate / Hero HUD-angle task 0.1.1 — 2026-10-03 — READY, not installed

- Continue Opus's Zapple level-2 effect-angle candidate and explicitly authorized native MP HUD on both modded c06/c07 forms. Preserve level 1/3, hitboxes and knockback.
- Fix HUD per-entry refusal/reset lifetime and count instant-set initialization by frames rather than MP changes. Reserved hit/shield recovery stays off.
- Isolated combined, angle-only, HUD-only and rebuilt baseline controls; narrow patches; latest 5099-file ready-assets.1 retained with info version only. Installed DK cargo/Incineroar preserved; unrelated in-flight source excluded.
- Builds, native signature/structure audits, negative controls, source/asset hashes and patch reproduction pass (B). All visual/lifecycle behavior unverified (D). Evidence: evidence/2026-10-03_pgwr_zapple_mana_hud/RESULT.md.


## 0.20.20+ready-assets.1 — 2026-10-03 — installed, visuals unverified

- Asset-only partial batch: jab sword animation-name hashes, Lucas/Ness c06/c07 themes and loading-screen starting-form assets/database routes.
- Seven files changed, one added; NRO and every unrelated baseline file preserved. 5099/5099 card files and protected plugin hashes verified.
- Hero angle/HUD, dash-grab and up-B gravity not included. Record: `evidence/2026-10-03_pgwr_ready_assets_1/INSTALL.md`.

## Lucas / Ness effect themes 0.1.0 — 2026-10-03 — READY, not installed

- Mythra c06/c07: Lucas down-smash charge orb and bursts and Ness back-throw PSI re-coloured to
  the costume palettes (c06 scarlet/crimson/magenta/violet; c07 white/gold/light pink). 17 emitter
  colour edits and 2 task-owned colour-baked star textures per slot; timing, alpha, scale,
  emission, shaders and models unchanged. No gameplay, NRO, config, motion or sound change.
- New `tools/customize_lucas_ness_effects.py` 1.0.0: semantic bank merge with recorded input
  hashes; package `builds/pgwr/lucas_ness_effect_theme-0.1.0/` (two `.eff` files) over the latest
  installed `dk_cargo-0.1.1-test`. Installer owns the collective version.
- B verified: converter round trip, 3543 unrelated decoded entries identical, 0 changed bytes
  outside owned ranges, reproducible, idempotent, negative and concurrent-addition controls,
  loader resolution. Appearance in game unverified (D). Evidence:
  `evidence/2026-10-03_pgwr_lucas_ness_effect_theme/RESULT.md`.

## Chrom jab sword 1.0.0 — 2026-10-03 — READY, asset-only delta, not installed

- **The Chrom jab's blade was invisible on hardware through 0.20.0-0.20.20 (user,
  2026-10-03) and the cause is byte-proven.** `build_esword_pose._build_jab_mlist`
  wrote the two appended motion-list entries' animation-name hash as
  `hash40('jabopen')` / `hash40('jabtoopen')`, but an animation-name hash covers the
  file name **with its extension** — every vanilla entry of that article proves it
  (`open` → `0xe32317ab0` == `hash40('z00open.nuanmb')`). Both jab entries named a
  file that does not exist, which is silent: no error, no log. The article kept
  playing `z00close`, whose `flamesword` **mesh visibility track is False**, and that
  track overrode the `set_visibility_whole(true)` the ACMD issues at frame 3. The
  Cloud fair was unaffected because it drives the vanilla `to_open` kind.
- Fixed in `src/pgwr/tools/build_esword_pose.py` 1.1.0: write the extension, and
  assert twice per build that each new hash resolves to a real file — once against
  the vanilla entry being cloned, once against the bytes read back off disk. The
  same module now also finds the ArcExplorer export through `paths.toml`, so it can
  run in this workspace at all (`dumps/arc` is absent), falling back rather than
  raising so `build.py`'s module-level import is unaffected.
- **Delta: two files, 884 bytes each, unchanged in size.** Differing byte offsets
  per slot 804–808 and 856–860, both inside the appended entries.
  `8b7be43a2435c971…` → `1816a2913b778433…` for
  `fighter/eflame/motion/esword/c0{6,7}/motion_list.bin`. The other 22 files of the
  article folders regenerate byte-identical, and nothing else in the 5098-file tree
  differs. **No Rust changed, so no NRO rebuild and none should be copied.**
- **No second visibility guard and no "always show the sword" fallback.**
  `attack_air_f::esword_visibility_guard` stays the single owner, and the global
  lever would have masked the real defect while breaking the fair's put-away.
  `chrom_jab.rs` changed **documentation only**.
- New `tools/audit_chrom_jab_sword.py`: **96 checks, 0 failures** on the delta with
  all four negative controls caught, and **10 failures when run against the
  installed baseline** — so a `PASS` is a statement about the fix rather than about
  the audit having run. Checked unchanged: `attack_11`/`_12`/`_13` still name
  `c00attack11.nuanmb` at cancel 23, `attack_air_f` still names
  `c05attackairf.nuanmb`, `config.json` still declares both jab clips, and
  per-state visibility/scale is intact (1.4 fair / 0.9 jab).
- Expected merged mod tree `1091b63be89a26bb319eeb38879e2d166cc66a0946e940ccea6a9e04d4f080cf`
  (5098 files) if nothing else is merged in.
- **All runtime unverified — tier D.** No build, no game, no emulator, no console,
  no card. Package `builds/pgwr/chrom-jab-sword-1.0.0/`; record
  `evidence/2026-10-03_pgwr_chrom_jab_sword/RESULT.md`; installer section and the
  14-step test in `CURRENT_INSTALL.md`.
- Recorded as *not* shipped: the article's `game_toopen` script is not in this
  workspace, so whether the jab settles in its own 0.9 state or the fair's 1.4 one
  cannot be settled offline — that is the expected next failure and it is a size
  problem, not a visibility one. Also not shipped: the
  `ADD_PARTIAL_MTION_SWORD_WHEN_CHANGEING` flag that every vanilla sword-drawing
  eflame script sets, because it is never cleared and therefore latches on anyway,
  so shipping it would only muddy attribution.

## Hero's Spin up-B air gravity 0.70/0.70 — 2026-10-03 — source complete, not installed

- Mythra c06/c07 up-B (Hero's Spin, Mii Swordfighter `Hi3`): `AIR_ACCEL_Y_SCALE` 0.85 → **0.70**
  and `AIR_SPEED_Y_SCALE` 0.90 → **0.70** in `mythra/hero_spin_params.rs`. Effective accel
  0.09010 → **0.07420** u/f², terminal 1.39500 → **1.08500** u/f. Two `f32` literals; nothing else.
  User request: "opponents still fall out of Mythra up-B too often."
- **Explicitly labelled intentional custom tuning**, not donor data: Mii's dedicated `Hi3` kinetic
  cannot be installed on `elight`, so the mod rescales Mii's *common* air values by hand. The file
  header now records the whole chain (build .c 1.00/1.00 → .d 0.85/0.90 → now), states the numbers
  are meant to be retuned again, and corrects the previous header's claim that they were "the
  donor's own tuning" — they are the donor *project's* tuning, from one trace of this move on this
  recipient.
- Chosen from a measurement, not a feel: new tier-B tool `tools/audit_hero_spin_airtime.py` reads
  the constants out of the Rust source and the donor's own `ATTACK` literals out of the ACMD, and
  reports per hit window the attacker descent since the previous window as a fraction of that
  window's box band (`gap/band`). The binding window is 31 → 38, the only seven-frame hole in the
  donor's schedule: **0.81 → 0.63**. Descent over the string falls 58.2 → **45.8** u; the finisher
  at frames 47/48 still connects. Below ~0.55 the move stops reading as falling, which is why it
  stopped here.
- No permanent hover: the phase still exits on ground contact (`LANDING_FALL_SPECIAL`) and at the
  end of the 85-frame motion (`FALL_SPECIAL`), and `air_exec` is registered on `STATUS_AIR_SPIN`
  alone so it stops applying the instant the phase ends. `--check` asserts the descent stays
  strictly monotone, with zero-scales and 1.0-scales as negative controls.
- **Unchanged and checked unchanged:** launch, the frame 47/48 finisher, damage/knockback/hitbox
  geometry/frame data (`hero_spin_acmd.rs` byte-identical), landing and recovery, `end()`'s
  `AttackModule::clear_all` + jostle restore, status ids `0x1F1..0x1F4`, the costume gate, motions
  and trail. No fighter-wide parameter, no victim gravity, no opponent constraint, no unrelated
  attack buff, no asset, status id, motion entry, sound bank or `config.json` change.
- **Not bundled on purpose:** moving `JostleModule::set_status(false)` from frame 11 to frame 8 (the
  first box opens with jostle still on — a real one-frame retention gap). It edits donor frame data
  and would make the package two state-changing changes, so it is recorded as the first candidate
  for the *next* controlled build.
- Offline: audit `--check` PASS (2 negative controls); offline release build clean, no new warnings;
  NRO `f2634b91fa4e5360f9de235d0f6b735c68b8dac574636680a0e61b2ac37ecda4` (487,424 B), reproducible,
  and **different** (`65107e7b…`) when rebuilt at the old values — the constants are genuinely
  compiled in. Isolated cache `builds/.cache/pgwr-fb-upb-gravity-target`. That NRO is a
  **verification artefact, not a package**; the installer must rebuild from shared source.
- **Hit retention is unverified until the console run.** Evidence, hashes, build command and the
  9-step test (vanilla + Pyra controls, retention at low/high damage, small/large opponents, both
  facings, grounded/aerial starts, DI, finisher, landing, recovery, cleanup, regression sweep):
  `evidence/2026-10-03_pgwr_upb_gravity/RESULT.md`.

## Loading presentation 0.1.0 — 2026-10-03 — READY, not installed

- Reuse exact installed themed G&W loading artwork for eflame-first c06/c07;
  clone four recipient layout rows with only category-3/eye-flash donor fields,
  route those four costumes by measured cNN lookup. Preserve Mythra and names.
- Deliver semantic shared-database union tool, four-file delta/manifest and decoded
  previews; installer owns collective version. No gameplay/NRO/config/framework change.
- B verified: 5098-file latest installed-package baseline includes Incineroar and
  DK cargo; 5095 files unchanged, 3 changed + 1 added, native mapping and 16 matrix
  routes, reproducibility, PRC round trips and concurrent-field controls PASS.
  Visual/runtime result unverified. Evidence/test instructions:
  `evidence/2026-10-03_pgwr_loading_presentation/RESULT.md`.

## 2026-10-03 — user console verdict / next batch requested

- User reports latest mod works great overall; recorded with remaining issues and scoped six-agent handoffs in `evidence/2026-10-03_pgwr_user_verdict/RESULT.md`. No new code/build/install in this handoff session.

## gaogaen_throw_b 0.3.0 on 0.20.20 — 2026-10-03 — installed, hardware unverified

- Installed Incineroar's back throw on G&W `eflame` c06/c07 at owned status `0x208`, the only READY
  queue section. Everything from 0.20.20 remains on the card; shared plugin/`info.toml` version is
  deliberately **not** bumped and stays 0.20.20, so this is a task-package identity, not a release.
- NRO `5d7d9b8e565d9b38d6a73d804a36f4028e6fcd80ff92f15739ed96f3b783689b` (487,424 B);
  mod tree `7a33ab21e5a6c313b20c7c6160d4b7cf92914bf759a45be11a5c4364e50bae2c` (1992 files).
  Delta vs 0.20.20: 15 changed, 2 added owned clips, 0 removed. dk_cargo (incomplete) and T-0054
  (pending) excluded.
- Verified offline: package check PASS; card read 1990/1990 equal *before* the write and 1992/1992
  equal *after*, against both the package and the manifest's own hashes, with a recomputed card tree
  hash matching; built NRO equals staged NRO from the package's own cargo cache; motion lists show
  one key added and zero existing entries altered; all prior sound tones and samples byte-equal.
- **No gameplay claim.** Runtime is tier D. The pinned SIMD `Vector3` hook-ABI warning is unresolved
  and compilation cannot settle it. Evidence:
  `evidence/2026-10-03_pgwr_0.20.20+gaogaen_throw_b/INSTALL.md`; test sheet `.../RESULT.md`.

## 0.20.20 — 2026-10-02 — installed, hardware unverified

- Combined Snake down throw on G&W and Lucas down smash/Ness back throw on Mythra c06/c07. Semantic merges preserve both Mythra motion edits and all donor effect/sound additions.
- DK cargo and Incineroar back throw remain incomplete and excluded.
- Fresh offline build, 1990-file card equality and protected-plugin hashes verified. Evidence: `evidence/2026-10-02_pgwr_0.20.20/INSTALL.md`.
- Corrected Ness ATTACK_ABS documentation (11 damage, angle 135, KBG 130, BKB 15); runtime constants unchanged.

## Snake down throw (ThrowLw) on G&W c06/c07 - 2026-10-02 - PENDING, no shared release bump

- Target `eflame` c06/c07, so it replaces **G&W's own down throw** on those
  costumes and leaves every other move and every vanilla costume alone.
  Registered on the same gated agent as the other overrides, so c00-c05 keep
  every stock script pointer.
- **The move kind is `throw_lw`, not `AttackLw4`.** They differ by one word and
  both exist in Snake. `AttackLw4` is the **down smash**: his
  `attack_data_param.prc` carries an `attack_lw4` AI record at `cancel_frame: 56`
  and no `throw_lw` record, `game_attacklw4` opens with `START_SMASH_HOLD` /
  `se_common_smash_start_02` / `rbkind_smashhold1` / `PHYSICS_START_CHARGE` with
  an `AttackLw4Charge` follow-up, and the two kinds differ in clip
  (`e01throwlw` vs `c04attacklw4`) and cancel (48 vs 56). `AttackLw4.txt` and
  `AttackLw4Charge.txt` are pinned at the same commit as the control.
- **`game_throwlw`, `sound_throwlw` and `expression_throwlw` are ported
  verbatim**, including the three `FIGHTER_STATUS_THROW_WORK_INT_TARGET_*` reads
  and the `ATK_HIT_ABS` release on bone `throw` at frame 35.
- **The victim's prone outcome is `collision_attr_lay`, not knockback.** The
  donor's throw box is damage 9.0, angle 270, with **kbg/fkb/bkb all zero**, so
  there is no launch to copy; the attribute routes the victim to the engine's
  `FIGHTER_STATUS_KIND_LAY_DOWN` (0x56) instead of `DAMAGE_FLY*`, and the get-up
  is the victim's own state. Recorded so a later reader does not "simplify" the
  two `ATTACK_ABS` calls into a plain launch.
- **A deliberately empty `effect_throwlw` is registered.** Snake's `ThrowLw`
  defines no effect script; G&W's defines four. Omitting the handler would have
  left the generated Default one installed, so G&W's effects kept playing over
  Snake's silent throw while the NRO still carried them. Found by inspecting the
  built NRO.
- **Four** tones are appended, not the two the script names:
  `se_snake_catch_tight` is the only **kind-1 (sequence)** tone among the 111
  tones of `se_snake_c00` and references `se_snake_catch_tight_01` and
  `..._01_layer` by bank-relative index 92/93, which are rebased to 545/546. The
  shared codec's `group_links` asserts on donor tone kinds other than 0 and 3
  and correctly refused; appending the two named tones alone would have produced
  a byte-consistent bank whose grab sound points at two unrelated tones already
  at index 92/93 in Pyra's 544-tone bank. 544 tones preserved per slot.
  No `PLAY_SEQUENCE` is played, so `eflame.sqb` is deliberately untouched.
- Motion metadata is the donor's, entry whole: `throw_lw` cancel **50 -> 48**,
  flags `0x80` unchanged, **1 of 841** entries changed per slot, file size
  preserved. `attack_lw4` (the down smash) stays at cancel 34 and is asserted
  untouched.
- Clip retargeted onto the built c06/c07 skeleton: 77 of 87 transform nodes
  kept, the 10 dropped are `FaceN` and the nine `S_Bandanna*`, 0 case-only
  matches, and **every limb bone measured moving** against the recipient idle -
  the build refuses a static limb, which is the R.O.B. down-tilt failure mode.
- **No custom status id**: `ThrowLw` is a vanilla status kind. Next free Pyra id
  stays `0x208`. No `config.json` change (no new clip names), no c00-c05 file, no
  Mythra file, no `status/mod.rs` edit, **no shared version bump**.
- Shared tree touched only in `acmd/mod.rs`, three narrow hunks, with an
  unapplied copy at
  `refs/snake_throw_lw/integration/0001-acmd-mod-add-snake_throw_lw.patch`.
- Verified offline (tier B): donor inventory, delta build, sound merge with two
  negative controls, delta audit, and a clean `cargo skyline build --release
  --features snake-neutral-b,hero-side-b --offline`. **All behaviour unverified** -
  no console, no emulator, no tests, no card access.

## T-0060 Lucas down smash on Mythra - 2026-10-02 - PENDING, no shared release bump

- Target Mythra (`elight`) c06/c07, so this replaces **stock Mythra's** down smash there
  and leaves the G&W half of the mod untouched. Full family: `AttackLw4` plus the
  `AttackLw4Hold` charge, all **seven** of the donor's own scripts in
  `plugin/src/mythra/lucas_attack_lw4.rs`, his own 17/14/11 three-hit frame data, effects
  and sounds. Only `mythra/mod.rs` was touched in the shared tree (4 narrow additions).
- Clips retargeted onto the Mythra skeleton: 66 of 68 nodes survive, the 2 dropped are
  `Bat`/`BatL`, 0 case-only matches, **0 parent mismatches**; all 17 real limb bones
  present and measurably moving, and the build refuses to ship a static one.
- Motion metadata is the donor's: `attack_lw4` cancel **316** against Mythra's 56, a
  **2-byte** delta at entry-relative offsets [62, 63]; `attack_lw4_hold` is
  **byte-identical** between the two fighters and needed no change. The charge kind is
  `attack_lw4_hold`, not `attack_lw4_charge` - proven against G&W's independently dumped
  motion list.
- Assets are recipient-owned: `LUCAS_PSI_HOLD` / `LUCAS_PSI_ATK_LW` merged into the
  already-declared `ef_elight_c06/c07.eff` (128 -> 130 emitters, 0 lost, 0 id
  relocations) rather than shipping a donor `.eff` nothing loads; 5 SE + 1 VC tone
  appended to Mythra's own banks with all **389** SE and **233** VC baseline tones
  preserved byte-for-byte. No stand-in sounds.
- No `config.json` change (both clip names already exist at the same vanilla ARC path),
  **no new status id** (vanilla kinds, so Hero's Spin `0x1F1..0x1F4` and the next free id
  are untouched), no `elight.sqb` append, no c00-c05 file.
- Delta package `builds/pgwr/T-0060-lucas-downsmash/` against the **installed 0.20.19**
  baseline (not vanilla - it carries the 25 Hero motion entries): **16 overrides + 4
  vanilla-path clip overrides, 0 removed, 0 unrequested**. Offline checks pass with
  negative controls; release compile clean with no new warnings.
- **Not installed, no console run, no emulator, no tests - all behaviour unverified.**
  The shared plugin does not currently compile (a concurrent agent's `ness_throw_b.rs`
  references an unlinked `singletons` crate), so this task compiled from an isolated copy
  and its NRO is a **verification artefact, not the package**.
- Evidence `evidence/2026-10-02_pgwr_T-0060_lucas_downsmash/RESULT.md`; pins and
  inventory `refs/lucas_attack_lw4/`; install section and 13-step console test in
  `CURRENT_INSTALL.md`.

## 2026-10-03 — dk_cargo 0.1.1-test (INSTALLED controlled retest)

- User-authorized installation: 5098/5098 card files verified, NRO matches
  build/package, protected plugins/Skyline unchanged; backup and record in
  `evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test_install/INSTALL.md`. Gameplay unverified.

- Hardware 0.1.0: pickup/carry/jumping/release exercised successfully; three
  directional cargo throw crashes at null native shared-motion capture reference.
- Preserve queued stock victim states through three owned End/Exit comparisons;
  exact scalar alias control checks and isolated build passed. Runtime fix unverified.
- No assets, status allocations, shared registrations or frameworks changed.
  Evidence and hashes: `evidence/2026-10-03_pgwr_dk_cargo-0.1.1-test/RESULT.md`.

## 2026-10-03 — dk_cargo 0.1.0-test (Codex; INSTALLED for hardware test)

- User-authorized installation: 5098/5098 card files verified, NRO matches
  build/package, protected plugins/Skyline unchanged; backup and record in
  `evidence/2026-10-03_pgwr_dk_cargo-0.1.0-test_install/INSTALL.md`. Gameplay unverified.

- Added owned pickup/carry/ground-air/directional throw and victim callback
  runtime, escape/release/cleanup, approved receiver extensions as a narrow
  unapplied patch, and an isolated combined candidate over Gaogaen 0.3.0.
- Offline build and package/ABI checks passed; production allocation pending;
  no install or runtime conclusion. Full hashes, dependencies, failures and
  hardware checklist: `evidence/2026-10-03_pgwr_dk_cargo/RESULT.md`.

## 2026-10-02 — dk_cargo research.1 (Codex; INCOMPLETE, NOT READY)

- Recovered forward-grab direction dispatch, existing-link pickup/throw events,
  mash message, generic lift callback and native offset dependencies (offline B).
- Pinned 207 conservative donor functions, 97 common functions, 94 victim motion
  lists, body suffix routing and 15 donor pose templates. Semantic graph incomplete.
- Added 30 checked template deltas to the existing 28 attacker clips/bank deltas.
- Recorded explicit authorization for +0x170/+0x210 cargo extensions; unimplemented.
- Corrected PLT artifacts, victim motion names and inferred camera hook requirement.
- Requested 15 attacker + three victim roles per eligible table; no IDs chosen.
- No runtime implementation/build, registration patch, shared version bump or install.
- Package/reproduction/evidence: own `CURRENT_INSTALL.md` entry.

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

## 0.20.19 - 2026-10-02 - collective install of three Freebuff tasks

- Packaged and installed: Little Mac forward-smash fist trails (eflame c06/c07 slot banks, donor
  folder bank removed), Snake up tilt on c06/c07, Hero mana for the c06/c07 pair (feature
  `hero-mana-reserved` off), plus the T-0052 Kazap arrival change built earlier as 0.20.18.
- NRO `1771152551c8...`, tree `755e3e5543dd...`, 1984 files; delta vs 0.20.17: 19 changed, 2 added,
  1 removed. Assembled from the 0.20.17 tree plus measured deltas; `build.py` not run.
- Tools: `package_pgwr_release.py` follows the last sound merge in the chain;
  `audit_snake_uptilt_delta.py --combined` accepts other changes' added/removed files;
  `audit_littlemac_fsmash.py` honours `MGW_EXPORT`.
- Unverified: all behaviour. Record `evidence/2026-10-02_pgwr_0.20.19/INSTALL.md`.

## 2026-10-02 (Freebuff slot 1) - Little Mac f-smash fist trails on G&W c06/c07: source READY, not packaged, not installed

- **The fist trails now have a bank their own fighter can load.** The move's ACMD already
  asked for Little Mac's own `littlemac_attack_line` / `littlemac_attack_arc`; the emitters
  were shipped in `effect/fighter/littlemac/ef_littlemac.eff`, a folder no `eflame` loader
  ever searches, so both calls were silent no-ops. They are now merged into
  recipient-owned `effect/fighter/eflame/ef_eflame_c06.eff` and `..._c07.eff`
  (both sha256 `6ab84bb729d8...`), declared per costume group, with the donor-folder bank
  removed from the payload. Vanilla `ef_eflame.eff` is untouched, so c00-c05 and standalone
  Mr. Game & Watch are unaffected. No stand-in effect, no `sys_*` substitute.
- **Merge, not replace: all 95 vanilla eflame emitters survive, exactly 2 are added**, and
  the packed bank is re-read and compared field by field - decoded emitter data, opaque
  subsections and geometry/texture/shader payloads all byte-identical.
- **Defect found and fixed: a model-id collision is silent.** `LITTLEMAC_ATTACK_ARC` ships a
  G3PR whose descriptor id `1347192488` is already used by a *different* Pyra mesh, and
  `PrimitiveInfo.AddPrimitive` returns without a word on a duplicate id - the arc would have
  drawn Pyra's model, with every offline check still green. `merge_hero_neutral_b_effects.py`
  is now 1.2.0: `.bfres` ids and model names relocate alongside `.bntx`, rewriting only the
  three fields that name a model. `1347192488` -> `95091467`, name `pgwr_hero_95091467`.
  `handbook/graveyard.md` R-EFF-MERGE-1.
- **The effect converter is reproducible instead of lost.** The pinned commit is the HEAD of
  the public MIT repo KillzXGaming/EffectLibrary; `tools/fetch_effect_library.py` fetches and
  verifies it, and `build_hero_effect_converter.py --from-source` compiles it project-locally
  into `builds/.cache/` (nothing installed system-wide). Upstream `Program.cs` does not
  compile standalone - the tool adds the one missing `using`. `handbook/graveyard.md` R-EFF-MERGE-2.
- **Tools:** `build_littlemac_fsmash_effect.py` 2.1.0 (+`--check` smoke test),
  `build_hero_effect_converter.py` 1.1.0, `merge_hero_neutral_b_effects.py` 1.2.0,
  `audit_littlemac_fsmash.py` 1.2.0, new `tools/fetch_effect_library.py`.
- **No Rust changed and no version bump is required for this part** - the ACMD was already
  correct; only the bank it resolved against was wrong. The plugin still compiles in its own
  cargo cache and the built NRO carries all four effect handlers plus both emitter names.
- **Not done here:** the full `src/pgwr/build.py` run (`dumps/arc` does not exist in this
  checkout and `build_chrom_jab.py` hard-codes it), packaging, install, and every behavioural
  question - whether the line and arcs draw, and whether the arc is now the right mesh, is
  **unverified** hardware. Record and installer procedure: `CURRENT_INSTALL.md` and
  `evidence/2026-10-02_pgwr_T-0050/RESULT.md`.

## 2026-10-02 (Freebuff slot 2) - Snake up tilt (AttackHi3) on G&W c06/c07: source + offline audit, READY, not installed

- **G&W c06/c07 up tilt is Snake's `AttackHi3`**: his own four scripts, his own clip
  retargeted onto the built recipient skeleton, his own `attack_hi3` motion entry whole
  (cancel frame **38**, flags **0x84**, `game_script` `game_attackhi3`) and his own sounds.
  Gated by `set_costume([6,7])`, registered at `Priority::High` over the generated G&W
  `AttackHi3`. No new status id (`AttackHi3` is a vanilla status kind; next free Pyra id
  stays `0x208`), no article, no work-id write, no stand-in.
- **New files:** `src/pgwr/plugin/src/acmd/snake_attack_hi3.rs`,
  `src/pgwr/tools/build_snake_uptilt.py`, `tools/merge_snake_uptilt_sound.py`,
  `tools/audit_snake_uptilt_delta.py`, and the re-pinned donor ACMD under
  `refs/snake_attack_hi3/donor_acmd/`.
- **The donor ACMD text had to be re-pinned from upstream.** `dumps/scripts/` no longer
  holds `SSBU-Dumped-Scripts-main`, so the path TODO.md cites is gone and the external
  export named by `paths.toml` is nearly empty. Rule 17 forbids approximating it, so the
  same commit the project already pins (`59004685238a3f6f93bae905d3a4e079701c40b4`,
  WuBoytH/SSBU-Dumped-Scripts) was fetched again and hashed. R.O.B.'s `AttackLw3.txt` came
  with it as a control, because the shipped `acmd::robot_attack_lw3` was written from that
  exact file - reading the two side by side is what shows how much the dump loses. Snake's
  AttackHi3 has no branch, no lost braces and no article call, so nothing was dropped.
- **Measured (tier B):** 87 -> 77 transform nodes kept, the 10 dropped are `FaceN` and the
  nine `S_Bandanna*` nodes, 0 case-only matches, 98 visibility nodes from the recipient
  idle, Material group dropped, 48 frames. **The leg chain carries the kick** - the
  failure the user rejected on the R.O.B. down tilt is now measured and asserted, not
  assumed: `LegL/R` 92.6/78.0 deg, `KneeL/R` 97.8/80.6, `FootL/R` 102.6/54.4,
  `ToeL/R` 0.59 units of translation. `deploy_for_slot` refuses to write a clip whose leg
  chain is static.
- **Sound merge is append-only and proved so:** `se_eflame_c06/c07` keep all 543 tones
  byte-for-byte and gain only `se_snake_attackhard_H01`; `vc_eflame_c06/c07` keep all 240
  and gain only `vc_snake_attack01..04` (the four names are measured out of the
  `seq_snake_rnd_attack` record by CRC32, not listed by hand); `eflame.sqb` keeps 13
  records and gains that record, idempotently.
- **Verification:** plugin compiles with no errors in cache
  `builds/.cache/pgwr-fb-2-snake-up-tilt-target`, NRO
  `75deff8de447f8f4d171539d8791f046e5c190a60901b05b5ec9ddef809dc313` (466,944 B) carrying
  all four handler names, both sound names and both effect names. Delta audit passes
  against the installed 0.20.17: 18 changed files, 0 added, 0 removed, `attack_hi3` the
  only motion-list change per slot, banks/sqb append-only, no c00-c05 file in the delta,
  with three negative controls that all fire. Evidence
  `evidence/2026-10-02_pgwr_snake_uptilt/`.
- **Deliberately unchanged:** the hitbox bones stay `top`/`kneel`/`legl` as the donor wrote
  them. G&W's own up tilt - the handler this replaces - also writes `top`, so remapping two
  of the three would make this handler differ from the one it supersedes on a question no
  offline measurement can settle. None of the three names is on the built c06/c07 skeleton;
  that is measured, carried into the manual test, and flagged as the one open item.
- **NOT installed, NOT packaged by me.** Rule 23: the designated installer agent builds,
  packages and installs. Installer section with commands and a 12-step console test:
  `CURRENT_INSTALL.md`, "Snake up tilt (AttackHi3) on G&W c06/c07".
- **Unverified: all behaviour.** No console, no emulator, no automated test.

## 2026-10-02 (Freebuff slot 3, T-0057) - Hero mana on the c06/c07 Pyra/Mythra pair: source READY, not packaged, not installed

- **The mana system was missing, not broken.** The Hero neutral-B and side-B in this mod
  hard-wired the donor's affordability gate to "always yes" and never kept an MP value, so
  there was nothing to repair. `mana=off` in the neutral-B gate log, "SUCCESS_SP is always
  true" in the side-B module docstring, "Mana prices excluded" in `donor_params.rs` and
  "Hero neutral-B without mana" in the boot banner were the whole of it.
- **The six prices are measured, not remembered:** N1/N2/N3 = 6 / 16 / 36, S1/S2/S3 = 8 /
  18 / 42, `sp_max` 100, `recover_sp` 1 every `sp_recover_frame` 60 frames, hit and shield
  multipliers 0.8. All of it out of the pinned donor `fighter/brave/param/vl.prc`
  (sha256 `dafa43c6...`, from `gamedata/ssbu-13.0.4/data.arc` `ef615e67...`), decoded by
  the new `tools/dump_hero_mana_params.py`. Every Hash40 key matches the key the
  T-0033/T-0049 contract had predicted from `ParamLabels.csv`.
- **The gate is the donor's, at the donor's sites.** `price <= mp` decides and the debit
  happens only on success, once per cast: neutral-B's SHOOT MAIN, side-B's ATTACK1/2/3
  MAINs, and **not** the Kazap finisher, matching the pinned caller list in
  `refs/brave_special_s/flag_success_sp.c`.
- **Out of MP is the donor's out of MP.** The motion plays, nothing is spent, and no
  projectile, no sparks and no lightning appear - the three paths the donor itself gates
  on `SUCCESS_SP`. One `REFUSE` line with the shortfall, never a silent no-op.
- **One meter for the pair.** Keyed by the entry/player slot with both `eflame` and
  `elight` accepted for a c06/c07 entry, so the value survives the down-B swap with no
  copy step; recovery follows whichever half is the active body. Reset to full once per
  stock on `DEAD`/`REBIRTH`/`ENTRY` and on a new match, and passive recovery pauses while a
  spell charges, as the donor's own `DISABLE_SP_AUTO_RECOVER` does.
- **Bounded event logging, always on:** `sd:/ultimate/pgwr_mana_log.txt`, one line per
  `CAST` / `SPEND` / `REFUSE` / `RECOVER` / `RESET` / `DEBIT-SUPPRESSED`, one rate line per
  60 frames, capped at 4000 lines per boot. It does not depend on the `logging` feature.
- **Two reserved parts are not built and not approved**, behind the new Cargo feature
  `hero-mana-reserved` (off by default): the fighter HUD gauge and recovery on being hit.
  For the HUD the useful new result is that **the vanilla layout already contains the MP
  gauge** - `blyt/info_melee_lct_player_sp.bflyt`, panes `sp_00..sp_03`,
  `MELEE_GAUGE_SP_GET/USE` - so an approved build would author no assets, and all three
  candidate hook sites are byte-verified on the 13.0.4 image by the new
  `tools/audit_hero_mana_native.py` (all MATCH, `refs/brave_special_n/T-0057/reserved_sites.json`).
- **Zero asset delta, no new status id.** The meter reuses the existing Hero status
  blocks, so this merges into a collective build with nothing but Rust.
- Compile-checked in `builds/.cache/pgwr-fb-3-mythra-mana-target` with
  `snake-neutral-b,hero-side-b` (NRO 471,040 B, sha256 `1189bd1c...`), and also with
  `snake-neutral-b` alone and with `hero-mana-reserved` added. No packaging, no install, no
  card access, no emulator, no console run. **All behaviour is unverified.**

## 2026-10-02 (T-0052 retry) - Kazap arrival re-wired to the donor's own link event (source + build, 0.20.18)

- **Cause settled from hardware (tier A).** The user's 0.20.17 run produced
  `evidence/2026-10-02_pgwr_T-0052/pgwr_hero_s_log_card2_2026-10-02.txt`
  (sha256 `ff7afc8c...`, 3066 lines, `BOOT v0.20.17`, 15 Kazaps / 30 bolts). Every one of
  the 32 `BOLT` samples reads `move_dist=0.0` against `threshold=300.0` with
  `owner_ok=true`: the engine never accumulates `FLOAT_MOVE_DIST` for this cloned article
  on Mythra, so the arrival predicate could never fire at any threshold. The null-owner
  cause is excluded.
- **The same log refutes "the bolt travels".** The bolt's position is byte-identical for its
  whole life (both bolts of a Kazap share one point, `y = 85.0 =
  param_special_s.offset_y_lightning`), while MapCorrection ran 900 times. Graveyard
  R-HERO-S-7; the cause of the stationary bolt is still undiagnosed.
- **Behavioural change (exactly one, rule 11):** `receiver.rs` raises the owned
  `LIGHTNING_ARRIVED` flag when the donor's own lightning event `0x214e64eedd` arrives -
  30 of 30 bolts in the log - gated on our own third attack and our own per-move bolt
  count, with all three suppression paths logged. That event is what
  `state.rs` always said it was replacing; the `FLOAT_MOVE_DIST` substitute was dead.
  No donor work id, no invented distance, no new interception: the slot was already patched.
- **Diagnostics:** `bolt_work()` prints the bolt's own `FLOAT_HEAD`/`FLOAT_TAIL`/`FLOAT_DIR`
  beside `MOVE_DIST` at Main and in the bounded `BOLT` sample, so the next log separates
  "the extension machinery never writes them" from "only MOVE_DIST is missing".
  `tools/audit_hero_side_b_log.py` **1.1.0** reports travel, grades the arrival event, and
  `--smoke` now pins both archived card logs plus three negative controls.
- `src/pgwr/plugin/Cargo.toml`: version `0.20.17` -> `0.20.18` (rule 6). Build:
  `cargo skyline build --release --features snake-neutral-b,hero-side-b`, clean in 17.69s,
  NRO `62c36331435fbefa247a18699aa90c151f0a09aa5e7804c806697afceb09ee7e` (466,944 B) in
  `builds/.cache/pgwr-heroside-target`. **New binary: not an asset-only delta. Not
  packaged, not installed** (rule 23).
- **Unverified: all behaviour.** The Zapple orientation fix shipped in 0.20.17 is still
  tier D - no log line can see effect orientation. No console run, no emulator, tests
  benched. Reports: `RESULT.md` (first run) and `RESULT-0.20.18.md` in
  `evidence/2026-10-02_pgwr_T-0052/`; finding
  `kb/findings/the-donor-link-event-was-the-arrival-signal-all-along.md`.

## 2026-10-02 (T-0056) - collective install of 0.20.17; prior card state marked tested

- **Installed `0.20.17`** to the SD card (E:) as the collective release of three queued
  changes: **T-0052** (Hero side-B: `brave_lightning2_swordspark` on `sword1` now `rot_z = -90`,
  plus the `BOLT` / `ACTIVATE lightning` / `APPEND lightning arrived` diagnostics),
  **T-0053** (Monkey Flip: donor `KICK -> FLIP_FALL` general lockout for HI/S/LW, object-owned
  lock records, one bounded `SWAPGUARD` line) and **T-0048** (R.O.B. down tilt, stretched-arm
  recipe 3.0.0, the two `c02attacklw3.nuanmb` clips `06fb085e...`).
- `src/pgwr/plugin/Cargo.toml`: version `0.20.16` -> `0.20.17` (rule 6). `info.toml` in the
  package follows, so the card's `info.toml` reads 0.20.17.
- New release NRO `22bfbd01421280f61c15bdde54b9674df87e9beeccd28108f3a1bdeef960f901` (466,944 B),
  built in the isolated cache `builds/.cache/pgwr-T0056-target` with features
  `snake-neutral-b,hero-side-b`. **Not an asset-only release**: installed without `--reused-nro`.
- Mod tree `730dd088d7999fd633736caab998a0f884d86631dcd36a7f6a3ce20327858394`, 1983 files,
  delta against the previous card state exactly three files (the two down-tilt clips and
  `info.toml`), 0 added / 0 removed. Backup
  `evidence/sd-backups/sd-backup-20261002-022035`; framework installation OFF; the four
  protected plugins are byte-unchanged.
- `tools/package_pgwr_release.py` -> **1.3.0**: new `--skip-donor-checks`, for the case where
  `dumps/arc` exists but is empty. It skips only the two motion-entry comparisons that read the
  donor export, prints a warning, records `donor_checks` in `MANIFEST.json`, and `--check`
  refuses a manifest that claims complete donor checks when the flag was used.
- Offline checks: release compile clean; built == staged == card NRO; `package_pgwr_release.py
  --check` PASS; the new marker strings (`BOLT life=`, `ACTIVATE lightning`,
  `APPEND lightning arrived`, `SWAPGUARD`, `GENERAL HI/S/LW`, `PGWR-MFLIP`) present in the NRO;
  forward-smash regression control identical to the previously installed tree; Hero side-B
  package audit identical to it (same 8 known inert start/hold entries); independent post-install
  re-hash 1983/1983 with 0 manifest mismatches. **No behavioural evidence of any kind.**
- `logging` stays off in this release, so T-0053's `[PGWR-MFLIP]` markers do not appear and
  Monkey Flip is judged by eye; `sd:/ultimate/pgwr_hero_s_log.txt` is written independently and
  will carry the Kazap `BOLT` lines. Records:
  `evidence/2026-10-02_pgwr_T-0056/INSTALL.md`, `evidence/install-record-2026-10-02_022035.json`.
- Documentation: every `CURRENT_INSTALL.md` section whose change was on the card before this run
  is now marked **TESTED 2026-10-02**, with the provenance recorded and no verdict invented
  where the user reported none (the Little Mac angled forward smashes are marked *exercised*,
  not *routed*). Installer procedure step 6 now says how to record such a declaration.
- Card log archived as evidence: `evidence/2026-10-02_pgwr_T-0056/pgwr_snake_log_card_2026-10-02.txt`
  (sha256 `d146f7ae5224d676c09e2a82f4fdab4619508802292ec00549e296309f75e60e`, 5198 lines, Snake
  `BOOT v0.20.16` sessions, 0 `FAIL`/`REFUSED`), and no crash report on the card is newer than
  2026-09-30 04:09.

## 2026-10-02 (T-0052) - Hero side-B: Zapple bolt orientation, Kazap discriminators

- `src/pgwr/plugin/src/mythra/hero_side_b/script_acmd.rs` `effect_2`:
  `brave_lightning2_swordspark` on joint `sword1` uses `rot_z = -90` instead of `0`.
  **The only behavioural change in this task.** It was the sole `sword1`-attached lightning
  emitter in the file not already using `-90`; level 1 uses the same joint and emitter
  family at `-90` and is the user's hardware-confirmed control. Hero's `Sword1` bind basis
  `[[0,0,1],[0,-1,0],[1,0,0]]` differs from Mythra's `[[0,1,0],[-1,0,0],[0,0,1]]`
  (`refs/brave_special_s/skeleton_bones.md` s4), and every `sword1` effect inherits the
  recipient's bone space. Tier D until hardware. The joint string `sword1` is unchanged:
  Mythra's own confirmed-working Cloud fair/jab trails use it.
- `weapon.rs` `lightning_exec`: new bounded `BOLT life=/move_dist=/threshold=/owner_ok=/x=/y=`
  line sampled at `life % 5 == 0 || life <= 2` (~7 lines/bolt), logged **before** the arrival
  branch, plus a line for the arrived-but-no-owned-state case. No behaviour change.
- `attack3_acmd.rs`: new `ACTIVATE lightning frame=10` (and its no-state variant).
- `fighter.rs` `loop_attack3`: new `APPEND lightning arrived; ...` and an
  `APPEND skipped: ... no owned state` line. No behaviour change.
- **Why the diagnostics were required:** the old `LIGHTNING arrived` line sat *inside* the
  `if let Some(s) = state::get(owner(...))` arm, so "the distance signal never arrives" and
  "the owner lookup returned null" both produced empty output. The 2026-10-01/02 card log
  has 13 Kazaps, 26 bolts and zero such lines - equally consistent with both.
- **Card log recovered and archived** (it was already on the card, not missing):
  `evidence/2026-10-02_pgwr_T-0052/pgwr_hero_s_log_card_2026-10-02.txt`, sha256
  `5311f05919164096f31a040f6f33edca4dd41d0f17d42fd50aa047b250dbdb99`, 2712 lines.
  It excludes activation, article creation, the bolt's Lua states and its travel.
- **Kazap's arrival predicate is deliberately unchanged.** `LIGHTNING_CHECK_LENGTH * 10` =
  300.0 equals the bolt's entire designed travel over its `life=30` frames at 10 units per
  frame, and whether the engine accumulates `FLOAT_MOVE_DIST` for a *cloned* article on
  Mythra is unmeasured. Lowering the threshold would be a guess at the one number the new
  `BOLT` line measures directly.
- `tools/audit_hero_side_b_log.py` -> **1.0.0** (new). Grades a Hero side-B log into
  reached / never-reached chain steps and names cause (a) vs (b) from the `BOLT` samples.
  `--smoke` asserts the archived card log plus three synthetic negative controls (success /
  distance-stalled / owner-null); the first version failed those and the controls are now
  part of the smoke test.
- Built NRO `5051e5815ac85c0aa2c5bfe4c18151c9b667ddfdee76fdf5e9619624cd038096` (466944 B),
  features `snake-neutral-b,hero-side-b`, no errors, cache `builds/.cache/pgwr-heroside-target`.
  **A new binary: the delta is not asset-only.**
- **Build caveat recorded:** `CARGO_TARGET_DIR=../../builds/.cache/...` as written in the
  documented command resolves to `src/builds/` from `src/pgwr/plugin`; it needs three `../`.
- **Not packaged, not installed, no tests, no emulator, no card write.** Every behavioural
  claim is tier D; the build compiling proves nothing about what is drawn or which status
  runs. Staging + 8 manual checks: the T-0052 section in `CURRENT_INSTALL.md`.

## 2026-10-02 (T-0048) - R.O.B. down tilt, stretched-arm animation variant

- `src/pgwr/tools/build_robot_dtilt.py` -> **3.0.0**. New `deform_arm()` deforms each arm as
  a rigid block rooted at `Shoulder{L,R}` (rotate onto the recipe `arm_aim`, then slide along
  it to a target anchored to the fighter's origin). `solve_limb` is now feet only: recipe 2.0.0
  fed it wrist goals ~5.2x the arm's length and it clamped them without an error, so frame 3
  peaked short of the donor capsule.
- Transform serialization is scale-aware and orthonormal-safe: `decompose()` separates rotation
  from scale by Gram-Schmidt over the matrix's own columns, `quaternion()` orthonormalizes
  first, and the emitted transform carries the measured scale instead of a hardcoded
  `[1,1,1]`. This recipe scales nothing; the report now measures that (2.7e-15).
- `active_hitbox()` parses the frame-3 capsule out of `robot_attack_lw3.rs` at run time and
  records that file's hash, so the preview overlay and the reported hand-to-capsule gap cannot
  drift from the donor hitbox.
- Preview is now seven panels (frames 0,1,2,3,4,6,15) on one shared z/y bound and scale, drawing
  every bone plus the capsule overlay in the same mapping, so extended arms are never clipped.
- Reservation and report identity are no longer hardcoded to T-0036: `--task-id` (or
  `PGWR_BUILD_TASK`) drives the shared-build lock owner, the report/manifest identity and the
  reserved cargo cache name, and a live reservation held by another task aborts the run.
- `src/pgwr/assets/robot_dtilt/recipe.json` -> **3.0.0**: `arm_reach`/`arm_aim` replace the
  wrist offsets; peak reach 1.20 body heights, `H` = 12.8334 with its measurement provenance.
- Staged `builds/pgwr/0.20.16+robot-dtilt.5` from the installed `0.20.16+robot-dtilt.4`: mod
  tree `a976ff51...` (1983 files, 0 added / 0 removed, only both `c02attacklw3.nuanmb`
  changed), both NROs byte-unchanged, manifest `ef124696...`. Gameplay, motion entries,
  costume gate, sounds/effects/rumble, duration 28 and cancel 15 unchanged.
- **Not installed, no tests, no emulator, no card access.** Appearance and palm/hitbox
  alignment are tier D and need the user's console check.

## Research only - 2026-10-02 (T-0049)

- Replaced outdated mana/HUD draft in place; recovered matching 13.0.4 main and measured SP arithmetic, recovery and actual HUD callback candidates. Shared meter persists across forms; spell entry never refills; world effects do not satisfy the requested HUD. No runtime/content change. Implementation remains blocked on original ARC inputs and full lifecycle/frame/damage/pane ABI plus reserved-hook hand-back.

## 2026-10-02 collective build-only verification

- Reused `0.20.16+robot-dtilt.4` for full T-0036/T-0042 coverage; manifest, 1983-file tree and both NRO hashes checked. No artifact change, fresh compilation, connected-device access or game testing. Record/checklist: `evidence/2026-10-02_pgwr_console-89c7baa998178f244493-build/VERIFY.json`.


## Unreleased - 2026-10-02 (T-0042 install, no mod content change)

- Installed `builds/pgwr/0.20.16+robot-dtilt.4` to the SD card (E:) as the collective
  installer. No mod content, NRO, version or asset changed: the package is 0.20.16 with
  the two T-0036 down-tilt clips, and the plugin NRO is the one already on the card.
- Record `evidence/2026-10-02_pgwr_T-0042/INSTALL.md`,
  `evidence/install-record-2026-10-02_002850.json`; backup
  `evidence/sd-backups/sd-backup-20261002-002850`.
- `src/pgwr/install-to-card.sh`: fixed card autodetect (the `ls -d /[a-z]` volume scan
  returns nothing in Git Bash on Windows, so no card was ever found on this machine) and
  added `--reused-nro` for asset-only variants whose cargo cache has been pruned. New
  tools `tools/verify_installed_card.py` and `tools/check_forward_smash_package.py`.
- Corrected `CURRENT_INSTALL.md` and `STATUS.md`: Little Mac 0.20.16 was already
  installed on 2026-10-01; its angled forward smashes are on the card, untested.

## 0.20.16+robot-dtilt.4 - 2026-10-01 (T-0036 stage-only animation variant)

- Core banner/info version and unchanged NRO remain 0.20.16; custom animation recipe
  `src/pgwr/assets/robot_dtilt/recipe.json` is version 2.0.0. No Rust compilation or card install.
- Replaces both filtered R.O.B. clips with recipient bind/idle-based motion: explicit
  165-bone tracks, planted feet and bent knees, torso/neck articulation, low right palm
  strike with left-arm guard, recovery to idle at cancel 15; donor duration ends at 28.
- Preserves all other 1981 mod files, including complete motion lists, effects/sounds,
  routing, vanilla costume assets and unrelated moves. ACMD and skeleton sources untouched;
  `build.py` changes only its down-tilt description. Generator retains its existing API.
- First authoring draft exceeded recipient arm reach; wrist goals were revised using
  measured recipient lengths. Final recipe has zero unreachable distance in its IK report.
  This is offline authoring evidence, not console validation. No automated tests/Ryujinx.
- Package hashes/manual checks: own section of `CURRENT_INSTALL.md`; generation report
  and joint preview: `evidence/2026-10-01_pgwr_T-0036/`. Visual quality remains needs_review.

## 0.20.16 - 2026-10-01 (staged, not installed)

- **Little Mac's up/down-angled forward smash on Pyra/G&W c06/c07** (`AttackS4Hi` /
  `AttackS4Lw`), completing the family that 0.20.14 started. His own
  `attack_s4_hi` / `attack_s4_lw` motion entries taken whole (cancel 44, flags 0x84), his own
  `c03attacks4hi` / `c03attacks4lw` clips retargeted onto the built grafted skeleton, and all
  eight handler functions transcribed from `AttackS4Hi.txt` / `AttackS4Lw.txt` - including
  the down-angled one's weaker 24%/21-base-knockback values, its `set_attack_height_all(LOW)`,
  and the `SO_VAR_FLOAT_LR` branch that mirrors the slash arc to his facing.
- **Reverses an earlier wrong "blocked" verdict.** 0.20.14 shipped the angled variants as
  impossible, reasoning that because no name or hash for them exists in `main.bin` the engine
  could not route to them. The measurement was right and the inference was wrong: **65 of the
  72** fighters with a c00 motion list on disk do carry both angled kinds with their own clips,
  and the 7 that do not (`chrom diddy eflame elight gamewatch miiswordsman younglink`) are
  characters whose angled forward smash was never authored. No separate status is required
  either - the motion-list entry carries its own `game_script`, and the plugin now registers
  all four handler sets to match, because a motion with no script is a move that animates and
  hits nothing. **No native hook is involved; rule 17 is not engaged.**
- `c03attacks4hi` / `c03attacks4lw` are new file names per slot and are declared in
  `config.json`; the audit checks the pristine export to confirm the base game really lacks
  both, so "new file" is measured rather than assumed.
- **Cargo cache is isolated and recorded in the package.** Built and packaged in
  `builds/.cache/pgwr-lm-target/`, `"cargo_target": "pgwr-lm-target"` in `MANIFEST.json`.
  `install-to-card.sh` resolves `PGWR_CARGO_TARGET` -> the manifest's `cargo_target` -> the
  feature-derived default, and echoes the cache it chose. `package_pgwr_release.py` gains
  `--cargo-target`, and `--check` now asserts the manifest's recorded cache is the one the NRO
  was actually read from. Both exist because a 0.20.14 packaging run shipped another agent's
  stale NRO while still printing `PASS`; only grepping the packaged binary for this move's own
  sound names caught it. That grep is now `check_handlers` in the audit.
- `tools/audit_littlemac_fsmash.py` v1.1.0: covers all four kinds, all four clips, all four
  sound names, asserts the two angled kinds are genuinely absent from the base game, and adds
  the packaged-NRO handler check. Report is now version-keyed
  (`refs/littlemac_attack_s4/audit_0_20_16.json`).
- Built on the installed 0.20.15 baseline; delta **4 added** (two angled clips per slot),
  **4 intended overrides**, 0 unexpected, 0 removed. 1983 mod files. NRO
  `81460e74313350aaf569ce832045e8586387ab4ddf10e51bfdb690a8d29ef834`.
- **Hardware result for the neutral punch is TIER A** (reported by the user on 0.20.14: works
  great, animation too, and G&W's prop no longer appears). **The angled variants are tier D
  until the 0.20.16 console run** - see `CURRENT_INSTALL.md` test steps 9-12.

## 0.20.15 - 2026-10-01 (installed 2026-10-01)

- **Hero's side-B (Zap / Zapple / Kazap) on Mythra c06/c07**, mana excluded, behind Cargo feature
  `hero-side-b` (asset env `PGWR_HERO_SIDE_B=1`). Owned statuses `0x1FA..0x1FE`, cloned spark/lightning
  weapons with owned Lua states, native-checked hitboxes, Hero effects/trails merged into Mythra's c06/c07 banks.
  Built on the installed 0.20.14 baseline; delta +46 / 6 changed / 0 removed files. See `CURRENT_INSTALL.md`.
- Tooling: `tools/merge_hero_side_b_effects.py` (new); `package_pgwr_release.py` gains `--hero-side-b` and the
  missing `--cargo-target` argument, and checks the chained side-B effect merge.

## 0.20.14 - 2026-09-30, installed 2026-10-01

- **Little Mac's forward smash on Pyra/G&W c06/c07** (`AttackS4` + `AttackS4Charge`),
  replacing G&W's prop-spawning forward smash. Hitboxes, timing, effects, sounds, rumble,
  slope and the charge physics are his own, translated from
  `dumps/scripts/.../lua2cpp_littlemac/littlemac/AttackS4.txt` and `AttackS4Charge.txt`.
- Animation and cancel frame are his too: `c03attacks4s.nuanmb` and
  `c03attacks4charge.nuanmb` retargeted onto the built grafted skeleton, and his own
  `attack_s4_s` / `attack_s4_hold` motion entries taken whole (cancel frame **44** against
  G&W's 43; flags 0x84 against 0x80). Tool `src/pgwr/tools/build_littlemac_fsmash.py`;
  ACMD `plugin/src/acmd/littlemac_attack_s4.rs`, registered at `Priority::High` over the
  generated G&W handlers. Both clip names already exist on the recipient, so this adds
  **no** new motion file and needs no `config.json` motion declaration.
- `dumps/arc/fighter/littlemac` exists on disk but holds **0 of its 4290 indexed files**, so
  the whole donor closure (18 files) was pulled live over arc-network into
  `refs/littlemac_attack_s4/` (`tools/fetch_arc_files.py --set littlemac_attack_s4`,
  0 failures, re-verifiable with `--check`). Provenance `refs/littlemac_attack_s4/SOURCE.json`.
- Measured on the built 165-bone recipient: **46 of his 50 bones survive, 0 parent
  mismatches**, and the whole `Bust -> ClavicleC -> ClavicleR -> ShoulderR -> ArmR ->
  HandR -> HaveR` chain keeps identical parents. Every hitbox is parented to `armr`, which
  survives, so the boxes land where they land on him. The 4 dropped bones are helper bones
  (`H_ClavicleR/L`, `H_SholderR/L`).
- Sounds are his own, not stand-ins (rule 17): `se_littlemac_smash_s02` and
  `vc_littlemac_attack05` merged into Pyra's c06/c07 banks via `tools/merge_donor_sound.py`,
  which gained a `DONOR_ROOTS` table because his banks are in `refs/`, not the export. Tone
  lookup is `crc32(lowercased name)`; both measured present before the port was written.
  `effect/fighter/littlemac/ef_littlemac.eff` is shipped byte-exact and declared in
  `config.json` for `littlemac_attack_line`; both required emitters verified present.
- **The up/down-angled forward smash is deliberately NOT shipped.** Pyra, Mythra and G&W
  have no `attack_s4_hi` / `attack_s4_lw` motion kinds and no such status, and the 39,156-entry
  const table in `lua2cpp_common.nro` has zero `S4_HI`/`S4_LW`/`attacks4hi`/`attacks4lw`
  entries; eflame's own status table registers exactly one smash status. Only 7 of 72
  fighters lack the angled pair, and all three of ours are among them. Adding the clips
  would ship files the engine can never call, so delivering it needs an authorized native
  hook on the input-to-status decision (rule 17). Evidence and the ready-to-use extracted
  clips: `refs/littlemac_attack_s4/SOURCE.json` -> `blocked_variants`.
  > **SUPERSEDED by 0.20.16 - this reasoning was wrong, not just cautious.** The measurements
  > above are all still true, but the conclusion does not follow. 65 of the 72 fighters *do*
  > carry the angled pair, and the motion-list entry carries its own `game_script`, so no
  > separate status and no native hook are needed. The entry is kept as written because a
  > changelog records what was believed at the time; see the 0.20.16 entry for the reversal
  > and `refs/littlemac_attack_s4/SOURCE.json` -> `angled_variants` for the full argument.
- Baseline is the **installed 0.20.13** (built with `PGWR_UI_BASELINE=builds/pgwr/0.20.13/...`),
  so Snake neutral-B, Monkey Flip, R.O.B. dtilt, the Cloud trails, the Chrom jab and the
  c06 Ursula / c07 Wilhelmine naming are all retained. Delta vs 0.20.13: **1 file added**
  (`effect/fighter/littlemac/ef_littlemac.eff`), **20 intended overrides** (the 4 clips,
  2 motion lists, 12 sound banks, `config.json`, `info.toml`), 0 unexpected, 0 removed.
- NRO `e8bf3f0713489bad278e937c8a22baa8498ce393761dee94940d35734303165c` (335,872 bytes),
  mod tree `cf778b3c5cef9d7db3738cf5f79023cd095dcee98a6626c0528a7e81e9b10604` (1933 files).
  Package `builds/pgwr/0.20.14/`, manifest `MANIFEST.json`, audit
  `refs/littlemac_attack_s4/audit_0_20_14.json`, tool `tools/audit_littlemac_fsmash.py`.
- Offline checks only: release compile, built==packaged NRO, donor-entry byte comparison,
  clip retarget, sound resolution, effect emitters, package validation and baseline delta.
  **Nothing here says the punch plays, looks right or is audible** - that needs the console.
- **Installed 2026-10-01** on the user's explicit instruction ("then install what you have right
  now"), framework installation OFF. Record `evidence/install-record-2026-10-01_002928.json`;
  automatic backup `evidence/sd-backups/sd-backup-20261001-002928` holds 0.20.13. Built ==
  packaged == card NRO, and all 1933 mod files independently re-hashed byte-identical on the
  card; `libsmashline_plugin.nro` still `5f4091ee...` and the other protected plugins unchanged.
  **Hardware test pending.**
- Trap worth recording: the first packaging attempt silently picked up a **stale NRO** from a
  shared cargo cache, because the packager picks its cache directory from `MANIFEST.json`.
  It was caught only by grepping the packaged binary for this move's own sound names. A
  `PASS` from the packager is therefore not sufficient evidence that the binary is the one
  just built.

## 0.20.13 - 2026-09-30

- Collective install of two READY `CURRENT_INSTALL.md` sections on the installed 0.20.11
  baseline: **R.O.B. down tilt (`AttackLw3`)** on Pyra c06/c07, and **Character Naming**
  (c06 "Ursula", c07 "Wilhelmine"). Snake neutral-B retained; feature `snake-neutral-b` only,
  `logging` still off.
- Mod tree is 0.20.12 plus exactly `ui/param/database/ui_chara_db.prc`,
  `ui/message/msg_name.xmsbt` and the `info.toml` version — nothing added or removed
  (1932 files, tree `2fcfaa992a62dca741e5bd3dfc5cfcad53b1d24f173bd0939a5aadf051b0f31d`).
  0.20.12 pinned the old name files with `PGWR_UI_BASELINE`; combining the two READY
  sections is the deliberate installer decision recorded in `CURRENT_INSTALL.md`.
- NRO `57128f65b667d574ad6da54fff353e8e200b1b98afbbb4e6b3407b9ba33622ae` (331,776 bytes),
  compiled from an isolated copy of the plugin crate so the Little Mac forward-smash port
  (another agent's unregistered in-flight work) and Hero side-B are excluded. Little Mac's
  f-smash is not built: `builds/pgwr/0.20.14/` has no plugin NRO and no MANIFEST.
- Installed with framework installation OFF. Built/package/card NRO and all 1932 mod files
  independently hash-verified equal; the four protected plugins byte-unchanged.
  Record `evidence/install-record-2026-09-30_235634.json`; backup
  `evidence/sd-backups/sd-backup-20260930-235634` holds 0.20.11. **Hardware test pending** —
  offline checks prove packaging, not behaviour.
- Collective combination, so a hardware failure is not attributable to one change on its own
  (AGENTS rules 11 and 23). The two are file-disjoint; a controlled follow-up is cheap.

## Unreleased — 2026-09-30

- Character Naming (c06 Ursula, c07 Wilhelmine): created custom character name tool
  `src/pgwr/tools/build_custom_names.py` with full offline validation (`--check`).
  Configures Pyra/Mythra costume c06 to display "Ursula" (CSS uppercase banner "URSULA")
  and c07 to display "Wilhelmine" (CSS uppercase banner "WILHELMINE") for both Pyra (G&W)
  and Mythra. Modifies `ui_chara_db.prc` to route `n06_index -> 6` and `n07_index -> 7`
  across all 5 character entries (`eflame_first`, `eflame_only`, `elight_first`,
  `elight_only`, `element`), leaving layout indices (`cXX_index = 0`), vanilla slots
  c00–c05, and standalone Mr. Game & Watch (`ui_chara_gamewatch`) untouched.
  Generates 40 XML entries across message categories 0..3 in `src/pgwr/ui/message/msg_name.xmsbt`.
  Integrated into `src/pgwr/build.py`. Concrete files staged in `builds/pgwr/staged_names/`
  and queued in `CURRENT_INSTALL.md`; not installed on card per collective workflow.

- Hero side-B source continuation (2026-10-01): added owned article-slot allocation source, relocated lightning effect and log
  allocation helpers, and removed an initializer's fixed Hero article-slot query.
  A new native event audit identifies an additional recipient receiver dependency;
  rule 17 hand-back is required for Mythra class +0x170 before a complete package.
- Hero side-B source continuation: extracted/hash-checked all 16 spark/lightning
  motion lists with explicit dump permission, preserving the original 184-file pin.
  Added owned entry/hold loops, EXEC, native-checked successful S1/S2/S32 game ACMD
  and S3 activation dispatch. Generated complete relocated native spans, parameter
  field views and signatures; added three approved hook wrappers, scoped owned
  callbacks and independent crash-tail logger. All remain disconnected/uncompiled.
  Input/generator checks pass; no build, package or installation. Remaining status,
  weapon, sword and resource translation is recorded in STATUS/CURRENT_INSTALL.
  Native S3's zero direct ATTACK count is measured, retracting the prior artifact
  assumption; canonical tier-B evidence is SOURCE_STATUS section 6.

## 0.20.12 - 2026-09-30

- R.O.B. down tilt (`AttackLw3`) on Pyra/G&W c06/c07, replacing G&W's manhole-cover dtilt.
  ACMD `acmd::robot_attack_lw3` (game/effect/sound/expression, Priority::High over the generated
  G&W one); R.O.B.'s own `attack_lw3` motion-list entry whole (cancel 15, flags 0x80) and his
  `c02attacklw3` clip retargeted by node name (11 of 82 nodes exist on the recipient); three
  `se_robot_*` tones, `vc_robot_attack01-04` and the `seq_robot_rnd_attack` record appended to
  Pyra's c06/c07 banks and `eflame.sqb`. Donor files live-extracted into `refs/robot_attack_lw3/`.
- New tools: `src/pgwr/tools/build_robot_dtilt.py`, `tools/merge_robot_dtilt_sound.py`,
  `tools/audit_robot_dtilt_delta.py`; `fetch_arc_files.py --set robot_attack_lw3`.
  `build.py` gains `PGWR_UI_BASELINE` (keep an earlier package's two name files);
  `package_pgwr_release.py` accepts a later merge chained after Snake's.
- Baseline is installed 0.20.11 including Snake (feature `snake-neutral-b`); delta audit: 18 changed
  files, none added or removed, only `attack_lw3` changed in both motion lists, banks/sqb append-only.
  NRO sha256 `e8bf3f0713489bad278e937c8a22baa8498ce393761dee94940d35734303165c`; 1932 files,
  tree `3854a891f94b0591240526a0d47aede0ab7ed4f940e5b1dd64eba090e4f3f1ee`. Not installed.
  Offline only; the pose on G&W's body and all sounds are unverified on hardware.

## 0.20.11 - 2026-09-30

- Prepare costume-gated Snake neutral-B for Pyra/G&W c06/c07: owned hold/throw
  statuses, lower-body dispatch and native-audited donor ACMD, 29 body motions,
  cloned pin, nine exact donor sounds and genuine grenade item handling.
- Retain the authorized signature-checked life bridge and range-checked C-ABI guard.
  Snake writes its own crash-tail log; global observer logging remains disabled.
- Fix sound merging to preserve the assembled baseline banks: all 457 prior tones
  per bank remain byte-exact, with nine Snake tones appended. SQB records preserved.
- Release/generator/native/lower/ABI/package checks pass offline; baseline delta
  confirms 211 added files, ten intended overrides and no removed mod files.
- Package NRO sha256 `00a6c76555cfaa8bacb38322dad5096ae42c53a600d75c2efe0f9eec1fc33206`;
  1932 files, tree `e2c6ebf75e2cb1211a4dcaa37556541302afcb685e162acf2a5957140b023c7c`.
- Installed at user request; NRO/1932 mod files independently verified and protected
  framework hashes unchanged. Hardware behavior unverified. Record: `evidence/install-record-2026-09-30_222459.json`.
- Installer and card-verification tools select the isolated Snake cache from manifest features.
  New files: `builds/pgwr/0.20.11/CREATED_FILES.json`.

## 0.20.10 - 2026-09-30

- Silent performance build: removed all runtime SD card disk logging (`sd:/ultimate/pgwr_log.txt`) and per-frame observer callbacks for gameplay feel testing without I/O latency or frame drops.
- Feature-gated `article::log` and `monkey_flip::log` behind `cfg(feature = "logging")` with zero-cost inline no-op implementations when inactive.
- Disabled stock Diddy per-frame observer callback (`diddy_probe::install()`) when `logging` is inactive, eliminating per-frame telemetry overhead.
- Disabled `gate_trace` per-frame `on_line` callbacks in `acmd` and `mythra` modules when `logging` is inactive.
- Logging infrastructure fully backed up in `evidence/logging_backup_0.20.9/` (byte-exact source files and restore procedures). Can be re-enabled on any subsequent install with a single feature flag (`--with-logging` or `default = ["logging"]`).
- Retains Chrom jab and Cloud forward air custom Cloud sword trails (`tex_cloud_sword1/2`) on c06/c07, Monkey Flip aerial lockout and capture handling, and all G&W moves.
- Built and packaged 0.20.10: NRO sha256 `2ba2d1821cd822401affa5d20dfa7da5c44f5147483a7dfed8e593a68c58f0ee`; 1721 mod files, tree sha256 `ede8c200198ee7faa542f9abe20f5bb98ab6a4b7ccb0ac0b005bab5f10eb167f`.
- Installed and byte-verified on SD card: `evidence/install-record-2026-09-30_145657.json`. Backup holds 0.20.9 (`evidence/sd-backups/sd-backup-20260930-145657`); protected framework hashes unchanged.

## 0.20.9 - 2026-09-30

- Route custom Cloud sword trails (`tex_cloud_sword1`, `tex_cloud_sword2`) on Chrom's jab (`Attack11`,
  `Attack12`, `Attack13`) on Pyra/G&W c06/c07, replacing the placeholder Mythra trail (`tex_elight_sword1/2`).
- Trail ribbon uses Cloud's custom donor textures recolored to match each costume's scheme:
  c06 Black & Pink (dark crimson core, radiant magenta-pink edge) and c07 Radiant Gold (pure white core, champagne gold body/edge).
- Uses `JAB_TRAIL_TIP` (14.5 * 0.9 = 13.05) matching the jab's 0.9x Aegis blade scale.
- Completes registration for `effect_attack12/13`, `sound_attack12/13`, and `expression_attack12/13` pointing to Chrom jab handlers.
- Built and packaged 0.20.9: NRO sha256 `5ab7bdc591c2cfa577e4ea36080df2f57d3f558d08523ed2a000b48162945dc2`; 1709 mod files, tree sha256 `b7b42a95dd8a78a8af83c97f2aa9204c0f4be942db94b7a263d5506f095c0bab`.

## 0.20.8 - 2026-09-30

- Cloud Forward Air custom sword trails: replaced placeholder Mythra trail (`tex_elight_sword1/2`)
  with custom copies of Cloud's sword trail (`tex_cloud_sword1/2`) recolored to match Mythra's
  costume schemes. c06 uses Black & Pink Mythra scheme (dark crimson/black core, radiant magenta-pink edge);
  c07 uses White & Champagne Gold scheme (pure white core, radiant champagne gold body, warm gold edge).
- Added `src/pgwr/tools/build_cloud_trail.py` with standalone smoke tests; integrated trail generation into
  `build_color_themes.py`; updated `attack_air_f.rs` effect script to route Cloud's trail.
- Pinned Cloud trail donor files in `refs/cloud_attack_air_f/trail/` and updated `SOURCE.json`.
- Adopt the user's collective installation queue in root `CURRENT_INSTALL.md`.
  Development agents prepare their sections; a user-designated installer assembles
  and installs requested ready changes. Canonical rule: `AGENTS.md` 23.
- NRO sha256 `389d14259684c1c35ecf0dbe793ce5c2862510c8b214f31303fef5e2fcf0cb17`; 1709 mod files, tree sha256 `c548b3cdf681b7d1128a256d0ed6754367083d88dc4d0fa95f693736343e7922`. Installed and independently byte-verified on card: `evidence/install-record-2026-09-30_134152.json`. Automatic backup holds 0.20.7; protected framework hashes unchanged. Hardware test passed (`evidence/2026-09-30_pgwr_0.20.8/RESULT.md`).
- New files: `CURRENT_INSTALL.md`,
  `src/pgwr/tools/build_cloud_trail.py`,
  `src/pgwr/assets/custom_cloud_trails/trail_c06/tex_cloud_sword1.nutexb`,
  `src/pgwr/assets/custom_cloud_trails/trail_c06/tex_cloud_sword2.nutexb`,
  `src/pgwr/assets/custom_cloud_trails/trail_c07/tex_cloud_sword1.nutexb`,
  `src/pgwr/assets/custom_cloud_trails/trail_c07/tex_cloud_sword2.nutexb`.

## 0.20.7 - 2026-09-30

- Restore the donor's aerial side-B input lock when Monkey Flip JUMP ends in normal FALL. Store availability separately from per-move state so starting another phase cannot reset it.
- Compose side-B and Fire availability in the existing global-table callback; refresh the owned side-B lock on native ground/cliff, hit and reset events, including Mythra landing for the paired entry. No per-frame forced status, donor work IDs, or framework plugin replacement.
- Ship this side-only restriction as one hardware experiment. Donor kick/STICK_ATTACK2 general special lock (up-B/side-B/down-B) is recovered and remains the next separate change under AGENTS rule 11. Victim T-pose is unchanged and deferred at the user's direction.
- Add `tools/audit_diddy_special_lockout.py` 1.0.0 with actual dump instruction smoke assertions and pinned `refs/diddy_monkey_flip/special_lockout.json`; compilation passes. Assets reused from 0.20.6 except version label; hardware test pending.
- NRO sha256 `8dea58a20e8c06bfa71f8818818bf91649103a2b04d3de33522e70dff1b629f8`; 1701 mod files, tree `0a883520e042c06f7a1ccf675e1e183ff63d31d1942e5ab960733035344158d2`. Installed and independently byte-verified after the user remounted the card: `evidence/install-record-2026-09-30_130439.json`. Backup holds 0.20.6; protected framework hashes unchanged. Manifest and complete created-file inventory are linked from STATUS.
- Improve `tools/audit_pgwr_svc_guard.py` to 1.0.1: resolve the named zero-size asm symbol; check its exact instructions and compiled caller without assuming its bytes occur only once. ABI audit passes.

## 0.20.6 - 2026-09-30

- Correct the Monkey Flip range guard's syscall call boundary using the five-instruction C-ABI QueryMemory stub from pinned smashline commit `be3ef308ed8e479922da192a391e0684184af2af`. Whether register clobber caused 0.20.5's refusals remains a hypothesis.
- Forward rejected events to Pyra's original receiver; add bounded logs of query result, address, requested size, region and permissions. Owned capture setup, statuses and copied offset data are unchanged.
- Release compilation, compiled guard audit, copied-data comparison, log-summary smoke and package checks pass (offline). Assets equal 0.20.5 except the version label. Hardware 0.20.6: capture confirmed by the user and ten logged cling entries; grabbed opponents T-pose. Both release paths were not separately confirmed. Evidence: `evidence/2026-09-30_pgwr_0.20.6/RESULT.md`.
- NRO sha256 `f56efc2a6d66a3d97bc946a38ddff2d2fec9af57c640ae3e58f05480ab2f2e07`; 1701 mod files, tree sha256 `8dde9d8f975f6c7d63df6d56a1240d7e0d6429cfe65d0f2bb1f16a7c2cfb60f3`. Installed and byte-verified: `evidence/install-record-2026-09-30_122044.json`; protected framework hashes unchanged. Complete created-file inventory is linked from STATUS.
- Add `tools/audit_pgwr_svc_guard.py` 1.0.0 and `tools/summarise_pgwr_capture_log.py` 1.0.0; package source hashes pin both.

## 0.20.5 - 2026-09-30

- Add an owned Monkey Flip native capture-event receiver on Pyra c06/c07 custom JUMP, authorized by the user. Full 13.0.4 Pyra/Diddy handler signatures guard the Pyra class +0x170 wrapper; other events retain Pyra's original receiver.
- Translate the donor capture branch: queued attacker STICK request, event acceptance/constraint writes, CatchModule setup and link attributes/flags/translated offset. Engine retains victim routing; no hand-built link or forced victim status.
- Copy 94 victim-kind offset triples from the shipped common thrown params with `tools/gen_mflip_capture_data.py` 1.0.0; generated `monkey_flip_capture_data.rs` owns offsets and full native signatures. `capture_owned_data.json` pins hashes and kind mapping.
- SVC QueryMemory validates ranges before raw reads; live identities/sender category are checked; game calls hold no locks, with a thread-local re-entry guard. File logs: `CAPTURE READY/EVENT/ACCEPT/SETUP/REFUSED`. Item-specific attachment branches remain unported and are refused.
- Recover the missing receiver in `tools/audit_mflip_capture_native.py` 1.1.0; exported wrapper and decoder instructions verify the setup and copied table. Retract the status-script-only assumption (graveyard R-MFLIP-2026-09-30).
- Native audit smoke checks, generated-data comparison, release compilation and package checks pass. All 1701 mod files match 0.20.4 except `info.toml` version. Hardware run failed to grab: 276 invalid event/fighter range refusals, no capture setup or cling. User verdict and full log: `evidence/2026-09-30_pgwr_0.20.5/RESULT.md`; attack/jump release could not be tested after a port capture.
- NRO sha256 `b4fe0235df36ff948bde88da2294abcbf2dfdccc4a181c105b46fb2f6d59b5eb`; mod tree `202a4a4f89a5c21018efb43007b151ba3b4674278a0c2ecc3ad3547eea005c7c`. Installed and byte-verified: `evidence/install-record-2026-09-30_114510.json`; automatic backup holds 0.20.4. All four protected framework plugin hashes are unchanged. Created-file inventory: `builds/pgwr/0.20.5/CREATED_FILES.json`. Older releases archived under `evidence/build-archives/` per rule 5; last three + 0.20.0 last-known-good retained.

## 0.20.4 - 2026-09-30

- **Fix: G&W's up-B only came back when hit, not on landing or ledge** (user, hardware, 0.20.x; log showed only `REFRESH ... +0x220`).
  0.19.0 had assumed class slot `+0x210` was the landing event (R-23, refuted). Scanning `main` for every writer of G&W's flag
  `0x200000E2` found slot `+0x168` (`0xa835c0`): on a situation change to anything but AIR, clear the flag unless in SPECIAL_HI.
  Pyra (`0xa0cdc0`) and Mythra (`0xa29ed0`) both override `+0x168` with a forwarder to their own landing code, so the slot is
  **wrapped**: the original runs first, then G&W's rule for c06/c07. Both forwarders' bytes and slot pointers are checked at boot.
- **Mythra c06/c07 touching ground or a ledge also gives G&W's up-B back**, at the user's request (the two share one player slot).
- G&W's lua2cpp also clears the flag in `GIMMICK_TORNADO` main (`0x8b70`); not ported (stage gimmick).
- `info.toml` version and the boot banner now come from `Cargo.toml`. 0.20.0-0.20.3 shipped `info.toml` "0.19.0" and a banner reading 0.19.0.
- Assets rebuilt from source: the four jab esword clips now carry `JAB_SIZE_FACTOR` 0.9. 0.20.2/0.20.3 reused 0.20.0's tree, and
  the card's `jabopen`/`jabtoopen` read `Sword1` scale **1.0**, so the 0.9 the user asked for in 0.20.2 is on the card for the first time.
  No other asset differs from 0.20.3.
- `tools/audit_event_slots.py` covers `+0x168` for G&W, Pyra and Mythra (`--smoke`); `refs/gamewatch_special_hi/event_slots.json` regenerated.
- Incident: this session's `build.py` briefly regenerated `builds/pgwr/0.20.3` (the version had moved under it); restored from the
  installer backup and verified (tree `5cc3ee90…`, NRO `d9ea48fa…`).
- NRO `743fbb3ee7bfd333f65219b3709080b83ab3805b677645e12bbd2e4b883811e8`, 1701 files, tree `d04ba00d5ac13e6edefd44868aef0b02517fe0b4b7c7eaa432fc42000b2455a3`.
  Installed and byte-verified (`evidence/install-record-2026-09-30_112330.json`); **no console run yet**.

## 0.20.3 - 2026-09-30

- **Monkey Flip gains a donor control: stock Diddy is now observed.** New `plugin/src/diddy_probe.rs` registers
  a `diddy` agent with exactly one `on_line(Main, ...)` callback and **no** status or acmd scripts, so nothing of his is
  replaced. In the locked smashline a line callback is additive (`install_line_callback_costume` -> `CALLBACKS`), so it runs
  in addition to his own status main. His scripts, clips, hitboxes, damage, motion and frame data are untouched, which is
  what keeps him a valid vanilla control rather than a second copy of our code. This is the crate's first `diddy`
  registration; every previous statement that no donor fighter is registered applied to `diddy` and `gamewatch` and is now
  true only of `gamewatch`.
  It logs his own `SPECIAL_S` Monkey Flip block - `SPECIAL_S_JUMP` (0x1E5) through `SPECIAL_S_DAMAGE_FALL` (0x1EF) in *his*
  table, never equated with our ids (AGENTS.md rule 19) - plus `CLUNG_DIDDY`, one line per status change (budget 24) and a
  bounded per-frame window (budget 90). Per-entry counters are static, never written into his WorkModule.
  Why it was needed: the 0.20.2 run is the only hardware data that exists for Monkey Flip, and playing Diddy produced
  **zero** `[PGWR-MFLIP]` lines because no `diddy` agent existed - the donor could not be observed at all.
- **`VICTIM` lines gained `near=` and `ndtop=`, the nearest active fighter, measured independently of any capture.**
  The 0.20.2 run logged 26 `VICTIM` frames that all read `victim=0xffffffff`, `link=0x50000000` (the engine's null),
  `is_catch=false`, `dist=-1.00`, `dtop=-1.00` - with no published capture there is no victim object, so the log could not
  answer the one question it exists for: was an opponent inside the box? `nearest_opponent` scans the battle object id
  range for the closest live fighter and reports his distance from the box's own anchor, directly comparable against the
  radius the `CATCH` boxes are given.
  Safety: every id is guarded by `sv_battle_object::is_active`, the accessor is re-checked for null and for identity with
  the attacker, and only `BATTLE_OBJECT_CATEGORY_FIGHTER` is accepted, so no article or projectile in the same id range is
  touched or cast. Read-only, so it cannot fault (AGENTS.md rule 25).
- Neither change writes state. Both are diagnostics; no donor behaviour was altered and no status was forced.
- NRO `d9ea48fa80b1708a7e8a7e01e26a2689f564b4f8bedbb17e0446ab424d490919`, mod tree unchanged at 1701 files /
  `5cc3ee90...`. Installed and byte-verified; **no console run yet**, so this is source/compilation evidence, not a claim of
  behaviour. Install record `evidence/install-record-2026-09-30_061334.json`.

## 0.20.2 - 2026-09-30

- **The Chrom jab's blade and sword trail are both slightly smaller** (1.0x -> 0.9x), on the user's report that 1.0 was still a
  shade too large. One number changed it: `JAB_SIZE_FACTOR` in `tools/build_esword_pose.py` and `chrom_jab.rs`, which the build
  asserts are equal. Because `JAB_TRAIL_TIP` is derived from that same factor, the ribbon resizes with the blade rather than needing
  a second edit - the reason 0.20.0 split the two into a per-move state in the first place.
- The Cloud fair is untouched: `SIZE_FACTOR` stays 1.4 and `attack_air_f::TRAIL_TIP` stays 14.5 * 1.4. Confirmed by reading the
  `Sword1` scale back out of the shipped clips **on the card**: fair 1.4, jab 0.9, both c06 and c07.
- 0.9 is a **taste value**, recorded as such. 1.0 was the measured candidate (Chrom's furthest jab box at z = 8.4 radius 3.5 gives
  ~11.9 reach against vanilla Aegis' 11.39); the console called it a shade too big, so the arithmetic is not the authority here.
  The offline geometry tools have disagreed with each other and with the console before (R-21), so if 0.9 is still off, it is the
  same single number to change and no code changes with it.
- **Fix: no Monkey Flip diagnostic ever reached the card log.** Every `[PGWR-MFLIP]` line in
  `status/monkey_flip.rs` and `acmd/monkey_flip.rs` was a bare `println!`, which only reaches the
  console's TCP stream. `article::log` is the only writer of `sd:/ultimate/pgwr_log.txt`, and it
  stamps `crate::LOG`; nothing else in the crate opens that file. Two hardware runs of Monkey Flip,
  on G&W and on Diddy, therefore left a log with **zero** `[PGWR-MFLIP]` lines even though the move
  fired - which is why the victim half of the capture has never been measured despite 0.15.1
  shipping per-frame telemetry for it.
  A new `status::monkey_flip::log` mirrors `article::log` with the move's own prefix, and all 12
  sites now call it. No diagnostic was removed and **no state-changing call was added**: this only
  changes where the existing lines go.
- The instrumentation it unblocks is unchanged from 0.15.1 and still standing: `VICTIM` (per frame,
  budget 90), `VICTIMSTATUS` (per victim-status change, budget 12), `CATCH HANDOFF`, `CLING`,
  `CATCHBOX`, `CATCHGEO`. The capture window is `STICK`/`STICK_ATTACK`/`STICK_ATTACK2`/
  `STICK_JUMP`/`STICK_JUMP2` every frame plus `JUMP` while `kick_frame` is 5-30.
- NRO `e614f3ded152f9dab9bf5b994bde47bb6276bf27e9a9c74e29f6fe3db87dca92`, 1701 mod files, **installed and byte-verified**
  (`evidence/install-record-2026-09-30_054617.json`; the 0.20.0 state it replaced is backed up at
  `evidence/sd-backups/sd-backup-20260930-054617`). Compiles clean, but **no console run of 0.20.2 yet**, so everything above is
  source/compilation evidence, not a claim of behaviour.
- Version 0.20.2 rather than 0.20.1: a concurrent session had already claimed 0.20.1 in
  `Cargo.toml`/`Cargo.lock` and was mid-build of it. One shared plugin binary carries both changes.

## 0.20.0 - 2026-09-30

- **The Chrom jab now draws its own blade size and its own trail length; the Cloud fair is unchanged.**
  The fair and the jab share one esword article, so a per-move size had to be a per-move *state*.
  `tools/build_esword_pose.py` adds `jab_open`/`jab_to_open` clips plus two entries appended to the article's `motion_list.bin`
  (15 -> 17), the new entries being byte-copies of `open`/`to_open` with only the kind and clip hash changed.
  They carry `JAB_SIZE_FACTOR` (1.0 here; lowered to 0.9 in 0.20.2) against the fair's `SIZE_FACTOR` = 1.4, which is untouched.
- 1.0 for the jab was measured, not chosen: Chrom's furthest jab hitbox is at z = 8.4 with radius 3.5, so the move's reach is ~11.9
  units, and vanilla Aegis reaches 11.39. At the fair's 1.4 the blade overhung those boxes by ~4 units. The fair's 1.4 remains a
  taste value for Cloud's much longer sword and is labelled as such where it is defined.
- `chrom_jab.rs` opens with `jab_to_open` instead of `to_open` and stops importing `attack_air_f::TRAIL_TIP`: its own
  `JAB_TRAIL_TIP` is Mythra's 14.5 scaled by the same factor the blade is, so the ribbon ends at the tip instead of stopping
  short of it - the mismatch reported after 0.15.2, which the shared constant could not express because the two blades differ.
  `build_esword_pose.py` fails the build if the Rust and Python `JAB_SIZE_FACTOR` disagree, so the two cannot drift.
- Closing still uses the shared `to_close`: it ends in the shared resting `close` state, which draws nothing and carries no scale.
- Support: `_parse_mlist` replaces the old ad-hoc reader, and `verify_mlist_roundtrip` re-serializes the dump's own parse and
  requires the bytes back, so appending entries to a dumped binary fails the build rather than shipping a list the game cannot read.
  The 15 vanilla entries are read back unchanged on the card; the two new ones resolve to `jabopen`/`jabtoopen`.
- Offline only: compiles clean and the assets build, 1701 mod files  installed and byte-verified
  (`libpyra_gamewatch_reskin.nro` `244447f8aa46e09ffe23b80bc9778119f8a42d5056df5aaa480664c8f5c466c4`,
  install record `evidence/install-record-2026-09-30_051537.json`; superseded on the card by 0.20.2, which only lowers
  `JAB_SIZE_FACTOR`). The two new clips are declared in `config.json`, without which
  ARCropolis would not load them - an undeclared new file is the silent no-load failure `build.py` exists to catch.
  No console run yet, so this is source/compilation evidence, not a claim of behaviour.

- **Fix: only the fully charged Hero fireball could be shot on Mythra c06/c07.** Not intended - a wrong `global_table` slot.
  `shoot_input()` and the guard-cancel check in `mythra/hero_neutral_b/fighter.rs` read the pad-trigger word from `global_table[0x10]`,
  which is not a button word, so `FIGHTER_PAD_FLAG_SPECIAL_TRIGGER | FIGHTER_PAD_FLAG_ATTACK_TRIGGER` never matched and `TO_SHOOT` was
  never set. Both now read `global_table[0x1f]`, the slot the hardware-verified Monkey Flip kick uses for the same mask
  (`status/monkey_flip.rs`); every other index in the plugin matches `handbook/06_statuses.md`.
- Effect: the mid-charge shoot in `hold_loop` was dead, so no small/medium fireball could be released; guard-cancel out of the charge was
  also dead. Only the full-charge branch still fired, via `CANCEL` and the engine's own `sub_check_charge_cancel_jump_mini_attack`, which
  reads real button state internally. Quick-tap shoot from `START` was dead for the same reason.
- **Hardware-validated (PASS).** `evidence/2026-09-30_pgwr_0.20.0/RESULT.md`, from `BOOT v0.20.0` at
  line 1362 of `sd:/ultimate/pgwr_log.txt`. 14 shots with `INIT begin` charges 6, 9, 11, 26, 29, 32,
  32, 33, 36, 38, 54, 81, 81, 81; `NATIVE map collision supplied level=` 0 x3 / 1 x8 / 2 x3 and
  `PROJECTILE fly level=` 1 x3 / 2 x8 / 3 x3, so small, medium and large all release. Zero `FAIL`
  lines. The 0.18.1 run in the same file is the control: 12 shots, all `charge=81`, all `level=2`/`3`,
  with the `charge=` histogram showing 11, 18, 27, 33, 39, 43, 45, 50, 61, 65 and 78 passed through
  without ever firing - medium charge (threshold 18) was reached and never released. No crash report
  on the card is newer than 0.18.0's two, so 0.18.1's initializer fix still holds. Card byte-verified
  against the staged build: NRO `244447f8...`, 1701 mod files, tree `5cc3ee90...`.
  Rollback archive `builds/pgwr/0.20.0/card-mod-folder.tar`; `builds/pgwr/last-known-good.json` now
  points here.

## 0.19.0 - 2026-09-30

- **G&W's own up-B (Fire) on Pyra c06/c07.** Ported from G&W's status code in `lua2cpp_gamewatch.nro`, recovered with `tools/nro_decomp`
  (`refs/gamewatch_special_hi/`): `SPECIAL_HI` pre/init/exec/main/end replaced on the gated agent, plus G&W's `SPECIAL_HI_FALL` and
  `SPECIAL_HI_CLOSE` as custom ids `0x1F9` / `0x1FA` (`plugin/src/status/special_hi.rs`). Stick tilt on frame 9, landing window from 11, parachute on 33,
  fast-fall/jump flick closes it, no double jump afterwards, landing lag from G&W's `param_special_hi.landing_frame` (40) via the params bridge.
- G&W's status flags, saved `attack_air_kind` and "up-B used" flag live in plugin per-entry storage, not his WorkModule indices (rule 19).
- Articles `rescue` (firemen + trampoline) and `parachute` cloned onto eflame (`TERM+2`, `TERM+3`), `use_original_code = false`; their
  visibility ACMD is generated into this crate. Model/motion files for all eight slots (rescue c04 has no `model.nuanmb`, as the donor), themed like
  the other G&W articles; c06 uses the pink skin's models. +335 files, all declared in config.json.
- Body ACMD for `special_hi`, `special_air_hi`, `special_hi_open`, `special_hi_close` (`acmd/generated/special.rs`); new `gen_acmd.py` rules
  R27 (flags -> plugin storage), R28 (keep the `0x2127e37c07` ledge-grab notify, verified as a hash40 immediate in G&W's NRO), R29 (empty stubs so
  Pyra's same-named effect scripts do not run), R30 (article scripts). Other generated groups are byte-unchanged.
- Up-B lockout and refresh: G&W's `global_table[0x26]` callback is installed from `SPECIAL_HI` main; G&W's two fighter-class event handlers are
  reproduced by pointing **Pyra's own** vtable slots `+0x210` / `+0x220` (`main+0x4faf9c8`) at plugin functions after checking the slots and the
  default handlers' bytes (`tools/audit_event_slots.py`). Only Pyra's class is touched; c00-c05 get the default behaviour. Which events call
  the slots is tier D - the `[PGWR-UPB] REFRESH` log line settles it.
- Known gaps: sound stand-ins per R2 (`wave10_lo` silent); the dump has no up-B effect scripts.
- Tools: `tools/main_image.py` (new), `tools/maindesc.py` (rewritten; the old one pointed at the pre-migration dump and could not run),
  `tools/audit_event_slots.py` (new, `--smoke`), `tools/package_pgwr_release.py` 1.1.0 (`--scope`).
  `src/pgwr/tools/extract_gw_params.py`: `param_special_hi[0]` route, hero param route and Cloud override are generator output (`--check` exact).
- Built on 0.18.1. NRO `e71c1e57d6cf4dd9aec05bb45aa6380e115022b9b1418075e19f89611e155708`, 1697 mod files, tree `0b2205ff9503cc9f…`. Installed and verified;
  hardware validation pending. Boot log: `[PGWR] BOOT v0.19.0`, `[PGWR-UPB] READY ...`, `[PGWR-UPB] REGISTERED ...`.

## 0.18.1 - 2026-09-30

- **Fix: full-charge Hero fireball on Mythra c06/c07 crashed the game** (0.18.0, two crash reports, `evidence/2026-09-30_pgwr_0.18.0/RESULT.md`).
  The fireball class constructor (`main+0x33c8ea0`) reads `map_collision_fireball{,_m,_l}` from Hero's decoded vl.prc object
  `*(*(main+0x52bb3b0)+0x1298)`, which was null because no Hero was in the match. An inline hook right after that load supplies
  a static object with the donor values (up/down/half_width 2/-2/2, 3.5/-3.5/4.5, 5/-5/5). It is active only inside the plugin's own
  initializer call, so a real Hero's fireball keeps Hero's object. It is the same method as the 0.14.0 breath bridge.
  The constructor bytes are part of the install-time signature check. Log: `[PGWR-HERO-N] NATIVE map collision supplied level=N hero_object=absent|present`.
- `tools/gen_hero_fireball_initializer.py` 1.1.0 emits those values from `dumps/arc/fighter/brave/param/vl.prc` and verifies decoder offsets,
  decoder fallback values and constructor loads.
- Cloud fair landing lag on Pyra c06/c07 restored to 11.0 (`landing_attack_air_frame_f`); 0.18.0 shipped 17.0 from a params.rs
  regeneration. The G&W up-B session fixed this in `src/pgwr/tools/extract_gw_params.py`, and it ships in this build.
- Mod tree identical to 0.18.0 except `info.toml` version. NRO `fa61a0fc2616951f99949d3826f1c695a18d4436d88d8122abd87ccfe9e0be05`.
  Installed and byte-verified; hardware validation pending.

## 0.18.0 ? 2026-09-30

- Hero neutral-B on Mythra c06/c07: five custom fighter phases, six owned projectile states, donor charge thresholds/kinetics/cancels, and successful shot behavior with mana omitted. No Hero fighter work IDs or fighter-code calls on Mythra.
- Thirteen owned motion registrations per costume, twelve distinct donor clips, and all eight costume groups of copied fireball model/motion assets. Donor motion-list timing retained; expression/sound/effect tail bindings validated.
- Sixteen original Hero effect resources merged into both Mythra banks; c07 texture IDs/names relocated to preserve both the gold bank and original fireball texture data. Original sound samples, tone records, random-group dependencies and voice sequences copied into recipient banks.
- User-authorized, byte-verified 13.0.4 plugin-local initializer hook and owned ember helper. Original Hero initialization passes through; framework NROs remain unchanged.
- Includes the previously staged 0.17.0 sword/trail changes at the user's explicit request. The user reported the card's 0.16.0 runs; this combined release requires its own console test.
- Release/plugin/asset checks pass. Manifest: `builds/pgwr/0.18.0/MANIFEST.json`; SD installation record is linked from STATUS. File log includes `[PGWR] BOOT v0.18.0` and `[PGWR-HERO-N]` state/projectile diagnostics. Hardware validation pending.

## 0.17.0 â€” 2026-09-30 (built and staged; **NOT installed**)

- **The jab keeps Chrom's move and loses Chrom's sword.** 0.16.0 shipped a
  `chrom_sword` article clone; on hardware the hitboxes and animation were right
  and **no sword appeared at all**. The cause was never found (`handbook/graveyard.md`
  R-22). Rather than keep debugging a permanent-weapon article that vanilla never
  poses from script, the jab now draws **Pyra's own Aegis esword** - one of eflame's
  five native articles, the same one the fair has used since 0.14.1 - and trails
  with the same **Mythra** textures the fair uses. One weapon, one effect, two moves.
- **Jab ACMD:** frame 3 `set_visibility_whole(true)` + `add_motion_partial("to_open")`,
  frame 20 `to_close` + `set_visibility_whole(false)`. This is byte-for-byte the
  pattern 0.15.1 proved on hardware for the fair. Chrom's afterimage *timing* is
  kept (trail on 3, off 8) so the blade and its trail start together as they do in
  his own script. Hitboxes, damage, angle, knockback, hitlag, hit-attribute,
  reference joint and the `attack_11` entry (cancel 23) are all unchanged from 0.16.0.
- **Fair trail retuned â€” the fix for "the trail no longer matches the sword".**
  `AFTER_IMAGE4_ON_arg29` is called with two bones, both the **body's** `sword1`,
  which no code scales; `build_esword_pose.py` scales the **article's** `Sword1` by
  1.4. So after 0.15.2 the blade grew along a chain the ribbon does not ride and the
  trail stopped short. The call's 7th argument is the only bone-space length among
  its 29 - Mythra passes `14.5`, where her blade tip sits - and it is now
  `TRAIL_TIP = 14.5 * 1.4`. **Derived, not measured, and untested**; it is the one
  thing the next hardware pass is for. `unk26`/`unk27` are left at Mythra's values as
  the next lever, one change at a time (rule 11).
- **One visibility guard, not two.** `attack_air_f`'s guard is renamed
  `esword_visibility_guard` and now lists `attack_11`/`attack_12`/`attack_13`
  alongside `attack_air_f`. The fair and the jab share one article and one set of
  clips, so two guards would race on the same motion transitions and the winner
  would be registration order. `chrom_jab` no longer registers a guard at all. Still
  keyed on motion *transition* only (rule 19).
- **`chrom_sword` removed outright**, not left dormant: the `clone_weapon` call, the
  accessor, the 8 slots of `fighter/eflame/{model,motion}/chrom_sword/*` and the 136
  `config.json` declarations (17 paths x 8 slots). Local article id 7 is free again.
  Mod tree **1369 -> 1233 files**. `refs/chrom_jab/` is kept as the donor record for
  the retargeted animation.
- **Size policy settled by the user:** keep 1.4x and retune the trail. Recorded in
  the manifest that the size is a **per-clip** value, so the fair and the jab cannot
  be given different blade sizes without a second article - they both drive
  `z00open`. Known cost: the 1.4x tip overhangs Chrom's jab boxes, which reach ~11.9
  along `sword1`. Cosmetic only.
- **Not installed.** The user asked that the card be left alone. `build-plugin.sh
  --stage-only` was used deliberately and `install-to-card.sh` was not run, so the
  card still holds 0.16.0. NRO `307ba0d3â€¦` (225,280 B), mod tree
  `5bc99a39â€¦`, 1233 files, config groups c06 58 / c07 57 (was 75 / 74).
  Manifest `builds/pgwr/0.17.0/MANIFEST.json`.

## 0.16.0 â€” 2026-09-30

- **The G&W costume's jab is now Chrom's jab**, with Chrom's own sword. Donor
  `lua2cpp_chrom/chrom/Attack11.txt`: three hitboxes (one on `top`, two on `sword1`)
  active frames 5-8, 6.5%, angle 62, 60 BKB / 40 KBG, hitlag 1.4 - taken verbatim. The
  animation is Chrom's 42-frame `c00attack11.nuanmb`, retargeted by
  `tools/build_chrom_jab.py`, and the motion entry is Chrom's own (`attack_11`, cancel
  frame 23; G&W's was 16).
- **The old jab was a one-frame pose** (`gamewatch/c00attack11.nuanmb` is 1 frame over 41
  nodes) played up to three times, because G&W's script set both `ENABLE_COMBO` and
  `ENABLE_100`. Chrom's script sets neither, so the new jab is **one hit and the rapid
  does not start**; `attack_12`/`attack_13` are registered to the same handler anyway, so
  a chain that Pyra's native status starts regardless is still Chrom's slash rather than
  the old spray.
- **New cloned article: `chrom_sword`**, the third weapon cloned onto eflame
  (`clone_weapon("chrom", WEAPON_KIND_CHROM_SWORD 0x1B6, "eflame", "chrom_sword", false)`,
  local article id `TERM + 2` = 7). It is the first article here that is not G&W's, and
  the first whose donor directory name (`sword`) differs from its name on eflame - the
  name passed to `clone_weapon` is what smashline substitutes into the engine's `get_file`
  lookup, so both strings matter and either one wrong is a silent no-load.
- **Why Chrom's sword rather than Pyra's.** The Aegis article owns its pose in its own
  clips (R-20/R-21) and no body clip could re-aim it. Chrom's sword is the inverse: its
  motion list holds only `entry_l`/`entry_r`, its skeleton is two bones (`HaveR` ->
  `Sword`) and its single mesh is skinned to one of them, so *the body animation aims the
  blade*. Measured: its blade runs along +z with its tip at 10.908 against the Aegis
  blade's 11.39, so the reach is unchanged to within half a unit.
- **The retarget filter changed with it.** `build_cloud_fair.py` filters donor nodes
  against G&W's own 45 bones and keeps 36 of Cloud's; that is enough when only G&W's mesh
  is drawn. For a body-aimed weapon it is not: the jab clip is filtered against the
  **built** 165-bone grafted skeleton and keeps **80 of 96**, including `Sword1`/`Sword2`.
- Donor material was live-extracted: `refs/chrom_jab/` holds Chrom's Falchion
  (model + motion for all eight costumes), his body skeleton and params - 139 files, 0
  failures, per-file sha256 in `extraction.json`, provenance in `SOURCE.json`. Tool:
  `tools/fetch_arc_files.py` (new, reusable, `--check` re-verifies offline).
- **Known gaps, stated rather than implied.** The afterimage is **not ported**: Chrom's
  trail textures are in hand and his three donor lines are recorded verbatim in
  `acmd/chrom_jab.rs`, but the trail needs one-slot-effect routing for the costume. The
  swing sound is substituted (`se_eflame_swing_s01`) because Chrom's bank is not loaded
  for an eflame agent. And the sword is spawned with **no `change_motion`**, which is what
  the donor does - if vanilla status code is what establishes that pose, the clone has no
  donor code to reproduce it.
- Installed 2026-09-30 02:18. NRO `25a1c0fbâ€¦`, 1369 mod files, tree
  `d4da98f0â€¦`. Backup `evidence/sd-backups/sd-backup-20260930-021808` (the 0.15.2 card).
  **No console verification yet** - the move has never been seen.
- **c07 Mythra light sword effects rebuilt from scratch** (installed 2026-09-30 02:27).
  Derives c07's effect bank (`ef_elight_c07.eff`) and sword trails (`trail_c07/`) directly from
  the c06 dark effects donor bank (`refs/skins/black_and_pink_mythra/mythra skin/effect/fighter/elight/ef_elight.eff`)
  instead of hue-shifting vanilla green effects.
  - Slashes, beams, auras (314 emitters): transformed to brilliant white cores (`[1.0, 0.98, 0.94]`)
    and champagne gold bodies (`[1.0, 0.88, 0.55]`).
  - Sparkles and particles (71 emitters): magenta/purple mapped to soft pastel light pink
    (`[1.0, 0.78, 0.88]`), gold/orange to light gold (`[1.0, 0.90, 0.65]`).
  - Switch transformation (25 emitters, `P_ElightChangeStart/End/Win3`): brilliant white core,
    light gold body, and soft light pink sparkle bursts.
  - Sword trails: radiant white core (`[255, 255, 255]`), light gold body (`[248, 215, 140]`).
  - Bit-for-bit preservation of all 594 emitter timings, alpha curves, and particle scale curves.
  - Verified offline with `tools/verify_color_themes.py` (0 errors), packaged, and installed to
    card (`evidence/install-record-2026-09-30_0227.json`). Pre-install backup: `evidence/sd-backups/sd-backup-20260930-022727`.

## 0.15.2 â€” 2026-09-30

- **The Aegis blade is scaled 1.4x on the drawn sword states** (`SIZE_FACTOR` in
  `tools/build_esword_pose.py`). It is applied to `Sword1`, the bone the blade's geometry
  is skinned to, so the blade grows while the hilt stays the size the hand holds. Only the
  states that are drawn are touched (`z00open`, `z00toopen`), and the tool refuses to scale
  a clip whose base scale is not 1 - otherwise the read-back check would not mean anything.
  User report behind it: on 0.15.1 the sword "appears and disappears properly now" but "is
  just too small maybe".
- **That number is a taste value, not a measurement, and the source says so in as many
  words.** Two attempts to measure the blade offline - `fair_sword_geometry.py` v1 (rigid
  attachment to the body bone, refuted as R-21) and v2 (the real article chain) - disagreed
  with each other *and* with the console, so neither was allowed to set it. One number tunes
  it; 1.0 restores vanilla size.
- **The angle is deliberately unchanged.** The user's later report is "the angle might be
  wrong, I'm not sure", which is not a basis for a change, and nothing offline has yet
  predicted the in-game orientation correctly. Settling it means *reading* the orientation on
  the console - the plugin can log the sword article's own joint positions during the fair -
  rather than modelling it a fourth time.
- `build.py::safe_rmtree()` now retries on `OSError` rather than only `PermissionError`. A
  wipe died with `[WinError 145] The directory is not empty` and left the package half
  deleted; the wipe is the first thing `main()` does, so that failure had already destroyed
  the previous package by the time it was reported.
- Card: 1233 mod files, NRO `930eb327â€¦`, installed 2026-09-30 01:39. Record
  `evidence/install-record-2026-09-30_0139.json`, manifest `builds/pgwr/0.15.2/MANIFEST.json`,
  rollback `evidence/sd-backups/sd-backup-20260930-013943`.
- The plugin binary differs from 0.15.1 in its version banner only.

## 0.15.1 â€” 2026-09-30 (plugin: diagnostics only; the asset change below is behaviour)

- The unmeasured half of Monkey Flip's capture is the **victim's** half, so the move
  now logs both sides. `plugin/src/status/monkey_flip.rs` gains a per-frame `VICTIM`
  line inside the capture window (the leap's own box frames and every cling phase)
  carrying the attacker's `is_catch`/`capture`/`LINK_NO_CAPTURE`, and the victim's
  `status`/`situation`/`motion`/motion frame, its own `is_catch`, its own capture id
  and its own `LINK_NO_CAPTURE` link, plus the victim's distance from the fighter
  (`dist`) and from the `top` anchor the donor's boxes hang off (`dtop`) - the number
  the box-to-victim arithmetic never had. A one-shot `VICTIMSTATUS` line fires on
  every victim status change, and the victim's status, motion and frame were added to
  the existing `CATCH HANDOFF` and `CLING entry` lines. `vmotion`/`vframe` are
  separate fields on purpose: "never left `WAIT`", "entered a grabbed status with no
  motion" and "in a grabbed status whose motion never advances" are three different
  failures with three different fixes.
- Bounded: 90 `VICTIM` lines and 12 `VICTIMSTATUS` lines per entry, reset on `Pre`,
  so no run can fill the card; every other line stays bounded by the number of phase
  transitions. The reason for the exception is `handbook/16`: the swap project's
  freeze left its log readable only to leap frame 17, so the frames leading into a
  connection have to be on the card *before* it happens.
- No state-changing call was added. Nothing hand-builds a capture: `set_catch` +
  `LinkModule::link` + a victim status request froze the console in the swap
  project's build `.f`, and build `.e` had already shown that `set_catch` alone
  publishes no `LINK_NO_CAPTURE` node and does not route the victim. The engine owns
  the routing and the donor's `CLUNG_DIDDY` stays the victim status.
- Built: `plugin/target/aarch64-skyline-switch/release/libpyra_gamewatch_reskin.nro`,
  225,280 B, sha256 `8cbbab40f6c038bbad8f7e9b8e226167d77457b783ff6af7d03baf857795df5d`,
  markers `v0.15.1`, `VICTIM`, `VICTIMSTATUS`, `dtop=` present and the 0.15.0 banner
  absent from the binary. Offline: `gen_acmd.py --check` reports all four generated
  files up to date, `smoke_monkey_flip.py` OK. **None of that is behaviour evidence**.
- **The Aegis sword on c06/c07 is now hidden from the article's own clips**, after the
  two mechanisms 0.15.0 shipped turned out to do nothing at all:
  - `tools/build_esword_pose.py` (new) writes `fighter/eflame/motion/esword/c06|c07/`
    with the `flamesword` mesh-visibility track set per state - **False** in `close`,
    `to_close` and the four `d01specials*` (special-S) clips, **True** in `open` and
    `to_open`. Vanilla has it True in all eight, which is exactly why an article
    generated once stayed drawn for the rest of the match: 24 scripts call
    `generate_article(ESWORD)` and 142 call `add_motion_partial`, so no per-move guard
    can cover the spawn sites (R-18) - the resting state itself has to be undrawn.
  - The state table is asserted at build time against the article's own
    `motion_list.bin`, including that entry 0 is `close`; that entry being the
    resting state is the whole basis of the fix, so it fails the build rather than
    silently shipping a sword that is drawn when it should be hidden.
  - **Retired, and refuted rather than merely untested:** `build.py::hide_esword()`
    (scaled the esword model's `Root` basis to 1e-3) and
    `build_cloud_fair.sword_node()` (a `Sword1` track in the body fair clip). Both
    were live on the 0.15.0 card and left the sword exactly as it was - still drawn,
    still at the wrong angle. The article is posed by its own clips, which animate
    `HaveR`, `Sword1` and `Sword_flameA..E` and never `Root`; a body clip can move
    the hand but cannot re-angle the blade. `handbook/graveyard.md` R-20/R-21,
    `evidence/2026-09-30_pgwr_0.15.0/RESULT.md`.
  - The esword *model* override goes with them (46 files), so the skeleton is the
    game's own again; 0.14.1's copy was semantically identical to vanilla anyway.
  - `tools/fair_sword_geometry.py` is marked **stale**: it models the blade as rigidly
    attached to the body bone, which is the refuted assumption, so its distance and
    cosine figures measure the model rather than the game. Do not quote them.
  - **Not attempted: the blade's angle relative to the hand**, which is still vanilla
    Pyra's grip. Correcting it needs the attach chain confirmed first (owner `HaveR`
    -> the article's `HaveR` -> `Sword1`, blade axis read from the esword mesh).
- `build.py`'s `info.toml` version string was still `0.15.0`; it now reads `0.15.1`, so
  the plugin banner, `info.toml`, CHANGELOG and MANIFEST agree (rule 6). The plugin
  binary is unchanged by this - it was already built at 0.15.1.
- Staged and installed to the card 2026-09-30 01:23: NRO `8cbbab40â€¦`, 1233 mod files.
  Record `evidence/install-record-2026-09-30_0123.json`, manifest
  `builds/pgwr/0.15.1/MANIFEST.json`, rollback
  `evidence/sd-backups/sd-backup-20260930-012319`.

## 0.15.0 â€” 2026-09-30

- Give Mr. Game & Watch on Pyra c06/c07 **Diddy's Monkey Flip on side-B**, ported
  from the frozen swap project (`src/mgw_swap`) and re-derived from the donor dumps
  (`dumps/scripts/.../lua2cpp_diddy/diddy/SpecialS*.txt`):
  - Status machine: eleven custom `eflame` statuses (`0x1EE`-`0x1F8`), allocated
    above `FIGHTER_EFLAME_STATUS_KIND_NUM` and asserted at load, in
    `plugin/src/status/monkey_flip.rs`. Side `SPECIAL_S` now interrupts into the
    first phase, so c00-c05 keep Pyra's Rethunder Toss untouched.
  - ACMD: the donor's own `game_`/`effect_`/`sound_`/`expression_` scripts for the
    eleven phases in `plugin/src/acmd/monkey_flip.rs`, including the donor's two
    `CATCH` boxes and their clear schedule. Donor sound names are mapped to
    resident `se_eflame_*` names; donor voice clips are dropped; Diddy's effect
    names are kept and will not spawn on `eflame` (recorded open item).
  - Assets: Diddy's twelve clips retargeted onto the recipient skeleton
    (`src/pgwr/tools/build_monkey_flip.py`, importing the swap project's debugged
    helpers) and shipped under **spare eflame clip names** - no new file name is
    introduced, so `config.json` is unchanged. The donor's twelve motion entries
    are copied whole into `motion_list.bin`, with only their animation-name field
    repointed.
  - Offline verification: `src/pgwr/tools/smoke_monkey_flip.py` (donor data,
    twelve distinct retargets, plugin/asset script agreement) and the plugin
    compiled at 0.15.0. **Not confirmed on hardware.**
- Remove Judge from side-B. Its status (`0x1EE`), its ACMD override and
  `plugin/src/status/judge.rs` are gone; one button cannot own two moves, and its
  first phase now uses the freed id. The file-addition probe Judge carried
  (`d01specialsl.nuanmb` under its own name, declared in `config.json`) is still
  built and still byte-exact, but nothing plays that motion kind any more, so the
  probe is no longer exercised at runtime. See `STATUS.md`.
- Fix the fair's sword on Pyra c06/c07 (the Aegis `ESWORD` article):
  - Grip: the article hangs off the *grafted* `Sword1` hand bone and no body clip
    animates that bone, so the blade took the hand's own +z and pointed away from
    Cloud's hitbox. `tools/build_cloud_fair.py` now writes a constant `Sword1`
    track into the fair clip, turning the grip 180 deg about the bone's local Y.
    Measured with `tools/fair_sword_geometry.py`: blade-to-hitbox mean distance
    10.57 -> 5.37, direction cosine -0.79 -> +0.79.
  - Size: measured, not guessed. A scale sweep on the corrected grip gives
    0.8/5.34, 0.9/5.23, 1.0/5.37, 1.1/5.72, 1.4/7.20, so the blade was **not** too
    small and stays native. The residual ~5 units is positional - it belongs to
    the hitboxes, not the blade.
  - Visibility: the 0.14.1 `sword_visibility_guard` was refuted on hardware (it
    only reacted to a motion change, while 48 eflame scripts generate the
    article). Replaced by a *model* lever: `hide_esword()` scales the esword
    skeleton's `Root` basis by 1e-3 instead of collapsing it to zero - zero cannot
    be scaled back up - and the fair clip scales `Sword1` back by 1e3, so the sword
    exists only while the fair plays.
  - Offline only. Open question: whether a bone scale propagates to the article
    attached to that bone.

## 0.14.1 â€” 2026-09-29

- Port Cloud's Forward Air (`AttackAirF`) to Mr. Game & Watch on Pyra c06/c07:
  - Animation: retargeted Cloud's `c05attackairf.nuanmb` and `c05landingairf.nuanmb` to G&W humanoid skeleton with G&W idle visibility tracks.
  - Motion parameters: Cloud cancel frames (54 for fair, 20 for landing) written to `motion_list.bin`; landing lag set to 11.0f via param bridge.
  - Hitboxes: full Cloud hitbox set (frame 18 spike angle 270 / grounded 60 / aerial sweetspot & sourspot 45; frame 20 late hit).
  - Weapon: Pyra's Aegis sword (`ESWORD`) model uncollapsed; dynamic `sword_visibility_guard` enables sword article during fair and hides it on all other moves. **Refuted on hardware 2026-09-30** - the guard only reacted to a motion change, so the sword stayed out on every other move. Replaced in 0.15.0; see `handbook/graveyard.md` R-18.
  - Effects: `AFTER_IMAGE4_ON_arg29` sword trail on `sword1` (frames 16â€“26); themed Mythra sword trail textures deployed to `effect/fighter/eflame/trail_c06` and `trail_c07` via `libone_slot_eff.nro`.
- Apply pale champagne effect palette to c07 Mythra sword glow and edge-mask textures.
