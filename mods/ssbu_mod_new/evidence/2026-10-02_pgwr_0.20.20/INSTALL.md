# pgwr 0.20.20 collective installation — 2026-10-02

User request: "they're all done now, install on the switch". Installed to the identified Switch SD card (E:) with `src/pgwr/install-to-card.sh --no-smashline`, `MGW_PACKAGE=builds/pgwr/0.20.20`.

Included: Snake down throw on eflame c06/c07; Lucas down smash and Ness back throw on elight c06/c07. Excluded: DK cargo (BLOCKED, no runtime implementation) and Incineroar back throw (PENDING, incomplete victim/native routing). No reserved hook or framework change included. Ness camera zoom/offset remains the donor-port's documented gap.

Verified B: pre-install 0.20.19 card/package equality, 1984/1984 files. Individual audits and negative controls passed for all three deltas. Fresh offline combined 0.20.20 build passed with existing dead-code warnings, features snake-neutral-b,hero-side-b; logging and hero-mana-reserved off. Task-owned Cargo home/target under builds/.cache. First sandbox build failed with `error calling dlltool 'dlltool.exe': Zugriff verweigert (os error 5)`; same offline build passed with tool execution permission. No emulator or game launch.

Assembly: copied verified baseline, applied Snake and Lucas asset deltas, copied Ness clips, merged Ness throw_b entry with Lucas attack_lw4 entry, appended Ness sounds/sequence after Lucas and merged NESS_PSI_RUSH after both Lucas emitters. Both slots retain every baseline emitter plus exactly three new names (131 total, not the handoff's stated 130); all samples, tones and labels retained, only two Mythra motion entries and one eflame throw entry differ. All six new clips match agent payload hashes. Scope allowlist: 34 changed/added mod paths, six added, zero removed. Config unchanged. Full build.py was not run; baseline asset checks are inherited through unchanged hashes, and new dependencies were audited separately. Built/package/card NRO equality and all four protected framework hashes checked.

- NRO SHA-256: `7242d2f5af32bcc5304aa0e94930fe22ac689bd21db9b213f2ecfdac5fbf2098` (479232 bytes).
- Mod tree SHA-256: `10cd7a07a629897aa24c775173cffbfa13f071c5308f19fe0b483995a9f78abc`, 1990 files.
- SD destinations: `sd:/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpyra_gamewatch_reskin.nro` and `sd:/ultimate/mods/pyra_gamewatch_reskin/`.
- Automatic backup: `evidence/sd-backups/sd-backup-20261002-193356` (0.20.19).
- Evidence: MANIFEST.json and COLLECTIVE_DELTA.json under builds/pgwr/0.20.20; installer-output.txt, protected-before.json, protected-after.json, post-install-verification.txt and card-artifacts.json in this evidence folder.

Corrections: Ness handoff misread ATTACK_ABS: 11 is damage, 135 angle, 130 KBG, 0 FKB, 15 BKB. Fixed CURRENT_INSTALL.md and source comment; executable donor constants unchanged. Earlier Snake/Lucas compile-blocker notes were stale; combined build settles compilation. PENDING solely for a missing hardware verdict is now installation complete / hardware unverified.

## Console checks

1. Fresh boot. In Training, compare stock Snake/Lucas/Ness with their ported moves. Check vanilla Pyra and Mythra c00: the corresponding moves remain vanilla.
2. G&W body (Pyra c06): grab, choose down throw. Expect Snake's animation, 9 damage, and the victim placed prone rather than launched. Check normal get-up options at low and high damage.
3. Repeat Snake down throw facing both ways on small and large victims. Confirm release, sound, and recovery; other throws and down smash retain their previous behavior.
4. Mythra c06: use down smash (down + attack / smash-stick input), both uncharged and charged. Expect Lucas's charge pose/PSI orb and three successive PSI attacks with sounds. Compare spacing and hits to stock Lucas; do not require one victim to take all three hits.
5. Repeat down smash facing both ways, then interrupt the charge and the attacks with an opponent hit. Check that effects stop and the fighter recovers normally. Note any unusually long recovery/cancel behavior: donor motion metadata says cancel 316 while the clip is 74 frames; runtime interpretation is unverified.
6. Mythra c06: grab and choose back throw. Expect Ness's animation/PSI/sounds, 11 damage and a backward/upward launch; verify release and both facings with small and large victims. Default finish-camera zoom/offset is a known gap.
7. Repeat all three new moves on c07 and after swapping bodies with down-B. Check existing Snake grenade/up tilt, Monkey Flip, Fire, Little Mac forward smash, R.O.B. down tilt, Mythra up air/up-B, Hero specials/mana and Luigi down throw for regressions.
8. Report each move separately, with costume and facing. On crash, send the newest atmosphere/crash_reports file and available ultimate logs from boot. Logging is off for these three new moves, so no new per-move success markers are expected. Existing Snake/Hero logs, when present, should identify BOOT v0.20.20; a BOOT marker verifies version only, not gameplay.

All gameplay remains unverified (tier D). A failure in this deliberately combined package does not identify which change caused it. Compare against 0.20.19 backup before attributing cause; earlier/new crash requires restoring last bootable state.
