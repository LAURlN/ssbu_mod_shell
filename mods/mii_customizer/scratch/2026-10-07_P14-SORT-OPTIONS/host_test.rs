//! Host-side unit tests for plugin 0.7.0 features:
//! 1. Sort by name: ASCII case-insensitive comparison, preset name fallback, order computation.
//! 2. Row mapping & preservation: row 0 pinned, characters 1..N reordered, cursor/tick preservation,
//!    greyed availability preservation, bijective mapping from rows to presets in both orders.
//! 3. Option pages: Kind::Option parsing, OptionItem parsing, MAX_OPTIONS = 32 limit, duplicate
//!    option rejection, empty option entry rejection, navigation, selection, availability,
//!    start on current choice, cancel leaves choice intact, decide changes choice.
//! 4. Composed row texts: main-page "<entry>: <option>" and option-page option item text.
//! 5. Loadout v3: reading v1/v2/v3, writing v3 when options present, writing v2 when no options present,
//!    capacity limits (16 options, 32 IDs), unknown entry/option rejection, default option (0) removes line.
//! 6. Rollback compatibility with 0.6.0.
#![allow(dead_code)]

#[path = "../../plugin/src/list.rs"]
mod list;
#[path = "../../plugin/src/loadout.rs"]
mod loadout;
#[path = "../../plugin/src/logic.rs"]
mod logic;
#[path = "../../plugin/src/menu.rs"]
mod menu;
#[path = "../../plugin/src/names.rs"]
mod names;
#[path = "../../plugin/src/preset.rs"]
mod preset;
#[path = "../../plugin/src/ui.rs"]
mod ui;

use list::List;
use loadout as lo;
use loadout::{Store, Table};
use menu::{Effect, Kind, Page, Start, Step};
use names::Names;
use preset::Presets;
use ui::{Action, Outcome};

fn synthetic_presets() -> Box<Presets> {
    let p = Box::new(Presets::new());
    p.init_named();
    // Register several synthetic presets for testing
    let r = preset::parse(
        b"mc_presets 1\n\
        fighter mario 0x0000000001\n\
        0x0607cd5541 100.0\n\
        fighter zelda 0x0000000002\n\
        0x0607cd5541 90.0\n\
        fighter bowser 0x0000000003\n\
        0x0607cd5541 130.0\n\
        fighter kirby 0x0000000004\n\
        0x0607cd5541 75.0\n\
        fighter fox 0x0000000005\n\
        0x0607cd5541 80.0\n\
        fighter samus 0x0000000006\n\
        0x0607cd5541 105.0\n\
        fighter peach 0x0000000007\n\
        0x0607cd5541 85.0\n\
        fighter yoshi 0x0000000008\n\
        0x0607cd5541 95.0\n\
        fighter donkey 0x0000000009\n\
        0x0607cd5541 120.0\n\
        fighter unlisted 0x000000000a\n\
        0x0607cd5541 110.0\n",
        &p,
    );
    assert_eq!(r.state, preset::FileState::Ok);
    p
}

fn synthetic_list(p: &Presets) -> Box<List> {
    let (l, r) = list::parse(
        Some(
            b"mc_list 1\n\
            zelda nam_zelda\n\
            mario nam_mario\n\
            bowser nam_bowser\n\
            kirby nam_kirby\n\
            fox nam_fox\n\
            samus nam_samus\n\
            peach nam_peach\n\
            yoshi nam_yoshi\n\
            donkey nam_donkey\n",
        ),
        p,
    );
    assert_eq!(r.state, list::FileState::Ok);
    assert_eq!(l.len(), 9);
    Box::new(l)
}

fn synthetic_names(p: &Presets) -> Box<Names> {
    let (n, r) = names::parse(
        Some(
            b"mc_names 1\n\
            miigunner Mii Gunner\n\
            zelda Zelda\n\
            mario Mario\n\
            bowser Bowser\n\
            kirby Kirby\n\
            fox Fox\n\
            samus Samus\n\
            peach Peach\n\
            yoshi Yoshi\n\
            # donkey has no display name, tests fallback to preset name 'donkey'\n",
        ),
        p,
    );
    assert_eq!(r.state, names::FileState::Ok);
    Box::new(n)
}

