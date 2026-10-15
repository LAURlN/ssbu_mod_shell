# mii_customizer - Skyline plugin, 0.5.0 `menu`

Character stat presets per saved Mii, chosen inside the Mii maker from a menu of things to
customize. The stat engine (0.3.0) and the character list on the native headgear screen
(0.4.0) have run on the console (`evidence/2026-10-05_session1/`,
`evidence/2026-10-06_session2/`). **What 0.5.0 adds - the menu pages, greyed rows and literal
row text - is built and checked offline only and has never been loaded by the game.**
Design, proofs, log guide and console test plan of 0.5.0: `research/P11-MENU.md`. Earlier:
`research/P10-UI-SLICE.md` (0.4.0 UI), `research/P7-PRESET-ENGINE.md` (0.3.0 stat engine),
`research/P4-OVERRIDE-SLICE.md` (identity of a fighter), `research/P3-DIAG-PLUGIN.md`
(0.1.0), `research/P2-PLUGIN-SCAFFOLD.md` (0.0.1). Their packages under `builds/` are
unchanged.

## Editor UI ("mod mode")

Six more hooks, installed all or none after 6 site and 48 probe word compares, and not at
all when `sd:/ultimate/mii_customizer/ui_off` exists (the stat engine does not depend on
them):

| site | role |
|---|---|
| `0x180a030` edit-menu dispatcher | arms mod mode: exit value 7 (rewritten to 1) or value 1 with ZL/ZR held |
| `0x180abd0` headgear state | swaps the page's list in on the first tick, keeps the Mii's headgear untouched, reads the decision and restores everything on the last tick; for another page it undoes the state's pop and raises the state reader's restart byte |
| `0x328b5d0` "not in the item table" | 1 for an unavailable row while the row filler asks (greyed, cannot be decided), else 0 for our handles |
| `0x3288330` message key of a handle | the row's message label |
| `0x19cd100` `sort_id_list` | ignored while a list is open |
| `0x19ccb20` row filler | literal text for the rows of the main page |

Files read once at load, never written: `list.txt` (`mc_list 1`: which presets the
character pages show, with their message labels) and `menu.txt` (`mc_menu 1`):

```text
mc_menu 1
entry <id> <stats|slot> <text>     # one row of the main page, at most 48, at most one stats
label <id> <message_label>         # fallback label for that row
allow <id> <preset_name>           # that character is selectable on that slot's page
```

Without a usable `menu.txt` mod mode opens the character list directly, as 0.4.0 did. A
`stats` page sets or clears the edited Mii's preset (store updated, `loadouts.txt` saved).
On a `slot` page only the first row (the Mii's own class) and `allow`ed characters can be
decided; nothing is stored for a slot in this build. `sd:/ultimate/mii_customizer/text_off`
switches literal row text off (rows show their `label`, or `nam_mii_hat_unknown`).
Example: `builds/0.5.0-menu/example/menu.txt`.

## What it does

At load it reads two files once, then compares four instruction words at one site of the
13.0.4 `main` module with the audited values and installs a replace hook only if they
match:

| file / site | what | effect |
|---|---|---|
| `sd:/ultimate/mii_customizer/presets.txt` | presets: per fighter name, values for a set of param hashes | defines which hashes the hook reacts to |
| `sd:/ultimate/mii_customizer/loadouts.txt` | per saved-Mii ID: a preset name and/or explicit values | decides which Mii gets what |
| `0x4e53e0` | float-param thunk | may return a loadout value; log events `RQ`, `L3`, `OV`, `L4`, `L5`, `F5`, `X2` |

The 0.2.0 log-only hook on `0x4e53f0` is gone.

Per request (`x1` = param hash, `x2`):

1. `x1` is not a field hash of the preset file and not `weight` / `walk_speed_max`: tail
   jump to the original. This is the path of almost every request in the game: a bounded
   lookup in a 256-slot table built at load, 20 instructions when the hash's home slot is
   empty and 9 more per further examined slot (never more than `probe_max` slots, printed
   in the `L0|fields` line; 1 for a ten-field preset file). No call, no stack frame, no
   write, no lock.
2. Known hash, `x2 != 0`: counted (`x2nz=` in `L5`), then the same tail jump.
3. Known hash, `x2 == 0`: the original is called first. Its value is replaced only if all
   of this holds, re-checked on every request (nothing is cached):
   - `x0 != 0`; `[x0] == base + 0x4f89490`; `parent = [x0+8] != 0`; `[parent+0x50] == x0`;
   - the game says `parent` is the module accessor of a fighter whose kind is in
     `logic::ACCEPTED_KINDS` (Mii Gunner, 74) with an entry id `p` in 0..7 (`resolve` in
     `src/lib.rs`, pinned `skyline_smash` binding only);
   - the saved-fighter ID at `T + 0xe58 + p*0x240` (`T = 0x5307760`) is non-zero and the
     loadout file gives it a value for this hash: an explicit line if there is one,
     otherwise the value its preset has for the hash.

Anything else returns the original value: other objects, other fighters, unknown identity,
a Mii without a line, a preset without that field, no file, bad file. With no usable
loadout file no game function is called from the hook at all.

## Preset file, `mc_presets 1`

```text
mc_presets 1
# comment
fighter <name> <kind hash>
<field hash> <decimal value>
```

Generated from the user's own game file by `tools/stat-presets` (not part of this
package). First line exactly `mc_presets 1`. `<name>` is `[a-z0-9_]{1,31}`; hashes are
`0x` + 10 hex digits; values are plain decimals, finite, not range-limited. `#` comments,
blank lines, spaces or tabs, `\n` or `\r\n`. Limits: 512 KiB, 128 presets, 48 fields per
preset, 48 distinct field hashes in the file. A bad line is skipped and logged with its
line number (first 32); a `fighter` line that is rejected (bad name, bad hash, duplicate
name, 129th preset) takes its field lines with it (`skipped=`); a repeated field inside one
preset keeps the first value. A bad first line, an unreadable file or a file over the size
limit: no presets at all.

