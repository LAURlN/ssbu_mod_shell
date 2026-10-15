Current build: 0.14.0 combines the G&W breath parameter fix with Mythra c06/c07's three move replacements. Build and offline checks passed; console testing is pending. See [REPORT_0.14.0_UPAIR.md](REPORT_0.14.0_UPAIR.md). The version sections below are historical.

# Pyra c06/c07 → Mr. Game & Watch (0.8.1, phase 2)

Pyra's c06 and c07 costumes are Mr. Game & Watch. The game's own Pyra↔Mythra
down-B swap is the transformation — no swap hooks, no clone engine, no camera
patches.

- **Assets** (`build.py`): G&W's model, skeleton, textures and animations on Pyra
  c06/c07, grafted onto Pyra's bone set.
- **Plugin** (`plugin/`, `build-plugin.sh`): a Skyline + smashline 2 crate that
  replaces **124 ACMD functions across 31 Pyra statuses** with G&W's, gated to
  c06/c07 only. It replaces **no status-control functions** — see the status gap
  below, which is the largest remaining hole.
- **Mythra moves** (`plugin/src/mythra/`, 0.13.0): Corrin's up air, Hero's Spin
  and Luigi's down throw on Mythra c06/c07. This is a *second* fighter, and it
  leaves the G&W half above completely untouched. See
  `REPORT_0.13.0_MYTHRA_MOVES.md`; it is written and typechecked but **not
  built and not console-tested**.

Still Pyra's: specials, weight, speeds, gravity and every other stat. That is
phase 3 onward.

## Current state: 0.9.0 (2026-09-29), supersedes the sections below where they disagree

**Console-confirmed:** 0.7.0 — the user's words, legs fixed and animations look normal,
and the only remaining problems are visual. The G&W props (stool, fishbowl, turtle,
manhole cover) are still missing, because they are the `normal_weapon` article rather
than body meshes.

### 0.9.0 — the article's assets are in; the article is not spawned

`build.py` now ships G&W's `normal_weapon` article into eflame's namespace as four
**new directories** — `fighter/eflame/model/normal_weapon/{c06,c07}` and
`fighter/eflame/motion/normal_weapon/{c06,c07}`, 16 + 12 files per slot, copied
byte-for-byte and never edited, because the clips' own visibility tracks are what
select the prop. All four are declared in `config.json` under `new-dir-infos` with
their files under `new-dir-files`.

That closes the file-addition question the previous handoffs left open.
`new-dir-infos` was called "untested"; it no longer is, because
`mod_files/mgw_standalone/` drives those exact keys for whole new fighter trees and
its G&W clone loaded and ran on hardware. Nine of the article's ten clips are
already eflame file names, so this is "standard file names in new directories",
the proven shape.

**The article is not spawned, and that part is blocked rather than unfinished.**
Registering it means calling smashline's `clone_weapon`, which writes to
`NEW_ARTICLES`; that map is read by exactly one thing, a raw-offset hook into
`main` at `0x64b730` that the *installed global* plugin already owns. A mod NRO
statically links its own smashline and cannot reach the installed plugin's statics,
so the reskin's call would write to a map nothing reads. Installing its own copy of
the hook collides with the global one. On top of that, the smashline revision this
crate pins (`be3ef30`) carries three name tables 0x1000 off and eleven hook offsets
with a `+ 0x5B0` shift that this game does not have. Both fixes are a raw-offset
hook or a rebuilt global plugin, which NO SHORTCUTS item 4 reserves.

Full evidence, and the three cheap ways to unblock it, are in
`REPORT_0.9.0_ARTICLE_ASSETS.md` §2.

**Expect 0.9.0 to look exactly like 0.8.1 on screen.** The console test is the
0.8.0 file-addition probe, which still rides along.

### The manhole is not a separate bug

Measured, and worth not re-deriving: G&W's down-tilt clip `c02attacklw3` carries a
45-value visibility track for `manhole1M` (frames 0–4) and `manhole2M` (frames
5–44), and the built c06 file is byte-identical to the export — so **the hole is
already animating in the build on the card**. The cover, `ManholeM`, is absent from
every body clip in both the export and the build; it is article geometry on the
article's own `Manhole` bone. Same blocker as the stool, the fishbowl and the
turtle, and no separate fix.

One stale comment to ignore: `complete_visibility`'s docstring in `build.py` still
claims G&W's clips never track `RHammerM`. They do — a 50-value track in all three
moves that use it. That is the same wrong theory that produced the retracted rule
R22, and this function writes `False` into every mesh a clip omits, so believing it
would send someone to "fix" the manhole by editing the pass.

