# 0.10.0 console test

Build: `0.10.0` — the moves now actually drive G&W's `normal_weapon` article.

Card is now on **0.10.0** (installed 2026-09-29 16:05; see the addendum below for
why the previous run was not a valid test).

## RESULT 2026-09-29 16:14 — boot clean, article registered, CRASH at fight start

**The registration works.** This is the hard part of the design and it is proven:

```
[MGW-SL] p7: verified resource globals, name tables and path hooks
[PGWR-ART] registered gamewatch article 125 (normal_weapon) on eflame as local article 0; use_original_code=false
[PGWR] Pyra G&W reskin plugin v0.10.0 ... loaded
[PGWR] gated fighter=eflame costumes=[6, 7]
[PGWR] NOT registered: elight (Mythra), gamewatch (real G&W)
[NRO hook] Loaded eflame. BindFlag: Lazy
```

No `REFUSED` anywhere, the 13.0.4 version guard passed, and `pgwr_article::register()`
fired before every `install_*`. The game then crashed starting the fight.

**Fault:** `sd:/atmosphere/crash_reports/01790691291_01006a800016e000.log`

```
Type:            Data Abort
Address:         0x20      Fault Address: 0x0
Thread:          TaskWorker2
ReturnAddress[04]: smashline + 0x25cc4 (fighter_initialize_object_data + 0x2c)
ReturnAddress[03]: cross2_Release.nss + 0x607e3c
ReturnAddress[02]: cross2_Release.nss + 0x17eecb8
ReturnAddress[01]: cross2_Release.nss + 0x17eeff8
ReturnAddress[00]: cross2_Release.nss + 0x17ddf64
```

