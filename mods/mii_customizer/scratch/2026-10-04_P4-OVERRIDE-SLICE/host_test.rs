//! Host-side unit tests for plugin/src/loadout.rs and plugin/src/logic.rs (the pure part of
//! the 0.2.0 override build). Built and run by run_host_test.sh with the host rustc; no
//! skyline toolchain involved. The two files are compiled unchanged.
#![allow(dead_code)]

#[path = "../../plugin/src/loadout.rs"]
mod loadout;
#[path = "../../plugin/src/logic.rs"]
mod logic;

use loadout::*;
use logic::*;

const GUNNER: i32 = 0x4a;

fn text<const N: usize>(b: &LineBuf<N>) -> String {
    String::from_utf8(b.as_bytes().to_vec()).unwrap()
}

fn file(body: &str) -> Vec<u8> {
    format!("mc_loadouts 1\n{}", body).into_bytes()
}

fn one_reject(body: &str) -> Reject {
    let (table, report) = parse(&file(body));
    assert_eq!(report.state, FileState::Ok, "{body:?}");
    assert_eq!(table.len(), 0, "{body:?}");
    assert_eq!(report.accepted, 0, "{body:?}");
    assert_eq!(report.rejected, 1, "{body:?}");
    assert_eq!(report.rejects().len(), 1);
    assert_eq!(report.rejects()[0].0, 2, "line number of {body:?}");
    report.rejects()[0].1
}

// ---------------------------------------------------------------- loadout file

#[test]
fn contract_constants() {
    assert_eq!(VERSION_LINE, "mc_loadouts 1");
    assert_eq!(MAX_FILE, 16384);
    assert_eq!(MAX_IDS, 32);
    assert_eq!(KEY_NAMES, ["weight", "walk_speed_max"]);
    assert_eq!(RANGES, [(60.0, 140.0), (0.5, 2.0)]);
    // key index == hash index, so a loadout key cannot be applied to the other hash
    assert_eq!(key_index(hash_name(hash_index(HASH_WEIGHT).unwrap())), Some(0));
    assert_eq!(key_index(hash_name(hash_index(HASH_WALK_SPEED_MAX).unwrap())), Some(1));
}

#[test]
fn delivered_example_file() {
    let bytes = std::fs::read(concat!(env!("MC_MOD_DIR"), "/builds/0.2.0-override/example/loadouts.txt")).unwrap();
    let (table, report) = parse(&bytes);
    assert_eq!(report.state, FileState::Ok);
    assert_eq!((report.accepted, report.replaced, report.rejected), (2, 0, 0));
    assert_eq!(table.len(), 1);
    assert_eq!(table.get(0x0000f589, 0), Some(130.0));
    assert_eq!(table.get(0x0000f589, 1), Some(1.6));
    assert_eq!(table.get(0x0000f58b, 0), None);
    assert_eq!(table.get(0x0000f58b, 1), None);
}

#[test]
fn well_formed_file() {
    let (table, report) = parse(&file(
        "# comment line\n\n0000f589 weight 130.0\n0000F589\twalk_speed_max\t1.6   # trailing comment\n  \t \n  0000f58b   weight   60\n",
    ));
    assert_eq!(report.state, FileState::Ok);
    assert_eq!(report.lines, 7);
    assert_eq!((report.accepted, report.replaced, report.rejected), (3, 0, 0));
    assert_eq!(table.len(), 2);
    assert_eq!(table.get(0xf589, 0), Some(130.0));
    assert_eq!(table.get(0xf589, 1), Some(1.6));
    assert_eq!(table.get(0xf58b, 0), Some(60.0));
    assert_eq!(table.get(0xf58b, 1), None);
    assert_eq!(table.get(0x1234, 0), None);
}

