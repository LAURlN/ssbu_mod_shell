# P4-OVERRIDE-SLICE - plugin 0.2.0: per-saved-Mii stat override from a mod-owned file

Task: `prompts/P4-OVERRIDE-SLICE.md`. Date 2026-10-05. Worker: Claude Opus 5.5.
Status: **DONE** (built and checked offline; one narrow deviation from the identity rule,
section 1.2, for the coordinator to accept or reject).

Nothing here is runtime evidence. The plugin has never been loaded by Skyline, never run on a
console or emulator, and is installed nowhere. **A** = console (gate 1 only), **B** = measured
offline in this task, **C** = read from pinned source, **D** = hypothesis. Not READY; packaging,
installation and the final test plan are the coordinator's.

Paths are relative to `mods/mii_customizer/` unless marked workspace-relative.

## Result in short

- `builds/0.2.0-override/libmii_customizer.nro`, sha256
  `4477dc9acdbef341638a89174df5f2b8946125e0cfa24f10358cc8ad4abf59c9`, 53248 bytes, with
  `MANIFEST.json` and `example/loadouts.txt` (sha256 `4c2ae058267e...3ea1`). Two further
  recompiles gave the same NRO hash.
- One value-changing hook (`0x4e53e0`) and one log-only hook (`0x4e53f0`). The 0.1.0 hooks at
  `0x179e440` and `0x17c8210` are gone.
- A request is overridden only if: hash is `weight` or `walk_speed_max`; the object has vtable
  `0x4f89490` with a parent that points back to it; the game reports that parent as the module
  accessor of a fighter of kind Mii Gunner with entry id `p` in 0..7; the saved-fighter ID in
  player slot `p` is non-zero and has a value for that key in the loadout file. Anything else
  returns the original value. Nothing is cached between requests.
- "Which parent is which player" is answered in the code by the game's own functions (entry id,
  two independent sources that must agree) and printed in every L3 line as `p=`. Whether entry
  id `p` is the index of the saved-Mii slot table is the one mapping question the console test
  still has to confirm; the log is built to show it either way (section 4).
- Offline checks: image facts 35/35, binary and source 69/69, host unit tests 25/25, and 17 of
  17 deliberate mutations of the pure code are caught by those tests.

## 1. Identity: functions and constants, and where they are declared

Dependency added: `skyline_smash 0.1.0`, git `https://github.com/ultimate-research/skyline-smash`,
revision `315e4e8bebb460ebb9f02f30f07b0f13883ba3d6` (lib name `smash`), feature `weak_l2cvalue`
as in the reference plugin. Source read in the local cargo checkout of that revision (C).

### 1.1 What is used

| item | declared in `skyline-smash@315e4e8` | kind | 13.0.4 image (B) |
|---|---|---|---|
| `app::BattleObjectModuleAccessor { vtable: u64, battle_object_id: u32 }` | `src/cpp.rs:387-390` | struct | `get_kind` itself does `ldr w0,[x0,#8]` on its accessor argument |
| `app::utility::get_category(&mut accessor) -> i32` | `src/cpp.rs:1769-1771` | binding inline: `(battle_object_id >> 28) as u8` | the game's `app::utility::get_category(uint)` at `0x15cdfe0` is `lsr w0,w0,#0x1c; ret` |
| `app::sv_battle_object::module_accessor(id)` | `src/cpp.rs:20597-20598`, `_ZN3app16sv_battle_object15module_accessorEj` | exported | `0x2283700`: object lookup, returns `[obj+0x20]` |
| `app::sv_battle_object::category(id)` | `src/cpp.rs:20545-20546`, `..8categoryEj` | exported | `0x22835d0`: `[obj+8] >> 28` |
| `app::sv_battle_object::kind(id)` | `src/cpp.rs:20601-20602`, `..4kindEj` | exported | `0x2283540`: `[obj+0xc]` |
| `app::sv_battle_object::entry_id(id)` | `src/cpp.rs:20613-20614`, `..8entry_idEj` | exported | `0x2284020`: `[obj+0x10]` |
| `app::utility::get_kind(&mut accessor)` | `src/cpp.rs:1774-1775`, `_ZN3app7utility8get_kindEPKNS_26BattleObjectModuleAccessorE` | exported | `0x15cdff0`: null check, id from `[x0+8]`, lookup, `[obj+0xc]` or -1 |
| `app::lua_bind::WorkModule::get_int(accessor, int)` | `src/cpp.rs:11109-11113`, `_ZN3app8lua_bind24WorkModule__get_int_implEPNS_26BattleObjectModuleAccessorEi` | exported | `0x208dbc0`: `ldr x0,[x0,#0x50]; ldr x8,[x0]; ldr x2,[x8,#0x98]; br x2` |
| `lib::lua_const::BATTLE_OBJECT_CATEGORY_FIGHTER` = `0x0` | `src/lua_const.rs:506` | constant | - |
| `lib::lua_const::FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID` = `0x10000000` | `src/lua_const.rs:6610` | constant | exported `FighterUtil::is_valid_entry_id` (`0x6946c0`) reads exactly this id through `[accessor+0x50]` slot `+0x98` and compares with -1 |
| `lib::lua_const::FIGHTER_KIND_MIIGUNNER` = `0x4A` | `src/lua_const.rs:7251` | constant | **not corroborated offline (C only)**; L0 prints it, L3 prints the kind the game returns |

