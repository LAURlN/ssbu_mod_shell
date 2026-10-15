# Handoff to Space Bunny Alpha

> **Superseded 2026-09-29.** This project is parked. The active work is
> `mod_files/pyra_gamewatch_reskin/HANDOFF_SPACE_BUNNY_ALPHA.md`. Do not continue M0/M1 here.

Updated 2026-09-28. Workspace: `<workspace root>`.
Continue inside `pyra_mythra_clone/`. **The active work is now M1, not the
recorder.** The recorder is parked: it records, replays and diffs correctly, but
its equality gate is not clean, and that is a characterised gap rather than an
active blocker. The user has stated that a playable character matters more than
exact comparison, so the milestone priority moved.

Recorder history: six hardware runs fixed a freeze deadlock, a file-creation
failure (`O_EXCL`) and a duplicate-callback invalidation, all confirmed on
hardware; run 6 introduced a crash which was reverted. See
`reports/trace-freeze-incident-2026-09-28.md` and `reports/console-2026-09-28-run5/`
through `-run7/`.

M1 state: an instrumented Clone Engine and a **Pyra/Mythra pair pack** are
installed on the card and have **never been run**. See "M1: clone loading" below.

## Goal and current direction

The user wants an additional selectable Pyra/Mythra pair with eight costumes,
coexisting with the originals, playing exactly like them and eventually fully
editable into two original characters that transform into one another.

Read `ASSESSMENT.md` for the current architecture. Use Clone Engine to run original
behavior first, then replace character logic in editable layers and compare
traces after each replacement. Native machine-code relocation is parked. Neither
a working playable clone nor full independence has been demonstrated.

The immediate milestone is **M0: reliable state capture and repeatable playback**.
After M0, investigate loading a single Mythra clone (M1), then single-form fidelity
(M2), pair support (M3), and editable behavior layers (M4/M5). Do not treat a
compiled recorder or passing PC fixtures as a passing console baseline.

## Exact checkpoint

- Recorder source: `trace/`, version **0.1.1**.
- Build: `trace/target/aarch64-skyline-switch/release/libpmclone_trace.nro`.
- Isolated package: `test_output/PyraMythra_trace_check.zip`.
- NRO size: **167,936 bytes**.
- SHA-256: `b0b86987d408281924c32fea9c3f1c9f700950ca6f399b4946110bf15dcf7592`.
- Installed on SD at
  `sd:/atmosphere/contents\01006A800016E000\romfs\skyline\plugins\libpmclone_trace.nro`.
- Installed readback matched this build.
- Build history: `2b54f5cb...` froze; `d924a4c1...` fixed the freeze; `1ceb6265...`
  added the directory instrumentation; `7ff07206...` removed exclusive create;
  `9616a6a7...` first-wins duplicates and saves inputs on invalid sessions;
  `5127ccb0...` **crashed on attack, reverted**; `b0b86987...` is the revert.
- `b0b86987...` is functionally the run 5 recorder. It is not byte-identical to
  `9616a6a7...` because the source now carries comments recording the crash.

### Run 1: freeze on D-pad up (FIXED, confirmed on hardware)

`pmclone_trace.log` stopped after `record requested; arming` with no crash
report, which identifies a lockup rather than a fault. `SESSION` is a
`std::sync::Mutex`; `on_fighter` held it and called `change_status_force`, which
re-entered the same callback on the same thread and blocked forever.

Fixed by splitting `arm_fighter` into `plan_arm` (reads, lock held) and
`apply_arm` (writes, lock released), plus a thread-local `IN_HOOK` re-entrancy
guard on all four session entry points.

### Run 2 and 3: arming completes, file creation fails (FIXED, confirmed on hardware)

No freeze. Sessions 1, 2 and 3 all reached file creation and all failed:

```
session 1: cannot create sd:/ultimate/pmclone_trace/traces/0001_rec.trace.csv: Result code: 514
session 2: cannot create sd:/ultimate/pmclone_trace/traces/0002_rec.trace.csv: Result code: 514
session 3: cannot create sd:/ultimate/pmclone_trace/traces/0003_rec.trace.csv: Result code: 514
```

`514` = `0x202` = FSS PathNotFound. The `play refused: cannot read
inputs/last.inputs` lines are correct: no recording was ever completed.

**Do not repeat the FSS-directory theory from run 2; run 3 disproved it.** The
instrumentation showed all three `create_dir_all` calls returning Ok, including
`traces/`. The directory resolves fine. Creating the *file inside it* is what
fails.

That leaves the open mode as the only distinguishing input, and it is decisive:

| Call | Flags | Result |
| --- | --- | --- |
| `boot_log` to the log | `.append(true).create(true)` | works |
| `fs::write` to `counter.txt` | `.create(true).truncate(true)` | works |
| `begin` to the trace CSV | **`.create_new(true)`** | **514** |

`create_new(true)` is `O_EXCL`; it was the only exclusive create in the plugin
and the only one that failed. It existed solely to implement the "refuse to
overwrite a trace" guarantee. The run 2 depth observation was a confound: every
working write was directly in `pmclone_trace/`, so nesting looked causal when
the open mode was the real variable.

Third fix: open with `.write(true).create(true).truncate(false)` and keep the
guarantee by refusing a file whose length is non-zero. The length check is not
atomic against a concurrent writer, which is acceptable and stated in the
source: names are session numbered and only one controller can record.

Earlier, `begin` discarded the `create_dir_all` result with `let _ =`, which is
why the first attempt logged nothing useful. It now goes through `ensure_dir`
and logs the real error, and `prepare_dirs` creates the tree at plugin init.
Both were kept: they are what exposed the true cause.

If the 514 persists with `O_EXCL` gone, the Horizon SD path is refusing the
*filename*, not the mode, and the next thing to try is a shorter, simpler name.
**It did not persist: run 4 wrote a 908 KB trace. `O_EXCL` was the cause.**

### Run 4: first real capture, invalidated by a duplicate callback

```
session 4 started: Record -> .../0004_rec.trace.csv
session 4 INVALID: duplicate object callback in frame 212
session 4 finished (duplicate object callback in frame 212): Record, 213 frames, 640 rows
```

Freeze, file creation and buffered row writing are all confirmed working now.
`0004_rec.trace.csv` is 908,486 bytes: three objects for 213 frames
(`fighter:elight`, CPU `fighter:k48`, and `article:elight_esword#0` present for
all 213), full work columns. Preserved in `reports/console-2026-09-28-run4/`.

Frame 212 sampled `fighter:elight` twice — status 0 at motion frame 54, and
status 39 at motion frame 0. That second sample is a mid-frame status
transition, so **Smashline's Main line fires twice in one frame when a fighter's
status changes**. The calls are sequential, not nested, so the `IN_HOOK` guard
correctly did not suppress them. The one-row-per-object-per-frame model was
wrong, and it invalidated every capture containing an attack.

Status 39 is not identified. The trace has no status-kind name table.

The capture was also **static**: Mythra stood still for all 213 frames, position
pinned at `-35.999996`, status 0 throughout. No attack landed. That was
undiagnosable because the invalidation also skipped `save_inputs`, so there was
no `inputs/last.inputs` to inspect.

Fourth fix: `flush_rows` is first-wins on `(slot, object, order)` and counts the
extras instead of invalidating, logging the count at session end. `order` stays
in the key because several articles of one name legitimately share a slot and
object. Invalid sessions now still save their inputs.

Beware when reading the card: the newest Atmosphère crash report is from 15:02
and is an older `ssbu_clone_engine` null deref, roughly seven hours before the
recorder was even installed. It is not evidence about the recorder. Full detail,
including the live confound of the still-installed private module loader, is in
`reports/trace-freeze-incident-2026-09-28.md`.

The user explicitly asked, "can you put the stuff on the switch?" after the build.
That request authorized installing this recorder and superseded the earlier
read-only restriction for that installation. Do not ask them to authorize the
already completed copy again. It does not authorize unrelated SD cleanup/repair.

`F:` was FAT32, label `SWITCH SD`, serial `130F-145B`, with about 14 GB free.
Windows Get-Volume reported a repair warning. A read-only `chkdsk F:` subsequently
reported no file-system problems; no repair command was run. The card may now be
back in the console: check availability before accessing it.

The SD already had Skyline-related plugins including `libarcropolis.nro`,
`libnro_hook.nro`, `libsmashline_plugin.nro`, and `plugin.nro`. Only the new recorder
file was copied. The old plugins were not removed or replaced. Their presence
does not establish a clean gameplay baseline; investigate conflicts if evidence
points to them, preserving existing files.

## M1: clone loading (ACTIVE)

The card previously **could not load a clone by any path**: the installed mod
folder was the old private-module loader, with no `fighter.toml` and no
`libssbu_clone_engine.nro`. That is now fixed and the pair pack is installed.

### What is on the card