#[test]
fn line_endings_and_missing_final_newline() {
    let (table, report) = parse(b"mc_loadouts 1\r\n0000f589 weight 100\r\n0000f589 walk_speed_max 1.0");
    assert_eq!(report.state, FileState::Ok);
    assert_eq!((report.lines, report.accepted, report.rejected), (3, 2, 0));
    assert_eq!(table.get(0xf589, 0), Some(100.0));
    assert_eq!(table.get(0xf589, 1), Some(1.0));
    // version line only
    let (table, report) = parse(b"mc_loadouts 1");
    assert_eq!((report.state, report.lines, table.len()), (FileState::Ok, 1, 0));
    let (table, report) = parse(b"mc_loadouts 1\n");
    assert_eq!((report.state, report.lines, table.len()), (FileState::Ok, 1, 0));
}

#[test]
fn bad_first_line_disables_everything() {
    for head in [
        "", "\n", "mc_loadouts 2\n", "mc_loadouts 1 \n", " mc_loadouts 1\n", "mc_loadouts  1\n", "mc_loadouts\n",
        "MC_LOADOUTS 1\n", "mc_loadouts 1.0\n", "mc_loadouts 10\n", "# c\nmc_loadouts 1\n", "0000f589 weight 130\n",
        "mc_loadouts 1 # v\n", "mc_loadouts\t1\n",
    ] {
        let bytes = format!("{head}0000f589 weight 130.0\n").into_bytes();
        let (table, report) = parse(&bytes);
        assert_eq!(report.state, FileState::BadVersionLine, "{head:?}");
        assert_eq!(table.len(), 0, "{head:?}");
        assert_eq!(report.accepted, 0);
        let store = Store::new();
        store.publish(&table);
        assert_eq!(store.lookup(0xf589, 0), None);
    }
    let (table, report) = parse(b"\xef\xbb\xbfmc_loadouts 1\n0000f589 weight 130.0\n");
    assert_eq!((report.state, table.len()), (FileState::BadVersionLineBom, 0));
    let (table, report) = parse(b"\xffmc_loadouts 1\n0000f589 weight 130.0\n");
    assert_eq!((report.state, table.len()), (FileState::BadVersionLine, 0));
    assert_eq!(FileState::BadVersionLine.name(), "bad_version_line");
}

#[test]
fn file_size_limit() {
    let mut bytes = file("0000f589 weight 130.0\n");
    while bytes.len() < MAX_FILE {
        bytes.push(b'\n');
    }
    assert_eq!(bytes.len(), MAX_FILE);
    let (table, report) = parse(&bytes);
    assert_eq!((report.state, table.get(0xf589, 0)), (FileState::Ok, Some(130.0)));
    bytes.push(b'\n');
    let (table, report) = parse(&bytes);
    assert_eq!((report.state, table.len(), report.accepted), (FileState::TooLarge, 0, 0));
}

#[test]
fn rejected_ids() {
    for id in ["f589", "0000f58", "0000f5890", "0x00f589", "0000f58g", "0000 f589", "+000f589", "-000f589", "f589f589f"] {
        let why = one_reject(&format!("{id} weight 100\n"));
        assert!(why == Reject::BadId || why == Reject::FieldCount, "{id}: {why:?}");
    }
    assert_eq!(one_reject("0000f58g weight 100\n"), Reject::BadId);
    assert_eq!(one_reject("f589 weight 100\n"), Reject::BadId);
    assert_eq!(one_reject("00000000 weight 100\n"), Reject::ZeroId);
    assert_eq!(parse_id("ffffffff"), Ok(0xffff_ffff));
    assert_eq!(parse_id("0000F589"), Ok(0xf589));
    assert_eq!(parse_id("00000001"), Ok(1));
}

#[test]
fn rejected_keys_and_field_counts() {
    for key in ["Weight", "weight_", "walk_speed", "walk_speed_max2", "dash_speed", "0", "jump"] {
        assert_eq!(one_reject(&format!("0000f589 {key} 100\n")), Reject::UnknownKey, "{key}");
    }
    for line in ["0000f589", "0000f589 weight", "0000f589 weight 100 1", "weight", "0000f589 weight=100", "0000f589,weight,100"] {
        assert_eq!(one_reject(&format!("{line}\n")), Reject::FieldCount, "{line}");
    }
    // a comment that cuts a field off
    assert_eq!(one_reject("0000f589 weight #100\n"), Reject::FieldCount);
    // other white space is not a separator
    assert_eq!(one_reject("0000f589\u{a0}weight 100\n"), Reject::FieldCount);
}

