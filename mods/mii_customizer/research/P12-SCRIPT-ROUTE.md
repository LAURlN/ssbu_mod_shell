# P12-SCRIPT-ROUTE - how mod code can own a Mii Gunner move script per fighter object

> **Coordinator review, 2026-10-07.** `check_p12_script_route.py` rerun: 17/17, exit 0
> (`--neg` not rerun). Accepted as the fact base for the first-move design. What the
> coordinator takes from it: the console's Smashline is the user's 13.0.4 build `5f4091ee...`
> and must not be replaced; a script registered for agent `miigunner` receives the fighter
> object and can reach the entry id, i.e. the same input this mod's saved-ID lookup uses;
> originals can be called (`original_acmd`, `original_status`); an added motion needs the
> clip, a rebuilt `motion_list.bin` and its scripts; nothing in the framework or the other
> mod is Mii-specific ("not found"); the game's own script table is per agent object, filled
> by `sv_set_function_hash` (so a direct hook is possible but is a second mechanism). The
> spike compiles; nothing of it has run. All behaviour for Miis stays D.


Task: P12-SCRIPT-ROUTE (Space Bunny Alpha). Facts only: reading sources, binaries and existing
notes plus one compile-only spike. Nothing is run in the game, nothing installed, no emulator,
no SD, no commits, no edits to ssbu_mod_new or to framework plugins.

Status: DONE (written and extended 2026-10-07).

Evidence tiers used here: **A** = console-tested (always in ssbu_mod_new, cited as theirs),
**B** = offline measurement reproduced by a script in `scratch/2026-10-07_P12-SCRIPT-ROUTE/`
and re-checked by `evidence/P12-SCRIPT-ROUTE/check_p12_script_route.py`,
**C** = pinned third-party source (repository + commit stated), **D** = hypothesis.
Rule of this task: anything about in-game behaviour that THIS mod has not tested is D here,
whatever tier it has in ssbu_mod_new. ssbu_mod_new content is cited by path + line only;
no handbook text is copied beyond short quotations of the cited lines.

Paths: `gamedata/...`, `kb/...`, `mods/...` are workspace-relative. `research/...`,
`plugin/...`, `scratch/...`, `builds/...`, `evidence/...` are relative to `mods/mii_customizer/`.
Framework source used for C-tier quotes: cargo cache
`~/.cargo/git/checkouts/smashline-0ccc30393002c4aa/be3ef30`, repository
`https://github.com/hdr-development/smashline`, commit
`be3ef308ed8e479922da192a391e0684184af2af` (`git log -1` = "Merge pull request #84 ..."),
workspace `version = "1.6.7"` in its `Cargo.toml:5`. Vendored copies of the plugin source
also exist under `mods/ssbu_mod_new/src/mgw_standalone/smashline_1304` (version `1.6.8`,
repository `https://github.com/WuBoytH/smashline-2`) and
`mods/ssbu_mod_new/src/mgw_standalone/vendor/smashline-release/smashline-1.6.8`.

## Short answers

- **Q1.** The console runs one script framework: the global `libsmashline_plugin.nro`, card
  hash `5f4091ee…`, "the 13.0.4 build from `mgw_standalone/smashline_1304`" - recorded at
  `mods/ssbu_mod_new/handbook/11_smashline_skyline.md:5` (their tier A) and re-confirmed per
  install at `mods/ssbu_mod_new/CURRENT_INSTALL.md:254`. ssbu_mod_new builds against the four
  git crates pinned in `mods/ssbu_mod_new/src/pgwr/plugin/Cargo.toml:55` (rev comments) and
  `:59` (dependency lines), locked to smashline commit
  `be3ef308ed8e479922da192a391e0684184af2af` at
  `mods/ssbu_mod_new/src/pgwr/plugin/Cargo.lock:458`.
- **Q2.** Registration API (C, be3ef30): `Agent::new(name)` + `set_costume` + `game_acmd` /
  `effect_acmd` / `sound_acmd` / `expression_acmd` + `install` (builder.rs:103, :114, :149,
  :159, :169, :180, :255); `status(...)` and `on_line(...)` (builder.rs:192, :207);
  originals via `original_acmd` (lib.rs:440) and `original_status` (lib.rs:445), both used
  in ssbu_mod_new (mgw_swap/src/hero_spin.rs:521, pgwr gaogaen_throw_b.rs:88). Costume gate
  is install-time (handbook/11_smashline_skyline.md:6: "A gate; C mechanism"; the gate itself
  observed on their console at evidence log line 8). Per-frame callback example with tier-A
  console output. Everything in this mod's own use of it = D until it runs on hardware.
- **Q3.** Inside a script: argument is `&mut L2CAgentBase` (builder.rs:3), take
  `agent.module_accessor` (chrom_jab.rs:197), then
  `WorkModule::get_int(agent.module_accessor, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID)`
  exactly as at ssbu_mod_new mythra/mod.rs:140 and in this mod at plugin/src/lib.rs:408
  inside `resolve` (plugin/src/lib.rs:385) - so yes, a script sees the same input
  `resolve` needs; the saved-ID lookup itself is `read_player` (plugin/src/lib.rs:254),
  gated by `logic::decide` (plugin/src/logic.rs:253) with
  `ACCEPTED_KINDS` (plugin/src/logic.rs:14).
- **Q4.** ssbu_mod_new rebuilds `motion_list.bin` with
  `tools/build_hero_neutral_b_assets.py` (`entry_bytes` at :66, write at :126, round-trip
  assert at :128) and declares the new clip per costume group through config.json built by
  `src/pgwr/build.py:1278` / group append at `:1365` / invariant at `:1388` / key at `:1394`.
  One added body motion needs: the new `.nuanmb` clip (declared), the rewritten
  `motion_list.bin` (replaced, not declared), and the ACMD scripts the entry names
  (`game_<owned>` etc., packed at build_hero_neutral_b_assets.py:69). Declared new names
  loading on the console is their tier A (handbook/04_motion_lists_animation.md:14, log
  lines 18 and 57). For this mod: D.