| Item | State |
| --- | --- |
| `atmosphere/contents/01006A800016E000/romfs/skyline/plugins/libssbu_clone_engine.nro` | installed, SHA-256 `ec56ee9153e66806dff1dddc3abbeab401318ec19ca4d15e6754b350cb2ffbcc`, 1,810,432 bytes, readback verified |
| `sd:/ultimate/mods/PyraMythraClone/` | 1,041 files: `fighter.toml`, `fighter/`, `effect/`, `camera/`, `sound/`, `ui/` |
| old `plugin.nro` (private loader) | moved to `plugin.nro.bak-private-loader`, **not deleted**; restore by renaming back if the engine conflicts |
| `libpmclone_trace.nro` | still installed; harmless, but it consumes D-pad taunts as commands, so **disable it by renaming to `.nro.off` before any character-select test** |

The pack is the **pair**, not a standalone: `mgw_mythra` (base `elight`,
selectable, shown as "Pyra/Mythra (Clone)") plus `mgw_pyra` (base `eflame`,
`css = false`, so paired into the same entry). Built from
`mod_output_pair/`, staged at `build/pyra_mythra_pair/`, which is the copy to
rebuild from. A trimmed single-Mythra pack also sits at `build/mythra_single/`
and is **not** what is installed.

### The frontier crash and the instrumented engine

The last full clone run died at `main+0x35c23a8`, inside Clone Engine's own
`copy_model_probe`, returning into `custom_article_data_cache_insert`. That
report was mis-filed earlier in this project as "unrelated"; it is in fact the
documented M1 crash. Report preserved at
`reports/console-2026-09-28-freeze/01790600523_01006a800016e000.log`.

`copy_model_probe::Residency::fatal()` is
`file_path != NOT_FOUND && !resident()`. It guards *"the model resolves to a
path but is not resident"*. It does **not** guard *"the model does not resolve
at all"*, which reads as not-fatal, is handed to native, and reaches native's
not-found path at `0x35c23a4`, which sets `x8 = 0` and loads `[x8+0x20]`. The
crash report matches exactly: `Address 0x20`, `Fault Address 0x0`.

**This is a hypothesis from source reading, not proof.** The engine's own
`[copymodel]` line was lost because the Skyline log is a TCP stream and the game
kills the thread inside `call_original!` (the p11 lesson). So the deployed engine
adds a breadcrumb sink and changes **no guard behaviour**:

- Every call appends to `sd:/ultimate/clone_engine/copymodel-breadcrumbs.txt`
  before anything can kill the thread.
- The suspected case is tagged `UNRESOLVED-THEN-NATIVE`.
- A startup self-test line proves the sink works, so a missing file can never be
  mistaken for a quiet run.
- Capped at 256 reports; synchronous writes, as p11 established is required.

If the next crash shows `UNRESOLVED-THEN-NATIVE`, the fix is small. If it shows
something else, the hypothesis is cheaply dead.

### Honest scope note

`ASSESSMENT.md` is blunt that the **pair** is M3 and hard: Clone Engine gives one
custom kind per player entry, while vanilla Pyra/Mythra is two fighters sharing
one entry with a native link event. The single form is the part that must work
first. The user has said a playable character matters more than exact comparison,
so broken sword behaviour would be an acceptable intermediate.

## M1 update 2026-09-28 23:30: pair test collected, pack never reached the CSS

**The pair test WAS run. "Pyra/Mythra (Clone)" did not appear on the CSS.** The
user confirmed this directly. That is the discriminator the p1 notes could not
make, and it resolves as **pack-not-loaded**, not pack-loaded-but-broken.

Card state was verified before drawing any conclusion: both installed binaries
matched the hashes recorded above exactly (`ec56ee91...` engine,
`b0b86987...` recorder), so the card was in the state this document claims.

### The breadcrumbs came back negative

`copymodel-breadcrumbs.txt` exists: **148 lines**, written **23:19-23:22**, i.e.
after the 23:11 engine install, so the instrumented engine did run. Results:

- **Zero `UNRESOLVED-THEN-NATIVE` tags.** The `fatal()` blind-spot hypothesis
  is not confirmed.
- Every line is `enter` with `doomed=false`. No call was ever in the suspected
  state.
- **No crash report exists after 22:49.** Writes continued to 23:22, so that
  run survived.

Do not over-read this. `copy_kind` is `active_kirby_copy_kind()`, which is
Kirby-specific and unrelated to the `mgw_mythra` kind, so `copy_kind=None` on
every line is expected. The `variant=2`/`variant=9` entries look like ordinary
vanilla fighter model loads. **148 breadcrumbs with no clone-specific evidence
is not proof the clone was exercised** - it is consistent with the clone never
being instantiated at all.

The startup self-test line is **absent** from the file even though
`install()` writes it. Most likely the file was deleted after boot but before
the first model call, which also means all 148 lines are one launch against a
manually cleaned file. Confirm rather than assume.