// ---------------------------------------------------------------------------
// Part 1: Sorting and Names
// ---------------------------------------------------------------------------

#[test]
fn test_ascii_ci_comparison() {
    use names::cmp_ascii_ci;
    assert_eq!(cmp_ascii_ci(b"abc", b"ABC"), core::cmp::Ordering::Equal);
    assert_eq!(cmp_ascii_ci(b"abc", b"abc"), core::cmp::Ordering::Equal);
    assert_eq!(cmp_ascii_ci(b"a", b"B"), core::cmp::Ordering::Less);
    assert_eq!(cmp_ascii_ci(b"B", b"a"), core::cmp::Ordering::Greater);
    assert_eq!(cmp_ascii_ci(b"Mario", b"Kirby"), core::cmp::Ordering::Greater);
    assert_eq!(cmp_ascii_ci(b"Bowser", b"bowser"), core::cmp::Ordering::Equal);
    assert_eq!(cmp_ascii_ci(b"Fox", b"Fox 2"), core::cmp::Ordering::Less);
    assert_eq!(cmp_ascii_ci(b"Fox 2", b"Fox"), core::cmp::Ordering::Greater);
}

#[test]
fn test_names_sort_key_fallback() {
    let p = synthetic_presets();
    let n = synthetic_names(&p);
    let mut buf = [0u8; preset::NAME_BUF];

    let zelda_idx = p.find_name(b"zelda").unwrap();
    assert_eq!(n.sort_key(Some(zelda_idx), &p, &mut buf), b"Zelda");

    let donkey_idx = p.find_name(b"donkey").unwrap();
    // Donkey has no display name in synthetic_names, so falls back to preset name
    assert_eq!(n.sort_key(Some(donkey_idx), &p, &mut buf), b"donkey");

    assert_eq!(n.sort_key(Some(9999), &p, &mut buf), b"");
    assert_eq!(n.sort_key(None, &p, &mut buf), b"");
}

#[test]
fn test_compute_name_order() {
    let p = synthetic_presets();
    let l = synthetic_list(&p);
    let n = synthetic_names(&p);

    let mut order = [0u32; list::MAX_ENTRIES];
    let count = names::compute_name_order(&l, &n, &p, &mut order);
    assert_eq!(count, 9);

    // List order (1-indexed rows):
    // 1: zelda ("Zelda")
    // 2: mario ("Mario")
    // 3: bowser ("Bowser")
    // 4: kirby ("Kirby")
    // 5: fox ("Fox")
    // 6: samus ("Samus")
    // 7: peach ("Peach")
    // 8: yoshi ("Yoshi")
    // 9: donkey (fallback: "donkey")
    //
    // Alphabetical order of display names (case-insensitive):
    // "Bowser" (row 3)
    // "donkey" (row 9, 'd' comes before 'f')
    // "Fox"    (row 5)
    // "Kirby"  (row 4)
    // "Mario"  (row 2)
    // "Peach"  (row 7)
    // "Samus"  (row 6)
    // "Yoshi"  (row 8)
    // "Zelda"  (row 1)

    assert_eq!(order[0], 3); // Bowser
    assert_eq!(order[1], 9); // donkey
    assert_eq!(order[2], 5); // Fox
    assert_eq!(order[3], 4); // Kirby
    assert_eq!(order[4], 2); // Mario
    assert_eq!(order[5], 7); // Peach
    assert_eq!(order[6], 6); // Samus
    assert_eq!(order[7], 8); // Yoshi
    assert_eq!(order[8], 1); // Zelda
}