## Loadout file, `mc_loadouts 1` or `mc_loadouts 2`

```text
mc_loadouts 2
# comment
0000f589 preset fox
0000f589 weight 130.0
0000f58b walk_speed_max 1.6
```

Lines `<id: 8 hex digits> <key> <value>`. Keys: `preset <name>` (version 2 only; the name
must be in the preset file), `weight` 60.0..140.0, `walk_speed_max` 0.5..2.0 (ranges are
proposals from the first console test, not declared safe). An explicit line wins over the
preset for its one stat. ID `00000000` is invalid; at most 32 distinct IDs; a later line
for the same id+key replaces an earlier one. A bad line is ignored and logged (first 32).
A `preset` line with an unknown or malformed name is rejected and that Mii has no preset,
also when an earlier line gave it one. In a version 1 file `preset` is an unknown key. A
bad first line, an unreadable file or a file over 16 KiB switches all overrides off.
Example with a format description for hand editing:
`builds/0.3.0-presets/example/loadouts.txt`.

## Saving

`loadout::serialise` turns the in-memory loadout state into `mc_loadouts 2` text (per ID
its `preset` line, then its explicit lines; stable order; host-tested to read back as the
same state). `save_loadouts()` in `src/lib.rs`, exported as `mc_save_loadouts`, writes that
text to `loadouts.new`, reads it back, deletes `loadouts.txt` and renames the new file.
The editor UI calls it when a stats row is decided for a saved Mii (ran on the console in
session 2). Its power-loss behaviour is described at `save_locked`; at load a well-formed
`loadouts.new` is read when `loadouts.txt` does not exist (`loadout::load`).

## What it does not do

- No Lua, layout, message, save-file or asset change; it writes its log
  (`sd:/ultimate/mii_customizer_log.txt`, append) and `loadouts.txt`. Mod mode never
  changes the Mii: the headgear handle and the working record are compared with their
  values at the start of the visit whenever a page closes (`mc|UI|page`, `mc|UI|exit`).
- No `skyline::hook` macro (its expansion unwraps), no `unwrap`/`expect`/`panic!`, no
  thread, no mutex, no heap type in its own code. State is fixed-size statics and atomics.
- The identity lookup runs under a per-thread re-entry guard (thread pointer register,
  eight slots, never waits); a nested or surplus call returns the original value.
- The log gate is a try-lock taken after the original has returned; a busy gate drops the
  line and counts it.

## Layout

- `src/preset.rs` - preset file format, the preset table, the field-hash table. Pure.
- `src/loadout.rs` - loadout file format v1/v2, table, serialisation, lookup store and
  the resolution order. Pure.
- `src/logic.rs` - constants (accepted kinds, site, static tables), pointer guard,
  identity/decision logic, re-entry guard, formatting, seen-fighter table (logging only).
  Pure.
- `src/list.rs` - list file format. Pure.
- `src/menu.rs` - menu file format, and the pages: rows, availability, cursor and tick,
  what a finished page leads to. Pure.
- `src/ui.rs` - UI sites, probes and offsets, synthetic list handles, the mode state of a
  visit, the conditions for entering the headgear state again. Pure.
- `src/editor.rs` - the six UI hooks and the game calls they make.
- `src/lib.rs` - entry stub (assembly), `resolve`, the stat hook, logging, load,
  `save_loadouts`, hook installation.

The six pure files are unit-tested on the host, unchanged, by
`scratch/2026-10-06_P11-MENU/run_host_test.sh` (it also runs the 0.3.0 tests).

The hook target is a hand-written assembly stub that passes the return address as a
ninth argument. Do not replace it with an in-function read of x30: with
`opt-level = "z"` the outliner places a `bl` before such a read (observed in the first
0.1.0 build). `mc_param_impl` must stay free of anything that needs a stack frame;
`check_build.py` fails if its path for unknown hashes gains a call or a stack write.

## Build

```sh
# from the workspace root
bash mods/mii_customizer/build-plugin.sh          # offline; --online lets cargo fetch
bash mods/mii_customizer/scratch/2026-10-06_P11-MENU/run_host_test.sh
python mods/mii_customizer/scratch/2026-10-06_P11-MENU/mutation_control.py
python mods/mii_customizer/scratch/2026-10-06_P11-MENU/write_manifest.py
export PYTHONPATH=mods/ssbu_mod_new/builds/.cache/dk_cargo/python
python mods/mii_customizer/evidence/P11-MENU/check_p11_menu.py --selftest
```

Output `builds/0.5.0-menu/libmii_customizer.nro` + `MANIFEST.json` (written by
`write_manifest.py`); cargo target `builds/.cache/plugin-target/`; build log
`builds/.cache/build-0.5.0.log`. The build script never installs, runs or contacts a
console. The 0.3.0 scripts `check_build.py` / `mutation_control.sh` in
`scratch/2026-10-05_P7-PRESET-ENGINE/` belong to the 0.3.0 package and are not maintained
for later versions.

Dependencies, both git without `rev` in `Cargo.toml` and pinned by `Cargo.lock` (reason
in `Cargo.toml`): `skyline 0.6.0` `ultimate-research/skyline-rs`
`6b52d321275639f26c2371d8142550ba0013a5e4`; `skyline_smash 0.1.0`
`ultimate-research/skyline-smash` `315e4e8bebb460ebb9f02f30f07b0f13883ba3d6`.
Do not run `cargo update`.
