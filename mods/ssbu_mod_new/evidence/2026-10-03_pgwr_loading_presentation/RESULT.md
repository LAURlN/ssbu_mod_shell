# Loading presentation 0.1.0 — 2026-10-03

**READY for collective integration; NOT installed. B verified offline; visual behavior
unverified.** No console, emulator, SD access, framework changes or gameplay edits.
No raw-offset hook is introduced; native analysis was read-only.

Delta: two themed G&W portraits for eflame-first c06/c07, four costume-specific
loading layout rows and four layout routes. Shared databases are regenerated as
semantic unions against the installer's final candidate, not stale replacements.
Ursula uses installed Shadow Purple artwork; Wilhelmine uses installed Golden
Light artwork. eflame-only artwork and **every** Mythra asset remain unchanged.
Exact 1036x1164 G&W BNTX files, all mipmaps, are reused without re-encoding.

Baseline includes Gaogaen 0.3.0 and DK cargo 0.1.1-test on shared 0.20.20:
`builds/pgwr/dk_cargo-0.1.1-test/ultimate/mods/pyra_gamewatch_reskin`.
Verified 5098/5098 files against its manifest and tree
`dae0bff00e20cbe3b5da37215fe82f745ac27c7d8776d180fd08644fc3be6f5e`.
Inherited NRO also rehashed:
`214dc3126430598fb5e71093f6d5d584e17e662a593b67acf0eb0b777eb66058`.
Calculated task-only union: 5099 files, 3 changed, 1 added, 5095 unchanged;
tree `0f768dec7d0992903022406c4df368f65c0a0808e21427c389e5318b45f64c95`.
This is a calculated union of checked files, not an installed/card tree claim.

| Delta path | SHA-256 |
|---|---|
| ui/param/database/ui_chara_db.prc | 2c256f3398173acb6eab32320a22373aa8af19cb96468ad19742fb92cb7f1414 |
| ui/param/database/ui_layout_db.prc | 71b03f6dfb503fc9c2c3c8a409ef48a58f1946ad19c2c68c5f94672102c9d2ee |
| ui/replace_patch/chara/chara_3/chara_3_eflame_first_06.bntx | bb0def2d8c68cf620146351532de67b31f75179a3394f02628a32958ddac2630 |
| ui/replace_patch/chara/chara_3/chara_3_eflame_first_07.bntx | 55ed0574aa4da5e333e058b3aefb260328a99914e08452b1c3fee4689865774d |

Measured native mapping and exact input hashes: `AUDIT.json`, `NATIVE.asm.txt`;
canonical findings: `handbook/18_loading_presentation.md`. Native path was resolved
from local main and ARC resources, not guessed category numbering. Both 2/4-player
first-form and 5/8-player only-form routes have database resolution checks for both
costumes and both starts (16 matrix rows). All eight player pane names exist.
PRC round trips, identical four-file reproduction, repeat application, invalid
route rejection, occupied layout conflict rejection and concurrent Mythra-name/
Pyra-CSS-field preservation controls passed. Every original layout row remained
identical; all non-loading fields on the four new rows retain recipient values.

Extraction (workspace root):

```powershell
tools/arc-extract/target/release/arc-extract.exe --arc gamedata/ssbu-13.0.4/data.arc --out gamedata/ssbu-13.0.4/loading-presentation ui/layout/system/matchup/matchup/layout.arc ui/layout/system/loading/loading/layout.arc ui/param/database/ui_chara_db.prc ui/param/database/ui_layout_db.prc ui/replace_patch/chara/chara_3/chara_3_eflame_first_06.bntx ui/replace_patch/chara/chara_3/chara_3_eflame_first_07.bntx ui/replace_patch/chara/chara_3/chara_3_elight_first_06.bntx
```

Integration must run **after the final build and other UI/name tasks**:
`python -B src/pgwr/tools/loading_presentation/package.py apply --candidate builds/pgwr/INSTALLER_VERSION/ultimate/mods/pyra_gamewatch_reskin`.
Keep the returned four hashes; installer recomputes its collective manifest/version.
Do not copy the two staged PRCs over a union. No config change, new status ID,
NRO rebuild or framework dependency. Existing installed loading source assets and
native game resources are prerequisites. Other tasks' source/config/assets were
not changed. Concrete package: `builds/pgwr/loading-presentation-0.1.0/`.

Test matrix and 10-step checks: `src/pgwr/tools/loading_presentation/README.md`.

| Mode | Costumes / starts | Player slots / count |
|---|---|---|
| Training loading | c06/c07 x G&W/Mythra | trainer slot and CPU as available |
| Versus loading | c06/c07 x G&W/Mythra | P1/P2 at 2; P1–P4 at 4; P1–P5 at 5; P1–P8 at 8 |
| Mixed modded forms | c06 G&W + c07 Mythra, reverse starts | exchange player slots |
| Vanilla controls | Pyra/Mythra c00/c05; stock G&W c00/c06/c07 | Training; 2/5/8-player Versus |
| Regression controls | CSS, HUD, results, names, swapping, Incineroar/DK cargo | both costumes |

Unverified: runtime route, Training transition, visibility, clipping, actual
eye-flash placement, and behavior preservation. There is no asset-patch log marker;
pass/fail is visual versus installed baseline. Retain boot log
`sd:/ultimate/pgwr_log.txt` and any new `sd:/atmosphere/crash_reports/` file.
No reachable-work blocker remains; console observations are required for a fix verdict.

Out of scope: existing decoded c07 Mythra paired artwork shows stray lines/face
color artifacts. It is retained byte-for-byte; broader recoloring/render repair
was not bundled into this G&W loading change.

Development failures (resolved, verified): initial smoke gate wrongly expected
1016px width; actual BNTX is 1036x1164, so the gate now parses the container instead
of asserting a remembered width. Native byte assertions initially used guessed
MOVZ/BL encodings (AssertionError); disassembly resolved the real MOV/ORR alias
`0x320007e3` and BL `0x944d5139`, and the final native checks pass. Git read initially
failed with `fatal: detected dubious ownership`; the read-only command uses a
process-local safe.directory override without changing git configuration.
