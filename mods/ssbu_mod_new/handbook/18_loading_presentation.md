# Battle loading presentation

**B, verified offline 2026-10-03** by `src/pgwr/tools/loading_presentation/audit.py`;
evidence `evidence/2026-10-03_pgwr_loading_presentation/{AUDIT.json,NATIVE.asm.txt}`.
Main image sha256 `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`.
All visual behavior below remains **D, unverified** pending controlled console checks.

The measured matchup call at main+`1eea890` passes category 3 into
`323ed80 -> 32384c0`. The relocation-backed path table at `5180998`, index 3,
points to `chara/chara_3/chara_3_` at `441fa1e`. The database `is_patch` flag
selects the `ui/replace_patch/` prefix; database name_id supplies `eflame_first`,
`elight_first`, `eflame_only`, or `elight_only`, with costume suffix `_06/_07`.
These paths exist in the actual ARC index; no added-path/config declaration is needed.
The main loading artwork route examined here is a BNTX replacement texture,
not a battle body-model import. The tips layout `system/loading/loading` is
distinct from `system/matchup/matchup`; the latter contains eight player panes.

For five or more participants the branch at `1eea82c..1eea888` recognizes
`ui_chara_flame_first`/`ui_chara_light_first` and selects their `_only` identities.
These database IDs **omit the initial e** although the file/name IDs use eflame/elight.
Resolve hashes from ui_chara_db and ParamLabels instead of equating their spelling.
No player-number-specific texture filenames appear in this measured path.

`32648c0` formats `c%02d_index`; `3280910` finds ui_layout_db by ui_chara_id and
the resulting chara_color. Changing cNN_index without adding an appropriate
layout row risks a failed lookup. This is separate from costume artwork suffix
and the `nNN_index` used for names. The old naming package deliberately kept
layout routing at 0; that alone does not tailor Aegis's paired portrait placement
to a G&W canvas.

Loading presentation 0.1.0 creates **four** layout rows for flame-first/only,
colors 6/7, copying each recipient's current color-0 values except the measured
24 `chara_3_*` and 33 `eye_{0,1,2}_*` fields copied from the G&W donor row.
It retains CSS fields, chara_0/1/5/7 fields, spirit eye-info offsets and flags;
vanilla layout rows are not altered. Only the four eflame c06/c07 routes change.
The two eflame-first BNTX replacements reuse the installed eflame-only themed
G&W artwork byte-for-byte, all mipmaps included. Mythra assets and routes remain
unchanged. Actual placement, eye-flash behavior and Training transition are
not established by the file/native inspection.

Union shared databases with `package.py apply` after the final collective build
and other UI tasks; never copy stale whole databases from the task delta.
The tool rejects occupied incompatible layout routes/rows and owned portrait
conflicts. Offline concurrent name/CSS preservation and conflict controls passed.
Canonical package/test instructions: `src/pgwr/tools/loading_presentation/README.md`.
