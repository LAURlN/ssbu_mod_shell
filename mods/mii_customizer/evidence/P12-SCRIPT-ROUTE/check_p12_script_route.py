#!/usr/bin/env python3
"""evidence check for P12-SCRIPT-ROUTE.

Re-reads, from disk:

  * every file:line quoted in research/P12-SCRIPT-ROUTE.md (and asserts each
    quoted substring actually appears in the report - quotes and report cannot
    drift apart);
  * extra file:line facts the report cites by line number only;
  * every hash the report states (input NRO, spike NRO x2, git commit of the
    pinned framework checkout, hash40 constants);
  * every instruction word cited in Q6 of the report, plus the structural facts
    they support (segments, symbol table, registration counts, switch keys,
    veneer -> GOT names, adrp/add targets);
  * the Q7 spike facts (NRO size/sha, undefined symbols, runtime import
    strings, build log);
  * the Q5 not-found claims (grep counts over the pinned framework checkout,
    the vendored copies and ssbu_mod_new's own code).

Usage:
    python evidence/P12-SCRIPT-ROUTE/check_p12_script_route.py          # positive
    python evidence/P12-SCRIPT-ROUTE/check_p12_script_route.py --neg    # + controls

Exit 0 = everything re-read identically; exit 1 = any mismatch (or a negative
control that failed to trip).

Negative controls (behind --neg): four deliberately wrong expectations (wrong
instruction word, wrong file:line quote, wrong sha256, wrong symbol size).
Each MUST be detected as a mismatch; if one passes, the checker exits 1.
"""
from __future__ import annotations

import hashlib
import struct
import subprocess
import sys
import zlib
from pathlib import Path

HERE = Path(__file__).resolve()
# .../mods/mii_customizer/evidence/P12-SCRIPT-ROUTE/this.py
MOD = HERE.parents[2]           # mods/mii_customizer
WS = HERE.parents[4]            # workspace root
REPORT = MOD / 'research/P12-SCRIPT-ROUTE.md'
CO = Path.home() / '.cargo/git/checkouts/smashline-0ccc30393002c4aa/be3ef30'
CO_COMMIT = 'be3ef308ed8e479922da192a391e0684184af2af'

IN_NRO = WS / 'gamedata/mii_customizer/P11-MOVE-PLAN/prebuilt;/nro/release/lua2cpp_miigunner.nro'
SPIKE_NRO = MOD / 'builds/.cache/p12-script-route/aarch64-skyline-switch/release/libp12_spike.nro'
SPIKE_NRO_CLEAN = MOD / 'builds/.cache/p12-script-route/rebuild/aarch64-skyline-switch/release/libp12_spike.nro'
SPIKE_LOG = MOD / 'scratch/2026-10-07_P12-SCRIPT-ROUTE/spike/build_offline.log'
SPIKE_LOCK = MOD / 'scratch/2026-10-07_P12-SCRIPT-ROUTE/spike/Cargo.lock'
REF_LOCK = MOD if False else WS / 'mods/ssbu_mod_new/src/pgwr/plugin/Cargo.lock'
MAIN_BIN = WS / 'gamedata/ssbu-13.0.4/main.bin'

IN_NRO_SHA = '64ec160d90eb97680266710155481c8baab1688ad98e890942be525c2007330c'
SPIKE_SHA = '728c1ce7bec8b30b8943441e5f109ac71401b4b51e48931c3252ae782cb586a1'

sys.path.insert(0, str(WS / 'mods/ssbu_mod_new/tools/nro_decomp'))
import nro_flatten as nf  # noqa: E402


def hash40(name: str) -> int:
    return ((len(name) & 0xFFFFFFFF) << 32) | (zlib.crc32(name.encode()) & 0xFFFFFFFF)