- **Q5.** Not found. No Mii-specific agent-name, costume-slot or custom-special-variant
  handling in ssbu_mod_new's plugin code or in the pinned framework source. Only hits are
  generic victim tables, comments and one enum constant (`MiiGunnerBlaster = 0x33,`). Full
  grep accounting in Q5.
- **Q6.** The hash -> function table is NOT global: it lives inside each freshly created
  animcmd agent object. The NRO export `create_agent_fighter_animcmd_game_miigunner`
  (0x47850, size 0x1b44) picks a branch by a 40-bit switch over arg0 (19 keys, one decoded
  as hash40 `miigunner`), allocates the object (`operator new(0xc8)`), constructs it, then
  registers every script with `lib::L2CAgent::sv_set_function_hash(void*, phx::Hash40)`:
  196 calls in the miigunner leaf (207 in the whole dispatcher), each passing the script
  body's address in this NRO's .text in x1 and the hash40 in x2. `game_attacks3` is
  registered at 0x47e34 with hash 0x0d28325277 and body 0xbc500. Details + exact words in Q6.
- **Q7.** The spike compiles. `cargo skyline build --release -- --offline` with
  `CARGO_TARGET_DIR=../../../builds/.cache/p12-script-route` from
  `scratch/2026-10-07_P12-SCRIPT-ROUTE/spike/` exited 0, zero warnings, NRO 32768 bytes,
  sha256 `728c1ce7bec8b30b8943441e5f109ac71401b4b51e48931c3252ae782cb586a1` (byte-identical
  across a clean rebuild). 18 named undefined syms; four `smashline_install_*` names present
  as strings for runtime `LookupSymbol`. Compiling proves compiling only - load/behaviour = D.
- **Q8.** See the table. No recommendation, per the task.

## Q1. What is on the console for scripts

Recorded in ssbu_mod_new (cited by path + line; their tier A where marked):

- `mods/ssbu_mod_new/handbook/11_smashline_skyline.md:5` (tier A):
  "Do **not** replace the global `libsmashline_plugin.nro` (card: `5f4091ee…`, the 13.0.4
  build from `mgw_standalone/smashline_1304`). Upstream releases only support 13.0.5+. Do
  not touch `libarcropolis.nro`, `libarc_network.nro`, `libnro_hook.nro`. (A)"
  -> one script framework (Smashline), plus ARCropolis / arc_network / nro_hook as the other
  protected plugins; upstream smashline releases are 13.0.5+ and would be wrong for this dump.
- `mods/ssbu_mod_new/CURRENT_INSTALL.md:254` (re-stated on every install, e.g. backup
  `sd-backup-20261003-021215`): "Framework installation OFF; all four" /
  `:255`: "protected plugins byte-unchanged (smashline still `5f4091ee…`)." -> the card
  plugin's identity is tracked by hash in CURRENT_INSTALL.md; the install script can leave
  the framework alone (`--no-smashline`).
