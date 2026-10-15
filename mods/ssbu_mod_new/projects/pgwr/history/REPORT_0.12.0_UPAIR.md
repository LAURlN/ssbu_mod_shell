# 0.12.1: up air (Claude, 2026-09-29)

Installed on the card. **0.12.0 crashed on hardware**; 0.12.1 is the fix and is
also not yet run. The 0.12.0 crash and its cause are kept below because the fix is
one flag and the reason is not obvious.

## What was wrong

Up air did nothing. G&W's `game_attackairhi` is two article calls and nothing else:

```
frame 8:  ArticleModule::generate_article(..., *FIGHTER_GAMEWATCH_GENERATE_ARTICLE_BREATH, false, -1)
frame 9:  ArticleModule::shoot(..., *FIGHTER_GAMEWATCH_GENERATE_ARTICLE_BREATH, *ARTICLE_OPE_TARGET_ALL, false)
frame 41: FT_MOTION_RATE(2.0)
```

There is **no hitbox in the move at all** - the projectile carries it. Rule R1 dropped
both calls because eflame has no article 6, so the generated function was
`on_flag(ENABLE_LANDING)`, three `frame`s, a `FT_MOTION_RATE`, and nothing else. The
move could not do anything, and there was no other part of it left.

## The three changes

1. **`plugin/src/article.rs`** registers a *second* clone, `breath`, after
   `normal_weapon`: `clone_weapon("gamewatch", *WEAPON_KIND_GAMEWATCH_BREATH
   (0x7E = 126), "eflame", "breath", false)`. The local id is `FIGHTER_EFLAME_ARTICLE_TERM
   + returned`, read back from the return value, so it is 5 for `normal_weapon` and 6 for
   `breath`. **The call order is the index** - smashline appends each fighter's article
   descriptors in the order `clone_weapon` was called, so swapping the two calls would
   not crash, it would hand every move the wrong article with no error anywhere.
2. **`tools/gen_acmd.py` R26** rewrites `*FIGHTER_GAMEWATCH_GENERATE_ARTICLE_BREATH` to
   `crate::article::breath()` and teaches R1's `kill_article` to keep those lines, the
   same shape R23 already does for `normal_weapon`. It has to run before R1, because R1
   drops any `ArticleModule::` line still naming a G&W article.
3. **`build.py`** ships the article's files. This is the part that is not optional -
   see below.

One compile error came out of this and is now rule R24: the dump prints
`shoot`'s target as a bare `*ARTICLE_OPE_TARGET_ALL` where the locked skyline-smash
(315e4e8) binding takes `ArticleOperationTarget`. `remove_exist` is fine - the dump
already prints that one wrapped.

## Why the files ship for all eight slots, and the move still only works on c06/c07

These are two different things and the project has already been burned by conflating
them. The user asked for c06/c07 only; that is the *behaviour*, and it is already true
and stays true:

- the spawn lives in `game_attackairhi`, an ACMD override registered through
  `Agent::new("eflame").set_costume([6, 7])`, so smashline only installs it for c06/c07;
- nothing else in the plugin spawns the breath - `note_breath` is only called from that
  generated function, and `lifetime` tracks `normal_weapon` only.

The *files* are a different question and the answer is all eight. smashline registers
the clone on the fighter **kind**, so vanilla Pyra c00-c05 carry the article table entry
too, and the engine loads an article's model while initialising the fighter. 0.10.0/0.11.0
recorded the failure mode exactly: crash 01790691291, a null read in
`fighter_initialize_object_data` while loading the article's model, when a slot was
missing its files. Vanilla slots never spawn it, so the files are loaded and never
shown - invisible to the player, but removing them risks a match-start crash.

## A donor detail worth not re-deriving

G&W's `breath` model is **not** uniform across his eight colours, unlike `normal_weapon`:

- `model.nuanmb` is present in c00, c01, c02, c06 and absent from c03, c04, c05, c07;
- every slot's three `.nutexb` textures differ from the others;
- the motion folders, by contrast, are byte-identical across all eight (all seven
  compare equal to c00 with `diff -r -q`).