### Root cause of the missing CSS entry

`ui_chara` is **not a file** - it is a hash used as an ID in the CSK chara
database. `css_registration.rs` computes `hash40(definition.ui_chara)` and
passes it to the CSK as `ui_chara_id`, with `clone_from_ui_chara_id` pointing at
`ui_chara_elight` as the donor. Nothing needs to exist on disk under that name.
The pack's 14 `ui/replace/chara/chara_*/chara_*_mgw_*.bntx` portraits are
correctly structured. **Building new portrait assets would not have fixed this
and that option is off the table.**

The gate is in `register_csk_css_slot()`, which needs two exported CSK symbols,
`add_chara_db_entry_info` and `add_chara_layout_db_entry_info`. If either is
absent it returns early and **no CSS row is ever written**, however correct the
pack is. That matches the symptom precisely: `kinds.txt` shows kinds 121/122
allocated, so the kind machinery worked, but no visible entry appeared.

Registration is also deferred by `css_slot_nro_hook` until a post-CSK NRO load
event where both symbols resolve, guarded by `CSS_SLOT_REGISTRATION_STARTED`.

Every one of those outcomes printed only via `skyline::println!` - the TCP log
the handoff already documents as lossy - which is why the refusal left no
durable trace and the run looked clean.

### Change made: durable CSS registration log

One engine change, mirroring the `copy_model_probe` breadcrumb sink: a
synchronous, capped SD sink at
`sd:/ultimate/clone_engine/css-registration.txt`, with a startup self-test so an
absent file can never be read as a quiet run. It records the symbol lookups, the
eligible-definition count, the `register_v1_with` refusal, the per-fighter
publish, and the `get_ui_chara_from_entry_id` resolution.

- Build: `f737715fe394b3289b28641a05c145f2100162c3da8cc5452c24eee7a0fa12f4`,
  1,814,528 bytes. Release build succeeded; new sink strings verified present in
  the NRO. Installed and readback hash-matched.
- **`libpmclone_trace.nro` renamed to `.nro.off`** before this test, per the
  procedure above. It was still enabled during the 23:19 run, so D-pad
  navigation may have been affected. Restore by renaming back.

**No guard or registration behaviour was changed.** This build only makes the
existing outcome observable. Do not interpret a refusal line as a new bug
without reading which of the recorded steps failed.

### Correction: build f737715f could not answer the question

The user booted the CSS with `f737715f...` installed. Still no clone.
**`css-registration.txt` was never created.**

The breadcrumbs prove the engine ran correctly and the new binary was live:
`copymodel-breadcrumbs.txt` now contains **two** `#0 enter` lines (two boots),
with the selftest line at **line 149** - exactly where boot 2 begins - and 166
further `enter` lines after it. No crash report newer than 22:49.

**The cause was a defect in the instrumentation, not in the pack.**
`css_log_selftest()` was placed as the first line *inside*
`register_csk_css_slot()`, which is only reached once the CSK symbols resolve.
If they never resolve, the function returns at the symbol check and the file is
never created. The self-test sat in the one path that was never taken, so an
absent file proved nothing. Lesson: a proof-of-life must be emitted on the
failure path too, or it cannot witness its own absence.

### Rebuild 5518e16d: self-test moved to init, negative paths logged

- `css_log_selftest()` now runs in `lib.rs` init immediately after
  `fighter_packs::load_all()`, so the sink always proves itself regardless of
  CSK state. The file's existence is now unconditional.
- `css_slot_nro_hook` logs a capped `WAIT nro='<name>'` line on every NRO event
  where the CSK symbols are not yet resolvable, with the per-symbol booleans and
  the definition count. This is the previously silent case.
- `fighter_packs` logs pack discovery (`NO PACKS` when `ultimate/mods` has no
  `fighter.toml`), each parse (`PACK PARSE FAILED` with line and message), the
  declaration count, and `KIND <n> = <name>` on successful registration.

Build `5518e16d84937bb3787a93e6e50116e9a7f5f07d962596af9ffc0948959f1f58`,
1,818,624 bytes. Release build succeeded; all new sink strings verified present
in the NRO. Installed, readback hash-matched, stale log cleared.

**Still no guard or registration behaviour was changed.** These two builds only
made the existing outcome observable, and `f737715f` was discarded rather than
interpreted precisely because its self-test could not witness its own absence.

This distinguishes all three previously indistinguishable causes: symbols never
resolve, the NRO hook never fires, or the pack never registers a kind.

