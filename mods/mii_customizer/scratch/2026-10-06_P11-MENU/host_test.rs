//! Host-side unit tests for the pure part of plugin 0.5.0 that the 0.3.0 tests
//! (scratch/2026-10-05_P7-PRESET-ENGINE/host_test.rs) do not cover: list.rs, ui.rs, menu.rs,
//! `Store::set_preset` (with a concurrent reader) and `loadout::load` (contract B+).
//! Built and run by run_host_test.sh with the host rustc; the source files are compiled
//! unchanged.
#![allow(dead_code)]

#[path = "../../plugin/src/list.rs"]
mod list;
#[path = "../../plugin/src/loadout.rs"]
mod loadout;
#[path = "../../plugin/src/logic.rs"]
mod logic;
#[path = "../../plugin/src/menu.rs"]
mod menu;
#[path = "../../plugin/src/preset.rs"]
mod preset;
#[path = "../../plugin/src/ui.rs"]
mod ui;

use list::List;
use loadout as lo;
use loadout::{Origin, Probe, Src, Store, Update};
use menu::{Effect, Kind, Menu, Page, Start, Step};
use preset::Presets;
use std::sync::atomic::{AtomicBool, Ordering};
use ui::{Action, Dispatch, Dropped, Entry, Mode, Outcome};

const W: u64 = 0x0607cd5541; // weight
const WS: u64 = 0x0ee2ec2860; // walk_speed_max
const HAT: u64 = 0x5a00_000f_a9ef_a5ea; // a real headgear handle (session 2 log)

fn mod_file(rel: &str) -> Vec<u8> {
    std::fs::read(format!("{}/{}", env!("MC_MOD_DIR"), rel)).unwrap()
}

/// The three synthetic presets of the 0.3.0 tests: zz_synth_fast (weight 70),
/// zz_synth_heavy (weight 135), zz_synth_partial.
fn presets() -> Box<Presets> {
    let p = Box::new(Presets::new());
    p.init_named();
    let r = preset::parse(&mod_file("scratch/2026-10-05_P7-PRESET-ENGINE/synthetic_presets.txt"), &p);
    assert_eq!((r.state, r.presets, r.rejected), (preset::FileState::Ok, 3, 0));
    p
}

fn lfile(body: &str) -> Vec<u8> {
    format!("mc_list 1\n{body}").into_bytes()
}

fn llist(p: &Presets, body: &str) -> (Box<List>, list::Report) {
    let (l, r) = list::parse(Some(&lfile(body)), p);
    (Box::new(l), r)
}

fn mfile(body: &str) -> Vec<u8> {
    format!("mc_menu 1\n{body}").into_bytes()
}

fn mmenu(p: &Presets, body: &str) -> (Box<Menu>, menu::Report) {
    let (m, r) = menu::parse(Some(&mfile(body)), p);
    (m, r)
}

fn one_reject(p: &Presets, body: &str) -> (u32, menu::Reject) {
    let (_, r) = mmenu(p, body);
    assert_eq!(r.rejected, 1, "{body:?}");
    r.rejects()[0]
}

fn s(bytes: &[u8]) -> &str {
    std::str::from_utf8(bytes).unwrap()
}

// ---------------------------------------------------------------- list.rs (contract F)

#[test]
fn list_contract_constants() {
    assert_eq!(list::VERSION_LINE, "mc_list 1");
    assert_eq!(list::MAX_FILE, 16 * 1024);
    assert_eq!(list::MAX_ENTRIES, 128);
    assert_eq!(list::LABEL_MAX, 63);
    assert_eq!(list::DEFAULT_PREFIX, "nam_chr1_00_");
}

#[test]
fn list_well_formed() {
    let p = presets();
    let (l, r) = llist(
        &p,
        "# comment\n\nzz_synth_heavy nam_chr1_00_dedede\r\n\tzz_synth_fast \t nam_chr1_00_fox   # trailing\nzz_synth_partial x\n",
    );
    assert_eq!((r.state, r.fallback, r.accepted, r.rejected, r.lines), (list::FileState::Ok, false, 3, 0, 6));
    assert_eq!(l.len(), 3);
    assert_eq!((l.preset(0), l.preset(1), l.preset(2), l.preset(3)), (Some(1), Some(0), Some(2), None));
    assert_eq!((s(l.label(0)), s(l.label(1)), s(l.label(2))), ("nam_chr1_00_dedede", "nam_chr1_00_fox", "x"));
    assert_eq!(l.label(3), b"");
    assert_eq!(l.label(usize::MAX), b"");
    assert_eq!((l.find_preset(0), l.find_preset(1), l.find_preset(2), l.find_preset(3)), (Some(1), Some(0), Some(2), None));
}

#[test]
fn list_rejected_lines_leave_the_rest() {
    let p = presets();
    let long = "a".repeat(64);
    let body = format!(
        "zz_synth_fast\nzz_synth_fast a b\nZZ nam_x\nnope nam_x\nzz_synth_fast nam_ok\nzz_synth_fast nam_again\nzz_synth_heavy Nam\nzz_synth_heavy {long}\nzz_synth_heavy nam_ok2\n"
    );
    let (l, r) = llist(&p, &body);
    assert_eq!((r.state, r.accepted, r.rejected), (list::FileState::Ok, 2, 7));
    use list::Reject::*;
    assert_eq!(
        r.rejects(),
        &[(2, FieldCount), (3, FieldCount), (4, BadName), (5, UnknownPreset), (7, DupPreset), (8, BadLabel), (9, BadLabel)]
    );
    assert_eq!(l.len(), 2);
    assert_eq!((s(l.label(0)), s(l.label(1))), ("nam_ok", "nam_ok2"));
    // 63 characters are a label, 64 are not
    assert!(list::valid_label("a".repeat(63).as_bytes()));
    assert!(!list::valid_label(long.as_bytes()));
    assert!(!list::valid_label(b""));
}

#[test]
fn list_fallback_states() {
    let p = presets();
    let check = |bytes: Option<&[u8]>, state| {
        let (l, r) = list::parse(bytes, &p);
        assert_eq!((r.state, r.fallback), (state, true));
        assert_eq!(l.len(), 3);
        assert_eq!(s(l.label(0)), "nam_chr1_00_zz_synth_fast");
        assert_eq!(s(l.label(2)), "nam_chr1_00_zz_synth_partial");
        assert_eq!((l.preset(0), l.preset(2)), (Some(0), Some(2)));
    };
    check(None, list::FileState::Absent);
    check(Some(b"mc_list 2\nzz_synth_fast x\n"), list::FileState::BadVersionLine);
    check(Some(b"mc_list 1 \nzz_synth_fast x\n"), list::FileState::BadVersionLine);
    check(Some(b"\xef\xbb\xbfmc_list 1\nzz_synth_fast x\n"), list::FileState::BadVersionLineBom);
    check(Some(b""), list::FileState::BadVersionLine);
    let mut big = lfile("");
    big.resize(list::MAX_FILE + 1, b'\n');
    check(Some(&big), list::FileState::TooLarge);
    big.truncate(list::MAX_FILE);
    let (l, r) = list::parse(Some(&big), &p);
    assert_eq!((r.state, r.fallback, l.len()), (list::FileState::Ok, false, 0));
}

// ---------------------------------------------------------------- ui.rs: handles

#[test]
fn synthetic_handles() {
    assert_eq!(ui::row_handle(0), 0x5a00_00fe_4d43_0000);
    assert_eq!(ui::row_handle(87), 0x5a00_00fe_4d43_0057);
    assert_eq!(ui::display_handle(87), 0x5a00_01fe_4d43_0057);
    for row in [0u32, 1, 87, 128, 0xfffe, ui::NO_ROW] {
        assert_eq!(ui::synth_row(ui::row_handle(row)), Some(row));
        assert_eq!(ui::synth_row(ui::display_handle(row)), Some(row));
        // the game compares the low 40 bits only: both kinds are the same item
        assert!(ui::same_item(ui::row_handle(row), ui::display_handle(row)));
    }
    // only the low 16 bits of a row are kept
    assert_eq!(ui::synth_row(ui::row_handle(0x1_0005)), Some(5));
    for other in [0u64, HAT, 0x1300_00fe_4d43_0001, 0x5a00_00ff_4d43_0001, 0x5a00_00fe_4d44_0001, u64::MAX] {
        assert_eq!(ui::synth_row(other), None, "{other:#x}");
    }
}

