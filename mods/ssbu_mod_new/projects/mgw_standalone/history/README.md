# MGW Pyra/Mythra pair prototype - p16

The new package is in `mod_output_pair`. It registers one Mythra CSS entry
that expands to two clone kinds: Mythra and a hidden Pyra partner. Down-special
is passed to the game's native Element swap. Pyra uses the exported c00 assets;
Mythra uses the black-and-pink skin. This pair has not been tested on hardware.

The p15 run again crashed at `cross2_Release.nss + 0x35c23a8` on Elight body
file `0x34e65`, despite exact SD/package NRO matches. Disassembly of the local
13.0.4 executable showed that the previous residency checker called the wrong
function at `0x3540380` and used a resource-record stride of `0x48`. The native
builder calls `0x35c2040` to resolve the relative filename and indexes its
record table with a stride of `0x18`. p16 uses those native values. The route
log file is included in the package because runtime attempts to create a new
file returned result code 514 in p15.

Replace the previous `MGW_Standalone_Probe` folder on the SD card rather than
overlaying it: the old folder contains Game & Watch files that are absent from
this pair. Copy the global engine NRO, the new probe folder, and
`ultimate/clone_engine/p16-model-route.txt` from `mod_output_pair`.

The p14 console run used the correct engine NRO (its SHA-256 matched the local
package), but crashed again at `cross2_Release.nss + 0x35c23a8` with Elight's
body-model file index `0x34e65`. Its route breadcrumb failed to write. p15
recognizes the known Elight body search index directly, considers the clone
body even when the preflight checker calls the original resident, and records
the full decision in `sd:/ultimate/clone_engine/p15-model-route.txt`. The
relative filename is now null-terminated. The breadcrumb uses the same
read-then-write filesystem operations used by the working kind ledger, and
startup reports the exact error if writing fails. This package has not passed
a console test. Copy the global engine NRO and the full probe mod folder from
`mod_output`, then inspect the p15 breadcrumb and Atmosphere report.

The p13 test used the correct NROs and reached the native model builder, but
faulted on the same body-model file. Review found a deterministic bug in the
engine's residency checker: it read the file table's record index but compared
the uninitialized output field to the record count. That made a resident clone
body fail the candidate check. p14 assigns and checks the fetched index. A
focused host test covers an in-range record entry and the two rejected cases.
Look for `[copymodel] p14` at startup and `body-route ... routed=true` during
Mythra Probe loading. The engine also writes these route decisions to
`sd:/ultimate/clone_engine/p14-model-route.txt` and reports `WRITE OK` or
`WRITE FAILED` at startup; send that file if the TCP log loses its tail.
Gameplay remains unverified until the console retest.

The p12 console run used the correct NROs (both SD hashes matched), but still
crashed at `main + 0x35c23a8` on Elight body file index `0x34e65`. Its dynamic
`[articlebody]` line never ran: the failing weapon preload bypasses that article
path resolver. p13 moves the same narrow body-model route to the actual native
model builder hook. Check for `[copymodel] p13` at startup and
`[copymodel] body-route ... routed=true` while loading Mythra Probe. The SD card
has not been modified by this build; copy the new package before testing it.

The latest supplied crash was at `main + 0x35c23a8` while building Elight's
`bunshin` article (weapon kind `0x252`). The log resolved `model.numdlb` to file
index `0x34e65`, which the pinned archive list identifies as
`fighter/elight/model/body/c00/model.numdlb`. The original body's resource
record was not resident (`stop=flag`). Bunshin uses the fighter body model;
copying body files into `model/bunshin` did not address this lookup.

p12 routes only that article's body-directory lookup to the clone's body
directory when the original record is absent and the clone record is resident.
The engine prints `[articlebody] p12` at startup and an `[articlebody]` line
with both lookup indices, residency results and `routed=true/false` when the
lookup occurs. Replace the global `libssbu_clone_engine.nro` and the full
`MGW_Standalone_Probe` folder from `mod_output` for this test. A successful
local build and pack lint do not verify gameplay; the console run is the gate.