#[test]
fn rejected_values() {
    for v in [
        "abc", "1e2", "1E2", "inf", "-inf", "nan", "NaN", "infinity", "0x64", "100.", ".5", "1.2.3", "1,5", "+100", "--1", "-",
        "100f", "1_00", "١٠٠", "1234567890123456789", "0.0000000000000000001", "1000000000000000000000000",
    ] {
        assert_eq!(one_reject(&format!("0000f589 weight {v}\n")), Reject::BadValue, "{v}");
    }
    for (key, v) in [
        ("weight", "59.999"), ("weight", "140.001"), ("weight", "0"), ("weight", "-100"), ("weight", "1000"),
        ("weight", "999999999999999999"), ("walk_speed_max", "0.499"), ("walk_speed_max", "2.001"),
        ("walk_speed_max", "0"), ("walk_speed_max", "-1.0"), ("walk_speed_max", "100"), ("weight", "1.6"),
    ] {
        assert_eq!(one_reject(&format!("0000f589 {key} {v}\n")), Reject::OutOfRange, "{key} {v}");
    }
}

#[test]
fn accepted_range_boundaries_and_decimal_values() {
    for (key, v, want) in [
        ("weight", "60", 60.0f32), ("weight", "60.0", 60.0), ("weight", "140", 140.0), ("weight", "140.000", 140.0),
        ("weight", "104.5", 104.5), ("weight", "0104", 104.0), ("walk_speed_max", "0.5", 0.5),
        ("walk_speed_max", "2", 2.0), ("walk_speed_max", "2.0", 2.0), ("walk_speed_max", "1.155", 1.155),
        ("walk_speed_max", "1.6", 1.6), ("walk_speed_max", "001.5230", 1.523),
    ] {
        let (table, report) = parse(&file(&format!("0000f589 {key} {v}\n")));
        assert_eq!(report.rejected, 0, "{key} {v}");
        assert_eq!(table.get(0xf589, key_index(key).unwrap()), Some(want), "{key} {v}");
    }
    assert_eq!(parse_decimal("130.0"), Some(130.0));
    assert_eq!(parse_decimal("-1.5"), Some(-1.5));
    assert_eq!(parse_decimal("0.1"), Some(0.1));
    assert_eq!(parse_decimal("123456789012345678"), Some(123456789012345678.0));
    assert_eq!(parse_decimal(""), None);
    assert!(!in_range(0, f32::NAN) && !in_range(0, f32::INFINITY) && !in_range(2, 1.0));
}

#[test]
fn non_utf8_line_is_ignored_alone() {
    let mut bytes = file("0000f589 weight 130.0\n");
    bytes.extend_from_slice(b"0000f58b weight 1\xff0\n");
    bytes.extend_from_slice(b"# caf\xe9\n");
    bytes.extend_from_slice(b"0000f58b walk_speed_max 1.2\n");
    let (table, report) = parse(&bytes);
    assert_eq!(report.state, FileState::Ok);
    assert_eq!((report.accepted, report.rejected), (2, 2));
    assert_eq!(report.rejects(), &[(3, Reject::NonUtf8), (4, Reject::NonUtf8)]);
    assert_eq!(table.get(0xf589, 0), Some(130.0));
    assert_eq!(table.get(0xf58b, 0), None);
    assert_eq!(table.get(0xf58b, 1), Some(1.2));
}

#[test]
fn later_line_replaces_earlier_one() {
    let (table, report) = parse(&file(
        "0000f589 weight 130\n0000f589 walk_speed_max 1.6\n0000f589 weight 70\n0000f589 weight 999\n0000F589 walk_speed_max 0.75\n",
    ));
    assert_eq!((report.accepted, report.replaced, report.rejected), (4, 2, 1));
    assert_eq!(report.rejects(), &[(5, Reject::OutOfRange)]);
    assert_eq!(table.len(), 1);
    // the rejected later line does not disturb the value set before it
    assert_eq!(table.get(0xf589, 0), Some(70.0));
    assert_eq!(table.get(0xf589, 1), Some(0.75));
}

