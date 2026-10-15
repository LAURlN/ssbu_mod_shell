# 0.8.0 — the file-addition experiment (built, not yet run)

**One question:** can a mod add a file whose name the base game does not have, and have
a motion entry that names it actually play?

Nothing else in this build changed. It is a deliberate, isolated experiment, and it is
the gate on `normal_weapon` (the fishbowl, the stool, the manhole, the spray) because a
cloned article needs model and motion folders under `eflame` that eflame has never had.

## Why this needs an experiment at all

`HANDOFF.md` (repo root, Monkey Flip) is the only console evidence, and it says newly
added animation names never load:

> the twelve slots in `motion_list.bin` were mapped to animation file names that exist
> in **no** base Game & Watch folder ... The engine parses the entry, then fails to load
> that clip, and leaves the previously loaded clip playing.

That is the trap this mod has been dodging since 0.7.0, where the 20 G&W clips eflame
lacks are stored under spare eflame names (`build_motion`'s ALIAS notes). But the Monkey
Flip mod shipped new clip names with **no `config.json`** at all, so it never exercised
ARCropolis' own file-addition route. That route is the one the handoff's "How to do it
properly", step 1 asks to be tested first, and it had never been tested.

## The route, read out of ARCropolis' source rather than from memory

The installed `libarcropolis.nro` (F:, 2347008 bytes, 2025-06-25) still parses the
legacy per-mod `config.json`; the strings `new-dir-infos`, `new-dir-infos-base`,
`new-dir-files`, `share-to-vanilla` and `share-to-added` are all in the binary, and so is
`is_handler_consumed`'s extension list, which only exists inside the file-addition loop
of `process_mods`. So the route is available on the card.

From `Raytwo/ARCropolis` `src/fs.rs` (`process_mods`), in order:

1. `add_dir_info` for every `new-dir-infos` entry, and `add_dir_info_with_base` for every
   `new-dir-infos-base` pair. These create directories the base game does not have.
2. For every mod file whose game path is absent from `data.arc`: `add_file` (registers
   the file in the arc) and `add_searchable_file_recursive` (registers the file's *name*
   in the arc's search tree, creating parent folders as needed).
3. `unshare_files` for the hashes the mod owns.
4. `add_files_to_directory(context, dir_hash, file_hashes)` for every `new-dir-files`
   entry — this adds the listed file hashes to that directory's file table.

`src/replacement/addition.rs` shows `add_files_to_directory` rebuilds the directory's
`DirInfo` from the existing entries plus the new ones, so it works on a directory that
already exists. That is all this experiment needs, so `new-dir-infos` is empty here: the
probe file goes into `fighter/eflame/motion/body/c06`, which the base game has.

The clone packs in `sd_backups/2026-09-29_before_pyra_gw_reskin/` use exactly these five
keys and were written against a working ARCropolis, so the key names and shape here are
copied from them.

## What changed

### Assets — `build.py`

One clip leaves the alias rule:

* `d01specialsl.nuanmb` (G&W's `special_s_1_l`, Judge's held pose) is written under its
  **own G&W name** into `fighter/eflame/motion/body/c06` and `c07`. That name exists in no
  eflame folder in the base game, so it is a genuine new file. The build asserts it
  (`referenced - new_files <= pyra_names`, so no *other* new name can creep in; a
  byte-exact-copy assert; and a "the build introduced exactly this and config.json
  declares exactly this" check).
* The file is **verbatim G&W data** — SHA-256
  `e5690eabc16431a4ac88c8e8f54843c902fc034fe6fd04d990cc51d40245c63d` in both slots — and
  is excluded from `complete_visibility`, per the guide's rule that the pass is for clips
  written under Pyra's names and is itself a workaround.
* `special_s_1_l`'s motion entry now names that file. It is G&W's own entry, copied
  whole, so its flags, blend and cancel frame are unchanged from 0.7.0.
* `clips_aliased` goes 20 → 19, `clips_identity` 302 → 303. Nothing else moved.

`mod_output/.../pyra_gamewatch_reskin/config.json` (new, SHA-256
`b0830e07b0a635cdbb76876460104d1b404a59bb74c99f941df115721722510b`):

```json
{
  "new-dir-infos": [],
  "new-dir-infos-base": {},
  "new-dir-files": {
    "fighter/eflame/motion/body/c06": ["fighter/eflame/motion/body/c06/d01specialsl.nuanmb"],
    "fighter/eflame/motion/body/c07": ["fighter/eflame/motion/body/c07/d01specialsl.nuanmb"]
  },
  "share-to-vanilla": {},
  "share-to-added": {}
}
```

### Plugin — `judge.rs`

`special_s_1_l` was already played by the Judge status on ground side-B, so the probe
costs no new status id and no new button. `judge_pre` records the control reading
(`MotionModule::end_frame` of whatever is playing, i.e. the idle) and then requests
`special_s_1_l`; the first executable frame logs the comparison and runs the real reveal
from frame 3. Judge's own shape is unchanged from frame 3 on.

The measurement follows the guide's traps: `MotionModule::motion_kind` is printed but is
**not** the evidence (trap 2 — it echoes the request); `end_frame` is the evidence (trap
3). G&W's idle is 60 frames (`a00wait1`, or 59 for `a00wait2`) and `d01specialsl.nuanmb`
is 51, so the two readings cannot be confused. The log line prints its own verdict and
hard-codes no expected value, so it cannot be wrong by construction.

Because the probe clip is verbatim, the four meshes G&W's own visibility groups never
touch (`LHammerM`, `RHammerM`, `flagman1M_FLIP`, `flagman2M_FLIP` — the hammer and the
"1"/"2" sign-holding G&W) have no track in it. **Seeing the signs flash for the probe's
three frames is expected, and is further evidence that the new file was read.** This is
the handoff item-8 workaround showing through on purpose, not a regression.

## Install (only both of these; nothing else on the card changes)

1. `mod_output/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpyra_gamewatch_reskin.nro`
   → `sd:/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/`
   — 151552 bytes, SHA-256 `ed2988e148d2e6ec52f213202b53c0cb0aeb5ae92277f08985006bbf4b4d4378`
   (on the card now: `4d74191056230bdb0d7693d32f72b2177c3338096b749c5ead72320e8e60576b`)
2. `mod_output/pyra_gamewatch_reskin/ultimate/mods/pyra_gamewatch_reskin/` →
   `sd:/ultimate/mods/pyra_gamewatch_reskin/` — 737 files (the card has 736).
   **`config.json` is a new file and must be copied.** The folder is rebuilt from scratch
   each build, so replace it rather than merging.

Do not replace `libarcropolis.nro`, `libarc_network.nro`, `libnro_hook.nro` or
`libsmashline_plugin.nro`. Rollback: `sd_backups/2026-09-29_before_pgwr_0.7.0/`.

## The test

The log is the answer; the picture is a second, independent answer.

1. Boot, enter a match as **Pyra c06**. Confirm one line:
   `[PGWR] Pyra G&W reskin plugin v0.8.0 (...) loaded`
2. **Stand still, then press side-B once.** Watch the first three frames.
3. Repeat on **c07**.
4. **Vanilla Pyra c00–c05**: press side-B on each. Expect the stock Rethunder Toss, and
   **no** `[PGWR]` line for those entries — the costume gate is the negative control.
5. **Mythra**: press side-B. Expect the stock spin, no `[PGWR]` line.
6. **Real G&W**: press side-B. Expect the stock Judge with the number card, no `[PGWR]`
   line.
7. Re-check that c06 still walks, jabs and does every aerial normally (0.7.0's result
   must not regress).

### Expected log, filtered on `[PGWR]`

For each of c06 and c07:

```
[PGWR] JUDGE enter: status 0x1ee entry 0 colour 6 control_end_frame 60.00 probe special_s_1_l for 3 frames, then reveal special_s_1
[PGWR] FILEADD entry=0 requested=special_s_1_l control_end_frame=60.00 new_file_end_frame=51.00 frame=0.00 motion_kind=0xd1b8e3ff8 -> NEW FILE LOADED
[PGWR] JUDGE reveal: entry 0 at frame 3
[PGWR] JUDGE hold: entry 0 at frame 16
[PGWR] JUDGE end: entry 0 at frame 46
```

`colour 6` / `colour 7` is c06 / c07. `control_end_frame` is **60.00 or 59.00** (the idle
shuffles between G&W's `a00wait1` and `a00wait2`) — both correct, both different from 51.

### How to read it

| `[PGWR] FILEADD ...` | meaning |
| --- | --- |
| `new_file_end_frame=51.00 ... -> NEW FILE LOADED` | **Pass.** ARCropolis' `new-dir-files` route works. Step 2 (the `normal_weapon` clone and its new model/motion folders) is unblocked. |
| `new_file_end_frame=60.00 ... -> NEW FILE DID NOT LOAD` (or 59.00, or equal to the control) | **Fail.** The engine still cannot see the file. Stop here and hand back — do not squeeze the article's assets into an unrelated folder, as the handoff says. |
| no `FILEADD` line at all, but a `JUDGE enter` line | the status ran but the probe never reached its first executable frame — a plugin bug, not a file-addition result. Report both lines. |
| no `[PGWR]` line at all on c06/c07 | the gate or the NRO is not live. Check step 1 of the install and the version banner. |
| a `FILEADD` line on c00–c05, Mythra or real G&W | **the gate has failed. Stop and report** — that is a regression, not a test result. |

### What to look for on screen

* **Pass:** on pressing side-B the pose snaps from standing into Judge's held pose for
  about three frames — the arm out, and (expected) the "1"/"2" signs flashing with it —
  then the normal reveal → hold → end sequence follows, unchanged from 0.7.0.
* **Fail:** the pose never changes. Judge's reveal runs from the first frame and the
  held pose never arrives, which is the Monkey Flip signature exactly.

## What this does *not* settle

Only the **new file in an existing directory** case. The article folders
(`fighter/eflame/model/normal_weapon/c06`, `.../motion/normal_weapon/c06`) are
**directories the base game does not have at all**, so they need `new-dir-infos` as well.
They are deliberately *not* declared here: nothing loads them until step 2, and a
mis-declared empty directory tree would cost a boot cycle without answering anything.
They get their own test at step 2, where they have a consumer.

## If it passes

Steps 2–5 of the handoff's "How to do it properly" unblock, in order: clone
`normal_weapon` as eflame's own with `use_original_code = false`, port its statuses out of
`lua2cpp_gamewatch.nro`, then replace R1/R6/R21's `NORMAL_WEAPON` drops in the generator
with a real translation, then the down-attack hammers (`rhand_hammer`).