#[test]
fn outcome_tells_decide_from_cancel() {
    assert_eq!(ui::outcome(ui::row_handle(0), 88), Outcome::Decide(0));
    assert_eq!(ui::outcome(ui::row_handle(87), 88), Outcome::Decide(87));
    // a row the list does not have
    assert_eq!(ui::outcome(ui::row_handle(88), 88), Outcome::Cancel);
    assert_eq!(ui::outcome(ui::row_handle(0), 0), Outcome::Cancel);
    // the display copy = nothing was decided, even on the same row
    assert_eq!(ui::outcome(ui::display_handle(0), 88), Outcome::Cancel);
    assert_eq!(ui::outcome(ui::display_handle(87), 88), Outcome::Cancel);
    assert_eq!(ui::outcome(ui::display_handle(ui::NO_ROW), 88), Outcome::Cancel);
    // any other hint, a real handle, garbage
    assert_eq!(ui::outcome(ui::row_handle(3) | (2 << 40), 88), Outcome::Cancel);
    assert_eq!(ui::outcome(HAT, 88), Outcome::Cancel);
    assert_eq!(ui::outcome(0, 88), Outcome::Cancel);
    assert_eq!(ui::outcome(u64::MAX, 88), Outcome::Cancel);
}

#[test]
fn action_of_a_finished_screen() {
    let p = presets();
    let (l, _) = llist(&p, "zz_synth_heavy a\nzz_synth_fast b\n");
    assert_eq!(ui::rows(&l), 3);
    assert_eq!(ui::action(Outcome::Cancel, 0xf589, &l), Action::Cancelled);
    assert_eq!(ui::action(Outcome::Cancel, 0, &l), Action::Cancelled);
    assert_eq!(ui::action(Outcome::Decide(1), 0, &l), Action::UnsavedMii);
    assert_eq!(ui::action(Outcome::Decide(0), 0, &l), Action::UnsavedMii);
    assert_eq!(ui::action(Outcome::Decide(0), 0xf589, &l), Action::Clear { id: 0xf589 });
    assert_eq!(ui::action(Outcome::Decide(1), 0xf589, &l), Action::Set { id: 0xf589, preset: 1 });
    assert_eq!(ui::action(Outcome::Decide(2), 0xf58b, &l), Action::Set { id: 0xf58b, preset: 0 });
    assert_eq!(ui::action(Outcome::Decide(3), 0xf589, &l), Action::NoEntry);
    assert_eq!((ui::current_row(None, &l), ui::current_row(Some(1), &l), ui::current_row(Some(0), &l)), (0, 1, 2));
    assert_eq!(ui::current_row(Some(2), &l), ui::NO_ROW);
}

/// The game's key hash, written out independently: seed 0x811c9dc5, `h = h * 0x89 ^ byte`.
fn key_hash(text: &[u8]) -> u32 {
    text.iter().fold(0x811c_9dc5u32, |h, b| (h as u64 * 0x89) as u32 ^ *b as u32)
}

#[test]
fn label_struct() {
    assert_eq!(ui::LABEL_STRUCT, 0x48);
    let mut out = [0xaau8; ui::LABEL_STRUCT];
    ui::write_label(&mut out, b"nam_mii_hat_none_m");
    assert_eq!(u32::from_le_bytes(out[0..4].try_into().unwrap()), key_hash(b"nam_mii_hat_none_m"));
    assert_eq!(u32::from_le_bytes(out[4..8].try_into().unwrap()), 18);
    assert_eq!(&out[8..26], b"nam_mii_hat_none_m");
    assert!(out[26..].iter().all(|b| *b == 0));
    // values computed outside Rust (python: h=0x811c9dc5; h=(h*0x89 ^ b) & 0xffffffff)
    assert_eq!(ui::label_hash(b""), 0x811c_9dc5);
    assert_eq!(ui::label_hash(b"a"), 0x1850_6e0c);
    // cut at 63 bytes, always terminated
    let long = [b'x'; 80];
    ui::write_label(&mut out, &long);
    assert_eq!(u32::from_le_bytes(out[4..8].try_into().unwrap()), 63);
    assert_eq!(&out[8..71], &long[..63]);
    assert_eq!(out[71], 0);
    assert_eq!(u32::from_le_bytes(out[0..4].try_into().unwrap()), key_hash(&long[..63]));
    ui::write_label(&mut out, b"");
    assert_eq!(out[4..], [0u8; 0x44]);
}

#[test]
fn row_labels_of_the_character_list() {
    let p = presets();
    let (l, _) = llist(&p, "zz_synth_heavy nam_chr1_00_dedede\n");
    assert_eq!(s(ui::row_label(0, &l)), "nam_mii_hat_none_m");
    assert_eq!(s(ui::row_label(1, &l)), "nam_chr1_00_dedede");
    assert_eq!(s(ui::row_label(2, &l)), "nam_mii_hat_unknown");
    assert_eq!(s(ui::row_label(ui::NO_ROW, &l)), "nam_mii_hat_unknown");
}

// ---------------------------------------------------------------- ui.rs: entry decision

#[test]
fn dispatch_decision() {
    let never = || -> bool { panic!("pad state asked") };
    assert_eq!(ui::dispatch(7, true, 88, never), Dispatch::ArmA);
    assert_eq!(ui::dispatch(7, true, 0, never), Dispatch::RefuseA);
    assert_eq!(ui::dispatch(7, false, 88, never), Dispatch::RefuseA);
    assert_eq!(ui::dispatch(1, true, 88, || true), Dispatch::ArmB);
    assert_eq!(ui::dispatch(1, true, 88, || false), Dispatch::Pass);
    assert_eq!(ui::dispatch(1, false, 88, never), Dispatch::Pass);
    assert_eq!(ui::dispatch(1, true, 0, never), Dispatch::Pass);
    for value in [-2, -1, 0, 2, 3, 4, 5, 6, 8, 9, 100] {
        assert_eq!(ui::dispatch(value, true, 88, never), Dispatch::Pass, "{value}");
    }
    assert!(ui::zl_or_zr(1 << 8) && ui::zl_or_zr(1 << 9) && ui::zl_or_zr(u64::MAX));
    assert!(!ui::zl_or_zr(0) && !ui::zl_or_zr(!(3 << 8)));
    assert_eq!((ui::EXIT_MOD, ui::EXIT_HEADGEAR), (7, 1));
}

// ---------------------------------------------------------------- ui.rs: mode state machine

const ALL: [u64; 3] = [u64::MAX; 3];

#[test]
fn mode_one_page_visit() {
    let m = Mode::new();
    assert_eq!((m.phase(), m.active_rows(), m.active_page(), m.in_visit()), (ui::PHASE_IDLE, 0, 0, false));
    assert!(!m.arm(Entry::A, 0, 2), "no scene");
    assert!(!m.arm(Entry::A, 0x1000, 0), "no page");
    assert!(m.arm(Entry::A, 0x1000, 2));
    assert_eq!(m.phase(), ui::PHASE_PENDING);
    // nothing answers for synthetic handles before the list is swapped in
    assert_eq!((m.active_rows(), m.is_active_sub(0x2000), m.row_available(0)), (0, false, false));
    let pending = m.take_pending(0x1000).unwrap();
    assert_eq!((pending.entry, pending.page, pending.hint, pending.in_visit), (Entry::A, 2, None, false));
    assert_eq!(m.phase(), ui::PHASE_IDLE);
    assert_eq!(m.take_pending(0x1000), None, "consumed");
    assert!(!m.activate(Entry::A, 0x1000, 0x2000, 0, 2, 2, &ALL), "no rows");
    assert!(!m.activate(Entry::A, 0x1000, 0, 5, 2, 2, &ALL), "no sub-object");
    assert!(!m.activate(Entry::A, 0, 0x2000, 5, 2, 2, &ALL), "no scene");
    assert!(!m.activate(Entry::A, 0x1000, 0x2000, 5, 0, 2, &ALL), "no page");
    assert!(m.activate(Entry::A, 0x1000, 0x2000, 5, 2, 2, &[0b10101, 0, 0]));
    assert_eq!((m.phase(), m.active_rows(), m.active_page(), m.in_visit()), (ui::PHASE_ACTIVE, 5, 2, true));
    assert!(m.is_active_sub(0x2000) && !m.is_active_sub(0x2008) && !m.is_active_sub(0));
    assert_eq!([0, 1, 2, 3, 4, 5, 64, 200].map(|r| m.row_available(r)), [true, false, true, false, true, false, false, false]);
    assert!(!m.arm(Entry::B, 0x1000, 2), "armed while a list is open");
    assert!(!m.activate(Entry::A, 0x1000, 0x2000, 5, 2, 2, &ALL), "second activate");
    assert_eq!(m.opened(0x1000, 0x2008), None);
    assert_eq!(m.opened(0x1008, 0x2000), None);
    let o = m.opened(0x1000, 0x2000).unwrap();
    assert_eq!((o.entry, o.rows, o.page, o.depth), (Entry::A, 5, 2, 2));
    m.disarm();
    assert_eq!((m.phase(), m.active_rows(), m.active_page(), m.in_visit()), (ui::PHASE_IDLE, 0, 0, false));
    assert_eq!(m.opened(0x1000, 0x2000), None);
    assert!(!m.row_available(0));
}