#[test]
fn at_most_32_distinct_ids() {
    let mut body = String::new();
    for i in 1..=40u32 {
        body += &format!("{:08x} weight {}\n", i, 60 + i);
    }
    // known ids still accept further keys and replacements after the table is full
    body += "00000005 walk_speed_max 1.25\n00000005 weight 61\n00000028 walk_speed_max 1.0\n";
    let (table, report) = parse(&file(&body));
    assert_eq!(report.state, FileState::Ok);
    assert_eq!(table.len(), 32);
    assert_eq!((report.accepted, report.replaced, report.rejected), (34, 1, 9));
    assert!(report.rejects().iter().all(|(_, why)| *why == Reject::TooManyIds));
    assert_eq!(report.rejects()[0].0, 34); // line of the 33rd id
    assert_eq!(report.rejects().last().unwrap().0, 44);
    assert_eq!(table.get(32, 0), Some(92.0));
    assert_eq!(table.get(33, 0), None);
    assert_eq!(table.get(40, 1), None);
    assert_eq!(table.get(5, 0), Some(61.0));
    assert_eq!(table.get(5, 1), Some(1.25));
}

#[test]
fn reject_log_is_bounded_but_counts_everything() {
    let mut body = String::new();
    for _ in 0..200 {
        body += "zzz\n";
    }
    body += "0000f589 weight 130\n";
    let (table, report) = parse(&file(&body));
    assert_eq!(report.rejected, 200);
    assert_eq!(report.rejects().len(), REJECT_LOG_LIMIT);
    assert_eq!(report.rejects()[63], (65, Reject::FieldCount));
    assert_eq!(table.get(0xf589, 0), Some(130.0));
    for why in [Reject::NonUtf8, Reject::FieldCount, Reject::BadId, Reject::ZeroId, Reject::UnknownKey, Reject::BadValue, Reject::OutOfRange, Reject::TooManyIds] {
        assert!(!why.name().is_empty() && why.name().bytes().all(|b| b.is_ascii_lowercase() || b == b'_' || b.is_ascii_digit()));
    }
}

#[test]
fn arbitrary_bytes_never_panic() {
    let mut seed = 0x2545_f491_4f6c_dd1du64;
    let mut next = move || {
        seed ^= seed << 13;
        seed ^= seed >> 7;
        seed ^= seed << 17;
        seed
    };
    let alphabet = b"mc_loadouts 1\n\r\t #0123456789abcdefABCDEFweight walk_speed_max.-+\xff\xc3\xa9x";
    for round in 0..3000 {
        let len = (next() % 400) as usize;
        let mut bytes = if round % 2 == 0 { b"mc_loadouts 1\n".to_vec() } else { Vec::new() };
        for _ in 0..len {
            bytes.push(alphabet[(next() % alphabet.len() as u64) as usize]);
        }
        let (table, report) = parse(&bytes);
        assert!(table.len() <= MAX_IDS);
        for entry in table.entries() {
            assert_ne!(entry.id, 0);
            for key in 0..KEYS {
                if entry.has[key] {
                    assert!(in_range(key, entry.value[key]));
                }
            }
        }
        if report.state != FileState::Ok {
            assert_eq!(table.len(), 0);
        }
    }
}