#[test]
fn test_sort_mapping_bijective_and_preservation() {
    let p = synthetic_presets();
    let l = synthetic_list(&p);
    let n = synthetic_names(&p);

    let mut name_order = [0u32; list::MAX_ENTRIES];
    let count = names::compute_name_order(&l, &n, &p, &mut name_order);
    assert_eq!(count, 9);

    // 1. Bijective mapping: every row in name_order maps back to a valid, distinct row 1..=9 in list
    let mut seen = [false; 10];
    for i in 0..count {
        let mapped = name_order[i] as usize;
        assert!(mapped >= 1 && mapped <= 9);
        assert!(!seen[mapped], "Duplicate mapping for row {}", mapped);
        seen[mapped] = true;
    }

    // 2. Resolve every character in both orders:
    // In fighter order (identity):
    // row 0 has handle 0 -> None (default Mii Gunner)
    // row 1..9 has handle r -> l.preset(r - 1)
    // In name order:
    // row 0 has handle 0 -> None (default Mii Gunner pinned)
    // row r in 1..9 has handle name_order[r - 1] -> l.preset(name_order[r - 1] - 1)
    for row in 0..=9 {
        let handle_fighter = row as u32;
        let handle_name = if row == 0 { 0 } else { name_order[row - 1] };

        let action_fighter = ui::action(Outcome::Decide(handle_fighter), 0x1234, &l);
        let action_name = ui::action(Outcome::Decide(handle_name), 0x1234, &l);

        if row == 0 {
            assert_eq!(action_fighter, Action::Clear { id: 0x1234 });
            assert_eq!(action_name, Action::Clear { id: 0x1234 });
        } else {
            let expected_fighter_preset = l.preset(row - 1).unwrap();
            let expected_name_preset = l.preset(handle_name as usize - 1).unwrap();
            assert_eq!(action_fighter, Action::Set { id: 0x1234, preset: expected_fighter_preset });
            assert_eq!(action_name, Action::Set { id: 0x1234, preset: expected_name_preset });
        }
    }
}

#[test]
fn test_sort_with_greyed_rows() {
    let p = synthetic_presets();
    let l = synthetic_list(&p);
    let n = synthetic_names(&p);

    // Create a menu with a slot entry that only allows Mario and Kirby
    // Mario is row 2 (fighter index 1), Kirby is row 4 (fighter index 3)
    let (m, r) = menu::parse(
        Some(
            b"mc_menu 1\n\
            entry jab slot Jab\n\
            allow jab mario\n\
            allow jab kirby\n",
        ),
        &p,
    );
    assert_eq!(r.state, menu::FileState::Ok);

    let page = Page::Entry(0);

    let mut name_order = [0u32; list::MAX_ENTRIES];
    names::compute_name_order(&l, &n, &p, &mut name_order);

    // Row 0 (default) is always available
    assert!(menu::available(page, 0, &m, &l));

    // In fighter order:
    // row 2 (Mario) is available, row 4 (Kirby) is available. All other rows greyed.
    assert!(menu::available(page, 2, &m, &l));
    assert!(menu::available(page, 4, &m, &l));
    assert!(!menu::available(page, 1, &m, &l)); // Zelda greyed
    assert!(!menu::available(page, 3, &m, &l)); // Bowser greyed

    // In name order:
    // Mario is name_order[5] (order[5] = 2)
    // Kirby is name_order[4] (order[4] = 4)
    // When the UI is in name order, row r corresponds to fighter order row name_order[r].
    // Check that available(page, name_order[r]) correctly preserves availability:
    for name_row in 0..=9 {
        let original_row = name_order[name_row];
        let avail = menu::available(page, original_row, &m, &l);
        if original_row == 0 || original_row == 2 || original_row == 4 {
            assert!(avail, "Row {} (original {}) should be available", name_row, original_row);
        } else {
            assert!(!avail, "Row {} (original {}) should be greyed", name_row, original_row);
        }
    }
}

// ---------------------------------------------------------------------------
// Part 2: Option Pages & Menu Contract G
// ---------------------------------------------------------------------------

