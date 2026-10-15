# Probe initialization crash — 2026-09-26

## User evidence

- p1: both new characters selectable, no portraits/icons, match start crashes.
- First attempt selected both probes. A later attempt selected only Mythra Probe
  and also crashed. Therefore selecting two probes is not a necessary trigger.
- Atmosphere report: `4cd0d165-1796-4d1c-bc0f-e4f6df62297a/Pasted text.txt`.
- Skyline log: `7670999c-e60c-4499-8ad4-663f3d05810f/Pasted text.txt`.
  Raw copies are in `evidence/` beside this document.

## Confirmed panic site

The report has PC `smashline+0x33224`, opcode `d4200020` (`brk #1`), LR
`smashline+0x33918`, and X22 `smashline+0x497a8`. The exact packaged v1.6.8
binary contains that trap and call. Applying its ELF dynamic RELA addends to
the Rust Location at +0x497a8 yields `src/create_agent.rs:1181:10`.
This is the `unwrap()` in `agent_hash`, accessing Smashline's status-agent
vtable custom data. This is a software panic, not an unsupported CPU opcode.

## Confirmed address mismatch

The second log reaches `elight/esword`, native weapon kind 593 (`0x251`), with
factory wrapper `main+0x64c2d0` and target `main+0x33abee0`. The clone's fighter
initialization has already entered the module-accessor row bridge. No
`[MGW-CLONE] form=` callbacks have run.

The distributed Smashline v1.6.8 source installs `create_agent_status_weapon`
at `0x33abee0 + 0x5b0`, i.e. `0x33ac490`. The user's supplied main dump confirms:

| Address | Actual instruction / role |
| --- | --- |
| `0x33abee0` | `sub sp, sp, #0x90`, weapon status factory entry |
| `0x33ac490` | `add sp, sp, #0x90`, tail/exit path, not a function entry |
| `0x33b65b0` | `blr x8`, the intended Lua-module enable site |
| `0x33acde0`, `0x33add40`, `0x33aeca0` | weapon ACMD factory entries |

The missed wrapper creation explains why the later unconditional metadata read
panics. That final causal link must still be confirmed by a console retest.
The fix targets hook installation, and does not suppress the unwrap or bypass
status-agent validation.

The same explicit +0x5b0 displacement appears in 32 references at 31 sites.
`offset-audit.json` records every occurrence, source line, native instruction
bytes and shifted/unshifted disassembly. All corrected sites were inspected:
function entries, inline call sites, and weapon owner/name lookup points match
the roles their source hooks expect. The new build checks their first
instruction at startup before installing hooks, and refuses mismatches.