The NRO imports exactly these six game symbols and no other (`check_build.py`); all six are in
the dynamic symbol table of the 13.0.4 image (`step0.py`). `get_category` is not an import: it
is the binding's inline function and compiles to a load of `[accessor+8]` and a shift.

### 1.2 How they are combined (`resolve` in `plugin/src/lib.rs`), and the one deviation

Called only after condition 1 passed (vtable, non-null parent, back-pointer), with
`accessor = parent`:

1. `cat = utility::get_category(accessor)`; must equal `BATTLE_OBJECT_CATEGORY_FIGHTER`.
   Otherwise stop: **no game function is called for a non-fighter parent.**
2. `id = accessor.battle_object_id`; `sv_battle_object::module_accessor(id)` must return this
   very `parent`. This proves, through an exported function, that the value read at `+8` is
   the id of a registered object whose module accessor is `parent`.
3. `sv_battle_object::category(id)` must be the fighter category (exported confirmation of 1).
4. `kind_o = sv_battle_object::kind(id)`, `entry_o = sv_battle_object::entry_id(id)`,
   `kind_a = utility::get_kind(accessor)`,
   `entry_a = WorkModule::get_int(accessor, FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID)`.
   Required: `kind_a == kind_o`, `entry_a == entry_o`, `0 <= entry <= 7`.
5. Outside `resolve`: `kind == FIGHTER_KIND_MIIGUNNER`.

So kind and entry id each come from two exported functions (one taking `parent` as the module
accessor, one taking the object id) that must agree; the functions taking the accessor are
called last, after the object registered under the id is shown to be a fighter with this
accessor. The compiled order is the same (`evidence/P4-OVERRIDE-SLICE/05_nro_resolve_disasm.txt`,
asserted by `check_build.py`).

**Deviation from "ONLY through exported game functions".** The pinned binding has no exported
function that takes a module accessor and returns its category or its object id. The category
by accessor (step 1) and the id itself (step 2) therefore come from the binding's declared
struct field `battle_object_id`, via the binding's own `get_category` and one field read. That
is not a guessed offset: the binding declares it (C), the exported `get_kind` reads the same
`[x0+8]` as its object id (B), and step 2 checks it at runtime through an exported function,
so a wrong offset gives vanilla, not a wrong fighter. Category is then confirmed by the
exported `sv_battle_object::category`.

The strictly exported alternative was analysed and not used: `app::fighter::get_id_from_entry_id(p)`
(`src/cpp.rs:243-244`, `0x15ce250`) would give the id from the entry id without the field.
Reasons against (B, from its instructions): it dereferences the `FighterManager` singleton
pointer at `0x52b84f8` without a null check, and the binding declares no symbol to test that
pointer; it branches to an abort import for `p >= 8`; it makes a virtual call (slot `+0x518`)
on the fighter object whose meaning is unknown and which decides whether an id is returned at
all. The field route needs none of that. If the coordinator wants the strict form anyway, it is
a change of two lines in `resolve` plus a seventh import; I would not ship it without a console
log showing `0x52b84f8` handling first.

### 1.3 Why these calls are safe to make from inside the hook (B unless marked)

- The object lookup `0x3ac560` used by all five id/accessor functions is pure reads: category
  switch, index bound check, compare of the stored id with the requested one, null otherwise
  (ids with category above 4 give null at once).
