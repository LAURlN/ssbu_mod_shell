# T-0033 - Finding 2: simultaneous c06/c07 Cloud sword trails - collision and ownership inventory

Owner: task T-0033 (research child of T-0035). Date: 2026-10-01. Evidence tier **B** for every byte
and source claim; the failure explanation is **tier D (hypothesis)** and the matrix at the end is
the experiment that would settle it. No emulator, no console, no automated test was run.

## Symptom

The user reports: Ursula (Pyra c06) loses the **jab and fair sword trails only when Wilhelmine
(Pyra c07) is also present**. Both moves request the same two texture names, so one shared
resource pair is the whole of the reported surface.

## What the code actually does (tier B, source read)

| step | file:line | fact |
|---|---|---|
| request | `plugin/src/acmd/chrom_jab.rs:266-292` (jab, on at frame 3, `AFTER_IMAGE_OFF(2)` at 8) and `plugin/src/acmd/attack_air_f.rs:215-241` (fair, on at 16, off at 26) | both call `AFTER_IMAGE4_ON_arg29(tex_cloud_sword1, tex_cloud_sword2, 10, "sword1", 0,0,-0.08, "sword1", TIP, 0,-0.08, true, "null", "sword1", ..., *TRAIL_BLEND_ALPHA, 101, *TRAIL_CULL_NONE, 1.4, 0.1)` - one script, one name pair, both slots |
| generation | `src/pgwr/tools/build_cloud_trail.py:92-119` | `tex_cloud_sword1` is decoded, recoloured per slot, re-encoded, then **`new_data[-108:-44] = raw[-108:-44]` copies the donor's resource-name block verbatim**; only `[-44:-20]` is asserted equal (format/mips/dimensions). `tex_cloud_sword2` is `shutil.copy2` of the donor - identical bytes in both slots |
| deployment | `src/pgwr/tools/build_color_themes.py:469-499` | writes `effect/fighter/eflame/trail_c06/` and `trail_c07/`, each with `tex_cloud_sword1/2`, a `tex_eflame_cloud_sword1/2` byte-copy alias, and Mythra's `tex_elight_sword1..5` plus `tex_eflame_sword1..5` aliases - 14 NUTEXB per slot |
| declaration | `src/pgwr/build.py:1327-1331` | the 14 files of each slot folder are declared under `fighter/eflame/c06` and `fighter/eflame/c07` (verified in `builds/pgwr/0.20.16/.../config.json`) |
| routing | `src/pgwr/tools/one_slot_effects_reference.rs` (pinned upstream source of the shipped `libone_slot_eff.nro`) | `get_trail_folder_hash` (main+0x355f1f4) redirects the searched folder to `effect/fighter/<fighter>/trail_c<slot>`; `get_raw_nutexb_data` (main+0x355ff00) rewrites each loaded NUTEXB footer name `NAME` -> `NAME_C<slot>` and records `hash40(name) -> hash40(name_c<slot>)` per slot; `make_after_image` (main+0x3562450) rewrites the two requested hashes before the trail is built |

So the per-slot differentiation is done by the plugin's rename, keyed on the **internal NUTEXB
resource name**, not on the file name and not on anything the mod controls at runtime.

## Collision / ownership inventory (tier B, measured with `tools/effect_trail_inventory.py`)

Full per-file listing: `T-0033/trail_inventory.json`. Each eflame slot folder holds **14 files but
only 7 distinct internal names**; every name appears exactly twice.

| internal name | files in each slot folder | requestable? (`dumps/scripts/ParamLabels.csv`) | c06 vs c07 bytes |
|---|---|---|---|
| `TEX_CLOUD_SWORD1` | `tex_cloud_sword1.nutexb`, `tex_eflame_cloud_sword1.nutexb` | yes (`tex_cloud_sword1` = 0x10dd44e2a9) | **different** (the intended recolour) |
| `TEX_CLOUD_SWORD2` | `tex_cloud_sword2.nutexb`, `tex_eflame_cloud_sword2.nutexb` | yes (0x10444db313) | **identical** (verbatim donor copy) |
| `TEX_ELIGHT_SWORD1` | `tex_elight_sword1.nutexb`, `tex_eflame_sword1.nutexb` | yes (0x11bb204d6a / 0x11d7d80df4) | different |
| `TEX_ELIGHT_SWORD2` | `tex_elight_sword2.nutexb`, `tex_eflame_sword2.nutexb` | yes | **identical** |
| `TEX_ELIGHT_SWORD3` | `tex_elight_sword3.nutexb`, `tex_eflame_sword3.nutexb` | yes | different |
| `TEX_ELIGHT_SWORD4` | `tex_elight_sword4.nutexb`, `tex_eflame_sword4.nutexb` | yes | different |
| `TEX_ELIGHT_SWORD5` | `tex_elight_sword5.nutexb`, `tex_eflame_sword5.nutexb` | yes | **identical** |

Ownership facts that follow:

1. **Cross-slot shared identifier**: `TEX_CLOUD_SWORD1` is the internal name in *both* slots'
   folders. That is by design - the plugin's rename is the only thing that separates them - and
   the rename key is `(original name, slot)`, so the mapping table itself is per-slot and cannot
   collide (source read, lines 384-418 and 139-151).
2. **Within-slot duplicate**: two files in the same folder carry the same internal name, so after
   the rename they are two registrations of the *same* resource name `NAME_C<slot>`. This exists
   in c06 and c07 identically.
3. **Dead files**: `tex_eflame_cloud_sword1/2.nutexb` and `tex_eflame_sword4/5.nutexb` have **no
   matching engine label** (`tex_eflame_sword1..3` exist, `4`/`5` do not; no
   `tex_eflame_cloud_*` exists), so under an internal-name lookup nothing can ever request them.
   Under a file-name lookup they are exact byte duplicates of a file that *is* requestable.
   Either way they double a registration and change nothing.
4. **Name/file mismatch**: `tex_eflame_sword1.nutexb` carries `TEX_ELIGHT_SWORD1`. Vanilla's
   invariant is file name == internal name. The mod breaks it deliberately, to satisfy both lookup
   conventions at once, at the cost of point 2.
5. **Elight is the same shape**: `effect/fighter/elight/trail_c06|c07` hold 8 files,
   `TEX_ELIGHT_SWORD1..5` + `TEX_BRAVE_SWORD1/2` + `TEX_BRAVE_LIGHTNINGSWORD1`, of which
   `tex_elight_sword2/5` and all three brave ones are **byte-identical across the two slots**.
   Mythra's trails are reported working, which is evidence that a shared internal name across
   slots is *not by itself* fatal - important negative control for hypothesis H1.

## Ranked hypotheses (tier D - none of these is settled)

**H0 (baseline, must be excluded first): the request is not being rewritten at all.**
`make_after_image`/`get_new_effect_name` only substitute when the name is in
`FIGHTER_EFFECT_NAMES[fighter kind]`, and that set is filled in `get_raw_nutexb_data` with the
*pre-rename* name for the kind recorded in `EFF_FIGHTER_KIND`. Note `one_slot_cleanup`
(main+0x60bfbc) clears `EFF_FIGHTER_NAME`, `EFF_FIGHTER_SLOT` and `EFF_FIGHTER_TRAIL_SLOT` but
**not `EFF_FIGHTER_KIND`**, so a load that happens outside a fighter lookup registers trail names
against a stale kind. If that happens, `is_effect_for_fighter(eflame, tex_cloud_sword1)` is false,
no substitution occurs, and the game looks for `tex_cloud_sword1` in a folder it never enters.
*Distinguishing observation:* the trail works with c06 alone but not with c07 - i.e. the mapping
for one slot is missing while the other exists. *Settles it:* the matrix rows 3-6 below.

**H1 (name collision in the loaded-resource table).** Both slots register the same internal name;
after the rename they are distinct, but if the *duplicate pair inside one slot* is what the
resource table collapses (first wins, later registration ignored or freed), the surviving
registration depends on file iteration order, and adding a second slot changes that order.
*Distinguishing observation:* removing the alias duplicates makes the problem disappear with no
other change. *Experiment:* the fix below, shipped as a single change.

**H2 (load order / per-slot handle).** `SlotCache` caches "does trail_c<slot> exist" at first
query and never invalidates it (`SlotCache::create_cache_entry`, lines 36-67). If the first query
happens before ARCropolis has discovered that slot's folder, the slot is cached as absent forever
and the plugin falls back to the vanilla `trail/` folder for it - the trail is then missing, and
which slot misses depends on which player loaded first. *Distinguishing observation:* the
*second* player to load is the one that loses the trail, and swapping P1/P2 swaps which slot
loses it. *Settles it:* matrix rows 4-6 (order sweep).

**H3 (shared effect cleanup / cross-kind).** Pyra and Mythra are different kinds, but the esword
article is Mythra-derived and Pyra's sword is attached from it; `unload_effects`/handle offsets are
per kind and slot (`tmp`, lines 510-549). A Mythra player in the match may therefore clear or
rebind an eflame trail resource. *Distinguishing observation:* the symptom depends on who else is
in the match, not only on which slot. *Settles it:* add Mythra c06/c07 as a third player to rows
1-2.