A null read, in *game* code, on the path out of `fighter_initialize_object_data`
(the `get_static_fighter_data` hook's caller). It is not a Rust panic: there is no
`Failed to append article table`, so the donor does have a descriptor for weapon
125 and the append succeeded. And smashline's own `get_static_fighter_data`
null-checks every pointer it dereferences, so it is not faulting inside itself.

**Cause: `new-dir-infos-base` was empty.** Boot printed, twice, and only for this
mod:

```
[arcropolis::replacement::addition] Cannot get file info range for 'Unknown' (0x1e7b508bbb)
[arcropolis::replacement::addition] Cannot get file info range for 'Unknown' (0x1e0c57bb2d)
```

That message occurs **zero** times in all six archived runs of the working clone
pack (`mod_files/mgw_standalone/latest_logs/*.txt`), so it is a fault of this
config. The pointers are outside the range healthy runs use (`0x31..`-`0x36..`),
i.e. `DirInfo`s that were never created. ARCropolis derived the base directory
itself, which is unreliable for a path whose parent (`fighter/eflame/model/
normal_weapon/`) does not exist in the base game at all; two of the four
directories got garbage and the game's model load for the new article then
dereferenced NULL.

**Note:** the other suspicious boot line,
`File discovery collected path '.../config.json' but it does not exist and/or is
invalid!`, is **benign** — it appears in the good probe runs too. Do not chase it.

### Fix shipped 2026-09-29 16:20

`build.py`'s `build_config_json()` now fills `new-dir-infos-base`, mapping each
new directory to the same slot of the donor fighter (verified present in the
export, 16/12/16/12 files):

```json
"new-dir-infos-base": {
  "fighter/eflame/model/normal_weapon/c06": "fighter/gamewatch/model/normal_weapon/c06",
  "fighter/eflame/motion/normal_weapon/c06": "fighter/gamewatch/motion/normal_weapon/c06",
  "fighter/eflame/model/normal_weapon/c07": "fighter/gamewatch/model/normal_weapon/c07",
  "fighter/eflame/motion/normal_weapon/c07": "fighter/gamewatch/motion/normal_weapon/c07"
}
```

Only `config.json` changed (one file, copied and `diff`-verified against the
build). Both NROs are untouched: reskin `a8465ff8…`, smashline `b906669d…`.
Nothing else on the card was modified.

## ADDENDUM 2026-09-29 16:05 — the earlier "no props" result was INVALID

The test that reported "there is no hole, and none of the other moves were
visible" **did not run 0.10.0 or 0.9.0 at all.** It ran 0.8.x-era assets against
an unpatched smashline plugin. It must not be recorded as a code failure.

Proven by three independent checks against the card, before any install:

| check | on card | required for 0.10.0 |
| --- | --- | --- |
| `libpyra_gamewatch_reskin.nro` | `ed2988e1…` | `a8465ff8…` |
| `libsmashline_plugin.nro` | `5f4091ee…` | `b906669d…` |
| `grep -c PGWR-ART` in the card's smashline | **0** | 2 |
| mod folder | 737 files, `"new-dir-infos": []` | 793 files, 4 dirs |
| `normal_weapon` dirs on card | **0** | 4 |

The zero `PGWR-ART` hits are the decisive one: `pgwr_article::register()` — the
only call that registers article 125 on eflame — had never been on the card. And
`new-dir-infos` was empty with no `normal_weapon` directory, so the prop meshes
were absent even had an article existed. "None of the other moves were visible" is
the necessary consequence of those two omissions, not a bug.

**The manhole hole is exempt from this retraction and remains an open bug.** The
hole (`manhole1M` frames 0–4, `manhole2M` frames 5–44 in `c02attacklw3`) is a
*body* mesh, not article geometry. It needs neither the registration nor the
`normal_weapon` directories, and the body clips that *were* on the card drive it.
So that observation was valid and still needs chasing.

## Install now on the card (done by the assistant, 2026-09-29 16:05)

Backup of the previous state: `mod_files/pyra_gamewatch_reskin/sd-backup-20260929-160422/`
(`plugins/` = the two old NROs, `card-mod-folder.tar` = the 737-file mod folder, 752 entries).
To roll back, restore those two NROs and untar over `/f/ultimate/mods/`.

Post-install verification, all green:

- reskin NRO on card = `a8465ff83b72d08d552f3169b51cc0d1e2b8184173b0886ac2ceedf278bce850`
- smashline NRO on card = `b906669d4754bbf04f3d419bbd06f83a7b3ff1e0e505d0ac76c1531b74af7230`
- `grep -c PGWR-ART` in the card's smashline = **2**
- `diff -r` build vs card mod folder = **identical**, 793 files
- card `config.json` `new-dir-infos` = all four `normal_weapon/c06,c07` dirs
- card `info.toml` version = `0.10.0`

The card copy of the mod folder was staged as `pyra_gamewatch_reskin.new` and only
swapped in after the 793-file count and the four per-dir counts (16/12/16/12) were
confirmed, so the card was never left half-written.

## What changed since the last build you tested

**Three** things, all of which matter:

1. **The moves spawn the article.** Every move that holds a prop now calls it
   again, straight from G&W's own scripts:

   | move | what you should see |
   | --- | --- |
   | **forward tilt** | the **stool** |
   | **jab**, and the rapid chain | the **spray** |
   | **down tilt** | the **manhole cover** |
   | **neutral air** | the **fishbowl** |
   | **back air** | the **turtle** |
   | **down taunt** | the **spray** |

2. `libpyra_gamewatch_reskin.nro` — changed, now `a8465ff8…`
3. `libsmashline_plugin.nro` — changed, now `b906669d…`. It registers the article
   on Pyra at startup. Nothing was added except that one call.

## Set expectations before you start

This is a real test, and the honest expectation is **props that appear but may
not behave**.

The article now exists and the right clip plays. But it has **no behaviour of its
own yet** — no code that tells it to follow his hand, hold still, or carry a
hitbox. That code lives inside G&W's game files and copying it is the next piece
of work, not this one.

So: the stool may well appear, and may be a stool sitting in mid-air rather than
in his hand. That is a **success**, not a bug. What would be a failure is the game
not booting, or the log lines below not appearing.

## Install — these three, nothing else

1. `mod_output/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libpyra_gamewatch_reskin.nro`
2. `mod_files/mgw_standalone/target-smashline/aarch64-skyline-switch/release/libsmashline_plugin.nro`
   → `sd:/atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libsmashline_plugin.nro`

   **Overwrite the old one.** This is deliberate and was agreed. Do **not** grab a
   fresh smashline from the internet instead — current releases only support
   13.0.5 and up, and this card is on 13.0.4. The build you want is the one from
   this repo.
3. **Replace the whole** `mod_output/pyra_gamewatch_reskin/ultimate/mods/pyra_gamewatch_reskin/`
   folder. It is not an overlay any more: it now contains `config.json` and four
   new directories that 0.7.0's copy does not have. `build.py` deletes and
   rewrites the package, so diff it against what is on the card first.

Leave `libarcropolis.nro`, `libarc_network.nro` and `libnro_hook.nro` alone.

Verify before booting:

```bash
sha256sum mod_output/atmosphere/.../libpyra_gamewatch_reskin.nro
# expect a8465ff83b72d08d552f3169b51cc0d1e2b8184173b0886ac2ceedf278bce850
sha256sum mod_files/mgw_standalone/target-smashline/.../libsmashline_plugin.nro
# expect b906669d4754bbf04f3d419bbd06f83a7b3ff1e0e505d0ac76c1531b74af7230
find mod_output/pyra_gamewatch_reskin -type f | wc -l
# expect 793
```

## The test

In training mode, with the full Skyline log from startup.

| # | do this | expect |
| - | ------- | ------ |
| 0 | Just boot, read the startup log | the two lines quoted below |
| 1 | Pyra **c06**, Judge (side-B) on the ground, once | see the `FILEADD` line below |
| 2 | Pyra **c07**, same | same, second `entry=` value |
| 3 | Pyra **c00**–**c05**, side-B | Pyra's Rethunder Toss, **no** `[PGWR] JUDGE` or `FILEADD` line |
| 4 | Mythra, and Mythra↔Pyra down-B both ways | vanilla Mythra, the swap transforms as before |
| 5 | Real **Game & Watch** | completely vanilla, props and all |
| 6 | Judge three times in a row | no duplicate or stuck state |
| 7 | **Forward tilt** on c06 | the **stool** — tell me if it appears, and whether it's in his hand or floating |
| 8 | **Jab**, then the rapid chain | the **spray** |
| 9 | **Neutral air** and **back air** | the **fishbowl** / the **turtle** |
| 10 | **Down tilt** | the **manhole cover** — and the hole in the ground? |
| 11 | **Down taunt** | the **spray** |
| 12 | Look at the **down tilt** on c06/c07 | see the question below |

### The startup lines that matter

```
[MGW-SL] p7: verified resource globals, name tables and path hooks
[PGWR-ART] registered gamewatch article 125 (normal_weapon) on eflame as local article 0; use_original_code=false
```

- `[MGW-SL] REFUSED` anywhere → the plugin decided the game is not the build it
  was made for and installed **nothing**. Send the whole log; nothing else in this
  test will be meaningful.
- `[PGWR-ART] REFUSED` instead of the second line → the fighter names weren't
  found, so nothing registered. Send the log.
- Both lines good → the registration worked. **Send the log regardless**, because
  "registered" plus no prop on screen is itself a result we need.

### The line each prop move should print

```
[PGWR] ARTICLE spawn: entry 0 motion attack_s3 prop 1 id 125
```

One of these per move, naming the clip the article was told to play. `prop` is
which one was asked for — 0 spray, 1 stool, 2 manhole, 3 fishbowl, 4 turtle.
Those motion names can be read straight against the article's own
`motion_list.bin`; all of them are in it.

- Seeing the line **but no prop** means the article was asked for and did not show
  — the most likely place for a problem, and worth saying so plainly.
- **No line at all** means the move didn't reach that point, which is a different
  and more basic problem.
- A line with a motion name not in the list (e.g. anything invented) would mean
  the clip name is wrong; all six of ours are in it, so that should not happen.

### The Judge line that matters

```
[PGWR] FILEADD entry=0 requested=special_s_1_l control_end_frame=60.00 new_file_end_frame=51.00 frame=0.00 motion_kind=0x… -> NEW FILE LOADED
```

- **Pass** — ends `-> NEW FILE LOADED`, and `new_file_end_frame` is 51 while
  `control_end_frame` is 60 or 59. The two cannot be confused.
- **Fail** — ends `-> NEW FILE DID NOT LOAD`, or the two numbers are equal, or
  there is no `[PGWR] FILEADD` line at all.

Report both lines verbatim, including the numbers.

### Question 7 — the down tilt

Please describe what you actually see, in one sentence:

- **a hole in the ground with nothing in his hands** — this is the expected and
  correct result. The hole is a body mesh and is already animating; only the
  *cover* he swings is missing, and that is the article.
- **nothing manhole-related at all** — that contradicts the clip data, and it
  means something cheaper is broken, which is much better news. Say so.
- **a manhole cover with no hole** — also useful, and also different from either
  of the above.

## What would make this run invalid

If the game fails to boot, send the Atmosphere report as well as the Skyline log.
A boot failure here would most likely mean the `new-dir-infos` declarations are
wrong, or that the new smashline build refused its version check. Both are clean,
early signals rather than mysteries.

If Pyra c00–c05, Mythra or real G&W look wrong, that is the one result that would
make me stop and undo the smashline change, so please say so plainly if you see
it.