#[test]
fn store_lookup() {
    let store = Store::new();
    assert_eq!((store.len(), store.lookup(0xf589, 0)), (0, None));
    let (table, _) = parse(&file("0000f589 weight 130.0\n0000f589 walk_speed_max 1.6\n0000f58c weight 61\n"));
    store.publish(&table);
    assert_eq!(store.len(), 2);
    assert_eq!(store.lookup(0xf589, 0), Some((0, 130.0)));
    assert_eq!(store.lookup(0xf589, 1), Some((0, 1.6)));
    assert_eq!(store.lookup(0xf58c, 0), Some((1, 61.0)));
    assert_eq!(store.lookup(0xf58c, 1), None);
    assert_eq!(store.lookup(0xf58b, 0), None);
    assert_eq!(store.lookup(0, 0), None);
    assert_eq!(store.lookup(0xf589, 2), None);
    assert_eq!(store.lookup(0xf589, usize::MAX), None);
    // once per (entry, key)
    assert!(store.first_apply(0, 0));
    assert!(!store.first_apply(0, 0));
    assert!(store.first_apply(0, 1));
    assert!(store.first_apply(1, 0));
    assert!(!store.first_apply(99, 0) && !store.first_apply(0, 9));
    // a full table
    let mut body = String::new();
    for i in 1..=32u32 {
        body += &format!("{:08x} walk_speed_max 1.5\n", i << 8);
    }
    let (table, _) = parse(&file(&body));
    store.publish(&table);
    assert_eq!(store.len(), 32);
    assert_eq!(store.lookup(32 << 8, 1), Some((31, 1.5)));
    assert_eq!(store.lookup(0xf589, 0), None);
    // an empty table switches everything off again
    store.publish(&Table::new());
    assert_eq!((store.len(), store.lookup(1 << 8, 1)), (0, None));
}

// ---------------------------------------------------------------- decision

fn facts() -> Facts {
    Facts { fighter_cat: 0, cat_accessor: 0, round_trip: true, cat_object: 0, kind_accessor: GUNNER, kind_object: GUNNER, entry_accessor: 1, entry_object: 1 }
}

fn store_f589() -> Store {
    let store = Store::new();
    let (table, _) = parse(&file("0000f589 weight 130.0\n0000f589 walk_speed_max 1.6\n0000aaaa weight 70\n"));
    store.publish(&table);
    store
}

#[test]
fn constants_match_the_reports() {
    assert_eq!(HASH_WEIGHT, 0x0607cd5541);
    assert_eq!(HASH_WALK_SPEED_MAX, 0x0ee2ec2860);
    assert_eq!(TABLE_BASE, 0x5307760);
    assert_eq!(VTABLE_WORK, 0x4f89490);
    assert_eq!(VTABLE_OTHER, 0x4f73738);
    assert_eq!(PARENT_WORK_OFFSET, 0x50);
    assert_eq!(id_addr(0, 0), Some(0x53085b8));
    assert_eq!(special_addr(0, 0), Some(0x5307802));
    assert_eq!(id_addr(0, 1), Some(0x53085b8 + 0x240));
    assert_eq!(id_addr(0x7100000000, 7), Some(0x7100000000 + 0x5307760 + 0xe58 + 7 * 0x240));
    assert_eq!(id_addr(0, 8), None);
    assert_eq!(special_addr(0, 8), None);
    assert_eq!(id_addr(0, u32::MAX), None);
    assert_eq!((SITE_PARAM.offset, SITE_PARAM.words), (0x4e53e0, [0xf9401c00, 0xf9400008, 0xf9401903, 0xd61f0060]));
    assert_eq!((SITE_CUSTOM.offset, SITE_CUSTOM.words), (0x4e53f0, [0xf9401c00, 0xf9400008, 0xf9401d03, 0xd61f0060]));
    assert_eq!(core::mem::size_of::<Site>(), 24);
    assert!(words_equal(&SITE_PARAM.words, &SITE_PARAM.words));
    assert!(!words_equal(&SITE_PARAM.words, &SITE_CUSTOM.words));
    assert_eq!(hash_index(HASH_WEIGHT), Some(0));
    assert_eq!(hash_index(HASH_WALK_SPEED_MAX), Some(1));
    assert_eq!(hash_index(HASH_WEIGHT + 1), None);
    assert_eq!(hash_index(0), None);
}