- Build `5518e16d84937bb3787a93e6e50116e9a7f5f07d962596af9ffc0948959f1f58`,
  1,818,624 bytes. Release build clean, all new strings verified in the NRO,
  installed with readback hash match. Stale `css-registration.txt` removed so
  the next boot is unambiguous. **Still no behaviour change.**

## Two things this document did not record

**There is a 22:49 crash, newer than the 15:02 "frontier"** this file names.
`01790628549_01006a800016e000.log` is a `User Break` in `nnSdk + 0x389998`, the
same signature as run 6's `status_Attack_Main_button` assert. It predates the
23:11 engine build, so it is **not** evidence about the instrumented engine.

**That crash happened with the run-6 revert already installed.** The recorder
on the card is `b0b86987...` with mtime **22:47:10**; session 8 ran at **22:49**
logging `frame 0 has no callbacks` - the run-6 signature - and then crashed.
Sessions 9/10/11 at 22:56 were clean. Session 8 is absent from this document,
which jumps from run 6 to "run 7 confirmed the revert". **The revert may not be
a complete fix**, and the run-7 reports cover only sessions 9/10/11. This is
the most consequential unexamined evidence on the card.

## ROOT CAUSE FOUND 2026-09-28 23:52: CSK Collection was in the wrong title

`css-registration.txt` under build `5518e16d` answered the question cleanly.
**The pack was never at fault.** It loads perfectly:

```
1 fighter.toml pack(s) under sd:/ultimate/mods: PyraMythraClone
  PACK PARSED PyraMythraClone: 2 fighter declaration(s)
  KIND 121 = mgw_mythra (base 91, ui_chara ui_chara_mgw_mythra, CSS row inherited from base)
  KIND 122 = mgw_pyra   (base 90, ui_chara ui_chara_mgw_pyra,   pack publishes its own CSS row)
  WAIT nro='common'/'item'/'koopajr'/'rockman'/'purin'/'buddy'/'sonic':
        CSK symbols not resolvable yet (add_chara=false add_layout=false)
```

Both kinds registered, both bases resolved (91 = elight, 90 = eflame). The CSK
symbols were `false` on **every** NRO event, so `register_csk_css_slot()` was
never entered and no CSS row was ever constructed.

**The cause: `libthe_csk_collection.nro` was installed under the wrong title.**

| | |
| --- | --- |
| CSK Collection was at | `01006A800016E000_S/romfs/skyline/plugins/` |
| The game boots | `01006A800016E000` - whose `plugins/` had no CSK NRO |

Atmosphere loads plugins only from the running title's directory, so the library
defining `add_chara_db_entry_info` / `add_chara_layout_db_entry_info` was never
in the process. Not a naming error and not a load-order race: seven NRO events
spanning most of the roster is ample opportunity for a real race to resolve.
`main.bin` contains no `add_chara_db*` strings either, consistent with these
being CSK-plugin-side symbols.

**Fix applied:** copied the NRO to
`01006A800016E000/romfs/skyline/plugins/libthe_csk_collection.nro`, readback
hash-matched (`185769ca5272ff118a2e00ad6c564570abf8af5ffd32f94e495451e913a78841`,
1,380,352 bytes). **Copied, not moved**; the `_S` copy is untouched and is for
something unrelated - the user confirmed it can be ignored. Nothing else depends
on that title for this work.

### A separate, still-unproven issue: DLC field values

`custom_fighters/template_v2/src/csk.rs`, the upstream template this code was
derived from, carries an explicit warning: **Pyra is a DLC base**, and a DLC row
keeps shop and unlock fields "the select screen checks", so such a row "is never
drawn". The engine sets `is_dlc=false`, `save_no=0` (an occupied Mythra slot),
`shop_item_tag`/`alt_chara_id` to `0x2302_d482a` (`hash40("-1")`).

This is **not** the cause of the missing entry - no row was ever written, so a
field value cannot explain it. But once the symbols resolve, a DLC-base row may
still be rejected on these fields. Expect it as the *next* failure, not this one.

## First action for the next session

**Boot once and collect `sd:/ultimate/clone_engine/css-registration.txt`.** With
the CSK plugin present the symbols should now resolve, and a `symbols resolved`
line plus a `PUBLISHED` line for `ui_chara_mgw_mythra` means the CSS row was
written. Check for a DLC-field rejection if the entry still does not appear.
Under build `5518e16d...` the file must exist: the self-test now runs at init.
Read it in order - `NO PACKS` means the mod directory was not seen at all, a
`PACK PARSE FAILED` line means `fighter.toml` is malformed, `KIND <n> = ...`
means the kind registered and the failure is downstream in the CSK path, and a
run of `WAIT nro=` lines that never reaches a `symbols resolved` line means the
CSK symbols are not becoming available. Those imply four different fixes, so do
not guess between them.