#[test]
fn mode_pending_is_dropped() {
    let m = Mode::new();
    assert_eq!(m.clear_pending(), Dropped::Nothing);
    assert!(m.arm(Entry::B, 0x1000, 1));
    assert_eq!(m.clear_pending(), Dropped::Arm);
    assert_eq!(m.take_pending(0x1000), None);
    // an arm on one scene never opens a list on another
    assert!(m.arm(Entry::B, 0x1000, 1));
    assert_eq!(m.take_pending(0x3000), None);
    assert_eq!((m.phase(), m.in_visit()), (ui::PHASE_IDLE, false));
    assert_eq!(m.take_pending(0x1000), None);
    // a second arm replaces the first
    assert!(m.arm(Entry::A, 0x1000, 2));
    assert!(m.arm(Entry::B, 0x5000, 1));
    assert_eq!(m.take_pending(0x1000), None);
    assert!(m.arm(Entry::B, 0x5000, 1));
    assert_eq!(m.take_pending(0x5000).map(|p| (p.entry, p.page)), Some((Entry::B, 1)));
    // an open list is not "pending"
    assert!(m.activate(Entry::B, 0x5000, 0x6000, 3, 1, 1, &ALL));
    assert_eq!(m.clear_pending(), Dropped::Nothing);
    assert_eq!(m.phase(), ui::PHASE_ACTIVE);
}

#[test]
fn mode_pages_of_one_visit() {
    let m = Mode::new();
    assert_eq!(m.next_page(0x1000, 3, None), None, "no visit");
    assert!(m.arm(Entry::A, 0x1000, 2));
    assert_eq!(m.next_page(0x1000, 3, None), None, "armed is not a visit");
    let first = m.take_pending(0x1000).unwrap();
    assert!(!first.in_visit);
    assert_eq!(m.next_page(0x1000, 3, None), None, "a page that was taken but never opened is not a visit");
    assert_eq!(m.phase(), ui::PHASE_IDLE);
    assert!(m.activate(first.entry, 0x1000, 0x2000, 24, 2, 2, &ALL));
    assert_eq!(m.next_page(0x1000, 3, None), None, "list still open");
    for change in 1..=10u32 {
        m.page_closed();
        assert_eq!((m.phase(), m.active_rows(), m.active_page(), m.in_visit()), (ui::PHASE_IDLE, 0, 0, true));
        assert!(!m.is_active_sub(0x2000) && !m.row_available(0));
        assert_eq!(m.next_page(0x9000, 3, None), None, "another scene");
        assert_eq!(m.next_page(0x1000, 0, None), None, "no page");
        let (page, hint) = if change % 2 == 1 { (3 + change, None) } else { (2, Some(change)) };
        assert_eq!(m.next_page(0x1000, page, hint), Some(change));
        assert_eq!((m.phase(), m.changes()), (ui::PHASE_PENDING, change));
        assert_eq!(m.next_page(0x1000, page, hint), None, "already pending");
        let next = m.take_pending(0x1000).unwrap();
        assert_eq!((next.entry, next.page, next.hint, next.in_visit), (Entry::A, page, hint, true));
        assert!(m.activate(next.entry, 0x1000, 0x2000, 89, page, 2, &[1, 0, 0]));
        assert_eq!((m.active_page(), m.row_available(0), m.row_available(1)), (page, true, false));
        assert_eq!(m.opened(0x1000, 0x2000).map(|o| (o.page, o.depth)), Some((page, 2)));
    }
    m.disarm();
    assert_eq!((m.in_visit(), m.next_page(0x1000, 2, None)), (false, None));
    // a new visit starts its page count again
    assert!(m.arm(Entry::A, 0x1000, 2));
    assert_eq!(m.changes(), 0);
}

#[test]
fn mode_next_page_that_never_opens() {
    let m = Mode::new();
    assert!(m.arm(Entry::A, 0x1000, 2));
    let first = m.take_pending(0x1000).unwrap();
    assert!(m.activate(first.entry, 0x1000, 0x2000, 24, 2, 2, &ALL));
    m.page_closed();
    assert_eq!(m.next_page(0x1000, 5, Some(4)), Some(1));
    // the dispatcher runs before the headgear state does: the visit is over
    assert_eq!(m.clear_pending(), Dropped::Page);
    assert_eq!((m.phase(), m.in_visit()), (ui::PHASE_IDLE, false));
    assert_eq!(m.take_pending(0x1000), None);
    // the next page waits, and the headgear state of another scene ticks first
    assert!(m.arm(Entry::A, 0x1000, 2));
    let first = m.take_pending(0x1000).unwrap();
    assert!(m.activate(first.entry, 0x1000, 0x2000, 24, 2, 2, &ALL));
    m.page_closed();
    assert_eq!(m.next_page(0x1000, 5, None), Some(1));
    assert_eq!(m.take_pending(0x7000), None);
    assert_eq!((m.phase(), m.in_visit()), (ui::PHASE_IDLE, false));
}

#[test]
fn reentry_conditions() {
    let good = ui::StackView { depth_open: 2, depth_now: 1, slot_state: 5, current_state: 5, restart: 0, change_cb: (0, 0) };
    assert_eq!(ui::can_reenter(&good), Ok(()));
    assert_eq!(ui::can_reenter(&ui::StackView { depth_open: 18, depth_now: 17, ..good }), Ok(()));
    assert_eq!(ui::can_reenter(&ui::StackView { depth_open: 1, depth_now: 0, ..good }), Ok(()));
    let bad = |view: ui::StackView| ui::can_reenter(&view).unwrap_err();
    assert_eq!(bad(ui::StackView { depth_open: 0, depth_now: 0, ..good }), "depth_range");
    assert_eq!(bad(ui::StackView { depth_open: 19, depth_now: 18, ..good }), "depth_range");
    assert_eq!(bad(ui::StackView { depth_open: u32::MAX, depth_now: u32::MAX - 1, ..good }), "depth_range");
    // the original did not pop (depth 0 is never decremented), or popped twice
    assert_eq!(bad(ui::StackView { depth_now: 2, ..good }), "not_popped");
    assert_eq!(bad(ui::StackView { depth_now: 0, ..good }), "not_popped");
    assert_eq!(bad(ui::StackView { depth_now: 3, ..good }), "not_popped");
    assert_eq!(bad(ui::StackView { slot_state: 3, ..good }), "slot_state");
    assert_eq!(bad(ui::StackView { current_state: 3, ..good }), "current_state");
    assert_eq!(bad(ui::StackView { restart: 1, ..good }), "restart_set");
    assert_eq!(bad(ui::StackView { change_cb: (0x1234, 0), ..good }), "change_callback");
    assert_eq!(bad(ui::StackView { change_cb: (0, 1), ..good }), "change_callback");
    assert_eq!((ui::STATE_HEADGEAR, ui::STACK_SLOTS), (5, 19));
}