- On null, or when the object's state byte `[obj+0x3a]` is 3 or less, each function falls back
  to a static dummy object. Its one-time construction takes a C++ static guard
  (`0x39c0100`/`0x39c0110`); that is the only lock on these paths and it is taken at most once
  per boot per process. Consequence: for an object in state 3 or below the round trip of step 2
  fails and the request stays vanilla (log `st=rt`). What states 0..3 are is not established (D:
  not yet active / being removed).
- `get_kind` additionally calls slot 0 of the looked-up object's vtable and returns -1 if it
  answers true. What that slot tests is not established (D); the function is the engine's own
  exported kind getter.
- `WorkModule::get_int` reaches slot `+0x98` = `0x4e4600` for both vtables: it indexes
  `[x0+0x18]` by bits 24..27 of the id and tail-calls slot `+0x10` of that sub-object with the
  low 24 bits. It does not touch `[x0+0x38]`, the object the param thunk forwards to, so no
  path from the identity lookup back into `0x4e53e0` was found.
- Re-entry is guarded anyway: before `resolve` the hook enters a per-thread guard keyed by the
  thread pointer register (`tpidrro_el0`), eight slots, compare-exchange, never waits. A nested
  call on the same thread (`st=reent`) or a ninth concurrent thread (`st=gfull`) returns the
  original value. Both are counted in L5 and should read 0.

### 1.4 The new log-only site `0x4e53f0` (B)

Words `f9401c00 f9400008 f9401d03 d61f0060` = `ldr x0,[x0,#0x38]; ldr x8,[x0];
ldr x3,[x8,#0x38]; br x3` (the prompt's instruction text is confirmed; note the third word is
`...1d03`, not the `...1903` of `0x4e53e0`). 8-aligned; next function starts at `0x4e5400`;
exactly two relocated pointers to it, slot `+0x278` of vtables `0x4f73738` and `0x4f89490`; no
direct branch into `0x4e53e0..0x4e53fc`; none of the four words is PC-relative. The same
4-word far-hook reasoning as for `0x4e53e0` applies (research/P3-DIAG-PLUGIN.md 0c; the far
form on `0x4e53e0` is tier A from gate 1).

Its stub differs from the 0.1.0 pattern on purpose: it saves x0-x8 and q0-q7, calls the logger
with (x0, w1, w2, return address), restores everything and tail-jumps to the trampoline. The
original therefore runs with the caller's registers, stack and return address, and whatever
it returns never passes through plugin code. If the trampoline pointer were missing the stub
executes the four original instructions itself. L6 is thus written before the original runs.

## 2. The plugin

`plugin/src/loadout.rs` (file format, pure), `plugin/src/logic.rs` (constants, decision,
guard, formatting, pure), `plugin/src/lib.rs` (stubs, `resolve`, hooks, logging, install).
Crate version `0.2.0`, variant `override`.

### 2.1 Loadout file v1 as implemented

Path `sd:/ultimate/mii_customizer/loadouts.txt`, opened with `File::open` once at plugin load,
before any hook is installed, into a fixed 16385-byte static buffer; never written, created
or deleted. Rules exactly as in the prompt. Points where the contract left room, and what I
chose (all toward "no override"):

| point | choice |
|---|---|
| file larger than 16 KiB | the whole file is refused (`state=too_large`), not truncated: a cut line could turn into another valid value |
| line endings | `\n` and `\r\n` both end a line (a file edited on Windows would otherwise fail its first line). A trailing `\r` is stripped, nothing else |
| UTF-8 byte order mark | not accepted: first line is then not exactly `mc_loadouts 1`. Logged as `state=bad_version_line_bom` so the cause is visible |
| non-UTF-8 | per line: that line is ignored (`non_utf8`), also when the bad byte is inside a comment. On line 1 it is a bad first line |
| number syntax | optional `-`, digits, optionally `.` and digits; at most 18 digits. No exponent, no `+`, no `inf`/`nan`, no `.5` or `5.`. Own parser, so "finite only" holds by construction. Negative numbers parse and are then `out_of_range` |
| ID syntax | exactly 8 hex digits, either case |
| field count | exactly three fields after comment removal; anything else `field_count` |
| 33rd distinct ID | that line `too_many_ids`; lines for the 32 known IDs still work |
| rejected-line log | first 64 rejected lines are logged with line number and reason, all are counted (`rejected=`). A 16 KiB file of bad lines would otherwise write thousands of lines at boot |
| empty file / only the version line | bad first line / valid with zero entries; both mean overrides off |
| no file vs unreadable | `state=absent` when the OS error kind is NotFound, else `state=unreadable`, with the raw error number. Both mean overrides off. How this target maps a missing file or folder to an error kind is unverified |