Then, if the user has run anything further, pull:

- `sd:/ultimate/clone_engine/copymodel-breadcrumbs.txt` — for any run that got
  as far as loading models.
- The newest Atmosphère report from `sd:/atmosphere/crash_reports/`, matching the
  run time. Ignore anything older than the pair test; this card accumulates
  reports from unrelated experiments.
- Whether "Pyra/Mythra (Clone)" appeared in Character Select at all, and whether
  the match started. **Answered for the 23:19 run: it did not appear.**

Do not rebuild the engine or change guards before reading the breadcrumbs. One
change per build; run 6 proved why.

### Recorder run 7: revert confirmed, and a third noise source

After the run 6 revert, sessions 9/10/11 all completed clean with no crash, so
the revert is good. The control is still not clean, and there are now **three**
sources rather than two:

| Object | Differences | Cause |
| --- | --- | --- |
| `article:elight_esword#0` | 267 | animation phase persists across sessions; arming does not touch articles |
| `fighter:elight` | 251 | `INT_ATTACK_SERIAL`, 3 vs 6, every frame |
| `fighter:k34` | 251 | **new** - CPU AI differs between two playbacks of identical inputs |

The CPU appearing in the *control* is new; at run 5 it only differed in
recording-versus-playback. Control total 769 of 1304; recording-versus-playback
518. Evidence in `reports/console-2026-09-28-run7/`.

Known-bad, do not retry: `MotionModule::set_frame` on a weapon, and zeroing
`INT_ATTACK_SERIAL`. Both are recorded as suspects beside the reverted code in
`trace/src/session.rs`.

### If the test has not been run yet

Rename `libpmclone_trace.nro` to `libpmclone_trace.nro.off` first. The recorder
consumes D-pad taunts as commands, which would interfere with character-select
navigation, then test: look for "Pyra/Mythra (Clone)" in the Xenoblade series,
report whether it appears **before selecting anyone**, and if it does, start a
match alone against a stock fighter and report whether the match starts. Do not
fight yet; every crash in this chain is in fighter initialization.

## Recorder: first action when it is picked up again

**Do not run more recordings yet.** The toolchain is proven; more sessions of the
same kind will produce the same uninterpretable comparison. The blocker is that
two playbacks of identical inputs do not start from the same game state.

The next work is to make session start state reproducible. An attempt to do this
**crashed the game and has been reverted**; do not repeat it.

Build `5127ccb0...` changed two things at once and the next run died:

- `apply_arm` zeroed `INT_ATTACK_SERIAL` via `WorkModule::set_int`.
- `on_weapon` called `MotionModule::set_frame(boma, 0.0, false)` on every
  article while arming.

The run logged `frame 0 has no callbacks` and then raised a **User Break**
(SDK assert, not a fault) in `L2CFighterCommon::status_Attack_Main_button` on
the next attack. Full report in `reports/trace-freeze-incident-2026-09-28.md`
under run 6, evidence in `reports/console-2026-09-28-crash-setframe/`.

Suspects, neither proven:

- The article `set_frame` fits "no callbacks": `MotionModule` is the *fighter*
  motion API and is not valid on a weapon. The weapon-specific path has not
  been identified.
- The serial reset fits the assert: zeroing a monotonic serial the game uses
  for attack bookkeeping is exactly what `status_Attack_Main_button` would
  object to.

**One change per build from here.** Shipping both together is what made this
unattributable.

Open items in priority order:

1. Find the correct weapon/article motion API, or another way to make article
   phase reproducible. 334 of the 652 control differences.
2. Decide how to handle `INT_ATTACK_SERIAL` without zeroing it. 318 of the 652.
   If it must be made reproducible it needs a valid non-zero starting value.
3. CPU state, still deliberately untouched: `fighter:k82` motion differs on 55
   frames but only in recording-versus-playback, not in the control.

Gate unchanged: **play versus play must be zero differences** before a
recording-versus-playback comparison means anything.

The test procedure itself is proven and unchanged: D-pad up, wait a second,
attack with face buttons until the status changes, back to idle, D-pad down,
then D-pad left twice for two playbacks.

1. Training mode, normal Mythra, a standing CPU out of attack range, flat hazard-free
   stage, normal speed, no items, both grounded at 0 percent, default taunt mappings.
2. Tap D-pad up, release, wait one second, perform a short neutral attack sequence,
   return to idle, tap down to stop. There is no on-screen recording indicator.
3. Tap left to replay. Wait longer than the original recording, then tap left again
   for a second playback. Keep the same fighters and starting form.