#[test]
fn small_helpers() {
    // clamp_selected: (selected, cursor, count)
    assert_eq!(ui::clamp_selected(-1, 3, 5), None);
    assert_eq!(ui::clamp_selected(4, 0, 5), None);
    assert_eq!(ui::clamp_selected(5, 4, 5), Some(4));
    assert_eq!(ui::clamp_selected(87, 51, 52), Some(51));
    assert_eq!(ui::clamp_selected(87, 60, 52), Some(0));
    assert_eq!(ui::clamp_selected(87, -1, 52), Some(0));
    assert_eq!(ui::clamp_selected(0, 0, 0), Some(0));
    // first_difference
    assert_eq!(ui::first_difference(&[1, 2, 3], &[1, 2, 3]), None);
    assert_eq!(ui::first_difference(&[1, 2, 3], &[1, 9, 9]), Some(1));
    assert_eq!(ui::first_difference(&[1, 2, 3], &[1, 2]), Some(2));
    assert_eq!(ui::first_difference(&[], &[]), None);
    // vector_count
    assert_eq!(ui::vector_count(0x1000, 0x1000 + 52 * 8, 0x1000 + 64 * 8), Some(52));
    assert_eq!(ui::vector_count(0x1000, 0x1008, 0x1008), Some(1));
    assert_eq!(ui::vector_count(0, 8, 8), None);
    assert_eq!(ui::vector_count(0x1000, 0x1000, 0x1040), None, "empty");
    assert_eq!(ui::vector_count(0x1000, 0x0ff8, 0x1040), None, "end before begin");
    assert_eq!(ui::vector_count(0x1000, 0x1010, 0x1008), None, "capacity before end");
    assert_eq!(ui::vector_count(0x1004, 0x100c, 0x100c), None, "unaligned");
    assert_eq!(ui::vector_count(0x1000, 0x100c, 0x1010), None, "partial element");
    assert_eq!(ui::vector_count(0x1000, 0x1000 + 4096 * 8, 0x1000 + 4096 * 8), Some(4096));
    assert_eq!(ui::vector_count(0x1000, 0x1000 + 4097 * 8, 0x1000 + 4097 * 8), None);
    // same_item
    assert!(ui::same_item(HAT, HAT));
    assert!(ui::same_item(HAT, HAT | (7 << 40)), "the hint is not part of the item");
    assert!(!ui::same_item(HAT, HAT ^ 1));
    assert!(ui::same_item(0, 0x1300_0000_0000_0001), "two handles that are not headgear");
    assert!(ui::same_item(0x5a00_0000_0000_0000, 0), "a zero hash is not a headgear");
    assert!(!ui::same_item(HAT, 0));
    assert!(!ui::same_item(0, HAT));
}

#[test]
fn site_records() {
    assert_eq!((ui::UI_SITES, ui::PROBES), (6, 48));
    assert_eq!(ui::UI_SITE_LIST.len(), ui::UI_SITE_NAMES.len());
    let mut seen = std::collections::HashSet::new();
    for site in ui::UI_SITE_LIST.iter().chain(ui::PROBE_LIST.iter()) {
        assert_eq!(site.offset % 4, 0);
        assert!(site.offset >= 0x100 && site.offset < 0x39c_8000, "{:#x} is not in .text", site.offset);
        assert!(seen.insert(site.offset), "{:#x} twice", site.offset);
    }
    assert_eq!(ui::HAT_STATIC - ui::WORK_RECORD, 0x138);
    assert!(ui::RECORD_SNAPSHOT > 0x138 + 8);
}

// ---------------------------------------------------------------- Store::set_preset

fn field(p: &Presets, hash: u64) -> usize {
    p.fields.find(hash).unwrap()
}

#[test]
fn store_set_and_clear_preset() {
    let p = presets();
    let (w, ws) = (field(&p, W), field(&p, WS));
    let store = Store::new();
    assert_eq!(store.set_preset(0, Some(0)), Update::ZeroId);
    assert_eq!(store.set_preset(0, None), Update::ZeroId);
    assert_eq!((store.len(), store.generation()), (0, 0));
    assert_eq!(store.set_preset(0xf589, None), Update::Unchanged, "clearing what is not there");
    assert_eq!(store.len(), 0);

    assert_eq!(store.set_preset(0xf589, Some(0)), Update::Added);
    assert_eq!((store.len(), store.generation(), store.preset_of_id(0xf589)), (1, 1, Some(0)));
    let hit = store.resolve(0xf589, w, &p).unwrap();
    assert_eq!((hit.value, hit.src), (70.0, Src::Preset));
    assert!(store.first_apply(hit.entry, w) && !store.first_apply(hit.entry, w));

    assert_eq!(store.set_preset(0xf589, Some(0)), Update::Unchanged);
    assert_eq!(store.generation(), 1);
    assert!(!store.first_apply(hit.entry, w), "an unchanged preset keeps its OV marks");

    assert_eq!(store.set_preset(0xf589, Some(1)), Update::Changed);
    assert_eq!((store.len(), store.generation(), store.preset_of_id(0xf589)), (1, 2, Some(1)));
    assert_eq!(store.resolve(0xf589, w, &p).map(|h| h.value), Some(135.0));
    assert!(store.first_apply(hit.entry, w), "a changed preset is reported again");

    assert_eq!(store.set_preset(0xf58b, Some(0)), Update::Added);
    assert_eq!(store.resolve(0xf58b, ws, &p).map(|h| h.value), Some(1.5));
    assert_eq!(store.resolve(0xf589, ws, &p).map(|h| h.value), Some(0.75));

    assert_eq!(store.set_preset(0xf589, None), Update::Changed);
    assert_eq!((store.preset_of_id(0xf589), store.resolve(0xf589, w, &p)), (None, None));
    assert_eq!(store.set_preset(0xf589, None), Update::Unchanged);
    // the entry without content is not written; the other one is
    let table = store.snapshot();
    assert_eq!(table.len(), 1);
    assert_eq!((table.preset(0xf58b), table.preset(0xf589)), (Some(0), None));
    // its place is reused by its own ID
    assert_eq!(store.set_preset(0xf589, Some(2)), Update::Changed);
    assert_eq!(store.len(), 2);
    assert_eq!(store.preset_of_id(0), None);
    assert_eq!(store.preset_of_id(0xdead), None);
}

#[test]
fn store_explicit_values_stay() {
    let p = presets();
    let (w, ws) = (field(&p, W), field(&p, WS));
    let (table, report) = lo::parse(b"mc_loadouts 2\n0000f589 weight 130.0\n0000f589 preset zz_synth_fast\n", &p);
    assert_eq!((report.state, report.rejected), (lo::FileState::Ok, 0));
    let store = Store::new();
    store.publish(&table);
    assert_eq!(store.resolve(0xf589, w, &p).map(|h| (h.value, h.src)), Some((130.0, Src::Explicit)));
    assert_eq!(store.resolve(0xf589, ws, &p).map(|h| (h.value, h.src)), Some((1.5, Src::Preset)));
    assert_eq!(store.set_preset(0xf589, Some(1)), Update::Changed);
    assert_eq!(store.resolve(0xf589, w, &p).map(|h| (h.value, h.src)), Some((130.0, Src::Explicit)));
    assert_eq!(store.resolve(0xf589, ws, &p).map(|h| (h.value, h.src)), Some((0.75, Src::Preset)));
    assert_eq!(store.set_preset(0xf589, None), Update::Changed);
    assert_eq!(store.resolve(0xf589, w, &p).map(|h| (h.value, h.src)), Some((130.0, Src::Explicit)));
    assert_eq!(store.resolve(0xf589, ws, &p), None);
    let table = store.snapshot();
    assert_eq!((table.len(), table.get(0xf589, 0), table.preset(0xf589)), (1, Some(130.0), None));
}

#[test]
fn store_full() {
    let store = Store::new();
    for id in 1..=lo::MAX_IDS as u32 {
        assert_eq!(store.set_preset(id, Some(0)), Update::Added);
    }
    assert_eq!(store.set_preset(1000, Some(0)), Update::Full);
    assert_eq!((store.len(), store.preset_of_id(1000)), (lo::MAX_IDS, None));
    assert_eq!(store.set_preset(7, Some(1)), Update::Changed, "a known ID can still change");
    assert_eq!(store.set_preset(1000, None), Update::Unchanged);
}

