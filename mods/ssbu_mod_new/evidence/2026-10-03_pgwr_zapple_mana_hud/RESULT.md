# Hero Zapple angle + owned battle mana HUD — 0.1.1 — 2026-10-03

READY for collective installation; NOT installed. Runtime/visual claims unverified (tier D). No emulator, console, card access, commit, push or framework change.

Package `builds/pgwr/zapple-mana-hud-0.1.1/`; plugin/banner/info version 0.20.21. MANIFEST SHA-256 `5e0219f203ec6cbb8a66d953ca8adc08032659b44af3bee28a44cc515893c019`. Installed baseline remains `builds/pgwr/0.20.20+ready-assets.1`, NRO `214dc3126430598fb5e71093f6d5d584e17e662a593b67acf0eb0b777eb66058`.

| Variant | NRO SHA-256 | Bytes |
|---|---|---|
| combined | `48291984dfc2ae4e5c0b92ab19c15312807170f643f68bc992a792f98b3c2b65` | 585728 |
| angle-only | `5c9007035b87fc2f79c1dc6e9b2de352d29f2797ab9f3e2115f27b9aa5179ec6` | 581632 |
| hud-only | `8af1619d2ab2f0c4e335dd8375b9709be3b0d76836d139bd42965fd58479e241` | 585728 |
| baseline-control | `3a0c6d0760c7a9c5bb3f360a6d7ef7ae6d9034a61d330cd8fa7289c5772e3eb9` | 581632 |

Mod tree `7bade18fdeb9a12de6eccb66586e44b4b53f4a405e55755d910b2edf8ecb3e5f`; 5099 files. All 5098 files other than info.toml byte-identical to latest ready-assets.1; info changes only version. Chrom jab, Lucas/Ness effect themes and loading assets retained. Mod asset delta is zero. Source is the installed DK/Incineroar snapshot plus six narrowly checked files (four HUD/feature files, one angle file, Cargo.lock version). No dashgrab/up-B gravity changes. Package controls are NRO alternatives over the same asset tree, not overlays to install together. Baseline-control is the installed source rebuilt at version 0.20.21, not a byte-identical replacement for the installed NRO. All hashes are in MANIFEST.

## What changed

Continued Opus's native call route (hero-mana-hud independent of hero-mana-reserved). The owned per-entry meter feeds native panel selection/SP update/shortage flash for active c06/c07 eflame and elight. No instruction hook or vtable write added. Every frame re-resolves the entry's own HUD player and panel; no dereferenced game pointer persists across frames. Unknown classes/parts refuse. Range-checked reads, bounded listener walk, cooldown/thrash limits and capped lock-free diagnostic gates remain. File logging holds no lock over a game call.

Fixed two lifecycle errors found by source inspection: per-entry dead/refusal/cooldown state now resets once at the owned stock/entry boundary (swaps preserve it), and the eight-frame instant-set window now counts observed frames even with unchanged MP. Existing mana spending/regen/stock logic is preserved. Native destruction/reselection remains responsible for removal on CSS/player replacement; hardware checks remain necessary.

Retained Zapple `(16.3,18.2,-83.5)` as a hypothesis-driven visual correction. Ground +X direction error 0.0191/0.0379 degrees, air 0.0414/0.0665 under the two tested Euler orders, for both costumes. This aligns an assumed emission +X with the donor joint; the actual emitted axis, roll and rendered effect are not established. The user said roughly 5%, not a numeric requirement. Corrected the source comment that treated this joint calculation as the established cause/rendered angle. Level 1, level 3 and all hitboxes/knockback remained semantically identical in the script scope check.

## Verified offline (tier B)

- Final combined NRO reproduced byte-for-byte after explicit cross-snapshot cache invalidation (`build-reproducibility-final.txt`).
- Four isolated release builds passed offline, with existing dead-code and DK/Incineroar Vector3 FFI warnings; no new HUD warning. Final captured build logs: build-combined.txt, build-hud-only.txt, build-angle-only.txt, build-baseline-control.txt here. Packaged NROs hash-equal to built NROs.