`build.py` lists the files per donor slot and `build_article` still asserts
`on_disk == set(names)` for each, so a slot that disagrees with this table fails the
build rather than shipping something undeclared. `article_files` is deliberately strict:
an unknown donor slot is a build error, never a silent fallback to c00.

This also corrects an older comment that said G&W's eight `normal_weapon` folders were
byte-identical. The **motion** folders are; the **model** folders are not, because every
colour has its own textures. What is uniform there is the set of file *names*, which is
the only thing that table encodes, so one list covering all eight slots is still right.

## Card

- reskin NRO `1b88d28f68e621c85de3557610529bb8c3e7ae9f41bf8228c20d8752d5ac4d7f`
- mod tree: 1109 files (was 961)
- `libsmashline_plugin.nro` deliberately **not** touched: still
  `5f4091eed89c5854c2bfccb9f25b6e8da8c03ebedcaa5ab36eadebfc078bc8f7`

**`install-to-card.sh` must keep being run with `--no-smashline`.** Without it the
script installs `b906669d...` from `mod_files/mgw_standalone/target-smashline`, which is
Space Bunny's 0.10.0 rebuild of the global plugin - the one that **crashed the game**
and was rolled back. It is no longer needed: registering the article from this mod's own
NRO via `clone_weapon` is enough, because the mod's `smashline` crate resolves every
`smashline_*` symbol at runtime through `nn::ro::LookupSymbol` and calls into the
installed plugin. The script's own header comment still describes the old design and is
now misleading.

Backup: `sd-backup-20260929-184753/` (the 0.11.2 mod tree, 961 files).
The old `pgwr_log.txt` was set aside as `pgwr_log-0.11.2.txt` so this test's log is
unambiguous.

## 0.12.0 crashed, and why: `use_original_code`

**Symptom.** 0.12.0 froze on the exact frame the puff spawned, with no crash code
captured. `sd:/ultimate/pgwr_log.txt` held only the two boot lines - no
`BREATH spawned`, which is emitted *immediately after* the `generate_article` call.
So the death was inside `generate_article`, i.e. inside the article's own
construction.

**Cause.** `clone_weapon`'s last argument is not a preference. In the locked
smashline (`create_agent_status_weapon`, be3ef30) it decides whether the donor's
script module is loaded when the article is created:
`get_weapon_code_dependency` -> `load_fighter_module(0x1C)` -> retry the original
create. With it `false` the article's status agent is built as a bare
`L2CWeaponCommon` with `original_set_status_scripts = None` - **an agent with no
status scripts at all**.

For `normal_weapon` that is fine, and was measured in 0.11.0: it has no donor
status code, because there is no `gamewatch_normal_weapon` script folder. It is a
dumb prop whose animation its own clips select. 0.11.x proved it on hardware.

For `breath` it was the crash. The donor has a folder
`SSBU-Dumped-Scripts-main/smashline/lua2cpp_gamewatch/gamewatch_breath/` containing
`AttackAirHi.txt` - the projectile's own attack script, three shrinking hitboxes
(97/55/40 damage) then a strong one (4.3 launch, 65 base). **That is the damage up
air does**; the fighter-side script only spawns and shoots. So the article's first
status call had nothing to run, on the spawn frame.

**Fix.** `use_original_code = true` for `breath` only. `normal_weapon` stays
`false` - it is console-proven and has no code to load. The difference is evidence,
not taste, and the comment at the call site says so.

Two supporting changes: the boot line is now written **before** the `clone_weapon`
call, because a failed module load is followed by a
`while !is_fighter_module_loaded` spin and the last log line is what distinguishes
"hung loading gamewatch" from "crashed"; and the boot lines now say which article
got donor code.

## The other four G&W articles, measured the same way

The same `lua2cpp_gamewatch/` listing decides whether an article needs donor code,
so it is worth recording rather than re-deriving per article:

| article | donor script folder | needs `use_original_code` |
| --- | --- | --- |
| `normal_weapon` | **none** | no - proven working |
| `breath` | `gamewatch_breath/AttackAirHi.txt` | **yes** |
| `bomb` | `gamewatch_bomb/` | yes, when f-air is done |
| `octopus` | `gamewatch_octopus/` | yes |
| `food` | `gamewatch_food/` | yes |
| `oil` | `gamewatch_oil/` | yes |
| `parachute` | `gamewatch_parachute/` | yes |
| `rescue` | `gamewatch_rescue/` | yes |

