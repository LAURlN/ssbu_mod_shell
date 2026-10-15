# Loading presentation 0.1.0

Status: checked offline, hardware unverified; asset/database delta only, no installation.
Baseline: `builds/pgwr/dk_cargo-0.1.1-test`, including Incineroar and DK cargo.
Purpose: selected G&W body on eflame c06/c07 uses the installed themed G&W
`chara_3` artwork and donor loading placement instead of a combined Aegis canvas.
Mythra artwork/routing stays byte-identical. Ursula = c06 Shadow Purple;
Wilhelmine = c07 Golden Light. No image synthesis, recolouring or new filename guesses.

## Reproduce and integrate

From the mod repository root:

```powershell
python -B src/pgwr/tools/loading_presentation/package.py prepare --output builds/pgwr/loading-presentation-reproduction
python -B src/pgwr/tools/loading_presentation/audit.py
python -B src/pgwr/tools/loading_presentation/package.py apply --candidate builds/pgwr/INSTALLER_VERSION/ultimate/mods/pyra_gamewatch_reskin
```

Use a fresh output name for reproduction. The audit checks the canonical 0.1.0
package. `apply` refuses the installed baseline and this task's immutable package.
It returns final four-file hashes. Run it on the installer's staged union **after**
all name/UI tasks: it reads the candidate's current databases, retains unrelated
rows/fields, appends four costume layout rows, and changes just four cNN routes.
Do not overlay this package's two PRC files onto a concurrently assembled release.
The two BNTX files are owned here; conflicting portrait edits cause refusal.
No `config.json` union is required: all four paths are verified in the game ARC index.
No NRO rebuild for this task; retain the installer's collective gameplay NRO.
Installer owns release version/info/manifest, checks overlaps and records installation.

`prepare` needs existing local game resources under workspace
`gamedata/ssbu-13.0.4/loading-presentation/`; extraction commands and hashes are
in the evidence report. `audit.py` reads the existing workspace-local Capstone
5.0.7 install under `builds/.cache/gaogaen_throw_b/python`; it does not modify it.
The image preview uses the existing `texture_cli/ultimate_tex_cli.exe`.

## Check boundaries

Four delta files: `ui_chara_db.prc`, `ui_layout_db.prc`, and
`chara_3_eflame_first_06/07.bntx`. Each BNTX is an exact copy of the installed
`eflame_only` render, including all mipmaps. c06/c07 route to distinct layout
colors on **only** `eflame_first` and `eflame_only`. Four appended layout rows
clone each recipient's existing color-0 row and replace only 24 `chara_3_*`
and 33 `eye_{0,1,2}_*` fields with measured G&W values. CSS, results, spirits
info offsets and all other fields retain the current recipient values.
Vanilla layout rows are untouched; all elight rows/routes are untouched.

Native path: `main+1eea890` selects category 3; `323ed80 -> 32384c0`
builds the texture lookup; relocation-backed category table at `5180998`
maps index 3 to `chara/chara_3/chara_3_`; `is_patch` picks replace_patch.
`32648c0` formats `c%02d_index`; `3280910` matches ui_chara_id and layout color.
At five or more fighters, `1eea82c..1eea888` checks flame/light-first and routes
to flame/light-only. Full instruction windows and input hashes are in evidence.
Training's exact transition and actual cropping, eye flash, player-slot placement,
and resource load success require the user's console test. File checks are not a fix verdict.

## Console matrix (10 steps)

For steps 2–7, repeat **c06 Ursula and c07 Wilhelmine**, and both starting
forms. G&W start expects the themed solo G&W; Mythra start expects the prior
Mythra display. No c07 Mythra artifact repair is bundled with this task.

1. Fresh boot of installer-recorded hashes. Keep `sd:/ultimate/pgwr_log.txt` from boot.
2. Training loading: start as G&W, then Mythra; check image and costume name.
3. Versus two fighters: modded fighter P1, then P2, both starts; check clipping/eye flash.
4. Versus four fighters: cycle modded fighter through P1–P4, both starts.
5. Versus five fighters: cycle through P1–P5; check native `_only` boundary.
6. Versus eight fighters: cycle through P1–P8; verify no blank or wrong-slot render.
7. Two simultaneous modded entries: c06 G&W + c07 Mythra, then reversed starts/slots.
8. Vanilla controls: Pyra/Mythra c00 and c05 in Training and 2/5/8-player Versus;
   stock G&W c00/c06/c07. Compare with the installed baseline, not an assumed vanilla mod state.
9. Regress CSS previews/selection and Ursula/Wilhelmine names; battle HUD, results,
   swap both directions and existing Incineroar/DK cargo behavior must match baseline.
10. Return observations/screenshots and boot log. On failure/crash stop; preserve the
    new `sd:/atmosphere/crash_reports/` report. There is no new runtime log marker
    in this asset-only patch. Wrong form, wrong theme, clipping, misplaced flashes,
    blank portrait, changed vanilla control or any new crash is a failure.