def sha256_of(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def resolve(p: str) -> Path:
    if p.startswith('CO:'):
        return CO / p[3:]
    if p.startswith('MOD:'):
        return MOD / p[4:]
    return WS / p


# ---------------------------------------------------------------------------
# quotes: (path, line, substring); every substring must also occur in REPORT
# ---------------------------------------------------------------------------
Q = [
    # ---- Q1 ----
    ('mods/ssbu_mod_new/handbook/11_smashline_skyline.md', 5,
     'Do **not** replace the global `libsmashline_plugin.nro` (card: `5f4091ee…`, the 13.0.4'),
    ('mods/ssbu_mod_new/handbook/11_smashline_skyline.md', 5,
     '`libarcropolis.nro`, `libarc_network.nro`, `libnro_hook.nro`. (A)'),
    ('mods/ssbu_mod_new/CURRENT_INSTALL.md', 254, 'Framework installation OFF; all four'),
    ('mods/ssbu_mod_new/CURRENT_INSTALL.md', 255, 'protected plugins byte-unchanged (smashline still `5f4091ee…`).'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/Cargo.toml', 46, 'Measured on 2026-09-17 that'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/Cargo.toml', 47, 'FighterEntry'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/Cargo.toml', 54, 'Do not run `cargo update`'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/Cargo.toml', 55, '6b52d321275639f26c2371d8142550ba0013a5e4'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/Cargo.toml', 56, '315e4e8bebb460ebb9f02f30f07b0f13883ba3d6'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/Cargo.toml', 57, 'fdc6144a0a429ce37b304733531edcb76c8f2578'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/Cargo.toml', 58, 'be3ef308ed8e479922da192a391e0684184af2af'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/Cargo.toml', 62, 'git = "https://github.com/hdr-development/smashline"'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/Cargo.lock', 456, 'name = "smashline"'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/Cargo.lock', 458,
     'source = "git+https://github.com/hdr-development/smashline#be3ef308ed8e479922da192a391e0684184af2af"'),
    ('mods/ssbu_mod_new/src/mgw_standalone/smashline_1304/Cargo.toml', 5, 'version = "1.6.8"'),
    ('mods/ssbu_mod_new/src/mgw_standalone/smashline_1304/Cargo.toml', 7,
     'An object script replacement engine for Super Smash Bros. Ultimate'),
    ('mods/ssbu_mod_new/src/mgw_standalone/smashline_1304/Cargo.toml', 9, 'https://github.com/WuBoytH/smashline-2'),
    # ---- Q2 ----
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/chrom_jab.rs', 190,
     'pub unsafe extern "C" fn game_attack11(agent: &mut L2CAgentBase) {'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/chrom_jab.rs', 197, 'agent.module_accessor,'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/chrom_jab.rs', 353, 'pub fn install() {'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/chrom_jab.rs', 354, 'let mut agent = Agent::new("eflame");'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/chrom_jab.rs', 355,
     'agent.set_costume(crate::TARGET_COSTUMES.to_vec());'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/chrom_jab.rs', 359,
     'agent.game_acmd("game_attack11", game_attack11, Priority::High);'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/chrom_jab.rs', 362,
     'agent.effect_acmd("effect_attack11", effect_attack11, Priority::High);'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/chrom_jab.rs', 365,
     'agent.sound_acmd("sound_attack11", sound_attack11, Priority::High);'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/chrom_jab.rs', 368,
     'agent.expression_acmd("expression_attack11", expression_attack11, Priority::High);'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/chrom_jab.rs', 372, 'agent.install();'),
    ('CO:crates/smashline/src/builder.rs', 3,
     'pub type AcmdFunction = unsafe extern "C" fn(&mut crate::L2CAgentBase);'),
    ('CO:crates/smashline/src/builder.rs', 103, 'pub fn new(agent: impl AsHash40) -> Self {'),
    ('CO:crates/smashline/src/builder.rs', 114,
     'pub fn set_costume(&mut self, costumes: Vec<usize>) -> &mut Self {'),
    ('CO:crates/smashline/src/builder.rs', 149,
     'pub fn game_acmd(&mut self, name: impl AsHash40, function: AcmdFunction, priority: Priority) -> &mut Self {'),
    ('CO:crates/smashline/src/builder.rs', 192, 'pub fn status<M: StatusLineMarker, T>('),
    ('CO:crates/smashline/src/builder.rs', 207, 'pub fn on_line<M: StatusLineMarker, T>('),
    ('CO:crates/smashline/src/builder.rs', 255, 'pub fn install(&self) {'),
    ('CO:crates/smashline/src/builder.rs', 257, 'crate::api::install_acmd_script_costume('),
    ('CO:crates/smashline/src/lib.rs', 34, 'pub enum Priority {'),
    ('CO:crates/smashline/src/lib.rs', 440,
     'pub fn original_acmd(agent: &mut L2CAgentBase, name: Hash40) -> AcmdFunction {'),
    ('CO:crates/smashline/src/lib.rs', 445, 'pub fn original_status<L: StatusLineMarker, T>('),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_neutral_b/fighter.rs', 349,
     'let mut agent = Agent::new("elight");'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_neutral_b/fighter.rs', 351,
     'agent.status(Pre, *FIGHTER_STATUS_KIND_SPECIAL_N, redirect);'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_neutral_b/fighter.rs', 356,
     'agent.status(Exec, HOLD, hold_exec); agent.on_line(Main, lifecycle); agent.install();'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/registration.rs', 45,
     'let mut agent = Agent::new("elight");'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/registration.rs', 47,
     'agent.status(Pre, *FIGHTER_STATUS_KIND_SPECIAL_S, callbacks.entry.pre);'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_side_b/registration.rs', 66, 'agent.install();'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/status/gaogaen_throw_b.rs', 72,
     '#[skyline::hook(replace = smash::lua2cpp::L2CFighterCommon_sub_is_not_throw_status_kind)]'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/status/gaogaen_throw_b.rs', 78, 'original!()(fighter, kind)'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/status/gaogaen_throw_b.rs', 88,
     'original_status(Pre, fighter, *FIGHTER_STATUS_KIND_THROW)(fighter)'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/status/dk_cargo/mod.rs', 125,
     'original_status(Pre,fighter,stock)(fighter)'),
    ('mods/ssbu_mod_new/src/mgw_swap/src/hero_spin.rs', 252,
     'return original_status(Pre, fighter, *FIGHTER_STATUS_KIND_SPECIAL_HI)(fighter);'),
    ('mods/ssbu_mod_new/src/mgw_swap/src/monkey_flip_status.rs', 136,
     'return original_status(Pre, fighter, *FIGHTER_STATUS_KIND_SPECIAL_S)(fighter);'),
    ('mods/ssbu_mod_new/src/mgw_swap/src/hero_spin.rs', 516,
     'branch. `original_acmd` is the script pointer smashline captured'),
    ('mods/ssbu_mod_new/src/mgw_swap/src/hero_spin.rs', 521,
     'original_acmd(agent, Hash40::new(name))(agent);'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/mod.rs', 196,
     'unsafe extern "C" fn gate_trace(agent: &mut L2CAgent) {'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/mod.rs', 245, '#[cfg(feature = "logging")]'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/mod.rs', 248, '.on_line(Main, gate_trace)'),
    ('mods/ssbu_mod_new/CURRENT_INSTALL.md', 246, 'All gameplay unverified'),
    ('mods/ssbu_mod_new/CURRENT_INSTALL.md', 253, '`logging` **off**'),
    ('mods/ssbu_mod_new/CURRENT_INSTALL.md', 772,
     '(T-0056): exercised on hardware'),
    ('mods/ssbu_mod_new/CURRENT_INSTALL.md', 774,
     'by the user. The T-0053 section below is its'),
    ('mods/ssbu_mod_new/handbook/11_smashline_skyline.md', 6,
     'Costume gating at install time'),
    ('mods/ssbu_mod_new/handbook/11_smashline_skyline.md', 6, 'A gate; C mechanism'),
    ('mods/ssbu_mod_new/handbook/11_smashline_skyline.md', 7, '(A, p9->p10)'),
    ('mods/ssbu_mod_new/handbook/11_smashline_skyline.md', 11, 'Smashline Main fires twice in a frame'),
    ('mods/ssbu_mod_new/evidence/2026-09-30_pgwr_0.18.0/pgwr_log_from_boot.txt', 8,
     '[PGWR] MYTHRA GATE ACTIVE: entry 0 is Mythra'),
    # ---- Q3 ----
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/mod.rs', 140,
     'let id = WorkModule::get_int(agent.module_accessor, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID) as usize;'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/article.rs', 250,
     'so the battle object id is not guaranteed to be below 8; the entry id is'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/article.rs', 252,
     'unsafe fn entry(boma: *mut BattleObjectModuleAccessor) -> usize {'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/article.rs', 253,
     'WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID) as usize'),
    ('MOD:plugin/src/lib.rs', 385, 'unsafe fn resolve(parent: u64) -> Ident {'),
    ('MOD:plugin/src/lib.rs', 386, 'let accessor = parent as *mut BattleObjectModuleAccessor;'),
    ('MOD:plugin/src/lib.rs', 408,
     'facts.entry_accessor = WorkModule::get_int(accessor, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID);'),
    ('MOD:plugin/src/lib.rs', 411, 'logic::identify(&facts)'),
    ('MOD:plugin/src/lib.rs', 254, 'unsafe fn read_player(p: u32) -> Option<(u32, [u8; 4])> {'),
    ('MOD:plugin/src/lib.rs', 534, 'if let Some((id, _)) = read_player(ident.player as u32) {'),
    ('MOD:plugin/src/lib.rs', 538,
     'logic::decide(&ident, &logic::ACCEPTED_KINDS, slot_id, &STORE, &PRESETS, field)'),
    ('MOD:plugin/src/logic.rs', 10,
     "`FIGHTER_KIND_MIIGUNNER` on 13.0.4: the binding's constant, confirmed on the console"),
    ('MOD:plugin/src/logic.rs', 11, '(`evidence/2026-10-05_gate2/RESULT.md`, every Gunner line `kind=74`).'),
    ('MOD:plugin/src/logic.rs', 12, 'pub const KIND_MIIGUNNER: i32 = 0x4a;'),
    ('MOD:plugin/src/logic.rs', 14, 'pub const ACCEPTED_KINDS: [i32; 1] = [KIND_MIIGUNNER];'),
    ('MOD:plugin/src/logic.rs', 16, 'console-confirmed for'),
    ('MOD:plugin/src/logic.rs', 18, 'pub const TABLE_BASE: usize = 0x530_7760;'),
    ('MOD:plugin/src/logic.rs', 211, 'pub fn identify(f: &Facts) -> Ident {'),
    ('MOD:plugin/src/logic.rs', 253,
     'pub fn decide(ident: &Ident, kinds: &[i32], slot_id: u32, store: &Store, presets: &Presets, field: usize) -> Decision {'),
    ('MOD:research/P7-PRESET-ENGINE.md', 113,
     '## 2. The hot path (B, from the disassembly of the staged NRO)'),
    # ---- Q4 ----
    ('mods/ssbu_mod_new/handbook/04_motion_lists_animation.md', 14,
     '**Declared new names do load (A, 2026-09-30):**'),
    ('mods/ssbu_mod_new/handbook/04_motion_lists_animation.md', 14,
     'listed under `new-dir-files` `fighter/elight/c0N`'),
    ('mods/ssbu_mod_new/evidence/2026-09-30_pgwr_0.18.0/pgwr_log_from_boot.txt', 18,
     '[PGWR-HERO-N] CLIP status=0x1f5 motion=0x1920438ca3 frame=1.0 end=7.0'),
    ('mods/ssbu_mod_new/evidence/2026-09-30_pgwr_0.18.0/pgwr_log_from_boot.txt', 57,
     '[PGWR-HERO-N] CLIP status=0x1f9 motion=0x14c7a6c6ff frame=1.0 end=73.0'),
    ('mods/ssbu_mod_new/tools/build_hero_neutral_b_assets.py', 66, 'def entry_bytes(entry, owned, clip):'),
    ('mods/ssbu_mod_new/tools/build_hero_neutral_b_assets.py', 69,
     "struct.pack_into('<QQ', raw, 0, base.hash40(owned), base.hash40('game_' + owned.replace('_', '')))"),
    ('mods/ssbu_mod_new/tools/build_hero_neutral_b_assets.py', 70,
     "struct.pack_into('<Q', raw, 24, base.hash40(clip))"),
    ('mods/ssbu_mod_new/tools/build_hero_neutral_b_assets.py', 126,
     'mlist.write_bytes(base.encode_mlist(magic, path, entries))'),
    ('mods/ssbu_mod_new/tools/build_hero_neutral_b_assets.py', 128,
     'assert base.encode_mlist(*loaded) == mlist.read_bytes()'),
    ('mods/ssbu_mod_new/src/pgwr/build.py', 1278, 'def build_config_json():'),
    ('mods/ssbu_mod_new/src/pgwr/build.py', 1306, 'def add(slot, path):'),
    ('mods/ssbu_mod_new/src/pgwr/build.py', 1365,
     "declared.setdefault(f'fighter/elight/{slot}', []).append(f'fighter/elight/motion/body/{slot}/{clip}')"),
    ('mods/ssbu_mod_new/src/pgwr/build.py', 1377,
     "f'fighter/elight/motion/{article}/{slot}/motion_list.bin')"),
    ('mods/ssbu_mod_new/src/pgwr/build.py', 1388,
     'require(new_files == sorted(f for fs in declared.values() for f in fs),'),
    ('mods/ssbu_mod_new/src/pgwr/build.py', 1394, "'new-dir-files': declared,"),
    ('mods/ssbu_mod_new/handbook/10_arcropolis_config_json.md', 5,
     'are eligible added files. (C, ARCropolis `fs.rs`)'),
    ('mods/ssbu_mod_new/handbook/10_arcropolis_config_json.md', 6,
     'per costume group** (`fighter/<f>/c0N`)',),
    ('mods/ssbu_mod_new/handbook/10_arcropolis_config_json.md', 18, '`new-dir-files` is group-scoped'),
    ('mods/ssbu_mod_new/handbook/10_arcropolis_config_json.md', 19, '(2026-10-01, B)'),
    # ---- Q5 ----
    ('CO:crates/actions/src/attack.rs', 197, 'MiiGunnerBlaster = 0x33,'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/status/dk_cargo/data.rs', 1364,
     '"miifighter", "miigunner", "miiswordsman"'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/status/monkey_flip_capture_data.rs', 77,
     '72 => Some([0.0f32, -1.0f32, 0.0f32]), // MIIFIGHTER'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/status/monkey_flip_capture_data.rs', 78,
     '73 => Some([0.0f32, -1.0f32, 0.0f32]), // MIISWORDSMAN'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/status/monkey_flip_capture_data.rs', 79,
     '74 => Some([0.0f32, -1.0f32, 0.0f32]), // MIIGUNNER'),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/mythra/hero_spin_params.rs', 11,
     "`miiswordsman`'s own parameter block and cannot be installed on `elight`."),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/acmd/littlemac_attack_s4.rs', 27,
     'chrom diddy eflame elight gamewatch miiswordsman younglink'),
    ('mods/ssbu_mod_new/src/mgw_standalone/vendor/ssbu_clone_engine/src/fighter_param_thrown.rs', 264,
     'held_only_bridge!(miifighter_suplex_offset_bridge, OFF_MIIFIGHTER_SUPLEX_OFFSET, "miifighter_suplex_offset");'),
    ('CO:src/create_agent.rs', 253,
     'let costume = crate::utils::get_agent_costume(agent.battle_object as *const BattleObject).unwrap_or(0);'),
    ('CO:src/create_agent.rs', 265, 'if has_costume && !c.contains(&(costume as usize)) {'),
    ('mods/ssbu_mod_new/handbook/07_articles.md', 6,
     'registered from `main`, not from `lua2cpp_*.nro`'),
    # ---- Q6 ----
    ('CO:src/create_agent.rs', 522, 'function_map'),
    ('CO:src/create_agent.rs', 536, 'agent.sv_set_function_hash('),
    ('CO:src/create_agent.rs', 1198, 'create_agent_hook! {'),
    ('CO:src/create_agent.rs', 1199, '0x64c310 => (Game, fighter);'),
    # ---- Q7 ----
    ('MOD:scratch/2026-10-07_P12-SCRIPT-ROUTE/spike/Cargo.toml', 15, '[dependencies]'),
    ('MOD:scratch/2026-10-07_P12-SCRIPT-ROUTE/spike/Cargo.toml', 25,
     'skyline = { git = "https://github.com/ultimate-research/skyline-rs" }'),
    ('MOD:scratch/2026-10-07_P12-SCRIPT-ROUTE/spike/Cargo.toml', 28,
     'smashline = { git = "https://github.com/hdr-development/smashline" }'),
    ('MOD:scratch/2026-10-07_P12-SCRIPT-ROUTE/spike/src/lib.rs', 18,
     'pub unsafe extern "C" fn game_attacks3(agent: &mut L2CAgentBase) {'),
    ('MOD:scratch/2026-10-07_P12-SCRIPT-ROUTE/spike/src/lib.rs', 21, '*FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID,'),
    ('MOD:scratch/2026-10-07_P12-SCRIPT-ROUTE/spike/src/lib.rs', 26, 'Agent::new("miigunner")'),
    ('MOD:scratch/2026-10-07_P12-SCRIPT-ROUTE/spike/src/lib.rs', 27,
     '.game_acmd("game_attacks3", game_attacks3, Default)'),
    ('kb/reference/cargo-skyline.md', 61, '`cargo skyline build --release -- --offline`'),
    ('CO:Cargo.toml', 5, 'version = "1.6.7"'),
    ('CO:crates/smashline/src/lib.rs', 312, 'macro_rules! decl_imports {'),
    ('CO:crates/smashline/src/lib.rs', 319, 'skyline::nn::ro::LookupSymbol'),
    ('CO:crates/smashline/src/lib.rs', 323, 'please install the smashline plugin!'),
    ('CO:crates/smashline/src/lib.rs', 347, 'fn smashline_install_acmd_script_costume('),
    ('CO:crates/smashline/src/lib.rs', 364, 'fn smashline_install_status_script_costume('),
    ('CO:crates/smashline/src/lib.rs', 379, 'fn smashline_install_line_callback_costume('),
    ('CO:crates/smashline/src/lib.rs', 403, 'fn smashline_install_state_callback_costume('),
]