Storage: 32 x (u32 ID, 2 presence flags, 2 f32 bit patterns) in atomics, filled once before the
hooks exist, read-only afterwards. A looked-up value is range-checked again before it is
returned.

### 2.2 Decision per request (`param_event`)

1. Not one of the two hashes: tail-jump to the original, as in 0.1.0 (two compares).
2. Call the original, keep its result as `orig`.
3. Condition 1 (`logic::pointer_guard`): `x0 != 0`, `[x0] == base+0x4f89490`,
   `parent = [x0+8] != 0`, `[parent+0x50] == x0`. `[parent+0x50]` is read only for this vtable,
   whose single constructor site stores that parent (`step0.py`). Failing: `st=vt|nopar|back`.
4. If the loadout store is empty: `st=off`. **No game function is called in this state**, so a
   boot without the file behaves like the 0.1.0 diagnostic on this hook. This is deliberate: it
   makes "file removed" a clean control for "the identity calls cause a problem".
5. Otherwise guard + `resolve` (1.2): `st=reent|gfull|cat|rt|cat2|kindx|entx|entr`.
6. `st=kind` unless the kind is Mii Gunner.
7. Read the u32 at `T+0xe58+p*0x240`. Zero: `st=noid`. No value for this ID and key: `st=noent`.
8. `st=ok`: return the loadout value. Every other state returns `orig`.

No cache: the parent table that exists in the code is logging state only and is never read by
the decision (`logic::decide` has no access to it). So there is no cached identity that could
outlive a parent or follow a reused address; the cost is six short game calls per `weight` /
`walk_speed_max` request of a fighter while a loadout file is active (gate 1 counted about 600
such requests in a few minutes of play).

### 2.3 Log lines

File and style as 0.1.0: `sd:/ultimate/mii_customizer_log.txt`, append, `mc|<event>|seq=<n>`.

```
mc|L0|seq=0|mii_customizer 0.2.0-override loaded|base=..|T=..|id_p0=..|special_p0=..|hook_param=..|hook_custom=..|gunner_kind=74|fighter_cat=0|entry_work_id=0x10000000
mc|L0|seq=1|loadout|path=sd:/ultimate/mii_customizer/loadouts.txt|state=ok|version_line_ok=1|bytes=..|lines=..|accepted=2|replaced=0|rejected=0|ids=1|overrides=on
mc|L0|seq=..|loadout_reject|line=7|reason=out_of_range          (first 64 rejected lines)
mc|L0|seq=2|loadout_entry|id=0000f589|weight=130.0000|walk_speed_max=1.6000   (one per accepted ID; `-` = key absent)
mc|L0|seq=..|loadout|path=..|state=absent|os_error=..|overrides=off           (no file; once)
mc|L0|seq=..|site=0x4e53f0|name=custom|expected=..|found=..|match=1           (then installed=1|trampoline=..|after=..)
mc|L0|seq=..|site=0x4e53e0|name=param|...
mc|L0|seq=..|load_done|base_ok=1
mc|L3|seq=..|h=weight|n=1|slot=0|x0=..|parent=..|x2=0x0|ra=0x6c65b0|bits=0x43020000|v=130.0000|p=0|kind=74|id=0000f589|ov=1|orig=104.0000|vt=1|st=ok|chg=0
mc|OV|seq=..|id=0000f589|key=weight|p=0|parent=..|orig=104.0000|new=130.0000|newbits=0x43020000|ra=..
mc|L4|seq=..|parent=..|slot=0|p0=0000f589:00000000|p1=0000f58b:02020202|...|p7=..
mc|L5|seq=..|weight=..|walk_speed_max=..|parents=..|parent_overflow=..|l6=..|dropped=..|orig_null=..|st=ok:120,kind:40,noent:118
mc|L6|seq=..|n=1|x0=..|vt=1|parent=..|w1=..|w2=..|ra=..
```

- **L3** `v`/`bits` are what the caller received, `orig` what the game returned, `p` the entry
  id (-1 unknown), `kind` the fighter kind (-1 unknown), `id` the slot ID that was read
  (`00000000` when no slot was read), `ov` 1 if overridden. Added beyond the prompt: `vt`
  (1 = `0x4f89490`, 2 = `0x4f73738`, 0 = other), `st` (reason, list in 2.2) and `chg`.
  Kept: the first 4 per hash per parent. Added, bounded: up to 8 more lines per hash per parent
  whenever the outcome for that parent differs from the previous request (`chg=1`) - needed
  because an identity may resolve only after the first four requests, and because a parent
  address can be reused by another fighter in a later match. 32 parents per boot as before.
