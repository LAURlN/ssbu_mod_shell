//! Host-side unit tests for plugin/src/logic.rs (the pure part of the 0.1.0 diagnostic).
//! Built and run by run_host_test.sh with the host rustc; no skyline toolchain involved.
#![allow(dead_code)]

#[path = "../../plugin/src/logic.rs"]
mod logic;

use logic::*;
use std::sync::atomic::AtomicU32;

fn text<const N: usize>(b: &LineBuf<N>) -> String {
    String::from_utf8(b.as_bytes().to_vec()).unwrap()
}

#[test]
fn constants_match_the_reports() {
    assert_eq!(HASH_WEIGHT, 0x0607cd5541);
    assert_eq!(HASH_WALK_SPEED_MAX, 0x0ee2ec2860);
    assert_eq!(TABLE_BASE, 0x5307760);
    assert_eq!(id_addr(0, 0), Some(0x53085b8));
    assert_eq!(special_addr(0, 0), Some(0x5307802));
    assert_eq!(id_addr(0, 1), Some(0x53085b8 + 0x240));
    assert_eq!(special_addr(0, 1), Some(0x53079ca));
    assert_eq!(id_addr(0x7100000000, 7), Some(0x7100000000 + 0x5307760 + 0xe58 + 7 * 0x240));
    assert_eq!(id_addr(0, 8), None);
    assert_eq!(special_addr(0, 8), None);
    assert_eq!(id_addr(0, u32::MAX), None);
    assert_eq!(SITE_PARAM.offset, 0x4e53e0);
    assert_eq!(SITE_STORE.offset, 0x179e440);
    assert_eq!(SITE_LOAD.offset, 0x17c8210);
    assert_eq!(core::mem::size_of::<Site>(), 24);
}

#[test]
fn hash_filter() {
    assert_eq!(hash_index(HASH_WEIGHT), Some(0));
    assert_eq!(hash_index(HASH_WALK_SPEED_MAX), Some(1));
    assert_eq!(hash_index(0), None);
    assert_eq!(hash_index(HASH_WEIGHT - 1), None);
    assert_eq!(hash_index(HASH_WEIGHT | 1 << 40), None);
    assert_eq!(hash_name(0), "weight");
    assert_eq!(hash_name(1), "walk_speed_max");
}

#[test]
fn word_compare() {
    assert!(words_equal(&SITE_PARAM.words, &[0xf9401c00, 0xf9400008, 0xf9401903, 0xd61f0060]));
    for k in 0..4 {
        let mut w = SITE_STORE.words;
        w[k] ^= 1;
        assert!(!words_equal(&w, &SITE_STORE.words));
    }
}

#[test]
fn editor_range_is_inclusive() {
    assert!(!in_editor_range(0x19d094c));
    assert!(in_editor_range(0x19d0950));
    assert!(in_editor_range(0x19d4000));
    assert!(in_editor_range(0x19dc304));
    assert!(!in_editor_range(0x19dc308));
    assert!(!in_editor_range(0x230f2a8));
    assert!(!in_editor_range(0x25cd0e8));
}

#[test]
fn first_64_then_count_only() {
    let c = AtomicU32::new(0);
    let mut logged = 0;
    for i in 1..=200u32 {
        let (n, log) = count_event(&c, L1_LOG_LIMIT);
        assert_eq!(n, i);
        assert_eq!(log, i <= 64);
        logged += log as u32;
    }
    assert_eq!(logged, 64);
    // wrap-around does not re-open logging
    let c = AtomicU32::new(u32::MAX);
    assert_eq!(count_event(&c, 64), (0, false));
}

#[test]
fn totals_cadence() {
    let due: Vec<u32> = (0..=1800).filter(|n| totals_due(*n)).collect();
    assert_eq!(due, vec![600, 1200, 1800]);
}

#[test]
fn parent_table_four_per_hash_per_parent() {
    let t = ParentTable::new();
    let first = t.observe(0x1000, 0);
    assert_eq!(first, Seen { slot: Some(0), is_new: true, nth: 1, log: true });
    for n in 2..=10u32 {
        let s = t.observe(0x1000, 0);
        assert_eq!(s.slot, Some(0));
        assert!(!s.is_new);
        assert_eq!(s.nth, n);
        assert_eq!(s.log, n <= 4);
    }
    // the other hash has its own budget on the same parent and is not "new"
    let s = t.observe(0x1000, 1);
    assert_eq!(s, Seen { slot: Some(0), is_new: false, nth: 1, log: true });
    // a second parent gets the next slot
    let s = t.observe(0x2000, 1);
    assert_eq!(s, Seen { slot: Some(1), is_new: true, nth: 1, log: true });
    assert_eq!(t.distinct(), 2);
    assert_eq!(t.overflow(), 0);
}