4. Avoid pausing, resetting Training, changing speed, or swapping forms for this
   initial test. Close Smash before collecting files.
5. Preserve `ultimate/pmclone_trace/pmclone_trace.log`, `inputs/`, and `traces/`
   locally under a new dated report directory. Keep all three captures. Preserve
   timestamp-matched Atmosphere crash reports if the game crashes.

Compare both playback traces and recording versus first playback:

```powershell
python pyra_mythra_clone/tools/trace_diff.py FIRST.trace.csv SECOND.trace.csv --ignore none --json comparison.json
```

Use actual paths. Playback files have names like `0002_play_last.trace.csv`;
the recording is `0001_rec.trace.csv`. Exit 0 = identical captured fields, 1 =
differences, 2 = malformed/incomplete/invalid input. Keep tolerance at its default
zero. Do not ignore fields to force a pass. Inspect the first differing frame and
session log to distinguish reset differences, recorder timing, and game behavior.

After repeated playback passes, exercise hitstop and article creation. Right
D-pad replays with one selected input frame replaced by neutral. `perturb.txt`
contains `frame N` (default 60), counting input `i` lines from zero; that frame
must be in range and non-neutral. Choose an input that actually affects behavior.
This tests an **input change**, and the original planned controlled gameplay
parameter-change test is still outstanding.

## Source map and changes made this session

| File | Role |
| --- | --- |
| `trace/src/input.rs` | Final mapped-input hook, 8-byte mapped-input struct, runtime signature search |
| `trace/src/session.rs` | Taunt commands, arming/reset, input recording/playback, CSV writing and validity checks |
| `trace/src/sample.rs` | Fighter/article callbacks, native state reads, hitboxes and kinetic speeds |
| `trace/src/names.rs` | Vanilla names and optional Clone Engine base-fighter mapping |
| `trace/src/work_ids.rs` | Generated selected instance-work IDs |
| `tools/gen_trace_work_ids.py` | Generator using pinned skyline-smash constants |
| `tools/trace_diff.py` | PC comparison, compound-field parsing and capture validity checks |
| `tools/test_trace_diff.py` | Existing comparison fixtures/tests |
| `tools/test_trace_recorder_contract.py` | Added signed-zero, NaN, duplicate-key and incomplete-capture regressions |
| `tools/package_trace_check.py` | Local package creation, dump signature checks, NRO/source freshness and readback |

### Added or changed for M1

| File | Role |
| --- | --- |
| `upstream/clone_engine/src/copy_model_probe.rs` | Added the SD breadcrumb sink and `UNRESOLVED-THEN-NATIVE` tagging. **No guard behaviour was changed.** The `fatal()` blind spot is documented in a comment at the call site. |
| `build/pyra_mythra_pair/PyraMythraClone/` | The installed pair pack, staged copy. Rebuild from `mod_output_pair/ultimate/mods/MGW_Standalone_Probe/`. |
| `build/mythra_single/MythraClone/` | Trimmed single-Mythra pack, **not installed**; kept as the M1 stepping stone if the pair fails to initialise. |
| `reports/console-2026-09-28-crash-setframe/` | Run 6 crash: the regression I introduced, and the evidence for both reverted calls. |
| `reports/console-2026-09-28-run7/` | Revert-confirmed baseline and the third control noise source. |
| `mod_files/mgw_standalone/DIAGNOSIS.md` | The p1–p11 crash chain. **Read before touching the engine.** Documents through p11 only; p12–p16 left no artefacts in the workspace, and the 15:02 report is the frontier. |
| `trace/README.md` | Installation, commands, test procedure, format and known limitations |
| `reports/trace-build.json` | NRO/source hashes and static-check evidence |
| `reports/trace-continuation.md` | Change history, check results, deployment record and remaining acceptance gates |

A partial recorder and old compiled binary already existed when this session
started. Changes hardened that implementation: reject an unexpected hook offset;
accept valid article owner object ID zero; avoid assuming active fighter identity
when lookup fails; validate playback starts/roster and perturbation inputs; cap
recordings at 3600 input calls; detect missing/duplicate callbacks and missing
fighter slots; report write/save errors; refuse trace-file overwrite; write
completion/invalid footers; invalidate on observed exit from Training.

The diff previously converted floating values too early and could conceal signed
zero or NaN differences. It now preserves float text, uses numerical tolerance
only when requested, rejects duplicate compound keys and empty captures, and
requires recorder completion counts to match the rows and contiguous frames.

## Unresolved issues that matter

This is an experimental recorder, not a full state snapshot or proven frame clock.