Pinned native dump SHA256:
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`.
Unmodified upstream source archive remains in `downloads/`; source overlay is
`smashline_1304/`, prepared by `tools/prepare_smashline_1304.py`.

## UI and resource observations

p1's resource generator handles fighter resources; it does not supply the new
CSS portrait BNTX textures. The generated config contains no UI portrait entries.
Mythra's source portrait identity is `elight_only`, under `ui/replace_patch`,
not `elight` under `ui/replace`. The local dump has no UI texture files.
The user supplied all 16 requested c00 source textures. `tools/build_probe_ui.py`
checks the observed single-texture BNTX layout and changes the one shared
length-prefixed name used by the container, texture and dictionary leaf. The
shorter names fit the original allocations. The dictionary's single-leaf
branch bit remains valid because both keys retain their trailing `_00`.
Readback verifies the three name references agree; the pixel bytes, dictionary
links, offsets and relocation table remain byte-identical. The package adds the
new files to the existing normal UI archive groups because clones are non-DLC
CSS entries. On-console rendering remains unverified.

The log also reports article residency misses and ARCropolis filesize warnings.
These are not proven to be the cause of the reported Smashline panic. Recheck
them after the factory hooks are corrected; do not treat a successful build as
evidence that article models, parameters or portraits work on Switch.

## Next console gate

Use the corrected runtime in a separate p2 package; replace p1's runtime file.
Look for `[MGW-SL] p2: verified 13.0.4 offset profile` and no `[MGW-SL] REFUSED`.
Then test Watch Probe alone, Mythra Probe alone, and both together. For each,
confirm `[MGW-CLONE] form=... expected=... selected=...` with matching IDs,
movement/attacks, respawn and results. Send the complete log on any failure.
Keep the original swap plugin disabled for this isolated test.

## p2 follow-up: invalid game-state pointer in Smashline input hook

The new Atmosphere report identifies the fault as Smashline+0x1b9d8,
`process_inputs_hook+0x38`, on the main thread. The matching p2 ELF symbol is
at 0x1b9a0. Disassembly shows the hook calling `get_game_state()`, loading a
pointer chain from the game text base plus 0x52c1760, then executing `ldr x8,
[x8]` at the faulting instruction. The report's X8 is 0x3f8000003f800000
(float 1.0 twice), so the hook interprets ordinary float data as a pointer.
Evidence: `evidence/p2-smashline-input-crash.txt`.

This is separate from p2's corrected 0x5B0 hook-address profile: that profile
passed its live version guard, but did not validate this data pointer. The
upstream hook exists only to load a development plugin after a button chord;
the probe does not use development hot reload. p3 therefore omits
`runtime_reload::install()` while keeping the other Smashline hooks. Startup
marker: `[MGW-SL] p3: verified 13.0.4 offsets; development hot reload disabled`.
Build and package completed locally; p3 still requires console retest. If it
crashes, retain the new Atmosphere report and complete Skyline log.

## p3 follow-up: null costume table during fighter initialization

The new Atmosphere report is preserved in `evidence/p3-costume-lookup-crash.txt`; its paired Skyline startup log is `evidence/p3-costume-lookup-skyline.txt`. Portrait registration succeeds and the log reaches clone-pack discovery. The crash is a Data Abort in Smashline at `+0x2f874`, reading address `0xe8` from a null base while `fighter_initialize_object_data` is handling the clone engine's module-accessor bridge.

Disassembly of the exact p3 runtime maps this instruction to `get_costume_from_entry_id`: upstream reads a pointer from the undocumented `main + 0x5324680` table and then reads the entry record at `+0xe8`. That table is null in this run. The 13.0.4 pinned symbol table provides the supported `FighterManager` singleton, `get_fighter_information(entry_id)`, and `FighterInformation::fighter_color` symbols. The Smash-rs bindings already wrap the manager singleton and entry lookup; the color accessor's pinned game implementation reads the color byte from the returned information object.

p4 replaces the stale global-table dereference with those game APIs, checks the entry range and propagates absent manager/entry as `None`. The source preparation script applies the same exact replacement and fails if upstream source no longer matches. The p3 crash report and p4 runtime build are separate validation points: the build cannot confirm console crash resolution or that both probe fighters load. At startup expect `[MGW-SL] p4: verified 13.0.4 offsets; native FighterManager costume lookup`, then retest one probe alone, the other alone, both together, and an original fighter with each. Keep the full Skyline log and Atmosphere report if it fails again.

## p4 follow-up: effect-transplant metadata is absent during fighter load

The new Atmosphere report is preserved in `evidence/p4-effects-crash.txt`; the paired Skyline log is `evidence/p4-effects-skyline.txt`. The clone probe itself reports build p4, registers both entries, and reaches Game & Watch's model and effect routing. The process then aborts at Smashline+0x34118 (`brk #1`) on TaskWorker2. Skyline's panic hook identifies the source exactly: `called Option::unwrap() on a None value`, `src/effects.rs:26:61`; the stack returns through `ssbu_clone_engine+0xa2048`, `fighter_init_second_row_bridge+0x64`.

In pinned Smashline, `load_fighter_effects` calls the game's original `load_effects` first, then unconditionally unwraps `FilesystemInfo::instance()` so it can search for optional sibling `/transplant` folders. That singleton lookup explicitly returns `None` when the pointer at `Text + 0x5332f20` is null. The failure is in this additional transplant scan, after the original effect loader has returned. p5 keeps the original call and only scans when FilesystemInfo exists and the supplied search index is present in its path list. Missing metadata skips that optional scan for that load and emits one diagnostic; later effect loads can scan normally when the resource index is available. This also prevents the unchecked path-list indexing panic.

The p4 Skyline paste includes `[MGW-CLONE] build p4` but does not include the p4 Smashline startup marker, so it does not independently prove which global Smashline NRO was installed. p5 has a distinct marker, `[MGW-SL] p5: verified 13.0.4 offsets; guarded effect transplant lookup`; replace the global `libsmashline_plugin.nro` as well as the probe folder and check for that line. The paste also reports `msg_name.xmsbt` missing/invalid during file discovery. That warning is separate from the `FilesystemInfo` panic and remains an open packaging observation.