- **OV** once per (ID, key) per boot, at the first applied override.
- **L4** once per new parent, all eight slots, as in 0.1.0. **L5** with every L4 and every
  600th request; `st=` lists the number of requests per outcome since boot (`ok` = overridden).
- **L6** first 64 calls of `0x4e53f0`: `x0`, vtable class, `parent = [x0+8]` only when
  `vt=1` (else 0), `w1`, `w2` as signed decimals, module-relative return address. Join with L3
  through `parent` to get the player.

### 2.4 Never-panic and state rules

No `unwrap`, `expect`, `panic!`, assert, indexing expression, `format!`, `static mut`, heap
type or std number parser in `plugin/src` (checked mechanically). Fixed-size statics and
atomics only. The only `unsafe` data access outside the hooks is the file buffer, used once on
the loading thread before any hook exists. If the param trampoline pointer were missing the
hook performs the thunk's own loads, as 0.1.0 did (`orig_null`, expected 0).

## 3. Build and offline checks

| check | command (from the workspace root) | result | output |
|---|---|---|---|
| image facts | `python mods/mii_customizer/scratch/2026-10-04_P4-OVERRIDE-SLICE/step0.py` | 35 passed, 0 failed | `evidence/P4-OVERRIDE-SLICE/01_step0.txt` |
| host unit tests | `bash mods/mii_customizer/scratch/2026-10-04_P4-OVERRIDE-SLICE/run_host_test.sh` | 25 passed, 0 failed | `.../02_host_test.txt` |
| mutation control | `bash .../mutation_control.sh` | 17 caught, 0 missed | `.../02b_mutation_control.txt` |
| build | `bash mods/mii_customizer/build-plugin.sh` | exit 0, 0 warnings, hash reproduced on 2 rebuilds | `.../06_*` |
| binary + source | `python .../check_build.py --write-manifest` | 69 passed, 0 failed | `.../03_check_build.txt` |

Image: workspace-relative `gamedata/ssbu-13.0.4/main.bin`, sha256 `f70c97d2...7613`.

- **Build.** `Cargo.toml` names `skyline` and `skyline_smash` by bare git URL without `rev`,
  as the reference plugin's comments require (a `rev` on one side gives two `skyline` crates).
  `Cargo.lock` was started from the reference plugin's lock and reduced by cargo; it holds one
  `skyline` (`6b52d32...`), one `skyline_smash` (`315e4e8...`), `nnsdk 0.6.2` git `d23f1316...`
  (pulled in by `skyline_smash`), and every locked package also appears in the reference lock
  with the same version and source (asserted). Built offline from the local cargo cache; first
  build 31 s. `build-plugin.sh` now maps 0.2.x to the `override` variant. No source was copied
  from the reference plugin.
- **Host tests** compile `loadout.rs` and `logic.rs` unchanged. Parser: every rejection rule
  (version line in 16 wrong forms, BOM, size limit at 16384/16385 bytes, IDs, zero ID, keys,
  field counts, 22 malformed numbers, 12 out-of-range values), range boundaries, replacement,
  the 32-ID limit, CRLF, bounded reject log, 3000 random inputs that must never yield an
  out-of-range entry, and the delivered example file. Decision: vtable classes, pointer guard,
  each identity fact missing in turn, each decision condition, same ID on another port, the
  other Gunner, slot ID 0, non-Gunner with a stale-looking slot, empty store. Guard: re-entry,
  full, release, six threads racing.
- **Mutation control.** 17 single-line weakenings of the pure code (range bounds, zero ID,
  version, ID limit, size limit, exponent, kind test, slot ID 0, round trip, category, entry
  mismatch, entry 8, other vtable, back-pointer, re-entry) each make at least one test fail.
- **Binary.** Two site records; exactly six game imports; no thread creation, no inline hook,
  no delete/rename/create-directory import; param stub unchanged from 0.1.0; custom stub
  instruction-for-instruction as designed with the original four words as fallback; hash
  compare before any call; `resolve` call order and its early exits; thread-pointer read before
  `resolve`; one open site for the loadout path.

Not covered by any offline check: the hooks at runtime, the stubs at runtime, SD reads and
writes, and every statement in section 5.