- Native audit: 25 full spans + 9 relocated vtable slots MATCH, generated Rust table IDENTICAL. Native smoke: FNV reference vectors and one-bit mismatch control PASS. Pinned image SHA-256 `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`.

- HUD audit: each HUD-enabled build 115 constants + 17 structure + 9 source + 20 NRO feature checks, zero mismatches. Smoke: five correct/wrong constants, chara hash and non-Hero selector controls PASS. Reports codex_hud_combined.json / codex_hud_hud-only.json.

- Four joint measurements rerun against the latest installed clips; solver smoke eight checks PASS. Rotation constants present in combined and absent in HUD-only (codex_nro_angle.json).

- Package --check: 5099-file hashes, version consistency, four NRO hashes/feature markers, exact six-file source scope, every unrelated installed-source file unchanged. All three LF narrow patches applied sequentially to an isolated installed snapshot and reproduced final source text. No source dependency revisions changed.

- Source inspection: signature mismatch branches return before ENABLED; per-entry gates/refusal/teardown behavior above. No console signature-mismatch injection was run.

## Failures / corrections during recovery

The first default build hit Skyline target-json PermissionDenied outside the workspace; existing tool execution permission enabled the offline build. One relative target path was wrong, causing a partial cache inside the isolated builds/.cache snapshot; it was stopped and the intended cache selected. Source-scope check initially counted that target cache, then was corrected to exclude build artifacts. No system dependency installed.

A baseline-control NRO failed the HUD audit's expected new HUD-absent literal because its original source never had that diagnostic. The original baseline was preserved; angle-only supplies that check instead. An initial narrow patch failed on mixed LF/CRLF context; final patches use LF and all apply cleanly. A temporary package-tool string edit produced an unterminated string SyntaxError, repaired before packaging verification. A docs read failed under the host CP1252 default (UnicodeDecodeError); task-written docs were normalized to UTF-8 and the changelog update completed. A reproduction build without the documented src/lib.rs timestamp invalidation served HUD-only from the shared cache; feature/hash mismatch caught it before packaging. Final reproduction uses invalidation; never trust an uninvalidated cross-snapshot cache. Opus's cached manifest is now marked SUPERSEDED: its asset baseline was outdated and its cache location was not a deliverable.

## Remaining hardware uncertainty (tier D)

Native panel initialization, drawing/placement, update thread/lifecycle and 5-8-player layouts are not verified. svcQueryMemory guards readability at the read instant, not concurrent lifetime; this route assumes the fighter/HUD event context is serialized as native donor dispatch is. Calling selection directly on the fighter Main line is still a runtime assumption. The existing owned meter lacks a shared simulation-frame dedupe token: if Main callbacks duplicate at status changes, regen can advance extra ticks. This task preserves that installed logic and explicitly tests the rate. Recovery-on-hit/shield remains disabled. READY means concrete checked package, not a successful hardware result.

## Console checks (11)

1. Have the designated installer verify the chosen NRO hash. Start with baseline-control, then angle-only and HUD-only in separate boots, using the same assets and match setup. Compare the combined build only after each change passes alone. Development agent made no card change.

2. Vanilla controls: Pyra/Mythra c00 and c05 retain their own HUD and moves; real Hero retains normal MP; Kirby copying Hero retains normal MP. Another ordinary fighter never gains this gauge.

3. For c06 and c07, enter directly as Mythra, then directly as the G&W body (eflame). Expect an owned MP gauge on that player's actual damage panel, initially 100. Compare the baseline-control: no added pair gauge there.

4. Mythra level-2 side-B: ground/air, facing left/right, both costumes. Compare baseline-control versus angle-only, same camera and charge. Judge whether the bolt now points naturally forward and is no longer too high. Check level 1 and level 3 look and launch as before. A worse angle is a failed candidate; revert angle only.