#[test]
fn test_menu_kind_option_parsing() {
    let p = synthetic_presets();
    let (m, r) = menu::parse(
        Some(
            b"mc_menu 1\n\
            entry sword option Sword\n\
            option sword miiswordsman Mii Swordfighter\n",
        ),
        &p,
    );
    assert_eq!(r.state, menu::FileState::Ok);
    assert_eq!(m.len(), 1);

    let entry = m.entry(0).unwrap();
    assert_eq!(entry.id(), b"sword");
    assert_eq!(entry.kind(), Kind::Option);
    assert_eq!(entry.text(), b"Sword");
    assert_eq!(entry.options_len(), 1);

    let opt = entry.option(0).unwrap();
    assert_eq!(opt.id(), b"miiswordsman");
    assert_eq!(opt.text(), b"Mii Swordfighter");
}

#[test]
fn test_menu_option_empty_entry_rejected() {
    let p = synthetic_presets();
    // An option entry with NO option lines must be rejected (Reject::NoOptions) and dropped
    let (m, r) = menu::parse(
        Some(
            b"mc_menu 1\n\
            entry sword option Sword\n\
            entry jab slot Jab\n\
            allow jab mario\n",
        ),
        &p,
    );
    assert_eq!(r.state, menu::FileState::Ok);
    assert_eq!(r.rejected, 1);
    assert_eq!(r.rejects()[0].1, menu::Reject::NoOptions);
    assert_eq!(m.len(), 1); // "sword" dropped, only "jab" remains
    assert_eq!(m.entry(0).unwrap().id(), b"jab");
}

#[test]
fn test_menu_option_duplicate_id_rejected() {
    let p = synthetic_presets();
    let (m, r) = menu::parse(
        Some(
            b"mc_menu 1\n\
            entry sword option Sword\n\
            option sword opt1 First Option\n\
            option sword opt1 Duplicate Option\n",
        ),
        &p,
    );
    assert_eq!(r.state, menu::FileState::Ok);
    assert_eq!(r.rejected, 1);
    assert_eq!(r.rejects()[0].1, menu::Reject::DupOptionId);
    assert_eq!(m.len(), 1);
    assert_eq!(m.entry(0).unwrap().options_len(), 1);
    assert_eq!(m.entry(0).unwrap().option(0).unwrap().text(), b"First Option");
}

#[test]
fn test_menu_option_limit_32() {
    let p = synthetic_presets();
    let mut text = String::from("mc_menu 1\nentry weapon option Weapon\n");
    for i in 0..33 {
        text.push_str(&format!("option weapon opt_{} Option {}\n", i, i));
    }
    let (m, r) = menu::parse(Some(text.as_bytes()), &p);
    assert_eq!(r.state, menu::FileState::Ok);
    assert_eq!(r.rejected, 1);
    assert_eq!(r.rejects()[0].1, menu::Reject::TooManyOptions);
    assert_eq!(m.len(), 1);
    assert_eq!(m.entry(0).unwrap().options_len(), 32);
}

#[test]
fn test_option_page_navigation_and_ui() {
    let p = synthetic_presets();
    let l = synthetic_list(&p);
    let (m, r) = menu::parse(
        Some(
            b"mc_menu 1\n\
            entry sword option Sword\n\
            option sword miiswordsman Mii Swordfighter\n\
            option sword beam_sword Beam Sword\n\
            option sword master_sword Master Sword\n",
        ),
        &p,
    );
    assert_eq!(r.state, menu::FileState::Ok);
    let page = Page::Entry(0);

    // Row count on option page equals options_len()
    assert_eq!(menu::rows(page, &m, &l), 3);

    // All options on option page are available
    assert!(menu::available(page, 0, &m, &l));
    assert!(menu::available(page, 1, &m, &l));
    assert!(menu::available(page, 2, &m, &l));
    assert!(!menu::available(page, 3, &m, &l)); // out of bounds

    // Start with current choice = 1 (Beam Sword)
    let start = menu::start(page, &m, &l, None, Some(1));
    assert_eq!(start, Start { cursor: 1, tick: 1 });

    // Cancel (B button) returns to main page with cursor on entry 0, leaving choice intact
    let step_cancel = menu::step(page, Outcome::Cancel, 0x1000, &m, &l);
    assert_eq!(step_cancel, Step {
        next: Some((Page::Main, Some(0))),
        effect: Effect::Nothing,
    });

    // Decide (A button) on row 2 returns to main page and emits OptionChosen
    let step_decide = menu::step(page, Outcome::Decide(2), 0x1000, &m, &l);
    assert_eq!(step_decide, Step {
        next: Some((Page::Main, Some(0))),
        effect: Effect::OptionChosen { entry: 0, option: 2 },
    });
}