#[test]
fn store_serialise_round_trip_after_updates() {
    let p = presets();
    let (table, _) = lo::parse(b"mc_loadouts 2\n0000f589 weight 130.0\n0000f58b preset zz_synth_heavy\n", &p);
    let store = Store::new();
    store.publish(&table);
    assert_eq!(store.set_preset(0xf589, Some(0)), Update::Changed);
    assert_eq!(store.set_preset(0xf58b, None), Update::Changed);
    assert_eq!(store.set_preset(0x0001_0000, Some(2)), Update::Added);
    let now = store.snapshot();
    let mut text = [0u8; lo::MAX_FILE];
    let len = lo::serialise(&now, &p, &mut text).unwrap();
    let text = &text[..len];
    assert_eq!(
        s(text),
        "mc_loadouts 2\n0000f589 preset zz_synth_fast\n0000f589 weight 130\n00010000 preset zz_synth_partial\n"
    );
    let (back, report) = lo::parse(text, &p);
    assert_eq!((report.state, report.rejected), (lo::FileState::Ok, 0));
    assert!(back == now);
    // and a store published from the file resolves like the one that was saved
    let again = Store::new();
    again.publish(&back);
    for id in [0xf589u32, 0xf58b, 0x0001_0000] {
        for f in 0..p.fields.len() {
            assert_eq!(again.resolve(id, f, &p).map(|h| h.value.to_bits()), store.resolve(id, f, &p).map(|h| h.value.to_bits()));
        }
    }
}

#[test]
fn store_set_preset_with_concurrent_resolve() {
    let p = presets();
    let (w, ws) = (field(&p, W), field(&p, WS));
    let (table, _) = lo::parse(b"mc_loadouts 2\n0000f589 walk_speed_max 1.25\n0000f589 preset zz_synth_fast\n", &p);
    let store = Store::new();
    store.publish(&table);
    let stop = AtomicBool::new(false);
    let (p, store, stop) = (&*p, &store, &stop);
    std::thread::scope(|scope| {
        let readers: Vec<_> = (0..3)
            .map(|_| {
                scope.spawn(move || {
                    let (mut fast, mut heavy, mut none, mut other) = (0u64, 0u64, 0u64, 0u64);
                    while !stop.load(Ordering::Relaxed) {
                        // an existing entry: the old or the new preset, or (cleared) none
                        match store.resolve(0xf589, w, p).map(|h| (h.value, h.src)) {
                            Some((v, Src::Preset)) if v == 70.0 => fast += 1,
                            Some((v, Src::Preset)) if v == 135.0 => heavy += 1,
                            None => none += 1,
                            got => panic!("weight resolved to {got:?}"),
                        }
                        // the explicit value never moves
                        assert_eq!(store.resolve(0xf589, ws, p).map(|h| (h.value, h.src)), Some((1.25, Src::Explicit)));
                        // an entry that is being added: nothing, or complete
                        match store.resolve(0xf58b, w, p).map(|h| (h.value, h.src)) {
                            None => {}
                            Some((v, Src::Preset)) if v == 135.0 || v == 70.0 => other += 1,
                            got => panic!("new entry resolved to {got:?}"),
                        }
                        assert_eq!(store.resolve(0xf58b, ws, p).map(|h| h.src).unwrap_or(Src::Preset), Src::Preset);
                    }
                    (fast, heavy, none, other)
                })
            })
            .collect();
        for round in 0..2_000_000u32 {
            let update = match round % 3 {
                0 => store.set_preset(0xf589, Some(1)),
                1 => store.set_preset(0xf589, None),
                _ => store.set_preset(0xf589, Some(0)),
            };
            assert_eq!(update, Update::Changed);
            if round == 1000 {
                assert_eq!(store.set_preset(0xf58b, Some(1)), Update::Added);
            }
        }
        stop.store(true, Ordering::Relaxed);
        let mut reads = 0;
        for reader in readers {
            let (fast, heavy, none, other) = reader.join().unwrap();
            reads += fast + heavy + none + other;
        }
        assert!(reads > 0);
    });
    // round 1_999_999 is a clear
    assert_eq!((store.preset_of_id(0xf589), store.preset_of_id(0xf58b)), (None, Some(1)));
    assert_eq!(store.generation(), 2_000_001);
}

// ---------------------------------------------------------------- loadout::load (contract B+)

#[test]
fn load_picks_the_file() {
    let p = presets();
    let main = b"mc_loadouts 2\n0000f589 preset zz_synth_fast\n";
    let new = b"mc_loadouts 2\n0000f589 preset zz_synth_heavy\n0000f58b weight 100\n";
    // loadouts.txt exists: it is the file, whatever loadouts.new holds
    let (table, report, origin) = lo::load(Probe::Bytes(main), Probe::Bytes(new), &p);
    assert_eq!((origin, report.state, table.len(), table.preset(0xf589)), (Origin::Main, lo::FileState::Ok, 1, Some(0)));
    let (table, _, origin) = lo::load(Probe::Bytes(main), Probe::Absent, &p);
    assert_eq!((origin, table.preset(0xf589)), (Origin::Main, Some(0)));
    // also when it is malformed: loadouts.new is not a fallback for a bad main file
    let (table, report, origin) = lo::load(Probe::Bytes(b"garbage\n"), Probe::Bytes(new), &p);
    assert_eq!(origin, Origin::Main);
    assert_ne!(report.state, lo::FileState::Ok);
    assert_eq!(table.len(), 0);
    let (table, report, origin) = lo::load(Probe::Bytes(b""), Probe::Bytes(new), &p);
    assert_eq!((origin, table.len()), (Origin::Main, 0));
    assert_ne!(report.state, lo::FileState::Ok);
    // loadouts.txt missing and loadouts.new well-formed: recovered
    let (table, report, origin) = lo::load(Probe::Absent, Probe::Bytes(new), &p);
    assert_eq!((origin, report.state), (Origin::Recovered, lo::FileState::Ok));
    assert_eq!((table.len(), table.preset(0xf589), table.get(0xf58b, 0)), (2, Some(1), Some(100.0)));
    assert_eq!(origin.name(), "recovered_new");
    // a recovered file with a rejected line still counts (the file state is ok)
    let (table, report, origin) = lo::load(Probe::Absent, Probe::Bytes(b"mc_loadouts 2\nxyz\n0000f589 weight 100\n"), &p);
    assert_eq!((origin, report.state, report.rejected, table.len()), (Origin::Recovered, lo::FileState::Ok, 1, 1));
    // loadouts.new that does not parse as a whole: off, table empty
    let (table, report, origin) = lo::load(Probe::Absent, Probe::Bytes(b"mc_loadouts 9\n0000f589 weight 100\n"), &p);
    assert_eq!((origin, table.len()), (Origin::Off, 0));
    assert_ne!(report.state, lo::FileState::Ok);
    let (table, _, origin) = lo::load(Probe::Absent, Probe::Bytes(b""), &p);
    assert_eq!((origin, table.len()), (Origin::Off, 0));
    // nothing there, or not readable
    for (a, b) in [
        (Probe::Absent, Probe::Absent),
        (Probe::Absent, Probe::Unreadable),
        (Probe::Unreadable, Probe::Absent),
        (Probe::Unreadable, Probe::Bytes(new)),
        (Probe::Unreadable, Probe::Unreadable),
    ] {
        let (table, _, origin) = lo::load(a, b, &p);
        assert_eq!((origin, table.len()), (Origin::Off, 0), "{a:?} {b:?}");
    }
}

// ---------------------------------------------------------------- menu.rs (contract G)

#[test]
fn menu_contract_constants() {
    assert_eq!(menu::VERSION_LINE, "mc_menu 1");
    assert_eq!(menu::MAX_FILE, 16 * 1024);
    assert_eq!(menu::MAX_ENTRIES, 48);
    assert_eq!(menu::ID_MAX, 31);
    assert_eq!(menu::TEXT_MAX, 40);
    assert_eq!(menu::DEFAULT_LABEL, "nam_chr1_00_miigunner");
    assert_eq!(menu::AVAIL_WORDS, ui::AVAIL_WORDS);
    assert!(menu::AVAIL_WORDS * 64 >= list::MAX_ENTRIES + 1);
}