- Frames are grouped between one human controller's mapping calls, with state
  sampled by Smashline Main callbacks. One input call per simulation frame and
  callback behavior during hitstop are unproven. Missing callbacks currently
  invalidate a trace; that may reveal a sampling limitation rather than a game bug.
- Arming restores position, facing, percent, clears speed and requests/forces WAIT.
  It does not restore RNG, stale moves, articles, shield, CPU state, hidden partner
  state, or all work values. Repeated playback may therefore differ from frame 0.
- **Synchronous SD writes still happen while `SESSION` is held**, from inside the
  input-mapping hook (`begin`, `flush_rows`, `finish`). A slow write on the input
  thread is an independent freeze hazard that will surface during recording rather
  than arming. Moving the I/O off the lock is the next known correction.
- Game calls must never be made with `SESSION` held; use `plan_arm`/`apply_arm`.
  A thread-local `IN_HOOK` guard catches mistakes, but it is a backstop, not a
  licence to call into the engine under the lock.
- Both Pyra/Mythra objects are not guaranteed to appear every frame: inactive
  forms are only sampled if their Main callback executes.
- Hitbox reads cover IDs 0..7 using pinned `AttackData` bindings. The part field
  is always zero; not every collision field or part is captured.
- `hitstop` is the boolean `StopModule::is_stop`, not remaining hitlag frames.
- Missing measurements include per-joint hurtboxes, shield stun, status/int64 work,
  weapon per-energy speeds, RNG, and other hidden engine state.
- Article instance suffixes are per-frame ordinals sorted by battle-object ID;
  they are not persistent creation identities. Clone article-name normalization
  is unfinished. Only one human's mapped inputs are replayed.
- Native ABI/layout correctness and performance under synchronous SD writes need
  hardware evidence. Matching symbol names and compiling do not establish either.
- Comparing identical captured fields cannot prove equality of unmeasured behavior.

Do not repair these gaps by guessing offsets or suppressing differences. Use the
first hardware evidence to prioritize the next correction.

## Build and checks

PowerShell, Python 3.8.10, cargo-skyline 3.5.0, Switch toolchain `skyline-v3`.
Dependencies are pinned in `trace/Cargo.lock`; do not run `cargo update` casually.

From the workspace root:

```powershell
$env:PATH = "$env:USERPROFILE\.cargo\bin;%MSYS2_MINGW_BIN%;$env:PATH"
$env:CARGO_NET_OFFLINE = 'true'
Push-Location pyra_mythra_clone/trace
try {
    cargo skyline build --release
    if ($LASTEXITCODE -ne 0) { throw 'Recorder build failed' }
} finally { Pop-Location }
python -m unittest pyra_mythra_clone/tools/test_trace_diff.py pyra_mythra_clone/tools/test_trace_recorder_contract.py
python pyra_mythra_clone/tools/package_trace_check.py
```

Last results: release build succeeded, **19 tests passed**, package/readback
checks passed (re-run 2026-09-28 after the deadlock fix).
`cargo skyline build --release --offline` is rejected by this cargo-skyline
version; use the environment variable above.

Input signature occurred uniquely at main+`0x1750f70` in
`reference/dumps/images/main.bin`, SHA-256
`f70c97d2bdcd00c2e81559f5abd0871e3c550b240d2005ab2e6085957a9d7613`.
The two manually declared FighterManager/FighterEntry symbol names were present.
The live process build ID has not been verified. Runtime refuses a nonmatching
signature/location. Sources for the hook are linked in `trace/README.md`.

The packager writes locally to `test_output/` and `../mod_output/new_standalone`;
it does not deploy to the SD. The latter directory also holds older loader files:
use the isolated recorder ZIP or the single NRO for this test. Old recorders
without completion footers will be rejected by the updated diff.

## Wider project context

`HANDOFF.md` preserves the earlier private-module loader checkpoint: its console
test passed, but factories were never called and it installs no playable fighter.
Copied assets and complete dump inputs already exist; do not re-extract everything.
The workspace root's `HANDOFF.md` concerns an older Game & Watch moveset and is
not the current implementation handoff.

After M0, read `../mod_files/mgw_standalone/DIAGNOSIS.md` and `ARCHITECTURE.md`
for the earlier p1-p16 clone crash chain. That experiment never produced a working
hardware clone; p16 was not tested. `upstream/clone_engine/` is the clean reference,
not the earlier patched experiment. Pair support remains substantial work.

`HANDOFF_WEAK_MODEL.md` describes the shared trace contract and delegated data/ACMD
tasks. Other contributors' files exist under `moveset/`, `tools/`, and `tests/`;
their current completion was not audited here. Inspect their reports before
claiming completion or changing their work. No sub-agents were used in this session.