- Crate version / commit ssbu_mod_new builds against -
  `mods/ssbu_mod_new/src/pgwr/plugin/Cargo.toml:55`-`:58` list the exact revisions and say
  "Do not run `cargo update`" (`:54`):
  `:55` "skyline 0.6.0        skyline-rs    6b52d321275639f26c2371d8142550ba0013a5e4",
  `:56` "skyline_smash 0.1.0  skyline-smash 315e4e8bebb460ebb9f02f30f07b0f13883ba3d6",
  `:57` "smash_script 0.1.0   smash-script  fdc6144a0a429ce37b304733531edcb76c8f2578",
  `:58` "smashline 0.1.0      smashline     be3ef308ed8e479922da192a391e0684184af2af".
  The dependency lines `:59`-`:62` deliberately carry no `rev` (comment at `:46`: "Measured on 2026-09-17 that
  was 327" type errors "plus `FighterEntry` is ambiguous" at `:47`); the lock honours the pins:
  `mods/ssbu_mod_new/src/pgwr/plugin/Cargo.lock:456` `name = "smashline"`, `:457`
  `version = "0.1.0"`, `:458` `source = "git+https://github.com/hdr-development/smashline#be3ef308ed8e479922da192a391e0684184af2af"`.
- The card plugin's own source tree (what `5f4091ee…` was built from):
  `mods/ssbu_mod_new/src/mgw_standalone/smashline_1304/Cargo.toml:5` `version = "1.6.8"`,
  `:7` `description = "An object script replacement engine for Super Smash Bros. Ultimate"`,
  `:9` `repository = "https://github.com/WuBoytH/smashline-2"`.

Tiers: the card facts and their "do not replace" rule are marked (A) in their handbook; the
crate pins are build files (B, read directly). Note the deliberate version split: the build
crate is hdr-development/smashline `be3ef308` (workspace 1.6.7) while the installed plugin
source is WuBoytH/smashline-2 1.6.8 - both trees declare the same four
`smashline_install_*` import names (checked; see Q7), but whether the card's `5f4091ee…`
binary exports exactly what the spike needs at load is **not** verified here (D).

## Q2. The API as used in ssbu_mod_new

All examples are `mods/ssbu_mod_new/...` (reference only, never edited).

**Registering ACMD game / effect / sound / expression scripts** - their tier for the
registration call itself is C (pinned source, be3ef30); the *effect on the console* is
separately A where noted:

- `src/pgwr/plugin/src/acmd/chrom_jab.rs:353` `pub fn install() {`, then
  `:354` `let mut agent = Agent::new("eflame");`,
  `:355` `agent.set_costume(crate::TARGET_COSTUMES.to_vec());`,
  `:359` `agent.game_acmd("game_attack11", game_attack11, Priority::High);`,
  `:362` `agent.effect_acmd("effect_attack11", effect_attack11, Priority::High);`,
  `:365` `agent.sound_acmd("sound_attack11", sound_attack11, Priority::High);`,
  `:368` `agent.expression_acmd("expression_attack11", expression_attack11, Priority::High);`,
  `:372` `agent.install();` (script body declared at `:190` as
  `pub unsafe extern "C" fn game_attack11(agent: &mut L2CAgentBase) {`).
- Framework side (C, be3ef30): `crates/smashline/src/builder.rs:149`
  `pub fn game_acmd(&mut self, name: impl AsHash40, function: AcmdFunction, priority: Priority) -> &mut Self {`
  and the same shape at `:159` (`effect_acmd`), `:169` (`sound_acmd`), `:180`
  (`expression_acmd`); `:255` `pub fn install(&self) {` -> `:257`
  `crate::api::install_acmd_script_costume(` (the import resolved at runtime; see Q7).
  Priorities: `crates/smashline/src/lib.rs:34` `pub enum Priority {` (`Low`, `Default`,
  `High`).
- Console tier A for replacement scripts actually running: their Monkey Flip note
  `CURRENT_INSTALL.md:772` "**INSTALLED: 0.20.7 independently verified. TESTED 2026-10-02
  (T-0056): exercised on hardware" / `:774` "by the user. The T-0053 section below is its
  successor and is what 0.20.17 now ships.**".

**Registering / wrapping a status function** (C for the API; A for the hero machine):

- `src/pgwr/plugin/src/mythra/hero_neutral_b/fighter.rs:349`
  `let mut agent = Agent::new("elight");`, `:351`
  `agent.status(Pre, *FIGHTER_STATUS_KIND_SPECIAL_N, redirect);` - a Pre hook on the vanilla
  special-N status that redirects into the mod's own status kinds; `:356`
  `agent.status(Exec, HOLD, hold_exec); agent.on_line(Main, lifecycle); agent.install();`.
- `src/pgwr/plugin/src/mythra/hero_side_b/registration.rs:47`
  `agent.status(Pre, *FIGHTER_STATUS_KIND_SPECIAL_S, callbacks.entry.pre);` (same file
  registers Main/End/Exec/CheckAttack for owned kinds, `:45`-`:66`, closing with `:66`
  `agent.install();`).
- Framework side (C): `builder.rs:192` `pub fn status<M: StatusLineMarker, T>(`.
- Their tier A: the hero status machine's owned status 0x1f5 playing its clip on the console
  is in `evidence/2026-09-30_pgwr_0.18.0/pgwr_log_from_boot.txt:18` (quoted in Q4). The
  gaogaen throw wrapper is shipped but "All gameplay unverified; nothing here has been run
  on hardware" (`CURRENT_INSTALL.md:246`).

**Calling the original script / status from a replacement** - yes, two framework APIs plus
skyline's `original!()`:

- `crates/smashline/src/lib.rs:440` `pub fn original_acmd(agent: &mut L2CAgentBase, name: Hash40) -> AcmdFunction {`
  and `:445` `pub fn original_status<L: StatusLineMarker, T>(`.
- Used: `src/mgw_swap/src/hero_spin.rs:521`
  `original_acmd(agent, Hash40::new(name))(agent);` (their comment at `:516`: "The vanilla
  branch. `original_acmd` is the script pointer smashline captured"); status originals at
  `src/pgwr/plugin/src/status/gaogaen_throw_b.rs:88`
  `original_status(Pre, fighter, *FIGHTER_STATUS_KIND_THROW)(fighter)`,
  `src/pgwr/plugin/src/status/dk_cargo/mod.rs:125`
  `original_status(Pre,fighter,stock)(fighter)`, `src/mgw_swap/src/hero_spin.rs:252`
  `return original_status(Pre, fighter, *FIGHTER_STATUS_KIND_SPECIAL_HI)(fighter);`,
  `src/mgw_swap/src/monkey_flip_status.rs:136`
  `return original_status(Pre, fighter, *FIGHTER_STATUS_KIND_SPECIAL_S)(fighter);`.
- For direct skyline hooks (not the ACMD/status builder): `original!()` -
  `src/pgwr/plugin/src/status/gaogaen_throw_b.rs:72`
  `#[skyline::hook(replace = smash::lua2cpp::L2CFighterCommon_sub_is_not_throw_status_kind)]`
  with `:78` `original!()(fighter, kind)`.
- No `original_acmd` call in `src/pgwr/plugin/src/` (grep: 0 hits); it is used in
  `src/mgw_swap/` (grep: 1 call).

**Per-frame callbacks** (C API, A output):

- `builder.rs:207` `pub fn on_line<M: StatusLineMarker, T>(`; example
  `src/pgwr/plugin/src/acmd/mod.rs:196` `unsafe extern "C" fn gate_trace(agent: &mut L2CAgent) {`
  registered at `:248` `.on_line(Main, gate_trace)` under `:245` `#[cfg(feature = "logging")]`
  - that registration is feature-gated and the installed builds say
  `CURRENT_INSTALL.md:253` "features `snake-neutral-b,hero-side-b`, `logging` **off**".
  The other per-frame site, `mythra/hero_neutral_b` `lifecycle` at fighter.rs:356, did run
  on their console: `evidence/2026-09-30_pgwr_0.18.0/pgwr_log_from_boot.txt:8`
  `[PGWR] MYTHRA GATE ACTIVE: entry 0 is Mythra, running c06/c07 move replacements, reported colour 7`
  (their tier A; that exact line format is mythra/mod.rs's, the acmd/mod.rs one is a
  sibling). Caveat they record: `handbook/11_smashline_skyline.md:11`
  "Smashline Main fires twice in a frame when a status changes" (their tier A).

**How the fighter is named / filters** (C, be3ef30):

- Name: an agent-name string, not a kind number - `builder.rs:103`
  `pub fn new(agent: impl AsHash40) -> Self {` (strings hash40'd); ssbu_mod_new passes
  `"eflame"` (chrom_jab.rs:354) / `"elight"` (fighter.rs:349).
- Costume filter: `builder.rs:114` `pub fn set_costume(&mut self, costumes: Vec<usize>) -> &mut Self {`,
  used as `set_costume(crate::TARGET_COSTUMES.to_vec())` (chrom_jab.rs:355); their
  `handbook/11_smashline_skyline.md:6`: "Costume gating at install time:
  `Agent::new(x).set_costume([6,7])`" with tier "(A gate; C mechanism)".
- No other filters (no kind-branch, no entry-id-branch in the builder API) - a branch on
  saved-ID must live inside the script body (this is the "with a branch" mechanism in Q8).

For THIS mod: registering anything for `"miigunner"` this way is untested = **D**, however
well it works for eflame/elight.

## Q3. Inside a script function: arg -> BOMA -> entry id

1. The ACMD function argument is the agent: `crates/smashline/src/builder.rs:3`
   `pub type AcmdFunction = unsafe extern "C" fn(&mut crate::L2CAgentBase);`.
2. Module accessor on it: `src/pgwr/plugin/src/acmd/chrom_jab.rs:190` declares the fn,
   `:197` uses `agent.module_accessor,` (ArticleModule call) - the field is on the argument.
3. Entry id: `src/pgwr/plugin/src/mythra/mod.rs:140`
   `let id = WorkModule::get_int(agent.module_accessor, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID) as usize;`
   - exactly this pattern, same argument shape, in a live script-adjacent callback. Also
   `src/pgwr/plugin/src/article.rs:252` `unsafe fn entry(boma: *mut BattleObjectModuleAccessor) -> usize {`
   / `:253`
   `WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID) as usize` with their
   comment `:249`-`:250` "so the battle object id is not guaranteed to be below 8; the entry id is".

Does that yield what plugin/src/lib.rs needs? **Yes.** This mod's identity chain:

- `plugin/src/lib.rs:385` `unsafe fn resolve(parent: u64) -> Ident {` casts
  `:386` `let accessor = parent as *mut BattleObjectModuleAccessor;` and reads
  `:408` `facts.entry_accessor = WorkModule::get_int(accessor, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);`
  then `:411` `logic::identify(&facts)` (the function behind it:
  `plugin/src/logic.rs:211` `pub fn identify(f: &Facts) -> Ident {`). A script's
  `agent.module_accessor` is the same
  `*mut BattleObjectModuleAccessor`, so a script can do the identical read (it *is the
  same call*: compare mythra/mod.rs:140 with plugin/src/lib.rs:408).
- The saved-ID lookup is `plugin/src/lib.rs:254`
  `unsafe fn read_player(p: u32) -> Option<(u32, [u8; 4])> {` (called at `:534`
  `if let Some((id, _)) = read_player(ident.player as u32) {`), with the static table at
  `plugin/src/logic.rs:18` `pub const TABLE_BASE: usize = 0x530_7760;` and the gate
  `plugin/src/logic.rs:253`
  `pub fn decide(ident: &Ident, kinds: &[i32], slot_id: u32, store: &Store, presets: &Presets, field: usize) -> Decision {`
  checking `:14` `pub const ACCEPTED_KINDS: [i32; 1] = [KIND_MIIGUNNER];`, invoked from
  `plugin/src/lib.rs:538`:
  `logic::decide(&ident, &logic::ACCEPTED_KINDS, slot_id, &STORE, &PRESETS, field)`.
- Kind constant already console-confirmed for this mod: `plugin/src/logic.rs:10`
  "`FIGHTER_KIND_MIIGUNNER` on 13.0.4: the binding's constant, confirmed on the console",
  `:11` "(`evidence/2026-10-05_gate2/RESULT.md`, every Gunner line `kind=74`).", value at
  `:12` `pub const KIND_MIIGUNNER: i32 = 0x4a;`. The player table is "console-confirmed for
  local players 0 and 1" (`plugin/src/logic.rs:16`).
- Background on the hot path: `research/P7-PRESET-ENGINE.md:113`
  `## 2. The hot path (B, from the disassembly of the staged NRO)`.

So a script body can compute the same `(kind, entry id, saved Mii id)` tuple `resolve` +
`read_player` compute today, entirely inside the ACMD function. What is *not* established:
that a `game_attacks3` replacement for `"miigunner"` fires on hardware at all (D).

## Q4. Motion change: motions not in the original motion_list.bin

**Console fact (their tier A):** `mods/ssbu_mod_new/handbook/04_motion_lists_animation.md:14`
states "**Declared new names do load (A, 2026-09-30):**" and that Hero neutral-B "adds new
kinds (`pgwr_hero_special_n_start` ...) naming new clips (`pgwrherospecialnstart.nuanmb`
...) listed under `new-dir-files` `fighter/elight/c0N`", evidenced by
`mods/ssbu_mod_new/evidence/2026-09-30_pgwr_0.18.0/pgwr_log_from_boot.txt:18`
`[PGWR-HERO-N] CLIP status=0x1f5 motion=0x1920438ca3 frame=1.0 end=7.0` and `:57`
`[PGWR-HERO-N] CLIP status=0x1f9 motion=0x14c7a6c6ff frame=1.0 end=73.0` - the new clips'
own lengths (7, 73 frames).

**Which tool rebuilds motion_list.bin:**
`mods/ssbu_mod_new/tools/build_hero_neutral_b_assets.py` -

- `:66` `def entry_bytes(entry, owned, clip):` rewrites one motion entry: `:69`
  `struct.pack_into('<QQ', raw, 0, base.hash40(owned), base.hash40('game_' + owned.replace('_', '')))`
  (offset 0 = new kind hash, offset 8 = the `game_...` ACMD script hash the entry runs),
  `:70` `struct.pack_into('<Q', raw, 24, base.hash40(clip))` (the clip file-name hash);
- `:126` `mlist.write_bytes(base.encode_mlist(magic, path, entries))` writes the list,
  `:128` `assert base.encode_mlist(*loaded) == mlist.read_bytes()` round-trips it.

**config.json / new-dir-files mechanism** (`mods/ssbu_mod_new/src/pgwr/build.py`):
`:1278` `def build_config_json():`, `:1306` `def add(slot, path):` (group-scoped append
plus "exists in the base game, so it is not a new file" check), `:1365`
`declared.setdefault(f'fighter/elight/{slot}', []).append(f'fighter/elight/motion/body/{slot}/{clip}')`
(new body clips), `:1377`
`f'fighter/elight/motion/{article}/{slot}/motion_list.bin')` (new article lists),
`:1388` `require(new_files == sorted(f for fs in declared.values() for f in fs),` - every
new file declared and nothing else, `:1394` `'new-dir-files': declared,`. Key semantics:
`mods/ssbu_mod_new/handbook/10_arcropolis_config_json.md:5` "`.prc`, `.nuanmb`, `motion_list.bin` are eligible added files. (C, ARCropolis `fs.rs`)"; `:6` "Fighter files
load **per costume group** (`fighter/<f>/c0N`); add article files to the existing group via
`new-dir-files`" (their A); `:18` "`new-dir-files` is group-scoped" + `:19` "(2026-10-01, B).".

**Exact file list one added motion needs** (body motion on an existing fighter, from the
lines above):

1. the new clip `fighter/<f>/motion/body/<slot>/<clip>.nuanmb` (new file -> declared per
   costume group via build.py:1365);
2. the fighter's `motion_list.bin` with one added/rewritten entry (existing file -> replaced,
   therefore NOT declared; entry carries kind hash, `game_<owned>` script hash, clip hash,
   and expression/sound/effect script hashes in the tail per build_hero_neutral_b_assets.py:69);
3. the ACMD scripts the entry names (`game_<owned>` etc.) registered - the Q2 mechanism;
4. no `.prc` is required by the mechanism (eligible, not mandatory); for an *article*
   motion the article's `motion_list.bin` is itself new and declared (build.py:1377).

For this mod: tool+config behaviour is read (B/C), the console claim is theirs (A), and
nothing here has been done for `miigunner` - **D**.

## Q5. Mii specifics in ssbu_mod_new / framework source

**Not found.** Searches (all reproducible by the checker):

- Pinned framework, cargo checkout `be3ef30` (repo `hdr-development/smashline`, commit
  be3ef308): `grep -ri "miigunner\|miifighter\|miiswordsman" --include=*.rs` -> **0 hits**;
  case-sensitive lowercase -> 0; case-insensitive across the whole checkout -> **1 hit**,
  `crates/actions/src/attack.rs:197` `MiiGunnerBlaster = 0x33,` (an article-kind enum value,
  not treatment of Mii fighters). The same single hit exists in both vendored copies under
  `mods/ssbu_mod_new/src/mgw_standalone/` (5 case-insensitive hits total there, the other 3
  being `vendor/ssbu_clone_engine/src/fighter_param_thrown.rs:264`
  `held_only_bridge!(miifighter_suplex_offset_bridge, OFF_MIIFIGHTER_SUPLEX_OFFSET, "miifighter_suplex_offset");`
  - a per-fighter param bridge for one Mii Fighter offset among many, not agent/costume/
  variant special-casing - and its declaration lines `:18` / `:316`).
- ssbu_mod_new plugin code (`src/pgwr/plugin/src`, case-insensitive): **9 hits in 4 files**,
  all generic tables or comments:
  - `src/pgwr/plugin/src/status/dk_cargo/data.rs:1364` - `VICTIM_AGENTS` list containing
    `"miifighter", "miigunner", "miiswordsman"` (one row of the generic victim table);
  - `src/pgwr/plugin/src/status/monkey_flip_capture_data.rs:77` `72 => Some([0.0f32, -1.0f32, 0.0f32]), // MIIFIGHTER`,
    `:78` `73 => Some([0.0f32, -1.0f32, 0.0f32]), // MIISWORDSMAN`, `:79`
    `74 => Some([0.0f32, -1.0f32, 0.0f32]), // MIIGUNNER` - generic kind-indexed capture
    offsets, Miis just rows;
  - `src/pgwr/plugin/src/mythra/hero_spin_params.rs:11`
    "`miiswordsman`'s own parameter block and cannot be installed on `elight`." - a comment
    saying a donor param block is *not* usable, i.e. still no Mii install;
  - `src/pgwr/plugin/src/acmd/littlemac_attack_s4.rs:27`
    "chrom diddy eflame elight gamewatch miiswordsman younglink" - a list of fighters that
    *lack* angled f-smash; a comment, not handling.
- Costume slots: framework costume gating is generic over any agent hash
  (`be3ef30` `src/create_agent.rs:253`
  `let costume = crate::utils::get_agent_costume(agent.battle_object as *const BattleObject).unwrap_or(0);`
  and `:265` `if has_costume && !c.contains(&(costume as usize)) {`); no Mii-specific
  costume logic anywhere.
- Custom special variants (variant bytes): `grep -ri "variant" src/pgwr/plugin/src --include=*.rs`
  -> 6 hits, none about Mii custom specials (angled f-smash variants and hero side-B air
  variants only). **Not found.** (This mod's own variant research lives under its P3
  evidence dir; ssbu_mod_new does not implement variant-byte handling.)

Consequence for the designer: nothing in the reference mod or the framework prevents
registering `"miigunner"` scripts, and nothing in them has ever done it - every Mii-specific
step is this mod's own work and stays D until tested.

## Q6. Vanilla script lookup for `game_attacks3` (no framework)

Input: `gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miigunner.nro`,
sha256 `64ec160d90eb97680266710155481c8baab1688ad98e890942be525c2007330c`, 1,662,976 bytes.
NRO0 header at file offset 0x10; segments: text fileoff 0x0 size 0x133000, ro fileoff
0x133000 size 0x5f000, data fileoff 0x192000 size 0x4000 (file offset == load address for
text). MOD0 at 0x133070. 564 dynamic symbols, only **11 defined** (shn != 0) - the
`create_agent_*` dispatchers; the ACMD script functions themselves are NOT in the symbol
table. The game dispatcher for this mod's move:
`_ZN7lua2cpp43create_agent_fighter_animcmd_game_miigunnerEN3phx6Hash40EPN3app12BattleObjectEPNS2_26BattleObjectModuleAccessorEP9lua_State`
at **0x47850, size 0x1b44** (status sibling at 0x480 size 0x42c). Their handbook notes the
export convention: `mods/ssbu_mod_new/handbook/07_articles.md:6` "Article agents are
registered from `main`, not from `lua2cpp_*.nro` (there is no `create_agent_article_*`);
NRO exports are spelled `create_agent_fighter_*`. `Elf64_Sym` = 0x18 bytes. (B)".

How it picks the function (all words below are the literal bytes in the file, capstone
`bytes.hex()`, re-read by the checker):

1. **Switch over arg0.** Head: `0x47850 f657bda9 stp x22, x21, [sp, #-0x30]!`; `0x47868
   089c4092 and x8, x0, #0xffffffffff` masks arg0 (a Hash40, per the mangled signature) to
   40 bits; `0x47880 1f0109eb cmp x8, x9` / `0x47884 0c040054 b.gt #0x47904` start a
   19-key binary-search tree (keys rebuilt with movz/movk, each consumed by a `cmp x8, ...`;
   count and values re-derived by `scratch/.../decode_keys2.py`). Exactly one key decodes:
   at `0x479b8 c9298fd2 mov x9, #0x794e` / `0x479bc a92bb0f2 movk x9, #0x815d, lsl #16` /
   `0x479c0 2901c0f2 movk x9, #9, lsl #32` = hash40 `0x09815d794e` = hash40("miigunner")
   (length byte 9 = len "miigunner"; crc32 verified), then `0x479c4 1f0109eb cmp x8, x9`,
   `0x479c8 e0150054 b.eq #0x47c84` -> the big leaf. The other 18 keys have length bytes
   0x0f-0x1b (15-27 chars) and do not decode against any known fighter/script name list -
   **open question** (see summary); they are other possible arg0 values of this same
   dispatcher, not other registrations.
2. **The leaf builds the per-agent table.** At `0x47c84 00198052 mov w0, #0xc8` /
   `0x47c88 eaa10394 bl #0x130430` -> `_Znwm` (operator new, GOT 0x193bf0) allocates a
   0xc8-byte object; `0x47c90`-`0x47c98` copy x22/x21/x20 (the dispatcher's x1/x2/x3 =
   BattleObject*, BattleObjectModuleAccessor*, lua_State* per the mangled ctor) into
   x1/x2/x3; `0x47c9c 25a50394 bl #0x131130` ->
   `_ZN7lua2cpp27L2CFighterAnimcmdGameCommonC2EPN3app12BattleObjectEPNS1_26BattleObjectModuleAccessorEP9lua_State`
   (GOT 0x194270); `0x47ca8 680200f9 str x8, [x19]` stores the vtable pointer (cell
   0x192a20 in .data). x19 = the fresh agent object.
3. **Registration.** Then a run of blocks, each:

   ```
   0x47e34 e24e8ad2 mov  x2, #0x5277
   0x47e38 4206a5f2 movk x2, #0x2832, lsl #16
   0x47e3c a10300b0 adrp x1, #0xbc000
   0x47e40 21001491 add  x1, x1, #0x500
   0x47e44 a201c0f2 movk x2, #0xd, lsl #32
   0x47e48 e00313aa mov  x0, x19
   0x47e4c b5a40394 bl   #0x131120
   ```

   x2 = hash40 `0x0d28325277` = hash40("game_attacks3") (length 0xd = 13); x1 =
   **0xbc500**, the address of a real code body in this NRO's .text (prologue
   `0xbc500 ff4301d1 sub sp, sp, #0x50`, `0xbc514 f40300aa mov x20, x0`, ... - the script
   itself); x0 = the fresh agent. The callee `#0x131120` is a veneer -> GOT 0x194268 =
   `_ZN3lib8L2CAgent20sv_set_function_hashEPvN3phx6Hash40E` - i.e. member fn
   `sv_set_function_hash(void* fn, Hash40 hash)` with `this` = the new object in x0,
   function pointer in x1, hash in x2. (Same three-argument shape the framework calls:
   be3ef30 `src/create_agent.rs:536` `agent.sv_set_function_hash(` with an unreachable
   stub at `:537` and the replaced script's hash at `:538`.)
4. **Counts / other scripts.** 207 `bl #0x131120` calls in the whole dispatcher (first
   0x47994, last 0x492f4), 196 inside the miigunner leaf 0x47c84..0x492f8. Neighbouring
   registrations: `game_attack11` at 0x47dc4 (hash 0x0d04731edc), `game_attackhi3` at
   0x47e50, `game_attacklw3` at 0x47e6c; the same pattern appears for the other categories
   in their own dispatchers (`sound_attacks3` in `create_agent_fighter_animcmd_sound`
   0x49760, `effect_attacks3` in `..._effect` 0x4b830, `expression_attacks3` in
   `..._expression` 0x495d0). Epilogue `0x492f8 e00313aa mov x0, x19` returns the object.
5. **Where the table lives.** Inside the freshly allocated agent object (x0/x19), one entry
   per script, filled at creation - not a static global. The framework's read of it
   corroborates this: be3ef30 `src/create_agent.rs:521`-`:525` copies
   `agent.function_map` into `original_scripts` after calling the original creator, then
   overlays its own entries (`:536`-`:539`) and stores the replacement handles for
   call-time resolution (`:540`-`:543`). So dispatch = hash lookup in that per-object map;
   the game's own call site that performs the lookup is in `main` and was not pinned here
   (open question, not needed to judge the alternatives below).
6. **Main side (what a direct hook would face).** The framework's hook table (C):
   be3ef30 `src/create_agent.rs:1198`-`:1206`
   `create_agent_hook! { 0x64c310 => (Game, fighter); 0x64c930 => (Effect, fighter); ... }`.
   Measured at `gamedata/ssbu-13.0.4/main.bin:0x64c310` (B): `080c40b9 ldr w8, [x0, #0xc]`,
   `1f750171 cmp w8, #0x5d`, jump table load, `00011fd6 br x8` at 0x64c338 - a computed
   jump keyed by a word at `[x0,#0xc]` over at most 0x5e+1 values (a kind-like index; the
   field is not proven to be the kind here - D). How main reaches the NRO's exported
   dispatcher was not established (open question).

**For a designer judging a direct hook:** the table is per-instance and filled during
creation, so a replacement must happen either (a) before/inside creation (hook the
dispatcher - main-side at 0x64c310-family or the NRO export itself), or (b) after creation
by calling `sv_set_function_hash(fn, hash)` on the instance - which is exactly what
smashline does; without the framework both routes need this mod's own hook code and its own
`nn::ro::LookupSymbol`-free call plumbing. Facts only; comparison in Q8.

## Q7. Compile-only experiment (spike crate)

Crate: `scratch/2026-10-07_P12-SCRIPT-ROUTE/spike/` (separate from `plugin/`;
`build-plugin.sh` untouched; not staged under `builds/<version>/`).

- `Cargo.toml:15` `[dependencies]` with the same four bare git URLs and no `rev`, `:25`
  `skyline = { git = "https://github.com/ultimate-research/skyline-rs" }` ... `:28`
  `smashline = { git = "https://github.com/hdr-development/smashline" }`; revisions come
  from `Cargo.lock` copied from `mods/ssbu_mod_new/src/pgwr/plugin/Cargo.lock`.
- `src/lib.rs:18` `pub unsafe extern "C" fn game_attacks3(agent: &mut L2CAgentBase) {`
  whose body reads `:21` `*FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID,` via
  `agent.module_accessor` and does nothing else; registered at `:26`
  `Agent::new("miigunner")` / `:27`
  `.game_acmd("game_attacks3", game_attacks3, Default)`.
- Command (form matches `kb/reference/cargo-skyline.md:61`
  "`cargo skyline build --release -- --offline`"):

  ```
  cd scratch/2026-10-07_P12-SCRIPT-ROUTE/spike
  CARGO_TARGET_DIR=../../../builds/.cache/p12-script-route \
      cargo skyline build --release -- --offline > build_offline.log 2>&1
  ```

  Runs: (1) full build exit **0**, 1m09s, warnings = 0 (observed 2026-10-07; that log was
  later replaced by run 3); (2) re-run on the same target dir exit 0 (0.52s, no-op, same
  bytes); (3) clean build from an empty target dir
  (`CARGO_TARGET_DIR=../../../builds/.cache/p12-script-route/rebuild`) exit **0**, 57.25s,
  warnings = 0 (`grep -c ^warning` = 0) - log kept as `build_offline.log`. All four crates
  resolved from the local cargo cache at the pinned commits ("Compiling smashline v0.1.0
  (https://github.com/hdr-development/smashline#be3ef308)" in the log); nothing was fetched,
  `--offline` never failed for a missing crate.
- NRO: `builds/.cache/p12-script-route/aarch64-skyline-switch/release/libp12_spike.nro`,
  32768 bytes, sha256
  `728c1ce7bec8b30b8943441e5f109ac71401b4b51e48931c3252ae782cb586a1` - byte-identical in
  the clean rebuild (`builds/.cache/p12-script-route/rebuild/.../libp12_spike.nro`).
- Undefined dynamic symbols (18 named; shn == 0): `WorkModule__get_int_impl` (the smash
  binding `_ZN3app8lua_bind24WorkModule__get_int_implEPNS_26BattleObjectModuleAccessorEi`),
  `_ZN2nn2ro12LookupSymbolEPmPKc`, `__nro_header_start`, `free`, `malloc`, `memcpy`,
  `posix_memalign`, `pthread_cond_destroy`, `pthread_cond_init`, `pthread_cond_signal`,
  `pthread_cond_wait`, `pthread_getspecific`, `pthread_key_create`, `pthread_key_delete`,
  `pthread_mutex_destroy`, `pthread_mutex_lock`, `pthread_mutex_unlock`,
  `pthread_setspecific`. These the NRO loader resolves from the process - NOT from the
  framework.
- What the *framework* must provide at load: the four names appear as strings in the NRO -
  `smashline_install_acmd_script_costume` @17253, `smashline_install_status_script_costume`
  @17366, `smashline_install_state_callback_costume` @17406,
  `smashline_install_line_callback_costume` @17985 - resolved at runtime by
  `nn::ro::LookupSymbol` per be3ef30 `crates/smashline/src/lib.rs:312`
  `macro_rules! decl_imports {` -> `:319` `skyline::nn::ro::LookupSymbol(...)` -> `:323`
  `panic!("Could not find '{}', please install the smashline plugin!", ...)`. The import
  declarations are at `lib.rs:347` `fn smashline_install_acmd_script_costume(`, `:364`
  `fn smashline_install_status_script_costume(`, `:379`
  `fn smashline_install_line_callback_costume(`, `:403`
  `fn smashline_install_state_callback_costume(`. All four names exist in both vendored
  plugin sources (smashline_1304 and vendor/.../smashline-1.6.8, `decl_imports` at lib.rs:312
  in each), so a build of this spike needs, at load, a `libsmashline_plugin.nro` exporting
  those names - the card's `5f4091ee…` binary is from that source family, but the export
  match was not checked against the binary (D). Strings `game_attacks3` @16453 and
  `miigunner` @16444 are retained in the NRO.
- The spike was never loaded by anything: a successful build proves only that it compiles
  against the pinned crates (**B** for compile, **D** for any runtime behaviour).

## Q8. Mechanism x evidence table

| mechanism | console-proven in ssbu_mod_new (their tier) | only read / measured here (tier) | unknown for Miis (this mod) |
|---|---|---|---|
| Framework ACMD replacement with a saved-ID branch in the script body (`Agent::new("miigunner").game_acmd(...)` + branch) | costume-gated ACMD replacement of game/effect/sound/expression scripts runs on hardware for eflame/elight (GATE log `evidence/2026-09-30_pgwr_0.18.0/pgwr_log_from_boot.txt:8`; Monkey Flip "exercised on hardware" `CURRENT_INSTALL.md:772`-`:774`) - **A for their fighters**; costume gate "(A gate; C mechanism)" `handbook/11_smashline_skyline.md:6` | builder API C (be3ef30 builder.rs:103/:149/:255); spike compiles (Q7, B); call-time original via `original_acmd` (mgw_swap/src/hero_spin.rs:521, C) | whether smashline's install path accepts `"miigunner"` and fires on a Gunner at all - never attempted by ssbu_mod_new (Q5 not found) = **D**; saved-ID branch inside a script = **D** |
| Framework status wrapper (`agent.status(Pre, ...)` + `original_status`) | hero neutral-B owned status machine ran on console (CLIP log `:18`/`:57` under status 0x1f5) - **A for elight**; gaogaen wrapper shipped but "All gameplay unverified" (`CURRENT_INSTALL.md:246`) | status API C (builder.rs:192, lib.rs:445); wrapper call sites read at gaogaen_throw_b.rs:88, dk_cargo/mod.rs:125, hero_spin.rs:252, monkey_flip_status.rs:136 | no status has ever been registered for `miigunner` by anyone in this workspace = **D**; interaction of a wrapper with this mod's own direct hooks = **D** |
| Direct hook of the script lookup (hook the creator / call `sv_set_function_hash` on the instance, no framework) | not used for scripts by ssbu_mod_new; their skyline patch/hook machinery is A for other things (`handbook/11_smashline_skyline.md:7` "(A, p9->p10)") | Q6 decode, this mod (B): table is per-agent, filled at creation (0x47c84 leaf, 196 calls, `game_attacks3` @0x47e34 -> body 0xbc500); framework's own hook+overlay C (create_agent.rs:1199, :521-:543); main.bin 0x64c310 jump table (B) | every runtime aspect - load order, whether main's jump table leads to this NRO export for kind 74, collisions with a loaded libsmashline_plugin = **D**; 18 of 19 dispatcher keys undecoded (open) |
| Motion change at status start (new motion_list entry + declared clip, played from the replacement status) | declared new motion names load and play: "Declared new names do load (A, 2026-09-30)" `handbook/04_motion_lists_animation.md:14` + log `:18`/`:57`; per-group loading (A) `handbook/10_arcropolis_config_json.md:6` | tool/config mechanics B: build_hero_neutral_b_assets.py:66/:126/:128, build.py:1278/:1365/:1388/:1394; key semantics C `handbook/10_arcropolis_config_json.md:5`, group scoping B `:18`-`:19` | no motion_list/config build for a `miigunner` slot exists; whether Mii custom-skeleton slots behave like c0N groups = **D** |

No recommendation, per the task.

## Final summary

- **Task ID:** P12-SCRIPT-ROUTE
- **Status:** DONE - all eight questions answered from offline sources plus one compile-only
  spike; nothing run in the game. (Two sub-facts inside Q6 are explicitly open, not
  blocking: the 18 undecoded switch keys, and the main -> NRO call relationship.)

**Changed files (exclusive scope only):**

- `mods/mii_customizer/research/P12-SCRIPT-ROUTE.md` (this report, new)
- `mods/mii_customizer/evidence/P12-SCRIPT-ROUTE/check_p12_script_route.py` (new)
- `mods/mii_customizer/scratch/2026-10-07_P12-SCRIPT-ROUTE/` (new: `q6_final_disasm.py`,
  `decode_keys2.py`, pre-existing `classify_keys.py`/`find_script_hash.py`/
  `disasm_register.py`/`trace_game_attacks3.py`/`miigunner_syms.txt`, and `spike/`
  {`Cargo.toml`, `Cargo.lock`, `src/lib.rs`, `build_offline.log`})
- `mods/mii_customizer/builds/.cache/p12-script-route/` (build output: `libp12_spike.nro`
  in two target dirs + intermediates; not staged under `builds/<version>/`)

**Checks run:**

1. `python evidence/P12-SCRIPT-ROUTE/check_p12_script_route.py` - re-reads every quoted
   file:line in this report, both sha256 hashes, every cited instruction word and the
   symbol/GOT/registration facts of Q6-Q7; exit 1 on any mismatch. Output pasted in the
   task reply after the last edit to this report.
2. Same script with `--neg` - four negative controls (wrong instruction word, wrong
   file:line quote, wrong sha256, wrong symbol size), each must be detected.
3. `cargo skyline build --release -- --offline` (spike, Q7) - exit 0, warnings 0, NRO
   sha256 re-verified after the final report edit.

**Open questions:**

1. The 18 undecoded switch keys of `create_agent_fighter_animcmd_game_miigunner` (hash40
   length bytes 15-27; five pairs differ by exactly 1) - what arg0 values are they?
2. How `main` reaches the NRO export: `main.bin` 0x64c310 dispatches on `[x0,#0xc] <= 0x5d`
   to targets inside main; the bridge to `create_agent_fighter_*` in the NRO (handbook/07:6)
   is not pinned.
3. Does the card's `libsmashline_plugin.nro` (`5f4091ee…`) export the four
   `smashline_install_*` names the spike needs at load? (Source family says yes - Q7 - the
   binary was not checked; loading was not tested = D.)
4. Everything runtime for `"miigunner"`: registration firing, per-instance saved-ID branch,
   motion play for a Mii slot - D until the user tests on hardware.
