"""Negative control for the P11 host tests (host_test.rs next to this file).

Each mutation is applied to a COPY of the pure plugin sources under
builds/.cache/host-test/mut11/ (plugin/src is not touched); the test must then fail or stop
compiling. A mutation whose text is not found counts as missed.

  python scratch/2026-10-06_P11-MENU/mutation_control.py [filter]     (from mods/mii_customizer)

Exit 0 only when every mutation is caught.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOD = HERE.parents[1]
WORK = MOD / "builds/.cache/host-test/mut11"
SOURCES = ("list.rs", "loadout.rs", "logic.rs", "menu.rs", "preset.rs", "ui.rs")
RUSTC = ["rustc", "+stable-x86_64-pc-windows-gnu", "--edition", "2021", "--test", "-C", "opt-level=1"]

# (name, file, old text, new text). Every occurrence of the old text is replaced.
M = [
    # ---- list.rs (contract F)
    ("list file limit 16 KiB + 1", "list.rs", "pub const MAX_FILE: usize = 16 * 1024;", "pub const MAX_FILE: usize = 16 * 1024 + 1;"),
    ("64-character labels accepted", "list.rs", "pub const LABEL_MAX: usize = 63;", "pub const LABEL_MAX: usize = 64;"),
    ("list version line 2 accepted", "list.rs", '"mc_list 1"', '"mc_list 2"'),
    ("duplicate preset accepted in the list", "list.rs", "if self.find_preset(preset).is_some() {", "if false {"),
    ("line with an unknown preset not reported", "list.rs", "None => Err(Reject::UnknownPreset),", "None => continue,"),
    ("fallback label family changed", "list.rs", '"nam_chr1_00_"', '"nam_chr1_01_"'),
    ("upper-case labels accepted", "list.rs", "label.iter().all(|b| matches!(*b, b'a'..=b'z' | ", "label.iter().all(|b| matches!(*b, b'A'..=b'Z' | b'a'..=b'z' | "),
    ("list comments not stripped", "list.rs", "let text = line.split(|b| *b == b'#').next().unwrap_or(&[]);", "let text = line;"),
    # ---- ui.rs: handles, outcome, action, label
    ("synthetic hash changed", "ui.rs", "const SYNTH_HASH: u64 = 0xfe_4d43_0000;", "const SYNTH_HASH: u64 = 0xfd_4d43_0000;"),
    ("display copy has no hint", "ui.rs", "row_handle(row) | (1 << HINT_SHIFT)", "row_handle(row)"),
    ("outcome ignores the hint (cancel reads as decide)", "ui.rs", "Some(row) if decided & HINT_MASK == 0 && row < rows =>", "Some(row) if row < rows =>"),
    ("outcome ignores the row count", "ui.rs", "Some(row) if decided & HINT_MASK == 0 && row < rows =>", "Some(row) if decided & HINT_MASK == 0 =>"),
    ("unsaved Mii (ID 0) gets a store action", "ui.rs", "Outcome::Decide(_) if saved_id == 0 => Action::UnsavedMii,", ""),
    ("decided row off by one", "ui.rs", "Outcome::Decide(row) => match list.preset(row as usize - 1) {", "Outcome::Decide(row) => match list.preset(row as usize) {"),
    ("row 0 does not clear", "ui.rs", "Outcome::Decide(0) => Action::Clear { id: saved_id },", ""),
    ("label hash multiplier changed", "ui.rs", "hash.wrapping_mul(0x89)", "hash.wrapping_mul(0x8b)"),
    ("label not cut at 63 bytes", "ui.rs", "pub const LABEL_TEXT_MAX: usize = 0x3f;", "pub const LABEL_TEXT_MAX: usize = 0x40;"),
    ("current row of a listed preset off by one", "ui.rs", "Some(index) => index as u32 + 1,", "Some(index) => index as u32,"),
    # ---- ui.rs: entry decision
    ("arming exit value 7 -> 6", "ui.rs", "pub const EXIT_MOD: i32 = 7;", "pub const EXIT_MOD: i32 = 6;"),
    ("entry B without ZL/ZR", "ui.rs", "} else if value == EXIT_HEADGEAR && usable && held() {", "} else if value == EXIT_HEADGEAR && usable {"),
    ("entry A armed without anything to show", "ui.rs", "let usable = ready && entries != 0;", "let usable = true;"),
    ("ZR bit moved", "ui.rs", "pub const BUTTON_ZR: u64 = 1 << 9;", "pub const BUTTON_ZR: u64 = 1 << 10;"),
    # ---- ui.rs: mode state machine
    ("arm accepted while a list is open", "ui.rs", "if scene == 0 || page == 0 || self.phase() == PHASE_ACTIVE {", "if scene == 0 || page == 0 {"),
    ("pending page taken by another scene", "ui.rs", "let found = if scene != 0 && self.scene.load(Ordering::Relaxed) == scene && page != 0 {", "let found = if scene != 0 && page != 0 {"),
    ("dropped page not told from a dropped arm", "ui.rs", "let dropped = if self.visit.swap(0, Ordering::Relaxed) != 0 { Dropped::Page } else { Dropped::Arm };", "let dropped = Dropped::Arm;"),
    ("scene not compared (opened / next_page)", "ui.rs", "            || self.scene.load(Ordering::Relaxed) != scene\n", ""),
    ("sub-object not compared", "ui.rs", "            || self.sub.load(Ordering::Relaxed) != sub\n", ""),
    ("next page without a visit", "ui.rs", "            || self.visit.load(Ordering::Relaxed) == 0\n", ""),
    ("next page while a list is open", "ui.rs", "            || self.phase() != PHASE_IDLE\n", ""),
    ("availability mask ignored", "ui.rs", "Some(word) => word.load(Ordering::Relaxed) & (1u64 << (row % 64)) != 0,", "Some(_) => true,"),
    ("rows beyond the page count as available", "ui.rs", "        if row >= self.active_rows() {\n            return false;\n        }\n", ""),
    ("page changes not counted", "ui.rs", "let changes = self.changes.fetch_add(1, Ordering::Relaxed).wrapping_add(1);", "let changes = self.changes.load(Ordering::Relaxed).wrapping_add(1);"),
    ("cursor hint lost", "ui.rs", "self.hint.store(hint.unwrap_or(NO_HINT), Ordering::Relaxed);", "self.hint.store(NO_HINT, Ordering::Relaxed);"),
    ("activate with zero rows", "ui.rs", "if scene == 0 || sub == 0 || rows == 0 || page == 0 || self.phase() != PHASE_IDLE {", "if scene == 0 || sub == 0 || page == 0 || self.phase() != PHASE_IDLE {"),
    ("second activate accepted", "ui.rs", "if scene == 0 || sub == 0 || rows == 0 || page == 0 || self.phase() != PHASE_IDLE {", "if scene == 0 || sub == 0 || rows == 0 || page == 0 {"),
    # ---- ui.rs: re-entry conditions (M3)
    ("re-entry without a pop", "ui.rs", "if view.depth_now.wrapping_add(1) != view.depth_open {", "if false {"),
    ("re-entry at depth 19", "ui.rs", "if view.depth_open == 0 || view.depth_open >= STACK_SLOTS {", "if view.depth_open == 0 {"),
    ("re-entry at depth 0", "ui.rs", "if view.depth_open == 0 || view.depth_open >= STACK_SLOTS {", "if view.depth_open >= STACK_SLOTS {"),
    ("re-entry over another state in the slot", "ui.rs", "if view.slot_state != STATE_HEADGEAR {", "if false {"),
    ("re-entry while another state is current", "ui.rs", "if view.current_state != STATE_HEADGEAR {", "if false {"),
    ("re-entry with the restart byte already set", "ui.rs", "if view.restart != 0 {", "if false {"),
    ("re-entry with a change callback", "ui.rs", "if view.change_cb != (0, 0) {", "if false {"),
    ("headgear state number 5 -> 4", "ui.rs", "pub const STATE_HEADGEAR: u32 = 5;", "pub const STATE_HEADGEAR: u32 = 4;"),
    # ---- ui.rs: helpers
    ("stale selected row not clamped", "ui.rs", "if selected < 0 || (selected as u32) < count {", "if selected < 0 {"),
    ("two non-headgear handles differ", "ui.rs", "(false, false) => true,", "(false, false) => false,"),
    ("same_item compares the hint bits", "ui.rs", "(true, true) => (a ^ b) & 0xff_ffff_ffff == 0,", "(true, true) => a == b,"),
    ("native vector of any size accepted", "ui.rs", "if bytes & 7 != 0 || bytes / 8 > NATIVE_COUNT_MAX {", "if bytes & 7 != 0 {"),
    ("empty native vector accepted", "ui.rs", "if begin == 0 || end <= begin || cap < end || begin & 7 != 0 {", "if begin == 0 || end < begin || cap < end || begin & 7 != 0 {"),
    ("a hook site listed twice", "ui.rs", "[SITE_DISPATCH, SITE_STATE5, SITE_UNLISTED, SITE_LABEL, SITE_SORT, SITE_ROWFILL];", "[SITE_DISPATCH, SITE_STATE5, SITE_UNLISTED, SITE_LABEL, SITE_SORT, SITE_SORT];"),
    # ---- menu.rs (contract G)
    ("menu version line 2 accepted", "menu.rs", '"mc_menu 1"', '"mc_menu 2"'),
    ("49 menu entries accepted", "menu.rs", "pub const MAX_ENTRIES: usize = 48;", "pub const MAX_ENTRIES: usize = 49;"),
    ("41-byte text accepted", "menu.rs", "pub const TEXT_MAX: usize = 40;", "pub const TEXT_MAX: usize = 41;"),
    ("32-character ids accepted", "menu.rs", "pub const ID_MAX: usize = 31;", "pub const ID_MAX: usize = 32;"),
    ("menu file limit 16 KiB + 1", "menu.rs", "pub const MAX_FILE: usize = 16 * 1024;", "pub const MAX_FILE: usize = 16 * 1024 + 1;"),
    ("second stats entry accepted", "menu.rs", "if kind == Kind::Stats && self.has_stats() {", "if false {"),
    ("duplicate id accepted", "menu.rs", "if self.find_id(id).is_some() {", "if false {"),
    ("characters above U+FFFF accepted", "menu.rs", " && c <= 0xffff", ""),
    ("control characters accepted", "menu.rs", "c >= 0x20 && c != 0x7f", "c != 0x7f"),
    ("text not checked as UTF-8", "menu.rs", "Err(_) => false,", "Err(_) => true,"),
    ("allow accepted on the stats entry", "menu.rs", "if slot.kind != Kind::Slot {", "if false {"),
    ("duplicate allow accepted", "menu.rs", "if *word & bit != 0 {", "if false {"),
    ("allow of an unknown preset becomes preset 0", "menu.rs", "let preset = presets.find_name(name).ok_or(Reject::UnknownPreset)?;", "let preset = presets.find_name(name).unwrap_or(0);"),
    ("second label replaces the first", "menu.rs", "        if slot.label_len != 0 {\n            return Err(Reject::DupLabel);\n        }\n", ""),
    ("label for an unknown id creates nothing but is accepted", "menu.rs", "let index = self.find_id(id).ok_or(Reject::UnknownId)?;\n        let slot = self.entries.get_mut(index).ok_or(Reject::UnknownId)?;\n        if slot.label_len", "let index = self.find_id(id).unwrap_or(0);\n        let slot = self.entries.get_mut(index).ok_or(Reject::UnknownId)?;\n        if slot.label_len"),
    ("file without entries is state ok", "menu.rs", "        report.state = FileState::NoEntry;\n", ""),
    ("unknown first word ignored silently", "menu.rs", "            Err(Reject::UnknownWord)\n", "            continue\n"),
    ("extra field on a label / allow line accepted", "menu.rs", "if id.is_empty() || value.is_empty() || !trim(fields).is_empty() {", "if id.is_empty() || value.is_empty() {"),
    ("entry text not trimmed", "menu.rs", "let text = trim(rest);", "let text = rest;"),
    ("'#' cuts the entry text", "menu.rs", "let text = trim(rest);", "let text = trim(rest.split(|b| *b == b'#').next().unwrap_or(&[]));"),
    ("unknown kind becomes slot", "menu.rs", "                    Err(Reject::BadKind)\n", "                    Ok(Kind::Slot)\n"),
    # ---- menu.rs: pages (contract M)
    ("slot rows all available (no greying)", "menu.rs", "Some(preset) => e.allows(preset),", "Some(_) => true,"),
    ("slot default row unavailable", "menu.rs", "Some(_) if row == 0 => true,", "Some(_) if row == 0 => false,"),
    ("stats rows need an allow line", "menu.rs", "            Some(e) if e.kind() == Kind::Stats => true,\n", ""),
    ("unavailable row can be decided", "menu.rs", "Outcome::Decide(row) if !available(page, row, menu, list) => {", "Outcome::Decide(row) if false => {"),
    ("slot decision reaches the store", "menu.rs", "Kind::Slot => Step { next: back, effect: Effect::SlotChosen { row } },", "Kind::Slot => Step { next: back, effect: Effect::Store(ui::action(outcome, saved_id, list)) },"),
    ("stats decision leaves mod mode", "menu.rs", "Kind::Stats => Step { next: back, effect: Effect::Store(ui::action(outcome, saved_id, list)) },", "Kind::Stats => Step { next: None, effect: Effect::Store(ui::action(outcome, saved_id, list)) },"),
    ("stats decision stores nothing", "menu.rs", "Kind::Stats => Step { next: back, effect: Effect::Store(ui::action(outcome, saved_id, list)) },", "Kind::Stats => Step { next: back, effect: Effect::Nothing },"),
    ("B on an entry page leaves mod mode", "menu.rs", "Outcome::Cancel => Step { next: back, effect: Effect::Nothing },", "Outcome::Cancel => Step { next: None, effect: Effect::Nothing },"),
    ("back to the main page without the cursor", "menu.rs", "let back = Some((Page::Main, Some(entry as u32)));", "let back = Some((Page::Main, None));"),
    ("B on the main page opens an entry", "menu.rs", "            _ => leave(Effect::Nothing),\n        },\n        Page::Entry(entry) => {", "            _ => Step { next: Some((Page::Entry(0), None)), effect: Effect::Nothing },\n        },\n        Page::Entry(entry) => {"),
    ("direct page cancel stores", "menu.rs", "Outcome::Cancel => leave(Effect::Nothing),", "Outcome::Cancel => leave(Effect::Store(ui::action(Outcome::Decide(0), saved_id, list))),"),
    ("slot tick follows the cursor", "menu.rs", "_ => Start { cursor: hinted, tick: 0 },", "_ => Start { cursor: hinted, tick: hinted },"),
    ("main page shows a tick", "menu.rs", "Page::Main => Start { cursor: hinted, tick: ui::NO_ROW },", "Page::Main => Start { cursor: hinted, tick: hinted },"),
    ("cursor hint beyond the page kept", "menu.rs", "Some(row) if row < count => row,", "Some(row) => row,"),
    ("row 0 label of an entry page changed", "menu.rs", '"nam_chr1_00_miigunner"', '"nam_chr1_00_miifighter"'),
    ("main page ignores the entry's fallback label", "menu.rs", "Some(e) if !e.label().is_empty() => e.label(),", "Some(e) if false => e.label(),"),
    ("literal text on character rows", "menu.rs", "        _ => None,\n    }\n}\n\n/// Where the cursor and the tick", "        _ => menu.entry(0).map(|e| e.text_c()),\n    }\n}\n\n/// Where the cursor and the tick"),
    ("page codes shifted", "menu.rs", "Page::Entry(entry) => 3 + entry.min(MAX_ENTRIES) as u32,", "Page::Entry(entry) => 4 + entry.min(MAX_ENTRIES) as u32,"),
    ("menu without entries still opens the main page", "menu.rs", "    if menu.len() == 0 {\n        Page::Direct", "    if false {\n        Page::Direct"),
    ("entry page of a missing entry has rows", "menu.rs", "            Some(_) => ui::rows(list),\n            None => 0,", "            Some(_) => ui::rows(list),\n            None => 1,"),
    # ---- loadout.rs: Store::set_preset, load (B+)
    ("ID 0 can get a preset at runtime", "loadout.rs", "return Update::ZeroId;", "{}"),
    ("changed preset keeps its OV marks", "loadout.rs", "            applied.store(0, Ordering::Relaxed);\n            self.generation", "            self.generation"),
    ("generation not counted", "loadout.rs", "self.generation.fetch_add(1, Ordering::Relaxed);", ""),
    ("same preset reported as a change", "loadout.rs", "if cell.load(Ordering::Relaxed) == word {", "if false {"),
    ("full store reported as unchanged", "loadout.rs", "_ => return Update::Full,", "_ => return Update::Unchanged,"),
    ("clearing an unknown ID adds an entry", "loadout.rs", "        if word == 0 {\n            return Update::Unchanged;\n        }\n", ""),
    ("preset word off by one", "loadout.rs", "Some(preset) if preset < u32::MAX as usize => preset as u32 + 1,", "Some(preset) if preset < u32::MAX as usize => preset as u32 + 2,"),
    ("new entry visible without its count", "loadout.rs", "self.count.store(len as u32 + 1, Ordering::Release);", ""),
    ("loadouts.new used although it does not parse", "loadout.rs", "                if report.state == FileState::Ok {\n                    (table, report, Origin::Recovered)", "                if true {\n                    (table, report, Origin::Recovered)"),
    ("recovered file reported as main", "loadout.rs", "(table, report, Origin::Recovered)", "(table, report, Origin::Main)"),
    ("loadouts.new read although loadouts.txt is unreadable", "loadout.rs", "Probe::Unreadable => (Table::new(), Report::new(), Origin::Off),", "Probe::Unreadable => load(Probe::Absent, new, presets),"),
    ("malformed loadouts.txt falls back to loadouts.new", "loadout.rs", "            let (table, report) = parse(bytes, presets);\n            (table, report, Origin::Main)", "            let (table, report) = parse(bytes, presets);\n            if report.state != FileState::Ok { return load(Probe::Absent, new, presets); }\n            (table, report, Origin::Main)"),
]


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else ""
    env = dict(os.environ)
    env["MC_MOD_DIR"] = MOD.as_posix()
    env["PATH"] = str(Path.home() / ".cargo/bin") + os.pathsep + env.get("PATH", "")
    caught = missed = 0
    for name, file, old, new in M:
        if only not in name:
            continue
        if WORK.exists():
            shutil.rmtree(WORK)
        (WORK / "plugin/src").mkdir(parents=True)
        (WORK / "scratch/x").mkdir(parents=True)
        for src in SOURCES:
            shutil.copy(MOD / "plugin/src" / src, WORK / "plugin/src" / src)
        shutil.copy(HERE / "host_test.rs", WORK / "scratch/x/host_test.rs")
        target = WORK / "plugin/src" / file
        text = target.read_bytes().decode("utf-8")
        if old not in text:
            print("NOT APPLIED  %s" % name)
            missed += 1
            continue
        target.write_bytes(text.replace(old, new).encode("utf-8"))
        exe = WORK / "t.exe"
        build = subprocess.run(RUSTC + [str(WORK / "scratch/x/host_test.rs"), "-o", str(exe)],
                               capture_output=True, text=True, env=env)
        if build.returncode != 0:
            print("CAUGHT (does not compile)  %s" % name)
            caught += 1
            continue
        try:
            run = subprocess.run([str(exe)], capture_output=True, text=True, env=env, timeout=300)
            failed = run.returncode != 0
            count = sum(1 for line in run.stdout.splitlines() if line.endswith("FAILED") and line.startswith("test "))
        except subprocess.TimeoutExpired:
            failed, count = True, -1
        if failed:
            print("CAUGHT (%s)  %s" % ("timeout" if count < 0 else "%d tests fail" % count, name))
            caught += 1
        else:
            print("MISSED  %s" % name)
            missed += 1
        sys.stdout.flush()
    if WORK.exists():
        shutil.rmtree(WORK)
    print("%d caught, %d missed" % (caught, missed))
    sys.exit(0 if missed == 0 else 1)


main()
