# Knowledge triage: what worked, what is open, what was wrong

Sources read (all in modpack_test_1): `.agents/rules/*` (3), root `HANDOFF.md`, `GEMINI_MYTHRA_GAMEWATCH_HANDOFF.md`,
`README.txt`, `mod_files/pyra_gamewatch_reskin/{README, HANDOFF_SPACE_BUNNY_ALPHA, HANDOFF_ARTICLE_SEARCH, REPORT_*}`,
`mod_files/mythra_gamewatch_swap/DIAGNOSIS.md`, `mod_files/mgw_standalone/{README, DIAGNOSIS, ARCHITECTURE}`,
`pyra_mythra_clone/{README, HANDOFF, ASSESSMENT, reports/trace-freeze-incident}`, `reports/console-*`, and the memory notes.
I did not read: the 924 dumped ACMD reference files, the 60+ raw crash logs, `QUESTIONS.md`, `HANDOFF_WEAK_MODEL.md`,
`tests/scenarios.md`, the Gemini `01a0a728…` task dump, the Monkey Flip / Hi3 manifests in `references/`. Those need a pass in phase 2.

**Confidence tiers used below**

- **A** hardware: the user confirmed on the console, or a console crash/log was decoded and reproduced
- **B** measured offline against dumps/binary with a script that still exists (reproducible)
- **C** read from pinned third-party source (ARCropolis, smashline, smash-script)
- **D** inference / hypothesis
- **X** refuted by later evidence

**How reliable were the authors?** The pattern is consistent: entries that cite a console log or a decoded
crash report held up; entries that cite "offline build passed" or "static reading" were wrong ~1 in 3 times.
The reviewer notes added later ("Claude review 2026-09-29", REPORT_0.8.1_RETRACTION, REPORT_0.14.0) are the
most trustworthy narrative documents in the tree. Space Bunny Alpha's own reports contain the most retracted claims;
Astra's (pmclone) reports are careful but for a path that was parked.

---

## 1. Status by project (what actually works; from the user's description + the reports)

### mythra_gamewatch_swap (hook-based swap; Mythra c06/c07 <-> real G&W c06/c07)
| Item | State | Tier |
| --- | --- | --- |
| Swap both directions via redirected pair table `[28,91,-1]` | works; return-pose displacement and G&W camera were bugs ("down-B scuffed"); v0.8.5/0.8.6 offline fixes, no console verdict recorded | A (works) / open (polish) |
| G&W fair = Shulk fair (needs injected `SwordR` bone + mesh) | works ("has done so all along") | A |
| Mythra uair = Corrin, dthrow = Luigi (raw anim copy, no retarget) | works | A |
| Mythra up-B = Mii Hero's Spin `Hi3` (start/hold/ground/air) | ground+air play; final hit timing tuned over builds .b-.g, last retest not recorded | A / open |
| G&W side-B = Diddy Monkey Flip: startup animation | fixed and confirmed ("looks and feels great") | A |
| Monkey Flip kick window | root cause found (frame 36 vs `is_end` order), fix built, no console result | B, untested |
| Monkey Flip grab/cling | **never connected**, see section 4 | open |
| Snake grenade on G&W c07 | stack overflow crash of unknown origin; feature-gated OFF (`.p4`) | A (crash), cause unknown |
| c06 support = c07 assets + motion delta | built and validated offline, console status not recorded | B |

### mgw_standalone (Clone Engine 0.3.1-beta.1 + smashline 1.6.8 rebuilt for 13.0.4)
| Item | State | Tier |
| --- | --- | --- |
| Stand-alone G&W clone ("Watch Probe") in its own CSS slot, own assets, skins, portraits | loads and plays on hardware since p6 | A |
| Mythra clone | always crashes; 16 iterations found ~6 distinct native faults (see section 5); p16 untested | A |
| Pair (Mythra + hidden Pyra) | never reached; Clone Engine identity model is one kind per entry | C (ARCHITECTURE) |
| Its by-product: `smashline_1304` overlay with all 13.0.4 offset corrections | is the plugin whose hash `5f4091ee…` is on the card; reused by pgwr | A |