#[test]
fn vtable_and_pointer_guard() {
    let base = 0x39_9280_4000usize;
    assert_eq!(vtable_class(base, (base + 0x4f89490) as u64), 1);
    assert_eq!(vtable_class(base, (base + 0x4f73738) as u64), 2);
    assert_eq!(vtable_class(base, (base + 0x4f89498) as u64), 0);
    assert_eq!(vtable_class(base, 0x4f89490), 0);
    assert_eq!(vtable_class(base, 0), 0);
    assert_eq!(vtable_class(0, 0x4f89490), 0);

    assert_eq!(pointer_guard(0x1000, 1, 0x2000, 0x1000), St::Ok);
    assert_eq!(pointer_guard(0, 1, 0x2000, 0), St::Vtable);
    assert_eq!(pointer_guard(0x1000, 2, 0x2000, 0x1000), St::Vtable);
    assert_eq!(pointer_guard(0x1000, 0, 0x2000, 0x1000), St::Vtable);
    assert_eq!(pointer_guard(0x1000, 1, 0, 0x1000), St::NoParent);
    assert_eq!(pointer_guard(0x1000, 1, 0x2000, 0x1008), St::BackPtr);
    assert_eq!(pointer_guard(0x1000, 1, 0x2000, 0), St::BackPtr);
}

#[test]
fn identify_requires_every_fact() {
    assert_eq!(identify(&facts()), Ident { st: St::Ok, kind: GUNNER, player: 1 });
    assert_eq!(identify(&Facts { cat_accessor: 1, ..facts() }), Ident::unknown(St::Category));
    assert_eq!(identify(&Facts { cat_accessor: 4, ..facts() }), Ident::unknown(St::Category));
    assert_eq!(identify(&Facts { round_trip: false, ..facts() }), Ident::unknown(St::RoundTrip));
    assert_eq!(identify(&Facts { cat_object: 5, ..facts() }), Ident::unknown(St::Category2));
    assert_eq!(identify(&Facts { kind_object: 0x4b, ..facts() }), Ident::unknown(St::KindMismatch));
    assert_eq!(identify(&Facts { kind_accessor: -1, ..facts() }), Ident::unknown(St::KindMismatch));
    assert_eq!(identify(&Facts { entry_object: 0, ..facts() }).st, St::EntryMismatch);
    for bad in [-1, 8, 9, 0x5000_0000, i32::MIN] {
        let id = identify(&Facts { entry_accessor: bad, entry_object: bad, ..facts() });
        assert_eq!((id.st, id.player), (St::EntryRange, -1), "{bad}");
    }
    for p in 0..8 {
        assert_eq!(identify(&Facts { entry_accessor: p, entry_object: p, ..facts() }).player, p);
    }
    // the placeholder values the hook starts from never produce an identity
    let start = Facts { fighter_cat: 0, cat_accessor: 0, round_trip: false, cat_object: -1, kind_accessor: -1, kind_object: -2, entry_accessor: -1, entry_object: -2 };
    assert_eq!(identify(&start).st, St::RoundTrip);
    assert_eq!(identify(&Facts { round_trip: true, ..start }).st, St::Category2);
    assert_eq!(identify(&Facts { round_trip: true, cat_object: 0, ..start }).st, St::KindMismatch);
    // a non-Gunner fighter still gets an identity (for the log); the kind test is in decide()
    assert_eq!(identify(&Facts { kind_accessor: 0, kind_object: 0, ..facts() }), Ident { st: St::Ok, kind: 0, player: 1 });
}