# extra file:line facts the report cites by line number only (no report-sync)
EXTRA = [
    ('CO:crates/smashline/src/builder.rs', 159,
     'pub fn effect_acmd(&mut self, name: impl AsHash40, function: AcmdFunction, priority: Priority) -> &mut Self {'),
    ('CO:crates/smashline/src/builder.rs', 169,
     'pub fn sound_acmd(&mut self, name: impl AsHash40, function: AcmdFunction, priority: Priority) -> &mut Self {'),
    ('CO:crates/smashline/src/builder.rs', 180,
     'pub fn expression_acmd(&mut self, name: impl AsHash40, function: AcmdFunction, priority: Priority) -> &mut Self {'),
    ('CO:src/create_agent.rs', 521, 'let original_scripts: HashMap<Hash40, AcmdFunction> = agent'),
    ('CO:src/create_agent.rs', 537, 'unreachable_smashline_script'),
    ('CO:src/create_agent.rs', 538, 'script.script.read().replace.as_hash40(),'),
    ('CO:src/create_agent.rs', 540, 'user_scripts.insert('),
    ('mods/ssbu_mod_new/src/pgwr/plugin/src/article.rs', 249, 'The player slot (0-7)'),
    ('mods/ssbu_mod_new/src/mgw_standalone/smashline_1304/crates/smashline/src/lib.rs', 312,
     'macro_rules! decl_imports {'),
    ('mods/ssbu_mod_new/src/mgw_standalone/vendor/smashline-release/smashline-1.6.8/crates/smashline/src/lib.rs',
     312, 'macro_rules! decl_imports {'),
]

