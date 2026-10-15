# P7-PRESET-ENGINE - plugin 0.3.0: character stat presets per saved Mii

Task: `prompts/P7-PRESET-ENGINE.md`. Date 2026-10-05. Worker: Claude Opus 5.5.
Status: **DONE** (built and checked offline; contract gaps and my readings of them are in
section 7 for the coordinator to accept or change).

Nothing here is runtime evidence. Plugin 0.3.0 has never been loaded by Skyline, never run
on a console or emulator, and is installed nowhere. **A** = console (gates 1 and 2 only),
**B** = measured offline in this task, **C** = read from pinned source, **D** = hypothesis.
Not READY: packaging, installation and the final test plan are the coordinator's.

Paths are relative to `mods/mii_customizer/` unless marked workspace-relative.

## Result in short

- `builds/0.3.0-presets/libmii_customizer.nro`, sha256
  `55a786b63681935d709e7f4375ccf951dbe279a938d8bf731019a7541ac800dc`, 65536 bytes, with
  `MANIFEST.json` and `example/loadouts.txt` (sha256 `5046aee4...d2d7`, 1904 bytes). A forced
  recompile gave the same NRO hash; 0 compiler warnings.
- One hook, `0x4e53e0`. The log-only hook on `0x4e53f0` and its stub are gone.
- A request is overridden only if: `x2 == 0`; the hash is a field hash of the loaded preset
  file or `weight` / `walk_speed_max`; the object is a fighter's work object (pointer guard
  and `resolve` exactly as in 0.2.0); the fighter's kind is in `logic::ACCEPTED_KINDS`
  (`[74]`); the saved-fighter ID of its player is non-zero and has, for that hash, an explicit
  line or a preset that contains the hash. Explicit beats preset beats the game's value.
- Every other hash leaves the hook after a bounded table lookup: 20 instructions when the
  hash's home slot is empty, 9 more per further examined slot, no call, no stack frame, no
  write (section 2).
- `loadout::serialise` and `save_loadouts()` are compiled in. **`save_loadouts()` is not
  called from anywhere in 0.3.0 and has never run**; that is by design of the prompt.