`panel` and `entry` have no folder, so they behave like `normal_weapon`.

## Card (0.12.1)

- reskin NRO `f132410f80ecec51d8df42cbf4b1de1815a986ae750c9c8c80fb2fd44f37f9bb`
- mod tree: 1109 files, unchanged from 0.12.0
- `libsmashline_plugin.nro` untouched: `5f4091ee...`
- backups: `sd-backup-20260929-184753/` (0.11.2 tree), `sd-backup-20260929-190420/`
  (0.12.0 tree). `pgwr_log.txt` cleared; the 0.11.2 log is kept as
  `pgwr_log-0.11.2.txt`.

**Note on who built this NRO.** Another agent was working in this same crate
concurrently - it now also contains a `mythra/` module (Corrin's up air, Hero's
Spin, Luigi's down throw on `elight` c06/c07), and that module was mid-edit and
failing to compile while 0.12.1 was being built. 0.12.1's NRO is the **whole**
current crate including that module, not my changes alone. My changes are
`plugin/src/article.rs`, `plugin/src/acmd/mod.rs`, the generated
`acmd/generated/*`, `tools/gen_acmd.py` and `build.py`.

## Console test (0.12.1)

Log lines (`[PGWR]`) at boot, all three must appear:

```
---- boot v0.12.1: registered gamewatch weapon kind 125 as eflame_normal_weapon, clone index 0, local article id 5, donor code off (it has none)
---- boot v0.12.1: registering gamewatch breath with donor code
---- boot v0.12.1: registered gamewatch weapon kind 126 as eflame_breath, clone index 1, local article id 6, donor code on
```

The middle line is the hang detector: if the game freezes on the first up air and
that is the *last* line in the log, the donor module is not loading and the flag
approach is wrong.

1. **Vanilla control first.** Load a match with vanilla Pyra c00, c05 and Mythra.
   They must load and play normally, and produce no `[PGWR]` line. The article is
   registered on the whole fighter kind, so this is the one thing that could
   disturb them. A crash at match start here means the file route, not the move.
2. **Real Mr. Game & Watch** still has his own up air.
3. **c06 and c07, up air (down-B, then up + A).** Does the breath projectile appear,
   come out of his mouth, travel, and hit? Each spawn logs `BREATH spawned` then
   `BREATH shot`. This time the lines are expected to appear - their absence is
   what 0.12.0's log proved.
4. **c06's other aerials** must not regress: nair fishbowl, b-air turtle.
5. Repeat up air several times, and get KO'd mid-move. Does a stray breath linger?

Report per case: projectile visible or not, and what the `BREATH` lines say.

### 0.12.0 console test - SUPERSEDED, kept because the crash is the evidence

0.12.0 installed plugin `1b88d28f...`, 961 + 148 = 1109 mod files. It crashed.

1. **Vanilla control first.** Load a match with vanilla Pyra c00, c05 and Mythra. They
   must load and play normally, and produce **no** `[PGWR]` line for up air. The article
   is registered on the whole fighter kind now, so this is the one thing that could
   disturb them. A crash at match start here means the file route, not the move.
2. **Real Mr. Game & Watch** still has his own up air.
3. **c06 and c07, up air (down-B, then up + A).** Does the breath projectile appear?
   Does it come out of his mouth? Does it travel and hit? Each spawn logs
   `BREATH spawned` then `BREATH shot`, with `IS_EXIST_ARTICLE` and `active` counts.
4. **c06, the other aerials** must not regress: nair still shows the fishbowl, b-air the
   turtle, f-air the bomb behaviour it had before.
5. Repeat up air a few times in a row and get KO'd mid-move. Does a stray breath linger?

Report per case: projectile visible or not, and what the `BREATH` lines say. If the
projectile does not appear, the `BREATH spawned` line's `IS_EXIST_ARTICLE` value
distinguishes "the article does not exist" from "it spawned and is somewhere else".