p5 source generation completed (32 references, 31 verified instruction sites), both NROs compiled, and clone-pack lint reports 0 errors and 0 warnings. All 92 SD-layout files were copied directly to `mod_output`; hashes match the p5 manifest, no ZIP was created, and the p5 validation is in `mod_files/mgw_standalone/p5-validation.json`. Switch verification is still pending.


## p5 follow-up: native model lookup and a wider Smashline address audit

Evidence: `evidence/p5-model-skyline.txt` and `evidence/p5-model-crash.txt`.
The full startup marker confirms p5 was installed. The new failure is a Data
Abort at native main+0x4a0aa4, reading +8 from a null internal model pointer.
The lookup hash 0x04d27eea40 decodes to `have`. Its caller chain runs through
0x48f6d4, 0x48e378, 0x48ecbc, 0x3a8be4 and the engine's phase-115 bridge.
That bridge wraps a shared BattleObject phase, so its name alone does not
establish which fighter/article model is missing. The log reports unresolved
article resource indices before the fault. No specific asset absence has yet
been established as the complete cause of this native crash.

The p5 explanation that FilesystemInfo might not be ready was not established.
Native get_search_path_index at 0x353e344/348 loads main+0x5331f20;
Smashline instead read main+0x5332f20. The same independent audit finds stale
ResServiceNX, dynamic-module-manager, effect-manager and identity-table globals.
The relocated main table at 0x5185bd0 has food/rescue/esword at indices
119/120/593; the old 0x5186bd0 lookup reads `fighter` for those entries.
The correct fighter table is 0x4f80e20, and the weapon owner table is 0x5188240.
`native-support-audit.json` records native instructions and relocated strings.
The dynamic manager is verified by 0x17e4914..0x17e4920, which reads two pointers
from 0x5326cd0 and calls 0x22b6f60. EffectManager is verified at 0x60bfc4/8.

p6 fixes those specific globals. It also corrects the upstream -0x40 path-hook
positions: the old positions include prologues, string loops and epilogues.
Fighter-name hooks are placed after their native x2 loads, and one duplicate
hook is removed. All changes live in the overlay generator; vendor source is
unchanged. The startup gate now checks 83 native instruction sites. It does
not prove every dependency address or live clone behavior correct.

At the user's request, p6 materializes the available donor motions, article
models, effects, parameters and AI files under the two clone namespaces.
Motion-list entries remain unchanged; only the directory hash is retargeted.
Mythra's esword and winsword lists actually reference Pyra's esword directory.
Its four open/close clips differ from Mythra's local counterparts. The exact
Pyra clips therefore live in a separate clone-owned `eflame_esword` motion
folder, and both copied lists point there. Zero motion paths remain zero.
`donor-copy-manifest.json` records every source hash, destination hash and edit.
`MISSING_DUMPS.md` currently lists 18 fighter and fighter-voice sound-bank
files. They remain explicit archive aliases until the user supplies them.

Retest must confirm `[MGW-SL] p6: verified resource globals, name tables and
path hooks`, followed by `filesystem metadata resolved at main+0x5331f20`.
The native-model crash remains console-unverified. Test each clone alongside
an original, then both together; retain the entire new crash report if it
fails, since a changed PC is a new diagnostic point.


## p6 package record

The p6 probe and Smashline runtime built successfully. Clone-pack lint reports
zero errors and zero warnings. The final SD-layout tree contains 1,235 files in
`mod_output`; no zip was created. The output file hashes match the p6 manifest,
and both NROs contain their p6 startup markers. `p6-validation.json` records
runtime SHA256 `32b111573bfbe76348115f3975e33b03cedf01bef14b4914ec8f25d17cdb0c3e`
and probe SHA256 `65a9c026e7fa4efe1063316ceb13dd5491b67a7a9beee83bf9e8ccaad8020029`.

1,143 donor files were physically copied from the user dump. Fifteen retargeted
motion lists parse to end-of-file, retain all entries, and have no referenced
animation missing from the corresponding copied motion folder. Eighteen sound
bank files remain explicit aliases, listed in `MISSING_DUMPS.md`. The native
crash itself still needs a Switch retest; the new runtime is an evidence-based
address/resource correction, not console confirmation that the crash is gone.

## p6 follow-up: Mythra-only native initialization crash

Evidence is preserved in `evidence/p6-mythra-skyline.txt` and
`evidence/p6-mythra-crash.txt`. The user reports that Watch Probe now loads and
works, while Mythra Probe crashes. The Skyline paste contains both p6 startup
markers, so this is the p6 package.