## 4. For the coordinator's test plan

Decisions that depend on it, which offline work cannot settle: whether fighters' work objects
have vtable `0x4f89490`; whether the game's entry id is the index of the saved-Mii slot table;
whether the identity resolves at the time the engine asks; whether the values the engine
receives here are the ones that drive walking and knockback.

Install (coordinator): replace the 0.1.0 NRO with `builds/0.2.0-override/libmii_customizer.nro`;
copy `builds/0.2.0-override/example/loadouts.txt` to `sd:/ultimate/mii_customizer/loadouts.txt`
(new folder); remove the two file probes. Gunner A = saved ID `0000f589` (first special option
in all four slots), Gunner B = `0000f58b` (third option in all four), as in gate 1.

### 4.1 User steps (10)

Rules for all matches: 2 players, 2 controllers, stock, no items, a flat stage
(Final Destination), hazards off.

1. Delete `sd:/ultimate/mii_customizer_log.txt` if present. Boot to the main menu.
2. **Control.** P1 Mario, P2 Kirby. Walk both left and right for 10 seconds (stick tilted
   fully but not snapped, so they walk, not dash), one grab and up throw each, quit the match.
3. **Match 1.** P1 = Gunner A, P2 = Gunner B. Stand both at the same spot, then walk both in
   the same direction at the same moment across the stage. Do it twice.
4. Same match, **weight check**: at 0 % each, B grabs A and up-throws once (no pummel); then A
   grabs B and up-throws once. Watch how high each victim goes. Then let both take damage to
   roughly the same percentage (trade hits to about 80 %) and repeat both up throws once.
5. Quit the match. Write down: who walked faster, who flew higher from the throw.
6. **Match 2, ports swapped.** P1 = Gunner B, P2 = Gunner A. Repeat steps 3 and 4. Quit.
7. **Stale-slot check (one minute).** P1 = Mario, P2 = Gunner B. Walk both, quit.
8. Close the game (HOME, close). Copy the log from the card, whole file, as `log_boot1.txt`.
9. **No-file control.** Rename `sd:/ultimate/mii_customizer/loadouts.txt` to `loadouts.off`,
   delete the log, boot, play match 1 again (step 3 and one throw pair of step 4), close the game.
10. Copy the log as `log_boot2.txt`, rename the file back. If anything crashed or froze: note
    the step and copy the newest file in `atmosphere/crash_reports/` too.

Why the up throw: a throw has one hit, no spacing or timing to get right, and both Gunners
have the same throw, so the only difference between "B throws A" and "A throws B" is the
victim's weight. That throw knockback uses the weight this hook returns is D; the log tells
(section 4.3, row "feel").

### 4.2 What the user should see and feel

| step | expected with the example file (D until tested) |
|---|---|
| 2 | nothing unusual |
| 3, 6 | Gunner A walks clearly faster than B (1.6 against 1.0), whichever port A is on. Dash and run are unchanged |
| 4, 6 | A (weight 130 against 104) goes visibly less high from B's up throw than B (104) does from A's, more clearly at 80 % |
| 7 | Mario and Gunner B normal |
| 9 | A walks like B and flies like B |

### 4.3 Which log lines prove what

Read L3 lines by `parent`: one parent is one fighter in one match.

| claim | lines that show it |
|---|---|
| plugin and file loaded | L0: `0.2.0-override loaded`, `gunner_kind=74`; `loadout|state=ok|...|accepted=2|rejected=0|ids=1|overrides=on`; `loadout_entry|id=0000f589|weight=130.0000|walk_speed_max=1.6000`; both sites `match=1`, `installed=1` |
| **player mapping is right** | step 2: two parents with different `kind` and different `orig` weights; the one carrying P1's character must show `p=0`, the other `p=1` (the coordinator reads the two characters' weights from the extracted `fighter_param.prc`; this needs no Mii). Step 3: the parent with `p=0` shows `id=0000f589`, the one with `p=1` `id=0000f58b`, and the L4 line shows the same two slots. Step 6: `p=0` -> `0000f58b`, `p=1` -> `0000f589` |
| override only for f589, on either port | L3 with `id=0000f589`: `ov=1|orig=104.0000|v=130.0000|st=ok` (weight) and `ov=1|orig=1.0000|v=1.6000` (walk), with `p=0` in match 1 and `p=1` in match 2. `mc|OV|id=0000f589|key=weight` and `|key=walk_speed_max` once each. No OV line with any other ID |
| the other Gunner is vanilla | L3 with `id=0000f58b`: `ov=0|v=104.0000|orig=104.0000|st=noent` and `v=1.0000` |
| non-Mii fighters are vanilla | steps 2 and 7: every L3 of a parent whose `kind` is not 74 has `ov=0|st=kind` and `v == orig` |
| stale slot question | step 7: the L4 line of Mario's parent shows whether slot `p0` still holds `0000f58b` from match 2 or was cleared. Either way Mario's L3 must be `ov=0|st=kind` |
| no-file control | boot 2 L0: `loadout|...|state=absent|...|overrides=off`; every L3 `ov=0|p=-1|kind=-1|st=off`; no OV line |
| totals | last L5: `st=ok:<n>` grows only while A is in a match; `dropped=0`, `orig_null=0`, no `reent`, no `gfull` |
| when special choices are applied | L6 lines: `w1`/`w2` and `ra`, joined to a player through `parent` (same value as in L3). Expected (D): calls around fighter creation with the slot row and the chosen option |