# Q6 instruction words (file bytes.hex(), capstone convention)
WORDS = {
    0x47850: 'f657bda9', 0x47868: '089c4092', 0x47880: '1f0109eb', 0x47884: '0c040054',
    0x479b8: 'c9298fd2', 0x479bc: 'a92bb0f2', 0x479c0: '2901c0f2', 0x479c4: '1f0109eb',
    0x479c8: 'e0150054', 0x47c84: '00198052', 0x47c88: 'eaa10394', 0x47c9c: '25a50394',
    0x47ca0: '480a00f0', 0x47ca4: '08812891', 0x47ca8: '680200f9',
    0x47e34: 'e24e8ad2', 0x47e38: '4206a5f2', 0x47e3c: 'a10300b0', 0x47e40: '21001491',
    0x47e44: 'a201c0f2', 0x47e48: 'e00313aa', 0x47e4c: 'b5a40394',
    0x47dc4: '82db83d2', 0x492f8: 'e00313aa', 0xbc500: 'ff4301d1', 0xbc514: 'f40300aa',
}
# note: 0x47e4c was corrected from a manual endianness slip to b5a40394 (bytes in file order)

# 19 switch keys of the dispatcher: (offset, value) re-derived from movz/movk + cmp
KEYS = [
    (0x47860, 0x160676ad85), (0x47888, 0x14b8a68375), (0x4789c, 0x15863044e1),
    (0x478b0, 0x14b8a68376), (0x478c4, 0x1512b89461), (0x47904, 0x173e726ce0),
    (0x47918, 0x1a0ccc13f9), (0x4792c, 0x173e726ce1), (0x47940, 0x19784a46e2),
    (0x479b8, 0x09815d794e), (0x479cc, 0x0f7b74073a), (0x479e0, 0x14b7dd87bd),
    (0x47a58, 0x160676ad86), (0x47a6c, 0x16d2834636), (0x47a80, 0x16ea8e0f2d),
    (0x47adc, 0x15863044e2), (0x47af0, 0x1593d1c1c0), (0x47b68, 0x1a0ccc13fa),
    (0x47b7c, 0x1bb7ad2e04),
]

