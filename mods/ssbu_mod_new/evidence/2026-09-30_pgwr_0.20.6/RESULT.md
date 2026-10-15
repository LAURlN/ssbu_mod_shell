# Monkey Flip 0.20.6 console result - 2026-09-30

Tier A: user reports "so it works now" and "the opponents just t pose when grabbed and don't enter the grabbed animation". Capture confirmed; victim pose fails. The user accepts deferring that pose issue if difficult. Attack/jump release was not separately confirmed in the user's report.

Install: `evidence/install-record-2026-09-30_122044.json`; package `builds/pgwr/0.20.6/MANIFEST.json`.
NRO sha256 `f56efc2a6d66a3d97bc946a38ddff2d2fec9af57c640ae3e58f05480ab2f2e07`.
Mod tree sha256 `8dde9d8f975f6c7d63df6d56a1240d7e0d6429cfe65d0f2bb1f16a7c2cfb60f3`, 1701 files.
Log `pgwr_log.txt` sha256 `1db52e0811a5b1adc363496fa3af79b5552289ef84fbe847694ff0c3709d47ef`; final boot line 2604.
10 EVENT, ACCEPT, SETUP and CLING entries; zero REFUSED. 447 victim samples show capture and status 0xf0.
Victim motion hash 0xbe8fc34b2 and advancing frame are logged; this is insufficient evidence of the intended visual pose.
No stock Diddy telemetry in this boot; prior 0.20.5 donor capture control retained. No crash/freeze reported.

Verdict: capture passes, grabbed pose fails. Aerial-use restrictions are missing: user notes stock Diddy cannot repeatedly Monkey Flip without landing and cannot up-B after the kick before landing/hit. Port native end flags and their availability checks in separate controlled builds per workspace rule 11.
0.20.5 vs 0.20.6 changed guard call boundary and rejection forwarding together. The result supports that correction as a whole, without isolating syscall register clobber as the cause.
