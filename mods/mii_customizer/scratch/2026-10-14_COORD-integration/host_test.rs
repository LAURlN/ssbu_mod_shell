//! Host test for the 2026-10-14 coordinator fix: a saved slot is written back under the
//! donor whose preset index is stored, not under the first donor `IMPLEMENTED_MOVES` lists
//! for the entry (`menu::slot_names` ignores the preset). Needed once an entry has several
//! donors (tilt_up: miifighter + snake; aerials share one status).
//! Run: rustc +stable-x86_64-pc-windows-gnu --edition 2021 --test -O host_test.rs -o <exe>
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

use loadout::Store;
use preset::Presets;

fn presets() -> Box<Presets> {
    let p = Box::new(Presets::new());
    p.init_named();
    let r = preset::parse(
        b"mc_presets 1\n\
        fighter miifighter 0x0000000001\n\
        0x0607cd5541 100.0\n\
        fighter fox 0x0000000002\n\
        0x0607cd5541 100.0\n\
        fighter mario 0x0000000003\n\
        0x0607cd5541 100.0\n",
        &p,
    );
    assert_eq!(r.rejected, 0);
    p
}

#[test]
fn slot_is_saved_under_the_stored_donor() {
    let p = presets();
    let text = b"mc_menu 1\n\
        entry stats stats Stats\n\
        entry smash_up slot Up Smash\n\
        allow smash_up fox\n";
    let (m, r) = menu::parse_filtered(Some(text), &p, true);
    assert_eq!(r.rejected, 0);
    let entry_idx = m.find_id(b"smash_up").unwrap();
    let mario = p.find_name(b"mario").unwrap();

    // The store holds "mario" for smash_up; the menu's slot_names would answer "fox".
    let store = Store::new();
    store.set_slot(0x00000001, entry_idx, Some(mario));
    let snap = store.snapshot_with_validator(&*m);

    let mut buf = [0u8; 4096];
    let len = loadout::serialise(&snap, &p, &mut buf).unwrap();
    let out = std::str::from_utf8(&buf[..len]).unwrap();
    assert!(out.contains("00000001 slot smash_up mario\n"), "{out}");
    assert!(!out.contains("slot smash_up fox"), "{out}");
}

#[test]
fn implemented_donor_round_trips() {
    let p = presets();
    let text = b"mc_menu 1\n\
        entry stats stats Stats\n\
        entry aerial_back slot Back Air\n\
        allow aerial_back mario\n";
    let (m, r) = menu::parse_filtered(Some(text), &p, true);
    assert_eq!(r.rejected, 0);
    let (table, report) = loadout::parse_with_validator(b"mc_loadouts 3\n00000001 slot aerial_back mario\n", &p, &*m);
    assert_eq!(report.rejected, 0);
    let mut buf = [0u8; 4096];
    let len = loadout::serialise(&table, &p, &mut buf).unwrap();
    let out = std::str::from_utf8(&buf[..len]).unwrap();
    assert!(out.contains("00000001 slot aerial_back mario\n"), "{out}");
}