#[test]
fn menu_well_formed() {
    let p = presets();
    let (m, r) = mmenu(
        &p,
        "# the menu\r\n\r\nentry stats stats Stats\r\n  entry\tjab  slot \t Jab #1 (A)  \r\n\t# indented comment\nentry ftilt slot Forward Tilt\nlabel jab nam_chr1_00_mario   # fallback\nallow jab zz_synth_heavy\t# why not\nallow ftilt zz_synth_fast\nallow jab zz_synth_partial\nlabel stats nam_chr1_00_kirby\n",
    );
    assert_eq!((r.state, r.rejected, r.entries, r.labels, r.allows, r.lines), (menu::FileState::Ok, 0, 3, 2, 3, 12));
    assert_eq!(m.len(), 3);
    let e = |i: usize| m.entry(i).unwrap();
    assert_eq!((s(e(0).id()), e(0).kind(), s(e(0).text()), s(e(0).label())), ("stats", Kind::Stats, "Stats", "nam_chr1_00_kirby"));
    assert_eq!((s(e(1).id()), e(1).kind(), s(e(1).text()), s(e(1).label())), ("jab", Kind::Slot, "Jab #1 (A)", "nam_chr1_00_mario"));
    assert_eq!((s(e(2).id()), e(2).kind(), s(e(2).text()), s(e(2).label())), ("ftilt", Kind::Slot, "Forward Tilt", ""));
    assert_eq!([0, 1, 2, 3, 200].map(|i| e(1).allows(i)), [false, true, true, false, false]);
    assert_eq!([0, 1, 2].map(|i| e(2).allows(i)), [true, false, false]);
    assert_eq!((e(0).allowed(), e(1).allowed(), e(2).allowed()), (0, 2, 1));
    assert!(m.entry(3).is_none() && m.entry(usize::MAX).is_none());
    assert_eq!((m.find_id(b"ftilt"), m.find_id(b"ftil"), m.find_id(b"")), (Some(2), None, None));
    // the text is a C string for the game's setter
    let c = e(1).text_c();
    assert_eq!(&c[..10], b"Jab #1 (A)");
    assert!(c[10..].iter().all(|b| *b == 0));
    // no final newline, and CRLF on the last line
    let (m, r) = menu::parse(Some(b"mc_menu 1\nentry a slot A"), &p);
    assert_eq!((r.state, m.len(), r.lines), (menu::FileState::Ok, 1, 2));
    let (m, r) = menu::parse(Some(b"mc_menu 1\r\nentry a slot A\r\n"), &p);
    assert_eq!((r.state, m.len(), s(m.entry(0).unwrap().text())), (menu::FileState::Ok, 1, "A"));
}

#[test]
fn menu_rejected_lines() {
    let p = presets();
    use menu::Reject::*;
    let base = "entry stats stats Stats\nentry jab slot Jab\n";
    let cases: &[(&str, menu::Reject)] = &[
        ("page x slot X", UnknownWord),
        ("Entry x slot X", UnknownWord),
        ("entry", FieldCount),
        ("entry x", FieldCount),
        ("entry x slot", FieldCount),
        ("entry x slot   \t ", FieldCount),
        ("entry X slot X", BadId),
        ("entry a-b slot X", BadId),
        ("entry abcdefghijklmnopqrstuvwxyz012345 slot X", BadId),
        ("entry jab slot Again", DupId),
        ("entry x Slot X", BadKind),
        ("entry x move X", BadKind),
        ("entry x slot 12345678901234567890123456789012345678901", BadText),
        ("entry x slot a\u{7}b", BadText),
        ("entry x slot a\u{7f}b", BadText),
        ("entry x slot a\u{85}b", BadText),
        ("entry x slot a\u{1f600}b", BadText),
        ("entry stats2 stats More Stats", SecondStats),
        ("label", FieldCount),
        ("label jab", FieldCount),
        ("label jab nam_a nam_b", FieldCount),
        ("label nope nam_a", UnknownId),
        ("label JAB nam_a", BadId),
        ("label jab Nam", BadLabel),
        ("allow jab", FieldCount),
        ("allow jab zz_synth_fast zz_synth_heavy", FieldCount),
        ("allow nope zz_synth_fast", UnknownId),
        ("allow jab nobody", UnknownPreset),
        ("allow jab ZZ", BadName),
        ("allow stats zz_synth_fast", NotSlot),
    ];
    for (line, why) in cases {
        let body = format!("{base}{line}\nentry tail slot Tail\n");
        let (m, r) = mmenu(&p, &body);
        assert_eq!((r.state, r.rejected), (menu::FileState::Ok, 1), "{line:?}");
        assert_eq!(r.rejects(), &[(4, *why)], "{line:?}");
        // the rest stays
        assert_eq!((m.len(), s(m.entry(2).unwrap().id())), (3, "tail"), "{line:?}");
        assert_eq!(m.entry(1).unwrap().allowed(), 0, "{line:?}");
        assert_eq!(m.entry(1).unwrap().label(), b"", "{line:?}");
    }
    // invalid UTF-8 in the text
    let mut bytes = mfile("entry x slot a");
    bytes.extend_from_slice(b"\xff\xfeb\n");
    let (m, r) = menu::parse(Some(&bytes), &p);
    assert_eq!((m.len(), r.rejects()), (0, &[(2, BadText)][..]));
    // duplicates of label and allow: the first stays
    assert_eq!(one_reject(&p, "entry jab slot Jab\nlabel jab nam_a\nlabel jab nam_b\n"), (4, DupLabel));
    let (m, _) = mmenu(&p, "entry jab slot Jab\nlabel jab nam_a\nlabel jab nam_b\n");
    assert_eq!(s(m.entry(0).unwrap().label()), "nam_a");
    assert_eq!(one_reject(&p, "entry jab slot Jab\nallow jab zz_synth_fast\nallow jab zz_synth_fast\n"), (4, DupAllow));
    // label / allow before the entry line: unknown id
    assert_eq!(one_reject(&p, "allow jab zz_synth_fast\nentry jab slot Jab\n"), (2, UnknownId));
    // a rejected entry line defines nothing
    let (m, r) = mmenu(&p, "entry jab move Jab\nallow jab zz_synth_fast\nentry ok slot Ok\n");
    assert_eq!((m.len(), r.rejects()), (1, &[(2, BadKind), (3, UnknownId)][..]));
}

#[test]
fn menu_text_limits() {
    let p = presets();
    assert!(menu::valid_text("1234567890123456789012345678901234567890".as_bytes()));
    assert!(!menu::valid_text("12345678901234567890123456789012345678901".as_bytes()));
    assert!(!menu::valid_text(b""));
    assert!(menu::valid_text("Sm\u{e9}sh \u{30b8}\u{30e3}\u{30d6}".as_bytes()), "two- and three-byte characters");
    assert!(menu::valid_text("\u{ffff}".as_bytes()));
    assert!(!menu::valid_text("\u{10000}".as_bytes()), "four-byte sequences are not read by the game's converter");
    assert!(!menu::valid_text(b"a\tb"));
    assert!(!menu::valid_text(b"a\0b"));
    assert!(!menu::valid_text(b"\xc3"));
    assert!(menu::valid_id(b"a") && menu::valid_id(b"abcdefghijklmnopqrstuvwxyz01234"));
    assert!(!menu::valid_id(b"") && !menu::valid_id(b"abcdefghijklmnopqrstuvwxyz012345") && !menu::valid_id(b"a b"));
    // 13 three-byte characters = 39 bytes fit, with their terminator
    let text = "\u{30b8}".repeat(13);
    let (m, r) = mmenu(&p, &format!("entry x slot {text}\n"));
    assert_eq!((r.rejected, m.len()), (0, 1));
    assert_eq!(m.entry(0).unwrap().text(), text.as_bytes());
    assert_eq!(m.entry(0).unwrap().text_c()[39], 0);
    let (m, _) = mmenu(&p, "entry x slot 1234567890123456789012345678901234567890\n");
    assert_eq!(m.entry(0).unwrap().text_c()[40], 0, "40 bytes are still terminated");
}

