# Handoff: the remaining article props, and the status-script gap

Written 2026-09-29 for a fresh instance. Everything below is **measured** unless
marked as reasoning. Where something failed, that is recorded too — several of
the dead ends here cost real time and should not be re-explored.

Read `README.md` and `REPORT_0.8.1_RETRACTION.md` first for the mod's own state.
This file covers what comes *after* them.

---

## 0. Where the hardware is right now

**Superseded 2026-09-29 16:18 — read this first.** The card is now on **0.10.0**,
installed and verified by `install-to-card.sh` (see `README.md` for the standing
install rule). The 0.8.x state described below is kept only as history. The
rollback snapshot for it is `sd_backups/2026-09-29_before_pgwr_0.8.1/`; the
current one is `mod_files/pyra_gamewatch_reskin/sd-backup-20260929-161810/`.

**Installing to the card is the agent's job** (user, 2026-09-29), and it stays
that way for whoever inherits this. Do not print copy instructions and stop. Run
`install-to-card.sh`, or `build-plugin.sh` with no arguments. `--stage-only` is
the only way to skip it. `build-plugin.sh` previously carried a header saying it
deliberately never touched the card; that is now inverted, and the old header was
the direct cause of a wasted test cycle (the card ran 0.8.x against an unpatched
smashline plugin, so all five props were absent and it read as a code bug).

What 0.10.0 established on hardware, for whoever picks this up:

- **The article registration works.** `[PGWR-ART] registered gamewatch article 125
  (normal_weapon) on eflame as local article 0; use_original_code=false`, with no
  `REFUSED`, on a 13.0.4 card. That was the hardest part of the design.
- **It then crashed starting the fight** — a null read (`Data Abort`, address
  `0x20`, fault `0x0`) on `TaskWorker2`, out of `fighter_initialize_object_data`.
  Cause: `new-dir-infos-base` was `{}` and ARCropolis's own base derivation is
  unreliable for a directory whose parent is also new. Fixed in `build.py`; see
  the 2026-09-29 entry in `.agents/rules/move_replacement_guide.md`.
- **Still unverified on hardware:** whether the props appear once that is fixed,
  and the article's behaviour. With `use_original_code = false` it has no `Main`,
  so a prop may appear frozen in mid-air. That is success, not a bug.

### The file-addition probe, as it stands

Superseded by 0.10.0 — the `new-dir-infos` route worked, so the probe below is
no longer the thing that matters. Recorded because its PASS/FAIL criteria are
still the right shape for reading the next log:

```
[PGWR] FILEADD entry=0 new_file_end_frame=… control_end_frame=… -> NEW FILE LOADED
```

- **Pass** — `-> NEW FILE LOADED`, and `new_file_end_frame` differs from the
  control (control is 60.00 or 59.00; the shipped clip is 51 frames).
- **Fail** — `-> NOT LOADED`, the two numbers equal, or no `[PGWR] FILEADD` line.

**Everything about the articles is gated behind this.** The three missing props
need new *directories*, which is the untested half of the same mechanism. Do not
build the article until this result is known.

---

## 1. The prop classification — the single most useful thing here

The user's original complaint list, resolved against the data. This is what
replaces guesswork.

| move | prop | where the mesh lives | fix |
| --- | --- | --- | --- |
| **d tilt** | manhole | **body** `manhole1M` / `manhole2M` | data already correct — see below |
| **ledge getup** | alarm clock | **body** `AlarmM`; `lhand_alarm` state exists | should already work |
| **f tilt** | stool | **article only** `chairM` | needs `normal_weapon` |
| **nair** | fishbowl | **article only** `TankM`, `FishL1-4M`, `FishR1-4M`, `SplashM`, `OverflowM` | needs `normal_weapon` |
| **bair** | turtle | **article only** `Kame`, `Head1M`, `Head2M`, `BFootM`, `FFootM` | needs `normal_weapon` |
| **up smash** | — | **no prop exists** | nothing to do; drop it |
| d smash / down attacks | hammer | **body** `RHammerM` | clip-animated, should already work |

**The manhole is the odd one out and the reason is worth understanding.** G&W's
down-tilt clip `c02attacklw3` turns the manhole on **in his own body model**:
`manhole1M` for frames 0–4, then `manhole2M` for frames 5–44. That track is
intact in the built mod — the built `c02attacklw3.nuanmb` is G&W's file
byte-for-byte, with both tracks animating. Separately the article carries its own
`ManholeM` on a dedicated **`Manhole` bone** (92 tris), while the body meshes sit
on the **`Head`** bone (1700 / 2072 tris). Different objects: the body pair is
almost certainly the hole, the article mesh the cover he swings.