#[test]
fn decide_all_conditions() {
    let store = store_f589();
    let gunner = Ident { st: St::Ok, kind: GUNNER, player: 0 };
    assert_eq!(decide(&gunner, GUNNER, 0xf589, &store, 0), Decision { st: St::Ok, entry: 0, value: Some(130.0) });
    assert_eq!(decide(&gunner, GUNNER, 0xf589, &store, 1), Decision { st: St::Ok, entry: 0, value: Some(1.6) });
    // same saved fighter on another port
    let port2 = Ident { player: 1, ..gunner };
    assert_eq!(decide(&port2, GUNNER, 0xf589, &store, 0).value, Some(130.0));
    // the other Gunner: no entry
    assert_eq!(decide(&port2, GUNNER, 0xf58b, &store, 0), Decision::vanilla(St::NoEntry));
    // an entry without this key
    assert_eq!(decide(&gunner, GUNNER, 0xaaaa, &store, 0).value, Some(70.0));
    assert_eq!(decide(&gunner, GUNNER, 0xaaaa, &store, 1), Decision::vanilla(St::NoEntry));
    // slot id 0 (default Mii, or nothing in the slot)
    assert_eq!(decide(&gunner, GUNNER, 0, &store, 0), Decision::vanilla(St::NoSlotId));
    // not a Gunner, even if the slot still holds a known id
    for kind in [0, 0x49, 0x4b, -1] {
        assert_eq!(decide(&Ident { kind, ..gunner }, GUNNER, 0xf589, &store, 0), Decision::vanilla(St::NotGunner));
    }
    // identity not resolved: the reason is passed through, never an override
    for st in [St::Off, St::Vtable, St::NoParent, St::BackPtr, St::Reentry, St::GuardFull, St::Category, St::RoundTrip, St::Category2, St::KindMismatch, St::EntryMismatch, St::EntryRange] {
        let d = decide(&Ident { st, kind: GUNNER, player: 0 }, GUNNER, 0xf589, &store, 0);
        assert_eq!(d, Decision::vanilla(st));
    }
    for player in [-1, 8, 100] {
        assert_eq!(decide(&Ident { player, ..gunner }, GUNNER, 0xf589, &store, 0), Decision::vanilla(St::EntryRange));
    }
    // empty store
    assert_eq!(decide(&gunner, GUNNER, 0xf589, &Store::new(), 0), Decision::vanilla(St::NoEntry));
    assert_eq!(decide(&gunner, GUNNER, 0xf589, &store, 2), Decision::vanilla(St::NoEntry));
}

#[test]
fn status_names_are_distinct() {
    let all = [St::Ok, St::Off, St::Vtable, St::NoParent, St::BackPtr, St::Reentry, St::GuardFull, St::Category, St::RoundTrip, St::Category2,
        St::KindMismatch, St::EntryMismatch, St::EntryRange, St::NotGunner, St::NoSlotId, St::NoEntry];
    assert_eq!(all.len(), ST_COUNT);
    let mut names: Vec<&str> = all.iter().map(|s| s.name()).collect();
    for (i, st) in all.iter().enumerate() {
        assert_eq!(*st as usize, i);
    }
    names.sort();
    names.dedup();
    assert_eq!(names.len(), ST_COUNT);
}

#[test]
fn thread_guard() {
    let guard = ThreadGuard::new();
    let a = guard.enter(0x1000);
    assert_eq!(a, Enter::Entered(0));
    assert_eq!(guard.enter(0x1000), Enter::Reentry);
    assert_eq!(guard.enter(0x2000), Enter::Entered(1));
    assert_eq!(guard.enter(0x2000), Enter::Reentry);
    guard.leave(0);
    assert_eq!(guard.enter(0x2000), Enter::Reentry);
    assert_eq!(guard.enter(0x1000), Enter::Entered(0));
    guard.leave(0);
    guard.leave(1);
    assert_eq!(guard.enter(0), Enter::Full);
    for t in 1..=GUARD_SLOTS as u64 {
        assert_eq!(guard.enter(t), Enter::Entered(t as usize - 1));
    }
    assert_eq!(guard.enter(99), Enter::Full);
    assert_eq!(guard.enter(3), Enter::Reentry);
    guard.leave(2);
    assert_eq!(guard.enter(99), Enter::Entered(2));
    guard.leave(1000); // out of range: ignored
}

#[test]
fn thread_guard_under_contention() {
    use std::sync::atomic::{AtomicU32, Ordering};
    use std::sync::Arc;
    let guard = Arc::new(ThreadGuard::new());
    let inside = Arc::new(AtomicU32::new(0));
    let bad = Arc::new(AtomicU32::new(0));
    let mut handles = Vec::new();
    for t in 1..=6u64 {
        let (guard, inside, bad) = (guard.clone(), inside.clone(), bad.clone());
        handles.push(std::thread::spawn(move || {
            for _ in 0..20000 {
                match guard.enter(t) {
                    Enter::Entered(slot) => {
                        inside.fetch_add(1, Ordering::Relaxed);
                        if guard.enter(t) != Enter::Reentry {
                            bad.fetch_add(1, Ordering::Relaxed);
                        }
                        guard.leave(slot);
                    }
                    _ => {
                        bad.fetch_add(1, Ordering::Relaxed);
                    }
                }
            }
        }));
    }
    for h in handles {
        h.join().unwrap();
    }
    // 6 threads, 8 slots: every enter succeeds and every nested enter is seen as re-entry
    assert_eq!((inside.load(Ordering::Relaxed), bad.load(Ordering::Relaxed)), (120000, 0));
}