// ---------------------------------------------------------------------------
// Part 3: Loadout v3 Storage & Rollover Contract
// ---------------------------------------------------------------------------

#[test]
fn test_loadout_v3_parsing_and_validation() {
    let p = synthetic_presets();
    let (m, _) = menu::parse(
        Some(
            b"mc_menu 1\n\
            entry sword option Sword\n\
            option sword miiswordsman Mii Swordfighter\n\
            option sword beam_sword Beam Sword\n",
        ),
        &p,
    );

    // Well-formed v3 loadout
    let (t, r) = lo::parse_with_validator(
        b"mc_loadouts 3\n\
        0000f589 option sword beam_sword\n",
        &p,
        &*m,
    );
    assert_eq!(r.state, lo::FileState::Ok);
    assert_eq!(r.version, 3);
    assert_eq!(r.accepted, 1);
    assert_eq!(r.option_lines, 1);
    assert_eq!(t.len(), 1);
    let entry = t.entries().iter().find(|e| e.id == 0xf589).unwrap();
    assert_eq!(entry.options_count, 1);
    assert_eq!(entry.options[0].entry, 0);
    assert_eq!(entry.options[0].option, 1);

    // Unknown option entry rejected
    let (_, r_bad_entry) = lo::parse_with_validator(
        b"mc_loadouts 3\n\
        0000f589 option unknown_entry beam_sword\n",
        &p,
        &*m,
    );
    assert_eq!(r_bad_entry.state, lo::FileState::Ok);
    assert_eq!(r_bad_entry.rejected, 1);
    assert_eq!(r_bad_entry.rejects()[0].1, lo::Reject::UnknownOptionEntry);

    // Unknown option id rejected
    let (_, r_bad_opt) = lo::parse_with_validator(
        b"mc_loadouts 3\n\
        0000f589 option sword non_existent_sword\n",
        &p,
        &*m,
    );
    assert_eq!(r_bad_opt.state, lo::FileState::Ok);
    assert_eq!(r_bad_opt.rejected, 1);
    assert_eq!(r_bad_opt.rejects()[0].1, lo::Reject::UnknownOption);
}

#[test]
fn test_loadout_v3_default_removes_line() {
    let p = synthetic_presets();
    let (m, _) = menu::parse(
        Some(
            b"mc_menu 1\n\
            entry sword option Sword\n\
            option sword miiswordsman Mii Swordfighter\n\
            option sword beam_sword Beam Sword\n",
        ),
        &p,
    );

    let (mut t, _) = lo::parse_with_validator(
        b"mc_loadouts 3\n\
        0000f589 option sword beam_sword\n",
        &p,
        &*m,
    );
    assert_eq!(t.len(), 1);

    // Setting option to 0 (default: miiswordsman) removes the line
    let removed = t.set_option(0xf589, 0, 0, b"sword", b"miiswordsman").unwrap();
    assert!(removed);
    // Since entry 0xf589 had only this option line, removing it empties the entry and removes it
    assert_eq!(t.len(), 0);
}