So either the body prop already shows and the user is seeing the *missing cover*,
or the down tilt is not playing `c02attacklw3` at all. **Both are unconfirmed —
ask the user to look at the down tilt and report what they actually see** before
spending effort on it. An earlier instance recommended a body-visibility-group
change here; that was wrong, and building it would have been a no-op or a
regression.

**Why the other three cannot be visibility tricks:** the body model contains no
stool, no fishbowl and no turtle, and scanning every body clip for `chairM`,
`TankM` and `Kame` returns zero hits. There is no mesh to reveal. They need the
article, full stop.

### The classifier — use it for anything new

For a prop, ask in this order:

1. Is the mesh in `export/fighter/gamewatch/model/body/c06/model.numshb`?
2. Does any clip in `export/fighter/gamewatch/motion/body/c06/` turn it on?
   (`tools/untracked_meshes.py` answers this.)
3. Only if both are no: is it in `export/fighter/gamewatch/model/normal_weapon/c06/`?

Steps 1–2 mean the data is already shipped and the problem is elsewhere — most
often the status not requesting the right motion. Step 3 means the article.

---

## 2. Rule R22 was wrong, and is gone

0.8.1-draft added generator rule R22 to rewrite

```rust
VisibilityModule::set_int64(hash40("rhand"), hash40("rhand_hammer"))
```

into a direct `ModelModule::set_mesh_visibility(.., "RHammerM", true)`, on the
theory that the hammer needed a code fix because `rhand_hammer` is not a state in
any visibility table.

The premise was **half** right and the conclusion wrong. `rhand_hammer` genuinely
does not exist — `rhand` has exactly one state, the empty one — so the donor's
call is a genuine no-op. **But G&W's own clips turn `RHammerM` on**:
`f03downattacku` and `f04downattackd` at frame 11, `g03slipattack` at frame 18.
Those three clip names are not aliased; they overwrite Pyra's same-named files and
the built files are byte-identical to G&W's export. The hammer plays on its own.

R22 is removed; the donor's original dead call is restored verbatim at all three
sites. **Do not re-add it.** The `RULES` docstring in `tools/gen_acmd.py` carries
the retraction.

**The generalisable lesson, and the trap that caused it:** a dead `set_int64` in a
donor script is *not* evidence that the prop is missing. Check whether the clip
already carries the visibility track before writing any code.

---

## 3. The visibility table, fully decoded

`param_visibility_data_body` stores each state's mesh list as **`hash40` of the
lowercased** mesh name, while the model stores mixed case. The table has
`hash40("alarmm") = 0x61917c347`; the model says `AlarmM`.

Group and **state** names are ordinary exact-case `hash40` (`hash40("head") =
0x4a7f3f69c`, `hash40("lhand_alarm") = 0xb4d9cb5ed`). Only the mesh lists are
lowercased, and nothing in the file says so.

With that key **124 of 134** hashes resolve. The other 10 are all `0x7FB997A80`,
the "shows nothing" sentinel every group carries as its empty state.

Proven by brute force, not inferred: every 4-character name over `[A-Za-z0-9_]`
against the ten 4-char hashes returns exactly `no1m`..`no9m` and `keym` — the
lowercased forms of the model's `No1M`..`No9M` and `KeyM`. **When a hash table will
not resolve, check case, then brute-force the shortest entries**: `hash40`'s high
32 bits are the string length, so the length histogram is free information and
makes a 4-char search affordable.

Decoded contents (recorded in `build-record.json` under
`expression_vl.visibility_groups` on every build):

| group | states | what they show |
| --- | --- | --- |
| `head` | 6 | `HeadM`+`NoseM`, `HeadBM`+`NoseM2`, `sparky1M`, `DiverM`, `DiverFLIPM`, ∅ |
| `helmet` | 2 | ∅, `HelmetM` (the working dash helmet) |
| `lhand` | 5 | ∅, **`AlarmM`**, `BlockM`, `BucketM`, `KeyM` |
| `oil` | 4 | ∅, `OilDM`, `+OilMM`, `+OilUM` |
| `rhand` | 1 | ∅ — **no `rhand_hammer`, confirmed** |
| `zzz` | 13 | `Maru1M`–`3M` then `+LZzz1M`–`3M`, and the `R` mirror |
| `hand` | 6 | `LhandMove`/`LhandHold`/`LhandOpen` × `Rhand*` |
| `panel`, `panel_flip` | 10 each | `No1M`…`No9M` and the `_f` variants |
| `body` | 2 | 36 props: `Ball*`, `Vermin*`, `Oilpanic*`, `sheff*`, `judge*`, `fireattack*`, `flagman*`, `greenhouse*`, `lion*`, `manhole*` |