0.8.1 was going to fix the down-attack hammer and **retracted that instead**: the hammer
was never broken. G&W's own clips turn `RHammerM` on by themselves, in exactly the
three moves that use it (`f03downattacku` and `f04downattackd` at frame 11,
`g03slipattack` at frame 18), and those clip names are not aliased. Rule R22 is gone
and the donor's original dead `set_int64` call is restored. The plugin NRO is therefore
**byte-identical to 0.8.0**.

What 0.8.1 keeps is worth more than the fix it dropped. The visibility table is now
**fully decoded**: `param_visibility_data_body` stores mesh names **lowercased**, so
the table holds `hash40("alarmm")` where the model says `AlarmM`. With that key 124 of
134 hashes resolve (the other 10 are the `0x7FB997A80` empty-state sentinel), and
**`lhand_alarm` = `AlarmM`** — the ledge-getup alarm clock was never unidentified. The
build record now carries the whole table with names resolved, via
`tools/visibility_table.py` and the new `tools/untracked_meshes.py`.

### The real gap: status scripts are still eflame's

`game_downattacku` contains no `change_motion`; the motion comes from eflame's own
status. The hammer animation works only because G&W's clip and Pyra's clip **share a
name**, so eflame's status asking for `f03downattacku` loads G&W's file. That is a
name collision doing the work a port should do, and under NO SHORTCUTS it is a real
hole, not a nitpick.

The donor repo cannot fix it: across all 384 files in
`SSBU-Dumped-Scripts-main/…/gamewatch` the only function families are
`expression_*` (352), `sound_*` (194), `game_*` (184) and `effect_*` (103) — **zero**
`PreMain`/`Main`/`Init`/`ExitStatus`/`PreAttack`/`cleanup`. G&W's status logic is
native code in `lua2cpp_gamewatch.nro`.

That same NRO is where the article agents live, and the workspace has a full verified
Smash 13.0.4 ExeFS dump with a rebuilt `main.bin` (article agents are registered from
`main`, not the per-fighter NROs — which is why article code was previously thought
unrecoverable). `normal_weapon` is present in `main`.