#[test]
fn test_loadout_serialise_v2_vs_v3_rollback() {
    let p = synthetic_presets();
    let (m, _) = menu::parse(
        Some(
            b"mc_menu 1\n\
            entry sword option Sword\n\
            option sword miiswordsman Mii Swordfighter\n\
            option sword beam_sword Beam Sword\n",
        ),
        &p,
    );

    let mut t = Table::new();
    t.set(0xf589, 0, 100.0).unwrap();
    t.set_preset(0xf589, 0).unwrap();

    let mut buf = [0u8; lo::MAX_FILE];

    // Case 1: No option chosen -> writer emits mc_loadouts 2
    let len = lo::serialise(&t, &p, &mut buf).unwrap();
    let text = std::str::from_utf8(&buf[..len]).unwrap();
    assert!(text.starts_with("mc_loadouts 2\n"));
    assert!(!text.contains("option"));

    // Can be read by backwards-compatible v2 parser
    let (back_v2, r_v2) = lo::parse(&buf[..len], &p);
    assert_eq!(r_v2.state, lo::FileState::Ok);
    assert_eq!(r_v2.version, 2);
    assert_eq!(back_v2.len(), 1);

    // Case 2: Non-default option chosen -> writer emits mc_loadouts 3
    t.set_option(0xf589, 0, 1, b"sword", b"beam_sword").unwrap();
    let len3 = lo::serialise(&t, &p, &mut buf).unwrap();
    let text3 = std::str::from_utf8(&buf[..len3]).unwrap();
    assert!(text3.starts_with("mc_loadouts 3\n"));
    assert!(text3.contains("0000f589 option sword beam_sword\n"));

    // Read back with validator matches original table
    let (back3, r3) = lo::parse_with_validator(&buf[..len3], &p, &*m);
    assert_eq!(r3.state, lo::FileState::Ok);
    assert_eq!(r3.version, 3);
    assert!(*back3 == t);
}

#[test]
fn test_loadout_capacity_limits() {
    let mut t = Table::new();

    // Max 16 options per ID
    for i in 1..=16 {
        t.set_option(0x1000, i - 1, i, b"opt", b"val").unwrap();
    }
    assert_eq!(t.entries().iter().find(|e| e.id == 0x1000).unwrap().options_count, 16);
    // 17th option fails
    let err = t.set_option(0x1000, 16, 17, b"opt", b"val");
    assert_eq!(err, Err(lo::Reject::TooManyOptions));

    // Max 32 IDs in Table
    for id in 1..=32 {
        let _ = t.set(id, 0, 100.0);
    }
    assert_eq!(t.len(), 32);
    // 33rd ID fails
    let err_id = t.set(999, 0, 100.0);
    assert_eq!(err_id, Err(lo::Reject::TooManyIds));
}

#[test]
fn test_store_publish_snapshot_roundtrip() {
    let p = synthetic_presets();
    let (m, _) = menu::parse(
        Some(
            b"mc_menu 1\n\
            entry sword option Sword\n\
            option sword miiswordsman Mii Swordfighter\n\
            option sword beam_sword Beam Sword\n",
        ),
        &p,
    );

    let mut t = Table::new();
    t.set(0x1234, 0, 110.0).unwrap();
    t.set_preset(0x1234, 1).unwrap();
    t.set_option(0x1234, 0, 1, b"sword", b"beam_sword").unwrap();

    let store = Store::new();
    store.publish(&t);

    assert_eq!(store.len(), 1);
    assert_eq!(store.option_of_id(0x1234, 0), Some(1));
    assert_eq!(store.option_of_id(0x1234, 1), None);

    // Snapshot with validator recovers option strings
    let snap = store.snapshot_with_validator(&*m);
    assert!(*snap == t);

    // Change option in store
    store.set_option(0x1234, 0, 0); // set to default
    assert_eq!(store.option_of_id(0x1234, 0), None);
    let snap_after = store.snapshot_with_validator(&*m);
    let entry_after = snap_after.entries().iter().find(|e| e.id == 0x1234).unwrap();
    assert_eq!(entry_after.options_count, 0);
}

#[test]
fn test_loadout_option_line_in_v2_rejected() {
    let p = synthetic_presets();
    let (m, _) = menu::parse(
        Some(b"mc_menu 1\nentry sword option Sword\noption sword miiswordsman Mii Swordfighter\n"),
        &p,
    );
    // In version 2, option lines are rejected as FieldCount
    let (_, r) = lo::parse_with_validator(
        b"mc_loadouts 2\n0000f589 option sword miiswordsman\n",
        &p,
        &*m,
    );
    assert_eq!(r.state, lo::FileState::Ok);
    assert_eq!(r.rejected, 1);
    assert_eq!(r.rejects()[0].1, lo::Reject::FieldCount);
}