#[test]
fn parent_table_keeps_32_and_counts_the_rest() {
    let t = ParentTable::new();
    for p in 1..=32u64 {
        let s = t.observe(p * 0x100, 0);
        assert!(s.is_new && s.log);
        assert_eq!(s.slot, Some(p as usize - 1));
    }
    let s = t.observe(0xdead_0000, 0);
    assert_eq!(s, Seen { slot: None, is_new: false, nth: 0, log: false });
    let s = t.observe(0xdead_0000, 1);
    assert!(!s.log && !s.is_new);
    assert_eq!(t.distinct(), 32);
    assert_eq!(t.overflow(), 2);
    // known parents still work when the table is full
    let s = t.observe(0x2000, 0);
    assert_eq!((s.slot, s.is_new, s.nth), (Some(31), false, 2));
    // out-of-range hash index cannot index out of bounds
    let s = t.observe(0x100, 7);
    assert_eq!(s.slot, None);
}

#[test]
fn parent_table_null_parent_and_threads() {
    let t = ParentTable::new();
    let s = t.observe(0, 0);
    assert!(s.is_new);
    let s = t.observe(0, 0);
    assert!(!s.is_new);
    assert_eq!(t.distinct(), 1);

    static SHARED: ParentTable = ParentTable::new();
    let handles: Vec<_> = (0..8)
        .map(|_| {
            std::thread::spawn(|| {
                let mut new = 0u32;
                let mut logged = 0u32;
                for round in 0..1000u64 {
                    let s = SHARED.observe(0x5000 + (round % 20) * 8, (round % 2) as usize);
                    new += s.is_new as u32;
                    logged += s.log as u32;
                }
                (new, logged)
            })
        })
        .collect();
    let (mut new, mut logged) = (0, 0);
    for h in handles {
        let (n, l) = h.join().unwrap();
        new += n;
        logged += l;
    }
    assert_eq!(new, 20, "each parent is new exactly once across threads");
    assert_eq!(SHARED.distinct(), 20);
    // each parent sees exactly one hash here (round%20 fixes round%2): 4 logged lines each
    assert_eq!(logged, 20 * 4);
}

#[test]
fn line_formatting() {
    let mut b: LineBuf<128> = LineBuf::new();
    b.s("mc|L3|seq=").dec(12).s("|x0=").hex(0x7101abcdef).s("|z=").hex(0).s("|bits=0x").hex_fixed(0x42c80000, 8);
    b.end_line();
    assert_eq!(text(&b), "mc|L3|seq=12|x0=0x7101abcdef|z=0x0|bits=0x42c80000\n");

    let mut b: LineBuf<64> = LineBuf::new();
    b.dec(0).s(",").dec(u64::MAX).s(",").hex(u64::MAX).s(",").hex_fixed(0xab, 2).s(",").hex_fixed(0x5, 2);
    assert_eq!(text(&b), "0,18446744073709551615,0xffffffffffffffff,ab,05");

    let mut b: LineBuf<160> = LineBuf::new();
    push_player(&mut b, 0, 0x1234, [0, 1, 2, 0xff]);
    push_player(&mut b, 7, 0xdeadbeef, [2, 2, 2, 2]);
    assert_eq!(text(&b), "|p0=00001234:000102ff|p7=deadbeef:02020202");
}

#[test]
fn float_formatting() {
    let cases: [(f32, &str); 10] = [
        (0.0, "0.0000"),
        (98.0, "98.0000"),
        (1.155, "1.1550"),
        (-0.5, "-0.5000"),
        (1.99996, "2.0000"),
        (104.0, "104.0000"),
        (f32::NAN, "nan"),
        (f32::INFINITY, "inf"),
        (f32::NEG_INFINITY, "-inf"),
        (5.0e9, "big"),
    ];
    for (v, want) in cases.iter() {
        let mut b: LineBuf<32> = LineBuf::new();
        b.f32_dec(*v);
        assert_eq!(text(&b), *want, "{}", v);
    }
}

#[test]
fn truncation_never_overruns_and_keeps_the_newline() {
    let mut b: LineBuf<16> = LineBuf::new();
    for _ in 0..10 {
        b.s("0123456789").hex(u64::MAX).dec(u64::MAX);
    }
    b.end_line();
    let bytes = b.as_bytes();
    assert_eq!(bytes.len(), 16);
    assert_eq!(bytes[15], b'\n');
    assert_eq!(&bytes[..15], b"01234567890xfff");
    b.end_line();
    b.s("more");
    assert_eq!(b.as_bytes().len(), 16);

    let mut b: LineBuf<1> = LineBuf::new();
    b.s("x").end_line();
    assert_eq!(b.as_bytes(), b"\n");
    let mut b: LineBuf<0> = LineBuf::new();
    b.s("x").end_line();
    assert_eq!(b.as_bytes(), b"");
}