### 4.4 Failure patterns and what each would mean

| pattern | meaning |
|---|---|
| L3 of fighters show `vt=2|st=vt`, `parent` meaningless | fighters' work objects have vtable `0x4f73738`; condition 1 as specified can never hold. Needs an offline look at what `[x0+8]` is for that vtable before anything is changed |
| `st=cat` or `st=rt` on every line of a fighter | `[parent+8]` is not that fighter's object id, or the object is not registered under it: the parent is not the module accessor the binding assumes |
| `st=rt` on the first lines, later a `chg=1` line with `st=ok`/`kind`/`noent` | identity resolves only after the object becomes active; requests before that stay vanilla. Harmless unless the engine keeps an early value (then the feel is vanilla although OV lines exist) |
| `st=kindx` or `st=entx` | the two sources of kind / entry id disagree; do not trust either |
| Gunners show `st=kind` with `kind=<n>`, n not 74 | the binding's kind constant is wrong for 13.0.4; n is the right value |
| `st=entr` | entry id outside 0..7 for a fighter (unexpected in a 2-player match) |
| Gunner lines `p=0|id=00000000|st=noid` while L4 shows the ID in another slot | entry id is not the slot index; the L4 line gives the actual slot per player, the mapping needs another source |
| A's parent shows `id=0000f58b` and B's `id=0000f589` (and B gets faster) | entry id and slot index are swapped relative to each other; same conclusion |
| `ov=1` lines and OV present, but A walks or flies like B | the value that drives the behaviour is read elsewhere or was taken before the override applied; compare the `ra` of the `ov=1` lines with P4-STAT-SITES |
| walk works, throw height equal | weight for throw knockback is not read through this function (or throws are a poor probe); try a single-hit attack before concluding |
| step 7: Mario's L4 shows `p0=0000f58b` | slots are not cleared for non-Mii players. Harmless here (kind test), but a non-saved default Mii Gunner on that port would then get the previous Mii's loadout; needs its own test before release |
| `reent` or `gfull` in L5 `st=` | the identity calls re-enter the hook, or more than eight threads ask at once; those requests were vanilla |
| L0 `site=0x4e53f0 ... match=0` / `installed=0` | another plugin hooks that site or the runtime refused; the param hook still works, L6 is absent |
| `state=unreadable` with the file present, or `state=absent` | path or SD access problem; `os_error` gives the code. Overrides are off, the game is vanilla |
| crash or freeze at boot before `load_done` | last L0 line names the step: file read (`loadout` line missing) or a hook install (a `match=1` line without `installed=`). A plugin that fails to load at all (no `mc|` line) points at symbol resolution of the six imports |
| crash when a match loads, last line an L6 | the `0x4e53f0` stub or its trampoline |
| crash when a match loads, last lines L0 only, boot 1 only (boot 2 fine) | the identity calls: boot 2 never makes them. This is what the no-file control is for |
| crash in both boots at match load | the hook mechanics themselves, independent of identity |

Rollback: put the 0.1.0 NRO back or remove the plugin; delete
`sd:/ultimate/mii_customizer/`. The plugin writes nothing but its log.

## 5. Not verified

- Anything at runtime: loading with six game imports, both hooks, the stubs, the file read,
  the guard register, the cost of the identity calls per request.
