# Ready asset batch 1 — installed 2026-10-03

User request: "they are not all done, but install the ones that are done already".

Included only READY deliverables: chrom-jab-sword-1.0.0; lucas_ness_effect_theme-0.1.0; loading-presentation-0.1.0. Excluded: Hero level-2 angle/mana HUD and dash-grab slide (no ready handoff); up-B gravity (PENDING, no concrete installable package; its verification binary contains concurrent work). No live worker source compiled or modified.

Package: `builds/pgwr/0.20.20+ready-assets.1/`; baseline `builds/pgwr/dk_cargo-0.1.1-test/` including Incineroar. Plugin/info version 0.20.20 inherited unchanged; asset batch/task versions recorded in MANIFEST. This is an asset-only release variant, not a new runtime version.

Verified B: card matches baseline 5098/5098 before installation; effect package preservation/loader resolution passes; loading audit passes native route matrix, player panes, reproduction/conflict controls; jab audit passes including its negative controls. All eight delta payloads match task manifests, UI PRCs applied semantically. Collective scope: exactly seven existing files changed, one added, zero removed; every other baseline byte retained. Config, all gameplay clips/params/sounds and plugin binary unchanged. All 5099 installed mod files rehashed against package and manifest; all plugin hashes unchanged. Framework install OFF. No console/emulator run by installer.

- NRO SHA-256 `214dc3126430598fb5e71093f6d5d584e17e662a593b67acf0eb0b777eb66058` (unchanged).
- Mod tree SHA-256 `a38d16c037389f730c842fc70fbda04b033b2dfc1e70ee7f4060520702dbf153` (sorted relative-path/TAB/hash/LF), 5099 files.
- Destination: `sd:/ultimate/mods/pyra_gamewatch_reskin/`; inherited plugin at `sd:/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpyra_gamewatch_reskin.nro`.
- Automatic rollback backup: `evidence/sd-backups/sd-backup-20261003-114100`.
- Evidence: PRE_INSTALL.json, POST_INSTALL.json, JAB_AUDIT.json, jab-audit-output.txt, LOADING_APPLY.json, installer-output.txt; package MANIFEST.json and COLLECTIVE_DELTA.json.

First install attempt failed at final directory rename with `mv: cannot move ... Permission denied`; automatic rollback restored 5098 files and all plugin hashes, independently verified in ROLLBACK_VERIFIED.json. A concurrent read-only staging traversal was in flight; directory-handle contention is a hypothesis, not an established cause. Retried the identical package with no concurrent card reads, then performed the recorded post-install comparison. First-attempt output retained in installer-first-attempt.txt.

All new runtime/visual outcomes unverified (tier D). Offline jab investigation identifies an invalid animation-name hash; it does not establish hardware causality without a controlled run. The original agent checklist incorrectly described vanilla Pyra/Mythra jabs as having no sword; use the unchanged baseline/stock fighters as controls, not that description. A combined visual failure does not isolate a cause; restore prior bootable package if a new crash occurs.

## Console checks

1. Fresh boot. On c06 and c07, enter Training starting as G&W, then starting as Mythra: the loading screen should show the selected body and correct costume/name. Repeat a two-player Versus match; check five/eight-player loading when convenient.
2. G&W c06/c07: single jab and jab chains facing both ways. Sword should appear with the swing and existing themed trail, then disappear after the jab. Check interruption by hit/grab/KO and later idle/walk/jump for stuck visibility.
3. Check G&W forward air: its larger sword and trail must retain the prior appearance/timing. Swap to Mythra and back; verify jab visibility returns only where appropriate.
4. Mythra c06: tap and charge Lucas down smash, then Ness back throw. Expect scarlet/crimson with magenta/violet accents; existing timing, damage and sounds should remain unchanged.
5. Mythra c07: repeat both moves. Expect light white/gold with pink accents. Check both facings and interruption cleanup. Other themed effects must retain their previous appearance.
6. Vanilla Pyra/Mythra c00 and c05, plus real Lucas/Ness/G&W: compare against the prior baseline. Preserve CSS previews, costume names, battle HUD, results and starting-form selection.
7. Spot-check DK cargo, Incineroar back throw, Snake down throw/grenade and the form swap. Report each of the three new changes separately. No new per-move log markers exist for this asset-only update; BOOT v0.20.20 cannot distinguish it from the prior binary. Return available ultimate logs from boot and any newest atmosphere/crash_reports file on crash. No up-B gravity, dash-grab slide or Hero angle/HUD fix is included.