This is the first console test for the separate roster character project.
It adds **two independent entries**, `MGW Mythra Probe` and `MGW Watch Probe`,
each with one c00 costume. It is **not yet the combined transforming character**.
The portraits use the user's dumped textures with clone-specific container,
texture and dictionary names. p2 added all 16 requested textures.

p2 replaced the bundled Smashline runtime with a source build correcting
32 displaced address references against the user's 13.0.4 executable dump.
The old runtime missed the sword article's status factory and subsequently
panicked reading Smashline agent metadata. See `DIAGNOSIS.md` and
`offset-audit.json` for evidence. p3 disables Smashline's development hot reload.
The latest crash report showed its input hook treating float data at stale main
offset `0x52c1760` as a pointer. This feature only loads development scripts
and is not used by the probe. p4 replaced the costume lookup with native APIs. p5 guarded an absent
filesystem pointer; the dump now proves its address was wrong. p6 corrects the
filesystem, resource service, module manager and name-table addresses, and moves
misplaced name hooks to their verified native sites. It removes one duplicate
hook. The runtime checks 83 native instructions before installing.

p6 also copies available motion, article-model, effect, AI and parameter files
from the user's dump into each clone namespace. Motion lists retain every entry
and change only the directory hash to the clone's own path. Mythra's sword lists
reference Pyra's sword animations; those exact clips have their own copied folder.
The current missing donor files are listed in MISSING_DUMPS.md; until supplied,
their original archive aliases remain explicit in config.json. Shared native
executable code and common game resources remain dependencies of this probe.
This build still needs a Switch retest.

p6 testing confirmed Watch Probe works but Mythra Probe crashes during native
fighter/article initialization. The crash is at `cross2_Release.nss + 0x4983e4`;
the p6 Skyline log shows native Elight article kinds 593 (`esword`) and 594
(`bunshin`) kept their original owner, with no clone article mapping. p7 uses
Clone Engine's supported `[[fighter.article]]` declarations for those two
verified article names. The dump includes and the pack copies the sword model
and both articles' motion lists. It has no separate `bunshin` model folder, so
the base article supplies that model; the pack linter reports this as one
inheritance warning. This addresses the ownership gap seen in p6; the crash
resolution still needs console confirmation.

p8 keeps one c00 costume per probe and imports the selected skins into that
slot. Black-and-Pink Mythra's c06 body and sword textures, effect bank and five
sword-trail textures are copied into `mgw_mythra` c00 paths. Pink G&W's c05
body and all 13 article-model components are copied into `mgw_watch` c00
paths. The source mod files remain untouched. Available skin portraits are
given the clone's BNTX name and c00 dictionary bit; UI variants the source skins
do not provide keep the generated clone portrait. `skin-import-manifest.json`
records every imported file and its source/output SHA-256.

p8's console log named the fault: the motion bind at `main + 0x497350` asks
`[module+0x30]`'s vtable `+0x240` method for a state, and the answer 5 takes
the branch at `0x49748c` that never creates the motion holder. The tail at
`0x4983cc` then dereferences the holder that was never created, at `0x4983e4`.
Two weapons survived because their state was not 5 and native built the holder
itself; the third crashed with `x0 = 5` and `x9 = 0`.

p9 kept every p8 diagnostic and added two things: an `[articlescope] STATE`
line printed before the native call, so the module state survives the crash,
and a guard that patched that single conditional branch to `nop` for the
duration of the call when - and only when - the module already has a bound
motion resource and no holder. Its first console run never reached the article.
The report shows the Data Abort at `cross2_Release.nss + 0x49748c`, `x8`
holding that address and `x9` holding `0xd503201f`: the value the guard was
storing. A plugin cannot store into the game's text with a plain write, however
correct the instruction and the address are.