- Offline checks: host unit tests 47/47; mutation control 61 of 61 caught; binary and source
  check 98/98; image facts for the site 35/35 (0.2.0's script, rerun unchanged); the plugin's
  parser over the generated preset file: 94 presets, 10 field hashes, 940 values, 0 rejects,
  25 517 bytes, every value bit-identical to an independent reading.
- One thing to decide before installing (section 6, first item): the save function makes the
  NRO import three SDK file functions that 0.2.0 did not import.

## 1. Contracts as implemented

Sources: `plugin/src/preset.rs` (A, D), `plugin/src/loadout.rs` (B), `plugin/src/logic.rs`
(C), `plugin/src/lib.rs` (hook, load, log, save). The first three are pure and compiled
unchanged into the host tests.

### A. Preset file `sd:/ultimate/mii_customizer/presets.txt`

Read once at load into a static 512 KiB + 1 byte buffer, before the hook exists; never
written. Rules as in the prompt. Storage is fixed-size and atomics-only (no `unsafe`):
128 presets x (32-byte name, kind hash, 64-bit presence mask, 50 value slots).

Where the contract left room, and what I chose:

| point | choice |
|---|---|
| a rejected `fighter` line (bad name, bad hash, wrong field count, duplicate name, 129th preset) | the field lines that follow it belong to no preset: they are not stored and not merged into the previous preset. They are counted (`skipped=`), not logged one by one; the `fighter` line is the logged reject |
| a field repeated inside one preset | the second line is rejected (`dup_field`), the first value stays (same "first wins" as duplicate names) |
| field hash `0x0000000000` | rejected (`bad_hash`): 0 is the table's "empty" key, and a request with `x1 == 0` must never match |
| hex digits | either case; the prefix must be `0x` |
| encoding | the file is read as bytes. Everything the format means is ASCII, so a non-ASCII byte inside a comment is harmless and one inside a field makes that field invalid. (The loadout file keeps 0.2.0's stricter rule: a line that is not UTF-8 is rejected whole) |
| byte order mark | bad first line (`state=bad_version_line_bom`) |
| a preset with no field lines | a valid preset that changes nothing |
| 48 fields per preset vs 48 distinct hashes | both are tested. With "first wins" a preset reaches the per-preset limit only by holding 48 different fields; its 49th line is `too_many_fields` even if its hash is also new |
| do `weight` / `walk_speed_max` count toward the 48 distinct hashes | yes when the file uses them. The table of known hashes has 50 places: the two named keys (field index 0 and 1, always) plus up to 48 from the file |
| reject log | first 32 rejected lines with line number and reason; all are counted |
| value syntax | 0.2.0's own decimal parser (optional `-`, digits, optional `.` and digits, at most 18 digits, no exponent), so "finite" holds by construction; no range |

Reasons a line can have: `field_count`, `bad_name`, `bad_hash`, `dup_name`,
`too_many_presets`, `no_preset` (field line before any `fighter` line), `dup_field`,
`too_many_fields`, `too_many_hashes`, `bad_value`.

### B. Loadout file `sd:/ultimate/mii_customizer/loadouts.txt`

First line `mc_loadouts 1` or `mc_loadouts 2`, nothing else. 16 KiB limit, 32 IDs, ranges
and every other rule of 0.2.0 unchanged (the delivered 0.2.0 example file reads exactly as
before; host test). New: `<id> preset <name>` in version 2.

| point | choice |
|---|---|
| "a `preset` line naming an unknown preset is rejected and logged, and that Mii has no preset" | read literally: the line is rejected (`unknown_preset`) and an earlier valid `preset` line of the same ID is taken away as well (`cleared=` in the L0 line). Explicit values of that ID stay. An ID left with nothing is not in the table |
| a name that is not `[a-z0-9_]{1,31}` | `bad_name`, same effect as an unknown preset |
| several valid `preset` lines for one ID | the last one counts (0.2.0's replace rule, counted in `replaced=`) |
| `preset` in a version 1 file | `unknown_key` |
| preset file missing or refused | every `preset` line is `unknown_preset`; explicit lines still work |
| reject log | first 32 (0.2.0 logged 64) |

Resolution (`Store::resolve`, the only place that decides a value): for saved ID `i` and
field index `f`: an explicit value for (`i`, `f`) if `f` is one of the two named keys and
the value is inside its accepted range; otherwise, if `i` has a preset and the preset has
`f`, the preset value; otherwise nothing (the game's value). Preset values are not
range-limited, also for `weight` and `walk_speed_max`.

### C. Who gets it

Unchanged from 0.2.0: pointer guard, `resolve` (same six imports, same call order, checked
in the binary), re-entry guard, saved ID from `T + 0xe58 + p*0x240`, non-zero. The kind
test is `kinds.contains(&ident.kind)` with `logic::ACCEPTED_KINDS: [i32; 1] =
[KIND_MIIGUNNER]` (74, tier A from gate 2). Adding a kind is one array element. The L0 line
prints the binding's constant next to the array (`gunner_kind=74|accepted_kinds=74`).

### D. Which requests

`mc_param_impl` (hook target behind the unchanged assembly stub):

1. `PRESETS.fields.find(x1)` is `None` -> tail jump to the original.
2. Otherwise tail jump to `known_request` (same signature). There: `x2 != 0` -> three
   atomic updates (total, per field, first `x2` and return address per field), then the
   same tail jump to the original; nothing is logged on this path and no register the
   original reads is changed (checked in the binary). `x2 == 0` -> the original is called,
   then `param_event` decides and logs.

With no usable loadout file (or no accepted line) no game function is called from the hook,
as in 0.2.0 (`st=off`).

## 2. The hot path (B, from the disassembly of the staged NRO)

The table: 256 slots of 8 bytes, linear probing, no deletion, key 0 = empty; slot =
top 8 bits of `(h ^ (h >> 32)) * 0x9e3779b97f4a7c15`. Built at load, read-only afterwards.
`probe_max` is the longest probe sequence any stored key needed; a lookup never examines
more slots than that and stops at the first empty slot.

Cost of a request for a hash that is in no file (`evidence/P7-PRESET-ENGINE/05_nro_hook_disasm.txt`,
asserted by `check_build.py`):

| case | instructions in `mc_param_impl` | of which |
|---|---|---|
| home slot empty | 20 | 1 multiply, 4 loads (return address argument, probe bound, key, trampoline pointer), 2 compares-with-zero, 0 stores, 0 calls |
| each further examined slot | +9 | 1 load, 2 compares (key against 0, key against hash) |
| upper bound (every examined slot holds another key) | 17 + 9 x `probe_max` | `probe_max` <= 50 by construction (host test builds that worst case) |

Plus what the hook mechanism itself adds: the 8-instruction stub and the trampoline. For
the generated ten-field preset file `probe_max` is 1 (all ten hashes sit in their home
slot), so a miss is 20 instructions if the slot it probes is empty and 26 if it holds one
of the ten. The value is printed at load (`L0|fields|...|probe_max=`).

The first build had this lookup inside one large function; the compiler then saved four
registers and called two outlined fragments before the lookup on every request. Moving
everything else into `known_request` made the miss path frameless. `check_build.py` now
fails if that path gains a call, a stack write or an atomic update.

A request for a known hash costs what a `weight` request cost in 0.2.0 (identity through
six short game calls, no cache) plus a scan of the 64-slot log table. How often the ten
fields are requested per frame is not known; the `F5` counters of the first console log
will say (section 5.4).

## 3. Serialisation and `save_loadouts()`

`loadout::serialise(&Table, &Presets, &mut [u8])` writes `mc_loadouts 2`, then per ID in
table order its `preset` line and its explicit lines in key order. IDs are 8 lower-case hex
digits. A value is written as the shortest plain decimal that the plugin's own parser reads
back to the same bits (found by trying 0, 1, 2, ... fraction digits and re-parsing each; no
float formatting from std). Errors instead of bad text: `Overflow` (buffer or 16 KiB),
`Preset` (index without a name), `Number` (no such decimal within 18 digits; cannot happen
for values inside the two accepted ranges).

Host tests: `parse(serialise(x)) == x` for an empty table, hand-built tables, 3000 random
tables whose explicit values are arbitrary f32 inside the ranges, every table the two
parser fuzz tests produce (4000 inputs), and the largest possible table (32 IDs with
31-character preset names and both keys: under 8 KiB). Equality compares order, ID, preset
and value bits. The text is also a fixed point (`serialise(parse(text)) == text`).

`save_loadouts()` (`plugin/src/lib.rs`; exported as `mc_save_loadouts` so that it stays in
the NRO):

1. snapshot of the store -> text in a static 16 KiB buffer; the text is parsed again and
   must equal the snapshot, else nothing is written;
2. `File::create("sd:/ultimate/mii_customizer/loadouts.new")`, `write_all`, `sync_all`;
3. read `loadouts.new` back and compare with the text, else stop (the old file is intact);
4. `remove_file(loadouts.txt)` (a missing file is fine);
5. `rename(loadouts.new, loadouts.txt)`;
6. one `mc|SV|` log line with the step that ended it. A second caller during a save gets
   `busy` and never waits.

Why not "rename over the existing file": the std of this target implements `fs::rename`
with `nn::fs::RenameFile` and maps its result `0x402` to `AlreadyExists` (C: the toolchain's
own source, `library/std/src/sys/fs/switch.rs`, functions `rename` and the `r_try!` macro).
I took that as "does not replace"; it is not tested here.

Power loss, by moment:

| moment | on the card afterwards | next boot |
|---|---|---|
| before or during step 2 | old `loadouts.txt`; `loadouts.new` missing, empty or partial | old state. Safe |
| between 3 and 4 | old `loadouts.txt`; complete `loadouts.new` | old state. Safe; the new choice is lost |
| between 4 and 5 | no `loadouts.txt`; complete, verified `loadouts.new` | **all Miis vanilla** (no file = no overrides). Safe default, but the choice is not restored: 0.3.0 does not read `loadouts.new` |
| after 5 | new `loadouts.txt` | new state |

So it is safe in the sense "never a half-written `loadouts.txt`, never a wrong value", and
not safe in the sense "the saved choice survives": one window loses it until someone
renames the file by hand. Closing that window needs a reader rule ("if `loadouts.txt` is
absent and `loadouts.new` exists, read that"), which is a change to contract B and therefore
left to the coordinator. Whether a FAT/exFAT card can lose more than the file being changed
at a power cut is outside what this code controls.

Not exercised at all: the function at runtime, `File::create` on a path that already exists,
`sync_all`, `remove_file`, `rename` on this target.

## 4. Log reference

File and style unchanged: `sd:/ultimate/mii_customizer_log.txt`, append, `mc|<event>|seq=<n>`.
Hashes are printed as in the preset file (`0x` + 10 digits); the ten of the generated file:

| field index | hash | name |
|---|---|---|
| 0 | `0x0607cd5541` | `weight` |
| 1 | `0x0ee2ec2860` | `walk_speed_max` |
| 2 | `0x0d5aaabf9b` | `run_speed_max` |
| 3 | `0x0adec47ea3` | `dash_speed` |
| 4 | `0x1220fc2660` | `air_speed_x_stable` |
| 5 | `0x12ec5626fe` | `air_speed_y_stable` |
| 6 | `0x0ba18057d9` | `air_accel_y` |
| 7 | `0x0f71f4d4f8` | `air_accel_x_mul` |
| 8 | `0x06a0d82dad` | `jump_y` |
| 9 | `0x0cc9d2f2da` | `jump_speed_x` |

```
mc|L0|seq=0|mii_customizer 0.3.0-presets loaded|base=..|T=..|id_p0=..|special_p0=..|hook_param=..|gunner_kind=74|accepted_kinds=74|fighter_cat=0|entry_work_id=0x10000000
mc|L0|seq=1|presets|path=sd:/ultimate/mii_customizer/presets.txt|state=ok|bytes=25517|lines=1228|presets=94|hashes=10|field_lines=940|rejected=0|skipped=0
mc|L0|seq=..|presets_reject|line=7|reason=dup_name                      (first 32 rejected lines)
mc|L0|seq=2|fields|n=10|probe_max=1|0=0x0607cd5541|1=0x0ee2ec2860|2=0x0d5aaabf9b|...   (every hash the hook reacts to)
mc|L0|seq=3|loadout|path=sd:/ultimate/mii_customizer/loadouts.txt|state=ok|version=2|bytes=..|lines=..|accepted=1|preset_lines=1|replaced=0|rejected=0|cleared=0|ids=1|overrides=on
mc|L0|seq=..|loadout_reject|line=30|reason=unknown_preset               (first 32 rejected lines)
mc|LO|seq=4|id=0000f589|preset=fox|preset_fields=10|weight=-|walk_speed_max=-   (one per saved ID; `-` = no preset / no explicit value)
mc|L0|seq=..|presets|path=..|state=absent|os_error=-1                   (file missing; `loadout|...` likewise; `unreadable` for other errors)
mc|L0|seq=..|site=0x4e53e0|name=param|expected=..|found=..|match=1      (then installed=1|trampoline=..|after=..)
mc|L0|seq=..|load_done|base_ok=1
mc|RQ|seq=..|h=0x0d5aaabf9b|field=2|vt=1|parent=..|ra=0x..|orig=1.3700
mc|L3|seq=..|h=0x0d5aaabf9b|slot=0|x0=..|parent=..|ra=0x..|p=0|kind=74|id=0000f589|ov=1|orig=1.3700|v=2.4020|bits=0x4019ba5e|vt=1|st=ok|src=preset
mc|OV|seq=..|id=0000f589|h=0x0d5aaabf9b|src=preset|preset=fox|p=0|parent=..|orig=1.3700|new=2.4020|newbits=0x4019ba5e|ra=0x..
mc|L4|seq=..|parent=..|slot=0|kind=74|p=0|p0=0000f589:00000000|p1=0000f58b:02020202|...|p7=..
mc|L5|seq=..|req=..|x2nz=0|parents=2|parent_overflow=0|dropped=0|orig_null=0|st=ok:120,kind:40,noent:118|src=explicit:0,preset:120
mc|F5|seq=..|n=10|0x0607cd5541=31/12/0|0x0ee2ec2860=20/9/0|...          (per hash: requests with x2 == 0 / overridden / requests with x2 != 0)
mc|X2|seq=..|h=0x0ba18057d9|x2=0x1|ra=0x..|passed_through=1
mc|SV|seq=..|result=ok|step=0|bytes=..|os_error=0                       (never written by 0.3.0: nothing calls the save)
```

| event | when | bound per boot |
|---|---|---|
| `L0`, `LO` | load | fixed + 32 + 32 reject lines + 32 `LO` |
| `RQ` | the first `x2 == 0` request of each known hash, from any object | 50 |
| `L3` | the first request of a hash for one fighter (see below), at most 16 hashes per fighter | 64 x 16 |
| `OV` | the first applied override per (saved ID, hash) | 32 x 50 |
| `L4` | each new fighter, with all eight ID slots | 64 |
| `L5`, `F5` | with each `L4`, and when the request count reaches 600, 1200, 2400, ... (doubling) | 64 + about 20 |
| `X2` | the first `x2 != 0` request of each known hash; written later, from a request that may log | 50 |

"One fighter" in `L3`/`L4` is the parent address together with what was resolved about it
(kind, player, saved ID): `logic::seen_key`. A parent address reused by another fighter in
a later match, or an identity that resolves only after the first requests, gets its own
`L4` and its own first lines. The table is logging state only; `decide` cannot see it.

`L3` fields: `v`/`bits` what the caller received, `orig` what the game returned, `p` entry
id (-1 unknown), `kind` (-1 unknown), `id` the slot ID that was read (`00000000` when none
was read), `ov`, `vt` (1 = `0x4f89490`, 2 = `0x4f73738`, 0 = other), `st` (reasons as in
0.2.0: `ok off vt nopar back reent gfull cat rt cat2 kindx entx entr kind noid noent`),
`src=explicit|preset|-`, `ra` the module-relative return address of the caller.

## 5. For the coordinator's test plan

Decisions that depend on a console run and that offline work cannot settle: which of the
ten fields the engine asks for through `0x4e53e0` with `x2 == 0` at all; whether the values
returned there drive running, jumping, falling and air movement; whether ten per-frame
candidates through the uncached identity path cost anything noticeable; whether the plugin
loads with its three new SDK imports (section 6).

### 5.1 Presets to use

Compared with the vanilla Gunner the two presets should differ in opposite directions in
as many of the ten fields as possible. From the generated file (B; these few numbers are
the values the log will show):

| field | Gunner (game) | `fox` | `purin` (Jigglypuff) | what to look at |
|---|---|---|---|---|
| `weight` | 104 | 77 | 68 | how far a throw sends them |
| `walk_speed_max` | 1.0 | 1.523 | 0.735 | walking side by side |
| `run_speed_max` | 1.37 | 2.402 | 1.271 | running across the stage |
| `dash_speed` | 1.63 | 2.09 | 1.65 | the first step of a dash |
| `air_speed_x_stable` | 0.93 | 1.11 | 1.332 | sideways drift in the air |
| `air_speed_y_stable` | 1.45 | 2.10 | 0.98 | fall speed |
| `air_accel_y` | 0.098 | 0.23 | 0.053 | how quickly the fall builds up |
| `air_accel_x_mul` | 0.043 | 0.08 | 0.08 | how quickly air drift builds up |
| `jump_y` | 30.9 | 35.0 | 19.79 | jump height |
| `jump_speed_x` | 0.95 | 0.68 | 0.70 | sideways speed of a running jump |

`fox` is the "fast, light, falls like a stone" preset; `purin` is the "slow on the ground,
floats, low jump" one. Between them fall speed differs 2.1 times, gravity 4.3 times, run
speed 1.9 times, jump height value 1.8 times, and the vanilla Gunner lies between the two
in walk speed, run speed, fall speed, gravity and jump height, so B is a usable middle
reference for those. Their weights are both low (and both air-drift values are above the
Gunner's), so the second boot adds the explicit line `weight 130.0` on top of `purin`:
that gives the weight contrast (130 against `fox`'s 77) and tests "explicit wins over
preset" in the same run. If a heavy and slow real fighter is preferred instead of the
explicit line, `gaogaen` (Incineroar: weight 116, walk 0.62, run 1.18, the slowest ground
values in the file) is the alternative; its air values are close to the Gunner's.

The copied numbers are only numbers: whether a Gunner with them moves like that fighter is
what the test shows, and stats outside the ten (double-jump height, short hop, fast-fall
speed, ground friction, air friction and more) stay the Gunner's.

### 5.2 Install (coordinator) and files

- NRO: `builds/0.3.0-presets/libmii_customizer.nro` replaces 0.2.0.
- `sd:/ultimate/mii_customizer/presets.txt`: workspace
  `gamedata/mii_customizer/P6-PRESET-DATA/presets.txt` (sha256 `f6acbba1...5c0d`, 25 517 bytes).
- `sd:/ultimate/mii_customizer/loadouts.txt`, boot 1: the delivered example with the
  placeholder replaced: `0000f589 preset fox`. No line for `0000f58b`.
- Boot 2 file, prepared next to it as `loadouts_boot2.txt`:
  `mc_loadouts 2` / `0000f589 preset purin` / `0000f589 weight 130.0` / `0000f58b preset fox`.

### 5.3 User steps (10)

All matches: 2 players, 2 controllers, stock, no items, Final Destination, hazards off.

1. Delete `sd:/ultimate/mii_customizer_log.txt` if present. Boot to the main menu.
2. **Match 1.** P1 = Gunner A (0000f589), P2 = Gunner B (0000f58b). Ground: stand both on
   the same spot; walk both the same way; then dash and keep running both the same way
   across the stage. Do each twice.
3. Same match, air: both full-hop at the same moment and do nothing (who goes higher, who
   lands first); both full-hop while holding the stick toward the other (who drifts
   further); one running jump each; one double jump each. Then B grabs A and up-throws
   once, A grabs B and up-throws once, both near 0 %.
4. Quit. Write down for A against B: walk, run, jump height, fall, drift, throw height.
5. **Match 2, ports swapped.** P1 = Gunner B, P2 = Gunner A. Run once, full-hop once. Quit.
6. **Match 3, control.** P1 = Mario, P2 = Kirby. Run, full-hop, 20 seconds. Quit, close the
   game, copy the log as `log_boot1.txt`.
7. With the console off (or the card in the PC): rename `loadouts.txt` to
   `loadouts_boot1.txt` and `loadouts_boot2.txt` to `loadouts.txt`. Delete the log. Boot.
8. **Match 4.** P1 = Gunner A, P2 = Gunner B. Repeat steps 2 and 3 completely.
9. **Match 5, control.** P1 = Mario, P2 = Gunner B. Run and full-hop both, 20 seconds. Quit.
10. Close the game, copy the log as `log_boot2.txt`. If anything crashed or froze: note the
    step and copy the newest file in `atmosphere/crash_reports/` too.

The control match is the last one of each boot on purpose: the `F5` line written when its
fighters appear contains the counts of everything played before it.

Expected feel (D until tested): boot 1, A walks and runs clearly faster than B, falls
faster, is thrown higher (77 against 104). Boot 2, A floats (slow fall, low jump, more
drift), is slower on the ground than B, and is thrown clearly less high than B (explicit
130 against `fox`'s 77); B now moves as A did in boot 1. Mario, Kirby normal in both.

### 5.4 Which log lines prove what

Read `L3` lines by `parent` + `id`: one such pair is one fighter in one match. There are
at most ten `L3` lines per fighter with the generated file, one per hash.

| claim | lines that show it |
|---|---|
| plugin and both files loaded | `L0`: `0.3.0-presets loaded`, `accepted_kinds=74`; `presets\|...\|state=ok\|...\|presets=94\|hashes=10\|field_lines=940\|rejected=0\|skipped=0`; `fields\|n=10\|probe_max=1\|...`; `loadout\|...\|state=ok\|version=2\|...\|rejected=0`; `site=0x4e53e0 ... match=1`, `installed=1`; no line mentioning `0x4e53f0` |
| who has what | boot 1: one `LO` line, `id=0000f589\|preset=fox\|preset_fields=10\|weight=-\|walk_speed_max=-`. Boot 2: `id=0000f589\|preset=purin\|preset_fields=10\|weight=130.0000\|walk_speed_max=-` and `id=0000f58b\|preset=fox\|...` |
| **a field was requested through the hook** | an `RQ` line with its hash (first request by any object, with the caller's `ra`), and an `L3` line with its hash for the fighter in question; in `F5` the first number after `<hash>=` is above 0 |
| **it was overridden from the preset** | `L3` with `id=0000f589\|ov=1\|orig=<Gunner value>\|v=<preset value>\|st=ok\|src=preset` (values: table 5.1), and one `OV` line `id=0000f589\|h=<hash>\|src=preset\|preset=fox` per hash; in `F5` the second number is above 0. Ten hashes -> ten `OV` lines per ID if all ten are requested |
| explicit wins over preset | boot 2: `L3` and `OV` for `h=0x0607cd5541` with `id=0000f589`: `v=130.0000\|src=explicit` (the preset alone would give 68); the other nine hashes `src=preset\|preset=purin` |
| the override follows the saved Mii, not the port | match 2: the `L3` lines with `id=0000f589` have `p=1` and are still `ov=1` |
| **left alone for B** | boot 1: every `L3` with `id=0000f58b` has `ov=0\|st=noent\|src=-` and `v` equal to `orig`; no `OV` line with `id=0000f58b` in `log_boot1.txt` |
| **left alone for non-Mii fighters** | matches 3 and 5: every `L3` whose `kind` is not 74 has `ov=0\|st=kind\|src=-`, `v` equal to `orig`; `L5 st=` gains `kind:<n>` |
| stale slot (open since gate 2) | match 5: the `L4` line of Mario's fighter shows whether slot `p0` still holds `0000f589` from match 4. Either way Mario's lines must be `st=kind` |
| totals sane | last `L5`: `dropped=0`, `orig_null=0`, no `reent`, no `gfull`, `parent_overflow=0`; `src=explicit:<n>` is 0 in boot 1 |
| `x2` | `L5 x2nz=0` and no `X2` line: none of the known hashes was ever requested with `x2 != 0`. Otherwise each `X2` line gives hash, the `x2` value and the caller; those requests were passed through unchanged |

**Which of the ten fields were never requested through `0x4e53e0` with `x2 == 0`.** Take the
last `F5` line of each boot (written when the control match starts, so it covers all Gunner
play of that boot):

- `<hash>=0/0/0` in both boots, and no `RQ` line with that hash in either log: the engine
  never asked for that field through this function while the user played. This mechanism
  cannot cover that stat; it is read some other way (P4-STAT-SITES lists direct-call sites
  for all ten).
- `<hash>=0/0/N` with N above 0 (and an `X2` line): it is requested, but only with
  `x2 != 0`, which contract D passes through. That would be a contract question, not a dead
  end.
- First number above 0 but no `L3` line with `kind=74` for that hash: it is requested, but
  not from the Gunners' work objects (look at `vt` and `st` of the `RQ` line and of the
  `L3` lines that do exist for it).
- Requested and overridden (`OV` present) but no difference in play: the value that drives
  that behaviour comes from another read (compare the `ra` of the `ov=1` line with the
  P4-STAT-SITES tables), or it is taken once before the identity resolves (then the first
  `L3` line of that fighter for the hash shows `st=rt` or `st=off` and a later one `ok`).

`F5` is only as fresh as the last new fighter or doubling threshold; `RQ` lines are written
at the moment of the first request and are the definitive "was ever requested" record.

### 5.5 Failure patterns added by 0.3.0 (those of P4-OVERRIDE-SLICE 4.4 still apply)

| pattern | meaning |
|---|---|
| no `mc\|` line at all, other plugins fine | the NRO did not load: first suspect is one of the three new imports (section 6). Roll back to 0.2.0 |
| `presets\|...\|state=absent` or `unreadable` with the file on the card | path or SD problem; `os_error` is -1 for "not found". All `preset` lines are then `unknown_preset` and nobody is changed |
| `presets\|...\|state=too_large` / `bad_version_line` | the file is not the generated one |
| `loadout_reject\|...\|reason=unknown_preset` | name not in `presets.txt` (the placeholder was not replaced, or a typo); that Mii is vanilla |
| every `L3` has `p=-1\|kind=-1\|st=off` | no accepted loadout line; nothing is resolved or changed |
| `L3` lines of a Gunner show `ov=1` for some hashes and `ov=0\|st=noent` for others | the preset does not contain those hashes (not possible with the generated file: `preset_fields=10`) |
| frame drops while Gunners are on screen, none in the Mario/Kirby match | cost of the uncached identity path at the request rate `F5` shows; then a per-frame cache keyed by parent needs designing |
| frame drops also without Gunners | cost of the known-hash path for non-fighters or of logging; compare `req=` in `L5` over time |
| crash at boot after the `presets` line | parsing or the 598 KiB of zero-initialised statics; the last `L0` line names the step reached |

Rollback: put the 0.2.0 NRO back (it ignores `presets.txt`; a version 2 loadout file is a
bad first line for it, so restore the version 1 file too) or remove the plugin; delete
`sd:/ultimate/mii_customizer/`. 0.3.0 writes nothing but its log.

## 6. Not verified

- **Three new SDK imports.** Because `save_loadouts` is compiled in, the NRO now imports
  `nn::fs::DeleteFile`, `nn::fs::RenameFile` and `nn::fs::RenameDirectory` (the last because
  std's `rename` contains both branches), which 0.2.0 did not. What I could establish (B):
  the 13.0.4 `main` module itself imports `DeleteFile`, so the SDK exports that one; an
  ARCropolis NRO in the workspace's emulator folder
  (workspace `testenv/ryujinx/data/sdcard/.../skyline/plugins/libarcropolis.nro`, sha256
  `92171b2f...9a1c`) imports all three. Not established: that the card's ARCropolis is that
  build, and what Skyline does with a plugin whose import cannot be resolved. If the
  coordinator has the card's plugin files, searching one for the two `Rename` symbol names
  settles it without a console session. If not, the first boot of the test settles it
  (failure = no `mc|` line).
- Anything at runtime: loading, the hook, the stub with the new two-function split, both
  file reads (a 25 KiB file and `std::fs::metadata`, neither used by 0.2.0), the parse at
  boot, about 598 KiB of zeroed static memory, the cost per request.
- That the engine requests any of the eight new fields through `0x4e53e0`, with `x2 == 0`,
  from the fighter's work object; that the values returned there drive behaviour. Gate 2
  showed this for `weight` and `walk_speed_max` only.
- That `x2` is 0 for these requests. P4-STAT-SITES found an `x2` register move at a few
  call sites (`walk_speed_max` 1, `air_accel_y` 3, `jump_speed_x` 2); what is in the
  register is unknown. Such requests are passed through and reported.
- `save_loadouts` and everything in section 3 that concerns the card.
- How this target reports a missing file. From the toolchain source (C): `File::open` of a
  missing file returns a generic error, not `NotFound`, which is why 0.3.0 asks
  `fs::metadata` first; 0.2.0 would have logged `unreadable` for a missing file.
- Presets for kinds that are not selectable characters (`miienemy*`, `koopag`, ...) load like
  any other; filtering is the UI's or the generator's business.
- CPU players, more than two players, other modes, Ice-Climbers-style pairs: as in 0.2.0.
- A cold-tree rebuild; the emulator was not used.

## 7. Deviations, gaps and readings for review

1. Contract A and B choices where the text was open: tables in section 1. The two that
   reject more than a lenient reading would: field hash 0, and a repeated field inside one
   preset. The one that goes further than a minimal reading: an unknown `preset` line also
   removes an earlier valid one of the same ID.
2. Field lines of a rejected `fighter` line are counted (`skipped=`), not listed, so that
   one bad `fighter` line does not use up the 32 logged rejects with its ten fields.
3. Logging differs from the letter of the prompt in four bounded ways:
   (a) `L3` "first line per (parent, field hash)" is per (parent **and identity**, field
   hash), with 64 remembered fighters instead of 32 parents. Reason: with parent alone, a
   later fighter at a reused address would produce no lines, and the test's "left alone for
   B / for non-Mii" evidence would depend on the allocator. The `chg` lines of 0.2.0 are
   gone.
   (b) `L5` is not written every 600th request but at 600, 1200, 2400, ... and with each
   `L4`. Reason: ten fields, some probably asked every frame, would otherwise mean a file
   append on the game thread every few seconds for the whole session.
   (c) Added, bounded: `RQ` (once per hash), `F5` (with each `L5`), `X2` (once per hash),
   `SV` (only from the save, so never in 0.3.0). `RQ` and `F5` exist to answer the
   "never requested" question definitively.
   (d) `L4` additionally shows `kind` and `p`.
4. A missing file is now detected with `fs::metadata` before `File::open` (section 6).
5. `MC_SITES` has one record; `mc_save_loadouts` is a new exported symbol. No other export
   changed.
6. No runtime writer of the store exists yet. The store is atomics-only so that the UI task
   can add one (`set preset of ID`), but its interaction with a concurrent `resolve` and
   with `OV` marks is not designed.
7. `scratch/2026-10-04_P4-OVERRIDE-SLICE/check_build.py` and `host_test.rs` (not edited)
   describe 0.2.0 and no longer match the crate; the 0.2.0 NRO is unchanged. `step0.py`
   there is still valid for the site and was rerun.
8. Out of scope, suggested: (a) decide the `loadouts.new` reader rule before the UI calls
   the save; (b) a kb note that this target's `fs::rename` does not replace and `File::open`
   reports a missing file as a generic error (toolchain source,
   `library/std/src/sys/fs/switch.rs`); (c) `STATUS.md` still says P7 has no report.

## 8. Build and offline checks

All commands from the workspace root. Image: workspace `gamedata/ssbu-13.0.4/main.bin`,
sha256 `f70c97d2...7613`.

| check | command | result | output |
|---|---|---|---|
| image facts, site `0x4e53e0` | `python mods/mii_customizer/scratch/2026-10-04_P4-OVERRIDE-SLICE/step0.py` | 35 passed, 0 failed | `evidence/P7-PRESET-ENGINE/01_step0_rerun.txt` |
| host unit tests | `bash mods/mii_customizer/scratch/2026-10-05_P7-PRESET-ENGINE/run_host_test.sh` | 47 passed, 0 failed | `.../02_host_test.txt` |
| mutation control | `bash .../mutation_control.sh` | 61 caught, 0 missed | `.../02b_mutation_control.txt` |
| build | `bash mods/mii_customizer/build-plugin.sh` | exit 0, 0 warnings, same hash after a forced recompile | `.../06_*` |
| binary + source | `python .../check_build.py --write-manifest` | 98 passed, 0 failed | `.../03_check_build.txt` |
| generated preset file | `python .../check_real_presets.py` | 8 passed, 0 failed | `.../04_real_preset_file.txt` |
| hook disassembly | `python .../dis_hook.py 44` | listing | `.../05_nro_hook_disasm.txt` |

- **Host tests** (`preset.rs`, `loadout.rs`, `logic.rs` unchanged). Preset parser: every
  contract constant; 16 wrong first lines, BOM; 512 KiB / 512 KiB + 1; names (31 ok, 32 and
  six other forms rejected); kind and field hash forms; field counts; a rejected `fighter`
  line not leaking into the previous preset; duplicate names; field before any `fighter`;
  repeated field; 128 / 130 presets; 48 / 49 distinct hashes with and without the named keys;
  18 malformed values, negative, zero and large values accepted; bounded reject log; 3000
  random inputs with invariants. Hash table: empty table, hash 0, the ten real hashes
  against 200 000 random 40-bit values, 50 hashes forced into one slot (`probe_max` 50, all
  found, an absent one with the same slot not found, 51st refused), a cluster wrapping the
  table end, two hashes equal in their low 32 bits. Loadout parser: 0.2.0's tests for both
  versions, the 0.2.0 example file, the delivered 0.3.0 example with and without the
  placeholder, `preset` in version 1 and 2, unknown / malformed names, clearing, 18 wrong
  first lines, size limit, 32 IDs mixing both line kinds, bounded reject log, 4000 random
  inputs. Resolution order for four IDs across explicit / preset / partial preset / nothing.
  Store publish, snapshot, once-per-(ID, field) marks, ID 0. `decide` with the kind list
  (one kind, two kinds, none). Serialisation: section 3. Unchanged from 0.2.0: pointer guard,
  `identify`, re-entry guard with six threads. Logging: the seen-fighter table, the `L5`
  schedule, formatting.
- **Mutation control.** 61 single-line weakenings of the three pure files (every limit and
  constant of contracts A and B, each rejection rule, the table lookup, the resolution
  order, serialisation, equality, the kind test, the identity rules, the logging bounds)
  each make at least one test fail. The first run missed two ("lookup compares only the
  low 32 bits", "ID 0 can have a loadout"); two tests were added and the full run repeated.
- **Binary.** One site record, none for `0x4e53f0`, and its four instruction words nowhere
  in the file; the six game imports of 0.2.0 and no other game symbol; the stub unchanged
  since 0.1.0; the miss path as in section 2 (instruction counts asserted); the known-hash
  path tests `x2` before the original and writes no argument register before it; `resolve`
  as in 0.2.0; `mc_save_loadouts` exported, with no `bl`/`b` to it and its address stored
  nowhere but its symbol entry; file creation, removal and rename only inside `save_locked`
  in the source; locked dependencies identical to 0.2.0's manifest.
- **Generated preset file.** Workspace `gamedata/mii_customizer/P6-PRESET-DATA/presets.txt`
  exists: 25 517 bytes, sha256 `f6acbba17d510aae0f0a2cc49cc5417287d4f0d0a8428dbf52d3ca4505865c0d`.
  The plugin's parser (host build): `state=ok`, 1228 lines, **94 presets, 10 distinct field
  hashes, 940 field lines, 0 rejected, 0 skipped**, 10 fields in every preset, longest name
  12, `probe_max=1`. All 940 stored values have the bits of the correctly rounded decimal
  (independent Python reading). The file was not copied anywhere.
- **Synthetic test data.** `scratch/2026-10-05_P7-PRESET-ENGINE/synthetic_presets.txt`: three
  presets named `zz_synth_*` with invented round numbers and made-up kind hashes.

Not covered by any offline check: everything in section 6.

## Closing summary

- **Task ID:** P7-PRESET-ENGINE
- **Status:** DONE
- **Changed files:**
  - `plugin/Cargo.toml`, `plugin/Cargo.lock` (version 0.3.0 only), `plugin/src/lib.rs`
    (rewritten), `plugin/src/logic.rs` (reworked), `plugin/src/loadout.rs` (reworked: v2,
    serialisation, resolution), `plugin/src/preset.rs` (new), `plugin/README.md` (rewritten)
  - `build-plugin.sh` (variant mapping: 0.2.x `override`, from 0.3.0 `presets`)
  - `builds/0.3.0-presets/libmii_customizer.nro`, `MANIFEST.json`, `example/loadouts.txt` (new)
  - `builds/.cache/`: `build-0.3.0.log`, `host-test/host_test_p7.exe`,
    `host-test/preset_report_p7.exe`, `plugin-target/` (updated)
  - `research/P7-PRESET-ENGINE.md` (this file)
  - `evidence/P7-PRESET-ENGINE/`: `01_step0_rerun.txt`, `02_host_test.txt`,
    `02b_mutation_control.txt`, `03_check_build.txt`, `04_real_preset_file.txt`,
    `05_nro_hook_disasm.txt`, `06_build-0.3.0.log`, `06_build-0.3.0.stdout.txt`,
    `06_build-0.3.0-recompile.stdout.txt`
  - `scratch/2026-10-05_P7-PRESET-ENGINE/`: `host_test.rs`, `run_host_test.sh`,
    `mutation_control.sh`, `check_build.py`, `check_real_presets.py`, `preset_report.rs`,
    `dis_hook.py`, `synthetic_presets.txt`
- **Observed checks:** image facts 35/35; host tests 47/47; mutation control 61/61 caught;
  build exit 0, 0 warnings, hash reproduced; binary/source check 98/98; generated preset
  file 8/8 (94 presets, 10 hashes, 940 values, 0 rejects, 25 517 bytes).
- **Not touched:** `STATUS.md`, `CURRENT_INSTALL.md`, `CHANGELOG.md`, `kb/`, `tools/`,
  `mods/ssbu_mod_new` (read only), the toolchain and cargo checkouts (read only), other
  workers' files, workspace `gamedata/` (read only), SD card, emulator. No commits,
  branches, agents or installs.
- **Could not verify:** section 6. In one line: nothing at runtime; whether the NRO loads
  with the three new file-function imports; whether the eight new fields are requested
  through this hook and act on the game; `save_loadouts` in any form.