SPIKE_UNDEF_EXPECTED = {
    '__nro_header_start',
    '_ZN2nn2ro12LookupSymbolEPmPKc',
    '_ZN3app8lua_bind24WorkModule__get_int_implEPNS_26BattleObjectModuleAccessorEi',
    'free', 'malloc', 'memcpy', 'posix_memalign',
    'pthread_cond_destroy', 'pthread_cond_init', 'pthread_cond_signal', 'pthread_cond_wait',
    'pthread_getspecific', 'pthread_key_create', 'pthread_key_delete',
    'pthread_mutex_destroy', 'pthread_mutex_lock', 'pthread_mutex_unlock', 'pthread_setspecific',
}

SPIKE_STRINGS = {
    b'smashline_install_acmd_script_costume': 17253,
    b'smashline_install_status_script_costume': 17366,
    b'smashline_install_state_callback_costume': 17406,
    b'smashline_install_line_callback_costume': 17985,
    b'game_attacks3': 16453,
    b'miigunner': 16444,
}

INSTALL_NAMES = [
    'smashline_install_acmd_script_costume',
    'smashline_install_status_script_costume',
    'smashline_install_line_callback_costume',
    'smashline_install_state_callback_costume',
]

MII_RE = ('miigunner', 'miifighter', 'miiswordsman')


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def read_lines(p: Path, cache: dict) -> list[str]:
    if p not in cache:
        cache[p] = p.read_text(encoding='utf-8', errors='replace').splitlines()
    return cache[p]


def check_quotes(entries, cache, report_text=None):
    errs = []
    by_path: dict[str, list] = {}
    for e in entries:
        by_path.setdefault(e[0], []).append(e)
    for path, items in by_path.items():
        fp = resolve(path)
        if not fp.is_file():
            errs.append(f'{path}: FILE NOT FOUND')
            continue
        lines = read_lines(fp, cache)
        for _, ln, sub in items:
            if ln > len(lines):
                errs.append(f'{path}:{ln}: file has only {len(lines)} lines')
                continue
            if sub not in lines[ln - 1]:
                errs.append(f'{path}:{ln}: substring not found: {sub[:80]!r}')
            if report_text is not None and sub not in report_text:
                errs.append(f'report-sync: {path}:{ln} substring missing from report: {sub[:80]!r}')
    return errs


def build_key(d: bytes, off: int):
    first = struct.unpack_from('<I', d, off)[0]
    if (first & 0xFF800000) != 0xD2800000 or ((first >> 21) & 3) != 0:
        return None
    rd = first & 0x1F
    val = (first >> 5) & 0xFFFF
    seen = {0}
    for j in range(1, 8):
        w = struct.unpack_from('<I', d, off + 4 * j)[0]
        if (w & 0xFF800000) == 0xF2800000 and (w & 0x1F) == rd:
            hw = (w >> 21) & 3
            if hw in (1, 2) and hw not in seen:
                val |= ((w >> 5) & 0xFFFF) << (16 * hw)
                seen.add(hw)
                if len(seen) == 3:
                    return val, rd
            elif hw in seen:
                return None
    return None


def bl_target(d: bytes, off: int):
    w = struct.unpack_from('<I', d, off)[0]
    if (w & 0xFC000000) != 0x94000000:
        return None
    disp = w & 0x3FFFFFF
    if disp & 0x2000000:
        disp -= 0x4000000
    return off + disp * 4


def adrp_target(d: bytes, off: int):
    w = struct.unpack_from('<I', d, off)[0]
    if (w & 0x9F000000) != 0x90000000:
        return None
    imm = (((w >> 5) & 0x7FFFF) << 2) | ((w >> 29) & 3)
    if imm & (1 << 20):
        imm -= 1 << 21
    return (off & ~0xFFF) + (imm << 12)