// ---------------------------------------------------------------- logging helpers

#[test]
fn parent_table_counts_and_changes() {
    let t = ParentTable::new();
    let first = t.observe(0xaaa0, 0);
    assert_eq!(first, Seen { slot: Some(0), is_new: true, nth: 1, log: true });
    for n in 2..=4 {
        assert_eq!(t.observe(0xaaa0, 0), Seen { slot: Some(0), is_new: false, nth: n, log: true });
    }
    assert!(!t.observe(0xaaa0, 0).log);
    assert_eq!(t.observe(0xaaa0, 1).nth, 1);
    assert_eq!(t.observe(0, 0).slot, Some(1));

    let unresolved = signature(St::RoundTrip, &Ident::unknown(St::RoundTrip), 0);
    let gunner = Ident { st: St::Ok, kind: GUNNER, player: 0 };
    let applied = signature(St::Ok, &gunner, 0xf589);
    assert_ne!(unresolved, 0);
    assert_ne!(signature(St::Ok, &Ident { st: St::Ok, kind: 0, player: 0 }, 0), 0);
    // first signature is not a change; an identity that resolves later is
    assert!(!t.changed(Some(0), 0, unresolved));
    assert!(!t.changed(Some(0), 0, unresolved));
    assert!(t.changed(Some(0), 0, applied));
    assert!(!t.changed(Some(0), 0, applied));
    // the same address reused by a fighter with another id / port / kind
    assert!(t.changed(Some(0), 0, signature(St::NoEntry, &gunner, 0xf58b)));
    assert!(t.changed(Some(0), 0, signature(St::Ok, &Ident { player: 1, ..gunner }, 0xf589)));
    assert!(t.changed(Some(0), 0, signature(St::NotGunner, &Ident { kind: 0, ..gunner }, 0xf589)));
    // per hash, bounded
    assert!(!t.changed(Some(0), 1, applied));
    let mut reported = 0;
    for i in 0..100u32 {
        reported += t.changed(Some(0), 1, signature(St::Ok, &gunner, i + 1)) as u32;
    }
    assert_eq!(reported, L3_CHANGES_PER_PARENT_PER_HASH);
    assert!(!t.changed(None, 0, applied));
    assert!(!t.changed(Some(99), 0, applied));
    assert!(!t.changed(Some(0), 2, applied));

    let full = ParentTable::new();
    for p in 1..=40u64 {
        full.observe(p << 8, 0);
    }
    assert_eq!((full.distinct(), full.overflow()), (32, 8));
}

#[test]
fn formatting() {
    let mut b: LineBuf<160> = LineBuf::new();
    b.s("mc|L3").s("|p=").int(-1).s("|kind=").int(74).s("|id=").hex_fixed(0xf589, 8).s("|orig=").f32_dec(104.0).s("|v=").f32_dec(1.6);
    b.s("|x=").hex(0x24730e8d80).s("|n=").dec(0).s("|m=").int(i64::MIN).end_line();
    assert_eq!(text(&b), "mc|L3|p=-1|kind=74|id=0000f589|orig=104.0000|v=1.6000|x=0x24730e8d80|n=0|m=-9223372036854775808\n");
    let mut small: LineBuf<8> = LineBuf::new();
    small.s("0123456789abcdef").end_line();
    assert_eq!(small.as_bytes(), b"0123456\n");
    let mut p: LineBuf<64> = LineBuf::new();
    push_player(&mut p, 1, 0xf58b, [2, 2, 2, 2]);
    assert_eq!(text(&p), "|p1=0000f58b:02020202");
    assert!(totals_due(600) && totals_due(1200) && !totals_due(0) && !totals_due(599));
}