### pyra_gamewatch_reskin (current, 0.14.0)
| Item | State | Tier |
| --- | --- | --- |
| Costume gate `Agent::new("eflame").set_costume([6,7])`; vanilla Pyra c00-c05, Mythra, real G&W unaffected | confirmed with the negative control | A |
| G&W model/skeleton/textures/animations on Pyra c06/c07; legs, animations look normal (0.7.0) | confirmed ("legs fixed, animations look normal") | A |
| ~124 ACMD functions, then 388 "common" scripts generated from the dumps | jab, tilts, aerials (except uair), grabs, throws "mostly right" | A |
| Down-B = vanilla Element swap, unchanged | by design | A |
| Props (`normal_weapon`: stool, manhole, fishbowl, turtle, spray) | **appear** since 0.11.0; lifetime rules in 0.11.1-.2 (fishbowl/turtle removal, ledge attack) partly fixed, not fully | A / open |
| Judge (side-B), custom status `0x1EE` | built; console result not recorded in the reports I read | B, unverified |
| Up-air breath | crashed 0.12.0/.1, disabled 0.12.2, **bridge built 0.14.0, not tested** | B, untested |
| Mythra c06/c07 moves (Corrin uair, Hero's Spin, Luigi dthrow) via the pgwr plugin | built 0.14.0, not tested | B, untested |
| Fair (bomb article), Fire (up-B), Chef (neutral-B), specials, sounds, effects, stats, taunts, Final, results | not done ("small things", user) | - |

### pyra_mythra_clone (parked)
Private NRO loader passed a console test (27 factories in private images, factories never called). Trace recorder
v0.1.1 ran on hardware after 4 fixes, first control comparison not clean. No clone exists. See section 5 for the
hardware-proven general lessons it produced.

---

## 2. Confirmed knowledge worth carrying into the handbook

Grouped by handbook file. "Src" is the file to lift it from. All tier A/B unless stated.

### 04 motion lists / animation
- `hash40(name) = (len << 32) | crc32(name)`; the motion-list animation-name hash **includes** the extension (`hash40('d01specials.nuanmb')`). (root HANDOFF, guide §7)
- `motion_list.bin`: header `magic(hash40 "motion") u64, motion_path u64, count u64`; entry = 24-byte header
  (`kind, game_script u64, flags u16, blend u8, animations u8, size u32`) + animation hashes padded to 4 + tail;
  `size % 8 == 4` -> last 2 bytes hold the **cancel frame**. Copy donor entries **whole**; round-trip assert. (guide §7, 2026-09-29 entries)
- The entry carries per-move timing (cancel frame, blend), so porting only clips gives wrong FAF (Pyra's list gave G&W jab cancel 22 vs 16). (guide 2026-09-29 "new file names")
- `motion_path` in the list is not the folder animations load from (vanilla G&W c07 names `c00`). (root HANDOFF trap 6)
- **`MotionModule::motion_kind` only echoes the request** - not evidence a clip loaded. Use `end_frame`/`frame` of the playing clip; a clip that failed to load leaves the previous clip playing. (root HANDOFF; this is the Monkey Flip root cause)
- `.prc` beside the motions are per-fighter and skeleton specific: `ik.prc`, `scharge.prc`, `update.prc`, `flip.prc`; leaving Pyra's on a G&W skeleton dislocated legs. (guide, fixed in 0.7.0, A)
- Retarget by bone-name intersection; drop donor-only tracks (`Miihead`, `Finger*4_eff`); c06/c07 skeletons of Pyra/Mythra and of G&W are byte-identical. (guide, Hi3 manifests)
- Corrin/Luigi clips worked applied raw to `elight` c07 (A) - an observation, not a rule.
- Mii option identity: `Hi1` = Stone Scabbard, `Hi3` = Hero's Spin (an entire release shipped the wrong one). Verify a move's identity from game script behaviour, not from its suffix. (guide 2026-09-26)

### 05 ACMD porting
- ACMD alone is not a port: `game_downattacku` has no `change_motion`; statuses (`PreMain/Main/Init/ExitStatus/cleanup`) are native code in `lua2cpp_<fighter>.nro`. The donor dump repo has **zero** status functions for G&W (384 files: expression 352, sound 194, game 184, effect 103). (B)
- A script that exists on the recipient but not the donor keeps running (Pyra nair/bair sword trails on G&W). Derive the script set from the motion list; port what the donor has, empty what only the recipient has. (B)
- Dump conversion artifacts (rules R14-R21 in `gen_acmd.py`): printed `frame(false, N)`; `if call == X` rendered as discarded call + hardcoded `false == true`; `methodlua2cpp::L2CFighterAnimcmd<X>Common::fn()` is a real method; six macros exist only as raw bindings (`THROW_ITEM_OFFSET`, `SHOOT_ITEM_BULLET*`, `IS_HAVE_ITEM_KIND`, `DOWN_EFFECT`, `SET_RATE_ARTICLE_V`); donor article ids index past recipient table -> `if false`; ItemModule calls lose args -> list as unported, never guess. (B)
- Dumps are evidence, not drop-in code; maintainer states conversion errors exist. `smashline-hdr/` in that repo is a formatting variant, not HDR balance data. (movemakerguide)
- `smash_script::macros::CATCH` takes 11 values and always pushes 11 (`x2,y2,z2` -> empty `L2CValue` when `None`); verbatim signature in DIAGNOSIS 2026-09-17. (C) - see graveyard X-4: this was NOT why the grab failed.
- Log parsers drift silently: assert capture-group counts at start-up and keep a fixture (Monkey Flip log tool read `vpos.x` as distance). (process lesson, B)

### 06 statuses
- Custom status ids start at `FIGHTER_<X>_STATUS_KIND_NUM`: eflame `0x1EE` (last real `0x1ED`), elight `0x1F1`, G&W c07 swap used `0x210-0x21a`, `0x220`. Keep the literal and `assert_eq!` against the const at load (LuaConst deref is not const). (B)
- 13.0.4 common table: `SPECIAL_N 0x1DC, SPECIAL_S 0x1DD, SPECIAL_HI 0x1DE, SPECIAL_LW 0x1DF`, `COMMON_NUM 0x1DC`, `MAX 0x1E1`; **no `SPECIAL_S_START`**. (B)
- Bindings gaps: `StatusModule::change_status` does not exist -> `change_status_request_from_script(ma, kind, true)`; `CancelModule` has only `enable_cancel`; no `FIGHTER_STATUS_KIND_RESET` (use WAIT); `set_default_int64` takes `u64`, `set_mesh_visibility` takes `Hash40`; a status callback must return `L2CValue::new_int(0)` (never `default()`). `MotionModule::change_motion` takes 8 args, game passes `(ma, hash, 0.0, 1.0, false, 0.0, false, false)`. (C/B)
- Do not branch on `status_kind` inside `Pre` to tell phases apart (Hi3 air entry ran ground kinetics). Register distinct Pre callbacks / pass the phase. Preserve `FIGHTER_STATUS_ATTR_START_TURN` when redirecting a special. (A, Hi3)
- Only the active form reliably gets `on_line(Main)`; dormant partner callbacks are UNVERIFIED. (guide §4.9)
- Never force state every frame (visibility, hit status, position) - masks transfer failures. (A, swap history)
- Air kinetics: take gravity/terminal speed from the donor PRC, effects from the **recipient**; check exit frame against the last ACMD frame (finisher at 47-48 was never reached). (A, Hi3 .c/.d)

### 07 articles
- Article table in `main` (13.0.4): 1845 records x 0x18 B at `0x3EACF88` `{name_ptr, pad, data_ptr, pad, flags 0x403, pad}`; blocks are per fighter; G&W has 9 articles, global 120-128: `rescue, parachute, panel, oil, octopus, normal_weapon(125), breath(126), entry, bomb`. `data_ptr` are runtime VAs, useless statically. (B, `article_table.py`)
- Article agents are registered from `main`, not from `lua2cpp_*.nro` (there is no `create_agent_article_*`); NRO exports are spelled `create_agent_fighter_*`. `Elf64_Sym` = 0x18 bytes. (B)
- **`clone_weapon` from the mod plugin works**: the `smashline` crate resolves `smashline_*` with `nn::ro::LookupSymbol` and calls the *installed* plugin. Local article id = `FIGHTER_<X>_ARTICLE_TERM + returned index`; call order = index. (A: 0.11.0 props appear; memory `smashline-clone-weapon`)
- Article files: ship for **all 8 slots** of the fighter kind, because the table is per kind and models load at fighter init (missing slot -> null-read crash at match start). G&W `normal_weapon` motion folders identical across colours; model folders differ (textures). `breath` model.nuanmb exists only in c00/c01/c02/c06. (A/B)
- `normal_weapon` has no G&W status code: its whole behaviour = owner move scripts (spawn, change_motion, remove) + descriptor. Removal-on-interrupt is native code keyed to G&W as owner; `article.rs::lifetime` re-implements it on the gated agent. (B)
- Use `FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID` (not battle object id) to index per-player state. (B)
- Breath article: donor constructor `0x33fc140` reads `*(*(main+0x52bb3b0)+0x690)` = **G&W's decoded fighter parameter object** (`param_breath` at `+0x118..0x12c`: pos_offset_x/y, life 34, move_interval 7, speed_y 8.5, scale_mul 1.9). Bridge: static parameter view for x24 during our synchronous `generate_article` + 2 WorkModule param hooks. Built; untested. (B, 0.14.0)

### 08 visibility / models
- `param_visibility_data_body` stores per-state **mesh names lowercased** (`hash40("alarmm")`), group/state names exact case. This decoded 124/134 hashes; the 10 left are the `0x7FB997A80` empty sentinel. `lhand_alarm`=`AlarmM`. Brute-force shortest hashes first; hash40's high 32 bits are the length. (B, the single most valuable fact)
- The table's node names are **bone** names, not mesh names (0 of 94 overlap the 98 meshes). (B)
- The "second G&W" on Pyra was `flagman*_FLIP` meshes + missing visibility groups: G&W's body holds 98 meshes but clips track 94; being-thrown clips had no group and drew all 98. `complete_visibility()` fixes it by writing explicit False tracks. (B; fix is A "looks normal") - a workaround; keep `build.py` docstring note (stale) in mind.
- Hammers (`RHammerM` at f11/f11/f18) and manhole (`manhole1M/2M` in `c02attacklw3`) are already animated by G&W's own clips; only the cover `ManholeM` is article geometry. Ask "does any clip already turn it on?" (`untracked_meshes.py` on the *original export*) before writing code. (B)
- Adding a mesh needs all four model files consistent (numdlb, numshb, numatb, nusktb) + bounding sphere + visibility track. (Shulk fair, A)
- Aegis sword: 42 Pyra scripts generate it; `hide_esword()` collapses `Root` basis to hide it on c06/c07 (workaround, 0.5.0).

### 10 ARCropolis config.json
- Keys `new-dir-infos` (JSON array of path strings), `new-dir-infos-base` (map), `new-dir-files`, `share-to-vanilla`, `share-to-added`. Processing order (source): reshare -> new dirs -> add missing files -> unshare -> new-dir-files. `.prc`, `.nuanmb`, `motion_list.bin` are eligible added files. (C, ARCropolis `fs.rs`)
- Fighter files load **per costume group** (`fighter/<f>/c0N`); add article files to the existing group via `new-dir-files`. Inventing new dir-infos gave `Cannot get file info range for 'Unknown'` + Data Abort 0x20 in `fighter_initialize_object_data`. Supplying a `new-dir-infos-base` guess made it *worse* (startup crash `d4200020` in arcropolis). Working template = the standalone clone pack config. (A)
- A message that also appears in known-good logs is benign (`File discovery collected path '.../config.json' but it does not exist`). Run the good pack as a control before trusting an alarming line. (A)
- Root-HANDOFF Monkey Flip failure = mod with **no** config.json at all; it is not evidence about the file-add route.

### 11 smashline / skyline
- Do **not** replace the global `libsmashline_plugin.nro` (card: `5f4091ee…`, the 13.0.4 build from `mgw_standalone/smashline_1304`). Upstream releases only support 13.0.5+. Do not touch `libarcropolis.nro`, `libarc_network.nro`, `libnro_hook.nro`. (A)
- Costume gating at install time: `Agent::new(x).set_costume([6,7])` (smashline `be3ef308`, checked against entry costume at offset 100 on the *entry*, so an entry created as Pyra c06 reports 6 while Mythra is active). Both `install_script` and `install_status_scripts` are filtered. (A gate; C mechanism)
- Skyline hooks: `skyline::patching::Patch::in_text(off).nop()/data()` - a plain store into `.text` faults (Data Abort at the patch site). (A, p9->p10)
- Exclusive create (`O_EXCL`) on the SD returns result 514 (0x202); non-exclusive works; the "unregistered runtime directory" theory was wrong. (A)
- Skyline log is a TCP stream; the thread dies before its last lines arrive. For crash-adjacent lines also write to a file on the SD (`sd:/ultimate/<x>_log.txt`, open/append/close per line). (A)
- A non-reentrant `Mutex` held across game-mutating calls deadlocks (Main callback fires again for a status change on the same thread). Plan under lock, apply outside; thread-local re-entrancy guard. (A, freeze fixed)
- Smashline Main fires twice in a frame when a status changes (regular + on-change); rows are `first-wins`. (A)

### 12 native / offsets (13.0.4 only)
- ExeFS `main` NSO0 42,910,639 B sha256 `77936fe2…d92e`, build id `3eae0063…`; flat image 86,672,752 B (`f70c97d2…`), VA == file offset for `.text` (`0x100`), `.rodata 0x39C8000`, `.data 0x4F16000`; `.bss` absent. Console crash reports: `base + offset` = flat-image offset. (B)
- Fighter entry (observations): `+0x14` count, `+0x18/0x1c` kinds, `+0x41` costume, `+0xe0` entry id, `+0x4160` sub-fighter ptr array, `+0x41f0` handoff pose, `+0x5918..a` active/target index, `+0x5920` switch state (6 = begin). (B)
- Swap hooks installed on this binary: `0x35c23a4, 0x17e5c00, 0x658af0, 0x655484, 0x64f9e8, 0x64fbcc, 0x6516e4, 0x1492a3c, 0x65a760, 0x656720, 0x658328` + 4 sound-id null guards `0x656fdc, 0x656e80, 0x656470, 0x655fc8`. (B/A)
- Corrected smashline tables: fighter names `0x4f80e20`, weapon names `0x5185bd0`, weapon owner names `0x5188240` (upstream is +0x1000); upstream weapon hooks carry a bogus `+0x5B0`; path hooks `-0x40` land in prologues; `FilesystemInfo` at `main+0x5331f20` (not `…2f20`); costume lookup must use `FighterManager::get_fighter_information(...).fighter_color` (table at `0x5324680` is null); dev hot-reload reads `0x52c1760` as a pointer -> disabled. (A, mgw_standalone p2-p7, `offset-audit.json`, `native-support-audit.json`)
- Addresses in fighter *status* dumps are relative to that fighter's own NRO (with a 0x10 prefix before `NRO0`), never `main`. NRO import table records are 24 B (`target,type 0x402,index,0`), index addresses the NRO's own symbol table (not `main_symbols.json` position). (B)
- Constant table: `lua2cpp_common.nro` `construct_bind_const_value_table` 0x52d8c0; 0x4c0d XXH64(seed -1) name hashes at 0x6a5b70; `FIGHTER_GAMEWATCH_GENERATE_ARTICLE_NORMAL_WEAPON` = slot `0xeb1c`. (B, `constmap.py`)
- Fighter ids: Mythra `elight` kind 91, Pyra `eflame` 90, G&W `gamewatch` 28 (clone-engine ids are dynamic - resolve by name).
- Ghidra: full 86 MB `main.bin` is not viable (17 min, stalls at 0x22b01d0); 1.4 MB NROs are minutes. Use Jython `.py` scripts. For "which function references string X": adrp/add scan over the flat image (`find_rodata_xref.py`). (A)

### 13 swap / pairs
- Pair = one fighter entry with sub-fighter table redirected `[90,91,-1]` -> `[28,91,-1]`; Element changer machinery is native. (A)
- Pose repair must run **after** the native restore returns (an early nested WAIT callback got overwritten by the original departure pose). (A, 2026-09-15)
- Drop any held live item before the owning body goes dormant. Per-entry state in fixed arrays tagged with owner id, cleared at boundaries. (A/B)

### 14 clone engine
- Clone Engine keys identity by **entry**, one custom kind per entry; a two-base pair fails `clone_kind_of_object`, `param_override_kind`, `ENTRY_FIGHTER_BOMA`. Needs a maintained fork for pairs. (C)
- Mythra clone crash chain (each a hardware crash, decoded): Smashline factory hook at `+0x5b0` (1) -> input-hook float-as-pointer (2) -> costume table null (3) -> `FilesystemInfo` (4) -> wrong global addresses / model lookup `have` null (5) -> motion-bind state 5 skips holder allocation at `0x49748c` (`main+0x497350` routine) (6) -> holder+0x10 vtable+0x38 returns 0 at `0x4984d4` (7) -> `bunshin` body model file `0x34e65` not resident (`0x35c23a8`) (8). p16 (route body lookup with stride 0x18 via `0x35c2040`) untested. (A)
- Mythra's esword/winsword lists reference **Pyra's** esword dir; Mythra owns `esword` + `bunshin` articles with no separate bunshin model (uses the body model). (B)
- BNTX portrait rename in-place works only for the verified single-leaf layout; do not generalize. (B)
- Need the extra dump list: `mgw_standalone/MISSING_DUMPS.md` (18 sound banks). (B)

### 03 dumps
- Live dumping = `libarc_network.nro` on the SD **and** Smash running, port 43022, close ArcExplorer during scripted extraction; "refused" means the plugin is missing, not that the tool is broken. Region 2 only. (A, memory)
- Two "dumps" in `source_audit` are GitHub tree listings only; `rubendal/ssbu` holds diffs (404s on raw fetch). Cite only files that exist locally. (A)

### 02 toolchain
- Windows: MSYS2 (`mingw-w64-x86_64-binutils gcc`) first on PATH; `cargo +stable-x86_64-pc-windows-gnu install cargo-skyline` (3.5.0 matches skyline-rs `6b52d32`, judge by commit date not version); MSVC fails (GNU `link.exe` first on PATH); bundled rustup dlltool cannot build import libs. Run builds from `cmd` (`build_plugin.cmd`): PowerShell reports exit 255 while cargo says Finished and NRO packaging happens after that line. (A)
- `build.py` needs the **cp312** interpreter (`scratch/py312`), system Python 3.8 cannot import vendored `ssbh_data_py`. `cargo skyline build … --offline` fails until `cargo fetch` was run once online.
- **After every deploy compare the packaged NRO hash with the built NRO hash** (a deploy printed the previous build's hash). (A)
- `Cargo.toml` uses git deps pinned by `rev`; `[patch]` with the same git URL is rejected by cargo. (A, measured 2026-09-17; contradicts guide §1, see R-6)
- `install-to-card.sh`: finds card by contents, backs up, stages `.new`, verifies, rolls back. Installing is the agent's job, running the game is the user's.

### 17 hardware test protocol
- Hand over: exact file + SHA-256, exact SD destination, numbered short test, which log lines prove what, a vanilla negative control. Log prefixes `[MGW-*]`, `[PGWR*]`; file log `sd:/ultimate/pgwr_log.txt` reset per run.
- One change per build for anything that mutates state (two changes at once turned a diagnosis into a revert). A change that moves a crash *earlier* is a regression: revert, do not stack a third variant on the same premise.
- An invalid test is not a code failure: verify the card really holds the build before interpreting (`grep -c` a marker in the NRO). The "none of the moves are visible" report was a 0.8.x card.
- Compilation, offline byte-compare and lint are never validation.

---

## 3. Refuted / retracted claims (goes to `handbook/graveyard.md`)

| ID | Claim | Where | Verdict |
| --- | --- | --- | --- |
| R-1 | "A mod NRO cannot register a cloned article; the global smashline must be patched (`pgwr_article.rs`); install three files" | guide "DECIDED: global smashline patched", pgwr README top+"Installed" sections, `install-to-card.sh` default | **X.** The `smashline` crate calls the installed plugin via LookupSymbol. The rebuilt global plugin (0.10.0) crashed; 0.11.0 mod-side `clone_weapon` made props appear. README and script are stale. **Armed hazard.** |
| R-2 | "`clone_weapon` unworkable, provable" (weapon table displaced by 0x1000) | Space Bunny run 3 | **X.** True for upstream `be3ef30` but the card runs the corrected build. Claude review 2026-09-29 §2 |
| R-3 | "Second G&W is the dormant Aegis/DIVER partner" | README, run-2 RESULT | **X.** It was the untracked `flagman*_FLIP` (and all-98-mesh) rendering; fixed by explicit visibility tracks |
| R-4 | "Grab fails because of the 8- vs 11-argument CATCH (three-value underrun)" | guide 2026-09-15 "CORRECTED", DIAGNOSIS 2026-09-17 | **X.** Measured in `.h`: 8-value hand push and 11-value macro create the same live entry; arity is not the cause. Keep the macro as correct shape |
| R-5 | "Monkey Flip failed because the slots pointed at non-existent files" vs "new file names load fine" | root HANDOFF vs guide 2026-09-29 (two offline entries) | **Unresolved but narrowed.** Fix that worked = map slots to existing names and overwrite. The failing mod had no config.json. Articles with `new-dir-files` into existing costume groups loaded on hardware (0.11.0). The 0.8.0 isolated file-add probe (`FILEADD … NEW FILE LOADED`) result is **not recorded anywhere I found** - rerun as a labelled experiment |
| R-6 | "`[patch]` sections must stay" | guide §1 vs root HANDOFF / pgwr Cargo.toml | Cargo rejects same-source patches; pgwr builds without. Check swap `Cargo.toml` and normalise |
| R-7 | "Breath crash = null frame/timing tracker; five readers; guard the caller (options 1-3)" | REPORT_0.12.2 | **X (interpretation).** `+0x690` is G&W's decoded fighter param object; crash site and PC facts stand, the cure is the 0.14.0 param bridge (untested) |
| R-8 | "R22: dead `set_int64` hammer call needs `set_mesh_visibility`" | 0.8.0 | **X**, retracted in 0.8.1; hammer clips self-animate. Stale `complete_visibility` docstring in `build.py` still says otherwise |
| R-9 | "Manhole is a separate open bug" | 0.10.0 RESULT addendum | Half body mesh (works), half article. Not separate |
| R-10 | FSS "runtime-created directory not resolvable" for result 514 | pmclone freeze report run 2 | **X.** `O_EXCL` |
| R-11 | `life()` fuse hook fixes Snake grenade | DIAGNOSIS .p1-.p3 | **X.** Stack overflow ~14 MB away; grenade is not the cause; disabled |
| R-12 | "`new-dir-infos-base` empty causes the null read; fill it from the donor" | 0.10.0 fix | **X.** Made it crash at startup. Both `new-dir-infos` and the base guess were wrong; costume-group `new-dir-files` is the working shape |
| R-13 | "`CATCHGEO` centre equals fighter origin / box never moves" | `.i` build | timing artifact (value written after the creating frame) |
| R-14 | "A box of radius 8 enclosed the victim" | `.g` | **X.** Distance ignored the +2.5 y offset and airborne height; victim was outside |
| R-15 | "`GrabModule::size` reads back per-box size" | `.h` | **X.** Returns same value for all boxes |
| R-16 | Gemini handoff: "no implementation exists", paths `user-specific paths`, `ArcExplorer export directory` | GEMINI handoff | historical; entire doc superseded, archive |

Method note: most of these were caught only because a later agent reran the measurement with a control (or
because a console log disagreed with an offline result). That is the rule to write down: **every non-trivial
claim needs a control run before it enters the handbook.** (The "NO SHORTCUTS" violation table in
HANDOFF_SPACE_BUNNY_ALPHA is not a claim list but a roadmap; carry it into `projects/pgwr/TODO.md`.)

## 4. The Monkey Flip grab: consolidated state (`handbook/15_grabs_catch.md`)

Eliminated by measurement: box exists (`CATCHBOX grab0/1/2=true`); cleared exactly on the donor schedule; arity;
grab module inactive (`set_rebound(true)`, `sleep(false)`, size mul, check_front all accepted and held); anchor `top`
reads back as fighter origin (engine-side anchor); donor status code and ACMD contain nothing else grab related
(`SpecialSJump*` has no Grab/Catch/Link call - the engine converts box to catch); hand-built `set_catch` + `LinkModule::link`
+ status request **freezes the console** (do not do it; `set_catch` alone gives `is_catch` but publishes no
`LINK_NO_CAPTURE` node and does not route the victim).

Never actually tested: a live box that truly contains the victim (victim was outside in every prior build, y offset).
Specified next experiment: drop or invert the y offset (0.0 then -2.5, radius 8) and log box-to-victim distance;
if it still fails, issue `CATCH` from a status the engine already knows to test "Smashline-added statuses are not
evaluated for grabs". Related unknown: what state the leap status must be in for the engine to accept the box
(Diddy's native status vs ours).

## 5. What the failed/parked projects still teach

- pmclone: Clone Engine gives exactness only if the clone runs the *original* vtable/lua2cpp and every "is this Pyra/Mythra"
  site accepts the clone; ~150 raw immediates against kinds 90/91 are noise. Relocating machine code gives independence but not editability.
  Fidelity test idea (differential traces vs vanilla) is sound, but the reset gaps (attack serial, article animation phase, CPU AI) were never solved;
  zeroing `INT_ATTACK_SERIAL` or `MotionModule::set_frame` on a weapon crashes (`status_Attack_Main_button` assert).
- The whole route was parked by the user on 2026-09-29 in favour of the reskin ("no shortcuts" rules in `AGENT_RULES.md`).

## 6. Consistency problems to fix in the docs themselves

1. Three "guide" files with overlapping scope (`movemakerguide` - sourcing, `move_replacement_guide` - everything, `move_reployment_guide` - one 2026-09-29 entry that duplicates a lessons-log entry and is marked "NOT YET TESTED"). Fold all into the handbook, one topic per file.
2. `move_replacement_guide.md` sections describing the *swap* project (§10 inventory, §11 drift, status-id tables) belong under `projects/mgw_swap`; its lessons log contains entries whose "DISPUTED" banners are the only sign they are wrong.
3. The pgwr README opens with 0.14.0, then "0.8.1 phase 2", then "Current state 0.9.0", then "Known gaps in 0.3.0"; rewrite as one STATUS.md.
4. Three different "next console test" blocks.
5. Path drift: `<user>`/`<user>`, `ArcExplorer export directory`, `Downloads\ArcExplorer_win_x64`, `F:` SD, `192.168.2.166`. All go to `paths.toml`.
6. `move_replacement_guide` §4 rule 5 "Do not target down-B" is a project rule for the swap, not a general rule; in pgwr down-B is the vanilla swap "by design".