p10 keeps that guard but writes through `skyline::patching::Patch`, the helper
Skyline's own hooks use, and then reads the word back instead of assuming the
write landed. The `[articlescope] STATE` dump stays. Every way the guard can
decline now has its own line - `FORCE refused` for an unexpected instruction,
`FORCE failed` for a rejected write or a read-back mismatch, `FORCE restored`
when the branch goes back - so a guard that does not engage says so instead of
looking like a silent crash.

p10's console run proved the guard worked and moved the fault. Four weapon
motion setups finished with holders built, and the crash became `main +
0x4984d4`: `[holder+0x10]`, asked through its vtable `+0x38` for something with
the argument 0, answered 0, and the caller dereferenced it. What that run could
not say is which bind it was. The report again ended a few lines short, because
Skyline's log is a TCP stream and the game kills the thread inside the hooked
call - the lines written immediately before the fault never arrive.

p11 keeps the guard, the `[articlescope] STATE` dump and every earlier line,
and adds a second sink: the same lines are written to
`sd:/ultimate/clone_engine/p11-breadcrumbs.txt` as they are produced, the folder
the engine already writes its kind ledger into. Every bind gets a `[bind]
enter` line - not just first sight - with the module, weapon kind, resource,
count, holder, the holder's head words and the state getter, and a `[bind]
exit` line only once the call returns. Every weapon motion setup gets the same
`[setup] enter` / `[setup] exit` pair. The file's last line is therefore the
call the thread died in, and the dying weapon's kind survives even when the TCP
log has lost its tail. The armed marker says whether that file is writable
(`write ok`), because a dead sink would look exactly like a silent crash.

The moves are the native base moves. Mythra's down-B is deliberately intercepted
and returns to wait/fall while paired-fighter support is being developed.
G&W still has his normal bucket. Hero's Spin, grenade and the old swap hooks are
not included in this probe. The existing costume mod remains a separate build.

## Install this test

**Requires Smash Ultimate 13.0.4**, Skyline and ARCropolis already installed.
The upstream Clone Engine used here supports only that game version.

1. Back up the affected SD files. Temporarily move the existing
   `libmythra_gamewatch_swap.nro` out of the SD's global Skyline plugins folder
   and move `ultimate/mods/mythra_gamewatch_swap` out of the active mods folder.
   Keep the backups outside loader directories. Disable other fighter/roster
   replacements for this first test so the log has one source of changes.
2. Copy the contents of `mod_output` to the SD card root. It contains the clone
   engine, Smashline, NRO Hook, CSK runtime, and probe mod in their SD paths.
   Back up existing versions before replacing dependency files; keep one copy of
   each runtime plugin. Skyline and ARCropolis themselves are not bundled.
   **For every probe update, replace `libssbu_clone_engine.nro` and
   `libsmashline_plugin.nro` as well as the `MGW_Standalone_Probe` folder.
   Copying only the mod folder leaves the older runtimes in place, and a stale
   engine NRO is enough to hide every p14 diagnostic.**
3. In ARCropolis, enable `MGW Standalone - Clone Probe` (version 0.7.3), then restart Smash.
   The probe's `plugin.nro` stays inside its mod folder, not in global plugins.

This prototype has not been tested on a Switch. Test in local versus/training first.

## Console test and log

Keep the full Skyline log from startup, including `[fighterpack]`,
`[clone_engine]`, `[css118]`, `[MGW-SL]`, `[MGW-CLONE]`, `[motionbind]` and
`[articlescope]` and `[copymodel]` lines. Confirm these markers at startup:

- `[MGW-SL] p7: verified resource globals, name tables and path hooks` from
  Smashline. A `[MGW-SL] REFUSED` line means the runtime declined to install
  its hooks; send that log before further gameplay tests.
- `[MGW-CLONE] build p14: two independent clones, corrected model residency check in engine,
  ...` from the probe, which
  shows the new `plugin.nro` is the installed one.
- `[copymodel] p14: body-model routing at native builder with corrected
  resource-record index check`
  from the global Clone Engine NRO.
- `[motionbind] p11 diagnostics armed: motion bind BEFORE trace plus CRASH
  BREADCRUMBS at sd:/ultimate/clone_engine/p11-breadcrumbs.txt (write ok), ...
  forced holder path at 0x49748c applied with skyline::patching` from the clone
  engine. Without this line the installed `libssbu_clone_engine.nro` is not
  the p11 build, and a Mythra crash would say nothing new. `write ok` means the
  breadcrumb file is open; `WRITE FAILED` means only the TCP log has the lines.

1. Confirm both new portraits appear and both original roster entries remain.
2. Select Mythra Probe versus an original fighter. Check that the match loads
   and the black-and-pink skin appears, then try walking, jumping, sword attacks
   and native up-B. Down-B should log
   that the swap is deferred and stay as Mythra. If the match crashes here, the
   last `[motionbind]` and `[articlescope]` lines before the crash are the ones
   to send, along with `sd:/ultimate/clone_engine/p11-breadcrumbs.txt` (see
   "Reading the p11 diagnostics" below).
3. Confirm Watch Probe is pink on its body and articles. Put both probes in one
   match and check that each has its own model, attacks and articles. Also test
   Mythra Probe alongside original Mythra.
4. Repeat the Watch Probe check if needed; p6 already loaded and played as G&W.
5. Check original Mythra's down-B and original G&W's bucket. The probe callbacks
   should not print for those fighters.

Send the full log and tell me which numbered step failed or passed. On a crash,
also include `sd:/ultimate/clone_engine/p11-breadcrumbs.txt` - its last line is
the call the thread died in - plus the Atmosphere report and the exact
selection/move. An
`IDENTITY MISMATCH`, `REFUSED`, missing portrait, or absence of probe callback
logs is a failed gate, even if a match appears to run.

### Reading the p11 diagnostics

The first fault was the native routine at main `+0x4983e4` (`ldr x0, [x9,
#0x18]`), which dereferences the motion holder at `[module+0x10]`. p8 proved
the branch that strands it: `0x497484` calls `[module+0x30]`'s vtable `+0x240`
method and `0x49748c` skips holder creation when it answers 5, so the module
reaches `0x4983cc` with a bound resource and no holder. p10 opened that branch
for one call at a time through `skyline::patching`; native then built the holder
and the fault moved on to `main + 0x4984d4`, where `holder+0x10` answered 0 to
its vtable `+0x38` method and the caller dereferenced the answer.

The lines that decide the next change:

- `sd:/ultimate/clone_engine/p11-breadcrumbs.txt` - the last line is the call
  the thread died in. A `[bind] enter` with no `[bind] exit` names the module,
  its weapon kind, its resource and holder state and the holder's head words; a
  `[setup] enter` with no `[setup] exit` names the weapon whose motion setup
  never returned, which is the one to compare against the weapons that loaded.
- `[articlescope] STATE n=... object=... kind=593 module=... mkind=...
  holder=0x0 res=0x... count=2 state_obj=... vt=... method=@0x... +0x38=...
  +0x256=0 flags=[...]`, printed before the native call so it survives the
  crash (the file repeats it as `[setup] enter`). `method=@` is
  `[vtable+0x240]` relative to the main image: the getter which answered 5.
  The suffix `CRASH PRECONDITION` marks the module that used to die here.
- `[motionbind] FORCE holder path module=0x...: nop state-5 skip at 0x...
  for this call` means the guard engaged and native built the holder, followed
  by `FORCE restored 0x54004e20 at 0x...` once the call returns.
  `FORCE refused` means `0x49748c` did not hold the expected instruction, and
  `FORCE failed` means the write was rejected or did not read back - either way
  the call ran unpatched, so send that line before anything else.
- `[motionbind] BEFORE ... NULL HOLDER WITH A BOUND RESOURCE: 0x4983e4 faults
  next` still records the state on entry; under p11 it describes the state the
  guard repairs rather than a guaranteed crash.

If Mythra still crashes, the breadcrumb file ends on the crossing that never
came back: the `[bind] enter` or `[setup] enter` without its exit line names the
module and weapon kind, and whether a `[force] applied` line sits inside it says
if the guard engaged for that very call. The `STATE` line printed before it adds
the vtable host and `method=@` of the getter. No `[motionbind] p11 diagnostics
armed` at startup means the installed `libssbu_clone_engine.nro` is not the p11
build.

The log prints dynamically assigned clone kinds, entry IDs, battle object IDs,
base kinds, status and position. Clone kind numbers can change with installed
mods; the code resolves them by name each boot.

## Restore the existing costume mod

Remove `ultimate/mods/MGW_Standalone_Probe` from the active SD mods directory,
remove this test's `libssbu_clone_engine.nro` if it was newly installed, restore
the backed-up runtime versions and the original costume mod/plugin. Keep any
engine another installed clone pack already needed. No console save data or
firmware changes are required by this package.

## Build and package locally

Source and build inputs live in `mod_files/mgw_standalone`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File mod_files/mgw_standalone/build-probe.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File mod_files/mgw_standalone/build-smashline.ps1
python mod_files/mgw_standalone/tools/package_probe.py
```

Use Python 3.11+ and the existing Cargo Skyline toolchain. The build uses the
locked dependencies offline. On this PC, the build script adds the existing
`%MSYS2_MINGW_BIN%` to its process PATH for GNU host build tools, then restores
PATH. Skyline may require write access to its own Cargo toolchain directory.

The packaging script verifies pinned vendor commits, checks release asset sizes
and published digests where available, checks NRO headers, regenerates and lints
ARCropolis mappings, hashes model inputs, and copies the finished SD files into
`mod_output` in the usual SD card folder layout. Each run gets a fresh staging
directory and leaves unrelated files already in `mod_output` in place.

The available donor resources come from this workspace's own `export` dump.
`donor-copy-manifest.json` records physical copies and motion-path changes.
`skin-import-manifest.json` records the imported skin files; the Pink G&W ZIP
is checked against its extracted folder before packaging.
`MISSING_DUMPS.md` lists inputs still borrowed through explicit archive aliases.
Original donor files are never modified.

## Pinned components

| Component | Version / source |
| --- | --- |
| Clone Engine | [0.3.1-beta.1](https://github.com/PropaSmike/ssbu_clone_engine/releases/tag/0.3.1-beta.1), commit `b420a90de60584e6fc18266a870570dc7fb0435b` |
| Clone Pack Workbench | [source](https://github.com/PropaSmike/clone_pack_workbench), commit `495e7ba99f0020cb9a5e87afd6d3fa6a64e03fcc` |
| Smashline | [v1.6.8 source](https://github.com/HDR-Development/smashline/releases/tag/v1.6.8), MGW p2 offset corrections, p3 hot reload fix, p4 native costume lookup, p5 checked effect-transplant search, and p6 resource globals/name-table/path-hook corrections; `smashline_1304/Cargo.lock` pins the rebuilt runtime's dependencies |
| NRO Hook | [v0.4.0](https://github.com/ultimate-research/nro-hook-plugin/releases/tag/v0.4.0) |
| CSK Collection runtime | [5.0.6 for 13.0.4](https://gamebanana.com/mods/499008) |

Only CSK's runtime is included; its optional feature packs are not installed.
`manifest.json` in the staging directory records exact hashes and source URLs. These are local
assembly checks, not evidence of on-console compatibility. See `ARCHITECTURE.md`
in the source folder for the next integration steps and known engine constraints.