def dyn_info(d: bytes):
    mod0 = struct.unpack_from('<I', d, 4)[0]
    dyn = mod0 + struct.unpack_from('<i', d, mod0 + 4)[0]
    tags = {}
    i = dyn
    while True:
        t, v = struct.unpack_from('<qQ', d, i)
        i += 16
        if t == 0:
            break
        tags.setdefault(t, v)
    symtab, strtab = tags[6], tags[5]

    def symname(k):
        nm = struct.unpack_from('<I', d, symtab + 24 * k)[0]
        e = d.index(b'\0', strtab + nm)
        return d[strtab + nm:e].decode('latin1')

    got = {}
    for off, sz in ((tags[7], tags[8]), (tags[0x17], tags[2])):
        for j in range(sz // 24):
            ro, ri, _ra = struct.unpack_from('<QQq', d, off + 24 * j)
            if (ri & 0xFFFFFFFF) == 1026:  # R_JUMP_SLOT
                got[ro] = symname(ri >> 32)
    return tags, symname, got


def veneer_got(d: bytes, target: int, got: dict):
    adrp, ldr = struct.unpack_from('<2I', d, target)
    if (adrp & 0x9F000000) != 0x90000000 or (ldr & 0xFFC00000) != 0xF9400000:
        return None, None
    imm = (((adrp >> 5) & 0x7FFFF) << 2) | ((adrp >> 29) & 3)
    if imm & (1 << 20):
        imm -= 1 << 21
    page = ((target & ~0xFFF) + (imm << 12)) & 0xFFFFFFFF
    g = (page + ((ldr >> 10) & 0xFFF) * 8) & 0xFFFFFFFF
    return g, got.get(g)


def words_check(d: bytes, words: dict):
    errs = []
    for off, hx in words.items():
        if off + 4 > len(d):
            errs.append(f'word {off:#x}: past end of file')
            continue
        got = d[off:off + 4].hex()
        if got != hx:
            errs.append(f'word {off:#x}: expected {hx}, got {got}')
    return errs


def grep_rs(root: Path, pattern_lower: tuple, ignore_case=True):
    """yield (relpath, lineno, line) for lines containing any pattern."""
    import re
    rx = re.compile('|'.join(pattern_lower), re.IGNORECASE if ignore_case else 0)
    for f in sorted(root.rglob('*.rs')):
        try:
            text = f.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        rel = str(f.relative_to(root)).replace('\\', '/')
        for i, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                yield (rel, i, line)


# ---------------------------------------------------------------------------
# structural checks: each returns a list of error strings
# ---------------------------------------------------------------------------
def s_report():
    errs = []
    if not REPORT.is_file():
        return [f'report missing: {REPORT}']
    text = REPORT.read_text(encoding='utf-8', errors='replace')
    if not text.startswith('# P12-SCRIPT-ROUTE'):
        errs.append('report does not start with the task title')
    if 'Status: DONE' not in text:
        errs.append('report missing "Status: DONE"')
    if '## Final summary' not in text:
        errs.append('report missing "## Final summary"')
    return errs


def s_in_nro_hash():
    errs = []
    if not IN_NRO.is_file():
        return [f'input NRO missing: {IN_NRO}']
    got = sha256_of(IN_NRO)
    if got != IN_NRO_SHA:
        errs.append(f'input NRO sha256: expected {IN_NRO_SHA}, got {got}')
    size = IN_NRO.stat().st_size
    if size != 1662976:
        errs.append(f'input NRO size: expected 1662976, got {size}')
    return errs


def s_spike_hashes():
    errs = []
    for p in (SPIKE_NRO, SPIKE_NRO_CLEAN):
        if not p.is_file():
            errs.append(f'spike NRO missing: {p}')
            continue
        got = sha256_of(p)
        if got != SPIKE_SHA:
            errs.append(f'{p.name} sha256: expected {SPIKE_SHA}, got {got}')
        size = p.stat().st_size
        if size != 32768:
            errs.append(f'{p.name} size: expected 32768, got {size}')
    return errs


def s_checkout_commit():
    errs = []
    if not CO.is_dir():
        return [f'checkout missing: {CO}']
    try:
        out = subprocess.run(['git', '-C', str(CO), 'rev-parse', 'HEAD'],
                             capture_output=True, text=True, timeout=30)
        head = out.stdout.strip()
    except Exception as e:  # pragma: no cover
        return [f'git rev-parse failed: {e}']
    if head != CO_COMMIT:
        errs.append(f'checkout HEAD: expected {CO_COMMIT}, got {head!r}')
    return errs


def s_in_nro_structure():
    d = IN_NRO.read_bytes()
    errs = []
    if d.find(b'NRO0') != 0x10:
        errs.append(f'NRO0 magic at {d.find(b"NRO0"):#x}, expected 0x10')
    mod0 = struct.unpack_from('<I', d, 4)[0]
    if mod0 != 0x133070:
        errs.append(f'MOD0 at {mod0:#x}, expected 0x133070')
    segs = [struct.unpack_from('<2I', d, 0x10 + 16 + 8 * i) for i in range(3)]
    want = [(0x0, 0x133000), (0x133000, 0x5f000), (0x192000, 0x4000)]
    if segs != want:
        errs.append(f'segments {[(hex(a), hex(b)) for a, b in segs]} != {[(hex(a), hex(b)) for a, b in want]}')
    syms, _rel, _ = nf.parse(d)
    if len(syms) != 564:
        errs.append(f'total dynamic symbols: expected 564, got {len(syms)}')
    defined = [(n, v, s) for (n, info, shn, v, s) in syms if shn != 0]
    if len(defined) != 11:
        errs.append(f'defined symbols: expected 11, got {len(defined)}')
    disp = ('_ZN7lua2cpp43create_agent_fighter_animcmd_game_miigunner'
            'EN3phx6Hash40EPN3app12BattleObjectEPNS2_26BattleObjectModuleAccessorEP9lua_State')
    st = ('_ZN7lua2cpp44create_agent_fighter_status_script_miigunner'
          'EN3phx6Hash40EPN3app12BattleObjectEPNS2_26BattleObjectModuleAccessorEP9lua_State')
    got = {n: (v, s) for n, v, s in defined}
    if got.get(disp) != (0x47850, 0x1b44):
        errs.append(f'dispatcher symbol: got {got.get(disp)}, expected (0x47850, 0x1b44)')
    if got.get(st) != (0x480, 0x42c):
        errs.append(f'status dispatcher symbol: got {got.get(st)}, expected (0x480, 0x42c)')
    return errs


def s_words():
    return words_check(IN_NRO.read_bytes(), WORDS)


def s_hash40_and_block():
    d = IN_NRO.read_bytes()
    errs = []
    if hash40('game_attacks3') != 0x0d28325277:
        errs.append(f'hash40(game_attacks3) = {hash40("game_attacks3"):#x}')
    if hash40('miigunner') != 0x09815d794e:
        errs.append(f'hash40(miigunner) = {hash40("miigunner"):#x}')
    if hash40('game_attack11') != 0x0d04731edc:
        errs.append(f'hash40(game_attack11) = {hash40("game_attack11"):#x}')
    # game_attacks3 block: hash -> x2, body -> x1, bl -> sv_set_function_hash
    bk = build_key(d, 0x47e34)
    if bk != (0x0d28325277, 2):
        errs.append(f'movz/movk at 0x47e34 assembles to {bk}, expected (0x0d28325277, 2)')
    tgt = adrp_target(d, 0x47e3c)
    if tgt != 0xbc000:
        errs.append(f'adrp at 0x47e3c targets {tgt and hex(tgt)}, expected 0xbc000')
    w = struct.unpack_from('<I', d, 0x47e40)[0]
    if (w & 0xFF800000) != 0x91000000 or ((w >> 10) & 0xFFF) != 0x500 or (w & 0x1F) != 1:
        errs.append(f'add at 0x47e40 not `add x1, x1, #0x500` (word {w:08x})')
    if (tgt or 0) + 0x500 != 0xBC500:
        errs.append('x1 for game_attacks3 is not 0xbc500')
    if bl_target(d, 0x47e4c) != 0x131120:
        errs.append(f'bl at 0x47e4c -> {bl_target(d, 0x47e4c) and hex(bl_target(d, 0x47e4c))}, expected 0x131120')
    # miigunner key block
    bk = build_key(d, 0x479b8)
    if bk != (0x09815d794e, 9):
        errs.append(f'movz/movk at 0x479b8 assembles to {bk}, expected (0x09815d794e, 9)')
    # neighbouring registrations claimed in Q6.4
    for off, name in ((0x47DC4, 'game_attack11'), (0x47E50, 'game_attackhi3'),
                      (0x47E6C, 'game_attacklw3')):
        bk = build_key(d, off)
        want = (hash40(name), 2)
        if bk != want:
            errs.append(f'movz/movk at {off:#x}: got {bk and hex(bk[0])}, expected {hex(want[0])} ({name})')
    # vtable cell: adrp+add at 0x47ca0/0x47ca4 -> 0x192a20
    vt = adrp_target(d, 0x47ca0)
    w = struct.unpack_from('<I', d, 0x47ca4)[0]
    if vt != 0x192000 or ((w >> 10) & 0xFFF) != 0xA20:
        errs.append(f'vtable adrp/add: {vt and hex(vt)} + imm {((w >> 10) & 0xFFF):#x}, expected 0x192000+0xa20')
    return errs


def s_registration_counts():
    d = IN_NRO.read_bytes()
    errs = []
    total = [o for o in range(0x47850, 0x47850 + 0x1b44, 4) if bl_target(d, o) == 0x131120]
    if len(total) != 207:
        errs.append(f'registration calls in dispatcher: expected 207, got {len(total)}')
    leaf = [o for o in total if 0x47C84 <= o < 0x492F8]
    if len(leaf) != 196:
        errs.append(f'registration calls in miigunner leaf: expected 196, got {len(leaf)}')
    if total and (total[0] != 0x47994 or total[-1] != 0x492f4):
        errs.append(f'first/last registration {total[0]:#x}/{total[-1]:#x}, expected 0x47994/0x492f4')
    return errs


def s_switch_keys():
    d = IN_NRO.read_bytes()
    errs = []
    found = []
    off = 0x47850
    while off < 0x47850 + 0x1b44:
        built = build_key(d, off)
        if built is None:
            off += 4
            continue
        val, _rd = built
        consumed = False
        for j in range(1, 11):
            w = struct.unpack_from('<I', d, off + 4 * j)[0]
            if (w & 0xFFE0FC1F) == 0xEB00001F:
                consumed = True
                break
            if (w & 0xFC000000) == 0x94000000:
                break
        if consumed:
            found.append((off, val))
        off += 4
    if found != KEYS:
        errs.append(f'switch keys mismatch: got {[(hex(o), hex(v)) for o, v in found]}')
    return errs


def s_veneers():
    d = IN_NRO.read_bytes()
    errs = []
    _tags, _symname, got = dyn_info(d)
    expect = {
        0x130430: ('_Znwm', 0x193bf0),
        0x131120: ('_ZN3lib8L2CAgent20sv_set_function_hashEPvN3phx6Hash40E', 0x194268),
        0x131130: ('_ZN7lua2cpp27L2CFighterAnimcmdGameCommonC2EPN3app12BattleObject'
                   'EPNS1_26BattleObjectModuleAccessorEP9lua_State', 0x194270),
    }
    for target, (name, got_addr) in expect.items():
        g, n = veneer_got(d, target, got)
        if g != got_addr or n != name:
            errs.append(f'veneer {target:#x}: GOT {g and hex(g)} = {n!r}, expected {got_addr:#x} = {name!r}')
    return errs


def s_main_bin():
    if not MAIN_BIN.is_file():
        return [f'main.bin missing: {MAIN_BIN}']
    d = MAIN_BIN.read_bytes()
    want = {0x64c310: '080c40b9', 0x64c314: '1f750171', 0x64c338: '00011fd6'}
    return words_check(d, want)


def s_build_log():
    errs = []
    if not SPIKE_LOG.is_file():
        return [f'log missing: {SPIKE_LOG}']
    text = SPIKE_LOG.read_text(encoding='utf-8', errors='replace')
    import re as _re
    text = _re.sub(r'\x1b\[[0-9;]*m', '', text)  # cargo colourises its progress lines
    bad = [l for l in text.splitlines() if l.startswith('warning')]
    if bad:
        errs.append(f'{len(bad)} warning lines in build log')
    for needle in ('Finished `release` profile',
                   'Compiling smashline v0.1.0 (https://github.com/hdr-development/smashline#be3ef308)',
                   '57.25s'):
        if needle not in text:
            errs.append(f'build log missing: {needle!r}')
    for p in (SPIKE_LOCK, REF_LOCK):
        if not p.is_file():
            errs.append(f'lock missing: {p}')
        elif 'smashline#be3ef308ed8e479922da192a391e0684184af2af' not in p.read_text(encoding='utf-8', errors='replace'):
            errs.append(f'{p.name} does not pin smashline#be3ef308')
    return errs


def s_spike_nro_symbols():
    d = SPIKE_NRO.read_bytes()
    errs = []
    mod0 = struct.unpack_from('<I', d, 4)[0]
    dyn = mod0 + struct.unpack_from('<i', d, mod0 + 4)[0]
    tags = {}
    i = dyn
    while True:
        t, v = struct.unpack_from('<qQ', d, i)
        i += 16
        if t == 0:
            break
        tags.setdefault(t, v)
    symtab, strtab = tags[6], tags[5]
    cnt = (strtab - symtab) // 24
    undef = set()
    for k in range(cnt):
        nm, info, oth, shn, val, sz = struct.unpack_from('<IBBHQQ', d, symtab + 24 * k)
        if shn == 0 and nm != 0:
            e = d.index(b'\0', strtab + nm)
            undef.add(d[strtab + nm:e].decode('latin1'))
    if undef != SPIKE_UNDEF_EXPECTED:
        missing = SPIKE_UNDEF_EXPECTED - undef
        extra = undef - SPIKE_UNDEF_EXPECTED
        errs.append(f'undefined syms differ: missing={sorted(missing)} extra={sorted(extra)}')
    for s, off in SPIKE_STRINGS.items():
        pos = d.find(s)
        if pos != off:
            errs.append(f'string {s!r} at {pos}, expected {off}')
    return errs


def s_q5_greps():
    errs = []
    # pinned framework: exactly one case-insensitive hit
    hits = list(grep_rs(CO, MII_RE))
    if len(hits) != 1 or hits[0][0] != 'crates/actions/src/attack.rs' or hits[0][1] != 197:
        errs.append(f'checkout Mii hits: {hits[:5]} (expected exactly attack.rs:197)')
    # ssbu_mod_new pgwr plugin: 9 case-insensitive hits in 4 files
    pgwr = WS / 'mods/ssbu_mod_new/src/pgwr/plugin/src'
    hits = list(grep_rs(pgwr, MII_RE))
    files = {h[0] for h in hits}
    want_files = {
        'acmd/littlemac_attack_s4.rs', 'mythra/hero_spin_params.rs',
        'status/dk_cargo/data.rs', 'status/monkey_flip_capture_data.rs',
    }
    if len(hits) != 9:
        errs.append(f'pgwr Mii hits: expected 9, got {len(hits)}')
    if files != want_files:
        errs.append(f'pgwr Mii hit files: {sorted(files)}')
    # 'variant' hits in pgwr: 6, none mentioning a Mii
    var_hits = list(grep_rs(pgwr, ('variant',)))
    if len(var_hits) != 6:
        errs.append(f'pgwr variant hits: expected 6, got {len(var_hits)}')
    mii_var = [h for h in var_hits if any(k in h[2].lower() for k in MII_RE)]
    if mii_var:
        errs.append(f'pgwr variant hits mentioning a Mii: {mii_var}')
    # vendored copies under mgw_standalone: 5 hits in 3 files
    mgw = WS / 'mods/ssbu_mod_new/src/mgw_standalone'
    hits = list(grep_rs(mgw, MII_RE))
    if len(hits) != 5:
        errs.append(f'mgw_standalone Mii hits: expected 5, got {len(hits)}')
    if len({h[0] for h in hits}) != 3:
        errs.append(f'mgw_standalone Mii hit files: expected 3, got {sorted({h[0] for h in hits})}')
    # original_acmd / original_status in this-mod code
    def count(root, pat):
        import re
        rx = re.compile(pat)
        n = 0
        for f in root.rglob('*.rs'):
            n += len(rx.findall(f.read_text(encoding='utf-8', errors='replace')))
        return n
    if count(pgwr, r'original_acmd\(') != 0:
        errs.append('original_acmd( found in src/pgwr/plugin/src (expected 0)')
    if count(WS / 'mods/ssbu_mod_new/src/mgw_swap/src', r'original_acmd\(') != 1:
        errs.append('original_acmd( count in src/mgw_swap/src != 1')
    n = count(pgwr, r'original_status\(') + count(WS / 'mods/ssbu_mod_new/src/mgw_swap/src', r'original_status\(')
    if n != 4:
        errs.append(f'original_status( count in own code: expected 4, got {n}')
    # the four smashline_install_* names in all three framework source trees
    trees = [CO / 'src',
             WS / 'mods/ssbu_mod_new/src/mgw_standalone/smashline_1304/src',
             WS / 'mods/ssbu_mod_new/src/mgw_standalone/vendor/smashline-release/smashline-1.6.8/src']
    for tree in trees:
        if not tree.is_dir():
            errs.append(f'tree missing: {tree}')
            continue
        for name in INSTALL_NAMES:
            if not any(name in f.read_text(encoding='utf-8', errors='replace')
                       for f in tree.rglob('*.rs')):
                errs.append(f'{name} not found in {tree}')
    return errs


POSITIVE = [
    ('report present', s_report),
    ('input NRO sha256 + size (Q6)', s_in_nro_hash),
    ('spike NRO sha256 + size x2 (Q7)', s_spike_hashes),
    ('pinned framework checkout commit (C tier)', s_checkout_commit),
    ('input NRO segments/symbols (Q6)', s_in_nro_structure),
    ('Q6 instruction words', s_words),
    ('Q6 hash40 constants + game_attacks3 block', s_hash40_and_block),
    ('Q6 registration counts 207/196', s_registration_counts),
    ('Q6 switch keys (19)', s_switch_keys),
    ('Q6 veneer -> GOT names', s_veneers),
    ('main.bin 0x64c310 words (Q6)', s_main_bin),
    ('Q7 build log + lock pins', s_build_log),
    ('Q7 spike NRO undefined syms + strings', s_spike_nro_symbols),
    ('Q5 not-found grep counts (Q2/Q5)', s_q5_greps),
]


# ---------------------------------------------------------------------------
# negative controls (must be DETECTED)
# ---------------------------------------------------------------------------
def n_wrong_word():
    d = IN_NRO.read_bytes()
    bad = dict(WORDS)
    bad[0x47E34] = '00000000'
    return None if words_check(d, bad) else 'corrupted expectation at 0x47e34 was NOT detected'


def n_wrong_quote():
    errs = check_quotes([('mods/ssbu_mod_new/CURRENT_INSTALL.md', 255,
                          'smashline still `deadbeef…`')], {})
    return None if errs else 'wrong file:line quote was NOT detected'


def n_wrong_sha():
    got = sha256_of(IN_NRO)
    return None if got != '0' * 64 else 'wrong sha256 expectation was NOT detected'


def n_wrong_sym():
    d = IN_NRO.read_bytes()
    syms, _rel, _ = nf.parse(d)
    got = {n: (v, s) for (n, info, shn, v, s) in syms if shn != 0}
    disp = ('_ZN7lua2cpp43create_agent_fighter_animcmd_game_miigunner'
            'EN3phx6Hash40EPN3app12BattleObjectEPNS2_26BattleObjectModuleAccessorEP9lua_State')
    if got.get(disp) == (0x47850, 0x1B45):
        return 'wrong dispatcher size (0x1b45) was NOT detected'
    return None


CONTROLS = [
    ('control 1: wrong instruction word at 0x47e34 is detected', n_wrong_word),
    ('control 2: wrong file:line quote is detected', n_wrong_quote),
    ('control 3: wrong sha256 is detected', n_wrong_sha),
    ('control 4: wrong dispatcher symbol size is detected', n_wrong_sym),
]


def main(argv):
    neg = '--neg' in argv
    cache: dict = {}
    report_text = REPORT.read_text(encoding='utf-8', errors='replace') if REPORT.is_file() else ''
    failures = 0
    total = 0

    print('== P12-SCRIPT-ROUTE evidence check ==')

    print('-- quotes re-read at cited file:line --')
    for label, entries in (('quoted lines', Q), ('extra cited lines', EXTRA)):
        errs = check_quotes(entries, cache)
        total += 1
        if errs:
            failures += 1
            print(f'  FAIL {label} ({len(entries)} quotes)')
            for e in errs:
                print(f'       {e}')
        else:
            print(f'  OK   {label}: {len(entries)} quotes re-read')

    print('-- report sync (every quoted substring occurs in the report) --')
    total += 1
    errs = check_quotes(Q, cache, report_text=report_text)
    if errs:
        failures += 1
        print(f'  FAIL report-sync ({len(errs)} problems)')
        for e in errs:
            print(f'       {e}')
    else:
        print(f'  OK   report contains all {len(Q)} quoted substrings')

    print('-- structural checks --')
    for name, fn in POSITIVE:
        total += 1
        errs = fn()
        if errs:
            failures += 1
            print(f'  FAIL {name}')
            for e in errs:
                print(f'       {e}')
        else:
            print(f'  OK   {name}')

    if neg:
        print('-- negative controls (each must be detected) --')
        for name, fn in CONTROLS:
            total += 1
            err = fn()
            if err is not None:
                failures += 1
                print(f'  FAIL {name}: {err}')
            else:
                print(f'  OK   {name}')
    else:
        print('-- negative controls skipped (run with --neg) --')

    ok = failures == 0
    print(f'RESULT: {"PASS" if ok else "FAIL"} ({total - failures}/{total} checks passed'
          f'{"" if neg else ", negative controls not run"})')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
