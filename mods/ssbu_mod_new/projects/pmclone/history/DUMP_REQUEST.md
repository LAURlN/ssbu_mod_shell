# Dump acquisition checkpoint — 2026-09-28

> **Resolved 2026-09-28 (later the same day).** The outage was not Arc Explorer: the
> `libarc_network.nro` Skyline plugin had been deleted from the SD plugins folder, so
> nothing listened on port 43022. It was restored from the official
> jam1garner/arc-network release. All 36 missing paths were then extracted (missing
> now 0), the six live-comparison files were exported and are byte-identical to the
> earlier exports, and the title screen shows **13.0.4**, matching the ExeFS dump
> label. The running process's build ID was not read. Evidence:
> `reports/live-verification-2026-09-28.json`. The text below is the original request.

The archive server at `192.168.2.166:43022` currently refuses connections, including
through Arc Explorer's `smash_arc.dll`. Arc Explorer has been closed. No SD writes
have been made. Local work can continue from the existing inputs, but the following
archive gaps remain.

## Files to export

Export the **36 exact archive paths** listed in
[`reports/dump-missing-paths.txt`](reports/dump-missing-paths.txt), preserving their
folder structure under:

```text
<workspace root>\export
```

For example, `sound/config/config.nus3conf` should become:

```text
dumps\arc\sound\config\config.nus3conf
```

These paths were absent when inventoried. There is no need to overwrite existing
exports. If bulk selection is easier, exporting their parent folders is also
usable, but preserve existing files or put that export in a separate folder and
tell the next contributor its location. This list includes reference inputs
whose exact role is still under investigation, not a claim that every file will
be modified or included in the installed clone.

## Fresh archive comparison

Export these six files separately, preserving their folder structure, under:

```text
<workspace root>\pyra_mythra_clone\reference\dumps\live-archive
```

```text
prebuilt:/nro/release/lua2cpp_eflame.nro
prebuilt:/nro/release/lua2cpp_elight.nro
prebuilt:/nro/release/lua2cpp_element.nro
prebuilt:/nro/release/lua2cpp_common.nro
ui/param/database/ui_chara_db.prc
fighter/common/param/fighter_param.prc
```

On disk use `prebuilt/nro/...` (without the colon). These fresh copies allow a
hash comparison with earlier exports without silently reusing them. Use Arc
Explorer's same US English region (region 2) as the earlier extraction when a
regional choice is needed. Other language variants are not yet validated.

Please also record the Smash version shown on the title screen. The existing
ExeFS dump is labeled **13.0.4**. We have verified its contents internally, but
have not independently read the running process's build ID. A different game
version requires a matching ExeFS dump before using the native address profile.

## Already available — do not redump unnecessarily

- All 9,234 previously prepared character resources remain available.
- `main`, `main.npdm`, `rtld`, `sdk`, `subsdk0` are now independently snapshotted
  under `reference/dumps/exefs`.
- All four NSOs' enabled segment hashes passed. Their decompressed images are
  under `reference/dumps/images`. `main.bin` exactly matches the existing native
  analysis image (SHA-256 `f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`).
- Existing selected module inputs and shared configuration files are snapshotted
  under `reference/dumps/archive` with hashes in `reports/dump-inventory.json`.

No full RAM dump or full game dump is requested at this point. Further specific
dependencies may be discovered during code and internal resource-reference analysis.

## Contributor commands

Run from the workspace root:

```powershell
python -m pip install --target pyra_mythra_clone/tools/python_deps -r pyra_mythra_clone/tools/requirements-dumps.txt
python pyra_mythra_clone/tools/inventory_dumps.py
```

The inventory validates ExeFS and selected shared/module snapshots. For the
previously prepared bulk assets, it records current presence/size and labels
the old source hashes as not freshly reverified. Use `--verify-assets` to rehash
those as well; this can take considerably longer on this filesystem.

If the archive server becomes available, the existing extractor can acquire the
same paths without console writes:

```powershell
python pyra_mythra_clone/tools/extract_missing.py --paths pyra_mythra_clone/reports/dump-missing.json
python pyra_mythra_clone/tools/extract_missing.py --paths pyra_mythra_clone/reports/dump-live-verification-paths.json --export pyra_mythra_clone/reference/dumps/live-archive
python pyra_mythra_clone/tools/inventory_dumps.py
```

The extractor skips existing files. Keep the fresh-comparison directory separate
from old exports. Reports include a pending flag until a contributor compares
fresh files and records the console version/build evidence. Do not infer dump
completeness from successful NSO decoding or the earlier loader test.
