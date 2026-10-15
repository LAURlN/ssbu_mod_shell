# 0.8.1 — retract the hammer fix, and decode the visibility table

Status: **built, not yet run.** The card is still on 0.7.0.

0.8.1 was originally going to fix the down-attack / ground-getup hammer. **It does
not, because the hammer was never broken.** This release retracts that work and
keeps the two things it produced that turned out to be worth more than the fix:
a complete decode of `param_visibility_data_body`, and the finding that the real
NO SHORTCUTS gap is the **status scripts**, not the props.

**The plugin NRO is byte-identical to 0.8.0** (`ed2988e1…`). Nothing about game
behaviour changed in this release. 0.8.0's file-addition experiment is untouched.

## The retraction

0.8.1-draft added generator rule **R22** to `gen_acmd.py`, rewriting

```rust
VisibilityModule::set_int64(hash40("rhand"), hash40("rhand_hammer"))
```

into `ModelModule::set_mesh_visibility(.., "RHammerM", true)`, on the theory that
`rhand_hammer` is not a state in any visibility table and therefore the hammer
must be shown by native code.

The first half is true and still is. The second half is wrong.

**G&W's own clips turn the hammer on by themselves**, in exactly the three moves
that use it:

| clip | frames | value |
| --- | --- | --- |
| `f03downattacku.nuanmb` | 11 → 46 | `False ×11`, then `True ×36`, then `False` |
| `f04downattackd.nuanmb` | 11 → 46 | same |
| `g03slipattack.nuanmb` | 18 → 47 | `False ×18`, then `True ×30`, then `False` |

These three clip names are **not aliased**. They collide with Pyra's own
same-named files, so `build.py` overwrites them, and the built files are
byte-identical to G&W's export (`5ec0aad7`, `dad015b3`, `9ffd1b66`). The down
attack status resolves its motion by name and asks for precisely those names, so
the visibility track plays without any help from our code.

R22 has been removed from `gen_acmd.py`, and the donor's original dead
`set_int64` call is restored at all three sites. That call is genuinely a no-op
(`rhand` has one state, and it is the empty one) and it is genuinely harmless. It
stays because faithfulness to the donor is the policy, not because it does
anything. The `RULES` docstring now carries the retraction and the lesson so it
cannot be re-added by someone re-deriving the same wrong theory.

The `build.py` guard that existed only to protect R22 has gone too. In its place
the build now **records the whole visibility table with mesh names resolved**
(see below), which is the durable version of the same idea.

## The decode: mesh names are lowercased

This is the actual find. `param_visibility_data_body` stores each state's mesh
list as `hash40` of the **lowercase** mesh name, while the model stores the
mixed-case name. G&W's model has `AlarmM`; the table has
`hash40("alarmm") = 0x61917c347`. Group and *state* names are ordinary exact-case
`hash40` — `hash40("head") = 0x4a7f3f69c`, `hash40("lhand_alarm") = 0xb4d9cb5ed` —
so only the mesh lists are affected, and nothing in the file says so.

Proof rather than inference: brute-forcing every 4-character name over
`[A-Za-z0-9_]` against the ten 4-char hashes in G&W's table returns exactly
`no1m`, `no2m` … `no9m` and `keym` — the lowercased forms of the model's `No1M` …
`No9M` and `KeyM`. Before that key, 0 of 134 hashes resolved, which is why the
table looked like noise and `lhand_alarm` sat unidentified.

With it, **124 of 134 resolve**. The other 10 are all `0x7FB997A80`, the
"shows nothing" sentinel every group carries as its empty state.

### The decoded table

| group | states | what each state shows |
| --- | --- | --- |
| `head` | 6 | `HeadM`+`NoseM` · `HeadBM`+`NoseM2` · `sparky1M` · `DiverM` · `DiverFLIPM` · ∅ |
| `helmet` | 2 | ∅ · **`HelmetM`** — the dash-attack helmet, already working |
| `lhand` | 5 | ∅ · **`AlarmM`** · `BlockM` · `BucketM` · `KeyM` |
| `oil` | 4 | ∅ · `OilDM` · `+OilMM` · `+OilUM` (cumulative) |
| `rhand` | 1 | ∅ — **no `rhand_hammer` state exists, confirmed** |
| `zzz` | 13 | `Maru1M`–`3M` then `+LZzz1M`–`3M`, and the `R` mirror |
| `hand` | 6 | `LhandMove`/`LhandHold`/`LhandOpen` × `Rhand*` combinations |
| `panel` | 10 | `No1M` … `No9M` |
| `panel_flip` | 10 | `No1M_f` … `No9M_f` |
| `body` | 2 | 36 props: `Ball*`, `Vermin*`, `Oilpanic*`, `sheff*`, `judge*`, `fireattack*`, `flagman*`, `greenhouse*`, `lion*`, `manhole*` |

**`lhand_alarm` = `AlarmM`.** The ledge-getup alarm clock was never unidentified
— it is a body mesh, the state exists in G&W's table, and `build.py` already
merges it into the built eflame table (verified: `lhand_alarm` → `0x61917c347` →
`alarmm`, match true).

Note `body`'s state includes `manhole1M`/`manhole2M`, so the **down-tilt manhole
exists as a body mesh too** — worth checking before assuming it needs the article.

### Tooling