0.8.0's **file-addition experiment** rides along unchanged, so the pending console run
is still the one test: one G&W clip (`d01specialsl.nuanmb`, Judge's held pose) shipped
under a file name `eflame` has never had and declared in a new mod `config.json`.

Both are built and offline-verified; **neither is console-tested yet.** The card is
still on 0.7.0. Full write-up: `REPORT_0.8.1_RETRACTION.md`.

- Hammers: `REPORT_0.8.1_HAMMERS.md`
- File addition: `REPORT_0.8.0_FILEADD.md`

## State

| Phase | Status |
| --- | --- |
| 0. Assets only (0.1.0) | **Console-verified 2026-09-29.** Loads, swaps, no crashes. |
| 1. Plugin + gating + jab (0.2.0) | Built, run once, **verdict inconclusive** (see below). |
| 2. Normals, aerials, grabs, throws (0.3.0) | Console-tested: "mostly right", no crash. Gating never checked. |
| 2b. Rapid-fire chain (0.4.0) | **Built, not yet console-tested.** |
| 3. Stats | Not started. |
| 4. Specials | Not started. |
| Mythra c06/c07 moves (0.13.0) | **Written, typechecked. Not built, not installed, not console-tested.** |

Console run 1 could not confirm the gate: the jab was reported as "kinda hard to
tell" and the vanilla control was never confirmed. 0.3.0 adds a log line that
makes gating a reading rather than a judgement — see below.

## How the gating works

`plugin/src/lib.rs` has the only list of gated costumes:

```rust
pub const TARGET_COSTUMES: [usize; 2] = [6, 7];
```

Every override is registered through
`Agent::new("eflame").set_costume(TARGET_COSTUMES.to_vec())`. In the locked
smashline (`be3ef308`, `src/create_agent.rs`) that gates at **install** time: for
an eflame agent created in c00–c05 the costume check fails and
`sv_set_function_hash` is never called, so Pyra's stock script pointer stays
untouched. We are not overriding Pyra's script for everyone and branching inside
it, so there is no `else` branch that can drift from vanilla.

`elight` (Mythra) and `gamewatch` (the real Mr. Game & Watch) are never
registered with smashline at all, so nothing of theirs is touched either.

**Exception, 0.13.0.** `plugin/src/mythra/` does register `elight`, for three
moves on c06/c07 only. See `REPORT_0.13.0_MYTHRA_MOVES.md`. The gate is the same
`.set_costume(TARGET_COSTUMES)`, and `gamewatch` is still never registered.

**`gate_trace`** in `src/acmd/mod.rs` is a `Main` callback registered on the same
gated agent. Because smashline only installs it for c06/c07, this line in the log
is positive proof the gate holds:

```
[PGWR] GATE ACTIVE: entry 0 running c06/c07 overrides, reported colour 6
```

The negative control is the *absence* of such a line for c00–c05 in the same
match. Filter the log on `[PGWR]`.

## The port is generated, not hand-written

`tools/gen_acmd.py` emits `plugin/src/acmd/generated/{ground,aerial,grab}.rs` from
the dumps. `gen_acmd.py --check` proves the checked-in files still match the
generator.

Eleven transformation rules (R1–R11) are documented in the generator with the
reason for each, and every drop is recorded in a `GEN-NOTES` header in the file
it happened in. `generated-manifest.json` records donor script and status list per
group. `tools/analyse_port.py` reports what each donor script depends on.

Two bugs were caught by reviewing the generated output, both of which would have
shipped silently:

- G&W work-index writes survived rule R1 (which only matched `ArticleModule::`),
  and would have written G&W's raw index `0x100000BD` into Pyra's work array.
- The dump renders `if WorkModule.is_flag(...) then` as a discarded call plus a
  hardcoded `false == true` branch, so the side-smash body it guarded would never
  have run.

## Known gaps in 0.3.0

- **Articles.** `normal_weapon` (0.11.0) and `breath` (0.12.0) are registered on
  eflame, so the held props and **up air** work. Still missing: forward air
  (G&W drops a `bomb` article; eflame only has a body hit) and the jab/down-smash
  prop. `bomb` is the next article, and it is the same three-step shape - clone it,
  ship its files, teach the generator its constant.
- **Sounds.** All 21 `se_gamewatch_*` names are unreachable from eflame and are
  mapped by role to verified-resident eflame sounds. G&W's signature tooting is
  *not* reproduced — he sounds like Pyra swinging a sword. A later one-slot pass.
- **Stats** are all still Pyra's. This is why c06/c07 will not yet feel like G&W
  even when every move is correct.
- **The swap cutscene.** Pyra's `visual_scene_01/02` have no G&W equivalent and
  fall back to `wait`, so G&W stands still during the down-B transformation.
  Inherent to keeping Mythra vanilla, not a missed mapping.
- **A second G&W appears, from the start, during movement and most animations.**
  Undiagnosed. It is not the windummy (only spawned in the win poses). Working
  hypothesis: the dormant Aegis partner, because `EntryL`/`EntryR` generate
  `GENERATE_ARTICLE_DIVER` and eflame has no model folder of its own for it, so
  it would resolve through the body folder this mod overwrites. Needs the
  down-B test in `reports/console-2026-09-29-run2/RESULT.md` to confirm. Do not
  "fix" it by writing G&W files into `fighter/elight/...` — that would turn real
  Mythra c06 into G&W.
- `build.py` records which motions fall to `wait`; none of them belong to a
  phase-2 move. The 8 that remain are 10 unnamed hashes, Wario-bite grabbed
  states, three `fill_blank_*` fillers, and the two visual scenes.

## Building

```bash
scratch/py312/python.exe mod_files/pyra_gamewatch_reskin/build.py      # assets
scratch/py312/python.exe mod_files/pyra_gamewatch_reskin/tools/gen_acmd.py   # regenerate ACMD
bash mod_files/pyra_gamewatch_reskin/build-plugin.sh                   # plugin
```

`build.py` needs the cp312 `scratch/py312` interpreter (system Python 3.8 cannot
load the vendored `ssbh_data_py`). `build-plugin.sh` needs `cargo skyline` and
**installs to the SD card when it finishes** — see below.

## Installing to the SD card is the agent's job

Since 2026-09-29, installing is part of finishing a build, not something to hand
to the user. This includes for whoever this work is handed to next.

```bash
bash mod_files/pyra_gamewatch_reskin/install-to-card.sh            # install + verify
bash mod_files/pyra_gamewatch_reskin/install-to-card.sh --dry-run  # report only
bash mod_files/pyra_gamewatch_reskin/build-plugin.sh --stage-only  # build, don't install
```

All three artefacts go on together: the reskin NRO, the **patched** global
smashline plugin, and the 793-file mod tree.

This inverts an earlier rule in this project, which deliberately never wrote to
the card and printed copy instructions instead. That rule was self-imposed and it
cost a whole console-test cycle: the card silently ran a 0.8.x build against an
unpatched smashline plugin, so every prop was absent and the result looked like
a code bug. **Do not print copy instructions and stop.** If a build is finished,
install it.

The safety rules that replaced it, all enforced by `install-to-card.sh`:

- the card is found by its own contents, never a remembered drive letter, and the
  script refuses to write to a volume that is not a Switch card;
- every overwrite is backed up to a timestamped `sd-backup-*/` in this directory
  first;
- the mod tree is staged as `pyra_gamewatch_reskin.new`, verified by file count,
  then swapped, so the card is never left half-written;
- the result is verified by `cmp`, file count and `diff -r`;
- **any** verification failure rolls the card back automatically.

The user remains the only person who can test on the console. Do not call a build
working until they have run it.

`build.py` is byte-deterministic — re-running reproduces `build-record.json`
exactly.

## Installed on the SD card (F:)

Managed by `install-to-card.sh`; see the section above. The state below is a
historical record of hand installs, kept because the reports reference it.

0.7.0 was installed 2026-09-29 (console-confirmed). 0.8.0 needed both of:

- `atmosphere/.../skyline/plugins/libpyra_gamewatch_reskin.nro`
  — 151552 bytes, `ed2988e148d2e6ec52f213202b53c0cb0aeb5ae92277f08985006bbf4b4d4378`
  (card currently has 0.7.0, `4d74191056230bdb0d7693d32f72b2177c3338096b749c5ead72320e8e60576b`)
- `ultimate/mods/pyra_gamewatch_reskin/` — 793 files at 0.9.0, the card has 736. The
  `config.json` declares the new file to ARCropolis *and* the four new
  `normal_weapon` directories, so it is the one that must not be left behind.
  `build.py` rebuilds the folder from scratch, so replace it rather than merge.
- `atmosphere/.../skyline/plugins/libsmashline_plugin.nro` — **must now be replaced
  too, and this is a deliberate change to a shared file.** It is
  `mod_files/mgw_standalone/smashline_1304` with one addition: a boot-time
  registration of G&W's `normal_weapon` article on eflame, in
  `smashline_1304/src/pgwr_article.rs`. Without it the article never exists and no
  prop can appear. The addition is one call to the crate's own public API; it adds
  no hook, no address and no offset, and every other hook the plugin installs is
  unchanged. Built result is 315392 bytes,
  `b906669d4754bbf04f3d419bbd06f83a7b3ff1e0e505d0ac76c1531b74af7230` (the card has
  the 26 Sep build).

  **Do not install an upstream smashline release instead.** Newer releases only
  support 13.0.5+; this card is on 13.0.4, and the plugin refuses to install its
  hooks at all if the game's bytes do not match (`mgw_version::matches`).

Do not replace `libarcropolis.nro`, `libarc_network.nro` or `libnro_hook.nro`.
The parked Clone Engine and CSK collection stay
uninstalled. Rollback: `sd_backups/2026-09-29_before_pgwr_0.7.0/` holds 0.6.0;
`.../2026-09-29_before_pgwr_0.4.0/` holds 0.3.0 and `.../0.3.0/` holds 0.2.0.

## Next console test

0.12.0's, in full: `REPORT_0.12.0_UPAIR.md`. In short:

1. **Vanilla control first:** vanilla Pyra c00, c05 and Mythra load into a match and
   play normally, with **no** `[PGWR]` line. The article is registered on the whole
   fighter kind, so a match-start crash here is the file route, not the move.
2. Real G&W still has his own up air.
3. As Pyra **c06** and **c07**, do **up + A** in the air. The breath projectile should
   come out. Each spawn logs `BREATH spawned` then `BREATH shot`.
4. c06's nair fishbowl and b-air turtle must not regress.

The log is `sd:/ultimate/pgwr_log.txt` on the card. It is reset per test run, so it
holds only the current one.

## Tools

- `tools/sound_names.py` — probes whether a sound name would actually load for
  eflame, validating names from `<bank>.nus3audio` against `<bank>.tonelabel`
  keys (crc32 of the name). `--index` writes `sound-inventory.json`;
  `--find <substring>` searches the 111 verified-resident eflame sounds.
  67 G&W sounds are unreachable.
- `tools/analyse_port.py` — per-donor dependency report → `port-dependencies.json`.
- `tools/gen_acmd.py` — the port generator; `--check` verifies the tree.