The Atmosphere report faults on TaskWorker2 at
`cross2_Release.nss + 0x4983e4`, address `0x18`; LR is `+0x497488`. The stack
passes through Clone Engine's `module_accessor_init_row_bridge` and Smashline's
`fighter_initialize_object_data`. Disassembly of the user's 13.0.4 dump at
main-text offset `0x4983e4` is `ldr x0, [x9, #0x18]`; immediately beforehand,
`x9` is loaded from `[x19, #0x10]`. The crash report has `x9 == 0`, confirming
the null dereference. That instruction identifies the failure site, but does
not by itself name the missing object's semantic role.

The same Skyline log reaches Mythra's Elight articles. Its name hooks resolve
weapon kinds 593 and 594 as `esword` and `bunshin`; the owner hooks leave both
at native owner 91 (`ours None`). p6's fighter manifest registered no articles
for `mgw_mythra`, despite shipping clone-owned article model and motion files.
This is a concrete clone-ownership gap on the failing initialization path.

p7 adds the Clone Engine-supported base-article declarations for `esword` and
`bunshin`, using the names confirmed by the log. This gives those articles
clone-specific weapon kinds and owner/resource routing while retaining their
copied file names. The change targets the observed gap; only a console retest
can establish whether it resolves this native crash. Test Mythra Probe against
an original fighter first, then test both probes together. If it still fails,
the new PC and complete Skyline log will locate the next initialization stage.

## p7 follow-up: the fault is a missing motion holder, not article ownership

Evidence: `latest_logs/skyline.txt` and `latest_logs/atmosphere.txt`. The report
is byte-identical to p6 at the fault - PC `cross2_Release.nss + 0x4983e4`
(`ldr x0, [x9, #0x18]`), LR `+0x497488`, `x9 = 0`, Data Abort address `0x18`, on
TaskWorker2, with the same frames (clone engine
`module_accessor_init_row_bridge`, main `+0x6875c4`, `+0x3af458`, `+0x3a640c`,
`+0x33a0578`). p7's article declarations did engage - the log carries clone-tagged
records for `esword` (0x251) and `bunshin` (0x252) and builds the clone's sword
weapons at `[wpnctor] #29..#35 kind=593/594` - but the fault itself is unchanged.

The routine that faults is the one this project already probes as
`motion_bind_probe` (`main + 0x497350`):

| Address | Role |
| --- | --- |
| `0x497484` | virtual call on `[module+0x30]`, vtable slot `+0x240`; result compared with 5 |
| `0x49748c` | `b.eq 0x497e50`: state 5 skips holder creation entirely |
| `0x497d10` | `str x24, [x19, #0x10]`: attaches the motion holder on the other path |
| `0x4983cc` | `ldr x8, [x19, #0x148]`: the motion resource |
| `0x4983d4` / `0x4983d8` | `bail` when the resource, or its `+0x98` count, is empty |
| `0x4983dc` | `ldr x9, [x19, #0x10]`: the motion holder |
| `0x4983e4` | `ldr x0, [x9, #0x18]`: faults when that holder is null |

So the clone's module reaches the block with a **bound, non-empty motion resource
but no motion holder**. The routine attaches the holder only on the path where the
earlier state query returns something other than 5, and the caller chain is main
`0x6081f8` -> `0x3a7320` -> module accessor init `0x6867e0` (bridged) ->
`0x6875c0` -> `0x3af300` -> the weapon motion setup at `0x339fee0`, the function
this project already wraps with `weapon_motion_setup_probe`. The p7 log stops
exactly there, during the clone's esword article resolution.

Two gaps made the log silent about this:

- The engine's motion diagnostics (`motion_bind_probe`, `motion_rate_guard`,
  `change_motion_probe`) install only under the `diag_article_motion` feature,
  which the p7 NRO was built without: the log has no `[motionbind]`,
  `[motionrate]`, `[changemotion]`, `[weaponmotion]` or `[weaponmodel]` line.
- Those lines were emitted *after* `call_original!`, so a crash inside the hooked
  call would have silenced them even when enabled.

p8 builds the engine with `default + diag_article_motion`, moves the decisive
state to pre-call lines, and adds the state-query inputs to the trace. Look for:

- `[motionbind] p8 diagnostics armed: ...` at startup, which proves this engine
  NRO is the one installed.
- `[motionbind] BEFORE ... module=... kind=593 ... count=<nonzero> holder=0x0 ...`
  `NULL HOLDER WITH A BOUND RESOURCE: 0x4983e4 faults next`, naming the article
  kind whose motion holder is missing.