5. On HUD-only, spend N1/N2/N3 (6/16/36 MP) and S1/S2/S3 (8/18/42 MP). Gauge follows the SPEND totals. Hold charging: no passive refill. Idle: RECOVER +1 per 60 observed active Main callbacks, up to 100; confirm real-time rate on hardware.

6. Drain below the chosen spell price, then attempt it: REFUSE, no debit/projectile/lightning, shortage flash on the owned gauge. Regenerate until affordable and cast again. HUD refusal must never disable the spells' existing meter.

7. Spend, swap to G&W and back at least ten times, spaced apart, including under damage and while moving. MP remains shared (apart from logged recovery). Gauge stays visible on both forms and never changes another player's gauge.

8. Lose a stock on either form: RESET to 100, no stale shortage or old amount; respawn and spend again. Leave to CSS, select vanilla in the same player slot, then rematch with c06/c07. No stale mod gauge on vanilla and a fresh 100 MP for the new mod pair.

9. Two modded pairs in different player slots: spend different amounts, swap independently; no cross-talk. Reorder player/controller slots and test teams, then a 5-8-player match with a real Hero. Verify each gauge belongs to its player and fits the condensed HUD.

10. Pause, end match, results, rematch and return to CSS repeatedly. No crash/stuck gauge. On combined build, regress DK cargo, Incineroar back throw, Chrom jab blade, Lucas/Ness effects and loading portraits. These assets/registrations were preserved offline.

11. Return the mana log from boot plus the ordinary pgwr log; on crash, the latest atmosphere crash report. Treat any HUD REFUSED / SELECT-FAILED / OFF as a failed HUD test even if gameplay remains playable. Save the chosen variant hash with the log.

## Exact diagnostics

File: `sd:/ultimate/pgwr_mana_log.txt` (append-only across boots; identify each boot's registration block; capped at 4000 lines per process). Also `sd:/ultimate/pgwr_log.txt`; crashes under `sd:/atmosphere/crash_reports/`.

Exact success literals:

- `[PGWR-MANA] HUD READY route=game-part-selector spans=25 slots=9 chara=0xc1ffff0e29e05d6a (no hook installed)`

- `[PGWR-MANA] HUD BIND entry=<e> form=<mythra|pyra> player=<p> panel=<i> class=<a|b> selects=<n> mp=<value>`; REBIND may replace BIND on swaps. `pyra` names the G&W body's internal eflame form. Entry, HUD player and panel are distinct mapped indices, not assumed equal.

- At a fresh full-meter S2 cast, e=0: `[PGWR-MANA] SPEND entry=0 form=mythra label=S2 price=18 100 -> 82.0` (use actual e and pre-cast total; regen may alter it).

- `[PGWR-MANA] RECOVER +1 <before> -> <after>` and `[PGWR-MANA] RESET by=stock mp=100.0`.

- Insufficient MP: `[PGWR-MANA] REFUSE entry=<e> form=mythra label=<N1..N3|S1..S3> price=<price> mp=<value> short=<missing>`.

- Angle-only: `[PGWR-MANA] HUD absent: built without the hero-mana-hud feature`. Baseline-control predates this diagnostic and does not emit it.

Failure literals: `[PGWR-MANA] HUD REFUSED signature `, `HUD REFUSED slot `, `HUD REFUSED entry=`, `HUD SELECT-FAILED entry=`, `HUD OFF entry=`. Signature/slot mismatch returns before enabling any HUD call. Structural refusal skips that player; repeated selection failures or thrashing disable its gauge until a stock/entry boundary. `HUD LOST entry=` alone is expected during HUD teardown and should be followed by successful display when battle resumes. `BUDGET reached; later events are not written` means the log is incomplete; it is not a HUD failure. BIND proves a selected native part pointer, not drawn pixels; READY proves signature checks, not visual success.