**`lhand_alarm` = `AlarmM`.** The ledge-getup alarm clock was never unidentified.
`build.py` already merges the state into the built eflame table (verified:
`lhand_alarm` → `0x61917c347` → `alarmm`).

Note the `body` group is **all-or-nothing**: one state shows all 36 prop meshes,
the other shows none. If a future move needs a subset, `tools/visibility_table.py`
has `set_state()` to add a state — but prefer a clip track, which is finer-grained.

---

## 4. The article registry — found, and fully decoded

Article agents are registered from the game **`main`** binary, *not* from the
per-fighter `lua2cpp_*.nro`. Two independent confirmations: the NRO exports no
`create_agent_article_*` at all, and the registry below exists only in `main`.

The ExeFS `main` is an **NSO0** with every segment compressed (flags `0x3F`), so
the usable artefact is the decompressed flat image
`pyra_mythra_clone/reference/dumps/images/main.bin` (86,672,752 bytes).
Virtual address == file offset, `.text` content at `0x100`, `.rodata` at
`0x39C8000`, `.data` at `0x4F16000`.

**The registry is 1845 records of 0x18 bytes at `0x3EACF88`:**

```
{ u32 name_ptr, u32 pad, u32 data_ptr, u32 pad, u32 flags, u32 pad }
```

All 1845 names resolve. `flags` is `0x403` for every record and carries no
information. Blocks are **per-fighter and contiguous**, so a fighter's local
`FIGHTER_<X>_GENERATE_ARTICLE_*` value is a block offset.

**G&W has 9 articles, local indices 0–8, at global 120–128:**

| local | global | article |
| --- | --- | --- |
| 0 | 120 | `rescue` |
| 1 | 121 | `parachute` |
| 2 | 122 | `panel` |
| 3 | 123 | `oil` |
| 4 | 124 | `octopus` |
| **5** | **125** | **`normal_weapon`** — stool, manhole, fishbowl, turtle |
| 6 | 126 | `breath` |
| 7 | 127 | `entry` |
| 8 | 128 | `bomb` |

`fish`, `friedprawns`, `sausage`, `steak` also have `model/`+`motion/` folders but
are food items, not registry articles — that distinction is what makes the count
agree at 9.

`tools/article_table.py` re-derives all of this and asserts two cross-checks:
`eflame` occupies exactly 5 records immediately before `elight` (and
`ARTICLE_TERM = 0x5` is the *exclusive* end, so articles 0–4), and G&W's own
`model/`+`motion/` folders name exactly those nine. Run it before trusting any
article index.

The table start is pinned by requiring **every** `name_ptr` to resolve as a real
string. A looser `data_ptr`/`flags` walk overshoots to 306,168 records, so do not
use those fields to find boundaries.

---

## 5. The dead end — and what is *not* dead

**What is blocked.** Each record's `data_ptr` increments by exactly 8, and the
whole 1849-slot span `0x5185BD0..0x5189590` is **0/1849 nonzero**. The
surrounding pages are essentially all zero (page `0x5180000` is 0/4096 nonzero
*bytes*). An `adrp`+`str` scan of `.text` at that range finds 3 stores, **none** at
an article slot. So they are not unrelocated `.data` pointers either. The reading
consistent with all of it: they are **runtime virtual addresses** and the game
loads `main` at a **non-zero base**, so `0x5185BD0` is not where those objects
live in the flat image. `.bss` (35,252,880 bytes) is **not in the image at all**,
so anything past ~`0x52A8C50` is absent rather than zero.

Consequence: the registry tells us **which** articles exist and their order, and
**nothing** about their behaviour. Reaching `normal_weapon`'s logic needs the load
base for `main`, which `pyra_mythra_clone/reports/exefs-dumps.json` does not record.

An earlier claim in these notes — that the slots are `.bss` vtables filled in by
load-time constructors — is **wrong** and is what the scans above disproved.

**What is not blocked, and is the more important half.** The article's own
`motion/normal_weapon/c06` has its own `motion_list.bin` (11 entries) and its
clips' **own visibility tracks select the prop**. Measured:

- `0x09b01369d5` `c01attacks3s` → `chairM` (stool)
- `0x0a18b4d5e5` `c02attacklw3` → `ManholeM` (manhole cover)
- `0x0c3a4e2597` `c05attackairn`, `0x0d562c06c5` `c05landingairn` → fishbowl meshes
- `0x0c33f869bc` `c05attackairb`, `0x0d5f9a4aee` `c05landingairb` → turtle meshes
- `0x09007be1e4` `j01appeallw`, `0x099c52257e` `c00attack11`, `0x0a5ae1e07e` `c00attack100`, `0x0ea34e5703` `c00attackend` → 15× `KiriM1..KiriM15` (the spray)

The article also has a **dedicated skeleton** with its own `Manhole`, `Tank` and
`Body2` bones. So it is a real, self-contained, bone-rigged object.

**Why this may make the dead end irrelevant.** `main` contains the animcmd
strings `ARTICLE_MOT_CHANGE`, `ARTICLE_SHOOT`, `ARTICLE_OPE`, `ARTICLE_SETVS` —
*fighter-side* commands that tell the article what to do. Combined with the
article having its own motion list and prop-selecting clips, the strong prior is
that the agent is **thin**: it exists, gets handed a motion, and the clip's
visibility track picks the prop. If that holds, the missing original code is not a
shortcut, because there is almost nothing in it. Write a minimal article and
flag it unverified.

---

## 6. `new-dir-infos` — read from source, not guessed

From `Raytwo/ARCropolis` `src/fs.rs` (`process_mods`). In order:

1. `preprocess_reshare` (map dep → source)
2. **`new_dir_infos`** → `add_dir_info(ctx, Path::new(dir_info))` — a JSON
   **array of plain path strings**, not objects. `new_dir_infos_base` →
   `add_dir_info_with_base(ctx, new, base)`, a map, **sorted by the new-path key**.
3. *Only then*, for each mod file whose hash is not in `data.arc`:
   `add_file` + `add_searchable_file_recursive`.

A new directory must exist as a DirInfo **before** the files inside it are added.
That is the whole reason `normal_weapon`'s `model/` and `motion/` folders need this
key while `fighter/eflame/motion/body/c06` does not.

Two details that decide eligibility:

- `is_handler_consumed` skips `config.json`, `plugin.nro`, `bgm_property.bin` and
  anything ending in `prcx prcxml stdatx stdatxml stprmx stprmxml xmsbt
  patch3audio motdiff yml`. **`.prc` is not in that list**, nor are `.nuanmb` or
  `motion_list.bin`, so those are added by `add_file` when absent from `data.arc`.
- `add_file` clones its `FilePath`/`FileInfo`/`FileData` from a hardcoded
  `BASE_MODEL = fighter/mario/model/body/c00/model.numdlb`, sets
  `standalone_file` + `unshared_nus3bank` and load type 1. It is generic because
  the loader dispatches on the file extension at load time.

`new-dir-infos` is **untested**. It is the cheapest possible probe: declare the
article's directories and put nothing in them, and see whether ARCropolis mounts
them. One boot cycle, no Rust, and it tests the riskiest mechanism in isolation.

**Do not ship a probe into a build that is mid-console-test** — changing
`config.json` or the asset tree under the user invalidates the run in progress.

---

## 7. The status scripts — the biggest remaining gap, and the NO SHORTCUTS issue

The plugin replaces **124 ACMD functions** (`game_`/`effect_`/`sound_`/
`expression_`) across 31 Pyra statuses. It replaces **no status-control
functions**. `PreMain`, `Main`, `Init`, `InitAfterDeath`, `ExitStatus` and
`cleanup` are all still eflame's.

The clean example:

```rust
unsafe extern "C" fn game_downattacku(agent: &mut L2CAgentBase) { ... }   // ported
```

contains **no `change_motion` at all**. The motion comes from eflame's own status.
The animation only looks right because G&W's clip and Pyra's clip **share a name**,
so eflame's status asking for `f03downattacku` happens to load G&W's file. That is
a name collision doing the work a port should do, and under NO SHORTCUTS it is a
real hole, not a nitpick.

**The donor repo cannot fix it.** Across all 384 files in
`SSBU-Dumped-Scripts-main/smashline/lua2cpp_gamewatch/gamewatch` the only function
families are `expression_*` 352, `sound_*` 194, `game_*` 184, `effect_*` 103 —
**zero** `PreMain`/`Main`/`Init`/`ExitStatus`/`PreAttack`/`cleanup`.

They are native code in `lua2cpp_gamewatch.nro` (1,417,216 bytes), reached through
the exported `create_agent_**fighter**_status_script_gamewatch`. Note the
**"fighter"** — searching for `create_agent_status_script_gamewatch` matches
nothing and looks like "the NRO has no scripts". `tools/nro_syms.py` lists all
**576** exports with offsets.