#[test]
fn menu_limits_and_file_states() {
    let p = presets();
    let mut body = String::new();
    for i in 0..50 {
        body += &format!("entry e{i} slot Entry {i}\n");
    }
    let (m, r) = mmenu(&p, &body);
    assert_eq!((m.len(), r.entries, r.rejected), (48, 48, 2));
    assert_eq!(r.rejects(), &[(50, menu::Reject::TooManyEntries), (51, menu::Reject::TooManyEntries)]);
    assert_eq!(s(m.entry(47).unwrap().id()), "e47");
    // more rejected lines than the log keeps
    let (_, r) = mmenu(&p, &"bad\n".repeat(40));
    assert_eq!((r.rejected, r.rejects().len(), r.state), (40, menu::REJECT_LOG_LIMIT, menu::FileState::NoEntry));

    let state = |bytes: Option<&[u8]>| {
        let (m, r) = menu::parse(bytes, &p);
        assert_eq!(m.len(), 0);
        assert_eq!(menu::first_page(&m), Page::Direct);
        r.state
    };
    assert_eq!(state(None), menu::FileState::Absent);
    assert_eq!(state(Some(b"")), menu::FileState::BadVersionLine);
    assert_eq!(state(Some(b"mc_menu 2\nentry a slot A\n")), menu::FileState::BadVersionLine);
    assert_eq!(state(Some(b" mc_menu 1\nentry a slot A\n")), menu::FileState::BadVersionLine);
    assert_eq!(state(Some(b"mc_list 1\nentry a slot A\n")), menu::FileState::BadVersionLine);
    assert_eq!(state(Some(b"\xef\xbb\xbfmc_menu 1\nentry a slot A\n")), menu::FileState::BadVersionLineBom);
    assert_eq!(state(Some(b"mc_menu 1\n")), menu::FileState::NoEntry);
    assert_eq!(state(Some(b"mc_menu 1\n# nothing\nentry A slot A\n")), menu::FileState::NoEntry);
    let mut big = mfile("entry a slot A\n");
    big.resize(menu::MAX_FILE + 1, b'\n');
    assert_eq!(state(Some(&big)), menu::FileState::TooLarge);
    big.truncate(menu::MAX_FILE);
    let (m, r) = menu::parse(Some(&big), &p);
    assert_eq!((r.state, m.len()), (menu::FileState::Ok, 1));
}

#[test]
fn delivered_example_menu() {
    let p = presets();
    let (m, r) = menu::parse(Some(&mod_file("builds/0.5.0-menu/example/menu.txt")), &p);
    assert_eq!((r.state, r.rejected), (menu::FileState::Ok, 0));
    assert!(m.len() >= 3);
    assert_eq!((0..m.len()).filter(|i| m.entry(*i).unwrap().kind() == Kind::Stats).count(), 1);
    // today no slot allows anything
    assert!((0..m.len()).all(|i| m.entry(i).unwrap().allowed() == 0));
}

// ---------------------------------------------------------------- pages (contract M)

/// Menu: 0 stats, 1 jab (allows zz_synth_heavy), 2 ftilt (allows nothing).
/// List rows: 0 default, 1 heavy, 2 fast (zz_synth_partial is not listed).
fn world(p: &Presets) -> (Box<Menu>, Box<List>) {
    let (m, r) = mmenu(p, "entry stats stats Stats\nentry jab slot Jab\nentry ftilt slot Forward Tilt\nlabel ftilt nam_chr1_00_fox\nallow jab zz_synth_heavy\n");
    assert_eq!(r.rejected, 0);
    let (l, r) = llist(p, "zz_synth_heavy nam_chr1_00_dedede\nzz_synth_fast nam_chr1_00_fox\n");
    assert_eq!(r.rejected, 0);
    (m, l)
}

#[test]
fn page_codes() {
    for page in [Page::Direct, Page::Main, Page::Entry(0), Page::Entry(1), Page::Entry(47)] {
        assert_ne!(page.code(), 0);
        assert_eq!(Page::from_code(page.code()), Some(page));
    }
    assert_eq!((Page::Direct.code(), Page::Main.code(), Page::Entry(0).code(), Page::Entry(47).code()), (1, 2, 3, 50));
    assert_eq!((Page::from_code(0), Page::from_code(51), Page::from_code(u32::MAX)), (None, None, None));
}

#[test]
fn page_rows_and_availability() {
    let p = presets();
    let (m, l) = world(&p);
    let empty = Menu::new();
    assert_eq!((menu::first_page(&m), menu::first_page(&empty)), (Page::Main, Page::Direct));
    assert_eq!(menu::rows(Page::Main, &m, &l), 3);
    assert_eq!(menu::rows(Page::Direct, &m, &l), 3);
    assert_eq!(menu::rows(Page::Entry(0), &m, &l), 3);
    assert_eq!(menu::rows(Page::Entry(2), &m, &l), 3);
    assert_eq!(menu::rows(Page::Entry(3), &m, &l), 0, "no such entry");
    assert_eq!(menu::rows(Page::Main, &empty, &l), 0);
    let avail = |page| [0u32, 1, 2, 3].map(|row| menu::available(page, row, &m, &l));
    assert_eq!(avail(Page::Main), [true, true, true, false]);
    assert_eq!(avail(Page::Direct), [true, true, true, false]);
    assert_eq!(avail(Page::Entry(0)), [true, true, true, false], "stats: every row");
    assert_eq!(avail(Page::Entry(1)), [true, true, false, false], "slot: the default and what is allowed");
    assert_eq!(avail(Page::Entry(2)), [true, false, false, false], "slot without allow lines: the default only");
    assert_eq!(avail(Page::Entry(3)), [false, false, false, false]);
    assert_eq!(menu::available_mask(Page::Main, &m, &l), [0b111, 0, 0]);
    assert_eq!(menu::available_mask(Page::Entry(1), &m, &l), [0b011, 0, 0]);
    assert_eq!(menu::available_mask(Page::Entry(2), &m, &l), [0b001, 0, 0]);
    assert_eq!(menu::available_mask(Page::Entry(3), &m, &l), [0, 0, 0]);
    // the mask is what Mode answers the row filler with
    let mode = Mode::new();
    assert!(mode.arm(Entry::A, 1, Page::Entry(2).code()));
    mode.take_pending(1).unwrap();
    assert!(mode.activate(Entry::A, 1, 2, 3, Page::Entry(2).code(), 2, &menu::available_mask(Page::Entry(2), &m, &l)));
    assert_eq!([0, 1, 2, 3].map(|r| mode.row_available(r)), [true, false, false, false]);
}

#[test]
fn page_row_labels_and_text() {
    let p = presets();
    let (m, l) = world(&p);
    // main page: the entry's fallback label, else the game's "unknown"; literal text on top
    assert_eq!(s(menu::row_label(Page::Main, 0, &m, &l)), "nam_mii_hat_unknown");
    assert_eq!(s(menu::row_label(Page::Main, 2, &m, &l)), "nam_chr1_00_fox");
    assert_eq!(s(menu::row_label(Page::Main, 3, &m, &l)), "nam_mii_hat_unknown");
    assert_eq!(menu::row_text(Page::Main, 1, &m).map(|t| &t[..4]), Some(&b"Jab\0"[..]));
    assert_eq!(menu::row_text(Page::Main, 3, &m), None);
    // entry pages: the Mii's own class, then the list
    for page in [Page::Entry(0), Page::Entry(1)] {
        assert_eq!(s(menu::row_label(page, 0, &m, &l)), "nam_chr1_00_miigunner");
        assert_eq!(s(menu::row_label(page, 1, &m, &l)), "nam_chr1_00_dedede");
        assert_eq!(s(menu::row_label(page, 2, &m, &l)), "nam_chr1_00_fox");
        assert_eq!(menu::row_text(page, 0, &m), None);
        assert_eq!(menu::row_text(page, 1, &m), None);
    }
    // without a menu: exactly the 0.4.0 list
    assert_eq!(s(menu::row_label(Page::Direct, 0, &m, &l)), "nam_mii_hat_none_m");
    assert_eq!(s(menu::row_label(Page::Direct, 1, &m, &l)), "nam_chr1_00_dedede");
    assert_eq!(menu::row_text(Page::Direct, 0, &m), None);
}

#[test]
fn page_start() {
    let p = presets();
    let (m, l) = world(&p);
    let st = |page, preset, hint| menu::start(page, &m, &l, preset, hint);
    let none = ui::NO_ROW;
    // main page: no tick, cursor on the entry it was left from
    assert_eq!(st(Page::Main, Some(1), None), Start { cursor: 0, tick: none });
    assert_eq!(st(Page::Main, None, Some(2)), Start { cursor: 2, tick: none });
    assert_eq!(st(Page::Main, None, Some(3)), Start { cursor: 0, tick: none });
    // stats: cursor and tick on the Mii's preset, else row 0
    assert_eq!(st(Page::Entry(0), None, None), Start { cursor: 0, tick: 0 });
    assert_eq!(st(Page::Entry(0), Some(1), None), Start { cursor: 1, tick: 1 });
    assert_eq!(st(Page::Entry(0), Some(0), Some(1)), Start { cursor: 2, tick: 2 });
    assert_eq!(st(Page::Entry(0), Some(2), None), Start { cursor: 0, tick: none }, "a preset the list does not show");
    assert_eq!(st(Page::Direct, Some(0), None), Start { cursor: 2, tick: 2 });
    assert_eq!(st(Page::Direct, None, None), Start { cursor: 0, tick: 0 });
    // slot: tick on the default whatever the Mii's stat preset is
    assert_eq!(st(Page::Entry(1), Some(1), None), Start { cursor: 0, tick: 0 });
    assert_eq!(st(Page::Entry(2), None, None), Start { cursor: 0, tick: 0 });
    assert_eq!(st(Page::Entry(2), None, Some(2)), Start { cursor: 2, tick: 0 }, "after a refused row");
    assert_eq!(st(Page::Entry(2), None, Some(9)), Start { cursor: 0, tick: 0 });
}