- `[articlescope] BEFORE object=... kind=593 ... owner=None - native: no owner kind
  resolved, the motion setup runs unscoped`, which separates "the clone scope was
  never applied" from "the scope applied and the holder still was not attached".

Watch Probe keeps working because Game & Watch declares no articles, so its
fighter initialization never binds an article motion. Either outcome above is
decisive for the next change; a crash without those lines means the installed
`libssbu_clone_engine.nro` is not the p8 build.

## p9: p8 named the branch, p9 patches it

Evidence: `latest_logs/skyline.txt` and `latest_logs/atmosphere.txt` from the
p8 run. The diagnostics installed - the log carries `[motionbind] BEFORE`,
`[articlescope] BEFORE` and `[weaponmotion]` - and the fault is unchanged: PC
`cross2_Release.nss + 0x4983e4`, Data Abort address `0x18`, `X09 = 0`,
TaskWorker2. The stack now names the caller: `ReturnAddress[00]:
ssbu_clone_engine (motion_bind_probe + 0x390)`, so the faulting code was
entered through this project's own `call_original!` at `0x497350`.

Three weapon motion setups ran for article kind 593, all of them unscoped
(`owner=None`, which is by design inside the construction bracket):

| # | object | module | result |
| --- | --- | --- | --- |
| 1 | `0x6ac90bb170` | `0x6ab7d34180` | holder `0x0 -> 0x6ac2d02ba0`, survived |
| 2 | `0x6ac90c29d0` | `0x6ab7d42780` | holder `0x0 -> 0x6ac2d04ae0`, survived |
| 3 | `0x6ac90ca230` | `0x6ab7d30a80` | holder never created, crashed |

The registers identify the branch. `X00 = 5` at the fault, and only one route
into the tail at `0x4983cc` can reach it with `x0` still 5:

| Address | Role |
| --- | --- |
| `0x497478` / `0x49747c` | load `[module+0x30]`'s vtable and slot `+0x240` |
| `0x497484` | `blr x8`; `0x497488 cmp w0, #5` |
| `0x49748c` | `b.eq 0x497e50`: state 5 skips `0x49749c`'s 0xa0-byte allocation |
| `0x497d10` | `str x24, [x19, #0x10]`: the only store of that holder |
| `0x497e50 -> 0x4980ac -> 0x498208 -> 0x49832c` | the state-5 route, taken with the flags at `+0x24f/+0x250/+0x251/+0x252` all 0 |
| `0x498348` | `cbz x8, 0x4983cc`: a null holder goes straight to the tail |
| `0x4983cc` / `0x4983dc` / `0x4983e4` | resource bound, holder reloaded, `ldr x0, [x9, #0x18]` faults |

Every other route into `0x4983cc` executes a `bl` first and would leave `x0`
as a pointer rather than 5, so the crash is the state-5 route. The routine
only ever *reads* `[module+0x148]`, so the resource was already bound when the
call entered - exactly the precondition the p8 `[motionbind] BEFORE` line
reports. The two surviving weapons were not in state 5, so `0x497d10` stored a
holder and the same tail then ran safely.

Two gaps in the p8 log: the crashing call's own `[motionbind] BEFORE` line is
missing (the file ends at `[articledata_lookup] #2`, so the last lines went
with the crash), and the log carries no `[PluginManager]`, `[MGW-SL]`,
`[MGW-CLONE]` or `p8 diagnostics armed` markers at all - only engine
`dbg_log!` output. The p8-only motion lines still prove which engine NRO ran.

p9 changes two things:

- `[articlescope] STATE ...` records the module, its kind, holder, resource
  and count, the state object and vtable, the `[vtable+0x240]` getter's offset
  in the main image, `+0x38`, `+0x256` and the four flags **before** the
  native call, from the one probe whose line always survives, with a `CRASH
  PRECONDITION` suffix when the holder is null and the resource is bound.
- `motion_bind_probe` patches `0x49748c` to `nop` for the duration of that one
  call when the precondition holds, so native takes the path the two surviving
  weapons took and builds the holder itself. The original word is restored
  as soon as the call returns, the patch is logged before it is applied, and
  it refuses to run unless `0x49748c` still reads `0x54004e20` - a build that
  is not looking at this routine logs `FORCE refused` and changes nothing.

## p10: p9's patch never reached the article, the write itself faulted

Evidence: `latest_logs/atmosphere.txt` from the p9 run. It is a different
crash from every previous one:

| Field | Value |
| --- | --- |
| `Exception Info / Address` | `0000007278a9b48c (cross2_Release.nss + 0x49748c)` - the patch site |
| `X[08]` | `0000007278a9b48c (cross2_Release.nss + 0x49748c)` |
| `X[09]` | `00000000d503201f` - the `nop` the guard was writing |
| `LR` / `PC` | `ssbu_clone_engine (motion_bind_probe + 0x490 / + 0x4c0)` |
| `Fault Address` | `0000000000000000` |

So the guard engaged, its encoding check passed, and then the store faulted: a
plugin cannot write the game's text with a plain store, however correct the
address and the value are. Skyline's own hooks do not hit this because they
write through the runtime helper behind `skyline::patching::Patch`, which
handles the section permissions.

p10 keeps the guard and the `[articlescope] STATE` dump, changes the write to
`Patch::in_text(0x49748c).nop()` and the restore to
`Patch::in_text(0x49748c).data(0x54004e20)`, and reads the word back rather than
assuming it landed. Every way the guard can decline now logs instead of
faulting:

- `FORCE refused` - `0x49748c` did not hold `0x54004e20`.
- `FORCE failed` - `Patch` returned an error, or the read-back is not a `nop`.
- `FORCE restored` - the branch was put back after the call returned.

Note for the next report: the p9 skyline log was truncated at the head (it
starts at `[stagepanel]` rather than at boot), so none of the p9 startup
markers or `STATE` lines were visible even though the crash PC proves the p9
engine was installed. A log copied from boot is worth more than a longer one.

## p11: the log loses its tail, so the breadcrumbs go to the SD card

Evidence: `latest_logs/atmosphere.txt` from the p10 run.

The guard worked. The Data Abort at `cross2_Release.nss + 0x49748c` is gone,
and the report no longer points at the patch site: four weapon motion setups
completed with holders that native created after the state-5 skip was nop'd for
the call. The fault moved to a new site inside the same routine:

| Address | Instruction | Reading |
| --- | --- | --- |
| `0x4984bc` | `ldr x8, [x19, #0x10]` | the motion holder |
| `0x4984c0` | `ldr x0, [x8, #0x10]` | the object the holder keeps at +0x10 |
| `0x4984c8` | `ldr x8, [x8, #0x38]` | that object's vtable slot +0x38 |
| `0x4984cc` | `mov w1, wzr` | argument 0 |
| `0x4984d0` | `blr x8` | returns 0 (`X20 = 0` in the report) |
| `0x4984d4` | `ldr x8, [x0]` | Data Abort: the answer is dereferenced without a null check |

So this fault is a null return from the vtable `+0x38` method of the object at
`holder+0x10`, not another missing holder. Which call it was is unknown: the p10
report ends at the `FORCE holder path` line for module `0x4eada40780`, while the
crashing module (`X19 = 0x4ec1e6f780`, holder `0x4eac5f4d40`) never printed its
own line. Skyline's log is a TCP stream (`skyline::logging::log` ->
`skyline_tcp_send_raw`) and the game kills the thread inside `call_original!`,
so the last lines never arrive - a limitation no further logging through that
stream can fix.

p11 adds a second sink. The engine already writes the SD card through
`std::fs` (`kind_ledger` writes `sd:/ultimate/clone_engine/kinds.txt`), so the
motion probes now mirror every line into
`sd:/ultimate/clone_engine/p11-breadcrumbs.txt` as they produce it:

- `[bind] enter` for **every** call, not just first sight, with the module,
  weapon kind, caller, resource, count, holder, the holder's head words
  (`+0x8`, `+0x10`, `+0x18`, `+0x50`) and the state object, plus
  `FORCE-CANDIDATE` when the guard condition holds.
- `[bind] exit` only once the call returns, so an enter without an exit is the
  call that died.
- `[force] applied` / `refused` / `nop verified` / `failed` / `restored`.
- `[setup] enter` / `[setup] exit` around each weapon motion setup, carrying the
  weapon kind, so the dying weapon is identifiable without the TCP tail.
- A startup self-test: the armed marker carries the file path and `write ok` or
  `WRITE FAILED`, so a dead sink cannot masquerade as an absent crash.

The guard, the `[articlescope] STATE` dump and all p8/p9/p10 lines are
unchanged; p11 differs only in where the lines land. `std::fs` writes on the
spawning thread are synchronous, so a breadcrumb always reaches the card before
the native call it describes can kill the thread.