**H4 (the slot's recolour is a no-op).** `tex_cloud_sword2` is a byte copy of the donor in both
slots and `tex_cloud_sword1` is the only recoloured file, so if the engine ever asks for sword2
where slot-specific colour matters, c06 and c07 are *supposed* to look the same there. This is a
cosmetic gap, not the reported "trail disappears", but it will look like one if only one of the
two ribbon textures resolves. *Settles it:* the same matrix; if the ribbon shows as a single
untextured streak, this is it.

## Smallest owned-resource fix

**One file per internal resource name per slot folder.** Concretely, in
`src/pgwr/tools/build_color_themes.py:469-499`:

* drop the `tex_eflame_cloud_sword1/2.nutexb` byte-copy aliases (lines 496-498),
* drop `tex_eflame_sword1..5.nutexb` (lines 485-487) and keep the `tex_elight_sword1..5` files, or
  keep the eflame-named trio **and** rewrite its footer name to `TEX_EFLAME_SWORD1..3` so that
  file name == internal name again. **This is the one judgement call for the implementer:** the
  eflame-named trio exists so a request for `tex_eflame_sword1..3` (the names the base
  `ef_eflame.eff` references) still finds a file. Recommended: keep the trio, fix its internal
  names, and delete `tex_eflame_sword4/5` (no such label exists). Then every folder holds exactly
  one file per name and file name == internal name, which is the vanilla invariant.

This keeps everything the report is not about untouched: **no ACMD change** (same
`tex_cloud_sword1`/`tex_cloud_sword2` request, same geometry `0,0,-0.08` / `sword1` / `TIP`,
same `TRAIL_BLEND_ALPHA`, `TRAIL_CULL_NONE`, axis X, rate 1.4 / 0.1, same frames), same article
attachment (`esword` visibility + `jab_to_open`/`to_open`), same timing, same plugin, same
`config.json` group structure. Only the *number of files that claim a name* changes: 14 -> 8 per
slot folder.

If H0 survives that change, the next owned step (not in this task) is a per-slot trail bank
(`effect/fighter/eflame/ef_eflame_c0N.eff`) so the trail is requested through a bank whose entry
names are already per-slot, exactly as Mythra does - that also removes the dependence on the
plugin's rename for eflame, and it is the same merge machinery as Finding 1.

## Manual matrix for the user (this is the experiment)

One character select, Pyra only, no other mods; in each row note whether the **ribbon** is visible
on the jab *and* the fair, and its colour. Row 1 is the vanilla negative control.

| # | P1 | P2 | expected if the mod is healthy | what it discriminates |
|---|---|---|---|---|
| 1 | Pyra c00 | - | vanilla Pyra trail (control; nothing themed) | proves the harness/observation is sound |
| 2 | Pyra c06 | - | black & pink ribbon on jab and fair | the reported working case |
| 3 | Pyra c07 | - | white & gold ribbon on jab and fair | the reported working case, other slot |
| 4 | Pyra c06 | Pyra c07 | **both** ribbons, each in its own colour | the bug; which slot fails first |
| 5 | Pyra c07 | Pyra c06 | both again | **load order** - if the failing slot changes with the order, H2 |
| 6 | Pyra c06 | Pyra c07 (redo after a rematch, same order) | both | one-shot vs persistent (mount/discovery timing, H2) |
| 7 | Pyra c06 | Mythra c06 | both Pyra ribbons + Mythra's | cross-kind effect cleanup, H3 |
| 8 | Pyra c06 | Mario | both | confirms it is c07 specifically, not "a second player" |
| 9 | Pyra c06 | Pyra c07, jab only (no fair) | both jabs | separates the shared request from per-move state |
| 10 | Pyra c06 | Pyra c07, after removing one alias pair from `trail_c07` only | both | single-change test of H1 |

Also record, for rows 4 and 5: which slot lost the trail, whether the ribbon appears as a
single-colour streak (H4), and whether the *sword blade* itself is present in both cases - a
missing ribbon with a correct blade is a texture/resource problem, a missing blade is an article
problem and belongs to a different task.

## Packaging files shared with Finding 1 (the two fixes must run sequentially)

Both fixes change the same generated outputs, so they cannot be built independently:

1. `src/pgwr/build.py` - `build_config_json()` declaration block (lines 1316-1339), the
   `littlemac_s4_eff.build(MOD)` call (1455) and the elight merge block (1456-1464). Its invariant
   `require(new_files == sorted(...declared...))` fails if either side changes alone.
2. `src/pgwr/tools/build_color_themes.py` - writes both trail folders and both banks, and copies
   `libone_slot_eff.nro` into the package (lines 515-519, with the assertions that the *shared*
   bank and folder are absent).
3. `src/pgwr/tools/build_cloud_trail.py` - the recolour and the footer patch both fixes depend on.
4. The generated `config.json` (`new-dir-files` for `fighter/eflame/c06` and `/c07`), the packaged
   tree, `MANIFEST.json`, `asset_build_record.json` and the baseline delta.
5. `dumps/arc/effect/fighter/eflame/ef_eflame.eff` - the *same* missing input Finding 1 needs; one
   console dump request covers both.
6. Housekeeping owned by whoever builds the combined release: `projects/pgwr/STATUS.md`,
   `CHANGELOG.md`, the project's section of `CURRENT_INSTALL.md` for the collective installer,
   and the shared effect-merging tool if Finding 1's merge is added.

## Unverified

Everything about runtime: which hypothesis fires, whether the ribbons differ per slot in a
1-player match, and the lookup convention (internal name vs file name) that H1/H0 rest on. No
emulator and no automated test was run in this task, by instruction.