`tools/visibility_table.py` gained `mesh_names()` (lowerhash → name, from
`model.numshb`), `resolve_state_meshes()` and `summarise_groups()`. The build
record's `expression_vl.visibility_groups` now carries the whole table with names
resolved, so a future dump that changes it shows up as a reviewable diff instead
of a silent behaviour change on hardware.

`tools/untracked_meshes.py` is new: it lists which body meshes G&W's clip set
never turns on, and which names a clip tracks that the model does not contain.
It was written to classify props before writing code, and it is what disproved
R22. It must be run against the **original export**, not the built mod, because
`complete_visibility` writes tracks for all 98 meshes and would hide the set.

## The real gap: status scripts are still eflame's

This is the part that matters for NO SHORTCUTS, and it is a bigger hole than the
hammer ever was.

The plugin replaces **124 ACMD functions** (`game_`/`effect_`/`sound_`/
`expression_`) across 31 Pyra statuses. It does **not** replace any status-control
function. The down attack is the clean example:

```rust
unsafe extern "C" fn game_downattacku(agent: &mut L2CAgentBase) { ... }   // ported
```

contains no `change_motion` at all. The motion comes from eflame's own
`PreAttack`/`Main` for that status. The hammer animation works only because G&W's
clip and Pyra's clip happen to share a name, so eflame's status asking for
`f03downattacku` happens to load G&W's file. That is a **name collision doing the
work a port should be doing.**

**The donor data does not contain status scripts.** Across all 384 files in
`SSBU-Dumped-Scripts-main/smashline/lua2cpp_gamewatch/gamewatch`, the function
families are:

| family | count |
| --- | --- |
| `expression_*` | 352 |
| `sound_*` | 194 |
| `game_*` | 184 |
| `effect_*` | 103 |
| `PreMain` / `Main` / `Init` / `ExitStatus` / `PreAttack` / `cleanup` | **0** |

So `PreMain`, `Main`, `Init`, `InitAfterDeath`, `ExitStatus` and `cleanup` are
absent from that repository entirely. G&W's status logic lives in
`lua2cpp_gamewatch.nro` as native code, alongside the
`create_agent_status_script_gamewatch` registration that points at it.

**This also unblocks the article.** The workspace has a full, verified Smash
13.0.4 ExeFS dump (`Super Smash Bros. Ultimate 13.0.4 […][UPD]/Program #0/0/`,
with a rebuilt `pyra_mythra_clone/reference/dumps/images/main.bin`, 86,672,752
bytes, `main` text+rodata+data verified). Article agents are registered from
`main`, not from the per-fighter `lua2cpp_*.nro` files — which is why the earlier
conclusion that article code was unrecoverable was wrong. `normal_weapon` is
present in `main`.

## Build verification (offline, done)

* `build.py` — exit 0, **737 files**, second run byte-identical
  (`build-record.json` diffs clean; output tree hashes to
  `6e4dc956b7b85ec4e50dfe07499f0134dda7b1d1973dbd6af7c6bc1d4a052245`).
* `gen_acmd.py --check` — `common.rs`, `ground.rs`, `aerial.rs`, `rapid.rs`,
  `grab.rs` all up to date. R22 is absent from all four.
* `bash build-plugin.sh` — clean release build.
* **NRO**: `libpyra_gamewatch_reskin.nro`, 151552 bytes,
  `ed2988e148d2e6ec52f213202b53c0cb0aeb5ae92277f08985006bbf4b4d4378`
  — identical to 0.8.0, as a clean revert should be.
* Unchanged: `expression_vl.prc` sha `ee5d4ac2…`, `config.json` sha `b0830e07…`,
  the probe clip byte-exact copy, `clips_aliased` 20→19, `clips_identity` 302→303.

## Install

Nothing is installed. When you are ready:

1. `sd:/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpyra_gamewatch_reskin.nro`
2. `sd:/ultimate/mods/pyra_gamewatch_reskin/` — the whole directory from
   `mod_output/pyra_gamewatch_reskin/`, **including `config.json`**. The tree is
   not reproducible from 0.7.0 (it writes a `motion_list.bin` and new clips), so
   diff it rather than copying old files over the top.

Do not replace `libarcropolis.nro`, `libarc_network.nro`, `libnro_hook.nro` or
`libsmashline_plugin.nro`.

## Console test

The test is now **0.8.0's file-addition test only** — this release changed no
behaviour, so testing anything else would only add noise.

Side B, **Pyra costume 6**, side B once. Read the log for:

```
[PGWR] FILEADD entry=0 new_file_end_frame=… control_end_frame=… -> NEW FILE LOADED
```

* **Pass** — `-> NEW FILE LOADED`, and `new_file_end_frame` differs from the
  control (control reads 60.00 or 59.00; the new clip is 51 frames).
* **Fail** — `-> NOT LOADED`, the two numbers equal, or no `[PGWR] FILEADD` line.

`new-dir-infos` is **not** exercised by this release; it is empty on purpose and
is the next thing to test once `new-dir-files` is known to work.

Worth watching while you are in there, since it costs nothing extra: the
**down attack hammer** and the **ledge getup alarm clock**. The data says both
should already be present. If the hammer is there, the name-collision theory is
confirmed and the status port becomes the priority. If the alarm is missing, that
is new information about `lhand_alarm` reaching eflame at runtime.