- That fighters' work objects have vtable `0x4f89490` (B says only: that vtable's object is the
  one stored at `[parent+0x50]` by the one constructor found; 0.1.0 did not log `[x0]`).
- That the entry id equals the index `p` of `T+0xe58+p*0x240`; that it does so for CPU players,
  more than two players, other modes, Ice-Climbers-style pairs.
- `FIGHTER_KIND_MIIGUNNER = 0x4A` for 13.0.4 (binding only).
- That slots are cleared for non-Mii players and for non-saved default Miis (stale-slot risk).
- The meaning of object state byte `[obj+0x3a]` and of slot 0 called by `get_kind`.
- That throw knockback or any other physics uses the weight returned here, and that walk speed
  on screen follows `walk_speed_max` returned here. Gate 1 shows the requests, not their use.
- Safety of the value ranges; they are the prompt's proposals.
- How a missing file or folder is reported by `std::fs` on this target (`absent` vs `unreadable`).
- That no other installed plugin hooks `0x4e53f0` (L0 would show `words_differ`).
- A cold-tree rebuild; the emulator was not used.

## 6. Deviations and notes for review

1. Category by accessor and the object id come from the binding's struct field, not from an
   exported function (1.2). Everything else about identity is exported functions.
2. Loadout choices where the contract was open are in the table of 2.1; the two that reject
   more than a lenient reading would are "file over 16 KiB refuses the whole file" and "BOM is
   a bad first line".
3. Logging beyond the prompt: `vt`, `st`, `chg` in L3; bounded change lines; `st=` counters in
   L5; `loadout_entry` lines; reject log capped at 64 lines.
4. With no usable loadout file the identity is not resolved at all, so L3 then shows
   `p=-1|kind=-1|st=off` instead of the player. Chosen so that the no-file boot is a clean
   control. To log identity in that state too, remove the `STORE.len() == 0` branch in
   `param_event`.
5. L6 is written before the original runs (transparent stub), unlike L3.
6. `scratch/2026-10-04_P3-DIAG-PLUGIN/check_build.py` and `host_test.rs` (not edited) describe
   0.1.0 and no longer match the crate; the 0.1.0 NRO is unchanged (`ae49c1c8...`).
7. Out of scope, suggested: a line in workspace `kb/reference/cargo-skyline.md` that a crate
   depending on `skyline` + `skyline_smash` builds offline here from the reference plugin's
   lock in about half a minute; and, when P4-STAT-SITES returns, comparing its site list with
   the `ra` values of the first console log of this build.

## Closing summary

- **Task ID:** P4-OVERRIDE-SLICE
- **Status:** DONE
- **Changed files:**
  - `plugin/Cargo.toml` (0.2.0, dependencies), `plugin/Cargo.lock` (regenerated from the
    reference lock), `plugin/src/lib.rs` (rewritten), `plugin/src/logic.rs` (reworked),
    `plugin/src/loadout.rs` (new), `plugin/README.md` (rewritten)
  - `build-plugin.sh` (variant mapping)
  - `builds/0.2.0-override/libmii_customizer.nro`, `MANIFEST.json`, `example/loadouts.txt` (new)
  - `builds/.cache/`: `build-0.2.0.log`, `host-test/host_test_p4.exe`, `plugin-target/` (updated)
  - `research/P4-OVERRIDE-SLICE.md` (this file)
  - `evidence/P4-OVERRIDE-SLICE/`: `01_step0.txt`, `02_host_test.txt`,
    `02b_mutation_control.txt`, `03_check_build.txt`, `04_nro_text_0x80.txt`,
    `05_nro_resolve_disasm.txt`, `06_build-0.2.0.log`, `06_build-0.2.0-recompile.stdout.txt`
  - `scratch/2026-10-04_P4-OVERRIDE-SLICE/`: `step0.py`, `check_build.py`, `host_test.rs`,
    `run_host_test.sh`, `mutation_control.sh`, and unmodified copies of `d.py`, `rel.py`,
    `dynsym.py`, `flatdis.py`, `nso.py`
- **Observed checks:** step 0 35/35; host tests 25/25; mutation control 17/17 caught; build
  exit 0 with the hash reproduced; binary/source check 69/69.
- **Not touched:** `mods/ssbu_mod_new` (read only), the cargo checkout of the binding (read
  only), `kb/`, `STATUS.md`, `CURRENT_INSTALL.md`, `CHANGELOG.md`, other workers' files, SD
  card, emulator. No commits, branches, agents or installs.
- **Could not verify:** section 5.