**This is the better Ghidra target than `main.bin`** — 1.4 MB is a minutes-long
job. The blocker is that `Elf64_Sym` is **0x18 bytes, not 0x10**
(`st_name`, `st_info`, `st_other`, `st_shndx`, then `st_value`, `st_size`). That
stride error broke the first version of `nro_syms.py`. Even corrected, the `MOD0`
header's table offsets do not fit the documented layout for that NRO and no
assignment resolves names, so **do not ship a parser that claims to read the
dynsym** — the current tool enumerates `_Z`/`__` names with file offsets instead,
which is reliable. Getting per-status `Main`/`PreMain` *addresses* needs the NRO
decompiled.

---

## 8. Tooling

All under `mod_files/pyra_gamewatch_reskin/tools/`, run with
`scratch/py312/python.exe` (needs cp312 + `ssbh_data_py`).

| tool | what it does |
| --- | --- |
| `article_table.py` | decodes the 1845-entry article registry, prints G&W's block, asserts both cross-checks |
| `visibility_table.py` | reads/edits `param_visibility_data_body`; now resolves lowercased mesh names |
| `untracked_meshes.py` | which body meshes no clip ever turns on — the classifier's step 2 |
| `find_rodata_xref.py` | scans `.text` for `adrp`(+`add`) into a given string address or raw address |
| `nro_syms.py` | lists exported symbol names in a fighter NRO with file offsets |

`build.py` records the whole decoded visibility table into `build-record.json` on
every build, so a future dump that changes it shows up as a reviewable diff rather
than a silent change on hardware.

Build commands: `scratch/py312/python.exe build.py` (assets) →
`tools/gen_acmd.py` → `tools/gen_common.py` → `bash build-plugin.sh`. `gen_acmd.py
--check` must pass. `build.py` is byte-deterministic. **Never hand-edit
`generated/*.rs`; change the generator.**

---

## 9. Ghidra — measured, so you do not repeat it

- **Do not analyse the whole 86 MB `main.bin`.** Default analysis spent 17
  minutes producing **one** `Decompiling` log line while the project stayed at
  5 KB — Ghidra does not flush until the end, so a killed run leaves nothing.
  Trimming the decompiler-backed analyzers got it writing but it still stalled at
  the *same* address (`0x22b01d0`, a third into `.text`), so the analyzer names in
  that list did not all match this build. Budget hours, or slice the image.
- Scripts must be **Jython `.py`**, not `.java`: Ghidra's `JavaScriptProvider`
  will not compile a `.java` passed to `-preScript` and wants a `.class`.
- `setAnalysisOption` in a pre-script does not reliably suppress the
  auto-analysis that follows. Check the log for `Decompiling` lines rather than
  trusting the option list.
- Scratch project: `scratch/ghidra/proj`, scripts in `scratch/ghidra/ghidra_scripts`,
  runner `scratch/ghidra/analyze_main.sh`, Ghidra 11.1.2 at
  `scratch/ghidra/ghidra_11.1.2_PUBLIC` (workspace-local, nothing global).

## 10. Unresolved, stated as unresolved

- `adrp`+`add` finds **zero** references within ±128 KB of the registry at
  `0x3EACF88`, and no 32- or 64-bit pointer anywhere in the file targets
  `0x3EACF88` or `0x3EADB40`. `VA == file offset` holds for `.text` and is
  **unproven for `.rodata`**. An `adrp`+`add` target preserves the low 12 bits of
  the real address, so a base could be recovered by filtering on a low-12
  signature — but 79–111 candidates appear and none dominates. Not merely
  unfinished: genuinely open.
- The article *store scan* only covered `str` with an **immediate** offset. Code
  filling a uniform 1849-entry array would use a **register-offset** store
  (`str xN, [xM, xIdx, lsl #3]`) or `stp`, which that scan structurally could not
  see. Widening it is cheap and is the first thing to try.

## 11. Recommended order

1. **Get the 0.8.1 test result.** Everything downstream is gated on it.
2. **Ask the user what the down tilt actually looks like** — is a manhole already
   visible, and is a cover missing? This costs one sentence and prevents building
   the wrong fix.
3. **Add the `new-dir-infos` probe** (declare the article directories, ship
   nothing in them). Cheapest test of the riskiest mechanism, one boot cycle.
4. **Widen the article store scan** to register-offset and pair stores.
5. **Ghidra the 1.4 MB NRO** for the per-status `Main`/`PreMain` — the real
   NO SHORTCUTS gap, and much cheaper than `main.bin`.
6. Only then build `normal_weapon` for the three props that genuinely need it.