#[test]
fn page_steps() {
    let p = presets();
    let (m, l) = world(&p);
    let id = 0xf589;
    let st = |page, outcome| menu::step(page, outcome, id, &m, &l);
    let main_at = |entry: u32| Some((Page::Main, Some(entry)));
    // main page
    assert_eq!(st(Page::Main, Outcome::Cancel), Step { next: None, effect: Effect::Nothing });
    for row in 0..3u32 {
        assert_eq!(st(Page::Main, Outcome::Decide(row)), Step { next: Some((Page::Entry(row as usize), None)), effect: Effect::Nothing });
    }
    assert_eq!(st(Page::Main, Outcome::Decide(3)), Step { next: None, effect: Effect::Nothing });
    // stats page: as 0.4.0, then back to the main page with the cursor on Stats
    assert_eq!(st(Page::Entry(0), Outcome::Cancel), Step { next: main_at(0), effect: Effect::Nothing });
    assert_eq!(st(Page::Entry(0), Outcome::Decide(0)), Step { next: main_at(0), effect: Effect::Store(Action::Clear { id }) });
    assert_eq!(st(Page::Entry(0), Outcome::Decide(1)), Step { next: main_at(0), effect: Effect::Store(Action::Set { id, preset: 1 }) });
    assert_eq!(st(Page::Entry(0), Outcome::Decide(2)), Step { next: main_at(0), effect: Effect::Store(Action::Set { id, preset: 0 }) });
    assert_eq!(
        menu::step(Page::Entry(0), Outcome::Decide(2), 0, &m, &l),
        Step { next: main_at(0), effect: Effect::Store(Action::UnsavedMii) }
    );
    // slot pages: nothing is ever stored
    assert_eq!(st(Page::Entry(1), Outcome::Cancel), Step { next: main_at(1), effect: Effect::Nothing });
    assert_eq!(st(Page::Entry(1), Outcome::Decide(0)), Step { next: main_at(1), effect: Effect::SlotChosen { row: 0 } });
    assert_eq!(st(Page::Entry(1), Outcome::Decide(1)), Step { next: main_at(1), effect: Effect::SlotChosen { row: 1 } });
    assert_eq!(st(Page::Entry(1), Outcome::Decide(2)), Step { next: Some((Page::Entry(1), Some(2))), effect: Effect::Refused { row: 2 } });
    assert_eq!(st(Page::Entry(2), Outcome::Decide(0)), Step { next: main_at(2), effect: Effect::SlotChosen { row: 0 } });
    assert_eq!(st(Page::Entry(2), Outcome::Decide(1)), Step { next: Some((Page::Entry(2), Some(1))), effect: Effect::Refused { row: 1 } });
    assert_eq!(st(Page::Entry(2), Outcome::Decide(7)), Step { next: Some((Page::Entry(2), Some(7))), effect: Effect::Refused { row: 7 } });
    // a page that does not exist leaves mod mode
    assert_eq!(st(Page::Entry(3), Outcome::Decide(0)), Step { next: None, effect: Effect::Nothing });
    assert_eq!(st(Page::Entry(3), Outcome::Cancel), Step { next: None, effect: Effect::Nothing });
    // no menu: one page, left by anything
    assert_eq!(st(Page::Direct, Outcome::Cancel), Step { next: None, effect: Effect::Nothing });
    assert_eq!(st(Page::Direct, Outcome::Decide(0)), Step { next: None, effect: Effect::Store(Action::Clear { id }) });
    assert_eq!(st(Page::Direct, Outcome::Decide(1)), Step { next: None, effect: Effect::Store(Action::Set { id, preset: 1 }) });
    assert_eq!(
        menu::step(Page::Direct, Outcome::Decide(1), 0, &m, &l),
        Step { next: None, effect: Effect::Store(Action::UnsavedMii) }
    );
}

/// A whole visit as the hooks drive it: only a decided stats row ever reaches the store, and
/// the simulated state stack is where it was after any number of page changes.
#[test]
fn visit_walkthrough() {
    let p = presets();
    let (m, l) = world(&p);
    let store = Store::new();
    let mode = Mode::new();
    let (scene, sub, id) = (0x1000u64, 0x2000u64, 0xf589u32);
    // stack as the dispatcher leaves it: [.., 3, 5], depth 2
    let mut depth = 2u32;
    let stack = [1u32, 3, 5];
    assert!(mode.arm(Entry::A, scene, menu::first_page(&m).code()));
    // (decided handle or None for B, expected next page)
    let script: &[(Option<u32>, Option<Page>)] = &[
        (Some(1), Some(Page::Entry(1))),      // main -> Jab
        (Some(2), Some(Page::Entry(1))),      // a greyed row reported as decided: same page
        (None, Some(Page::Main)),             // B
        (Some(2), Some(Page::Entry(2))),      // main -> Forward Tilt
        (Some(0), Some(Page::Main)),          // the default
        (Some(0), Some(Page::Entry(0))),      // main -> Stats
        (Some(1), Some(Page::Main)),          // heavy
        (Some(0), Some(Page::Entry(0))),      // Stats again
        (Some(0), Some(Page::Main)),          // clear
        (Some(0), Some(Page::Entry(0))),
        (None, Some(Page::Main)),
        (None, None),                         // B on the main page: leave
    ];
    let mut stored = Vec::new();
    for (k, (decided, expect)) in script.iter().enumerate() {
        let pending = mode.take_pending(scene).unwrap();
        assert_eq!(pending.in_visit, k != 0);
        let page = Page::from_code(pending.page).unwrap();
        let rows = menu::rows(page, &m, &l);
        let start = menu::start(page, &m, &l, store.preset_of_id(id), pending.hint);
        assert!(start.cursor < rows);
        assert!(mode.activate(pending.entry, scene, sub, rows, page.code(), depth, &menu::available_mask(page, &m, &l)));
        // the screen: a decision leaves the list entry in the slot, B leaves the display copy
        let slot = match decided {
            Some(row) => ui::row_handle(*row),
            None => ui::display_handle(start.cursor),
        };
        let opened = mode.opened(scene, sub).unwrap();
        let outcome = ui::outcome(slot, opened.rows);
        let step = menu::step(page, outcome, id, &m, &l);
        mode.page_closed();
        depth -= 1; // the original's pop
        if let Effect::Store(action) = step.effect {
            match action {
                Action::Set { id, preset } => stored.push(store.set_preset(id, Some(preset))),
                Action::Clear { id } => stored.push(store.set_preset(id, None)),
                other => panic!("{other:?}"),
            }
        }
        assert_eq!(step.next.map(|n| n.0), *expect, "step {k}");
        match step.next {
            Some((next, hint)) => {
                let view = ui::StackView {
                    depth_open: opened.depth,
                    depth_now: depth,
                    slot_state: stack[opened.depth as usize],
                    current_state: 5,
                    restart: 0,
                    change_cb: (0, 0),
                };
                assert_eq!(ui::can_reenter(&view), Ok(()));
                depth = opened.depth;
                assert_eq!(mode.next_page(scene, next.code(), hint), Some(k as u32 + 1));
                assert_eq!(depth, 2, "depth after page change {}", k + 1);
            }
            None => mode.disarm(),
        }
    }
    assert_eq!(depth, 1, "back at the edit menu's level");
    assert_eq!(mode.phase(), ui::PHASE_IDLE);
    assert_eq!(stored, [Update::Added, Update::Changed]);
    assert_eq!(store.preset_of_id(id), None);
}
